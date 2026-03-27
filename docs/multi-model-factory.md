# Multi-Model AI Software Factory

> How Cognitive OS evolves from single-provider (Claude only) to a true multi-model factory where different AI models handle different layers of work.
> Updated: 2026-03-27

---

## Vision

Cognitive OS is not tied to one AI model. It orchestrates MULTIPLE models as a factory:

- **Strategic layer** (reasoning, architecture) -- most capable model
- **Execution layer** (implementation, features) -- balanced model
- **Worker layer** (repetitive, bulk) -- fastest/cheapest model

The key insight: there is no "best model." There is only the best ORCHESTRATION of models. A $0.25/1M token model doing docs is better than a $75/1M token model doing the same docs. The factory's job is to match task to model with precision.

---

## Current State (v0.1.0)

Today we support 8 models via `lib/model_router.py` but primarily use Claude:

```
CURRENT:
  Claude Opus 4.6    -> design, debugging, proposals     (expensive, deep reasoning)
  Claude Sonnet 4    -> implementation, specs, verification (balanced)
  Claude Haiku 3.5   -> archiving, docs, formatting       (cheap, fast)

  GPT-4o             -> configured, rarely used
  Gemini 2.5 Pro     -> configured, rarely used
  DeepSeek R1        -> configured, rarely used
  Llama 3 70B        -> local model, configured but untested
  Qwen 3 32B         -> local model, configured but untested
```

The model router (`lib/model_router.py`) already maps tasks to capability requirements (reasoning, speed, code, long_context, budget) and selects the best model based on scores. LiteLLM integration exists for non-Claude routing. The infrastructure is in place; what remains is operational validation and dynamic selection.

---

## Future State: The 3-Layer Factory Model

```
+---------------------------------------------------+
|  STRATEGIC LAYER (Brain)                          |
|  Models: Claude Opus, Gemini 2.5 Pro, GPT-4o     |
|  Tasks: architecture, design, complex debugging    |
|  Role: CTO / Chief Architect                      |
|  Cost: $$$  Speed: Slow  Quality: Highest         |
+---------------------------------------------------+
|  EXECUTION LAYER (Senior Engineers)               |
|  Models: Claude Sonnet, DeepSeek R1, GPT-4o       |
|  Tasks: implementation, refactoring, testing       |
|  Role: Senior Engineer / Tech Lead                |
|  Cost: $$   Speed: Medium  Quality: High          |
+---------------------------------------------------+
|  WORKER LAYER (Execution Army)                    |
|  Models: Claude Haiku, Llama 3, Qwen 3            |
|  Tasks: bulk operations, docs, formatting, scraping|
|  Role: Junior Dev / Automation Worker             |
|  Cost: $    Speed: Fast   Quality: Adequate       |
+---------------------------------------------------+
```

Each layer has different cost, speed, and quality characteristics. The orchestrator assigns tasks to the appropriate layer based on complexity classification.

---

## How It Maps to the SDD Pipeline

The Spec-Driven Development pipeline routes each phase to the appropriate factory layer:

| SDD Phase | Layer | Default Model | Why |
|---|---|---|---|
| explore | Strategic | opus | Deep codebase understanding needed |
| propose | Strategic | opus | Architecture decisions require deep reasoning |
| spec | Execution | sonnet | Structured writing, balanced quality/cost |
| design | Strategic | opus | Technical design decisions are high-stakes |
| tasks | Execution | sonnet | Mechanical decomposition, predictable output |
| apply | Execution | sonnet | Code implementation, fast iteration cycles |
| verify | Execution | sonnet | Quality verification with structured checks |
| archive | Worker | haiku | Simple documentation, minimal reasoning needed |

This mapping is defined in `rules/model-routing.md` and implemented by `lib/model_router.py`. The `TASK_REQUIREMENTS` dictionary maps each task to its primary capability need (reasoning, speed, code, long_context, budget), and `select_model()` picks the best available model.

---

## How It Maps to the Safety Mesh

The safety mesh (see `docs/safety-mesh.md`) uses different model tiers for different verification layers:

| Safety Layer | Model Used | Why |
|---|---|---|
| Clarification gate | None (bash hook) | No LLM needed -- keyword matching and scoring |
| Blast radius | None (bash hook) | No LLM needed -- file counting and pattern detection |
| Assumption tracking | None (bash hook) | No LLM needed -- regex pattern matching |
| Cross-verification | Worker (haiku) | Cheap second opinion on agent claims |
| Adversarial review | Strategic (opus) | Deep critical analysis requires strongest reasoning |
| Planning poker | All 3 layers | Each layer estimates independently for consensus |

Planning poker (`lib/planning_poker.py`) is the clearest example of multi-model collaboration: three agents with different capability profiles independently estimate a task's complexity, then their estimates are compared and reconciled through divergence detection and consensus building.

---

## Dynamic Model Selection

Instead of static routing, the factory dynamically selects models based on four factors:

1. **Task complexity** -- determines which layer handles the task
2. **Budget remaining** -- may downgrade to a cheaper layer
3. **Historical performance** -- calibrated per model via estimation accuracy tracking
4. **Availability** -- fallback chain if the primary provider is unavailable

### Selection Flow Example

```
Task arrives: "Add JWT authentication"
  |
  +-- Planning Poker estimates: LARGE complexity
  |
  +-- Budget check: 60% remaining -> full budget available
  |
  +-- Historical: sonnet succeeded 85% on similar tasks
  |
  +-- Selection:
      explore -> opus    (strategic -- needs deep understanding)
      spec    -> sonnet  (execution -- structured output OK)
      apply   -> sonnet  (execution -- implementation)
      verify  -> opus    (strategic -- critical review)
      archive -> haiku   (worker -- simple docs)

      Estimated cost: $2.40
      With all-opus:  $8.50 (3.5x more expensive, marginally better)
```

The `select_model()` function in `lib/model_router.py` implements this logic. It scores candidates by their primary capability requirement, filters by budget constraints, and optionally prefers local models for zero-cost execution.

---

## Multi-Provider Routing via LiteLLM

LiteLLM proxy (already running in Docker via `docker-compose.cognitive-os.yml`) enables routing to any provider through a single API interface:

```
Cognitive OS -> LiteLLM Proxy -> Anthropic (Claude)
                              -> OpenAI (GPT-4o)
                              -> Google (Gemini)
                              -> DeepSeek
                              -> Local (Ollama/vLLM)
```

Benefits:

- **Single API interface** regardless of provider -- `lib/litellm_client.py` handles all non-Claude models
- **Automatic failover** if one provider is down -- `route_and_execute()` falls back to Claude
- **Cost tracking per provider** -- `lib/cost_predictor.py` normalizes costs across providers
- **Rate limit distribution** -- `lib/rate_limit_protection.py` distributes load across providers

The `route_and_execute()` function in `lib/model_router.py` orchestrates the full flow: select the best model, check if LiteLLM routing is available, execute through the appropriate provider, and return a `RoutedResult` with cost and token tracking.

---

## Agent Definition Format

Agents declare their model preferences in squad or package definitions:

```yaml
# In squads/backend-squad.yaml or cos-package.yaml
agents:
  architect:
    layer: strategic
    preferred_model: opus
    fallback: gemini-2.5-pro
    tasks: [design, propose, verify]

  implementer:
    layer: execution
    preferred_model: sonnet
    fallback: deepseek-r1
    tasks: [apply, spec, tasks]

  documenter:
    layer: worker
    preferred_model: haiku
    fallback: qwen-3-32b  # local, free
    tasks: [archive, document-feature]
```

Per-agent model overrides are supported via `customizations/{agent-name}.yaml` (see `rules/agent-customization.md`). The deep merge system applies: customization replaces the base model, with fallback chains preserved.

---

## Cost Optimization Strategies

### 1. Layer-appropriate selection

Do not use opus for docs. Do not use haiku for architecture. The model router ensures each task is handled by the cheapest model that meets the capability threshold.

### 2. Local model offloading

Use Llama 3 70B or Qwen 3 32B for zero-cost worker tasks. Local models have `cost_per_1m_in: 0` and `cost_per_1m_out: 0` in the routing table. The resource governor tracks these as $0.00, making them ideal for iterative loops (TDD, auto-refine).

### 3. Provider arbitrage

Same quality, cheapest provider. DeepSeek R1 offers comparable reasoning to Claude Opus at a fraction of the cost ($0.55/$2.19 vs $15.00/$75.00 per 1M tokens). Gemini 2.5 Pro provides 1M context at $1.25/$5.00.

### 4. Batch to workers

Bulk operations (formatting, doc generation, boilerplate) are parallelized across haiku or local models. Multiple cheap calls replace one expensive call.

### 5. Cache in Engram

Never re-compute what has been computed before. SDD artifacts (specs, designs, proposals) are stored in Engram with structured topic keys. Subsequent sessions retrieve rather than regenerate.

### 6. Model downgrade chain

When budget pressure is detected (managed by `rules/resource-governance.md`):

| Budget Used | Action |
|---|---|
| < 80% | Use routing table as-is |
| 80-95% | Force sonnet for all non-critical tasks |
| 95-100% | Force haiku for everything except security/critical |
| > 100% | BLOCK all agent launches, alert user |

---

## Capability Assessment

The `lib/capability_levels.py` module assesses model capability and auto-disables unnecessary safety nets:

| Level | Name | Description | Disabled Components |
|---|---|---|---|
| 1 | basic | All safety nets active | None |
| 2 | good | All safety nets active | None |
| 3 | excellent | Model manages its own context | context-management |
| 4 | autonomous | Model is self-correcting | + clarification-gate, assumption-tracking, confidence-gate, model-routing, blast-radius |

Higher-capability models (like Claude Opus at level 3-4) need fewer guardrails. Lower-capability models (like local Llama at level 1-2) get the full safety mesh. The `should_component_run()` function checks whether a given hook or rule should activate based on the current model's capability level.

---

## Roadmap Integration

| Phase | What Changes |
|---|---|
| Phase 1 (Q2 2026) | LiteLLM routing active, 3+ providers validated, local models via Ollama |
| Phase 2 (Q3 2026) | Dynamic layer selection based on task analysis, Paperclip dashboard shows model usage |
| Phase 3 (Q4 2026) | A/B testing for skills across models, security scanning with model-appropriate analysis |
| Phase 5 (2027+) | Fully autonomous model selection, self-optimizing routing based on historical accuracy |

See `docs/roadmap.md` Phase 1 for the detailed implementation plan.

---

## Relationship to Existing Components

| Component | Role in Factory | Location |
|---|---|---|
| `model_router.py` | Static routing table with dynamic selection logic | `lib/model_router.py` |
| `planning_poker.py` | Multi-model estimation -- uses all 3 layers independently | `lib/planning_poker.py` |
| `capability_levels.py` | Model capability assessment -- drives layer assignment and safety net toggling | `lib/capability_levels.py` |
| `cost_predictor.py` | Historical cost data from actual API responses -- informs model selection | `lib/cost_predictor.py` |
| `estimation_calibrator.py` | Accuracy tracking per model -- improves selection over time | `lib/estimation_calibrator.py` |
| `agent_bus.py` | Communication between models working on same task via Valkey pub/sub | `lib/agent_bus.py` |
| `rate_limit_protection.py` | Distributes load across providers to avoid rate limits | `lib/rate_limit_protection.py` |
| `litellm_client.py` | LiteLLM proxy client for non-Claude model execution | `lib/litellm_client.py` |

---

## Architecture Alignment

The multi-model factory respects the 5-layer architecture (see `docs/architecture-principles.md`):

- **Layer 1 (Rules)**: `rules/model-routing.md` defines WHAT model to use for each task type. Model-agnostic.
- **Layer 2 (Skills)**: Skills are written for any LLM. They do not reference specific models.
- **Layer 3 (Hooks)**: No hooks are model-specific. They enforce rules regardless of which model executed.
- **Layer 4 (Libs)**: `lib/model_router.py` and `lib/litellm_client.py` implement the routing mechanism. Replaceable.
- **Layer 5 (Externals)**: LiteLLM proxy, Anthropic API, OpenAI API, Ollama. All accessed through Layer 4 adapters.

This means swapping or adding a new model provider requires changes ONLY in Layer 4 and 5 -- rules, skills, and hooks remain untouched.

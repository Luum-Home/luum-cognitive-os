# Architecture Principles: Clean Architecture for Agent Operating Systems

> The 5-layer dependency model that governs how Cognitive OS agentic primitives relate to each other.
> This is a novel architectural pattern adapted from Clean Architecture for AI agent systems.

---

## The 5-Layer Architecture

```
┌─────────────────────────────────────────────┐
│           Layer 1: RULES (Core)             │
│  Pure behavioral constraints. No deps.      │
│  "What agents MUST and MUST NOT do"         │
├─────────────────────────────────────────────┤
│           Layer 2: SKILLS (Capabilities)    │
│  Agent procedures. Depend on rules.         │
│  "HOW agents accomplish tasks"              │
├─────────────────────────────────────────────┤
│           Layer 3: HOOKS (Integration)      │
│  Lifecycle glue. Implement rules.           │
│  "WHEN rules are enforced"                  │
├─────────────────────────────────────────────┤
│           Layer 4: LIBS (Infrastructure)    │
│  Runtime code. Replaceable.                 │
│  "WITH WHAT agents execute"                 │
├─────────────────────────────────────────────┤
│           Layer 5: EXTERNALS (Services)     │
│  Docker, LLM APIs, Engram, Git.             │
│  "WHERE agents operate"                     │
└─────────────────────────────────────────────┘
```

Inner layers define intent. Outer layers implement mechanism. The boundary between them is strict and directional.

---

## The Dependency Rule

**Dependencies ONLY point inward (toward Layer 1).**

- Layer 5 depends on Layer 4 (libs call external services)
- Layer 4 depends on Layer 3 (libs are invoked by hooks)
- Layer 3 depends on Layer 2 (hooks enforce skills' contracts)
- Layer 2 depends on Layer 1 (skills follow rules)
- Layer 1 depends on NOTHING

### What This Means Concretely

```
rules/trust-score.md              <- defines what trust score IS          (Layer 1)
  ^ referenced by
skills/sdd-verify/SKILL.md        <- uses trust score in verification     (Layer 2)
  ^ implemented by
hooks/trust-score-validator.sh    <- extracts and logs trust scores       (Layer 3)
  ^ uses
lib/claude_executor.py            <- runs the agent that produces scores  (Layer 4)
  ^ calls
Claude API (external)             <- the actual LLM service               (Layer 5)
```

### Prohibited Dependencies

| From | To | Why |
|------|----|-----|
| Rule -> Hook | A rule must not reference a specific hook by filename | Rules are intent, not mechanism |
| Rule -> Lib | A rule must not import a Python module | Rules are model-agnostic markdown |
| Skill -> Lib | A skill must not call a lib function directly | Skills are LLM instructions, not code |
| Hook -> Rule (write) | A hook must not modify a rule's content | Hooks enforce rules, they do not define them |
| Lib -> Rule (read) | A lib must not parse rules/*.md directly | Libs receive parameters via config or function args |

### Permitted Dependencies

| From | To | How |
|------|----|-----|
| Skill -> Rule | By name reference | "Follow rules/acceptance-criteria.md" |
| Hook -> Rule | By reading content | Parse a rule to extract thresholds |
| Hook -> Config | By reading YAML | Read cognitive-os.yaml for parameters |
| Hook -> Hook shared lib | By sourcing | `source hooks/_lib/common.sh` |
| Lib -> Config | By reading YAML | Read cognitive-os.yaml for service URLs |
| Lib -> External | By API call | HTTP, subprocess, socket |

---

## Layer Characteristics

### Layer 1: Rules (Core)

Rules are pure behavioral constraints. They define what agents MUST and MUST NOT do, independent of any implementation.

| Property | Value |
|----------|-------|
| Format | Markdown (.md) |
| Location | `rules/` |
| Dependencies | NONE |
| Loaded by | `self-install.sh` symlinks 16 core rules to `.claude/rules/cos/`; all others load on contextual trigger |
| Testing | Behavior tests: does the system follow the rule? |
| Count | 16 core always-loaded; 150+ total |

**Design constraints:**
- A rule describes WHAT, never HOW. "Every agent completion must include a Trust Report" is a rule. "Extract the score with grep and log it to JSONL" is a hook's job.
- Rules are model-agnostic. They work whether the LLM is Claude, GPT, Gemini, or a local model.
- Rules reference other rules by name, never by file path of a hook or lib.

**Antipattern: Rule-as-documentation.** When a rule exceeds ~60 lines, it is mixing behavioral constraint (WHAT) with implementation guidance (HOW) and rationale (WHY). Fix: keep the rule concise; move documentation to `docs/`.

**Example:** `rules/trust-score.md` defines what a Trust Report contains and how trust is scored. It does not describe how `hooks/trust-score-validator.sh` extracts the score.

### Layer 2: Skills (Capabilities)

Skills are structured instructions that tell the LLM agent how to accomplish a task. They translate rules into actionable procedures.

| Property | Value |
|----------|-------|
| Format | Markdown (SKILL.md) with YAML frontmatter |
| Location | `skills/*/` |
| Dependencies | May reference rules by name |
| Testing | Behavior tests: does the skill produce correct output? |
| Count | 72 |

**Design constraints:**
- Skills are instructions FOR the LLM, not code executed BY the system.
- A skill may contain illustrative code blocks (examples for the agent to follow), but the skill itself is not executable code.
- Skills reference rules conceptually: "follow the acceptance criteria rule" not "call lib/verify.py".

**Antipattern: Skill-calling-code.** A skill that embeds Python functions or bash scripts as its implementation rather than as examples. Skills instruct the agent to USE tools (Bash, Read, Edit), not to BE tools.

**Example:** `skills/sdd-verify/SKILL.md` instructs the agent to perform adversarial review following `rules/adversarial-review.md` and produce a Trust Report per `rules/trust-score.md`.

### Layer 3: Hooks (Integration)

Hooks are lifecycle interceptors that enforce rules at runtime. They are the glue between the declarative world (rules, skills) and the executable world (libs, externals).

| Property | Value |
|----------|-------|
| Format | Bash scripts (.sh) |
| Location | `hooks/` |
| Dependencies | May source `hooks/_lib/*.sh`; may read rules and config |
| Shared code | `hooks/_lib/common.sh` (require_tool, resolve_session_dir, etc.) |
| Testing | Behavior tests: does the hook fire correctly and produce expected side effects? |
| Count | 94 scripts; 46 registered in `.claude/settings.json` |

**Design constraints:**
- Hooks are thin wrappers. They detect conditions and trigger actions, but complex logic belongs in `lib/`.
- Hooks read `cognitive-os.yaml` for thresholds and parameters.
- Hooks write to `metrics/*.jsonl` for observability.
- Hooks exit with specific codes: 0 (pass), 2 (block), other (error).

**Antipattern: Hook-with-business-logic.** When a hook exceeds ~100 lines, it likely contains logic that should live in `lib/`. The hook should call the lib function, not reimplement it.

**Example:** `hooks/trust-score-validator.sh` extracts Trust Report scores from agent output and logs them to `metrics/trust-scores.jsonl`. The scoring formula is defined in `rules/trust-score.md`; the hook just extracts and records.

### Layer 4: Libs (Infrastructure)

Libs are runtime Python modules that provide programmatic capabilities. They are the workhorses that hooks and the orchestrator call to execute complex operations.

| Property | Value |
|----------|-------|
| Format | Python (.py) |
| Location | `lib/` |
| Dependencies | Standard library + approved external packages |
| Testing | Unit tests: pure function testing |
| Count | 22 modules |

**Design constraints:**
- Libs receive parameters, they do not parse markdown rules.
- Libs are replaceable: swapping `lib/agent_bus.py` from Valkey to a different pub/sub should not require changing any rule or skill.
- Libs should be stdlib-only where possible. External dependencies (FastAPI, valkey) are used only when necessary.

**Antipattern: Lib-reading-rules.** A lib that opens and parses `rules/*.md` to extract a threshold. Fix: the threshold should come from `cognitive-os.yaml` or be passed as a function parameter.

**Example:** `lib/claude_executor.py` wraps the Claude CLI subprocess. It knows nothing about trust scores, acceptance criteria, or SDD phases. It just runs commands and returns results.

### Layer 5: Externals (Services)

Externals are services that the system depends on but does not own. They are accessed through adapters in Layer 4.

| Property | Value |
|----------|-------|
| Format | Docker Compose, API configs, MCP servers |
| Location | `docker-compose.cognitive-os.yml`, `infra/` |
| Dependencies | External services (Valkey, PostgreSQL, ClickHouse, etc.) |
| Testing | Integration tests with testcontainers |
| Count | 18 Docker services across 4 profiles |

**Design constraints:**
- Every external is accessed through an adapter in `lib/`. No hook or skill calls an external directly.
- Externals are optional. The system degrades gracefully when services are unavailable (e.g., Agent Bus falls back to file-based signaling).
- Profile-based activation: services are grouped by purpose (default, memory, observability, ui, automation).

**Antipattern: Tight-coupling to externals.** A hook that directly calls `valkey-cli` instead of going through `lib/agent_bus.py`. Fix: use the lib adapter, which handles connection failures and fallbacks.

**Example:** Langfuse (observability), Valkey (pub/sub), Cognee (knowledge graph) are all accessed through dedicated client modules in `lib/`.

---

## Cross-Cutting Concerns

Some concerns span multiple layers. They are handled by establishing clear read/write boundaries.

### Configuration (cognitive-os.yaml)

The single source of truth for all runtime parameters.

| Layer | Interaction |
|-------|-------------|
| Rules | May reference config sections conceptually ("read from cognitive-os.yaml") |
| Skills | May instruct agents to read config |
| Hooks | Read config values at runtime to determine behavior |
| Libs | Read config values for service URLs, thresholds, limits |
| Config itself | Never modified by hooks or libs at runtime |

### Memory (Engram)

Persistent memory across sessions via SQLite (MCP server).

| Layer | Interaction |
|-------|-------------|
| Rules | Define WHAT to remember (topic key conventions, organization) |
| Skills | Instruct agents to save/search memory |
| Hooks | Auto-save session summaries, error patterns |
| Libs | Programmatic access for automation pipelines |

Pattern: rules define the schema, skills tell agents what to save, hooks enforce when to save, libs provide the API.

### Metrics (.cognitive-os/metrics/*.jsonl)

Append-only observation logs in JSONL format.

| Layer | Interaction |
|-------|-------------|
| Rules | Define what metrics matter (KPI targets, thresholds) |
| Skills | Read metrics for reporting (KPI dashboards, trend analysis) |
| Hooks | Write metrics entries after each tool use |
| Libs | Read metrics for analysis (singularity, self-improvement) |

Pattern: hooks write, skills and libs read. Rules define what is measured. No agentic primitive writes metrics upstream of its layer.

### Testing

Each layer has its own test category, matching the nature of what is being verified.

| Layer | Test Type | What It Verifies |
|-------|-----------|------------------|
| Rules | Behavior tests | Does the system follow the rule? |
| Skills | Behavior tests | Does the skill produce correct output structure? |
| Hooks | Behavior tests | Does the hook fire on the right trigger and produce expected side effects? |
| Libs | Unit tests | Does the function return correct values for given inputs? |
| Externals | Integration tests | Does the system work with real services (testcontainers)? |

---

## The Replaceability Principle

Each layer should be replaceable without affecting inner layers. This is the key benefit of strict dependency direction.

| Replace this... | Without affecting... | What changes |
|-----------------|----------------------|--------------|
| Claude API with OpenAI API | Rules, Skills, Hooks | Only `lib/claude_executor.py` and `lib/model_router.py` |
| Valkey with Redis or NATS | Rules, Skills | Only `lib/agent_bus.py` |
| Bash hooks with Python hooks | Rules, Skills | Hook interface stays the same; scripts change language |
| Engram with a different memory system | Rules | Skills reference memory conceptually; lib adapter changes |
| Docker with Kubernetes | Rules, Skills, Hooks | Only externals layer and some lib adapters |
| JSONL metrics with a time-series DB | Rules, Skills | Only hooks (write path) and libs (read path) |

The further inward the layer, the more stable it is. Rules almost never change. Externals change frequently.

---

## Anti-Patterns (With Real Examples)

### 1. Rule-as-documentation

**Symptom:** `rules/closed-loop-prompts.md` is 270 lines. It mixes the rule (what agents must do), documentation (how the system works), philosophy (why this matters), and configuration examples.

**Fix:** The rule itself should be ~60 lines: the behavioral constraint plus severity tiers. The rest moves to `docs/closed-loop-prompts.md` as reference documentation.

**Test:** If removing a section from a rule does not change agent behavior, that section is documentation, not a rule.

### 2. Hook-with-business-logic

**Symptom:** A hook that contains classification logic, registry lookups, and multi-step repair execution in a single bash script exceeding 200 lines.

**Fix:** Move the logic to a `lib/*.py` module. The hook becomes a thin caller: detect the condition, invoke the lib function, log the result.

**Test:** If a hook needs unit tests for its internal logic, that logic belongs in a lib.

### 3. Skill-calling-code

**Symptom:** A skill that contains executable Python functions or bash scripts as its core implementation rather than as illustrative examples for the agent.

**Fix:** Skills are instructions for the LLM. If computation is needed, the skill instructs the agent to use a tool (Bash, Python REPL). The skill itself is always markdown.

**Test:** If removing the code blocks makes the skill non-functional (as opposed to less illustrative), the code is misplaced.

### 4. Lib-reading-rules

**Symptom:** A Python module that opens `rules/trust-score.md` and parses it to extract the scoring formula.

**Fix:** The scoring parameters should come from `cognitive-os.yaml` or be passed as function arguments. The rule defines intent; the lib should not need to parse prose.

**Test:** If a lib has `open("rules/...")` in its source, it is violating the dependency rule.

### 5. Config-as-code

**Symptom:** `cognitive-os.yaml` containing conditional logic: "if phase is reconstruction, then rewrite; else patch."

**Fix:** Config declares WHAT (phase: reconstruction). Hooks and skills implement the conditional behavior based on the config value.

**Test:** If a config value reads like an if/else statement, the logic belongs in a hook.

---

## Comparison with Traditional Clean Architecture

| Principle | Clean Architecture (Uncle Bob) | Agent OS Architecture |
|-----------|-------------------------------|----------------------|
| Dependency rule | Inner layers do not know about outer | Rules do not know about hooks or libs |
| Entity independence | Entities have no framework deps | Rules are pure markdown, no code deps |
| Use case isolation | Use cases orchestrate entities | Skills orchestrate rules for the agent |
| Interface adapters | Translate between use cases and external | Hooks translate between rules and runtime |
| Frameworks are details | DB, web framework are replaceable | LLM provider, Docker services are replaceable |
| Testability | Each layer testable independently | Rules (behavior), Skills (behavior), Hooks (behavior), Libs (unit), Externals (integration) |
| Separation of concerns | Business logic vs infrastructure | Agent intent vs execution mechanism |

### Key Differences

1. **Rules are prose, not code.** In traditional Clean Architecture, entities are classes or structs. In Agent OS Architecture, the innermost layer is natural language markdown consumed directly by the LLM.

2. **Skills are instructions, not use cases.** Use cases in Clean Architecture contain executable logic. Skills in Agent OS are procedural instructions that the LLM interprets and executes using tools.

3. **The LLM is the runtime.** In traditional architectures, the runtime is a programming language VM. Here, the LLM itself is the execution engine that reads skills and follows rules.

4. **Progressive loading replaces dependency injection.** Instead of injecting implementations at startup, rules and skills are loaded progressively based on context (3-level loading: catalog, full skill, references).

---

## Architectural Decision Records

### ADR-1: Rules are Markdown, Not Code

**Context:** Rules govern agent behavior. They must be consumable by any LLM model.

**Decision:** Rules are written in plain Markdown with no executable code.

**Rationale:**
- Portable: works with any LLM that reads text (Claude, GPT, Gemini, local models)
- Human-readable: developers can read and review rules without tooling
- Version-controlled: standard git diffs show exactly what changed
- Model-agnostic: no coupling to a specific API or SDK

**Consequences:** Rules cannot enforce themselves. Hooks (Layer 3) are needed to implement enforcement.

### ADR-2: Hooks are Bash, Not Python

**Context:** Claude Code hooks must be shell scripts. Even without this constraint, hooks should be lightweight.

**Decision:** Hooks are written in Bash, with shared utilities in `hooks/_lib/`.

**Rationale:**
- Fast startup: <100ms per hook invocation (no interpreter warm-up)
- Zero dependencies: runs on any POSIX system
- Universal: every CI/CD environment, container, and developer machine has bash
- Constrained: bash's limitations naturally keep hooks thin (complex logic moves to libs)

**Consequences:** Complex logic must be delegated to `lib/*.py`. Hooks call Python scripts when needed.

### ADR-3: Libs are Python

**Context:** The system needs runtime capabilities: HTTP servers, testing frameworks, data processing.

**Decision:** Library modules are written in Python 3.9+ with stdlib-only preference.

**Rationale:**
- Rich ecosystem: pytest, testcontainers, FastAPI, JSON processing
- Available everywhere: Python is pre-installed on most systems
- Stdlib-only core: core modules avoid pip dependencies for portability
- Async support: needed for webhook server and agent bus

**Consequences:** External dependencies (FastAPI, valkey) are isolated to specific modules. Core libs use only stdlib.

### ADR-4: CLI Tools are Go

**Context:** The `cos-test` TUI needs fast startup and cross-platform distribution.

**Decision:** CLI tools are written in Go.

**Rationale:**
- Single binary: no runtime needed, no dependency management
- Fast startup: sub-millisecond launch time
- Cross-platform: compiles for macOS, Linux, Windows from one source
- TUI ecosystem: Cobra (CLI) and Bubbletea (TUI) are mature

**Consequences:** Go is only used for user-facing CLI tools. Internal automation uses Python.

### ADR-5: Externals Use Docker Compose

**Context:** The system integrates 18 optional services (Langfuse, Valkey, Cognee, etc.).

**Decision:** External services are defined in `docker-compose.cognitive-os.yml` with profile-based activation.

**Rationale:**
- Reproducible: same environment everywhere
- Optional: profiles allow running only needed services
- Isolated: each service runs in its own container
- Replaceable: swapping a service means changing one container definition

**Consequences:** Docker must be available for full functionality. The system degrades gracefully without it (hooks detect missing Docker and skip infrastructure checks).

---

## Layer Migration Guide

When an agentic primitive is in the wrong layer, follow this process:

### Step 1: Identify the Antipattern

| Symptom | Likely Issue |
|---------|-------------|
| Rule file > 60 lines | Rule mixing intent with documentation |
| Hook file > 100 lines | Hook containing business logic |
| Skill with executable code as implementation | Skill doing lib's job |
| Lib parsing rules/*.md | Lib violating dependency direction |
| Config with conditional logic | Config doing hook's job |

### Step 2: Extract to the Correct Layer

1. **Rule -> Rule + Docs:** Keep the behavioral constraint in the rule. Move explanations, examples, and rationale to `docs/`.

2. **Hook -> Hook + Lib:** Extract the logic into a `lib/*.py` function. The hook calls the function, checks the return value, and logs the result.

3. **Skill -> Skill + Tool instruction:** Replace executable code with instructions for the agent to use tools. "Run `python lib/analyze.py`" instead of embedding the analysis code.

4. **Lib -> Lib + Config:** Replace `open("rules/...")` with reading from `cognitive-os.yaml` or function parameters.

### Step 3: Update Tests

- If logic moved from hook to lib: add unit tests for the lib function
- If rule was split: verify behavior tests still pass
- If skill was refactored: verify skill structure tests pass

### Step 4: Verify

Run `tests/behavior/test_architecture_principles.py` to verify:
- No layer violations were introduced
- Dependency direction is maintained
- File sizes are within bounds

---

## Progressive Loading and Layer Budgets

The 5-layer architecture works with the progressive loading system to minimize context window usage.

### Loading Strategy by Layer

| Layer | Loading Strategy | Token Budget |
|-------|-----------------|--------------|
| Rules | RULES-COMPACT.md always loaded (~1,500 tokens); full rules on contextual trigger | ~1,500 base + ~500 per triggered rule |
| Skills | CATALOG.md at session start (~2,000 tokens); full SKILL.md on demand | ~2,000 base + ~1-3K per active skill |
| Hooks | Never loaded into context (they run externally) | 0 tokens |
| Libs | Never loaded into context (they run externally) | 0 tokens |
| Externals | Never loaded into context | 0 tokens |

Only Layers 1 and 2 consume context window tokens. Layers 3-5 execute outside the LLM context, which is a key architectural advantage: the system can have 57 hooks and 22 lib modules without consuming any context tokens.

### Max Active Skills

At most 5 skills should be loaded simultaneously (Level 2). When a sixth skill is needed, the least recently used skill is conceptually unloaded. This prevents context bloat while maintaining capability.

---

## Summary

The 5-layer architecture provides:

1. **Stability gradient:** Inner layers change rarely; outer layers change often. Rules are stable for months. External service versions change weekly.

2. **Testability:** Each layer has its own test strategy matched to what it does. No layer requires testing infrastructure from another layer.

3. **Replaceability:** Any external service, any lib module, any hook implementation can be swapped without affecting the layers above it.

4. **Token efficiency:** Only Layers 1 and 2 consume context tokens. The system scales to 57 hooks and 22 libs without increasing LLM costs.

5. **Model independence:** Rules and skills are plain text. They work with any LLM that can read markdown, making the entire inner core model-agnostic.

The dependency rule is the single most important principle. Every architectural decision flows from it: if dependencies only point inward, then inner layers are stable, testable, and replaceable. Violate this rule, and the benefits collapse.

---

## System Knowledge Graph

> "If you don't understand the whole system, you make bad decisions." -- James Gosling

The System Knowledge Graph maps every agentic primitive in Cognitive OS and their relationships across all 5 layers. It answers the question agents need before modifying anything: "What else will break if I change this?"

### Why It Exists

Agents modify agentic primitives in isolation. A hook change might silently break a rule's enforcement. A lib refactor might orphan a metrics file that three skills depend on. The knowledge graph makes these invisible dependencies visible.

### How to Use

The `cos map` CLI command provides several views into the graph:

```bash
# Show dependency tree for one agentic primitive
cos map trust-score

# Show what breaks if a file changes
cos map --affected hooks/trust-score-validator.sh

# Full system summary (agentic primitive counts, cross-layer edges, orphans)
cos map --full

# Show disconnected agentic primitives (no edges — potential dead code)
cos map --orphans

# Show most-connected agentic primitives (highest modification risk)
cos map --hotspots

# Export as JSON for visualization tools
cos map --json
```

### Example: Dependency Tree

```
trust-score (Layer 1 -- RULES)
+-- ENFORCED BY: trust-score-validator (Layer 3)
|   +-- WRITES TO: metrics/trust-scores.jsonl
+-- ENFORCED BY: confidence-gate (Layer 3)
+-- REFERENCED BY: sdd-verify (Layer 2)
+-- COMPACTED IN: RULES-COMPACT.md
+-- SYMLINKED: .claude/rules/cos/trust-score.md

IMPACT: 6 agentic primitives across 3 layers
RISK: HIGH
```

### Relation Types

| Relation | Meaning | Example |
|----------|---------|---------|
| ENFORCES | Hook implements a rule's constraint | `trust-score-validator.sh` enforces `trust-score` |
| REFERENCES | Skill mentions a rule or another skill | `sdd-verify` references `trust-score` |
| WRITES_TO | Hook/lib writes to a metrics file | `error-pipeline.sh` writes to `error-learning.jsonl` |
| READS_FROM | Hook/lib reads a metrics file | `error-pattern-detector.sh` reads `error-learning.jsonl` |
| SOURCES | Hook sources a shared lib script | `trust-score-validator.sh` sources `_lib/common.sh` |
| IMPORTS | Python lib imports another lib | `agent_dashboard.py` imports `agent_bus` |
| REGISTERED | Hook is registered in settings.json | `trust-score-validator.sh` registered as PostToolUse |
| CATALOGED | Skill is listed in CATALOG.md | `sdd-verify` cataloged in CATALOG.md |
| COMPACTED | Rule is referenced in RULES-COMPACT.md | `trust-score` compacted in RULES-COMPACT.md |
| SYMLINKED | Rule is symlinked into .claude/rules/ | `trust-score.md` symlinked to `.claude/rules/cos/` |

### Risk Classification

| Level | Dependents | Action |
|-------|-----------|--------|
| LOW | 0-2 | Modify freely |
| MEDIUM | 3-5 | Review affected agentic primitives |
| HIGH | 6-10 | Run `cos map` first, review carefully |
| CRITICAL | 10+ or 3+ layers | Full impact analysis required |

### Integration with Existing Tools

The knowledge graph complements two existing tools:

- **Blast Radius** (`rules/blast-radius.md`): estimates impact from prompt text before an agent launches. The graph provides the actual dependency data.
- **Impact Analysis** (`lib/impact_analysis.py`): analyzes changed source code files (imports, tests, Docker services). The graph analyzes Cognitive OS agentic primitives (rules, skills, hooks, libs).

### The Rule

Before modifying an agentic primitive with >5 dependents, run `cos map <primitive>` first. This is enforced by convention, not by a hook -- the graph itself is a diagnostic tool, not a gate.

### Implementation

- **Python library**: `lib/system_graph.py` -- builds and queries the graph
- **Go CLI**: `cmd/cos/internal/cli/map.go` -- user-facing `cos map` command
- **Tests**: `tests/unit/test_system_graph.py` -- 20+ unit tests

# Prompt-Driven Governance

## ADR-012 (docs/adrs/ADR-012-prompt-driven-governance.md): Move governance hooks from imperative bash to declarative prompt templates

### Status
Proposed

### Context

Cognitive OS has 80+ bash hooks encoding governance behavior imperatively. Five of these hooks — clarification-gate, blast-radius, assumption-tracker, prompt-quality, and completeness-check — perform natural language evaluation using regex and keyword matching. This approach has three structural problems:

1. **Low accuracy**. Regex cannot reason about intent. `clarification-gate.sh` gives +15 points for "no file paths" but cannot distinguish between "implement auth" (genuinely vague) and "follow the approach we discussed" (clear in context). The assumption-tracker flags "I think" everywhere, including legitimate reasoning ("I think this is the correct pattern because...").

2. **Hard to modify**. Changing scoring requires editing bash, understanding grep flags, and testing regex interactions. A non-engineer cannot adjust the clarification threshold or add a new quality dimension without understanding `grep -qiE` syntax.

3. **Brittleness**. Each hook re-implements the same boilerplate: stdin parsing, jq extraction, session-aware metrics directory resolution, private mode check, capability level check. This is 30-40 lines of identical scaffolding per hook before any actual logic begins.

Claude Code now supports `type: prompt` hooks that use Haiku for fast LLM evaluation. This creates an alternative: encode governance logic as natural language prompts that Haiku evaluates, replacing regex with reasoning.

### Decision

Convert governance hooks that perform **natural language judgment** from bash to prompt hooks. Keep hooks that perform **deterministic checks** (file existence, exit codes, string matching) in bash.

### The Pattern: Prompt-Driven Governance

Instead of:

```bash
# hooks/clarification-gate.sh — 180 lines of bash
score=0
echo "$prompt" | grep -qiE '\b(all|every|complete)\b' && score=$((score + 20))
echo "$prompt" | grep -qiE '\b(add auth|improve performance)\b' && score=$((score + 20))
# ... 7 more regex patterns ...
if [ "$score" -gt 60 ]; then exit 2; fi
```

Write:

```json
{
  "type": "prompt",
  "prompt": "templates/prompt-hooks/clarification-gate.md"
}
```

Where the template contains the evaluation criteria in plain English, and Haiku returns structured JSON with a score and reasoning.

## Hook Classification

### Convert to prompt hooks (natural language judgment)

| Hook | Lines | Type | Why convert |
|------|-------|------|-------------|
| `clarification-gate.sh` | 180 | PreToolUse | Ambiguity is contextual; regex misses nuance and false-positives on legitimate patterns. An LLM can distinguish "add auth" (vague) from "add JWT middleware to internal/auth/middleware.go" (clear) without 7 separate regex checks. |
| `assumption-tracker.sh` | 164 | PostToolUse | Assumption detection is semantic. "I think this is correct because the tests pass" is not an assumption. "I think the database is PostgreSQL" is. Regex treats both identically. |
| `prompt-quality.sh` | 161 | PreToolUse | Quality scoring across 5 dimensions (specificity, actionability, context, measurability, scope clarity) is inherently subjective. Each dimension currently uses 2-3 regex patterns that cover a fraction of what the dimension actually means. |
| `scope-creep-detector.sh` | ~100 | PostToolUse | Detecting whether an edit is "within scope" requires understanding the task intent, not just matching file paths against a list. |

### Keep as bash (deterministic logic)

| Hook | Lines | Type | Why keep |
|------|-------|------|----------|
| `blast-radius.sh` | 201 | PreToolUse | File counting, keyword detection, and threshold classification are deterministic. The regex patterns match concrete tokens (docker, jwt, migration) that do not require contextual reasoning. The accuracy ceiling for this task is already near the LLM ceiling. |
| `completeness-check.sh` | 147 | PreToolUse | Simple presence checks ("does the prompt contain 'all files' without listing them?"). Binary signals that regex handles well. |
| `content-policy.sh` | — | PostToolUse | Prohibited term matching is exact string matching. An LLM adds no value over grep for this. |
| `secret-detector.sh` | — | PreToolUse | Pattern matching for API keys, tokens, and credentials is well-defined regex territory. |
| `rate-limiter.sh` | — | PreToolUse | Counter arithmetic. No natural language involved. |
| `auto-checkpoint.sh` | — | PostToolUse | Timestamp comparison and git stash. Pure infrastructure. |
| `error-learning.sh` | — | PostToolUse | Exit code parsing and JSONL logging. Deterministic. |
| `result-truncator.sh` | — | PostToolUse | Character counting and string slicing. |
| `scope-proportionality.sh` | — | PostToolUse | File count comparison against thresholds. |

### Maybe convert (marginal benefit)

| Hook | Lines | Why maybe |
|------|-------|-----------|
| `blast-radius.sh` | 201 | The keyword lists work well, but an LLM could catch implicit infrastructure impact ("set up the database" without using the word "migration"). Marginal accuracy gain does not justify the latency cost. |
| `completeness-check.sh` | 147 | The red flag patterns ("all files", "follow patterns") are simple enough for regex, but an LLM could detect subtler incompleteness. Low priority. |

## Cost Analysis

### Per-call cost

| Model | Input tokens | Output tokens | Cost per call |
|-------|-------------|---------------|---------------|
| Haiku 3.5 | ~800 (prompt template + agent prompt excerpt) | ~200 (JSON response) | ~$0.00045 |

Breakdown: 800 input tokens at $0.25/1M = $0.0002, 200 output tokens at $1.25/1M = $0.00025.

### Per-session cost

| Scenario | Prompt hook calls | Session cost |
|----------|------------------|--------------|
| Light session (5 agent launches) | 10 (2 hooks x 5 launches) | ~$0.0045 |
| Normal session (15 agent launches) | 30 (2 hooks x 15 launches) | ~$0.014 |
| Heavy session (30 agent launches) | 60 (2 hooks x 30 launches) | ~$0.027 |

### Cost comparison

| Approach | Session cost (normal) | Annual cost (daily use) |
|----------|----------------------|------------------------|
| Bash hooks | $0.00 | $0.00 |
| Prompt hooks (4 converted) | ~$0.014 | ~$5.11 |
| Full governance suite (all hooks) | ~$0.03 | ~$10.95 |

The annual cost of prompt-driven governance is under $11 — roughly the cost of one opus call. This is negligible relative to the agent execution costs that the governance system protects against (a single bad agent launch from a vague prompt costs $0.50-$2.00 in wasted tokens).

### Latency comparison

| Approach | Latency per hook | Impact on agent launch |
|----------|-----------------|----------------------|
| Bash hook | 50-200ms | Imperceptible |
| Prompt hook (Haiku) | 1-2s | Noticeable but acceptable |
| Two prompt hooks chained | 2-4s | Borderline; may need parallelization |

**Mitigation**: Claude Code runs prompt hooks inline. If two prompt hooks fire on the same PreToolUse event (e.g., clarification-gate + prompt-quality), they execute sequentially, adding 2-4 seconds. Options:

1. **Merge the two PreToolUse prompt hooks into one**. A single prompt template can score both ambiguity and quality, returning both scores in one call. This halves the latency.
2. **Accept the latency**. 2-4 seconds before an agent launch (which itself takes 30-300 seconds) is a 1-5% overhead.
3. **Make the slower hook async**. Prompt-quality is advisory (never blocks), so it could run async and report results after the agent launches.

Recommendation: Option 1 (merge) for PreToolUse hooks, separate prompt for PostToolUse (assumption-tracker) since it runs after completion and does not block anything.

## Trade-off Matrix

| Dimension | Bash hooks | Prompt hooks | Winner |
|-----------|-----------|-------------|--------|
| Latency | 50-200ms | 1-2s | Bash |
| Cost | $0 | ~$0.0005/call | Bash |
| Accuracy (ambiguity detection) | Low — regex misses context | High — LLM reasons about intent | Prompt |
| Accuracy (assumption detection) | Low — false positives on "I think" in reasoning context | High — distinguishes assumption from reasoning | Prompt |
| Accuracy (quality scoring) | Medium — covers common patterns | High — evaluates holistically | Prompt |
| Customizability | Edit bash + regex | Edit English prose | Prompt |
| Debuggability | Read bash (hard) | Read the prompt (easy) | Prompt |
| Offline capability | Works without network | Requires API call | Bash |
| Determinism | Identical results on identical input | May vary slightly between calls | Bash |
| Boilerplate | 30-40 lines per hook | Zero (handled by Claude Code runtime) | Prompt |
| Testability | bash -n + bats | Input/output examples | Tie |

### What you gain

- **Higher accuracy on subjective evaluation**. The clarification gate's 7 regex patterns cover perhaps 60% of ambiguity signals. An LLM covers 90%+ because it reasons about the prompt holistically.
- **Transparency**. A prompt template is readable by anyone who speaks English. The scoring criteria are stated in the template, not encoded in grep flags.
- **Customizability**. Changing the weight of "missing file paths" from +15 to +10 means editing a number in a markdown file, not debugging `grep -qE` interactions.
- **Eliminated boilerplate**. The 30-40 lines of stdin parsing, jq extraction, session awareness, private mode check, and capability level check disappear. Claude Code handles all of that for prompt hooks.

### What you give up

- **Speed**. 1-2 seconds per prompt hook call, versus 50-200ms for bash.
- **Determinism**. Bash regex produces identical output for identical input. An LLM may score the same prompt 72 one time and 68 the next. Mitigation: structured output format with explicit rubric reduces variance.
- **Offline capability**. Bash hooks work without network. Prompt hooks require an API call. Mitigation: if the API call fails, the hook should degrade to "pass" (not block), same as the existing bash hooks when jq is missing.
- **Cost**. Approximately $0.0005 per hook call. Negligible in absolute terms.

## Prompt Template Design

### Directory structure

```
templates/prompt-hooks/
  clarification-gate.md       # PreToolUse — ambiguity scoring
  prompt-quality.md           # PreToolUse — quality scoring (merged with above in Phase 1)
  assumption-tracker.md       # PostToolUse — assumption detection
  scope-creep-detector.md     # PostToolUse — scope violation detection
```

### Template contract

Every prompt hook template MUST:

1. **State the evaluation criteria explicitly** with point values or weights.
2. **Define the output format** as JSON with required fields.
3. **Include the decision threshold** (e.g., "score > 60 = BLOCK").
4. **Include 2-3 examples** of inputs and expected outputs for calibration.
5. **Fit within 500 tokens** to keep per-call costs under $0.0005.

### Example: Clarification Gate prompt template

```markdown
# Clarification Gate

Evaluate this agent prompt for ambiguity. Score 0-100 where higher = more ambiguous.

## Scoring Criteria

- Missing file paths or directories: +15 if the prompt describes a code change but names no specific files
- Unbounded scope: +20 if words like "all", "every", "complete" appear without a count (e.g., "47 endpoints")
- Missing technology: +15 if the prompt says "implement" or "create" without naming a language or framework
- Action without target: +20 if there is an action verb ("add auth", "improve performance") without specifying which files or components
- Open questions: +15 if the prompt contains unresolved questions ("which?", "what type?")
- Very short: +20 if the prompt is under 50 characters
- No acceptance criteria: +10 if there are no verification commands or success conditions

## Output Format

Return ONLY valid JSON:
{"score": <0-100>, "verdict": "<PASS|WARN|BLOCK>", "questions": ["<question 1>", ...]}

Verdicts: score 0-29 = PASS, 30-60 = WARN, 61-100 = BLOCK.

## Examples

Input: "Add auth to the project"
Output: {"score": 70, "verdict": "BLOCK", "questions": ["Which files should be modified?", "Which auth framework (JWT, OAuth, session)?", "What are the acceptance criteria?"]}

Input: "Implement CreateOrder in internal/orders/application/use_cases/create_order.go using the declared framework. Acceptance criteria: go build exits 0, go test ./internal/orders/... exits 0."
Output: {"score": 0, "verdict": "PASS", "questions": []}

## Agent Prompt to Evaluate

{{agent_prompt}}
```

### Example: Assumption Tracker prompt template

```markdown
# Assumption Tracker

Analyze this agent response for assumptions — places where the agent guessed instead of working from verified information.

## What counts as an assumption

- HIGH: Explicit assumption language ("I assume", "I'm assuming", "presumably", "without more info")
- HIGH: Stating facts about the project without evidence ("the database is PostgreSQL", "this uses REST")
- MEDIUM: Hedging language that implies uncertainty ("I think", "probably", "likely", "it seems")
- NOT an assumption: Reasoning from evidence ("I think this is correct because the tests pass", "it seems to work based on the output above")

The key distinction: an assumption fills in MISSING information. Reasoning from PRESENT evidence is not an assumption.

## Output Format

Return ONLY valid JSON:
{"count": <number>, "assumptions": [{"text": "<quote>", "confidence": "<HIGH|MEDIUM>"}], "warn": <true if count >= 3>}

## Agent Response to Analyze

{{agent_response}}
```

## Metrics Continuity

Prompt hooks MUST write to the same JSONL metrics files as their bash predecessors. The orchestrator, KPI system, and dashboards read these files. Changing the file format or location would break downstream consumers.

| Hook | Metrics file | Format preserved |
|------|-------------|-----------------|
| clarification-gate | `clarification-events.jsonl` | `{timestamp, score, questions, verdict, agent}` |
| prompt-quality | `prompt-quality.jsonl` | `{timestamp, score, specificity, actionability, context, measurability, scope_clarity, agent}` |
| assumption-tracker | `assumptions.jsonl` | `{timestamp, assumption_count, agent, assumptions}` |
| scope-creep-detector | `scope-creep.jsonl` | `{timestamp, file, task, phase, action}` |

For prompt hooks, the Claude Code runtime handles stdin/stdout. The prompt template instructs Haiku to return JSON. A thin bash wrapper (or the prompt itself) must write the JSON response to the correct JSONL file.

**Open question**: Does Claude Code's `type: prompt` hook support writing to files, or only returning text to the hook pipeline? If it only returns text, a hybrid approach is needed: the prompt hook evaluates and returns a verdict, and a companion `type: command` hook writes metrics. Alternatively, the prompt template can instruct Haiku to include a metrics payload in its response, and the hook runner writes it.

## Implementation Plan

### Phase 1: Clarification gate + prompt quality (merged)

**Why merged**: Both are PreToolUse hooks on Agent. Running them as separate prompt hooks adds 2-4s latency. A single prompt can evaluate both ambiguity (0-100) and quality (0-100) and return both scores.

1. Create `templates/prompt-hooks/clarification-and-quality.md` with combined scoring rubric
2. Register as `type: prompt` hook in settings.json for PreToolUse on Agent
3. Validate output format: `{"ambiguity_score": N, "quality_score": N, "verdict": "PASS|WARN|BLOCK", "questions": [...], "suggestions": [...]}`
4. Write metrics to both `clarification-events.jsonl` and `prompt-quality.jsonl`
5. Run both bash and prompt versions in parallel for 1 week, compare accuracy
6. If prompt version matches or exceeds bash accuracy: remove bash hooks
7. If prompt version underperforms on specific cases: add examples to template and retry

**Acceptance criteria**:
- `grep -c "BLOCK" clarification-events.jsonl` on test prompts matches or exceeds bash version
- False positive rate on well-formed prompts is zero
- Latency < 2.5 seconds per evaluation
- Metrics format identical to bash version

### Phase 2: Assumption tracker

1. Create `templates/prompt-hooks/assumption-tracker.md`
2. Register as PostToolUse prompt hook on Agent
3. Key improvement: distinguish "I think X because evidence" from "I think X" (no evidence)
4. Parallel run for 1 week against bash version
5. Measure: false positive rate reduction (bash version flags ~30% false positives on "I think" in reasoning context)

### Phase 3: Scope creep detector

1. Create `templates/prompt-hooks/scope-creep-detector.md`
2. Register as PostToolUse prompt hook on Edit|Write
3. Key improvement: understand task intent, not just match file paths
4. Higher latency concern here since Edit/Write is more frequent than Agent — may need async execution

### Phase 4: Evaluation and decision

After 2-4 weeks of parallel operation:
- Compare accuracy metrics between bash and prompt versions
- Measure latency impact on developer experience
- Decide per-hook whether to keep prompt version, revert, or run hybrid
- Document findings in this file

## Hybrid Architecture

Not all hooks need to be pure-prompt or pure-bash. A hybrid approach keeps deterministic checks in bash and delegates judgment calls to prompts:

```
PreToolUse on Agent:
  1. [bash] rate-limiter.sh        — counter arithmetic, BLOCK if exceeded
  2. [bash] blast-radius.sh        — keyword counting, advisory
  3. [prompt] clarification+quality — LLM evaluation, BLOCK if ambiguity > 60
  4. [bash] completeness-check.sh  — simple presence checks, advisory

PostToolUse on Agent:
  1. [bash] error-learning.sh      — exit code parsing
  2. [prompt] assumption-tracker   — semantic analysis, advisory
  3. [bash] trust-score-validator  — regex extraction of TRUST_REPORT header
  4. [bash] consequence-evaluator  — score comparison against thresholds
```

The bash hooks run first (fast, deterministic, zero cost). The prompt hooks run after (slower, smarter, negligible cost). If the bash hooks already BLOCK, the prompt hooks never fire — saving both latency and cost.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Haiku accuracy insufficient for scoring | Low | Medium | Include calibration examples in template. Run parallel with bash version before committing. |
| Latency degrades developer experience | Medium | Medium | Merge PreToolUse prompt hooks. Make advisory hooks async. Accept 1-2s for blocking hooks. |
| Haiku output format inconsistent | Medium | Low | Strict JSON schema in prompt. Fallback to "PASS" on parse error. |
| API outage blocks all agent launches | Low | High | Prompt hooks degrade to "PASS" on API failure, same as bash hooks degrade when jq is missing. |
| Cost creep in heavy sessions | Low | Low | $0.03/session max. Budget cap in cognitive-os.yaml. |
| Non-deterministic scoring confuses users | Medium | Low | Show score AND reasoning in output. Users understand "the LLM scored this 72 because..." better than "regex matched 4 patterns = 70". |

## Consequences

### What becomes easier

- **Modifying governance criteria**: Edit English prose instead of bash regex.
- **Adding new evaluation dimensions**: Write a sentence instead of a grep pattern.
- **Debugging false positives**: The prompt template is the documentation. Read it to understand why a score was assigned.
- **Onboarding new contributors**: "Read the template" versus "understand this bash script".
- **Accuracy on edge cases**: LLM handles context that regex structurally cannot.

### What becomes harder

- **Offline development**: Prompt hooks require API connectivity. Mitigation: degrade to pass.
- **Reproducible testing**: Same input may produce slightly different scores. Mitigation: use score bands (PASS/WARN/BLOCK) not exact numbers for decisions.
- **Cost tracking**: Need to track prompt hook costs separately in cost-events.jsonl.
- **Latency-sensitive workflows**: If a developer launches 30 agents rapidly, 30-60 seconds of cumulative prompt hook overhead is noticeable.

### What stays the same

- **Metrics format**: JSONL files remain identical.
- **Hook registration**: Still in settings.json, just with `type: prompt` instead of `type: command`.
- **Phase-aware behavior**: Prompt templates reference the current phase for decision thresholds.
- **Capability level auto-disable**: Prompt hooks check capability level the same way.
- **Deterministic hooks**: 70% of hooks remain bash. Only the judgment-heavy 30% move to prompts.

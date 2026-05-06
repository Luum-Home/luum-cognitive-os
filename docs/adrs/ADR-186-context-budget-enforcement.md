---
adr: 186
title: Context Budget Enforcement — Activate the ADR-038 Wave 3 Limits
status: proposed
date: 2026-05-05
supersedes: []
superseded_by: null
extends: [ADR-038]
implementation_files:
  - hooks/context-budget-meter.sh             # to create — last-in-chain UserPromptSubmit aggregator
  - hooks/_lib/context_budget_lib.sh          # to create — shared accountant
  - lib/context_budget.py                     # to create — token counter + budget reader
  - tests/contracts/test_context_budget_enforcement.py  # to create
  - tests/unit/test_context_budget.py         # to create
  - .cognitive-os/metrics/context-budget.jsonl # runtime artifact
tier: maintainer
tags: [context-management, observability, governance, postmortem-2026-05-05, ADR-038-wave3]
---

# ADR-186: Context Budget Enforcement — Activate the ADR-038 Wave 3 Limits

## Status

**Proposed.** Filed in response to today's substantial increase in
context-injection paths (ADR-173-bis skill router suggester, ADR-179
rule router suggester, ADR-181 ADR-relevance suggester, ADR-183 cross-
session peer context, ADR-185 audit messages inbox). Each adds
`additionalContext` on UserPromptSubmit. The ADR-038 Wave 2 budget was
declarative; Wave 3 enforcement was promised but not delivered.
Without enforcement, the orchestrator's prompt grows silently.

## Context

ADR-038 Wave 2 declared in `cognitive-os.yaml`:

```yaml
context_budget:
  static_max_tokens:  4000   # preamble + KNOWN TRAPS + WORKING DIR
  turn_max_tokens:    8000   # per tool-use round
  user_max_tokens:   12000   # accumulated user-facing per task
  cache_max_tokens:  32000   # MCP/engram retrievals
```

Wave 3 was meant to enforce these. It never landed.

In the past 8 hours of session work, the following new
`additionalContext` emitters were added or formalized:

| Hook | ADR | Estimated chars on hit | Hit rate (prelim) |
|---|---|---|---|
| `skill-router-prompt-suggest.sh` | 173-bis | 150–300 | ~30 % |
| `rule-router-prompt-suggest.sh` | 179 | 200–500 | ~25 % |
| `adr-relevance-suggest.sh` | 181 | 150–400 | ~15 % |
| `cross-session-peer-context.sh` | 183 (planned) | 200–500 | varies |
| `agent-message-inbox-context.sh` | 185 (planned) | 100–300 | varies |

Worst-case all-fire prompt overhead: ~800–2000 extra chars before the
operator's actual question is consumed. Plus the orchestrator's reply
+ the next turn's reply + accumulating across the session.

The MANDATORY PROJECT RULES preamble injected to every sub-agent has
also grown: KNOWN TRAPS, RELEVANT DISCOVERIES, and rule references
have been edited multiple times this session.

The `subagent-context-injector` is currently the largest single source
of static context per agent launch. We have not measured its current
size precisely.

## Decision

Activate Wave 3 of ADR-038: enforce the context budget at runtime via
two new artifacts and one extension to existing hooks.

### `lib/context_budget.py`

Pure Python, std-lib only.

```python
def count_tokens(text: str, model: str = "claude-sonnet-4.5") -> int: ...
def read_budget(config_path: Path) -> dict: ...
def evaluate(layer: str, used: int) -> tuple[Verdict, float]:
    # returns (PASS | WARN | BLOCK, ratio_used)
```

Token counting uses the simple heuristic `len(text) // 4` for v1. v2
can integrate `tiktoken` or Anthropic's tokenizer when allowed by the
operator (env var `COS_USE_REAL_TOKENIZER=1`).

### `hooks/context-budget-meter.sh`

UserPromptSubmit hook, registered **last in chain** so it sees all
prior `additionalContext` injections. Sums the lengths and writes:

```jsonl
{"ts": "2026-05-05T...Z", "session_id": "...",
 "prompt_chars": 1234, "additional_context_chars": 567,
 "preamble_chars": 3245, "total_chars": 5046,
 "tokens_estimate": 1262, "layer": "static",
 "budget_token_max": 4000, "ratio_used": 0.32, "verdict": "PASS"}
```

Verdict thresholds:

- `PASS` — used ≤ 1.0 × budget.
- `WARN` — used > 1.0 × budget AND ≤ 1.2 × budget. Stderr warning;
  no blocking.
- `BLOCK` — used > 1.5 × budget. Returns non-zero unless
  `COS_ALLOW_CONTEXT_BUDGET_OVERRUN=1` is set.

The 1.0–1.5 band is intentional: most violations should be visible but
not blocking until the operator confirms the budget is calibrated for
real workload.

### Per-hook accountant (extension)

Each hook that emits `additionalContext` calls a shared helper before
emission:

```bash
. hooks/_lib/context_budget_lib.sh

context_budget_emit_or_skip "skill-router-prompt-suggest" "$content"
# - if remaining budget < len(content): emit warning to stderr,
#   skip injection
# - else: emit content + increment counter
```

This makes the **first hooks in the chain authoritative** and starves
later hooks if the budget is already consumed. Operator can re-order
priority via `cognitive-os.yaml`.

### Sub-agent preamble accountant

`hooks/subagent-context-injector.sh` is wrapped to count its emitted
preamble. If the preamble exceeds 4000 tokens (`static_max_tokens`),
emit `WARN` to the agent prelaunch log. If exceeds 1.5×, emit `BLOCK`
unless `COS_ALLOW_AGENT_PREAMBLE_OVERRUN=1`.

## Acceptance Criteria

1. `lib/context_budget.py` exposes the API above. Tests cover token
   estimation accuracy (heuristic mode within 20 % of `tiktoken` for
   English text), threshold evaluation, and budget reading from
   `cognitive-os.yaml`.

2. `hooks/context-budget-meter.sh` registered as the LAST hook in the
   UserPromptSubmit chain in `scripts/_lib/settings-driver-claude-code.sh`.

3. `hooks/_lib/context_budget_lib.sh` available; called by:
   - `skill-router-prompt-suggest.sh`
   - `rule-router-prompt-suggest.sh`
   - `adr-relevance-suggest.sh`
   - `cross-session-peer-context.sh` (when implemented per ADR-183)
   - `agent-message-inbox-context.sh` (when implemented per ADR-185)

4. Sub-agent preamble (`subagent-context-injector.sh`) counts its
   output and logs to `.cognitive-os/metrics/context-budget.jsonl`
   under `layer=static`.

5. `tests/contracts/test_context_budget_enforcement.py` verifies:
   - Hooks emit when budget allows.
   - Hooks skip when budget exceeded.
   - Threshold transitions PASS → WARN → BLOCK at the documented
     ratios.
   - Override env vars work correctly.

6. `.cognitive-os/metrics/context-budget.jsonl` accumulates one entry
   per UserPromptSubmit with the full breakdown.

7. NO new pip dependency. v1 uses `len(text) // 4` heuristic.
   `tiktoken` is opt-in via env var.

## Border Cases

- **Operator wants verbose suggestions for a particular prompt**: env
  var `COS_ALLOW_CONTEXT_BUDGET_OVERRUN=1` skips enforcement for that
  invocation; the metric log records the override.
- **A hook produces dynamic content size that depends on data**: the
  hook checks `context_budget_remaining()` before assembling the
  payload; truncates from the bottom if needed.
- **Tokenizer disagreement**: heuristic mode is intentionally
  conservative (counts `len // 4`, which underestimates for code-
  heavy text). Operator who needs precision sets
  `COS_USE_REAL_TOKENIZER=1` after `pip install tiktoken`.
- **Sub-agent preamble exceeds static budget legitimately**: operator
  reviews `subagent-context-injector` output, trims KNOWN TRAPS or
  RELEVANT DISCOVERIES sections, OR raises `static_max_tokens` in
  `cognitive-os.yaml` with rationale.
- **Budget is wrong for a workload type** (e.g. SDD-large benefits
  from larger turn budget): per-skill budget overrides via
  `cognitive-os.yaml > context_budget_overrides.<skill>` mapping.
  Implemented in v2.

## Consequences

### Positive

- The runaway-context risk that today's session created becomes
  observable + bounded.
- Operator gains a quantitative metric per prompt: how many tokens
  did the orchestrator's hooks add?
- Future ADRs that add another `additionalContext` source can be
  tested against the existing budget instead of being measured by
  intuition.
- Wave 2's declarative budget gains real teeth.

### Negative

- Adds ~5–15 ms latency to each UserPromptSubmit (token counting +
  log write).
- Heuristic tokenizer in v1 is approximate; operator may see WARN
  states that real tokenizer would not flag.
- Hook ordering matters more now: a low-priority suggester at the end
  of the chain might be starved while a high-priority one earlier
  consumes budget. Mitigation: documented priority order in
  `cognitive-os.yaml`.

### Neutral

- Does not affect downstream agents; it's a pre-prompt accountant.
- The metric log adds another JSONL but mirrors the existing
  `metrics/` pattern.

## Alternatives Rejected

- **Hard cap with no override**: would block real work when the
  budget is mis-calibrated. Rejected; soft-block via env override is
  safer for v1.
- **Per-hook fixed allowance**: too rigid. Some prompts genuinely
  benefit from one suggester firing fully (e.g. ADR-relevance on a
  doctrinal question). Rejected.
- **Tokenizer always on**: adds runtime dep + ~30 ms per call.
  Rejected for v1; opt-in for operators who care about accuracy.
- **Trim preamble dynamically**: too risky — KNOWN TRAPS are there
  for a reason. Better to surface the warning and let the operator
  decide what to trim.

## Falsifiable Claim

ADR-186 is correct if, in a 30-day audit window after activation:

1. **Visibility**: 100 % of UserPromptSubmit events produce a
   `context-budget.jsonl` entry.
2. **Calibration**: 90 % of entries have `verdict=PASS`. WARN rate
   ≤ 8 %, BLOCK rate ≤ 2 %.
3. **Override usage**: `COS_ALLOW_CONTEXT_BUDGET_OVERRUN=1` is used
   < 5 % of total prompts. Higher rate would indicate the budget is
   miscalibrated rather than the work is truly oversized.
4. **Latency**: 99th percentile meter hook latency < 30 ms.

If (2) is exceeded (lots of WARN/BLOCK in normal work), the budget
needs raising. If (3) is exceeded, same diagnosis. If (4) is
exceeded, the meter implementation needs optimization.

## Cross-References

- **ADR-038** — Wave 2 declared the budget; this ADR is Wave 3
  (enforcement).
- **ADR-173-bis** (skill router observability) — emits
  `additionalContext`; will use the per-hook accountant.
- **ADR-179** (rules auto-derive) — same.
- **ADR-181** (ADR-relevance suggester) — same.
- **ADR-183** (cross-session event log) — same when implemented.
- **ADR-185** (audit messages) — same when implemented.
- **ADR-182** (branch ownership lock) — its hook does NOT emit
  context (only blocks); not affected by ADR-186.
- **ADR-184** (manager-of-managers daemon) — daemon's intent
  protocol is offline; not affected.
- **`.cognitive-os/metrics/context-budget.jsonl`** — new runtime
  artifact.

## Open Questions

- Whether to enforce at sub-agent launch ALSO. If a sub-agent's
  prompt + preamble exceeds the user-layer budget, that's a separate
  signal. Proposed: yes, but as a follow-up. v1 only meters the
  orchestrator's UserPromptSubmit and the agent preamble injector.
- Whether to track accumulated cost across a session and warn on
  long-session drift. Proposed: deferred; covered by Phoenix
  observability if activated (see ADR-058).

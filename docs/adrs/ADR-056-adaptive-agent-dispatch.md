# ADR-056 — Adaptive Agent() dispatch: 3-tier auto-switch Claude → Qwen

- **Status**: L1 IMPLEMENTED (advisory-only). L2/L3 DEFERRED.
- **Date**: 2026-04-21
- **Supersedes / extends**: ADR-049 (LLM gateway & overflow providers),
  ADR-050 (per-skill routing policy, reserved), ADR-051 (Qwen agent loop).
- **Owner**: LLM dispatch coordinator.

## 1. Problem

ADR-049 added an overflow cascade (`scripts/orchestrator.py --providers
qwen,claude`) that routes sub-agent dispatches through Qwen first, preserving
Claude Max subscription quota for the primary user↔Claude Code chat. That
cascade **only applies to code paths that go through `lib/dispatch.py`**.

Native `Agent()` tool invocations emitted by Claude Code itself bypass the
cascade entirely. They count against the same Claude Max bucket as the
primary chat. When the bucket runs dry — as it did today, 2026-04-21 at
18:30 local — the user's session surfaces *"out of extra usage — resets
in Nhrs"* mid-task, and every subsequent native `Agent()` fails with no
fallback.

We cannot, today, intercept native `Agent()` at the dispatch level.
Claude Code does not expose a hook that rewrites the tool call before it
hits the Anthropic API. We can, however:

1. **Observe quota pressure** by reading `llm-dispatch.jsonl` (which
   *does* log rate-limit errors from the cascaded path) and
   `cost-events.jsonl` (which captures per-agent cost estimates).
2. **Advise the orchestrator** via `PreToolUse:Agent` hooks that emit
   `hookSpecificOutput.additionalContext` — the same mechanism
   `hooks/blast-radius.sh` uses for blast-radius warnings.
3. **Opt-in block + rewrite** through progressive levels (L2, L3) once
   the L1 data confirms the heuristic is accurate enough to act on.

Without any intervention, the user discovers the quota failure *post-hoc*
when Claude Code refuses the next `Agent()` tool call. The cost is
user-perceived latency, lost mid-task context, and — in multi-agent
sprints — cascading failures of downstream agents.

## 2. Decision

Ship a **three-tier progressive system** for adaptive `Agent()` dispatch.
Each tier is independently togglable. L1 ships now (advisory-only, always
on). L2 and L3 are documented here but deferred — implementation waits
until L1 telemetry validates the pressure heuristic.

### L1 — Quota Pressure Advisory (advisory-only, always on)

**Shipping: this ADR.**

- **Hook**: `hooks/agent-quota-advisor.sh` (PreToolUse:Agent).
- **Library**: `lib/quota_pressure.py` — pure-Python heuristic.
- **Signals**:
  - Recent rate-limit errors in `llm-dispatch.jsonl` (last 30min window).
  - Session cost accumulated in `cost-events.jsonl` (last 30min) vs
    `daily_alert_usd` from `cognitive-os.yaml`.
- **Pressure score**: weighted blend in `[0.0, 1.0]`. 50/50 between
  rate-limit signal and cost signal. See §4.
- **Thresholds**:
  | Score     | Band     | Behavior |
  |-----------|----------|----------|
  | `< 0.5`   | LOW      | Silent. Normal operation. |
  | `0.5-0.8` | ADVISORY | Emit `additionalContext` recommending `--providers qwen,claude`. |
  | `>= 0.8`  | STRONG   | Advisory upgraded — mentions the `COS_AUTO_REDIRECT_AGENT=1` kill-switch (L2 hint). |
- **Kill-switch**: `COS_DISABLE_AGENT_ADVISOR=1` silences the hook.
- **Never blocks.** Always exits 0. Degrades silently when JSONL files
  are missing, jq is unavailable, or Python can't import `lib.quota_pressure`.

### L2 — Auto-Redirect with Block (opt-in, deferred)

**Deferred. Design only.**

- **Activation**: `COS_AUTO_REDIRECT_AGENT=1` environment variable.
- **Behavior**: PreToolUse:Agent hook returns a `permissionDecision: "deny"`
  with an `additionalContext` telling the orchestrator to use
  `scripts/orchestrator.py --providers qwen,claude` instead. The native
  `Agent()` call is blocked; the orchestrator must retry via the cascade.
- **Trigger conditions** (either):
  - `quota_pressure > 0.7`
  - A rate-limit error was recorded in the last **5 minutes** (tight window
    because at that point the primary chat is already throttled).
- **Trade-off**: breaks the orchestrator flow if the retry path isn't
  wired. Agents launched via native `Agent()` are still useful for
  tool-use parity (Read/Edit/Bash with hooks firing); the Qwen agent loop
  (ADR-051) is not yet at feature parity. L2 assumes the orchestrator
  can fall back *manually* to the cascade — hence the opt-in flag.

### L3 — Transparent Bridge (opt-in per-skill, deferred)

**Deferred. Design only — ADR-050 dependency.**

- **Activation**: per-skill frontmatter in the skill's SKILL.md —
  `routing.auto_fallback_to_qwen: true`. Requires ADR-050 (per-skill
  routing policy) to be implemented first.
- **Behavior**: When `quota_pressure > 0.7` AND the launching skill opts
  in, the PreToolUse:Agent hook **rewrites** the tool call via
  `hookSpecificOutput.updatedInput`. Specifically:
  - Intercepts the `Agent` tool input.
  - Replaces it with a `Bash` invocation of
    `scripts/orchestrator.py --providers qwen,claude --prompt "…"`.
  - The transparent substitution means the orchestrator doesn't need
    fallback logic — the redirect is invisible.
- **Feature loss at L3**: the native `Agent()` tool ships a rich set of
  hooks (blast-radius, reinvention-check, completeness-check, etc.).
  The cascaded path invokes `lib/dispatch.py` directly, which today only
  runs a subset. Skills that opt in to L3 **explicitly accept** losing:
  - `PreToolUse:Agent` chain (blast-radius, reinvention-check, clarification-gate).
  - `PostToolUse:Agent` chain (completion-gate, trust-score-validator,
    audit-id-enricher, auto-rollback-trigger).
  - Native preamble injection.
- Only skills where quota preservation matters more than full governance
  should opt in. Initial candidates: `document-feature`, `skill-creator`,
  `sdd-archive` (already routed to haiku, so governance overhead is low).

## 3. Phase Plan

| Phase | Scope | Gate |
|-------|-------|------|
| **L1** | Advisory-only hook + quota_pressure lib + tests + smoke | **This PR.** |
| **L2** | Opt-in block via `COS_AUTO_REDIRECT_AGENT=1` | Needs: 2 weeks of L1 telemetry confirming the 0.7 threshold catches real quota events before they fail. |
| **L3** | Transparent bridge with per-skill opt-in | Needs: ADR-050 shipped. Initial rollout limited to 3 low-risk skills. |

Escalation between phases is manual and explicit: no auto-promotion.
Each phase is an independent shipping decision.

## 4. Quota Pressure Heuristic (L1 detail)

```
rate_limit_signal = min(1.0, rate_limit_count_last_30min / 2.0)
cost_signal       = min(1.0, cost_usd_last_30min / daily_alert_usd)
pressure          = 0.5 * rate_limit_signal + 0.5 * cost_signal
```

### Rate-limit detection

Matches the same `_RATE_LIMIT_PATTERNS` tuple used in `lib/dispatch.py`
and `hooks/rate-limit-detector.sh`. A dispatch record counts as a signal
when `success: false` AND `error` contains any of:

- `out of extra usage`
- `rate limit exceeded`
- `approximate usage limit`
- `approaching your usage limit`
- `usage limit`
- `429`
- `too many requests`
- `quota exceeded`

Note: this signal is *lagging*. The first rate-limit error only appears
after the quota has already been exhausted. The heuristic cannot predict
exhaustion — it reacts to early errors within the same 30min window.

### Cost signal

Sums `payload.estimated_cost_usd` from `cost-events.jsonl` (and
`cost_usd` from `llm-dispatch.jsonl` as fallback shape) for the last 30
minutes. Normalizes against `resources.budget.daily_alert_usd`
(currently `$10` per `cognitive-os.yaml`). Cost at 100% of daily alert
contributes 0.5 to the pressure score on its own.

### Window

30 minutes. Matches observed Claude Max rate-limit refresh cadence from
ADR-049 telemetry. Configurable via the `window_min` parameter on the
library function (not yet exposed to the hook — add only if tuning proves
necessary).

## 5. Observability

### New metric

- **Location**: currently inline in hook output (emitted as
  `additionalContext` when bands trigger). L2 may add a dedicated
  `quota-pressure.jsonl` file once we need per-invocation history.
- **Schema** (if/when the JSONL is added):
  ```json
  {
    "ts": "2026-04-21T18:30:00Z",
    "pressure": 0.73,
    "band": "ADVISORY",
    "rate_limit_count_30min": 1,
    "cost_usd_30min": 7.85,
    "daily_budget_usd": 10.0
  }
  ```
- **Consumers**: eventual `/llm-status` skill report, ADR-053
  auto-optimizer.

### Existing feeds reused

- `.cognitive-os/metrics/llm-dispatch.jsonl` — source of truth for
  rate-limit error signal.
- `.cognitive-os/metrics/cost-events.jsonl` — source of truth for
  session cost signal.
- `.cognitive-os/metrics/rate-limit-events.jsonl` — already populated by
  `hooks/rate-limit-detector.sh` for post-facto user advisories (separate
  from L1's pre-facto advisory).

## 6. Kill-switches

| Switch | Layer | Effect |
|--------|-------|--------|
| `COS_DISABLE_AGENT_ADVISOR=1` | L1 | Silences advisory hook entirely. |
| Remove `agent-quota-advisor.sh` from `apply-efficiency-profile.sh` | L1 | Hook no longer registered. |
| `COS_AUTO_REDIRECT_AGENT` unset | L2 | L2 never activates (default off). |
| Skill frontmatter `routing.auto_fallback_to_qwen` absent | L3 | L3 never activates for that skill (default off). |

Only literal `"1"` activates positive switches. `"0"`, `"false"`, empty
string do not. Matches ADR-049's kill-switch convention.

## 7. Verification

- **13 unit tests** in `tests/unit/test_agent_quota_advisor.py`:
  - Library math (zero-case, window filtering, escalation with rate-limits,
    escalation with cost, saturation cap, malformed-JSONL tolerance,
    band boundaries).
  - Hook shell behavior (silent at low pressure, advisory at medium,
    strong advisory with L2 hint at high, kill-switch silences,
    non-Agent tools ignored, missing metrics tolerated).
- **Smoke script**: `scripts/smoke-agent-quota-advisor.sh` — 4-check
  live verification (silence-on-empty, advisory-at-0.5, strong-at-1.0,
  kill-switch).
- **Registration check**: `apply-efficiency-profile.sh` sanity loop now
  includes `agent-quota-advisor.sh`. A missing registration warns.

## 8. Related ADRs

- **ADR-049** — LLM gateway & overflow providers. Parent policy. This ADR
  is the *missing* enforcement layer for native `Agent()` calls, which
  ADR-049 explicitly marked out of scope.
- **ADR-050** — Per-skill routing policy (reserved). L3 blocked on this.
- **ADR-051** — Qwen agent loop. Tool-use parity for cascaded path.
  L2/L3 usefulness scales with ADR-051's feature completeness.
- **ADR-052** — Provider benchmark harness (reserved). Future use: feed
  pressure-band outcomes into the harness to tune thresholds.
- **ADR-053** — Dispatch auto-optimizer (reserved). Will eventually
  self-tune the 0.5 / 0.8 thresholds from observed false-positive /
  false-negative rates.

## 9. Open Questions

1. **Native `Agent()` quota state is unobservable pre-call.** We only
   learn about exhaustion from an error *after* the call fails. L1 is
   a lagging indicator by construction. Best-effort is all we can do
   without Claude Code exposing a quota-inspection API. Noted as a
   known limitation.

2. **False positives under burst load.** The 30min window means a brief
   burst of 2 rate-limit errors (e.g. a single failing batch) continues
   to trigger the advisory for 30min after recovery. Acceptable for L1
   (advisory only). L2 will need a decay function or a shorter window
   (5min — see §L2) to avoid over-blocking.

3. **Cost attribution.** `cost-events.jsonl` mixes real and estimated
   costs. Estimated costs are inflated (`is_estimate: true`). L1 treats
   them identically. If this biases the cost signal significantly, add
   a filter in `lib/quota_pressure.py::_sum_recent_cost` to weight
   estimates at 0.5×.

4. **Cross-project contamination.** The JSONL files are per-project. A
   user running two Claude Code sessions on different projects burns the
   *same* Claude Max quota but each project sees only its own signals.
   L1 under-reports. No fix at L1. L2 could query a shared session-wide
   state file at `~/.cognitive-os/shared/quota-pressure.jsonl` — not yet
   built.

5. **Interaction with `hooks/rate-limit-detector.sh`.** That hook fires
   PostToolUse and writes to `rate-limit-events.jsonl`. Consider whether
   L1 should read that file *too* (earlier detection, bypass the
   cascade-only `llm-dispatch.jsonl` filter). Deferred to the first L1
   tuning pass.

6. **Schema additionalContext availability.** Confirmed present in
   `PreToolUse:Agent` — `hooks/blast-radius.sh` uses the same pattern
   and has been in production for two months. No alternative needed.

## 10. Decision Record

- **Accepted**: L1 advisory-only.
- **Deferred with design**: L2 (opt-in auto-redirect), L3 (transparent
  bridge, gated on ADR-050).
- **Rejected alternatives**:
  - *Modify `lib/dispatch.py` to wrap native `Agent()`* — impossible;
    native calls bypass `lib/dispatch.py` by design.
  - *Hard-block `Agent()` on any rate-limit error* — too aggressive;
    false positives from transient API errors would kill productive
    sessions.
  - *Pre-check quota via Anthropic usage API* — no such API exposed to
    Claude Code subscribers today.

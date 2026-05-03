# Boring Reliability Control Plane Audit — 2026-05-03

**Auditor:** Claude Sonnet 4.6 (read-only + execution audit, no code changes)
**Date:** 2026-05-03
**Repo:** luum-cognitive-os (main branch)
**Reference doc:** `docs/architecture/boring-reliability-control-plane.md`
**Trigger:** Follow-up to the 2026-05-02 DX assessment
(`docs/reports/dx-assessment-2026-05-02.md`). The boring-reliability commits
(`b04efb67`, `fe43587d`, `e0a3d400`) introduced 10 operator tools claiming to
address several findings from the assessment. This report verifies each tool
end-to-end so future sessions can measure progress against a real baseline,
not against the existence of files.

---

## Summary Table

| # | Tool | Binary exists | `--help` works | Real invocation | Signal verified | Status |
|---|------|---------------|----------------|-----------------|-----------------|--------|
| 1 | `cos-adoption-profile` | yes (153b wrapper → `cos_adoption_profile.py`) | yes (argparse) | exit 0, valid JSON | counts present: 8 primitives, 7 blocking, 8 default-visible, 1 advisory | **REAL** |
| 2 | `cos-preamble-budget` | yes (152b wrapper → `cos_preamble_budget.py`) | yes (argparse) | exit 0, valid JSON | estimated 800 tokens vs 3000 budget; file breakdown + primitive estimate present | **REAL** |
| 3 | `cos-default-visible-reducer` | yes (160b wrapper → `cos_default_visible_reducer.py`) | yes (argparse) | exit 0, valid JSON | 1 recommendation (`destructive-rm-blocker.sh` → `lab`); status = warn | **REAL** |
| 4 | `cos-false-positive-ledger` | yes (158b wrapper → `cos_false_positive_ledger.py`) | yes (argparse) | exit 0, valid JSON | scanned 118,892 events in 114 files, 1,035 events flagged — but signal is INFLATED (see Findings) | **WORKS** |
| 5 | `cos-wip-safety-score` | yes (153b wrapper → `cos_wip_safety_score.py`) | yes (argparse) | exit 0, valid JSON | score 92/100, 1 snapshot marker, 0 stashes, 0 dirty paths | **REAL** |
| 6 | `cos-recovery-drill` | yes (151b wrapper → `cos_recovery_drill.py`) | yes (argparse) | exit 0, valid JSON | 3/3 scenarios pass: stash-reapply (5 tests), snapshot-restore (9 tests), wip-score | **REAL** |
| 7 | `cos-runtime-hook-reality` | yes (153b wrapper → `runtime_hook_reality.py`, 13.7KB) | yes (argparse) | exit 0, valid JSON; 0 findings | audited 116 hooks: 29 real_blocking, 59 real_advisory, 28 observe_only, 0 undocumented, 0 missing | **REAL** |
| 8 | `cos-silent-failure-audit` | yes (155b wrapper → `silent_failure_audit.py`, 11.2KB) | yes (argparse) | exit 0 (text mode); JSON mode also works | 201 files, 1,580 occurrences, 0 fail, 0 warn; 65 legacy_audited entries | **REAL** |
| 9 | `cos-dispatch-smoke` | yes (153b wrapper → `cos_dispatch_smoke.py`) | yes (argparse) | exit 0, valid JSON | populates `llm-dispatch.jsonl` (2,310b) and `task-history.jsonl` (1,396b); provider = `offline_dispatch_smoke` | **REAL** |
| 10 | `cos-boring-reliability` | yes (155b wrapper → `cos_boring_reliability.py`, 4.3KB) | yes (argparse) | exit 1 (overall = fail), valid JSON dashboard | aggregates all 9 sub-tools; readiness shows 1 fail (`repo-hygiene`: orphan snapshot marker) | **REAL** (exit 1 is honest, not a bug) |

**Status legend:**

- **REAL** — runs, produces meaningful signal, fails when it should.
- **WORKS** — runs and emits non-zero data, but the signal is trivial or distorted.
- **SKELETON** — exists but produces no useful output.
- **BROKEN** — fails to run or crashes.

8/10 REAL, 1/10 WORKS, 0/10 SKELETON, 0/10 BROKEN.

---

## Findings

### Tool 4 — `cos-false-positive-ledger`: inflated FP count (signal noisy)

- **Status:** WORKS — runs and produces real counts, but the metric is misleading.
- **Issue:** The tool does a substring match for the literal string `"bypass"`
  across all JSONL event text. The 851 events attributed to `so-vitals` and 164
  to `aci-observations` match because those events contain the filename
  `"adaptive-bypass.jsonl"` in their event payloads — not because an actual
  hook bypass occurred.
- **Impact:** The 1,035 reported "false positive events" are largely
  false-positives *about* false-positives. The real bypass/FP rate for hooks
  is obscured. `adaptive-bypass.jsonl` itself is 0 bytes (no actual bypasses
  recorded in the file the tool is supposed to be a proxy for).
- **Root cause:** `scripts/cos_false_positive_ledger.py` line 45 serializes
  the entire event payload to JSON and checks if any of
  `("false_positive", "bypass", "overrode", "operator_bypass")` appears
  anywhere in that text. A file *named* `adaptive-bypass.jsonl` listed in a
  so-vitals heartbeat fires the match on every heartbeat tick.
- **Recommendation:** match only on top-level event keys or a scoped
  `event_type` / `bypass_kind` field; alternatively exclude filename strings
  from the match surface.

### Tool 10 — `cos-boring-reliability`: overall exits 1 (expected for current state)

- **Status:** REAL. The exit 1 is correct, not a defect.
- **Issue:** The dashboard reports `status: fail` because `readiness.status =
  fail`. The readiness failure is `repo-hygiene`: one orphaned pre-agent
  snapshot marker exists at
  `.cognitive-os/runtime/pre-agent-snapshot-toolu_01XwryayB4512AotgHSky3V1.json`.
- **Impact:** This is honest signaling — the dashboard is doing its job. To
  flip the aggregator to exit 0, clear the orphan snapshot marker.

### Tool 3 — `cos-default-visible-reducer`: `destructive-rm-blocker.sh` flagged

- **Status:** REAL — also a valid signal worth a policy decision.
- **Note:** `hooks/destructive-rm-blocker.sh` lives in `core` distribution but
  is classified `advisory` in maturity, and is not in the hardcoded
  `CORE_KEEP` set. The reducer correctly proposes demotion to `lab`.
  Acting on this is a maintainer policy call, not a code defect.

### Tool 2 — `cos-preamble-budget`: core preamble estimate is optimistic

- **Status:** REAL — but the value is partial.
- **Note:** The `core` profile resolves only one preamble file
  (`docs/architecture/core-adoption-preamble.md`, 823 bytes / ~205 tokens).
  `AGENTS.md` is not included in the `core` profile's `PROFILE_RULE_FILES`.
  The 800-token estimate therefore omits anything Claude Code loads from
  `AGENTS.md` at session start. If the budget is meant to reflect the full
  context tax (which is the operator-relevant number), `AGENTS.md` should be
  added to the `core` profile inputs.

---

## Baseline Values (2026-05-03)

These are the numbers the tools emit on the current `main`. Future sessions
can re-run the same tools and compare to track movement.

| Metric | Value |
|--------|-------|
| Core primitives | 8 |
| Core hooks | 8 |
| Core blocking count | 7 (at SLO budget of 7) |
| Core default-visible count | 8 (budget: 10) |
| Core advisory count | 1 |
| Preamble estimated tokens (core) | 800 / 3,000 |
| Default-visible reducer recommendations | 1 |
| Hooks audited by runtime-hook-reality | 116 |
| `real_blocking` | 29 |
| `real_advisory` | 59 |
| `observe_only` | 28 |
| `documented_but_not_projected` | 0 |
| `projected_but_undocumented` | 0 |
| Runtime reality findings | 0 |
| Silent-failure files | 201 |
| Silent-failure occurrences | 1,580 |
| Silent-failure fail findings | 0 |
| Silent-failure `legacy_audited` entries | 65 |
| FP ledger events scanned | 118,892 |
| FP ledger flagged events (raw) | 1,035 (inflated — see Findings) |
| FP ledger real bypass events (`adaptive-bypass.jsonl`) | 0 bytes |
| WIP score | 92/100 |
| WIP dirty paths | 0 |
| WIP stash count | 0 |
| WIP snapshot markers | 1 (orphan) |
| Recovery drill pass rate | 3/3 (100%) |
| Dispatch smoke `llm-dispatch.jsonl` | 2,310 bytes (was 0 in DX assessment) |
| Dispatch smoke `task-history.jsonl` | 1,396 bytes (was 0 in DX assessment) |
| Architecture readiness pass | 11/12 |
| Architecture readiness fail | 1 (`repo-hygiene`: orphan snapshot marker) |
| `cos-boring-reliability --profile core` exit code | 1 (honest — `repo-hygiene` fail) |

---

## Cross-reference to the 2026-05-02 DX assessment

| DX assessment finding | Boring-reliability tool | Verified status |
|---|---|---|
| `\|\| true` silent surface (103 → 119, +16) | `cos-silent-failure-audit` | REAL — 1,580 occurrences classified, 65 in `legacy_audited`, 0 fail. Growth without classification will fail the gate. |
| `llm-dispatch.jsonl` 0 bytes | `cos-dispatch-smoke` | REAL — file is now 2,310 bytes after smoke run. |
| `task-history.jsonl` 0 bytes | `cos-dispatch-smoke` | REAL — file is now 1,396 bytes after smoke run. |
| Cold-start preamble overhead | `cos-preamble-budget` | REAL but PARTIAL — measures 800 of estimated 3,000-token budget for `core`, omits `AGENTS.md` (see Findings). |
| Theatre layer (trust/blast/review advisory) | `cos-runtime-hook-reality` + adoption-profile | REAL — 29 `real_blocking`, 59 `real_advisory`, 28 `observe_only`, all classified, no `documented_but_not_projected`. |
| False positives in gates | `cos-false-positive-ledger` | WORKS but NOISY — see Finding #1, substring match inflates count. |
| WIP loss in multi-orchestrator | `cos-wip-safety-score` + `cos-recovery-drill` | REAL — score 92/100, 3/3 drill scenarios pass. |
| Onboarding 1-day SR | `docs/getting-started/core-30-minute-onboarding.md` | NOT VERIFIED IN THIS AUDIT — out of scope for tool audit; doc exists but its claim is "30 minutes", which would require live new-developer testing to verify. |

---

## Operator dashboard summary

Run this single command to see the operator picture:

```bash
scripts/cos-boring-reliability --profile core
```

On the current `main`, that exits 1 with one explanatory failure
(`repo-hygiene` orphan snapshot marker). To clear:

```bash
rm .cognitive-os/runtime/pre-agent-snapshot-toolu_01XwryayB4512AotgHSky3V1.json
scripts/cos-boring-reliability --profile core
```

After clearing, the dashboard should exit 0 and report all checks green —
modulo the false-positive ledger noise documented above, which the dashboard
treats as informational, not failing.

---

## Recommendations

In priority order:

1. **Fix `cos-false-positive-ledger` substring match** so the FP signal is
   actually meaningful. Without this, the dashboard's "false-positive count"
   reflects log filenames, not real bypasses. ~30 min change to
   `scripts/cos_false_positive_ledger.py` plus a test.
2. **Add `AGENTS.md` to the `core` profile preamble inputs** so
   `cos-preamble-budget` reflects the full context tax. ~10 min change to
   the profile rule file list.
3. **Decide policy on `destructive-rm-blocker.sh`**: keep in `core` and add
   to `CORE_KEEP`, or accept the demotion to `lab`. ~5 min decision +
   commit.
4. **Clear the orphan snapshot marker** so the aggregator dashboard exits
   0. One-line `rm`.
5. **Verify the 30-minute onboarding doc empirically** — have a new
   developer (or simulated cold-start session) follow it timed. Not a
   tool-audit task.

---

## Conclusion

The boring-reliability control plane is **operationally real**. 8 of the 10
tools work end-to-end, write meaningful signals, and fail when they should.
The single defect (`cos-false-positive-ledger` substring noise) is a
~30-minute fix, not a structural problem. The dashboard's exit-1 state is
correct behaviour reflecting a single piece of repo-hygiene debt.

This converts six items the 2026-05-02 DX assessment marked as "no
movement" into items now backed by executable instrumentation, which is
the conceptual upgrade documented in `boring-reliability-control-plane.md`:
*"a gate is allowed to be default-visible only when it is real, measurable,
reversible, documented honestly, evidence-backed."*

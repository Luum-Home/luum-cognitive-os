# Post-Mortem: False-Done Compounding (2026-05-02)

**Authors:** Matias Nahuel Améndola (operator) + Claude (architect)
**Date:** 2026-05-02
**Severity:** HIGH — false completion state propagated to plan files and committed to main
**Status:** Resolved (adversarial review caught issues; commits corrected in-session)
**Related ADRs:** ADR-105 (bilateral claim verification), ADR-106 (multi-session safety primitives)

---

## TL;DR

A sub-agent in Wave C claimed "3 DELETE hooks already archived" in its commit message. The adversarial review pass discovered the claim was false: all three files still existed in `hooks/`, one was still registered in `.claude/settings.json`, and one "archive" copy was actually a symlink. The plan had been marked `[x]` on this false basis. Concurrently, a stash from a parallel agent never re-applied (59 modified files), and a second orchestrator session committed 3 uncoordinated fixes to main. The compounding risk: in multi-IDE multi-session workflows, false-done checkboxes survive across session boundaries and become ground truth for subsequent sessions — exponential error accumulation.

---

## TIMELINE

| Time | Event |
|---|---|
| Session start | Wave A dispatched: `fix(harness): reclassify session-sanity hook + reconcile scope phase 4` → commit `983a97e5` |
| Wave B | `feat(peer-card): implement ADR-077 Phase 1` → commit `c7dbf21c` |
| Wave C | `docs(plans): close so-existential-validation Phase 1 + design Phase 3` → commit `c8987b7a` ⚠️ *false-done* |
| During session | Parallel agent triggered `pre-agent-snapshot.sh` (stash auto `auto-pre-agent-94d24b09-...`), 59 files stashed, never re-applied |
| Concurrently | Second orchestrator session (X-COS-Session: 1777732313 / 1777731331) committed fixes `eaac243f`, `49c46c69`, `b1de3c40` to main without coordination |
| Post-commit | Operator requested adversarial review (manual, not automatic) |
| Adversarial review | `Code Reviewer` agent with `rules/adversarial-review.md` surfaced 2 HIGH + multiple LOW findings in ~15 min |
| Resolution | Issues corrected in-session; plan checkboxes revised |

---

## ROOT CAUSE ANALYSIS

### Layer 1 (Superficial) — Presence ≠ Removal Fallacy

The sub-agent found 3 files in `docs/archive/hooks/` and concluded "DELETE done." It never ran the inverse verification: `ls hooks/completeness-check.sh`, `ls hooks/post-agent-verify.sh`, `ls hooks/prompt-quality.sh`. The files existed in both locations simultaneously. "Archive present" was confused for "original removed."

### Layer 2 — Trust Score Measures Self-Report, Not Factuality

`rules/trust-score.md` evaluates evidence, criteria, and self-awareness from the agent's own report. A TRUST_REPORT of 90+ is compatible with false factual claims when the "verification" cited is adjacent to (not inverse of) the claim. The agent cited the archive directory's listing as evidence. That is truthy — the listing existed — but it does not prove the claim's full predicate.

### Layer 3 — Plan Checkboxes Are Unstructured Markdown

Marking `[x]` on a plan item is a text edit with no downstream contract. No hook reads plan files. No diff check verifies that the claim attached to `[x]` is supported by an executable command result. A checkbox is not a proof.

### Layer 4 — Absence of Domain-Specific Verification Helpers

No utility script `verify-archived.sh` exists that checks bilaterally: (a) file present in archive AND (b) original absent from `hooks/` AND (c) no references in `settings.json` / `cognitive-os.yaml`. Each individual check is straightforward; the absence of an integrated helper means agents improvise — and improvisation defaults to the optimistic partial check.

### Layer 5 (Structural) — Adversarial Review Was Off the Critical Path

The adversarial review that caught both HIGH findings ran because the operator requested it manually. If the operator had said "push," commit `c8987b7a` would have reached `origin/main` with the false-done claim intact. Wave D agents in subsequent sessions would have read `[x]` in the plan as ground truth and built on top of it.

---

## SECONDARY FAILURES

### Wave B HIGH — Scope Invariant Dead Code

ADR-077 mandates `scope: personal` for peer-card observations. `lib/peer_card.py` defined `OBSERVATION_SCOPE = "personal"` as an unreferenced constant: `safe_save()` accepted no `scope` parameter and propagated none to the engram call. Peer-cards were silently written to `scope: project` (engram default), violating the ADR. No test covered this invariant because the test suite did not include an assertion that peer-card observations land in `scope: personal`.

### Race Condition — Stash Leak

`pre-agent-snapshot.sh` created `stash@{0}` (`auto-pre-agent-94d24b09-...`) holding 59 modified files. The stash was never re-applied. Work from that stash was effectively invisible to any subsequent agent or operator reviewing the working tree state.

### Concurrent Session Commit Collision

A second orchestrator session (X-COS-Session: 1777732313 / 1777731331) committed 3 fixes (`eaac243f`, `49c46c69`, `b1de3c40`) to main without any coordination signal. No provenance collision was detectable at review time; commits landed cleanly but represented uncontrolled parallel state mutation.

---

## WHAT WORKED

- **Adversarial review with forced findings** (`rules/adversarial-review.md`): the `Code Reviewer` agent in adversarial mode with explicit severity labeling detected both HIGH issues and all LOW findings in a single ~15-minute pass.
- **Operator skepticism**: the manual trigger of adversarial review before pushing was the gating action that caught everything.
- **Engram audit trail**: observation IDs (16364 and others from Wave A/B/C agents) enable future sessions to reconstruct the discovery chain.

---

## WHAT FAILED

- **Orchestrator relied on TRUST_REPORT without bilateral verification**: the orchestrator committed Wave C output after reading a high trust score, without independently checking `ls hooks/` or `grep settings.json`.
- **Adversarial review was opt-in, not mandatory**: the policy in `rules/adversarial-review.md` exists but is not enforced on the commit path. No hook blocks `git commit` when a plan checkbox transitions `[ ]` → `[x]` without a verification command attached.
- **Stash lifecycle had no alarm**: `pre-agent-snapshot.sh` created a stash that was never surfaced to the operator as "unapplied work."
- **No provenance enforcement between sessions**: the second orchestrator session's commits are indistinguishable from main-session commits in the log; no `X-COS-Session` cross-reference blocked or flagged the overlap.

---

## ACTION ITEMS

| # | Action | Owner | ADR |
|---|---|---|---|
| 1 | Define bilateral claim verification contract for high-stakes claims | Architecture | ADR-105 |
| 2 | Extend plan checkbox format to require `(verified: <cmd>)` inline | Architecture | ADR-105 |
| 3 | Add stash-leak alarm: auto-pre-agent stashes unapplied >N minutes block dispatch | Architecture | ADR-106 |
| 4 | Add advisory plan-file lock per session; second writer receives explicit conflict error | Architecture | ADR-106 |
| 5 | Define provenance requirement: every commit to main MUST carry X-COS-Session | Architecture | ADR-106 |
| 6 | Orchestrator self-check: for filesystem claims in agent reports, orchestrator runs independent inverse verification before committing | Process | ADR-106 |
| 7 | Write `verify-archived.sh` helper: bilateral check (archive present + original absent + no config refs) | Implementation | ADR-105 |
| 8 | Add peer-card scope invariant test: assert engram observations land in `scope: personal` | Implementation | — |

---

## COMPOUNDING RISK MODEL

```
Session 0: Wave C writes false [x] to plan file
Session 1: reads [x] as ground truth, builds Wave D on top
Session 2: reads [x] + Wave D artifacts, extends further
...
Session N: 5+ commits buried under the false-done assumption
Discovery at Session N: requires N-session archaeology, may be unrecoverable
```

The operator's characterization was exact: false-done × sessions × time = exponential catastrophe potential. This is not a theoretical risk; it nearly happened in this session without the manual adversarial review gate.

---

## LESSONS

1. **Archive operations require bilateral proof**: "file A exists in archive" and "file A is absent from source + config" are two separate assertions. Both must be verified. A helper script is not optional — it is the only way to make bilateral verification consistent.

2. **Orchestrator trust in sub-agent TRUST_REPORT is insufficient for filesystem claims**: the orchestrator must run inverse verification independently before committing any claim tagged as "done," "archived," "wired," or "registered."

3. **Plan checkboxes are a liability without inline verification commands**: `[x] archived foo.sh` is meaningless without `(verified: ls hooks/foo.sh → not found)`. The format must change.

4. **Adversarial review must be on the critical path, not optional**: a single mandatory adversarial pass on any commit that closes plan items would have prevented this incident. The ~15-minute cost is dominated by the N-session recovery cost if it misses.

5. **Stash leaks are invisible failures**: auto-pre-agent stashes are silent. 59 modified files in `stash@{0}` represent invisible work. Any stash older than the current session must surface as an alarm before further dispatch.

---

## REFERENCES

- Incident: `docs/incidents/2026-05-02-false-done-compounding.md` (this file)
- ADR-105: `docs/adrs/ADR-105-claim-verification-contract.md`
- ADR-106: `docs/adrs/ADR-106-multi-session-safety-primitives.md`
- Prior incident: `docs/incidents/2026-05-01-session-multi-spawn-hang.md`
- Engram observation 16364: peer-card adversarial-review-fixes (Wave B fixer)
- Commits: `983a97e5` (Wave A), `c7dbf21c` (Wave B), `c8987b7a` (Wave C false-done)
- Concurrent session commits: `eaac243f`, `49c46c69`, `b1de3c40`

---

**Signed:** 2026-05-02
**Review frequency:** After any session producing plan checkbox transitions
**Ownership:** Matias Nahuel Améndola

# Pending-Truth Architecture — How Tasks Are Obtained and Closed

> **Status**: canonical (2026-05-12)
> **Scope**: OS
> **Owners**: ADR-273 (read side), ADR-274 (audit side), ADR-275 (write side
> + projection), ADR-248 (control-plane loop), ADR-105 (bilateral discipline).

This doc is the **single architectural map** of how Cognitive OS gets,
projects, closes, and protects task state across the 5 source surfaces it
historically accumulated. It exists because the pattern was discovered the
hard way: three adversarial-review iterations on 2026-05-12 surfaced
read/write/projection/drift gaps in sequence (single-instance fix →
audit-but-not-projected → projected-but-not-closed). This doc names the
finished shape so the next operator does not have to re-derive it.

## The four invariants

1. **OBTAIN** — 5 source surfaces normalized into 1 ledger (`docs/06-Daily/reports/
   pending-truth-latest.json`).
2. **PROJECT** — ledger + audit findings surfaced at session-start across
   all 3 harnesses, with a single ranked "what to attack first" list.
3. **CLOSE** — every closure carries bilateral proof (ADR-105) and lands
   in `.cognitive-os/audit/closure-trail.jsonl`. Manual edits to source
   surfaces still work but are flagged as LOW trust.
4. **PREVENT DRIFT** — staleness, drift, and ledger-orphan edits are
   detected via 3 anti-drift hooks (ADR-273 Slice C).

If any invariant is broken, the others lose value: an aggregator with no
projector is invisible; a projector with no atomic closer requires
operators to edit 5 sources manually for each "done".

---

## Layer 1 — OBTAIN (read side)

```
5 SOURCE SURFACES
  ├─ plans/*.md checkboxes            ─┐
  ├─ docs/02-Decisions/adrs/ADR-*.md (status)       ├─→  scripts/cos-pending-truth-aggregator
  ├─ follow-ups (ADR frontmatter)      │    (ADR-273 Slice A)
  ├─ user-requests/queue.jsonl         │
  └─ .cognitive-os/tasks/active-tasks  ─┘
                                              │
                                              ▼
                                   docs/06-Daily/reports/pending-truth-latest.json
                                   (~279 items, schema: pending-truth/v1)

  scripts/cos-pending-truth-verify    (ADR-273 Slice B)
    deterministic verifier — runs after aggregator
    classifies each item:
      verified-pending | verified-done | obsolete | ambiguous
    checks: path-exists, ADR status, CHANGELOG keyword match
    (intentionally NOT semantic — semantic verification is a Phase 2
    follow-up; deterministic checks catch ~2.5% of mismarks vs ~25%
    Opus-driven, but they never lie)

  scripts/cos-operational-guide-audit.py    (ADR-274)
    specialized audit for the §Operational Guide contract on
    maintainer-tier capability ADRs
    output: docs/06-Daily/reports/operational-guide-audit-latest.{json,md}

  scripts/cos-control-plane-audit    (ADR-248)
    orchestrator: runs audits per lane (hook-fast | hourly | pre-public)
    emits findings → .cognitive-os/tasks/control-plane-remediation.jsonl
    + .cognitive-os/metrics/control-plane-audit.jsonl
    operational-guide-coverage is one of the registered audits (ADR-274
    Phase 3); adr-partial-lifecycle is registered for hourly/pre-public
    lanes so ADR lifecycle debt becomes normal remediation queue input.

  scripts/cos-adr-partial-ledger + scripts/cos-adr-partial-audit
    ADR lifecycle bridge: turns Active/partial|blocked|deferred ADRs into
    docs/06-Daily/reports/adr-partial-backlog-latest.{json,md}, then emits
    control-plane findings for missing remaining-work metadata, stale
    partials without follow-up ADRs, and possible close candidates.
```

**Trust contract** (ADR-105): the aggregator does not invent. Items only
appear in the ledger if a source surface declared them. The verifier
never marks anything `verified-done` without a positive evidence check.

---

## Layer 2 — PROJECT (where the data is consumed)

```
scripts/cos-session-start-projector    (ADR-275)
  reads all of Layer 1 plus:
    - git state (branch, ahead/behind, dirty)
    - staged operator-deploy dirs (docs/05-Methodology/runbooks/*-staging/)
  emits, bounded to top-N (default 5, configurable
  COS_PROJECTOR_LIMIT):
    - pending_truth: by_status counts, top_actionable items
    - operational_guide: P0/P1 counts, top_backfill ADRs
    - control_plane: open findings
    - adr_partials: partial/deferred/blocked ADR lifecycle backlog
    - staged_deployments: dirs awaiting operator deploy
    - git_state: branch + ahead/behind/dirty
    - suggested_next_actions: ranked cheapest-unblocker first

  60s cache TTL (.cognitive-os/runtime/session-start-projection.cache.json)
  bypass: COS_PROJECTOR_NOCACHE=1

WIRED INTO 3 HARNESSES at SessionStart (ADR-008 cross-harness portability):
  - .claude/settings.json        (hooks.SessionStart[0].hooks[])
  - .codex/hooks.json            (hooks.SessionStart[])
  - .cognitive-os/cos-runner-hooks.json  (events.SessionStart[])
                                          [gitignored: local-only]
```

**Why bounded**: an unbounded projection is the same anti-pattern that
motivated the projector (state-not-surfaced). 279 items in a session-start
block is noise; top-5 actionable + counts is signal.

**Why cached**: protects against thrashing on rapid re-runs (operator
opens 4 terminals in 10 seconds). Cache is content-deterministic so
parallel sessions see the same projection.

---

## Layer 3 — CLOSE (write side)

**Canonical status vocabulary**: [`docs/02-Decisions/adrs/STATUS-TAXONOMY.md`](../adrs/STATUS-TAXONOMY.md)
defines the decision-status and implementation-status values that all
closure primitives consume (`accepted | implemented | partial |
partial-blocked | blocked | deferred | superseded | tombstone |
not-applicable | resolved`). Both close primitives below validate against
this vocabulary before writing.

**Trust signal** — `scripts/cos-closure-trust-signal.py` quantifies the
asymmetry between audited closures (via the primitives below) and
manual closures (direct source edits): emits HIGH | MEDIUM | LOW | ZERO
band and feeds the trust-report (ADR-244) via the
`closure-trust-signal` audit registered in
`manifests/control-plane-audits.yaml`.

```
scripts/cos-pending-truth-close    (ADR-275) — ATOMIC, AUDITED
  flags:
    --id     <ledger-id>     required, exact match from
                             pending-truth-latest.json
    --proof  <ref>           required, one of:
                               path:line  (e.g. lib/foo.py:42)
                               ADR-NNN    (must be accepted|implemented)
                               test-id    (tests/X.py::test_Y)
                               commit-sha
    --reason <text>          optional, free-text, persisted
    --dry-run                show what would change, write nothing

  steps:
    1. Find item by id (404 if not found → exit 2)
    2. Verify proof bilaterally per ADR-105 (exit 3 on rejection)
    3. Apply canonical closure edit to the original source:
       plan-checkbox → `- [ ]` → `- [x] (verified: <proof>)`
       adr-slice     → frontmatter implementation_status → implemented
       audit-finding → annotate closure-trail; source JSON unchanged
       follow-up/user-request → append closed_at + closure_proof
    4. Append entry to .cognitive-os/audit/closure-trail.jsonl
    5. Re-run aggregator (--skip-refresh to disable)
    6. Exit 0 + print closure receipt

  schema_version: closure-trail/v1
```

Parallel ADR lifecycle closure:

```
scripts/cos-adr-close
  unit: ADR decision record rather than task/checkbox
  updates: implementation_status, classification_basis, evidence fields
  refreshes: docs/02-Decisions/adrs/INDEX.md + ADR partial backlog ledger
  projection: cos-session-start-projector emits [adr-partial-close]
              actions from adr-partial-backlog-latest.json
```

This is intentionally separate from `cos-pending-truth-close`: pending-truth
closes task items from source surfaces; `cos-adr-close` closes the execution
state of an architectural decision. The projector now consumes both, so the
operator sees one ranked action list instead of two disconnected queues.

**Manual closures still work** (editing the source surface directly) —
the aggregator picks them up on next run. But manual closures land in the
ledger WITHOUT a closure-trail entry, which produces a LOW trust signal
in the trust-report (ADR-244). The asymmetry is by design: friction-free
manual editing for operators in a hurry, but the audit shows who closed
what cold.

**Why bilateral proof**: history showed 25% of plan checkboxes marked
`[x]` were unverified (Opus batch sweep, 2026-05-12). The close primitive
fails fast on proof rejection so no closure can land that the verifier
would later flag.

---

## Layer 4 — PREVENT DRIFT (anti-staleness)

```
Three hooks in hooks/ (ADR-273 Slice C):

pending-truth-drift-detector.sh    PostToolUse Edit|Write
  emits additionalContext (non-blocking nudge) when an edited path is
  mentioned in any ledger item's next_action / evidence

pending-truth-verify-weekly.sh     Stop (async, fire-and-forget)
  if ledger >7d stale OR >50% of items have last_verified >7d:
    background-runs scripts/cos-pending-truth-verify --max-age-days 7

pending-truth-staleness-gate.sh    PreToolUse Bash
  on `git commit*` if ledger >30d old: emits additionalContext
  warning to refresh aggregator+verifier

ALL THREE are conditional_opt_in (manifests/hook-registration-classification.yaml).
They live in hooks/ but do not fire by default — operator promotes to active
via apply-efficiency-profile.sh maintainer after reviewing nudge frequency
on real workflow (ADR-275 §gate-symmetry).
```

**Why advisory, not blocking**: the cost of a false-positive nudge >>
the cost of a 30-day-old ledger. Blocking on staleness would force the
operator to refresh on every commit, including the commits that refresh
the ledger.

---

## Cross-references

| ADR | Owns |
|---|---|
| **ADR-105** | Bilateral claim verification — proof contract for closures |
| **ADR-244** | Trust-report enforcement — closure-trail feeds trust score |
| **ADR-248** | Control-plane audit loop — orchestrates audits + remediation queue |
| **ADR-273** | Pending-truth ledger (aggregator + verifier + Slice C hooks) |
| **ADR-274** | §Operational Guide contract + audit + control-plane wiring |
| **ADR-275** | Closure & projection primitives + gate symmetry for opt-in hooks |
| **ADR-008** | Multi-tool support — projector wired into 3 harnesses |
| **ADR-117** | Stash mutation reversibility — closure-trail follows the named/audited pattern |

## Artifact locations

| Artifact | Path | Format |
|---|---|---|
| Aggregated ledger | `docs/06-Daily/reports/pending-truth-latest.json` | pending-truth/v1 |
| Aggregated ledger (human) | `docs/06-Daily/reports/pending-truth-latest.md` | markdown |
| §Operational Guide audit | `docs/06-Daily/reports/operational-guide-audit-latest.{json,md}` | operational-guide-audit/v1 |
| ADR partial backlog | `docs/06-Daily/reports/adr-partial-backlog-latest.{json,md}` | adr-partial-backlog/v1 |
| Control-plane findings | `.cognitive-os/tasks/control-plane-remediation.jsonl` | append-only JSONL |
| Closure audit trail | `.cognitive-os/audit/closure-trail.jsonl` | closure-trail/v1 |
| Projection cache | `.cognitive-os/runtime/session-start-projection.cache.json` | session-start-projection/v1 |

## Operational sequence — what a session looks like cold

1. **SessionStart** fires across whichever harness opened → projector
   prints summary block to stderr (or stdout in `COS_PROJECTOR_STRICT=1`):
   ```
   === Cognitive OS — Session Start Projection (ADR-275) ===
   git: branch=main ahead=0 dirty=False
   pending-truth ledger: 279 items {'verified-pending': 267, ...}
   operational-guide backfill: P0=0 P1=0
   control-plane open findings: 134
   ADR partial backlog: 120 items {'partial': 118, ...}
   staged-for-operator-deploy: 0 dir(s)
   Suggested next actions (top-5): ...
   ```
2. Operator/agent picks one suggested action.
3. When work is done: `cos-pending-truth-close --id <X> --proof <Y>`
   atomically closes + records.
4. Anti-drift hooks (Slice C) fire opportunistically based on edits and
   the 7d/30d staleness thresholds.
5. Weekly: control-plane-audit-hourly lane re-runs registered audits,
   including adr-partial-lifecycle, plus recurrence counts; new findings land in remediation queue with
   time-to-detect / time-to-remediate metrics (ADR-248).

## Why this beats the prior state

| Before | After |
|---|---|
| 5 source surfaces, each edited by hand | 1 ledger, 1 closer, 5 surfaces auto-synced |
| "Done" claims unverifiable cold | Closure-trail with bilateral proof |
| Session start = `rules/startup-protocol.md` (4 static lines) | Session start = top-5 actionable from real queue |
| Staleness invisible until adversarial review | 3 advisory hooks detect at edit/commit time |
| Per-IDE special-casing | Single projector, 3 harness adapters |

## Known follow-ups

Not yet implemented; tracked as Phase 2+ of ADR-275:

- **Semantic verifier**: deterministic verifier catches ~2.5% mismarks
  vs ~25% Opus-driven. A bounded-scope LLM verifier per item would close
  this gap without polluting the trust signal.
- **Multi-source atomic close**: one operator action closes a checkbox +
  its owning ADR + its tracking follow-up in one transaction. The interim
  bridge is projector-level: pending-truth and ADR lifecycle close actions
  are ranked together, but still executed by their dedicated close commands.
- **Trust-report quantification**: unaudited closures (manual edits with
  no closure-trail entry) should explicitly lower the trust score.
- **Projector top-N ranking heuristic**: current default is age-desc;
  recency × blast-radius × unblocking-count is better.

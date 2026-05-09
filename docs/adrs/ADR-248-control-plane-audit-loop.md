---
adr: 248
title: Control-Plane Audit Loop for ADR-239+ Primitive Drift
status: accepted
relationship_chain_exempt: true
date: 2026-05-08
supersedes: []
superseded_by: null
extends: [ADR-239, ADR-240, ADR-247]
implementation_files:
  - manifests/control-plane-audits.yaml
  - scripts/cos-control-plane-audit
  - tests/unit/test_control_plane_audit.py
tier: maintainer
tags: [control-plane, audits, hooks, scheduler, primitive-coherence, adr-239-plus]
---

<!-- ADR_RELATION_CHAIN_EXEMPT: part of the 2026-05-08 implementation-ledger ADR burst; relationship depth is tracked by control-plane audits rather than new transitive ADR scope. -->

# ADR-248: Control-Plane Audit Loop for ADR-239+ Primitive Drift

## Status

Accepted — Slice A implemented.

## Context

ADR-239 and later ADRs define the right classes of protection: isolated write
worktrees, primitive coherence, history rewrite wrappers, post-rewrite push
markers, claim enforcement, chaos source guards, release freeze, and
manifest-driven postmortem audits.

The missing operational layer is a way to run those detectors precisely and
repeatedly without hand-invoking every script. The operator explicitly asked for
tools that can run from hooks or every N minutes to detect inconsistencies and
resolve the ADR-239+ backlog without hardcoding sensitive data or manually
fixing each primitive first.

## Operational complement: loops, not "more care"

The reliability claim for ADR-239+ must not be "agents will be more careful."
The strongest honest guarantee available in real systems is an automatic control
loop:

```text
declarative contract
→ automatic detector
→ hook / scheduler / release gate
→ metrics
→ remediation queue
→ separate fix
→ regression-prevention test
```

As of 2026-05-08, COS has the skeleton of this loop, but it is not yet closed
end-to-end. The current `hook-fast` aggregate correctly reports a blocked state
instead of a false green:

```text
scripts/cos-control-plane-audit --lane hook-fast --json
status: block
15 findings
11 blockers
4 warnings
```

That blocked result is useful evidence: the system already sees that closure
work remains.

Current surface status:

| Layer | Status |
|---|---|
| Primitive coherence detector | Implemented: `scripts/primitive-coherence-audit.py` |
| ADR-242 through ADR-246 detector | Implemented: `scripts/cos-postmortem-regression-audit` |
| Manifest-driven checks | Implemented: `manifests/postmortem-regression-audit.yaml` |
| Lane aggregator | Implemented: `scripts/cos-control-plane-audit` |
| `hook-fast`, `hourly`, `pre-public` lanes | Implemented: `manifests/control-plane-audits.yaml` |
| Pre-public risk audit | Exists |
| State retention audit | Exists |
| Worktree / ownership audit | Partial |
| Safe auto-correction | Partial; not generalized |
| Transactional release freeze | Missing; ADR-246 remains pending |
| Formal scheduler / hook wiring | Implemented for `hook-fast` on Agent PreToolUse via `hooks/control-plane-audit.sh`; broader hourly scheduler remains future work |

Prevention map:

| Problem class | Correct prevention | Current detector | Missing closure |
|---|---|---|---|
| Agent changes branch without notice | Block branch switching and require an agent worktree | Partial | Integrate into the control-plane loop |
| Sensitive data reintroduced after sanitization | Pre-public audit, secret scanners, and freeze | Partial | Final rewrite path and freeze |
| Content rewrite confused with metadata rewrite | Content-only default | Partial | Explicit detector for metadata flags |
| Agents write during history rewrite | `cos release freeze` | Missing; audit detects the gap | Implement ADR-246 |
| Reports publish sensitive paths | Output sanitization contract | Partial | Manifest-driven public-report rules |
| Scripts outside ownership | Ownership manifest and rename detector | Partial | ADR-241 / ownership detector expansion |
| Noisy false positives | Adversarial pattern tests | Partial | False-positive / false-negative metrics |
| Stale generated scorecards | Generated-report freshness audit | Partial | Timestamp and source-hash checks |
| "Closed" claimed while blockers remain | Claim enforcer | Missing; audit detects the gap | Implement ADR-244 |
| Hook exists but is not wired | Producer-consumer audit | Partial ADR-240 | Expand coverage |

The next maturity step is to move from "audits that an operator can run" to
"audits that run automatically and block in the right place":

1. `hook-fast` runs through `hooks/control-plane-audit.sh` before agent launch, before commit/push/destructive git commands, and before public report writes. The hook filters payloads so unrelated Bash/Edit calls do not pay the audit cost.
2. `hourly` runs through `hooks/control-plane-audit-hourly.sh` on Stop/session-end with cooldown, emitting metrics without making session cleanup brittle.
3. `pre-public --strict` runs inside `cos release freeze` via `manifests/release-freeze.yaml` before sanitize, force-push, or publication. Without a freeze, an audit can pass and another agent can dirty the repository seconds later.

Auto-correction is allowed only for safe classes:

| Finding class | Auto-fix policy |
|---|---|
| Regenerable stale report | Allowed |
| Cache, metrics, or runtime garbage | Allowed |
| Missing generated index | Allowed |
| Unexpected branch switch | Block; do not auto-fix |
| History rewrite | Block without a transaction id |
| Metadata rewrite | Requires explicit operator intent |
| Sensitive data in history | Propose remediation; require operator approval |
| Chaos test mutating source | Block; do not silently fix |
| False "tests pass" claim | Downgrade or block |

The repair loop is therefore:

```text
detect → propose → apply only if the finding is in a safe class → measure result
```

It is not "the agent fixes everything by itself."

This doctrine intentionally assumes that the current audit set only scratches
the surface. Each new incident must become a manifest rule; each rule must emit
a stable finding; each finding must have a metric; each fix must reduce or clear
the finding; regressions must re-open the finding; and new classes must be added
without hardcoding private data. ADR-247 and ADR-248 are the start of that
meta-system.

## Decision

Introduce a manifest-driven control-plane audit runner:

```text
manifests/control-plane-audits.yaml
scripts/cos-control-plane-audit
```

The runner executes declared read-only audits by lane and aggregates their JSON
findings into one report. It is not a repair engine. It creates the stable
feedback loop that future hooks, cron jobs, launchd timers, or release-freeze
transactions can consume.

Slice A lanes:

- `hook-fast` — fast non-mutating checks suitable for lifecycle hooks.
- `hourly` — periodic local sweep for primitive drift.
- `pre-public` — release-readiness sweep that can include slower public-risk
  checks.

Slice A audits:

- `primitive-coherence` — `scripts/primitive-coherence-audit.py --json`.
- `postmortem-regressions` — `scripts/cos-postmortem-regression-audit --json`.
- `pre-public-risk` — `scripts/cos-pre-public-risk-audit --json` in the
  `pre-public` lane.

## Enforcement model

1. Audits declare `mutates: false`; mutating audit specs are blocked before
   execution.
2. Audits must emit JSON with an expected `schema_version`.
3. The runner returns block if any underlying audit has block findings.
4. Warnings remain warnings unless `--strict` is passed.
5. Sensitive values stay outside the manifest; audits may consume env-var names
   but not hardcoded private values.

## Hook and schedule integration

The runner is designed to be called by future hooks or timers:

```bash
scripts/cos-control-plane-audit --lane hook-fast --json
scripts/cos-control-plane-audit --lane hourly --json
scripts/cos-control-plane-audit --lane pre-public --json --strict
```

A hook should use `hook-fast`. A launchd/cron automation should use `hourly`.
A release transaction should use `pre-public`.

## Alternatives rejected

- **Run every audit from every hook** — rejected because heavy checks in hot
  paths cause operator fatigue and disablement.
- **Make each ADR install its own scheduler** — rejected because per-ADR timers
  recreate the incoherence problem at the scheduling layer.
- **Auto-fix findings directly from the runner** — rejected because ADR-240 and
  ADR-247 require detect-first/remediate-second with explicit commits.
- **Hardcode audit commands in shell hooks** — rejected because lanes and audit
  membership must be versioned in a manifest.

## Consequences

Positive:

- ADR-239+ detectors can run continuously without bespoke glue per ADR.
- Hooks and cron/launchd can consume the same audit lanes.
- A single report shows whether unresolved postmortem classes remain.
- Future remediation tools can consume stable finding codes.

Negative:

- The runner adds one more manifest to maintain.
- If an underlying audit is noisy, the aggregate lane is noisy.
- Hook integration must be careful to use only the fast lane.

## Verification

```bash
python3 -m pytest tests/unit/test_control_plane_audit.py tests/unit/test_postmortem_regression_audit.py tests/audit/test_adr_contracts.py -q
scripts/cos-control-plane-audit --lane hook-fast --json
```


## Implementation note — 2026-05-08 full loop wiring

The initial hook-fast Agent-only wiring has been expanded into the full ADR-248 loop:

- `hooks/control-plane-audit.sh` filters hook payloads and runs `scripts/cos-control-plane-audit --lane hook-fast --json` before Agent launches, `git commit`, `git push`, destructive git commands, and public report/document writes under `docs/reports/`, `docs/history/`, and `docs/business/`.
- `hooks/control-plane-audit-hourly.sh` runs the `hourly` lane on Stop/session-end with a 3600-second cooldown.
- `lib/release_freeze.py` now includes the `control_plane_pre_public` check, which executes `scripts/cos-control-plane-audit --lane pre-public --json --strict` inside the release freeze transaction.
- `.claude/settings.json`, `templates/security-profiles/*.json`, and `scripts/apply-efficiency-profile.sh` all project the hooks so they do not become producer-without-consumer artifacts.


## Implementation note — 2026-05-08 remediation queue and metrics

The control-plane runner now persists the loop state, not just stdout:

- Latest report: `.cognitive-os/reports/control-plane/latest.json`
- Remediation queue: `.cognitive-os/tasks/control-plane-remediation.jsonl`
- Metrics stream: `.cognitive-os/metrics/control-plane-audit.jsonl`
- Runtime state: `.cognitive-os/runtime/control-plane-audit/findings-state.json`

Each finding receives a stable id derived from lane, audit id, ADR, code, message, and path/primitive. Metrics include findings by ADR, new/resolved counts, recurrence count, time-to-remediate for resolved findings, and false-positive rate from explicit labels in `.cognitive-os/tasks/control-plane-remediation-labels.jsonl`.

Automatic correction is intentionally gated. The runner supports `--apply-safe-fixes`, but it only executes commands declared under `remediation.safe_fixes` whose `safe_class` appears in `remediation.safe_classes`. The default manifest declares safe classes but no fixes. This preserves the doctrine: detect → propose → apply only if safe class → measure result.


## Future primitive safety boundary

ADR-248 consumes detectors; it does not make undeclared primitives safe by
itself. A new skill/hook/rule/script/daemon/repair command is protected by the
control loop only after ADR-240 or a sibling manifest declares its owner,
lifecycle, read/write surfaces, mutability, ordering edges, bypasses, external
tool boundaries, and tests. Otherwise the runner can only catch generic classes
that already exist in a detector.

This is deliberate: the guarantee is not “any new primitive is automatically
safe.” The guarantee is “any new primitive that goes through the declarative
registration contract becomes auditable, measurable, queueable, and eligible
for safe-class remediation if explicitly allowed.”


## Incident closure status

The incident-by-incident closure table is maintained in `docs/reports/primitive-coherence-drift-postmortem-2026-05-08.md` under “Incident closure status — 2026-05-08”.

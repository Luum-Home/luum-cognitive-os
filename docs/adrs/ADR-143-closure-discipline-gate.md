---
adr: 143
title: Closure Discipline Gate — Validation Nervous System Must Close With the Change
status: accepted
date: 2026-05-04
supersedes: []
superseded_by: null
implementation_files:
  - scripts/cos-closure-discipline-audit
  - scripts/cos_closure_discipline_audit.py
  - tests/unit/test_closure_discipline_audit.py
  - docs/manual-tests/closure-discipline.md
tier: maintainer
tags: [validation, closure, governance, testing, local-ci]
---

# ADR-143: Closure Discipline Gate — Validation Nervous System Must Close With the Change

## Status

**Accepted.** Closure discipline is now a first-class blocking maintainer gate.

This ADR does not require every task to run the full release suite. It requires
changes to close the validation surfaces they invalidate. Feature-local tests are
necessary but not sufficient when the change touches the mechanisms that decide
whether work is done.

## Context

The 2026-05-03 ADR/commit batch was architecturally coherent and its targeted
new-surface tests passed, but `make test-laptop` later exposed drift:

1. workflow tests still expected active `.github/workflows/*.yml` files after
   ADR-130 suspended GitHub Actions as `.yml.disabled`;
2. runtime-hook reality carried a hardcoded projected hook count (`115`) while
   the actual projection had changed (`114`);
3. the validation capsule assumed every repository had
   `hooks/_lib/safe-worktree-remove.sh`, which is false for minimal consumer
   repos used by tests;
4. work-inventory tests created temporary worktrees that the ADR-121 ephemeral
   path filter now deliberately skips;
5. ADR-133 verification failed because two blocking primitives had lifecycle
   metadata (`governance_class: meta-governance`) that contradicted the
   primitive-lifecycle audit rule requiring blocking/high-risk primitives to be
   `runtime-safety`.

This is not a failure of the new ADRs' direction. It is a failure to close the
system that validates the direction. The SO already had partial closure
mechanisms:

| Existing surface | What it covers | Gap exposed |
|---|---|---|
| Definition of Done / `dod-check` | Agent response evidence by task complexity | Consumes reported evidence; does not detect stale validators. |
| `verification-before-completion` skill | Requires fresh verification before success claims | Procedural; not wired to known closure-drift classes. |
| `completion-gate.sh` / `dod-gate.sh` | Post-agent completion warnings | Agent-output scoped; does not scan repo validation infrastructure. |
| Validation capsule (ADR-109/113) | Isolated broad validation | Can itself drift or assume COS-only helpers. |
| Derived artifact gate | Canonical-to-generated artifact closure | Only covers registered derived artifacts. |
| Local CI migration (ADR-131) | Replaces suspended GitHub Actions | Did not force tests to understand `.yml.disabled` preservation. |
| Primitive lifecycle governor (ADR-126) | Metadata consistency | Not pulled into a named closure discipline gate. |
| Work inventory doctor | WIP/branch/worktree closure | Does not validate test assumptions after implementation changes. |

The missing primitive is a structural closure audit: a quick local-CI gate that
checks whether the validation nervous system still matches repository reality.

## Decision

Add `scripts/cos-closure-discipline-audit` as a blocking maintainer primitive and
wire it into `scripts/cos-ci-local.sh quick`.

The gate is intentionally narrow and evidence-driven. It audits the drift
classes that just escaped targeted validation:

1. **Suspended workflow references** — tests/scripts must not reference active
   `.github/workflows/*.yml` files when only the ADR-130 `.yml.disabled` artifact
   exists, unless they explicitly use an active-or-disabled compatibility helper.
2. **Hardcoded runtime hook counts** — runtime reality tests must assert
   report-derived parity/findings, not magic integers such as `115`.
3. **Validation capsule minimal-repo fallback** — the capsule may use the ADR-129
   safe worktree helper in COS checkouts, but must retain a non-`rm -rf` fallback
   for minimal repos.
4. **Primitive lifecycle consistency** — `primitive_lifecycle.py --json` findings
   are closure failures for maintainer quick CI.
5. **Self-wiring** — quick local CI must run the closure discipline audit, or the
   audit is decorative.

The gate is not a substitute for `make test-laptop`. For pre-commit WIP validation, use `make test-laptop-direct`; the validation capsule used by `make test-laptop` validates the current `HEAD` in an isolated worktree, so it is the post-commit/release-safety proof path, not proof of uncommitted edits. It is the fast guard that
prevents agents from leaving obvious validation-system drift for the broad lane
to discover after the batch is declared done.

## Alternatives rejected

1. **Rely only on `make test-laptop`.** Rejected because broad validation is too late in the loop: it finds stale validators after the agent has already formed a completion claim.
2. **Add more prose to the DoD skill.** Rejected because the failure mode is structural repository drift, not lack of instructions.
3. **Revert fast reconstruction batches when broad validation fails.** Rejected because many failures are validator drift, not invalid architecture; the correct move is targeted closure hardening plus evidence.

## Consequences

### Positive

- Fast agent batches can still move quickly, but stale validation infrastructure
  becomes visible before a closure claim.
- The SO now distinguishes **feature validation** from **validator closure**.
- ADR-130/131 workflow suspension is mechanically understood by tests instead of
  relying on maintainer memory.
- Hook demotions/promotions no longer require updating a magic test integer.
- Validation capsule portability is tested against minimal repos, not just the
  COS checkout.

### Negative / Trade-offs

- Quick CI gains another maintainer-only blocking check.
- The closure audit must stay focused; if it becomes a broad test runner it will
  duplicate `make test-laptop` and increase DX tax.
- Some findings are structural and conservative. A legitimate exception must be
  encoded in the audit with an ADR-backed reason, not bypassed by deleting tests.

## Verification

```bash
scripts/cos-closure-discipline-audit --fail-on-findings --json
python3 -m pytest tests/unit/test_closure_discipline_audit.py -q
python3 -m pytest \
  tests/unit/test_test_lanes_workflow.py \
  tests/unit/test_primitive_gap_workflow.py \
  tests/unit/test_primitive_coverage.py \
  tests/unit/test_cos_work_inventory.py::TestCollectWorktreesDirect \
  tests/unit/test_runtime_hook_reality.py::test_repository_settings_hook_count_is_report_derived_not_hardcoded \
  tests/unit/test_validation_capsule.py::test_validation_capsule_runs_in_isolated_worktree \
  -q
python3 scripts/primitive_lifecycle.py --json
bash scripts/cos-ci-local.sh quick
```

Manual proof path: [`docs/manual-tests/closure-discipline.md`](../manual-tests/closure-discipline.md).

## Border Cases

- A workflow may be restored from `.yml.disabled` to active `.yml`. The audit then
  allows direct active references again.
- A test may mention both active and disabled workflow paths as part of an
  explicit compatibility helper. The audit allows this when `.disabled` or a
  `workflow_file(...)` helper appears near the reference.
- A consumer repo may not have COS hook helper libraries. The validation capsule
  must still clean up with `git worktree remove --force` plus `git worktree
  prune`, never silent `rm -rf`.
- A broad lane can still fail for real product bugs. This ADR only prevents the
  known class where the validators themselves were stale.

## Cross-references

- ADR-109: Validation Capsule Worktree Isolation
- ADR-113: Validation Capsule Liveness Primitives
- ADR-121: Foundation Hardening Program
- ADR-126: Agentic Primitive Lifecycle Governor
- ADR-130: Suspend All GitHub Actions Workflows
- ADR-131: Local-CI Migration
- ADR-133: Expansion Without Monsterization
- [`docs/architecture/validation-nervous-system.md`](../architecture/validation-nervous-system.md)
- [`docs/definition-of-done.md`](../definition-of-done.md)

---
status: Accepted
date: 2026-05-14
deciders: Cognitive OS maintainers
tags:
  - dependencies
  - installer
  - git-hooks
  - maintenance
implementation_status: Implemented
---

# ADR-308: Dependency Maintenance Across Install, Update, and Git Hooks

## Status

Accepted


## Context

ADR-305 added a read-only dependency coverage audit and ADR-307 added triage plus a fail-new profile ratchet. Those primitives make dependency drift visible, but they do not automatically run when operators install the SO, update an existing install, or trigger repository maintenance through Git events.

The existing construction surfaces are split across several paths:

- `scripts/setup.sh` for local maintainer setup.
- `install.sh`, `scripts/cos-bootstrap.sh`, `scripts/cos-deps-install.sh`, and `scripts/cos_deps_install.py` for installation and host-tool profiles.
- `scripts/cos-update.sh`, `hooks/self-install.sh`, and `scripts/register-mcps.sh` for update/sync behavior.
- `scripts/auto-update-projects.sh` for propagating COS source updates to registered installations.
- `scripts/setup-git-hooks.sh` plus checked-in `.githooks/pre-push`, `.githooks/post-merge`, and `.githooks/post-rewrite` for Git-triggered propagation after `git push`, merge-based `git pull`, and rebase-based `git pull --rebase`.
- `.githooks/pre-commit`, `.githooks/post-commit`, and hook gates under `hooks/` for local safety checks.

The high-risk failure mode is hidden mutation: a `git pull`, `git push`, or background auto-update must not unexpectedly install host tools or rewrite an operator machine. The second failure mode is silent drift: if new scripts start requiring tools, the SO should surface that during the normal construction/update lifecycle, not only when a maintainer remembers to run an audit manually.

## Decision

Add a single advisory maintenance primitive, `scripts/cos-deps-maintain`, backed by `lib/dependency_maintenance.py`.

The primitive runs the existing dependency coverage loop:

1. coverage reconciliation from ADR-305;
2. dependency tool intake/triage from ADR-307;
3. profile ratchet evaluation from ADR-307;
4. an explicit `scripts/cos-deps-install.sh --profile <profile> --dry-run` install plan.

Default behavior is read-only and advisory. It never installs tools automatically. It prints the command an operator can run and leaves `--apply` as an explicit human/operator action.

Wire the primitive into the construction surfaces where drift matters:

- `scripts/setup.sh` after Python/tool setup and before doctor.
- `scripts/cos-update.sh` after source-level sync helpers and before `hooks/self-install.sh`.
- `scripts/auto-update-projects.sh` once per source update before downstream project propagation.
- `scripts/setup-git-hooks.sh` generated `pre-push`, `post-merge`, and `post-rewrite` blocks.
- checked-in `.githooks/pre-push`, `.githooks/post-merge`, and `.githooks/post-rewrite` so the current repository uses the same contract.

`COS_DEPS_MAINTENANCE=0` disables the check for emergency/offline flows. Git hook wrappers set `COS_DEPS_MAINTENANCE_ALREADY=1` when handing off to auto-update so pull/push paths do not run the same advisory audit twice. `COS_DEPS_RATCHET_STRICT=1` enables strict ratchet mode for hooks/CI that intentionally want to reject unaccepted findings; at the time of this ADR it blocks because the repository has 114 unaccepted actionable findings and no accepted baseline. Normal install/update/git hooks keep the check advisory.

## Consequences

Positive:

- Dependency drift is visible during setup, update, `git pull`, and maintainer `git push` propagation.
- Git-triggered flows stay safe: no background host-tool installation.
- Existing ADR-305/ADR-307 primitives become part of the SO construction lifecycle rather than isolated maintainer commands.
- Operators get one stable command for diagnostics: `scripts/cos-deps-maintain --mode <surface> --json`.

Negative / trade-offs:

- Setup/update/hooks do extra read-only work and can be noisy while the current baseline still has accepted debt to triage.
- Strict enforcement remains opt-in until the historical baseline is reviewed.
- The primitive reports installer plans but does not solve manifest completeness by itself; follow-up work still needs profile/lane changes.

## Alternatives rejected

- **Leave the behavior as implicit agent instruction only.** Rejected because this ADR records a runtime/authoring contract that needs durable tests or audits rather than conversation-only memory.

## Verification

- `bash -n scripts/cos-deps-maintain scripts/setup.sh scripts/cos-update.sh scripts/auto-update-projects.sh scripts/setup-git-hooks.sh .githooks/pre-push .githooks/post-merge .githooks/post-rewrite`
- `bash scripts/cos-deps-maintain --mode doctor --no-install-plan --json`
- `.venv/bin/python -m pytest tests/unit/test_dependency_maintenance.py tests/audit/test_dependency_maintenance_integration.py -q`
- `python3 scripts/derived_artifact_gate.py`

```bash
python3 -m pytest tests/unit -q
```

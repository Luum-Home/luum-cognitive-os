---

adr: 130
title: Suspend All GitHub Actions Workflows — Preserve as .disabled Until Local-CI Migration
status: accepted
implementation_status: implemented
date: 2026-05-03
supersedes: []
superseded_by: null
implementation_files:
  - .github/workflows/ci.yml.disabled
  - .github/workflows/claude-interactive.yml.disabled
  - .github/workflows/claude-issue-triage.yml.disabled
  - .github/workflows/claude-pr-review.yml.disabled
  - .github/workflows/cos-config-audit.yml.disabled
  - .github/workflows/cross-platform.yml.disabled
  - .github/workflows/go-quality.yml.disabled
  - .github/workflows/primitive-gap-audit.yml.disabled
  - .github/workflows/test-lanes.yml.disabled
  - .github/workflows/test-quality.yml.disabled
  - .github/workflows/weekly-public-metrics.yml.disabled
tier: maintainer
tags: [ci, billing, github-actions, dx, future-work]
---

# ADR-130: Suspend All GitHub Actions Workflows — Preserve as .disabled Until Local-CI Migration

## Status

Accepted.

## Update — 2026-05-03 (same day)

The original decision suspended only the three Claude API workflows
plus `cross-platform.yml`. After confirming with the maintainer that
the GitHub account has no payment method available and the goal is
**zero spend until self-hosted CI is in place**, the scope was
extended to **all eleven workflows**.

Linux-only workflows alone could in theory fit the free-tier 2,000
minutes/month budget, but:

- The maintainer pushes to `main` ~50 times/day. `ci.yml` and
  `test-lanes.yml` trigger on every push to main and would burn the
  free-tier quota in roughly one week.
- Once the quota is exhausted, every workflow's job fails to start
  with the same "spending limit" message — the same failure mode
  this ADR was created to address.
- The cleanest posture under "no payment available" is total
  suspension. Restoration is per-file rename when self-hosted CI
  is ready.

The full list of suspended files is in `implementation_files`.

## Context

GitHub Actions billing on this private repository hit its spending limit
on 2026-05-02. The user-visible symptom: every PR check failed in 2–13s
with the message *"The job was not started because recent account
payments have failed or your spending limit needs to be increased"*.

Triaging the workflows revealed that three of the eleven YAML files
invoke the Anthropic Claude API on every PR or issue event:

- `.github/workflows/claude-interactive.yml`
- `.github/workflows/claude-issue-triage.yml`
- `.github/workflows/claude-pr-review.yml`

These are the workflows whose minute consumption is least predictable
because they spawn long-running Claude API calls. They are also the
ones whose value is most easily reproduced locally — the same
analysis happens during normal Claude Code sessions on the
maintainer's machine.

The remaining eight workflows (shellcheck, pytest, go quality, audit,
test lanes, etc.) cover ground that is **also** reproduced locally by
the existing COS hook surface, but those workflows produce real
matrix coverage (Linux + macOS + Docker) that is genuinely harder to
replicate on a single maintainer's machine. They stay for now.

## Decision

Disable the three Claude API workflows by **renaming them to
`.disabled`**. GitHub Actions only auto-discovers files matching
`.yml` / `.yaml` under `.github/workflows/`, so a `.disabled` extension
takes them out of execution without losing the YAML content.

This is preferred over `gh workflow disable` because:

1. `gh workflow disable` toggles UI-only state. A future commit that
   touches the YAML or a forced re-enable can restore execution.
2. A filesystem rename is version-controlled and is visible in
   `git diff` reviews. Re-enabling requires an explicit rename back
   to `.yml`, which a reviewer can catch.
3. The `.disabled` files remain in the repo as documentation. Nothing is
   lost; the workflows are recoverable with `mv *.disabled *.yml`.

## Acceptance Criteria

1. `.github/workflows/` contains no file matching `claude-*.yml`.
2. `.github/workflows/` contains the three `.disabled` companions.
3. New PRs and issue events do not trigger Claude-API workflow runs.
4. The eight non-Claude workflows continue to run unchanged.
5. ADR is committed in the same change as the rename so future
   readers find the decision record next to the artifacts it
   describes.

## Border Cases

- **Re-enabling on demand.** Run `mv .github/workflows/claude-*.yml.disabled
  .github/workflows/claude-*.yml` and commit. No code change required.
- **Dependabot or similar bots updating the YAML.** Bots match on
  `*.yml`, so `.disabled` files are ignored. No bot churn.
- **Workflow YAML referenced by docs.** Update doc references to point
  at the `.disabled` filename so the docs do not claim the workflows are
  active.
- **Branch protection rules requiring those checks.** Verify in
  GitHub repo settings that the three Claude workflows are not in the
  required-status-checks list before merging this ADR. Otherwise the
  base branch becomes unmergeable.

## Consequences

**Positive.**

- GitHub Actions billing on Claude API workflows drops to zero.
- The maintainer can run the same analyses inside a Claude Code
  session on demand, with no per-PR cost.
- Future readers of the repo see the workflows in `.disabled` form and
  understand the suspension was deliberate.

**Negative / trade-offs.**

- PRs no longer get the automated Claude PR review comment. The
  maintainer who already reviews each PR by hand is unaffected; an
  external contributor scenario does change, but this repo currently
  has a single maintainer.
- Issue triage automation goes manual.
- The interactive workflow that responded to `@claude` mentions in
  comments stops responding. Existing mentions on closed issues are
  unaffected.

## Alternatives Rejected

- **Pay GitHub more.** Increases recurring spending without addressing
  the structural cost driver (Claude API calls on every PR). Fine as a
  short-term unblocker, weak as a long-term posture.
- **`gh workflow disable` only.** UI-state-only toggle that can be
  silently re-enabled. Filesystem rename is version-controlled.
- **Delete the YAMLs entirely.** Loses recovery information. The
  `.disabled` form keeps the original configuration documented in the repo
  for future restoration or migration.

## Future Work

Tracked in engram under `backlog/local-ci-migration` (this ADR is the
first reference). Two options are on the table for the eight
remaining workflows once the maintainer has cycles for it:

1. **Self-hosted runner on the maintainer's Mac.** Registers as a
   `launchd` service, no GitHub Actions minutes consumed. Risk:
   jobs queue indefinitely while the machine is asleep. Mitigated
   by running `caffeinate` while the runner is online.
2. **Pre-push CI hook that consolidates the eight workflows into a
   single `scripts/cos-ci-local.sh`.** Push only succeeds if local
   CI passes. Loses cross-platform matrix coverage. Aligns with the
   existing project philosophy of hook-enforced governance.

A combined approach (self-hosted as primary, hosted as paid fallback)
remains an option but adds configuration complexity to eleven
workflows that would each need a `runs-on: [self-hosted,
ubuntu-latest]` matrix.

## Cross-references

- Source: `docs/reports/dx-assessment-2026-05-02.md` (CI failure
  cluster, originally attributed to test-suite drift).
- Related: ADR-128 (data-layer integrity), ADR-129 (safe worktree
  removal). All three are products of the 2026-05-02 DX audit.
- Backlog topic: `backlog/local-ci-migration`.

## Alternatives rejected

- Leave the ADR without an alternatives section — rejected because ADR-067+ audit contracts require a falsifiable record of considered options.

## Verification

```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```


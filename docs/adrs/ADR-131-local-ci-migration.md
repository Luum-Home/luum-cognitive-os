---

adr: 131
title: Local-CI Migration — Three-Layer Architecture to Replace GitHub Actions
status: accepted
implementation_status: implemented
date: 2026-05-03
supersedes: []
superseded_by: null
implementation_files:
  - scripts/cos-ci-local.sh
  - git-hooks/pre-push
  - scripts/install-git-hooks.sh
  - scripts/cos-weekly-config-audit.sh
  - scripts/cos-weekly-primitive-gap.sh
  - scripts/cos-weekly-public-metrics.sh
  - scripts/install-launchd-jobs.sh
  - scripts/cos-pr-review.sh
tier: maintainer
tags: [ci, local-execution, dogfood, dx]
---

# ADR-131: Local-CI Migration — Three-Layer Architecture to Replace GitHub Actions

## Status

Accepted. Implemented in the same PR that lands this ADR. Companion
to ADR-130 (which suspended all eleven workflows to a `.disabled`
state pending this migration).

Implementation files are listed in the frontmatter and are present
in the working tree alongside this ADR.

## Context

ADR-130 suspended all eleven GitHub Actions workflows because the
GitHub account has no payment method and the free-tier minute budget
was burning faster than the maintainer's commit cadence allowed.

The honest follow-up question — *"can we replace all of those locally?"* —
has the honest answer: **yes, every one of them**. Six categories of
workflow with six categories of local replacement, none of which
require new infrastructure that does not already exist.

This ADR captures the target architecture so that when the maintainer
returns with cycles to do the work, the design decisions are not
re-litigated.

## Decision

Three layers, each owning a category of trigger.

### Layer 1 — Pre-push hook

`git-hooks/pre-push` (tracked) invokes `scripts/cos-ci-local.sh`.
The hook is wired up via `git config core.hooksPath git-hooks`,
installed by running `bash scripts/install-git-hooks.sh` once after
clone. The script
consolidates the seven ubuntu-only workflows that previously ran on
push or pull_request:

- `ci.yml` (pytest)
- `test-lanes.yml` (test lane orchestration)
- `test-quality.yml` (test-quality audit)
- `go-quality.yml` (`gofmt -l` + `go vet`)
- `cos-config-audit.yml` (config drift audit)
- `primitive-gap-audit.yml` (aspirational classification)
- `weekly-public-metrics.yml` (when the maintainer wants a fresh
  metrics snapshot before pushing)

If any check fails, the push aborts. Exit semantics match standard
git pre-push contract. `--no-verify` remains available as the
explicit operator escape.

Feedback target: **10–30 seconds** for the common path, replacing
the 2–5 minute cold-start of GitHub Actions. The local script
operates on the actual checked-out tree, so there is no clone,
runner provisioning, or cache-restore overhead.

### Layer 2 — launchd schedules on the maintainer's Mac

The three weekly workflows previously triggered via cron-style
schedules become `launchd` plists generated and installed by
`scripts/install-launchd-jobs.sh`. The script generates the plists
into `~/Library/LaunchAgents/` rather than committing them to the
repo, so the absolute repo path is resolved at install time and
the source-of-truth is the install script plus the three wrapper
scripts it invokes:

- `scripts/cos-weekly-config-audit.sh` — Mondays 09:00
- `scripts/cos-weekly-public-metrics.sh` — Mondays 12:00
- `scripts/cos-weekly-primitive-gap.sh` — Mondays 12:30

(All times are local Mac time; the original workflows used UTC, but
launchd's `StartCalendarInterval` uses local time.)

`launchd` runs the job at the next opportunity if the Mac was asleep
at the scheduled moment, so a Monday-morning sleep does not skip the
audit. Logs land at `~/Library/Logs/cos/<name>.{out,err}.log`.

Outputs land under `.cognitive-os/reports/weekly/<date>/` for the
config audit and under `docs/reports/` for the primitive-gap and
public-metrics outputs (matching the directories the workflows used).

### Layer 3 — CLI on-demand for Claude review

The three Claude API workflows
(`claude-interactive.yml`, `claude-issue-triage.yml`,
`claude-pr-review.yml`) become a single `scripts/cos-pr-review.sh`
CLI invoked manually:

```bash
scripts/cos-pr-review.sh <PR-number>
```

The script:

1. `gh pr diff <PR>` to capture the change.
2. Runs the analysis locally — either spawns a Claude Code session
   targeted at the diff, or invokes a local agent against the diff
   text. The maintainer already does this manually for every PR
   they review.
3. `gh pr comment <PR> --body-file <report>` to post the review
   back to the PR for visibility and audit trail.

Issue triage and `@claude` mention responding fold into the same
script with subcommands or remain explicitly manual.

### Cross-platform coverage

`cross-platform.yml` ran a `macos-latest` + `ubuntu-latest` matrix.
Replacement is the maintainer's Mac (native macOS) plus
`docker run --rm ubuntu:latest <cmd>` for Linux coverage. Run from
the same `cos-ci-local.sh` when needed. Acceptable approximation
for a project whose primary target runtime is macOS Claude Code.

## Acceptance Criteria

1. `scripts/cos-ci-local.sh` exists and exits non-zero if any of the
   seven ubuntu-equivalent checks fails.
2. `.git/hooks/pre-push` invokes the script and aborts the push on
   non-zero exit.
3. The three `launchd` plists are present in `launchd/` with
   `Label`, `ProgramArguments`, `StartCalendarInterval`, and
   `StandardOutPath`/`StandardErrorPath` set so the operator can
   debug when a job fails.
4. `scripts/cos-pr-review.sh` accepts a PR number, captures diff,
   runs analysis, and posts a comment back to the PR.
5. Wall-clock for `cos-ci-local.sh` end-to-end on a clean tree:
   under 60 seconds. (The seven workflows together take 5–10
   minutes on hosted runners.)
6. README documents the new flow: "push → local CI runs → PR review
   on demand". The doc replaces any prior reference to GitHub
   Actions checks as the gating mechanism.
7. The eleven `.disabled` workflow files remain in repo as
   documentation and recovery artifacts. They are not deleted.

## Border Cases

- **Mac asleep when a launchd job fires.** `launchd` reschedules
  on wake. Job runs late but runs. No silent skips.
- **Pre-push hook hangs.** Operator interrupts with `Ctrl+C`. Push
  is aborted, no partial state on remote. `--no-verify` available
  as the explicit escape.
- **Operator runs on a non-Mac machine.** `launchd` is macOS-only;
  on Linux fall back to `cron` or `systemd` user units. The plists
  document the schedule; equivalent crontab lines are easy to derive.
- **A check needs an environment the local Mac does not have**
  (e.g. Postgres for an integration test). The check moves into a
  `docker run` block in `cos-ci-local.sh`. Long-term, the same
  approach can layer in any service the previous GHA workflows
  depended on.
- **PR review script needs Anthropic API access.** Either uses the
  maintainer's local Claude Code session (no API cost) or an
  explicit `ANTHROPIC_API_KEY` from `~/.config/cos/secrets`
  (operator-controlled, not in repo).
- **The maintainer's machine is the SPOF.** Documented honestly
  below. Acceptable for a single-maintainer project; the moment
  a second maintainer joins, the architecture must be revisited
  (probably toward self-hosted runner with explicit failover).

## Consequences

**Positive.**

- Zero per-PR cost. No GitHub Actions spend, ever.
- Faster feedback: 10–30 seconds vs 2–5 minutes of hosted-runner
  cold start.
- No "works on my machine, fails in CI" divergence — the local
  script *is* the CI.
- Works fully offline. Push fails when offline (correct), but
  every check that was supposed to run before push has already
  run.
- Coherent with the project's stated philosophy of hook-enforced,
  locally-executable governance. Applying that to the project's
  own CI is the long-form dogfood.

**Negative / trade-offs.**

- **Single-maintainer SPOF.** If the maintainer's machine breaks
  or is unavailable, no CI runs. For a solo dev this is the same
  property `git commit` already has; for a team it would be
  unacceptable.
- **No third-party verification.** A bug or compromise in the
  local hook goes undetected by an external check. Solo dev
  accepts this; team would not.
- **Cross-platform via Docker is ~95% fidelity.** Glibc / kernel
  differences not exercised. Acceptable for a project whose target
  runtime is macOS Claude Code; would not be acceptable for a
  cross-platform library shipping to enterprise customers.
- **Loss of GitHub PR check status badges.** Replaceable with
  `gh pr comment` posting a verification report. The badge UX is
  gone; the audit trail remains.
- **Manual trigger for issue triage and `@claude` mentions.**
  Acceptable because the maintainer already responds manually to
  these.

## Alternatives Rejected

- **Self-hosted runner only.** Solves billing but inherits all of
  GitHub Actions' overhead (queue, runner provisioning, log
  shipping) for a solo dev who could just run the script directly.
  Adds a daemon to babysit. Rejected as over-engineered for the
  use case.
- **Pay GitHub.** Out of scope — the maintainer has no payment
  method on the account, which is the reason ADR-130 was written
  in the first place.
- **Hybrid GitHub Actions + local.** Maintains two CI systems with
  divergent semantics. Rejected for the same reason as splitting
  governance between hooks and CI: every duplication creates a
  drift surface.
- **Disable CI entirely with no replacement.** Rejected because
  the project's value proposition includes hook-enforced
  governance. Removing the gates would contradict the architecture
  ADR-130 is meant to preserve.

## Cross-references

- ADR-130 — suspended the eleven workflows that this ADR migrates.
- `docs/reports/dx-assessment-2026-05-02.md` — the assessment that
  surfaced the GitHub Actions billing issue.
- Future engram topic key: `backlog/local-ci-migration` — already
  noted as the tracking key from prior sessions.

## Alternatives rejected

- Leave the ADR without an alternatives section — rejected because ADR-067+ audit contracts require a falsifiable record of considered options.

## Verification

```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```


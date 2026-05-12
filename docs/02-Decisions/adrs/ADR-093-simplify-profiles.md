---
adr: 93
title: Simplify Install Profiles — Collapse 3-Tier System to `default` + `--full`
status: accepted
implementation_status: partial
date: '2026-04-30'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: implementation evidence plus partial/deferred/future signal
partial_remaining: any follow-up install step.
remaining_in_scope: true
partial_remaining_basis: explicit body remaining signal
---

# ADR-093: Simplify Install Profiles — Collapse 3-Tier System to `default` + `--full`

<!-- Renumbered-from: ADR-002 (docs/04-Concepts/architecture/harness-adoption-gap/ADR-002-simplify-profiles.md) -->
<!-- Renumbered-to: ADR-093 (ADR-087 migration, 2026-04-30) -->

## Status

Accepted (2026-04-16)

## Context

As of 2026-04-16 the installer exposed a three-tier profile system: `--lean`,
`--standard`, `--full`, with an auto-detection fallback that chose `lean` when
the target directory was empty or not a git repo. Internally there was a fourth
alias (`--minimal`) used by `cos-init.sh` for what the user-facing flag called
`--lean`.

An empirical fresh-install simulation (`bash install.sh` in a clean `/tmp`
directory) surfaced two problems:

1. **Zero-skill default UX.** Auto-detection picked `lean` for empty/new
   repositories. The `--lean` profile installed **zero** skills under
   `.claude/skills/`. Users who expected core skills like `/compose-prompt`,
   `/plan-feature`, `/auto-refine`, etc. to exist after the first install got
   none — the harness showed nothing, the orchestrator inlined logic that
   should have been skill calls, and the "vanilla value" of the OS was invisible
   until the user discovered they needed to re-run with `--standard` or
   `--full`. This is the opposite of what vanilla `git`, `gh`, and `claude`
   do: those tools work out-of-the-box with sensible defaults and no flags.

2. **Cognitive load for no payoff.** The three-way choice
   (`lean` / `standard` / `full`) required the user to model what each tier
   meant before their first session. There was no user-visible win from having
   a middle tier: `standard` was either "good enough" (making `lean` pointless)
   or "not good enough" (making `full` the only answer). The auto-detection
   heuristic (`has_git && src_count >= 5`) was a partial mitigation that
   shifted the problem rather than solving it — users still had to learn the
   three names to override or debug the choice.

The ADR-001 ghost-skill analysis already identified ten skills that deliver
most of the immediate "vanilla value": `compose-prompt`, `exhaustive-prompt`,
`agent-dashboard`, `auto-refine`, `verification-before-completion`,
and `cos-status`. Those ten cover prompt composition, agent supervision,
planning, verification, and status/observability — exactly the primitives an
orchestrator needs the first time it runs the OS.

## Decision

Collapse the installer surface to two tiers that match the vanilla DX of
`claude`, `gh`, and `git`: one sensible default that requires no flags, and
one power-user override for maximum install.

- **`default`** (no flag). Installs the ten curated "vanilla value" skills
  listed above into `.claude/skills/`, copies the 14 core rules
  (`RULES-COMPACT.md` plus the set already hard-coded in `self-install.sh`
  as `CORE_RULES`) into `.claude/rules/cos/`, and wires the pre-existing
  standard hook set (what was previously called the `standard` tier:
  ~29 hooks including rate-limiter, agent-prelaunch, auto-verify, dod-gate,
  completion-gate, mlflow-sync, etc.). Target token overhead remains
  ~8000 tokens per session.

- **`--full`**. Installs every skill, every rule, and every hook available in
  the repo. Intended for mature projects and for contributors working on
  Cognitive OS itself. Target token overhead ~142000 tokens per session.

Auto-detection is removed. There is no heuristic to train; the default
install is always the same, and `--full` is always opt-in.

## Alternatives rejected

- Keep the previous behavior unchanged — rejected because the audit or runtime failure would remain deterministic and would continue masking real regressions.
## Consequences

### User-facing

- `install.sh` without flags produces a working OS with 10 skills visible to
  the harness immediately after the first session — the orchestrator can
  invoke `/compose-prompt`, `/plan-feature`, `/auto-refine`, etc. without
  any follow-up install step.
- Help text shrinks: `install.sh --help` only documents `--full`, `--from`,
  and `--force`. The mental model the user has to hold is two values, not
  four.
- **BREAKING CHANGE**: users who previously ran `install.sh --lean` or
  `install.sh --standard` will see those flags rejected with a migration
  message pointing to this ADR. The fix is to drop the flag (for what used
  to be `standard`) or accept the slightly richer default (for what used to
  be `lean`). The 14 core rules kept by the new `default` are a superset of
  what `lean` delivered.
- `COS_PROFILE=lean` and `COS_PROFILE=standard` environment values are
  rejected with the same migration message. `COS_PROFILE=full` continues to
  work.

### Installer-side

- `scripts/apply-efficiency-profile.sh` accepts `default` and `full`, and
  silently maps legacy names (`lean`, `standard`, `minimal`) to `default`
  with a stderr note. This keeps existing deployments working after they
  pull the new version — their `cognitive-os.yaml` need not be rewritten
  immediately.
- `scripts/cos-init.sh` accepts `--default` and `--full`, and rejects
  `--minimal` / `--standard` / `--lean` with migration guidance. `install.sh`
  always passes `--default` or `--full`, so the rejection path only fires
  for direct users.
- `scripts/generate-project-settings.sh` accepts `--default` / `--full` and
  silently aliases `--minimal` / `--standard` to `--default` so the
  migration window does not break existing `auto-update-projects.sh`
  invocations that still pass the old flags.
- `scripts/auto-update-projects.sh` reads the mode recorded in the
  installations registry and rewrites legacy values (`lean`, `standard`,
  `minimal`) to `default` before invoking `cos-init.sh`. Projects installed
  under the old flags auto-upgrade on the next scheduled run of the update
  cascade — no manual intervention required.
- `cognitive-os.yaml` now ships with `efficiency.profile: default` and the
  `profiles:` map only defines `default` and `full`. The reader in
  `self-install.sh` and `apply-efficiency-profile.sh` treats unknown legacy
  values as `default` rather than erroring.

### Ecosystem

- Documentation references that mentioned `--lean` or `--standard` need to
  be updated in a follow-up pass (tests, wizard flows, tutorials). This ADR
  does not block that work — legacy flags still work in the generator
  (aliased) and the registry migration means no external project needs a
  manual fix.
- `cos-status` (the upcoming UX5 skill listed in `DEFAULT_SKILLS`) does not
  yet exist as a skill directory — only as `scripts/cos-status.sh`. The
  installer skips missing skill names silently, so the install succeeds with
  9 skills installed until the skill wrapper is authored. Once the
  directory exists, the next install cycle picks it up without any code
  change.

## Migration Guidance

For end users:

| Before | After |
|---|---|
| `install.sh` (auto-detected to `lean` in empty dir) | `install.sh` (always `default`) |
| `install.sh --lean` | `install.sh` — note the default now installs 10 skills, a strict superset of lean |
| `install.sh --standard` | `install.sh` — same hook set, plus 10 skills |
| `install.sh --full` | `install.sh --full` — unchanged |
| `COS_PROFILE=lean bash install.sh` | rejected with guidance; run without the env var |
| `COS_PROFILE=standard bash install.sh` | rejected with guidance; run without the env var |
| `COS_PROFILE=full bash install.sh` | unchanged |

For existing installations:

- Run `bash scripts/cos-update.sh` (or wait for the git post-merge hook to
  fire `auto-update-projects.sh`). The registry entry's `mode` field is
  normalized to `default` on the next cascade.
- If `cognitive-os.yaml` contains `efficiency.profile: lean` or
  `efficiency.profile: standard`, the OS continues to work — both map to
  `default` at runtime. Rewriting the value is optional; the next time the
  file is regenerated it will say `default`.

**Cross-references:** ADR-001 (harness skill sync path),
`scripts/apply-efficiency-profile.sh`, `install.sh`, `scripts/cos-init.sh`,
`scripts/auto-update-projects.sh`, `cognitive-os.yaml`.

## Verification

Run the focused contract for this decision:

```bash
python3 -m pytest tests/behavior/test_efficiency_profiles.py -q
```

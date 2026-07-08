---
type: reference-synthesis
source: docs/08-References/migration-from/from-vanilla-claude-code.md
provenance: "Onboarding/migration guide for users of stock Claude Code who want to add Cognitive OS governance without changing how Claude reasons or how they interact with it."
---

## What it is

A migration guide covering what changes when Cognitive OS is installed on top of vanilla Claude Code, the install/uninstall procedure, update mechanics, and an FAQ addressing common adoption concerns (behavior change, cost overhead, disabling, settings conflicts, hook failure modes).

## Key mechanics

- **Core promise**: COS does not change how Claude reasons or how the user interacts with it — it adds hooks firing at lifecycle points Claude Code already exposes (session start, before/after tool calls, session end).
- **What changes after install**: `settings.json` gets ~14 governance hooks registered; a `.cognitive-os/` directory (rules, skills, hooks, metrics storage) and `cognitive-os.yaml` config appear in the project; hooks fire automatically from the next session with no manual invocation. The Claude Code UI, model selection, and existing `CLAUDE.md` are untouched unless the user opts into `/cognitive-os-init`.
- **Install**: prerequisites are bash, git, Python 3.10+. Remote (`curl | bash install.sh --harness=claude`) or local (`/path/to/repo/install.sh --harness=claude`) install, then verify via `cos-status.sh` (expects `PASS active settings driver is valid` and `PASS wired hooks exist`). Optional step 4, `/cognitive-os-init`, detects the project stack (Node/Go/Python/etc.) and writes project-specific rules/skills — explicitly optional; the governance layer works without it.
- **Keeping updated**: `scripts/setup-git-hooks.sh` installs a git hook that re-runs the installer for all registered projects on `git pull` in the COS source repo; manual re-runs of `install.sh` also work.
- **Uninstall**: canonical path is `scripts/uninstall.sh` (removes `.cognitive-os/`, reverts `settings.json`). Manual fallback (Option B): delete `.cognitive-os/` and manually strip COS hook entries from `settings.json`'s hooks arrays.
- **FAQ answers**: reasoning is unchanged; the most visible change is a Trust Report appended to some agent completions (from `trust-score-validator.sh`); hook overhead is <200ms per tool call typical, no external API calls in the governance layer itself (cites SLO 2 in `rules/so-slo.md`); temporary disable via `apply-efficiency-profile.sh minimal`, restore via `... standard`, or remove a specific hook entry; the installer merges rather than overwrites `settings.json` (verify via `git diff`); each hook has advisory mode (exit 0, log-only) and blocking mode (exit 2) — default profile uses advisory except for security-critical paths (credential guard, license guard); a hook that exits 1 is treated as advisory.

## Relations & where used

Referenced by `from-hermes.md` as the canonical install-detail source. References `rules/so-slo.md` (SLO 2, hook latency budget) and the efficiency-profile scripts (`apply-efficiency-profile.sh`).

## Status / caveats

The document flags its own gap: `scripts/uninstall.sh` is described as "the canonical path" but the doc notes "if it does not exist in the version you installed, use Option B" — i.e., the uninstall script's presence is not guaranteed across all install versions, tracked as a future-release fix in `.cognitive-os/plans/`. Everything else in the guide describes stable, already-shipped install/hook behavior rather than aspirational features.

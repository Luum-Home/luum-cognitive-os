---
type: methodology-synthesis
source: docs/05-Methodology/onboarding/walkthrough.md
provenance: "Captures the canonical clone-to-first-demo path so a hostile auditor can reproduce every step on a clean machine in under 10 minutes."
---

## What it is

A 9-step, timed walkthrough from `git clone` to a verified, hook-protected Cognitive OS install with an audited demo run. It is the canonical answer to "what do I do after cloning?" and is referenced by item M2 of the pre-public-readiness checklist. Distilled from a live captured transcript into public-safe expected-output snippets (raw transcripts are not committed because they can leak local usernames/paths).

## Key mechanics

- **Prerequisites**: Git 2.30+, Bash 4+, Python 3.10+ are required for steps 1-7; Go 1.21+ and Claude Code only matter from step 8 onward.
- **The 9 steps**: (1) clone, (2) read README's "what it is/isn't" + 5-Minute Demo sections, (3) optional `install.sh --harness=claude` into a sample project, (4) `cos-status.sh` verify (expects `Skills: 168 exposed`, `Hooks: 159 wired`, `Rules: 0 source` on fresh clone, `Health: OK`), (5) `cos-status.sh --verbose` for full transparency (slowest step, ~38s cold), (6) `demo-governance.sh` fires 4 real hooks with crafted payloads — no live API calls — expecting all `[OK]` lines, (7) `DRY_RUN=true cos-history-sanitization-smoke.sh` proves the destructive history-sanitization path is gated behind explicit env vars, (8) read CONTRIBUTING/CHANGELOG, (9) branch to next docs based on goal (setup, migration, ADRs, demo paths, comparisons, readiness audit).
- **Measured timing**: steps 4-7 measured live at 52s total; full walkthrough estimated at ~7 minutes, under the 10-minute goal.
- Includes a failure-mode table mapping symptoms (e.g., `python3: command not found`, `Health: FAIL`, hangs >60s in step 5) to causes and fixes.

## Relations & where used

- Canonical path linked from the pre-public-readiness checklist (`docs/09-Quality/legal/pre-public-readiness-checklist.md`, item M2).
- Points onward to `docs/00-MOCs/entrypoints/getting-started.md`, `docs/08-References/migration-from/from-vanilla-claude-code.md`, ADR-001/093/131, `docs/09-Quality/manual-tests/proof-paths.md`, and `docs/08-References/root/vs-alternatives.md`.
- Exercises `scripts/cos-status.sh`, `scripts/demo-governance.sh`, `scripts/cos-history-sanitization-smoke.sh`, and `install.sh`.

## Status / caveats

- The public GitHub URL (`github.com/luum-home/luum-cognitive-os`) is reserved but **not yet published** — step 1 will fail for external readers until launch; internal reviewers must use a local mirror.
- The Asciicast/screencast is explicitly pending public-release cut.
- Step 4's expected output (`168 skills`, `159 hooks`, `35 packages`) is a point-in-time snapshot from one captured transcript on an *installed* project, not the self-hosted repo — these counts will drift and should not be treated as current totals (compare against `hooks.md`, which describes the self-hosted repo as having 46 registered / 94 total hook scripts, a different number for a different install target).

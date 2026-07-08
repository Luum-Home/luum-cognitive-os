---
type: quality-synthesis
source: docs/09-Quality/root/testing-cognitive-os-suite.md
provenance: "Documents the Cognitive OS's own 3-layer test pyramid (infrastructure, behavior, quality) and how to invoke each layer via cos-test scripts or the /cognitive-os-test skill."
---

## What it is

Reference doc for the SO-internal `.cognitive-os/tests/` suite: a 3-layer pyramid (Layer 1 deterministic infrastructure checks, Layer 2 semi-deterministic behavior simulations, Layer 3 LLM-evaluated quality tests via promptfoo), distinct from the main `tests/` pytest suite covered in `testing.md`.

## Key mechanics

- **Directory layout**: `.cognitive-os/tests/{infra,behavior,quality}/`, runner scripts at `.cognitive-os/scripts/{test-cognitive-os.sh, test-cognitive-os-full.sh}`, skill at `.cognitive-os/skills/cognitive-os-test/SKILL.md`, results appended to `.cognitive-os/metrics/test-results.jsonl`.
- **Layer 1 (Infrastructure)** — fully deterministic, no external deps beyond bash/python3/optionally yq: `test-hooks.sh` (existence, permissions, syntax, registration; detects orphan/phantom hooks), `test-skills.sh` (SKILL.md frontmatter + CATALOG.md sync), `test-rules.sh` (rule files referenced in RULES-COMPACT.md and vice versa), `test-config.sh` (YAML validity of cognitive-os.yaml/squad/customization configs), `test-docker.sh` (container/healthcheck status, non-blocking), `test-metrics.sh` (JSONL validity).
- **Layer 2 (Behavior)** — mock JSON piped to hooks via stdin: `test-hook-triggers.sh`, `test-private-mode.sh` (flag-based gating), `test-phase-system.sh` (cycles through reconstruction/stabilization/production/maintenance, verifies phase-appropriate rule injection, restores config), `test-resource-governor.sh` (budget thresholds against mock cost data: empty/low=allow, 80%+=downgrade warning, 100%+=block).
- **Layer 3 (Quality)** — LLM-evaluated via promptfoo, requires an explicit eval provider key (e.g. `OPENAI_API_KEY`): tests endpoint-creation framework adherence, handler patterns, DTO location, code-review substance, phase awareness, gate enforcement, entity patterns, cross-service comms.
- Invocation: `bash .cognitive-os/scripts/test-cognitive-os.sh` (Layer 1 only), `bash .cognitive-os/scripts/test-cognitive-os-full.sh --skip-quality` (Layers 1+2), same script without the flag (all layers), or `/cognitive-os-test` skill.
- Test-results schema example includes per-layer pass/fail/warn counts and an overall `pass_rate`.
- Adding tests: infra tests use `pass()/fail()/warn()` + summary lines + exit codes, auto-discovered; behavior tests mock JSON via stdin with `trap ... EXIT` cleanup; quality tests are promptfoo cases with `contains`/`not-contains`/`contains-any` assertions.

## Relations & where used

- Distinct from (and referenced alongside) `testing.md`, which documents the ~5639-test pytest suite in `tests/` run via `cos-test` (the Go/Bubbletea TUI). This doc's suite lives entirely under `.cognitive-os/tests/` and is a separate, smaller, SO-internal self-check layer.
- References `constitutional-gates.md` conceptually (gate enforcement tests in Layer 3).

## Status / caveats

No explicit dates or version pins; describes current-state architecture as of the source doc. No inconsistencies found within the file itself, but note the naming overlap with `testing-cognitive-os.md` (a different, research-oriented doc) and `testing.md` (the pytest suite doc) — three similarly named files cover three different testing surfaces.

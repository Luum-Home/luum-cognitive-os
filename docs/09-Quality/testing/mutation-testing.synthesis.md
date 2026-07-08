---
type: quality-synthesis
source: docs/09-Quality/testing/mutation-testing.md
provenance: "Explains mutation testing (cosmic-ray) as the objective measure of whether tests verify real behavior versus structural-only checks, and documents the CI gate and thresholds."
---

## What it is
A focused guide to mutation testing as the Cognitive OS's technique for quantifying whether tests actually verify behavior, versus being "structural-only" (existence/string checks). Explains the mechanism, why it was adopted, the CI gate, local usage with `cosmic-ray`, and guidelines for writing mutation-killing tests.

## Key mechanics
- **Mechanism:** mutates source (`>`→`<`, deletes returns, `True`↔`False`, etc.) and checks whether tests fail. A failing test "kills" the mutant; a passing-through mutant "survives," indicating the test doesn't verify that behavior.
- **Motivation:** many codebase tests were found to be structural-only (file existence, config string content, section headers) — these provide zero protection against logic bugs. Mutation testing quantifies the gap objectively.
- **Baseline:** ~34% kill rate on `lib/rate_limiter.py`. Target for new code: 60%+.
- **CI gate (`.github/workflows/test-quality.yml`), two checks per PR:** (1) structural test detector — static analysis blocking merge if new tests are purely structural; (2) mutation testing via cosmic-ray on changed `lib/*.py` files (max 5 per PR for speed) — blocks merge below 40% kill rate.
- **Local commands:** `python scripts/check_test_quality.py [file|--ci]` for the structural detector; `cosmic-ray init/exec` + `cr-report` for mutation runs, with a documented single-module `.cosmic-ray.toml` recipe (`module-path`, `timeout=30`, targeted `test-command`, local distributor).
- **Kill-vs-survive example pair:** a structural test asserting only `Path(...).exists()` survives all mutations; a behavioral test asserting boundary behavior (`rl.allow()` returning `True`/`True`/`False` across calls) kills boundary mutations.
- **Guidelines for mutation-killing tests:** assert on return values, assert on exceptions via `pytest.raises`, assert on state changes (attributes, DB rows, file contents post-operation); avoid asserting only on file existence or source-string containment.
- **Thresholds table:** mutation kill rate (new code) 40% min / 60%+ target; structural-only test files: blocked / 0.

## Relations & where used
- `docs/09-Quality/testing/README.md` — parent testing guide; this doc is the detailed reference it links to for mutation testing.
- `.github/workflows/test-quality.yml` — the CI workflow enforcing both gates described here.
- `.cosmic-ray.toml` — the project-wide mutation config referenced for the full-run path.
- `scripts/check_test_quality.py` — the structural-test static analyzer.

## Status / caveats
- The 34% baseline is specific to `lib/rate_limiter.py` only, not a project-wide figure — do not generalize it as the whole codebase's kill rate.
- No explicit "last updated" date in this document; treat the 34%/40%/60% figures as current as of the adjacent `README.md` (dated 2026-04-16) unless a fresher source is found.

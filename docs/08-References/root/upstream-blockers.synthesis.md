---
type: reference-synthesis
source: docs/08-References/root/upstream-blockers.md
provenance: "Living tracking ledger of dependency-upgrade work that is ready to execute but blocked on third-party upstream releases or resolver conditions."
---

## What it is

A tracking file (last reviewed 2026-05-04) enumerating work items that are implementation-ready but blocked on external release events, each with a trigger condition, the action to take once unblocked, and an effort estimate.

## Key mechanics

- **Format per entry**: Where (affected files/paths), Trigger (the upstream condition to watch), Action (what to do once unblocked), Estimate, First-flagged date, and sometimes a Last-proof date documenting the most recent verification attempt.
- **Active blockers**:
  - `default_backend()` cleanup in `hermes-agent` (3 files) — blocked on `cryptography` package dropping the deprecated symbol (announced for 49.0.0; at 47.x as of 2026-04-27). ~30 min mechanical fix.
  - `rich` 14 -> 15 — blocked on `cognee`/`instructor` allowing `rich>=15`; last proof (2026-05-04) shows `uv lock` still fails because `luum-cognitive-os[memory]` pulls `cognee` -> `instructor` constrained to `rich>=13.7.0,<15.0.0`. ~15 min once unblocked.
  - `wrapt` 1 -> 2 — blocked on OpenTelemetry/OpenInference/`deprecated`/`arize-phoenix` transitive deps validating `wrapt 2.x`; last proof (2026-05-04) notes the resolver *can* accept `wrapt>=2` already, but the bump is held pending targeted instrumentation integration tests since no first-party code imports it. ~30 min plus monitoring.
  - Setuptools 82 lock-churn — blocked on the torch/sentence-transformers semantic stack supporting `setuptools>=82`, or an explicit decision to downgrade `torch 2.11.0`/CUDA 13 to `torch 2.10.0`/CUDA 12; action is `uv lock --upgrade-package 'setuptools>=82'` applied only if the diff is setuptools-only or an explicit semantic-stack decision; notes `pkg_resources` import scan is clear and `tests/audit/test_no_undefined_imports.py` no longer allowlists it.
  - Python all-extras major resolver blockers — blocked on 8 named upstream packages relaxing constraints (`arize-phoenix>=15`, `importlib-metadata>=9`, `lxml>=6`, `marshmallow>=4`, `packaging>=26`, `pandas>=3`, `protobuf>=7`, `snowballstemmer>=3`); ~45 min resolver proof + targeted tests once unblocked.
- **Resolved section**: currently empty ("(none yet)") — kept as a placeholder for audit history once items clear.
- **Conventions**: add an entry when newly blocked; move to Resolved when the upstream release lands *and* the work is committed; re-evaluate any blocker waiting >90 days since the trigger may be a false alarm.
- **ADR-145 lane-split note**: clarifies that the Python major-version blockers listed are no longer *core-lock* blockers post-ADR-145 — they are lane-specific watch items under `requirements/dependency-lanes/*`, and core dependency hygiene should not wait on them.

## Relations & where used

- Cross-references `docs/06-Daily/reports/python-major-deps-review-2026-05-04.md` and `docs/06-Daily/reports/python-major-followup-2026-05-04.md` for detailed resolver evidence.
- References `docs/01-Build-Log/SESSION-HANDOFF-2026-04-25.md` as the origin of the first three entries.
- Governed procedurally by ADR-145 (dependency lane split), which changes how the Python resolver blockers should be prioritized relative to core-lock work.

## Status / caveats

- This is explicitly a **living, dated tracking ledger**, not stable reference material — "Last reviewed: 2026-05-04" and individual "Last proof" dates mean every specific status (cryptography at 47.x, `wrapt` resolver acceptance, etc.) is a point-in-time snapshot that is expected to change as upstream releases land. Treat all version/status claims here as needing re-verification against the live file rather than this synthesis.
- No internal inconsistencies found; the ADR-145 note at the bottom is itself a later addendum that partially reclassifies earlier entries in the same document (from "core blockers" to "lane-specific watch items") — this is a legitimate evolution, not a contradiction, but worth noting as an example of the document being amended in place over time.

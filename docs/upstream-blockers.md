# Upstream Blockers — Items Waiting on External Releases

Tracking file for work that is **ready to do** but blocked on third-party releases. Each entry has a trigger condition (what needs to happen upstream), an action (what we do once unblocked), and an estimate.

Last reviewed: 2026-05-04.

## Active blockers

### `default_backend()` cleanup in hermes-agent

- **Where**: `.claude/plugins/hermes-agent/` (3 files reference the deprecated `default_backend()` API)
- **Trigger**: `cryptography` package drops the deprecated symbol (announced for 49.0.0). Track at https://github.com/pyca/cryptography/releases — currently at 47.x as of 2026-04-27.
- **Action**: replace each `default_backend()` call with explicit backend reference (or remove if no longer needed by the new API). Run hermes-agent test suite after.
- **Estimate**: ~30 min (3 files, mechanical replacement).
- **First flagged**: 2026-04-25 in `docs/SESSION-HANDOFF-2026-04-25.md`.

### `rich` 14 → 15

- **Trigger**: `cognee` / `instructor` allow `rich>=15` in the all-extras resolver.
- **Action**: bump `rich` once `uv lock` succeeds with `rich>=15`; run `scripts/cos_watch.py` smoke and dependency import tests.
- **Estimate**: ~15 min.
- **First flagged**: 2026-04-25.
- **Last proof**: 2026-05-04 `uv lock` with `rich>=15` fails because `luum-cognitive-os[memory]` pulls `cognee`, which pulls `instructor` constrained to `rich>=13.7.0,<15.0.0`.

### `wrapt` 1 → 2

- **Trigger**: OpenTelemetry / OpenInference / `deprecated` / `arize-phoenix` transitive deps validate `wrapt 2.x`.
- **Action**: bump `wrapt` and re-run Phoenix/OpenTelemetry instrumentation tests.
- **Estimate**: ~30 min plus monitoring.
- **First flagged**: 2026-04-25.
- **Last proof**: 2026-05-04 resolver can accept `wrapt>=2`, but no first-party code imports it and instrumentation packages remain the risk surface, so the bump stays held pending targeted integration tests.

### Python all-extras major resolver blockers

- **Trigger**: upstream packages relax constraints blocking the 2026-05-04 major review: `arize-phoenix>=15`, `importlib-metadata>=9`, `lxml>=6`, `marshmallow>=4`, `packaging>=26`, `pandas>=3`, `protobuf>=7`, `snowballstemmer>=3`.
- **Action**: re-run `uv lock` with temporary direct constraints and update `docs/reports/python-major-deps-review-2026-05-04.md` before any blanket `--apply --major`.
- **Estimate**: ~45 min resolver proof + targeted tests.
- **First flagged**: 2026-05-04.

## Resolved (kept for audit)

(none yet)

## Conventions

- Add a new entry when an item gets blocked on an upstream release.
- Move to "Resolved" when the upstream release lands AND the work is committed.
- If a blocker has been waiting more than 90 days, re-evaluate whether the trigger is still relevant — sometimes the API never changes and the "blocker" was a false alarm.
- Cross-reference with `docs/SESSION-HANDOFF-*.md` files when first flagging.

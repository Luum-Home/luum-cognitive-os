# Upstream Blockers — Items Waiting on External Releases

Tracking file for work that is **ready to do** but blocked on third-party releases. Each entry has a trigger condition (what needs to happen upstream), an action (what we do once unblocked), and an estimate.

Last reviewed: 2026-04-27.

## Active blockers

### `default_backend()` cleanup in hermes-agent

- **Where**: `.claude/plugins/hermes-agent/` (3 files reference the deprecated `default_backend()` API)
- **Trigger**: `cryptography` package drops the deprecated symbol (announced for 49.0.0). Track at https://github.com/pyca/cryptography/releases — currently at 47.x as of 2026-04-27.
- **Action**: replace each `default_backend()` call with explicit backend reference (or remove if no longer needed by the new API). Run hermes-agent test suite after.
- **Estimate**: ~30 min (3 files, mechanical replacement).
- **First flagged**: 2026-04-25 in `docs/SESSION-HANDOFF-2026-04-25.md`.

### `rich` 14 → 15

- **Trigger**: `cognee` unpins `rich<13.7.0` upstream. Track at https://github.com/topoteretes/cognee/issues
- **Action**: bump `rich` in `requirements.txt` and any tool that pinned 14.x; run UI smoke tests for any rich-based output.
- **Estimate**: ~15 min.
- **First flagged**: 2026-04-25.

### `wrapt` 1 → 2

- **Trigger**: OpenTelemetry / `deprecated` / `arize-phoenix` transitive deps validate `wrapt 2.x`.
- **Action**: bump `wrapt` and re-run instrumentation tests.
- **Estimate**: ~30 min plus monitoring.
- **First flagged**: 2026-04-25.

## Resolved (kept for audit)

(none yet)

## Conventions

- Add a new entry when an item gets blocked on an upstream release.
- Move to "Resolved" when the upstream release lands AND the work is committed.
- If a blocker has been waiting more than 90 days, re-evaluate whether the trigger is still relevant — sometimes the API never changes and the "blocker" was a false alarm.
- Cross-reference with `docs/SESSION-HANDOFF-*.md` files when first flagging.

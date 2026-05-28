#!/usr/bin/env bash
# SCOPE: both
# Cognitive OS init — Python implementation since 2026-04-27 (Phase 2.final).
# This shim preserves backward compat for `bash scripts/cos-init.sh`.
# Full implementation in scripts/cos_init.py (per ADR-066 polyglot policy).
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-}"
if [ -z "$PYTHON_BIN" ] && [ -x "$SCRIPT_DIR/../.venv/bin/python" ]; then
  PYTHON_BIN="$SCRIPT_DIR/../.venv/bin/python"
fi
if [ -z "$PYTHON_BIN" ] && command -v uv >/dev/null 2>&1 && [ -f "$SCRIPT_DIR/../pyproject.toml" ]; then
  exec uv run --project "$SCRIPT_DIR/.." python "$SCRIPT_DIR/cos_init.py" "$@"
fi
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3 2>/dev/null || printf python3)}"
exec "$PYTHON_BIN" "$SCRIPT_DIR/cos_init.py" "$@"

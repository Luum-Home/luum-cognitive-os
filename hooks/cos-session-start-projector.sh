#!/usr/bin/env bash
# SCOPE: os-only
# ADR-275 — Wrapper invoking scripts/cos-session-start-projector (Python).
# SessionStart hook. Non-blocking; projector exits 0 always.

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"
exec python3 "$PROJECT_DIR/scripts/cos-session-start-projector"

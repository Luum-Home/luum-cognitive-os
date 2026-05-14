#!/usr/bin/env bash
# SCOPE: both
# Cognitive OS init — Python implementation since 2026-04-27 (Phase 2.final).
# This shim preserves backward compat for `bash scripts/cos-init.sh`.
# Full implementation in scripts/cos_init.py (per ADR-066 polyglot policy).
exec python3 "$(dirname "$0")/cos_init.py" "$@"

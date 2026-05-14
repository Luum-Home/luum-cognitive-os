#!/usr/bin/env bash
# SCOPE: both
# export-engram-to-obsidian.sh — one-way Engram → Obsidian Markdown export.
#
# Dry-run is the default. Pass --write to create/update files in the vault.
# Obsidian is a human-readable graph/audit layer; Engram remains source of truth.
#
# Usage:
#   bash scripts/export-engram-to-obsidian.sh --vault /path/to/vault [--project luum-agent-os]
#   bash scripts/export-engram-to-obsidian.sh --vault /path/to/vault --write

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

ROOT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}}"
PYTHON_BIN="${PYTHON:-python3}"

exec "$PYTHON_BIN" "$OS_ROOT/lib/engram_obsidian_exporter.py" "$@"

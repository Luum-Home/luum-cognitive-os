#!/usr/bin/env bash
# SCOPE: os-only
# native-agent-heartbeat.sh — PreToolUse:Agent + PostToolUse:Agent hook
#
# Thin shim (ADR-033): forwards the raw hook payload to the harness-agnostic
# event-capture layer. The Claude Code adapter preserves legacy behaviour
# (agent-heartbeat.jsonl + AgentBusMetrics notifications) and additionally
# emits canonical events so downstream consumers stay harness-independent.
#
# Why a shell wrapper? Hook registration (scripts/apply-efficiency-profile.sh)
# expects a script path. Keeping this file preserves the registration contract.
#
# Migration: see docs/02-Decisions/adrs/ADR-033-harness-agnostic-event-capture.md.

set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}"

# Read stdin into a tempfile to avoid shell quoting issues.
TMP=$(mktemp "${TMPDIR:-/tmp}/native-agent-heartbeat-XXXXXX")
trap 'rm -f "$TMP"' EXIT
cat > "$TMP"

PYTHONPATH="$PROJECT_DIR:${PYTHONPATH:-}" \
COGNITIVE_OS_PROJECT_DIR="$PROJECT_DIR" \
python3 - "$TMP" <<'PYEOF' 2>/dev/null || true
import sys
from pathlib import Path
from lib.harness_adapter.dispatch import handle_event

payload = Path(sys.argv[1]).read_text(encoding="utf-8")
handle_event(payload)
PYEOF

exit 0

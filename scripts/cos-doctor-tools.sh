#!/usr/bin/env bash
# SCOPE: os-only
# cos-doctor-tools.sh — Verify host tooling visible to Cognitive OS.
#
# This command answers a narrow question: "Can this host actually see the
# harness projection and optional memory/MCP tools the OS claims to use?"

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OS_SOURCE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$OS_SOURCE_ROOT}}}"
source "$OS_SOURCE_ROOT/scripts/_lib/settings-driver.sh"

STRICT=false

usage() {
  cat <<'EOF'
cos doctor tools — verify active harness and optional tool availability

Usage:
  bash scripts/cos-doctor-tools.sh [--strict]

Flags:
  --strict  Exit non-zero when optional tooling such as Engram is unavailable.
  --help    Show this help.

Checks:
  - active harness detection
  - active settings driver exists and is valid JSON
  - Codex native lifecycle keys when the active harness is codex
  - Engram CLI search availability
  - Engram MCP stdio startup availability

Exit codes:
  0  Core host wiring passed; optional checks may warn.
  1  Core host wiring failed, or optional checks failed under --strict.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --strict) STRICT=true ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown flag: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

failures=0
warnings=0

pass() { printf 'PASS %s\n' "$*"; }
warn() { printf 'WARN %s\n' "$*"; warnings=$((warnings + 1)); }
fail() { printf 'FAIL %s\n' "$*"; failures=$((failures + 1)); }

ACTIVE_HARNESS="$(cos_detect_harness "$PROJECT_ROOT")"
ACTIVE_DRIVER="$(cos_settings_driver_label "$ACTIVE_HARNESS")"
ACTIVE_DRIVER_PATH="$(cos_settings_driver_path "$PROJECT_ROOT" "$ACTIVE_HARNESS")"

printf 'Project: %s\n' "$PROJECT_ROOT"
printf 'Harness: %s\n' "$ACTIVE_HARNESS"
printf 'Settings driver: %s\n' "$ACTIVE_DRIVER"

case "$ACTIVE_HARNESS" in
  claude|codex) pass "active harness is supported: $ACTIVE_HARNESS" ;;
  *) fail "unsupported active harness: $ACTIVE_HARNESS" ;;
esac

if [ -f "$ACTIVE_DRIVER_PATH" ]; then
  pass "settings driver exists: $ACTIVE_DRIVER"
else
  fail "settings driver missing: $ACTIVE_DRIVER"
fi

if [ -f "$ACTIVE_DRIVER_PATH" ] && command -v python3 >/dev/null 2>&1; then
  if python3 - "$ACTIVE_DRIVER_PATH" "$ACTIVE_HARNESS" <<'PYEOF'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
harness = sys.argv[2]

try:
    data = json.loads(path.read_text())
except Exception as exc:
    print(f"invalid JSON: {exc}", file=sys.stderr)
    raise SystemExit(1)

if harness == "codex":
    if "hooks" in data:
        print("Codex driver must use native top-level lifecycle keys, not Claude hooks wrapper", file=sys.stderr)
        raise SystemExit(1)
    lifecycle_keys = {"SessionStart", "UserPromptSubmit", "Stop"}
    present = lifecycle_keys.intersection(data)
    if not present:
        print("Codex driver has no known lifecycle keys", file=sys.stderr)
        raise SystemExit(1)
else:
    if not isinstance(data.get("hooks"), dict):
        print("Claude driver missing top-level hooks object", file=sys.stderr)
        raise SystemExit(1)
PYEOF
  then
    pass "settings driver JSON contract is valid"
  else
    fail "settings driver JSON contract failed"
  fi
elif [ -f "$ACTIVE_DRIVER_PATH" ]; then
  warn "python3 unavailable; settings driver JSON contract was not checked"
fi

if command -v engram >/dev/null 2>&1; then
  ENGRAM_BIN="$(command -v engram)"
  pass "engram CLI found: $ENGRAM_BIN"
  if python3 - "$PROJECT_ROOT" <<'PYEOF'
import subprocess
import sys

project_root = sys.argv[1]
cmd = ["engram", "search", "cognitive os", "--limit", "1"]
try:
    result = subprocess.run(cmd, cwd=project_root, text=True, capture_output=True, timeout=8)
except Exception as exc:
    print(str(exc), file=sys.stderr)
    raise SystemExit(1)

if result.returncode != 0:
    print((result.stderr or result.stdout).strip(), file=sys.stderr)
    raise SystemExit(result.returncode)
PYEOF
  then
    pass "engram CLI search works"
  else
    warn "engram CLI is installed but search failed"
  fi

  if python3 - "$PROJECT_ROOT" <<'PYEOF'
import subprocess
import sys
from pathlib import Path

project = Path(sys.argv[1]).name or "cognitive-os"
cmd = ["engram", "mcp", "--tools=agent", "--project", project]
try:
    result = subprocess.run(
        cmd,
        cwd=sys.argv[1],
        input="",
        text=True,
        capture_output=True,
        timeout=5,
    )
except subprocess.TimeoutExpired:
    # A stdio MCP server that stays alive waiting for JSON-RPC is usable.
    raise SystemExit(0)
except Exception as exc:
    print(str(exc), file=sys.stderr)
    raise SystemExit(1)

if result.returncode != 0:
    print((result.stderr or result.stdout).strip(), file=sys.stderr)
    raise SystemExit(result.returncode)
PYEOF
  then
    pass "engram MCP stdio starts"
  else
    warn "engram MCP stdio probe failed"
  fi
else
  warn "engram CLI not found on PATH"
fi

if [ "$ACTIVE_HARNESS" = "codex" ]; then
  CODEX_CONFIG="${CODEX_HOME:-$HOME/.codex}/config.toml"
  if [ -f "$CODEX_CONFIG" ] && grep -qi "engram" "$CODEX_CONFIG"; then
    pass "Codex config mentions Engram"
  else
    warn "Codex config does not appear to register Engram MCP yet"
  fi
fi

if [ "$failures" -gt 0 ] || { [ "$STRICT" = true ] && [ "$warnings" -gt 0 ]; }; then
  printf 'Result: FAIL (%s failure(s), %s warning(s))\n' "$failures" "$warnings"
  exit 1
fi

printf 'Result: PASS (%s warning(s))\n' "$warnings"
exit 0

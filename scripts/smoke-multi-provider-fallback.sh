#!/usr/bin/env bash
# SCOPE: both
# smoke-multi-provider-fallback.sh — Exercise each configured provider in isolation (ADR-062 Phase 4).
#
# For each provider in lib/providers/REGISTRY:
#   - Calls is_configured() first.
#   - If configured: sends a trivial "say hi" prompt via provider.call() with 30s timeout.
#   - Prints: [OK], [SKIP: not configured], or [FAIL: <reason>].
#
# Exit codes:
#   0 — all CONFIGURED providers responded successfully (skips don't count as failures)
#   1 — one or more configured providers failed
#
# Usage:
#   bash scripts/smoke-multi-provider-fallback.sh

set -uo pipefail

cd "$(dirname "$0")/.."
PROJECT_DIR="$(pwd)"

# Load .env if present (API keys)
if [ -f "$PROJECT_DIR/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$PROJECT_DIR/.env" 2>/dev/null || true
  set +a
fi

# ── colour helpers ─────────────────────────────────────────────────────────────
_green()  { printf '\033[32m%s\033[0m' "$1"; }
_red()    { printf '\033[31m%s\033[0m' "$1"; }
_yellow() { printf '\033[33m%s\033[0m' "$1"; }

FAIL_COUNT=0
PASS_COUNT=0
SKIP_COUNT=0

printf "ADR-062 Multi-Provider Smoke Test — %s\n" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf "─────────────────────────────────────────\n"

# Single Python call: iterate all providers, print result lines
result=$(
  uv run python3 - <<'PYEOF' 2>&1
import sys
import signal
from pathlib import Path

sys.path.insert(0, str(Path(".").resolve()))

from lib.providers import REGISTRY

def _timeout_handler(signum, frame):
    raise TimeoutError("timed out after 30s")

for name, mod in REGISTRY.items():
    try:
        configured = mod.is_configured()
    except Exception as exc:
        print(f"FAIL\t{name}\tis_configured() raised: {exc!r:.80}")
        continue

    if not configured:
        print(f"SKIP\t{name}\tnot configured")
        continue

    # Send trivial prompt with 30s timeout
    signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(30)
    try:
        r = mod.call(
            messages=[{"role": "user", "content": "Reply with exactly: hi"}],
            max_tokens=10,
            model_hint="haiku",
        )
        signal.alarm(0)
    except TimeoutError:
        print(f"FAIL\t{name}\ttimed out after 30s")
        continue
    except Exception as exc:
        signal.alarm(0)
        print(f"FAIL\t{name}\tcall() raised: {exc!r:.120}")
        continue

    if r.get("success"):
        print(f"OK\t{name}\t{r.get('model','')}")
    else:
        err = (r.get("error") or "no error field")[:120]
        print(f"FAIL\t{name}\t{err}")
PYEOF
)

# Parse and display each line
while IFS=$'\t' read -r status name detail; do
  case "$status" in
    OK)
      printf "  %s  %-14s  %s\n" "$(_green "[OK]")" "$name" "$detail"
      PASS_COUNT=$((PASS_COUNT + 1))
      ;;
    SKIP)
      printf "  %s  %-14s  %s\n" "$(_yellow "[SKIP: not configured]")" "$name" ""
      SKIP_COUNT=$((SKIP_COUNT + 1))
      ;;
    FAIL)
      printf "  %s  %-14s  %s\n" "$(_red "[FAIL]")" "$name" "$detail"
      FAIL_COUNT=$((FAIL_COUNT + 1))
      ;;
    *)
      # raw Python error / unexpected output — print as-is
      printf "  [INFO] %s\t%s\t%s\n" "$status" "$name" "$detail"
      ;;
  esac
done <<< "$result"

printf "─────────────────────────────────────────\n"
printf "Configured: %d passed, %d failed | Skipped (unconfigured): %d\n" \
  "$PASS_COUNT" "$FAIL_COUNT" "$SKIP_COUNT"

if [ "$FAIL_COUNT" -gt 0 ]; then
  printf "%s\n" "$(_red "SMOKE FAILED: $FAIL_COUNT configured provider(s) did not respond.")"
  exit 1
fi

printf "%s\n" "$(_green "All configured providers OK.")"
exit 0

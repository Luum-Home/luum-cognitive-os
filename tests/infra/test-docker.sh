#!/usr/bin/env bash
# Layer 1: Docker Infrastructure Tests
# Checks if Cognitive OS containers are running and healthy.
set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../../.." && pwd)}"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.cognitive-os.yml"
DOCKER="$(command -v docker 2>/dev/null || echo "/Applications/Docker.app/Contents/Resources/bin/docker")"

PASS=0
FAIL=0
WARN=0

pass() { PASS=$((PASS + 1)); echo "  PASS: $1"; }
fail() { FAIL=$((FAIL + 1)); echo "  FAIL: $1"; }
warn() { WARN=$((WARN + 1)); echo "  WARN: $1"; }

echo "=== DOCKER INFRASTRUCTURE TESTS ==="
echo ""

# ---- Pre-check: Docker available ----
if ! command -v "$DOCKER" &>/dev/null; then
  warn "Docker not found — skipping container checks"
  echo ""
  echo "=== DOCKER SUMMARY ==="
  echo "  PASS: $PASS  FAIL: $FAIL  WARN: $WARN"
  exit 0
fi

if ! "$DOCKER" info &>/dev/null 2>&1; then
  warn "Docker daemon not running — skipping container checks"
  echo ""
  echo "=== DOCKER SUMMARY ==="
  echo "  PASS: $PASS  FAIL: $FAIL  WARN: $WARN"
  exit 0
fi

# ---- Pre-check: Compose file exists ----
if [ ! -f "$COMPOSE_FILE" ]; then
  warn "docker-compose.cognitive-os.yml not found — skipping"
  echo ""
  echo "=== DOCKER SUMMARY ==="
  echo "  PASS: $PASS  FAIL: $FAIL  WARN: $WARN"
  exit 0
fi

# ---- Extract expected containers ----
CONTAINERS=$(grep 'container_name:' "$COMPOSE_FILE" | awk '{print $2}' | tr -d '"' | tr -d "'")

echo "--- Container Status ---"
while IFS= read -r container; do
  [ -z "$container" ] && continue

  # Check if container exists and get its status
  STATUS=$("$DOCKER" inspect --format='{{.State.Status}}' "$container" 2>/dev/null || echo "not_found")
  HEALTH=$("$DOCKER" inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no_healthcheck{{end}}' "$container" 2>/dev/null || echo "unknown")

  case "$STATUS" in
    running)
      case "$HEALTH" in
        healthy|no_healthcheck)
          pass "$container: UP ($HEALTH)"
          ;;
        unhealthy)
          warn "$container: RUNNING but UNHEALTHY"
          ;;
        starting)
          warn "$container: RUNNING, health starting"
          ;;
        *)
          pass "$container: UP (health=$HEALTH)"
          ;;
      esac
      ;;
    exited|dead|paused)
      fail "$container: DOWN ($STATUS)"
      ;;
    not_found)
      fail "$container: NOT FOUND (never started?)"
      ;;
    *)
      warn "$container: UNKNOWN status ($STATUS)"
      ;;
  esac
done <<< "$CONTAINERS"

# ---- Summary ----
echo ""
echo "=== DOCKER SUMMARY ==="
echo "  PASS: $PASS"
echo "  FAIL: $FAIL"
echo "  WARN: $WARN"
echo ""

# Docker failures are non-blocking (services may not be needed)
exit 0

#!/usr/bin/env bash
# SCOPE: os-only
# Infrastructure Health Check — SessionStart hook
# Auto-detects Docker status and required services.
# Outputs advisory messages about missing infrastructure.
# Env: INFRA_AUTO_START=true to auto-start missing services (default: false)
set -euo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.cognitive-os.yml"
CONFIG_FILE="$PROJECT_DIR/.cognitive-os/cognitive-os.yaml"
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
METRICS_FILE="$METRICS_DIR/infra-health.jsonl"
INFRA_AUTO_START="${INFRA_AUTO_START:-false}"
INFRA_START_TIMEOUT="${INFRA_START_TIMEOUT:-10}"
INFRA_CHECK_TIMEOUT="${INFRA_CHECK_TIMEOUT:-5}"
DOCKER="$(command -v docker 2>/dev/null || echo "")"
TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

run_bounded() {
  # Run a command with a wall-clock timeout without relying on GNU timeout.
  # Prints captured stdout and returns the command exit code, or 124 on timeout.
  local limit="$1"
  shift
  local out_file err_file pid waited status
  out_file="${TMPDIR:-/tmp}/infra-health-out-$$-$RANDOM"
  err_file="${TMPDIR:-/tmp}/infra-health-err-$$-$RANDOM"
  "$@" >"$out_file" 2>"$err_file" &
  pid=$!
  waited=0
  while kill -0 "$pid" 2>/dev/null; do
    if [ "$waited" -ge "$limit" ]; then
      kill "$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true
      rm -f "$out_file" "$err_file" 2>/dev/null || true
      return 124
    fi
    sleep 1
    waited=$((waited + 1))
  done
  wait "$pid"
  status=$?
  cat "$out_file" 2>/dev/null || true
  rm -f "$out_file" "$err_file" 2>/dev/null || true
  return "$status"
}

run_compose_start() {
  # SessionStart infrastructure checks are advisory. Docker compose can block on
  # image pulls or daemon contention, so auto-start attempts must be bounded.
  "$DOCKER" compose "$@" &
  local pid=$!
  local waited=0
  while kill -0 "$pid" 2>/dev/null; do
    if [ "$waited" -ge "$INFRA_START_TIMEOUT" ]; then
      kill "$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true
      return 124
    fi
    sleep 1
    waited=$((waited + 1))
  done
  wait "$pid"
}

# Ensure metrics directory exists
mkdir -p "$METRICS_DIR"

# ---- 1. Check Docker daemon ----
if [ -z "$DOCKER" ] || ! run_bounded "$INFRA_CHECK_TIMEOUT" "$DOCKER" info >/dev/null; then
  echo "Docker is not active. Start Docker to use infrastructure services."
  echo "{\"timestamp\":\"$TIMESTAMP\",\"docker\":false,\"running\":0,\"expected\":0,\"action\":\"none\",\"message\":\"Docker not active\"}" >> "$METRICS_FILE"
  exit 0
fi

# ---- 2. Check compose file exists ----
if [ ! -f "$COMPOSE_FILE" ]; then
  echo "No docker-compose.cognitive-os.yml found. Infrastructure health check skipped."
  echo "{\"timestamp\":\"$TIMESTAMP\",\"docker\":true,\"running\":0,\"expected\":0,\"action\":\"none\",\"message\":\"No compose file\"}" >> "$METRICS_FILE"
  exit 0
fi

# ---- 3. Discover expected services and profiles from config ----
# Read configured services from cognitive-os.yaml resources.infrastructure.services
expected_services=""
if [ -f "$CONFIG_FILE" ] && command -v python3 >/dev/null 2>&1; then
  expected_services=$(python3 -c "
import yaml, sys
try:
    with open('$CONFIG_FILE') as f:
        cfg = yaml.safe_load(f)
    svc = cfg.get('resources', {}).get('infrastructure', {}).get('services', {})
    for name in sorted(svc.keys()):
        mode = svc[name].get('mode', 'on_demand')
        print(f'{name}:{mode}')
except Exception:
    pass
" 2>/dev/null || true)
fi

# ---- 4. Get running services from docker compose ----
running_json=$(run_bounded "$INFRA_CHECK_TIMEOUT" "$DOCKER" compose -f "$COMPOSE_FILE" ps --format json || true)
running_services=""
running_count=0

if [ -n "$running_json" ]; then
  # docker compose ps --format json outputs one JSON object per line
  running_services=$(echo "$running_json" | python3 -c "
import sys, json
services = set()
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        obj = json.loads(line)
        state = obj.get('State', obj.get('state', '')).lower()
        name = obj.get('Service', obj.get('service', obj.get('Name', obj.get('name', ''))))
        if state == 'running' and name:
            services.add(name)
    except (json.JSONDecodeError, AttributeError):
        continue
for s in sorted(services):
    print(s)
" 2>/dev/null || true)
  if [ -n "$running_services" ]; then
    running_count=$(echo "$running_services" | wc -l | tr -d ' ')
  fi
fi

# ---- 5. Compare running vs expected ----
expected_count=0
missing_services=""
missing_profiles=""
always_services=""

if [ -n "$expected_services" ]; then
  while IFS=: read -r svc_name svc_mode; do
    [ -z "$svc_name" ] && continue

    # Skip services that don't need Docker (migrated to pip, cloud, or disabled)
    if [ "$svc_mode" = "pip" ] || [ "$svc_mode" = "cloud" ] || [ "$svc_mode" = "disabled" ] || [ "$svc_mode" = "cli" ]; then
      continue
    fi

    expected_count=$((expected_count + 1))

    # Check if this service (or a container matching it) is running
    is_running=false
    if [ -n "$running_services" ]; then
      # Match service name or name containing the service key (e.g., paperclip-pg matches paperclip)
      if echo "$running_services" | grep -qi "$svc_name"; then
        is_running=true
      fi
    fi

    if [ "$is_running" = "false" ]; then
      # Determine profile for the service from docker-compose
      profile=$(run_bounded "$INFRA_CHECK_TIMEOUT" "$DOCKER" compose -f "$COMPOSE_FILE" config --format json | python3 -c "
import sys, json
try:
    cfg = json.load(sys.stdin)
    services = cfg.get('services', {})
    # Search for service matching '$svc_name'
    for name, svc_cfg in services.items():
        if '$svc_name' in name.lower():
            profiles = svc_cfg.get('profiles', [])
            if profiles:
                print(profiles[0])
            else:
                print('default')
            break
    else:
        print('default')
except Exception:
    print('default')
" 2>/dev/null || echo "default")
      missing_services="${missing_services:+$missing_services, }$svc_name (profile: $profile)"
      if [ "$profile" != "default" ] && ! echo "$missing_profiles" | grep -q "$profile"; then
        missing_profiles="${missing_profiles:+$missing_profiles }$profile"
      fi
      if [ "$svc_mode" = "always" ]; then
        always_services="${always_services:+$always_services }$svc_name"
      fi
    fi
  done <<< "$expected_services"
fi

# ---- 6. Report ----
if [ "$expected_count" -eq 0 ]; then
  echo "Infrastructure: no services configured in cognitive-os.yaml"
  echo "{\"timestamp\":\"$TIMESTAMP\",\"docker\":true,\"running\":$running_count,\"expected\":0,\"action\":\"none\",\"message\":\"No services configured\"}" >> "$METRICS_FILE"
  exit 0
fi

echo "Infrastructure: $running_count/$expected_count services running"

action="none"
if [ -n "$missing_services" ]; then
  # Report each missing service
  IFS=',' read -ra MISSING_ARR <<< "$missing_services"
  for svc_info in "${MISSING_ARR[@]}"; do
    svc_info=$(echo "$svc_info" | sed 's/^[[:space:]]*//')
    echo "  [WARN] $svc_info is not running"
  done

  # ---- 7. Auto-start or suggest ----
  if [ "$INFRA_AUTO_START" = "true" ]; then
    action="auto_start"
    # Start default (no-profile) services first
    run_compose_start -f "$COMPOSE_FILE" up -d 2>/dev/null || true
    # Start services with specific profiles
    if [ -n "$missing_profiles" ]; then
      for profile in $missing_profiles; do
        run_compose_start -f "$COMPOSE_FILE" --profile "$profile" up -d 2>/dev/null || true
        echo "  Auto-started profile: $profile"
      done
    fi
    echo "  Auto-started missing services."
  else
    action="suggest"
    echo "  To start missing services:"
    echo "    docker compose -f docker-compose.cognitive-os.yml up -d"
    if [ -n "$missing_profiles" ]; then
      for profile in $missing_profiles; do
        echo "    docker compose -f docker-compose.cognitive-os.yml --profile $profile up -d"
      done
    fi
    if [ -n "$always_services" ]; then
      echo "  Note: '$always_services' is configured as always-on and should be started."
    fi
  fi
fi

# ---- 8. Smart infrastructure (on-demand service management) ----
smart_start_enabled=""
if [ -f "$CONFIG_FILE" ]; then
  smart_start_enabled=$(grep 'smart_start:' "$CONFIG_FILE" 2>/dev/null | head -1 | sed 's/.*smart_start:[[:space:]]*//' | tr -d '[:space:]' || true)
fi

if [ "$smart_start_enabled" = "true" ] && command -v python3 >/dev/null 2>&1 && [ -n "$expected_services" ]; then
  echo "  Smart infrastructure enabled:"
  while IFS=: read -r svc_name svc_mode; do
    [ -z "$svc_name" ] && continue
    if [ "$svc_mode" = "always" ]; then
      python3 -c "
import sys
sys.path.insert(0, '$PROJECT_DIR/lib')
from smart_infra import ensure_service
ensure_service('$svc_name')
" 2>/dev/null || true
      echo "    $svc_name: ensured (always-on)"
    else
      echo "    $svc_name: on-demand (will start when needed)"
    fi
  done <<< "$expected_services"
fi

# ---- 9. (Removed 2026-04-24, ADR-058) former trace-UI auto-provisioning ----
# The former observability-stack auto-provisioner is retired. Phoenix
# (pip install arize-phoenix) is the LLM-native trace UI — no API key
# provisioning step is required.

# ---- 10. Log to metrics ----
echo "{\"timestamp\":\"$TIMESTAMP\",\"docker\":true,\"running\":$running_count,\"expected\":$expected_count,\"missing\":\"${missing_services}\",\"action\":\"$action\"}" >> "$METRICS_FILE"

exit 0

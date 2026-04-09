#!/usr/bin/env bash
# Infrastructure Health Check — SessionStart hook
# Auto-detects Docker status and required services.
# Outputs advisory messages about missing infrastructure.
# Env: INFRA_AUTO_START=true to auto-start missing services (default: false)
set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.cognitive-os.yml"
CONFIG_FILE="$PROJECT_DIR/.cognitive-os/cognitive-os.yaml"
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
METRICS_FILE="$METRICS_DIR/infra-health.jsonl"
INFRA_AUTO_START="${INFRA_AUTO_START:-false}"
DOCKER="$(command -v docker 2>/dev/null || echo "")"
TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Ensure metrics directory exists
mkdir -p "$METRICS_DIR"

# ---- 1. Check Docker daemon ----
if [ -z "$DOCKER" ] || ! "$DOCKER" info >/dev/null 2>&1; then
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
running_json=$("$DOCKER" compose -f "$COMPOSE_FILE" ps --format json 2>/dev/null || true)
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
    expected_count=$((expected_count + 1))

    # Check if this service (or a container matching it) is running
    is_running=false
    if [ -n "$running_services" ]; then
      # Match service name or name containing the service key (e.g., langfuse-web matches langfuse)
      if echo "$running_services" | grep -qi "$svc_name"; then
        is_running=true
      fi
    fi

    if [ "$is_running" = "false" ]; then
      # Determine profile for the service from docker-compose
      profile=$("$DOCKER" compose -f "$COMPOSE_FILE" config --format json 2>/dev/null | python3 -c "
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
    "$DOCKER" compose -f "$COMPOSE_FILE" up -d 2>/dev/null || true
    # Start services with specific profiles
    if [ -n "$missing_profiles" ]; then
      for profile in $missing_profiles; do
        "$DOCKER" compose -f "$COMPOSE_FILE" --profile "$profile" up -d 2>/dev/null || true
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

# ---- 9. Auto-provision Langfuse API keys if Langfuse is running but keys are absent ----
# This runs setup-langfuse.sh silently (idempotent: skips if keys already in .env).
LANGFUSE_PUBLIC_KEY_VAL="${LANGFUSE_PUBLIC_KEY:-}"
if [ -z "$LANGFUSE_PUBLIC_KEY_VAL" ] && [ -f "$PROJECT_DIR/.env" ]; then
  LANGFUSE_PUBLIC_KEY_VAL=$(grep -E '^LANGFUSE_PUBLIC_KEY=' "$PROJECT_DIR/.env" 2>/dev/null | tail -1 | cut -d= -f2-)
fi

LANGFUSE_RUNNING=false
if echo "$running_services" | grep -qi "langfuse"; then
  LANGFUSE_RUNNING=true
fi

if [ "$LANGFUSE_RUNNING" = "true" ] && [ -z "$LANGFUSE_PUBLIC_KEY_VAL" ]; then
  SETUP_SCRIPT="$PROJECT_DIR/scripts/setup-langfuse.sh"
  if [ -f "$SETUP_SCRIPT" ]; then
    echo "  Langfuse is running but API keys are not set — running setup-langfuse.sh..."
    bash "$SETUP_SCRIPT" 2>&1 | sed 's/^/  /' || true
  fi
fi

# ---- 10. Log to metrics ----
echo "{\"timestamp\":\"$TIMESTAMP\",\"docker\":true,\"running\":$running_count,\"expected\":$expected_count,\"missing\":\"${missing_services}\",\"action\":\"$action\"}" >> "$METRICS_FILE"

exit 0

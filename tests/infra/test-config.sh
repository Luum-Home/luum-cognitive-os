#!/usr/bin/env bash
# Layer 1: Configuration Validation Tests
# Verifies cognitive-os.yaml, squad YAMLs, and customization YAMLs parse correctly.
set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../../.." && pwd)}"
AOS="$PROJECT_DIR/.cognitive-os"
CONFIG="$AOS/cognitive-os.yaml"
SQUADS_DIR="$AOS/squads"
CUSTOM_DIR="$AOS/customizations"

PASS=0
FAIL=0
WARN=0

pass() { PASS=$((PASS + 1)); echo "  PASS: $1"; }
fail() { FAIL=$((FAIL + 1)); echo "  FAIL: $1"; }
warn() { WARN=$((WARN + 1)); echo "  WARN: $1"; }

# Detect YAML parser
YAML_PARSER=""
if command -v yq &>/dev/null; then
  YAML_PARSER="yq"
elif command -v python3 &>/dev/null; then
  YAML_PARSER="python3"
else
  echo "ERROR: No YAML parser available (need yq or python3)"
  exit 1
fi

validate_yaml() {
  local file="$1"
  if [ "$YAML_PARSER" = "yq" ]; then
    yq eval '.' "$file" >/dev/null 2>&1
  else
    python3 -c "import yaml; yaml.safe_load(open('$file'))" 2>/dev/null
  fi
}

get_yaml_field() {
  local file="$1" field="$2"
  if [ "$YAML_PARSER" = "yq" ]; then
    yq eval ".$field" "$file" 2>/dev/null
  else
    python3 -c "
import yaml
with open('$file') as f:
    d = yaml.safe_load(f)
keys = '$field'.split('.')
v = d
for k in keys:
    if v is None or not isinstance(v, dict):
        print('null')
        exit()
    v = v.get(k)
if v is None:
    print('null')
else:
    print(v)
" 2>/dev/null
  fi
}

echo "=== CONFIGURATION TESTS ==="
echo ""

# ---- Test 1: cognitive-os.yaml exists and parses ----
echo "--- cognitive-os.yaml ---"
if [ ! -f "$CONFIG" ]; then
  fail "cognitive-os.yaml not found"
else
  if validate_yaml "$CONFIG"; then
    pass "cognitive-os.yaml is valid YAML"
  else
    fail "cognitive-os.yaml is INVALID YAML"
  fi

  # ---- Test 2: Required fields exist ----
  echo ""
  echo "--- Required fields ---"

  PHASE=$(get_yaml_field "$CONFIG" "project.phase")
  if [ -n "$PHASE" ] && [ "$PHASE" != "null" ]; then
    pass "project.phase = $PHASE"
  else
    fail "project.phase is missing"
  fi

  BUDGET=$(get_yaml_field "$CONFIG" "resources.budget.monthly_limit_usd")
  if [ -n "$BUDGET" ] && [ "$BUDGET" != "null" ]; then
    pass "resources.budget.monthly_limit_usd = $BUDGET"
  else
    fail "resources.budget is missing"
  fi

  LOADING=$(get_yaml_field "$CONFIG" "skills.loading.strategy")
  if [ -n "$LOADING" ] && [ "$LOADING" != "null" ]; then
    pass "skills.loading.strategy = $LOADING"
  else
    fail "skills.loading is missing"
  fi

  # Additional fields
  PROJECT_NAME=$(get_yaml_field "$CONFIG" "project.name")
  if [ -n "$PROJECT_NAME" ] && [ "$PROJECT_NAME" != "null" ]; then
    pass "project.name = $PROJECT_NAME"
  else
    warn "project.name is missing"
  fi

  MEMORY_PROVIDER=$(get_yaml_field "$CONFIG" "memory.provider")
  if [ -n "$MEMORY_PROVIDER" ] && [ "$MEMORY_PROVIDER" != "null" ]; then
    pass "memory.provider = $MEMORY_PROVIDER"
  else
    warn "memory.provider is missing"
  fi
fi

# ---- Test 3: Squad YAMLs parse correctly ----
echo ""
echo "--- Squad YAMLs ---"
if [ -d "$SQUADS_DIR" ]; then
  for squad in "$SQUADS_DIR"/*.yaml "$SQUADS_DIR"/*.yml; do
    [ ! -f "$squad" ] && continue
    name=$(basename "$squad")
    if validate_yaml "$squad"; then
      pass "Squad $name is valid YAML"
    else
      fail "Squad $name is INVALID YAML"
    fi
  done
else
  warn "No squads directory found"
fi

# ---- Test 4: Customization YAMLs parse correctly ----
echo ""
echo "--- Customization YAMLs ---"
if [ -d "$CUSTOM_DIR" ]; then
  FOUND_CUSTOM=false
  for custom in "$CUSTOM_DIR"/*.yaml "$CUSTOM_DIR"/*.yml; do
    [ ! -f "$custom" ] && continue
    FOUND_CUSTOM=true
    name=$(basename "$custom")
    if validate_yaml "$custom"; then
      pass "Customization $name is valid YAML"
    else
      fail "Customization $name is INVALID YAML"
    fi
  done
  if ! $FOUND_CUSTOM; then
    warn "No customization YAML files found"
  fi
else
  warn "No customizations directory found"
fi

# ---- Test 5: Sessions directory and active-sessions.json ----
echo ""
echo "--- Session Concurrency ---"

SESSIONS_DIR="$AOS/sessions"
ACTIVE_SESSIONS="$SESSIONS_DIR/active-sessions.json"

if [ -d "$SESSIONS_DIR" ]; then
  pass "sessions/ directory exists"
else
  warn "sessions/ directory does not exist (will be created on first session)"
fi

if [ -f "$ACTIVE_SESSIONS" ]; then
  if jq empty "$ACTIVE_SESSIONS" 2>/dev/null; then
    pass "active-sessions.json is valid JSON"

    # Check for stale locks (PID not running)
    LOCKS_DIR="$SESSIONS_DIR/locks"
    STALE_LOCKS=0
    if [ -d "$LOCKS_DIR" ]; then
      for lockfile in "$LOCKS_DIR"/*.lock; do
        [ ! -f "$lockfile" ] && continue
        LOCK_PID=$(jq -r '.pid // 0' "$lockfile" 2>/dev/null)
        if [ "$LOCK_PID" -gt 0 ] && ! kill -0 "$LOCK_PID" 2>/dev/null; then
          STALE_LOCKS=$((STALE_LOCKS + 1))
        fi
      done
    fi

    if [ "$STALE_LOCKS" -eq 0 ]; then
      pass "No stale locks found"
    else
      warn "$STALE_LOCKS stale lock(s) found — run /sessions cleanup"
    fi

    # Check for stale sessions (PID not running)
    STALE_SESSIONS=$(jq -r '.sessions[].pid' "$ACTIVE_SESSIONS" 2>/dev/null | while read -r pid; do
      if [ "$pid" -gt 0 ] 2>/dev/null && ! kill -0 "$pid" 2>/dev/null; then
        echo "stale"
      fi
    done | wc -l | tr -d ' ')

    if [ "$STALE_SESSIONS" -eq 0 ]; then
      pass "No stale sessions in registry"
    else
      warn "$STALE_SESSIONS stale session(s) — run /sessions cleanup"
    fi
  else
    fail "active-sessions.json is INVALID JSON"
  fi
else
  warn "active-sessions.json does not exist (will be created on first session)"
fi

# Check sessions config in cognitive-os.yaml
CONCURRENCY=$(get_yaml_field "$CONFIG" "sessions.concurrency")
if [ -n "$CONCURRENCY" ] && [ "$CONCURRENCY" != "null" ]; then
  pass "sessions.concurrency = $CONCURRENCY"
else
  warn "sessions.concurrency not configured"
fi

# ---- Summary ----
echo ""
echo "=== CONFIG SUMMARY ==="
echo "  PASS: $PASS"
echo "  FAIL: $FAIL"
echo "  WARN: $WARN"
echo ""

[ "$FAIL" -gt 0 ] && exit 1
exit 0

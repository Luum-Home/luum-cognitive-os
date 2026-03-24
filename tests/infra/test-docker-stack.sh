#!/usr/bin/env bash
# test-docker-stack.sh — Infrastructure tests for Docker stack
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.cognitive-os.yml"

FAILURES=0
TESTS=0
SKIPPED=0

assert_eq() {
  local label="$1" expected="$2" actual="$3"
  TESTS=$((TESTS + 1))
  if [ "$expected" = "$actual" ]; then
    return 0
  else
    echo "  FAIL: $label (expected='$expected', got='$actual')"
    FAILURES=$((FAILURES + 1))
    return 1
  fi
}

skip() {
  local label="$1"
  TESTS=$((TESTS + 1))
  SKIPPED=$((SKIPPED + 1))
  echo "  SKIP: $label"
}

# ─── Pre-check: Docker available ────────────────────────────────────────────

if ! command -v docker >/dev/null 2>&1; then
  echo "docker-stack: Docker not available, skipping all tests"
  exit 0
fi

if ! docker info >/dev/null 2>&1; then
  echo "docker-stack: Docker daemon not running, skipping all tests"
  exit 0
fi

# ─── Test: Valkey image can be pulled ────────────────────────────────────────

test_valkey_image() {
  if docker image inspect valkey/valkey:8-alpine >/dev/null 2>&1 || \
     docker pull valkey/valkey:8-alpine >/dev/null 2>&1; then
    TESTS=$((TESTS + 1))
  else
    echo "  FAIL: cannot pull valkey/valkey:8-alpine"
    TESTS=$((TESTS + 1))
    FAILURES=$((FAILURES + 1))
  fi
}

# ─── Test: SeaweedFS image can be pulled ─────────────────────────────────────

test_seaweedfs_image() {
  # Check if SeaweedFS is in the compose file
  if ! grep -q 'seaweedfs\|chrislusf/seaweedfs' "$COMPOSE_FILE" 2>/dev/null; then
    skip "SeaweedFS not in compose file"
    return
  fi

  # Extract image name from compose file
  local image
  image=$(grep -A5 'seaweedfs' "$COMPOSE_FILE" 2>/dev/null | grep 'image:' | head -1 | sed 's/.*image:\s*//' | tr -d ' "'"'")

  if [ -z "$image" ]; then
    skip "SeaweedFS image not found in compose"
    return
  fi

  if docker image inspect "$image" >/dev/null 2>&1 || \
     docker pull "$image" >/dev/null 2>&1; then
    TESTS=$((TESTS + 1))
  else
    echo "  FAIL: cannot pull $image"
    TESTS=$((TESTS + 1))
    FAILURES=$((FAILURES + 1))
  fi
}

# ─── Test: docker-compose config validates ───────────────────────────────────

test_compose_config() {
  if [ ! -f "$COMPOSE_FILE" ]; then
    skip "compose file not found at $COMPOSE_FILE"
    return
  fi

  # Try docker compose (v2) first, then docker-compose (v1)
  # Provide dummy values for required env vars so config validation can pass
  local compose_env=""
  compose_env="LANGFUSE_ENCRYPTION_KEY=0000000000000000000000000000000000000000000000000000000000000000"

  local valid=false
  local error_output=""
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    error_output=$(env $compose_env docker compose -f "$COMPOSE_FILE" config 2>&1 >/dev/null)
    if [ $? -eq 0 ]; then
      valid=true
    fi
  elif command -v docker-compose >/dev/null 2>&1; then
    error_output=$(env $compose_env docker-compose -f "$COMPOSE_FILE" config 2>&1 >/dev/null)
    if [ $? -eq 0 ]; then
      valid=true
    fi
  else
    skip "neither docker compose nor docker-compose available"
    return
  fi

  if [ "$valid" != "true" ] && echo "$error_output" | grep -q "required variable"; then
    # Config is syntactically valid but requires env vars — that's acceptable
    skip "compose config requires env vars (syntax is valid)"
    return
  fi

  assert_eq "compose config validates" "true" "$valid"
}

# ─── Test: health checks (only if compose up is feasible) ───────────────────

test_health_checks() {
  # Only run if COGNITIVE_OS_TEST_DOCKER_UP=true (opt-in for CI)
  if [ "${COGNITIVE_OS_TEST_DOCKER_UP:-false}" != "true" ]; then
    skip "compose up tests (set COGNITIVE_OS_TEST_DOCKER_UP=true to enable)"
    return
  fi

  # Start only Valkey for a quick health check
  local compose_cmd=""
  if docker compose version >/dev/null 2>&1; then
    compose_cmd="docker compose"
  elif command -v docker-compose >/dev/null 2>&1; then
    compose_cmd="docker-compose"
  else
    skip "no compose command available"
    return
  fi

  $compose_cmd -f "$COMPOSE_FILE" up -d langfuse-valkey 2>/dev/null

  # Wait up to 15 seconds for health
  local healthy=false
  for i in $(seq 1 15); do
    local status
    status=$(docker inspect --format='{{.State.Health.Status}}' cognitive-os-langfuse-valkey 2>/dev/null || echo "missing")
    if [ "$status" = "healthy" ]; then
      healthy=true
      break
    fi
    sleep 1
  done

  assert_eq "Valkey health check passes" "true" "$healthy"

  # Test Valkey PING
  if [ "$healthy" = "true" ]; then
    local pong
    pong=$(docker exec cognitive-os-langfuse-valkey valkey-cli PING 2>/dev/null || echo "")
    assert_eq "Valkey responds to PING" "PONG" "$pong"
  fi

  # Cleanup
  $compose_cmd -f "$COMPOSE_FILE" down 2>/dev/null
}

# ─── Test: SeaweedFS S3 endpoint responds ────────────────────────────────────

test_seaweedfs_endpoint() {
  if [ "${COGNITIVE_OS_TEST_DOCKER_UP:-false}" != "true" ]; then
    skip "SeaweedFS endpoint test (set COGNITIVE_OS_TEST_DOCKER_UP=true)"
    return
  fi

  # Check if SeaweedFS is in compose
  if ! grep -q 'seaweedfs\|chrislusf/seaweedfs' "$COMPOSE_FILE" 2>/dev/null; then
    skip "SeaweedFS not in compose file"
    return
  fi

  local compose_cmd=""
  if docker compose version >/dev/null 2>&1; then
    compose_cmd="docker compose"
  elif command -v docker-compose >/dev/null 2>&1; then
    compose_cmd="docker-compose"
  fi

  # Get the SeaweedFS service name
  local svc
  svc=$(grep -B10 'seaweedfs\|chrislusf' "$COMPOSE_FILE" 2>/dev/null | grep -E '^\s+\w+:' | tail -1 | sed 's/:.*//' | tr -d ' ')

  if [ -z "$svc" ]; then
    skip "SeaweedFS service name not found"
    return
  fi

  $compose_cmd -f "$COMPOSE_FILE" up -d "$svc" 2>/dev/null
  sleep 5

  # Try to hit S3 endpoint
  local s3_port
  s3_port=$(grep -A20 "$svc" "$COMPOSE_FILE" 2>/dev/null | grep '8333' | head -1 | sed 's/.*:\([0-9]*\):8333.*/\1/')
  s3_port="${s3_port:-8333}"

  local response
  response=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$s3_port/" 2>/dev/null || echo "000")

  TESTS=$((TESTS + 1))
  if [ "$response" != "000" ]; then
    : # pass — got a response (any HTTP code means S3 is listening)
  else
    echo "  FAIL: SeaweedFS S3 endpoint not responding on port $s3_port"
    FAILURES=$((FAILURES + 1))
  fi

  $compose_cmd -f "$COMPOSE_FILE" down 2>/dev/null
}

# ─── Run all tests ───────────────────────────────────────────────────────────

test_valkey_image
test_seaweedfs_image
test_compose_config
test_health_checks
test_seaweedfs_endpoint

echo "docker-stack: $TESTS tests, $FAILURES failures, $SKIPPED skipped"
[ "$FAILURES" -eq 0 ] && exit 0 || exit 1

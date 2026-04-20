#!/usr/bin/env bash
# SCOPE: project
# =============================================================================
# setup-langfuse.sh — Automated Langfuse API key provisioning
# =============================================================================
# Fully automated: no manual account creation, no UI steps.
#
# Strategy:
#   1. If LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY already set in .env → skip
#   2. Generate stable keys (deterministic from project ID so they're idempotent)
#   3. Write keys to .env so Langfuse headless init wires them on next container start
#   4. Restart langfuse-web so it picks up the new LANGFUSE_INIT_PROJECT_* values
#   5. Verify the keys work via the Langfuse health + auth API
#
# Idempotent: safe to run on first install AND on repeat runs.
# Called from: hooks/infra-health.sh (SessionStart) when Langfuse is running
#              scripts/cos-init.sh during first-time setup
#
# Usage:
#   bash scripts/setup-langfuse.sh
#   bash scripts/setup-langfuse.sh --force   # regenerate even if keys exist
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.cognitive-os.yml"

LANGFUSE_PORT="${LANGFUSE_PORT:-3100}"
LANGFUSE_BASE_URL="http://localhost:${LANGFUSE_PORT}"
FORCE="${1:-}"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
log()   { echo "[setup-langfuse] $*"; }
ok()    { echo "[setup-langfuse] ✓ $*"; }
warn()  { echo "[setup-langfuse] ⚠ $*" >&2; }
err()   { echo "[setup-langfuse] ✗ $*" >&2; }

# Read a value from .env (returns empty string if not found or empty)
env_get() {
  local key="$1"
  local val
  val=$(grep -E "^${key}=" "${ENV_FILE}" 2>/dev/null | tail -1 | cut -d= -f2-)
  echo "${val}"
}

# Write or update a key=value in .env
env_set() {
  local key="$1"
  local val="$2"
  if grep -q "^${key}=" "${ENV_FILE}" 2>/dev/null; then
    # Update in-place (macOS + Linux compatible)
    if [[ "$(uname)" == "Darwin" ]]; then
      sed -i '' "s|^${key}=.*|${key}=${val}|" "${ENV_FILE}"
    else
      sed -i "s|^${key}=.*|${key}=${val}|" "${ENV_FILE}"
    fi
  else
    echo "${key}=${val}" >> "${ENV_FILE}"
  fi
}

# Generate a stable pk-... key seeded from a string (no random — idempotent across runs)
# Format follows Langfuse convention: pk-lf-... / sk-lf-...
_sha256_hex() {
  # Cross-platform SHA-256 hex output. Prefers python3 (most reliable across macOS/Linux).
  local input="$1"
  if command -v python3 &>/dev/null; then
    python3 -c "import hashlib, sys; print(hashlib.sha256(sys.argv[1].encode()).hexdigest())" "${input}"
  elif command -v openssl &>/dev/null; then
    # macOS: openssl dgst outputs "(stdin)= <hash>", Linux: just "<hash>"
    printf '%s' "${input}" | openssl dgst -sha256 | grep -oE '[0-9a-f]{64}$'
  else
    # last resort: md5sum (less ideal, but universally available)
    printf '%s' "${input}" | md5sum | awk '{print $1$1}'
  fi
}

gen_public_key() {
  local seed="${1:-cognitive-os-project}"
  local hash
  hash=$(_sha256_hex "${seed}-public")
  echo "pk-lf-${hash:0:32}"
}

gen_secret_key() {
  local seed="${1:-cognitive-os-project}"
  local hash
  hash=$(_sha256_hex "${seed}-secret")
  echo "sk-lf-${hash:0:32}"
}

gen_password() {
  # Random 20-char password for the init admin user
  if command -v openssl &>/dev/null; then
    openssl rand -base64 16 | tr -d '/+=' | head -c 20
  elif command -v python3 &>/dev/null; then
    python3 -c "import secrets, string; print(secrets.token_urlsafe(16)[:20])"
  else
    date +%s%N | sha256sum | head -c 20
  fi
}

# ---------------------------------------------------------------------------
# Step 0: ensure .env exists
# ---------------------------------------------------------------------------
if [[ ! -f "${ENV_FILE}" ]]; then
  warn ".env not found — copying from env.example"
  cp "${PROJECT_ROOT}/env.example" "${ENV_FILE}"
fi

# ---------------------------------------------------------------------------
# Step 1: check if keys already set (idempotency)
# ---------------------------------------------------------------------------
EXISTING_PUBLIC=$(env_get "LANGFUSE_PUBLIC_KEY")
EXISTING_SECRET=$(env_get "LANGFUSE_SECRET_KEY")

if [[ -n "${EXISTING_PUBLIC}" && -n "${EXISTING_SECRET}" && "${FORCE}" != "--force" ]]; then
  ok "LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY already set — skipping provisioning."
  ok "Public key: ${EXISTING_PUBLIC}"
  echo ""
  echo "To re-provision, run:  bash scripts/setup-langfuse.sh --force"
  exit 0
fi

log "Provisioning Langfuse API keys..."

# ---------------------------------------------------------------------------
# Step 2: generate stable API keys
# ---------------------------------------------------------------------------
PROJECT_ID=$(env_get "LANGFUSE_INIT_PROJECT_ID")
PROJECT_ID="${PROJECT_ID:-cognitive-os-project}"

PUBLIC_KEY=$(gen_public_key "${PROJECT_ID}")
SECRET_KEY=$(gen_secret_key "${PROJECT_ID}")

log "Generated public key:  ${PUBLIC_KEY}"
log "Generated secret key:  ${SECRET_KEY:0:12}... (truncated for display)"

# ---------------------------------------------------------------------------
# Step 3: ensure init user credentials are set
# ---------------------------------------------------------------------------
INIT_EMAIL=$(env_get "LANGFUSE_INIT_USER_EMAIL")
INIT_PASSWORD=$(env_get "LANGFUSE_INIT_USER_PASSWORD")

if [[ -z "${INIT_EMAIL}" ]]; then
  env_set "LANGFUSE_INIT_USER_EMAIL" "admin@cognitive-os.local"
  INIT_EMAIL="admin@cognitive-os.local"
  log "Set LANGFUSE_INIT_USER_EMAIL=${INIT_EMAIL}"
fi

if [[ -z "${INIT_PASSWORD}" ]]; then
  INIT_PASSWORD=$(gen_password)
  env_set "LANGFUSE_INIT_USER_PASSWORD" "${INIT_PASSWORD}"
  log "Generated LANGFUSE_INIT_USER_PASSWORD (saved to .env)"
fi

# ---------------------------------------------------------------------------
# Step 4: write keys to .env
# ---------------------------------------------------------------------------
env_set "LANGFUSE_PUBLIC_KEY" "${PUBLIC_KEY}"
env_set "LANGFUSE_SECRET_KEY" "${SECRET_KEY}"
ok "Keys written to ${ENV_FILE}"

# ---------------------------------------------------------------------------
# Step 5: check if Langfuse container is running
# ---------------------------------------------------------------------------
LANGFUSE_RUNNING=false
if command -v docker &>/dev/null; then
  if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "cognitive-os-langfuse$"; then
    LANGFUSE_RUNNING=true
  fi
fi

if [[ "${LANGFUSE_RUNNING}" == "true" ]]; then
  log "Langfuse container is running — recreating to apply headless init with new keys..."
  # Force-recreate (not just restart) so docker re-reads env vars from compose file.
  # restart only re-launches the process; recreate re-creates the container with fresh env.
  docker compose -f "${COMPOSE_FILE}" up -d --force-recreate langfuse-web 2>/dev/null || {
    warn "Could not recreate langfuse-web — keys will take effect on next 'docker compose up'"
  }

  # Wait for Langfuse to become healthy
  log "Waiting for Langfuse to become healthy (up to 90s)..."
  HEALTHY=false
  for i in $(seq 1 18); do
    if curl -sf "${LANGFUSE_BASE_URL}/api/public/health" &>/dev/null; then
      ok "Langfuse is healthy."
      HEALTHY=true
      break
    fi
    sleep 5
  done

  if [[ "${HEALTHY}" == "false" ]]; then
    warn "Langfuse did not become healthy in 90s — skipping verification."
  else
    # ---------------------------------------------------------------------------
    # Step 6: flush Redis negative cache, then verify the keys work
    # ---------------------------------------------------------------------------
    # Langfuse caches negative API key lookups in Redis/Valkey. After headless init
    # provisions new keys, stale "not-found" cache entries can cause 401s.
    # Flush the relevant cache keys to force a fresh DB lookup.
    VALKEY_CONTAINER=$(docker ps --format '{{.Names}}' 2>/dev/null | grep "cognitive-os-langfuse-valkey" | head -1)
    if [[ -n "${VALKEY_CONTAINER}" ]]; then
      log "Flushing Langfuse API key cache in Redis..."
      # Delete all api-key:* entries (negative cache + stale entries)
      CACHE_KEYS=$(docker exec "${VALKEY_CONTAINER}" valkey-cli -a langfuse_redis KEYS "api-key:*" 2>/dev/null | tr '\n' ' ')
      if [[ -n "${CACHE_KEYS}" ]]; then
        # shellcheck disable=SC2086
        docker exec "${VALKEY_CONTAINER}" valkey-cli -a langfuse_redis DEL ${CACHE_KEYS} &>/dev/null || true
        ok "Flushed $(echo "${CACHE_KEYS}" | wc -w | tr -d ' ') cache entries."
      fi
    fi

    log "Verifying API keys against ${LANGFUSE_BASE_URL}..."
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
      -u "${PUBLIC_KEY}:${SECRET_KEY}" \
      "${LANGFUSE_BASE_URL}/api/public/projects" 2>/dev/null || echo "000")

    if [[ "${HTTP_CODE}" == "200" ]]; then
      ok "API keys verified — Langfuse is fully configured."
    elif [[ "${HTTP_CODE}" == "401" ]]; then
      warn "API key verification returned 401."
      warn "This may happen if Langfuse was already running with different keys."
      warn "Try: docker compose -f docker-compose.cognitive-os.yml up -d --force-recreate langfuse-web"
    else
      warn "API key verification returned HTTP ${HTTP_CODE} — Langfuse may still be starting up."
    fi
  fi
else
  log "Langfuse is not running — keys will be applied via headless init on next 'docker compose up'."
  log "The LANGFUSE_INIT_PROJECT_PUBLIC_KEY / _SECRET_KEY are wired in docker-compose.cognitive-os.yml"
  log "and will be provisioned automatically when langfuse-web starts."
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "============================================================"
echo "  Langfuse Setup Complete"
echo "============================================================"
echo "  Public Key:  ${PUBLIC_KEY}"
echo "  Secret Key:  ${SECRET_KEY:0:12}..."
echo "  Admin email: ${INIT_EMAIL}"
echo "  UI:          ${LANGFUSE_BASE_URL}"
echo ""
echo "  These values are stored in .env and will be auto-loaded"
echo "  on the next Langfuse container start via headless init."
echo "============================================================"

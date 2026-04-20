#!/usr/bin/env bash
# SCOPE: os-only
# =============================================================================
# cos-bootstrap.sh — Cognitive OS one-command setup
# =============================================================================
# Idempotent: safe to run multiple times. Each step checks before acting.
#
# Usage:
#   bash scripts/cos-bootstrap.sh [OPTIONS]
#
# Options:
#   --profile minimal|standard|full   Service profile (default: standard)
#   --dry-run                          Show what would happen without doing it
#   --help                             Show this help message
#
# Profiles:
#   minimal   Langfuse stack only (6 containers: pg, valkey, clickhouse,
#             seaweedfs, worker, web)
#   standard  Langfuse + LiteLLM (7 containers) — recommended
#   full      All services (langfuse, litellm, nemo-guardrails, paperclip,
#             jupyter, memu, cognee)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env"
ENV_EXAMPLE="${PROJECT_ROOT}/env.example"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.cognitive-os.yml"
COS_DIR="${PROJECT_ROOT}/.cognitive-os"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
PROFILE="standard"
DRY_RUN=false
TOTAL_STEPS=9
STEP=0

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)
      PROFILE="${2:-standard}"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --help|-h)
      cat <<'EOF'
cos-bootstrap.sh — Cognitive OS one-command setup

USAGE
  bash scripts/cos-bootstrap.sh [OPTIONS]

OPTIONS
  --profile minimal|standard|full
      Service profile to start (default: standard)
      minimal:  Langfuse stack only (LLM observability)
      standard: Langfuse + LiteLLM (recommended)
      full:     All services (langfuse, litellm, paperclip, jupyter, etc.)

  --dry-run
      Print each step without executing it.

  --help
      Show this message.

EXAMPLES
  bash scripts/cos-bootstrap.sh
  bash scripts/cos-bootstrap.sh --profile minimal
  bash scripts/cos-bootstrap.sh --profile full
  bash scripts/cos-bootstrap.sh --dry-run
EOF
      exit 0
      ;;
    *)
      echo "Unknown argument: $1. Run with --help for usage." >&2
      exit 1
      ;;
  esac
done

# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------
step() {
  STEP=$((STEP + 1))
  echo ""
  echo "┌─ Step ${STEP}/${TOTAL_STEPS}: $*"
}

ok()   { echo "│  ✓ $*"; }
info() { echo "│  → $*"; }
warn() { echo "│  ⚠ $*" >&2; }
err()  { echo "│  ✗ $*" >&2; }
done_step() { echo "└─ done"; }

dry() {
  if [[ "${DRY_RUN}" == "true" ]]; then
    echo "│  [DRY-RUN] would run: $*"
    return 0
  fi
  "$@"
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Read a value from .env (returns empty string if not found or empty)
env_get() {
  local key="$1"
  grep -E "^${key}=" "${ENV_FILE}" 2>/dev/null | tail -1 | cut -d= -f2- || true
}

# Write or update a key=value in .env without overwriting existing non-empty values
env_set() {
  local key="$1"
  local val="$2"
  if grep -q "^${key}=" "${ENV_FILE}" 2>/dev/null; then
    if [[ "$(uname)" == "Darwin" ]]; then
      sed -i '' "s|^${key}=.*|${key}=${val}|" "${ENV_FILE}"
    else
      sed -i "s|^${key}=.*|${key}=${val}|" "${ENV_FILE}"
    fi
  else
    echo "${key}=${val}" >> "${ENV_FILE}"
  fi
}

# Merge new vars from env.example into .env — never overwrite existing values
merge_env() {
  local example="$1"
  local target="$2"
  local added=0

  while IFS= read -r line; do
    # Skip comments and empty lines
    [[ "${line}" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line}" ]] && continue

    local key
    key="${line%%=*}"
    [[ -z "${key}" ]] && continue

    # Only add if key doesn't exist in target at all
    if ! grep -q "^${key}=" "${target}" 2>/dev/null; then
      echo "${line}" >> "${target}"
      added=$((added + 1))
    fi
  done < "${example}"

  echo "${added}"
}

# Check if docker is available
check_docker() {
  if ! command -v docker &>/dev/null; then
    return 1
  fi
  if ! docker info &>/dev/null 2>&1; then
    return 1
  fi
  return 0
}

# Wait for a service health endpoint with timeout
wait_for_health() {
  local name="$1"
  local url="$2"
  local timeout="${3:-120}"
  local interval=5
  local elapsed=0

  info "Waiting for ${name} to be healthy (timeout: ${timeout}s)..."
  while [[ ${elapsed} -lt ${timeout} ]]; do
    if curl -sf "${url}" &>/dev/null 2>&1; then
      ok "${name} is healthy."
      return 0
    fi
    sleep "${interval}"
    elapsed=$((elapsed + interval))
    info "  ${elapsed}s elapsed..."
  done
  warn "${name} did not become healthy within ${timeout}s — continuing anyway."
  return 0
}

# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
echo "╔══════════════════════════════════════════════════════════╗"
echo "║          Cognitive OS — Bootstrap Setup                  ║"
echo "║  Profile: ${PROFILE}$(printf '%*s' $((49 - ${#PROFILE})) '')║"
if [[ "${DRY_RUN}" == "true" ]]; then
echo "║  Mode:    DRY-RUN (no changes will be made)              ║"
fi
echo "╚══════════════════════════════════════════════════════════╝"

# ---------------------------------------------------------------------------
# Step 1 — .env setup
# ---------------------------------------------------------------------------
step ".env setup"

if [[ "${DRY_RUN}" == "true" ]]; then
  if [[ ! -f "${ENV_FILE}" ]]; then
    info "Would copy env.example → .env"
  else
    info "Would merge new vars from env.example into existing .env"
  fi
  done_step
else
  if [[ ! -f "${ENV_FILE}" ]]; then
    cp "${ENV_EXAMPLE}" "${ENV_FILE}"
    ok "Created .env from env.example"
  else
    added_count=$(merge_env "${ENV_EXAMPLE}" "${ENV_FILE}")
    if [[ "${added_count}" -gt 0 ]]; then
      ok "Merged ${added_count} new variable(s) from env.example into .env"
    else
      ok ".env is already up-to-date (no new vars to add)"
    fi
  fi
  done_step
fi

# ---------------------------------------------------------------------------
# Step 2 — Generate LANGFUSE_ENCRYPTION_KEY if missing
# ---------------------------------------------------------------------------
step "LANGFUSE_ENCRYPTION_KEY generation"

if [[ "${DRY_RUN}" == "true" ]]; then
  existing=$(env_get "LANGFUSE_ENCRYPTION_KEY" 2>/dev/null || true)
  if [[ -z "${existing}" ]]; then
    info "Would generate LANGFUSE_ENCRYPTION_KEY (openssl rand -hex 32)"
  else
    ok "LANGFUSE_ENCRYPTION_KEY already set — skipping"
  fi
  done_step
else
  existing=$(env_get "LANGFUSE_ENCRYPTION_KEY" 2>/dev/null || true)
  if [[ -z "${existing}" ]]; then
    if command -v openssl &>/dev/null; then
      key=$(openssl rand -hex 32)
    elif command -v python3 &>/dev/null; then
      key=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    else
      err "Cannot generate encryption key: openssl and python3 are both missing."
      exit 1
    fi
    env_set "LANGFUSE_ENCRYPTION_KEY" "${key}"
    ok "Generated and saved LANGFUSE_ENCRYPTION_KEY"
  else
    ok "LANGFUSE_ENCRYPTION_KEY already set — skipping"
  fi
  done_step
fi

# ---------------------------------------------------------------------------
# Step 3 — Docker network
# ---------------------------------------------------------------------------
step "Docker network (cognitive-os-network)"

if [[ "${DRY_RUN}" == "true" ]]; then
  info "Would run: docker network create cognitive-os-network"
  done_step
else
  if ! check_docker; then
    warn "Docker is not available or not running — skipping network creation."
    warn "Start Docker and re-run this script to complete Docker setup."
    done_step
  else
    if docker network inspect cognitive-os-network &>/dev/null 2>&1; then
      ok "Network 'cognitive-os-network' already exists — skipping"
    else
      docker network create cognitive-os-network
      ok "Created Docker network 'cognitive-os-network'"
    fi
    done_step
  fi
fi

# ---------------------------------------------------------------------------
# Step 4 — Start Docker services
# ---------------------------------------------------------------------------
step "Docker services (profile: ${PROFILE})"

# Determine which services to start based on profile
get_services_for_profile() {
  case "${PROFILE}" in
    minimal)
      echo "langfuse-pg langfuse-valkey langfuse-clickhouse langfuse-seaweedfs langfuse-worker langfuse-web"
      ;;
    standard)
      echo "langfuse-pg langfuse-valkey langfuse-clickhouse langfuse-seaweedfs langfuse-worker langfuse-web litellm"
      ;;
    full)
      # All default services — let compose handle it
      echo ""
      ;;
    *)
      err "Unknown profile: ${PROFILE}. Valid options: minimal, standard, full"
      exit 1
      ;;
  esac
}

if [[ "${DRY_RUN}" == "true" ]]; then
  services=$(get_services_for_profile)
  if [[ -z "${services}" ]]; then
    info "Would run: docker compose -f docker-compose.cognitive-os.yml up -d"
  else
    info "Would run: docker compose -f docker-compose.cognitive-os.yml up -d ${services}"
  fi
  done_step
else
  if ! check_docker; then
    warn "Docker is not available — skipping service startup."
    done_step
  elif [[ ! -f "${COMPOSE_FILE}" ]]; then
    warn "docker-compose.cognitive-os.yml not found at ${COMPOSE_FILE} — skipping."
    done_step
  else
    # Load .env for compose
    set -a
    # shellcheck source=/dev/null
    [[ -f "${ENV_FILE}" ]] && source "${ENV_FILE}"
    set +a

    services=$(get_services_for_profile)
    if [[ -z "${services}" ]]; then
      info "Starting all services..."
      docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d
    else
      info "Starting: ${services}"
      # shellcheck disable=SC2086
      docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d ${services}
    fi
    ok "Docker services started (profile: ${PROFILE})"
    done_step
  fi
fi

# ---------------------------------------------------------------------------
# Step 5 — Health checks
# ---------------------------------------------------------------------------
step "Health checks"

if [[ "${DRY_RUN}" == "true" ]]; then
  info "Would check health of: Langfuse (http://localhost:3100), LiteLLM (http://localhost:4000)"
  done_step
else
  if ! check_docker; then
    warn "Docker not available — skipping health checks."
    done_step
  else
    # Langfuse is always part of every profile
    langfuse_port="${LANGFUSE_PORT:-3100}"
    wait_for_health "Langfuse" "http://localhost:${langfuse_port}/api/public/health" 120

    if [[ "${PROFILE}" == "standard" || "${PROFILE}" == "full" ]]; then
      litellm_port="${LITELLM_PORT:-4000}"
      wait_for_health "LiteLLM" "http://localhost:${litellm_port}/health" 60
    fi
    done_step
  fi
fi

# ---------------------------------------------------------------------------
# Step 6 — Langfuse API key provisioning
# ---------------------------------------------------------------------------
step "Langfuse API key provisioning"

LANGFUSE_SETUP_SCRIPT="${SCRIPT_DIR}/setup-langfuse.sh"

if [[ "${DRY_RUN}" == "true" ]]; then
  info "Would run: bash scripts/setup-langfuse.sh"
  done_step
else
  if [[ -f "${LANGFUSE_SETUP_SCRIPT}" ]]; then
    bash "${LANGFUSE_SETUP_SCRIPT}" || warn "setup-langfuse.sh encountered an issue — check output above."
  else
    warn "setup-langfuse.sh not found at ${LANGFUSE_SETUP_SCRIPT} — skipping."
  fi
  done_step
fi

# ---------------------------------------------------------------------------
# Step 7 — Rules/hooks symlink sync (self-install)
# ---------------------------------------------------------------------------
step "Rules and hooks symlink sync (self-install)"

SELF_INSTALL_SCRIPT="${PROJECT_ROOT}/hooks/self-install.sh"

if [[ "${DRY_RUN}" == "true" ]]; then
  info "Would run: CLAUDE_PROJECT_DIR=${PROJECT_ROOT} bash hooks/self-install.sh"
  done_step
else
  if [[ -f "${SELF_INSTALL_SCRIPT}" ]]; then
    CLAUDE_PROJECT_DIR="${PROJECT_ROOT}" bash "${SELF_INSTALL_SCRIPT}" || warn "self-install.sh encountered an issue."
    ok "Rules and hooks synced"
  else
    warn "hooks/self-install.sh not found — skipping symlink sync."
  fi
  done_step
fi

# ---------------------------------------------------------------------------
# Step 8 — .cognitive-os/ directory structure
# ---------------------------------------------------------------------------
step ".cognitive-os/ directory structure"

COS_DIRS=(
  "${COS_DIR}/sessions"
  "${COS_DIR}/metrics"
  "${COS_DIR}/tasks"
  "${COS_DIR}/checkpoints"
  "${COS_DIR}/plans/features"
  "${COS_DIR}/plans/bugs"
  "${COS_DIR}/plans/chores"
  "${COS_DIR}/plans/migrations"
  "${COS_DIR}/dynamic-tools"
  "${COS_DIR}/workflows/steps"
)

if [[ "${DRY_RUN}" == "true" ]]; then
  info "Would create directories:"
  for d in "${COS_DIRS[@]}"; do
    info "  ${d}"
  done
  done_step
else
  created=0
  for d in "${COS_DIRS[@]}"; do
    if [[ ! -d "${d}" ]]; then
      mkdir -p "${d}"
      created=$((created + 1))
    fi
  done
  if [[ ${created} -gt 0 ]]; then
    ok "Created ${created} missing director(ies) under .cognitive-os/"
  else
    ok ".cognitive-os/ directory structure already complete"
  fi
  done_step
fi

# ---------------------------------------------------------------------------
# Step 9 — Summary
# ---------------------------------------------------------------------------
step "Summary"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║          Cognitive OS — Bootstrap Complete               ║"
echo "╠══════════════════════════════════════════════════════════╣"

if [[ "${DRY_RUN}" == "true" ]]; then
echo "║  Mode:    DRY-RUN — no changes were made                 ║"
echo "╠══════════════════════════════════════════════════════════╣"
fi

echo "║  Profile: ${PROFILE}$(printf '%*s' $((49 - ${#PROFILE})) '')║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  Services & Ports:                                       ║"
echo "║    Langfuse UI:  http://localhost:3100                   ║"
if [[ "${PROFILE}" == "standard" || "${PROFILE}" == "full" ]]; then
echo "║    LiteLLM:      http://localhost:4000                   ║"
fi
if [[ "${PROFILE}" == "full" ]]; then
echo "║    Paperclip:    http://localhost:3200                   ║"
echo "║    Jupyter:      http://localhost:8888                   ║"
fi
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  Next steps:                                             ║"
echo "║    1. Set ANTHROPIC_API_KEY in .env                      ║"
echo "║    2. Open Claude Code:  claude                          ║"
echo "║    3. Initialize COS:    /cognitive-os-init              ║"
echo "║    4. Check health:      /cognitive-os-status            ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  To update later:  bash scripts/cos-update.sh           ║"
echo "╚══════════════════════════════════════════════════════════╝"

done_step

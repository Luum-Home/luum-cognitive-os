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
#   minimal   Paperclip only (1 container)
#   standard  Paperclip + Valkey
#   full      All services including ADR-060-gated optional containers:
#               --profile guardrails  → nemo-guardrails
#               --profile jupyter     → jupyter
#               --profile memory      → cognee + memu-pg
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${PROJECT_ROOT}/hooks/_lib/portable.sh"
ENV_FILE="${PROJECT_ROOT}/.env"
ENV_EXAMPLE="${PROJECT_ROOT}/env.example"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.cognitive-os.yml"
COS_DIR="${PROJECT_ROOT}/.cognitive-os"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
PROFILE="standard"
DRY_RUN=false
TOTAL_STEPS=7
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
      minimal:  Paperclip only
      standard: Paperclip + Valkey (recommended)
      full:     All services — activates compose profiles guardrails
                (nemo-guardrails), jupyter, and memory (cognee + memu-pg)
                in addition to the standard base services.

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
    portable_sed_inplace "s|^${key}=.*|${key}=${val}|" "${ENV_FILE}"
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
# Step 2 — Docker network
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
# Step 3 — Start Docker services
# ---------------------------------------------------------------------------
step "Docker services (profile: ${PROFILE})"

# Determine which services to start based on profile
# ADR-058 (2026-04-24): former observability stack removed — observability is now Phoenix
# via `uv run phoenix serve` (pip path, no Docker). The minimal/standard
# profiles are therefore thin; `full` still brings up the remaining Docker
# services (paperclip, nemo-guardrails, jupyter, etc.).
get_services_for_profile() {
  case "${PROFILE}" in
    minimal)
      echo "paperclip-pg paperclip"
      ;;
    standard)
      echo "paperclip-pg paperclip valkey"
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
  if [[ "${PROFILE}" == "full" ]]; then
    info "Would run: docker compose -f docker-compose.cognitive-os.yml --profile guardrails --profile jupyter --profile memory up -d"
  elif [[ -z "${services}" ]]; then
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
    if [[ "${PROFILE}" == "full" ]]; then
      info "Starting all services (including guardrails, jupyter, memory profiles)..."
      docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" \
        --profile guardrails --profile jupyter --profile memory up -d
    elif [[ -z "${services}" ]]; then
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
# Step 4 — Health checks
# ---------------------------------------------------------------------------
step "Health checks"

if [[ "${DRY_RUN}" == "true" ]]; then
  info "Would check health of: Paperclip (http://localhost:3200)"
  done_step
else
  if ! check_docker; then
    warn "Docker not available — skipping health checks."
    done_step
  else
    paperclip_port="${PAPERCLIP_PORT:-3200}"
    wait_for_health "Paperclip" "http://localhost:${paperclip_port}/api/health" 120
    done_step
  fi
fi

# ---------------------------------------------------------------------------
# Step 5 — Rules/hooks symlink sync (self-install)
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
# Step 6 — .cognitive-os/ directory structure
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
# Step 7 — Summary
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
echo "║    Phoenix UI:   http://localhost:6006 (uv run phoenix serve) ║"
if [[ "${PROFILE}" == "standard" || "${PROFILE}" == "full" ]]; then
echo "║    Paperclip:    http://localhost:3200                   ║"
fi
if [[ "${PROFILE}" == "full" ]]; then
echo "║    Jupyter:      http://localhost:8888                   ║"
echo "║    NeMo Guard.:  http://localhost:8000                   ║"
echo "║    Cognee/Memu:  (memory profile — no public HTTP port)  ║"
fi
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  Next steps:                                             ║"
echo "║    1. Optional: set provider keys you explicitly enable   ║"
echo "║    2. Open Claude Code:  claude                          ║"
echo "║    3. Initialize COS:    /cognitive-os-init              ║"
echo "║    4. Check health:      /cognitive-os-status            ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  To update later:  bash scripts/cos-update.sh           ║"
echo "╚══════════════════════════════════════════════════════════╝"

done_step

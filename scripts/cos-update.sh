#!/usr/bin/env bash
# =============================================================================
# cos-update.sh — Cognitive OS update for existing installations
# =============================================================================
# Idempotent: safe to run multiple times.
#
# Usage:
#   bash scripts/cos-update.sh [OPTIONS]
#
# Options:
#   --pull-images      Pull latest Docker images before restarting services
#   --dry-run          Show what would happen without doing it
#   --help             Show this help message
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env"
ENV_EXAMPLE="${PROJECT_ROOT}/env.example"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.cognitive-os.yml"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
PULL_IMAGES=false
DRY_RUN=false
TOTAL_STEPS=7
STEP=0

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --pull-images)
      PULL_IMAGES=true
      shift
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --help|-h)
      cat <<'EOF'
cos-update.sh — Cognitive OS update for existing installations

USAGE
  bash scripts/cos-update.sh [OPTIONS]

OPTIONS
  --pull-images
      Pull latest Docker images before restarting services.
      NOTE: This may pull newer versions that haven't been tested.
      Pinned digest images will be unaffected unless digests are updated.

  --dry-run
      Print each step without executing it.

  --help
      Show this message.

EXAMPLES
  bash scripts/cos-update.sh
  bash scripts/cos-update.sh --pull-images
  bash scripts/cos-update.sh --dry-run
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

# Merge new vars from env.example into .env — never overwrite existing values
merge_env() {
  local example="$1"
  local target="$2"
  local added=0
  local skipped=0

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
    else
      skipped=$((skipped + 1))
    fi
  done < "${example}"

  echo "${added}:${skipped}"
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
  local timeout="${3:-90}"
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
echo "║          Cognitive OS — Update                           ║"
if [[ "${DRY_RUN}" == "true" ]]; then
echo "║  Mode:    DRY-RUN (no changes will be made)              ║"
fi
echo "╚══════════════════════════════════════════════════════════╝"

# ---------------------------------------------------------------------------
# Pre-flight: verify COS is installed
# ---------------------------------------------------------------------------
step "Pre-flight check"

if [[ ! -f "${PROJECT_ROOT}/cognitive-os.yaml" ]]; then
  err "cognitive-os.yaml not found. Is Cognitive OS installed in this directory?"
  err "Run: bash scripts/cos-bootstrap.sh"
  exit 1
fi
ok "cognitive-os.yaml found — COS installation detected"

if [[ ! -f "${ENV_FILE}" ]]; then
  warn ".env not found — will create from env.example"
fi

done_step

# ---------------------------------------------------------------------------
# Step 1 — Merge new env vars
# ---------------------------------------------------------------------------
step "Merge new env vars from env.example"

if [[ "${DRY_RUN}" == "true" ]]; then
  info "Would merge new vars from env.example into .env (never overwriting existing)"
  done_step
else
  if [[ ! -f "${ENV_FILE}" ]]; then
    cp "${ENV_EXAMPLE}" "${ENV_FILE}"
    ok "Created .env from env.example"
  else
    result=$(merge_env "${ENV_EXAMPLE}" "${ENV_FILE}")
    added="${result%%:*}"
    skipped="${result##*:}"
    if [[ "${added}" -gt 0 ]]; then
      ok "Added ${added} new variable(s) to .env (${skipped} existing preserved)"
    else
      ok ".env is up-to-date (${skipped} vars already present, none overwritten)"
    fi
  fi
  done_step
fi

# ---------------------------------------------------------------------------
# Step 2 — Pull images (optional)
# ---------------------------------------------------------------------------
step "Docker image pull"

if [[ "${DRY_RUN}" == "true" ]]; then
  if [[ "${PULL_IMAGES}" == "true" ]]; then
    info "Would run: docker compose pull"
  else
    info "Skipped (pass --pull-images to enable)"
  fi
  done_step
else
  if [[ "${PULL_IMAGES}" == "true" ]]; then
    if ! check_docker; then
      warn "Docker not available — skipping image pull."
    elif [[ ! -f "${COMPOSE_FILE}" ]]; then
      warn "Compose file not found — skipping image pull."
    else
      info "Pulling Docker images (this may take a while)..."
      docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" pull
      ok "Images pulled"
    fi
  else
    info "Skipped (pass --pull-images to pull latest images)"
  fi
  done_step
fi

# ---------------------------------------------------------------------------
# Step 3 — Restart changed services
# ---------------------------------------------------------------------------
step "Restart Docker services"

if [[ "${DRY_RUN}" == "true" ]]; then
  info "Would run: docker compose up -d (restart changed containers only)"
  done_step
else
  if ! check_docker; then
    warn "Docker not available — skipping service restart."
    done_step
  elif [[ ! -f "${COMPOSE_FILE}" ]]; then
    warn "Compose file not found — skipping service restart."
    done_step
  else
    # Load .env
    set -a
    # shellcheck source=/dev/null
    [[ -f "${ENV_FILE}" ]] && source "${ENV_FILE}"
    set +a

    # Capture which containers were running before
    running_before=$(docker compose -f "${COMPOSE_FILE}" ps --services --filter "status=running" 2>/dev/null || true)

    docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d

    running_after=$(docker compose -f "${COMPOSE_FILE}" ps --services --filter "status=running" 2>/dev/null || true)

    restarted=0
    if [[ -n "${running_before}" ]]; then
      while IFS= read -r svc; do
        [[ -n "${svc}" ]] && restarted=$((restarted + 1))
      done <<< "${running_after}"
    fi

    ok "Services updated (${restarted} running)"
    done_step
  fi
fi

# ---------------------------------------------------------------------------
# Step 4 — Health checks
# ---------------------------------------------------------------------------
step "Health checks"

if [[ "${DRY_RUN}" == "true" ]]; then
  info "Would check Langfuse and LiteLLM health endpoints"
  done_step
else
  if ! check_docker; then
    warn "Docker not available — skipping health checks."
    done_step
  else
    langfuse_port="${LANGFUSE_PORT:-3100}"
    # Only wait if langfuse is supposed to be running
    if docker compose -f "${COMPOSE_FILE}" ps langfuse-web 2>/dev/null | grep -q "running\|Up"; then
      wait_for_health "Langfuse" "http://localhost:${langfuse_port}/api/public/health" 90
    else
      info "Langfuse not running — skipping health check"
    fi

    litellm_port="${LITELLM_PORT:-4000}"
    if docker compose -f "${COMPOSE_FILE}" ps litellm 2>/dev/null | grep -q "running\|Up"; then
      wait_for_health "LiteLLM" "http://localhost:${litellm_port}/health" 60
    else
      info "LiteLLM not running — skipping health check"
    fi
    done_step
  fi
fi

# ---------------------------------------------------------------------------
# Step 5 — Langfuse API key provisioning (idempotent)
# ---------------------------------------------------------------------------
step "Langfuse API key provisioning"

LANGFUSE_SETUP_SCRIPT="${SCRIPT_DIR}/setup-langfuse.sh"

if [[ "${DRY_RUN}" == "true" ]]; then
  info "Would run: bash scripts/setup-langfuse.sh (skips if keys already set)"
  done_step
else
  if [[ -f "${LANGFUSE_SETUP_SCRIPT}" ]]; then
    bash "${LANGFUSE_SETUP_SCRIPT}" || warn "setup-langfuse.sh encountered an issue — check output above."
  else
    warn "setup-langfuse.sh not found — skipping."
  fi
  done_step
fi

# ---------------------------------------------------------------------------
# Step 6 — Rules/hooks sync
# ---------------------------------------------------------------------------
step "Rules and hooks sync (self-install)"

SELF_INSTALL_SCRIPT="${PROJECT_ROOT}/hooks/self-install.sh"

if [[ "${DRY_RUN}" == "true" ]]; then
  info "Would run: CLAUDE_PROJECT_DIR=${PROJECT_ROOT} bash hooks/self-install.sh"
  done_step
else
  if [[ -f "${SELF_INSTALL_SCRIPT}" ]]; then
    CLAUDE_PROJECT_DIR="${PROJECT_ROOT}" bash "${SELF_INSTALL_SCRIPT}" || warn "self-install.sh encountered an issue."
    ok "Rules and hooks synced"
  else
    warn "hooks/self-install.sh not found — skipping."
  fi
  done_step
fi

# ---------------------------------------------------------------------------
# Step 7 — Summary
# ---------------------------------------------------------------------------
step "Summary"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║          Cognitive OS — Update Complete                  ║"
if [[ "${DRY_RUN}" == "true" ]]; then
echo "║  Mode:    DRY-RUN — no changes were made                 ║"
fi
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  What happened:                                          ║"
echo "║    • New .env vars merged (existing preserved)           ║"
if [[ "${PULL_IMAGES}" == "true" ]]; then
echo "║    • Docker images pulled                                ║"
fi
echo "║    • Docker services restarted (changed containers only) ║"
echo "║    • Langfuse API keys verified                          ║"
echo "║    • Rules and hooks re-synced                           ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  Next: open Claude Code and run /cognitive-os-status     ║"
echo "╚══════════════════════════════════════════════════════════╝"

done_step

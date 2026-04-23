#!/usr/bin/env bash
# SCOPE: os-only
# =============================================================================
# cos-update.sh — Idempotent Cognitive OS update with verify + rollback (UX6)
# =============================================================================
# Safe to run any number of times. On the second and subsequent runs with no
# upstream changes, the script short-circuits with "Already up to date."
#
# Pipeline:
#   1. Pre-state snapshot  (SHA-256 of settings + listings of skills/rules/cos)
#   2. Backup + rotate     (.cognitive-os/backups/pre-update-<UTC-ts>/, keep 3)
#   3. Apply               (delegates to hooks/self-install.sh)
#   4. Post-state snapshot + diff
#   5. Verify              (re-run self-install, pytest audit, go build)
#   6. Rollback on verify failure (if --auto-rollback or interactive)
#
# Exit codes:
#   0  success (or already up to date)
#   1  apply failed
#   2  verify failed
#
# Usage:
#   bash scripts/cos-update.sh [OPTIONS]
#
# Flags:
#   --dry-run         Show what would happen, mutate nothing
#   --auto-rollback   On verify failure, automatically restore from backup
#   --no-verify       Skip the post-update verification suite
#   --force           Bypass the "already up to date" short-circuit
#   --pull-images     (legacy) delegated to docker compose pull
#   --help            Show this message
#
# Design notes:
#   - stdout is deterministic across runs with identical inputs. All run-specific
#     details (timestamps, backup paths, diff output) go to stderr so that two
#     --dry-run invocations produce byte-identical stdout (test_update_idempotent).
#   - bash 3.2 compatible — no `mapfile`, no associative arrays.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${PROJECT_ROOT}/hooks/_lib/portable.sh"
CLAUDE_DIR="${PROJECT_ROOT}/.claude"
COS_DIR="${PROJECT_ROOT}/.cognitive-os"
BACKUP_ROOT="${COS_DIR}/backups"
SETTINGS_FILE="${CLAUDE_DIR}/settings.json"
SELF_INSTALL_SCRIPT="${PROJECT_ROOT}/hooks/self-install.sh"
ENV_FILE="${PROJECT_ROOT}/.env"
ENV_EXAMPLE="${PROJECT_ROOT}/env.example"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.cognitive-os.yml"
PYPROJECT_FILE="${PROJECT_ROOT}/pyproject.toml"
STATE_DIR="${COS_DIR}/state"
PYPROJECT_SHA_FILE="${STATE_DIR}/pyproject.sha"
APPLY_EFF_PROFILE_SCRIPT="${SCRIPT_DIR}/apply-efficiency-profile.sh"
APPLY_EFF_PROFILE_SHA_FILE="${STATE_DIR}/apply-efficiency-profile.sha"
DOCKER_COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.cognitive-os.yml"
DOCKER_COMPOSE_SHA_FILE="${STATE_DIR}/docker-compose.sha"
REGISTER_MCPS_SCRIPT="${SCRIPT_DIR}/register-mcps.sh"
COGNITIVE_OS_YAML="${PROJECT_ROOT}/cognitive-os.yaml"

MAX_BACKUPS=3

# ---------------------------------------------------------------------------
# Flag defaults
# ---------------------------------------------------------------------------
DRY_RUN=false
AUTO_ROLLBACK=false
NO_VERIFY=false
FORCE=false
PULL_IMAGES=false

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)       DRY_RUN=true; shift ;;
    --auto-rollback) AUTO_ROLLBACK=true; shift ;;
    --no-verify)     NO_VERIFY=true; shift ;;
    --force)         FORCE=true; shift ;;
    --pull-images)   PULL_IMAGES=true; shift ;;
    --help|-h)
      cat <<'EOF'
cos-update.sh — Idempotent Cognitive OS update (UX6)

USAGE
  bash scripts/cos-update.sh [OPTIONS]

BEHAVIOR
  This script is idempotent: running it twice in a row with no upstream
  changes produces no mutations and short-circuits with "Already up to date."

  Pipeline:
    1. Capture pre-state snapshot (SHA-256 of settings + dir listings)
    2. Create backup under .cognitive-os/backups/pre-update-<UTC>/
       (rotated: only the last 3 backups are kept)
    3. Apply update via hooks/self-install.sh
    4. Diff post-state against pre-state
    5. Verify (re-run self-install; run pytest audit; go build)
    6. Rollback if verification fails (auto with --auto-rollback)

OPTIONS
  --dry-run
      Show planned actions without mutating the filesystem.
      Two --dry-run invocations produce identical stdout.

  --auto-rollback
      On verify failure, automatically restore settings.json from the most
      recent backup and prompt the user to re-run hooks/self-install.sh to
      rebuild symlinks.

  --no-verify
      Skip the post-update verification suite (faster but less safe).

  --force
      Bypass the "already up to date" short-circuit. Always runs the backup,
      apply, and verify pipeline end-to-end.

  --pull-images
      Legacy compatibility: delegates `docker compose pull` before apply.

  --help
      Show this message.

EXIT CODES
   0  success (including idempotent no-op)
   1  apply phase failed
   2  verify phase failed

EXAMPLES
  bash scripts/cos-update.sh
  bash scripts/cos-update.sh --dry-run
  bash scripts/cos-update.sh --auto-rollback
  bash scripts/cos-update.sh --no-verify --force
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
#   stdout — deterministic, stable across runs (used by test_update_idempotent)
#   stderr — run-specific (timestamps, paths, diffs, backup details)
# ---------------------------------------------------------------------------
say()  { printf '%s\n' "$*"; }               # deterministic stdout
note() { printf '%s\n' "$*" >&2; }           # run-specific stderr
warn() { printf 'WARN: %s\n' "$*" >&2; }
err()  { printf 'ERROR: %s\n' "$*" >&2; }

banner() {
  say "============================================================"
  say "  Cognitive OS — Update"
  say "  idempotent | verify | rollback"
  say "============================================================"
}

# ---------------------------------------------------------------------------
# Cross-platform SHA-256 helper (bash 3.2 compat; macOS + Linux)
# ---------------------------------------------------------------------------
sha256_of() {
  local file="$1"
  if [[ ! -f "$file" ]]; then
    echo "MISSING"
    return 0
  fi
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$file" | awk '{print $1}'
  elif command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$file" | awk '{print $1}'
  else
    # Fallback: size-based fingerprint (not cryptographic)
    wc -c < "$file" | tr -d ' '
  fi
}

# List entries in a directory as stable, sorted "name|type" lines.
# type = L (symlink), F (file), D (dir). MISSING if the directory does not exist.
list_dir() {
  local dir="$1"
  if [[ ! -d "$dir" ]]; then
    echo "MISSING"
    return 0
  fi
  # Enumerate non-recursively; bash 3.2: no globstar. Use find with depth 1.
  find "$dir" -mindepth 1 -maxdepth 1 \
    \( -type l -o -type f -o -type d \) 2>/dev/null | while IFS= read -r entry; do
      local base t
      base="$(basename "$entry")"
      if [[ -L "$entry" ]]; then t=L
      elif [[ -f "$entry" ]]; then t=F
      elif [[ -d "$entry" ]]; then t=D
      else t=?
      fi
      printf '%s|%s\n' "$base" "$t"
    done | LC_ALL=C sort
}

# ---------------------------------------------------------------------------
# Snapshot: capture the state that matters for idempotence + rollback
# ---------------------------------------------------------------------------
# Snapshot dumps four things to stdout (used to fingerprint and to diff):
#   SETTINGS_SHA=<hex>
#   SKILLS_LIST=<sorted>
#   RULES_LIST=<sorted>
#   COS_LIST=<sorted>
snapshot_into() {
  local out="$1"
  {
    echo "SETTINGS_SHA=$(sha256_of "$SETTINGS_FILE")"
    echo "--- SKILLS_LIST ---"
    list_dir "$COS_DIR/skills"
    echo "--- RULES_LIST ---"
    list_dir "$CLAUDE_DIR/rules/cos"
    echo "--- COS_LIST ---"
    list_dir "$COS_DIR"
  } > "$out"
}

# Fingerprint a snapshot file — a single hash representing the whole state.
fingerprint_of() {
  local snapshot="$1"
  if [[ ! -f "$snapshot" ]]; then
    echo "MISSING"
    return 0
  fi
  sha256_of "$snapshot"
}

# ---------------------------------------------------------------------------
# Backup + rotate
# ---------------------------------------------------------------------------
make_backup() {
  # Creates .cognitive-os/backups/pre-update-<UTC>/{settings.json,meta.txt,
  # skills.list,rules.list,cos.list}
  # Prints backup path to stderr.
  local ts dir
  ts="$(date -u +%Y%m%dT%H%M%SZ)"
  dir="${BACKUP_ROOT}/pre-update-${ts}"

  mkdir -p "$dir"

  if [[ -f "$SETTINGS_FILE" ]]; then
    cp "$SETTINGS_FILE" "$dir/settings.json"
  fi

  list_dir "$COS_DIR/skills"       > "$dir/skills.list" 2>/dev/null || true
  list_dir "$CLAUDE_DIR/rules/cos" > "$dir/rules.list"  2>/dev/null || true
  list_dir "$COS_DIR"              > "$dir/cos.list"    2>/dev/null || true

  {
    echo "timestamp_utc=${ts}"
    echo "project_root=${PROJECT_ROOT}"
    echo "settings_sha=$(sha256_of "$SETTINGS_FILE")"
    echo "git_head=$(git -C "$PROJECT_ROOT" rev-parse --short HEAD 2>/dev/null || echo unknown)"
  } > "$dir/meta.txt"

  note "Backup created: ${dir}"
  echo "$dir"
}

rotate_backups() {
  # Keep only the last MAX_BACKUPS pre-update-* directories (lexical sort).
  # bash 3.2 compatible: no mapfile; use while-read.
  [[ -d "$BACKUP_ROOT" ]] || return 0

  local all=()
  while IFS= read -r d; do
    [[ -n "$d" ]] && all+=("$d")
  done < <(find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -name 'pre-update-*' 2>/dev/null | LC_ALL=C sort)

  local total="${#all[@]}"
  if (( total <= MAX_BACKUPS )); then
    return 0
  fi

  local to_prune=$(( total - MAX_BACKUPS ))
  local i
  for (( i=0; i<to_prune; i++ )); do
    local victim="${all[$i]}"
    note "Rotating out old backup: ${victim}"
    rm -rf "$victim"
  done
}

# ---------------------------------------------------------------------------
# Apply phase: delegate to self-install
# ---------------------------------------------------------------------------
run_self_install() {
  # Returns the self-install exit code. Captures output to stderr for
  # transparency but does NOT propagate it to stdout (stdout is deterministic).
  if [[ ! -f "$SELF_INSTALL_SCRIPT" ]]; then
    warn "hooks/self-install.sh not found — nothing to apply"
    return 0
  fi
  if COGNITIVE_OS_PROJECT_DIR="$PROJECT_ROOT" bash "$SELF_INSTALL_SCRIPT" >&2; then
    return 0
  else
    return $?
  fi
}

# ---------------------------------------------------------------------------
# Python dependency sync — runs `uv sync` only when pyproject.toml changes.
# Caches the SHA-256 of pyproject.toml in .cognitive-os/state/pyproject.sha so
# that subsequent updates without upstream changes are no-ops.
# ---------------------------------------------------------------------------
sync_python_deps_if_changed() {
  [[ -f "$PYPROJECT_FILE" ]] || return 0

  local current_sha previous_sha=""
  current_sha="$(sha256_of "$PYPROJECT_FILE")"
  if [[ -f "$PYPROJECT_SHA_FILE" ]]; then
    previous_sha="$(cat "$PYPROJECT_SHA_FILE" 2>/dev/null || echo "")"
  fi

  if [[ "$current_sha" == "$previous_sha" ]]; then
    note "pyproject.toml unchanged (sha ${current_sha:0:8}); skipping uv sync"
    return 0
  fi

  if ! command -v uv >/dev/null 2>&1; then
    warn "pyproject.toml changed but 'uv' is not installed — skipping dependency sync"
    warn "  install uv (https://docs.astral.sh/uv/) and re-run to sync Python deps"
    return 0
  fi

  note "pyproject.toml changed (${previous_sha:0:8}→${current_sha:0:8}); running uv sync"
  if ( cd "$PROJECT_ROOT" && uv sync >&2 ); then
    mkdir -p "$STATE_DIR"
    printf '%s\n' "$current_sha" > "$PYPROJECT_SHA_FILE"
    note "pyproject.sha cache updated"
    return 0
  else
    warn "uv sync failed; not updating pyproject.sha (will retry on next update)"
    return 1
  fi
}

# ---------------------------------------------------------------------------
# Settings regeneration — re-runs scripts/apply-efficiency-profile.sh when that
# script changes. Mirrors sync_python_deps_if_changed: caches the SHA-256 of
# apply-efficiency-profile.sh in .cognitive-os/state/apply-efficiency-profile.sha
# so subsequent updates without upstream changes are no-ops.
#
# This closes the downstream-project drift gap: when cos-update.sh copies a
# new apply-efficiency-profile.sh (e.g. adding a hook registration), the
# downstream's .claude/settings.json would otherwise stay stale because
# cos-update.sh only runs self-install — not the profile generator.
#
# Failure is non-fatal (WARN + continue), same pattern as uv sync.
# Missing script (edge case: minimal install) is a silent skip.
# ---------------------------------------------------------------------------
regenerate_settings_if_profile_changed() {
  if [[ ! -f "$APPLY_EFF_PROFILE_SCRIPT" ]]; then
    # Silent skip — minimal install may not ship the profile generator.
    return 0
  fi

  local current_sha previous_sha=""
  current_sha="$(sha256_of "$APPLY_EFF_PROFILE_SCRIPT")"
  if [[ -f "$APPLY_EFF_PROFILE_SHA_FILE" ]]; then
    previous_sha="$(cat "$APPLY_EFF_PROFILE_SHA_FILE" 2>/dev/null || echo "")"
  fi

  if [[ "$current_sha" == "$previous_sha" && "$FORCE" != "true" ]]; then
    note "apply-efficiency-profile.sh unchanged (sha ${current_sha:0:8}); skipping settings regen"
    return 0
  fi

  # Resolve current profile from cognitive-os.yaml; default to 'default'.
  # Use grep+awk for bash 3.2 compatibility (no yq/python dependency here).
  local profile=""
  if [[ -f "$COGNITIVE_OS_YAML" ]]; then
    profile="$(grep -A1 '^efficiency:' "$COGNITIVE_OS_YAML" 2>/dev/null \
      | grep 'profile:' \
      | awk '{print $2}' \
      | tr -d "'\"" \
      | head -1)"
  fi
  if [[ -z "$profile" ]]; then
    profile="default"
  fi

  note "apply-efficiency-profile.sh changed (${previous_sha:0:8}→${current_sha:0:8}); regenerating settings.json with profile '${profile}'"
  if bash "$APPLY_EFF_PROFILE_SCRIPT" "$profile" >&2; then
    mkdir -p "$STATE_DIR"
    printf '%s\n' "$current_sha" > "$APPLY_EFF_PROFILE_SHA_FILE"
    note "apply-efficiency-profile.sha cache updated"
    return 0
  else
    warn "apply-efficiency-profile.sh failed; not updating sha cache (will retry on next update)"
    return 1
  fi
}

# ---------------------------------------------------------------------------
# Auto-recreate docker containers when docker-compose.cognitive-os.yml changes.
# Mirrors regenerate_settings_if_profile_changed: caches SHA-256 of the compose
# file in .cognitive-os/state/docker-compose.sha. When the pin sha of any image
# is updated upstream, this function detects the compose change and runs
# `docker compose pull` + `up -d --force-recreate` so running containers pick
# up the new images.
#
# Without this, downstream projects update compose via cos-update but their
# containers keep running the old images indefinitely (restart: unless-stopped
# doesn't recreate with the new pin). The 2026-04-21 langfuse-worker incident
# (crash loop from old entrypoint that was removed upstream) was exactly this
# scenario.
#
# Graceful degradation:
#   - compose file missing → silent skip
#   - docker binary missing → skip with note (running compose stack not our concern)
#   - docker daemon not up → skip (user may not have started docker yet)
#   - pull failure → WARN, do NOT recreate (old containers keep running, no worse)
#   - up -d failure → WARN + revert sha cache so next run retries
#
# Failure is non-fatal. Honors --force to re-run even on matching sha.
# ---------------------------------------------------------------------------
recreate_docker_if_compose_changed() {
  [[ -f "$DOCKER_COMPOSE_FILE" ]] || return 0

  # Locate docker binary (may be outside PATH in OrbStack installs)
  local docker=""
  for candidate in \
    /opt/homebrew/bin/docker \
    /usr/local/bin/docker \
    /Applications/OrbStack.app/Contents/Resources/bin/docker
  do
    [[ -x "$candidate" ]] && { docker="$candidate"; break; }
  done
  [[ -n "$docker" ]] || docker="$(command -v docker 2>/dev/null || true)"
  if [[ -z "$docker" ]]; then
    note "docker binary not found — skipping container freshness check"
    return 0
  fi

  # Daemon up? Fail silently if not.
  if ! timeout 2 "$docker" info >/dev/null 2>&1; then
    note "docker daemon not responding — skipping container recreate"
    return 0
  fi

  local current_sha previous_sha=""
  current_sha="$(sha256_of "$DOCKER_COMPOSE_FILE")"
  if [[ -f "$DOCKER_COMPOSE_SHA_FILE" ]]; then
    previous_sha="$(cat "$DOCKER_COMPOSE_SHA_FILE" 2>/dev/null || echo "")"
  fi

  if [[ "$current_sha" == "$previous_sha" && "$FORCE" != "true" ]]; then
    note "docker-compose.cognitive-os.yml unchanged (sha ${current_sha:0:8}); skipping container recreate"
    return 0
  fi

  note "docker-compose.cognitive-os.yml changed (${previous_sha:0:8}→${current_sha:0:8}); pulling + recreating cognitive-os containers"
  if [[ "$DRY_RUN" == "true" ]]; then
    note "[DRY RUN] would run: docker compose -f $DOCKER_COMPOSE_FILE pull && up -d --force-recreate"
    return 0
  fi

  if ! "$docker" compose -f "$DOCKER_COMPOSE_FILE" pull >&2; then
    warn "docker compose pull failed; not updating sha cache (will retry on next update)"
    return 1
  fi

  # Note: --force-recreate targets running services only; services that aren't
  # up stay down. Build failures (e.g. Dockerfile pip issues) in ONE service
  # can abort the entire recreate — use --no-build where safe, or target only
  # pulled services. We rely on the user running `docker compose build` manually
  # when Dockerfile changes are involved.
  if "$docker" compose -f "$DOCKER_COMPOSE_FILE" up -d --force-recreate --no-build >&2; then
    mkdir -p "$STATE_DIR"
    printf '%s\n' "$current_sha" > "$DOCKER_COMPOSE_SHA_FILE"
    note "docker-compose.sha cache updated"
    return 0
  else
    warn "docker compose up failed; not updating sha cache (will retry on next update)"
    return 1
  fi
}

# ---------------------------------------------------------------------------
# MCP registration — calls scripts/register-mcps.sh with the profile from
# cognitive-os.yaml. Caching is handled inside register-mcps.sh (mcps.sha).
# Failure is non-fatal (WARN + continue), matching the uv sync behavior.
# ---------------------------------------------------------------------------
register_mcps_if_changed() {
  [[ -f "$REGISTER_MCPS_SCRIPT" ]] || { warn "register-mcps.sh not found — skipping MCP registration"; return 0; }

  # Read profile from cognitive-os.yaml; default to 'standard' if absent.
  # Use grep+awk for bash 3.2 compatibility (no yq/python dependency here).
  local profile
  profile="$(grep -E '^\s*profile:' "$COGNITIVE_OS_YAML" 2>/dev/null | head -1 | awk '{print $2}' | tr -d '"' | tr -d "'")"
  if [[ -z "$profile" ]]; then
    profile="standard"
    note "cognitive-os.yaml has no 'profile:' key; defaulting to '${profile}'"
  fi

  local dry_flag=""
  [[ "$DRY_RUN" == "true" ]] && dry_flag="--dry-run"

  note "Registering MCPs for profile '${profile}'..."
  if bash "$REGISTER_MCPS_SCRIPT" --profile "$profile" --cache-dir "$STATE_DIR" ${dry_flag} >&2; then
    return 0
  else
    warn "MCP registration encountered errors (see log above) — continuing update"
    return 0   # non-fatal
  fi
}

# Optional docker compose pull (legacy --pull-images)
pull_images_if_requested() {
  [[ "$PULL_IMAGES" == "true" ]] || return 0
  if ! command -v docker >/dev/null 2>&1; then
    warn "--pull-images requested but docker not available; skipping"
    return 0
  fi
  if [[ ! -f "$COMPOSE_FILE" ]]; then
    warn "--pull-images requested but compose file not found; skipping"
    return 0
  fi
  note "Pulling docker images..."
  if [[ -f "$ENV_FILE" ]]; then
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" pull >&2 || warn "docker compose pull failed"
  else
    docker compose -f "$COMPOSE_FILE" pull >&2 || warn "docker compose pull failed"
  fi
}

# ---------------------------------------------------------------------------
# Verification phase
# ---------------------------------------------------------------------------
verify_installation() {
  # Returns 0 on pass, non-zero on failure. Each check runs independently and
  # contributes a WARN (non-fatal) or FAIL (fatal) to the verdict.
  local failures=0

  note "Verify 1/3: re-running self-install (must exit 0)"
  if ! COGNITIVE_OS_PROJECT_DIR="$PROJECT_ROOT" bash "$SELF_INSTALL_SCRIPT" >&2; then
    err "self-install re-run failed"
    failures=$((failures + 1))
  fi

  note "Verify 2/3: pytest audit suite (fast)"
  if command -v python3 >/dev/null 2>&1 && [[ -d "$PROJECT_ROOT/tests/audit" ]]; then
    if ! ( cd "$PROJECT_ROOT" && python3 -m pytest tests/audit/ -m audit --tb=no -q >&2 ); then
      err "pytest audit suite failed"
      failures=$((failures + 1))
    fi
  else
    note "  (skipped: python3 or tests/audit/ not available)"
  fi

  note "Verify 3/3: go build (if cmd/cos-dispatch exists)"
  if [[ -d "$PROJECT_ROOT/cmd/cos-dispatch" ]]; then
    if command -v go >/dev/null 2>&1; then
      if ! ( cd "$PROJECT_ROOT" && go build ./... >&2 ); then
        err "go build ./... failed"
        failures=$((failures + 1))
      fi
    else
      warn "  go not installed — skipping build check"
    fi
  else
    note "  (skipped: cmd/cos-dispatch not present)"
  fi

  return "$failures"
}

# ---------------------------------------------------------------------------
# Rollback
# ---------------------------------------------------------------------------
latest_backup_dir() {
  [[ -d "$BACKUP_ROOT" ]] || { echo ""; return 0; }
  local last=""
  while IFS= read -r d; do
    [[ -n "$d" ]] && last="$d"
  done < <(find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -name 'pre-update-*' 2>/dev/null | LC_ALL=C sort)
  echo "$last"
}

perform_rollback() {
  local backup_dir="$1"
  if [[ -z "$backup_dir" || ! -d "$backup_dir" ]]; then
    err "no backup directory available for rollback"
    return 1
  fi

  note "Rolling back from: $backup_dir"

  if [[ -f "$backup_dir/settings.json" ]]; then
    cp "$backup_dir/settings.json" "$SETTINGS_FILE"
    note "  restored .claude/settings.json"
  fi

  note "  NOTE: symlinks under .claude/skills/, .claude/rules/cos/, and"
  note "        .cognitive-os/ are NOT automatically restored. Please run:"
  note "          bash hooks/self-install.sh"
  note "        to rebuild them from the current source tree."
  return 0
}

prompt_or_auto_rollback() {
  local backup_dir="$1"
  if [[ "$AUTO_ROLLBACK" == "true" ]]; then
    note "--auto-rollback set; restoring from backup automatically"
    perform_rollback "$backup_dir"
    return
  fi

  if [[ ! -t 0 ]]; then
    note "non-interactive shell; skipping rollback prompt (use --auto-rollback)"
    return
  fi

  local reply
  printf 'Verify failed. Roll back settings.json from %s? [y/N] ' "$backup_dir" >&2
  read -r reply || reply=""
  case "$reply" in
    y|Y|yes|YES) perform_rollback "$backup_dir" ;;
    *)           note "rollback declined by user" ;;
  esac
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
banner

if [[ "$DRY_RUN" == "true" ]]; then
  say "[dry-run] No files will be modified."
fi

# --- Pre-flight ------------------------------------------------------------
if [[ ! -f "${PROJECT_ROOT}/cognitive-os.yaml" ]]; then
  err "cognitive-os.yaml not found at ${PROJECT_ROOT}"
  err "Is this a Cognitive OS project root?"
  exit 1
fi
say "pre-flight: cognitive-os.yaml found"

# Ensure the backup root exists (harmless when dry-run and no writes follow)
if [[ "$DRY_RUN" != "true" ]]; then
  mkdir -p "$BACKUP_ROOT"
fi

# --- Pre-state snapshot ----------------------------------------------------
PRE_SNAPSHOT="$(mktemp -t cos-update.XXXXXX)"
snapshot_into "$PRE_SNAPSHOT"
PRE_FP="$(fingerprint_of "$PRE_SNAPSHOT")"
note "pre-state fingerprint: ${PRE_FP}"

# --- Short-circuit check (dry-run friendly) --------------------------------
# For dry-run we probe what self-install WOULD do by running it in a scratch
# fingerprint comparison only if not forced. But to keep --dry-run idempotent
# and mutation-free, we never execute self-install in dry-run — we just report.
if [[ "$DRY_RUN" == "true" ]]; then
  say "plan:"
  say "  - capture pre-state snapshot (SHA-256 of settings + listings)"
  say "  - create backup at .cognitive-os/backups/pre-update-<UTC>/"
  say "  - rotate backups to last ${MAX_BACKUPS}"
  say "  - sync Python deps via uv sync if pyproject.toml changed"
  say "  - regenerate settings.json via scripts/apply-efficiency-profile.sh if the profile script changed"
  say "  - register mcps via scripts/register-mcps.sh if manifest changed"
  say "  - run hooks/self-install.sh"
  say "  - capture post-state snapshot and diff against pre-state"
  if [[ "$NO_VERIFY" == "true" ]]; then
    say "  - skip verification (--no-verify)"
  else
    say "  - verify: re-run install hooks, pytest audit, go build"
  fi
  if [[ "$AUTO_ROLLBACK" == "true" ]]; then
    say "  - on verify failure: auto-rollback settings.json"
  fi
  rm -f "$PRE_SNAPSHOT"
  exit 0
fi

# --- Backup + rotate -------------------------------------------------------
BACKUP_DIR="$(make_backup)"
rotate_backups

# --- Apply -----------------------------------------------------------------
pull_images_if_requested

# Sync Python dependencies BEFORE self-install so that any new deps introduced
# upstream in pyproject.toml are present when self-install.sh runs.
# Failure here is a WARN (does not abort the update) so that partial offline
# environments still get the self-install updates applied.
sync_python_deps_if_changed || warn "python dependency sync encountered errors (see log above)"

# Regenerate .claude/settings.json when apply-efficiency-profile.sh has changed.
# Done BEFORE self-install so self-install operates on the refreshed settings.
# Placed after file sync (sync_python_deps_if_changed above) and before verify.
regenerate_settings_if_profile_changed || warn "settings regeneration encountered errors (see log above)"

# Recreate docker containers if compose changed (closes the image-drift gap
# — see recreate_docker_if_compose_changed docstring for the 2026-04-21
# incident that motivated this).
recreate_docker_if_compose_changed || warn "docker container recreate encountered errors (see log above)"

register_mcps_if_changed

apply_rc=0
if ! run_self_install; then
  apply_rc=$?
fi

# --- Post-state snapshot + diff -------------------------------------------
POST_SNAPSHOT="$(mktemp -t cos-update.XXXXXX)"
snapshot_into "$POST_SNAPSHOT"
POST_FP="$(fingerprint_of "$POST_SNAPSHOT")"
note "post-state fingerprint: ${POST_FP}"

if [[ "$PRE_FP" == "$POST_FP" && "$FORCE" != "true" ]]; then
  say "Already up to date. No changes applied."
else
  if [[ "$PRE_FP" == "$POST_FP" ]]; then
    say "State unchanged (running under --force)."
  else
    say "Update applied."
    note "diff summary:"
    diff "$PRE_SNAPSHOT" "$POST_SNAPSHOT" >&2 || true
  fi
fi

rm -f "$PRE_SNAPSHOT" "$POST_SNAPSHOT"

# Apply failure is distinct from verify failure.
if [[ $apply_rc -ne 0 ]]; then
  err "apply phase failed (self-install exit ${apply_rc})"
  exit 1
fi

# --- Verify ----------------------------------------------------------------
if [[ "$NO_VERIFY" == "true" ]]; then
  say "verify: skipped (--no-verify)"
  say "Done."
  exit 0
fi

say "verify: running checks..."
verify_failures=0
if ! verify_installation; then
  verify_failures=$?
fi

if (( verify_failures > 0 )); then
  err "verify phase failed (${verify_failures} check(s) failed)"
  prompt_or_auto_rollback "$BACKUP_DIR"
  exit 2
fi

say "verify: all checks passed"
say "Done."
exit 0

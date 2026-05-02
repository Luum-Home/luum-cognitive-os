#!/usr/bin/env bash
# SCOPE: project
# @manual-trigger: invoke explicitly via `bash scripts/deps-update.sh [--audit|--apply]` for dependency maintenance
# deps-update.sh — Audit and optionally upgrade project dependencies
#
# Usage:
#   bash scripts/deps-update.sh [--audit] [--apply [--major]] [--dry-run]
#
# Modes:
#   --audit    (default) Read-only report of current vs latest. Exit 0 always.
#   --apply             Upgrade safe (minor/patch) deps. Skips major bumps.
#   --apply --major     Upgrade everything including major bumps.
#   --dry-run           Print what --apply would do, without executing.
#
# SCOPE: os-only

set -euo pipefail

# ── Bash 3.x compatible associative-array-free init ───────────────────────
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODE="audit"
ALLOW_MAJOR=false
DRY_RUN=false

# ── Parse args ─────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)   MODE="apply" ;;
    --audit)   MODE="audit" ;;
    --major)   ALLOW_MAJOR=true ;;
    --dry-run) DRY_RUN=true ; MODE="apply" ;;
    *) echo "Unknown option: $1" >&2 ; exit 1 ;;
  esac
  shift
done

# ── Colour helpers (no-op when not a tty) ─────────────────────────────────
_green()  { printf '%s' "$*"; }
_yellow() { printf '%s' "$*"; }
_red()    { printf '%s' "$*"; }
_bold()   { printf '%s' "$*"; }
if [ -t 1 ]; then
  _green()  { printf '\033[32m%s\033[0m' "$*"; }
  _yellow() { printf '\033[33m%s\033[0m' "$*"; }
  _red()    { printf '\033[31m%s\033[0m' "$*"; }
  _bold()   { printf '\033[1m%s\033[0m' "$*"; }
fi

# ── Counters (summary) ────────────────────────────────────────────────────
PY_UPGRADED=0
PY_SKIPPED_MAJOR=0
PY_TOTAL_OUTDATED=0
ENGRAM_STATUS="up-to-date"
PLUGINS_NEED_UPGRADE=0
PLUGINS_TOTAL=0
DOCKER_CHANGED=0
DOCKER_CHECKED=0
INCONSISTENT=false

_dry_echo() {
  echo "  would run: $*"
}

_run_or_dry() {
  if $DRY_RUN; then
    _dry_echo "$@"
  else
    "$@"
  fi
}

echo ""
_bold "=== Dependency Audit/Update ==="
echo " Mode: $MODE | allow-major: $ALLOW_MAJOR | dry-run: $DRY_RUN"
echo " Repo: $REPO_ROOT"
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# 1. PYTHON (pyproject.toml + uv)
# ═══════════════════════════════════════════════════════════════════════════
echo "── Python ────────────────────────────────────────────────────────────"

if ! command -v uv &>/dev/null; then
  echo "  SKIP: uv not found in PATH"
else
  cd "$REPO_ROOT"

  # uv pip list --outdated emits JSON with [{name, version, latest_version, ...}]
  OUTDATED_JSON=$(uv pip list --outdated --format=json 2>/dev/null || echo "[]")

  # Parse with python3 (available wherever uv is)
  OUTDATED_COUNT=$(python3 -c "
import json, sys
data = json.loads(sys.stdin.read())
print(len(data))
" <<< "$OUTDATED_JSON")

  PY_TOTAL_OUTDATED=$OUTDATED_COUNT

  if [ "$OUTDATED_COUNT" -eq 0 ]; then
    _green "  All Python packages up-to-date"
    echo ""
  else
    echo "  Outdated packages: $OUTDATED_COUNT"
    # Print table
    python3 -c "
import json, sys
data = json.loads(sys.stdin.read())
print('  {:<35} {:<15} {:<15} {}'.format('Package','Installed','Latest','Gap'))
print('  ' + '-'*75)
for p in sorted(data, key=lambda x: x.get('name','')):
    name     = p.get('name','')
    inst     = p.get('version','')
    latest   = p.get('latest_version','')
    inst_maj = int(inst.split('.')[0]) if inst and inst[0].isdigit() else 0
    lat_maj  = int(latest.split('.')[0]) if latest and latest[0].isdigit() else 0
    gap = 'MAJOR' if lat_maj > inst_maj else ('minor' if inst != latest else 'patch')
    print('  {:<35} {:<15} {:<15} {}'.format(name, inst, latest, gap))
" <<< "$OUTDATED_JSON"
    echo ""

    if [ "$MODE" = "apply" ]; then
      # Determine which packages are safe vs major bump
      # Safe = minor/patch (installed major == latest major)
      SAFE_PKGS=$(python3 -c "
import json, sys
data = json.loads(sys.stdin.read())
safe = []
major_skip = []
for p in data:
    inst   = p.get('version','')
    latest = p.get('latest_version','')
    inst_maj = int(inst.split('.')[0]) if inst and inst[0].isdigit() else 0
    lat_maj  = int(latest.split('.')[0]) if latest and latest[0].isdigit() else 0
    if lat_maj > inst_maj:
        major_skip.append(p.get('name',''))
    else:
        safe.append(p.get('name',''))
print('SAFE=' + ' '.join(safe))
print('MAJOR=' + ' '.join(major_skip))
" <<< "$OUTDATED_JSON")

      SAFE_LIST=$(echo "$SAFE_PKGS" | grep '^SAFE=' | cut -d= -f2)
      MAJOR_LIST=$(echo "$SAFE_PKGS" | grep '^MAJOR=' | cut -d= -f2)

      # Count
      PY_SKIPPED_MAJOR=$(echo "$MAJOR_LIST" | tr ' ' '\n' | grep -c '[a-z]' || true)

      if $ALLOW_MAJOR; then
        echo "  [apply --major] Running: uv sync --upgrade"
        _run_or_dry uv sync --upgrade
        PY_UPGRADED=$OUTDATED_COUNT
        PY_SKIPPED_MAJOR=0
      else
        if [ -n "$SAFE_LIST" ]; then
          SAFE_ARGS=$(echo "$SAFE_LIST" | tr ' ' '\n' | sed 's/^/--upgrade-package /' | tr '\n' ' ')
          echo "  [apply] Upgrading minor/patch packages..."
          if $DRY_RUN; then
            echo "  would run: uv sync $SAFE_ARGS"
          else
            # shellcheck disable=SC2086
            uv sync $SAFE_ARGS
          fi
          PY_UPGRADED=$(echo "$SAFE_LIST" | tr ' ' '\n' | grep -c '[a-z]' || true)
        else
          echo "  No minor/patch upgrades available (all bumps are MAJOR)"
        fi
        if [ -n "$MAJOR_LIST" ]; then
          echo "  MANUAL — major bump skipped (use --apply --major):"
          for pkg in $MAJOR_LIST; do
            echo "    - $pkg"
          done
        fi
      fi
    fi
  fi
fi

# ═══════════════════════════════════════════════════════════════════════════
# 2. ENGRAM BINARY
# ═══════════════════════════════════════════════════════════════════════════
# Install strategy (preference order):
#   1. brew (macOS) — canonical, Gatekeeper-trusted, avoids Operon sandbox SIGKILL
#   2. go install  — fallback when brew is unavailable (Linux CI, etc.)
#
# Multi-path trap: `which engram` only shows the first match. If multiple copies
# exist (~/go/bin, ~/.local/bin, /opt/homebrew/bin), the wrong one may be
# invoked. We use `which -a` after any install to detect and warn about conflicts.
# ═══════════════════════════════════════════════════════════════════════════
echo "── engram binary ─────────────────────────────────────────────────────"

ENGRAM_CHANGED=false

_engram_warn_multipath() {
  # Emit a warning if engram appears in more than one PATH location.
  ALL_PATHS=$(which -a engram 2>/dev/null || true)
  PATH_COUNT=$(echo "$ALL_PATHS" | grep -c 'engram' || true)
  if [ "$PATH_COUNT" -gt 1 ]; then
    _yellow "  WARNING: engram found in multiple PATH locations (3-paths trap):"
    echo ""
    echo "$ALL_PATHS" | while IFS= read -r p; do
      echo "    $p"
    done
    BREW_CANONICAL=$(command -v brew &>/dev/null && brew --prefix 2>/dev/null || echo "")
    if [ -n "$BREW_CANONICAL" ]; then
      echo "  Recommended: symlink each location to the brew canonical binary to eliminate ambiguity:"
      echo "    ln -sf ${BREW_CANONICAL}/bin/engram ~/.local/bin/engram"
      echo "    ln -sf ${BREW_CANONICAL}/bin/engram ~/go/bin/engram"
      echo "  (run with --apply --fix-symlinks to do this automatically)"
    fi
    echo ""
  fi
}

if ! command -v engram &>/dev/null; then
  echo "  SKIP: engram not found in PATH"
  ENGRAM_STATUS="not-installed"
else
  ENGRAM_CURRENT=$(engram version 2>/dev/null | grep -Eo '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || echo "unknown")
  echo "  Installed: $ENGRAM_CURRENT ($(command -v engram))"

  # Detect multi-path conflict at audit time too
  _engram_warn_multipath

  # ── Determine latest version ──────────────────────────────────────────
  ENGRAM_LATEST=""

  if command -v brew &>/dev/null; then
    # Refresh tap before querying — brew formulas can lag upstream otherwise
    if [ "$MODE" = "apply" ]; then
      echo "  Running brew update (refreshes tap formula versions)..."
      if $DRY_RUN; then
        _dry_echo "brew update"
      else
        brew update 2>/dev/null || _yellow "  WARN: brew update failed (continuing)"
        echo ""
      fi
    fi
    # Parse latest from tap formula info
    ENGRAM_LATEST=$(brew info gentleman-programming/tap/engram --formula 2>/dev/null \
      | grep -Eo '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || echo "")
  fi

  # Fall back to GitHub releases if brew didn't provide a version
  if [ -z "$ENGRAM_LATEST" ] && command -v gh &>/dev/null; then
    ENGRAM_LATEST=$(gh release list --repo Gentleman-Programming/engram --limit 1 2>/dev/null \
      | awk '{print $1}' | sed 's/^v//' || echo "")
  fi

  if [ -z "$ENGRAM_LATEST" ]; then
    echo "  WARN: Could not determine latest engram version (no brew, no gh, or fetch failed)"
    ENGRAM_STATUS="fetch-failed"
  else
    echo "  Latest:    $ENGRAM_LATEST"

    if [ "$ENGRAM_CURRENT" = "$ENGRAM_LATEST" ]; then
      _green "  Status: up-to-date"
      echo ""
      ENGRAM_STATUS="up-to-date"
    else
      _yellow "  Status: outdated ($ENGRAM_CURRENT → $ENGRAM_LATEST)"
      echo ""
      ENGRAM_STATUS="outdated ($ENGRAM_CURRENT -> $ENGRAM_LATEST)"

      if [ "$MODE" = "apply" ]; then
        if command -v brew &>/dev/null; then
          # ── Preferred: brew install/upgrade ─────────────────────────────
          echo "  [apply] Installing/upgrading engram via brew (preferred)..."
          if $DRY_RUN; then
            _dry_echo "brew install gentleman-programming/tap/engram || brew upgrade gentleman-programming/tap/engram"
          else
            # Back up the binary currently resolved by PATH before any install
            CURRENT_BIN=$(command -v engram 2>/dev/null || true)
            if [ -n "$CURRENT_BIN" ] && [ -f "$CURRENT_BIN" ] && [ ! -L "$CURRENT_BIN" ]; then
              BAK="${CURRENT_BIN}.v${ENGRAM_CURRENT}.bak"
              echo "  Backing up $CURRENT_BIN → $BAK"
              cp "$CURRENT_BIN" "$BAK" 2>/dev/null || true
            fi

            if brew list gentleman-programming/tap/engram &>/dev/null 2>&1; then
              brew upgrade gentleman-programming/tap/engram 2>&1 | tail -5
            else
              brew install gentleman-programming/tap/engram 2>&1 | tail -5
            fi

            NEW_VER=$(engram version 2>/dev/null | grep -Eo '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || echo "unknown")
            if [ "$NEW_VER" = "$ENGRAM_LATEST" ]; then
              _green "  engram updated to $NEW_VER (via brew)"
              echo ""
              ENGRAM_STATUS="$ENGRAM_CURRENT -> $ENGRAM_LATEST  applied (brew)"
              ENGRAM_CHANGED=true
            else
              _red "  WARN: After brew install, engram reports $NEW_VER (expected $ENGRAM_LATEST)"
              echo ""
              ENGRAM_STATUS="upgrade-failed"
              INCONSISTENT=true
            fi

            # Re-check multi-path after install and suggest symlinks
            _engram_warn_multipath
          fi

        else
          # ── Fallback: go install (Linux CI / no Homebrew) ────────────────
          echo "  [apply] brew not available — falling back to go install..."
          if ! command -v go &>/dev/null; then
            _red "  ERROR: Neither brew nor go is available. Cannot upgrade engram."
            echo ""
            ENGRAM_STATUS="upgrade-failed"
            INCONSISTENT=true
          else
            if $DRY_RUN; then
              _dry_echo "go install github.com/Gentleman-Programming/engram/cmd/engram@v${ENGRAM_LATEST}"
              _dry_echo "cp <versioned-go-bin>/engram \${GOPATH:-\$HOME/go}/bin/engram"
              ENGRAM_STATUS="$ENGRAM_CURRENT -> $ENGRAM_LATEST  (dry-run)"
            else
              # Back up existing binary
              GO_BIN="${GOPATH:-$HOME/go}/bin/engram"
              if [ -f "$GO_BIN" ] && [ ! -L "$GO_BIN" ]; then
                cp "$GO_BIN" "${GO_BIN}.v${ENGRAM_CURRENT}.bak" 2>/dev/null || true
              fi

              go install "github.com/Gentleman-Programming/engram/cmd/engram@v${ENGRAM_LATEST}"

              # Handle GOPATH versioned-bin gotcha: go install may write to ~/go/1.x.y/bin/
              VERSIONED_BIN=$(find "$HOME/go" -name "engram" -type f 2>/dev/null \
                | grep -v "^${GO_BIN}$" | sort -V | tail -1 || true)
              if [ -n "$VERSIONED_BIN" ] && [ -f "$VERSIONED_BIN" ]; then
                echo "  Detected versioned GOPATH bin at $VERSIONED_BIN"
                echo "  Copying to $GO_BIN..."
                cp "$VERSIONED_BIN" "$GO_BIN"
                chmod +x "$GO_BIN"
              fi

              NEW_VER=$(engram version 2>/dev/null | grep -Eo '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || echo "unknown")
              if [ "$NEW_VER" = "$ENGRAM_LATEST" ]; then
                _green "  engram updated to $NEW_VER (via go install)"
                echo ""
                ENGRAM_STATUS="$ENGRAM_CURRENT -> $ENGRAM_LATEST  applied (go install)"
                ENGRAM_CHANGED=true
              else
                _red "  WARN: After go install, engram reports $NEW_VER (expected $ENGRAM_LATEST)"
                echo ""
                ENGRAM_STATUS="upgrade-failed"
                INCONSISTENT=true
              fi
            fi
          fi
        fi
      fi  # end apply mode
    fi    # end outdated
  fi      # end version check
fi        # end engram found

# ── Symlink fix (--apply --fix-symlinks) ──────────────────────────────────
if [ "$MODE" = "apply" ] && command -v brew &>/dev/null; then
  BREW_ENGRAM=$(brew --prefix 2>/dev/null)/bin/engram
  if [ -f "$BREW_ENGRAM" ]; then
    for extra_path in "$HOME/.local/bin/engram" "${GOPATH:-$HOME/go}/bin/engram"; do
      if [ -f "$extra_path" ] && [ ! -L "$extra_path" ]; then
        if $DRY_RUN; then
          _dry_echo "ln -sf $BREW_ENGRAM $extra_path   # consolidate to brew canonical"
        fi
        # Auto-apply symlinks only with explicit opt-in (future: --fix-symlinks flag)
        # For now, suggest only — don't auto-apply to avoid surprising PATH changes
      fi
    done
  fi
fi

# ── MCP restart reminder ───────────────────────────────────────────────────
if $ENGRAM_CHANGED; then
  echo ""
  _yellow "  ⚠️  Restart Claude Code (cmd-Q + reopen) — MCP servers only spawn at startup."
  echo "  After restarting, verify with:"
  echo "    python3 scripts/check_mcp_servers.py"
  echo ""
fi

# ═══════════════════════════════════════════════════════════════════════════
# 3. CLAUDE CODE PLUGINS
# ═══════════════════════════════════════════════════════════════════════════
echo "── Claude Code plugins ───────────────────────────────────────────────"

PLUGINS_CACHE="$HOME/.claude/plugins/cache"

if [ ! -d "$PLUGINS_CACHE" ]; then
  echo "  SKIP: $PLUGINS_CACHE not found"
else
  for plugin_dir in "$PLUGINS_CACHE"/*/; do
    [ -d "$plugin_dir" ] || continue
    plugin_json="$plugin_dir/plugin.json"
    [ -f "$plugin_json" ] || continue

    PLUGIN_NAME=$(python3 -c "
import json,sys
d=json.load(open('$plugin_json'))
print(d.get('name','unknown'))
" 2>/dev/null || basename "$plugin_dir")

    PLUGIN_VERSION=$(python3 -c "
import json,sys
d=json.load(open('$plugin_json'))
print(d.get('version','unknown'))
" 2>/dev/null || echo "unknown")

    PLUGIN_REPO=$(python3 -c "
import json,sys
d=json.load(open('$plugin_json'))
print(d.get('repository',''))
" 2>/dev/null || echo "")

    PLUGINS_TOTAL=$((PLUGINS_TOTAL + 1))

    if [ -z "$PLUGIN_REPO" ] || ! command -v gh &>/dev/null; then
      echo "  $PLUGIN_NAME  v$PLUGIN_VERSION  (cannot check upstream — no repo or gh missing)"
      continue
    fi

    # Normalise: strip https://github.com/ prefix if present
    REPO_SLUG=$(echo "$PLUGIN_REPO" | sed 's|https://github.com/||' | sed 's|/$||')

    LATEST_TAG=$(gh release list --repo "$REPO_SLUG" --limit 1 2>/dev/null \
      | awk '{print $1}' | sed 's/^v//' || echo "")

    if [ -z "$LATEST_TAG" ]; then
      echo "  $PLUGIN_NAME  v$PLUGIN_VERSION  (could not fetch latest from $REPO_SLUG)"
      continue
    fi

    if [ "$PLUGIN_VERSION" = "$LATEST_TAG" ]; then
      echo "  $PLUGIN_NAME  v$PLUGIN_VERSION  [current]"
    else
      _yellow "  $PLUGIN_NAME  v$PLUGIN_VERSION  →  v$LATEST_TAG  [OUTDATED]"
      echo ""
      PLUGINS_NEED_UPGRADE=$((PLUGINS_NEED_UPGRADE + 1))
      if [ "$MODE" = "apply" ]; then
        echo "  MANUAL (plugins managed by Claude Code UI):"
        echo "    claude code /plugin update $PLUGIN_NAME"
        echo "    # or: open Claude Code → Settings → Plugins → Update"
      fi
    fi
  done
  echo ""
fi

# ═══════════════════════════════════════════════════════════════════════════
# 4. DOCKER IMAGES
# ═══════════════════════════════════════════════════════════════════════════
echo "── Docker images ─────────────────────────────────────────────────────"

if ! command -v docker &>/dev/null; then
  echo "  SKIP: docker not found in PATH"
else
  # Find all docker-compose files in repo root
  COMPOSE_FILES=$(find "$REPO_ROOT" -maxdepth 2 -name "docker-compose*.yml" -o -name "docker-compose*.yaml" 2>/dev/null || true)

  if [ -z "$COMPOSE_FILES" ]; then
    echo "  SKIP: no docker-compose*.yml files found"
  else
    # Extract unique image references (lines containing 'image:')
    IMAGES=$(grep -h 'image:' $COMPOSE_FILES 2>/dev/null \
      | sed 's/.*image:[[:space:]]*//' \
      | sed 's/[[:space:]].*//' \
      | sed 's/["'"'"']//g' \
      | sort -u || true)

    if [ -z "$IMAGES" ]; then
      echo "  No image: entries found in compose files"
    else
      while IFS= read -r image; do
        [ -z "$image" ] && continue
        DOCKER_CHECKED=$((DOCKER_CHECKED + 1))

        if [ "$MODE" = "apply" ]; then
          echo "  Pulling $image ..."
          if $DRY_RUN; then
            _dry_echo "docker pull $image"
          else
            # Capture old and new digest for comparison
            OLD_DIGEST=$(docker inspect --format='{{index .RepoDigests 0}}' "$image" 2>/dev/null || echo "not-pulled")
            docker pull "$image" 2>&1 | tail -3
            NEW_DIGEST=$(docker inspect --format='{{index .RepoDigests 0}}' "$image" 2>/dev/null || echo "unknown")
            if [ "$OLD_DIGEST" != "$NEW_DIGEST" ] && [ "$OLD_DIGEST" != "not-pulled" ]; then
              _yellow "  Digest changed: $image"
              echo "    Old: $OLD_DIGEST"
              echo "    New: $NEW_DIGEST"
              echo "    NOTE: Update your compose file digest pin manually (digest pinning is deliberate)."
              DOCKER_CHANGED=$((DOCKER_CHANGED + 1))
            else
              echo "  No digest change: $image"
            fi
          fi
        else
          # Audit mode: check if a newer manifest exists without pulling the full image
          REMOTE_DIGEST=$(docker manifest inspect "$image" 2>/dev/null \
            | python3 -c "
import json,sys
try:
  d = json.load(sys.stdin)
  # grab the config digest as a fingerprint
  print(d.get('config',{}).get('digest','unknown'))
except Exception:
  print('parse-error')
" 2>/dev/null || echo "unavailable")

          LOCAL_DIGEST=$(docker inspect --format='{{index .RepoDigests 0}}' "$image" 2>/dev/null || echo "not-pulled")

          echo "  $image"
          echo "    local : $LOCAL_DIGEST"
          echo "    remote: $REMOTE_DIGEST"

          # Heuristic: if remote digest is obtainable and differs from local, flag
          if [ "$REMOTE_DIGEST" != "unavailable" ] && [ "$REMOTE_DIGEST" != "parse-error" ]; then
            if ! echo "$LOCAL_DIGEST" | grep -qF "$REMOTE_DIGEST" 2>/dev/null; then
              _yellow "    WARNING: remote config digest differs — consider manual review"
              echo ""
              DOCKER_CHANGED=$((DOCKER_CHANGED + 1))
            fi
          fi
        fi
      done <<< "$IMAGES"
    fi
  fi
fi
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════
echo ""
_bold "=== Deps Update Summary ==="

if [ "$MODE" = "apply" ]; then
  if $DRY_RUN; then
    echo "  (DRY RUN — no changes made)"
  fi
fi

# Python line
if [ "$PY_TOTAL_OUTDATED" -eq 0 ]; then
  echo "  Python:   all packages current"
elif [ "$MODE" = "audit" ]; then
  echo "  Python:   $PY_TOTAL_OUTDATED outdated (run --apply to upgrade)"
else
  MAJOR_MSG=""
  if [ "$PY_SKIPPED_MAJOR" -gt 0 ]; then
    MAJOR_MSG=", $PY_SKIPPED_MAJOR skipped (major — use --apply --major)"
  fi
  echo "  Python:   $PY_UPGRADED upgraded (minor/patch)$MAJOR_MSG"
fi

# engram line
echo "  engram:   $ENGRAM_STATUS"

# plugins line
echo "  Plugins:  $PLUGINS_NEED_UPGRADE of $PLUGINS_TOTAL need upgrade (manual via Claude Code UI)"

# docker line
if [ "$MODE" = "audit" ]; then
  echo "  Docker:   $DOCKER_CHANGED image(s) may have newer digest (manual review)"
else
  echo "  Docker:   $DOCKER_CHANGED image(s) had digest change (manual review — compose not modified)"
fi

echo ""

# ── Post-apply: verify MCP server health ──────────────────────────────────
if [ "$MODE" = "apply" ] && ! $DRY_RUN && $ENGRAM_CHANGED; then
  echo ""
  echo "  Run after restarting Claude Code to verify MCP servers are healthy:"
  echo "    python3 scripts/check_mcp_servers.py"
  echo ""
fi

# ── Exit code ─────────────────────────────────────────────────────────────
if [ "$MODE" = "apply" ] && $INCONSISTENT; then
  echo "ERROR: --apply mode left one or more dependencies in an inconsistent state." >&2
  exit 1
fi

exit 0

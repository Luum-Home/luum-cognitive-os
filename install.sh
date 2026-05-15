#!/usr/bin/env bash
# install.sh — Install Cognitive OS into the current project
#
# UX1 + UX8 — ADR-093 collapsed the 3-tier profile system to 2 tiers:
#   default  — 10 curated core skills, ~29 standard hooks, 14 core rules (~8000 tokens/session)
#   --full   — every skill, hook, and rule (~142000 tokens/session)
#
# Legacy flags (--lean, --standard) are silently remapped to `default` with a
# stderr migration notice. See docs/02-Decisions/adrs/ADR-093-simplify-profiles.md.
set -euo pipefail

REPO_URL="${COGNITIVE_OS_REPO_URL:-https://github.com/luum-home/luum-cognitive-os.git}"
VERSION="${COGNITIVE_OS_VERSION:-main}"
TARGET_DIR=".cognitive-os"
FORCE="${COGNITIVE_OS_FORCE:-false}"
TEMP_DIR=$(mktemp -d)
SOURCE_DIR=""
FROM_FLAG=""
PROFILE=""             # Resolved profile: default | full
PROFILE_SOURCE=""      # flag | env | auto
SKIP_MANIFEST_CHECK="${COGNITIVE_OS_SKIP_MANIFEST_CHECK:-false}"
INSTALL_DEPS=false
HARNESS="${COGNITIVE_OS_HARNESS:-}"
SUPPORTED_HARNESSES="claude codex agents-md opencode vscode-copilot cursor qwen-code kimi-code gemini-cli warp amp-code jetbrains-junie qoder factory-droid cline continue-dev kilo-code zed-ai augment-code goose aider shell-ci"
# INSTALL_SCOPE controls which SCOPE-tagged files are copied.
# Values: project (SCOPE:project + SCOPE:both), both (backward-compatible
#         alias for project; not a separate installed surface), all
#         (everything, including SCOPE:os-only — for COS self-hosting).
INSTALL_SCOPE="${COS_INSTALL_SCOPE:-both}"

cleanup() { rm -rf "$TEMP_DIR"; }
trap cleanup EXIT

# ── Argument parsing ──────────────────────────────────────────────────
show_help() {
  cat <<'USAGE'
Usage: install.sh [OPTIONS]

Install Cognitive OS into the CURRENT DIRECTORY (your project).

IMPORTANT: Run this command FROM your project directory, not from the
Cognitive OS repo. The installer creates .cognitive-os/ and writes the
selected harness driver settings in the current working directory.

Profiles (ADR-093):
  (default)      10 curated core skills, ~29 standard hooks, 14 core rules
                   (~8000 tokens/session overhead). Works out of the box.
  --full         Every skill, hook, and rule available
                   (~142000 tokens/session). For mature projects and COS
                   contributors.

Legacy flags:
  --lean, --standard, --profile=lean|standard
                 Silently remapped to the default profile with a stderr
                 migration notice. Kept for backwards compatibility.

Options:
  --full                 Install everything (see above).
  --profile=NAME         Explicit profile: 'default' or 'full'. Legacy values
                         ('lean', 'standard') are accepted and remapped.
  --harness=NAME         Settings/instruction projection target
                         (default: claude). Supported:
                         claude, codex, agents-md, opencode, vscode-copilot,
                         cursor, qwen-code, kimi-code, gemini-cli, warp,
                         amp-code, jetbrains-junie, qoder, factory-droid,
                         cline, continue-dev, kilo-code, zed-ai, augment-code,
                         goose, aider, shell-ci.
  --from PATH            Use a local Cognitive OS repo instead of cloning.
  --force                Overwrite existing installation without prompting.
  --skip-manifest-check  Skip the post-install dependency report.
  --install-deps         After advisory manifest check, install portable,
                         non-auth-bound dependencies via cos-deps-install,
                         then run uv sync and register MCP servers.
  --scope=SCOPE          Filter installed files by SCOPE tag (default: both).
                           project  — consumer filtered install; files tagged
                                      SCOPE:project or SCOPE:both
                           both     — backward-compatible alias for project;
                                      not a separate installed surface (ADR-320)
                           all      — maintainer/self-hosting install; every file,
                                      including SCOPE:os-only
  --help, -h             Show this help message.

Environment variables:
  COGNITIVE_OS_VERSION              Git branch/tag to install (default: main)
  COGNITIVE_OS_REPO_URL             Git remote to clone when not using --from
                                    (default: https://github.com/luum-home/luum-cognitive-os.git)
  COGNITIVE_OS_FORCE                Set to "true" to overwrite without prompting
  COGNITIVE_OS_SKIP_MANIFEST_CHECK  Set to "true" to skip the dependency report
  COGNITIVE_OS_HARNESS              Settings/instruction projection target.
                                    See --harness for supported values.
  COS_PROFILE                       Override profile: 'default' or 'full'.
                                    Legacy values ('lean', 'standard') remapped.
  COS_INSTALL_SCOPE                 Override scope filter: project|both|all.

Examples:
  # Default install (Claude driver)
  cd /path/to/your-project
  /path/to/luum-agent-os/install.sh

  # Codex driver install
  /path/to/luum-agent-os/install.sh --harness=codex

  # Structural IDE projection (example: Cursor project rules + MCP placeholder)
  /path/to/luum-agent-os/install.sh --harness=cursor

  # Full install (everything)
  /path/to/luum-agent-os/install.sh --full

  # Install from local repo
  bash install.sh --from /path/to/luum-agent-os

  # Install from GitHub (remote)
  curl -sL https://raw.githubusercontent.com/.../install.sh | bash

  # Force overwrite existing installation
  ./install.sh --force
USAGE
  exit 0
}

# Normalize a raw profile value (from flag or env) to the ADR-093 canonical
# set. Legacy values are remapped with a stderr note. Unknown values fail.
normalize_profile() {
  local raw="$1"
  local context="$2"   # "flag" | "env"
  case "$raw" in
    default|full)
      PROFILE="$raw"
      ;;
    lean|standard|minimal)
      echo "Note: ADR-093 collapsed '$raw' into 'default'. Using 'default'." >&2
      echo "      Drop the flag next time: see docs/02-Decisions/adrs/ADR-093-simplify-profiles.md" >&2
      PROFILE="default"
      ;;
    *)
      echo "Error: unknown profile '$raw' (from $context)." >&2
      echo "       Valid profiles (ADR-093): default, full." >&2
      echo "       Legacy (remapped to default): lean, standard." >&2
      exit 1
      ;;
  esac
}

normalize_harness() {
  local raw="$1"
  local valid
  for valid in $SUPPORTED_HARNESSES; do
    if [ "$raw" = "$valid" ]; then
      HARNESS="$raw"
      return
    fi
  done
  echo "Error: unsupported harness '$raw'." >&2
  echo "       Valid harnesses: $SUPPORTED_HARNESSES." >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --from)
      if [[ -z "${2:-}" ]]; then
        echo "Error: --from requires a path argument." >&2
        exit 1
      fi
      FROM_FLAG="$2"
      shift 2
      ;;
    --force)
      FORCE="true"
      shift
      ;;
    --skip-manifest-check)
      SKIP_MANIFEST_CHECK="true"
      shift
      ;;
    --install-deps)
      INSTALL_DEPS=true
      shift
      ;;
    --scope=*)
      # --scope=project|both|all: filter installed files by SCOPE tag
      _scope_val="${1#--scope=}"
      case "$_scope_val" in
        project|both|all)
          INSTALL_SCOPE="$_scope_val"
          ;;
        *)
          echo "Error: --scope must be project, both, or all (got: '$_scope_val')." >&2
          exit 1
          ;;
      esac
      shift
      ;;
    --scope)
      if [[ -z "${2:-}" ]]; then
        echo "Error: --scope requires a value: project, both, or all." >&2
        exit 1
      fi
      case "$2" in
        project|both|all)
          INSTALL_SCOPE="$2"
          ;;
        *)
          echo "Error: --scope must be project, both, or all (got: '$2')." >&2
          exit 1
          ;;
      esac
      shift 2
      ;;
    --full)
      normalize_profile "full" "flag"
      PROFILE_SOURCE="flag"
      shift
      ;;
    --lean|--standard)
      # Legacy shorthand — remap via normalize_profile for the stderr note.
      normalize_profile "${1#--}" "flag"
      PROFILE_SOURCE="flag"
      shift
      ;;
    --profile=*)
      normalize_profile "${1#--profile=}" "flag"
      PROFILE_SOURCE="flag"
      shift
      ;;
    --profile)
      if [[ -z "${2:-}" ]]; then
        echo "Error: --profile requires a name argument." >&2
        exit 1
      fi
      normalize_profile "$2" "flag"
      PROFILE_SOURCE="flag"
      shift 2
      ;;
    --harness=*)
      normalize_harness "${1#--harness=}"
      shift
      ;;
    --harness)
      if [[ -z "${2:-}" ]]; then
        echo "Error: --harness requires a name argument." >&2
        exit 1
      fi
      normalize_harness "$2"
      shift 2
      ;;
    --help|-h)
      show_help
      ;;
    *)
      echo "Unknown option: $1" >&2
      echo "Valid: --full, --profile=NAME, --harness=NAME, --from PATH, --force, --skip-manifest-check, --install-deps, --scope=SCOPE, --help" >&2
      echo "Legacy (remapped): --lean, --standard" >&2
      echo "Run 'install.sh --help' for full usage." >&2
      exit 1
      ;;
  esac
done

# ENV override (only if no explicit flag was passed).
if [ -z "$PROFILE" ] && [ -n "${COS_PROFILE:-}" ]; then
  normalize_profile "$COS_PROFILE" "env"
  PROFILE_SOURCE="env"
fi

# Auto default: ADR-093 removed auto-detection. Default is always `default`.
if [ -z "$PROFILE" ]; then
  PROFILE="default"
  PROFILE_SOURCE="auto"
fi

# Default harness: Claude remains the default for backwards compatibility, but
# the installer now surfaces the active driver explicitly in the summary.
if [ -z "$HARNESS" ]; then
  HARNESS="claude"
else
  normalize_harness "$HARNESS"
fi

# ── Source detection ──────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -n "$FROM_FLAG" ]; then
  # Explicit --from flag
  if [ ! -d "$FROM_FLAG" ]; then
    echo "Error: --from path does not exist: $FROM_FLAG" >&2
    exit 1
  fi
  FROM_FLAG="$(cd "$FROM_FLAG" && pwd)"
  if [ -d "$FROM_FLAG/hooks" ] && [ -d "$FROM_FLAG/rules" ] && [ -d "$FROM_FLAG/skills" ]; then
    SOURCE_DIR="$FROM_FLAG"
  else
    echo "Error: --from path does not look like a Cognitive OS repo." >&2
    echo "       Expected hooks/, rules/, skills/ directories in: $FROM_FLAG" >&2
    exit 1
  fi
elif [ -d "$SCRIPT_DIR/hooks" ] && [ -d "$SCRIPT_DIR/rules" ] && [ -d "$SCRIPT_DIR/skills" ]; then
  # Running from within the repo itself
  SOURCE_DIR="$SCRIPT_DIR"
fi

echo "=== Cognitive OS Installer ==="
echo ""
echo "Profile: $PROFILE (source: $PROFILE_SOURCE)"
echo "Harness: $HARNESS"
echo ""

# Guard: prevent installing COS into its own repo
CWD="$(pwd)"
if [ -n "$SOURCE_DIR" ] && [ "$CWD" = "$SOURCE_DIR" ]; then
  echo "Error: You are running the installer FROM the Cognitive OS repo itself." >&2
  echo "" >&2
  echo "The installer installs into the CURRENT DIRECTORY. You should run it" >&2
  echo "from your PROJECT directory, not from the Cognitive OS source." >&2
  echo "" >&2
  echo "Example:" >&2
  echo "  cd /path/to/your-project" >&2
  echo "  $SOURCE_DIR/install.sh" >&2
  echo "" >&2
  exit 1
fi

if [ -n "$SOURCE_DIR" ]; then
  echo "Using local Cognitive OS from: $SOURCE_DIR"
  echo "Installing into: $CWD"
  echo ""
fi

# Check prerequisites (git only needed for remote install)
if [ -z "$SOURCE_DIR" ] && ! command -v git >/dev/null 2>&1; then
  echo "Error: git is required but not installed." >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "Warning: jq is not installed. Settings merge requires jq."
  echo "         Install jq for safest merge with existing harness settings."
  HAS_JQ=false
else
  HAS_JQ=true
fi

# ── Pre-install conflict detection ──────────────────────────────────
if [ -d ".claude" ]; then
  echo "Detected existing .claude/ configuration:"
  existing_hooks=0
  existing_rules=0
  existing_commands=0
  has_claude_md=false

  if [ -f ".claude/settings.json" ]; then
    existing_hooks=$(jq '[.hooks // {} | to_entries[] | .value[] | .hooks[]? ] | length' .claude/settings.json 2>/dev/null || echo "?")
    echo "  - settings.json: $existing_hooks hooks registered"
  fi

  if [ -d ".claude/rules" ]; then
    existing_rules=$(find .claude/rules -maxdepth 2 -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
    echo "  - rules/: $existing_rules rule files"
  fi

  if [ -d ".claude/commands" ]; then
    existing_commands=$(find .claude/commands -maxdepth 1 -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
    echo "  - commands/: $existing_commands command files"
  fi

  if [ -f ".claude/CLAUDE.md" ]; then
    has_claude_md=true
    echo "  - CLAUDE.md: present"
  fi

  echo ""
  echo "Cognitive OS will MERGE settings and namespace rules under cos/"
  echo "Your existing configuration will be preserved."
  echo ""
fi

# Check if already installed
if [ -d "$TARGET_DIR" ]; then
  if [ "$FORCE" = "true" ]; then
    echo "Overwriting existing installation..."
    rm -rf "$TARGET_DIR"
  elif [ -t 0 ]; then
    # Interactive terminal — ask for confirmation
    echo "Cognitive OS is already installed in $TARGET_DIR"
    read -rp "Overwrite? (y/N): " confirm </dev/tty
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
      echo "Aborted."
      exit 0
    fi
    rm -rf "$TARGET_DIR"
  else
    # Non-interactive (piped) — abort safely
    echo "Cognitive OS is already installed in $TARGET_DIR"
    echo "To overwrite, run: COGNITIVE_OS_FORCE=true bash install.sh"
    exit 0
  fi
fi

# ── Prepare source (local copy or remote clone) ──────────────────────
prepare_source() {
  if [ -n "$SOURCE_DIR" ]; then
    # Local: copy only the directories cos-init.sh needs, skip .venv/reference/node_modules
    echo "Copying from local source..."
    rm -rf "$TEMP_DIR"
    mkdir -p "$TEMP_DIR"
    # Use rsync if available (excludes broken symlinks in .venv, reference/, etc.)
    if command -v rsync >/dev/null 2>&1; then
      set +e
      rsync -a \
        --exclude='.venv' \
        --exclude='node_modules' \
        --exclude='reference' \
        --exclude='.git' \
        --exclude='.cognitive-os/metrics' \
        --exclude='.cognitive-os/runtime' \
        --exclude='__pycache__' \
        "$SOURCE_DIR/" "$TEMP_DIR/"
      rsync_status=$?
      set -e
      if [ "$rsync_status" -ne 0 ]; then
        # Local source installs can race with live agent/test artifacts being
        # created or removed. rsync returns 23/24 for partial transfer or
        # vanished files; continue and let required-file checks below catch
        # any genuinely missing installer inputs.
        if [ "$rsync_status" -eq 23 ] || [ "$rsync_status" -eq 24 ]; then
          echo "WARNING: local source changed during copy; continuing with partial rsync." >&2
        else
          exit "$rsync_status"
        fi
      fi
    else
      # Fallback: cp with error suppression for broken symlinks
      cp -r "$SOURCE_DIR" "$TEMP_DIR.bak" 2>/dev/null || true
      mv "$TEMP_DIR.bak" "$TEMP_DIR"
      rm -rf "$TEMP_DIR/.cognitive-os/metrics" "$TEMP_DIR/.cognitive-os/runtime" 2>/dev/null || true
    fi
  else
    # Remote: git clone
    echo "Downloading Cognitive OS ($VERSION)..."
    git clone --depth 1 --branch "$VERSION" "$REPO_URL" "$TEMP_DIR" 2>/dev/null || \
      git clone --depth 1 "$REPO_URL" "$TEMP_DIR"
  fi
}

prepare_source

# ── Delegate to cos-init.sh ──────────────────────────────────────────
# cos-init.sh handles: rules, hooks, skills, templates, settings driver,
# cognitive-os.yaml, and registry registration.
# It uses generate-project-settings.sh for correct hook paths and
# installs to namespaced cos/ subdirectories.
COS_INIT="$TEMP_DIR/scripts/cos-init.sh"

if [ ! -f "$COS_INIT" ]; then
  echo "Error: cos-init.sh not found in source." >&2
  exit 1
fi

echo "Running cos-init.sh..."
# Map canonical profile → cos-init.sh flag. ADR-093: default + full only.
COS_INIT_FLAG="--$PROFILE"

# COS_SOURCE_DIR tells cos-init.sh where to copy files from (temp dir).
# COS_ORIGINAL_SOURCE tells it the real source repo path for the registry,
# so auto-update-projects.sh can find projects installed from this repo.
# COS_INSTALL_SCOPE propagates the --scope flag so cos-init.sh can filter
# SCOPE-tagged files during copy.
COS_SOURCE_DIR="$TEMP_DIR" COS_ORIGINAL_SOURCE="${SOURCE_DIR:-}" COS_INSTALL_SCOPE="$INSTALL_SCOPE" COGNITIVE_OS_HARNESS="$HARNESS" bash "$COS_INIT" "$COS_INIT_FLAG"

# ── Install Claude project instructions only for Claude harness ────────
if [ "$HARNESS" = "claude" ]; then
  if [ ! -f ".claude/CLAUDE.md" ]; then
    TEMPLATE="$TEMP_DIR/templates/CLAUDE.md.template"
    if [ -f "$TEMPLATE" ]; then
      mkdir -p ".claude"
      cp "$TEMPLATE" ".claude/CLAUDE.md"
      echo "Created .claude/CLAUDE.md from template."
    fi
  else
    echo "Existing .claude/CLAUDE.md preserved (not overwritten)."
  fi
fi

# ── Post-install summary (UX1) ────────────────────────────────────────
# Count what actually landed under the canonical skill surface and, for Claude,
# the driver projection surface.
skills_available=0
if [ -d ".cognitive-os/skills/cos" ]; then
  for d in .cognitive-os/skills/cos/*/; do
    [ -d "$d" ] && skills_available=$((skills_available + 1))
  done
fi
skills_exposed=0
if [ -d ".claude/skills" ]; then
  for d in .claude/skills/*/; do
    [ -d "$d" ] && skills_exposed=$((skills_exposed + 1))
  done
fi

echo ""
echo "Cognitive OS installed successfully."
echo ""
echo "Profile:        $PROFILE"
echo "Harness:        $HARNESS"
case "$HARNESS" in
  claude)
    settings_driver=".claude/settings.json"
    skills_line="Skills exposed: $skills_exposed (under .claude/skills/ Claude projection)"
    ;;
  codex)
    settings_driver=".codex/hooks.json"
    skills_line="Skills available: $skills_available (under .cognitive-os/skills/cos/ canonical surface)"
    ;;
  *)
    if [ -f ".cognitive-os/install-meta.json" ]; then
      settings_driver="$(python3 - <<'PY'
import json
from pathlib import Path

meta = json.loads(Path(".cognitive-os/install-meta.json").read_text())
print(meta.get("settings_driver") or meta.get("settings_path") or "see .cognitive-os/install-meta.json")
PY
)"
    else
      settings_driver="see .cognitive-os/install-meta.json"
    fi
    skills_line="Skills available: $skills_available (under .cognitive-os/skills/cos/ canonical surface; this harness receives references unless a native skill projection is signed)"
    ;;
esac
echo "Settings:       $settings_driver"
echo "$skills_line"
echo ""
echo "Project structure:"
echo "  .cognitive-os/hooks/cos/     - COS hooks (namespaced)"
echo "  .cognitive-os/skills/cos/    - COS skills (kernel path, namespaced)"
echo "  .cognitive-os/templates/cos/ - COS templates (namespaced)"
echo "  $settings_driver        - Active harness settings driver"
if [ "$HARNESS" = "claude" ]; then
  echo "  .claude/skills/              - Claude skill projection (ADR-001)"
  echo "  .claude/rules/cos/           - Claude-compatible rule projection"
elif [ "$HARNESS" != "codex" ]; then
  echo "  Note: $HARNESS is a structural or harness-specific projection unless"
  echo "        manifests/harness-projection.yaml records a stronger proof_level."
fi
echo ""

if [ "$HARNESS" = "claude" ] && [ "$skills_exposed" -eq 0 ]; then
  echo "WARNING: 0 skills are exposed to the harness under .claude/skills/." >&2
  echo "         This is likely a bug — run 'bash hooks/self-install.sh' or" >&2
  echo "         re-run this installer with --force to repair." >&2
  echo "" >&2
fi

echo "Next checks:"
echo "  COGNITIVE_OS_PROJECT_DIR=\"\$PWD\" bash <cos-source>/scripts/cos-status.sh"
if [ "$HARNESS" = "claude" ]; then
  echo "  claude  # then run /cognitive-os-init when you want project-specific generation"
elif [ "$HARNESS" = "codex" ]; then
  echo "  Open Codex in this project; hooks are projected in .codex/hooks.json."
else
  echo "  Open $HARNESS in this project; projection is written to $settings_driver."
  echo "  Check manifests/harness-projection.yaml before claiming runtime enforcement."
fi
echo ""
echo "Existing harness configuration is preserved and merged where supported."
echo ""

# ── Manifest check (advisory) ─────────────────────────────────────────
# Reports declared dependencies (Python deps, CLIs, MCP servers) against
# what is actually installed on the user's system. NEVER fails the install
# — only the user sees "MISSING" hints with install commands.
#
# Skipped if:
#   - --skip-manifest-check / COGNITIVE_OS_SKIP_MANIFEST_CHECK=true
#   - python3 not on PATH (the loader needs it)
#   - source repo is too old to ship the manifest
MANIFEST_CHECK="$TEMP_DIR/scripts/manifest-check.sh"
if [ "$SKIP_MANIFEST_CHECK" = "true" ]; then
  echo "Manifest check skipped (--skip-manifest-check)."
  echo ""
elif ! command -v python3 >/dev/null 2>&1; then
  echo "Manifest check skipped (python3 not found)."
  echo ""
elif [ ! -f "$MANIFEST_CHECK" ]; then
  echo "Manifest check skipped (source repo predates manifests/)."
  echo ""
else
  echo "Checking declared dependencies for profile '$PROFILE'..."
  echo ""
  # Exit 0 = all required present; 1 = some required missing (still ok to use
  # COS, just with degraded features); 2 = manifest broken (a bug, surface it).
  set +e
  bash "$MANIFEST_CHECK" --profile "$PROFILE"
  manifest_exit=$?
  set -e
  if [ "$manifest_exit" = "2" ]; then
    echo ""
    echo "WARNING: dependency manifest failed validation (exit 2). This is a" >&2
    echo "         Cognitive OS bug — please report it. Install itself succeeded." >&2
    echo ""
  fi
fi

# ── Dependency installation (--install-deps) ───────────────────────────
# Only runs when --install-deps flag is passed. Without it the advisory-only
# behavior from PR #6 is fully preserved.
if [ "$INSTALL_DEPS" = "true" ]; then
  echo "Installing dependencies (--install-deps)..."
  echo ""

  # Host/tool dependencies via the manifest-driven installer.
  COS_DEPS_INSTALL="${TEMP_DIR}/scripts/cos-deps-install.sh"
  if [ -x "$COS_DEPS_INSTALL" ]; then
    deps_profile="$PROFILE"
    echo "Running cos-deps-install.sh --profile ${deps_profile} --apply..."
    if bash "$COS_DEPS_INSTALL" --profile "$deps_profile" --apply; then
      echo "  cos-deps-install: OK"
    else
      echo "  WARN: cos-deps-install reported failures — continuing with degraded tools" >&2
    fi
  else
    echo "  WARN: cos-deps-install.sh not found — skipping host dependency install" >&2
  fi

  # Python deps via uv sync
  if command -v uv >/dev/null 2>&1; then
    echo "Running uv sync..."
    if ( uv sync ); then
      echo "  uv sync: OK"
    else
      echo "  WARN: uv sync failed — Python dependencies may be incomplete" >&2
    fi
  else
    echo "  WARN: uv not installed — skipping Python dependency sync" >&2
  fi

  # MCP servers via register-mcps.sh
  REGISTER_MCPS="${TEMP_DIR}/scripts/register-mcps.sh"
  if [ ! -f "$REGISTER_MCPS" ]; then
    # When running from the repo itself (SOURCE_DIR set), try the real path
    if [ -n "${SOURCE_DIR:-}" ] && [ -f "${SOURCE_DIR}/scripts/register-mcps.sh" ]; then
      REGISTER_MCPS="${SOURCE_DIR}/scripts/register-mcps.sh"
    fi
  fi
  if [ -f "$REGISTER_MCPS" ] && command -v python3 >/dev/null 2>&1; then
    echo "Registering MCP servers for profile '${PROFILE}'..."
    if bash "$REGISTER_MCPS" --profile "$PROFILE"; then
      echo "  MCP registration: OK"
    else
      echo "  WARN: MCP registration encountered errors — see output above" >&2
    fi
  else
    echo "  WARN: register-mcps.sh not found or python3 unavailable — skipping MCP registration" >&2
  fi

  echo ""
fi

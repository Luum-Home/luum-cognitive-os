#!/usr/bin/env bash
# SCOPE: os-only
# =============================================================================
# register-mcps.sh — Register MCP servers declared in manifests/dependencies.yaml
# =============================================================================
# Idempotent. Safe to run multiple times. Uses SHA-256 caching of the manifest
# section to skip registration when nothing changed.
#
# Usage:
#   bash scripts/register-mcps.sh --profile <lean|standard|default|full> \
#                                  [--dry-run] [--cache-dir <dir>]
#
# Registration strategy (in priority order):
#   1. If `claude` CLI is on PATH: `claude mcp add <name> <command> [args...]`
#   2. If `claude` is absent: merge mcpServers into ~/.claude/settings.json
#      via Python (atomic tempfile+mv).
#   3. If neither claude nor jq nor settings.json available: WARN + exit 0.
#
# Flags:
#   --profile   Profile name to look up MCP recommendations (required)
#   --dry-run   Print actions without writing anything
#   --cache-dir Override the cache directory (default: .cognitive-os/state)
#   --help      Show this message
#
# Exit codes:
#   0  success (or already up-to-date)
#   1  fatal error (bad arguments, manifest broken)
#
# bash 3.2 compatible — no mapfile, no associative arrays.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
PROFILE=""
DRY_RUN=false
CACHE_DIR="${PROJECT_ROOT}/.cognitive-os/state"

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)
      if [[ -z "${2:-}" ]]; then
        echo "Error: --profile requires a value." >&2
        exit 1
      fi
      PROFILE="$2"
      shift 2
      ;;
    --profile=*)
      PROFILE="${1#--profile=}"
      shift
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --cache-dir)
      if [[ -z "${2:-}" ]]; then
        echo "Error: --cache-dir requires a path." >&2
        exit 1
      fi
      CACHE_DIR="$2"
      shift 2
      ;;
    --cache-dir=*)
      CACHE_DIR="${1#--cache-dir=}"
      shift
      ;;
    --help|-h)
      cat <<'EOF'
register-mcps.sh — Register MCP servers from the dependency manifest

USAGE
  bash scripts/register-mcps.sh --profile <profile> [--dry-run] [--cache-dir <dir>]

FLAGS
  --profile NAME    Profile to use: lean, standard, default, full (required)
  --dry-run         Show actions without writing anything
  --cache-dir DIR   Override state cache directory (default: .cognitive-os/state)
  --help            Show this help

REGISTRATION STRATEGY
  1. If `claude` CLI is on PATH: uses `claude mcp add`
  2. If `claude` is absent: merges mcpServers into ~/.claude/settings.json via Python
  3. If neither is available: WARN and exit 0

EXIT CODES
  0  Success (or already up-to-date, or gracefully degraded)
  1  Fatal error (bad args, broken manifest)
EOF
      exit 0
      ;;
    *)
      echo "Unknown argument: $1. Use --help for usage." >&2
      exit 1
      ;;
  esac
done

if [[ -z "$PROFILE" ]]; then
  echo "Error: --profile is required." >&2
  echo "Usage: bash scripts/register-mcps.sh --profile <profile>" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Logging helpers (same pattern as cos-update.sh)
# ---------------------------------------------------------------------------
note() { printf '%s\n' "$*" >&2; }
warn() { printf 'WARN: %s\n' "$*" >&2; }
err()  { printf 'ERROR: %s\n' "$*" >&2; }

# ---------------------------------------------------------------------------
# Cross-platform SHA-256 helper (bash 3.2 compat; macOS + Linux)
# ---------------------------------------------------------------------------
sha256_of_string() {
  local str="$1"
  if command -v shasum >/dev/null 2>&1; then
    printf '%s' "$str" | shasum -a 256 | awk '{print $1}'
  elif command -v sha256sum >/dev/null 2>&1; then
    printf '%s' "$str" | sha256sum | awk '{print $1}'
  else
    # Fallback: length-based fingerprint (not cryptographic, but sufficient
    # for detecting any content change)
    printf '%s' "$str" | wc -c | tr -d ' '
  fi
}

# ---------------------------------------------------------------------------
# Resolve the best available Python interpreter that has pyyaml available.
# Preference order:
#   1. The project's own .venv (most likely to have deps)
#   2. Whatever `python3` resolves on PATH
# ---------------------------------------------------------------------------
PYTHON_BIN=""

_find_python() {
  # Try the project venv first
  local venv_python="${PROJECT_ROOT}/.venv/bin/python3"
  if [[ -x "$venv_python" ]]; then
    if "$venv_python" -c "import yaml" >/dev/null 2>&1; then
      echo "$venv_python"
      return 0
    fi
  fi
  # Fall back to PATH python3
  if command -v python3 >/dev/null 2>&1; then
    if python3 -c "import yaml" >/dev/null 2>&1; then
      echo "python3"
      return 0
    fi
  fi
  echo ""
}

PYTHON_BIN="$(_find_python)"

if [[ -z "$PYTHON_BIN" ]]; then
  warn "No Python interpreter with pyyaml found. MCP registration skipped."
  warn "  Install pyyaml (pip install pyyaml) or use 'uv sync' to set up the project venv."
  exit 0
fi

# ---------------------------------------------------------------------------
# Fetch MCP list for profile via Python
# ---------------------------------------------------------------------------
get_mcps_json() {
  # Returns a JSON array of objects: [{name, command, args, env, register_to}]
  # Uses COS_MANIFEST_PATH env override so tests can inject a scratch manifest.
  "$PYTHON_BIN" - <<PYEOF
import sys, json, os
sys.path.insert(0, '${PROJECT_ROOT}/lib')
# Honor COS_MANIFEST_PATH env override (set by tests)
manifest_path = os.environ.get('COS_MANIFEST_PATH')
try:
    from manifest_loader import get_mcps_for_profile, ManifestError
    mcps = get_mcps_for_profile('${PROFILE}', path=manifest_path if manifest_path else None)
    print(json.dumps(mcps))
except ManifestError as e:
    print(f'MANIFEST_ERROR: {e}', file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
    sys.exit(1)
PYEOF
}

# ---------------------------------------------------------------------------
# SHA cache helpers
# ---------------------------------------------------------------------------
MCP_SHA_FILE="${CACHE_DIR}/mcps.sha"

current_manifest_section_sha() {
  # SHA of the manifest file itself (whole file is fine — cheap and correct)
  local manifest_path
  manifest_path="${COS_MANIFEST_PATH:-${PROJECT_ROOT}/manifests/dependencies.yaml}"
  if [[ ! -f "$manifest_path" ]]; then
    echo "MISSING"
    return
  fi
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$manifest_path" | awk '{print $1}'
  elif command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$manifest_path" | awk '{print $1}'
  else
    wc -c < "$manifest_path" | tr -d ' '
  fi
}

sha_changed() {
  local current
  current="$(current_manifest_section_sha)"
  local previous=""
  if [[ -f "$MCP_SHA_FILE" ]]; then
    previous="$(cat "$MCP_SHA_FILE" 2>/dev/null || echo "")"
  fi
  if [[ "$current" == "$previous" ]]; then
    return 1   # NOT changed
  fi
  return 0   # changed (or first run)
}

save_sha() {
  local current
  current="$(current_manifest_section_sha)"
  mkdir -p "$CACHE_DIR"
  printf '%s\n' "$current" > "$MCP_SHA_FILE"
}

# ---------------------------------------------------------------------------
# Check if MCP is already registered via `claude mcp list`
# ---------------------------------------------------------------------------
mcp_already_registered_via_claude() {
  local name="$1"
  # `claude mcp list` outputs one name per line (or JSON — accept both)
  if claude mcp list 2>/dev/null | grep -qF "$name"; then
    return 0
  fi
  return 1
}

# ---------------------------------------------------------------------------
# Register one MCP via `claude mcp add`
# ---------------------------------------------------------------------------
register_via_claude_cli() {
  local name="$1"
  local command="$2"
  shift 2
  # Remaining args are the MCP command args
  note "  registering '${name}' via claude mcp add"
  if [[ "$DRY_RUN" == "true" ]]; then
    note "  [dry-run] would run: claude mcp add ${name} ${command} $*"
    return 0
  fi
  claude mcp add "$name" "$command" "$@"
}

# ---------------------------------------------------------------------------
# Fallback: merge mcpServers into ~/.claude/settings.json via Python
# ---------------------------------------------------------------------------
register_via_settings_json() {
  local name="$1"
  local command="$2"
  local args_json="$3"   # JSON array string, e.g. '["-y","@anthropic/engram"]'
  local settings_file="${HOME}/.claude/settings.json"

  note "  registering '${name}' via settings.json merge (claude CLI not found)"

  if [[ "$DRY_RUN" == "true" ]]; then
    note "  [dry-run] would merge mcpServers.${name} into ${settings_file}"
    return 0
  fi

  "$PYTHON_BIN" - <<PYEOF
import json, os, sys, tempfile
from pathlib import Path

settings_path = Path(os.path.expanduser('${settings_file}'))
settings_path.parent.mkdir(parents=True, exist_ok=True)

# Read existing settings (or start fresh)
if settings_path.exists():
    try:
        existing = json.loads(settings_path.read_text())
    except json.JSONDecodeError:
        existing = {}
else:
    existing = {}

if not isinstance(existing, dict):
    existing = {}

# Deep-merge mcpServers
mcp_servers = existing.setdefault('mcpServers', {})
if not isinstance(mcp_servers, dict):
    mcp_servers = {}
    existing['mcpServers'] = mcp_servers

args = json.loads('${args_json}')
mcp_servers['${name}'] = {
    'command': '${command}',
    'args': args,
    'env': {},
}

# Atomic write via tempfile + rename
tmp = settings_path.parent / (settings_path.name + '.tmp')
tmp.write_text(json.dumps(existing, indent=2) + '\n')
tmp.replace(settings_path)
print(f"  merged mcpServers.${name} into {settings_path}")
PYEOF
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
note "register-mcps: profile='${PROFILE}' dry_run=${DRY_RUN}"

# The SHA cache records whether the manifest file has changed since the last
# run.  It is a PERFORMANCE HINT, NOT a correctness gate.
#
# Using it as an early-exit caused a declared-vs-actual drift bug:
#   1. Manifest declares A, B, C. First run installs all. SHA saved.
#   2. User removes B (claude mcp remove B, or edits settings.json directly).
#   3. git pull with no manifest change → SHA unchanged → early-exit fires →
#      B is never reinstalled.
#
# Correct behaviour: always run the per-MCP loop so each item is checked
# against the actual registered state.  The per-MCP check inside the loop
# (via `claude mcp list`) is what provides idempotence — not the SHA cache.
# The SHA is still written at the end so future changes are detectable for
# telemetry and logging purposes.

note "reading MCP list for profile '${PROFILE}'..."

# Fetch MCPs as JSON
mcp_json=""
if ! mcp_json="$(get_mcps_json 2>&1)"; then
  err "Failed to load manifest: ${mcp_json}"
  exit 1
fi

# Count MCPs (Python one-liner to avoid bash JSON parsing)
mcp_count="$("$PYTHON_BIN" -c "import json,sys; data=json.loads(sys.stdin.read()); print(len(data))" <<< "$mcp_json" 2>/dev/null || echo "0")"

if [[ "$mcp_count" == "0" ]]; then
  note "No MCPs declared for profile '${PROFILE}'; nothing to register"
  if [[ "$DRY_RUN" != "true" ]]; then
    save_sha
  fi
  exit 0
fi

note "Found ${mcp_count} MCP(s) to register for profile '${PROFILE}'"

# Determine registration strategy
has_claude=false
if command -v claude >/dev/null 2>&1; then
  has_claude=true
fi

if [[ "$has_claude" == "false" ]]; then
  # Check if we have any fallback path
  settings_file="${HOME}/.claude/settings.json"
  settings_dir="${HOME}/.claude"
  if [[ ! -d "$settings_dir" ]] && [[ "$DRY_RUN" != "true" ]]; then
    warn "claude CLI not found and ~/.claude/ does not exist — will create settings.json on first registration"
  fi
fi

# Process each MCP
"$PYTHON_BIN" - <<PYEOF
import json, subprocess, sys, os

mcps = json.loads('''${mcp_json}''')

has_claude = '${has_claude}' == 'true'
dry_run = '${DRY_RUN}' == 'true'

for mcp in mcps:
    name = mcp['name']
    command = mcp['command']
    args = mcp.get('args', [])
    args_json = json.dumps(args)

    if has_claude:
        # Check if already registered
        try:
            result = subprocess.run(
                ['claude', 'mcp', 'list'],
                capture_output=True, text=True, timeout=10
            )
            if name in result.stdout:
                print(f"  '{name}' already registered (claude mcp list); skipping", file=sys.stderr)
                continue
        except Exception:
            pass  # If we can't check, proceed with registration

        print(f"  registering '{name}' via claude mcp add", file=sys.stderr)
        if dry_run:
            print(f"  [dry-run] would run: claude mcp add {name} {command} {' '.join(args)}", file=sys.stderr)
        else:
            cmd = ['claude', 'mcp', 'add', name, command] + args
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode != 0:
                print(f"WARN: claude mcp add failed for '{name}': {r.stderr.strip()}", file=sys.stderr)
            else:
                print(f"  '{name}' registered successfully", file=sys.stderr)
    else:
        # Fallback: write to settings.json
        import tempfile
        from pathlib import Path

        settings_path = Path(os.path.expanduser('~/.claude/settings.json'))

        if dry_run:
            print(f"  [dry-run] would merge mcpServers.{name} into {settings_path}", file=sys.stderr)
            continue

        settings_path.parent.mkdir(parents=True, exist_ok=True)

        if settings_path.exists():
            try:
                existing = json.loads(settings_path.read_text())
            except json.JSONDecodeError:
                existing = {}
        else:
            existing = {}

        if not isinstance(existing, dict):
            existing = {}

        mcp_servers = existing.setdefault('mcpServers', {})
        if not isinstance(mcp_servers, dict):
            mcp_servers = {}
            existing['mcpServers'] = mcp_servers

        if name in mcp_servers:
            print(f"  '{name}' already in settings.json; skipping", file=sys.stderr)
            continue

        print(f"  registering '{name}' via settings.json (no claude CLI)", file=sys.stderr)
        mcp_servers[name] = {
            'command': command,
            'args': args,
            'env': {},
        }
        tmp = settings_path.parent / (settings_path.name + '.tmp')
        tmp.write_text(json.dumps(existing, indent=2) + '\n')
        tmp.replace(settings_path)
        print(f"  '{name}' merged into {settings_path}", file=sys.stderr)

print("register-mcps: done", file=sys.stderr)
PYEOF

# Save SHA cache (skip if dry-run)
if [[ "$DRY_RUN" != "true" ]]; then
  save_sha
  note "mcps.sha cache updated"
fi

exit 0

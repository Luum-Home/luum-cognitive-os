#!/usr/bin/env bash
# SCOPE: os-only
# lib-symlink-divergence-detector.sh — PreToolUse Bash hook.
#
# Why: The symlink-mutation-guard.sh only catches `rm + ln -s` patterns.
# This hook catches the case that actually caused silent drift (ADR-267):
# `rm + cat > lib/X.py` that replaces a symlink with a real file, followed
# by content divergence over time.
#
# For each file staged to lib/ (git add), this hook checks whether a same-named
# counterpart exists in packages/*/lib/. If one does AND neither file is a
# symlink to the other AND content differs → BLOCK the commit.
#
# Trigger: PreToolUse — command contains `git commit`
# Exit: 0 = allow, 1 = block
#
# Bypass: COS_ALLOW_LIB_DIVERGENCE=1 (logged to audit trail)
# Full report: python3 scripts/cos_lib_symlink_invariant_audit.py
#
# Dependencies: git, python3 (stdlib only), no external binaries per file.
# Performance target: <500ms for ≤20 staged files.

set -uo pipefail

# Killswitch
if [ "${DISABLE_HOOK_LIB_SYMLINK_DIVERGENCE:-false}" = "true" ]; then
  exit 0
fi

# Read stdin JSON tool-call payload
INPUT=$(cat)
[ -z "$INPUT" ] && exit 0

# Only intercept Bash tool calls
TOOL_NAME=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    d = json.loads(sys.stdin.read() or '{}')
    print(d.get('tool_name', ''))
except Exception:
    print('')
" 2>/dev/null)
[ "$TOOL_NAME" = "Bash" ] || exit 0

COMMAND=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    d = json.loads(sys.stdin.read() or '{}')
    print(d.get('tool_input', {}).get('command', ''))
except Exception:
    print('')
" 2>/dev/null)
[ -n "$COMMAND" ] || exit 0

# Only trigger on git commit commands
echo "$COMMAND" | grep -qE '\bgit\b.*\bcommit\b' || exit 0

# Resolve project root
PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}}"
LOG_DIR="${PROJECT_DIR}/.cognitive-os/logs"
LOG_FILE="${LOG_DIR}/lib-symlink-divergence-detector.jsonl"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Ensure log dir exists (best-effort, don't fail hook if it doesn't)
mkdir -p "$LOG_DIR" 2>/dev/null || true

log_event() {
  local level="$1"
  local message="$2"
  local extras="${3:-}"
  printf '{"ts":"%s","hook":"lib-symlink-divergence-detector","level":"%s","message":"%s"%s}\n' \
    "$TIMESTAMP" "$level" "$message" "$extras" >> "$LOG_FILE" 2>/dev/null || true
}

# Bypass with env var (logged)
if [ "${COS_ALLOW_LIB_DIVERGENCE:-0}" = "1" ]; then
  log_event "BYPASS" "COS_ALLOW_LIB_DIVERGENCE=1 — skipping divergence check"
  exit 0
fi

# Get staged files from the index (only files in lib/)
STAGED_LIB_FILES=$(git -C "$PROJECT_DIR" diff --cached --name-only --diff-filter=ACM 2>/dev/null \
  | grep -E '^lib/[^/]+\.py$' || true)

[ -n "$STAGED_LIB_FILES" ] || exit 0

# Use Python for the actual content + symlink checks (single process, no per-file spawning)
BLOCK_RESULT=$(python3 - "$PROJECT_DIR" "$STAGED_LIB_FILES" <<'PYEOF'
import os
import sys
import glob

repo = sys.argv[1]
staged_raw = sys.argv[2]
staged_files = [f.strip() for f in staged_raw.splitlines() if f.strip()]

packages_dir = os.path.join(repo, "packages")
blocked = []   # (lib_rel, pkg_rel, reason)

for lib_rel in staged_files:
    lib_abs = os.path.join(repo, lib_rel)
    basename = os.path.basename(lib_rel)

    # Find counterparts: packages/*/lib/<basename> at any depth (up to 3)
    pattern_1 = os.path.join(packages_dir, "*", "lib", basename)
    pattern_2 = os.path.join(packages_dir, "*", "lib", "*", basename)
    pattern_3 = os.path.join(packages_dir, "*", "lib", "*", "*", basename)
    counterparts = []
    for pat in (pattern_1, pattern_2, pattern_3):
        counterparts.extend(glob.glob(pat))

    if not counterparts:
        continue

    # Check symlink status and content
    lib_is_link = os.path.islink(lib_abs)
    try:
        lib_real = os.path.realpath(lib_abs)
    except OSError:
        lib_real = lib_abs

    for pkg_abs in counterparts:
        pkg_rel = os.path.relpath(pkg_abs, repo)
        pkg_is_link = os.path.islink(pkg_abs)
        try:
            pkg_real = os.path.realpath(pkg_abs)
        except OSError:
            pkg_real = pkg_abs

        # If one is a symlink to the other -> invariant satisfied, skip
        if lib_is_link and lib_real == os.path.realpath(pkg_abs):
            continue
        if pkg_is_link and pkg_real == os.path.realpath(lib_abs):
            continue

        # Neither is symlink to the other - read and compare content
        try:
            with open(lib_abs, "rb") as f:
                lib_data = f.read()
        except OSError:
            continue
        try:
            with open(pkg_abs, "rb") as f:
                pkg_data = f.read()
        except OSError:
            continue

        if lib_data != pkg_data:
            blocked.append((lib_rel, pkg_rel, "content_drift"))

for lib_rel, pkg_rel, reason in blocked:
    print(f"BLOCK|{lib_rel}|{pkg_rel}|{reason}")
PYEOF
)

if [ -z "$BLOCK_RESULT" ]; then
  log_event "PASS" "no divergence detected in staged lib/ files"
  exit 0
fi

# One or more divergences found -- block the commit
echo ""
echo "========================================================================"
echo "  BLOCKED: lib-symlink-divergence-detector (ADR-267)"
echo "========================================================================"
echo ""
echo "Staged lib/ file(s) have diverged from their packages/*/lib/ counterparts"
echo "without a symlink relationship. The project invariant requires these to be"
echo "symlinks, NOT independent copies."
echo ""
echo "Divergent pairs:"
while IFS='|' read -r prefix lib_rel pkg_rel reason; do
  if [ "$prefix" = "BLOCK" ]; then
    echo "  ERROR  ${lib_rel}  vs  ${pkg_rel}  (${reason})"
    log_event "BLOCK" "content_drift detected" ",\"lib_path\":\"${lib_rel}\",\"pkg_path\":\"${pkg_rel}\""
  fi
done <<< "$BLOCK_RESULT"

echo ""
echo "Full report:"
echo "  python3 ${PROJECT_DIR}/scripts/cos_lib_symlink_invariant_audit.py --format markdown"
echo ""
echo "To bypass (emergency only -- will be logged):"
echo "  COS_ALLOW_LIB_DIVERGENCE=1 git commit ..."
echo ""

exit 1

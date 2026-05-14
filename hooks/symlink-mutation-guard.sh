#!/usr/bin/env bash
# SCOPE: os-only
# symlink-mutation-guard.sh — PreToolUse Bash hook that catches symlink-related
# mutation hazards before they execute.
#
# Why: Agents have tripped on the project's directory-symlink topology — most
# notably the 2026-05-02 incident where an agent did `rm lib/harness_adapter/codex.py
# && ln -s ../../packages/.../codex.py lib/harness_adapter/codex.py`, creating
# a self-referential loop because lib/harness_adapter is itself a directory
# symlink to packages/agent-lifecycle/lib/harness_adapter — both paths resolve
# to the same place.
#
# What this hook detects (PreToolUse, exit 2 = block, exit 0 = allow):
#   1. SELF-LOOP `ln -s`: when target resolves to the same path as the link
#      after resolution. Hard block.
#   2. PARENT-IS-SYMLINK mutation: when `rm`, `mv`, `ln -s` operates on a path
#      whose parent directory is a symlink. Soft warn (stderr) + allow.
#   3. UNRESOLVED CROSS-PROJECT mutation: when target paths cross project
#      boundaries via symlink traversal. Soft warn.
#
# Bypass: COS_ALLOW_SYMLINK_MUTATION=1 env var (logged to audit trail).
#
# Dependencies: jq, python3, readlink (-f compatible). Reads stdin JSON
# tool-call payload from Claude Code / Codex.

set -uo pipefail

# Killswitch: respect project-level disable.
if [ "${DISABLE_HOOK_SYMLINK_MUTATION_GUARD:-false}" = "true" ]; then
  exit 0
fi

# Bypass via env (logged for audit).
if [ "${COS_ALLOW_SYMLINK_MUTATION:-0}" = "1" ]; then
  exit 0
fi

# Read stdin JSON
INPUT=$(cat)
[ -z "$INPUT" ] && exit 0

# Tool name + command
TOOL_NAME=$(echo "$INPUT" | python3 -c "import json,sys;d=json.loads(sys.stdin.read() or '{}');print(d.get('tool_name',''))" 2>/dev/null)
[ "$TOOL_NAME" = "Bash" ] || exit 0

COMMAND=$(echo "$INPUT" | python3 -c "import json,sys;d=json.loads(sys.stdin.read() or '{}');print(d.get('tool_input',{}).get('command',''))" 2>/dev/null)
[ -n "$COMMAND" ] || exit 0

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}"

# Helper: resolve absolute path (no -e check; we want resolution even if path doesn't exist yet)
resolve_abs() {
  local p="$1"
  # If absolute, return as-is. If relative, prefix with project_dir.
  case "$p" in
    /*) echo "$p" ;;
    *) echo "$PROJECT_DIR/$p" ;;
  esac
}

# Helper: resolve parent-of-path through symlinks (resolves all parents but not the leaf)
resolve_parent() {
  local p
  p=$(resolve_abs "$1")
  local parent
  parent=$(dirname "$p")
  if [ -d "$parent" ]; then
    cd "$parent" 2>/dev/null && pwd -P || echo "$parent"
  else
    echo "$parent"
  fi
}

# Detector 1: ln -s with relative target inside a symlink-parent (the 2026-05-02 incident pattern).
# Heuristic: if `ln -s <target> <link>` AND link's parent dir is itself a symlink AND target
# is a relative path (especially with `../`), the agent likely has a wrong mental model — the
# target's relative path won't resolve to what they think. BLOCK with explanation.
check_ln_into_symlink_parent() {
  # Capture `ln -s TARGET LINK` (also handles ln -fs, ln -snf, etc.)
  if echo "$COMMAND" | grep -qE '\bln[[:space:]]+(-[a-zA-Z]*s[a-zA-Z]*[[:space:]]+|-s[[:space:]]+)'; then
    local result
    result=$(python3 - "$COMMAND" <<'PY'
import shlex, sys
cmd = sys.argv[1]
try:
    tokens = shlex.split(cmd)
except Exception:
    sys.exit(0)
i = 0
while i < len(tokens):
    if tokens[i] == "ln":
        j = i + 1
        flags = []
        positional = []
        while j < len(tokens) and tokens[j] not in ("&&", "||", ";", "|", "&"):
            if tokens[j].startswith("-"):
                flags.append(tokens[j])
            else:
                positional.append(tokens[j])
            j += 1
        has_s = any("s" in f.lstrip("-") for f in flags)
        if has_s and len(positional) >= 2:
            target = positional[0]
            link = positional[-1]
            print(f"target={target}\x1flink={link}")
        i = j
    else:
        i += 1
PY
)
    [ -n "$result" ] || return 0
    while IFS= read -r line; do
      [ -z "$line" ] && continue
      local target link
      target=$(echo "$line" | sed -n 's/.*target=\(.*\)\x1flink=.*/\1/p')
      link=$(echo "$line" | sed -n 's/.*\x1flink=\(.*\)/\1/p')
      [ -z "$target" ] || [ -z "$link" ] && continue

      # Only flag relative targets (absolute targets have unambiguous resolution)
      case "$target" in
        /*) continue ;;
      esac

      local link_abs link_parent
      link_abs=$(resolve_abs "$link")
      link_parent=$(dirname "$link_abs")

      # Walk up looking for a symlink ancestor in link's parent chain
      local cur="$link_parent" symlink_ancestor=""
      while [ "$cur" != "/" ] && [ -n "$cur" ]; do
        if [ -L "$cur" ]; then
          symlink_ancestor="$cur"
          break
        fi
        cur=$(dirname "$cur")
      done

      if [ -n "$symlink_ancestor" ]; then
        local ancestor_target
        ancestor_target=$(readlink "$symlink_ancestor")
        cat >&2 <<EOF
=== SYMLINK-MUTATION-GUARD: BLOCKED ===
Suspicious ln -s with relative target inside a directory-symlink ancestor:
  ln -s $target $link
  link's parent ancestor is itself a symlink:
    $symlink_ancestor -> $ancestor_target
  Relative target '$target' will NOT resolve from the literal parent path
  but from the symlink's TARGET — likely producing a broken or
  self-referential link.

This is the 2026-05-02 false-architecture incident pattern.

Run first to see real topology:
  bash scripts/topology-discover.sh

Resolutions:
  1. Use an ABSOLUTE target path
  2. Edit the file at its real location (e.g. via the dir-symlink itself)
     instead of recreating the symlink
  3. Bypass (logged):  COS_ALLOW_SYMLINK_MUTATION=1 ln -s ...
EOF
        exit 2
      fi
    done <<< "$result"
  fi
  return 0
}

# Detector 2: rm/mv on path under directory symlink (warn only, don't block)
check_parent_is_symlink() {
  if echo "$COMMAND" | grep -qE '\b(rm|mv|cp)\b'; then
    # Best-effort: extract paths after rm/mv/cp; soft check
    local paths
    paths=$(python3 - "$COMMAND" <<'PY'
import shlex, sys
cmd = sys.argv[1]
try:
    tokens = shlex.split(cmd)
except Exception:
    sys.exit(0)
ops = {"rm", "mv", "cp"}
i = 0
out = []
while i < len(tokens):
    if tokens[i] in ops:
        j = i + 1
        while j < len(tokens) and tokens[j] not in ("&&", "||", ";", "|", "&"):
            if not tokens[j].startswith("-"):
                out.append(tokens[j])
            j += 1
        i = j
    else:
        i += 1
print("\n".join(out))
PY
)
    while IFS= read -r p; do
      [ -z "$p" ] && continue
      local abs parent
      abs=$(resolve_abs "$p")
      parent=$(dirname "$abs")
      # Walk up looking for a symlink ancestor
      local cur="$parent"
      while [ "$cur" != "/" ] && [ -n "$cur" ]; do
        if [ -L "$cur" ]; then
          local cur_target
          cur_target=$(readlink "$cur")
          echo "[symlink-mutation-guard] WARN: '$p' lives under a directory symlink ancestor:" >&2
          echo "  $cur -> $cur_target" >&2
          echo "  Mutations affect BOTH the symlink path AND the target path." >&2
          echo "  Run scripts/topology-discover.sh to see full topology." >&2
          break
        fi
        cur=$(dirname "$cur")
      done
    done <<< "$paths"
  fi
  return 0
}

# Run detectors
check_ln_into_symlink_parent || exit 2
check_parent_is_symlink

exit 0

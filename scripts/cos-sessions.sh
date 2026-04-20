#!/usr/bin/env bash
# SCOPE: os-only
# cos-sessions — Show Cognitive OS session history
#
# Reads .cognitive-os/metrics/session-log.jsonl (written by hooks/session-sanity.sh)
# and displays per-project + cross-project session history.
#
# Usage:
#   bash scripts/cos-sessions.sh                 # show last 10 sessions for THIS project
#   bash scripts/cos-sessions.sh --last 5        # show last N sessions
#   bash scripts/cos-sessions.sh --all-projects  # show sessions across all COS-installed projects
#   bash scripts/cos-sessions.sh --json          # machine-parseable output
#   bash scripts/cos-sessions.sh --help          # this message

set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
SESSION_LOG="$PROJECT_DIR/.cognitive-os/metrics/session-log.jsonl"
REGISTRY_DIRS=()

# Flags
LAST=10
ALL_PROJECTS=false
JSON=false

usage() {
  cat <<'EOF'
Usage: cos-sessions [OPTIONS]

Show Cognitive OS session history — which sessions ran in which projects, when.

Options:
  --last N           Show last N sessions (default: 10)
  --all-projects     Aggregate across all projects registered in auto-update-projects
  --json             Machine-parseable JSON output
  --help, -h         Show this help

Examples:
  cos sessions                      # last 10 sessions in this project
  cos sessions --last 3             # last 3 sessions in this project
  cos sessions --all-projects       # all sessions across all COS-installed projects
  cos sessions --all-projects --json

Source:  .cognitive-os/metrics/session-log.jsonl (appended by hooks/session-sanity.sh)
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --last) LAST="$2"; shift 2;;
    --all-projects) ALL_PROJECTS=true; shift;;
    --json) JSON=true; shift;;
    --help|-h) usage; exit 0;;
    *) echo "Unknown option: $1" >&2; usage; exit 1;;
  esac
done

# ── Resolve session logs to read ────────────────────────────────────────
LOG_FILES=()

if [ "$ALL_PROJECTS" = true ]; then
  # Read the auto-update-projects registry to find all COS-installed projects
  REGISTRY_FILE="$PROJECT_DIR/.cognitive-os/projects-registry.json"
  if [ -f "$REGISTRY_FILE" ]; then
    # Extract project_dir field from each registry entry
    while IFS= read -r pdir; do
      [ -z "$pdir" ] && continue
      candidate="$pdir/.cognitive-os/metrics/session-log.jsonl"
      [ -f "$candidate" ] && LOG_FILES+=("$candidate")
    done < <(grep -oE '"project_dir"[[:space:]]*:[[:space:]]*"[^"]+"' "$REGISTRY_FILE" | sed 's/.*"\([^"]*\)"$/\1/')
  fi
  # Also always include current project's log
  [ -f "$SESSION_LOG" ] && LOG_FILES+=("$SESSION_LOG")
else
  [ -f "$SESSION_LOG" ] && LOG_FILES=("$SESSION_LOG")
fi

# Deduplicate
if [ ${#LOG_FILES[@]} -gt 1 ]; then
  IFS=$'\n' LOG_FILES=($(printf "%s\n" "${LOG_FILES[@]}" | sort -u))
fi

if [ ${#LOG_FILES[@]} -eq 0 ]; then
  if [ "$JSON" = true ]; then
    echo '{"sessions":[],"note":"no session-log.jsonl found"}'
  else
    echo "No session history available."
    echo "Run a session with session-sanity hook wired to start logging."
    echo "Expected location: $SESSION_LOG"
  fi
  exit 0
fi

# ── Collect all entries, sort by timestamp descending ────────────────────
ALL_ENTRIES=$(for f in "${LOG_FILES[@]}"; do cat "$f" 2>/dev/null; done | sort -r -t'"' -k4)
SELECTED=$(echo "$ALL_ENTRIES" | head -n "$LAST")

if [ "$JSON" = true ]; then
  # Wrap entries in a JSON array
  printf '{"sessions":['
  first=true
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    if [ "$first" = true ]; then
      first=false
    else
      printf ','
    fi
    printf '%s' "$line"
  done <<< "$SELECTED"
  printf '],"count":%d,"source_files":%d}\n' "$(echo "$SELECTED" | grep -c . || true)" "${#LOG_FILES[@]}"
  exit 0
fi

# ── Human-readable table ────────────────────────────────────────────────
if [ "$ALL_PROJECTS" = true ]; then
  echo "COS Sessions (cross-project, last $LAST)"
else
  echo "COS Sessions — $(basename "$PROJECT_DIR") (last $LAST)"
fi
echo "═══════════════════════════════════════════════════════════════════════════════"
printf "%-22s %-20s %-12s %-5s %-4s %s\n" "TIMESTAMP" "PROJECT" "PROFILE" "SKILLS" "HOOKS" "SELF"
printf "%-22s %-20s %-12s %-5s %-4s %s\n" "─────────────────────" "──────────────────" "──────────" "─────" "────" "────"

# Parse each JSONL entry with Python for robustness
python3 <<PYEOF
import json, sys
data = """$SELECTED"""
for line in data.strip().split("\n"):
    if not line.strip():
        continue
    try:
        r = json.loads(line)
    except Exception:
        continue
    ts = r.get("timestamp", "-")[:19]  # trim Z
    proj = r.get("project", "-")[:20]
    prof = r.get("profile", "-")[:12]
    skl = str(r.get("skills_count", "?"))
    hks = str(r.get("hooks_wired", "?"))
    selfh = "yes" if r.get("self_hosted") else "no"
    print(f"{ts:<22} {proj:<20} {prof:<12} {skl:<5} {hks:<4} {selfh}")
PYEOF

echo ""
if [ "$ALL_PROJECTS" = true ]; then
  echo "Sources: ${#LOG_FILES[@]} log file(s)"
else
  echo "Source:  $SESSION_LOG"
fi

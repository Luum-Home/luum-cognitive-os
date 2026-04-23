#!/usr/bin/env bash
# SCOPE: os-only
# cos-ghost-skills.sh — List skills exposed but never invoked in the last N days.
#
# A "ghost" skill is one present in the active skill exposure surface that has
# zero matching records in .cognitive-os/metrics/skill-usage.jsonl within the
# window.
#
# Intended as the input for the next cleanup sprint: these are candidates for
# archival / de-exposure.
#
# Usage:
#   bash scripts/cos-ghost-skills.sh              # default 30 days, text output
#   bash scripts/cos-ghost-skills.sh --days 14
#   bash scripts/cos-ghost-skills.sh --json

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}}}"

DAYS=30
MODE="pretty"

usage() {
  cat <<EOF
cos ghost-skills — list skills with zero invocations in the window

Usage:
  bash scripts/cos-ghost-skills.sh [--days N] [--json] [--help]

Flags:
  --days N   Window size in days (default: 30)
  --json     Machine-parseable JSON output
  --help     Show this help and exit

Exit code: 0 always.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --days) shift; DAYS="${1:-30}" ;;
    --json) MODE="json" ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown flag: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required for cos-ghost-skills" >&2
  exit 1
fi

PROJECT_ROOT="$PROJECT_ROOT" DAYS="$DAYS" MODE="$MODE" python3 <<'PYEOF'
import json, os, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

root = Path(os.environ["PROJECT_ROOT"])
days = int(os.environ.get("DAYS", "30"))
mode = os.environ.get("MODE", "pretty")

sys.path.insert(0, str(root))
try:
    from lib.telemetry import iter_records, SKILL_USAGE_FILE
except Exception as exc:
    print(f"error: cannot import lib.telemetry ({exc})", file=sys.stderr)
    sys.exit(1)

cutoff = datetime.now(timezone.utc) - timedelta(days=days)


def in_window(rec):
    ts = rec.get("timestamp")
    if not ts:
        return False
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")) >= cutoff
    except Exception:
        return False


invoked = set()
for r in iter_records(SKILL_USAGE_FILE):
    if in_window(r):
        name = r.get("name")
        if name:
            invoked.add(name)

skills_dir = root / ".claude" / "skills"
canonical_skills_dir = root / ".cognitive-os" / "skills" / "cos"
legacy_skills_dir = root / ".cognitive-os" / "skills"

if canonical_skills_dir.is_dir():
    skills_dir = canonical_skills_dir
elif skills_dir.is_dir():
    skills_dir = skills_dir
elif legacy_skills_dir.is_dir():
    skills_dir = legacy_skills_dir

exposed = set()
if skills_dir.is_dir():
    for entry in skills_dir.iterdir():
        if entry.is_dir() and not entry.name.startswith("."):
            exposed.add(entry.name)

ghosts = sorted(exposed - invoked)

if mode == "json":
    json.dump({
        "window_days": days,
        "skills_surface": str(skills_dir),
        "exposed_count": len(exposed),
        "invoked_count": len(invoked & exposed),
        "ghost_count":   len(ghosts),
        "ghosts":        ghosts,
    }, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    sys.exit(0)

print(f"Ghost skills — last {days} day(s)")
print(f"  surface : {skills_dir}")
print(f"  exposed : {len(exposed)}")
print(f"  invoked : {len(invoked & exposed)}")
print(f"  ghosts  : {len(ghosts)}")
if not ghosts:
    print("(none — every exposed skill had at least one invocation)")
else:
    print()
    for g in ghosts:
        print(f"  · {g}")
PYEOF
exit 0

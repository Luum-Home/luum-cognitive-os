#!/usr/bin/env bash
# cleanup_snapshots.sh — Prune expired pre-agent snapshots (ADR-099)
#
# Reads ttl_days from cognitive-os.yaml (key: snapshots.ttl_days, default: 30).
# Deletes snapshot directories older than ttl_days from .cognitive-os/snapshots/.
#
# Usage:
#   ./scripts/cleanup_snapshots.sh [--ttl-days N] [--dry-run] [--project-dir PATH]
#
# Options:
#   --ttl-days N       Override TTL (days). Default: read from cognitive-os.yaml or 30.
#   --dry-run          Show what would be deleted, do not delete.
#   --project-dir PATH Project root (default: CLAUDE_PROJECT_DIR or cwd).
#
# Exit codes: 0=success, 1=error

set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${COGNITIVE_OS_PROJECT_DIR:-$(pwd)}}"
TTL_DAYS=""
DRY_RUN=false

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --ttl-days)
      TTL_DAYS="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --project-dir)
      PROJECT_DIR="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

# Read TTL from cognitive-os.yaml if not provided
if [ -z "$TTL_DAYS" ]; then
  YAML="$PROJECT_DIR/cognitive-os.yaml"
  if [ -f "$YAML" ] && command -v python3 >/dev/null 2>&1; then
    TTL_DAYS=$(python3 -c "
import sys
try:
    # Simple YAML parse without PyYAML dependency
    with open('$YAML') as f:
        content = f.read()
    # Find 'ttl_days:' line under 'snapshots:' block
    in_snapshots = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith('snapshots:'):
            in_snapshots = True
            continue
        if in_snapshots:
            if stripped.startswith('ttl_days:'):
                val = stripped.split(':', 1)[1].strip()
                print(val)
                sys.exit(0)
            elif stripped and not stripped.startswith('#') and ':' in stripped and not stripped.startswith(' ') and not stripped.startswith('\t'):
                in_snapshots = False
    print(30)
except Exception:
    print(30)
" 2>/dev/null || echo 30)
  fi
  TTL_DAYS="${TTL_DAYS:-30}"
fi

SNAPSHOTS_DIR="$PROJECT_DIR/.cognitive-os/snapshots"

if [ ! -d "$SNAPSHOTS_DIR" ]; then
  echo "No snapshots directory found: $SNAPSHOTS_DIR"
  exit 0
fi

echo "Pruning snapshots older than $TTL_DAYS days from $SNAPSHOTS_DIR"
if [ "$DRY_RUN" = true ]; then
  echo "(dry-run: no files will be deleted)"
fi

if command -v python3 >/dev/null 2>&1; then
  python3 - <<PYEOF
import sys
sys.path.insert(0, '$PROJECT_DIR')
from lib.snapshot_manager import prune_expired, list_snapshots
from pathlib import Path

repo = Path('$PROJECT_DIR')
ttl = int('$TTL_DAYS')
dry_run = '$DRY_RUN' == 'true'

if dry_run:
    import time
    snaps = list_snapshots(repo)
    cutoff = time.time() - (ttl * 86400)
    to_delete = [s for s in snaps if s.get('timestamp', 0) < cutoff]
    if to_delete:
        print(f"Would delete {len(to_delete)} snapshot(s):")
        for s in to_delete:
            print(f"  {s.get('snapshot_id', '?')} ({s.get('timestamp_iso', '?')})")
    else:
        print("No expired snapshots found.")
else:
    deleted = prune_expired(repo, ttl_days=ttl)
    if deleted:
        print(f"Deleted {len(deleted)} snapshot(s):")
        for d in deleted:
            print(f"  {d}")
    else:
        print("No expired snapshots to prune.")
PYEOF
else
  echo "python3 not available. Falling back to find-based prune."
  find "$SNAPSHOTS_DIR" -mindepth 1 -maxdepth 1 -type d -mtime +"$TTL_DAYS" | while read -r snap; do
    if [ "$DRY_RUN" = true ]; then
      echo "  Would delete: $(basename "$snap")"
    else
      rm -rf "$snap"
      echo "  Deleted: $(basename "$snap")"
    fi
  done
fi

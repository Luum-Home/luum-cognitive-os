#!/usr/bin/env bash
# @on-demand: run periodically to prune snapshots older than ttl_days (ADR-099); no Claude event triggers it
# cleanup-snapshots.sh — Prune expired pre-agent snapshots (ADR-099)
#
# Reads ttl_days from cognitive-os.yaml (key: snapshots.ttl_days, default: 30).
# Deletes snapshot directories older than ttl_days from .cognitive-os/snapshots/.
# Also enforces snapshots.max_total_mb when configured.
#
# Usage:
#   ./scripts/cleanup-snapshots.sh [--ttl-days N] [--max-total-mb N] [--dry-run] [--project-dir PATH]
#
# Options:
#   --ttl-days N       Override TTL (days). Default: read from cognitive-os.yaml or 30.
#   --max-total-mb N   Override aggregate snapshot cap. Default: snapshots.max_total_mb or none.
#   --dry-run          Show what would be deleted, do not delete.
#   --project-dir PATH Project root (default: CLAUDE_PROJECT_DIR or cwd).
#
# Exit codes: 0=success, 1=error

set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${COGNITIVE_OS_PROJECT_DIR:-$(pwd)}}"
TTL_DAYS=""
MAX_TOTAL_MB=""
DRY_RUN=false

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --ttl-days)
      TTL_DAYS="$2"
      shift 2
      ;;
    --max-total-mb)
      MAX_TOTAL_MB="$2"
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

YAML="$PROJECT_DIR/cognitive-os.yaml"

read_snapshot_config_int() {
  local key="$1"
  local default_value="$2"
  if [ ! -f "$YAML" ] || ! command -v python3 >/dev/null 2>&1; then
    printf '%s\n' "$default_value"
    return 0
  fi
  python3 - "$YAML" "$key" "$default_value" <<'PYEOF' 2>/dev/null || printf '%s\n' "$default_value"
import sys
from pathlib import Path

yaml_path, key, default = sys.argv[1], sys.argv[2], sys.argv[3]
in_snapshots = False
for line in Path(yaml_path).read_text().splitlines():
    stripped = line.strip()
    if stripped.startswith('snapshots:'):
        in_snapshots = True
        continue
    if not in_snapshots:
        continue
    if stripped and not line.startswith((' ', '\t')) and ':' in stripped:
        break
    if stripped.startswith(f'{key}:'):
        raw = stripped.split(':', 1)[1].split('#', 1)[0].strip()
        print(raw or default)
        sys.exit(0)
print(default)
PYEOF
}

# Read retention config from cognitive-os.yaml if not provided
if [ -z "$TTL_DAYS" ]; then
  TTL_DAYS=$(read_snapshot_config_int ttl_days 30)
fi
if [ -z "$MAX_TOTAL_MB" ]; then
  MAX_TOTAL_MB=$(read_snapshot_config_int max_total_mb "")
fi

SNAPSHOTS_DIR="$PROJECT_DIR/.cognitive-os/snapshots"

if [ ! -d "$SNAPSHOTS_DIR" ]; then
  echo "No snapshots directory found: $SNAPSHOTS_DIR"
  exit 0
fi

echo "Pruning snapshots older than $TTL_DAYS days from $SNAPSHOTS_DIR"
if [ -n "$MAX_TOTAL_MB" ]; then
  echo "Enforcing aggregate snapshot cap of $MAX_TOTAL_MB MiB"
fi
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
max_total_raw = '$MAX_TOTAL_MB'
max_total = int(max_total_raw) if max_total_raw else None

def _snapshot_size(path: Path) -> int:
    return sum(p.stat().st_size for p in path.rglob('*') if p.is_file())

if dry_run:
    import time
    snaps = list_snapshots(repo)
    cutoff = time.time() - (ttl * 86400)
    to_delete = [s for s in snaps if s.get('timestamp', 0) < cutoff]
    remaining = [s for s in snaps if s not in to_delete]
    if max_total is not None:
        cap = max_total * 1024 * 1024
        sized = []
        for snap in remaining:
            snap_dir = Path(snap.get('snapshot_dir', ''))
            if snap_dir.is_dir():
                sized.append((snap, _snapshot_size(snap_dir)))
        total = sum(size for _, size in sized)
        for snap, size in sorted(sized, key=lambda item: item[0].get('timestamp', 0)):
            if total <= cap:
                break
            to_delete.append(snap)
            total -= size
    if to_delete:
        print(f"Would delete {len(to_delete)} snapshot(s):")
        for s in to_delete:
            print(f"  {s.get('snapshot_id', '?')} ({s.get('timestamp_iso', '?')})")
    else:
        print("No expired or over-cap snapshots found.")
else:
    deleted = prune_expired(repo, ttl_days=ttl, max_total_mb=max_total)
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

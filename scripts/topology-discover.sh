#!/usr/bin/env bash
# SCOPE: both
# topology-discover.sh — generate a manifest of file/directory symlinks in the project.
#
# Why: Agents have made false-architecture assumptions (e.g., assuming
# `lib/harness_adapter/codex.py` is a file-level symlink when in fact the
# parent `lib/harness_adapter/` is a directory-level symlink). The wrong
# mental model led to a self-referential `ln -s` loop that was only
# recovered because the file existed in git. This primitive surfaces the
# real topology so agents (and humans) can verify before mutating.
#
# Output: writes JSON manifest to .cognitive-os/topology.json with shape:
#   {
#     "schema_version": "1.0.0",
#     "generated_at_epoch": <int>,
#     "directory_symlinks": [{ "path": "lib/harness_adapter",
#                              "target": "packages/agent-lifecycle/lib/harness_adapter",
#                              "resolved": "<absolute>" }, ...],
#     "file_symlinks":      [{ "path": "lib/ground_truth.py",
#                              "target": "../packages/verification-audit/lib/ground_truth.py",
#                              "resolved": "<absolute>" }, ...],
#     "summary": { "directory_count": N, "file_count": M }
#   }
#
# Idempotent. Cheap (<1s on this repo). Safe to run any time.

set -uo pipefail

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}}"
OUT_FILE="$PROJECT_DIR/.cognitive-os/topology.json"
JSON=0
QUIET=0

for arg in "$@"; do
  case "$arg" in
    --json) JSON=1 ;;
    --quiet) QUIET=1 ;;
    --out=*) OUT_FILE="${arg#--out=}" ;;
    --help|-h)
      cat <<EOF
Usage: topology-discover.sh [--json] [--quiet] [--out=PATH]

Discover all symlinks (file + directory) in the project and emit a manifest.

  --json    Print JSON to stdout (also written to manifest unless --out=-)
  --quiet   Suppress human summary
  --out=PATH  Override manifest path (default .cognitive-os/topology.json)
EOF
      exit 0 ;;
    *) echo "Unknown arg: $arg" >&2; exit 2 ;;
  esac
done

cd "$PROJECT_DIR" || { echo "Cannot cd to $PROJECT_DIR" >&2; exit 2; }
command -v python3 >/dev/null 2>&1 || { echo "python3 required" >&2; exit 2; }

# Build manifest via Python (does its own walk; atomic write)
mkdir -p "$(dirname "$OUT_FILE")"
python3 - "$OUT_FILE" "$PROJECT_DIR" <<'PY'
import json
import os
import sys
import time
from pathlib import Path

out_path = Path(sys.argv[1])
project_dir = Path(sys.argv[2]).resolve()

PRUNE = {".git", "node_modules", ".venv", "venv",
         "__pycache__", ".pytest_cache", ".ruff_cache",
         ".mypy_cache", "dist", "build"}
PRUNE_PATHS = {project_dir / ".cognitive-os" / "sessions",
               project_dir / ".cognitive-os" / "runtime",
               project_dir / ".cognitive-os" / "metrics"}

dir_symlinks = []
file_symlinks = []

for root, dirs, files in os.walk(project_dir, followlinks=False):
    root_path = Path(root)
    if any(p in root_path.parts for p in PRUNE):
        dirs[:] = []
        continue
    if root_path in PRUNE_PATHS:
        dirs[:] = []
        continue

    # Inspect dirs (still listed before walk descends) + files for symlinks.
    for name in list(dirs):
        full = root_path / name
        if full.is_symlink():
            try:
                target = os.readlink(full)
                try:
                    resolved = str(full.resolve())
                except Exception:
                    resolved = ""
                rel = str(full.relative_to(project_dir))
                dir_symlinks.append({"path": rel, "target": target, "resolved": resolved})
            except OSError:
                pass
            # Don't descend into symlinked dirs (avoids double-counting & loops)
            dirs.remove(name)

    for name in files:
        full = root_path / name
        if full.is_symlink():
            try:
                target = os.readlink(full)
                try:
                    resolved = str(full.resolve())
                except Exception:
                    resolved = ""
                rel = str(full.relative_to(project_dir))
                file_symlinks.append({"path": rel, "target": target, "resolved": resolved})
            except OSError:
                pass

dir_symlinks.sort(key=lambda e: e["path"])
file_symlinks.sort(key=lambda e: e["path"])

manifest = {
    "schema_version": "1.0.0",
    "generated_at_epoch": int(time.time()),
    "project_dir": str(project_dir),
    "directory_symlinks": dir_symlinks,
    "file_symlinks": file_symlinks,
    "summary": {
        "directory_count": len(dir_symlinks),
        "file_count": len(file_symlinks),
    },
}

# Atomic write
tmp = out_path.with_suffix(out_path.suffix + ".tmp")
tmp.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
os.replace(tmp, out_path)
PY

if [ "$JSON" = "1" ]; then
  cat "$OUT_FILE"
elif [ "$QUIET" != "1" ]; then
  python3 -c "
import json
m = json.load(open('$OUT_FILE'))
s = m['summary']
print(f\"Topology: {s['directory_count']} directory symlinks, {s['file_count']} file symlinks\")
print(f\"Manifest: $OUT_FILE\")
print()
if m['directory_symlinks']:
    print('Directory symlinks (mutations affect BOTH paths):')
    for e in m['directory_symlinks'][:5]:
        print(f\"  {e['path']} -> {e['target']}\")
    if len(m['directory_symlinks']) > 5:
        print(f\"  ... and {len(m['directory_symlinks'])-5} more\")
"
fi

exit 0

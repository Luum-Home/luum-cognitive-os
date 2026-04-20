#!/bin/bash
# SCOPE: both
# Engram Sync — Exports project-scoped observations to JSON for git tracking.
#
# Only exports observations where project matches the current repo.
# This keeps cross-device sync to THIS project only — not your entire engram.
#
# Usage:
#   ./scripts/engram-sync.sh           # export current project
#   ./scripts/engram-sync.sh --all     # export all observations (NOT recommended)
#   ./scripts/engram-sync.sh --import  # import exports back into engram
#
# Output: .engram/exports/{project}.jsonl (one JSON object per line)

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
EXPORT_DIR="$PROJECT_DIR/.engram/exports"
DB_PATH="${ENGRAM_DB:-$HOME/.engram/engram.db}"

# Determine project name — try git remote, fallback to dir name
PROJECT_NAME="${COGNITIVE_OS_PROJECT:-}"
if [ -z "$PROJECT_NAME" ]; then
  if [ -d "$PROJECT_DIR/.git" ]; then
    REMOTE=$(git -C "$PROJECT_DIR" remote get-url origin 2>/dev/null || true)
    if [ -n "$REMOTE" ]; then
      PROJECT_NAME=$(basename "$REMOTE" .git)
    fi
  fi
fi
[ -z "$PROJECT_NAME" ] && PROJECT_NAME=$(basename "$PROJECT_DIR")

if [ ! -f "$DB_PATH" ]; then
  echo "engram DB not found at $DB_PATH — nothing to sync" >&2
  exit 0
fi

MODE="${1:-export}"

# ─── Import mode ──────────────────────────────────────────────────────────────
if [ "$MODE" = "--import" ]; then
  EXPORT_FILE="$EXPORT_DIR/${PROJECT_NAME}.jsonl"
  if [ ! -f "$EXPORT_FILE" ]; then
    echo "No export file at $EXPORT_FILE — nothing to import" >&2
    exit 0
  fi

  python3 << PYEOF
import sqlite3, json, sys
db = sqlite3.connect("$DB_PATH")
imported = 0
skipped = 0
with open("$EXPORT_FILE") as f:
    for line in f:
        try:
            obs = json.loads(line)
            # Skip if already exists (by title + project)
            existing = db.execute(
                "SELECT id FROM observations WHERE title=? AND project=?",
                (obs.get("title", ""), obs.get("project", ""))
            ).fetchone()
            if existing:
                skipped += 1
                continue

            db.execute("""INSERT INTO observations
                (session_id, type, title, content, project, scope,
                 topic_key, revision_count, duplicate_count,
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, ?, ?)""",
                (obs.get("session_id", "imported"),
                 obs.get("type", "discovery"),
                 obs.get("title", ""),
                 obs.get("content", ""),
                 obs.get("project", "$PROJECT_NAME"),
                 obs.get("scope", "project"),
                 obs.get("topic_key"),
                 obs.get("created_at", ""),
                 obs.get("updated_at", "")))
            imported += 1
        except Exception as e:
            print(f"Error importing line: {e}", file=sys.stderr)

db.commit()
db.close()
print(f"Imported {imported} observations, skipped {skipped} duplicates")
PYEOF
  exit 0
fi

# ─── Export mode (default) ────────────────────────────────────────────────────
mkdir -p "$EXPORT_DIR"

EXPORT_FILTER=""
if [ "$MODE" != "--all" ]; then
  # Match project name + common variations
  EXPORT_FILTER="AND (project = '$PROJECT_NAME' OR project = 'luum-agent-os' OR project = 'luum-cognitive-os' OR project = 'cognitive-os-demo')"
fi

EXPORT_FILE="$EXPORT_DIR/${PROJECT_NAME}.jsonl"

python3 << PYEOF
import sqlite3, json
db = sqlite3.connect("$DB_PATH")
rows = db.execute(f"""
    SELECT session_id, type, title, content, project, scope,
           topic_key, created_at, updated_at
    FROM observations
    WHERE deleted_at IS NULL
    $EXPORT_FILTER
    ORDER BY created_at ASC
""").fetchall()

cols = ["session_id", "type", "title", "content", "project", "scope",
        "topic_key", "created_at", "updated_at"]

with open("$EXPORT_FILE", "w") as f:
    for row in rows:
        obs = dict(zip(cols, row))
        f.write(json.dumps(obs, default=str) + "\n")

print(f"Exported {len(rows)} observations to {'$EXPORT_FILE'}")
db.close()
PYEOF

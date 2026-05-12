#!/usr/bin/env bash
# SCOPE: os-only
# ADR-269 Primitive 2 — SessionStart hook warning operators about
# history-rewrite bundles that are not registered in the ledger.
#
# Non-blocking: emits a visible WARN to stderr (operator sees it on every
# session until they run `cos-history-rewrite-audit --register ...`).
#
# Bypass: COS_ALLOW_UNDOCUMENTED_REWRITES=1 (logged with reason).
# Latency target: <500ms (no network, no git fsck, just glob+yaml).
set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${COS_PROJECT_DIR:-$(pwd)}}"
LOG_DIR="$PROJECT_DIR/.cognitive-os/logs"
LOG_FILE="$LOG_DIR/history-rewrite-documented.jsonl"
mkdir -p "$LOG_DIR"

TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

write_log() {
  local status="$1" message="$2" orphan_count="${3:-0}"
  python3 - "$LOG_FILE" "$TS" "$status" "$message" "$orphan_count" <<'PY2' || true
import json, sys
log_file, ts, status, message, orphan_count = sys.argv[1:6]
try:
    n = int(orphan_count)
except ValueError:
    n = 0
entry = {
    "schema_version": "history-rewrite-documented/v1",
    "timestamp": ts,
    "status": status,
    "message": message,
    "orphan_count": n,
}
with open(log_file, "a", encoding="utf-8") as fh:
    fh.write(json.dumps(entry, sort_keys=True) + "\n")
PY2
}

if [ "${COS_ALLOW_UNDOCUMENTED_REWRITES:-0}" = "1" ]; then
  write_log "bypassed" "COS_ALLOW_UNDOCUMENTED_REWRITES=1 set; skipping orphan-bundle warning"
  exit 0
fi

ORPHANS_JSON="$(
  PYTHONPATH="$PROJECT_DIR" python3 - "$PROJECT_DIR" <<'PY2' 2>/dev/null || echo '{"status":"error","orphans":[]}'
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
try:
    from lib.history_rewrite_ledger import find_orphan_bundles
    orphans = [str(p.relative_to(Path(sys.argv[1]))) for p in find_orphan_bundles(Path(sys.argv[1]))]
    print(json.dumps({"status": "ok", "orphans": orphans}))
except Exception as exc:
    print(json.dumps({"status": "error", "orphans": [], "error": repr(exc)}))
PY2
)"

ORPHAN_COUNT="$(printf '%s' "$ORPHANS_JSON" | python3 -c "import json,sys; print(len(json.load(sys.stdin).get('orphans', [])))" 2>/dev/null || echo 0)"

if [ "${ORPHAN_COUNT:-0}" = "0" ]; then
  write_log "ok" "no orphan history-rewrite bundles detected" 0
  exit 0
fi

cat >&2 <<EOF
WARN: UNDOCUMENTED HISTORY REWRITE DETECTED (ADR-269)
  $ORPHAN_COUNT recovery bundle(s) have no matching entry in
  manifests/history-rewrite-ledger.yaml.

  Inspect: scripts/cos-history-rewrite-audit --orphans
  Resolve: scripts/cos-history-rewrite-audit --register <bundle> --adr ADR-NNN --reason "..."
  Bypass : COS_ALLOW_UNDOCUMENTED_REWRITES=1 (logged)
EOF

printf '%s' "$ORPHANS_JSON" | python3 - <<'PY2' 1>&2 2>/dev/null || true
import json, sys
data = json.load(sys.stdin)
for p in (data.get("orphans") or [])[:5]:
    print(f"  - {p}")
PY2

write_log "warn" "orphan history-rewrite bundles detected" "$ORPHAN_COUNT"
exit 0

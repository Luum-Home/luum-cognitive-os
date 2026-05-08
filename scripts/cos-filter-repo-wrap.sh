#!/usr/bin/env bash
# ADR-242 governed wrapper around git-filter-repo.
set -euo pipefail

PROJECT_DIR="$(pwd)"
RULES_FILE=""
BACKUP_MIRROR=""
RECOVERY_JSON=""
FORCE_RE_RUN=0
DRY_RUN=0
PASSTHROUGH=()

while [ "$#" -gt 0 ]; do
  case "$1" in
    --project-dir) PROJECT_DIR="$2"; shift 2 ;;
    --rules) RULES_FILE="$2"; shift 2 ;;
    --backup-mirror) BACKUP_MIRROR="$2"; shift 2 ;;
    --recovery-json) RECOVERY_JSON="$2"; shift 2 ;;
    --force-re-run) FORCE_RE_RUN=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --) shift; PASSTHROUGH=("$@"); break ;;
    *) echo "cos-filter-repo-wrap: unknown arg $1" >&2; exit 2 ;;
  esac
done

[ -n "$RULES_FILE" ] || { echo "cos-filter-repo-wrap: --rules required" >&2; exit 2; }
[ -f "$RULES_FILE" ] || { echo "cos-filter-repo-wrap: rules file not found: $RULES_FILE" >&2; exit 2; }
PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd)"
RUNTIME_DIR="$PROJECT_DIR/.cognitive-os/runtime"
mkdir -p "$RUNTIME_DIR"
STATE_FILE="$RUNTIME_DIR/last-filter-repo.json"
[ -n "$RECOVERY_JSON" ] || RECOVERY_JSON="$RUNTIME_DIR/recovery.json"

HEAD_SHA="$(git -C "$PROJECT_DIR" rev-parse HEAD)"
RULES_HASH="$(shasum -a 256 "$RULES_FILE" | awk '{print $1}')"
ENV_HASH="$({ env | grep -E '^(COS_HISTORY_SANITIZE_|COS_ALLOW_DESTRUCTIVE_GIT=|COS_HISTORY_SANITIZE_METADATA=)' || true; } | LC_ALL=C sort | shasum -a 256 | awk '{print $1}')"
TRIPLE_HASH="$(printf '%s\n%s\n%s\n' "$HEAD_SHA" "$RULES_HASH" "$ENV_HASH" | shasum -a 256 | awk '{print $1}')"

if [ -f "$STATE_FILE" ] && [ "$FORCE_RE_RUN" != "1" ]; then
  PREV_TRIPLE="$(python3 - "$STATE_FILE" <<'PY' 2>/dev/null || true
import json,sys
try:
    print(json.load(open(sys.argv[1])).get('triple_hash',''))
except Exception:
    print('')
PY
)"
  if [ "$PREV_TRIPLE" = "$TRIPLE_HASH" ]; then
    echo "cos-filter-repo-wrap: refusing idempotent re-run on same HEAD/rules/env; pass --force-re-run to override." >&2
    exit 2
  fi
fi

snapshot_remotes() {
  python3 - "$PROJECT_DIR" <<'PY'
import json, subprocess, sys
root=sys.argv[1]
remotes={}
remote_names=subprocess.run(['git','-C',root,'remote'],text=True,capture_output=True).stdout.splitlines()
for name in remote_names:
    name=name.strip()
    if not name: continue
    urls={}
    for kind in ('fetch','push'):
        p=subprocess.run(['git','-C',root,'remote','get-url',f'--{kind}',name],text=True,capture_output=True)
        if p.returncode == 0 and p.stdout.strip(): urls[kind]=p.stdout.strip()
    if urls: remotes[name]=urls
print(json.dumps(remotes, sort_keys=True))
PY
}

restore_remotes() {
  local json="$1"
  python3 - "$PROJECT_DIR" "$json" <<'PY'
import json, subprocess, sys
root=sys.argv[1]
remotes=json.loads(sys.argv[2] or '{}')
restored=[]
for name, urls in remotes.items():
    fetch=urls.get('fetch') or urls.get('push')
    push=urls.get('push') or fetch
    if not fetch: continue
    exists=subprocess.run(['git','-C',root,'remote','get-url',name],text=True,capture_output=True).returncode == 0
    if not exists:
        subprocess.run(['git','-C',root,'remote','add',name,fetch],check=False)
    else:
        subprocess.run(['git','-C',root,'remote','set-url',name,fetch],check=False)
    if push:
        subprocess.run(['git','-C',root,'remote','set-url','--push',name,push],check=False)
    restored.append(name)
print(json.dumps(restored))
PY
}

REMOTES_JSON="$(snapshot_remotes)"
if [ "$DRY_RUN" = "1" ]; then
  python3 - <<PY
import json
print(json.dumps({
  'schema_version':'cos-filter-repo-wrap-plan/v1',
  'status':'dry-run',
  'head':'$HEAD_SHA',
  'rules_hash':'$RULES_HASH',
  'env_hash':'$ENV_HASH',
  'triple_hash':'$TRIPLE_HASH',
  'remotes': json.loads('''$REMOTES_JSON'''),
}, indent=2, sort_keys=True))
PY
  exit 0
fi

command -v git-filter-repo >/dev/null 2>&1 || { echo "cos-filter-repo-wrap: git-filter-repo not found" >&2; exit 2; }
PRE_HEAD="$HEAD_SHA"
set +e
git -C "$PROJECT_DIR" filter-repo "${PASSTHROUGH[@]}" --replace-text "$RULES_FILE" --force
RC=$?
set -e
RESTORED_JSON="$(restore_remotes "$REMOTES_JSON")"
POST_HEAD="$(git -C "$PROJECT_DIR" rev-parse HEAD 2>/dev/null || true)"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
python3 - "$RECOVERY_JSON" "$STATE_FILE" <<PY
import json, pathlib, sys
payload={
  'schema_version':'cos-filter-repo-recovery/v1',
  'status':'ok' if $RC == 0 else 'failed',
  'timestamp':'$TS',
  'pre_head':'$PRE_HEAD',
  'post_head':'$POST_HEAD',
  'backup_mirror_path':'$BACKUP_MIRROR',
  'rules_file':'$RULES_FILE',
  'rules_hash':'$RULES_HASH',
  'env_hash':'$ENV_HASH',
  'triple_hash':'$TRIPLE_HASH',
  'remotes_before': json.loads('''$REMOTES_JSON'''),
  'remotes_restored': json.loads('''$RESTORED_JSON'''),
  'returncode': $RC,
}
for path in sys.argv[1:]:
    p=pathlib.Path(path); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(payload, indent=2, sort_keys=True)+'\n')
PY
exit "$RC"

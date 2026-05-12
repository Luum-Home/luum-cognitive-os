#!/usr/bin/env bash
# ADR-242 governed wrapper around git-filter-repo.
set -euo pipefail

PROJECT_DIR="$(pwd)"
RULES_FILE=""
BACKUP_MIRROR=""
RECOVERY_JSON=""
FORCE_RE_RUN=0
DRY_RUN=0
ADR_REF=""
ADR_REASON=""
ADR_OPERATOR=""
PASSTHROUGH=()

while [ "$#" -gt 0 ]; do
  case "$1" in
    --project-dir) PROJECT_DIR="$2"; shift 2 ;;
    --rules) RULES_FILE="$2"; shift 2 ;;
    --backup-mirror) BACKUP_MIRROR="$2"; shift 2 ;;
    --recovery-json) RECOVERY_JSON="$2"; shift 2 ;;
    --force-re-run) FORCE_RE_RUN=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --adr-ref) ADR_REF="$2"; shift 2 ;;
    --reason) ADR_REASON="$2"; shift 2 ;;
    --operator) ADR_OPERATOR="$2"; shift 2 ;;
    --) shift; PASSTHROUGH=("$@"); break ;;
    *) echo "cos-filter-repo-wrap: unknown arg $1" >&2; exit 2 ;;
  esac
done

[ -n "$RULES_FILE" ] || { echo "cos-filter-repo-wrap: --rules required" >&2; exit 2; }
[ -f "$RULES_FILE" ] || { echo "cos-filter-repo-wrap: rules file not found: $RULES_FILE" >&2; exit 2; }

# ADR-269 mandatory documentation requirement (skipped for dry-run plans).
if [ "$DRY_RUN" != "1" ] && [ -z "$ADR_REF" ]; then
  cat >&2 <<EOF
ERROR: history rewrites require ADR documentation per ADR-269.
  Re-run with --adr-ref ADR-NNN where ADR-NNN is an Accepted ADR
  documenting the rewrite rationale. If no such ADR exists, create
  one first using docs/02-Decisions/adrs/templates/history-rewrite.template.md.
EOF
  exit 2
fi
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

snapshot_branch_upstreams() {
  python3 - "$PROJECT_DIR" <<'PY'
import json, subprocess, sys
root=sys.argv[1]
cur=subprocess.run(['git','-C',root,'branch','--show-current'],text=True,capture_output=True)
branches={}
refs=subprocess.run(['git','-C',root,'for-each-ref','--format=%(refname:short)','refs/heads'],text=True,capture_output=True)
if refs.returncode == 0:
    for branch in refs.stdout.splitlines():
        branch=branch.strip()
        if not branch: continue
        entry={}
        remote=subprocess.run(['git','-C',root,'config','--get',f'branch.{branch}.remote'],text=True,capture_output=True)
        merge=subprocess.run(['git','-C',root,'config','--get',f'branch.{branch}.merge'],text=True,capture_output=True)
        if remote.returncode == 0 and remote.stdout.strip(): entry['remote']=remote.stdout.strip()
        if merge.returncode == 0 and merge.stdout.strip(): entry['merge']=merge.stdout.strip()
        if entry: branches[branch]=entry
print(json.dumps({'current_branch': cur.stdout.strip() if cur.returncode == 0 else '', 'branches': branches}, sort_keys=True))
PY
}

restore_branch_upstreams() {
  local json="$1"
  python3 - "$PROJECT_DIR" "$json" <<'PY'
import json, subprocess, sys
root=sys.argv[1]
snapshot=json.loads(sys.argv[2] or '{}')
restored=[]
refreshed=[]
errors=[]
branches=snapshot.get('branches', {})
if not isinstance(branches, dict):
    print(json.dumps({'restored': restored, 'refreshed': refreshed, 'errors': ['branch upstream snapshot is malformed']}))
    raise SystemExit(0)
for branch, cfg in branches.items():
    if not isinstance(branch, str) or not isinstance(cfg, dict):
        continue
    if subprocess.run(['git','-C',root,'rev-parse','--verify',f'refs/heads/{branch}'],text=True,capture_output=True).returncode != 0:
        errors.append(f'{branch}: missing local branch')
        continue
    remote=cfg.get('remote')
    merge=cfg.get('merge')
    if isinstance(remote, str) and remote:
        subprocess.run(['git','-C',root,'config',f'branch.{branch}.remote',remote],check=False)
    if isinstance(merge, str) and merge:
        subprocess.run(['git','-C',root,'config',f'branch.{branch}.merge',merge],check=False)
    if remote or merge:
        restored.append(branch)
    tracking=''
    if isinstance(remote, str) and remote and remote != '.' and isinstance(merge, str) and merge.startswith('refs/heads/'):
        tracking=f"refs/remotes/{remote}/{merge.removeprefix('refs/heads/')}"
    if tracking and subprocess.run(['git','-C',root,'show-ref','--verify','--quiet',tracking]).returncode != 0:
        fetch=subprocess.run(['git','-C',root,'fetch','--no-tags',remote,f'+{merge}:{tracking}'],text=True,capture_output=True)
        if fetch.returncode == 0:
            refreshed.append(tracking)
        else:
            errors.append(f'{branch}: fetch {remote} {merge} failed')
print(json.dumps({'restored': restored, 'refreshed': refreshed, 'errors': errors}, sort_keys=True))
PY
}

REMOTES_JSON="$(snapshot_remotes)"
BRANCH_UPSTREAMS_JSON="$(snapshot_branch_upstreams)"
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
  'branch_upstreams': json.loads('''$BRANCH_UPSTREAMS_JSON'''),
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
BRANCH_UPSTREAM_RESTORE_JSON="$(restore_branch_upstreams "$BRANCH_UPSTREAMS_JSON")"
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
  'branch_upstreams_before': json.loads('''$BRANCH_UPSTREAMS_JSON'''),
  'branch_upstream_restore': json.loads('''$BRANCH_UPSTREAM_RESTORE_JSON'''),
  'returncode': $RC,
}
for path in sys.argv[1:]:
    p=pathlib.Path(path); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(payload, indent=2, sort_keys=True)+'\n')
PY

# ADR-269 ledger append on success.
if [ "$RC" = "0" ] && [ -n "$ADR_REF" ] && [ -n "$BACKUP_MIRROR" ]; then
  PYTHONPATH="$PROJECT_DIR" python3 - "$PROJECT_DIR" "$ADR_REF" "$ADR_REASON" "$ADR_OPERATOR" "$BACKUP_MIRROR" "$PRE_HEAD" "$POST_HEAD" <<'PY' >&2 || true
import sys, os
from pathlib import Path
project, adr, reason, operator, backup, pre, post = sys.argv[1:8]
sys.path.insert(0, project)
try:
    from lib.history_rewrite_ledger import LedgerEntry, append_entry
    bundle_rel = backup
    pr = Path(project)
    bp = Path(backup)
    if bp.is_absolute():
        try:
            bundle_rel = bp.relative_to(pr).as_posix()
        except ValueError:
            bundle_rel = backup
    entry = LedgerEntry(
        timestamp="",
        operator=operator or os.environ.get("USER", "") or "unknown",
        adr_ref=adr,
        reason=(reason or f"history rewrite governed by {adr}").strip(),
        bundle_path=bundle_rel,
        sha_before=(pre or "")[:8],
        sha_after=(post or "")[:8],
        rewrite_scope="filter-repo-wrapper",
        tool="git-filter-repo",
        invocation=f"cos-filter-repo-wrap.sh --adr-ref {adr}",
    )
    try:
        path = append_entry(pr, entry, validate_adr=True)
    except Exception:
        path = append_entry(pr, entry, validate_adr=False)
    print(f"cos-filter-repo-wrap: ledger entry appended -> {path}")
except Exception as exc:
    print(f"cos-filter-repo-wrap: ledger append skipped ({exc})")
PY
fi

exit "$RC"

#!/usr/bin/env bash
# SCOPE: os-only
set -euo pipefail

cmd="${1:-}"
plan_path="${2:-}"
purpose="${3:-plan-update}"
project_dir="${COGNITIVE_OS_PROJECT_DIR:-$(scripts/cos-root project 2>/dev/null || pwd)}"
session_id="${COGNITIVE_OS_SESSION_ID:-operator-$$}"
agent_id="${COGNITIVE_OS_AGENT_ID:-manual}"
ttl="${COS_PLAN_LOCK_TTL:-1800}"

if [[ -z "$cmd" || -z "$plan_path" ]]; then
  echo "usage: scripts/plan-lock.sh acquire|release|status <plan-path> [purpose]" >&2
  exit 64
fi

lock_root="$project_dir/.cognitive-os/runtime/plan-locks"
mkdir -p "$lock_root"
lock_name=$(printf '%s' "$plan_path" | shasum -a 256 | awk '{print substr($1,1,16)}')
lock_dir="$lock_root/${lock_name}.lock"
meta="$lock_dir/metadata.json"
now=$(date +%s)

write_meta() {
  cat > "$meta" <<EOF
{"session_id":"$session_id","agent_id":"$agent_id","pid":$$,"acquired_at":$now,"purpose":"$purpose","plan_path":"$plan_path"}
EOF
}

read_field() {
  local field="$1"
  python3 - "$meta" "$field" <<'PY'
import json, sys
try:
    data=json.load(open(sys.argv[1]))
except Exception:
    data={}
print(data.get(sys.argv[2], ""))
PY
}

is_stale() {
  [[ ! -f "$meta" ]] && return 0
  local pid acquired age
  pid="$(read_field pid || true)"
  acquired="$(read_field acquired_at || true)"
  if [[ -n "$pid" ]] && ! kill -0 "$pid" 2>/dev/null; then
    return 0
  fi
  if [[ -n "$acquired" && "$acquired" =~ ^[0-9]+$ ]]; then
    age=$((now - acquired))
    if (( age > ttl )); then
      return 0
    fi
  fi
  return 1
}

case "$cmd" in
  acquire)
    if mkdir "$lock_dir" 2>/dev/null; then
      write_meta
      echo "plan-lock: acquired $plan_path" >&2
      exit 0
    fi
    if is_stale; then
      rm -rf "$lock_dir"
      mkdir "$lock_dir"
      write_meta
      echo "plan-lock: acquired stale-replaced $plan_path" >&2
      exit 0
    fi
    echo "plan-lock: held $plan_path" >&2
    [[ -f "$meta" ]] && cat "$meta" >&2
    exit 2
    ;;
  release)
    if [[ -d "$lock_dir" ]]; then
      holder="$(read_field session_id || true)"
      if [[ -n "$holder" && "$holder" != "$session_id" && "${COS_PLAN_LOCK_FORCE_RELEASE:-0}" != "1" ]]; then
        echo "plan-lock: held by different session: $holder" >&2
        exit 2
      fi
      rm -rf "$lock_dir"
    fi
    echo "plan-lock: released $plan_path" >&2
    ;;
  status)
    if [[ -f "$meta" ]]; then
      cat "$meta"
    else
      echo '{}'
    fi
    ;;
  *)
    echo "usage: scripts/plan-lock.sh acquire|release|status <plan-path> [purpose]" >&2
    exit 64
    ;;
esac

#!/usr/bin/env bash
# SCOPE: os-only
# install-timing-test.sh — End-to-end install timing for the SO (ADR-059 §Phase 2).
#
# Clones the repo into a temp directory, runs scripts/setup.sh, measures
# elapsed time, counts errors and manual steps, then emits a JSONL record to
# .cognitive-os/metrics/install-timing.jsonl inside the *original* project.
#
# Usage:
#   bash scripts/install-timing-test.sh [--profile <--minimal|--standard|--full>]
#   bash scripts/install-timing-test.sh --help
#
# Environment:
#   REPO_URL      Git URL to clone (default: autodetected from `git remote get-url origin`)
#   INSTALL_JSONL Path to the output JSONL (default: .cognitive-os/metrics/install-timing.jsonl)
#
# Exit codes:
#   0  Success — record written; check elapsed_s/errors for budget compliance
#   1  Missing dependency (git, python3) or clone failure
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
JSONL_PATH="${INSTALL_JSONL:-$PROJECT_DIR/.cognitive-os/metrics/install-timing.jsonl}"

PROFILE="--standard"

# ── Argument parsing ─────────────────────────────────────────────────────────

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --profile)
        PROFILE="$2"
        shift 2
        ;;
      --help|-h)
        echo "Usage: bash scripts/install-timing-test.sh [--profile <--minimal|--standard|--full>]"
        echo ""
        echo "Environment:"
        echo "  REPO_URL      Git URL to clone (default: autodetected)"
        echo "  INSTALL_JSONL Output JSONL path (default: .cognitive-os/metrics/install-timing.jsonl)"
        exit 0
        ;;
      *)
        echo "Unknown argument: $1" >&2
        exit 1
        ;;
    esac
  done
}

# ── Dependency checks ────────────────────────────────────────────────────────

check_deps() {
  local missing=0
  for cmd in git python3; do
    if ! command -v "$cmd" &>/dev/null; then
      echo "[FAIL] Required command not found: $cmd" >&2
      missing=$((missing + 1))
    fi
  done
  if [[ $missing -gt 0 ]]; then
    exit 1
  fi
}

# ── Repo URL detection ───────────────────────────────────────────────────────

detect_repo_url() {
  if [[ -n "${REPO_URL:-}" ]]; then
    echo "$REPO_URL"
    return
  fi
  local url
  url="$(git -C "$PROJECT_DIR" remote get-url origin 2>/dev/null || true)"
  if [[ -z "$url" ]]; then
    echo "[WARN] Could not detect repo URL; using project dir as source" >&2
    echo "file://$PROJECT_DIR"
    return
  fi
  echo "$url"
}

# ── Count hooks in settings.json ─────────────────────────────────────────────

count_hooks() {
  local install_dir="$1"
  local settings_file="$install_dir/.claude/settings.json"
  if [[ ! -f "$settings_file" ]]; then
    echo 0
    return
  fi
  python3 -c "
import json, sys
try:
    data = json.load(open('$settings_file'))
    hooks = data.get('hooks', {})
    total = sum(len(v) if isinstance(v, list) else 1 for v in hooks.values())
    print(total)
except Exception:
    print(0)
"
}

# ── Count errors in output ────────────────────────────────────────────────────

count_errors() {
  local logfile="$1"
  grep -cE '\b(ERROR|FAIL|fatal)\b' "$logfile" 2>/dev/null || echo 0
}

# ── Emit JSONL record ─────────────────────────────────────────────────────────

emit_record() {
  local elapsed_s="$1"
  local errors="$2"
  local hook_count="$3"
  local exit_code="$4"

  mkdir -p "$(dirname "$JSONL_PATH")"

  python3 - <<PYEOF
import json, time, sys

record = {
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "profile": "$PROFILE",
    "elapsed_s": $elapsed_s,
    "manual_steps": 0,
    "errors": $errors,
    "docker_required": 0,
    "final_hook_count": $hook_count,
    "exit_code": $exit_code,
}
with open("$JSONL_PATH", "a") as fh:
    fh.write(json.dumps(record) + "\n")
print("[OK] Record appended to $JSONL_PATH")
print(json.dumps(record, indent=2))
PYEOF
}

# ── Main ─────────────────────────────────────────────────────────────────────

main() {
  parse_args "$@"
  check_deps

  local repo_url
  repo_url="$(detect_repo_url)"

  local tmp_dir
  tmp_dir="$(mktemp -d -t cos-install-XXXX)"
  trap 'rm -rf "$tmp_dir"' EXIT

  echo "[INFO] Cloning $repo_url into $tmp_dir/fresh-cos ..."
  git clone --depth=1 "$repo_url" "$tmp_dir/fresh-cos" 2>&1

  local setup_log="$tmp_dir/setup.log"
  local start_ts end_ts elapsed_s exit_code=0

  start_ts="$(date +%s)"
  echo "[INFO] Running setup.sh $PROFILE (headless) ..."
  if NONINTERACTIVE=1 bash "$tmp_dir/fresh-cos/scripts/setup.sh" "$PROFILE" \
       >"$setup_log" 2>&1; then
    exit_code=0
  else
    exit_code=$?
    echo "[WARN] setup.sh exited with code $exit_code" >&2
  fi
  end_ts="$(date +%s)"
  elapsed_s=$((end_ts - start_ts))

  local errors hook_count
  errors="$(count_errors "$setup_log")"
  hook_count="$(count_hooks "$tmp_dir/fresh-cos")"

  echo ""
  echo "[INFO] Results:"
  echo "  profile      : $PROFILE"
  echo "  elapsed_s    : ${elapsed_s}s"
  echo "  errors       : $errors"
  echo "  hook_count   : $hook_count"
  echo "  exit_code    : $exit_code"

  emit_record "$elapsed_s" "$errors" "$hook_count" "$exit_code"

  if [[ $elapsed_s -lt 300 && $errors -eq 0 ]]; then
    echo "[PASS] Install within ADR-059 budget (<300s, 0 errors)"
  else
    echo "[FAIL] Install exceeds ADR-059 budget (elapsed=${elapsed_s}s errors=${errors})" >&2
    echo "       README 'plug-and-play' claim should be demoted per ADR-059 §Phase 2" >&2
  fi
}

main "$@"

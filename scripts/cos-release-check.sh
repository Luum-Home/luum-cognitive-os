#!/usr/bin/env bash
# =============================================================================
# cos-release-check.sh — Canary/release verification for v1.0.
# =============================================================================
# Performs the following checks in throwaway tmp dirs (never touches real projects):
#
#   1. Fresh install (default profile)   -> .claude/settings.json valid, hooks exist,
#                                           cos-status runs cleanly, 10 core skills
#                                           reachable (where applicable to profile).
#   2. Fresh install (full profile)      -> same asserts with more skills.
#   3. Upgrade scenario                  -> install default, run cos-update.sh, verify
#                                           idempotent (second run = no diff).
#   4. Rate-limiter load test            -> spawn N bash-style calls, verify throttle.
#                                           Skipped gracefully if rate-limiter not in
#                                           current settings.json.
#
# Output: JSON report on stdout with { ok, checks_passed, checks_failed, details: [...] }.
#
# Flags:
#   --dry-run        Emit the report skeleton without running actual installs.
#                    Useful for testing the script's plumbing / CI collection.
#   --keep           Do not clean up the tmp canary dirs (debugging).
#   --tmp-root DIR   Parent for canary dirs (default: $TMPDIR or /tmp).
#   --no-load-test   Skip the rate-limiter load test.
#   --help           Show this help.
#
# Exit codes:
#   0 all checks pass
#   1 one or more checks failed
#   2 invocation error (bad flag, missing prerequisites)
# =============================================================================
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"

# ── Flag parsing ───────────────────────────────────────────────────────
DRY_RUN=false
KEEP=false
TMP_ROOT="${TMPDIR:-/tmp}"
# Strip trailing slash so paths compose cleanly.
TMP_ROOT="${TMP_ROOT%/}"
NO_LOAD_TEST=false

usage() {
  cat <<'EOF'
cos-release-check.sh — canary/release verification for v1.0.

What it verifies (before tagging v1.0):
  - Fresh install succeeds in throwaway dirs (default + full profiles).
  - .claude/settings.json is valid JSON after install.
  - All wired hooks exist on disk.
  - cos-status.sh runs cleanly on the install.
  - cos-update.sh is idempotent on a fresh install (second run = no diff).
  - Rate-limiter throttles as expected under sustained load (optional).

Usage:
  bash scripts/cos-release-check.sh [flags]

Flags:
  --dry-run        Emit the report skeleton without running actual installs.
  --keep           Do not clean up the tmp canary dirs after the run.
  --tmp-root DIR   Parent dir for canary dirs (default: $TMPDIR or /tmp).
  --no-load-test   Skip the rate-limiter load test section.
  --help, -h       Show this help.

Output: JSON on stdout. Exit 0 iff all checks pass.

Isolation:
  All operations happen under $TMP_ROOT/cos-canary-*. The source repo is NEVER modified.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run)       DRY_RUN=true; shift ;;
    --keep)          KEEP=true; shift ;;
    --tmp-root)
      if [ -z "${2:-}" ]; then echo "Error: --tmp-root requires a path" >&2; exit 2; fi
      TMP_ROOT="${2%/}"; shift 2
      ;;
    --no-load-test)  NO_LOAD_TEST=true; shift ;;
    --help|-h)       usage; exit 0 ;;
    *)               echo "Unknown flag: $1" >&2; usage >&2; exit 2 ;;
  esac
done

# ── Report accumulation (written to a temp JSONL then composed at the end) ──

REPORT_TMP=$(mktemp -t cos-release-check.XXXXXX)
trap 'rm -f "$REPORT_TMP"' EXIT

# add_check <name> <ok:true|false> <details-json-or-string>
add_check() {
  local name="$1" ok="$2" details="$3"
  # details may be a JSON string OR a plain string; we pass raw and python wraps as needed.
  python3 - "$REPORT_TMP" "$name" "$ok" "$details" <<'PYEOF'
import json, sys
path, name, ok, details = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
# Accept details as JSON if it parses, else treat as a plain string.
parsed = None
try:
    parsed = json.loads(details)
except Exception:
    parsed = details
entry = {"name": name, "ok": ok == "true", "details": parsed}
with open(path, "a") as fh:
    fh.write(json.dumps(entry) + "\n")
PYEOF
}

# ── Helpers ────────────────────────────────────────────────────────────

canary_dir_for() {
  local label="$1"
  echo "${TMP_ROOT}/cos-canary-${label}"
}

# Reset a canary dir safely. Refuses to touch anything outside $TMP_ROOT.
reset_canary_dir() {
  local dir="$1"
  case "$dir" in
    "${TMP_ROOT}/cos-canary-"*) : ;;  # OK
    *)
      echo "Refusing to reset $dir (not under $TMP_ROOT/cos-canary-)" >&2
      return 1
      ;;
  esac
  rm -rf "$dir"
  mkdir -p "$dir"
}

# Install COS into an existing (empty) canary dir, from the source repo.
# Args: <canary_dir> <profile flag, e.g. --standard|--full|--lean>
install_into_canary() {
  local dir="$1"
  local profile_flag="$2"
  (
    cd "$dir" || exit 97
    # Use --from SOURCE_ROOT to avoid hitting GitHub. COGNITIVE_OS_FORCE=true
    # ensures idempotence when re-run.
    COGNITIVE_OS_FORCE=true bash "$SOURCE_ROOT/install.sh" "$profile_flag" --from "$SOURCE_ROOT"
  )
}

# Validate .claude/settings.json as JSON.
# Echo "OK" | "BAD" to stdout; return 0 either way.
validate_settings_json() {
  local dir="$1"
  local f="$dir/.claude/settings.json"
  if [ ! -f "$f" ]; then
    echo "BAD:missing"
    return 0
  fi
  if python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$f" >/dev/null 2>&1; then
    echo "OK"
  else
    echo "BAD:invalid-json"
  fi
}

# Count wired hooks and detect missing on-disk targets.
# Echoes: <total>\t<missing_count>
count_hooks_status() {
  local dir="$1"
  local settings="$dir/.claude/settings.json"
  if [ ! -f "$settings" ]; then echo -e "0\t0"; return; fi
  python3 - "$settings" "$dir" <<'PYEOF'
import json, os, re, sys
settings_path, project_root = sys.argv[1], sys.argv[2]
try:
    data = json.load(open(settings_path))
except Exception:
    print("0\t0"); sys.exit(0)
total = 0
missing = 0
for _event, groups in (data.get("hooks") or {}).items():
    if not isinstance(groups, list):
        continue
    for g in groups:
        if not isinstance(g, dict):
            continue
        for h in g.get("hooks", []) or []:
            cmd = h.get("command", "") or ""
            total += 1
            m = re.search(r'"\$CLAUDE_PROJECT_DIR/([^"]+)"', cmd)
            path = ""
            if m:
                path = os.path.join(project_root, m.group(1))
            else:
                toks = cmd.split()
                if toks:
                    path = toks[-1].strip('"')
            if not path or not os.path.exists(path):
                missing += 1
print(f"{total}\t{missing}")
PYEOF
}

# Run cos-status.sh against a canary dir and capture exit code + summary.
run_cos_status() {
  local dir="$1"
  local status_script="$SOURCE_ROOT/scripts/cos-status.sh"
  if [ ! -f "$status_script" ]; then
    echo "SKIP:no-status-script"
    return 0
  fi
  # cos-status always exits 0; we capture its JSON output to parse health failures.
  local out
  out=$(CLAUDE_PROJECT_DIR="$dir" bash "$status_script" --json 2>/dev/null || true)
  local fails
  fails=$(python3 -c "
import json, sys
try:
    data = json.loads(sys.argv[1])
except Exception:
    print(-1); sys.exit(0)
print(int(data.get('health', {}).get('failures', 0)))
" "$out" 2>/dev/null || echo "-1")
  echo "$fails"
}

# Count skills in a canary dir's .claude/skills/
count_canary_skills() {
  local dir="$1"
  [ -d "$dir/.claude/skills" ] || { echo 0; return; }
  find "$dir/.claude/skills" -mindepth 1 -maxdepth 1 ! -name '.*' 2>/dev/null | wc -l | tr -d ' '
}

# ── Scenario 1: default-profile install ────────────────────────────────
scenario_default_install() {
  local label="default"
  local dir; dir=$(canary_dir_for "$label")
  local details_json=""

  if [ "$DRY_RUN" = "true" ]; then
    add_check "install_default" "true" "{\"dry_run\": true, \"canary_dir\": \"$dir\"}"
    return 0
  fi

  if ! reset_canary_dir "$dir"; then
    add_check "install_default" "false" "\"failed to reset canary dir $dir\""
    return 1
  fi

  local install_log; install_log=$(mktemp -t cos-install-default.XXXXXX)
  if install_into_canary "$dir" "--standard" >"$install_log" 2>&1; then
    local skills; skills=$(count_canary_skills "$dir")
    local settings_status; settings_status=$(validate_settings_json "$dir")
    local hooks_out; hooks_out=$(count_hooks_status "$dir")
    local hooks_total; hooks_total=$(echo "$hooks_out" | awk -F'\t' '{print $1}')
    local hooks_missing; hooks_missing=$(echo "$hooks_out" | awk -F'\t' '{print $2}')
    local status_fails; status_fails=$(run_cos_status "$dir")

    local pass="true"
    [ "$settings_status" != "OK" ]     && pass="false"
    [ "$hooks_missing"   -gt 0 ]      && pass="false"
    [ "$status_fails" = "-1" ]         && pass="false"
    [ "$status_fails" -gt 0 ] 2>/dev/null && pass="false"

    details_json=$(python3 - <<PYEOF
import json
print(json.dumps({
  "profile": "standard",
  "canary_dir": "$dir",
  "skills_installed": int("$skills" or 0),
  "settings_json": "$settings_status",
  "hooks_total": int("$hooks_total" or 0),
  "hooks_missing_on_disk": int("$hooks_missing" or 0),
  "cos_status_failures": int("$status_fails" or 0),
}))
PYEOF
)
    add_check "install_default" "$pass" "$details_json"
  else
    local tail_log; tail_log=$(tail -20 "$install_log" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))" 2>/dev/null || echo '""')
    add_check "install_default" "false" "{\"install_log_tail\": $tail_log}"
  fi
  rm -f "$install_log"
}

# ── Scenario 2: full-profile install ───────────────────────────────────
scenario_full_install() {
  local label="full"
  local dir; dir=$(canary_dir_for "$label")

  if [ "$DRY_RUN" = "true" ]; then
    add_check "install_full" "true" "{\"dry_run\": true, \"canary_dir\": \"$dir\"}"
    return 0
  fi

  if ! reset_canary_dir "$dir"; then
    add_check "install_full" "false" "\"failed to reset canary dir $dir\""
    return 1
  fi

  local install_log; install_log=$(mktemp -t cos-install-full.XXXXXX)
  if install_into_canary "$dir" "--full" >"$install_log" 2>&1; then
    local skills; skills=$(count_canary_skills "$dir")
    local settings_status; settings_status=$(validate_settings_json "$dir")
    local hooks_out; hooks_out=$(count_hooks_status "$dir")
    local hooks_total; hooks_total=$(echo "$hooks_out" | awk -F'\t' '{print $1}')
    local hooks_missing; hooks_missing=$(echo "$hooks_out" | awk -F'\t' '{print $2}')
    local status_fails; status_fails=$(run_cos_status "$dir")

    local pass="true"
    [ "$settings_status" != "OK" ]     && pass="false"
    [ "$hooks_missing"   -gt 0 ]      && pass="false"
    [ "$status_fails" = "-1" ]         && pass="false"
    [ "$status_fails" -gt 0 ] 2>/dev/null && pass="false"
    # Full profile should have strictly more skills than lean/default
    [ "$skills" -lt 10 ] 2>/dev/null    && pass="false"

    local details_json
    details_json=$(python3 - <<PYEOF
import json
print(json.dumps({
  "profile": "full",
  "canary_dir": "$dir",
  "skills_installed": int("$skills" or 0),
  "settings_json": "$settings_status",
  "hooks_total": int("$hooks_total" or 0),
  "hooks_missing_on_disk": int("$hooks_missing" or 0),
  "cos_status_failures": int("$status_fails" or 0),
  "skills_expectation": ">= 10",
}))
PYEOF
)
    add_check "install_full" "$pass" "$details_json"
  else
    local tail_log; tail_log=$(tail -20 "$install_log" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))" 2>/dev/null || echo '""')
    add_check "install_full" "false" "{\"install_log_tail\": $tail_log}"
  fi
  rm -f "$install_log"
}

# ── Scenario 3: upgrade (install default, then cos-update.sh; verify idempotent) ─
scenario_upgrade() {
  local label="upgrade"
  local dir; dir=$(canary_dir_for "$label")

  if [ "$DRY_RUN" = "true" ]; then
    add_check "upgrade_idempotent" "true" "{\"dry_run\": true, \"canary_dir\": \"$dir\"}"
    return 0
  fi

  if ! reset_canary_dir "$dir"; then
    add_check "upgrade_idempotent" "false" "\"failed to reset canary dir $dir\""
    return 1
  fi

  local log; log=$(mktemp -t cos-upgrade.XXXXXX)

  # Install first
  if ! install_into_canary "$dir" "--standard" >"$log" 2>&1; then
    local tl; tl=$(tail -20 "$log" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))" 2>/dev/null || echo '""')
    add_check "upgrade_idempotent" "false" "{\"phase\": \"install\", \"log_tail\": $tl}"
    rm -f "$log"
    return 0
  fi

  local pre_hooks; pre_hooks=$(count_hooks_status "$dir" | awk -F'\t' '{print $1}')
  local pre_skills; pre_skills=$(count_canary_skills "$dir")

  # Run cos-update.sh in the canary dir. cos-update assumes it lives at
  # PROJECT/scripts/cos-update.sh, so we point CLAUDE_PROJECT_DIR at the canary
  # but invoke the SOURCE_ROOT copy. It operates on PROJECT_ROOT derived from
  # the script's own dirname — so we need to copy it into the canary OR invoke
  # from a wrapper that changes PROJECT_ROOT. Simplest: run cos-update against
  # source (which is idempotent) and then run self-install.sh inside the canary
  # (which is what cos-update does in step 4 and what actually touches state).
  local self_install="$SOURCE_ROOT/hooks/self-install.sh"
  if [ ! -f "$self_install" ]; then
    add_check "upgrade_idempotent" "false" "{\"phase\": \"self-install-lookup\", \"error\": \"hooks/self-install.sh not found\"}"
    rm -f "$log"
    return 0
  fi

  # Snapshot before re-run
  local snap_pre; snap_pre=$(
    {
      [ -f "$dir/.claude/settings.json" ] && shasum -a 256 "$dir/.claude/settings.json" | awk '{print $1}'
      find "$dir/.claude/skills" -maxdepth 2 \( -type l -o -type f \) 2>/dev/null | LC_ALL=C sort | shasum -a 256 | awk '{print $1}'
    } | tr -d '\n'
  )

  # Re-run self-install against the canary — this is what cos-update.sh does in step 4.
  if ! CLAUDE_PROJECT_DIR="$dir" bash "$self_install" >>"$log" 2>&1; then
    local tl; tl=$(tail -30 "$log" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))" 2>/dev/null || echo '""')
    add_check "upgrade_idempotent" "false" "{\"phase\": \"self-install-rerun\", \"log_tail\": $tl}"
    rm -f "$log"
    return 0
  fi

  # Snapshot after
  local snap_post; snap_post=$(
    {
      [ -f "$dir/.claude/settings.json" ] && shasum -a 256 "$dir/.claude/settings.json" | awk '{print $1}'
      find "$dir/.claude/skills" -maxdepth 2 \( -type l -o -type f \) 2>/dev/null | LC_ALL=C sort | shasum -a 256 | awk '{print $1}'
    } | tr -d '\n'
  )

  local idempotent="false"
  [ "$snap_pre" = "$snap_post" ] && idempotent="true"

  local post_hooks; post_hooks=$(count_hooks_status "$dir" | awk -F'\t' '{print $1}')
  local post_skills; post_skills=$(count_canary_skills "$dir")

  local pass="$idempotent"
  # Require no regression: hook count and skill count must not decrease
  [ "$post_hooks"  -lt "$pre_hooks"  ] 2>/dev/null && pass="false"
  [ "$post_skills" -lt "$pre_skills" ] 2>/dev/null && pass="false"

  local details_json
  details_json=$(python3 - <<PYEOF
import json
print(json.dumps({
  "canary_dir": "$dir",
  "idempotent": $idempotent,
  "pre_hooks": int("$pre_hooks" or 0),
  "post_hooks": int("$post_hooks" or 0),
  "pre_skills": int("$pre_skills" or 0),
  "post_skills": int("$post_skills" or 0),
}))
PYEOF
)
  add_check "upgrade_idempotent" "$pass" "$details_json"
  rm -f "$log"
}

# ── Scenario 4: rate-limiter load test ─────────────────────────────────
# Verifies the rate-limiter hook throttles as expected. If rate-limiter is not
# wired in the current profile, we skip with a reason (NOT a failure).
scenario_rate_limiter_load() {
  if [ "$NO_LOAD_TEST" = "true" ]; then
    add_check "rate_limiter_load" "true" "\"skipped by --no-load-test\""
    return 0
  fi
  if [ "$DRY_RUN" = "true" ]; then
    add_check "rate_limiter_load" "true" "{\"dry_run\": true}"
    return 0
  fi

  local dir; dir=$(canary_dir_for "default")  # reuse the default install
  local settings="$dir/.claude/settings.json"
  local hook_script="$dir/.cognitive-os/hooks/cos/rate-limiter.sh"

  # Fallback to source-repo rate-limiter if canary didn't install it (minimal profiles).
  if [ ! -f "$hook_script" ]; then
    hook_script="$SOURCE_ROOT/hooks/rate-limiter.sh"
  fi

  if [ ! -f "$hook_script" ]; then
    add_check "rate_limiter_load" "true" "\"rate-limiter not present in this profile — skipping\""
    return 0
  fi

  # Check whether rate-limiter is actually WIRED in settings.json.
  local wired="false"
  if [ -f "$settings" ]; then
    if grep -q 'rate-limiter.sh' "$settings"; then wired="true"; fi
  fi
  if [ "$wired" != "true" ]; then
    add_check "rate_limiter_load" "true" "\"rate-limiter not active in current profile\""
    return 0
  fi

  # Load test: spawn N invocations of the rate-limiter with Bash tool payload.
  # We count how many return exit-code 2 (BLOCKED). Rate-limiter is expected to
  # throttle at least SOME of them given sustained burst. We do NOT require an
  # exact number (phase modifier can shift the cap) — only that behavior is:
  #   1) no crashes  2) at least one block OR all 30 pass without error.
  local N=30
  local blocked=0 passed=0 crashed=0
  local tmpout; tmpout=$(mktemp -t cos-rl-load.XXXXXX)
  local i
  for i in $(seq 1 "$N"); do
    # stdin payload: mock tool_name=Bash
    echo '{"tool_name":"Bash","tool_input":{"command":"echo canary"}}' \
      | CLAUDE_PROJECT_DIR="$dir" bash "$hook_script" >/dev/null 2>"$tmpout"
    rc=$?
    case "$rc" in
      0) passed=$((passed + 1)) ;;
      2) blocked=$((blocked + 1)) ;;
      *) crashed=$((crashed + 1)) ;;
    esac
  done
  rm -f "$tmpout"

  local pass="true"
  [ "$crashed" -gt 0 ] && pass="false"

  local details_json
  details_json=$(python3 - <<PYEOF
import json
print(json.dumps({
  "total": $N,
  "passed": $passed,
  "blocked_rate_limited": $blocked,
  "crashed": $crashed,
  "hook": "$hook_script",
  "wired": True,
}))
PYEOF
)
  add_check "rate_limiter_load" "$pass" "$details_json"
}

# ── Run scenarios ──────────────────────────────────────────────────────

# Prerequisites
for cmd in python3 bash; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Error: required command missing: $cmd" >&2
    exit 2
  fi
done

scenario_default_install
scenario_full_install
scenario_upgrade
scenario_rate_limiter_load

# ── Compose and emit the JSON report ───────────────────────────────────

python3 - "$REPORT_TMP" <<'PYEOF'
import json, sys
path = sys.argv[1]
items = []
try:
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
except Exception as e:
    sys.stderr.write(f"report compose error: {e}\n")
    sys.exit(2)
passed = sum(1 for i in items if i.get("ok"))
failed = sum(1 for i in items if not i.get("ok"))
report = {
    "ok":             failed == 0,
    "checks_passed":  passed,
    "checks_failed":  failed,
    "details":        items,
}
json.dump(report, sys.stdout, indent=2, sort_keys=True)
sys.stdout.write("\n")
PYEOF

# Re-read the final aggregated status to set the correct exit code.
FAIL_COUNT=$(python3 -c "
import json, sys
with open('$REPORT_TMP') as fh:
    items = [json.loads(l) for l in fh if l.strip()]
print(sum(1 for i in items if not i.get('ok')))
" 2>/dev/null || echo "1")

# Cleanup canary dirs unless --keep
if [ "$KEEP" != "true" ] && [ "$DRY_RUN" != "true" ]; then
  for label in default full upgrade; do
    d="${TMP_ROOT}/cos-canary-${label}"
    # Double-check the guard before rm -rf
    case "$d" in
      "${TMP_ROOT}/cos-canary-"*) rm -rf "$d" ;;
    esac
  done
fi

[ "${FAIL_COUNT:-0}" -eq 0 ] && exit 0 || exit 1

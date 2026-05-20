#!/usr/bin/env bash
# SCOPE: both
# cos-status.sh — Transparency command for Cognitive OS state
#
# Shows what is currently active:
#   - Profile (from cognitive-os.yaml)
#   - Skills exposed + installed
#   - Hooks wired (grouped by event)
#   - Rules (source + auto-injected)
#   - Packages installed
#   - Install source / last session
#   - Health checks (3 asserts)
#
# Flags: --verbose, --json, --observability, --portability, --help
#
# Example:
#   bash scripts/cos-status.sh
#   bash scripts/cos-status.sh --verbose
#   bash scripts/cos-status.sh --json

set -uo pipefail  # NOTE: no -e — we want to keep running through optional checks

# ── Locate project root ────────────────────────────────────────────────
# Uses canonical runtime precedence when available; otherwise derives from the
# script location.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}}}"
source "${SCRIPT_DIR}/_lib/settings-driver.sh"
source "${SCRIPT_DIR}/../hooks/_lib/portable.sh"

canonical_skills_dir() {
  printf '%s/.cognitive-os/skills/cos' "$PROJECT_ROOT"
}

legacy_skills_dir() {
  printf '%s/.cognitive-os/skills' "$PROJECT_ROOT"
}

driver_skills_dir() {
  printf '%s/.claude/skills' "$PROJECT_ROOT"
}

canonical_rules_dir() {
  printf '%s/.cognitive-os/rules/cos' "$PROJECT_ROOT"
}

driver_rules_dir() {
  if [ -d "$PROJECT_ROOT/.claude/rules/cos" ]; then
    printf '%s/.claude/rules/cos' "$PROJECT_ROOT"
  else
    printf '%s/.claude/rules' "$PROJECT_ROOT"
  fi
}

source_rules_dir() {
  if [ -d "$(canonical_rules_dir)" ]; then
    printf '%s' "$(canonical_rules_dir)"
  elif [ -d "$PROJECT_ROOT/rules" ]; then
    printf '%s/rules' "$PROJECT_ROOT"
  else
    printf '%s' "$(canonical_rules_dir)"
  fi
}

active_settings_harness() {
  cos_detect_harness "$PROJECT_ROOT"
}

active_settings_driver_label() {
  cos_settings_driver_label "$(active_settings_harness)"
}

active_settings_driver_path() {
  cos_settings_driver_path "$PROJECT_ROOT" "$(active_settings_harness)"
}

# ── Flag parsing ───────────────────────────────────────────────────────

MODE="pretty"   # pretty | json
VERBOSE=0
OBSERVABILITY=0
PORTABILITY=0

usage() {
  cat <<EOF
cos status — show what is currently active in Cognitive OS

Usage:
  bash scripts/cos-status.sh [flags]

Flags:
  --verbose    Expand each section with individual names
  --json       Machine-parseable JSON output (implies no color)
  --observability
               Show ADR-304 telemetry SLO status only
  --portability
               Show SCOPE proof coverage plus project projection/runtime scope status
  --help       Show this help and exit

Reads:
  - cognitive-os.yaml         (profile)
  - current settings driver   (wired hooks, harness-aware)
  - .claude/skills/           (driver-exposed skills)
  - .cognitive-os/skills/cos/ (canonical installed skills, when present)
  - .cognitive-os/rules/cos/  (canonical rules, when present)
  - rules/                    (repo rule source fallback)
  - packages/                 (installed packages)

Exit code: 0 always (health issues are reported in the output, not via exit code).

When to run:
  - At session start, to confirm COS is wired correctly
  - After install/update, to verify the new state
  - When something feels broken, to compare expected vs actual
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --verbose|-v) VERBOSE=1 ;;
    --json)       MODE="json" ;;
    --observability) OBSERVABILITY=1 ;;
    --portability) PORTABILITY=1 ;;
    --help|-h)    usage; exit 0 ;;
    *) echo "Unknown flag: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done


# ── Observability-only surface (ADR-304) ─────────────────────────────────

emit_observability_status() {
  local mode="$1"
  PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}" python3 - "$PROJECT_ROOT" "$mode" <<'PYEOF'
import json
import sys
from pathlib import Path

import yaml

from lib.telemetry_aggregator import aggregate_streams

repo = Path(sys.argv[1])
mode = sys.argv[2]
manifest = repo / "manifests/observability-slo.yaml"
queue = repo / ".cognitive-os/tasks/control-plane-remediation.jsonl"
report = aggregate_streams(repo, manifest, enable_self_tuning=False)
snapshot = report.to_snapshot_dict()

queue_records = []
if queue.exists():
    for line in queue.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            queue_records.append(json.loads(line))
        except json.JSONDecodeError:
            pass
telemetry_queue = [r for r in queue_records if r.get("audit_id") == "telemetry-aggregator"]
subprocess_noise = [
    r for r in queue_records
    if "subprocess-timeout" in str(r.get("code", ""))
    or "subprocess-timeout" in str(r.get("audit_id", ""))
    or "subprocess-timeout" in str(r.get("message", ""))
]
snapshot["operator"] = {
    "manifest": str(manifest.relative_to(repo)),
    "remediation_queue": str(queue.relative_to(repo)),
    "queue_records": len(queue_records),
    "telemetry_queue_records": len(telemetry_queue),
    "subprocess_timeout_noise_records": len(subprocess_noise),
}

if mode == "json":
    json.dump(snapshot, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    raise SystemExit(0)

summary = snapshot["summary"]
print("COS Observability")
print("═════════════════")
print(f"Manifest: {snapshot['operator']['manifest']}")
print(f"SLOs: {summary['n_evaluations']} evaluated, {summary['n_breaches']} breach(es), {summary['n_stream_missing']} missing stream(s)")
print(f"Remediation queue: {snapshot['operator']['queue_records']} total rows, {snapshot['operator']['telemetry_queue_records']} telemetry rows, {snapshot['operator']['subprocess_timeout_noise_records']} subprocess-timeout noise rows")
print("")
print("SLO status:")
for ev in snapshot["evaluations"]:
    status = ev.get("status", "unknown").upper()
    sid = ev.get("slo_id", "?")
    if "value" in ev:
        target = f"{ev.get('comparator')} {ev.get('target')}"
        samples = ev.get("window_summary", {}).get("n_samples")
        sample_text = f", samples={samples}" if samples is not None else ""
        print(f"  - {sid}: {status} value={ev.get('value'):.3f} target {target}{sample_text}")
    else:
        reason = ev.get("window_summary", {}).get("reason", "")
        suffix = f" ({reason})" if reason else ""
        print(f"  - {sid}: {status}{suffix}")
PYEOF
}


# ── Portability-only surface ───────────────────────────────────────────────

emit_portability_status() {
  local mode="$1"
  PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}" python3 - "$PROJECT_ROOT" "$mode" <<'PYEOF'
import json
import subprocess
import sys
from pathlib import Path

repo = Path(sys.argv[1])
mode = sys.argv[2]

def run_json(command):
    result = subprocess.run(command, cwd=repo, text=True, capture_output=True, check=False)
    if result.returncode not in (0, 2):
        return {
            "error": "command_failed",
            "command": command,
            "returncode": result.returncode,
            "stdout_tail": result.stdout[-2000:],
            "stderr_tail": result.stderr[-2000:],
        }
    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        return {
            "error": "invalid_json",
            "command": command,
            "returncode": result.returncode,
            "message": str(exc),
            "stdout_tail": result.stdout[-2000:],
            "stderr_tail": result.stderr[-2000:],
        }
    payload["_exit_code"] = result.returncode
    return payload

scope_both = run_json([
    "python3",
    str(repo / "scripts" / "cos-scope-both-portability-audit"),
    "--repo-root",
    str(repo),
    "--json",
    "--no-write",
])
scope_projection = run_json([
    "python3",
    str(repo / "scripts" / "cos-scope-projection-audit"),
    "--repo-root",
    str(repo),
    "--run-install-smoke",
    "--strict",
    "--json",
    "--no-write",
])

proof_summary = scope_both.get("summary", {}) if isinstance(scope_both, dict) else {}
projection_summary = scope_projection.get("summary", {}) if isinstance(scope_projection, dict) else {}
errors = [
    item.get("error")
    for item in (scope_both, scope_projection)
    if isinstance(item, dict) and item.get("error")
]
status = "pass"
if errors or proof_summary.get("missing", 0) or projection_summary.get("block_findings", 0):
    status = "fail"

snapshot = {
    "schema_version": "cos-portability-status/v1",
    "status": status,
    "scope_both": scope_both,
    "scope_projection": scope_projection,
    "summary": {
        "both_total": projection_summary.get("both_total", proof_summary.get("total", 0)),
        "both_with_proofs": projection_summary.get("both_with_proofs", proof_summary.get("covered", 0)),
        "missing_proofs": proof_summary.get("missing", 0),
        "hot_path_missing": proof_summary.get("hot_path_missing", 0),
        "source_total": projection_summary.get("source_total", 0),
        "source_by_scope": projection_summary.get("source_by_scope", {}),
        "projection_total": projection_summary.get("projection_total", 0),
        "projection_by_scope": projection_summary.get("projection_by_scope", {}),
        "projection_block_findings": projection_summary.get("block_findings", 0),
        "install_smoke_status": scope_projection.get("install_smoke", {}).get("status") if isinstance(scope_projection, dict) else None,
    },
}

if mode == "json":
    json.dump(snapshot, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    raise SystemExit(0)

summary = snapshot["summary"]
print("COS Portability")
print("═══════════════")
print(f"Status: {snapshot['status'].upper()}")
print("")
print("SCOPE both portability:")
print(f"  covered: {proof_summary.get('covered', 0)}")
print(f"  missing: {proof_summary.get('missing', 0)}")
print(f"  hot-path missing: {proof_summary.get('hot_path_missing', 0)}")
print(f"  total: {proof_summary.get('total', 0)}")
print("")
print("By priority:")
for priority in ("hot_path", "shared_lib", "agent_lifecycle", "other"):
    item = proof_summary.get("by_priority", {}).get(priority)
    if not item:
        continue
    print(f"  {priority}: {item.get('covered', 0)}/{item.get('total', 0)} covered, {item.get('missing', 0)} missing")
print("")
print("Scope projection/runtime:")
print(f"  source primitives: {summary['source_total']}")
print(f"  source by scope: {json.dumps(summary['source_by_scope'], sort_keys=True)}")
print(f"  both proofs: {summary['both_with_proofs']}/{summary['both_total']}")
print(f"  project projection scanned: {summary['projection_total']}")
print(f"  project projection by scope: {json.dumps(summary['projection_by_scope'], sort_keys=True)}")
print(f"  projection block findings: {summary['projection_block_findings']}")
print(f"  install smoke: {summary['install_smoke_status']}")
if errors:
    print("")
    print("Errors:")
    for error in errors:
        print(f"  - {error}")
PYEOF
}

if [ "$PORTABILITY" -eq 1 ]; then
  emit_portability_status "$MODE"
  exit 0
fi

if [ "$OBSERVABILITY" -eq 1 ]; then
  emit_observability_status "$MODE"
  exit 0
fi

# ── Color helpers ──────────────────────────────────────────────────────
# Colorize only if stdout is a TTY AND not --json.

if [ -t 1 ] && [ "$MODE" != "json" ]; then
  C_BOLD=$'\033[1m'
  C_DIM=$'\033[2m'
  C_GREEN=$'\033[32m'
  C_RED=$'\033[31m'
  C_YELLOW=$'\033[33m'
  C_BLUE=$'\033[34m'
  C_RESET=$'\033[0m'
else
  C_BOLD="" C_DIM="" C_GREEN="" C_RED="" C_YELLOW="" C_BLUE="" C_RESET=""
fi

# ── Data collection ────────────────────────────────────────────────────

# Profile — read from cognitive-os.yaml (efficiency.profile)
# Minimal YAML: take the first line that starts with "  profile:" after "efficiency:".
get_profile() {
  local yaml="$PROJECT_ROOT/cognitive-os.yaml"
  if [ ! -f "$yaml" ]; then
    echo "unknown"
    return
  fi
  # awk state machine: enter efficiency block, capture profile within 10 lines.
  awk '
    /^efficiency:/ { inblock=1; next }
    inblock && /^[a-zA-Z]/ { inblock=0 }
    inblock && /^  profile:/ {
      sub(/^  profile:[[:space:]]*/, "");
      sub(/[[:space:]]*#.*$/, "");
      gsub(/["\x27]/, "");
      print; exit
    }
  ' "$yaml" | head -1
}

get_install_meta_field() {
  local field="$1"
  local meta="$PROJECT_ROOT/.cognitive-os/install-meta.json"
  [ -f "$meta" ] || return
  command -v python3 >/dev/null 2>&1 || return
  python3 - "$meta" "$field" <<'PYEOF' 2>/dev/null
import json
import sys

try:
    data = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception:
    sys.exit(0)
value = data.get(sys.argv[2], "")
if value is not None:
    print(value)
PYEOF
}

# Count skills in a directory. A skill is a subdirectory containing SKILL.md,
# or a loose subdirectory (legacy installs). We count subdirectories under the dir.
count_skills() {
  local dir="$1"
  [ -d "$dir" ] || { echo 0; return; }
  # Count entries (files or dirs) at depth 1, excluding hidden files.
  local n
  n=$(find "$dir" -mindepth 1 -maxdepth 1 ! -name ".*" 2>/dev/null | wc -l | tr -d ' ')
  echo "${n:-0}"
}

list_skills() {
  local dir="$1"
  [ -d "$dir" ] || return
  find "$dir" -mindepth 1 -maxdepth 1 ! -name ".*" 2>/dev/null \
    | xargs -n1 basename 2>/dev/null | sort
}

# Count rule files in rules/ (*.md, excluding RULES-COMPACT.md index).
count_rules() {
  local dir="${1:-$(source_rules_dir)}"
  [ -d "$dir" ] || { echo 0; return; }
  local n
  n=$(find "$dir" -maxdepth 1 -name '*.md' ! -name 'RULES-COMPACT.md' 2>/dev/null | wc -l | tr -d ' ')
  echo "${n:-0}"
}

count_packages() {
  local dir="$PROJECT_ROOT/packages"
  [ -d "$dir" ] || { echo 0; return; }
  local n
  n=$(find "$dir" -mindepth 1 -maxdepth 1 -type d ! -name ".*" 2>/dev/null | wc -l | tr -d ' ')
  echo "${n:-0}"
}

list_packages() {
  local dir="$PROJECT_ROOT/packages"
  [ -d "$dir" ] || return
  find "$dir" -mindepth 1 -maxdepth 1 -type d ! -name ".*" 2>/dev/null \
    | xargs -n1 basename 2>/dev/null | sort
}

# Parse the active settings driver for hooks. Uses python3 for JSON — always
# available on macOS and linux. If python3 missing, we fall back to a
# "unknown — jq not available" mode.
#
# Emits one line per hook: "EVENT<TAB>COMMAND<TAB>HOOK_PATH_OR_EMPTY"
parse_hooks() {
  local settings
  settings="$(active_settings_driver_path)"
  if [ ! -f "$settings" ]; then
    return
  fi
  if ! command -v python3 >/dev/null 2>&1; then
    return
  fi
  python3 - "$settings" "$PROJECT_ROOT" <<'PYEOF'
import json, sys, re, os

settings_path = sys.argv[1]
project_root = sys.argv[2]

try:
    with open(settings_path) as fh:
        data = json.load(fh)
except Exception:
    sys.exit(0)

hooks_block = data.get("hooks", {}) or {}
if not isinstance(hooks_block, dict):
    hooks_block = {}
if not hooks_block:
    hooks_block = {
        event: groups
        for event, groups in data.items()
        if isinstance(groups, list)
    }

for event, matcher_groups in hooks_block.items():
    if not isinstance(matcher_groups, list):
        continue
    for group in matcher_groups:
        if not isinstance(group, dict):
            continue
        for h in group.get("hooks", []) or []:
            cmd = h.get("command", "") or ""
            # Extract a COS-managed script path from the command.
            m = re.search(
                r'(\$PWD/hooks/[^"\s]+|hooks/[^"\s]+|\.cognitive-os/hooks/cos/[^"\s]+|\.claude/hooks/[^"\s]+|\.codex/hooks/[^"\s]+)',
                cmd,
            )
            path = ""
            if m:
                matched = m.group(1)
                if matched.startswith("$PWD/"):
                    matched = matched[len("$PWD/") :]
                path = os.path.join(project_root, matched)
            else:
                # Fallback: last whitespace-separated token
                toks = cmd.split()
                if toks:
                    path = toks[-1].strip('"')
            print(f"{event}\t{cmd}\t{path}")
PYEOF
}

# Health checks — three asserts. Each emits "OK<TAB>msg" or "FAIL<TAB>msg<TAB>hint".
run_health_checks() {
  local skills_dir
  skills_dir="$(driver_skills_dir)"
  local settings
  local settings_label
  settings="$(active_settings_driver_path)"
  settings_label="$(active_settings_driver_label)"

  # 1. Canonical skills are the source-of-truth; driver skills are fallback exposure.
  if [ -d "$(canonical_skills_dir)" ] && [ "$(count_skills "$(canonical_skills_dir)")" -gt 0 ]; then
    printf 'OK\t.cognitive-os/skills/cos/ canonical (%d entries)\n' "$(count_skills "$(canonical_skills_dir)")"
  elif [ -d "$skills_dir" ] && [ "$(count_skills "$skills_dir")" -gt 0 ]; then
    printf 'OK\t.claude/skills/ driver projection (%d entries)\n' "$(count_skills "$skills_dir")"
  else
    printf 'FAIL\t.cognitive-os/skills/cos/ is empty and driver projection has no skills\tbash hooks/self-install.sh\n'
  fi

  # 2. Active settings driver valid JSON
  if [ -f "$settings" ]; then
    if command -v python3 >/dev/null 2>&1; then
      if python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$settings" >/dev/null 2>&1; then
        printf 'OK\t%s is valid JSON\n' "$settings_label"
      else
        printf 'FAIL\t%s is not valid JSON\tfix JSON syntax or regenerate via bash hooks/self-install.sh\n' "$settings_label"
      fi
    else
      printf 'OK\t%s present (JSON not verified — python3 missing)\n' "$settings_label"
    fi
  else
    printf 'FAIL\t%s missing\tbash hooks/self-install.sh\n' "$settings_label"
  fi

  # 3. Every wired hook exists on disk
  if [ -f "$settings" ] && command -v python3 >/dev/null 2>&1; then
    local missing=0 missing_names=""
    while IFS=$'\t' read -r event cmd path; do
      [ -z "$path" ] && continue
      if [ ! -e "$path" ]; then
        missing=$((missing + 1))
        missing_names="$missing_names $(basename "$path")"
      fi
    done < <(parse_hooks)
    if [ "$missing" -eq 0 ]; then
      printf 'OK\tall wired hooks exist on disk\n'
    else
      printf "FAIL\t%d wired hook(s) missing:%s\tbash hooks/self-install.sh\n" "$missing" "$missing_names"
    fi
  else
    printf 'OK\twired-hooks check skipped (settings or python3 missing)\n'
  fi
}

# Last session end — read latest session meta.json if any.
get_last_session() {
  local sessions_dir="$PROJECT_ROOT/.cognitive-os/sessions"
  [ -d "$sessions_dir" ] || { echo ""; return; }
  # Find latest meta.json by mtime, print its parent dir name.
  local latest
  latest=$(find "$sessions_dir" -name meta.json -type f 2>/dev/null | xargs ls -t 2>/dev/null | head -1)
  [ -z "$latest" ] && { echo ""; return; }
  # Use stat to get mtime; macOS vs Linux differ.
  portable_stat_mtime "$latest" | python3 -c "
import sys, datetime, time
epoch = int(sys.stdin.read().strip())
print(datetime.datetime.fromtimestamp(epoch).strftime('%Y-%m-%d %H:%M:%S'))
"
}

# Runtime daemons — for each expected singleton (defined by the launcher
# hook being registered in settings.json), report alive/down status plus
# PID and uptime. Zero-dependency: uses kill -0 + ps for cross-platform.
#
# Emits TSV: name<TAB>status<TAB>pid<TAB>uptime_sec<TAB>reason
# status ∈ {OK, DOWN, STALE, UNREGISTERED}
get_daemons() {
  local settings
  settings="$(active_settings_driver_path)"
  local runtime_dir="$PROJECT_ROOT/.cognitive-os/runtime"

  # Known daemons: name | pidfile | cmdline_match | launcher_hook_pattern
  # Add a row per daemon we care about. Order matters for display.
  local rows=(
    "session-watchdog|session-watchdog.pid|so-session-watchdog.py|session-watchdog-launcher.sh"
    "reaper|reaper-heartbeat.pid|so-reaper|reaper-daemon-launcher.sh|reaper-heartbeat.sh"
  )

  for row in "${rows[@]}"; do
    local name pidfile match launcher_patterns
    name="${row%%|*}"; row="${row#*|}"
    pidfile="${row%%|*}"; row="${row#*|}"
    match="${row%%|*}"; row="${row#*|}"
    launcher_patterns="$row"

    # Is the launcher registered? If not, daemon is intentionally off.
    local registered=0
    if [ -f "$settings" ]; then
      local IFS='|'
      for pat in $launcher_patterns; do
        if grep -q "$pat" "$settings" 2>/dev/null; then
          registered=1
          break
        fi
      done
      unset IFS
    fi
    if [ "$registered" -eq 0 ]; then
      printf '%s\tUNREGISTERED\t-\t-\tlauncher not in current settings driver\n' "$name"
      continue
    fi

    local pf="$runtime_dir/$pidfile"
    if [ ! -f "$pf" ]; then
      printf '%s\tDOWN\t-\t-\tno pidfile at %s\n' "$name" "$pf"
      continue
    fi

    local pid
    pid=$(tr -d '[:space:]' < "$pf" 2>/dev/null)
    if [ -z "$pid" ] || ! kill -0 "$pid" 2>/dev/null; then
      printf '%s\tSTALE\t%s\t-\tpidfile references dead PID\n' "$name" "${pid:-?}"
      continue
    fi

    # PID alive — verify cmdline (defends against PID reuse)
    local cmd
    cmd=$(ps -p "$pid" -o command= 2>/dev/null || true)
    if ! echo "$cmd" | grep -q "$match"; then
      printf '%s\tSTALE\t%s\t-\tPID alive but not %s\n' "$name" "$pid" "$match"
      continue
    fi

    # Uptime = now - pidfile mtime (approximation; process start time
    # extraction is platform-specific, pidfile mtime is close enough).
    local now pfile_mtime uptime
    now=$(date +%s)
    pfile_mtime=$(portable_stat_mtime "$pf" 2>/dev/null || echo "$now")
    uptime=$((now - pfile_mtime))
    printf '%s\tOK\t%s\t%s\talive\n' "$name" "$pid" "$uptime"
  done
}

# Install source — currently we derive "self-hosted" (repo root matches
# package root). Future: read from a state file written by install.sh.
get_install_source() {
  local marker="$PROJECT_ROOT/.cognitive-os/install-source"
  if [ -f "$marker" ]; then
    head -1 "$marker"
  else
    # Self-hosted if install.sh lives at the root
    if [ -f "$PROJECT_ROOT/install.sh" ] || [ -f "$PROJECT_ROOT/hooks/self-install.sh" ]; then
      echo "$PROJECT_ROOT (self-hosted)"
    else
      echo "unknown"
    fi
  fi
}

# ── Rendering ──────────────────────────────────────────────────────────

PROFILE="$(get_profile)"
[ -z "$PROFILE" ] && PROFILE="unknown"
if [ "$PROFILE" = "unknown" ]; then
  META_MODE="$(get_install_meta_field mode)"
  [ -n "$META_MODE" ] && PROFILE="$META_MODE"
fi
ACTIVE_DISTRIBUTION="$(get_install_meta_field active_distribution)"
[ -z "$ACTIVE_DISTRIBUTION" ] && {
  if [ "$PROFILE" = "full" ]; then
    ACTIVE_DISTRIBUTION="full"
  elif [ "$PROFILE" = "default" ]; then
    ACTIVE_DISTRIBUTION="core"
  else
    ACTIVE_DISTRIBUTION="unknown"
  fi
}

DAEMONS_TSV="$(get_daemons)"
SKILLS_DRIVER_PATH="$(driver_skills_dir)"
SKILLS_DRIVER=$(count_skills "$SKILLS_DRIVER_PATH")
SKILLS_KERNEL_COS=$(count_skills "$(canonical_skills_dir)")
SKILLS_KERNEL_ROOT=$(count_skills "$(legacy_skills_dir)")
# Prefer the canonical kernel path if populated, else the flat install path
if [ "$SKILLS_KERNEL_COS" -gt 0 ]; then
  SKILLS_KERNEL=$SKILLS_KERNEL_COS
  SKILLS_KERNEL_PATH=".cognitive-os/skills/cos/"
else
  SKILLS_KERNEL=$SKILLS_KERNEL_ROOT
  SKILLS_KERNEL_PATH=".cognitive-os/skills/"
fi

RULES_SOURCE_PATH="$(source_rules_dir)"
RULES_DRIVER_PATH="$(driver_rules_dir)"
RULES_COUNT=$(count_rules "$RULES_SOURCE_PATH")
RULES_DRIVER_COUNT=$(count_rules "$RULES_DRIVER_PATH")
PACKAGES_COUNT=$(count_packages)
INSTALL_SOURCE="$(get_install_source)"
LAST_SESSION="$(get_last_session)"
HOOKS_DRIVER_PATH="$(active_settings_driver_label)"

# Collect hook events into associative array (via temp file — macOS bash 3 has
# no associative arrays on older systems, but we use bash 4 features below
# conditionally).
HOOK_TSV="$(parse_hooks || true)"

# Compute event -> count table (portable: use awk).
render_hook_table() {
  local tsv="$1"
  if [ -z "$tsv" ]; then return; fi
  printf '%s\n' "$tsv" | awk -F'\t' '{print $1}' | sort | uniq -c \
    | awk '{printf "%s\t%s\n", $2, $1}'
}

HOOK_EVENTS_TSV="$(render_hook_table "$HOOK_TSV")"
TOTAL_HOOKS=$(printf '%s' "$HOOK_TSV" | awk 'NF>0' | wc -l | tr -d ' ')
[ -z "$TOTAL_HOOKS" ] && TOTAL_HOOKS=0

HEALTH_TSV="$(run_health_checks)"
HEALTH_FAIL_COUNT=$(printf '%s' "$HEALTH_TSV" | awk -F'\t' '$1=="FAIL"' | awk 'NF>0' | wc -l | tr -d ' ')
[ -z "$HEALTH_FAIL_COUNT" ] && HEALTH_FAIL_COUNT=0

# ── Primitive distribution counts (ADR-124/126/127) ────────────────────
# Per-distribution active primitive counts surfaced from the lifecycle
# manifest via active_primitive_index.py. Fail-soft: empty object if the
# index cannot be built (e.g., manifest missing).
# active_primitive_index.py returns rc=1 when surface exceeds DX thresholds,
# which trips pipefail. Wrap the producer in a subshell that swallows rc so the
# downstream parser always sees the data on stdin.
PRIMITIVES_JSON=$( { python3 "$PROJECT_ROOT/scripts/active_primitive_index.py" --json --project-dir "$PROJECT_ROOT" 2>/dev/null || true; } \
  | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin).get("summary", {}) or {}
except Exception:
    d = {}
out = {
    "counts_by_tier": d.get("counts_by_tier", {}),
    "active_counts_by_tier": d.get("active_counts_by_tier", {}),
    "default_visible_counts_by_tier": d.get("default_visible_counts_by_tier", {}),
    "active_surface_count": d.get("active_surface_count", 0),
    "default_visible_count": d.get("default_visible_count", 0),
    "status": d.get("status", "unknown"),
}
print(json.dumps(out))
' 2>/dev/null )
[ -z "$PRIMITIVES_JSON" ] && PRIMITIVES_JSON='{}'

# ── Governance ROI (friction-vs-catch) ─────────────────────────────────
# Fail-soft dashboard slice: cos status must remain usable even when metrics,
# PyYAML, or the ROI module are unavailable in a consumer project.
GOVERNANCE_ROI_JSON=$(PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}" python3 - "$PROJECT_ROOT" <<'PYEOF_GOV' 2>/dev/null
import json
import sys
from pathlib import Path

try:
    from scripts.cos_governance_roi import build_report

    report = build_report(Path(sys.argv[1]), 24)
    out = {
        "roi": report.get("roi", {}),
        "friction_vs_catch": report.get("friction_vs_catch", {}),
        "catch_ledger": report.get("catch_ledger", {}),
        "phase_policy": report.get("phase_policy", {}),
        "recommendations": (report.get("recommendations") or [])[:5],
    }
except Exception as exc:
    out = {"error": str(exc)}

print(json.dumps(out))
PYEOF_GOV
)
[ -z "$GOVERNANCE_ROI_JSON" ] && GOVERNANCE_ROI_JSON='{}'

# ── JSON output ────────────────────────────────────────────────────────

emit_json() {
  PRIMITIVES_JSON="$PRIMITIVES_JSON" GOVERNANCE_ROI_JSON="$GOVERNANCE_ROI_JSON" python3 - <<PYEOF
import json, sys, os

profile = "$PROFILE"
active_distribution = "$ACTIVE_DISTRIBUTION"
skills_driver = int("$SKILLS_DRIVER")
skills_driver_path = "$SKILLS_DRIVER_PATH"
skills_kernel = int("$SKILLS_KERNEL")
skills_kernel_path = "$SKILLS_KERNEL_PATH"
rules_count = int("$RULES_COUNT")
rules_driver_count = int("$RULES_DRIVER_COUNT")
rules_driver_path = "$RULES_DRIVER_PATH"
rules_source_path = "$RULES_SOURCE_PATH"
packages_count = int("$PACKAGES_COUNT")
install_source = """$INSTALL_SOURCE"""
last_session = """$LAST_SESSION"""
total_hooks = int("$TOTAL_HOOKS" or 0)

primitives_raw = os.environ.get("PRIMITIVES_JSON", "{}")
try:
    primitives = json.loads(primitives_raw) if primitives_raw.strip() else {}
except json.JSONDecodeError:
    primitives = {}

governance_raw = os.environ.get("GOVERNANCE_ROI_JSON", "{}")
try:
    governance_roi = json.loads(governance_raw) if governance_raw.strip() else {}
except json.JSONDecodeError:
    governance_roi = {}

# Parse hook tsv
hook_tsv = """$HOOK_TSV"""
hooks_by_event = {}
hook_list = []
for line in hook_tsv.splitlines():
    if not line.strip():
        continue
    parts = line.split("\t")
    if len(parts) < 3:
        continue
    event, cmd, path = parts[0], parts[1], parts[2]
    hooks_by_event.setdefault(event, 0)
    hooks_by_event[event] += 1
    hook_list.append({"event": event, "path": path, "exists": bool(path) and os.path.exists(path)})

# Parse health tsv
health_tsv = """$HEALTH_TSV"""
health = []
for line in health_tsv.splitlines():
    if not line.strip():
        continue
    parts = line.split("\t")
    status = parts[0]
    msg = parts[1] if len(parts) > 1 else ""
    hint = parts[2] if len(parts) > 2 else ""
    health.append({"status": status, "message": msg, "hint": hint})

out = {
    "profile": profile,
    "active_distribution": active_distribution,
    "skills": {
        "driver_exposed": skills_driver,
        "driver_path": skills_driver_path,
        "kernel_installed": skills_kernel,
        "kernel_path": skills_kernel_path,
    },
    "hooks": {
        "driver_path": "$HOOKS_DRIVER_PATH",
        "total": total_hooks,
        "by_event": hooks_by_event,
    },
    "rules": {
        "driver_exposed": rules_driver_count,
        "driver_path": rules_driver_path,
        "source_count": rules_count,
        "source_path": rules_source_path,
    },
    "packages": {"count": packages_count},
    "primitives": primitives,
    "governance_roi": governance_roi,
    "install": {"source": install_source},
    "session": {"last_end": last_session},
    "health": {
        "checks": health,
        "failures": sum(1 for h in health if h["status"] == "FAIL"),
    },
}
json.dump(out, sys.stdout, indent=2, sort_keys=True)
sys.stdout.write("\n")
PYEOF
}

# ── Pretty output ──────────────────────────────────────────────────────

pretty_print() {
  printf '%sCOS Status%s\n' "${C_BOLD}" "${C_RESET}"
  printf '%s══════════%s\n\n' "${C_DIM}" "${C_RESET}"

  printf '%-16s %s %s(cognitive-os.yaml)%s\n' "Profile:" "${C_BOLD}${PROFILE}${C_RESET}" "${C_DIM}" "${C_RESET}"
  printf '%-16s %s %s(install boundary)%s\n' "Distribution:" "${C_BOLD}${ACTIVE_DISTRIBUTION}${C_RESET}" "${C_DIM}" "${C_RESET}"

  # Skills section
  local skills_line
  if [ "$SKILLS_DRIVER" -gt 0 ]; then
    skills_line="${C_GREEN}OK${C_RESET}"
  else
    skills_line="${C_RED}EMPTY${C_RESET}"
  fi
  printf '%-16s %d exposed -> %s/  %s\n' "Skills:" "$SKILLS_DRIVER" "${SKILLS_DRIVER_PATH#$PROJECT_ROOT/}" "$skills_line"
  printf '%-16s %d installed -> %s\n' "" "$SKILLS_KERNEL" "$SKILLS_KERNEL_PATH"
  if [ "$VERBOSE" -eq 1 ] && [ "$SKILLS_DRIVER" -gt 0 ]; then
    list_skills "$SKILLS_DRIVER_PATH" | head -20 | awk '{printf "                   - %s\n", $0}'
    if [ "$SKILLS_DRIVER" -gt 20 ]; then
      printf '                   ... (%d more, use --json for full list)\n' "$((SKILLS_DRIVER - 20))"
    fi
  fi

  # Primitives section (ADR-124/126/127 — per-distribution active surface)
  if [ -n "$PRIMITIVES_JSON" ] && [ "$PRIMITIVES_JSON" != "{}" ]; then
    PRIMITIVES_JSON="$PRIMITIVES_JSON" \
    COS_PRIM_VERBOSE="$VERBOSE" \
    COS_PRIM_C_GREEN="$C_GREEN" COS_PRIM_C_YELLOW="$C_YELLOW" COS_PRIM_C_RED="$C_RED" COS_PRIM_C_DIM="$C_DIM" COS_PRIM_C_RESET="$C_RESET" \
    python3 - <<'PYEOF_PRIM'
import json, os
try:
    p = json.loads(os.environ.get("PRIMITIVES_JSON", "{}"))
except Exception:
    p = {}
active = p.get("active_counts_by_tier") or {}
total = p.get("counts_by_tier") or {}
status = p.get("status", "unknown")
if active or total:
    cmap = {"pass": os.environ.get("COS_PRIM_C_GREEN",""),
            "warn": os.environ.get("COS_PRIM_C_YELLOW",""),
            "fail": os.environ.get("COS_PRIM_C_RED","")}
    color_status = cmap.get(status, os.environ.get("COS_PRIM_C_DIM",""))
    reset = os.environ.get("COS_PRIM_C_RESET","")
    print(f"Primitives:      core={active.get('core',0)}/{total.get('core',0)} team={active.get('team',0)}/{total.get('team',0)} maintainer={active.get('maintainer',0)}/{total.get('maintainer',0)} lab={active.get('lab',0)}/{total.get('lab',0)}  {color_status}{status}{reset}")
    if os.environ.get("COS_PRIM_VERBOSE") == "1":
        print(f"                 active_surface={p.get('active_surface_count',0)} default_visible={p.get('default_visible_count',0)}")
PYEOF_PRIM
  fi

  # Governance ROI section: exposes whether guard friction is paying for real
  # confirmed catches, and which phase policy should shape blocking posture.
  if [ -n "$GOVERNANCE_ROI_JSON" ] && [ "$GOVERNANCE_ROI_JSON" != "{}" ]; then
    GOVERNANCE_ROI_JSON="$GOVERNANCE_ROI_JSON" \
    COS_GOV_C_GREEN="$C_GREEN" COS_GOV_C_YELLOW="$C_YELLOW" COS_GOV_C_RED="$C_RED" COS_GOV_C_DIM="$C_DIM" COS_GOV_C_RESET="$C_RESET" \
    python3 - <<'PYEOF_GOV_STATUS'
import json
import os

try:
    g = json.loads(os.environ.get("GOVERNANCE_ROI_JSON", "{}"))
except Exception:
    g = {}

if g and not g.get("error"):
    roi = g.get("roi") or {}
    fvc = g.get("friction_vs_catch") or {}
    catches = g.get("catch_ledger") or {}
    phase = g.get("phase_policy") or {}
    ratio = f"{fvc.get('ratio')}x" if fvc.get("ratio") is not None else "unknown"
    status = str(fvc.get("status") or roi.get("status") or "unknown")
    color_by_status = {
        "paying": os.environ.get("COS_GOV_C_GREEN", ""),
        "watch": os.environ.get("COS_GOV_C_YELLOW", ""),
        "cut": os.environ.get("COS_GOV_C_RED", ""),
        "unknown": os.environ.get("COS_GOV_C_DIM", ""),
    }
    color = color_by_status.get(status, "")
    reset = os.environ.get("COS_GOV_C_RESET", "")
    net = roi.get("net_minutes_estimate", "n/a")
    phase_label = phase.get("phase", "unknown")
    strictness = phase.get("strictness", "unknown")
    confirmed = catches.get("confirmed_valid_blocks", 0)
    false_pos = catches.get("false_positive_overrides", 0)
    print(f"Governance ROI: net={net}m ratio={ratio} {color}{status}{reset} catches={confirmed} false+={false_pos} phase={phase_label}/{strictness}")
elif g.get("error"):
    dim = os.environ.get("COS_GOV_C_DIM", "")
    reset = os.environ.get("COS_GOV_C_RESET", "")
    print(f"Governance ROI: {dim}unavailable ({g.get('error')}){reset}")
PYEOF_GOV_STATUS
  fi

  # Hooks section
  printf '%-16s %d wired -> %s\n' "Hooks:" "$TOTAL_HOOKS" "$HOOKS_DRIVER_PATH"
  if [ -n "$HOOK_EVENTS_TSV" ]; then
    # Preferred event order
    local preferred="SessionStart UserPromptSubmit SubagentStart PreCompact PreToolUse PostToolUse Stop TeammateIdle TaskCreated TaskCompleted"
    # Emit in preferred order first, then any leftover events
    local emitted=""
    for ev in $preferred; do
      local cnt
      cnt=$(printf '%s\n' "$HOOK_EVENTS_TSV" | awk -F'\t' -v e="$ev" '$1==e {print $2}')
      if [ -n "$cnt" ]; then
        printf '  %-14s %s\n' "${ev}:" "$cnt"
        emitted="$emitted $ev"
      fi
    done
    # Leftovers
    printf '%s\n' "$HOOK_EVENTS_TSV" | while IFS=$'\t' read -r ev cnt; do
      [ -z "$ev" ] && continue
      case " $emitted " in *" $ev "*) continue ;; esac
      printf '  %-14s %s\n' "${ev}:" "$cnt"
    done
  fi

  # Daemons section (runtime singletons)
  if [ -n "$DAEMONS_TSV" ]; then
    local daemon_count daemon_ok daemon_bad
    daemon_count=$(printf '%s\n' "$DAEMONS_TSV" | grep -c . || echo 0)
    daemon_ok=$(printf '%s\n' "$DAEMONS_TSV" | awk -F'\t' '$2=="OK"' | wc -l | tr -d ' ')
    daemon_bad=$(printf '%s\n' "$DAEMONS_TSV" | awk -F'\t' '$2=="DOWN" || $2=="STALE"' | wc -l | tr -d ' ')
    local line_color
    if [ "$daemon_bad" -eq 0 ]; then
      line_color="${C_GREEN}${daemon_ok}/${daemon_count} alive${C_RESET}"
    else
      line_color="${C_RED}${daemon_bad} down${C_RESET} / ${daemon_ok} alive"
    fi
    printf '%-16s %s\n' "Daemons:" "$line_color"
    printf '%s\n' "$DAEMONS_TSV" | while IFS=$'\t' read -r name status pid uptime reason; do
      [ -z "$name" ] && continue
      local status_color
      case "$status" in
        OK)           status_color="${C_GREEN}alive${C_RESET}" ;;
        DOWN)         status_color="${C_RED}down${C_RESET}" ;;
        STALE)        status_color="${C_RED}stale${C_RESET}" ;;
        UNREGISTERED) status_color="${C_DIM}off${C_RESET}" ;;
        *)            status_color="$status" ;;
      esac
      if [ "$status" = "OK" ]; then
        printf '  %-14s %s  %spid=%s uptime=%ds%s\n' "${name}:" "$status_color" "${C_DIM}" "$pid" "$uptime" "${C_RESET}"
      elif [ "$VERBOSE" -eq 1 ] || [ "$status" = "DOWN" ] || [ "$status" = "STALE" ]; then
        printf '  %-14s %s  %s%s%s\n' "${name}:" "$status_color" "${C_DIM}" "$reason" "${C_RESET}"
      fi
    done
  fi

  # Rules section
  printf '%-16s %d source -> %s/\n' "Rules:" "$RULES_COUNT" "${RULES_SOURCE_PATH#$PROJECT_ROOT/}"
  printf '%-16s %d projected -> %s/\n' "" "$RULES_DRIVER_COUNT" "${RULES_DRIVER_PATH#$PROJECT_ROOT/}"
  if [ "$VERBOSE" -eq 1 ]; then
    find "$RULES_SOURCE_PATH" -maxdepth 1 -name '*.md' ! -name 'RULES-COMPACT.md' 2>/dev/null \
      | xargs -n1 basename 2>/dev/null | sort | head -15 \
      | awk '{printf "                   - %s\n", $0}'
    if [ "$RULES_COUNT" -gt 15 ]; then
      printf '                   ... (%d more)\n' "$((RULES_COUNT - 15))"
    fi
  fi

  # Packages section
  printf '%-16s %d installed\n' "Packages:" "$PACKAGES_COUNT"
  if [ "$VERBOSE" -eq 1 ] && [ "$PACKAGES_COUNT" -gt 0 ]; then
    list_packages | awk '{printf "                   - %s\n", $0}'
  fi

  # Install
  printf '%-16s %s\n' "Install:" "$INSTALL_SOURCE"

  # Last session
  if [ -n "$LAST_SESSION" ]; then
    printf '%-16s %s\n' "Last session:" "$LAST_SESSION"
  fi

  # Health
  printf '\n'
  if [ "$HEALTH_FAIL_COUNT" -eq 0 ]; then
    printf '%-16s %sall checks pass%s\n' "Health:" "${C_GREEN}OK ${C_RESET}" ""
    if [ "$VERBOSE" -eq 1 ]; then
      printf '%s\n' "$HEALTH_TSV" | while IFS=$'\t' read -r st msg _; do
        [ -z "$st" ] && continue
        printf '                   - %s\n' "$msg"
      done
    fi
  else
    printf '%-16s %s%d issue(s)%s\n' "Health:" "${C_RED}FAIL " "$HEALTH_FAIL_COUNT" "${C_RESET}"
    printf '%s\n' "$HEALTH_TSV" | while IFS=$'\t' read -r st msg hint; do
      [ "$st" = "FAIL" ] || continue
      printf '  %s- %s%s\n' "${C_RED}" "$msg" "${C_RESET}"
      [ -n "$hint" ] && printf '    %sFix: %s%s\n' "${C_DIM}" "$hint" "${C_RESET}"
    done
  fi

  printf '\n%s(run: bash scripts/cos-status.sh --verbose for details)%s\n' "${C_DIM}" "${C_RESET}"
}

# ── Entry point ────────────────────────────────────────────────────────

if [ "$MODE" = "json" ]; then
  emit_json
else
  pretty_print
fi

exit 0

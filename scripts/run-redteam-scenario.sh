#!/usr/bin/env bash
# SCOPE: both
# @manual-trigger: invoke to run a single red-team scenario YAML; part of red-team harness test suite
# run-redteam-scenario.sh — Layer 3 scenario runner for red-team-harness.
#
# Executes a single red-team scenario YAML:
#   1. Parses YAML with Python (PyYAML)
#   2. Seeds a tempdir mini-repo from initial_state (NOT a git worktree; KD2)
#   3. Substitutes ${SOURCE_DIR} / ${ARCHIVE_DIR} template vars
#   4. Evaluates detection_signals
#   5. Runs detection_command and compares exit code with expected_exit_code
#   6. Grades pass/partial/fail per grading_rubric
#   7. Writes JSON result to --out-dir/${scenario-id}.json
#
# Part of: red-team-harness Wave W5 (§3.4)
#
# Usage:
#   run-redteam-scenario.sh \
#     --scenario <id-or-path> \
#     [--scenarios-dir <path>] \
#     [--out-dir <path>] \
#     [--mode replay|live] \
#     [--mini-repo-keep] \
#     [--json]
#
# Exit codes:
#   0 — scenario passed
#   1 — scenario failed (expected fail mode not detected)
#   2 — scenario partial
#   3 — scenario errored (YAML invalid, fixture missing, etc.)
#
# Naming: kebab-case per RULES §13 (Bash)
set -uo pipefail

# ── Defaults ──────────────────────────────────────────────────────────────────
SCENARIO_ARG=""
SCENARIOS_DIR="tests/red_team/scenarios"
OUT_DIR="docs/reports/redteam"
MODE=""
MINI_REPO_KEEP=false
JSON_ONLY=false

# ── Argument parsing ──────────────────────────────────────────────────────────
while [ $# -gt 0 ]; do
  case "$1" in
    --scenario)       SCENARIO_ARG="$2"; shift 2 ;;
    --scenario=*)     SCENARIO_ARG="${1#--scenario=}"; shift ;;
    --scenarios-dir)  SCENARIOS_DIR="$2"; shift 2 ;;
    --scenarios-dir=*)SCENARIOS_DIR="${1#--scenarios-dir=}"; shift ;;
    --out-dir)        OUT_DIR="$2"; shift 2 ;;
    --out-dir=*)      OUT_DIR="${1#--out-dir=}"; shift ;;
    --mode)           MODE="$2"; shift 2 ;;
    --mode=*)         MODE="${1#--mode=}"; shift ;;
    --mini-repo-keep) MINI_REPO_KEEP=true; shift ;;
    --json)           JSON_ONLY=true; shift ;;
    --help|-h)
      sed -n '3,40p' "$0" | sed 's/^# //'
      exit 0 ;;
    *)
      echo "[run-redteam-scenario] ERROR: Unknown flag: $1" >&2
      exit 3 ;;
  esac
done

# ── Determine mode ────────────────────────────────────────────────────────────
if [ -z "$MODE" ]; then
  if [ "${COS_REDTEAM_LIVE:-}" = "1" ]; then
    MODE="live"
  else
    MODE="replay"
  fi
fi

# ── Validate required args ────────────────────────────────────────────────────
if [ -z "$SCENARIO_ARG" ]; then
  echo "[run-redteam-scenario] ERROR: --scenario is required" >&2
  exit 3
fi

# ── Resolve scenario path ─────────────────────────────────────────────────────
if [ -f "$SCENARIO_ARG" ]; then
  SCENARIO_PATH="$SCENARIO_ARG"
else
  # Try scenarios-dir/<id>.yaml
  CANDIDATE="${SCENARIOS_DIR}/${SCENARIO_ARG}.yaml"
  if [ -f "$CANDIDATE" ]; then
    SCENARIO_PATH="$CANDIDATE"
  else
    echo "[run-redteam-scenario] ERROR: Scenario not found: '$SCENARIO_ARG'" >&2
    echo "  Searched: $SCENARIO_ARG, $CANDIDATE" >&2
    exit 3
  fi
fi

# ── Python helper for YAML parsing and scenario execution ─────────────────────
PYTHON="${PYTHON:-python3}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "$(cd "$SCRIPT_DIR/.." && pwd)")"

# ── Create output directory ───────────────────────────────────────────────────
mkdir -p "$OUT_DIR"

# ── Execute via Python helper ─────────────────────────────────────────────────
START_TS=$(date +%s%N 2>/dev/null || date +%s)

RESULT_JSON=$("$PYTHON" - <<'PYEOF' "$SCENARIO_PATH" "$MODE" "$MINI_REPO_KEEP" "$REPO_ROOT"
import sys
import os
import json
import re
import shutil
import subprocess
import tempfile
import time

try:
    import yaml
except ImportError:
    print(json.dumps({
        "error": "PyYAML not installed. Run: pip install pyyaml",
        "status": "error"
    }))
    sys.exit(3)

scenario_path = sys.argv[1]
mode = sys.argv[2]
mini_repo_keep = sys.argv[3].lower() == "true"
repo_root = sys.argv[4]

# ── Load YAML ─────────────────────────────────────────────────────────────────
try:
    with open(scenario_path) as f:
        scenario = yaml.safe_load(f)
except Exception as e:
    print(json.dumps({"error": f"YAML parse error: {e}", "status": "error"}))
    sys.exit(3)

scenario_id = scenario.get("id", os.path.splitext(os.path.basename(scenario_path))[0])
version = scenario.get("version", "unknown")
scope = scenario.get("scope", "both")
expected_status = scenario.get("expected_status", None)

# ── Create tempdir mini-repo (KD2: NOT a git worktree) ───────────────────────
tmpdir = tempfile.mkdtemp(prefix=f"redteam-{scenario_id}-")

try:
    initial_state = scenario.get("initial_state", {})

    # Seed from fixture_dir if provided
    if "fixture_dir" in initial_state:
        fixture_dir = os.path.join(repo_root, initial_state["fixture_dir"])
        if not os.path.isdir(fixture_dir):
            raise FileNotFoundError(f"fixture_dir not found: {fixture_dir}")
        shutil.copytree(fixture_dir, tmpdir, dirs_exist_ok=True)

    # Create inline files
    for file_spec in initial_state.get("files", []):
        fpath = os.path.join(tmpdir, file_spec["path"])
        os.makedirs(os.path.dirname(fpath), exist_ok=True)
        content = file_spec.get("content", "")
        # Unescape \n in single-quoted YAML strings
        if isinstance(content, str):
            content = content.replace("\\n", "\n")
        with open(fpath, "w") as f:
            f.write(content)
        mode_int = file_spec.get("mode", 0o644)
        if isinstance(mode_int, str):
            mode_int = int(mode_int, 8)
        os.chmod(fpath, mode_int)

    # Apply overrides if fixture_dir used
    for override in initial_state.get("overrides", []):
        fpath = os.path.join(tmpdir, override["path"])
        os.makedirs(os.path.dirname(fpath), exist_ok=True)
        with open(fpath, "w") as f:
            f.write(override.get("content", ""))

    # Init git if requested
    if initial_state.get("git_init", False):
        git_user = initial_state.get("git_user", {})
        git_name = git_user.get("name", "Red Team")
        git_email = git_user.get("email", "redteam@example.local")
        subprocess.run(["git", "init"], cwd=tmpdir, check=True,
                       capture_output=True)
        subprocess.run(["git", "config", "user.name", git_name], cwd=tmpdir,
                       check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", git_email], cwd=tmpdir,
                       check=True, capture_output=True)
        subprocess.run(["git", "add", "-A"], cwd=tmpdir, check=True,
                       capture_output=True)
        subprocess.run(["git", "commit", "-m", "initial state"], cwd=tmpdir,
                       check=True, capture_output=True)

    # Run git_pre_state commands
    for pre_cmd in initial_state.get("git_pre_state", []):
        cmd = pre_cmd.get("run", "")
        subprocess.run(cmd, shell=True, cwd=tmpdir, check=True)

    # ── Determine template variable substitutions ─────────────────────────────
    # Extract SOURCE_DIR and ARCHIVE_DIR from detection_command or signals
    expected_fail = scenario.get("expected_fail_mode", {})
    detection_command_raw = expected_fail.get("detection_command", "")
    expected_exit_code = expected_fail.get("detection_exit_code", 0)

    # Default substitutions: derive from scenario structure
    # Look for --source-dir and --archive-dir in detection_command
    source_dir_match = re.search(r'--source-dir\s+\$\{SOURCE_DIR\}', detection_command_raw)
    archive_dir_match = re.search(r'--archive-dir\s+\$\{ARCHIVE_DIR\}', detection_command_raw)

    # Infer SOURCE_DIR / ARCHIVE_DIR from initial_state files or scenario defaults.
    # SOURCE_DIR: the non-archive, non-config top-level dir (e.g. hooks/, scripts/)
    # ARCHIVE_DIR: the deepest dir containing archive/attic files
    all_file_paths = [f["path"] for f in initial_state.get("files", [])]

    # Config/dot dirs to exclude from SOURCE_DIR candidates
    CONFIG_PREFIXES = (".claude", ".codex", ".cognitive-os", "docs", "plans")

    source_dirs = set()
    archive_dirs = set()
    for fpath in all_file_paths:
        parts = fpath.split("/")
        top = parts[0]
        is_archive = "archive" in fpath or "attic" in fpath
        is_config = top.startswith(".") or top in ("docs", "plans", "tests")
        if len(parts) >= 2:
            if is_archive:
                # Use parent dir of filename inside archive subtree
                archive_dirs.add(os.path.join(tmpdir, "/".join(parts[:-1])))
            elif not is_config:
                source_dirs.add(os.path.join(tmpdir, top))

    source_dir_val = sorted(source_dirs)[0] if source_dirs else os.path.join(tmpdir, "hooks")
    archive_dir_val = sorted(archive_dirs)[0] if archive_dirs else os.path.join(tmpdir, "docs/archive/hooks")

    def substitute_vars(text):
        """Substitute ${SOURCE_DIR} and ${ARCHIVE_DIR} template vars."""
        text = text.replace("${SOURCE_DIR}", source_dir_val)
        text = text.replace("${ARCHIVE_DIR}", archive_dir_val)
        return text

    # ── Evaluate detection_signals ────────────────────────────────────────────
    signals = expected_fail.get("detection_signals", [])
    signals_matched = 0
    signals_total = len(signals)
    signal_results = []

    for sig in signals:
        kind = sig.get("kind", "")
        expectation = sig.get("expectation", "present")
        sig_path_raw = sig.get("path", "")
        sig_path = substitute_vars(sig_path_raw)
        # Resolve relative to tmpdir if not absolute
        if not os.path.isabs(sig_path):
            sig_path = os.path.join(tmpdir, sig_path)

        matched = False
        detail = ""

        if kind == "file_exists":
            exists = os.path.exists(sig_path)
            if expectation == "present":
                matched = exists
                detail = "present" if exists else "absent"
            elif expectation == "absent":
                matched = not exists
                detail = "absent" if not exists else "present"

        elif kind == "config_reference":
            pattern = sig.get("pattern", "")
            if os.path.exists(sig_path):
                with open(sig_path) as f:
                    content = f.read()
                found = bool(re.search(pattern, content))
            else:
                found = False
            if expectation == "present":
                matched = found
                detail = "found" if found else "not found"
            elif expectation == "absent":
                matched = not found
                detail = "not found" if not found else "found"

        elif kind == "file_contains":
            pattern = sig.get("pattern", "")
            if os.path.exists(sig_path):
                with open(sig_path) as f:
                    content = f.read()
                found = bool(re.search(pattern, content, re.MULTILINE))
            else:
                found = False
            if expectation == "present":
                matched = found
                detail = "found" if found else "not found"
            elif expectation == "absent":
                matched = not found
                detail = "not found" if not found else "found"

        elif kind == "stash_present":
            pattern = sig.get("pattern", "")
            try:
                result = subprocess.run(
                    ["git", "stash", "list"],
                    cwd=tmpdir, capture_output=True, text=True
                )
                count = len([l for l in result.stdout.splitlines() if pattern in l])
                present = count >= 1
            except Exception:
                present = False
            if expectation == "present":
                matched = present
                detail = f"stash count={count}"
            elif expectation == "absent":
                matched = not present
                detail = f"stash count={count}"

        else:
            # Unknown signal kind: skip but count as unmatched
            detail = f"unknown signal kind: {kind}"
            matched = False

        if matched:
            signals_matched += 1
        signal_results.append({
            "kind": kind,
            "path": sig_path_raw,
            "expectation": expectation,
            "matched": matched,
            "detail": detail
        })

    # ── Run detection_command ─────────────────────────────────────────────────
    detection_exit = None
    detection_cmd_str = None

    if detection_command_raw and mode == "replay":
        detection_cmd_str = substitute_vars(detection_command_raw)
        # Resolve scripts/ relative to repo_root when running from tmpdir
        # Replace leading 'scripts/' with absolute path
        def resolve_cmd(cmd):
            # Replace bare script references with absolute paths from repo_root
            cmd = re.sub(r'(?<!\/)scripts/', f'{repo_root}/scripts/', cmd)
            cmd = re.sub(r'(?<!\/)hooks/', f'{tmpdir}/hooks/', cmd)
            cmd = re.sub(r'(?<!\/)plans/', f'{tmpdir}/plans/', cmd)
            return cmd

        resolved_cmd = resolve_cmd(detection_cmd_str)
        try:
            proc = subprocess.run(
                resolved_cmd,
                shell=True,
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=30
            )
            detection_exit = proc.returncode
        except subprocess.TimeoutExpired:
            detection_exit = -1
        except Exception as e:
            detection_exit = -2

    elif mode == "live":
        # Live mode: not implemented in CI (COS_REDTEAM_LIVE must be set)
        detection_exit = None

    # ── Grade result ──────────────────────────────────────────────────────────
    grading = scenario.get("grading_rubric", {})
    detection_exit_matches = (detection_exit == expected_exit_code) if detection_exit is not None else None

    # xfail handling
    if expected_status == "xfail":
        status = "xfail"
    elif signals_total == 0 and detection_exit is None:
        status = "pass"
    elif detection_exit_matches and signals_matched == signals_total:
        status = "pass"
    elif signals_matched == signals_total and not detection_exit_matches:
        status = "partial"
    elif detection_exit_matches and signals_matched < signals_total:
        status = "partial"
    else:
        status = "fail"

    # ── Build result ──────────────────────────────────────────────────────────
    result = {
        "scenario": scenario_id,
        "version": version,
        "mode": mode,
        "status": status,
        "signals_matched": signals_matched,
        "signals_total": signals_total,
        "signal_details": signal_results,
        "detection_exit": detection_exit,
        "expected_exit": expected_exit_code,
        "detection_command": detection_cmd_str,
        "detection_exit_matches": detection_exit_matches,
        "tempdir": tmpdir if mini_repo_keep else None,
        "verb": scenario.get("verbs", [None])[0],
        "severity": scenario.get("expected_severity", "UNKNOWN"),
        "scope": scope,
        "category": scenario.get("category", "unknown"),
    }

    print(json.dumps(result))
    sys.exit(0)

finally:
    if not mini_repo_keep and os.path.exists(tmpdir):
        shutil.rmtree(tmpdir, ignore_errors=True)

PYEOF
)

PY_EXIT=$?

# ── Extract duration ──────────────────────────────────────────────────────────
END_TS=$(date +%s%N 2>/dev/null || date +%s)
if [[ "$START_TS" =~ ^[0-9]{10}[0-9]+$ ]]; then
  # nanosecond precision available
  DURATION=$(python3 -c "print(round(($END_TS - $START_TS) / 1e9, 3))" 2>/dev/null || echo "0")
else
  DURATION="0"
fi

# ── Handle Python errors ──────────────────────────────────────────────────────
if [ $PY_EXIT -ne 0 ] && [ -z "$RESULT_JSON" ]; then
  RESULT_JSON="{\"scenario\":\"$SCENARIO_ARG\",\"status\":\"error\",\"error\":\"runner failed with exit $PY_EXIT\"}"
fi

# Merge duration into JSON
RESULT_JSON=$("$PYTHON" -c "
import json, sys
d = json.loads('''$RESULT_JSON''')
d['duration_seconds'] = $DURATION
print(json.dumps(d))
" 2>/dev/null || echo "$RESULT_JSON")

# ── Extract scenario id and status for output ─────────────────────────────────
SCENARIO_ID=$("$PYTHON" -c "import json,sys; d=json.loads('''$RESULT_JSON'''); print(d.get('scenario','unknown'))" 2>/dev/null || echo "$SCENARIO_ARG")
STATUS=$("$PYTHON" -c "import json,sys; d=json.loads('''$RESULT_JSON'''); print(d.get('status','error').upper())" 2>/dev/null || echo "ERROR")
VERSION=$("$PYTHON" -c "import json,sys; d=json.loads('''$RESULT_JSON'''); print(d.get('version','?'))" 2>/dev/null || echo "?")
SIGNALS_MATCHED=$("$PYTHON" -c "import json,sys; d=json.loads('''$RESULT_JSON'''); print(d.get('signals_matched','?'))" 2>/dev/null || echo "?")
SIGNALS_TOTAL=$("$PYTHON" -c "import json,sys; d=json.loads('''$RESULT_JSON'''); print(d.get('signals_total','?'))" 2>/dev/null || echo "?")
DETECT_EXIT=$("$PYTHON" -c "import json,sys; d=json.loads('''$RESULT_JSON'''); print(d.get('detection_exit','?'))" 2>/dev/null || echo "?")
EXPECTED_EXIT=$("$PYTHON" -c "import json,sys; d=json.loads('''$RESULT_JSON'''); print(d.get('expected_exit','?'))" 2>/dev/null || echo "?")

# ── Write JSON output ─────────────────────────────────────────────────────────
OUT_FILE="${OUT_DIR}/${SCENARIO_ID}.json"
mkdir -p "$OUT_DIR"
printf '%s\n' "$RESULT_JSON" > "$OUT_FILE"

# ── Human output ─────────────────────────────────────────────────────────────
if [ "$JSON_ONLY" = "false" ]; then
  printf 'SCENARIO: %s [v%s]\n' "$SCENARIO_ID" "$VERSION"
  printf 'MODE:     %s\n' "$MODE"
  printf 'STATUS:   %s\n' "$STATUS"
  printf 'SIGNALS:  %s/%s matched\n' "$SIGNALS_MATCHED" "$SIGNALS_TOTAL"
  printf 'DETECT:   exit=%s expected=%s\n' "$DETECT_EXIT" "$EXPECTED_EXIT"
  printf 'DURATION: %ss\n' "$DURATION"
  printf 'OUTPUT:   %s\n' "$OUT_FILE"
fi

# ── Map status to exit code ───────────────────────────────────────────────────
case "$STATUS" in
  PASS|XFAIL)  exit 0 ;;
  FAIL)        exit 1 ;;
  PARTIAL)     exit 2 ;;
  *)           exit 3 ;;
esac

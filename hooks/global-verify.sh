#!/usr/bin/env bash
# SCOPE: project
# @on-demand: wired conditionally by apply-efficiency-profile.sh; not a global default
# global-verify.sh — ADR-027 Phase 1 / ADR-028a §1 replacement for WS11
# PostToolUse:Agent hook. Runs targeted tests before/after agent work and
# blocks completion if the agent's claim contradicts the evidence.
#
# Inputs (via environment, provided by Claude Code hook matcher):
#   CLAUDE_PROJECT_DIR  — project root
#   AGENT_ID            — sub-agent identifier (if available)
#   AGENT_OUTPUT        — path to agent output JSONL (if available)
#
# Behavior:
#   - Before phase (called as PreToolUse Agent): resolve test targets from
#     the agent prompt / expected files, run them, store baseline in
#     .cognitive-os/runtime/verify-baseline/{agent_id}.json
#   - After phase (called as PostToolUse Agent): re-run the same tests,
#     compute diff, emit MetricEvent to verify-events.jsonl, and if an
#     agent claim "tests pass" contradicts evidence, print a BLOCKER
#     message and exit non-zero.
#
# The hook is SAFE TO SKIP when test resolution returns nothing OR when
# the environment is constrained (e.g. no pytest installed). It never
# blocks session cleanup.

set -uo pipefail

# A/B benchmark master kill-switch (vanilla baseline mode) — see
# hooks/_lib/killswitch_check.sh for the canonical check.
[ "${COS_DISABLE_ALL_GOVERNANCE:-}" = "1" ] && exit 0

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}"
cd "$PROJECT_DIR" || exit 0

AGENT_ID="${AGENT_ID:-unknown-$$}"
# VERIFY_BASELINE_DIR can be overridden (e.g. in tests) to write baseline files
# into an isolated directory rather than the live project tree.
BASELINE_DIR="${VERIFY_BASELINE_DIR:-$PROJECT_DIR/.cognitive-os/runtime/verify-baseline}"
BASELINE_FILE="$BASELINE_DIR/$AGENT_ID.json"
mkdir -p "$BASELINE_DIR" 2>/dev/null || true

MODE="${1:-auto}"  # before | after | auto

# Detect phase if not given
if [ "$MODE" = "auto" ]; then
  if [ -f "$BASELINE_FILE" ]; then MODE=after; else MODE=before; fi
fi

# Check if pytest is available; if not, skip entirely
if ! python3 -m pytest --version >/dev/null 2>&1; then
  echo "[global-verify] pytest not available — skipping" >&2
  exit 0
fi

python3 - "$MODE" "$PROJECT_DIR" "$AGENT_ID" "$BASELINE_FILE" "${VERIFY_RESOLVER_DIR:-}" <<'PYEOF'
import sys, json, os, subprocess, hashlib, shutil
from pathlib import Path

mode, project_dir, agent_id, baseline_file, verify_resolver_dir = sys.argv[1:6]
project_dir = Path(project_dir)

# VERIFY_RESOLVER_DIR (5th arg) lets tests inject a per-worker resolver without
# mutating the shared lib/targeted_test_resolver.py on disk.
if verify_resolver_dir:
    sys.path.insert(0, verify_resolver_dir)
sys.path.insert(0 if not verify_resolver_dir else 1, str(project_dir))

# Try to import the targeted test resolver (if it exists)
try:
    from lib.targeted_test_resolver import resolve_tests_for_changes
    resolver_available = True
except ImportError:
    resolve_tests_for_changes = None
    resolver_available = False

def cos_test_focused_plan(files_changed):
    """Return focused test paths from the canonical cos-test plan API, or None."""
    if not files_changed:
        return None
    args = ["focused", "--plan-json", "--no-testmon"]
    for path in files_changed:
        args.extend(["--changed-files", str(path)])

    override = os.environ.get("COS_TEST_BIN", "")
    if override:
        cmd = [override] + args
        cwd = project_dir
    elif (project_dir / "cmd" / "cos-test" / "go.mod").is_file() and shutil.which("go"):
        cmd = ["go", "run", "."] + args
        cwd = project_dir / "cmd" / "cos-test"
    else:
        return None

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=str(cwd))
    except Exception:
        return None
    if r.returncode != 0:
        return None
    try:
        plan = json.loads(r.stdout)
    except Exception:
        return None
    paths = [p for p in (plan.get("test_paths") or []) if p]
    if plan.get("mode") in {"mapped", "explicit"} and paths:
        return paths
    return None

def cos_test_available():
    """Return true when this project can use the canonical focused selector."""
    if os.environ.get("COS_TEST_BIN", ""):
        return True
    return (project_dir / "cmd" / "cos-test" / "go.mod").is_file() and shutil.which("go")

def resolve_targeted_tests(files_changed):
    """Resolve tests through cos-test focused first.

    Legacy resolver fallback is reserved for consumer projects that do not yet
    have cos-test installed. Tests/debug can opt in with
    COS_GLOBAL_VERIFY_ALLOW_LEGACY_RESOLVER=1.
    """
    test_ids = cos_test_focused_plan(files_changed)
    if test_ids:
        return test_ids
    allow_legacy = os.environ.get("COS_GLOBAL_VERIFY_ALLOW_LEGACY_RESOLVER") == "1" or not cos_test_available()
    if allow_legacy and resolver_available and files_changed:
        return resolve_tests_for_changes(files_changed)
    return []

def run_targeted_tests(files_changed):
    """Return dict with (passed, failed, test_ids_list) or None if no tests resolved."""
    test_ids = resolve_targeted_tests(files_changed)
    if not test_ids:
        return None  # no tests resolved, skip
    wrapper = project_dir / "scripts" / "pytest-with-summary.sh"
    report_root = Path(os.environ.get("COS_TEST_REPORT_DIR", project_dir / ".cognitive-os" / "reports" / "global-verify"))
    env = os.environ.copy()
    env["COS_TEST_REPORT_DIR"] = str(report_root)
    if wrapper.is_file():
        # Governance delegates execution/reporting to the canonical transport.
        # It still owns the before/after comparison, but test execution now
        # persists the same artifacts as cos-test runs.
        cmd = ["bash", str(wrapper), "--workers", "0", "--lane", "global-verify", "--", "--tb=no", "-q"] + list(test_ids)
    else:
        # Compatibility fallback for partially installed consumer projects.
        cmd = ["python3", "-m", "pytest", "--tb=no", "-q"] + list(test_ids)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120, cwd=str(project_dir), env=env)
        stdout = r.stdout + r.stderr
        import re
        import xml.etree.ElementTree as ET
        passed = 0
        failed = 0
        junit_files = sorted(report_root.glob("*/junit.xml"), key=lambda p: p.stat().st_mtime, reverse=True)
        if junit_files:
            try:
                root = ET.parse(junit_files[0]).getroot()
                suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
                total = sum(int(suite.attrib.get("tests", 0)) for suite in suites)
                failures = sum(int(suite.attrib.get("failures", 0)) for suite in suites)
                errors = sum(int(suite.attrib.get("errors", 0)) for suite in suites)
                skipped = sum(int(suite.attrib.get("skipped", 0)) for suite in suites)
                failed = failures + errors
                passed = max(0, total - failed - skipped)
            except Exception:
                pass
        if not junit_files:
            for line in stdout.splitlines():
                m = re.search(r'(\d+)\s+passed', line)
                if m:
                    passed = int(m.group(1))
                m = re.search(r'(\d+)\s+failed', line)
                if m:
                    failed = int(m.group(1))
        return {
            "test_count": len(test_ids),
            "passed": passed,
            "failed": failed,
            "returncode": r.returncode,
            "tests": list(test_ids)[:20],
            "fingerprint": hashlib.md5(("|".join(sorted(str(t) for t in test_ids))).encode()).hexdigest()[:12],
        }
    except subprocess.TimeoutExpired:
        return {"test_count": len(test_ids), "timeout": True, "tests": list(test_ids)[:20]}
    except Exception as e:
        return {"error": str(e)}

def get_changed_files():
    """Best-effort: git diff --name-only to see what the agent touched."""
    try:
        r = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True, text=True, timeout=10, cwd=str(project_dir)
        )
        files = [f for f in r.stdout.splitlines() if f.strip()]
        if not files:
            # Also check staged changes
            r2 = subprocess.run(
                ["git", "diff", "--name-only", "--cached"],
                capture_output=True, text=True, timeout=10, cwd=str(project_dir)
            )
            files = [f for f in r2.stdout.splitlines() if f.strip()]
        return files
    except Exception:
        return []

def emit_event(event_type, payload, severity="info"):
    """Emit a MetricEvent to verify-events.jsonl if lib.metric_event is available."""
    try:
        from lib.metric_event import MetricEvent, append_event
        p = project_dir / ".cognitive-os" / "metrics" / "verify-events.jsonl"
        ev = MetricEvent(source="global-verify", event_type=event_type, severity=severity, payload=payload)
        append_event(str(p), ev)
    except Exception:
        pass  # Graceful degradation: no metric emission if lib unavailable

if mode == "before":
    # VERIFY_FILES_OVERRIDE lets tests inject a synthetic changed-file list
    # so the contract tests don't depend on a dirty working tree (colon-separated).
    override = os.environ.get("VERIFY_FILES_OVERRIDE", "")
    if override:
        files = [f for f in override.split(":") if f.strip()]
    else:
        files = get_changed_files()
    baseline = run_targeted_tests(files)
    if baseline is None:
        # No tests resolved — write a skip marker so 'after' phase knows to no-op
        Path(baseline_file).write_text(
            json.dumps({"skipped": True, "reason": "no tests resolved for changed files", "files": files}),
            encoding="utf-8"
        )
        emit_event("verify.baseline.skipped", {"agent_id": agent_id, "files": files[:20]})
        print(f"[global-verify] before: skipped (0 tests resolved for {len(files)} changed files)", file=sys.stderr)
        sys.exit(0)
    Path(baseline_file).write_text(
        json.dumps({"baseline": baseline, "files": files, "mode": "before"}),
        encoding="utf-8"
    )
    emit_event("verify.baseline.captured", {"agent_id": agent_id, **{k: v for k, v in baseline.items() if k != "tests"}})
    print(
        f"[global-verify] before: {baseline.get('passed', 0)}P/{baseline.get('failed', 0)}F "
        f"across {baseline.get('test_count', 0)} tests",
        file=sys.stderr
    )
    sys.exit(0)

elif mode == "after":
    if not Path(baseline_file).is_file():
        print(f"[global-verify] after: no baseline found, skipping", file=sys.stderr)
        sys.exit(0)
    prev = json.loads(Path(baseline_file).read_text(encoding="utf-8"))
    if prev.get("skipped"):
        Path(baseline_file).unlink(missing_ok=True)
        print(f"[global-verify] after: baseline was skipped (no tests resolved), nothing to compare", file=sys.stderr)
        sys.exit(0)
    baseline = prev.get("baseline", {})
    if baseline.get("timeout") or baseline.get("error"):
        Path(baseline_file).unlink(missing_ok=True)
        print(f"[global-verify] after: baseline had error/timeout, skipping comparison", file=sys.stderr)
        sys.exit(0)
    current = run_targeted_tests(prev.get("files", []))
    Path(baseline_file).unlink(missing_ok=True)
    if current is None:
        emit_event("verify.after.no_tests", {"agent_id": agent_id}, severity="warn")
        print(f"[global-verify] after: no tests resolved (skip)", file=sys.stderr)
        sys.exit(0)
    if current.get("timeout") or current.get("error"):
        print(f"[global-verify] after: current run had error/timeout, skipping comparison", file=sys.stderr)
        sys.exit(0)
    # Compare
    before_passed = baseline.get("passed", 0)
    before_failed = baseline.get("failed", 0)
    after_passed = current.get("passed", 0)
    after_failed = current.get("failed", 0)
    delta_passed = after_passed - before_passed
    delta_failed = after_failed - before_failed
    regression = delta_failed > 0
    payload = {
        "agent_id": agent_id,
        "before": {"passed": before_passed, "failed": before_failed, "test_count": baseline.get("test_count", 0)},
        "after": {"passed": after_passed, "failed": after_failed, "test_count": current.get("test_count", 0)},
        "delta_passed": delta_passed,
        "delta_failed": delta_failed,
        "regression": regression,
    }
    emit_event("verify.after.compared", payload, severity="error" if regression else "info")
    if regression:
        print(
            f"[global-verify] BLOCKER: agent introduced {delta_failed} new test failure(s). "
            f"Before={before_passed}P/{before_failed}F  After={after_passed}P/{after_failed}F. "
            f"See .cognitive-os/metrics/verify-events.jsonl",
            file=sys.stderr
        )
        # Exit non-zero to signal the issue — Claude Code treats non-zero PostToolUse as blocker
        sys.exit(1)
    print(
        f"[global-verify] after: {before_passed}P/{before_failed}F -> {after_passed}P/{after_failed}F "
        f"(delta {delta_passed:+d}/{delta_failed:+d}) — OK",
        file=sys.stderr
    )
    sys.exit(0)

else:
    print(f"[global-verify] unknown mode: {mode}", file=sys.stderr)
    sys.exit(0)
PYEOF

"""Integration tests wrapping scripts/cos-release-check.sh.

These are the v1.0 release-gate tests. They are slow (they do fresh COS
installs into tmp directories) and gated behind ``-m canary`` so the default
CI run doesn't invoke them.

Run explicitly:
    python3 -m pytest tests/integration/test_fresh_install_canary.py -m canary -v

Notes
-----
- Every test uses ``--tmp-root`` pointing at pytest's tmp_path to guarantee
  isolation from any real ``/tmp/cos-canary-*`` directories that might exist
  from manual invocations.
- We run the shell script once per test class (via ``class``-scoped fixture)
  and assert against its JSON output. Re-running 4 full installs per test would
  be pointless.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RELEASE_CHECK = PROJECT_ROOT / "scripts" / "cos-release-check.sh"
CORE_SKILLS_CHECK = PROJECT_ROOT / "scripts" / "cos-core-skills-check.sh"


def _run_release_check(
    tmp_root: Path,
    *,
    dry_run: bool = False,
    no_load_test: bool = False,
    keep: bool = True,
    timeout: int = 600,
) -> dict:
    """Invoke cos-release-check.sh and return parsed JSON output."""
    cmd = [
        "bash",
        str(RELEASE_CHECK),
        "--tmp-root",
        str(tmp_root),
    ]
    if dry_run:
        cmd.append("--dry-run")
    if no_load_test:
        cmd.append("--no-load-test")
    if keep:
        cmd.append("--keep")

    env = os.environ.copy()
    env.setdefault("COGNITIVE_OS_PROJECT_DIR", str(PROJECT_ROOT))

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )
    # The script's exit code signals pass/fail; the JSON report is always on stdout.
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        pytest.fail(
            f"cos-release-check.sh did not emit valid JSON on stdout.\n"
            f"exit={result.returncode}\n"
            f"stdout (first 2000 chars):\n{result.stdout[:2000]}\n"
            f"stderr (first 2000 chars):\n{result.stderr[:2000]}\n"
            f"parse error: {exc}"
        )
    report["_exit_code"] = result.returncode
    report["_stderr"] = result.stderr
    return report


# ---------------------------------------------------------------------------
# Quick collection-time sanity checks — NOT marked canary so they always run.
# ---------------------------------------------------------------------------

class TestReleaseCheckPlumbing:
    """Smoke checks on the scripts themselves (fast, no install)."""

    def test_release_check_script_exists_and_executable(self):
        assert RELEASE_CHECK.is_file(), f"{RELEASE_CHECK} missing"
        assert os.access(RELEASE_CHECK, os.X_OK), f"{RELEASE_CHECK} not executable"

    def test_core_skills_check_script_exists_and_executable(self):
        assert CORE_SKILLS_CHECK.is_file(), f"{CORE_SKILLS_CHECK} missing"
        assert os.access(CORE_SKILLS_CHECK, os.X_OK), f"{CORE_SKILLS_CHECK} not executable"

    def test_release_check_help(self):
        out = subprocess.run(
            ["bash", str(RELEASE_CHECK), "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert out.returncode == 0
        # Help must mention at least one of the scope keywords
        assert any(kw in out.stdout.lower() for kw in ("canary", "release", "verify")), (
            f"help output missing canary/release/verify keyword: {out.stdout!r}"
        )

    def test_release_check_dry_run_emits_valid_json(self, tmp_path):
        report = _run_release_check(tmp_path, dry_run=True, keep=False)
        for key in ("ok", "checks_passed", "checks_failed", "details"):
            assert key in report, f"missing {key} in dry-run report"
        assert isinstance(report["details"], list)
        # Dry-run: everything should "pass" trivially.
        assert report["ok"] is True

    def test_release_check_dry_run_uses_canonical_runtime_env(self, tmp_path):
        env = os.environ.copy()
        env["COGNITIVE_OS_PROJECT_DIR"] = str(PROJECT_ROOT)
        env.pop("CODEX_PROJECT_DIR", None)
        env.pop("CLAUDE_PROJECT_DIR", None)

        result = subprocess.run(
            [
                "bash",
                str(RELEASE_CHECK),
                "--dry-run",
                "--tmp-root",
                str(tmp_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )

        assert result.returncode == 0, result.stderr
        report = json.loads(result.stdout)
        assert report["ok"] is True

    def test_release_check_uses_canonical_env_for_rate_limiter_hook(self):
        """Rate-limiter load checks should invoke hooks via the canonical project env."""
        script_text = RELEASE_CHECK.read_text()
        assert 'COGNITIVE_OS_PROJECT_DIR="$dir" bash "$hook_script"' in script_text

    def test_core_skills_check_json_parses(self):
        out = subprocess.run(
            ["bash", str(CORE_SKILLS_CHECK), "--json"],
            capture_output=True, text=True, timeout=30,
        )
        # exit code may be 0 or 1; we only require that stdout is valid JSON.
        data = json.loads(out.stdout)
        assert "skills" in data
        assert "total" in data
        assert data["total"] == 10
        names = [s["name"] for s in data["skills"]]
        expected = {
            "compose-prompt", "exhaustive-prompt", "agent-dashboard", "auto-refine",
            "verification-before-completion", "plan-feature", "session-backlog",
            "resource-governor", "paperclip-dashboard", "cos-status",
        }
        assert set(names) == expected, f"core skill names mismatch: {names!r}"


# ---------------------------------------------------------------------------
# Full canary run — marked as integration + canary, opt-in only.
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.canary
@pytest.mark.slow
class TestFreshInstallCanary:
    """End-to-end canary: runs the full release-check script and asserts each scenario."""

    @pytest.fixture(scope="class")
    def report(self, tmp_path_factory) -> dict:
        tmp_root = tmp_path_factory.mktemp("cos-canary-suite")
        # We keep=True so test-failures can be debugged; pytest cleans tmp_path after the session.
        return _run_release_check(tmp_root, keep=True, timeout=900)

    def test_overall_ok(self, report):
        assert report.get("ok") is True, (
            f"canary failed: {report.get('checks_failed')} check(s) FAIL.\n"
            f"details: {json.dumps(report.get('details'), indent=2)}"
        )

    def test_expected_scenarios_present(self, report):
        names = {d["name"] for d in report["details"]}
        expected = {"install_default", "install_full", "upgrade_idempotent", "rate_limiter_load"}
        missing = expected - names
        assert not missing, f"missing scenarios: {missing}"

    def test_default_install_ok(self, report):
        d = next(x for x in report["details"] if x["name"] == "install_default")
        assert d["ok"], f"default-install failed: {d['details']}"
        assert isinstance(d["details"], dict)
        assert d["details"].get("settings_json") == "OK"
        assert d["details"].get("hooks_missing_on_disk", -1) == 0
        assert d["details"].get("cos_status_failures", -1) == 0

    def test_full_install_ok(self, report):
        d = next(x for x in report["details"] if x["name"] == "install_full")
        assert d["ok"], f"full-install failed: {d['details']}"
        assert isinstance(d["details"], dict)
        assert d["details"].get("settings_json") == "OK"
        assert d["details"].get("hooks_missing_on_disk", -1) == 0
        # full profile expectation: >= 10 skills
        assert d["details"].get("skills_installed", -1) >= 10

    def test_upgrade_is_idempotent(self, report):
        d = next(x for x in report["details"] if x["name"] == "upgrade_idempotent")
        assert d["ok"], f"upgrade not idempotent: {d['details']}"
        assert isinstance(d["details"], dict)
        assert d["details"].get("idempotent") is True
        # No regression in hook/skill counts
        assert d["details"].get("post_hooks", 0) >= d["details"].get("pre_hooks", 0)
        assert d["details"].get("post_skills", 0) >= d["details"].get("pre_skills", 0)

    def test_rate_limiter_did_not_crash(self, report):
        d = next(x for x in report["details"] if x["name"] == "rate_limiter_load")
        # A "skipped" result is acceptable — we only fail on crash.
        assert d["ok"], f"rate-limiter load test failed: {d['details']}"
        if isinstance(d["details"], dict) and "crashed" in d["details"]:
            assert d["details"]["crashed"] == 0, (
                f"rate-limiter crashed {d['details']['crashed']} time(s) under load"
            )

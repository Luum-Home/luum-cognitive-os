"""Behavior tests for scripts/check-local-privacy.sh."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


pytestmark = [pytest.mark.unit, pytest.mark.behavior]

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / "check-local-privacy.sh"
PRE_COMMIT = PROJECT_ROOT / ".githooks" / "pre-commit"
RULE = PROJECT_ROOT / "rules" / "local-privacy-hygiene.md"
TEMPLATE = PROJECT_ROOT / "templates" / "local-privacy-patterns.example.txt"


def init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True)


# Every test but one runs the guard against a throwaway repository holding a
# handful of files, where 20s is orders of magnitude above the real cost and
# only a hang could reach it.
SANDBOX_TIMEOUT_S = 20

# The whole-repo scan is the exception, and its number is derived rather than
# guessed. These timeouts exist to catch a HANG — a wedged git subprocess, a
# lock wait, a runaway loop — not to impose a performance budget on the guard.
#
# Measured 2026-08-15 on 8526 tracked files, same command, same commit, twice:
#
#   load avg 11.77 (12 cores)  ->  1.87s user, 0.29s sys,  2.3-4.5s wall
#   load avg 180.56 (12 cores) ->  2.19s user, 0.50s sys, 32.8s wall,  8% CPU
#
# The work is a stable ~2s of CPU. The 8% CPU figure is the whole finding: at
# 32.8s wall the scan was waiting for a core, not scanning. A 2026-08-15 report
# recorded 41s wall for the same scan and read it as the scan being slow; it is
# the machine being oversubscribed by concurrent agent sessions. Making the scan
# faster cannot fix this — halving 2s of work still costs ~16s wall at 8% CPU.
#
# So the number is a hang detector, and 120s is ~60x the measured CPU cost: no
# realistic contention reaches it, and a genuine hang still fails in bounded
# time. Do not raise it again without re-measuring `user` time. If user time —
# not wall — has grown toward this number, the scan itself regressed and the
# fix belongs in the scan.
#
# The subprocess timeout is NOT the only ceiling, and raising it alone is worse
# than useless. pytest.ini sets `timeout = 30` per test, and tests/conftest.py
# caps any explicit subprocess timeout to that budget. With only the change
# above, this test stopped failing at 20s with a readable TimeoutExpired and
# started dying at 30s under pytest-timeout, whose thread-method dump aborts the
# whole session instead of one test. Hence the @pytest.mark.timeout(180) below:
# the pytest budget must sit ABOVE the subprocess timeout so the inner timer
# fires first and reports which command hung.
REPO_SCAN_TIMEOUT_S = 120
REPO_SCAN_PYTEST_BUDGET_S = 180


def run_guard(
    root: Path,
    *args: str,
    env: dict[str, str] | None = None,
    timeout: float = SANDBOX_TIMEOUT_S,
) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        [str(SCRIPT), "--root", str(root), *args],
        text=True,
        capture_output=True,
        cwd=root,
        env=merged_env,
        timeout=timeout,
        check=False,
    )


def test_staged_scan_blocks_developer_home_path(tmp_path: Path) -> None:
    init_git_repo(tmp_path)
    doc = tmp_path / "README.md"
    leaked = str(Path("/") / "Users" / "example" / "private-project")
    doc.write_text(f"leak: {leaked}\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True)

    result = run_guard(tmp_path, "--staged")

    assert result.returncode == 1
    assert "developer home path" in result.stderr
    assert leaked in result.stderr
    assert "README.md" in result.stderr


def test_staged_scan_reads_index_not_dirty_worktree(tmp_path: Path) -> None:
    init_git_repo(tmp_path)
    doc = tmp_path / "README.md"
    doc.write_text("Portable staged content uses $PROJECT_DIR.\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True)
    doc.write_text(
        f"Dirty content has {Path('/') / 'Users' / 'example' / 'private-project'}.\n",
        encoding="utf-8",
    )

    result = run_guard(tmp_path, "--staged")

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "privacy-guard-ok"


def test_private_pattern_file_blocks_ssh_key_filename(tmp_path: Path) -> None:
    init_git_repo(tmp_path)
    patterns = tmp_path / "patterns.txt"
    patterns.write_text("literal:deploy_customer_ed25519\n", encoding="utf-8")
    doc = tmp_path / "deploy.md"
    doc.write_text("Use key deploy_customer_ed25519 for the old host.\n", encoding="utf-8")
    subprocess.run(["git", "add", "deploy.md"], cwd=tmp_path, check=True)

    result = run_guard(
        tmp_path,
        "--staged",
        env={"COS_LOCAL_PRIVACY_PATTERNS_FILE": str(patterns)},
    )

    assert result.returncode == 1
    assert "private literal pattern" in result.stderr
    assert "deploy_customer_ed25519" in result.stderr


def test_allow_marker_permits_fictional_fixture(tmp_path: Path) -> None:
    doc = tmp_path / "fixture.md"
    doc.write_text(
        f"{Path('/') / 'Users' / 'example' / 'private-project'} # cos-allow-local-privacy-pattern\n",
        encoding="utf-8",
    )

    result = run_guard(tmp_path, str(doc))

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "privacy-guard-ok"


@pytest.mark.timeout(REPO_SCAN_PYTEST_BUDGET_S)
def test_repo_all_scan_passes() -> None:
    # `--all` is not the pre-commit path (.githooks/pre-commit invokes the
    # guard with --staged); the whole-repo scan runs in scripts/cos-patch-release.
    # Nobody waits on this interactively, so its cost is not a UX budget and
    # REPO_SCAN_TIMEOUT_S is a hang detector. See the constant for the numbers.
    result = run_guard(PROJECT_ROOT, "--all", timeout=REPO_SCAN_TIMEOUT_S)

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "privacy-guard-ok"


def test_pre_commit_invokes_local_privacy_guard() -> None:
    content = PRE_COMMIT.read_text(encoding="utf-8")

    assert "scripts/check-local-privacy.sh" in content
    assert "--staged" in content


def test_rule_and_template_document_private_configuration() -> None:
    rule = RULE.read_text(encoding="utf-8")
    template = TEMPLATE.read_text(encoding="utf-8")

    assert "scripts/check-local-privacy.sh --all" in rule
    assert ".cognitive-os/private/local-privacy-patterns.txt" in rule
    assert "literal:<private-project-name>" in template
    assert "regex:github[.]com/<private-org>/<private-repo>" in template


# ---------------------------------------------------------------------------
# A pattern that MATCHES usernames is not a username (2026-08-15)
# ---------------------------------------------------------------------------
# The guard used to read the quoted regex inside a documented `git grep` command
# as a leaked developer home path, so every audit report about privacy hygiene
# blocked its own commit. The first fix attempted was to edit the documents;
# that changed what was measured instead of the measurement, so the guard itself
# now distinguishes the two. These tests pin both halves: the pattern passes,
# and — the half that matters — a real path still fails.

HOME_ROOT = "/" + "Users" + "/"


def test_documented_username_pattern_is_not_a_leak(tmp_path: Path) -> None:
    """A regex describing usernames must not be reported as a username."""
    init_git_repo(tmp_path)
    (tmp_path / "REPORT.md").write_text(
        f'Command used: `git grep -nI -E \'{HOME_ROOT}[a-zA-Z0-9._-]+\'`\n',
        encoding="utf-8",
    )
    result = run_guard(tmp_path, str(tmp_path / "REPORT.md"))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "developer home path" not in (result.stdout + result.stderr)


def test_real_home_path_still_blocks_beside_a_pattern(tmp_path: Path) -> None:
    """The relaxation must not weaken the guard: a literal path still fails.

    Both lines live in the same file on purpose — the pattern must be ignored
    and the concrete path caught, in one pass.
    """
    init_git_repo(tmp_path)
    (tmp_path / "REPORT.md").write_text(
        f'config = "{HOME_ROOT}testuser/Projects/private/app.py"\n'
        f'command = `git grep -E \'{HOME_ROOT}[a-zA-Z0-9._-]+\'`\n',
        encoding="utf-8",
    )
    result = run_guard(tmp_path, str(tmp_path / "REPORT.md"))
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert "developer home path" in output
    assert "REPORT.md:1" in output, "must flag the literal path on line 1"
    assert "REPORT.md:2" not in output, "must not flag the documented pattern on line 2"

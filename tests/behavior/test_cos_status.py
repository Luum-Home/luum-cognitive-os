"""Behavior tests for scripts/cos-status.sh — the transparency command.

These tests verify that `cos status`:
  - runs without error against the real project
  - reports the current profile
  - reports numeric counts for skills/hooks/rules
  - emits valid JSON when --json is passed
  - prints a Health line in either OK or FAIL form
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path



PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
STATUS_SCRIPT = PROJECT_ROOT / "scripts" / "cos-status.sh"
WRAPPER_SCRIPT = PROJECT_ROOT / "scripts" / "cos"


def _run(
    args: list[str],
    timeout: int = 30,
    env_overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    """Run cos-status.sh with the given args and return the completed process."""
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(PROJECT_ROOT)
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        ["bash", str(STATUS_SCRIPT), *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
        cwd=str(PROJECT_ROOT),
    )


def _setup_canonical_only_project(tmp_path: Path) -> Path:
    """Create a minimal project that only contains canonical COS artifacts."""
    project = tmp_path / "canonical-only-project"
    project.mkdir()
    shutil.copy(PROJECT_ROOT / "cognitive-os.yaml", project / "cognitive-os.yaml")

    canonical_skill_dir = project / ".cognitive-os" / "skills" / "cos" / "test-skill"
    canonical_skill_dir.mkdir(parents=True)
    (canonical_skill_dir / "SKILL.md").write_text("# Test Skill Canonical\n")

    canonical_rules_dir = project / ".cognitive-os" / "rules" / "cos"
    canonical_rules_dir.mkdir(parents=True)
    (canonical_rules_dir / "test-rule.md").write_text("# Test Rule Canonical\n")

    return project


def _setup_codex_status_project(tmp_path: Path) -> Path:
    """Create a minimal Codex-first project with a harness settings driver."""
    project = _setup_canonical_only_project(tmp_path)

    hooks_dir = project / ".cognitive-os" / "hooks" / "cos"
    hooks_dir.mkdir(parents=True)
    (hooks_dir / "test-stop.sh").write_text("#!/usr/bin/env bash\nexit 0\n")

    codex_dir = project / ".codex"
    codex_dir.mkdir()
    (codex_dir / "hooks.json").write_text(
        json.dumps(
            {
                "hooks": {
                    "Stop": [
                        {
                            "matcher": "*",
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": 'bash "${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-$PWD}}/.cognitive-os/hooks/cos/test-stop.sh"',
                                }
                            ],
                        }
                    ]
                }
            }
        )
    )

    return project


def _setup_codex_pwd_hooks_project(tmp_path: Path) -> Path:
    """Create a Codex project wired through $PWD/hooks commands."""
    project = _setup_canonical_only_project(tmp_path)

    hooks_dir = project / "hooks"
    hooks_dir.mkdir()
    for hook_name in ("self-install.sh", "session-init.sh", "session-cleanup.sh"):
        hook = hooks_dir / hook_name
        hook.write_text("#!/usr/bin/env bash\nexit 0\n")
        hook.chmod(0o755)

    codex_dir = project / ".codex"
    codex_dir.mkdir()
    (codex_dir / "hooks.json").write_text(
        json.dumps(
            {
                "SessionStart": [
                    {
                        "matcher": "startup",
                        "hooks": [
                            {
                                "type": "command",
                                "command": 'export COGNITIVE_OS_HARNESS=codex; [ -x "$PWD/hooks/self-install.sh" ] && bash "$PWD/hooks/self-install.sh" || true',
                            },
                            {
                                "type": "command",
                                "command": 'export COGNITIVE_OS_HARNESS=codex; [ -x "$PWD/hooks/session-init.sh" ] && bash "$PWD/hooks/session-init.sh" || true',
                            },
                        ],
                    }
                ],
                "Stop": [
                    {
                        "matcher": "shutdown",
                        "hooks": [
                            {
                                "type": "command",
                                "command": 'export COGNITIVE_OS_HARNESS=codex; [ -x "$PWD/hooks/session-cleanup.sh" ] && bash "$PWD/hooks/session-cleanup.sh" || true',
                            }
                        ],
                    }
                ],
            }
        )
    )

    return project


def test_status_script_exists_and_is_executable():
    """The script must exist and have the executable bit set."""
    assert STATUS_SCRIPT.is_file(), f"{STATUS_SCRIPT} not found"
    assert os.access(STATUS_SCRIPT, os.X_OK), f"{STATUS_SCRIPT} is not executable"


def test_status_runs_without_error():
    """`cos status` must exit 0 and produce a recognizable report."""
    result = _run([])
    assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"
    assert "COS Status" in result.stdout
    # All major sections should be present.
    for section in ("Profile:", "Skills:", "Governance ROI:", "Hooks:", "Rules:", "Packages:", "Health:"):
        assert section in result.stdout, f"missing section {section!r} in output"


def test_status_reports_current_profile():
    """The reported profile must match cognitive-os.yaml's efficiency.profile."""
    # Read the expected profile the same way the script does (naive awk).
    yaml_text = (PROJECT_ROOT / "cognitive-os.yaml").read_text()
    in_block = False
    expected_profile = None
    for line in yaml_text.splitlines():
        if line.startswith("efficiency:"):
            in_block = True
            continue
        if in_block and line and not line.startswith((" ", "\t")):
            break
        if in_block and line.lstrip().startswith("profile:"):
            val = line.split(":", 1)[1].strip()
            val = val.split("#", 1)[0].strip().strip("'\"")
            expected_profile = val
            break
    assert expected_profile, "cognitive-os.yaml missing efficiency.profile"

    result = _run([])
    assert result.returncode == 0
    assert expected_profile in result.stdout, (
        f"expected profile {expected_profile!r} not in output"
    )


def test_status_counts_are_numeric():
    """Skill/hook/rule/package counts must be integers >= 0 in JSON mode."""
    result = _run(["--json"])
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)

    assert isinstance(data["skills"]["driver_exposed"], int)
    assert data["skills"]["driver_exposed"] >= 0

    assert isinstance(data["skills"]["kernel_installed"], int)
    assert data["skills"]["kernel_installed"] >= 0

    assert isinstance(data["hooks"]["total"], int)
    assert data["hooks"]["total"] >= 0

    assert isinstance(data["rules"]["source_count"], int)
    assert data["rules"]["source_count"] >= 0
    assert isinstance(data["rules"]["driver_exposed"], int)
    assert data["rules"]["driver_exposed"] >= 0

    assert isinstance(data["packages"]["count"], int)
    assert data["packages"]["count"] >= 0


def test_status_json_output_is_valid_json():
    """--json output must parse as valid JSON and contain the expected top-level keys."""
    result = _run(["--json"])
    assert result.returncode == 0
    data = json.loads(result.stdout)  # raises if invalid

    for key in ("profile", "skills", "hooks", "rules", "packages", "primitives", "governance_roi", "install", "health"):
        assert key in data, f"top-level key {key!r} missing from JSON output"
    assert "driver_path" in data["skills"]
    assert "driver_path" in data["hooks"]
    assert "driver_path" in data["rules"]
    assert "source_path" in data["rules"]
    assert "roi" in data["governance_roi"]
    assert "friction_vs_catch" in data["governance_roi"]
    assert "catch_ledger" in data["governance_roi"]
    assert "phase_policy" in data["governance_roi"]

    # health.checks must be a list; each check has status/message.
    checks = data["health"]["checks"]
    assert isinstance(checks, list)
    assert len(checks) >= 1
    for check in checks:
        assert "status" in check
        assert check["status"] in {"OK", "FAIL"}
        assert "message" in check


def test_status_help_flag_exits_zero():
    """--help must print usage and exit 0."""
    result = _run(["--help"])
    assert result.returncode == 0
    assert "cos status" in result.stdout.lower()
    assert "--verbose" in result.stdout
    assert "--json" in result.stdout


def test_status_unknown_flag_exits_nonzero():
    """An unknown flag must exit with a non-zero status."""
    result = _run(["--nonsense"])
    assert result.returncode != 0


def test_status_health_line_present():
    """A Health: line must be present, reporting either OK or FAIL state."""
    result = _run([])
    assert result.returncode == 0
    # Accept either the OK or FAIL form
    assert "Health:" in result.stdout
    has_ok = "all checks pass" in result.stdout
    has_fail = "issue(s)" in result.stdout
    assert has_ok or has_fail, "Health line is neither pass nor fail form"


def test_wrapper_dispatches_status_subcommand():
    """`cos status` via the wrapper must produce the same output as calling the script directly."""
    assert WRAPPER_SCRIPT.is_file(), "scripts/cos wrapper missing"
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(PROJECT_ROOT)
    result = subprocess.run(
        ["bash", str(WRAPPER_SCRIPT), "status", "--json"],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
        cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)
    assert "profile" in data


def test_status_uses_canonical_runtime_env_resolution():
    """Status should work when only canonical runtime env vars are present."""
    result = _run(
        ["--json"],
        env_overrides={
            "CLAUDE_PROJECT_DIR": "",
            "CODEX_PROJECT_DIR": "",
            "COGNITIVE_OS_PROJECT_DIR": str(PROJECT_ROOT),
        },
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)
    assert data["profile"]


def test_status_reports_canonical_state_without_claude_projection(tmp_path):
    """Status should still describe runtime state from canonical artifacts alone."""
    project = _setup_canonical_only_project(tmp_path)

    result = _run(
        ["--json"],
        env_overrides={
            "CLAUDE_PROJECT_DIR": "",
            "CODEX_PROJECT_DIR": "",
            "COGNITIVE_OS_PROJECT_DIR": str(project),
        },
    )

    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)

    assert data["skills"]["kernel_installed"] >= 1
    assert data["skills"]["driver_exposed"] == 0
    assert data["rules"]["source_count"] >= 1
    assert data["rules"]["source_path"].endswith(".cognitive-os/rules/cos")


def test_status_reads_hooks_from_codex_settings_driver(tmp_path):
    """Status should report the active Codex settings driver when it owns hook wiring."""
    project = _setup_codex_status_project(tmp_path)

    result = _run(
        ["--json"],
        env_overrides={
            "CLAUDE_PROJECT_DIR": "",
            "CODEX_PROJECT_DIR": "",
            "COGNITIVE_OS_PROJECT_DIR": str(project),
        },
    )

    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)

    assert data["hooks"]["driver_path"] == ".codex/hooks.json"
    assert data["hooks"]["total"] == 1
    assert data["hooks"]["by_event"].get("Stop") == 1


def test_status_resolves_codex_pwd_hook_commands_without_false_missing_hooks(tmp_path):
    """Status should resolve Codex $PWD/hooks commands instead of treating trailing 'true' as the hook path."""
    project = _setup_codex_pwd_hooks_project(tmp_path)

    result = _run(
        ["--json"],
        env_overrides={
            "CLAUDE_PROJECT_DIR": "",
            "CODEX_PROJECT_DIR": "",
            "COGNITIVE_OS_PROJECT_DIR": str(project),
            "COGNITIVE_OS_HARNESS": "codex",
        },
    )

    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)

    assert data["hooks"]["driver_path"] == ".codex/hooks.json"
    assert data["hooks"]["total"] == 3
    assert data["health"]["failures"] == 0


def test_status_portability_combines_proofs_and_projection_json():
    """--portability --json should expose both proof coverage and projection smoke status."""
    result = _run(["--portability", "--json"], timeout=180)
    assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout[-2000:]}"
    data = json.loads(result.stdout)

    assert data["schema_version"] == "cos-portability-status/v1"
    assert data["status"] == "pass"
    assert "scope_both" in data
    assert "scope_projection" in data
    assert data["summary"]["missing_proofs"] == 0
    assert data["summary"]["projection_block_findings"] == 0
    assert data["summary"]["install_smoke_status"] == "pass"

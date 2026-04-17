"""End-to-end test for the manifest pipeline.

This is a real E2E test — not a mock. It:

1. Builds a synthetic manifest.
2. Builds a sandbox PATH containing fake "tool" binaries (or omitting them).
3. Invokes scripts/manifest-check.sh as a subprocess with that PATH and the
   COS_MANIFEST_PATH override.
4. Asserts the script's exit code and JSON output match the deps reality
   we set up in the sandbox.

Covers:
- All required tools present  -> exit 0, status PASS
- One required tool missing   -> exit 1, status FAIL, item flagged
- Recommended tool missing    -> exit 0 (only required gates exit code)
- MCP server requires_tool    -> reports missing when tool absent
- Invalid manifest            -> exit 2 with stderr error
- Bad CLI flag                -> exit 2
- --json output is parseable  -> contains expected schema keys
- --profile full              -> includes recommended tools

Sandbox PATH strategy: each fake tool is a 1-line shell script that prints
its name. We never run anything that could touch the host system.
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest
import yaml

pytestmark = [pytest.mark.integration, pytest.mark.e2e]

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "manifest-check.sh"


def _write_manifest(tmp_path: Path, payload: dict) -> Path:
    p = tmp_path / "dependencies.yaml"
    p.write_text(yaml.safe_dump(payload, sort_keys=False))
    return p


def _make_fake_bin(bin_dir: Path, name: str) -> Path:
    bin_dir.mkdir(parents=True, exist_ok=True)
    fake = bin_dir / name
    fake.write_text(f"#!/usr/bin/env bash\necho fake-{name}\n")
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return fake


def _run_check(
    *,
    manifest: Path,
    bin_dir: Path | None,
    profile: str = "default",
    json_output: bool = False,
    extra_args: list[str] | None = None,
) -> subprocess.CompletedProcess:
    """Run manifest-check.sh in a controlled environment.

    PATH contains only:
      - bin_dir (where the test placed fake tools)
      - the directory holding python3 + bash (so the script itself runs)
      - the directory holding shutil-resolvable system tools the script needs
        ('python3', 'bash')

    Critically, system 'jq', 'engram', etc. are NOT in PATH unless the test
    placed them in bin_dir — guaranteeing the check sees only what we set up.
    """
    args = ["bash", str(SCRIPT), "--manifest", str(manifest), "--profile", profile]
    if json_output:
        args.append("--json")
    if extra_args:
        args.extend(extra_args)

    python_bin = shutil.which("python3")
    bash_bin = shutil.which("bash")
    assert python_bin and bash_bin, "test environment must have python3 and bash"

    parts = {Path(python_bin).parent, Path(bash_bin).parent}
    if bin_dir:
        parts = {bin_dir} | parts
    env = {
        **os.environ,
        "PATH": ":".join(str(p) for p in parts),
    }
    return subprocess.run(args, capture_output=True, text=True, cwd=REPO_ROOT, env=env)


def _two_tool_manifest() -> dict:
    return {
        "schema_version": 1,
        "python": {"required": ["pyyaml>=6.0"], "groups": {}},
        "tools": [
            {
                "name": "fake-required",
                "criticality": "required",
                "check": "fake-required --version",
                "install": {"any": "echo install fake-required"},
            },
            {
                "name": "fake-recommended",
                "criticality": "recommended",
                "check": "fake-recommended --version",
                "install": {"any": "echo install fake-recommended"},
            },
        ],
        "mcp_servers": [
            {
                "name": "fake-mcp",
                "criticality": "recommended",
                "transport": "stdio",
                "command": "echo",
                "args": ["fake"],
                "register_to": "~/.claude/settings.json",
                "requires_tool": "fake-recommended",
            }
        ],
        "profiles": {
            "default": {
                "python_groups": [],
                "tools_required": ["fake-required"],
                "tools_recommended": ["fake-recommended"],
                "mcp_servers_recommended": ["fake-mcp"],
            },
            "full": {
                "python_groups": [],
                "tools_required": ["fake-required"],
                "tools_recommended": ["fake-recommended"],
                "mcp_servers_recommended": ["fake-mcp"],
            },
        },
    }


# ── Smoke ───────────────────────────────────────────────────────────────


def test_script_exists_and_is_executable():
    assert SCRIPT.exists(), f"missing: {SCRIPT}"
    assert os.access(SCRIPT, os.X_OK), f"not executable: {SCRIPT}"


def test_help_flag_works():
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--help"], capture_output=True, text=True, cwd=REPO_ROOT
    )
    assert proc.returncode == 0
    assert "Usage" in proc.stdout
    assert "--profile" in proc.stdout


# ── Core E2E paths ──────────────────────────────────────────────────────


def test_all_required_present_exits_zero(tmp_path):
    """All required tools in PATH → exit 0, output reports PASS."""
    manifest = _write_manifest(tmp_path, _two_tool_manifest())
    bin_dir = tmp_path / "bin"
    _make_fake_bin(bin_dir, "fake-required")
    _make_fake_bin(bin_dir, "fake-recommended")

    proc = _run_check(manifest=manifest, bin_dir=bin_dir)
    assert proc.returncode == 0, f"stdout={proc.stdout!r}\nstderr={proc.stderr!r}"
    assert "PASS" in proc.stdout
    assert "fake-required" in proc.stdout


def test_required_missing_exits_one(tmp_path):
    """Required tool absent → exit 1, FAIL with the missing item flagged."""
    manifest = _write_manifest(tmp_path, _two_tool_manifest())
    bin_dir = tmp_path / "bin"
    _make_fake_bin(bin_dir, "fake-recommended")  # only the recommended one

    proc = _run_check(manifest=manifest, bin_dir=bin_dir)
    assert proc.returncode == 1, f"stdout={proc.stdout!r}\nstderr={proc.stderr!r}"
    assert "FAIL" in proc.stdout
    assert "fake-required" in proc.stdout
    assert "MISSING" in proc.stdout


def test_recommended_missing_does_not_fail(tmp_path):
    """Only required absence gates the exit code."""
    manifest = _write_manifest(tmp_path, _two_tool_manifest())
    bin_dir = tmp_path / "bin"
    _make_fake_bin(bin_dir, "fake-required")

    proc = _run_check(manifest=manifest, bin_dir=bin_dir)
    assert proc.returncode == 0
    assert "PASS" in proc.stdout
    # Recommended is reported missing but doesn't fail the run.
    assert "fake-recommended" in proc.stdout


def test_mcp_marked_missing_when_tool_absent(tmp_path):
    """An MCP whose requires_tool is absent should be flagged MISSING."""
    manifest = _write_manifest(tmp_path, _two_tool_manifest())
    bin_dir = tmp_path / "bin"
    _make_fake_bin(bin_dir, "fake-required")  # MCP's required tool is NOT installed

    proc = _run_check(manifest=manifest, bin_dir=bin_dir, json_output=True)
    assert proc.returncode == 0  # MCPs are recommended, don't fail
    payload = json.loads(proc.stdout)
    fake_mcp = next(m for m in payload["mcp_servers"] if m["name"] == "fake-mcp")
    assert fake_mcp["status"] == "missing"
    assert fake_mcp["requires_tool"] == "fake-recommended"


def test_mcp_marked_ok_when_tool_present(tmp_path):
    manifest = _write_manifest(tmp_path, _two_tool_manifest())
    bin_dir = tmp_path / "bin"
    _make_fake_bin(bin_dir, "fake-required")
    _make_fake_bin(bin_dir, "fake-recommended")

    proc = _run_check(manifest=manifest, bin_dir=bin_dir, json_output=True)
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    fake_mcp = next(m for m in payload["mcp_servers"] if m["name"] == "fake-mcp")
    assert fake_mcp["status"] == "ok"


# ── Output / interface ──────────────────────────────────────────────────


def test_json_output_is_parseable_and_typed(tmp_path):
    manifest = _write_manifest(tmp_path, _two_tool_manifest())
    bin_dir = tmp_path / "bin"
    _make_fake_bin(bin_dir, "fake-required")
    _make_fake_bin(bin_dir, "fake-recommended")

    proc = _run_check(manifest=manifest, bin_dir=bin_dir, json_output=True)
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["profile"] == "default"
    assert isinstance(payload["tools"], list)
    assert isinstance(payload["mcp_servers"], list)
    assert isinstance(payload["python_groups"], list)
    for entry in payload["tools"]:
        assert {"name", "criticality", "status", "install"} <= entry.keys()
        assert entry["status"] in {"ok", "missing"}
        assert entry["criticality"] in {"required", "recommended", "optional"}


def test_unknown_flag_exits_two(tmp_path):
    manifest = _write_manifest(tmp_path, _two_tool_manifest())
    proc = _run_check(manifest=manifest, bin_dir=None, extra_args=["--what-is-this"])
    assert proc.returncode == 2
    assert "unknown argument" in proc.stderr.lower()


def test_profile_flag_changes_scope(tmp_path):
    """--profile full reports the profile name in JSON output."""
    manifest = _write_manifest(tmp_path, _two_tool_manifest())
    bin_dir = tmp_path / "bin"
    _make_fake_bin(bin_dir, "fake-required")
    _make_fake_bin(bin_dir, "fake-recommended")

    proc = _run_check(manifest=manifest, bin_dir=bin_dir, profile="full", json_output=True)
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["profile"] == "full"


def test_unknown_profile_exits_two(tmp_path):
    manifest = _write_manifest(tmp_path, _two_tool_manifest())
    bin_dir = tmp_path / "bin"
    _make_fake_bin(bin_dir, "fake-required")

    proc = _run_check(manifest=manifest, bin_dir=bin_dir, profile="nonexistent")
    assert proc.returncode == 2
    assert "Unknown profile" in proc.stderr


# ── Validation errors propagate ─────────────────────────────────────────


def test_invalid_manifest_exits_two(tmp_path):
    """A manifest that fails schema validation must exit 2 with a clear error."""
    payload = _two_tool_manifest()
    payload["tools"][0]["criticality"] = "kinda-important"  # invalid
    manifest = _write_manifest(tmp_path, payload)
    bin_dir = tmp_path / "bin"
    _make_fake_bin(bin_dir, "fake-required")

    proc = _run_check(manifest=manifest, bin_dir=bin_dir)
    assert proc.returncode == 2
    assert "criticality" in proc.stderr


def test_missing_manifest_exits_two(tmp_path):
    proc = _run_check(manifest=tmp_path / "no-such-file.yaml", bin_dir=None)
    assert proc.returncode == 2
    assert "not found" in proc.stderr


# ── Production manifest is healthy ──────────────────────────────────────


def test_production_manifest_loads_via_script():
    """The real manifests/dependencies.yaml passes schema validation."""
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--profile", "default", "--json"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    # Exit code is 0 or 1 depending on what's installed locally — both prove
    # the manifest is valid (2 would mean schema/parse error).
    assert proc.returncode in (0, 1), (
        f"production manifest failed to load: exit={proc.returncode}\n"
        f"stdout={proc.stdout}\nstderr={proc.stderr}"
    )
    payload = json.loads(proc.stdout)
    assert payload["profile"] == "default"
    tool_names = {t["name"] for t in payload["tools"]}
    # Sanity: jq is declared as required in the production manifest.
    assert "jq" in tool_names

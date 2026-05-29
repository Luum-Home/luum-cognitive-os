from __future__ import annotations

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "check-bun-install-policy.py"


def _module():
    spec = importlib.util.spec_from_file_location("check_bun_install_policy", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_tracked_package_roots_have_bun_ignore_scripts_enabled() -> None:
    report = _module().build_report(REPO)

    assert report["status"] == "pass"
    assert report["canonical_package_manager"] == "bun"
    assert report["package_count"] >= 3
    assert report["failure_count"] == 0
    assert report["forbidden_lockfile_count"] == 0
    for row in report["rows"]:
        assert row["ignoreScripts"] is True
        assert row["bunfig"].endswith("bunfig.toml")
        assert row["packageManager"].startswith("bun@")
        assert row["packageManager_ok"] is True


def test_bun_policy_reports_lifecycle_script_impact() -> None:
    report = _module().build_report(REPO)
    by_path = {row["path"]: row for row in report["rows"]}

    assert by_path["package.json"]["lifecycle_scripts_blocked"] == {"postinstall": "node scripts/postinstall.js"}
    assert "preinstall/install/postinstall/prepare" in by_path["package.json"]["impact"]


def test_dependency_bearing_packages_commit_bun_lockfiles() -> None:
    report = _module().build_report(REPO)
    by_path = {row["path"]: row for row in report["rows"]}

    assert by_path["dashboard/package.json"]["bun_lock"] == "dashboard/bun.lock"
    assert by_path["examples/hello-world/package.json"]["bun_lock"] == "examples/hello-world/bun.lock"
    assert by_path["package.json"]["bun_lock_required"] is False

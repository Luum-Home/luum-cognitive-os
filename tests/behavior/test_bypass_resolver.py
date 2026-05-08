from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESOLVER = ROOT / "hooks" / "_lib" / "bypass-resolver.sh"


def run_resolver(tmp_path: Path, key: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    project = tmp_path / "project"
    project.mkdir()
    merged = os.environ.copy()
    merged.update(env or {})
    merged["COGNITIVE_OS_PROJECT_DIR"] = str(project)
    script = f"source {RESOLVER}; cos_bypass_allows {key}"
    return subprocess.run(["bash", "-lc", script], text=True, capture_output=True, env=merged)


def test_cos_bypass_allowlist_hit_with_whitespace(tmp_path: Path) -> None:
    proc = run_resolver(tmp_path, "push_collision", {"COS_BYPASS": " destructive_git, push_collision "})
    assert proc.returncode == 0


def test_cos_bypass_allowlist_miss(tmp_path: Path) -> None:
    proc = run_resolver(tmp_path, "push_collision", {"COS_BYPASS": "destructive_git"})
    assert proc.returncode != 0


def test_legacy_alias_hit(tmp_path: Path) -> None:
    proc = run_resolver(tmp_path, "destructive_git", {"COS_ALLOW_DESTRUCTIVE_GIT": "1"})
    assert proc.returncode == 0


def test_runtime_file_is_visible_to_pretool_style_process(tmp_path: Path) -> None:
    project = tmp_path / "project"
    runtime = project / ".cognitive-os" / "runtime"
    runtime.mkdir(parents=True)
    (runtime / "bypass.env").write_text("COS_BYPASS=branch_switch\n", encoding="utf-8")
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(project)
    proc = subprocess.run(["bash", "-lc", f"source {RESOLVER}; cos_bypass_allows branch_switch"], env=env)
    assert proc.returncode == 0


def test_truthy_alias_values(tmp_path: Path) -> None:
    proc = run_resolver(tmp_path, "push_collision", {"DISABLE_HOOK_PUSH_COLLISION_CHECK": "true"})
    assert proc.returncode == 0

from __future__ import annotations

import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def test_closure_wrapper_is_portable_and_syntax_valid() -> None:
    for path in [REPO / "scripts" / "cos-branch-worktree-closure", REPO / "scripts" / "cos_branch_worktree_closure.py"]:
        assert path.exists()
    assert subprocess.run(["bash", "-n", str(REPO / "scripts" / "cos-branch-worktree-closure")], check=False).returncode == 0
    assert subprocess.run(["python3", "-m", "py_compile", str(REPO / "scripts" / "cos_branch_worktree_closure.py")], check=False).returncode == 0


def test_branch_worktree_skill_projected_to_cli_ide_surfaces() -> None:
    for rel in [
        "skills/branch-worktree-closure/SKILL.md",
        ".codex/skills/branch-worktree-closure/SKILL.md",
        ".cognitive-os/skills/branch-worktree-closure/SKILL.md",
        ".claude/skills/branch-worktree-closure/SKILL.md",
    ]:
        text = (REPO / rel).read_text(encoding="utf-8")
        assert "scripts/cos-branch-worktree-closure --json" in text
        assert "scripts/cos land" in text


def test_agents_md_foregrounds_protected_main_landing() -> None:
    text = (REPO / "AGENTS.md").read_text(encoding="utf-8")
    assert "Protected Main Landing" in text
    assert "Do **not** run `git push origin main` directly" in text
    assert "scripts/cos-branch-worktree-closure --json" in text


def test_branch_worktree_closure_projected_to_all_ai_adapters() -> None:
    adapter_files = sorted((REPO / ".ai" / "adapters").glob("*/adapter.json"))
    assert adapter_files, "expected portable .ai adapters"
    missing: list[str] = []
    for adapter in adapter_files:
        text = adapter.read_text(encoding="utf-8")
        if "branch-worktree-closure" not in text and "cos-branch-worktree-closure" not in text:
            missing.append(str(adapter.relative_to(REPO)))
    assert missing == []

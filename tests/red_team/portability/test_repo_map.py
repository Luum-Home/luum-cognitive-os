# SCOPE: both
"""Portability probes for lib/repo_map.py — W3-1 repo-map context selector.

Bilateral assertion: build_repo_map() runs on any harness with python3 against
either a real COS checkout or a synthetic project directory, returning a
schema-stable RepoMapPacket within a token budget.

Falsification probes:
  - Token-budget violations: total selected output must respect max_tokens
    (modulo a single seed entry); a stub returning the full repo would fail.
  - Changed-file boost: a file passed via changed_files must be ranked with
    reason "changed_file" (proves the scoring is real, not a stub).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from lib.repo_map import build_repo_map  # noqa: E402


def _init_synth_project(root: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "t@e.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True)
    (root / "hooks").mkdir()
    (root / "hooks" / "alpha.sh").write_text("#!/bin/sh\necho alpha\n")
    (root / "skills").mkdir()
    (root / "skills" / "beta.md").write_text("# beta skill about parsing yaml\n")
    (root / "module.py").write_text(
        "def parse_yaml(text):\n    return text\n\nclass YamlReader:\n    pass\n"
    )
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "seed"], cwd=root, check=True, capture_output=True
    )


def test_build_repo_map_runs_and_returns_versioned_packet(tmp_path: Path) -> None:
    """Bilateral: build_repo_map returns a versioned packet on any harness."""
    _init_synth_project(tmp_path)
    packet = build_repo_map(tmp_path, "parse yaml", max_tokens=400).to_dict()

    assert packet["schema_version"]
    assert packet["query"] == "parse yaml"
    assert isinstance(packet["code_symbols"], list)
    assert isinstance(packet["governance"], dict)
    assert "hooks" in packet["governance"]
    assert "skills" in packet["governance"]
    assert packet["budget"]["max_tokens"] == 400
    assert "estimated_tokens" in packet["budget"] or "used_tokens" in packet["budget"]


def test_build_repo_map_respects_token_budget(tmp_path: Path) -> None:
    """Falsification: a stub ignoring max_tokens would dump the whole repo."""
    _init_synth_project(tmp_path)
    # Add many extra files to make the budget meaningful.
    for i in range(40):
        (tmp_path / f"extra_{i}.py").write_text(f"def fn_{i}():\n    pass\n")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "extras"], cwd=tmp_path, check=True, capture_output=True
    )

    packet = build_repo_map(tmp_path, "fn", max_tokens=120).to_dict()
    used = packet["budget"].get("used_tokens", packet["budget"].get("estimated_tokens"))
    # Allow seed-entry overshoot but reject a 10x runaway.
    assert used <= 400, (
        f"falsification: build_repo_map blew the token budget (used={used}, max=120)"
    )


def test_build_repo_map_marks_changed_files_with_changed_reason(tmp_path: Path) -> None:
    """Falsification: changed_files boost must be applied (scoring is live)."""
    _init_synth_project(tmp_path)
    packet = build_repo_map(
        tmp_path, "alpha", max_tokens=400, changed_files=["module.py"]
    ).to_dict()
    reasons = {entry["path"]: entry["reason"] for entry in packet["code_symbols"]}
    assert reasons.get("module.py") == "changed_file", (
        f"falsification: changed_file boost missing; reasons={reasons}"
    )

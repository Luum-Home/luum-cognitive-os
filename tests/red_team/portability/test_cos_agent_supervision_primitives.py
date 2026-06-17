# SCOPE: os-only
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WRAPPERS = ["cos-agent-run-status", "cos-agent-watch", "cos-progress-metric", "cos-handoff-if-dead"]
SKILL_PATHS = [
    ROOT / "skills" / "agent-run-supervision" / "SKILL.md",
    ROOT / ".codex" / "skills" / "agent-run-supervision" / "SKILL.md",
    ROOT / ".cognitive-os" / "skills" / "agent-run-supervision" / "SKILL.md",
    ROOT / ".cognitive-os" / "skills" / "cos" / "agent-run-supervision" / "SKILL.md",
    ROOT / ".claude" / "skills" / "agent-run-supervision" / "SKILL.md",
]


def run(cmd: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False, timeout=30)
    if check and result.returncode != 0:
        raise AssertionError(f"command failed {cmd}\nstdout={result.stdout}\nstderr={result.stderr}")
    return result


def init_repo(tmp_path: Path) -> Path:
    remote = tmp_path / "remote.git"
    repo = tmp_path / "repo"
    run(["git", "init", "--bare", str(remote)], tmp_path)
    run(["git", "clone", str(remote), str(repo)], tmp_path)
    run(["git", "switch", "-c", "main"], repo)
    run(["git", "config", "user.email", "test@example.com"], repo)
    run(["git", "config", "user.name", "Test User"], repo)
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    run(["git", "add", "README.md"], repo)
    run(["git", "commit", "-m", "base"], repo)
    run(["git", "push", "-u", "origin", "main"], repo)
    return repo


def test_agent_supervision_wrappers_are_portable_and_syntax_valid() -> None:
    for name in WRAPPERS:
        path = ROOT / "scripts" / name
        assert path.exists(), name
        assert path.stat().st_mode & 0o111, name
        assert subprocess.run(["bash", "-n", str(path)], check=False).returncode == 0
    assert subprocess.run(["python3", "-m", "py_compile", str(ROOT / "scripts" / "cos_agent_supervision.py")], check=False).returncode == 0


def test_agent_supervision_skill_projected_to_cli_ide_surfaces() -> None:
    canonical = SKILL_PATHS[0].read_text(encoding="utf-8")
    for path in SKILL_PATHS:
        assert path.exists(), str(path)
        assert path.read_text(encoding="utf-8") == canonical
    assert "como venimos" in canonical
    assert "how are we doing" in canonical
    assert "agente travado" in canonical


def test_agent_supervision_runs_from_arbitrary_consumer_cwd(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (repo / "wip.txt").write_text("work\n", encoding="utf-8")

    status = run([str(ROOT / "scripts" / "cos-agent-run-status"), "--project-dir", str(repo), "--process-id", "missing-agent-xyz", "--language", "es", "--json"], outside)
    payload = json.loads(status.stdout)
    assert payload["state"] == "dead-with-wip"
    assert payload["receipt_path"].startswith(str(repo))

    handoff = run([str(ROOT / "scripts" / "cos-handoff-if-dead"), "--project-dir", str(repo), "--process-id", "missing-agent-xyz", "--json"], outside)
    assert Path(json.loads(handoff.stdout)["handoff_path"]).exists()

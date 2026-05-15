from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "scripts" / "stash_quarantine_audit.py"
AUTO_CHECKPOINT = ROOT / "hooks" / "auto-checkpoint.sh"


def run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(cmd, cwd=cwd, env=merged, text=True, capture_output=True, check=False, timeout=30)


def init_repo(repo: Path) -> None:
    run(["git", "init"], repo)
    run(["git", "config", "user.email", "smoke@example.invalid"], repo)
    run(["git", "config", "user.name", "Smoke Test"], repo)
    (repo / "tracked.txt").write_text("initial\n", encoding="utf-8")
    run(["git", "add", "tracked.txt"], repo)
    commit = run(["git", "commit", "-m", "initial"], repo)
    assert commit.returncode == 0, commit.stderr


def stash_count(repo: Path) -> int:
    result = run(["git", "stash", "list"], repo)
    assert result.returncode == 0, result.stderr
    return len([line for line in result.stdout.splitlines() if line.strip()])


def test_stash_quarantine_smoke_audits_guidance_and_preserves_wip_without_stash(tmp_path: Path) -> None:
    repo = tmp_path / "consumer-repo"
    repo.mkdir()
    init_repo(repo)

    docs = repo / "docs"
    docs.mkdir()
    unsafe = docs / "recovery.md"
    unsafe.write_text("When done, run git stash pop.\n", encoding="utf-8")

    audit_result = run(["python3", str(AUDIT), "--project-dir", str(repo), "--json", "--fail", "docs/recovery.md"], repo)
    audit_payload = json.loads(audit_result.stdout)
    assert audit_result.returncode == 1
    assert audit_payload["findings"][0]["code"] == "bare-stash-operation"

    unsafe.write_text("Inspect first, then git stash apply <reviewed-stash-ref>.\n", encoding="utf-8")
    clean_audit = run(["python3", str(AUDIT), "--project-dir", str(repo), "--fail", "docs/recovery.md"], repo)
    assert clean_audit.returncode == 0, clean_audit.stdout + clean_audit.stderr

    before_stashes = stash_count(repo)
    (repo / "tracked.txt").write_text("changed but visible\n", encoding="utf-8")
    (repo / "untracked.txt").write_text("new and visible\n", encoding="utf-8")

    checkpoint_dir = repo / ".cognitive-os" / "checkpoints"
    checkpoint_dir.mkdir(parents=True)
    (checkpoint_dir / ".last-checkpoint").write_text(str(int(time.time()) - 600), encoding="utf-8")

    hook_result = run(["bash", str(AUTO_CHECKPOINT)], repo, env={"CLAUDE_PROJECT_DIR": str(repo)})
    assert hook_result.returncode == 0, hook_result.stderr
    assert stash_count(repo) == before_stashes
    assert (repo / "tracked.txt").read_text(encoding="utf-8") == "changed but visible\n"
    assert (repo / "untracked.txt").read_text(encoding="utf-8") == "new and visible\n"

    metadata_files = sorted(checkpoint_dir.glob("cos-*.json"))
    assert metadata_files
    metadata = json.loads(metadata_files[-1].read_text(encoding="utf-8"))
    assert metadata["mode"] == "copy"
    assert metadata["stash_name"] == "copy-only"
    copied = set(metadata["copied_files"])
    assert {"tracked.txt", "untracked.txt", "docs/recovery.md"}.issubset(copied)
    for rel in copied:
        copied_path = Path(metadata["checkpoint_files_dir"]) / rel
        assert copied_path.exists(), f"missing checkpoint copy for {rel}"

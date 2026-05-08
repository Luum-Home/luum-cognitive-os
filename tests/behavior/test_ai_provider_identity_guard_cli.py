from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _run(cmd: list[str], cwd: Path, *, env: dict | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False, env=env)


def _install_guard_fixture(repo: Path) -> None:
    (repo / "lib").mkdir()
    (repo / "scripts").mkdir()
    (repo / "manifests").mkdir()
    (repo / ".githooks").mkdir()
    shutil.copy2(ROOT / "lib" / "ai_provider_identity_guard.py", repo / "lib" / "ai_provider_identity_guard.py")
    shutil.copy2(ROOT / "scripts" / "ai-provider-identity-guard", repo / "scripts" / "ai-provider-identity-guard")
    shutil.copy2(ROOT / "manifests" / "ai-provider-identity-policy.yaml", repo / "manifests" / "ai-provider-identity-policy.yaml")
    shutil.copy2(ROOT / ".githooks" / "commit-msg", repo / ".githooks" / "commit-msg")
    shutil.copy2(ROOT / ".githooks" / "pre-commit", repo / ".githooks" / "pre-commit")
    (repo / "lib" / "__init__.py").write_text("\n", encoding="utf-8")
    (repo / "scripts" / "cos-dependency-adoption-gate").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    (repo / "scripts" / "cos-dependency-adoption-gate").chmod(0o755)


def test_staged_guard_blocks_provider_like_email(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _run(["git", "init", "--initial-branch=main"], repo)
    _run(["git", "config", "user.name", "Tester"], repo)
    _run(["git", "config", "user.email", "tester@example.com"], repo)
    _install_guard_fixture(repo)

    provider_email = "no" + "reply" + "@" + "anthropic" + ".com"
    (repo / "README.md").write_text(f"Co-authored-by: Assistant <{provider_email}>\n", encoding="utf-8")
    _run(["git", "add", "README.md"], repo)

    proc = _run(["python3", "scripts/ai-provider-identity-guard", "--staged"], repo)

    assert proc.returncode == 2
    assert "ai-provider" in proc.stdout


def test_commit_msg_hook_blocks_provider_coauthor(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _run(["git", "init", "--initial-branch=main"], repo)
    _run(["git", "config", "user.name", "Tester"], repo)
    _run(["git", "config", "user.email", "tester@example.com"], repo)
    _run(["git", "config", "core.hooksPath", ".githooks"], repo)
    _install_guard_fixture(repo)
    # This test isolates commit-msg; the full pre-commit hook has unrelated gates.
    (repo / ".githooks" / "pre-commit").unlink()

    (repo / "ok.txt").write_text("ok\n", encoding="utf-8")
    _run(["git", "add", "."], repo)
    provider = "Co" + "dex"
    proc = _run(["git", "commit", "-m", "feat: x", "-m", f"Co-authored-by: {provider}"], repo)

    assert proc.returncode != 0
    assert "AI-provider-looking" in (proc.stdout + proc.stderr)


def test_tracked_guard_scans_committed_files(tmp_path: Path) -> None:
    repo = tmp_path / "repo-tracked"
    repo.mkdir()
    _run(["git", "init", "--initial-branch=main"], repo)
    _run(["git", "config", "user.name", "Tester"], repo)
    _run(["git", "config", "user.email", "tester@example.com"], repo)
    _install_guard_fixture(repo)
    provider_email = "bot" + "@" + "openai" + ".com"
    (repo / "README.md").write_text(f"Contact: {provider_email}\n", encoding="utf-8")
    _run(["git", "add", "."], repo)
    # Bypass hooks so the fixture can represent already-committed historical content.
    _run(["git", "commit", "--no-verify", "-m", "seed"], repo)

    proc = _run(["python3", "scripts/ai-provider-identity-guard", "--tracked", "--json"], repo)

    assert proc.returncode == 2
    assert "ai-provider-email" in proc.stdout

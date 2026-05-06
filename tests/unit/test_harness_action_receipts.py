from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from lib.harness_action_receipts import (
    ReceiptError,
    append_receipt,
    make_receipt,
    promote_with_git_observation,
    promote_with_pre_push_evidence,
    promote_with_provider_evidence,
    receipt_stats,
    render_markdown_report,
    receipts_from_codex_directives,
    validate_receipt,
)

pytestmark = pytest.mark.unit

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "cos-action-receipt"


def run_git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def init_repo(repo: Path) -> None:
    run_git(repo, "init")
    run_git(repo, "config", "user.email", "test@example.com")
    run_git(repo, "config", "user.name", "Test User")


def commit_file(repo: Path, path: str, content: str = "content\n") -> str:
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    run_git(repo, "add", path)
    run_git(repo, "commit", "-m", f"add {path}")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()


def test_make_receipt_validates_required_schema(tmp_path: Path) -> None:
    receipt = make_receipt(
        event_type="vcs.stage",
        provider="unit-test",
        source="harness-directive",
        project_dir=tmp_path,
        evidence={"directive": "::git-stage{cwd=\"/tmp/x\"}"},
    )

    validate_receipt(receipt)
    assert receipt["schema_version"] == "harness-action-receipt.v1"
    assert receipt["domain"] == "vcs"
    assert receipt["action"] == "stage"
    assert receipt["trust"] == "advisory"


def test_validate_rejects_unknown_event(tmp_path: Path) -> None:
    receipt = make_receipt(event_type="vcs.stage", provider="unit-test", source="git-hook", project_dir=tmp_path)
    receipt["event_type"] = "vcs.teleport"

    with pytest.raises(ReceiptError, match="unsupported VCS event_type"):
        validate_receipt(receipt)


def test_codex_directive_parses_as_advisory_receipt(tmp_path: Path) -> None:
    text = f'Done. ::git-stage{{cwd="{tmp_path}"}} ::git-push{{cwd="{tmp_path}" branch="main"}}'

    receipts = receipts_from_codex_directives(text)

    assert [receipt["event_type"] for receipt in receipts] == ["vcs.stage", "vcs.push"]
    assert all(receipt["trust"] == "advisory" for receipt in receipts)
    assert all(receipt["source"] == "harness-directive" for receipt in receipts)
    assert receipts[1]["branch"] == "main"


def test_promotes_stage_receipt_when_staged_files_are_observed(tmp_path: Path) -> None:
    init_repo(tmp_path)
    target = tmp_path / "hello.txt"
    target.write_text("hello\n", encoding="utf-8")
    run_git(tmp_path, "add", "hello.txt")
    receipt = make_receipt(
        event_type="vcs.stage",
        provider="codex-desktop",
        source="harness-directive",
        project_dir=tmp_path,
    )

    promoted = promote_with_git_observation(receipt, tmp_path)

    assert promoted["trust"] == "observed"
    assert promoted["source"] == "local-git-observation"
    assert promoted["files"] == ["hello.txt"]
    assert promoted["evidence"]["observed_git_status"] == {"staged_files": ["hello.txt"]}


def test_stage_promotion_fails_without_staged_files(tmp_path: Path) -> None:
    init_repo(tmp_path)
    receipt = make_receipt(
        event_type="vcs.stage",
        provider="codex-desktop",
        source="harness-directive",
        project_dir=tmp_path,
    )

    with pytest.raises(ReceiptError, match="no staged files observed"):
        promote_with_git_observation(receipt, tmp_path)


def test_append_receipt_writes_jsonl(tmp_path: Path) -> None:
    receipt = make_receipt(event_type="vcs.commit", provider="git-hook", source="git-hook", trust="verified", project_dir=tmp_path)
    out = tmp_path / ".cognitive-os" / "metrics" / "vcs-actions.jsonl"

    written = append_receipt(receipt, project_dir=tmp_path)

    assert written == out
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert rows == [receipt]


def test_cli_emit_appends_receipt(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            str(SCRIPT),
            "emit",
            "vcs.stage",
            "--provider",
            "unit-test",
            "--source",
            "git-hook",
            "--trust",
            "verified",
            "--project-dir",
            str(tmp_path),
            "--file",
            "a.py",
            "--append",
            "--json",
        ],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["event_type"] == "vcs.stage"
    assert payload["trust"] == "verified"
    metrics = tmp_path / ".cognitive-os" / "metrics" / "vcs-actions.jsonl"
    assert metrics.exists()


def test_cli_parse_codex_promotes_when_git_state_supports_it(tmp_path: Path) -> None:
    init_repo(tmp_path)
    (tmp_path / "a.py").write_text("print('ok')\n", encoding="utf-8")
    run_git(tmp_path, "add", "a.py")
    result = subprocess.run(
        [str(SCRIPT), "parse-codex", "--text", f'::git-stage{{cwd="{tmp_path}"}}', "--promote-git", "--json"],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    receipts = json.loads(result.stdout)
    assert receipts[0]["trust"] == "observed"
    assert receipts[0]["files"] == ["a.py"]


def test_promotes_push_when_remote_ref_matches_local_commit(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    remote = tmp_path / "remote.git"
    repo.mkdir()
    init_repo(repo)
    run_git(remote.parent, "init", "--bare", remote.name)
    sha = commit_file(repo, "a.py")
    run_git(repo, "branch", "-M", "main")
    run_git(repo, "remote", "add", "origin", str(remote))
    run_git(repo, "push", "origin", "main")
    receipt = make_receipt(
        event_type="vcs.push",
        provider="codex-desktop",
        source="harness-directive",
        project_dir=repo,
        branch="main",
        remote="origin",
    )

    promoted = promote_with_git_observation(receipt, repo)

    assert promoted["trust"] == "observed"
    assert promoted["commit_sha"] == sha
    assert promoted["evidence"]["observed_git_status"]["remote_sha"] == sha


def test_promotes_push_with_pre_push_refs_to_verified(tmp_path: Path) -> None:
    receipt = make_receipt(
        event_type="vcs.push",
        provider="shell-git-hook",
        source="harness-directive",
        project_dir=tmp_path,
        branch="main",
        commit_sha="abc123",
    )

    promoted = promote_with_pre_push_evidence(
        receipt,
        "refs/heads/main abc123 refs/heads/main 000000\n",
    )

    assert promoted["trust"] == "verified"
    assert promoted["source"] == "git-hook"
    assert promoted["governed_path"] == "pre-push"
    assert promoted["evidence"]["pre_push"]["refs"][0]["local_sha"] == "abc123"


def test_promotes_with_provider_evidence_to_authoritative(tmp_path: Path) -> None:
    receipt = make_receipt(event_type="vcs.push", provider="github", source="provider-api", project_dir=tmp_path)

    promoted = promote_with_provider_evidence(
        receipt,
        {"accepted": True, "remote": "origin", "branch": "main", "remote_ref_sha": "def456"},
    )

    assert promoted["trust"] == "authoritative"
    assert promoted["commit_sha"] == "def456"
    assert promoted["remote"] == "origin"
    assert promoted["branch"] == "main"


def test_receipt_stats_and_markdown_report_count_by_trust(tmp_path: Path) -> None:
    append_receipt(
        make_receipt(event_type="vcs.stage", provider="unit", source="harness-directive", project_dir=tmp_path),
        project_dir=tmp_path,
    )
    append_receipt(
        make_receipt(event_type="vcs.merge.land", provider="cos-merge-queue", source="merge-queue", trust="authoritative", project_dir=tmp_path),
        project_dir=tmp_path,
    )

    stats = receipt_stats(project_dir=tmp_path)
    report = render_markdown_report(stats)

    assert stats["total"] == 2
    assert stats["by_trust"] == {"advisory": 1, "authoritative": 1}
    assert "| `vcs.merge.land` | 1 |" in report


def test_cli_stats_and_report(tmp_path: Path) -> None:
    append_receipt(
        make_receipt(event_type="vcs.stage", provider="unit", source="git-hook", trust="verified", project_dir=tmp_path),
        project_dir=tmp_path,
    )
    stats_result = subprocess.run(
        [str(SCRIPT), "stats", "--project-dir", str(tmp_path), "--json"],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )
    assert stats_result.returncode == 0, stats_result.stderr
    assert json.loads(stats_result.stdout)["verified"] == 1

    report_path = tmp_path / "receipt-report.md"
    report_result = subprocess.run(
        [str(SCRIPT), "report", "--project-dir", str(tmp_path), "--output", str(report_path), "--json"],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )
    assert report_result.returncode == 0, report_result.stderr
    assert "# VCS Action Receipts" in report_path.read_text(encoding="utf-8")

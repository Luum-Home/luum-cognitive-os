"""Unit tests for scripts/verify_claims.py.

The verifier runs commands; these tests keep the commands synthetic and the
working directory a tmp_path, so nothing depends on the repository's current
counts.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "verify_claims.py"
spec = importlib.util.spec_from_file_location("verify_claims", MODULE_PATH)
assert spec and spec.loader
verify_claims = importlib.util.module_from_spec(spec)
sys.modules["verify_claims"] = verify_claims
spec.loader.exec_module(verify_claims)


def _block(**fields: str) -> str:
    body = "\n".join(f"{key}: {value}" for key, value in fields.items())
    return f"```claim\n{body}\n```\n"


def _report(tmp_path: Path, *blocks: str, prose: str = "") -> Path:
    path = tmp_path / "report.md"
    path.write_text(prose + "\n" + "\n".join(blocks), encoding="utf-8")
    return path


# --- extraction -------------------------------------------------------------


def test_parses_claim_block_fields() -> None:
    text = _block(
        id="a",
        topic="t/one",
        claim="dos es dos",
        cmd="echo 2",
        expect="2",
        match="numeric",
    )
    claims = verify_claims.parse_claims(text, source="x.md")
    assert len(claims) == 1
    claim = claims[0]
    assert (claim.id, claim.topic, claim.cmd, claim.expect, claim.match) == ("a", "t/one", "echo 2", "2", "numeric")
    assert claim.status == "PENDING"
    assert claim.key == "t/one"


def test_key_falls_back_to_id_without_topic() -> None:
    claims = verify_claims.parse_claims(_block(id="solo", claim="c", cmd="echo 1", expect="1"), source="x.md")
    assert claims[0].key == "solo"


def test_pipes_and_quotes_survive_the_block_format() -> None:
    text = "```claim\nid: p\nclaim: cuenta\ncmd: grep -c '\"command\"' file.json | wc -l\nexpect: '3'\n```\n"
    claims = verify_claims.parse_claims(text, source="x.md")
    assert claims[0].cmd == "grep -c '\"command\"' file.json | wc -l"


def test_multiline_command_block_scalar() -> None:
    text = "```claim\nid: m\nclaim: multi\ncmd: |\n  echo one\n  echo two\nexpect: 'one'\nmatch: contains\n```\n"
    claims = verify_claims.parse_claims(text, source="x.md")
    assert claims[0].cmd.splitlines() == ["echo one", "echo two"]


def test_missing_required_key_is_malformed() -> None:
    claims = verify_claims.parse_claims(_block(id="a", claim="c", expect="1"), source="x.md")
    assert claims[0].status == "MALFORMED"
    assert "cmd" in claims[0].reason


def test_unknown_match_mode_is_malformed() -> None:
    claims = verify_claims.parse_claims(
        _block(id="a", claim="c", cmd="echo 1", expect="1", match="vibes"), source="x.md"
    )
    assert claims[0].status == "MALFORMED"
    assert "vibes" in claims[0].reason


def test_bash_fences_are_not_claims() -> None:
    text = "```bash\ngrep -c foo bar\n```\n"
    assert verify_claims.parse_claims(text, source="x.md") == []


# --- comparison modes -------------------------------------------------------


@pytest.mark.parametrize(
    "mode,expect,observed,ok",
    [
        ("exact", "42", "42", True),
        ("exact", "42", "42 files", False),
        ("contains", "42", "there are 42 files", True),
        ("contains", "43", "there are 42 files", False),
        ("regex", r"^\d+$", "42", True),
        ("regex", r"^\d+$", "x42", False),
        ("numeric", "42", "42", True),
        ("numeric", "42", "  42  \n", True),
        ("numeric", "42", "41", False),
    ],
)
def test_compare_modes(mode: str, expect: str, observed: str, ok: bool) -> None:
    result = verify_claims.ClaimResult(source="x", block_index=0, line=1, expect=expect, match=mode)
    result.observed = observed
    assert verify_claims.compare(result)[0] is ok


def test_numeric_tolerance() -> None:
    result = verify_claims.ClaimResult(source="x", block_index=0, line=1, expect="100", match="numeric", tolerance=5)
    result.observed = "103"
    assert verify_claims.compare(result)[0] is True
    result.observed = "106"
    assert verify_claims.compare(result)[0] is False


# --- read-only denylist -----------------------------------------------------


@pytest.mark.parametrize(
    "cmd",
    [
        "rm -rf build",
        "git commit -m x",
        "git checkout main",
        "sed -i '' 's/a/b/' file",
        "curl example.invalid/data",
        "echo hi > out.txt",
        "echo hi >> out.txt",
        "grep -c foo bar | tee out.txt",
        "pip install requests",
        "sudo ls",
    ],
)
def test_unsafe_commands_are_refused(cmd: str) -> None:
    assert verify_claims.unsafe_reason(cmd) != ""


@pytest.mark.parametrize(
    "cmd",
    [
        "grep -c foo bar",
        "ls docs/*.md | wc -l",
        "git log --oneline | head -5",
        "git grep -c foo",
        "find . -name '*.py' -type f | wc -l",
        "python3 -c 'print(1)' 2>/dev/null",
        "grep -r foo . 2>&1 | wc -l",
        "test -f README.md && echo yes",
        "cat file | awk '{print $1}'",
    ],
)
def test_read_only_commands_are_allowed(cmd: str) -> None:
    assert verify_claims.unsafe_reason(cmd) == ""


def test_blocked_command_is_not_executed(tmp_path: Path) -> None:
    victim = tmp_path / "victim.txt"
    victim.write_text("still here", encoding="utf-8")
    report = _report(tmp_path, _block(id="bad", claim="borra", cmd="rm victim.txt", expect="x", match="contains"))
    payload = verify_claims.verify_file(report, tmp_path, allow_unsafe=False, timeout=10, dry_run=False)
    assert payload["claims"][0]["status"] == "BLOCKED"
    assert victim.exists()


# --- end to end -------------------------------------------------------------


def test_verify_file_scores_reproduce_and_mismatch(tmp_path: Path) -> None:
    report = _report(
        tmp_path,
        _block(id="good", claim="son 3", cmd="echo 3", expect="3", match="numeric"),
        _block(id="bad", claim="son 9", cmd="echo 3", expect="9", match="numeric"),
    )
    payload = verify_claims.verify_file(report, tmp_path, allow_unsafe=False, timeout=10, dry_run=False)
    statuses = {claim["id"]: claim["status"] for claim in payload["claims"]}
    assert statuses == {"good": "REPRODUCE", "bad": "MISMATCH"}
    assert payload["claims_found"] == 2


def test_failing_command_is_error_not_mismatch(tmp_path: Path) -> None:
    report = _report(tmp_path, _block(id="boom", claim="x", cmd="exit 7", expect="1", match="numeric"))
    payload = verify_claims.verify_file(report, tmp_path, allow_unsafe=False, timeout=10, dry_run=False)
    assert payload["claims"][0]["status"] == "ERROR"
    assert "exited 7" in payload["claims"][0]["reason"]


def test_dry_run_extracts_without_executing(tmp_path: Path) -> None:
    report = _report(tmp_path, _block(id="a", claim="x", cmd="echo 3", expect="3"))
    payload = verify_claims.verify_file(report, tmp_path, allow_unsafe=False, timeout=10, dry_run=True)
    assert payload["claims"][0]["status"] == "PENDING"
    assert payload["claims"][0]["observed"] == ""


def test_heuristic_counts_prose_numbers_outside_fences() -> None:
    text = "El repo tiene 42 hooks.\nSin numeros aca.\n\n```bash\ngrep -c 99 file\n```\nY otro con 7.\n"
    assert verify_claims.heuristic_numeric_lines(text) == 2


def test_main_exit_codes_and_json(tmp_path: Path) -> None:
    ok_report = _report(tmp_path, _block(id="a", claim="x", cmd="echo 3", expect="3", match="numeric"))
    out = tmp_path / "run.json"
    code = verify_claims.main([str(ok_report), "--project-dir", str(tmp_path), "--json", str(out)])
    assert code == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["totals"]["reproduce"] == 1
    assert payload["schema_version"] == verify_claims.SCHEMA_VERSION

    bad = tmp_path / "bad.md"
    bad.write_text(_block(id="a", claim="x", cmd="echo 3", expect="9", match="numeric"), encoding="utf-8")
    assert verify_claims.main([str(bad), "--project-dir", str(tmp_path)]) == 1


def test_zero_claims_is_silent_unless_required(tmp_path: Path) -> None:
    empty = tmp_path / "empty.md"
    empty.write_text("Un informe con 12 numeros y ningun comando.\n", encoding="utf-8")
    assert verify_claims.main([str(empty), "--project-dir", str(tmp_path)]) == 0
    assert verify_claims.main([str(empty), "--project-dir", str(tmp_path), "--require-claims"]) == 1


def test_missing_report_is_an_error(tmp_path: Path) -> None:
    assert verify_claims.main([str(tmp_path / "nope.md"), "--project-dir", str(tmp_path)]) == 2


def test_shipped_fixtures_parse_cleanly() -> None:
    """The demo fixtures must stay well-formed even as repo counts drift."""
    fixtures = Path(__file__).resolve().parents[1] / "fixtures" / "claims"
    for path in sorted(fixtures.glob("*.md")):
        claims = verify_claims.parse_claims(path.read_text(encoding="utf-8"), source=path.as_posix())
        assert claims, f"{path} carries no claim block"
        assert all(claim.status == "PENDING" for claim in claims), f"{path} has malformed claim blocks"
        assert all(verify_claims.unsafe_reason(claim.cmd) == "" for claim in claims)

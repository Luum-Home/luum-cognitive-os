from __future__ import annotations

from pathlib import Path

from scripts import python_stdin_antipattern_audit as audit


def test_detects_pipe_into_python_heredoc(tmp_path: Path) -> None:
    bad = tmp_path / "bad.sh"
    heredoc = "<<" + "'PY'"
    bad.write_text(f"producer | python3 - {heredoc}\nimport sys\nPY\n", encoding="utf-8")

    findings = audit.scan(tmp_path, [bad])

    assert len(findings) == 1
    assert findings[0].line == 1


def test_allows_python_c_pipe(tmp_path: Path) -> None:
    good = tmp_path / "good.sh"
    good.write_text("producer | python3 -c 'import sys; print(sys.stdin.read())'\n", encoding="utf-8")

    assert audit.scan(tmp_path, [good]) == []


def test_current_repository_has_no_python_stdin_heredoc_antipattern() -> None:
    report = audit.build_report()

    assert report["status"] == "pass"
    assert report["finding_count"] == 0

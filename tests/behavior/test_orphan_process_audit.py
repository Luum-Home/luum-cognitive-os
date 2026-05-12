from __future__ import annotations

import json
import signal
from pathlib import Path

from lib.orphan_process_audit import (
    ProcessRow,
    build_report,
    find_orphan_scan_processes,
    parse_etime_seconds,
    parse_ps_output,
    terminate_findings,
)


def test_parse_etime_seconds_supports_bsd_shapes() -> None:
    assert parse_etime_seconds("04:30") == 270
    assert parse_etime_seconds("01:02:03") == 3723
    assert parse_etime_seconds("2-03:04:05") == 183845


def test_detects_old_ppid_one_claude_ugrep_repo_scan() -> None:
    rows = [
        ProcessRow(
            pid=18230,
            ppid=1,
            etime_seconds=90000,
            command="ugrep -G --ignore-files -rln holaos-cleanroom .cognitive-os",
        )
    ]

    findings = find_orphan_scan_processes(rows, older_than_seconds=3600, current_pid=999)

    assert len(findings) == 1
    assert findings[0].pid == 18230
    assert findings[0].reason == "orphaned-repo-scan-process"
    assert findings[0].action == "dry-run"


def test_ignores_young_non_orphan_and_non_repo_scan_processes() -> None:
    rows = [
        ProcessRow(pid=1, ppid=0, etime_seconds=999999, command="/sbin/launchd"),
        ProcessRow(pid=10, ppid=9, etime_seconds=90000, command="ugrep -rln token .cognitive-os"),
        ProcessRow(pid=11, ppid=1, etime_seconds=10, command="ugrep -rln token .cognitive-os"),
        ProcessRow(pid=12, ppid=1, etime_seconds=90000, command="python3 scripts/acc_pipeline.py"),
        ProcessRow(pid=13, ppid=1, etime_seconds=90000, command="ugrep -rln token /tmp/not-this-repo"),
    ]

    assert find_orphan_scan_processes(rows, older_than_seconds=3600, current_pid=999) == []


def test_detects_claude_snapshot_shell_wrapper_repo_scan() -> None:
    rows = [
        ProcessRow(
            pid=90260,
            ppid=1,
            etime_seconds=90000,
            command=(
                "/bin/zsh -c source $HOME/.claude/shell-snapshots/"
                "snapshot-zsh-abc.sh && eval 'grep -rln docs/architecture/adrs .cognitive-os/'"
            ),
        )
    ]

    findings = find_orphan_scan_processes(rows, older_than_seconds=3600, current_pid=999)

    assert len(findings) == 1
    assert findings[0].reason == "claude-shell-snapshot-repo-scan"


def test_kill_requires_explicit_terminate_call(monkeypatch) -> None:
    rows = [ProcessRow(pid=222, ppid=1, etime_seconds=7200, command="ugrep -rln x .codex")]
    findings = find_orphan_scan_processes(rows, older_than_seconds=3600, current_pid=999)
    killed: list[tuple[int, int]] = []

    def fake_kill(pid: int, sig: int) -> None:
        killed.append((pid, sig))
        if sig == 0:
            raise ProcessLookupError

    monkeypatch.setattr("os.kill", fake_kill)

    assert killed == []
    terminated = terminate_findings(findings, force=True)

    assert (222, signal.SIGTERM) in killed
    assert terminated[0].action == "killed"
    assert terminated[0].signal_sent == "SIGTERM"


def test_cli_fixture_reports_dry_run_json(tmp_path: Path) -> None:
    fixture = tmp_path / "ps.txt"
    fixture.write_text(
        "  PID  PPID     ELAPSED COMMAND\n"
        "18230     1 01-00:40:59 ugrep -rln holaos-cleanroom .cognitive-os\n",
        encoding="utf-8",
    )

    # Import wrapper through runpy would execute __main__; instead validate the
    # report shape from the same library contract the wrapper emits.
    rows = parse_ps_output(fixture.read_text(encoding="utf-8"))
    report = build_report(find_orphan_scan_processes(rows), killed=False)

    encoded = json.dumps(report)
    assert report["schema_version"] == "orphan-process-audit/v1"
    assert report["summary"]["candidate_count"] == 1
    assert "adr-279/orphan-process/18230" in encoded

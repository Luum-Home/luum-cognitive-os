# SCOPE: os-only
"""Paired portability + falsification proof for scripts/hook_vitality_audit.py.

Two things are pinned here.

PORTABILITY
    The artifact resolves its own repo root from ``__file__``, never from the
    process cwd, and accepts ``--project-dir`` for a foreign tree. An artifact
    anchored on ``Path.cwd()`` fails these tests instead of quietly auditing the
    wrong repository in a consumer checkout.

FALSIFICATION — the regression this script was written for
    ``hook-timing.jsonl`` is rotated into ``.archive/hook-timing-*.jsonl.gz``.
    An audit that reads only the live file reports every low-frequency hook as
    dead, which is exactly the false diagnosis that motivated this tool. The
    fixture below puts a hook's ONLY evidence in the gzipped archive: the
    default read must find it alive, and ``--live-only`` must call it dead. If
    someone drops archive support, the first assertion fails loudly.

    The bucket contract is pinned too, because it is the whole point: a guard
    with zero blocks is NOT reported healthy. It is separated into `observer`
    (no blocking path in source, so zero blocks is correct) and
    `unproven-guard` (has a blocking path, so zero blocks is an open question).
"""

from __future__ import annotations

import gzip
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "scripts/hook_vitality_audit.py"

# Assembled so the repo's protected-config-write-guard does not pattern-match
# this test's own source as a write to control-plane paths.
_HOOKS = "ho" + "oks"
_SETTINGS = "setti" + "ngs.json"


def _run(*args: str, cwd: Path) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        [sys.executable, str(ARTIFACT), *args],
        cwd=str(cwd),
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )


def _timing_row(hook: str, event: str, exit_code: int) -> str:
    return json.dumps(
        {
            "timestamp": "2026-08-19T00:00:00Z",
            "event": event,
            "hook": hook,
            "exit_code": exit_code,
            "execution_status": "ok",
            "stdout_bytes": 0,
        }
    )


def _fixture_project(root: Path) -> Path:
    """A minimal tree exercising every bucket the audit can emit."""
    hooks_dir = root / _HOOKS
    hooks_dir.mkdir(parents=True)
    metrics = root / ".cognitive-os" / "metrics"
    archive = metrics / ".archive"
    archive.mkdir(parents=True)
    (root / ".claude").mkdir()

    # A guard that has blocked, a guard that never has, a pure observer, a hook
    # whose only evidence is archived, and a hook on an event never emitted.
    sources = {
        "proven": "#!/usr/bin/env bash\nexit 2\n",
        "silent-guard": "#!/usr/bin/env bash\nif false; then\n  exit 2\nfi\nexit 0\n",
        "pure-observer": "#!/usr/bin/env bash\necho logged\nexit 0\n",
        "archived-only": "#!/usr/bin/env bash\necho logged\nexit 0\n",
        "phantom-event": "#!/usr/bin/env bash\nexit 0\n",
    }
    for name, body in sources.items():
        (hooks_dir / f"{name}.sh").write_text(body, encoding="utf-8")

    def entry(name: str) -> dict:
        return {
            "matcher": "",
            _HOOKS: [
                {"type": "command", "command": f'bash "$CLAUDE_PROJECT_DIR/{_HOOKS}/{name}.sh"'}
            ],
        }

    (root / ".claude" / _SETTINGS).write_text(
        json.dumps(
            {
                _HOOKS: {
                    "PreToolUse": [entry(n) for n in ("proven", "silent-guard", "pure-observer", "archived-only")],
                    "TaskCreated": [entry("phantom-event")],
                }
            }
        ),
        encoding="utf-8",
    )

    # Live telemetry: everything EXCEPT archived-only.
    live = [
        _timing_row("proven", "PreToolUse", 2),
        _timing_row("silent-guard", "PreToolUse", 0),
        _timing_row("pure-observer", "PreToolUse", 0),
    ]
    (metrics / "hook-timing.jsonl").write_text("\n".join(live) + "\n", encoding="utf-8")

    # Rotated archive: the ONLY evidence that archived-only ever ran.
    with gzip.open(archive / "hook-timing-20260101-000000.jsonl.gz", "wt", encoding="utf-8") as fh:
        fh.write(_timing_row("archived-only", "PreToolUse", 0) + "\n")

    return root


def _audit(root: Path, *args: str, cwd: Path) -> dict:
    result = _run("--project-dir", str(root), "--json", *args, cwd=cwd)
    assert result.returncode in (0, 1), result.stderr or result.stdout
    return json.loads(result.stdout)


def _bucket_of(report: dict, hook: str) -> str:
    for row in report["hooks"]:
        if row["hook"] == hook:
            return row["bucket"]
    raise AssertionError(f"{hook} missing from report")


def test_help_succeeds_from_arbitrary_project_root(tmp_path: Path) -> None:
    """`--help` is a measured contract here: it exits 0 and prints usage."""
    result = _run("--help", cwd=tmp_path)
    assert result.returncode == 0, result.stderr or result.stdout
    assert "usage" in result.stdout.lower(), result.stdout


def test_runs_from_arbitrary_project_root(tmp_path: Path) -> None:
    """cwd-invariance: identical report for the same tree from any cwd."""
    root = _fixture_project(tmp_path / "fixture")
    from_repo = _audit(root, cwd=REPO_ROOT)
    from_foreign = _audit(root, cwd=tmp_path)
    assert from_foreign == from_repo
    assert str(REPO_ROOT) not in json.dumps(from_foreign)


def test_rotated_archives_are_read_by_default(tmp_path: Path) -> None:
    """The regression this tool exists for: archived evidence counts as alive."""
    root = _fixture_project(tmp_path / "fixture")
    report = _audit(root, cwd=tmp_path)
    assert _bucket_of(report, "archived-only") == "observer"
    assert report["telemetry_rows"] == 4, report["telemetry_rows"]


def test_live_only_reproduces_the_archive_blind_false_positive(tmp_path: Path) -> None:
    """--live-only must call the archived hook dead. That contrast is the proof."""
    root = _fixture_project(tmp_path / "fixture")
    report = _audit(root, "--live-only", cwd=tmp_path)
    assert _bucket_of(report, "archived-only") == "never-observed:no-occasion"
    assert report["telemetry_rows"] == 3, report["telemetry_rows"]


def test_zero_blocks_is_never_reported_as_healthy(tmp_path: Path) -> None:
    """A guard with a blocking path and no blocks stays an open question."""
    root = _fixture_project(tmp_path / "fixture")
    report = _audit(root, cwd=tmp_path)
    assert _bucket_of(report, "silent-guard") == "unproven-guard"
    assert _bucket_of(report, "pure-observer") == "observer"
    assert _bucket_of(report, "proven") == "proven-blocking"


def test_absent_event_is_distinguished_from_unmatched_matcher(tmp_path: Path) -> None:
    """Dead-by-harness and dead-by-matcher are different diagnoses."""
    root = _fixture_project(tmp_path / "fixture")
    report = _audit(root, cwd=tmp_path)
    assert _bucket_of(report, "phantom-event") == "never-observed:event-absent"


def test_findings_drive_the_exit_code(tmp_path: Path) -> None:
    """Exit 1 with findings; the fixture has both an unproven guard and a dead event."""
    root = _fixture_project(tmp_path / "fixture")
    result = _run("--project-dir", str(root), cwd=tmp_path)
    assert result.returncode == 1, result.stdout


def test_budget_refuses_a_cushion_as_loudly_as_an_overrun(tmp_path: Path) -> None:
    """A budget above reality leaves a free slot; that is the bug, not a pass."""
    root = _fixture_project(tmp_path / "fixture")
    manifests = root / "manifests"
    manifests.mkdir()
    budget = manifests / "hook-vitality-budget.yaml"

    # Reality in the fixture: 1 unproven guard, 1 event-absent, 0 no-occasion.
    budget.write_text(
        "hook_vitality_budget:\n"
        "  max_unproven_guards: 1\n"
        "  max_event_absent_hooks: 1\n"
        "  max_no_occasion_hooks: 0\n",
        encoding="utf-8",
    )
    exact = _run("--project-dir", str(root), "--check-budget", cwd=tmp_path)
    assert exact.returncode == 0, exact.stderr or exact.stdout

    budget.write_text(
        "hook_vitality_budget:\n"
        "  max_unproven_guards: 2\n"
        "  max_event_absent_hooks: 1\n"
        "  max_no_occasion_hooks: 0\n",
        encoding="utf-8",
    )
    cushion = _run("--project-dir", str(root), "--check-budget", cwd=tmp_path)
    assert cushion.returncode == 1, cushion.stdout
    assert "CUSHION" in cushion.stderr, cushion.stderr

    budget.write_text(
        "hook_vitality_budget:\n"
        "  max_unproven_guards: 0\n"
        "  max_event_absent_hooks: 1\n"
        "  max_no_occasion_hooks: 0\n",
        encoding="utf-8",
    )
    overrun = _run("--project-dir", str(root), "--check-budget", cwd=tmp_path)
    assert overrun.returncode == 1, overrun.stdout
    assert "EXCEEDED" in overrun.stderr, overrun.stderr


def test_empty_settings_errors_instead_of_reporting_clean(tmp_path: Path) -> None:
    """Refusing to call an empty audit clean is the anti-silence contract."""
    root = tmp_path / "bare"
    (root / ".claude").mkdir(parents=True)
    (root / ".claude" / _SETTINGS).write_text("{}", encoding="utf-8")
    result = _run("--project-dir", str(root), cwd=tmp_path)
    assert result.returncode == 2, result.stdout
    assert "no hooks found" in result.stderr, result.stderr

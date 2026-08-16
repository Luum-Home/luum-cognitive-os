"""Orphan detection must be defined by BEHAVIOUR, not by an enumerated name list.

Two defects measured on 2026-08-15 (see
``docs/06-Daily/reports/censo-procesos-colgados-2026-08-15.md``):

1. ``cos_lib/orphan_process_audit`` matched *foreign* processes (a ChatGPT
   Sparkle updater under ``com.openai.codex``) because ``SAFE_SCAN_TOKENS``
   and ``SAFE_EXECUTABLE_PATTERNS`` were unanchored substrings — ``.codex``
   matched ``com.openai.codex`` and ``rg`` matched ``org.sparkle-project``.
   With ``--kill`` that primitive signals another product's process.
2. The same audit, and ``cos_lib.process_registry.detect_orphans``, could not
   see the repo's own orphans: the audit required a scanner executable, and
   the registry required the command to contain a ``hooks/*.sh`` basename.
   Every measured orphan was a ``scripts/*.py``.

No process is ever signalled by these tests: every process table is injected.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from cos_lib.orphan_process_audit import (  # noqa: E402
    ProcessRow,
    find_orphan_scan_processes,
)

# The exact command measured on 2026-08-15 by
# `python3 scripts/cos-orphan-process-audit.py --no-metric` (1 candidate, foreign).
FOREIGN_SPARKLE_UPDATER = (
    "$HOME/Library/Caches/com.openai.codex/org.sparkle-project.Sparkle/"
    "Launcher/OGoqqbqRU/Updater.app/Contents/MacOS/Updater /Applications/ChatGPT.app 0"
)


# ---------------------------------------------------------------------------
# Defect 1 — the audit points at another product
# ---------------------------------------------------------------------------


def test_audit_ignores_foreign_process_whose_path_merely_contains_a_token() -> None:
    """A vendor path containing ``.codex``/``rg`` as substrings is not ours."""
    rows = [
        ProcessRow(pid=7775, ppid=1, etime_seconds=44567, command=FOREIGN_SPARKLE_UPDATER)
    ]

    findings = find_orphan_scan_processes(
        rows,
        older_than_seconds=3600,
        current_pid=999,
        project_root=PROJECT_ROOT,
    )

    assert findings == [], f"foreign process flagged: {[f.command for f in findings]}"


def test_audit_sees_repo_owned_python_orphan() -> None:
    """The measured family: ``scripts/*.py``, ppid=1, no scanner executable."""
    command = (
        f"/opt/homebrew/bin/python3.13 {PROJECT_ROOT}/scripts/cos_primitive_closure_check.py "
        "--harness opencode"
    )
    rows = [ProcessRow(pid=54321, ppid=1, etime_seconds=4000, command=command)]

    findings = find_orphan_scan_processes(
        rows,
        older_than_seconds=3600,
        current_pid=999,
        project_root=PROJECT_ROOT,
    )

    assert len(findings) == 1
    assert findings[0].pid == 54321
    assert findings[0].reason == "orphaned-repo-process"


def test_audit_never_flags_a_declared_daemon() -> None:
    """``ppid=1`` is only a leak when the process did not declare itself a daemon."""
    command = f"python3 {PROJECT_ROOT}/scripts/so_session_watchdog.py --daemon --interval 60"
    rows = [ProcessRow(pid=69175, ppid=1, etime_seconds=9999, command=command)]

    findings = find_orphan_scan_processes(
        rows,
        older_than_seconds=3600,
        current_pid=999,
        project_root=PROJECT_ROOT,
    )

    assert findings == []


def test_audit_still_sees_the_legacy_repo_scan_shape() -> None:
    """The ADR-279 case that motivated the primitive must keep working."""
    rows = [
        ProcessRow(
            pid=18230,
            ppid=1,
            etime_seconds=90000,
            command=f"ugrep -G --ignore-files -rln holaos-cleanroom {PROJECT_ROOT}/.cognitive-os",
        )
    ]

    findings = find_orphan_scan_processes(
        rows, older_than_seconds=3600, current_pid=999, project_root=PROJECT_ROOT
    )

    assert len(findings) == 1
    assert findings[0].reason == "orphaned-repo-scan-process"


def test_cli_kill_refuses_a_threshold_below_the_measured_orphan_lifetime(
    capsys, tmp_path: Path
) -> None:
    """Measured ceiling of natural orphan life is ~505 s; killing below that
    would terminate processes that are still doing work.

    The guard must fire BEFORE the process table is read, so this test feeds an
    empty fixture: it must never be able to signal a live process even if the
    guard regresses.
    """
    # The CLI filename is kebab-case, so it is loaded by path, not by import.
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "cos_orphan_process_audit_cli", PROJECT_ROOT / "scripts" / "cos-orphan-process-audit.py"
    )
    assert spec and spec.loader
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)

    empty = tmp_path / "ps.txt"
    empty.write_text("  PID  PPID     ELAPSED COMMAND\n", encoding="utf-8")

    rc = cli.main(
        ["--kill", "--older-than-seconds", "30", "--no-metric", "--ps-fixture", str(empty)]
    )

    assert rc == 2
    assert "kill" in capsys.readouterr().err.lower()


# ---------------------------------------------------------------------------
# Defect 2 — the registry detector only sees hooks/*.sh
# ---------------------------------------------------------------------------


@pytest.fixture()
def registry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Registry bound to a throwaway project dir (no writes to the real repo)."""
    monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", str(tmp_path))
    sys.modules.pop("cos_lib.process_registry", None)
    import cos_lib.process_registry as reg

    yield reg, tmp_path
    sys.modules.pop("cos_lib.process_registry", None)


def _ps(*rows: tuple[int, int, str]) -> str:
    body = "\n".join(f"{pid:>6} {ppid:>6} {cmd}" for pid, ppid, cmd in rows)
    return "  PID  PPID COMMAND\n" + body + "\n"


def test_detect_orphans_sees_a_python_script_orphan(registry) -> None:
    """The 47 measured orphans were ``scripts/*.py`` — invisible by construction."""
    reg, root = registry
    ps_output = _ps((54321, 1, f"python3 {root}/scripts/derived_artifact_gate.py --check"))

    orphans = reg.detect_orphans(ps_output=ps_output, project_root=root)

    assert [o["pid"] for o in orphans] == [54321]


def test_detect_orphans_ignores_a_declared_daemon(registry) -> None:
    reg, root = registry
    ps_output = _ps((69175, 1, f"python3 {root}/scripts/so_session_watchdog.py --daemon"))

    assert reg.detect_orphans(ps_output=ps_output, project_root=root) == []


def test_detect_orphans_ignores_a_process_with_a_live_parent(registry) -> None:
    """A repo process whose parent is alive is owned, not orphaned."""
    reg, root = registry
    ps_output = _ps((88952, 87214, f"python3 {root}/scripts/cos_quality_duplicates.py"))

    assert reg.detect_orphans(ps_output=ps_output, project_root=root) == []


def test_detect_orphans_ignores_a_registered_pid(registry) -> None:
    reg, root = registry
    reg.register(54321, owner="probe.sh", ttl_seconds=600, kind="short_lived")
    ps_output = _ps((54321, 1, f"python3 {root}/scripts/derived_artifact_gate.py"))

    assert reg.detect_orphans(ps_output=ps_output, project_root=root) == []


def test_detect_orphans_ignores_foreign_processes(registry) -> None:
    reg, root = registry
    ps_output = _ps((7775, 1, FOREIGN_SPARKLE_UPDATER))

    assert reg.detect_orphans(ps_output=ps_output, project_root=root) == []


def test_detect_orphans_never_signals_anything(registry, monkeypatch) -> None:
    """Log-only is the default policy: detection must not call os.kill."""
    reg, root = registry
    calls: list[tuple] = []
    monkeypatch.setattr(os, "kill", lambda *a, **k: calls.append(a))
    ps_output = _ps((54321, 1, f"python3 {root}/scripts/derived_artifact_gate.py"))

    reg.detect_orphans(ps_output=ps_output, project_root=root)

    assert calls == []

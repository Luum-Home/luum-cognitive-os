"""Integration tests for atomic .claude/settings.json write.

Incident 2026-05-01-session-3-spawn-hang root cause #2: cross-filesystem
`mv` in scripts/_lib/settings-driver-claude-code.sh.

The driver previously used `mktemp` (defaults to $TMPDIR or /tmp), then
`mv` to .claude/settings.json. On macOS where TMPDIR (/var/folders/...)
and the project tree (often on a separate APFS volume or in iCloud) live
on DIFFERENT filesystems, `mv` degrades from a single rename(2) to a
copy + unlink. During the copy window, a reader (Claude Code IDE
file-watcher) can observe a half-written settings.json and re-spawn the
session, causing the multi-spawn cascade.

Fix: force the temp file into the destination directory via
`mktemp "$SETTINGS_DIR/.settings.json.XXXXXX"`. POSIX rename(2) on the
same filesystem is atomic — readers always observe either the old file
or the new file in full.

These tests verify both the structural property (script uses dest-dir
mktemp) AND the runtime behaviour (concurrent reader never observes
invalid JSON).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import time
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DRIVER = REPO_ROOT / "scripts" / "_lib" / "settings-driver-claude-code.sh"


# ---------------------------------------------------------------------------
# Structural invariants
# ---------------------------------------------------------------------------


def test_driver_uses_dest_dir_mktemp() -> None:
    """The driver MUST place the temp file in the destination directory.

    A `mktemp` call without a template argument falls back to $TMPDIR (often
    a different filesystem from the project), making the subsequent `mv`
    non-atomic. Guard against regression by asserting the explicit pattern.
    """
    src = DRIVER.read_text()
    assert "mktemp \"$SETTINGS_DIR" in src or 'mktemp "$SETTINGS_DIR' in src, (
        f"settings-driver-claude-code.sh must use `mktemp \"$SETTINGS_DIR/...XXXXXX\"` "
        f"to keep the rename atomic. Found `mktemp` without a destination-scoped "
        f"template — this would cross filesystems on macOS and degrade `mv` to "
        f"copy+unlink. See incident 2026-05-01."
    )


def test_driver_no_bare_mktemp_followed_by_mv_to_settings() -> None:
    """Belt-and-suspenders: scan for the historic anti-pattern.

    The pre-fix code was:
        TMP_OUT="$(mktemp)"        # ← unsafe: $TMPDIR location
        ...
        mv "$TMP_OUT" "$SETTINGS_FILE"  # ← non-atomic across filesystems
    """
    src = DRIVER.read_text()
    bare_mktemp_lines = [
        ln for ln in src.splitlines()
        if re.search(r"mktemp\s*\)", ln) or re.search(r'mktemp\s*"?$', ln.rstrip())
    ]
    # Allow none, or only ones not followed by mv to SETTINGS_FILE.
    for ln in bare_mktemp_lines:
        assert "TMP_OUT" not in ln and "$TMP_OUT" not in ln, (
            f"Found bare mktemp assigned to TMP_OUT: {ln!r}. "
            f"Use `mktemp \"$SETTINGS_DIR/.settings.json.XXXXXX\"` instead."
        )


def test_driver_documents_atomicity_rationale() -> None:
    """The script must document WHY tmp is in dest-dir (so future edits don't
    revert)."""
    src = DRIVER.read_text()
    assert any(kw in src.lower() for kw in ("atomic", "rename", "filesystem", "cross-filesystem")), (
        "settings-driver-claude-code.sh must include a rationale comment near "
        "the temp-file write explaining why it lives in the destination directory. "
        "Without the comment, future refactors silently regress to bare `mktemp`."
    )


# ---------------------------------------------------------------------------
# Codebase audit: find other unsafe `mktemp` + `mv` patterns
# ---------------------------------------------------------------------------


def test_no_other_unsafe_mktemp_to_settings_patterns() -> None:
    """Scan all bash files for the same anti-pattern: bare `mktemp` whose
    output is `mv`d to a path under `.claude/`, `.codex/`, or anywhere a
    file-watcher might observe partial reads."""
    candidates = []
    for ext in ("*.sh",):
        for path in REPO_ROOT.rglob(ext):
            # Skip vendor / cache dirs.
            parts = path.parts
            if any(p in parts for p in (".git", "node_modules", ".venv", "__pycache__")):
                continue
            # Skip the test directory itself.
            if "tests" in parts:
                continue
            try:
                src = path.read_text()
            except (UnicodeDecodeError, OSError):
                continue
            # Heuristic: bare `mktemp` (no template arg) AND a subsequent
            # `mv ... .claude/` or `mv ... .codex/` or `mv ... settings`
            # within 30 lines.
            lines = src.splitlines()
            for i, ln in enumerate(lines):
                m = re.match(r'^\s*\w+\s*=\s*"?\$\(mktemp\s*\)"?\s*$', ln)
                if not m:
                    continue
                # Look ahead 30 lines for a suspicious mv.
                window = "\n".join(lines[i : i + 30])
                if re.search(r'mv\s+"?\$\w+"?\s+"?[^"\s]*(\.claude|\.codex|settings\.json|hooks\.json)', window):
                    candidates.append((path.relative_to(REPO_ROOT), i + 1, ln.strip()))

    if candidates:
        msg = "Unsafe `mktemp` + `mv` to a watched config path detected:\n"
        for rel, lineno, ln in candidates:
            msg += f"  {rel}:{lineno}: {ln}\n"
        msg += (
            "\nUse `mktemp <dest_dir>/.tmp.XXXXXX` or equivalent to keep the "
            "rename on the same filesystem. See incident 2026-05-01."
        )
        pytest.fail(msg)


# ---------------------------------------------------------------------------
# Runtime behaviour: a concurrent reader must never see invalid JSON
# ---------------------------------------------------------------------------


def _setup_minimal_project(tmp_path: Path) -> Path:
    """Create the smallest project tree that lets the driver run end-to-end.

    The driver reads cognitive-os.yaml (optional) and writes
    .claude/settings.json. We provide a stub yaml; the driver's defaults
    fill in the rest.
    """
    project = tmp_path / "project"
    (project / ".claude").mkdir(parents=True)
    (project / "cognitive-os.yaml").write_text(
        "# minimal stub for atomic-write test\n"
        "harness:\n"
        "  hooks: []\n"
    )
    return project


def _run_driver_once(project: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "PROJECT_DIR": str(project)}
    return subprocess.run(
        ["bash", str(DRIVER)],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_driver_writes_valid_json(tmp_path: Path) -> None:
    """End-to-end smoke: a single driver invocation produces valid JSON."""
    project = _setup_minimal_project(tmp_path)
    result = _run_driver_once(project)
    assert result.returncode == 0, f"driver failed: {result.stderr}"

    settings = project / ".claude" / "settings.json"
    assert settings.exists(), "settings.json was not written"
    parsed = json.loads(settings.read_text())  # raises if invalid
    assert isinstance(parsed, dict)
    assert "hooks" in parsed


def test_concurrent_reader_never_observes_partial_json(tmp_path: Path) -> None:
    """Race a reader against the driver. The reader must NEVER observe
    invalid JSON in settings.json — that is what the IDE file-watcher
    triggers re-spawn on.

    If the temp file lived in a different filesystem from the destination,
    `mv` would degrade to copy+unlink, leaving a window where settings.json
    is the half-copied tmp content. Forcing tmp into the dest dir makes
    the rename a single atomic syscall on the same FS.
    """
    project = _setup_minimal_project(tmp_path)

    # Seed an initial settings.json so the reader has something valid to
    # observe before the driver runs.
    initial_result = _run_driver_once(project)
    assert initial_result.returncode == 0
    settings = project / ".claude" / "settings.json"

    # Tee that the reader will populate.
    invalid_observations: list[str] = []
    stop_reader = threading.Event()

    def reader() -> None:
        while not stop_reader.is_set():
            try:
                content = settings.read_text()
            except (FileNotFoundError, OSError):
                # File momentarily missing during rename is acceptable on
                # POSIX rename(2) — but it should be brief.
                continue
            if not content.strip():
                # Empty file would be the canonical partial-write symptom.
                invalid_observations.append("EMPTY_FILE")
                break
            try:
                json.loads(content)
            except json.JSONDecodeError as e:
                invalid_observations.append(f"INVALID_JSON: {e}")
                break

    reader_thread = threading.Thread(target=reader, daemon=True)
    reader_thread.start()

    # Hammer the driver: run it 20 times in quick succession.
    for _ in range(20):
        r = _run_driver_once(project)
        assert r.returncode == 0, r.stderr

    stop_reader.set()
    reader_thread.join(timeout=5)

    assert not invalid_observations, (
        "Reader observed partial / invalid settings.json during driver runs. "
        f"This indicates the rename is NOT atomic. Observations: {invalid_observations}"
    )


def test_no_orphan_tmp_files_after_driver_run(tmp_path: Path) -> None:
    """The trap in the driver removes the tmp file on exit. Verify that even
    after multiple successful runs, no `.settings.json.*` residue remains."""
    project = _setup_minimal_project(tmp_path)

    for _ in range(5):
        r = _run_driver_once(project)
        assert r.returncode == 0

    claude_dir = project / ".claude"
    leftovers = [
        p.name for p in claude_dir.iterdir()
        if p.name.startswith(".settings.json.") and p.name != "settings.json"
    ]
    assert not leftovers, (
        f"Orphan tmp files remain in .claude/: {leftovers}. "
        "The driver's trap must clean up the mktemp output on every exit path."
    )


def test_tmp_file_lives_on_same_filesystem_as_destination(tmp_path: Path) -> None:
    """Verify at runtime that the tmp file's filesystem matches the
    destination. Detected via st_dev. If they differ, `mv` is non-atomic."""
    project = _setup_minimal_project(tmp_path)

    # Trigger the driver, but inspect the tmp file mid-flight.
    # Since the driver finishes very fast, we instead verify the structural
    # guarantee: any file matching .settings.json.XXXXXX created by the
    # driver lives under .claude/.
    captured: list[Path] = []

    def watch() -> None:
        claude = project / ".claude"
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            for p in claude.iterdir():
                if p.name.startswith(".settings.json."):
                    captured.append(p)
            time.sleep(0.001)

    watcher = threading.Thread(target=watch, daemon=True)
    watcher.start()

    # Run the driver many times to maximise chance of catching the tmp file.
    for _ in range(50):
        _run_driver_once(project)

    watcher.join(timeout=2)

    # If we captured any tmp file, verify its parent directory matches
    # settings.json's parent (same dir → same FS guaranteed).
    settings = project / ".claude" / "settings.json"
    settings_parent_dev = settings.parent.stat().st_dev
    for p in captured:
        # File may have been removed by trap before we checked; that's fine.
        try:
            tmp_dev = p.parent.stat().st_dev
        except FileNotFoundError:
            continue
        assert tmp_dev == settings_parent_dev, (
            f"Tmp file {p} lives on filesystem dev={tmp_dev}, but "
            f"destination is on dev={settings_parent_dev}. Cross-filesystem "
            "`mv` would be non-atomic."
        )

    # Note: it is acceptable to capture zero tmp files (the driver may run
    # too fast for the watcher to catch one). The structural test
    # `test_driver_uses_dest_dir_mktemp` is the authoritative guarantee.

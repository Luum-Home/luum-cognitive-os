#!/usr/bin/env python3
# SCOPE: os-only
"""Guard: error-learning.jsonl has exactly ONE path across the whole repo.

Origin (2026-08-15): the repo carried two files named ``error-learning.jsonl``
in different directories. ``.cognitive-os/error-learning.jsonl`` held 102 rows
and had zero readers; ``.cognitive-os/metrics/error-learning.jsonl`` held 11 and
had every reader. Nothing named the split, because a search by filename shows
both as "the" error-learning log. See
``docs/06-Daily/reports/error-learning-ruta-partida-2026-08-15.md``.

Two invariants, both population-guarded — a scan that matches nothing must FAIL,
not pass. A guard that goes green because its glob broke is the exact failure
mode this file exists to prevent.

  1. Every ``error-learning.jsonl`` path literal in executable source resolves
     under ``metrics/``.
  2. The canonical path has readers, and every writer targets it.

Exit-code contract when run directly: 0 clean, 1 findings, 2 error.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# Directories holding executable code. Docs, ADRs, reports and .ai/ primitive
# snapshots are excluded: they DESCRIBE paths, they do not open files.
EXECUTABLE_DIRS = (
    "bin",
    "cos_lib",
    "hooks",
    "mcp-server",
    "packages",
    "scripts",
    "cmd",
)

# Population floors. Deliberately well under the measured counts (21 readers,
# 3 writers on 2026-08-15) so ordinary refactors do not trip them, but above
# zero so a broken scan cannot pass.
MIN_PATH_LITERALS = 10
MIN_READER_FILES = 8

# The known-bad shape: ".cognitive-os" joined to the filename with no "metrics"
# segment in between — i.e. the file sitting directly under .cognitive-os/.
# Path literals built from a variable ($METRICS_DIR, metrics_dir, base) cannot be
# resolved statically and are covered by the behavioural tests below instead;
# flagging them here would be a guess dressed up as an assertion.
_ORPHAN = re.compile(
    r"""(?ix)
    \.cognitive-os                 # the project state dir
    (?P<between>[^\n]{0,40}?)      # whatever joins it to the filename
    error-learning\.jsonl
    """
)

# Rows written to the legacy orphan stop here. Anything newer means a writer
# came back.
FREEZE_EPOCH_DATE = "2026-08-16"

# The one file allowed to name the orphan path: the operator-facing inspector,
# which READS the orphan and writes only to the canonical file. Every entry
# carries a reason, and a stale entry fails the test rather than sitting there
# silently widening the hole.
ORPHAN_READERS_ALLOWED = {
    "scripts/migrate_error_learning_orphan.py":
        "read-only inspector for the frozen orphan; writes only to the canonical path",
}


def _grep_path_literals() -> list[tuple[str, int, str]]:
    """Return (file, lineno, line) for every error-learning.jsonl mention in code.

    No ``--include`` filter: eight of this repo's executables are kebab-case with
    no extension (``bin/cos-errors``, ``bin/cos-test``, …) and an extension
    filter silently drops them.
    """
    proc = subprocess.run(
        # --untracked: a new writer is an untracked file until it is committed,
        # and a guard that only sees the index green-lights it right up to the
        # moment it lands.
        ["git", "grep", "-n", "--untracked", "error-learning.jsonl", "--", *EXECUTABLE_DIRS],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode not in (0, 1):
        raise RuntimeError(f"git grep failed: {proc.stderr.strip()}")

    hits: list[tuple[str, int, str]] = []
    for raw in proc.stdout.splitlines():
        parts = raw.split(":", 2)
        if len(parts) != 3:
            continue
        path, lineno, line = parts
        # Test fixtures build their own trees; they are not the product's paths.
        if "/tests/" in f"/{path}" or path.endswith("_test.go"):
            continue
        hits.append((path, int(lineno), line))
    return hits


def _offenders(hits: list[tuple[str, int, str]]) -> list[tuple[str, int, str]]:
    bad = []
    for path, lineno, line in hits:
        if path in ORPHAN_READERS_ALLOWED:
            # Naming the orphan is exactly this file's job: it inspects the
            # frozen 102 rows so the operator can decide the migration. The
            # exemption is per-file and narrow, not a pattern — a second
            # would have to be argued for on its own terms.
            continue
        match = _ORPHAN.search(line)
        if match and "metrics" not in match.group("between").lower():
            bad.append((path, lineno, line.strip()))
    return bad


def _on_disk_error_learning_files() -> list[Path]:
    """Every file literally named error-learning.jsonl in the working tree."""
    proc = subprocess.run(
        ["find", ".", "-name", "error-learning.jsonl", "-not", "-path", "./.git/*"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    # NOTE: str.lstrip("./") would eat the leading dot of ".cognitive-os".
    return [
        REPO_ROOT / (line[2:] if line.startswith("./") else line)
        for line in proc.stdout.split()
        if line.strip()
    ]


def test_every_error_learning_path_literal_is_canonical() -> None:
    hits = _grep_path_literals()
    assert len(hits) >= MIN_PATH_LITERALS, (
        f"population guard: only {len(hits)} error-learning.jsonl mentions found in "
        f"{EXECUTABLE_DIRS}; the scan is broken, not the repo clean"
    )

    bad = _offenders(hits)
    assert not bad, (
        "error-learning.jsonl path split — these point somewhere other than "
        "metrics/error-learning.jsonl:\n"
        + "\n".join(f"  {p}:{n}: {ln}" for p, n, ln in bad)
    )


def test_no_allowlisted_orphan_reader_has_gone_stale() -> None:
    """An exemption must not outlive the file it exempts.

    A suppressor that suppresses nothing is a bug, not a neutral leftover: it
    reads as coverage while covering nothing, and the next person to add a
    genuine offender finds a familiar-looking allowlist waiting for one more
    entry. Deleting the inspector must therefore fail here, forcing the
    exemption out with it.
    """
    stale = [rel for rel in ORPHAN_READERS_ALLOWED if not (REPO_ROOT / rel).exists()]
    assert not stale, (
        "ORPHAN_READERS_ALLOWED exempts files that no longer exist — delete the "
        "entries, do not leave the hole open:\n" + "\n".join(f"  {p}" for p in stale)
    )


def test_canonical_path_has_readers() -> None:
    """A writer aimed at a path nobody reads is a private log, not learning.

    Counts distinct FILES that mention the canonical path, which is the closest
    reproducible proxy for "somebody consumes this".
    """
    hits = _grep_path_literals()
    files = {path for path, _, _ in hits}
    assert len(files) >= MIN_READER_FILES, (
        f"population guard: only {len(files)} files reference the canonical "
        f"error-learning.jsonl (floor {MIN_READER_FILES}). Either the consumers "
        f"were deleted or this scan stopped seeing them."
    )


def test_no_error_learning_file_outside_metrics_receives_new_rows() -> None:
    """The legacy orphan is frozen evidence, not a live stream.

    It is deliberately NOT deleted (it documents a 3-month leak), so the
    invariant is "no new rows", not "no file". A second copy appearing in a
    third directory fails here too.
    """
    on_disk = _on_disk_error_learning_files()
    assert on_disk, (
        "population guard: no error-learning.jsonl found on disk at all — "
        "the scan is broken, or telemetry stopped being written"
    )

    canonical = REPO_ROOT / ".cognitive-os" / "metrics" / "error-learning.jsonl"
    outside = [p for p in on_disk if p != canonical]

    for path in outside:
        newest = ""
        for line in path.read_text(errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            stamp = re.search(r"\"(?:ts|timestamp)\"\s*:\s*\"([0-9-]{10})", line)
            if stamp and stamp.group(1) > newest:
                newest = stamp.group(1)
        assert newest and newest < FREEZE_EPOCH_DATE, (
            f"{path.relative_to(REPO_ROOT)} has rows dated {newest or '(unparseable)'} "
            f"— a writer is still aiming outside "
            f".cognitive-os/metrics/. Point it at the canonical path."
        )


def test_evolve_queue_writer_targets_canonical_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The writer that caused the split must now resolve under metrics/."""
    monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", str(tmp_path))
    monkeypatch.delenv("CODEX_PROJECT_DIR", raising=False)
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)

    from cos_lib.evolve_task_queue import error_learning_path

    resolved = error_learning_path()
    assert resolved == tmp_path / ".cognitive-os" / "metrics" / "error-learning.jsonl", (
        f"evolve_task_queue writes to {resolved}, not the canonical metrics path"
    )


def main() -> int:
    try:
        hits = _grep_path_literals()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if len(hits) < MIN_PATH_LITERALS:
        print(
            f"ERROR: population guard tripped — {len(hits)} mentions found, "
            f"expected >= {MIN_PATH_LITERALS}",
            file=sys.stderr,
        )
        return 2

    bad = _offenders(hits)
    files = {path for path, _, _ in hits}
    print(f"error-learning.jsonl mentions: {len(hits)} across {len(files)} files")
    if bad:
        print("NON-CANONICAL PATHS:")
        for path, lineno, line in bad:
            print(f"  {path}:{lineno}: {line}")
        return 1
    print("all path literals resolve under metrics/ — single path holds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
# SCOPE: os-only
"""Immutable stash identity helpers (ADR-221).

Git's ``stash@{N}`` reflog positions drift whenever another stash is pushed.
These helpers keep persisted identity on the stash commit SHA and resolve the
current human ref only at the last possible moment for commands that require it.
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

_STASH_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class StashEntry:
    sha: str
    ref: str
    subject: str


def _run(repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def is_stash_sha(value: str | None) -> bool:
    return bool(value and _STASH_SHA_RE.match(value.strip()))


def list_stashes(repo: Path) -> list[StashEntry]:
    """Return current stash entries as immutable SHA + current reflog ref."""
    result = _run(Path(repo), ["stash", "list", "--format=%H%x1f%gd%x1f%gs"])
    if result.returncode != 0:
        return []
    entries: list[StashEntry] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\x1f", 2)
        if len(parts) != 3:
            continue
        sha, ref, subject = (p.strip() for p in parts)
        if is_stash_sha(sha) and ref:
            entries.append(StashEntry(sha=sha, ref=ref, subject=subject))
    return entries


def resolve_top_stash_sha(repo: Path) -> str | None:
    """Return the SHA of the current top stash, or None if no stash exists."""
    result = _run(Path(repo), ["rev-parse", "--verify", "stash@{0}"])
    sha = result.stdout.strip()
    if result.returncode != 0 or not is_stash_sha(sha):
        return None
    return sha


def resolve_sha_to_ref(repo: Path, stash_sha: str) -> str | None:
    """Return the current ``stash@{N}`` ref for ``stash_sha`` if present."""
    wanted = stash_sha.strip()
    if not is_stash_sha(wanted):
        return None
    for entry in list_stashes(Path(repo)):
        if entry.sha == wanted:
            return entry.ref
    return None


def find_by_subject(repo: Path, subject: str) -> list[StashEntry]:
    """Return entries whose subject contains ``subject``."""
    needle = subject.strip()
    if not needle:
        return []
    return [entry for entry in list_stashes(Path(repo)) if needle in entry.subject]

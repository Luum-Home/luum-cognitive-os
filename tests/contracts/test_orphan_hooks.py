"""
Contract test: Orphan Hook Detection (ADR-028 Phase B D2)

Every .sh file in hooks/ must be EITHER:
  1. Referenced in .claude/settings.json (registered), OR
  2. Listed in tests/contracts/EXCLUDED_HOOKS.txt (whitelisted with reason)

Failure means a new hook was added without being wired into settings.json and without
a documented reason for leaving it unregistered. This blocks the "add dead code" anti-pattern.

To resolve a failure:
  a) Register the hook in .claude/settings.json under the appropriate event, OR
  b) Add the hook to EXCLUDED_HOOKS.txt with a clear reason (category + explanation).

To whitelist a new unregistered hook, add it to EXCLUDED_HOOKS.txt in the format:
    <hook-filename.sh> | <reason>

Lines starting with '#' and blank lines are ignored.
"""

import json
import os
import re
import sys
from pathlib import Path

import pytest

# ── Paths ────────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent.parent.parent
HOOKS_DIR = PROJECT_ROOT / "hooks"
SETTINGS_JSON = PROJECT_ROOT / ".claude" / "settings.json"
EXCLUDED_HOOKS_FILE = Path(__file__).parent / "EXCLUDED_HOOKS.txt"

# ── Helpers ──────────────────────────────────────────────────────────────────


def _collect_hook_files() -> set[str]:
    """Return basenames of all .sh files in hooks/ (excluding _lib/ subdirectory)."""
    result: set[str] = set()
    for path in HOOKS_DIR.glob("*.sh"):
        result.add(path.name)
    return result


def _collect_registered_hooks() -> set[str]:
    """Return basenames of all hooks referenced in .claude/settings.json."""
    if not SETTINGS_JSON.exists():
        return set()

    with SETTINGS_JSON.open() as f:
        settings = json.load(f)

    registered: set[str] = set()

    def _walk(obj: object) -> None:
        if isinstance(obj, dict):
            cmd = obj.get("command", "")
            if cmd and ".sh" in cmd:
                # Extract the filename from paths like:
                #   bash "$CLAUDE_PROJECT_DIR/hooks/foo.sh"
                #   /absolute/path/to/hooks/foo.sh
                match = re.search(r"hooks/([^/\s\"']+\.sh)", cmd)
                if match:
                    registered.add(match.group(1))
            for value in obj.values():
                _walk(value)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    _walk(settings.get("hooks", {}))
    return registered


def _collect_whitelist() -> dict[str, str]:
    """
    Parse EXCLUDED_HOOKS.txt and return {filename: reason}.
    Lines starting with '#' or empty lines are ignored.
    Entries may include a _lib/ prefix for library files.
    """
    whitelist: dict[str, str] = {}
    if not EXCLUDED_HOOKS_FILE.exists():
        return whitelist

    for raw_line in EXCLUDED_HOOKS_FILE.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|", maxsplit=1)
        filename = parts[0].strip()
        reason = parts[1].strip() if len(parts) > 1 else "no reason provided"
        # Normalise: strip leading path components so both "_lib/foo.sh" and "foo.sh" match
        basename = Path(filename).name
        whitelist[basename] = reason
    return whitelist


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def hook_files() -> set[str]:
    return _collect_hook_files()


@pytest.fixture(scope="module")
def registered_hooks() -> set[str]:
    return _collect_registered_hooks()


@pytest.fixture(scope="module")
def whitelist() -> dict[str, str]:
    return _collect_whitelist()


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_settings_json_exists() -> None:
    """settings.json must exist for the contract to be enforceable."""
    assert SETTINGS_JSON.exists(), (
        f"settings.json not found at {SETTINGS_JSON}. "
        "The orphan hook contract requires settings.json to determine registered hooks."
    )


def test_excluded_hooks_file_exists() -> None:
    """EXCLUDED_HOOKS.txt must exist alongside this test."""
    assert EXCLUDED_HOOKS_FILE.exists(), (
        f"EXCLUDED_HOOKS.txt not found at {EXCLUDED_HOOKS_FILE}. "
        "Create this file with intentionally-unregistered hooks and their reasons."
    )


def test_whitelist_entries_have_reasons() -> None:
    """Every whitelist entry must have a non-empty reason."""
    bad: list[str] = []
    for raw_line in EXCLUDED_HOOKS_FILE.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|", maxsplit=1)
        filename = parts[0].strip()
        reason = parts[1].strip() if len(parts) > 1 else ""
        if not reason:
            bad.append(filename)

    assert not bad, (
        f"These whitelist entries are missing a reason:\n"
        + "\n".join(f"  {f}" for f in sorted(bad))
        + "\nAdd '| <reason>' after each filename."
    )


def test_no_orphan_hooks(
    hook_files: set[str],
    registered_hooks: set[str],
    whitelist: dict[str, str],
) -> None:
    """
    Every hook file must be registered in settings.json OR whitelisted.

    A hook is an 'orphan' if it is neither registered nor whitelisted.
    Orphan hooks are dead code — they consume disk space but fire on no event.

    To resolve: either register in .claude/settings.json or add to EXCLUDED_HOOKS.txt.
    """
    orphans: list[str] = []
    for hook in sorted(hook_files):
        is_registered = hook in registered_hooks
        is_whitelisted = hook in whitelist
        if not is_registered and not is_whitelisted:
            orphans.append(hook)

    if orphans:
        lines = [
            "",
            f"Found {len(orphans)} orphan hook(s) — neither registered nor whitelisted:",
            "",
        ]
        for h in orphans:
            lines.append(f"  hooks/{h}")
        lines += [
            "",
            "Fix options:",
            "  a) Register in .claude/settings.json under the appropriate event, OR",
            "  b) Add to tests/contracts/EXCLUDED_HOOKS.txt with a reason:",
            "     <hook-filename.sh> | <category>: <explanation>",
            "",
        ]
        pytest.fail("\n".join(lines))


def test_whitelist_no_stale_entries(
    hook_files: set[str],
    whitelist: dict[str, str],
) -> None:
    """
    Whitelist entries must refer to existing hook files.

    Stale entries (hook was deleted but whitelist not updated) are noise.
    Clean them up to keep EXCLUDED_HOOKS.txt accurate.
    """
    stale: list[str] = []
    for whitelisted_name in whitelist:
        # Check both as top-level file and as potential _lib/ file
        exists_toplevel = whitelisted_name in hook_files
        exists_in_lib = (HOOKS_DIR / "_lib" / whitelisted_name).exists()
        if not exists_toplevel and not exists_in_lib:
            stale.append(whitelisted_name)

    if stale:
        lines = [
            "",
            f"Found {len(stale)} stale whitelist entry/entries in EXCLUDED_HOOKS.txt:",
            "(these files no longer exist in hooks/)",
            "",
        ]
        for h in sorted(stale):
            lines.append(f"  {h}")
        lines += [
            "",
            "Remove these entries from tests/contracts/EXCLUDED_HOOKS.txt.",
            "",
        ]
        pytest.fail("\n".join(lines))


def test_registered_hooks_exist_on_disk(
    registered_hooks: set[str],
) -> None:
    """
    Every hook referenced in settings.json must exist as a file.

    A hook registered in settings.json but missing from disk will silently fail
    at runtime. This test catches that before it becomes a production issue.
    """
    missing: list[str] = []
    for hook in sorted(registered_hooks):
        if not (HOOKS_DIR / hook).exists():
            missing.append(hook)

    if missing:
        lines = [
            "",
            f"Found {len(missing)} hook(s) registered in settings.json but missing from disk:",
            "",
        ]
        for h in missing:
            lines.append(f"  hooks/{h}  (referenced in .claude/settings.json)")
        lines += [
            "",
            "Either create the missing file or remove the registration from settings.json.",
            "",
        ]
        pytest.fail("\n".join(lines))


# ── Summary (informational, never fails) ─────────────────────────────────────


def test_coverage_summary(
    hook_files: set[str],
    registered_hooks: set[str],
    whitelist: dict[str, str],
) -> None:
    """Print hook coverage statistics (informational only, never fails)."""
    total = len(hook_files)
    registered_count = len(hook_files & registered_hooks)
    whitelisted_count = len(hook_files & set(whitelist.keys()))
    orphan_count = len(
        [h for h in hook_files if h not in registered_hooks and h not in whitelist]
    )

    print(
        f"\n── Hook Coverage ──────────────────────────────────────────\n"
        f"  Total hook files:  {total}\n"
        f"  Registered:        {registered_count} ({100 * registered_count // total if total else 0}%)\n"
        f"  Whitelisted:       {whitelisted_count} ({100 * whitelisted_count // total if total else 0}%)\n"
        f"  Orphans:           {orphan_count}\n"
        f"──────────────────────────────────────────────────────────"
    )
    # This test always passes; it's purely informational.
    assert True

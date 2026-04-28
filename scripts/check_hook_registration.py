#!/usr/bin/env python3
# SCOPE: both
"""Validate that all hooks in hooks/*.sh are registered in security/efficiency profiles.

A hook is considered registered when it appears in ALL of:
  - templates/security-profiles/*.json
  - scripts/apply-efficiency-profile.sh
  - .claude/settings.local.json  (or settings.json)

Hooks that intentionally skip registration can be allowlisted in
hooks/_lib/registration-allowlist.txt.

Exit 0 if all registered (or allowlisted), exit 1 with details of unregistered hooks.
"""
from __future__ import annotations

import sys
from pathlib import Path


def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def get_hooks_on_disk(root: Path) -> set[str]:
    """Return set of hook filenames from hooks/*.sh, excluding _lib helpers."""
    hooks_dir = root / "hooks"
    if not hooks_dir.exists():
        return set()
    result = set()
    for f in hooks_dir.iterdir():
        if f.is_file() and f.suffix == ".sh" and not f.name.startswith("_"):
            result.add(f.name)
    return result


def _read_file_safe(path: Path) -> str:
    try:
        return path.read_text(errors="ignore") if path.exists() else ""
    except OSError:
        return ""


def get_settings_content(root: Path) -> str:
    """Return combined content of settings files."""
    parts = []
    for name in ("settings.local.json", "settings.json"):
        p = root / ".claude" / name
        parts.append(_read_file_safe(p))
    return "\n".join(parts)


def get_security_profile_content(root: Path) -> str:
    """Return combined security profile JSON content.

    Security profiles are the source of truth for set-security-profile.sh.
    The script applies those JSON artifacts; it should not be treated as the
    hook registry.
    """
    profile_dir = root / "templates" / "security-profiles"
    if not profile_dir.is_dir():
        return ""
    return "\n".join(
        _read_file_safe(path)
        for path in sorted(profile_dir.glob("*.json"))
    )


def check_hook_registered(hook_name: str, root: Path) -> dict[str, bool]:
    security = get_security_profile_content(root)
    efficiency = _read_file_safe(root / "scripts" / "apply-efficiency-profile.sh")
    settings = get_settings_content(root)
    return {
        "security_profile": hook_name in security,
        "efficiency_profile": hook_name in efficiency,
        "settings_json": hook_name in settings,
    }


def load_allowlist(root: Path) -> set[str]:
    path = root / "hooks" / "_lib" / "registration-allowlist.txt"
    if not path.exists():
        return set()
    result = set()
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            result.add(line)
    return result


def main() -> int:
    root = get_project_root()
    on_disk = get_hooks_on_disk(root)
    allowlist = load_allowlist(root)

    if not on_disk:
        print("Hook registration OK: no hooks found on disk")
        return 0

    unregistered: list[tuple[str, dict[str, bool]]] = []
    for hook in sorted(on_disk):
        if hook in allowlist:
            continue
        checks = check_hook_registered(hook, root)
        if not all(checks.values()):
            unregistered.append((hook, checks))

    if unregistered:
        print(f"UNREGISTERED hooks ({len(unregistered)}):")
        for hook, checks in unregistered:
            missing = [k for k, v in checks.items() if not v]
            print(f"  - {hook}  (missing: {', '.join(missing)})")
        print(
            "\nTo register: add to templates/security-profiles/*.json and "
            "scripts/apply-efficiency-profile.sh, then re-run set-security-profile.sh."
        )
        print(
            "To allowlist intentionally unregistered hooks, "
            "add the filename to hooks/_lib/registration-allowlist.txt"
        )
        return 1

    wired = len(on_disk) - len(allowlist & on_disk)
    print(
        f"Hook registration OK: {len(on_disk)} hooks on disk, "
        f"{wired} fully registered, "
        f"{len(allowlist & on_disk)} allowlisted"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# SCOPE: both
"""Validate that all hooks in hooks/*.sh have an effective projection path.

A hook is considered registered when it is directly named by a projection
artifact or when a projected dispatcher names it. This keeps the checker aligned
with the current default/maintainer profile, where the Bash hot path projects
hooks/bash-hot-path-dispatcher.sh and lets that dispatcher fan out to
command-scoped gates.

Hooks that intentionally skip registration can be allowlisted in
hooks/_lib/registration-allowlist.txt or classified with an intentional-absence
status in manifests/hook-registration-classification.yaml.

Exit 0 if all registered (or allowlisted), exit 1 with details of unregistered hooks.
"""
from __future__ import annotations

import sys
from pathlib import Path
import re
import yaml
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.project_paths import repo_root_from_file

get_project_root = lambda: repo_root_from_file(__file__)
get_project_root = lambda: repo_root_from_file(__file__)
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
    """Return combined content of concrete settings files."""
    parts = []
    for name in ("settings.local.json", "settings.json"):
        p = root / ".claude" / name
        parts.append(_read_file_safe(p))
    parts.append(_read_file_safe(root / ".codex" / "hooks.json"))
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


def get_projection_source_content(root: Path) -> str:
    """Return committed projection source content.

    Settings drivers are authoritative projection producers. They matter even
    when the currently checked-out settings file is using a lean profile.
    """
    paths = [
        root / "scripts" / "_lib" / "settings-driver-claude-code.sh",
        root / "scripts" / "_lib" / "settings-driver-codex.sh",
        root / "scripts" / "_lib" / "settings-driver-bare.sh",
    ]
    return "\n".join(_read_file_safe(path) for path in paths)


def dispatcher_targets(root: Path) -> set[str]:
    """Return hooks invoked by the hot-path dispatcher."""
    text = _read_file_safe(root / "hooks" / "bash-hot-path-dispatcher.sh")
    return set(re.findall(r'"hooks/([A-Za-z0-9_.-]+\.sh)"', text))


def dispatcher_projected(root: Path) -> bool:
    name = "bash-hot-path-dispatcher.sh"
    return name in "\n".join(
        [
            get_settings_content(root),
            get_projection_source_content(root),
            get_security_profile_content(root),
            _read_file_safe(root / "scripts" / "apply-efficiency-profile.sh"),
        ]
    )


def check_hook_registered(hook_name: str, root: Path) -> dict[str, bool]:
    security = get_security_profile_content(root)
    efficiency = _read_file_safe(root / "scripts" / "apply-efficiency-profile.sh")
    settings = get_settings_content(root)
    projection_sources = get_projection_source_content(root)
    routed_by_dispatcher = dispatcher_projected(root) and hook_name in dispatcher_targets(root)
    directly_projected = hook_name in "\n".join([security, efficiency, settings, projection_sources])
    return {
        "direct_projection": directly_projected,
        "dispatcher_projection": routed_by_dispatcher,
        "effective_projection": directly_projected or routed_by_dispatcher,
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


def load_intentionally_absent_classifications(root: Path) -> set[str]:
    path = root / "manifests" / "hook-registration-classification.yaml"
    if not path.exists():
        return set()
    intentional_statuses = {
        "candidate_promote",
        "conditional_opt_in",
        "demoted",
        "deprecated",
        "future",
        "git_or_manual",
        "internal_helper",
        "manual_trigger",
        "opt_in",
        "projected_elsewhere",
    }
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return set()
    absent: set[str] = set()
    for entry in payload.get("entries", []) or []:
        status = str(entry.get("status", ""))
        if status in intentional_statuses:
            absent.add(Path(str(entry.get("path", ""))).name)
    return absent


def main() -> int:
    root = get_project_root()
    on_disk = get_hooks_on_disk(root)
    allowlist = load_allowlist(root)
    intentionally_absent = load_intentionally_absent_classifications(root)
    intentionally_skipped = (allowlist | intentionally_absent) & on_disk

    if not on_disk:
        print("Hook registration OK: no hooks found on disk")
        return 0

    unregistered: list[tuple[str, dict[str, bool]]] = []
    for hook in sorted(on_disk):
        if hook in intentionally_skipped:
            continue
        checks = check_hook_registered(hook, root)
        if not checks["effective_projection"]:
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

    wired = len(on_disk) - len(intentionally_skipped)
    print(
        f"Hook registration OK: {len(on_disk)} hooks on disk, "
        f"{wired} fully registered, "
        f"{len(intentionally_skipped)} intentionally absent"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

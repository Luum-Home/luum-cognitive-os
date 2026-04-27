#!/usr/bin/env python3
"""cos_init.py — Python bootstrap for Cognitive OS project initialization.

Strangler-fig migration of scripts/cos-init.sh (Phase 2.1 → 2.3).
This module replaces bash functions one at a time while the bash shim in
cos-init.sh delegates individual functions here via --internal-call.

Migration status (Phase 2.3):
  MIGRATED:   detect_harness       (inlined from scripts/_lib/settings-driver.sh::cos_detect_harness)
  MIGRATED:   scope_allows         (cos-init.sh lines 121-143)
  MIGRATED:   skill_scope_allows   (cos-init.sh lines 147-167)
  MIGRATED:   install_rule         (cos-init.sh install_rule function)
  MIGRATED:   install_hook         (cos-init.sh install_hook function)
  MIGRATED:   install_skill_dir    (cos-init.sh install_skill_dir function)

Usage (direct):
    python3 scripts/cos_init.py [--default|--full] [--harness claude|codex]

Usage (internal dispatcher — called by bash shim):
    python3 scripts/cos_init.py --internal-call detect_harness [project_root]
    python3 scripts/cos_init.py --internal-call scope_allows <file_path>
    python3 scripts/cos_init.py --internal-call skill_scope_allows <skill_dir>
    python3 scripts/cos_init.py --internal-call install_rule <name> <rules_source> <dest1>[:<dest2>...]
    python3 scripts/cos_init.py --internal-call install_hook <name> <hooks_source> <hooks_dest>
    python3 scripts/cos_init.py --internal-call install_skill_dir <skill_dir> <kernel_dest> <driver_dest>
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# ── Repository root (cos source directory) ───────────────────────────
COS_SOURCE_DIR = Path(__file__).parent.parent.resolve()
COS_INIT_SH = COS_SOURCE_DIR / "scripts" / "cos-init.sh"


# ── Migrated functions ───────────────────────────────────────────────

def detect_harness(project_root: str = ".") -> str:
    """Detect the active harness for a project directory.

    Inlined from scripts/_lib/settings-driver.sh::cos_detect_harness.
    Detects the active harness (claude|codex) by inspecting filesystem markers
    and environment variables. Priority order matches the bash implementation
    exactly (parity required for strangler-fig correctness):

      1. COGNITIVE_OS_HARNESS env var (explicit override)
      2. .codex/hooks.json present AND .claude/settings.json absent  → codex
      3. .claude/settings.json present AND .codex/hooks.json absent  → claude
      4. CODEX_PROJECT_DIR / CODEX_SESSION_ID / CODEX_HOME env vars  → codex
      5. Default → claude
    """
    root = Path(project_root).resolve()

    # Priority 1: explicit env override
    explicit = os.environ.get("COGNITIVE_OS_HARNESS", "")
    if explicit:
        return explicit

    codex_hooks = root / ".codex" / "hooks.json"
    claude_settings = root / ".claude" / "settings.json"

    # Priority 2: only codex markers present
    if codex_hooks.is_file() and not claude_settings.is_file():
        return "codex"

    # Priority 3: only claude markers present
    if claude_settings.is_file() and not codex_hooks.is_file():
        return "claude"

    # Priority 4: Codex environment variables
    if (
        os.environ.get("CODEX_PROJECT_DIR", "")
        or os.environ.get("CODEX_SESSION_ID", "")
        or os.environ.get("CODEX_HOME", "")
    ):
        return "codex"

    # Priority 5: default
    return "claude"


def scope_allows(file_path: str, install_scope: str = "both") -> bool:
    """Port from scripts/cos-init.sh::scope_allows() (lines 121-143).

    Returns True if the file's SCOPE header allows installation under the
    given install_scope. Files without a SCOPE header are universal (always allowed).

    Byte-for-byte port — do NOT optimise the bash logic.
    """
    import re as _re

    path = Path(file_path)

    # Non-files always pass (matches: [ -f "$f" ] || return 0)
    if not path.is_file():
        return True

    # If scope is "all", never filter
    if install_scope == "all":
        return True

    # Extract SCOPE header from first 3 lines only (fast, matches head -3 | grep -m1 -oE)
    # Bash pattern: '(# SCOPE:|<!-- SCOPE:) [a-zA-Z_/-]+'  then awk '{print $NF}' | tr -d ' '
    try:
        with path.open(encoding="utf-8", errors="replace") as fh:
            head = [fh.readline() for _ in range(3)]
    except OSError:
        return True

    scope_val = ""
    pattern = _re.compile(r'(?:# SCOPE:|<!-- SCOPE:)\s+([a-zA-Z_/-]+)')
    for line in head:
        m = pattern.search(line)
        if m:
            scope_val = m.group(1).strip()
            break

    # No SCOPE header → include unconditionally
    if not scope_val:
        return True

    # project/both scopes: allow "project" or "both", block "os-only"
    if scope_val in ("project", "both"):
        return True
    if scope_val == "os-only":
        return False
    # Unknown tag → include (be permissive)
    return True


def skill_scope_allows(skill_dir: str, install_scope: str = "both") -> bool:
    """Port from scripts/cos-init.sh::skill_scope_allows() (lines 147-167).

    Returns True if the skill's `audience:` or `scope:` SKILL.md frontmatter
    allows installation. Mirror the bash logic exactly.

    Byte-for-byte port — do NOT optimise the bash logic.
    """
    skill_md = Path(skill_dir) / "SKILL.md"

    # No SKILL.md → allow (matches: [ -f "$skill_md" ] || return 0)
    if not skill_md.is_file():
        return True

    # If scope is "all", never filter
    if install_scope == "all":
        return True

    # Extract audience/scope field from frontmatter.
    # Bash: grep -E '^(audience|scope):' | head -1 | awk -F: '{print $2}' | tr -d " '\"\r"
    audience = ""
    try:
        with skill_md.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                stripped = line.rstrip("\n")
                if stripped.startswith(("audience:", "scope:")):
                    # awk -F: '{print $2}' gives everything after the first colon
                    parts = stripped.split(":", 1)
                    if len(parts) == 2:
                        audience = parts[1].translate(
                            str.maketrans("", "", " '\"\r")
                        )
                    break
    except OSError:
        return True

    # No audience field → allow
    if not audience:
        return True

    if audience in ("project", "both", "adopters", "human"):
        return True
    if audience in ("os", "os-dev", "os-only"):
        return False
    # Unknown → allow (be permissive)
    return True


# ── Phase 2.3: install workhorses ────────────────────────────────────

def install_rule(
    name: str,
    rules_source: str,
    rule_dests: list[str],
) -> str:
    """Port from scripts/cos-init.sh::install_rule().

    Takes a rule name (no extension), source directory, and list of destination
    directories. Copies <rules_source>/<name>.md to each destination.

    Byte-for-byte port — do NOT optimise the bash logic.

    Returns one of: "installed", "skipped" (source missing → bash used [ -f ] || return),
    "error".
    """
    src = Path(rules_source) / f"{name}.md"
    if not src.is_file():
        # Matches bash: [ -f "$src" ] || return (no-op exit 0 in bash, counter not incremented)
        return "skipped"

    try:
        for dest_dir in rule_dests:
            dest = Path(dest_dir)
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src), str(dest / f"{name}.md"))
    except OSError as exc:
        print(f"cos_init.py: install_rule '{name}' failed: {exc}", file=sys.stderr)
        return "error"

    return "installed"


def install_hook(
    name: str,
    hooks_source: str,
    hooks_dest: str,
) -> str:
    """Port from scripts/cos-init.sh::install_hook().

    Takes a hook name (no extension), source directory, and destination directory.
    Copies <hooks_source>/<name>.sh to <hooks_dest>/<name>.sh and sets executable bit.

    Byte-for-byte port — do NOT optimise the bash logic.

    Returns one of: "installed", "skipped" (source missing), "error".
    """
    src = Path(hooks_source) / f"{name}.sh"
    if not src.is_file():
        # Matches bash: [ -f "$src" ] || return
        return "skipped"

    dest_dir = Path(hooks_dest)
    dest_path = dest_dir / f"{name}.sh"

    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src), str(dest_path))
        # chmod +x — set executable bits for user/group/other (matches bash chmod +x)
        current_mode = dest_path.stat().st_mode
        dest_path.chmod(current_mode | 0o111)
    except OSError as exc:
        print(f"cos_init.py: install_hook '{name}' failed: {exc}", file=sys.stderr)
        return "error"

    return "installed"


def install_skill_dir(
    skill_dir: str,
    skill_dest_kernel: str,
    skill_dest_driver: str,
    install_scope: str = "both",
) -> str:
    """Port from scripts/cos-init.sh::install_skill_dir().

    Takes a full skill directory path, kernel dest, driver dest.
    Calls skill_scope_allows() to filter. Then:
      - rm -rf kernel/<name> driver/<name>
      - cp -r skill_dir kernel/<name>
      - ln -s ../../.cognitive-os/skills/cos/<name> driver/<name>  (relative symlink)

    Byte-for-byte port — do NOT optimise the bash logic.

    Returns one of: "installed", "skipped" (scope-filtered), "error".
    """
    skill_path = Path(skill_dir)
    skill_name = skill_path.name

    # skill_scope_allows "$skill_dir" || return 0
    if not skill_scope_allows(str(skill_path), install_scope=install_scope):
        return "skipped"

    kernel_dest = Path(skill_dest_kernel) / skill_name
    driver_dest = Path(skill_dest_driver) / skill_name

    try:
        # rm -rf "$SKILL_DEST_KERNEL/$skill_name" "$SKILL_DEST_DRIVER/$skill_name"
        if kernel_dest.exists() or kernel_dest.is_symlink():
            if kernel_dest.is_symlink() or kernel_dest.is_file():
                kernel_dest.unlink()
            else:
                shutil.rmtree(str(kernel_dest))
        if driver_dest.exists() or driver_dest.is_symlink():
            driver_dest.unlink()

        # cp -r "$skill_dir" "$SKILL_DEST_KERNEL/$skill_name"
        Path(skill_dest_kernel).mkdir(parents=True, exist_ok=True)
        shutil.copytree(str(skill_path), str(kernel_dest))

        # ln -s "../../.cognitive-os/skills/cos/$skill_name" "$SKILL_DEST_DRIVER/$skill_name"
        # Relative symlink (matches bash exactly)
        Path(skill_dest_driver).mkdir(parents=True, exist_ok=True)
        symlink_target = f"../../.cognitive-os/skills/cos/{skill_name}"
        driver_dest.symlink_to(symlink_target)
    except OSError as exc:
        print(f"cos_init.py: install_skill_dir '{skill_name}' failed: {exc}", file=sys.stderr)
        return "error"

    return "installed"


# ── Bash subprocess shim (unmigrated functions) ───────────────────────

def _call_bash_function(function_name: str, *args: str) -> int:
    """Delegate an unmigrated function to the bash implementation.

    Used during the strangler-fig transition. Once a function is fully
    migrated to Python it is removed from this dispatcher and the bash
    shim in cos-init.sh stops calling --internal-call for it.
    """
    bash_source = f"source {COS_INIT_SH} && {function_name} {' '.join(args)}"
    result = subprocess.run(
        ["bash", "-c", bash_source],
        cwd=os.getcwd(),
    )
    return result.returncode


# ── Internal-call dispatcher ──────────────────────────────────────────

_INTERNAL_DISPATCH: dict[str, callable] = {
    "detect_harness": detect_harness,
    "scope_allows": scope_allows,
    "skill_scope_allows": skill_scope_allows,
    "install_rule": install_rule,
    "install_hook": install_hook,
    "install_skill_dir": install_skill_dir,
}


def _run_internal_call(function_name: str, extra_args: list[str]) -> int:
    """Dispatch --internal-call invocations from the bash shim."""
    if function_name not in _INTERNAL_DISPATCH:
        print(
            f"cos_init.py: unknown --internal-call target '{function_name}'",
            file=sys.stderr,
        )
        return 1

    fn = _INTERNAL_DISPATCH[function_name]

    # scope_allows and skill_scope_allows: read INSTALL_SCOPE from env, return exit code
    if function_name in ("scope_allows", "skill_scope_allows"):
        install_scope = os.environ.get("INSTALL_SCOPE", "both")
        if not extra_args:
            print(
                f"cos_init.py: {function_name} requires a path argument",
                file=sys.stderr,
            )
            return 1
        result = fn(extra_args[0], install_scope)
        # True → allowed → exit 0, False → blocked → exit 1
        return 0 if result else 1

    # install_rule: <name> <rules_source> <dest1>[:<dest2>...]
    if function_name == "install_rule":
        if len(extra_args) < 3:
            print(
                "cos_init.py: install_rule requires <name> <rules_source> <dest1>[:<dest2>...]",
                file=sys.stderr,
            )
            return 1
        name, rules_source = extra_args[0], extra_args[1]
        # dests are passed as colon-separated string in arg 3
        rule_dests = extra_args[2].split(":")
        status = install_rule(name, rules_source, rule_dests)
        print(status)
        return 0 if status != "error" else 1

    # install_hook: <name> <hooks_source> <hooks_dest>
    if function_name == "install_hook":
        if len(extra_args) < 3:
            print(
                "cos_init.py: install_hook requires <name> <hooks_source> <hooks_dest>",
                file=sys.stderr,
            )
            return 1
        status = install_hook(extra_args[0], extra_args[1], extra_args[2])
        print(status)
        return 0 if status != "error" else 1

    # install_skill_dir: <skill_dir> <kernel_dest> <driver_dest>
    if function_name == "install_skill_dir":
        if len(extra_args) < 3:
            print(
                "cos_init.py: install_skill_dir requires <skill_dir> <kernel_dest> <driver_dest>",
                file=sys.stderr,
            )
            return 1
        install_scope = os.environ.get("INSTALL_SCOPE", "both")
        status = install_skill_dir(extra_args[0], extra_args[1], extra_args[2], install_scope)
        print(status)
        return 0 if status != "error" else 1

    result = fn(*extra_args) if extra_args else fn()
    if result is not None:
        print(result)
    return 0


# ── CLI argument parser ───────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cos_init.py",
        description="Bootstrap Cognitive OS in a project (Python layer).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Modes:\n"
            "  --default  10 curated skills, ~29 standard hooks, 14 core rules (~8K tokens/session)\n"
            "  --full     Everything (~142K tokens/session)\n\n"
            "Legacy flags --minimal, --standard, --lean are remapped to --default.\n"
        ),
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--default", dest="mode", action="store_const", const="--default")
    mode_group.add_argument("--full", dest="mode", action="store_const", const="--full")
    mode_group.add_argument("--minimal", dest="mode", action="store_const", const="--default",
                            help=argparse.SUPPRESS)
    mode_group.add_argument("--standard", dest="mode", action="store_const", const="--default",
                            help=argparse.SUPPRESS)
    mode_group.add_argument("--lean", dest="mode", action="store_const", const="--default",
                            help=argparse.SUPPRESS)
    parser.add_argument("--harness", choices=["claude", "codex"],
                        default=os.environ.get("COGNITIVE_OS_HARNESS", ""),
                        help="Target harness (claude or codex). Overrides auto-detection.")
    # Internal dispatcher (used by bash shim)
    parser.add_argument("--internal-call", dest="internal_call", metavar="FUNCTION",
                        help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    # Accept positional mode arg like the bash script (e.g. cos-init.sh --full)
    parsed, extra = parser.parse_known_args(argv)

    # --internal-call: function dispatcher for the bash shim
    if parsed.internal_call:
        return _run_internal_call(parsed.internal_call, extra)

    # Legacy mode passed as positional (bash compat)
    mode = parsed.mode or "--default"
    if extra and extra[0] in ("--default", "--full", "--minimal", "--standard", "--lean"):
        mode = extra.pop(0)
    if mode in ("--minimal", "--standard", "--lean"):
        print(f"Note: ADR-002 collapsed '{mode}' into '--default'. Using '--default'.", file=sys.stderr)
        mode = "--default"

    # Delegate full execution to bash until migration is complete.
    # This preserves all unmigrated logic while the Python layer grows.
    cmd = ["bash", str(COS_INIT_SH), mode]
    if parsed.harness:
        cmd += ["--harness", parsed.harness]
    cmd += extra
    env = os.environ.copy()
    result = subprocess.run(cmd, env=env)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""cos_init.py — Python bootstrap for Cognitive OS project initialization.

Strangler-fig migration of scripts/cos-init.sh (Phase 2.1).
This module replaces bash functions one at a time while the bash shim in
cos-init.sh delegates individual functions here via --internal-call.

Migration status (Phase 2.1):
  MIGRATED:   detect_harness  (inlined from scripts/_lib/settings-driver.sh::cos_detect_harness)
  BASH-SHELL: scope_allows, skill_scope_allows, install_rule, install_hook, install_skill_dir

Usage (direct):
    python3 scripts/cos_init.py [--default|--full] [--harness claude|codex]

Usage (internal dispatcher — called by bash shim):
    python3 scripts/cos_init.py --internal-call detect_harness [project_root]
"""
from __future__ import annotations

import argparse
import os
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

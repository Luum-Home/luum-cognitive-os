#!/usr/bin/env python3
# SCOPE: both
"""cos_init.py — Python bootstrap for Cognitive OS project initialization.

Phase 2.final: full Python main(). scripts/cos-init.sh is now a 1-line shim.

Migration history (Phases 2.1 → 2.3 → 2.final):
  MIGRATED:   detect_harness       (Phase 2.1)
  MIGRATED:   scope_allows         (Phase 2.2)
  MIGRATED:   skill_scope_allows   (Phase 2.2)
  MIGRATED:   install_rule         (Phase 2.3)
  MIGRATED:   install_hook         (Phase 2.3)
  MIGRATED:   install_skill_dir    (Phase 2.3)
  MIGRATED:   main()               (Phase 2.final, 2026-04-27)

Usage (direct):
    python3 scripts/cos_init.py [--default|--full] [--harness claude|codex|opencode|vscode-copilot|cursor|qwen-code|kimi-code|gemini-cli|warp|amp-code|jetbrains-junie|qoder|factory-droid|cline|continue-dev|kilo-code|zed-ai|augment-code|goose|aider|shell-ci]

Usage (internal dispatcher — kept for backward compat):
    python3 scripts/cos_init.py --internal-call detect_harness [project_root]
    python3 scripts/cos_init.py --internal-call scope_allows <file_path>
    python3 scripts/cos_init.py --internal-call skill_scope_allows <skill_dir>
    python3 scripts/cos_init.py --internal-call install_rule <name> <rules_source> <dest1>[:<dest2>...]
    python3 scripts/cos_init.py --internal-call install_hook <name> <hooks_source> <hooks_dest>
    python3 scripts/cos_init.py --internal-call install_skill_dir <skill_dir> <kernel_dest> <driver_dest>
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

try:
    import yaml
except ImportError:  # PyYAML is optional for stdlib-only internal calls.
    yaml = None  # type: ignore[assignment]
_YAML_ERRORS = (OSError, AttributeError) if yaml is None else (OSError, yaml.YAMLError, AttributeError)

# ── Repository root (cos source directory) ───────────────────────────
COS_SOURCE_DIR = Path(__file__).parent.parent.resolve()
if str(COS_SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(COS_SOURCE_DIR))

from lib.script_io import write_json as _write_json_if_changed


def _load_harness_projection_registry() -> dict[str, object]:
    registry_path = COS_SOURCE_DIR / "manifests" / "harness-projection-registry.json"
    try:
        return json.loads(registry_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Missing shared harness registry: {registry_path}. Run scripts/generate_harness_projection_registry.py") from exc


def _registry_harnesses() -> list[dict[str, object]]:
    rows = _load_harness_projection_registry().get("harnesses", [])
    return [row for row in rows if isinstance(row, dict)]


def _implemented_registry_harnesses() -> list[dict[str, object]]:
    return [row for row in _registry_harnesses() if row.get("status") == "implemented"]


_SUPPORTED_HARNESS_ROWS = _implemented_registry_harnesses()
SUPPORTED_HARNESSES = tuple(str(row["id"]) for row in _SUPPORTED_HARNESS_ROWS)
STRUCTURAL_INSTRUCTION_HARNESSES = {
    str(row["id"])
    for row in _SUPPORTED_HARNESS_ROWS
    if row.get("id") not in {"claude", "codex", "shell-ci"}
}
SHELL_CI_HARNESSES = {str(row["id"]) for row in _SUPPORTED_HARNESS_ROWS if row.get("id") == "shell-ci"}
HARNESS_SETTINGS = {
    str(row["id"]): (str(row.get("primary_settings_path") or ".cognitive-os/install-meta.json"), str(row.get("primary_settings_path") or ".cognitive-os/install-meta.json"))
    for row in _SUPPORTED_HARNESS_ROWS
}


# ── ADR-093 canonical mode constants ─────────────────────────────────
DEFAULT_RULES = (
    "trust-score acceptance-criteria closed-loop-prompts definition-of-done "
    "agent-quality adaptive-bypass phase-aware-agents token-economy "
    "responsiveness credential-management content-policy license-policy research-first-protocol error-learning "
    "model-routing result-management"
).split()

DEFAULT_HOOKS = (
    "error-learning error-pipeline result-truncator session-init host-tool-doctor session-cleanup "
    "user-prompt-capture session-wrapup-trigger session-heartbeat memory-prefetch "
    "clarification-gate blast-radius scope-proportionality bash-hot-path-dispatcher provenance-scan orchestrator-claim-gate "
    "error-pattern-detector auto-refine auto-verify dod-gate "
    "trust-score-validator skill-metrics-tracker inject-phase-context stack-detector "
    "pre-compaction-flush rate-limiter large-file-advisor secret-detector content-policy "
    "research-compliance-guard "
    "doc-sync-detector auto-checkpoint claim-validator completion-gate "
    "clarification-interceptor agent-checkpoint session-sanity confidentiality-enforcer "
    "session-learning crash-recovery teammate-idle task-created task-completed"
).split()

DEFAULT_SKILLS = (
    "compose-prompt exhaustive-prompt cos-status auto-refine "
    "verification-before-completion plan-feature session-backlog resource-governor "
).split()

# Core rules kept after efficiency-profile filtering (default tier)
COS_INIT_CORE_RULES = [
    "RULES-COMPACT.md",
    "adaptive-bypass.md",
    "acceptance-criteria.md",
    "agent-quality.md",
    "trust-score.md",
    "definition-of-done.md",
    "phase-aware-agents.md",
    "closed-loop-prompts.md",
    "token-economy.md",
    "responsiveness.md",
    "agent-security.md",
    "credential-management.md",
    "content-policy.md",
    "license-policy.md",
    "research-first-protocol.md",
    "error-learning.md",
]

INSTALL_BOUNDARY_MANIFEST = COS_SOURCE_DIR / "manifests" / "primitive-install-boundary.yaml"


def _load_install_boundary(mode: str) -> dict[str, object]:
    """Load the profile distribution boundary used by consumer installs.

    ADR-093 keeps `core` as an alias for the default profile. The lifecycle
    manifest tracks broad primitive state, while this boundary is the runtime
    install contract: default/core may project only entries explicitly listed
    with the `core` distribution.
    """
    profile = "full" if mode == "--full" else "default"
    try:
        if yaml is None:
            raise OSError("PyYAML unavailable")
        manifest = yaml.safe_load(INSTALL_BOUNDARY_MANIFEST.read_text(encoding="utf-8")) or {}
    except _YAML_ERRORS:
        return {
            "profile": profile,
            "active_distribution": "full" if profile == "full" else "core",
            "primitives": {},
        }
    profiles = manifest.get("profiles") if isinstance(manifest, dict) else None
    row = profiles.get(profile, {}) if isinstance(profiles, dict) else {}
    if not isinstance(row, dict):
        row = {}
    return {
        "profile": profile,
        "active_distribution": str(row.get("active_distribution") or ("full" if profile == "full" else "core")),
        "primitive_distribution": str(row.get("primitive_distribution") or ("explicit" if profile == "full" else "core")),
        "primitives": row.get("primitives") if isinstance(row.get("primitives"), dict) else {},
    }


def _boundary_names(boundary: dict[str, object], kind: str, fallback: tuple[str, ...] | list[str]) -> list[str]:
    primitives = boundary.get("primitives")
    if not isinstance(primitives, dict):
        return list(fallback)
    raw_items = primitives.get(kind)
    if not isinstance(raw_items, list):
        return list(fallback)

    names: list[str] = []
    for item in raw_items:
        if not isinstance(item, str):
            continue
        path = Path(item)
        if kind == "hooks" and path.suffix == ".sh":
            names.append(path.stem)
        elif kind == "rules" and path.suffix == ".md":
            names.append(path.stem)
        elif kind == "skills":
            # skills/name/SKILL.md → name
            if path.name == "SKILL.md" and path.parent.name:
                names.append(path.parent.name)
            else:
                names.append(path.name)
    return names or list(fallback)


# ── Migrated functions ───────────────────────────────────────────────

def detect_harness(project_root: str = ".") -> str:
    """Detect the active harness for a project directory.

    Inlined from scripts/_lib/settings-driver.sh::cos_detect_harness.
    Detects the active harness (claude|codex plus structural instruction harnesses) by inspecting filesystem markers
    and environment variables. Priority order matches the bash implementation
    exactly (parity required for strangler-fig correctness):

      1. COGNITIVE_OS_HARNESS env var (explicit override)
      2. .cognitive-os/install-meta.json harness field              → installed harness
      3. .codex/hooks.json present AND .claude/settings.json absent  → codex
      4. .claude/settings.json present AND .codex/hooks.json absent  → claude
      5. CODEX_PROJECT_DIR / CODEX_SESSION_ID / CODEX_HOME env vars  → codex
      6. Default → claude
    """
    root = Path(project_root).resolve()

    # Priority 1: explicit env override
    explicit = os.environ.get("COGNITIVE_OS_HARNESS", "")
    if explicit:
        return explicit

    meta_path = root / ".cognitive-os" / "install-meta.json"
    if meta_path.is_file():
        try:
            meta_harness = json.loads(meta_path.read_text(encoding="utf-8")).get("harness")
        except (OSError, json.JSONDecodeError):
            meta_harness = None
        if meta_harness in SUPPORTED_HARNESSES:
            return str(meta_harness)

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
    """Return whether a SCOPE-tagged file belongs in the requested install surface.

    ADR-320 records the current product boundary: ``project`` and ``both`` are
    backward-compatible aliases for the same consumer filtered install surface;
    only ``all`` is a distinct maintainer/self-hosting superset. Files without a
    SCOPE header are universal and always allowed.
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
    """Return True when a skill may be installed for the requested scope.

    The canonical `<!-- SCOPE: ... -->` marker takes precedence over legacy
    `audience:` frontmatter. Several OS-maintainer skills are user-invocable and
    historically declared `audience: both`; without marker precedence they leak
    into consumer-project installs despite `SCOPE: os-only`.
    """
    skill_md = Path(skill_dir) / "SKILL.md"

    # No SKILL.md → allow (matches historical behavior).
    if not skill_md.is_file():
        return True

    # If scope is "all", never filter.
    if install_scope == "all":
        return True

    try:
        lines = skill_md.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return True

    import re as _re

    for line in lines[:8]:
        match = _re.search(r"<!--\s*SCOPE:\s*([A-Za-z0-9_-]+)\s*-->", line)
        if not match:
            continue
        scope_marker = match.group(1).strip()
        if scope_marker in ("project", "both"):
            return True
        if scope_marker == "os-only":
            return False
        return True

    # Legacy fallback: extract audience/scope field from frontmatter.
    audience = ""
    for line in lines:
        stripped = line.rstrip("\n")
        if stripped.startswith(("audience:", "scope:")):
            parts = stripped.split(":", 1)
            if len(parts) == 2:
                audience = parts[1].translate(str.maketrans("", "", " \'\"\r"))
            break

    # No audience field → allow.
    if not audience:
        return True

    if audience in ("project", "both", "adopters", "human"):
        return True
    if audience in ("os", "os-dev", "os-only"):
        return False
    # Unknown → allow (be permissive).
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

    Takes a full skill directory path, kernel dest, optional driver dest.
    Calls skill_scope_allows() to filter. Then:
      - rm -rf kernel/<name> [driver/<name>]
      - cp -r skill_dir kernel/<name>
      - when a driver dest is provided:
        ln -s ../../.cognitive-os/skills/cos/<name> driver/<name>  (relative symlink)

    Driver destinations are harness views over canonical `.cognitive-os/skills/cos`.
    Claude projects use `.claude/skills`; Codex/OpenAI projects use `.agents/skills`.

    Returns one of: "installed", "skipped" (scope-filtered), "error".
    """
    skill_path = Path(skill_dir)
    skill_name = skill_path.name

    # skill_scope_allows "$skill_dir" || return 0
    if not skill_scope_allows(str(skill_path), install_scope=install_scope):
        return "skipped"

    kernel_dest = Path(skill_dest_kernel) / skill_name
    driver_dest = Path(skill_dest_driver) / skill_name if skill_dest_driver else None

    try:
        # rm -rf "$SKILL_DEST_KERNEL/$skill_name" ["$SKILL_DEST_DRIVER/$skill_name"]
        if kernel_dest.exists() or kernel_dest.is_symlink():
            if kernel_dest.is_symlink() or kernel_dest.is_file():
                kernel_dest.unlink()
            else:
                shutil.rmtree(str(kernel_dest))
        if driver_dest is not None and (driver_dest.exists() or driver_dest.is_symlink()):
            if driver_dest.is_symlink() or driver_dest.is_file():
                driver_dest.unlink()
            else:
                shutil.rmtree(str(driver_dest))

        # cp -r "$skill_dir" "$SKILL_DEST_KERNEL/$skill_name"
        Path(skill_dest_kernel).mkdir(parents=True, exist_ok=True)
        shutil.copytree(str(skill_path), str(kernel_dest))

        if driver_dest is not None:
            # ln -s "../../.cognitive-os/skills/cos/$skill_name" "$SKILL_DEST_DRIVER/$skill_name"
            # Relative symlink (matches bash exactly)
            Path(skill_dest_driver).mkdir(parents=True, exist_ok=True)
            symlink_target = f"../../.cognitive-os/skills/cos/{skill_name}"
            driver_dest.symlink_to(symlink_target)
    except OSError as exc:
        print(f"cos_init.py: install_skill_dir '{skill_name}' failed: {exc}", file=sys.stderr)
        return "error"

    return "installed"


# ── Internal-call dispatcher ──────────────────────────────────────────

_INTERNAL_DISPATCH: dict[str, Callable[..., object]] = {
    "detect_harness": detect_harness,
    "scope_allows": scope_allows,
    "skill_scope_allows": skill_scope_allows,
    "install_rule": install_rule,
    "install_hook": install_hook,
    "install_skill_dir": install_skill_dir,
}


def _run_internal_call(function_name: str, extra_args: list[str]) -> int:
    """Dispatch --internal-call invocations from the bash shim (backward compat)."""
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
        description="Bootstrap Cognitive OS in a project.",
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
    parser.add_argument("--harness", choices=list(SUPPORTED_HARNESSES),
                        default=None,
                        help="Target harness. Overrides auto-detection.")
    # Internal dispatcher (kept for backward compat)
    parser.add_argument("--internal-call", dest="internal_call", metavar="FUNCTION",
                        help=argparse.SUPPRESS)
    return parser


# ── Helper: detect project name ───────────────────────────────────────

def _detect_project_name(project_dir: Path) -> str:
    """Port of the project-name detection block (cos-init.sh lines 219-230)."""
    # package.json: jq -r '.name // empty'
    pkg = project_dir / "package.json"
    if pkg.is_file():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8", errors="replace"))
            name = data.get("name", "")
            if name:
                return name
        except (json.JSONDecodeError, OSError):
            pass

    # go.mod: head -1 | sed 's/module //' | sed 's|.*/||'
    go_mod = project_dir / "go.mod"
    if go_mod.is_file():
        try:
            first_line = go_mod.read_text(encoding="utf-8", errors="replace").splitlines()[0]
            if first_line.startswith("module "):
                module_path = first_line[len("module "):].strip()
                return module_path.rsplit("/", 1)[-1]
        except (OSError, IndexError):
            pass

    # pyproject.toml: grep '^name' | head -1 | sed 's/.*= *"//' | sed 's/".*//'
    pyproject = project_dir / "pyproject.toml"
    if pyproject.is_file():
        try:
            for line in pyproject.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.startswith("name"):
                    # name = "some-name" or name = 'some-name'
                    m = re.search(r'=\s*["\']([^"\']+)["\']', line)
                    if m:
                        return m.group(1)
        except OSError:
            pass

    # Fallback: basename of directory
    return project_dir.name


# ── Helper: detect project stack ─────────────────────────────────────

def _detect_stack(project_dir: Path) -> list[str]:
    """Port of the stack detection block (cos-init.sh lines 233-253)."""
    stack = []
    if (project_dir / "package.json").is_file():
        stack.append("node")
    if (project_dir / "go.mod").is_file():
        stack.append("go")
    if any((project_dir / f).is_file() for f in ("pyproject.toml", "setup.py", "requirements.txt")):
        stack.append("python")
    if (project_dir / "Cargo.toml").is_file():
        stack.append("rust")
    if any((project_dir / f).is_file() for f in ("pom.xml", "build.gradle", "build.gradle.kts")):
        stack.append("java")
    return stack


# ── Helper: get COS version ───────────────────────────────────────────

def _get_cos_version(cos_source: Path) -> str:
    """Port of the version-detection block (cos-init.sh lines 629-639)."""
    # Try git tag first
    if (cos_source / ".git").is_dir():
        try:
            result = subprocess.run(
                ["git", "describe", "--tags", "--abbrev=0"],
                cwd=str(cos_source),
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                tag = result.stdout.strip().lstrip("v")
                if tag:
                    return tag
        except (subprocess.TimeoutExpired, OSError):
            pass

    # VERSION file
    version_file = cos_source / "VERSION"
    if version_file.is_file():
        v = version_file.read_text(encoding="utf-8", errors="replace").strip()
        if v:
            return v

    # Short SHA
    if (cos_source / ".git").is_dir():
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=str(cos_source),
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                sha = result.stdout.strip()
                if sha:
                    return sha
        except (subprocess.TimeoutExpired, OSError):
            pass

    return "unknown"




def _is_ephemeral_install(project_path: str, project_name: str = "") -> bool:
    """Return True for disposable test/canary installs that must not be globally registered."""
    name = project_name or ""
    if name.startswith("cos-canary-") or name == "validate-test":
        return True

    path = str(Path(project_path).resolve())
    tmpdir = os.environ.get("TMPDIR", "")
    prefixes = ["/tmp/", "/private/tmp/", "/var/folders/", "/private/var/folders/"]
    if tmpdir:
        prefixes.append(str(Path(tmpdir).resolve()))
    return any(path.startswith(prefix) for prefix in prefixes)


# ── Helper: registry update ───────────────────────────────────────────

def _registry_register(
    project_path: str,
    mode: str,
    version: str,
    project_name: str,
    source_dir: str,
) -> None:
    """Port of cos_registry_register() (cos-registry.sh lines 40-108)."""
    # Skip writing to production registry during pytest
    registry_file_env = os.environ.get("COS_REGISTRY_FILE", "")
    registry_file = Path(registry_file_env) if registry_file_env else Path.home() / ".cognitive-os" / "installations.json"

    if os.environ.get("PYTEST_CURRENT_TEST", "") and not registry_file_env:
        return

    if not registry_file_env and _is_ephemeral_install(project_path, project_name):
        return

    registry_file.parent.mkdir(parents=True, exist_ok=True)

    if not registry_file.is_file():
        registry_file.write_text(json.dumps({"installations": []}, indent=2))

    try:
        data = json.loads(registry_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        data = {"installations": []}

    # Resolve to absolute path
    abs_path = str(Path(project_path).resolve())
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    installations = data.get("installations", [])
    existing_idx = next(
        (i for i, e in enumerate(installations) if e.get("path") == abs_path),
        None,
    )

    entry = {
        "path": abs_path,
        "mode": mode,
        "version": version,
        "project_name": project_name,
        "source": source_dir,
    }
    if existing_idx is not None:
        # Update existing entry
        installations[existing_idx].update(entry)
        installations[existing_idx]["updated_at"] = now
    else:
        # Add new entry
        entry["installed_at"] = now
        entry["updated_at"] = now
        installations.append(entry)

    data["installations"] = installations
    try:
        registry_file.write_text(json.dumps(data, indent=2))
    except OSError as exc:
        print(f"Warning: could not update registry: {exc}", file=sys.stderr)


# ── Helper: update .gitignore ─────────────────────────────────────────

def _update_gitignore(project_dir: Path) -> None:
    """Port of the .gitignore update block (cos-init.sh lines 666-697)."""
    cos_gitignore_patterns = [
        "# Cognitive OS runtime (not committed)",
        ".cognitive-os/sessions/",
        ".cognitive-os/metrics/",
        ".cognitive-os/tasks/",
        ".cognitive-os/checkpoints/",
        ".cognitive-os/dynamic-tools/",
        ".cognitive-os/rate-limit-state.json",
        ".cognitive-os/install-meta.json",
        "",
        "# Cognitive OS local settings",
        ".claude/settings.local.json",
    ]

    gitignore = project_dir / ".gitignore"
    if gitignore.is_file():
        existing = gitignore.read_text(encoding="utf-8", errors="replace")
        to_add = []
        for pattern in cos_gitignore_patterns:
            # Skip comments and empty lines for dedup check (mirrors bash logic)
            if not pattern or pattern.startswith("#"):
                continue
            if pattern not in existing:
                to_add.append(pattern)
        if to_add:
            with gitignore.open("a", encoding="utf-8") as fh:
                for p in to_add:
                    fh.write(p + "\n")
    else:
        with gitignore.open("w", encoding="utf-8") as fh:
            for pattern in cos_gitignore_patterns:
                fh.write(pattern + "\n")


# ── Helper: write cognitive-os.yaml ──────────────────────────────────

def _write_cognitive_os_yaml(
    project_dir: Path,
    project_name: str,
    stack: list[str],
    mode: str,
) -> None:
    """Port of the cognitive-os.yaml creation block (cos-init.sh lines 464-513)."""
    yaml_path = project_dir / "cognitive-os.yaml"
    if yaml_path.is_file():
        print("Existing cognitive-os.yaml preserved")
        return

    # Build stack list
    try:
        import yaml as _yaml  # pyyaml
        stack_list = stack if stack else []
        config = {
            "project": {
                "name": project_name,
                "phase": "reconstruction",
                "stack": stack_list,
            },
            "sessions": {
                "concurrency": True,
                "isolation": "per-session",
                "lock_strategy": "advisory",
                "lock_timeout_seconds": 300,
                "cleanup_on_exit": True,
            },
            "models": {
                "routing": {
                    "default": "sonnet",
                    "design": "opus",
                    "implementation": "sonnet",
                    "debugging": "opus",
                    "documentation": "haiku",
                }
            },
            "quality": {
                "coverage": {"minimum": 80},
                "auto_verify": True,
                "verification_retries": 3,
            },
            "resources": {
                "budget": {
                    "monthly_limit_usd": 200,
                    "daily_alert_usd": 10,
                    "per_agent_max_usd": 2.00,
                }
            },
            "model_capability": {"level": 3},
        }
        content = f"# Cognitive OS Configuration — generated by cos-init ({mode})\n"
        content += _yaml.dump(config, default_flow_style=False, allow_unicode=True)
    except ImportError:
        # Fallback: manual string construction (no pyyaml)
        stack_lines = "".join(f"      - {s}\n" for s in stack) if stack else ""
        content = f"""# Cognitive OS Configuration — generated by cos-init ({mode})
project:
  name: {project_name}
  phase: reconstruction
  stack:
{stack_lines}
sessions:
  concurrency: true
  isolation: per-session
  lock_strategy: advisory
  lock_timeout_seconds: 300
  cleanup_on_exit: true

models:
  routing:
    default: sonnet
    design: opus
    implementation: sonnet
    debugging: opus
    documentation: haiku

quality:
  coverage:
    minimum: 80
  auto_verify: true
  verification_retries: 3

resources:
  budget:
    monthly_limit_usd: 200
    daily_alert_usd: 10
    per_agent_max_usd: 2.00

model_capability:
  level: 3
"""

    yaml_path.write_text(content, encoding="utf-8")
    print("Created cognitive-os.yaml")


# ── Helper: apply efficiency profile ──────────────────────────────────

def _apply_efficiency_profile(
    mode: str,
    project_dir: Path,
    rule_dests: list[str],
) -> int:
    """Port of the efficiency-profile filtering block (cos-init.sh lines 515-583).

    Returns the final rules_installed count.
    """
    # Determine profile
    efficiency_profile = "full" if mode == "--full" else "default"

    yaml_path = project_dir / "cognitive-os.yaml"
    if yaml_path.is_file():
        try:
            text = yaml_path.read_text(encoding="utf-8", errors="replace")
            m = re.search(r'^efficiency:\s*\n\s+profile:\s*([^\s#]+)', text, re.MULTILINE)
            if m:
                ep = m.group(1).strip().strip("'\"")
                if ep in ("default", "full"):
                    efficiency_profile = ep
                elif ep in ("lean", "standard", "minimal"):
                    print(
                        f"Note: cognitive-os.yaml efficiency.profile='{ep}' → 'default' (ADR-093).",
                        file=sys.stderr,
                    )
                    efficiency_profile = "default"
                elif ep:
                    print(
                        f"Warning: unknown efficiency.profile='{ep}' in cognitive-os.yaml → treating as 'default'.",
                        file=sys.stderr,
                    )
                    efficiency_profile = "default"
        except OSError:
            pass

    if efficiency_profile == "default":
        for rules_dir in rule_dests:
            rdir = Path(rules_dir)
            if not rdir.is_dir():
                continue
            for rule_path in sorted(rdir.glob("*.md")):
                base = rule_path.name
                if base not in COS_INIT_CORE_RULES:
                    rule_path.unlink(missing_ok=True)

    # Recount: use the driver dest (first writable dest is fine; use the cos driver)
    count = 0
    for rules_dir in rule_dests:
        rdir = Path(rules_dir)
        if rdir.is_dir():
            count = sum(1 for _ in rdir.glob("*.md"))
            break
    return count


# ── Helper: harness settings generation ──────────────────────────────


def _upsert_agents_md_for_kimi(project_dir: Path, common_body: str) -> None:
    agents = project_dir / "AGENTS.md"
    start = "<!-- COGNITIVE_OS_KIMI_START -->"
    end = "<!-- COGNITIVE_OS_KIMI_END -->"
    block = (
        f"{start}\n"
        "# Cognitive OS for Kimi Code CLI\n\n"
        + common_body
        + "\nRun Kimi from this project root, or pass `--work-dir .`. "
        "If using the projected MCP placeholder, pass `--mcp-config-file .kimi/mcp.json`.\n"
        f"{end}\n"
    )
    if agents.exists():
        text = agents.read_text(encoding="utf-8")
        if start in text and end in text:
            before = text.split(start, 1)[0]
            after = text.split(end, 1)[1]
            agents.write_text(before + block + after.lstrip("\n"), encoding="utf-8")
        else:
            sep = "" if text.endswith("\n") else "\n"
            agents.write_text(text + sep + "\n" + block, encoding="utf-8")
    else:
        agents.write_text(block, encoding="utf-8")


def _upsert_agents_md_block(project_dir: Path, marker_slug: str, title: str, body: str, extra: str = "") -> None:
    """Append or replace a bounded Cognitive OS block in project AGENTS.md."""
    agents = project_dir / "AGENTS.md"
    start = f"<!-- COGNITIVE_OS_{marker_slug.upper().replace('-', '_')}_START -->"
    end = f"<!-- COGNITIVE_OS_{marker_slug.upper().replace('-', '_')}_END -->"
    block = (
        f"{start}\n"
        f"# {title}\n\n"
        f"{body}\n"
        f"{extra}\n"
        "Proof boundary: this is account-free structural projection of project instructions/config only. "
        "It does not prove account-backed runtime behavior or native Claude/Codex lifecycle hook parity.\n"
        f"{end}\n"
    )
    if agents.exists():
        text = agents.read_text(encoding="utf-8")
        if start in text and end in text:
            before = text.split(start, 1)[0]
            after = text.split(end, 1)[1]
            agents.write_text(before + block + after.lstrip("\n"), encoding="utf-8")
        else:
            sep = "" if text.endswith("\n") else "\n"
            agents.write_text(text + sep + "\n" + block, encoding="utf-8")
    else:
        agents.write_text(block, encoding="utf-8")

def _write_structural_instruction_harness_settings(project_dir: Path, cos_source: Path, harness: str, mode: str) -> None:
    """Write project-local instruction/config files for harnesses without native COS hooks.

    These drivers prove consumer-project projection of instructions, rules, skills,
    and optional MCP placeholders. They do not claim native lifecycle hook parity.
    """

    common_body = (
        "# Cognitive OS\n\n"
        "This project has Cognitive OS installed under `.cognitive-os/`.\n\n"
        "## Portable Cognitive OS Contract\n\n"
        "- Read `cognitive-os.yaml` when present for phase and project configuration.\n"
        "- Use `.cognitive-os/rules/cos/RULES-COMPACT.md` as the compact governance entrypoint; "
        "load full rules from `.cognitive-os/rules/cos/` only when their contextual triggers match.\n"
        "- Use `.cognitive-os/skills/cos/` for reusable SKILL.md procedures. If this harness supports "
        "slash commands, invoke the matching `/skill-name`; otherwise open the matching `SKILL.md` and follow it.\n"
        "- State or infer acceptance criteria before implementation, then verify them with concrete commands "
        "before claiming completion.\n"
        "- For medium or larger feature work, prefer the local consumer SDD lane: `cos sdd next --feature <slug>`, "
        "review generated requirements/design/tasks, run `cos sdd approve <slug>` before implementation, "
        "then complete traceability and run `cos sdd review <slug>`. If the `cos` binary is unavailable, "
        "use the same `.cognitive-os/workflows/sdd/` artifact layout manually.\n"
        "- Use Engram when available: search memory before repeating past work, save decisions/bugfixes/"
        "discoveries/configuration changes, and write a session summary before ending substantial work.\n"
        "- If `.cognitive-os/seed-memory.md` exists and its Inherited Knowledge section still has only the "
        "placeholder, do the one-time Engram retrieval described there and avoid duplicating entries.\n"
        "- Structural projection boundary: this file provides project instructions, rule/skill references, "
        "and proof-level guardrails. Do not claim Claude/Codex native lifecycle hook parity unless this "
        "harness exposes equivalent lifecycle events and the mapping has been runtime-smoked.\n"
        "- Preserve the repository `AGENTS.md` contract when present.\n"
    )

    if harness == "agents-md":
        _upsert_agents_md_block(
            project_dir,
            "agents_md",
            "Cognitive OS for AGENTS.md-native tools",
            common_body,
            "AGENTS.md is the universal markdown baseline for tools that read the Agentic AI Foundation project guidance format. Use host-specific adapters only for advanced native surfaces.\n",
        )
        print("Created AGENTS.md with universal COS projection")
        return

    if harness == "opencode":
        _upsert_agents_md_block(
            project_dir,
            "opencode",
            "Cognitive OS for opencode",
            common_body,
            "opencode loads this through `opencode.json` alongside the canonical COS rule and skill paths.\n",
        )
        _write_json_if_changed(
            project_dir / "opencode.json",
            {
                "$schema": "https://opencode.ai/config.json",
                "instructions": [
                    "AGENTS.md",
                    ".cognitive-os/rules/cos/RULES-COMPACT.md",
                    ".cognitive-os/rules/cos/*.md",
                    ".cognitive-os/skills/cos/*/SKILL.md",
                ],
                "plugin": [".opencode/plugins/cos-primitive-guard.js"],
                "mcp": {},
                "permission": {"bash": "ask", "edit": "ask"},
                "experimental": {
                    "cognitive_os_hooks": ".opencode/cos-hooks.json",
                },
            },
        )
        plugin_source = cos_source / "packages" / "opencode-adapter" / "plugins" / "cos-primitive-guard.js"
        plugin_target = project_dir / ".opencode" / "plugins" / "cos-primitive-guard.js"
        if plugin_source.exists():
            plugin_target.parent.mkdir(parents=True, exist_ok=True)
            plugin_target.write_text(plugin_source.read_text(encoding="utf-8"), encoding="utf-8")
        driver = cos_source / "scripts" / "_lib" / "settings-driver-opencode.sh"
        if driver.exists():
            subprocess.run(
                ["bash", str(driver)],
                cwd=project_dir,
                env={**os.environ, "PROJECT_DIR": str(project_dir), "PROFILE": "full" if mode == "--full" else "default"},
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
        print("Created opencode.json with COS instruction projection, native primitive guard plugin, and COS hook projection")
        return

    if harness == "vscode-copilot":
        instructions = project_dir / ".github" / "copilot-instructions.md"
        instructions.parent.mkdir(parents=True, exist_ok=True)
        instructions.write_text(common_body, encoding="utf-8")
        _write_json_if_changed(
            project_dir / ".vscode" / "mcp.json",
            {"servers": {}},
        )
        print("Created .github/copilot-instructions.md and .vscode/mcp.json with COS projection")
        return



    if harness == "kimi-code":
        _upsert_agents_md_for_kimi(project_dir, common_body)
        _write_json_if_changed(
            project_dir / ".kimi" / "mcp.json",
            {"mcpServers": {}},
        )
        (project_dir / ".kimi" / "README.md").write_text(
            "# Kimi Code CLI Cognitive OS Projection\n\n"
            "Run from the project root so Kimi loads `AGENTS.md`, or use `kimi --work-dir .`.\n"
            "Use `kimi --mcp-config-file .kimi/mcp.json` when opting into the projected MCP placeholder.\n"
            "This structural projection does not configure credentials or claim native lifecycle hook parity.\n",
            encoding="utf-8",
        )
        print("Created AGENTS.md and .kimi/mcp.json with Kimi Code CLI COS projection")
        return

    if harness == "qwen-code":
        qwen_md = project_dir / "QWEN.md"
        qwen_md.write_text(common_body, encoding="utf-8")
        _write_json_if_changed(
            project_dir / ".qwen" / "settings.json",
            {
                "context": {
                    "fileName": ["QWEN.md", "AGENTS.md", ".cognitive-os/rules/cos/RULES-COMPACT.md"],
                    "includeDirectories": [".cognitive-os/rules/cos", ".cognitive-os/skills/cos"],
                    "loadFromIncludeDirectories": True,
                    "fileFiltering": {"respectGitIgnore": True},
                },
                "mcpServers": {},
                "tools": {"approvalMode": "default"},
            },
        )
        print("Created .qwen/settings.json and QWEN.md with COS projection")
        return



    if harness == "gemini-cli":
        gemini_md = project_dir / "GEMINI.md"
        gemini_md.write_text(
            common_body
            + "\nGemini CLI should load this file through `contextFileName` and project-local `.gemini/settings.json`.\n",
            encoding="utf-8",
        )
        _write_json_if_changed(
            project_dir / ".gemini" / "settings.json",
            {
                "contextFileName": ["GEMINI.md", "AGENTS.md"],
                "includeDirectories": [".cognitive-os/rules/cos", ".cognitive-os/skills/cos"],
                "loadMemoryFromIncludeDirectories": True,
                "fileFiltering": {"respectGitIgnore": True, "enableRecursiveFileSearch": True},
                "mcpServers": {},
                "autoAccept": False,
            },
        )
        print("Created .gemini/settings.json and GEMINI.md with Gemini CLI COS projection")
        return

    if harness == "warp":
        _upsert_agents_md_block(
            project_dir,
            "warp",
            "Cognitive OS for Warp Agent",
            common_body,
            "Warp project rules use root `AGENTS.md` by default. Keep `WARP.md` absent unless the operator intentionally wants Warp's documented precedence over `AGENTS.md`.\n",
        )
        (project_dir / ".warp" / "README.md").write_text(
            "# Warp Cognitive OS Projection\n\n"
            "Warp reads root `AGENTS.md` as project rules. This directory is informational only; no user-global Warp settings are written.\n",
            encoding="utf-8",
        )
        print("Created AGENTS.md with Warp COS projection")
        return

    if harness == "amp-code":
        _upsert_agents_md_block(
            project_dir,
            "amp",
            "Cognitive OS for Amp",
            common_body,
            "Amp supports @-mentions from AGENTS.md. Treat `.cognitive-os/rules/cos/RULES-COMPACT.md` and `.cognitive-os/skills/cos/` as the COS entrypoints.\n",
        )
        _write_json_if_changed(project_dir / ".amp" / "settings.json", {"amp.mcpServers": {}})
        print("Created AGENTS.md and .amp/settings.json with Amp COS projection")
        return

    if harness == "jetbrains-junie":
        junie = project_dir / ".junie" / "AGENTS.md"
        junie.parent.mkdir(parents=True, exist_ok=True)
        junie.write_text(
            "# Cognitive OS for JetBrains Junie\n\n"
            + common_body
            + "\nJunie's preferred project guideline location is `.junie/AGENTS.md`; root `AGENTS.md` remains available for other AGENTS.md-native tools.\n",
            encoding="utf-8",
        )
        (project_dir / ".junie" / "README.md").write_text(
            "# Junie Cognitive OS Projection\n\n"
            "Junie reads `.junie/AGENTS.md` by default. MCP configuration is intentionally not generated because JetBrains exposes it through IDE project settings and an mcp.json editor flow.\n",
            encoding="utf-8",
        )
        print("Created .junie/AGENTS.md with JetBrains Junie COS projection")
        return

    if harness == "qoder":
        _upsert_agents_md_block(
            project_dir,
            "qoder",
            "Cognitive OS for Qoder CLI",
            common_body,
            "Qoder CLI uses project `AGENTS.md` as its memory file and project `.mcp.json` for committed MCP server definitions.\n",
        )
        _write_json_if_changed(project_dir / ".mcp.json", {"mcpServers": {}})
        _write_json_if_changed(project_dir / ".qoder" / "settings.json", {"permissions": {"ask": [], "allow": [], "deny": []}})
        print("Created AGENTS.md, .mcp.json, and .qoder/settings.json with Qoder COS projection")
        return

    if harness == "factory-droid":
        _upsert_agents_md_block(
            project_dir,
            "factory_droid",
            "Cognitive OS for Factory Droid",
            common_body,
            "Factory Droid reads project `AGENTS.md`, can load project `.factory/skills/`, project `.factory/mcp.json`, and project hooks from `.factory/settings.json`.\n",
        )
        _write_json_if_changed(project_dir / ".factory" / "mcp.json", {"mcpServers": {}})
        _write_json_if_changed(project_dir / ".factory" / "settings.json", {"hooks": {}})
        skill = project_dir / ".factory" / "skills" / "cognitive-os" / "SKILL.md"
        skill.parent.mkdir(parents=True, exist_ok=True)
        skill.write_text(
            "---\n"
            "name: cognitive-os\n"
            "description: Use when Factory Droid needs Cognitive OS governance, rules, skills, verification, or proof-level boundaries.\n"
            "---\n\n"
            "# Cognitive OS\n\n"
            "Use `.cognitive-os/rules/cos/RULES-COMPACT.md` as the compact governance entrypoint. "
            "Use `.cognitive-os/skills/cos/` for projected COS skills. Do not claim native lifecycle parity unless Factory hooks are explicitly mapped and runtime-smoked.\n",
            encoding="utf-8",
        )
        print("Created AGENTS.md, .factory/mcp.json, .factory/settings.json, and .factory/skills/cognitive-os/SKILL.md with Factory Droid COS projection")
        return



    if harness == "cline":
        rule = project_dir / ".clinerules" / "cognitive-os.md"
        rule.parent.mkdir(parents=True, exist_ok=True)
        rule.write_text(
            "# Cognitive OS for Cline\n\n"
            + common_body
            + "\nCline should load this workspace rule as project instructions. MCP configuration is intentionally not generated until a stable project-local Cline MCP path is signed.\n",
            encoding="utf-8",
        )
        (project_dir / ".cline" / "README.md").write_text(
            "# Cline Cognitive OS Projection\n\n"
            "This structural projection writes `.clinerules/cognitive-os.md` only. It does not write user-global Cline MCP settings or credentials.\n",
            encoding="utf-8",
        )
        print("Created .clinerules/cognitive-os.md with Cline COS projection")
        return

    if harness == "continue-dev":
        rule = project_dir / ".continue" / "rules" / "cognitive-os.md"
        rule.parent.mkdir(parents=True, exist_ok=True)
        rule.write_text(
            "---\n"
            "name: Cognitive OS\n"
            "description: Cognitive OS governance, skills, and proof-level boundary\n"
            "alwaysApply: true\n"
            "---\n\n"
            + common_body,
            encoding="utf-8",
        )
        _write_json_if_changed(project_dir / ".continue" / "mcpServers" / "cognitive-os.json", {"mcpServers": {}})
        print("Created .continue/rules/cognitive-os.md and .continue/mcpServers/cognitive-os.json with Continue COS projection")
        return

    if harness == "kilo-code":
        _upsert_agents_md_block(
            project_dir,
            "kilo_code",
            "Cognitive OS for Kilo Code",
            common_body,
            "Kilo Code should use this AGENTS.md block plus `.kilocode/rules/cognitive-os.md` as project instructions.\n",
        )
        rule = project_dir / ".kilocode" / "rules" / "cognitive-os.md"
        rule.parent.mkdir(parents=True, exist_ok=True)
        rule.write_text("# Cognitive OS for Kilo Code\n\n" + common_body, encoding="utf-8")
        _write_json_if_changed(
            project_dir / ".kilo" / "kilo.jsonc",
            {
                "instructions": ["AGENTS.md", ".kilocode/rules/cognitive-os.md", ".cognitive-os/rules/cos/RULES-COMPACT.md"],
                "mcp": {},
                "permissions": {"default": "ask"},
            },
        )
        print("Created AGENTS.md, .kilocode/rules/cognitive-os.md, and .kilo/kilo.jsonc with Kilo COS projection")
        return

    if harness == "zed-ai":
        rules = project_dir / ".rules"
        rules.write_text(
            "# Cognitive OS for Zed AI\n\n"
            + common_body
            + "\nZed loads `.rules` as a project rule surface. MCP/context servers are represented as an empty project-local placeholder.\n",
            encoding="utf-8",
        )
        _write_json_if_changed(project_dir / ".zed" / "settings.json", {"context_servers": {}})
        print("Created .rules and .zed/settings.json with Zed COS projection")
        return

    if harness == "augment-code":
        rule = project_dir / ".augment" / "rules" / "cognitive-os.md"
        rule.parent.mkdir(parents=True, exist_ok=True)
        rule.write_text("# Cognitive OS for Augment\n\n" + common_body, encoding="utf-8")
        _write_json_if_changed(project_dir / ".augment" / "mcp.json", {"mcpServers": {}})
        (project_dir / ".augment" / "README.md").write_text(
            "# Augment/Auggie Cognitive OS Projection\n\n"
            "Use `auggie --rules .augment/rules/cognitive-os.md --mcp-config .augment/mcp.json` from the project root when opting into this structural projection. No user-global Augment settings are written.\n",
            encoding="utf-8",
        )
        print("Created .augment/rules/cognitive-os.md and .augment/mcp.json with Augment COS projection")
        return

    if harness == "goose":
        hints = project_dir / ".goosehints"
        hints.write_text(
            "# Cognitive OS for Goose\n\n"
            + common_body
            + "\nGoose should treat this file as project-local guidance. MCP/server setup remains operator-controlled.\n",
            encoding="utf-8",
        )
        print("Created .goosehints with Goose COS projection")
        return

    if harness == "aider":
        conventions = project_dir / "CONVENTIONS.md"
        conventions.write_text(
            "# Cognitive OS for Aider\n\n"
            + common_body
            + "\nAider should read this file through `.aider.conf.yml` so COS governance becomes project-local context.\n",
            encoding="utf-8",
        )
        (project_dir / ".aider.conf.yml").write_text(
            "read:\n"
            "  - CONVENTIONS.md\n"
            "  - .cognitive-os/rules/cos/RULES-COMPACT.md\n"
            "auto-commits: false\n"
            "yes-always: false\n",
            encoding="utf-8",
        )
        print("Created CONVENTIONS.md and .aider.conf.yml with Aider COS projection")
        return

    if harness == "cursor":
        rule = project_dir / ".cursor" / "rules" / "cognitive-os.mdc"
        rule.parent.mkdir(parents=True, exist_ok=True)
        rule.write_text(
            "---\n"
            "description: Cognitive OS governance, skills, and verification contract\n"
            "alwaysApply: true\n"
            "---\n\n"
            + common_body,
            encoding="utf-8",
        )
        _write_json_if_changed(
            project_dir / ".cursor" / "mcp.json",
            {"mcpServers": {}},
        )
        print("Created .cursor/rules/cognitive-os.mdc and .cursor/mcp.json with COS projection")
        return

    raise ValueError(f"unsupported structural instruction harness: {harness}")



def _install_provenance_scan_guardrail(project_dir: Path, cos_source: Path) -> bool:
    """Install the project-local provenance scanner binary and default policy."""
    bin_dir = project_dir / ".cognitive-os" / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    copied = False
    for name in ("provenance-scan", "provenance_scan.py"):
        src = cos_source / "scripts" / name
        if not src.is_file():
            continue
        dest = bin_dir / name
        shutil.copy2(str(src), str(dest))
        if name == "provenance-scan":
            dest.chmod(dest.stat().st_mode | 0o111)
        copied = True

    policy_src = cos_source / "manifests" / "provenance-scan.yaml"
    policy_dest = project_dir / ".cognitive-os" / "provenance-scan.yaml"
    if policy_src.is_file() and not policy_dest.exists():
        shutil.copy2(str(policy_src), str(policy_dest))
        copied = True
    return copied

def _write_shell_ci_harness_settings(project_dir: Path, cos_source: Path, mode: str) -> None:
    """Project Shell/CI commands and workflow as a first-class harness."""

    profile = "full" if mode == "--full" else "default"
    projector = cos_source / "scripts" / "project_shell_ci.py"
    if not projector.is_file():
        raise FileNotFoundError(projector)
    result = subprocess.run(
        [sys.executable, str(projector), "--project-dir", str(project_dir), "--profile", profile, "--json"],
        cwd=project_dir,
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout)[-500:])
    print("Created .cognitive-os/shell-ci-projection.json and shell/CI driver files")

def _apply_harness_settings(
    project_dir: Path,
    cos_source: Path,
    mode: str,
    harness: str,
    settings_relative_path: str,
    settings_label: str,
) -> None:
    """Port of the settings generation block plus structural instruction harnesses."""
    if harness in STRUCTURAL_INSTRUCTION_HARNESSES:
        _write_structural_instruction_harness_settings(project_dir, cos_source, harness, mode)
        return
    if harness in SHELL_CI_HARNESSES:
        _write_shell_ci_harness_settings(project_dir, cos_source, mode)
        return

    generator = cos_source / "scripts" / "generate-project-settings.sh"
    merge_script = cos_source / "scripts" / "merge-settings.sh"
    settings_path = project_dir / settings_relative_path

    if generator.is_file() and shutil.which("jq"):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp_f:
            generated_tmp = tmp_f.name
        try:
            result = subprocess.run(
                ["bash", str(generator), mode, f"--harness={harness}", f"--output={generated_tmp}"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                if settings_path.is_file():
                    # Merge: keep project hooks, replace COS hooks
                    if merge_script.is_file():
                        import tempfile as _tf
                        with _tf.NamedTemporaryFile(suffix=".json", delete=False) as mf:
                            merged_tmp = mf.name
                        try:
                            merge_result = subprocess.run(
                                ["bash", str(merge_script), str(settings_path),
                                 generated_tmp, merged_tmp],
                                capture_output=True,
                                text=True,
                                timeout=30,
                            )
                            if merge_result.returncode == 0:
                                shutil.move(merged_tmp, str(settings_path))
                                print(f"Merged COS hooks into existing {settings_label}")
                            else:
                                print(
                                    f"Warning: Could not merge settings. Your {settings_label} was preserved."
                                )
                        finally:
                            Path(merged_tmp).unlink(missing_ok=True)
                    else:
                        print(f"Warning: merge-settings.sh not found. Your {settings_label} was preserved.")
                else:
                    settings_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(generated_tmp, str(settings_path))
                    print(f"Created {settings_label} with project-appropriate hook paths")
            else:
                print(
                    f"Warning: generate-project-settings.sh failed. Falling back to copy for {settings_label}."
                )
                _fallback_settings(cos_source, settings_path)
        finally:
            Path(generated_tmp).unlink(missing_ok=True)
    else:
        # No generator or no jq — fallback to direct copy
        _fallback_settings(cos_source, settings_path)


def _fallback_settings(cos_source: Path, settings_path: Path) -> None:
    """Direct copy fallback for settings.json (cos-init.sh lines 614-619)."""
    src = cos_source / ".claude" / "settings.json"
    if src.is_file() and not settings_path.is_file():
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src), str(settings_path))
        print(f"Warning: Created {settings_path} without path transformation (jq missing)")


# ── Full main() ───────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:  # noqa: C901 — port fidelity requires length
    """Full Python init — ports all 12 procedural sections from cos-init.sh."""
    raw_args = list(sys.argv[1:] if argv is None else argv)
    parser = _build_parser()
    parsed, extra = parser.parse_known_args(argv)

    # --internal-call: function dispatcher for backward compat
    if parsed.internal_call:
        return _run_internal_call(parsed.internal_call, extra)

    # ── Resolve mode ──────────────────────────────────────────────────
    mode = parsed.mode or "--default"
    legacy_mode = next((arg for arg in raw_args if arg in ("--minimal", "--standard", "--lean")), "")
    if extra and extra[0] in ("--default", "--full", "--minimal", "--standard", "--lean"):
        mode = extra.pop(0)
        legacy_mode = mode if mode in ("--minimal", "--standard", "--lean") else legacy_mode
    if legacy_mode:
        print(f"Note: ADR-093 collapsed '{legacy_mode}' into '--default'. Using '--default'.", file=sys.stderr)
    if mode in ("--minimal", "--standard", "--lean"):
        mode = "--default"
    if mode not in ("--default", "--full"):
        print(f"Usage: cos_init.py [--default|--full]", file=sys.stderr)
        print("", file=sys.stderr)
        print("  --default  10 curated skills, ~29 standard hooks, 14 core rules (~8K tokens/session)", file=sys.stderr)
        print("  --full     Everything (~142K tokens/session)", file=sys.stderr)
        return 1

    # ── Resolve directories ───────────────────────────────────────────
    cos_source = COS_SOURCE_DIR
    project_dir = Path.cwd().resolve()

    # ── Self-hosting guard ────────────────────────────────────────────
    # If running inside luum-agent-os itself, refuse (use self-install.sh instead).
    if (project_dir / "hooks" / "self-install.sh").is_file() and project_dir == cos_source:
        print("Error: Cannot run cos-init inside luum-agent-os itself.", file=sys.stderr)
        print("       This repo uses self-install.sh for self-hosting.", file=sys.stderr)
        return 1

    # ── Detect harness ────────────────────────────────────────────────
    harness_override = parsed.harness or os.environ.get("COGNITIVE_OS_HARNESS", "")
    if harness_override:
        harness = harness_override
    else:
        harness = detect_harness(str(project_dir))

    if harness not in HARNESS_SETTINGS:
        print(f"Error: unsupported harness '{harness}' (expected one of: {', '.join(SUPPORTED_HARNESSES)}).", file=sys.stderr)
        return 1
    settings_relative_path, settings_label = HARNESS_SETTINGS[harness]

    # ── Scope filter ─────────────────────────────────────────────────
    install_scope = os.environ.get("COS_INSTALL_SCOPE", "both")
    if install_scope not in ("project", "both", "all"):
        print(f"Warning: unknown COS_INSTALL_SCOPE='{install_scope}' → treating as 'both'.", file=sys.stderr)
        install_scope = "both"

    # ── 1. Detect existing project stack ─────────────────────────────
    project_name = _detect_project_name(project_dir)
    detected_stack = _detect_stack(project_dir)
    has_claude_dir = (project_dir / ".claude").is_dir()
    has_docker = any(
        (project_dir / f).is_file()
        for f in ("docker-compose.yml", "docker-compose.yaml", "compose.yml")
    )

    # ── Print header ──────────────────────────────────────────────────
    print(f"=== Cognitive OS Init ({mode}) ===")
    print(f"Harness: {harness}")
    print(f"Scope filter: {install_scope}")
    if install_scope in {"project", "both"}:
        print("Scope surface: consumer-filtered (project and both are equivalent; ADR-320)")
    elif install_scope == "all":
        print("Scope surface: maintainer/self-hosting (includes os-only primitives; ADR-320)")
    print()
    print(f"Project: {project_name}")
    if detected_stack:
        print(f"Stack:   {', '.join(detected_stack)}")
    if has_docker:
        print("Docker:  detected")
    if has_claude_dir:
        print("Claude:  existing .claude/ found (will merge)")
    print()

    # ── 2. Define mode components ─────────────────────────────────────
    # (constants defined at module level: DEFAULT_RULES, DEFAULT_HOOKS, DEFAULT_SKILLS)
    install_boundary = _load_install_boundary(mode)
    active_distribution = str(install_boundary.get("active_distribution") or ("full" if mode == "--full" else "core"))
    default_rules = _boundary_names(install_boundary, "rules", DEFAULT_RULES)
    default_hooks = _boundary_names(install_boundary, "hooks", DEFAULT_HOOKS)
    default_skills = _boundary_names(install_boundary, "skills", DEFAULT_SKILLS)

    # ── 3. Create directory structure ────────────────────────────────
    # SAFETY: replace symlinks with real directories
    for dir_check in (".cognitive-os", ".claude", ".codex", ".cursor", ".github", ".vscode"):
        p = project_dir / dir_check
        if p.is_symlink():
            target = os.readlink(str(p))
            print(f"WARNING: {dir_check} is a symlink ({target}) — replacing with real directory")
            p.unlink()

    driver_dirs = [str(Path(settings_relative_path).parent)]
    if harness == "claude":
        driver_dirs.extend([".claude/rules/cos", ".claude/skills", ".claude/commands"])
    elif harness == "codex":
        driver_dirs.extend([".agents/skills"])
    elif harness == "vscode-copilot":
        driver_dirs.extend([".vscode"])
    elif harness == "cursor":
        driver_dirs.extend([".cursor/rules"])
    elif harness == "qwen-code":
        driver_dirs.extend([".qwen"])
    elif harness == "kimi-code":
        driver_dirs.extend([".kimi"])
    elif harness == "gemini-cli":
        driver_dirs.extend([".gemini"])
    elif harness == "warp":
        driver_dirs.extend([".warp"])
    elif harness == "amp-code":
        driver_dirs.extend([".amp"])
    elif harness == "jetbrains-junie":
        driver_dirs.extend([".junie"])
    elif harness == "qoder":
        driver_dirs.extend([".qoder"])
    elif harness == "factory-droid":
        driver_dirs.extend([".factory", ".factory/skills/cognitive-os"])
    elif harness == "cline":
        driver_dirs.extend([".clinerules", ".cline"])
    elif harness == "continue-dev":
        driver_dirs.extend([".continue/rules", ".continue/mcpServers"])
    elif harness == "kilo-code":
        driver_dirs.extend([".kilocode/rules", ".kilo"])
    elif harness == "zed-ai":
        driver_dirs.extend([".zed"])
    elif harness == "augment-code":
        driver_dirs.extend([".augment/rules"])
    elif harness == "goose":
        driver_dirs.extend([])
    elif harness == "aider":
        driver_dirs.extend(["."])
    elif harness == "shell-ci":
        driver_dirs.extend(["scripts", ".github/workflows", ".cognitive-os/scripts/cos"])

    for d in [
        *driver_dirs,
        ".cognitive-os/rules/cos",
        ".cognitive-os/hooks/cos",
        ".cognitive-os/skills/cos",
        ".cognitive-os/templates/cos",
        ".cognitive-os/metrics",
        ".cognitive-os/sessions",
        ".cognitive-os/tasks",
    ]:
        (project_dir / d).mkdir(parents=True, exist_ok=True)

    # ── 4. Install rules ──────────────────────────────────────────────
    rules_installed = 0
    rules_source = str(cos_source / "rules")
    rule_dest_kernel = str(project_dir / ".cognitive-os" / "rules" / "cos")
    rule_dest_driver = (
        str(project_dir / ".claude" / "rules" / "cos")
        if harness == "claude"
        else ""
    )
    rule_dests = [rule_dest_kernel]
    if rule_dest_driver:
        rule_dests.append(rule_dest_driver)

    if mode == "--full":
        # Install all rules (respecting scope filter)
        for rule_path in sorted(Path(rules_source).glob("*.md")):
            if not scope_allows(str(rule_path), install_scope):
                continue
            for dest_dir in rule_dests:
                shutil.copy2(str(rule_path), str(Path(dest_dir) / rule_path.name))
            rules_installed += 1
    else:
        # Default mode: install only the core rules declared by the install
        # boundary manifest.
        for name in default_rules:
            status = install_rule(name, rules_source, rule_dests)
            if status == "installed":
                rules_installed += 1

    # Always install RULES-COMPACT.md
    compact = Path(rules_source) / "RULES-COMPACT.md"
    if compact.is_file():
        for dest_dir in rule_dests:
            shutil.copy2(str(compact), str(Path(dest_dir) / "RULES-COMPACT.md"))

    # ── 5. Install hooks ─────────────────────────────────────────────
    hooks_installed = 0
    hooks_source = str(cos_source / "hooks")
    hooks_dest = str(project_dir / ".cognitive-os" / "hooks" / "cos")
    Path(hooks_dest).mkdir(parents=True, exist_ok=True)

    if mode == "--full":
        for hook_path in sorted(Path(hooks_source).glob("*.sh")):
            if not scope_allows(str(hook_path), install_scope):
                continue
            dest_path = Path(hooks_dest) / hook_path.name
            shutil.copy2(str(hook_path), str(dest_path))
            dest_path.chmod(dest_path.stat().st_mode | 0o111)
            hooks_installed += 1
        # Copy hook libs if they exist
        hooks_lib = Path(hooks_source) / "_lib"
        if hooks_lib.is_dir():
            dest_lib = Path(hooks_dest) / "_lib"
            if dest_lib.exists():
                shutil.rmtree(str(dest_lib))
            shutil.copytree(str(hooks_lib), str(dest_lib))
        wrapper_src = cos_source / "scripts" / "hook-timing-wrapper.sh"
        if wrapper_src.is_file():
            dest_lib = Path(hooks_dest) / "_lib"
            dest_lib.mkdir(parents=True, exist_ok=True)
            wrapper_dest = dest_lib / "hook-timing-wrapper.sh"
            shutil.copy2(str(wrapper_src), str(wrapper_dest))
            wrapper_dest.chmod(wrapper_dest.stat().st_mode | 0o111)
    else:
        # Default mode: install only the core hooks declared by the install
        # boundary manifest.
        for name in default_hooks:
            status = install_hook(name, hooks_source, hooks_dest)
            if status == "installed":
                hooks_installed += 1
        # Always copy _lib if it exists
        hooks_lib = Path(hooks_source) / "_lib"
        if hooks_lib.is_dir():
            dest_lib = Path(hooks_dest) / "_lib"
            if dest_lib.exists():
                shutil.rmtree(str(dest_lib))
            shutil.copytree(str(hooks_lib), str(dest_lib))
        wrapper_src = cos_source / "scripts" / "hook-timing-wrapper.sh"
        if wrapper_src.is_file():
            dest_lib = Path(hooks_dest) / "_lib"
            dest_lib.mkdir(parents=True, exist_ok=True)
            wrapper_dest = dest_lib / "hook-timing-wrapper.sh"
            shutil.copy2(str(wrapper_src), str(wrapper_dest))
            wrapper_dest.chmod(wrapper_dest.stat().st_mode | 0o111)

    # ── 6. Install skills ─────────────────────────────────────────────
    skills_installed = 0
    skills_source = cos_source / "skills"
    skill_dest_kernel = str(project_dir / ".cognitive-os" / "skills" / "cos")
    if harness == "claude":
        skill_dest_driver = str(project_dir / ".claude" / "skills")
    elif harness == "codex":
        skill_dest_driver = str(project_dir / ".agents" / "skills")
    else:
        skill_dest_driver = ""

    if skills_source.is_dir():
        Path(skill_dest_kernel).mkdir(parents=True, exist_ok=True)
        if skill_dest_driver:
            Path(skill_dest_driver).mkdir(parents=True, exist_ok=True)

        if mode == "--full":
            for skill_dir in sorted(skills_source.iterdir()):
                if not skill_dir.is_dir():
                    continue
                status = install_skill_dir(
                    str(skill_dir), skill_dest_kernel, skill_dest_driver, install_scope
                )
                if status == "installed":
                    skills_installed += 1
        else:
            # Default: install the curated core skills declared by the install
            # boundary manifest.
            for name in default_skills:
                skill_dir = skills_source / name
                if not skill_dir.is_dir():
                    continue
                status = install_skill_dir(
                    str(skill_dir), skill_dest_kernel, skill_dest_driver, install_scope
                )
                if status == "installed":
                    skills_installed += 1

        # Copy CATALOG.md with optional driver symlink projection
        catalog_src = skills_source / "CATALOG.md"
        if catalog_src.is_file():
            catalog_kernel = Path(skill_dest_kernel) / "CATALOG.md"
            shutil.copy2(str(catalog_src), str(catalog_kernel))
            if skill_dest_driver:
                catalog_driver = Path(skill_dest_driver) / "CATALOG.md"
                if catalog_driver.exists() or catalog_driver.is_symlink():
                    catalog_driver.unlink()
                catalog_driver.symlink_to("../../.cognitive-os/skills/cos/CATALOG.md")

    # ── 7. Install templates ──────────────────────────────────────────
    templates_source = cos_source / "templates"
    if templates_source.is_dir():
        tmpl_dest = project_dir / ".cognitive-os" / "templates" / "cos"
        tmpl_dest.mkdir(parents=True, exist_ok=True)
        for tmpl in sorted(templates_source.glob("*.md")):
            if not scope_allows(str(tmpl), install_scope):
                continue
            shutil.copy2(str(tmpl), str(tmpl_dest / tmpl.name))

    # ── 7b. Install repo-local provenance guardrail support ─────────────
    provenance_scan_installed = _install_provenance_scan_guardrail(project_dir, cos_source)

    # ── 8. Create cognitive-os.yaml ──────────────────────────────────
    _write_cognitive_os_yaml(project_dir, project_name, detected_stack, mode)

    # ── 8b. Apply efficiency profile filtering ────────────────────────
    rules_installed = _apply_efficiency_profile(mode, project_dir, rule_dests)

    # ── 9. Create/merge harness settings ─────────────────────────────
    _apply_harness_settings(
        project_dir, cos_source, mode, harness, settings_relative_path, settings_label
    )

    # ── 10. Save install metadata ─────────────────────────────────────
    registry_source = os.environ.get("COS_ORIGINAL_SOURCE", str(cos_source))
    cos_version = _get_cos_version(Path(registry_source))

    meta = {
        "mode": mode.lstrip("-"),
        "version": cos_version,
        "source": registry_source,
        "harness": harness,
        "active_distribution": active_distribution,
        "install_boundary_manifest": str(INSTALL_BOUNDARY_MANIFEST.relative_to(COS_SOURCE_DIR)),
        "settings_driver": settings_label,
        "installed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "project_name": project_name,
        "rules_installed": rules_installed,
        "hooks_installed": hooks_installed,
        "skills_installed": skills_installed,
        "provenance_scan_installed": provenance_scan_installed,
    }
    meta_path = project_dir / ".cognitive-os" / "install-meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    # ── 11. Register in global COS installations registry ────────────
    _registry_register(
        str(project_dir),
        mode.lstrip("-"),
        cos_version,
        project_name,
        registry_source,
    )

    # ── 12. Add to .gitignore ─────────────────────────────────────────
    _update_gitignore(project_dir)

    # ── Summary ───────────────────────────────────────────────────────
    print()
    print(f"Cognitive OS initialized ({mode.lstrip('-')} mode)")
    print(f"  Rules:  {rules_installed} installed")
    print(f"  Hooks:  {hooks_installed} registered")
    print(f"  Skills: {skills_installed} available")
    print()
    print("Next: start coding! The AI knows what to do.")
    print()
    if mode == "--default":
        print("Need maximum coverage? Re-run with --full:")
        print(f"  bash {cos_source}/scripts/cos-init.sh --full")

    return 0


if __name__ == "__main__":
    sys.exit(main())

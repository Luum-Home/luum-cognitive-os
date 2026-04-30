#!/usr/bin/env python3
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
    python3 scripts/cos_init.py [--default|--full] [--harness claude|codex]

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

# ── Repository root (cos source directory) ───────────────────────────
COS_SOURCE_DIR = Path(__file__).parent.parent.resolve()

# ── ADR-093 canonical mode constants ─────────────────────────────────
DEFAULT_RULES = (
    "trust-score acceptance-criteria closed-loop-prompts definition-of-done "
    "agent-quality adaptive-bypass phase-aware-agents token-economy "
    "responsiveness credential-management content-policy error-learning "
    "model-routing result-management"
).split()

DEFAULT_HOOKS = (
    "error-learning error-pipeline result-truncator session-init host-tool-doctor session-cleanup "
    "user-prompt-capture session-wrapup-trigger session-heartbeat memory-prefetch "
    "clarification-gate blast-radius scope-proportionality "
    "error-pattern-detector auto-refine auto-verify completeness-check dod-gate "
    "trust-score-validator skill-metrics-tracker inject-phase-context stack-detector "
    "pre-compaction-flush rate-limiter large-file-advisor secret-detector content-policy "
    "doc-sync-detector auto-checkpoint claim-validator completion-gate "
    "clarification-interceptor agent-checkpoint session-sanity confidentiality-enforcer "
    "session-learning crash-recovery teammate-idle task-created task-completed"
).split()

DEFAULT_SKILLS = (
    "compose-prompt exhaustive-prompt agent-dashboard auto-refine "
    "verification-before-completion plan-feature session-backlog resource-governor "
    "paperclip-dashboard cos-status"
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
    "error-learning.md",
]


# ── Migrated functions ───────────────────────────────────────────────

def detect_harness(project_root: str = ".") -> str:
    """Detect the active harness for a project directory.

    Inlined from scripts/_lib/settings-driver.sh::cos_detect_harness.
    Detects the active harness (claude|codex) by inspecting filesystem markers
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
        if meta_harness in {"claude", "codex"}:
            return meta_harness

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

    Takes a full skill directory path, kernel dest, optional driver dest.
    Calls skill_scope_allows() to filter. Then:
      - rm -rf kernel/<name> [driver/<name>]
      - cp -r skill_dir kernel/<name>
      - when a driver dest is provided:
        ln -s ../../.cognitive-os/skills/cos/<name> driver/<name>  (relative symlink)

    Codex and future hosts use canonical `.cognitive-os/skills/cos` as the
    install surface until they have an explicit skills driver contract.

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

_INTERNAL_DISPATCH: dict[str, object] = {
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
    parser.add_argument("--harness", choices=["claude", "codex"],
                        default=None,
                        help="Target harness (claude or codex). Overrides auto-detection.")
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

def _apply_harness_settings(
    project_dir: Path,
    cos_source: Path,
    mode: str,
    harness: str,
    settings_relative_path: str,
    settings_label: str,
) -> None:
    """Port of the settings generation block (cos-init.sh lines 585-620)."""
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

    if harness == "claude":
        settings_relative_path = ".claude/settings.json"
        settings_label = ".claude/settings.json"
    elif harness == "codex":
        settings_relative_path = ".codex/hooks.json"
        settings_label = ".codex/hooks.json"
    else:
        print(f"Error: unsupported harness '{harness}' (expected claude or codex).", file=sys.stderr)
        return 1

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

    # ── 3. Create directory structure ────────────────────────────────
    # SAFETY: replace symlinks with real directories
    for dir_check in (".cognitive-os", ".claude", ".codex"):
        p = project_dir / dir_check
        if p.is_symlink():
            target = os.readlink(str(p))
            print(f"WARNING: {dir_check} is a symlink ({target}) — replacing with real directory")
            p.unlink()

    driver_dirs = [str(Path(settings_relative_path).parent)]
    if harness == "claude":
        driver_dirs.extend([".claude/rules/cos", ".claude/commands"])

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
        # Default mode: install the 14 core rules
        for name in DEFAULT_RULES:
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
        # Default mode: the standard hook set
        for name in DEFAULT_HOOKS:
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
    skill_dest_driver = (
        str(project_dir / ".claude" / "skills")
        if harness == "claude"
        else ""
    )

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
            # Default: install the curated core skills
            for name in DEFAULT_SKILLS:
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
        "settings_driver": settings_label,
        "installed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "project_name": project_name,
        "rules_installed": rules_installed,
        "hooks_installed": hooks_installed,
        "skills_installed": skills_installed,
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

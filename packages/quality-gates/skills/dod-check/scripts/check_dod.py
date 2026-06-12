#!/usr/bin/env python3
"""Deterministic Definition of Done checker for Cognitive OS worktrees.

The checker is intentionally conservative and cheap by default: it inspects the
current Git worktree, classifies change complexity, checks high-signal hygiene,
and recommends a smallest validation command for the changed surface. Harness
skills such as Codex `$dod-check` and Claude Code `/dod-check` call this shared
script so enforcement stays outside prompt prose.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

def resolve_root() -> Path:
    for name in ("COGNITIVE_OS_PROJECT_DIR", "CODEX_PROJECT_DIR", "CLAUDE_PROJECT_DIR"):
        value = os.environ.get(name, "")
        if value:
            return Path(value)
    return Path.cwd()


ROOT = resolve_root()


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    evidence: str


@dataclass(frozen=True)
class Report:
    verdict: str
    complexity: str
    changed_files: list[str]
    dod_profiles: list[str]
    stack_signals: list[str]
    recommended_command: str | None
    checks: list[Check]


def run(cmd: list[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False, timeout=timeout)


def run_git(args: list[str], timeout: int = 10) -> subprocess.CompletedProcess[str] | None:
    cmd = ["git", "-c", "core.fsmonitor=false", "-c", "core.untrackedCache=false", *args]
    try:
        return run(cmd, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None


def changed_files() -> list[str]:
    proc = run_git(["diff", "--name-only", "HEAD"], timeout=10)
    files = [line.strip() for line in (proc.stdout if proc else "").splitlines() if line.strip()]
    proc_untracked = run_git(["ls-files", "--others", "--exclude-standard"], timeout=5)
    files.extend(line.strip() for line in (proc_untracked.stdout if proc_untracked else "").splitlines() if line.strip())
    return sorted(dict.fromkeys(files))


def classify(files: list[str]) -> str:
    if not files:
        return "trivial"
    lowered = "\n".join(files).lower()
    if any(token in lowered for token in ("secret", "credential", "auth", "payment", "migration", "release", "version")):
        return "critical"
    if len(files) > 10 or any(path.startswith(("cmd/", "packages/", "internal/", "hooks/")) for path in files):
        return "large"
    if len(files) > 3 or any(path.startswith(("rules/", "skills/", ".codex/skills/", ".claude/commands/")) for path in files):
        return "medium"
    return "small"


def recommended_command(files: list[str]) -> str | None:
    if not files:
        return None
    file_set = set(files)
    if any(path.endswith(".sh") or path.startswith("hooks/") for path in file_set):
        hook_files = [path for path in files if path.endswith(".sh")]
        if hook_files:
            return "bash -n " + " ".join(hook_files)
    if any(path.endswith(".py") for path in file_set):
        py_files = [path for path in files if path.endswith(".py")]
        return "python3 -m py_compile " + " ".join(py_files)
    if any(path.startswith(("rules/", "skills/", ".codex/skills/", ".claude/commands/", "AGENTS.md")) for path in file_set):
        return "python3 scripts/prompt_aggressive_language_audit.py " + " ".join(files) + " --fail-debt"
    return "git diff --check"


def infer_dod_profiles(files: list[str]) -> list[str]:
    """Infer portable DoD profile overlays from changed paths.

    Profiles are intentionally stack-neutral. They identify the kind of work
    touched by the diff so the skill can load profile-specific completion
    criteria without assuming a framework, package manager, database, or UI
    library.
    """

    profiles: set[str] = set()
    for raw_path in files:
        path = raw_path.lower()
        name = Path(path).name
        suffix = Path(path).suffix

        if (
            ".storybook/" in path
            or "/stories/" in path
            or name.endswith((".stories.tsx", ".stories.ts", ".stories.jsx", ".stories.js", ".stories.mdx"))
            or suffix == ".mdx"
        ):
            profiles.add("storybook-docs")

        if (
            "/ui/" in path
            or "/components/" in path
            or "/component" in path
            or "/tokens/" in path
            or "/theme" in path
            or name in {"preview.tsx", "preview.ts", "theme.ts", "tokens.css"}
        ) and suffix in {".ts", ".tsx", ".js", ".jsx", ".css", ".scss", ".vue", ".svelte"}:
            profiles.add("ui-component")

        if (
            "/features/" in path
            or "/app/" in path
            or "/pages/" in path
            or "/routes/" in path
            or "/hooks/" in path
            or "/contexts/" in path
        ) and suffix in {".ts", ".tsx", ".js", ".jsx", ".vue", ".svelte"}:
            profiles.add("frontend-feature")

        if (
            "/api/" in path
            or "/handlers/" in path
            or "/services/" in path
            or "/server/" in path
            or "/auth/" in path
            or "/webhook" in path
            or "/cron" in path
            or "/jobs/" in path
            or "/migrations/" in path
            or "/db/" in path
            or "/database/" in path
            or "/repositories/" in path
            or name in {"route.ts", "route.js", "server.ts", "server.js"}
        ) and suffix in {".ts", ".tsx", ".js", ".jsx", ".py", ".go", ".rs", ".java", ".kt", ".rb", ".php", ".cs", ".ex", ".exs", ".sql"}:
            profiles.add("backend-api")

    return sorted(profiles)


def _read_optional(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def detect_stack_signals(root: Path = ROOT) -> list[str]:
    """Detect stack/tooling signals from repository files.

    This is evidence-only. A signal means the repo contains a conventional
    manifest/config/dependency reference; it does not mean the checker may invent
    commands. Validation commands still come from configured scripts or explicit
    project files.
    """

    signals: set[str] = set()

    package_json = root / "package.json"
    if package_json.exists():
        signals.add("node")
        text = _read_optional(package_json).lower()
        dependency_markers = {
            '"next"': "nextjs",
            '"react"': "react",
            '"vue"': "vue",
            '"svelte"': "svelte",
            '"@angular/core"': "angular",
            '"@storybook/': "storybook",
            '"storybook"': "storybook",
            '"vitest"': "vitest",
            '"jest"': "jest",
            '"playwright"': "playwright",
            '"cypress"': "cypress",
            '"typescript"': "typescript",
            '"tailwindcss"': "tailwind",
            '"zod"': "zod",
        }
        for marker, signal in dependency_markers.items():
            if marker in text:
                signals.add(signal)
        for manager_file, signal in {
            "pnpm-lock.yaml": "pnpm",
            "yarn.lock": "yarn",
            "package-lock.json": "npm",
            "bun.lockb": "bun",
            "bun.lock": "bun",
        }.items():
            if (root / manager_file).exists():
                signals.add(signal)

    python_manifests = ("pyproject.toml", "requirements.txt", "setup.py", "setup.cfg", "Pipfile", "uv.lock")
    if any((root / name).exists() for name in python_manifests):
        signals.add("python")
        text = "\n".join(_read_optional(root / name).lower() for name in python_manifests)
        for marker, signal in {
            "django": "django",
            "fastapi": "fastapi",
            "flask": "flask",
            "pytest": "pytest",
            "ruff": "ruff",
            "mypy": "mypy",
        }.items():
            if marker in text:
                signals.add(signal)

    manifest_signals = {
        "go.mod": "go",
        "Cargo.toml": "rust",
        "pom.xml": "maven",
        "build.gradle": "gradle",
        "build.gradle.kts": "gradle",
        "Gemfile": "ruby",
        "composer.json": "php",
        "mix.exs": "elixir",
        "deno.json": "deno",
        "deno.jsonc": "deno",
        "Dockerfile": "docker",
        "docker-compose.yml": "docker-compose",
        "docker-compose.yaml": "docker-compose",
    }
    for manifest, signal in manifest_signals.items():
        if (root / manifest).exists():
            signals.add(signal)

    if any(root.glob("*.csproj")) or any(root.glob("**/*.csproj")):
        signals.add("dotnet")
    if (root / ".storybook").exists():
        signals.add("storybook")
    if (root / "tsconfig.json").exists():
        signals.add("typescript")
    if any((root / name).exists() for name in ("vite.config.ts", "vite.config.js", "vite.config.mts")):
        signals.add("vite")
    if any((root / name).exists() for name in ("next.config.js", "next.config.mjs", "next.config.ts")):
        signals.add("nextjs")

    return sorted(signals)


def file_text(path: str) -> str:
    try:
        return (ROOT / path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def check_hygiene(files: list[str]) -> list[Check]:
    checks: list[Check] = []
    checks.append(Check("changed_files_present", "PASS" if files else "WARN", f"{len(files)} changed/untracked file(s)"))
    blocked_paths = [p for p in files if p == ".env" or p.startswith("secrets/") or p.endswith((".pem", ".key")) or p == ".git/config"]
    checks.append(Check("blocked_paths_absent", "PASS" if not blocked_paths else "FAIL", ", ".join(blocked_paths) or "no blocked paths touched"))
    todo_hits: list[str] = []
    for path in files:
        if not path.endswith((".py", ".sh", ".md", ".go", ".ts", ".tsx", ".js", ".jsx")):
            continue
        text = file_text(path)
        for idx, line in enumerate(text.splitlines(), 1):
            if re.search(r"\b(" + "TO" + "DO|FIXME|HACK)\b", line):
                todo_hits.append(f"{path}:{idx}")
                break
    checks.append(Check("todo_fixme_absent", "PASS" if not todo_hits else "FAIL", ", ".join(todo_hits) or "no TODO/FIXME/HACK markers in changed text files"))
    return checks


def run_recommended(command: str | None) -> Check:
    if not command:
        return Check("recommended_validation", "WARN", "no changed files; no validation command recommended")
    proc = subprocess.run(command, cwd=ROOT, shell=True, text=True, capture_output=True, check=False, timeout=120)
    evidence = f"exit={proc.returncode}; command={command}"
    if proc.stdout.strip():
        evidence += f"; stdout={proc.stdout.strip()[:200]}"
    if proc.stderr.strip():
        evidence += f"; stderr={proc.stderr.strip()[:200]}"
    return Check("recommended_validation", "PASS" if proc.returncode == 0 else "FAIL", evidence)


def build_report(run_validation: bool = False) -> Report:
    files = changed_files()
    complexity = classify(files)
    profiles = infer_dod_profiles(files)
    stack_signals = detect_stack_signals(ROOT)
    command = recommended_command(files)
    checks = check_hygiene(files)
    checks.append(
        Check(
            "dod_profiles",
            "PASS",
            ", ".join(profiles) if profiles else "no surface-specific DoD profile inferred; base DoD applies",
        )
    )
    checks.append(
        Check(
            "stack_signals",
            "PASS" if stack_signals else "WARN",
            ", ".join(stack_signals) if stack_signals else "no stack manifest/config signals detected",
        )
    )
    if command:
        checks.append(Check("recommended_command_present", "PASS", command))
    else:
        checks.append(Check("recommended_command_present", "WARN", "no command recommended for empty worktree"))
    if run_validation:
        checks.append(run_recommended(command))
    statuses = [check.status for check in checks]
    verdict = "FAIL" if "FAIL" in statuses else "WARN" if "WARN" in statuses else "PASS"
    return Report(verdict, complexity, files, profiles, stack_signals, command, checks)


def markdown(report: Report) -> str:
    lines = [f"## DoD Check: {report.verdict}", f"Complexity: {report.complexity}", ""]
    lines.append(f"Changed files: {len(report.changed_files)}")
    lines.append(f"DoD profiles: {', '.join(report.dod_profiles) if report.dod_profiles else 'none'}")
    lines.append(f"Stack signals: {', '.join(report.stack_signals) if report.stack_signals else 'none'}")
    if report.recommended_command:
        lines.append(f"Recommended validation: `{report.recommended_command}`")
    lines.append("\n| Check | Status | Evidence |")
    lines.append("|---|---|---|")
    for check in report.checks:
        evidence = check.evidence.replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {check.name} | {check.status} | {evidence} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--run-recommended", action="store_true")
    parser.add_argument("--fail-on-warn", action="store_true")
    args = parser.parse_args()
    report = build_report(run_validation=args.run_recommended)
    if args.format == "json":
        print(json.dumps(asdict(report), indent=2, sort_keys=True))
    else:
        print(markdown(report), end="")
    if report.verdict == "FAIL" or (args.fail_on_warn and report.verdict == "WARN"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

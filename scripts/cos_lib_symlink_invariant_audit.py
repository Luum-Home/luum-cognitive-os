#!/usr/bin/env python3
# SCOPE: os-only
"""cos-lib-symlink-invariant-audit — ADR-267 follow-up.

Detects silent drift between lib/*.py (root) and packages/*/lib/*.py
counterparts.  The project invariant claims "lib/*.py are SYMLINKS — NOT
duplicates"; this script enforces that invariant and surfaces violations.

Four conditions are checked per same-named file pair:

  ERROR  — File exists in both, content diverged
  WARN   — File exists in both, content identical, neither is a symlink to
           the other  (real-file dupe — invariant violated but no drift yet)
  ERROR  — File is a symlink pointing to a non-existent target (dangling)
  ERROR  — Symlink resolves but to a path outside packages/ (cross-project
           leak)

Usage:
  python3 scripts/cos_lib_symlink_invariant_audit.py [options]

Flags:
  --format  text|json|markdown   Output format (default: text)
  --output  <path>               Write to file instead of stdout
  --ci                           Exit 1 if any ERROR (warns not exit-blocking)
  --scope   lib|packages|both    Directories to walk (default: both)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

SEVERITY_ERROR = "ERROR"
SEVERITY_WARN = "WARN"

# Same basename does not always mean "duplicate counterpart". These package
# modules are intentionally distinct public surfaces that share conventional
# names with root lib modules (`dispatch.py`, `retry_classifier.py`,
# `__init__.py`). Treating them as drift would make the audit noisy and hide
# real silent-copy regressions.
INTENTIONAL_DISTINCT_MODULE_PAIRS: set[tuple[str, str]] = {
    (
        "lib/dispatch.py",
        "packages/agent-lifecycle/lib/harness_adapter/dispatch.py",
    ),
    (
        "lib/retry_classifier.py",
        "packages/agent-lifecycle/lib/event_projections/retry_classifier.py",
    ),
    (
        "lib/__init__.py",
        "packages/agent-lifecycle/lib/event_projections/__init__.py",
    ),
    (
        "lib/__init__.py",
        "packages/agent-lifecycle/lib/harness_adapter/__init__.py",
    ),
    (
        "lib/__init__.py",
        "packages/llm-providers/lib/__init__.py",
    ),
}


@dataclass
class Finding:
    severity: str          # "ERROR" | "WARN"
    condition: str         # short tag e.g. "content_drift"
    lib_path: str          # relative to repo root
    pkg_path: str          # relative to repo root (may be empty for dangling)
    message: str


@dataclass
class AuditResult:
    findings: list[Finding] = field(default_factory=list)
    passing_pairs: int = 0
    scanned_root_files: int = 0
    scanned_pkg_files: int = 0
    elapsed_s: float = 0.0

    @property
    def error_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == SEVERITY_ERROR)

    @property
    def warn_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == SEVERITY_WARN)


# ---------------------------------------------------------------------------
# Core audit
# ---------------------------------------------------------------------------

def _read_bytes(path: Path) -> bytes | None:
    """Read file bytes via low-level I/O to avoid codec issues."""
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except OSError:
        return None


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_symlink_to(src: Path, target: Path) -> bool:
    """Return True if src is a symlink whose realpath == target's realpath."""
    try:
        return os.path.islink(src) and os.path.realpath(src) == os.path.realpath(target)
    except OSError:
        return False


def _collect_root_lib(repo: Path) -> dict[str, Path]:
    """Return {basename: Path} for lib/*.py (top-level only, no subdirs)."""
    lib_dir = repo / "lib"
    if not lib_dir.is_dir():
        return {}
    result: dict[str, Path] = {}
    with os.scandir(lib_dir) as it:
        for entry in it:
            if entry.name.endswith(".py") and not entry.name.startswith("__pycache__"):
                # Use lstat so symlinks are not transparently followed here
                result[entry.name] = Path(entry.path)
    return result


def _collect_pkg_lib(repo: Path) -> dict[str, list[Path]]:
    """Return {basename: [Path, ...]} for packages/*/lib/**/*.py.

    The walk is depth-limited to 3 levels below packages/*/lib/ to match the
    historical shape of the repo without spawning subprocesses.
    """
    packages_dir = repo / "packages"
    if not packages_dir.is_dir():
        return {}

    result: dict[str, list[Path]] = {}

    def _walk(directory: Path, depth: int) -> Iterator[Path]:
        if depth < 0:
            return
        try:
            with os.scandir(directory) as it:
                for entry in it:
                    if entry.name == "__pycache__":
                        continue
                    if entry.is_file(follow_symlinks=False) and entry.name.endswith(".py"):
                        yield Path(entry.path)
                    elif entry.is_dir(follow_symlinks=False):
                        yield from _walk(Path(entry.path), depth - 1)
        except PermissionError:
            pass

    with os.scandir(packages_dir) as pkg_it:
        for pkg_entry in pkg_it:
            if not pkg_entry.is_dir(follow_symlinks=False):
                continue
            lib_dir = Path(pkg_entry.path) / "lib"
            if not lib_dir.is_dir():
                continue
            for py_path in _walk(lib_dir, depth=3):
                name = py_path.name
                result.setdefault(name, []).append(py_path)

    return result


def run_audit(repo: Path, scope: str = "both") -> AuditResult:
    """Execute the full audit and return an AuditResult."""
    t0 = time.monotonic()
    result = AuditResult()

    packages_dir = repo / "packages"

    root_files: dict[str, Path] = {}
    pkg_files: dict[str, list[Path]] = {}

    if scope in ("lib", "both"):
        root_files = _collect_root_lib(repo)
        result.scanned_root_files = len(root_files)

    if scope in ("packages", "both"):
        pkg_files = _collect_pkg_lib(repo)
        result.scanned_pkg_files = sum(len(v) for v in pkg_files.values())

    # ----- Dangling symlink check: root lib -----
    for name, path in root_files.items():
        if os.path.islink(path):
            real = None
            try:
                real = Path(os.path.realpath(path))
            except OSError:
                pass
            if real is None or not real.exists():
                result.findings.append(Finding(
                    severity=SEVERITY_ERROR,
                    condition="dangling_symlink",
                    lib_path=str(path.relative_to(repo)),
                    pkg_path="",
                    message=(
                        f"{path.relative_to(repo)} is a dangling symlink "
                        f"(target does not exist)."
                    ),
                ))
                continue
            # Cross-project leak check
            try:
                real.relative_to(packages_dir)
            except ValueError:
                result.findings.append(Finding(
                    severity=SEVERITY_ERROR,
                    condition="cross_project_leak",
                    lib_path=str(path.relative_to(repo)),
                    pkg_path=str(real),
                    message=(
                        f"{path.relative_to(repo)} symlink resolves outside "
                        f"packages/ → {real}"
                    ),
                ))

    # ----- Pair-wise content / symlink check -----
    if scope == "both":
        for name, root_path in root_files.items():
            if name not in pkg_files:
                continue  # no counterpart in packages — not an invariant violation

            for pkg_path in pkg_files[name]:
                root_rel = str(root_path.relative_to(repo))
                pkg_rel = str(pkg_path.relative_to(repo))
                if (root_rel, pkg_rel) in INTENTIONAL_DISTINCT_MODULE_PAIRS:
                    continue

                # Skip the dangling/cross-project ones already flagged above
                if os.path.islink(root_path):
                    real = None
                    try:
                        real = Path(os.path.realpath(root_path))
                    except OSError:
                        pass
                    if real is None or not real.exists():
                        continue  # already reported as dangling

                root_is_link_to_pkg = _is_symlink_to(root_path, pkg_path)
                pkg_is_link_to_root = _is_symlink_to(pkg_path, root_path)

                if root_is_link_to_pkg or pkg_is_link_to_root:
                    # Proper symlink relationship — invariant satisfied
                    result.passing_pairs += 1
                    continue

                # Neither is symlink to the other — read content
                root_data = _read_bytes(root_path)
                pkg_data = _read_bytes(pkg_path)

                if root_data is None or pkg_data is None:
                    # Can't read one side — treat as error
                    result.findings.append(Finding(
                        severity=SEVERITY_ERROR,
                        condition="unreadable_file",
                        lib_path=str(root_path.relative_to(repo)),
                        pkg_path=str(pkg_path.relative_to(repo)),
                        message=(
                            f"Cannot read one or both files: "
                            f"{root_path.relative_to(repo)} / {pkg_path.relative_to(repo)}"
                        ),
                    ))
                    continue

                if root_data != pkg_data:
                    result.findings.append(Finding(
                        severity=SEVERITY_ERROR,
                        condition="content_drift",
                        lib_path=str(root_path.relative_to(repo)),
                        pkg_path=str(pkg_path.relative_to(repo)),
                        message=(
                            f"Content diverged: {root_path.relative_to(repo)} "
                            f"vs {pkg_path.relative_to(repo)} "
                            f"(root sha256={_sha256(root_data)[:12]}… "
                            f"pkg sha256={_sha256(pkg_data)[:12]}…)"
                        ),
                    ))
                else:
                    # Same content but neither is a symlink — real-file dupe
                    result.findings.append(Finding(
                        severity=SEVERITY_WARN,
                        condition="real_file_dupe",
                        lib_path=str(root_path.relative_to(repo)),
                        pkg_path=str(pkg_path.relative_to(repo)),
                        message=(
                            f"Real-file dupe (identical content, no symlink): "
                            f"{root_path.relative_to(repo)} "
                            f"vs {pkg_path.relative_to(repo)}"
                        ),
                    ))

    result.elapsed_s = time.monotonic() - t0
    return result


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def _format_text(result: AuditResult, repo: Path) -> str:
    lines: list[str] = []
    lines.append(
        f"lib-symlink-invariant audit — "
        f"{result.error_count} ERROR(s), {result.warn_count} WARN(s), "
        f"{result.passing_pairs} passing pair(s) "
        f"[{result.elapsed_s:.2f}s | "
        f"root={result.scanned_root_files} pkg={result.scanned_pkg_files}]"
    )
    lines.append("")
    if not result.findings:
        lines.append("  ✓ No violations found.")
    for f in result.findings:
        tag = f"[{f.severity}][{f.condition}]"
        lines.append(f"  {tag} {f.message}")
    return "\n".join(lines)


def _format_json(result: AuditResult) -> str:
    payload = {
        "summary": {
            "errors": result.error_count,
            "warns": result.warn_count,
            "passing_pairs": result.passing_pairs,
            "scanned_root_files": result.scanned_root_files,
            "scanned_pkg_files": result.scanned_pkg_files,
            "elapsed_s": round(result.elapsed_s, 3),
        },
        "findings": [
            {
                "severity": f.severity,
                "condition": f.condition,
                "lib_path": f.lib_path,
                "pkg_path": f.pkg_path,
                "message": f.message,
            }
            for f in result.findings
        ],
    }
    return json.dumps(payload, indent=2)


def _format_markdown(result: AuditResult) -> str:
    lines: list[str] = []
    lines.append("# lib-symlink-invariant audit (ADR-267)")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| ERRORs | {result.error_count} |")
    lines.append(f"| WARNs | {result.warn_count} |")
    lines.append(f"| Passing pairs | {result.passing_pairs} |")
    lines.append(f"| Root lib files scanned | {result.scanned_root_files} |")
    lines.append(f"| Package lib files scanned | {result.scanned_pkg_files} |")
    lines.append(f"| Elapsed | {result.elapsed_s:.2f}s |")
    lines.append("")
    if not result.findings:
        lines.append("**No violations found.**")
        return "\n".join(lines)
    lines.append("## Findings")
    lines.append("")
    lines.append("| Severity | Condition | lib_path | pkg_path | Message |")
    lines.append("|---|---|---|---|---|")
    for f in result.findings:
        msg = f.message.replace("|", "\\|")
        lines.append(
            f"| {f.severity} | {f.condition} | `{f.lib_path}` | `{f.pkg_path}` | {msg} |"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cos-lib-symlink-invariant-audit",
        description="Detect silent drift between lib/*.py and packages/*/lib/*.py.",
    )
    p.add_argument(
        "--format",
        choices=["text", "json", "markdown"],
        default="text",
        help="Output format (default: text)",
    )
    p.add_argument(
        "--output",
        metavar="PATH",
        default=None,
        help="Write report to file instead of stdout",
    )
    p.add_argument(
        "--ci",
        action="store_true",
        help="Exit 1 if any ERROR is found (warns are not exit-blocking)",
    )
    p.add_argument(
        "--scope",
        choices=["lib", "packages", "both"],
        default="both",
        help="Directories to include in the walk (default: both)",
    )
    p.add_argument(
        "--repo",
        metavar="PATH",
        default=None,
        help="Path to repo root (auto-detected from this script's location if omitted)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Auto-detect repo root: two levels up from scripts/
    if args.repo:
        repo = Path(args.repo).resolve()
    else:
        repo = Path(__file__).resolve().parent.parent

    result = run_audit(repo, scope=args.scope)

    fmt = args.format
    if fmt == "text":
        report = _format_text(result, repo)
    elif fmt == "json":
        report = _format_json(result)
    else:
        report = _format_markdown(result)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report + "\n", encoding="utf-8")
    else:
        print(report)

    if args.ci and result.error_count > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

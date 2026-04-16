# scope: both
"""ADR auto-detection — analyze git commits for architectural significance.

Scores commits against weighted signals (dependency changes, config schema
changes, hook modifications, license impacts, etc.) and generates draft ADR
documents when the total weight exceeds a configurable threshold.

Usage:
    from lib.adr_detector import analyze_commit, generate_adr_draft, get_next_adr_number

    result = analyze_commit("abc1234", "/path/to/project")
    if result["triggered"]:
        path = generate_adr_draft(result["commit_hash"], result["signals"], "/path/to/project")
"""
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Signal weights — each signal type has a base weight.  Multiple signals are
# additive but each type caps at 1.0 to prevent noise from bulk changes.
# ---------------------------------------------------------------------------

DEFAULT_WEIGHTS: Dict[str, float] = {
    "dependency_change": 0.40,
    "config_schema_change": 0.35,
    "hook_change": 0.30,
    "license_change": 0.60,
    "large_deletion": 0.25,
    "new_integration": 0.30,
    "file_structure_change": 0.20,
    "breaking_change": 0.50,
}

DEFAULT_THRESHOLD = 0.70

# Files whose presence in a commit diff triggers the dependency signal.
DEPENDENCY_FILES = {
    "go.mod", "go.sum",
    "pyproject.toml", "requirements.txt", "setup.cfg",
    "package.json", "pnpm-lock.yaml", "yarn.lock",
    "Cargo.toml", "Gemfile",
}

CONFIG_FILES = {
    "cognitive-os.yaml",
    "cos-dispatch.toml",
}

HOOK_FILES_PATTERN = re.compile(r"^hooks/.*\.sh$|^\.claude/settings\.json$")

LICENSE_FILES = {"LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"}

BREAKING_CHANGE_PATTERNS = re.compile(
    r"(^packages/.*/(?:api|interface|protocol))"
    r"|(\.proto$)"
    r"|(openapi\.ya?ml$)"
    r"|(swagger\.json$)"
)

ADR_PATH_PATTERN = re.compile(r"^docs/architecture/adrs/")


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def analyze_commit(commit_hash: str, project_dir: str) -> Dict[str, Any]:
    """Analyze a commit for ADR-worthiness.

    Returns a dict with keys:
        commit_hash, commit_message, signals, total_score, triggered, threshold
    """
    project_dir = str(project_dir)

    # Get commit message
    commit_message = _git(
        ["git", "log", "-1", "--format=%s", commit_hash],
        cwd=project_dir,
    ).strip()

    # Get list of changed files with stats
    stat_output = _git(
        ["git", "show", "--stat", "--format=", commit_hash],
        cwd=project_dir,
    )

    # Get the actual file list (names only)
    name_status = _git(
        ["git", "diff-tree", "--no-commit-id", "-r", "--name-status", commit_hash],
        cwd=project_dir,
    )

    changed_files = _parse_name_status(name_status)

    # Check for ADR-only changes (avoid recursive detection)
    non_adr_files = [
        f for f in changed_files
        if not ADR_PATH_PATTERN.match(f["path"])
    ]
    if not non_adr_files:
        return {
            "commit_hash": commit_hash,
            "commit_message": commit_message,
            "signals": [],
            "total_score": 0.0,
            "triggered": False,
            "threshold": DEFAULT_THRESHOLD,
        }

    # Run all signal detectors
    signals: List[Dict[str, Any]] = []
    signals.extend(_check_dependency_change(changed_files))
    signals.extend(_check_config_schema_change(changed_files))
    signals.extend(_check_hook_change(changed_files))
    signals.extend(_check_license_change(changed_files))
    signals.extend(_check_large_deletion(changed_files, stat_output))
    signals.extend(_check_new_integration(changed_files))
    signals.extend(_check_file_structure_change(changed_files))
    signals.extend(_check_breaking_change(changed_files))

    total_score = sum(s["weight"] for s in signals)
    triggered = total_score >= DEFAULT_THRESHOLD

    return {
        "commit_hash": commit_hash,
        "commit_message": commit_message,
        "signals": signals,
        "total_score": round(total_score, 2),
        "triggered": triggered,
        "threshold": DEFAULT_THRESHOLD,
    }


# ---------------------------------------------------------------------------
# ADR generation
# ---------------------------------------------------------------------------

def generate_adr_draft(
    commit_hash: str,
    signals: List[Dict[str, Any]],
    project_dir: str,
) -> str:
    """Generate an ADR markdown draft from commit info and signals.

    Returns the path to the created ADR file.
    """
    project_dir = str(project_dir)
    adrs_dir = os.path.join(project_dir, "docs", "architecture", "adrs")
    os.makedirs(adrs_dir, exist_ok=True)

    number = get_next_adr_number(adrs_dir)

    commit_message = _git(
        ["git", "log", "-1", "--format=%s", commit_hash],
        cwd=project_dir,
    ).strip()

    commit_body = _git(
        ["git", "log", "-1", "--format=%b", commit_hash],
        cwd=project_dir,
    ).strip()

    title = _build_title(commit_message, signals)
    slug = _slugify(title)
    filename = f"ADR-{number:03d}-{slug}.md"
    filepath = os.path.join(adrs_dir, filename)

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    signal_table = _build_signal_table(signals)
    total_weight = sum(s["weight"] for s in signals)

    context = _build_context(commit_message, commit_body, signals)
    decision = _build_decision(commit_message, commit_body)
    consequences = _build_consequences(signals)

    content = f"""# ADR-{number:03d}: {title}

## Status

Draft

## Date

{date_str}

## Context

{context}

## Decision

{decision}

## Consequences

{consequences}

## Detection Signals

{signal_table}
**Total weight:** {total_weight:.2f} (threshold: {DEFAULT_THRESHOLD})

## Source

- **Commit:** `{commit_hash}`
- **Message:** {commit_message}

---
*Auto-generated by cos-dispatch ADR detector. Review and promote to Accepted or reject.*
"""

    with open(filepath, "w") as f:
        f.write(content)

    return filepath


def get_next_adr_number(adrs_dir: str) -> int:
    """Find the next available ADR number by scanning existing ADR files."""
    if not os.path.isdir(adrs_dir):
        return 1

    max_num = 0
    pattern = re.compile(r"^ADR-(\d{3})")
    for entry in os.listdir(adrs_dir):
        m = pattern.match(entry)
        if m:
            num = int(m.group(1))
            if num > max_num:
                max_num = num

    return max_num + 1


# ---------------------------------------------------------------------------
# Signal detectors
# ---------------------------------------------------------------------------

def _check_dependency_change(
    changed_files: List[Dict[str, str]],
) -> List[Dict[str, Any]]:
    dep_files = [f for f in changed_files if os.path.basename(f["path"]) in DEPENDENCY_FILES]
    if dep_files:
        return [{
            "type": "dependency_change",
            "weight": DEFAULT_WEIGHTS["dependency_change"],
            "description": "Dependency files changed",
            "files": [f["path"] for f in dep_files],
        }]
    return []


def _check_config_schema_change(
    changed_files: List[Dict[str, str]],
) -> List[Dict[str, Any]]:
    config_files = [
        f for f in changed_files
        if os.path.basename(f["path"]) in CONFIG_FILES
    ]
    if config_files:
        return [{
            "type": "config_schema_change",
            "weight": DEFAULT_WEIGHTS["config_schema_change"],
            "description": "Configuration schema files changed",
            "files": [f["path"] for f in config_files],
        }]
    return []


def _check_hook_change(
    changed_files: List[Dict[str, str]],
) -> List[Dict[str, Any]]:
    hook_files = [
        f for f in changed_files
        if HOOK_FILES_PATTERN.search(f["path"])
    ]
    if hook_files:
        return [{
            "type": "hook_change",
            "weight": DEFAULT_WEIGHTS["hook_change"],
            "description": "Hook or settings configuration changed",
            "files": [f["path"] for f in hook_files],
        }]
    return []


def _check_license_change(
    changed_files: List[Dict[str, str]],
) -> List[Dict[str, Any]]:
    license_files = [
        f for f in changed_files
        if os.path.basename(f["path"]) in LICENSE_FILES
    ]
    if license_files:
        return [{
            "type": "license_change",
            "weight": DEFAULT_WEIGHTS["license_change"],
            "description": "License files changed",
            "files": [f["path"] for f in license_files],
        }]
    return []


def _check_large_deletion(
    changed_files: List[Dict[str, str]],
    stat_output: str,
) -> List[Dict[str, Any]]:
    deleted = [f for f in changed_files if f["status"] == "D"]
    if len(deleted) > 20:
        return [{
            "type": "large_deletion",
            "weight": DEFAULT_WEIGHTS["large_deletion"],
            "description": f"{len(deleted)} files deleted",
            "files": [f["path"] for f in deleted[:10]],  # cap evidence list
        }]
    return []


def _check_new_integration(
    changed_files: List[Dict[str, str]],
) -> List[Dict[str, Any]]:
    new_packages = [
        f for f in changed_files
        if f["status"] == "A" and f["path"].startswith("packages/")
    ]
    if new_packages:
        return [{
            "type": "new_integration",
            "weight": DEFAULT_WEIGHTS["new_integration"],
            "description": "New package added",
            "files": [f["path"] for f in new_packages[:5]],
        }]
    return []


def _check_file_structure_change(
    changed_files: List[Dict[str, str]],
) -> List[Dict[str, Any]]:
    # Detect new directories by looking for added files in previously
    # non-existent directories.  We approximate this by checking for added
    # files whose parent directory contains at least 2 path segments that
    # didn't exist among modified files.
    added = [f for f in changed_files if f["status"] == "A"]
    new_dirs = set()
    existing_dirs = {os.path.dirname(f["path"]) for f in changed_files if f["status"] != "A"}
    for f in added:
        d = os.path.dirname(f["path"])
        if d and d not in existing_dirs:
            new_dirs.add(d)

    if new_dirs:
        return [{
            "type": "file_structure_change",
            "weight": DEFAULT_WEIGHTS["file_structure_change"],
            "description": f"New directories: {', '.join(sorted(new_dirs)[:5])}",
            "files": sorted(new_dirs)[:5],
        }]
    return []


def _check_breaking_change(
    changed_files: List[Dict[str, str]],
) -> List[Dict[str, Any]]:
    breaking = [
        f for f in changed_files
        if BREAKING_CHANGE_PATTERNS.search(f["path"])
    ]
    if breaking:
        return [{
            "type": "breaking_change",
            "weight": DEFAULT_WEIGHTS["breaking_change"],
            "description": "API or interface files changed",
            "files": [f["path"] for f in breaking[:5]],
        }]
    return []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _git(cmd: List[str], cwd: str) -> str:
    """Run a git command and return stdout.  Returns empty string on error."""
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=10,
        )
        return result.stdout
    except (subprocess.SubprocessError, OSError):
        return ""


def _parse_name_status(output: str) -> List[Dict[str, str]]:
    """Parse git diff-tree --name-status output into list of {status, path}."""
    files = []
    for line in output.strip().splitlines():
        parts = line.split("\t", 1)
        if len(parts) == 2:
            files.append({"status": parts[0][0], "path": parts[1]})
    return files


def _build_title(commit_message: str, signals: List[Dict[str, Any]]) -> str:
    """Build an ADR title from the commit message."""
    # Strip conventional commit prefix
    title = re.sub(r"^(feat|fix|chore|docs|refactor|style|test|ci|build|perf)(\(.+?\))?:\s*", "", commit_message)
    # Truncate to reasonable length
    if len(title) > 80:
        title = title[:77] + "..."
    return title


def _slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    s = text.lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s]+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")[:60]


def _build_signal_table(signals: List[Dict[str, Any]]) -> str:
    """Build a markdown table of detection signals."""
    lines = ["| Signal | Weight | Evidence |", "|--------|--------|----------|"]
    for s in signals:
        evidence = ", ".join(s.get("files", [])[:3])
        lines.append(f"| {s['description']} | {s['weight']:.2f} | {evidence} |")
    return "\n".join(lines)


def _build_context(
    commit_message: str, commit_body: str, signals: List[Dict[str, Any]],
) -> str:
    """Build the Context section from commit info and signals."""
    parts = [f"This change was auto-detected as architecturally significant based on {len(signals)} signal(s)."]
    if commit_body:
        parts.append(f"\nFrom the commit description:\n{commit_body}")
    signal_types = ", ".join(s["type"].replace("_", " ") for s in signals)
    parts.append(f"\nDetected signal types: {signal_types}.")
    return "\n".join(parts)


def _build_decision(commit_message: str, commit_body: str) -> str:
    """Build the Decision section from commit info."""
    parts = [commit_message]
    if commit_body:
        parts.append(commit_body)
    parts.append("\n*[Review and expand this section with the rationale behind the decision.]*")
    return "\n\n".join(parts)


def _build_consequences(signals: List[Dict[str, Any]]) -> str:
    """Build the Consequences section from signals."""
    parts = ["*[Review and expand this section with actual consequences.]*\n"]
    parts.append("Potential areas of impact based on detected signals:\n")
    for s in signals:
        parts.append(f"- **{s['type'].replace('_', ' ').title()}**: {s['description']}")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Metrics logging
# ---------------------------------------------------------------------------

def log_detection(
    result: Dict[str, Any],
    adr_path: Optional[str],
    project_dir: str,
) -> None:
    """Append a detection record to the metrics JSONL file."""
    metrics_dir = os.path.join(project_dir, ".cognitive-os", "metrics")
    os.makedirs(metrics_dir, exist_ok=True)
    log_file = os.path.join(metrics_dir, "adr-detections.jsonl")

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "commit_hash": result.get("commit_hash", ""),
        "commit_message": result.get("commit_message", ""),
        "total_score": result.get("total_score", 0.0),
        "threshold": result.get("threshold", DEFAULT_THRESHOLD),
        "triggered": result.get("triggered", False),
        "signal_count": len(result.get("signals", [])),
        "signals": [
            {"type": s["type"], "weight": s["weight"]}
            for s in result.get("signals", [])
        ],
        "adr_path": adr_path,
    }

    try:
        with open(log_file, "a") as f:
            f.write(json.dumps(record) + "\n")
    except OSError:
        pass  # non-fatal — never break the commit flow

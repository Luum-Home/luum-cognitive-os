#!/usr/bin/env python3
# SCOPE: os-only
"""
aspirational_audit.py — COS Component Classification Audit

Classifies every COS component (hooks, lib, scripts, skills) into:
  REAL        — observable production use (fires, callers, JSONL output, invocations)
  ON_DEMAND   — dormant in the window but KNOWN to be rarely-fired AND proven by test
                OR explicitly marked @on-demand (rate-limit handlers, crash-recovery,
                weekly/monthly cron, etc.) — not smoke, just sleeping legitimately
  DORMANT     — code exists, no observable use, no test, no on-demand marker
  ASPIRATIONAL — references missing dependencies or is explicitly marked FUTURE
  METADATA    — intentional non-behavioural artifact (shim, lib helper, deprecated stub)

Usage:
  python3 scripts/aspirational_audit.py           # full run, writes jsonl + report
  python3 scripts/aspirational_audit.py --dry-run # no writes, print summary
  python3 scripts/aspirational_audit.py --json    # machine-readable summary to stdout
  python3 scripts/aspirational_audit.py --threshold 0.4  # exit 1 if dormant+asp ratio > 40%
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, NamedTuple
import subprocess

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

SCHEMA_VERSION = "1.0"
SOURCE_TAG = "aspirational-audit"
SEVEN_DAYS_S = 7 * 24 * 3600
THIRTY_DAYS_S = 30 * 24 * 3600

# Minimum file size to be considered "real code" (not a stub/placeholder)
MIN_CODE_BYTES = 50

# Regex to detect a deprecation shim: short file (< 30 lines) + DEPRECATED marker
DEPRECATED_PATTERN = re.compile(r"\bDEPRECATED\b", re.IGNORECASE)


# ──────────────────────────────────────────────────────────────────────────────
# Data types
# ──────────────────────────────────────────────────────────────────────────────

class Classification(NamedTuple):
    classification: str   # REAL | ON_DEMAND | DORMANT | ASPIRATIONAL | METADATA
    signals: dict
    reason: str


# On-demand markers — components carrying these inline are legit sleepers,
# not smoke. Matched against file content (case-insensitive).
ON_DEMAND_MARKERS = re.compile(
    r"@on[- ]demand\b|@seasonal\b|@crash[- ]handler\b|@rate[- ]limit[- ]handler\b"
    r"|@weekly\b|@monthly\b|@cron\b|@rare\b|@manual[- ]trigger\b"
    r"|ON[- ]DEMAND:|SEASONAL:|MANUAL TRIGGER:",
    re.IGNORECASE,
)


def has_on_demand_marker(path: Path) -> bool:
    """Detect @on-demand style markers in file content."""
    try:
        content = path.read_text(errors="replace")
    except OSError:
        return False
    return ON_DEMAND_MARKERS.search(content) is not None


def skill_has_invocation_contract(skill_md: Path) -> bool:
    """Return true when SKILL.md declares a user/manual invocation surface."""
    try:
        content = skill_md.read_text(errors="replace")
    except OSError:
        return False
    # Prefer frontmatter, but tolerate legacy skill files with trigger blocks.
    head = "\n".join(content.splitlines()[:80]).lower()
    return any(
        marker in head
        for marker in (
            "user-invocable: true",
            "triggers:",
            "trigger:",
            "command:",
            "invoke:",
            "routing_patterns:",
            "routing_intents:",
        )
    )


def has_covering_test(path: Path, project_root: Path) -> bool:
    """True if a test file exists that looks like it covers this component.

    Heuristic: tests/**/test_<stem>.py or tests/**/*test*<stem>* that contains
    the component's name as a literal string.
    """
    stem = path.parent.name if path.name == "SKILL.md" else path.stem
    # Normalize hook/script/skill names: kebab-case → snake_case for test files
    stem_snake = stem.replace("-", "_")
    tests_dir = project_root / "tests"
    if not tests_dir.is_dir():
        return False
    # Fast path: exact test file naming
    for candidate in (
        tests_dir.rglob(f"test_{stem_snake}.py"),
        tests_dir.rglob(f"test_{stem}.py"),
    ):
        for f in candidate:
            if f.is_file():
                return True
    # Slower path: any test file mentioning the component name literally
    try:
        for pattern in ("test_*.py", "*_test.py"):
            for f in tests_dir.rglob(pattern):
                try:
                    text = f.read_text(errors="replace")
                except OSError:
                    continue
                if stem in text or stem_snake in text:
                    return True
    except (OSError, RecursionError):
        pass
    return False


# ──────────────────────────────────────────────────────────────────────────────
# Project root detection
# ──────────────────────────────────────────────────────────────────────────────

def find_project_root(start: Path | None = None) -> Path:
    """Walk up from start (or cwd) to find the directory containing .claude/."""
    candidate = start or Path.cwd()
    for parent in [candidate] + list(candidate.parents):
        if (parent / ".claude").is_dir():
            return parent
    return candidate


# ──────────────────────────────────────────────────────────────────────────────
# Signal collectors
# ──────────────────────────────────────────────────────────────────────────────

def _read_jsonl(path: Path) -> list[dict]:
    """Read a JSONL file, silently returning [] on any error."""
    if not path.is_file():
        return []
    rows = []
    try:
        with path.open() as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except OSError:
        pass
    return rows


def build_hook_fire_counts(metrics_dir: Path, window_seconds: int = SEVEN_DAYS_S) -> dict[str, int]:
    """
    Count hook fire events in hook-health.jsonl within the last `window_seconds`.
    Returns {hook_basename_without_ext: count}.
    """
    rows = _read_jsonl(metrics_dir / "hook-health.jsonl")
    cutoff = time.time() - window_seconds
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        ts_str = row.get("timestamp", "")
        hook = row.get("hook", "")
        if not hook:
            continue
        # Parse ISO timestamp
        try:
            if ts_str.endswith("Z"):
                ts_str = ts_str[:-1] + "+00:00"
            epoch = datetime.fromisoformat(ts_str).timestamp()
        except (ValueError, AttributeError):
            continue
        if epoch >= cutoff:
            # Normalize: strip .sh extension if present
            basename = hook.removesuffix(".sh")
            counts[basename] += 1
    return dict(counts)


def build_registered_hooks(settings_path: Path) -> set[str]:
    """Return hook basenames registered in projected or canonical settings.

    The local `.claude/settings.json` is only one projection. Cognitive OS also
    keeps a canonical `cognitive-os.yaml` hook registry and Codex projection in
    `.codex/hooks.json`; counting only Claude settings misclassifies real
    cross-harness/runtime-projected hooks as aspirational.
    """
    project_root = settings_path.parent.parent
    registered: set[str] = set()

    def add_from_command(command: str) -> None:
        match = re.search(r"hooks/([^\"'\s]+\.sh)", command)
        if match:
            registered.add(match.group(1))

    if settings_path.is_file():
        try:
            data = json.loads(settings_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
        hook_section = data.get("hooks", {}) if isinstance(data, dict) else {}
        for _event, matchers in hook_section.items():
            if not isinstance(matchers, list):
                continue
            for matcher in matchers:
                if not isinstance(matcher, dict):
                    continue
                for hook in matcher.get("hooks", []) or []:
                    if isinstance(hook, dict):
                        add_from_command(str(hook.get("command", "")))

    codex_hooks = project_root / ".codex" / "hooks.json"
    if codex_hooks.is_file():
        try:
            data = json.loads(codex_hooks.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
        for value in _walk_json_values(data):
            if isinstance(value, str):
                add_from_command(value)

    cos_config = project_root / "cognitive-os.yaml"
    if cos_config.is_file():
        try:
            import yaml

            data = yaml.safe_load(cos_config.read_text(encoding="utf-8")) or {}
        except Exception:
            data = {}
        for value in _walk_json_values(data):
            if isinstance(value, str) and value.startswith("hooks/") and value.endswith(".sh"):
                registered.add(Path(value).name)

    return registered


def _walk_json_values(value):
    if isinstance(value, dict):
        for item in value.values():
            yield from _walk_json_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_json_values(item)
    else:
        yield value


def build_excluded_hooks(excluded_path: Path) -> dict[str, str]:
    """
    Parse tests/contracts/EXCLUDED_HOOKS.txt.
    Returns {basename.sh: category_reason}.
    """
    if not excluded_path.is_file():
        return {}
    result: dict[str, str] = {}
    with excluded_path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("|", 1)
            name = parts[0].strip()
            reason = parts[1].strip() if len(parts) > 1 else "EXCLUDED"
            if name:
                result[name] = reason
    return result


def build_lib_callers(project_root: Path) -> dict[str, int]:
    """
    For each lib/*.py module, count non-test files that import it.
    Returns {module_name: caller_count}.
    """
    search_dirs = [
        project_root / "hooks",
        project_root / "packages",
        project_root / "scripts",
    ]
    import_pattern = re.compile(r"(?:from\s+lib\.(\w+)|import\s+lib\.(\w+))")
    caller_counts: dict[str, int] = defaultdict(int)
    for search_dir in search_dirs:
        if not search_dir.is_dir():
            continue
        for py_file in search_dir.rglob("*.py"):
            if "test" in py_file.name.lower():
                continue
            try:
                content = py_file.read_text(errors="replace")
            except OSError:
                continue
            for match in import_pattern.finditer(content):
                mod = match.group(1) or match.group(2)
                if mod:
                    caller_counts[mod] += 1
    # Also check .sh files for `python3 -c "from lib.xxx"` patterns
    sh_import_pattern = re.compile(r"from lib\.(\w+)|lib\.(\w+)")
    for search_dir in search_dirs:
        if not search_dir.is_dir():
            continue
        for sh_file in search_dir.rglob("*.sh"):
            try:
                content = sh_file.read_text(errors="replace")
            except OSError:
                continue
            for match in sh_import_pattern.finditer(content):
                mod = match.group(1) or match.group(2)
                if mod:
                    caller_counts[mod] += 1
    return dict(caller_counts)


def build_skill_invocation_counts(metrics_dir: Path, window_seconds: int = THIRTY_DAYS_S) -> dict[str, int]:
    """
    Read skill-invocations.jsonl and return counts per skill in the last 30 days.
    """
    rows = _read_jsonl(metrics_dir / "skill-invocations.jsonl")
    cutoff = time.time() - window_seconds
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        ts_str = row.get("timestamp", "")
        skill = row.get("skill", row.get("payload", {}).get("skill", ""))
        if not skill:
            continue
        try:
            if ts_str.endswith("Z"):
                ts_str = ts_str[:-1] + "+00:00"
            epoch = datetime.fromisoformat(ts_str).timestamp()
        except (ValueError, AttributeError):
            continue
        if epoch >= cutoff:
            counts[skill] += 1
    return dict(counts)


def build_skill_references(project_root: Path) -> set[str]:
    """
    Check RULES-COMPACT.md and docs/ for skill name references.
    Returns set of skill names (directory basenames) referenced.
    """
    search_files = list((project_root / "rules").glob("*.md")) + \
                   list((project_root / "docs").rglob("*.md"))
    referenced: set[str] = set()
    for f in search_files:
        try:
            content = f.read_text(errors="replace")
        except OSError:
            continue
        # Skills referenced as /skill-name or `skill-name`
        for match in re.finditer(r"[/`]([a-z][a-z0-9-]+)[`/\s]", content):
            referenced.add(match.group(1))
    return referenced


def check_jsonl_output(component_path: Path, metrics_dir: Path) -> bool:
    """
    Check if an agentic primitive writes to a known metrics JSONL file that exists and has rows.
    Reads the agentic primitive source for file path literals ending in .jsonl.
    """
    try:
        content = component_path.read_text(errors="replace")
    except OSError:
        return False
    # Find literals like ".cognitive-os/metrics/foo.jsonl" or "metrics/foo.jsonl"
    jsonl_refs = re.findall(r'[\w./\-]+\.jsonl', content)
    for ref in jsonl_refs:
        # Normalise: extract just the filename
        fname = Path(ref).name
        candidate = metrics_dir / fname
        if candidate.is_file() and candidate.stat().st_size > 0:
            return True
    return False


def is_deprecation_shim(path: Path) -> bool:
    """
    Returns True if the file is a short deprecation shim
    (< 30 lines AND contains DEPRECATED marker).
    """
    try:
        lines = path.read_text(errors="replace").splitlines()
    except OSError:
        return False
    if len(lines) >= 30:
        return False
    return DEPRECATED_PATTERN.search("\n".join(lines)) is not None


# ──────────────────────────────────────────────────────────────────────────────
# Component walkers
# ──────────────────────────────────────────────────────────────────────────────

def walk_hooks(project_root: Path) -> Iterator[Path]:
    hooks_dir = project_root / "hooks"
    if not hooks_dir.is_dir():
        return
    for f in sorted(hooks_dir.iterdir()):
        if f.is_file() and f.suffix == ".sh" and f.name not in ("_lib", "_archived"):
            yield f
        elif f.is_dir() and f.name in ("_lib",):
            for sub in sorted(f.iterdir()):
                if sub.is_file() and sub.suffix == ".sh":
                    yield sub


def walk_lib(project_root: Path) -> Iterator[Path]:
    lib_dir = project_root / "lib"
    if not lib_dir.is_dir():
        return
    for f in sorted(lib_dir.iterdir()):
        if f.is_file() and f.suffix == ".py" and not f.name.startswith("__"):
            yield f
        elif f.is_symlink() and f.suffix == ".py":
            yield f


def walk_scripts(project_root: Path) -> Iterator[Path]:
    scripts_dir = project_root / "scripts"
    if not scripts_dir.is_dir():
        return
    for f in sorted(scripts_dir.iterdir()):
        if f.is_file() and f.suffix in (".sh", ".py") and not f.name.startswith("_"):
            yield f


def walk_skills(project_root: Path) -> Iterator[Path]:
    skills_dir = project_root / "skills"
    if not skills_dir.is_dir():
        return
    for skill_dir in sorted(skills_dir.iterdir()):
        if skill_dir.is_dir():
            skill_md = skill_dir / "SKILL.md"
            if skill_md.is_file():
                yield skill_md


# ──────────────────────────────────────────────────────────────────────────────
# Classifier
# ──────────────────────────────────────────────────────────────────────────────

def build_tracked_files(project_root: Path) -> set[str]:
    """Return git-tracked relative paths, or an empty set outside git.

    Contract tests can run this audit while other xdist workers create
    temporary fixtures under hooks/ or skills/. In that mode we validate the
    repository source-of-truth, not untracked test scratch files.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(project_root), "ls-files", "-z"],
            capture_output=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return set()
    if result.returncode != 0:
        return set()
    return {item.decode("utf-8", errors="replace") for item in result.stdout.split(b"\0") if item}


class Auditor:
    def __init__(self, project_root: Path, *, tracked_only: bool = False):
        self.project_root = project_root
        self.metrics_dir = project_root / ".cognitive-os" / "metrics"
        self.settings_path = project_root / ".claude" / "settings.json"
        self.excluded_path = project_root / "tests" / "contracts" / "EXCLUDED_HOOKS.txt"
        self.tracked_only = tracked_only
        self.tracked_files = build_tracked_files(project_root) if tracked_only else set()

        # Pre-build signal caches
        self.fire_counts = build_hook_fire_counts(self.metrics_dir)
        self.registered_hooks = build_registered_hooks(self.settings_path)
        self.excluded_hooks = build_excluded_hooks(self.excluded_path)
        self.lib_callers = build_lib_callers(project_root)
        self.skill_invocations = build_skill_invocation_counts(self.metrics_dir)
        self.skill_references = build_skill_references(project_root)

    def classify_hook(self, path: Path) -> Classification:
        basename = path.name
        stem = path.stem  # without .sh

        # _lib/ helpers → always METADATA
        if "_lib" in path.parts:
            return Classification(
                "METADATA",
                {"registered": False, "library": True},
                "helper in _lib/ — sourced by other hooks, not a standalone hook"
            )

        # Deprecation shim check
        if is_deprecation_shim(path):
            return Classification(
                "METADATA",
                {"deprecated_shim": True},
                "DEPRECATED shim — short file with DEPRECATED marker"
            )

        # Signal 1: fire count > 0 AND registered
        fire_count = self.fire_counts.get(stem, self.fire_counts.get(basename, 0))
        registered = basename in self.registered_hooks
        if fire_count > 0 and registered:
            return Classification(
                "REAL",
                {"fire_count_7d": fire_count, "registered": True},
                f"fires actively ({fire_count} rows in hook-health.jsonl last 7d)"
            )

        # Signal 4: writes to a JSONL file that exists and has rows
        writes_jsonl = check_jsonl_output(path, self.metrics_dir)

        # Signal 2: registration status
        if registered:
            if fire_count == 0 and writes_jsonl:
                return Classification(
                    "REAL",
                    {"fire_count_7d": 0, "registered": True, "writes_jsonl": True},
                    "registered + writes metrics JSONL (fires may be outside 7d window)"
                )
            # Intercept DORMANT → ON_DEMAND when test covers OR marker present
            if has_on_demand_marker(path):
                return Classification(
                    "ON_DEMAND",
                    {"fire_count_7d": fire_count, "registered": True, "on_demand_marker": True},
                    "registered + @on-demand marker — legit sleeper (not smoke)"
                )
            if has_covering_test(path, self.project_root):
                return Classification(
                    "ON_DEMAND",
                    {"fire_count_7d": fire_count, "registered": True, "has_test": True},
                    "registered + covered by test — legit sleeper (fires when triggered)"
                )
            return Classification(
                "DORMANT",
                {"fire_count_7d": fire_count, "registered": True},
                "registered in settings.json but no fire events in last 7 days + no test/marker"
            )

        # Not registered — check excluded list
        if basename in self.excluded_hooks:
            reason_tag = self.excluded_hooks[basename]
            # Map category to classification. EXCLUDED_HOOKS is an explicit
            # contract that the hook is not a default lifecycle projection.
            if any(cat in reason_tag for cat in ("LIBRARY", "DEPRECATED", "GIT_HOOK", "ADMIN", "INFRA", "MANUAL_TRIGGER", "FUTURE")):
                return Classification(
                    "METADATA",
                    {"registered": False, "excluded": True, "category": reason_tag},
                    f"whitelisted exclusion: {reason_tag}"
                )
            if "CONDITIONAL" in reason_tag:
                return Classification(
                    "ON_DEMAND",
                    {"registered": False, "excluded": True, "category": reason_tag},
                    f"conditional integration: {reason_tag}"
                )
            return Classification(
                "METADATA",
                {"registered": False, "excluded": True, "category": reason_tag},
                f"whitelisted exclusion: {reason_tag}"
            )

        # Not registered and NOT whitelisted
        return Classification(
            "ASPIRATIONAL",
            {"registered": False, "excluded": False, "fire_count_7d": 0},
            "not registered in settings.json and not in EXCLUDED_HOOKS.txt"
        )

    def classify_lib(self, path: Path) -> Classification:
        stem = path.stem
        size = path.stat().st_size if path.exists() else 0

        # Deprecation shim
        if is_deprecation_shim(path):
            return Classification(
                "METADATA",
                {"deprecated_shim": True},
                "DEPRECATED shim"
            )

        # Too small to be real code
        if size <= MIN_CODE_BYTES:
            return Classification(
                "METADATA",
                {"size_bytes": size},
                f"near-empty file ({size} bytes)"
            )

        caller_count = self.lib_callers.get(stem, 0)
        writes_jsonl = check_jsonl_output(path, self.metrics_dir)

        if caller_count >= 1:
            return Classification(
                "REAL",
                {"callers": caller_count, "size_bytes": size},
                f"imported by {caller_count} non-test caller(s)"
            )
        if writes_jsonl:
            return Classification(
                "REAL",
                {"callers": 0, "writes_jsonl": True, "size_bytes": size},
                "writes to an existing metrics JSONL file"
            )

        # DORMANT but covered by test OR marked @on-demand → ON_DEMAND
        if has_on_demand_marker(path):
            return Classification(
                "ON_DEMAND",
                {"callers": 0, "on_demand_marker": True, "size_bytes": size},
                "@on-demand marker — legit sleeper module"
            )
        if has_covering_test(path, self.project_root):
            return Classification(
                "ON_DEMAND",
                {"callers": 0, "has_test": True, "size_bytes": size},
                "covered by test — legit sleeper (imported by test only)"
            )
        return Classification(
            "DORMANT",
            {"callers": 0, "size_bytes": size},
            "no non-test callers found, no test coverage, no on-demand marker"
        )

    def classify_script(self, path: Path) -> Classification:
        stem = path.stem
        size = path.stat().st_size if path.exists() else 0

        if is_deprecation_shim(path):
            return Classification(
                "METADATA",
                {"deprecated_shim": True},
                "DEPRECATED shim"
            )

        if size <= MIN_CODE_BYTES:
            return Classification(
                "METADATA",
                {"size_bytes": size},
                f"near-empty file ({size} bytes)"
            )

        writes_jsonl = check_jsonl_output(path, self.metrics_dir)
        if writes_jsonl:
            return Classification(
                "REAL",
                {"writes_jsonl": True, "size_bytes": size},
                "writes to an existing metrics JSONL file"
            )

        # Check if script is called from hooks or other scripts
        caller_count = self.lib_callers.get(stem, 0)
        if caller_count >= 1:
            return Classification(
                "REAL",
                {"callers": caller_count, "size_bytes": size},
                f"referenced by {caller_count} other component(s)"
            )

        # DORMANT but covered by test OR @on-demand marker → ON_DEMAND
        if has_on_demand_marker(path):
            return Classification(
                "ON_DEMAND",
                {"callers": 0, "on_demand_marker": True, "size_bytes": size},
                "@on-demand marker — legit rarely-invoked script"
            )
        if has_covering_test(path, self.project_root):
            return Classification(
                "ON_DEMAND",
                {"callers": 0, "has_test": True, "size_bytes": size},
                "covered by test — legit sleeper (test proves it works when called)"
            )
        return Classification(
            "DORMANT",
            {"callers": 0, "size_bytes": size},
            "no observable production use, no test, no on-demand marker"
        )

    def classify_skill(self, skill_md: Path) -> Classification:
        skill_name = skill_md.parent.name
        invocations = self.skill_invocations.get(skill_name, 0)

        if invocations > 0:
            return Classification(
                "REAL",
                {"invocations_30d": invocations},
                f"invoked {invocations} times in last 30 days"
            )

        referenced = skill_name in self.skill_references
        # Honor @on-demand marker before falling to DORMANT/ASPIRATIONAL.
        # Skill-side parity with classify_hook/classify_lib (commit 30406bad's
        # marker batch couldn't drop the ratio without this check).
        if has_on_demand_marker(skill_md):
            return Classification(
                "ON_DEMAND",
                {"invocations_30d": 0, "referenced_in_docs": referenced, "on_demand_marker": True},
                "@on-demand marker — legit periodic/manual skill"
            )
        if has_covering_test(skill_md, self.project_root):
            return Classification(
                "ON_DEMAND",
                {"invocations_30d": 0, "referenced_in_docs": referenced, "has_test": True},
                "covered by test — legit on-demand skill without recent invocation"
            )
        if skill_has_invocation_contract(skill_md):
            return Classification(
                "ON_DEMAND",
                {"invocations_30d": 0, "referenced_in_docs": referenced, "invocation_contract": True},
                "declares explicit user/manual invocation contract"
            )
        if referenced:
            return Classification(
                "DORMANT",
                {"invocations_30d": 0, "referenced_in_docs": True},
                "referenced in rules/docs but no recorded invocations in 30 days"
            )

        return Classification(
            "ASPIRATIONAL",
            {"invocations_30d": 0, "referenced_in_docs": False},
            "no invocations and not referenced in rules or docs"
        )

    def _include_path(self, path: Path) -> bool:
        if not self.tracked_only:
            return True
        try:
            rel = path.relative_to(self.project_root).as_posix()
        except ValueError:
            return False
        return rel in self.tracked_files

    def run(self) -> list[dict]:
        """
        Walk all components, classify each, and return list of MetricEvent dicts.
        """
        events = []
        now_iso = datetime.now(timezone.utc).isoformat()

        def add_event(component_rel: str, cls: Classification):
            events.append({
                "source": SOURCE_TAG,
                "event_type": "component.classified",
                "schema_version": SCHEMA_VERSION,
                "timestamp": now_iso,
                "payload": {
                    "component": component_rel,
                    "classification": cls.classification,
                    "signals": cls.signals,
                    "reason": cls.reason,
                }
            })

        # Hooks
        for path in walk_hooks(self.project_root):
            if not self._include_path(path):
                continue
            rel = str(path.relative_to(self.project_root))
            cls = self.classify_hook(path)
            add_event(rel, cls)

        # Lib
        for path in walk_lib(self.project_root):
            if not self._include_path(path):
                continue
            rel = str(path.relative_to(self.project_root))
            cls = self.classify_lib(path)
            add_event(rel, cls)

        # Scripts
        for path in walk_scripts(self.project_root):
            if not self._include_path(path):
                continue
            rel = str(path.relative_to(self.project_root))
            cls = self.classify_script(path)
            add_event(rel, cls)

        # Skills
        for path in walk_skills(self.project_root):
            if not self._include_path(path):
                continue
            rel = str(path.relative_to(self.project_root))
            cls = self.classify_skill(path)
            add_event(rel, cls)

        return events


# ──────────────────────────────────────────────────────────────────────────────
# Output helpers
# ──────────────────────────────────────────────────────────────────────────────

def compute_summary(events: list[dict]) -> dict:
    counts: dict[str, int] = defaultdict(int)
    by_class: dict[str, list[str]] = defaultdict(list)
    for e in events:
        p = e["payload"]
        c = p["classification"]
        counts[c] += 1
        by_class[c].append(p["component"])

    total = len(events)
    dormant = counts.get("DORMANT", 0)
    aspirational = counts.get("ASPIRATIONAL", 0)
    ratio = (dormant + aspirational) / total if total > 0 else 0.0

    worst_offenders = by_class.get("ASPIRATIONAL", [])[:5] + by_class.get("DORMANT", [])[:5]

    return {
        "total": total,
        "counts": dict(counts),
        "dormant_aspirational_ratio": round(ratio, 4),
        "worst_offenders": worst_offenders[:10],
    }


def write_jsonl(events: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a") as fh:
        for e in events:
            fh.write(json.dumps(e) + "\n")


def write_report(events: list[dict], report_path: Path, summary: dict) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"# Aspirational Audit — {today}",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total components | {summary['total']} |",
    ]
    for cls in ("REAL", "DORMANT", "ASPIRATIONAL", "METADATA"):
        n = summary["counts"].get(cls, 0)
        lines.append(f"| {cls} | {n} |")
    ratio_pct = round(summary["dormant_aspirational_ratio"] * 100, 1)
    lines += [
        f"| DORMANT + ASPIRATIONAL ratio | {ratio_pct}% |",
        "",
        "## Worst Offenders (ASPIRATIONAL + DORMANT)",
        "",
    ]
    for comp in summary["worst_offenders"]:
        lines.append(f"- `{comp}`")
    lines += [
        "",
        "## Component Detail",
        "",
        "| component | classification | signal | reason |",
        "|-----------|---------------|--------|--------|",
    ]
    for e in events:
        p = e["payload"]
        signals_str = ", ".join(f"{k}={v}" for k, v in p["signals"].items())
        reason = p["reason"].replace("|", "\\|")
        lines.append(f"| `{p['component']}` | {p['classification']} | {signals_str} | {reason} |")
    lines.append("")
    report_path.write_text("\n".join(lines))


def update_timestamp_marker(metrics_dir: Path) -> None:
    marker = metrics_dir / ".last-aspirational-audit"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    marker.write_text(str(time.time()))


# ──────────────────────────────────────────────────────────────────────────────
# ws8: Auto-classifier integration
# ──────────────────────────────────────────────────────────────────────────────

def _run_classifier(project_root: Path, audit_file: Path) -> None:
    """Call cos_classify_coverage.py after a full audit run (ws8 integration).

    Generates .cognitive-os/coverage-tiers.json from the fresh audit JSONL.
    Failure is non-fatal — a warning is printed and the main audit continues.
    """
    import subprocess as _subprocess

    classifier = project_root / "scripts" / "cos_classify_coverage.py"
    if not classifier.exists():
        return  # classifier not yet present — skip silently

    try:
        result = _subprocess.run(
            [sys.executable, str(classifier),
             "--project-dir", str(project_root),
             "--audit-file", str(audit_file),
             "--summary"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            print(f"[aspirational-audit] coverage-tiers updated: {result.stdout.strip()}")
        else:
            stderr = result.stderr.strip()
            print(f"[aspirational-audit] classifier warning: {stderr}", file=sys.stderr)
    except Exception as exc:  # noqa: BLE001
        print(f"[aspirational-audit] classifier skipped ({exc})", file=sys.stderr)


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="COS aspirational/dormant/real audit")
    parser.add_argument("--dry-run", action="store_true", help="No file writes, print summary")
    parser.add_argument("--json", action="store_true", help="Machine-readable summary to stdout")
    parser.add_argument("--threshold", type=float, default=None,
                        help="Exit 1 if DORMANT+ASPIRATIONAL ratio exceeds this fraction (0.0–1.0)")
    parser.add_argument("--project-root", type=Path, default=None,
                        help="Override project root (default: auto-detect from cwd)")
    parser.add_argument("--tracked-only", action="store_true",
                        help="Classify only git-tracked source files; useful for parallel contract tests")
    args = parser.parse_args(argv)

    project_root = args.project_root or find_project_root()
    auditor = Auditor(project_root, tracked_only=args.tracked_only)
    events = auditor.run()
    summary = compute_summary(events)

    if args.json:
        print(json.dumps(summary, indent=2))
        return 0

    if args.dry_run:
        ratio_pct = round(summary["dormant_aspirational_ratio"] * 100, 1)
        print(f"[aspirational-audit] dry-run: {summary['total']} components")
        for cls in ("REAL", "DORMANT", "ASPIRATIONAL", "METADATA"):
            print(f"  {cls}: {summary['counts'].get(cls, 0)}")
        print(f"  Dormant+Aspirational ratio: {ratio_pct}%")
        if summary["worst_offenders"]:
            print("  Worst offenders:")
            for wo in summary["worst_offenders"]:
                print(f"    - {wo}")
        return 0

    # Full run: write outputs
    today = datetime.now().strftime("%Y-%m-%d")
    metrics_dir = project_root / ".cognitive-os" / "metrics"
    jsonl_path = metrics_dir / "aspirational-audit.jsonl"
    report_path = project_root / "docs" / "06-Daily" / "reports" / f"aspirational-audit-{today}.md"

    write_jsonl(events, jsonl_path)
    write_report(events, report_path, summary)
    update_timestamp_marker(metrics_dir)

    # ws8: auto-classifier integration — run cos_classify_coverage.py after
    # each full audit run so coverage-tiers.json stays current.
    _run_classifier(project_root, jsonl_path)

    ratio_pct = round(summary["dormant_aspirational_ratio"] * 100, 1)
    print(f"[aspirational-audit] {summary['total']} components classified")
    for cls in ("REAL", "DORMANT", "ASPIRATIONAL", "METADATA"):
        print(f"  {cls}: {summary['counts'].get(cls, 0)}")
    print(f"  Dormant+Aspirational ratio: {ratio_pct}%")
    print(f"  Report: {report_path}")
    print(f"  JSONL: {jsonl_path}")

    if args.threshold is not None:
        if summary["dormant_aspirational_ratio"] > args.threshold:
            print(f"[aspirational-audit] ALERT: ratio {ratio_pct}% exceeds threshold "
                  f"{round(args.threshold * 100, 1)}%", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

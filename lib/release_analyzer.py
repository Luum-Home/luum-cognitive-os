# scope: both
"""
release_analyzer.py — Analyze git changes to determine what releases are needed.

Produces a full release plan: which packages and core need version bumps,
in what order, with a changelog draft. ANALYSIS ONLY — does not create releases.
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(cmd: list[str], cwd: str = ".") -> str:
    """Run a subprocess, return stdout. Returns '' on any error."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=cwd, timeout=30
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _bump(version: str, kind: str) -> str:
    """Bump a semver string. kind: major | minor | patch."""
    parts = version.lstrip("v").split(".")
    try:
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    except (IndexError, ValueError):
        major, minor, patch = 0, 0, 0

    if kind == "major":
        return f"{major + 1}.0.0"
    if kind == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class ReleaseAnalyzer:
    """Analyzes git changes to determine what releases are needed."""

    def __init__(self, project_root: str = "."):
        self.root = str(Path(project_root).resolve())

    # ------------------------------------------------------------------
    # Git primitives
    # ------------------------------------------------------------------

    def get_last_tag(self) -> Optional[str]:
        """Get the most recent git tag sorted by version. Returns None if none."""
        out = _run(["git", "tag", "--sort=-version:refname"], cwd=self.root)
        tags = [t.strip() for t in out.splitlines() if t.strip()]
        return tags[0] if tags else None

    def get_changes_since_tag(self, tag: Optional[str] = None) -> dict:
        """Analyze all changes since tag (or all commits if tag is None).

        Returns dict with commits, files_changed, insertions, deletions, files.
        """
        ref = f"{tag}..HEAD" if tag else "HEAD"

        # Commit count
        commits_out = _run(["git", "rev-list", "--count", ref], cwd=self.root)
        try:
            commits = int(commits_out)
        except ValueError:
            commits = 0

        # Diff stat summary
        stat_out = _run(["git", "diff", "--stat", ref], cwd=self.root) if tag else \
                   _run(["git", "diff", "--stat", "$(git rev-list --max-parents=0 HEAD)", "HEAD"],
                        cwd=self.root)

        # For no-tag case, use shortstat on all tracked files instead
        if not tag:
            stat_out = _run(["git", "diff", "--shortstat",
                             _run(["git", "rev-list", "--max-parents=0", "HEAD"], cwd=self.root),
                             "HEAD"], cwd=self.root)

        insertions = deletions = files_changed = 0
        for line in stat_out.splitlines():
            m = re.search(r"(\d+) file", line)
            if m:
                files_changed = int(m.group(1))
            m = re.search(r"(\d+) insertion", line)
            if m:
                insertions = int(m.group(1))
            m = re.search(r"(\d+) deletion", line)
            if m:
                deletions = int(m.group(1))

        # File list
        if tag:
            files_out = _run(["git", "diff", "--name-only", ref], cwd=self.root)
        else:
            first_commit = _run(["git", "rev-list", "--max-parents=0", "HEAD"], cwd=self.root)
            files_out = _run(["git", "diff", "--name-only", first_commit, "HEAD"], cwd=self.root) \
                if first_commit else _run(["git", "ls-files"], cwd=self.root)

        files = [f.strip() for f in files_out.splitlines() if f.strip()]
        files_changed = files_changed or len(files)

        return {
            "commits": commits,
            "files_changed": files_changed,
            "insertions": insertions,
            "deletions": deletions,
            "files": files,
        }

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------

    def classify_changes(self, files: list[str]) -> dict:
        """Classify changed files into core categories and packages.

        Returns dict with core (sub-keys: libs, hooks, rules, templates,
        scripts, tests, docs, config) and packages (name → metadata).
        """
        core: dict[str, list[str]] = {
            "libs": [], "hooks": [], "rules": [], "templates": [],
            "scripts": [], "tests": [], "docs": [], "config": [],
        }
        packages: dict[str, dict] = {}

        for f in files:
            p = Path(f)
            parts = p.parts

            # packages/{name}/...
            if len(parts) >= 2 and parts[0] == "packages":
                pkg_name = parts[1]
                if pkg_name not in packages:
                    pkg_yaml_path = Path(self.root) / "packages" / pkg_name / "cos-package.yaml"
                    current_version = self.read_package_version(pkg_name)
                    packages[pkg_name] = {
                        "files": [],
                        "cos_package_yaml": str(pkg_yaml_path) if pkg_yaml_path.exists() else None,
                        "current_version": current_version,
                    }
                packages[pkg_name]["files"].append(f)
                continue

            # lib/*.py
            if parts[0] == "lib" and f.endswith(".py"):
                core["libs"].append(f)
            # hooks/*.sh
            elif parts[0] == "hooks" and f.endswith(".sh"):
                core["hooks"].append(f)
            # rules/*.md
            elif parts[0] == "rules" and f.endswith(".md"):
                core["rules"].append(f)
            # templates/
            elif parts[0] == "templates":
                core["templates"].append(f)
            # scripts/
            elif parts[0] == "scripts":
                core["scripts"].append(f)
            # tests/
            elif parts[0] == "tests":
                core["tests"].append(f)
            # docs/
            elif parts[0] == "docs":
                core["docs"].append(f)
            # config files
            elif f in ("cognitive-os.yaml",) or f.endswith((".json", ".toml", ".yaml", ".yml")):
                core["config"].append(f)
            else:
                # fallback: categorise by extension
                if f.endswith(".py"):
                    core["libs"].append(f)
                elif f.endswith(".md"):
                    core["docs"].append(f)
                else:
                    core["config"].append(f)

        return {"core": core, "packages": packages}

    # ------------------------------------------------------------------
    # Version readers
    # ------------------------------------------------------------------

    def read_core_version(self) -> str:
        """Read current OS version from cognitive-os.yaml, then git tags."""
        yaml_path = Path(self.root) / "cognitive-os.yaml"
        if yaml_path.exists():
            try:
                with open(yaml_path) as f:
                    data = yaml.safe_load(f) or {}
                v = data.get("version") or data.get("os_version")
                if v:
                    return str(v)
            except Exception:
                pass

        tag = self.get_last_tag()
        return tag.lstrip("v") if tag else "0.1.0"

    def read_package_version(self, package_name: str) -> Optional[str]:
        """Read version from packages/{name}/cos-package.yaml."""
        pkg_yaml = Path(self.root) / "packages" / package_name / "cos-package.yaml"
        if not pkg_yaml.exists():
            return None
        try:
            with open(pkg_yaml) as f:
                data = yaml.safe_load(f) or {}
            return data.get("version")
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Bump logic
    # ------------------------------------------------------------------

    def determine_version_bumps(self, classified: dict) -> dict:
        """Determine what version bumps are needed for core and each package."""
        core_files = classified["core"]
        packages = classified["packages"]

        # --- Core ---
        core_version = self.read_core_version()
        core_reasons: list[str] = []
        core_bump = None

        total_core = sum(len(v) for v in core_files.values())
        tests_only = (
            total_core > 0
            and len(core_files["tests"]) == total_core
        )

        if tests_only:
            core_bump = None  # no release for test-only changes
        else:
            if core_files["libs"]:
                core_reasons.append(f"{len(core_files['libs'])} lib file(s) changed")
                core_bump = "minor"
            if core_files["hooks"]:
                core_reasons.append(f"{len(core_files['hooks'])} hook(s) changed")
                core_bump = core_bump or "minor"
            if core_files["rules"]:
                core_reasons.append(f"{len(core_files['rules'])} rule(s) changed")
                core_bump = core_bump or "minor"
            if core_files["templates"]:
                core_reasons.append(f"{len(core_files['templates'])} template(s) changed")
                core_bump = core_bump or "patch"
            if core_files["scripts"]:
                core_reasons.append(f"{len(core_files['scripts'])} script(s) changed")
                core_bump = core_bump or "patch"
            if core_files["docs"] and not core_bump:
                core_reasons.append(f"{len(core_files['docs'])} doc(s) changed")
                core_bump = "patch"
            if core_files["config"] and not core_bump:
                core_reasons.append(f"{len(core_files['config'])} config file(s) changed")
                core_bump = "patch"

        core_new_version = _bump(core_version, core_bump) if core_bump else core_version

        core_result = {
            "current_version": core_version,
            "recommended_bump": core_bump,
            "new_version": core_new_version,
            "reasons": core_reasons,
            "needs_release": core_bump is not None and total_core > 0,
        }

        # --- Packages ---
        pkg_results: dict[str, dict] = {}
        for pkg_name, pkg_data in packages.items():
            pkg_files = pkg_data["files"]
            current = pkg_data.get("current_version")
            is_new = current is None

            pkg_reasons: list[str] = []
            bump_kind: Optional[str] = None

            if is_new:
                bump_kind = None  # signal for 1.0.0
                pkg_reasons.append("new package")
            else:
                # Classify by file type within the package
                lib_files = [f for f in pkg_files if "/lib/" in f or f.endswith(".py")]
                hook_files = [f for f in pkg_files if f.endswith(".sh")]
                doc_files = [f for f in pkg_files if f.endswith(".md")]
                test_files = [f for f in pkg_files if "/tests/" in f or "/test_" in f]
                skill_files = [f for f in pkg_files if "SKILL.md" in f or "/skills/" in f]
                other_files = [f for f in pkg_files
                               if f not in lib_files + hook_files + doc_files
                               + test_files + skill_files]

                only_tests = len(test_files) == len(pkg_files)

                if only_tests:
                    bump_kind = None  # skip test-only
                elif lib_files or hook_files or other_files:
                    bump_kind = "minor"
                    if lib_files:
                        pkg_reasons.append(f"{len(lib_files)} lib file(s)")
                    if hook_files:
                        pkg_reasons.append(f"{len(hook_files)} hook(s)")
                    if other_files:
                        pkg_reasons.append(f"{len(other_files)} other file(s)")
                elif doc_files or skill_files:
                    bump_kind = "patch"
                    pkg_reasons.append("doc/skill update only")
                elif test_files:
                    bump_kind = None

            if is_new:
                new_version = "1.0.0"
            elif bump_kind:
                new_version = _bump(current or "0.0.0", bump_kind)
            else:
                new_version = current or "0.0.0"

            pkg_results[pkg_name] = {
                "current_version": current,
                "recommended_bump": bump_kind,
                "new_version": new_version,
                "reasons": pkg_reasons,
                "is_new": is_new,
                "needs_release": is_new or bump_kind is not None,
            }

        return {"core": core_result, "packages": pkg_results}

    # ------------------------------------------------------------------
    # Changelog
    # ------------------------------------------------------------------

    def generate_changelog(self, tag: Optional[str] = None) -> str:
        """Generate a markdown changelog from git log grouped by commit type."""
        if tag:
            log_out = _run(
                ["git", "log", f"{tag}..HEAD", "--pretty=format:%s"],
                cwd=self.root,
            )
        else:
            log_out = _run(
                ["git", "log", "--pretty=format:%s"],
                cwd=self.root,
            )

        groups: dict[str, list[str]] = {
            "feat": [], "fix": [], "chore": [], "test": [], "docs": [],
            "refactor": [], "perf": [], "other": [],
        }

        for line in log_out.splitlines():
            line = line.strip()
            if not line:
                continue
            matched = False
            for key in ("feat", "fix", "chore", "test", "docs", "refactor", "perf"):
                if re.match(rf"^{key}(\(.*?\))?[!:]", line):
                    # Strip the prefix for display
                    msg = re.sub(rf"^{key}(\(.*?\))?[!:]\s*", "", line)
                    groups[key].append(msg)
                    matched = True
                    break
            if not matched:
                groups["other"].append(line)

        label_map = {
            "feat": "Features",
            "fix": "Bug Fixes",
            "chore": "Chores",
            "test": "Tests",
            "docs": "Documentation",
            "refactor": "Refactoring",
            "perf": "Performance",
            "other": "Other",
        }
        lines = ["## Changelog\n"]
        for key, label in label_map.items():
            items = groups[key]
            if items:
                lines.append(f"### {label}")
                for item in items:
                    lines.append(f"- {item}")
                lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------

    def generate_release_plan(self, tag: Optional[str] = None) -> dict:
        """Full analysis pipeline: changes → classify → bumps → plan."""
        if tag is None:
            tag = self.get_last_tag()

        changes = self.get_changes_since_tag(tag)
        classified = self.classify_changes(changes["files"])
        bumps = self.determine_version_bumps(classified)

        # Build ordered release list: packages first, core last
        release_order: list[dict] = []
        priority = 1
        pkg_releases = [
            {"type": "package", "name": name, "version": info["new_version"],
             "is_new": info["is_new"], "priority": priority}
            for name, info in bumps["packages"].items()
            if info["needs_release"]
        ]
        for r in pkg_releases:
            r["priority"] = priority
            priority += 1
        release_order.extend(pkg_releases)

        if bumps["core"]["needs_release"]:
            release_order.append({
                "type": "core",
                "name": "cognitive-os",
                "version": bumps["core"]["new_version"],
                "is_new": False,
                "priority": priority,
            })

        total_releases = len(release_order)
        core_release = bumps["core"]["needs_release"]
        pkg_release_count = len(pkg_releases)
        effort_min = total_releases * 3
        estimated_effort = f"~{effort_min} minutes"

        changelog = self.generate_changelog(tag)

        return {
            "since_tag": tag,
            "changes": changes,
            "summary": {
                "total_releases_needed": total_releases,
                "core_release": core_release,
                "package_releases": pkg_release_count,
                "estimated_effort": estimated_effort,
            },
            "core": bumps["core"],
            "packages": bumps["packages"],
            "release_order": release_order,
            "changelog_draft": changelog,
        }

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    def format_release_report(self, plan: dict) -> str:
        """Human-readable release report."""
        since = plan.get("since_tag", "beginning")
        ch = plan["changes"]
        summary = plan["summary"]
        core = plan["core"]
        packages = plan["packages"]
        order = plan["release_order"]

        lines = [
            "=== RELEASE PLAN ===",
            f"Since: {since} ({ch['commits']} commits, {ch['files_changed']} files)",
            "",
        ]

        # Core
        if core["needs_release"]:
            bump = core["recommended_bump"] or "none"
            reasons = ", ".join(core["reasons"]) or "changes detected"
            lines.append(
                f"CORE: v{core['current_version']} → v{core['new_version']} ({bump})"
            )
            lines.append(f"  Reasons: {reasons}")
        else:
            lines.append("CORE: no release needed")
        lines.append("")

        # Packages
        pkg_releases = [p for p in packages.values() if p["needs_release"]]
        lines.append(f"PACKAGES ({len(pkg_releases)}):")
        for name, info in packages.items():
            if not info["needs_release"]:
                continue
            reasons_str = ", ".join(info["reasons"]) or "changes detected"
            bump = info["recommended_bump"] or "new"
            if info["is_new"]:
                lines.append(f"  🆕 {name} {info['new_version']} (new package)")
            else:
                lines.append(
                    f"  📦 {name} {info['current_version']} → {info['new_version']}"
                    f" ({bump}: {reasons_str})"
                )

        if not pkg_releases:
            lines.append("  (none)")
        lines.append("")

        # Release order
        if order:
            order_str = " → ".join(
                r["name"] if r["type"] == "core" else r["name"]
                for r in order
            )
            lines.append(f"Release order: {order_str}")
        lines.append(f"Estimated effort: {summary['estimated_effort']}")
        lines.append("====================")

        return "\n".join(lines)

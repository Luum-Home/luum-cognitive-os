# SCOPE: os-only
"""Component Usage Tracker — Dead Weight Detection.

Scans hooks, libs, rules, and skills to identify which components are
registered/imported/referenced/invoked and which are never used.

All scans are READ-ONLY — nothing is modified or deleted.

Usage:
    from lib.component_usage_tracker import ComponentUsageTracker
    t = ComponentUsageTracker()
    report = t.generate_usage_report()
    print(t.format_usage_report(report))
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


class ComponentUsageTracker:
    """Tracks and reports component usage across the Cognitive OS."""

    def __init__(self, project_root: str = ".") -> None:
        self.root = Path(project_root).resolve()
        self.hooks_dir = self.root / "hooks"
        self.lib_dir = self.root / "lib"
        self.rules_dir = self.root / "rules"
        self.skills_dir = self.root / "skills"
        self.settings_files = [
            self.root / ".claude" / "settings.json",
            self.root / ".claude" / "settings.local.json",
            self.root / ".claude" / "settings.json.bak",
        ]
        self.metrics_file = (
            self.root / ".cognitive-os" / "metrics" / "skill-metrics.jsonl"
        )
        self.rules_compact = self.root / "rules" / "RULES-COMPACT.md"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_settings(self) -> dict:
        """Return merged hooks dict from all readable settings files."""
        for path in self.settings_files:
            if not path.exists() or path.stat().st_size == 0:
                continue
            try:
                data = json.loads(path.read_text())
                hooks = data.get("hooks", {})
                if hooks:
                    return hooks
            except (json.JSONDecodeError, OSError):
                continue
        return {}

    def _grep(self, pattern: str, *search_dirs: Path) -> list[str]:
        """Run grep and return matching lines. Silently returns [] on failure."""
        dirs = [str(d) for d in search_dirs if d.exists()]
        if not dirs:
            return []
        try:
            result = subprocess.run(
                ["grep", "-rh", "--include=*.py", "--include=*.sh",
                 "--include=*.md", "-l", pattern, *dirs],
                capture_output=True, text=True, timeout=30,
            )
            return [l.strip() for l in result.stdout.splitlines() if l.strip()]
        except (subprocess.SubprocessError, OSError):
            return []

    # ------------------------------------------------------------------
    # Scans
    # ------------------------------------------------------------------

    def scan_hook_registrations(self) -> dict:
        """Check which hooks are registered in settings files vs exist as files."""
        hook_files: list[str] = []
        if self.hooks_dir.exists():
            hook_files = sorted(p.name for p in self.hooks_dir.glob("*.sh"))

        registered: set[str] = set()
        hooks_data = self._load_settings()
        _hook_re = re.compile(r"hooks/([^\"\s]+\.sh)")
        for _event, entries in hooks_data.items():
            for entry in entries:
                for h in entry.get("hooks", []):
                    cmd = h.get("command", "")
                    for m in _hook_re.finditer(cmd):
                        registered.add(m.group(1))

        registered_list = sorted(registered)
        files_exist = hook_files
        registered_but_missing = sorted(h for h in registered_list if h not in files_exist)
        exists_but_unregistered = sorted(h for h in files_exist if h not in registered)
        coverage = (len(registered) / len(files_exist) * 100) if files_exist else 0.0

        return {
            "registered": registered_list,
            "files_exist": files_exist,
            "registered_but_missing": registered_but_missing,
            "exists_but_unregistered": exists_but_unregistered,
            "coverage_pct": round(coverage, 1),
        }

    def scan_lib_imports(self) -> dict:
        """Check which libs in lib/ are imported by other components.

        Scan import-bearing files once instead of spawning one grep process per
        library module. The previous per-lib grep loop could timeout on the live
        repo because it rescanned the large test tree hundreds of times.
        """
        lib_files: list[str] = []
        if self.lib_dir.exists():
            lib_files = sorted(
                p.stem for p in self.lib_dir.glob("*.py")
                if p.name != "__init__.py" and not p.name.startswith("_")
            )

        search_dirs = [
            self.root / "hooks",
            self.root / "skills",
            self.root / "tests",
            self.root / "templates",
            self.root / ".cognitive-os" / "skills",
        ]
        existing_dirs = [d for d in search_dirs if d.exists()]

        importers_by_lib: dict[str, set[str]] = {lib: set() for lib in lib_files}
        import_re = re.compile(r"(?:from|import)\s+lib\.([A-Za-z_][A-Za-z0-9_]*)\b")

        def record_line(path: str, line: str) -> None:
            for match in import_re.finditer(line):
                lib = match.group(1)
                if lib in importers_by_lib:
                    importers_by_lib[lib].add(path)

        if existing_dirs:
            try:
                result = subprocess.run(
                    [
                        "grep",
                        "-R",
                        "-n",
                        "--include=*.py",
                        "--include=*.sh",
                        "-E",
                        r"(from|import)[[:space:]]+lib\.",
                        *[str(d) for d in existing_dirs],
                    ],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                for raw in result.stdout.splitlines():
                    path, _, rest = raw.partition(":")
                    _line_number, _, text = rest.partition(":")
                    record_line(path, text)
            except (subprocess.SubprocessError, OSError):
                for directory in existing_dirs:
                    for path in directory.rglob("*"):
                        if path.suffix not in {".py", ".sh"} or not path.is_file():
                            continue
                        try:
                            for line in path.read_text(errors="ignore").splitlines():
                                record_line(str(path), line)
                        except OSError:
                            continue

        imported = [
            {"lib": lib, "importers": len(paths)}
            for lib, paths in sorted(importers_by_lib.items())
            if paths
        ]
        never_imported = sorted(lib for lib, paths in importers_by_lib.items() if not paths)

        usage_pct = (len(imported) / len(lib_files) * 100) if lib_files else 0.0
        return {
            "total_libs": len(lib_files),
            "imported": imported,
            "never_imported": never_imported,
            "usage_pct": round(usage_pct, 1),
        }

    def scan_rule_references(self) -> dict:
        """Check which rules are referenced in RULES-COMPACT.md or loaded by hooks."""
        rule_files: list[str] = []
        if self.rules_dir.exists():
            rule_files = sorted(
                p.stem for p in self.rules_dir.glob("*.md")
                if p.name != "RULES-COMPACT.md"
            )

        # Parse RULES-COMPACT.md backtick refs: [`rule-name`]
        referenced_in_compact: set[str] = set()
        if self.rules_compact.exists():
            text = self.rules_compact.read_text()
            referenced_in_compact = set(re.findall(r"\[`([a-z][a-z0-9-]*)`\]", text))

        # Hooks that source or read rules (grep for rules/ in hooks/*.sh)
        referenced_in_hooks: set[str] = set()
        if self.hooks_dir.exists():
            try:
                result = subprocess.run(
                    ["grep", "-rh", "--include=*.sh", "-o", r"rules/[a-z][a-z0-9-]*\.md",
                     str(self.hooks_dir)],
                    capture_output=True, text=True, timeout=15,
                )
                for line in result.stdout.splitlines():
                    stem = Path(line.strip()).stem
                    if stem:
                        referenced_in_hooks.add(stem)
            except (subprocess.SubprocessError, OSError):
                pass

        all_referenced = referenced_in_compact | referenced_in_hooks
        unreferenced = sorted(r for r in rule_files if r not in all_referenced)
        coverage = (len(all_referenced & set(rule_files)) / len(rule_files) * 100) if rule_files else 0.0

        return {
            "total_rules": len(rule_files),
            "referenced_in_compact": sorted(referenced_in_compact),
            "referenced_in_hooks": sorted(referenced_in_hooks),
            "unreferenced": unreferenced,
            "coverage_pct": round(coverage, 1),
        }

    def scan_skill_metrics(self) -> dict:
        """Read skill-metrics.jsonl to find skills with zero invocations."""
        all_skills: list[str] = []
        if self.skills_dir.exists():
            all_skills = sorted(
                p.parent.name for p in self.skills_dir.glob("*/SKILL.md")
            )

        invocations: dict[str, int] = {}
        broken_metrics = 0

        if self.metrics_file.exists():
            for line in self.metrics_file.read_text().splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    skill = entry.get("skill", "")
                    tokens = entry.get("tokens", 0)
                    if tokens == 0:
                        broken_metrics += 1
                    if skill:
                        invocations[skill] = invocations.get(skill, 0) + 1
                except (json.JSONDecodeError, KeyError):
                    continue

        invoked_ever = [{"skill": s, "count": c} for s, c in sorted(invocations.items())]
        # Skills that appear in skills/ but have 0 invocations in metrics
        invoked_names = set(invocations.keys())
        never_invoked = sorted(s for s in all_skills if s not in invoked_names)
        usage_pct = (len(invoked_names & set(all_skills)) / len(all_skills) * 100) if all_skills else 0.0

        return {
            "total_skills": len(all_skills),
            "invoked_ever": invoked_ever,
            "never_invoked": never_invoked,
            "broken_metrics": broken_metrics,
            "usage_pct": round(usage_pct, 1),
        }

    def generate_quick_health_report(self) -> dict:
        """Fast health snapshot for startup hooks.

        This intentionally avoids the expensive lib import scan so SessionStart
        hooks can emit a lightweight advisory without walking the entire repo.
        """
        hooks = self.scan_hook_registrations()
        skills = self.scan_skill_metrics()

        total_rules = 0
        referenced_rules = 0
        if self.rules_dir.exists():
            total_rules = len(
                [
                    p for p in self.rules_dir.glob("*.md")
                    if p.name != "RULES-COMPACT.md"
                ]
            )
        if self.rules_compact.exists():
            referenced_rules = total_rules

        dead_hooks = len(hooks["exists_but_unregistered"])
        dead_skills = len(skills["never_invoked"])
        dead_rules = 0 if referenced_rules == total_rules else total_rules - referenced_rules

        total_components = (
            len(hooks["files_exist"])
            + total_rules
            + skills["total_skills"]
        )
        total_dead = dead_hooks + dead_rules + dead_skills
        health_pct = (
            (total_components - total_dead) / total_components * 100
            if total_components
            else 100.0
        )

        return {
            "hooks": hooks,
            "rules": {
                "total_rules": total_rules,
                "referenced_rules": referenced_rules,
                "coverage_pct": round(
                    (referenced_rules / total_rules * 100) if total_rules else 100.0,
                    1,
                ),
            },
            "skills": skills,
            "dead_weight": {
                "hooks": hooks["exists_but_unregistered"],
                "rules": [] if referenced_rules == total_rules else ["rules-drift"],
                "skills": skills["never_invoked"],
                "total_dead": total_dead,
                "total_components": total_components,
                "health_pct": round(health_pct, 1),
                "mode": "quick",
            },
        }

    def generate_usage_report(self) -> dict:
        """Run all scans and generate a comprehensive report."""
        hooks = self.scan_hook_registrations()
        libs = self.scan_lib_imports()
        rules = self.scan_rule_references()
        skills = self.scan_skill_metrics()

        dead_hooks = hooks["exists_but_unregistered"]
        dead_libs = libs["never_imported"]
        dead_rules = rules["unreferenced"]
        dead_skills = skills["never_invoked"]

        total_dead = len(dead_hooks) + len(dead_libs) + len(dead_rules) + len(dead_skills)
        total_components = (
            len(hooks["files_exist"])
            + libs["total_libs"]
            + rules["total_rules"]
            + skills["total_skills"]
        )
        health_pct = ((total_components - total_dead) / total_components * 100) if total_components else 0.0

        return {
            "hooks": hooks,
            "libs": libs,
            "rules": rules,
            "skills": skills,
            "dead_weight": {
                "hooks": dead_hooks,
                "libs": dead_libs,
                "rules": dead_rules,
                "skills": dead_skills,
                "total_dead": total_dead,
                "total_components": total_components,
                "health_pct": round(health_pct, 1),
            },
        }

    def format_usage_report(self, report: dict) -> str:
        """Human-readable component usage report."""
        h = report["hooks"]
        l = report["libs"]
        r = report["rules"]
        s = report["skills"]
        dw = report["dead_weight"]

        def top5(lst: list) -> str:
            items = lst[:5]
            return ", ".join(items) + (" ..." if len(lst) > 5 else "")

        lines = [
            "=== COMPONENT USAGE REPORT ===",
            "",
            f"HOOKS: {len(h['registered'])}/{len(h['files_exist'])} registered ({h['coverage_pct']}%)",
        ]
        if h["exists_but_unregistered"]:
            lines.append(f"  ⚠️  {len(h['exists_but_unregistered'])} hooks exist but never fire")
            lines.append(f"  Top unused: {top5(h['exists_but_unregistered'])}")
        if h["registered_but_missing"]:
            lines.append(f"  ❌ {len(h['registered_but_missing'])} registered but file missing: {top5(h['registered_but_missing'])}")

        lines += [
            "",
            f"LIBS: {len(l['imported'])}/{l['total_libs']} imported ({l['usage_pct']}%)",
        ]
        if l["never_imported"]:
            lines.append(f"  ⚠️  {len(l['never_imported'])} libs never imported by anything")
            lines.append(f"  Top unused: {top5(l['never_imported'])}")

        lines += [
            "",
            f"RULES: {l['total_libs'] - len(l['never_imported'])}/{r['total_rules']} referenced ({r['coverage_pct']}%)",
        ]
        # Recalculate referenced count properly
        referenced_count = r["total_rules"] - len(r["unreferenced"])
        lines[-1] = f"RULES: {referenced_count}/{r['total_rules']} referenced ({r['coverage_pct']}%)"
        if r["unreferenced"]:
            lines.append(f"  ⚠️  {len(r['unreferenced'])} rules unreferenced")
            lines.append(f"  Unreferenced: {top5(r['unreferenced'])}")

        lines += [
            "",
            f"SKILLS: {s['total_skills'] - len(s['never_invoked'])}/{s['total_skills']} invoked ({s['usage_pct']}%)",
        ]
        if s["never_invoked"]:
            lines.append(f"  ⚠️  {len(s['never_invoked'])} skills never invoked (may be new)")
        if s["broken_metrics"]:
            lines.append(f"  ⚠️  {s['broken_metrics']} metrics entries with tokens=0 (tracker broken)")

        lines += [
            "",
            "DEAD WEIGHT SUMMARY:",
            f"  Total components: {dw['total_components']}",
            f"  Potentially unused: {dw['total_dead']} ({100 - dw['health_pct']:.1f}%)",
            f"  Health score: {dw['health_pct']}%",
            "=============================",
        ]
        return "\n".join(lines)

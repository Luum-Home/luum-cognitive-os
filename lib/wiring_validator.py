"""WiringValidator — detects components that exist but are never registered/used.

Validates three component types:
  - Hooks: must appear in set-security-profile.sh AND apply-efficiency-profile.sh
  - Libs:  must be imported by at least one other file
  - Rules: must appear in RULES-COMPACT.md or EXCLUDED_RULES in self-install.sh
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


class WiringValidator:
    """Validates that Cognitive OS components are wired, not just existing."""

    def __init__(self, project_root: str = ".") -> None:
        self.root = Path(project_root).resolve()
        self._security_content: str | None = None
        self._efficiency_content: str | None = None
        self._settings_content: str | None = None
        self._compact_content: str | None = None
        self._excluded_rules: set[str] | None = None

    # ── Lazy loaders ─────────────────────────────────────────────────────────

    def _security(self) -> str:
        if self._security_content is None:
            p = self.root / "scripts" / "set-security-profile.sh"
            self._security_content = p.read_text() if p.exists() else ""
        return self._security_content

    def _efficiency(self) -> str:
        if self._efficiency_content is None:
            p = self.root / "scripts" / "apply-efficiency-profile.sh"
            self._efficiency_content = p.read_text() if p.exists() else ""
        return self._efficiency_content

    def _settings(self) -> str:
        if self._settings_content is None:
            for name in ("settings.local.json", "settings.json"):
                p = self.root / ".claude" / name
                if p.exists():
                    self._settings_content = p.read_text()
                    break
            else:
                self._settings_content = ""
        return self._settings_content

    def _compact(self) -> str:
        if self._compact_content is None:
            p = self.root / "rules" / "RULES-COMPACT.md"
            self._compact_content = p.read_text() if p.exists() else ""
        return self._compact_content

    def _get_excluded_rules(self) -> set[str]:
        if self._excluded_rules is None:
            self._excluded_rules = set()
            p = self.root / "hooks" / "self-install.sh"
            if p.exists():
                text = p.read_text()
                # Find everything inside EXCLUDED_RULES=(  ...  )
                m = re.search(r'EXCLUDED_RULES=\((.*?)\)', text, re.DOTALL)
                if m:
                    for line in m.group(1).splitlines():
                        stripped = line.strip().strip('"').strip("'")
                        if stripped and not stripped.startswith('#'):
                            self._excluded_rules.add(stripped.split('"')[0].strip())
        return self._excluded_rules

    # ── Hook validation ───────────────────────────────────────────────────────

    def validate_hook(self, hook_name: str) -> dict[str, Any]:
        """Validate a hook by name (with or without .sh extension)."""
        name = hook_name if hook_name.endswith(".sh") else f"{hook_name}.sh"
        bare = name[:-3]

        file_path = self.root / "hooks" / name
        file_exists = file_path.exists()

        in_security = name in self._security()
        in_efficiency = name in self._efficiency()
        in_settings = name in self._settings()

        checks = [file_exists, in_security, in_efficiency, in_settings]
        score = sum(checks) / len(checks)

        issues: list[str] = []
        fixes: list[str] = []
        if not file_exists:
            issues.append(f"hook file hooks/{name} does not exist")
        if not in_security:
            issues.append("not registered in scripts/set-security-profile.sh")
            fixes.append(f"Add '{name}' to set-security-profile.sh (standard + paranoid)")
        if not in_efficiency:
            issues.append("not registered in scripts/apply-efficiency-profile.sh")
            fixes.append(f"Add '{name}' to apply-efficiency-profile.sh (standard + full)")
        if not in_settings:
            issues.append("not active in current .claude/settings.json")
            fixes.append("Re-run: bash scripts/set-security-profile.sh standard")

        return {
            "name": name,
            "file_exists": file_exists,
            "in_security_profile": in_security,
            "in_efficiency_profile": in_efficiency,
            "in_settings_json": in_settings,
            "wiring_score": score,
            "issues": issues,
            "fix_commands": fixes,
        }

    # ── Lib validation ────────────────────────────────────────────────────────

    def validate_lib(self, lib_name: str) -> dict[str, Any]:
        """Validate a lib module by file name or bare name."""
        name = lib_name if lib_name.endswith(".py") else f"{lib_name}.py"
        bare = name[:-3]

        file_path = self.root / "lib" / name
        file_exists = file_path.exists()

        # Search for imports only in first-party directories (avoids scanning submodules)
        imported_by: list[str] = []
        patterns = [
            re.compile(rf'from\s+lib\.{re.escape(bare)}\s+import'),
            re.compile(rf'import\s+lib\.{re.escape(bare)}'),
            re.compile(rf'from\s+{re.escape(bare)}\s+import'),
            re.compile(rf'import\s+{re.escape(bare)}(?:\s|$)'),
        ]
        _search_dirs = ["lib", "hooks", "tests", "scripts", "skills"]
        for _dir in _search_dirs:
            _search = self.root / _dir
            if not _search.exists():
                continue
            for py_file in _search.rglob("*.py"):
                if py_file == file_path or "__pycache__" in str(py_file):
                    continue
                try:
                    content = py_file.read_text(errors="ignore")
                    if any(p.search(content) for p in patterns):
                        imported_by.append(str(py_file.relative_to(self.root)))
                except OSError:
                    continue

        test_file = self.root / "tests" / "unit" / f"test_{bare}.py"
        has_tests = test_file.exists()

        # Score: file + importers + tests
        score = (
            (1 if file_exists else 0)
            + (1 if imported_by else 0)
            + (1 if has_tests else 0)
        ) / 3

        issues: list[str] = []
        if not file_exists:
            issues.append(f"lib/{name} does not exist")
        if not imported_by:
            issues.append("no other module imports this lib")
        if not has_tests:
            issues.append(f"no unit test file at tests/unit/test_{bare}.py")

        return {
            "name": name,
            "file_exists": file_exists,
            "imported_by": imported_by,
            "has_tests": has_tests,
            "wiring_score": score,
            "issues": issues,
        }

    # ── Rule validation ───────────────────────────────────────────────────────

    def validate_rule(self, rule_name: str) -> dict[str, Any]:
        """Validate a rule by file name."""
        name = rule_name if rule_name.endswith(".md") else f"{rule_name}.md"

        file_path = self.root / "rules" / name
        file_exists = file_path.exists()

        in_compact = name.replace(".md", "") in self._compact() or name in self._compact()
        in_excluded = name in self._get_excluded_rules()
        in_claude = (self.root / ".claude" / "rules" / name).exists()

        # Excluded by design counts as fully wired
        if in_excluded:
            score = 1.0
        else:
            score = (
                (1 if file_exists else 0)
                + (1 if in_compact else 0)
                + (1 if in_claude else 0)
            ) / 3

        issues: list[str] = []
        if not file_exists:
            issues.append(f"rules/{name} does not exist")
        if not in_excluded and not in_compact:
            issues.append("not referenced in rules/RULES-COMPACT.md")
        if not in_excluded and not in_claude:
            issues.append("not symlinked in .claude/rules/")

        return {
            "name": name,
            "file_exists": file_exists,
            "in_rules_compact": in_compact,
            "in_excluded_rules": in_excluded,
            "in_claude_rules": in_claude,
            "wiring_score": score,
            "issues": issues,
        }

    # ── Bulk validation ───────────────────────────────────────────────────────

    def validate_all_hooks(self) -> list[dict[str, Any]]:
        results = []
        hooks_dir = self.root / "hooks"
        if not hooks_dir.exists():
            return results
        for hook_file in sorted(hooks_dir.glob("*.sh")):
            name = hook_file.name
            if name.startswith("_"):
                continue  # skip internal _lib/ helpers
            results.append(self.validate_hook(name))
        return sorted(results, key=lambda r: r["wiring_score"])

    def validate_all_libs(self) -> list[dict[str, Any]]:
        results = []
        lib_dir = self.root / "lib"
        if not lib_dir.exists():
            return results
        for lib_file in sorted(lib_dir.glob("*.py")):
            if lib_file.name.startswith("_"):
                continue
            results.append(self.validate_lib(lib_file.name))
        return sorted(results, key=lambda r: r["wiring_score"])

    def validate_all_rules(self) -> list[dict[str, Any]]:
        results = []
        rules_dir = self.root / "rules"
        if not rules_dir.exists():
            return results
        for rule_file in sorted(rules_dir.glob("*.md")):
            results.append(self.validate_rule(rule_file.name))
        return sorted(results, key=lambda r: r["wiring_score"])

    # ── Reporting ─────────────────────────────────────────────────────────────

    def get_unwired_components(self) -> dict[str, Any]:
        hooks = [r for r in self.validate_all_hooks() if r["wiring_score"] < 1.0]
        libs = [r for r in self.validate_all_libs() if r["wiring_score"] < 1.0]
        rules = [r for r in self.validate_all_rules() if r["wiring_score"] < 1.0]
        return {
            "hooks": hooks,
            "libs": libs,
            "rules": rules,
            "total_unwired": len(hooks) + len(libs) + len(rules),
        }

    def format_wiring_report(self) -> str:
        all_hooks = self.validate_all_hooks()
        all_libs = self.validate_all_libs()
        all_rules = self.validate_all_rules()

        def _section(label: str, items: list[dict], key: str = "name") -> str:
            total = len(items)
            wired = sum(1 for r in items if r["wiring_score"] >= 1.0)
            pct = (wired / total * 100) if total else 0
            lines = [f"{label}: {wired}/{total} fully wired ({pct:.1f}%)"]
            for r in items:
                if r["wiring_score"] < 1.0:
                    lines.append(f"  \u274c {r[key]} \u2014 " + "; ".join(r["issues"]))
            return "\n".join(lines)

        return "\n".join([
            "=== WIRING REPORT ===",
            _section("HOOKS", all_hooks),
            _section("LIBS", all_libs),
            _section("RULES", all_rules),
        ])

    def format_fix_commands(self) -> str:
        lines = ["=== FIX COMMANDS ==="]
        for r in self.validate_all_hooks():
            for fix in r.get("fix_commands", []):
                lines.append(f"# {r['name']}: {fix}")
        lines.append("bash scripts/set-security-profile.sh standard  # reload active settings")
        return "\n".join(lines)

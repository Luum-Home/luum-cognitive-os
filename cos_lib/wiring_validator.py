# SCOPE: os-only
"""WiringValidator — detects components that exist but are never registered/used.

Validates three component types:
  - Hooks: structural triage — file exists, named in set-security-profile.sh,
    declared in the canonical registry, and present in the active settings driver.

    CAVEAT, MEASURED 2026-08-19: cognitive-os.yaml > harness.hooks is the
    canonical DECLARATION (ADR-064) but it is NOT what registers a hook with
    Claude Code. scripts/_lib/settings-driver-claude-code.sh holds that registry
    as shell literals and never reads the yaml, so `in_efficiency_profile` is
    True for hooks that Claude Code never runs — hooks/publication-safety.sh is
    the live example. Do NOT read `wiring_score` as "this hook runs".
    The authoritative orphan gate is cos_lib/hook_registration_audit.py
    (scripts/audit_hook_registration.py); this validator stays the per-file
    triage across hooks, libs and rules.
  - Libs:  must be imported by at least one other file
  - Rules: must appear in RULES-COMPACT.md or EXCLUDED_RULES in self-install.sh
"""

from __future__ import annotations

import json
import re
import os
from pathlib import Path
from typing import Any


class WiringValidator:
    """Validates that Cognitive OS agentic primitives are wired, not just existing."""

    def __init__(self, project_root: str = ".") -> None:
        self.root = Path(project_root).resolve()
        self._security_content: str | None = None
        self._efficiency_content: str | None = None
        self._registry_hooks_set: set[str] | None = None
        self._settings_content: str | None = None
        self._settings_path: Path | None = None
        self._compact_content: str | None = None
        self._excluded_rules: set[str] | None = None
        self._python_contents: list[tuple[Path, str]] | None = None

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

    def _registry_hooks(self) -> set[str]:
        """Return hook basenames DECLARED in ``cognitive-os.yaml > harness.hooks``.

        Declared, not registered, and la distincion es todo el punto. Este
        docstring decia que el yaml era el registro y que "un hook registrado
        solo en el YAML debe contar igual como cableado" — lo contrario de lo
        que se midio el 2026-08-19, y contradecia el caveat del docstring de
        este mismo modulo unas lineas mas arriba.

        El driver de Claude Code (``scripts/_lib/settings-driver-claude-code.sh``)
        tiene su registro como literales de shell y nunca lee este yaml, asi que
        un hook presente aca y ausente alla existe y no corre nunca. El caso
        vivo esta declarado con ``scope: both``, sin opt-out, y con cero
        disparos en telemetria viva y rotada.

        O sea que esta senal contesta "fue declarado", y no puede leerse como
        "va a disparar". Para la segunda pregunta la autoridad es
        ``scripts/audit_hook_registration.py``, que cruza las superficies que
        deciden alcanzabilidad contra la telemetria. Mantenerlas separadas es
        deliberado: dos instrumentos contestando la misma pregunta con criterios
        distintos es como este repo termino con dos censos de kill-switches que
        no coincidian.

        Un regex por linea sobre las entradas ``script:`` evita una dependencia
        dura de YAML y aguanta el archivo de configuracion grande.
        """
        if self._registry_hooks_set is None:
            names: set[str] = set()
            for cand in (
                self.root / ".cognitive-os" / "cognitive-os.yaml",
                self.root / "cognitive-os.yaml",
            ):
                if not cand.exists():
                    continue
                text = cand.read_text(errors="ignore")
                for m in re.finditer(r"script:\s*(\S+\.sh)", text):
                    names.add(Path(m.group(1)).name)
                if names:
                    break
            self._registry_hooks_set = names
        return self._registry_hooks_set

    @staticmethod
    def _hook_command_text(path: Path) -> str:
        """Return the JSON string values that can name a hook, minus permissions.

        `.claude/settings.local.json` is gitignored, machine-specific, and holds
        a `permissions` allowlist and no hooks block at all. Reading it as the
        settings driver made `in_settings_json` a substring hit against permission
        strings — 36 accidental Trues on this tree, and a signal that measures
        something different in a clean clone or in CI. A candidate that yields no
        hook-command text is skipped rather than believed.
        """
        try:
            data = json.loads(path.read_text())
        except (OSError, ValueError):
            return ""
        if isinstance(data, dict):
            data = {k: v for k, v in data.items() if k != "permissions"}
        chunks: list[str] = []

        def walk(node: Any) -> None:
            if isinstance(node, str):
                chunks.append(node)
            elif isinstance(node, dict):
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        walk(data)
        return "\n".join(chunks)

    def _settings(self) -> str:
        if self._settings_content is None:
            self._settings_path = None
            fallback: tuple[Path, str] | None = None
            for p in self._settings_candidates():
                if not p.exists():
                    continue
                text = self._hook_command_text(p)
                if ".sh" in text:
                    self._settings_path = p
                    self._settings_content = text
                    break
                if fallback is None:
                    fallback = (p, text)
            if self._settings_content is None and fallback is not None:
                self._settings_path, self._settings_content = fallback
            if self._settings_content is None:
                self._settings_content = ""
        return self._settings_content

    def _settings_candidates(self) -> tuple[Path, ...]:
        """Return settings driver candidates in the current harness order."""
        claude_local = self.root / ".claude" / "settings.local.json"
        claude = self.root / ".claude" / "settings.json"
        codex = self.root / ".codex" / "hooks.json"

        explicit = os.environ.get("COGNITIVE_OS_HARNESS", "").strip().lower()
        if explicit == "codex":
            return (codex, claude_local, claude)
        if explicit == "claude":
            return (claude, claude_local, codex)

        codex_hints = any(
            os.environ.get(name, "")
            for name in ("CODEX_PROJECT_DIR", "CODEX_SESSION_ID", "CODEX_HOME")
        )
        if codex_hints:
            return (codex, claude_local, claude)

        return (claude, claude_local, codex)

    def _settings_label(self) -> str:
        """Return a human-readable label for the active settings driver."""
        self._settings()
        if self._settings_path is None:
            return "current settings driver"
        return self._settings_path.relative_to(self.root).as_posix()

    def _compact(self) -> str:
        if self._compact_content is None:
            p = self.root / "rules" / "RULES-COMPACT.md"
            self._compact_content = p.read_text() if p.exists() else ""
        return self._compact_content


    def _first_party_python_contents(self) -> list[tuple[Path, str]]:
        """Return cached first-party Python file contents for import scans.

        Lib wiring validates every lib module. Re-reading every Python file for
        every lib scales as modules × files and can exceed the suite timeout in
        broad serial runs. Cache file contents once per validator instance while
        keeping validation semantics identical.
        """
        if self._python_contents is not None:
            return self._python_contents

        contents: list[tuple[Path, str]] = []
        for search_dir in ("cos_lib", "hooks", "tests", "scripts", "skills"):
            root = self.root / search_dir
            if not root.exists():
                continue
            for py_file in root.rglob("*.py"):
                if "__pycache__" in py_file.parts:
                    continue
                try:
                    contents.append((py_file, py_file.read_text(errors="ignore")))
                except OSError:
                    continue
        self._python_contents = contents
        return contents

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
        file_path = self.root / "hooks" / name
        file_exists = file_path.exists()

        in_security = name in self._security()
        # ADR-064: canonical registry first, profile-script text as fallback.
        in_efficiency = name in self._registry_hooks() or name in self._efficiency()
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
            issues.append(
                "not declared in cognitive-os.yaml > harness.hooks "
                "(canonical declaration, ADR-064) nor in the apply-efficiency-profile.sh baseline"
            )
            fixes.append(
                f"Declare '{name}' in cognitive-os.yaml > harness.hooks AND add it by hand "
                "to scripts/_lib/settings-driver-claude-code.sh -- that driver does not read "
                "the yaml (ADR-064 verification note 2026-08-20) -- then run: "
                "bash scripts/apply-efficiency-profile.sh"
            )
        if not in_settings:
            issues.append(f"not active in current {self._settings_label()}")
            fixes.append("Re-run the appropriate harness settings generation flow for the active driver")

        return {
            "name": name,
            "file_exists": file_exists,
            "in_security_profile": in_security,
            "in_efficiency_profile": in_efficiency,
            "in_settings_json": in_settings,
            "settings_driver": self._settings_label(),
            "wiring_score": score,
            "issues": issues,
            "fix_commands": fixes,
        }

    # ── Lib validation ────────────────────────────────────────────────────────

    def validate_lib(self, lib_name: str) -> dict[str, Any]:
        """Validate a lib module by file name or bare name."""
        name = lib_name if lib_name.endswith(".py") else f"{lib_name}.py"
        bare = name[:-3]

        file_path = self.root / "cos_lib" / name
        if not file_path.exists():
            legacy = self.root / "lib" / name
            if legacy.exists():
                file_path = legacy
        file_exists = file_path.exists()

        # Search for imports only in first-party directories (avoids scanning submodules)
        imported_by: list[str] = []
        patterns = [
            re.compile(rf'from\s+cos_lib\.{re.escape(bare)}\s+import'),
            re.compile(rf'import\s+cos_lib\.{re.escape(bare)}'),
            re.compile(rf'from\s+lib\.{re.escape(bare)}\s+import'),
            re.compile(rf'import\s+lib\.{re.escape(bare)}'),
            re.compile(rf'from\s+{re.escape(bare)}\s+import'),
            re.compile(rf'import\s+{re.escape(bare)}(?:\s|$)'),
        ]
        for py_file, content in self._first_party_python_contents():
            if py_file == file_path:
                continue
            if any(pattern.search(content) for pattern in patterns):
                imported_by.append(str(py_file.relative_to(self.root)))

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
        in_canonical = (self.root / ".cognitive-os" / "rules" / "cos" / name).exists()
        in_claude = any(
            candidate.exists()
            for candidate in (
                self.root / ".claude" / "rules" / "cos" / name,
                self.root / ".claude" / "rules" / name,
            )
        )
        in_runtime_surface = in_canonical or in_claude

        # Excluded by design counts as fully wired
        if in_excluded:
            score = 1.0
        else:
            score = (
                (1 if file_exists else 0)
                + (1 if in_compact else 0)
                + (1 if in_runtime_surface else 0)
            ) / 3

        issues: list[str] = []
        if not file_exists:
            issues.append(f"rules/{name} does not exist")
        if not in_excluded and not in_compact:
            issues.append("not referenced in rules/RULES-COMPACT.md")
        if not in_excluded and not in_runtime_surface:
            issues.append("not present in canonical or driver rule surfaces")

        return {
            "name": name,
            "file_exists": file_exists,
            "in_rules_compact": in_compact,
            "in_excluded_rules": in_excluded,
            "in_canonical_rules": in_canonical,
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
        lib_dir = self.root / "cos_lib"
        if not lib_dir.exists():
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

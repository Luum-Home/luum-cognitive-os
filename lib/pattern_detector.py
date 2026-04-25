"""Pattern Detector — detects systemic problems in the Cognitive OS codebase.

Identifies dead metadata, broken chains, phantom entries, and structural tests
that indicate code-level rot. Symlink-aware: always resolves symlinks before
classifying anything as missing.

Usage:
    from lib.pattern_detector import PatternDetector

    detector = PatternDetector()
    issues = detector.run_all("/path/to/project")
    for issue in issues:
        print(f"[{issue.severity}] {issue.type}: {issue.description}")
"""
# SCOPE: os-only

import ast
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class DetectedPattern:
    """A systemic problem detected in the codebase."""

    type: str  # 'dead_metadata', 'broken_chain', 'phantom_entry', 'structural_test'
    severity: str  # 'critical', 'warning', 'info'
    component: str  # file path or component name
    description: str
    evidence: str  # what was checked and what was found
    suggestion: str  # how to fix it


def _resolve(path: str) -> str:
    """Resolve symlinks to canonical path."""
    return os.path.realpath(path)


def _file_exists(path: str) -> bool:
    """Check if file exists after resolving symlinks."""
    resolved = _resolve(path)
    return os.path.isfile(resolved)


def _grep_codebase(
    project_dir: str,
    pattern: str,
    extensions: Optional[List[str]] = None,
    exclude_dirs: Optional[List[str]] = None,
) -> List[str]:
    """Search codebase for a pattern, return matching lines.

    Uses subprocess grep for performance on large codebases.
    Falls back to pure-Python scan if grep is unavailable.
    """
    if extensions is None:
        extensions = [".py", ".sh", ".yaml", ".yml", ".json"]
    if exclude_dirs is None:
        exclude_dirs = [
            "__pycache__",
            ".git",
            "node_modules",
            ".cognitive-os",
            ".claude",
        ]

    include_args = []
    for ext in extensions:
        include_args.extend(["--include", f"*{ext}"])
    exclude_args = []
    for d in exclude_dirs:
        exclude_args.extend(["--exclude-dir", d])

    try:
        result = subprocess.run(
            ["grep", "-r", "-l", "--no-messages"]
            + include_args
            + exclude_args
            + [pattern, project_dir],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        # Fallback: pure Python scan
        matches = []
        for root, dirs, files in os.walk(project_dir):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for fname in files:
                if not any(fname.endswith(ext) for ext in extensions):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        if re.search(pattern, f.read()):
                            matches.append(fpath)
                except (OSError, PermissionError):
                    continue
        return matches


class PatternDetector:
    """Detects systemic problems in the Cognitive OS codebase."""

    # -----------------------------------------------------------------------
    # 1. Dead Metadata
    # -----------------------------------------------------------------------
    def detect_dead_metadata(self, project_dir: str) -> List[DetectedPattern]:
        """Find metadata fields written to SKILL.md frontmatter but never read by code."""
        patterns = []
        skills_dir = os.path.join(project_dir, "skills")
        if not os.path.isdir(skills_dir):
            return patterns

        # Collect all frontmatter keys used across SKILL.md files
        frontmatter_keys = self._collect_frontmatter_keys(skills_dir)

        # For each key, check if any code in lib/, hooks/, or skills/ reads it
        for key, sources in frontmatter_keys.items():
            # Skip universal keys that are always meaningful
            if key in ("name", "description", "version"):
                continue

            # Search for code that reads this field
            # Look for YAML parsing patterns, dict access, or grep-for-key
            search_patterns = [
                re.escape(key),  # direct reference
            ]
            found = False
            for sp in search_patterns:
                matches = _grep_codebase(
                    project_dir, sp, extensions=[".py", ".sh"]
                )
                # Filter out the SKILL.md files themselves
                code_matches = [
                    m
                    for m in matches
                    if not m.endswith(".md")
                    and not m.endswith("pattern_detector.py")
                ]
                if code_matches:
                    found = True
                    break

            if not found:
                sample_files = sources[:3]
                patterns.append(
                    DetectedPattern(
                        type="dead_metadata",
                        severity="warning",
                        component=f"frontmatter.{key}",
                        description=(
                            f"Frontmatter field '{key}' is defined in "
                            f"{len(sources)} SKILL.md file(s) but no code reads it."
                        ),
                        evidence=(
                            f"Defined in: {', '.join(sample_files)}. "
                            f"Searched lib/, hooks/ for references — none found."
                        ),
                        suggestion=(
                            f"Either write code that uses '{key}' or remove it "
                            f"from the affected SKILL.md files."
                        ),
                    )
                )

        return patterns

    def _collect_frontmatter_keys(self, skills_dir: str) -> Dict[str, List[str]]:
        """Parse YAML frontmatter from SKILL.md files, return {key: [file_paths]}."""
        keys: Dict[str, List[str]] = {}
        for root, _dirs, files in os.walk(skills_dir):
            for fname in files:
                if fname != "SKILL.md":
                    continue
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        content = f.read()
                except (OSError, PermissionError):
                    continue

                fm_keys = self._parse_frontmatter_keys(content)
                rel_path = os.path.relpath(fpath, skills_dir)
                for k in fm_keys:
                    keys.setdefault(k, []).append(rel_path)
        return keys

    @staticmethod
    def _parse_frontmatter_keys(content: str) -> List[str]:
        """Extract top-level keys from YAML frontmatter delimited by ---.

        Handles SKILL.md files that begin with an HTML comment before the
        opening ``---`` delimiter (e.g. ``<!-- SCOPE: both -->``).  Uses
        ``re.MULTILINE`` so ``^---`` matches the start of any line, not only
        the very start of the string.
        """
        import re as _re
        m = _re.search(r"^---\s*\n(.*?)\n^---", content, _re.DOTALL | _re.MULTILINE)
        if not m:
            return []
        block = m.group(1)
        found_keys = []
        for line in block.split("\n"):
            if ":" in line and not line.startswith(" ") and not line.startswith("\t"):
                key = line.split(":", 1)[0].strip()
                if key and not key.startswith("#"):
                    found_keys.append(key)
        return found_keys

    # -----------------------------------------------------------------------
    # 2. Broken Chains
    # -----------------------------------------------------------------------
    def detect_broken_chains(self, project_dir: str) -> List[DetectedPattern]:
        """Find imports/references to files that don't exist (symlink-aware)."""
        patterns = []
        patterns.extend(self._check_python_imports(project_dir))
        patterns.extend(self._check_hook_references(project_dir))
        return patterns

    def _check_python_imports(self, project_dir: str) -> List[DetectedPattern]:
        """Check Python imports in lib/*.py for broken references."""
        patterns = []
        lib_dir = os.path.join(project_dir, "lib")
        if not os.path.isdir(lib_dir):
            return patterns

        for fname in os.listdir(lib_dir):
            if not fname.endswith(".py") or fname.startswith("__"):
                continue
            fpath = os.path.join(lib_dir, fname)
            if not _file_exists(fpath):
                continue
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    source = f.read()
            except (OSError, PermissionError):
                continue

            try:
                tree = ast.parse(source, filename=fname)
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        broken = self._is_broken_import(
                            alias.name, project_dir, fpath
                        )
                        if broken:
                            patterns.append(broken)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        broken = self._is_broken_import(
                            node.module, project_dir, fpath
                        )
                        if broken:
                            patterns.append(broken)

        return patterns

    def _is_broken_import(
        self, module_name: str, project_dir: str, source_file: str
    ) -> Optional[DetectedPattern]:
        """Check if a module import resolves to an existing file."""
        # Only check local imports (lib.*, hooks.*, etc.)
        parts = module_name.split(".")
        if parts[0] not in ("lib", "hooks", "skills"):
            return None

        # Convert module path to file path
        rel_path = os.path.join(*parts) + ".py"
        abs_path = os.path.join(project_dir, rel_path)

        # Also check for package (directory with __init__.py)
        pkg_path = os.path.join(project_dir, *parts, "__init__.py")

        if _file_exists(abs_path) or _file_exists(pkg_path):
            return None

        rel_source = os.path.relpath(source_file, project_dir)
        return DetectedPattern(
            type="broken_chain",
            severity="critical",
            component=rel_source,
            description=(
                f"Import '{module_name}' in {rel_source} "
                f"resolves to no existing file."
            ),
            evidence=(
                f"Checked: {rel_path} (resolved: {_resolve(abs_path)}), "
                f"also checked package {os.path.join(*parts, '__init__.py')}. "
                f"Neither exists."
            ),
            suggestion=f"Fix the import or create the missing module '{module_name}'.",
        )

    def _check_hook_references(self, project_dir: str) -> List[DetectedPattern]:
        """Check settings.json hook commands for references to missing files."""
        patterns = []
        settings_path = os.path.join(project_dir, ".claude", "settings.json")
        if not _file_exists(settings_path):
            return patterns

        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                settings = __import__("json").load(f)
        except (OSError, ValueError):
            return patterns

        hooks = settings.get("hooks", {})
        for event_name, event_list in hooks.items():
            if not isinstance(event_list, list):
                continue
            for entry in event_list:
                hook_list = entry.get("hooks", [])
                if not isinstance(hook_list, list):
                    continue
                for hook in hook_list:
                    cmd = hook.get("command", "")
                    broken = self._check_hook_command(
                        cmd, project_dir, event_name
                    )
                    if broken:
                        patterns.append(broken)

        return patterns

    def _check_hook_command(
        self, command: str, project_dir: str, event_name: str
    ) -> Optional[DetectedPattern]:
        """Check if a hook command references an existing script."""
        if not command:
            return None

        # Extract file path from commands like:
        #   bash "$CLAUDE_PROJECT_DIR/hooks/some-hook.sh"
        #   python3 "$CLAUDE_PROJECT_DIR/lib/some_lib.py"
        match = re.search(
            r'\$CLAUDE_PROJECT_DIR["/]*([\w./_-]+)', command
        )
        if not match:
            return None

        rel_path = match.group(1).strip('"').strip("'")
        abs_path = os.path.join(project_dir, rel_path)

        if _file_exists(abs_path):
            return None

        return DetectedPattern(
            type="broken_chain",
            severity="critical",
            component=f"settings.json:hooks.{event_name}",
            description=(
                f"Hook command references '{rel_path}' which does not exist."
            ),
            evidence=(
                f"Command: {command}\n"
                f"Resolved path: {_resolve(abs_path)} — file not found."
            ),
            suggestion=(
                f"Create the missing file '{rel_path}' or remove the hook entry."
            ),
        )

    # -----------------------------------------------------------------------
    # 3. Phantom Entries
    # -----------------------------------------------------------------------
    def detect_phantom_entries(self, project_dir: str) -> List[DetectedPattern]:
        """Find catalog/config entries pointing to non-existent components."""
        patterns = []
        patterns.extend(self._check_catalog_entries(project_dir))
        patterns.extend(self._check_config_flags(project_dir))
        return patterns

    def _check_catalog_entries(self, project_dir: str) -> List[DetectedPattern]:
        """Check CATALOG.md skill entries for missing SKILL.md implementations."""
        patterns = []
        catalog_path = os.path.join(project_dir, "skills", "CATALOG.md")
        if not _file_exists(catalog_path):
            return patterns

        try:
            with open(catalog_path, "r", encoding="utf-8") as f:
                content = f.read()
        except (OSError, PermissionError):
            return patterns

        # Parse table rows: | skill-name | description | /invoke | audience |
        for line in content.split("\n"):
            line = line.strip()
            if not line.startswith("|") or line.startswith("|--") or line.startswith("| Skill"):
                continue
            cols = [c.strip() for c in line.split("|")]
            # cols[0] is empty (before first |), cols[1] is skill name
            if len(cols) < 3:
                continue
            skill_name = cols[1].strip()
            if not skill_name or skill_name == "Skill":
                continue

            skill_md = os.path.join(
                project_dir, "skills", skill_name, "SKILL.md"
            )
            if not _file_exists(skill_md):
                patterns.append(
                    DetectedPattern(
                        type="phantom_entry",
                        severity="warning",
                        component=f"CATALOG.md:{skill_name}",
                        description=(
                            f"Skill '{skill_name}' listed in CATALOG.md "
                            f"but no SKILL.md found."
                        ),
                        evidence=(
                            f"Expected: skills/{skill_name}/SKILL.md "
                            f"(resolved: {_resolve(skill_md)}) — not found."
                        ),
                        suggestion=(
                            f"Create skills/{skill_name}/SKILL.md or "
                            f"remove the entry from CATALOG.md."
                        ),
                    )
                )

        return patterns

    def _check_config_flags(self, project_dir: str) -> List[DetectedPattern]:
        """Check cognitive-os.yaml config keys are actually read by code."""
        patterns = []
        config_path = os.path.join(project_dir, "cognitive-os.yaml")
        if not _file_exists(config_path):
            return patterns

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                content = f.read()
        except (OSError, PermissionError):
            return patterns

        # Extract top-level and second-level YAML keys
        config_keys = self._extract_yaml_keys(content)

        for key_path, line_num in config_keys:
            # Search for references to this key in code
            # Use the leaf key (last segment) for searching
            leaf = key_path.split(".")[-1]
            # Skip very common/generic keys
            if leaf in (
                "name", "type", "description", "version", "port",
                "true", "false", "enabled", "config",
            ):
                continue

            matches = _grep_codebase(
                project_dir, re.escape(leaf), extensions=[".py", ".sh"]
            )
            code_matches = [
                m
                for m in matches
                if not m.endswith(".yaml")
                and not m.endswith(".yml")
                and not m.endswith(".md")
                and "pattern_detector" not in m
            ]
            if not code_matches:
                patterns.append(
                    DetectedPattern(
                        type="phantom_entry",
                        severity="info",
                        component=f"cognitive-os.yaml:{key_path}",
                        description=(
                            f"Config key '{key_path}' in cognitive-os.yaml "
                            f"is not referenced by any code."
                        ),
                        evidence=(
                            f"Searched for '{leaf}' in .py and .sh files — "
                            f"no references found."
                        ),
                        suggestion=(
                            f"Either write code that reads '{key_path}' "
                            f"or remove it from cognitive-os.yaml."
                        ),
                    )
                )

        return patterns

    @staticmethod
    def _extract_yaml_keys(content: str) -> List[Tuple[str, int]]:
        """Extract dotted key paths from YAML content (simple parser).

        Returns list of (dotted_key_path, line_number).
        Only goes 2 levels deep to avoid noise.
        """
        keys = []
        indent_stack: List[Tuple[int, str]] = []

        for line_num, line in enumerate(content.split("\n"), 1):
            stripped = line.strip()
            # Skip comments and empty lines
            if not stripped or stripped.startswith("#"):
                continue
            # Skip YAML document markers
            if stripped in ("---", "..."):
                continue
            # Skip list items
            if stripped.startswith("- "):
                continue

            match = re.match(r"^(\s*)(\w[\w_-]*)\s*:", line)
            if not match:
                continue

            indent = len(match.group(1))
            key = match.group(2)

            # Pop stack to find parent
            while indent_stack and indent_stack[-1][0] >= indent:
                indent_stack.pop()

            indent_stack.append((indent, key))

            # Build dotted path (only up to depth 2 for relevance)
            if len(indent_stack) <= 2:
                path = ".".join(s[1] for s in indent_stack)
                keys.append((path, line_num))

        return keys

    # -----------------------------------------------------------------------
    # 4. Structural Tests
    # -----------------------------------------------------------------------
    def detect_structural_tests(self, project_dir: str) -> List[DetectedPattern]:
        """Find tests that only verify file existence, not behavior."""
        patterns = []
        tests_dir = os.path.join(project_dir, "tests")
        if not os.path.isdir(tests_dir):
            return patterns

        for root, _dirs, files in os.walk(tests_dir):
            for fname in files:
                if not fname.startswith("test_") or not fname.endswith(".py"):
                    continue
                fpath = os.path.join(root, fname)
                result = self._analyze_test_file(fpath, project_dir)
                if result:
                    patterns.append(result)

        return patterns

    def _analyze_test_file(
        self, fpath: str, project_dir: str
    ) -> Optional[DetectedPattern]:
        """Analyze a test file for structural-only assertions."""
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                source = f.read()
        except (OSError, PermissionError):
            return None

        try:
            tree = ast.parse(source, filename=fpath)
        except SyntaxError:
            return None

        total_asserts = 0
        structural_asserts = 0

        # Patterns indicating structural-only tests
        structural_patterns = {
            "exists", "is_file", "is_dir", "isfile", "isdir",
            "path.exists", "os.path.isfile", "os.path.isdir",
        }
        structural_string_patterns = [
            re.compile(r'assert.*\.exists\(\)'),
            re.compile(r'assert.*is_file\(\)'),
            re.compile(r'assert.*is_dir\(\)'),
            re.compile(r'assert.*os\.path\.isfile'),
            re.compile(r'assert.*os\.path\.isdir'),
            re.compile(r'assert.*os\.path\.exists'),
            re.compile(r'assert\s+.*\bin\b.*content', re.IGNORECASE),
        ]

        for node in ast.walk(tree):
            # Count assert statements and assert method calls
            if isinstance(node, ast.Assert):
                total_asserts += 1
                # Check if the assertion is structural
                assertion_code = ast.get_source_segment(source, node)
                if assertion_code and any(
                    p.search(assertion_code) for p in structural_string_patterns
                ):
                    structural_asserts += 1
            elif isinstance(node, ast.Call):
                func = node.func
                func_name = ""
                if isinstance(func, ast.Attribute):
                    func_name = func.attr
                elif isinstance(func, ast.Name):
                    func_name = func.id

                if func_name.startswith("assert"):
                    total_asserts += 1
                    # Check args for structural patterns
                    call_code = ast.get_source_segment(source, node)
                    if call_code and any(
                        p.search(call_code) for p in structural_string_patterns
                    ):
                        structural_asserts += 1

        if total_asserts == 0:
            return None

        # Flag if ALL assertions are structural
        if structural_asserts == total_asserts and total_asserts > 0:
            rel_path = os.path.relpath(fpath, project_dir)
            return DetectedPattern(
                type="structural_test",
                severity="info",
                component=rel_path,
                description=(
                    f"Test file has {total_asserts} assertion(s), "
                    f"all structural (file existence / string-in-content)."
                ),
                evidence=(
                    f"All {total_asserts} assertion(s) use path.exists(), "
                    f"is_file(), or 'in content' checks. "
                    f"No behavioral assertions found."
                ),
                suggestion=(
                    "Add behavioral tests that exercise actual code logic, "
                    "not just file/string existence."
                ),
            )

        return None

    # -----------------------------------------------------------------------
    # Run all detectors
    # -----------------------------------------------------------------------
    def run_all(self, project_dir: str) -> List[DetectedPattern]:
        """Run all detectors and return combined results."""
        results = []
        results.extend(self.detect_dead_metadata(project_dir))
        results.extend(self.detect_broken_chains(project_dir))
        results.extend(self.detect_phantom_entries(project_dir))
        results.extend(self.detect_structural_tests(project_dir))
        return results

    def run_type(self, project_dir: str, detection_type: str) -> List[DetectedPattern]:
        """Run a specific detector by type name."""
        dispatch = {
            "dead-metadata": self.detect_dead_metadata,
            "broken-chains": self.detect_broken_chains,
            "phantoms": self.detect_phantom_entries,
            "structural-tests": self.detect_structural_tests,
        }
        detector = dispatch.get(detection_type)
        if detector is None:
            raise ValueError(
                f"Unknown detection type: {detection_type}. "
                f"Valid types: {', '.join(dispatch.keys())}"
            )
        return detector(project_dir)

    def format_report(self, patterns: List[DetectedPattern]) -> str:
        """Format detected patterns into a human-readable report."""
        if not patterns:
            return "No systemic issues detected."

        lines = [f"Pattern Detector Report — {len(patterns)} issue(s) found\n"]

        # Group by severity
        by_severity = {"critical": [], "warning": [], "info": []}
        for p in patterns:
            by_severity.get(p.severity, by_severity["info"]).append(p)

        for severity in ("critical", "warning", "info"):
            items = by_severity[severity]
            if not items:
                continue
            lines.append(f"\n{'=' * 60}")
            lines.append(f"  {severity.upper()} ({len(items)})")
            lines.append(f"{'=' * 60}")
            for p in items:
                lines.append(f"\n  [{p.type}] {p.component}")
                lines.append(f"  {p.description}")
                lines.append(f"  Evidence: {p.evidence}")
                lines.append(f"  Fix: {p.suggestion}")

        return "\n".join(lines)

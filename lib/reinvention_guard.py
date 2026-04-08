"""
Reinvention Guard — Prevents building features that already exist upstream.

Before creating any new lib/, hook, or skill, this guard checks:
1. Does this already exist in our adopted upstreams (Hermes, Pi)?
2. Did we evaluate a tool that does this and reject it? Why?
3. Is there a pattern we can port instead of building from scratch?

This addresses the root cause: "velocity without integration" —
building fast without checking if someone already solved the problem.

Usage:
    from lib.reinvention_guard import ReinventionGuard

    guard = ReinventionGuard()
    results = guard.check("context compressor with LLM summarization",
                          keywords=["compressor", "compress", "summarize"])
    print(guard.format_report(results))
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

try:
    import yaml  # type: ignore
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False


@dataclass
class ExistingImplementation:
    source: str           # "hermes", "pi", "cos-lib", "registry", "docs"
    file_path: str        # path to the implementation (relative when possible)
    description: str      # what it does / why it matched
    relevance: float      # 0.0–1.0, higher = more keyword matches
    recommendation: str   # "adopt", "adapt", "reference", "ignore"


class ReinventionGuard:
    """Check whether something similar already exists before building it."""

    def __init__(self, project_root: str = ".") -> None:
        # Use resolve() to normalise symlinks (important on macOS /var -> /private/var)
        self.project_root = Path(project_root).resolve()
        self.hermes_path = self.project_root / ".claude/plugins/hermes-agent"
        self.pi_path = self.project_root / ".claude/plugins/pi-mono"
        self.lib_path = self.project_root / "lib"
        self.registry_path = (
            self.project_root / ".cognitive-os/adoption-registry.yaml"
        )
        self.docs_path = self.project_root / "docs"
        self.landscape_doc = self.docs_path / "competitive-landscape.md"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check(
        self,
        description: str,
        keywords: Optional[List[str]] = None,
    ) -> List[ExistingImplementation]:
        """
        Check if something similar already exists before building it.

        Args:
            description: What we're about to build.
            keywords: Search terms (defaults to words from description).

        Returns:
            List of existing implementations, sorted by relevance (descending).
        """
        if keywords is None:
            stop = {"a", "an", "the", "with", "for", "and", "or", "of", "to",
                    "in", "that", "is", "are", "be", "this"}
            keywords = [
                w.lower().strip(".,;:()[]")
                for w in description.split()
                if w.lower().strip(".,;:()[]") not in stop and len(w) > 2
            ]

        results: List[ExistingImplementation] = []

        results.extend(self._search_repo(self.hermes_path, "hermes", keywords))
        results.extend(self._search_repo(self.pi_path, "pi", keywords))
        results.extend(self._search_repo(self.lib_path, "cos-lib", keywords))
        results.extend(self._check_registry(keywords))
        results.extend(self._search_docs(keywords))

        # Sort by relevance descending, deduplicate by file_path
        seen: Dict[str, float] = {}
        deduped: List[ExistingImplementation] = []
        for r in sorted(results, key=lambda x: -x.relevance):
            if r.file_path not in seen:
                seen[r.file_path] = r.relevance
                deduped.append(r)

        return deduped[:10]

    def format_report(self, results: List[ExistingImplementation]) -> str:
        """Format results as a human-readable advisory report."""
        if not results:
            return (
                "REINVENTION CHECK: No existing implementations found. "
                "Safe to build."
            )

        lines = [
            f"REINVENTION CHECK: Found {len(results)} existing implementation(s)!\n",
            "Consider adopting/adapting before building from scratch.\n",
        ]
        for r in results:
            lines.append(f"  [{r.source.upper()}] {r.file_path}")
            lines.append(f"    {r.description}")
            lines.append(
                f"    Relevance: {r.relevance:.2f}  |  Recommendation: {r.recommendation}"
            )
            lines.append("")

        lines.append("Decision ladder: adopt > adapt > reference > build from scratch")
        lines.append("Document your decision in .cognitive-os/adoption-registry.yaml")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _search_repo(
        self,
        repo_path: Path,
        source: str,
        keywords: List[str],
    ) -> List[ExistingImplementation]:
        """Grep for keywords in source files under repo_path."""
        if not repo_path.exists():
            return []

        # Map file_path -> match count
        match_counts: Dict[str, int] = {}

        for keyword in keywords:
            if not keyword or len(keyword) < 3:
                continue
            try:
                proc = subprocess.run(
                    [
                        "grep",
                        "-rl",
                        "--include=*.py",
                        "--include=*.ts",
                        "--include=*.tsx",
                        "--include=*.js",
                        "--include=*.go",
                        "--include=*.sh",
                        "-i",
                        keyword,
                        str(repo_path),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue

            for line in proc.stdout.strip().splitlines():
                fpath = line.strip()
                if not fpath:
                    continue
                # Skip test files to reduce noise
                # Skip test files: match path segment boundaries to avoid
                # false positives from temp dirs like 'test_finds_foo0/'
                fpath_lower = fpath.lower()
                if (
                    "/tests/" in fpath_lower
                    or "/test/" in fpath_lower
                    or fpath_lower.endswith("_test.py")
                    or fpath_lower.endswith("_test.ts")
                    or fpath_lower.endswith("_test.go")
                    or fpath_lower.endswith(".spec.ts")
                    or fpath_lower.endswith(".spec.js")
                    or fpath_lower.endswith(".test.ts")
                    or fpath_lower.endswith(".test.js")
                ):
                    continue
                match_counts[fpath] = match_counts.get(fpath, 0) + 1

        if not match_counts:
            return []

        max_matches = max(match_counts.values())
        results: List[ExistingImplementation] = []
        for fpath, count in match_counts.items():
            relevance = min(count / max(max_matches, 1), 1.0)
            recommendation = self._recommend(source, fpath)
            # Use resolve() on the found path to ensure consistent comparison
            try:
                rel_path = str(Path(fpath).resolve().relative_to(self.project_root))
            except ValueError:
                rel_path = fpath

            results.append(
                ExistingImplementation(
                    source=source,
                    file_path=rel_path,
                    description=f"Matched {count} keyword(s) in {source} source",
                    relevance=relevance,
                    recommendation=recommendation,
                )
            )

        return results

    def _check_registry(
        self, keywords: List[str]
    ) -> List[ExistingImplementation]:
        """Check adoption-registry.yaml for already-adopted items."""
        if not self.registry_path.exists():
            return []

        if not _HAS_YAML:
            return self._grep_file(
                self.registry_path,
                "registry",
                keywords,
                description_prefix="Adoption registry entry",
            )

        try:
            text = self.registry_path.read_text(encoding="utf-8")
            data = yaml.safe_load(text) or {}
        except Exception:
            return []

        results: List[ExistingImplementation] = []
        adoptions = data.get("adoptions") or []
        if not isinstance(adoptions, list):
            return []

        kw_lower = [k.lower() for k in keywords]
        for entry in adoptions:
            if not isinstance(entry, dict):
                continue
            entry_text = " ".join(str(v) for v in entry.values()).lower()
            matches = sum(1 for k in kw_lower if k in entry_text)
            if matches > 0:
                relevance = min(matches / max(len(kw_lower), 1), 1.0)
                aid = entry.get("id", "unknown")
                src_file = entry.get("source_file", "")
                our_file = entry.get("our_file", "")
                description = (
                    f"Already adopted from {entry.get('source', '?')}: "
                    f"{src_file} → {our_file}"
                )
                results.append(
                    ExistingImplementation(
                        source="registry",
                        file_path=f"adoption-registry.yaml#{aid}",
                        description=description,
                        relevance=relevance,
                        recommendation="reference",
                    )
                )

        return results

    def _search_docs(
        self, keywords: List[str]
    ) -> List[ExistingImplementation]:
        """Search competitive-landscape.md and other evaluation docs."""
        results: List[ExistingImplementation] = []

        docs_to_search = [
            self.landscape_doc,
            self.docs_path / "competitive-analysis.md",
            self.docs_path / "competitive-arena.md",
        ]

        for doc in docs_to_search:
            if not doc.exists():
                continue
            results.extend(
                self._grep_file(
                    doc,
                    "docs",
                    keywords,
                    description_prefix=f"Mentioned in {doc.name}",
                )
            )

        return results

    def _grep_file(
        self,
        file_path: Path,
        source: str,
        keywords: List[str],
        description_prefix: str = "Found in",
    ) -> List[ExistingImplementation]:
        """Grep a single file for keywords."""
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace").lower()
        except OSError:
            return []

        kw_lower = [k.lower() for k in keywords if len(k) >= 3]
        matches = sum(1 for k in kw_lower if k in text)
        if matches == 0:
            return []

        relevance = min(matches / max(len(kw_lower), 1), 1.0)
        try:
            rel_path = str(file_path.resolve().relative_to(self.project_root))
        except ValueError:
            rel_path = str(file_path)

        return [
            ExistingImplementation(
                source=source,
                file_path=rel_path,
                description=f"{description_prefix}: {matches} keyword(s) matched",
                relevance=relevance,
                recommendation="reference",
            )
        ]

    def _recommend(self, source: str, file_path: str) -> str:
        """Suggest adopt/adapt/reference based on source and file type."""
        if source in ("registry", "docs"):
            return "reference"
        if source == "cos-lib":
            return "adopt"
        # hermes or pi upstream
        if file_path.endswith((".py", ".ts", ".go")):
            return "adapt"
        return "reference"

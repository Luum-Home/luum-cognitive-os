# scope: both
"""Code Reviewer — Engram-integrated code review with adversarial protocol.

Provides structured code review with severity tiers (BLOCKER/CONCERN/SUGGESTION/QUESTION),
Engram memory integration for past review context, and adversarial review enforcement
(every review MUST produce at least one finding).

Inspired by GGA (Gentleman Guardian Angel) patterns for AI-powered code review
with persistent memory across sessions.

Usage:
    from lib.code_reviewer import CodeReviewer, ReviewReport, ReviewFinding

    reviewer = CodeReviewer(project_root="/path/to/project")
    report = reviewer.review_files(["src/auth.py"], context="Adding JWT support")
    print(reviewer.format_report(report))

Python 3.9+ compatible.
Author: luum
License: MIT
"""

import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class Severity(str, Enum):
    """Review finding severity tiers per adversarial-review.md."""

    BLOCKER = "BLOCKER"
    CONCERN = "CONCERN"
    SUGGESTION = "SUGGESTION"
    QUESTION = "QUESTION"


class ReviewStatus(str, Enum):
    """Overall review status."""

    PASSED = "PASSED"
    FAILED = "FAILED"


@dataclass
class ReviewFinding:
    """A single review finding with severity classification.

    Follows the format from rules/adversarial-review.md:
    - severity: BLOCKER, CONCERN, SUGGESTION, or QUESTION
    - file: path to the affected file
    - line: optional line number
    - what: description of the issue
    - why: why it matters
    - recommendation: suggested fix or action
    """

    severity: str
    file: str
    line: Optional[int]
    what: str
    why: str
    recommendation: str

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "severity": self.severity,
            "file": self.file,
            "line": self.line,
            "what": self.what,
            "why": self.why,
            "recommendation": self.recommendation,
        }


@dataclass
class ReviewReport:
    """Structured review report with findings and context data.

    status is FAILED if any BLOCKER findings exist, PASSED otherwise.
    Per adversarial review protocol, findings list must never be empty.
    """

    status: str
    findings: List[ReviewFinding]
    files_reviewed: int
    engram_context_used: bool = False
    past_review_count: int = 0
    review_dimensions: List[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.review_dimensions:
            self.review_dimensions = [
                "correctness",
                "security",
                "performance",
                "maintainability",
                "test_coverage",
            ]

    @property
    def blocker_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.BLOCKER)

    @property
    def concern_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.CONCERN)

    @property
    def suggestion_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.SUGGESTION)

    @property
    def question_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.QUESTION)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "status": self.status,
            "findings": [f.to_dict() for f in self.findings],
            "files_reviewed": self.files_reviewed,
            "engram_context_used": self.engram_context_used,
            "past_review_count": self.past_review_count,
            "review_dimensions": self.review_dimensions,
            "timestamp": self.timestamp,
            "summary": {
                "blockers": self.blocker_count,
                "concerns": self.concern_count,
                "suggestions": self.suggestion_count,
                "questions": self.question_count,
                "total": len(self.findings),
            },
        }


# --- Static analysis patterns ---

_SECURITY_PATTERNS = [
    (re.compile(r"\bexec\s*\(", re.IGNORECASE), "Use of exec() detected", "security"),
    (re.compile(r"\beval\s*\(", re.IGNORECASE), "Use of eval() detected", "security"),
    (re.compile(r"password\s*=\s*['\"][^'\"]+['\"]", re.IGNORECASE), "Hardcoded password", "security"),
    (re.compile(r"api[_-]?key\s*=\s*['\"][^'\"]+['\"]", re.IGNORECASE), "Hardcoded API key", "security"),
    (re.compile(r"token\s*=\s*['\"][A-Za-z0-9+/=]{20,}['\"]", re.IGNORECASE), "Hardcoded token", "security"),
    (re.compile(r"SECRET|PRIVATE_KEY", re.IGNORECASE), "Potential secret in code", "security"),
    (re.compile(r"subprocess\.call\s*\(.*shell\s*=\s*True", re.IGNORECASE), "Shell injection risk", "security"),
    (re.compile(r"os\.system\s*\(", re.IGNORECASE), "Use of os.system() — prefer subprocess", "security"),
]

_QUALITY_PATTERNS = [
    (re.compile(r"#\s*TODO\b", re.IGNORECASE), "TODO comment found", "maintainability"),
    (re.compile(r"#\s*FIXME\b", re.IGNORECASE), "FIXME comment found", "maintainability"),
    (re.compile(r"#\s*HACK\b", re.IGNORECASE), "HACK comment found", "maintainability"),
    (re.compile(r"#\s*XXX\b", re.IGNORECASE), "XXX comment found", "maintainability"),
    (re.compile(r"except\s*:\s*$", re.MULTILINE), "Bare except clause", "correctness"),
    (re.compile(r"except\s+Exception\s*:\s*\n\s*pass", re.MULTILINE), "Silenced exception", "correctness"),
    (re.compile(r"print\s*\(", re.IGNORECASE), "Print statement (use logging)", "maintainability"),
    (re.compile(r"\.format\s*\(.*\bpassword\b", re.IGNORECASE), "Password in format string", "security"),
]

_PERFORMANCE_PATTERNS = [
    (re.compile(r"time\.sleep\s*\(\s*\d{2,}", re.IGNORECASE), "Long sleep detected", "performance"),
    (re.compile(r"for\s+.*\brange\s*\(\s*\d{6,}", re.IGNORECASE), "Large loop range", "performance"),
    (re.compile(r"\+\s*=\s*.*\bstr\b|\bstring\b.*\+\s*=", re.IGNORECASE), "String concatenation in loop", "performance"),
]


def _extract_service_from_path(file_path: str) -> str:
    """Extract service/module name from file path for engram topic keys."""
    parts = file_path.replace("\\", "/").split("/")
    # Try common patterns: internal/service/, src/service/, packages/service/
    for prefix in ("internal", "src", "packages", "services", "apps", "lib"):
        if prefix in parts:
            idx = parts.index(prefix)
            if idx + 1 < len(parts):
                return parts[idx + 1]
    # Fallback: use first directory component
    if len(parts) > 1:
        return parts[0]
    return "root"


def _get_git_diff_files(project_root: str, staged: bool = False) -> List[str]:
    """Get list of changed files from git."""
    try:
        cmd = ["git", "diff", "--name-only"]
        if staged:
            cmd.append("--cached")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=10,
        )
        if result.returncode == 0:
            return [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return []


def _get_git_diff(project_root: str, base_branch: Optional[str] = None) -> str:
    """Get git diff content."""
    try:
        if base_branch:
            cmd = ["git", "diff", f"{base_branch}...HEAD"]
        else:
            cmd = ["git", "diff"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=30,
        )
        if result.returncode == 0:
            return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return ""


def _detect_base_branch(project_root: str) -> Optional[str]:
    """Auto-detect base branch (main/master/develop)."""
    for candidate in ("main", "master", "develop"):
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--verify", candidate],
                capture_output=True,
                text=True,
                cwd=project_root,
                timeout=5,
            )
            if result.returncode == 0:
                return candidate
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
    return None


def _scan_content(content: str, file_path: str) -> List[ReviewFinding]:
    """Scan file content for known patterns."""
    findings: List[ReviewFinding] = []
    lines = content.split("\n")

    for line_num, line in enumerate(lines, start=1):
        for pattern, message, dimension in _SECURITY_PATTERNS:
            if pattern.search(line):
                severity = Severity.BLOCKER if "hardcoded" in message.lower() else Severity.CONCERN
                findings.append(
                    ReviewFinding(
                        severity=severity,
                        file=file_path,
                        line=line_num,
                        what=message,
                        why=f"Security issue detected in {dimension} dimension",
                        recommendation=f"Review and fix: {message.lower()}",
                    )
                )

        for pattern, message, dimension in _QUALITY_PATTERNS:
            if pattern.search(line):
                findings.append(
                    ReviewFinding(
                        severity=Severity.SUGGESTION if "TODO" in message or "FIXME" in message else Severity.CONCERN,
                        file=file_path,
                        line=line_num,
                        what=message,
                        why=f"Quality issue in {dimension} dimension",
                        recommendation=f"Address: {message.lower()}",
                    )
                )

        for pattern, message, dimension in _PERFORMANCE_PATTERNS:
            if pattern.search(line):
                findings.append(
                    ReviewFinding(
                        severity=Severity.CONCERN,
                        file=file_path,
                        line=line_num,
                        what=message,
                        why=f"Performance concern in {dimension} dimension",
                        recommendation=f"Optimize: {message.lower()}",
                    )
                )

    return findings


def _scan_diff(diff_content: str) -> List[ReviewFinding]:
    """Scan a git diff for patterns (only added lines)."""
    findings: List[ReviewFinding] = []
    current_file = ""
    current_line = 0

    for line in diff_content.split("\n"):
        # Track current file
        if line.startswith("+++ b/"):
            current_file = line[6:]
            continue
        # Track line numbers from hunk headers
        if line.startswith("@@"):
            match = re.search(r"\+(\d+)", line)
            if match:
                current_line = int(match.group(1))
            continue
        # Only scan added lines
        if line.startswith("+") and not line.startswith("+++"):
            added_line = line[1:]
            for pattern, message, dimension in _SECURITY_PATTERNS + _QUALITY_PATTERNS + _PERFORMANCE_PATTERNS:
                if pattern.search(added_line):
                    severity = Severity.BLOCKER if "hardcoded" in message.lower() else Severity.SUGGESTION
                    findings.append(
                        ReviewFinding(
                            severity=severity,
                            file=current_file,
                            line=current_line,
                            what=message,
                            why=f"Found in added line ({dimension} dimension)",
                            recommendation=f"Review: {message.lower()}",
                        )
                    )
            current_line += 1
        elif not line.startswith("-"):
            current_line += 1

    return findings


class CodeReviewer:
    """Code reviewer with Engram memory integration.

    Searches past reviews before reviewing, saves findings after review.
    Enforces adversarial review protocol: at least one finding always.
    """

    def __init__(self, project_root: Optional[str] = None):
        self.project_root = project_root or os.getcwd()

    def review_files(self, files: List[str], context: str = "") -> ReviewReport:
        """Review a list of files. Returns structured report.

        Args:
            files: List of file paths to review (relative to project_root).
            context: Optional context string (e.g., task description).

        Returns:
            ReviewReport with findings, status, and context data.
        """
        all_findings: List[ReviewFinding] = []

        for file_path in files:
            full_path = os.path.join(self.project_root, file_path)
            if not os.path.isfile(full_path):
                all_findings.append(
                    ReviewFinding(
                        severity=Severity.QUESTION,
                        file=file_path,
                        line=None,
                        what="File not found",
                        why="Cannot review a file that does not exist",
                        recommendation="Verify file path is correct",
                    )
                )
                continue

            try:
                with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                all_findings.extend(_scan_content(content, file_path))
            except OSError:
                all_findings.append(
                    ReviewFinding(
                        severity=Severity.QUESTION,
                        file=file_path,
                        line=None,
                        what="Could not read file",
                        why="File read error prevents review",
                        recommendation="Check file permissions",
                    )
                )

        # Adversarial review: MUST have at least one finding
        all_findings = self._enforce_adversarial(all_findings, files)

        status = ReviewStatus.FAILED if any(f.severity == Severity.BLOCKER for f in all_findings) else ReviewStatus.PASSED

        return ReviewReport(
            status=status,
            findings=all_findings,
            files_reviewed=len(files),
        )

    def review_diff(self, diff: str, context: str = "") -> ReviewReport:
        """Review a git diff. Returns structured report.

        Args:
            diff: Git diff content string.
            context: Optional context string.

        Returns:
            ReviewReport with findings from diff analysis.
        """
        if not diff or not diff.strip():
            return ReviewReport(
                status=ReviewStatus.PASSED,
                findings=[
                    ReviewFinding(
                        severity=Severity.QUESTION,
                        file="(no changes)",
                        line=None,
                        what="Empty diff provided",
                        why="No changes to review",
                        recommendation="Verify there are actual changes to review",
                    )
                ],
                files_reviewed=0,
            )

        # Count files in diff
        file_count = diff.count("+++ b/")
        findings = _scan_diff(diff)

        # Adversarial review: MUST have at least one finding
        diff_files = re.findall(r"\+\+\+ b/(.*)", diff)
        findings = self._enforce_adversarial(findings, diff_files)

        status = ReviewStatus.FAILED if any(f.severity == Severity.BLOCKER for f in findings) else ReviewStatus.PASSED

        return ReviewReport(
            status=status,
            findings=findings,
            files_reviewed=file_count,
        )

    def search_past_reviews(self, files: List[str]) -> List[dict]:
        """Search engram for past reviews of these files.

        Returns list of past review context dictionaries.
        This is a data preparation method — actual engram calls are made
        by the skill/orchestrator using mem_search.

        Args:
            files: List of file paths to search reviews for.

        Returns:
            List of search query dicts suitable for engram mem_search.
        """
        queries: List[dict] = []
        services_seen = set()

        for file_path in files:
            service = _extract_service_from_path(file_path)
            if service not in services_seen:
                services_seen.add(service)
                queries.append({
                    "query": f"review/{service}",
                    "type": "review",
                    "service": service,
                    "file": file_path,
                })

        return queries

    def save_review(self, report: ReviewReport, change_name: str = "") -> dict:
        """Prepare review findings for engram persistence.

        Returns a dict suitable for mem_save. The actual save is performed
        by the skill/orchestrator.

        Args:
            report: The ReviewReport to save.
            change_name: Optional change/PR name for topic key.

        Returns:
            Dict with title, content, type, topic_key for mem_save.
        """
        # Determine service from reviewed files
        services = set()
        for finding in report.findings:
            services.add(_extract_service_from_path(finding.file))
        service_str = ", ".join(sorted(services)) if services else "unknown"

        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        topic_key = f"review/{service_str}/{date_str}"
        if change_name:
            topic_key = f"review/{change_name}/{date_str}"

        # Format content
        lines = [
            f"**Status**: {report.status}",
            f"**Files reviewed**: {report.files_reviewed}",
            f"**Findings**: {len(report.findings)} "
            f"({report.blocker_count} blockers, {report.concern_count} concerns, "
            f"{report.suggestion_count} suggestions, {report.question_count} questions)",
            "",
        ]

        for finding in report.findings:
            line_str = f" (line {finding.line})" if finding.line else ""
            lines.append(f"### [{finding.severity}] {finding.what}")
            lines.append(f"**Location**: {finding.file}{line_str}")
            lines.append(f"**Why**: {finding.why}")
            lines.append(f"**Recommendation**: {finding.recommendation}")
            lines.append("")

        return {
            "title": f"Code review: {service_str} ({report.status})",
            "content": "\n".join(lines),
            "type": "review",
            "topic_key": topic_key,
            "scope": "project",
        }

    def get_changed_files(self, staged: bool = False) -> List[str]:
        """Get changed files from git.

        Args:
            staged: If True, get staged files only. Otherwise, all changed.

        Returns:
            List of changed file paths.
        """
        return _get_git_diff_files(self.project_root, staged=staged)

    def get_diff(self, base_branch: Optional[str] = None) -> str:
        """Get git diff content.

        Args:
            base_branch: Compare against this branch. Auto-detects if None.

        Returns:
            Diff content string.
        """
        if base_branch is None:
            base_branch = _detect_base_branch(self.project_root)
        return _get_git_diff(self.project_root, base_branch=base_branch)

    def detect_base_branch(self) -> Optional[str]:
        """Auto-detect the base branch (main/master/develop)."""
        return _detect_base_branch(self.project_root)

    # --- Engram bidirectional integration (GGA-style) ---

    def search_past_reviews_from_engram(
        self,
        files: List[str],
        project: str = "",
        *,
        mem_search_fn: Optional[Callable[..., Any]] = None,
        mem_get_fn: Optional[Callable[..., Any]] = None,
    ) -> List[dict]:
        """Search engram for past reviews of the services touched by *files*.

        This method performs actual engram calls via the provided callables.
        If no callables are supplied, it falls back to returning empty results
        (graceful degradation when engram is unavailable).

        Args:
            files: File paths to extract services from.
            project: Engram project name (e.g. ``"luum-cognitive-os"``).
            mem_search_fn: Callable matching ``mem_search(query, project, limit)``.
                           Must return a list of dicts with at least ``"id"`` keys.
            mem_get_fn: Callable matching ``mem_get_observation(id)`` that returns
                        the full observation dict.

        Returns:
            List of past review context dicts, each containing:
            ``{"service", "topic_key", "title", "content", "id"}``.
        """
        if mem_search_fn is None:
            return []

        results: List[dict] = []
        services_seen: set = set()

        for file_path in files:
            service = _extract_service_from_path(file_path)
            if service in services_seen:
                continue
            services_seen.add(service)

            # Search review/* and bugfix/* topic keys for this service
            for prefix in ("review", "bugfix", "implementation"):
                query = f"{prefix}/{service}"
                try:
                    hits = mem_search_fn(query=query, project=project, limit=5)
                    if not hits:
                        continue
                    # Normalise: hits may be a list of dicts or objects
                    for hit in (hits if isinstance(hits, list) else [hits]):
                        hit_id = hit.get("id") if isinstance(hit, dict) else getattr(hit, "id", None)
                        if hit_id is None:
                            continue
                        # Fetch full content if getter available
                        content = ""
                        title = hit.get("title", "") if isinstance(hit, dict) else getattr(hit, "title", "")
                        if mem_get_fn is not None:
                            try:
                                full = mem_get_fn(id=hit_id)
                                content = (
                                    full.get("content", "")
                                    if isinstance(full, dict)
                                    else getattr(full, "content", "")
                                )
                            except Exception:
                                pass
                        results.append({
                            "service": service,
                            "topic_key": query,
                            "title": title,
                            "content": content,
                            "id": hit_id,
                        })
                except Exception:
                    # Engram unavailable — graceful degradation
                    continue

        return results

    def save_review_to_engram(
        self,
        report: ReviewReport,
        project: str = "",
        service: str = "",
        change_name: str = "",
        *,
        mem_save_fn: Optional[Callable[..., Any]] = None,
    ) -> dict:
        """Save review findings to engram for future reference.

        Performs the actual ``mem_save`` call when *mem_save_fn* is supplied.
        Always returns the prepared payload dict (useful for testing even
        without a live engram connection).

        Args:
            report: The ReviewReport to persist.
            project: Engram project name.
            service: Service name override. Auto-detected from findings if empty.
            change_name: Optional change/PR name for the topic key.
            mem_save_fn: Callable matching ``mem_save(**kwargs)``.

        Returns:
            The payload dict that was (or would be) sent to ``mem_save``.
        """
        payload = self.save_review(report, change_name=change_name)
        payload["project"] = project

        # Override service if explicitly provided
        if service:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            payload["topic_key"] = f"review/{service}/{date_str}"
            if change_name:
                payload["topic_key"] = f"review/{change_name}/{date_str}"
            payload["title"] = f"Code review: {service} ({report.status})"

        if mem_save_fn is not None:
            try:
                mem_save_fn(
                    title=payload["title"],
                    content=payload["content"],
                    type=payload.get("type", "review"),
                    topic_key=payload["topic_key"],
                    scope=payload.get("scope", "project"),
                    project=project,
                )
            except Exception:
                # Engram unavailable — payload is still returned
                pass

        return payload

    def review_with_engram(
        self,
        files: List[str],
        project: str = "",
        context: str = "",
        change_name: str = "",
        *,
        mem_search_fn: Optional[Callable[..., Any]] = None,
        mem_get_fn: Optional[Callable[..., Any]] = None,
        mem_save_fn: Optional[Callable[..., Any]] = None,
    ) -> ReviewReport:
        """Full review lifecycle: search engram -> review -> save to engram.

        Convenience method that orchestrates the bidirectional flow.

        Returns:
            ReviewReport (with ``engram_context_used`` and ``past_review_count``
            populated when engram was available).
        """
        # 1. Pre-review: search engram for past context
        past_reviews = self.search_past_reviews_from_engram(
            files, project=project, mem_search_fn=mem_search_fn, mem_get_fn=mem_get_fn,
        )

        # 2. Review files (static analysis)
        report = self.review_files(files, context=context)

        # 3. Enrich report with engram metadata
        if past_reviews:
            report.engram_context_used = True
            report.past_review_count = len(past_reviews)

        # 4. Post-review: save findings to engram
        if mem_save_fn is not None:
            services = {_extract_service_from_path(f) for f in files}
            service_str = ", ".join(sorted(services)) if services else ""
            self.save_review_to_engram(
                report,
                project=project,
                service=service_str,
                change_name=change_name,
                mem_save_fn=mem_save_fn,
            )

        return report

    @staticmethod
    def format_report(report: ReviewReport) -> str:
        """Format a ReviewReport as a human-readable markdown string."""
        lines = [
            f"# Code Review Report",
            "",
            f"**Status**: {report.status}",
            f"**Files reviewed**: {report.files_reviewed}",
            f"**Engram context used**: {'Yes' if report.engram_context_used else 'No'}",
            f"**Findings**: {len(report.findings)}",
            f"  - Blockers: {report.blocker_count}",
            f"  - Concerns: {report.concern_count}",
            f"  - Suggestions: {report.suggestion_count}",
            f"  - Questions: {report.question_count}",
            "",
            "---",
            "",
        ]

        for i, finding in enumerate(report.findings, 1):
            line_str = f" (line {finding.line})" if finding.line else ""
            lines.append(f"### {i}. [{finding.severity}] {finding.what}")
            lines.append("")
            lines.append(f"**Location**: `{finding.file}`{line_str}")
            lines.append(f"**What**: {finding.what}")
            lines.append(f"**Why**: {finding.why}")
            lines.append(f"**Recommendation**: {finding.recommendation}")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _enforce_adversarial(
        findings: List[ReviewFinding], files: List[str]
    ) -> List[ReviewFinding]:
        """Enforce adversarial review protocol: at least one finding.

        Per rules/adversarial-review.md, every review MUST produce at least
        one finding. If no issues found, add a SUGGESTION.
        """
        if findings:
            return findings

        # Generate a minimal suggestion if no findings exist
        file_str = files[0] if files else "(reviewed files)"
        return [
            ReviewFinding(
                severity=Severity.SUGGESTION,
                file=file_str,
                line=None,
                what="Consider adding or improving test coverage",
                why="No issues found in static analysis; manual review recommended for logic correctness",
                recommendation="Verify edge cases and error handling paths with additional tests",
            )
        ]


# --- Module-level convenience functions ---


def review_files(files: List[str], project_root: Optional[str] = None, context: str = "") -> ReviewReport:
    """Convenience function: review files and return report."""
    reviewer = CodeReviewer(project_root=project_root)
    return reviewer.review_files(files, context=context)


def review_diff(diff: str, project_root: Optional[str] = None, context: str = "") -> ReviewReport:
    """Convenience function: review a diff and return report."""
    reviewer = CodeReviewer(project_root=project_root)
    return reviewer.review_diff(diff, context=context)


def format_report(report: ReviewReport) -> str:
    """Convenience function: format a report as markdown."""
    return CodeReviewer.format_report(report)

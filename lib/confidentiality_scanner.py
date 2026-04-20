# SCOPE: both
"""Confidentiality scanner — detects IP leaks in generated output.

When an AI agent reads from one project and writes docs for another, it must
not mention the source project. This module scans text for paths, attribution
phrases, repo URLs, and protected terms that would constitute a confidentiality
violation.

Usage::

    from lib.confidentiality_scanner import load_protected_terms, scan_text, scan_file

    terms = load_protected_terms(".cognitive-os/confidentiality.yaml")
    violations = scan_text(text, current_project_dir="/Users/me/Projects/my-project", terms=terms)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Violation:
    """A single confidentiality violation found in text.

    Attributes:
        line_number: 1-based line number; 0 when line number is not available
                     (e.g. when calling scan_text directly).
        matched_text: The exact substring that triggered the violation.
        pattern_type: One of: ``external_path``, ``attribution_phrase``,
                      ``repo_url``, ``protected_term``.
        severity: ``high`` for paths/repos/protected terms; ``medium`` for
                  attribution phrases.
    """

    line_number: int
    matched_text: str
    pattern_type: str
    severity: str


@dataclass
class ProtectedTerms:
    """Collection of terms that must not appear in generated output.

    Attributes:
        project_names: Internal project identifiers (e.g. ``"project-alpha"``).
        client_names:  Client identifiers (e.g. ``"acme-corp"``).
        repo_urls:     Full repository slugs (e.g. ``"org/repo-privado"``).
        org_names:     GitHub / GitLab organisation names (e.g. ``"luum"``).
    """

    project_names: List[str] = field(default_factory=list)
    client_names: List[str] = field(default_factory=list)
    repo_urls: List[str] = field(default_factory=list)
    org_names: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Compiled regex patterns (module-level for performance)
# ---------------------------------------------------------------------------

# Matches any /Users/<user>/Projects/<project> path fragment.
_EXTERNAL_PATH_RE = re.compile(r"/Users/[^/\s]+/Projects/[^/\s\"']+")

# Attribution phrases in English.
_EN_ATTRIBUTION = (
    r"(?:based on|adapted from|inspired by|taken from|copied from"
    r"|extracted from|reused from|ported from)"
)

# Attribution phrases in Spanish.
_ES_ATTRIBUTION = (
    r"(?:basado en|basada en|extraído de|extraída de|modelo tomado de"
    r"|tomado de|tomada de|copiado de|copiada de|adaptado de|adaptada de"
    r"|reutilizado de|reutilizada de|inspirado en|inspirada en)"
)

_ATTRIBUTION_RE = re.compile(
    rf"(?:{_EN_ATTRIBUTION}|{_ES_ATTRIBUTION})",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_protected_terms(config_path: str = ".cognitive-os/confidentiality.yaml") -> ProtectedTerms:
    """Load protected terms from a YAML configuration file.

    Returns an empty :class:`ProtectedTerms` instance when the file does not
    exist or cannot be parsed, so callers can rely on this function without
    error handling.

    Args:
        config_path: Path to the YAML configuration file.

    Returns:
        A :class:`ProtectedTerms` populated from the file, or an empty one on
        any failure.
    """
    path = Path(config_path)
    if not path.exists():
        return ProtectedTerms()

    if yaml is None:
        # PyYAML not available — return empty terms rather than crashing.
        return ProtectedTerms()

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return ProtectedTerms()

    return ProtectedTerms(
        project_names=list(raw.get("project_names", []) or []),
        client_names=list(raw.get("client_names", []) or []),
        repo_urls=list(raw.get("repo_urls", []) or []),
        org_names=list(raw.get("org_names", []) or []),
    )


def scan_text(
    text: str,
    current_project_dir: str = "",
    terms: Optional[ProtectedTerms] = None,
) -> List[Violation]:
    """Scan a block of text for confidentiality violations.

    All returned :class:`Violation` objects have ``line_number=0`` because
    this function operates on a pre-joined text blob. Use :func:`scan_file` to
    get per-line numbers.

    Args:
        text: The text to scan.
        current_project_dir: Absolute path of the project being documented.
            Paths that start with this prefix are *not* flagged as external.
        terms: Protected terms to match against. Defaults to empty terms (only
            structural patterns such as external paths are still detected).

    Returns:
        A list of :class:`Violation` objects, possibly empty.
    """
    if terms is None:
        terms = ProtectedTerms()

    violations: List[Violation] = []

    # -- 1. External filesystem paths -----------------------------------------
    for match in _EXTERNAL_PATH_RE.finditer(text):
        matched = match.group(0)
        # Strip trailing punctuation that may have been captured.
        matched = matched.rstrip(".,;:)'\"")
        if current_project_dir:
            # Normalise so "/Users/x/Projects/p" matches "/Users/x/Projects/p/"
            norm_current = current_project_dir.rstrip("/")
            norm_matched = matched.rstrip("/")
            if norm_matched == norm_current or norm_matched.startswith(norm_current + "/"):
                continue  # Same project — allowed.
        violations.append(
            Violation(
                line_number=0,
                matched_text=matched,
                pattern_type="external_path",
                severity="high",
            )
        )

    # -- 2. Attribution phrases -----------------------------------------------
    for attr_match in _ATTRIBUTION_RE.finditer(text):
        # Look at the text *after* the attribution phrase for a protected term
        # or a filesystem path.
        rest = text[attr_match.end() :]
        # Grab up to the next 120 characters (one or two sentences).
        snippet = rest[:120]

        triggered = False

        # Check for any protected term in the trailing snippet.
        all_protected = list(terms.project_names) + list(terms.client_names)
        for pt in all_protected:
            if pt and pt.lower() in snippet.lower():
                violations.append(
                    Violation(
                        line_number=0,
                        matched_text=f"{attr_match.group(0)} … {pt}",
                        pattern_type="attribution_phrase",
                        severity="medium",
                    )
                )
                triggered = True
                break

        if not triggered:
            # Check for an external path in the trailing snippet.
            path_match = _EXTERNAL_PATH_RE.search(snippet)
            if path_match:
                matched_path = path_match.group(0).rstrip(".,;:)'\"")
                norm_current = current_project_dir.rstrip("/")
                norm_path = matched_path.rstrip("/")
                is_same = bool(
                    current_project_dir
                    and (
                        norm_path == norm_current
                        or norm_path.startswith(norm_current + "/")
                    )
                )
                if not is_same:
                    violations.append(
                        Violation(
                            line_number=0,
                            matched_text=f"{attr_match.group(0)} … {matched_path}",
                            pattern_type="attribution_phrase",
                            severity="medium",
                        )
                    )

    # -- 3. Repository URLs ---------------------------------------------------
    if terms.org_names:
        for org in terms.org_names:
            if not org:
                continue
            # Match github.com/<org>/<repo> or gitlab.com/<org>/<repo>
            repo_url_re = re.compile(
                rf"(?:github\.com|gitlab\.com)/{re.escape(org)}/[^\s\"'>\])]+"
            )
            for match in repo_url_re.finditer(text):
                violations.append(
                    Violation(
                        line_number=0,
                        matched_text=match.group(0).rstrip(".,;:)'\""),
                        pattern_type="repo_url",
                        severity="high",
                    )
                )

    # -- 4. Direct protected term references ----------------------------------
    all_direct = list(terms.project_names) + list(terms.client_names)
    for term in all_direct:
        if not term:
            continue
        # Use word-boundary matching; terms may contain hyphens.
        pattern = re.compile(
            rf"(?<![/\w]){re.escape(term)}(?![/\w-])",
            re.IGNORECASE,
        )
        for match in pattern.finditer(text):
            violations.append(
                Violation(
                    line_number=0,
                    matched_text=match.group(0),
                    pattern_type="protected_term",
                    severity="high",
                )
            )

    return violations


def scan_file(
    file_path: str,
    current_project_dir: str = "",
    terms: Optional[ProtectedTerms] = None,
) -> List[Violation]:
    """Scan a file line by line for confidentiality violations.

    Args:
        file_path: Path to the file to scan.
        current_project_dir: Absolute path of the project being documented.
        terms: Protected terms to match against.

    Returns:
        A list of :class:`Violation` objects with accurate ``line_number``
        values (1-based).
    """
    path = Path(file_path)
    violations: List[Violation] = []

    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return violations

    for line_number, line in enumerate(lines, start=1):
        line_violations = scan_text(line, current_project_dir=current_project_dir, terms=terms)
        for v in line_violations:
            violations.append(
                Violation(
                    line_number=line_number,
                    matched_text=v.matched_text,
                    pattern_type=v.pattern_type,
                    severity=v.severity,
                )
            )

    return violations


def is_scannable_path(file_path: str) -> bool:
    """Return ``True`` when the path points to a documentation-type file.

    Only documentation files (Markdown, READMEs, CHANGELOGs) need to be
    scanned; source code and binary files are excluded.

    Args:
        file_path: The file path to evaluate (does not need to exist on disk).

    Returns:
        ``True`` for ``.md`` files, paths containing ``/docs/``, files named
        ``README*`` or ``CHANGELOG*``.  ``False`` otherwise.
    """
    p = Path(file_path)
    name = p.name

    if p.suffix.lower() == ".md":
        return True
    if name.startswith("README"):
        return True
    if name.startswith("CHANGELOG"):
        return True
    if "/docs/" in file_path.replace("\\", "/"):
        return True

    return False

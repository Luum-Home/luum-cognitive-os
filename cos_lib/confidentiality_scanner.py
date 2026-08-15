# SCOPE: both
"""Confidentiality scanner — detects IP leaks in generated output.

When an AI agent reads from one project and writes docs for another, it must
not mention the source project. This module scans text for paths, attribution
phrases, repo URLs, and protected terms that would constitute a confidentiality
violation.

Usage::

    from cos_lib.confidentiality_scanner import load_protected_terms, scan_text, scan_file

    terms = load_protected_terms(".cognitive-os/confidentiality.yaml")
    violations = scan_text(text, current_project_dir="<current-project-root>", terms=terms)
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
        repo_urls:     Full repository slugs (e.g. ``"org/repo-private"``).
        org_names:     GitHub / GitLab organization names (e.g. ``"luum"``).
        scan_external_paths: When False, ``external_path`` violations are not
                     reported. Defaults to True.
    """

    project_names: List[str] = field(default_factory=list)
    client_names: List[str] = field(default_factory=list)
    repo_urls: List[str] = field(default_factory=list)
    org_names: List[str] = field(default_factory=list)
    scan_external_paths: bool = True


# Every top-level key the loader understands. The shipped template is asserted
# against this set by tests/unit/test_confidentiality_schema_contract.py, so a
# key can never again be documented in the template without being consumed here.
CONFIG_KEYS: frozenset[str] = frozenset(
    {
        "project_names",
        "client_names",
        "repo_urls",
        "org_names",
        "scan_external_paths",
        # Legacy keys, accepted so configs written against the pre-2026-08-15
        # template keep working instead of silently loading zero terms.
        "protected_terms",
        "protected_orgs",
    }
)

_LEGACY_ALIASES = {
    "protected_terms": "project_names",
    "protected_orgs": "org_names",
}


def _coerce_terms(value: object) -> List[str]:
    """Normalise a config value into a flat list of strings.

    Accepts a plain list of strings, a single string, or the legacy list of
    ``{term: ..., reason: ...}`` mappings used by the old template.
    """
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    if not isinstance(value, (list, tuple)):
        return []
    out: List[str] = []
    for item in value:
        if isinstance(item, str):
            if item:
                out.append(item)
        elif isinstance(item, dict):
            term = item.get("term") or item.get("name") or item.get("value")
            if isinstance(term, str) and term:
                out.append(term)
    return out


def _coerce_bool(value: object, default: bool = True) -> bool:
    """Normalise a config value into a bool, tolerating YAML-ish strings."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("true", "yes", "on", "1"):
            return True
        if lowered in ("false", "no", "off", "0"):
            return False
    return default


# ---------------------------------------------------------------------------
# Compiled regex patterns (module-level for performance)
# ---------------------------------------------------------------------------

# Matches macOS developer home project path fragments without embedding a host path literal.
_MAC_HOME_PREFIX = "/" + "Users" + "/"
_PROJECTS_SEGMENT = "/" + "Projects" + "/"
_EXTERNAL_PATH_RE = re.compile(
    re.escape(_MAC_HOME_PREFIX)
    + r"[^/\s]+"
    + re.escape(_PROJECTS_SEGMENT)
    + r"[^/\s\"']+"
)

# Attribution phrases in English.
_EN_ATTRIBUTION = (
    r"(?:based on|adapted from|inspired by|taken from|copied from"
    r"|extracted from|reused from|ported from)"
)

# Additional English attribution phrases that may expose source-project lineage.
_ADDITIONAL_ATTRIBUTION = (
    r"(?:extracted from|model taken from)"
)

_ATTRIBUTION_RE = re.compile(
    rf"(?:{_EN_ATTRIBUTION}|{_ADDITIONAL_ATTRIBUTION})",
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

    try:
        text = path.read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001
        return ProtectedTerms()

    if yaml is None:
        raw: dict[str, object] = {}
        current_key: str | None = None
        allowed = set(CONFIG_KEYS)
        for raw_line in text.splitlines():
            line = raw_line.split("#", 1)[0].rstrip()
            if not line.strip():
                continue
            indent = len(line) - len(line.lstrip(" "))
            stripped = line.strip()
            if indent == 0 and stripped.endswith(":"):
                key = stripped[:-1]
                current_key = key if key in allowed else None
                if current_key:
                    raw[current_key] = []
                continue
            if indent == 0 and ":" in stripped:
                key, value = stripped.split(":", 1)
                key = key.strip()
                value = value.strip()
                if key in allowed:
                    if value == "[]":
                        raw[key] = []
                    elif value:
                        raw[key] = [value.strip('"').strip("'")]
                current_key = None
                continue
            if current_key and stripped.startswith("-"):
                value = stripped[1:].strip()
                # Legacy list-of-mappings form: "- term: my-project".
                if value.startswith(("term:", "name:", "value:")):
                    value = value.split(":", 1)[1].strip()
                elif ":" in value and not value.startswith(("http", '"', "'")):
                    # Any other mapping key inside a legacy entry (e.g. reason:)
                    # carries no protected term.
                    continue
                value = value.strip('"').strip("'")
                if value:
                    bucket = raw.setdefault(current_key, [])
                    if isinstance(bucket, list):
                        bucket.append(value)
    else:
        try:
            raw = yaml.safe_load(text) or {}
        except Exception:  # noqa: BLE001
            return ProtectedTerms()

    if not isinstance(raw, dict):
        return ProtectedTerms()

    # Legacy keys fold into their modern equivalent instead of being dropped.
    # Both forms may coexist; entries are merged, preserving order and
    # de-duplicating.
    merged: dict[str, List[str]] = {
        "project_names": [],
        "client_names": [],
        "repo_urls": [],
        "org_names": [],
    }
    for key in ("project_names", "client_names", "repo_urls", "org_names"):
        merged[key].extend(_coerce_terms(raw.get(key)))
    for legacy_key, modern_key in _LEGACY_ALIASES.items():
        merged[modern_key].extend(_coerce_terms(raw.get(legacy_key)))

    for key, values in merged.items():
        seen: set[str] = set()
        deduped: List[str] = []
        for value in values:
            if value not in seen:
                seen.add(value)
                deduped.append(value)
        merged[key] = deduped

    return ProtectedTerms(
        project_names=merged["project_names"],
        client_names=merged["client_names"],
        repo_urls=merged["repo_urls"],
        org_names=merged["org_names"],
        scan_external_paths=_coerce_bool(raw.get("scan_external_paths"), default=True),
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
    # Suppressed entirely when the config sets scan_external_paths: false.
    for match in _EXTERNAL_PATH_RE.finditer(text) if terms.scan_external_paths else ():
        matched = match.group(0)
        # Strip trailing punctuation that may have been captured.
        matched = matched.rstrip(".,;:)'\"")
        if current_project_dir:
            # Normalise so the project root matches the same root with a trailing slash
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

        if not triggered and terms.scan_external_paths:
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

# SCOPE: both
"""Trust Report Parser -- Machine-parseable Trust Report extraction.

Parses the structured TRUST_REPORT header line and the full human-readable
Trust Report from agent output. Inspired by GGA's STATUS: PASSED/FAILED
deterministic header pattern.

The machine-parseable header format (Wave 3 — Pydantic schema):
    TRUST_REPORT: SCORE=75 STATUS=MEDIUM EVIDENCE=3 UNCERTAINTIES=2
    ---
    WHAT I VERIFIED:
      - [verified item]
    UNSURE ABOUT:
      - [uncertainty item]
    HUMAN SHOULD CHECK:
      - [action item]

Usage:
    from lib.trust_report_parser import TrustReportParser

    parser = TrustReportParser()
    report = parser.extract_from_output(agent_output)
    if report:
        print(report.score, report.status)

Wave 3 change: TrustReport is now a Pydantic v2 model defined in
lib/trust_report_schema.py. The parser validates the extracted fields
through that schema so structural errors surface immediately with clear
error messages pointing at the malformed section.

Legacy format (pre-Wave-3) is still supported on a best-effort basis.
"""

from __future__ import annotations

import re
from typing import Optional

from pydantic import ValidationError

from lib.trust_report_schema import TrustReport, score_to_status


# Re-export for callers that previously imported from this module.
__all__ = ["TrustReport", "TrustReportParser", "score_to_status", "TrustReportParseError"]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class TrustReportParseError(ValueError):
    """Raised when a TRUST_REPORT block is found but cannot be parsed.

    Attributes:
        malformed_section: Excerpt from the malformed section for quick diagnosis.
        hint: Human-readable hint on how to fix the report.
    """

    def __init__(self, message: str, *, malformed_section: str = "", hint: str = "") -> None:
        super().__init__(message)
        self.malformed_section = malformed_section
        self.hint = hint

    def __str__(self) -> str:
        parts = [super().__str__()]
        if self.malformed_section:
            excerpt = self.malformed_section[:200].strip()
            parts.append(f"\nMalformed section (first 200 chars):\n  {excerpt!r}")
        if self.hint:
            parts.append(f"\nHint: {self.hint}")
        return "".join(parts)


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Machine-parseable header: TRUST_REPORT: SCORE=75 STATUS=MEDIUM EVIDENCE=3 UNCERTAINTIES=2
_HEADER_RE = re.compile(
    r"TRUST_REPORT:\s+"
    r"SCORE=(\d+)\s+"
    r"STATUS=(\w+)\s+"
    r"EVIDENCE=(\d+)\s+"
    r"UNCERTAINTIES=(\d+)",
    re.IGNORECASE,
)

# Legacy format: "Score: XX/100" inside a TRUST REPORT block
_LEGACY_SCORE_RE = re.compile(
    r"Score:\s*(\d+)\s*/\s*100",
    re.IGNORECASE,
)

# Count [check] / [warn] / [fail] markers in EVIDENCE PROVIDED section
_EVIDENCE_MARKER_RE = re.compile(r"\[(?:check|warn|fail)\]", re.IGNORECASE)

# Count items in "WHAT I'M UNSURE ABOUT" section (lines starting with -)
_UNSURE_SECTION_RE = re.compile(
    r"WHAT I'M UNSURE ABOUT[:\s]*\n((?:\s*-\s*.+\n?)*)",
    re.IGNORECASE,
)

# Detect the start of a legacy Trust Report block
_TRUST_REPORT_BLOCK_RE = re.compile(
    r"TRUST\s+REPORT\s*:",
    re.IGNORECASE,
)

# Section parsers for the Wave-3 human-readable body.
# Uses MULTILINE so ^ anchors at each line start, avoiding the "consumed newline"
# problem where the trailing \n? of one bullet block swallows the newline that
# the next section header relies on.
_SECTION_RE = re.compile(
    r"^(WHAT I VERIFIED|UNSURE ABOUT|HUMAN SHOULD CHECK)\s*:?\s*$\n"
    r"((?:[ \t]+-[ \t]*.+\n?)*)",
    re.IGNORECASE | re.MULTILINE,
)

_BULLET_RE = re.compile(r"^[ \t]*-[ \t]*(.+)$", re.MULTILINE)


def _extract_bullets(block: str) -> list[str]:
    """Extract bullet-point items from a section block."""
    return [m.group(1).strip() for m in _BULLET_RE.finditer(block) if m.group(1).strip()]


def _parse_sections(body: str) -> dict[str, list[str]]:
    """Parse named sections from the human-readable body."""
    sections: dict[str, list[str]] = {
        "WHAT I VERIFIED": [],
        "UNSURE ABOUT": [],
        "HUMAN SHOULD CHECK": [],
    }
    for m in _SECTION_RE.finditer(body):
        key = m.group(1).upper()
        bullets = _extract_bullets(m.group(2))
        for canonical in sections:
            if canonical in key:
                sections[canonical] = bullets
                break
    return sections


# ---------------------------------------------------------------------------
# Public parser
# ---------------------------------------------------------------------------

class TrustReportParser:
    """Parse Trust Reports from agent output.

    Returns validated :class:`lib.trust_report_schema.TrustReport` instances.
    Raises :class:`TrustReportParseError` when a TRUST_REPORT block is found
    but cannot be validated.
    """

    def parse(self, text: str) -> Optional[TrustReport]:
        """Parse a Trust Report from text that IS the report.

        Tries the machine-parseable header first, then falls back to
        parsing the legacy human-readable format.

        Args:
            text: The Trust Report text (header + body, or just body).

        Returns:
            TrustReport if successfully parsed, None otherwise.

        Raises:
            TrustReportParseError: If a header is found but the extracted
                fields fail Pydantic validation.
        """
        report = self._parse_header(text)
        if report is not None:
            return report
        return self._parse_legacy(text)

    def extract_from_output(self, full_output: str) -> Optional[TrustReport]:
        """Find and parse a Trust Report from full agent output.

        Searches the output for either:
        1. A TRUST_REPORT: header line (Wave-3 / new format)
        2. A "TRUST REPORT:" block (legacy format)

        Args:
            full_output: The complete agent output text.

        Returns:
            TrustReport if found and parsed, None otherwise.

        Raises:
            TrustReportParseError: If a report block is detected but cannot
                be parsed or validated — includes the malformed section and a
                hint about what to fix.
        """
        if not full_output:
            return None

        header_match = _HEADER_RE.search(full_output)
        if header_match:
            start = header_match.start()
            return self._parse_header(full_output[start:])

        block_match = _TRUST_REPORT_BLOCK_RE.search(full_output)
        if block_match:
            block_text = full_output[block_match.start():]
            return self._parse_legacy(block_text)

        return None

    def format_header(self, report: TrustReport) -> str:
        """Return the machine-parseable TRUST_REPORT: header line."""
        return report.header_line()

    def format_full(self, report: TrustReport) -> str:
        """Return the full human-readable Trust Report block."""
        return report.as_text()

    # ----- internal -----

    def _parse_header(self, text: str) -> Optional[TrustReport]:
        """Parse the machine-parseable header format (Wave 3)."""
        match = _HEADER_RE.search(text)
        if not match:
            return None

        score_raw = int(match.group(1))
        status_raw = match.group(2).upper()
        evidence_count = int(match.group(3))
        uncertainty_count = int(match.group(4))

        # Extract body after the separator (if present)
        separator_idx = text.find("---", match.end())
        if separator_idx != -1:
            body = text[separator_idx + 3:].strip()
        else:
            body = text[match.end():].strip()

        sections = _parse_sections(body)

        try:
            return TrustReport(
                score=score_raw,
                status=status_raw,  # type: ignore[arg-type]
                evidence_count=evidence_count,
                uncertainty_count=uncertainty_count,
                verified=sections["WHAT I VERIFIED"],
                unsure=sections["UNSURE ABOUT"],
                human_should_check=sections["HUMAN SHOULD CHECK"],
            )
        except ValidationError as exc:
            malformed = text[match.start(): match.start() + 300]
            hint = (
                "Check that SCORE matches STATUS band (HIGH 90-100, MEDIUM 70-89, "
                "LOW 50-69, CRITICAL 0-49), UNCERTAINTIES >= 1, and SCORE is 0-100."
            )
            raise TrustReportParseError(
                f"TRUST_REPORT block found but failed validation: {exc}",
                malformed_section=malformed,
                hint=hint,
            ) from exc

    def _parse_legacy(self, text: str) -> Optional[TrustReport]:
        """Parse the legacy human-readable Trust Report format (pre-Wave-3)."""
        score_match = _LEGACY_SCORE_RE.search(text)
        if not score_match:
            return None

        score = int(score_match.group(1))
        if not (0 <= score <= 100):
            raise TrustReportParseError(
                f"Legacy TRUST REPORT has out-of-range score: {score}",
                malformed_section=text[:200],
                hint="Score must be between 0 and 100 inclusive.",
            )

        status = score_to_status(score)

        # Count evidence markers
        evidence_count = len(_EVIDENCE_MARKER_RE.findall(text))

        # Count uncertainty items (legacy section name)
        uncertainty_count = 0
        unsure_match = _UNSURE_SECTION_RE.search(text)
        if unsure_match:
            items = unsure_match.group(1).strip()
            if items:
                uncertainty_count = len(
                    [line for line in items.split("\n") if line.strip().startswith("-")]
                )

        # Clamp uncertainty_count to at least 1 for legacy reports so that
        # the Pydantic model (uncertainty_count >= 1) doesn't reject them.
        # Legacy agents weren't required to emit a structured uncertainty section,
        # so we treat "unknown" as 1 rather than blocking ingestion.
        uncertainty_count_validated = max(uncertainty_count, 1)

        sections = _parse_sections(text)
        # For legacy format, fall back to counting bullets in raw text
        if not sections["WHAT I VERIFIED"]:
            # Try the old "WHAT I'M CONFIDENT ABOUT" section
            confident_re = re.compile(
                r"WHAT I'M CONFIDENT ABOUT[:\s]*\n((?:\s*-\s*.+\n?)*)",
                re.IGNORECASE,
            )
            cm = confident_re.search(text)
            if cm:
                sections["WHAT I VERIFIED"] = _extract_bullets(cm.group(1))

        if not sections["UNSURE ABOUT"] and unsure_match:
            sections["UNSURE ABOUT"] = _extract_bullets(unsure_match.group(1))

        # Build check list from "WHAT THE HUMAN SHOULD VERIFY" (legacy name)
        if not sections["HUMAN SHOULD CHECK"]:
            human_re = re.compile(
                r"WHAT THE HUMAN SHOULD (?:VERIFY|CHECK)[:\s]*\n((?:\s*-\s*.+\n?)*)",
                re.IGNORECASE,
            )
            hm = human_re.search(text)
            if hm:
                sections["HUMAN SHOULD CHECK"] = _extract_bullets(hm.group(1))

        try:
            return TrustReport(
                score=score,
                status=status,
                evidence_count=evidence_count,
                uncertainty_count=uncertainty_count_validated,
                verified=sections["WHAT I VERIFIED"],
                unsure=sections["UNSURE ABOUT"],
                human_should_check=sections["HUMAN SHOULD CHECK"],
            )
        except ValidationError as exc:
            raise TrustReportParseError(
                f"Legacy TRUST REPORT failed validation: {exc}",
                malformed_section=text[:300],
                hint="Ensure score is 0-100 and status matches band.",
            ) from exc

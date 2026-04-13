# scope: both
"""Trust Report Parser -- Machine-parseable Trust Report extraction.

Parses the structured TRUST_REPORT header line and the full human-readable
Trust Report from agent output. Inspired by GGA's STATUS: PASSED/FAILED
deterministic header pattern.

The machine-parseable header format:
    TRUST_REPORT: SCORE=75 STATUS=MEDIUM EVIDENCE=3 UNCERTAINTIES=2
    ---
    Score: 75/100
    ...rest of human-readable report...

Usage:
    from lib.trust_report_parser import TrustReportParser

    parser = TrustReportParser()
    report = parser.extract_from_output(agent_output)
    if report:
        print(report.score, report.status)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


# Status thresholds matching rules/trust-score.md
_STATUS_THRESHOLDS = [
    (90, "HIGH"),       # 90-100
    (70, "MEDIUM"),     # 70-89
    (50, "LOW"),        # 50-69
    (0, "CRITICAL"),    # 0-49
]


def score_to_status(score: int) -> str:
    """Convert a numeric trust score to a status label.

    Returns:
        HIGH (90+), MEDIUM (70-89), LOW (50-69), CRITICAL (<50).
    """
    for threshold, status in _STATUS_THRESHOLDS:
        if score >= threshold:
            return status
    return "CRITICAL"


@dataclass(frozen=True)
class TrustReport:
    """Parsed Trust Report with both machine and human data."""

    score: int
    status: str           # HIGH, MEDIUM, LOW, CRITICAL
    evidence_count: int
    uncertainty_count: int
    raw_text: str         # Full report text (human-readable portion)

    def __str__(self) -> str:
        return (
            f"TrustReport(score={self.score}, status={self.status}, "
            f"evidence={self.evidence_count}, uncertainties={self.uncertainty_count})"
        )


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


class TrustReportParser:
    """Parse Trust Reports from agent output."""

    def parse(self, text: str) -> Optional[TrustReport]:
        """Parse a Trust Report from text that IS the report.

        Tries the machine-parseable header first, then falls back to
        parsing the legacy human-readable format.

        Args:
            text: The Trust Report text (header + body, or just body).

        Returns:
            TrustReport if successfully parsed, None otherwise.
        """
        # Try machine-parseable header first
        report = self._parse_header(text)
        if report is not None:
            return report

        # Fall back to legacy format
        return self._parse_legacy(text)

    def extract_from_output(self, full_output: str) -> Optional[TrustReport]:
        """Find and parse a Trust Report from full agent output.

        Searches the output for either:
        1. A TRUST_REPORT: header line (new format)
        2. A "TRUST REPORT:" block (legacy format)

        Args:
            full_output: The complete agent output text.

        Returns:
            TrustReport if found and parsed, None otherwise.
        """
        if not full_output:
            return None

        # Try new header format first
        header_match = _HEADER_RE.search(full_output)
        if header_match:
            # Extract everything from the header to the end (or next major section)
            start = header_match.start()
            raw_text = full_output[start:]
            return TrustReport(
                score=int(header_match.group(1)),
                status=header_match.group(2).upper(),
                evidence_count=int(header_match.group(3)),
                uncertainty_count=int(header_match.group(4)),
                raw_text=raw_text.strip(),
            )

        # Try legacy format
        block_match = _TRUST_REPORT_BLOCK_RE.search(full_output)
        if block_match:
            # Extract from "TRUST REPORT:" to the end
            block_text = full_output[block_match.start():]
            return self._parse_legacy(block_text)

        return None

    def format_header(self, report: TrustReport) -> str:
        """Generate the machine-parseable header line for a TrustReport.

        Args:
            report: A TrustReport instance.

        Returns:
            The TRUST_REPORT: header string.
        """
        return (
            f"TRUST_REPORT: SCORE={report.score} STATUS={report.status} "
            f"EVIDENCE={report.evidence_count} UNCERTAINTIES={report.uncertainty_count}"
        )

    def format_full(self, report: TrustReport) -> str:
        """Generate a complete Trust Report with header and separator.

        Args:
            report: A TrustReport instance.

        Returns:
            Header + separator + raw_text.
        """
        header = self.format_header(report)
        return f"{header}\n---\n{report.raw_text}"

    # ----- internal -----

    def _parse_header(self, text: str) -> Optional[TrustReport]:
        """Parse the machine-parseable header format."""
        match = _HEADER_RE.search(text)
        if not match:
            return None

        score = int(match.group(1))
        status = match.group(2).upper()
        evidence_count = int(match.group(3))
        uncertainty_count = int(match.group(4))

        # Extract the body after the separator (if present)
        separator_idx = text.find("---", match.end())
        if separator_idx != -1:
            raw_text = text[separator_idx + 3:].strip()
        else:
            raw_text = text[match.end():].strip()

        return TrustReport(
            score=score,
            status=status,
            evidence_count=evidence_count,
            uncertainty_count=uncertainty_count,
            raw_text=raw_text,
        )

    def _parse_legacy(self, text: str) -> Optional[TrustReport]:
        """Parse the legacy human-readable Trust Report format."""
        # Extract score
        score_match = _LEGACY_SCORE_RE.search(text)
        if not score_match:
            return None

        score = int(score_match.group(1))
        status = score_to_status(score)

        # Count evidence markers
        evidence_count = len(_EVIDENCE_MARKER_RE.findall(text))

        # Count uncertainty items
        uncertainty_count = 0
        unsure_match = _UNSURE_SECTION_RE.search(text)
        if unsure_match:
            items = unsure_match.group(1).strip()
            if items:
                uncertainty_count = len(
                    [line for line in items.split("\n") if line.strip().startswith("-")]
                )

        return TrustReport(
            score=score,
            status=status,
            evidence_count=evidence_count,
            uncertainty_count=uncertainty_count,
            raw_text=text.strip(),
        )

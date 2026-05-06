# SCOPE: both
"""Research-quality advisor for audit/research reports.

Scores a markdown report on four dimensions tied to ADR-175 and grounded
in the 2026-05-05 audit-asymmetry incident (see
``docs/reports/cos-side-deep-rebuttal-2026-05-05.md`` and the three
opus-deep-audit reports of the same date):

* Symmetric citation (40%) — every comparison row cites ``file:line`` on
  BOTH sides; rows with file:line on only one side count as asymmetric.
* Confidence levels (25%) — every prose claim block carries a HIGH /
  MEDIUM / LOW marker (or an explicit "Confidence:" line).
* Numerical specificity (20%) — numeric claims are surrounded by a
  fenced bash/shell block capturing the command that produced them.
* Falsifiable claim section (15%) — the report contains a section
  explicitly listing claims that could be falsified, or a TRUST_REPORT
  / UNCERTAINTIES block that documents how the report could be wrong.

Standard library only.  ADR-175.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple

# ---------------------------------------------------------------------------
# Heuristic regexes
# ---------------------------------------------------------------------------

# "file.py:123" or "path/to/file.sh:12-45" — must include extension to avoid
# matching plain colons in prose.
_FILE_LINE_RE = re.compile(
    r"`?[\w./_\-]+\.(?:py|sh|md|yaml|yml|json|jsonl|toml|go|ts|js|tsx|jsx|rs|rb|html|css|sql)`?"
    r":\s*\d+(?:\s*[-–]\s*\d+)?"
)

# Confidence markers: HIGH / MEDIUM / LOW or "Confidence: ..." line.
_CONFIDENCE_RE = re.compile(
    r"\b(HIGH|MEDIUM|LOW)\b|(?:^|\s)Confidence\s*:\s*\w+",
    re.IGNORECASE,
)

# Bare numerical claim — at least 2 digits or a decimal — used to detect
# unsupported numbers in prose paragraphs.
_NUMBER_RE = re.compile(r"\b\d{2,}(?:[.,]\d+)?\b")

# Cheap-but-wrong tokens that signal hand-wavy phrasing.
_HAND_WAVY_RE = re.compile(
    r"\b(?:roughly|approximately|several|many|some|a lot of|various|"
    r"around|about)\b",
    re.IGNORECASE,
)

# Fenced bash/shell block (captures the inner content).
_FENCED_SHELL_RE = re.compile(
    r"```(?:bash|sh|shell|console|terminal)\s*\n(.*?)\n```",
    re.DOTALL | re.IGNORECASE,
)

# Falsifiability section heuristics.
_FALSIFIABLE_HEADINGS = (
    "falsifiable",
    "uncertainties",
    "uncertainty",
    "trust report",
    "trust_report",
    "what could be wrong",
    "limitations",
    "how this could be wrong",
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class DimensionScore:
    """Score for a single dimension."""

    name: str
    weight: float
    score: float           # 0..100
    findings: List[str] = field(default_factory=list)


@dataclass
class ResearchQualityReport:
    """Aggregated research-quality report for a single markdown file."""

    overall_score: float
    dimensions: List[DimensionScore]
    asymmetric_rows: int
    total_rows: int
    suggestions: List[str] = field(default_factory=list)

    def to_jsonable(self) -> dict:
        """Convert to a JSON-serialisable dict for logging."""
        return {
            "overall_score": round(self.overall_score, 2),
            "asymmetric_rows": self.asymmetric_rows,
            "total_rows": self.total_rows,
            "dimensions": [
                {
                    "name": d.name,
                    "weight": d.weight,
                    "score": round(d.score, 2),
                    "findings": d.findings,
                }
                for d in self.dimensions
            ],
            "suggestions": self.suggestions,
        }


# ---------------------------------------------------------------------------
# Advisor
# ---------------------------------------------------------------------------


class ResearchQualityAdvisor:
    """Score audit/research reports for evidence quality.

    Pure regex-based.  No external network or filesystem access.

    Knobs (overridable via ``__init__`` for tests):

    * ``min_table_rows`` — tables with fewer rows are ignored when
      scoring symmetric citation; small tables shouldn't dominate.
    * ``warn_threshold`` — overall score below this triggers a stderr
      warning in the hook (default 70, per ADR-175 §threshold).
    """

    SYMMETRIC_WEIGHT = 0.40
    CONFIDENCE_WEIGHT = 0.25
    NUMERICAL_WEIGHT = 0.20
    FALSIFIABLE_WEIGHT = 0.15

    def __init__(
        self,
        min_table_rows: int = 2,
        warn_threshold: float = 70.0,
    ) -> None:
        self.min_table_rows = min_table_rows
        self.warn_threshold = warn_threshold

    # -- public API -------------------------------------------------------

    def score(self, markdown_text: str) -> ResearchQualityReport:
        """Compute the four-dimension score for ``markdown_text``."""
        text = markdown_text or ""

        sym_score, asym_rows, total_rows, sym_findings = self._score_symmetric(text)
        conf_score, conf_findings = self._score_confidence(text)
        num_score, num_findings = self._score_numerical(text)
        fals_score, fals_findings = self._score_falsifiable(text)

        dims = [
            DimensionScore(
                name="symmetric_citation",
                weight=self.SYMMETRIC_WEIGHT,
                score=sym_score,
                findings=sym_findings,
            ),
            DimensionScore(
                name="confidence_levels",
                weight=self.CONFIDENCE_WEIGHT,
                score=conf_score,
                findings=conf_findings,
            ),
            DimensionScore(
                name="numerical_specificity",
                weight=self.NUMERICAL_WEIGHT,
                score=num_score,
                findings=num_findings,
            ),
            DimensionScore(
                name="falsifiable_claim",
                weight=self.FALSIFIABLE_WEIGHT,
                score=fals_score,
                findings=fals_findings,
            ),
        ]

        overall = sum(d.score * d.weight for d in dims)

        report = ResearchQualityReport(
            overall_score=round(overall, 2),
            dimensions=dims,
            asymmetric_rows=asym_rows,
            total_rows=total_rows,
        )
        report.suggestions = self.suggest_improvements(report)
        return report

    def suggest_improvements(self, report: ResearchQualityReport) -> List[str]:
        """Actionable improvement hints based on per-dimension findings."""
        out: List[str] = []
        by_name = {d.name: d for d in report.dimensions}

        sym = by_name.get("symmetric_citation")
        if sym and sym.score < 80:
            out.append(
                "Add file:line citations on both sides of every comparison row "
                "(asymmetric depth is the documented 2026-05-05 audit bug)."
            )
        conf = by_name.get("confidence_levels")
        if conf and conf.score < 80:
            out.append(
                "Tag each prose claim with a HIGH/MEDIUM/LOW confidence "
                "marker so readers can weight your conclusions."
            )
        num = by_name.get("numerical_specificity")
        if num and num.score < 80:
            out.append(
                "Surround numeric claims with the bash command that produced "
                "them in a fenced block (```bash ... ```)."
            )
        fals = by_name.get("falsifiable_claim")
        if fals and fals.score < 80:
            out.append(
                "Add a 'Falsifiable claims' or 'Uncertainties' section "
                "describing how the report could be wrong."
            )
        return out

    # -- helpers ----------------------------------------------------------

    @staticmethod
    def _iter_table_rows(text: str) -> List[str]:
        """Return data rows from every markdown pipe table.

        Rules (kept simple): a row starts with ``|``, contains at least
        one more ``|``, and is not the header separator (``|---|...``).
        """
        rows: List[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped.startswith("|") or stripped.count("|") < 3:
                continue
            # Skip separator: cells are only - : space
            inner = stripped.strip("|")
            cells = [c.strip() for c in inner.split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                continue
            # Skip pure-header rows by content heuristic: header text usually
            # has no file:line and very few columns.  We let the symmetric
            # scorer deal with that — it is already the correct policy.
            rows.append(stripped)
        return rows

    def _score_symmetric(
        self, text: str
    ) -> Tuple[float, int, int, List[str]]:
        """Score symmetric citation across all table rows."""
        rows = self._iter_table_rows(text)
        # First row is typically the header — drop if it has no digits at all.
        if rows and not _NUMBER_RE.search(rows[0]) and not _FILE_LINE_RE.search(rows[0]):
            rows = rows[1:]

        if len(rows) < self.min_table_rows:
            # Too small to score table-level symmetry; check global symmetry
            # instead — does the doc cite file:line at all?
            citations = _FILE_LINE_RE.findall(text)
            score = 100.0 if len(citations) >= 4 else 50.0 * (len(citations) / 4.0)
            findings: List[str] = []
            if score < 80:
                findings.append(
                    f"Only {len(citations)} file:line citations found (no scoreable comparison table)."
                )
            return score, 0, 0, findings

        asym = 0
        total = len(rows)
        per_row_findings: List[str] = []
        for row in rows:
            inner = row.strip("|")
            cells = [c.strip() for c in inner.split("|")]
            # Need at least 4 cells to even talk about symmetric comparison.
            if len(cells) < 4:
                continue
            # Heuristic: any cell that looks like a "verdict" cell (just a
            # short word like CONFIRMED / IGUAL / CORRECTED) is excluded;
            # remaining cells are evidence cells.
            evidence_cells = [c for c in cells if len(c) > 12]
            if not evidence_cells:
                continue
            cells_with_citation = sum(
                1 for c in evidence_cells if _FILE_LINE_RE.search(c)
            )
            cells_with_handwavy = sum(
                1 for c in evidence_cells if _HAND_WAVY_RE.search(c)
            )
            # Asymmetric if at least one evidence cell cites file:line and
            # at least one other evidence cell has no file:line citation.
            if (
                cells_with_citation >= 1
                and cells_with_citation < len(evidence_cells)
            ):
                asym += 1
                if cells_with_handwavy:
                    per_row_findings.append(
                        f"Row with hand-wavy phrasing on uncited side: '{row[:120]}...'"
                    )

        # Score: 100 when no asymmetric rows, 0 when all rows are asymmetric.
        score = 100.0 * (1.0 - (asym / max(total, 1)))
        if asym:
            per_row_findings.insert(
                0,
                f"{asym}/{total} table rows have asymmetric file:line citation",
            )
        return score, asym, total, per_row_findings

    def _score_confidence(self, text: str) -> Tuple[float, List[str]]:
        """Score per-claim confidence markers.

        Scoring blends two signals:

        * Absolute marker count — a report with many ``Confidence: HIGH``
          markers should score well even if the per-claim ratio is low.
        * Per-claim ratio — paragraphs containing verdict-like words
          should each carry a marker.
        """
        markers = _CONFIDENCE_RE.findall(text)
        # Absolute-count signal: 0 markers = 0; >= 6 markers = 100.
        absolute_score = min(100.0, (len(markers) / 6.0) * 100.0)

        claim_words = (
            r"\b(verdict|claim|finding|recommend|recommendation|"
            r"conclude|conclusion|assert|propose)\b"
        )
        paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
        claim_paragraphs = [
            p for p in paragraphs if re.search(claim_words, p, re.IGNORECASE)
        ]

        findings: List[str] = []
        if not claim_paragraphs:
            return absolute_score, (
                ["No claim-style paragraphs detected; scored on marker count alone."]
                if absolute_score < 80
                else []
            )
        tagged = sum(1 for p in claim_paragraphs if _CONFIDENCE_RE.search(p))
        ratio_score = 100.0 * tagged / len(claim_paragraphs)
        # Take the better of the two signals — either consistent per-claim
        # tagging OR a strong absolute commitment to confidence labelling
        # earns full credit.
        score = max(ratio_score, absolute_score)
        if tagged < len(claim_paragraphs) and score < 80:
            findings.append(
                f"{len(claim_paragraphs) - tagged}/{len(claim_paragraphs)} "
                "claim paragraphs lack a HIGH/MEDIUM/LOW marker"
            )
        return score, findings

    def _score_numerical(self, text: str) -> Tuple[float, List[str]]:
        """Score whether numeric claims are backed by a captured command."""
        # Strip fenced blocks to find numbers in prose only.
        prose = _FENCED_SHELL_RE.sub("", text)
        # Strip inline code spans (`...`) to avoid false positives.
        prose = re.sub(r"`[^`]+`", "", prose)
        prose_numbers = _NUMBER_RE.findall(prose)

        fenced = _FENCED_SHELL_RE.findall(text)
        has_command_evidence = any(
            re.search(r"\b(grep|wc|find|ls|jq|awk|sed|cat|head|tail|gh|python3?)\b", b)
            for b in fenced
        )

        findings: List[str] = []
        if not prose_numbers:
            return 100.0, findings

        if not fenced:
            return 0.0, [
                f"{len(prose_numbers)} numeric claims in prose with no fenced command blocks at all"
            ]

        # Heuristic: ratio of fenced blocks-with-commands to numeric-claim
        # density.  Saturates fast — 1 captured command for ≤5 numbers is fine.
        density = len(prose_numbers) / max(len(fenced), 1)
        if has_command_evidence and density <= 5.0:
            score = 100.0
        elif has_command_evidence and density <= 10.0:
            score = 75.0
            findings.append(
                f"High numeric-claim density ({density:.1f} numbers per fenced block); "
                "some numbers may not be backed by a captured command."
            )
        elif has_command_evidence:
            score = 50.0
            findings.append(
                f"Very high numeric-claim density ({density:.1f}); most numbers likely lack capture."
            )
        else:
            score = 25.0
            findings.append("Fenced blocks present but none look like captured commands.")
        return score, findings

    def _score_falsifiable(self, text: str) -> Tuple[float, List[str]]:
        """Score presence of an explicit falsifiability section."""
        lowered = text.lower()
        matched = [h for h in _FALSIFIABLE_HEADINGS if h in lowered]
        if not matched:
            return 0.0, ["No 'Falsifiable claims' / 'Uncertainties' / 'Trust Report' section."]

        # Find the first such heading and check it has actual content (>40 chars
        # of prose after the heading line).
        for heading in matched:
            idx = lowered.find(heading)
            tail = text[idx : idx + 800]
            # Section is concrete if it has either (a) at least 40 non-heading
            # chars of prose, OR (b) at least one bullet point.
            non_heading = re.sub(r"^#+\s.*$", "", tail, flags=re.MULTILINE)
            has_bullet = bool(re.search(r"^\s*[-*]\s+\S", tail, re.MULTILINE))
            if has_bullet or len(non_heading.strip()) >= 80:
                return 100.0, []
        return 50.0, [
            "Falsifiability heading found but section is empty or stub-only."
        ]


# ---------------------------------------------------------------------------
# Convenience entry points
# ---------------------------------------------------------------------------


def score_file(path: Path) -> ResearchQualityReport:
    """Convenience: score a markdown file by path."""
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    return ResearchQualityAdvisor().score(text)


__all__ = [
    "ResearchQualityAdvisor",
    "ResearchQualityReport",
    "DimensionScore",
    "score_file",
]

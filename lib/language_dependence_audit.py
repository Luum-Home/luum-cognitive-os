"""Audit agentic primitive routing patterns for natural-language dependence.

The audit is intentionally structural: it extracts string literals from regex
patterns and lets an optional language detector decide whether those literals
look like human language. It does not maintain a list of Spanish/English words.

ADR-296 + ADR-297 context (post-2026-05-13):

  Findings reported by this audit are no longer "broken right now" — the
  semantic matcher (ADR-296) and the LLM tie-breaker (ADR-297) catch
  multilingual prompts independently of regex coverage. Findings are now
  **tech debt to clean up over time** plus a **regression gate**: each
  language-dependent pattern represents work that should migrate to the
  semantic path (or be deleted if redundant). The
  `test_language_dependence_audit_does_not_regress` test in
  tests/unit/test_semantic_skill_matcher.py caps the total finding count
  so new monolingual patterns cannot land silently.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sre_parse  # type: ignore[deprecated]
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

try:
    import yaml  # type: ignore[import]
except Exception:  # pragma: no cover - PyYAML is a core dependency in this repo
    yaml = None  # type: ignore[assignment]

TECHNICAL_LITERAL_RE = re.compile(
    r"^(?:/[\w.-]+|https?|github|com|org|net|[a-z0-9]+(?:[-_/.:][a-z0-9]+)+|[a-z]+\.[a-z0-9]+)$",
    re.IGNORECASE,
)
WORDISH_RE = re.compile(r"^[^\W\d_]{3,}$", re.UNICODE)


@dataclass(frozen=True)
class LanguageGuess:
    """Detected natural language for one extracted literal."""

    literal: str
    language: str
    confidence: float
    detector: str


@dataclass(frozen=True)
class RoutingPatternFinding:
    """One suspicious routing regex finding."""

    file: str
    primitive: str
    primitive_type: str
    pattern: str
    confidence: float
    line: int | None
    extracted_literals: tuple[str, ...]
    language_guesses: tuple[LanguageGuess, ...]
    structural_score: int
    severity: str
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "file": self.file,
            "primitive": self.primitive,
            "primitive_type": self.primitive_type,
            "pattern": self.pattern,
            "confidence": self.confidence,
            "line": self.line,
            "extracted_literals": list(self.extracted_literals),
            "language_guesses": [guess.__dict__ for guess in self.language_guesses],
            "structural_score": self.structural_score,
            "severity": self.severity,
            "recommendation": self.recommendation,
        }


@dataclass(frozen=True)
class AuditReport:
    """Language-dependence audit result."""

    root: str
    detector: str
    scanned_files: int
    scanned_patterns: int
    total_findings: int
    findings: tuple[RoutingPatternFinding, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "language-dependence-audit/v1",
            "root": self.root,
            "detector": self.detector,
            "scanned_files": self.scanned_files,
            "scanned_patterns": self.scanned_patterns,
            "finding_count": len(self.findings),
            "total_finding_count": self.total_findings,
            "findings": [finding.to_dict() for finding in self.findings],
        }


class OptionalLinguaDetector:
    """Thin adapter around lingua-language-detector when installed."""

    def __init__(self) -> None:
        self._detector = None
        self.name = "heuristic"
        if os.environ.get("COS_LANGUAGE_AUDIT_DISABLE_LINGUA") in {"1", "true", "TRUE"}:
            return
        try:
            from lingua import LanguageDetectorBuilder  # type: ignore[import]

            self._detector = LanguageDetectorBuilder.from_all_languages().build()
            self.name = "lingua"
        except Exception:
            self._detector = None

    def detect(self, literal: str) -> LanguageGuess | None:
        if self._detector is None:
            return None
        confidence_values = self._detector.compute_language_confidence_values(literal)
        if not confidence_values:
            return None
        best = confidence_values[0]
        confidence = float(best.value)
        if confidence < 0.35:
            return None
        language = getattr(best.language, "iso_code_639_1", None)
        language_code = str(language.name).lower() if language is not None else str(best.language).lower()
        return LanguageGuess(literal=literal, language=language_code, confidence=confidence, detector=self.name)


def _frontmatter(text: str) -> tuple[dict[str, Any], int]:
    lines = text.splitlines()
    start = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "---":
            start = index
            break
        if stripped.startswith("<!--") or stripped == "":
            continue
        return {}, 0
    if start is None:
        return {}, 0
    end = None
    for index in range(start + 1, len(lines)):
        if lines[index].strip() == "---":
            end = index
            break
    if end is None:
        return {}, 0
    if yaml is None:
        return {}, end + 1
    data = yaml.safe_load("\n".join(lines[start + 1 : end])) or {}
    return data if isinstance(data, dict) else {}, end + 1


def _routing_pattern_line(text: str, pattern: str) -> int | None:
    needle_options = [f"pattern: '{pattern}'", f'pattern: "{pattern}"', f"pattern: {pattern}"]
    for line_number, line in enumerate(text.splitlines(), start=1):
        if any(needle in line for needle in needle_options):
            return line_number
    # Fall back to substring search; useful if YAML normalized quoting.
    for line_number, line in enumerate(text.splitlines(), start=1):
        if pattern in line and "pattern:" in line:
            return line_number
    return None


def _iter_regex_literals(parsed: Iterable[tuple[Any, Any]]) -> Iterable[str]:
    buffer: list[str] = []

    def flush() -> Iterable[str]:
        nonlocal buffer
        if buffer:
            literal = "".join(buffer)
            buffer = []
            yield literal

    for op, arg in parsed:
        if op is sre_parse.LITERAL:
            buffer.append(chr(arg))
            continue
        yield from flush()
        if op is sre_parse.SUBPATTERN:
            yield from _iter_regex_literals(arg[-1])
        elif op is sre_parse.BRANCH:
            for branch in arg[1]:
                yield from _iter_regex_literals(branch)
        elif op in {sre_parse.MAX_REPEAT, sre_parse.MIN_REPEAT}:
            yield from _iter_regex_literals(arg[2])
        elif op is sre_parse.IN:
            # Character classes are usually technical shape constraints.
            continue
    yield from flush()


def extract_regex_literals(pattern: str) -> tuple[str, ...]:
    """Extract literal word-like fragments from a regex without keyword lists."""
    try:
        parsed = sre_parse.parse(pattern)
        raw_literals = list(_iter_regex_literals(parsed))
    except Exception:
        raw_literals = re.findall(r"[^\\\[\]().|?+*{}^$\s]+", pattern)

    literals: list[str] = []
    for raw in raw_literals:
        for token in re.split(r"\s+", raw):
            cleaned = token.strip("'\"`.,:;!?()[]{}^$\\")
            if not cleaned or len(cleaned) < 3:
                continue
            if TECHNICAL_LITERAL_RE.match(cleaned):
                continue
            if WORDISH_RE.match(cleaned):
                literals.append(cleaned)
    return tuple(dict.fromkeys(literals))


def structural_risk_score(pattern: str, literals: Sequence[str]) -> int:
    """Score whether a regex looks like natural-language intent matching."""
    score = 0
    if r"\b" in pattern:
        score += 2
    if "|" in pattern:
        score += 2
    if re.search(r"\.\{0,\d+\}", pattern):
        score += 2
    if r"\w" in pattern:
        score += 1
    if any(ord(ch) > 127 for ch in pattern):
        score += 2
    if len(literals) >= 3:
        score += 1
    if re.search(r"/?[a-z0-9]+(?:-[a-z0-9]+)+", pattern, re.IGNORECASE):
        score -= 2
    if "http" in pattern or "github" in pattern:
        score -= 3
    if re.search(r"\.[a-z0-9]{1,5}", pattern, re.IGNORECASE):
        score -= 1
    return score


def _fallback_language_guesses(literals: Sequence[str]) -> tuple[LanguageGuess, ...]:
    """Dependency-free fallback: marks word-like literals as unknown natural language."""
    guesses = []
    for literal in literals:
        if WORDISH_RE.match(literal):
            guesses.append(LanguageGuess(literal=literal, language="und", confidence=0.40, detector="heuristic"))
    return tuple(guesses)


def _pattern_finding(
    *,
    root: Path,
    path: Path,
    primitive_type: str,
    primitive: str,
    pattern: str,
    confidence: float,
    line: int | None,
    detector: OptionalLinguaDetector,
) -> RoutingPatternFinding | None:
    literals = extract_regex_literals(pattern)
    if not literals:
        return None
    guesses = tuple(guess for literal in literals if (guess := detector.detect(literal)) is not None)
    if not guesses:
        guesses = _fallback_language_guesses(literals)
    score = structural_risk_score(pattern, literals)
    if not guesses and score < 4:
        return None
    if score < 2 and all(guess.language == "und" for guess in guesses):
        return None
    severity = "high" if score >= 5 and any(guess.detector != "heuristic" for guess in guesses) else "medium"
    if score < 4:
        severity = "low"
    return RoutingPatternFinding(
        file=str(path.relative_to(root)),
        primitive=primitive,
        primitive_type=primitive_type,
        pattern=pattern,
        confidence=confidence,
        line=line,
        extracted_literals=tuple(literals),
        language_guesses=guesses,
        structural_score=score,
        severity=severity,
        recommendation=(
            "Prefer ADR-296 semantic routing — the SKILL.md `description` "
            "field is now the multilingual source of truth. Delete or migrate "
            "language-dependent routing_patterns; reserve routing_patterns "
            "ONLY for explicit slash-commands, IDs, URLs, and paths "
            "(routing_intents lists are also indexed by the semantic matcher "
            "if you need supplementary utterances). Ambiguous prompts are "
            "broken by ADR-297's LLM fallback."
        ),
    )


def _iter_candidate_files(root: Path) -> Iterable[tuple[Path, str]]:
    for base, primitive_type in ((root / "skills", "skill"), (root / "rules", "rule")):
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.md")):
            yield path, primitive_type
    packages = root / "packages"
    if packages.exists():
        for path in sorted(packages.glob("*/skills/*/SKILL.md")):
            yield path, "skill"
        for path in sorted(packages.glob("*/rules/*.md")):
            yield path, "rule"


def audit(root: Path, min_severity: str = "medium") -> AuditReport:
    detector = OptionalLinguaDetector()
    findings: list[RoutingPatternFinding] = []
    scanned_files = 0
    scanned_patterns = 0
    for path, primitive_type in _iter_candidate_files(root):
        text = path.read_text(encoding="utf-8", errors="replace")
        if "routing_patterns" not in text:
            continue
        frontmatter, _ = _frontmatter(text)
        patterns = frontmatter.get("routing_patterns")
        if not isinstance(patterns, list):
            continue
        scanned_files += 1
        primitive = str(frontmatter.get("name") or path.parent.name if primitive_type == "skill" else path.stem)
        for entry in patterns:
            if not isinstance(entry, dict) or not entry.get("pattern"):
                continue
            pattern = str(entry["pattern"])
            confidence = float(entry.get("confidence", 0.80))
            scanned_patterns += 1
            finding = _pattern_finding(
                root=root,
                path=path,
                primitive_type=primitive_type,
                primitive=primitive,
                pattern=pattern,
                confidence=confidence,
                line=_routing_pattern_line(text, pattern),
                detector=detector,
            )
            if finding:
                findings.append(finding)
    severity_rank = {"low": 1, "medium": 2, "high": 3}
    min_rank = severity_rank.get(min_severity, 2)
    visible_findings = tuple(finding for finding in findings if severity_rank[finding.severity] >= min_rank)
    return AuditReport(
        root=str(root),
        detector=detector.name,
        scanned_files=scanned_files,
        scanned_patterns=scanned_patterns,
        total_findings=len(findings),
        findings=visible_findings,
    )


def render_markdown(report: AuditReport) -> str:
    lines = [
        "# Language Dependence Audit",
        "",
        f"- Detector: `{report.detector}`",
        f"- Scanned files: {report.scanned_files}",
        f"- Scanned routing patterns: {report.scanned_patterns}",
        f"- Findings shown: {len(report.findings)}",
        f"- Total findings including low severity: {report.total_findings}",
        "",
    ]
    if not report.findings:
        lines.append("No language-dependent routing patterns found.")
        return "\n".join(lines) + "\n"
    lines.extend(["| Severity | File | Line | Primitive | Languages | Pattern |", "|---|---|---:|---|---|---|"])
    for finding in report.findings:
        languages = ", ".join(sorted({guess.language for guess in finding.language_guesses})) or "unknown"
        pattern = finding.pattern.replace("|", "\\|")
        lines.append(
            f"| {finding.severity} | `{finding.file}` | {finding.line or ''} | `{finding.primitive}` | {languages} | `{pattern}` |"
        )
    lines.append("")
    lines.append("Recommendation: migrate natural-language intent matching to `routing_intents`; keep regex routing for explicit commands, primitive IDs, URLs, and file/path shapes.")
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit routing_patterns for natural-language dependence.")
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown")
    parser.add_argument("--min-severity", choices=["low", "medium", "high"], default="medium", help="Minimum severity to include in output")
    parser.add_argument("--output", help="Optional output path")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    report = audit(root, min_severity=args.min_severity)
    rendered = json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n" if args.json else render_markdown(report)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

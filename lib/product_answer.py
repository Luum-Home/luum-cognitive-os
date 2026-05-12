"""ADR-280 product question-to-evidence primitive."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

QUESTION_BANK_SCHEMA = "product-question-bank/v1"
CLAIM_EVIDENCE_SCHEMA = "product-claim-evidence/v1"
REPORT_SCHEMA = "product-answer-report/v1"
DEFAULT_STATUS_ORDER = ["real", "partial-real", "partial", "aspirational", "blocked"]


@dataclass(frozen=True)
class ProductAnswerError(Exception):
    """Raised when product answer manifests are invalid or no question matches."""

    message: str

    def __str__(self) -> str:
        return self.message


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML mapping from ``path``."""
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ProductAnswerError(f"manifest must be a mapping: {path}")
    return payload


def load_question_bank(path: Path) -> dict[str, Any]:
    """Load and validate the product question bank manifest."""
    payload = load_yaml(path)
    if payload.get("schema_version") != QUESTION_BANK_SCHEMA:
        raise ProductAnswerError(f"invalid product question bank schema: {path}")
    questions = payload.get("questions")
    if not isinstance(questions, dict) or not questions:
        raise ProductAnswerError(f"product question bank has no questions: {path}")
    return payload


def load_claim_evidence(path: Path) -> dict[str, Any]:
    """Load and validate the product claim evidence manifest."""
    payload = load_yaml(path)
    if payload.get("schema_version") != CLAIM_EVIDENCE_SCHEMA:
        raise ProductAnswerError(f"invalid product claim evidence schema: {path}")
    claims = payload.get("claims")
    if not isinstance(claims, dict) or not claims:
        raise ProductAnswerError(f"product claim evidence has no claims: {path}")
    return payload


def _normalize(text: str) -> str:
    return " ".join(text.casefold().strip().split())


def _contains(haystack: str, needle: str) -> bool:
    return _normalize(needle) in _normalize(haystack)


def _score_question(question_text: str, question_id: str, row: dict[str, Any]) -> int:
    normalized = _normalize(question_text)
    score = 0
    if normalized == _normalize(question_id):
        score += 100
    for alias in row.get("aliases", []) or []:
        alias_text = str(alias)
        if normalized == _normalize(alias_text):
            score += 90
        elif _contains(question_text, alias_text):
            score += 35
    for keyword in row.get("keywords", []) or []:
        if _contains(question_text, str(keyword)):
            score += 10
    return score


def select_question(
    question_bank: dict[str, Any],
    question_text: str | None = None,
    question_id: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """Select a question row by explicit id or best keyword/alias match."""
    questions = question_bank["questions"]
    if question_id:
        if question_id not in questions:
            raise ProductAnswerError(f"unknown question id: {question_id}")
        return question_id, questions[question_id]

    if not question_text:
        default_id = question_bank.get("default_question_id")
        if isinstance(default_id, str) and default_id in questions:
            return default_id, questions[default_id]
        raise ProductAnswerError("question text or --question-id is required")

    scored = sorted(
        ((_score_question(question_text, qid, row), qid, row) for qid, row in questions.items()),
        key=lambda item: (-item[0], item[1]),
    )
    best_score, best_id, best_row = scored[0]
    if best_score <= 0:
        available = ", ".join(sorted(questions))
        raise ProductAnswerError(f"no product question matched; available question ids: {available}")
    return best_id, best_row


def _status_rank(status: str, status_order: list[str]) -> int:
    try:
        return status_order.index(status)
    except ValueError:
        return len(status_order)


def _lowest_status(statuses: list[str], status_order: list[str]) -> str:
    if not statuses:
        return "unknown"
    return max(statuses, key=lambda status: _status_rank(status, status_order))


def _existing_path(project_dir: Path, rel: str) -> bool:
    return (project_dir / rel).exists()


def _claim_summary(claim_id: str, claim: dict[str, Any], project_dir: Path) -> dict[str, Any]:
    evidence = [str(item) for item in claim.get("evidence", []) or []]
    missing = [rel for rel in evidence if not _existing_path(project_dir, rel)]
    return {
        "claim_id": claim_id,
        "status": str(claim.get("status", "unknown")),
        "maturity": str(claim.get("maturity", "unknown")),
        "confidence": float(claim.get("confidence", 0.0) or 0.0),
        "summary": str(claim.get("summary", "")),
        "approved_wording": str(claim.get("approved_wording", "")),
        "evidence": evidence,
        "missing_evidence": missing,
        "boundaries": [str(item) for item in claim.get("boundaries", []) or []],
    }


def build_answer(
    project_dir: Path,
    question_text: str | None = None,
    question_id: str | None = None,
    question_bank_path: Path | None = None,
    claim_evidence_path: Path | None = None,
    strict: bool = False,
) -> dict[str, Any]:
    """Build an evidence-backed product answer report."""
    root = project_dir.resolve()
    bank_path = question_bank_path or root / "manifests" / "product-question-bank.yaml"
    evidence_path = claim_evidence_path or root / "manifests" / "product-claim-evidence.yaml"
    bank = load_question_bank(bank_path)
    evidence_manifest = load_claim_evidence(evidence_path)
    selected_id, selected = select_question(bank, question_text, question_id)

    approved_sources = [str(item) for item in selected.get("approved_sources", []) or []]
    missing_sources = [rel for rel in approved_sources if not _existing_path(root, rel)]
    claims_manifest = evidence_manifest["claims"]
    claim_ids = [str(item) for item in selected.get("related_claims", []) or []]
    missing_claim_ids = [claim_id for claim_id in claim_ids if claim_id not in claims_manifest]
    claim_rows = [
        _claim_summary(claim_id, claims_manifest[claim_id], root)
        for claim_id in claim_ids
        if claim_id in claims_manifest
    ]
    all_missing_evidence = sorted(
        {rel for claim in claim_rows for rel in claim["missing_evidence"]} | set(missing_sources)
    )
    status_order = [str(item) for item in evidence_manifest.get("status_order", DEFAULT_STATUS_ORDER)]
    claim_status = _lowest_status([claim["status"] for claim in claim_rows], status_order)
    has_blocked_claim = any(claim["status"] == "blocked" for claim in claim_rows)
    has_aspirational_claim = any(claim["status"] == "aspirational" for claim in claim_rows)

    finding_messages: list[str] = []
    if missing_claim_ids:
        finding_messages.append(f"missing claim ids: {', '.join(missing_claim_ids)}")
    if all_missing_evidence:
        finding_messages.append(f"missing evidence paths: {', '.join(all_missing_evidence)}")
    if has_blocked_claim:
        finding_messages.append("selected answer references blocked claims")
    if strict and has_aspirational_claim:
        finding_messages.append("strict answer references aspirational claims")

    status = "pass"
    if finding_messages:
        status = "fail"
    elif has_aspirational_claim or claim_status in {"partial", "partial-real"}:
        status = "warn"

    confidences = [claim["confidence"] for claim in claim_rows if claim["confidence"] > 0]
    confidence = round(sum(confidences) / len(confidences), 2) if confidences else 0.0
    if all_missing_evidence or missing_claim_ids:
        confidence = min(confidence, 0.5)

    trust_score = int(round(confidence * 100))
    if status == "fail":
        trust_status = "LOW"
    elif trust_score >= 80 and status == "pass":
        trust_status = "HIGH"
    else:
        trust_status = "MEDIUM"

    return {
        "schema_version": REPORT_SCHEMA,
        "adr": "ADR-280",
        "status": status,
        "question": question_text or selected_id,
        "question_id": selected_id,
        "category": str(selected.get("category", "unknown")),
        "answer_short": str(selected.get("answer_short", "")),
        "answer_long": str(selected.get("answer_long", "")),
        "recommended_pitch": str(selected.get("recommended_pitch", "")),
        "claim_status": claim_status,
        "confidence": confidence,
        "trust_report": {
            "score": trust_score,
            "status": trust_status,
            "evidence_count": len(set(approved_sources + [rel for claim in claim_rows for rel in claim["evidence"]])) ,
            "uncertainty_count": len(selected.get("gaps", []) or []) + len(finding_messages),
        },
        "approved_sources": approved_sources,
        "claims": claim_rows,
        "unsafe_claims_to_avoid": [str(item) for item in selected.get("unsafe_claims_to_avoid", []) or []],
        "gaps": [str(item) for item in selected.get("gaps", []) or []],
        "findings": finding_messages,
        "strict": strict,
        "manifests": {
            "question_bank": str(bank_path),
            "claim_evidence": str(evidence_path),
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    """Render a product answer report as concise Markdown."""
    evidence = sorted({rel for rel in report["approved_sources"]})
    lines = [
        f"# Product Answer: {report['question_id']}",
        "",
        f"**Status:** {report['status']}  ",
        f"**Claim status:** {report['claim_status']}  ",
        f"**Confidence:** {report['confidence']}",
        "",
        "## Short answer",
        "",
        report["answer_short"],
        "",
        "## Recommended pitch",
        "",
        f"> {report['recommended_pitch']}",
        "",
        "## Longer answer",
        "",
        report["answer_long"],
        "",
        "## Evidence",
    ]
    lines.extend(f"- `{rel}`" for rel in evidence)
    lines.extend(["", "## Unsafe claims to avoid"])
    lines.extend(f"- {claim}" for claim in report["unsafe_claims_to_avoid"])
    lines.extend(["", "## Gaps"])
    lines.extend(f"- {gap}" for gap in report["gaps"])
    if report["findings"]:
        lines.extend(["", "## Findings"])
        lines.extend(f"- {finding}" for finding in report["findings"])
    trust = report["trust_report"]
    lines.extend([
        "",
        f"TRUST_REPORT: SCORE={trust['score']} STATUS={trust['status']} EVIDENCE={trust['evidence_count']} UNCERTAINTIES={trust['uncertainty_count']}",
    ])
    return "\n".join(lines) + "\n"

"""ADR-280/282 product question-to-evidence primitive and answer-card cache."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

QUESTION_BANK_SCHEMA = "product-question-bank/v1"
CLAIM_EVIDENCE_SCHEMA = "product-claim-evidence/v1"
REPORT_SCHEMA = "product-answer-report/v1"
CARD_SCHEMA = "product-answer-card/v1"
INDEX_SCHEMA = "product-answer-routing-index/v1"
LEDGER_SCHEMA = "product-answer-freshness-ledger/v1"
DEFAULT_STATUS_ORDER = ["real", "partial-real", "partial", "aspirational", "blocked"]
DEFAULT_CACHE_DIR = Path(".cognitive-os") / "product-answers"


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
    normalized_haystack = _normalize(haystack)
    normalized_needle = _normalize(needle)
    if not normalized_needle:
        return False
    pattern = r"(?<![a-z0-9])" + re.escape(normalized_needle) + r"(?![a-z0-9])"
    return re.search(pattern, normalized_haystack) is not None


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


def _relative_to_project(project_dir: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(project_dir.resolve()))
    except ValueError:
        return str(path)


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
            "evidence_count": len(set(approved_sources + [rel for claim in claim_rows for rel in claim["evidence"]])),
            "uncertainty_count": len(selected.get("gaps", []) or []) + len(finding_messages),
        },
        "approved_sources": approved_sources,
        "claims": claim_rows,
        "unsafe_claims_to_avoid": [str(item) for item in selected.get("unsafe_claims_to_avoid", []) or []],
        "gaps": [str(item) for item in selected.get("gaps", []) or []],
        "findings": finding_messages,
        "strict": strict,
        "cache": {"mode": "live", "freshness": "not_checked"},
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
    cache = report.get("cache") or {}
    if cache.get("mode") == "card":
        lines.extend([
            "",
            "## Cache",
            "",
            f"Using fresh product answer card: `{cache.get('card_path')}`",
            f"Source freshness: {cache.get('freshness')}",
        ])
    lines.extend([
        "",
        f"TRUST_REPORT: SCORE={trust['score']} STATUS={trust['status']} EVIDENCE={trust['evidence_count']} UNCERTAINTIES={trust['uncertainty_count']}",
    ])
    return "\n".join(lines) + "\n"


def cache_dir(project_dir: Path, override: Path | None = None) -> Path:
    """Return the ADR-282 product answer cache directory."""
    return override if override is not None else project_dir / DEFAULT_CACHE_DIR


def card_paths(project_dir: Path, question_id: str, cache_dir_override: Path | None = None) -> dict[str, Path]:
    """Return all ADR-282 paths for a question id."""
    directory = cache_dir(project_dir, cache_dir_override)
    return {
        "dir": directory,
        "markdown": directory / f"{question_id}.md",
        "json": directory / f"{question_id}.json",
        "index": directory / "index.yaml",
        "ledger": directory / "freshness-ledger.jsonl",
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def answer_source_paths(project_dir: Path, report: dict[str, Any]) -> list[str]:
    """Return canonical source paths that make a card stale when changed."""
    rels: set[str] = set(report.get("approved_sources", []) or [])
    for claim in report.get("claims", []) or []:
        rels.update(str(item) for item in claim.get("evidence", []) or [])
    manifests = report.get("manifests", {}) or {}
    for manifest_path in manifests.values():
        rels.add(_relative_to_project(project_dir, Path(str(manifest_path))))
    return sorted(rels)


def compute_source_hashes(project_dir: Path, source_paths: list[str]) -> dict[str, str]:
    """Compute sha256 hashes for source paths relative to ``project_dir``."""
    hashes: dict[str, str] = {}
    for rel in sorted(set(source_paths)):
        path = project_dir / rel
        hashes[rel] = _sha256_file(path) if path.exists() and path.is_file() else "MISSING"
    return hashes


def card_metadata(project_dir: Path, report: dict[str, Any]) -> dict[str, Any]:
    """Build frontmatter metadata for an ADR-282 answer card."""
    source_paths = answer_source_paths(project_dir, report)
    trust = report.get("trust_report", {}) or {}
    return {
        "schema_version": CARD_SCHEMA,
        "adr": "ADR-282",
        "question_id": report["question_id"],
        "last_generated": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": "fresh",
        "answer_status": report["status"],
        "claim_status": report["claim_status"],
        "confidence": report["confidence"],
        "trust_score": trust.get("score", 0),
        "source_hashes": compute_source_hashes(project_dir, source_paths),
    }


def _frontmatter_markdown(metadata: dict[str, Any], body: str) -> str:
    return "---\n" + yaml.safe_dump(metadata, sort_keys=True, allow_unicode=True) + "---\n" + body


def _split_frontmatter(markdown: str) -> tuple[dict[str, Any], str]:
    if not markdown.startswith("---\n"):
        return {}, markdown
    _, rest = markdown.split("---\n", 1)
    raw, body = rest.split("---\n", 1)
    payload = yaml.safe_load(raw) or {}
    if not isinstance(payload, dict):
        return {}, body
    return payload, body


def card_freshness(project_dir: Path, question_id: str, cache_dir_override: Path | None = None) -> dict[str, Any]:
    """Check whether a materialized answer card is fresh."""
    paths = card_paths(project_dir, question_id, cache_dir_override)
    if not paths["markdown"].exists() or not paths["json"].exists():
        return {
            "schema_version": LEDGER_SCHEMA,
            "question_id": question_id,
            "freshness": "missing",
            "card_path": str(paths["markdown"]),
            "changed_sources": [],
            "missing_sources": [],
        }
    metadata, _body = _split_frontmatter(paths["markdown"].read_text(encoding="utf-8"))
    stored_hashes = metadata.get("source_hashes", {}) if isinstance(metadata, dict) else {}
    if not isinstance(stored_hashes, dict):
        stored_hashes = {}
    current_hashes = compute_source_hashes(project_dir, [str(item) for item in stored_hashes])
    changed = sorted(rel for rel, old_hash in stored_hashes.items() if current_hashes.get(rel) != old_hash)
    missing = sorted(rel for rel, new_hash in current_hashes.items() if new_hash == "MISSING")
    freshness = "fresh" if not changed and not missing else "stale"
    return {
        "schema_version": LEDGER_SCHEMA,
        "question_id": question_id,
        "freshness": freshness,
        "card_path": str(paths["markdown"]),
        "json_path": str(paths["json"]),
        "changed_sources": changed,
        "missing_sources": missing,
        "stored_source_count": len(stored_hashes),
        "checked_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }


def _write_ledger_row(paths: dict[str, Path], row: dict[str, Any]) -> None:
    paths["ledger"].parent.mkdir(parents=True, exist_ok=True)
    with paths["ledger"].open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_answer_card(
    project_dir: Path,
    report: dict[str, Any],
    cache_dir_override: Path | None = None,
) -> dict[str, Any]:
    """Materialize a product answer report as Markdown, JSON, and freshness ledger row."""
    paths = card_paths(project_dir, report["question_id"], cache_dir_override)
    paths["dir"].mkdir(parents=True, exist_ok=True)
    metadata = card_metadata(project_dir, report)
    body = render_markdown({**report, "cache": {"mode": "materialized", "freshness": "fresh"}})
    paths["markdown"].write_text(_frontmatter_markdown(metadata, body), encoding="utf-8")
    report_with_cache = {
        **report,
        "adr": "ADR-282",
        "cache": {
            "mode": "materialized",
            "freshness": "fresh",
            "card_path": str(paths["markdown"]),
            "json_path": str(paths["json"]),
            "source_hashes": metadata["source_hashes"],
        },
    }
    paths["json"].write_text(json.dumps(report_with_cache, indent=2, sort_keys=True), encoding="utf-8")
    ledger_row = {
        "schema_version": LEDGER_SCHEMA,
        "event": "refresh",
        "question_id": report["question_id"],
        "freshness": "fresh",
        "card_path": str(paths["markdown"]),
        "json_path": str(paths["json"]),
        "source_count": len(metadata["source_hashes"]),
        "generated_at": metadata["last_generated"],
    }
    _write_ledger_row(paths, ledger_row)
    return report_with_cache


def refresh_routing_index(
    project_dir: Path,
    question_bank_path: Path | None = None,
    cache_dir_override: Path | None = None,
) -> dict[str, Any]:
    """Write a compact ADR-282 routing index for product answer cards."""
    root = project_dir.resolve()
    bank_path = question_bank_path or root / "manifests" / "product-question-bank.yaml"
    bank = load_question_bank(bank_path)
    directory = cache_dir(root, cache_dir_override)
    directory.mkdir(parents=True, exist_ok=True)
    entries: dict[str, Any] = {}
    for question_id, row in sorted(bank["questions"].items()):
        paths = card_paths(root, question_id, cache_dir_override)
        freshness = card_freshness(root, question_id, cache_dir_override)
        entries[question_id] = {
            "card": _relative_to_project(root, paths["markdown"]),
            "json": _relative_to_project(root, paths["json"]),
            "aliases": [str(item) for item in row.get("aliases", []) or []],
            "keywords": [str(item) for item in row.get("keywords", []) or []],
            "max_answer_tokens": int(row.get("max_answer_tokens", 700) or 700),
            "freshness": freshness["freshness"],
        }
    index = {
        "schema_version": INDEX_SCHEMA,
        "adr": "ADR-282",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "entries": entries,
    }
    (directory / "index.yaml").write_text(yaml.safe_dump(index, sort_keys=True, allow_unicode=True), encoding="utf-8")
    return index


def refresh_answer_cards(
    project_dir: Path,
    question_id: str | None = None,
    question_bank_path: Path | None = None,
    claim_evidence_path: Path | None = None,
    cache_dir_override: Path | None = None,
    strict: bool = False,
) -> dict[str, Any]:
    """Regenerate one or all ADR-282 answer cards."""
    root = project_dir.resolve()
    bank_path = question_bank_path or root / "manifests" / "product-question-bank.yaml"
    bank = load_question_bank(bank_path)
    question_ids = [question_id] if question_id else sorted(bank["questions"])
    reports = []
    for qid in question_ids:
        report = build_answer(
            root,
            question_id=qid,
            question_bank_path=question_bank_path,
            claim_evidence_path=claim_evidence_path,
            strict=strict,
        )
        reports.append(write_answer_card(root, report, cache_dir_override))
    index = refresh_routing_index(root, bank_path, cache_dir_override)
    return {
        "schema_version": "product-answer-refresh-report/v1",
        "adr": "ADR-282",
        "status": "pass" if all(report["status"] != "fail" for report in reports) else "fail",
        "refreshed_count": len(reports),
        "questions": [report["question_id"] for report in reports],
        "cards": [report["cache"]["card_path"] for report in reports],
        "index": _relative_to_project(root, cache_dir(root, cache_dir_override) / "index.yaml"),
        "index_entry_count": len(index["entries"]),
    }


def load_cached_answer(
    project_dir: Path,
    question_text: str | None = None,
    question_id: str | None = None,
    question_bank_path: Path | None = None,
    cache_dir_override: Path | None = None,
) -> dict[str, Any] | None:
    """Return a fresh cached answer report when available, otherwise None."""
    root = project_dir.resolve()
    bank_path = question_bank_path or root / "manifests" / "product-question-bank.yaml"
    bank = load_question_bank(bank_path)
    selected_id, _selected = select_question(bank, question_text, question_id)
    freshness = card_freshness(root, selected_id, cache_dir_override)
    if freshness["freshness"] != "fresh":
        return None
    paths = card_paths(root, selected_id, cache_dir_override)
    report = json.loads(paths["json"].read_text(encoding="utf-8"))
    report["question"] = question_text or question_id or selected_id
    report["cache"] = {
        **(report.get("cache") or {}),
        "mode": "card",
        "freshness": "fresh",
        "card_path": str(paths["markdown"]),
        "json_path": str(paths["json"]),
    }
    return report

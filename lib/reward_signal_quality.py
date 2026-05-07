"""Reward signal quality validation for ADR-204.

Rows that can influence routing, promotion, demotion, or maintainer proposals are
classified before rollups. Only ``valid`` rows are eligible for scoring.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml  # type: ignore[import]
except Exception:  # pragma: no cover - minimal env fallback only
    yaml = None


@dataclass(frozen=True)
class SignalValidation:
    stream: str
    status: str
    eligible_for_rollup: bool
    reasons: list[str] = field(default_factory=list)
    subject_id: str | None = None
    line_number: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "stream": self.stream,
            "status": self.status,
            "eligible_for_rollup": self.eligible_for_rollup,
            "reasons": self.reasons,
            "subject_id": self.subject_id,
            "line_number": self.line_number,
        }


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_contract(path: Path | None = None) -> dict[str, Any]:
    contract_path = path or repo_root() / "manifests" / "reward-signal-contract.yaml"
    if yaml is None:
        raise RuntimeError("PyYAML is required to read reward signal contract")
    data = yaml.safe_load(contract_path.read_text(encoding="utf-8")) or {}
    if data.get("schema_version") != "reward-signal-contract/v1":
        raise ValueError(f"invalid reward signal contract: {contract_path}")
    return data


def known_skill_ids(project_dir: Path, contract: dict[str, Any]) -> set[str]:
    sources = (contract.get("known_subject_sources", {}) or {}).get("skills_dirs", []) or []
    ids: set[str] = set()
    for source in sources:
        root = project_dir / str(source)
        if not root.exists():
            continue
        for child in root.iterdir():
            if child.is_dir() and (child / "SKILL.md").exists():
                ids.add(child.name)
    return ids


def _is_missing(value: Any) -> bool:
    return value is None or value == ""


def _has_confidence_source(row: dict[str, Any], stream_cfg: dict[str, Any]) -> bool:
    for field_name in stream_cfg.get("confidence_source_fields", []) or []:
        value = row.get(field_name)
        if isinstance(value, list) and value:
            return True
        if isinstance(value, str) and value.strip():
            return True
        if value not in (None, "", []):
            return True
    return False


def validate_row(stream: str, row: dict[str, Any], stream_cfg: dict[str, Any], known_subjects: set[str] | None = None, line_number: int | None = None) -> SignalValidation:
    reasons: list[str] = []
    status = "valid"

    for field_name in stream_cfg.get("required_fields", []) or []:
        if _is_missing(row.get(field_name)):
            reasons.append(f"missing_required_field:{field_name}")
            status = "corrupt"

    subject_field = stream_cfg.get("subject_field")
    subject_id = row.get(subject_field) if subject_field else None
    subject_text = str(subject_id) if subject_id is not None else None

    if stream_cfg.get("subject_type") == "skill":
        if not isinstance(subject_id, str) or not subject_id.strip():
            reasons.append("missing_skill_id")
            status = "corrupt"
        elif known_subjects is not None and subject_id not in known_subjects:
            reasons.append("unknown_skill_id")
            status = "corrupt"

    outcome_field = stream_cfg.get("outcome_field")
    if outcome_field and outcome_field in row and not isinstance(row.get(outcome_field), bool):
        reasons.append(f"non_boolean_outcome:{outcome_field}")
        status = "corrupt"

    for field_name, bounds in (stream_cfg.get("numeric_fields", {}) or {}).items():
        if field_name not in row:
            continue
        value = row.get(field_name)
        if not isinstance(value, (int, float)):
            reasons.append(f"non_numeric_field:{field_name}")
            status = "corrupt"
            continue
        if "min" in bounds and value < bounds["min"]:
            reasons.append(f"numeric_below_min:{field_name}")
            status = "corrupt"
        if "max" in bounds and value > bounds["max"]:
            reasons.append(f"numeric_above_max:{field_name}")
            status = "corrupt"

    score_field = stream_cfg.get("score_field")
    if score_field and score_field in row:
        score = row.get(score_field)
        if not isinstance(score, (int, float)):
            reasons.append(f"non_numeric_score:{score_field}")
            status = "corrupt"
        else:
            if score < stream_cfg.get("score_min", 0) or score > stream_cfg.get("score_max", 100):
                reasons.append(f"score_out_of_range:{score_field}")
                status = "corrupt"
            default_score = 75
            if score == default_score and not _has_confidence_source(row, stream_cfg) and status != "corrupt":
                reasons.append("default_trust_score_without_evidence")
                status = "suspect"

    eligible = status == "valid"
    return SignalValidation(stream, status, eligible, reasons, subject_text, line_number)


def read_jsonl(path: Path) -> Iterable[tuple[int, dict[str, Any] | None, str | None]]:
    if not path.exists():
        return
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                yield line_number, None, f"invalid_json:{exc.msg}"
                continue
            if not isinstance(payload, dict):
                yield line_number, None, "non_object_json"
                continue
            yield line_number, payload, None


def audit_stream(project_dir: Path, contract: dict[str, Any], stream: str, limit: int | None = None) -> list[SignalValidation]:
    stream_cfg = (contract.get("streams", {}) or {}).get(stream)
    if not isinstance(stream_cfg, dict):
        raise ValueError(f"unknown reward signal stream: {stream}")
    path = project_dir / str(stream_cfg.get("path"))
    known_subjects = known_skill_ids(project_dir, contract) if stream_cfg.get("known_subject_source") == "skills_dirs" else None
    results: list[SignalValidation] = []
    for index, (line_number, row, error) in enumerate(read_jsonl(path) or [], 1):
        if limit is not None and index > limit:
            break
        if error is not None:
            results.append(SignalValidation(stream, "corrupt", False, [error], None, line_number))
            continue
        assert row is not None
        results.append(validate_row(stream, row, stream_cfg, known_subjects, line_number))
    return results


def summarize(results: Iterable[SignalValidation]) -> dict[str, int]:
    summary = {"valid": 0, "suspect": 0, "corrupt": 0, "total": 0, "eligible_for_rollup": 0}
    for result in results:
        summary["total"] += 1
        summary[result.status] += 1
        if result.eligible_for_rollup:
            summary["eligible_for_rollup"] += 1
    return summary


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def repair_stream(project_dir: Path, contract: dict[str, Any], stream: str, *, execute: bool = False, archive_root: Path | None = None) -> dict[str, Any]:
    """Archive-first cleanup for ADR-204 reward streams.

    Invalid/suspect rows are copied to recovery before the source JSONL is
    rewritten with only rollup-eligible rows. Dry-run reports the planned split.
    """
    stream_cfg = (contract.get("streams", {}) or {}).get(stream)
    if not isinstance(stream_cfg, dict):
        raise ValueError(f"unknown reward signal stream: {stream}")
    path = project_dir / str(stream_cfg.get("path"))
    results = audit_stream(project_dir, contract, stream)
    eligible_lines = {result.line_number for result in results if result.eligible_for_rollup}
    quarantined_lines = {result.line_number for result in results if not result.eligible_for_rollup}
    existing_lines = path.read_text(encoding="utf-8", errors="replace").splitlines() if path.exists() else []
    archive_dir = archive_root or project_dir / ".cognitive-os" / "recovery" / f"reward-signal-cleanup-{utc_stamp()}"
    archive_path = archive_dir / f"{stream}.quarantined.jsonl"
    kept_path = archive_dir / f"{stream}.kept.jsonl"

    if execute and existing_lines:
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_path.write_text(
            "\n".join(line for idx, line in enumerate(existing_lines, 1) if idx in quarantined_lines) + ("\n" if quarantined_lines else ""),
            encoding="utf-8",
        )
        kept = [line for idx, line in enumerate(existing_lines, 1) if idx in eligible_lines]
        kept_path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
        tmp.replace(path)

    return {
        "stream": stream,
        "path": str(path),
        "execute": bool(execute),
        "archive_path": str(archive_path),
        "kept_path": str(kept_path),
        "summary_before": summarize(results),
        "kept_rows": len(eligible_lines),
        "quarantined_rows": len(quarantined_lines),
    }


def repair_streams(project_dir: Path, contract: dict[str, Any], streams: list[str] | None = None, *, execute: bool = False) -> dict[str, Any]:
    selected = streams or sorted((contract.get("streams", {}) or {}).keys())
    archive_dir = project_dir / ".cognitive-os" / "recovery" / f"reward-signal-cleanup-{utc_stamp()}"
    repairs = [repair_stream(project_dir, contract, stream, execute=execute, archive_root=archive_dir) for stream in selected]
    return {
        "schema_version": "reward-signal-repair/v1",
        "project_dir": str(project_dir),
        "execute": bool(execute),
        "archive_dir": str(archive_dir),
        "streams": repairs,
        "summary": {
            "kept_rows": sum(item["kept_rows"] for item in repairs),
            "quarantined_rows": sum(item["quarantined_rows"] for item in repairs),
        },
    }

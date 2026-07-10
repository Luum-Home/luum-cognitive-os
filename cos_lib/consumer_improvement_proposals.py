# SCOPE: both
"""Consumer-project improvement proposal exchange.

Exports sanitized improvement signals from a project that implements Cognitive OS
and imports them upstream as propose-only review artifacts. This module does not
mutate runtime hooks, skills, rules, manifests, Engram, or Obsidian vaults.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "cos-consumer-improvement-proposals.v1"
_ALLOWED_ACTIONS = {"project-local", "upstream-candidate", "harness-gap", "docs-only", "reject"}
_SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|token|secret|password|passwd|bearer)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"(?i)authorization:\s*bearer\s+[^\s,;]+"),
    re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"ghp_[A-Za-z0-9_]{12,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{12,}"),
    re.compile(r"/(?:Users|home)/[^/\s]+"),
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            if "payload" in payload and isinstance(payload.get("payload"), dict):
                flat = dict(payload["payload"])
                flat.setdefault("timestamp", payload.get("timestamp", ""))
                rows.append(flat)
            else:
                rows.append(payload)
    return rows


def sanitize_text(value: Any, *, limit: int = 240) -> str:
    """Return a bounded text excerpt with common secret/path patterns redacted."""
    text = str(value or "").replace("\n", " ").replace("\r", " ")
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        return text[: limit - 1].rstrip() + "…"
    return text


def _proposal_id(project: str, action: str, subject: str, evidence: dict[str, Any]) -> str:
    raw = json.dumps({"project": project, "action": action, "subject": subject, "evidence": evidence}, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _skill_exists(project_root: Path, skill: str) -> bool:
    candidates = [
        project_root / "skills" / skill / "SKILL.md",
        project_root / ".cognitive-os" / "skills" / "cos" / skill / "SKILL.md",
        project_root / ".cognitive-os" / "skills" / skill / "SKILL.md",
    ]
    return any(path.exists() for path in candidates)


def _make_proposal(
    *,
    project: str,
    action: str,
    title: str,
    summary: str,
    primitive_id: str | None,
    evidence: dict[str, Any],
    required_tests: list[str] | None = None,
) -> dict[str, Any]:
    subject = primitive_id or title
    return {
        "proposal_id": _proposal_id(project, action, subject, evidence),
        "action": action,
        "title": title,
        "summary": sanitize_text(summary, limit=500),
        "primitive_id": primitive_id or "",
        "evidence": evidence,
        "required_tests": required_tests or [],
        "human_approval_required": True,
        "runtime_effect": "none",
        "blocked_actions": [
            "auto_merge",
            "auto_promote_core_or_team",
            "copy_credentials",
            "import_raw_vault",
            "mutate_consumer_runtime",
        ],
    }


def _skill_feedback_proposals(project_root: Path, project: str, threshold: int) -> list[dict[str, Any]]:
    rows = _read_jsonl(project_root / ".cognitive-os" / "metrics" / "skill-feedback.jsonl")
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        skill = sanitize_text(row.get("skill", ""), limit=120)
        if not skill:
            continue
        counts[skill]["success" if row.get("success") is True else "failure"] += 1
    proposals: list[dict[str, Any]] = []
    for skill, counter in sorted(counts.items()):
        failures = int(counter["failure"])
        if failures < threshold:
            continue
        action = "upstream-candidate" if _skill_exists(project_root, skill) else "project-local"
        proposals.append(
            _make_proposal(
                project=project,
                action=action,
                title=f"Review degraded skill {skill}",
                summary=f"Skill {skill} reported {failures} failures and {int(counter['success'])} successes in consumer metrics.",
                primitive_id=f"skills/{skill}",
                evidence={"source": "skill-feedback.jsonl", "failure_count": failures, "success_count": int(counter["success"])},
                required_tests=["run project-specific skill regression or /optimize-skill before promotion"],
            )
        )
    return proposals


def _error_learning_proposals(project_root: Path, project: str, threshold: int) -> list[dict[str, Any]]:
    rows = _read_jsonl(project_root / ".cognitive-os" / "metrics" / "error-learning.jsonl")
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        error_type = sanitize_text(row.get("type") or row.get("error_type") or "unknown", limit=80)
        service = sanitize_text(row.get("service") or row.get("target") or "unknown", limit=120)
        grouped[(error_type, service)].append(row)
    proposals: list[dict[str, Any]] = []
    for (error_type, service), events in sorted(grouped.items()):
        if len(events) < threshold:
            continue
        excerpts = [sanitize_text(event.get("message") or event.get("error") or event.get("output"), limit=180) for event in events[:3]]
        proposals.append(
            _make_proposal(
                project=project,
                action="project-local",
                title=f"Capture repeated {error_type} pattern for {service}",
                summary=f"Consumer project saw {len(events)} repeated {error_type} events for {service}; start as project-local repair evidence before upstreaming.",
                primitive_id="",
                evidence={"source": "error-learning.jsonl", "error_type": error_type, "service": service, "count": len(events), "sanitized_excerpts": excerpts},
                required_tests=["prove the repair in the consumer project before proposing upstream"],
            )
        )
    return proposals


def _repair_queue_proposals(project_root: Path, project: str) -> list[dict[str, Any]]:
    rows = _read_jsonl(project_root / ".cognitive-os" / "metrics" / "skill-repair-queue.jsonl")
    proposals: list[dict[str, Any]] = []
    for row in rows:
        if row.get("status", "pending") != "pending":
            continue
        skill = sanitize_text(row.get("skill", ""), limit=120)
        if not skill:
            continue
        action = "upstream-candidate" if _skill_exists(project_root, skill) else "project-local"
        proposals.append(
            _make_proposal(
                project=project,
                action=action,
                title=f"Process pending repair signal for {skill}",
                summary=f"Skill repair queue recommends {row.get('suggested_action', 'investigate')} for {skill}.",
                primitive_id=f"skills/{skill}",
                evidence={"source": "skill-repair-queue.jsonl", "failure_count": int(row.get("failure_count", 0) or 0), "suggested_action": sanitize_text(row.get("suggested_action", "investigate"), limit=80), "sample_errors": [sanitize_text(x, limit=160) for x in row.get("sample_errors", [])[:3] if isinstance(row.get("sample_errors", []), list)]},
                required_tests=["/optimize-skill or project-local equivalent, then re-run affected workflow"],
            )
        )
    return proposals


def _acc_gap_proposals(project_root: Path, project: str) -> list[dict[str, Any]]:
    path = project_root / "docs" / "acc" / "latest.json"
    if not path.exists():
        return []
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    findings = report.get("findings", [])
    if not isinstance(findings, list):
        return []
    proposals: list[dict[str, Any]] = []
    for finding in findings[:20]:
        if not isinstance(finding, dict):
            continue
        status = str(finding.get("mapping_status") or finding.get("status") or "")
        if status not in {"missing", "partial", "unverified", "stale", "overexposed", "fail", "warn"}:
            continue
        fid = sanitize_text(finding.get("id") or finding.get("capability_id") or finding.get("title") or "acc-gap", limit=140)
        proposals.append(
            _make_proposal(
                project=project,
                action="harness-gap",
                title=f"Review consumer ACC gap {fid}",
                summary=f"Consumer/project ACC report surfaced {status} for {fid}.",
                primitive_id=sanitize_text(finding.get("primitive_id") or finding.get("path") or "", limit=180),
                evidence={"source": "docs/07-Capabilities/acc/latest.json", "status": status, "finding_id": fid},
                required_tests=["python3 scripts/acc_pipeline.py --project-dir . --refresh"],
            )
        )
    return proposals


def build_consumer_improvement_bundle(
    project_root: Path,
    *,
    project: str,
    profile: str = "core",
    since: str = "30d",
    reporter: str = "consumer-project",
    producer_type: str = "human",
    producer_identity: str | None = None,
    source_repo: str | None = None,
    machine_id: str | None = None,
    threshold: int = 3,
) -> dict[str, Any]:
    """Build a sanitized, portable, propose-only improvement proposal bundle."""
    proposals: list[dict[str, Any]] = []
    proposals.extend(_skill_feedback_proposals(project_root, project, threshold))
    proposals.extend(_error_learning_proposals(project_root, project, threshold))
    proposals.extend(_repair_queue_proposals(project_root, project))
    proposals.extend(_acc_gap_proposals(project_root, project))

    deduped: dict[str, dict[str, Any]] = {proposal["proposal_id"]: proposal for proposal in proposals}
    normalized = sorted(deduped.values(), key=lambda item: (item["action"], item["proposal_id"]))
    action_counts = Counter(proposal["action"] for proposal in normalized)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "proposals_available" if normalized else "pass",
        "mode": "propose_only",
        "runtime_effect": "none",
        "project": project,
        "profile": profile,
        "since": since,
        "generated_at": _utc_now(),
        "proposal_count": len(normalized),
        "action_counts": dict(sorted(action_counts.items())),
        "proposals": normalized,
        "provenance": {
            "producer": {
                "type": producer_type,
                "identity": producer_identity or reporter,
                "repo": source_repo or "",
                "machine_id": machine_id or "unknown",
                "generated_at": _utc_now(),
            }
        },
        "policy": {
            "human_approval_required": True,
            "auto_merge": False,
            "auto_promote_core_or_team": False,
            "raw_vault_export": False,
            "credential_copy": False,
        },
    }


def write_consumer_improvement_bundle(bundle: dict[str, Any], output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def import_consumer_improvement_bundle(project_root: Path, bundle_path: Path) -> dict[str, Any]:
    """Import a consumer proposal bundle as a review artifact only."""
    try:
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"status": "fail", "reason": str(exc), "runtime_effect": "none"}
    if bundle.get("schema_version") != SCHEMA_VERSION:
        return {"status": "fail", "reason": "unsupported schema_version", "runtime_effect": "none"}
    proposals = bundle.get("proposals", [])
    if not isinstance(proposals, list):
        return {"status": "fail", "reason": "proposals must be a list", "runtime_effect": "none"}
    invalid = [p for p in proposals if not isinstance(p, dict) or p.get("action") not in _ALLOWED_ACTIONS or p.get("runtime_effect") != "none"]
    if invalid:
        return {"status": "fail", "reason": "invalid proposal action or runtime_effect", "invalid_count": len(invalid), "runtime_effect": "none"}

    target_dir = project_root / ".cognitive-os" / "improvements" / "proposals"
    target_dir.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9-]", "-", str(bundle.get("project", "consumer")).lower()).strip("-") or "consumer"
    target = target_dir / f"consumer-improvement-proposals-{slug}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    artifact = {
        "schema_version": SCHEMA_VERSION,
        "status": "proposed",
        "runtime_effect": "none",
        "source_bundle": str(bundle_path),
        "imported_at": _utc_now(),
        "project": bundle.get("project", ""),
        "profile": bundle.get("profile", ""),
        "proposal_count": len(proposals),
        "proposals": proposals,
        "policy": {
            "propose_only": True,
            "human_approval_required": True,
            "no_runtime_mutation": True,
        },
    }
    target.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "status": "proposed",
        "runtime_effect": "none",
        "written_to": str(target),
        "proposal_count": len(proposals),
        "action_counts": bundle.get("action_counts", {}),
    }

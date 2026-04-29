# SCOPE: both
"""Governed self-improvement loop for Cognitive OS.

This module turns session evidence into *draft* improvements. It never mutates
runtime behavior directly: promotion requires explicit approval and writes only
under canonical `.cognitive-os/` state.
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ImprovementSignal:
    """Evidence-backed signal that may justify a governed improvement."""

    signal_type: str
    slug: str
    title: str
    summary: str
    evidence: list[dict[str, Any]]
    recommended_artifact: str = "skill"
    priority: str = "P1"


@dataclass(frozen=True)
class ImprovementDraft:
    """Draft improvement artifact stored under `.cognitive-os/improvements`."""

    draft_id: str
    status: str
    signal: ImprovementSignal
    created_at: str
    draft_dir: str
    skill_path: str | None = None
    approvals_required: bool = True
    tests_required: list[str] = field(default_factory=list)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return normalized[:80] or "improvement"


def _read_jsonl(path: Path, max_lines: int = 500) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[:max_lines]:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            entries.append(payload)
    return entries


def _metrics_dir(project_dir: Path) -> Path:
    return project_dir / ".cognitive-os" / "metrics"


def _count_by_key(entries: list[dict[str, Any]], key_fn) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        key = key_fn(entry)
        if not key:
            continue
        grouped.setdefault(key, []).append(entry)
    return grouped


def suggest_improvement_signals(
    project_dir: str | Path,
    *,
    min_repeated_errors: int = 3,
    min_skill_failures: int = 2,
    min_successful_steps: int = 5,
) -> list[ImprovementSignal]:
    """Return governed improvement signals from local session evidence.

    Signals are deterministic and side-effect free. They are intentionally
    conservative: repeated failures suggest a draft skill, but they do not edit
    skills/rules until an explicit promotion step happens.
    """
    root = Path(project_dir)
    metrics = _metrics_dir(root)
    errors = _read_jsonl(metrics / "error-learning.jsonl")
    skill_archive = _read_jsonl(metrics / "skill-archive.jsonl") + _read_jsonl(
        metrics / "skill-metrics.jsonl"
    )
    sessions = _read_jsonl(metrics / "session-learnings.jsonl")

    signals: list[ImprovementSignal] = []

    error_groups = _count_by_key(
        errors,
        lambda item: f"{item.get('type') or item.get('error_type') or 'unknown'}:"
        f"{item.get('service') or item.get('component') or item.get('fingerprint') or 'unknown'}",
    )
    for key, group in sorted(error_groups.items()):
        if len(group) < min_repeated_errors:
            continue
        slug = _slugify(f"repair {key}")
        signals.append(
            ImprovementSignal(
                signal_type="repeated_error",
                slug=slug,
                title=f"Draft repair skill for repeated {key}",
                summary=f"Detected {len(group)} repeated error events for `{key}`.",
                evidence=group[:10],
                recommended_artifact="skill",
                priority="P0",
            )
        )

    skill_groups = _count_by_key(
        [entry for entry in skill_archive if entry.get("success") is False],
        lambda item: item.get("skill_name") or item.get("skill"),
    )
    for skill_name, group in sorted(skill_groups.items()):
        if len(group) < min_skill_failures:
            continue
        slug = _slugify(f"improve {skill_name}")
        signals.append(
            ImprovementSignal(
                signal_type="skill_failure",
                slug=slug,
                title=f"Draft improvement for failing skill `{skill_name}`",
                summary=f"Detected {len(group)} failed executions for skill `{skill_name}`.",
                evidence=group[:10],
                recommended_artifact="skill",
                priority="P1",
            )
        )

    for entry in sessions:
        steps = entry.get("steps") or entry.get("tool_calls") or entry.get("iteration_count")
        success = entry.get("success") is True or entry.get("status") == "success"
        if isinstance(steps, int) and steps >= min_successful_steps and success:
            label = entry.get("task") or entry.get("goal") or entry.get("summary") or "successful workflow"
            slug = _slugify(f"reuse {label}")
            signals.append(
                ImprovementSignal(
                    signal_type="successful_multistep_workflow",
                    slug=slug,
                    title=f"Draft reusable skill for `{label}`",
                    summary=f"Detected successful workflow requiring {steps} steps.",
                    evidence=[entry],
                    recommended_artifact="skill",
                    priority="P2",
                )
            )

    return signals


def _skill_markdown(signal: ImprovementSignal) -> str:
    trigger_words = sorted(set(re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{3,}", signal.slug)))[:8]
    trigger_line = ", ".join(trigger_words) or signal.slug
    evidence_count = len(signal.evidence)
    return f"""---
name: {signal.slug}
version: 0.1.0
description: Governed draft skill generated from Cognitive OS evidence: {signal.summary}
triggers: [{trigger_line}]
auto-generated: true
governed-improvement: true
status: draft
---

# {signal.title}

## Purpose

{signal.summary}

## Evidence

- Signal type: `{signal.signal_type}`
- Evidence events: {evidence_count}
- Priority: {signal.priority}

## Procedure

1. Reproduce or inspect the evidence before changing behavior.
2. Identify the smallest reusable workflow that prevents the recurrence.
3. Run the relevant targeted tests before applying this skill in production.
4. If the procedure fails, update this draft with the failure evidence instead of promoting it.

## Verification Checklist

- [ ] Evidence links are still valid.
- [ ] The target workflow has an automated or manual proof path.
- [ ] No secrets or developer-specific absolute paths are embedded.
- [ ] Promotion was explicitly approved.

## Contextual Trigger

Use this draft when the task resembles: `{trigger_line}`.
"""


def create_improvement_draft(project_dir: str | Path, signal: ImprovementSignal) -> ImprovementDraft:
    """Create a draft improvement under `.cognitive-os/improvements/drafts`."""
    root = Path(project_dir)
    draft_id = signal.slug
    draft_dir = root / ".cognitive-os" / "improvements" / "drafts" / draft_id
    draft_dir.mkdir(parents=True, exist_ok=True)

    skill_path = draft_dir / "SKILL.md"
    skill_path.write_text(_skill_markdown(signal), encoding="utf-8")

    draft = ImprovementDraft(
        draft_id=draft_id,
        status="draft",
        signal=signal,
        created_at=_utc_now(),
        draft_dir=str(draft_dir.relative_to(root)),
        skill_path=str(skill_path.relative_to(root)),
        tests_required=[
            "python3 -m pytest tests/unit/test_governed_self_improvement.py -q",
            "manual approval before promotion",
        ],
    )
    (draft_dir / "improvement.json").write_text(
        json.dumps(asdict(draft), indent=2, sort_keys=True), encoding="utf-8"
    )
    return draft


def load_improvement_draft(project_dir: str | Path, draft_id: str) -> ImprovementDraft:
    """Load a draft from canonical state."""
    root = Path(project_dir)
    draft_file = root / ".cognitive-os" / "improvements" / "drafts" / draft_id / "improvement.json"
    data = json.loads(draft_file.read_text(encoding="utf-8"))
    signal = ImprovementSignal(**data["signal"])
    return ImprovementDraft(signal=signal, **{k: v for k, v in data.items() if k != "signal"})


def promote_improvement_draft(
    project_dir: str | Path,
    draft_id: str,
    *,
    approved_by: str | None = None,
    auto_promote: bool = False,
) -> dict[str, Any]:
    """Promote an approved draft skill into canonical `.cognitive-os/skills/cos`.

    Promotion is intentionally denied unless `approved_by` is supplied or the
    caller explicitly opts into `auto_promote`.
    """
    if not approved_by and not auto_promote:
        raise PermissionError("promotion requires approved_by or auto_promote=True")

    root = Path(project_dir)
    draft = load_improvement_draft(root, draft_id)
    if not draft.skill_path:
        raise ValueError(f"draft {draft_id} has no skill artifact to promote")

    source = root / draft.skill_path
    if not source.exists():
        raise FileNotFoundError(source)

    target_dir = root / ".cognitive-os" / "skills" / "cos" / draft.signal.slug
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "SKILL.md"
    shutil.copyfile(source, target)

    promotion = {
        "draft_id": draft_id,
        "status": "promoted",
        "approved_by": approved_by or "auto-promote",
        "promoted_at": _utc_now(),
        "target": str(target.relative_to(root)),
        "source": draft.skill_path,
    }
    (target_dir / "promotion.json").write_text(
        json.dumps(promotion, indent=2, sort_keys=True), encoding="utf-8"
    )
    return promotion

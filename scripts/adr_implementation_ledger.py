#!/usr/bin/env python3
# SCOPE: both
"""Build a portable ADR implementation-status ledger for Cognitive OS."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_PRECEDENCE = ("COGNITIVE_OS_PROJECT_DIR", "CODEX_PROJECT_DIR", "CLAUDE_PROJECT_DIR")
SESSION_PRECEDENCE = ("COGNITIVE_OS_SESSION_ID", "CODEX_SESSION_ID", "CLAUDE_SESSION_ID")
ATTENTION_STATES = {"blocked", "partial", "pending", "pending_evidence", "unknown"}
IMPLEMENTED_TERMS = re.compile(r"\b(implemented|done|completed|shipped|landed|closed)\b", re.IGNORECASE)
PARTIAL_TERMS = re.compile(r"\b(partial|partially|partly|in progress|remaining|follow-up|follow up)\b", re.IGNORECASE)
BLOCKED_TERMS = re.compile(r"\b(blocked|deferred|waiting|depends on|requires|until)\b", re.IGNORECASE)
PENDING_TERMS = re.compile(r"\b(pending|todo|not implemented|not yet|open question|unresolved)\b", re.IGNORECASE)
EVIDENCE_TERMS = re.compile(r"\b(commit|implemented in|files?|tests?|script|hook|skill|rule|path|where:)\b", re.IGNORECASE)


@dataclass(slots=True)
class AdrRecord:
    """One ADR implementation-state record."""

    adr_id: str
    title: str
    path: str
    decision_state: str
    implementation_state: str
    reason: str
    evidence: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)


def resolve_project_dir(explicit: str | None = None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    for name in PROJECT_PRECEDENCE:
        if value := os.environ.get(name):
            return Path(value).expanduser().resolve()
    return Path.cwd().resolve()


def resolve_session_id(explicit: str | None = None) -> str:
    if explicit:
        return explicit
    for name in SESSION_PRECEDENCE:
        if value := os.environ.get(name):
            return value
    return "default"


def parse_now(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def run_git(project_dir: Path, args: list[str]) -> list[str]:
    try:
        proc = subprocess.run(["git", "-C", str(project_dir), *args], capture_output=True, text=True, timeout=5, check=False)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def extract_heading(text: str) -> str:
    match = re.search(r"^#\s+(.+?)\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else "Untitled ADR"


def extract_status(text: str) -> str:
    for pattern in (r"^##\s+Status\s*$\s*([\s\S]*?)(?:^##\s+|\Z)", r"^Status:\s*(.+?)\s*$", r"^\*\*Status\*\*:\s*(.+?)\s*$"):
        match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
        if match:
            raw = re.sub(r"\s+", " ", match.group(1)).strip(" -*`\n\t")
            if raw:
                return raw[:160]
    return ""


def decision_state_from_status(status: str) -> str:
    normalized = status.lower()
    if not normalized:
        return "missing_status"
    if "superseded" in normalized or "replaced" in normalized:
        return "superseded"
    if "reserved" in normalized:
        return "reserved"
    if "accepted" in normalized or "approved" in normalized:
        return "accepted"
    if "draft" in normalized:
        return "draft"
    if "proposed" in normalized:
        return "proposed"
    return "unknown"


def extract_open_questions(text: str) -> list[str]:
    questions: list[str] = []
    for heading in ("Open Questions", "Open questions", "Unresolved", "Follow-up", "Follow-ups", "Risks"):
        section = re.search(rf"^##\s+{re.escape(heading)}\s*$([\s\S]*?)(?:^##\s+|\Z)", text, re.MULTILINE)
        if not section:
            continue
        for match in re.finditer(r"^\s*[-*]\s+(?:\[[ xX]\]\s*)?(.+?)\s*$", section.group(1), re.MULTILINE):
            item = match.group(1).strip()
            if item and not IMPLEMENTED_TERMS.search(item):
                questions.append(item[:180])
    for match in re.finditer(r"^\s*[-*]\s+\[ \]\s+(.+?)\s*$", text, re.MULTILINE):
        item = match.group(1).strip()
        if item:
            questions.append(item[:180])
    return list(dict.fromkeys(questions))[:10]


def extract_explicit_evidence(text: str, project_dir: Path) -> list[str]:
    evidence: list[str] = []
    for line in text.splitlines():
        stripped = line.strip(" -*\t")
        if stripped and len(stripped) <= 240 and EVIDENCE_TERMS.search(stripped) and IMPLEMENTED_TERMS.search(stripped):
            evidence.append(stripped)
    for token in re.findall(r"`([^`]+)`", text):
        if token.startswith(("docs/", "hooks/", "scripts/", "skills/", "rules/", "lib/", "tests/")) and (project_dir / token).exists():
            evidence.append(f"existing path: {token}")
    return list(dict.fromkeys(evidence))[:12]


def git_evidence_for_adr(project_dir: Path, adr_id: str) -> list[str]:
    return [f"commit: {line}" for line in run_git(project_dir, ["log", "--all", "--grep", adr_id, "--oneline", "--", "."])[:5]]


def implementation_state(decision_state: str, status: str, text: str, evidence: list[str], open_questions: list[str]) -> tuple[str, str]:
    status_text = f"{status}\n{text}"
    if decision_state in {"superseded", "reserved"}:
        return decision_state, f"ADR decision state is {decision_state}"
    if BLOCKED_TERMS.search(status_text) and open_questions:
        return "blocked", "Open questions or dependency language indicate blocked work"
    if PARTIAL_TERMS.search(status_text) and open_questions:
        return "partial", "Implementation language is partial and unresolved items remain"
    if PENDING_TERMS.search(status_text) and not evidence:
        return "pending", "Pending/unresolved language found and no implementation evidence was detected"
    if evidence and open_questions:
        return "partial", "Implementation evidence exists, but open questions or unchecked follow-ups remain"
    if evidence and IMPLEMENTED_TERMS.search(status_text):
        return "implemented", "Implementation evidence and completion language were detected"
    if evidence:
        return "pending_evidence", "Evidence references exist, but the ADR does not state completion clearly"
    if decision_state in {"accepted", "proposed", "draft"}:
        return "pending", "Decision exists, but implementation evidence was not found"
    return "unknown", "No reliable implementation status signal was found"


def scan_adrs(project_dir: Path) -> list[AdrRecord]:
    adrs_dir = project_dir / "docs" / "adrs"
    if not adrs_dir.exists():
        return []
    records: list[AdrRecord] = []
    for path in sorted(adrs_dir.glob("ADR-*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        adr_id = path.stem
        status = extract_status(text)
        decision_state = decision_state_from_status(status)
        open_questions = extract_open_questions(text)
        evidence = extract_explicit_evidence(text, project_dir)
        evidence.extend(git_evidence_for_adr(project_dir, adr_id))
        evidence = list(dict.fromkeys(evidence))[:15]
        impl_state, reason = implementation_state(decision_state, status, text, evidence, open_questions)
        records.append(AdrRecord(adr_id, extract_heading(text), path.relative_to(project_dir).as_posix(), decision_state, impl_state, reason, evidence, open_questions))
    return records


def record_to_dict(record: AdrRecord) -> dict[str, Any]:
    return {
        "adr_id": record.adr_id,
        "title": record.title,
        "path": record.path,
        "decision_state": record.decision_state,
        "implementation_state": record.implementation_state,
        "reason": record.reason,
        "evidence": record.evidence,
        "open_questions": record.open_questions,
    }


def summarize(records: list[AdrRecord]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for record in records:
        counts[record.implementation_state] = counts.get(record.implementation_state, 0) + 1
    attention = [record for record in records if record.implementation_state in ATTENTION_STATES]
    return {"total": len(records), "implementation_counts": dict(sorted(counts.items())), "attention_count": len(attention), "attention": [record_to_dict(r) for r in attention[:50]]}


def md_escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def render_markdown(project_dir: Path, session_id: str, now: datetime, records: list[AdrRecord]) -> str:
    summary = summarize(records)
    lines = [
        f"# ADR Implementation Ledger — {now.date().isoformat()}",
        "",
        "> Generated by `scripts/adr_implementation_ledger.py`.",
        f"> Project: `{project_dir}` | Session: `{session_id}`",
        "",
        "## Summary",
        "",
        f"- Total ADRs scanned: {summary['total']}",
        f"- ADRs needing attention: {summary['attention_count']}",
        f"- Implementation states: `{json.dumps(summary['implementation_counts'], sort_keys=True)}`",
        "",
        "## ADRs Needing Attention",
        "",
        "| ADR | Implementation | Reason | Open questions | Evidence |",
        "|-----|----------------|--------|----------------|----------|",
    ]
    attention = [record for record in records if record.implementation_state in ATTENTION_STATES]
    if not attention:
        lines.append("| none | implemented/superseded only | - | - | - |")
    for record in attention[:100]:
        questions = "; ".join(record.open_questions[:2]) if record.open_questions else "-"
        evidence = "; ".join(record.evidence[:2]) if record.evidence else "-"
        lines.append(f"| {md_escape(record.adr_id + ' — ' + record.title)} | {md_escape(record.implementation_state)} | {md_escape(record.reason)} | {md_escape(questions)} | {md_escape(evidence)} |")
    if len(attention) > 100:
        lines.append(f"_and {len(attention) - 100} more ADRs not shown_")
    lines.append("")
    return "\n".join(lines)


def write_outputs(project_dir: Path, session_id: str, now: datetime, records: list[AdrRecord]) -> tuple[Path, Path, Path]:
    metrics_dir = project_dir / ".cognitive-os" / "metrics"
    session_dir = project_dir / ".cognitive-os" / "sessions" / session_id
    metrics_dir.mkdir(parents=True, exist_ok=True)
    session_dir.mkdir(parents=True, exist_ok=True)
    payload = {"timestamp": now.isoformat().replace("+00:00", "Z"), "event": "adr_implementation_reconciled", "session_id": session_id, "summary": summarize(records), "records": [record_to_dict(r) for r in records]}
    latest_path = metrics_dir / "adr-implementation-latest.json"
    jsonl_path = metrics_dir / "adr-implementation.jsonl"
    markdown_path = session_dir / "adr-implementation-ledger.md"
    latest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with jsonl_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    markdown_path.write_text(render_markdown(project_dir, session_id, now, records), encoding="utf-8")
    return latest_path, jsonl_path, markdown_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a Cognitive OS ADR implementation ledger.")
    parser.add_argument("--project-dir", help="Project root. Defaults to COS/Codex/Claude env precedence or cwd.")
    parser.add_argument("--session-id", help="Session id. Defaults to COS/Codex/Claude env precedence or default.")
    parser.add_argument("--write", action="store_true", help="Write latest JSON, JSONL metric, and session markdown ledger.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable summary.")
    parser.add_argument("--now", help="Override generation timestamp for tests.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project_dir = resolve_project_dir(args.project_dir)
    session_id = resolve_session_id(args.session_id)
    now = parse_now(args.now)
    records = scan_adrs(project_dir)
    latest_path = jsonl_path = markdown_path = None
    if args.write:
        latest_path, jsonl_path, markdown_path = write_outputs(project_dir, session_id, now, records)
    if args.json:
        print(json.dumps({"project_dir": str(project_dir), "session_id": session_id, "summary": summarize(records), "latest_path": str(latest_path) if latest_path else None, "jsonl_path": str(jsonl_path) if jsonl_path else None, "markdown_path": str(markdown_path) if markdown_path else None}, ensure_ascii=False, sort_keys=True))
    else:
        print(render_markdown(project_dir, session_id, now, records))
        if latest_path:
            print(f"ADR latest written to: {latest_path}")
        if jsonl_path:
            print(f"ADR metric appended to: {jsonl_path}")
        if markdown_path:
            print(f"ADR ledger written to: {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

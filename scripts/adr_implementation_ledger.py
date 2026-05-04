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

import yaml

PROJECT_PRECEDENCE = ("COGNITIVE_OS_PROJECT_DIR", "CODEX_PROJECT_DIR", "CLAUDE_PROJECT_DIR")
SESSION_PRECEDENCE = ("COGNITIVE_OS_SESSION_ID", "CODEX_SESSION_ID", "CLAUDE_SESSION_ID")
ATTENTION_STATES = {"blocked", "partial", "pending", "pending_evidence", "unknown"}
IMPLEMENT_CURRENT_ATTENTION_STATES = ATTENTION_STATES | {"implement-current"}
KNOWN_CLOSURE_CLASSES = {"evidence-only", "absorbed", "superseded", "obsolete-by-context", "deferred", "implement-current"}
DEFAULT_CLOSURE_METADATA = Path("manifests/adr-closure-metadata.yaml")
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
    missing_required_paths: list[str] = field(default_factory=list)
    closure_class: str = ""
    closure_reason: str = ""


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


def extract_frontmatter(text: str) -> dict[str, Any]:
    """Return YAML frontmatter when present."""
    match = re.match(r"\A---\s*\n([\s\S]*?)\n---\s*(?:\n|\Z)", text)
    if not match:
        return {}
    payload = yaml.safe_load(match.group(1)) or {}
    return payload if isinstance(payload, dict) else {}


def load_closure_metadata(project_dir: Path, metadata_path: Path | None = None) -> dict[str, dict[str, str]]:
    """Load explicit ADR closure metadata keyed by ADR id.

    This file is the durable handoff between human ADR reconciliation and the
    heuristic ledger. It prevents old accepted/proposed language from being
    re-counted as implementation debt after a later ADR or validation pass has
    intentionally closed, absorbed, superseded, or deferred the item.
    """
    path = metadata_path or project_dir / DEFAULT_CLOSURE_METADATA
    if not path.exists():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    rows = payload.get("adrs", [])
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected top-level 'adrs' list")
    out: dict[str, dict[str, str]] = {}
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"{path}: adrs[{index}] must be a mapping")
        adr_id = str(row.get("adr_id", "")).strip()
        closure_class = str(row.get("closure_class", "")).strip()
        reason = str(row.get("reason", "")).strip()
        if not adr_id:
            raise ValueError(f"{path}: adrs[{index}] missing adr_id")
        if closure_class not in KNOWN_CLOSURE_CLASSES:
            raise ValueError(f"{path}: {adr_id} has invalid closure_class {closure_class!r}")
        if not reason:
            raise ValueError(f"{path}: {adr_id} missing closure reason")
        out[adr_id] = {"closure_class": closure_class, "reason": reason}
    return out


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


PATH_PREFIXES = ("docs/", "hooks/", "scripts/", "skills/", "rules/", "lib/", "tests/", "manifests/", "docker/", "requirements/")


def normalized_repo_path(token: str) -> str | None:
    """Return a safe repository-relative path from a prose token."""
    candidate = token.strip().split()[0].strip("'\".,:;)")
    if candidate.startswith("./"):
        candidate = candidate[2:]
    if candidate.startswith(PATH_PREFIXES) and ".." not in Path(candidate).parts:
        return candidate
    return None


def extract_declared_implementation_paths(text: str) -> list[str]:
    """Extract implementation_files from frontmatter as falsifiable path claims."""
    raw = extract_frontmatter(text).get("implementation_files", [])
    if not isinstance(raw, list):
        return []
    paths: list[str] = []
    for value in raw:
        if not isinstance(value, str):
            continue
        path = normalized_repo_path(value)
        if path:
            paths.append(path)
    return list(dict.fromkeys(paths))


def extract_section(text: str, heading: str) -> str:
    section = re.search(rf"^##\s+{re.escape(heading)}\s*$([\s\S]*?)(?:^##\s+|\Z)", text, re.MULTILINE | re.IGNORECASE)
    return section.group(1) if section else ""


def extract_acceptance_required_paths(text: str) -> list[str]:
    """Extract repo paths named by Acceptance Criteria.

    Backticked repo paths in acceptance criteria are treated as required. This
    keeps the ledger from marking accepted ADRs implemented while their named
    helper/script/doc is absent.
    """
    section = extract_section(text, "Acceptance Criteria")
    if not section:
        return []
    paths: list[str] = []
    for line in section.splitlines():
        if "optional" in line.lower():
            continue
        for token in re.findall(r"`([^`]+)`", line):
            path = normalized_repo_path(token)
            if path:
                paths.append(path)
    return list(dict.fromkeys(paths))


def missing_required_paths_for_adr(text: str, project_dir: Path) -> list[str]:
    required_paths = extract_declared_implementation_paths(text)
    required_paths.extend(extract_acceptance_required_paths(text))
    missing: list[str] = []
    for path in dict.fromkeys(required_paths):
        if not (project_dir / path).exists():
            missing.append(path)
    return missing


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


def implementation_state(
    decision_state: str,
    status: str,
    text: str,
    evidence: list[str],
    open_questions: list[str],
    missing_required_paths: list[str],
) -> tuple[str, str]:
    status_text = f"{status}\n{text}"
    if decision_state in {"superseded", "reserved"}:
        return decision_state, f"ADR decision state is {decision_state}"
    if missing_required_paths:
        sample = ", ".join(missing_required_paths[:3])
        suffix = "" if len(missing_required_paths) <= 3 else f", +{len(missing_required_paths) - 3} more"
        if evidence:
            return "partial", f"Required implementation paths are missing: {sample}{suffix}"
        return "pending", f"Required implementation paths are missing: {sample}{suffix}"
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


def apply_closure_metadata(record: AdrRecord, metadata: dict[str, dict[str, str]]) -> AdrRecord:
    """Apply explicit closure metadata to a heuristic record."""
    closure = metadata.get(record.adr_id)
    if not closure:
        return record
    closure_class = closure["closure_class"]
    closure_reason = closure["reason"]
    state_by_class = {
        "evidence-only": "implemented",
        "absorbed": "absorbed",
        "superseded": "superseded",
        "obsolete-by-context": "obsolete",
        "deferred": "deferred",
        "implement-current": "pending",
    }
    state = state_by_class[closure_class]
    if closure_class == "implement-current":
        reason = f"Closure metadata keeps this ADR in current implementation backlog: {closure_reason}"
    else:
        reason = f"Closure metadata marks this ADR as {closure_class}: {closure_reason}"
    evidence = list(record.evidence)
    evidence.insert(0, f"closure metadata: {closure_class}")
    return AdrRecord(
        record.adr_id,
        record.title,
        record.path,
        record.decision_state,
        state,
        reason,
        list(dict.fromkeys(evidence))[:15],
        record.open_questions,
        record.missing_required_paths,
        closure_class,
        closure_reason,
    )


def scan_adrs(project_dir: Path) -> list[AdrRecord]:
    adrs_dir = project_dir / "docs" / "adrs"
    if not adrs_dir.exists():
        return []
    closure_metadata = load_closure_metadata(project_dir)
    records: list[AdrRecord] = []
    for path in sorted(adrs_dir.glob("ADR-*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        adr_id = path.stem
        status = extract_status(text)
        decision_state = decision_state_from_status(status)
        open_questions = extract_open_questions(text)
        missing_required_paths = missing_required_paths_for_adr(text, project_dir)
        evidence = extract_explicit_evidence(text, project_dir)
        evidence.extend(git_evidence_for_adr(project_dir, adr_id))
        evidence = list(dict.fromkeys(evidence))[:15]
        impl_state, reason = implementation_state(decision_state, status, text, evidence, open_questions, missing_required_paths)
        record = AdrRecord(
            adr_id,
            extract_heading(text),
            path.relative_to(project_dir).as_posix(),
            decision_state,
            impl_state,
            reason,
            evidence,
            open_questions,
            missing_required_paths,
        )
        records.append(apply_closure_metadata(record, closure_metadata))
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
        "missing_required_paths": record.missing_required_paths,
        "closure_class": record.closure_class,
        "closure_reason": record.closure_reason,
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
        "| ADR | Implementation | Reason | Missing required paths | Open questions | Evidence |",
        "|-----|----------------|--------|------------------------|----------------|----------|",
    ]
    attention = [record for record in records if record.implementation_state in ATTENTION_STATES]
    if not attention:
        lines.append("| none | implemented/superseded only | - | - | - | - |")
    for record in attention[:100]:
        missing = "; ".join(record.missing_required_paths[:3]) if record.missing_required_paths else "-"
        questions = "; ".join(record.open_questions[:2]) if record.open_questions else "-"
        evidence = "; ".join(record.evidence[:2]) if record.evidence else "-"
        lines.append(f"| {md_escape(record.adr_id + ' — ' + record.title)} | {md_escape(record.implementation_state)} | {md_escape(record.reason)} | {md_escape(missing)} | {md_escape(questions)} | {md_escape(evidence)} |")
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

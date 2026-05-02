#!/usr/bin/env python3
# SCOPE: both
"""Portable session backlog reconciler for Cognitive OS.

This command normalizes pending work signals from the repository, local
`.cognitive-os` ledgers, git, and optional Engram into one markdown backlog and
one JSONL reconciliation event. It is intentionally harness-agnostic: Codex,
Claude Code, and future drivers should feed the same local ledgers rather than
making their private transcript formats the source of truth.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

PROJECT_PRECEDENCE = (
    "COGNITIVE_OS_PROJECT_DIR",
    "CODEX_PROJECT_DIR",
    "CLAUDE_PROJECT_DIR",
)
SESSION_PRECEDENCE = (
    "COGNITIVE_OS_SESSION_ID",
    "CODEX_SESSION_ID",
    "CLAUDE_SESSION_ID",
)
PENDING_STATUSES = {"in_progress", "pending", "failed", "queued", "blocked"}
COMPLETED_STATUSES = {"completed", "done"}
STALE_STATUSES = {"cancelled", "cancelled-stale", "stale"}
MAX_TABLE_ITEMS = 20


@dataclass(slots=True)
class BacklogItem:
    """One normalized actionable item from any backlog source."""

    task: str
    source: str
    context: str = ""
    effort: str = "1 session"
    priority: int = 4
    status: str = "pending"
    evidence: dict[str, Any] = field(default_factory=dict)

    def key(self) -> str:
        normalized = re.sub(r"\s+", " ", self.task.strip().lower())
        return f"{self.source}:{normalized}"


@dataclass(slots=True)
class PlanSummary:
    """Compact status for one plan document."""

    name: str
    progress: str
    next_phase: str
    remaining: str


@dataclass(slots=True)
class BacklogResult:
    """Full reconciliation result."""

    items: list[BacklogItem]
    plans: list[PlanSummary]
    sources: set[str]
    warnings: list[str]
    engram_saved: bool = False


def resolve_project_dir(explicit: str | None = None) -> Path:
    """Resolve project root with canonical cross-harness precedence."""
    if explicit:
        return Path(explicit).expanduser().resolve()
    for env_name in PROJECT_PRECEDENCE:
        value = os.environ.get(env_name)
        if value:
            return Path(value).expanduser().resolve()
    return Path.cwd().resolve()


def resolve_session_id(explicit: str | None = None) -> str:
    """Resolve session id with canonical cross-harness precedence."""
    if explicit:
        return explicit
    for env_name in SESSION_PRECEDENCE:
        value = os.environ.get(env_name)
        if value:
            return value
    return "default"


def parse_now(value: str | None) -> datetime:
    """Return UTC timestamp, honoring an explicit testable ISO timestamp."""
    if not value:
        return datetime.now(timezone.utc)
    text = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def read_json(path: Path, warnings: list[str]) -> Any | None:
    """Best-effort JSON reader."""
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        warnings.append(f"Malformed JSON skipped: {path}: {exc}")
        return None


def run_git(project_dir: Path, args: list[str], warnings: list[str]) -> list[str]:
    """Run a git command and return stdout lines without failing the command."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(project_dir), *args],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        warnings.append(f"Git command unavailable: git {' '.join(args)}: {exc}")
        return []
    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or "non-zero exit"
        warnings.append(f"Git command skipped: git {' '.join(args)}: {detail}")
        return []
    return [line for line in proc.stdout.splitlines() if line.strip()]


def classify_task_status(status: str) -> int:
    """Map task status to priority tier."""
    if status in {"in_progress", "failed", "blocked"}:
        return 1
    if status in {"pending", "queued"}:
        return 2
    return 4


def collect_active_tasks(project_dir: Path, warnings: list[str]) -> list[BacklogItem]:
    """Collect open entries from the active task ledger."""
    data = read_json(project_dir / ".cognitive-os" / "tasks" / "active-tasks.json", warnings)
    if not isinstance(data, dict):
        return []
    items: list[BacklogItem] = []
    for task in data.get("tasks", []):
        if not isinstance(task, dict):
            continue
        status = str(task.get("status", "pending"))
        if status in COMPLETED_STATUSES:
            continue
        description = str(task.get("description") or task.get("id") or "Unnamed task")
        context = f"status={status}"
        if task.get("id"):
            context += f"; id={task['id']}"
        items.append(
            BacklogItem(
                task=description,
                source="active-tasks",
                context=context,
                priority=classify_task_status(status),
                status=status,
                evidence={
                    "id": task.get("id"),
                    "expectedOutputs": task.get("expectedOutputs", []),
                    "checkCommand": task.get("checkCommand"),
                },
            )
        )
    return items


def collect_dispatch_queue(project_dir: Path, warnings: list[str]) -> list[BacklogItem]:
    """Collect queued launches from dispatch queue when present."""
    data = read_json(project_dir / ".cognitive-os" / "tasks" / "dispatch-queue.json", warnings)
    if data is None:
        return []
    queue: Iterable[Any]
    if isinstance(data, dict):
        queue = data.get("tasks") or data.get("queue") or []
    elif isinstance(data, list):
        queue = data
    else:
        return []
    items: list[BacklogItem] = []
    for entry in queue:
        if not isinstance(entry, dict):
            continue
        description = str(entry.get("description") or entry.get("id") or "Queued dispatch")
        items.append(
            BacklogItem(
                task=description,
                source="dispatch-queue",
                context=f"priority={entry.get('priority', 'unknown')}",
                priority=2,
                status="queued",
                evidence={"id": entry.get("id"), "model": entry.get("model")},
            )
        )
    return items


def checkbox_counts(text: str) -> tuple[int, int]:
    """Return completed and total markdown checkbox counts."""
    total = 0
    done = 0
    for match in re.finditer(r"^\s*[-*]\s+\[([ xX])\]", text, re.MULTILINE):
        total += 1
        if match.group(1).lower() == "x":
            done += 1
    return done, total


def extract_pending_checkboxes(text: str, limit: int = 5) -> list[str]:
    """Extract unchecked checkbox labels from markdown."""
    labels = []
    pattern = re.compile(r"^\s*[-*]\s+\[ \]\s+(.+?)\s*$", re.MULTILINE)
    for match in pattern.finditer(text):
        label = re.sub(r"\s+", " ", match.group(1).strip())
        if label:
            labels.append(label)
        if len(labels) >= limit:
            break
    return labels


def extract_title(path: Path, text: str) -> str:
    """Extract a readable title for a plan document."""
    match = re.search(r"^#\s+(.+?)\s*$", text, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return path.relative_to(path.parents[2]).as_posix() if len(path.parents) > 2 else path.name


def collect_plans(project_dir: Path, warnings: list[str]) -> tuple[list[BacklogItem], list[PlanSummary]]:
    """Collect plan checkbox tasks and plan status summaries."""
    plans_dir = project_dir / ".cognitive-os" / "plans"
    if not plans_dir.exists():
        warnings.append("No .cognitive-os/plans directory found")
        return [], []
    items: list[BacklogItem] = []
    summaries: list[PlanSummary] = []
    for path in sorted(plans_dir.rglob("*.md")):
        try:
            text = path.read_text()
        except OSError as exc:
            warnings.append(f"Plan skipped: {path}: {exc}")
            continue
        done, total = checkbox_counts(text)
        if total == 0:
            continue
        title = extract_title(path, text)
        pending = extract_pending_checkboxes(text)
        progress = f"{done}/{total} tasks done"
        if done == total:
            next_phase = "Complete"
            remaining = "0"
        else:
            next_phase = pending[0] if pending else "Pending task"
            remaining = "1 session" if total - done <= 3 else "2-3 sessions"
        summaries.append(PlanSummary(title, progress, next_phase, remaining))
        if done < total:
            rel = path.relative_to(project_dir).as_posix()
            context = f"{progress}; file={rel}"
            priority = 2 if done > 0 else 3
            for label in pending:
                items.append(
                    BacklogItem(
                        task=label,
                        source="plans",
                        context=context,
                        priority=priority,
                        status="pending",
                    )
                )
    return items, summaries


def collect_user_requests(project_dir: Path, session_id: str, warnings: list[str]) -> list[BacklogItem]:
    """Collect pending user request queue entries across sessions."""
    sessions_dir = project_dir / ".cognitive-os" / "sessions"
    if not sessions_dir.exists():
        return []
    candidate_files = []
    current = sessions_dir / session_id / "user-requests.jsonl"
    if current.exists():
        candidate_files.append(current)
    candidate_files.extend(path for path in sorted(sessions_dir.glob("*/user-requests.jsonl")) if path != current)
    items: list[BacklogItem] = []
    for path in candidate_files:
        try:
            lines = path.read_text().splitlines()
        except OSError as exc:
            warnings.append(f"User request queue skipped: {path}: {exc}")
            continue
        for line_no, line in enumerate(lines, 1):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as exc:
                warnings.append(f"Malformed user request skipped: {path}:{line_no}: {exc}")
                continue
            if entry.get("status") != "pending":
                continue
            message = str(entry.get("message", "Pending user request")).strip()
            if not message:
                continue
            try:
                rel = path.relative_to(project_dir).as_posix()
            except ValueError:
                rel = str(path)
            items.append(
                BacklogItem(
                    task=message[:180],
                    source="user-requests",
                    context=f"queue={rel}; timestamp={entry.get('timestamp', '?')}",
                    priority=1,
                    status="pending",
                )
            )
    return items


def collect_changelog_next_steps(project_dir: Path, warnings: list[str]) -> list[BacklogItem]:
    """Collect next-step bullets from recent changelog documents."""
    changelog_dir = project_dir / ".cognitive-os" / "changelogs"
    if not changelog_dir.exists():
        return []
    items: list[BacklogItem] = []
    paths = sorted(changelog_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:10]
    for path in paths:
        try:
            text = path.read_text()
        except OSError as exc:
            warnings.append(f"Changelog skipped: {path}: {exc}")
            continue
        section = re.search(r"^##\s+Next Steps\s*$([\s\S]*?)(?:^##\s+|\Z)", text, re.MULTILINE)
        if not section:
            continue
        for match in re.finditer(r"^\s*[-*]\s+(.+?)\s*$", section.group(1), re.MULTILINE):
            label = match.group(1).strip()
            if label and not re.search(r"\b(done|completed)\b", label, re.IGNORECASE):
                items.append(
                    BacklogItem(
                        task=label,
                        source="changelogs",
                        context=f"file={path.relative_to(project_dir).as_posix()}",
                        priority=3,
                        status="pending",
                    )
                )
    return items


def collect_handoffs(project_dir: Path, warnings: list[str]) -> list[BacklogItem]:
    """Collect still-active next-step bullets from recent handoff docs."""
    items: list[BacklogItem] = []
    handoffs = sorted(project_dir.glob("docs/SESSION-HANDOFF-*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:5]
    for path in handoffs:
        try:
            text = path.read_text()
        except OSError as exc:
            warnings.append(f"Handoff skipped: {path}: {exc}")
            continue
        for heading in ("Next Steps", "What remains", "Remaining Work"):
            section = re.search(rf"^##\s+{re.escape(heading)}\s*$([\s\S]*?)(?:^##\s+|\Z)", text, re.MULTILINE | re.IGNORECASE)
            if not section:
                continue
            for match in re.finditer(r"^\s*[-*]\s+(.+?)\s*$", section.group(1), re.MULTILINE):
                label = match.group(1).strip()
                if label and not re.search(r"\b(done|completed|closed)\b", label, re.IGNORECASE):
                    items.append(
                        BacklogItem(
                            task=label,
                            source="handoffs",
                            context=f"file={path.relative_to(project_dir).as_posix()}",
                            priority=3,
                            status="pending",
                        )
                    )
            break
    return items


def collect_git_items(project_dir: Path, warnings: list[str]) -> list[BacklogItem]:
    """Collect git state that represents unresolved work."""
    items: list[BacklogItem] = []
    status_lines = run_git(project_dir, ["status", "--porcelain"], warnings)
    for line in status_lines[:20]:
        items.append(
            BacklogItem(
                task=f"Resolve git working tree entry: {line}",
                source="git",
                context="git status --porcelain",
                priority=1,
                status="pending",
                effort="< 30min",
            )
        )
    stash_lines = run_git(project_dir, ["stash", "list"], warnings)
    for line in stash_lines[:10]:
        items.append(
            BacklogItem(
                task=f"Review stash: {line}",
                source="git",
                context="git stash list",
                priority=2,
                status="pending",
                effort="< 30min",
            )
        )
    branch_lines = run_git(project_dir, ["branch", "--no-merged", "HEAD"], warnings)
    for line in branch_lines[:10]:
        branch = line.replace("*", "").strip()
        if branch and branch not in {"main", "master"}:
            items.append(
                BacklogItem(
                    task=f"Review unmerged branch: {branch}",
                    source="git",
                    context="git branch --no-merged HEAD",
                    priority=3,
                    status="pending",
                    effort="1 session",
                )
            )
    return items


def collect_engram_items(project_dir: Path, warnings: list[str], enabled: bool) -> list[BacklogItem]:
    """Best-effort Engram search for pending session/backlog observations."""
    if not enabled:
        warnings.append("Engram search skipped by --no-engram")
        return []
    try:
        sys.path.insert(0, str(project_dir))
        from lib.engram_client import search_observations  # type: ignore[import]
    except Exception as exc:  # pragma: no cover - import environment dependent
        warnings.append(f"Engram search unavailable: {exc}")
        return []
    queries = (
        "session/backlog latest pending next steps",
        "session summary next steps remaining work",
        "queued pending deferred future session backlog",
    )
    items: list[BacklogItem] = []
    seen_obs: set[str] = set()
    for query in queries:
        for obs in search_observations(query, limit=5, project=project_dir.name):
            obs_id = str(obs.get("id") or obs.get("sync_id") or obs.get("title"))
            if obs_id in seen_obs:
                continue
            seen_obs.add(obs_id)
            content = str(obs.get("content", ""))
            title = str(obs.get("title", "Engram observation"))
            candidates = extract_next_step_lines(content)
            if not candidates and re.search(r"pending|next steps|remaining|queued|deferred", title + content, re.IGNORECASE):
                candidates = [title]
            for candidate in candidates[:5]:
                items.append(
                    BacklogItem(
                        task=candidate,
                        source="engram",
                        context=f"observation={obs_id}; title={title[:80]}",
                        priority=2,
                        status="pending",
                        evidence={"observation": obs_id},
                    )
                )
    if not items:
        warnings.append("Engram search returned no backlog candidates")
    return items


def extract_next_step_lines(content: str) -> list[str]:
    """Extract likely next-step bullets from an Engram observation."""
    extracted: list[str] = []
    section = re.search(r"^##\s+Next Steps\s*$([\s\S]*?)(?:^##\s+|\Z)", content, re.MULTILINE | re.IGNORECASE)
    search_space = section.group(1) if section else content
    for match in re.finditer(r"^\s*[-*]\s+(?:\[[ xX]\]\s*)?(.+?)\s*$", search_space, re.MULTILINE):
        label = match.group(1).strip()
        if label and re.search(r"pending|next|todo|remaining|implement|fix|add|repair|investigate", label, re.IGNORECASE):
            extracted.append(label)
    return extracted


def dedupe_items(items: list[BacklogItem]) -> list[BacklogItem]:
    """Deduplicate while preserving the highest priority source."""
    by_key: dict[str, BacklogItem] = {}
    for item in items:
        key = re.sub(r"\s+", " ", item.task.strip().lower())
        existing = by_key.get(key)
        if existing is None or item.priority < existing.priority:
            by_key[key] = item
        elif existing is not None and item.source not in existing.source.split("+"):
            existing.source += f"+{item.source}"
    return sorted(by_key.values(), key=lambda item: (item.priority, item.source, item.task.lower()))


def reconcile(project_dir: Path, session_id: str, include_engram: bool) -> BacklogResult:
    """Collect and normalize backlog state from every supported source."""
    warnings: list[str] = []
    plans_items, plans = collect_plans(project_dir, warnings)
    collectors = [
        collect_active_tasks(project_dir, warnings),
        collect_dispatch_queue(project_dir, warnings),
        plans_items,
        collect_user_requests(project_dir, session_id, warnings),
        collect_changelog_next_steps(project_dir, warnings),
        collect_handoffs(project_dir, warnings),
        collect_git_items(project_dir, warnings),
        collect_engram_items(project_dir, warnings, include_engram),
    ]
    items = dedupe_items([item for group in collectors for item in group])
    sources = {item.source for item in items}
    return BacklogResult(items=items, plans=plans, sources=sources, warnings=warnings)


def md_escape(value: str) -> str:
    """Escape Markdown table delimiters."""
    return value.replace("|", "\\|").replace("\n", " ").strip()


def render_priority_section(title: str, headers: tuple[str, str, str, str], items: list[BacklogItem]) -> str:
    """Render one priority table."""
    lines = [f"## {title}", "", f"| {' | '.join(headers)} |", "|------|--------|---------|-------------|"]
    if not items:
        lines.append("_(none found)_")
        return "\n".join(lines)
    for item in items[:MAX_TABLE_ITEMS]:
        third = item.context or item.status
        lines.append(
            f"| {md_escape(item.task)} | {md_escape(item.source)} | {md_escape(third)} | {md_escape(item.effort)} |"
        )
    if len(items) > MAX_TABLE_ITEMS:
        lines.append(f"_and {len(items) - MAX_TABLE_ITEMS} more items not shown_")
    return "\n".join(lines)


def render_markdown(result: BacklogResult, project_dir: Path, session_id: str, now: datetime) -> str:
    """Render deterministic backlog markdown."""
    by_priority = {priority: [item for item in result.items if item.priority == priority] for priority in range(1, 5)}
    total = len(result.items)
    sources = ", ".join(sorted(result.sources)) if result.sources else "none"
    top = next((item.task for item in result.items if item.priority in {1, 2}), "Backlog is empty — all tracked work appears complete.")
    quick = [item.task for item in result.items if item.effort == "< 30min"][:3]
    parallel = [item.task for item in result.items if item.priority in {2, 3}][:3]

    lines = [
        f"# Session Backlog — {now.date().isoformat()}",
        "",
        "> Generated by `scripts/cos_session_backlog.py`. Sources scanned: plans, Engram, active-tasks, dispatch-queue, user request queues, changelogs, handoffs, and git state.",
        f"> Project: `{project_dir}` | Session: `{session_id}`",
        "",
    ]
    if result.warnings:
        lines.extend(["## Source Warnings", ""])
        lines.extend(f"- {warning}" for warning in result.warnings[:20])
        if len(result.warnings) > 20:
            lines.append(f"- and {len(result.warnings) - 20} more warnings not shown")
        lines.append("")

    lines.append(render_priority_section("Priority 1: In-Progress (resume immediately)", ("Task", "Source", "Context", "Est. Effort"), by_priority[1]))
    lines.append("")
    lines.append(render_priority_section("Priority 2: Ready to Start (dependencies met)", ("Task", "Source", "Blocked by", "Est. Effort"), by_priority[2]))
    lines.append("")
    lines.append(render_priority_section("Priority 3: Planned (needs prerequisites)", ("Task", "Source", "Prerequisites", "Est. Effort"), by_priority[3]))
    lines.append("")
    lines.append(render_priority_section("Priority 4: Backlog (no urgency)", ("Task", "Source", "Notes", "Est. Effort"), by_priority[4]))
    lines.extend(["", "## Plans Status Summary", "", "| Plan | Progress | Next Phase | Est. Remaining |", "|------|----------|------------|----------------|"])
    if result.plans:
        for plan in result.plans[:MAX_TABLE_ITEMS]:
            lines.append(
                f"| {md_escape(plan.name)} | {md_escape(plan.progress)} | {md_escape(plan.next_phase)} | {md_escape(plan.remaining)} |"
            )
        if len(result.plans) > MAX_TABLE_ITEMS:
            lines.append(f"_and {len(result.plans) - MAX_TABLE_ITEMS} more plans not shown_")
    else:
        lines.append("_(none found)_")
    lines.extend(
        [
            "",
            "## Recommendations for Next Session",
            "",
            f"1. **Start with**: {top}",
            f"2. **Quick wins**: {', '.join(quick) if quick else 'none found'}",
            f"3. **Can parallelize**: {', '.join(parallel) if parallel else 'none found'}",
            "",
            "---",
            f"_Backlog generated: {now.isoformat().replace('+00:00', 'Z')} | Items: {total} | Sources: {sources}_",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(project_dir: Path, session_id: str, markdown: str, result: BacklogResult, now: datetime) -> tuple[Path, Path]:
    """Write backlog markdown and reconciliation metric."""
    session_dir = project_dir / ".cognitive-os" / "sessions" / session_id
    metrics_dir = project_dir / ".cognitive-os" / "metrics"
    session_dir.mkdir(parents=True, exist_ok=True)
    metrics_dir.mkdir(parents=True, exist_ok=True)
    backlog_path = session_dir / "backlog.md"
    backlog_path.write_text(markdown)

    metric_path = metrics_dir / "backlog-reconciliation.jsonl"
    counts = {str(priority): sum(1 for item in result.items if item.priority == priority) for priority in range(1, 5)}
    metric = {
        "timestamp": now.isoformat().replace("+00:00", "Z"),
        "event": "backlog_reconciled",
        "session_id": session_id,
        "backlog_path": str(backlog_path),
        "item_count": len(result.items),
        "priority_counts": counts,
        "sources": sorted(result.sources),
        "warnings": result.warnings,
        "engram_saved": result.engram_saved,
    }
    with metric_path.open("a") as handle:
        handle.write(json.dumps(metric, ensure_ascii=False, sort_keys=True) + "\n")
    return backlog_path, metric_path


def sync_engram(project_dir: Path, markdown: str, date: str, result: BacklogResult) -> bool:
    """Best-effort Engram upsert via local CLI wrapper when available."""
    try:
        sys.path.insert(0, str(project_dir))
        from lib.engram_client import save_observation  # type: ignore[import]
    except Exception:
        return False
    latest = save_observation(
        "Session Backlog — latest",
        markdown,
        type_="discovery",
        topic_key="session/backlog/latest",
        project=project_dir.name,
    )
    dated = save_observation(
        f"Session Backlog — {date}",
        markdown,
        type_="discovery",
        topic_key=f"session/backlog/{date}",
        project=project_dir.name,
    )
    result.engram_saved = bool(latest and dated)
    return result.engram_saved


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(description="Reconcile portable Cognitive OS session backlog.")
    parser.add_argument("--project-dir", help="Project root. Defaults to COS/Codex/Claude env precedence or cwd.")
    parser.add_argument("--session-id", help="Session id. Defaults to COS/Codex/Claude env precedence or default.")
    parser.add_argument("--write", action="store_true", help="Write backlog.md and backlog-reconciliation.jsonl.")
    parser.add_argument("--sync-engram", action="store_true", help="Best-effort upsert to Engram session/backlog/latest and dated topic.")
    parser.add_argument("--no-engram", action="store_true", help="Skip Engram searches during reconciliation.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable summary instead of markdown.")
    parser.add_argument("--now", help="Override generation timestamp, for tests. ISO-8601 UTC preferred.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the reconciler."""
    args = build_parser().parse_args(argv)
    project_dir = resolve_project_dir(args.project_dir)
    session_id = resolve_session_id(args.session_id)
    now = parse_now(args.now)
    result = reconcile(project_dir, session_id, include_engram=not args.no_engram)
    markdown = render_markdown(result, project_dir, session_id, now)

    if args.sync_engram:
        sync_engram(project_dir, markdown, now.date().isoformat(), result)
        markdown = render_markdown(result, project_dir, session_id, now)

    backlog_path = None
    metric_path = None
    if args.write:
        backlog_path, metric_path = write_outputs(project_dir, session_id, markdown, result, now)

    if args.json:
        summary = {
            "project_dir": str(project_dir),
            "session_id": session_id,
            "item_count": len(result.items),
            "priority_counts": {str(priority): sum(1 for item in result.items if item.priority == priority) for priority in range(1, 5)},
            "sources": sorted(result.sources),
            "warnings": result.warnings,
            "backlog_path": str(backlog_path) if backlog_path else None,
            "metric_path": str(metric_path) if metric_path else None,
            "engram_saved": result.engram_saved,
        }
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    else:
        print(markdown)
        if backlog_path:
            print(f"Backlog written to: {backlog_path}")
        if metric_path:
            print(f"Metric appended to: {metric_path}")
        if args.sync_engram:
            print(f"Engram sync: {'saved' if result.engram_saved else 'skipped/unavailable'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

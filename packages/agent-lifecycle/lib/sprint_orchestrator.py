"""Sprint orchestrator — ADR-036 MVP.

Sprint = a named batch of N agent tasks launched from a YAML spec, tracked via
canonical events, and optionally closed with a consolidated commit.

This module provides:
  - :class:`SprintTask` / :class:`SprintManifest` dataclasses (the manifest is
    the durable record written to ``.cognitive-os/sprints/<id>.json``).
  - YAML-spec loading (``load_spec``) + validation.
  - Manifest persistence (``save_manifest`` / ``load_manifest``).
  - Canonical events (``SprintStarted``, ``SprintTaskLaunched``,
    ``SprintTaskCompleted``, ``SprintCancelled``, ``SprintCompleted``) that
    extend the ADR-033 ``CanonicalEvent`` base and auto-register into the
    shared event registry.

Explicitly OUT of MVP (stubbed, follow-up tasks):
  - TUI (``cos watch --sprint``) — see :func:`render_sprint_status_stub`.
  - Test aggregation — see :func:`aggregate_test_results_stub`.
  - Consolidated commit execution — see :func:`consolidate_commits_stub`.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional

try:
    from lib.harness_adapter.base import CanonicalEvent, now_epoch
except ImportError:  # pragma: no cover — exercised only when imported as top-level
    from harness_adapter.base import CanonicalEvent, now_epoch


# ---------------------------------------------------------------------------
# Status enums
# ---------------------------------------------------------------------------


class SprintStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class SprintTaskStatus(str, Enum):
    PENDING = "pending"
    LAUNCHED = "launched"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# Commit strategies (see ADR-036 §Consolidated commits)
# ---------------------------------------------------------------------------


class CommitStrategy(str, Enum):
    #: Each task commits independently as it completes (MVP default).
    PER_TASK = "per_task"
    #: Single squashed commit after all tasks complete successfully.
    SQUASH = "squash"
    #: No commits — caller is responsible.
    NONE = "none"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class SprintTask:
    """One unit of work inside a sprint."""

    id: str
    title: str
    prompt: str
    file_scope: List[str] = field(default_factory=list)
    model: str = "sonnet"
    status: str = SprintTaskStatus.PENDING.value
    started_at: Optional[float] = None
    ended_at: Optional[float] = None
    agent_id: Optional[str] = None  # correlates with canonical AgentStart.agent_id

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SprintTask":
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class SprintManifest:
    """Durable record of a sprint. Written to ``.cognitive-os/sprints/<id>.json``."""

    id: str
    name: str
    tasks: List[SprintTask] = field(default_factory=list)
    commit_strategy: str = CommitStrategy.PER_TASK.value
    status: str = SprintStatus.PENDING.value
    created_at: float = 0.0
    started_at: Optional[float] = None
    ended_at: Optional[float] = None
    spec_path: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["tasks"] = [t.to_dict() if isinstance(t, SprintTask) else t for t in self.tasks]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SprintManifest":
        tasks_raw = data.get("tasks", [])
        tasks = [
            t if isinstance(t, SprintTask) else SprintTask.from_dict(t)
            for t in tasks_raw
        ]
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        payload = {k: v for k, v in data.items() if k in known and k != "tasks"}
        return cls(tasks=tasks, **payload)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)


# ---------------------------------------------------------------------------
# Canonical events (extend ADR-033 registry)
# ---------------------------------------------------------------------------


@dataclass
class SprintStarted(CanonicalEvent):
    event_type: ClassVar[str] = "sprint_started"

    sprint_id: str = ""
    sprint_name: str = ""
    task_count: int = 0
    started_at: float = 0.0
    commit_strategy: str = CommitStrategy.PER_TASK.value
    session_id: Optional[str] = None


@dataclass
class SprintTaskLaunched(CanonicalEvent):
    event_type: ClassVar[str] = "sprint_task_launched"

    sprint_id: str = ""
    task_id: str = ""
    agent_id: str = ""
    model: str = "sonnet"
    launched_at: float = 0.0
    session_id: Optional[str] = None


@dataclass
class SprintTaskCompleted(CanonicalEvent):
    event_type: ClassVar[str] = "sprint_task_completed"

    sprint_id: str = ""
    task_id: str = ""
    agent_id: str = ""
    exit_status: str = "success"  # "success" | "error" | "timeout"
    ended_at: float = 0.0
    duration_ms: Optional[int] = None
    session_id: Optional[str] = None


@dataclass
class SprintCancelled(CanonicalEvent):
    event_type: ClassVar[str] = "sprint_cancelled"

    sprint_id: str = ""
    cancelled_at: float = 0.0
    reason: str = ""
    session_id: Optional[str] = None


@dataclass
class SprintCompleted(CanonicalEvent):
    event_type: ClassVar[str] = "sprint_completed"

    sprint_id: str = ""
    ended_at: float = 0.0
    tasks_succeeded: int = 0
    tasks_failed: int = 0
    duration_ms: Optional[int] = None
    session_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Spec loading + validation
# ---------------------------------------------------------------------------


class SprintSpecError(ValueError):
    """Raised when a YAML spec does not satisfy the minimum schema."""


def _load_yaml(path: Path) -> Dict[str, Any]:
    """Tiny YAML loader — prefer PyYAML, fall back to a minimal subset parser.

    The minimal parser supports the specific shape we document in the example
    spec so we don't hard-require PyYAML in test environments.
    """
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text) or {}
    except ImportError:
        return _parse_minimal_yaml(text)


def _parse_minimal_yaml(text: str) -> Dict[str, Any]:
    """Parse the subset of YAML used by example sprint specs.

    Supports: scalar key: value, list items with "- ", nested dicts under a key.
    This is NOT a general YAML parser — it exists only so tests can run without
    PyYAML. In production, PyYAML is expected.
    """
    import re

    root: Dict[str, Any] = {}
    stack: List = [(0, root)]  # (indent, container)
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        indent = len(line) - len(line.lstrip())
        while stack and indent < stack[-1][0]:
            stack.pop()
        container = stack[-1][1]
        stripped = line.strip()

        list_match = re.match(r"^- (.*)$", stripped)
        if list_match and isinstance(container, list):
            content = list_match.group(1)
            if ":" in content:
                key, _, val = content.partition(":")
                item: Dict[str, Any] = {}
                if val.strip():
                    item[key.strip()] = _coerce_scalar(val.strip())
                container.append(item)
                stack.append((indent + 2, item))
            else:
                container.append(_coerce_scalar(content))
            i += 1
            continue

        if ":" in stripped:
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip()
            if not val:
                # Peek: list or dict?
                j = i + 1
                while j < len(lines) and (not lines[j].strip() or lines[j].lstrip().startswith("#")):
                    j += 1
                if j < len(lines):
                    next_indent = len(lines[j]) - len(lines[j].lstrip())
                    if lines[j].lstrip().startswith("- "):
                        new_list: List[Any] = []
                        container[key] = new_list
                        stack.append((next_indent, new_list))
                    else:
                        new_dict: Dict[str, Any] = {}
                        container[key] = new_dict
                        stack.append((next_indent, new_dict))
                else:
                    container[key] = None
            else:
                container[key] = _coerce_scalar(val)
        i += 1
    return root


def _coerce_scalar(val: str) -> Any:
    if val.startswith(('"', "'")) and val.endswith(('"', "'")) and len(val) >= 2:
        return val[1:-1]
    if val.lower() in ("true", "false"):
        return val.lower() == "true"
    if val.lower() in ("null", "~"):
        return None
    try:
        if "." in val:
            return float(val)
        return int(val)
    except ValueError:
        return val


def load_spec(yaml_path: Path | str) -> SprintManifest:
    """Load a sprint YAML spec into a fresh :class:`SprintManifest`.

    Generates a new sprint id + created_at on every call. The returned manifest
    is *not* persisted — call :func:`save_manifest` to write it.
    """
    path = Path(yaml_path)
    if not path.exists():
        raise SprintSpecError(f"spec not found: {path}")

    raw = _load_yaml(path)
    if not isinstance(raw, dict):
        raise SprintSpecError("spec root must be a mapping")

    name = raw.get("name")
    if not name or not isinstance(name, str):
        raise SprintSpecError("spec must set a non-empty 'name'")

    tasks_raw = raw.get("tasks")
    if not isinstance(tasks_raw, list) or not tasks_raw:
        raise SprintSpecError("spec must declare a non-empty 'tasks' list")

    commit_strategy = raw.get("commit_strategy", CommitStrategy.PER_TASK.value)
    if commit_strategy not in {c.value for c in CommitStrategy}:
        raise SprintSpecError(
            f"unknown commit_strategy '{commit_strategy}'; "
            f"valid: {sorted(c.value for c in CommitStrategy)}"
        )

    tasks: List[SprintTask] = []
    for idx, entry in enumerate(tasks_raw):
        if not isinstance(entry, dict):
            raise SprintSpecError(f"task[{idx}] must be a mapping")
        tid = entry.get("id") or f"t{idx + 1}"
        title = entry.get("title")
        prompt = entry.get("prompt")
        if not title or not isinstance(title, str):
            raise SprintSpecError(f"task[{idx}] missing 'title'")
        if not prompt or not isinstance(prompt, str):
            raise SprintSpecError(f"task[{idx}] missing 'prompt'")
        file_scope = entry.get("file_scope") or []
        if not isinstance(file_scope, list):
            raise SprintSpecError(f"task[{idx}] file_scope must be a list")
        model = entry.get("model", "sonnet")
        tasks.append(
            SprintTask(
                id=str(tid),
                title=title,
                prompt=prompt,
                file_scope=[str(p) for p in file_scope],
                model=str(model),
            )
        )

    sprint_id = raw.get("id") or f"sprint-{uuid.uuid4().hex[:8]}"
    return SprintManifest(
        id=str(sprint_id),
        name=name,
        tasks=tasks,
        commit_strategy=commit_strategy,
        status=SprintStatus.PENDING.value,
        created_at=now_epoch(),
        spec_path=str(path),
        notes=raw.get("notes"),
    )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def default_sprints_dir(project_dir: Optional[Path] = None) -> Path:
    base = Path(project_dir) if project_dir else Path.cwd()
    return base / ".cognitive-os" / "sprints"


def manifest_path(sprint_id: str, project_dir: Optional[Path] = None) -> Path:
    return default_sprints_dir(project_dir) / f"{sprint_id}.json"


def save_manifest(manifest: SprintManifest, path: Optional[Path] = None) -> Path:
    target = Path(path) if path else manifest_path(manifest.id)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(manifest.to_json(), encoding="utf-8")
    return target


def load_manifest(path: Path | str) -> SprintManifest:
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    return SprintManifest.from_dict(data)


def list_manifests(project_dir: Optional[Path] = None) -> List[SprintManifest]:
    d = default_sprints_dir(project_dir)
    if not d.exists():
        return []
    out: List[SprintManifest] = []
    for p in sorted(d.glob("*.json")):
        try:
            out.append(load_manifest(p))
        except Exception:  # noqa: BLE001 — skip corrupt manifests
            continue
    return out


# ---------------------------------------------------------------------------
# State transitions
# ---------------------------------------------------------------------------


_ALLOWED_TRANSITIONS = {
    SprintStatus.PENDING.value: {
        SprintStatus.RUNNING.value,
        SprintStatus.CANCELLED.value,
    },
    SprintStatus.RUNNING.value: {
        SprintStatus.COMPLETED.value,
        SprintStatus.FAILED.value,
        SprintStatus.CANCELLED.value,
    },
    SprintStatus.COMPLETED.value: set(),
    SprintStatus.CANCELLED.value: set(),
    SprintStatus.FAILED.value: set(),
}


def transition(manifest: SprintManifest, new_status: str) -> None:
    """Validate + apply a sprint-level status transition in place."""
    current = manifest.status
    allowed = _ALLOWED_TRANSITIONS.get(current, set())
    if new_status not in allowed:
        raise ValueError(
            f"illegal sprint transition {current!r} -> {new_status!r} "
            f"(allowed: {sorted(allowed) or 'none (terminal)'})"
        )
    manifest.status = new_status
    if new_status == SprintStatus.RUNNING.value and manifest.started_at is None:
        manifest.started_at = now_epoch()
    if new_status in {
        SprintStatus.COMPLETED.value,
        SprintStatus.CANCELLED.value,
        SprintStatus.FAILED.value,
    }:
        manifest.ended_at = now_epoch()


# ---------------------------------------------------------------------------
# MVP stubs for follow-up work
# ---------------------------------------------------------------------------


def render_sprint_status_stub(manifest: SprintManifest) -> str:
    """MVP placeholder for the ``cos watch --sprint`` TUI.

    Full TUI (Bubbletea-style table with live tokens/tools/elapsed) is a
    follow-up task. This text renderer gives ``cos sprint status`` something
    usable now.
    """
    lines = [
        f"Sprint: {manifest.name} ({manifest.id})",
        f"Status: {manifest.status}",
        f"Commit strategy: {manifest.commit_strategy}",
        f"Tasks ({len(manifest.tasks)}):",
    ]
    for t in manifest.tasks:
        lines.append(f"  [{t.status}] {t.id} — {t.title} (model={t.model})")
    return "\n".join(lines)


def aggregate_test_results_stub(
    sprint_id: str,
    task_results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """MVP stub. Full implementation: parse per-task test output, sum
    passed/failed/skipped, emit ``SprintTestSummary`` canonical events.

    Follow-up task: implement parsing for pytest, go test, jest, vitest.
    """
    return {
        "sprint_id": sprint_id,
        "task_count": len(task_results),
        "status": "stubbed — aggregation pending ADR-036 follow-up",
    }


def consolidate_commits_stub(
    manifest: SprintManifest,
    project_dir: Path,
) -> Dict[str, Any]:
    """MVP stub. Full implementation: when ``commit_strategy == 'squash'``,
    on :class:`SprintCompleted` run ``git reset --soft <base>`` + single commit.

    Follow-up task: implement safe squash with rollback on failure.
    """
    return {
        "sprint_id": manifest.id,
        "strategy": manifest.commit_strategy,
        "status": "stubbed — commit consolidation pending ADR-036 follow-up",
    }

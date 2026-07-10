# SCOPE: both
"""Read-only Concurrent Agent Safety status composer.

This module intentionally does not repair or mutate repository state. It composes
existing Cognitive OS primitives into one status payload so orchestrators,
doctors, and dashboards can see cross-session safety facts without inventing a
parallel coordination system.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class SafetyFinding:
    """One read-only issue discovered by the safety status composer."""

    severity: str
    code: str
    message: str
    path: str | None = None


@dataclass(frozen=True)
class HookProjectionStatus:
    """Whether a safety hook appears in known harness projection surfaces."""

    hook: str
    claude: bool
    codex: bool
    config: bool
    claude_driver: bool
    codex_required: bool = True

    @property
    def complete_for_baseline(self) -> bool:
        """Return true when required projection surfaces are present."""

        codex_ok = self.codex if self.codex_required else True
        return self.claude and codex_ok and self.config and self.claude_driver


@dataclass(frozen=True)
class ConcurrentAgentSafetyStatus:
    """Aggregated read-only status for existing concurrent-agent primitives."""

    project_dir: str
    generated_at: str
    active_sessions: list[dict[str, Any]] = field(default_factory=list)
    locks: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    task_claims: list[dict[str, Any]] = field(default_factory=list)
    stash_alarm: dict[str, Any] | None = None
    claim_gate_projection: list[HookProjectionStatus] = field(default_factory=list)
    recent_agent_heartbeats: list[dict[str, Any]] = field(default_factory=list)
    findings: list[SafetyFinding] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize status into a JSON-safe dictionary."""

        data = asdict(self)
        data["claim_gate_projection"] = [
            {
                **asdict(item),
                "complete_for_baseline": item.complete_for_baseline,
            }
            for item in self.claim_gate_projection
        ]
        return data


def collect_status(project_dir: str | Path = ".") -> ConcurrentAgentSafetyStatus:
    """Collect cross-session safety status without modifying the repository."""

    root = Path(project_dir).resolve()
    findings: list[SafetyFinding] = []
    projections = _collect_projection_status(root)
    for projection in projections:
        if not projection.complete_for_baseline:
            findings.append(
                SafetyFinding(
                    severity="warn",
                    code="projection_incomplete",
                    message=(
                        f"{projection.hook} is not present in every required projection "
                        "surface for its supported harness surface"
                    ),
                    path=projection.hook,
                )
            )

    stash_alarm = _read_json_object(root / ".cognitive-os" / "runtime" / "stash-leak-alarm.json")
    if isinstance(stash_alarm, dict) and stash_alarm.get("blocking"):
        findings.append(
            SafetyFinding(
                severity="block",
                code="stash_leak_blocking",
                message="Blocking auto-pre-agent stash leak alarm is present",
                path=".cognitive-os/runtime/stash-leak-alarm.json",
            )
        )

    locks = {
        "git_index": _collect_git_index_locks(root),
        "edit": _collect_lock_metadata(root / ".cognitive-os" / "runtime" / "edit-locks"),
        "plan": _collect_lock_metadata(root / ".cognitive-os" / "runtime" / "plan-locks"),
        "resource": _collect_lock_metadata(root / ".cognitive-os" / "runtime" / "resource-leases"),
    }
    # ADR-238 #3: only emit ``concurrent_write`` when the SO ``sessions/locks``
    # directory actually exists. On a fresh non-SO consumer project the
    # directory is absent, and the empty key was leaking into JSON consumers
    # expecting the canonical 4-key portability schema.
    concurrent_write_dir = root / ".cognitive-os" / "sessions" / "locks"
    if concurrent_write_dir.is_dir():
        locks["concurrent_write"] = _collect_json_lock_files(concurrent_write_dir, root)

    return ConcurrentAgentSafetyStatus(
        project_dir=str(root),
        generated_at=_now_iso(),
        active_sessions=_collect_active_sessions(root),
        locks=locks,
        task_claims=_collect_task_claims(root),
        stash_alarm=stash_alarm if isinstance(stash_alarm, dict) else None,
        claim_gate_projection=projections,
        recent_agent_heartbeats=_collect_recent_agent_heartbeats(root),
        findings=findings,
    )


def status_to_json(status: ConcurrentAgentSafetyStatus, *, indent: int | None = 2) -> str:
    """Render a status object as stable JSON."""

    return json.dumps(status.to_dict(), indent=indent, sort_keys=True)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _read_json_object(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _collect_projection_status(root: Path) -> list[HookProjectionStatus]:
    hooks = (
        ("orchestrator-claim-gate.sh", True),
        ("plan-claim-validator.sh", False),
        ("concurrent-write-guard.sh", False),
    )
    claude = _read_text(root / ".claude" / "settings.json")
    codex = _read_text(root / ".codex" / "hooks.json")
    config = _read_text(root / "cognitive-os.yaml")
    claude_driver = _read_text(root / "scripts" / "_lib" / "settings-driver-claude-code.sh")
    return [
        HookProjectionStatus(
            hook=f"hooks/{hook}",
            claude=f"hooks/{hook}" in claude,
            codex=f"hooks/{hook}" in codex,
            config=f"hooks/{hook}" in config,
            claude_driver=f"hooks/{hook}" in claude_driver,
            codex_required=codex_required,
        )
        for hook, codex_required in hooks
    ]


def _collect_active_sessions(root: Path) -> list[dict[str, Any]]:
    sessions_dir = root / ".cognitive-os" / "sessions"
    active_file = sessions_dir / "active-sessions.json"
    data = _read_json_object(active_file)
    if isinstance(data, dict) and isinstance(data.get("sessions"), list):
        return [_clean_mapping(item) for item in data["sessions"] if isinstance(item, Mapping)]

    sessions: list[dict[str, Any]] = []
    if not sessions_dir.is_dir():
        return sessions
    for meta_path in sorted(sessions_dir.glob("*/meta.json")):
        item = _read_json_object(meta_path)
        if isinstance(item, dict):
            sessions.append(_clean_mapping(item))
    return sessions


def _collect_git_index_locks(root: Path) -> list[dict[str, Any]]:
    lock_dir = root / ".cognitive-os" / "runtime" / "git-index.lock"
    meta = _read_json_object(lock_dir / "meta.json")
    if isinstance(meta, dict):
        item = _clean_mapping(meta)
        item.setdefault("lock_path", _relpath(lock_dir, root))
        return [item]
    return []


def _collect_task_claims(root: Path) -> list[dict[str, Any]]:
    data = _read_json_object(root / ".cognitive-os" / "runtime" / "task-claims.json")
    if not isinstance(data, dict) or not isinstance(data.get("claims"), dict):
        return []
    claims = [item for item in data["claims"].values() if isinstance(item, Mapping)]
    return [_clean_mapping(item) for item in sorted(claims, key=lambda item: str(item.get("task_id", "")))]


def _collect_lock_metadata(root_dir: Path) -> list[dict[str, Any]]:
    if not root_dir.is_dir():
        return []
    results: list[dict[str, Any]] = []
    for lock_dir in sorted(path for path in root_dir.rglob("*") if path.is_dir()):
        meta_json = _read_json_object(lock_dir / "meta.json")
        if isinstance(meta_json, dict):
            item = _clean_mapping(meta_json)
        else:
            item = _parse_simple_yaml(lock_dir / "meta.yaml")
        if item:
            item.setdefault("lock_path", str(lock_dir))
            results.append(item)
    return results


def _collect_json_lock_files(root_dir: Path, project_root: Path) -> list[dict[str, Any]]:
    if not root_dir.is_dir():
        return []
    results: list[dict[str, Any]] = []
    for lock_file in sorted(root_dir.glob("*.lock")):
        item = _read_json_object(lock_file)
        if isinstance(item, dict):
            clean = _clean_mapping(item)
            clean.setdefault("lock_path", _relpath(lock_file, project_root))
            results.append(clean)
    return results


def _parse_simple_yaml(path: Path) -> dict[str, Any]:
    text = _read_text(path)
    if not text:
        return {}
    parsed: dict[str, Any] = {}
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"')
        if key:
            parsed[key] = value
    return parsed


def _collect_recent_agent_heartbeats(root: Path) -> list[dict[str, Any]]:
    bus_dir = root / ".cognitive-os" / "agent-bus"
    if not bus_dir.is_dir():
        return []
    heartbeats: list[dict[str, Any]] = []
    for heartbeat_path in sorted(bus_dir.glob("*/heartbeat.jsonl")):
        latest = _latest_jsonl_object(heartbeat_path)
        if isinstance(latest, dict):
            latest.setdefault("agent_id", heartbeat_path.parent.name)
            heartbeats.append(_clean_mapping(latest))
    return sorted(heartbeats, key=lambda item: str(item.get("timestamp", item.get("timestamp_epoch", ""))), reverse=True)[:20]


def _latest_jsonl_object(path: Path) -> Any:
    try:
        lines = [line for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()]
    except OSError:
        return None
    for line in reversed(lines):
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    return None


def _clean_mapping(raw: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): _json_safe(value) for key, value in raw.items()}


def _json_safe(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Mapping):
        return _clean_mapping(value)
    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray, str)):
        return [_json_safe(item) for item in value]
    return str(value)


def _relpath(path: Path, root: Path) -> str:
    try:
        return os.fspath(path.relative_to(root))
    except ValueError:
        return os.fspath(path)

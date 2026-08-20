# SCOPE: os-only
"""Cross-session lineage and recursion fuses (harness recursivo, 2026-08-19).

Three things live here, and nothing else:

1. **Lineage** — who launched whom. ``parent_session_id`` was declared in
   :mod:`cos_lib.hook_event_types` and written by nobody; this module is the
   writer. A parent that cannot be known is recorded as ``None``, never as an
   invented id: an absent edge is a gap you can see, a fabricated one is a lie
   you cannot.

2. **Two fuses, because depth and volume are different quantities.**
   Depth is a property of the *path*: it travels in an inherited environment
   variable incremented by one per generation, and three siblings sharing a
   depth is correct, not a bug (`pi-subagents#239`). Total and width are
   properties of the *tree*: no environment variable can bound them, so they
   live in a counter file updated under an exclusive lock.

3. **A decision function that never launches anything.**
   :func:`evaluate_relaunch` is pure with respect to the process table: it
   reads state and returns a verdict. Launching is somebody else's job, and
   that job is unreachable unless an operator armed it by writing a file.

Ordering of the fuses follows what the survey found saves most
(``docs/06-Daily/reports/investigacion-harness-recursivo-2026-08-19.md``):
runtime-imposed total first, stall detection second, and depth last — depth
is checked, but it is the fuse most often found broken when probed, so it is
not the one carrying the weight.
"""
from __future__ import annotations

import fcntl
import json
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Environment contract ────────────────────────────────────────────────────
# These are set by the launcher on the CHILD process, never by a shell prefix.
# A `VAR=1 claude ...` prefix does reach the child harness (it is that
# process's own environment); what it does NOT reach is a hook of the CURRENT
# session, because that hook is a child of the harness, not of the Bash tool.
ENV_PARENT = "COS_PARENT_SESSION_ID"
ENV_DEPTH = "COS_SESSION_DEPTH"
ENV_ROOT = "COS_LINEAGE_ROOT_ID"
ENV_GOAL = "COS_LINEAGE_GOAL_ID"
#: Operator kill-switch. Honoured only via `export` before the harness starts
#: or via the `env` block of .claude/settings.json — see module docstring.
ENV_DISABLE = "COS_DISABLE_AUTONOMOUS_RELAUNCH"

#: Literal an operator must write into the arm file. Chosen so that a document
#: *about* arming does not arm anything: the token must be the file's first
#: JSON object, not a substring of prose.
ARM_TOKEN = "ARMED"

#: Arm-file modes. ``dry-run`` decides and records; only ``spawn`` starts a
#: process. Arming defaults to ``dry-run`` because a Stop hook that both lets
#: goal-stop-gate block the stop (continuing the goal in this session) and
#: spawns a successor for the same goal continues it twice. Turning that into a
#: single opt-in flag would hide the hazard; two deliberate acts surface it.
MODE_DRY_RUN = "dry-run"
MODE_SPAWN = "spawn"

# ── Defaults. Low on purpose; see ADR discussion in the report. ─────────────
DEFAULT_MAX_DEPTH = 3
DEFAULT_MAX_TOTAL = 5
DEFAULT_MAX_WIDTH = 2
DEFAULT_MAX_NO_PROGRESS = 2


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class LineageRecord:
    """One session, and the session that launched it (if that is known)."""

    session_id: str
    parent_session_id: str | None
    depth: int
    root_id: str
    recorded_at: str
    source: str = "unknown"
    pid: int = 0
    goal_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FuseLimits:
    max_depth: int = DEFAULT_MAX_DEPTH
    max_total: int = DEFAULT_MAX_TOTAL
    max_width: int = DEFAULT_MAX_WIDTH
    max_no_progress: int = DEFAULT_MAX_NO_PROGRESS


@dataclass
class RelaunchDecision:
    """Verdict of :func:`evaluate_relaunch`. ``allowed`` gates the launch path."""

    allowed: bool
    fuse: str
    reason: str
    session_id: str = ""
    parent_depth: int = 0
    child_depth: int = 0
    root_id: str = ""
    total_used: int = 0
    width_used: int = 0
    limits: dict[str, int] = field(default_factory=dict)
    decided_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── Depth: the path property, carried in the environment ────────────────────

def current_depth(env: dict[str, str] | None = None) -> int:
    """Depth of the *current* session, from the inherited variable.

    A session started by a human has no variable and is depth 0. A malformed
    or negative value is treated as unknown-and-therefore-deep: it returns a
    value that will trip the depth fuse rather than one that will pass it.
    """
    src = os.environ if env is None else env
    raw = src.get(ENV_DEPTH, "")
    if raw == "":
        return 0
    try:
        val = int(raw)
    except (TypeError, ValueError):
        # Garbage in the variable is not evidence of shallowness.
        return DEFAULT_MAX_DEPTH
    return val if val >= 0 else DEFAULT_MAX_DEPTH


def resolve_parent(env: dict[str, str] | None = None) -> str | None:
    """Parent session id from the environment, or ``None`` when unknown."""
    src = os.environ if env is None else env
    val = (src.get(ENV_PARENT) or "").strip()
    return val or None


def resolve_root(session_id: str, env: dict[str, str] | None = None) -> str:
    """Lineage root id: inherited if present, otherwise this session is the root."""
    src = os.environ if env is None else env
    val = (src.get(ENV_ROOT) or "").strip()
    return val or session_id


def child_env(
    *,
    parent_session_id: str,
    root_id: str,
    parent_depth: int,
    goal_id: str = "",
) -> dict[str, str]:
    """Environment overlay handed to a child session. Depth is parent + 1."""
    env = {
        ENV_PARENT: parent_session_id,
        ENV_ROOT: root_id,
        ENV_DEPTH: str(parent_depth + 1),
    }
    if goal_id:
        env[ENV_GOAL] = goal_id
    return env


# ── Store: the tree properties, on disk, under a lock ───────────────────────

class LineageStore:
    """Append-only lineage plus a locked counter file.

    The counter is the fuse that an environment variable cannot be. It is
    keyed by lineage root so that two unrelated roots do not starve each
    other, and it is never reset at session start — a counter that resets per
    session is decoration, not a fuse.
    """

    def __init__(self, base_dir: Path | str):
        self.base_dir = Path(base_dir)
        self.lineage_path = self.base_dir / "lineage.jsonl"
        self.decisions_path = self.base_dir / "decisions.jsonl"
        self.counters_path = self.base_dir / "counters.json"
        self.arm_path = self.base_dir / "autonomy.enabled"

    # -- arming ------------------------------------------------------------
    def arm_mode(self) -> str:
        """``dry-run`` (default) or ``spawn``. Unreadable arm file → dry-run."""
        try:
            payload = json.loads(self.arm_path.read_text(encoding="utf-8"))
            mode = str(payload.get("mode") or MODE_DRY_RUN)
        except Exception:  # noqa: BLE001
            return MODE_DRY_RUN
        return mode if mode == MODE_SPAWN else MODE_DRY_RUN

    def is_armed(self, goal_id: str = "") -> tuple[bool, str]:
        """``(armed, reason)``. Absent file → not armed, and that is the default.

        Off-by-default is a decision written down, not an accident of the
        filesystem: every other method creates its directories, this one
        refuses to, and the launch path is gated on this method alone.
        """
        if not self.arm_path.is_file():
            return False, f"not armed: {self.arm_path} does not exist"
        try:
            raw = self.arm_path.read_text(encoding="utf-8").strip()
            payload = json.loads(raw)
        except Exception as exc:  # noqa: BLE001
            return False, f"not armed: arm file unreadable or not JSON ({exc})"
        if not isinstance(payload, dict):
            return False, "not armed: arm file is not a JSON object"
        if payload.get("state") != ARM_TOKEN:
            return False, f"not armed: arm file state is {payload.get('state')!r}"
        armed_goal = str(payload.get("goal_id") or "")
        if not armed_goal:
            return False, "not armed: arm file names no goal_id"
        if goal_id and armed_goal != goal_id:
            return False, (
                f"not armed for this goal: armed for {armed_goal!r}, "
                f"asked for {goal_id!r}"
            )
        expires = payload.get("expires_at_epoch")
        if isinstance(expires, (int, float)) and time.time() > expires:
            return False, "not armed: arm file expired"
        return True, f"armed for goal {armed_goal!r}"

    def arm(self, goal_id: str, ttl_seconds: int = 3600, mode: str = MODE_DRY_RUN) -> Path:
        if mode not in (MODE_DRY_RUN, MODE_SPAWN):
            raise ValueError(f"unknown arm mode: {mode!r}")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "state": ARM_TOKEN,
            "goal_id": goal_id,
            "mode": mode,
            "armed_at": _now(),
            "expires_at_epoch": time.time() + ttl_seconds,
        }
        _atomic_write_json(self.arm_path, payload)
        return self.arm_path

    def disarm(self) -> bool:
        if self.arm_path.exists():
            self.arm_path.unlink()
            return True
        return False

    # -- lineage -----------------------------------------------------------
    def record_session(self, record: LineageRecord) -> LineageRecord:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        _locked_append(self.lineage_path, json.dumps(record.to_dict(), sort_keys=True))
        return record

    def records(self) -> list[LineageRecord]:
        if not self.lineage_path.is_file():
            return []
        out: list[LineageRecord] = []
        for line in self.lineage_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            known = {f for f in LineageRecord.__dataclass_fields__}  # type: ignore[attr-defined]
            out.append(LineageRecord(**{k: v for k, v in data.items() if k in known}))
        return out

    def chain(self, session_id: str) -> list[LineageRecord]:
        """Root-to-session chain, reconstructed from disk. Cycle-safe."""
        by_id = {r.session_id: r for r in self.records()}
        seen: set[str] = set()
        rev: list[LineageRecord] = []
        cur: str | None = session_id
        while cur and cur in by_id and cur not in seen:
            seen.add(cur)
            rec = by_id[cur]
            rev.append(rec)
            cur = rec.parent_session_id
        rev.reverse()
        return rev

    # -- counters ----------------------------------------------------------
    def read_counters(self, root_id: str) -> dict[str, Any]:
        data = _read_json(self.counters_path)
        entry = data.get(root_id) or {}
        return {
            "total": int(entry.get("total", 0)),
            "children": dict(entry.get("children", {})),
        }

    def reserve_slot(self, root_id: str, parent_session_id: str, limits: FuseLimits) -> tuple[bool, str, dict[str, Any]]:
        """Check-and-increment under one exclusive lock.

        Reading the counter and then incrementing it in two steps is how two
        concurrent Stop hooks both pass a cap of one. The whole transaction
        happens inside the lock, and the caller only launches on ``True``.
        """
        self.base_dir.mkdir(parents=True, exist_ok=True)
        with _exclusive(self.counters_path) as fh:
            fh.seek(0)
            raw = fh.read()
            try:
                data = json.loads(raw) if raw.strip() else {}
            except json.JSONDecodeError:
                data = {}
            entry = data.setdefault(root_id, {"total": 0, "children": {}})
            total = int(entry.get("total", 0))
            children = entry.setdefault("children", {})
            width = int(children.get(parent_session_id, 0))

            if total >= limits.max_total:
                return False, f"total cap reached: {total}/{limits.max_total} sessions in lineage {root_id}", {"total": total, "width": width}
            if width >= limits.max_width:
                return False, f"width cap reached: parent {parent_session_id} already launched {width}/{limits.max_width} children", {"total": total, "width": width}

            entry["total"] = total + 1
            children[parent_session_id] = width + 1
            fh.seek(0)
            fh.truncate()
            fh.write(json.dumps(data, indent=2, sort_keys=True))
            fh.flush()
            os.fsync(fh.fileno())
            return True, "slot reserved", {"total": total + 1, "width": width + 1}

    # -- decisions ---------------------------------------------------------
    def record_decision(self, decision: RelaunchDecision) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        _locked_append(self.decisions_path, json.dumps(decision.to_dict(), sort_keys=True))

    def decisions(self) -> list[dict[str, Any]]:
        if not self.decisions_path.is_file():
            return []
        out = []
        for line in self.decisions_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return out


# ── The decision ────────────────────────────────────────────────────────────

def evaluate_relaunch(
    store: LineageStore,
    *,
    session_id: str,
    goal_id: str = "",
    consecutive_no_progress: int = 0,
    limits: FuseLimits | None = None,
    env: dict[str, str] | None = None,
) -> RelaunchDecision:
    """Decide whether a child session may be launched. Launches nothing.

    Fuse order is deliberate: the switch first (a disarmed repo must not even
    read a counter), then the kill-switch, then stall, then the tree caps,
    then depth. Depth last because the survey found it is the cap most often
    published and least often binding.
    """
    lim = limits or FuseLimits()
    src = os.environ if env is None else env
    root_id = resolve_root(session_id, src)
    depth = current_depth(src)
    limits_dict = asdict(lim)

    def _no(fuse: str, reason: str, total: int = 0, width: int = 0) -> RelaunchDecision:
        return RelaunchDecision(
            allowed=False, fuse=fuse, reason=reason, session_id=session_id,
            parent_depth=depth, child_depth=depth + 1, root_id=root_id,
            total_used=total, width_used=width, limits=limits_dict,
        )

    armed, arm_reason = store.is_armed(goal_id)
    if not armed:
        return _no("disarmed", arm_reason)

    if (src.get(ENV_DISABLE) or "").strip() == "1":
        return _no("kill-switch", f"{ENV_DISABLE}=1 in the harness environment")

    if consecutive_no_progress >= lim.max_no_progress:
        return _no(
            "stall",
            f"no progress for {consecutive_no_progress} consecutive evaluations "
            f"(limit {lim.max_no_progress}); relaunching would buy nothing",
        )

    if depth + 1 > lim.max_depth:
        return _no("depth", f"depth cap reached: child would be generation {depth + 1}, cap {lim.max_depth}")

    counters = store.read_counters(root_id)
    if counters["total"] >= lim.max_total:
        return _no("total", f"total cap reached: {counters['total']}/{lim.max_total} in lineage {root_id}", counters["total"])
    width = int(counters["children"].get(session_id, 0))
    if width >= lim.max_width:
        return _no("width", f"width cap reached: {width}/{lim.max_width} children of {session_id}", counters["total"], width)

    return RelaunchDecision(
        allowed=True, fuse="none",
        reason=f"all fuses clear ({arm_reason}); child would be generation {depth + 1}",
        session_id=session_id, parent_depth=depth, child_depth=depth + 1,
        root_id=root_id, total_used=counters["total"], width_used=width,
        limits=limits_dict,
    )


# ── Small file primitives ───────────────────────────────────────────────────

class _exclusive:
    """Context manager yielding a read/write handle holding an exclusive lock."""

    def __init__(self, path: Path):
        self.path = path
        self._fh = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch()
        self._fh = open(self.path, "r+", encoding="utf-8")
        fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX)
        return self._fh

    def __exit__(self, *exc):
        if self._fh is not None:
            try:
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
            finally:
                self._fh.close()
        return False


def _locked_append(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            fh.write(line + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        raw = path.read_text(encoding="utf-8").strip()
        return json.loads(raw) if raw else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp{os.getpid()}")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def default_store(project_dir: Path | str) -> LineageStore:
    return LineageStore(Path(project_dir) / ".cognitive-os" / "lineage")

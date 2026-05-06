# SCOPE: os-only
"""Agent-bus metrics adapter — ADR-028b D1.C.

Bridges agent_bus heartbeat events (real-time, pub/sub) to durable
`MetricEvent` records (append-only JSONL) for offline analysis,
watchdog scans, and dashboards that don't run a subscriber.

Principle: don't duplicate agent_bus infrastructure. Subscribe to
what's already there; emit MetricEvents only on state transitions.

Python 3.9+ compatible, stdlib + `lib.metric_event`.
"""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# lib/ import layout: agent_bus lives in packages/agent-coordination/lib.
# Keep imports lazy/guarded so the module is importable without Valkey
# installed.
try:
    # lib/agent_bus.py is a symlink to packages/agent-coordination/lib/agent_bus.py.
    # Python can't import package paths with hyphens, so we go through the symlink.
    from lib.agent_bus import (  # type: ignore
        OrchestratorSubscriber,
        _DEFAULT_FALLBACK_DIR,  # type: ignore
        _DEFAULT_VALKEY_URL,  # type: ignore
    )
except Exception:  # pragma: no cover — fallback path used under tests
    OrchestratorSubscriber = None  # type: ignore[assignment]
    _DEFAULT_FALLBACK_DIR = ".cognitive-os/agent-bus"
    _DEFAULT_VALKEY_URL = os.environ.get(
        "VALKEY_URL",
        os.environ.get("COS_VALKEY_URL", "redis://localhost:6379"),
    )

from lib.metric_event import MetricEvent, append_event


# --- Constants --------------------------------------------------------------

_DEFAULT_STALE_SECONDS = 300
_DEFAULT_METRICS_PATH = ".cognitive-os/metrics/agent-heartbeat.jsonl"


def _project_root() -> Path:
    return Path(
        os.environ.get(
            "COGNITIVE_OS_PROJECT_DIR",
            os.environ.get("CLAUDE_PROJECT_DIR", str(Path(__file__).resolve().parent.parent)),
        )
    )


# --- Adapter ----------------------------------------------------------------


class AgentBusMetrics:
    """Bridges agent_bus heartbeats to MetricEvent JSONL records.

    Uses `OrchestratorSubscriber` when Valkey is available; reads FallbackBus
    files directly otherwise. Both paths produce identical MetricEvent output.

    Args:
        metrics_path: JSONL sink. Default `.cognitive-os/metrics/agent-heartbeat.jsonl`.
        valkey_url: Redis-compatible URL.
        fallback_dir: FallbackBus base directory. Default `.cognitive-os/agent-bus`.
        stale_threshold_seconds: Age beyond which an agent is considered stale.
        subscriber: pre-constructed OrchestratorSubscriber (for tests/reuse).
    """

    def __init__(
        self,
        metrics_path: Optional[str] = None,
        valkey_url: str = _DEFAULT_VALKEY_URL,
        fallback_dir: Optional[str] = None,
        stale_threshold_seconds: int = _DEFAULT_STALE_SECONDS,
        subscriber: Any = None,
    ) -> None:
        root = _project_root()
        self._metrics_path = str(
            Path(metrics_path) if metrics_path else root / _DEFAULT_METRICS_PATH
        )
        self._fallback_dir = Path(fallback_dir) if fallback_dir else root / _DEFAULT_FALLBACK_DIR
        self._stale_threshold_seconds = int(stale_threshold_seconds)
        self._valkey_url = valkey_url

        # Track agents we have already emitted agent_launched for — so
        # intermediate alive=True beats don't produce duplicate events.
        self._seen_launched: Dict[str, bool] = {}
        self._lock = threading.Lock()

        # Optional subscriber for Valkey path. Lazy — only constructed if the
        # caller asks for subscribe(); tests inject their own.
        self._subscriber = subscriber

    # -- Event callback ----------------------------------------------------

    def on_heartbeat_event(self, data: Dict[str, Any]) -> None:
        """Callback invoked per heartbeat message.

        Emits exactly one MetricEvent per state transition:
          - first heartbeat for an agent → agent_launched
          - alive==False              → agent_completed
          - everything else           → silence (transport already logged
                                        it in agent_bus, repeating here
                                        is waste).
        """
        if not isinstance(data, dict):
            return
        agent_id = str(data.get("agent_id", "")).strip()
        if not agent_id:
            return
        alive = bool(data.get("alive", True))
        phase = str(data.get("phase", "") or data.get("step", ""))
        tokens_used = int(data.get("tokens_used", 0) or 0)
        session_id = str(data.get("session_id", "") or os.environ.get("COGNITIVE_OS_SESSION_ID", ""))

        with self._lock:
            seen = self._seen_launched.get(agent_id, False)

            if not alive:
                event_type = "agent_completed"
                # Clear tracker so a re-launched agent_id produces a fresh
                # agent_launched next time (unlikely but supported).
                self._seen_launched.pop(agent_id, None)
            elif not seen:
                event_type = "agent_launched"
                self._seen_launched[agent_id] = True
            else:
                # Intermediate alive=True beat — no event emitted.
                return

        self._emit(
            event_type=event_type,
            agent_id=agent_id,
            session_id=session_id,
            phase=phase,
            alive=alive,
            tokens_used=tokens_used,
        )

    # -- Stale / live detection -------------------------------------------

    def scan_stale(self, max_age_seconds: Optional[int] = None) -> List[Dict[str, Any]]:
        """Return agents whose last heartbeat is older than max_age_seconds."""
        threshold = int(max_age_seconds if max_age_seconds is not None else self._stale_threshold_seconds)
        now = time.time()
        out: List[Dict[str, Any]] = []
        for rec in self._collect_last_beats():
            age = now - float(rec.get("last_beat_epoch", 0.0))
            if age > threshold:
                out.append({**rec, "age_seconds": age})
        return out

    def list_live(self, max_age_seconds: Optional[int] = None) -> List[Dict[str, Any]]:
        """Return agents with a heartbeat within max_age_seconds."""
        threshold = int(max_age_seconds if max_age_seconds is not None else self._stale_threshold_seconds)
        now = time.time()
        out: List[Dict[str, Any]] = []
        for rec in self._collect_last_beats():
            age = now - float(rec.get("last_beat_epoch", 0.0))
            if age <= threshold:
                out.append({**rec, "age_seconds": age})
        return out

    # -- Hung-agent remediation -------------------------------------------

    def mark_hung_and_publish(self, agent_id: str) -> Dict[str, Any]:
        """Flag an agent as hung and signal it to stop.

        1. Emits MetricEvent(event_type="agent_hung").
        2. Publishes `{"command": "stop"}` to `cos:agent:{agent_id}:control`.
           When Valkey is unavailable, writes to the FallbackBus control file.
        """
        agent_id = str(agent_id or "").strip()
        if not agent_id:
            raise ValueError("agent_id is required")

        age = None
        last = self._last_beat_for(agent_id)
        if last is not None:
            age = time.time() - float(last.get("timestamp_epoch", last.get("last_beat_epoch", 0.0)))

        self._emit(
            event_type="agent_hung",
            agent_id=agent_id,
            session_id=os.environ.get("COGNITIVE_OS_SESSION_ID", ""),
            phase=str((last or {}).get("phase", "")),
            alive=False,
            tokens_used=int((last or {}).get("tokens_used", 0) or 0),
            extra={"age_seconds": age} if age is not None else None,
        )

        sent_via = self._send_stop_signal(agent_id)
        with self._lock:
            self._seen_launched.pop(agent_id, None)
        return {"agent_id": agent_id, "stop_sent_via": sent_via, "age_seconds": age}

    # -- Valkey subscription (opt-in) --------------------------------------

    def subscribe(self) -> Any:
        """Attach the adapter to a live OrchestratorSubscriber.

        Constructs one if not injected, registers the heartbeat callback,
        and calls `subscribe_all()` so the subscriber starts listening on
        the wildcard heartbeat channel. Returns the subscriber.
        """
        if self._subscriber is None:
            if OrchestratorSubscriber is None:
                raise RuntimeError(
                    "agent_bus.OrchestratorSubscriber unavailable — install 'redis' or "
                    "run in a checkout with lib/agent_bus.py on the path."
                )
            self._subscriber = OrchestratorSubscriber(
                valkey_url=self._valkey_url,
                fallback_dir=str(self._fallback_dir),
            )
        # Register the callback BEFORE subscribing so no early messages are lost.
        self._subscriber.on_heartbeat(self.on_heartbeat_event)
        # Activate the subscription — subscribe_all() psubscribes to the
        # wildcard heartbeat/progress/question channels and starts the
        # listener thread. Without this, on_heartbeat_event is never invoked.
        try:
            self._subscriber.subscribe_all()
        except Exception:
            # Fallback mode (no Valkey) — subscriber has no channels to join,
            # but on_heartbeat_event still callable by direct dispatch in tests.
            pass
        return self._subscriber

    # -- Internals ---------------------------------------------------------

    def _emit(
        self,
        *,
        event_type: str,
        agent_id: str,
        session_id: str,
        phase: str,
        alive: bool,
        tokens_used: int,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        payload: Dict[str, Any] = {
            "agent_id": agent_id,
            "session_id": session_id,
            "phase": phase,
            "alive": alive,
            "tokens_used": tokens_used,
        }
        if extra:
            payload.update(extra)
        ev = MetricEvent(
            source="agent_bus_metrics",
            event_type=event_type,
            payload=payload,
        )
        append_event(self._metrics_path, ev)

    def _collect_last_beats(self) -> List[Dict[str, Any]]:
        """Return the most-recent heartbeat per agent from EITHER source.

        Prefers the in-memory subscriber state (Valkey path) when available;
        falls back to scanning FallbackBus files.
        """
        sub = self._subscriber
        if sub is not None and getattr(sub, "_use_valkey", False):
            # Snapshot the subscriber's in-memory dict safely.
            try:
                with getattr(sub, "_lock", threading.Lock()):
                    beats = dict(getattr(sub, "_agent_heartbeats", {}))
            except Exception:
                beats = {}
            out: List[Dict[str, Any]] = []
            for agent_id, hb in beats.items():
                ts = float(hb.get("timestamp_epoch", 0.0))
                out.append({
                    "agent_id": agent_id,
                    "last_beat_epoch": ts,
                    "last_phase": str(hb.get("phase", "") or hb.get("step", "")),
                })
            return out

        # FallbackBus path: scan disk.
        return self._scan_fallback_dir()

    def _scan_fallback_dir(self) -> List[Dict[str, Any]]:
        """Read the last heartbeat.jsonl entry for each agent directory."""
        out: List[Dict[str, Any]] = []
        base = self._fallback_dir
        if not base.is_dir():
            return out
        for agent_dir in sorted(base.iterdir()):
            if not agent_dir.is_dir():
                continue
            hb_file = agent_dir / "heartbeat.jsonl"
            if not hb_file.is_file():
                continue
            last = _read_last_jsonl_line(hb_file)
            if not last:
                continue
            out.append({
                "agent_id": agent_dir.name,
                "last_beat_epoch": float(last.get("timestamp_epoch", 0.0)),
                "last_phase": str(last.get("phase", "") or last.get("step", "")),
            })
        return out

    def _last_beat_for(self, agent_id: str) -> Optional[Dict[str, Any]]:
        sub = self._subscriber
        if sub is not None and getattr(sub, "_use_valkey", False):
            try:
                with getattr(sub, "_lock", threading.Lock()):
                    return dict(getattr(sub, "_agent_heartbeats", {}).get(agent_id, {})) or None
            except Exception:
                return None
        hb_file = self._fallback_dir / agent_id / "heartbeat.jsonl"
        if not hb_file.is_file():
            return None
        return _read_last_jsonl_line(hb_file)

    def _send_stop_signal(self, agent_id: str) -> str:
        """Try Valkey publish first; fall back to FallbackBus control file."""
        payload = {"type": "control", "agent_id": agent_id, "command": "stop", "timestamp_epoch": time.time()}
        # Valkey path via subscriber's own client (reuse connection if present)
        sub = self._subscriber
        client = getattr(sub, "_client", None) if sub is not None else None
        if client is not None and getattr(sub, "_use_valkey", False):
            try:
                client.publish(f"cos:agent:{agent_id}:control", json.dumps(payload))
                return "valkey"
            except Exception:
                pass
        # FallbackBus path
        ctrl_dir = self._fallback_dir / agent_id
        ctrl_dir.mkdir(parents=True, exist_ok=True)
        ctrl_file = ctrl_dir / "control.jsonl"
        with open(ctrl_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")
        interrupt = ctrl_dir / "interrupt"
        tmp = ctrl_dir / ".interrupt.tmp"
        tmp.write_text(json.dumps({**payload, "type": "interrupt"}), encoding="utf-8")
        tmp.replace(interrupt)
        return "fallback"


# --- Helpers ---------------------------------------------------------------


def _read_last_jsonl_line(path: Path) -> Optional[Dict[str, Any]]:
    """Return the last well-formed JSON object in `path`, or None.

    Safe for empty files and trailing garbage.
    """
    try:
        with open(path, "rb") as f:
            # Read tail only; heartbeat files can grow large.
            try:
                f.seek(0, os.SEEK_END)
                size = f.tell()
                tail = 4096 if size > 4096 else size
                f.seek(size - tail)
                raw = f.read().decode("utf-8", errors="ignore")
            except Exception:
                f.seek(0)
                raw = f.read().decode("utf-8", errors="ignore")
    except OSError:
        return None

    for line in reversed([ln for ln in raw.splitlines() if ln.strip()]):
        try:
            parsed = json.loads(line)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, ValueError):
            continue
    return None


__all__ = ["AgentBusMetrics"]

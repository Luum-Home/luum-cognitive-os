#!/usr/bin/env python3
"""cos-executor — harness-agnostic live event daemon (ADR-034).

Subscribes to the Valkey agent pub/sub bus (or tails FallbackBus JSONL
files when Valkey is down) and re-publishes normalised live events on
the aggregated channel ``cos:canonical:live``. Consumers (``cos-watch``,
cost dashboards, MLflow bridge) subscribe to that single channel.

Behaviour:
- PID-locked via ``.cognitive-os/runtime/cos-executor.pid`` (mirrors
  ``hooks/reaper-heartbeat.sh``). Double-starts are a no-op.
- Writes ``.cognitive-os/runtime/orchestrator-mode`` = ``executor`` on
  startup, removes it on shutdown. ``orchestrator_capabilities.py`` may
  read this file to flip the banner indicator even if the env var is
  not exported.
- Graceful SIGTERM / SIGINT: unsubscribes, cleans state files, exits 0.
- Never raises into its caller; logs to
  ``.cognitive-os/metrics/executor.log``.

CLI:
    cos-executor.py --daemon           start (idempotent)
    cos-executor.py --status           print ALIVE or DEAD + pid
    cos-executor.py --stop             send SIGTERM to running daemon
    cos-executor.py --foreground       run in-process (for tests)
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

# The orchestrator wraps agent messages with "type":"heartbeat|progress|..."
# and publishes on cos:agent:*. We rebroadcast those plus any canonical
# events written by harness adapters into cos:canonical:live.

CANONICAL_CHANNEL = "cos:canonical:live"
MAX_EVENTS_PER_SEC = 50
FALLBACK_POLL_INTERVAL = 0.5


def _project_dir() -> Path:
    return Path(os.environ.get("COGNITIVE_OS_PROJECT_DIR",
                               os.environ.get("CLAUDE_PROJECT_DIR",
                                              os.getcwd())))


def _runtime_dir() -> Path:
    d = _project_dir() / ".cognitive-os" / "runtime"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _metrics_dir() -> Path:
    d = _project_dir() / ".cognitive-os" / "metrics"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _pid_file() -> Path:
    return _runtime_dir() / "cos-executor.pid"


def _mode_file() -> Path:
    return _runtime_dir() / "orchestrator-mode"


def _log_path() -> Path:
    return _metrics_dir() / "executor.log"


def _log(msg: str) -> None:
    try:
        with open(_log_path(), "a", encoding="utf-8") as fh:
            fh.write(f"[{time.strftime('%Y-%m-%dT%H:%M:%S')}] {msg}\n")
    except OSError:
        pass


# ---------------------------------------------------------------------------
# PID-file guard (mirrors reaper-heartbeat.sh semantics)
# ---------------------------------------------------------------------------


def _existing_pid() -> Optional[int]:
    pf = _pid_file()
    if not pf.exists():
        return None
    try:
        pid = int(pf.read_text().strip() or "0")
    except (OSError, ValueError):
        return None
    if pid <= 0:
        return None
    try:
        os.kill(pid, 0)
        return pid
    except OSError:
        return None


def _claim_pid() -> None:
    _pid_file().write_text(str(os.getpid()))


def _release_pid() -> None:
    try:
        _pid_file().unlink()
    except OSError:
        pass


def _write_mode() -> None:
    try:
        _mode_file().write_text("executor")
    except OSError:
        pass


def _clear_mode() -> None:
    try:
        _mode_file().unlink()
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Executor core
# ---------------------------------------------------------------------------


class CosExecutor:
    """Subscribe to the agent bus, re-publish on the canonical channel."""

    def __init__(self, valkey_url: Optional[str] = None) -> None:
        self.valkey_url = valkey_url or os.environ.get(
            "VALKEY_URL",
            os.environ.get("COS_VALKEY_URL", "redis://localhost:6379"),
        )
        self._client: Any = None
        self._pubsub: Any = None
        self._use_valkey = False
        self._stop = threading.Event()
        self._published = 0
        self._last_rate_reset = time.time()
        self._rate_window_count = 0

    # ---- setup ------------------------------------------------------

    def _connect(self) -> None:
        try:
            import redis  # type: ignore
            self._client = redis.Redis.from_url(
                self.valkey_url, socket_connect_timeout=2, decode_responses=True
            )
            self._client.ping()
            self._pubsub = self._client.pubsub()
            self._pubsub.psubscribe("cos:agent:*:*")
            self._use_valkey = True
            _log("connected to Valkey, psubscribed cos:agent:*:*")
        except Exception as exc:  # noqa: BLE001
            _log(f"valkey unavailable ({exc!r}); using file fallback")
            self._use_valkey = False

    def _rate_ok(self) -> bool:
        now = time.time()
        if now - self._last_rate_reset >= 1.0:
            self._last_rate_reset = now
            self._rate_window_count = 0
        if self._rate_window_count >= MAX_EVENTS_PER_SEC:
            return False
        self._rate_window_count += 1
        return True

    def _republish(self, payload: Dict[str, Any]) -> None:
        if not self._rate_ok():
            _log("rate-limit: dropped event")
            return
        self._published += 1
        if self._use_valkey and self._client is not None:
            try:
                self._client.publish(CANONICAL_CHANNEL,
                                     json.dumps(payload, default=str))
                return
            except Exception as exc:  # noqa: BLE001
                _log(f"republish failed: {exc!r}")
                self._use_valkey = False
        # Persistent fallback — append to canonical-live.jsonl so consumers
        # that cannot speak pub/sub still see events.
        target = _metrics_dir() / "canonical-live.jsonl"
        try:
            with open(target, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(payload, default=str) + "\n")
        except OSError:
            pass

    # ---- loops ------------------------------------------------------

    def _valkey_loop(self) -> None:
        assert self._pubsub is not None
        while not self._stop.is_set():
            try:
                msg = self._pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if not msg:
                    continue
                if msg.get("type") not in ("message", "pmessage"):
                    continue
                raw = msg.get("data", "")
                if not isinstance(raw, str):
                    continue
                try:
                    data = json.loads(raw)
                except (json.JSONDecodeError, ValueError):
                    continue
                self._republish(data)
            except Exception as exc:  # noqa: BLE001
                _log(f"valkey loop error: {exc!r}")
                time.sleep(1)

    def _fallback_loop(self) -> None:
        """Tail FallbackBus JSONL files when Valkey is unavailable."""
        bus_dir = _project_dir() / ".cognitive-os" / "agent-bus"
        offsets: Dict[str, int] = {}
        while not self._stop.is_set():
            if not bus_dir.exists():
                time.sleep(FALLBACK_POLL_INTERVAL)
                continue
            for agent_dir in bus_dir.iterdir():
                if not agent_dir.is_dir():
                    continue
                for f in agent_dir.glob("*.jsonl"):
                    key = str(f)
                    try:
                        size = f.stat().st_size
                    except OSError:
                        continue
                    prev = offsets.get(key, 0)
                    if size < prev:
                        prev = 0
                    if size == prev:
                        continue
                    try:
                        with open(f, "r", encoding="utf-8", errors="replace") as fh:
                            fh.seek(prev)
                            for line in fh:
                                line = line.strip()
                                if not line:
                                    continue
                                try:
                                    data = json.loads(line)
                                except (json.JSONDecodeError, ValueError):
                                    continue
                                self._republish(data)
                            offsets[key] = fh.tell()
                    except OSError:
                        continue
            time.sleep(FALLBACK_POLL_INTERVAL)

    # ---- lifecycle --------------------------------------------------

    def run(self) -> None:
        _write_mode()
        _log(f"starting cos-executor (pid={os.getpid()})")
        self._connect()

        if self._use_valkey:
            t = threading.Thread(target=self._valkey_loop,
                                 daemon=True, name="executor-valkey")
        else:
            t = threading.Thread(target=self._fallback_loop,
                                 daemon=True, name="executor-fallback")
        t.start()

        try:
            while not self._stop.is_set():
                time.sleep(0.5)
        finally:
            _log(f"stopping; {self._published} events republished")
            if self._pubsub is not None:
                try:
                    self._pubsub.punsubscribe()
                    self._pubsub.close()
                except Exception:  # noqa: BLE001
                    pass
            _clear_mode()

    def stop(self) -> None:
        self._stop.set()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _cmd_status() -> int:
    pid = _existing_pid()
    if pid:
        print(f"ALIVE pid={pid}")
        return 0
    print("DEAD")
    return 1


def _cmd_stop() -> int:
    pid = _existing_pid()
    if not pid:
        print("not running")
        return 0
    try:
        os.kill(pid, signal.SIGTERM)
        print(f"sent SIGTERM to {pid}")
        return 0
    except OSError as exc:
        print(f"kill failed: {exc}", file=sys.stderr)
        return 2


def _cmd_daemon() -> int:
    if _existing_pid():
        return 0  # idempotent — already running
    try:
        pid = os.fork()
    except OSError as exc:
        print(f"fork failed: {exc}", file=sys.stderr)
        return 3
    if pid > 0:
        # Parent returns immediately; the PID we print is the child pid.
        print(f"started pid={pid}")
        return 0
    # Child: detach and run.
    os.setsid()
    _claim_pid()
    _install_signal_handlers()
    try:
        CosExecutor().run()
    finally:
        _release_pid()
    os._exit(0)  # noqa: SLF001 — child must not run atexit again


def _cmd_foreground() -> int:
    if _existing_pid():
        print("already running", file=sys.stderr)
        return 1
    _claim_pid()
    _install_signal_handlers()
    try:
        CosExecutor().run()
    finally:
        _release_pid()
    return 0


_EXECUTOR: Optional[CosExecutor] = None


def _install_signal_handlers() -> None:
    def _graceful(_sig, _frm):
        if _EXECUTOR is not None:
            _EXECUTOR.stop()
        _release_pid()
        _clear_mode()

    signal.signal(signal.SIGTERM, _graceful)
    signal.signal(signal.SIGINT, _graceful)


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(prog="cos-executor")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--daemon", action="store_true",
                       help="start daemon (idempotent)")
    group.add_argument("--status", action="store_true",
                       help="print ALIVE/DEAD")
    group.add_argument("--stop", action="store_true",
                       help="SIGTERM the running daemon")
    group.add_argument("--foreground", action="store_true",
                       help="run in the current process (tests)")
    args = parser.parse_args(argv)

    if args.status:
        return _cmd_status()
    if args.stop:
        return _cmd_stop()
    if args.daemon:
        return _cmd_daemon()
    if args.foreground:
        return _cmd_foreground()
    return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

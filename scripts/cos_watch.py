#!/usr/bin/env python3
# SCOPE: os-only
"""cos-watch — live agent TUI (ADR-034).

Subscribes to the canonical live channel (``cos:canonical:live``) or,
when Valkey is unavailable, tails
``.cognitive-os/metrics/canonical-live.jsonl`` /
``.cognitive-os/agent-bus/<id>/*.jsonl``.

Shows for the target agent(s):

    agent_id   elapsed   model   tokens(in/out/cache)   tools   last PROGRESS markers (5)   last action

Rendering backend:
- If ``rich`` is installed: :class:`rich.live.Live` auto-refreshing panel.
- Otherwise: plain text repainted with ``\\r`` / ANSI clear.

CLI:
    cos_watch.py --agent-id AGENT_ID
    cos-watch.py --latest          # most recently-seen agent
    cos-watch.py --once            # render a single snapshot then exit
    cos-watch.py --feed FILE       # read events from a JSONL file (tests)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Deque, Dict, Iterable, List, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.project_paths import project_dir_from_env as _project_dir


CANONICAL_CHANNEL = "cos:canonical:live"
REFRESH_HZ = 2.0


@dataclass
class AgentView:
    agent_id: str
    started_at: float = 0.0
    model: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    cache_tokens: int = 0
    tool_count: int = 0
    last_tool: Optional[str] = None
    last_message: Optional[str] = None
    status: str = "running"
    progress: Deque[str] = field(default_factory=lambda: deque(maxlen=5))

    def ingest(self, event: Dict[str, Any]) -> None:
        etype = event.get("event_type") or event.get("type") or ""
        if etype in ("agent_start",):
            self.started_at = float(event.get("started_at") or time.time())
            self.model = event.get("model") or self.model
        elif etype in ("agent_end",):
            self.status = event.get("exit_status", "ended")
            tu = event.get("token_usage") or {}
            self.input_tokens = tu.get("input", self.input_tokens)
            self.output_tokens = tu.get("output", self.output_tokens)
            self.cache_tokens = tu.get("cached", self.cache_tokens)
        elif etype in ("tool_use_start",):
            self.last_tool = event.get("tool_name")
            self.tool_count += 1
        elif etype in ("tool_use_end",):
            status = event.get("exit_status", "success")
            if status != "success":
                self.last_message = f"{event.get('tool_name')} → {status}"
        elif etype in ("tool_use",):  # post-hoc aggregate
            self.tool_count += 1
            self.last_tool = event.get("tool_name")
        elif etype in ("progress_marker",):
            cur = event.get("step_current", 0)
            tot = event.get("step_total", 0)
            msg = event.get("message", "")
            self.progress.append(f"[{cur}/{tot}] {msg}"[:80])
            self.last_message = msg or self.last_message
        elif etype in ("heartbeat_tick", "heartbeat"):
            if event.get("alive") is False:
                self.status = "dead"
            step = event.get("step")
            if step:
                self.last_message = step
        elif etype in ("token_usage",):
            self.input_tokens = event.get("input_tokens", self.input_tokens)
            self.output_tokens = event.get("output_tokens", self.output_tokens)
            cr = event.get("cache_read")
            if cr is not None:
                self.cache_tokens = cr
        elif etype in ("progress",):  # agent_bus progress event
            tool = event.get("tool")
            if tool:
                self.tool_count += 1
                self.last_tool = tool
            action = event.get("action")
            if action:
                self.last_message = action

    def elapsed_s(self) -> float:
        if not self.started_at:
            return 0.0
        return max(0.0, time.time() - self.started_at)


# ---------------------------------------------------------------------------
# Event sources
# ---------------------------------------------------------------------------


def _iter_valkey(stop: Optional[callable] = None) -> Iterable[Dict[str, Any]]:
    try:
        import redis  # type: ignore
    except ImportError:
        return
    url = os.environ.get(
        "VALKEY_URL",
        os.environ.get("COS_VALKEY_URL", "redis://localhost:6379"),
    )
    try:
        client = redis.Redis.from_url(url, socket_connect_timeout=2,
                                      decode_responses=True)
        client.ping()
        pubsub = client.pubsub()
        pubsub.subscribe(CANONICAL_CHANNEL)
    except Exception:
        return
    while True:
        if stop is not None and stop():
            return
        msg = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
        if not msg:
            continue
        raw = msg.get("data", "")
        if not isinstance(raw, str):
            continue
        try:
            yield json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            continue


def _iter_file(path: Path, follow: bool = True,
               stop: Optional[callable] = None) -> Iterable[Dict[str, Any]]:
    if not path.exists() and not follow:
        return
    offset = 0
    while True:
        if stop is not None and stop():
            return
        if path.exists():
            size = path.stat().st_size
            if size < offset:
                offset = 0
            if size > offset:
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    fh.seek(offset)
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            yield json.loads(line)
                        except (json.JSONDecodeError, ValueError):
                            continue
                    offset = fh.tell()
        if not follow:
            return
        time.sleep(0.3)


def _fallback_bus_files() -> List[Path]:
    base = _project_dir() / ".cognitive-os" / "agent-bus"
    if not base.exists():
        return []
    out: List[Path] = []
    for agent_dir in base.iterdir():
        if agent_dir.is_dir():
            out.extend(agent_dir.glob("*.jsonl"))
    return out


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _format_panel(view: AgentView) -> str:
    el = view.elapsed_s()
    m, s = divmod(int(el), 60)
    tokens = f"in={view.input_tokens} out={view.output_tokens} cache={view.cache_tokens}"
    prog = "\n  ".join(list(view.progress)) or "(no PROGRESS markers yet)"
    return (
        f"agent_id : {view.agent_id}\n"
        f"status   : {view.status}\n"
        f"elapsed  : {m:02d}m{s:02d}s\n"
        f"model    : {view.model or '-'}\n"
        f"tokens   : {tokens}\n"
        f"tools    : {view.tool_count}  last={view.last_tool or '-'}\n"
        f"last     : {view.last_message or '-'}\n"
        f"progress :\n  {prog}\n"
    )


def _render_rich(view: AgentView) -> None:
    try:
        from rich.panel import Panel
        from rich.text import Text
    except ImportError:
        _render_plain(view)
        return
    # Single render (the caller handles the loop)
    text = Text(_format_panel(view))
    print(Panel(text, title="cos-watch", subtitle=view.agent_id))


def _render_plain(view: AgentView) -> None:
    # ANSI clear + home (safe on non-TTY: writes a few control chars).
    sys.stdout.write("\x1b[2J\x1b[H")
    sys.stdout.write(_format_panel(view))
    sys.stdout.write("\n")
    sys.stdout.flush()


def render(view: AgentView, use_rich: bool = True) -> str:
    """Return the rendered string. Also writes to stdout when use_rich=False.

    Exposed for tests so we can snapshot the rendered panel without a TTY.
    """
    s = _format_panel(view)
    if use_rich:
        try:
            from rich.panel import Panel  # noqa: F401
            _render_rich(view)
            return s
        except ImportError:
            pass
    _render_plain(view)
    return s


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _pick_latest_agent(views: Dict[str, AgentView]) -> Optional[str]:
    if not views:
        return None
    # Most recent started_at, breaking ties by insertion order.
    return max(views.keys(), key=lambda a: views[a].started_at or 0.0)


def run(agent_id: Optional[str],
        latest: bool,
        once: bool,
        feed: Optional[Path]) -> int:
    views: Dict[str, AgentView] = {}

    if feed is not None:
        events: Iterable[Dict[str, Any]] = _iter_file(feed, follow=False)
    else:
        # Prefer Valkey; fall back to canonical-live.jsonl; then FallbackBus.
        canon_file = _project_dir() / ".cognitive-os" / "metrics" / "canonical-live.jsonl"
        valkey_iter = iter(_iter_valkey())
        has_valkey_event = False
        try:
            first = next(valkey_iter)
            has_valkey_event = True
        except StopIteration:
            first = None

        if has_valkey_event:
            def _with_first() -> Iterable[Dict[str, Any]]:
                yield first  # type: ignore[misc]
                for ev in valkey_iter:
                    yield ev
            events = _with_first()
        elif canon_file.exists():
            events = _iter_file(canon_file, follow=not once)
        else:
            # Fallback: read all agent-bus files in sequence.
            files = _fallback_bus_files()
            def _iter_all() -> Iterable[Dict[str, Any]]:
                for p in files:
                    for ev in _iter_file(p, follow=False):
                        yield ev
            events = _iter_all()

    rendered_any = False
    for ev in events:
        aid = (ev.get("agent_id") or ev.get("id") or "unknown")
        v = views.setdefault(aid, AgentView(agent_id=aid))
        v.ingest(ev)

        target = agent_id
        if latest and target is None:
            target = _pick_latest_agent(views)
        if target is None and agent_id is None and not latest:
            # No filter — render whichever agent just updated.
            target = aid

        if target and target in views:
            render(views[target], use_rich=_has_rich())
            rendered_any = True
            if once:
                return 0

    # If --once with no events consumed, still draw an empty frame for UX.
    if once and not rendered_any:
        render(AgentView(agent_id=agent_id or "unknown"),
               use_rich=_has_rich())
    return 0


def _has_rich() -> bool:
    try:
        import rich  # type: ignore  # noqa: F401
        return True
    except ImportError:
        return False


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(prog="cos-watch")
    parser.add_argument("--agent-id", dest="agent_id", default=None)
    parser.add_argument("--latest", action="store_true",
                        help="watch the most recently seen agent")
    parser.add_argument("--once", action="store_true",
                        help="render a single snapshot and exit")
    parser.add_argument("--feed", type=Path, default=None,
                        help="read events from a JSONL file (tests)")
    args = parser.parse_args(argv)

    if not args.agent_id and not args.latest and not args.feed:
        args.latest = True
    return run(args.agent_id, args.latest, args.once, args.feed)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

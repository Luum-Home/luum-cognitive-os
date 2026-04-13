# scope: both
"""Cognitive OS Agent Dashboard -- Terminal-based real-time agent monitor.

Subscribes to all agent bus events and displays active agents, their phases,
last heartbeat times, and pending questions.

Usage:
    python lib/agent_dashboard.py
    python lib/agent_dashboard.py --url redis://localhost:6379
    python lib/agent_dashboard.py --refresh 2

Python 3.9+ compatible.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _format_ago(epoch: float) -> str:
    """Format a timestamp as 'Xs ago' or 'Xm ago'."""
    diff = time.time() - epoch
    if diff < 0:
        return "just now"
    if diff < 60:
        return "%ds ago" % int(diff)
    if diff < 3600:
        return "%dm ago" % int(diff / 60)
    return "%dh ago" % int(diff / 3600)


def _status_icon(alive: bool, last_epoch: float) -> str:
    """Return a status indicator based on alive flag and recency."""
    if not alive:
        return "[DEAD]"
    age = time.time() - last_epoch
    if age < 10:
        return "[ OK ]"
    if age < 15:
        return "[SLOW]"
    return "[LOST]"


def _clear_screen() -> None:
    """Clear the terminal screen."""
    os.system("cls" if os.name == "nt" else "clear")


class AgentDashboard:
    """Terminal dashboard showing real-time agent status.

    Args:
        valkey_url: Redis-compatible connection URL.
        refresh_interval: Seconds between display refreshes.
    """

    def __init__(
        self,
        valkey_url: str = "redis://localhost:6379",
        refresh_interval: float = 1.0,
    ) -> None:
        self.valkey_url = valkey_url
        self.refresh_interval = refresh_interval
        self._agents: Dict[str, Dict[str, Any]] = {}
        self._questions: Dict[str, List[Dict[str, Any]]] = {}
        self._recent_progress: Dict[str, Dict[str, Any]] = {}
        self._errors: Dict[str, str] = {}
        self._subscriber: Any = None

    def _on_heartbeat(self, data: Dict[str, Any]) -> None:
        """Handle heartbeat events."""
        agent_id = data.get("agent_id", "unknown")
        self._agents[agent_id] = data

    def _on_progress(self, data: Dict[str, Any]) -> None:
        """Handle progress events."""
        agent_id = data.get("agent_id", "unknown")
        msg_type = data.get("type", "")

        if msg_type == "complete":
            self._agents.setdefault(agent_id, {})
            self._agents[agent_id]["step"] = "COMPLETE"
            self._agents[agent_id]["alive"] = False
        elif msg_type == "error":
            self._errors[agent_id] = data.get("error", "unknown error")
        else:
            self._recent_progress[agent_id] = data

    def _on_question(self, data: Dict[str, Any]) -> None:
        """Handle question events."""
        agent_id = data.get("agent_id", "unknown")
        self._questions.setdefault(agent_id, []).append(data)

    def _render(self) -> None:
        """Render the dashboard to the terminal."""
        _clear_screen()

        now = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
        print("=" * 72)
        print("  Cognitive OS Agent Dashboard    %s" % now)
        print("=" * 72)
        print()

        if not self._agents:
            print("  No agents detected. Waiting for heartbeats...")
            print()
            print("  Make sure agents are running with agent_id parameter")
            print("  and AGENT_BUS_ENABLED=true is set.")
            return

        # Header
        print(
            "  %-8s %-20s %-12s %-15s %s"
            % ("STATUS", "AGENT", "PHASE", "LAST SEEN", "STEP")
        )
        print("  " + "-" * 68)

        # Sort: alive first, then by agent_id
        sorted_agents = sorted(
            self._agents.items(),
            key=lambda x: (not x[1].get("alive", False), x[0]),
        )

        for agent_id, info in sorted_agents:
            alive = info.get("alive", False)
            last_epoch = info.get("timestamp_epoch", 0)
            phase = info.get("phase", "?")
            step = info.get("step", "?")
            status = _status_icon(alive, last_epoch)
            ago = _format_ago(last_epoch) if last_epoch else "never"

            # Truncate for display
            agent_display = agent_id[:20]
            phase_display = phase[:12]
            step_display = step[:30]

            print(
                "  %-8s %-20s %-12s %-15s %s"
                % (status, agent_display, phase_display, ago, step_display)
            )

        # Recent progress
        if self._recent_progress:
            print()
            print("  RECENT ACTIVITY:")
            print("  " + "-" * 68)
            for agent_id, prog in list(self._recent_progress.items())[-5:]:
                tool = prog.get("tool", "?")
                action = prog.get("action", "")[:40]
                step_n = prog.get("step_current", 0)
                step_t = prog.get("step_total", 0)
                step_str = ""
                if step_t > 0:
                    step_str = " [%d/%d]" % (step_n, step_t)
                print("  %-20s %s %s%s" % (agent_id[:20], tool, action, step_str))

        # Pending questions
        pending = {
            aid: qs for aid, qs in self._questions.items() if qs
        }
        if pending:
            print()
            print("  PENDING QUESTIONS:")
            print("  " + "-" * 68)
            for agent_id, questions_list in pending.items():
                latest = questions_list[-1]
                qs = latest.get("questions", [])
                print("  %s (round %d):" % (agent_id, latest.get("round", 1)))
                for q in qs[:3]:
                    print("    - %s" % q[:60])
                if len(qs) > 3:
                    print("    ... and %d more" % (len(qs) - 3))

        # Errors
        if self._errors:
            print()
            print("  ERRORS:")
            print("  " + "-" * 68)
            for agent_id, err in list(self._errors.items())[-3:]:
                print("  %-20s %s" % (agent_id[:20], err[:50]))

        print()
        print("  Press Ctrl+C to exit")

    def run(self) -> None:
        """Run the dashboard in a loop."""
        from lib.agent_bus import OrchestratorSubscriber, is_valkey_available

        if not is_valkey_available(self.valkey_url):
            print("ERROR: Valkey is not available at %s" % self.valkey_url)
            print("Start Valkey/Redis and try again.")
            sys.exit(1)

        self._subscriber = OrchestratorSubscriber(valkey_url=self.valkey_url)
        self._subscriber.on_heartbeat(self._on_heartbeat)
        self._subscriber.on_progress(self._on_progress)
        self._subscriber.on_question(self._on_question)
        self._subscriber.subscribe_all()

        print("Connecting to Valkey at %s..." % self.valkey_url)
        print("Waiting for agent events. Press Ctrl+C to exit.")

        try:
            while True:
                self._render()
                time.sleep(self.refresh_interval)
        except KeyboardInterrupt:
            print("\nShutting down dashboard...")
        finally:
            if self._subscriber:
                self._subscriber.stop()


def main() -> None:
    """Entry point for the dashboard CLI."""
    parser = argparse.ArgumentParser(
        description="Cognitive OS Agent Dashboard -- real-time agent monitor"
    )
    parser.add_argument(
        "--url",
        default="redis://localhost:6379",
        help="Valkey/Redis URL (default: redis://localhost:6379)",
    )
    parser.add_argument(
        "--refresh",
        type=float,
        default=1.0,
        help="Refresh interval in seconds (default: 1.0)",
    )
    args = parser.parse_args()

    dashboard = AgentDashboard(valkey_url=args.url, refresh_interval=args.refresh)
    dashboard.run()


if __name__ == "__main__":
    main()

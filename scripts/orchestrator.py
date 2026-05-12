#!/usr/bin/env python3
# SCOPE: both
"""Cognitive OS Orchestrator — dogfood entry point.

Launches sub-Claude agents via `lib.claude_executor.ClaudeExecutor`, which
publishes heartbeats on the agent_bus and is monitored by
`lib.agent_bus_metrics.AgentBusMetrics`. Every launch from this script:

  - registers on agent_bus (heartbeats visible to so-vitals, so-agent-status)
  - emits agent_launched / agent_completed MetricEvents to
    .cognitive-os/metrics/agent-heartbeat.jsonl
  - runs under ORCHESTRATOR_MODE=executor (auto-activated via AutoExecutor)
  - degrades to FallbackBus files when Valkey is not reachable

Usage:
    python3 scripts/orchestrator.py --task "Write a one-line summary of docs/02-Decisions/adrs/ADR-028.md"
    echo "Write a greeting." | python3 scripts/orchestrator.py
    python3 scripts/orchestrator.py --task "..." --model sonnet --timeout 120
    python3 scripts/orchestrator.py --list-live   # show agents currently running
    python3 scripts/orchestrator.py --scan-stale  # show hung agents

Exit codes:
    0  task succeeded
    1  task failed or timed out
    2  misconfigured (bad args, executor unavailable)
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import uuid
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))


# --- Helpers ----------------------------------------------------------------

# Patterns matched against ClaudeExecutor error output to decide whether
# to trigger the ADR-049 direct-SDK fallback (Alibaba Qwen). Case-insensitive.
# Mirror of the list in hooks/rate-limit-detector.sh — keep in sync.
_RATE_LIMIT_PATTERNS = (
    "out of extra usage",
    "rate limit exceeded",
    "approximate usage limit",
    "approximately usage limit",
    "approaching your usage limit",
    "you're out of",
    "usage limit reached",
)


def _is_rate_limit_error(error: str) -> bool:
    """True if error text matches any known Claude subscription rate-limit wording."""
    if not error:
        return False
    low = error.lower()
    return any(p in low for p in _RATE_LIMIT_PATTERNS)


def _short_id() -> str:
    """Short, unique agent id — first 8 hex chars of a uuid4."""
    return uuid.uuid4().hex[:8]


def _fallback_disabled(verbose: bool = False) -> bool:
    """True if any kill-switch env var blocks fallback."""
    if os.environ.get("COS_DISABLE_LLM_FALLBACK", "").strip() == "1":
        if verbose:
            print("[orchestrator] COS_DISABLE_LLM_FALLBACK=1 — no fallback", file=sys.stderr)
        return True
    return False


def _try_qwen_primary(prompt: str, claude_model: str | None = None, verbose: bool = False):
    """Dispatch a prompt via lib/qwen_provider.py direct-SDK as PRIMARY path
    for sub-agents (ADR-049 corrected architecture).

    Sub-agents invoked via scripts/orchestrator.py go to Qwen by default to
    preserve Claude Max subscription quota for the primary user↔Claude Code
    chat (which cannot be redirected).

    Honors skill frontmatter model suggestions: if `claude_model` is passed
    (e.g. "opus"/"sonnet"/"haiku" from the skill's declared model), maps it
    to the best Qwen bundle equivalent.

    Returns a ClaudeExecutor-compatible result object (has `.success`, `.text`,
    `.input_tokens`, `.output_tokens`, `.cost_usd`, `.error`) on success, or
    None if Qwen is unavailable. In the None case, caller should try Claude
    as fallback (or surface the original error).

    Returns None (Qwen skipped) if any of the following is true:
      * COS_DISABLE_QWEN=1 in env (per-provider kill-switch)
      * lib.qwen_provider import fails (module missing)
      * qwen_provider.is_configured() returns False (API key unset)
    """
    if os.environ.get("COS_DISABLE_QWEN", "").strip() == "1":
        if verbose:
            print("[orchestrator] COS_DISABLE_QWEN=1 — Qwen primary disabled", file=sys.stderr)
        return None
    # (Kill-switches checked at top of function; see _fallback_disabled for
    # COS_DISABLE_LLM_FALLBACK handling. COS_FORCE_CLAUDE_PRIMARY and
    # COS_DISABLE_QWEN handled in cmd_run and at top of this function.)

    try:
        from lib.qwen_provider import call as qwen_call, is_configured, select_model
    except ImportError as e:
        if verbose:
            print(f"[orchestrator] qwen_provider import failed: {e}", file=sys.stderr)
        return None

    if not is_configured():
        if verbose:
            print(
                "[orchestrator] qwen_provider unconfigured (ALIBABA_QWEN_API_KEY unset) — "
                "returning original Claude error",
                file=sys.stderr,
            )
        return None

    # Honor the skill's declared Claude tier (opus/sonnet/haiku) when choosing
    # the Qwen bundle model, so a skill designed for Opus maps to qwen3.6-plus
    # rather than always landing on the default.
    chosen_model = select_model(claude_model_hint=claude_model)

    if verbose:
        print(
            f"[orchestrator] Claude rate-limit detected → falling back to qwen_provider "
            f"(ADR-049, claude_hint={claude_model!r} → qwen_model={chosen_model!r})",
            file=sys.stderr,
        )

    messages = [{"role": "user", "content": prompt}]
    result = qwen_call(messages, model=chosen_model)

    # Adapt QwenResult → ClaudeExecutor-like namespace so cmd_run's reporting
    # logic stays provider-agnostic.
    class _FallbackResult:
        def __init__(self, r):
            self.success = r.success
            self.text = r.text
            self.input_tokens = r.tokens_in
            self.output_tokens = r.tokens_out
            self.cost_usd = r.cost_usd
            self.error = r.error
            self.provider = "alibaba_qwen"

    return _FallbackResult(result)


def _activate_executor_mode() -> dict:
    """Attempt to activate executor mode; return mode descriptor."""
    try:
        from lib.orchestrator_mode_activator import AutoExecutor

        return AutoExecutor.check_and_activate()
    except Exception as e:
        return {"mode": "degraded", "error": str(e), "valkey_available": False}


def _read_prompt_from_args_or_stdin(args: argparse.Namespace) -> str:
    if args.task:
        return args.task.strip()
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    return ""


# --- Subcommands ------------------------------------------------------------


def cmd_list_live(args: argparse.Namespace) -> int:
    from lib.agent_bus_metrics import AgentBusMetrics

    abm = AgentBusMetrics()
    live = abm.list_live(max_age_seconds=args.max_age)
    if not live:
        print("No live agents.")
        return 0
    print(f"{'AGENT ID':<24} {'PHASE':<16} {'AGE(s)':>8}")
    for rec in live:
        print(f"{rec['agent_id']:<24} {(rec.get('last_phase') or '-'):<16} {int(rec['age_seconds']):>8}")
    return 0


def cmd_scan_stale(args: argparse.Namespace) -> int:
    from lib.agent_bus_metrics import AgentBusMetrics

    abm = AgentBusMetrics()
    stale = abm.scan_stale(max_age_seconds=args.max_age)
    if not stale:
        print("No stale agents.")
        return 0
    print(f"{'AGENT ID':<24} {'PHASE':<16} {'AGE(s)':>8}  STATE")
    for rec in stale:
        print(f"{rec['agent_id']:<24} {(rec.get('last_phase') or '-'):<16} {int(rec['age_seconds']):>8}  STALE")
    return 0


def cmd_kill_hung(args: argparse.Namespace) -> int:
    from lib.agent_bus_metrics import AgentBusMetrics

    abm = AgentBusMetrics()
    result = abm.mark_hung_and_publish(args.agent_id)
    print(f"marked hung: {result}")
    return 0


def _agent_bus_fallback_dir() -> Path:
    return (
        Path(
            os.environ.get("COGNITIVE_OS_PROJECT_DIR")
            or os.environ.get("CLAUDE_PROJECT_DIR")
            or os.getcwd()
        )
        / ".cognitive-os"
        / "agent-bus"
    )


def cmd_control(args: argparse.Namespace) -> int:
    from lib.agent_bus import OrchestratorSubscriber

    fallback_dir = _agent_bus_fallback_dir()
    sub = OrchestratorSubscriber(fallback_dir=str(fallback_dir))
    sent_via = sub.send_control(args.agent_id, args.command)
    print(f"control: {args.command} -> {args.agent_id} via {sent_via}")
    return 0


def cmd_answer(args: argparse.Namespace) -> int:
    from lib.agent_bus import OrchestratorSubscriber

    fallback_dir = _agent_bus_fallback_dir()
    sub = OrchestratorSubscriber(fallback_dir=str(fallback_dir))
    sent_via = sub.answer_question(args.agent_id, args.answer, round_num=args.round)
    print(f"answer: round {args.round} -> {args.agent_id} via {sent_via}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    prompt = _read_prompt_from_args_or_stdin(args)
    if not prompt:
        print("ERROR: no task provided. Pass --task or pipe via stdin.", file=sys.stderr)
        return 2

    # Activate executor mode (Valkey if available, fallback otherwise)
    mode = _activate_executor_mode()
    mode_label = mode.get("mode", "unknown")
    valkey = bool(mode.get("valkey_available"))
    if args.verbose:
        print(f"[orchestrator] executor mode={mode_label} valkey={valkey}", file=sys.stderr)

    # Build the agent id and wire up metrics bridge
    agent_id = args.agent_id or f"orch-{_short_id()}"
    os.environ.setdefault("COGNITIVE_OS_SESSION_ID", f"orchestrator-{agent_id}")

    try:
        from lib.agent_bus import OrchestratorSubscriber
        from lib.agent_bus_metrics import AgentBusMetrics
        from lib.claude_executor import ClaudeExecutor
    except ImportError as e:
        print(f"ERROR: executor/adapter import failed: {e}", file=sys.stderr)
        return 2

    # Subscribe the adapter so heartbeats from the sub-claude flow into
    # .cognitive-os/metrics/agent-heartbeat.jsonl as MetricEvents.
    abm = AgentBusMetrics()
    orchestrator_subscriber = None
    try:
        orchestrator_subscriber = OrchestratorSubscriber(fallback_dir=str(_agent_bus_fallback_dir()))
        orchestrator_subscriber.subscribe_agent(agent_id)
        if args.verbose:
            print(f"[orchestrator] control subscriber wired for agent_id={agent_id}", file=sys.stderr)
    except Exception as e:
        if args.verbose:
            print(f"[orchestrator] direct subscriber start failed: {e}", file=sys.stderr)

    if valkey:
        try:
            # subscribe() registers the heartbeat callback AND calls
            # subscribe_all() so the subscriber starts listening on
            # cos:agent:*:heartbeat. Listener thread spawns inside agent_bus.
            abm.subscribe()
        except Exception as e:
            if args.verbose:
                print(f"[orchestrator] metrics subscriber start failed: {e}", file=sys.stderr)

    # Launch the sub-claude. ClaudeExecutor's __init__ spawns an
    # AgentPublisher heartbeat thread when agent_id is provided.
    executor = ClaudeExecutor(
        agent_id=agent_id,
        default_model=args.model,
        default_timeout=args.timeout,
        verbose=args.verbose,
    )

    if args.verbose:
        print(f"[orchestrator] launching agent_id={agent_id} model={args.model or 'default'}", file=sys.stderr)

    # ADR-049 (corrected architecture — Option B): delegate cascade to
    # lib/dispatch.py. cmd_run becomes a thin wrapper that instantiates
    # ClaudeExecutor and forwards the task to the abstract dispatcher.
    # Benefits: uniform metrics logging, testable in isolation, reusable
    # from skills/hooks/future auto-router.
    from lib.dispatch import dispatch as _dispatch

    providers_raw = getattr(args, "providers", None) or "qwen,claude"
    providers_list = [p.strip() for p in providers_raw.split(",") if p.strip()]

    t0 = time.monotonic()
    dr = _dispatch(
        prompt=prompt,
        providers=providers_list,
        claude_executor=executor,
        claude_model=args.model,
        task_type="general",   # orchestrator CLI has no task-type hint yet
        skill_name=None,       # skills will set this when they call dispatch() directly
        timeout=args.timeout,
        verbose=args.verbose,
    )
    elapsed = time.monotonic() - t0

    # Adapt DispatchResult → old-shape object for downstream print logic below.
    result = type("_Adapt", (), {
        "success": dr.success,
        "text": dr.text,
        "input_tokens": dr.input_tokens,
        "output_tokens": dr.output_tokens,
        "cost_usd": dr.cost_usd,
        "error": dr.error,
    })()
    provider_used = dr.provider_used

    # Stop subscribers if we started them
    if orchestrator_subscriber and hasattr(orchestrator_subscriber, "stop"):
        try:
            orchestrator_subscriber.stop()
        except Exception:
            pass
    if abm._subscriber and hasattr(abm._subscriber, "stop"):
        try:
            abm._subscriber.stop()
        except Exception:
            pass

    # Report
    print(f"agent_id:    {agent_id}")
    print(f"provider:    {provider_used}")
    print(f"success:     {result.success}")
    print(f"elapsed:     {elapsed:.2f}s")
    print(f"input_tok:   {getattr(result, 'input_tokens', 0)}")
    print(f"output_tok:  {getattr(result, 'output_tokens', 0)}")
    print(f"cost_usd:    {getattr(result, 'cost_usd', 0.0):.4f}")
    if getattr(result, "error", None):
        print(f"error:       {result.error}", file=sys.stderr)
    if args.show_text:
        print("---")
        print(getattr(result, "text", "") or "")

    return 0 if result.success else 1


# --- CLI --------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="orchestrator",
        description="Cognitive OS dogfood orchestrator: launch agents via ClaudeExecutor, "
                    "observe through agent_bus_metrics.",
    )
    sub = p.add_subparsers(dest="cmd")

    r = sub.add_parser("run", help="Launch a sub-claude agent (default)")
    r.add_argument("--task", "-t", help="Prompt text (or pipe via stdin).")
    r.add_argument("--model", "-m", default=None, help="Model shortname (opus/sonnet/haiku).")
    r.add_argument("--timeout", type=int, default=600, help="Timeout in seconds.")
    r.add_argument("--agent-id", default=None, help="Override agent id.")
    r.add_argument("--show-text", action="store_true", help="Print the agent's text output.")
    r.add_argument(
        "--providers",
        default="qwen,openrouter,gemini,ollama,claude",
        help="Comma-separated priority-cascade list of providers (ADR-062). "
             "Default: 'qwen,openrouter,gemini,ollama,claude' — preserves Claude Max "
             "quota for the main user↔Claude Code chat; Claude is last-resort only. "
             "Primary = first, fallbacks = rest in order. "
             "Unconfigured providers (missing API keys / daemon not running) are skipped. "
             "Examples: 'qwen,claude' (legacy 2-tier), 'qwen' (solo Qwen), "
             "'qwen,openai,claude' (opt-in OpenAI tier). "
             "Opt-in providers (openai, deepseek, claude_sdk) require their API keys set. "
             "Override session-wide with COS_FORCE_CLAUDE_PRIMARY=1 (rewrites list to 'claude'). "
             "Ensemble (parallel multi-provider) is a separate future flag '--ensemble'.",
    )
    r.add_argument("--verbose", action="store_true")
    r.set_defaults(func=cmd_run)

    ll = sub.add_parser("list-live", help="List live agents (from agent_bus_metrics).")
    ll.add_argument("--max-age", type=int, default=300, help="Liveness threshold in seconds.")
    ll.set_defaults(func=cmd_list_live)

    ss = sub.add_parser("scan-stale", help="List stale agents.")
    ss.add_argument("--max-age", type=int, default=300, help="Staleness threshold in seconds.")
    ss.set_defaults(func=cmd_scan_stale)

    kh = sub.add_parser("kill-hung", help="Mark an agent as hung and publish stop signal.")
    kh.add_argument("agent_id")
    kh.set_defaults(func=cmd_kill_hung)

    ctl = sub.add_parser("control", help="Send a live/fallback control command to an agent.")
    ctl.add_argument("agent_id")
    ctl.add_argument("command", choices=["stop", "pause", "resume"])
    ctl.set_defaults(func=cmd_control)

    ans = sub.add_parser("answer", help="Send a clarification answer to an agent.")
    ans.add_argument("agent_id")
    ans.add_argument("answer", nargs="+", help="One or more answer strings.")
    ans.add_argument("--round", type=int, default=1, help="Clarification round number.")
    ans.set_defaults(func=cmd_answer)

    # Top-level shortcuts: if no subcommand, default to `run` with remaining args.
    args, remaining = p.parse_known_args(argv)
    if not args.cmd:
        # Parse as `run`
        ns = r.parse_args(remaining)
        return cmd_run(ns)

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

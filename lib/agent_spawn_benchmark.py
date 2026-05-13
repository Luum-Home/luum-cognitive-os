"""ADR-303 sub-agent spawn cold-start benchmark.

Measures the operator-side cost of "spawn a sub-agent" — what happens
*before* the sub-agent's first tool call:

  1. Wall-clock latency of the SubagentStart hook chain.
  2. Token payload (preamble + injected context) charged to every spawn.

No LLM call is made. All measurement is local hook execution.

The harness mirrors `scripts/startup-benchmark.sh` (ADR-028 D-stream) so
that the budget tests share their shape.

Record schema (one per run, appended to JSONL):

    {
      "timestamp": "2026-05-13T12:34:56Z",
      "project_dir": "...",
      "preamble": {bytes, est_tokens, path},
      "subagent_start_hooks": [{hook, duration_ms, exit_code, stdout_bytes}],
      "context_injector": {wall_ms, bytes_emitted, est_tokens, path},
      "mandatory_rules_inject": {bytes, est_tokens, path},
      "skill_catalog_inject": {bytes, est_tokens, path},
      "totals": {total_wall_ms, total_payload_tokens, total_payload_bytes},
      "slo": {wall_target_ms, payload_target_tokens, status}
    }
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ─── Defaults (overridable by env) ──────────────────────────────────────────

DEFAULT_WALL_BUDGET_MS = 3000
DEFAULT_PAYLOAD_TOKEN_BUDGET = 20000
PER_HOOK_TIMEOUT_SEC = 5

# ─── Helpers ────────────────────────────────────────────────────────────────


def bytes_to_tokens(n: int) -> int:
    """Rough estimator: 1 token ≈ 4 bytes."""
    return (int(n) + 2) // 4


def file_size(path: Path) -> int:
    try:
        return path.stat().st_size if path.is_file() else 0
    except OSError:
        return 0


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ─── Settings parsing ───────────────────────────────────────────────────────


def load_subagent_start_hooks(settings_path: Path) -> list[str]:
    """Return the list of command strings registered under SubagentStart."""
    if not settings_path.is_file():
        return []
    try:
        data = json.loads(settings_path.read_text())
    except (json.JSONDecodeError, OSError):
        return []

    hooks_block = data.get("hooks") if isinstance(data.get("hooks"), dict) else {}
    if not hooks_block:
        hooks_block = {
            event: groups
            for event, groups in data.items()
            if isinstance(groups, list)
        }

    commands: list[str] = []
    for group in hooks_block.get("SubagentStart", []) or []:
        for h in group.get("hooks", []) or []:
            cmd = h.get("command")
            if cmd:
                commands.append(cmd)
    return commands


# ─── Hook execution ─────────────────────────────────────────────────────────


def _short_hook_name(cmd: str) -> str:
    """Strip path noise and quoting to produce a stable short label."""
    # Pull the last hooks/* fragment from the command for a stable label
    m = re.search(r"hooks/([A-Za-z0-9._-]+)", cmd)
    if m:
        return m.group(1)
    tokens = shlex.split(cmd, posix=True)
    if tokens:
        return Path(tokens[-1]).name
    return cmd[:40]


def run_hook(cmd: str, project_dir: Path, timeout_sec: int = PER_HOOK_TIMEOUT_SEC) -> dict[str, Any]:
    """Run one hook command with a synthetic JSON payload on stdin.

    Returns {hook, duration_ms, exit_code, stdout_bytes, stdout_est_tokens}.
    """
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    env["CODEX_PROJECT_DIR"] = str(project_dir)
    env["COGNITIVE_OS_PROJECT_DIR"] = str(project_dir)
    env["SESSION_ID"] = f"spawn-bench-{os.getpid()}"

    synthetic_stdin = json.dumps(
        {
            "prompt": "benchmark probe — measure subagent spawn cold start",
            "session_id": env["SESSION_ID"],
            "tool_name": "Agent",
        }
    ).encode("utf-8")

    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            ["bash", "-c", cmd],
            input=synthetic_stdin,
            capture_output=True,
            text=False,
            timeout=timeout_sec,
            cwd=str(project_dir),
            env=env,
            check=False,
        )
        duration_ms = int((time.monotonic() - t0) * 1000)
        stdout_bytes = len(proc.stdout or b"")
        exit_code = proc.returncode
    except subprocess.TimeoutExpired:
        duration_ms = timeout_sec * 1000
        stdout_bytes = 0
        exit_code = 124

    return {
        "hook": _short_hook_name(cmd),
        "command": cmd,
        "duration_ms": duration_ms,
        "exit_code": exit_code,
        "stdout_bytes": stdout_bytes,
        "stdout_est_tokens": bytes_to_tokens(stdout_bytes),
    }


# ─── Record assembly ────────────────────────────────────────────────────────


@dataclass
class SpawnBenchmarkRecord:
    timestamp: str
    project_dir: str
    preamble: dict[str, Any]
    subagent_start_hooks: list[dict[str, Any]]
    context_injector: dict[str, Any]
    mandatory_rules_inject: dict[str, Any]
    skill_catalog_inject: dict[str, Any]
    totals: dict[str, Any]
    slo: dict[str, Any]


def _measure_file_component(label: str, path: Path) -> dict[str, Any]:
    b = file_size(path)
    return {
        "label": label,
        "path": str(path),
        "bytes": b,
        "est_tokens": bytes_to_tokens(b),
        "exists": path.is_file(),
    }


def _find_context_injector_hook(hook_results: list[dict[str, Any]]) -> dict[str, Any] | None:
    for hr in hook_results:
        if "subagent-context-injector" in hr.get("hook", ""):
            return hr
    # Fallback: any hook whose command references subagent-context-injector
    for hr in hook_results:
        if "subagent-context-injector" in hr.get("command", ""):
            return hr
    return None


def build_record(project_dir: Path, settings_path: Path) -> SpawnBenchmarkRecord:
    # 1. Preamble
    preamble_path = project_dir / "templates" / "agent-preamble.md"
    preamble = _measure_file_component("agent-preamble", preamble_path)

    # 2. Hooks (live timing)
    commands = load_subagent_start_hooks(settings_path)
    hook_results = [run_hook(c, project_dir) for c in commands]

    total_wall_ms = sum(h["duration_ms"] for h in hook_results)
    total_stdout_bytes = sum(h["stdout_bytes"] for h in hook_results)

    # 3. Context injector breakdown
    ci = _find_context_injector_hook(hook_results)
    if ci is not None:
        context_injector = {
            "wall_ms": ci["duration_ms"],
            "bytes_emitted": ci["stdout_bytes"],
            "est_tokens": ci["stdout_est_tokens"],
            "path": str(project_dir / "hooks" / "subagent-context-injector.sh"),
            "exit_code": ci["exit_code"],
        }
    else:
        context_injector = {
            "wall_ms": 0,
            "bytes_emitted": 0,
            "est_tokens": 0,
            "path": str(project_dir / "hooks" / "subagent-context-injector.sh"),
            "exit_code": None,
        }

    # 4. Static injected components — preamble carries mandatory rules
    # (RULES-COMPACT.md is part of the agent-preamble template by reference).
    rules_compact = project_dir / "rules" / "RULES-COMPACT.md"
    mandatory_rules_inject = _measure_file_component("rules-compact", rules_compact)

    # 5. Skill catalog — what gets enumerated on every spawn
    catalog_compact = project_dir / "skills" / "CATALOG-COMPACT.md"
    skill_catalog_inject = _measure_file_component("skills-catalog-compact", catalog_compact)

    # 6. Totals — payload is the sum of what spawn-time hooks emit, plus the
    #    preamble that the injector concatenates. We sum stdout bytes from
    #    hooks (covers context_injector output) plus the preamble file size
    #    as a conservative upper bound when the injector wraps it inside JSON.
    total_payload_bytes = total_stdout_bytes + preamble["bytes"]
    total_payload_tokens = bytes_to_tokens(total_payload_bytes)

    # 7. SLO
    wall_target = int(os.environ.get("AGENT_SPAWN_BUDGET_MS", DEFAULT_WALL_BUDGET_MS))
    token_target = int(os.environ.get("AGENT_SPAWN_TOKEN_BUDGET", DEFAULT_PAYLOAD_TOKEN_BUDGET))
    wall_pass = total_wall_ms <= wall_target
    token_pass = total_payload_tokens <= token_target
    slo_status = "pass" if (wall_pass and token_pass) else "breach"

    totals = {
        "total_wall_ms": total_wall_ms,
        "total_payload_bytes": total_payload_bytes,
        "total_payload_tokens": total_payload_tokens,
        "hook_count": len(hook_results),
    }
    slo = {
        "wall_target_ms": wall_target,
        "wall_measured_ms": total_wall_ms,
        "wall_status": "pass" if wall_pass else "breach",
        "payload_target_tokens": token_target,
        "payload_measured_tokens": total_payload_tokens,
        "payload_status": "pass" if token_pass else "breach",
        "status": slo_status,
    }

    return SpawnBenchmarkRecord(
        timestamp=now_iso(),
        project_dir=str(project_dir),
        preamble=preamble,
        subagent_start_hooks=hook_results,
        context_injector=context_injector,
        mandatory_rules_inject=mandatory_rules_inject,
        skill_catalog_inject=skill_catalog_inject,
        totals=totals,
        slo=slo,
    )


# ─── Output helpers ─────────────────────────────────────────────────────────


def append_jsonl(record: SpawnBenchmarkRecord, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(asdict(record), separators=(",", ":"))
    with output_path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def render_markdown(record: SpawnBenchmarkRecord) -> str:
    r = asdict(record)
    lines: list[str] = []
    lines.append(f"# Sub-Agent Spawn Cold-Start Benchmark — {r['timestamp']}")
    lines.append("")
    lines.append(f"Project: `{r['project_dir']}`")
    lines.append("")

    lines.append("## 1. SubagentStart Hook Timing")
    lines.append("")
    lines.append("| # | Hook | Duration (ms) | Exit | Stdout bytes | Est. tokens |")
    lines.append("|---|------|---------------|------|--------------|-------------|")
    for i, h in enumerate(r["subagent_start_hooks"], 1):
        lines.append(
            f"| {i} | {h['hook']} | {h['duration_ms']} | {h['exit_code']} | "
            f"{h['stdout_bytes']} | {h['stdout_est_tokens']} |"
        )
    lines.append("")
    lines.append(f"**Total wall-clock:** {r['totals']['total_wall_ms']} ms")
    lines.append("")

    lines.append("## 2. Payload Components")
    lines.append("")
    lines.append("| Component | Path | Bytes | Est. tokens |")
    lines.append("|-----------|------|-------|-------------|")
    for comp_key in ("preamble", "mandatory_rules_inject", "skill_catalog_inject"):
        c = r[comp_key]
        lines.append(
            f"| {comp_key} | `{c['path']}` | {c['bytes']} | {c['est_tokens']} |"
        )
    ci = r["context_injector"]
    lines.append(
        f"| context_injector_stdout | `{ci['path']}` | {ci['bytes_emitted']} | {ci['est_tokens']} |"
    )
    lines.append("")
    lines.append(
        f"**Total payload:** {r['totals']['total_payload_bytes']} bytes "
        f"(~{r['totals']['total_payload_tokens']} tokens)"
    )
    lines.append("")

    lines.append("## 3. SLO Status")
    lines.append("")
    slo = r["slo"]
    lines.append("| Dimension | Target | Measured | Status |")
    lines.append("|-----------|--------|----------|--------|")
    lines.append(
        f"| Spawn wall-clock | < {slo['wall_target_ms']} ms | {slo['wall_measured_ms']} ms | {slo['wall_status'].upper()} |"
    )
    lines.append(
        f"| Payload tokens | < {slo['payload_target_tokens']} | {slo['payload_measured_tokens']} | {slo['payload_status'].upper()} |"
    )
    lines.append("")
    lines.append(f"**Overall:** {slo['status'].upper()}")
    lines.append("")
    return "\n".join(lines)


def default_output_path(project_dir: Path) -> Path:
    return project_dir / ".cognitive-os" / "metrics" / "agent-spawn-benchmark.jsonl"


def default_settings_path(project_dir: Path) -> Path:
    return project_dir / ".claude" / "settings.json"

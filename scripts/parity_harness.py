#!/usr/bin/env python3
# SCOPE: both
"""Parity harness — Claude Agent() vs Qwen agent loop (ADR-051 Phase 4).

Runs each task in a YAML task-set through BOTH providers and emits:
  - One JSONL record per (task, provider) pair to
    `.cognitive-os/metrics/parity-results.jsonl`
  - A CSV summary (stdout or --csv path)
  - A Markdown comparison report (stdout or --report path)

The harness is deliberately provider-agnostic: both branches produce the same
`ParityResult` shape (success, tokens, cost, latency, tool calls, files
modified, text) so downstream tooling (ADR-052 benchmark harness, ADR-053
auto-optimizer) can consume the same record regardless of the underlying
provider.

Usage:
    python3 scripts/parity_harness.py --tasks docs/benchmarks/parity-smoke.yaml
    python3 scripts/parity_harness.py --tasks ... --report docs/benchmarks/out.md
    python3 scripts/parity_harness.py --tasks ... --only-qwen    # debug mode
    python3 scripts/parity_harness.py --tasks ... --dry-run      # no providers

The tests in tests/unit/test_parity_harness.py exercise the pure-python layer
(YAML loading, CSV/MD rendering, run_task with injected providers). No real
API call is ever made in the test suite.

Reference: docs/adrs/ADR-051-qwen-agent-loop.md §"Phase 4"
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# --- Data classes -----------------------------------------------------------


@dataclass
class ParityTask:
    """One entry in the task-set YAML."""

    id: str
    description: str
    prompt: str
    tools_allowed: Optional[List[str]] = None
    success_cmd: Optional[str] = None
    watch_paths: List[str] = field(default_factory=list)


@dataclass
class ParityResult:
    """Per-(task, provider) outcome. Serialized to JSONL."""

    task_id: str
    provider: str                   # "claude" | "qwen"
    model: str = ""
    success: bool = False
    text: str = ""                  # final assistant text (trimmed for logs)
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    tool_calls: int = 0
    files_modified: List[str] = field(default_factory=list)
    success_cmd_exit: Optional[int] = None   # None = not run
    error: str = ""
    text_hash: str = ""             # md5 of final text — cheap diff signal

    def to_record(self) -> Dict[str, Any]:
        d = asdict(self)
        # Keep text preview bounded in JSONL (full text is not essential here)
        if len(self.text) > 500:
            d["text"] = self.text[:500] + f"...[+{len(self.text)-500}ch]"
        return d


# --- Task-set loading -------------------------------------------------------


def load_tasks(path: Path) -> List[ParityTask]:
    """Parse a YAML task-set file. Accepts either PyYAML or a minimal stdlib
    fallback (sufficient for the smoke file's simple shape).
    """
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(text)
    except ImportError:
        data = _minimal_yaml_parse(text)

    if not isinstance(data, dict) or "tasks" not in data:
        raise ValueError(f"task-set file must have a top-level 'tasks:' key: {path}")

    out: List[ParityTask] = []
    for raw in data["tasks"]:
        if not isinstance(raw, dict) or "id" not in raw or "prompt" not in raw:
            raise ValueError(f"task entry missing id/prompt: {raw!r}")
        out.append(
            ParityTask(
                id=str(raw["id"]),
                description=str(raw.get("description", "")),
                prompt=str(raw["prompt"]),
                tools_allowed=raw.get("tools_allowed"),
                success_cmd=raw.get("success_cmd"),
                watch_paths=list(raw.get("watch_paths", []) or []),
            )
        )
    return out


def _minimal_yaml_parse(text: str) -> Dict[str, Any]:
    """Last-resort YAML-ish parser for the smoke task-set shape. Supports:
      - `tasks:` top-level list of mappings
      - string scalars, inline [a, b] lists, block '|' literals
    Not a full YAML implementation — only exists so the harness runs on a
    stdlib-only env. Real use should have PyYAML installed.
    """
    import re
    lines = text.splitlines()
    tasks: List[Dict[str, Any]] = []
    cur: Dict[str, Any] = {}
    in_block = False
    block_key = ""
    block_buf: List[str] = []
    block_indent = 0

    def _flush_block():
        nonlocal in_block, block_key, block_buf
        if in_block:
            # Dedent to the least-indented non-empty line
            stripped = [ln[block_indent:] if len(ln) >= block_indent else ln
                        for ln in block_buf]
            cur[block_key] = "\n".join(stripped).rstrip("\n")
            in_block = False
            block_key = ""
            block_buf = []

    for raw in lines:
        line = raw.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"):
            if in_block:
                block_buf.append(line)
            continue
        stripped = line.lstrip(" ")
        indent = len(line) - len(stripped)

        if in_block:
            if indent >= block_indent or not stripped:
                block_buf.append(line)
                continue
            _flush_block()

        if stripped.startswith("- "):
            # New task entry
            if cur:
                tasks.append(cur)
            cur = {}
            stripped = stripped[2:]

        m = re.match(r"([A-Za-z_][\w-]*)\s*:\s*(.*)$", stripped)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()

        if val == "|":
            in_block = True
            block_key = key
            block_buf = []
            block_indent = indent + 2
            continue
        if val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            if not inner:
                cur[key] = []
            else:
                cur[key] = [p.strip().strip('"').strip("'") for p in inner.split(",")]
            continue
        if val == "":
            cur[key] = None
            continue
        # Scalar — strip surrounding quotes
        cur[key] = val.strip('"').strip("'")

    _flush_block()
    if cur:
        tasks.append(cur)

    # Top-level `tasks:` wrapping — the first synthetic "cur" is actually the
    # parent dict, so re-check: if the first task has only {"tasks": None} it's
    # the marker. Our simple loop doesn't emit that marker — we just collect
    # all dash-prefixed entries. Assume the file has `tasks:` header.
    return {"tasks": tasks}


# --- File-diff helpers ------------------------------------------------------


def _snapshot_files(paths: List[str], project_root: Path) -> Dict[str, str]:
    """Return {relpath: sha256} for each watched path. Missing files → "".
    Directories are expanded to files.
    """
    out: Dict[str, str] = {}
    for rel in paths:
        target = (project_root / rel).resolve()
        if not target.exists():
            out[rel] = ""
            continue
        if target.is_dir():
            for f in sorted(target.rglob("*")):
                if f.is_file():
                    out[str(f.relative_to(project_root))] = _hash_file(f)
        elif target.is_file():
            out[rel] = _hash_file(target)
    return out


def _hash_file(p: Path) -> str:
    try:
        h = hashlib.sha256()
        h.update(p.read_bytes())
        return h.hexdigest()
    except OSError:
        return ""


def _diff_snapshots(before: Dict[str, str], after: Dict[str, str]) -> List[str]:
    """Return list of files whose hash changed between the two snapshots."""
    changed: List[str] = []
    for k, v in after.items():
        if before.get(k, "") != v:
            changed.append(k)
    for k in before:
        if k not in after:
            changed.append(k)
    return sorted(set(changed))


# --- Provider wrappers ------------------------------------------------------


def run_via_qwen(
    task: ParityTask,
    project_root: Path,
    verbose: bool = False,
) -> ParityResult:
    """Dispatch the task through lib.qwen_agent_loop.run_agent."""
    try:
        from lib import qwen_agent_loop
    except ImportError as exc:
        return ParityResult(
            task_id=task.id, provider="qwen",
            error=f"qwen_agent_loop import failed: {exc}",
        )

    before = _snapshot_files(task.watch_paths, project_root)
    t0 = time.monotonic()
    try:
        res = qwen_agent_loop.run_agent(
            task=task.prompt,
            tools_allowed=task.tools_allowed,
            verbose=verbose,
        )
    except Exception as exc:  # noqa: BLE001
        return ParityResult(
            task_id=task.id, provider="qwen",
            latency_ms=int((time.monotonic() - t0) * 1000),
            error=f"{type(exc).__name__}: {exc}",
        )
    latency_ms = int((time.monotonic() - t0) * 1000)
    after = _snapshot_files(task.watch_paths, project_root)

    text = getattr(res, "text", "") or ""
    return ParityResult(
        task_id=task.id,
        provider="qwen",
        model=getattr(res, "model", "") or "",
        success=bool(getattr(res, "success", False)),
        text=text,
        tokens_in=int(getattr(res, "tokens_in", 0) or 0),
        tokens_out=int(getattr(res, "tokens_out", 0) or 0),
        cost_usd=float(getattr(res, "cost_usd", 0.0) or 0.0),
        latency_ms=latency_ms,
        tool_calls=int(getattr(res, "tool_calls_made", 0) or 0),
        files_modified=_diff_snapshots(before, after),
        success_cmd_exit=_run_success_cmd(task, project_root),
        error=getattr(res, "error", "") or "",
        text_hash=hashlib.md5(text.encode("utf-8")).hexdigest() if text else "",
    )


def run_via_claude(
    task: ParityTask,
    project_root: Path,
    claude_executor: Any,
    timeout: int = 300,
    verbose: bool = False,
) -> ParityResult:
    """Dispatch the task through ClaudeExecutor.run(...)."""
    before = _snapshot_files(task.watch_paths, project_root)
    t0 = time.monotonic()
    try:
        r = claude_executor.run(task.prompt, timeout=timeout)
    except Exception as exc:  # noqa: BLE001
        return ParityResult(
            task_id=task.id, provider="claude",
            latency_ms=int((time.monotonic() - t0) * 1000),
            error=f"{type(exc).__name__}: {exc}",
        )
    latency_ms = int((time.monotonic() - t0) * 1000)
    after = _snapshot_files(task.watch_paths, project_root)

    # ClaudeResult field names differ slightly from AgentLoopResult; normalize.
    text = getattr(r, "result_text", None) or getattr(r, "text", "") or ""
    tool_calls = getattr(r, "tool_calls", [])
    try:
        tool_calls_count = len(tool_calls) if tool_calls is not None else 0
    except TypeError:
        tool_calls_count = 0
    tokens_in = getattr(r, "tokens_in", 0) or getattr(r, "input_tokens", 0) or 0
    tokens_out = getattr(r, "tokens_out", 0) or getattr(r, "output_tokens", 0) or 0

    return ParityResult(
        task_id=task.id,
        provider="claude",
        model=getattr(r, "model_used", "") or "",
        success=bool(getattr(r, "success", False)),
        text=text,
        tokens_in=int(tokens_in),
        tokens_out=int(tokens_out),
        cost_usd=float(getattr(r, "cost_usd", 0.0) or 0.0),
        latency_ms=latency_ms,
        tool_calls=tool_calls_count,
        files_modified=_diff_snapshots(before, after),
        success_cmd_exit=_run_success_cmd(task, project_root),
        error=getattr(r, "error_message", "") or getattr(r, "error", "") or "",
        text_hash=hashlib.md5(text.encode("utf-8")).hexdigest() if text else "",
    )


def _run_success_cmd(task: ParityTask, project_root: Path) -> Optional[int]:
    """Run task.success_cmd in a subshell; return exit code or None."""
    if not task.success_cmd:
        return None
    try:
        p = subprocess.run(
            task.success_cmd,
            shell=True,
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=60,
        )
        return p.returncode
    except subprocess.TimeoutExpired:
        return 124
    except Exception:  # noqa: BLE001
        return 255


# --- Harness orchestration --------------------------------------------------


def run_task(
    task: ParityTask,
    project_root: Path,
    qwen_fn: Optional[Callable[..., ParityResult]] = None,
    claude_fn: Optional[Callable[..., ParityResult]] = None,
    claude_executor: Any = None,
    only_provider: Optional[str] = None,
    verbose: bool = False,
) -> List[ParityResult]:
    """Run one task through both providers. Injected *_fn parameters replace
    the real provider call — used by tests to avoid real API calls.
    """
    q_fn = qwen_fn or run_via_qwen
    c_fn = claude_fn or run_via_claude
    results: List[ParityResult] = []

    if only_provider in (None, "qwen"):
        results.append(q_fn(task, project_root, verbose=verbose))
    if only_provider in (None, "claude"):
        if c_fn is run_via_claude and claude_executor is None:
            results.append(ParityResult(
                task_id=task.id, provider="claude",
                error="no claude_executor provided — skipping claude leg",
            ))
        else:
            # Signature for the default run_via_claude includes claude_executor;
            # test-injected claude_fn may use a reduced signature.
            try:
                results.append(c_fn(
                    task, project_root,
                    claude_executor=claude_executor,
                    verbose=verbose,
                ))
            except TypeError:
                # Injected stub with simpler signature
                results.append(c_fn(task, project_root, verbose=verbose))

    return results


def emit_jsonl(
    records: List[ParityResult],
    path: Path,
    run_id: str,
) -> None:
    """Append each result as a JSONL record."""
    path.parent.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with path.open("a", encoding="utf-8") as fh:
        for r in records:
            rec = r.to_record()
            rec["ts"] = ts
            rec["run_id"] = run_id
            fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")


def render_csv(results: List[ParityResult]) -> str:
    """Render results as CSV with a stable column order."""
    buf = io.StringIO()
    cols = [
        "task_id", "provider", "model", "success",
        "tokens_in", "tokens_out", "cost_usd",
        "latency_ms", "tool_calls", "files_modified_count",
        "success_cmd_exit", "text_hash", "error",
    ]
    w = csv.writer(buf)
    w.writerow(cols)
    for r in results:
        w.writerow([
            r.task_id, r.provider, r.model, r.success,
            r.tokens_in, r.tokens_out, f"{r.cost_usd:.6f}",
            r.latency_ms, r.tool_calls, len(r.files_modified),
            "" if r.success_cmd_exit is None else r.success_cmd_exit,
            r.text_hash, r.error[:200],
        ])
    return buf.getvalue()


def render_markdown(results: List[ParityResult], tasks: List[ParityTask]) -> str:
    """Produce a Markdown comparison report with per-task winners."""
    by_task: Dict[str, Dict[str, ParityResult]] = {}
    for r in results:
        by_task.setdefault(r.task_id, {})[r.provider] = r

    out: List[str] = []
    out.append("# Parity Harness Report — Claude vs Qwen")
    out.append("")
    out.append(f"Tasks: {len(tasks)}. Providers: claude, qwen.")
    out.append("")
    out.append("| Task | Claude $ | Qwen $ | Claude ms | Qwen ms | Claude ok | Qwen ok | Winner (cost) | Winner (latency) |")
    out.append("|---|---:|---:|---:|---:|:---:|:---:|:---:|:---:|")

    # Totals
    tot_c = {"cost": 0.0, "lat": 0, "ok": 0, "n": 0}
    tot_q = {"cost": 0.0, "lat": 0, "ok": 0, "n": 0}

    for t in tasks:
        c = by_task.get(t.id, {}).get("claude")
        q = by_task.get(t.id, {}).get("qwen")

        c_cost = c.cost_usd if c else float("nan")
        q_cost = q.cost_usd if q else float("nan")
        c_lat = c.latency_ms if c else 0
        q_lat = q.latency_ms if q else 0
        c_ok = "✓" if c and c.success else "✗"
        q_ok = "✓" if q and q.success else "✗"

        if c and q:
            cost_winner = "qwen" if q_cost <= c_cost else "claude"
            lat_winner = "qwen" if q_lat <= c_lat else "claude"
            tot_c["cost"] += c.cost_usd; tot_c["lat"] += c.latency_ms
            tot_c["ok"] += int(c.success); tot_c["n"] += 1
            tot_q["cost"] += q.cost_usd; tot_q["lat"] += q.latency_ms
            tot_q["ok"] += int(q.success); tot_q["n"] += 1
        else:
            cost_winner = "—"
            lat_winner = "—"

        out.append(
            f"| `{t.id}` | {c_cost:.6f} | {q_cost:.6f} | "
            f"{c_lat} | {q_lat} | {c_ok} | {q_ok} | {cost_winner} | {lat_winner} |"
        )

    out.append("")
    out.append("## Totals (paired tasks only)")
    out.append("")
    if tot_c["n"]:
        out.append(f"- Claude: {tot_c['ok']}/{tot_c['n']} ok, ${tot_c['cost']:.4f}, {tot_c['lat']} ms total")
        out.append(f"- Qwen:   {tot_q['ok']}/{tot_q['n']} ok, ${tot_q['cost']:.4f}, {tot_q['lat']} ms total")
        if tot_c["cost"] > 0:
            ratio = tot_q["cost"] / tot_c["cost"] if tot_c["cost"] else 0.0
            out.append(f"- Cost ratio Qwen/Claude: {ratio:.3f}× "
                       f"(Qwen is {'cheaper' if ratio < 1 else 'pricier'})")

    out.append("")
    out.append("## Per-task details")
    out.append("")
    for t in tasks:
        out.append(f"### `{t.id}` — {t.description}")
        out.append("")
        for provider in ("claude", "qwen"):
            r = by_task.get(t.id, {}).get(provider)
            if r is None:
                out.append(f"- **{provider}**: (not run)")
                continue
            preview = r.text.strip().replace("\n", " ")
            if len(preview) > 120:
                preview = preview[:120] + "…"
            out.append(
                f"- **{provider}**: success={r.success} "
                f"tokens={r.tokens_in}→{r.tokens_out} "
                f"cost=${r.cost_usd:.6f} latency={r.latency_ms}ms "
                f"tools={r.tool_calls} files±{len(r.files_modified)}"
            )
            if preview:
                out.append(f"    - preview: `{preview}`")
            if r.error:
                out.append(f"    - error: `{r.error[:160]}`")
        out.append("")

    return "\n".join(out)


# --- CLI --------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(
        prog="parity-harness",
        description="ADR-051 Phase 4 — parity harness for Claude vs Qwen.",
    )
    p.add_argument("--tasks", required=True, type=Path,
                   help="YAML task-set file (see docs/benchmarks/parity-smoke.yaml).")
    p.add_argument("--jsonl", type=Path,
                   default=_PROJECT_ROOT / ".cognitive-os" / "metrics" / "parity-results.jsonl",
                   help="Append-only JSONL output. Default under .cognitive-os/metrics/.")
    p.add_argument("--csv", type=Path, default=None,
                   help="Write CSV summary to this path (default: stdout).")
    p.add_argument("--report", type=Path, default=None,
                   help="Write Markdown report to this path (default: stdout).")
    p.add_argument("--only-qwen", action="store_true", help="Skip Claude leg.")
    p.add_argument("--only-claude", action="store_true", help="Skip Qwen leg.")
    p.add_argument("--dry-run", action="store_true",
                   help="Load+render only; do not invoke any provider.")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args(argv)

    if not args.tasks.exists():
        print(f"ERROR: task-set file not found: {args.tasks}", file=sys.stderr)
        return 2

    tasks = load_tasks(args.tasks)
    if not tasks:
        print("ERROR: task-set is empty", file=sys.stderr)
        return 2

    run_id = uuid.uuid4().hex[:12]
    only_provider: Optional[str] = None
    if args.only_qwen and args.only_claude:
        print("ERROR: --only-qwen and --only-claude are mutually exclusive", file=sys.stderr)
        return 2
    if args.only_qwen:
        only_provider = "qwen"
    elif args.only_claude:
        only_provider = "claude"

    # Instantiate ClaudeExecutor lazily — only if we'll actually call it.
    claude_executor = None
    if not args.dry_run and only_provider != "qwen":
        try:
            from lib.claude_executor import ClaudeExecutor
            claude_executor = ClaudeExecutor(verbose=args.verbose)
        except Exception as exc:  # noqa: BLE001
            print(f"WARNING: ClaudeExecutor unavailable ({exc}); skipping Claude leg",
                  file=sys.stderr)

    all_results: List[ParityResult] = []
    for t in tasks:
        if args.verbose:
            print(f"[parity] running task {t.id}", file=sys.stderr)
        if args.dry_run:
            # Emit placeholder results so the report still renders.
            if only_provider in (None, "claude"):
                all_results.append(ParityResult(task_id=t.id, provider="claude",
                                                error="dry-run"))
            if only_provider in (None, "qwen"):
                all_results.append(ParityResult(task_id=t.id, provider="qwen",
                                                error="dry-run"))
            continue
        all_results.extend(run_task(
            t,
            _PROJECT_ROOT,
            claude_executor=claude_executor,
            only_provider=only_provider,
            verbose=args.verbose,
        ))

    # JSONL — always (tests inspect this file too)
    emit_jsonl(all_results, args.jsonl, run_id)

    csv_text = render_csv(all_results)
    md_text = render_markdown(all_results, tasks)

    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        args.csv.write_text(csv_text, encoding="utf-8")
    else:
        print(csv_text)

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(md_text, encoding="utf-8")
    else:
        print(md_text)

    print(f"\nrun_id: {run_id}", file=sys.stderr)
    print(f"jsonl:  {args.jsonl}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

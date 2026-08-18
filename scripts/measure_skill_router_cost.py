#!/usr/bin/env python3
"""Measure the CPU-vs-wall cost of SkillRouter construction and of the
UserPromptSubmit hook that builds one on every user prompt.

Why CPU and wall separately: a high wall time with low CPU means the process is
not getting scheduled (machine contention), while CPU close to wall means real
work. Reading only the wall clock cannot tell a hang from a busy machine, and
reading only CPU hides starvation. This script prints both plus a calibration
control (a pure CPU spin) so the reader can tell which regime the box is in.

Read-only. Does not touch repository state. Deterministic given the same tree.

Exit codes:
  0  routing-table CPU within budget (<= --budget-cpu, default 0.60s)
  1  routing-table CPU over budget
  2  error
"""

from __future__ import annotations

import argparse
import json
import os
import resource
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HOOK = PROJECT_ROOT / "hooks" / "skill-router-prompt-suggest.sh"

# The prompt the failing unit tests used; a GitHub URL routes to repo-forensics
# at confidence 0.99, i.e. it exercises the full high-confidence path.
SAMPLE_PROMPT = "audit https://github.com/HKUDS/OpenSpace and evaluate it"


def _cpu_self() -> float:
    r = resource.getrusage(resource.RUSAGE_SELF)
    return r.ru_utime + r.ru_stime


def _cpu_children() -> float:
    r = resource.getrusage(resource.RUSAGE_CHILDREN)
    return r.ru_utime + r.ru_stime


def calibrate(seconds: float = 1.0) -> float:
    """Return the fraction of a core this process actually gets.

    1.0 means an idle box. 0.2 means the process is being preempted and any
    wall-clock reading is inflated roughly 5x.
    """
    c0, t0 = _cpu_self(), time.monotonic()
    while time.monotonic() - t0 < seconds:
        pass
    wall = time.monotonic() - t0
    return (_cpu_self() - c0) / wall if wall else 0.0


def measure_routing_table() -> tuple[float, float, int]:
    sys.path.insert(0, str(PROJECT_ROOT))
    import cos_lib.skill_router as sr  # noqa: PLC0415

    sr._clear_skill_md_cache()
    c0, t0 = _cpu_self(), time.monotonic()
    table = sr._build_default_routing_table(PROJECT_ROOT)
    return time.monotonic() - t0, _cpu_self() - c0, len(table)


def count_yaml_parses() -> int:
    """Number of yaml.safe_load calls one routing-table build costs."""
    sys.path.insert(0, str(PROJECT_ROOT))
    import yaml  # noqa: PLC0415

    import cos_lib.skill_router as sr  # noqa: PLC0415

    calls = [0]
    original = yaml.safe_load

    def counting(*args, **kwargs):
        calls[0] += 1
        return original(*args, **kwargs)

    yaml.safe_load = counting
    try:
        sr._clear_skill_md_cache()
        sr._build_default_routing_table(PROJECT_ROOT)
    finally:
        yaml.safe_load = original
    return calls[0]


def measure_hook(timeout: float) -> dict:
    """Run the hook exactly as tests/unit/test_skill_router_prompt_suggest_hook.py does."""
    if not HOOK.exists():
        return {"status": "hook-missing"}
    tmp = Path(tempfile.mkdtemp(prefix="skill-router-cost-"))
    (tmp / ".cognitive-os" / "metrics").mkdir(parents=True, exist_ok=True)
    (tmp / "cos_lib").symlink_to(PROJECT_ROOT / "cos_lib")
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(tmp)
    env["PROJECT_DIR"] = str(tmp)
    env["PYTHONPATH"] = str(PROJECT_ROOT)

    c0, t0 = _cpu_children(), time.monotonic()
    try:
        proc = subprocess.run(
            ["bash", str(HOOK)],
            input=json.dumps({"prompt": SAMPLE_PROMPT}),
            capture_output=True,
            text=True,
            env=env,
            timeout=timeout,
        )
        status, stdout_len = f"rc={proc.returncode}", len(proc.stdout)
    except subprocess.TimeoutExpired:
        status, stdout_len = f"TIMEOUT>{timeout}s", 0
    wall, cpu = time.monotonic() - t0, _cpu_children() - c0
    log = tmp / ".cognitive-os" / "metrics" / "skill-suggestion.jsonl"
    return {
        "status": status,
        "wall": wall,
        "cpu": cpu,
        "stdout_bytes": stdout_len,
        "wrote_log": log.exists(),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--budget-cpu", type=float, default=0.60,
                    help="max acceptable CPU seconds for one routing-table build")
    ap.add_argument("--hook-timeout", type=float, default=10.0,
                    help="timeout for the hook run (10s = the unit test ceiling)")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of text")
    args = ap.parse_args()

    try:
        share = calibrate()
        wall, cpu, entries = measure_routing_table()
        parses = count_yaml_parses()
        hook = measure_hook(args.hook_timeout)
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 2

    over_budget = cpu > args.budget_cpu
    report = {
        "cpu_share_of_one_core": round(share, 3),
        "routing_table": {
            "wall_s": round(wall, 3),
            "cpu_s": round(cpu, 3),
            "entries": entries,
            "yaml_safe_load_calls": parses,
        },
        "hook": {k: (round(v, 3) if isinstance(v, float) else v) for k, v in hook.items()},
        "budget_cpu_s": args.budget_cpu,
        "over_budget": over_budget,
    }

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"CPU share of one core (calibration): {share:.2f}"
              f"{'  <-- machine is contended, wall times are inflated' if share < 0.8 else ''}")
        print(f"Routing table: wall={wall:.2f}s cpu={cpu:.2f}s "
              f"entries={entries} yaml.safe_load={parses}")
        print(f"Hook:          wall={hook.get('wall', 0):.2f}s cpu={hook.get('cpu', 0):.2f}s "
              f"{hook.get('status')} stdout={hook.get('stdout_bytes')}B "
              f"log={hook.get('wrote_log')}")
        print(f"Budget: cpu <= {args.budget_cpu}s -> "
              f"{'OVER BUDGET' if over_budget else 'within budget'}")

    return 1 if over_budget else 0


if __name__ == "__main__":
    sys.exit(main())

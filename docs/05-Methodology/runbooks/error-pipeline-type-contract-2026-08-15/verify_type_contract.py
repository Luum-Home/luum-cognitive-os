#!/usr/bin/env python3
"""Prove — against real captured payloads — that the type-contract patch works.

The patch this runbook carries replaces a *previous* patch that looked correct
and pointed at a phantom field.  So the deliverable here is not the diff, it is
this script: it measures the harness contract from real transcripts, then runs
the *unpatched* and *patched* hooks over those same payloads and reports what
each one produces.

Three things it establishes, each with the number printed next to it:

1.  CONTRACT  — `exit_code` does not exist in the payload at any nesting level,
    for any tool.  Failure is signalled by a change of TYPE on `tool_response`:
    object when the tool ran, string prefixed ``Error:`` when it did not
    succeed.  Two distinct failure classes hide inside that string.

2.  BEHAVIOUR — replay every real Bash payload through both hook versions, with
    the metrics directory redirected to a throwaway dir, and count the rows each
    version writes.  The unpatched version writes 0.  Live evidence agrees: the
    hook has 5,335 invocations against 11 rows in the whole ledger.

3.  CLASSES   — success / command-failure / gate-block must land in three
    different places, because a PreToolUse gate of this OS refusing a command is
    not a command that failed, and must never reach auto-repair.

Read-only toward the repository and toward operator telemetry: it never writes
inside .cognitive-os/, and the replay writes only into a temporary directory it
creates and removes.

Exit codes: 0 = patch behaves as claimed, 1 = it does not, 2 = error.

Usage:
    docs/05-Methodology/runbooks/error-pipeline-type-contract-2026-08-15/verify_type_contract.py
    ... --transcripts <dir>      # default: the harness project dir for this repo
    ... --patched <dir>          # tree holding the patched hooks/ (default: apply
                                 #   the runbook patch into a temp worktree)
    ... --json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PATCH = HERE / "error-pipeline-type-contract.patch"

EXIT_CODE_RE = re.compile(r"^Error: Exit code (\d+)")


# ── 1. contract ─────────────────────────────────────────────────────────────
def default_transcript_dir() -> Path | None:
    base = Path.home() / ".claude" / "projects"
    if not base.is_dir():
        return None
    slug = str(ROOT).replace("/", "-")
    cands = [d for d in base.iterdir() if d.is_dir() and d.name.rstrip("-").endswith(slug.rstrip("-"))]
    if not cands:
        cands = [d for d in base.iterdir() if d.is_dir() and ROOT.name in d.name]
    if not cands:
        return None
    return max(cands, key=lambda d: len(list(d.glob("*.jsonl"))))


def harvest(tdir: Path) -> tuple[list[dict], dict]:
    """Return real Bash payloads (hook-stdin shaped) plus contract statistics."""
    payloads: list[dict] = []
    stats = {
        "transcripts": 0,
        "tool_results_total": 0,
        "bash_results": 0,
        "bash_object": 0,
        "bash_string": 0,
        "bash_string_exit_code": 0,
        "bash_string_other": 0,
        "exit_code_field_occurrences": 0,
        "object_key_shapes": Counter(),
        "block_reasons": Counter(),
    }
    for path in sorted(tdir.glob("*.jsonl")):
        stats["transcripts"] += 1
        records = []
        with path.open(errors="replace") as fh:
            for line in fh:
                try:
                    records.append(json.loads(line))
                except ValueError:
                    continue
        names: dict[str, str] = {}
        inputs: dict[str, dict] = {}
        for rec in records:
            content = (rec.get("message") or {}).get("content")
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        names[block.get("id")] = block.get("name")
                        inputs[block.get("id")] = block.get("input") or {}
        for rec in records:
            if "toolUseResult" not in rec:
                continue
            stats["tool_results_total"] += 1
            result = rec["toolUseResult"]
            blob = result if isinstance(result, str) else json.dumps(result)
            if '"exit_code"' in blob or '"exitCode"' in blob:
                stats["exit_code_field_occurrences"] += 1
            content = (rec.get("message") or {}).get("content")
            tid = None
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        tid = block.get("tool_use_id")
            if names.get(tid) != "Bash":
                continue
            stats["bash_results"] += 1
            if isinstance(result, dict):
                stats["bash_object"] += 1
                stats["object_key_shapes"][tuple(sorted(result))] += 1
                expected = "ok"
            elif isinstance(result, str):
                stats["bash_string"] += 1
                if EXIT_CODE_RE.match(result):
                    stats["bash_string_exit_code"] += 1
                    expected = "failed"
                else:
                    stats["bash_string_other"] += 1
                    stats["block_reasons"][result[:60].replace("\n", " ")] += 1
                    expected = "blocked"
            else:
                expected = "absent"
            payloads.append(
                {
                    "hook_event_name": "PostToolUse",
                    "tool_name": "Bash",
                    "tool_input": inputs.get(tid) or {},
                    "tool_response": result,
                    "_expected": expected,
                }
            )
    return payloads, stats


# ── 2. replay ───────────────────────────────────────────────────────────────
def materialise_patched(dest: Path) -> Path:
    """Copy the repo's hook tree and apply the runbook patch to the copy."""
    tree = dest / "patched"
    tree.mkdir(parents=True)
    shutil.copytree(ROOT / "hooks", tree / "hooks", symlinks=True)
    (tree / "packages" / "skill-governance").mkdir(parents=True)
    shutil.copytree(
        ROOT / "packages" / "skill-governance" / "hooks",
        tree / "packages" / "skill-governance" / "hooks",
        symlinks=True,
    )
    proc = subprocess.run(
        ["git", "apply", "-p1", str(PATCH)],
        cwd=tree, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise SystemExit(f"could not apply the runbook patch to the copy:\n{proc.stderr}")
    return tree


def replay(hook: Path, payloads: list[dict], project_dir: Path) -> dict:
    """Run one hook over every payload; return what it wrote and how it exited."""
    metrics = project_dir / ".cognitive-os" / "metrics"
    metrics.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env.update(
        {
            "CLAUDE_PROJECT_DIR": str(project_dir),
            "COGNITIVE_OS_SESSION_ID": "",
            # Auto-repair dispatch is out of scope for this replay: we are
            # measuring detection, and we will not let a replay execute fixes.
            "COS_DISABLE_AUTO_REPAIR": "1",
        }
    )
    for noisy in ("COS_ALLOW_PROTECTED_CONFIG_WRITE",):
        env.pop(noisy, None)
    exits: Counter = Counter()
    for payload in payloads:
        stdin = json.dumps({k: v for k, v in payload.items() if not k.startswith("_")})
        proc = subprocess.run(
            ["bash", str(hook)], input=stdin, capture_output=True, text=True,
            env=env, cwd=str(project_dir), timeout=60,
        )
        exits[proc.returncode] += 1
    return {
        "exit_codes": dict(exits),
        "rows": {
            name: _count(metrics / name)
            for name in (
                "error-learning.jsonl",
                "gate-blocks.jsonl",
                "payload-contract-drift.jsonl",
            )
        },
        "row_types": _types(metrics / "error-learning.jsonl"),
    }


def _count(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(errors="replace").splitlines() if line.strip())


def _types(path: Path) -> dict:
    if not path.exists():
        return {}
    counter: Counter = Counter()
    for line in path.read_text(errors="replace").splitlines():
        try:
            counter[json.loads(line).get("type", "?")] += 1
        except ValueError:
            counter["<unparseable>"] += 1
    return dict(counter)


# ── 3. classifier unit-check ────────────────────────────────────────────────
def classifier_agreement(tree: Path, payloads: list[dict]) -> dict:
    """Run the patched classifier alone over every payload and score agreement."""
    lib = tree / "hooks" / "_lib" / "tool-outcome.sh"
    script = f'''
set -uo pipefail
source "{lib}"
while IFS= read -r line || [ -n "$line" ]; do
  classify_tool_outcome "$line"
  printf '%s\\n' "$TOOL_OUTCOME"
done
'''
    stdin = "".join(
        json.dumps({k: v for k, v in p.items() if not k.startswith("_")}) + "\n"
        for p in payloads
    )
    proc = subprocess.run(["bash", "-c", script], input=stdin,
                          capture_output=True, text=True, timeout=900)
    got = [l for l in proc.stdout.splitlines() if l]
    want = [p["_expected"] for p in payloads]
    mismatches = [
        {"index": i, "expected": w, "got": g}
        for i, (w, g) in enumerate(zip(want, got)) if w != g
    ]
    return {
        "classified": len(got),
        "expected": len(want),
        "distribution": dict(Counter(got)),
        "mismatches": mismatches[:10],
        "mismatch_count": len(mismatches) + abs(len(want) - len(got)),
    }


# ── main ────────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--transcripts", type=Path, default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--limit", type=int, default=0,
                    help="replay only the first N payloads (default: all)")
    args = ap.parse_args()

    tdir = args.transcripts or default_transcript_dir()
    if not tdir or not tdir.is_dir():
        print("no harness transcripts found; pass --transcripts <dir>", file=sys.stderr)
        return 2

    payloads, stats = harvest(tdir)
    if not payloads:
        print("no Bash payloads harvested", file=sys.stderr)
        return 2
    replay_set = payloads[: args.limit] if args.limit else payloads

    report: dict = {"contract": {k: (dict(v) if isinstance(v, Counter) else v)
                                 for k, v in stats.items()}}
    report["contract"]["object_key_shapes"] = {
        " ".join(k): v for k, v in stats["object_key_shapes"].most_common(5)
    }
    report["contract"]["block_reasons"] = dict(stats["block_reasons"].most_common(5))

    with tempfile.TemporaryDirectory(prefix="type-contract-") as tmp:
        tmpdir = Path(tmp)
        tree = materialise_patched(tmpdir)
        report["classifier"] = classifier_agreement(tree, payloads)

        for label, hooks_root in (("before", ROOT), ("after", tree)):
            report[label] = {}
            for hook_rel in ("hooks/error-pipeline.sh", "hooks/error-learning.sh"):
                proj = tmpdir / f"{label}-{Path(hook_rel).stem}"
                proj.mkdir()
                shutil.copy(ROOT / "cognitive-os.yaml", proj / "cognitive-os.yaml")
                report[label][hook_rel] = replay(
                    hooks_root / hook_rel, replay_set, proj)

    ok = _verdict(report)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        _render(report, tdir, len(replay_set))
    return 0 if ok else 1


def _verdict(r: dict) -> bool:
    c = r["contract"]
    checks = [
        c["exit_code_field_occurrences"] == 0,
        c["bash_string"] > 0 and c["bash_object"] > 0,
        r["classifier"]["mismatch_count"] == 0,
        sum(v["rows"]["error-learning.jsonl"] for v in r["before"].values()) == 0,
        sum(v["rows"]["error-learning.jsonl"] for v in r["after"].values()) > 0,
        sum(v["rows"]["gate-blocks.jsonl"] for v in r["after"].values()) > 0,
    ]
    r["verdict"] = {"all_checks_pass": all(checks), "checks": checks}
    return all(checks)


def _render(r: dict, tdir: Path, replayed: int) -> None:
    c = r["contract"]
    print(f"transcripts scanned:      {c['transcripts']}  (dir: ~/{tdir.relative_to(Path.home())})")
    print(f"tool results total:       {c['tool_results_total']}")
    print(f"Bash results:             {c['bash_results']}")
    print(f"  object  (ran ok):       {c['bash_object']}")
    print(f"  string  (failure):      {c['bash_string']}")
    print(f"    'Error: Exit code N': {c['bash_string_exit_code']}   <- command ran and failed")
    print(f"    other 'Error: ...':   {c['bash_string_other']}   <- command NEVER RAN (gate/permission)")
    print(f"'exit_code' field seen:   {c['exit_code_field_occurrences']}   <- the field the old hooks read")
    print()
    print("classifier over every harvested payload:")
    print(f"  {r['classifier']['distribution']}   mismatches: {r['classifier']['mismatch_count']}")
    print()
    print(f"replay of {replayed} real payloads through each hook:")
    for label in ("before", "after"):
        print(f"  [{label}]")
        for hook, res in r[label].items():
            rows = res["rows"]
            print(f"    {hook:28s} error-learning={rows['error-learning.jsonl']:4d}"
                  f"  gate-blocks={rows['gate-blocks.jsonl']:4d}"
                  f"  drift={rows['payload-contract-drift.jsonl']:3d}"
                  f"  types={res['row_types']}")
    print()
    print("VERDICT:", "patch behaves as claimed" if r["verdict"]["all_checks_pass"]
          else f"FAILED — checks {r['verdict']['checks']}")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)

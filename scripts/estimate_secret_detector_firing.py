#!/usr/bin/env python3
"""Estimate how often secret-detector's PreToolUse paths would fire, by replaying
historical Bash/Edit/Write/MultiEdit tool inputs from Claude Code transcripts
through the real hook.

Read-only. Never prints secret material: only pattern labels and counts.

Exit codes: 0 = no payload reaches the all-secrets block branch,
            1 = at least one payload reaches it, 2 = error.

Usage:
    python3 scripts/estimate_secret_detector_firing.py [--root DIR] [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# Same patterns as hooks/secret-detector.sh (SECRET_PATTERNS), Python-escaped.
PATTERNS = [
    r"(AKIA|ASIA)[0-9A-Z]{16}",
    r"ghp_[A-Za-z0-9]{36,}",
    r"gho_[A-Za-z0-9]{36,}",
    r"ghu_[A-Za-z0-9]{36,}",
    r"ghs_[A-Za-z0-9]{36,}",
    r"ghr_[A-Za-z0-9]{36,}",
    r"xox[abprs]-[A-Za-z0-9-]{10,}",
    r"https://hooks\.slack\.com/services/[A-Za-z0-9/_-]{20,}",
    r"sk_live_[A-Za-z0-9]{20,}",
    r"sk-proj-[A-Za-z0-9_-]{20,}",
    r"sk-ant-[A-Za-z0-9_-]{20,}",
    r"npm_[A-Za-z0-9]{20,}",
    r"sk-[A-Za-z0-9]{32,}",
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
]
UNION = re.compile("|".join(f"(?:{p})" for p in PATTERNS))
TOOLS = {"Bash", "Edit", "Write", "MultiEdit"}
FIELDS = ("command", "content", "new_string", "file_path")

REPO = Path(__file__).resolve().parent.parent
HOOK = REPO / "hooks" / "secret-detector.sh"


def iter_tool_inputs(root: Path):
    """Yield (tool_name, tool_input) for every historical tool_use, plus totals."""
    total = 0
    for path in sorted(root.rglob("*.jsonl")):
        try:
            with path.open("r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if '"tool_use"' not in line:
                        continue
                    hit = UNION.search(line)
                    try:
                        rec = json.loads(line)
                    except Exception:
                        continue
                    msg = rec.get("message") or {}
                    content = msg.get("content")
                    if not isinstance(content, list):
                        continue
                    for block in content:
                        if not isinstance(block, dict) or block.get("type") != "tool_use":
                            continue
                        name = block.get("name")
                        if name not in TOOLS:
                            continue
                        total += 1
                        if not hit:
                            continue
                        ti = block.get("input") or {}
                        blob = "\n".join(
                            str(ti[f]) for f in FIELDS if isinstance(ti.get(f), str)
                        )
                        if blob and UNION.search(blob):
                            yield name, ti
        except OSError:
            continue
    yield "__TOTAL__", total


def run_hook(tool: str, tool_input: dict, sandbox: Path):
    payload = json.dumps(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": tool,
            "tool_input": tool_input,
        }
    )
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(sandbox))
    proc = subprocess.run(
        ["/bin/bash", str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        env=env,
    )
    decision = None
    if proc.stdout.strip():
        try:
            decision = (
                json.loads(proc.stdout).get("hookSpecificOutput", {}).get("permissionDecision")
            )
        except Exception:
            decision = "unparseable"
    return proc.returncode, decision


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--root",
        default=str(Path.home() / ".claude" / "projects"),
        help="transcript root (default: the user's Claude Code projects dir)",
    )
    ap.add_argument("--json", action="store_true", help="emit JSON")
    args = ap.parse_args()

    root = Path(args.root).expanduser()
    if not root.is_dir():
        print(f"ERROR: transcript root not found: {root}", file=sys.stderr)
        return 2
    if not HOOK.exists():
        print(f"ERROR: hook not found: {HOOK}", file=sys.stderr)
        return 2

    tally = {"total_tool_calls": 0, "pattern_matches": 0, "would_redact": 0, "would_block": 0,
             "no_output": 0, "by_tool": {}, "by_pattern": {}}
    block_shapes = []

    with tempfile.TemporaryDirectory(prefix="secret-detector-replay-") as tmp:
        sandbox = Path(tmp)
        for tool, item in iter_tool_inputs(root):
            if tool == "__TOTAL__":
                tally["total_tool_calls"] = item
                break
            tally["pattern_matches"] += 1
            tally["by_tool"][tool] = tally["by_tool"].get(tool, 0) + 1
            blob = "\n".join(
                str(item[f]) for f in FIELDS if isinstance(item.get(f), str)
            )
            for idx, pat in enumerate(PATTERNS):
                if re.search(pat, blob):
                    tally["by_pattern"][pat] = tally["by_pattern"].get(pat, 0) + 1
            rc, decision = run_hook(tool, item, sandbox)
            if decision == "allow":
                tally["would_redact"] += 1
            elif decision in ("block", "deny"):
                tally["would_block"] += 1
                block_shapes.append({"tool": tool, "fields": sorted(k for k in item), "rc": rc,
                                     "decision": decision})
            else:
                tally["no_output"] += 1

    tally["block_shapes"] = block_shapes
    if args.json:
        print(json.dumps(tally, indent=2, sort_keys=True))
    else:
        print(f"transcript root      : {root}")
        print(f"tool calls scanned   : {tally['total_tool_calls']}")
        print(f"pattern matches      : {tally['pattern_matches']}")
        print(f"  -> redact + allow  : {tally['would_redact']}")
        print(f"  -> all-secrets path: {tally['would_block']}")
        print(f"  -> hook silent     : {tally['no_output']}")
        for pat, n in sorted(tally["by_pattern"].items(), key=lambda kv: -kv[1]):
            print(f"    pattern {pat!r}: {n}")
        for shape in block_shapes:
            print(f"    BLOCK shape: {shape}")
    return 1 if tally["would_block"] else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# SCOPE: os-only
"""Counterfactual probe: does the rule-router suppression actually discriminate?

Runs hooks/rule-router-prompt-suggest.sh four times against a throwaway project
directory -- never the operator's real metrics -- and asserts the four cells of
a 2x2 that a working suppression must produce:

                                  suppression ON   suppression OFF
    real task-notification payload      silent          EMITS
    typed prompt (positive control)     EMITS           EMITS

"suppression OFF" is the kill-switch the hook itself ships,
``COS_RULE_ROUTER_ALL_PAYLOADS=1``: the surgical revert, not a patched copy of
the hook, so the probe exercises the same code path an operator would use to
back the change out.

The positive control is the half that matters. A suppression that broke the
router outright would make the top-left cell go silent too and read as success;
the control fails loudly instead. A negative control (filler text emits in
neither branch) guards the other end.

The task-notification payload is a REAL one, pulled from this machine's
transcripts and chosen because the router scores it >= 0.80 -- a
task-notification the router never matched would go silent in both branches and
prove nothing. If no such payload exists locally the probe exits 2 rather than
publish a green it did not earn.

Exit: 0 all four cells as expected / 1 the probe does not discriminate /
      2 could not run (no corpus, missing hook).
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

HOOK = REPO / "hooks" / "rule-router-prompt-suggest.sh"

# A typed prompt the router demonstrably matches. Same anchor the precision
# script uses as its control, for the same reason: if the router stops matching
# it, the instrument is broken and must say so instead of reporting zeros.
CONTROL_TYPED_PROMPT = "check error-learning.jsonl for repeats before retrying"
CONTROL_FILLER_PROMPT = "zzzqqq unrelated lorem ipsum filler text padding here"


def transcript_glob() -> str:
    slug = str(REPO).replace("/", "-").replace(".", "-")
    return f"~/.claude/projects/{slug}/*.jsonl"


def user_prompts(pattern: str) -> list[str]:
    out: list[str] = []
    for path in sorted(glob.glob(os.path.expanduser(pattern))):
        try:
            with open(path, errors="ignore") as fh:
                for line in fh:
                    if '"type": "user"' not in line and '"type":"user"' not in line:
                        continue
                    try:
                        rec = json.loads(line)
                    except (ValueError, TypeError):
                        continue
                    if rec.get("type") != "user":
                        continue
                    content = (rec.get("message") or {}).get("content")
                    if isinstance(content, str) and content.strip():
                        out.append(content)
        except OSError:
            continue
    return out


def pick_emitting_task_notification(prompts: list[str]) -> str | None:
    from cos_lib.prompt_origin import ORIGIN_TASK_NOTIFICATION, classify_origin
    from cos_lib.rule_router import RuleRouter

    router = RuleRouter()
    for p in prompts:
        if classify_origin(p) != ORIGIN_TASK_NOTIFICATION:
            continue
        if router.top_matches(p, n=3, min_confidence=0.80):
            return p
    return None


def make_sandbox(root: Path) -> Path:
    """A project dir the hook can write to, with nothing of the operator's in it."""
    (root / ".cognitive-os" / "metrics").mkdir(parents=True, exist_ok=True)
    for name in ("cos_lib", "rules", "manifests"):
        src = REPO / name
        if src.exists() and not (root / name).exists():
            (root / name).symlink_to(src)
    return root


def run_hook(sandbox: Path, prompt: str, *, all_payloads: bool) -> tuple[str, list[dict]]:
    """Return (stdout, telemetry rows written by this invocation)."""
    log = sandbox / ".cognitive-os" / "metrics" / "rule-suggestion.jsonl"
    before = len(log.read_text().splitlines()) if log.is_file() else 0

    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(sandbox)
    env["PROJECT_DIR"] = str(sandbox)
    env["PYTHONPATH"] = str(REPO)
    env.pop("COS_RULE_ROUTER_ALL_PAYLOADS", None)
    if all_payloads:
        env["COS_RULE_ROUTER_ALL_PAYLOADS"] = "1"

    # The faithful envelope for this event -- the six fields the harness really
    # sends -- so the probe cannot pass on a payload the harness never produces.
    sys.path.insert(0, str(REPO))
    from tests.utils.harness_payload import payload as harness_payload

    stdin = json.dumps(harness_payload("UserPromptSubmit", cwd=str(sandbox),
                                       prompt=prompt))
    proc = subprocess.run(["bash", str(HOOK)], input=stdin, capture_output=True,
                          text=True, env=env, timeout=60)
    rows: list[dict] = []
    if log.is_file():
        for line in log.read_text().splitlines()[before:]:
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    pass
    return proc.stdout.strip(), rows


def emitted(stdout: str) -> bool:
    if not stdout:
        return False
    try:
        return "additionalContext" in json.loads(stdout).get("hookSpecificOutput", {})
    except ValueError:
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--transcripts", default=transcript_glob())
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not HOOK.is_file():
        print(f"ERROR: hook not found at {HOOK}", file=sys.stderr)
        return 2

    prompts = user_prompts(args.transcripts)
    if not prompts:
        print(f"ERROR: no local transcripts at {args.transcripts} -- the probe "
              f"needs a REAL task-notification payload and refuses to invent one",
              file=sys.stderr)
        return 2

    tn = pick_emitting_task_notification(prompts)
    if tn is None:
        print("ERROR: no task-notification in the local corpus scores >= 0.80. "
              "Such a payload would go silent in BOTH branches, so the probe "
              "cannot discriminate and refuses to report a pass.", file=sys.stderr)
        return 2

    cells: dict[str, dict] = {}
    with tempfile.TemporaryDirectory(prefix="rrps-probe-") as td:
        sandbox = make_sandbox(Path(td))
        for label, prompt in (("task_notification", tn),
                              ("typed_control", CONTROL_TYPED_PROMPT),
                              ("filler_control", CONTROL_FILLER_PROMPT)):
            for branch, all_payloads in (("suppression_on", False),
                                         ("suppression_off", True)):
                out, rows = run_hook(sandbox, prompt, all_payloads=all_payloads)
                cells[f"{label}/{branch}"] = {
                    "emitted": emitted(out),
                    "telemetry_rows": len(rows),
                    "evaluated": [r.get("evaluated") for r in rows],
                    "skipped_reason": [r.get("skipped_reason") for r in rows],
                    "prompt_origin": [r.get("prompt_origin") for r in rows],
                }

    checks = [
        ("task-notification is SILENT with the suppression on",
         cells["task_notification/suppression_on"]["emitted"] is False),
        ("task-notification EMITS with the suppression reverted "
         "(the branches differ -- the probe discriminates)",
         cells["task_notification/suppression_off"]["emitted"] is True),
        ("skipped payload still leaves a telemetry row",
         cells["task_notification/suppression_on"]["telemetry_rows"] == 1),
        ("that row is marked evaluated=false with a reason",
         cells["task_notification/suppression_on"]["evaluated"] == [False]
         and cells["task_notification/suppression_on"]["skipped_reason"]
         == ["not-human-authored:task-notification"]),
        ("POSITIVE CONTROL: typed prompt still emits AFTER the change",
         cells["typed_control/suppression_on"]["emitted"] is True),
        ("positive control also emits with the suppression reverted",
         cells["typed_control/suppression_off"]["emitted"] is True),
        ("NEGATIVE CONTROL: filler emits in neither branch",
         cells["filler_control/suppression_on"]["emitted"] is False
         and cells["filler_control/suppression_off"]["emitted"] is False),
    ]
    failed = [name for name, ok in checks if not ok]

    if args.json:
        print(json.dumps({"cells": cells,
                          "checks": {n: ok for n, ok in checks},
                          "failed": failed}, indent=2, sort_keys=True))
    else:
        for name, ok in checks:
            print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
        print()
        for k in sorted(cells):
            c = cells[k]
            print(f"  {k:38} emitted={str(c['emitted']):5} "
                  f"rows={c['telemetry_rows']} evaluated={c['evaluated']} "
                  f"origin={c['prompt_origin']}")
        if failed:
            print(f"\nFINDING: {len(failed)} check(s) failed -- the suppression "
                  f"does not behave as claimed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

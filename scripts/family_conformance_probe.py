#!/usr/bin/env python3
# SCOPE: os-only
"""Enumerate a family of controls BY BEHAVIOUR and flag the member that differs.

Why this exists
---------------
On 2026-08-15 three separate fixes each repaired part of a family and left the
rest standing. The clearest case is commit 3a6e737b, whose own message says
"Applied to check-local-privacy.sh and check_absolute_paths.py, which carry the
same defect independently" — the author looked for the family and found two of
three. Eight hours later the third member, ``hooks/research-compliance-guard.sh``,
blocked a legitimate commit with the defect that had just been fixed twice.

The census was taken by TEXT, and the family is defined by BEHAVIOUR. The third
member builds its pattern literal by concatenation (``MAC_HOME_SEG='/'"Users"``)
so that it does not trip itself, which also makes it invisible to any grep for
the pattern. It hid from the search because it was written to hide from itself.

So: do not ask who matches a pattern. Ask who REACTS to an input.

Method
------
A family is three fixtures and a screen, and nothing else:

  null          content the whole population must ignore. Separates "reacts to
                the content" from "reacts to being invoked at all" — a candidate
                that errors on an argv shape it does not accept reacts to BOTH
                real fixtures and would otherwise be reported as defective.
  must-trigger  content every member is supposed to catch.
  must-not-trigger
                the discriminator: content that RESEMBLES the trigger but is
                legitimate. Without it a member that blocks everything is
                indistinguishable from one that blocks correctly.

Every candidate is run against all three, in a throwaway git sandbox, under
every argv shape the family declares. The first shape that reacts to
must-trigger is the shape the other two fixtures are judged under — a member is
never scored across two different invocations.

The partition falls out; nobody declares membership:

  NON-MEMBER    silent on must-trigger under every shape
  CONFORMING    reacts to must-trigger, silent on must-not-trigger
  DEFECTIVE     reacts to must-trigger AND to must-not-trigger (over-trigger)
  INVERTED      silent on must-trigger, reacts to must-not-trigger
  NOISE         reacts to the null fixture; measures the invocation, not content
  UNMEASURABLE  timeout, or could not be executed

Following ``hooks/_lib/tool-outcome.sh``, "did not react" NEVER collapses into
"reacted correctly": NON-MEMBER and UNMEASURABLE are their own classes and are
counted separately from CONFORMING.

What this deliberately is not
-----------------------------
It does not know the names of the three known defects. Hardcoding them would be
the same move ``scripts/check_subagent_context_arrival.py`` rejects in its
docstring: mocking the transcript and asserting on the mock. The probe is
credible only if the known defects come back out of a run that was never told
they exist — run with ``--at <rev>`` against a commit that predates a fix and
the member should appear as DEFECTIVE.

Cheap green, closed
-------------------
An instrument that flags nobody exits 0 and measures nothing. If a family scans
to zero MEMBERS (not zero candidates — zero members), this exits 2. Silence is
not a pass.

Exit codes
----------
  0  every family had members and all of them conform
  1  at least one DEFECTIVE or INVERTED member
  2  error, or a family whose population guard failed (no members found)

Usage
-----
    python3 scripts/family_conformance_probe.py [--family NAME] [--at REV] [-v]
    python3 scripts/family_conformance_probe.py --json
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
FAMILY_ROOT = REPO / "tests" / "fixtures" / "family-probe"
TIMEOUT_S = 10  # a guard that needs longer than this on ONE staged file is unmeasurable

# A reaction is an exit code that refuses, or a harness block emitted on stdout.
# Exit 0 with a block payload is how a PreToolUse hook says no, so the exit code
# alone is not enough.
BLOCK_MARKERS = (
    '"permissionDecision": "block"',
    '"permissionDecision":"block"',
    '"decision": "block"',
    '"decision":"block"',
    '"continue": false',
    '"continue":false',
)

BLOCKED = "blocked"
SILENT = "silent"
UNMEASURABLE = "unmeasurable"


@dataclass
class Family:
    name: str
    question: str
    candidate_globs: list[str]
    channel_screen: list[str]
    fixture_path: str
    argv_shapes: list[list[str]]
    substitutions: dict[str, str] = field(default_factory=dict)
    stdin_payload: str = ""
    min_members: int = 2

    @classmethod
    def load(cls, spec_dir: Path) -> "Family":
        spec = yaml.safe_load((spec_dir / "family.yaml").read_text())
        return cls(
            name=spec["name"],
            question=spec["question"].strip(),
            candidate_globs=spec["candidate_globs"],
            channel_screen=spec["channel_screen"],
            fixture_path=spec["fixture_path"],
            argv_shapes=[list(s or []) for s in spec["argv_shapes"]],
            substitutions=spec.get("substitutions") or {},
            stdin_payload=spec.get("stdin_payload", ""),
            min_members=int(spec.get("min_members", 2)),
        )


def fixture_text(spec_dir: Path, name: str, subs: dict[str, str]) -> str:
    """Render a stored fixture into the bytes the candidate will see.

    A fixture whose job is to CONTAIN the bad thing cannot be stored verbatim in
    a repository that scans for the bad thing. That is not a flaw in the probe;
    it is the same wall that made this family hard to enumerate, seen from the
    other side.

    The repository already contains the answer. ``hooks/research-compliance-guard.sh``
    composes its own pattern at run time (``MAC_HOME_SEG='/'"Users"``) precisely
    so that it does not trip itself — the property that made it invisible to the
    grep census that missed it. The fixtures do the same: a substitution value
    may be a LIST of pieces, joined here and only here. Nothing versioned holds
    the assembled literal, so no future gate has to carry an exception for these
    files, and the composition states what makes the input dangerous instead of
    leaving it implicit in an example.
    """
    text = (spec_dir / name).read_text()
    for token, value in subs.items():
        joined = "".join(value) if isinstance(value, list) else value
        text = text.replace(token, joined)
    return text


def build_sandbox(root: Path, rel_path: str, content: str) -> None:
    home = root / "home"
    home.mkdir(parents=True, exist_ok=True)
    target = root / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    env = {**os.environ, "HOME": str(home), "GIT_CONFIG_GLOBAL": "/dev/null"}
    for cmd in (
        ["git", "init", "-q"],
        ["git", "config", "user.email", "probe@example.invalid"],
        ["git", "config", "user.name", "probe"],
        ["git", "add", rel_path],
    ):
        subprocess.run(cmd, cwd=root, env=env, capture_output=True, check=False)


def run_candidate(
    candidate: Path, source: Path, argv: list[str], sandbox: Path, rel_path: str, stdin: str
) -> tuple[str, str]:
    """Run one candidate against one prepared sandbox. Returns (outcome, detail)."""
    home = sandbox / "home"
    env = {
        **os.environ,
        "HOME": str(home),
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_TERMINAL_PROMPT": "0",
        "NO_COLOR": "1",
        "COGNITIVE_OS_PROJECT_DIR": str(sandbox),
        "CLAUDE_PROJECT_DIR": str(sandbox),
        "CODEX_PROJECT_DIR": str(sandbox),
    }
    # No bypass variables. A probe that disables the thing it measures is theatre.
    for key in list(env):
        if "BYPASS" in key or key.startswith("DISABLE_HOOK_"):
            env.pop(key)

    argv = [a.replace("{fixture}", rel_path) for a in argv]
    interpreter = ["python3"] if source.suffix == ".py" else ["bash"]
    cmd = [*interpreter, str(candidate), *argv]
    try:
        proc = subprocess.run(
            cmd,
            cwd=sandbox,
            env=env,
            input=stdin,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return UNMEASURABLE, "timeout"
    except OSError as exc:  # pragma: no cover - execution environment
        return UNMEASURABLE, f"exec-error: {exc}"

    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode >= 126:
        return UNMEASURABLE, f"exit={proc.returncode}"
    if proc.returncode != 0:
        return BLOCKED, f"exit={proc.returncode}"
    if any(marker in (proc.stdout or "") for marker in BLOCK_MARKERS):
        return BLOCKED, "block-payload"
    return SILENT, f"exit=0 out={len(out)}b"


def materialize(source: Path, at_rev: str | None, workdir: Path) -> Path | None:
    """Return a runnable copy of the candidate, optionally from an older commit."""
    if at_rev is None:
        return source
    rel = source.relative_to(REPO)
    proc = subprocess.run(
        ["git", "show", f"{at_rev}:{rel}"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return None  # did not exist at that revision
    dest = workdir / rel.name
    dest.write_text(proc.stdout)
    return dest


def screen_candidates(family: Family, at_rev: str | None) -> tuple[list[Path], int]:
    """Static screen on the family's INPUT CHANNEL, never on its pattern.

    Executing all 708 scripts under hooks/ and scripts/ is neither fast nor safe
    (installers, LLM dispatchers, daemons live there). The screen asks only
    whether a candidate can read staged repository content at all. It is the one
    place a member could still hide, and it is deliberately orthogonal to the
    pattern the family is about: the guard that concatenates its literal to stay
    invisible to a pattern grep still says ``git diff --cached`` in the clear.
    """
    seen: list[Path] = []
    total = 0
    for pattern in family.candidate_globs:
        for path in sorted(REPO.glob(pattern)):
            if not path.is_file():
                continue
            total += 1
            try:
                text = path.read_text(errors="ignore")
            except OSError:
                continue
            if any(needle in text for needle in family.channel_screen):
                seen.append(path)
    return seen, total


def classify(null: str, pos: str, neg: str) -> str:
    if null == BLOCKED:
        return "NOISE"
    if UNMEASURABLE in (null, pos, neg):
        return "UNMEASURABLE"
    if pos == BLOCKED and neg == SILENT:
        return "CONFORMING"
    if pos == BLOCKED and neg == BLOCKED:
        return "DEFECTIVE"
    if pos == SILENT and neg == BLOCKED:
        return "INVERTED"
    return "NON-MEMBER"


def probe_family(spec_dir: Path, at_rev: str | None, verbose: bool) -> dict:
    family = Family.load(spec_dir)
    fixtures = {
        "null": fixture_text(spec_dir, "null.md", family.substitutions),
        "pos": fixture_text(spec_dir, "must-trigger.md", family.substitutions),
        "neg": fixture_text(spec_dir, "must-not-trigger.md", family.substitutions),
    }
    candidates, scanned = screen_candidates(family, at_rev)

    def probe_one(source: Path) -> dict:
        workdir = Path(tempfile.mkdtemp(prefix="famprobe-"))
        try:
            candidate = materialize(source, at_rev, workdir)
            if candidate is None:
                return {
                    "candidate": str(source.relative_to(REPO)),
                    "verdict": "ABSENT-AT-REV",
                    "shape": None,
                }
            results: dict[str, tuple[str, str]] = {}
            chosen: list[str] | None = None
            for shape in family.argv_shapes:
                sandbox = workdir / ("sbx-pos-" + str(family.argv_shapes.index(shape)))
                sandbox.mkdir(parents=True, exist_ok=True)
                build_sandbox(sandbox, family.fixture_path, fixtures["pos"])
                outcome = run_candidate(
                    candidate, source, shape, sandbox, family.fixture_path, family.stdin_payload
                )
                if outcome[0] == BLOCKED:
                    chosen = shape
                    results["pos"] = outcome
                    break
                results["pos"] = outcome
            if chosen is None:
                chosen = family.argv_shapes[0]
            for key in ("null", "neg"):
                sandbox = workdir / f"sbx-{key}"
                sandbox.mkdir(parents=True, exist_ok=True)
                build_sandbox(sandbox, family.fixture_path, fixtures[key])
                results[key] = run_candidate(
                    candidate, source, chosen, sandbox, family.fixture_path, family.stdin_payload
                )
            verdict = classify(results["null"][0], results["pos"][0], results["neg"][0])
            return {
                "candidate": str(source.relative_to(REPO)),
                "verdict": verdict,
                "shape": chosen,
                "null": results["null"],
                "pos": results["pos"],
                "neg": results["neg"],
            }
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    with ThreadPoolExecutor(max_workers=16) as pool:
        rows = list(pool.map(probe_one, candidates))

    buckets: dict[str, list[dict]] = {}
    for row in rows:
        buckets.setdefault(row["verdict"], []).append(row)
    members = (
        len(buckets.get("CONFORMING", []))
        + len(buckets.get("DEFECTIVE", []))
        + len(buckets.get("INVERTED", []))
    )
    return {
        "family": family.name,
        "question": family.question,
        "at": at_rev or "working tree",
        "scanned": scanned,
        "screened_in": len(candidates),
        "members": members,
        "min_members": family.min_members,
        "buckets": buckets,
        "rows": rows,
    }


def report(result: dict, verbose: bool) -> None:
    print(f"\n=== family: {result['family']}  ({result['at']}) ===")
    print(f"  {result['question']}")
    print(
        f"  scanned {result['scanned']} candidates, "
        f"{result['screened_in']} passed the channel screen, "
        f"{result['members']} are members"
    )
    for verdict in ("DEFECTIVE", "INVERTED", "CONFORMING", "NOISE", "UNMEASURABLE"):
        rows = result["buckets"].get(verdict, [])
        if not rows:
            continue
        print(f"  {verdict} ({len(rows)}):")
        for row in rows:
            shape = " ".join(row["shape"] or []) or "(no args)"
            print(f"    - {row['candidate']}   [{shape}]")
            if verbose and verdict in ("DEFECTIVE", "INVERTED", "UNMEASURABLE"):
                for key in ("null", "pos", "neg"):
                    print(f"        {key}: {row[key][0]} {row[key][1]}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--family", default=None, help="Probe only this family.")
    parser.add_argument(
        "--at",
        default=None,
        help="Materialize candidates from this git revision instead of the working tree.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable results.")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    if not FAMILY_ROOT.is_dir():
        print(f"ERROR: no family fixtures at {FAMILY_ROOT.relative_to(REPO)}", file=sys.stderr)
        return 2
    specs = sorted(p for p in FAMILY_ROOT.iterdir() if (p / "family.yaml").is_file())
    if args.family:
        specs = [p for p in specs if p.name == args.family]
    if not specs:
        print("ERROR: no families to probe", file=sys.stderr)
        return 2

    results = [probe_family(spec, args.at, args.verbose) for spec in specs]
    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        for result in results:
            report(result, args.verbose)

    exit_code = 0
    for result in results:
        # Population guard: an instrument that flags nobody is not a pass.
        if result["members"] < result["min_members"]:
            print(
                f"POPULATION GUARD FAILED: family {result['family']} found "
                f"{result['members']} members, expected at least {result['min_members']}",
                file=sys.stderr,
            )
            exit_code = max(exit_code, 2)
        bad = len(result["buckets"].get("DEFECTIVE", [])) + len(
            result["buckets"].get("INVERTED", [])
        )
        if bad:
            exit_code = max(exit_code, 1)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Run one snippet against a git revision AND against the working tree, and
refuse to report numbers when both runs measured the same artefact.

The failure this exists to prevent
----------------------------------
A "before/after" measurement extracts old code with `git archive` and runs a
snippet against it.  In a repo installed as an editable package, site-packages
carries a `.pth` file holding the live repo root, so `import cos_lib.agent_bus`
resolves to the LIVE tree no matter what the cwd is.  The "before" run silently
measures the "after" code and its output looks like perfect evidence.

Verified on this repo (see docs/06-Daily/reports/medicion-antes-despues-blindada-2026-08-15.md):
`python -I` does NOT prevent it (`-I` implies `-E -s`, not `-S`; site processing
still runs the `.pth`).  `-S` does prevent it, and also removes site-packages,
so nothing third-party imports any more.  What works is prepending the run root
to PYTHONPATH plus pruning the live root out of sys.path in the child.

The contract
------------
This module does not assert on the RESULT.  It asserts on the PROVENANCE of
whatever produced the result: every run reports, for each module it loaded, the
resolved real path AND the sha256 of the file contents.

  * two runs with the same provenance digest  -> NullComparison (the comparison
    is void, whatever the numbers say)
  * a run that loaded a file from outside its own root -> ProvenanceLeak

Path alone is not enough.  ~22% of `lib/*.py` in this repo are symlinks into
`packages/*/lib/*.py`, and a `git archive` of the checked-out revision produces
a different path holding byte-identical content.  Both cases are the same
artefact wearing two paths, so the identifier hashes content and resolves
symlinks before comparing.

Usage (library)
---------------
    from scripts.revision_probe import run_pair
    pair = run_pair("HEAD~2", snippet, modules=["cos_lib.agent_bus"])
    pair.before.value, pair.after.value      # stdout of each run
    pair.before.provenance                   # {module: (relpath, sha256)}

`run_pair` raises on a void comparison.  There is no flag to downgrade that to
a warning: a warning is read only by someone who already suspects, and the
whole point is that nobody suspects.

Usage (CLI)
-----------
    python3 scripts/revision_probe.py --rev HEAD~2 \
        --module cos_lib.agent_bus --snippet-file /tmp/snippet.py

Exit codes: 0 comparison valid, 1 comparison rejected, 2 error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "NullComparison",
    "ProvenanceLeak",
    "NothingMeasured",
    "ProbeError",
    "RunResult",
    "PairResult",
    "run_pair",
]


class ProbeError(RuntimeError):
    """The probe could not produce a comparison at all."""


class NullComparison(ProbeError):
    """Both runs resolved to the same artefact: the comparison measures nothing."""


class ProvenanceLeak(ProbeError):
    """A run loaded a module from outside the root it was supposed to measure."""


class NothingMeasured(ProbeError):
    """A module under comparison never loaded, so the pair proves nothing."""


# The child-side prelude.  Kept as source text (not a file in the repo) so the
# runner lands INSIDE the run root, which makes sys.path[0] the run root.
_RUNNER = r'''
import json, os, sys, hashlib

RUN_ROOT = os.path.realpath(sys.argv[1])
LIVE_ROOT = os.path.realpath(sys.argv[2])
SNIPPET = sys.argv[3]
OUT = sys.argv[4]

# The editable install puts LIVE_ROOT on sys.path via a .pth in site-packages.
# Dropping it here is what stops a module missing from RUN_ROOT from silently
# falling through to the live tree.  When RUN_ROOT *is* LIVE_ROOT (the working
# tree run) this is a no-op by construction.
if RUN_ROOT != LIVE_ROOT:
    sys.path[:] = [
        p for p in sys.path
        if os.path.realpath(p or os.getcwd()) != LIVE_ROOT
    ]
sys.path.insert(0, RUN_ROOT)

_before = set(sys.modules)
_status = "ok"
_error = ""
try:
    with open(SNIPPET) as fh:
        code = compile(fh.read(), SNIPPET, "exec")
    exec(code, {"__name__": "__main__", "__file__": SNIPPET})
except BaseException as exc:  # noqa: BLE001 - provenance must survive failures
    _status = "error"
    _error = "%s: %s" % (type(exc).__name__, exc)

def _digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

prov = {}
leaks = {}
for name, mod in list(sys.modules.items()):
    if name in _before or mod is None:
        continue
    f = getattr(mod, "__file__", None)
    if not f or not f.endswith(".py"):
        continue
    real = os.path.realpath(f)
    under_run = real == RUN_ROOT or real.startswith(RUN_ROOT + os.sep)
    under_live = real == LIVE_ROOT or real.startswith(LIVE_ROOT + os.sep)
    if not (under_run or under_live):
        continue  # stdlib / third-party: not part of the artefact under test
    try:
        d = _digest(real)
    except OSError:
        continue
    rel = os.path.relpath(real, RUN_ROOT if under_run else LIVE_ROOT)
    entry = [rel, d]
    if under_run:
        prov[name] = entry
    else:
        leaks[name] = entry

with open(OUT, "w") as fh:
    json.dump({"status": _status, "error": _error,
               "provenance": prov, "leaks": leaks}, fh)
'''


@dataclass
class RunResult:
    label: str
    root: str
    value: str
    stderr: str
    returncode: int
    provenance: dict  # {module: (relpath, sha256)}

    def digest(self) -> str:
        """Stable identifier of WHAT this run measured (never of the result)."""
        payload = json.dumps(sorted(self.provenance.items()), sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]


@dataclass
class PairResult:
    rev: str
    before: RunResult
    after: RunResult


def _repo_root(start: Path | None = None) -> Path:
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=str(start or Path.cwd()),
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(out.stdout.strip()).resolve()


def _extract(rev: str, root: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    archive = subprocess.run(
        ["git", "archive", rev],
        cwd=str(root),
        capture_output=True,
        check=False,
    )
    if archive.returncode != 0:
        raise ProbeError(
            f"git archive {rev} failed: {archive.stderr.decode(errors='replace').strip()}"
        )
    tar = subprocess.run(
        ["tar", "-x", "-C", str(dest)], input=archive.stdout, capture_output=True
    )
    if tar.returncode != 0:
        raise ProbeError(f"tar failed: {tar.stderr.decode(errors='replace').strip()}")


def _run_one(
    label: str,
    run_root: Path,
    live_root: Path,
    snippet_path: Path,
    timeout_s: int,
) -> RunResult:
    # `timeout(1)` is absent on this macOS; subprocess handles the deadline.
    runner = run_root / f".revision_probe_runner_{os.getpid()}.py"
    out_fd, out_path = tempfile.mkstemp(prefix="revprobe-", suffix=".json")
    os.close(out_fd)
    runner.write_text(_RUNNER)
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["PYTHONPATH"] = str(run_root)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        proc = subprocess.run(
            [sys.executable, str(runner), str(run_root), str(live_root),
             str(snippet_path), out_path],
            cwd=str(run_root),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        try:
            payload = json.loads(Path(out_path).read_text())
        except (OSError, ValueError) as exc:
            raise ProbeError(
                f"[{label}] runner produced no provenance ({exc}); stderr: {proc.stderr[-500:]}"
            ) from exc
    finally:
        runner.unlink(missing_ok=True)
        Path(out_path).unlink(missing_ok=True)

    if payload["leaks"]:
        raise ProvenanceLeak(
            f"[{label}] loaded modules from outside its own root: "
            + ", ".join(sorted(payload["leaks"]))
        )
    if payload["status"] == "error":
        raise ProbeError(f"[{label}] snippet raised {payload['error']}")

    return RunResult(
        label=label,
        root=str(run_root),
        value=proc.stdout,
        stderr=proc.stderr,
        returncode=proc.returncode,
        provenance={k: tuple(v) for k, v in payload["provenance"].items()},
    )


def run_pair(
    rev: str,
    snippet: str,
    *,
    modules: list[str] | None = None,
    repo_root: str | os.PathLike | None = None,
    timeout_s: int = 120,
    workdir: str | os.PathLike | None = None,
) -> PairResult:
    """Run `snippet` against `rev` and against the working tree.

    `modules`, when given, is the set of modules whose provenance must be
    present and must differ between the two runs.  Leave it empty and the probe
    compares every module either run loaded from inside its own root.

    Raises NullComparison when both runs resolved to the same artefact, and
    ProvenanceLeak when a run reached outside its own root.
    """
    live_root = Path(repo_root).resolve() if repo_root else _repo_root()
    tmp = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix="revprobe-"))
    owns_tmp = workdir is None
    try:
        old_root = tmp / "rev"
        _extract(rev, live_root, old_root)

        snippet_path = tmp / "snippet.py"
        snippet_path.write_text(snippet)

        before = _run_one("before", old_root, live_root, snippet_path, timeout_s)
        after = _run_one("after", live_root, live_root, snippet_path, timeout_s)

        wanted = modules or sorted(set(before.provenance) | set(after.provenance))
        missing = [m for m in wanted if m not in before.provenance or m not in after.provenance]
        if missing:
            raise NothingMeasured(
                "modules never loaded in both runs, so nothing was compared: "
                + ", ".join(missing)
            )

        same = [m for m in wanted if before.provenance[m][1] == after.provenance[m][1]]
        if len(same) == len(wanted):
            raise NullComparison(
                f"before and after resolved to the SAME artefact for every module "
                f"({', '.join(wanted)}); rev={rev} digest={before.digest()}. "
                "The comparison is void regardless of the numbers it printed."
            )
        return PairResult(rev=rev, before=before, after=after)
    finally:
        if owns_tmp:
            shutil.rmtree(tmp, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--rev", required=True, help="revision to use as 'before'")
    ap.add_argument("--snippet-file", required=True, help="python file to run in both roots")
    ap.add_argument("--module", action="append", default=[],
                    help="module whose provenance must differ (repeatable)")
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)

    try:
        pair = run_pair(
            args.rev,
            Path(args.snippet_file).read_text(),
            modules=args.module or None,
            timeout_s=args.timeout,
        )
    except (NullComparison, ProvenanceLeak, NothingMeasured) as exc:
        print(f"REJECTED: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps({
            "rev": pair.rev,
            "before": {"digest": pair.before.digest(),
                       "provenance": pair.before.provenance,
                       "value": pair.before.value},
            "after": {"digest": pair.after.digest(),
                      "provenance": pair.after.provenance,
                      "value": pair.after.value},
        }, indent=2, default=list))
    else:
        for run in (pair.before, pair.after):
            print(f"== {run.label} (digest {run.digest()})")
            for mod, (rel, sha) in sorted(run.provenance.items()):
                print(f"   {mod}  {rel}  sha256:{sha[:12]}")
            print(run.value.rstrip("\n"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

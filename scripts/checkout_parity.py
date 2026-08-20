#!/usr/bin/env python3
# SCOPE: os-only
"""Answer one question about a green gate: does it belong to the code, or to this checkout?

A gate that passes here and fails on a clean clone is not measuring the code, it
is measuring the machine it ran on. The failure mode has no textual signature --
nothing declares "I depend on an untracked file" -- so a static detector cannot
find it. What CAN find it is a differential: run the same gate twice, once
against the working tree and once against a tree containing only what `git
archive HEAD` ships, and compare the verdicts. If they differ, the green was the
checkout's.

Usage:
    scripts/checkout_parity.py -- <command to run>
    scripts/checkout_parity.py --ref origin/main -- .venv/bin/pytest tests/audit -q

Exit codes:
    0  both trees agree (the gate's verdict is a property of the code)
    1  the trees disagree (the verdict depends on checkout-local state)
    2  the procedure itself failed (archive/extract error, bad usage)

Semantics of --ref, learned the hard way: it changes only the CLEAN side. The
dirty side is always the working tree as it stands right now, running the code
you have checked out. So `--ref <old>` asks "does my current tree agree with
what <old> shipped", which is NOT a retrospective on <old>. To ask whether an
already-fixed bug would have been caught, materialise the old ref twice by hand
and add the machine-local artefact to one copy -- the divergence you are hunting
is between two trees at the SAME commit.

Read-only with respect to the repository: it never writes inside the working
tree, never stages, never mutates git state. The only writes go to a temporary
directory, removed on exit unless --keep is passed.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Variables whose value is an approval, a budget override or a harness bypass.
# The subprocess inherits the parent environment, so a probe launched from a
# session that already exported an approval measures a gate that approves
# everything. Scrubbed on BOTH sides so the comparison stays honest.
APPROVAL_ENV_PREFIXES = (
    "COS_ALLOW_",
    "COS_FORCE_",
    "COS_DISABLE_",
    "COS_SKIP_",
    "DISABLE_HOOK_",
    "DRY_RUN",
)


def _run(cmd: list[str], cwd: Path, env: dict[str, str], timeout: int):
    """Run one side of the comparison. Returns (exit_code, stdout+stderr)."""
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return 124, f"TIMEOUT after {timeout}s"
    except OSError as exc:
        return 2, f"OSError: {exc}"
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def _clean_env(real_root: Path, target_root: Path, extra: list[str] | None = None) -> dict[str, str]:
    """Build the environment for one side.

    Two hazards are neutralised:

    1. Inherited approval / bypass variables. A gate measured under an inherited
       ``COS_ALLOW_*`` is a gate that was told to say yes.
    2. Absolute paths pointing back at the real checkout. ``PYTHONPATH``,
       ``COS_ROOT`` and friends would make the clean tree import and read the
       dirty one, silently defeating the whole comparison. Any value mentioning
       the real root is rewritten to the tree actually under test.
    """
    env = {}
    real = str(real_root)
    target = str(target_root)
    for key, value in os.environ.items():
        if any(key.startswith(p) for p in APPROVAL_ENV_PREFIXES):
            continue
        if real in value:
            value = value.replace(real, target)
        env[key] = value
    env["PWD"] = target

    # A venv installed in editable mode drops a .pth naming the real checkout,
    # so site-packages silently appends the dirty tree to sys.path -- from the
    # clean run too. PYTHONPATH is consulted before .pth entries, so pinning the
    # tree under test at the front is what keeps `import cos_lib` honest. This
    # was not a precaution: the leak is present in this repo's .venv today.
    existing = env.get("PYTHONPATH", "")
    parts = [p for p in existing.split(os.pathsep) if p and p != target]
    env["PYTHONPATH"] = os.pathsep.join([target, *parts])

    env["COS_CHECKOUT_PARITY"] = "1"
    for item in extra or []:
        key, _, value = item.partition("=")
        env[key] = value
    return env


def materialise_tracked_tree(ref: str, dest: Path) -> None:
    """Extract exactly what `git archive <ref>` ships -- the tree that travels.

    `git worktree` is blocked in this repo (ADR-055b) and would be the wrong
    tool anyway: a worktree shares the object store and the ignore rules but,
    more importantly, `git archive` is the honest model of a fresh clone plus
    checkout -- tracked content only, no ignored files, no untracked leftovers.
    """
    dest.mkdir(parents=True, exist_ok=True)
    archive = subprocess.Popen(
        ["git", "archive", ref], cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    extract = subprocess.Popen(["tar", "-x", "-C", str(dest)], stdin=archive.stdout)
    if archive.stdout is not None:
        archive.stdout.close()
    extract.communicate()
    archive.wait()
    if archive.returncode != 0:
        err = archive.stderr.read().decode() if archive.stderr else ""
        raise RuntimeError(f"git archive {ref} failed ({archive.returncode}): {err}")
    if extract.returncode != 0:
        raise RuntimeError(f"tar extract failed ({extract.returncode})")


def materialise_tracked_worktree(dest: Path) -> None:
    """Copy the CURRENT content of tracked files only -- no commit required.

    `git archive HEAD` answers "does the last commit stand on its own", which
    makes uncommitted work invisible to the clean side. That is the wrong
    question just before you commit, which is precisely when you want the
    answer. This mode keeps every local edit to tracked files and drops only
    what would not travel: ignored files, untracked files, build output.
    """
    listing = subprocess.run(
        ["git", "ls-files", "-s", "-z"], cwd=str(ROOT), capture_output=True, check=True
    )
    dest.mkdir(parents=True, exist_ok=True)
    for raw in listing.stdout.split(b"\0"):
        if not raw:
            continue
        meta, _, path = raw.partition(b"\t")
        # Mode 160000 is a gitlink (submodule): a tracked path that is a
        # directory pointer, not content. `git archive` omits it, so this mode
        # must too, or the two clean trees stop being the same tree.
        if meta.split(b" ", 1)[0] == b"160000":
            continue
        rel = path.decode("utf-8", "surrogateescape")
        src = ROOT / rel
        if not src.exists():  # deleted-but-still-tracked
            continue
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        if src.is_symlink():
            target = os.readlink(src)
            if not out.is_symlink():
                out.symlink_to(target)
        else:
            shutil.copy2(src, out)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run one gate against the working tree and against the tracked-only tree, and compare verdicts.",
    )
    parser.add_argument(
        "--ref",
        default="HEAD",
        help=(
            "Git ref to materialise as the tracked-only tree (default: HEAD). "
            "Changes the clean side only; the dirty side is always the current working tree."
        ),
    )
    parser.add_argument(
        "--worktree",
        action="store_true",
        help=(
            "Build the clean tree from the CURRENT content of tracked files instead of "
            "from --ref. Use this before committing: it keeps your uncommitted edits and "
            "removes only what would not travel."
        ),
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Per-side timeout in seconds (default: 600). Portable: does not use timeout(1), absent on macOS.",
    )
    parser.add_argument(
        "--keep",
        action="store_true",
        help="Keep the extracted tree for inspection instead of deleting it.",
    )
    parser.add_argument(
        "--show-output",
        action="store_true",
        help="Print the tail of each side's output, not just the verdicts.",
    )
    parser.add_argument(
        "--env",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help=(
            "Set a variable on BOTH sides. For toolchain preconditions a fresh clone "
            "would satisfy differently (e.g. PYTEST_ALLOW_NONVENV=1, since a linked "
            "venv still resolves to its real prefix). Symmetric by construction: it "
            "cannot manufacture agreement, only remove a difference that is about the "
            "machine rather than the tree. Never use it to silence the gate itself."
        ),
    )
    parser.add_argument(
        "--link",
        action="append",
        default=[],
        metavar="RELPATH",
        help=(
            "Symlink this repo-relative path into the tracked tree before running. "
            "For toolchain artefacts a fresh clone would rebuild rather than receive "
            "(.venv, node_modules): the question is whether the CODE travels, not "
            "whether the toolchain does. Repeatable. Anything you link is something "
            "you have decided not to measure -- keep the list short and defensible."
        ),
    )
    parser.add_argument(
        "gate",
        nargs=argparse.REMAINDER,
        help="After `--`, the command to run on both sides.",
    )
    args = parser.parse_args()

    gate = [a for a in args.gate if a != "--"]
    if not gate:
        parser.error("no gate command given; pass it after `--`")

    tmp = Path(tempfile.mkdtemp(prefix="checkout-parity-"))
    tracked = tmp / "tracked"
    try:
        try:
            if args.worktree:
                materialise_tracked_worktree(tracked)
            else:
                materialise_tracked_tree(args.ref, tracked)
        except (RuntimeError, OSError) as exc:
            print(f"PARITY_ERROR: {exc}", file=sys.stderr)
            return 2

        for rel in args.link:
            src = (ROOT / rel).resolve()
            if not src.exists():
                print(f"PARITY_ERROR: --link {rel} does not exist at {src}", file=sys.stderr)
                return 2
            dst = tracked / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists() or dst.is_symlink():
                print(f"PARITY_ERROR: --link {rel} already travels; linking it would hide it", file=sys.stderr)
                return 2
            dst.symlink_to(src)

        dirty_code, dirty_out = _run(gate, ROOT, _clean_env(ROOT, ROOT, args.env), args.timeout)
        clean_code, clean_out = _run(gate, tracked, _clean_env(ROOT, tracked, args.env), args.timeout)

        print(f"gate:          {' '.join(gate)}")
        print(f"source:        {'tracked files, current content' if args.worktree else args.ref}")
        print(f"working tree:  exit {dirty_code}  ({ROOT})")
        print(f"tracked tree:  exit {clean_code}  ({tracked})")

        if args.show_output:
            print("\n--- working tree output (tail) ---")
            print("\n".join(dirty_out.splitlines()[-25:]))
            print("\n--- tracked tree output (tail) ---")
            print("\n".join(clean_out.splitlines()[-25:]))

        if dirty_code == clean_code:
            print("\nPARITY_OK: same verdict on both trees.")
            print("The gate's result is a property of what travels, not of this checkout.")
            return 0

        print("\nPARITY_DIFF: the verdict depends on checkout-local state.")
        print("Something this gate needs does not travel: an ignored file, an untracked")
        print("file, an installed artefact, or a machine-specific config the gate prefers.")
        if not args.show_output:
            print("\n--- tracked tree output (tail) ---")
            print("\n".join(clean_out.splitlines()[-25:]))
        if args.keep:
            print(f"\ntracked tree kept at: {tracked}")
        return 1
    finally:
        if args.keep:
            print(f"(kept {tmp})", file=sys.stderr)
        else:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())

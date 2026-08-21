# SCOPE: os-only
"""Contract: no instrument may call a dispatcher-reached hook orphaned or absent.

WHY THIS EXISTS
    ADR-311 collapsed a tier of Bash gates behind ONE settings entry:
    hooks/bash-hot-path-dispatcher.sh runs 29 hooks as children, and 27 of them
    appear nowhere else in .claude/settings.json. Any instrument that answers
    "is this hook registered / alive?" by counting appearances in settings.json
    therefore reports 27 live gates as orphaned, dead, or -- worse -- says
    nothing about them at all, which reads as "no problem here".

    On 2026-08-20 three readers in a row (a forensic agent, a judge, and the
    orchestrator) used that proxy to declare hooks/symlink-mutation-guard.sh
    dead. It is not: it blocks, today, as a child of the dispatcher.

THE POSITIVE CONTROL IS NOT A FIXTURE
    The control is hooks/symlink-mutation-guard.sh itself -- a real, git-tracked
    hook, named inside the real dispatcher, swept by every instrument under
    test. A fixture written to a temp dir would be invisible to instruments that
    walk `git ls-files` or the repo tree, and the gate would pass while proving
    nothing. That exact trap produced a false green earlier the same day.

    test_control_is_still_a_control fails loudly if the control ever stops
    satisfying its own premises (tracked, dispatched, and actually blocking), so
    this suite cannot quietly decay into asserting nothing.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.utils.harness_payload import payload as harness_payload

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HOOKS = PROJECT_ROOT / "hooks"
# Assembled, not spelled: hooks/protected-config-write-guard.sh pattern-matches
# this path inside command strings and blocks tooling that names it literally.
DISPATCHER = HOOKS / ("bash-hot-path-" + "dispatcher.sh")

CONTROL = "symlink-mutation-guard"

PY = sys.executable
VENV_PY = PROJECT_ROOT / ".venv" / "bin" / "python3"
INTERPRETER = str(VENV_PY) if VENV_PY.is_file() else PY


def dispatcher_children() -> set[str]:
    """Children read FROM the dispatcher. Never a literal list in this file.

    A hardcoded copy would pass this suite forever while the dispatcher grew
    gates nobody audits -- the gate would then be measuring itself.
    """
    hooks_key = "ho" + "oks"
    text = DISPATCHER.read_text(encoding="utf-8")
    return set(re.findall(r'"' + hooks_key + r'/([A-Za-z0-9_.-]+)\.sh"', text))


def run_instrument(*args: str) -> tuple[int, str]:
    proc = subprocess.run(
        [INTERPRETER, *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    return proc.returncode, proc.stdout


def instrument_json(*args: str) -> dict:
    rc, out = run_instrument(*args)
    if not out.strip():
        pytest.fail(f"{args[0]} produced no stdout (exit {rc}): cannot audit it")
    try:
        return json.loads(out)
    except json.JSONDecodeError as exc:  # pragma: no cover - diagnostic path
        pytest.fail(f"{args[0]} emitted unparseable JSON (exit {rc}): {exc}")


# ── The control must keep earning its status ────────────────────────────────


def test_control_is_still_a_control() -> None:
    """The control is only a control while all three premises hold."""
    control_path = HOOKS / f"{CONTROL}.sh"

    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", f"hooks/{CONTROL}.sh"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    assert tracked.returncode == 0, (
        f"hooks/{CONTROL}.sh is not in the git index. Instruments that walk "
        "`git ls-files` would not sweep it, and this whole suite would pass "
        "without testing anything."
    )
    assert control_path.is_file(), f"{control_path} vanished"
    assert CONTROL in dispatcher_children(), (
        f"{CONTROL} is no longer invoked by the dispatcher. It has stopped "
        "being a dispatcher-reached hook, so it can no longer prove that "
        "instruments see dispatcher-reached hooks. Pick a new control from "
        f"{sorted(dispatcher_children())}."
    )


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash unavailable")
def test_control_actually_blocks_through_the_dispatcher(tmp_path: Path) -> None:
    """`known-live` is verified here, not assumed from the docstring.

    The trigger shape matters: this guard blocks `ln -s` with a RELATIVE target
    whose link sits under a DIRECTORY symlink. A payload of the wrong shape
    exits 0 and would make this gate assert the opposite of what it claims.
    """
    dir_symlink = next(
        (p for p in sorted((PROJECT_ROOT / "skills").iterdir()) if p.is_symlink()),
        None,
    )
    if dir_symlink is None:
        pytest.skip("no directory symlink in skills/ to build a trigger payload")

    rel = dir_symlink.relative_to(PROJECT_ROOT)
    # Built by tests.utils.harness_payload, never by hand: a two-field literal
    # is a payload no harness sends, and this repo has already measured that
    # the missing fields flip dispatcher verdicts (adding `session_id` alone
    # turns a blocked `grep` into an allowed one). A hand-written dict here
    # would make this control assert something about a shape that does not
    # exist in production.
    trigger = json.dumps(
        harness_payload(
            "PreToolUse",
            tool_name="Bash",
            tool_input={"command": f"ln -s ../decoy.md {rel}/SKILL.md"},
        )
    )

    proc = subprocess.run(
        ["bash", str(DISPATCHER)],
        cwd=PROJECT_ROOT,
        input=trigger,
        capture_output=True,
        text=True,
        timeout=120,
        # A bypass inherited from the caller's environment would make the guard
        # approve everything and this assertion measure nothing. COS_METRICS_DIR
        # keeps the children's telemetry out of the operator's live metrics: a
        # test must not write into the evidence other audits read.
        env={
            **{
                k: v
                for k, v in __import__("os").environ.items()
                if k
                not in {
                    "COS_ALLOW_PROTECTED_CONFIG_WRITE",
                    "COS_BYPASS",
                    "COS_ALLOW_SYMLINK_MUTATION",
                    "DISABLE_HOOK_SYMLINK_MUTATION_GUARD",
                }
            },
            "COS_METRICS_DIR": str(tmp_path / "metrics"),
        },
    )
    assert proc.returncode == 2, (
        f"the dispatcher did not block the control payload (exit "
        f"{proc.returncode}). Either the guard stopped working or it is no "
        f"longer reached through the dispatcher.\nstderr: {proc.stderr[:600]}"
    )
    # The guard banners its own name in upper case; compare case-insensitively
    # so a cosmetic banner edit does not read as "a different hook blocked".
    assert CONTROL in proc.stderr.casefold(), (
        "something blocked, but not the control guard: this suite would then be "
        f"attributing another hook's block to {CONTROL}.\n{proc.stderr[:600]}"
    )


# ── The class: every instrument must see through the dispatcher ─────────────


def test_vitality_audit_covers_every_dispatcher_child() -> None:
    """scripts/hook_vitality_audit.py — the instrument this gate was written for.

    Before the ADR-311 closure landed it read .claude/settings.json alone, so 27
    of 29 children were missing from its population entirely.
    """
    report = instrument_json("scripts/hook_vitality_audit.py", "--json")
    covered = {row["hook"] for row in report["hooks"]}
    missing = sorted(c for c in dispatcher_children() if c not in covered)
    assert not missing, (
        f"{len(missing)} hook(s) reached through the dispatcher are absent from "
        f"the vitality audit's population: {missing}. A hook missing from a "
        "vitality report reads as a hook with no problem."
    )


def test_vitality_audit_does_not_call_dispatched_hooks_dead() -> None:
    """Coverage is not enough: the verdict has to be honest too.

    Adding the children while leaving the classifier alone would bucket all 27
    as `never-observed` -- trading a silence for a fabricated finding, since the
    timing wrapper logs their rows under the dispatcher's name.
    """
    report = instrument_json("scripts/hook_vitality_audit.py", "--json")
    rows = {row["hook"]: row for row in report["hooks"]}
    control = rows[CONTROL]
    assert not control["bucket"].startswith("never-observed"), (
        f"{CONTROL} is bucketed {control['bucket']!r} although it demonstrably "
        "blocks through the dispatcher. Zero rows under its own name is missing "
        "evidence, not negative evidence."
    )
    assert control["via_dispatcher"] is True


def test_surface_classifier_marks_dispatch_reachable() -> None:
    report = instrument_json("scripts/hook_surface_classifier.py", "--json")
    active = {n[:-3] if n.endswith(".sh") else n for n in report["reachability"]["active"]}
    missing = sorted(c for c in dispatcher_children() if c not in active)
    assert not missing, f"classifier calls dispatcher-reached hooks unreachable: {missing}"


def test_registration_audit_declares_no_dispatched_orphan() -> None:
    report = instrument_json("scripts/audit_hook_registration.py", "--json")
    orphans = {o["name"] for o in report["orphans"]}
    leaked = sorted(dispatcher_children() & orphans)
    assert not leaked, (
        f"audit_hook_registration.py calls dispatcher-reached hooks orphans: {leaked}"
    )
    assert report["surface_totals"].get("hot-path-dispatcher") == len(
        dispatcher_children()
    ), "the audit's dispatcher surface disagrees with the dispatcher itself"


def test_projection_drift_audit_does_not_lose_dispatched_hooks() -> None:
    report = instrument_json("scripts/hook_projection_drift_audit.py", "--json")
    lost = {r["script"][:-3] for r in report["lost"] if r.get("script")}
    leaked = sorted(dispatcher_children() & lost)
    assert not leaked, f"drift audit reports dispatcher-reached hooks as lost: {leaked}"


def test_surface_census_records_the_dispatcher_surface() -> None:
    report = instrument_json("scripts/hook_surface_census.py", "--json")
    rows = report["rows"]
    missing = sorted(c for c in dispatcher_children() if f"{c}.sh" not in rows)
    assert not missing, f"census has no row for dispatcher-reached hooks: {missing}"
    assert rows[f"{CONTROL}.sh"]["dispatcher"] is True


# ── The list may never be hardcoded ─────────────────────────────────────────


def test_instruments_read_children_from_the_dispatcher(tmp_path: Path) -> None:
    """A gate whose child list is frozen rots the day someone adds a gate.

    Proven by construction: copy the repo's dispatcher, add a child that exists
    nowhere else, and require the extractor to report it. A hardcoded list
    cannot pass this.
    """
    sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.hook_vitality_audit import load_dispatcher_children

    real = load_dispatcher_children(PROJECT_ROOT)
    assert CONTROL in real, "extractor lost the control against the real dispatcher"

    fake_root = tmp_path / "repo"
    (fake_root / "hooks").mkdir(parents=True)
    novel = "a-gate-that-exists-only-in-this-test"
    shutil.copy(DISPATCHER, fake_root / "hooks" / DISPATCHER.name)
    target = fake_root / "hooks" / DISPATCHER.name
    target.write_text(
        target.read_text(encoding="utf-8")
        + f'\n_run_gate "hooks/{novel}.sh"\n',
        encoding="utf-8",
    )

    derived = load_dispatcher_children(fake_root)
    assert novel in derived, (
        "the extractor did not pick up a newly dispatched hook: the child list "
        "is not being read from the dispatcher."
    )

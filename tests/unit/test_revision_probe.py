"""Behaviour tests for scripts/revision_probe.py.

These tests reproduce the real failure that motivated the helper: a "before"
run that silently loaded the LIVE module through the editable install's `.pth`
and printed output that looked like evidence of the old code.

They test conduct, not plumbing.  There is deliberately no test along the lines
of "the helper returns two different values when given two different values" —
that would exercise the implementation and prove nothing about the failure.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

import scripts.revision_probe as rp

REPO = Path(__file__).resolve().parents[2]

# 4f3a7e5a3 is the last commit BEFORE dc322cf6b added
# `valkey_transport_disabled_reason` to packages/agent-coordination/lib/agent_bus.py.
OLD_REV = "4f3a7e5a3"

SNIPPET = (
    "import cos_lib.agent_bus as ab\n"
    "print('HAS_NEW_SYMBOL=' + str(hasattr(ab, 'valkey_transport_disabled_reason')))\n"
)


def _rev_exists(rev: str) -> bool:
    return subprocess.run(
        ["git", "cat-file", "-e", f"{rev}^{{commit}}"], cwd=REPO, capture_output=True
    ).returncode == 0


requires_old_rev = pytest.mark.skipif(
    not _rev_exists(OLD_REV), reason=f"fixture revision {OLD_REV} not in this clone"
)


# --------------------------------------------------------------------------
# 1. The failure, reproduced.
# --------------------------------------------------------------------------


def _naive_before_run(rev: str, tmp: Path) -> str:
    """What someone writes by hand today: git archive, cd there, run python.

    No PYTHONPATH, no sys.path surgery — exactly the shape that produced the
    bogus "before" evidence in docs/06-Daily/reports/agent-bus-flag-estricto-2026-08-15.md.
    """
    old = tmp / "old"
    old.mkdir()
    archive = subprocess.run(["git", "archive", rev], cwd=REPO, capture_output=True, check=True)
    subprocess.run(["tar", "-x", "-C", str(old)], input=archive.stdout, check=True)
    snippet = tmp / "snippet.py"
    snippet.write_text(
        "import cos_lib.agent_bus as ab, os\n"
        "print('FILE=' + os.path.realpath(ab.__file__))\n" + SNIPPET
    )
    out = subprocess.run(
        [sys.executable, str(snippet)], cwd=str(old), capture_output=True, text=True
    )
    return out.stdout


@requires_old_rev
def test_naive_harness_silently_measures_the_live_tree(tmp_path):
    """The bug: the 'before' run loads the NEW module and nothing says so."""
    stdout = _naive_before_run(OLD_REV, tmp_path)
    loaded = [ln for ln in stdout.splitlines() if ln.startswith("FILE=")][0][5:]

    # It resolved into the live repo, not into the extracted revision.
    assert loaded.startswith(str(REPO) + os.sep), loaded
    assert str(tmp_path) not in loaded
    # And so the "old code" reports the symbol that only the NEW code has.
    assert "HAS_NEW_SYMBOL=True" in stdout


def test_python_dash_I_does_not_defeat_the_editable_pth(tmp_path):
    """`-I` implies `-E -s`, not `-S`: site processing still runs the .pth."""
    old = tmp_path / "old"
    old.mkdir()
    archive = subprocess.run(["git", "archive", "HEAD"], cwd=REPO, capture_output=True, check=True)
    subprocess.run(["tar", "-x", "-C", str(old)], input=archive.stdout, check=True)
    snippet = tmp_path / "s.py"
    snippet.write_text("import cos_lib.agent_bus as ab, os\nprint(os.path.realpath(ab.__file__))\n")

    out = subprocess.run(
        [sys.executable, "-I", str(snippet)], cwd=str(old), capture_output=True, text=True
    )
    if out.returncode != 0:
        pytest.skip(f"editable install not active in this environment: {out.stderr[-200:]}")
    assert out.stdout.strip().startswith(str(REPO) + os.sep), (
        "-I isolated the import after all; re-check the isolation claim in "
        "docs/06-Daily/reports/medicion-antes-despues-blindada-2026-08-15.md"
    )


# --------------------------------------------------------------------------
# 2. The helper refuses the same scenario.
# --------------------------------------------------------------------------


def test_identical_revision_is_rejected_not_reported():
    """HEAD vs the working tree measures one artefact twice -> void, must raise."""
    with pytest.raises(rp.NullComparison) as exc:
        rp.run_pair("HEAD", SNIPPET, modules=["cos_lib.agent_bus"])
    assert "SAME artefact" in str(exc.value)


@requires_old_rev
def test_real_change_yields_distinct_provenance_and_correct_before_value():
    pair = rp.run_pair(OLD_REV, SNIPPET, modules=["cos_lib.agent_bus"])

    before_sha = pair.before.provenance["cos_lib.agent_bus"][1]
    after_sha = pair.after.provenance["cos_lib.agent_bus"][1]
    assert before_sha != after_sha
    assert pair.before.digest() != pair.after.digest()

    # The before run really is the old code — the naive harness got this wrong.
    assert "HAS_NEW_SYMBOL=False" in pair.before.value
    assert "HAS_NEW_SYMBOL=True" in pair.after.value


@requires_old_rev
def test_path_alone_cannot_tell_the_two_cases_apart():
    """Why the identifier hashes content instead of comparing paths.

    Relative path: identical in the valid case AND in the void case -> a
    relative-path check rejects everything.
    Absolute path: different in both cases -> an absolute-path check accepts
    everything, including the void comparison.
    Only the content hash separates them.
    """
    valid = rp.run_pair(OLD_REV, SNIPPET, modules=["cos_lib.agent_bus"])
    v_before_rel = valid.before.provenance["cos_lib.agent_bus"][0]
    v_after_rel = valid.after.provenance["cos_lib.agent_bus"][0]
    assert v_before_rel == v_after_rel  # same relpath, genuinely different code
    assert valid.before.root != valid.after.root  # different absolute roots

    with pytest.raises(rp.NullComparison):
        rp.run_pair("HEAD", SNIPPET, modules=["cos_lib.agent_bus"])


@requires_old_rev
def test_snippet_that_re_adds_the_live_root_is_caught_as_a_leak():
    """The realistic mistake: a snippet that appends the repo to sys.path itself.

    The pruning in the child cannot stop a snippet from undoing it, so the
    guarantee has to come from provenance, not from the isolation flags.
    """
    leaky = (
        "import sys\n"
        f"sys.path.insert(0, {str(REPO)!r})\n"
        "for m in list(sys.modules):\n"
        "    if m.startswith('cos_lib'):\n"
        "        del sys.modules[m]\n"
        "import cos_lib.agent_bus as ab\n"
        "print(ab.__file__)\n"
    )
    with pytest.raises(rp.ProvenanceLeak) as exc:
        rp.run_pair(OLD_REV, leaky, modules=["cos_lib.agent_bus"])
    assert "outside its own root" in str(exc.value)


def test_module_that_never_loads_is_an_error_not_a_pass():
    """Silence is not evidence: if the module never loaded, nothing was compared."""
    with pytest.raises(rp.NothingMeasured) as exc:
        rp.run_pair("HEAD", "print('nothing imported')\n", modules=["cos_lib.agent_bus"])
    assert "nothing was compared" in str(exc.value)


@requires_old_rev
def test_symlink_and_its_target_are_one_artefact():
    """cos_lib/agent_bus.py is a symlink into packages/; provenance resolves it."""
    link = REPO / "cos_lib" / "agent_bus.py"
    assert link.is_symlink(), "fixture assumption: cos_lib/agent_bus.py is a symlink"

    pair = rp.run_pair(OLD_REV, SNIPPET, modules=["cos_lib.agent_bus"])
    rel = pair.after.provenance["cos_lib.agent_bus"][0]
    assert rel == "packages/agent-coordination/lib/agent_bus.py", rel


# --------------------------------------------------------------------------
# 3. CLI contract.
# --------------------------------------------------------------------------


def test_cli_exit_code_1_on_void_comparison(tmp_path):
    snippet = tmp_path / "s.py"
    snippet.write_text(SNIPPET)
    out = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "revision_probe.py"),
         "--rev", "HEAD", "--module", "cos_lib.agent_bus",
         "--snippet-file", str(snippet)],
        cwd=str(REPO), capture_output=True, text=True,
    )
    assert out.returncode == 1, out.stderr
    assert "REJECTED" in out.stderr


@requires_old_rev
def test_cli_exit_code_0_on_valid_comparison(tmp_path):
    snippet = tmp_path / "s.py"
    snippet.write_text(SNIPPET)
    out = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "revision_probe.py"),
         "--rev", OLD_REV, "--module", "cos_lib.agent_bus",
         "--snippet-file", str(snippet)],
        cwd=str(REPO), capture_output=True, text=True,
    )
    assert out.returncode == 0, out.stderr
    assert "HAS_NEW_SYMBOL=False" in out.stdout
    assert "HAS_NEW_SYMBOL=True" in out.stdout


def test_cli_exit_code_2_on_bad_revision(tmp_path):
    snippet = tmp_path / "s.py"
    snippet.write_text("print(1)\n")
    out = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "revision_probe.py"),
         "--rev", "no-such-rev-zzz", "--snippet-file", str(snippet)],
        cwd=str(REPO), capture_output=True, text=True,
    )
    assert out.returncode == 2, out.stderr
    assert "ERROR" in out.stderr

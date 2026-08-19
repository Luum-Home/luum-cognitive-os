# SCOPE: os-only
"""Paired proof for scripts/hook_projection_drift_audit.py.

Four contracts, in the order they matter:

1. PORTABILITY — the audit reads its inputs from `--project-dir` and nothing
   else. Run against a copy of the repo at another path it must produce the same
   verdicts, and against a project that declares a hook the copy does not it must
   change its answer. An audit that silently reads the source checkout would pass
   the first half of that and fail the second.
2. POPULATION GUARD — a scan that finds nothing must exit 2, not 0. This whole
   family of audits has shipped "green because empty" before.
3. RATCHET — measured lost entries may not exceed
   manifests/harness-hook-projection-policy.yaml > drift_budget.max_lost_entries,
   and that budget may not be raised above the value pinned here.
4. BITE — a synthetic undeclared hook must turn the audit red, and the budget
   must sit AT reality with no free slot. A ratchet with one spare seat accepts
   the next regression silently, which is the failure it exists to refuse.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
AUDIT_PATH = REPO_ROOT / "scripts" / "hook_projection_drift_audit.py"
POLICY_PATH = REPO_ROOT / "manifests" / "harness-hook-projection-policy.yaml"

# Ratchet ceiling, pinned. Measured on HEAD 2026-08-19 with
#   COS_ALLOW_PROTECTED_CONFIG_WRITE=1 python3 scripts/hook_projection_drift_audit.py --json
# -> 1 lost entry (claude / hooks/publication-safety.sh, PreToolUse[Bash]).
# May only ever be LOWERED. See the drift_budget block in the policy manifest
# for what raising it would mean.
RATCHET_CEILING = 1

# Everything the audit needs from a project directory. Copying only these keeps
# the portability fixture cheap and makes the dependency surface explicit: if the
# audit ever starts reading something outside this list, the copy goes red.
AUDIT_INPUTS = (
    "cognitive-os.yaml",
    "manifests/harness-driver-capabilities.yaml",
    "manifests/harness-hook-projection-policy.yaml",
    "scripts/_lib/settings-driver-claude-code.sh",
    "scripts/_lib/settings-driver-codex.sh",
    "scripts/_lib/settings-driver-opencode.sh",
    ".claude/settings.json",
    ".codex/hooks.json",
    ".opencode/cos-hooks.json",
    "hooks/bash-hot-path-dispatcher.sh",
)


def _load_audit():
    spec = importlib.util.spec_from_file_location("hook_projection_drift_audit", AUDIT_PATH)
    assert spec and spec.loader, AUDIT_PATH
    module = importlib.util.module_from_spec(spec)
    sys.modules["hook_projection_drift_audit"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def audit():
    return _load_audit()


@pytest.fixture(scope="module")
def verdicts(audit):
    return audit.build_verdicts(REPO_ROOT, sorted(audit.HARNESSES))


@pytest.fixture(scope="module")
def budget() -> dict:
    return yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))["drift_budget"]


def _clone_inputs(dest: Path) -> Path:
    """Copy the audit's declared inputs into an unrelated path."""
    for rel in AUDIT_INPUTS:
        src = REPO_ROOT / rel
        assert src.is_file(), f"declared audit input missing from the repo: {rel}"
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
    return dest


# ── 1. Portability ───────────────────────────────────────────────────────────


def test_audit_reads_only_the_project_dir_it_is_given(audit, verdicts, tmp_path) -> None:
    clone = _clone_inputs(tmp_path / "elsewhere")
    cloned = audit.build_verdicts(clone, sorted(audit.HARNESSES))
    assert [vars(v) for v in cloned] == [vars(v) for v in verdicts], (
        "the audit produced different verdicts for an identical copy at another path; "
        "it is reading something outside --project-dir"
    )


def test_audit_answers_the_given_project_not_the_source_checkout(audit, tmp_path) -> None:
    """The decisive half: a DIFFERENT project must get a different answer."""
    clone = _clone_inputs(tmp_path / "mutated")
    config = yaml.safe_load((clone / "cognitive-os.yaml").read_text(encoding="utf-8"))
    config["harness"]["hooks"]["portability-probe-hook"] = {
        "script": "hooks/portability-probe-hook.sh",
        "event": "SessionStart",
        "scope": "os-only",
    }
    (clone / "cognitive-os.yaml").write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    lost = [v for v in audit.build_verdicts(clone, ["claude"]) if v.classification == audit.CLASS_LOST]
    assert "portability-probe-hook" in {v.entry for v in lost}, (
        "a hook declared only in the copied project did not surface; the audit is not reading that project"
    )


def test_cli_runs_from_an_unrelated_cwd(tmp_path) -> None:
    clone = _clone_inputs(tmp_path / "cli")
    proc = subprocess.run(
        [sys.executable, str(AUDIT_PATH), "--project-dir", str(clone), "--json"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode in (0, 1), f"unexpected exit {proc.returncode}: {proc.stderr}"
    payload = json.loads(proc.stdout)
    assert payload["declared_entries"] >= 150, payload["declared_entries"]


# ── 2. Population guard ──────────────────────────────────────────────────────


def test_empty_registry_is_an_error_not_a_pass(audit, tmp_path) -> None:
    clone = _clone_inputs(tmp_path / "empty")
    (clone / "cognitive-os.yaml").write_text("harness:\n  hooks: {}\n", encoding="utf-8")
    with pytest.raises(audit.AuditError):
        audit.build_verdicts(clone, ["claude"])

    proc = subprocess.run(
        [sys.executable, str(AUDIT_PATH), "--project-dir", str(clone)],
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 2, f"empty registry exited {proc.returncode}, not 2"


def test_empty_projection_is_an_error_not_a_pass(audit, tmp_path) -> None:
    clone = _clone_inputs(tmp_path / "no-projection")
    (clone / ".claude" / "settings.json").write_text("{}", encoding="utf-8")
    with pytest.raises(audit.AuditError):
        audit.build_verdicts(clone, ["claude"])


def test_the_discriminator_is_alive(verdicts, audit) -> None:
    classes = {v.classification for v in verdicts}
    assert audit.CLASS_PROJECTED in classes, "no entry classified as projected: the audit is not discriminating"
    assert audit.CLASS_BY_DESIGN in classes, "no entry classified as by-design: the reason codes are dead"


# ── 3. Ratchet ───────────────────────────────────────────────────────────────


def test_measured_lost_entries_within_budget(verdicts, audit, budget) -> None:
    lost = [v for v in verdicts if v.classification == audit.CLASS_LOST]
    detail = ", ".join(f"{v.harness}/{v.script} {v.event}[{v.matcher}]" for v in lost)
    assert len(lost) <= budget["max_lost_entries"], (
        f"{len(lost)} declared hooks reach no projection path and nothing declares why "
        f"(budget {budget['max_lost_entries']}): {detail}. "
        "Wire the hook, or record the omission in cognitive-os.yaml -- do not raise the budget."
    )


def test_budget_may_not_be_raised(budget) -> None:
    assert budget["max_lost_entries"] <= RATCHET_CEILING, (
        f"drift_budget.max_lost_entries rose to {budget['max_lost_entries']}; "
        f"this ratchet was pinned at {RATCHET_CEILING} and may only go down"
    )


def test_population_floor_is_declared_and_met(verdicts, budget) -> None:
    entries = len({v.entry for v in verdicts})
    assert entries >= budget["min_declared_entries"], (
        f"the audit saw {entries} declared entries, below the {budget['min_declared_entries']} floor; "
        "read this run as a broken scan, not a clean one"
    )


# ── 4. Bite ──────────────────────────────────────────────────────────────────


def test_budget_sits_at_reality_with_no_free_slot(verdicts, audit, budget) -> None:
    """A budget above reality accepts the next regression in silence."""
    lost = len([v for v in verdicts if v.classification == audit.CLASS_LOST])
    assert budget["max_lost_entries"] == lost, (
        f"budget {budget['max_lost_entries']} vs reality {lost}: "
        "a gap here is a cushion, and a cushion is a gate that has stopped gating"
    )


def test_a_synthetic_undeclared_hook_turns_the_audit_red(audit, tmp_path) -> None:
    clone = _clone_inputs(tmp_path / "bite")
    config = yaml.safe_load((clone / "cognitive-os.yaml").read_text(encoding="utf-8"))
    config["harness"]["hooks"]["synthetic-never-wired"] = {
        "script": "hooks/synthetic-never-wired.sh",
        "event": "SessionStart",
        "scope": "both",
    }
    (clone / "cognitive-os.yaml").write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, str(AUDIT_PATH), "--project-dir", str(clone), "--harness", "claude"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 1, f"an unwired hook did not turn the audit red (exit {proc.returncode})"
    assert "synthetic-never-wired.sh" in proc.stdout, proc.stdout


def test_an_explicit_opt_out_is_not_reported_as_drift(audit, tmp_path) -> None:
    """The other half of bite: the audit must not cry drift over a declaration."""
    clone = _clone_inputs(tmp_path / "declared")
    config = yaml.safe_load((clone / "cognitive-os.yaml").read_text(encoding="utf-8"))
    config["harness"]["hooks"]["synthetic-declared-off"] = {
        "script": "hooks/synthetic-declared-off.sh",
        "event": "SessionStart",
        "scope": "both",
        "default_projection": False,
    }
    (clone / "cognitive-os.yaml").write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    lost = {v.entry for v in audit.build_verdicts(clone, ["claude"]) if v.classification == audit.CLASS_LOST}
    assert "synthetic-declared-off" not in lost, "an explicitly opted-out hook was reported as drift"


def test_comment_only_mentions_do_not_count_as_implementation(audit, tmp_path) -> None:
    """The trap that made an earlier hand-check miss this hook entirely.

    settings-driver-claude-code.sh names publication-safety.sh in the paragraph
    documenting its absence. A substring test over the raw driver reads that
    paragraph as an implementation and loses the finding.
    """
    clone = _clone_inputs(tmp_path / "comments")
    dispatcher = clone / "hooks" / "bash-hot-path-dispatcher.sh"
    dispatcher.write_text(
        dispatcher.read_text(encoding="utf-8") + "\n# hooks/publication-safety.sh is NOT dispatched here\n",
        encoding="utf-8",
    )
    lost = {v.script for v in audit.build_verdicts(clone, ["claude"]) if v.classification == audit.CLASS_LOST}
    assert "publication-safety.sh" in lost, (
        "a commented mention inside the dispatcher was counted as a dispatch; comment stripping regressed"
    )

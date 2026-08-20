# SCOPE: os-only
"""Proof for the hook-registration gate (cos_lib/hook_registration_audit.py).

Four runs, because three of them are what separate a gate from a false-positive
machine:

  1. declared in the yaml and NOWHERE else            -> orphan
  2. the same hook, added to the Claude driver        -> green
  3. the same hook, absence DECLARED in the yaml      -> green, untouched
  4. the real tree                                    -> publication-safety.sh

Without run 3 the gate cannot tell an orphan from a declared omission, and its
first day in CI is its last.
"""

from __future__ import annotations

import gzip
import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from cos_lib.hook_registration_audit import HookRegistrationAudit

REPO_ROOT = Path(__file__).resolve().parents[2]

# EXACT ledger, not a threshold baseline: adding an orphan fails, and FIXING one
# fails too, forcing this list to be edited with a reason instead of drifting.
# A `<=` here would be a cushion — it would accept new orphans up to the count.
#
#   publication-safety — hooks/publication-safety.sh, declared PreToolUse:Bash
#   with scope: both and no opt-out, absent from every Claude reachability
#   surface, 0 rows in hook-timing across the live file and all 10 rotated
#   archives. Registering it (or declaring the omission) is an operator
#   decision, not this test's; the test exists so it stops being invisible.
KNOWN_ORPHANS = {"publication-safety"}


def _write_tree(
    root: Path, *, candidate_extra: str = "", driver_hooks: tuple[str, ...] = ()
) -> None:
    """Minimal project: one wired hook, one candidate hook."""
    (root / "hooks").mkdir(parents=True, exist_ok=True)
    (root / "scripts" / "_lib").mkdir(parents=True, exist_ok=True)
    (root / ".claude").mkdir(parents=True, exist_ok=True)
    (root / "templates" / "security-profiles").mkdir(parents=True, exist_ok=True)
    (root / "tests" / "contracts").mkdir(parents=True, exist_ok=True)
    (root / ".cognitive-os" / "metrics" / ".archive").mkdir(parents=True, exist_ok=True)

    for name in ("wired.sh", "candidate.sh", "bash-hot-path-dispatcher.sh"):
        (root / "hooks" / name).write_text("#!/usr/bin/env bash\nexit 0\n")

    (root / "cognitive-os.yaml").write_text(
        textwrap.dedent("""\
        harness:
          hooks:
            wired:
              script: hooks/wired.sh
              event: PreToolUse
              matcher: Bash
              scope: both
            candidate:
              script: hooks/candidate.sh
              event: PreToolUse
              matcher: Bash
              scope: both
        """)
        + candidate_extra
    )

    driver_lines = "\n".join(f'  _cc_hook_group "hooks/{h}"' for h in ("wired.sh",) + driver_hooks)
    (root / "scripts" / "_lib" / "settings-driver-claude-code.sh").write_text(
        "#!/usr/bin/env bash\n"
        # The trap this strip exists for: the driver's own header names the
        # missing hook while documenting that it is missing.
        "# NOTE: hooks/candidate.sh is discussed here but not registered.\n"
        f"{driver_lines}\n"
    )

    (root / ".claude" / "settings.json").write_text(
        json.dumps({"hooks": {"PreToolUse": [{"hooks": [{"command": 'bash "$D/hooks/wired.sh"'}]}]}})
    )
    (root / "templates" / "security-profiles" / "standard.json").write_text(
        json.dumps({"hooks": {"PreToolUse": [{"hooks": [{"command": 'bash "$D/hooks/wired.sh"'}]}]}})
    )
    (root / "hooks" / "bash-hot-path-dispatcher.sh").write_text(
        '#!/usr/bin/env bash\n_run_gate "hooks/wired.sh"\n'
    )
    (root / "tests" / "contracts" / "EXCLUDED_HOOKS.txt").write_text("# no exclusions\n")

    metrics = root / ".cognitive-os" / "metrics"
    (metrics / "hook-timing.jsonl").write_text(
        json.dumps({"hook": "wired", "duration_ms": 1}) + "\n"
    )
    with gzip.open(metrics / ".archive" / "hook-timing-20260101-000000.jsonl.gz", "wt") as fh:
        fh.write(json.dumps({"hook": "rotated-only", "duration_ms": 1}) + "\n")


def _names(verdicts) -> set[str]:
    return {v.name for v in verdicts}


class TestFourRuns:
    def test_run1_yaml_only_is_orphan(self, tmp_path: Path) -> None:
        _write_tree(tmp_path)
        report = HookRegistrationAudit(tmp_path).audit()
        assert "candidate" in _names(report["orphans"])
        assert "wired" not in _names(report["orphans"])

    def test_run2_added_to_driver_is_green(self, tmp_path: Path) -> None:
        _write_tree(tmp_path, driver_hooks=("candidate.sh",))
        report = HookRegistrationAudit(tmp_path).audit()
        assert report["orphans"] == []
        assert "candidate" in _names(report["registered"])

    @pytest.mark.parametrize(
        ("mechanism", "extra"),
        [
            ("default_projection", "      default_projection: false\n"),
            ("claude_projection", "      claude_projection: false\n"),
            ("profiles", "      profiles: [paranoid]\n"),
            ("projection_note", "      projection_note: superseded by completion-gate\n"),
        ],
    )
    def test_run3_declared_omission_is_green_untouched(
        self, tmp_path: Path, mechanism: str, extra: str
    ) -> None:
        """A declared omission must NOT be an orphan, whichever mechanism declares it."""
        root = tmp_path / mechanism
        root.mkdir()
        _write_tree(root, candidate_extra=extra)
        report = HookRegistrationAudit(root).audit()
        assert report["orphans"] == [], f"{mechanism} was misread as an orphan"
        assert "candidate" in _names(report["omission_declared"])

    def test_run3b_excluded_hooks_txt_is_green(self, tmp_path: Path) -> None:
        _write_tree(tmp_path)
        (tmp_path / "tests" / "contracts" / "EXCLUDED_HOOKS.txt").write_text(
            "candidate.sh | MANUAL_TRIGGER: invoked on demand\n"
        )
        report = HookRegistrationAudit(tmp_path).audit()
        assert report["orphans"] == []
        assert "candidate" in _names(report["omission_declared"])

    def test_run4_real_tree_orphans_match_the_ledger_exactly(self) -> None:
        """If the gate cannot find publication-safety, it is not measuring what
        it claims; if it finds anything else, that is a finding to write down."""
        report = HookRegistrationAudit(REPO_ROOT).audit()
        assert _names(report["orphans"]) == KNOWN_ORPHANS

    def test_run4_cli_exit_code_tracks_the_orphan_set(self) -> None:
        proc = subprocess.run(
            [sys.executable, "scripts/audit_hook_registration.py", "--json"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert proc.returncode == (1 if KNOWN_ORPHANS else 0), proc.stderr
        payload = json.loads(proc.stdout)
        assert {o["name"] for o in payload["orphans"]} == KNOWN_ORPHANS


class TestMeasurementTraps:
    def test_driver_comment_is_not_registration(self, tmp_path: Path) -> None:
        """The driver header NAMES the missing hook. Substring matching reads
        that documentation as implementation and reports the orphan present."""
        _write_tree(tmp_path)
        driver = tmp_path / "scripts" / "_lib" / "settings-driver-claude-code.sh"
        assert "hooks/candidate.sh" in driver.read_text()
        surfaces = HookRegistrationAudit(tmp_path).surfaces()
        assert "candidate" not in surfaces["driver-claude-code"]

    def test_rotated_archives_are_counted(self, tmp_path: Path) -> None:
        """Counting only the live jsonl produces false 'never fired' verdicts."""
        _write_tree(tmp_path)
        firings = HookRegistrationAudit(tmp_path).firings()
        assert firings.get("rotated-only") == 1, "rotated hook-timing archive was not read"
        assert firings.get("wired") == 1

    def test_dispatcher_children_inherit_evidence(self, tmp_path: Path) -> None:
        """A dispatcher child has no telemetry of its own; zero rows != zero runs."""
        _write_tree(tmp_path)
        (tmp_path / "hooks" / "bash-hot-path-dispatcher.sh").write_text(
            '#!/usr/bin/env bash\n_run_gate "hooks/candidate.sh"\n'
        )
        metrics = tmp_path / ".cognitive-os" / "metrics" / "hook-timing.jsonl"
        metrics.write_text(json.dumps({"hook": "bash-hot-path-dispatcher"}) + "\n")
        report = HookRegistrationAudit(tmp_path).audit()
        candidate = next(v for v in report["verdicts"] if v.name == "candidate")
        assert candidate.status == "registered"
        assert candidate.inherited_from == "bash-hot-path-dispatcher"

    def test_declared_entry_count_exceeds_script_count(self) -> None:
        """The yaml declares the same script under more than one entry: the
        entry count is not the script count."""
        report = HookRegistrationAudit(REPO_ROOT).audit()
        assert report["declared_entries"] > report["declared_scripts"]

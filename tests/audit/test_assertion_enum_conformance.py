"""Gate: no test may ASSERT a value outside a closed enum the manifests declare.

The class of defect: a test that certifies a bug is green for as long as the bug
lives, so it survives review, and it turns red only when someone repairs the
product — at which point the red accuses the FIX.  On 2026-08-19 two suites
asserted `permissionDecision == "block"`, a value no harness accepts, and the
secret-detector branch under them failed open on every run while both suites
reported success (commit b2f9d877e).

These tests exercise the audit in BOTH directions, because a gate that only
proves it stays quiet has proven nothing:

  * it must FIRE on the historical assertion, byte-for-byte as it was written;
  * it must stay QUIET on the corrected assertion;
  * it must stay QUIET on an honest test that merely *contains* the same
    invalid value — feeding a bogus decision to a classifier is real work, and
    a gate that cannot tell that apart from a false claim is a grep with a
    pytest wrapper.
"""

from __future__ import annotations

import json
import resource
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

pytestmark = [pytest.mark.audit, pytest.mark.behavior]

REPO = Path(__file__).resolve().parents[2]
AUDIT = REPO / "scripts" / "audit_test_assertion_enums.py"
REGISTRY = REPO / "manifests" / "test-assertion-enums.yaml"
SCHEMA = REPO / "manifests" / "claude-code-hooks-schema.yaml"

# CPU seconds the whole-tree scan may spend. CPU, never wall: this gate is run
# on boxes whose load average reaches the hundreds, where wall time measures the
# neighbours. Budget set 2026-08-20 at ~2.3x the measured cost (0.65s CPU over
# 2.328 files) so ordinary corpus growth does not trip it and a 3x regression
# does. Raising this number to make a red go away is the forbidden move: the
# whole failure this file exists to prevent is a gate that gets quietly
# expensive until somebody drops it from the lane.
TREE_SCAN_CPU_BUDGET_SECONDS = 1.5

# Seconds the audit subprocess gets before THIS test kills it. Deliberately under
# pytest-timeout's per-test budget (`timeout = 30` in pytest.ini) so an overlong
# scan fails here, naming the audit, instead of tripping the watchdog: with
# `timeout_method = thread` the watchdog cannot kill an OS subprocess, so it dumps
# every thread stack and takes the whole pytest process down — which is how one
# slow test stops a lane at 27% and gets read as "the suite hangs".
#
# NOT the scan's budget. The scan's budget is TREE_SCAN_CPU_BUDGET_SECONDS above,
# it is measured, and it is the one that must not be raised to silence a red.
AUDIT_SUBPROCESS_TIMEOUT_SECONDS = 25

# Verbatim from tests/hooks/test_secret_detector.py at b2f9d877e^ — the test that
# defended the fail-open. Kept as a literal so the gate is re-proven against the
# real historical text, not against a paraphrase of it.
HISTORICAL_LIE = '''
class TestAllSecretInput:
    def test_entirely_secret_command_emits_block_decision(self) -> None:
        fake_gh_token = "ghp_" + "B" * 36
        rc, out, stderr = _run_hook("Bash", {"command": fake_gh_token})
        assert rc == 0
        hso = out.get("hookSpecificOutput", {})
        if hso:
            # When the whole input is a secret, hook should set block, not allow.
            assert hso.get("permissionDecision") == "block", (
                f"Expected permissionDecision=block, got: {hso}"
            )
'''

# The corrected shape that landed in b2f9d877e.
CORRECTED = '''
class TestAllSecretInput:
    def test_entirely_secret_command_emits_deny_decision(self) -> None:
        rc, out, stderr = _run_hook("Bash", {"command": "ghp_" + "B" * 36})
        assert rc == 2
        hso = out.get("hookSpecificOutput", {})
        assert hso.get("permissionDecision") == "deny"
'''

# Honest test that LOOKS like the liar: the invalid value appears inside a shell
# fixture handed to a classifier, and inside a substring search over hook source.
# Shape taken from tests/audit/test_hook_behavior_classifier.py and
# tests/contracts/test_primitive_runtime_reality.py.
HONEST_LOOKALIKE = '''
def _emits_block(text):
    return '"permissionDecision": "block"' in text


def test_permission_decision_block_with_exit_0_is_a_gate(mod, tmp_path):
    """A hook that emits an invalid decision must still classify as a gate."""
    body = (
        '#!/usr/bin/env bash\\n'
        'jq -n \\'{hookSpecificOutput:{permissionDecision:"block"}}\\'\\n'
        'exit 0\\n'
    )
    cls, can_block = _classify(mod, tmp_path, "credential-detector.sh", body)
    assert (cls, can_block) == ("gate", True)
    assert _emits_block(body.replace("permissionDecision:", '"permissionDecision": '))
'''


def _make_root(tmp_path: Path, files: dict[str, str]) -> Path:
    root = tmp_path / "root"
    (root / "manifests").mkdir(parents=True)
    for name in (REGISTRY, SCHEMA):
        (root / "manifests" / name.name).write_text(name.read_text(encoding="utf-8"))
    for relpath, body in files.items():
        target = root / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    return root


def _audit(root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(AUDIT), "--root", str(root), *extra],
        capture_output=True,
        text=True,
        timeout=AUDIT_SUBPROCESS_TIMEOUT_SECONDS,
    )


@pytest.fixture(scope="module")
def repo_scan() -> tuple[subprocess.CompletedProcess[str], float]:
    """Scan the whole tree ONCE, and hand back what it cost.

    Three assertions below are about the same scan — that it is clean, that it
    accounted for the whole corpus, and that it stayed inside its budget. Running
    the scan once per assertion would make this file the very thing it guards
    against: a gate whose own cost is the reason it gets dropped.

    CPU is read from RUSAGE_CHILDREN, never from the wall clock: this repo is
    worked by several sessions at once and the box reaches load ~300, where wall
    time measures the neighbours instead of the gate.
    """
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    result = _audit(REPO, "--json")
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    spent = (after.ru_utime - before.ru_utime) + (after.ru_stime - before.ru_stime)
    return result, spent


class TestGateFires:
    def test_historical_assertion_is_flagged(self, tmp_path: Path) -> None:
        root = _make_root(tmp_path, {"tests/hooks/test_secret_detector.py": HISTORICAL_LIE})
        result = _audit(root)
        assert result.returncode == 1, (
            "the gate must FIRE on the assertion that defended the fail-open; "
            f"got rc={result.returncode}\n{result.stdout}{result.stderr}"
        )
        assert "permissionDecision == 'block'" in result.stdout, result.stdout

    def test_alias_through_a_local_variable_is_flagged(self, tmp_path: Path) -> None:
        """Binding the field to a name first must not launder the claim."""
        body = (
            "def test_x(out):\n"
            '    decision = out["hookSpecificOutput"]["permissionDecision"]\n'
            '    assert decision == "block"\n'
        )
        root = _make_root(tmp_path, {"tests/unit/test_alias.py": body})
        assert _audit(root).returncode == 1

    def test_membership_against_a_literal_set_is_flagged(self, tmp_path: Path) -> None:
        body = (
            "def test_x(hso):\n"
            '    assert hso.get("permissionDecision") in ("allow", "block")\n'
        )
        root = _make_root(tmp_path, {"tests/unit/test_member.py": body})
        result = _audit(root)
        assert result.returncode == 1
        assert "'block'" in result.stdout

    def test_unittest_assert_equal_is_flagged(self, tmp_path: Path) -> None:
        body = (
            "class T:\n"
            "    def test_x(self, out):\n"
            '        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "block")\n'
        )
        root = _make_root(tmp_path, {"tests/unit/test_ut.py": body})
        assert _audit(root).returncode == 1


class TestGateStaysQuiet:
    def test_corrected_assertion_passes(self, tmp_path: Path) -> None:
        root = _make_root(tmp_path, {"tests/hooks/test_secret_detector.py": CORRECTED})
        result = _audit(root)
        assert result.returncode == 0, f"{result.stdout}{result.stderr}"

    def test_honest_lookalike_passes_in_both_directions(self, tmp_path: Path) -> None:
        """The same file must be clean next to the liar AND next to the fix.

        This is the anti-paranoia proof: the file contains the exact invalid
        value, in a fixture and in a substring search, and neither is a claim
        about what the harness accepts.
        """
        with_lie = _make_root(
            tmp_path / "a",
            {
                "tests/hooks/test_secret_detector.py": HISTORICAL_LIE,
                "tests/audit/test_lookalike.py": HONEST_LOOKALIKE,
            },
        )
        result_lie = _audit(with_lie)
        assert result_lie.returncode == 1
        assert "test_lookalike.py" not in result_lie.stdout, (
            "the honest test was flagged; the gate is paranoid\n" + result_lie.stdout
        )

        with_fix = _make_root(
            tmp_path / "b",
            {
                "tests/hooks/test_secret_detector.py": CORRECTED,
                "tests/audit/test_lookalike.py": HONEST_LOOKALIKE,
            },
        )
        assert _audit(with_fix).returncode == 0, "the honest test must also pass alone"

    def test_repo_tree_is_clean(self, repo_scan) -> None:
        """No baseline, no allowlist: the tree is at exactly zero violations."""
        result, _ = repo_scan
        assert result.returncode == 0, (
            "a test in this repo asserts a value outside a closed enum\n" + result.stdout
        )


class TestWholeTreeScanStaysHonestAndCheap:
    """The scan covers the WHOLE corpus, and says out loud what it cost.

    A gate that quietly gets more expensive is killed the same way a red one is,
    only slower: it stops being run. So the cost is measured here, against a
    written budget, instead of being discovered the day the lane starts timing
    out and somebody deletes the test.
    """

    def test_scan_reports_the_whole_corpus_as_its_population(self, repo_scan) -> None:
        """`files_parsed < files_scanned` is an optimisation, not a sample.

        The audit skips the AST parse of files that provably cannot hold the
        constant. It must still ACCOUNT for them: the published population is
        every file the globs matched, and the census books zero blindness.
        """
        result, _ = repo_scan
        assert result.returncode == 0, result.stdout + result.stderr
        payload = json.loads(result.stdout)
        scanned = payload["files_scanned"]
        parsed = payload["files_parsed"]
        census = payload["census"]
        assert scanned > 1000, f"the corpus should be the whole tree, got {scanned}"
        assert 0 < parsed < scanned, (
            f"parsed={parsed} scanned={scanned}: the pre-filter either did nothing "
            "or swallowed the corpus"
        )
        assert census["population"] == scanned, (
            "the census must account for every file in scope, not only the parsed "
            f"ones: population={census['population']} scanned={scanned}"
        )
        assert census["blind"] == {"ninguna": 0}, census["blind"]

    def test_subprocess_timeout_fires_before_the_pytest_watchdog(self, pytestconfig) -> None:
        """The two budgets must stay ordered, or the failure mode comes back.

        `tests/conftest.py::_effective_subprocess_timeout` was written to enforce
        exactly this ordering suite-wide, but it reads the budget from
        `config.getoption("timeout")`, which is the COMMAND-LINE flag — the
        `pytest.ini` value never reaches it, so the cap is inert on a normal run
        and every call-site timeout is honoured in full. Until that is fixed, the
        ordering is this file's own responsibility.
        """
        ini = float(pytestconfig.getini("timeout") or 0)
        assert ini > 0, "pytest.ini no longer declares a per-test timeout budget"
        assert AUDIT_SUBPROCESS_TIMEOUT_SECONDS < ini, (
            f"the audit subprocess may run {AUDIT_SUBPROCESS_TIMEOUT_SECONDS}s but "
            f"pytest-timeout kills the test at {ini}s. In that order the watchdog "
            "wins, and with timeout_method=thread it aborts the whole pytest "
            "process instead of failing this one test."
        )

    def test_whole_tree_scan_stays_within_its_cpu_budget(self, repo_scan) -> None:
        """CPU, not wall: this box runs at load ~300 and wall measures neighbours."""
        result, spent = repo_scan
        assert result.returncode == 0, result.stdout
        assert spent < TREE_SCAN_CPU_BUDGET_SECONDS, (
            f"the whole-tree scan spent {spent:.2f}s CPU against a "
            f"{TREE_SCAN_CPU_BUDGET_SECONDS}s budget. Raising the budget is the "
            "forbidden repair: find what got expensive, or move the scan off the "
            "lane with the reason written down."
        )


class TestPreFilterIsSoundNotASample:
    """The pre-filter drops PARSES, never files — and here is the proof.

    `_may_hold_constant` skips `ast.parse` when the source provably cannot yield
    a Constant equal to a registered field. Three ways such a constant can exist,
    three probes. A pre-filter that missed any of them would be a silent sample:
    the gate would print "0 violations" over a corpus it never really read.
    """

    def test_field_name_synthesised_by_an_escape_is_still_flagged(self, tmp_path: Path) -> None:
        """The name never appears verbatim — it is spelled with \\x70."""
        body = 'def test_x(out):\n    assert out["\\x70ermissionDecision"] == "block"\n'
        assert "permissionDecision" not in body, "the probe must not leak the name verbatim"
        root = _make_root(tmp_path, {"tests/unit/test_escaped.py": body})
        result = _audit(root)
        assert result.returncode == 1, (
            "an escaped key laundered the claim past the pre-filter\n"
            + result.stdout
            + result.stderr
        )

    def test_name_split_across_adjacent_literals_is_still_flagged(self, tmp_path: Path) -> None:
        """Implicit concatenation is folded by the parser, so it must be parsed."""
        body = 'def test_x(out):\n    assert out["permission" "Decision"] == "block"\n'
        assert "permissionDecision" not in body, "the probe must not leak the name verbatim"
        root = _make_root(tmp_path, {"tests/unit/test_split.py": body})
        result = _audit(root)
        assert result.returncode == 1, (
            "a name split across adjacent literals laundered the claim\n"
            + result.stdout
            + result.stderr
        )

    def test_a_file_that_cannot_hold_the_constant_is_not_parsed(self, tmp_path: Path) -> None:
        """The skip is real, and this is the declared cost of it.

        A file with no field name, no character escape and no literal fragment
        of the name is never handed to `ast.parse`, so a SYNTAX ERROR in such a
        file no longer aborts the audit. That is a deliberate narrowing: this
        gate reads assertions, it is not a syntax checker, and pytest collection
        already fails on a test file that does not parse. A broken file that DOES
        mention the field is still parsed, and still exits 2.
        """
        unparseable = "def test_x( :::\n"
        root = _make_root(tmp_path, {"tests/unit/test_broken.py": unparseable})
        result = _audit(root)
        assert result.returncode == 0, (
            "the pre-filter did not skip a file it should have proved harmless\n"
            + result.stdout
            + result.stderr
        )

        mentions = 'x = {"permissionDecision": 1}\ndef test_x( :::\n'
        root2 = _make_root(tmp_path / "b", {"tests/unit/test_broken2.py": mentions})
        result2 = _audit(root2)
        assert result2.returncode == 2, (
            "a syntactically broken file that mentions the field must still fail "
            f"loud; got rc={result2.returncode}\n{result2.stdout}{result2.stderr}"
        )


class TestRegistryContract:
    def test_registry_does_not_inline_values(self) -> None:
        """Copying the values here is the drift this registry exists to prevent."""
        registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
        for entry in registry["enums"]:
            assert "values" not in entry, f"enum {entry['id']} inlines its values"
            assert entry["rationale"].strip(), f"enum {entry['id']} has no rationale"

    def test_every_pointer_resolves_to_a_live_enum(self) -> None:
        registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
        for entry in registry["enums"]:
            doc = yaml.safe_load((REPO / entry["source"]).read_text(encoding="utf-8"))
            node = doc
            for part in entry["pointer"].split("."):
                assert part in node, f"{entry['id']}: pointer breaks at {part!r}"
                node = node[part]
            assert isinstance(node, list) and node

    def test_excluded_fields_carry_a_reason(self) -> None:
        """`not_registered` is the gate's declared blind spot, not commentary."""
        registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
        excluded = registry.get("not_registered") or []
        assert excluded, "a gate that declares no blind spot is claiming to be total"
        registered = {e["field"] for e in registry["enums"]}
        for item in excluded:
            assert item["field"] not in registered, f"{item['field']} is on both lists"
            assert len(item["reason"].strip()) > 40, f"{item['field']}: reason is a stub"

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


def _audit(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(AUDIT), "--root", str(root)],
        capture_output=True,
        text=True,
        timeout=120,
    )


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

    def test_repo_tree_is_clean(self) -> None:
        """No baseline, no allowlist: the tree is at exactly zero violations."""
        result = _audit(REPO)
        assert result.returncode == 0, (
            "a test in this repo asserts a value outside a closed enum\n" + result.stdout
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

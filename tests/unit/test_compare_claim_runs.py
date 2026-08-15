"""Unit tests for scripts/compare_claim_runs.py.

The comparator's product is DISAGREE: two runs that each reproduced their own
number and still contradict each other.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "compare_claim_runs.py"
spec = importlib.util.spec_from_file_location("compare_claim_runs", MODULE_PATH)
assert spec and spec.loader
compare_claim_runs = importlib.util.module_from_spec(spec)
sys.modules["compare_claim_runs"] = compare_claim_runs
spec.loader.exec_module(compare_claim_runs)


def _claim(
    *,
    id: str = "c",
    topic: str = "",
    cmd: str = "echo 1",
    expect: str = "1",
    observed: str = "1",
    status: str = "REPRODUCE",
    claim: str = "una afirmacion",
    source: str = "run.md",
) -> dict[str, Any]:
    return {
        "id": id,
        "topic": topic,
        "cmd": cmd,
        "expect": expect,
        "observed": observed,
        "status": status,
        "claim": claim,
        "source": source,
    }


def _verdicts(rows: list[dict[str, Any]]) -> dict[str, str]:
    return {row["key"]: row["verdict"] for row in rows}


def _run_file(tmp_path: Path, name: str, claims: list[dict[str, Any]]) -> Path:
    path = tmp_path / name
    path.write_text(
        json.dumps(
            {
                "schema_version": "verifiable-claim.v1",
                "totals": {},
                "reports": [{"path": name, "claims": claims}],
            }
        ),
        encoding="utf-8",
    )
    return path


# --- pairing ----------------------------------------------------------------


def test_pairs_by_topic_even_with_different_ids() -> None:
    rows = compare_claim_runs.compare_runs(
        [_claim(id="a1", topic="t/x", cmd="echo 1", expect="1", observed="1")],
        [_claim(id="b7", topic="t/x", cmd="printf 1", expect="1", observed="1")],
    )
    assert len(rows) == 1
    assert rows[0]["matched_by"] == "topic"
    assert rows[0]["verdict"] == "AGREE"
    assert rows[0]["method_differs"] is True


def test_pairs_by_id_when_no_topic() -> None:
    rows = compare_claim_runs.compare_runs(
        [_claim(id="same", cmd="echo 1")],
        [_claim(id="same", cmd="printf 1")],
    )
    assert rows[0]["matched_by"] == "id"


def test_pairs_by_normalised_command_as_last_resort() -> None:
    rows = compare_claim_runs.compare_runs(
        [_claim(id="a", cmd="grep -c foo  bar")],
        [_claim(id="b", cmd="grep  -c foo bar")],
    )
    assert len(rows) == 1
    assert rows[0]["matched_by"] == "cmd"


# --- verdicts ---------------------------------------------------------------


def test_disagreement_is_reported_even_when_both_reproduced() -> None:
    """The historical defect: both runs self-consistent, contradicting each other."""
    rows = compare_claim_runs.compare_runs(
        [_claim(id="a", topic="t/try-except", cmd="grep -c try f", expect="439", observed="439")],
        [_claim(id="b", topic="t/try-except", cmd="python3 ast.py", expect="61", observed="61")],
    )
    assert _verdicts(rows) == {"t/try-except": "DISAGREE"}
    assert "439" in rows[0]["note"] and "61" in rows[0]["note"]
    assert rows[0]["a"]["status"] == "REPRODUCE"
    assert rows[0]["b"]["status"] == "REPRODUCE"


def test_same_command_different_output_is_flagged_as_non_deterministic() -> None:
    rows = compare_claim_runs.compare_runs(
        [_claim(id="a", topic="t/x", cmd="echo $RANDOM", expect="1", observed="1")],
        [_claim(id="b", topic="t/x", cmd="echo $RANDOM", expect="2", observed="2")],
    )
    assert rows[0]["verdict"] == "DISAGREE"
    assert "non-deterministic" in rows[0]["note"]


def test_same_output_contradictory_expectations() -> None:
    rows = compare_claim_runs.compare_runs(
        [_claim(id="a", topic="t/x", expect="18", observed="18")],
        [_claim(id="b", topic="t/x", expect="20", observed="18")],
    )
    assert rows[0]["verdict"] == "DISAGREE_CLAIM"


def test_errored_side_is_incomparable_not_agreement() -> None:
    rows = compare_claim_runs.compare_runs(
        [_claim(id="a", topic="t/x", observed="5")],
        [_claim(id="b", topic="t/x", observed="", status="ERROR")],
    )
    assert rows[0]["verdict"] == "INCOMPARABLE"


def test_blocked_side_is_incomparable() -> None:
    rows = compare_claim_runs.compare_runs(
        [_claim(id="a", topic="t/x", observed="5")],
        [_claim(id="b", topic="t/x", observed="", status="BLOCKED")],
    )
    assert rows[0]["verdict"] == "INCOMPARABLE"


def test_unpaired_claims_are_only_a_and_only_b() -> None:
    rows = compare_claim_runs.compare_runs(
        [_claim(id="a", topic="t/only-a", cmd="echo a")],
        [_claim(id="b", topic="t/only-b", cmd="echo b")],
    )
    assert _verdicts(rows) == {"t/only-a": "ONLY_A", "t/only-b": "ONLY_B"}


def test_agreement_from_different_commands_is_labelled_corroboration() -> None:
    rows = compare_claim_runs.compare_runs(
        [_claim(id="a", topic="t/x", cmd="ls | wc -l", expect="501", observed="501")],
        [_claim(id="b", topic="t/x", cmd="find . | wc -l", expect="501", observed="501")],
    )
    assert rows[0]["verdict"] == "AGREE"
    assert "independent corroboration" in rows[0]["note"]


def test_whitespace_differences_do_not_create_false_disagreement() -> None:
    rows = compare_claim_runs.compare_runs(
        [_claim(id="a", topic="t/x", observed="42")],
        [_claim(id="b", topic="t/x", observed="  42  ")],
    )
    assert rows[0]["verdict"] == "AGREE"


# --- cli --------------------------------------------------------------------


def test_main_exit_codes(tmp_path: Path) -> None:
    agree_a = _run_file(tmp_path, "a.json", [_claim(id="x", topic="t", observed="1", expect="1")])
    agree_b = _run_file(tmp_path, "b.json", [_claim(id="y", topic="t", observed="1", expect="1")])
    assert compare_claim_runs.main([str(agree_a), str(agree_b)]) == 0

    disagree_b = _run_file(tmp_path, "c.json", [_claim(id="y", topic="t", observed="2", expect="2")])
    out = tmp_path / "cmp.json"
    assert compare_claim_runs.main([str(agree_a), str(disagree_b), "--json", str(out)]) == 1
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["totals"]["DISAGREE"] == 1
    assert payload["schema_version"] == compare_claim_runs.SCHEMA_VERSION


def test_main_rejects_non_verify_claims_json(tmp_path: Path) -> None:
    bogus = tmp_path / "bogus.json"
    bogus.write_text(json.dumps({"hello": "world"}), encoding="utf-8")
    assert compare_claim_runs.main([str(bogus), str(bogus)]) == 2

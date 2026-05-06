from __future__ import annotations

import json
from pathlib import Path

import pytest

from lib.context_budget import count_tokens, evaluate, filter_hook_output, read_budget, record_usage

pytestmark = pytest.mark.unit


def test_count_tokens_heuristic_rounds_up() -> None:
    assert count_tokens("") == 0
    assert count_tokens("abcd") == 1
    assert count_tokens("abcde") == 2


def test_evaluate_thresholds() -> None:
    budgets = {"static": 100}
    assert evaluate("static", 100, budgets).verdict == "PASS"
    assert evaluate("static", 110, budgets).verdict == "WARN"
    assert evaluate("static", 151, budgets).verdict == "BLOCK"


def test_read_budget_from_cognitive_os_yaml(tmp_path: Path) -> None:
    cfg = tmp_path / "cognitive-os.yaml"
    cfg.write_text("context_budget:\n  static_max_tokens: 123\n  turn_max_tokens: 456\n", encoding="utf-8")
    budgets = read_budget(cfg)
    assert budgets["static"] == 123
    assert budgets["turn"] == 456
    assert budgets["user"] == 12000


def test_record_usage_appends_jsonl(tmp_path: Path) -> None:
    row = record_usage(tmp_path, source="test", layer="static", text="hello world", session_id="s1")
    assert row["source"] == "test"
    log = tmp_path / ".cognitive-os" / "metrics" / "context-budget.jsonl"
    saved = json.loads(log.read_text().splitlines()[0])
    assert saved["session_id"] == "s1"


def test_filter_hook_output_skips_blocking_context(tmp_path: Path) -> None:
    (tmp_path / "cognitive-os.yaml").write_text("context_budget:\n  static_max_tokens: 1\n", encoding="utf-8")
    payload = {"hookSpecificOutput": {"additionalContext": "x" * 20}}
    assert filter_hook_output(tmp_path, source="test", hook_json=json.dumps(payload), session_id="s1") == ""


def test_default_budgets_cover_all_layers(tmp_path: Path) -> None:
    budgets = read_budget(tmp_path / "missing.yaml")
    assert budgets == {"static": 4000, "turn": 8000, "user": 12000, "cache": 32000}


def test_block_override_allows_but_keeps_block_verdict(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COS_ALLOW_CONTEXT_BUDGET_OVERRUN", "1")
    verdict = evaluate("static", 151, {"static": 100})
    assert verdict.verdict == "BLOCK"
    assert verdict.allowed is True
    assert verdict.reason == "override"


def test_warn_band_extends_through_1_5_before_block() -> None:
    assert evaluate("static", 121, {"static": 100}).verdict == "WARN"
    assert evaluate("static", 150, {"static": 100}).verdict == "WARN"
    assert evaluate("static", 151, {"static": 100}).verdict == "BLOCK"


def test_filter_hook_output_passes_non_json_and_no_context(tmp_path: Path) -> None:
    assert filter_hook_output(tmp_path, source="test", hook_json="not-json", session_id="s1") == "not-json"
    payload = json.dumps({"hookSpecificOutput": {"permissionDecision": "allow"}})
    assert filter_hook_output(tmp_path, source="test", hook_json=payload, session_id="s1") == payload
    assert not (tmp_path / ".cognitive-os" / "metrics" / "context-budget.jsonl").exists()


def test_filter_hook_output_allows_block_with_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COS_ALLOW_CONTEXT_BUDGET_OVERRUN", "1")
    (tmp_path / "cognitive-os.yaml").write_text("context_budget:\n  static_max_tokens: 1\n", encoding="utf-8")
    payload = json.dumps({"hookSpecificOutput": {"additionalContext": "x" * 20}})
    assert filter_hook_output(tmp_path, source="test", hook_json=payload, session_id="s1") == payload
    row = json.loads((tmp_path / ".cognitive-os" / "metrics" / "context-budget.jsonl").read_text().splitlines()[-1])
    assert row["verdict"] == "BLOCK"
    assert row["allowed"] is True
    assert row["reason"] == "override"

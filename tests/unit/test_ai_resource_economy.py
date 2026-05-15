from __future__ import annotations

from pathlib import Path

from scripts import ai_budget_preflight, ai_resource_economy_audit

ROOT = Path(__file__).resolve().parents[2]


def test_ai_resource_economy_audit_passes() -> None:
    report = ai_resource_economy_audit.build_report(ROOT)
    assert report["status"] == "pass", report
    assert report["summary"]["ledger_field_count"] >= 12


def test_budget_preflight_blocks_high_loop_risk() -> None:
    report = ai_budget_preflight.build_preflight(
        task="large multi-agent repair",
        paths=["cognitive-os.yaml"],
        expected_agents=5,
        expected_tests=50,
        token_budget=100,
    )
    assert report["status"] == "block"
    assert "split_task" in report["recommended_actions"]
    assert report["estimates"]["loop_risk"] == "high"


def test_budget_preflight_passes_small_local_task() -> None:
    report = ai_budget_preflight.build_preflight(
        task="inspect one manifest",
        paths=["manifests/ai-resource-economy.yaml"],
        expected_agents=1,
        expected_tests=1,
        token_budget=8000,
    )
    assert report["status"] in {"pass", "warn"}
    assert report["estimates"]["file_count"] == 1

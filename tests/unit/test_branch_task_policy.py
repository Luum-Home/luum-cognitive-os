from __future__ import annotations

import pytest

from lib.branch_task_policy import branch_for_task, evaluate_branch_for_task


@pytest.mark.unit
def test_branch_for_task_slugs_task_id_not_prompt_text() -> None:
    assert branch_for_task("Release v0.28 / Fix") == "codex/task/release-v0.28-fix"


@pytest.mark.unit
def test_evaluate_branch_for_task_pass_and_block(tmp_path) -> None:
    passed = evaluate_branch_for_task(tmp_path, task_id="abc", current="codex/task/abc")
    blocked = evaluate_branch_for_task(tmp_path, task_id="abc", current="main")

    assert passed.status == "PASS"
    assert blocked.status == "BLOCK"
    assert blocked.expected_branch == "codex/task/abc"

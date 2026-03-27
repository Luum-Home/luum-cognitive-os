"""Behavior tests for sprint contract format validation.

Migrated from test-sprint-contracts.sh.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior


# ---------------------------------------------------------------------------
# Helper: validate task contract
# ---------------------------------------------------------------------------


def validate_task_contract(task_content: str) -> tuple[str, int]:
    """Validate that a task markdown block contains proper Verification: lines.

    Returns (status, return_code) where status is
    "valid" | "missing_verification" | "empty_verification".
    """
    lines = task_content.splitlines()

    has_verification = any(
        re.match(r"^\s*Verification:", line) for line in lines
    )
    if not has_verification:
        return "missing_verification", 1

    for line in lines:
        if re.match(r"^\s*Verification:\s*$", line):
            return "empty_verification", 1

    return "valid", 0


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestTaskContractValidation:
    """Tests for the validate_task_contract function."""

    def test_task_with_verification(self):
        task = (
            "Task: Implement login endpoint\n"
            "Phase: apply\n"
            "Verification: `curl -s localhost:8080/login | grep 200`\n"
        )
        status, rc = validate_task_contract(task)
        assert status == "valid"
        assert rc == 0

    def test_task_without_verification(self):
        task = (
            "Task: Implement login endpoint\n"
            "Phase: apply\n"
            "Description: Build the login route\n"
        )
        status, rc = validate_task_contract(task)
        assert status == "missing_verification"
        assert rc == 1

    def test_verification_with_command(self):
        task = (
            "Task: Add health check\n"
            "Phase: apply\n"
            'Verification: `npm test -- --grep "health check"`\n'
        )
        status, rc = validate_task_contract(task)
        assert status == "valid"
        assert rc == 0

    def test_verification_with_assertion(self):
        task = (
            "Task: Update config schema\n"
            "Phase: spec\n"
            "Verification: Config file passes JSON schema validation without errors\n"
        )
        status, rc = validate_task_contract(task)
        assert status == "valid"
        assert rc == 0

    def test_multiple_verifications(self):
        task = (
            "Task: Implement auth middleware\n"
            "Phase: apply\n"
            'Verification: `npm test -- --grep "auth middleware"`\n'
            "Verification: Unauthorized requests return 401 status code\n"
            "Verification: `curl -s -o /dev/null -w '%{http_code}' localhost:8080/protected` returns 401\n"
        )
        status, rc = validate_task_contract(task)
        assert status == "valid"
        assert rc == 0

    def test_empty_verification(self):
        task = (
            "Task: Implement caching layer\n"
            "Phase: apply\n"
            "Verification:\n"
        )
        status, rc = validate_task_contract(task)
        assert status == "empty_verification"
        assert rc == 1

    def test_full_task_block(self, tmp_path: Path):
        """All tasks in a block have valid verification lines."""
        tasks = [
            (
                "Task: Create database schema\n"
                "Phase: spec\n"
                "Verification: Schema DDL is syntactically valid SQL\n"
            ),
            (
                "Task: Implement API endpoints\n"
                "Phase: apply\n"
                'Verification: `npm test -- --grep "API endpoints"` passes\n'
                "Verification: All endpoints return proper JSON content-type\n"
            ),
            (
                "Task: Write integration tests\n"
                "Phase: verify\n"
                "Verification: `npm run test:integration` exits with code 0\n"
            ),
        ]
        for task in tasks:
            status, _ = validate_task_contract(task)
            assert status == "valid"

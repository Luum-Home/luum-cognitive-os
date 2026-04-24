"""Behavioral tests for skills/doc-sync — ADR-059 Phase 1 pilot.

doc-sync reads .cognitive-os/metrics/stale-docs.jsonl and updates docs.
Tests validate the data contract of that JSONL file and the skill's
stated preconditions (no LLM calls needed).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
STALE_DOCS_PATH = PROJECT_ROOT / ".cognitive-os" / "metrics" / "stale-docs.jsonl"

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# 1. Imports / invocation — SKILL.md exists with correct frontmatter
# ---------------------------------------------------------------------------


class TestDocSyncSkillExists:
    def test_skill_md_present(self):
        skill_md = PROJECT_ROOT / "skills" / "doc-sync" / "SKILL.md"
        assert skill_md.exists()

    def test_skill_md_has_audience(self):
        skill_md = PROJECT_ROOT / "skills" / "doc-sync" / "SKILL.md"
        content = skill_md.read_text()
        assert "audience:" in content


# ---------------------------------------------------------------------------
# 2. Contract test — stale-docs.jsonl schema validation
# ---------------------------------------------------------------------------


class TestDocSyncDataContract:
    def test_stale_docs_jsonl_schema_when_present(self):
        """If stale-docs.jsonl exists, every line must match the documented schema."""
        if not STALE_DOCS_PATH.exists():
            pytest.skip("stale-docs.jsonl does not exist (no stale docs — valid state)")

        required_keys = {"timestamp", "changed_file", "stale_docs", "change_type"}
        valid_change_types = {
            "controller", "entity", "config", "usecase",
            "route", "hook", "rule", "docker",
        }

        lines = STALE_DOCS_PATH.read_text().strip().splitlines()
        for i, line in enumerate(lines):
            if not line.strip():
                continue
            record = json.loads(line)
            missing = required_keys - set(record.keys())
            assert not missing, (
                f"stale-docs.jsonl line {i+1} missing keys: {missing}"
            )
            ct = record.get("change_type", "")
            assert ct in valid_change_types, (
                f"stale-docs.jsonl line {i+1}: invalid change_type={ct!r}"
            )
            assert isinstance(record["stale_docs"], list), (
                f"stale-docs.jsonl line {i+1}: stale_docs must be a list"
            )

    def test_stale_docs_jsonl_write_is_valid_schema(self, tmp_path: Path):
        """Writing a well-formed stale-docs record to a tmp file must be parseable."""
        record = {
            "timestamp": "2026-04-24T10:00:00Z",
            "changed_file": "apps/service/controller.go",
            "stale_docs": ["docs/api-reference.md"],
            "change_type": "controller",
        }
        jsonl_file = tmp_path / "stale-docs.jsonl"
        jsonl_file.write_text(json.dumps(record) + "\n")

        lines = jsonl_file.read_text().strip().splitlines()
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["change_type"] == "controller"
        assert parsed["stale_docs"] == ["docs/api-reference.md"]


# ---------------------------------------------------------------------------
# 3. Happy path — empty stale-docs.jsonl => "No stale docs" scenario
# ---------------------------------------------------------------------------


class TestDocSyncHappyPath:
    def test_empty_stale_docs_is_valid_state(self, tmp_path: Path):
        """SKILL.md: 'If file is empty, report No stale docs and exit'. Empty = valid."""
        empty_file = tmp_path / "stale-docs.jsonl"
        empty_file.write_text("")
        assert empty_file.exists()
        content = empty_file.read_text().strip()
        assert content == "", "Empty stale-docs.jsonl should have no lines"

    def test_grouping_by_stale_doc(self, tmp_path: Path):
        """Multiple entries pointing to the same stale_docs target group correctly."""
        records = [
            {
                "timestamp": "2026-04-24T09:00:00Z",
                "changed_file": "apps/service/controller_a.go",
                "stale_docs": ["docs/api.md"],
                "change_type": "controller",
            },
            {
                "timestamp": "2026-04-24T09:01:00Z",
                "changed_file": "apps/service/controller_b.go",
                "stale_docs": ["docs/api.md"],
                "change_type": "controller",
            },
        ]
        jsonl_file = tmp_path / "stale-docs.jsonl"
        jsonl_file.write_text("\n".join(json.dumps(r) for r in records) + "\n")

        # Parse and group by stale_docs target
        groups: dict[str, list[str]] = {}
        for line in jsonl_file.read_text().strip().splitlines():
            record = json.loads(line)
            for doc in record["stale_docs"]:
                groups.setdefault(doc, []).append(record["changed_file"])

        assert "docs/api.md" in groups
        assert len(groups["docs/api.md"]) == 2

    def test_doc_sync_skill_documents_metrics_path(self):
        """SKILL.md must reference the stale-docs.jsonl path so agents know where to read."""
        skill_md = PROJECT_ROOT / "skills" / "doc-sync" / "SKILL.md"
        content = skill_md.read_text()
        assert "stale-docs.jsonl" in content


# ---------------------------------------------------------------------------
# 4. Error handling — missing stale-docs.jsonl is explicitly handled
# ---------------------------------------------------------------------------


class TestDocSyncErrorHandling:
    def test_skill_documents_missing_file_behavior(self):
        """SKILL.md must document the 'file does not exist' edge case."""
        skill_md = PROJECT_ROOT / "skills" / "doc-sync" / "SKILL.md"
        content = skill_md.read_text()
        # SKILL.md says: "If the file is empty or doesn't exist, report..."
        assert "doesn't exist" in content or "does not exist" in content

    def test_invalid_json_line_raises_decode_error(self, tmp_path: Path):
        """A malformed JSONL line must raise JSONDecodeError when parsed."""
        bad_file = tmp_path / "bad-stale-docs.jsonl"
        bad_file.write_text('{"timestamp": "bad", "unclosed\n')

        with pytest.raises(json.JSONDecodeError):
            for line in bad_file.read_text().strip().splitlines():
                json.loads(line)

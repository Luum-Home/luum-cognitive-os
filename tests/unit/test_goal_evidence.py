# SCOPE: os-only
"""Unit tests for lib/goal_evidence.py — T-05 AC."""

from __future__ import annotations

import json

from lib.goal_evidence import parse_evidence, validate_evidence
from lib.goal_state import EvidencePacket, CommandEvidence


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_valid_packet_dict(**overrides) -> dict:
    base = {
        "iteration": 1,
        "files_changed": ["lib/foo.py"],
        "commands_run": [
            {"command": "pytest tests/", "exit_code": 0, "output_excerpt": "1 passed"}
        ],
        "passing_checks": ["AC-001"],
        "acceptance_coverage": {"AC-001": "pytest passed with 1 test"},
        "remaining_gaps": [],
        "blockers": [],
        "next_action": None,
        "raw_summary": "Ran tests, all passed.",
    }
    base.update(overrides)
    return base


def _valid_json(**overrides) -> str:
    return json.dumps(_make_valid_packet_dict(**overrides))


# ---------------------------------------------------------------------------
# T-05: parse_evidence — valid packet
# ---------------------------------------------------------------------------


class TestParseEvidenceValid:
    def test_plain_json_accepted(self):
        result = parse_evidence(_valid_json())
        assert result.valid is True
        assert result.packet is not None
        assert isinstance(result.packet, EvidencePacket)
        assert result.errors == []

    def test_fenced_markdown_json_accepted(self):
        raw = "```json\n" + _valid_json() + "\n```"
        result = parse_evidence(raw)
        assert result.valid is True
        assert result.packet is not None

    def test_fenced_markdown_without_lang_tag(self):
        raw = "```\n" + _valid_json() + "\n```"
        result = parse_evidence(raw)
        assert result.valid is True
        assert result.packet is not None

    def test_fields_correctly_populated(self):
        result = parse_evidence(_valid_json())
        pkt = result.packet
        assert pkt.iteration == 1
        assert pkt.files_changed == ["lib/foo.py"]
        assert len(pkt.commands_run) == 1
        assert isinstance(pkt.commands_run[0], CommandEvidence)
        assert pkt.commands_run[0].exit_code == 0
        assert pkt.passing_checks == ["AC-001"]
        assert pkt.acceptance_coverage == {"AC-001": "pytest passed with 1 test"}
        assert pkt.remaining_gaps == []
        assert pkt.blockers == []
        assert pkt.next_action is None
        assert pkt.raw_summary == "Ran tests, all passed."
        assert pkt.source == "explicit-packet"


# ---------------------------------------------------------------------------
# T-05: parse_evidence — invalid packets (field-specific errors)
# ---------------------------------------------------------------------------


class TestParseEvidenceInvalid:
    def test_missing_iteration_field(self):
        d = _make_valid_packet_dict()
        del d["iteration"]
        result = parse_evidence(json.dumps(d))
        assert result.valid is False
        assert any("iteration" in e for e in result.errors)

    def test_missing_files_changed(self):
        d = _make_valid_packet_dict()
        del d["files_changed"]
        result = parse_evidence(json.dumps(d))
        assert result.valid is False
        assert any("files_changed" in e for e in result.errors)

    def test_missing_acceptance_coverage(self):
        d = _make_valid_packet_dict()
        del d["acceptance_coverage"]
        result = parse_evidence(json.dumps(d))
        assert result.valid is False
        assert any("acceptance_coverage" in e for e in result.errors)

    def test_missing_raw_summary(self):
        d = _make_valid_packet_dict()
        del d["raw_summary"]
        result = parse_evidence(json.dumps(d))
        assert result.valid is False
        assert any("raw_summary" in e for e in result.errors)

    def test_invalid_json_string(self):
        result = parse_evidence("{not valid json")
        assert result.valid is False
        assert len(result.errors) > 0

    def test_plain_string_no_json(self):
        result = parse_evidence("I made progress today.")
        assert result.valid is False
        assert len(result.errors) > 0

    def test_commands_run_not_a_list(self):
        d = _make_valid_packet_dict(commands_run="bad")
        result = parse_evidence(json.dumps(d))
        assert result.valid is False
        assert any("commands_run" in e for e in result.errors)

    def test_command_missing_exit_code(self):
        d = _make_valid_packet_dict(
            commands_run=[{"command": "ls"}]
        )
        result = parse_evidence(json.dumps(d))
        assert result.valid is False
        assert any("exit_code" in e for e in result.errors)

    def test_files_changed_not_a_list(self):
        d = _make_valid_packet_dict(files_changed="not-a-list")
        result = parse_evidence(json.dumps(d))
        assert result.valid is False
        assert any("files_changed" in e for e in result.errors)


# ---------------------------------------------------------------------------
# T-05: acceptance_checks coverage validation
# ---------------------------------------------------------------------------


class TestAcceptanceCoverageValidation:
    def test_uncovered_check_rejected(self):
        d = _make_valid_packet_dict(acceptance_coverage={"AC-001": "done"})
        result = parse_evidence(
            json.dumps(d),
            acceptance_checks=["AC-001", "AC-002"],
        )
        assert result.valid is False
        assert any("AC-002" in e for e in result.errors)

    def test_all_checks_covered_accepted(self):
        d = _make_valid_packet_dict(
            acceptance_coverage={"AC-001": "done", "AC-002": "also done"}
        )
        result = parse_evidence(
            json.dumps(d),
            acceptance_checks=["AC-001", "AC-002"],
        )
        assert result.valid is True

    def test_no_acceptance_checks_arg_skips_coverage_check(self):
        d = _make_valid_packet_dict(acceptance_coverage={})
        result = parse_evidence(json.dumps(d), acceptance_checks=None)
        assert result.valid is True

    def test_empty_acceptance_checks_arg_skips_coverage_check(self):
        d = _make_valid_packet_dict(acceptance_coverage={})
        result = parse_evidence(json.dumps(d), acceptance_checks=[])
        assert result.valid is True


# ---------------------------------------------------------------------------
# T-05: validate_evidence (post-parse helper)
# ---------------------------------------------------------------------------


class TestValidateEvidence:
    def _make_packet(self, coverage: dict) -> EvidencePacket:
        return EvidencePacket(
            iteration=1,
            files_changed=[],
            commands_run=[],
            passing_checks=list(coverage.keys()),
            acceptance_coverage=coverage,
            remaining_gaps=[],
            blockers=[],
            next_action=None,
            raw_summary="done",
        )

    def test_full_coverage_returns_no_errors(self):
        pkt = self._make_packet({"AC-001": "done", "AC-002": "also done"})
        errors = validate_evidence(pkt, ["AC-001", "AC-002"])
        assert errors == []

    def test_missing_check_returns_error(self):
        pkt = self._make_packet({"AC-001": "done"})
        errors = validate_evidence(pkt, ["AC-001", "AC-002"])
        assert len(errors) == 1
        assert "AC-002" in errors[0]

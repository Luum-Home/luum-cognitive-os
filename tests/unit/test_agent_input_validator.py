"""
tests/unit/test_agent_input_validator.py

Behavioral tests for lib/agent_input_validator.py (ADR-038 Wave 1).

Coverage targets:
  - required field missing → fail
  - optional field missing → ok
  - extra fields in payload not in schema → ok (informational)
  - type mismatch → fail
  - unknown type → informational note, not failure
  - multi-field schema with mixed required/optional
  - parse_schema handles full prompt block extraction
  - format_escalation produces ESCALATION prefix
"""


from lib.agent_input_validator import (
    format_escalation,
    parse_schema,
    validate_input,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SIMPLE_SCHEMA = """
task_description: str (required) — natural language description of the task
acceptance_criteria: list[str] (optional) — verifiable expected outcomes
blast_radius: int (optional) — estimated number of files affected
working_dir: path (optional) — absolute path to operate in
"""

FULL_PROMPT_WITH_SCHEMA = f"""
SKILL: Load `templates/agent-preamble.md`

INPUT SCHEMA:
{SIMPLE_SCHEMA.strip()}

Some other content that should be ignored.
"""


# ---------------------------------------------------------------------------
# parse_schema
# ---------------------------------------------------------------------------


class TestParseSchema:
    def test_parses_all_fields(self):
        specs = parse_schema(SIMPLE_SCHEMA)
        assert len(specs) == 4
        names = [s.name for s in specs]
        assert names == ["task_description", "acceptance_criteria", "blast_radius", "working_dir"]

    def test_required_flag(self):
        specs = parse_schema(SIMPLE_SCHEMA)
        by_name = {s.name: s for s in specs}
        assert by_name["task_description"].required is True
        assert by_name["acceptance_criteria"].required is False
        assert by_name["blast_radius"].required is False

    def test_type_resolution(self):
        specs = parse_schema(SIMPLE_SCHEMA)
        by_name = {s.name: s for s in specs}
        assert by_name["task_description"].python_type is str
        assert by_name["blast_radius"].python_type is int
        assert by_name["working_dir"].python_type is str  # path maps to str

    def test_extracts_block_from_full_prompt(self):
        specs = parse_schema(FULL_PROMPT_WITH_SCHEMA)
        assert len(specs) == 4
        assert specs[0].name == "task_description"

    def test_skips_placeholder_lines(self):
        schema = """
task_description: str (required) — description
... custom fields per launch ...
"""
        specs = parse_schema(schema)
        assert len(specs) == 1
        assert specs[0].name == "task_description"

    def test_skips_blank_lines(self):
        schema = "\n\nfoo: str (required)\n\nbar: int (optional)\n\n"
        specs = parse_schema(schema)
        assert len(specs) == 2

    def test_unknown_type_flagged(self):
        schema = "widget: Widget (required) — custom type"
        specs = parse_schema(schema)
        assert len(specs) == 1
        assert specs[0].unknown_type is True
        assert specs[0].python_type is None

    def test_cardinality_defaults_to_required(self):
        # Line with no (required|optional) marker
        schema = "implicit_field: str — description without cardinality"
        specs = parse_schema(schema)
        assert len(specs) == 1
        assert specs[0].required is True


# ---------------------------------------------------------------------------
# validate_input — required field
# ---------------------------------------------------------------------------


class TestRequiredField:
    def test_missing_required_field_fails(self):
        ok, errors = validate_input(SIMPLE_SCHEMA, payload={})
        assert ok is False
        assert any("task_description" in e and "MISSING_REQUIRED" in e for e in errors)

    def test_none_required_field_fails(self):
        ok, errors = validate_input(SIMPLE_SCHEMA, payload={"task_description": None})
        assert ok is False
        assert any("task_description" in e for e in errors)

    def test_empty_string_required_field_fails(self):
        ok, errors = validate_input(SIMPLE_SCHEMA, payload={"task_description": ""})
        assert ok is False

    def test_present_required_field_passes(self):
        ok, errors = validate_input(
            SIMPLE_SCHEMA,
            payload={"task_description": "implement the feature"},
        )
        assert ok is True
        assert not any("MISSING_REQUIRED" in e for e in errors)


# ---------------------------------------------------------------------------
# validate_input — optional field
# ---------------------------------------------------------------------------


class TestOptionalField:
    def test_missing_optional_field_is_ok(self):
        ok, errors = validate_input(
            SIMPLE_SCHEMA,
            payload={"task_description": "do something"},
        )
        assert ok is True
        assert not any("acceptance_criteria" in e and "MISSING_REQUIRED" in e for e in errors)

    def test_none_optional_field_is_ok(self):
        ok, errors = validate_input(
            SIMPLE_SCHEMA,
            payload={"task_description": "do something", "blast_radius": None},
        )
        assert ok is True


# ---------------------------------------------------------------------------
# validate_input — extra fields
# ---------------------------------------------------------------------------


class TestExtraFields:
    def test_extra_field_not_in_schema_is_ok(self):
        ok, errors = validate_input(
            SIMPLE_SCHEMA,
            payload={
                "task_description": "do something",
                "undeclared_field": "extra value",
                "another_extra": 42,
            },
        )
        assert ok is True
        # No error about undeclared fields
        assert not any("undeclared_field" in e for e in errors)


# ---------------------------------------------------------------------------
# validate_input — type mismatch
# ---------------------------------------------------------------------------


class TestTypeMismatch:
    def test_wrong_type_fails(self):
        ok, errors = validate_input(
            SIMPLE_SCHEMA,
            payload={
                "task_description": "do something",
                "blast_radius": "not_an_int",  # should be int
            },
        )
        assert ok is False
        assert any("TYPE_MISMATCH" in e and "blast_radius" in e for e in errors)

    def test_correct_type_passes(self):
        ok, errors = validate_input(
            SIMPLE_SCHEMA,
            payload={
                "task_description": "do something",
                "blast_radius": 5,
            },
        )
        assert ok is True
        assert not any("TYPE_MISMATCH" in e for e in errors)

    def test_bool_does_not_satisfy_integer_field(self):
        ok, errors = validate_input(
            SIMPLE_SCHEMA,
            payload={
                "task_description": "do something",
                "blast_radius": True,
            },
        )
        assert ok is False
        assert any("TYPE_MISMATCH" in e and "blast_radius" in e for e in errors)

    def test_list_type_mismatch(self):
        ok, errors = validate_input(
            SIMPLE_SCHEMA,
            payload={
                "task_description": "do something",
                "acceptance_criteria": "should be a list",  # str instead of list
            },
        )
        assert ok is False
        assert any("TYPE_MISMATCH" in e and "acceptance_criteria" in e for e in errors)

    def test_list_type_correct(self):
        ok, errors = validate_input(
            SIMPLE_SCHEMA,
            payload={
                "task_description": "do something",
                "acceptance_criteria": ["check A", "check B"],
            },
        )
        assert ok is True

    def test_list_str_rejects_wrong_item_type(self):
        ok, errors = validate_input(
            SIMPLE_SCHEMA,
            payload={
                "task_description": "do something",
                "acceptance_criteria": ["check A", 123],
            },
        )
        assert ok is False
        assert any("TYPE_MISMATCH" in e and "item 1" in e for e in errors)


# ---------------------------------------------------------------------------
# validate_input — unknown type
# ---------------------------------------------------------------------------


class TestUnknownType:
    def test_unknown_type_is_informational_not_failure(self):
        schema = "widget: Widget (required) — a custom widget"
        ok, errors = validate_input(schema, payload={"widget": object()})
        # Should pass — unknown type skips validation
        assert ok is True
        assert any("UNKNOWN_TYPE" in e for e in errors)

    def test_unknown_type_missing_required_still_fails(self):
        schema = "widget: Widget (required) — a custom widget"
        ok, errors = validate_input(schema, payload={})
        assert ok is False
        assert any("MISSING_REQUIRED" in e and "widget" in e for e in errors)


# ---------------------------------------------------------------------------
# validate_input — multi-field mixed schema
# ---------------------------------------------------------------------------


class TestMixedSchema:
    MIXED = """
name: str (required) — entity name
count: int (required) — number of items
label: str (optional) — display label
tags: list (optional) — list of tags
"""

    def test_all_required_present_passes(self):
        ok, errors = validate_input(
            self.MIXED,
            payload={"name": "alice", "count": 3},
        )
        assert ok is True

    def test_multiple_required_missing_all_reported(self):
        ok, errors = validate_input(self.MIXED, payload={})
        assert ok is False
        missing = [e for e in errors if "MISSING_REQUIRED" in e]
        assert len(missing) == 2
        field_names = " ".join(missing)
        assert "name" in field_names
        assert "count" in field_names

    def test_full_payload_passes(self):
        ok, errors = validate_input(
            self.MIXED,
            payload={"name": "bob", "count": 7, "label": "primary", "tags": ["a", "b"]},
        )
        assert ok is True
        assert not any("MISSING_REQUIRED" in e or "TYPE_MISMATCH" in e for e in errors)


# ---------------------------------------------------------------------------
# format_escalation
# ---------------------------------------------------------------------------


class TestFormatEscalation:
    def test_empty_errors_returns_empty_string(self):
        assert format_escalation([]) == ""

    def test_escalation_starts_with_keyword(self):
        msg = format_escalation(["MISSING_REQUIRED: field 'x' is required"])
        assert msg.startswith("ESCALATION:")

    def test_contains_all_errors(self):
        errors = [
            "MISSING_REQUIRED: field 'a' is required",
            "TYPE_MISMATCH: field 'b' expected int but got str",
        ]
        msg = format_escalation(errors)
        assert "field 'a'" in msg
        assert "field 'b'" in msg

    def test_stopping_notice_included(self):
        msg = format_escalation(["MISSING_REQUIRED: field 'x' is required"])
        assert "Stopping" in msg


# ---------------------------------------------------------------------------
# Integration: full prompt extraction + validation
# ---------------------------------------------------------------------------


class TestIntegration:
    def test_validates_from_full_prompt(self):
        ok, errors = validate_input(
            FULL_PROMPT_WITH_SCHEMA,
            payload={"task_description": "build the thing"},
        )
        assert ok is True

    def test_escalation_message_from_full_prompt(self):
        ok, errors = validate_input(FULL_PROMPT_WITH_SCHEMA, payload={})
        assert ok is False
        msg = format_escalation(errors)
        assert "ESCALATION:" in msg
        assert "task_description" in msg

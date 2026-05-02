"""Unit tests for lib.format_converter token-efficient renderings."""

import json

from lib.format_converter import FormatConverter


def test_markdown_table_escapes_pipes_and_truncates_cells():
    records = [{"name": "a|b", "detail": "x" * 80}]
    rendered = FormatConverter.to_markdown_table(records)
    assert "a\\|b" in rendered
    assert "..." in rendered
    assert len(rendered) < len(json.dumps(records)) + 40


def test_tsv_escapes_tabs_and_newlines():
    records = [{"name": "alpha\tbeta", "detail": "line1\nline2"}]
    rendered = FormatConverter.to_tsv(records)
    assert "alpha\\tbeta" in rendered
    assert "line1\\nline2" in rendered
    assert "\t" in rendered.splitlines()[0]


def test_compact_kv_flattens_nested_dicts():
    rendered = FormatConverter.to_compact_kv({"agent": {"id": "a1"}, "ok": True})
    assert "agent.id=a1" in rendered
    assert "ok=true" in rendered


def test_auto_format_prefers_tsv_for_agent_lists():
    records = [{"id": i, "status": "done"} for i in range(4)]
    rendered = FormatConverter.auto_format(records, context="agent")
    assert rendered.startswith("id\tstatus")


def test_auto_format_prefers_markdown_for_human_lists():
    records = [{"id": i, "status": "done"} for i in range(4)]
    rendered = FormatConverter.auto_format(records, context="human")
    assert rendered.startswith("| id | status |")


def test_auto_format_handles_mixed_plain_values():
    assert FormatConverter.auto_format(["a", "b", 3]) == "a\nb\n3"

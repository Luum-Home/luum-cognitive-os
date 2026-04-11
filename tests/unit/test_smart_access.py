"""Unit tests for lib/smart_access.py."""

import json
import pytest

from lib.smart_access import SmartAccess


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tasks_file(tmp_path):
    """Write a sample active-tasks.json and return its path."""
    data = {
        "tasks": [
            {"id": "t1", "status": "in_progress", "description": "Work in progress"},
            {"id": "t2", "status": "completed", "description": "Already done"},
            {"id": "t3", "status": "failed", "description": "Needs retry"},
            {"id": "t4", "status": "completed", "description": "Another done"},
        ]
    }
    p = tmp_path / "active-tasks.json"
    p.write_text(json.dumps(data))
    return str(p)


@pytest.fixture()
def tasks_file_list_format(tmp_path):
    """active-tasks.json where root is a list (alternate schema)."""
    data = [
        {"id": "a1", "status": "in_progress"},
        {"id": "a2", "status": "completed"},
    ]
    p = tmp_path / "active-tasks-list.json"
    p.write_text(json.dumps(data))
    return str(p)


@pytest.fixture()
def plan_approved(tmp_path):
    p = tmp_path / "plan.md"
    p.write_text("# My Plan\n\nStatus: APPROVED\n\nSome more content.\n")
    return str(p)


@pytest.fixture()
def plan_completed(tmp_path):
    p = tmp_path / "plan.md"
    p.write_text("# My Plan\n\n<!-- status: COMPLETED -->\n")
    return str(p)


@pytest.fixture()
def skill_md(tmp_path):
    content = (
        "---\n"
        "name: my-skill\n"
        "description: Does something useful\n"
        "version: 1.2.3\n"
        "---\n"
        "# My Skill\n\nLong description here.\n"
    )
    p = tmp_path / "SKILL.md"
    p.write_text(content)
    return str(p)


@pytest.fixture()
def skill_md_no_frontmatter(tmp_path):
    p = tmp_path / "SKILL.md"
    p.write_text("# Skill without frontmatter\n\nJust a heading.\n")
    return str(p)


@pytest.fixture()
def config_yaml(tmp_path):
    content = (
        "project:\n"
        "  phase: reconstruction\n"
        "  name: luum-agent-os\n"
        "resources:\n"
        "  budget:\n"
        "    daily_alert_usd: 10\n"
    )
    p = tmp_path / "cognitive-os.yaml"
    p.write_text(content)
    return str(p)


@pytest.fixture()
def markdown_file(tmp_path):
    content = (
        "# Document\n\n"
        "## Section One\n\n"
        "Content of section one.\n"
        "More content.\n\n"
        "## Section Two\n\n"
        "Content of section two.\n"
    )
    p = tmp_path / "doc.md"
    p.write_text(content)
    return str(p)


# ---------------------------------------------------------------------------
# get_active_tasks
# ---------------------------------------------------------------------------


def test_get_active_tasks_filters_completed(tasks_file):
    result = SmartAccess.get_active_tasks(tasks_file)
    ids = {t["id"] for t in result}
    assert "t1" in ids
    assert "t3" in ids
    assert "t2" not in ids
    assert "t4" not in ids
    assert len(result) == 2


def test_get_active_tasks_list_format(tasks_file_list_format):
    result = SmartAccess.get_active_tasks(tasks_file_list_format)
    assert len(result) == 1
    assert result[0]["id"] == "a1"


def test_get_active_tasks_empty_file(tmp_path):
    p = tmp_path / "empty.json"
    p.write_text("[]")
    result = SmartAccess.get_active_tasks(str(p))
    assert result == []


def test_get_active_tasks_missing_file(tmp_path):
    result = SmartAccess.get_active_tasks(str(tmp_path / "nonexistent.json"))
    assert result == []


def test_get_active_tasks_corrupt_json(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not valid json")
    result = SmartAccess.get_active_tasks(str(p))
    assert result == []


# ---------------------------------------------------------------------------
# get_task_by_id
# ---------------------------------------------------------------------------


def test_get_task_by_id_found(tasks_file):
    task = SmartAccess.get_task_by_id("t3", tasks_file)
    assert task is not None
    assert task["id"] == "t3"
    assert task["status"] == "failed"


def test_get_task_by_id_not_found(tasks_file):
    task = SmartAccess.get_task_by_id("nonexistent", tasks_file)
    assert task is None


def test_get_task_by_id_missing_file(tmp_path):
    result = SmartAccess.get_task_by_id("t1", str(tmp_path / "missing.json"))
    assert result is None


# ---------------------------------------------------------------------------
# get_plan_status
# ---------------------------------------------------------------------------


def test_get_plan_status_approved(plan_approved):
    assert SmartAccess.get_plan_status(plan_approved) == "APPROVED"


def test_get_plan_status_completed(plan_completed):
    assert SmartAccess.get_plan_status(plan_completed) == "COMPLETED"


def test_get_plan_status_in_progress(tmp_path):
    p = tmp_path / "plan.md"
    p.write_text("# Plan\nStatus: IN_PROGRESS\n")
    assert SmartAccess.get_plan_status(str(p)) == "IN_PROGRESS"


def test_get_plan_status_missing(tmp_path):
    result = SmartAccess.get_plan_status(str(tmp_path / "missing.md"))
    assert result == "UNKNOWN"


def test_get_plan_status_no_status_line(tmp_path):
    p = tmp_path / "plan.md"
    p.write_text("# Plan\n\nThis plan has no status marker.\n")
    assert SmartAccess.get_plan_status(str(p)) == "UNKNOWN"


# ---------------------------------------------------------------------------
# get_skill_frontmatter
# ---------------------------------------------------------------------------


def test_get_skill_frontmatter(skill_md):
    fm = SmartAccess.get_skill_frontmatter(skill_md)
    assert fm.get("name") == "my-skill"
    assert fm.get("description") == "Does something useful"
    assert fm.get("version") == "1.2.3"


def test_get_skill_frontmatter_no_frontmatter(skill_md_no_frontmatter):
    fm = SmartAccess.get_skill_frontmatter(skill_md_no_frontmatter)
    assert fm == {}


def test_get_skill_frontmatter_missing_file(tmp_path):
    fm = SmartAccess.get_skill_frontmatter(str(tmp_path / "SKILL.md"))
    assert fm == {}


def test_get_skill_frontmatter_empty_file(tmp_path):
    p = tmp_path / "SKILL.md"
    p.write_text("")
    fm = SmartAccess.get_skill_frontmatter(str(p))
    assert fm == {}


# ---------------------------------------------------------------------------
# get_config_value
# ---------------------------------------------------------------------------


def test_get_config_value_nested(config_yaml):
    phase = SmartAccess.get_config_value("project.phase", config_yaml)
    assert phase == "reconstruction"


def test_get_config_value_top_level(config_yaml):
    # 'project' key itself — returns None because it has no inline value
    val = SmartAccess.get_config_value("project.name", config_yaml)
    assert val == "luum-agent-os"


def test_get_config_value_deep_nested(config_yaml):
    val = SmartAccess.get_config_value("resources.budget.daily_alert_usd", config_yaml)
    assert val == "10"


def test_get_config_value_missing_key(config_yaml):
    val = SmartAccess.get_config_value("project.nonexistent", config_yaml)
    assert val is None


def test_get_config_value_missing_file(tmp_path):
    val = SmartAccess.get_config_value("project.phase", str(tmp_path / "missing.yaml"))
    assert val is None


# ---------------------------------------------------------------------------
# count_lines
# ---------------------------------------------------------------------------


def test_count_lines(tmp_path):
    p = tmp_path / "file.txt"
    p.write_text("line1\nline2\nline3\n")
    assert SmartAccess.count_lines(str(p)) == 3


def test_count_lines_empty(tmp_path):
    p = tmp_path / "empty.txt"
    p.write_text("")
    assert SmartAccess.count_lines(str(p)) == 0


def test_count_lines_missing(tmp_path):
    assert SmartAccess.count_lines(str(tmp_path / "missing.txt")) == 0


# ---------------------------------------------------------------------------
# read_section
# ---------------------------------------------------------------------------


def test_read_section_found(markdown_file):
    content = SmartAccess.read_section(markdown_file, "## Section One")
    assert "Content of section one." in content
    assert "More content." in content
    # Should not bleed into Section Two
    assert "Content of section two." not in content


def test_read_section_second_section(markdown_file):
    content = SmartAccess.read_section(markdown_file, "## Section Two")
    assert "Content of section two." in content


def test_read_section_not_found(markdown_file):
    content = SmartAccess.read_section(markdown_file, "## Nonexistent Section")
    assert content == ""


def test_read_section_missing_file(tmp_path):
    content = SmartAccess.read_section(str(tmp_path / "missing.md"), "## Section")
    assert content == ""


def test_read_section_max_lines(tmp_path):
    lines = ["## Big Section\n"] + [f"line {i}\n" for i in range(100)]
    p = tmp_path / "big.md"
    p.write_text("".join(lines))
    content = SmartAccess.read_section(str(p), "## Big Section", max_lines=5)
    result_lines = [l for l in content.splitlines() if l.strip()]
    assert len(result_lines) <= 5


# ---------------------------------------------------------------------------
# files_never_fully_read
# ---------------------------------------------------------------------------


def test_files_never_fully_read():
    result = SmartAccess.files_never_fully_read()
    assert isinstance(result, list)
    assert len(result) > 0
    # Must include the key files
    joined = " ".join(result)
    assert "active-tasks.json" in joined
    assert "cognitive-os.yaml" in joined

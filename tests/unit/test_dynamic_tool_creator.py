"""Unit tests for lib/dynamic_tool_creator.py."""

import json
import os
import stat
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure lib/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "lib"))

from dynamic_tool_creator import DynamicToolCreator, _slugify


@pytest.fixture
def tmp_project(tmp_path):
    """Create a temporary project directory with .cognitive-os structure."""
    cos_dir = tmp_path / ".cognitive-os"
    cos_dir.mkdir()
    return tmp_path


@pytest.fixture
def creator(tmp_project):
    """Create a DynamicToolCreator rooted in the temp project."""
    return DynamicToolCreator(
        project_root=str(tmp_project),
        session_id="test-session-001",
    )


class TestSlugify:
    def test_basic(self):
        assert _slugify("JSON Validator") == "json-validator"

    def test_special_chars(self):
        assert _slugify("my_tool!@#$%") == "my-tool"

    def test_truncation(self):
        long_name = "a" * 100
        assert len(_slugify(long_name)) <= 64

    def test_empty_stripped(self):
        assert _slugify("---") == ""


class TestCreateTool:
    def test_create_bash_tool(self, creator, tmp_project):
        result = creator.create_tool(
            name="greet",
            description="Say hello",
            implementation='echo "Hello, $1!"',
            tool_type="bash",
        )

        assert result["name"] == "greet"
        assert result["type"] == "bash"
        assert result["invocable"] is True
        assert os.path.isfile(result["path"])

        # Verify file is executable
        st = os.stat(result["path"])
        assert st.st_mode & stat.S_IEXEC

        # Verify shebang
        with open(result["path"]) as f:
            content = f.read()
        assert content.startswith("#!/usr/bin/env bash")
        assert 'echo "Hello, $1!"' in content

    def test_create_python_tool(self, creator, tmp_project):
        result = creator.create_tool(
            name="adder",
            description="Add two numbers",
            implementation="def add(a, b): return a + b",
            tool_type="python",
        )

        assert result["type"] == "python"
        assert result["path"].endswith(".py")
        assert os.path.isfile(result["path"])

        with open(result["path"]) as f:
            content = f.read()
        assert "def add(a, b):" in content

    def test_create_skill_tool(self, creator, tmp_project):
        result = creator.create_tool(
            name="deploy helper",
            description="Assists with deployments",
            implementation="1. Check status\n2. Deploy\n3. Verify",
            tool_type="skill",
        )

        assert result["type"] == "skill"
        assert result["path"].endswith("SKILL.md")
        assert os.path.isfile(result["path"])

        with open(result["path"]) as f:
            content = f.read()
        assert "deploy-helper" in content
        assert "dynamic-tool: true" in content

    def test_invalid_type_raises(self, creator):
        with pytest.raises(ValueError, match="tool_type must be"):
            creator.create_tool("x", "desc", "code", tool_type="ruby")

    def test_empty_name_raises(self, creator):
        with pytest.raises(ValueError, match="cannot be empty"):
            creator.create_tool("", "desc", "code")

    def test_name_producing_empty_slug_raises(self, creator):
        with pytest.raises(ValueError, match="empty slug"):
            creator.create_tool("---", "desc", "code")

    def test_creates_in_dynamic_tools_dir(self, creator, tmp_project):
        result = creator.create_tool("mytool", "desc", "echo hi", "bash")
        expected_dir = str(tmp_project / ".cognitive-os" / "dynamic-tools")
        assert result["path"].startswith(expected_dir)

    def test_overwrite_existing_tool(self, creator):
        creator.create_tool("mytool", "v1", "echo v1", "bash")
        result = creator.create_tool("mytool", "v2", "echo v2", "bash")

        with open(result["path"]) as f:
            assert "echo v2" in f.read()

        # Registry should have only one entry
        tools = creator.list_dynamic_tools()
        matching = [t for t in tools if t["name"] == "mytool"]
        assert len(matching) == 1
        assert matching[0]["description"] == "v2"


class TestListDynamicTools:
    def test_empty_initially(self, creator):
        assert creator.list_dynamic_tools() == []

    def test_lists_created_tools(self, creator):
        creator.create_tool("tool-a", "desc a", "echo a", "bash")
        creator.create_tool("tool-b", "desc b", "print('b')", "python")

        tools = creator.list_dynamic_tools()
        assert len(tools) == 2
        names = {t["name"] for t in tools}
        assert names == {"tool-a", "tool-b"}


class TestGetTool:
    def test_get_existing(self, creator):
        creator.create_tool("finder", "find stuff", "find .", "bash")
        tool = creator.get_tool("finder")
        assert tool is not None
        assert tool["name"] == "finder"

    def test_get_nonexistent(self, creator):
        assert creator.get_tool("nonexistent") is None


class TestRecordUsage:
    def test_increments_usage(self, creator):
        creator.create_tool("counter", "count", "wc -l", "bash")
        creator.record_usage("counter")
        creator.record_usage("counter")

        tool = creator.get_tool("counter")
        assert tool["usage_count"] == 2
        assert tool["last_used_at"] is not None

    def test_noop_for_unknown(self, creator):
        # Should not raise
        creator.record_usage("does-not-exist")


class TestPromoteToSkill:
    def test_promote_bash_tool(self, creator, tmp_project):
        creator.create_tool("linter", "lint files", "shellcheck $@", "bash")
        skill_dir = creator.promote_to_skill("linter")

        assert os.path.isdir(skill_dir)
        skill_md = os.path.join(skill_dir, "SKILL.md")
        assert os.path.isfile(skill_md)

        # Script should be copied
        assert os.path.isfile(os.path.join(skill_dir, "linter.sh"))

        # Check promoted in auto-generated path
        assert "skills/auto-generated/linter" in skill_dir

        # Registry should mark as promoted
        tool = creator.get_tool("linter")
        assert tool["promoted"] is True
        assert tool["promoted_to"] == skill_dir

    def test_promote_python_tool(self, creator, tmp_project):
        creator.create_tool("parser", "parse data", "import json", "python")
        skill_dir = creator.promote_to_skill("parser")

        assert os.path.isfile(os.path.join(skill_dir, "parser.py"))
        assert os.path.isfile(os.path.join(skill_dir, "SKILL.md"))

    def test_promote_skill_tool(self, creator, tmp_project):
        creator.create_tool("helper", "help", "1. Do thing", "skill")
        skill_dir = creator.promote_to_skill("helper")

        assert os.path.isfile(os.path.join(skill_dir, "SKILL.md"))

    def test_promote_nonexistent_raises(self, creator):
        with pytest.raises(ValueError, match="not found"):
            creator.promote_to_skill("ghost")


class TestCleanupSessionTools:
    def test_removes_all_tools(self, creator):
        creator.create_tool("a", "desc", "echo a", "bash")
        creator.create_tool("b", "desc", "print('b')", "python")

        removed = creator.cleanup_session_tools(keep_promoted=False)
        assert removed == 2
        assert creator.list_dynamic_tools() == []

    def test_keeps_promoted_tools(self, creator):
        creator.create_tool("keep-me", "desc", "echo keep", "bash")
        creator.create_tool("remove-me", "desc", "echo remove", "bash")
        creator.promote_to_skill("keep-me")

        removed = creator.cleanup_session_tools(keep_promoted=True)
        assert removed == 1

        tools = creator.list_dynamic_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "keep-me"

    def test_cleanup_removes_skill_directories(self, creator):
        creator.create_tool("my-skill", "desc", "step 1", "skill")
        tool = creator.get_tool("my-skill")
        skill_dir = os.path.dirname(tool["path"])
        assert os.path.isdir(skill_dir)

        creator.cleanup_session_tools(keep_promoted=False)
        assert not os.path.isdir(skill_dir)

    def test_cleanup_empty_returns_zero(self, creator):
        assert creator.cleanup_session_tools() == 0


class TestShouldCreateTool:
    def test_below_threshold(self, creator):
        assert creator.should_create_tool(2) is False

    def test_at_threshold(self, creator):
        assert creator.should_create_tool(3) is True

    def test_above_threshold(self, creator):
        assert creator.should_create_tool(10) is True

    def test_custom_threshold(self, creator):
        assert creator.should_create_tool(4, threshold=5) is False
        assert creator.should_create_tool(5, threshold=5) is True


class TestFormatToolList:
    def test_empty(self, creator):
        assert "No dynamic tools" in creator.format_tool_list()

    def test_with_tools(self, creator):
        creator.create_tool("toolx", "does x", "echo x", "bash")
        output = creator.format_tool_list()
        assert "toolx" in output
        assert "does x" in output
        assert "bash" in output


class TestBashToolIsExecutable:
    def test_executable_flag(self, creator):
        result = creator.create_tool("runner", "run", "echo run", "bash")
        st = os.stat(result["path"])
        assert st.st_mode & stat.S_IEXEC != 0


class TestPythonToolIsImportable:
    def test_importable(self, creator):
        result = creator.create_tool(
            "math-helper",
            "Math utilities",
            "def double(x):\n    return x * 2",
            "python",
        )
        # Verify the file can be loaded as a Python module
        import importlib.util

        spec = importlib.util.spec_from_file_location("math_helper", result["path"])
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert module.double(5) == 10

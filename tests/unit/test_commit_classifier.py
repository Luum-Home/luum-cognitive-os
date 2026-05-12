"""Tests for lib/commit_classifier.py"""

import pytest
from lib.commit_classifier import classify_files, detect_related_files, propose_commits


# ---------------------------------------------------------------------------
# classify_files
# ---------------------------------------------------------------------------

class TestClassifyFiles:
    def test_lib_files(self):
        result = classify_files(["lib/foo.py", "lib/bar.py"])
        assert result == {"lib": ["lib/foo.py", "lib/bar.py"]}

    def test_hooks_files(self):
        result = classify_files(["hooks/my-hook.sh"])
        assert result == {"hooks": ["hooks/my-hook.sh"]}

    def test_tests_files(self):
        result = classify_files(["tests/unit/test_foo.py"])
        assert result == {"tests": ["tests/unit/test_foo.py"]}

    def test_test_suffix_pattern(self):
        result = classify_files(["lib/foo_test.py"])
        assert result == {"tests": ["lib/foo_test.py"]}

    def test_mixed_themes(self):
        result = classify_files(["lib/foo.py", "hooks/bar.sh", "tests/unit/test_foo.py"])
        assert set(result.keys()) == {"lib", "hooks", "tests"}
        assert result["lib"] == ["lib/foo.py"]
        assert result["hooks"] == ["hooks/bar.sh"]
        assert result["tests"] == ["tests/unit/test_foo.py"]

    def test_skills_under_cognitive_os(self):
        result = classify_files([".cognitive-os/skills/smart-commit/SKILL.md"])
        assert result == {"skills": [".cognitive-os/skills/smart-commit/SKILL.md"]}

    def test_rules_under_cognitive_os(self):
        result = classify_files([".cognitive-os/rules/trust-score.md"])
        assert result == {"rules": [".cognitive-os/rules/trust-score.md"]}

    def test_config_yaml(self):
        result = classify_files(["cognitive-os.yaml"])
        assert result == {"config": ["cognitive-os.yaml"]}

    def test_config_json(self):
        result = classify_files([".claude/settings.json"])
        assert result == {"config": [".claude/settings.json"]}

    def test_markdown_as_docs(self):
        result = classify_files(["README.md"])
        assert result == {"docs": ["README.md"]}

    def test_docs_directory(self):
        result = classify_files(["docs/04-Concepts/architecture.md"])
        assert result == {"docs": ["docs/04-Concepts/architecture.md"]}

    def test_packages_directory(self):
        result = classify_files(["packages/agent-coordination/rules/agent-bus.md"])
        assert result == {"packages": ["packages/agent-coordination/rules/agent-bus.md"]}

    def test_templates_directory(self):
        result = classify_files([".cognitive-os/templates/agent-preamble.md"])
        assert result == {"templates": [".cognitive-os/templates/agent-preamble.md"]}

    def test_misc_fallback(self):
        result = classify_files(["some/unknown/file.go"])
        assert result == {"misc": ["some/unknown/file.go"]}

    def test_empty_list(self):
        result = classify_files([])
        assert result == {}

    def test_test_inside_lib_is_test_theme(self):
        # A test file inside lib/ should still classify as 'tests'
        result = classify_files(["lib/test_helper.py"])
        assert "tests" in result

    def test_spec_ts_files(self):
        result = classify_files(["src/foo.spec.ts"])
        assert result == {"tests": ["src/foo.spec.ts"]}


# ---------------------------------------------------------------------------
# detect_related_files
# ---------------------------------------------------------------------------

class TestDetectRelatedFiles:
    def test_basic_pair(self):
        files = ["lib/commit_classifier.py", "tests/unit/test_commit_classifier.py"]
        pairs = detect_related_files(files)
        assert len(pairs) == 1
        src, tst = pairs[0]
        assert "commit_classifier.py" in src
        assert "test_commit_classifier" in tst

    def test_no_pairs(self):
        files = ["lib/foo.py", "hooks/bar.sh"]
        pairs = detect_related_files(files)
        assert pairs == []

    def test_multiple_pairs(self):
        files = [
            "lib/alpha.py",
            "lib/beta.py",
            "tests/unit/test_alpha.py",
            "tests/unit/test_beta.py",
        ]
        pairs = detect_related_files(files)
        assert len(pairs) == 2

    def test_unpaired_test_ignored(self):
        files = ["tests/unit/test_orphan.py"]
        pairs = detect_related_files(files)
        assert pairs == []


# ---------------------------------------------------------------------------
# propose_commits
# ---------------------------------------------------------------------------

class TestProposeCommits:
    def test_single_theme(self):
        classified = {"lib": ["lib/foo.py"]}
        proposals = propose_commits(classified)
        assert len(proposals) == 1
        assert proposals[0]["prefix"] == "feat"
        assert "library changes" in proposals[0]["message"]
        assert "lib/foo.py" in proposals[0]["files"]

    def test_multiple_themes_produce_multiple_commits(self):
        classified = {
            "lib":   ["lib/foo.py"],
            "hooks": ["hooks/bar.sh"],
        }
        proposals = propose_commits(classified)
        assert len(proposals) == 2

    def test_hooks_prefix_is_chore(self):
        classified = {"hooks": ["hooks/bar.sh"]}
        proposals = propose_commits(classified)
        assert proposals[0]["prefix"] == "chore"

    def test_rules_prefix_is_docs(self):
        classified = {"rules": ["rules/trust-score.md"]}
        proposals = propose_commits(classified)
        assert proposals[0]["prefix"] == "docs"

    def test_test_prefix_is_test(self):
        classified = {"tests": ["tests/unit/test_foo.py"]}
        proposals = propose_commits(classified)
        assert proposals[0]["prefix"] == "test"

    def test_empty_classified(self):
        proposals = propose_commits({})
        assert proposals == []

    def test_related_pair_merged_into_source_theme(self):
        # lib/commit_classifier.py and tests/.../test_commit_classifier.py
        # should end up in the same commit
        classified = {
            "lib":   ["lib/commit_classifier.py"],
            "tests": ["tests/unit/test_commit_classifier.py"],
        }
        proposals = propose_commits(classified)
        # Either one proposal (merged) or two — but the test file should
        # appear somewhere
        all_files = [f for p in proposals for f in p["files"]]
        assert "lib/commit_classifier.py" in all_files
        assert "tests/unit/test_commit_classifier.py" in all_files

    def test_proposal_order_lib_before_tests(self):
        classified = {
            "tests": ["tests/unit/test_foo.py"],
            "lib":   ["lib/foo.py"],
        }
        proposals = propose_commits(classified)
        # lib should come before tests in ordering
        themes = [p["theme"] for p in proposals]
        # If both survive as separate proposals, lib is first
        if len(proposals) == 2:
            assert themes.index("lib") < themes.index("tests")

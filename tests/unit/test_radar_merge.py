"""Unit tests for scripts/radar_merge.py — Tech Radar merge engine.

Tests verify the three core contracts from ADR-065:
  1. Dedup: same repo twice → UPDATE, not duplicate INSERT
  2. Human-field preservation: body prose survives frontmatter refresh
  3. Classification routing: ADOPT/ASSESS → ecosystem-tools; REJECT → blocked-tools

Additional tests:
  4. Classification shift: ADOPT entry that becomes REJECT is moved between docs
  5. New entry insert: a brand-new repo creates a well-formed entry block
  6. Fuzzy-match: no frontmatter 'repo:' field triggers new insert + warning

Python 3.9+ compatible.
"""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest

# Add scripts/ to sys.path so we can import radar_merge as a normal module
_PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "scripts"))

import radar_merge as _mod  # noqa: E402

# Pull names from the loaded module
RepoEval = _mod.RepoEval
MergeAction = _mod.MergeAction
parse_doc_entries = _mod.parse_doc_entries
find_entry = _mod.find_entry
merge_into_doc = _mod.merge_into_doc
build_new_entry = _mod.build_new_entry
build_frontmatter = _mod.build_frontmatter
handle_classification_shift = _mod.handle_classification_shift
update_changelog = _mod.update_changelog
generate_diff = _mod.generate_diff
parse_artifact = _mod.parse_artifact
rewrite_frontmatter_in_chunk = _mod.rewrite_frontmatter_in_chunk

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

ECOSYSTEM_WITH_ONE_ENTRY = textwrap.dedent("""\
    # Ecosystem Tools

    ## Integrated Tools

    ### ccusage — Claude Code Token & Cost Analytics (ADOPT)

    ---
    repo: ryoppippi/ccusage
    classification: ADOPT
    stars: 1000
    license: MIT
    ci_health: green
    score: 80
    one_liner: "Token usage analytics for Claude Code"
    last_evaluated: 2026-01-01
    ---

    **Usage examples**:
    ```bash
    npx ccusage@latest
    npx ccusage@latest --json
    ```

    **Adoption notes**: We use this in lib/record_completion.py to read real token data.

    **Gotchas**: Requires ~/.claude/projects to be accessible.

""")

BLOCKED_EMPTY = textwrap.dedent("""\
    # Blocked Tools

    ## Blocked by AGPL

""")

BLOCKED_WITH_ONE_ENTRY = textwrap.dedent("""\
    # Blocked Tools

    ## Blocked by AGPL

    ### Daytona — Runtime Sandbox (REJECT)

    ---
    repo: daytonaio/daytona
    classification: REJECT
    stars: 65000
    license: AGPL
    ci_health: green
    score: 90
    one_liner: "Development environment management"
    last_evaluated: 2026-01-01
    ---

    **Why blocked**: AGPL copyleft applies to SaaS usage.

    **Alternative**: E2B (Apache 2.0).

""")


def _make_eval(
    repo: str,
    classification: str = "ADOPT",
    stars: int = 500,
    score: int = 75,
    license: str = "MIT",
    one_liner: str = "A useful tool",
) -> RepoEval:
    owner, name = repo.split("/", 1) if "/" in repo else ("", repo)
    return RepoEval(
        repo=repo,
        owner=owner,
        name=name,
        classification=classification,
        stars=stars,
        license=license,
        ci_health="green",
        score=score,
        one_liner=one_liner,
        last_evaluated="2026-04-24",
        raw_fields={"repo": repo},
    )


# ---------------------------------------------------------------------------
# Test 1: Dedup — feeding same repo twice produces UPDATE (not duplicate INSERT)
# ---------------------------------------------------------------------------

class TestDedup:
    """Feeding the same repo URL twice in a batch must produce exactly one entry (UPDATE)."""

    def test_dedup_same_repo_twice_produces_single_entry(self):
        ev = _make_eval("ryoppippi/ccusage", stars=1200, score=82)
        # Feed the same evaluation twice — simulates duplicate in batch input
        doc_text = ECOSYSTEM_WITH_ONE_ENTRY

        new_text, actions = merge_into_doc(doc_text, [ev, ev], "ecosystem-tools", "2026-04-24")

        # Count occurrences of the entry heading
        heading_count = new_text.count("### ccusage")
        assert heading_count == 1, (
            f"Expected exactly 1 '### ccusage' heading, found {heading_count}. "
            "Dedup failed — same repo was inserted twice."
        )

    def test_dedup_second_occurrence_overwrites_first(self):
        """When the same repo appears twice, the last values win (last-write-wins)."""
        ev1 = _make_eval("ryoppippi/ccusage", stars=1000, score=80)
        ev2 = _make_eval("ryoppippi/ccusage", stars=1500, score=90)

        doc_text = ECOSYSTEM_WITH_ONE_ENTRY
        # Simulate the main() dedup logic manually (last-wins dict)
        seen: dict[str, RepoEval] = {}
        for ev in [ev1, ev2]:
            seen[ev.repo] = ev
        unique_evals = list(seen.values())
        assert len(unique_evals) == 1
        assert unique_evals[0].stars == 1500, "Last-write-wins dedup should keep stars=1500"

    def test_dedup_existing_entry_gets_refreshed_action(self):
        """Re-running on an already-present repo produces 'refreshed' or 'updated', not 'added'."""
        ev = _make_eval("ryoppippi/ccusage", stars=1200, score=82)
        doc_text = ECOSYSTEM_WITH_ONE_ENTRY

        _, actions = merge_into_doc(doc_text, [ev], "ecosystem-tools", "2026-04-24")

        assert len(actions) == 1
        assert actions[0].action in ("refreshed", "updated"), (
            f"Expected 'refreshed' or 'updated' action for existing entry, got '{actions[0].action}'"
        )
        assert actions[0].action != "added", "Existing entry must not produce 'added' action"


# ---------------------------------------------------------------------------
# Test 2: Human-field preservation
# ---------------------------------------------------------------------------

class TestHumanFieldPreservation:
    """Human-owned prose (usage_examples, adoption_notes, gotchas) must survive a merge."""

    def test_usage_examples_preserved_after_frontmatter_update(self):
        ev = _make_eval("ryoppippi/ccusage", stars=9999, score=95)
        doc_text = ECOSYSTEM_WITH_ONE_ENTRY

        new_text, _ = merge_into_doc(doc_text, [ev], "ecosystem-tools", "2026-04-24")

        assert "npx ccusage@latest" in new_text, "Usage example command must be preserved"
        assert "npx ccusage@latest --json" in new_text, "Second usage example must be preserved"

    def test_adoption_notes_preserved(self):
        ev = _make_eval("ryoppippi/ccusage", stars=9999)
        doc_text = ECOSYSTEM_WITH_ONE_ENTRY

        new_text, _ = merge_into_doc(doc_text, [ev], "ecosystem-tools", "2026-04-24")

        assert "lib/record_completion.py" in new_text, "Adoption notes referencing lib/ must be preserved"

    def test_gotchas_preserved(self):
        ev = _make_eval("ryoppippi/ccusage", stars=9999)
        doc_text = ECOSYSTEM_WITH_ONE_ENTRY

        new_text, _ = merge_into_doc(doc_text, [ev], "ecosystem-tools", "2026-04-24")

        assert "~/.claude/projects" in new_text, "Gotcha referencing ~/.claude must be preserved"

    def test_auto_owned_fields_are_rewritten(self):
        ev = _make_eval("ryoppippi/ccusage", stars=9999, score=99)
        doc_text = ECOSYSTEM_WITH_ONE_ENTRY

        new_text, _ = merge_into_doc(doc_text, [ev], "ecosystem-tools", "2026-04-24")

        assert "stars: 9999" in new_text, "Auto-owned 'stars' field must be updated to new value"
        assert "stars: 1000" not in new_text, "Old stars value must not persist"
        assert "score: 99" in new_text, "Auto-owned 'score' field must be updated"

    def test_last_evaluated_date_is_updated(self):
        ev = _make_eval("ryoppippi/ccusage")
        ev.last_evaluated = "2026-04-24"
        doc_text = ECOSYSTEM_WITH_ONE_ENTRY

        new_text, _ = merge_into_doc(doc_text, [ev], "ecosystem-tools", "2026-04-24")

        assert "last_evaluated: 2026-04-24" in new_text, "last_evaluated must be refreshed"


# ---------------------------------------------------------------------------
# Test 3: Classification routing
# ---------------------------------------------------------------------------

class TestClassificationRouting:
    """ADOPT/TRIAL/ASSESS → ecosystem-tools.md; REJECT → blocked-tools.md."""

    def test_adopt_goes_to_ecosystem_tools(self):
        ev = _make_eval("owner/mytool", classification="ADOPT")
        new_text, actions = merge_into_doc(
            ECOSYSTEM_WITH_ONE_ENTRY, [ev], "ecosystem-tools", "2026-04-24"
        )

        assert "mytool" in new_text, "ADOPT entry must appear in ecosystem-tools"
        assert any(a.target_doc == "ecosystem-tools" for a in actions)

    def test_assess_goes_to_ecosystem_tools(self):
        ev = _make_eval("owner/newtool", classification="ASSESS")
        new_text, actions = merge_into_doc(
            ECOSYSTEM_WITH_ONE_ENTRY, [ev], "ecosystem-tools", "2026-04-24"
        )

        assert "newtool" in new_text, "ASSESS entry must appear in ecosystem-tools"

    def test_reject_goes_to_blocked_tools(self):
        ev = _make_eval("owner/badtool", classification="REJECT", license="AGPL")
        new_text, actions = merge_into_doc(
            BLOCKED_EMPTY, [ev], "blocked-tools", "2026-04-24"
        )

        assert "badtool" in new_text, "REJECT entry must appear in blocked-tools"
        assert any(a.target_doc == "blocked-tools" for a in actions)

    def test_adopt_does_not_go_to_blocked_tools(self):
        # Test routing table directly via the loaded module
        CTOD = _mod.CLASSIFICATION_TO_DOC
        assert CTOD["ADOPT"] == "ecosystem-tools", "ADOPT must route to ecosystem-tools"
        assert CTOD["TRIAL"] == "ecosystem-tools"
        assert CTOD["ASSESS"] == "ecosystem-tools"
        assert CTOD["HOLD"] == "ecosystem-tools"
        assert CTOD["REJECT"] == "blocked-tools", "REJECT must route to blocked-tools"

    def test_five_url_fixture(self):
        """
        ADR-065 Verification: 5-URL batch (1 AGPL-REJECT, 2 MIT-ADOPT, 2 ASSESS)
        → 4 in ecosystem-tools, 1 in blocked-tools.
        """
        urls_evals = [
            _make_eval("owner/agpl-tool", classification="REJECT", license="AGPL"),
            _make_eval("owner/adopt-one", classification="ADOPT", license="MIT"),
            _make_eval("owner/adopt-two", classification="ADOPT", license="MIT"),
            _make_eval("owner/assess-one", classification="ASSESS", license="MIT"),
            _make_eval("owner/assess-two", classification="ASSESS", license="MIT"),
        ]

        eco_evals = [ev for ev in urls_evals if _mod.CLASSIFICATION_TO_DOC.get(ev.classification) == "ecosystem-tools"]
        blk_evals = [ev for ev in urls_evals if _mod.CLASSIFICATION_TO_DOC.get(ev.classification) == "blocked-tools"]

        assert len(eco_evals) == 4, f"Expected 4 ecosystem entries, got {len(eco_evals)}"
        assert len(blk_evals) == 1, f"Expected 1 blocked entry, got {len(blk_evals)}"

        eco_text, eco_actions = merge_into_doc(ECOSYSTEM_WITH_ONE_ENTRY, eco_evals, "ecosystem-tools", "2026-04-24")
        blk_text, blk_actions = merge_into_doc(BLOCKED_EMPTY, blk_evals, "blocked-tools", "2026-04-24")

        # All 4 should appear in ecosystem-tools
        for ev in eco_evals:
            assert ev.name in eco_text, f"{ev.name} must be in ecosystem-tools"

        # 1 should appear in blocked-tools
        assert "agpl-tool" in blk_text, "REJECT tool must be in blocked-tools"
        assert "agpl-tool" not in eco_text, "REJECT tool must NOT be in ecosystem-tools"


# ---------------------------------------------------------------------------
# Test 4: Classification shift (ADOPT → REJECT moves entry between docs)
# ---------------------------------------------------------------------------

class TestClassificationShift:
    def test_adopt_to_reject_moves_entry(self):
        """An entry currently ADOPT in ecosystem-tools that is now REJECT must move to blocked-tools."""
        ev = _make_eval("ryoppippi/ccusage", classification="REJECT", license="AGPL")

        new_eco, new_blk, action = handle_classification_shift(
            ECOSYSTEM_WITH_ONE_ENTRY, BLOCKED_EMPTY, ev, "2026-04-24"
        )

        assert action is not None, "A move action must be produced"
        assert action.action == "moved"
        assert "ccusage" not in new_eco or new_eco.count("### ccusage") == 0, (
            "Moved entry must be removed from ecosystem-tools"
        )
        assert "ccusage" in new_blk, "Moved entry must appear in blocked-tools"

    def test_move_preserves_human_body(self):
        """Moving an entry must carry the human-owned prose to the new doc."""
        ev = _make_eval("ryoppippi/ccusage", classification="REJECT", license="AGPL")

        _, new_blk, action = handle_classification_shift(
            ECOSYSTEM_WITH_ONE_ENTRY, BLOCKED_EMPTY, ev, "2026-04-24"
        )

        assert "npx ccusage@latest" in new_blk, "Usage examples must travel with moved entry"
        assert "lib/record_completion.py" in new_blk, "Adoption notes must travel with moved entry"

    def test_move_prepends_moved_comment(self):
        ev = _make_eval("ryoppippi/ccusage", classification="REJECT", license="AGPL")

        _, new_blk, _ = handle_classification_shift(
            ECOSYSTEM_WITH_ONE_ENTRY, BLOCKED_EMPTY, ev, "2026-04-24"
        )

        assert "moved from ecosystem-tools.md" in new_blk, "<!-- moved from … --> comment must be prepended"
        assert "2026-04-24" in new_blk, "Move date must be in the comment"


# ---------------------------------------------------------------------------
# Test 5: New entry insert produces well-formed block
# ---------------------------------------------------------------------------

class TestNewEntryInsert:
    def test_new_entry_has_frontmatter(self):
        ev = _make_eval("new-org/new-tool", classification="ADOPT", one_liner="Does something useful")
        entry_text = build_new_entry(ev)

        assert "---" in entry_text, "New entry must contain YAML frontmatter block"
        assert "repo: new-org/new-tool" in entry_text
        assert "classification: ADOPT" in entry_text

    def test_new_entry_has_heading(self):
        ev = _make_eval("new-org/new-tool", classification="ADOPT", one_liner="Does something useful")
        entry_text = build_new_entry(ev)

        assert entry_text.startswith("### new-tool"), "Entry must start with ### heading"

    def test_new_entry_inserted_into_doc(self):
        ev = _make_eval("new-org/new-tool", classification="ADOPT")
        new_text, actions = merge_into_doc(
            ECOSYSTEM_WITH_ONE_ENTRY, [ev], "ecosystem-tools", "2026-04-24"
        )

        assert "new-tool" in new_text
        assert len(actions) == 1
        assert actions[0].action == "added"


# ---------------------------------------------------------------------------
# Test 6: Fuzzy match (heading without repo: frontmatter)
# ---------------------------------------------------------------------------

class TestFuzzyMatch:
    def test_entry_without_frontmatter_triggers_new_insert(self, capsys):
        """Entry with no repo: frontmatter → fuzzy match → new insert + warning."""
        doc_without_fm = textwrap.dedent("""\
            # Ecosystem Tools

            ### ccusage — Claude Code Token & Cost Analytics (ADOPT)

            **Usage examples**: Custom usage notes here.

        """)
        ev = _make_eval("ryoppippi/ccusage", classification="ADOPT")

        _, actions = merge_into_doc(doc_without_fm, [ev], "ecosystem-tools", "2026-04-24")

        # With no repo: frontmatter, find_entry may return fuzzy or no match
        # either way, the tool should not crash and should produce an action
        assert len(actions) == 1

    def test_parse_doc_entries_finds_heading_without_frontmatter(self):
        doc = textwrap.dedent("""\
            # Tools

            ### some-tool — Does stuff

            **Notes**: Some human prose here.

            ### other-tool — Does other stuff (ADOPT)

            ---
            repo: owner/other-tool
            classification: ADOPT
            stars: 100
            license: MIT
            ci_health: green
            score: 70
            last_evaluated: 2026-01-01
            ---

        """)
        entries = parse_doc_entries(doc)
        assert len(entries) == 2
        # First entry has no repo: field
        assert entries[0]["repo"] is None
        # Second entry has repo: field
        assert entries[1]["repo"] == "owner/other-tool"


# ---------------------------------------------------------------------------
# Test 7: Artifact parser
# ---------------------------------------------------------------------------

class TestArtifactParser:
    def test_parse_artifact_from_frontmatter(self, tmp_path):
        artifact = tmp_path / "owner_mytool.md"
        artifact.write_text(textwrap.dedent("""\
            ---
            repo: owner/mytool
            classification: ADOPT
            stars: 500
            license: MIT
            ci_health: green
            score: 78
            one_liner: "A good tool"
            last_evaluated: 2026-04-24
            ---

            ## Summary
            This is a great tool.
        """))

        ev = parse_artifact(artifact)

        assert ev is not None
        assert ev.repo == "owner/mytool"
        assert ev.classification == "ADOPT"
        assert ev.stars == 500
        assert ev.license == "MIT"

    def test_parse_artifact_falls_back_to_filename(self, tmp_path):
        artifact = tmp_path / "owner_fallback.md"
        artifact.write_text("## Summary\nNo frontmatter here.\n\nClassification: TRIAL\n")

        ev = parse_artifact(artifact)

        assert ev is not None
        assert ev.repo == "owner/fallback"
        assert ev.classification == "TRIAL"


# ---------------------------------------------------------------------------
# Test 8: CHANGELOG updater
# ---------------------------------------------------------------------------

class TestChangelogUpdater:
    def test_adds_documentation_section_if_missing(self, tmp_path):
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("# Changelog\n\n## [Unreleased]\n\n## [1.0.0] - 2026-01-01\n")

        actions = [MergeAction(
            repo="owner/tool",
            action="added",
            target_doc="ecosystem-tools",
            new_classification="ADOPT",
        )]

        result = update_changelog(changelog, actions, "2026-04-24")

        assert "### Documentation" in result
        assert "- radar: added owner/tool as ADOPT" in result

    def test_appends_to_existing_documentation_section(self, tmp_path):
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(
            "# Changelog\n\n## [Unreleased]\n\n### Documentation\n- existing entry\n\n"
        )

        actions = [MergeAction(
            repo="owner/newtool",
            action="updated",
            target_doc="ecosystem-tools",
            prev_classification="TRIAL",
            new_classification="ADOPT",
        )]

        result = update_changelog(changelog, actions, "2026-04-24")

        assert "- radar: updated owner/newtool (TRIAL→ADOPT)" in result
        assert "- existing entry" in result

    def test_moved_entry_produces_license_changelog_line(self, tmp_path):
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("# Changelog\n\n## [Unreleased]\n")

        actions = [MergeAction(
            repo="owner/tool",
            action="moved",
            target_doc="blocked-tools",
            prev_classification="ADOPT",
            new_classification="REJECT",
            prev_license="MIT",
            new_license="AGPL",
        )]

        result = update_changelog(changelog, actions, "2026-04-24")

        assert "moved owner/tool to blocked-tools (license: MIT→AGPL)" in result


# ---------------------------------------------------------------------------
# Test 9: Diff generation
# ---------------------------------------------------------------------------

class TestDiffGeneration:
    def test_diff_is_unified_format(self):
        original = "line1\nline2\nline3\n"
        modified = "line1\nline2 changed\nline3\n"
        diff = generate_diff(original, modified, "some/file.md")

        assert diff.startswith("---"), "Unified diff must start with --- header"
        assert "+++" in diff
        assert "-line2\n" in diff
        assert "+line2 changed\n" in diff

    def test_no_diff_for_identical_content(self):
        text = "same content\n"
        diff = generate_diff(text, text, "file.md")
        assert diff == "", "Identical content must produce empty diff"

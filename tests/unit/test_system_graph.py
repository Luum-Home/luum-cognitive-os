"""Unit tests for lib/system_graph.py

Validates graph building, edge detection, risk calculation, formatting,
and the real-project integration test.

Python 3.9+ compatible.
"""

import json
from pathlib import Path

import pytest

from lib.system_graph import (
    Component,
    Edge,
    Layer,
    RelationType,
    SystemGraph,
    build_graph,
    calculate_risk,
    export_graph_json,
    find_hotspots,
    find_orphans,
    format_dependency_tree,
    format_full_graph_summary,
    get_affected_components,
    get_component_graph,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures: create minimal project structures for isolated tests
# ---------------------------------------------------------------------------


@pytest.fixture
def minimal_project(tmp_path):
    """Create a minimal project with rules, skills, hooks, libs."""
    # Rules
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "trust-score.md").write_text("# Trust Score\nAgent trust protocol.\n")
    (rules_dir / "acceptance-criteria.md").write_text("# Acceptance Criteria\nEvery prompt must have criteria.\n")
    (rules_dir / "RULES-COMPACT.md").write_text(
        "# Rules Compact\n- trust-score: Agent trust\n- acceptance-criteria: Prompt criteria\n"
    )

    # Skills
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    sdd_verify_dir = skills_dir / "sdd-verify"
    sdd_verify_dir.mkdir()
    (sdd_verify_dir / "SKILL.md").write_text(
        "# SDD Verify\nFollow trust-score rule. Check acceptance-criteria.\n"
    )
    other_skill_dir = skills_dir / "doc-sync"
    other_skill_dir.mkdir()
    (other_skill_dir / "SKILL.md").write_text("# Doc Sync\nSync documentation.\n")

    # CATALOG.md
    (skills_dir / "CATALOG.md").write_text(
        "# Catalog\n| sdd-verify | Verify | /sdd-verify |\n| doc-sync | Sync docs | /doc-sync |\n"
    )

    # Hooks
    hooks_dir = tmp_path / "hooks"
    hooks_dir.mkdir()
    (hooks_dir / "trust-score-validator.sh").write_text(
        '#!/bin/bash\n# CONCERNS: trust-score, quality\n'
        'source "$(dirname "$0")/_lib/common.sh"\n'
        '# Validates trust_score in agent output\n'
        'echo "metrics/trust-scores.jsonl"\n'
    )
    (hooks_dir / "confidence-gate.sh").write_text(
        '#!/bin/bash\n# CONCERNS: trust-score, confidence\n'
        '# Checks confidence gate based on trust score\n'
    )
    (hooks_dir / "error-pipeline.sh").write_text(
        '#!/bin/bash\n# CONCERNS: error-learning\n'
        '# Writes to metrics/error-learning.jsonl\n'
    )

    # _lib shared code
    lib_hooks_dir = hooks_dir / "_lib"
    lib_hooks_dir.mkdir()
    (lib_hooks_dir / "common.sh").write_text("#!/bin/bash\n# Shared utilities\n")

    # Libs
    lib_dir = tmp_path / "lib"
    lib_dir.mkdir()
    (lib_dir / "__init__.py").write_text("")
    (lib_dir / "agent_bus.py").write_text("# Agent bus module\nclass AgentBus:\n    pass\n")
    (lib_dir / "agent_dashboard.py").write_text(
        "# Dashboard\nfrom lib.agent_bus import AgentBus\n"
    )
    (lib_dir / "estimation_calibrator.py").write_text(
        "# Reads metrics/trust-scores.jsonl\ndef calibrate(): pass\n"
    )

    # .claude/settings.json
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    settings = {
        "hooks": {
            "PostToolUse": [
                {
                    "matcher": "Agent",
                    "hooks": [
                        {
                            "type": "command",
                            "command": 'bash "$CLAUDE_PROJECT_DIR/hooks/trust-score-validator.sh"',
                        },
                        {
                            "type": "command",
                            "command": 'bash "$CLAUDE_PROJECT_DIR/hooks/confidence-gate.sh"',
                        },
                    ],
                }
            ],
            "PostToolUse_Bash": [
                {
                    "matcher": "Bash",
                    "hooks": [
                        {
                            "type": "command",
                            "command": 'bash "$CLAUDE_PROJECT_DIR/hooks/error-pipeline.sh"',
                        }
                    ],
                }
            ],
        }
    }
    (claude_dir / "settings.json").write_text(json.dumps(settings, indent=2))

    # .claude/rules/cos/ symlinks
    rules_cos_dir = claude_dir / "rules" / "cos"
    rules_cos_dir.mkdir(parents=True)
    (rules_cos_dir / "trust-score.md").symlink_to(rules_dir / "trust-score.md")

    return tmp_path


# ---------------------------------------------------------------------------
# Test: Component discovery
# ---------------------------------------------------------------------------


class TestBuildGraphFindsComponents:
    """Tests that build_graph discovers components in each layer."""

    def test_build_graph_finds_rules(self, minimal_project):
        graph = build_graph(str(minimal_project))
        rule_names = [
            n for n, c in graph.components.items() if c.layer == Layer.RULES
        ]
        assert "trust-score" in rule_names
        assert "acceptance-criteria" in rule_names
        # RULES-COMPACT.md should not be a regular rule component
        assert "RULES-COMPACT" not in rule_names

    def test_build_graph_finds_skills(self, minimal_project):
        graph = build_graph(str(minimal_project))
        skill_names = [
            n for n, c in graph.components.items() if c.layer == Layer.SKILLS
        ]
        assert "sdd-verify" in skill_names
        assert "doc-sync" in skill_names

    def test_build_graph_finds_hooks(self, minimal_project):
        graph = build_graph(str(minimal_project))
        hook_names = [
            n for n, c in graph.components.items()
            if c.layer == Layer.HOOKS and not n.startswith("hooks/")
        ]
        assert "trust-score-validator" in hook_names
        assert "confidence-gate" in hook_names
        assert "error-pipeline" in hook_names

    def test_build_graph_finds_libs(self, minimal_project):
        graph = build_graph(str(minimal_project))
        lib_names = [
            n for n, c in graph.components.items() if c.layer == Layer.LIBS
        ]
        assert "agent_bus" in lib_names
        assert "agent_dashboard" in lib_names
        assert "estimation_calibrator" in lib_names

    def test_component_has_line_count(self, minimal_project):
        graph = build_graph(str(minimal_project))
        comp = graph.components["trust-score"]
        assert comp.lines > 0

    def test_component_has_relative_path(self, minimal_project):
        graph = build_graph(str(minimal_project))
        comp = graph.components["trust-score"]
        assert comp.path == "rules/trust-score.md"


# ---------------------------------------------------------------------------
# Test: Edge detection
# ---------------------------------------------------------------------------


class TestEdgeDetection:
    """Tests that edges between components are correctly detected."""

    def test_edge_enforces_detected(self, minimal_project):
        """Hook mentions rule name -> ENFORCES edge."""
        graph = build_graph(str(minimal_project))
        enforces_edges = [
            e for e in graph.edges
            if e.relation == RelationType.ENFORCES
            and e.source == "trust-score-validator"
            and e.target == "trust-score"
        ]
        assert len(enforces_edges) >= 1

    def test_edge_references_detected(self, minimal_project):
        """Skill mentions rule -> REFERENCES edge."""
        graph = build_graph(str(minimal_project))
        ref_edges = [
            e for e in graph.edges
            if e.relation == RelationType.REFERENCES
            and e.source == "sdd-verify"
            and e.target == "trust-score"
        ]
        assert len(ref_edges) >= 1

    def test_edge_writes_to_detected(self, minimal_project):
        """Hook writes to metrics -> WRITES_TO edge."""
        graph = build_graph(str(minimal_project))
        write_edges = [
            e for e in graph.edges
            if e.relation == RelationType.WRITES_TO
            and e.source == "trust-score-validator"
            and "trust-scores.jsonl" in e.target
        ]
        assert len(write_edges) >= 1

    def test_edge_sources_detected(self, minimal_project):
        """Hook sources _lib -> SOURCES edge."""
        graph = build_graph(str(minimal_project))
        source_edges = [
            e for e in graph.edges
            if e.relation == RelationType.SOURCES
            and e.source == "trust-score-validator"
        ]
        assert len(source_edges) >= 1

    def test_edge_registered_detected(self, minimal_project):
        """Hook in settings.json -> REGISTERED edge."""
        graph = build_graph(str(minimal_project))
        reg_edges = [
            e for e in graph.edges
            if e.relation == RelationType.REGISTERED
            and e.source == "trust-score-validator"
        ]
        assert len(reg_edges) >= 1

    def test_edge_cataloged_detected(self, minimal_project):
        """Skill in CATALOG.md -> CATALOGED edge."""
        graph = build_graph(str(minimal_project))
        cat_edges = [
            e for e in graph.edges
            if e.relation == RelationType.CATALOGED
            and e.source == "sdd-verify"
        ]
        assert len(cat_edges) >= 1

    def test_edge_compacted_detected(self, minimal_project):
        """Rule in RULES-COMPACT.md -> COMPACTED edge."""
        graph = build_graph(str(minimal_project))
        compact_edges = [
            e for e in graph.edges
            if e.relation == RelationType.COMPACTED
            and e.source == "trust-score"
        ]
        assert len(compact_edges) >= 1

    def test_edge_imports_detected(self, minimal_project):
        """Python lib imports another -> IMPORTS edge."""
        graph = build_graph(str(minimal_project))
        import_edges = [
            e for e in graph.edges
            if e.relation == RelationType.IMPORTS
            and e.source == "agent_dashboard"
            and e.target == "agent_bus"
        ]
        assert len(import_edges) >= 1

    def test_edge_symlinked_detected(self, minimal_project):
        """Symlink in .claude/rules/cos/ -> SYMLINKED edge."""
        graph = build_graph(str(minimal_project))
        sym_edges = [
            e for e in graph.edges
            if e.relation == RelationType.SYMLINKED
            and e.source == "trust-score"
        ]
        assert len(sym_edges) >= 1


# ---------------------------------------------------------------------------
# Test: get_component_graph
# ---------------------------------------------------------------------------


class TestGetComponentGraph:
    def test_get_component_graph_returns_edges(self, minimal_project):
        graph = build_graph(str(minimal_project))
        result = get_component_graph(graph, "trust-score")
        assert result["component"] is not None
        assert result["component"].name == "trust-score"
        # trust-score should have incoming edges (enforced by hooks, referenced by skills)
        assert len(result["incoming"]) > 0 or len(result["outgoing"]) > 0
        assert isinstance(result["layers_affected"], set)
        assert result["risk_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL", "UNKNOWN")


# ---------------------------------------------------------------------------
# Test: get_affected_components (transitive)
# ---------------------------------------------------------------------------


class TestGetAffectedComponents:
    def test_get_affected_components_transitive(self, minimal_project):
        """Changing trust-score should affect hooks, skills, and metrics."""
        graph = build_graph(str(minimal_project))
        affected = get_affected_components(graph, "rules/trust-score.md")
        assert "trust-score" in affected
        # The hook that enforces trust-score should be affected
        assert "trust-score-validator" in affected

    def test_affected_returns_empty_for_unknown_file(self, minimal_project):
        graph = build_graph(str(minimal_project))
        affected = get_affected_components(graph, "nonexistent/file.py")
        assert affected == []


# ---------------------------------------------------------------------------
# Test: Risk calculation
# ---------------------------------------------------------------------------


class TestRiskCalculation:
    def test_risk_low(self):
        """0-2 dependents -> LOW."""
        graph = SystemGraph()
        graph.components["isolated"] = Component(
            name="isolated", path="rules/isolated.md", layer=Layer.RULES
        )
        graph.components["dep1"] = Component(
            name="dep1", path="hooks/dep1.sh", layer=Layer.HOOKS
        )
        graph.edges.append(Edge(
            source="dep1", target="isolated",
            relation=RelationType.ENFORCES, evidence="test"
        ))
        risk, _ = calculate_risk(graph, "isolated")
        assert risk == "LOW"

    def test_risk_medium(self):
        """3-5 dependents -> MEDIUM."""
        graph = SystemGraph()
        graph.components["mid"] = Component(
            name="mid", path="rules/mid.md", layer=Layer.RULES
        )
        for i in range(4):
            dep_name = f"dep{i}"
            graph.components[dep_name] = Component(
                name=dep_name, path=f"hooks/{dep_name}.sh", layer=Layer.HOOKS
            )
            graph.edges.append(Edge(
                source=dep_name, target="mid",
                relation=RelationType.ENFORCES, evidence="test"
            ))
        risk, _ = calculate_risk(graph, "mid")
        assert risk == "MEDIUM"

    def test_risk_high(self):
        """6-10 dependents -> HIGH."""
        graph = SystemGraph()
        graph.components["hot"] = Component(
            name="hot", path="rules/hot.md", layer=Layer.RULES
        )
        for i in range(7):
            dep_name = f"dep{i}"
            graph.components[dep_name] = Component(
                name=dep_name, path=f"hooks/{dep_name}.sh", layer=Layer.HOOKS
            )
            graph.edges.append(Edge(
                source=dep_name, target="hot",
                relation=RelationType.ENFORCES, evidence="test"
            ))
        risk, _ = calculate_risk(graph, "hot")
        assert risk == "HIGH"

    def test_risk_critical_many_dependents(self):
        """10+ dependents -> CRITICAL."""
        graph = SystemGraph()
        graph.components["mega"] = Component(
            name="mega", path="rules/mega.md", layer=Layer.RULES
        )
        for i in range(12):
            dep_name = f"dep{i}"
            graph.components[dep_name] = Component(
                name=dep_name, path=f"hooks/{dep_name}.sh", layer=Layer.HOOKS
            )
            graph.edges.append(Edge(
                source=dep_name, target="mega",
                relation=RelationType.ENFORCES, evidence="test"
            ))
        risk, _ = calculate_risk(graph, "mega")
        assert risk == "CRITICAL"

    def test_risk_critical_cross_layer(self):
        """3+ layers -> CRITICAL even with fewer dependents."""
        graph = SystemGraph()
        graph.components["cross"] = Component(
            name="cross", path="rules/cross.md", layer=Layer.RULES
        )
        # Add deps from 3 different layers
        graph.components["skill1"] = Component(
            name="skill1", path="skills/skill1/SKILL.md", layer=Layer.SKILLS
        )
        graph.components["hook1"] = Component(
            name="hook1", path="hooks/hook1.sh", layer=Layer.HOOKS
        )
        graph.components["lib1"] = Component(
            name="lib1", path="lib/lib1.py", layer=Layer.LIBS
        )
        for dep in ["skill1", "hook1", "lib1"]:
            graph.edges.append(Edge(
                source=dep, target="cross",
                relation=RelationType.REFERENCES, evidence="test"
            ))
        risk, _ = calculate_risk(graph, "cross")
        # 3 dependents across 4 layers (rules + skills + hooks + libs) -> CRITICAL
        assert risk == "CRITICAL"

    def test_risk_unknown_component(self):
        graph = SystemGraph()
        risk, explanation = calculate_risk(graph, "nonexistent")
        assert risk == "UNKNOWN"
        assert "not found" in explanation


# ---------------------------------------------------------------------------
# Test: Formatting
# ---------------------------------------------------------------------------


class TestFormatting:
    def test_format_dependency_tree_has_ascii_art(self, minimal_project):
        graph = build_graph(str(minimal_project))
        tree = format_dependency_tree(graph, "trust-score")
        assert "trust-score" in tree
        assert "+--" in tree
        assert "IMPACT:" in tree
        assert "RISK:" in tree

    def test_format_dependency_tree_unknown_component(self, minimal_project):
        graph = build_graph(str(minimal_project))
        tree = format_dependency_tree(graph, "nonexistent")
        assert "not found" in tree

    def test_format_full_summary_has_counts(self, minimal_project):
        graph = build_graph(str(minimal_project))
        summary = format_full_graph_summary(graph)
        assert "Components:" in summary
        assert "Edges:" in summary
        assert "rules" in summary
        assert "skills" in summary
        assert "hooks" in summary
        assert "libs" in summary


# ---------------------------------------------------------------------------
# Test: Orphan detection
# ---------------------------------------------------------------------------


class TestOrphanDetection:
    def test_orphan_detection(self):
        """Component with no edges should be an orphan."""
        graph = SystemGraph()
        graph.components["connected"] = Component(
            name="connected", path="rules/connected.md", layer=Layer.RULES
        )
        graph.components["orphan"] = Component(
            name="orphan", path="rules/orphan.md", layer=Layer.RULES
        )
        graph.edges.append(Edge(
            source="hook1", target="connected",
            relation=RelationType.ENFORCES, evidence="test"
        ))
        orphans = find_orphans(graph)
        orphan_names = [o.name for o in orphans]
        assert "orphan" in orphan_names
        assert "connected" not in orphan_names


# ---------------------------------------------------------------------------
# Test: Hotspot detection
# ---------------------------------------------------------------------------


class TestHotspotDetection:
    def test_find_hotspots(self, minimal_project):
        """Components with many edges should appear as hotspots."""
        graph = build_graph(str(minimal_project))
        hotspots = find_hotspots(graph, min_edges=1)
        # There should be at least one hotspot
        assert len(hotspots) > 0
        # Each hotspot is (name, count, risk)
        name, count, risk = hotspots[0]
        assert isinstance(name, str)
        assert count >= 1
        assert risk in ("LOW", "MEDIUM", "HIGH", "CRITICAL", "UNKNOWN")


# ---------------------------------------------------------------------------
# Test: JSON export
# ---------------------------------------------------------------------------


class TestExportJSON:
    def test_export_json_valid(self, minimal_project):
        graph = build_graph(str(minimal_project))
        outfile = str(minimal_project / "graph.json")
        export_graph_json(graph, outfile)

        with open(outfile) as f:
            data = json.load(f)

        assert "nodes" in data
        assert "edges" in data
        assert "summary" in data
        assert len(data["nodes"]) > 0
        assert data["summary"]["total_components"] == len(data["nodes"])
        assert data["summary"]["total_edges"] == len(data["edges"])

        # Verify node structure
        node = data["nodes"][0]
        assert "id" in node
        assert "path" in node
        assert "layer" in node
        assert "layer_name" in node

        # Verify edge structure
        if data["edges"]:
            edge = data["edges"][0]
            assert "source" in edge
            assert "target" in edge
            assert "relation" in edge
            assert "evidence" in edge


# ---------------------------------------------------------------------------
# Test: Real project integration
# ---------------------------------------------------------------------------


class TestRealProjectGraph:
    """Integration test: run on the actual luum-agent-os codebase."""

    @pytest.fixture
    def real_project_root(self) -> str:
        """Get the real project root."""
        return str(Path(__file__).resolve().parent.parent.parent)

    def test_real_project_graph(self, real_project_root):
        """Build graph on actual codebase, verify >100 components."""
        graph = build_graph(real_project_root)

        # Should find a substantial number of components
        assert len(graph.components) > 100, (
            f"Expected >100 components, found {len(graph.components)}"
        )

        # Should find edges
        assert len(graph.edges) > 50, (
            f"Expected >50 edges, found {len(graph.edges)}"
        )

        # Should have components in multiple layers
        layers_found = {c.layer for c in graph.components.values()}
        assert Layer.RULES in layers_found
        assert Layer.SKILLS in layers_found
        assert Layer.HOOKS in layers_found
        assert Layer.LIBS in layers_found

        # Known components should exist
        assert "trust-score" in graph.components
        assert "acceptance-criteria" in graph.components

        # Summary should be non-empty
        summary = format_full_graph_summary(graph)
        assert "Components:" in summary
        assert len(summary) > 100

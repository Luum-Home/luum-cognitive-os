# scope: both
"""System Knowledge Graph — Dependency mapping across all Cognitive OS layers.

Scans the entire project to build a graph of components (rules, skills, hooks,
libs) and their relationships (enforces, references, writes_to, etc.).

Answers: "If I change component X, what else is affected?"

Python 3.9+ compatible. Stdlib only.
"""

import json
import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


class Layer(Enum):
    """The 5-layer architecture from architecture-principles.md."""
    RULES = 1
    SKILLS = 2
    HOOKS = 3
    LIBS = 4
    EXTERNALS = 5


class RelationType(Enum):
    """Types of relationships between components."""
    ENFORCES = "enforced_by"
    REFERENCES = "referenced_by"
    WRITES_TO = "writes_to"
    READS_FROM = "reads_from"
    SOURCES = "sources"
    SYMLINKED = "symlinked_to"
    IMPORTS = "imports"
    REGISTERED = "registered_in"
    CATALOGED = "cataloged_in"
    COMPACTED = "compacted_in"


# Display labels for relation types (for tree output)
_RELATION_LABELS = {
    RelationType.ENFORCES: "ENFORCED BY",
    RelationType.REFERENCES: "REFERENCED BY",
    RelationType.WRITES_TO: "WRITES TO",
    RelationType.READS_FROM: "READ BY",
    RelationType.SOURCES: "SOURCES",
    RelationType.SYMLINKED: "SYMLINKED",
    RelationType.IMPORTS: "IMPORTS",
    RelationType.REGISTERED: "REGISTERED IN",
    RelationType.CATALOGED: "CATALOGED IN",
    RelationType.COMPACTED: "COMPACTED IN",
}

# Reverse labels (for incoming edges displayed from the component's perspective)
_REVERSE_LABELS = {
    RelationType.ENFORCES: "ENFORCES",
    RelationType.REFERENCES: "REFERENCES",
    RelationType.WRITES_TO: "WRITTEN BY",
    RelationType.READS_FROM: "READS",
    RelationType.SOURCES: "SOURCED BY",
    RelationType.SYMLINKED: "SYMLINK OF",
    RelationType.IMPORTS: "IMPORTED BY",
    RelationType.REGISTERED: "REGISTERS",
    RelationType.CATALOGED: "CATALOGS",
    RelationType.COMPACTED: "COMPACTS",
}


@dataclass
class Component:
    """A node in the system graph."""
    name: str
    path: str
    layer: Layer
    concerns: List[str] = field(default_factory=list)
    lines: int = 0


@dataclass
class Edge:
    """A directed relationship between two components."""
    source: str       # component name
    target: str       # component name
    relation: RelationType
    evidence: str     # line/file where the relation was found


@dataclass
class SystemGraph:
    """The complete dependency graph of the system."""
    components: Dict[str, Component] = field(default_factory=dict)
    edges: List[Edge] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _count_lines(filepath: str) -> int:
    """Count lines in a file, returning 0 on error."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except (OSError, IOError):
        return 0


def _read_file(filepath: str) -> str:
    """Read file content, returning empty string on error."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except (OSError, IOError):
        return ""


def _extract_concerns(content: str) -> List[str]:
    """Extract CONCERNS tag from a hook file."""
    match = re.search(r"#\s*CONCERNS:\s*(.+)", content)
    if match:
        return [c.strip() for c in match.group(1).split(",")]
    return []


def _normalize_name(name: str) -> str:
    """Normalize a component name for matching.

    Converts underscores to hyphens and lowercases to enable fuzzy matching
    between rule names (kebab-case) and references in hook/skill files.
    """
    return name.lower().replace("_", "-").replace(" ", "-")


def _name_variations(name: str) -> List[str]:
    """Generate variations of a component name for grep-style matching.

    E.g. 'trust-score' -> ['trust-score', 'trust_score', 'trust score']
    """
    normalized = _normalize_name(name)
    return [
        normalized,
        normalized.replace("-", "_"),
        normalized.replace("-", " "),
    ]


# ---------------------------------------------------------------------------
# Scanners — each discovers components or edges
# ---------------------------------------------------------------------------

def _scan_rules(project_root: str, graph: SystemGraph) -> None:
    """Scan rules/*.md and register as Layer 1 components."""
    rules_dir = os.path.join(project_root, "rules")
    if not os.path.isdir(rules_dir):
        return

    for filename in sorted(os.listdir(rules_dir)):
        if not filename.endswith(".md"):
            continue
        if filename == "RULES-COMPACT.md":
            continue

        name = filename[:-3]  # strip .md
        filepath = os.path.join(rules_dir, filename)
        content = _read_file(filepath)

        graph.components[name] = Component(
            name=name,
            path=os.path.relpath(filepath, project_root),
            layer=Layer.RULES,
            lines=_count_lines(filepath),
        )


def _scan_skills(project_root: str, graph: SystemGraph) -> None:
    """Scan skills/*/SKILL.md and register as Layer 2 components."""
    skills_dir = os.path.join(project_root, "skills")
    if not os.path.isdir(skills_dir):
        return

    for entry in sorted(os.listdir(skills_dir)):
        skill_dir = os.path.join(skills_dir, entry)
        if not os.path.isdir(skill_dir):
            continue
        if entry.startswith("_") or entry == "auto-generated":
            continue

        skill_file = os.path.join(skill_dir, "SKILL.md")
        if not os.path.isfile(skill_file):
            continue

        graph.components[entry] = Component(
            name=entry,
            path=os.path.relpath(skill_file, project_root),
            layer=Layer.SKILLS,
            lines=_count_lines(skill_file),
        )


def _scan_hooks(project_root: str, graph: SystemGraph) -> None:
    """Scan hooks/*.sh and register as Layer 3 components."""
    hooks_dir = os.path.join(project_root, "hooks")
    if not os.path.isdir(hooks_dir):
        return

    for filename in sorted(os.listdir(hooks_dir)):
        if not filename.endswith(".sh"):
            continue
        if filename.startswith("_"):
            continue

        name = filename[:-3]  # strip .sh
        filepath = os.path.join(hooks_dir, filename)
        content = _read_file(filepath)
        concerns = _extract_concerns(content)

        graph.components[name] = Component(
            name=name,
            path=os.path.relpath(filepath, project_root),
            layer=Layer.HOOKS,
            concerns=concerns,
            lines=_count_lines(filepath),
        )


def _scan_libs(project_root: str, graph: SystemGraph) -> None:
    """Scan lib/*.py and register as Layer 4 components."""
    lib_dir = os.path.join(project_root, "lib")
    if not os.path.isdir(lib_dir):
        return

    for filename in sorted(os.listdir(lib_dir)):
        if not filename.endswith(".py"):
            continue
        if filename == "__init__.py":
            continue

        name = filename[:-3]  # strip .py
        filepath = os.path.join(lib_dir, filename)

        graph.components[name] = Component(
            name=name,
            path=os.path.relpath(filepath, project_root),
            layer=Layer.LIBS,
            lines=_count_lines(filepath),
        )


def _detect_enforces(project_root: str, graph: SystemGraph) -> None:
    """Detect ENFORCES edges: hooks that mention rule names."""
    hooks_dir = os.path.join(project_root, "hooks")
    if not os.path.isdir(hooks_dir):
        return

    rule_names = [
        name for name, comp in graph.components.items()
        if comp.layer == Layer.RULES
    ]

    for name, comp in list(graph.components.items()):
        if comp.layer != Layer.HOOKS:
            continue

        filepath = os.path.join(project_root, comp.path)
        content = _read_file(filepath).lower()
        if not content:
            continue

        for rule_name in rule_names:
            for variation in _name_variations(rule_name):
                if variation in content:
                    graph.edges.append(Edge(
                        source=name,
                        target=rule_name,
                        relation=RelationType.ENFORCES,
                        evidence=f"{comp.path} mentions '{variation}'",
                    ))
                    break  # one match per rule is enough


def _detect_references(project_root: str, graph: SystemGraph) -> None:
    """Detect REFERENCES edges: skills that mention rule or skill names."""
    rule_names = [
        name for name, comp in graph.components.items()
        if comp.layer == Layer.RULES
    ]
    skill_names = [
        name for name, comp in graph.components.items()
        if comp.layer == Layer.SKILLS
    ]

    for name, comp in list(graph.components.items()):
        if comp.layer != Layer.SKILLS:
            continue

        filepath = os.path.join(project_root, comp.path)
        content = _read_file(filepath).lower()
        if not content:
            continue

        # Skills referencing rules
        for rule_name in rule_names:
            for variation in _name_variations(rule_name):
                if variation in content:
                    graph.edges.append(Edge(
                        source=name,
                        target=rule_name,
                        relation=RelationType.REFERENCES,
                        evidence=f"{comp.path} mentions '{variation}'",
                    ))
                    break

        # Skills referencing other skills
        for skill_name in skill_names:
            if skill_name == name:
                continue
            for variation in _name_variations(skill_name):
                if variation in content:
                    graph.edges.append(Edge(
                        source=name,
                        target=skill_name,
                        relation=RelationType.REFERENCES,
                        evidence=f"{comp.path} mentions '{variation}'",
                    ))
                    break


def _detect_writes_to(project_root: str, graph: SystemGraph) -> None:
    """Detect WRITES_TO edges: hooks/libs that write to metrics files."""
    # Pattern matches things like: metrics/trust-scores.jsonl, .cognitive-os/metrics/foo.jsonl
    metrics_pattern = re.compile(
        r"""(?:metrics/|\.cognitive-os/metrics/)([a-zA-Z0-9_-]+\.jsonl)"""
    )

    # Snapshot the component list to avoid mutation during iteration
    components_snapshot = list(graph.components.items())
    new_components: Dict[str, Component] = {}

    for name, comp in components_snapshot:
        if comp.layer not in (Layer.HOOKS, Layer.LIBS):
            continue

        filepath = os.path.join(project_root, comp.path)
        content = _read_file(filepath)
        if not content:
            continue

        found_metrics: Set[str] = set()
        for match in metrics_pattern.finditer(content):
            metrics_file = f"metrics/{match.group(1)}"
            found_metrics.add(metrics_file)

        for metrics_file in sorted(found_metrics):
            # Register the metrics file as a pseudo-component if not exists
            if metrics_file not in graph.components and metrics_file not in new_components:
                new_components[metrics_file] = Component(
                    name=metrics_file,
                    path=f".cognitive-os/{metrics_file}",
                    layer=Layer.EXTERNALS,
                    lines=0,
                )
            graph.edges.append(Edge(
                source=name,
                target=metrics_file,
                relation=RelationType.WRITES_TO,
                evidence=f"{comp.path} writes to {metrics_file}",
            ))

    graph.components.update(new_components)


def _detect_reads_from(project_root: str, graph: SystemGraph) -> None:
    """Detect READS_FROM edges: libs/hooks that read metrics files."""
    # We look for patterns like open(...jsonl...) or reading from metrics paths
    # This is heuristic: if a lib/hook mentions a .jsonl file with read-like context
    metrics_pattern = re.compile(
        r"""(?:metrics/|\.cognitive-os/metrics/)([a-zA-Z0-9_-]+\.jsonl)"""
    )

    # Snapshot to avoid mutation during iteration
    components_snapshot = list(graph.components.items())
    new_components: Dict[str, Component] = {}

    for name, comp in components_snapshot:
        if comp.layer not in (Layer.LIBS, Layer.HOOKS):
            continue

        filepath = os.path.join(project_root, comp.path)
        content = _read_file(filepath)
        if not content:
            continue

        found_metrics: Set[str] = set()
        for match in metrics_pattern.finditer(content):
            metrics_file = f"metrics/{match.group(1)}"
            found_metrics.add(metrics_file)

        for metrics_file in sorted(found_metrics):
            # Only add READS_FROM if we didn't already add WRITES_TO for the same pair
            already_writes = any(
                e.source == name
                and e.target == metrics_file
                and e.relation == RelationType.WRITES_TO
                for e in graph.edges
            )
            if not already_writes:
                if metrics_file not in graph.components and metrics_file not in new_components:
                    new_components[metrics_file] = Component(
                        name=metrics_file,
                        path=f".cognitive-os/{metrics_file}",
                        layer=Layer.EXTERNALS,
                        lines=0,
                    )
                graph.edges.append(Edge(
                    source=name,
                    target=metrics_file,
                    relation=RelationType.READS_FROM,
                    evidence=f"{comp.path} reads {metrics_file}",
                ))

    graph.components.update(new_components)


def _detect_sources(project_root: str, graph: SystemGraph) -> None:
    """Detect SOURCES edges: hooks that source _lib/ files."""
    source_pattern = re.compile(r'source\s+["\']?.*?_lib/([a-zA-Z0-9_-]+\.sh)')

    # Snapshot to avoid mutation during iteration
    components_snapshot = list(graph.components.items())
    new_components: Dict[str, Component] = {}

    for name, comp in components_snapshot:
        if comp.layer != Layer.HOOKS:
            continue

        filepath = os.path.join(project_root, comp.path)
        content = _read_file(filepath)
        if not content:
            continue

        for match in source_pattern.finditer(content):
            lib_file = f"_lib/{match.group(1)}"
            lib_name = f"hooks/{lib_file}"
            if lib_name not in graph.components and lib_name not in new_components:
                lib_path = os.path.join(project_root, "hooks", lib_file)
                if os.path.isfile(lib_path):
                    new_components[lib_name] = Component(
                        name=lib_name,
                        path=f"hooks/{lib_file}",
                        layer=Layer.HOOKS,
                        lines=_count_lines(lib_path),
                    )
            if lib_name in graph.components or lib_name in new_components:
                graph.edges.append(Edge(
                    source=name,
                    target=lib_name,
                    relation=RelationType.SOURCES,
                    evidence=f"{comp.path} sources {lib_file}",
                ))

    graph.components.update(new_components)


def _detect_imports(project_root: str, graph: SystemGraph) -> None:
    """Detect IMPORTS edges: Python libs that import other libs."""
    lib_names = [
        name for name, comp in graph.components.items()
        if comp.layer == Layer.LIBS
    ]

    import_pattern = re.compile(
        r"(?:from\s+lib\.(\w+)\s+import|import\s+lib\.(\w+))"
    )

    for name, comp in graph.components.items():
        if comp.layer != Layer.LIBS:
            continue

        filepath = os.path.join(project_root, comp.path)
        content = _read_file(filepath)
        if not content:
            continue

        for match in import_pattern.finditer(content):
            imported = match.group(1) or match.group(2)
            if imported and imported != name and imported in lib_names:
                graph.edges.append(Edge(
                    source=name,
                    target=imported,
                    relation=RelationType.IMPORTS,
                    evidence=f"{comp.path} imports lib.{imported}",
                ))


def _detect_registered(project_root: str, graph: SystemGraph) -> None:
    """Detect REGISTERED edges: hooks registered in .claude/settings.json."""
    settings_path = os.path.join(project_root, ".claude", "settings.json")
    if not os.path.isfile(settings_path):
        return

    content = _read_file(settings_path)
    if not content:
        return

    try:
        settings = json.loads(content)
    except json.JSONDecodeError:
        return

    hooks_section = settings.get("hooks", {})
    for event_type, hook_groups in hooks_section.items():
        if not isinstance(hook_groups, list):
            continue
        for group in hook_groups:
            if not isinstance(group, dict):
                continue
            matcher = group.get("matcher", "")
            hook_list = group.get("hooks", [])
            for hook_entry in hook_list:
                if not isinstance(hook_entry, dict):
                    continue
                command = hook_entry.get("command", "")
                # Extract hook filename from command
                hook_match = re.search(r"hooks/([a-zA-Z0-9_-]+\.sh)", command)
                if hook_match:
                    hook_filename = hook_match.group(1)
                    hook_name = hook_filename[:-3]  # strip .sh
                    if hook_name in graph.components:
                        graph.edges.append(Edge(
                            source=hook_name,
                            target="settings.json",
                            relation=RelationType.REGISTERED,
                            evidence=f"{event_type}[{matcher or '*'}]: {hook_filename}",
                        ))

    # Register settings.json as a pseudo-component
    if "settings.json" not in graph.components:
        graph.components["settings.json"] = Component(
            name="settings.json",
            path=".claude/settings.json",
            layer=Layer.EXTERNALS,
            lines=_count_lines(settings_path),
        )


def _detect_cataloged(project_root: str, graph: SystemGraph) -> None:
    """Detect CATALOGED edges: skills listed in CATALOG.md."""
    catalog_path = os.path.join(project_root, "skills", "CATALOG.md")
    if not os.path.isfile(catalog_path):
        return

    content = _read_file(catalog_path).lower()
    if not content:
        return

    # Register CATALOG.md as a pseudo-component
    if "CATALOG.md" not in graph.components:
        graph.components["CATALOG.md"] = Component(
            name="CATALOG.md",
            path="skills/CATALOG.md",
            layer=Layer.SKILLS,
            lines=_count_lines(catalog_path),
        )

    for name, comp in graph.components.items():
        if comp.layer != Layer.SKILLS or name == "CATALOG.md":
            continue
        if name.lower() in content:
            graph.edges.append(Edge(
                source=name,
                target="CATALOG.md",
                relation=RelationType.CATALOGED,
                evidence=f"CATALOG.md lists '{name}'",
            ))


def _detect_compacted(project_root: str, graph: SystemGraph) -> None:
    """Detect COMPACTED edges: rules referenced in RULES-COMPACT.md."""
    compact_path = os.path.join(project_root, "rules", "RULES-COMPACT.md")
    if not os.path.isfile(compact_path):
        return

    content = _read_file(compact_path).lower()
    if not content:
        return

    # Register RULES-COMPACT.md as pseudo-component
    if "RULES-COMPACT.md" not in graph.components:
        graph.components["RULES-COMPACT.md"] = Component(
            name="RULES-COMPACT.md",
            path="rules/RULES-COMPACT.md",
            layer=Layer.RULES,
            lines=_count_lines(compact_path),
        )

    for name, comp in graph.components.items():
        if comp.layer != Layer.RULES or name == "RULES-COMPACT.md":
            continue
        if name.lower() in content:
            graph.edges.append(Edge(
                source=name,
                target="RULES-COMPACT.md",
                relation=RelationType.COMPACTED,
                evidence=f"RULES-COMPACT.md references '{name}'",
            ))


def _detect_symlinks(project_root: str, graph: SystemGraph) -> None:
    """Detect SYMLINKED edges: .claude/rules/cos/ symlinks to rules/."""
    symlink_dir = os.path.join(project_root, ".claude", "rules", "cos")
    if not os.path.isdir(symlink_dir):
        # Also check .claude/rules/ directly
        symlink_dir = os.path.join(project_root, ".claude", "rules")
        if not os.path.isdir(symlink_dir):
            return

    for filename in sorted(os.listdir(symlink_dir)):
        if not filename.endswith(".md"):
            continue

        filepath = os.path.join(symlink_dir, filename)
        if os.path.islink(filepath) or os.path.isfile(filepath):
            rule_name = filename[:-3]  # strip .md
            if rule_name in graph.components:
                rel_path = os.path.relpath(filepath, project_root)
                graph.edges.append(Edge(
                    source=rule_name,
                    target=rel_path,
                    relation=RelationType.SYMLINKED,
                    evidence=f"{rel_path} -> rules/{filename}",
                ))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_graph(project_root: str) -> SystemGraph:
    """Scan the entire project and build the dependency graph.

    Scans:
    - rules/*.md -> find references to hooks, skills, metrics files
    - skills/*/SKILL.md -> find references to rules, other skills
    - hooks/*.sh -> find: source _lib/, grep for rule names, metrics writes
    - lib/*.py -> find imports, file reads
    - .claude/settings.json -> hook registrations
    - skills/CATALOG.md -> skill listings
    - rules/RULES-COMPACT.md -> rule listings
    - .claude/rules/cos/ -> symlinks
    """
    graph = SystemGraph()

    # Phase 1: Discover components
    _scan_rules(project_root, graph)
    _scan_skills(project_root, graph)
    _scan_hooks(project_root, graph)
    _scan_libs(project_root, graph)

    # Phase 2: Discover edges
    _detect_enforces(project_root, graph)
    _detect_references(project_root, graph)
    _detect_writes_to(project_root, graph)
    _detect_reads_from(project_root, graph)
    _detect_sources(project_root, graph)
    _detect_imports(project_root, graph)
    _detect_registered(project_root, graph)
    _detect_cataloged(project_root, graph)
    _detect_compacted(project_root, graph)
    _detect_symlinks(project_root, graph)

    return graph


def get_component_graph(graph: SystemGraph, component_name: str) -> Dict:
    """Get all edges (incoming and outgoing) for a specific component.

    Returns:
        {
            "component": Component or None,
            "incoming": [Edge, ...],    # edges where target == component_name
            "outgoing": [Edge, ...],    # edges where source == component_name
            "layers_affected": set of Layer values,
            "risk_level": str,
            "risk_explanation": str,
        }
    """
    component = graph.components.get(component_name)

    incoming = [e for e in graph.edges if e.target == component_name]
    outgoing = [e for e in graph.edges if e.source == component_name]

    # Collect layers from all connected components
    layers_affected: Set[Layer] = set()
    if component:
        layers_affected.add(component.layer)
    for edge in incoming + outgoing:
        other = edge.source if edge.target == component_name else edge.target
        other_comp = graph.components.get(other)
        if other_comp:
            layers_affected.add(other_comp.layer)

    risk_level, risk_explanation = calculate_risk(graph, component_name)

    return {
        "component": component,
        "incoming": incoming,
        "outgoing": outgoing,
        "layers_affected": layers_affected,
        "risk_level": risk_level,
        "risk_explanation": risk_explanation,
    }


def get_affected_components(graph: SystemGraph, file_path: str) -> List[str]:
    """Given a file path, return all components that would be affected.

    Traverses the graph transitively: if A affects B and B affects C,
    returns [A, B, C].
    """
    # Find component by file path
    target_name: Optional[str] = None
    for name, comp in graph.components.items():
        if comp.path == file_path or file_path.endswith(comp.path):
            target_name = name
            break

    if target_name is None:
        # Try matching by filename without extension
        basename = os.path.basename(file_path)
        name_no_ext = os.path.splitext(basename)[0]
        if name_no_ext in graph.components:
            target_name = name_no_ext

    if target_name is None:
        return []

    # BFS to find all transitively affected components
    visited: Set[str] = set()
    queue = [target_name]

    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)

        # Find all components that depend on current
        for edge in graph.edges:
            if edge.target == current and edge.source not in visited:
                queue.append(edge.source)
            if edge.source == current and edge.target not in visited:
                queue.append(edge.target)

    return sorted(visited)


def calculate_risk(
    graph: SystemGraph, component_name: str
) -> Tuple[str, str]:
    """Calculate risk level of modifying a component.

    Returns (risk_level, explanation).

    LOW: 0-2 dependents
    MEDIUM: 3-5 dependents
    HIGH: 6-10 dependents
    CRITICAL: 10+ dependents or crosses 3+ layers
    """
    component = graph.components.get(component_name)
    if component is None:
        return ("UNKNOWN", f"Component '{component_name}' not found in graph")

    # Count unique components that depend on this one (incoming edges)
    dependents: Set[str] = set()
    for edge in graph.edges:
        if edge.target == component_name:
            dependents.add(edge.source)
        if edge.source == component_name:
            dependents.add(edge.target)

    # Count layers affected
    layers: Set[Layer] = {component.layer}
    for dep_name in dependents:
        dep_comp = graph.components.get(dep_name)
        if dep_comp:
            layers.add(dep_comp.layer)

    num_deps = len(dependents)
    num_layers = len(layers)

    if num_deps > 10 or num_layers >= 3:
        level = "CRITICAL"
        explanation = (
            f"{num_deps} dependents across {num_layers} layers. "
            f"Modification has wide blast radius."
        )
    elif num_deps >= 6:
        level = "HIGH"
        explanation = (
            f"{num_deps} dependents across {num_layers} layers. "
            f"Careful review recommended."
        )
    elif num_deps >= 3:
        level = "MEDIUM"
        explanation = (
            f"{num_deps} dependents across {num_layers} layers."
        )
    else:
        level = "LOW"
        explanation = (
            f"{num_deps} dependents. Well-isolated component."
        )

    return level, explanation


def format_dependency_tree(
    graph: SystemGraph, component_name: str, max_depth: int = 3
) -> str:
    """Format a component's dependencies as an ASCII tree.

    Example output:

    trust-score (Layer 1 -- RULES)
    +-- ENFORCED BY: trust-score-validator (Layer 3)
    |   +-- WRITES TO: metrics/trust-scores.jsonl
    +-- ENFORCED BY: confidence-gate (Layer 3)
    +-- REFERENCED BY: sdd-verify (Layer 2)
    +-- COMPACTED IN: RULES-COMPACT.md
    +-- SYMLINKED: .claude/rules/cos/trust-score.md

    IMPACT: 6 components across 3 layers
    RISK: HIGH
    """
    component = graph.components.get(component_name)
    if component is None:
        return f"Component '{component_name}' not found in graph."

    lines: List[str] = []
    layer_label = component.layer.name
    lines.append(f"{component_name} (Layer {component.layer.value} -- {layer_label})")

    # Collect outgoing edges (things this component connects to)
    outgoing = [e for e in graph.edges if e.source == component_name]
    # Collect incoming edges (things that connect to this component)
    incoming = [e for e in graph.edges if e.target == component_name]

    all_edges: List[Tuple[str, str, str]] = []

    # Format incoming edges (show as "ENFORCED BY: X", "REFERENCED BY: X", etc.)
    for edge in incoming:
        label = _RELATION_LABELS.get(edge.relation, edge.relation.value.upper())
        other = edge.source
        other_comp = graph.components.get(other)
        layer_info = ""
        if other_comp:
            layer_info = f" (Layer {other_comp.layer.value})"
        all_edges.append((label, f"{other}{layer_info}", other))

    # Format outgoing edges
    for edge in outgoing:
        label = _RELATION_LABELS.get(edge.relation, edge.relation.value.upper())
        other = edge.target
        other_comp = graph.components.get(other)
        layer_info = ""
        if other_comp:
            layer_info = f" (Layer {other_comp.layer.value})"
        all_edges.append((label, f"{other}{layer_info}", other))

    # Deduplicate
    seen: Set[str] = set()
    unique_edges: List[Tuple[str, str, str]] = []
    for label, display, other_name in all_edges:
        key = f"{label}:{other_name}"
        if key not in seen:
            seen.add(key)
            unique_edges.append((label, display, other_name))

    # Render tree
    for i, (label, display, other_name) in enumerate(unique_edges):
        is_last = i == len(unique_edges) - 1
        connector = "+-- " if not is_last else "+-- "
        prefix = "|   " if not is_last else "    "
        lines.append(f"{connector}{label}: {display}")

        # Sub-edges (depth 2) for the connected component
        if max_depth > 1:
            sub_outgoing = [
                e for e in graph.edges
                if e.source == other_name and e.target != component_name
            ]
            sub_incoming = [
                e for e in graph.edges
                if e.target == other_name and e.source != component_name
            ]
            sub_edges = sub_outgoing[:3] + sub_incoming[:3]  # limit
            for j, sub_edge in enumerate(sub_edges):
                sub_label = _RELATION_LABELS.get(
                    sub_edge.relation, sub_edge.relation.value.upper()
                )
                sub_other = (
                    sub_edge.target
                    if sub_edge.source == other_name
                    else sub_edge.source
                )
                sub_is_last = j == len(sub_edges) - 1
                sub_connector = "+-- " if not sub_is_last else "+-- "
                lines.append(f"{prefix}{sub_connector}{sub_label}: {sub_other}")

    # Summary
    affected = get_affected_components(graph, component.path)
    risk_level, _ = calculate_risk(graph, component_name)

    # Count layers from affected
    affected_layers: Set[int] = set()
    for a in affected:
        ac = graph.components.get(a)
        if ac:
            affected_layers.add(ac.layer.value)

    lines.append("")
    lines.append(f"IMPACT: {len(affected)} components across {len(affected_layers)} layers")
    lines.append(f"RISK: {risk_level}")

    return "\n".join(lines)


def format_full_graph_summary(graph: SystemGraph) -> str:
    """Summary of the entire system graph."""
    # Count by layer
    counts: Dict[str, int] = defaultdict(int)
    for comp in graph.components.values():
        counts[comp.layer.name] += 1

    # Find most connected
    edge_counts: Dict[str, int] = defaultdict(int)
    for edge in graph.edges:
        edge_counts[edge.source] += 1
        edge_counts[edge.target] += 1

    most_connected = sorted(
        edge_counts.items(), key=lambda x: -x[1]
    )[:5]

    # Find orphans (no edges at all)
    all_in_edges = {name for name in graph.components if name not in edge_counts}
    orphans = sorted(all_in_edges)

    # Cross-layer edges
    cross_layer = 0
    for edge in graph.edges:
        s_comp = graph.components.get(edge.source)
        t_comp = graph.components.get(edge.target)
        if s_comp and t_comp and s_comp.layer != t_comp.layer:
            cross_layer += 1

    # Components with >10 dependents
    high_dep = [
        (name, count) for name, count in edge_counts.items() if count > 10
    ]

    total = len(graph.components)
    rules = counts.get("RULES", 0)
    skills = counts.get("SKILLS", 0)
    hooks = counts.get("HOOKS", 0)
    libs = counts.get("LIBS", 0)
    externals = counts.get("EXTERNALS", 0)

    lines = [
        "System Knowledge Graph Summary:",
        f"+-- Components: {total} ({rules} rules, {skills} skills, {hooks} hooks, {libs} libs, {externals} externals)",
        f"+-- Edges: {len(graph.edges)} connections",
    ]

    if most_connected:
        top_name, top_count = most_connected[0]
        lines.append(f"+-- Most connected: {top_name} ({top_count} edges)")

    lines.append(f"+-- Orphans: {len(orphans)} (no incoming or outgoing edges)")
    lines.append(f"+-- Cross-layer edges: {cross_layer}")
    lines.append(f"+-- Potential issues: {len(high_dep)} components with >10 dependents")

    if orphans:
        lines.append("")
        lines.append("Orphan components:")
        for o in orphans[:10]:
            comp = graph.components.get(o)
            layer = comp.layer.name if comp else "?"
            lines.append(f"  - {o} ({layer})")
        if len(orphans) > 10:
            lines.append(f"  ... and {len(orphans) - 10} more")

    if high_dep:
        lines.append("")
        lines.append("High-dependency hotspots:")
        for name, count in sorted(high_dep, key=lambda x: -x[1])[:10]:
            comp = graph.components.get(name)
            layer = comp.layer.name if comp else "?"
            risk, _ = calculate_risk(graph, name)
            lines.append(f"  - {name} ({layer}): {count} edges [{risk}]")

    return "\n".join(lines)


def find_orphans(graph: SystemGraph) -> List[Component]:
    """Find components with no incoming or outgoing edges."""
    connected: Set[str] = set()
    for edge in graph.edges:
        connected.add(edge.source)
        connected.add(edge.target)

    orphans = []
    for name, comp in graph.components.items():
        if name not in connected:
            orphans.append(comp)

    return sorted(orphans, key=lambda c: (c.layer.value, c.name))


def find_hotspots(graph: SystemGraph, min_edges: int = 5) -> List[Tuple[str, int, str]]:
    """Find components with the most connections (highest risk).

    Returns list of (name, edge_count, risk_level) sorted by edge count desc.
    """
    edge_counts: Dict[str, int] = defaultdict(int)
    for edge in graph.edges:
        edge_counts[edge.source] += 1
        edge_counts[edge.target] += 1

    hotspots = []
    for name, count in edge_counts.items():
        if count >= min_edges:
            risk, _ = calculate_risk(graph, name)
            hotspots.append((name, count, risk))

    return sorted(hotspots, key=lambda x: -x[1])


def export_graph_json(graph: SystemGraph, filepath: str) -> None:
    """Export graph as JSON for visualization tools."""
    nodes = []
    for name, comp in graph.components.items():
        nodes.append({
            "id": name,
            "name": name,
            "path": comp.path,
            "layer": comp.layer.value,
            "layer_name": comp.layer.name,
            "concerns": comp.concerns,
            "lines": comp.lines,
        })

    edges = []
    for edge in graph.edges:
        edges.append({
            "source": edge.source,
            "target": edge.target,
            "relation": edge.relation.value,
            "relation_type": edge.relation.name,
            "evidence": edge.evidence,
        })

    data = {
        "nodes": nodes,
        "edges": edges,
        "summary": {
            "total_components": len(nodes),
            "total_edges": len(edges),
            "layers": {
                layer.name: sum(1 for n in nodes if n["layer"] == layer.value)
                for layer in Layer
            },
        },
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ---------------------------------------------------------------------------
# CLI entry point (for subprocess calls from Go)
# ---------------------------------------------------------------------------

def _cli_main() -> None:
    """Entry point for command-line usage."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m lib.system_graph <command> [args]")
        print("Commands: tree <component>, affected <file>, summary, orphans, hotspots, json <outfile>")
        sys.exit(1)

    # Find project root (parent of lib/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    command = sys.argv[1]
    graph = build_graph(project_root)

    if command == "tree":
        if len(sys.argv) < 3:
            print("Usage: python -m lib.system_graph tree <component-name>")
            sys.exit(1)
        component = sys.argv[2]
        print(format_dependency_tree(graph, component))

    elif command == "affected":
        if len(sys.argv) < 3:
            print("Usage: python -m lib.system_graph affected <file-path>")
            sys.exit(1)
        file_path = sys.argv[2]
        affected = get_affected_components(graph, file_path)
        if affected:
            print(f"Affected components ({len(affected)}):")
            for a in affected:
                comp = graph.components.get(a)
                layer = comp.layer.name if comp else "?"
                print(f"  - {a} ({layer})")
        else:
            print(f"No components found matching '{file_path}'")

    elif command == "summary":
        print(format_full_graph_summary(graph))

    elif command == "orphans":
        orphans = find_orphans(graph)
        if orphans:
            print(f"Orphan components ({len(orphans)}):")
            for o in orphans:
                print(f"  - {o.name} ({o.layer.name}) @ {o.path}")
        else:
            print("No orphan components found.")

    elif command == "hotspots":
        hotspots = find_hotspots(graph)
        if hotspots:
            print(f"Hotspot components ({len(hotspots)}):")
            for name, count, risk in hotspots:
                print(f"  - {name}: {count} edges [{risk}]")
        else:
            print("No hotspots found (all components have <5 edges).")

    elif command == "json":
        if len(sys.argv) < 3:
            print("Usage: python -m lib.system_graph json <output-file>")
            sys.exit(1)
        outfile = sys.argv[2]
        export_graph_json(graph, outfile)
        print(f"Graph exported to {outfile}")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    _cli_main()

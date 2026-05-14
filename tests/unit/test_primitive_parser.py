from pathlib import Path

from lib.primitive_parser import detect_primitive_kind, parse_primitive_file


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_parse_skill_contract_with_frontmatter(tmp_path: Path) -> None:
    path = write(
        tmp_path / "skills" / "code-review" / "SKILL.md",
        """---
name: code-review
version: 1.0.0
description: Review any repository with evidence.
audience: both
triggers: [review, evidence]
---
<!-- SCOPE: both -->
# Code Review

Use for code review in any repo.
""",
    )

    contract = parse_primitive_file(path, tmp_path)

    assert contract.kind == "skill"
    assert contract.scope_marker == "both"
    assert contract.title == "Code Review"
    assert contract.audience == "both"
    assert contract.activation.mode == "contextual"
    assert contract.activation.triggers == ("review", "evidence")
    assert contract.structural_findings == ()
    assert "repo-agnostic-language" in contract.semantic_hints


def test_parse_skill_scope_marker_after_long_frontmatter(tmp_path: Path) -> None:
    path = write(
        tmp_path / "skills" / "add-hook" / "SKILL.md",
        """---
name: add-hook
version: 0.1.0
description: Add a Cognitive OS hook.
audience: os
tags:
- hooks
platforms:
- claude-code
prerequisites: []
routing_patterns:
- pattern: add-hook
  confidence: 0.95
summary_line: Add a Cognitive OS hook.
triggers:
- add-hook
- new hook
routing_intents:
- intent: add_hook_request
  description: User asks to add a hook.
  confidence: 0.85
---
<!-- SCOPE: os-only -->

# Add Hook
""",
    )

    contract = parse_primitive_file(path, tmp_path)

    assert contract.scope_marker == "os-only"
    assert contract.structural_findings == ()


def test_parse_package_skill_is_skill_surface(tmp_path: Path) -> None:
    path = write(
        tmp_path / "packages" / "agent" / "skills" / "wiki-ingest" / "SKILL.md",
        """---
name: wiki-ingest
version: 1.0.0
description: Ingest project wiki pages.
triggers: wiki
---
<!-- SCOPE: project -->
# Wiki Ingest
""",
    )

    contract = parse_primitive_file(path, tmp_path)

    assert detect_primitive_kind(path, tmp_path) == "skill"
    assert contract.kind == "skill"
    assert contract.scope_marker == "project"
    assert "package-primitive-surface" in contract.semantic_hints


def test_parse_package_hook_is_hook_surface(tmp_path: Path) -> None:
    path = write(
        tmp_path / "packages" / "adaptive-workflow" / "hooks" / "adaptive-bypass.sh",
        """#!/usr/bin/env bash
# SCOPE: both
# PreToolUse hook.
echo ok
""",
    )

    contract = parse_primitive_file(path, tmp_path)

    assert contract.kind == "hook"
    assert contract.is_primitive is True
    assert contract.scope_marker == "both"
    assert contract.activation.mode == "event"


def test_parse_support_files_are_not_primitives(tmp_path: Path) -> None:
    archived = write(tmp_path / "hooks" / "_archived" / "old.sh.bak", "# no scope\n")
    allowlist = write(tmp_path / "hooks" / "_lib" / "registration-allowlist.txt", "# names\n")
    script_lib = write(tmp_path / "scripts" / "_lib" / "local-service.sh", "#!/usr/bin/env bash\n")

    assert parse_primitive_file(archived, tmp_path).is_primitive is False
    assert parse_primitive_file(allowlist, tmp_path).kind == "support"
    assert parse_primitive_file(script_lib, tmp_path).kind == "script-lib"
    assert parse_primitive_file(script_lib, tmp_path).is_primitive is False


def test_parse_rule_index_has_always_activation(tmp_path: Path) -> None:
    path = write(
        tmp_path / "rules" / "RULES-COMPACT.md",
        """<!-- SCOPE: both -->
# COS Rules Index

## Always Active
""",
    )

    contract = parse_primitive_file(path, tmp_path)

    assert contract.kind == "rule-index"
    assert contract.activation.mode == "always"
    assert contract.structural_findings == ()


def test_rule_markdown_contract_does_not_require_yaml(tmp_path: Path) -> None:
    path = write(
        tmp_path / "rules" / "recommendation-grounding.md",
        """<!-- SCOPE: both -->
# Recommendation Grounding

## Purpose

Ground recommendations in evidence for any repository.

## Contextual Trigger

- recommendation
- evidence
""",
    )

    contract = parse_primitive_file(path, tmp_path)

    assert contract.kind == "rule"
    assert contract.frontmatter == {}
    assert "frontmatter" not in "\n".join(contract.structural_findings)
    assert contract.activation.mode == "contextual"
    assert contract.activation.triggers == ("recommendation", "evidence")
    assert contract.structural_findings == ()


def test_rule_reports_missing_contract_parts(tmp_path: Path) -> None:
    path = write(tmp_path / "rules" / "thin.md", "# Thin\n\nBody only.\n")

    contract = parse_primitive_file(path, tmp_path)

    assert contract.kind == "rule"
    assert "rule-missing-scope-marker" in contract.structural_findings
    assert "rule-missing-opening-section" in contract.structural_findings
    assert "rule-missing-contextual-trigger" in contract.structural_findings


def test_hook_uses_event_activation_not_contextual_trigger(tmp_path: Path) -> None:
    path = write(
        tmp_path / "hooks" / "post-tool-validate.sh",
        """#!/usr/bin/env bash
# SCOPE: os-only
# Handles PostToolUse validation for Cognitive OS.
echo ok
""",
    )

    contract = parse_primitive_file(path, tmp_path)

    assert contract.kind == "hook"
    assert contract.scope_marker == "os-only"
    assert contract.activation.mode == "event"
    assert "PostToolUse" in contract.activation.triggers
    assert "hook-missing-scope-marker" not in contract.structural_findings


def test_script_and_template_contracts(tmp_path: Path) -> None:
    script = write(
        tmp_path / "scripts" / "cos-check.py",
        """#!/usr/bin/env python3
# SCOPE: os-only
\"\"\"Check manifests/ for drift.\"\"\"
""",
    )
    template = write(
        tmp_path / "templates" / "agent-preamble.md",
        """<!-- SCOPE: both -->
# Agent Preamble

Hello {{name}} for any repository.
""",
    )

    script_contract = parse_primitive_file(script, tmp_path)
    template_contract = parse_primitive_file(template, tmp_path)

    assert script_contract.kind == "script"
    assert script_contract.activation.mode == "manual"
    assert "cos-maintainer-command-name" in script_contract.semantic_hints
    assert "os-internal-reference" in script_contract.semantic_hints
    assert template_contract.kind == "template"
    assert template_contract.activation.mode == "template"
    assert "template-placeholders" in template_contract.semantic_hints
    assert "repo-agnostic-language" in template_contract.semantic_hints


def test_template_scope_can_come_from_structure_manifest(tmp_path: Path) -> None:
    manifest = tmp_path / "manifests" / "primitive-structure-scopes.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        """schema_version: primitive-structure-scopes/v1
items:
- path: templates/project-templates/typescript/package.json.tmpl
  scope: project
  rationale: JSON cannot carry comments safely.
""",
        encoding="utf-8",
    )
    template = write(
        tmp_path / "templates" / "project-templates" / "typescript" / "package.json.tmpl",
        '{"name": "{{.ProjectName}}"}\n',
    )

    contract = parse_primitive_file(template, tmp_path)

    assert contract.kind == "template"
    assert contract.scope_marker == "project"
    assert contract.structural_findings == ()


def test_scope_parser_ignores_prose_scope_colon(tmp_path: Path) -> None:
    path = write(
        tmp_path / "rules" / "scope-prose.md",
        """# Scope Prose

This sentence says scope: both in prose, but it is not a marker.
""",
    )

    contract = parse_primitive_file(path, tmp_path)

    assert contract.scope_marker is None
    assert "rule-missing-scope-marker" in contract.structural_findings


def test_skill_scope_can_come_from_yaml_frontmatter(tmp_path: Path) -> None:
    path = write(
        tmp_path / "skills" / "deep-tool-research" / "SKILL.md",
        """---
name: deep-tool-research
version: 1.0.0
description: Deep tool research.
scope: both
triggers: [deep-tool-research]
---
# Deep Tool Research
""",
    )

    contract = parse_primitive_file(path, tmp_path)

    assert contract.scope_marker == "both"

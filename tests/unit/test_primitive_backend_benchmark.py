from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "primitive_backend_benchmark.py"
spec = importlib.util.spec_from_file_location("primitive_backend_benchmark", MODULE_PATH)
assert spec and spec.loader
primitive_backend_benchmark = importlib.util.module_from_spec(spec)
sys.modules["primitive_backend_benchmark"] = primitive_backend_benchmark
spec.loader.exec_module(primitive_backend_benchmark)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def seed_candidate(base: Path, dirname: str, *, license_text: str, readme: str, package: str = "") -> None:
    write(base / dirname / "LICENSE", license_text)
    write(base / dirname / "README.md", readme)
    if package:
        write(base / dirname / "pyproject.toml", package)


def seed_all_candidates(base: Path) -> None:
    seed_candidate(
        base,
        "qartez-mcp",
        license_text="Qartez MCP Dual License Commercial License Small Team License",
        readme="MCP code intelligence tree-sitter references blast radius cuts AI token usage by ~94% JSON tools local index",
        package='[project]\nname = "qartez-mcp"\nversion = "0.9.9"\n',
    )
    seed_candidate(
        base,
        "jcodemunch-mcp",
        license_text="Dual-Use License NON-COMMERCIAL USE COMMERCIAL USE PAID LICENSE REQUIRED",
        readme="MCP token-efficient source exploration via tree-sitter symbols compact JSON local CLI 95% token usage",
        package='[project]\nname = "jcodemunch-mcp"\nversion = "1.80.3"\n',
    )
    seed_candidate(
        base,
        "repowise",
        license_text="GNU AFFERO GENERAL PUBLIC LICENSE Version 3",
        readme="MCP dependency graph git history documentation wiki architectural decisions docs local index 27x fewer tokens",
        package='[project]\nname = "repowise"\nversion = "0.4.1"\nlicense = "AGPL-3.0-only"\n',
    )
    seed_candidate(
        base,
        "CodeGraphContext",
        license_text="MIT License Permission is hereby granted",
        readme="MCP Turn code repositories into a queryable graph for AI agents local CLI tree-sitter code graph references",
        package='[project]\nname = "codegraphcontext"\nversion = "0.4.5"\n',
    )


def test_classify_license_blocks_agpl_and_allows_mit() -> None:
    classify = primitive_backend_benchmark.classify_license

    assert classify("GNU AFFERO GENERAL PUBLIC LICENSE", "")[0] == "blocked"
    assert classify("MIT License", "")[1] is True
    kind, compatible, notes = classify("Dual-Use License. Commercial License required.", "")
    assert kind == "review-required"
    assert compatible is False
    assert "approval" in notes


def test_evaluate_candidate_scores_codegraphcontext_as_compatible_adapter(tmp_path: Path) -> None:
    seed_all_candidates(tmp_path)

    result = primitive_backend_benchmark.evaluate_candidate("codegraphcontext", tmp_path)

    assert result.license_kind == "compatible"
    assert result.license_compatible is True
    assert result.answers["local_offline"].answer == "yes"
    assert result.answers["adapter_fit"].answer == "yes"
    assert result.answers["first_class_primitives"].answer == "no"


def test_evaluate_candidate_keeps_repowise_eval_only_when_agpl(tmp_path: Path) -> None:
    seed_all_candidates(tmp_path)

    result = primitive_backend_benchmark.evaluate_candidate("repowise", tmp_path)

    assert result.license_kind == "blocked"
    assert result.license_compatible is False
    assert result.recommendation == "evaluate-only-license-blocked"
    assert result.answers["stale_docs"].answer == "yes"


def test_main_writes_json_and_markdown_reports(tmp_path: Path) -> None:
    candidates = tmp_path / "candidates"
    project = tmp_path / "project"
    seed_all_candidates(candidates)
    write(project / "skills" / "demo" / "SKILL.md", "# Demo skill")
    write(project / "docs" / "reports" / "primitive-coverage-latest.md", "# Compact evidence")

    exit_code = primitive_backend_benchmark.main(
        [
            "--candidates-dir",
            str(candidates),
            "--project-dir",
            str(project),
            "--json-out",
            "docs/06-Daily/reports/bench.json",
            "--markdown-out",
            "docs/06-Daily/reports/bench.md",
        ]
    )

    assert exit_code == 0
    data = json.loads((project / "docs/06-Daily/reports/bench.json").read_text(encoding="utf-8"))
    assert {candidate["name"] for candidate in data["candidates"]} == {
        "qartez",
        "jcodemunch",
        "repowise",
        "codegraphcontext",
    }
    assert data["token_baseline"]["repo_text_bytes"] > 0
    markdown = (project / "docs/06-Daily/reports/bench.md").read_text(encoding="utf-8")
    assert "Primitive Coverage Backend Benchmark" in markdown
    assert "CodeGraphContext" in markdown or "codegraphcontext" in markdown

from __future__ import annotations

from pathlib import Path

import yaml

from lib.cross_stack_adoption_truth import build_report, normalize_name


def _write_fixture(project: Path) -> None:
    (project / "manifests").mkdir()
    (project / "docs" / "business").mkdir(parents=True)
    (project / "pyproject.toml").write_text('[project]\ndependencies = ["requests>=2", "untracked-lib==1"]\n', encoding="utf-8")
    (project / "package.json").write_text('{"dependencies":{"left-pad":"1.3.0"}}', encoding="utf-8")
    (project / "go.mod").write_text('module example.com/app\n\nrequire github.com/acme/go-lib v1.0.0\n', encoding="utf-8")
    (project / "NOTICE").write_text('requests\nLicensed under Apache-2.0\n\nGhostLib\nLicensed under MIT\n', encoding="utf-8")
    (project / "docs" / "component-sources.md").write_text(
        '| Source | URL | License | Components | Status |\n'
        '|---|---|---|---|---|\n'
        '| requests | https://example.com/requests | Apache-2.0 | HTTP | ACTIVE -- used |\n'
        '| PlannedTool | https://example.com/planned | MIT | Future feature | PLANNED -- roadmap |\n'
        '| WatchTool | https://example.com/watch | MIT | Watch feature | WATCH -- not integrated |\n',
        encoding="utf-8",
    )
    (project / "docs" / "business" / "pitch.md").write_text('We use watchtool for routing. PlannedTool dashboard is included.\n', encoding="utf-8")
    (project / "manifests" / "cross-stack-adoption-truth.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "cross-stack-adoption-truth/v1",
                "sources": {
                    "python_pyproject_globs": ["pyproject.toml"],
                    "node_package_json_globs": ["package.json"],
                    "go_mod_globs": ["go.mod"],
                    "notice": "NOTICE",
                    "component_sources": "docs/component-sources.md",
                    "external_inventory_globs": [],
                    "marketing_doc_globs": ["docs/business/*.md"],
                },
                "allowlists": {"transitive_only": ["left-pad"], "notice_optional": []},
                "strict_block_verdicts": ["DEAD_IN_NOTICE", "ASPIRATIONAL_PLANNED", "OVERCLAIMED"],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_normalize_name_handles_urls_and_extras() -> None:
    assert normalize_name("requests[security]") == "requests"
    assert normalize_name("github.com/acme/go-lib") == "go-lib"


def test_adoption_truth_classifies_core_verdicts(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    report = build_report(tmp_path, strict=True)
    by_name = {row["name"]: row for row in report["rows"]}
    assert by_name["requests"]["adoption_verdict"] == "INTEGRATED"
    assert by_name["untracked-lib"]["adoption_verdict"] == "INTEGRATED_UNTRACKED"
    assert by_name["ghostlib"]["adoption_verdict"] == "DEAD_IN_NOTICE"
    assert by_name["plannedtool"]["adoption_verdict"] == "ASPIRATIONAL_PLANNED"
    assert by_name["watchtool"]["adoption_verdict"] == "OVERCLAIMED"
    assert by_name["left-pad"]["adoption_verdict"] == "NOT_APPLICABLE"
    assert report["status"] == "block"

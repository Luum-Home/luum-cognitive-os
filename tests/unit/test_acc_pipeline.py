from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import yaml

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "acc_pipeline.py"
spec = importlib.util.spec_from_file_location("acc_pipeline", MODULE_PATH)
assert spec and spec.loader
acc_pipeline = importlib.util.module_from_spec(spec)
sys.modules["acc_pipeline"] = acc_pipeline
spec.loader.exec_module(acc_pipeline)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def make_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "docs" / "reports").mkdir(parents=True)
    (root / "manifests").mkdir(parents=True)
    (root / "cognitive-os.yaml").write_text(yaml.safe_dump({"project": {"phase": "reconstruction"}}))
    (root / "manifests" / "harness-projection.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "harness-projection.v1",
                "harnesses": [
                    {"id": "claude", "display_name": "Claude Code", "status": "implemented", "projection_mode": "native-settings"},
                    {"id": "cursor", "display_name": "Cursor", "status": "planned", "projection_mode": "ide-rules-or-wrapper"},
                ],
            }
        )
    )
    (root / "manifests" / "primitive-projection-profiles.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "primitive-projection-profiles.v1",
                "profiles": {
                    "default": {"description": "default profile"},
                    "full": {"description": "full profile"},
                },
                "projection_classes": {
                    "shared": {},
                    "default": {},
                    "full": {},
                    "profile-driver": {},
                    "maintainer-only": {},
                },
                "profile_driver_scripts": [
                    {"path": "scripts/projected.sh", "class": "profile-driver", "source_manifest": "test"},
                ],
            }
        )
    )
    (root / "manifests" / "primitive-consumer-availability.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "primitive-consumer-availability.v1",
                "items": [
                    {
                        "path": "scripts/local.py",
                        "status": "maintainer-only",
                        "rationale": "test maintainer override",
                    }
                ],
            }
        )
    )
    (root / "manifests" / "shell-ci-projection.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "shell-ci-projection.v1",
                "profiles": {"default": {}, "full": {}},
                "commands": [{"path": "scripts/projected.sh", "class": "shell-ci-command"}],
                "workflows": [{"path": ".github/workflows/cognitive-os-shell-ci.yml"}],
            }
        )
    )
    script_payload = {
        "summary": {},
        "scripts": [
            {
                "path": "scripts/projected.sh",
                "role": "agentic-primitive",
                "role_source": "lifecycle",
                "lifecycle_id": "scripts/projected.sh",
                "lifecycle_state": "candidate",
                "consumer_accessibility": "install-profile-managed",
                "supported_harnesses": ["shell"],
                "distribution": "core",
                "evidence": ["test"],
            },
            {
                "path": "scripts/local.py",
                "role": "maintainer-tool",
                "role_source": "default",
                "consumer_accessibility": "so-local-only",
                "supported_harnesses": [],
                "evidence": [],
            },
        ],
    }
    write_json(root / "docs" / "reports" / "primitive-readiness-ledger-scripts-latest.json", script_payload)
    for family in ("hooks", "skills", "rules"):
        write_json(
            root / "docs" / "reports" / f"primitive-readiness-ledger-{family}-latest.json",
            {
                "summary": {},
                "items": [
                    {
                        "path": f"{family}/x",
                        "family": family,
                        "role": "runtime-safety" if family == "hooks" else "context-only",
                        "role_source": "test",
                        "lifecycle_id": f"{family}/x" if family == "hooks" else None,
                        "lifecycle_state": "advisory" if family == "hooks" else None,
                        "consumer_accessibility": "projected-consumer-surface" if family == "hooks" else "so-local-only",
                        "supported_harnesses": ["claude"] if family == "hooks" else [],
                        "evidence": ["test"],
                    }
                ],
            },
        )

    write_json(
        root / "docs" / "reports" / "primitive-readiness-ledger-templates-latest.json",
        {
            "summary": {},
            "items": [
                {
                    "path": "templates/quality.md",
                    "family": "templates",
                    "role": "quality-gate",
                    "role_source": "test",
                    "consumer_accessibility": "so-local-only",
                    "supported_harnesses": [],
                    "evidence": ["test"],
                }
            ],
        },
    )
    write_json(
        root / "docs" / "reports" / "primitive-harness-coverage-latest.json",
        {
            "schema_version": "primitive-harness-coverage.v1",
            "summary": {
                "total_primitives": 2,
                "gaps": 1,
                "unclassified_gaps": 0,
                "harness_wired_hooks": {"claude": 1, "codex": 1, "shell-ci": 0},
                "harness_projected_or_wired": {"claude": 2, "codex": 2, "shell-ci": 1},
                "gaps_by_policy": {"shell-command-only": 1},
            },
            "items": [
                {
                    "primitive": "hooks/x",
                    "family": "hooks",
                    "scope": "both",
                    "coverage": "claude+codex",
                    "gap": None,
                    "gap_policy": None,
                    "gap_status": None,
                    "gap_severity": None,
                    "harnesses": {},
                },
                {
                    "primitive": "scripts/projected.sh",
                    "family": "scripts",
                    "scope": "both",
                    "coverage": "shell-ci",
                    "gap": "scope=both but command only",
                    "gap_policy": "shell-command-only",
                    "gap_status": "aligned",
                    "gap_severity": "advisory",
                    "harnesses": {},
                },
            ],
        },
    )

    write_json(
        root / "docs" / "reports" / "primitive-fitness-ledger-latest.json",
        {
            "schema_version": "primitive-fitness-ledger.v1",
            "summary": {
                "total_reports": 1,
                "verdicts": {"promote": 1},
                "mapping_statuses": {"aligned": 1},
                "families": {"scripts": {"total": 1}},
            },
            "items": [
                {
                    "primitive_id": "scripts/projected.sh",
                    "family": "scripts",
                    "verdict": "promote",
                    "mapping_status": "aligned",
                    "delta": 4.0,
                    "baseline_score": 80,
                    "candidate_score": 84,
                    "source_report": "docs/reports/primitive-fitness/projected.json",
                    "missing_signals": [],
                    "safety_regressions": [],
                }
            ],
        },
    )
    write_json(
        root / "docs" / "reports" / "primitive-projection-fidelity-latest.json",
        {
            "schema_version": "primitive-projection-fidelity.v1",
            "summary": {"contracts": 1, "projection_rows": 2, "aligned": 2, "pending_runtime_smoke": 0},
            "items": [
                {
                    "contract_id": "hooks/x",
                    "service_mode_impact": "harness-embedded-only",
                    "projection_fidelity": [
                        {"harness": "claude", "status": "aligned"},
                        {"harness": "codex", "status": "aligned"},
                    ],
                }
            ],
        },
    )
    write_json(
        root / ".cognitive-os" / "metrics" / "primitive-interventions.jsonl",
        {
            "schema_version": "primitive-intervention.v1",
            "primitive_id": "hooks/x",
            "action_kind": "warn",
        },
    )
    write_json(
        root / ".cognitive-os" / "metrics" / "codebase-itinerary.jsonl",
        {
            "schema_version": "codebase-itinerary.v1",
            "tool": "Read",
            "category": "primitive_or_context",
            "session_id": "unit-session",
        },
    )
    write_json(
        root / "docs" / "reports" / "docs-execution-latest.json",
        {
            "summary": {"items": 1},
            "rows": [
                {
                    "path": "docs/x.md",
                    "line": 3,
                    "inferred_status": "stale",
                    "item": "done claim references missing proof",
                    "evidence": ["missing_path:x"],
                    "next_action": "update docs",
                }
            ],
        },
    )
    return root


def test_build_report_maps_readiness_rows_to_acc_statuses(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    payload = acc_pipeline.build_report(root, refresh=False, include_slow=False, fail_on_warn=False)

    statuses = {cap["id"]: cap["mapping_status"] for cap in payload["capabilities"]}

    assert statuses["script:scripts/projected.sh"] == "partial"
    assert statuses["script:scripts/local.py"] == "aligned"
    assert statuses["hook:hooks/x"] == "aligned"
    assert payload["summary"]["stale_weight"] >= 2
    assert payload["gate"]["phase"] == "reconstruction"
    assert payload["persistence"]["engram"]["status"] == "unavailable"
    assert payload["harness_projection"]["claude"]["status"] == "implemented"
    assert payload["harness_projection"]["cursor"]["status"] == "planned"
    assert payload["adapters"]["projection_profiles"]["status"] == "ok"
    assert payload["adapters"]["consumer_availability"]["status"] == "ok"
    assert payload["adapters"]["shell_ci_projection"]["status"] == "ok"
    assert payload["adapters"]["primitive_fitness_ledger"]["status"] == "ok"
    assert payload["adapters"]["harness_coverage"]["status"] == "ok"
    assert payload["adapters"]["projection_fidelity"]["status"] == "ok"
    assert payload["adapters"]["primitive_interventions"]["status"] == "ok"
    assert payload["adapters"]["codebase_itinerary"]["status"] == "ok"
    assert any(cap["id"] == "primitive_fitness:scripts/projected.sh" for cap in payload["capabilities"])
    assert any(cap["id"] == "harness_coverage:scripts/projected.sh" for cap in payload["capabilities"])
    assert any(cap["id"] == "projection_fidelity:hooks/x" for cap in payload["capabilities"])
    assert any(cap["id"] == "primitive_intervention:hooks/x" for cap in payload["capabilities"])
    assert any(cap["id"] == "codebase_itinerary:Read" for cap in payload["capabilities"])
    assert any(cap["id"] == "template:templates/quality.md" for cap in payload["capabilities"])
    compact = acc_pipeline.compact_summary(payload)
    assert compact["schema_version"] == "acc.compact.v1"
    assert compact["context_diet"]["read_this_first"] == "docs/acc/latest-compact.md"


def test_projected_readiness_row_becomes_aligned(tmp_path: Path) -> None:
    row = {
        "path": "skills/cos-status/SKILL.md",
        "role": "compatibility-wrapper",
        "role_source": "test",
        "consumer_accessibility": "repo-skill-not-projectable",
        "evidence": [],
    }

    cap = acc_pipeline.capability_from_readiness(
        row,
        "skills",
        {"skills/cos-status/SKILL.md": {"harnesses": ["claude", "codex"], "paths": [".cognitive-os/skills/cos/cos-status/SKILL.md"]}},
    )

    assert cap.mapping_status == "aligned"
    assert cap.consumer_accessibility == "projected-consumer-surface"
    assert "projected_harnesses:claude,codex" in cap.evidence


def test_harness_registry_reports_planned_harnesses(tmp_path: Path) -> None:
    root = make_repo(tmp_path)

    status, manifest = acc_pipeline.load_harness_projection(root)
    summary = acc_pipeline.harness_projection_summary(manifest, status)

    assert status.status == "ok"
    assert summary["claude"]["status"] == "implemented"
    assert summary["cursor"]["status"] == "planned"
    assert "cursor" not in acc_pipeline.implemented_harness_ids(manifest)


def test_refresh_adapters_includes_operational_primitive_reports(monkeypatch, tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    seen: list[str] = []

    def fake_run_json_command(root_path, name, command, timeout=120):
        seen.append(name)
        return acc_pipeline.AdapterStatus("ok", name, " ".join(command), summary={}), {}

    monkeypatch.setattr(acc_pipeline, "run_json_command", fake_run_json_command)

    adapters = acc_pipeline.refresh_adapters(root, include_slow=False)

    assert "primitive_projection_fidelity" in adapters
    assert "primitive_projection_fidelity" in seen
    assert "primitive_duplication" in adapters
    assert "primitive_duplication" in seen


def test_write_report_outputs_json_markdown_and_history(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    payload = acc_pipeline.build_report(root, refresh=False, include_slow=False, fail_on_warn=False)

    acc_pipeline.write_json(root / "docs" / "acc" / "latest.json", payload)
    (root / "docs" / "acc").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "acc" / "latest.md").write_text(acc_pipeline.render_markdown(payload))
    (root / "docs" / "acc" / "latest-compact.md").write_text(acc_pipeline.render_compact_markdown(payload))
    acc_pipeline.append_history(root, payload)

    assert json.loads((root / "docs" / "acc" / "latest.json").read_text())["schema_version"] == "acc.report.v1"
    assert "Agent Capability Coverage" in (root / "docs" / "acc" / "latest.md").read_text()
    assert "Primitive fitness reports" in (root / "docs" / "acc" / "latest.md").read_text()
    assert "Context Diet Rule" in (root / "docs" / "acc" / "latest-compact.md").read_text()
    assert "Primitive fitness reports" in (root / "docs" / "acc" / "latest-compact.md").read_text()
    assert (root / ".cognitive-os" / "metrics" / "acc-pipeline-history.jsonl").exists()


def test_fail_new_detects_new_partial_capability(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    baseline = acc_pipeline.build_report(root, refresh=False, include_slow=False, fail_on_warn=False)
    current = json.loads(json.dumps(baseline))
    current["capabilities"].append(
        {
            "id": "script:scripts/new_projectable.py",
            "kind": "script",
            "mapping_status": "partial",
            "evidence": ["consumer_accessibility:install-profile-managed"],
        }
    )

    new_debt = acc_pipeline.detect_new_debt(current, baseline)

    assert any(item["id"] == "script:scripts/new_projectable.py" for item in new_debt)


def test_fail_new_strictly_blocks_new_broad_local_default(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    baseline = acc_pipeline.build_report(root, refresh=False, include_slow=False, fail_on_warn=False)
    current = json.loads(json.dumps(baseline))
    current["capabilities"].append(
        {
            "id": "script:scripts/new_local_helper.py",
            "kind": "script",
            "mapping_status": "aligned",
            "evidence": [
                "availability_override:so-local-only",
                "availability_match:pattern",
                "availability_pattern:scripts/**",
            ],
        }
    )

    strict_debt = acc_pipeline.detect_new_debt(current, baseline, strict_local_defaults=True)
    loose_debt = acc_pipeline.detect_new_debt(current, baseline, strict_local_defaults=False)

    assert any(item["status"] == "unreviewed-local-default" for item in strict_debt)
    assert not loose_debt


def test_apply_fail_new_gate_blocks_payload(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    baseline = acc_pipeline.build_report(root, refresh=False, include_slow=False, fail_on_warn=False)
    current = json.loads(json.dumps(baseline))
    current["capabilities"].append(
        {
            "id": "rule:rules/new-rule.md",
            "kind": "rule",
            "mapping_status": "aligned",
            "evidence": [
                "availability_override:so-local-only",
                "availability_match:pattern",
                "availability_pattern:rules/*.md",
            ],
        }
    )

    acc_pipeline.apply_fail_new_gate(current, baseline, strict_local_defaults=True)

    assert current["gate"]["status"] == "block"
    assert current["new_debt"]["count"] == 1
    assert current["gate"]["blocks"][-1] == "new_debt:1"

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

import scripts.runtime_hook_reality as audit


REPO_ROOT = Path(__file__).resolve().parents[2]


def write_settings(root: Path, hooks: list[tuple[str, str, bool]]) -> Path:
    settings = root / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True, exist_ok=True)
    by_event: dict[str, list[dict[str, object]]] = {}
    for event, command, async_projected in hooks:
        hook_def: dict[str, object] = {"type": "command", "command": command}
        if async_projected:
            hook_def["async"] = True
        by_event.setdefault(event, [{"matcher": "", "hooks": []}])[0]["hooks"].append(hook_def)  # type: ignore[index, union-attr]
    settings.write_text(json.dumps({"hooks": by_event}, sort_keys=True), encoding="utf-8")
    return settings


def primitive(
    path: str,
    *,
    maturity: str = "advisory",
    lifecycle_state: str = "advisory",
    risk_class: str = "advisory",
    runtime_projection: bool = True,
) -> dict[str, object]:
    return {
        "id": path,
        "kind": "hook",
        "owner_adr": "ADR-126",
        "lifecycle_state": lifecycle_state,
        "maturity": maturity,
        "distribution": "team",
        "governance_class": "runtime-safety",
        "risk_class": risk_class,
        "supported_harnesses": ["claude"],
        "projection_targets": [".claude/settings.json", path],
        "runtime_projection": runtime_projection,
        "behavior_evidence": "test",
        "evidence_commands": [f"bash -n {path}"],
        "rollback_or_repair_command": "disable the hook projection",
        "sunset_criteria": "archive when unused",
    }


def write_manifest(root: Path, primitives: list[dict[str, object]]) -> Path:
    manifest = root / "manifests" / "primitive-lifecycle.yaml"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(yaml.safe_dump({"schema_version": 1, "primitives": primitives}), encoding="utf-8")
    return manifest


def write_hook(root: Path, path: str, body: str) -> None:
    hook = root / path
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text(body, encoding="utf-8")


def categories(report: dict[str, object]) -> dict[str, list[str]]:
    by_category = report["hooks_by_category"]
    assert isinstance(by_category, dict)
    return {
        category: [str(item["path"]) for item in hooks]  # type: ignore[index]
        for category, hooks in by_category.items()
    }


def test_classifies_projected_documented_hooks_by_observable_behavior(tmp_path: Path) -> None:
    write_hook(tmp_path, "hooks/blocking.sh", "#!/usr/bin/env bash\nexit 2\n")
    write_hook(tmp_path, "hooks/advisory.sh", "#!/usr/bin/env bash\nsafe-jsonl .cognitive-os/metrics/events.jsonl '{}'\nexit 0\n")
    write_hook(tmp_path, "hooks/observe.sh", "#!/usr/bin/env bash\necho observed\nexit 0\n")
    settings = write_settings(
        tmp_path,
        [
            ("PreToolUse", "bash hooks/blocking.sh", False),
            ("PostToolUse", "bash hooks/advisory.sh", True),
            ("Stop", "bash hooks/observe.sh", False),
        ],
    )
    manifest = write_manifest(
        tmp_path,
        [
            primitive("hooks/blocking.sh", maturity="blocking", lifecycle_state="blocking", risk_class="blocking"),
            primitive("hooks/advisory.sh"),
            primitive("hooks/observe.sh"),
        ],
    )

    report = audit.build_report(project_root=tmp_path, settings_path=settings, manifest_path=manifest)
    by_category = categories(report)

    assert by_category["real_blocking"] == ["hooks/blocking.sh"]
    assert by_category["real_advisory"] == ["hooks/advisory.sh"]
    assert by_category["observe_only"] == ["hooks/observe.sh"]
    assert report["summary"]["status"] == "pass"  # type: ignore[index]
    advisory = report["hooks_by_category"]["real_advisory"][0]  # type: ignore[index]
    assert advisory["async_projected"] is True
    assert advisory["projected_events"] == ["PostToolUse"]


def test_blocking_claim_without_exit2_is_not_real_blocking(tmp_path: Path) -> None:
    write_hook(tmp_path, "hooks/soft-block.sh", "#!/usr/bin/env bash\necho no hard block\nexit 0\n")
    settings = write_settings(tmp_path, [("PreToolUse", "bash hooks/soft-block.sh", False)])
    manifest = write_manifest(
        tmp_path,
        [primitive("hooks/soft-block.sh", maturity="blocking", lifecycle_state="blocking", risk_class="blocking")],
    )

    report = audit.build_report(project_root=tmp_path, settings_path=settings, manifest_path=manifest)

    assert categories(report)["real_blocking"] == []
    assert categories(report)["observe_only"] == ["hooks/soft-block.sh"]
    assert {finding["id"] for finding in report["findings"]} == {"blocking-hook-without-exit2"}
    assert report["summary"]["status"] == "fail"  # type: ignore[index]


def test_projected_undocumented_and_documented_not_projected_are_findings(tmp_path: Path) -> None:
    write_hook(tmp_path, "hooks/projected-only.sh", "#!/usr/bin/env bash\nexit 0\n")
    write_hook(tmp_path, "hooks/documented-only.sh", "#!/usr/bin/env bash\nexit 0\n")
    settings = write_settings(tmp_path, [("SessionStart", "bash hooks/projected-only.sh", False)])
    manifest = write_manifest(tmp_path, [primitive("hooks/documented-only.sh", runtime_projection=True)])

    report = audit.build_report(project_root=tmp_path, settings_path=settings, manifest_path=manifest)
    by_category = categories(report)

    assert by_category["projected_but_undocumented"] == ["hooks/projected-only.sh"]
    assert by_category["documented_but_not_projected"] == ["hooks/documented-only.sh"]
    assert [finding["id"] for finding in report["findings"]] == [
        "documented-hook-not-projected",
        "projected-hook-undocumented",
    ]


def test_non_projected_inactive_or_non_runtime_hooks_are_dormant(tmp_path: Path) -> None:
    settings = write_settings(tmp_path, [])
    manifest = write_manifest(
        tmp_path,
        [
            primitive("hooks/inactive.sh", lifecycle_state="archived", runtime_projection=True),
            primitive("hooks/not-runtime.sh", runtime_projection=False),
        ],
    )

    report = audit.build_report(project_root=tmp_path, settings_path=settings, manifest_path=manifest)

    assert categories(report)["dormant"] == ["hooks/inactive.sh", "hooks/not-runtime.sh"]
    assert report["summary"]["status"] == "pass"  # type: ignore[index]


def test_demoted_blocking_hook_is_dormant_not_exit2_failure(tmp_path: Path) -> None:
    write_hook(tmp_path, "hooks/demoted-blocking.sh", "#!/usr/bin/env bash\necho dormant\nexit 0\n")
    settings = write_settings(tmp_path, [])
    manifest = write_manifest(
        tmp_path,
        [
            primitive(
                "hooks/demoted-blocking.sh",
                maturity="blocking",
                lifecycle_state="demoted",
                risk_class="blocking",
                runtime_projection=False,
            )
        ],
    )

    report = audit.build_report(project_root=tmp_path, settings_path=settings, manifest_path=manifest)

    assert categories(report)["dormant"] == ["hooks/demoted-blocking.sh"]
    assert report["findings"] == []
    assert report["summary"]["status"] == "pass"  # type: ignore[index]


def test_repository_settings_hook_count_is_report_derived_not_hardcoded() -> None:
    report = audit.build_report(
        project_root=REPO_ROOT,
        settings_path=REPO_ROOT / ".claude" / "settings.json",
        manifest_path=REPO_ROOT / "manifests" / "primitive-lifecycle.yaml",
    )

    assert report["summary"]["status"] == "pass"
    assert report["summary"]["projected_unique_hooks"] == len(
        audit.load_projected_hooks(REPO_ROOT / ".claude" / "settings.json")
    )


def test_cli_emits_stable_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_hook(tmp_path, "hooks/advisory.sh", "#!/usr/bin/env bash\nprintf '{}\\n' >> .cognitive-os/metrics/runtime.jsonl\n")
    settings = write_settings(tmp_path, [("PostToolUse", "bash hooks/advisory.sh", False)])
    manifest = write_manifest(tmp_path, [primitive("hooks/advisory.sh")])

    exit_code = audit.main(["--project-root", str(tmp_path), "--settings", str(settings), "--manifest", str(manifest)])
    captured = capsys.readouterr()
    loaded = json.loads(captured.out)

    assert exit_code == 0
    assert loaded["summary"]["counts"]["real_advisory"] == 1
    assert list(loaded["summary"]["counts"]) == sorted(audit.CATEGORIES)

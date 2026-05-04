from __future__ import annotations

from pathlib import Path

import yaml

import scripts.silent_failure_audit as audit


def test_silent_failure_audit_fails_on_unclassified_pattern(tmp_path: Path) -> None:
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    (hooks / "x.sh").write_text("cmd 2>/dev/null || true\n", encoding="utf-8")
    allowlist = tmp_path / "allow.yaml"
    allowlist.write_text(yaml.safe_dump({"schema_version": 1, "entries": []}), encoding="utf-8")

    report = audit.build_report(tmp_path, hooks, allowlist)

    assert report["status"] == "fail"
    assert report["findings"][0]["id"] == "unclassified-silent-failure"


def test_silent_failure_audit_fails_when_surface_increases(tmp_path: Path) -> None:
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    (hooks / "x.sh").write_text("a || true\nb || true\n", encoding="utf-8")
    allowlist = tmp_path / "allow.yaml"
    allowlist.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "entries": [
                    {
                        "path": "hooks/x.sh",
                        "max_occurrences": 1,
                        "degradation_class": "legacy_audited",
                        "rationale": "Existing optional degradation audited.",
                        "owner": "original-maintainer",
                        "reviewed_on": "2026-05-03",
                        "transferability_state": "maintainer_cache",
                        "shape_b_action": "Requires second-maintainer review before Shape B.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    report = audit.build_report(tmp_path, hooks, allowlist)

    assert report["status"] == "fail"
    assert any(f["id"] == "silent-failure-surface-increased" for f in report["findings"])


def test_silent_failure_audit_passes_classified_baseline(tmp_path: Path) -> None:
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    (hooks / "x.sh").write_text("a || :\n", encoding="utf-8")
    allowlist = tmp_path / "allow.yaml"
    allowlist.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "entries": [
                    {
                        "path": "hooks/x.sh",
                        "max_occurrences": 1,
                        "degradation_class": "cleanup_best_effort",
                        "rationale": "Cleanup is best effort and must not block the parent hook.",
                        "owner": "original-maintainer",
                        "reviewed_on": "2026-05-03",
                        "transferability_state": "documented_classification",
                        "shape_b_action": "Classification is explicit enough for Shape A; re-review before Shape B.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    report = audit.build_report(tmp_path, hooks, allowlist)

    assert report["status"] == "pass"


def test_silent_failure_audit_fails_without_transferability_metadata(tmp_path: Path) -> None:
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    (hooks / "x.sh").write_text("a || :\n", encoding="utf-8")
    allowlist = tmp_path / "allow.yaml"
    allowlist.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "entries": [
                    {
                        "path": "hooks/x.sh",
                        "max_occurrences": 1,
                        "degradation_class": "cleanup_best_effort",
                        "rationale": "Cleanup is best effort and must not block the parent hook.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    report = audit.build_report(tmp_path, hooks, allowlist)

    assert report["status"] == "fail"
    assert {
        "missing-transferability-state",
        "missing-silent-failure-owner",
        "missing-silent-failure-review-date",
        "missing-shape-b-action",
    }.issubset({finding["id"] for finding in report["findings"]})


def test_maintainer_cache_entries_are_tracked_as_shape_b_debt_without_warning(tmp_path: Path) -> None:
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    (hooks / "x.sh").write_text("a || :\n", encoding="utf-8")
    allowlist = tmp_path / "allow.yaml"
    allowlist.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "entries": [
                    {
                        "path": "hooks/x.sh",
                        "max_occurrences": 1,
                        "degradation_class": "legacy_audited",
                        "rationale": "Legacy degradation audited by the original maintainer.",
                        "owner": "original-maintainer",
                        "reviewed_on": "2026-05-03",
                        "transferability_state": "maintainer_cache",
                        "shape_b_action": "Requires second-maintainer review before Shape B.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    report = audit.build_report(tmp_path, hooks, allowlist)

    assert report["status"] == "pass"
    assert report["warn_count"] == 0
    assert report["maintainer_cache_file_count"] == 1
    assert report["maintainer_cache_occurrence_count"] == 1
    assert any(finding["id"] == "shape-b-transferability-debt" for finding in report["findings"])


def test_repository_allowlist_is_not_all_legacy() -> None:
    report = audit.build_report()

    class_counts = report["counts_by_degradation_class"]
    assert report["file_count"] > 0
    assert class_counts["legacy_audited"] < report["file_count"]
    assert sum(count for name, count in class_counts.items() if name != "legacy_audited") > 0

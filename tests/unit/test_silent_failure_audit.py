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
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    report = audit.build_report(tmp_path, hooks, allowlist)

    assert report["status"] == "pass"

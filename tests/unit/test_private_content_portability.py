from pathlib import Path

from scripts.private_content_audit import (
    build_report,
    classify_path,
    load_manifest,
    secret_path_findings,
    unknown_surface_findings,
)


REPO = Path(__file__).resolve().parents[2]
MANIFEST = REPO / "manifests" / "private-content.yaml"


def test_strategy_root_is_local_only():
    manifest = load_manifest(MANIFEST)

    classification = classify_path(".cognitive-os/strategy/research/02-real-self-improvement.md", manifest, REPO)

    assert classification.content_class == "local-only"
    assert classification.surface_id == "strategy-private"
    assert classification.may_read_content is True


def test_secret_patterns_are_never_touch_even_inside_private_root():
    manifest = load_manifest(MANIFEST)

    classification = classify_path(".cognitive-os/strategy/.env.local", manifest, REPO)

    assert classification.content_class == "secret-never-touch"
    assert classification.surface_id == "secret-pattern"
    assert classification.may_read_content is False


def test_skeleton_manifest_classifies_current_private_roots():
    manifest = load_manifest(MANIFEST)

    for rel_path in [
        ".cognitive-os/plans/architecture/adr-200-plus-closure-plan.md",
        ".cognitive-os/recovery/stashes-20260506T200958Z/manifest.json",
        ".cognitive-os/metrics/agent-redirect.jsonl",
        ".cognitive-os/engram-bundles/session.json",
        ".cognitive-os/artifacts/evidence/report.json",
    ]:
        classification = classify_path(rel_path, manifest, REPO)
        assert classification.content_class == "local-only", rel_path


def test_unknown_cognitive_os_root_is_reported(tmp_path):
    manifest = load_manifest(MANIFEST)
    new_root = tmp_path / ".cognitive-os" / "new-private-surface"
    new_root.mkdir(parents=True)

    findings = unknown_surface_findings(tmp_path, manifest)

    assert any(finding.code == "unknown-private-root" for finding in findings)
    assert any(finding.path == ".cognitive-os/new-private-surface" for finding in findings)


def test_declared_cognitive_os_root_is_not_unknown(tmp_path):
    manifest = load_manifest(MANIFEST)
    strategy = tmp_path / ".cognitive-os" / "strategy"
    strategy.mkdir(parents=True)

    findings = unknown_surface_findings(tmp_path, manifest)

    assert findings == []


def test_secret_path_scan_does_not_need_to_read_secret_contents(tmp_path):
    manifest = load_manifest(MANIFEST)
    secret = tmp_path / ".env"
    secret.write_text("SHOULD_NOT_BE_READ=sentinel", encoding="utf-8")

    findings = secret_path_findings(tmp_path, manifest)

    assert len(findings) == 1
    assert findings[0].code == "secret-path-classified"
    assert findings[0].path == ".env"
    assert "sentinel" not in findings[0].message


def test_strict_report_passes_for_manifest_only():
    report = build_report(REPO, MANIFEST)

    assert report["summary"]["block"] == 0
    assert report["summary"]["warn"] == 0
    assert "secret-never-touch" in report["classes"]

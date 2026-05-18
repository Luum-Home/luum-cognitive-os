"""Tests for ADR-041 exercised coverage primitive classification."""
from __future__ import annotations

from pathlib import Path

from lib.exercised_coverage import classify_primitive, compute_tiers, distribution, scan_primitives


def test_scan_primitives_includes_extensionless_shebang_scripts(tmp_path: Path) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    tool = scripts / "cos-sample-tool"
    tool.write_text("#!/usr/bin/env python3\nprint('ok')\n", encoding="utf-8")

    assert "cos-sample-tool" in scan_primitives(tmp_path)


def test_scan_primitives_includes_packaged_skills(tmp_path: Path) -> None:
    skill = tmp_path / "packages" / "cos-pack" / "skills" / "sample-skill" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: sample-skill\n---\n", encoding="utf-8")

    assert "sample-skill" in scan_primitives(tmp_path)


def test_classify_waterfall_prefers_tests_over_invocation_and_declaration(tmp_path: Path) -> None:
    (tmp_path / "tests" / "behavior").mkdir(parents=True)
    (tmp_path / "tests" / "behavior" / "test_secret_detector.py").write_text(
        "def test_secret_detector(): assert True\n",
        encoding="utf-8",
    )
    metrics = tmp_path / ".cognitive-os" / "metrics"
    metrics.mkdir(parents=True)
    (metrics / "primitive-interventions.jsonl").write_text(
        '{"primitive_id":"secret-detector"}\n',
        encoding="utf-8",
    )
    manifests = tmp_path / "manifests"
    manifests.mkdir()
    (manifests / "primitive-lifecycle.yaml").write_text(
        "primitives:\n  - id: hooks/secret-detector.sh\n",
        encoding="utf-8",
    )

    assert classify_primitive("secret-detector", tmp_path) == 0


def test_classify_declared_only_as_tier_2(tmp_path: Path) -> None:
    manifests = tmp_path / "manifests"
    manifests.mkdir()
    (manifests / "primitive-lifecycle.yaml").write_text(
        "primitives:\n  - id: hooks/declared-only.sh\n",
        encoding="utf-8",
    )

    assert classify_primitive("declared-only", tmp_path) == 2


def test_compute_tiers_and_distribution(tmp_path: Path) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "dead-tool").write_text("#!/usr/bin/env bash\necho dead\n", encoding="utf-8")
    (tmp_path / "tests" / "behavior").mkdir(parents=True)
    (tmp_path / "tests" / "behavior" / "test_dead_tool.py").write_text("dead_tool = True\n", encoding="utf-8")

    tiers = compute_tiers(tmp_path)
    assert tiers["dead-tool"] == 0
    dist = distribution(tiers)
    assert sum(dist.values()) == len(tiers)

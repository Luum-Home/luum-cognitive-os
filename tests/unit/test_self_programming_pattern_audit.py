from __future__ import annotations

from pathlib import Path

import yaml

from scripts.self_programming_pattern_audit import REQUIRED_PATTERN_IDS, build_report


def test_self_programming_pattern_manifest_passes() -> None:
    report = build_report(Path("manifests/self-programming-agent-patterns.yaml"))

    assert report["status"] == "pass"
    assert report["summary"]["patterns"] == len(REQUIRED_PATTERN_IDS)
    assert report["findings"] == []


def test_self_programming_patterns_stay_non_default_runtime() -> None:
    manifest = yaml.safe_load(Path("manifests/self-programming-agent-patterns.yaml").read_text(encoding="utf-8"))

    assert manifest["policy"]["default_runtime_adoption"] is False
    assert set(manifest["policy"]["allowed_adoption_kinds"]) == {"pattern-only", "adapter-lab"}
    for pattern in manifest["patterns"]:
        assert pattern["id"] in REQUIRED_PATTERN_IDS
        assert pattern["adoption_kind"] == "pattern-only"
        assert pattern["required_gates"]
        assert pattern["observable_evidence"]

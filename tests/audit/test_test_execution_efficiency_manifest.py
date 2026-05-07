from __future__ import annotations

import yaml


def test_test_execution_efficiency_manifest_forbids_broad_first(project_root) -> None:
    manifest = yaml.safe_load((project_root / "manifests/test-execution-efficiency.yaml").read_text())
    assert manifest["schema_version"] == "test-execution-efficiency/v1"
    assert manifest["scope"] == "cognitive-os-maintainers-only"
    assert manifest["policy"]["broad_first_default"] is False
    assert manifest["policy"]["max_broad_reruns_without_targeted_pass"] == 0

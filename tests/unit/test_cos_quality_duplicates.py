from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "cos_quality_duplicates.py"
spec = importlib.util.spec_from_file_location("cos_quality_duplicates", MODULE_PATH)
assert spec and spec.loader
cos_quality_duplicates = importlib.util.module_from_spec(spec)
sys.modules["cos_quality_duplicates"] = cos_quality_duplicates
spec.loader.exec_module(cos_quality_duplicates)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_fallback_detects_lexical_duplicates_without_external_tools(tmp_path: Path) -> None:
    body = "\n".join([f"const value{i} = normalize(input{i});" for i in range(30)])
    write(tmp_path / "src" / "a.ts", body)
    write(tmp_path / "src" / "b.ts", body)

    data = cos_quality_duplicates.audit_project(tmp_path, ["src"], [], 20, 4, 0.5, False, None)

    assert data["schema_version"] == "cos-quality-duplicates.v1"
    assert data["summary"]["findings"] >= 1
    assert "lexical" in data["summary"]["by_lane"]
    assert "jscpd" in data["external_tools"]


def test_baseline_ratchet_fails_only_for_new_duplicate_identities(tmp_path: Path) -> None:
    body = "\n".join([f"return shared_policy_{i}(account);" for i in range(30)])
    write(tmp_path / "src" / "a.py", body)
    write(tmp_path / "src" / "b.py", body)
    baseline = tmp_path / ".cognitive-os" / "baselines" / "quality-duplicates.json"

    data = cos_quality_duplicates.audit_project(tmp_path, ["src"], [], 20, 4, 0.5, False, baseline)
    cos_quality_duplicates.write_baseline(baseline, data)
    same = cos_quality_duplicates.audit_project(tmp_path, ["src"], [], 20, 4, 0.5, False, baseline)
    assert same["ratchet"]["status"] == "pass"

    write(tmp_path / "src" / "c.py", body)
    changed = cos_quality_duplicates.audit_project(tmp_path, ["src"], [], 20, 4, 0.5, False, baseline)
    assert changed["ratchet"]["status"] == "fail"
    assert changed["ratchet"]["new_findings"] >= 1


def test_fleet_discovery_uses_registry_and_marker_scan_with_redacted_paths(tmp_path: Path) -> None:
    project_a = tmp_path / "project-a"
    project_b = tmp_path / "project-b"
    write(project_a / "cognitive-os.yaml", "project:\n  name: a\n")
    write(project_b / ".cognitive-os" / "install-meta.json", "{}")
    registry = tmp_path / "installations.json"
    registry.write_text(json.dumps({"installations": [{"path": str(project_a), "project_name": "a", "source": "src"}]}), encoding="utf-8")

    data = cos_quality_duplicates.fleet_report("src", tmp_path, registry, False, 10)

    assert data["project_count"] == 2
    assert data["path_redacted"] is True
    assert all(row["path"] is None for row in data["projects"])
    assert {row["discovery"] for row in data["projects"]} == {"registry+marker-scan", "marker-scan"}

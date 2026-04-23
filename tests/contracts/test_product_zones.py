"""Contract tests for the product zone taxonomy."""

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

VALID_ZONES = {"core", "compatibility", "extensions", "experimental"}


def _load_zones() -> tuple[Path, dict]:
    repo_root = Path(__file__).resolve().parents[2]
    manifest_path = repo_root / "manifests" / "product-zones.yaml"
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    return repo_root, data


def test_product_zones_manifest_exists():
    repo_root, _ = _load_zones()
    assert (repo_root / "manifests" / "product-zones.yaml").exists()


def test_four_product_zones_are_declared():
    _, data = _load_zones()
    assert set(data["zones"]) == VALID_ZONES
    for zone_name, zone in data["zones"].items():
        assert zone["description"], f"{zone_name} is missing a description"
        assert zone["default_change_policy"], f"{zone_name} is missing a change policy"


def test_classified_paths_exist_and_use_valid_zones():
    repo_root, data = _load_zones()
    classifications = data["path_classification"]
    assert len(classifications) >= 25

    for item in classifications:
        assert item["zone"] in VALID_ZONES, f"Invalid zone for {item['path']}: {item['zone']}"
        assert item["reason"], f"Missing reason for {item['path']}"
        assert (repo_root / item["path"]).exists(), f"Classified path does not exist: {item['path']}"


def test_each_zone_has_multiple_classified_surfaces():
    _, data = _load_zones()
    counts = {zone: 0 for zone in VALID_ZONES}
    for item in data["path_classification"]:
        counts[item["zone"]] += 1

    for zone, count in counts.items():
        assert count >= 3, f"{zone} should classify at least three real surfaces"


def test_required_product_surfaces_are_classified():
    _, data = _load_zones()
    paths = {item["path"]: item["zone"] for item in data["path_classification"]}

    expected = {
        "pkg/hook": "core",
        "internal/validator": "core",
        "internal/provider": "compatibility",
        "lib/compatibility_layer.py": "compatibility",
        "skills": "extensions",
        "rules": "extensions",
        "squads": "experimental",
    }

    for path, zone in expected.items():
        assert paths.get(path) == zone, f"{path} should be classified as {zone}"


def test_taxonomy_docs_and_verification_links_exist():
    repo_root, data = _load_zones()
    verification = data["verification"]

    for path in verification["contract_tests"] + verification["primary_docs"]:
        assert (repo_root / path).exists(), f"Missing taxonomy verification artifact: {path}"


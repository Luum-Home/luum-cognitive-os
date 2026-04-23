"""Contract tests for the durable kernel manifest."""

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit


def _load_contract() -> tuple[Path, dict]:
    repo_root = Path(__file__).resolve().parents[2]
    contract_path = repo_root / "manifests" / "kernel-contract.yaml"
    data = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    return repo_root, data


def test_kernel_contract_file_exists():
    repo_root, _ = _load_contract()
    assert (repo_root / "manifests" / "kernel-contract.yaml").exists()


def test_product_promise_is_short_and_product_facing():
    _, data = _load_contract()
    promise = data["product_promise"]
    assert "governable" in promise
    assert "verifiable" in promise
    assert "portable" in promise


def test_kernel_contract_paths_exist():
    repo_root, data = _load_contract()
    contracts = data["kernel"]["contracts"]
    assert len(contracts) >= 4
    for item in contracts:
        path = repo_root / item["path"]
        assert path.exists(), f"Missing kernel contract path: {path}"


def test_compatibility_and_execution_modules_exist():
    repo_root, data = _load_contract()
    compatibility_module = repo_root / data["compatibility_layer"]["module"]
    execution_module = repo_root / data["execution_profiles"]["module"]
    outcome_module = repo_root / data["outcome_metrics"]["module"]
    assert compatibility_module.exists()
    assert execution_module.exists()
    assert outcome_module.exists()


def test_manual_verification_guide_exists():
    repo_root, data = _load_contract()
    guide = repo_root / data["verification"]["manual_guide"]
    assert guide.exists()

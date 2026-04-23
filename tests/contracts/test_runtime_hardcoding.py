"""Contract tests for non-core hardcoding in protected runtime paths."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.unit

VALID_ZONES = {"extensions", "experimental"}
VALID_STATUSES = {"legacy_exception", "self_hosting_exception"}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_allowlist() -> dict[str, Any]:
    manifest_path = _repo_root() / "manifests" / "runtime-hardcoding-allowlist.yaml"
    return yaml.safe_load(manifest_path.read_text(encoding="utf-8"))


def _allowed_texts(data: dict[str, Any]) -> set[tuple[str, str, str]]:
    return {
        (item["path"], item["pattern_id"], item["required_text"])
        for item in data["allowlist"]
    }


def test_runtime_hardcoding_manifest_is_well_formed():
    repo_root = _repo_root()
    data = _load_allowlist()

    assert data["version"] == 1
    assert data["purpose"]
    assert data["protected_runtime_paths"]
    assert data["blocked_reference_patterns"]
    assert data["allowlist"]

    pattern_ids = {pattern["id"] for pattern in data["blocked_reference_patterns"]}
    assert len(pattern_ids) == len(data["blocked_reference_patterns"])

    for path in data["protected_runtime_paths"]:
        assert (repo_root / path).exists(), f"Protected runtime path is missing: {path}"

    for pattern in data["blocked_reference_patterns"]:
        assert pattern["zone"] in VALID_ZONES
        assert pattern["reason"]
        re.compile(pattern["regex"])

    for item in data["allowlist"]:
        assert item["pattern_id"] in pattern_ids
        assert item["zone"] in VALID_ZONES
        assert item["status"] in VALID_STATUSES
        assert item["reason"]
        assert item["remediation"]
        assert item["required_text"]
        path = repo_root / item["path"]
        assert path.exists(), f"Allowlisted path is missing: {item['path']}"
        assert item["required_text"] in path.read_text(encoding="utf-8")


def test_protected_runtime_paths_do_not_gain_new_non_core_references():
    repo_root = _repo_root()
    data = _load_allowlist()
    allowed = _allowed_texts(data)
    failures: list[str] = []

    for protected_path in data["protected_runtime_paths"]:
        path = repo_root / protected_path
        text = path.read_text(encoding="utf-8")

        for pattern in data["blocked_reference_patterns"]:
            regex = re.compile(pattern["regex"])
            for match in regex.finditer(text):
                matched_text = match.group(0)
                if (protected_path, pattern["id"], matched_text) in allowed:
                    continue

                line_number = text.count("\n", 0, match.start()) + 1
                failures.append(
                    f"{protected_path}:{line_number} matched {pattern['id']} with {matched_text!r}"
                )

    assert not failures, "New non-core runtime hardcoding found:\n" + "\n".join(failures)


def test_runtime_hardcoding_verification_links_exist():
    repo_root = _repo_root()
    data = _load_allowlist()
    verification = data["verification"]

    for path in verification["contract_tests"] + verification["primary_docs"]:
        assert (repo_root / path).exists(), f"Missing runtime-hardcoding artifact: {path}"


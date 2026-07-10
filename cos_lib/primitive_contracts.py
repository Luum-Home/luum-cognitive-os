"""Read-only helpers for ADR-256 primitive contracts."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

CONTRACTS_REL_PATH = Path("manifests") / "primitive-contracts.yaml"


def load_contract_manifest(root: Path) -> dict[str, Any]:
    """Load the primitive contract registry for *root*."""
    path = root / CONTRACTS_REL_PATH
    if not path.exists():
        return {"schema_version": "primitive-contracts.v1", "contracts": [], "fidelity_levels": {}}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def load_contracts(root: Path) -> list[dict[str, Any]]:
    """Return primitive contract rows from the registry."""
    contracts = load_contract_manifest(root).get("contracts", [])
    if not isinstance(contracts, list):
        raise ValueError("manifests/primitive-contracts.yaml contracts must be a list")
    return [contract for contract in contracts if isinstance(contract, dict)]


def contracts_by_id(root: Path) -> dict[str, dict[str, Any]]:
    """Index contracts by stable primitive contract id."""
    out: dict[str, dict[str, Any]] = {}
    for contract in load_contracts(root):
        contract_id = str(contract.get("id", "")).strip()
        if contract_id:
            out[contract_id] = contract
    return out


def contracts_by_source(root: Path) -> dict[str, dict[str, Any]]:
    """Index contracts by source and implementation_refs paths."""
    out: dict[str, dict[str, Any]] = {}
    for contract in load_contracts(root):
        for key in ["source", *list(contract.get("implementation_refs") or [])]:
            ref = str(key).strip()
            if ref:
                out[ref] = contract
    return out

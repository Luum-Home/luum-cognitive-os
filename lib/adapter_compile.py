"""Fidelity-preserving adapter compiler for consumer IDE files.

This module is the explicit bridge between the generated maintainer `.ai/`
overlay and native consumer-project files. It keeps `.ai/adapters/*` declarative
while delegating host-specific file emission to the existing governed harness
projection driver (`scripts/cos_init.py`).
"""
from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lib.lazy_imports import LazyImport

# Lazy yaml import (ADR-290 Pattern 1) — yaml is only needed when this module
# actually loads a manifest, not on every import.
_yaml = LazyImport(lambda: __import__("yaml"))

ENFORCEMENT_FIDELITY = {"native-lifecycle-enforced", "governed-wrapper-enforced", "ci-enforced"}
STRUCTURAL_FIDELITY = {"structural-advisory", "documented-only", "host-plugin-lifecycle-capable"}


@dataclass(frozen=True)
class CompileReceipt:
    """Machine-readable result of compiling a harness projection."""

    schema_version: str
    status: str
    harness: str
    output_dir: str
    mode: str
    proof_level: str | None
    projection_mode: str | None
    native_file_emission: bool
    projection_driver: str
    settings_paths: list[str]
    emitted_paths: list[str]
    fidelity_summary: dict[str, int]
    enforcement_claims: int
    advisory_claims: int
    generated_at: str
    command: list[str]
    dry_run: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "status": self.status,
            "harness": self.harness,
            "output_dir": self.output_dir,
            "mode": self.mode,
            "proof_level": self.proof_level,
            "projection_mode": self.projection_mode,
            "native_file_emission": self.native_file_emission,
            "projection_driver": self.projection_driver,
            "settings_paths": self.settings_paths,
            "emitted_paths": self.emitted_paths,
            "fidelity_summary": self.fidelity_summary,
            "enforcement_claims": self.enforcement_claims,
            "advisory_claims": self.advisory_claims,
            "generated_at": self.generated_at,
            "command": self.command,
            "dry_run": self.dry_run,
        }


def _load_yaml(path: Path) -> dict[str, Any]:
    data = _yaml.get().safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    return data if isinstance(data, dict) else {}


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    return data if isinstance(data, dict) else {}


def harness_projection(root: Path) -> dict[str, dict[str, Any]]:
    data = _load_yaml(root / "manifests" / "harness-projection.yaml")
    return {str(row["id"]): row for row in data.get("harnesses", []) if isinstance(row, dict) and row.get("id")}


def _adapter_dir(profile: dict[str, Any], harness: str) -> str:
    return str(profile.get("adapter_directory") or f"adapters/{harness}")


def _profile(root: Path, harness: str) -> dict[str, Any]:
    profile = _load_json(root / ".ai" / "profiles" / f"{harness}.json")
    if profile:
        return profile
    hp = harness_projection(root).get(harness, {})
    if not hp:
        raise ValueError(f"unknown harness: {harness}")
    return {
        "harness": harness,
        "proof_level": hp.get("proof_level"),
        "projection_mode": hp.get("projection_mode"),
        "settings_paths": list(hp.get("settings_paths") or []),
        "adapter_directory": f"adapters/{harness}",
        "contract_projection_fidelity": [],
    }


def _manifest(root: Path, profile: dict[str, Any]) -> dict[str, Any]:
    return _load_json(root / ".ai" / _adapter_dir(profile, str(profile.get("harness", ""))) / "adapter.json")


def fidelity_summary(profile: dict[str, Any], manifest: dict[str, Any]) -> dict[str, int]:
    rows = list(profile.get("contract_projection_fidelity") or [])
    if not rows:
        rows = list(manifest.get("projected_primitives") or [])
    counts: dict[str, int] = {}
    for row in rows:
        fidelity = str(row.get("fidelity") or row.get("declared_fidelity") or "unknown")
        counts[fidelity] = counts.get(fidelity, 0) + 1
        if fidelity == "structural-advisory" and bool(row.get("claims_runtime_enforcement")):
            raise ValueError("structural-advisory projection must not claim runtime enforcement")
    return dict(sorted(counts.items()))


def expected_settings_paths(root: Path, harness: str, profile: dict[str, Any]) -> list[str]:
    hp = harness_projection(root).get(harness, {})
    paths = list(profile.get("settings_paths") or []) or list(hp.get("settings_paths") or [])
    return [str(path) for path in paths]


def compile_adapter(
    *,
    root: Path,
    harness: str,
    output_dir: Path,
    mode: str = "default",
    dry_run: bool = False,
    timeout: int = 90,
) -> dict[str, Any]:
    """Compile a harness projection into a consumer project directory.

    The compiler preserves COS fidelity by reading `.ai/profiles/<harness>.json`
    and `.ai/adapters/<harness>/adapter.json`, then delegates native file writes
    to `scripts/cos_init.py`. This keeps the generated `.ai` overlay declarative
    while providing a real compiler entry point.
    """

    root = root.resolve()
    output_dir = output_dir.resolve()
    if mode not in {"default", "full"}:
        raise ValueError("mode must be 'default' or 'full'")
    profile = _profile(root, harness)
    manifest = _manifest(root, profile)
    counts = fidelity_summary(profile, manifest)
    enforcement = sum(count for fidelity, count in counts.items() if fidelity in ENFORCEMENT_FIDELITY)
    advisory = sum(count for fidelity, count in counts.items() if fidelity in STRUCTURAL_FIDELITY)
    settings = expected_settings_paths(root, harness, profile)
    command = [sys.executable, str(root / "scripts" / "cos_init.py"), f"--{mode}", "--harness", harness]

    emitted: list[str] = []
    status = "planned"
    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            command,
            cwd=output_dir,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr + result.stdout)
        status = "compiled"
        for rel in settings:
            if (output_dir / rel).exists():
                emitted.append(rel)
        if (output_dir / ".cognitive-os" / "install-meta.json").exists():
            emitted.append(".cognitive-os/install-meta.json")
    else:
        emitted = settings[:]

    receipt = CompileReceipt(
        schema_version="cos-adapter-compile.v1",
        status=status,
        harness=harness,
        output_dir=str(output_dir),
        mode=mode,
        proof_level=profile.get("proof_level"),
        projection_mode=profile.get("projection_mode"),
        native_file_emission=not dry_run,
        projection_driver="scripts/cos_init.py",
        settings_paths=settings,
        emitted_paths=sorted(dict.fromkeys(emitted)),
        fidelity_summary=counts,
        enforcement_claims=enforcement,
        advisory_claims=advisory,
        generated_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        command=command,
        dry_run=dry_run,
    )
    return receipt.to_dict()

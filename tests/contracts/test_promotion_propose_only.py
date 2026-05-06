"""Contract test: promotion + demotion proposers MUST be propose-only.

ADR-178 invariant. Computes SHA-256 of:
  - manifests/primitive-lifecycle.yaml
  - manifests/agentic-primitive-registry.lock.yaml

before and after running both proposers (with --apply) against a synthetic
SkillStore. SHA must be byte-identical.

This is a CRITICAL invariant: regression here means the SO has begun to
auto-mutate doctrine without human approval.
"""

from __future__ import annotations

import hashlib
import shutil
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "absent"


@pytest.fixture
def project_copy(tmp_path: Path) -> Path:
    proj = tmp_path / "proj"
    proj.mkdir()
    # Copy lifecycle + lock manifests verbatim
    (proj / "manifests").mkdir()
    for name in ("primitive-lifecycle.yaml", "agentic-primitive-registry.lock.yaml"):
        src = PROJECT_ROOT / "manifests" / name
        if src.exists():
            shutil.copy2(src, proj / "manifests" / name)
    return proj


def test_promoter_does_not_mutate_manifests(project_copy: Path, tmp_path: Path):
    from lib.skill_store import SkillStore
    from scripts.cos_promotion_proposer import main as promoter_main
    from scripts.cos_demotion_proposer import main as demoter_main

    lifecycle = project_copy / "manifests" / "primitive-lifecycle.yaml"
    lock = project_copy / "manifests" / "agentic-primitive-registry.lock.yaml"

    if not lifecycle.exists():
        pytest.skip("primitive-lifecycle.yaml not present")

    # Synthetic skill store with eligible-looking data so promoter would *want*
    # to act on something.
    db_path = tmp_path / "store.db"
    store = SkillStore(db_path)
    for _ in range(60):
        store.record_execution("aci-observation-capture", "s", 1, 50, "success")
    for _ in range(5):
        store.record_judgment(
            hashlib.sha256(b"aci-observation-capture").hexdigest(),
            "judge",
            "approve",
            0.95,
            "ok",
        )
    store.close()

    sha_lifecycle_before = _sha(lifecycle)
    sha_lock_before = _sha(lock)

    out_dir = tmp_path / "out"
    metrics = tmp_path / "m.jsonl"

    promoter_main(
        [
            "--db", str(db_path),
            "--lifecycle", str(lifecycle),
            "--out-root", str(out_dir / "promotion"),
            "--metrics", str(metrics),
            "--apply",
        ]
    )

    demoter_main(
        [
            "--db", str(db_path),
            "--lifecycle", str(lifecycle),
            "--out-root", str(out_dir / "demotion"),
            "--metrics", str(tmp_path / "d.jsonl"),
            "--apply",
        ]
    )

    sha_lifecycle_after = _sha(lifecycle)
    sha_lock_after = _sha(lock)

    assert sha_lifecycle_before == sha_lifecycle_after, (
        "primitive-lifecycle.yaml SHA changed — promote/demote must be propose-only"
    )
    assert sha_lock_before == sha_lock_after, (
        "agentic-primitive-registry.lock.yaml SHA changed — promote/demote must be propose-only"
    )

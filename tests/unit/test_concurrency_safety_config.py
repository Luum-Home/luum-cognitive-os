from __future__ import annotations

from pathlib import Path

import pytest

from lib.concurrency_safety import load_concurrency_safety_config

pytestmark = pytest.mark.unit


def write_config(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "cognitive-os.yaml"
    path.write_text(body, encoding="utf-8")
    return path


def test_missing_section_uses_safe_core_defaults(tmp_path: Path) -> None:
    cfg = write_config(tmp_path, "project:\n  phase: reconstruction\n")

    safety = load_concurrency_safety_config(str(cfg))

    assert safety.enabled is True
    assert safety.preserve_branches.require_manifest is True
    assert safety.stash_leak_alarm.warn_ttl_seconds == 600
    assert safety.stash_leak_alarm.block_ttl_seconds == 3600
    assert safety.plan_claims.require_bilateral_proof is True
    assert safety.resource_leases.critical_domains == (
        "auth",
        "billing",
        "migrations",
        "infrastructure",
    )


def test_consumer_projection_overrides_supported_policy(tmp_path: Path) -> None:
    cfg = write_config(
        tmp_path,
        """
concurrency_safety:
  enabled: true
  preserve_branches:
    enabled: false
    require_manifest: false
  stash_leak_alarm:
    warn_ttl_seconds: 120
    block_ttl_seconds: 900
  plan_claims:
    require_bilateral_proof: false
  resource_leases:
    default_ttl_seconds: 45
    critical_domains:
      - payments
      - deploy
""".lstrip(),
    )

    safety = load_concurrency_safety_config(str(cfg))

    assert safety.preserve_branches.enabled is False
    assert safety.preserve_branches.require_manifest is False
    assert safety.stash_leak_alarm.warn_ttl_seconds == 120
    assert safety.stash_leak_alarm.block_ttl_seconds == 900
    assert safety.plan_claims.require_bilateral_proof is False
    assert safety.resource_leases.default_ttl_seconds == 45
    assert safety.resource_leases.critical_domains == ("payments", "deploy")


def test_invalid_partial_projection_falls_back_safely(tmp_path: Path) -> None:
    cfg = write_config(
        tmp_path,
        """
concurrency_safety:
  enabled: sometimes
  stash_leak_alarm:
    warn_ttl_seconds: -1
    block_ttl_seconds: 10
  resource_leases:
    default_ttl_seconds: zero
    critical_domains: auth
""".lstrip(),
    )

    safety = load_concurrency_safety_config(str(cfg))

    assert safety.enabled is True
    assert safety.stash_leak_alarm.warn_ttl_seconds == 600
    assert safety.stash_leak_alarm.block_ttl_seconds == 600
    assert safety.resource_leases.default_ttl_seconds == 1800
    assert safety.resource_leases.critical_domains == (
        "auth",
        "billing",
        "migrations",
        "infrastructure",
    )

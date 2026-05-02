# SCOPE: both
"""Concurrency safety configuration projection for Cognitive OS consumers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional

from lib.config_loader import load_structured

DEFAULT_CRITICAL_DOMAINS = ("auth", "billing", "migrations", "infrastructure")


@dataclass(frozen=True)
class PreserveBranchesConfig:
    enabled: bool = True
    require_manifest: bool = True


@dataclass(frozen=True)
class StashLeakAlarmConfig:
    warn_ttl_seconds: int = 600
    block_ttl_seconds: int = 3600


@dataclass(frozen=True)
class PlanClaimsConfig:
    require_bilateral_proof: bool = True


@dataclass(frozen=True)
class ResourceLeasesConfig:
    critical_domains: tuple[str, ...] = DEFAULT_CRITICAL_DOMAINS
    default_ttl_seconds: int = 1800


@dataclass(frozen=True)
class ConcurrencySafetyConfig:
    enabled: bool = True
    preserve_branches: PreserveBranchesConfig = field(default_factory=PreserveBranchesConfig)
    stash_leak_alarm: StashLeakAlarmConfig = field(default_factory=StashLeakAlarmConfig)
    plan_claims: PlanClaimsConfig = field(default_factory=PlanClaimsConfig)
    resource_leases: ResourceLeasesConfig = field(default_factory=ResourceLeasesConfig)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["resource_leases"]["critical_domains"] = list(self.resource_leases.critical_domains)
        return data


def _as_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "1", "on"}:
            return True
        if normalized in {"false", "no", "0", "off"}:
            return False
    return default


def _as_positive_int(value: Any, default: int) -> int:
    if isinstance(value, bool):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _as_str_tuple(value: Any, default: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(value, list):
        return default
    cleaned = tuple(str(item).strip() for item in value if str(item).strip())
    return cleaned or default


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def load_concurrency_safety_config(config_path: Optional[str] = None) -> ConcurrencySafetyConfig:
    raw = _mapping(load_structured(config_path).get("concurrency_safety"))
    preserve_raw = _mapping(raw.get("preserve_branches"))
    stash_raw = _mapping(raw.get("stash_leak_alarm"))
    plan_raw = _mapping(raw.get("plan_claims"))
    leases_raw = _mapping(raw.get("resource_leases"))
    stash_warn = _as_positive_int(stash_raw.get("warn_ttl_seconds"), 600)
    stash_block = max(_as_positive_int(stash_raw.get("block_ttl_seconds"), 3600), stash_warn)
    return ConcurrencySafetyConfig(
        enabled=_as_bool(raw.get("enabled"), True),
        preserve_branches=PreserveBranchesConfig(
            enabled=_as_bool(preserve_raw.get("enabled"), True),
            require_manifest=_as_bool(preserve_raw.get("require_manifest"), True),
        ),
        stash_leak_alarm=StashLeakAlarmConfig(
            warn_ttl_seconds=stash_warn,
            block_ttl_seconds=stash_block,
        ),
        plan_claims=PlanClaimsConfig(
            require_bilateral_proof=_as_bool(plan_raw.get("require_bilateral_proof"), True)
        ),
        resource_leases=ResourceLeasesConfig(
            critical_domains=_as_str_tuple(leases_raw.get("critical_domains"), DEFAULT_CRITICAL_DOMAINS),
            default_ttl_seconds=_as_positive_int(leases_raw.get("default_ttl_seconds"), 1800),
        ),
    )


def project_runtime_dir(project_dir: str | Path) -> Path:
    return Path(project_dir) / ".cognitive-os" / "runtime"

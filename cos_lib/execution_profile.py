# SCOPE: both
"""Capability-centric execution profiles for durable model routing.

This module defines the stable execution intent for a task independently from
the currently preferred model, gateway, or provider. Model selection should be
a second step that satisfies the execution profile, not the starting point.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Dict, Optional


@dataclass(frozen=True)
class ExecutionProfile:
    """Stable execution contract for a task.

    The profile describes *what kind of execution is needed*, not *which model
    must be used*. Adapters and routers can then resolve this profile to the
    best current model or provider.
    """

    id: str
    description: str
    min_reasoning: int = 0
    min_speed: int = 0
    min_code: int = 0
    min_context_window: int = 0
    max_total_cost_per_1m: Optional[float] = None
    require_local: bool = False
    prefer_free: bool = False
    allow_advisor: bool = False

    def matches_capabilities(self, caps: Dict[str, float]) -> bool:
        """Return True when a model capability dict satisfies this profile."""
        if self.require_local and not caps.get("local", False):
            return False
        if caps.get("reasoning", 0) < self.min_reasoning:
            return False
        if caps.get("speed", 0) < self.min_speed:
            return False
        if caps.get("code", 0) < self.min_code:
            return False
        if caps.get("context", 0) < self.min_context_window:
            return False
        if self.max_total_cost_per_1m is not None:
            total_cost = caps.get("cost_per_1m_in", 0) + caps.get("cost_per_1m_out", 0)
            if total_cost > self.max_total_cost_per_1m:
                return False
        return True

    def rank_key(self, caps: Dict[str, float]) -> tuple:
        """Return a sortable key for choosing between compatible models."""
        total_cost = caps.get("cost_per_1m_in", 0) + caps.get("cost_per_1m_out", 0)
        return (
            1 if self.require_local and caps.get("local", False) else 0,
            1 if self.prefer_free and total_cost == 0 else 0,
            caps.get("reasoning", 0) - self.min_reasoning,
            caps.get("code", 0) - self.min_code,
            caps.get("speed", 0) - self.min_speed,
            caps.get("context", 0) - self.min_context_window,
            -total_cost,
        )


FRONTIER_REASONING = ExecutionProfile(
    id="frontier_reasoning",
    description="High-stakes reasoning, design, or debugging.",
    min_reasoning=8,
)

HIGH_CODE_GENERATION = ExecutionProfile(
    id="high_code_generation",
    description="Code-generation and implementation-heavy work.",
    min_reasoning=5,
    min_code=7,
    max_total_cost_per_1m=20.0,
    allow_advisor=True,
)

FAST_TURNAROUND = ExecutionProfile(
    id="fast_turnaround",
    description="Latency-sensitive tasks where speed matters most.",
    min_speed=7,
)

LONG_CONTEXT_ANALYSIS = ExecutionProfile(
    id="long_context_analysis",
    description="Repository-wide or document-heavy work requiring long context.",
    min_reasoning=6,
    min_context_window=200_000,
)

LOW_COST_BULK = ExecutionProfile(
    id="low_cost_bulk",
    description="Cheap bulk processing, scaffolding, or low-risk transformations.",
    min_code=4,
    max_total_cost_per_1m=5.0,
    prefer_free=True,
)

BALANCED_GENERAL = ExecutionProfile(
    id="balanced_general",
    description="Default balanced profile when task intent is unknown.",
    min_reasoning=6,
)

LOCAL_PRIVATE_EXECUTION = ExecutionProfile(
    id="local_private_execution",
    description="Local/private execution even if capability is lower.",
    min_code=4,
    require_local=True,
)


TASK_EXECUTION_PROFILES: Dict[str, ExecutionProfile] = {
    "sdd-propose": FRONTIER_REASONING,
    "sdd-design": FRONTIER_REASONING,
    "systematic-debugging": FRONTIER_REASONING,
    "sdd-improve": FRONTIER_REASONING,
    "sdd-apply": HIGH_CODE_GENERATION,
    "sdd-tasks": HIGH_CODE_GENERATION,
    "test-driven-development": HIGH_CODE_GENERATION,
    "sdd-archive": FAST_TURNAROUND,
    "doc-sync": FAST_TURNAROUND,
    "format": FAST_TURNAROUND,
    "sdd-explore": LONG_CONTEXT_ANALYSIS,
    "repo-scout": LONG_CONTEXT_ANALYSIS,
    "exhaustive-prompt": LONG_CONTEXT_ANALYSIS,
    "document-feature": LOW_COST_BULK,
    "skill-creator": LOW_COST_BULK,
    "openrouter/free": LOW_COST_BULK,
}

PROFILE_REGISTRY: Dict[str, ExecutionProfile] = {
    profile.id: profile
    for profile in (
        FRONTIER_REASONING,
        HIGH_CODE_GENERATION,
        FAST_TURNAROUND,
        LONG_CONTEXT_ANALYSIS,
        LOW_COST_BULK,
        BALANCED_GENERAL,
        LOCAL_PRIVATE_EXECUTION,
    )
}

SKILL_TIER_PROFILES: Dict[str, ExecutionProfile] = {
    "frontier": FRONTIER_REASONING,
    "balanced": BALANCED_GENERAL,
    "cheap": LOW_COST_BULK,
}


def resolve_execution_profile(
    task_type: str,
    *,
    budget_remaining: Optional[float] = None,
    prefer_local: bool = False,
) -> ExecutionProfile:
    """Resolve a task into a stable execution profile.

    `prefer_local` and budget constraints modify the stable base profile without
    forcing the caller to reason about provider or model names directly.
    """
    profile = TASK_EXECUTION_PROFILES.get(task_type, BALANCED_GENERAL)

    if prefer_local:
        return replace(
            LOCAL_PRIVATE_EXECUTION,
            id=f"{profile.id}+local",
            description=f"{profile.description} Routed through a local/private requirement.",
            min_reasoning=min(profile.min_reasoning, LOCAL_PRIVATE_EXECUTION.min_reasoning),
            min_speed=min(profile.min_speed, LOCAL_PRIVATE_EXECUTION.min_speed),
            min_code=max(profile.min_code, LOCAL_PRIVATE_EXECUTION.min_code),
        )

    if budget_remaining is not None and budget_remaining <= 0.01:
        return replace(
            profile,
            id=f"{profile.id}+budget_floor",
            prefer_free=True,
            max_total_cost_per_1m=0.0,
        )

    return profile


def resolve_runtime_execution_profile(
    task_type: str,
    *,
    skill_requirements: Optional[dict] = None,
    budget_remaining: Optional[float] = None,
    prefer_local: bool = False,
) -> ExecutionProfile:
    """Resolve runtime intent from task type plus optional skill routing data.

    This is the dispatch-facing resolver. It keeps provider/model names out of
    the first decision by translating skill frontmatter such as `tier:` and
    `need_long_context:` into the same stable execution profile contract used by
    model routing.
    """
    req = skill_requirements if isinstance(skill_requirements, dict) else {}

    explicit_profile = req.get("execution_profile") or req.get("capability_profile")
    if isinstance(explicit_profile, str) and explicit_profile in PROFILE_REGISTRY:
        profile = PROFILE_REGISTRY[explicit_profile]
    elif bool(req.get("need_long_context", False)):
        profile = LONG_CONTEXT_ANALYSIS
    else:
        tier = req.get("tier")
        profile = SKILL_TIER_PROFILES.get(tier, resolve_execution_profile(task_type)) if isinstance(tier, str) else resolve_execution_profile(task_type)

    if prefer_local:
        return replace(
            LOCAL_PRIVATE_EXECUTION,
            id=f"{profile.id}+local",
            description=f"{profile.description} Routed through a local/private requirement.",
            min_reasoning=min(profile.min_reasoning, LOCAL_PRIVATE_EXECUTION.min_reasoning),
            min_speed=min(profile.min_speed, LOCAL_PRIVATE_EXECUTION.min_speed),
            min_code=max(profile.min_code, LOCAL_PRIVATE_EXECUTION.min_code),
        )

    if budget_remaining is not None and budget_remaining <= 0.01:
        return replace(
            profile,
            id=f"{profile.id}+budget_floor",
            prefer_free=True,
            max_total_cost_per_1m=0.0,
        )

    return profile


def provider_cascade_for_profile(
    profile: ExecutionProfile,
    default_cascade: list[str],
) -> list[str]:
    """Return a provider cascade shaped by execution capability intent.

    Explicit provider overrides are handled by callers before this helper.
    """
    cascade = list(default_cascade)
    if len(cascade) <= 1:
        return cascade

    provider_names = ("claude", "qwen")
    other = [provider for provider in cascade if provider not in provider_names]

    if profile.id.startswith((FRONTIER_REASONING.id, LONG_CONTEXT_ANALYSIS.id)):
        ordered_known = [provider for provider in ("claude", "qwen") if provider in cascade]
    elif profile.id.startswith((LOW_COST_BULK.id, FAST_TURNAROUND.id)):
        ordered_known = [provider for provider in ("qwen", "claude") if provider in cascade]
    else:
        return cascade

    return ordered_known + other

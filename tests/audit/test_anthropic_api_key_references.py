"""Audit remaining ANTHROPIC_API_KEY references by policy category.

This is intentionally stricter than a grep ban: explicit CI, explicit direct API
providers and tests may mention the variable, but default local/operator
surfaces and historical docs should not introduce unclassified references.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

pytestmark = [pytest.mark.audit]

IGNORED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
}
IGNORED_SUFFIXES = {".pyc"}
IGNORED_PATHS = {
    ".env",
    ".claude/settings.local.json",
}
IGNORED_PATH_PREFIXES = (
    ".claude/worktrees/",
    ".claude/plugins/",
    ".cognitive-os/",
    ".engram/",
    "reference/",
)


@dataclass(frozen=True)
class AllowedReference:
    path: str
    category: str
    reason: str


ALLOWED_REFERENCES: tuple[AllowedReference, ...] = (
    # Explicit CI direct API: GitHub Actions have no local logged-in Claude Code account.
    AllowedReference(".github/workflows/claude-interactive.yml.disabled", "ci_explicit", "Claude Code action secret"),
    AllowedReference(".github/workflows/claude-issue-triage.yml.disabled", "ci_explicit", "Claude Code action secret"),
    AllowedReference(".github/workflows/claude-pr-review.yml.disabled", "ci_explicit", "Claude Code action secret"),
    AllowedReference("docs/05-Methodology/root/automation.md", "ci_explicit_docs", "Documents CI-only Claude action secret"),
    AllowedReference("workflows/README.md", "ci_explicit_docs", "Documents CI-only Claude action secret"),

    # Direct API implementation/policy surfaces; all must remain config-gated.
    AllowedReference("cognitive-os.yaml", "direct_api_opt_in_config", "claude_sdk opt-in disabled by default"),
    AllowedReference("lib/anthropic_direct_policy.py", "direct_api_policy", "central policy helper"),
    AllowedReference("lib/claude_executor.py", "direct_api_executor", "advisor fallback checks"),
    AllowedReference("packages/llm-providers/lib/__init__.py", "direct_api_provider", "provider inventory docs"),
    AllowedReference("pyproject.toml", "direct_api_optional_extra", "optional claude-sdk extra docs"),
    AllowedReference("rules/model-routing.md", "direct_api_routing_docs", "advisor preconditions"),
    AllowedReference("skills/llm-status/SKILL.md", "direct_api_status_docs", "status output example"),

    # Advisor MCP is an optional external-advisor provider and is separately contract-tested.
    AllowedReference("packages/advisor-mcp/README.md", "external_advisor_docs", "policy-gated provider docs"),
    AllowedReference("packages/advisor-mcp/cos-package.yaml", "external_advisor_metadata", "provider metadata"),
    AllowedReference("docs/04-Concepts/architecture/advisor-mcp-architecture-review.md", "external_advisor_policy_docs", "architecture review"),

    # Optional service docs with explicit non-default override.
    AllowedReference("infra/cognee/README.md", "optional_service_override_docs", "Anthropic override example only"),

    # Direct policy docs. Historical docs intentionally avoid the exact string.
    AllowedReference("docs/04-Concepts/architecture/direct-anthropic-api-policy.md", "policy_docs", "canonical policy"),
    AllowedReference("docs/02-Decisions/adrs/ADR-131-local-ci-migration.md", "policy_docs", "local CI migration names CI-only secret removal"),
    AllowedReference("docs/02-Decisions/adrs/ADR-139-account-agnostic-multi-provider-runtime.md", "policy_docs", "account-agnostic credential policy names legacy env var as banned/default-unsafe"),
    AllowedReference("docs/09-Quality/manual-tests/service-control-plane-proof-drills.md", "service_control_plane_security_docs", "manual drill verifies credential redaction"),
    AllowedReference("scripts/cos_auth_probe.py", "auth_probe_policy", "provider-specific auth readiness probe checks env presence only"),
    AllowedReference("tests/audit/test_adr_139_141_142_cloud_surfaces.py", "audit_test", "guards blocked credential defaults"),
    AllowedReference("tests/unit/test_service_control_plane_local_queue.py", "test_fixture", "secret redaction fixture"),
    AllowedReference("manifests/credential-safe-scripts.yaml", "credential_safe_runner_policy", "explicit denylist for credential-safe script runner"),
    AllowedReference("hooks/example-prompt-hook.sh.disabled", "disabled_example", "disabled prompt hook example documents env placeholder only"),
    AllowedReference("manifests/provider-profiles.yaml", "provider_profile_metadata", "provider profile declares env slot name, not a credential value"),

    # Explicit examples / benchmark / arena / tests.
    AllowedReference("docs/08-References/benchmarks/so-vs-vanilla-tasks.yaml", "fake_benchmark_secret", "fake key example"),
    AllowedReference("env.example", "commented_opt_in_example", "commented claude_sdk opt-in only"),
    AllowedReference("tests/arena/arena-config.yaml", "cost_bearing_test_config", "explicit arena providers"),
    AllowedReference("tests/unit/test_advisor_integration.py", "test_fixture", "test-only env setup"),
    AllowedReference("tests/unit/test_anthropic_direct_policy.py", "test_fixture", "canonical env helper tests"),
    AllowedReference("tests/unit/test_advisor_mcp.py", "test_fixture", "test-only env setup and docs guard"),
    AllowedReference("tests/unit/test_bootstrap.py", "test_fixture", "env merge preservation fixture"),
    AllowedReference("tests/unit/test_claude_executor.py", "test_fixture", "safe env redaction test"),
    AllowedReference("tests/unit/test_direct_anthropic_default_surfaces.py", "audit_test", "guards this policy"),
    AllowedReference("tests/unit/test_providers/test_claude_sdk.py", "test_fixture", "provider config fixtures"),
    AllowedReference("tests/audit/test_anthropic_api_key_references.py", "audit_test", "classifies this policy"),

    # Extension docs that explicitly say no direct key required.
    AllowedReference("packages/cos-advisory-llm/README.md", "native_prompt_hook_docs", "states no direct key required"),
    AllowedReference("docs/03-PoCs/research/orchestration-gaps/background-agent-patterns.md", "auth_rotation_research", "research report discusses detached-agent credential rotation risk"),

    # Research/cross-provider evaluation reports that reference env var in analysis context
    AllowedReference("docs/03-PoCs/research/ifixai-annex-b-cross-judge-2026-05-11.md", "provider_eval_research", "cross-judge evaluation report mentions env var in provider auth analysis"),
    AllowedReference("docs/03-PoCs/research/ifixai-annex-d-provider-imeisplit-2026-05-11.md", "provider_eval_research", "provider IMEI-split evaluation report mentions env var in auth context"),
)

_ALLOWED_BY_PATH = {entry.path: entry for entry in ALLOWED_REFERENCES}


def _iter_tracked_paths() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
    )
    return [
        PROJECT_ROOT / raw.decode("utf-8")
        for raw in result.stdout.split(b"\0")
        if raw
    ]


def _iter_text_files() -> list[Path]:
    paths: list[Path] = []
    for path in _iter_tracked_paths():
        if not path.is_file():
            continue
        rel_path = path.relative_to(PROJECT_ROOT).as_posix()
        rel_parts = set(path.relative_to(PROJECT_ROOT).parts)
        if rel_parts & IGNORED_DIRS:
            continue
        if rel_path in IGNORED_PATHS:
            continue
        if rel_path.startswith(IGNORED_PATH_PREFIXES):
            continue
        if path.suffix in IGNORED_SUFFIXES:
            continue
        paths.append(path)
    return paths


def _references() -> dict[str, list[int]]:
    found: dict[str, list[int]] = {}
    for path in _iter_text_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (FileNotFoundError, UnicodeDecodeError):
            continue
        lines = [idx for idx, line in enumerate(text.splitlines(), 1) if "ANTHROPIC_API_KEY" in line]
        if lines:
            found[path.relative_to(PROJECT_ROOT).as_posix()] = lines
    return found


def test_all_anthropic_api_key_references_are_classified() -> None:
    found = _references()
    unclassified = sorted(set(found) - set(_ALLOWED_BY_PATH))
    stale_allowlist = sorted(set(_ALLOWED_BY_PATH) - set(found))

    assert not unclassified, (
        "Unclassified ANTHROPIC_API_KEY references found. Either remove the "
        "reference from default/local surfaces, or add an explicit category to "
        "ALLOWED_REFERENCES with a reason:\n"
        + "\n".join(f"- {path}: lines {found[path]}" for path in unclassified)
    )
    assert not stale_allowlist, (
        "Stale ANTHROPIC_API_KEY audit allowlist entries; remove them so the "
        "audit remains precise:\n"
        + "\n".join(f"- {path}" for path in stale_allowlist)
    )


def test_no_forbidden_default_surface_references() -> None:
    found = _references()
    forbidden_prefixes = (
        "docker-compose",
        "scripts/cos-bootstrap",
        "packages/cos-advisory-llm/cos-package.yaml",
        "packages/ecosystem-tools/skills/cognee-integration/",
    )
    violations = [
        path
        for path in found
        if path.startswith(forbidden_prefixes)
        and path not in _ALLOWED_BY_PATH
    ]
    assert not violations, "Forbidden default-surface references: " + ", ".join(violations)


def test_audit_categories_are_unique_and_documented() -> None:
    paths = [entry.path for entry in ALLOWED_REFERENCES]
    assert len(paths) == len(set(paths)), "Duplicate ANTHROPIC_API_KEY audit allowlist path"
    for entry in ALLOWED_REFERENCES:
        assert entry.category
        assert entry.reason

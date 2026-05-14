from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

REPO = Path(__file__).resolve().parents[2]
AUTHORITY_DOC = REPO / "docs" / "04-Concepts" / "architecture" / "primitive-authority-write-effects.md"
CONSUMER_DOC = REPO / "docs" / "04-Concepts" / "architecture" / "consumer-project-primitive-accessibility.md"
ADR_146 = REPO / "docs" / "02-Decisions" / "adrs" / "ADR-146-primitive-readiness-ledger.md"


def test_primitive_authority_write_effects_doc_names_existing_enforcement_surfaces() -> None:
    text = AUTHORITY_DOC.read_text(encoding="utf-8")

    required_refs = {
        "manifests/primitive-scope-classification.yaml",
        "manifests/primitive-consumer-availability.yaml",
        "manifests/shell-ci-projection.yaml",
        "manifests/protected-config-write-policy.yaml",
        "manifests/primitive-coherence.yaml",
        "lib/consumer_improvement_proposals.py",
        "scripts/portable_ai_real_consumer_smoke.py",
        "tests/security/test_boundary_enforcement_p0.py",
        "tests/contracts/test_primitive_scope_governance.py",
    }
    missing = sorted(ref for ref in required_refs if ref not in text)
    assert not missing, "authority doc must link existing write-boundary evidence:\n" + "\n".join(missing)

    for authority_class in [
        "observe-only",
        "propose-only",
        "profile-projection-write",
        "project-local-write",
        "os-maintainer-write",
        "dangerous-human-approved",
    ]:
        assert authority_class in text

    assert "dynamic write-effects audit" in text


def test_consumer_projection_docs_do_not_revert_to_claude_codex_only_claim() -> None:
    joined = CONSUMER_DOC.read_text(encoding="utf-8") + "\n" + ADR_146.read_text(encoding="utf-8")

    stale_phrases = [
        "proof signs only Claude Code and OpenAI Codex default installs",
        "automated for Claude/Codex default installs",
        "current Claude/Codex proof boundary",
    ]
    offenders = [phrase for phrase in stale_phrases if phrase in joined]
    assert not offenders, "consumer projection docs regressed to stale Claude/Codex-only wording"

    consumer_text = CONSUMER_DOC.read_text(encoding="utf-8")
    for implemented_harness in ["agents-md", "opencode", "cursor", "qwen-code", "kimi-code", "shell-ci"]:
        assert implemented_harness in consumer_text
    assert "Structural projection is not runtime enforcement" in ADR_146.read_text(encoding="utf-8")

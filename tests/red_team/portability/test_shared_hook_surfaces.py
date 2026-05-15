"""Family-specific portability proof for reviewed shared hook surfaces."""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SHARED_HOOKS = [
    "hooks/aguara-scan.sh",
    "hooks/ai-provider-identity-guard.sh",
    "hooks/code-review-on-commit.sh",
    "hooks/confidentiality-enforcer.sh",
    "hooks/destructive-rm-blocker.sh",
    "hooks/doc-sync-detector.sh",
    "hooks/git-commit-scope-guard.sh",
    "hooks/global-verify.sh",
    "hooks/guardrails-validator.sh",
    "hooks/mcp-scan.sh",
    "hooks/parry-scan.sh",
    "hooks/predev-completeness-check.sh",
    "hooks/private-mode-gate.sh",
    "hooks/private-mode-metrics-gate.sh",
    "hooks/rate-limit-drain.sh",
    "hooks/rate-limit-precheck.sh",
    "hooks/rate-limiter.sh",
    "hooks/reinvention-check.sh",
    "hooks/release-guard.sh",
    "hooks/semgrep-scan.sh",
    "hooks/valkey-ensure.sh",
    "hooks/worktree-submodule-fix.sh",
]


def test_shared_hooks_have_portable_headers_and_no_source_checkout_paths() -> None:
    for rel in SHARED_HOOKS:
        text = (REPO / rel).read_text(encoding="utf-8")
        assert "SCOPE: both" in "\n".join(text.splitlines()[:8]), rel
        assert "/Users/" not in text, rel
        assert "matias" not in text.lower(), rel
        assert "SCOPE: both" in text, rel

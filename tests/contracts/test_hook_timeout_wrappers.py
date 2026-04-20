"""Contract test: D4 timeout wrappers in ADR-028 fixed hooks.

Verifies that every hook listed below wraps its python3 invocation in
`timeout <N>` — preventing hanging subprocess calls from blocking session
lifecycle or tool execution.

A hook passes if EITHER:
  1. The file contains `timeout <number>` (a numeric timeout wrapper), OR
  2. The file no longer exists (was legitimately deleted/replaced).

Fails if a D4-fixed hook regresses by dropping the timeout wrapper.

Source: ADR-028 D4 fix (2026-04-20) — CONCERN: subproc_without_timeout.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HOOKS_DIR = PROJECT_ROOT / "hooks"

# These are the hooks that the D4 audit fixed. Each must keep `timeout <N>`
# wrapping any python3/python subprocess call, or be deleted entirely.
D4_HOOKS = [
    "orchestrator-mode-detect.sh",
    "session-hygiene.sh",
    "ecosystem-check.sh",
    "usage-health-check.sh",
    "adr-detector.sh",
    "code-review-on-commit.sh",
    "mlflow-sync.sh",
]

# Pattern: `timeout` followed by whitespace and at least one digit
_TIMEOUT_RE = re.compile(r"\btimeout\s+\d+")


def _has_timeout_wrapper(path: Path) -> bool:
    """Return True if the file contains at least one `timeout <N>` invocation."""
    content = path.read_text(encoding="utf-8", errors="replace")
    return bool(_TIMEOUT_RE.search(content))


def _hook_path(name: str) -> Path:
    return HOOKS_DIR / name


# ---------------------------------------------------------------------------
# Parametrized contract test
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("hook_name", D4_HOOKS)
def test_d4_hook_has_timeout_wrapper(hook_name: str):
    """Hook must either not exist (deleted) or contain `timeout <N>` wrapping python3."""
    path = _hook_path(hook_name)

    if not path.exists():
        # Hook was removed — contract satisfied (no regression possible)
        pytest.skip(f"{hook_name} does not exist (deleted); timeout regression not possible")

    assert _has_timeout_wrapper(path), (
        f"REGRESSION: {hook_name} no longer contains a `timeout <N>` wrapper.\n"
        f"The D4 fix (ADR-028, 2026-04-20) added timeout wrappers to prevent hanging.\n"
        f"Re-add `timeout <seconds> python3 ...` around the python3 invocation."
    )


# ---------------------------------------------------------------------------
# Additional structural checks
# ---------------------------------------------------------------------------

class TestTimeoutWrapperQuality:
    """Spot-checks for timeout value sanity (not 0, not unreasonably long)."""

    @pytest.mark.parametrize("hook_name", D4_HOOKS)
    def test_timeout_value_is_positive(self, hook_name: str):
        """Timeout value must be a positive integer (> 0)."""
        path = _hook_path(hook_name)
        if not path.exists():
            pytest.skip(f"{hook_name} not found")

        content = path.read_text(encoding="utf-8", errors="replace")
        matches = _TIMEOUT_RE.findall(content)
        if not matches:
            pytest.skip(f"{hook_name} has no timeout wrapper (covered by parametrized test)")

        for match in matches:
            # Extract the number from "timeout <N>"
            parts = match.split()
            assert len(parts) == 2, f"Unexpected timeout format: {match!r}"
            value = int(parts[1])
            assert value > 0, (
                f"{hook_name}: timeout value must be positive, got {value}"
            )

    @pytest.mark.parametrize("hook_name", D4_HOOKS)
    def test_timeout_value_under_300_seconds(self, hook_name: str):
        """Timeout values should be reasonable (< 300s) for hook use cases."""
        path = _hook_path(hook_name)
        if not path.exists():
            pytest.skip(f"{hook_name} not found")

        content = path.read_text(encoding="utf-8", errors="replace")
        matches = _TIMEOUT_RE.findall(content)
        if not matches:
            pytest.skip(f"{hook_name} has no timeout wrapper")

        for match in matches:
            parts = match.split()
            value = int(parts[1])
            assert value < 300, (
                f"{hook_name}: timeout value {value}s is unreasonably large for a hook. "
                f"Hooks should complete in < 300s to avoid blocking the harness."
            )


class TestHookSyntaxValidity:
    """bash -n syntax check on each D4 hook to catch shell parse errors."""

    @pytest.mark.parametrize("hook_name", D4_HOOKS)
    def test_hook_passes_bash_n_syntax_check(self, hook_name: str):
        """bash -n must succeed (exit 0) — no shell syntax errors introduced."""
        import subprocess

        path = _hook_path(hook_name)
        if not path.exists():
            pytest.skip(f"{hook_name} not found")

        result = subprocess.run(
            ["bash", "-n", str(path)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode == 0, (
            f"{hook_name} failed `bash -n` syntax check:\n{result.stderr}"
        )

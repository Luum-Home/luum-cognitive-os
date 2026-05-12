# SCOPE: both
"""Portability probes for hooks/adr-detector.sh.

The hook is a PostToolUse Bash handler that fires on `git commit` commands and
must skip commits that touch only ADR files (recursive-detection guard at
hooks/adr-detector.sh:67).

Falsification probes:

1. Non-commit Bash input must exit 0 with no side effects.
2. The recursive-detection filter must reject canonical ADR paths
   (`docs/02-Decisions/adrs/ADR-NNN-*.md`). If the filter pattern drifts back to the
   removed `docs/04-Concepts/architecture/adrs/` namespace, this test fails.
3. The filter must NOT swallow non-ADR paths.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
HOOK = REPO_ROOT / "hooks" / "adr-detector.sh"


def _extract_filter_pattern() -> str:
    """Pull the grep pattern from the hook source so the test breaks if it drifts."""
    src = HOOK.read_text()
    match = re.search(r"grep -v '(\^docs/[^']+)'", src)
    assert match, "could not locate ADR filter pattern in adr-detector.sh"
    return match.group(1)


def test_non_commit_bash_exits_zero() -> None:
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "ls -la"},
        "tool_response": "",
    }
    result = subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 0, f"hook must exit 0 on non-commit Bash; stderr={result.stderr}"


def test_filter_rejects_canonical_adr_path() -> None:
    """Falsification: if the filter ever points at a non-canonical namespace
    (e.g. the removed docs/04-Concepts/architecture/adrs/ stubs), this fails."""
    pattern = _extract_filter_pattern()
    canonical_paths = [
        "docs/02-Decisions/adrs/ADR-100-example.md",
        "docs/02-Decisions/adrs/INDEX.md",
    ]
    result = subprocess.run(
        ["grep", "-v", pattern],
        input="\n".join(canonical_paths) + "\n",
        text=True,
        capture_output=True,
    )
    # grep -v returning empty stdout means all lines matched the pattern (i.e. were filtered out).
    assert result.stdout.strip() == "", (
        f"filter pattern {pattern!r} must reject canonical docs/02-Decisions/adrs/ paths; "
        f"leaked: {result.stdout!r}"
    )


def test_filter_preserves_non_adr_paths() -> None:
    pattern = _extract_filter_pattern()
    non_adr = ["src/foo.py", "hooks/bar.sh", "tests/baz_test.py"]
    result = subprocess.run(
        ["grep", "-v", pattern],
        input="\n".join(non_adr) + "\n",
        text=True,
        capture_output=True,
    )
    leaked = sorted(line for line in result.stdout.strip().split("\n") if line)
    assert leaked == sorted(non_adr), (
        f"filter must preserve non-ADR paths; pattern={pattern!r} kept {leaked}"
    )

#!/usr/bin/env python3
"""Pins the instrument-productivity findings of lote 34 (2026-08-15).

Two jobs:

1. Guard the evidence script itself. Its write-detection had confirmed false
   positives (hooks whose artifacts are megabytes on disk were reported as
   "never written"), so the regressions worth pinning are the write paths it
   learned to resolve, not the verdict counts.

2. Pin the two confirmed defects as CHARACTERIZATION tests. They assert the
   bug is still there, with the fix spelled out. When the operator applies the
   patch in docs/06-Daily/reports/lote34-instrumentos-2026-08-15.md, these
   tests fail loudly and get flipped to assert the fixed form. A silent revert
   cannot happen unnoticed either way.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "audit_instrument_productivity.py"

sys.path.insert(0, str(REPO / "scripts"))


def _load():
    import importlib

    return importlib.import_module("audit_instrument_productivity")


# --------------------------------------------------------------------------
# 1. The evidence script must keep resolving every known write path.
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "body,expected",
    [
        # Variable assignment + append redirect.
        ('OUT="$METRICS_DIR/a.jsonl"\necho x >> "$OUT"\n', "a.jsonl"),
        # Variable assignment + shared helper. The single most common form;
        # missing it reported ~every producing hook as "no-artifact".
        ('OUT="$METRICS_DIR/b.jsonl"\nsafe_jsonl_append "$OUT" "$E"\n', "b.jsonl"),
        # Helper called with an inline path, no variable in between
        # (hooks/codebase-itinerary-capture.sh:179).
        ('safe_jsonl_append "$METRICS_DIR/c.jsonl" "$LINE"\n', "c.jsonl"),
    ],
)
def test_write_detection_resolves_known_paths(body: str, expected: str) -> None:
    mod = _load()
    writes, _reads = mod.artifacts_for(body)
    assert expected in writes, f"write path not detected in:\n{body}"


def test_reader_is_not_counted_as_writer() -> None:
    """A hook that only reads must not be reported as producing the file."""
    mod = _load()
    writes, reads = mod.artifacts_for('IN="$METRICS_DIR/q.jsonl"\ntail -5 "$IN"\n')
    assert "q.jsonl" not in writes
    assert "q.jsonl" in reads


def test_census_matches_upstream_population() -> None:
    """Both audits must classify from the same rules, or the numbers diverge.

    This used to pin the instrument count to the literal 119. That number was a
    snapshot of a DEFECTIVE rule: the class came from filename tokens, and 82 of
    those 119 hooks had no instrument token at all — they reached the class
    through a final `else`. Pinning the output of a broken classifier turns the
    test into a ratchet that defends the bug.

    So the assertion now states the property the test was named for, computed
    live against the upstream census: the two scripts must agree hook-for-hook.
    It cannot go stale, and it fails loudly the day one of them grows a private
    copy of the rule again (which is exactly how the drift started).
    """
    mod = _load()
    spec = importlib.util.spec_from_file_location(
        "audit_gate_registration", REPO / "scripts" / "audit_gate_registration.py")
    upstream = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(upstream)

    mine = {r["name"]: r["class"] for r in mod.census().values()}
    theirs = {e["name"]: upstream.classify(e["name"], Path(real))[0]
              for real, e in upstream.census().items()}

    assert set(mine) == set(theirs), "the two censuses disagree about the population"
    disagreements = {n: (mine[n], theirs[n]) for n in mine if mine[n] != theirs[n]}
    assert not disagreements, f"class disagreements (mine, upstream): {disagreements}"
    assert mine, "empty census — the audit would report nothing and exit 0"


def test_script_is_read_only_toward_metrics() -> None:
    """The audit must never write telemetry — it is the evidence of the audit."""
    src = SCRIPT.read_text()
    for forbidden in ('"a"', "'a'", "'w'", '"w"'):
        assert f"open({forbidden}" not in src
    assert ".write_text(" not in src


def test_script_runs_and_uses_documented_exit_codes() -> None:
    proc = subprocess.run(
        [sys.executable, "-W", "ignore", str(SCRIPT)],
        cwd=REPO, capture_output=True, text=True, timeout=1800,
    )
    assert proc.returncode in (0, 1), f"unexpected exit {proc.returncode}"
    assert "class=instrument" in proc.stdout


# --------------------------------------------------------------------------
# 2. Characterization: the confirmed defects, still unfixed.
# --------------------------------------------------------------------------

EXIT_CODE_HOOKS = {
    "hooks/error-pipeline.sh": ".exit_code // \"0\"",
    "hooks/error-learning.sh": "stdin_field '.exit_code' '0'",
}


@pytest.mark.parametrize("rel,marker", sorted(EXIT_CODE_HOOKS.items()))
def test_exit_code_defect_is_still_present(rel: str, marker: str) -> None:
    """These hooks read a top-level .exit_code the harness does not send.

    The documented payload nests it (see
    docs/04-Concepts/architecture/agentic-mastery-operations.md):
        {"tool_response": {"content": "...", "exit_code": 1}}

    So EXIT_CODE always falls back to "0" and the hook exits immediately:
    21,046 invocations against 11 recorded rows.

    FIX (needs protected-config-write-guard review):
        jq -r '.tool_response.exit_code // .exit_code // "0"'

    When applied, flip this test to assert `.tool_response.exit_code`.
    """
    src = (REPO / rel).read_text()
    if ".tool_response.exit_code" in src:
        pytest.fail(
            f"{rel} now reads .tool_response.exit_code — the lote-34 fix "
            "landed. Update this test to assert the fixed form."
        )
    assert marker in src, f"{rel} changed shape; re-verify the lote-34 finding"


def test_doc_sync_detector_filter_still_excludes_repo_languages() -> None:
    """The filter admits only .go/.ts/.java; this repo is Python and Bash.

    3,565 tracked .py/.sh files against 195 .go/.ts/.java, so the hook discards
    nearly every edit: 1,991 runs, 0 rows, while cos_lib/singularity.py and
    hooks/_lib/singularity-suggestion.sh read the artifact it never writes.
    """
    src = (REPO / "hooks" / "doc-sync-detector.sh").read_text()
    if r"\.(go|ts|java)$" not in src:
        pytest.fail(
            "doc-sync-detector filter changed — re-verify the lote-34 finding "
            "and update this test."
        )


def test_stale_docs_consumers_still_exist() -> None:
    """Deleting doc-sync-detector would strand these readers. The cheap green."""
    out = subprocess.run(
        ["git", "grep", "-l", "stale-docs.jsonl", "--",
         "cos_lib/singularity.py", "hooks/_lib/singularity-suggestion.sh"],
        cwd=REPO, capture_output=True, text=True,
    ).stdout
    assert "cos_lib/singularity.py" in out
    assert "hooks/_lib/singularity-suggestion.sh" in out


def test_rate_limit_drain_reads_deprecated_queue_path() -> None:
    """The drain reads rate-limit-queue.json; the producer writes the .jsonl."""
    src = (REPO / "hooks" / "rate-limit-drain.sh").read_text()
    assert 'rate-limit-queue.json"' in src, (
        "drain no longer reads the legacy .json path — re-verify the finding"
    )

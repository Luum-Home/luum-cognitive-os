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
import json
import shutil
import subprocess
import sys
import tempfile
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
    "packages/skill-governance/hooks/skill-tracker.sh": ".exit_code // \"0\"",
}

# The measured contract. Reproduce every number here with
#   docs/05-Methodology/runbooks/error-pipeline-type-contract-2026-08-15/verify_type_contract.py
# over 57 harness transcripts:
#   1,962 Bash results — 1,837 objects, 125 strings (50 "Error: Exit code N",
#   75 other "Error: ..."), and ZERO occurrences of `exit_code` at any nesting
#   level for any tool.
TERNARY_PAYLOADS = [
    # (payload, expected TOOL_OUTCOME, note)
    ({"tool_response": {"stdout": "ok\n", "stderr": "", "interrupted": False,
                        "isImage": False, "noOutputExpected": False}},
     "ok", "success is an OBJECT — 1,837 of 1,962 real Bash results"),
    ({"tool_response": "Error: Exit code 1"},
     "failed", "the command RAN and exited non-zero — 50 real results"),
    ({"tool_response": "Error: Exit code 127"},
     "failed", "same class, different code"),
    ({"tool_response": 'Error: PreToolUse:Bash hook error: [bash "..."]: BLOCK'},
     "blocked", "a gate of THIS OS refused it — 75 real results, the "
                "single largest failure class, and not a command failure"),
    ({"tool_response": "Error: Permission for this action was denied"},
     "blocked", "permission denial — the command never ran either"),
    ({"tool_response": None}, "absent", "contract drift, and drift is NOT ok"),
    ({}, "absent", "no tool_response at all — drift, not success"),
]


def _classify(payload: dict, tree: Path | None = None) -> str:
    """Run the real shell classifier over a payload and return TOOL_OUTCOME."""
    lib = (tree or REPO) / "hooks" / "_lib" / "tool-outcome.sh"
    proc = subprocess.run(
        ["bash", "-c", f'set -uo pipefail; source "{lib}"; '
                       'classify_tool_outcome "$(cat)"; '
                       'printf "%s|%s" "$TOOL_OUTCOME" "$TOOL_EXIT_CODE"'],
        input=json.dumps(payload), capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.split("|")[0]


def _patched_tree() -> Path | None:
    """Materialise the runbook patch into a temp tree, or None if already applied."""
    if (REPO / "hooks" / "_lib" / "tool-outcome.sh").exists():
        return None  # the patch has landed; test the repo itself
    patch = (REPO / "docs" / "05-Methodology" / "runbooks"
             / "error-pipeline-type-contract-2026-08-15"
             / "error-pipeline-type-contract.patch")
    if not patch.exists():
        pytest.skip("neither the fix nor its patch is present")
    tmp = Path(tempfile.mkdtemp(prefix="tool-outcome-"))
    shutil.copytree(REPO / "hooks", tmp / "hooks", symlinks=True)
    (tmp / "packages" / "skill-governance").mkdir(parents=True)
    shutil.copytree(REPO / "packages" / "skill-governance" / "hooks",
                    tmp / "packages" / "skill-governance" / "hooks", symlinks=True)
    proc = subprocess.run(["git", "apply", "-p1", str(patch)],
                          cwd=tmp, capture_output=True, text=True)
    assert proc.returncode == 0, f"runbook patch no longer applies: {proc.stderr}"
    return tmp


@pytest.mark.parametrize("payload,expected,note",
                         TERNARY_PAYLOADS,
                         ids=[p[2].split("—")[0].strip()[:40] for p in TERNARY_PAYLOADS])
def test_tool_outcome_is_ternary_plus_drift(payload: dict, expected: str, note: str) -> None:
    """Success, command-failure and gate-block must classify differently.

    This replaces a characterization test that pinned the old hooks to
    `.exit_code`. That test was wrong on its own terms: it cited a documented
    payload `{"tool_response": {"content": ..., "exit_code": 1}}` that does not
    occur once in 2,686 real tool results, and it prescribed a "fix" that moved
    the read from one field the harness never sends to another field the harness
    never sends. Applying that fix would have flipped the test green while the
    hooks stayed exactly as dead as before — a test passing for the wrong
    reason, which is worse than a test failing.

    So this asserts the property instead of the defect: the classifier must
    separate the three real outcomes, and must never read absence as success.
    """
    tree = _patched_tree()
    assert _classify(payload, tree) == expected, note


def test_gate_blocks_are_not_command_failures() -> None:
    """The 75 largest "failures" are this OS blocking itself. Keep them apart.

    A PreToolUse gate refusing a command produces no exit code, no stdout and no
    stderr, because the command never ran. Bucketing it with real failures feeds
    the auto-repair loop our own guardrails and teaches the improvement loop from
    our own refusals.
    """
    tree = _patched_tree()
    gate = {"tool_response": 'Error: PreToolUse:Bash hook error: [bash "x"]: BLOCK'}
    real = {"tool_response": "Error: Exit code 2"}
    assert _classify(gate, tree) != _classify(real, tree)


@pytest.mark.parametrize("rel", sorted(EXIT_CODE_HOOKS))
def test_no_hook_reads_the_phantom_exit_code(rel: str) -> None:
    """Once the patch lands, no hook may go back to reading `.exit_code`.

    `exit_code` is absent from the payload at every nesting level, for every
    tool, in all 2,686 measured results. A permissive default on an absent field
    (`// "0"`) cannot tell "everything is fine" from "the field is gone", which
    is how these hooks logged 11 rows across 5,335 invocations each.
    """
    if not (REPO / "hooks" / "_lib" / "tool-outcome.sh").exists():
        pytest.skip("patch not applied yet; the ratchet arms on landing")
    src = (REPO / rel).read_text()
    for phantom in (".exit_code //", "stdin_field '.exit_code'",
                    ".tool_response.exit_code"):
        assert phantom not in src, (
            f"{rel} reads the phantom field via {phantom!r}. "
            "Classify on the type of tool_response — see hooks/_lib/tool-outcome.sh."
        )


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

"""Guard the payload-contract auditor: BLIND reads at 3, phantom fields at 9.

Two ratchets over the same auditor, both allowed to go down and never up:

* **BLIND** — a hook reading a harness-owned *verdict* field with a default that
  is itself a legal reading of that field, so it cannot tell "the tool
  succeeded" from "the field is not there".
* **PHANTOM** — a hook depending on a field that no payload the harness ever
  sent actually carried.  Measured by the canary against the in-repo corpus at
  ``tests/fixtures/payload-corpus/`` (see its README for re-capture).

See docs/06-Daily/reports/payload-contract-architecture-2026-08-15.md.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "audit_payload_field_contracts.py"
CAPTURE = ROOT / "scripts" / "capture_payload_corpus.py"
CORPUS = ROOT / "tests" / "fixtures" / "payload-corpus"

# Known BLIND reads as of 2026-08-15.  Shrinking this set is the point; growing
# it means a new hook was written with the defect the auditor exists to stop.
KNOWN_BLIND = {
    ("hooks/error-learning.sh", ".exit_code"),
    ("hooks/error-pipeline.sh", ".exit_code"),
    ("packages/skill-governance/hooks/skill-tracker.sh", ".exit_code"),
}

# Fields hooks depend on that no observed payload carried, as of 2026-08-15.
# Reproduce with:  scripts/audit_payload_field_contracts.py --canary
# Identical verdict on the 52-record corpus and on 2686 live payloads.
KNOWN_PHANTOM = {
    ("hooks/auto-refine.sh", ".tool_response.error"),
    ("hooks/error-learning.sh", ".exit_code"),
    ("hooks/error-pipeline.sh", ".exit_code"),
    ("hooks/post-git-orphan-notifier.sh", ".tool_response.exit_code"),
    ("hooks/skill-usage-tracker.sh", ".tool_response.duration_ms"),
    ("hooks/tool-sequence-capture.sh", ".tool_response.exit_code"),
    ("packages/quality-gates/hooks/completion-gate.sh", ".tool_response.error"),
    ("packages/skill-governance/hooks/skill-tracker.sh", ".exit_code"),
    ("packages/skill-governance/hooks/skill-tracker.sh", ".tool_response.model"),
}

# Every state a tool result arrives in.  All three were observed in real
# transcripts and each one reaches a hook differently; a corpus missing one of
# them cannot answer the question the canary exists to ask.
REQUIRED_STATES = {"object", "error_w_code", "error_no_code"}

# Tools whose payload shape the OS actually depends on.
REQUIRED_TOOLS = {"Bash", "Read", "Write", "Edit", "Agent"}


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def audit():
    return _load(SCRIPT, "_payload_audit")


@pytest.fixture(scope="module")
def capture():
    return _load(CAPTURE, "_payload_capture")


@pytest.fixture(scope="module")
def corpus_records():
    files = sorted(CORPUS.glob("*.jsonl"))
    assert files, f"no corpus under {CORPUS.name}; run scripts/capture_payload_corpus.py"
    recs = []
    for f in files:
        for line in f.read_text().splitlines():
            if line.strip():
                recs.append(json.loads(line))
    return recs


def test_script_exists_and_is_executable():
    assert SCRIPT.is_file(), f"missing {SCRIPT.name}"
    assert SCRIPT.stat().st_mode & 0o111, f"{SCRIPT.name} must be executable"


def test_scan_finds_payload_reads(audit):
    findings = audit.scan()
    assert len(findings) > 100, "auditor stopped seeing payload reads — regex rot?"


def test_blind_reads_do_not_grow(audit):
    blind = {(r["file"], r["field"]) for r in audit.scan() if r["verdict"] == "BLIND"}
    new = blind - KNOWN_BLIND
    assert not new, (
        "new BLIND payload read(s) — a verdict field is being read with a "
        f"permissive default: {sorted(new)}"
    )


def test_scan_is_deterministic(audit):
    assert audit.scan() == audit.scan()


@pytest.mark.parametrize(
    ("field", "default", "expected"),
    [
        (".exit_code", "0", "BLIND"),
        (".tool_response.is_error", "false", "BLIND"),
        (".tool_response.status", "ok", "BLIND"),
        (".tool_name", "unknown", "GUARDED"),
        (".tool_input.command", "", "INERT"),
        (".tool_response.stdout", "empty", "INERT"),
    ],
)
def test_default_classification(audit, field, default, expected):
    assert audit._classify(field, default) == expected


def test_only_harness_owned_roots_are_audited(audit):
    roots = {audit._root_of(r["field"]) for r in audit.scan()}
    assert roots <= audit.HARNESS_OWNED_ROOTS, (
        "auditor drifted into OS-owned state files; it must only cover fields "
        "the harness controls"
    )


# ── Canary: fields hooks depend on, against payloads the harness really sent ──


def test_phantom_field_dependencies_do_not_grow(audit):
    """The ratchet that would have caught moving .exit_code to .tool_response.exit_code."""
    missing, rows, _ = audit.canary(audit.CORPUS_DIR, audit.scan())
    assert rows > 0, "corpus carried no payloads — the canary would pass vacuously"
    phantom = {(r["file"], r["field"]) for r in missing}
    new = phantom - KNOWN_PHANTOM
    assert not new, (
        "hook(s) now depend on a payload field that no observed payload ever "
        f"carried: {sorted(new)}"
    )


def test_corpus_covers_every_result_state(audit):
    """Object, Error-with-code, Error-without-code all present."""
    seen, _ = audit.observed_fields(audit.CORPUS_DIR)
    assert REQUIRED_STATES <= seen["_states"], (
        f"corpus lost result state(s): {sorted(REQUIRED_STATES - seen['_states'])}"
    )


def test_corpus_covers_the_tools_the_os_depends_on(corpus_records):
    tools = {r["_corpus"]["tool"] for r in corpus_records}
    assert REQUIRED_TOOLS <= tools, f"corpus missing tool(s): {sorted(REQUIRED_TOOLS - tools)}"
    assert any(t.startswith("mcp__") for t in tools), "corpus has no MCP tool payload"


def test_corpus_is_harness_derived_not_hook_derived(audit):
    """A corpus built from the fields hooks read would validate by construction.

    The corpus must carry the keys the *harness emits*, most of which no hook
    has ever asked for.  If that surplus collapses, someone rebuilt the corpus
    from the hook side and the canary has stopped being able to fail.
    """
    seen, _ = audit.observed_fields(audit.CORPUS_DIR)
    corpus_keys = seen["toolUseResult"]
    hook_leaves = {
        r["field"].lstrip(".").split(".")[1].split("[")[0]
        for r in audit.scan()
        if r["field"].lstrip(".").startswith("tool_response.")
    }
    surplus = corpus_keys - hook_leaves
    assert len(surplus) > 40, (
        f"corpus carries only {len(surplus)} keys no hook reads — it looks "
        "derived from hook reads instead of from harness output"
    )


def test_corpus_carries_no_values(corpus_records, capture):
    """Keys and types are the payload contract; values are the privacy hazard."""
    offenders: list[str] = []

    def walk(v, path):
        if isinstance(v, dict):
            for k, sub in v.items():
                assert capture.SAFE_KEY_RE.match(k) or k == capture.REDACTED_KEY, (
                    f"unredacted key at {path}: {k!r}"
                )
                walk(sub, f"{path}.{k}")
        elif isinstance(v, list):
            for i, sub in enumerate(v):
                walk(sub, f"{path}[{i}]")
        elif isinstance(v, str):
            if v != capture.STR_TOKEN and not v.startswith("Error:"):
                offenders.append(f"{path}={v!r}")
        elif isinstance(v, bool):
            pass
        elif isinstance(v, (int, float)):
            assert v == 0, f"unredacted number at {path}: {v!r}"

    for rec in corpus_records:
        walk(rec["toolUseResult"], rec["_corpus"]["tool"])
    assert not offenders, f"corpus carries real string values: {offenders[:5]}"


def test_result_state_classifiers_agree(audit, capture):
    """Auditor and capture script must not drift apart on state classification."""
    cases = [
        {"stdout": "x"},
        [],
        "Error: Exit code 1\nboom",
        "Error: conflict-marker-guard blocked commit",
        "plain result",
    ]
    for c in cases:
        assert audit.result_state(c) == capture.result_state(c)

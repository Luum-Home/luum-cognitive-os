"""Behavioral contract test for the canonical-event-emitter reference skill.

ADR-064 P0 Task 9b acceptance gate.

Asserts:
1. The skill file exists at the canonical path.
2. Frontmatter is parseable with TIER: 0 and SCOPE: os-only.
3. The documented canonical event sequence is consistent with the fixture
   payloads in tests/fixtures/codex-live-session/ — i.e., the fixture set
   satisfies the contract events (session_start, user_prompt_submit,
   tool_use_start/end via Bash, session_end).
4. The skill is marked non-user-invocable (internal contract artifact).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_PATH = REPO_ROOT / "skills" / "__contracts__" / "canonical-event-emitter" / "SKILL.md"
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "codex-live-session"

# The canonical event sequence this contract mandates (event_type strings).
CANONICAL_EVENT_SEQUENCE = [
    "session_start",
    "user_prompt_submit",
    "tool_use_start",
    "tool_use_end",
    "session_end",
]

# Literal values the contract mandates.
CANONICAL_PROMPT = "canonical-event-emitter: emit reference sequence"
CANONICAL_COMMAND = "echo canonical-event-emitter-marker-2026"
CANONICAL_OUTPUT = "canonical-event-emitter-marker-2026"
CANONICAL_TOOL = "bash"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_frontmatter(text: str) -> dict:
    """Extract YAML frontmatter between --- delimiters and HTML-comment flags."""
    # HTML comment flags (<!-- SCOPE: x -->, <!-- TIER: N -->)
    html_flags: dict = {}
    for match in re.finditer(r"<!--\s*(\w+):\s*(.*?)\s*-->", text):
        html_flags[match.group(1).upper()] = match.group(2).strip()

    # YAML block between --- delimiters
    yaml_block_match = re.search(r"^---\n(.*?)\n---", text, re.DOTALL | re.MULTILINE)
    yaml_fields: dict = {}
    if yaml_block_match:
        yaml_text = yaml_block_match.group(1)
        for line in yaml_text.splitlines():
            if ":" in line:
                key, _, val = line.partition(":")
                yaml_fields[key.strip()] = val.strip().strip('"').strip("'")

    return {**yaml_fields, **html_flags}


def _read_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Test 1 — File existence
# ---------------------------------------------------------------------------

def test_skill_file_exists_at_canonical_path():
    """The contract skill MUST exist at the path ADR-064 specifies."""
    assert SKILL_PATH.exists(), (
        f"Canonical-event-emitter contract skill not found at {SKILL_PATH}. "
        "This file is required by ADR-064 P0 Task 9b."
    )
    assert SKILL_PATH.is_file(), f"{SKILL_PATH} exists but is not a regular file."


# ---------------------------------------------------------------------------
# Test 2 — Frontmatter correctness
# ---------------------------------------------------------------------------

def test_frontmatter_tier_zero():
    """TIER: 0 must be declared in the HTML-comment metadata."""
    text = SKILL_PATH.read_text(encoding="utf-8")
    fm = _parse_frontmatter(text)
    assert "TIER" in fm, (
        "SKILL.md missing <!-- TIER: N --> HTML-comment. "
        "Contract skills must declare TIER: 0."
    )
    assert fm["TIER"] == "0", (
        f"Expected TIER: 0 (highest priority), got TIER: {fm['TIER']!r}. "
        "Contract skills are always-available and must be TIER 0."
    )


def test_frontmatter_scope_os_only():
    """SCOPE: os-only must be declared — this skill is not user-invocable."""
    text = SKILL_PATH.read_text(encoding="utf-8")
    fm = _parse_frontmatter(text)
    assert "SCOPE" in fm, (
        "SKILL.md missing <!-- SCOPE: ... --> HTML-comment."
    )
    assert fm["SCOPE"] == "os-only", (
        f"Expected SCOPE: os-only, got {fm['SCOPE']!r}. "
        "Contract skills must be os-only to prevent catalog inclusion."
    )


def test_frontmatter_not_user_invocable():
    """user-invocable must be false — this is an internal contract artifact."""
    text = SKILL_PATH.read_text(encoding="utf-8")
    fm = _parse_frontmatter(text)
    raw = fm.get("user-invocable", "").lower()
    assert raw == "false", (
        f"Expected user-invocable: false, got {fm.get('user-invocable')!r}. "
        "Contract skills must never appear in the user-facing skill router."
    )


def test_frontmatter_name_matches_directory():
    """Skill name must match the directory name."""
    text = SKILL_PATH.read_text(encoding="utf-8")
    fm = _parse_frontmatter(text)
    assert fm.get("name") == "canonical-event-emitter", (
        f"Skill name {fm.get('name')!r} does not match directory 'canonical-event-emitter'."
    )


# ---------------------------------------------------------------------------
# Test 3 — Canonical event sequence documented in SKILL.md
# ---------------------------------------------------------------------------

def test_canonical_event_sequence_documented():
    """All five event types must appear in the SKILL.md body."""
    text = SKILL_PATH.read_text(encoding="utf-8")
    for event_type in CANONICAL_EVENT_SEQUENCE:
        assert event_type in text, (
            f"Event type '{event_type}' not found in canonical event sequence "
            f"documentation in {SKILL_PATH}."
        )


def test_canonical_prompt_documented():
    """The literal canonical prompt string must appear in SKILL.md."""
    text = SKILL_PATH.read_text(encoding="utf-8")
    assert CANONICAL_PROMPT in text, (
        f"Canonical prompt {CANONICAL_PROMPT!r} not documented in {SKILL_PATH}."
    )


def test_canonical_command_documented():
    """The literal bash command must appear in SKILL.md."""
    text = SKILL_PATH.read_text(encoding="utf-8")
    assert CANONICAL_COMMAND in text, (
        f"Canonical command {CANONICAL_COMMAND!r} not documented in {SKILL_PATH}."
    )


def test_canonical_output_marker_documented():
    """The literal output marker must appear in SKILL.md."""
    text = SKILL_PATH.read_text(encoding="utf-8")
    assert CANONICAL_OUTPUT in text, (
        f"Canonical output marker {CANONICAL_OUTPUT!r} not documented in {SKILL_PATH}."
    )


# ---------------------------------------------------------------------------
# Test 4 — Fixture alignment
#
# The fixtures in tests/fixtures/codex-live-session/ are the concrete payloads
# the integration test (test_harness_agnostic_skill_run.py) uses to drive the
# Codex adapter.  They must satisfy the contract's coverage of session_start,
# user_prompt_submit, and session_end (the three events the integration test
# covers).  tool_use_start/end are covered by exec_command_end.json which maps
# to a Bash execution.
# ---------------------------------------------------------------------------

def test_fixtures_directory_exists():
    """Fixture directory must exist — it is the concrete contract realization."""
    assert FIXTURES_DIR.exists(), (
        f"Fixtures directory not found at {FIXTURES_DIR}. "
        "These fixtures are the live contract realization for the Codex harness."
    )


def test_fixture_session_meta_satisfies_session_start():
    """session_meta.json must carry the fields needed for session_start event."""
    fixture = _read_fixture("session_meta.json")
    # The Codex adapter maps session_meta → SessionStart
    payload = fixture.get("payload", fixture)
    assert "id" in payload or "session_id" in payload or fixture.get("type") == "session_meta", (
        f"session_meta.json does not look like a session start payload: {list(payload.keys())}"
    )


def test_fixture_user_message_satisfies_user_prompt_submit():
    """user_message.json must carry a prompt for user_prompt_submit event.

    In the live Codex session the event type is 'response_item' with
    payload.role='user' and payload.content[].type='input_text'.  The Codex
    adapter normalises this into UserPromptSubmit.
    """
    fixture = _read_fixture("user_message.json")
    payload = fixture.get("payload", {})
    # Accept either the canonical 'user_message' type or the live Codex shape
    # (response_item with role=user carrying input_text content).
    has_user_role = payload.get("role") == "user"
    has_text_content = any(
        item.get("type") == "input_text"
        for item in payload.get("content", [])
        if isinstance(item, dict)
    )
    is_user_message = fixture.get("type") in ("user_message", "response_item")
    assert is_user_message and (has_user_role or "message" in payload), (
        f"user_message.json does not look like a user prompt payload. "
        f"type={fixture.get('type')!r}, payload keys: {list(payload.keys())}"
    )
    assert has_text_content or has_user_role, (
        "user_message.json payload must contain user-role content for UserPromptSubmit mapping."
    )


def test_fixture_task_complete_satisfies_session_end():
    """task_complete.json must carry the fields needed for session_end event."""
    fixture = _read_fixture("task_complete.json")
    assert fixture.get("type") == "task_complete" or "task_complete" in str(fixture), (
        f"task_complete.json does not look like a session end payload. "
        f"Top-level keys: {list(fixture.keys())}"
    )


def test_fixture_exec_command_satisfies_bash_tool_events():
    """exec_command_end.json must represent a Bash command (tool_use_start/end)."""
    fixture = _read_fixture("exec_command_end.json")
    payload = fixture.get("payload", {})
    # exec_command_end maps to Bash tool use; command list must be present
    assert "command" in payload, (
        f"exec_command_end.json missing 'command' field in payload. "
        f"Payload keys: {list(payload.keys())}"
    )
    # The command must be a Bash invocation (zsh/bash/sh is acceptable — it's
    # the shell wrapper that exec_command uses; the Codex adapter treats all
    # exec_command_end events as Bash tool events)
    cmd = payload["command"]
    assert isinstance(cmd, list) and len(cmd) > 0, (
        f"'command' field must be a non-empty list, got {cmd!r}"
    )


# ---------------------------------------------------------------------------
# Test 5 — Allowed-diff fields documented
# ---------------------------------------------------------------------------

def test_allowed_diff_fields_documented():
    """The SKILL.md must document the allowed-diff fields set."""
    text = SKILL_PATH.read_text(encoding="utf-8")
    # Check a representative sample of the allowed-diff fields are documented
    required_in_doc = ["harness", "session_id", "started_at", "ended_at", "duration_ms"]
    missing = [f for f in required_in_doc if f not in text]
    assert not missing, (
        f"Allowed-diff fields not documented in {SKILL_PATH}: {missing}. "
        "The contract must document which fields are excluded from byte-identity."
    )


# ---------------------------------------------------------------------------
# Test 6 — __contracts__ namespace is structurally correct
# ---------------------------------------------------------------------------

def test_contracts_namespace_uses_dunder_prefix():
    """The __contracts__ directory uses __ prefix — structural non-invocability signal."""
    contracts_dir = REPO_ROOT / "skills" / "__contracts__"
    assert contracts_dir.exists(), (
        f"__contracts__ directory not found at {contracts_dir}."
    )
    assert contracts_dir.name.startswith("__") and contracts_dir.name.endswith("__"), (
        f"Contract skill namespace must use __dunder__ convention, got: {contracts_dir.name!r}"
    )

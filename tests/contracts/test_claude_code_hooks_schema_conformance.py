"""Conformance of this repo's hooks against the PUBLISHED Claude Code schema.

This is deliberately not a test of the hooks against themselves. The assertions
read ``manifests/claude-code-hooks-schema.yaml`` — a transcription of the
upstream Claude Code hooks reference with source URLs and verification date
recorded in the file — and check that what our hooks emit is something Claude
Code would actually consume.

Sibling of ``test_codex_hooks_schema_conformance.py``, with one difference worth
naming: the Codex manifest describes a projection this repo GENERATES, so its
conformance test can re-run a driver and diff the output. Claude Code is the
harness this repo RUNS ON, and the hooks are hand-written. There is no driver to
re-run, so conformance here is a census of the hook sources plus a live
execution of the one hook whose payload matters most.

What it catches:

* A hook printing ``additionalContext`` at the ROOT of its JSON object. Claude
  Code reads the field only from inside ``hookSpecificOutput``. The root form is
  valid JSON, so the host parses it, finds no recognized field, and drops it —
  silently, with no fallback to plain text (a payload starting with ``{`` that
  parses is never re-read as prose). This failure mode produces no error
  anywhere: the hook exits 0, the JSON is well-formed, and the context vanishes.
* A hook whose ``# Async:`` header comment contradicts its ``async`` setting in
  ``.claude/settings.json``. The file disagreeing with its own registration is
  how a fire-and-forget hook goes on advertising that it blocks.
* ``async: true`` on a context-only event whose insertion point precedes the
  first prompt.

Run:
    python3 -m pytest tests/contracts/test_claude_code_hooks_schema_conformance.py -q
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = REPO_ROOT / "manifests" / "claude-code-hooks-schema.yaml"
SETTINGS = REPO_ROOT / ".claude" / "settings.json"
HOOKS_DIR = REPO_ROOT / "hooks"
INJECTOR = HOOKS_DIR / "subagent-context-injector.sh"

# ── Known debt, measured 2026-08-15 ──────────────────────────────────────────
# These hooks emit `{"additionalContext": ...}` at the root. Both are registered
# on UserPromptSubmit, both currently deliver nothing.
#
# This is a BASELINE, and per the project's gates-sin-trampa rule a baseline
# above reality is itself a bug: it must equal today's violation set EXACTLY,
# never merely contain it. A new flat-form hook therefore fails on arrival
# rather than landing in unused slack. When the runbook patch lands
# (docs/05-Methodology/runbooks/hooks-additional-context-shape-2026-08-15.md),
# the census returns an empty set, this test fails on the leftover entries, and
# emptying the list is the fix — not moving it.
KNOWN_ROOT_LEVEL_VIOLATIONS = {
    "hooks/cross-session-peer-context.sh",
    "hooks/agent-message-inbox-context.sh",
}

# `.claude/settings.json` registers these with `async: true` while their own
# `# Async:` header claims the opposite. Same exact-match discipline as above:
# the patch in the runbook empties this list, it never grows to absorb a
# regression.
KNOWN_ASYNC_HEADER_MISMATCHES = {
    "subagent-context-injector.sh",   # header says false, registered true
    "skill-md-routing-validator.sh",  # header says true, registered false
}

# `hookSpecificOutput` requires `hookEventName` ("It requires a hookEventName
# field set to the event name" — hooks.md, "JSON output"). This hook nests
# correctly but omits the event name.
KNOWN_MISSING_HOOK_EVENT_NAME = {
    "hooks/eas-validation-gate.sh",
}

# The injector emits the right shape on the right event and is still registered
# `async: true`, which is the single reason its context never reaches a
# sub-agent. Baselined rather than silently tolerated: this is THE defect the
# runbook patch exists to fix.
KNOWN_ASYNC_ON_CONTEXT_EMITTER = {
    "subagent-context-injector.sh on SubagentStart",
}

# SubagentStart is context-only, so `permissionDecision: "allow"` is inert.
# Harmless at runtime; kept visible because it records an author who believed
# the event could gate.
KNOWN_INERT_DECISION_FIELDS = {"permissionDecision"}

# Object literals whose FIRST key is additionalContext — i.e. a fresh root
# object built around the field rather than a member of hookSpecificOutput.
# Matches `json.dumps({"additionalContext": ...})` and `{'additionalContext':`.
#
# The brace alone is not enough to tell root from nested: a correctly nested
# payload written across lines opens with `"hookSpecificOutput": {` and puts
# `"additionalContext":` on the next line, so the naive pattern matches it too.
# _is_nested() re-reads the text just before the brace to separate the two.
_ROOT_OBJECT_RE = re.compile(r"""[{]\s*["']additionalContext["']\s*:""")


def _is_nested(text: str, brace_pos: int) -> bool:
    """True when the matched `{` is the value of a hookSpecificOutput key."""
    return "hookSpecificOutput" in text[max(0, brace_pos - 60) : brace_pos]


@pytest.fixture(scope="module")
def schema() -> dict:
    assert MANIFEST.exists(), f"missing published-schema manifest: {MANIFEST}"
    return yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def registrations() -> dict[str, list[dict]]:
    """Map hook basename -> list of {event, async, matcher} registrations."""
    data = json.loads(SETTINGS.read_text(encoding="utf-8"))
    out: dict[str, list[dict]] = {}
    for event, matchers in data.get("hooks", {}).items():
        for matcher in matchers:
            for handler in matcher.get("hooks", []):
                command = handler.get("command", "")
                for name in re.findall(r"hooks/([A-Za-z0-9_.-]+\.sh)", command):
                    out.setdefault(name, []).append(
                        {
                            "event": event,
                            "async": bool(handler.get("async", False)),
                            "matcher": matcher.get("matcher", ""),
                        }
                    )
    return out


def _hook_sources() -> list[Path]:
    return sorted(p for p in HOOKS_DIR.rglob("*") if p.suffix in {".sh", ".py"})


# ── The rule the manifest exists to state ────────────────────────────────────


def test_manifest_declares_nested_placement_only(schema):
    """The manifest must state the single placement, not hedge between two."""
    ac = schema["additional_context"]
    assert ac["placement"] == "hookSpecificOutput.additionalContext"
    assert ac["root_level_allowed"] is False, (
        "If the manifest ever declares the root form allowed, the test helper in "
        "tests/hooks/test_subagent_context_injector.py must change with it — and "
        "that needs a citation, not a preference."
    )
    assert ac["requires_sibling"] == "hookEventName"


def test_manifest_cites_sources_with_verification_dates(schema):
    """A contract claim without a URL and a date is an opinion."""
    sourced = [s for s in schema["sources"] if "url" in s]
    assert sourced, "manifest declares no sourced URLs"
    for src in sourced:
        assert src.get("verified"), f"source lacks a verified date: {src['url']}"
        assert str(src["verified"]).startswith("20"), src["verified"]


# ── Census: nobody may emit the root-level form ──────────────────────────────


def test_no_hook_emits_root_level_additional_context():
    """Root-level additionalContext is dropped by the host without a word."""
    violations = set()
    for path in _hook_sources():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in _ROOT_OBJECT_RE.finditer(text):
            if not _is_nested(text, match.start()):
                violations.add(str(path.relative_to(REPO_ROOT)))
                break

    unexpected = violations - KNOWN_ROOT_LEVEL_VIOLATIONS
    assert not unexpected, (
        "New hook(s) emit additionalContext at the ROOT of their JSON object: "
        f"{sorted(unexpected)}. Claude Code reads the field only from inside "
        "hookSpecificOutput; the root form parses as valid JSON and is then "
        "silently discarded. Move it to "
        '{"hookSpecificOutput": {"hookEventName": "<Event>", '
        '"additionalContext": "..."}} — see '
        "manifests/claude-code-hooks-schema.yaml."
    )

    stale = KNOWN_ROOT_LEVEL_VIOLATIONS - violations
    assert not stale, (
        f"Fixed hook(s) still listed as known violations: {sorted(stale)}. "
        "Remove them from KNOWN_ROOT_LEVEL_VIOLATIONS. A baseline above reality "
        "is slack a future regression lands in for free."
    )


# ── The header must not contradict the registration ──────────────────────────


def test_hook_async_header_matches_registration(registrations):
    """A hook claiming `# Async: false` while registered async:true is a lie.

    Not cosmetic: it is exactly how the injector kept advertising that it
    "completes before subagent starts" for as long as nobody diffed the file
    against settings.json.
    """
    header_re = re.compile(r"^#\s*Async:\s*(\S+)", re.MULTILINE | re.IGNORECASE)
    mismatches = []
    for path in _hook_sources():
        if path.suffix != ".sh":
            continue
        match = header_re.search(path.read_text(encoding="utf-8", errors="ignore"))
        if not match:
            continue
        declared = match.group(1).lower().strip("().,")
        if declared not in {"true", "false"}:
            continue
        for reg in registrations.get(path.name, []):
            if (declared == "true") != reg["async"]:
                mismatches.append((path.name, declared, reg["event"], reg["async"]))

    offending = {name for name, *_ in mismatches}

    unexpected = offending - KNOWN_ASYNC_HEADER_MISMATCHES
    assert not unexpected, (
        "New hook header(s) contradict their registration in "
        f".claude/settings.json: {sorted(unexpected)}. Full set:\n"
        + "\n".join(
            f"  {n} header says Async: {d} but registered on {e} with async={a}"
            for n, d, e, a in mismatches
        )
    )

    stale = KNOWN_ASYNC_HEADER_MISMATCHES - offending
    assert not stale, (
        f"Hook header(s) no longer mismatched but still baselined: {sorted(stale)}. "
        "Remove them from KNOWN_ASYNC_HEADER_MISMATCHES."
    )


def test_hook_specific_output_always_carries_event_name(schema):
    """`hookSpecificOutput` without `hookEventName` is an incomplete object.

    Found by a false positive of the root-level detector, which is the only
    reason it is written down: the payload nests correctly and still omits the
    field the host requires to route it.
    """
    pattern = re.compile(r"""["']hookSpecificOutput["']\s*:\s*[{]""")
    offenders = set()
    for path in _hook_sources():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in pattern.finditer(text):
            window = text[match.end() : match.end() + 400]
            if "hookEventName" not in window:
                offenders.add(str(path.relative_to(REPO_ROOT)))
                break

    unexpected = offenders - KNOWN_MISSING_HOOK_EVENT_NAME
    assert not unexpected, (
        f"hookSpecificOutput without hookEventName in {sorted(unexpected)}. The "
        'host requires it: {"hookSpecificOutput": {"hookEventName": "<Event>", '
        '...}} — see manifests/claude-code-hooks-schema.yaml.'
    )

    stale = KNOWN_MISSING_HOOK_EVENT_NAME - offenders
    assert not stale, (
        f"Fixed hook(s) still baselined as missing hookEventName: {sorted(stale)}."
    )


def test_async_not_used_on_prompt_preceding_context_events(schema, registrations):
    """async on SubagentStart/SessionStart cannot make its own insertion point.

    The manifest records this as CONTRA-INDICATED by inference, not as a quoted
    rule — the upstream docs name decision/permissionDecision/continue as inert
    under async and say nothing about additionalContext. What they do say is
    that async output arrives "on the next conversation turn" while these
    events insert "before the first prompt". Those cannot both hold.
    """
    contra = {
        entry["event"]
        for entry in schema["handler_fields"]["async"]["contraindicated_for"]
    }

    # Scope matters. `async` is the RIGHT setting for a hook that only has side
    # effects — the SessionStart daemon launchers, drift detectors and weekly
    # audits in this repo are all correctly async, and flagging them would be a
    # gate firing on files it has nothing to say about. The conflict is only
    # between "runs in the background" and "must be in the context window
    # before the first prompt", so it exists only for hooks that emit context.
    emitters = {
        path.name
        for path in _hook_sources()
        if "additionalContext" in path.read_text(encoding="utf-8", errors="ignore")
    }

    offenders = [
        f"{name} on {reg['event']}"
        for name, regs in registrations.items()
        for reg in regs
        if reg["async"] and reg["event"] in contra and name in emitters
    ]

    unexpected = set(offenders) - KNOWN_ASYNC_ON_CONTEXT_EMITTER
    assert not unexpected, (
        "Hooks registered async:true on an event whose additionalContext must "
        f"land before the first prompt: {sorted(unexpected)}. Remove `async` so "
        "the hook completes before the context window is built, or accept that "
        "the context never arrives. See "
        "docs/06-Daily/reports/contrato-salida-hooks-2026-08-15.md."
    )

    stale = KNOWN_ASYNC_ON_CONTEXT_EMITTER - set(offenders)
    assert not stale, (
        f"Fixed registration(s) still baselined: {sorted(stale)}. "
        "Remove them from KNOWN_ASYNC_ON_CONTEXT_EMITTER."
    )


# ── Live payload of the injector ─────────────────────────────────────────────


def _run_injector() -> dict:
    result = subprocess.run(
        ["bash", str(INJECTOR)],
        input=json.dumps(
            {
                "session_id": "conformance",
                "cwd": str(REPO_ROOT),
                "hook_event_name": "SubagentStart",
                "agent_id": "agent-conformance",
                "agent_type": "general-purpose",
                "prompt": "conformance probe",
            }
        ),
        capture_output=True,
        text=True,
        timeout=30,
        env={
            **__import__("os").environ,
            "CLAUDE_PROJECT_DIR": str(REPO_ROOT),
            "COS_SESSION_DIR": "/tmp/cos-conformance-session",
        },
    )
    assert result.returncode == 0, f"injector exited {result.returncode}: {result.stderr}"
    return json.loads(result.stdout)


def test_injector_payload_matches_schema(schema):
    """The injector's live output must be shaped the way the host reads it."""
    payload = _run_injector()
    assert "additionalContext" not in payload, (
        "injector emits additionalContext at the root — the host ignores it there"
    )
    hso = payload.get("hookSpecificOutput")
    assert isinstance(hso, dict), f"no hookSpecificOutput; got {sorted(payload)}"
    assert hso.get("hookEventName") == "SubagentStart"
    assert hso.get("additionalContext"), "additionalContext is empty"


def test_injector_payload_respects_the_10k_cap(schema):
    """Over the cap the host writes the text to a file and passes a preview."""
    cap = schema["additional_context"]["max_chars"]
    context = _run_injector()["hookSpecificOutput"]["additionalContext"]
    assert len(context) <= cap, (
        f"additionalContext is {len(context)} chars, over the {cap} cap — the "
        "host would replace the rules with a file path and a preview"
    )


def test_injector_emits_only_fields_the_event_honors(schema):
    """SubagentStart is context-only; decision fields there are inert.

    Advisory in the manifest, asserted here because an inert permissionDecision
    is a live signal that the author believed the event could gate.
    """
    hso = _run_injector()["hookSpecificOutput"]
    ignored = set(schema["events"]["SubagentStart"]["output_fields_ignored"])
    present = (ignored & set(hso)) - KNOWN_INERT_DECISION_FIELDS
    assert not present, (
        f"injector sets {sorted(present)} on SubagentStart, which the host "
        "ignores for this event (context only, no blocking or decision "
        "control). Harmless at runtime, misleading to the next reader."
    )

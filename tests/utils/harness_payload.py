"""The payload the harness really sends, so a hook test cannot invent one.

A hook test that writes ``{"tool_name": "Bash", "tool_input": {"command": ...}}``
is not testing the hook against the harness; it is testing the hook against the
two fields the test author remembered.  The harness sends six or seven, and at
least one of them changes verdicts: with a fabricated two-field payload,
``bash-hot-path-dispatcher`` blocks a plain ``grep``, and adding nothing but
``session_id`` makes the same command pass (see the field ablation in
``docs/06-Daily/reports/payloads-que-el-arnes-manda-2026-08-20.md``).

Use it like this::

    from tests.utils.harness_payload import payload

    p = payload("PreToolUse", tool_name="Bash",
                tool_input={"command": "grep -rn needle src/"})

``p`` carries every field the harness puts on that event, with values of the
right shape, and **refuses** a field the harness does not send::

    payload("PreToolUse", tool_name="Bash", tool_input={}, skill_name="x")
    # UnknownPayloadField: 'skill_name' is not a field the harness sends on
    # PreToolUse.  Fields sent: cwd, hook_event_name, session_id, tool_input,
    # tool_name, transcript_path

That refusal is the point: three tests in this repo fed hooks a ``skill_name``,
a ``tool_count`` and a ``main_worktree`` that no harness has ever sent.

Where the shape comes from
--------------------------
``tests/fixtures/hook-payload-envelope/envelope.json`` — captured from this
machine's harness transcripts by ``scripts/audit_hook_payload_fidelity.py
--capture``, **not** transcribed from documentation.  The fixture holds key
names and value kinds only; every operator value (paths, usernames, project
names, command text, prompts) is dropped at capture time and never reaches the
repo.  See the fixture README for the privacy argument and the two guards that
enforce it.

When a test needs real *content* — an actual command string the operator ran,
not a synthetic one — ``live_payloads()`` regenerates payloads with real values
from the local transcript at test time.  Those are never written to disk, and
the function returns an empty list on a machine with no transcripts, so a test
using it must skip rather than fail.

Genuinely synthetic payloads are still allowed
----------------------------------------------
Testing what a hook does with a truncated, malformed or field-less payload is a
real test, and it cannot use a faithful payload by definition.  Use
``malformed()`` / ``truncated()`` / ``without()``, or mark the literal with a
``# payload-synthetic: <reason>`` comment; the fabrication gate honours both.
"""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ENVELOPE_PATH = REPO_ROOT / "tests" / "fixtures" / "hook-payload-envelope" / "envelope.json"

__all__ = [
    "payload",
    "raw",
    "live_payloads",
    "malformed",
    "truncated",
    "without",
    "fields_sent",
    "UnknownPayloadField",
]


class UnknownPayloadField(KeyError):
    """A test asked for a payload field the harness does not send."""


class UnknownEvent(KeyError):
    """A test asked for an event the envelope has never observed."""


_ENVELOPE: dict | None = None


def _envelope() -> dict:
    global _ENVELOPE
    if _ENVELOPE is None:
        _ENVELOPE = json.loads(ENVELOPE_PATH.read_text())
    return _ENVELOPE


def fields_sent(event: str) -> set[str]:
    """The exact top-level field set the harness sends on ``event``."""
    events = _envelope()["events"]
    if event not in events:
        raise UnknownEvent(
            f"{event!r} is not in the payload envelope. Observed events: "
            f"{', '.join(sorted(events))}. Re-capture with "
            f"scripts/audit_hook_payload_fidelity.py --capture after a session "
            f"that exercised it."
        )
    return set(events[event])


# Value shapes.  Not "a plausible value" — the shape the harness uses, so a hook
# that parses the value (a UUID, an absolute .jsonl path) sees what it expects.
def _default_value(field: str, event: str, cwd: str) -> object:
    if field == "session_id":
        return str(uuid.uuid4())
    if field == "hook_event_name":
        return event
    if field == "cwd":
        return cwd
    if field == "transcript_path":
        return f"{cwd}/.cognitive-os/test-transcripts/{uuid.uuid4()}.jsonl"
    if field == "permission_mode":
        return "default"
    if field == "prompt":
        return ""
    if field in ("tool_input", "tool_response"):
        return {}
    if field == "stop_hook_active":
        return False
    return ""


def payload(event: str, *, cwd: str | Path | None = None, **fields) -> dict:
    """A payload carrying exactly the fields the harness sends on ``event``.

    Every field the harness sends is present; any field it does not send is a
    hard error.  ``cwd`` defaults to the repo root because that is what the
    harness sends when the session is opened here.
    """
    sent = fields_sent(event)
    unknown = set(fields) - sent
    if unknown:
        raise UnknownPayloadField(
            f"{', '.join(sorted(unknown))} "
            f"{'is not a field' if len(unknown) == 1 else 'are not fields'} "
            f"the harness sends on {event}. Fields sent: {', '.join(sorted(sent))}. "
            f"If the hook genuinely needs it, capture a session that produces it "
            f"(scripts/audit_hook_payload_fidelity.py --capture); if the test "
            f"needs a payload the harness would never send, use "
            f"tests.utils.harness_payload.without()/malformed()."
        )
    cwd_s = str(cwd or REPO_ROOT)
    out = {f: _default_value(f, event, cwd_s) for f in sorted(sent)}
    out.update(fields)
    return out


def raw(event: str, **kwargs) -> str:
    """``payload()`` serialised the way the harness writes it to a hook's stdin."""
    return json.dumps(payload(event, **kwargs))


def without(event: str, *drop: str, **kwargs) -> dict:
    """A faithful payload minus named fields — for testing degradation.

    Deliberately synthetic: use it to prove a hook survives a field the harness
    stopped sending, and say which field in the test name.
    """
    p = payload(event, **kwargs)
    for d in drop:
        p.pop(d, None)
    return p


def malformed(kind: str = "not-json") -> str:
    """Stdin a hook must survive but the harness would never send."""
    if kind == "not-json":
        return "this is not json at all"
    if kind == "empty":
        return ""
    if kind == "truncated":
        return '{"tool_name": "Bash", "tool_in'
    if kind == "array":
        return "[]"
    if kind == "null":
        return "null"
    raise ValueError(f"unknown malformed kind: {kind!r}")


def truncated() -> str:
    return malformed("truncated")


# ─────────────────────────────────────────────────────────────────────────────
# Real content, generated at test time, never written to the repo
# ─────────────────────────────────────────────────────────────────────────────
def _transcript_dir() -> Path | None:
    base = Path.home() / ".claude" / "projects"
    if not base.is_dir():
        return None
    cand = base / re.sub(r"[^A-Za-z0-9]+", "-", str(REPO_ROOT))
    return cand if cand.is_dir() else None


def live_payloads(event: str = "PreToolUse", tool: str | None = None,
                  limit: int = 25) -> list[dict]:
    """Real payloads with real values, rebuilt from this machine's transcripts.

    Returns ``[]`` when no transcript is available, so callers must
    ``pytest.skip`` rather than fail: these payloads carry operator data and by
    design never become a versioned fixture.
    """
    d = _transcript_dir()
    if d is None or event not in ("PreToolUse", "PostToolUse"):
        return []
    out: list[dict] = []
    files = sorted(d.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)[:3]
    for f in files:
        pending: dict[str, dict] = {}
        with f.open(errors="replace") as fh:
            for line in fh:
                if len(out) >= limit:
                    return out
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if rec.get("type") == "assistant":
                    for block in (rec.get("message") or {}).get("content") or []:
                        if not isinstance(block, dict) or block.get("type") != "tool_use":
                            continue
                        if tool and block.get("name") != tool:
                            continue
                        p = {
                            "session_id": rec.get("sessionId", ""),
                            "transcript_path": str(f),
                            "cwd": rec.get("cwd", ""),
                            "hook_event_name": "PreToolUse",
                            "tool_name": block.get("name", ""),
                            "tool_input": block.get("input") or {},
                        }
                        if rec.get("permissionMode"):
                            p["permission_mode"] = rec["permissionMode"]
                        if event == "PreToolUse":
                            out.append(p)
                        pending[block.get("id")] = p
                elif rec.get("type") == "user" and event == "PostToolUse":
                    tur = rec.get("toolUseResult")
                    if tur is None:
                        continue
                    for block in (rec.get("message") or {}).get("content") or []:
                        if isinstance(block, dict) and block.get("type") == "tool_result":
                            src = pending.get(block.get("tool_use_id"))
                            if not src:
                                continue
                            if tool and src["tool_name"] != tool:
                                continue
                            p = dict(src)
                            p["hook_event_name"] = "PostToolUse"
                            p["tool_response"] = tur
                            out.append(p)
    return out

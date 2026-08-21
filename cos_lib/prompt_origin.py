# SCOPE: both
"""Who authored the text that arrived on ``UserPromptSubmit``.

The harness delivers several very different things through the same event. A
person typing a request, a finished background agent reporting back, the
compaction preamble, the echo of a slash command -- all of them arrive as
``.prompt`` on ``UserPromptSubmit``, and a hook that treats them alike spends
the operator's context budget on text no operator wrote.

**There is no origin field to read.** The harness sends exactly six top-level
fields on this event -- ``cwd``, ``hook_event_name``, ``permission_mode``,
``prompt``, ``session_id``, ``transcript_path`` -- and none of them says where
the text came from::

    python3 -c "import json;print(sorted(json.load(open(
      'tests/fixtures/hook-payload-envelope/envelope.json'
      ))['events']['UserPromptSubmit']))"

So the origin has to come from the shape of ``.prompt`` itself. Every marker
below was taken from a real transcript on this machine, never from memory::

    python3 scripts/measure_rule_router_precision.py --composition

Non-human classes are not a guess about what "looks automated": each one is
cross-checked against live hook telemetry by that script, which reports how
many payloads of each class actually reached the hook. A class the hook never
saw cannot be costing context, and must not be counted as if it were.

Anything that does not match a known marker is ``typed``. That default is
deliberate: a false ``typed`` wastes a little context, a false non-human
silently drops a real request.
"""

from __future__ import annotations

__all__ = [
    "ORIGIN_TYPED",
    "ORIGIN_TASK_NOTIFICATION",
    "ORIGIN_COMPACTION",
    "ORIGIN_CROSS_SESSION",
    "ORIGIN_HARNESS_ECHO",
    "MACHINE_ORIGINS",
    "MIN_PROMPT_CHARS",
    "classify_origin",
    "is_human_authored",
    "skip_reason",
]

ORIGIN_TYPED = "typed"
ORIGIN_TASK_NOTIFICATION = "task-notification"
ORIGIN_COMPACTION = "compaction"
ORIGIN_CROSS_SESSION = "cross-session"
ORIGIN_HARNESS_ECHO = "harness-echo"

#: Origins no person typed. Ordered by how much of the real traffic they carry.
MACHINE_ORIGINS = frozenset({
    ORIGIN_TASK_NOTIFICATION,
    ORIGIN_COMPACTION,
    ORIGIN_CROSS_SESSION,
    ORIGIN_HARNESS_ECHO,
})

#: The hook drops anything shorter than this before it ever reaches Python.
#: Mirrors the ``-lt 10`` guard in hooks/rule-router-prompt-suggest.sh; the two
#: are pinned together by tests/unit/test_rule_router_prompt_suggest_hook.py.
MIN_PROMPT_CHARS = 10

# The background-agent completion report the harness injects as a user turn.
_TASK_NOTIFICATION_OPEN = "<task-notification>"

# The compaction preamble. Full observed opener; the prefix is kept long enough
# that a person writing *about* compaction does not trip it.
_COMPACTION_OPEN = "This session is being continued from a previous conversation"

# hcom / cross-session delivery: another agent's text, wrapped and handed over.
_CROSS_SESSION_OPEN = "Another Claude session sent a message:"

# Slash-command plumbing the harness echoes back into the turn. Observed as
# message openers in this repo's transcripts; a bare list, not a `startswith("<")`
# catch-all, so an operator who opens with a tag is still read as typed.
_HARNESS_ECHO_OPENERS = (
    "<local-command-caveat>",
    "<local-command-stdout>",
    "<local-command-stderr>",
    "<command-name>",
    "<command-message>",
)


def classify_origin(text: str) -> str:
    """Return one of the ``ORIGIN_*`` constants for a ``UserPromptSubmit`` prompt.

    Unknown shapes classify as :data:`ORIGIN_TYPED` on purpose -- see module
    docstring for why the default leans toward "a person wrote this".
    """
    if not isinstance(text, str):
        return ORIGIN_TYPED
    head = text.lstrip()
    if not head:
        return ORIGIN_TYPED
    if head.startswith(_TASK_NOTIFICATION_OPEN):
        return ORIGIN_TASK_NOTIFICATION
    if head.startswith(_COMPACTION_OPEN):
        return ORIGIN_COMPACTION
    if head.startswith(_CROSS_SESSION_OPEN):
        return ORIGIN_CROSS_SESSION
    if head.startswith(_HARNESS_ECHO_OPENERS):
        return ORIGIN_HARNESS_ECHO
    return ORIGIN_TYPED


def is_human_authored(text: str) -> bool:
    """True when the prompt has no marker of machine authorship."""
    return classify_origin(text) not in MACHINE_ORIGINS


def skip_reason(text: str) -> str:
    """Why a context-spending hook should skip this prompt, or ``""`` to proceed.

    The returned string is what lands in telemetry, so it names the class rather
    than saying "skipped": three months from now the question is not whether
    something was skipped but *what*, and whether the suppression reached
    further than intended.
    """
    origin = classify_origin(text)
    if origin in MACHINE_ORIGINS:
        return f"not-human-authored:{origin}"
    return ""

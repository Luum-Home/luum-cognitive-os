"""hooks/rule-router-prompt-suggest.sh: the origin suppression, executed.

Every test here runs the real hook as a subprocess against a throwaway project
directory and reads what it wrote. Nothing asserts that a file exists.

The payloads are built with tests.utils.harness_payload, so the hook sees the
six fields the harness really sends on UserPromptSubmit rather than the two a
test author would have remembered.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

from cos_lib.prompt_origin import (
    MIN_PROMPT_CHARS,
    ORIGIN_TASK_NOTIFICATION,
    ORIGIN_TYPED,
    classify_origin,
    is_human_authored,
    skip_reason,
)
from tests.utils.harness_payload import payload as harness_payload

pytestmark = pytest.mark.unit

PROJECT_ROOT = Path(__file__).parent.parent.parent
HOOK_PATH = PROJECT_ROOT / "hooks" / "rule-router-prompt-suggest.sh"

# A real task-notification opener. Shape taken from this repo's transcripts.
TASK_NOTIFICATION = (
    "<task-notification>\n"
    "<task-id>a416cd5404cf345bf</task-id>\n"
    "<status>completed</status>\n"
    "<summary>Agent completed</summary>\n"
    "<result>I checked error-learning.jsonl for repeats and rewrote the "
    "release-publishing flow with an annotated tag.</result>\n"
    "</task-notification>"
)
# A typed prompt the router demonstrably matches -- the positive control. If the
# suppression ever breaks the router outright, this is the test that says so.
TYPED_CONTROL = "check error-learning.jsonl for repeats before retrying"


def _sandbox(tmp_path: Path) -> Path:
    (tmp_path / ".cognitive-os" / "metrics").mkdir(parents=True, exist_ok=True)
    for name in ("cos_lib", "rules", "manifests"):
        src = PROJECT_ROOT / name
        if src.exists():
            (tmp_path / name).symlink_to(src)
    return tmp_path


def _run(sandbox: Path, prompt: str, env_overrides: dict | None = None):
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(sandbox)
    env["PROJECT_DIR"] = str(sandbox)
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    env.pop("COS_RULE_ROUTER_ALL_PAYLOADS", None)
    env.update(env_overrides or {})
    stdin = json.dumps(harness_payload("UserPromptSubmit", cwd=str(sandbox),
                                       prompt=prompt))
    return subprocess.run(["bash", str(HOOK_PATH)], input=stdin,
                          capture_output=True, text=True, env=env, timeout=60)


def _rows(sandbox: Path) -> list[dict]:
    log = sandbox / ".cognitive-os" / "metrics" / "rule-suggestion.jsonl"
    if not log.is_file():
        return []
    return [json.loads(ln) for ln in log.read_text().splitlines() if ln.strip()]


class TestOriginClassifier:
    def test_task_notification_is_machine_authored(self):
        assert classify_origin(TASK_NOTIFICATION) == ORIGIN_TASK_NOTIFICATION
        assert is_human_authored(TASK_NOTIFICATION) is False
        assert skip_reason(TASK_NOTIFICATION) == (
            "not-human-authored:task-notification")

    def test_typed_prompt_passes_through(self):
        assert classify_origin(TYPED_CONTROL) == ORIGIN_TYPED
        assert is_human_authored(TYPED_CONTROL) is True
        assert skip_reason(TYPED_CONTROL) == ""

    def test_unknown_shapes_default_to_typed(self):
        """A false 'typed' costs context; a false 'machine' drops a request."""
        for odd in ("<div>hola</div>", "```python\nprint(1)\n```", "?", "\n\n"):
            assert is_human_authored(odd) is True, odd

    def test_prose_about_compaction_is_not_compaction(self):
        assert is_human_authored(
            "This session is being noisy, can we talk about compaction?") is True


class TestHookSuppression:
    def test_task_notification_emits_nothing(self, tmp_path):
        r = _run(_sandbox(tmp_path), TASK_NOTIFICATION)
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == "", (
            f"machine-authored payload still spent context: {r.stdout!r}")

    def test_skipped_payload_is_still_recorded_with_a_reason(self, tmp_path):
        sandbox = _sandbox(tmp_path)
        _run(sandbox, TASK_NOTIFICATION)
        rows = _rows(sandbox)
        assert len(rows) == 1, "a skipped payload must not vanish from telemetry"
        assert rows[0]["evaluated"] is False
        assert rows[0]["skipped_reason"] == "not-human-authored:task-notification"
        assert rows[0]["prompt_origin"] == ORIGIN_TASK_NOTIFICATION

    def test_skipped_row_keeps_every_field_older_readers_use(self, tmp_path):
        """scripts/audit_rule_load_channels.py reads these unconditionally."""
        sandbox = _sandbox(tmp_path)
        _run(sandbox, TASK_NOTIFICATION)
        row = _rows(sandbox)[0]
        for field in ("ts", "session_id", "prompt_hash", "match_count",
                      "top_match", "top_confidence", "threshold_met", "matches"):
            assert field in row, f"skipped row dropped {field}"
        assert row["threshold_met"] is False
        assert row["matches"] == []

    def test_killswitch_restores_evaluation_of_every_payload(self, tmp_path):
        sandbox = _sandbox(tmp_path)
        r = _run(sandbox, TASK_NOTIFICATION,
                 {"COS_RULE_ROUTER_ALL_PAYLOADS": "1"})
        assert r.returncode == 0, r.stderr
        row = _rows(sandbox)[0]
        assert row["evaluated"] is True
        assert row["skipped_reason"] == ""

    def test_the_two_branches_differ(self, tmp_path):
        """The counterfactual, inline: same payload, opposite outcomes.

        If both branches produced the same stdout the suppression would be
        untested, whatever the other assertions say.
        """
        on = _run(_sandbox(tmp_path / "on"), TASK_NOTIFICATION)
        off = _run(_sandbox(tmp_path / "off"), TASK_NOTIFICATION,
                   {"COS_RULE_ROUTER_ALL_PAYLOADS": "1"})
        assert on.stdout.strip() == ""
        assert "additionalContext" in off.stdout, (
            "with the suppression reverted this payload must emit -- otherwise "
            "the probe does not discriminate and proves nothing")


class TestPositiveControl:
    def test_typed_prompt_still_emits_after_the_change(self, tmp_path):
        sandbox = _sandbox(tmp_path)
        r = _run(sandbox, TYPED_CONTROL)
        assert r.returncode == 0, r.stderr
        out = json.loads(r.stdout.strip())
        ctx = out["hookSpecificOutput"]["additionalContext"]
        assert "error-learning" in ctx, ctx
        row = _rows(sandbox)[0]
        assert row["evaluated"] is True
        assert row["threshold_met"] is True

    def test_filler_emits_in_neither_branch(self, tmp_path):
        filler = "zzzqqq unrelated lorem ipsum filler text padding here"
        assert _run(_sandbox(tmp_path / "a"), filler).stdout.strip() == ""
        assert _run(_sandbox(tmp_path / "b"), filler,
                    {"COS_RULE_ROUTER_ALL_PAYLOADS": "1"}).stdout.strip() == ""


def test_cross_session_stays_suppressed_by_operator_decision():
    """DECISION DEL OPERADOR, 2026-08-21: `cross-session` se suprime.

    Estaba en MACHINE_ORIGINS desde el principio, pero por default, no por
    decision: nadie la habia mirado. Quedaba abierta porque un relay entre
    sesiones PUEDE vehicular un pedido humano -- el texto lo escribio una
    persona, aunque el envoltorio lo ponga otra sesion.

    El operador decidio suprimirla igual. La evidencia que sostiene la decision,
    medida sobre los 680 prompts reales de 18 transcripts: 15 casos, y su tasa de
    emision es 0% -- nunca hizo que el router propusiera nada. Suprimir algo que
    emite cero no pierde ninguna sugerencia; solo deja de gastar la evaluacion.

    Este test existe para que revertirla cueste una decision explicita y no pase
    como un renombre. Si alguien la saca de MACHINE_ORIGINS, esto se pone rojo y
    lo obliga a escribir por que.
    """
    from cos_lib.prompt_origin import (MACHINE_ORIGINS, ORIGIN_CROSS_SESSION,
                                       classify_origin, skip_reason)
    # La forma sale de un transcript REAL, no inventada: mi primer intento uso un
    # `<cross-session-message>` a secas y clasifico como `typed`, porque el
    # marcador de verdad es la linea de texto que lo precede.
    real = ('Another Claude session sent a message:\n'
            '<cross-session-message from="uds:/tmp/cc-socks/2358">\n'
            'arregla el parser de fechas\n</cross-session-message>')
    assert classify_origin(real) == ORIGIN_CROSS_SESSION, (
        "el marcador dejo de reconocerse: un relay entre sesiones se estaria "
        "leyendo como prompt tipeado"
    )
    assert ORIGIN_CROSS_SESSION in MACHINE_ORIGINS
    assert skip_reason(real) == f"not-human-authored:{ORIGIN_CROSS_SESSION}"


def test_min_prompt_chars_matches_the_hooks_own_guard():
    """The Python constant and the bash literal must not drift apart."""
    src = HOOK_PATH.read_text()
    m = re.search(r'\$\{#prompt_text\}"?\s*-lt\s+(\d+)', src)
    assert m, "could not find the length guard in the hook"
    assert int(m.group(1)) == MIN_PROMPT_CHARS

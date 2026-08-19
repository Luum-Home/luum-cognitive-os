# SCOPE: os-only
"""Prueba exhaustiva del lazo de adherencia de skills.

Todo corre sobre fixtures sinteticos en ``tmp_path``. La telemetria real
(``.cognitive-os/metrics/*.jsonl``) es evidencia del operador: se lee, no se
escribe, y ningun test de este archivo la apunta.

Las cinco familias que exige el encargo, mas dos que salieron de escribirlo:

  trigger        sugerencia de alta confianza + invocacion -> el lazo cierra
  discriminador  alta confianza sin rastro -> hallazgo;
                 baja confianza sin rastro -> NO es hallazgo (el umbral corta)
  control nulo   sin sugerencias -> no inventa hallazgos
  instrumento    logger sin filas -> "no medible", nunca "0 invocaciones"
  mutacion       mover el umbral cambia el resultado (prueba que se lee)
  bypass         razon escrita cierra el lazo; bypass sin razon no
  read-only      la corrida no toca un solo byte de las fuentes
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = REPO_ROOT / "scripts" / "skill_adherence_loop.py"

BASE = datetime(2026, 8, 15, 3, 0, 0, tzinfo=timezone.utc)


# --------------------------------------------------------------------------- #
# Andamiaje de fixtures
# --------------------------------------------------------------------------- #
def _iso(offset_min: float) -> str:
    return (BASE + timedelta(minutes=offset_min)).isoformat()


def suggestion(offset_min: float, skill: str | None, confidence: float) -> dict:
    """Fila con el esquema exacto que emite hooks/skill-router-prompt-suggest.sh."""
    return {
        "ts": _iso(offset_min),
        "session_id": "unknown",
        "prompt_hash": hashlib.sha256(
            f"{offset_min}{skill}".encode()
        ).hexdigest()[:16],
        "skill_name": skill,
        "invoke_command": f"/{skill}" if skill else None,
        "confidence": confidence,
        "threshold_met": confidence >= 0.80,
    }


def invocation(offset_min: float, skill: str) -> dict:
    """Fila con el esquema exacto que emite hooks/skill-invocation-logger.sh."""
    return {
        "event_type": "skill.invoked",
        "payload": {"args": "", "session_id": "unknown", "skill_name": skill},
        "schema_version": 1,
        "severity": "info",
        "source": "skill-invocation-logger",
        "timestamp": _iso(offset_min),
    }


def bypass(offset_min: float, skill: str, reason: str, prompt_hash: str = "") -> dict:
    """Fila con el esquema que emite hooks/orchestrator-skill-invocation-gate.sh."""
    return {
        "ts": (BASE + timedelta(minutes=offset_min)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "session_id": "unknown",
        "prompt_hash": prompt_hash,
        "suggested_skill": skill,
        "confidence": 0.95,
        "reason": reason,
        "actor": "orchestrator-annotation",
    }


def write_corpus(
    tmp_path: Path,
    suggestions: list[dict],
    invocations: list[dict] | None = None,
    bypasses: list[dict] | None = None,
    *,
    omit_invocations_file: bool = False,
) -> tuple[Path, Path]:
    """Materializa un corpus sintetico. Devuelve (metrics_dir, events_file)."""
    metrics = tmp_path / "metrics"
    metrics.mkdir(exist_ok=True)

    def dump(name: str, rows: list[dict]) -> None:
        (metrics / name).write_text(
            "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8"
        )

    dump("skill-suggestion.jsonl", suggestions)
    if not omit_invocations_file:
        dump("skill-invocations.jsonl", invocations or [])
    if bypasses is not None:
        dump("skill-bypass.jsonl", bypasses)

    events = tmp_path / "events.jsonl"
    events.write_text("", encoding="utf-8")
    return metrics, events


def run(metrics: Path, events: Path, *extra: str) -> tuple[int, dict, str]:
    """Corre el artefacto en modo JSON y devuelve (exit_code, report, stderr)."""
    proc = subprocess.run(
        [
            sys.executable,
            str(ARTIFACT),
            "--metrics-dir",
            str(metrics),
            "--events-file",
            str(events),
            "--json",
            *extra,
        ],
        text=True,
        capture_output=True,
        timeout=90,
        check=False,
    )
    report = json.loads(proc.stdout) if proc.stdout.strip() else {}
    return proc.returncode, report, proc.stderr


def totals(report: dict) -> dict:
    return report["result"]["totals"]


# --------------------------------------------------------------------------- #
# 1. TRIGGER — el lazo cierra
# --------------------------------------------------------------------------- #
def test_trigger_high_confidence_suggestion_with_invocation_closes_the_loop(
    tmp_path: Path,
) -> None:
    metrics, events = write_corpus(
        tmp_path,
        suggestions=[suggestion(0, "run-tests", 0.95)],
        invocations=[invocation(2, "run-tests")],
    )
    code, report, _ = run(metrics, events)

    assert totals(report)["CLOSED"] == 1
    assert totals(report)["UNTRACED"] == 0
    assert totals(report)["UNMEASURABLE"] == 0
    assert report["result"]["adherence_over_measurable"] == 1.0
    assert report["result"]["findings"] == []
    assert code == 0, "un lazo cerrado no puede salir con hallazgos"

    detail = report["result"]["sessions"][0]["detail"][0]
    assert detail["verdict"] == "CLOSED"
    assert detail["evidence"] == "skill-invocations.jsonl", "la evidencia se declara"


def test_trigger_pairing_respects_the_window_and_the_skill_name(
    tmp_path: Path,
) -> None:
    """Una invocacion fuera de ventana, o de otra skill, no cierra el lazo.

    Sin esto el apareo seria "hubo alguna invocacion en algun momento", que es
    justamente el numero flojo que este script existe para no producir.
    """
    metrics, events = write_corpus(
        tmp_path,
        suggestions=[suggestion(0, "run-tests", 0.95)],
        # misma skill pero 45 min tarde (ventana = 30), y otra skill a tiempo.
        invocations=[invocation(45, "run-tests"), invocation(2, "cos-status")],
    )
    code, report, _ = run(metrics, events)

    assert totals(report)["CLOSED"] == 0
    assert totals(report)["UNTRACED"] == 1, "el logger estaba LIVE: es acusacion real"
    assert code == 1


# --------------------------------------------------------------------------- #
# 2. DISCRIMINADOR — el umbral corta de verdad
# --------------------------------------------------------------------------- #
def test_discriminator_high_confidence_without_trace_is_a_finding(
    tmp_path: Path,
) -> None:
    metrics, events = write_corpus(
        tmp_path,
        suggestions=[suggestion(0, "auto-rollback", 0.95)],
        # invocacion senuelo de OTRA skill: prueba que el logger grababa.
        invocations=[invocation(1, "otra-skill")],
        bypasses=[],
    )
    code, report, _ = run(metrics, events)

    assert report["result"]["sessions"][0]["logger_state"] == "LIVE"
    assert totals(report)["UNTRACED"] == 1
    assert totals(report)["UNMEASURABLE"] == 0
    assert code == 1

    finding = report["result"]["findings"][0]
    assert finding["skill"] == "auto-rollback"
    assert finding["confidence"] == 0.95


def test_discriminator_low_confidence_without_trace_is_not_a_finding(
    tmp_path: Path,
) -> None:
    """0.72 esta por debajo del umbral: no es mandatoria, no se acusa."""
    metrics, events = write_corpus(
        tmp_path,
        suggestions=[suggestion(0, "auto-rollback", 0.72)],
        invocations=[invocation(1, "otra-skill")],
        bypasses=[],
    )
    code, report, _ = run(metrics, events)

    assert report["result"]["high_confidence_total"] == 0
    assert totals(report)["UNTRACED"] == 0
    assert report["result"]["sessions"][0]["suggestions_below_threshold"] == 1
    assert code == 0


def test_discriminator_separates_high_from_low_in_the_same_session(
    tmp_path: Path,
) -> None:
    """Mezcladas en una sola ventana, el corte sigue cayendo donde debe."""
    metrics, events = write_corpus(
        tmp_path,
        suggestions=[
            suggestion(0, "alta-a", 0.95),
            suggestion(1, "baja-a", 0.60),
            suggestion(2, "alta-b", 0.90),
            suggestion(3, "baja-b", 0.89),  # justo por debajo de 0.90
        ],
        invocations=[invocation(4, "senuelo")],
        bypasses=[],
    )
    code, report, _ = run(metrics, events)

    assert report["result"]["high_confidence_total"] == 2
    assert totals(report)["UNTRACED"] == 2
    assert {f["skill"] for f in report["result"]["findings"]} == {"alta-a", "alta-b"}
    assert code == 1


# --------------------------------------------------------------------------- #
# 3. CONTROL NULO — no inventa hallazgos
# --------------------------------------------------------------------------- #
def test_null_control_no_suggestions_invents_nothing(tmp_path: Path) -> None:
    metrics, events = write_corpus(
        tmp_path, suggestions=[], invocations=[invocation(0, "run-tests")]
    )
    code, report, _ = run(metrics, events)

    assert report["result"]["sessions"] == []
    assert report["result"]["high_confidence_total"] == 0
    assert report["result"]["findings"] == []
    assert report["result"]["adherence_over_measurable"] is None, (
        "sin denominador no se publica una tasa; None, no 0.0 ni 1.0"
    )
    assert code == 0


def test_null_control_rows_without_skill_name_are_not_suggestions(
    tmp_path: Path,
) -> None:
    """El router loguea cada prompt; ``skill_name: null`` = no hubo match.

    En la telemetria real esas filas son mayoria. Contarlas como sugerencias
    infla el denominador y hunde artificialmente la tasa de adherencia.
    """
    metrics, events = write_corpus(
        tmp_path,
        suggestions=[suggestion(0, None, 0.0), suggestion(1, None, 0.0)],
        invocations=[],
    )
    code, report, _ = run(metrics, events)

    assert report["sources"]["suggestions"]["rows"] == 2
    assert report["sources"]["suggestions"]["usable"] == 0
    assert report["result"]["findings"] == []
    assert code == 0


# --------------------------------------------------------------------------- #
# 4. INSTRUMENTO MUERTO — "no medible", nunca "0 invocaciones"
# --------------------------------------------------------------------------- #
def test_dead_instrument_reports_unmeasurable_not_zero_invocations(
    tmp_path: Path,
) -> None:
    """El corazon del encargo: logger sin una sola fila.

    Sin la cuarta cubeta esta sugerencia se contaria como no-adherencia y la
    salida diria 0% de adherencia. Es ceguera, no incumplimiento.
    """
    metrics, events = write_corpus(
        tmp_path,
        suggestions=[suggestion(0, "auto-rollback", 0.95)],
        invocations=[],
        bypasses=[],
    )
    code, report, _ = run(metrics, events)

    assert report["result"]["sessions"][0]["logger_state"] == "DEAD_NO_ROWS"
    assert totals(report)["UNMEASURABLE"] == 1
    assert totals(report)["UNTRACED"] == 0, "con el instrumento mudo no se acusa"
    assert report["result"]["measurable_denominator"] == 0
    assert report["result"]["adherence_over_measurable"] is None
    assert report["result"]["blind_ratio"] == 1.0
    assert "MUDO" in report["instrument"]["logger_verdict"]
    assert code == 0, "ceguera no es hallazgo por defecto"


def test_dead_instrument_missing_file_is_not_an_error(tmp_path: Path) -> None:
    """El archivo ausente se trata igual que el archivo vacio: no medible."""
    metrics, events = write_corpus(
        tmp_path,
        suggestions=[suggestion(0, "auto-rollback", 0.95)],
        omit_invocations_file=True,
    )
    code, report, _ = run(metrics, events)

    assert report["sources"]["invocations"]["exists"] is False
    assert totals(report)["UNMEASURABLE"] == 1
    assert code == 0


def test_dead_instrument_stale_logger_does_not_accuse_later_sessions(
    tmp_path: Path,
) -> None:
    """El logger grabo y despues se callo: lo posterior no es acusable.

    Es el caso real de este repo — ultima fila 2026-08-15, sugerencias hasta
    2026-08-19 — y es el que mas facil se lee mal.
    """
    metrics, events = write_corpus(
        tmp_path,
        suggestions=[
            suggestion(0, "temprana", 0.95),      # con el logger vivo
            suggestion(600, "tardia", 0.95),      # 10 h despues, logger callado
        ],
        invocations=[invocation(1, "temprana")],
        bypasses=[],
    )
    code, report, _ = run(metrics, events)

    by_id = {s["id"]: s for s in report["result"]["sessions"]}
    states = {s["logger_state"] for s in by_id.values()}
    assert "LIVE" in states and "DEAD_OUT_OF_SPAN" in states

    assert totals(report)["CLOSED"] == 1
    assert totals(report)["UNMEASURABLE"] == 1
    assert totals(report)["UNTRACED"] == 0
    assert code == 0


def test_blind_findings_can_be_promoted_to_failure_on_demand(
    tmp_path: Path,
) -> None:
    """``--fail-on-blind`` existe para que la ceguera pueda romper un gate."""
    metrics, events = write_corpus(
        tmp_path,
        suggestions=[suggestion(0, "auto-rollback", 0.95)],
        invocations=[],
    )
    assert run(metrics, events)[0] == 0
    assert run(metrics, events, "--fail-on-blind")[0] == 1


# --------------------------------------------------------------------------- #
# 5. MUTACION — el umbral se lee de verdad
# --------------------------------------------------------------------------- #
def test_mutation_lowering_the_threshold_changes_the_verdict(
    tmp_path: Path,
) -> None:
    """Un umbral que no cambia nada al moverlo no esta siendo leido."""
    metrics, events = write_corpus(
        tmp_path,
        suggestions=[
            suggestion(0, "alta", 0.95),
            suggestion(1, "media", 0.70),
            suggestion(2, "baja", 0.30),
        ],
        invocations=[invocation(3, "senuelo")],
        bypasses=[],
    )
    code_default, default_report, _ = run(metrics, events)
    code_zero, zero_report, _ = run(metrics, events, "--threshold", "0.0")

    assert default_report["result"]["high_confidence_total"] == 1
    assert zero_report["result"]["high_confidence_total"] == 3, (
        "con umbral 0.0 las tres sugerencias entran al lazo"
    )
    assert totals(default_report)["UNTRACED"] == 1
    assert totals(zero_report)["UNTRACED"] == 3
    assert default_report["result"] != zero_report["result"]
    assert code_default == 1 and code_zero == 1


def test_mutation_raising_the_threshold_empties_the_loop(tmp_path: Path) -> None:
    """El movimiento inverso: subir el umbral tiene que apagar el hallazgo."""
    metrics, events = write_corpus(
        tmp_path,
        suggestions=[suggestion(0, "alta", 0.95)],
        invocations=[invocation(1, "senuelo")],
        bypasses=[],
    )
    assert run(metrics, events)[0] == 1
    code_high, report_high, _ = run(metrics, events, "--threshold", "0.99")
    assert report_high["result"]["high_confidence_total"] == 0
    assert code_high == 0


def test_mutation_threshold_is_echoed_in_the_report(tmp_path: Path) -> None:
    """El umbral usado viaja en la salida; un numero sin su umbral no se audita."""
    metrics, events = write_corpus(tmp_path, suggestions=[suggestion(0, "x", 0.95)])
    _, report, _ = run(metrics, events, "--threshold", "0.55")
    assert report["threshold"] == 0.55


@pytest.mark.parametrize("bad", ["1.5", "-0.1", "abc"])
def test_mutation_invalid_threshold_exits_two(tmp_path: Path, bad: str) -> None:
    metrics, events = write_corpus(tmp_path, suggestions=[suggestion(0, "x", 0.95)])
    code, _, _ = run(metrics, events, "--threshold", bad)
    assert code == 2


# --------------------------------------------------------------------------- #
# 6. BYPASS — la razon escrita es lo que cierra, no la anotacion vacia
# --------------------------------------------------------------------------- #
def test_bypass_with_written_reason_closes_the_loop(tmp_path: Path) -> None:
    sug = suggestion(0, "auto-rollback", 0.95)
    metrics, events = write_corpus(
        tmp_path,
        suggestions=[sug],
        invocations=[invocation(1, "senuelo")],
        bypasses=[
            bypass(1, "auto-rollback", "no aplica: el cambio es de docs", sug["prompt_hash"])
        ],
    )
    code, report, _ = run(metrics, events)

    assert totals(report)["BYPASSED"] == 1
    assert totals(report)["UNTRACED"] == 0
    assert report["result"]["adherence_over_measurable"] == 1.0
    assert code == 0


def test_bypass_without_reason_does_not_close_the_loop(tmp_path: Path) -> None:
    """§11 pide bypass AUDITADO. Sin razon escrita el lazo sigue abierto."""
    sug = suggestion(0, "auto-rollback", 0.95)
    metrics, events = write_corpus(
        tmp_path,
        suggestions=[sug],
        invocations=[invocation(1, "senuelo")],
        bypasses=[bypass(1, "auto-rollback", "", sug["prompt_hash"])],
    )
    code, report, _ = run(metrics, events)

    assert totals(report)["BYPASSED"] == 0
    assert totals(report)["UNTRACED"] == 1
    assert code == 1


# --------------------------------------------------------------------------- #
# 7. HIGIENE — determinismo, read-only y errores duros
# --------------------------------------------------------------------------- #
def test_run_is_deterministic_and_read_only(tmp_path: Path) -> None:
    """Dos corridas identicas, y ni un byte tocado en las fuentes."""
    metrics, events = write_corpus(
        tmp_path,
        suggestions=[suggestion(0, "alta", 0.95), suggestion(5, "otra", 0.95)],
        invocations=[invocation(1, "alta")],
        bypasses=[],
    )

    def fingerprint() -> dict[str, str]:
        return {
            str(p.relative_to(tmp_path)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(tmp_path.rglob("*"))
            if p.is_file()
        }

    before = fingerprint()
    code_a, report_a, _ = run(metrics, events)
    code_b, report_b, _ = run(metrics, events)
    after = fingerprint()

    assert report_a == report_b, "misma entrada, misma salida"
    assert code_a == code_b
    assert before == after, "el script escribio sobre sus fuentes"


def test_missing_suggestion_source_is_an_error_not_zero_findings(
    tmp_path: Path,
) -> None:
    """Sin la fuente no hay lazo que medir; salir 0 seria mentir en verde."""
    metrics = tmp_path / "vacio"
    metrics.mkdir()
    events = tmp_path / "events.jsonl"
    events.write_text("", encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, str(ARTIFACT), "--metrics-dir", str(metrics),
         "--events-file", str(events), "--json"],
        text=True, capture_output=True, timeout=90, check=False,
    )
    assert proc.returncode == 2
    assert "skill-suggestion.jsonl" in proc.stderr


def test_malformed_rows_are_counted_not_swallowed(tmp_path: Path) -> None:
    """Una fila rota se declara en el reporte en vez de desaparecer."""
    metrics, events = write_corpus(
        tmp_path,
        suggestions=[suggestion(0, "alta", 0.95)],
        invocations=[invocation(1, "alta")],
    )
    with (metrics / "skill-suggestion.jsonl").open("a", encoding="utf-8") as fh:
        fh.write("{esto no es json\n")

    code, report, _ = run(metrics, events)
    assert report["sources"]["suggestions"]["malformed"] == 1
    assert report["sources"]["suggestions"]["usable"] == 1
    assert code == 0


def test_derived_sessions_are_labelled_as_derived(tmp_path: Path) -> None:
    """Una ventana inferida no puede leerse como una sesion grabada."""
    metrics, events = write_corpus(
        tmp_path,
        suggestions=[suggestion(0, "a", 0.95), suggestion(120, "b", 0.95)],
        invocations=[invocation(1, "a")],
    )
    _, report, _ = run(metrics, events)
    sessions = report["result"]["sessions"]
    assert len(sessions) == 2, "120 min de hueco separan dos sesiones"
    assert all(s["source"] == "derived" for s in sessions)
    assert all(s["id"].startswith("derived:") for s in sessions)


def test_recorded_session_id_is_used_when_present(tmp_path: Path) -> None:
    """Cuando el session_id existe manda el grabado, no el derivado."""
    rows = [suggestion(0, "a", 0.95), suggestion(500, "b", 0.95)]
    for row in rows:
        row["session_id"] = "sess-real-1"
    metrics, events = write_corpus(tmp_path, suggestions=rows, invocations=[])

    _, report, _ = run(metrics, events)
    sessions = report["result"]["sessions"]
    assert len(sessions) == 1, "mismo session_id grabado = una sola sesion"
    assert sessions[0]["id"] == "rec:sess-real-1"
    assert sessions[0]["source"] == "recorded"


def test_events_skill_invoked_channel_is_reported(tmp_path: Path) -> None:
    """El gate consulta events.jsonl; el reporte tiene que decir si hay algo ahi."""
    metrics, events = write_corpus(
        tmp_path, suggestions=[suggestion(0, "a", 0.95)], invocations=[]
    )
    _, empty_report, _ = run(metrics, events)
    assert empty_report["instrument"]["events_skill_invoked"] == 0

    events.write_text(
        json.dumps({"event_type": "skill-invoked", "session_id": "s",
                    "payload": {"skill": "a"}}) + "\n",
        encoding="utf-8",
    )
    _, filled_report, _ = run(metrics, events)
    assert filled_report["instrument"]["events_skill_invoked"] == 1


def test_human_output_names_blindness_explicitly(tmp_path: Path) -> None:
    """La salida legible tiene que decir la palabra, no dejarla implicita."""
    metrics, events = write_corpus(
        tmp_path, suggestions=[suggestion(0, "a", 0.95)], invocations=[]
    )
    proc = subprocess.run(
        [sys.executable, str(ARTIFACT), "--metrics-dir", str(metrics),
         "--events-file", str(events)],
        text=True, capture_output=True, timeout=90, check=False,
    )
    assert proc.returncode == 0
    assert "UNMEASURABLE" in proc.stdout
    assert "NO CALCULABLE" in proc.stdout
    assert "lazo no observado" in proc.stdout

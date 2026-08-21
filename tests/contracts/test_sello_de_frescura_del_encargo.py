"""El encargo llega sellado, y sus premisas llegan como comandos.

Qué se mide y por qué
---------------------
Un encargo se congela cuando se lanza; el repo sigue moviéndose mientras el
agente corre sus 10-20 minutos. Una premisa vencida y una correcta se leen
exactamente igual, así que sin sello el agente no tiene forma de saber contra qué
foto fue escrito el texto.

Medido el 2026-08-20: tres encargos de una misma jornada afirmaron hechos que ya
eran falsos cuando el agente los leyó (`templates/project-gotchas.md` "dice"
algo ya corregido; un hook "registrado cero veces" medido con el instrumento
equivocado; `git worktree` "bloqueado" generalizando desde un solo bloqueo). Las
tres veces la red fue el agente corriendo el comando — al costo de una corrida
entera de agente cada vez.

De dónde salen las aserciones
-----------------------------
NO de leer la implementación. El sha esperado se le pregunta a `git` en un
subproceso independiente, y los positivos del detector salen de las secciones
"## Correcciones a las premisas del encargo" de los informes de ese día,
congeladas en tests/fixtures/briefs/. Un gate escrito desde el mismo modelo que
la implementación hereda su error y lo blinda.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "scripts"
FIXTURES = REPO / "tests" / "fixtures" / "briefs"
PREMISAS_VENCIDAS = FIXTURES / "premisas-que-vencieron-2026-08-20.txt"
ENCARGO_REAL = FIXTURES / "encargo-premisas-vencidas-2026-08-20.txt"

sys.path.insert(0, str(SCRIPTS))


def _import(name: str):
    import importlib

    return importlib.import_module(name)


def _head_segun_git() -> str:
    """El sha, preguntado aparte de la implementación que se está midiendo."""
    out = subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=False,
    )
    if out.returncode != 0:
        pytest.skip("sin git: el sello degrada a vacío por diseño")
    return out.stdout.strip()


# ── El sello ────────────────────────────────────────────────────────────────


def test_el_sello_lleva_el_head_real_y_no_uno_recordado():
    compose = _import("compose_agent_prompt")
    sello = compose.build_freshness_seal(REPO)
    head = _head_segun_git()
    assert head in sello, (
        "el sello no contiene el HEAD que git reporta ahora mismo. Un sello con "
        "un sha viejo o inventado es peor que ninguno: le da al agente una "
        "referencia falsa contra la que creer que verificó."
    )
    assert "git rev-parse HEAD" in sello, (
        "el sello dice contra qué se escribió pero no cómo comprobarlo. Sin el "
        "comando, vuelve a ser una conclusión."
    )


def test_el_sello_va_aunque_no_matchee_ninguna_trampa():
    """El caso donde antes el prompt salía idéntico a como entró — y es justo el
    caso donde nadie se entera de que la foto envejeció."""
    compose = _import("compose_agent_prompt")
    prompt = "Escribir un haiku sobre el otoño.\n"
    salida = compose.compose(prompt, REPO / "templates" / "no-existe.md", REPO)
    assert "SELLO DE FRESCURA" in salida, (
        "un encargo sin trampas ni premisas salió sin sello: la fuga es "
        "exactamente el encargo que nadie sospecha"
    )
    assert prompt.strip() in salida, "el compositor comió el encargo original"


def test_el_contrato_del_sello_viaja_en_el_canal_fijo():
    """Sellar sin decir qué hacer con el sello no sirve: el agente tiene que
    saber que un sha distinto convierte cada premisa en hipótesis."""
    texto = (REPO / "templates" / "agent-mandatory-rules.md").read_text()
    faltan = [
        m for m in ("SELLO DE FRESCURA", "git rev-parse HEAD", "hypothesis")
        if m not in texto
    ]
    assert not faltan, f"el canal a sub-agentes no explica el sello: falta {faltan}"


# ── El detector de premisas ─────────────────────────────────────────────────


def test_detecta_las_premisas_que_de_hecho_vencieron_ese_dia():
    """Los positivos NO son inventados: son las premisas que agentes reales
    refutaron el 2026-08-20, transcriptas de sus informes."""
    lint = _import("brief_premise_lint")
    texto = PREMISAS_VENCIDAS.read_text(encoding="utf-8")
    esperadas = [
        (i, l) for i, l in enumerate(texto.splitlines(), 1)
        if l.strip() and not l.startswith("#")
    ]
    hallados = {f.line for f in lint.lint(texto)}
    perdidas = [l for i, l in esperadas if i not in hallados]
    assert not perdidas, (
        f"{len(perdidas)} de {len(esperadas)} premisas que YA se pudrieron pasan "
        "sin ser marcadas:\n  " + "\n  ".join(perdidas)
    )


def test_no_le_grita_a_la_instruccion_pura():
    """Un detector que grita por todo se desactiva, y entonces no detecta nada.

    `templates/agent-preamble.md` es instrucción sin una sola afirmación sobre el
    estado del repo: es el control negativo natural, y ninguna de sus 70+ líneas
    debería disparar.
    """
    lint = _import("brief_premise_lint")
    hallazgos = lint.lint((REPO / "templates" / "agent-preamble.md").read_text())
    assert not hallazgos, (
        "el detector marca instrucción pura como premisa: "
        + "; ".join(f"L{f.line} {f.text[:70]}" for f in hallazgos)
    )


def test_una_premisa_que_ya_viaja_con_su_comando_no_se_marca():
    """La forma correcta no se pena. Si el detector molestara igual, el incentivo
    apuntaría a sacar los comandos del encargo."""
    lint = _import("brief_premise_lint")
    conclusion = "El hook `hooks/foo.sh` no existe en el árbol."
    con_comando = "Corré `ls -la hooks/foo.sh && readlink -f hooks/foo.sh` antes de citarlo."
    assert lint.lint(conclusion), "sonda rota: la conclusión tampoco dispara"
    assert not lint.lint(con_comando), "marcó una premisa que ya viaja ejecutable"


def test_el_detector_avisa_y_no_bloquea():
    """La decisión de diseño, cableada: un falso positivo que bloquea cuesta una
    corrida de agente; uno que avisa cuesta tres líneas de texto."""
    r = subprocess.run(
        [sys.executable, str(SCRIPTS / "compose_agent_prompt.py"), str(ENCARGO_REAL)],
        capture_output=True, text=True, check=False,
    )
    assert r.returncode == 0, "el compositor bloqueó un lanzamiento; es advisory"
    assert "PREMISAS DECLARATIVAS DETECTADAS" in r.stdout
    assert "no bloquea el lanzamiento" in r.stdout
    r2 = subprocess.run(
        [sys.executable, str(SCRIPTS / "brief_premise_lint.py"), "--quiet", str(ENCARGO_REAL)],
        capture_output=True, text=True, check=False,
    )
    assert r2.returncode == 1, (
        "el detector standalone debe salir 1 con hallazgos (contrato "
        "evidencia-ejecutable: 0 limpio / 1 hallazgos / 2 error)"
    )

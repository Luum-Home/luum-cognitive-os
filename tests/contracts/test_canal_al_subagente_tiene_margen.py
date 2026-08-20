"""El canal que se le inyecta a cada sub-agente no puede quedar sin margen.

Qué se mide y por qué
---------------------
`hooks/subagent-context-injector.sh` arma el contexto que todo sub-agente recibe
ANTES de su primer tool-call, y lo trunca a 10.000 caracteres — el tope duro de
`additionalContext`. El truncado corta **al final**, y al final vive el contrato
de reporte (`RESULT:` / `TRUST_REPORT:`) que el preámbulo le pide al agente.

O sea: cuando el canal se pasa, lo primero que se pierde es la instrucción de
cómo reportar. Y se pierde **en silencio** para quien escribió el texto: el
marcador de truncado lo ve el agente, no el autor.

Medido el 2026-08-20, y la razón por la que existe este archivo:

    antes de esa sesión   9.193 de 10.000   margen 807
    después               9.926 de 10.000   margen  74

Una sola jornada de correcciones —todas correctas, todas necesarias— consumió el
91% del margen. Ninguna era gratuita y ninguna se notó, porque nada medía el
total. Es la misma forma que esa sesión persiguió todo el día: un límite real,
un consumo invisible, y ningún instrumento preguntando.

Por qué el techo de este test es más bajo que el del injector
------------------------------------------------------------
El injector concatena DESPUÉS el "sidecar" de sesiones previas, cuyo tamaño es
variable y no está bajo control de quien edita estas plantillas. Un presupuesto
estático igual a 10.000 estaría verde justo hasta el día en que hay sidecar, y
ahí truncaría sin que nadie hubiera cambiado nada.

`PRESUPUESTO_ESTATICO` deja espacio para eso. No es un número de confort: es el
reconocimiento de que la parte fija comparte el cupo con una parte variable.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
INJECTOR = REPO / "hooks" / "subagent-context-injector.sh"

# Las dos fuentes que el injector SIEMPRE concatena (líneas 129 y 134-139).
FIJAS = [
    REPO / "templates" / "agent-mandatory-rules.md",
    REPO / "templates" / "agent-preamble.md",
]

# El techo real del injector, leído de su fuente y no transcripto acá — si él lo
# cambia, este test tiene que enterarse en vez de seguir midiendo contra un
# número viejo.
def _tope_del_injector() -> int:
    m = re.search(r"^MAX_CONTEXT_CHARS=(\d+)", INJECTOR.read_text(), re.M)
    assert m, "no se pudo leer MAX_CONTEXT_CHARS del injector: cambió de forma"
    return int(m.group(1))


# Espacio reservado para el sidecar variable. Bajarlo es legítimo; subirlo es
# comprarse el truncado silencioso del día que haya contenido de sesiones
# previas, que es exactamente lo que este test existe para impedir.
RESERVA_SIDECAR = 1200


def _tamanio_fijo() -> int:
    total = 0
    for i, f in enumerate(FIJAS):
        assert f.is_file(), f"{f} no existe: el injector la lee y no está"
        total += len(f.read_text())
        if i:  # el injector une con un salto de línea
            total += 1
    return total


def test_el_injector_sigue_teniendo_un_tope():
    """Si el truncado desapareciera, este test no tendría sentido y hay que saberlo."""
    assert _tope_del_injector() > 0
    assert "MAX_CONTEXT_CHARS" in INJECTOR.read_text()


def test_la_parte_fija_deja_lugar_para_el_sidecar():
    """El hallazgo. La suma de las plantillas fijas más la reserva no puede
    pasarse del tope del injector.

    Si esto falla, la respuesta NO es subir RESERVA_SIDECAR ni el tope: es
    recortar las plantillas. El truncado ya existe y es silencioso para quien
    edita; este test es el único momento en que el crecimiento se ve.
    """
    fijo = _tamanio_fijo()
    tope = _tope_del_injector()
    presupuesto = tope - RESERVA_SIDECAR
    assert fijo <= presupuesto, (
        f"el canal fijo mide {fijo} caracteres y el presupuesto es {presupuesto} "
        f"({tope} del injector menos {RESERVA_SIDECAR} reservados para el sidecar "
        f"de sesiones previas). Sobran {fijo - presupuesto}.\n\n"
        "Cuando el total se pasa, el injector trunca AL FINAL, y al final vive el "
        "contrato de reporte que el preámbulo le pide al agente: se pierde la "
        "instrucción de cómo reportar, en silencio para quien escribió el texto.\n\n"
        "Recortá las plantillas. Subir la reserva o el tope apaga la medición, "
        "no el problema.\n\n"
        "Archivos: " + ", ".join(str(f.relative_to(REPO)) for f in FIJAS)
    )


def test_el_contrato_de_reporte_esta_en_el_canal():
    """Control: sin esto, recortar hasta pasar el test podría borrar justo lo
    que el truncado borraba, y el gate quedaría verde por haber hecho a mano el
    daño que existe para prevenir."""
    texto = "\n".join(f.read_text() for f in FIJAS if f.is_file())
    faltan = [m for m in ("RESULT:", "TRUST_REPORT:") if m not in texto]
    assert not faltan, (
        f"el canal ya no le pide al agente {faltan}. Si se quitó a propósito, "
        "actualizá este control; si se perdió recortando para pasar el test de "
        "arriba, se hizo a mano el daño que el truncado hacía solo."
    )


def test_la_reserva_es_declarada_y_no_cero():
    """Una reserva en cero convierte este gate en el mismo truncado silencioso,
    solo que medido."""
    assert RESERVA_SIDECAR > 0, "sin reserva, el sidecar trunca y el gate no lo ve"

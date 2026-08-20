# SCOPE: os-only
"""Prueba de portabilidad de cos_lib/measurement.py.

El artefacto es SCOPE: both, o sea que se instala en el proyecto de otra
persona. Ahi no existe este repo, ni su cwd, ni su .venv. La sonda copia el
modulo a una raiz arbitraria, lo importa desde ahi y lo ejercita, para falsar la
hipotesis de que solo funciona en casa.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "cos_lib" / "measurement.py"


def _load_from(path: Path, name: str = "measurement_portable"):
    """Carga por ruta, registrando en sys.modules ANTES de ejecutar.

    No es ceremonia: dataclasses resuelve las anotaciones vía
    ``sys.modules[cls.__module__].__dict__``, y sin el registro previo eso es
    ``None.__dict__``. La sonda lo descubrió fallando, y el patrón importa
    porque este repo carga scripts así en sus propios tests.
    """
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return mod


def test_measurement_funciona_desde_una_raiz_arbitraria(tmp_path: Path) -> None:
    destino = tmp_path / "proyecto-ajeno" / "cos_lib"
    destino.mkdir(parents=True)
    copia = destino / "measurement.py"
    copia.write_text(ARTIFACT.read_text(encoding="utf-8"), encoding="utf-8")

    mod = _load_from(copia)
    censo = mod.Census(
        subject="sonda",
        sources=("un archivo del proyecto ajeno",),
        buckets={"ok": 1, "mal": 0},
        blind={"ninguna": 0},
        how="python3 -m pytest tests/red_team/portability/test_measurement.py",
    )
    assert censo.population == 1
    assert censo.share("ok") == 1.0
    assert "sonda" in censo.render()


def test_no_depende_del_repo_ni_de_su_cwd(tmp_path: Path, monkeypatch) -> None:
    """Sin imports del repo y sin leer el cwd: el modulo es autocontenido."""
    fuente = ARTIFACT.read_text(encoding="utf-8")
    assert str(REPO_ROOT) not in fuente, "ruta absoluta del repo embebida"
    assert "cos_lib." not in fuente.replace("cos_lib/measurement.py", ""), (
        "importa otro modulo del repo; no sobrevive a la proyeccion sola"
    )

    copia = tmp_path / "measurement.py"
    copia.write_text(fuente, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))
    sys.modules.pop("measurement_portable", None)
    mod = _load_from(copia)

    # La garantia central tiene que sobrevivir el viaje: sin ceguera declarada,
    # no hay censo.
    try:
        mod.Census(
            subject="x",
            sources=("f",),
            buckets={"a": 1},
            blind={},
            how="python3 -m pytest tests/red_team/portability/test_measurement.py",
        )
    except mod.CensusError:
        pass
    else:  # pragma: no cover
        raise AssertionError("la ceguera dejo de ser obligatoria fuera del repo")


def test_la_ceguera_alta_sigue_avisando_en_el_proyecto_ajeno(tmp_path: Path) -> None:
    copia = tmp_path / "measurement.py"
    copia.write_text(ARTIFACT.read_text(encoding="utf-8"), encoding="utf-8")
    mod = _load_from(copia)
    censo = mod.Census(
        subject="hallazgos",
        sources=("telemetria local",),
        buckets={"hallazgos": 0},
        blind={"instrumento sin datos": 40},
        how="python3 -m pytest tests/red_team/portability/test_measurement.py",
    )
    assert censo.is_a_finding("hallazgos") is False
    assert "no-observación" in censo.describe("hallazgos")

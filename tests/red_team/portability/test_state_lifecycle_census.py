# SPDX-License-Identifier: MIT
"""Prueba de portabilidad del censo de estado: por que es `os-only`.

La afirmacion a falsar es "este primitivo no tiene nada que medir fuera del SO".
Su poblacion son las superficies de `.cognitive-os/runtime` y `.cognitive-os/metrics`,
que un checkout de consumidor no tiene. Si en un arbol sin `.cognitive-os` el censo
igual devolviera familias, el scope declarado seria mentira y este archivo lo dice.

Sonda de falsacion: el mismo arbol, con y sin `.cognitive-os`. Uno tiene que dar
vacio y el otro no. Si el par empatara, la prueba dejaria de probar nada.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

import scripts.state_lifecycle_census as census  # noqa: E402


def _apuntar(monkeypatch, root: Path) -> dict:
    monkeypatch.setattr(census, "REPO", root)
    monkeypatch.setattr(census, "RUNTIME", root / ".cognitive-os" / "runtime")
    monkeypatch.setattr(census, "METRICS", root / ".cognitive-os" / "metrics")
    monkeypatch.setattr(census, "METRICS_ARCHIVE", root / ".cognitive-os" / "metrics" / ".archive")
    monkeypatch.setattr(census, "MANIFEST", root / "manifests" / "state-retention.yaml")
    monkeypatch.setattr(census, "CODE_DIRS", ("hooks", "scripts"))
    return census.build()


def _consumidor(tmp_path: Path) -> Path:
    """Checkout de consumidor: tiene hooks y scripts, no tiene .cognitive-os."""
    (tmp_path / "hooks").mkdir()
    (tmp_path / "hooks" / "algo.sh").write_text("#!/usr/bin/env bash\necho hola\n")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "manifests").mkdir()
    (tmp_path / "manifests" / "state-retention.yaml").write_text("surfaces: []\n")
    return tmp_path


def test_en_un_arbol_sin_cognitive_os_el_censo_no_mide_nada(tmp_path, monkeypatch):
    pop = _apuntar(monkeypatch, _consumidor(tmp_path))
    assert pop == {}, (
        "un consumidor no tiene estado de runtime del SO que censar; si aparecen "
        f"familias, el scope os-only esta mal declarado. pop={pop}"
    )


def test_en_un_arbol_sin_cognitive_os_no_explota(tmp_path, monkeypatch):
    """os-only no puede significar 'revienta afuera'. Degrada, no rompe."""
    root = _consumidor(tmp_path)
    try:
        _apuntar(monkeypatch, root)
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"el censo tiene que degradar a vacio, no fallar: {exc!r}")


def test_sonda_de_falsacion_el_mismo_arbol_con_cognitive_os_si_mide(tmp_path, monkeypatch):
    """El par de la primera. Unico cambio: existe .cognitive-os."""
    root = _consumidor(tmp_path)
    runtime = root / ".cognitive-os" / "runtime"
    runtime.mkdir(parents=True)
    (runtime / "una-superficie-de-estado").write_text("1\n")
    (root / ".cognitive-os" / "metrics").mkdir(parents=True)

    pop = _apuntar(monkeypatch, root)
    assert pop, "sin este lado el test anterior pasaria aunque el censo no midiera nunca"
    assert any(v["family"] == "una-superficie-de-estado" for v in pop.values()), pop

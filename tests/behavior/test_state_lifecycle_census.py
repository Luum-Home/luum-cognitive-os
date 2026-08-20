# SPDX-License-Identifier: MIT
"""Comportamiento del censo de estado sin ciclo de vida.

Cada test arma un arbol falso, corre el clasificador de verdad y mira el
veredicto. Los dos primeros son un par: el mismo archivo, con y sin codigo de
reset, tiene que caer en cubetas distintas. Si el clasificador ignorara la
evidencia de reset, el par pasaria a dar lo mismo y la sonda muere.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

import scripts.state_lifecycle_census as census  # noqa: E402


def _tree(tmp_path: Path, *, hook_body: str, extra: dict[str, str] | None = None) -> Path:
    """Arbol minimo: un archivo de estado, un hook que lo lee, un manifiesto vacio."""
    runtime = tmp_path / ".cognitive-os" / "runtime"
    runtime.mkdir(parents=True)
    (runtime / "gate-counter-familia").write_text("143\n")
    (tmp_path / ".cognitive-os" / "metrics").mkdir(parents=True)

    hooks = tmp_path / "hooks"
    hooks.mkdir()
    (hooks / "el-gate.sh").write_text(hook_body)

    manifest = tmp_path / "manifests"
    manifest.mkdir()
    (manifest / "state-retention.yaml").write_text("surfaces: []\n")

    for rel, body in (extra or {}).items():
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body)
        target.chmod(0o755)
    return tmp_path


@pytest.fixture
def apuntar_a(monkeypatch):
    def _apply(root: Path, code_dirs: tuple[str, ...] = ("hooks", "scripts")) -> dict:
        monkeypatch.setattr(census, "REPO", root)
        monkeypatch.setattr(census, "RUNTIME", root / ".cognitive-os" / "runtime")
        monkeypatch.setattr(census, "METRICS", root / ".cognitive-os" / "metrics")
        monkeypatch.setattr(census, "METRICS_ARCHIVE", root / ".cognitive-os" / "metrics" / ".archive")
        monkeypatch.setattr(census, "MANIFEST", root / "manifests" / "state-retention.yaml")
        monkeypatch.setattr(census, "CODE_DIRS", code_dirs)
        return census.build()

    return _apply


LECTOR_QUE_BLOQUEA = """#!/usr/bin/env bash
count=$(cat "$RUNTIME/gate-counter-familia")
if [ "$count" -ge 3 ]; then
  echo "BLOCK: insistencia" >&2
  exit 2
fi
"""


def test_lector_que_bloquea_y_nadie_resetea_cae_en_gobierna_sin_reset(tmp_path, apuntar_a):
    pop = apuntar_a(_tree(tmp_path, hook_body=LECTOR_QUE_BLOQUEA))

    entry = next(v for v in pop.values() if v["family"] == "gate-counter-familia")
    assert entry["bucket"] == "gobierna-sin-reset", entry
    assert any("hooks/el-gate.sh" in ref for ref in entry["governing"]), entry["governing"]
    assert entry["resetters"] == []


def test_sonda_de_falsacion_el_mismo_archivo_con_reset_cambia_de_cubeta(tmp_path, apuntar_a):
    """El par de la anterior. Unico cambio: existe codigo que lo borra."""
    pop = apuntar_a(
        _tree(
            tmp_path,
            hook_body=LECTOR_QUE_BLOQUEA,
            extra={"scripts/reaper.sh": '#!/usr/bin/env bash\nrm -f "$RUNTIME/gate-counter-familia"\n'},
        )
    )

    entry = next(v for v in pop.values() if v["family"] == "gate-counter-familia")
    assert entry["bucket"] == "gobierna-con-ciclo", entry
    assert entry["resetters"], "el rm del reaper tiene que contarse como ciclo de vida"


def test_lector_sin_extension_no_produce_un_falso_nadie_lo_lee(tmp_path, apuntar_a):
    """Regresion 2026-08-20: filtrar por extension perdia scripts/cos-graphify-*.

    Ese filtro invento dos huerfanos cuyo lector era un ejecutable con shebang y
    sin sufijo. Nota: tener PRODUCTOR no saca a nadie de "nadie-lo-lee" -- la
    cubeta habla del lector, no del escritor. Lo que la sonda mata es que el
    barrido ni siquiera abra el archivo sin extension.
    """
    root = _tree(
        tmp_path,
        hook_body="#!/usr/bin/env bash\necho sin-referencias\n",
        extra={
            "scripts/cos-medir-algo": (
                '#!/usr/bin/env bash\ncat "$PROJECT/.cognitive-os/metrics/medicion-huerfana.jsonl"\n'
            )
        },
    )
    (root / ".cognitive-os" / "metrics" / "medicion-huerfana.jsonl").write_text("")
    assert os.access(root / "scripts" / "cos-medir-algo", os.X_OK)

    pop = apuntar_a(root)
    entry = next(v for v in pop.values() if v["family"] == "medicion-huerfana.jsonl")
    assert any("cos-medir-algo" in ref for ref in entry["readers"]), (
        "el ejecutable sin extension quedo fuera del barrido; ese filtro es el que "
        f"fabrica huerfanos falsos. entry={entry}"
    )
    assert entry["bucket"] != "nadie-lo-lee", entry


def test_el_censo_publicado_declara_poblacion_y_ceguera(tmp_path, apuntar_a):
    """Un conteo sin ceguera declarada no puede salir de este script."""
    apuntar_a(_tree(tmp_path, hook_body=LECTOR_QUE_BLOQUEA))
    from cos_lib.measurement import Census, CensusError

    with pytest.raises(CensusError):
        Census(
            subject="censo sin ceguera",
            sources=("x",),
            buckets={"a": 1},
            blind={},
            how=census.HOW,
        )

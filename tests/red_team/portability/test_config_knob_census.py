# SPDX-License-Identifier: MIT
"""Prueba de portabilidad del censo de perillas: por que es `os-only`.

La afirmacion a falsar es "lo que este primitivo mide solo existe en el SO". Su
sujeto no son "archivos yaml" en general: son las lecturas *shell* del
`cognitive-os.yaml` canonico que viven en el plano de control del SO (`hooks/`,
`scripts/`, `cos_lib/`, `packages/`, `.claude/`, `.codex/`, `.opencode/`). Un
checkout de consumidor tiene un `cognitive-os.yaml` — se lo deja
`/cognitive-os-init` — pero no tiene esos lectores. Sin lectores no hay nada que
censar, y por eso el scope es os-only.

Sonda de falsacion: el MISMO arbol con dos lectores distintos. Uno corta el
comentario de fin de linea y el otro no. Si el par empatara —si el censo dijera
lo mismo de los dos— el instrumento seria ciego a la forma que dice medir, y
entonces el "cero hallazgos" del checkout de consumidor no probaria nada:
podria ser ceguera y no ausencia.

El tercer test es guarda de regresion del arreglo del 2026-08-20: la forma
`s/.*clave:[[:space:]]*//; s/#.*$//` es la que quedo en los seis hooks, y el
censo tiene que reconocerla como sana.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

import scripts.config_knob_census as census  # noqa: E402

CANON = "session:\n  lock_timeout_seconds: 300        # Lock auto-expires after 5 minutes\n"

# Lector roto: corta la clave, no corta el comentario. Es la forma 3.
LECTOR_SIN_CORTE = """#!/usr/bin/env bash
CONFIG_FILE="$PROJECT_DIR/cognitive-os.yaml"
T=$(grep 'lock_timeout_seconds:' "$CONFIG_FILE" | head -1 \
  | sed 's/.*lock_timeout_seconds:[[:space:]]*//' | tr -d '[:space:]')
"""

# Lector sano: el mismo, con el corte que se aplico en los seis hooks.
LECTOR_CON_CORTE = LECTOR_SIN_CORTE.replace(
    "sed 's/.*lock_timeout_seconds:[[:space:]]*//'",
    "sed 's/.*lock_timeout_seconds:[[:space:]]*//; s/#.*$//'",
)

# Lo que SI tiene un consumidor: el yaml, y codigo que no lo lee por shell.
CORPUS_CONSUMIDOR = {
    "scripts/build.sh": "#!/usr/bin/env bash\nnpm run build\n",
    "hooks/mi-hook.sh": "#!/usr/bin/env bash\necho hola\n",
}


def _censar(monkeypatch, tmp_path: Path, corpus: dict[str, str]) -> list[dict]:
    canon = tmp_path / "cognitive-os.yaml"
    canon.write_text(CANON)
    monkeypatch.setattr(census, "CANONICAL", canon)
    monkeypatch.setattr(census, "REPO", tmp_path)
    _, detalles = census.census_paths(corpus)
    return detalles


def test_un_checkout_de_consumidor_no_tiene_perillas_que_censar(tmp_path, monkeypatch):
    """os-only: sin lectores shell del canonico, el censo no encuentra nada."""
    detalles = _censar(monkeypatch, tmp_path, dict(CORPUS_CONSUMIDOR))
    assert detalles == [], (
        "un consumidor no tiene lecturas shell del cognitive-os.yaml del SO; si "
        f"aparecen hallazgos, el scope os-only esta mal declarado. detalles={detalles}"
    )


def test_la_sonda_de_falsacion_separa_al_lector_roto_del_sano(tmp_path, monkeypatch):
    """El par tiene que dar distinto, o el censo es ciego a lo que dice medir."""
    roto = _censar(monkeypatch, tmp_path,
                   {**CORPUS_CONSUMIDOR, "hooks/lector.sh": LECTOR_SIN_CORTE})
    sano = _censar(monkeypatch, tmp_path,
                   {**CORPUS_CONSUMIDOR, "hooks/lector.sh": LECTOR_CON_CORTE})

    formas_rotas = [d for d in roto if d.get("form") == 3]
    formas_sanas = [d for d in sano if d.get("form") == 3]

    assert formas_rotas, "el censo no vio la forma 3 en un lector que la tiene"
    assert not formas_sanas, (
        f"el censo marca como rota la forma que SI corta el comentario: {formas_sanas}"
    )
    assert formas_rotas != formas_sanas, "el par empato: la sonda no prueba nada"


def test_la_forma_que_quedo_en_los_seis_hooks_se_reconoce_sana(tmp_path, monkeypatch):
    """Regresion del arreglo 2026-08-20 sobre concurrent-write-guard y sus cinco pares."""
    detalles = _censar(monkeypatch, tmp_path,
                       {"hooks/lector.sh": LECTOR_CON_CORTE})
    assert [d for d in detalles if d.get("form") == 3] == []

# SCOPE: os-only
"""Portability proof for scripts/session-cleanup-counterfactual.sh.

La version anterior de este test afirmaba `"BORRADO" not in stdout` sobre la
salida ENTERA. Con una sola corrida alcanzaba; con tres es una asercion que no
distingue el caso bueno del malo — en RUN B el directorio se retira a proposito
(archive-first de ADR-119) y en RUN C se destruye a proposito, porque de eso se
trata un contrafactico. Se afirma por bloque, que ademas es mas fuerte: ahora
tambien se exige que el contrafactico REPRODUZCA el danio.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "scripts/session-cleanup-counterfactual.sh"


def _bloques(salida: str) -> dict:
    out = {}
    for p in re.split(r"^### ", salida, flags=re.M):
        for k in ("A", "B", "C"):
            if p.startswith("RUN " + k):
                out[k] = p
    return out


def _correr(tmp_path: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(ARTIFACT), str(tmp_path / "p")],
        capture_output=True, text=True, timeout=120, check=False,
    )


def test_counterfactual_runs_from_an_arbitrary_cwd(tmp_path: Path) -> None:
    """Falsification probe: resuelve su propio repo, nunca el cwd del llamador."""
    target = tmp_path / "proyecto"
    r = subprocess.run(
        ["bash", str(ARTIFACT), str(target)],
        cwd=tmp_path, capture_output=True, text=True,
        env=os.environ.copy(), timeout=120, check=False,
    )
    assert r.returncode == 0, r.stderr
    b = _bloques(r.stdout)
    assert set(b) == {"A", "B", "C"}, "faltan corridas: %s\n%s" % (sorted(b), r.stdout)
    assert target.exists() and REPO_ROOT not in target.parents
    # El contrafactico no puede haber tocado el arbol del repo.
    assert "IDENTICO" in r.stdout, r.stdout


def test_run_a_deja_intacta_la_sesion_viva(tmp_path: Path) -> None:
    r = _correr(tmp_path)
    assert r.returncode == 0, r.stderr
    a = _bloques(r.stdout)["A"]
    assert "session dir  : EXISTE" in a, a
    assert "contenido    : INTACTO en su lugar" in a, a
    assert "archivado    : NO" in a, a
    assert 'registrada   : ["fake-session-abc123"]' in a, (
        "se deregistro una sesion viva\n" + a
    )


def test_run_b_archiva_y_mergea_una_sola_vez(tmp_path: Path) -> None:
    r = _correr(tmp_path)
    assert r.returncode == 0, r.stderr
    bl = _bloques(r.stdout)["B"]
    assert bl.count("archivado    : SI") == 2, bl
    assert "DESTRUIDO" not in bl, "ADR-119 manda archive-first, no borrado\n" + bl
    assert bl.count("contenido    : INTACTO en el archivo (nada se destruyo)") == 2, bl
    # Dos disparos, las mismas 2 lineas: el merge es incremental por offset.
    assert bl.count("merge global : SI (2 lineas)") == 2, (
        "el merge duplico filas entre disparos\n" + bl
    )


def test_run_c_reproduce_el_danio(tmp_path: Path) -> None:
    """Si el contrafactico NO reproduce, el modelo del defecto es falso.

    Es la direccion que le faltaba a este test: con la identidad resuelta y el
    borrado del paso 1 reintroducido, la misma sesion que RUN A prueba viva
    queda destruida.
    """
    r = _correr(tmp_path)
    assert r.returncode == 0, r.stderr
    c = _bloques(r.stdout)["C"]
    assert "session dir  : BORRADO" in c, c
    assert "contenido    : DESTRUIDO" in c, (
        "el contrafactico no reprodujo el danio: el modelo del defecto no se "
        "sostiene\n" + c
    )
    assert "archivado    : NO" in c, "se borro sin archivar, que es el danio\n" + c

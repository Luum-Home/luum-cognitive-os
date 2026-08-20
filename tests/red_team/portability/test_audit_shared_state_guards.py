# SCOPE: os-only
"""Portability proof for scripts/audit_shared_state_guards.py."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "scripts/audit_shared_state_guards.py"


def test_censo_corre_desde_un_cwd_arbitrario(tmp_path: Path) -> None:
    """Sonda de falsación: el censo no puede depender del cwd del repo del SO.

    Resuelve sus rutas desde ``__file__``, así que corrido desde cualquier lado
    tiene que dar el mismo JSON. Si algún día alguien mete un ``Path('hooks')``
    relativo, esta prueba lo agarra: desde tmp_path no hay ningún ``hooks/``.
    """
    env = os.environ.copy()
    env.update({"COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
                "CLAUDE_PROJECT_DIR": str(tmp_path)})
    res = subprocess.run(["python3", str(ARTIFACT), "--json"], text=True,
                         capture_output=True, cwd=tmp_path, env=env,
                         timeout=120, check=False)
    assert res.returncode in (0, 1), res.stderr
    data = json.loads(res.stdout)
    assert data["total_shared_state_blockers"] > 0, (
        "el censo no encontró ningún guard: leyó un árbol vacío, o sea que "
        "resolvió sus rutas contra el cwd y no contra su propio __file__"
    )
    assert data["attributable"] + data["not_attributable"] == \
        data["total_shared_state_blockers"]


def test_las_dos_poblaciones_son_distintas_a_proposito(tmp_path: Path) -> None:
    """Atribución y escape se miden sobre poblaciones distintas, y debe notarse.

    Si alguien las colapsa en una sola, este número deja de diferir y el censo
    empieza a mentir sobre qué mide cada mitad.
    """
    res = subprocess.run(["python3", str(ARTIFACT), "--json"], text=True,
                         capture_output=True, cwd=REPO_ROOT, timeout=120,
                         check=False)
    data = json.loads(res.stdout)
    assert data["escape_census"]["blocking_hooks_with_bypass"] > \
        data["total_shared_state_blockers"], (
        "la población de escape debería ser más amplia que la de estado "
        "compartido: incluye guards que atribuyen bien y aun así no dan salida"
    )

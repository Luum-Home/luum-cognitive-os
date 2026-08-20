# SCOPE: os-only
"""Proof pareado de portabilidad + falsacion para scripts/audit_hook_registration.py.

Se fijan dos cosas.

PORTABILIDAD
    El artefacto resuelve su propia raiz desde ``__file__`` y no desde el cwd
    del proceso, y acepta un arbol ajeno por ``--project-dir``. Un auditor
    anclado en ``Path.cwd()`` pasaria desapercibido en el repo de origen y
    auditaria el repositorio equivocado en el checkout de un consumidor.

FALSACION — la regresion para la que se escribio este gate
    Un hook declarado en ``cognitive-os.yaml`` no llega a Claude Code por estar
    ahi: el driver ``scripts/_lib/settings-driver-claude-code.sh`` tiene su
    registro HARDCODEADO y no lee el yaml. El caso vivo que motivo el gate,
    medido el 2026-08-19, es ``hooks/publication-safety.sh``: declarado con
    ``scope: both`` y sin opt-out, ausente de las superficies decisorias, cero
    disparos.

    Pero un gate que marque a TODO hook ausente de alguna superficie es inutil:
    hay omisiones legitimas declaradas por al menos seis mecanismos distintos, y
    cientos de rojos garantizan que alguien lo apague. Asi que la falsacion
    tiene dos mitades, y las dos importan:

      - un hook solo-en-el-yaml, sin declaracion y sin evidencia de haber
        corrido, DEBE aparecer como huerfano;
      - el mismo hook, con su ausencia DECLARADA, NO debe aparecer.

    Sin la segunda mitad, un gate que marca todo pasa la primera.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts" / "audit_hook_registration.py"


def _run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, cwd=str(cwd or REPO), timeout=180,
    )


def test_el_script_existe_y_declara_su_scope():
    assert SCRIPT.is_file(), f"{SCRIPT} no existe"
    cabecera = SCRIPT.read_text().splitlines()[:3]
    assert any("SCOPE:" in ln for ln in cabecera), (
        "el artefacto no declara SCOPE en las primeras tres lineas"
    )


def test_no_depende_del_cwd(tmp_path):
    """Corrido desde un directorio ajeno, tiene que auditar SU repo.

    Un script anclado en cwd auditaria tmp_path —donde no hay hooks— y saldria
    verde por vacio, que es la peor forma de pasar: parece que no hay problemas.
    """
    desde_repo = _run(cwd=REPO)
    desde_afuera = _run(cwd=tmp_path)
    assert desde_repo.returncode == desde_afuera.returncode, (
        "el veredicto cambia segun desde donde se lo corra: esta anclado al cwd\n"
        f"desde el repo: {desde_repo.returncode} / desde afuera: {desde_afuera.returncode}"
    )
    assert "publication-safety" in (desde_afuera.stdout + desde_afuera.stderr), (
        "corrido desde afuera no encontro el huerfano conocido: audito otro arbol"
    )


def test_el_huerfano_conocido_aparece():
    """La mitad que prueba que el gate ve algo."""
    r = _run(cwd=REPO)
    salida = r.stdout + r.stderr
    assert "publication-safety" in salida, (
        "el huerfano medido el 2026-08-19 no aparece: el gate dejo de mirar "
        "alguna de las superficies decisorias, o el hook se arreglo y este "
        "proof necesita un caso nuevo.\n" + salida[-1500:]
    )
    assert r.returncode != 0, "encontro el huerfano y aun asi salio 0"


def test_una_omision_declarada_no_es_un_huerfano():
    """La mitad que impide el gate que marca todo.

    Se busca en la salida un hook que el propio gate reconozca como omision
    declarada. Si no hay ninguno, el gate no distingue las dos cosas y el
    hallazgo de arriba no significa nada.
    """
    r = _run(cwd=REPO)
    salida = r.stdout + r.stderr
    assert "opt-out" in salida or "default_projection" in salida, (
        "la salida no menciona ninguna omision declarada: el gate no distingue "
        "un huerfano de una ausencia legitima, y con 192 scripts eso son "
        "cientos de falsos rojos.\n" + salida[-1500:]
    )
    # Y la distincion tiene que ser efectiva, no decorativa: los declarados no
    # pueden estar en el bloque que hace fallar.
    if "FAIL" in salida:
        bloque_fail = salida.split("FAIL", 1)[1]
        assert "opt-out" not in bloque_fail.split("fix:")[0], (
            "un hook con omision declarada entro al bloque bloqueante"
        )


def test_el_json_es_consumible():
    """Un auditor que solo imprime prosa no se puede encadenar."""
    r = _run("--json", cwd=REPO)
    import json
    try:
        datos = json.loads(r.stdout)
    except json.JSONDecodeError as e:  # pragma: no cover
        raise AssertionError(f"--json no emitio JSON valido: {e}\n{r.stdout[:400]}")
    assert isinstance(datos, dict) and datos, "--json emitio un objeto vacio"

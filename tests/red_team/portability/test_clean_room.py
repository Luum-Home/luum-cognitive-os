# SCOPE: os-only
"""Proof pareado de portabilidad para scripts/clean_room.py.

Que custodia
------------
El clean room existe porque este repo se audita con sus propios instrumentos y eso
es circular. Su promesa concreta no es "los hooks no disparan" --los hooks disparan
sobre las tool-calls del agente, no sobre un subproceso-- sino tres cosas medibles:

  1. el arbol esta en un estado CONOCIDO, sin trabajo sin commitear contaminando
  2. `.cognitive-os/` no es el de la sesion viva
  3. la raiz es OTRA, asi que un instrumento anclado al cwd falla ruidosamente aca
     en vez de auditar el arbol equivocado en silencio

El modo de falla que importa
----------------------------
Un clean room que monta mal --clon vacio, checkout fallido, venv ausente-- corre el
comando igual y devuelve un veredicto sobre la nada. Y un veredicto sobre la nada se
lee identico a un veredicto limpio. Por eso el montaje falla con un codigo PROPIO
(2) que nunca se confunde con el del comando, y por eso la sonda de abajo verifica
que efectivamente DISCRIMINA entre el arbol sucio y HEAD.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts" / "clean_room.py"
MONTAJE_FALLIDO = 2


def _correr(*args: str, cwd: Path | None = None, timeout: int = 900):
    env = dict(os.environ)
    # Heredadas, convierten cualquier guard en uno que aprueba todo.
    for v in ("COS_ALLOW_PROTECTED_CONFIG_WRITE", "COS_BYPASS"):
        env.pop(v, None)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, timeout=timeout,
        cwd=str(cwd or REPO), env=env, check=False,
    )


def test_declara_scope():
    cabecera = SCRIPT.read_text().splitlines()[:3]
    assert any("SCOPE:" in ln for ln in cabecera), "no declara SCOPE en las primeras 3 lineas"


def test_monta_un_arbol_real_y_no_uno_vacio():
    """Control anti-vacio. Un clon vacio corre cualquier cosa y no prueba nada."""
    r = _correr("--run", "git ls-files | wc -l", "--quiet")
    assert r.returncode == 0, f"no monto: {r.stderr[-500:]}"
    n = int(r.stdout.strip().splitlines()[-1])
    assert n > 100, (
        f"el clean room monto un arbol de {n} archivos: cualquier medicion hecha ahi "
        "seria un veredicto sobre la nada"
    )


def test_el_arbol_del_clean_room_esta_limpio():
    """LA PROMESA CENTRAL: estado conocido, sin trabajo sin commitear.

    Es lo que habilita el veredicto POR DIFERENCIA -- "esto ya fallaba en HEAD" vs
    "esto lo rompi yo" -- que fue como se separaron los 31 fallos del 2026-08-20 en
    sus causas reales.
    """
    r = _correr("--run", "git status --porcelain | wc -l", "--quiet")
    assert r.returncode == 0, f"no monto: {r.stderr[-500:]}"
    sucios = int(r.stdout.strip().splitlines()[-1])
    assert sucios == 0, (
        f"el clean room tiene {sucios} archivos sucios: no es un estado conocido y "
        "la diferencia contra el arbol vivo no significa nada"
    )


def test_discrimina_del_arbol_vivo(tmp_path: Path):
    """LA FALSACION. Si da lo mismo que el arbol vivo, no aisla nada.

    Se siembra un archivo sin trackear en el repo REAL y se exige que el clean room
    NO lo vea. Una sonda que diera el mismo resultado en las dos ramas estaria rota
    y este archivo entero seria decorativo.
    """
    testigo = REPO / f".clean-room-testigo-{os.getpid()}.tmp"
    testigo.write_text("sembrado por el proof de clean_room\n", encoding="utf-8")
    try:
        assert testigo.is_file(), "no se pudo sembrar el testigo"
        r = _correr("--run", f"ls {testigo.name} 2>/dev/null | wc -l", "--quiet")
        assert r.returncode == 0, f"no monto: {r.stderr[-500:]}"
        visto = int(r.stdout.strip().splitlines()[-1])
        assert visto == 0, (
            "el clean room VE un archivo que solo existe en el arbol vivo: no esta "
            "aislado y su veredicto arrastra la contaminacion que existe para evitar"
        )
    finally:
        testigo.unlink(missing_ok=True)


def test_el_fallo_de_montaje_no_se_confunde_con_el_veredicto():
    """Un ref inexistente tiene que dar el codigo propio de montaje, no el del comando.

    Sin esto, "el clean room no arranco" y "el comando fallo" salen iguales, y se
    reportaria como hallazgo lo que fue un problema de herramienta.
    """
    r = _correr("--at", "no-existe-esta-ref-jamas", "--run", "true", "--quiet")
    assert r.returncode == MONTAJE_FALLIDO, (
        f"un checkout imposible devolvio {r.returncode} en vez de {MONTAJE_FALLIDO}: "
        "un fallo de montaje se puede leer como veredicto del comando"
    )


def test_el_comando_conserva_su_propio_exit_code():
    """Control simetrico del anterior: si el comando falla, ese codigo tiene que llegar."""
    assert _correr("--run", "true", "--quiet").returncode == 0
    r = _correr("--run", "exit 7", "--quiet")
    assert r.returncode == 7, (
        f"el exit code del comando se perdio: llego {r.returncode} y no 7"
    )


def test_las_variables_de_raiz_apuntan_al_clon():
    """Si apuntan al repo real, la contaminacion vuelve por la puerta de atras.

    Un instrumento que resuelve su raiz por CLAUDE_PROJECT_DIR auditaria el arbol
    vivo mientras cree estar en el clean room -- y saldria limpio, que es la peor
    forma de fallar.
    """
    r = _correr("--run", 'echo "$CLAUDE_PROJECT_DIR|$COGNITIVE_OS_PROJECT_DIR|$COS_METRICS_DIR"',
                "--quiet")
    assert r.returncode == 0, f"no monto: {r.stderr[-500:]}"
    linea = r.stdout.strip().splitlines()[-1]
    for valor in linea.split("|"):
        assert valor, f"una variable de raiz quedo vacia: {linea!r}"
        assert str(REPO) not in valor or "cos-clean-room-" in valor, (
            f"una variable de raiz apunta al repo REAL ({valor!r}): la medicion se "
            "vuelve a contaminar sin que nadie lo note"
        )


def test_no_depende_del_cwd(tmp_path: Path):
    """Corrido desde un directorio ajeno tiene que clonar SU repo, no el cwd."""
    desde_repo = _correr("--run", "git ls-files | wc -l", "--quiet")
    desde_afuera = _correr("--run", "git ls-files | wc -l", "--quiet", cwd=tmp_path)
    assert desde_repo.returncode == desde_afuera.returncode == 0, (
        f"repo={desde_repo.returncode} afuera={desde_afuera.returncode}\n{desde_afuera.stderr[-400:]}"
    )
    assert desde_repo.stdout.strip().splitlines()[-1] == desde_afuera.stdout.strip().splitlines()[-1], (
        "clona un arbol distinto segun desde donde se lo invoque: esta anclado al cwd"
    )

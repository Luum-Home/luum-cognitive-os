"""El bypass de research-compliance-guard no puede auto-concederse.

Por que existe
--------------
El 2026-08-19 este guard adopto la lectura del token desde el TEXTO del comando
—correcta, porque un prefijo `VAR=1 <comando>` no llega a los hooks— pero la
escribio como coincidencia en cualquier parte:

    [[ "$CMD" == *"COS_ALLOW_RESEARCH_COMPLIANCE_BYPASS=1"* ]]

Con eso, escribir *sobre* la variable aprobaba la operacion:

    echo 'usar COS_ALLOW_RESEARCH_COMPLIANCE_BYPASS=1' >> nota.md && git commit

Es palabra por palabra el primer error que ya habia pagado
hooks/protected-config-write-guard.sh (ver su cabecera, lineas 40-46), y el
comentario del propio guard decia "esto la adopta" habiendo adoptado la mitad:
la lectura sin el ancla que la vuelve segura.

Este test afirma el EFECTO de la funcion de aprobacion, no su forma: se puede
reescribir el ancla entera y el test sigue valiendo mientras la auto-concesion
quede rechazada y las vias legitimas sigan abiertas.

Los dos primeros casos son el hallazgo. Los otros tres son los controles sin
los cuales "rechaza la auto-concesion" tambien lo cumple un guard que rechaza
todo — que seria dejar al lector sin ninguna salida, peor que la mentira.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
HOOK = Path(os.environ.get(
    "COS_RESEARCH_GUARD_HOOK", REPO / "hooks" / "research-compliance-guard.sh"
))
VAR = "COS_ALLOW_RESEARCH_COMPLIANCE_BYPASS"


def _funcion_de_aprobacion() -> str:
    src = HOOK.read_text()
    try:
        inicio = src.index("_research_bypass_granted()")
        fin = src.index("if _RESEARCH_BYPASS_SOURCE=")
    except ValueError:  # pragma: no cover - solo contra la version vieja
        pytest.fail(
            f"{HOOK} no define _research_bypass_granted(): la aprobacion se "
            "decide de otra forma y este test no puede afirmar que sea segura."
        )
    return src[inicio:fin]


def _concede(cmd: str, *, entorno: dict[str, str] | None = None) -> bool:
    # El hook sourcea el resolvedor compartido antes de definir la funcion; la
    # sonda tiene que hacer lo mismo o estaria midiendo la sonda. Se descubrio
    # asi: sin este source, la via COS_BYPASS daba rojo y el hook estaba bien.
    resolver = REPO / "hooks" / "_lib" / "bypass-resolver.sh"
    script = (
        'CMD="$1"\n'
        + (f'source "{resolver}"\n' if resolver.is_file() else "")
        + _funcion_de_aprobacion()
        + '\nif _research_bypass_granted >/dev/null; then echo CONCEDE; '
          'else echo bloquea; fi\n'
    )
    with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as f:
        f.write(script)
        p = f.name
    try:
        env = dict(os.environ)
        env.pop(VAR, None)
        env.pop("COS_BYPASS", None)
        env.update(entorno or {})
        r = subprocess.run(
            ["/bin/bash", p, cmd], capture_output=True, text=True, env=env, timeout=30
        )
        assert r.returncode == 0, f"la sonda fallo: {r.stderr}"
        return r.stdout.strip() == "CONCEDE"
    finally:
        os.unlink(p)


# --- el hallazgo -----------------------------------------------------------

@pytest.mark.parametrize("cmd", [
    f"echo 'usar {VAR}=1' >> nota.md && git commit -m x",
    f"git commit -m 'documenta {VAR}=1'",
    f"cat docs/{VAR}=1.md && git push",
])
def test_mencionar_la_variable_no_concede(cmd):
    """Escribir SOBRE la variable no es activarla.

    Tres formas distintas de mencionarla sin asignarla en posicion de prefijo.
    La primera es la que se reprodujo; las otras dos existen porque un ancla
    escrita a medias puede tapar una y no las otras.
    """
    assert not _concede(cmd), f"se auto-concedio con: {cmd}"


# --- los controles ---------------------------------------------------------

@pytest.mark.parametrize("cmd", [
    f"{VAR}=1 git commit -m x",
    f"cd /tmp && {VAR}=1 git commit -m x",
    f"foo; {VAR}=1 git commit -m x",
])
def test_el_prefijo_en_posicion_valida_si_concede(cmd):
    """Sin esto, un guard que rechaza todo pasa el test de arriba."""
    assert _concede(cmd), f"no concedio con un prefijo valido: {cmd}"


def test_sin_token_no_concede():
    assert not _concede("git commit -m x")


def test_la_variable_exportada_concede():
    """Via 1 de 4: `export VAR=1` antes de lanzar el arnes. Esa forma SI llega
    a los hooks — el arnes hereda el entorno del shell que lo lanzo."""
    assert _concede("git commit -m x", entorno={VAR: "1"})


def test_la_clave_en_cos_bypass_concede():
    """Via 2 de 4: el resolvedor compartido de ADR-241, que ademas lee
    .cognitive-os/runtime/bypass.env en CADA invocacion — la unica escribible
    a mitad de sesion sin tocar settings.json."""
    src = HOOK.read_text()
    if "bypass-resolver" not in src:
        pytest.skip("este hook no sourcea el resolvedor compartido")
    assert _concede("git commit -m x", entorno={"COS_BYPASS": "research_compliance"})


def test_el_resolvedor_conoce_la_clave():
    """El alias tiene que estar registrado en el resolvedor, no solo usado
    aca: si no, la clave funciona por la lista y no por la variable historica.
    """
    resolver = (REPO / "hooks" / "_lib" / "bypass-resolver.sh").read_text()
    assert "research_compliance)" in resolver, (
        "hooks/_lib/bypass-resolver.sh no registra la clave research_compliance"
    )
    assert VAR in resolver, (
        f"el resolvedor registra la clave pero no mapea {VAR}"
    )

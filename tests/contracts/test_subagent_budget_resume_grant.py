# SCOPE: both
"""Reanudar a un sub-agente cortado no le devuelve presupuesto.

Qué se mide y por qué
---------------------
El contador de `hooks/subagent-budget-enforcer.sh` vive en

    .cognitive-os/sessions/<session_id>/subagent-tool-calls-<agent_id>

y es **acumulativo por invocación de sub-agente**. Ninguna reanudación lo
resetea: el `agent_id` sobrevive al mensaje que reanuda, así que el agente
cortado en 51/50 vuelve con presupuesto **cero** y su primer llamado vuelve a
chocar. La instrucción que le damos —"pará y reportá parcial, no actives el
bypass"— produce entonces trabajo irrecuperable, y el bypass ilimitado queda
como única salida: el incentivo exactamente al revés del que queremos.

Medido el 2026-08-20 sobre la telemetría del propio hook::

    grep '"action": "block"' .cognitive-os/metrics/subagent-budget-enforcer.jsonl \\
      | python3 -c 'import sys,json,collections;
    c=collections.Counter(json.loads(l)["agent_id"] for l in sys.stdin);
    print(len(c), sum(1 for v in c.values() if v>1))'
    # 93 agentes bloqueados, 58 de ellos bloqueados MÁS DE UNA VEZ

Y el caso puntual que originó el encargo::

    grep '"agent_id": "a11a796711b2e292b"' .cognitive-os/metrics/subagent-budget-enforcer.jsonl
    # ... "action": "block", "tool_calls": 51, "timestamp": "2026-08-20T16:58:17Z"
    # ... "action": "block", "tool_calls": 52, "timestamp": "2026-08-20T17:00:27Z"

Estado de los marcadores
------------------------
`hooks/**` está en `protected_globs` de
`manifests/protected-config-write-policy.yaml` con `default_mode: block`,
verificado corriendo `hooks/protected-config-write-guard.sh` (exit 2 sobre
`hooks/`, exit 0 sobre `tests/`). El parche existe y está probado sobre una
copia, pero **no se aplicó**: es revisión humana pendiente, no un bypass a
activar.

Los CUATRO tests que discriminan llevaban ``xfail(strict=True)`` mientras el parche
esperaba revision humana. Se aplico el 2026-08-20 y los marcadores se sacaron: el
propio ``strict`` los delato pasando. La nota de abajo describe aquel estado, la
misma convención que `tests/contracts/test_subagent_budget_enforcer_modes.py`:
fallan hoy a propósito y se vuelven falla dura en cuanto el parche entre, que
es el trinquete que obliga a sacar el marcador junto con el parche en lugar de
dejar un test verde que no prueba nada.

«Discriminan» es literal y se puede verificar. El gate lee el hook bajo prueba
de ``COS_TEST_BUDGET_HOOK``, así que se corre contra el candidato sin tocar la
superficie protegida::

    .venv/bin/python3 -m pytest tests/contracts/test_subagent_budget_resume_grant.py -q
    # 5 passed, 4 xfailed          <- contra el repo

    COS_TEST_BUDGET_HOOK=<copia parcheada> \
      .venv/bin/python3 -m pytest tests/contracts/test_subagent_budget_resume_grant.py -q
    # 4 failed [XPASS(strict)], 5 passed   <- el trinquete disparando

Los tests SIN marcador se dividen en dos clases y conviene no confundirlas:

* **Verdes con sentido, hoy y después del parche.**
  `test_reanudar_no_resetea_el_contador` (el hecho que el parche no cambia:
  concede, no resetea), `test_el_bypass_de_hoy_es_de_alcance_proyecto` (un
  agujero que el parche NO cierra) y `test_por_debajo_del_presupuesto_no_bloquea`
  (control negativo).
* **Vacuos hasta que entre el parche.** `test_concesion_sin_motivo_no_vale` y
  `test_la_concesion_es_por_agente` afirman "bloquea", y el hook de hoy bloquea
  igual porque no sabe leer concesiones. Llevaban ``xfail(strict=True)`` y el
  propio trinquete los delató con un XPASS contra el repo sin parchear: una
  sonda que da el mismo resultado en las dos ramas del contrafáctico está rota.
  Se dejan sin marcador y anotados, porque su poder discriminante aparece
  recién después del parche y siempre apareados con
  `test_concesion_acotada_con_motivo_destraba`, que es el que sí distingue.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = Path(
    os.environ.get(
        # Permite correr ESTE MISMO gate contra el parche candidato sin
        # tocar la superficie protegida. Sin la variable, mide el repo.
        "COS_TEST_BUDGET_HOOK",
        REPO_ROOT / "hooks" / "subagent-budget-enforcer.sh",
    )
)

PENDING = (
    "concesión acotada de reanudación no aplicada a "
    "hooks/subagent-budget-enforcer.sh (superficie protegida: revisión humana "
    "pendiente). Diseño y parche exacto en "
    "docs/06-Daily/reports/presupuesto-de-agente-irrecuperable-2026-08-20.md"
)

BUDGET = 50


def _payload(agent_id: str = "AG1") -> dict:
    return {
        "session_id": "S1",
        "agent_id": agent_id,
        "session_kind": "subagent",
        "tool_name": "Read",
        "tool_input": {},
    }


def _counter(proj: Path, agent_id: str) -> Path:
    return proj / ".cognitive-os" / "sessions" / "S1" / f"subagent-tool-calls-{agent_id}"


def _fire(
    proj: Path,
    start_count: int,
    agent_id: str = "AG1",
    env_extra: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Dispara el hook una vez con el contador arrancando en ``start_count``."""
    counter = _counter(proj, agent_id)
    counter.parent.mkdir(parents=True, exist_ok=True)
    (proj / ".cognitive-os" / "metrics").mkdir(parents=True, exist_ok=True)
    counter.write_text(str(start_count))

    env = os.environ.copy()
    # Un bypass heredado del entorno del operador convertiría cualquier rojo en
    # verde sin tocar el hook: se limpian a propósito.
    for leaked in (
        "COS_BYPASS",
        "COS_ALLOW_SUBAGENT_BUDGET_BYPASS",
        "COS_SUBAGENT_BUDGET_BYPASS_REASON",
        "COS_ALLOW_PROTECTED_CONFIG_WRITE",
        "DISABLE_HOOK_SUBAGENT_BUDGET_ENFORCER",
    ):
        env.pop(leaked, None)
    env.update(
        {
            "COGNITIVE_OS_PROJECT_DIR": str(proj),
            "COS_METRICS_DIR": str(proj / ".cognitive-os" / "metrics"),
            "COS_SUBAGENT_TOOL_CALL_BUDGET": str(BUDGET),
        }
    )
    env.update(env_extra or {})
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(_payload(agent_id)),
        capture_output=True,
        text=True,
        env=env,
    )


def _grant(proj: Path, agent_id: str, amount: int, reason: str | None) -> None:
    d = proj / ".cognitive-os" / "runtime" / "budget-grants"
    d.mkdir(parents=True, exist_ok=True)
    body = f"GRANT={amount}\n"
    if reason is not None:
        body += f"REASON={reason}\n"
    (d / agent_id).write_text(body)


# --------------------------------------------------------------------------
# Verdes hoy y después del parche: el hecho y el agujero.
# --------------------------------------------------------------------------


def test_reanudar_no_resetea_el_contador(tmp_path: Path) -> None:
    """El hallazgo central del encargo.

    El contador está en disco y sobrevive a cualquier mensaje de reanudación.
    Un agente cortado en 51/50 no vuelve con "poco" presupuesto: vuelve con
    CERO, y su primer llamado al reanudar bloquea de nuevo. Este test no
    cambia con el parche — el parche no resetea, concede.
    """
    result = _fire(tmp_path, start_count=BUDGET + 1)
    assert result.returncode == 2, (
        "el primer llamado tras reanudar debería bloquear: el contador es "
        f"acumulativo y arranca en {BUDGET + 1}. stderr={result.stderr!r}"
    )
    assert _counter(tmp_path, "AG1").exists(), (
        "el contador tiene que seguir en disco: es la persistencia que hace "
        "que reanudar no devuelva presupuesto"
    )


def test_el_bypass_de_hoy_es_de_alcance_proyecto(tmp_path: Path) -> None:
    """Hallazgo adversarial, severidad ALTA, que el parche NO cierra.

    `.cognitive-os/runtime/bypass.env` lo resuelve
    `hooks/_lib/bypass-resolver.sh::_cos_bypass_runtime_file`, que compone la
    ruta con el project dir y **sin ninguna componente de agente**. O sea: el
    bypass que escribe un sub-agente para destrabarse destraba a TODOS los
    sub-agentes concurrentes, y el motivo auditado que queda pegado a esas
    llamadas es el de OTRO encargo.

    Visto en la telemetría real del 2026-08-20: el agente `a2e61af8bbb75b87a`
    corrió 20 llamadas seguidas con `action=allow` y un `reason` de bypass
    ajeno a lo que estaba haciendo, del llamado 46 al 65.
    """
    runtime = tmp_path / ".cognitive-os" / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    (runtime / "bypass.env").write_text(
        "COS_BYPASS=subagent_budget\n"
        "COS_SUBAGENT_BUDGET_BYPASS_REASON=lo escribio OTRO agente\n"
    )
    result = _fire(tmp_path, start_count=BUDGET + 1, agent_id="AG2")
    assert result.returncode == 0, (
        "si esto bloquea, el bypass dejó de ser de alcance proyecto y el "
        "agujero se cerró: actualizá este test en vez de borrarlo"
    )


def test_por_debajo_del_presupuesto_no_bloquea(tmp_path: Path) -> None:
    """Control negativo: sin esto, un hook que bloquea SIEMPRE pasaría todos
    los tests de bloqueo de arriba y el gate no probaría nada."""
    result = _fire(tmp_path, start_count=10)
    assert result.returncode == 0, result.stderr


# --------------------------------------------------------------------------
# Dependen del parche. Trinquete: se vuelven falla dura cuando entre.
# --------------------------------------------------------------------------


def test_un_llamado_bloqueado_no_consume_presupuesto(tmp_path: Path) -> None:
    """Hoy el contador se incrementa ANTES de decidir el bloqueo, así que cada
    reintento de un agente cortado lo hunde más: medido, el agente
    `ae7fd3dbd1dfcbe71` acumuló 25 bloqueos y llegó a 75 llamadas contadas.

    Con el cobro apagado, el contador queda estacionado y una concesión de N
    da exactamente N llamados usables, no N menos lo gastado chocando.
    """
    result = _fire(tmp_path, start_count=BUDGET + 1)
    assert result.returncode == 2
    assert _counter(tmp_path, "AG1").read_text().strip() == str(BUDGET + 1), (
        "un llamado bloqueado no puede cobrar presupuesto"
    )


def test_concesion_acotada_con_motivo_destraba(tmp_path: Path) -> None:
    """La salida explícita y trazable: el orquestador concede N llamadas a UN
    agente, con motivo, y queda auditado."""
    _grant(tmp_path, "AG1", 20, "cerrar el informe y aplicar los parches ya disenados")
    result = _fire(tmp_path, start_count=BUDGET + 1)
    assert result.returncode == 0, result.stderr

    ledger = tmp_path / ".cognitive-os" / "metrics" / "subagent-budget-enforcer.jsonl"
    rows = [json.loads(line) for line in ledger.read_text().splitlines() if line.strip()]
    grants = [r for r in rows if r.get("action") == "grant"]
    assert grants, "una concesión sin constancia es un agujero, no una decisión"
    assert "cerrar el informe" in grants[-1]["reason"]


def test_concesion_sin_motivo_no_vale(tmp_path: Path) -> None:
    """Sin motivo la concesión no existe: es la diferencia entre una decisión
    con dueño y un `disable` puesto para apagar el rojo.

    **Sin marcador a propósito.** Este test es VACUO contra el hook de hoy: el
    hook actual no sabe leer concesiones, así que bloquea igual y el test pasa
    sin haber medido nada. Llevaba `xfail(strict=True)` y el propio trinquete
    lo delató con un XPASS — una sonda que da el mismo resultado en las dos
    ramas del contrafáctico está rota. Su poder discriminante existe recién
    después del parche, y solo apareado con
    `test_concesion_acotada_con_motivo_destraba`, que es el que sí distingue.
    """
    _grant(tmp_path, "AG1", 20, None)
    result = _fire(tmp_path, start_count=BUDGET + 1)
    assert result.returncode == 2, result.stderr


def test_la_concesion_se_recorta_al_techo(tmp_path: Path) -> None:
    """Techo duro: una concesión jamás puede más que duplicar el presupuesto
    base. Sin esto la concesión sería el bypass ilimitado con otro nombre —
    exactamente el verde barato que el encargo pide evitar."""
    _grant(tmp_path / "a", "AG1", 9999, "intento de barra libre")
    ok = _fire(tmp_path / "a", start_count=BUDGET * 2 - 1)
    assert ok.returncode == 0, "dentro del techo tiene que dejar pasar"

    _grant(tmp_path / "b", "AG1", 9999, "intento de barra libre")
    over = _fire(tmp_path / "b", start_count=BUDGET * 2)
    assert over.returncode == 2, (
        f"pasado el techo ({BUDGET} base + {BUDGET} de techo) tiene que bloquear "
        "por más que la concesión pida 9999"
    )


def test_la_concesion_es_por_agente(tmp_path: Path) -> None:
    """La diferencia con el bypass de hoy: la concesión de AG1 no destraba a
    AG2. Ver `test_el_bypass_de_hoy_es_de_alcance_proyecto` para el contraste.

    **Sin marcador a propósito**, por el mismo motivo que
    `test_concesion_sin_motivo_no_vale`: contra el hook de hoy es vacuo.
    """
    _grant(tmp_path, "AG1", 20, "solo para AG1")
    result = _fire(tmp_path, start_count=BUDGET + 1, agent_id="AG2")
    assert result.returncode == 2, (
        "AG2 montó la concesión de AG1: la concesión volvió a ser global"
    )


def test_el_mensaje_de_bloqueo_pide_el_informe_primero(tmp_path: Path) -> None:
    """La instrucción que de facto funcionó hoy —escribir el informe y los
    parches exactos ANTES de gastar presupuesto implementando— viaja por el
    mensaje de bloqueo y no por el preámbulo inyectado.

    El motivo es de presupuesto de canal: `templates/agent-preamble.md` y
    `templates/agent-mandatory-rules.md` suman 8.612 de los 10.000 caracteres
    del injector y quedan 188 de margen sobre la reserva del sidecar
    (`tests/contracts/test_canal_al_subagente_tiene_margen.py`). El stderr del
    bloqueo llega justo cuando hace falta y no cuesta un solo carácter del
    canal.
    """
    result = _fire(tmp_path, start_count=BUDGET + 1)
    assert result.returncode == 2
    assert "ESCRIBI PRIMERO el informe" in result.stderr, (
        "el mensaje de bloqueo no lleva la instrucción de informe-primero"
    )
    assert "budget-grants" in result.stderr, (
        "el mensaje de bloqueo no dice cómo pedir la concesión acotada"
    )

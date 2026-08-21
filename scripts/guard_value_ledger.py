#!/usr/bin/env python3
# SCOPE: os-only
# SPDX-License-Identifier: MIT
"""Cuanto valor entrega la capa de guards, medido: proteccion real vs friccion.

La pregunta que contesta
------------------------
El operador mantiene esta capa solo, y paga cada corrida con su suscripcion. La
pregunta no es si los guards funcionan --funcionan-- sino si lo que evitan vale
mas que lo que cuestan. Este script no opina: cuenta.

Las tres categorias, y por que la tercera es la que decide
---------------------------------------------------------
1. BLOQUEO QUE QUEDO EN PIE   -- el guard bloqueo y nadie lo revirtio. Es el unico
                                 caso donde el guard pudo haber evitado algo.
2. BLOQUEO REVERTIDO          -- bloqueo y despues se activo un bypass. El guard
                                 costo una interrupcion y no cambio el resultado.
3. BYPASS PROFILACTICO        -- se desarmo el guard SIN que hubiera bloqueado
                                 nada. Nadie fue interrumpido porque el guard ya
                                 estaba apagado antes de opinar.

La tercera es la que decide, y es la que nadie mide. Un guard que se desarma por
costumbre --porque estorbo una vez y ahora el prefijo va en todos los comandos--
no protege de nada y sigue apareciendo en los inventarios como control activo.
Da sensacion de cobertura, que es peor que no tenerlo: nadie busca una defensa
que cree tener.

Lo que este script NO puede decir
---------------------------------
No sabe si un bloqueo que quedo en pie evito un dano REAL o si el comando era
inofensivo y el autor simplemente se fue a hacer otra cosa. La telemetria no
registra contrafacticos. Por eso la categoria 1 es un TECHO de valor, no una
medicion de valor: el valor real es menor o igual, nunca mayor.

Esa asimetria es a proposito. Si el techo ya es bajo, la conclusion se sostiene
sin necesidad de afinar. Si el techo es alto, hace falta mirar caso por caso y
este script te dice cuales mirar.

Uso
---
    .venv/bin/python3 scripts/guard_value_ledger.py            # informe
    .venv/bin/python3 scripts/guard_value_ledger.py --json     # para encadenar
    .venv/bin/python3 scripts/guard_value_ledger.py --since 1d # ventana

Exit: 0 siempre. Es un instrumento de medicion, no un gate: no hay un umbral
correcto de "friccion aceptable" y fabricar uno seria inventar el numero que el
script existe para no inventar.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
METRICS = REPO / ".cognitive-os" / "metrics"


def _rows(name: str) -> list[dict]:
    """Lee un jsonl tolerando bytes corruptos y filas rotas.

    `errors="replace"` y no `2>/dev/null`: si una fila no parsea queremos
    contarla, no perderla en silencio. "No pude leer" y "no habia" son estados
    distintos y este archivo los separa (ver `unparsed` en la salida).
    """
    p = METRICS / f"{name}.jsonl"
    out: list[dict] = []
    malas = 0
    if not p.is_file():
        return out
    with p.open(errors="replace") as fh:
        for ln in fh:
            ln = ln.strip()
            if not ln:
                continue
            try:
                d = json.loads(ln)
                if isinstance(d, dict):
                    out.append(d)
            except Exception:
                malas += 1
    if malas:
        out.append({"__unparsed__": malas})
    return out


def _ts(row: dict) -> datetime | None:
    raw = row.get("timestamp") or row.get("ts")
    if not isinstance(raw, str):
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return None


def _since(arg: str | None) -> datetime | None:
    if not arg:
        return None
    unidad, num = arg[-1], arg[:-1]
    mult = {"h": "hours", "d": "days", "m": "minutes"}.get(unidad)
    if not mult or not num.isdigit():
        raise SystemExit(f"--since invalido: {arg!r} (usar 6h, 2d, 30m)")
    return datetime.now(timezone.utc) - timedelta(**{mult: int(num)})


def cobertura(filas: list[dict]) -> dict:
    """El lapso que las filas REALMENTE cubren, no el que se pidio.

    EL DEFECTO QUE ESTO ARREGLA, medido el 2026-08-21
    -------------------------------------------------
    Este archivo publicaba `"ventana": "todo"` cuando no se le pasaba `--desde`.
    Pero los JSONL de metrica **ROTAN**: `hook-timing.jsonl` cubria
    2026-08-20T15:45 -> 2026-08-21T14:21, o sea **22,6 horas**.

    Con esa etiqueta se publico "14.268 invocaciones -> 41 bloqueos (0,29%)" como
    si fuera la historia entera del sistema, y esa cifra se cito para decidir que
    partes del SO retirar. Era un dia.

    "Sin filtro" y "toda la historia" son cosas distintas, y la diferencia entre
    las dos la decide un archivo que rota, no el argumento de linea de comandos.
    Un instrumento no puede afirmar el alcance de sus datos a partir de lo que le
    pidieron: lo tiene que LEER de los datos.

    Devuelve `horas: None` cuando no hay ninguna fila con marca de tiempo -- que es
    "no lo se", distinto de cero.
    """
    ts = [t for t in (_ts(r) for r in filas) if t is not None]
    if not ts:
        return {"filas": len(filas), "desde": None, "hasta": None, "horas": None,
                "nota": "ninguna fila trae marca de tiempo: el lapso no es determinable"}
    lo, hi = min(ts), max(ts)
    return {
        "filas": len(filas),
        "desde": lo.isoformat(),
        "hasta": hi.isoformat(),
        "horas": round((hi - lo).total_seconds() / 3600, 1),
        "filas_sin_marca": len(filas) - len(ts),
    }


def _razon_normalizada(num: int, cob_num: dict, den: int, cob_den: dict) -> dict:
    """Una razon entre dos fuentes que NO cubren el mismo lapso.

    EL DEFECTO, medido el 2026-08-21
    --------------------------------
    Se publico "el guard de config bloqueo 20 veces contra 3.765 desarmes
    profilacticos, 1:188" y esa cifra sostuvo el argumento de que el guard no
    servia. Pero el numerador sale de `hook-timing.jsonl` y el denominador de
    `protected-config-bypass.jsonl`, y los dos archivos rotan por su cuenta:
    **24,5 h contra 65,7 h**. Era una razon entre un dia y tres dias.

    Dividir dos conteos crudos de ventanas distintas no da una razon: da el
    cociente de las ventanas multiplicado por la razon real. Aca se emiten las
    dos -- la cruda, porque es la que alguien va a querer chequear, y la
    normalizada por hora, que es la unica comparable -- y nunca la cruda sola.

    Si alguna cobertura no es determinable, la razon se NIEGA en vez de
    aproximarse: "no se puede calcular" es un estado, y colapsarlo en un numero
    es como nacio este defecto.
    """
    hn, hd = cob_num.get("horas"), cob_den.get("horas")
    out = {
        "bloqueos": num,
        "bypass_profilactico": den,
        "razon_cruda": f"1:{den // num}" if num else "n/d (cero bloqueos)",
        "ventana_bloqueos_h": hn,
        "ventana_bypass_h": hd,
    }
    if not hn or not hd:
        out["razon_por_hora"] = None
        out["nota"] = ("una de las dos fuentes no tiene lapso determinable: la razon "
                       "cruda NO es comparable y no se normaliza")
        return out
    tasa_n, tasa_d = num / hn, den / hd
    out["bloqueos_por_hora"] = round(tasa_n, 2)
    out["bypass_por_hora"] = round(tasa_d, 2)
    out["razon_por_hora"] = f"1:{round(tasa_d / tasa_n)}" if tasa_n else "n/d"
    out["nota"] = ("las dos fuentes cubren lapsos distintos; la razon comparable es "
                   "la normalizada por hora, no la cruda")
    return out


def build(desde: datetime | None = None) -> dict:
    def en_ventana(r: dict) -> bool:
        if desde is None:
            return True
        t = _ts(r)
        return t is None or t >= desde

    timing = [r for r in _rows("hook-timing") if en_ventana(r)]
    sin_parsear = sum(r.get("__unparsed__", 0) for r in timing)
    timing = [r for r in timing if "__unparsed__" not in r]

    # 1. Bloqueos por hook, desde el registro maestro del wrapper.
    bloqueos: Counter[str] = Counter()
    invocaciones: Counter[str] = Counter()
    for r in timing:
        hook = str(r.get("hook") or "?")
        invocaciones[hook] += 1
        if r.get("exit_code") == 2 or str(r.get("decision") or "").lower() == "block":
            bloqueos[hook] += 1

    # 2. Bypasses declarados: el agente/operador desarmo un guard a proposito.
    activaciones = [r for r in _rows("bypass-activation") if "__unparsed__" not in r and en_ventana(r)]
    por_hook_bypass: Counter[str] = Counter(str(r.get("hook") or "?") for r in activaciones)

    # 3. Bypass profilactico del guard de config: cada fila es un comando que
    #    llego con COS_ALLOW_PROTECTED_CONFIG_WRITE=1 ya puesto.
    profilacticos = [r for r in _rows("protected-config-bypass") if "__unparsed__" not in r and en_ventana(r)]
    bloqueos_config = bloqueos.get("protected-config-write-guard", 0)

    # 4. Presupuesto de sub-agentes: accion por fila.
    presupuesto = [r for r in _rows("subagent-budget-enforcer") if "__unparsed__" not in r and en_ventana(r)]
    acciones = Counter(str(r.get("action") or "?") for r in presupuesto)
    por_agente: dict[str, int] = defaultdict(int)
    for r in presupuesto:
        if str(r.get("action")) == "block":
            por_agente[str(r.get("agent_id") or "?")] += 1
    repetidos = sum(1 for n in por_agente.values() if n > 1)

    # 5. Bloqueos de git, con su motivo.
    git = [r for r in _rows("git-op-blocks") if "__unparsed__" not in r and en_ventana(r)]
    git_por_motivo = Counter(str(r.get("reason") or "?") for r in git)

    return {
        # `filtro_pedido` es lo que se pidio. `cobertura_real` es lo que los datos
        # efectivamente abarcan, POR FUENTE, porque cada JSONL rota por su cuenta:
        # un unico numero de ventana para todas seria falso para casi todas.
        "filtro_pedido": desde.isoformat() if desde else "sin filtro",
        "cobertura_real": {
            "hook-timing": cobertura(timing),
            "bypass-activation": cobertura(activaciones),
            "protected-config-bypass": cobertura(profilacticos),
            "subagent-budget-enforcer": cobertura(presupuesto),
            "git-op-blocks": cobertura(git),
        },
        "timing_rows": len(timing),
        "timing_unparsed": sin_parsear,
        "bloqueos_por_hook": dict(bloqueos.most_common()),
        "invocaciones_por_hook": dict(invocaciones.most_common(15)),
        "bloqueos_total": sum(bloqueos.values()),
        "bypass_declarado_total": len(activaciones),
        "bypass_declarado_por_hook": dict(por_hook_bypass.most_common()),
        "config_guard": _razon_normalizada(
            bloqueos_config, cobertura(timing),
            len(profilacticos), cobertura(profilacticos),
        ),
        "presupuesto_subagente": {
            "acciones": dict(acciones),
            "agentes_bloqueados": len(por_agente),
            "agentes_bloqueados_mas_de_una_vez": repetidos,
        },
        "git_blocks": {"total": len(git), "por_motivo": dict(git_por_motivo.most_common(8))},
    }


def render(d: dict) -> str:
    L: list[str] = []
    add = L.append
    add(f"LEDGER DE VALOR DE LOS GUARDS  (ventana: {d['ventana']})")
    add("=" * 72)
    add("")
    add(f"Registro maestro: {d['timing_rows']} invocaciones de hook"
        + (f"  ({d['timing_unparsed']} filas ilegibles)" if d["timing_unparsed"] else ""))
    add(f"Bloqueos totales: {d['bloqueos_total']}")
    add("")

    if d["bloqueos_por_hook"]:
        add("BLOQUEOS POR HOOK")
        for h, n in list(d["bloqueos_por_hook"].items())[:12]:
            inv = d["invocaciones_por_hook"].get(h, 0)
            tasa = f"{100*n/inv:.1f}%" if inv else "?"
            add(f"  {n:>6}  {h:<44} de {inv} invocaciones ({tasa})")
    else:
        add("BLOQUEOS POR HOOK: ninguno en la ventana.")
        add("  OJO: cero bloqueos puede significar que nada intento algo prohibido,")
        add("  o que el registro maestro no esta capturando la decision. Verificar")
        add("  con un caso conocido antes de leer este cero como salud.")
    add("")

    cg = d["config_guard"]
    add("GUARD DE CONFIG PROTEGIDA  --  la categoria que decide")
    add(f"  bloqueos efectivos:     {cg['bloqueos']}")
    add(f"  bypass profilactico:    {cg['bypass_profilactico']}   (comandos que llegaron")
    add("                                  con el guard ya desarmado)")
    if cg["bypass_profilactico"] > max(cg["bloqueos"], 1) * 3:
        add("")
        add("  >> El guard se desarma por costumbre, no por necesidad. Un control que")
        add("     llega apagado a la mayoria de los comandos no protege de nada y sigue")
        add("     contando como activo en los inventarios: da sensacion de cobertura,")
        add("     que es peor que no tenerlo, porque nadie busca la defensa que cree tener.")
    add("")

    ps = d["presupuesto_subagente"]
    add("PRESUPUESTO DE SUB-AGENTES")
    add(f"  acciones: {ps['acciones']}")
    add(f"  agentes bloqueados: {ps['agentes_bloqueados']}")
    add(f"  bloqueados mas de una vez: {ps['agentes_bloqueados_mas_de_una_vez']}")
    if ps["agentes_bloqueados"]:
        pct = 100 * ps["agentes_bloqueados_mas_de_una_vez"] / ps["agentes_bloqueados"]
        add(f"  -> {pct:.0f}% choco mas de una vez")
    add("")

    add("BLOQUEOS DE GIT")
    add(f"  total: {d['git_blocks']['total']}")
    for motivo, n in d["git_blocks"]["por_motivo"].items():
        add(f"    {n:>5}  {motivo}")
    add("")

    add("BYPASS DECLARADO (con motivo escrito)")
    add(f"  total: {d['bypass_declarado_total']}")
    for h, n in d["bypass_declarado_por_hook"].items():
        add(f"    {n:>5}  {h}")
    add("")
    add("-" * 72)
    add("LEER CON CUIDADO: un bloqueo que quedo en pie es un TECHO de valor, no una")
    add("medicion de valor. La telemetria no registra contrafacticos: no sabemos si")
    add("evito un dano real o si el comando era inofensivo. El valor real es menor o")
    add("igual, nunca mayor. Si el techo ya es bajo, la conclusion se sostiene sola.")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--since", help="ventana: 6h, 2d, 30m")
    a = ap.parse_args()
    d = build(_since(a.since))
    print(json.dumps(d, indent=2, ensure_ascii=False) if a.json else render(d))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# SCOPE: os-only
# SPDX-License-Identifier: MIT
"""Libro mayor de primitivas: una fila por primitiva, para triage humano acotado.

Por que existe
--------------
El censo (`cos_primitive_census.py`) contesta "como esta cada FAMILIA". Esto
contesta "que hago con ESTA primitiva", que es otra pregunta: la primera se lee
en una tabla de seis filas, la segunda necesita ~650 filas y una decision por fila.

El operador lo pidio asi el 2026-08-21: recorrer categoria por categoria sin
gastar un juez por primitiva. La unica forma de que eso sea barato es que la
maquina PRE-CLASIFIQUE con evidencia y el humano lea SOLO el monton ambiguo.

Los cuatro montones
-------------------
    SIRVE     llega Y se lo vio actuar          -> no se toca
    RUIDO     llega Y su medidor VE Y no actuo  -> borrable CON evidencia
    AMBIGUA   llega Y su medidor ES CIEGO       -> hay que LEER, no borrar
    OMITIDA   no llega Y ESO YA SE DECIDIO      -> no se lee: la decision existe
    DISCREPA  dos instrumentos se contradicen   -> leer PRIMERO, es lo mas barato

`OMITIDA` no estaba en la primera version y su ausencia produjo 107 hooks marcados
RUIDO que en realidad tenian su motivo escrito en
`manifests/hook-registration-classification.yaml`. Es la misma leccion que el
2026-08-20 obligo a crear `dispatched:unmeasured`: cuando aparece un estado del
mundo que el esquema no contempla, se AGREGA el estado. Repartir los casos entre
los que ya existen fabrica falsos positivos con aspecto de dato.

La distincion que hace todo el trabajo es RUIDO vs AMBIGUA, y NO es una gradacion
de confianza: es la diferencia entre "el medidor miro y no habia nada" y "el
medidor no puede mirar". Colapsarlas convierte un contador roto en una orden de
`git rm`. Es el mismo error que el 2026-08-20 casi borra 27 hooks, y la razon por
la que ahi se agrego un estado nuevo (`dispatched:unmeasured`) en vez de repartir
los casos entre los estados que ya existian.

DISCREPA es el monton mas valioso y el mas barato: no requiere juicio sobre la
utilidad, solo un JOIN. "Registrado pero jamas visto", "declarado bloqueante con
cero bloqueos", "citado en el indice pero inexistente en disco". Cada fila ahi es
un instrumento mintiendo o una primitiva rota, y las dos cosas se quieren saber.

Lo que este libro NO puede decidir, por familia
-----------------------------------------------
Medido el 2026-08-21, no asumido:

    hooks     hook-timing.jsonl vio 151 de 258 en disco, pero solo instrumenta lo
              que settings.json nombra. Un gate que corre DENTRO de un despachador
              es invisible para el.
              -> SIRVE/RUIDO son afirmables solo para el hook registrado DIRECTO.
                 El despachado va a AMBIGUA aunque su contador diga cero.

    skills    skill-invocations.jsonl tiene 9 filas historicas. El medidor NO VE.
              -> "sin uso observado" no dice nada sobre la skill, dice todo sobre
                 el contador. TODA skill alcanzable cae en AMBIGUA por construccion.

    rules     el router mide EMISION, no si el consejo sirvio. No existe
              rule-router.jsonl: nadie registra que ignoraste una sugerencia.
              -> se puede decidir si RUIDO POR SATURACION (cuesta contexto y se
                 emite de mas), no si el contenido vale.

Y `primitive-interventions.jsonl` parece transversal --tiene `primitive_family`--
pero en 3.334 filas registro UNA familia y OCHO hooks distintos. Un esquema de
cuatro familias con datos de una sola no es un medidor transversal, es una
promesa. No se lo usa como si lo fuera.

La utilidad NO se mide aca
--------------------------
Ninguna columna de este archivo dice si una primitiva sirve para lo que existe.
Eso se cierra leyendo una muestra. Lo que este libro hace es reducir CUANTO hay
que leer: de ~650 primitivas a las que caen en AMBIGUA y DISCREPA.

Uso
---
    scripts/cos_primitive_ledger.py                    # tabla resumen
    scripts/cos_primitive_ledger.py --write            # escribe el libro .md
    scripts/cos_primitive_ledger.py --familia hooks    # una sola
    scripts/cos_primitive_ledger.py --json

Exit: 0 si pudo clasificar todas las familias pedidas · 2 si alguna fuente de
evidencia falto. No hay exit 1: este instrumento no juzga, inventaria.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
METRICS = REPO / ".cognitive-os" / "metrics"
NO_PUDO = 2

# Que puede y que NO puede decidir el medidor de cada familia. Se imprime con el
# resultado: un monton "RUIDO" sin esta linea al lado es una orden de borrado
# disfrazada de dato.
COMPETENCIA = {
    "hooks": (
        "hook-timing.jsonl instrumenta lo que settings.json NOMBRA y vio 151 nombres "
        "distintos: puede distinguir 'nunca disparo' de 'no lo se' SOLO para esos. "
        "Es ciego a los gates que un despachador corre por dentro, y al hook que "
        "bloquea con exit 0 + JSON en stdout."
    ),
    "skills": (
        "skill-invocations.jsonl tiene 9 filas historicas: NO PUEDE decir que una "
        "skill no se uso. Toda skill alcanzable cae en AMBIGUA a proposito."
    ),
    "rules": (
        "mide si la regla se EMITE y cuanto contexto ocupa; NO si el consejo "
        "sirvio. Nadie registra una sugerencia ignorada."
    ),
}


def _leer_jsonl(nombre: str):
    """Devuelve (filas, None) o ([], motivo). Ausente NO es lista vacia."""
    p = METRICS / nombre
    if not p.is_file():
        return [], f"{nombre} ausente"
    out = []
    with p.open(errors="replace") as fh:
        for ln in fh:
            try:
                out.append(json.loads(ln))
            except Exception:
                continue
    return out, None


# --------------------------------------------------------------------------- #
# HOOKS
# --------------------------------------------------------------------------- #
def censar_hooks() -> tuple[list[dict], list[str]]:
    avisos = []
    en_disco = {p.stem: p for p in REPO.glob("hooks/*.sh")}
    en_disco.update({p.stem: p for p in REPO.glob("packages/*/hooks/*.sh")})

    settings = REPO / ".claude" / "settings.json"
    registrados: set[str] = set()
    # Los que llegan por despachador, aparte: el medidor de timing NO LOS VE.
    despachados: set[str] = set()
    if settings.is_file():
        crudo = settings.read_text(errors="replace")
        # Se matchea el basename dentro del texto del comando: el hook real puede
        # ir envuelto por el wrapper de timing, asi que el string no es la ruta sola.
        for stem in en_disco:
            if re.search(rf"/{re.escape(stem)}\.sh\b", crudo):
                registrados.add(stem)

        # CLAUSURA TRANSITIVA: un hook registrado puede DESPACHAR otros.
        #
        # `hooks/bash-hot-path-dispatcher.sh` corre `destructive-rm-blocker.sh`,
        # `destructive-git-blocker.sh` y ocho mas como gates P0 (commit 60f29880e,
        # "restore bash governance via tiered dispatcher"). Ninguno aparece en
        # settings.json, y sin seguir la cadena el libro los acusaba a los doce de
        # "la proyeccion los perdio" -- doce falsos positivos, dos de ellos sobre
        # los guards de `rm` y de git.
        #
        # El sintoma que lo delato: `rm-op-blocks.jsonl` tiene 269 filas. Un hook
        # supuestamente no cableado que igual escribe su bitacora no esta muerto:
        # esta corriendo por una via que el instrumento no mira.
        frontera = set(registrados)
        while frontera:
            nuevos = set()
            for padre in frontera:
                ruta = en_disco.get(padre)
                if not ruta or not ruta.is_file():
                    continue
                cuerpo = ruta.read_text(errors="replace")
                for stem in en_disco:
                    if stem not in registrados and re.search(
                        rf"hooks/{re.escape(stem)}\.sh\b", cuerpo
                    ):
                        nuevos.add(stem)
            registrados |= nuevos
            despachados |= nuevos
            frontera = nuevos
    else:
        avisos.append("settings.json ausente: no se puede saber que hook esta registrado")

    # Las OMISIONES DECLARADAS. Sin esto, un hook deliberadamente no registrado
    # --con status, motivo y proxima accion escritos-- sale como "nadie lo puede
    # invocar", que es acusar de muerto a algo que esta en regla. El limite estaba
    # declarado en la tabla del censo y aun asi la primera version lo ignoro: 107
    # hooks marcados RUIDO, casi todos con su motivo ya escrito.
    #
    # OJO: el archivo tiene extension .yaml y su contenido es JSON. Se parsea con
    # yaml, que lee JSON tambien, para no depender de esa coincidencia.
    # La DECLARACION CANONICA. `cognitive-os.yaml` no es un catalogo: cada entrada
    # trae `script`, `event` y `matcher`, y `.claude/settings.json` es su proyeccion
    # (ADR-144). Sin leerla, un hook declarado con evento y matcher que la proyeccion
    # perdio se reporta como "nadie lo registro" -- se acusa al hook en vez de al
    # proyector, que es donde esta el defecto.
    canonicos: dict[str, str] = {}
    canon = REPO / "cognitive-os.yaml"
    if canon.is_file():
        try:
            import yaml  # type: ignore
            texto = canon.read_text(errors="replace")
            for stem in en_disco:
                m = re.search(
                    rf"^\s+{re.escape(stem)}:\s*$\n((?:\s+\w+:.*\n)+)", texto, re.M
                )
                if m:
                    ev = re.search(r"event:\s*(\S+)", m.group(1))
                    mt = re.search(r"matcher:\s*(\S+)", m.group(1))
                    canonicos[stem] = f"event={ev.group(1) if ev else '?'} matcher={mt.group(1) if mt else '?'}"
        except Exception as exc:
            avisos.append(f"cognitive-os.yaml ilegible: {exc}")
    else:
        avisos.append("cognitive-os.yaml ausente: no se puede distinguir 'nunca declarado' de 'la proyeccion lo perdio'")

    omitidas: dict[str, str] = {}
    manif = REPO / "manifests" / "hook-registration-classification.yaml"
    if manif.is_file():
        try:
            import yaml  # type: ignore
            datos = yaml.safe_load(manif.read_text(errors="replace")) or {}
            for e in datos.get("entries", []):
                stem = Path(str(e.get("path", ""))).stem
                if stem:
                    omitidas[stem] = str(e.get("status") or "sin status")
        except Exception as exc:
            avisos.append(f"manifiesto de omisiones ilegible: {exc}")
    else:
        avisos.append(
            "manifests/hook-registration-classification.yaml ausente: todo hook no "
            "registrado se veria como ruido, incluidos los omitidos a proposito"
        )

    filas_t, err = _leer_jsonl("hook-timing.jsonl")
    if err:
        avisos.append(f"telemetria de hooks: {err}")
    vistos: Counter = Counter()
    bloqueos: Counter = Counter()
    for d in filas_t:
        nombre = Path(str(d.get("hook") or "")).stem
        if not nombre:
            continue
        vistos[nombre] += 1
        if d.get("exit_code") == 2 or d.get("decision") in ("block", "deny"):
            bloqueos[nombre] += 1

    medidor_ciego = bool(err) or not vistos

    out = []
    for stem in sorted(en_disco):
        reg = stem in registrados
        n = vistos.get(stem, 0)
        if not reg and n > 0 and stem not in omitidas:
            v, motivo = "DISCREPA", f"no esta en settings.json pero disparo {n} veces"
        elif not reg and stem in omitidas and n > 0:
            v, motivo = "DISCREPA", (
                f"declarado omitido ({omitidas[stem]}) pero disparo {n} veces: "
                "la omision describe otro estado del mundo"
            )
        elif not reg and stem in omitidas:
            v, motivo = "OMITIDA", f"omision declarada con motivo escrito ({omitidas[stem]})"
        elif not reg and stem in canonicos:
            # El caso mas grave del libro: la fuente canonica lo declara con evento
            # y matcher, y la proyeccion que EFECTIVAMENTE corre no lo tiene. No es
            # un hook olvidado -- es el contrato de proyeccion de ADR-144 roto en un
            # punto, y el sintoma es silencio: nadie ve el hook que falta.
            v, motivo = "DISCREPA", (
                f"declarado en cognitive-os.yaml ({canonicos[stem]}) pero AUSENTE de "
                ".claude/settings.json: la proyeccion lo perdio"
            )
        elif not reg:
            v, motivo = "DISCREPA", (
                "no registrado, sin declaracion canonica y SIN entrada en el manifiesto "
                "de omisiones, que exige una para todo hook no registrado"
            )
        elif n == 0 and stem in despachados:
            # LA MISMA LECCION, TERCERA VEZ. hook-timing.jsonl solo instrumenta lo
            # que settings.json nombra: el despachador. Los gates que el despachador
            # corre por dentro son invisibles para el, asi que su cero NO es "nunca
            # disparo", es "nadie lo estaba mirando". Sin esta rama el libro emitia
            # RUIDO sobre destructive-rm-blocker y destructive-git-blocker -- una
            # orden de borrado sobre los guards de `rm` y de git, con 269 filas de
            # rm-op-blocks.jsonl probando que funcionan.
            v, motivo = "AMBIGUA", (
                "corre por despachador (bash-hot-path-dispatcher u otro): el medidor "
                "de timing solo instrumenta al despachador, no a sus gates"
            )
        elif n == 0 and medidor_ciego:
            v, motivo = "AMBIGUA", "registrado, sin datos porque el medidor no pudo leerse"
        elif n == 0:
            v, motivo = "RUIDO", "registrado y el medidor VE, pero jamas disparo"
        elif bloqueos.get(stem, 0) > 0:
            v, motivo = "SIRVE", f"{n} corridas, {bloqueos[stem]} con efecto de bloqueo"
        else:
            v, motivo = "AMBIGUA", f"{n} corridas, cero efecto observable (puede bloquear con exit 0)"
        out.append({
            "familia": "hooks", "nombre": stem, "llega": reg,
            "efecto": n, "costo_chars": 0, "veredicto": v, "motivo": motivo,
        })
    return out, avisos


# --------------------------------------------------------------------------- #
# SKILLS
# --------------------------------------------------------------------------- #
def censar_skills() -> tuple[list[dict], list[str]]:
    avisos = []
    rutas = list(REPO.glob("skills/*/SKILL.md")) + list(REPO.glob("packages/*/skills/*/SKILL.md"))

    filas, err = _leer_jsonl("skill-invocations.jsonl")
    if err:
        avisos.append(f"contador de skills: {err}")
    if len(filas) < 50:
        avisos.append(
            f"el contador de skills tiene {len(filas)} filas historicas: no puede "
            "sostener ningun 'no se usa'. Por eso no se emite RUIDO en esta familia."
        )

    usadas: Counter = Counter()
    for d in filas:
        pl = d.get("payload") or {}
        nombre = pl.get("skill") or pl.get("skill_name") or d.get("skill")
        if nombre:
            usadas[str(nombre)] += 1

    out = []
    for p in sorted(rutas):
        nombre = p.parent.name
        texto = p.read_text(errors="replace")
        # Una skill sin `description` en el frontmatter no la puede elegir nadie:
        # es el unico campo que el router y el modelo ven antes de cargarla.
        tiene_desc = bool(re.search(r"^description:\s*\S", texto, re.M))
        n = usadas.get(nombre, 0)

        if not tiene_desc and n > 0:
            v, motivo = "DISCREPA", f"sin `description` en el frontmatter y aun asi se invoco {n} veces"
        elif not tiene_desc:
            v, motivo = "RUIDO", "sin `description`: el router no la puede proponer"
        elif n > 0:
            v, motivo = "SIRVE", f"invocada {n} veces"
        else:
            v, motivo = "AMBIGUA", "alcanzable; el contador no puede decir si se usa. Hay que LEERLA."
        out.append({
            "familia": "skills", "nombre": nombre, "llega": tiene_desc,
            "efecto": n, "costo_chars": len(texto), "veredicto": v, "motivo": motivo,
        })
    return out, avisos


# --------------------------------------------------------------------------- #
# RULES
# --------------------------------------------------------------------------- #
def censar_rules() -> tuple[list[dict], list[str]]:
    avisos = []
    rutas = sorted(REPO.glob("rules/*.md"))

    indice = REPO / "rules" / "RULES-COMPACT.md"
    citadas: set[str] = set()
    if indice.is_file():
        citadas = set(re.findall(r"\[`([a-z0-9-]+)`\]", indice.read_text(errors="replace")))
    else:
        avisos.append("RULES-COMPACT.md ausente: no se puede saber que regla esta citada")

    inst = REPO / "hooks" / "self-install.sh"
    excluidas: set[str] = set()
    nucleo: set[str] = set()
    if inst.is_file():
        crudo = inst.read_text(errors="replace")
        for var, destino in (("EXCLUDED_RULES", excluidas), ("CORE_RULES", nucleo)):
            # Se recorre LINEA POR LINEA hasta el `)` que cierra el array, y se
            # toman solo las entradas entrecomilladas.
            #
            # La primera version usaba `VAR=\((.*?)\)` con re.S y devolvia CERO
            # nombres para EXCLUDED_RULES: la primera linea del array trae un
            # comentario `# ── A) Hook-enforced (hook is the active enforcement
            # layer) ──` y el `.*?\)` cerraba en ESE parentesis. Con el array
            # vacio, las 95 reglas con omision declarada caian a DISCREPA -- 108
            # discrepancias inventadas por un regex, en el instrumento cuyo
            # unico trabajo es no inventarlas.
            dentro = False
            for linea in crudo.splitlines():
                if not dentro:
                    if re.match(rf"^{var}=\(\s*$", linea):
                        dentro = True
                    continue
                if re.match(r"^\s*\)\s*$", linea):
                    break
                m = re.search(r'"([^"]+)"', linea)
                if m:
                    destino.add(Path(m.group(1)).stem)
            if not destino:
                avisos.append(
                    f"{var} se parseo VACIO: o el array cambio de forma, o el parseo "
                    "esta roto. Cero entradas en un array que deberia tenerlas no se "
                    "trata como 'no hay omisiones declaradas'."
                )
    else:
        avisos.append("self-install.sh ausente: no se puede leer EXCLUDED_RULES ni CORE_RULES")

    out = []
    for p in rutas:
        nombre = p.stem
        if nombre == "RULES-COMPACT":
            continue
        texto = p.read_text(errors="replace")
        rutea = bool(re.search(r"^routing_patterns:", texto, re.M))
        retenida = bool(re.search(r"^routable:\s*false", texto, re.M))
        n_chars = len(texto)

        if nombre in nucleo:
            v, motivo = "SIRVE", "en CORE_RULES: llega siempre por el canal fijo"
        elif rutea:
            v, motivo = "SIRVE", "tiene routing_patterns: el router la puede emitir"
        elif retenida:
            v, motivo = "OMITIDA", "retenida a proposito (routable: false), con motivo escrito"
        elif nombre in excluidas:
            v, motivo = "OMITIDA", "omision declarada en EXCLUDED_RULES, con el hook que la reemplaza anotado al lado"
        elif nombre in citadas:
            v, motivo = "DISCREPA", "citada en el indice pero sin ruta ni omision declarada: nadie decidio"
        else:
            v, motivo = "RUIDO", "ni citada, ni ruteada, ni declarada omitida"
        out.append({
            "familia": "rules", "nombre": nombre, "llega": nombre in nucleo or rutea,
            "efecto": 0, "costo_chars": n_chars, "veredicto": v, "motivo": motivo,
        })
    # Las reglas citadas en el indice que NO existen en disco: la discrepancia mas
    # barata de todas, y la que produce una referencia rota en tiempo de ruteo.
    en_disco = {p.stem for p in rutas}
    for nombre in sorted(citadas - en_disco):
        out.append({
            "familia": "rules", "nombre": nombre, "llega": False, "efecto": 0,
            "costo_chars": 0, "veredicto": "DISCREPA",
            "motivo": "citada en RULES-COMPACT.md pero NO EXISTE en rules/",
        })
    return out, avisos


FAMILIAS = {"hooks": censar_hooks, "skills": censar_skills, "rules": censar_rules}
ORDEN = ["DISCREPA", "AMBIGUA", "RUIDO", "OMITIDA", "SIRVE"]


def render(filas: list[dict], avisos: list[str]) -> str:
    """El libro mayor, ordenado por lo que hay que leer primero."""
    L = ["# Libro mayor de primitivas", ""]
    L.append("Una fila por primitiva. Los montones estan ordenados por **cuanto hay que")
    L.append("leer**: `DISCREPA` primero porque es un JOIN y no requiere juicio; `SIRVE`")
    L.append("ultimo porque no hay nada que decidir ahi.")
    L.append("")
    L.append("`RUIDO` significa **el medidor miro y no habia nada**. `AMBIGUA` significa")
    L.append("**el medidor no puede mirar**. No son grados de confianza: colapsarlas")
    L.append("convierte un contador roto en una orden de borrado.")
    L.append("")

    por_fam: dict[str, list[dict]] = {}
    for f in filas:
        por_fam.setdefault(f["familia"], []).append(f)

    L.append("## Resumen")
    L.append("")
    L.append("| familia | total | DISCREPA | AMBIGUA | RUIDO | SIRVE |")
    L.append("|---|--:|--:|--:|--:|--:|")
    for fam, rs in por_fam.items():
        c = Counter(r["veredicto"] for r in rs)
        L.append(f"| {fam} | {len(rs)} | {c['DISCREPA']} | {c['AMBIGUA']} | {c['RUIDO']} | {c['SIRVE']} |")
    L.append("")

    if avisos:
        L.append("## Lo que no se pudo medir")
        L.append("")
        for a in avisos:
            L.append(f"- {a}")
        L.append("")

    for fam, rs in por_fam.items():
        L.append(f"## {fam}")
        L.append("")
        L.append(f"> **Competencia del medidor.** {COMPETENCIA.get(fam, '(no declarada)')}")
        L.append("")
        for bucket in ORDEN:
            sub = [r for r in rs if r["veredicto"] == bucket]
            if not sub:
                continue
            L.append(f"### {bucket} — {len(sub)}")
            L.append("")
            for r in sorted(sub, key=lambda x: -x["costo_chars"]):
                costo = f" · {r['costo_chars']:,} chars" if r["costo_chars"] else ""
                L.append(f"- [ ] `{r['nombre']}`{costo} — {r['motivo']}")
            L.append("")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--familia", help="hooks, skills o rules (coma para varias)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--write", action="store_true", help="escribe docs/06-Daily/reports/libro-mayor-primitivas.md")
    a = ap.parse_args()

    pedidas = list(FAMILIAS)
    if a.familia:
        pedidas = [f.strip() for f in a.familia.split(",") if f.strip()]
        desconocidas = [f for f in pedidas if f not in FAMILIAS]
        if desconocidas:
            raise SystemExit(f"familia desconocida: {desconocidas}. Hay: {list(FAMILIAS)}")

    filas: list[dict] = []
    avisos: list[str] = []
    for f in pedidas:
        rs, av = FAMILIAS[f]()
        filas.extend(rs)
        avisos.extend(av)

    if a.json:
        print(json.dumps({"filas": filas, "avisos": avisos}, indent=2, ensure_ascii=False))
    else:
        texto = render(filas, avisos)
        if a.write:
            destino = REPO / "docs" / "06-Daily" / "reports" / "libro-mayor-primitivas.md"
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(texto, encoding="utf-8")
            print(f"escrito: {destino.relative_to(REPO)}  ({len(filas)} filas)")
            c = Counter(r["veredicto"] for r in filas)
            print("  " + "  ".join(f"{k}={c[k]}" for k in ORDEN))
            print(f"  hay que LEER: {c['DISCREPA'] + c['AMBIGUA']} de {len(filas)}")
        else:
            print(texto)

    # No poder leer una fuente NO se degrada a "sin hallazgos".
    return NO_PUDO if any("ausente" in x for x in avisos) else 0


if __name__ == "__main__":
    sys.exit(main())

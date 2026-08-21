#!/usr/bin/env python3
# SCOPE: os-only
"""Cruce DECLARADO-contra-USADO de la superficie que se inyecta en contexto.

Por que existe
--------------
El SO declara una superficie enorme --canal fijo a todo sub-agente, 132 reglas,
~200 skills, servidores MCP-- y cada cosa declarada cuesta caracteres. Lo que
faltaba no era el inventario (el censo ya lo da) sino el cruce con el USO real,
para poder ordenar por desperdicio.

El metodo es el de `gh aw audit` (github/gh-aw, MIT, verificado 2026-08-21:
4.970 estrellas, ultimo push ese mismo dia): cruzar el manifiesto de lo
declarado contra las llamadas efectivas de los logs, y ordenar por costo. GitHub
reporto hasta -62% de tokens podando tools MCP que nadie llamaba.

Lo que este script NO hace, a proposito
---------------------------------------
No dice "esto no se usa" cuando el medidor no ve. Un contador con 9 filas para
200 skills no puede distinguir "nadie la llamo" de "no estoy mirando". El script
calcula, para cada instrumento, la MINIMA CUOTA DE USO DETECTABLE al 95%:

    mds = 1 - 0.05 ** (1 / N)

con N = observaciones del instrumento. Es la cuota p mas chica tal que un item
usado con esa frecuencia tendria menos de 5% de probabilidad de pasar
desapercibido en N tiradas ((1-p)^N <= 0.05). Con N=9 da 28,3%: el contador de
skills solo puede descartar skills que se usen mas de una vez cada cuatro. Por
eso esa familia sale SIN MEDICION y no CERO USO.

Y cada fuente declara SU ventana, medida del dato (min/max timestamp), nunca
"todo". El instrumento hermano `scripts/guard_value_ledger.py:154` escribe
`"ventana": "todo"` sobre un log rotado de ~23 h; de ahi salio publicado un
"0,29% de bloqueos" leido como historia completa. Aca no.

Uso
---
    scripts/declared_vs_used.py                 # tabla markdown
    scripts/declared_vs_used.py --json          # para encadenar
    scripts/declared_vs_used.py --all-projects  # transcripts de todos los repos
    scripts/declared_vs_used.py --top 40        # cuantas filas del ranking

Exit: 0 sin hallazgos - 1 hay items SIN USO OBSERVADO donde el medidor SI ve -
2 no se pudo medir (falta un instrumento o el repo no parsea).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

METRICS = REPO_ROOT / ".cognitive-os" / "metrics"
TOKEN_DIVISOR = 4  # misma convencion que scripts/cos_preamble_budget.py

# Cuota de uso que queremos poder descartar. Si el instrumento no llega a
# detectar algo usado en el 5% de las oportunidades, no lo dejamos opinar.
DEFAULT_MDS_THRESHOLD = 0.05

_TS_KEYS = ("timestamp", "ts", "time", "created_at", "@timestamp")


# ---------------------------------------------------------------- utilidades


def _parse_ts(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value:
        return None
    raw = value.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _row_ts(row: Dict[str, Any]) -> Optional[datetime]:
    for key in _TS_KEYS:
        dt = _parse_ts(row.get(key))
        if dt is not None:
            return dt
    payload = row.get("payload")
    if isinstance(payload, dict):
        for key in _TS_KEYS:
            dt = _parse_ts(payload.get(key))
            if dt is not None:
                return dt
    return None


def _window(stamps: List[datetime], rows: int, unparsed: int = 0) -> Dict[str, Any]:
    """Ventana MEDIDA del dato. Nunca la palabra 'todo'."""
    if not stamps:
        return {
            "desde": None,
            "hasta": None,
            "horas": 0.0,
            "filas": rows,
            "filas_sin_timestamp": unparsed,
            "nota": "ninguna fila trajo timestamp parseable: la ventana es desconocida",
        }
    lo, hi = min(stamps), max(stamps)
    return {
        "desde": lo.isoformat(),
        "hasta": hi.isoformat(),
        "horas": round((hi - lo).total_seconds() / 3600.0, 1),
        "filas": rows,
        "filas_sin_timestamp": unparsed,
        "nota": None,
    }


def _mds(n_observations: int) -> float:
    """Minima cuota de uso detectable al 95% con N observaciones."""
    if n_observations <= 0:
        return 1.0
    return 1.0 - 0.05 ** (1.0 / n_observations)


def _iter_jsonl(path: Path) -> Iterable[Tuple[Optional[Dict[str, Any]], str]]:
    if not path.exists():
        return
    with path.open(encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except (ValueError, TypeError):
                yield None, line
                continue
            yield (obj if isinstance(obj, dict) else None), line


def _chars(path: Path) -> int:
    try:
        return len(path.read_text(encoding="utf-8", errors="ignore"))
    except OSError:
        return 0


# ------------------------------------------------------------- lo declarado


def declare_canal_fijo() -> Dict[str, Any]:
    """El bloque que SubagentStart mete en TODO sub-agente, medido corriendolo."""
    hook = REPO_ROOT / "hooks" / "subagent-context-injector.sh"
    cap = 10000  # MAX_CONTEXT_CHARS del propio hook
    item: Dict[str, Any] = {
        "id": "canal-fijo/subagent-context-injector",
        "familia": "canal-fijo",
        "fuentes": [
            "templates/agent-mandatory-rules.md",
            "templates/agent-preamble.md",
        ],
        "cap_chars": cap,
    }
    if not hook.exists():
        item["error"] = f"no existe {hook.relative_to(REPO_ROOT)}"
        item["chars"] = 0
        return item
    try:
        proc = subprocess.run(
            ["bash", str(hook)],
            input=json.dumps({"prompt": "declared_vs_used probe"}),
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(REPO_ROOT),
        )
        payload = json.loads(proc.stdout)
        ctx = payload["hookSpecificOutput"]["additionalContext"]
        item["chars"] = len(ctx)
        item["medido_por"] = "ejecucion real del hook con payload por stdin"
    except Exception as exc:  # pragma: no cover - degradacion honesta
        composed = ""
        for name in ("agent-mandatory-rules.md", "agent-preamble.md"):
            part = _chars(REPO_ROOT / "templates" / name)
            composed += "\n\n---\n" if composed else ""
            composed += "x" * part
        item["chars"] = len(composed)
        item["medido_por"] = f"suma de templates (el hook no corrio: {exc})"
    item["tokens"] = item["chars"] // TOKEN_DIVISOR
    item["margen_chars"] = cap - item["chars"]
    item["margen_pct"] = round(100.0 * item["margen_chars"] / cap, 1)
    return item


def declare_reglas() -> Dict[str, Any]:
    """Reglas en disco vs reglas que el router puede realmente emitir."""
    roots = [REPO_ROOT / "rules"]
    roots.extend(sorted((REPO_ROOT / "packages").glob("*/rules")))
    en_disco: Dict[str, Dict[str, Any]] = {}
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.glob("*.md")):
            real = path.resolve()
            name = path.stem
            if name in en_disco:
                continue
            en_disco[name] = {
                "id": name,
                "familia": "regla",
                "path": os.path.relpath(real, REPO_ROOT),
                "chars": _chars(real),
                "es_symlink": path.is_symlink(),
            }

    routable: Dict[str, str] = {}
    withheld: Dict[str, str] = {}
    error = None
    try:
        from cos_lib.rule_router import RuleRouter

        router = RuleRouter()
        for entry in router.all_loaded():
            if entry.routable:
                routable[entry.rule_name] = entry.trigger_priority or "?"
            else:
                withheld[entry.rule_name] = entry.routable_reason or "?"
    except Exception as exc:  # pragma: no cover
        error = f"RuleRouter no cargo: {exc}"

    for name, item in en_disco.items():
        if name in routable:
            item["declaracion"] = "ruteable"
        elif name in withheld:
            item["declaracion"] = "retenida"
            item["motivo_retencion"] = withheld[name]
        else:
            item["declaracion"] = "sin-metadata-de-ruteo"

    return {
        "items": list(en_disco.values()),
        "en_disco": len(en_disco),
        "con_metadata_de_ruteo": len(routable) + len(withheld),
        "ruteables": len(routable),
        "retenidas": len(withheld),
        "chars_totales": sum(i["chars"] for i in en_disco.values()),
        "error": error,
    }


_FRONTMATTER_DESC = re.compile(
    r"^---\s*$(.*?)^---\s*$", re.MULTILINE | re.DOTALL
)


def _skill_description_chars(text: str) -> int:
    """Costo del pedazo SIEMPRE presente: name + description del frontmatter."""
    match = _FRONTMATTER_DESC.search(text)
    if not match:
        return 0
    block = match.group(1)
    keep = []
    grabbing = False
    for line in block.splitlines():
        if re.match(r"^(name|description)\s*:", line):
            grabbing = True
            keep.append(line)
        elif grabbing and re.match(r"^\s+\S", line):
            keep.append(line)
        elif re.match(r"^\S+\s*:", line):
            grabbing = False
    return len("\n".join(keep))


def declare_skills() -> Dict[str, Any]:
    roots = [REPO_ROOT / "skills"]
    roots.extend(sorted((REPO_ROOT / "packages").glob("*/skills")))
    items: Dict[str, Dict[str, Any]] = {}
    for root in roots:
        if not root.is_dir():
            continue
        for entry in sorted(root.iterdir()):
            skill_md = entry / "SKILL.md"
            if not skill_md.is_file():
                continue
            name = entry.name
            if name in items:
                continue
            real = skill_md.resolve()
            text = ""
            try:
                text = real.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                pass
            items[name] = {
                "id": name,
                "familia": "skill",
                "path": os.path.relpath(real, REPO_ROOT),
                "chars": len(text),
                "chars_descripcion": _skill_description_chars(text),
                "es_symlink": entry.is_symlink() or skill_md.is_symlink(),
            }

    router_table = 0
    error = None
    try:
        from cos_lib.skill_router import SkillRouter

        router = SkillRouter()
        router_table = int(router.routing_entry_count())
        for name in router.known_skills():
            if name not in items:
                items[name] = {
                    "id": name,
                    "familia": "skill",
                    "path": None,
                    "chars": 0,
                    "chars_descripcion": 0,
                    "es_symlink": False,
                    "nota": "en la tabla del router pero sin SKILL.md alcanzable en el repo",
                }
    except Exception as exc:  # pragma: no cover
        error = f"SkillRouter no cargo: {exc}"

    return {
        "items": list(items.values()),
        "universo": len(items),
        "router_table_size": router_table,
        "chars_totales": sum(i["chars"] for i in items.values()),
        "chars_descripcion_totales": sum(i["chars_descripcion"] for i in items.values()),
        "error": error,
    }


def declare_mcp() -> Dict[str, Any]:
    """Servidores MCP declarados POR EL REPO (no los del perfil del operador)."""
    candidates = [
        REPO_ROOT / ".mcp.json",
        REPO_ROOT / ".claude" / "settings.json",
        REPO_ROOT / ".claude" / "settings.local.json",
    ]
    items: List[Dict[str, Any]] = []
    revisados = []
    for path in candidates:
        revisados.append(os.path.relpath(path, REPO_ROOT))
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except (ValueError, OSError):
            continue
        servers = data.get("mcpServers")
        if not isinstance(servers, dict):
            continue
        for name, cfg in servers.items():
            items.append(
                {
                    "id": name,
                    "familia": "mcp",
                    "path": os.path.relpath(path, REPO_ROOT),
                    "chars": len(json.dumps(cfg, ensure_ascii=False)),
                    "nota": "el costo real es el schema de sus tools en cada turno, "
                    "que no vive en el repo",
                }
            )
    return {"items": items, "archivos_revisados": revisados}


# ------------------------------------------------------------- lo observado


def observe_skill_invocations() -> Dict[str, Any]:
    path = METRICS / "skill-invocations.jsonl"
    stamps: List[datetime] = []
    hits: Dict[str, int] = {}
    rows = 0
    unparsed = 0
    for obj, _raw in _iter_jsonl(path):
        rows += 1
        if obj is None:
            unparsed += 1
            continue
        dt = _row_ts(obj)
        if dt:
            stamps.append(dt)
        payload = obj.get("payload") if isinstance(obj.get("payload"), dict) else {}
        name = payload.get("skill_name") or obj.get("skill_name")
        if name:
            hits[str(name)] = hits.get(str(name), 0) + 1
    return {
        "id": "skill-invocations",
        "path": os.path.relpath(path, REPO_ROOT),
        "existe": path.exists(),
        "cubre": ["skill"],
        "observaciones": rows,
        "hits": hits,
        "ventana": _window(stamps, rows, unparsed),
        "limite": "un logger dedicado; solo registra invocaciones que pasaron por el "
        "hook que lo escribe, no las que el modelo hizo por su cuenta",
    }


def observe_rule_suggestions() -> Dict[str, Any]:
    path = METRICS / "rule-suggestion.jsonl"
    stamps: List[datetime] = []
    hits: Dict[str, int] = {}
    rows = 0
    unparsed = 0
    for obj, _raw in _iter_jsonl(path):
        rows += 1
        if obj is None:
            unparsed += 1
            continue
        dt = _row_ts(obj)
        if dt:
            stamps.append(dt)
        top = obj.get("top_match")
        if top:
            hits[str(top)] = hits.get(str(top), 0) + 1
        for m in obj.get("matches") or []:
            name = m.get("rule") or m.get("rule_name") if isinstance(m, dict) else None
            if name:
                hits[str(name)] = hits.get(str(name), 0) + 1
    return {
        "id": "rule-suggestion",
        "path": os.path.relpath(path, REPO_ROOT),
        "existe": path.exists(),
        "cubre": ["regla"],
        "observaciones": rows,
        "hits": hits,
        "ventana": _window(stamps, rows, unparsed),
        "limite": "registra que el router SUGIRIO la regla, no que el agente la haya "
        "leido ni obedecido; guarda prompt_hash, no el texto",
    }


def observe_primitive_interventions() -> Dict[str, Any]:
    path = METRICS / "primitive-interventions.jsonl"
    stamps: List[datetime] = []
    hits: Dict[str, int] = {}
    familias: Dict[str, int] = {}
    rows = 0
    unparsed = 0
    for obj, _raw in _iter_jsonl(path):
        rows += 1
        if obj is None:
            unparsed += 1
            continue
        dt = _row_ts(obj)
        if dt:
            stamps.append(dt)
        fam = str(obj.get("primitive_family") or "?")
        familias[fam] = familias.get(fam, 0) + 1
        pid = obj.get("primitive_id")
        if pid:
            hits[str(pid)] = hits.get(str(pid), 0) + 1
    return {
        "id": "primitive-interventions",
        "path": os.path.relpath(path, REPO_ROOT),
        "existe": path.exists(),
        "cubre": sorted(familias),
        "familias_registradas": familias,
        "observaciones": rows,
        "hits": hits,
        "ventana": _window(stamps, rows, unparsed),
        "limite": "el esquema tiene campo primitive_family (transversal) pero SOLO "
        "hay filas de una familia: es una promesa de medidor, no un medidor",
    }


def observe_hook_timing() -> Dict[str, Any]:
    path = METRICS / "hook-timing.jsonl"
    stamps: List[datetime] = []
    hits: Dict[str, int] = {}
    rows = 0
    unparsed = 0
    for obj, _raw in _iter_jsonl(path):
        rows += 1
        if obj is None:
            unparsed += 1
            continue
        dt = _row_ts(obj)
        if dt:
            stamps.append(dt)
        name = obj.get("hook") or obj.get("hook_name")
        if name:
            hits[str(name)] = hits.get(str(name), 0) + 1
    return {
        "id": "hook-timing",
        "path": os.path.relpath(path, REPO_ROOT),
        "existe": path.exists(),
        "cubre": ["hook"],
        "observaciones": rows,
        "hits": hits,
        "ventana": _window(stamps, rows, unparsed),
        "limite": "el archivo ROTA; la ventana de abajo es la real, cualquier "
        "afirmacion historica mas larga que eso es falsa",
    }


def _transcript_dirs(all_projects: bool) -> List[Path]:
    base = Path.home() / ".claude" / "projects"
    if not base.is_dir():
        return []
    if all_projects:
        return sorted(p for p in base.iterdir() if p.is_dir())
    # Claude Code aplana TODO caracter no alfanumerico a "-": un usuario
    # "matias.nahuel.amendola" produce "matias-nahuel-amendola". Reemplazar solo
    # "/" devolvia un directorio inexistente y el instrumento reportaba 0
    # observaciones en silencio, que es exactamente el falso CERO que este
    # script existe para no publicar.
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(REPO_ROOT))
    own = base / slug
    return [own] if own.is_dir() else []


def _collect_tool_use(obj: Any, depth: int = 0) -> List[Dict[str, Any]]:
    """Junta TODOS los bloques tool_use de una fila de transcript.

    La primera version solo miraba `message.content`. Un cruce con ripgrep
    (`rg -o '"type":"tool_use"'`) dio 28.728 ocurrencias contra 20.175 bloques
    vistos: el 30% vivia en otras ramas del JSON (sidechains, reintentos). Un
    instrumento que se pierde un tercio del corpus no puede firmar un cero.
    """
    if depth > 6:
        return []
    found: List[Dict[str, Any]] = []
    if isinstance(obj, dict):
        if obj.get("type") == "tool_use" and obj.get("name"):
            found.append(obj)
            return found
        for value in obj.values():
            if isinstance(value, (dict, list)):
                found.extend(_collect_tool_use(value, depth + 1))
    elif isinstance(obj, list):
        for value in obj:
            if isinstance(value, (dict, list)):
                found.extend(_collect_tool_use(value, depth + 1))
    return found


def observe_transcripts(all_projects: bool = False) -> Dict[str, Any]:
    """El corpus real: que herramientas y skills se invocaron de verdad."""
    dirs = _transcript_dirs(all_projects)
    stamps: List[datetime] = []
    skill_hits: Dict[str, int] = {}
    mcp_hits: Dict[str, int] = {}
    tool_hits: Dict[str, int] = {}
    read_skill_hits: Dict[str, int] = {}
    tool_use_events = 0
    files = 0

    skill_path_re = re.compile(r"skills/([^/]+)/SKILL\.md")

    for directory in dirs:
        for path in sorted(directory.rglob("*.jsonl")):
            files += 1
            try:
                fh = path.open(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            with fh:
                for line in fh:
                    if '"tool_use"' not in line:
                        continue
                    try:
                        obj = json.loads(line)
                    except (ValueError, TypeError):
                        continue
                    if not isinstance(obj, dict):
                        continue
                    dt = _row_ts(obj)
                    for block in _collect_tool_use(obj):
                        tool_use_events += 1
                        if dt:
                            stamps.append(dt)
                        name = str(block.get("name") or "?")
                        tool_hits[name] = tool_hits.get(name, 0) + 1
                        params = block.get("input") if isinstance(block.get("input"), dict) else {}
                        if name.startswith("mcp__"):
                            server = name.split("__")[1] if "__" in name else name
                            mcp_hits[server] = mcp_hits.get(server, 0) + 1
                        if name == "Skill":
                            sk = params.get("skill") or params.get("name")
                            if sk:
                                sk = str(sk).split(":")[-1]
                                skill_hits[sk] = skill_hits.get(sk, 0) + 1
                        elif name == "SlashCommand":
                            cmd = str(params.get("command") or "").lstrip("/").split()[0:1]
                            if cmd:
                                skill_hits[cmd[0]] = skill_hits.get(cmd[0], 0) + 1
                        elif name in ("Read", "Grep", "Glob"):
                            target = str(params.get("file_path") or params.get("path") or "")
                            found = skill_path_re.search(target)
                            if found:
                                key = found.group(1)
                                read_skill_hits[key] = read_skill_hits.get(key, 0) + 1

    merged_skills = dict(skill_hits)
    for key, count in read_skill_hits.items():
        merged_skills[key] = merged_skills.get(key, 0) + count

    return {
        "id": "transcripts",
        "path": str(dirs[0]) if dirs else str(Path.home() / ".claude" / "projects"),
        "existe": bool(dirs),
        "cubre": ["skill", "mcp"],
        "archivos": files,
        "observaciones": tool_use_events,
        "hits": merged_skills,
        "hits_invocacion_explicita": skill_hits,
        "hits_lectura_de_skill_md": read_skill_hits,
        "hits_mcp": mcp_hits,
        "hits_tool": dict(sorted(tool_hits.items(), key=lambda kv: -kv[1])[:40]),
        "ventana": _window(stamps, tool_use_events),
        "limite": "es el corpus mas grande que existe, pero solo ve lo que el modelo "
        "invoco como TOOL: una regla leida dentro del prompt del sistema no deja "
        "tool_use, asi que este instrumento NO cubre reglas ni el canal fijo",
        "alcance": "todos los proyectos" if all_projects else "solo este repo",
    }


# ---------------------------------------------------------------- veredicto


def _alcance_estructural(instrumento_id: str, item: Dict[str, Any]) -> Tuple[bool, str]:
    """Puede este instrumento EMITIR una fila con este item, aunque se usara?

    Sin este filtro el cruce publica falsos ceros: `rule-suggestion` solo puede
    nombrar reglas que el router considera ruteables, asi que una regla sin
    metadata de ruteo sale con 0 hits por construccion, no por desuso.
    """
    if instrumento_id == "rule-suggestion":
        decl = item.get("declaracion")
        if decl == "ruteable":
            return True, ""
        return False, (
            f"el router no puede sugerirla (declaracion={decl}): 0 filas es una "
            "consecuencia del cableado, no una senal de uso"
        )
    return True, ""


def _judge_family(
    familia: str,
    items: List[Dict[str, Any]],
    instruments: List[Dict[str, Any]],
    mds_threshold: float,
) -> Dict[str, Any]:
    covering = [i for i in instruments if familia in (i.get("cubre") or []) and i.get("existe")]
    if not covering:
        for item in items:
            item["veredicto"] = "SIN MEDICION"
            item["motivo"] = f"ningun instrumento declara cubrir la familia '{familia}'"
            item["hits"] = 0
            item["visto_en"] = []
        return {
            "familia": familia,
            "estado_del_medidor": "CIEGO",
            "motivo": "no hay instrumento que cubra la familia",
            "items_declarados": len(items),
            "instrumentos": [],
        }

    def _n(inst: Dict[str, Any]) -> int:
        # N util = observaciones ATRIBUIDAS a algun item, no filas del archivo.
        # rule-suggestion tiene 445 filas pero solo 313 nombran una regla; las
        # otras 132 son corridas sin match y no son tiradas del sorteo.
        return sum(int(v) for v in (inst.get("hits") or {}).values())

    for item in items:
        total = 0
        vistos_en: List[str] = []
        alcanzan: List[Dict[str, Any]] = []
        fuera_de_alcance: List[str] = []
        for inst in covering:
            puede, motivo = _alcance_estructural(inst["id"], item)
            if not puede:
                fuera_de_alcance.append(f"{inst['id']}: {motivo}")
                continue
            alcanzan.append(inst)
            count = int((inst.get("hits") or {}).get(item["id"], 0))
            if count:
                total += count
                vistos_en.append(inst["id"])
        item["hits"] = total
        item["visto_en"] = vistos_en
        item["instrumentos_que_lo_alcanzan"] = [i["id"] for i in alcanzan]

        if total > 0:
            item["veredicto"] = "USADO"
            item["motivo"] = f"{total} observacion(es) en {', '.join(vistos_en)}"
            continue
        if not alcanzan:
            item["veredicto"] = "SIN MEDICION"
            item["motivo"] = "; ".join(fuera_de_alcance) or "ningun instrumento lo alcanza"
            continue
        best = max(alcanzan, key=_n)
        n = _n(best)
        mds = _mds(n)
        item["mds"] = round(mds, 4)
        if mds <= mds_threshold:
            item["veredicto"] = "SIN USO OBSERVADO"
            item["motivo"] = (
                f"0 de {n} observaciones atribuidas en {best['id']}; ese instrumento "
                f"detectaria un uso >= {mds*100:.1f}% de las oportunidades"
            )
        else:
            item["veredicto"] = "SIN MEDICION"
            item["motivo"] = (
                f"{best['id']} solo tiene N={n} observaciones atribuidas: detectaria "
                f"uso >= {mds*100:.1f}%, por encima del umbral {mds_threshold*100:.1f}% "
                "— no distingue 'no se uso' de 'no miro'"
            )

    best_global = max(covering, key=_n)
    n_global = _n(best_global)
    mds_global = _mds(n_global)
    alcanzables = sum(1 for i in items if i.get("instrumentos_que_lo_alcanzan"))
    return {
        "familia": familia,
        "estado_del_medidor": "VE" if (mds_global <= mds_threshold and alcanzables) else "CIEGO",
        "instrumento_de_referencia": best_global["id"],
        "observaciones_atribuidas": n_global,
        "filas_del_archivo": int(best_global.get("observaciones", 0)),
        "items_declarados": len(items),
        "items_estructuralmente_alcanzables": alcanzables,
        "items_distintos_observados": len([v for v in (best_global.get("hits") or {}).values() if v]),
        "mds": round(mds_global, 4),
        "mds_pct": round(mds_global * 100, 1),
        "umbral_mds_pct": round(mds_threshold * 100, 1),
        "ventana": best_global["ventana"],
        "instrumentos": [
            {
                "id": i["id"],
                "filas": i.get("observaciones", 0),
                "observaciones_atribuidas": _n(i),
                "ventana": i["ventana"],
            }
            for i in covering
        ],
    }


def build_report(all_projects: bool = False, mds_threshold: float = DEFAULT_MDS_THRESHOLD) -> Dict[str, Any]:
    canal = declare_canal_fijo()
    reglas = declare_reglas()
    skills = declare_skills()
    mcp = declare_mcp()

    instruments = [
        observe_skill_invocations(),
        observe_rule_suggestions(),
        observe_primitive_interventions(),
        observe_hook_timing(),
        observe_transcripts(all_projects=all_projects),
    ]
    for inst in instruments:
        inst["observaciones_atribuidas"] = sum(int(v) for v in (inst.get("hits") or {}).values())

    juicios = {
        "regla": _judge_family("regla", reglas["items"], instruments, mds_threshold),
        "skill": _judge_family("skill", skills["items"], instruments, mds_threshold),
        "mcp": _judge_family("mcp", mcp["items"], instruments, mds_threshold),
    }

    # El canal fijo no necesita medidor: se inyecta por construccion en cada
    # spawn. Su pregunta no es "se usa" sino "cuanto ocupa del cap".
    canal["veredicto"] = "USADO POR CONSTRUCCION"
    canal["motivo"] = (
        "SubagentStart lo emite en todo spawn; no hay condicion que lo saltee "
        "salvo private-mode o killswitch"
    )

    ranking: List[Dict[str, Any]] = []
    for familia, items in (("regla", reglas["items"]), ("skill", skills["items"]), ("mcp", mcp["items"])):
        for item in items:
            # Requisito duro: solo entra al ranking lo que un instrumento
            # REALMENTE alcanza y con muestra suficiente. Todo lo demas queda
            # afuera, no abajo.
            if item.get("veredicto") != "SIN USO OBSERVADO":
                continue
            confianza = 1.0 - float(item.get("mds", 1.0))
            ranking.append(
                {
                    "id": item["id"],
                    "familia": familia,
                    "chars": item["chars"],
                    "tokens": item["chars"] // TOKEN_DIVISOR,
                    "confianza_del_cero": round(confianza, 4),
                    "desperdicio": round(item["chars"] * confianza, 1),
                    "path": item.get("path"),
                    "visto_por": item.get("instrumentos_que_lo_alcanzan"),
                }
            )
    ranking.sort(key=lambda r: -r["desperdicio"])

    sin_medicion = {
        familia: sum(1 for i in items if i.get("veredicto") == "SIN MEDICION")
        for familia, items in (("regla", reglas["items"]), ("skill", skills["items"]), ("mcp", mcp["items"]))
    }

    return {
        "generado": datetime.now(timezone.utc).isoformat(),
        "repo_head": subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        ).stdout.strip(),
        "umbral_mds_pct": round(mds_threshold * 100, 1),
        "declarado": {
            "canal_fijo": canal,
            "reglas": {k: v for k, v in reglas.items() if k != "items"},
            "skills": {k: v for k, v in skills.items() if k != "items"},
            "mcp": {"servidores": len(mcp["items"]), "archivos_revisados": mcp["archivos_revisados"]},
        },
        "instrumentos": [
            {k: v for k, v in i.items() if k != "hits"} for i in instruments
        ],
        "juicios": juicios,
        "ranking_desperdicio": ranking,
        "sin_medicion": sin_medicion,
        "items": {
            "regla": reglas["items"],
            "skill": skills["items"],
            "mcp": mcp["items"],
        },
    }


# ------------------------------------------------------------------- salida


def render(report: Dict[str, Any], top: int) -> str:
    out: List[str] = []
    a = out.append
    a(f"# Declarado contra usado — HEAD {report['repo_head']}")
    a("")
    canal = report["declarado"]["canal_fijo"]
    a("## 1. Canal fijo (todo sub-agente lo recibe)")
    a("")
    a(f"- chars: **{canal['chars']:,}** de {canal['cap_chars']:,} "
      f"(~{canal['tokens']:,} tokens) — margen {canal['margen_chars']:,} "
      f"({canal['margen_pct']}%)")
    a(f"- medido por: {canal.get('medido_por')}")
    a(f"- veredicto: **{canal['veredicto']}** — {canal['motivo']}")
    a("")

    a("## 2. Instrumentos y SU ventana (medida del dato, nunca \"todo\")")
    a("")
    a("| instrumento | cubre | filas | obs. atribuidas | ventana | horas |")
    a("|---|---|---|---|---|---|")
    for inst in report["instrumentos"]:
        w = inst["ventana"]
        rango = f"{(w['desde'] or '?')[:16]} → {(w['hasta'] or '?')[:16]}" if w["desde"] else "DESCONOCIDA"
        a(f"| `{inst['id']}` | {', '.join(inst.get('cubre') or []) or '—'} | "
          f"{inst.get('observaciones', 0):,} | {inst.get('observaciones_atribuidas', 0):,} | "
          f"{rango} | {w['horas']} |")
    a("")
    for inst in report["instrumentos"]:
        a(f"- `{inst['id']}` — límite: {inst['limite']}")
    a("")

    a("## 3. ¿Ve el medidor? (por familia)")
    a("")
    a("| familia | declarados | alcanzables por algún instrumento | instrumento | N atribuido | distintos vistos | mín. uso detectable (95%) | estado |")
    a("|---|---|---|---|---|---|---|---|")
    for familia, j in report["juicios"].items():
        if "mds" not in j:
            a(f"| {familia} | {j.get('items_declarados', 0)} | 0 | ninguno | 0 | 0 | — | **CIEGO** |")
            continue
        a(f"| {familia} | {j['items_declarados']} | {j['items_estructuralmente_alcanzables']} | "
          f"`{j['instrumento_de_referencia']}` | {j['observaciones_atribuidas']:,} | "
          f"{j['items_distintos_observados']} | {j['mds_pct']}% | **{j['estado_del_medidor']}** |")
    a("")
    a("_`N atribuido` = filas que nombran un item, no filas del archivo: una corrida "
      "del router sin match no es una tirada del sorteo._")
    a("")

    a("### Veredictos por familia")
    a("")
    a("| familia | USADO | SIN USO OBSERVADO | SIN MEDICIÓN |")
    a("|---|---|---|---|")
    for familia, items in report["items"].items():
        c = {"USADO": 0, "SIN USO OBSERVADO": 0, "SIN MEDICION": 0}
        for it in items:
            c[it.get("veredicto", "SIN MEDICION")] = c.get(it.get("veredicto", "SIN MEDICION"), 0) + 1
        a(f"| {familia} | {c['USADO']} | {c['SIN USO OBSERVADO']} | {c['SIN MEDICION']} |")
    a("")

    a("## 4. Ranking de desperdicio (SOLO donde el medidor ve)")
    a("")
    ranking = report["ranking_desperdicio"]
    if not ranking:
        a("_Vacío._ Ninguna familia con medidor que vea produjo items sin uso observado.")
    else:
        a("| # | item | familia | chars | tokens | confianza del cero | desperdicio |")
        a("|---|---|---|---|---|---|---|")
        for idx, row in enumerate(ranking[:top], 1):
            a(f"| {idx} | `{row['id']}` | {row['familia']} | {row['chars']:,} | "
              f"{row['tokens']:,} | {row['confianza_del_cero']:.2f} | {row['desperdicio']:,.0f} |")
        if len(ranking) > top:
            a("")
            a(f"_({len(ranking) - top} filas más; usar `--top`.)_")
    a("")

    a("## 5. SIN MEDICIÓN (no se propone borrar nada de acá)")
    a("")
    for familia, count in report["sin_medicion"].items():
        total = len(report["items"][familia])
        a(f"- **{familia}**: {count} de {total} items sin veredicto de uso posible")
        motivos: Dict[str, int] = {}
        for it in report["items"][familia]:
            if it.get("veredicto") == "SIN MEDICION":
                motivos[str(it.get("motivo"))] = motivos.get(str(it.get("motivo")), 0) + 1
        for motivo, n in sorted(motivos.items(), key=lambda kv: -kv[1])[:4]:
            a(f"  - {n}× {motivo}")
    a("")
    return "\n".join(out)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true", help="salida JSON")
    parser.add_argument("--all-projects", action="store_true", help="escanear transcripts de todos los repos")
    parser.add_argument("--top", type=int, default=25, help="filas del ranking (default 25)")
    parser.add_argument(
        "--mds-threshold",
        type=float,
        default=DEFAULT_MDS_THRESHOLD,
        help="cuota de uso que el instrumento debe poder descartar (default 0.05)",
    )
    args = parser.parse_args(argv)

    try:
        report = build_report(all_projects=args.all_projects, mds_threshold=args.mds_threshold)
    except Exception as exc:  # pragma: no cover
        print(f"NO PUDE MEDIR: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render(report, args.top))

    if report["declarado"]["canal_fijo"].get("error"):
        return 2
    return 1 if report["ranking_desperdicio"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

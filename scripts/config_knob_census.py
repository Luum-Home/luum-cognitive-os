# SCOPE: os-only
"""Censo de perillas de configuración: qué se declara, quién lo lee, y si llega.

POR QUÉ EXISTE. El 2026-08-20 se encontró que `cleanup_on_exit` y
`merge_metrics_on_exit` (hooks/session-cleanup.sh) leían
`.cognitive-os/cognitive-os.yaml` —un archivo que no existe en ningún
checkout— y que además el parseo no cortaba el comentario de fin de línea. La
perilla funcionaba en exactamente una configuración que no ocurre. La pregunta
que este script contesta es *cuántas más hay*, de forma reproducible.

Cuatro formas de estar roto, y son distintas:

  1. la lectura apunta a un archivo que no existe  -> el default rige siempre
  2. el archivo existe pero la clave no está ahí   -> mismo efecto, menos visible
  3. el parseo no llega al valor (comentario de fin de línea, típicamente)
  4. la clave está declarada en el yaml y NADIE la lee -> perilla decorativa

Lo que este instrumento NO puede ver, dicho para que nadie se confíe:

  * Un nombre de clave genérico (`enabled`, `name`, `path`, `mode`...) matchea
    en cualquier lado por casualidad. No se cuenta como leída ni como huérfana:
    se cuenta como CIEGA.
  * Un consumidor fuera de este repo (un instalador, un paquete externo, un
    proyecto consumidor) no se ve. Una clave "sin lector" acá puede tener
    lector allá — por eso el bucket se llama `sin_lector_en_este_repo`.
  * La forma 3 se detecta sólo en su variante medible: parseo shell sin corte
    de comentario SOBRE una clave cuya línea canónica sí tiene comentario. Un
    parseo que falle por indentación o por tipo no se ve.

Salida: JSON en stdout. Exit 0 sin hallazgos, 1 con hallazgos, 2 error.

Reproducir:
    python3 scripts/config_knob_census.py
    python3 scripts/config_knob_census.py --form 4 --list
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cos_lib.measurement import Census  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
CANONICAL = REPO / "cognitive-os.yaml"

# Directorios donde puede vivir un consumidor de configuración.
CODE_DIRS = ("hooks", "scripts", "cos_lib", "lib", "packages", "cmd", ".claude", ".codex", ".opencode")
TEST_DIRS = ("tests",)
DOC_DIRS = ("docs", "rules", "skills", "templates", "manifests")

CODE_SUFFIXES = {".sh", ".bash", ".py", ".go", ".js", ".ts", ".json", ".yaml", ".yml"}

# Nombres tan comunes que un match no prueba nada. La lista es corta a
# propósito: sólo entra un nombre que ya se vio matchear por casualidad.
GENERIC_KEYS = frozenset(
    {
        "enabled", "name", "path", "mode", "type", "value", "url", "id", "key",
        "level", "version", "description", "command", "when", "timeout", "limit",
        "default", "format", "source", "target", "action", "status", "port",
        "host", "user", "file", "dir", "max", "min", "size", "count", "order",
        "provider", "model", "prompt", "event", "hook", "hooks", "script",
        "args", "env", "tags", "role", "scope", "phase", "project", "reason",
        "on", "off", "true", "false", "note", "notes", "title", "label",
    }
)

# Claves que son plantilla/ejemplo, no perilla: lo que el instalador copia al
# proyecto consumidor. Un consumidor fuera del repo las lee.
EXAMPLE_PATH_PREFIXES = ("project.infrastructure",)


def leaf_keys(node: Any, prefix: str = "") -> list[tuple[str, str, Any]]:
    """(dotted_path, leaf_name, value) por cada hoja escalar del yaml.

    Los elementos de lista se recorren para bajar a sus mappings (una lista de
    hooks tiene claves adentro), pero el índice no forma parte del path.
    """
    out: list[tuple[str, str, Any]] = []
    if isinstance(node, dict):
        for k, v in node.items():
            key = str(k)
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(v, (dict, list)):
                out.extend(leaf_keys(v, path))
            else:
                out.append((path, key, v))
    elif isinstance(node, list):
        for item in node:
            if isinstance(item, (dict, list)):
                out.extend(leaf_keys(item, prefix))
    return out


def load_corpus() -> dict[str, str]:
    corpus: dict[str, str] = {}
    for group in (CODE_DIRS, TEST_DIRS, DOC_DIRS):
        for d in group:
            root = REPO / d
            if not root.is_dir():
                continue
            for p in root.rglob("*"):
                if not p.is_file() or p.is_symlink():
                    continue
                if p.suffix and p.suffix not in CODE_SUFFIXES and p.suffix != ".md":
                    continue
                if p.suffix == "" and p.parent.name not in ("hooks", "scripts", "bin"):
                    continue
                try:
                    corpus[str(p.relative_to(REPO))] = p.read_text(errors="replace")
                except OSError:
                    continue
    return corpus


# DOS tokenizadores, no uno. El primero corta en el guion y el segundo no: una
# clave como `acceptance-criteria` es invisible para el primero, y una como
# `lock_timeout_seconds` embebida en un token con guion es invisible para el
# segundo. Con uno solo el censo inventa huérfanas — se descubrió midiendo.
_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_TOKEN_HYPHEN = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*")


def build_index(corpus: dict[str, str]) -> dict[str, list[str]]:
    """token -> archivos que lo contienen. Una pasada, no una por clave."""
    idx: dict[str, set[str]] = {}
    for rel, text in corpus.items():
        for tok in set(_TOKEN.findall(text)) | set(_TOKEN_HYPHEN.findall(text)):
            idx.setdefault(tok, set()).add(rel)
    return {k: sorted(v) for k, v in idx.items()}


def bucket_of(rel: str) -> str:
    top = rel.split("/", 1)[0]
    if top in TEST_DIRS:
        return "test"
    if top in CODE_DIRS:
        return "code"
    return "doc"


def census_orphans(corpus: dict[str, str]) -> tuple[Census, list[dict[str, Any]]]:
    """Forma 4: claves declaradas que nadie lee."""
    import yaml

    index = build_index(corpus)
    data = yaml.safe_load(CANONICAL.read_text())
    keys = leaf_keys(data)
    seen: dict[str, tuple[str, Any]] = {}
    for path, leaf, val in keys:
        seen.setdefault(leaf, (path, val))

    buckets = {"leida_en_codigo": 0, "solo_en_tests": 0, "sin_lector_en_este_repo": 0}
    blind = {"nombre_generico_no_discriminable": 0, "plantilla_para_consumidor_externo": 0}
    details: list[dict[str, Any]] = []

    for leaf, (path, val) in sorted(seen.items()):
        if leaf in GENERIC_KEYS or len(leaf) < 5:
            blind["nombre_generico_no_discriminable"] += 1
            continue
        if any(path.startswith(p) for p in EXAMPLE_PATH_PREFIXES):
            blind["plantilla_para_consumidor_externo"] += 1
            continue
        hits = {"code": [], "test": [], "doc": []}
        for rel in index.get(leaf, ()):  # índice de tokens, no re-escaneo por clave
            hits[bucket_of(rel)].append(rel)
        if hits["code"]:
            buckets["leida_en_codigo"] += 1
            continue
        if hits["test"]:
            buckets["solo_en_tests"] += 1
            details.append({"key": path, "leaf": leaf, "value": val, "form": 4,
                            "verdict": "solo_en_tests", "tests": hits["test"][:5]})
            continue
        buckets["sin_lector_en_este_repo"] += 1
        details.append({"key": path, "leaf": leaf, "value": val, "form": 4,
                        "verdict": "sin_lector_en_este_repo", "docs": hits["doc"][:5]})

    c = Census(
        subject="claves declaradas en cognitive-os.yaml y su lector",
        sources=("cognitive-os.yaml", *CODE_DIRS, *TEST_DIRS, *DOC_DIRS),
        buckets=buckets,
        blind=blind,
        how="python3 scripts/config_knob_census.py --form 4",
    )
    return c, details


CFG_ASSIGN = re.compile(
    r'^\s*(?:local\s+)?([A-Za-z_][A-Za-z0-9_]*)=(["\']?)([^"\'\n]*cognitive-os\.yaml)\2\s*$',
    re.M,
)
# Dos idiomas para el mismo fallback, y el segundo se descubrio el 2026-08-20
# midiendo: concurrent-write-guard-codex-proxy.sh usa `[ -f "$X" ] || X=...`,
# sin el `!`, y se contaba como "sin fallback" teniendo uno. Un censo que
# reporta un falso positivo no mide, opina.
FALLBACK = re.compile(r'(!\s*-f\s+"?\$\{?[A-Za-z_])|(\[\s*-f\s+"?\$\{?[A-Za-z_][^\]]*\]\s*\|\|)', re.M)


def census_paths(corpus: dict[str, str]) -> tuple[Census, list[dict[str, Any]]]:
    """Formas 1 y 3 en shell: a qué archivo apunta la lectura, y si el parseo llega."""
    buckets = {"apunta_al_canonico": 0, "apunta_a_inexistente_sin_fallback": 0,
               "inexistente_con_fallback_al_canonico": 0}
    blind = {"ruta_no_resoluble_estaticamente": 0}
    details: list[dict[str, Any]] = []

    canon_lines = CANONICAL.read_text().splitlines()

    for rel, text in corpus.items():
        if bucket_of(rel) != "code" or not rel.endswith((".sh", ".bash")):
            continue
        for m in CFG_ASSIGN.finditer(text):
            var, _, raw = m.group(1), m.group(2), m.group(3)
            line_no = text[: m.start()].count("\n") + 1
            tail = "\n".join(text.splitlines()[line_no : line_no + 3])
            has_fb = bool(FALLBACK.search(tail)) and "cognitive-os.yaml" in tail
            if ".cognitive-os/cognitive-os.yaml" in raw or "$COGNITIVE_OS_DIR/cognitive-os.yaml" in raw:
                exists = (REPO / ".cognitive-os" / "cognitive-os.yaml").exists()
                if exists:
                    buckets["apunta_al_canonico"] += 1
                    continue
                if has_fb:
                    buckets["inexistente_con_fallback_al_canonico"] += 1
                    continue
                keys = sorted(set(re.findall(r"grep[^\n]*?'([a-z_]+):'", text)
                                  + re.findall(r'grep[^\n]*?"([a-z_]+):"', text)))
                buckets["apunta_a_inexistente_sin_fallback"] += 1
                details.append({"file": rel, "line": line_no, "var": var, "form": 1,
                                "points_to": raw, "keys_parsed": keys,
                                "verdict": "lee un archivo que no existe en ningún checkout"})
            elif "cognitive-os.yaml" in raw:
                buckets["apunta_al_canonico"] += 1
            else:
                blind["ruta_no_resoluble_estaticamente"] += 1

    # Forma 3: parseo sin corte de comentario sobre una clave cuya línea
    # canónica SÍ tiene comentario de fin de línea.
    for rel, text in corpus.items():
        if bucket_of(rel) != "code" or not rel.endswith((".sh", ".bash")):
            continue
        # Un pipeline shell partido con `\` es UNA sentencia: el corte del
        # comentario puede caer en la linea siguiente al sed. Medir por linea
        # marcaba como rotos a hooks que cortan bien.
        joined = re.sub(r"\\\n\s*", " ", text)
        for line in joined.splitlines():
            mm = re.search(r"sed\s+'s/\.\*([a-z_]+):\[\[:space:\]\]\*//'", line)
            if not mm:
                continue
            key = mm.group(1)
            if re.search(r"s/\[\[:space:\]\]\*#\.\*//|s/#\.\*//|cut\s+-d'?#", line):
                continue
            canon = [ln for ln in canon_lines if re.match(rf"^\s*{re.escape(key)}:", ln)]
            with_comment = [ln for ln in canon if re.search(r":\s*\S.*\s#", ln)]
            if with_comment:
                details.append({"file": rel, "form": 3, "key": key,
                                "canonical_line": with_comment[0].strip(),
                                "verdict": "el parseo se lleva el comentario pegado al valor"})

    c = Census(
        subject="lecturas shell de cognitive-os.yaml y el archivo al que apuntan",
        sources=tuple(CODE_DIRS),
        buckets=buckets,
        blind=blind,
        how="python3 scripts/config_knob_census.py --form 1",
    )
    return c, details


# ── prueba de giro ───────────────────────────────────────────────────────────
# Un hallazgo estático dice "parece desconectada". Esto dice "está": se gira la
# perilla en una copia de usar y tirar, se corre EL BLOQUE REAL del hook (se
# extrae del archivo, no se transcribe: una transcripción envejece) y se mira
# si el comportamiento cambia.

PROOFS = (
    {
        "hook": "hooks/concurrent-write-guard.sh",
        "knob": "lock_timeout_seconds",
        "begin": "# Read lock timeout from config",
        "var": "LOCK_TIMEOUT",
        "default": "300",
        "turned": "7",
        "shipped": "300",
        "canonical_comment": "        # Lock auto-expires after 5 minutes",
    },
    {
        "hook": "hooks/concurrent-write-guard-codex-proxy.sh",
        "knob": "lock_timeout_seconds",
        "begin": "LOCK_TIMEOUT=300",
        "var": "LOCK_TIMEOUT",
        "default": "300",
        "turned": "7",
        "shipped": "300",
        "canonical_comment": "        # Lock auto-expires after 5 minutes",
    },
    {
        # Perilla invertida: el default del hook es "apagado" (variable vacía) y
        # sólo enciende si el archivo dice true. Antes del arreglo el hook nunca
        # la veía; después la ve, y el valor que trae el canónico es `true`.
        "hook": "hooks/infra-health.sh",
        "knob": "smart_start",
        "begin": 'smart_start_enabled=""',
        "var": "smart_start_enabled",
        "default": "(vacío = apagado)",
        "turned": "true",
        "shipped": "true",
        "canonical_comment": "              # Lazy-load Docker services when skills need them",
    },
    {
        "hook": "hooks/session-init.sh",
        "knob": "max_concurrent",
        "begin": "MAX_CONCURRENT=10",
        "var": "MAX_CONCURRENT",
        "default": "10",
        "turned": "3",
        "shipped": "10",
        "canonical_comment": "               # Maximum simultaneous sessions",
    },
    {
        # Forma 3 pura: el archivo que lee es el canónico de la raíz, la clave
        # está, y el comentario de fin de línea se pega al valor.
        "hook": "hooks/predev-completeness-check.sh",
        "knob": "phase",
        "begin": 'PHASE="reconstruction"',
        "var": "PHASE",
        "default": "reconstruction",
        "turned": "production",
        "shipped": "reconstruction",
        "canonical_comment": "     # reconstruction | stabilization | production | maintenance",
    },
    {
        # Forma 3 pura, y con padre: el parseo hace `grep -A2 'parry:'`, así que
        # la clave sólo existe bajo ese bloque.
        "hook": "hooks/parry-scan.sh",
        "knob": "enabled",
        "parent": "parry",
        "begin": "# Check if parry is enabled in config",
        "var": "PARRY_ENABLED",
        "default": "(vacío = no apaga)",
        "turned": "false",
        "shipped": "false",
        "canonical_comment": "                   # Set to true after installing parry-guard",
    },
)


def _extract_block(text: str, begin: str) -> str:
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if begin in ln:
            start = i
            break
    else:
        return ""
    depth = 0
    out = []
    for ln in lines[start:]:
        out.append(ln)
        stripped = ln.strip()
        if stripped.startswith("if ") or stripped == "if":
            depth += 1
        elif stripped == "fi" or stripped.startswith("fi "):
            depth -= 1
            if depth <= 0 and len(out) > 1:
                break
    return "\n".join(out)


def run_proof() -> list[dict[str, Any]]:
    import os
    import shutil
    import subprocess
    import tempfile

    results = []
    for spec in PROOFS:
        hook = REPO / spec["hook"]
        hook_text = hook.read_text()
        block = _extract_block(hook_text, spec["begin"])
        if block and "CONFIG_FILE=" not in block:
            # El bloque usa CONFIG_FILE definido más arriba: se trae la
            # asignación real del hook, no una copia escrita a mano.
            for ln in hook_text.splitlines():
                if ln.startswith("CONFIG_FILE="):
                    block = ln + "\n" + block
                    break
        if not block:
            results.append({"hook": spec["hook"], "error": "no se pudo extraer el bloque"})
            continue
        # El subproceso HEREDA el entorno del padre. Se saca la variable de
        # escritura protegida antes de medir para que no contamine la corrida.
        env = dict(os.environ)
        env.pop("COS_ALLOW_PROTECTED_CONFIG_WRITE", None)
        parent = spec.get("parent", "session")
        line_c = f"  {spec['knob']}: {spec['turned']}{spec['canonical_comment']}"
        line_nc = f"  {spec['knob']}: {spec['turned']}"
        line_ship = f"  {spec['knob']}: {spec['shipped']}{spec['canonical_comment']}"
        scenarios = {
            "A_canonico_raiz_como_en_la_realidad": {"cognitive-os.yaml": line_c},
            "B_dot_cognitive_os_con_comentario": {".cognitive-os/cognitive-os.yaml": line_c},
            "C_dot_cognitive_os_sin_comentario": {".cognitive-os/cognitive-os.yaml": line_nc},
            # Las dos direcciones. D y E prueban que conectar la perilla no
            # movió el default: D sin ningún archivo (rige el default escrito en
            # el hook), E con el canónico tal como el repo lo versiona.
            "D_sin_archivo_rige_el_default_del_hook": {},
            "E_canonico_con_el_valor_que_el_repo_versiona": {"cognitive-os.yaml": line_ship},
        }
        obs = {}
        for name, files in scenarios.items():
            tmp = Path(tempfile.mkdtemp(prefix="knob-"))
            try:
                for rel, content in files.items():
                    fp = tmp / rel
                    fp.parent.mkdir(parents=True, exist_ok=True)
                    fp.write_text(f"{parent}:\n{content}\n")
                # Algunos hooks nombran la raíz `_PROJECT_DIR` (parry-scan) y
                # otros `PROJECT_DIR`. Se definen las dos: la que el bloque no
                # use queda inerte, y así el arnés no depende del nombre.
                # Algunos bloques deciden y SALEN (parry-scan hace `exit 0`
                # cuando la perilla dice false). Un `echo` al final del script
                # nunca se ejecutaria y el arnes leeria vacio justo cuando la
                # perilla FUNCIONA. El trap EXIT emite el valor por los dos
                # caminos, y `salio_temprano` distingue uno del otro.
                script = (f'PROJECT_DIR="{tmp}"\n_PROJECT_DIR="{tmp}"\n'
                          f'trap \'echo "__VALUE__=${{{spec["var"]}}}"\' EXIT\n'
                          f'{block}\necho "__REACHED_END__=1"\n')
                r = subprocess.run(["bash", "-c", script], capture_output=True,
                                   text=True, env=env)
                val = ""
                reached_end = False
                for ln in r.stdout.splitlines():
                    if ln.startswith("__VALUE__="):
                        val = ln.split("=", 1)[1]
                    elif ln.startswith("__REACHED_END__="):
                        reached_end = True
                obs[name] = val if reached_end else f"{val} [salio_temprano]"
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
        results.append({
            "hook": spec["hook"], "knob": spec["knob"],
            "default_hardcodeado": spec["default"], "valor_girado": spec["turned"],
            "valor_que_el_repo_versiona": spec["shipped"],
            "observado": obs,
            "perilla_conectada_en_la_realidad": obs.get("A_canonico_raiz_como_en_la_realidad") == spec["turned"],
            "default_intacto": obs.get("E_canonico_con_el_valor_que_el_repo_versiona") == spec["shipped"],
        })
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--form", choices=["1", "3", "4", "all"], default="all")
    ap.add_argument("--list", action="store_true", help="imprime el detalle por hallazgo")
    ap.add_argument("--prove", action="store_true",
                    help="gira la perilla en una copia de usar y tirar y mira si cambia algo")
    args = ap.parse_args()

    if not CANONICAL.is_file():
        print(json.dumps({"error": f"no existe {CANONICAL}"}), file=sys.stderr)
        return 2

    if args.prove:
        print(json.dumps({"pruebas_de_giro": run_proof()}, indent=2, ensure_ascii=False))
        return 0

    corpus = load_corpus()
    out: dict[str, Any] = {"corpus_files": len(corpus)}
    findings: list[dict[str, Any]] = []

    if args.form in ("4", "all"):
        c4, d4 = census_orphans(corpus)
        out["forma_4_claves_sin_lector"] = {
            "poblacion": c4.population, "medibles": c4.measurable,
            "buckets": dict(c4.buckets), "ciegos": dict(c4.blind),
            "how": c4.how, "hallazgo_real": c4.is_a_finding("sin_lector_en_este_repo"),
        }
        findings += d4
    if args.form in ("1", "3", "all"):
        c1, d1 = census_paths(corpus)
        out["forma_1_y_3_lecturas"] = {
            "poblacion": c1.population, "medibles": c1.measurable,
            "buckets": dict(c1.buckets), "ciegos": dict(c1.blind), "how": c1.how,
        }
        findings += d1

    if args.list:
        out["hallazgos"] = findings
    out["total_hallazgos"] = len(findings)
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())

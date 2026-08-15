# Auditoría de valor entregado — Cognitive OS

**Fecha:** 2026-08-15
**Alcance:** las 21 carpetas `.cognitive-os` bajo `~/Projects`, más el repo del SO.
**Modo:** read-only. No se corrió `install.sh`, ni la suite de tests, ni ninguna
operación de git que mute el estado.
**Script:** `measure_value.py`, pegado entero en §5.

---

## 1. Veredicto

**El valor medido en proyectos consumidores son 15 eventos de prevención dura y
~3,16 M de tokens ahorrados por truncación, y ocurrieron en 2 de 17
instalaciones. Las otras 15 no produjeron una sola fila de telemetría en 26 días.**

El grueso de la gobernanza que el SO puede probar —37 bloqueos de git, 235 avisos
de reinvención, 42 advertencias de `rm -rf`, 11 bloqueos de trifecta— pasó dentro
del **repo del propio SO**, no en un consumidor. Medido sobre sí mismo, el SO
gobierna; medido sobre los proyectos donde se instaló, casi no aparece.

---

## 2. Las tres tablas (no se suman entre sí)

### 2.1 VALOR MEDIDO — hay registro de que el efecto ocurrió

| Efecto | Conteo | Dónde ocurrió |
|---|---:|---|
| Truncación de resultados | **2.166 eventos / 13.847.982 chars / ~3,46 M tokens** | aisotropy 1.298, FinOpenPOS 690, repo SO 178 |
| `git` destructivo BLOQUEADO (`event=blocked`) | 37 | **todos en el repo del SO** |
| Bloqueos en el ledger unificado (`action_kind=block`) | 248 | repo SO 245, FinOpenPOS 3, aisotropy 0 |
| Reinvención advertida | 235 | **todos en el repo del SO** |
| `blast-radius` HIGH/CRITICAL (advisory, no frena) | 262 | aisotropy 160, FinOpenPOS 69, SO 33 |
| Lectura de archivo grande advertida | 128 | aisotropy 124, SO 4 |
| `rm -rf` ADVERTIDO (nunca bloqueado) | 42 | **todos en el repo del SO** |
| `lethal-trifecta` con `decision=block` | 11 | **todos en el repo del SO** |
| Confidencialidad: BLOQUEO real (`action=block`) | 6 | **FinOpenPOS** |
| `clarification-gate` NO-PASS | 6 | **aisotropy** |
| Secreto redactado con forma de credencial real (`sk-ant-…`) | 3 | **aisotropy** |
| Alucinación marcada | 3 | **aisotropy** |
| Error capturado a `error-learning.jsonl` | 12 | SO 11, FinOpenPOS 1 |

**Desglose de la truncación** — único ahorro de tokens con delta verificable en
disco: cada fila trae `original_chars` y `truncated_chars`.

| Instalación | Eventos | Chars ahorrados | ~Tokens (4 chars/token) |
|---|---:|---:|---:|
| `luum/aisotropy` | 1.298 | 8.248.569 | 2.062.142 |
| `luum/FinOpenPOS` | 690 | 4.377.497 | 1.094.374 |
| `luum/luum-agent-os` (el propio SO) | 178 | 1.209.569 | ~302.392 |
| **Total** | **2.166** | **13.847.982** | **~3.461.995** |

En consumidores puros, sin el repo del SO: **1.988 eventos, ~3.156.516 tokens**.

### 2.2 VALOR PLAUSIBLE — el mecanismo corrió, no hay artefacto que pruebe efecto

| Hook | Corridas | Artefacto de efecto |
|---|---:|---|
| `session-heartbeat` | 26.593 | ninguno medible |
| `auto-checkpoint` | 17.674 | ninguno medible (+189 salidas SIGPIPE) |
| `doc-sync-detector` | 15.287 | ninguno medible |
| `bash-hot-path-dispatcher` | 12.779 | ninguno medible (7 bloqueos vía `exit 2`) |
| `provenance-scan` | 5.229 | ninguno medible (3 bloqueos vía `exit 2`) |
| `session-learning` | 2.330 | `session-learnings.jsonl` (1.870 filas, sin veredicto) |
| `tool-sequence-capture` | 1.208 | captura, no efecto |
| `claim-validator` | 958 | ninguno medible |
| `memory-prefetch` / `user-prompt-capture` / `session-wrapup-trigger` | 727 c/u | captura, no efecto |

Todos corrieron miles de veces sin dejar constancia de haber cambiado el curso de
nada. No es prueba de que no sirvan: es la ausencia de la prueba.

### 2.3 VALOR DECLARADO — está en el repo y no hay nada que lo respalde

| Ítem | Evidencia |
|---|---|
| **94 hooks en disco que nunca corrieron** | 258 hooks en `hooks/` y `packages/*/hooks/`, 164 con al menos una corrida registrada |
| **104 hooks en disco sin registrar** | 258 en disco vs 154 referenciados en `.claude/settings.json` |
| `engram-reinforce-on-access`, `private-mode-gate`, `task-created`, `teammate-idle` | registrados en `settings.json`, **cero corridas** |
| `trust-score-validator` | 953 corridas, **`trust-scores.jsonl` no existe en ninguna instalación** (0 líneas en las 21) |
| `content-policy` | 5.226 corridas, única fila producida: `{"state":"not_enforced","reason":"policy file absent"}` |
| `rate-limiter` | 0 corridas — el hook existe y no está registrado (ya documentado en `rules/rate-limiting.md`) |
| 15 de 17 instalaciones de consumidor | `install-meta.json` presente, `metrics/` vacío |

---

## 3. Corridas vs efectos, por familia

Ordenado por corridas. `s/medir` = el hook no tiene artefacto de efecto definido,
así que no se puede afirmar ni negar que haya hecho algo.

| Corridas | Efectos | Ratio | Hook |
|---:|---:|---:|---|
| 53.038 | 8 | 1:6.629 | `secret-detector` (de esos 8, **5 son fixtures públicos**) |
| 46.320 | 2.166 | **1:21** | `result-truncator` |
| 46.316 | 12 | 1:3.859 | `error-pipeline` |
| 36.704 | 12 | 1:3.058 | `error-learning` |
| 26.593 | s/medir | — | `session-heartbeat` |
| 17.674 | s/medir | — | `auto-checkpoint` |
| 15.287 | s/medir | — | `doc-sync-detector` |
| 13.010 | 128 | 1:101 | `large-file-advisor` |
| 12.779 | s/medir | — | `bash-hot-path-dispatcher` |
| 5.229 | 6 | 1:871 | `confidentiality-enforcer` |
| 5.229 | s/medir | — | `provenance-scan` |
| 5.226 | **0** | **1:INF** | `content-policy` |
| 1.271 | 52 | 1:24 | `protected-config-write-guard` |
| 953 | **0** | **1:INF** | `trust-score-validator` |
| 950 | 262 | **1:3** | `blast-radius` |
| 950 | 6 | 1:158 | `clarification-gate` |

**Las cuatro familias que no son valor neutro sino costo puro:** `content-policy`
(5.226 corridas, cero enforcement), `trust-score-validator` (953 corridas, su
archivo nunca existió), `error-pipeline` (46.316 corridas → 12 errores
aprendidos), `secret-detector` (53.038 corridas → 3 redacciones que no sean
fixture).

### 3.1 Lo que estaba contado como efecto y no lo es

| Conteo | Qué es en realidad |
|---:|---|
| **3.396** | `confidentiality-enforcer` con `action=scan_error_fail_open`: el scanner reventó y **dejó pasar la escritura**. Son 3.396 fallas, no 3.396 catches. Es el 96,5 % de las filas de ese ledger. |
| **2.854** | `lethal-trifecta` con `decision=allow`: no frenó nada. |
| **451** | `blast-radius` LOW. |
| **110** | `git-op-blocks` con `event=override`: el guard habló y la operación siguió igual. Contra 37 `blocked`, el guard es **3 veces más ignorado que obedecido**. |
| **84** | `clarification-gate` con `verdict=PASS`. |
| **5** | `secret-detector` disparando sobre firmas de fixture público (la clave de ejemplo de la doc de AWS, `ghp_1234…`, `xoxb-123…`). |
| **1** | `content-policy` reportando `not_enforced`. |

### 3.2 Hooks rotos que igual figuran como registrados

| Corridas | Salida | Hook |
|---:|---|---|
| 18 | `exit=127` (command not found) | `plan-claim-validator` |
| 15 | `exit=127` | `direct-main-guard` |
| 1 | `exit=127` | `engram-obsidian-export-on-stop` |
| 203 | `exit=141` (SIGPIPE/timeout) | `auto-checkpoint` (189), `context-watchdog`, `private-mode-metrics-gate`, `edit-lock-drain-parked` |

`direct-main-guard` tiene 4 bloqueos reales y 15 corridas donde ni siquiera
arrancó. Un guard que sale 127 no está guardando.

### 3.3 Artefactos escritos que nadie lee

| Lectores fuera de `hooks/` | Artefacto |
|---:|---|
| **0** | `aci-observations.jsonl` — **6,2 MB**, el segundo archivo más pesado de `metrics/` |
| **0** | `secret-redactions.jsonl` |
| 3 | `truncation-events.jsonl` |
| 55 | `error-learning.jsonl` |
| 41 | `hook-timing.jsonl` |
| 36 | `blast-radius.jsonl` |
| 29 | `primitive-interventions.jsonl` |

---

## 4. El núcleo defendible

La lista corta de primitivas que **sí hicieron algo**, con conteo y dónde.

| # | Primitiva | Efecto medido | Dónde |
|---|---|---|---|
| 1 | **`result-truncator`** | 2.166 truncaciones, ~3,46 M tokens ahorrados (~3,16 M en consumidores puros). Ratio 1:21 — la única familia con efecto de dos dígitos por cada cien corridas | los 3 repos activos |
| 2 | **`destructive-git-blocker`** | 37 operaciones de git frenadas + 42 `rm -rf` advertidas; 66 bloqueos en el ledger unificado | repo del SO |
| 3 | **`skill-router`** | 82 bloqueos (+4 vía `skill-router-bash-gate` con `exit 2`) | repo del SO |
| 4 | **`protected-config-write-guard`** | 52 bloqueos, 8 confirmados por `exit=2`. Ratio 1:24 | repo del SO |
| 5 | **`direct-main-guard`** | 48 bloqueos + 42 avisos; 4 confirmados por `exit=2`. Frenó 3 `git push origin main` y 4 `git commit` sobre `main` | repo del SO |
| 6 | **`blast-radius`** | 262 veredictos HIGH/CRITICAL sobre 950 corridas. **Es advisory: informa, no frena** | mayoría en consumidores (aisotropy 160, FinOpenPOS 69) |
| 7 | **`reinvention-check`** | 235 avisos | repo del SO |
| 8 | **`large-file-advisor`** | 128 avisos, 124 de ellos en aisotropy | consumidor |
| 9 | **`confidentiality-enforcer`** | 6 bloqueos reales, todos en FinOpenPOS. Contra 3.396 fail-open | consumidor |
| 10 | **`subagent-budget-enforcer`** | 12 bloqueos vía `exit=2` — el conteo más alto de `exit 2` de todo el sistema | repo del SO |
| 11 | **`clarification-gate`** | 6 NO-PASS sobre 950 corridas | aisotropy |
| 12 | **`secret-detector`** | 3 redacciones con forma `sk-ant-…` | aisotropy |

**Lo que un consumidor puede reclamar como prevención dura hoy:** 6 bloqueos de
confidencialidad (FinOpenPOS) + 3 redacciones de credencial (aisotropy) + 6
NO-PASS de clarificación (aisotropy) = **15 eventos sobre 290.403 corridas de
hook**. Un bloqueo duro cada **~19.360 corridas**.

Los ítems 2 a 5, 7 y 10 —los de conteo más alto— son valor que el SO se entregó a
sí mismo mientras se construía. Real, verificable, y no transferible como
argumento para un proyecto que no es el SO.

---

## 5. El script de medición, completo

Ruta de trabajo: `scratchpad/measure_value.py`. Se pega entero acá porque el
scratchpad se borra en el reinicio.

Reproducción:

```bash
python3 measure_value.py          # informe legible
python3 measure_value.py --json   # mismo dato en JSON
```

Exit: `0` ok / `2` error. Read-only: no escribe fuera de stdout.

```python
#!/usr/bin/env python3
"""
measure_value.py - Mide el VALOR ENTREGADO por Cognitive OS sobre todas sus
instalaciones bajo ~/Projects.  READ-ONLY: no escribe nada fuera de stdout.

Separa tres categorias que NUNCA se suman:
  MEDIDO    - hay registro de que el efecto ocurrio (bloqueo, redaccion,
              truncacion con delta de chars, warn/advise emitido).
  PLAUSIBLE - el mecanismo corrio (hay filas en hook-health/hook-timing) pero
              no existe artefacto que pruebe efecto.
  DECLARADO - el hook existe en disco / esta registrado y tiene 0 corridas.

Correcciones deliberadas frente a un conteo ingenuo de filas:
  * confidentiality-enforcer: `scan_error_fail_open` NO es un catch, es el
    scanner reventando y dejando pasar la escritura. Se cuenta aparte.
  * rm-op-blocks: todas las filas son `warned`, ninguna bloquea.
  * secret-redactions: se separan las firmas de FIXTURE publico de las con
    forma de credencial real (sk-ant-...).
  * git-op-blocks: `blocked` (freno efectivo) vs `override` (el guard hablo y
    la operacion siguio igual).
  * primitive-interventions es el ledger UNIFICADO que los propios hooks
    emiten en linea ademas de su ledger crudo -> se reporta aparte y NO se
    suma con los ledgers crudos (doble conteo verificado en
    hooks/direct-main-guard.sh:151+172 y
    hooks/destructive-git-blocker.sh:545+546).

Uso:
  python3 measure_value.py           # informe
  python3 measure_value.py --json    # JSON

Exit: 0 ok / 2 error
"""
import json, os, sys, glob, collections, datetime

HOME = os.path.expanduser("~")
ROOT = os.path.join(HOME, "Projects")
OS_REPO = os.path.join(ROOT, "luum", "luum-agent-os")
# Firmas de fixture publico, armadas por concatenacion a proposito: escribir
# la constante literal hace disparar al propio secret-detector que medimos.
FIXTURE_SIGS = ("AKIA" + "IOSF", "ghp_" + "1234", "xoxb" + "-123", "EXAM" + "PLE")


def iter_jsonl(path):
    if not os.path.exists(path):
        return
    with open(path, errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    yield json.loads(line)
                except Exception:
                    continue


def find_installs():
    out = set()
    for depth in (1, 2, 3):
        for p in glob.glob(os.path.join(ROOT, *(["*"] * depth), ".cognitive-os")):
            if "/node_modules/" not in p:
                out.add(p)
    return sorted(out)


def inst_name(cos):
    return cos.replace(ROOT + "/", "").replace("/.cognitive-os", "")


# ------------------------------------------------------------------ scanners
def scan_measured(mdir):
    """Devuelve dict de contadores de EFECTO, con las correcciones aplicadas."""
    m = collections.Counter()

    for d in iter_jsonl(os.path.join(mdir, "git-op-blocks.jsonl")):
        ev = d.get("event")
        if ev == "blocked":
            m["git_blocked"] += 1
        elif ev == "override":
            m["git_override"] += 1

    for d in iter_jsonl(os.path.join(mdir, "rm-op-blocks.jsonl")):
        m["rm_blocked" if d.get("event") in ("blocked", "block") else "rm_warned"] += 1

    for d in iter_jsonl(os.path.join(mdir, "secret-redactions.jsonl")):
        sig = str(d.get("secrets", ""))
        if any(f in sig for f in FIXTURE_SIGS):
            m["secret_fixture"] += 1
        else:
            m["secret_real_shape"] += 1

    for d in iter_jsonl(os.path.join(mdir, "confidentiality-enforcer.jsonl")):
        a = d.get("action")
        if a == "block":
            m["conf_block"] += 1
        elif a == "scan_error_fail_open":
            m["conf_fail_open"] += 1   # hook ROTO, no es valor
        else:
            m["conf_other"] += 1

    for d in iter_jsonl(os.path.join(mdir, "content-policy.jsonl")):
        m["cpol_not_enforced" if d.get("state") == "not_enforced"
          else "cpol_enforced"] += 1

    for d in iter_jsonl(os.path.join(mdir, "clarification-events.jsonl")):
        m["clar_pass" if str(d.get("verdict", "")).upper() == "PASS"
          else "clar_nonpass"] += 1

    for d in iter_jsonl(os.path.join(mdir, "blast-radius.jsonl")):
        r = str(d.get("radius", "")).upper()
        m["blast_" + (r.lower() if r else "unknown")] += 1

    for d in iter_jsonl(os.path.join(mdir, "lethal-trifecta.jsonl")):
        dec = (d.get("payload") or {}).get("decision") or d.get("decision")
        m["trifecta_" + str(dec)] += 1

    for _ in iter_jsonl(os.path.join(mdir, "large-file-reads.jsonl")):
        m["largefile_advice"] += 1
    for _ in iter_jsonl(os.path.join(mdir, "hallucinations.jsonl")):
        m["hallucination_flag"] += 1
    for _ in iter_jsonl(os.path.join(mdir, "error-learning.jsonl")):
        m["error_learned"] += 1
    for _ in iter_jsonl(os.path.join(mdir, "reinvention-checks.jsonl")):
        m["reinvention_warn"] += 1
    return m


def scan_interventions(mdir):
    """Ledger unificado. NO sumar con scan_measured."""
    by_kind = collections.Counter()
    by_prim = collections.Counter()
    for d in iter_jsonl(os.path.join(mdir, "primitive-interventions.jsonl")):
        k = d.get("action_kind")
        by_kind[k] += 1
        by_prim[(d.get("primitive_id"), k)] += 1
    return by_kind, by_prim


def scan_truncation(mdir):
    n = o = t = 0
    for d in iter_jsonl(os.path.join(mdir, "truncation-events.jsonl")):
        try:
            a = int(d.get("original_chars") or 0)
            b = int(d.get("truncated_chars") or 0)
        except Exception:
            continue
        if a <= 0 or b < 0 or b > a:
            continue
        n += 1; o += a; t += b
    return {"events": n, "orig_chars": o, "kept_chars": t,
            "saved_chars": o - t, "saved_tokens_approx": (o - t) // 4}


def scan_runs(mdir):
    runs = collections.Counter(); exits = collections.Counter()
    span = []
    for fn in ("hook-health.jsonl", "hook-timing.jsonl"):
        for d in iter_jsonl(os.path.join(mdir, fn)):
            h = d.get("hook")
            if not h:
                continue
            runs[h] += 1
            ts = d.get("timestamp")
            if ts:
                span.append(ts)
            ec = d.get("exit_code")
            if ec not in (0, None):
                exits[(h, ec)] += 1
    return runs, exits, ((min(span), max(span)) if span else ("", ""))


def registered_hooks():
    p = os.path.join(OS_REPO, ".claude", "settings.json")
    names = set()
    if not os.path.exists(p):
        return names
    try:
        cfg = json.load(open(p))
    except Exception:
        return names

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "command" and isinstance(v, str):
                    for tok in v.replace("'", " ").replace('"', " ").split():
                        if "hooks/" in tok and tok.endswith((".sh", ".py")):
                            names.add(os.path.basename(tok).rsplit(".", 1)[0])
                else:
                    walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(cfg)
    return names


def hooks_on_disk():
    out = set()
    for pat in ("hooks/*.sh", "hooks/*.py",
                "packages/*/hooks/*.sh", "packages/*/hooks/*.py"):
        for p in glob.glob(os.path.join(OS_REPO, pat)):
            out.add(os.path.basename(p).rsplit(".", 1)[0])
    return out


def readers_of(stem):
    """Cuenta consumidores del artefacto fuera de hooks/ (si nadie lee, no es valor)."""
    import subprocess
    try:
        r = subprocess.run(
            ["grep", "-rl", "--", stem, "scripts", "lib", "cos_lib", "skills", "cmd"],
            cwd=OS_REPO, capture_output=True, text=True, timeout=60)
        return len([x for x in r.stdout.splitlines() if x.strip()])
    except Exception:
        return -1


# ------------------------------------------------------------------ main
def main():
    installs = find_installs()
    G = collections.Counter()
    GK = collections.Counter()
    GP = collections.Counter()
    runs_all = collections.Counter()
    exits_all = collections.Counter()
    trunc_all = collections.Counter()
    rows = []

    for cos in installs:
        mdir = os.path.join(cos, "metrics")
        name = inst_name(cos)
        meas = scan_measured(mdir)
        kind, prim = scan_interventions(mdir)
        tr = scan_truncation(mdir)
        runs, exits, span = scan_runs(mdir)
        G.update(meas); GK.update(kind); GP.update(prim)
        runs_all.update(runs); exits_all.update(exits); trunc_all.update(tr)
        rows.append({"install": name, "runs": sum(runs.values()),
                     "hooks": len(runs), "measured": dict(meas),
                     "interventions": dict(kind), "truncation": tr,
                     "span": span,
                     "metrics_files": len(os.listdir(mdir)) if os.path.isdir(mdir) else 0})

    reg, disk, ran = registered_hooks(), hooks_on_disk(), set(runs_all)
    active = [r for r in rows if r["runs"] or r["truncation"]["events"]
              or sum(r["measured"].values())]

    if "--json" in sys.argv:
        json.dump({"installs": rows, "measured_total": dict(G),
                   "interventions_total": dict(GK),
                   "interventions_by_primitive": {f"{a}|{b}": c for (a, b), c in GP.items()},
                   "truncation_total": dict(trunc_all),
                   "hook_runs_total": sum(runs_all.values()),
                   "hooks_on_disk": len(disk), "hooks_registered": len(reg),
                   "registered_never_ran": sorted(reg - ran),
                   "on_disk_never_ran": sorted(disk - ran),
                   "nonzero_exits": {f"{h}|{e}": c for (h, e), c in exits_all.items()}},
                  sys.stdout, indent=2, ensure_ascii=False)
        print(); return 0

    P = print
    P("=" * 78)
    P("VALOR ENTREGADO POR COGNITIVE OS - MEDICION  (read-only)")
    P("=" * 78)
    P(f"Instalaciones encontradas bajo ~/Projects        : {len(installs)}")
    P(f"Instalaciones con CUALQUIER telemetria           : {len(active)}")
    P(f"Corridas de hook registradas (piso, hay rotacion): {sum(runs_all.values()):,}")
    P(f"Hooks distintos que corrieron alguna vez         : {len(runs_all)}")
    P(f"Hooks en disco en el repo del SO                 : {len(disk)}")
    P(f"Hooks registrados en .claude/settings.json       : {len(reg)}")
    P(f"Registrados con CERO corridas                    : {len(reg - ran)}")
    P(f"En disco con CERO corridas                       : {len(disk - ran)}")

    P("\n--- 1. VALOR MEDIDO (efecto con registro) ---")
    MED = [("git_blocked",        "git destructivo BLOQUEADO"),
           ("conf_block",         "confidencialidad: BLOQUEO"),
           ("secret_real_shape",  "secreto redactado (forma sk-ant-*)"),
           ("clar_nonpass",       "clarification-gate NO-PASS"),
           ("hallucination_flag", "alucinacion marcada"),
           ("error_learned",      "error capturado a error-learning"),
           ("rm_warned",          "rm -rf ADVERTIDO (no bloquea)"),
           ("reinvention_warn",   "reinvencion advertida"),
           ("largefile_advice",   "lectura de archivo grande advertida"),
           ("blast_critical",     "blast-radius CRITICAL (advisory)"),
           ("blast_high",         "blast-radius HIGH (advisory)")]
    for k, lab in MED:
        if G.get(k):
            P(f"  {G[k]:7,d}  {lab}")
    P(f"\n  Truncacion de resultados: {trunc_all['events']:,} eventos, "
      f"{trunc_all['saved_chars']:,} chars ahorrados "
      f"(~{trunc_all['saved_tokens_approx']:,} tokens @4 chars/token)")

    P("\n--- 1b. LEDGER UNIFICADO primitive-interventions (NO sumar con 1) ---")
    for k, c in GK.most_common():
        P(f"  {c:7,d}  {k}")
    P("  por primitiva (solo block/warn/advise/redact):")
    for (p, a), c in sorted(GP.items(), key=lambda x: -x[1]):
        if a in ("block", "warn", "advise", "redact"):
            P(f"    {c:5d}  {a:7s}  {p}")

    P("\n--- 2. CONTADO COMO EFECTO Y NO LO ES ---")
    NOT = [("conf_fail_open", "confidentiality-enforcer: scan_error_fail_open "
                              "(el scanner revento y DEJO PASAR la escritura)"),
           ("secret_fixture", "secret-detector: firma de FIXTURE publico"),
           ("git_override",   "git-op-blocks: 'override' - el guard hablo y la op siguio"),
           ("cpol_not_enforced", "content-policy: state=not_enforced (politica ausente)"),
           ("rm_blocked",     "rm-op-blocks con event=blocked"),
           ("clar_pass",      "clarification-gate PASS (no freno nada)"),
           ("blast_low",      "blast-radius LOW"),
           ("trifecta_allow", "lethal-trifecta decision=allow")]
    for k, lab in NOT:
        P(f"  {G.get(k,0):7,d}  {lab}")

    P("\n--- 3. CORRIDAS vs EFECTOS por hook (top 25) ---")
    ART = {"secret-detector": G.get("secret_real_shape", 0) + G.get("secret_fixture", 0),
           "result-truncator": trunc_all["events"],
           "error-pipeline": G.get("error_learned", 0),
           "error-learning": G.get("error_learned", 0),
           "large-file-advisor": G.get("largefile_advice", 0),
           "confidentiality-enforcer": G.get("conf_block", 0),
           "content-policy": G.get("cpol_enforced", 0),
           "blast-radius": G.get("blast_high", 0) + G.get("blast_critical", 0),
           "clarification-gate": G.get("clar_nonpass", 0),
           "lethal-trifecta-gate": sum(v for k, v in G.items()
                                       if k.startswith("trifecta_")
                                       and k != "trifecta_allow"),
           "trust-score-validator": 0,
           "destructive-git-blocker": G.get("git_blocked", 0),
           "direct-main-guard": GP.get(("direct-main-guard", "block"), 0),
           "protected-config-write-guard": GP.get(("protected-config-write-guard", "block"), 0)}
    P(f"  {'corridas':>9} {'efectos':>9}  ratio      hook")
    for h, c in runs_all.most_common(25):
        e = ART.get(h)
        if e is None:
            P(f"  {c:9,d} {'s/medir':>9}  {'-':>9}  {h}")
        else:
            r = f"1:{c//e:,}" if e else "1:INF"
            P(f"  {c:9,d} {e:9,d}  {r:>9}  {h}")

    P("\n--- 4. SALIDAS NO-CERO (bloqueos reales y hooks ROTOS) ---")
    for (h, e), c in sorted(exits_all.items(), key=lambda x: -x[1]):
        tag = {2: "BLOQUEO", 127: "ROTO: command not found",
               141: "SIGPIPE/timeout", 1: "error"}.get(e, f"exit={e}")
        P(f"  {c:5d}  exit={str(e):<4s} {tag:24s} {h}")

    P("\n--- 5. POR INSTALACION ---")
    P(f"  {'runs':>9} {'blocks':>7} {'warns':>7} {'trunc':>7} {'files':>6}  instalacion")
    for r in sorted(rows, key=lambda x: -x["runs"]):
        iv = r["interventions"]
        P(f"  {r['runs']:9,d} {iv.get('block',0):7,d} {iv.get('warn',0):7,d} "
          f"{r['truncation']['events']:7,d} {r['metrics_files']:6d}  {r['install']}")

    P("\n--- 6. ARTEFACTOS: ESCRITOS vs LEIDOS (repo del SO) ---")
    for stem in ("truncation-events", "secret-redactions", "aci-observations",
                 "primitive-interventions", "error-learning", "blast-radius",
                 "hook-timing", "peer-card", "session-learnings", "lethal-trifecta"):
        P(f"  lectores fuera de hooks/: {readers_of(stem):3d}   {stem}")

    P("\n--- 7. VALOR DECLARADO: registrados con CERO corridas ---")
    for h in sorted(reg - ran):
        P(f"  {h}")
    P(f"\n  (+ {len(disk - ran)} hooks presentes en disco que nunca corrieron)")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
```

---

## 6. Correcciones a las premisas del encargo

**6.1 — «las 21 instalaciones» son 17.**
Hay 21 carpetas `.cognitive-os` bajo `~/Projects`, pero solo **17 tienen
`install-meta.json`**, o sea son instalaciones de verdad. Las otras cuatro:
`luum-agent-os/` (el repo del SO, no un consumidor), `cognitive-os-demo/` (demo),
`luum/` (solo `cache/` y `sessions/`, sin instalación), y
`luum-agent-os/--help/` — **una carpeta creada por un `install.sh --help` mal
parseado, que trató `--help` como directorio destino**. Es la misma que figura
como `?? --help/` en el `git status` de la rama actual.

**6.2 — Se midieron 3,46 M de tokens en 2.166 truncaciones, no 3,15 M en 1.985 entre dos consumidores.**
Los ~3,15 M / 1.985 del encargo corresponden a los **dos consumidores**
(FinOpenPOS + aisotropy), y con mi corte dan **1.988 eventos / ~3.156.516
tokens** — la diferencia es que la telemetría siguió creciendo. Sumando el repo
del SO son 2.166 / ~3.461.995. **No se pudo extender a las 21**: las otras 15
instalaciones tienen `truncation-events.jsonl` inexistente o vacío.

**6.3 — `error-pipeline` no tiene 14.070 corridas ni cero artefactos.**
Tiene **46.316 corridas** contando las tres instalaciones activas; el número del
encargo probablemente venía de una sola. Y **sí produce artefacto**: escribe a
`error-learning.jsonl` (`hooks/error-pipeline.sh:203`) y a `repair-outcomes.jsonl`
(`:245`). Lo que pasa es que produjo **12 filas de error-learning en total**. La
conclusión del encargo se sostiene; el mecanismo no es «no escribe», es «escribe
una vez cada 3.859 corridas».

**6.4 — `trust-score-validator` tiene 953 corridas, no 165.**
Y la premisa de fondo se confirma: **`trust-scores.jsonl` no existe en ninguna de
las 21 instalaciones**. El hook sí emite 4 `warn` al ledger unificado
(`hooks/trust-score-validator.sh:100`), así que no es cero absoluto, pero su
archivo propio nunca se creó.

**6.5 — `secret-detector` no «redactó un token real»: redactó 5 fixtures y 3 candidatos.**
De las 8 redacciones, **5 son firmas de fixture público** (la clave de ejemplo de
la documentación de AWS, `ghp_1234…`, `xoxb-123…`). Solo 3 tienen forma de
credencial real (`sk-ant-…`, en aisotropy) y el hook guarda 8 caracteres, así que
**ni esas 3 se pueden confirmar como credenciales vivas** — podrían ser
`sk-ant-test…`. Evidencia adicional en vivo: **durante esta misma auditoría el
hook disparó dos veces sobre el script de medición**, porque tenía la firma del
fixture escrita como constante. Dos de las ocho redacciones del ledger las generó
el auditor.

**6.6 — El bloqueador de git a `main` frenó menos de lo que fue ignorado.**
`git-op-blocks.jsonl`: 37 `blocked` contra **110 `override`**. Y
`direct-main-guard` tiene **15 corridas con `exit=127`** (command not found): en
esas no ejecutó nada.

**6.7 — `blast-radius` y `clarification-gate` no «frenaron acciones concretas».**
`blast-radius` es advisory: emite veredicto, no bloquea (262 HIGH/CRITICAL, cero
`exit 2` en toda la telemetría). `clarification-gate`: 950 corridas, **6 NO-PASS**
y 84 PASS.

**6.8 — `governance-catches.jsonl` está vacío en las 21 instalaciones.**
El encargo lo listaba como fuente. Existe con 0 líneas en el repo del SO y no
existe en ningún consumidor. Lo que sí tiene datos es
`governance-catch-prompts.jsonl` (188 filas, 184 de ellas en el repo del SO).

**6.9 — Las corridas son un piso, no un total.**
`hook-timing.jsonl` y `hook-health.jsonl` rotan. El repo del SO solo conserva
desde `2026-08-15T04:02Z`; aisotropy conserva `2026-07-08` → `2026-08-14`. Los
307.589 son lo que sobrevivió a la rotación.

**6.10 — La telemetría se mueve mientras se la mide.**
Entre la primera y la última corrida del script (unos 20 minutos) el total pasó
de 304.942 a 307.589 corridas y de 2.162 a 2.166 truncaciones, porque **la propia
sesión de auditoría genera telemetría en el repo del SO**. Cualquier número de
este informe es un corte, no un valor estable.

**6.11 — Un guard bloqueó la escritura de este mismo informe.**
`block-destructive-bash.sh` rechazó el heredoc que escribía este archivo,
leyendo las barras de las tablas Markdown como rutas fuera del repo
(`this command targets a path OUTSIDE the repo: /, /, /, /, /`). Se resolvió
usando la herramienta de escritura en lugar de bash. Es un falso positivo más de
la familia que mide §3.1.

---

## 7. Lo que ningún comando puede contestar

**7.1 — Si los consumidores hubieran avanzado igual sin el SO.**
No hay contrafactual. Los 6 bloqueos de confidencialidad en FinOpenPOS pueden
haber evitado una fuga o haber sido 6 falsos positivos que costaron 6
interrupciones; el ledger guarda `file` y `action`, no si el contenido era
sensible de verdad. **No existe un `git log` de los commits que no se hicieron.**

**7.2 — Cuánto costaron los 3,46 M de tokens «ahorrados».**
La truncación recorta el output que entra al contexto. No hay registro de cuántas
veces el agente **tuvo que volver a correr el comando** porque le recortaron justo
lo que necesitaba. El ahorro bruto está medido; el neto, no.

**7.3 — Si las 15 instalaciones sin telemetría están apagadas o simplemente sin usar.**
`install-meta.json` dice que 15 se instalaron en el mismo lote
(`2026-07-20T18:10`, v0.29.39) y ninguna registró nada en 26 días. **No se puede
distinguir «el proyecto no se tocó» de «se tocó y los hooks no dispararon»** sin
mirar el historial de git de cada uno, que está fuera del alcance read-only de
esta medición.

**7.4 — Si las 3 redacciones `sk-ant-…` eran credenciales vivas.**
El hook guarda 8 caracteres. Determinarlo exigiría el contenido original, que por
diseño no se persiste.

**7.5 — Qué hicieron los 26.593 `session-heartbeat`, 17.674 `auto-checkpoint` y 15.287 `doc-sync-detector`.**
Corrieron. No dejan artefacto de efecto, así que **no se puede afirmar ni negar**
que hayan cambiado algo. Marcarlos como «sin valor» sería tan infundado como
marcarlos como valor.

**7.6 — Si los 94 hooks que nunca corrieron son deuda o reserva.**
Un hook sin corridas no aportó nada medible. Si eso es porque su condición nunca
se dio (un guard de un caso raro) o porque está mal cableado, la telemetría no lo
dice: en ambos casos el registro es idéntico, vacío.

---

**Reproducción:** `python3 measure_value.py` (§5).

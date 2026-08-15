# QA contrafactual sobre `aisotropy` — qué eventos malos ocurrieron y cuántos previno el SO

**Fecha:** 2026-08-15
**Objeto de prueba:** el SO (este repo)
**Campo de pruebas:** `aisotropy`, consumidor vivo, 607 commits desde 2026-07-01
**Modo:** read-only en los dos repos. Cero escrituras fuera de este archivo.

---

## 1. Veredicto

**De 33 eventos malos reales en 607 commits, el SO previno 0.**

Los 7 casos de enforcement duro que sí hubo en el consumidor (4 redacciones de
secreto + 3 bloqueos de `confidentiality-enforcer`) no corresponden a ninguno de
los 33 eventos: ninguno de ellos llegó a la historia de git de todos modos, y no
hay forma de establecer si había algo que prevenir.

El corpus además es chico y se corrige solo: la mediana entre el commit que
introduce el defecto y el que lo arregla es de **328 segundos**. El repo se
autocorrige en 5 minutos y medio; ningún gate de sesión llega a tiempo.

---

## 2. El corpus: 33 eventos, y los ceros que también son hallazgo

| Familia | N | Comando |
|---|---:|---|
| Reverts reales (`git revert`) | **0** | `git log --since=2026-07-01 --format='%h\|%s'` filtrado por asunto `^Revert ` |
| Fix-ups ≤1h que tocan archivos del commit anterior | **21** | ver §6, bloque E2 |
| Confesiones de claim falso (nuevas, sin solapar con E2) | **7** | ver §6, bloque E6 |
| Roturas de build/formato declaradas | **5** | ver §6, bloque E5 |
| Credenciales que entraron a la historia | **0** | `git log -S` sobre 7 patrones + `git grep` sobre el árbol |
| Rutas de home commiteadas | **0** | `git log -S/Users/` → 3 commits, los 3 son `/Users/runner/` (CI) |
| `.env` commiteado | **0** | `git log --all -- .env` → vacío |
| **Total deduplicado** | **33** | |

### Los ceros, con su evidencia

- **Cero reverts en 607 commits.** Ni uno.
- **Cero secretos.** El árbol tiene dos coincidencias de patrón y las dos son
  legítimas: `.env.example:38` con `sk-ant-REPLACE_ME` y
  `internal/guardrails/redact_test.go:57` con un fixture `ghp_abcdef…`. `.env`
  está en `.gitignore:44` y nunca se commiteó.
- **Cero fugas de ruta privada.** Los 3 commits que tocan `/Users/` escriben
  `/Users/runner/work/...`, la ruta del runner de GitHub Actions, dentro de
  documentación sobre un bug de un wheel upstream.

### El evento verificado independientemente

`d37d6d2` (2026-07-24) metió una violación de `gofmt` — orden de imports en
`internal/o11y/metrics.go`. Sobrevivió **135 commits y 11 días** hasta `4d63653`
(2026-08-04), cuyo asunto dice: *the repo's CI has been red since d37d6d2*.
Reproducible hoy:

```
git show d37d6d2:internal/o11y/metrics.go | gofmt -d   # sale el diff
git show 4d63653:internal/o11y/metrics.go | gofmt -d   # sale vacío
git rev-list --count d37d6d2..4d63653                  # 135
```

Es el único evento del corpus que una máquina podía atrapar de forma
determinista en el momento de la escritura.

---

## 3. Las cuatro categorías

Cada evento tiene una categoría primaria. La ventana de correlación es ±1h
alrededor del commit padre.

| Categoría | Eventos | Qué pasó exactamente |
|---|---:|---|
| **No corrió** | **16** | 16 de los 21 fix-ups tienen, en el cuerpo del commit padre, un claim explícito de verificación (`Verified:`, `Measured before landing`, `build green`, `Proven rather than documented`) y fueron corregidos en menos de una hora. `hooks/orchestrator-claim-gate.sh` existe en el SO y bloquea `git commit`/`push` cuando el mensaje trae claims de alto riesgo sin evidencia independiente. **No está registrado en el consumidor.** Tampoco `plan-claim-validator.sh`. |
| **Corrió y no detectó** | **12** | 5 fix-ups sin claim en el padre + 7 confesiones de claim falso. En esas 12 ventanas corrieron `claim-validator` (441 corridas, 0 detecciones), `trust-score-validator` (441, todas exit 0), `blast-radius` (441, **0 HIGH/CRITICAL en las 21 ventanas**), `completion-gate` (311), `clarification-gate` (441, 0 non-PASS en ventana). En una sola ventana llegaron a correr **6.904** invocaciones de hook sin producir una sola señal. |
| **Detectó y no bloqueó** | **0** | `scope-proportionality` emitió 4 WARN dentro de 3 ventanas, pero por otro motivo (*Fix task deleted files in reconstruction phase*). `blast-radius` produjo 99 CRITICAL + 61 HIGH en todo el repo y ninguno cayó en una ventana de evento; además es advisory por diseño: 441 corridas, 441 con exit 0. |
| **Bloqueó y lo saltearon** | **0** | 98.095 filas de `hook-health.jsonl` con **cero** exit≠0. 141.679 filas de `hook-timing.jsonl` con 3 exit=2 (`confidentiality-enforcer`, 2026-07-08T21:40, 07-17T21:19, 07-17T23:30) y 180 exit=141 (`auto-checkpoint`, SIGPIPE). Ninguno de los 3 bloqueos cae en ventana de evento del corpus. Cero filas de `git-op-blocks.jsonl` atribuibles al consumidor. |
| *(quinta, honesta)* **Sin hook que lo cubra** | **5** | Las 5 roturas de build/formato. En los 257 hooks del SO no hay ninguno que corra `gofmt`, `go vet` o `go build`. La regla §14 delega calidad de Go a CI local, y el gate nativo del consumidor dice explícitamente que `ci.yml` se queda con gofmt/vet/build. |

**Los arreglos son distintos y por eso importa la partición:**

- Los 16 de *no corrió* se arreglan **registrando** un hook que ya existe. Es un
  problema de instalación, no de detección.
- Los 12 de *corrió y no detectó* se arreglan **cambiando el alcance del hook**.
  Caso concreto: `hooks/claim-validator.sh:49` hace
  `[ "$TOOL_NAME" != "Agent" ] && exit 0`. Valida el texto de respuesta de un
  sub-agente, nunca un mensaje de commit. Corrió 441 veces sobre el objeto
  equivocado.
- Los 5 sin cobertura se arreglan **escribiendo el hook**. `gofmt -l` es tres
  líneas de bash en PreToolUse sobre Write/Edit de `*.go`.
- Las categorías 3 y 4 están vacías: **no hay nada que arreglar ahí en el
  consumidor**, y cualquier plan que priorice "endurecer los gates advisory"
  está atacando un cuadrante sin datos.

---

## 4. La brecha de diseño: 13,6 % de superficie

| Métrica | Valor |
|---|---:|
| Hooks disponibles en el SO | 257 |
| Hooks registrados en el consumidor | 37 |
| Cobertura | **13,6 %** |
| Guards/gates del SO sin registrar en el consumidor | **81** |
| Hooks que efectivamente reportaron actividad | 33 (`hook-timing`) / 11 (`hook-health`) |

Entre los 81 sin registrar están los que cubrirían el corpus:
`orchestrator-claim-gate.sh`, `plan-claim-validator.sh`, `pre-commit-gate.sh`,
`adversarial-review-gate.sh`, `surface-fix-detector.sh`,
`scope-creep-detector.sh`, `dod-gate.sh`, `destructive-git-blocker.sh`,
`direct-main-guard.sh`, `conflict-marker-guard.sh`.

Y hay un hook registrado que está roto en producción: **`confidentiality-enforcer`
tiene 1.418 de 1.524 filas con `action=scan_error_fail_open`** — el 93 % de las
veces el scanner revienta y deja pasar la escritura. Sus 3 bloqueos reales
dispararon el prompt de `governance-catch-prompts` con `default: skip`, y las 3
veces quedó sin responder. No hay dato de si el bloqueo sirvió.

### Lo que sí previno algo en este repo no es del SO

`aisotropy` tiene sus propios ganchos de git:

```
.git/hooks/pre-commit -> scripts/license-gate-precommit.sh
.git/hooks/pre-push   -> scripts/pre-push-gate.sh   (creado 2026-07-27, bccefa7)
```

Son nativos del repo. El commit `b9f0105` — *"stage 5 skipped itself and still
reported all stages clean"* — es el repo auditando su propio gate, sin que
ningún hook del SO se lo pidiera.

---

## 5. Los 110 overrides: el problema es el gate

**Corrección primero: los 110 no son del consumidor.** `git-op-blocks.jsonl` vive
en el repo del SO y tiene **0 filas atribuibles a `aisotropy`**, porque
`destructive-git-blocker.sh` no está registrado ahí. Los 37 bloqueos y los 110
overrides son del SO sobre sí mismo, entre 2026-07-02 y 2026-08-15.

| Razón del override | N |
|---|---:|
| `inline_flag` | 71 |
| `branch_switch_override` | 36 |
| `main_branch_override` | 3 |

| Operación (override) | N |
|---|---:|
| `git checkout branch/context` | 35 |
| `git stash pop` | 22 |
| `git worktree` | 20 |
| `git reset` | 12 |
| `git stash drop` | 5 |
| `git checkout --` | 5 |
| `git rebase` | 4 |
| `git stash apply` / `git switch` | 2 / 2 |
| `git push origin main` | 3 |

**¿Razonables?** El trabajo, sí: 107 de 110 son operaciones locales y
recuperables — crear un worktree, cambiar de rama, restaurar un stash, resetear
el índice. Los 3 realmente riesgosos son los push a `main`, y los 3 están
etiquetados a propósito, uno con
`COS_DIRECT_MAIN_BYPASS_REASON="release-v0.29.37"`. Esos tres son el uso correcto
de una válvula.

**El mecanismo, no.** `hooks/destructive-git-blocker.sh:479` resuelve el override
así:

```bash
echo "$COMMAND" | grep -Eq '(^|[[:space:]])--allow-destructive($|[[:space:]])'
```

Busca el token en cualquier parte del string del comando. **70 de los 110
overrides ponen el token donde no ejecuta nada**: en un no-op del shell o dentro
de un comentario. Ejemplos textuales del ledger:

```
: --allow-destructive ; git reset HEAD -- scripts/...
: --allow-destructive ; git stash drop stash@{0}
git reset --hard 20c01e3d0 # --allow-destructive
```

El tercero es el que cierra el caso: el token está **después de un `#`**. El
comando que se ejecuta es `git reset --hard 20c01e3d0` a secas, y el guard lo
deja pasar porque la palabra aparece en el texto. Es un verde barato:
se satisface el gate sin tocar el intent.

Y el gate dispara mayormente sobre trabajo rutinario — `git checkout` de rama,
`git worktree`, `git stash pop` suman 77 de los 110. Un guard que interrumpe
principalmente para que le contesten con una cadena mágica no está protegiendo;
está entrenando a escribir la cadena.

**Dos arreglos separados:** (a) exigir que el token esté en el `argv` del comando
git guardado, no en el string completo — parsear, no `grep`; (b) sacar
`git worktree` y `git checkout` de rama de la lista de operaciones destructivas,
que es donde nace el 70 % del ruido.

---

## 6. El script que construye el corpus

Read-only, determinista, exit 0 sin eventos / 1 con eventos / 2 error de entorno.
No depende de estado de sesión. Corre en ~4 minutos (el bloque E2 hace un
`git show --name-only` por commit candidato).

```bash
CONSUMER=~/Projects/luum/aisotropy SO=. python3 qa_contrafactual_corpus.py
```

```python
#!/usr/bin/env python3
"""Corpus contrafactual: eventos malos reales en un repo consumidor vs. lo que
el SO tenia registrado en ese momento.

READ-ONLY. No escribe nada en ningun repo. Determinista.
Exit codes: 0 = sin eventos malos / 1 = hay eventos / 2 = error de entorno.
"""
from __future__ import annotations

import collections
import datetime as dt
import json
import os
import pathlib
import re
import subprocess
import sys

CONSUMER = pathlib.Path(os.environ.get("CONSUMER", pathlib.Path.home() / "Projects/luum/aisotropy")).expanduser()
SO = pathlib.Path(os.environ.get("SO", ".")).expanduser().resolve()
SINCE = os.environ.get("SINCE", "2026-07-01")
WINDOW = int(os.environ.get("WINDOW", "3600"))  # +-1h alrededor del commit padre

CRED_PATTERNS = ["sk-ant-", "sk-proj-", "ghp_", "xoxb-", "AKIA",
                 "BEGIN RSA PRIVATE KEY", "BEGIN OPENSSH PRIVATE KEY"]
FIXUP_RE = re.compile(r"\b(fix|fixup|typo|oops|hotfix|revert|undo|broke|broken|stale|never ran|blind)", re.I)
CLAIM_RE = re.compile(r"\b(verified|verificado|measured|medido|all (stages|tests|checks) (clean|pass)"
                      r"|0 fail|zero fail|tests pass|green|100%|confirmed|proven|clean)\b", re.I)


def git(*args, repo=CONSUMER, timeout=120):
    r = subprocess.run(["git", "-C", str(repo), *args],
                       capture_output=True, text=True, timeout=timeout)
    return r.stdout


def jsonl(path):
    out = []
    try:
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    except FileNotFoundError:
        pass
    return out


def epoch(s):
    try:
        return dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc).timestamp()
    except Exception:
        return None


def section(t):
    print(f"\n{'=' * 72}\n{t}\n{'=' * 72}")


def main():
    if not (CONSUMER / ".git").exists():
        print(f"ERROR: {CONSUMER} no es un repo git", file=sys.stderr)
        return 2

    events = collections.Counter()

    # ---------------------------------------------------------------- E1
    section("E1 - reverts reales (git revert)")
    reverts = [l for l in git("log", f"--since={SINCE}", "--format=%h|%s").splitlines()
               if l.split("|", 1)[1].startswith("Revert ")]
    print(f"reverts: {len(reverts)}")
    for r in reverts:
        print("  ", r)
    events["reverts"] = len(reverts)

    # ---------------------------------------------------------------- E2
    section("E2 - fix-ups <=1h que tocan archivos del commit anterior")
    log = [l.split("|", 2) for l in git("log", f"--since={SINCE}", "--format=%H|%ct|%s").splitlines()]
    log = [(h, int(t), s) for h, t, s in log]
    print(f"commits en ventana: {len(log)}")

    def files(h):
        return {x for x in git("show", "--name-only", "--format=", "-r", h).splitlines() if x}

    fixups = []
    for i in range(len(log) - 1):
        h, t, s = log[i]
        ph, pt, ps = log[i + 1]
        if t - pt <= 3600 and FIXUP_RE.search(s):
            ov = files(h) & files(ph)
            if ov:
                fixups.append((h, ph, pt, t - pt, len(ov), s, ps))
    print(f"fix-ups con solapamiento de archivos: {len(fixups)}")
    lat = sorted(d for _h, _p, _pt, d, _n, _s, _ps in fixups)
    if lat:
        print(f"latencia de correccion: min={lat[0]}s  mediana={lat[len(lat) // 2]}s  max={lat[-1]}s")
    for h, ph, _pt, d, n, s, ps in fixups:
        print(f"  {h[:9]} +{d:5d}s ov={n:3d} | {s[:86]}")
        print(f"            padre {ph[:9]} | {ps[:86]}")
    events["fixups"] = len(fixups)

    # ---------------------------------------------------------------- E2b
    section("E2b - de esos fix-ups, cuantos padres declaraban verificacion")
    claimed = []
    for _h, ph, _pt, _d, _n, _s, _ps in fixups:
        body = git("log", "-1", "--format=%B", ph)
        m = CLAIM_RE.search(body)
        if m:
            ctx = body[max(0, m.start() - 55):m.end() + 40].replace("\n", " ")
            claimed.append((ph, ctx))
    for ph, ctx in claimed:
        print(f"  {ph[:9]} CLAIM -> ...{ctx}...")
    print(f"padres con claim de verificacion: {len(claimed)}/{len(fixups)}")
    events["_claimed_parents"] = 0  # informativo, no suma al corpus

    # ---------------------------------------------------------------- E3
    section("E3 - credenciales en la historia")
    for p in CRED_PATTERNS:
        n = len(git("log", f"--since={SINCE}", "--oneline", f"-S{p}").splitlines())
        print(f"  git log -S{p!r}: {n} commits")
    tree = [f for f in git("grep", "-lIE",
                           r"(sk-ant-|sk-proj-|ghp_|xoxb-|AKIA)[A-Za-z0-9_-]{6,}").splitlines()
            if f and not f.startswith(".cognitive-os/")]
    print(f"  archivos del arbol con patron de credencial: {len(tree)} -> {tree}")
    print("  (clasificar a mano: placeholder de template y fixture de test no son fuga)")
    env_hist = git("log", "--all", "--oneline", "--", ".env").splitlines()
    print(f"  .env commiteado alguna vez: {len(env_hist)} commits")
    events["secrets_in_history"] = len(env_hist)

    # ---------------------------------------------------------------- E4
    section("E4 - rutas absolutas de home commiteadas")
    hits = git("log", f"--since={SINCE}", "--format=%h|%ad|%s", "--date=short", "-S/Users/").splitlines()
    print(f"  commits que tocan '/Users/': {len(hits)}")
    for h in hits:
        print("   ", h)
    print("  (clasificar a mano: /Users/runner/ es ruta de CI, no fuga de home)")

    # ---------------------------------------------------------------- E5
    section("E5 - roturas de build/formato declaradas")
    subjects = git("log", f"--since={SINCE}", "--format=%h|%ad|%s", "--date=short")
    gof = [l for l in subjects.splitlines()
           if re.search(r"gofmt|go mod tidy|compile break|broke all|red since", l, re.I)]
    print(f"  commits que declaran rotura de build/formato: {len(gof)}")
    for g in gof:
        print("   ", g)
    events["build_breaks"] = len(gof)

    # ---------------------------------------------------------------- E6
    section("E6 - claims falsos confesados en el asunto")
    claims = [l for l in subjects.splitlines()
              if re.search(r"skipped itself|was lying|never ran|blind spot|still reported"
                           r"|stale claim|false .*claim", l, re.I)]
    print(f"  commits que confiesan un claim falso: {len(claims)}")
    for c in claims:
        print("   ", c)
    events["false_claims"] = len(claims)

    # ---------------------------------------------------------------- H1
    section("H1 - superficie de hooks: SO disponible vs consumidor registrado")
    avail = {p.name for p in (SO / "hooks").glob("*.sh")}
    reg = set()
    try:
        cfg = json.load(open(CONSUMER / ".claude/settings.json"))
        for arr in cfg.get("hooks", {}).values():
            for m in arr:
                for hk in m.get("hooks", []):
                    reg |= set(re.findall(r"([a-z0-9._-]+\.sh)", hk.get("command", "")))
    except Exception as exc:
        print("  no se pudo leer settings.json del consumidor:", exc)
    print(f"  hooks disponibles en el SO: {len(avail)}")
    print(f"  hooks registrados en el consumidor: {len(reg)}")
    print(f"  cobertura: {100 * len(reg & avail) / max(1, len(avail)):.1f}%")
    gaps = sorted(a for a in avail - reg
                  if re.search(r"guard|gate|block|valid|check|enforce|policy|detect", a))
    print(f"  guards/gates NO registrados: {len(gaps)}")
    for g in gaps:
        print("   ", g)

    # ---------------------------------------------------------------- H2
    section("H2 - telemetria: que hizo cada hook en el consumidor")
    hh = jsonl(CONSUMER / ".cognitive-os/metrics/hook-health.jsonl")
    per = collections.Counter((r.get("hook"), r.get("exit_code")) for r in hh)
    print(f"  filas hook-health: {len(hh)}   hooks distintos: {len({r.get('hook') for r in hh})}")
    print(f"  corridas con exit_code != 0: {sum(v for k, v in per.items() if k[1] not in (0, None))}")
    for k, v in sorted(per.items()):
        print(f"    {v:7d}  {k[0]} exit={k[1]}")

    ht = jsonl(CONSUMER / ".cognitive-os/metrics/hook-timing.jsonl")
    nz = collections.Counter((r.get("hook"), r.get("exit_code")) for r in ht
                             if r.get("exit_code") not in (0, None))
    print(f"  filas hook-timing: {len(ht)}   hooks distintos: {len({r.get('hook') for r in ht})}")
    print(f"  exits != 0 en hook-timing: {dict(nz)}")

    conf = jsonl(CONSUMER / ".cognitive-os/metrics/confidentiality-enforcer.jsonl")
    print(f"  confidentiality-enforcer: {dict(collections.Counter(r.get('action') for r in conf))}")
    br = jsonl(CONSUMER / ".cognitive-os/metrics/blast-radius.jsonl")
    print(f"  blast-radius: {dict(collections.Counter(r.get('risk_level') for r in br))} (advisory)")
    for r in jsonl(CONSUMER / ".cognitive-os/metrics/secret-redactions.jsonl"):
        print("    redaccion:", r.get("timestamp"), r.get("tool"), r.get("secrets"), r.get("action"))

    # ---------------------------------------------------------------- H3
    section("H3 - correlacion evento <-> telemetria (ventana +-1h del commit padre)")
    brs = [(epoch(r.get("timestamp", "")), r.get("risk_level")) for r in br]
    cfs = [(epoch(r.get("timestamp", "")), r.get("action")) for r in conf]
    sps = [epoch(r.get("timestamp", "")) for r in
           jsonl(CONSUMER / ".cognitive-os/metrics/scope-proportionality.jsonl")]
    cls = [(epoch(r.get("timestamp", "")), r.get("verdict")) for r in
           jsonl(CONSUMER / ".cognitive-os/metrics/clarification-events.jsonl")]
    runs = [epoch(r.get("timestamp", "")) for r in hh]
    print(f"  {'evento':10} {'padre (UTC)':18} {'BR_HI':>6} {'CONF_crash':>11} "
          f"{'SCOPE':>6} {'CLAR_NO':>8} {'corridas':>9}")
    tot_hi = tot_det = 0
    for h, _ph, pt, _d, _n, _s, _ps in fixups:
        lo, hi = pt - WINDOW, pt + WINDOW
        b = sum(1 for t, l in brs if t and lo <= t <= hi and l in ("HIGH", "CRITICAL"))
        c = sum(1 for t, a in cfs if t and lo <= t <= hi and a == "scan_error_fail_open")
        s_ = sum(1 for t in sps if t and lo <= t <= hi)
        k = sum(1 for t, v in cls if t and lo <= t <= hi and v not in (None, "PASS"))
        r_ = sum(1 for t in runs if t and lo <= t <= hi)
        tot_hi += b
        tot_det += b + s_ + k
        d = dt.datetime.fromtimestamp(pt, dt.timezone.utc).strftime("%Y-%m-%d %H:%M")
        print(f"  {h[:9]:10} {d:18} {b:6} {c:11} {s_:6} {k:8} {r_:9}")
    print(f"  TOTAL blast-radius HIGH/CRITICAL sobre eventos: {tot_hi}")
    print(f"  TOTAL detecciones de cualquier hook sobre eventos: {tot_det}")

    # ---------------------------------------------------------------- H4
    section("H4 - git-op-blocks del SO: bloqueos vs overrides")
    gob = jsonl(SO / ".cognitive-os/metrics/git-op-blocks.jsonl")
    print(f"  {dict(collections.Counter(r.get('event') for r in gob))}")
    ovs = [r for r in gob if r.get("event") == "override"]
    print("  razon:", dict(collections.Counter(r.get("reason") for r in ovs)))
    print("  operacion:", dict(collections.Counter(r.get("op") for r in ovs).most_common(12)))
    tok = sum(1 for r in ovs
              if re.search(r"#[^\n]*--allow-destructive", r.get("command", ""))
              or re.search(r":\s+--allow-destructive\s*;", r.get("command", "")))
    print(f"  overrides con el token en un no-op ':' o en un comentario '#': {tok}")
    print(f"  filas atribuibles al consumidor: "
          f"{sum(1 for r in gob if CONSUMER.name in r.get('command', ''))}")

    print()
    real = {k: v for k, v in events.items() if not k.startswith("_")}
    print("RESUMEN eventos malos:", real)
    return 1 if sum(real.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
```

### Salida resumida de la corrida del 2026-08-15

```
E1 reverts: 0
E2 fix-ups con solapamiento: 21   (min 26s / mediana 328s / max 3024s)
E2b padres con claim de verificacion: 16/21
E3 .env commiteado: 0 | arbol: 2 archivos, ambos placeholder/fixture
E4 commits con '/Users/': 3, los 3 son /Users/runner/ (CI)
E5 roturas de build/formato: 5
E6 claims falsos confesados: 9  (2 ya contados en E2)
H1 hooks SO 257 | registrados 37 | cobertura 13.6% | guards sin registrar 81
H2 hook-health 98.095 filas, exit!=0: 0
   hook-timing 141.679 filas, exit!=0: confidentiality-enforcer=3, auto-checkpoint(SIGPIPE)=180
   confidentiality-enforcer: scan_error_fail_open=1418, otras=106
   blast-radius: LOW=281, CRITICAL=99, HIGH=61   (441 corridas, 441 exit 0)
   secret-redactions: 4
H3 blast-radius HIGH/CRITICAL sobre las 21 ventanas: 0
   detecciones de cualquier hook sobre las 21 ventanas: 8 (todas scope-proportionality, otro motivo)
H4 blocked=37 override=110 | inline_flag=71 branch_switch=36 main_branch=3
   overrides con token en no-op/comentario: 70
   filas atribuibles al consumidor: 0
RESUMEN: {'reverts': 0, 'fixups': 21, 'secrets_in_history': 0, 'build_breaks': 5, 'false_claims': 9}
```

---

## 7. Correcciones a las premisas del encargo

1. **«En los consumidores hubo 37 bloqueos contra 110 overrides».** Falso. Las
   147 filas de `git-op-blocks.jsonl` viven en el repo del SO. **Cero** son
   atribuibles al consumidor, porque `destructive-git-blocker.sh` no está
   registrado ahí. El bloqueador de git nunca corrió en `aisotropy`.

2. **«La cuarta categoría tiene al menos 110 instancias».** Falso en el
   consumidor: tiene **0**. Y en el SO los 110 no son "saltearon el bloqueo":
   71 usan `--allow-destructive`, que es la válvula documentada del propio hook
   (`hooks/destructive-git-blocker.sh:38`). Lo que sí es un hallazgo es *dónde*
   ponen el token: 70 de 110 lo escriben en un no-op o en un comentario.

3. **«98.095 filas de telemetría».** Correcto para `hook-health.jsonl`, pero ese
   archivo solo cubre **11** de los 33 hooks que efectivamente corrieron. La
   telemetría real del consumidor son ~240.000 filas entre dos archivos con
   retención distinta: `hook-timing.jsonl` (141.679 filas) se corta el
   2026-07-19 y `hook-health.jsonl` llega al 2026-08-14. Cualquier conteo sobre
   uno solo de los dos subestima.

4. **«Commits revertidos» como fuente de corpus.** No hay ninguno. Cero `git
   revert` en 607 commits.

5. **«Secretos que sí entraron a la historia».** Ninguno. Y ninguna ruta de home
   tampoco.

6. **«607 commits desde julio».** Correcto: `--since=2026-07-01` devuelve
   exactamente 607, que es toda la historia del repo en la ventana.

7. **El encargo asume que el corpus grande es el caso interesante.** Resultó al
   revés: 33 eventos en 607 commits es 5,4 %, y de esos solo 5 son mecánicamente
   atrapables. Los otros 28 son semánticos ("el header del board describía el
   render, no la medición") y el repo los corrige en una mediana de 5,5 minutos
   sin que ningún hook intervenga. El SO no está fallando en atraparlos: está
   corriendo 240.000 veces al lado de un proceso que ya se autocorrige.

---

## 8. Qué queda accionable, en orden

| # | Acción | Categoría que cierra | Costo |
|---|---|---|---|
| 1 | Escribir un hook `gofmt -l` / `go build` en PreToolUse sobre `*.go` y registrarlo | Sin hook (5 eventos, el único evento verificado independientemente) | bajo |
| 2 | Registrar `orchestrator-claim-gate.sh` en el consumidor | No corrió (16 eventos) | bajo |
| 3 | Arreglar `claim-validator.sh:49` para que también mire mensajes de commit, no solo respuestas de `Agent` | Corrió sin detectar (12 eventos) | medio |
| 4 | Arreglar el fail-open de `confidentiality-enforcer` (1.418 crashes) | Ninguna del corpus, pero es un hook que figura como cobertura y no cubre | medio |
| 5 | Parsear el `argv` en `destructive-git-blocker.sh:479` en vez de `grep` sobre el string, y sacar `git worktree`/`checkout` de rama de la lista de destructivas | Higiene del gate en el repo del SO | medio |

Lo que **no** hace falta tocar: los hooks advisory (`blast-radius`,
`scope-proportionality`, `clarification-gate`, `large-file-advisor`). No
produjeron un solo falso negativo relevante sobre este corpus porque no
produjeron nada, y endurecerlos no cierra ninguna de las cinco categorías.

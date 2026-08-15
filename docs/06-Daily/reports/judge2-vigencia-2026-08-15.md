# Juez 2 — Vigencia de los hallazgos del panel 2026-07-28 · auditado 2026-08-15

> Lente única: **¿siguen siendo ciertos los hallazgos del panel anterior, y tenía razón?**
> No audito el repo de cero. Re-corro los comandos que los 6 informes previos citaron.
> Sesión read-only salvo este archivo.

## Veredicto (una línea)

**Nada se arregló porque nada se tocó**: el repo no recibió un solo commit en los 18 días
posteriores al panel, así que 35 de 46 hallazgos re-verificados siguen exactamente igual,
4 empeoraron solos por el paso del tiempo, y el único que "se resolvió" lo hizo porque el
propio merge del 2026-07-28 lo convirtió en obsoleto — no por remediación.

---

## Tasa de remediación

**0 de 41 hallazgos remediables. 0.0%.**

```bash
# Nada entró al repo desde el panel — ni en main, ni en ninguna rama
git log --all --since=2026-07-29 --oneline | wc -l          # → 0

# Tampoco sobre los archivos concretamente denunciados
git log --all --since=2026-07-29 --oneline -- \
  README.md TRANSPARENCY.md CHANGELOG.md VERSION package.json \
  public-metrics-aspirational.json public-metrics-dogfood.json \
  rules/rate-limiting.md rules/RULES-COMPACT.md docs/00-MOCs/decisions.md \
  docs/03-PoCs/research/INDEX.md scripts/cos_doc_path_audit.py \
  scripts/check_entrypoint_adr_links.py scripts/documentation_truth_audit.py \
  docs/01-Build-Log/history/pre-sanitization-sha-inventory-2026-05-07.txt \
  skills/ hooks/ .claude/settings.json | wc -l               # → 0

git log -1 --format='%h %ad' --date=short                   # → 8602ddc70 2026-07-28
```

Denominador: 46 claims re-corridos, menos 4 `NO VERIFICABLE` (no son remediables con un
commit) y menos 1 `YA NO APLICA` = **41 remediables, 0 remediados**.

Antigüedad de cada superficie pública (`git log -1 --format='%ad' --date=short -- <f>`):

| Archivo | Último commit | Días al 2026-08-15 |
|---|---|---:|
| `public-metrics-aspirational.json` | `f5a831aa1` 2026-04-27 | 110 |
| `public-metrics-dogfood.json` | `f5a831aa1` 2026-04-27 | 110 |
| `TRANSPARENCY.md` | `c8dffd9cf` 2026-05-12 | 95 |
| `README.md` | `9621d8eab` 2026-05-22 | 85 |
| `package.json` | `5c9ab7b8b` 2026-05-29 | 78 |
| `CHANGELOG.md` / `VERSION` | `7ea8057a9` 2026-07-20 | 26 |

Los dos artefactos que el panel señaló como congelados (`public-metrics-*.json`) llevan
**110 días** sin tocarse. El README que los publica, 85.

---

## Tabla maestra

Distribución: **SIGUE ROTO 35 · PEOR 4 · NO VERIFICABLE 4 · EL JUEZ SE EQUIVOCÓ 2 · YA NO APLICA 1 · ARREGLADO 0.**

### A. Superficie pública — completa, sin muestreo (16/16)

| # | Claim | Fuente | Comando | Salida hoy | Categoría |
|---|---|---|---|---|---|
| A1 | hash del inventario SHA = `923170ea…` | `TRANSPARENCY.md:172,229` | `shasum -a 256 docs/01-Build-Log/history/pre-sanitization-sha-inventory-2026-05-07.txt` | `8cd1b416ab538446066fb4ec44a31f5faef8aa15e0e3e50b741858a42dd6ba8d` | **SIGUE ROTO** |
| A2 | el email previo del operador "aparece **2 veces**" en `git log -p` | `TRANSPARENCY.md:150-153` | `git log --all -S'soporte.esolutions' --oneline \| wc -l`; `grep -n esolutions docs/09-Quality/legal/pre-public-readiness-checklist.md` | `0`; sin salida | **SIGUE ROTO** |
| A3 | post-rewrite head `db846adb…` | `TRANSPARENCY.md:48` | `git cat-file -t db846adb6290456b431bfc191b08543f56a2e8d7` | `fatal: could not get object info` | **SIGUE ROTO** (ver corrección C3) |
| A4 | "**12 fire as PreTool/PostTool hooks**" de 14 capas | `README.md:26` | bucle `grep -c "$h.sh" .claude/settings.json` sobre las 12 capas | `dry-run-preview=0`, `rate-limiter=0`, `clarification-interceptor=0` → **disparan 9** | **SIGUE ROTO** |
| A5 | rate limiter "activo por defecto" para Bash/Agent/Edit/Write | `README.md:39-40`, `rules/rate-limiting.md:9` | `grep -c rate-limiter .claude/settings.json`; conteo en `hook-timing.jsonl` | `0` registros; `0` disparos sobre 149 hooks que sí dispararon | **SIGUE ROTO** |
| A6 | "The script **launches a minimal agent**" | `README.md:48` | `sed -n '1,12p' scripts/demo-governance.sh` | el script dice *"simulates a hook invocation … no live Claude API calls"* | **SIGUE ROTO** |
| A7 | "Added the `cos-patch-release` primitive…" repetido | `CHANGELOG.md` | `grep -c 'Added the \`cos-patch-release\` primitive' CHANGELOG.md`; `git log --diff-filter=A -- scripts/cos-patch-release` | `22`; agregado una sola vez en `414382d11` (2026-05-27, v0.29.7) | **SIGUE ROTO** |
| A8 | `total: 597`, `DORMANT: 165`, `ASPIRATIONAL: 69`, `ratio 0.392` | `public-metrics-aspirational.json` | `python3 scripts/aspirational_audit.py --dry-run --json` | `total 910`, `DORMANT 0`, `ASPIRATIONAL 0`, `ratio 0.0` | **PEOR** (110 días stale vs 92 en julio) |
| A9 | "navigable index of **~325 research artifacts**" | `README.md:190` | `find docs/03-PoCs/research docs/06-Daily/reports docs/04-Concepts/architecture docs/08-References/business -name '*.md' \| wc -l` | `845` (el `INDEX.md:5` dice `~538`) | **PEOR** (la brecha creció: era 840) |
| A10 | "zero frameworks prevent it before ours" | `docs/08-References/business/product-messaging.md:54` | búsqueda de universo enumerado / survey comparativo | no existe; además la línea cita `lib/handoff_dispatcher.py`, ruta inexistente | **NO VERIFICABLE** |
| A11 | badge `version-0.1.0` | `README.md:9` | `cat VERSION`; `grep -oE 'version-[0-9.]+-green' README.md` | `0.29.39` vs badge `0.1.0` | **SIGUE ROTO** |
| A12 | 4 badges de métricas | `README.md:11-14` | `grep -c '<org>/<repo>' README.md`; `ls .cognitive-os/metrics/badges/` | `4`; `No such file or directory`. Remote real: `Luum-Home/luum-cognitive-os` | **SIGUE ROTO** |
| A13 | `test_health: null`, `partial: true`, `overall 41.64` | `public-metrics-dogfood.json:9,23,24` | lectura directa | idéntico; la dimensión de mayor peso (25) sigue nula | **SIGUE ROTO** |
| A14 | "~300x acceleration", "100+ AI agents in parallel", "9-15 months → ~24h" | `docs/08-References/business/case-study.md:10,103,105` | intento de rastrear evidencia | el sujeto es el consumidor privado borrado por el rewrite | **NO VERIFICABLE** |
| A15 | `package.json` `"version": "0.1.0"` vs `VERSION`/`pyproject` `0.29.39` | `judge-documentacion:49` | `cat VERSION; grep -m1 '"version"' package.json` | `0.29.39` / `0.1.0`, mismo paquete | **SIGUE ROTO** |
| A16 | `npm test` → `bash tests/run-all-tests.sh`, que no existe | `judge-documentacion:52` | `grep -n '"test"' package.json; [ -e tests/run-all-tests.sh ]` | script declarado, archivo `MISSING` | **SIGUE ROTO** |

### B. Contradicciones internas de documentación — completas (8/8)

| # | Claim | Fuente | Comando | Salida hoy | Categoría |
|---|---|---|---|---|---|
| B1 | `rules/rate-limiting.md` se contradice en 11 líneas | `judge-documentacion:42` | `grep -nE 'lib/rate_limiter\|cos_lib.rate_limiter' rules/rate-limiting.md; [ -d lib ]` | L89 `lib/rate_limiter.py`, L100 `from cos_lib.rate_limiter`; `lib/` no existe | **SIGUE ROTO** |
| B2 | `RULES-COMPACT.md` cita 4 rutas `lib/*` | `judge-documentacion:43` | bucle `[ -e cos_lib/$p ]` / `[ -e lib/$p ]` | 4/4 existen sólo bajo `cos_lib/` | **SIGUE ROTO** |
| B3 | `cos_doc_path_audit.py` → `"status":"fail"` con exit `0` | `judge-documentacion:44` | `python3 scripts/cos_doc_path_audit.py >/dev/null; echo $?` | `exit: 0`, `status=fail`, **2733 findings** | **SIGUE ROTO** |
| B4 | `check_entrypoint_adr_links.py` normaliza el bug que debería detectar | `judge-documentacion:45` | `grep -coE '\]\(adrs/ADR-' docs/00-MOCs/entrypoints/README.md`; correr el checker | `96` links rotos; checker imprime `entrypoint ADR links: ok`, exit `0` | **SIGUE ROTO** |
| B5 | `status_policy.block` sobre fuentes stale, no implementado | `judge-documentacion:46` | `grep -niE 'max_age\|age_days\|mtime' scripts/documentation_truth_audit.py` | sin salida. Fuentes: `2026-05-12` (**95 días**) y `2026-06-16` (**60 días**) | **PEOR** (eran 77 y 42) |
| B6 | `pending-truth-latest.md` vs `.json` desfasados | `judge-documentacion:47` | `head -1 …md`; `json.load(…)['generated_at']` | md: `Verified 2026-08-15T03:18:16Z` · json: `2026-07-08T21:23:36Z` → **38 días** | **PEOR** (eran 20) |
| B7 | `decisions.md` dice "280 ADRs" | `judge-documentacion:50` | `grep -oE 'for [0-9]+ ADRs' docs/00-MOCs/decisions.md`; `ls docs/02-Decisions/adrs/ADR-*.md \| grep -vc synthesis` | `for 280 ADRs` vs **350** | **SIGUE ROTO** (el panel dijo 351 — ver C1) |
| B8 | dos caminos de onboarding divergentes | `judge-documentacion:51` | el comando publicado no produce salida; verificado a mano | `README:85` y `getting-started:59` usan `install.sh`; `getting-started-quick:6` usa `scripts/install-cos.sh`. Ambos existen | **SIGUE ROTO** en sustancia / **EL JUEZ SE EQUIVOCÓ** en el comando (ver C2) |

### C. Primitivas — muestreo declarado: **8 de ~14** claims falsables del informe

| # | Claim | Comando | Salida hoy | Categoría |
|---|---|---|---|---|
| C-P1..P6 | 6 skills citan rutas que no existen | `[ -e <ruta> ]` + `grep -rl` en `skills/<skill>/` | **6/6 siguen**: `deep-research-axis-gate.sh`, `cmd/main.go`, `hooks/old-hook.sh`, `tests/run-all-tests.sh`, `tests/unit/test-skills.sh`, `tests/red_team/portability/test_X.py`. Bonus: `packages/efficiency-profiles/profiles/standard.json` tampoco existe | **SIGUE ROTO** |
| C-P7 | 257 hooks en disco, 162 entradas registradas, 0 apuntando a archivo inexistente | parse JSON de `.claude/settings.json` | `257` / `162` / `0 MISSING`; **155** scripts distintos (panel dijo 154) y **10** eventos (panel dijo 9) | **SIGUE** (claim sano, ver C1) |
| C-P8 | `squads/` es un solo archivo | `ls -1 squads/` | `organization.yaml` | **SIGUE ROTO** |

### D. Código — muestreo declarado: **5 de ~8** hallazgos del informe

| # | Claim | Comando | Salida hoy | Categoría |
|---|---|---|---|---|
| D1 | conteos base (py/tests/go/rs/md, `lib/` ausente) | `git ls-files '<glob>' \| wc -l` | `3037` py · `2156` tests · `193` go · `3` rs · `2380` md · `lib/` = 0 entradas. **5/5 reproducen** | **SIGUE** |
| D2 | `yaml.py` y `scripts/yaml.py` divergentes | `md5 yaml.py scripts/yaml.py` | `b0961144…` vs `60d35461…` | **SIGUE ROTO** |
| D3 | `workflows/` código muerto autodeclarado | `head -3 workflows/DEPRECATED.md` | *"legacy pipeline system from the Sazonia project archive"* | **SIGUE ROTO** |
| D4 | `cos-review-approve` / `cos-review-gate` "WIP sin commitear" | `git ls-files scripts/cos-review-*` | ambos **trackeados** — entraron en el merge `8602ddc70` de esa misma noche | **YA NO APLICA** |
| D5 | `scripts/cos-config-audit.sh` es Python con extensión `.sh` | `head -1 scripts/cos-config-audit.sh`; `bash -n` | `#!/usr/bin/env python3`; `bash -n` reporta error de sintaxis en L49 | **SIGUE ROTO** |

### E. Funcionamiento — muestreo declarado: **4 de ~10** hallazgos del informe

| # | Claim | Comando | Salida hoy | Categoría |
|---|---|---|---|---|
| E1 | `timeout`/`gtimeout` no existen en este macOS | `command -v timeout gtimeout` | ambos `NOT FOUND` | **SIGUE** |
| E2 | `check_test_ratchet.py --help` cuelga (TIMEOUT a 20s) | correr con guarda de 25s | **termina, exit 0** en segundos. Pero no imprime ayuda: corre pytest y devuelve `Test ratchet SKIPPED` | **EL JUEZ SE EQUIVOCÓ** en el síntoma; el defecto de fondo (ignora `--help` y ejecuta) sigue |
| E3 | 257 hooks, 0 fallos de sintaxis | `for h in hooks/*.sh; do bash -n "$h"; done` | `chequeados=257 fallos=0` | **SIGUE** |
| E4 | `rate-limiter` nunca disparó | conteo en `hook-timing.jsonl` | `0` | **SIGUE ROTO** |

### F. Vale-la-pena — muestreo declarado: **5 de ~9** claims falsables

| # | Claim | Comando | Salida hoy | Categoría |
|---|---|---|---|---|
| F1 | 149 hooks dispararon, **108 nunca** | `python3 -c "…set(json.loads(l)['hook'] for l in open('.cognitive-os/metrics/hook-timing.jsonl'))"` | `149` distintos · `108` nunca. **Exacto** | **SIGUE ROTO** |
| F2 | disparos por hook (`session-heartbeat` 25.736, `secret-detector` 17.336, …) | mismo archivo, agregación por hook | hoy: `session-heartbeat` **1.450**, total 32.435 invocaciones. El `.jsonl` rota (mtime 2026-08-15 00:23) | **NO VERIFICABLE** (ver C4) |
| F3 | 1.162 truncaciones de resultado | `wc -l .cognitive-os/metrics/truncation-events.jsonl` | `134` | **NO VERIFICABLE** (mismo motivo) |
| F4 | commits por mes (2026-07: 76) | `git log --format=%ad --date=format:'%Y-%m' \| sort \| uniq -c` | `2026-07: 77` (+1, el merge de esa noche) | **SIGUE** |
| F5 | premisas corregidas (2380 md, 505 ADRs, 197 skills, 3 `.rs`) | `git ls-files` por glob | `2380` / `505` / `197` / `3`. **4/4 reproducen** | **SIGUE** |

---

## Correcciones al panel anterior

Cinco cosas que los informes previos afirmaron y que no se sostienen al re-correrlas.

**C1 — Off-by-one en tres conteos, en informes que exigen evidencia ejecutable.**
Con **cero commits** de por medio, un comando determinista tiene que dar el mismo número.
No lo da:

| Panel dijo | Comando | Hoy |
|---|---|---|
| `judge-documentacion:50,93` — **351** ADRs no-synthesis | `ls docs/02-Decisions/adrs/ADR-*.md \| grep -vc synthesis` | **350** |
| `judge-documentacion:93` — 351 + **150** synthesis + 4 = 505 | `ls … \| grep -c synthesis` | **151** (la descomposición correcta es 350 + 151 + 4) |
| `judge-funcionamiento:173` — **154** scripts distintos, **9** eventos de ciclo de vida | parse de `.claude/settings.json` | **155** scripts, **10** eventos |

Ninguno cambia la conclusión (280 ≠ 350 sigue siendo un claim falso), pero son tres números
publicados con comando al lado que el comando no reproduce. En un panel cuyo argumento
central es *"un número sin comando es opinión con dígitos"*, un número **con** comando que
no reproduce es peor que uno sin.

**C2 — `judge-documentacion:51` publicó un comando que no produce la evidencia que cita.**
El comando es:

```bash
for f in README.md docs/00-MOCs/entrypoints/getting-started{,-quick}.md; do
  grep -oE 'curl [^ ]*install[^ ]*' "$f"; done
```

Hoy devuelve **nada** para los tres archivos. Motivo: en `README.md:85` la línea es
`curl -sL https://…`, y el patrón exige que el token inmediatamente posterior a `curl `
contenga `install` — `-sL` no lo contiene. El hallazgo **es correcto** (verificado a mano:
`README:85` y `getting-started:59` usan `install.sh`; `getting-started-quick:6` usa
`scripts/install-cos.sh`), pero quien copie el comando publicado va a concluir que el
hallazgo es falso.

**C3 — `judge-adversarial` claim #3 se contradice con su propia tabla de "claims que resistieron".**
El claim #3 marca **FALSO** que los heads pre/post-rewrite estén declarados, apoyándose en
que *"ambos objetos están ausentes"*. Pero la ausencia del head **pre-rewrite** (`2d99d40a`)
no es un defecto: es exactamente lo que `TRANSPARENCY.md:179-181` y el §6 paso 4 declaran
como *proof-of-rewrite* — y el mismo informe lo lista como **VERDADERO** dieciséis líneas
más abajo (`judge-adversarial:83`). El hallazgo real es la mitad: sólo el head
**post-rewrite** (`db846adb`) debería ser alcanzable y no lo es. Presentarlo como "ambos
objetos ausentes = FALSO" infla un defecto de un objeto a dos y mete en el mismo saco la
propiedad que el documento acierta.

**C4 — `judge-vale-la-pena` construyó su sección más citable sobre un archivo que rota.**
Toda la tabla de "disparos por hook" (25.736 `session-heartbeat`, 17.336 `secret-detector`,
1.162 truncaciones) sale de `.cognitive-os/metrics/hook-timing.jsonl` y
`truncation-events.jsonl`, que son **archivos de runtime no versionados que se truncan**.
Hoy los mismos comandos dan 1.450, y 134. El informe no declara ventana temporal ni
congela el insumo, así que sus números más vistosos son irreproducibles a los 18 días. Lo
que **sí** reprodujo exacto es lo estructural (149 dispararon / 108 nunca / `rate-limiter` 0),
que es además lo que sostiene el argumento. La parte cuantitativa es adorno frágil.

**C5 — `judge-funcionamiento:117` reportó un cuelgue que no existe.**
`python3 scripts/check_test_ratchet.py --help` termina con exit `0`. El "TIMEOUT a los 20s"
midió una colecta de pytest con caché fría, no un defecto del script. El defecto real —
que `--help` no imprime ayuda sino que ejecuta la herramienta — sigue en pie y es más
barato de arreglar de lo que sugiere el informe.

**Lo que el panel acertó y conviene no perder de vista:** los 16 claims de superficie
pública reprodujeron **16/16**. La parte más dura del diagnóstico (hash autorrefutante,
rate limiter fantasma, boilerplate del CHANGELOG, métricas congeladas, badges rotos)
está intacta y verificada dos veces por jueces independientes con 18 días de distancia.

---

## Correcciones a las premisas de este encargo

1. **"árbol sucio: 10 entradas"** — el conteo es correcto pero no son 10 problemas.
   `git status --short` da 2 modificados (`pending-truth-latest.{json,md}`) + 2 carpetas
   untracked (`--help/`, `.agents/`) + **6 que son los informes del propio panel del
   2026-07-28**, que nunca se commitearon. El repo lleva 18 días con su auditoría más dura
   sin versionar, contra la norma de durabilidad del artefacto.

2. **`--help/` no es ruido inexplicable: lo creó el panel anterior.** `stat` da
   `Jul 28 22:41:16` — durante el barrido de `--help` de `judge-funcionamiento` (test 2.5,
   `for f in scripts/*.py; do python "$f" --help; done`). Algún script tomó `--help` como
   ruta de salida y escribió `--help/.cognitive-os/metrics/{ai-resource-ledger,context-budget}.jsonl`.
   Es un **hallazgo nuevo, no reportado por el panel**: existe al menos un script que
   interpreta `--help` como argumento posicional de directorio. `git check-ignore` confirma
   que ningún patrón lo cubre, así que va a seguir apareciendo en `git status` hasta que
   alguien lo borre.

3. **`.agents/` es del 2026-07-30** (`stat` → `Jul 30 11:15:30`), dos días *después* del
   panel y del último commit. Contiene ~40 symlinks de skills. Es la única escritura
   posterior al panel en todo el checkout junto con los `.jsonl` de runtime: alguien corrió
   una proyección de harness y no la commiteó.

4. **"Hoy es 2026-08-15" — confirmado, y la distancia importa más de lo que sugiere el brief.**
   No son 18 días de trabajo con hallazgos pendientes: son 18 días de **inactividad total**
   (`git log --all --since=2026-07-29` → 0). La tasa de remediación 0% no mide desidia
   frente a los hallazgos; mide que el repo se detuvo. Son diagnósticos distintos.

5. **"otro juez está corriendo la suite en paralelo"** — respetado, no corrí pytest. Pero
   conviene saber que el `--help/` del punto 2 y el desfase regenerado de `pending-truth`
   (B6, timestamp `2026-08-15T03:18:16Z`) prueban que **hay procesos escribiendo en este
   checkout hoy**. Cualquier medición sobre `.cognitive-os/metrics/*.jsonl` de esta sesión
   es un instantáneo, no un hecho estable.

---

## VERIFICADO vs NO VERIFICADO

### VERIFICADO — hay comando y salida en este informe

- Los 46 claims de la tabla maestra, cada uno con su comando y su salida de hoy.
- La tasa de remediación 0/41 (`git log --all --since=2026-07-29` → 0, dos veces: repo
  completo y archivos denunciados).
- Las 5 correcciones al panel (C1–C5): cada una con el comando que muestra la divergencia.
- El origen y la fecha de `--help/` y `.agents/` (`stat -f '%Sm %N'`).
- Que **ningún** claim de los 8 que el panel adversarial listó como "resistieron el ataque"
  se degradó: 5/5 SHAs `missing`, `47` matches de licencia, SBOM `CycloneDX 1.6`, `1775`
  líneas de inventario, 5/5 hooks resuelven por symlink. Cero regresiones ahí.

### NO VERIFICADO — juicio mío, sin comando que lo sostenga

- **Que la inactividad sea una pausa y no un abandono.** El dato es 18 días sin commits;
  la lectura es mía. Un repo con 2.164 commits en mayo y 77 en julio venía desacelerando
  antes del panel, así que la inactividad post-panel puede ser tendencia, no reacción.
- **Que arreglar A1 (el hash) sea barato.** Recalcularlo es un comando, pero decidir *cuál*
  de los dos hashes es el legítimo —recalcular sobre el archivo mutado, o revertir las dos
  ediciones cosméticas de `cb5376b33`/`a4ff8e9cb` y restaurar el hash original— es una
  decisión de política forense que no me corresponde y que ningún comando resuelve.
- **Que los 4 badges rotos importen comercialmente.** Un tercero que llega al README ve
  cuatro imágenes rotas; cuánto pesa eso no lo mide ningún script.
- **Que la clasificación `ON_DEMAND` del auditor sea el mecanismo que produce el 0.0%.**
  El panel de primitivas mostró 7 de 10 muestras mal clasificadas por matcheo de substring;
  no re-corrí esa auditoría de clasificación, así que traslado su conclusión como hipótesis,
  no como hecho verificado por mí.
- **La existencia de otros hallazgos no cubiertos.** Muestreé: primitivas 8/~14, código
  5/~8, funcionamiento 4/~10, vale-la-pena 5/~9. Los ~24 claims internos no re-corridos
  quedan sin veredicto de vigencia — y dado que hubo 0 commits, la presunción razonable es
  que también siguen igual, pero eso es inferencia, no medición.

---

## Cierre: las 3 acciones que más mueven la aguja

**1. Cerrar la superficie pública en un commit — badges, versión y métricas.**
Es lo único que un tercero ve antes de decidir si el repo es serio, son 6 archivos, y hoy
falla en 6 puntos independientes a la vez (badge `0.1.0`, `package.json` `0.1.0`, 4 URLs
`<org>/<repo>`, directorio `badges/` inexistente, dos JSON de 110 días, `npm test` roto).

```bash
# Prueba de que quedó hecho — las 5 líneas deben dar 0 / vacío / fecha de hoy
grep -c '<org>/<repo>' README.md                                   # esperado: 0
diff <(cat VERSION) <(python3 -c "import json;print(json.load(open('package.json'))['version'])")
[ -e "$(python3 -c "import json;print(json.load(open('package.json'))['scripts']['test'].split()[-1])")" ] && echo OK
python3 scripts/aspirational_audit.py --dry-run --json | python3 -c "import json,sys;a=json.load(sys.stdin);b=json.load(open('public-metrics-aspirational.json'));print('SYNC' if a['total']==b['total'] else 'STALE')"
git log -1 --format='%ad' --date=short -- public-metrics-aspirational.json  # esperado: hoy
```

**2. Resolver el hash de `TRANSPARENCY.md` y blindar el artefacto congelado.**
Es el claim que el propio documento invita a falsar, en el archivo que el README manda leer
primero. Decidir política (recalcular vs revertir `cb5376b33`+`a4ff8e9cb`), aplicarla, y
agregar el chequeo al gate para que un barrido cosmético no vuelva a mutar el inventario.

```bash
# Prueba: el hash publicado y el real coinciden, y el archivo tiene guarda
diff <(shasum -a 256 docs/01-Build-Log/history/pre-sanitization-sha-inventory-2026-05-07.txt | awk '{print $1}') \
     <(grep -oE '[0-9a-f]{64}' TRANSPARENCY.md | head -1) && echo "HASH OK"
git grep -l 'pre-sanitization-sha-inventory' -- tests/ scripts/ | head   # esperado: ≥1 gate
```

**3. Hacer que los tres auditores que devuelven verde en falso devuelvan rojo.**
`cos_doc_path_audit.py` (2733 findings, exit 0), `check_entrypoint_adr_links.py` (96 links
rotos, imprime `ok`) y `documentation_truth_audit.py` (sin noción de staleness, con fuentes
de 95 y 60 días bajo un `status_policy` que dice `block`). Mientras devuelvan 0, cualquier
CI atado al exit code certifica lo contrario de lo que mide — y ese es el mecanismo por el
que los otros 35 hallazgos pudieron sobrevivir 18 días sin que nada los señalara.

```bash
# Prueba: los tres exit codes tienen que reflejar su propio status
python3 scripts/cos_doc_path_audit.py >/dev/null 2>&1; echo "doc_path exit=$?"        # esperado: ≠0
python3 scripts/check_entrypoint_adr_links.py >/dev/null 2>&1; echo "adr_links exit=$?" # esperado: ≠0
grep -ciE 'max_age|age_days|mtime' scripts/documentation_truth_audit.py               # esperado: ≥1
```

---

### Cómo reproducir este informe

```bash
cd /path/to/luum-agent-os

# La medida de gobernanza (la única que hace falta si hay poco tiempo)
git log --all --since=2026-07-29 --oneline | wc -l     # → 0
git log -1 --format='%h %ad' --date=short              # → 8602ddc70 2026-07-28

# Superficie pública, los 6 comandos que más pesan
shasum -a 256 docs/01-Build-Log/history/pre-sanitization-sha-inventory-2026-05-07.txt
grep -c '<org>/<repo>' README.md; cat VERSION; grep -m1 '"version"' package.json
grep -c 'Added the `cos-patch-release` primitive' CHANGELOG.md
python3 scripts/aspirational_audit.py --dry-run --json
find docs/03-PoCs/research docs/06-Daily/reports docs/04-Concepts/architecture \
     docs/08-References/business -name '*.md' | wc -l
for h in dry-run-preview rate-limiter clarification-interceptor; do \
  printf '%-26s settings=%s\n' "$h" "$(grep -c "$h.sh" .claude/settings.json)"; done

# Auditores que mienten en verde
python3 scripts/cos_doc_path_audit.py >/dev/null 2>&1; echo "exit=$?"
python3 scripts/check_entrypoint_adr_links.py; echo "exit=$?"
grep -niE 'max_age|age_days|mtime' scripts/documentation_truth_audit.py

# Correcciones al panel anterior
ls docs/02-Decisions/adrs/ADR-*.md | grep -vc synthesis        # 350, el panel dijo 351
stat -f '%Sm %N' ./--help ./.agents                            # origen de las carpetas untracked
python3 -c "import json;h=set();[h.add(json.loads(l).get('hook')) for l in open('.cognitive-os/metrics/hook-timing.jsonl')];print(len(h))"
```

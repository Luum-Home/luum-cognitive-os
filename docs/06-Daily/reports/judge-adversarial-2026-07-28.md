# Juez adversarial — 2026-07-28

> Lente: **refutar**, no evaluar. Objetivo: encontrar la afirmación verificable
> más falsa del repositorio. Todo veredicto lleva el comando que lo sostiene.
> Sesión read-only salvo este archivo.

## Veredicto (una línea)

**El repo no miente sobre lo que su software hace; miente sobre la evidencia de que lo hace** — el documento de transparencia publica un hash SHA-256 que no coincide con su propio artefacto forense, y ese artefacto —el inventario "congelado" que sustituye al mirror pre-rewrite no publicado— fue editado dos veces por barridos cosméticos de documentación.

---

## Los 10 claims atacados

| # | Claim textual | Fuente | Comando de falsación | Resultado | Veredicto |
|---|---|---|---|---|---|
| 1 | "expect `923170ead7ef9fd7c072089a699f867e111ead1be38a84ce41eb1a4023104997`" (hash del inventario SHA pre-sanitización) | `TRANSPARENCY.md:172` y `TRANSPARENCY.md:229` | `shasum -a 256 docs/01-Build-Log/history/pre-sanitization-sha-inventory-2026-05-07.txt` | `8cd1b416ab538446066fb4ec44a31f5faef8aa15e0e3e50b741858a42dd6ba8d` | **FALSO** |
| 2 | "el email previo del operador **aparece 2 veces** en `git log -p`, dentro de `pre-public-readiness-checklist.md`" | `TRANSPARENCY.md:150-153`, `TRANSPARENCY.md:222` | `git log --all -S'soporte.esolutions' --oneline \| wc -l` → `0`; `grep -n 'esolutions' docs/09-Quality/legal/pre-public-readiness-checklist.md` → sin salida | 0 apariciones en toda la historia, 0 en el archivo citado | **FALSO** |
| 3 | "Pre-rewrite head `2d99d40a…` / Post-rewrite head `db846adb…`" | `TRANSPARENCY.md:47-48` | `git cat-file -t db846adb6290456b431bfc191b08543f56a2e8d7` | `fatal: could not get object info` (ambos objetos ausentes) | **FALSO** (el head post-rewrite declarado no existe en el repo publicado) |
| 4 | "a 14-layer safety mesh (**12 fire as PreTool/PostTool hooks**, 2 are library/conditional)" | `README.md:26` | bucle `grep -c "$h" .claude/settings.json` sobre las 12 capas-hook de `docs/04-Concepts/root/safety-mesh.md:18-33` | Layer 3 `dry-run-preview.sh` = `FUTURE … not yet wired`; Layer 10 `clarification-interceptor.sh` = `DEPRECATED`, sin registrar; Layer 4 `rate-limiter.sh` = 0 referencias. **Disparan 9, no 12** | **FALSO** |
| 5 | "`rate-limiter.sh` caps tool calls, agent spawns, and hourly spend (Layer 4)" / "El rate limiter **está activo por defecto** para Bash, Agent, Edit y Write" | `README.md:39-40`; `rules/rate-limiting.md:9` | `grep -c 'rate-limiter' .claude/settings.json` → `0`; `grep -c 'rate-limiter' .cognitive-os/metrics/hook-health.jsonl` → `0`; template de consumidor registra **solo** `PreToolUse Bash` | Nunca disparó en este repo; en el template no cubre Agent/Edit/Write | **FALSO** |
| 6 | "The script **launches a minimal agent**, intercepts a fabricated trust report" | `README.md:48` | `sed -n '1,12p' scripts/demo-governance.sh` | El propio script: *"Each step **simulates** a hook invocation using stdin payloads — **no live Claude API calls**"* | **FALSO** |
| 7 | "Added the `cos-patch-release` primitive for repeatable patch release preparation…" | `CHANGELOG.md` (22 releases distintas, de `0.29.9` a `0.29.39`) | `grep -c 'Added the \`cos-patch-release\` primitive' CHANGELOG.md` → `22`; `git log --diff-filter=A -- scripts/cos-patch-release` → `414382d11 2026-05-27 release: v0.29.7` | Se agregó **una vez** (v0.29.7). 21 de 22 entradas "Added" son boilerplate repetido | **FALSO** |
| 8 | `dormant_aspirational_ratio: 0.392`, `DORMANT: 165`, `ASPIRATIONAL: 69`, `total: 597` | `public-metrics-aspirational.json:2-10` (raíz del repo = superficie pública) | `python3 scripts/aspirational_audit.py --dry-run --json` | Hoy: `total 910`, `DORMANT 0`, `ASPIRATIONAL 0`, `ratio 0.0`. El JSON publicado tiene 3 meses (`git log -1 -- public-metrics-*.json` → `2026-04-27`) | **ENGAÑOSO-PERO-TÉCNICAMENTE-CIERTO** (era cierto al generarse; se publica sin fecha visible) |
| 9 | "navigable index of **~325 research artifacts**" | `README.md:190` | Comando del propio índice: `find docs/03-PoCs/research docs/06-Daily/reports docs/04-Concepts/architecture docs/08-References/business -name '*.md' \| wc -l` → `840` | El índice mismo (`docs/03-PoCs/research/INDEX.md:5`) dice `~538`. Tres números para el mismo objeto: 325 / 538 / 840 | **FALSO** (incoherente en las tres superficies) |
| 10 | "**zero frameworks prevent it before ours**" (cycle-deduplication) — marcado como *"citable in landing copy, sales decks, or HN posts"* | `docs/08-References/business/product-messaging.md:52-54` | Búsqueda de survey/matriz de frameworks que sustente el superlativo: no existe artefacto comparativo con datos crudos; `docs/08-References/root/vs-alternatives.md` no contiene una sola cifra (`grep -nE '[0-9]+%\|[0-9]+x' …` → sin salida) | Superlativo universal sobre todos los frameworks, sin universo enumerado | **NO VERIFICABLE** (y designado explícitamente como copy comercial) |

### Hallazgos adicionales del mismo barrido

| Claim | Fuente | Comando | Resultado |
|---|---|---|---|
| Badge `version-0.1.0` | `README.md:9` | `cat VERSION` | `0.29.39` — **FALSO** |
| 4 badges de métricas (Dogfood, REAL Primitives, Portability, Hook Wiring) | `README.md:11-14` | `grep -c '<org>/<repo>' README.md` → `4`; `ls .cognitive-os/metrics/badges/` → *No such file or directory* | URLs con placeholders sin sustituir y endpoint inexistente: **4 badges rotos en el README público** |
| `test_health: null`, `"partial": true` | `public-metrics-dogfood.json:9,24` | lectura directa | El score público `overall: 41.64` se calcula **sin** la dimensión de mayor peso (`test_health`, weight 25). Está declarado en el JSON, pero el badge que lo consumiría está roto → **ENGAÑOSO-PERO-TÉCNICAMENTE-CIERTO** |
| "~300x acceleration", "9-15 months → ~24 hours", "100+ AI agents in parallel" | `docs/08-References/business/case-study.md:10,104-105`; citado como *"Production proof"* en `executive-summary.md:76` | La plataforma fintech es el proyecto consumidor privado cuyos codenames fueron **borrados de la historia** por el propio rewrite (`TRANSPARENCY.md:45`) | **NO VERIFICABLE por diseño**: la evidencia del claim comercial más grande del repo fue deliberadamente eliminada del artefacto público |

---

## El claim más falso del repo

> **`TRANSPARENCY.md:172` / `TRANSPARENCY.md:229` — el hash declarado del inventario SHA pre-sanitización.**
>
> ```
> | Pre-rewrite SHAs are publicly recorded | …pre-sanitization-sha-inventory-2026-05-07.txt |
> `shasum -a 256 …` (expect `923170ead7ef9fd7c072089a699f867e111ead1be38a84ce41eb1a4023104997`) |
> ```

**Por qué es el peor, y no simplemente un número viejo:**

1. **Es autorrefutante.** El documento entrega el comando que lo desmiente. `TRANSPARENCY.md:3-5` promete: *"Every claim below maps to an artifact in-tree and a command you can run against your own clone"*, y `TRANSPARENCY.md:211-213` cierra con *"If a result diverges from what this document claims, file an issue"*. El paso 3 del kit anti-FUD diverge en un clon fresco, hoy.

2. **El artefacto "congelado" fue mutado — dos veces, por barridos cosméticos.**

   ```bash
   git log --oneline -- docs/01-Build-Log/history/pre-sanitization-sha-inventory-2026-05-07.txt
   # cb5376b33 2026-06-05 Rename Windsurf references to Devin
   # a4ff8e9cb 2026-05-16 fix: complete English-only audit cleanup
   # c8dffd9cf 2026-05-12 feat(docs): remove legacy docs bridges
   # 700e1260f 2026-05-12 feat(docs): bridge build log vault   ← único con hash 923170ea…
   ```

   Y el contenido de lo que cambió:

   ```diff
   -ab3322cc… feat(cos-dispatch): Phase 5.4 Cursor/Windsurf provider hardening + flag semantics
   +ab3322cc… feat(cos-dispatch): Phase 5.4 Cursor/Devin provider hardening + flag semantics
   ```

   Es decir: un rename de marketing reescribió el **mensaje de commit histórico** dentro del inventario forense. El registro público ahora afirma que un commit de 2026-04-16 mencionaba "Devin" — no lo hacía. Lo mismo con `α` → `alpha` en `a4ff8e9cb`.

3. **Es el sustituto público del mirror que no se publica.** `TRANSPARENCY.md:156-163` justifica no publicar el mirror pre-rewrite porque *contiene los datos que se limpiaron*, y ofrece este inventario como el sustituto verificable: *"Anyone with their own pre-rewrite clone can hash-compare against this file"*. Un tercero que haga exactamente eso obtiene un mismatch y no tiene forma de distinguir "editaron dos líneas cosméticas" de "manipularon la evidencia". **La instrumentación de confianza del repo falla justo en el punto donde el repo pide confianza.**

**Costo de reparación**: bajo (recalcular el hash o revertir las dos líneas). **Costo reputacional si un escéptico externo lo encuentra primero**: alto — es el documento que el README ordena leer primero (`README.md:3-5`).

---

## Claims que resistieron el ataque

Esto importa tanto como lo anterior: el repo **no** es un catálogo de humo.

| Claim | Comando | Resultado |
|---|---|---|
| "Pre-rewrite SHAs are NOT reachable from origin/main — that is the proof-of-rewrite" (`TRANSPARENCY.md:232-236`) | el bucle exacto del §6 paso 4 | 5/5 `missing`. **VERDADERO** |
| "Expect: 40+ matches" de strings de licencia preservados (`TRANSPARENCY.md:130`, `:226`) | `grep -E 'Apache\|FSL-1\.1-MIT' LICENSE NOTICE docs/09-Quality/legal/license-faq.md \| wc -l` | `47`. **VERDADERO** |
| "SBOM … CycloneDX 1.6" (`TRANSPARENCY.md:244-246`) | `jq -r '"\(.bomFormat) \(.specVersion)"' sbom.json` | `CycloneDX 1.6`. **VERDADERO** |
| "1,775 entries; one line per pre-rewrite commit" (`TRANSPARENCY.md:161`) | `wc -l < …sha-inventory-2026-05-07.txt` | `1775`. **VERDADERO** |
| Los 5 hooks nombrados en el README existen y resuelven por symlink a `packages/*` | `readlink -f hooks/{claim-validator,blast-radius,auto-rollback-trigger,trust-score-validator,rate-limiter}.sh` | 5/5 resuelven. **VERDADERO** |
| "`claim-validator.sh` blocks agents that report test results without running tests (Layer 6)" (`README.md:31-32`) | `docs/06-Daily/reports/aspirational-audit-2026-07-20.md` → `REAL \| fire_count_7d=10, registered=True`; `grep -c claim-validator .claude/settings.json` → `2` | Registrado y disparando. **VERDADERO** |
| "self-improvement y self-healing son propose-only y human-gated — autonomous production mutation is **not** claimed" (`README.md:184-186`) | lectura de la leyenda REAL/DORMANT/ASPIRATIONAL y de `docs/08-References/business/features.md:11-18` | El repo **se desmarca activamente** del claim más tentador del rubro. **VERDADERO y a favor** |

**Los 3 que resistieron mejor** (por dificultad de falsación y por lo que costaría fingirlos): la no-alcanzabilidad de los SHAs pre-rewrite, la preservación de los strings de licencia, y la clasificación honesta de self-healing como propose-only.

---

## No verificable

Claims que no pude ni confirmar ni refutar con un comando, y por qué:

1. **`case-study.md` — "~300x acceleration", "100+ agentes en paralelo", "700+ tests"** (`docs/08-References/business/case-study.md:10,104-105`). El sujeto es el proyecto consumidor privado cuyos identificadores fueron borrados por el rewrite de 2026-05-08. No hay logs, no hay junit, no hay harness. `executive-summary.md:76` lo llama *"Production proof"*. Es el claim comercial de mayor daño potencial del repo y su evidencia es estructuralmente inauditable desde el artefacto público.
2. **`product-messaging.md:54` — "zero frameworks prevent it before ours"**. Superlativo universal; no existe el conjunto enumerado de frameworks contra el que se afirma. Marcado explícitamente como copy para landing/deck/HN.
3. **`product-messaging.md:57` — "15–30% silent side-effect duplication … industry-wide"**. Cifra de industria sin cita primaria en el documento.
4. **`kubernetes-for-agents.md:520-522` — "runs in 96% of organizations" / "a market growing 10x faster than containers"**. Estadísticas externas sin fuente.
5. **`TRANSPARENCY.md:49` — "Commit count 2,440 (preserved, before and after)"**. Hoy `git rev-list --count HEAD` = `3253`. El claim es sobre el instante del rewrite, que ya no es observable desde este clon. No refutable, pero tampoco reproducible por un tercero.
6. **`TRANSPARENCY.md:222` (§6 paso 1)** — el comando `git log --all -p | grep …` **no termina en 10 minutos** en el repo actual. Un "copy-paste toolkit" que un escéptico no puede correr no es verificación. (Lo resolví con `git log --all -S` — pickaxe — que da la respuesta en segundos.)

---

## Correcciones a las premisas del encargo

El encuadre venía de un `ls` sin lectura. Cinco puntos no se sostienen:

1. **`hooks/` NO es un symlink de directorio.** Es un directorio real de 263 entradas donde los **archivos individuales** son symlinks a `packages/*/hooks/`. `readlink hooks` no devuelve nada; hay que hacer `readlink -f hooks/<archivo>.sh`. La trampa existe, pero un nivel más abajo del anunciado.
2. **`timeout` no existe en este macOS** (ni `gtimeout`). Mi primera ronda de greps sobre la historia devolvió `0` por *command not found*, no por ausencia de matches — un falso negativo que casi absuelve al claim #2. Lo rehíce con `git log --all -S` (pickaxe). **Cualquier comando con `timeout` en un informe de este repo es sospechoso por defecto.**
3. **`benchmarks/` no contiene métricas comerciales sin harness.** Contiene un solo fixture (`benchmarks/improvement/skip-classification-mini/`) con `evaluate.py`, labels privados y logs de ejecución — es decir, **sí tiene el harness que produce sus números**. La hipótesis "métricas de benchmark sin el harness" **no se verificó** ahí. Los claims comparativos problemáticos viven en `docs/08-References/business/`, no en `benchmarks/`.
4. **La distinción aspirational/dogfood SÍ está declarada donde un tercero la vería.** `README.md:178-186` publica la leyenda REAL/DORMANT/ASPIRATIONAL y apunta a la reconciliación. La premisa de que la distinción está escondida **no se sostiene**. Lo que sí falla es distinto: los dos JSON públicos están **congelados en 2026-04-27** y los cuatro badges que los expondrían apuntan a `<org>/<repo>` y a un directorio inexistente.
5. **"N reglas / N skills / N hooks activos donde N cuenta archivos".** Encontrado, pero con un matiz que corrige la hipótesis: el clasificador (`scripts/aspirational_audit.py:200-218`) cuenta un hook como `registered` si aparece en **cualquier** proyección de harness (`.cursor/hooks.json`, `.devin/hooks.json`, templates), no solo en la del harness activo. Por eso `rate-limiter.sh` figura `registered=True` en el audit del 2026-07-20 mientras tiene **0 referencias** en `.claude/settings.json` y **0 disparos** en `hook-health.jsonl`. No es conteo de archivos: es conteo de registros en harnesses que nadie está usando.

### Nota sobre el ratio 0.0% de DORMANT+ASPIRATIONAL

No es laundering reciente — `tests/contracts/EXCLUDED_HOOKS.txt` ronda las 95-125 entradas desde 2026-04-20 (`git log --reverse -- tests/contracts/EXCLUDED_HOOKS.txt` + `git show <sha>:… | grep -vc '^#'`). Pero el mecanismo sí merece nombrarse: **66 componentes salen del numerador vía whitelist**, y `20` de ellos con categoría literal `FUTURE: … not yet wired` (`grep -oE 'category=[A-Z_]+' docs/06-Daily/reports/aspirational-audit-2026-07-20.md | sort | uniq -c`). Un hook que el propio manifiesto describe como *"planned … — not yet wired"* se contabiliza `METADATA`, no `ASPIRATIONAL`. El 0.0% es exacto bajo la definición del clasificador y engañoso bajo la lectura natural de "no tenemos features aspiracionales".

---

## Cómo reproducir este informe

```bash
cd /path/to/luum-agent-os

# Claim #1 — el más falso
shasum -a 256 docs/01-Build-Log/history/pre-sanitization-sha-inventory-2026-05-07.txt
grep -n '923170ead7ef' TRANSPARENCY.md
git log --oneline -- docs/01-Build-Log/history/pre-sanitization-sha-inventory-2026-05-07.txt

# Claim #2 — usar pickaxe, NO `timeout` (no existe en macOS)
git log --all -S'soporte.esolutions' --oneline | wc -l

# Claim #4 y #5 — capas del safety mesh realmente cableadas
for h in clarification-gate blast-radius dry-run-preview rate-limiter scope-proportionality \
         claim-validator assumption-tracker trust-score-validator confidence-gate \
         clarification-interceptor auto-rollback-trigger reinvention-check; do
  printf '%-30s settings=%s excluded=%s\n' "$h" \
    "$(grep -c "$h.sh" .claude/settings.json)" \
    "$(grep -c "^$h.sh" tests/contracts/EXCLUDED_HOOKS.txt)"
done

# Claim #7 — changelog boilerplate
grep -c 'Added the `cos-patch-release` primitive' CHANGELOG.md
git log --diff-filter=A --format='%h %ad %s' --date=short -- scripts/cos-patch-release

# Claim #8 — métricas públicas vs realidad
python3 scripts/aspirational_audit.py --dry-run --json
git log -1 --format='%ad' --date=short -- public-metrics-aspirational.json

# Claim #9 — el índice contra su propio comando
find docs/03-PoCs/research docs/06-Daily/reports docs/04-Concepts/architecture \
     docs/08-References/business -name '*.md' | wc -l
```

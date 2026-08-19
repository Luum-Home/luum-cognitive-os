# Declaraciones sin atar: el hecho vive en N lugares y ninguno es la fuente

**Fecha**: 2026-08-19 · **Scope**: OS · **Tipo**: informe de arquitectura (propuesta, no implementación)
**Autor**: sub-agente arquitecto (problema B) · **Número de ADR**: sin reclamar, decide el operador
**Nada acá se escribió fuera de este archivo.** Todos los números salen de comandos read-only
que se citan al lado de cada uno.

---

## Resumen ejecutivo

- **12 hechos** que el SO declara sobre sí mismo viven en **56 sitios de declaración**
  (media 4,7 por hecho; ninguno en menos de 2). Ninguno de los 12 tiene una fuente
  única; los 56 se mantienen a mano.
- El diagnóstico del encargo se **confirma**, y el repo contiene el experimento que
  lo prueba: de las 5 claves de cabecera de los hooks, la única con gate de censo
  (`# SCOPE:`) tiene **257/257** de cobertura y deriva 0; las cuatro decorativas
  (`# Event:` 24, `# Async:` 13, `# Matcher:` 10, `# Latency:` 4 sobre 257) derivaron
  todas. Mismos autores, mismos archivos, misma semana: la única variable es el gate.
- **Recomendación (una frase)**: derivar del árbol los 4 hechos cuya deriva ya hizo
  daño —instalación, evento/matcher/async, existencia de hooks, capacidad de arnés—
  escribiendo **tres derivadores concretos antes de cualquier framework**, y borrar
  1 manifest + 5 listas fijas + 51 líneas de cabecera; **no** construir el
  verificador genérico hasta que los tres derivadores demuestren compartir forma.
- **No es "no hacer nada"** por un caso: el instalador borró dos rules en el disco de
  otra persona con exit 0 y cero warnings. La corrección a mano solo funciona donde
  alguien mira, y ahí nadie iba a mirar.
- **Costo**: <1 s de CI por gate derivador (referencia medida: `cos-scope-projection-audit`
  audita 1480 artefactos en **0,48 s**), **0 tokens por turno** (va a la lane de tests,
  no a un hook), y ~12 derivadores de 40-60 líneas contra 56 sitios a mano.
- **De A/C/D**: subsume **C** entero (es el hecho A1 de mi censo) y una esquina de **A**;
  **no** subsume **D** — depende de él. El paso 4 de mi migración está bloqueado por D.

---

## Correcciones a las premisas del encargo

1. **"cognitive-os.yaml > harness.hooks declara 190 scripts → hay 257 en hooks/*.sh".**
   Los dos números son correctos pero cuentan poblaciones distintas y el encargo los
   resta como si fueran la misma. Medido hoy: `harness.hooks` tiene **200 claves** que
   referencian **190 scripts distintos** (hay claves que comparten script), `hooks/*.sh`
   tiene **257 archivos** con **255 realpaths únicos** (42 symlinks a `packages/*/hooks/`),
   y el delta real es **67 archivos no declarados**, 0 declarados-sin-archivo.
   ```bash
   ls hooks/*.sh | wc -l                                   # 257
   for f in hooks/*.sh; do readlink -f "$f"; done|sort -u|wc -l   # 255
   python3 -c "import yaml;print(len(yaml.safe_load(open('cognitive-os.yaml'))['harness']['hooks']))"  # 200
   ```
   Que "cuántos hooks hay" admita 257/255/200/190 sin que ninguna definición esté
   escrita **es el problema, no un detalle de conteo**. Lo mismo pasa con las skills:
   el encargo dice 193, `skills/**/SKILL.md` da **119** y el repo entero da **437**
   (434 realpaths). Tres números, ninguna población definida.

2. **"harness-driver-capabilities.yaml dice opencode PreToolUse supported → el driver
   emite 0 handlers en tool.execute.before/after".** El hecho observable es correcto;
   la conclusión "el manifest miente" es más floja que la realidad, que es peor.
   El driver **sí** mapea `PreToolUse → tool.execute.before`
   (`scripts/_lib/settings-driver-opencode.sh:105`) y **excluye a propósito y por escrito**
   la proyección de scripts en esos dos eventos:

   > `# Tool-call events are enforced natively by cos-primitive-guard.js inline`
   > `# classifiers. Projecting their scripts would add 130+ serial bash spawns to`
   > `# every single tool invocation, so the keys stay present but empty.`
   > `SCRIPT_PROJECTION_EXCLUDED_EVENTS = {"tool.execute.before", "tool.execute.after"}`

   Y el plugin cumple: `packages/opencode-adapter/plugins/cos-primitive-guard.js` (389
   líneas) tiene `classifyBash`/`classifyRead`/`classifyTextTool`/`classifyAfter`
   enganchados en `tool.execute.before` (línea 364). O sea: **hay enforcement, por otro
   mecanismo**. El defecto real es que `status: supported` no tiene campo para
   distinguir "proyecto scripts" de "clasifico inline", y que el driver lleva arriba el
   comentario `# OpenCode capability matrix (mirror manifests/harness-driver-capabilities.yaml)`
   —un espejo mantenido a mano, que es exactamente la enfermedad. Un manifest que
   miente por *falta de vocabulario* se arregla distinto que uno que miente por deriva.

3. **"registration-allowlist.txt tenía 141 asientos inertes… sus 40 asientos vivos".**
   Ese estado ya no existe: el commit `c62e0cba4` ("sacar los asientos fantasma y medir
   la ocupacion como censo") lo cambió hoy. Hoy el archivo tiene **182 líneas vivas**
   (`grep -vE '^\s*(#|$)' hooks/_lib/registration-allowlist.txt | wc -l`), no 40. No
   remedí cuántas de esas 182 son inertes ahora; el encargo describe el estado previo al
   commit. La conclusión ("hay que borrarlo") sobrevive, la aritmética no.

4. **"1500 filas caen en otro archivo".** No lo verifiqué así y creo que la mecánica es
   otra. `source_metric` es el **6º argumento de texto libre** de
   `primitive_intervention_emit` (`hooks/_lib/primitive-intervention.sh:25`), que lo
   escribe *dentro de la fila* y nunca lo abre; todas las filas van a
   `primitive-interventions.jsonl` **por diseño** (línea 36), no por accidente. El
   defecto es un **puntero colgado**: de los 5 valores de `source_metric` usados en
   `hooks/*.sh`, **2** nombran archivos que no existen
   (`protected-config-write-blocks.jsonl`, `trust-scores.jsonl`). Peor de lo que suena:
   el helper documenta que ese campo "points at the hook-specific metric stream", y
   nada chequea que apunte a algo.

5. **"el guard también bloquea leer esas rutas" — el informe `instalador-borra-rules-2026-08-19.md`
   §3 dice que NO se reprodujo. Es falso: lo reproduje dos veces hoy.** Un `python3 - <<PY`
   que solo hacía `json.load` de `.claude/settings.json` fue bloqueado, y un
   `grep -rn "..." hooks/_lib/` también. En cambio `cat hooks/_lib/safe-jsonl.sh` **no**
   se bloqueó. El disparo depende de la forma del comando, no de si escribe. Ya existe
   `docs/06-Daily/reports/protected-config-guard-falsos-positivos-2026-08-19.md`; lo que
   corrijo es la afirmación "no se reprodujo" que quedó escrita en el otro informe de hoy.

6. **"249 hooks, 193 skills y 369 módulos".** Medido hoy: **257** hooks (255 realpaths),
   **119** `skills/**/SKILL.md` (437 en todo el repo), **370** `.py` en `cos_lib/`, y
   `lib/*.py` no existe (0 archivos). No cambia el argumento —la acumulación es real—
   pero tres de los cuatro números del encargo son de otra medición.

---

## Censo: qué hechos declara el SO y dónde viven

Cada fila es un hecho sobre el propio SO. "Sitios" cuenta lugares donde ese hecho está
**escrito** (no donde se lee). El comando de la columna derecha reproduce el conteo.

| # | Hecho | Realidad (derivable de) | Dónde está escrito | Sitios | Deriva medida hoy |
|---|-------|--------------------------|--------------------|:---:|---|
| **H1** | Qué hooks existen | `hooks/*.sh` = 257 (255 realpaths) | `cognitive-os.yaml:harness.hooks` (200), `manifests/hook-quality.yaml` (200), `manifests/hook-registration-classification.yaml` (109), `hooks/_lib/registration-allowlist.txt` (182), `.claude/settings.json` (154 scripts), `manifests/optional-hook-aliases.json`, `docs/…/scorecard-hooks.md` | **7** | 67 archivos sin declarar en `cognitive-os.yaml` |
| **H2** | En qué evento dispara | `settings.json` (162 entradas, 9 eventos) | `settings.json`, `cognitive-os.yaml:…event`, `hook-quality.yaml:…event`, cabecera `# Event:` (24/257), `manifests/harness-hook-projection-policy.yaml`, 4× `scripts/_lib/settings-driver-*.sh` | **6** | 6 cabeceras mentían (encargo); 2 "STAGING: not yet deployed" sobre hooks con 975 y 301 corridas |
| **H3** | Con qué matcher | `settings.json` | `settings.json`, `cognitive-os.yaml`, `hook-quality.yaml`, cabecera `# Matcher:` (10/257) | **4** | cobertura de cabecera 3,9% |
| **H4** | Si es async | `settings.json` (43 `async:true`) | `settings.json`, `cognitive-os.yaml`, cabecera `# Async:` (13/257), `forced_async()` en el driver opencode | **4** | `skill-md-routing-validator.sh` declaraba `Async: true`, registrado sin la clave |
| **H5** | Qué scope tiene | cabecera `# SCOPE:` (**257/257**) | cabecera, `primitive-scope-classification.yaml`, `primitive-scope-overrides.yaml`, `primitive-install-boundary.yaml` | **4** (1 con gate) | **0** — el único hecho con gate de censo |
| **H6** | Cuánto tarda | `.cognitive-os/metrics/hook-timing.jsonl` (+ `.gz` rotados) | cabecera `# Latency:` (4/257), `hook-quality.yaml:max_runtime_ms` (200) | **3** | latencias declaradas 10× abajo de la medida |
| **H7** | Qué test lo cubre | árbol de tests (1215 `.py` en 6 lanes) | `hook-quality.yaml:{behavior,census,false_positive}_tests` (200 registros) | **2** | un test contaba como cobertura por mencionar el nombre en un comentario |
| **H8** | Si puede bloquear | `exit 2` en el código + telemetría | `hook-quality.yaml:{maturity,safe_degradation}`, `manifests/hook-vitality-budget.yaml`, prosa de cabecera | **4** | un hook declarado `block` que no puede bloquear |
| **H9** | A qué JSONL escribe | `.cognitive-os/metrics/` = 122 archivos | 61 rutas literales en `hooks/*.sh`, 5 valores de `source_metric` | **3** | 23/61 rutas declaradas no existen; 2/5 `source_metric` colgados |
| **A1** | Qué arneses hay y qué soportan | los 4 `settings-driver-*.sh` + `cos-primitive-guard.js` | `manifests/harness-projection.yaml` (27), `manifests/harness-driver-capabilities.yaml` (4), `portable_ai_overlay.py:31` (8), `primitive_harness_coverage.py:35` (3), `COS_TO_OPENCODE_EVENT`, `SCRIPT_PROJECTION_EXCLUDED_EVENTS`, `cos_lib/harness_adapter/`, docs | **8** | **4 conteos distintos** del mismo hecho: 27 / 8 / 4 / 3 |
| **I1** | Qué rules se instalan | `manifests/primitive-install-boundary.yaml` (17) | ese manifest, `cos_init.py:DEFAULT_RULES`, `cos-init-global.sh:50` (14), `cmd/cos/internal/wizard/install.go:270` (14), `hooks/self-install.sh:CORE_RULES` (2), lista fija en `tests/behavior/test_cos_index_and_global_init.py:117` (14), texto de `--help`, `rules/*.md` (131) | **8** | **dos rules borradas en silencio en disco ajeno**, exit 0 |
| **R1** | Qué rules existen | `rules/*.md` = 131 | `rules/RULES-COMPACT.md` (índice a mano), `manifests/rule-routing-coverage.yaml`, `templates/agent-mandatory-rules.md`, `rules/ROADMAP.md §1` | **5** | `ROADMAP §1` lista hooks "no registrados" mantenida a mano |
| | **TOTAL** | | | **56** | |

**Lectura de la tabla.** No hay un solo hecho con un sitio. El hecho con **menos** sitios
(H7, 2) es el que produjo la falsa cobertura; el que tiene **más** (A1 e I1, 8) produjo
el bug que llegó a una máquina ajena. La correlación no es sitios→daño: es
**sitios sin derivador**→daño. H5 tiene 4 sitios y deriva 0, porque uno de esos 4 se
recomputa del árbol en cada corrida y falla si falta.

### El experimento que ya corrió en este repo

No hace falta discutir si el mecanismo funciona. Las cinco claves de cabecera de los
hooks son un experimento controlado: mismos archivos, mismos autores, misma semana.

| Clave | Gate que la deriva | Cobertura | Deriva conocida |
|---|---|---:|---|
| `# SCOPE:` | `scripts/cos-scope-projection-audit` (censo del árbol) | **257/257 (100%)** | 0 |
| `# Event:` | ninguno | 24/257 (9,3%) | sí |
| `# Async:` | ninguno | 13/257 (5,1%) | sí |
| `# Matcher:` | ninguno | 10/257 (3,9%) | sí |
| `# Latency:` | ninguno | 4/257 (1,6%) | sí (10×) |

```bash
grep -hoE '^#\s*(Async|Latency|Event|Matcher|SCOPE)\s*:' hooks/*.sh | sort | uniq -c | sort -rn
#  257 # SCOPE:   24 # Event:   13 # Async:   10 # Matcher:    4 # Latency:
```

Corolario incómodo: **una cabecera al 9% es peor que ninguna.** Al 0% nadie la cree; al
9% el lector asume que la ausencia significa "no aplica" en vez de "nadie la escribió".

---

## Régimen correcto por hecho

El criterio que decide, aplicado literalmente: *si mañana cambia la realidad, ¿este
archivo se actualiza solo, falla, o miente en silencio?*

- **derivado** — no hay archivo; se calcula del árbol al usarlo. Deriva imposible.
- **generado** — hay archivo con marca `generated_by:` y un gate que lo regenera en
  tmpdir y diffea. Deriva ⇒ CI rojo.
- **decidido** — declaración a mano legítima: expresa una *decisión* que ningún
  derivador puede computar (una política, una excepción con motivo, un dueño).

| Hecho | Régimen hoy | Régimen correcto | Por qué |
|---|---|---|---|
| H1 existencia | declarado ×7 | **derivado** | `ls hooks/*.sh` es la respuesta. Ninguna de las 7 copias agrega información. |
| H2 evento | declarado ×6 | **derivado** de `settings.json`; `settings.json` **generado** desde el registro de decisiones | El evento es consecuencia de la decisión "registrar este hook en este perfil", no un dato independiente. |
| H3 matcher | declarado ×4 | **derivado** (ídem H2) | ídem |
| H4 async | declarado ×4 | **decidido** en 1 sitio, **derivado** en los otros 3 | Async **sí** es una decisión (bloqueante vs fire-and-forget) — pero una sola, en el registro, no cuatro copias. |
| H5 scope | 1 derivado + 3 declarados | **derivado** (ya lo es) | Modelo a imitar. Los 3 manifests que lo repiten deberían leer, no declarar. |
| H6 latencia | declarado ×3 | **derivado con `Census`** | Es telemetría con ceguera (rotación a `.gz`): un entero pelado acá es deshonesto. Va sobre `cos_lib/measurement.py`, no sobre `int`. |
| H7 tests | declarado ×2 | **generado** | Derivable, pero caro de recomputar en cada lectura ⇒ se materializa y se revalida. Ya tiene `generated_by:` en la cabecera de `hook-quality.yaml`. |
| H8 puede bloquear | declarado ×4 | **decidido** (`maturity`) + **derivado** (`exit 2` existe en el código) + **`Census`** (se lo vio bloquear) | Tres cosas distintas que hoy comparten una palabra. Ese aplanamiento **es** el bug: "declarado block" tapaba "no tiene `exit 2`". |
| H9 sumidero JSONL | declarado en el código | **derivado**, y el destino **debe existir o ser creado por el emisor** | Una ruta que nadie abre no es una ruta, es un string. |
| A1 arneses | declarado ×8 | **derivado** del driver + **decidido** el `status` (con vocabulario nuevo: `script-projection` vs `inline-classifier`) | El manifest no puede saber lo que el driver decide; el driver sí sabe lo que proyecta. |
| I1 install set | declarado ×8 | **derivado** de `primitive-install-boundary.yaml`, que es el **decidido** | El manifest *es* la decisión de producto; las otras 7 copias son ruido con poder de borrar archivos. |
| R1 rules | declarado ×5 | **derivado** (`rules/*.md`) + **decidido** (`RULES-COMPACT.md` como índice curado) | El índice tiene valor editorial; la *lista* no. |

Regla general que sale del cuadro: **una declaración sin lector programático es un
comentario; una declaración con lector pero sin gate contra la realidad es un pasivo.**
Los 56 sitios se reparten hoy: ~6 con gate, el resto pasivos o comentarios disfrazados
de config.

---

## El mecanismo propuesto

**Nombre de trabajo: "un hecho, un derivador".** Tres piezas, y la tercera es la que
evita el problema recursivo.

### 1. El derivador es la única fuente

Para cada hecho derivable, una función `derive(repo_root) -> value` que lee el árbol. No
hay archivo intermedio salvo que la derivación sea cara (H7). Los sitios que hoy declaran
pasan a **llamar** al derivador. `scripts/cos-scope-projection-audit` ya es exactamente
esto para H5, y `tests/contracts/test_shipped_audits_declare_population.py` lo dice en su
propio código: *"Censo, no lista: se recalcula del árbol, así que un script nuevo entra solo."*

### 2. El espejo declara que es espejo

Donde el archivo generado es necesario (H7, y `settings.json` que un tercero consume),
lleva `generated_by:` y el gate lo regenera en tmpdir y diffea. `hook-quality.yaml` ya
tiene esa cabecera — lo que le falta es **partir el registro**: hoy mezcla campos
derivados (`script`, `event`, `matcher`, `scope`) con decididos (`criticality`,
`maturity`, `bypass_policy`) en el mismo diccionario, así que nadie sabe qué pisa un
`--sync` y por eso el `--sync` no está gateado. Dos sub-diccionarios, `derived:` y
`decided:`, y el `--sync` puede correr sin miedo.

### 3. Cada gate trae su propia mutación (esto es lo que impide la recursión)

El riesgo que el encargo nombra —"un verificador de declaraciones que hay que mantener a
mano"— se evita con dos restricciones duras:

- **Un gate, N hechos.** El gate hace censo del módulo de derivadores (no lista fija).
  Agregar el hecho 13 cuesta **cero líneas** en el gate. Si agregar un hecho obliga a
  editar el gate, el diseño ya falló y hay que tirarlo.
- **Cada derivador declara su `mutation`**: una perturbación mínima aplicable en tmpdir
  (crear `hooks/zz-fake.sh`, cambiar un `event`, borrar una rule del manifest) sobre la
  que el gate **debe** fallar. Es el mismo contrato que
  `manifests/proof-drill-registry.yaml` ya define para otras guardas, y es lo que
  distingue este gate de "una regla instalada que nunca se vio disparar", que
  `gates-sin-trampa` clasifica como bug.

### 4. Dónde NO va

- **No es un hook.** Hay 257. Un hook que valida declaraciones en cada tool-call es el
  problema recursivo con latencia. Va a la lane de tests + un `scripts/cos-fact-audit`
  de censo, corrible a mano.
- **No es un manifest nuevo.** Hay 137. Si el diseño termina en
  `manifests/fact-registry.yaml`, es el sitio 57.
- **No es un framework todavía.** Ver *Camino de migración*, paso 0.

### 5. Lo que este mecanismo NO puede hacer

Dicho al principio para que nadie confíe de más, como hace `measurement.py`:
no impide que alguien escriba un comentario con un número, ni que un `decided:` diga una
mentira (solo exige motivo y dueño), ni distingue "el hook evaluó y no encontró nada" de
"el hook no corrió" — eso es **D**, y sin D el gate de H9 produce 23 falsos positivos.

---

## Qué desaparece

Un diseño que solo agrega es parte del problema. Neto: **−1 manifest, −1 lista, −5 listas
fijas, −51 líneas de cabecera, −4 aserciones invertidas**; se agregan ~12 derivadores y 1 gate.

1. **`hooks/_lib/registration-allowlist.txt`** (182 líneas vivas) — borrado completo, junto
   con su lectura en `tests/audit/test_registration_allowlist_seats.py`,
   `tests/architecture/test_wiring.py`, `tests/audit/test_hooks_contracts.py` y
   `tests/audit/test_rules_enforcement.py`. Ese último usa la presencia en el allowlist
   como prueba de registro: **la aserción está invertida** (el allowlist lista lo que *no*
   está registrado). Un test invertido es peor que ningún test.
2. **Las 4 claves de cabecera decorativas**: `# Event:` (24), `# Async:` (13),
   `# Matcher:` (10), `# Latency:` (4) = **51 líneas** en 257 archivos. Se queda `# SCOPE:`,
   que es fuente primaria y tiene gate.
3. **`manifests/harness-driver-capabilities.yaml`** (217 líneas) — derivable de los 4
   `settings-driver-*.sh` más `cos-primitive-guard.js`. El comentario
   `# OpenCode capability matrix (mirror manifests/…)` desaparece con él.
4. **`DEFAULT_HARNESSES`** en `scripts/portable_ai_overlay.py:31` (8) y en
   `scripts/primitive_harness_coverage.py:35` (3) — dos constantes, dos poblaciones, un hecho.
5. **Tres listas de core rules**: `scripts/cos-init-global.sh:50` (14),
   `cmd/cos/internal/wizard/install.go:270` (14, con un comentario que promete un
   sincronismo que ya no existe) y la lista fija de
   `tests/behavior/test_cos_index_and_global_init.py:117` (14).
6. **La mitad estructural de una de las dos registries de 200.** `cognitive-os.yaml:harness.hooks`
   y `manifests/hook-quality.yaml` declaran ambos 200 hooks con `script`+`event`+`scope`.
   Propuesta: `cognitive-os.yaml` se queda como registro de **decisiones** (qué se registra,
   en qué perfil, async sí/no) y `hook-quality.yaml` pierde `script`/`event`/`matcher`/`scope`,
   que pasan a `derived:` regenerado.

**Lo que NO se borra y por qué**: `manifests/hook-registration-classification.yaml` (109
entradas) sobrevive — es el único de los siete sitios de H1 que guarda una **decisión con
motivo** (`status` + `rationale` + `next_action`). Es el modelo de lo que un `decided:`
debe parecer.

---

## Camino de migración

Ordenado por daño de la deriva, no por facilidad. Cada paso nombra su gate y **cómo se
prueba que el gate puede ponerse en rojo** — sin eso el paso no cuenta como hecho.

**Paso 0 — no construir el framework.** Escribir los pasos 1, 2 y 5 como tres derivadores
concretos e independientes. Solo si los tres comparten forma, extraer el tipo. El repo
tiene 137 manifests y 144 scripts con `audit|census|check` en el nombre porque la
abstracción llegó antes que los tres casos.

| # | Hecho | Qué se hace | Gate | Prueba de rojo |
|---|---|---|---|---|
| **1** | **I1 instalación** | Cerrar lo empezado hoy: derivar las 3 listas restantes de `primitive-install-boundary.yaml` | `tests/integration/test_install_rules_manifest_parity.py` (ya escrito hoy, aún untracked) | **Ya visto en rojo**: con el bug falla nombrando `model-routing.md` y `result-management.md`. Único paso con rojo demostrado. |
| **2** | **H2/H3/H4** evento, matcher, async | Derivar de `settings.json`; borrar las 47 cabeceras `# Event:`/`# Async:`/`# Matcher:` | gate derivador nuevo, lane `tests/contracts` | Mutación: cambiar el `event` de un hook en un `settings.json` de tmpdir ⇒ debe nombrar el hook |
| **3** | **H1** existencia | Colapsar 7 registries a 1 derivador + `hook-registration-classification.yaml` como decidido; borrar el allowlist y arreglar la aserción invertida | mismo gate | Mutación: `touch hooks/zz-fake.sh` en un worktree ⇒ debe nombrarlo. Correr en `git worktree add`, no en el checkout (los scanners caminan el filesystem, no el índice) |
| **4** | **H9** sumideros | Exigir que cada ruta declarada exista o la cree el emisor; matar los 2 `source_metric` colgados | gate + `Census` | **BLOQUEADO POR D.** Sin el veredicto "no corrió" vs "corrió y no emitió", 23 de 61 rutas dan falso positivo |
| **5** | **A1** arneses | Derivar del driver; borrar el manifest y las 2 `DEFAULT_HARNESSES`; agregar vocabulario `script-projection` / `inline-classifier` | gate derivador | Mutación: quitar `PreToolUse` de `COS_TO_OPENCODE_EVENT` ⇒ debe fallar |
| **6** | **H6/H8** latencia, capacidad de bloquear | Reescribir sobre `Census`, no sobre `int`; separar las tres cosas que `maturity` aplana | `manifests/hook-vitality-budget.yaml` (ya existe, ratchet sin colchón) | Mutación: subir el budget 1 por encima de la realidad ⇒ el audit ya falla por colchón |
| **7** | **H7/R1** | Partir `hook-quality.yaml` en `derived:`/`decided:` y gatear el `--sync` | regeneración en tmpdir + diff | Mutación: editar a mano un campo `derived:` ⇒ diff no vacío |

Los pasos 2, 3 y 5 son independientes entre sí y paralelizables. El 4 espera a D. El 6 y
el 7 son limpieza posterior y podrían no hacerse nunca sin que se rompa nada.

---

## Costo

**CI.** La referencia medida hoy, con el reloj:

```bash
/usr/bin/time -p python3 scripts/cos-scope-projection-audit --json   # real 0.48 s, 1480 artefactos
/usr/bin/time -p python3 scripts/hook_quality_audit.py --json        # real 19.88 s, 200 hooks
```

Los 0,48 s son el costo real de un derivador: parsear el árbol. Los 19,88 s de
`hook_quality_audit` **no son derivación**: son 200 `bash -n` (`syntax_checked: 200`), un
trabajo distinto que hoy viaja pegado. Separarlos baja el gate de H1/H2/H3 a ~1 s y deja
el syntax-check donde corresponde (lane de lint, no de contratos). **Costo incremental de
CI de los pasos 1-3 y 5: ~2 s**, contra una suite que ya corre 1215 archivos de test.

**Tokens por turno: 0.** Nada de esto es un hook ni entra al contexto. Es la diferencia
que más importa: la alternativa obvia —un PreToolUse que valide declaraciones— costaría
latencia en cada tool-call, y el driver de opencode ya documenta por qué eso no se hace
("130+ serial bash spawns to every single tool invocation").

**Mantenimiento del mecanismo (el problema recursivo).** ~12 derivadores de 40-60 líneas
= 500-700 líneas nuevas, más 1 gate que **no crece con los hechos**. Contra eso, lo que se
deja de mantener: 56 sitios de declaración a mano, de los cuales se borran ~10 archivos y
51 líneas de cabecera. El riesgo real no es el volumen sino la forma: si en 6 meses el
gate tiene una lista de excepciones, se volvió el sitio 57. Mitigación escrita en el
diseño: **el gate no admite baseline de excepciones**; un hecho o tiene derivador o está
declarado como `decided` con motivo y dueño. (Es el mismo criterio de igualdad exacta que
usa `tests/contracts/test_shipped_audits_declare_population.py`, que ni siquiera acepta
absorber un script nuevo.)

**Costo humano de la migración**: los pasos 1-3 y 5 son ~4 agentes sonnet de una sesión
cada uno. El paso 3 es el único que toca muchos archivos (borrar 51 líneas de cabecera en
47 hooks) y es puramente sustractivo.

---

## Qué de A, C y D subsume este diseño

**C (la abstracción de arneses tiene fugas) — subsumido entero.** Es el hecho **A1** de mi
censo. Los 9 archivos que hardcodean la convención de transcripts de Claude Code son
espejos sin derivador de un hecho —"dónde vive el transcript de este arnés"— que hoy no
tiene fuente en ningún lado. La forma es idéntica a los 4 conteos distintos de "cuántos
arneses hay" (27/8/4/3). El repo ya se movió en esa dirección hoy con
`1d77fa1af fix(audit): derivar el glob de transcripts en vez de hardcodear un checkout`:
eso es un derivador, escrito a mano, para un hecho. **Recomendación: C no necesita diseño
propio; necesita dos derivadores más (transcript-path y capability) y entra en mi paso 5.**

**A (señal sin consumidor) — subsumido solo en una esquina, y es el dual, no el mismo
problema.** B dice "la declaración no coincide con la realidad"; A dice "la realidad no
tiene quien la lea". Un derivador no crea un lector: puedo probar que
`agent-heartbeat.jsonl` se escribe correctamente y eso no hace que alguien lo abra. La
esquina que sí subsumo es exacta y vale: **un emisor que declara un destino inexistente**
—los 2 `source_metric` colgados, las 23 de 61 rutas ausentes— es un consumidor *declarado*
que no está, y eso mi gate H9 lo agarra. **Recomendación: A conserva diseño propio, pero
debería sacar de su alcance la parte "el destino declarado no existe" y dejármela.**

**D (no distingue "evalué y todo bien" de "no corrí") — NO lo subsumo: dependo de él.**
Dos vínculos duros. (1) Mi paso 4 es imposible sin el veredicto de D: "el archivo no
existe" significa hoy indistintamente "la ruta está mal" o "el hook nunca disparó", y sin
separarlas mi gate produce 23 falsos positivos y se lo apaga con un baseline —el verde
barato de manual. (2) Mis hechos runtime (H6 latencia, H8 capacidad de bloquear) se
construyen **sobre** `cos_lib/measurement.py`, la pieza de D que ya existe: un
`Census` con población y ceguera declaradas, no un `int`. **Recomendación: D es
prerequisito, o al menos debe cerrar antes del paso 4. Si hay que elegir uno solo, D
primero — porque sin él mi paso 4 no es implementable y los pasos 1-3 sí lo son sin nada
de A ni de C.**

Orden sugerido para el operador: **B(1-3) ‖ D → B(4) ; B(5)+C ; A**.

---

## La opción de no hacer nada

La considero en serio porque el argumento a favor es fuerte y hay que refutarlo con
números, no con principios.

**A favor.** Los 15 commits de hoy corrigieron 15 derivas a mano, cada uno con un agente
sonnet de una sesión. Si el ritmo es ~15/día en una sesión intensa de mantenimiento y
mucho menos en régimen normal, el costo anual de corregir a mano es del orden de decenas
de sesiones, y **el diagnóstico llegó gratis**: las 15 derivas se descubrieron mirando, sin
ningún mecanismo. Además el repo ya tiene 137 manifests, 144 scripts de auditoría y 257
hooks precisamente porque cada problema mereció su artefacto. El costo marginal de un
artefacto más no es su código: es que dentro de un año va a estar en la lista de cosas que
declaran algo que ya no hacen. La opción "aceptar el ruido y seguir corrigiendo" tiene un
historial de acierto en este repo que no hay que despreciar.

**En contra, y es decisivo.** La corrección a mano tiene una precondición: **que alguien
mire**. Las 15 derivas de hoy se descubrieron porque un operador estaba mirando el SO desde
adentro. El caso del instalador no cumple esa precondición: `cos_init.py --default` dejó
15 rules en vez de 17, con **exit 0 y cero warnings**, en el directorio de otra persona que
no lee este repo, no corre estas auditorías y no tiene forma de saber que le faltan dos
rules. Ahí el ciclo "deriva → alguien la ve → agente la corrige" nunca arranca. El
`# SCOPE:` al 100% contra `# Event:` al 9,3% muestra la otra mitad: donde no hay gate, la
disciplina no escala ni entre los propios mantenedores.

**Veredicto.** No hacer nada es la respuesta correcta para **H6, H7 y R1** —hechos internos,
cuyo lector es quien los escribió, donde una deriva cuesta una corrección barata. Es la
respuesta **incorrecta** para **I1** (llega a un tercero), **A1** (define si un arnés está
protegido o no) y **H2/H3/H4** (define si una guarda corre). Por eso la recomendación es un
subconjunto —4 hechos de 12— y no un programa. Y por eso el paso 0 es no construir el
framework: si a los tres derivadores concretos no les sale una forma común, la conclusión
honesta es quedarse con los tres derivadores sueltos y no tener mecanismo general.

---

## Comandos de este informe

```bash
ls hooks/*.sh | wc -l                                    # 257
for f in hooks/*.sh; do readlink -f "$f"; done | sort -u | wc -l   # 255
grep -hoE '^#\s*(Async|Latency|Event|Matcher|SCOPE)\s*:' hooks/*.sh | sort | uniq -c | sort -rn
grep -vE '^\s*(#|$)' hooks/_lib/registration-allowlist.txt | wc -l # 182
grep -rhoE '\.cognitive-os/metrics/[A-Za-z0-9_.\-]+\.jsonl' hooks/*.sh | sort -u | wc -l   # 61
ls .cognitive-os/metrics/*.jsonl | wc -l                 # 122
python3 -c "import yaml;print(len(yaml.safe_load(open('manifests/harness-projection.yaml'))['harnesses']))"  # 27
/usr/bin/time -p python3 scripts/cos-scope-projection-audit --json  # real 0.48
/usr/bin/time -p python3 scripts/hook_quality_audit.py --json       # real 19.88
```

El conteo de "23 de 61 rutas declaradas que no existen" se reproduce con:

```bash
grep -rhoE '\.cognitive-os/metrics/[A-Za-z0-9_.\-]+\.jsonl' hooks/*.sh | sort -u \
  | while read -r p; do [ -f "$p" ] || echo "MISS $p"; done | wc -l   # 23
```

# Linters y escáneres como catálogos de reglas: qué saben de sus propias reglas

**Fecha:** 2026-08-19
**Tipo:** investigación web (documentación oficial + repos upstream)
**Pregunta de origen:** el SO declara ~130 reglas sin señal de cuál se carga ni cuál
aplica, y tiene baselines que pueden quedar por encima de la realidad. ¿Cómo resuelven
esto las herramientas que administran cientos de reglas hace años?

**Alcance:** patrones y contratos, no código. No se leyó fuente de ninguna herramienta;
todo sale de documentación pública e issues del tracker upstream.

---

## Correcciones a las premisas del encargo

1. **"131 reglas declaradas" — el número cuenta dos archivos que no son reglas.**
   `ls rules/*.md | wc -l` devuelve 131, pero incluye `rules/ROADMAP.md` (roadmap de
   hooks sin registrar) y `rules/RULES-COMPACT.md` (el índice). Reglas propiamente
   dichas: **129**.

2. **"cero señal de cuáles se cargan o aplican" — hay señal de cuáles *tienen hook*,
   no de cuáles *dispararon*.** `rules/RULES-COMPACT.md` separa explícitamente las
   hook-enforced de las agent-instruction-only, y `hooks/self-install.sh:EXCLUDED_RULES`
   es la lista mecánica de exclusión. El faltante no es un inventario: es telemetría de
   disparo. La distinción cambia el arreglo (no hay que censar, hay que instrumentar), y
   es la misma que hacen ESLint y Semgrep entre "regla configurada" y "regla que produjo
   un hallazgo".

3. **"un baseline por encima de la realidad acepta violaciones nuevas" — ya está
   arreglado para los baselines de conteo.** `scripts/scope_closure_gate.py` implementa
   el chequeo bilateral: falla cuando el conteo *excede* el baseline y también cuando
   está *por debajo* (`FAIL — baseline is above reality (a cushion that accepts silent
   debt)`, línea 396). El gap real vive en los baselines de **identidades**
   (`volatile_number_audit.py`, `lint-shell.sh --new-only`,
   `cos_quality_duplicates.py::apply_ratchet`), que calculan `nuevos = actual − baseline`
   y nunca `huérfanos = baseline − actual`. Son dos bugs distintos con dos arreglos
   distintos, y las herramientas de afuera los tratan por separado.

4. **Confirmado:** `manifests/external-tool-adoption-freeze.yaml` tiene `frozen: true`
   desde 2026-05-11 con `hooks/adoption-freeze-gate.sh` como gate. La restricción del
   encargo se sostiene: nada de este informe propone adoptar código.

---

## P1 — ¿Reportan reglas habilitadas que nunca dispararon?

**Respuesta corta: en una corrida, sí, pero siempre por resta. Acumulado en el tiempo,
ningún CLI lo hace — lo hacen las plataformas, y el mejor patrón documentado no mide
"disparó" sino "alguien actuó".**

### El catálogo y los resultados son dos listas, y la resta es el reporte

Ninguna herramienta expone un "reglas que no dispararon". Todas exponen las dos listas y
dejan la resta al consumidor:

| Herramienta | Catálogo de lo que corrió | Hallazgos | La resta |
|---|---|---|---|
| SARIF / CodeQL | `runs[].tool.driver.rules[]` (array de `reportingDescriptor`) | `results[].ruleId` / `ruleIndex` | `driver.rules − distinct(results.ruleId)` |
| ESLint | `eslint --print-config <file>`, o `@eslint/config-inspector` | `ruleId` en el JSON de resultados | idem |
| Semgrep | `--time` con salida JSON | `results[].check_id` | idem, pero granular (ver abajo) |

La doc de GitHub sobre SARIF da el argumento de por qué el catálogo sirve de referencia
estable: al comparar SARIF de distintos codebases con la misma herramienta y reglas
*"you should see differences in the results of the analyses but not in the rules"*. El
catálogo no depende del código analizado; los resultados sí. Esa asimetría es lo que
convierte la resta en una medida de cobertura.

### Semgrep `--time` es el más cercano a lo que falta acá

`--time`: *"Include a timing summary with the results. If output format is json,
provides times for each pair (rule, target)."* El par **(regla, target)** existe aunque
no haya match. O sea: la salida dice "esta regla se evaluó contra estos N archivos", y
cruzarlo con findings da "se evaluó 400 veces y produjo 0". Eso separa `0 porque no hay
nada` de `0 porque nunca se evaluó` sin instrumentar nada extra.

### ESLint `--stats` NO sirve para esto (trampa a evitar)

`--stats` produce `times.passes[].rules`, y cada regla trae **solo** `total` en ms. No
hay conteos, ni tallies de errores/warnings por regla. Sirve para "corrió y tardó X", no
para "encontró". Si alguien acá espera que un flag tipo `--stats` resuelva P1, va a
terminar con tiempos y sin cobertura.

Para el lado del catálogo, ESLint sí tiene herramienta dedicada: `@eslint/config-inspector`
(oficial, org `eslint`) levanta un server local que muestra qué reglas están activas por
qué objeto de config, cuáles están deprecadas, y **cuántas de las reglas disponibles
estás usando**. Es censo de configuración, no de disparo — pero es el censo que hoy acá
no existe en forma consultable.

### Acumulado en el tiempo: el patrón es Tricorder, no un flag

Ningún CLI acumula. Las plataformas (Semgrep AppSec Platform, SonarQube por facetas de
issues por regla) guardan histórico, pero el patrón realmente transferible es el de
Google, documentado en CACM 2018 y en el paper de Tricorder (ICSE 2015):

- La métrica no es "la regla disparó", es **"alguien accionó el hallazgo"**. Botón
  *"Not useful"* en el flujo de code review, ~250 clicks por día medidos.
- Tope duro: hasta **10% de falsos positivos efectivos** en lo que se muestra en review.
- Los analizadores que no se accionan salen de la plataforma. La decisión es del
  desarrollador que recibe el hallazgo, no del autor de la regla — *"developers, not tool
  authors, will determine and act on a tool's perceived false-positive rate"*.

Traducido: una regla que dispara todo el tiempo y que nadie obedece está tan rota como
una que nunca dispara. Medir solo disparos deja la mitad afuera.

---

## P2 — Supresión huérfana: cómo la detectan

**Este es el mecanismo mejor resuelto de todos los que se revisaron. Es first-class en
ocho herramientas distintas y hay dos familias de diseño.**

### Familia A — reporte separado, hay que prenderlo

| Herramienta | Mecanismo | Default | Nota |
|---|---|---|---|
| ESLint | `linterOptions.reportUnusedDisableDirectives` + `--report-unused-disable-directives-severity` | `"warn"` en flat config | Desde el PR eslint#17611 también marca `eslint-enable` que no des-suprime nada |
| ESLint | `linterOptions.reportUnusedInlineConfigs` (v9.19.0) + `--report-unused-inline-configs` | off | Reporta config inline cuya severidad y opciones **ya coinciden** con lo configurado |
| Ruff | `RUF100` / `unused-noqa`, con `--fix` que las borra | off (opt-in vía select) | *"enforce that your suppressions are 'valid', in that the violations they say they ignore are actually being triggered and suppressed"* |
| Pylint | `useless-suppression` / `I0021` | off, y **no rompe el build** salvo `--fail-on=I0021` | *"reported when a message is explicitly disabled for a line or a block of code, but never triggered"* |
| mypy | `--warn-unused-ignores` o `enable_error_code = unused-ignore` | off | ver P4: exceptúa código inalcanzable |
| golangci-lint | `nolintlint` con `allow-unused: false` | linter opt-in | Agujero conocido (discussion #2395): si el linter objetivo está deshabilitado, el `nolint` huérfano no se reporta |
| PHPStan | `reportUnmatchedIgnoredErrors` | **`true`** | El único con default fatal. Por entrada: `reportUnmatched: true/false` |
| eslint-plugin-eslint-comments | `no-unused-disable` | plugin externo | El predecesor del flag nativo de ESLint |

### Familia B — la supresión es su propio test

`@ts-expect-error` de TypeScript (3.9+): si la línea siguiente **no** tiene error, el
compilador reporta que el directivo no era necesario. No hay flag que prender ni reporte
separado que leer: la supresión falla sola cuando deja de suprimir. El argumento de la
doc contra `@ts-ignore` es exactamente el problema del encargo — *"no way to know if a
`@ts-ignore` is actually suppressing an error without manually investigating what happens
when the `@ts-ignore` is removed"*, y si aparece un error nuevo en esa línea queda
tapado por el ignore olvidado.

**La lección de diseño está en la diferencia entre las dos familias.** La familia A
depende de que alguien prendió el flag; siete de ocho vienen apagadas por default y dos
(Pylint, golangci-lint) además no rompen el build sin configuración extra. La familia B
no se puede olvidar de prender. Cualquier mecanismo que se diseñe acá debería tender a
B: que el artefacto de supresión sea, él mismo, la aserción que falla.

---

## P3 — Baseline por encima de la realidad

**Respuesta corta: solo uno de los cuatro reconcilia hacia abajo solo, y es el que trata
el baseline como snapshot descartable en vez de como registro de deuda.**

| Herramienta | Detecta el colchón | Reconcilia sola | Cómo |
|---|---|---|---|
| Android Lint | Sí | No | `LintBaselineFixed` |
| PHPStan | Sí | No | `reportUnmatchedIgnoredErrors: true` |
| Betterer | N/A (no puede quedar arriba) | **Sí** | reescribe el snapshot en cada mejora |
| SonarQube | N/A (no hay baseline de conteo) | N/A | mueve la línea de tiempo, no congela un número |

**Android Lint** tiene dos issue-ids reservados para hablar del baseline mismo:
`LintBaseline` (informativo: cuántos se filtraron) y `LintBaselineFixed`, que reporta
issues que estaban en el baseline y ya no aparecen. La doc: *"it also keeps track of
issues that are not reported anymore"*, y el motivo declarado es *"so you can optionally
re-create the baseline to prevent the error from coming back undetected"* — es decir, la
herramienta nombra el problema del colchón exactamente. La reconciliación es manual:
borrar el archivo y regenerar.

**PHPStan** es el único con el chequeo prendido por default: si un patrón ignorado deja
de matchear, falla. La reconciliación sigue siendo manual — el issue phpstan#4502 pide un
`--remove-ignored-errors-from-baseline` que todavía no existe, y el ecosistema tapó el
hueco con herramientas de terceros (`phpstan-baseline-guard`) cuyo único trabajo es que
el baseline solo pueda achicarse.

**Betterer** es el caso interesante: *"By default Betterer will only update the results
file when your test results improve."* Mejor → reescribe el snapshot; peor → error. El
baseline nunca queda por encima de la realidad porque se regenera en cada corrida buena.
El costo está en la letra chica: el archivo de resultados deja de ser un registro de
deuda aceptada y pasa a ser una foto de ayer. No hay "esto se aceptó tal día por tal
motivo".

**SonarQube** esquiva el problema entero: no hay baseline de conteo, hay *new code
period*. Que la deuda vieja baje no le abre lugar a deuda nueva, porque el gate no se
evalúa contra un total sino contra el código nuevo. Es una salida arquitectónica, no un
chequeo.

### La regla que sale de los cuatro

Un baseline de **conteo** necesita chequeo bilateral (o auto-reescritura tipo Betterer).
Un baseline de **identidades** necesita reporte de huérfanos. No son el mismo arreglo, y
tenerlos mezclados es lo que hace que "arreglamos el baseline" suene resuelto cuando la
mitad sigue abierta.

---

## P4 — "Regla no aplicable" vs "regla rota"

**Respuesta corta: nadie saca esa distinción de la corrida de producción. La sacan de un
fixture que la regla *debe* hacer disparar.**

En producción, `0 hallazgos` es ambiguo por construcción. Las herramientas resuelven la
ambigüedad por dos caminos:

### 1. Prueba de vida por fixture (el camino principal)

- **Semgrep `--test`**: cada regla trae archivo de prueba con anotaciones
  `ruleid:<RULE_ID>` (verdadero positivo, protege contra falsos negativos), `ok:<RULE_ID>`
  (verdadero negativo, protege contra falsos positivos), más `todoruleid:` / `todook:`
  para lo que todavía no anda. `--test-ignore-todo` separa mecánicamente "esta regla
  todavía no funciona" de "esta regla funciona". Una regla sin fixture es una regla sin
  prueba de vida, y eso es visible.
- **CodeQL `codeql test run`** con archivos `.expected`: mismo contrato.
- **ESLint `RuleTester`**: el array `invalid` es obligatorio — no se puede publicar una
  regla sin al menos un caso que la haga disparar.

### 2. Distinguir "no había nada" de "nunca lo miré"

- **mypy** no reporta `unused-ignore` si el ignore quedó sin usar **porque el código es
  estáticamente inalcanzable** (chequeos de plataforma o versión). Sabe la diferencia
  entre "no hacía falta" y "nunca llegué a mirar esa línea", y solo acusa la primera.
- **Ruff** nombra los dos casos explícitamente en el tracker (issue astral-sh/ruff#8492):
  *"ruff has checked the rule and knows there is no problem in that line, so the noqa is
  not needed"* vs *"ruff has not checked the rule"*. El segundo caso **no** se administra
  borrando el `noqa`: se administra con `lint.external`, *"a list of rule codes or
  prefixes that are unsupported by Ruff, but should be preserved when (e.g.) validating
  `# noqa` directives"*. O sea: hay una lista declarada de "esto no es mío, no opino".
- **CodeQL** tiene *diagnostic queries* (`@kind diagnostic`) que reportan sobre el paso de
  extracción. Si el lenguaje no se extrajo, la query no salió "limpia": no corrió. La CLI
  reporta esos resultados a stdout junto con las métricas de resumen.

### Traducción a observer/guard

Un guard es una regla con un fixture que **falla** sin la regla y **pasa** con ella. Un
observer es una regla declarada sin ese fixture. La corrida limpia sobre el repo real no
prueba nada en ninguna de las dos direcciones, y esperar que la telemetría de producción
zanje la diferencia es el error que las cuatro herramientas evitan. La otra pieza —
`lint.external` de Ruff — dice que hace falta una **tercera** categoría declarada: "regla
que a propósito no evalúo acá", para que su silencio no se confunda con estar rota.

---

## Aplicabilidad concreta acá

| Mecanismo de afuera | ¿Aplica? | Dónde exactamente |
|---|---|---|
| Reporte de huérfanos en baseline de identidades (PHPStan `reportUnmatchedIgnoredErrors`, Android `LintBaselineFixed`) | **Sí, es el gap más grande** | `scripts/volatile_number_audit.py` calcula `new = [f for f in volatile if f.key not in baseline]` y nunca `baseline − actual` (281 entradas aceptadas sin verificar que sigan vivas). Igual en `scripts/lint-shell.sh --new-only` (solo `comm -13`) y en `scripts/cos_quality_duplicates.py::apply_ratchet`, que expone `baseline_findings` y `current_findings` pero no falla ni enumera huérfanos cuando el primero supera al segundo |
| Chequeo bilateral de baseline de conteo | **Ya implementado, falta propagarlo** | `scripts/scope_closure_gate.py` líneas 57-64 y 388-398. Es el patrón a copiar hacia adentro, no algo a importar de afuera |
| Prueba de vida por fixture (Semgrep `ruleid:`, ESLint `RuleTester.invalid`) | **Sí** | 129 reglas en `rules/`, ninguna con fixture asociado que pruebe que su hook dispara. Es la respuesta al observer/guard sin prueba |
| Categoría declarada "no evalúo esto acá" (`lint.external` de Ruff) | **Sí** | `hooks/self-install.sh:EXCLUDED_RULES` ya es esa lista; lo que falta es que el silencio de una regla excluida se reporte como *excluida*, no como *limpia* |
| Catálogo consultable de reglas activas (`@eslint/config-inspector`) | Parcial | `rules/RULES-COMPACT.md` cumple la función a mano; el riesgo es que se desincronice de `.claude/settings.json`, que es donde vive la verdad de qué hook está registrado |
| Resta catálogo − disparos por corrida (SARIF, Semgrep `--time`) | Sí, pero necesita telemetría que hoy no existe | No hay JSONL de "regla evaluada"; los `.cognitive-os/*.jsonl` registran eventos de hooks, no evaluaciones de reglas |
| Auto-reconciliación hacia abajo (Betterer) | **No para identidades**, sí para conteos | Ver "lo que no se puede transplantar" |
| Métrica de accionabilidad (Tricorder) | Como principio, no como estadística | N=1 operador; no hay volumen para un ratio de falsos positivos |

---

## Lo que NO se puede transplantar

1. **Nada de código, de ninguna de las once herramientas.**
   `manifests/external-tool-adoption-freeze.yaml` está `frozen: true` desde 2026-05-11
   con `hooks/adoption-freeze-gate.sh` bloqueando las rutas gateadas. Este informe es
   prosa sobre contratos públicos; no se leyó fuente de ninguna herramienta y no se
   propone vendorizar nada. Si alguna vez alguien quisiera mirar código, la licencia hay
   que verificarla **antes** de abrir el archivo, no después — y al menos dos casos
   (reglas de Semgrep CE bajo Semgrep Rules License, ediciones comerciales de SonarQube)
   no son MIT/BSD/Apache y caen bajo el criterio de `license-policy`.

2. **`@ts-expect-error` como diseño, no como implementación.**
   Funciona porque el compilador ya calcula el conjunto de errores por línea: el
   directivo se limita a preguntarle al motor. Acá no hay motor que sepa "esta regla se
   evaluó sobre este archivo". Un `expect-trigger` para reglas del SO, sin ese motor,
   sería una aserción sin nadie que la evalúe — o sea, exactamente el observer que se
   quiere eliminar, con otro nombre. Primero el motor (telemetría de evaluación), después
   el directivo autoverificable.

3. **La auto-reconciliación de Betterer, aplicada a baselines de identidades.**
   Reescribir el archivo en cada corrida verde funciona cuando el baseline es un snapshot
   descartable. Acá `manifests/volatile-number-baseline.json` y
   `manifests/ast-similarity-baseline.yaml` son **registros de deuda aceptada con motivo
   escrito**; regenerarlos automáticamente borra quién aceptó qué y cuándo, que es
   justamente lo que `gates-sin-trampa` exige preservar. El patrón de Betterer transplanta
   a los baselines de **conteo** (donde ya está resuelto por otra vía) y no a los de
   identidades.

4. **La estadística de Tricorder.**
   El 10% de falsos positivos efectivos y el botón *"Not useful"* dependen de miles de
   revisiones diarias y de un punto de inserción en el flujo de code review de una
   organización grande. Con un operador no hay muestra. Lo que sí transplanta es la
   política: una regla que nadie acciona se saca del catálogo, y la decisión es de quien
   recibe el hallazgo, no de quien escribió la regla.

5. **El *new code period* de SonarQube.**
   Esquiva el baseline moviendo la línea de tiempo, pero necesita un servidor con
   histórico por análisis y un concepto de "versión previa" en el proyecto. El SO no tiene
   ninguna de las dos cosas, y montarlas para evitar un chequeo bilateral de diez líneas
   es desproporcionado.

6. **La expectativa de que un flag tipo `--stats` resuelva P1.**
   ESLint `--stats` da tiempos por regla y **nada más** — sin conteos, sin tallies. Copiar
   la forma sin leer el contenido deja un dashboard de milisegundos y la pregunta de
   cobertura igual de abierta.

---

## Tabla de fuentes

| # | Fuente | URL | Qué aporta |
|---|---|---|---|
| 1 | ESLint — Configuration Files | https://eslint.org/docs/latest/use/configure/configuration-files | `reportUnusedDisableDirectives`, default `"warn"` |
| 2 | ESLint — Stats Data | https://eslint.org/docs/latest/extend/stats | forma del objeto `stats`; por regla solo `total` en ms |
| 3 | ESLint — CLI Reference | https://eslint.org/docs/latest/use/command-line-interface | `--stats`, `--report-unused-disable-directives-severity` |
| 4 | ESLint v9.19.0 release notes | https://eslint.org/blog/2025/01/eslint-v9.19.0-released/ | `linterOptions.reportUnusedInlineConfigs` |
| 5 | ESLint PR #17611 | https://github.com/eslint/eslint/pull/17611 | extensión del reporte a `eslint-enable` sin efecto |
| 6 | eslint/config-inspector | https://github.com/eslint/config-inspector | censo de reglas activas / deprecadas / cobertura del catálogo |
| 7 | ESLint blog — Introducing Config Inspector | https://eslint.org/blog/2024/04/eslint-config-inspector/ | motivación del censo de configuración |
| 8 | eslint-plugin-eslint-comments — no-unused-disable | https://mysticatea.github.io/eslint-plugin-eslint-comments/rules/no-unused-disable.html | antecedente del flag nativo |
| 9 | Semgrep — CLI reference | https://docs.semgrep.dev/cli-reference | `--time` (par regla,target), `--baseline-commit`, `--test`, `--test-ignore-todo` |
| 10 | Semgrep — Test rules | https://semgrep.dev/docs/writing-rules/testing-rules | `ruleid:` / `ok:` / `todoruleid:` / `todook:` |
| 11 | Semgrep — Managing findings | https://semgrep.dev/docs/managing-findings/ | `nosemgrep`, gestión de hallazgos |
| 12 | GitHub Docs — SARIF support for code scanning | https://docs.github.com/en/code-security/code-scanning/integrating-with-code-scanning/sarif-support-for-code-scanning | `tool.driver.rules[]`, `ruleId`/`ruleIndex`, estabilidad del catálogo |
| 13 | GitHub Docs — CodeQL query suites | https://docs.github.com/en/code-security/code-scanning/managing-your-code-scanning-configuration/codeql-query-suites | qué corre una suite |
| 14 | GitHub Docs — Analyzing your code with CodeQL queries | https://docs.github.com/en/code-security/codeql-cli/getting-started-with-the-codeql-cli/analyzing-your-code-with-codeql-queries | diagnostic queries (`@kind diagnostic`), métricas de resumen |
| 15 | Ruff — The Ruff Linter | https://docs.astral.sh/ruff/linter/ | semántica de `RUF100` |
| 16 | Ruff — unused-noqa (RUF100) | https://docs.astral.sh/ruff/rules/unused-noqa/ | regla y autofix |
| 17 | Ruff — Settings (`lint.external`) | https://docs.astral.sh/ruff/settings/ | tercera categoría: "código que no es mío, lo preservo" |
| 18 | Ruff issue #8492 | https://github.com/astral-sh/ruff/issues/8492 | "checked and no problem" vs "not checked" |
| 19 | Pylint — useless-suppression (I0021) | https://pylint.readthedocs.io/en/stable/user_guide/messages/information/useless-suppression.html | opt-in, no fatal salvo `--fail-on=I0021` |
| 20 | mypy — Error codes for optional checks | https://mypy.readthedocs.io/en/stable/error_code_list2.html | `unused-ignore`; excepción por código inalcanzable |
| 21 | TypeScript 3.9 release notes | https://www.typescriptlang.org/docs/handbook/release-notes/typescript-3-9.html | `@ts-expect-error`: la supresión se autoverifica |
| 22 | typescript-eslint — prefer-ts-expect-error | https://github.com/Josh-Cena/typescript-eslint/blob/85b851c97bb788a9333e901b0593c2e77044fa70/packages/eslint-plugin/docs/rules/prefer-ts-expect-error.md | argumento contra el ignore olvidado |
| 23 | PHPStan — Ignoring errors | https://phpstan.org/user-guide/ignoring-errors | `reportUnmatchedIgnoredErrors` (default true), `reportUnmatched` por entrada |
| 24 | PHPStan issue #4502 | https://github.com/phpstan/phpstan/issues/4502 | pedido de reconciliación automática, aún abierto |
| 25 | Android custom lint rules — Baselines | https://googlesamples.github.io/android-custom-lint-rules/usage/baselines.md.html | tracking de issues que ya no se reportan |
| 26 | Android custom lint rules — User guide | https://googlesamples.github.io/android-custom-lint-rules/user-guide.html | `LintBaseline` / `LintBaselineFixed` |
| 27 | Betterer — Results file | https://phenomnomnominal.github.io/betterer/docs/results-file/ | el snapshot como archivo de resultados |
| 28 | Betterer — Updating results | https://phenomnomnominal.github.io/betterer/docs/updating-results/ | *"only update the results file when your test results improve"* |
| 29 | golangci-lint discussion #2395 | https://github.com/golangci/golangci-lint/discussions/2395 | `nolintlint` / `allow-unused`, y su agujero con linters deshabilitados |
| 30 | SonarQube — Quality standards and new code | https://docs.sonarsource.com/sonarqube-server/user-guide/about-new-code | new code period en lugar de baseline de conteo |
| 31 | SonarQube — Issues | https://docs.sonarsource.com/sonarqube-server/10.5/user-guide/issues | `NOSONAR` y quality profiles |
| 32 | CACM — Lessons from Building Static Analysis Tools at Google | https://cacm.acm.org/research/lessons-from-building-static-analysis-tools-at-google/ | tope de 10% de FP efectivos; el desarrollador decide |
| 33 | Tricorder: Building a Program Analysis Ecosystem (ICSE 2015) | https://research.google.com/pubs/archive/43322.pdf | botón "Not useful", analizadores que se retiran |

---

## Evidencia ejecutable

Los cuatro hechos locales que sostienen la sección de aplicabilidad y las correcciones,
con el comando que los produjo:

```bash
# Corrección 1 — 131 archivos, 129 reglas
ls rules/*.md | wc -l                                  # 131
ls rules/*.md | grep -cE 'ROADMAP|RULES-COMPACT'       # 2

# Corrección 3 — el chequeo bilateral ya existe para conteos
grep -n 'baseline is above reality' scripts/scope_closure_gate.py

# Gap real — los baselines de identidades solo miran una dirección
grep -n 'not in baseline' scripts/volatile_number_audit.py
grep -n 'NOT in baseline' scripts/lint-shell.sh
grep -n 'new_findings' scripts/cos_quality_duplicates.py

# Premisa 4 — el freeze de adopción sigue activo
grep -n '^frozen:' manifests/external-tool-adoption-freeze.yaml
```

Los tres primeros bloques deberían quedar como aserciones en un test de auditoría el día
que se implemente el reporte de huérfanos: el gate nuevo tiene que hacer fallar el
`grep` que hoy pasa.

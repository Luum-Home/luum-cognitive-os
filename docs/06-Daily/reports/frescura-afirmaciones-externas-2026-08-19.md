# Frescura de las afirmaciones sobre sistemas externos

Fecha: 2026-08-19 · Repo: `luum-agent-os` · Instrumento: `scripts/external_claim_freshness_audit.py`

## Resumen ejecutivo

El censo derivado del árbol encuentra **313 afirmaciones perecederas estructuradas**
en `manifests/` (unidad = registro: el mapping más interno que ancla un sistema ajeno).
De esas: **8 declaran fecha de verificación** (todas del 2026-08-15, frescas), **0 vencidas**,
y **305 (97,4%) no declaran fecha: no se pueden juzgar**. Ese 97,4% es el resultado, no
un detalle: **"0 vencidas" sobre un censo 97% ciego no es un verde, es un no-observado**,
y el script lo dice en pantalla y sale con código 1 por eso.

De las 8 fechadas, **solo 1 declara el comando** que produjo la fecha. Las 18 file-level
con afirmaciones sin fechar están encabezadas por `dependencies.yaml` (119),
`ai-agent-harness-landscape.yaml` (37) y `external-tools-adoption.yaml` (35);
`harness-driver-capabilities.yaml`, el que motivó el encargo, aporta 3.

En prosa: **199 documentos vigentes** citan un sistema externo y **ninguno** declara marca
de verificación; 81 reportes/ADR quedan fuera del juicio por estar fechados por construcción.

Comando: `.venv/bin/python3 scripts/external_claim_freshness_audit.py --as-of 2026-08-19`

## Correcciones a las premisas del encargo

1. **La práctica ejemplar es mucho más delgada de lo que dice el encargo.** El brief afirma
   que `claude-code-hooks-schema.yaml` y `codex-hooks-schema.yaml` llevan `verified:` por
   fuente "con el comando de verificación escrito al lado (`how: curl -sSL ...`)". Falso para
   dos de los tres archivos: `grep -c 'how:'` devuelve **1** en `claude-code-hooks-schema.yaml`
   (que tiene 2 fuentes fechadas), **0** en `codex-hooks-schema.yaml` y **0** en
   `opencode-hooks-schema.yaml`. De 8 afirmaciones fechadas en todo el repo, **1 sola**
   trae el cómo. El hábito que hay que sistematizar existe en un único lugar, no en dos archivos.

2. **Son tres archivos con `verified:`, no dos.** `manifests/opencode-hooks-schema.yaml`
   también lleva `verified: 2026-08-15` en 4 registros y el encargo no lo menciona.
   Comando: `grep -rln '^\s*verified:' manifests/`

3. **`harness-driver-capabilities.yaml` no está del todo sin fechar.** El bloque `opencode`
   declara `version_baseline: "official-docs-2026-05-08"`: hay una fecha escrita, embutida en
   un string libre que ninguna máquina lee y ningún gate mira. La premisa "SIN fecha de
   verificación" es cierta como campo estructurado y falsa como "nadie escribió cuándo".
   Es un caso peor que la ausencia: parece dato y no lo es.

4. **"El driver emite 0 handlers y nadie lo sabía" es inexacto en la parte que importa.**
   En HEAD, la cabecera de `scripts/_lib/settings-driver-opencode.sh` documenta la
   divergencia de forma explícita: *"PreToolUse/PostToolUse hooks are NOT projected as
   scripts: the plugin enforces tool-call governance natively (classifyBash/classifyRead/...).
   Projecting 130+ per-tool-call bash spawns would freeze every tool call."* Y
   `packages/opencode-adapter/plugins/cos-primitive-guard.js` en HEAD **sí** implementa
   `tool.execute.before` (línea 364) con clasificadores inline (`classifyBash`, línea 247).
   Lo que era cero eran los **handlers proyectados como script**, por una política de latencia
   escrita; la capa de guardas llegaba a opencode por vía nativa. El defecto real es de otro
   tipo: el manifest declara `supported` sin decir *por qué vía*, y esa ambigüedad es lo que
   habilita las dos lecturas. Comandos:
   `git show HEAD:scripts/_lib/settings-driver-opencode.sh | sed -n 8,30p` y
   `git show HEAD:packages/opencode-adapter/plugins/cos-primitive-guard.js | grep -n 'tool.execute.before\|classifyBash'`

5. **El encargo subdimensiona el problema en dos órdenes de magnitud.** Nombra 3 manifests.
   El censo encuentra **18 archivos y 305 afirmaciones** sin fecha. `harness-driver-capabilities.yaml`
   es el 1% del problema (3 de 305); `dependencies.yaml` solo es el 39% (119 de 305).
   Arreglar los tres nombrados dejaría el censo en 96% ciego.

6. **El umbral no se pudo derivar de cadencia de releases porque ese dato no existe en el repo.**
   El encargo lo anticipa ("si no tenés ese dato... hacelo configurable"), y así quedó:
   `systems: {}` **vacío a propósito**, default 30 días con motivo escrito, y una guarda que
   **rechaza con exit 2** cualquier entrada de `systems` que fije un umbral sin `cadence_evidence`.
   Un umbral por sistema sin la evidencia de cadencia que lo justifica es un número inventado
   con formato de dato, y el instrumento se niega a aceptarlo.

7. **El scope no podía ser `both`.** El encargo plantea "¿le sirve a un proyecto consumidor
   saber si SU copia del SO envejeció?". La respuesta medida es no: `manifests/` **no aparece**
   en `manifests/primitive-install-boundary.yaml` (comando: `grep -c manifests manifests/primitive-install-boundary.yaml` → 0),
   así que una instalación consumidora no tiene manifests que envejezcan y el audit mediría
   población vacía. Quedó `SCOPE: os-only` con el alta correspondiente.

8. **El único primitivo que hoy deja en rojo la prueba de portabilidad no es el mío.**
   `tests/red_team/portability/test_os_only_scope_family.py::test_os_only_scope_none_budget_is_zero_after_family_proof`
   sigue fallando con `by_proof_level.none = 1`, y ese 1 es `scripts/hook_test_reality_census.py`,
   de la sesión concurrente (sin trackear, sin registrar). Mi script ya no cuenta ahí.

## Censo de afirmaciones perecederas

La distinción que ordena todo el trabajo: una afirmación sobre **nuestro árbol** se puede
*derivar* cuando uno quiere (si dudo de "hay 47 hooks registrados", cuento los hooks); una
afirmación sobre un **sistema ajeno** solo se puede *fechar*, porque el sistema ajeno cambia
sin avisarnos. Solo las segundas son perecederas.

### Estructuradas (`manifests/**`) — unidad: registro

| categoría | n | % sobre medibles |
|---|---:|---|
| fresca (≤30 días) | 8 | 100,0% |
| **vencida** | **0** | 0,0% — **no es un hallazgo: es una no-observación** |
| **sin fecha declarada (no juzgable)** | **305** | fuera de alcance (97,4% de 313) |
| archivo ilegible | 0 | fuera de alcance |

Archivos con afirmaciones externas sin fecha de verificación:

| n | archivo |
|---:|---|
| 119 | `manifests/dependencies.yaml` |
| 37 | `manifests/ai-agent-harness-landscape.yaml` |
| 35 | `manifests/external-tools-adoption.yaml` |
| 19 | `manifests/harness-projection.yaml` |
| 18 | `manifests/feature-tool-due-diligence.yaml` |
| 17 | `manifests/dependency-adoption-evidence.yaml` |
| 16 | `manifests/remote-control-plane-alternatives.yaml` |
| 13 | `manifests/external-tool-licenses.yaml` |
| 8 | `manifests/routing-benchmark-models.yaml` |
| 5 | `manifests/self-programming-agent-patterns.yaml` |
| 5 | `manifests/skill-router-retrieval.yaml` |
| 4 | `manifests/agent-orchestration-adapters.yaml` |
| 3 | `manifests/harness-driver-capabilities.yaml` |
| 2 | `manifests/provider-profiles.yaml` |
| 1 | `manifests/claude-code-hooks-schema.yaml` |
| 1 | `manifests/external-tool-adoption-freeze.yaml` |
| 1 | `manifests/opencode-hooks-schema.yaml` |
| 1 | `manifests/tool-discovery-preuse.yaml` |

Nótese que `dependency-adoption-evidence.yaml` y `routing-benchmark-models.yaml` no estaban
en el radar de nadie: aparecen porque el censo se deriva del árbol, no de una lista.

### Método de verificación — unidad: registro

De las 8 fechadas: **1 con comando reproducible**, **7 sin**. Las 305 sin fecha no aplican.
Una fecha sin el comando que la produjo no es reproducible: quien la revise en seis meses
no sabe qué correr.

### Prosa (`docs/**`, `rules/**`) — unidad: documento, NO comparable con lo anterior

| categoría | n |
|---|---:|
| declara marca de verificación | 0 |
| no declara | 199 |
| fechado por construcción (reportes diarios, ADR) — fuera del juicio | 81 |

El instrumento **no puede localizar la afirmación adentro de la prosa**: solo ve si el
documento declara una marca. Por eso este censo va aparte, con su propia unidad, y no se
mezcla con el estructurado.

## El umbral y de dónde sale

Vive en `manifests/external-claim-freshness.yaml`, no en el código.

- **Default: 30 días.** No está elegido para que hoy dé verde — hoy da rojo con cualquier
  valor, porque la ceguera domina y el script se niega a reportar verde bajo ceguera alta.
- **De dónde sale, con lo único medible que hay:** el único intervalo observado en que una
  afirmación sobre un arnés externo quedó divergente sin que nadie la revisara es
  `harness-driver-capabilities.yaml`, último commit 2026-07-10, revisado hoy → **40 días**
  (`git log -1 --format=%ad --date=short -- manifests/harness-driver-capabilities.yaml`).
  La práctica correcta, cuando se ejerce, produce afirmaciones de **4 días**
  (`verified: 2026-08-15`). 30 es la ventana redonda más grande estrictamente por debajo
  del único intervalo en que una afirmación externa se sabe que envejeció mal acá.
- **Es un placeholder declarado, no una medición de cadencia**, y el archivo lo dice con esas
  palabras en `default_rationale`. La cadencia real de releases de cada sistema afirmado no
  está en este repo; cuando los agentes de investigación la traigan, cada sistema entra en
  `systems:` con su cadencia y su comando, y el default deja de aplicarle.
- **`systems: {}` está vacío a propósito.** El loader **falla con exit 2** si alguien agrega
  una entrada sin `cadence_evidence`. Es la contraparte de "no inventar el umbral": el
  instrumento no acepta un número que no venga con cómo se supo.
- **`blind_ratio_threshold: 0.20`** espeja `cos_lib.measurement.BLIND_WARNING_THRESHOLD`
  a propósito: nadie puede aflojarlo sin que se vea en el manifest.

## El script

`scripts/external_claim_freshness_audit.py` — `SCOPE: os-only`, read-only, determinista.

- **Deriva el censo del árbol.** Recorre `manifests/**/*.{yaml,yml,json}` y marca como
  afirmación perecedera todo *mapping con ancla externa directa*: un valor escalar con URL
  a host no local, o una clave que afirma algo de un tercero (`license`, `spdx`,
  `package_names`, `version_baseline`, `upstream_version`, `official_sources`). Toma el
  mapping **más interno** para que una afirmación no se cuente dos veces en el padre y en
  el hijo. No hay lista fija de archivos: una lista fija nace desactualizada, que es
  exactamente el defecto que el instrumento persigue.
- **Reporta por afirmación**: fecha declarada, antigüedad en días, umbral aplicado y de dónde
  salió (`<default>` o el sistema), y si trae comando reproducible.
- **Usa `cos_lib.measurement.Census`** para los tres censos. Ningún conteo sale sin
  denominador ni sin bucket de ceguera.
- **`--as-of YYYY-MM-DD`** para reproducir una corrida: la fecha es un input, no un implícito.
  Dos corridas seguidas con `--as-of` fijo dan bytes idénticos (`cmp -s` → OK).
- **Códigos de salida**: 0 sin hallazgos / **1 hallazgos** / 2 error del instrumento
  (config faltante, umbral sin evidencia de cadencia). Verificado: `--project-dir /tmp` → 2.
- **Hoy sale 1**, y no por vencidas: sale 1 porque la ceguera (97,4%) supera el umbral.
  Esa es la decisión de diseño central. Si el criterio fuera solo "vencidas > 0", este
  instrumento saldría **0 sobre un repo que no puede juzgar 305 de sus 313 afirmaciones**,
  y sería un verde barato con forma de gate.

## El contrato y sus dos corridas

`tests/contracts/test_external_claims_declare_verification.py`, 5 aserciones.

El baseline es **por archivo y con conteo exacto**, no una lista de nombres: un baseline de
nombres dejaría pasar una afirmación nueva agregada *dentro* de un archivo ya listado, que
es la forma más probable de que esto crezca (nadie crea un manifest nuevo para sumar una
dependencia). Con conteo, cualquier movimiento —una más o una menos— rompe.

Incómodo y a propósito: `claude-code-hooks-schema.yaml`, el ejemplar de la práctica correcta,
aparece en **los dos** baselines (1 afirmación sin fecha, 1 fechada sin comando). El baseline
lo dice en vez de redondearlo.

### Dirección 1 — afirmación perecedera nueva sin fecha: **FALLA**

Se agregó `manifests/_freshness_contract_selftest.yaml` con una fuente externa sin `verified:`:

```
F....                                                                    [100%]
E   AssertionError: estas afirmaciones sobre sistemas AJENOS no declaran cuando se
    verificaron (archivo: sin_fecha_ahora vs baseline):
    {'manifests/_freshness_contract_selftest.yaml': (1, 0)}. Una afirmacion sobre nuestro
    arbol se deriva cuando uno quiere; una sobre un sistema ajeno solo se puede fechar.
    Agrega `verified: YYYY-MM-DD` y `how: <comando reproducible>` al lado de la fuente,
    como en manifests/claude-code-hooks-schema.yaml. NO pongas la fecha de hoy sin haber
    mirado la fuente: eso convierte el instrumento en su opuesto.
FAILED tests/contracts/test_external_claims_declare_verification.py::test_ninguna_afirmacion_externa_nueva_omite_su_fecha
1 failed, 4 passed in 3.35s
```

### Dirección 2 — la MISMA afirmación, fechada y con comando: **PASA**

```
.....                                                                    [100%]
5 passed in 2.78s
```

El archivo de autoprueba se borró al terminar (`selftest file removed: YES`); no queda en el
árbol. Estado final del contrato sobre el repo real: **5 passed**.

### Alta os-only y prueba de portabilidad

`SCOPE: os-only`, por lo dicho en la corrección 7. Alta hecha en los dos lugares que exige la
familia: `OS_ONLY_PRIMITIVE_PROOF_BASELINE` en
`tests/red_team/portability/test_os_only_scope_family.py`, y entrada en
`manifests/primitive-behavior-evidence.yaml` apuntando a la prueba de familia y al contrato.

El resolvedor real del gate, extraído de `hooks/scope-marker-portability-gate.sh` y corrido
sobre las dos rutas, con control negativo:

```
=== mio (vacio = tiene prueba pareada):
[exit=0]
=== control negativo:
scripts/hook_test_reality_census.py
[exit=0]
```

`primitive_scope_health.py` clasifica el script como
`scope=os-only, consumer_surface=maintainer-only, plane=control-plane`, y su `proof_level`
pasó de `none` a probado. `by_proof_level.none` bajó a **1**, que es el script ajeno
de la corrección 8.

## La ceguera declarada

Lo que este instrumento **no** puede ver, dicho para que nadie se confíe:

- **No verifica que la afirmación sea verdadera.** Mide si *declara* cuándo y cómo se
  verificó. Un `verified: 2026-08-19` recién puesto sin haber mirado la fuente pasa el audit
  y miente igual. El audit hace visible la omisión, no la falsedad. Por eso el mensaje de
  error del contrato dice explícitamente que poner la fecha de hoy sin mirar la fuente
  convierte el instrumento en su opuesto.
- **No puede juzgar 305 de 313 afirmaciones estructuradas** (97,4%): no declaran fecha. Eso
  no es "están al día" ni "están vencidas". Es **no se puede juzgar**, y va a `blind`.
- **No puede localizar afirmaciones dentro de la prosa.** De los 199 documentos vigentes que
  citan un sistema externo, solo sabe que ninguno declara una marca; no sabe cuántas
  afirmaciones perecederas contienen ni cuáles envejecieron.
- **No juzga los 81 reportes y ADR** que citan sistemas externos: están fechados por
  construcción y son registros históricos, no afirmaciones vigentes. Es una exclusión por
  regla escrita en el manifest, no un olvido.
- **La detección por ancla puede tener falsos positivos**: una URL de nuestra propia
  organización en GitHub cuenta como sistema ajeno. La decisión fue deliberada —un repo
  propio también cambia sin que este archivo se entere— pero infla el denominador.
- **`Census` no impide** que alguien lea `census.buckets["vencida"]` y publique ese entero
  suelto. Hace que el camino honesto sea el más corto, no que el deshonesto sea imposible.

## Lo que NO hice y por qué

- **No toqué ninguna fecha.** Ni una. Poner `verified: 2026-08-19` en manifests sin verificarlos
  de verdad es falsificar evidencia y haría que el instrumento sirva para lo contrario de lo
  que existe: un censo 100% "fresco" y 100% falso.
- **No inventé entradas en `systems:`.** Quedó vacío, con el default aplicando a todo y una
  guarda que rechaza cualquier entrada futura sin `cadence_evidence`.
- **No investigué el ecosistema.** Es el trabajo de los dos agentes en paralelo; este es el
  instrumento que hace que la pregunta se conteste sola la próxima vez.
- **No arreglé las 305 afirmaciones sin fecha.** Fecharlas exige salir a verificar cada fuente:
  es trabajo de investigación, no de instrumentación, y hacerlo sin verificar sería el punto
  anterior.
- **No toqué archivos de la sesión concurrente** (`settings-driver-opencode.sh`,
  `cos-primitive-guard.js`, `hook_exercise_audit.py`, `cos_init.py` y los tests asociados
  aparecen modificados en el working tree y no son míos).
- **No registré `scripts/hook_test_reality_census.py`** en la familia os-only, aunque es el
  único `proof_level: none` que queda. No es mío, y darle de alta sin conocer su prueba
  pareada sería exactamente el gesto de "apagar el rojo" que la norma prohíbe. Queda
  señalado en la corrección 8 para quien corresponda.
- **No commiteé ni pusheé nada**, según el encargo.

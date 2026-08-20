# Frases prohibidas: buscarlas donde pueden estar, no donde se declararon

Fecha: 2026-08-20 · Ámbito: `scripts/documentation_truth_audit.py`,
`manifests/documentation-truth-claims.yaml`, `tests/unit/test_documentation_truth_audit.py`

## Resumen ejecutivo

Una frase prohibida se buscaba sólo dentro de los `required_docs` del propio claim.
Medido sobre HEAD: el barrido completo eran **18 documentos**, y para el claim
`claude_code_hook_registration` —que no declara ninguno— eran **0 archivos, con
resultado `pass`**. Ahora cada frase se busca contra **3233 archivos** (`.md`,
`.sh`, `.py`, `.yaml`, `.yml`), y cada fila del reporte dice contra cuántos, porque
N=0 fue el defecto. Se agregan tres rechazos nuevos: frase prohibida sin superficie
(0 archivos), alcance angostado sin motivo escrito, y `required_phrases` sin
`required_docs` donde buscarlas. El costo del barrido es 2,4 s (27,3 MB) contra
27,8 s de la primera versión, gracias a un prefiltro literal por archivo.

El árbol **no** queda en verde: el barrido encontró una tercera copia viva de la
mentira de ayer, en `cos_lib/wiring_validator.py:61`, archivo que este encargo me
prohíbe tocar. Es un hallazgo, no un fallo del gate.

## Correcciones a las premisas del encargo

1. **«El audit dio verde» — no.** Al empezar esta sesión el audit estaba en
   **rojo con 2 bloqueos** (`.venv/bin/python3 scripts/documentation_truth_audit.py --no-write`
   → `block_count: 2`), y el contrato `tests/contracts/test_documentation_truth_audit.py::test_current_documentation_truth_audit_passes`
   ya fallaba antes de que yo tocara nada. Los dos bloqueos eran ajenos al defecto
   del encargo: (a) el bloque generado de `documentation-truth-control.md` quedó
   viejo cuando otra sesión agregó el claim `disk_ceiling_single_source`, y (b) el
   propio claim `claude_code_hook_registration` bloqueaba por `required_phrase`
   faltante. Lo que sí dio verde fue **la parte de frases prohibidas** del claim, y
   por el motivo del encargo: se chequeó contra cero archivos.

2. **«Se busca en cero archivos y pasa» — cierto para `forbidden_phrases`, falso
   para `required_phrases`.** Las dos mitades del mismo mecanismo fallan al revés:
   `forbidden_phrases` sobre cero documentos da `pass` (falla-abierto), y
   `required_phrases` sobre cero documentos da `block` con el mensaje
   «Required phrase missing», que culpa a la prosa cuando el problema es que no hay
   dónde mirar. La segunda mitad estaba fuera del encargo y se arregla igual:
   `required_phrase_surface` ahora nombra la causa real.

3. **La frase declarada no coincidía con ninguna de las copias vivas.** El claim
   declara la frase con backticks simples; la copia que sacó `5ccae36bd` iba **sin**
   backticks, y la que sigue viva en `cos_lib/wiring_validator.py:61` va con
   backticks **dobles** (rst). Con comparación literal, ampliar el alcance a todo el
   repo **no habría encontrado ninguna de las dos**. El defecto tenía una segunda
   capa que el encargo no menciona, y sin arreglarla la corrida 1 daría verde.

4. **Tres defectos, no dos.** Además del alcance y del claim vacío, el matcheo por
   substring genera falsos positivos por cruce de palabras: `master-plan-checklist.md`
   dice «plan-only Claude/Codex settings projection» y contenía la frase prohibida
   «only Claude/Codex» sin decirla. Con el alcance viejo nunca se veía; con el nuevo
   habría sido el primer falso positivo del gate.

5. **`git worktree` está bloqueado** por `destructive-git-blocker` (ADR-055b), así
   que el «antes» no se midió en un worktree limpio sino corriendo el script y el
   manifiesto de HEAD (`git show HEAD:…`) en proceso contra este árbol. Mismo
   número, sin reescribir el estado compartido.

6. **Bug lateral encontrado y arreglado:** `--manifest` apuntando fuera de
   `--project-dir` reventaba con `ValueError` en `rel()` al armar el reporte. Se
   necesita justamente para reproducir un claim en aislamiento (corrida 3), así que
   ahora la etiqueta cae al path absoluto en vez de tirar.

## El alcance: qué se barre y qué no, con el motivo

Declarado en `manifests/documentation-truth-claims.yaml` bajo `forbidden_phrase_scan`,
y visible en la salida del audit (`summary.forbidden_phrase_scan`) y en la tabla
«Forbidden-phrase scan surface» del `.md` generado.

**Se barre:** `.md`, `.sh`, `.py`, `.yaml`, `.yml` en todo el repo. Las tres copias
de ayer vivían en un `.md`, un `.sh` y un docstring de `.py`: excluir «código» habría
dejado afuera dos de las tres. `hooks/`, `scripts/`, `cos_lib/`, `packages/`,
`rules/`, `skills/`, `templates/`, `manifests/` y `docs/` entran completos.

Los symlinks se resuelven y se deduplican por path real, así que un hook alcanzable
como `hooks/x.sh` y como `packages/*/hooks/x.sh` es **un** archivo, no dos (426
symlinks fuera de los directorios podados).

**No se barre** (conteos de la corrida 2):

| Archivos | Qué | Por qué |
|---|---|---|
| — | `.git`, `.venv`, `node_modules`, `reference`, `.cognitive-os`, cachés, `dist`/`build`/`target` | Internos de VCS, virtualenvs, árboles de terceros, estado de runtime y telemetría rotada, salida de build. Nada de eso es prosa del repo y es la mayoría de los bytes. |
| 2373 | `tests/**` | El instrumento. Un test que verifica la ausencia de una frase **tiene que contenerla** (`tests/contracts/test_primitive_authority_docs.py` lista tres). La alternativa es deformar el test para no confundir al auditor. |
| 1819 | `.claude/plugins/**` | Caché de plugins de terceros, no se escribe en este repo. |
| 501 | `docs/06-Daily/reports/**` | Informes anclados a fecha y ledgers `-latest` generados: registro histórico y salida de máquina. |
| 240 | Nombre con `YYYY-MM-DD` en cualquier parte del repo | Registro fechado: cita el estado de ese día a propósito. |
| 11 | `**/archive/**`, `**/archived/**` | Registro de lo que fue. |
| 7 | ADR con `status: superseded/deprecated/rejected/withdrawn` | Una decisión superada conserva su prosa original por diseño. |
| 10 | `packages/*/tests/**` | Igual que `tests/**`, por la otra ruta del layout. |
| 1 | `rules/session-close-doc-truth.md` | La regla que **define** esta disciplina la enseña citando una frase prohibida de ejemplo. Autorreferencia. |
| 2 | El manifiesto de claims y este auditor | Autorreferencia, excluidos en código y no por configuración: son la fuente de las frases. |

**Contrapeso al recorte:** los `required_docs` de cualquier claim se barren
**siempre**, aunque una exclusión genérica los tapara. Por eso
`volatile_number_prose` sigue vigilando `docs/06-Daily/reports/numeros-volatiles-2026-08-15.md`,
que es un informe fechado dentro de un directorio excluido: nombrarlo en el claim es
la manera de volver a meterlo. Hay test (`test_required_docs_are_scanned_even_when_globally_excluded`).

**Costo:** 3233 archivos, 27,3 MB, **2,4 s**. La primera versión (una alternación
regex de 27 frases sobre todo el árbol) tardaba 27,8 s. El prefiltro es literal: cada
frase aporta su átomo más largo, se baja el archivo a minúsculas una vez y sólo se
corre el regex de las frases cuyo ancla aparece.

## Mentira viva vs cita histórica: cómo se distinguen

Cuatro mecanismos, ninguno de ellos un allowlist por archivo:

1. **Clase de archivo, no archivo.** Fecha en el nombre, `status: superseded` en el
   frontmatter, `archive/`, `CHANGELOG`, `docs/06-Daily/reports/**`. Un registro
   fechado cita el estado de su día; marcarlo sería un falso positivo masivo y la
   forma más rápida de que alguien apague el gate. Los mensajes de commit no son
   archivos y quedan fuera por construcción.
2. **Frase, no substring.** Los límites rechazan vecinos de palabra incluyendo `-` y
   `/`, así que «plan-only Claude/Codex» **no** matchea «only Claude/Codex». Sin
   esto, el primer falso positivo del gate ampliado habría sido
   `docs/08-References/business/master-plan-checklist.md:337`.
3. **Tolerancia a la tipografía.** Los átomos se separan por espacios y por
   decoración markdown/rst (backticks, comillas, `*`, `_`), así que la misma
   afirmación se caza pelada, entre backticks simples y entre dobles. Ésta es la que
   hace que la corrida 1 dé rojo: la frase declarada y las dos copias vivas están
   escritas de tres maneras distintas.
4. **Alcance por frase, con motivo escrito.** Una frase genérica se angosta a las
   superficies del claim y el motivo queda en el manifiesto; angostar **sin** motivo
   es bloqueo (`forbidden_phrase_scope`). Es la salida honesta para una coincidencia,
   y deja rastro en vez de silencio.

**Lo que estos mecanismos no ven** (declarado en `known_blind_spots`): la inversión
semántica. `tests/behavior/test_consumer_project_projection.py:272` dice «not only
Claude/Codex», que contiene la frase prohibida y afirma lo contrario. Hoy la única
instancia vive en `tests/`, ya excluido. Una futura en prosa viva se arregla haciendo
la frase más específica, **nunca** agregando el archivo a `exclude_globs`.

## El claim vacío

`forbidden_phrase_surface` es una fila por frase y por claim, y lleva
`checked_files:N` en la evidencia. Si N es 0, es **bloqueo**, y el mensaje dice qué
falta: «Forbidden phrase declared with no surface to check it against (0 files)»,
con `next_action` = «widen or fix scan_scope so the phrase is checked against at
least one existing file».

Con el alcance por defecto repo-wide, N sólo puede ser 0 si el claim declaró un
`scope` que no resuelve a ningún archivo existente —el caso realista: la superficie
se declaró bien y después el archivo se borró o se renombró—. La otra puerta que
antes estaba abierta también se cerró: `required_phrase_surface` bloquea cuando un
claim declara `required_phrases` sin ningún `required_doc` existente, en vez de
reportar «frase faltante» y hacer buscar la prosa que sí está.

Los dos rechazos son la parte del trabajo que sola habría atrapado el caso de ayer:
el claim `claude_code_hook_registration` se registró sin `required_docs` y hoy eso no
se puede registrar en silencio. Su arreglo: declara las tres superficies que sí deben
llevar la verdad actual (`scripts/_lib/settings-driver-claude-code.sh`,
`hooks/inject-phase-context.sh`, `templates/project-gotchas.md`).

## Las cuatro corridas

### 1. Con la copia de ayer reintroducida en `hooks/inject-phase-context.sh` → BLOCK

Reintroducida textualmente la línea 204 que sacó `5ccae36bd`, corrido el audit, y el
archivo restaurado desde una copia previa.

```
sha256 before: 24304c59e4a54def95f9b5d4afcd9b6b192c9d082cbf91cabb8f752032d762e8
reintroduced at line 204
--- RUN 1: with the 2026-08-19 copy reintroduced ---
exit=2
status: block block_count: 1 files checked: 3233
  forbidden_phrase | Forbidden stale phrase present in 2 place(s), checked against 3233 files: the canonical hook registry is `cognitive-os.yaml > harness.hooks`
   evidence: ['cos_lib/wiring_validator.py:61', 'hooks/inject-phase-context.sh:204', 'checked_files:3233']
sha256 after restore: 24304c59e4a54def95f9b5d4afcd9b6b192c9d082cbf91cabb8f752032d762e8
RESTORED BYTE-IDENTICAL
```

`git status --porcelain hooks/inject-phase-context.sh` quedó vacío y
`/bin/bash -n hooks/inject-phase-context.sh` pasa.

### 2. Con el árbol actual → BLOCK, por una copia viva que no me toca arreglar

```
--- RUN 2: current tree ---
exit=2
status: block block_count: 1 rows: 120
files checked: 3233
 BLOCK claude_code_hook_registration | forbidden_phrase | Forbidden stale phrase present in 1 place(s), checked against 3233 files: the canonical hook registry is `cogn
    ['cos_lib/wiring_validator.py:61', 'checked_files:3233']
```

El encargo esperaba `pass`. Es la premisa que se cae: la mentira de ayer tiene una
tercera copia viva y el gate la ve. Ver «Copias vivas que aparecieron».

### 3. Claim con `forbidden_phrases` y sin superficie → BLOCK por claim vacío

```
--- RUN 3: claim with forbidden_phrases and no surface ---
exit=2
status: block block_count: 1
  BLOCK claim_with_nowhere_to_look | forbidden_phrase_surface
   message: Forbidden phrase declared with no surface to check it against (0 files): the canonical hook registry is `cognitive-os.yaml > harness.hooks`
   evidence: ['scope:docs/04-Concepts/architecture/a-doc-that-was-deleted.md', 'checked_files:0']
   next_action: widen or fix scan_scope so the phrase is checked against at least one existing file
```

### 4. Control anti-paranoia: informe fechado que **cita** la frase vieja → sigue verde

Este mismo informe cita la frase prohibida varias veces y está anclado a fecha
(`…-2026-08-20.md`, dentro de `docs/06-Daily/reports/`). El control es que su
existencia no mueva el veredicto:

```
$ grep -c 'canonical hook registry' docs/06-Daily/reports/frases-prohibidas-donde-no-mire-2026-08-20.md
4

$ .venv/bin/python3 scripts/documentation_truth_audit.py --no-write --json --fail-on-block
exit=2
antes de escribir este informe (corrida 2):
  status=block  block_count=1  files_checked=3233
  excluidos por 'docs/06-Daily/reports/**' = 501
  filas bloqueantes = ['claude_code_hook_registration:forbidden_phrase:cos_lib/wiring_validator.py:61']
despues de escribirlo (corrida 4):
  status=block  block_count=1  files_checked=3233
  excluidos por 'docs/06-Daily/reports/**' = 502
  filas bloqueantes = ['claude_code_hook_registration:forbidden_phrase:cos_lib/wiring_validator.py:61']
```

El informe suma un archivo a la clase excluida y **cero** filas bloqueantes: el
veredicto es identico antes y despues. Si el gate no distinguiera la cita del
registro historico, escribir este informe lo habria puesto rojo por si mismo.
Ademas hay test unitario del mismo control
(`test_date_anchored_report_citing_the_phrase_stays_green`), que en un arbol
sintetico mete la frase en un `…-2026-08-19.md` y exige `pass`.

## Copias vivas que aparecieron

Ampliar el alcance destapó **una** copia viva de la mentira de ayer, más un grupo de
coincidencias que no son deuda:

- **`cos_lib/wiring_validator.py:61` — copia viva, REAL.** El docstring de
  `_registry_hooks()` dice «ADR-064: the canonical hook registry is
  ``cognitive-os.yaml > harness.hooks``» y sigue con la consecuencia falsa: «a hook
  registered solely in the YAML must still count as wired». El archivo **se
  contradice a sí mismo**: su docstring de módulo (líneas 8–16) ya lleva el
  `CAVEAT, MEASURED 2026-08-19` que dice exactamente lo contrario. `5ccae36bd`
  anticipó esta copia y la dejó explícitamente en manos de otro agente; este encargo
  me prohíbe tocar el archivo, así que queda **sin arreglar y bloqueando**. El fix es
  una línea: alinear el docstring del método con el del módulo.
- **`tests/contracts/test_primitive_authority_docs.py:49–51` y
  `tests/behavior/test_consumer_project_projection.py:272` — coincidencia.** El
  primero es la lista de frases contra la que asserta; el segundo dice «not only
  Claude/Codex», que afirma lo contrario. Clasificados como instrumento, `tests/**`
  excluido con motivo escrito.
- **«not implemented yet» en 14 lugares — coincidencia.** ADR-225, ADR-234, ADR-236,
  ADR-264, `docs/09-Quality/security/release-signing.md`,
  `docs/04-Concepts/architecture/opensage-self-programming-patterns.md`,
  `scripts/audit_adrs.py` y otros, todos describiendo alguna otra cosa como pendiente.
  Inglés genérico, no la firma de un claim: un cambio en el audit de authority no
  debería obligar a tocar ninguno. La frase se angostó a las dos superficies del
  claim `primitive_authority_write_effects`, con el motivo escrito en el manifiesto.
- **`docs/08-References/business/master-plan-checklist.md:337` — falso positivo del
  matcheo, ya eliminado.** «plan-only Claude/Codex» contenía «only Claude/Codex»
  cruzando el guion. Lo resuelve la regla de límites, no una exclusión.
- **`rules/session-close-doc-truth.md:34` — autorreferencia.** La regla que define
  esta disciplina cita «no atomic close primitive exists» como ejemplo didáctico.

## Lo que NO hice y por qué

- **No arreglé `cos_lib/wiring_validator.py`.** Prohibido explícitamente por el
  encargo; es de otro agente en la misma sesión. Queda como hallazgo con archivo,
  línea y el fix de una línea.
- **No agregué `required_docs` a los claims para achicar el alcance.** El único claim
  que los recibió es `claude_code_hook_registration`, y para lo contrario: para que
  su `required_phrases` tenga dónde buscarse. Sus frases prohibidas se chequean
  contra los 3233 archivos igual que las de todos.
- **No excluí `hooks/`, `scripts/` ni `cos_lib/`.** Dos de las tres copias de ayer
  vivían ahí. Es donde más importa mirar.
- **No armé un allowlist de archivos.** Las exclusiones son clases (fecha en el
  nombre, status de ADR, `tests/**`, terceros) con motivo escrito. Las dos entradas
  puntuales que hay son autorreferencia del propio instrumento, y el manifiesto deja
  dicho que el crecimiento de `exclude_globs` es en sí mismo el olor a vigilar.
- **No moví ningún baseline ni bajé la severidad de nada** para que la corrida 2 diera
  verde. Habría sido el verde barato exacto que el encargo prohíbe.
- **No toqué `.json`.** Casi todo el `.json` del repo es reporte generado o settings
  proyectados; el riesgo de prosa mentirosa está en `.md`/`.sh`/`.py`. Si aparece un
  caso, se agrega el sufijo, que es una línea del manifiesto.
- **No registré el audit en ningún gate nuevo.** Ya corre por
  `tests/contracts/test_documentation_truth_audit.py` y por el adaptador ACC
  `documentation_truth`; ese contrato **falla hoy** por la copia de
  `wiring_validator.py`, y así debe quedar hasta que se arregle.

---
date: 2026-08-19
scope: os-only
kind: report
topic: gate contra tests que certifican defectos
---

# Gate contra tests que certifican bugs

## Resumen ejecutivo

De las cuatro señales propuestas elegí **una sola: el test afirma un valor de un
enum cerrado que no está en el enum**. Es la única decidible sin correr nada,
sin telemetría y sin corpus de payloads, y la única cuyo veredicto no es una
heurística sino una comparación contra un contrato transcripto en
`manifests/claude-code-hooks-schema.yaml`.

El gate es `scripts/audit_test_assertion_enums.py`, gateado por
`tests/audit/test_assertion_enum_conformance.py` (lane `audit`,
`gate_class: release_blocking`), con el registro de enums en
`manifests/test-assertion-enums.yaml`.

Atrapa **2 de los 4 casos de hoy** — las dos suites de `secret-detector` que
afirmaban `permissionDecision == "block"`. No atrapa las otras dos, y eso está
declarado abajo y en el propio manifiesto, en un bloque `not_registered` que el
gate testea.

Violaciones hoy: **0**. Al primer commit del día (`8a2d75c93`): **2**.
Sin baseline, sin allowlist, sin excepciones: el árbol está en cero exacto.

## Correcciones a las premisas del encargo

1. **"Dos `assert ... == ""` sobre el payload bloqueado"** — el caso 1 existió,
   pero al escribir el gate se ve que no es de la misma familia que los otros
   tres. `== ""` no es un valor fuera de un enum: es una afirmación sobre un
   efecto vacío. Ninguna señal estática que no sea "sospechar de todo string"
   lo separa de un test honesto que verifica silencio. Lo dejé afuera a
   conciencia, no por olvido.

2. **"habría atrapado dos de los cuatro casos"** — verificado, y la aritmética
   es más incómoda de lo que sugiere la frase. Los "cuatro casos" del encargo
   agrupan **cinco archivos de test**: el caso 3 son dos suites. El gate atrapa
   **2 archivos de 5**, que es el mismo 2/4 sólo si se cuenta por caso. Medido:
   `scripts/audit_test_assertion_enums.py --root <archive de 8a2d75c93>` → 2
   hallazgos, ambos del caso 3.

3. **"`test_cwd_enforcer_rewrite.py:72`"** — el archivo no está en `tests/unit/`
   como sugería la lista; está en `tests/integration/test_cwd_enforcer_rewrite.py`,
   y el `main_worktree` está en la línea 72 de la función `_make_yaml`, sí. Lo
   comprobé con `find` porque el `sed` sobre la ruta implícita no encontró nada.

4. **"El contrato está en `manifests/claude-code-hooks-schema.yaml`"** — cierto,
   pero el contrato transcribe **un solo enum de valores** en todo el archivo
   (`permission_decision_values`, línea 241). El campo `decision`, que gobierna
   PostToolUse / UserPromptSubmit / Stop, tiene declarado el **campo** y no sus
   **valores**. Es decir: la señal que el encargo llama "chequeable
   estáticamente contra el manifest" hoy alcanza exactamente a un campo. El
   gate está construido para más y hoy corre con uno; inventar el enum de
   `decision` acá habría sido la deuda que este registro existe para evitar.

5. **"`git log` te da los commits"** — sí, y también da una trampa: al
   reconstruir el árbol pre-fix hay que tomar `b2f9d877e^`, no el commit del
   día anterior. Los dos archivos de test cambiaron dos veces hoy.

6. **Restricción del encargo, verificada y no asumida.** Me pediste no tocar
   `hooks/session-cleanup.sh` ni `hooks/protected-config-write-guard.sh`.
   `git status --short` muestra 54 rutas sucias de otras sesiones, ninguna de
   ellas es un archivo que yo escribí, y ninguno de los cuatro archivos de este
   commit aparecía en esa lista antes de crearlos. El `git add` fue por rutas
   explícitas.

7. **Un número del encargo que no reproduje**: "199 tests verdes sobre 36 hooks
   sin registrar" y "17 sobre dos hooks que en producción nunca escribieron una
   fila". No los recontré — quedan fuera del alcance de este gate por decisión
   (ver *Lo que NO hice*), así que no los cito como propios.

## Las cuatro señales evaluadas, con su costo

| # | Señal | Qué atrapa de hoy | Costo de construirla | Veredicto |
|---|-------|-------------------|----------------------|-----------|
| 1 | **El payload no viene del contrato** (campos que el arnés nunca manda: `skill_name`, `tool_count`, `main_worktree`) | casos 1, 4 y el masivo | Alto y hoy **insatisfacible**: el corpus `tests/fixtures/payload-corpus/` son 52 registros, todos PostToolUse y sin `tool_input`, así que exigir "el campo existe en el corpus" deja sin poder pasar a todo test de PreToolUse. Requiere primero ampliar el corpus por captura, que no es trabajo estático | **Descartada**, con el motivo escrito |
| 2 | **Valor fuera de un enum cerrado** | caso 3 (2 archivos) | Bajo: AST + un puntero al manifest. Cero falsos positivos medidos sobre 2306 archivos | **Elegida** |
| 3 | **El test verifica exit code en vez de efecto** | caso 3 parcialmente | Bajo detectar, **imposible gatear**: `assert rc == 2` es la forma correcta de verificar un hook bloqueante — es exactamente lo que afirma el test corregido. La señal separa poblaciones por muestreo, no casos por regla | **Descartada**: gatearla convierte en sospechoso al arreglo |
| 4 | **El hook bajo test nunca corrió en producción** | el caso masivo (199 + 17) | Medio-alto y con la fuente rota: `hook-health.jsonl` no sirve (hooks con 0 filas ahí tienen 9.500–12.400 corridas en el wrapper) y `hook-timing.jsonl` exige rehidratar `.archive/*.gz`. Además es una señal **de cobertura, no de mentira**: un test sobre un hook dormido puede ser perfectamente honesto | **Descartada** para este gate |

La razón de fondo para elegir la 2: es la única donde el gate no opina. Compara
un literal contra una lista que otro archivo transcribe del contrato del arnés.
Si el hallazgo es falso, el que está mal es el manifiesto, y eso es una
discusión con evidencia — no una heurística que hay que calibrar.

## El gate y sus tres corridas

### Diseño

- **Registro**: `manifests/test-assertion-enums.yaml`. Cada enum declara
  `source` + `pointer` y **nunca** copia los valores; el script los lee del
  manifiesto de origen. Un registro que duplicara los valores se desincronizaría
  del contrato — el modo de falla exacto que viene a prevenir. El test
  `test_registry_does_not_inline_values` lo hace imposible.
- **Detección**: AST, no grep. Sólo cuenta como afirmación un **acceso real a
  la clave** (`x["permissionDecision"]`, `x.get("permissionDecision")`, o un
  alias local de cualquiera de los dos) comparado con un literal por `==`,
  `!=`, `in`/`not in` sobre una colección literal, o vía
  `assertEqual`/`assertIn`. Un string que *contiene* el nombre del campo —un
  fixture de bash, un payload que se construye, una búsqueda de substring sobre
  el fuente de un hook, un docstring que describe el bug histórico— no es una
  afirmación y no se marca.
- **Alcance**: `tests/**/*.py`, declarado en el registro.

### Corrida 1 — el bug reintroducido: el gate FALLA

Árbol reconstruido con los dos archivos de test tal como estaban en
`b2f9d877e^`, byte por byte (`git show b2f9d877e^:<path>`), más el look-alike
honesto sin tocar:

```
$ .venv/bin/python3 scripts/audit_test_assertion_enums.py --root $RR
scanned 3 test file(s) for closed-enum assertions [permissionDecision=allow|deny|ask|defer]

2 assertion(s) state a value the enum does not contain:

  tests/hooks/test_secret_detector.py:115
    asserts permissionDecision == 'block'; allowed: allow|deny|ask|defer
    contract: manifests/claude-code-hooks-schema.yaml:events.PreToolUse.permission_decision_values
  tests/unit/test_secret_detector_updated_input.py:215
    asserts permissionDecision == 'block'; allowed: allow|deny|ask|defer
    contract: manifests/claude-code-hooks-schema.yaml:events.PreToolUse.permission_decision_values

A test asserting a value outside the enum does not fail — it CERTIFIES the
defect. Fix the assertion against the contract, do not widen the enum.
EXIT=1
```

### Corrida 2 — el árbol corregido: el gate PASA

Mismos tres archivos, versión de HEAD, y después el árbol real completo:

```
$ .venv/bin/python3 scripts/audit_test_assertion_enums.py --root $FR
scanned 3 test file(s) for closed-enum assertions [permissionDecision=allow|deny|ask|defer]
no test asserts a value outside a registered closed enum
EXIT=0

$ .venv/bin/python3 scripts/audit_test_assertion_enums.py
scanned 2306 test file(s) for closed-enum assertions [permissionDecision=allow|deny|ask|defer]
no test asserts a value outside a registered closed enum
EXIT=0
```

### Corrida 3 — el test honesto que se le parece: PASA en las dos

El look-alike es `tests/audit/test_hook_behavior_classifier.py`, que contiene
literalmente `permissionDecision:"block"` dentro de un fixture de bash, porque
su trabajo es clasificar un hook que emite esa decisión. Un gate por grep lo
marcaría. Estuvo presente en las corridas 1 y 2 y no aparece en ninguna salida.
La suite del gate lo prueba como aserción, no como observación
(`test_honest_lookalike_passes_in_both_directions`), y el archivo real sigue
verde:

```
$ .venv/bin/python3 -m pytest tests/audit/test_assertion_enum_conformance.py -q
..........                                                               [100%]
10 passed in 2.83s

$ .venv/bin/python3 -m pytest tests/audit/test_hook_behavior_classifier.py \
      tests/hooks/test_secret_detector.py \
      tests/unit/test_secret_detector_updated_input.py -q
..................................                                       [100%]
34 passed in 7.20s
```

Árbol restaurado: nada del árbol de trabajo se modificó para las corridas. Las
reconstrucciones se hicieron en el scratchpad con `git show` y `git archive`, y
los cuatro archivos de este commit son todos nuevos:
`git status --short -- tests/audit/test_assertion_enum_conformance.py scripts/audit_test_assertion_enums.py manifests/test-assertion-enums.yaml` no muestra
ningún `M`.

## Qué NO atrapa

Declarado acá y, en forma legible por máquina, en el bloque `not_registered`
del manifiesto, que el test `test_excluded_fields_carry_a_reason` obliga a
mantener poblado y motivado.

1. **Los casos 1, 2 y 4 del encargo.** El `assert ... == ""` de context-budget,
   el `async: true` de la taxonomía de eventos y el `main_worktree` del
   cwd-enforcer no son valores de enum cerrado. Ninguno de los tres se marca.
2. **El campo `decision`** (PostToolUse / UserPromptSubmit / Stop). El manifest
   declara el campo y no sus valores. Registrable el día que el contrato los
   transcriba con su cita; no antes.
3. **El campo `matcher`.** Existe el enum en `manifests/codex-hooks-schema.yaml`
   pero "matcher" es palabra genérica y aparece en este corpus como matcher de
   pytest y de regex. Registrarlo sin un scope por archivo daría falsos
   positivos.
4. **`hookEventName`.** El mapa `events:` del manifiesto es deliberadamente
   parcial: transcribe sólo los eventos que este repo registra y nombra el
   resto en un comentario. Tratar sus claves como enum cerrado marcaría tests
   honestos sobre eventos reales del arnés.
5. **Tests fuera de Python.** El scan es AST de Python. Hoy no hay pérdida
   medible: `grep -rn "permissionDecision" tests/` sin filtro de extensión
   devuelve 43 líneas y todas caen en archivos `.py`.
6. **Valores que se construyen y no se afirman.** Un test que le **manda**
   `permissionDecision: "maybe-later"` a un wrapper para ver cómo lo trata es
   trabajo honesto y no se marca. Es la contracara de no ser paranoico.
7. **El fuente de los hooks.** Este gate mira el corpus de tests. Que un hook
   emita un valor inválido es asunto de
   `tests/contracts/test_claude_code_hooks_schema_conformance.py` y de
   `scripts/audit_payload_field_contracts.py`.

## Cuántos tests del repo lo violan hoy

**Cero**, sobre 2306 archivos de test.

```
$ .venv/bin/python3 scripts/audit_test_assertion_enums.py --json | head -20
{ "enums": [{"field": "permissionDecision", "id": "claude-permission-decision",
             "values": ["allow","deny","ask","defer"]}],
  "files_scanned": 2306, "findings": [], "root": "<repo>" }
```

No hay baseline ni allowlist: el gate exige igualdad exacta con cero. El cero es
de hoy y es reciente — al primer commit del día (`8a2d75c93`) el repo cargaba
**2**, y son las dos que `b2f9d877e` corrigió esta misma tarde:

```
$ git archive 8a2d75c93 tests | tar -x -C $D && \
  git show 8a2d75c93:manifests/claude-code-hooks-schema.yaml > $D/manifests/... && \
  .venv/bin/python3 scripts/audit_test_assertion_enums.py --root $D
scanned 2252 test file(s) ...
2 assertion(s) state a value the enum does not contain:
  tests/hooks/test_secret_detector.py:115
  tests/unit/test_secret_detector_updated_input.py:215
```

Nota sobre el conteo: `files_scanned` se movió entre 2252 y 2306 durante la
sesión porque hay otras sesiones agregando tests en el mismo checkout. El número
de hallazgos no se movió.

## Lo que NO hice y por qué

- **No registré el enum de `decision`.** Habría subido la cobertura del gate sin
  costo aparente y con una deuda invisible: los valores no están en el
  contrato transcripto, así que los habría inventado. Un enum inventado en el
  registro es exactamente la mentira que el gate persigue, una capa más arriba.
- **No construí la señal del corpus de payloads.** El corpus es hoy 52
  registros todos de PostToolUse y sin `tool_input`; exigirlo dejaría sin poder
  pasar a todo test de PreToolUse. Ampliarlo es captura, no análisis estático, y
  no entra en el alcance de este encargo.
- **No toqué ningún test existente.** El gate está en cero sin mover una línea
  ajena. Si hubiera encontrado violaciones, el arreglo correcto es la aserción,
  nunca ensanchar el enum — el script lo dice en su propia salida.
- **No metí el gate en `rules/RULES-COMPACT.md`.** Ese archivo es índice
  compartido y hay cuatro sesiones escribiendo; agregarle una línea desde un
  sub-agente es pedir un conflicto. Queda como decisión del orquestador.
- **Hallazgo lateral que no arreglé**: el docstring de
  `scripts/audit_gate_registration.py` afirma en presente que «`secret-detector`
  blocks via `permissionDecision: "block"`». Desde `b2f9d877e` emite `deny` con
  exit 2. Es una contradicción de documentación, de otro archivo y de otro
  dueño; queda anotada acá y no la corregí desde este encargo.

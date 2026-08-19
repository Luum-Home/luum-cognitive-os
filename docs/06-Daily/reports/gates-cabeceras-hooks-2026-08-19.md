# Gates para las cabeceras de `hooks/**` — 2026-08-19

## Resumen ejecutivo

- **`# Event:` → GATEAR.** Lector real: el registro (`cognitive-os.yaml`). Deriva real hoy: 0.
- **`# Matcher:` → GATEAR.** Mismo lector, misma contrastabilidad. Deriva real hoy: 0.
- **`# Async:` → GATEAR con alcance ampliado.** El gate que existía leía UNA fuente
  (`.claude/settings.json`, que es *generado*). Contra las **cuatro** fuentes reales aparecen
  **12 registraciones derivadas** (4 hooks × 3 plantillas de perfil). Corregidas.
- **`# Latency:` → BORRAR.** Cero lectores en el código, cinco grafías distintas de la
  clave, 8 de 21 hooks sin muestras suficientes para juzgar, y **9 de las 13 medibles se
  contradicen con su propio p50** (hasta ×68). Eliminadas 27 líneas de 24 archivos.
- El censo del encargo (24/13/10/4 "derivadas") medía **presencia**, no deriva.
- Hallazgo mayor: el arreglo del 16 y el 19/08 se aplicó a la copia y no al molde.
  `set-security-profile.sh` copia la plantilla **encima** de `settings.json`: aplicar
  cualquier perfil reinyectaba `async: true` en los cuatro emisores de contexto.

## Correcciones a las premisas del encargo

**1. Los cuatro números (24 / 13 / 10 / 4) no son deriva: son presencia.**

```
$ for k in Event Async Matcher Latency; do printf "%-9s %s\n" "$k" \
    "$(grep -l "^# $k:" hooks/*.sh | wc -l)"; done
Event     24
Async     13
Matcher   10
Latency    4
```

Coinciden dígito por dígito con los del encargo. La deriva real contra el registro
canónico, sobre `hooks/**/*.sh` (31 / 14 / 14 / 21 archivos con la clave), era **0, 1 y 1**
antes de mirar las plantillas de perfil. El censo del arquitecto contó cuántos archivos
*tienen* la clave y lo publicó como cuántos *mienten*.

**2. "La única con gate no derivó nada; las cuatro sin gate derivaron todas" no se
sostiene.** `# Async:` **sí tenía** gate desde antes
(`test_hook_async_header_matches_registration`), y el propio encargo lo señala en el Paso 0.
El experimento natural no tiene el diseño que se le atribuye: no es gate-vs-sin-gate, es
*alcance del gate*. `# SCOPE:` no deriva porque su censo cubre las tres proyecciones;
`# Async:` derivaba porque el suyo cubría una.

**3. "Hoy hay seis cabeceras que mienten sobre latencia por un factor de 10".**
No verifiqué de dónde sale el 6. Lo medido: **13 cabeceras juzgables**, de las cuales **9
mienten ya en el p50** (no en la cola) y **4 sólo en p95**. Por encima de ×10 hay **2**
(`orchestrator-skill-invocation-gate` ×13,0 y `engram-crystallize-on-session-end` ×68,6).
Ni 6 ni ×10: la premisa subestima la cantidad y sobreestima el umbral.

**4. "Se eliminan de los 257 archivos" / "51 líneas de cabecera decorativa".**
La población con clave de latencia son **24 archivos**, no 257. Las líneas borradas fueron
**27**. Los 257 son el total de `hooks/*.sh`, que es la población del censo de `# SCOPE:`,
no la de ninguna de las otras cuatro claves.

**5. `hooks/*.sh` no es el árbol de hooks.** El glob de un nivel ve 257 archivos; `rglob`
ve más (hay hooks en subdirectorios). Todo censo escrito con `hooks/*.sh` es
estructuralmente ciego a ellos. El gate nuevo usa `rglob`.

**6. Restricción del encargo verificada, no asumida.** "No toques
`manifests/claude-code-hooks-schema.yaml` ni el manifest de codex": confirmado con
`git diff --name-only` — ninguno de los dos aparece entre mis modificaciones. Sí aparecen
en el working tree, modificados por los otros dos agentes, tal como el encargo anticipaba.

## La contradicción entre los dos instrumentos de Async

No había contradicción entre dos mediciones del mismo objeto: había **dos objetos
distintos**, y ninguno de los dos era el correcto.

- El censo del arquitecto reportaba 13 = archivos con la clave `# Async:`. No medía deriva.
- El test `test_hook_async_header_matches_registration` medía deriva de verdad, y daba 0
  **correctamente para la fuente que lee**.

La hipótesis que el encargo pedía verificar —"el test cubre sólo los ~154 registrados y el
censo los 257"— es cierta pero no explica nada, porque el censo no medía deriva. Y la
segunda hipótesis —"tratan distinto la ausencia de la clave `async`"— es falsa: el test ya
lo documenta y lo implementa bien (`bool(handler.get("async", False))`, ausente == `false`
== default del host).

Lo que sí estaba mal, y es el hallazgo grande, apareció al preguntar **cuál es la
autoridad**:

```
$ grep -n "settings.json" scripts/compose_agent_prompt.py | head -1
37:  ".claude/settings.json is GENERATED (ADR-064): canonical hook registry is "
$ sed -n '87p' scripts/set-security-profile.sh
# Copy the profile JSON as the new settings.json, stripping metadata-only keys
```

`.claude/settings.json` es una **copia**. Hay CUATRO fuentes de registro:

| fuente | rol | hooks |
|---|---|---|
| `cognitive-os.yaml > harness.hooks` | canónico (ADR-064) | 190 |
| `.claude/settings.json` | proyección viva, generada | 154 |
| `templates/security-profiles/*.json` | moldes que **sobrescriben** la proyección | 3 archivos |
| `scripts/_lib/settings-driver-claude-code.sh` | generador en bash del bloque `hooks` | 1 archivo |

La cuarta apareció **después** de escribir la primera version de este informe, y la
encontro un rojo ajeno: `test_cross_session_event_taxonomy::test_settings_driver_wires_event_emitters_and_context_hooks`.
Es un generador en **bash** —ni JSON ni YAML—, asi que ningun parser de configuracion lo
ve. Su contenido hoy es correcto (`"false"` para los cinco emisores), pero mi gate leia
tres de cuatro moldes: exactamente el defecto que este informe le imputa al gate anterior.
Corregido antes de entregar. La leccion se generaliza: **la pregunta no es "lei el
registro?" sino "cuantas cosas escriben este archivo?"**, y la respuesta en este repo era
cuatro, no una.

El test de conformance lee sólo la segunda. Los arreglos del 2026-08-16
(`subagent-context-injector`) y del 2026-08-19 (los tres `*-prompt-suggest` /
`adr-relevance-suggest`) se aplicaron a la copia. **Las tres plantillas seguían con
`async: true`.** Correr `set-security-profile.sh {minimal,standard,paranoid}` reinyectaba
los cuatro defectos que esos dos informes daban por cerrados, y el test seguía verde hasta
que alguien aplicara un perfil.

Eso responde el "y si el que está mal es el test que hoy da verde, eso es un hallazgo mayor
que el encargo": el test no está *mal*, está **incompleto de alcance**, que en la práctica
es lo mismo — un gate que mira dos de tres fuentes tiene exactamente la forma del defecto
que dejó pasar.

## Clave por clave: GATE / BORRAR / DERIVAR, con su lector real

### `# Event:` → **GATEAR**

- **Qué afirma:** en qué evento del host corre el archivo.
- **Lector real:** el registro. No hay código que parsee la cabecera, pero la afirmación es
  exactamente contrastable contra `cognitive-os.yaml > harness.hooks` y contra las dos
  proyecciones. El lector humano que abre el hook para saber cuándo corre es el consumidor,
  y es el que se equivoca cuando la cabecera miente.
- **Deriva real:** 0 (31 archivos con la clave).
- **Por qué no DERIVAR:** la cabecera es prosa entrelazada con el resto del bloque de
  comentario (`Trigger:`, `Exit:`, `Bypass:`, `Log:`). Generarla exigiría un generador que
  reescriba bloques de comentario en 31 archivos — más superficie de la que ahorra. El gate
  cuesta un test y cubre lo mismo.

### `# Matcher:` → **GATEAR**

- Mismo lector, misma contrastabilidad, deriva 0 sobre 14 archivos.
- Matiz implementado: el matcher del host es un regex alternado (`Bash|Write|Edit`) y la
  cabecera nombra **una** alternativa. La comparación es de contención en ambos sentidos,
  no de igualdad; comparar por igualdad daría falsos positivos en masa.

### `# Async:` → **GATEAR, con las tres fuentes**

- **Lector real:** el host, y —vía `set-security-profile.sh`— las plantillas.
- **Deriva real:** 12 registraciones (4 hooks × 3 plantillas). Corregidas.
- El gate anterior no se borra ni se toca: sigue cubriendo su fuente. El nuevo la amplía.

### `# Latency:` → **BORRAR**

Ver sección propia.

### Bonus: cabecera de registro sobre hook no registrado

Categoría que ninguna de las cuatro claves cubría por separado. Dos casos vivos:
`adr-detector.sh` (`# ASYNC: true`) y `clean-room-ast-similarity-gate.sh`
(`# Event: PreToolUse`, `# Matcher: Bash`). Los dos figuran en
`hooks/_lib/registration-allowlist.txt`, que es donde este repo **ya** declara "no
registrado a propósito" y que es un ratchet que sólo achica. El gate usa esa lista como
excepción, no un baseline propio: **cero entradas de baseline en los cuatro tests**.

## `# Latency:` — por qué no

**No tiene un solo lector.** El único consumidor de latencia en el repo es
`scripts/hook_timing_report.py`, y su tabla `LATENCY_BUDGETS_MS` es **por EVENTO y está
hardcodeada** — no lee ninguna cabecera. Dos autoridades sobre lo mismo, y la que nadie
verifica contradice a la que sí se mide.

**No hay una clave que gatear.** Cinco grafías conviven: `# Latency:`,
`# Latency budget:`, `# Latency target:`, `# p95 latency target:`, `# LATENCY BUDGET:`.
Un gate sobre `# Latency:` habría cubierto 4 archivos de 24 — un gate al 17% de la
población, que es la forma canónica del colchón.

**Y las que se pueden juzgar, mienten.** Medido sobre `hook-timing.jsonl` **más los 7
rotados** de `.cognitive-os/metrics/.archive/`, excluyendo `skipped`, usando
`body_duration_ms` (el trabajo del hook, sin el wrapper), n≥20 para juzgar:

```
POBLACION GLOBAL n=261391  p50=161ms  p95=808ms  p99=2916ms

hook                                    bud     n    p50     p95   veredicto(p50)
engram-crystallize-on-session-end.sh    150   313  10289  10983   MIENTE ×68.6
orchestrator-skill-invocation-gate.sh    30   199    390    869   MIENTE ×13.0
edit-lock-pre-tool.sh                    30  1037    205    703   MIENTE ×6.8
agent-working-dir-inject.sh              50   199    230    452   MIENTE ×4.6
orchestrator-decision-trace.sh          100   194    310    772   MIENTE ×3.1
skill-failure-monitor.sh                 50   313    141    408   MIENTE ×2.8
skill-post-execution-analysis.sh        200   194    541   1218   MIENTE ×2.7
adr-relevance-suggest.sh                250   338    519   4252   MIENTE ×2.1
skill-router-prompt-suggest.sh          500   330   1073  14951   MIENTE ×2.1
rule-router-prompt-suggest.sh           200   341    193    940   sólo p95 ×4.7
rule-md-routing-validator.sh            100  1007     69    217   sólo p95 ×2.2
skill-md-routing-validator.sh           100  1037     52    214   sólo p95 ×2.1
query-tailored-context-inject.sh        300   199    172    368   sólo p95 ×1.2
(8 más: n<20 → NO MEDIBLE, no "cumple")

miente_en_p50=9  sólo_en_p95=4  no_medible=8
```

Reproducible con `scratchpad/lat2.py` (adjunto al final).

**El dato que cierra la discusión:** el p50 global de *todos* los hooks es **161 ms**.
Siete cabeceras prometen ≤50 ms y dos prometen ≤30 ms. Están por debajo del piso del
harness: son físicamente inalcanzables sin importar qué haga el hook. No son mediciones
desactualizadas, son **aspiraciones que nunca se midieron**.

**Por qué no se puede gatear sin trampa.** Un gate `p50 < presupuesto` falla hoy en 9
hooks. Las salidas serían: (a) arreglar 9 hooks —trabajo real, ajeno a este encargo, y en
varios casos el costo es genuino (Python startup, subprocess de engram)—; (b) baseline con
los 9 —colchón, prohibido—; (c) ensanchar el margen hasta que pase —el verde barato que el
encargo prohíbe explícitamente. Y el ×68 de `engram-crystallize` no es contención de una
máquina cargada: es el p50, con n=313, sobre siete archivos rotados.

**Decisión: borrar la promesa numérica, dejar la autoridad medida.** 27 líneas eliminadas
de 24 archivos. La latencia sigue teniendo dueño —`scripts/hook_timing_report.py`, por
evento, contra telemetría real— y ahora es el único. Una latencia declarada que nadie
verifica es una promesa al lector que el repo no sostiene; el conteo de líneas bajando es
el resultado correcto.

**Lo que NO borré:** la prosa no numérica que explica *por qué* un hook es barato
(`best-effort`, `short-circuits immediately`, `corre async-in-background`). No afirma un
número, así que no puede mentir sobre uno.

## La deriva corregida, y quién mentía en cada caso

**12 registraciones, 4 hooks, 3 plantillas. En los 12 mentía el REGISTRO, no la cabecera.**

| hook | cabecera | plantillas | quién mentía | evidencia |
|---|---|---|---|---|
| `skill-router-prompt-suggest.sh` | `Async: false` | `async: true` × 3 | el registro | informe `async-context-emitters-2026-08-19.md`: async en `UserPromptSubmit` entrega el contexto un prompt tarde |
| `rule-router-prompt-suggest.sh` | `Async: false` | `async: true` × 3 | el registro | ídem |
| `adr-relevance-suggest.sh` | `Async: false` | `async: true` × 3 | el registro | ídem |
| `subagent-context-injector.sh` | `Async: false` | `async: true` × 3 | el registro | `check_subagent_context_arrival.py`: 31 arribos genuinos **después** de sacar `async`; con `async` hay emisión (`hook_success`) y cero arribo |

El criterio no fue "la cabecera es más fácil de tocar". Fue que en los cuatro casos existe
evidencia de arribo, medida y citada en informes previos, de que `async` **borra** el
efecto del hook en estos dos eventos. El `settings.json` vivo ya había sido corregido por
esa misma evidencia; lo que quedó sin corregir fue el molde. Corregir la cabecera para que
dijera `true` habría sido documentar el defecto en vez de arreglarlo.

**Los dos casos de cabecera-sin-registro: no mentía ninguno de los dos.**

- `clean-room-ast-similarity-gate.sh` — su propia cabecera ya dice (líneas 21-23) que es
  `manual_trigger` pendiente de ADR-271 Fase 3 y que está en la allowlist. Está registrado
  en `templates/security-profiles/{standard,minimal}.json` pero no en `cognitive-os.yaml`.
  Cero telemetría en el archivo vivo **y en los 7 rotados**, consistente con "pendiente de
  soak". El que estaba incompleto era mi censo, que miraba una sola fuente. Nada que
  corregir en el archivo.
- `adr-detector.sh` — `# ASYNC: true`, sin registro en ninguna de las tres fuentes, cero
  telemetría. Figura en `registration-allowlist.txt:119` con el motivo del ratchet escrito.
  Es un hook muerto, y eso es un hallazgo aparte de este encargo: **no lo toqué**, porque
  decidir si se cablea o se borra es una decisión de operador, no un ajuste de cabecera.
  El gate lo acepta por la allowlist, así que el día que salga de esa lista sin quedar
  registrado, el gate se pone rojo.

## Las dos corridas de cada gate

Gate nuevo: `tests/contracts/test_hook_header_registration_claims.py` (5 tests).

**FALLANDO — `# Async:`, sin inyección: la deriva real de hoy**

```
$ .venv/bin/python3 -m pytest tests/contracts/test_hook_header_registration_claims.py -q
...F.
E   AssertionError: cabecera `# Async:` contradice alguna registración
      adr-relevance-suggest.sh: cabecera dice Async: false pero
        templates/security-profiles/minimal.json lo registra en UserPromptSubmit con async=True
      adr-relevance-suggest.sh: ... paranoid.json ...
      adr-relevance-suggest.sh: ... standard.json ...
      rule-router-prompt-suggest.sh: ... (×3)
      skill-router-prompt-suggest.sh: ... (×3)
      subagent-context-injector.sh: cabecera dice Async: false pero
        templates/security-profiles/minimal.json lo registra en SubagentStart con async=True
      subagent-context-injector.sh: ... (×2 más)
    Arreglo: si el origen es templates/security-profiles/*.json, sacá la clave `async`
    de esa registración: aplicar el perfil copia la plantilla encima de
    .claude/settings.json y reinyecta el defecto.
1 failed, 4 passed in 0.20s
```

**FALLANDO — los otros tres, con deriva inyectada a propósito**

```
$ # Event: UserPromptSubmit -> PreCompact en skill-router-prompt-suggest.sh
$ # Matcher: WebFetch agregado a git-commit-scope-guard.sh (registrado con Bash)
$ # adr-detector.sh sacado de registration-allowlist.txt
$ .venv/bin/python3 -m pytest tests/contracts/test_hook_header_registration_claims.py -q
  skill-router-prompt-suggest.sh: cabecera dice ['PreCompact'], registrado en ['UserPromptSubmit']
  git-commit-scope-guard.sh: cabecera dice 'WebFetch', registrado con ['Bash']
  adr-detector.sh: declara ['Async'] y no figura en ninguna fuente de registro
FAILED ...::test_event_header_names_a_real_registration
FAILED ...::test_matcher_header_names_a_real_registration
FAILED ...::test_registration_header_without_registration
3 failed, 2 passed in 0.17s
```

**FALLANDO — deriva inyectada en el cuarto molde (el generador en bash)**

```
$ # el asiento "false" del generador cambiado a "true" para un emisor
$ .venv/bin/python3 -m pytest tests/contracts/test_hook_header_registration_claims.py -q
  skill-router-prompt-suggest.sh: cabecera dice Async: false pero
    scripts/_lib/settings-driver-claude-code.sh lo registra en None con async=True
1 failed, 4 passed in 0.25s
```

**FALLANDO — el baseline por encima de la realidad**

```
$ # KNOWN_EVENT_HEADER_DRIFT = {"skill-router-prompt-suggest.sh", "no-existe.sh"}
$ .venv/bin/python3 -m pytest tests/contracts/test_hook_header_registration_claims.py -q
E   AssertionError: entradas ya corregidas que siguen en el baseline:
      ['no-existe.sh', 'skill-router-prompt-suggest.sh']. Borralas. Un baseline por
      encima de la realidad es colchón que la próxima regresión ocupa sin encender el rojo.
1 failed, 4 passed in 0.37s
```

**PASANDO — árbol corregido, sin inyecciones**

```
$ .venv/bin/python3 -m pytest tests/contracts/test_hook_header_registration_claims.py \
    tests/contracts/test_claude_code_hooks_schema_conformance.py -q
...............
15 passed in 0.95s
```

El gate anterior sigue verde: no se aflojó nada para hacer pasar el nuevo.

### Forma del gate

- **Censo derivado del árbol**: `sorted(HOOKS_DIR.rglob("*.sh"))`. Ninguna lista curada
  decide qué se revisa; un hook nuevo entra solo, y los subdirectorios no quedan afuera.
- **Baselines vacíos, con las tres aserciones** de
  `test_shipped_audits_declare_population.py`: no absorbe uno nuevo (`unexpected`), no deja
  listado uno ya corregido (`stale`), no guarda asientos sobre archivos inexistentes
  (`ghosts`). Están implementadas en un solo helper, `_assert_baseline`.
- **Un quinto test que protege el alcance del gate**:
  `test_all_registration_sources_are_all_present`, que exige que las **cuatro** fuentes
  hayan aportado asientos. Si mañana alguien renombra el directorio de plantillas o el
  generador en bash, el gate no pierde cobertura en silencio — que es exactamente
  como el defecto de hoy sobrevivió a dos informes que lo daban por cerrado.
- **Mensajes que dicen el arreglo**, incluido el caso específico "el origen es una
  plantilla de perfil" con la razón de por qué eso importa.

## Lo que NO hice y por qué

- **No toqué `manifests/claude-code-hooks-schema.yaml` ni el manifest de codex.** Los tenían
  otros dos agentes. El gate nuevo no los necesita: lee `cognitive-os.yaml`,
  `.claude/settings.json` y `templates/security-profiles/*.json`.
- **No modifiqué `test_claude_code_hooks_schema_conformance.py`.** Su test de `# Async:`
  es correcto para la fuente que lee; ampliarle el alcance in-place habría creado un
  conflicto con el agente que trabaja sobre el manifest que ese archivo consume. El gate
  nuevo es un archivo aparte, y los dos conviven verdes.
- **No arreglé los 9 hooks que exceden su presupuesto de latencia.** Son lentos de verdad
  (arranque de Python, subprocess de engram); acelerarlos es trabajo de performance, no de
  cabeceras. Borré la promesa, no la evidencia: los números medidos quedan en este informe
  y en `scripts/hook_timing_report.py`.
- **No borré `adr-detector.sh`** pese a estar muerto (cero registros, cero telemetría en 8
  archivos de timing). Borrar un hook es decisión de operador.
- **No promoví los scripts de medición** (`scratchpad/census.py`, `scratchpad/lat2.py`) a
  `scripts/`. El primero quedó subsumido por el test — que es la forma ejecutable
  definitiva de esa medición. El segundo mide algo que el repo ya reporta por evento
  (`scripts/hook_timing_report.py`); agregar un tercer instrumento de latencia habría
  repetido el error de tener dos autoridades. Los números de este informe se reproducen
  con `hook_timing_report.py` más el fragmento pegado arriba.
- **No pusheé ni commiteé.** Todo queda en el working tree.

---

### Evidencia ejecutable

### Suite de contratos completa

```
$ .venv/bin/python3 -m pytest tests/contracts/ -q -p no:randomly --timeout=120
5 failed, 844 passed, 3 skipped, 16 xfailed in 785.63s
```

Los 5 rojos son previos a este trabajo y ninguno es mio. Triaje:

| test | por que no es mio |
|---|---|
| `test_hook_quality_system` (x2) | `manifests/hook-quality.yaml` desincronizado de `cognitive-os.yaml`, que no toque. Verificado sacando mi archivo de test del arbol: el `--check` falla identico con y sin el. |
| `test_cross_session_event_taxonomy::test_settings_driver_wires_event_emitters_and_context_hooks` | espera `"true"` para un emisor en el generador; el generador dice `"false"` desde el arreglo del 19/08. El test quedo viejo respecto de ese cambio. `git status` sobre el generador: limpio, no lo modifique. |
| `test_core_extensions_split::test_aspirational_audit_reports_zero_active_dormant_debt` | auditoria de deuda dormant, sin relacion con cabeceras. |
| `test_p95_hook_latency::test_no_hook_p95_exceeds_ceiling` | lee telemetria, no cabeceras. Corrobora la seccion de latencia de este informe desde el otro lado: los hooks efectivamente exceden. |

```bash
# El gate (censo derivado, baselines vacios, cuatro fuentes)
.venv/bin/python3 -m pytest tests/contracts/test_hook_header_registration_claims.py -q

# La afirmación de que el encargo contó presencia y no deriva
for k in Event Async Matcher Latency; do \
  printf "%-9s %s\n" "$k" "$(grep -l "^# $k:" hooks/*.sh | wc -l)"; done

# Cero promesas numéricas de latencia sobrevivientes
grep -rniE "latency" hooks/*.sh | grep -cE "[0-9]+\s*(ms|s)\b"   # -> 0

# La autoridad de latencia que sí se mide
.venv/bin/python3 scripts/hook_timing_report.py
```

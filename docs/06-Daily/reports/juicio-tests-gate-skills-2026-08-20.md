# Juicio de los tests y la documentación de `orchestrator-skill-invocation-gate.sh`

Fecha: 2026-08-20 · Alcance: read-only · Objeto: `hooks/orchestrator-skill-invocation-gate.sh`,
sus tres suites, ADR-188, `rules/skill-invocation-mandatory.md`, manifiestos y el mensaje de bloqueo.

## Veredicto

La suite prueba bien el gate que ADR-188 describe (12 de 16 mutantes muertos), pero ese gate no es el
que corre: en producción evalúa una sugerencia de hace 48 días contra un contador global de 143, y la
conducta que se acaba de agregar para arreglarlo —abstenerse sin identidad de sesión— sobrevive a
todas las mutaciones porque ningún test la toca.

## Correcciones a las premisas del encargo

1. **«El hook está quieto mientras vos lo analizás» — falso, y me obligó a rehacer la medición.**
   El archivo cambió entre mi primera lectura (`shasum a28555…` era `1c14d…`, 8158 bytes, 01:49) y mi
   cuarta llamada (10382 bytes, 01:57). Los mutantes M1–M10 se generaron de la versión vieja. Rehíce
   la matriz completa contra la versión de las 01:57 y **todo lo que reporto abajo es de esa versión**.
   El objeto de un juicio de mutación tiene que estar congelado: pegué copia en
   `scratchpad/mut/v2/M0_control.sh` y medí contra la copia, no contra el archivo vivo.

2. **«El conteo acumulado de bypasses apareció sin ADR» — parcialmente falso.** El contador *por
   sesión* y el umbral de 3 SÍ están decididos por escrito: ADR-188 §Enforcement layers y
   `rules/skill-invocation-mandatory.md` §Enforcement, que hasta declara la ruta
   `.cognitive-os/runtime/skill-bypass-counter-<session_id>`. Lo que nunca se decidió es la
   **acumulación entre sesiones**: los 143 del archivo `skill-bypass-counter-unknown` no son una
   política, son el efecto de que `session_id` colapse a la clave `unknown`. La premisa correcta no es
   "falta el ADR" sino "el ADR describe un contador que en la realidad nunca fue por sesión".

3. **«El mensaje del gate ofrece un remedio que nadie puede ejecutar» — cierto, pero por una razón
   distinta a la del encargo.** El encargo lo atribuye a que la anotación no se puede escribir. Medí
   que la anotación SÍ funciona cuando va en el `tool_input` y nombra la skill correcta (el test de
   contrato lo prueba y mi sonda lo reprodujo). Lo que la rompe es otra cosa: el gate exige el nombre
   que devuelve `last_suggestion()` —hoy `repo-forensics`, de julio— y el orquestador anota la skill
   que el router acaba de sugerirle (`auto-refine`). Sonda 1 abajo: anotar `auto-refine` con
   `repo-forensics` vigente da WARN igual. La salida existe; apunta a otro lado.

4. **«Los tests de hooks escriben en `.cognitive-os/metrics/*.jsonl`» — no estos.** Las tres suites
   redirigen con `COGNITIVE_OS_PROJECT_DIR` a un `tmp_path`. 0 filas ensuciadas en 17 corridas
   completas (ver sección siguiente). La advertencia era correcta como precaución y falsa como
   diagnóstico de estas suites.

5. **«El gate está registrado sólo en `Agent`» — lo creí y me equivoqué; lo corrijo antes de que
   viaje.** `.claude/settings.json` lo lista una sola vez, bajo matcher `Agent`. Pero el brazo `Bash`
   está cableado indirectamente: `hooks/bash-hot-path-dispatcher.sh:153` lo invoca
   (`_run_gate "hooks/orchestrator-skill-invocation-gate.sh" || exit $?`). Los dos brazos que declara
   `cognitive-os.yaml` existen. Lo que sí queda sin probar es la composición dispatcher→gate.

## Cuántas filas de telemetría ensucié al medir

**Cero.** `.cognitive-os/metrics/skill-bypass.jsonl`: 12 filas antes, 12 después, mismo contenido.

```bash
wc -l < .cognitive-os/metrics/skill-bypass.jsonl   # 12   (antes)
shasum .cognitive-os/metrics/skill-bypass.jsonl    # 1c14d05f16fe796f346adaa923285a53598d1ec4
# ... 17 corridas de las 3 suites (1 control + 16 mutantes) + 4 sondas ...
wc -l < .cognitive-os/metrics/skill-bypass.jsonl   # 12   (después)
shasum .cognitive-os/metrics/skill-bypass.jsonl    # 1c14d05f16fe796f346adaa923285a53598d1ec4
```

Motivo: las tres suites exportan `COGNITIVE_OS_PROJECT_DIR=<tmp_path>` y el hook deriva
`METRICS_DIR` de ahí. Mis sondas hacen lo mismo y además hacen `env.pop` de
`COS_ALLOW_PROTECTED_CONFIG_WRITE`, `COS_METRICS_DIR`, `COS_ALLOW_SKILL_BYPASS`,
`COS_SKILL_BYPASS_REASON` y el killswitch, para que el subproceso no herede el permiso con el que yo
leí el archivo protegido.

No ensucié, pero **encontré sucio de antes**: `.cognitive-os/runtime/skill-bypass-counter-unknown`
contiene `143` y sigue en disco. Es el bucket compartido, no lo toqué.

## Los tests bajo mutación: cuáles sobreviven

Método (reproducible): copio el hook, lo mutilo con `sed`/`awk`, copio las tres suites a un directorio
neutro reapuntando su constante `HOOK`/`ARTIFACT` a `os.environ["COS_MUT_HOOK"]`, y corro pytest una
vez por mutante. Scripts en `scratchpad/mut/` (`mkmutants.sh`, `prep_tests.sh`, `probe_mismatch.py`).

```bash
S=<scratchpad>/mut
cd "$S/suite2"
env -u COS_ALLOW_PROTECTED_CONFIG_WRITE COS_MUT_HOOK="$S/v2/M8_never_block.sh" \
  .venv/bin/python3 -m pytest t_contracts.py t_audit.py t_portability.py -o addopts= -q
```

Control M0 (copia idéntica): **15 passed**. La reubicación no altera el veredicto.

| Mutante | Qué rompe | Resultado |
|---|---|---|
| M1 | `exit 0` tras el killswitch (el gate no hace nada) | **muerto** — 10 fallan |
| M2 | `INVOKED=1` siempre | **muerto** — 8 fallan |
| M3 | el contador no incrementa | **muerto** — 2 fallan |
| M4 | `_emit_audit` mudo | **muerto** — 8 fallan |
| M5 | umbral `>=0.90` invertido a `<0.90` | **muerto** — 11 fallan |
| M6 | sin dedup del marcador de pass | **muerto** — 1 falla |
| M7 | env-override sin razón no bloquea | **muerto** — 1 falla |
| M8 | umbral de BLOCK 3 → 99 (nunca bloquea) | **muerto** — 2 fallan |
| M9 | anotación `SKILL_BYPASS` ignorada | **muerto** — 1 falla |
| M10 | la fila de auditoría pierde `reason` | **muerto** — 8 fallan |
| M11 | `INVOKED=0` siempre (nunca reconoce la invocación) | **muerto** — 3 fallan |
| M12 | el killswitch se ignora | **muerto** — 1 falla |
| M13 | se borra el filtro de `tool_name` (corre para toda herramienta) | **SOBREVIVE** — 15 passed |
| M14 | la abstención sin sesión **bloquea** (exit 2) en vez de permitir | **SOBREVIVE** — 15 passed |
| M15 | la abstención no deja ninguna fila anónima | **SOBREVIVE** — 15 passed |
| M16 | vuelve al bug histórico: `SESSION_ID` vacío ⇒ `"unknown"` | **SOBREVIVE** — 15 passed |

**Puntaje: 12 de 16 mutantes muertos (75 %).**

Y del otro lado, por test — de los 15 tests, **13 mueren con al menos un mutante y 2 no mueren con
ninguno**:

- `t_contracts::test_last_suggestion_returns_highest_confidence_for_session` — no ejecuta el hook. Es
  un unit test de `cos_lib.skill_router` alojado en el archivo de contratos del gate; por
  construcción, ninguna mutación del hook puede matarlo.
- `t_portability::test_..._passes_unrelated_tool_from_arbitrary_project_root` — manda
  `tool_name="Read"` sobre un `tmp_path` sin sugerencias sembradas. En ese payload **todos** los
  caminos del hook terminan en `exit 0`: el filtro de herramienta, el `LS_OUT` vacío, y ahora también
  la abstención. Afirma `returncode == 0` sobre una entrada donde el 0 está garantizado aunque el
  hook no exista. Por eso M13 pasa entero.

El mutante que más importa es **M16**: reintroduce textualmente el bug que la cabecera del propio
hook acaba de documentar como causa raíz (143 en un bucket compartido, bloqueo permanente de todo
payload anónimo) y **la suite lo deja pasar**. El arreglo que se acaba de escribir no tiene ni un
test que lo defienda de su propia regresión.

## Efecto vs forma, aserción por aserción

Clasificación: **efecto** = algo cambió en disco, en el veredicto del consumidor o en la clasificación
de una fila. **forma** = un exit code, un literal en stderr, la presencia de un campo.

`tests/contracts/test_skill_invocation_gate.py` (8 tests)

| Test | Aserciones | Tipo | Muere con |
|---|---|---|---|
| `high_confidence_skill_invoked_passes` | `rc==0`; contador **no** existe | forma + efecto (ausencia) | M11 |
| `bypass_annotation_passes_and_audits` | `rc==0`; fila existe; `suggested_skill`, `actor`, `confidence` | efecto | M1, M2, M4, M5, M9, M10 |
| `bespoke_warns_then_blocks_after_three` | `rc` 0/0/2; `"WARN"`, `"1/3"`, `"2/3"`, `"BLOCK"` en stderr | **forma** (literales) | M1, M2, M3, M5, M8 |
| `low_confidence_no_enforcement` | `rc==0`; sin contador; sin fila; sin `"WARN"` | efecto (ausencia) | M5 |
| `env_override_with_reason_passes_and_audits` | `rc==0`; `actor=="env-override"`; razón contiene el texto | efecto | M1, M2, M4, M5, M10 |
| `env_override_without_reason_blocks` | `rc==2`; `"COS_SKILL_BYPASS_REASON"` en stderr | **forma** | M1, M2, M5, M7 |
| `killswitch_disables_hook` | `rc==0`; sin `"WARN"` | **forma** | M12 |
| `last_suggestion_returns_highest_confidence` | max por sesión; `None` para otra sesión | efecto (de la lib, no del hook) | **ninguno** |

`tests/hooks/test_skill_invocation_gate_audit.py` (6 tests) — la suite fuerte

| Test | Aserciones | Tipo | Muere con |
|---|---|---|---|
| `unannotated_bypass_writes_an_audit_row` | `rc==0`; `"WARN"`; exactamente 1 fila | efecto + forma | M1, M2, M4, M5, M10 |
| `audit_row_carries_the_consumer_contract` | 4 campos del contrato; valores; `outcome`; `reason` no vacío; `ts` parseable | efecto | M1, M2, M4, M5, M10 |
| `consumer_classifies_the_row_as_bypassed` | control `UNMEASURABLE==1` → tras el gate `BYPASSED==1`, `UNTRACED==0`, `UNMEASURABLE==0`, exit 0 | **efecto puro, punta a punta** | M1, M2, M4, M5, M10 |
| `block_also_writes_its_row` | `[0,0,2]`; 3 filas; `outcome=="blocked"`; razón no vacía | efecto | M1..M5, M8, M10 |
| `invoked_emits_a_pass_row_not_counted_as_bypass` | 1 fila; `outcome=="invoked"`; `reason==""`; consumidor `BYPASSED==0` | efecto | M1, M4, M5, M10, M11 |
| `pass_rows_are_deduplicated_per_prompt` | 4 corridas ⇒ 1 fila | efecto | M1, M4, M5, M6, M10, M11 |

`tests/red_team/portability/test_orchestrator-skill-invocation-gate.py` (1 test): `rc==0`. **Forma
pura sobre una entrada trivial.** No muere con nada.

Lectura: la suite de `tests/hooks/` es la que sostiene el gate y es casi toda de efecto —
`consumer_classifies_the_row_as_bypassed` incluso cierra el lazo contra el consumidor real. Las de
forma (`WARN`/`BLOCK`/`1/3` en stderr) no certifican un defecto hoy, porque van acompañadas de una
aserción de efecto en el mismo test o en un vecino. **Ninguna de las 15 aserciones afirma una
conducta rota.** El problema de esta suite no es certificar el defecto: es que le falta la mitad
nueva del hook.

Sí hay una aserción que envejece mal: `bespoke_warns_then_blocks_after_three` depende de los literales
`"1/3"` y `"2/3"`. Si alguien hace configurable el umbral, ese test se pone rojo por el formato del
mensaje, no por la conducta.

## Lo que la documentación afirma y el código no hace

1. **ADR-188 §Operational Guide: la anotación va «in the assistant response»**, con el formato
   `SKILL_BYPASS: <skill-name> (confidence <score>) — <concrete-reason>`. El hook sólo lee
   `.tool_input` (líneas 67-72: `tostring`, `.prompt`, `.command`, `.cmd`, `.description`). Una
   anotación en la prosa del asistente es invisible. `rules/skill-invocation-mandatory.md` dice lo
   correcto («emit a one-line annotation in the tool input») y con otro formato
   (`confidence=<N.NN>`). **La misma decisión contiene las dos versiones y una es inejecutable.**

2. **ADR-188 §Answers: «absences mean the skill was invoked».** Falso en las dos direcciones. Hoy el
   código escribe una fila `outcome="invoked"` en el caso positivo (línea 175), así que la invocación
   deja rastro, no ausencia. Y la ausencia significa, en la práctica, que el gate se abstuvo o que
   `last_suggestion()` devolvió `None`.

3. **ADR-188 §Answers: «Is the gate firing (< 30 ms)? — check `tests/contracts/test_skill_invocation_gate.py`
   p99 latency assertion».** Esa aserción no existe. El archivo tiene 208 líneas y ni una medición de
   tiempo (`grep -n "latency\|perf_counter\|elapsed" tests/contracts/test_skill_invocation_gate.py`
   no devuelve nada). El ADR remite a una prueba imaginaria.

4. **ADR-188 AC#2 y §Falsifiable Claim #4: «Latency budget: < 30 ms», «p99 < 50 ms».** Telemetría real
   del arnés, `.cognitive-os/metrics/hook-timing.jsonl`, n=4 mediciones de este hook: **p50 = 642 ms,
   p95 = 671 ms, máx = 724 ms**. Mi propia medición aislada (5 corridas, máquina cargada) da mediana
   228 ms. Cualquiera de las dos incumple el presupuesto por un orden de magnitud: el hook arranca
   hasta tres `python3` por invocación. Y el arreglo de hoy **borró la línea `# Latency budget: <30 ms.`
   de la cabecera del hook** sin tocar el ADR: eso apaga la contradicción del lado que no la mide, que
   es exactamente el verde barato de `gates-sin-trampa`.

5. **ADR-188 AC#5: «`skill-bypass.jsonl` accumulates one entry per bypass (annotated or
   env-overridden)».** El código emite cinco `outcome` distintos: `invoked`, `bypass-annotated`,
   `env-override`, `bypass-unannotated`, `blocked`. El AC describe dos de los cinco.

6. **ADR-188 §Decision y AC#1: «the highest-confidence suggestion since the most recent user prompt».**
   El anclaje existe en `last_suggestion()` pero nunca se activa: busca eventos
   `user_prompt_submit`/`user_prompt` en `.cognitive-os/sessions/events.jsonl`, y ese archivo tiene
   28 795 filas donde los tipos más frecuentes son `session-heartbeat` (15 431), `merge_queued`
   (3 662), `file-write-intent` (2 082) — ninguno de anclaje. Sin ancla, el docstring dice
   explícitamente «we treat the entire suggestion log for that session as in-scope». Resultado medido:

   ```bash
   .venv/bin/python3 -c "import sys;sys.path.insert(0,'.');\
   from cos_lib.skill_router import last_suggestion;print(last_suggestion('unknown',project_root='.'))"
   # {'skill': 'repo-forensics', 'confidence': 0.99,
   #  'prompt_hash': '0c2d5e662ce11ff8', 'timestamp': '2026-07-03T18:39:16.715516+00:00'}
   ```

   **El gate lleva 48 días exigiendo la misma skill de julio.** Las 12 filas del log lo confirman:
   las 12 son `repo-forensics`, `outcome=blocked`, `session_id=unknown`, con el contador de 132 a 143.

7. **ADR-188 §Enforcement y la regla: «el contador es por `session_id`».** `skill-suggestion.jsonl`
   tiene 582 filas y **una sola** `session_id` distinta: `"unknown"`. Lo mismo del lado del gate. El
   contador nunca fue por sesión; fue uno global que cruzó el umbral de 3 en mayo y desde entonces
   bloquea todo. La premisa 2 de mi encargo se corrige acá: está decidido por escrito, pero lo escrito
   nunca ocurrió.

8. **ADR-188 AC#2: registrado «via `scripts/_lib/settings-driver-claude-code.sh`» en los matchers
   `Agent` y `Bash`.** En `Agent` es directo. En `Bash` ya no: pasa por
   `hooks/bash-hot-path-dispatcher.sh:153`. El ADR describe un cableado que cambió y nadie actualizó.

9. **ADR-188 §Operational Guide y `rules` §Emergency Env Override, la salida del bloqueo.** El ADR la
   escribe como `COS_ALLOW_SKILL_BYPASS=1 COS_SKILL_BYPASS_REASON='<text>' <agent-launch>`. Un hook es
   hijo del arnés, no del shell del Bash tool: ese prefijo le pone la variable al comando y nunca al
   hook, que ya decidió. `scripts/audit_killswitch_activation.py` marca las dos salidas emitidas por
   este hook como **`incompleto`** — «mensaje emitido que nombra la variable sin nombrar vía»
   (líneas 228 y 246). Las vías que sí funcionan (`export` antes de lanzar el arnés, o el bloque `env`
   de `.claude/settings.json`) no aparecen en ningún mensaje ni en el ADR.

   ```bash
   .venv/bin/python3 scripts/audit_killswitch_activation.py --json \
     | .venv/bin/python3 -c "import json,sys;[print(e) for e in json.load(sys.stdin) \
       if 'orchestrator-skill-invocation-gate' in e['file']]"
   ```

10. **`manifests/hook-quality.yaml`: `max_runtime_ms: 1500`, `maturity: observe`,
    `bypass_policy: not_required_observe_only`.** El manifiesto se dio a sí mismo 50× el presupuesto
    del ADR y clasifica como «observe» un hook que sale con exit 2. Los `behavior_tests` que lista
    incluyen cuatro archivos (`test_bash_hot_path_dispatcher_*`, `test_primitive_coherence_audit`,
    `test_research_quality_advisor`) que no ejercitan la conducta del gate: lo nombran de pasada.

## Lo que el código hace y nadie documentó

1. **Se abstiene cuando no puede probar la identidad de la sesión, y escribe en otro archivo.** Desde
   el cambio de las 01:57, `SESSION_ID` vacío ⇒ fila en
   `.cognitive-os/metrics/anonymous/skill-bypass-anonymous.jsonl` con `outcome="abstained"` y `exit 0`.
   No está en ADR-188, ni en `rules/skill-invocation-mandatory.md`, ni en ningún manifiesto — el
   directorio ni siquiera existe todavía en el repo. Es la conducta más consecuente del hook (decide
   si el gate rige o no) y es la que M14/M15/M16 muestran sin ningún test. Consecuencia práctica que
   nadie escribió: si en producción `session_id` sigue resolviendo vacío —y las 582 sugerencias dicen
   que sí—, **el gate pasa a ser un no-op silencioso** y `skill-bypass.jsonl` deja de crecer. Alguien
   va a leer ese cero como «nadie bypasseó».

2. **Reconoce la invocación con un `/{skill}` suelto en cualquier parte del `tool_input`.** El regex de
   la línea 75 acepta tres formas y el ADR sólo documenta dos y media: `Load skills/X/SKILL.md`,
   `skill: "X"` y —no documentada— `/X` seguido de espacio, fin de línea o backtick, buscada sobre el
   `tostring` del `tool_input` entero. Un `cd /repo-forensics`, una ruta, o el nombre citado en prosa
   dentro de un prompt satisfacen el gate. El propio test
   `invoked_emits_a_pass_row...` usa `"/run-tests --quick"` como comando: la rama laxa es la que está
   bajo prueba, no la documentada.

3. **`COS_METRICS_DIR` redirige la escritura de auditoría.** Agregada hoy, con comentario en el código
   y en ninguna doc. Cambia dónde aparece la evidencia de un bloqueo.

4. **Marcador de deduplicación en `.cognitive-os/runtime/skill-gate-pass-<sesión>-<hash>-<skill>`.**
   Archivos que se crean y nunca se limpian. No están en `runtime_artifacts` del ADR (que sólo declara
   `skill-bypass.jsonl`), ni el contador `skill-bypass-counter-<sid>` está declarado ahí.

5. **La razón del BLOQUEO lleva el contador crudo dentro del texto** (`"BLOCK tras 143 bypasses sin
   anotacion..."`). Cuando el contador es global, esa frase afirma algo falso sobre la sesión — las 12
   filas de hoy dicen «tras 132…143 bypasses en la sesión» con el mismo `prompt_hash`. El campo cuenta
   reintentos y el texto los llama comportamiento.

6. **`jq` o `python3` ausentes ⇒ `exit 0` silencioso** (líneas 27-28). Degradación razonable, sin
   registrar y sin documentar: idéntica desde afuera a «no había nada que bloquear».

## Qué deberían afirmar los tests, en prosa

Para quien los vaya a escribir. Lo que ya está en `tests/hooks/` se conserva tal cual — es la parte
sana. Falta esto:

- **Que sin identidad de sesión el gate se abstiene, y que abstenerse tiene las dos mitades.** Un
  payload sin `session_id` y sin `COGNITIVE_OS_SESSION_ID`, con una sugerencia de alta confianza
  sembrada, debe salir 0, **no** debe tocar `skill-bypass.jsonl`, **no** debe crear ni leer ningún
  `skill-bypass-counter-*`, y **debe** dejar exactamente una fila en el bucket anónimo con
  `outcome="abstained"` y `session_id: null`. Los tres pedazos por separado: si sólo se afirma el
  exit 0, M14/M15/M16 siguen vivos.

- **Que el bucket `unknown` no puede volver.** Dos payloads anónimos consecutivos no deben producir
  escalamiento: el segundo tiene que salir 0 igual que el primero, aunque haya un
  `skill-bypass-counter-unknown` con un número alto ya puesto en el `PROJECT_DIR` de prueba. Ese
  fixture —un contador viejo de 143 sembrado a mano— es el test de regresión que le faltaba al
  arreglo de hoy.

- **Que el contador es de la sesión que lo generó.** Dos `session_id` distintos, cada uno con su
  sugerencia; tres bypasses en la sesión A deben bloquear A y dejar a B en su primer aviso. Hoy nada
  afirma el aislamiento, y era justamente lo que estaba roto.

- **Que la sugerencia tiene que ser de este prompt.** Sembrar una sugerencia con `ts` de hace 40 días
  y un evento `user_prompt_submit` posterior en `events.jsonl`: el gate no debe exigir nada. Y la
  variante que decide el diseño: sin ningún evento de anclaje, ¿el gate se abstiene o aplica la
  sugerencia más vieja del log? Hoy aplica la más vieja y nadie lo eligió. El test tiene que
  fijar la respuesta que el equipo quiera, pero tiene que fijarla.

- **Que la anotación que el gate acepta es la que el operador puede escribir.** Sembrar la skill X y
  anotar `SKILL_BYPASS: Y` debe seguir avisando (correcto), pero el mensaje de aviso debe nombrar X
  para que Y sea corregible. Y el formato del ADR
  (`SKILL_BYPASS: X (confidence 0.95) — razón`) debe aceptarse igual que el de la regla
  (`SKILL_BYPASS: X confidence=0.95 reason=...`), o el ADR se corrige. Un test por formato.

- **Que la anotación fuera del `tool_input` no cuenta.** Explícito: un payload cuya única mención de
  `SKILL_BYPASS` está en un campo que el hook no lee debe avisar. Ese test convierte en rojo la frase
  «in the assistant response» del ADR, que es lo que se quiere.

- **Que reconocer la invocación no es reconocer una cadena.** Un comando que contiene `/repo-forensics`
  como parte de una ruta (`ls /tmp/repo-forensics/`) **no** debe contar como invocación. Si el equipo
  decide que la forma laxa se queda, entonces el test la afirma a propósito y el ADR la documenta;
  hoy no está ni afirmada ni documentada.

- **Que el pass no se puede leer como bypass, ya cubierto, más su recíproco:** que la fila de bloqueo
  llegue al consumidor clasificada como `BYPASSED` (hoy sólo se prueba con la fila de aviso).

- **Que el filtro de herramienta filtra.** El test de portabilidad actual afirma 0 sobre una entrada
  donde todo da 0. Debe sembrar una sugerencia de alta confianza *y* mandar `tool_name="Read"`: recién
  ahí el exit 0 significa «el filtro funcionó». Con eso M13 muere.

- **Que el presupuesto de latencia es un número medido o no es un presupuesto.** O se agrega una
  aserción de tiempo (la que el ADR ya dice que existe), o se corrige el ADR a lo que
  `hook-timing.jsonl` mide. Las dos cosas cierran; dejarlo como está es la tercera opción, que es la
  que hay hoy.

- **Que el mensaje de bloqueo ofrece una vía ejecutable.** Un test que corra
  `scripts/audit_killswitch_activation.py` y falle si este hook aparece con veredicto `incompleto`.
  Es el único de la lista que no necesita fixture: el instrumento ya existe y hoy lo marca dos veces.

## Lo que no pude medir

- **Por qué `session_id` llega vacío en producción.** El envelope capturado
  (`tests/fixtures/hook-payload-envelope/envelope.json`) declara `session_id` presente en las 2 013
  observaciones de `PreToolUse` — pero su propio `source` dice «reconstructed from harness
  transcripts», no capturado del stdin de un hook. Contra eso, 582 de 582 sugerencias y 12 de 12
  filas del gate resolvieron a `unknown`. Una de las dos fuentes miente y no tengo con qué desempatar
  sin instrumentar el stdin real del hook, que sería escribir, no leer.

- **Si el gate llega a correr por el brazo `Bash`.** Verifiqué el cableado
  (`bash-hot-path-dispatcher.sh:153`) pero no que el dispatcher le pase el payload íntegro ni que
  respete su exit 2. Ninguna de las tres suites cubre esa composición.

- **La latencia con la máquina en reposo.** Los 228 ms de mediana son de una máquina a load alto. Los
  642 ms de `hook-timing.jsonl` son del arnés real pero con n=4. Ninguno de los dos es un p99 en el
  sentido del ADR; los dos incumplen el presupuesto por márgenes que ningún ruido explica.

- **Si `.cognitive-os/metrics/anonymous/` funciona bajo el arnés real.** Lo vi crearse en mi sonda
  aislada. En el repo todavía no existe, así que la rama nunca se ejecutó en producción.

- **Las tres suites en su ubicación original.** Corrí copias reapuntadas para no tocar el hook vivo
  que otro agente está editando. El control M0 da 15/15 idéntico, pero no descarto que el `conftest.py`
  de la raíz (inyección de markers, `COS_METRICS_DIR`) cambie algo que mi `conftest` mínimo no
  reproduce.

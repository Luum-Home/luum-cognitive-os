# Tests que escriben la telemetría del operador — 2026-08-20

## Resumen ejecutivo

- **Censo de escritores** (población declarada): `grep -rl 'cognitive-os/metrics' hooks/*.sh | wc -l` → **111 hooks** escriben en `.cognitive-os/metrics/`. De ésos, **3 honraban `COS_METRICS_DIR`** (ahora 4) y **12 usan `resolve_session_dir`**. O sea: **96 de 111 construyen la ruta a mano** y ningún mecanismo previo los alcanza. La respuesta al "¿ya existe el mecanismo?" es **no**: los dos candidatos (`COS_METRICS_DIR`, `COS_SESSION_SCOPED_METRICS`) son mediados por helper y cubren ≤11% de la población.
- **Archivos con escrituras confirmadas durante corridas de test**: `skill-bypass.jsonl` (probado, ver §Las tres corridas). Además `hook-health.jsonl` y `protected-config-bypass.jsonl` crecieron durante mis corridas, pero **no puedo atribuirlos**: hay sesiones vivas del operador escribiendo en paralelo. Ceguera declarada, no resuelta.
- **Filas contaminadas**: **12 de 12** en `skill-bypass.jsonl` son replays sintéticos (§Cuántas filas son de test).
- **Decisión sobre las 12 filas: se dejan.** Borrarlas es exactamente lo que voy a prohibir. Argumento completo en §Qué hago con las 12 filas.
- **Arreglo**: dos capas en un `conftest.py` de la **raíz** (prevención por env + detección por filesystem, que atrapa el `open(..., "a")` directo) y el fin del bucket por defecto en `orchestrator-skill-invocation-gate.sh`.
- **Parte (2), el contador**: medida y **no implementada**, por orden explícito de prioridad. Veredicto: **mide una cosa distinta de la que dice, y no debería gobernar**. §Veredicto del contador.

## Correcciones a las premisas del encargo

1. **"11 filas" → son 12, y siguen subiendo.** Al empezar eran 11; al recontar, sin que yo escribiera nada, eran 12 y el contador había pasado de 142 a 143. La contaminación no es un hecho pasado que se audita: está ocurriendo mientras se la mide.
2. **"Diez incrementos en dos minutos" describe mal el contador.** El contador **no es de sesión ni se reinicia nunca**: `.cognitive-os/runtime/skill-bypass-counter-unknown` **nació el 2026-05-18** y acumula monótonamente desde entonces (`stat -f %SB`). Los "10 incrementos" son la cola visible de 143 acumulados en 94 días. El mensaje que emite el gate —"tras N bypasses **en la sesión**"— es falso en las dos mitades: ni son bypasses ni son de una sesión.
3. **"Los tests escriben en la telemetría" es cierto pero no es el mecanismo completo.** Las dos suites que más obviamente tocan este hook (`tests/hooks/test_skill_invocation_gate_audit.py`, `tests/contracts/test_skill_invocation_gate.py`) **hacen las cosas bien**: fijan `COGNITIVE_OS_PROJECT_DIR` a `tmp_path` y pasan `session_id`. El que contamina es un llamador sin identidad y sin override de PROJECT_DIR. No lo identifiqué por nombre (§Lo que NO hice).
4. **"El bucket por defecto hereda la identidad de la sesión viva del operador" — no exactamente, y la corrección importa.** No hereda la identidad del operador: crea una identidad **de nadie** que todos comparten. En 94 días **el único contador que existió es el `-unknown`**: no hay ni uno solo para una sesión real, en un `runtime/` que no se limpia (sobreviven archivos del 2026-05-16). Es peor que herencia — el estado compartido es el **único** estado que el gate tuvo jamás.
5. **"Sólo un hook usa identidad fabricada para gobernar" resultó ser lo que quedó, no lo que medí primero.** Mi primer grep dio 1 y era frágil. Refinado: **30 hooks fabrican** una identidad de reemplazo y **33 la interpolan en una ruta**; de ésos, **1** la usa como clave de estado suelto que decide (el gate), y **7** la usan para `sessions/$SESSION_ID/...`. Esos 7 quedan sin auditar (§Lo que NO hice).
6. **`session_id` vacío en 296.383/296.383 filas** — no lo verifiqué, viene del encargo. Lo que sí verifiqué es coherente con eso, y por eso el arreglo **no asume que la identidad normalmente llega**: se abstiene, que es la rama barata.

## Qué archivos reciben escrituras de tests

Censo con población y ceguera, reproducible:

```bash
grep -rl 'cognitive-os/metrics' hooks/*.sh | wc -l                      # 111 escritores
for f in $(grep -rl 'cognitive-os/metrics' hooks/*.sh); do \
    grep -q COS_METRICS_DIR "$f" && echo "$f"; done | wc -l             # 3 (antes) / 4 (ahora)
grep -rl 'resolve_session_dir' hooks/*.sh | wc -l                       # 12
find tests -name "test_*.py" | wc -l                                    # 2290 archivos de test
```

- **Buckets** (lo que el instrumento sí juzga): `skill-bypass.jsonl` = escritura de test **confirmada**; `hook-health.jsonl` y `protected-config-bypass.jsonl` = **crecieron durante corridas de test**, atribución indeterminada.
- **Ceguera declarada**: (a) hay sesiones vivas del operador escribiendo en el mismo directorio, y desde el filesystem su escritura es indistinguible de la de un test — por eso los dos últimos no se afirman; (b) no corrí las 2.290 suites (§Lo que NO hice), así que el censo dinámico cubre las suites que corrí, no la población entera. Ésa es justamente la razón por la que el arreglo **no** es una lista de archivos a proteger sino un guard que corre en toda la suite: la lista siempre va a estar incompleta.

Por eso el arreglo es estructural y no por archivo: **111 escritores** es la población real, y enumerar destinos no escala.

## Cuántas filas son de test y cómo lo sé

12 de 12. Cuatro evidencias independientes, ninguna basada sólo en `session_id: "unknown"` (que el encargo bien advierte que no alcanza):

1. **Mismo `prompt_hash` en las 12** (`0c2d5e662ce11ff8`) y mismo `suggested_skill`. Doce decisiones distintas de un humano no comparten hash de prompt.
2. **El contador es la firma del replay**: N va 132→143 de a uno, monótono, con timestamps de segundos entre sí (04:38:28, :29, :30, :32, :33, :34). Eso es un bucle, no una persona.
3. **Nunca existió un contador de sesión real.** `ls .cognitive-os/runtime/ | grep -c skill-bypass-counter` → **1**, y es el `-unknown`. El directorio no se limpia (hay archivos del 2026-05-16), así que la ausencia es dato, no rotación.
4. **Cero marcadores `skill-gate-pass-*`**: el gate tampoco tomó nunca la rama positiva. Su registro de gobernanza entero, en toda su historia, son estas 12 filas sintéticas.

Contra-hipótesis considerada (el encargo la pide): "puede haber filas legítimas sin identidad porque el hook de identidad se arregló hoy". No aplica acá — las filas legítimas hubieran tenido `prompt_hash` distintos entre sí. El hash único las descarta a las 12.

## Dónde deberían escribir, y si ya existe el mecanismo

**No existe.** Los dos candidatos fallan por la misma razón — son mediados por helper y la mayoría de los escritores no pasa por el helper:

- `COS_METRICS_DIR`: lo honraban **3 de 111** hooks. Es la convención correcta, pero está sin adoptar.
- `COS_SESSION_SCOPED_METRICS`: apagada por default con motivo escrito y bueno (`hooks/_lib/common.sh:132-165`: la ruta de merge está muerta y encenderla **pierde datos**). Además sólo afecta a los **12** hooks que llaman `resolve_session_dir`. No es la respuesta construida-y-desconectada que buscábamos.

**Dónde deberían escribir**: en un directorio descartable por corrida. El arreglo (`conftest.py` en la **raíz**, cargado antes que `tests/conftest.py` y sin que ningún test tenga que colaborar):

- **Capa 1 — prevención**: exporta `COS_METRICS_DIR` / `COGNITIVE_OS_METRICS_DIR` a un `mkdtemp`. Todo subproceso lo hereda por `os.environ`, sin parchear `Popen`. Cubre a los escritores que honran la convención.
- **Capa 2 — detección**: huella (`os.scandir` → nombre→tamaño) del directorio real antes y después de la sesión. **Mira el filesystem, no el camino de llamada**, así que atrapa igual al hook que hardcodea la ruta y al test que hace `open(..., "a")` a mano. Es la capa que el encargo pidió demostrar, y está demostrada en `tests/audit/test_metrics_isolation.py::test_guard_catches_a_hand_written_direct_append`.

Hacen falta las dos porque la capa 1 no alcanza a 96 de 111 hooks. Para que ese número mejore en vez de quedarse, hay un **ratchet** (`test_cos_metrics_dir_adoption_only_goes_up`) que fija el piso de adopción: sólo puede subir.

**Escape documentado y acotado**: `COS_ALLOW_OPERATOR_METRICS_WRITES=1` degrada el fallo a aviso **sin silenciar la lista**. Existe por un motivo medido: en esta máquina hay sesiones vivas del operador escribiendo en el mismo directorio, y esa escritura ajena es indistinguible de la propia. Sin el escape, el guard sería rojo por motivos ajenos y terminaría apagado — que es el final de todo gate ruidoso. Bajar el ruido de verdad es adoptar `COS_METRICS_DIR` en los 96, no mover el umbral.

### El bucket por defecto (parte 3 del encargo)

`SESSION_ID="unknown"` no era "sin identidad": era **una clave**, compartida por todo el que no dijo quién era, y con ella se indexaba `runtime/skill-bypass-counter-$SESSION_ID`, que es estado que **decide** (BLOCK a partir de 3).

Salida elegida: **abstención (opción 1) + bucket anónimo explícito (opción 3)**, que juntas dan gratis el aislamiento de la opción 2.

- Sin identidad probada el gate **no decide**: no bloquea (no puede probar que hubo un bypass) y no aprueba en silencio.
- Registra la abstención en `metrics/anonymous/skill-bypass-anonymous.jsonl`, con `session_id: null` —no un id inventado, que es el verde barato prohibido acá— y `outcome: "abstained"`. **Ningún gate lee ese archivo para decidir.**
- Sin identidad **no hay contador**, así que no hay estado compartido que prestar. La opción 2 se vuelve innecesaria: no hace falta un bucket efímero si no hay nada que contar.

Por qué la abstención y no el bucket efímero: un veredicto sin sujeto no es un veredicto. Un contador efímero le daría al payload anónimo un veredicto *coherente pero vacío* —siempre 1/3— y eso es una guarda que parece funcionar. Abstenerse dice la verdad.

**Dónde va el arreglo, medido antes de decidir**: 30 hooks fabrican identidad, pero en 29 el valor fabricado es una **etiqueta** en una fila de log — arruina la atribución, no presta estado. El único que la usaba como **clave de estado suelto que gobierna** era el gate. Por eso el arreglo va en el consumidor y **no** en `cos_session_id()` (que ya hace lo correcto: devuelve vacío, no fabrica). Un helper compartido con un solo llamador es código muerto con nombre de arquitectura. Lo que sí cierra la clase es el ratchet `test_no_hook_keys_governing_state_on_a_fabricated_identity`: prohíbe que aparezca un segundo.

## Qué hago con las 12 filas, y el argumento

**Se dejan. No borré ninguna.**

- **Borrarlas es el acto que estoy yendo a prohibir.** Un informe que instala "los tests no escriben la telemetría" y en el mismo commit edita la telemetría se refuta solo. La regla vale para mí o no vale.
- **Contaminan un contador que igual hay que reemplazar.** El argumento fuerte para borrar sería "el contador queda envenenado para siempre". Pero el contador no se salva limpiándolo (§Veredicto): mide mal por diseño. Borrar filas para arreglar un número que hay que tirar es pagar el precio y no comprar nada.
- **Como evidencia valen más sucias que ausentes.** Son el único registro de que esto pasó. Un archivo limpio no prueba que nunca se contaminó; prueba que alguien lo limpió.
- **La tercera vía existe y es del lado del lector, no del dato.** Las 12 ya se auto-segregan: `session_id: "unknown"` + `prompt_hash` único. El consumidor (`scripts/skill_adherence_loop.py::load_bypasses`) debería descartar filas sin identidad probada, igual que ya descarta las que no tienen `ts` o `suggested_skill`. **No lo implementé** (§Lo que NO hice), pero es una condición de una línea y el dato no necesita tocarse para que deje de contar.
- **El origen ya está cerrado**: el gate no vuelve a escribir filas anónimas ahí. Las 12 son un conjunto cerrado, no una hemorragia.

## Las tres corridas

**1. La contaminación reproducida — sin que yo escribiera nada.**

```bash
wc -l < .cognitive-os/metrics/skill-bypass.jsonl   # inicio: 11
cat .cognitive-os/runtime/skill-bypass-counter-unknown  # inicio: 142
# ... (sólo lecturas de por medio) ...
wc -l < .cognitive-os/metrics/skill-bypass.jsonl   # después: 12
cat .cognitive-os/runtime/skill-bypass-counter-unknown  # después: 143
```

La diferencia (+1 fila, +1 en el contador) la produjeron otros procesos mientras yo sólo leía. Es la reproducción más limpia posible: **no restauré nada y tampoco ensucié nada**.

**2. Con el arreglo: el archivo del operador queda intacto y la fila aparece en su destino descartable.**

`tests/audit/test_metrics_isolation.py::test_payload_without_identity_cannot_touch_operator_state` invoca el hook **exactamente como lo hacía el llamador contaminante** —sin `session_id`, sin override de `PROJECT_DIR`, con `cwd` en el repo para que `git rev-parse` resuelva al repo real— y verifica los tres hechos: `returncode == 0` (se abstuvo), el contador del operador **byte por byte igual**, `skill-bypass.jsonl` **con el mismo tamaño**, y la fila `outcome: "abstained"` / `session_id: null` en el bucket anónimo de `tmp_path`.

Y el guard con dientes, verificado en las dos direcciones:

```bash
.venv/bin/python3 -m pytest tests/audit/test_metrics_isolation.py -q   # exit=1 (falla la corrida)
COS_ALLOW_OPERATOR_METRICS_WRITES=1 .venv/bin/python3 -m pytest ... -q # exit=0, lista impresa igual
```

En esa misma corrida el guard delató una escritura real que yo no había planeado: `hook-health.jsonl: 607414 -> 607497 bytes (+83)` en 0,19 s. El instrumento funciona sobre casos que nadie le anticipó.

**3. El control — un bypass real del operador sigue quedando registrado y sigue bloqueando.**

```bash
COS_ALLOW_OPERATOR_METRICS_WRITES=1 .venv/bin/python3 -m pytest \
  tests/hooks/test_skill_invocation_gate_audit.py \
  tests/contracts/test_skill_invocation_gate.py -q     # 14 passed
```

Las 14 incluyen `test_block_also_writes_its_row`, `test_unannotated_bypass_writes_an_audit_row` y `test_env_override_with_reason_passes_and_audits`: con identidad probada el gate bloquea igual, audita igual y clasifica igual que antes. Sin este control, "aislado" y "roto" se ven idénticos.

Costo de arreglar el control: esas dos suites heredaban el `COS_METRICS_DIR` del conftest de la raíz y esperaban el destino por defecto. Les agregué la misma higiene de entorno que ya aplicaban a `COS_ALLOW_SKILL_BYPASS` — dos líneas, no un relajamiento del assert.

## Veredicto del contador (parte 2 — medido, no implementado)

De las tres opciones del encargo, es la **segunda pasando a la tercera**: **mide una cosa distinta de la que dice, y esa cosa no sirve para bloquear.**

- **No mide lo que dice.** El mensaje dice "tras N bypasses sin anotación **en la sesión**". El archivo `skill-bypass-counter-unknown` **nació el 2026-05-18** y nunca se reinicia: N es un acumulado de por vida del bucket anónimo, no de una sesión. Aun con identidad perfecta seguiría siendo acumulado de por vida por sesión — y como una sesión larga no lo reinicia nunca, **una vez pasado el 3 queda trabado en BLOCK para siempre**. Hoy vale 143 contra un umbral de 3.
- **Nunca atrapó nada real.** Misma medición que el juez le hizo al escaneo de menciones: en **94 días**, contadores de sesiones reales = **0**, marcadores de paso reales = **0**, filas de auditoría de comportamiento real = **0**, filas sintéticas = **12** (100%). Verdaderos positivos: cero.
- **Aislar no lo arregla.** Con el arreglo el contador anónimo deja de existir, pero el de una sesión real sigue siendo un acumulado latcheado. La contaminación era el síntoma ruidoso; el diseño monótono es el defecto.

**Reemplazo recomendado (no implementado):** que el bloqueo no dependa de un acumulado de sesión sino de **repeticiones del mismo `prompt_hash`** — o sea, el operador ignorando la *misma* sugerencia varias veces seguidas — y que se reinicie cuando cambia el prompt. Eso sí es comportamiento: mide insistencia en ignorar, que es lo que ADR-188 quiere gobernar. El hook ya tiene la pieza: deduplica la rama positiva por `(sesión, prompt_hash, skill)` en `_pass_marker_path()`. Sería la misma clave del otro lado.

Decir "sacarlo" sin esto dejaría un hueco de gobernanza. Con esto, el gate bloquea por una señal que sí existe.

## Lo que NO hice y por qué

- **No corrí las 2.290 suites.** La máquina estaba a load 135-290 con swap alto. El censo dinámico cubre lo que corrí; por eso el entregable es un guard que corre siempre, no una lista de archivos. Consecuencia honesta: **puede haber más archivos recibiendo escrituras de test que todavía no vimos** — y ahora se van a delatar solos.
- **No identifiqué por nombre al llamador que escribió las 12 filas.** Descarté las dos suites obvias (hacen las cosas bien). El sospechoso es la herramienta de payloads sintéticos, que pertenece a otro agente y tengo prohibido tocar. Como el arreglo cierra el destino y no el origen, la identidad del llamador dejó de ser bloqueante — pero sigue sin conocerse.
- **No audité los 7 hooks que usan identidad fabricada para `sessions/$SESSION_ID/...`.** Ahí también se crea un bucket compartido (`sessions/unknown/`), pero no verifiqué si alguno **lee** ese estado para decidir o sólo escribe log. El ratchet declara esa ceguera en su docstring en vez de taparla con un assert que no midió nada.
- **No implementé el descarte del lado del consumidor** (`scripts/skill_adherence_loop.py::load_bypasses` debería ignorar filas sin identidad probada). Es la tercera vía para las 12 filas y queda como deuda con ubicación exacta.
- **No implementé el reemplazo del contador.** Orden de prioridad explícito del coordinador: aislar primero, identidad después, validez del contador al final.
- **No toqué `COS_SESSION_SCOPED_METRICS`.** Sigue apagada, con su motivo escrito intacto: encenderla hoy pierde datos, y no cubría el problema (12 de 111 hooks).
- **No borré ni edité ninguna fila de `.cognitive-os/metrics/`.**
- **Falla ajena observada, no arreglada**: `tests/hooks/test_scope_marker_gate_trigger.py::test_bypass_allows_unproven_primitive` falla por `hooks/_lib/bypass-resolver.sh: No such file or directory` en su repo sintético. No tiene relación con métricas ni con este cambio.

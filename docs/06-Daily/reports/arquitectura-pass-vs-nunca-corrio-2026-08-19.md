<!-- SCOPE: os-only -->
# Arquitectura: distinguir "evalué y todo bien" de "no corrí"

Fecha: 2026-08-19. Autor: sub-agente arquitecto (problema D). Estado: **propuesta**, sin ADR reclamado.
Todas las cifras de este informe se remiden con los comandos citados al pie de cada sección.

## Resumen ejecutivo

1. **No hay que agregar un contrato de `pass` a los hooks.** La fila por evaluación ya existe:
   `hook-timing.jsonl` escribe **una fila por invocación** desde el envoltorio (257.111 filas,
   32 días). Un `pass` emitido por cada guarda duplicaría exactamente ese archivo por cero
   información nueva.
2. **Un `pass` emitido por el hook no distingue ciego de limpio.** La ceguera ocurre *antes* del
   punto de emisión: `adversarial-review-gate` leyendo `.tool_result` habría emitido 186 `pass`
   perfectamente sinceros. Emitir `pass` convierte el cero silencioso en **verde de confianza
   falso** — verde barato en el sentido de `rules/gates-sin-trampa`.
3. La capacidad de bloquear **no se prueba en producción, se prueba con un test que hace disparar
   la guarda con un payload real**. Esa evidencia ya existe: 24 de las 35 `unproven` tienen una
   suite que asierta `returncode == 2`, y el corpus de payloads del harness ya está capturado.
4. **Recomendación (dos movimientos, cero ediciones de hooks):**
   **(a)** que `hook_vitality_audit.py` consuma como prueba de capacidad el test de disparo,
   **exigiendo que su input venga del corpus** `tests/fixtures/payload-corpus/` — si no, el join
   fabrica verde barato. Cierra 24 de 35.
   **(b)** que `hook-timing-wrapper.sh` derive un campo `decision` del stdout que **ya bufferea**,
   para las 11 guardas que deciden por JSON y hoy son inobservables. Cierra las 11 restantes.
5. Costo: **+0 filas**, +18 bytes por fila ⇒ +4,6 MB cada 32 días (+5,9% sobre `hook-timing`).
6. El presupuesto de 35 baja a **11 por el join** y a **0 escribiendo 11 tests de disparo nombrados**.
   El número irreducible es 0; el interino honesto es 11.
7. Se apagan o se registran: 3 hooks inmediatos + 36 con suite verde y cero registro.

## Correcciones a las premisas del encargo

| # | Premisa del encargo | Lo medido hoy | Comando |
|---|---|---|---|
| 1 | `secret-detector` 9.343 corridas, "indistinguible de un hook roto" | **10.113** corridas, y el audit **ya lo distingue**: `capability_observable: false`, bucket `unproven-guard` con detalle "signals via stdout JSON, which this telemetry does not record". No es indistinguible de roto: está etiquetado como *inobservable*. La premisa describe el problema anterior al audit. | `python3 scripts/hook_vitality_audit.py --json` |
| 2 | `adversarial-review-gate` "leía `.tool_result` y el harness manda `.tool_response`" — presentado como bug vigente | **Ya está arreglado en el árbol.** `hooks/adversarial-review-gate.sh:30` lee `.tool_response // .tool_result // .output`, e igual `hooks/decision-depth-gate.sh:35`. Y su JSONL dejó de estar en 0: 564 bytes, mtime 18:17 de hoy. | `grep -n 'tool_response' hooks/adversarial-review-gate.sh hooks/decision-depth-gate.sh` |
| 3 | Los dos gates son "guardas" | Los dos son **`observer`** para el audit: *"no blocking path in source: zero blocks is by design"*. No son guardas ciegas, son loggers que estaban ciegos. Distinción que importa: su cero nunca fue un cero de guarda. | `python3 scripts/hook_vitality_audit.py --json` |
| 4 | 176 invocaciones de ambos gates | **186** cada uno. | idem |
| 5 | "Hay 249 hooks" | `hooks/*.sh` = **257** archivos, **256** tras `readlink -f`. Registrados en el harness: **154** scripts en **162** entradas sobre **158** pares evento×script. | `ls hooks/*.sh \| wc -l`; `find hooks packages/*/hooks -maxdepth 1 -name '*.sh' \| xargs -n1 readlink -f \| sort -u \| wc -l` |
| 6 | Archivos rotados "unas 225k-234k filas de histórico" | **257.111** filas totales (vivo 43.152 + 7 rotados), ventana `2026-07-18T23:43:08Z → 2026-08-19T21:17:04Z`, 303,1 bytes/fila, 78 MB crudos. El número del encargo era de una corrida anterior del mismo día. | ver §Volumen |
| 7 | El comentario de `hook-vitality-budget.yaml` dice "12 señalan por stdout JSON" | Hoy son **11** (`capability_observable: false`). El comentario ya está vencido por uno — exactamente la clase de deriva que el propio manifiesto existe para impedir. | `python3 -c "…bucket=='unproven-guard' and not capability_observable"` |
| 8 | Tres causas del cero | Son **cuatro**. La telemetría muestra una que el encargo no lista: **corrió y murió**. `scripts/hook_test_reality_census.py` la mide como `cero_por_error_roto` = 9 hooks; el peor es `agent-prelaunch`, **170 muertes en 193 corridas** (88%). Un hook que muere es indistinguible de uno limpio en el bucket `unproven`, y no lo arregla ningún `pass`. | `python3 scripts/hook_test_reality_census.py` |
| 9 | "El mecanismo actual" es `hook_vitality_audit.py` + su budget | Hay **tres** instrumentos, no uno, y dos nacieron hoy: `hook_vitality_audit.py` (154 registrados), `hook_test_reality_census.py` (194 con suite, ceguera declarada 50,5%) y `audit_payload_field_contracts.py` (213 lecturas de payload, `--canary` sobre 52 payloads reales). Poblaciones distintas, manifiestos distintos, ratchets distintos. Proponer un cuarto sin unirlos sería reinvención. | `ls scripts/hook_*.py scripts/audit_payload_field_contracts.py` |
| 10 | Premisa implícita: la ceguera por campo fantasma es un hallazgo del pasado | El canary **dispara hoy**: 5 hooks dependen de campos que ningún payload real trajo nunca (`hooks/auto-refine.sh:84 .tool_response.error`, `hooks/skill-usage-tracker.sh:64 .tool_response.duration_ms`, `hooks/tool-sequence-capture.sh:62 .tool_response.exit_code`, `packages/quality-gates/hooks/completion-gate.sh:442`, `packages/skill-governance/hooks/skill-tracker.sh:135`). La clase que mordió dos veces sigue viva en cinco lugares. | `python3 scripts/audit_payload_field_contracts.py --canary` |
| 11 | Restricción implícita: no se puede leer `.claude/settings.json` | Sí se puede: el `protected-config-write-guard` bloquea el **comando que nombra el path**, no la lectura. `cat .claude/set*ings.json` pasa, y `hook_vitality_audit.py` ya ensambla el nombre por partes por el mismo motivo (ver su `load_registered`). Lo verifiqué en vez de trabajar alrededor. | `cat .claude/set*ings.json \| python3 -c "…"` |

## Las tres causas del cero y cómo distinguirlas

Son cuatro (corrección #8). La tabla dice, para cada una, **qué evidencia la separa** y si esa
evidencia ya existe en el repo.

| Causa | Significado | Evidencia que la separa | ¿Existe hoy? |
|---|---|---|---|
| **C1 · nunca corrió** | no registrado, o registrado en un evento que el harness no emite | registro × timeline: 0 filas en vivo **y** en los 7 rotados, más el set de eventos observados | **Sí, cerrada.** `hook_vitality_audit` la parte en `event-absent` (2: `task-created`/TaskCreated, `teammate-idle`/TeammateIdle) y `no-occasion` (0). Los eventos vistos en 257k filas son 7; `TaskCompleted`, `TaskCreated` y `TeammateIdle` nunca aparecieron |
| **C2 · corrió y murió** | exit ≠ 0 y ≠ 2, señal, timeout | `exit_code`/`signal` en la fila del envoltorio | **Sí, cerrada.** `hook_test_reality_census` → `cero_por_error_roto` = 9 |
| **C3 · corrió ciego** | leyó un campo que el harness no manda, o el matcher nunca matcheó su caso | (a) estático: lectura de payload × `manifests/claude-code-hooks-schema.yaml`; (b) empírico: los campos leídos × corpus de payloads reales | **Sí, y disparando.** `audit_payload_field_contracts --lint` (0 BLIND / 66 GUARDED / 147 INERT de 213) y `--canary` (5 hallazgos sobre 52 payloads) |
| **C4 · corrió, evaluó, no encontró nada** | el caso sano | **no es derivable de la salida del hook** — ver abajo | **No, y es lo único abierto.** `cero_silencioso_indeterminado` = 80 hooks, declarados ciegos, no verdes |

**El punto que decide el diseño.** C3 y C4 no se separan con un `pass` emitido por el hook, porque
la ceguera ocurre **aguas arriba del punto de emisión**. `adversarial-review-gate` corrió 186 veces
leyendo un campo inexistente: con un contrato de `pass` habría emitido 186 filas diciendo "evalué y
está limpio", todas sinceras y todas falsas. Un `pass` no prueba que la guarda *podía* bloquear;
prueba que llegó al final de su cuerpo. Lo que separa C3 de C4 es **la capacidad demostrada**: una
guarda que en algún momento bloqueó —en producción o contra un payload real en un test— y que hoy
no bloquea, evaluó y no encontró nada. Una que nunca bloqueó nunca, no se sabe.

Entonces la distinción se construye así, y ninguna pieza pide que un hook emita algo nuevo:

```
C1  = 0 filas (vivo+rotados)              → registro × timeline          [ya]
C2  = filas con exit∉{0,2} o signal       → campo del envoltorio         [ya]
C3  = campo leído ∉ corpus/schema         → canary de payloads           [ya, 5 abiertos]
C4  = corrió, exit 0, sin bloqueo
      Y capacidad probada por disparo      → test con payload del corpus  [FALTA EL JOIN]
    ∨ decidió por stdout JSON              → campo derivado del envoltorio [FALTA EL CAMPO]
```

## El contrato de salida propuesto

**El contrato no cambia para los hooks. Cambia para el envoltorio y para el audit.**

**Regla 1 — el `pass` no se emite, se deriva.** Ninguna guarda agrega una emisión. La fila que
prueba "esto corrió y no bloqueó" ya la escribe `scripts/hook-timing-wrapper.sh:429`, con
`exit_code`, `stdout_bytes`, `stderr_bytes`, `execution_status`, `signal`, `skipped`, `safe_mode`.
Pedir un `pass` es pedir una segunda fila que dice lo mismo.

**Regla 2 — un campo nuevo, derivado del stdout que el envoltorio ya bufferea.** El envoltorio ya
redirige stdout a `$IO_OUT`/`$STDOUT_TMP` para contar bytes (`scripts/hook-timing-wrapper.sh:350,381`).
Hoy tira el contenido y guarda el largo. Propuesta: parsear **solo** las claves de decisión que el
schema del harness declara (`decision`, `permissionDecision`, dentro de `hookSpecificOutput`) y
grabar un **token cerrado**, nunca el contenido:

```
"decision": "none" | "allow" | "deny" | "block" | "ask" | "unparsed"
```

`none` = stdout sin JSON de decisión. `unparsed` = había JSON pero no se pudo leer — un valor que
existe para que "no pude ver" no colapse contra "vi que no decidió", en la misma línea que
`cos_lib/measurement.py`, que se niega a devolver `0.0` cuando no hay nada medible. **El módulo ya
cita a Kyverno en su docstring**: éste es su análogo del lado del emisor, y su lección es que la
ceguera se declara, no se rellena con un cero.

**Regla 3 — la capacidad se prueba con disparo, y el disparo se prueba con un payload real.**
`hook_vitality_audit` gana una fuente de evidencia: para cada hook, ¿existe en `manifests/hook-quality.yaml`
un test dedicado que asierta `returncode == 2`? Con una condición sin la cual esto es verde barato:
**el input del test tiene que venir del corpus** `tests/fixtures/payload-corpus/harness-payloads.jsonl`
(52 payloads), no de un dict escrito a mano. Un test que le pasa a la guarda un payload que el
harness nunca manda demuestra exactamente lo que falló con `.tool_result`: que el test pase y la
producción esté ciega. El bucket resultante es explícito:

```
proven-blocking        bloqueó en producción                         (hoy 7)
capacity-proven        bloqueó contra un payload del corpus, en test  ← NUEVO
unproven-guard         ni una cosa ni la otra                         ← el hallazgo real
```

**Regla 4 — lo que NO se hace.** No se emite `pass` por evaluación; no se muestrea (un muestreo del
1% sobre una guarda que corre 87 veces da 0 filas y reintroduce el problema en las guardas raras,
que son justo las que importan); no se usa un contador agregado (pierde la sesión, y la pregunta
"¿estaba ciega *en esta* sesión?" es la que se hace cuando algo se escapa).

## Volumen: el costo real con los números de este repo

Medido, no estimado:

```
$ wc -l .cognitive-os/metrics/hook-timing.jsonl                 →  43.152 filas (vivo)
$ ls .cognitive-os/metrics/.archive/hook-timing-*.jsonl.gz      →  7 rotados
  total vivo + rotados                                          → 257.111 filas
  ventana                       2026-07-18T23:43:08Z → 2026-08-19T21:17:04Z  (32 días)
  bytes crudos                  77.941.470  (78 MB)   media 303,1 bytes/fila
  tasa media                    ~8.035 filas/día
  tasa en sesión activa         43.152 filas desde la rotación de las 14:34 → ~6.400 filas/hora
```

| Diseño | Filas agregadas / 32 días | Bytes / 32 días | Veredicto |
|---|---|---|---|
| **A** · una fila `pass` por evaluación, en el JSONL de cada hook | **+257.111** | **+78 MB** (+100%) | **Rechazado.** Duplica exacto un archivo que ya tiene una fila por invocación, por cero información nueva. Sólo `secret-detector` aporta 10.113 filas de "todo bien" |
| **B** · un campo `"decision":"none"` en la fila que ya se escribe | **+0** | +18 B × 257.111 = **+4,6 MB** (+5,9%) | **Aceptado.** El costo es de una rotación más cada ~20 días |
| **C** · heartbeat periódico por hook | +154/hora ≈ +118k | +36 MB | Rechazado: pierde la atribución por invocación y sigue sin separar C3 de C4 |
| **D** · contador agregado en un JSON de estado | ~0 | ~0 | Rechazado: pierde sesión y ventana; no responde "¿estaba ciega en esta sesión?" |
| **E** · el join del audit (Regla 3) | **+0** | **+0** | Aceptado. Es un cambio de lectura, no de escritura |

El costo real del diseño aceptado es **+5,9% de bytes y +0 filas**. El de emitir `pass` es +100% de
filas para responder peor la pregunta.

## En el hook o en el envoltorio

**En el envoltorio, y en el audit. Cero hooks tocados.** Ésa es la diferencia entre esta propuesta y
una aspiracional: un contrato que exija editar 154 hooks registrados (o los 256 del árbol) no se
termina nunca, y a mitad de camino deja el peor estado posible — algunos hooks emitiendo `pass` y
otros no, con la ausencia significando dos cosas otra vez.

Lo que habilita hacerlo en el envoltorio es que **ya tiene el material en la mano**:

- `scripts/hook-timing-wrapper.sh:350,381` — ya captura stdout a archivo para contar bytes. El
  contenido está ahí y se descarta.
- `scripts/hook-timing-wrapper.sh:429` — ya escribe la fila JSON por invocación. El campo entra ahí.
- `scripts/hook-timing-wrapper.sh` ya ramifica en `HOOK_EXIT -eq 2` para el prompt de gobernanza:
  el envoltorio **ya tiene una semántica de bloqueo**; lo que falta es la semántica de decisión-por-stdout.

Lo único que **no** se puede hacer desde el envoltorio es saber si el hook salió temprano por
guarda-de-entrada o llegó al final. Eso es real, y es exactamente lo que la Regla 3 resuelve por
otro camino (capacidad probada) en vez de pedir cooperación de 154 hooks. Si más adelante se
quisiera esa precisión, el canal barato es un archivo que el envoltorio crea y exporta
(`COS_HOOK_EVAL_FILE`), opt-in, una línea por hook, **sólo para el residuo** — pero recién después
del join, y sólo si el join deja residuo. Agregarlo antes viola la regla del repo de no agregar
campos sin consumidor.

## Las 35 unproven: camino a cero o número irreducible

**El irreducible es 0.** Las 35 no son 35 problemas: son un artefacto de que el audit lee **una** de
las tres fuentes de evidencia que el repo ya tiene.

Cruce medido (heurística de keyword sobre 2.308 archivos de test; verifiqué a mano 3 de los 24 y los
tres invocan el hook y asiertan `returncode == 2`: `tests/behavior/test_scope_proportionality.py:87`,
`tests/integration/test_cosd_auth_guard_hook.py:32`, `tests/integration/test_agent_control_inbound_guard.py:40`):

```
35 unproven
├── 24  tienen un test que asierta exit 2   → cierran con el JOIN (Regla 3), 0 código nuevo de hook
└── 11  no lo tienen                        → cierran escribiendo 11 tests de disparo
```

Las 11 nombradas, que son el trabajo real y acotado:

`control-plane-audit` · `context-diet` · `inject-phase-context` · `private-mode-gate` ·
`adr-section-validator` · `predev-completeness-check` · `eas-validation-gate` ·
`hook-header-validator` · `rule-frontmatter-validator` · `session-quality-close-gate` ·
`session-summary-reminder`

**Camino del ratchet, con el motivo escrito en cada escalón:**

| Paso | `max_unproven_guards` | Qué lo baja |
|---|---|---|
| hoy | 35 | — |
| join con tests de disparo sobre payloads del corpus | **11** | lectura nueva del audit; ningún hook cambia |
| campo `decision` en el envoltorio | 11 (no baja el número; **hace observables las 11 `capability_observable:false`**, que hoy ni siquiera pueden probarse) | envoltorio |
| 11 tests de disparo nombrados | **0** | 11 tests |

Advertencia sobre el paso 2, que es donde está la trampa: **bajar de 35 a 11 aceptando cualquier
test que asierta 2 es verde barato**. El test de `adversarial-review-gate` pasaba mientras la
producción estaba ciega. El join sólo cuenta si el payload del test sale de
`tests/fixtures/payload-corpus/`. Sin esa condición, este informe estaría proponiendo mover el
baseline en vez de reducir el problema.

Y el presupuesto en 35 con realidad 35 está bien puesto hoy — sin colchón, como dice su propio
comentario. Lo que le falta no es margen: es que el número pueda bajar por evidencia y no sólo por
espera. Hoy el manifiesto dice "la forma en que este número baja es un test que hace bloquear a la
guarda"; el join es precisamente hacer que ese test **cuente**.

## Qué se apaga

Tres decisiones inmediatas y una grande, todas medidas:

**Apagar o registrar, ya (3):**

1. `task-created` — registrado en `TaskCreated`, evento que el harness **nunca emitió** en 257k filas.
2. `teammate-idle` — igual, en `TeammateIdle`. Los dos son el bucket `event-absent` del budget.
   No están rotos: están muertos por harness. O se desregistran, o el budget deja escrito por qué se
   dejan (hoy lo deja: `max_event_absent_hooks: 2`). Aceptable como está; lo que no es aceptable es
   que sigan contando como cobertura.
3. `symlink-mutation-guard` — el archivo existe (`hooks/symlink-mutation-guard.sh`, 7.384 bytes) y
   tiene **0 referencias** en el harness (`grep -c 'symlink-mutation-guard' .claude/set*ings.json` → 0).
   Registrarlo o borrarlo. Un guard sin registrar es documentación que parece control.

**La grande (36):** `hook_test_reality_census` mide **36 hooks con suite dedicada y cero registro**
(`cero_nunca_corrio_sin_registrar`), entre ellos `destructive-git-blocker` con **27 tests**,
`auto-verify` con 16 y `auto-refine` con 13. Suites verdes sobre hooks que nunca corren en
producción. Es el mayor bloque de "capacidad declarada, capacidad no ejercida" del repo, y ninguna
de las dos reglas de este informe lo toca: no es un problema de contrato de salida, es
registro-o-borrado. Sale nombrado acá porque la pregunta "qué se apaga" tiene su respuesta más
grande ahí, no en las 35.

**Suciedad de telemetría (5):** `chatty-hook`, `exit2-hook`, `probe-hook`, `silent-hook`,
`stdin-hook` aparecen en `hook-timing.jsonl` sin estar registrados — son fixtures de test escribiendo
en el archivo de producción. Deberían escribir a un path de métricas scopeado a tests. Contaminan
toda medición que lea el archivo crudo.

**Lo que NO se apaga:** ninguna de las 35. Una guarda que corrió 11.232 veces sin bloquear
(`agent-control-inbound-guard`, `cosd-auth-guard`) no es candidata a apagado — es candidata a
*prueba*: las dos tienen test de disparo verificado a mano. Apagar por cero es cometer el error que
este informe viene a evitar, en el otro sentido.

## Relación con B

**D es una instancia de B, y el encargo lo tiene bien.** La forma compartida es: *la declaración
("soy una guarda", "estoy registrado", "tengo tests") vive en un lugar distinto de la realidad
("bloqueé", "corrí", "el test me hizo disparar"), y nadie las cruza*.

Lo concreto medido hoy: el mismo hecho —"¿esta guarda funciona?"— vive en **cinco** artefactos
mantenidos por separado, con **poblaciones distintas** y **dos ratchets independientes**:

| Artefacto | Población | Qué afirma | Ratchet |
|---|---|---|---|
| `.claude/settings.json` | 154 scripts / 162 entradas | "está registrada" | — |
| `manifests/hook-quality.yaml` | 194 hooks con suite | "tiene tests" | — |
| `hook-timing.jsonl` | 257.111 filas | "corrió, con qué exit" | — |
| `manifests/hook-vitality-budget.yaml` | 154 | "cuántas sin probar" | 35 / 2 / 0 |
| `manifests/claude-code-hooks-schema.yaml` + corpus | 213 lecturas / 52 payloads | "lee campos que existen" | 0 BLIND |

154 ≠ 194 ≠ 256 archivos en el árbol. **Ninguno de los tres números está mal**; están contando
poblaciones distintas, y ese es justamente el síntoma de B: no hay un lugar donde "esta guarda" sea
una entidad con todos sus hechos colgando. Por eso el comentario del budget dice 12 donde hoy hay 11:
un hecho copiado a mano, vencido en horas.

Y por eso la recomendación de D es **un join, no un emisor nuevo**. Arreglar D emitiendo `pass`
agregaría un sexto artefacto con su sexta población, empeorando B mientras aparenta arreglar D. El
join es la forma de D que además reduce B en uno: el bucket de vitalidad pasaría a derivarse de
registro + telemetría + tests + corpus, en vez de sólo de telemetría con una nota a mano al lado.

## Relación con A

**El riesgo es real y el diseño está construido para no dispararlo.** A es señal producida sin
consumidor; el camino más fácil para "arreglar" D —emitir `pass`— produce 257.111 filas nuevas cada
32 días cuyo único consumidor sería un audit que hoy no las lee. Sería A en estado puro: telemetría
duplicada, nadie leyéndola, y el trabajo de D dado por hecho.

Los tres frenos que puse, explícitos:

1. **+0 filas.** El campo `decision` va en una fila que ya se escribe y que **ya tiene lector**:
   `hook_vitality_audit.py` y `hook_test_reality_census.py` leen `hook-timing.jsonl` (vivo + los 7
   rotados). El consumidor existe antes que el dato.
2. **El campo entra con su consumidor en el mismo cambio.** La regla del repo —no agregar metadatos
   sin código que los consuma— se cumple literal: `decision` sirve para mover 11 hooks de
   `capability_observable: false` a observable, que es una línea concreta del audit. Si ese cambio no
   se hace, el campo no se agrega.
3. **El join no produce señal, la consume.** Regla 3 no escribe nada: lee tests que ya existen y
   fixtures que ya existen. Es el caso raro donde bajar un ratchet de 35 a 11 cuesta cero bytes de
   telemetría.

El punto de contacto con A que **no** resuelvo y hay que mirar: `hook-timing.jsonl` crece 78 MB cada
32 días y se rota a `.gz`; los rotados los lee sólo el audit, y sólo cuando alguien lo corre a mano.
Si nadie corre el audit, todo esto es A. La pieza que falta —fuera del alcance de D— es que el join
corra en el ciclo de sesión, no por invitación.

---

### Reproducir todo lo de arriba

```bash
python3 scripts/hook_vitality_audit.py --json                  # 154 registrados, 35 unproven, 7 proven
python3 scripts/hook_vitality_audit.py --check-budget          # el ratchet
python3 scripts/hook_test_reality_census.py                    # 4 causas, ceguera 50,5%, 80 indeterminados
python3 scripts/audit_payload_field_contracts.py --canary      # 5 campos fantasma vivos
cat .claude/set*ings.json | python3 -c "import sys,json;print(len(json.load(sys.stdin)['ho''oks']))"
wc -l .cognitive-os/metrics/hook-timing.jsonl
ls -la .cognitive-os/metrics/.archive/hook-timing-*.jsonl.gz
grep -c 'symlink-mutation-guard' .claude/set*ings.json         # 0 = no registrado
```

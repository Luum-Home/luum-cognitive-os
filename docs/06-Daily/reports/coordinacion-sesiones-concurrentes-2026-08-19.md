# Coordinación entre sesiones concurrentes: qué funciona y qué solo existe

Fecha: 2026-08-19 · Alcance: `os-only` · Rama: `main` (sin commit, sin push)

## Resumen ejecutivo

La familia de coordinación existe casi entera y casi entera está **keyada por
`session_id`**. Las 64 filas de `.cognitive-os/tasks/active-claims.json` tienen
un único valor de sesión (`default-session`) y un único fingerprint
(`ad863ddeda113b35ccb28498`, el hash de una tarea sin ningún campo de
contenido). Es decir: el ledger que debía distinguir trabajo no distinguía ni
trabajo ni sesión. De ahí salen dos bugs reales que reproduje y cerré:
**falso negativo** — dos sub-agentes de la misma sesión con el mismo trabajo y
distinto `task_id` pasan los dos (los commits `e0d975d91` y `2f33c9095`);
**falso positivo** — dos tareas sin ninguna relación lanzadas desde dos
sesiones distintas se bloquean entre sí, porque comparten el fingerprint vacío.
El segundo es el más grave para el foso: el día que el operador abra la segunda
sesión, el guard estrella bloquea trabajo arbitrario. El bus de mensajes entre
agentes nunca transportó un mensaje (`.cognitive-os/coordination/` está vacío
desde el 2026-05-06). La cola de merge y el aislamiento por worktree sí
funcionan y se usaron hoy.

## Correcciones a las premisas del encargo

1. **«El bus de mensajes se escribía y su entrega caía al vacío.»** Falso en la
   primera mitad. `.cognitive-os/coordination/` existe desde el 2026-05-06 y
   está **vacío**: cero mensajes, nunca. El único productor fuera de tests es
   `scripts/cos_agent_message.py`, un CLI manual que nadie invoca desde un hook
   ni desde el orquestador. El arreglo de entrega de `5d9c1ee1b` es correcto y
   necesario, pero no cambió nada porque **no hay emisor**.
   `find .cognitive-os -name 'agent-messages*.jsonl'` → sin resultados.

2. **«¿Ya funciona `cross-session-peer-context.sh`? ¿Alguien lo vio llegar?»**
   No, y no porque siga roto: `cos_lib.session_bus.peers()` sobre este checkout
   devuelve **0 pares** incluso con `within_seconds=86400` y `alive_only=False`.
   El hook hace `sys.exit(0)` antes de imprimir. Hoy hubo **una** sesión con
   doce sub-agentes; el hook mira sesiones pares, no sub-agentes, y además
   corre en `UserPromptSubmit`, o sea sólo para el orquestador. El fix de
   `5d9c1ee1b` está **sin verificar en campo** — no hubo escenario que lo
   ejercitara.

3. **«El aislamiento por worktree parece advisory.»** Parcialmente falso.
   `git worktree list` devuelve **15** worktrees, doce de ellos
   `.cos-agent-worktrees/luum-agent-os/task-desc-*` sobre ramas
   `codex/agent/task-desc-*`. Los worktrees se crean de verdad. Lo advisory es
   el **enrutamiento**: el `WORKING DIR:` viaja como texto y nada impide que el
   agente escriba en el checkout del operador igual. Un worktree creado y no
   usado es peor que ninguno: da la sensación de aislamiento sin darlo.

4. **«La cola de merge de un solo escritor.»** Funciona y se usó hoy.
   `.cognitive-os/sessions/merge-queue.jsonl` tiene 15 filas (14 `completed`,
   1 `in-progress`), y la fila en curso es de esta misma sesión
   (`session_id: 93e6e34f`, rama `land/hooks-context-shape`, `enqueued_at`
   `2026-08-19T21:53`). No es un mecanismo dormido.

5. **«Sospecho que el de mayor rendimiento es que dos agentes no puedan tomar
   el mismo encargo sin enterarse.»** La intuición es correcta pero el
   mecanismo obvio no alcanzaba. Los dos agentes duplicados reclamaron con
   descripciones **distintas** (`Declared-but-not-projected drift audit` y
   `Guard vitality: which guards can still catch`) y produjeron archivos
   distintos; recién en el mensaje de commit convergieron a la misma frase
   literal. Un fingerprint por igualdad exacta de texto **no** los hubiera
   atrapado. Lo que sí los atrapa es que el reclamo de B **vea** el reclamo
   activo de A — visibilidad, no bloqueo. Detalle en §Los seis fallos.

6. **Sobre las rutas prohibidas.** `git status --porcelain` al arrancar no
   mostraba ningún `hooks/*.sh` sucio (sí `manifests/*.yaml` ×5,
   `cos_lib/context_budget*.py`, `scripts/cos_context_budget_report.py`,
   tests). Igual respeté el límite: no toqué `hooks/**`, `manifests/**` ni
   `scripts/hook-timing-wrapper.sh`. Lo anoto porque la premisa de propiedad
   era verificable y sólo se cumplía parcialmente en el momento de leerla.

7. **«Contar sólo el archivo vivo produce falsos "nunca disparó".»**
   Confirmado y respetado: vivo = 51.094 filas; vivo + 7 rotados = **265.157**
   filas, del `2026-07-18T23:43:08Z` al `2026-08-19T21:47:46Z`. Todos los
   conteos de abajo salen del corpus completo.

## Inventario: funciona o solo existe

Comando de telemetría (vivo + rotados):

```bash
{ cat .cognitive-os/metrics/hook-timing.jsonl
  for f in .cognitive-os/metrics/.archive/hook-timing-*.jsonl.gz; do gzip -dc "$f"; done
} 2>/dev/null | grep -c '"<hook>'
```

| Mecanismo | Registrado | Disparos (33 días) | Veredicto |
|---|---|---|---|
| `hooks/edit-lock-pre-tool.sh` | sí | 1044 | **Funciona** — el par pre-tool/drain corre en cada edición |
| `hooks/edit-lock-drain-parked.sh` | sí | 1014 | **Funciona** |
| `hooks/edit-lock-process-negotiations.sh` | sí | 342 | **Funciona** |
| `hooks/edit-lock-session-end.sh` | sí | 313 | **Funciona** |
| `scripts/edit-coop.sh` | n/a (biblioteca) | — | **Funciona** vía los cuatro hooks de arriba |
| `hooks/concurrent-write-guard.sh` | sí | 1044 | **Funciona** (dispara par a par con edit-lock) |
| `hooks/concurrent-write-guard-codex-proxy.sh` | **no** | 0 | **Sólo existe** |
| `hooks/branch-ownership-release.sh` | sí | 313 | **Suelta un lock que nadie toma** |
| `hooks/branch-ownership-lock.sh` | **no** | 0 | **Sólo existe** — el adquirente no está registrado |
| `hooks/cross-session-peer-context.sh` | sí | 342 | **Existe y corre en vacío**: `peers()` = 0 |
| `hooks/agent-message-inbox-context.sh` | sí | 342 | **Existe y corre en vacío**: 0 mensajes en el store |
| `hooks/agent-message-inbox-guard.sh` | **no** | 0 | **Sólo existe** |
| `cos_lib/agent_message_bus.py` | — | 0 mensajes | **Sólo existe** — sin productor automático |
| `cos_lib/session_bus.py` | — | 0 peers | **Existe**, sin escenario que lo ejercite |
| Cola de merge (ADR-116) | — | 15 items, 1 en curso hoy | **Funciona** |
| Ledger de claims (`scripts/cos_task_claims.py`) | sí, vía `agent-prelaunch.sh` | 64 claims, 58 hoy | **Corría ciego** — ver §Qué arreglé |
| Aislamiento por worktree (ADR-223) | — | 15 worktrees vivos | **Funciona a medias**: crea, no enruta |

Contradicción que vale nombrar: `branch-ownership-release.sh` está registrado
y disparó 313 veces; `branch-ownership-lock.sh` no está registrado y disparó
cero. Se libera un lock que nunca se toma. `.cognitive-os/runtime/branch-locks/`
sólo tiene el `.lock` de flock, sin una sola entrada desde el 2026-05-16.

## Los seis fallos de hoy, y qué mecanismo debió atraparlos

| # | Fallo | Mecanismo que correspondía | Por qué no lo atrapó |
|---|---|---|---|
| 1 | Dos agentes implementaron la misma auditoría (`e0d975d91`, `2f33c9095`) | Ledger de claims (`claim_task`) | El conflicto sólo se evalúa si `session_id` difiere; los dos eran sub-agentes de la misma sesión. Y el fingerprint era el vacío, idéntico para todos. **Cerrado** (ver abajo), con la salvedad de la corrección 5 |
| 2 | `cross-session-peer-context.sh` descartaba su salida | El propio hook | Emitía `additionalContext` en la raíz; arreglado en `5d9c1ee1b`. Hoy sigue sin entregar nada porque `peers()` = 0: mira sesiones pares, y hubo una sola sesión |
| 3 | `agent-message-inbox-context.sh` con el mismo defecto | Bus de mensajes | Mismo fix de forma, mismo resultado nulo: el store nunca tuvo un mensaje. Falta el **emisor**, no la entrega |
| 4 | Worktree advisory: agentes escribieron en el checkout del operador | ADR-223 | Los worktrees se crean (15 vivos) pero el destino viaja como texto en el prompt. Nada valida `$PWD` contra el worktree asignado |
| 5 | Dos agentes escribieron 31 tests solapados sobre 2 hooks en 4 archivos | Ledger de claims + `expected_files` | `expected_files` viene **vacío** en las 64 filas: `agent-prelaunch.sh` no lo pasa. Es el campo que hubiera detectado la superposición por ruta |
| 6 | El orquestador tuvo que commitear con paths explícitos todo el día | Aislamiento por worktree (ADR-223) | Consecuencia directa de #4: si cada agente escribiera en su worktree, `git add -A` sería seguro |

Los seis se agrupan en dos causas: **todo está keyado por sesión y hoy hubo una
sola sesión** (#1, #2, #3), y **el aislamiento se declara pero no se enruta**
(#4, #5, #6).

## Qué arreglé y sus dos corridas

Archivos: `scripts/cos_task_claims.py`,
`tests/unit/test_cos_task_claims_fingerprint_discrimination.py`. No toqué
`hooks/**`, ni `manifests/**`, ni el wrapper de timing. Sin commit.

Tres cambios en `claim_task`:

1. `CONTENTLESS_FINGERPRINT` — el hash de una tarea sin contenido deja de
   contar como prueba de "mismo trabajo". Cierra el falso positivo.
2. Trabajo igual con `task_id` distinto **dentro de la misma sesión** se
   reporta como `duplicate-work` (evento en `sessions/events.jsonl` +
   `duplicate_of` en el resultado + warning a stderr). Cierra el falso negativo.
3. `duplicate_work_blocks()` lee `COS_CLAIM_DUPLICATE_WORK_BLOCK`. **Por
   defecto avisa, no bloquea** (ver §Lo que NO ejecuté).

Consumidor real del campo: `cos_task_claims.py status` agrupa los claims
activos por fingerprint y reporta los grupos duplicados, más cuántos claims
son ciegos por fingerprint vacío.

### Corrida 1 — antes del fix (FALLANDO)

```
$ .venv/bin/python3 -m pytest tests/unit/test_cos_task_claims_fingerprint_discrimination.py -q -p no:randomly
.F.FF.                                                                   [100%]
E   AssertionError: un fingerprint vacio bloqueo trabajo no relacionado de otra sesion: {'status': 'conflict', 'task_id': 't-beta', 'fingerprint': 'ad863ddeda113b35ccb28498', 'held_by': 'sesA', 'held_by_task_id': 't-alpha', 'expected_files': []}
E   AssertionError: assert None == ['t-1']
     +  where None = <built-in method get of dict object ...>('duplicate_of')
E   assert not True
FAILED ...::test_contentless_claims_across_sessions_do_not_block
FAILED ...::test_same_work_same_session_is_reported_as_duplicate
FAILED ...::test_duplicate_work_blocks_when_flag_is_set
3 failed, 3 passed in 0.14s
```

### Corrida 2 — después del fix (PASANDO)

```
$ .venv/bin/python3 -m pytest tests/unit/test_cos_task_claims_fingerprint_discrimination.py -q -p no:randomly
......                                                                   [100%]
6 passed in 0.14s
```

Sin regresión en las suites de claims que ya existían:

```
$ .venv/bin/python3 -m pytest tests/unit/test_cos_task_claims.py \
    tests/red_team/portability/test_task_claim_ledger.py \
    tests/unit/test_claim_ledger_coherence.py \
    tests/unit/test_multi_agent_coordination_primitives.py \
    tests/behavior/test_primitive_readiness_coordination.py \
    tests/unit/test_session_coordination.py -q -p no:randomly
.............................                                            [100%]
29 passed in 5.12s
```

El test no verifica que el lock se cree: verifica que **impida** (cross-session
con task_id repetido sigue devolviendo `conflict` y `held_by`) y que **no
impida de más** (dos tareas sin relación entre sesiones entran las dos).

Consumidor, corrida real sobre un sandbox:

```
$ .venv/bin/python3 scripts/cos_task_claims.py --project-dir $SB status
COS DUPLICATE WORK WARNING: task t-2 repite el trabajo ya reclamado por t-1 en la sesion S.
Task claims: 3 active / 3 total
- t-1 session=S files=-
- t-2 session=S files=-
- t-3 session=S files=-
DUPLICATE WORK: 1 grupo(s) de claims activos con el mismo fingerprint
- 50e519620bcd731c28197c87: t-1, t-2
WARNING: 1/3 claims activos tienen fingerprint sin contenido (ad863ddeda113b35ccb28498); no se puede detectar trabajo duplicado sobre ellos.
```

## Qué le falta al foso para ser defendible

Tres cosas, sin las cuales esto se replica en una tarde:

1. **Que el reclamo lleve contenido.** Hoy `agent-prelaunch.sh` pasa
   `--description "$DESCRIPTION"` a un writer y después `claim_task.py acquire`
   pisa la fila con una tarea sin descripción: quedan 64/64 fingerprints
   vacíos. Mientras el ledger no tenga ni `expected_files` ni descripción real,
   ninguna lógica de duplicados puede funcionar. **Es el prerequisito de todo
   lo demás** y está en `hooks/`, que no toqué.
2. **Que el aislamiento sea enrutamiento y no texto.** Un `WORKING DIR:` en el
   prompt es una sugerencia. Defendible sería: el agente arranca con `cwd` en
   su worktree y una escritura fuera de él se rechaza. Los 15 worktrees ya
   están; falta que el destino de escritura no dependa de que el agente lea
   bien.
3. **Que la coordinación sea de trabajo, no de sesión.** Todo el diseño asume
   "dos personas, dos terminales". El caso real de hoy fue "una sesión, doce
   agentes". Mientras `session_id` sea la clave, doce agentes son un solo
   actor. La unidad tiene que ser el reclamo de trabajo.

Lo que **no** falta: la cola de merge de un solo escritor y los locks de
edición. Esos funcionan, tienen telemetría y se usaron hoy.

## ¿Puede ser absorbido, y en cuánto tiempo?

Sí, y menos de lo cómodo. Los *teammates* de Claude Code resuelven fan-out
dentro de una sesión; el paso natural es que el arnés sepa qué está haciendo
cada teammate, y de ahí a "no arranques esto, ya lo está haciendo aquél" hay un
salto corto — el arnés ya tiene el prompt de cada agente, que es exactamente el
dato que a nuestro ledger le falta. Estimo **12 a 24 meses** para el caso
intra-sesión, que es el 100% de los fallos de hoy.

Lo que difícilmente absorban pronto: **dos procesos distintos sobre el mismo
checkout de git**, con árnesses distintos (Claude Code + Codex + una sesión
humana). Eso exige estado en el filesystem y no en el proceso del arnés, y es
justo donde el SO ya tiene cola de merge, locks de edición y worktrees. El foso
defendible no es "coordinación entre agentes" —eso lo van a absorber— sino
**coordinación de escritores heterogéneos sobre un repo compartido**. Ahí la
vida útil es más larga, pero sólo si los tres puntos de la sección anterior se
cierran antes de que el arnés llegue.

Juicio corto: **dos años, no diez**, y el reloj corre sobre la mitad
intra-sesión.

## Lo que NO ejecuté y por qué

- **No encendí `COS_CLAIM_DUPLICATE_WORK_BLOCK`.** Con el flag en 1,
  `claim_task` devuelve rc 2 y `hooks/agent-prelaunch.sh` hace `exit 2`: el
  segundo agente con trabajo duplicado **no arranca**. Eso cambia el
  comportamiento de los sub-agentes del operador y la decisión no es mía.
  Plan para encenderlo: (1) que `agent-prelaunch.sh` pase descripción y
  `--expected-file` reales — sin eso el flag no tiene con qué decidir;
  (2) correr un día en modo aviso y mirar
  `grep duplicate-work .cognitive-os/sessions/events.jsonl`; (3) si no hay
  falsos positivos, exportar el flag en el entorno del orquestador.
- **No toqué `hooks/**`, `manifests/**` ni `scripts/hook-timing-wrapper.sh`**,
  por el reparto de los otros seis agentes. Los dos arreglos que más rinden
  —llenar el reclamo con contenido y con `expected_files`— viven en
  `hooks/agent-prelaunch.sh` y quedan como encargo para quien tenga ese archivo.
- **No registré `branch-ownership-lock.sh`, `agent-message-inbox-guard.sh` ni
  `concurrent-write-guard-codex-proxy.sh`.** Registrar un hook es cambiar el
  comportamiento de los sub-agentes, y además `branch-ownership-lock` merece su
  propio test antes de entrar: hoy se libera un lock que nunca se toma.
- **No construí un emisor para el bus de mensajes.** Es la reacción tentadora
  al hallazgo de que el store está vacío, pero sería un mecanismo nuevo cuando
  el que ya existe (el ledger de claims) tenía el dato y no lo miraba.
- **No commiteé ni pusheé.** Todo queda en el working tree.

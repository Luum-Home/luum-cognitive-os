# Registro de los 36 hooks "que nunca corrieron" — 2026-08-19

## Resumen ejecutivo

- **Registrados: 0.** Ninguno correspondía.
- **Frenados: 36 / 36.** Los 36 tienen una declaración de omisión escrita.
- **Para borrar: 0.** Uno (`task-completed`) queda reportado como muerto por
  harness, pero es opt-in para sistemas de tareas externos: se reporta, no se borra.
- **El hallazgo que invalida el encargo:** **27 de los 36 ya corren hoy**, en el
  perfil `default` del operador, invocados como hijos de
  `hooks/bash-hot-path-dispatcher.sh` (9365 corridas). El `runs=0` del censo es un
  **falso negativo**: el wrapper de timing sólo instrumenta hooks registrados en
  `.claude/settings.json`, y el dispatcher llama a sus hijos sin wrapper.
- Dos de esos 27 (`destructive-git-blocker`, `git-commit-scope-guard`) **devuelven
  `exit 2` sobre un `git commit -m` corriente, hoy**. No son bloqueadores latentes:
  son bloqueadores en producción.
- Registrarlos a nivel top-level los **duplicaría** (doble ejecución por comando),
  agregando ~1.5 s de latencia por `git commit` y rompiendo los que llevan estado.

## Correcciones a las premisas del encargo

1. **"36 hooks que nunca corrieron, ni una vez, en 252.496 filas" — FALSO para 27.**
   Corren. La prueba (traza de ejecución del dispatcher con payload real):

   ```bash
   PAY='{"tool_name":"Bash","tool_input":{"command":"git commit -m probe"},"session_id":"probe","cwd":"'$PWD'"}'
   COS_ALLOW_PROTECTED_CONFIG_WRITE=1 bash -c \
     'echo "$1" | bash -x hooks/bash-hot-path-dispatcher.sh 2>&1 \
      | grep -oE "hooks/[a-z0-9-]+\.sh" | sort -u' _ "$PAY"
   ```

   Devuelve `destructive-git-blocker`, `conflict-marker-guard`,
   `untracked-work-preservation-guard`, `direct-main-guard`, `branch-ownership-lock`,
   `cross-session-coordination-guard`, `agent-message-inbox-guard`. Con payload `rm`
   aparecen `destructive-rm-blocker` y `symlink-mutation-guard`; con `curl`,
   `network-egress-guard`.

   Origen del error: `scripts/hook_test_reality_census.py:47` define
   `SETTINGS = REPO / ".claude" / "settings.json"` y de ahí sale `registered`. Un
   hijo del dispatcher nunca aparece ahí. La categoría
   `cero_nunca_corrio_sin_registrar` mide **"no está en settings.json y no emite
   telemetría propia"**, que no es lo mismo que "nunca corrió".

2. **"Registrarlos es la acción de mayor rendimiento que queda" — FALSO, y es
   negativa.** Para los 27 el efecto de registrarlos es doble ejecución. La cadena
   completa del dispatcher para `git commit` mide **1527–2443 ms** (3 corridas);
   duplicarla es ~1.5 s extra por commit, más corrupción de estado en
   `pre-commit-content-hash-dedupe` y `rate-limiter`.

3. **"Olvido — se escribió, se probó, nadie lo enchufó. `destructive-git-blocker`
   con 27 tests huele a esto" — FALSO.** `destructive-git-blocker` está enchufado
   (`hooks/bash-hot-path-dispatcher.sh:139`) y **bloquea hoy**: sobre
   `git commit -m probe` en `main` devuelve `rc=2` con el mensaje
   `BLOCKED: destructive git op ... (ADR-055b, r5-stash-residue)`. La categoría
   "olvido" quedó **vacía**: 0 de 36.

4. **"Dos arquitectos, por caminos independientes, señalaron esto."** Los dos
   leyeron la misma métrica con el mismo falso negativo. Dos caminos que parten del
   mismo censo no son independientes.

5. **"Hay al menos seis mecanismos distintos de declaración de omisión."** Encontré
   cinco relevantes, y falta el que más pesa en la lista del encargo: la **ruta por
   dispatcher** (`hooks/bash-hot-path-dispatcher.sh`), que no es una declaración de
   omisión sino lo contrario — una declaración de *registro indirecto*. Es
   precisamente el que hay que mirar antes de concluir "olvido".

6. **"`teammate-idle` está en `hook-vitality-budget.yaml` … no lo registres."**
   Correcto pero irrelevante: `teammate-idle` **no está entre los 36**. Sí lo está
   `task-completed`, que es el caso análogo (evento `TaskCompleted` nunca observado
   en 225.941 filas) y **no** está contabilizado en `max_event_absent_hooks: 2`.

7. **`publication-safety` no es un descubrimiento pendiente**: es la única entrada
   `LOST` ya presupuestada en `manifests/harness-hook-projection-policy.yaml`
   (`drift_budget.max_lost_entries: 1`), con el motivo escrito en el propio bloque.

## Por qué nunca se registró cada uno

### A. Ya está registrado, vía dispatcher — 27 (la premisa era falsa)

Ruteados por `hooks/bash-hot-path-dispatcher.sh` en el perfil `default`, y además
declarados en el perfil `full` de `manifests/harness-hook-projection-policy.yaml`.
Clasificación `active` / `profile_scoped` en
`manifests/hook-registration-classification.yaml`.

`network-egress-guard`, `destructive-rm-blocker`, `symlink-mutation-guard`,
`destructive-git-blocker`, `conflict-marker-guard`, `untracked-work-preservation-guard`,
`direct-main-guard`, `branch-ownership-lock`, `cross-session-coordination-guard`,
`agent-message-inbox-guard`, `git-commit-scope-guard`, `orchestrator-claim-gate`,
`pre-commit-content-hash-dedupe`, `scope-marker-portability-gate`,
`external-pattern-cleanroom-gate`, `adoption-freeze-gate`, `dependency-license-classifier`,
`research-to-runtime-firewall`, `research-compliance-guard`, `spdx-header-required`,
`external-cache-content-leak`, `attribution-completeness-validator`,
`lib-symlink-divergence-detector`, `legal-review-required-on-runtime-import`,
`pending-truth-staleness-gate`, `release-guard`, `skill-router-bash-gate`.

Ocho de ellos llevan además en `tests/contracts/EXCLUDED_HOOKS.txt` la marca
`GIT_HOOK: … invoked by git/security profile paths, not a default Claude lifecycle
matcher`. Es exacta: entran por el boundary de commit del dispatcher, no por un
matcher propio.

### B. Decisión escrita, fuera del hot path — 6

| Hook | Declaración | Dónde |
|---|---|---|
| `agent-bash-cwd-enforcer` | `profile_scoped` — "projected … in the full profile and by security profiles" | classification |
| `rate-limit-precheck` | `profile_scoped` — "intentionally absent from the default maintainer hot path" | classification |
| `rate-limiter` | `profile_scoped` — "keep out of default projection unless runtime quota evidence requires blocking enforcement" | classification + `rules/rate-limiting.md` |
| `auto-refine` | `future` — "needs PostToolUse matcher definition before active projection" | classification + `rules/ROADMAP.md` §2.3 |
| `auto-verify` | `future` — idem §2.1 | classification + ROADMAP |
| `dod-gate` | `future` — "needs PreToolUse or PostToolUse matcher definition" | classification + ROADMAP §2.2 |

`rate-limiter` es el caso donde el encargo pedía justo lo prohibido:
`rules/rate-limiting.md` dice textual que registrarlo *"es una decisión pendiente
del operador, no un olvido de documentación"*.

### C. Decisión escrita, otro harness / opt-in — 2

| Hook | Declaración |
|---|---|
| `concurrent-write-guard-codex-proxy` | `projected_elsewhere` — "Codex-only … **do not add to Claude settings**" |
| `publication-safety` | `conditional_opt_in` — no-op sin manifest de publicación; es la entrada `LOST` presupuestada del drift ratchet |

### D. Muerto por harness — 1

`task-completed`: `status: demoted`, *"Lifecycle manifest marks TaskCompleted
default_projection=false"*, y `EXCLUDED_HOOKS.txt` lo marca `MANUAL_TRIGGER`. El
evento `TaskCompleted` nunca apareció en 225.941 filas. **No registrar.** Tampoco
borrar: sigue siendo el handler válido para sistemas de tareas externos. Lo que sí
corresponde es contabilizarlo — hoy no está en `max_event_absent_hooks`.

### E. Olvido — 0

Vacía. Ningún hook de los 36 carece de declaración. Verificado cruzando los 36
contra el perfil `full` de `harness-hook-projection-policy.yaml`,
`hook-registration-classification.yaml` y `tests/contracts/EXCLUDED_HOOKS.txt`:
la lista de "sin declaración en ningún lado" salió vacía (`[]`).

## Los observadores registrados, con su latencia medida

**Ninguno.** Los 14 sin ruta de bloqueo se reparten así:

- 11 ya corren por dispatcher (`adoption-freeze-gate`,
  `attribution-completeness-validator`, `dependency-license-classifier`,
  `external-cache-content-leak`, `external-pattern-cleanroom-gate`,
  `legal-review-required-on-runtime-import`, `lib-symlink-divergence-detector`,
  `research-to-runtime-firewall`, `spdx-header-required`,
  `pending-truth-staleness-gate`, `agent-bash-cwd-enforcer` — este último en
  `full`/security, no en `default`).
- 3 son `future` sin matcher definido (`auto-refine`, `auto-verify`, `dod-gate`).
  Registrar un hook sin matcher decidido es exactamente el "corre y no hace nada,
  y ahora además cuesta" que el encargo prohíbe.

Latencia medida igual, porque es el dato que justifica **no** duplicarlos
(`echo "$PAY" | bash hooks/<h>.sh`, ms de reloj de pared, 1 corrida c/u, payload
`git commit -m probe`):

| Hook | ms | rc |
|---|---:|---:|
| `destructive-git-blocker` | 1269 | **2** |
| `direct-main-guard` | 811 | 0 |
| `git-commit-scope-guard` | 466 | **2** |
| `conflict-marker-guard` | 374 | 0 |
| `orchestrator-claim-gate` | 316 | 0 |
| `scope-marker-portability-gate` | 272 | 0 |
| `untracked-work-preservation-guard` | 262 | 0 |
| `cross-session-coordination-guard` | 236 | 0 |
| `agent-message-inbox-guard` | 230 | 0 |
| `pending-truth-staleness-gate` | 196 | 0 |
| `branch-ownership-lock` | 194 | 0 |
| `lib-symlink-divergence-detector` | 178 | 0 |
| `pre-commit-content-hash-dedupe` | 154 | 0 |
| `spdx-header-required` | 135 | 0 |

Cadena completa del dispatcher sobre `git commit`: **1527 / 1649 / 2443 ms** (3
corridas). El corto-circuito `|| exit $?` hace que en la práctica se corte en
`destructive-git-blocker`.

## LOS QUE PUEDEN DENEGAR — tabla para el operador

22 de los 36 tienen ruta de bloqueo (`exit 2` alcanzable). **Ninguno se registró.**
La columna que decide no es "cuántas veces habría disparado" sino **"cuántas veces
ya dispara"**: 20 de los 22 están vivos hoy.

| Hook | Qué bloquea | Estado real | Disparos |
|---|---|---|---|
| `destructive-git-blocker` | git destructivo / commit-push desde rama protegida (ADR-055b) | **vivo, bloquea hoy** | `rc=2` en `git commit -m` sobre `main`, reproducido |
| `git-commit-scope-guard` | `git commit -m` sin scope explícito (ADR-089) | **vivo, bloquea hoy** | `rc=2` en `git commit -m`, reproducido |
| `direct-main-guard` | escritura directa a `main` | vivo | `rc=0` en la probe; dispara por otra condición |
| `destructive-rm-blocker` | `rm` destructivo | vivo | no disparó en probe `rm -f` |
| `symlink-mutation-guard` | mutación de symlinks (`rm/mv/ln/find -delete`) | vivo | no disparó en probe |
| `network-egress-guard` | `curl/wget/nc/ssh/scp/rsync`, `git clone/fetch/pull/push` | vivo | no disparó en probe `curl` |
| `conflict-marker-guard` | marcadores de conflicto staged | vivo | 0 |
| `untracked-work-preservation-guard` | git destructivo con trabajo sin trackear | vivo | 0 |
| `branch-ownership-lock` | commit sobre rama de otra sesión | vivo | 0 |
| `cross-session-coordination-guard` | colisión entre sesiones concurrentes | vivo | 0 |
| `agent-message-inbox-guard` | inbox de mensajes sin drenar | vivo | 0 |
| `orchestrator-claim-gate` | claim de orquestador en commit | vivo | 0 |
| `pre-commit-content-hash-dedupe` | contenido duplicado por hash en commit | vivo | 0 |
| `scope-marker-portability-gate` | falta de marcador `SCOPE:` en commit | vivo | 0 |
| `skill-router-bash-gate` | mutación de dependencias sin ruteo de skill | vivo | no ejercitado |
| `release-guard` | `git tag` / mutación de `VERSION` | vivo | no ejercitado |
| `research-compliance-guard` | compliance de research en commit | vivo | 0 |
| `publication-safety` | gate de publicación | **`LOST` presupuestado**, no corre | no medible |
| `rate-limiter` | token bucket, bloquea bajo presión sostenida | fuera de `default` **por decisión** | no medible |
| `pending-truth-staleness-gate` | (sólo `permissionDecision: "allow"`) | vivo, **no puede denegar** | — |
| `agent-bash-cwd-enforcer` | (sólo `permissionDecision: "allow"`) | `full`/security, **no puede denegar** | — |
| `task-completed` | `exit 2` en evento inexistente | **código inalcanzable** | 0, estructural |

Tres casos de "ruta de bloqueo aparente" que **no** bloquean, tal como anticipaba
el encargo:

- `task-completed` — el evento `TaskCompleted` no existe en este harness. Su
  `exit 2` es código muerto por definición.
- `agent-bash-cwd-enforcer` y `pending-truth-staleness-gate` — el `grep` de
  `permissionDecision` da positivo, pero el valor es `"allow"` en los tres puntos
  de emisión (`agent-bash-cwd-enforcer.sh:197,210`,
  `pending-truth-staleness-gate.sh:55`). No deniegan.
- `destructive-rm-blocker` — su única aparición de `"deny"` (línea 82) es una
  comparación de string contra un veredicto de política
  (`[ "$POLICY_VERDICT" = "deny" ]`), no una emisión de `permissionDecision`. Sí
  deniega, pero por `exit 2`, no por JSON.

**Recomendación al operador:** no hay nada que encender acá. Si querés más
cobertura de bloqueo, la palanca es una sola y está declarada:
`cognitive-os.yaml:586` → `profile: default | full`. Cambiarla proyecta los 32 del
perfil `full` de una vez. Eso es una decisión de perfil, no 36 decisiones de hook.

## Verificación: cuáles vi correr y cuáles no

**Vi correr (traza de ejecución sobre el dispatcher, con payload real):**
`destructive-git-blocker`, `conflict-marker-guard`, `untracked-work-preservation-guard`,
`direct-main-guard`, `branch-ownership-lock`, `cross-session-coordination-guard`,
`agent-message-inbox-guard` (payload `git commit`); `destructive-rm-blocker`,
`symlink-mutation-guard` (payload `rm`); `network-egress-guard` (payload `curl`).
**10 de 36 vistos ejecutar de punta a punta.**

**Vi bloquear de verdad (rc=2 + mensaje):** `destructive-git-blocker`,
`git-commit-scope-guard`. **2 de 36.**

**Ejecuté individualmente sin verlos en la cadena** (14 de la tabla de latencia):
corren y devuelven rc, pero su invocación desde el dispatcher para *ese* payload
quedó tapada por el corto-circuito en `destructive-git-blocker`. Están en el
dispatcher por lectura de código (`hooks/bash-hot-path-dispatcher.sh:159-182`), no
por observación de la cadena completa.

**No vi correr:** los 9 fuera del dispatcher. `rate-limiter`, `rate-limit-precheck`
y `agent-bash-cwd-enforcer` requieren perfil `full`/security; `auto-refine`,
`auto-verify` y `dod-gate` no tienen matcher; `publication-safety` no tiene ruta de
proyección; `concurrent-write-guard-codex-proxy` es de Codex; `task-completed`
espera un evento que no existe. **No verificados en ejecución, y no los registré.**

**Comandos de verificación del encargo — no corridos, a propósito.**
`apply-efficiency-profile.sh`, `hook_quality_audit.py --check` y
`pytest tests/contracts/` estaban condicionados a "después de registrar el grupo
observador". Como no registré nada, `cognitive-os.yaml` quedó sin tocar y no hay
proyección que aplicar ni contrato que pueda haber cambiado. Correrlos habría
producido un verde que no prueba nada de este trabajo.

## Lo que NO hice y por qué

1. **No registré ningún hook.** 27 ya están registrados (vía dispatcher) y
   registrarlos de nuevo los duplica; los 9 restantes tienen decisión escrita. La
   regla del propio encargo —"registrar un hook cuya omisión estaba decidida y
   escrita" es verde barato— se aplica a los 36.
2. **No toqué `cognitive-os.yaml` ni `.claude/settings.json`.** Working tree limpio
   salvo este informe.
3. **No borré `task-completed`.** Muerto para este harness, no muerto en general:
   sigue siendo el handler de sistemas de tareas externos, y el encargo pedía
   "reportar para borrado", no borrar.
4. **No arreglé `scripts/hook_test_reality_census.py`.** Es el bug de origen —
   `registered` mira sólo `.claude/settings.json` e ignora la ruta por dispatcher,
   inflando `cero_nunca_corrio_sin_registrar` con 27 hooks vivos. Arreglarlo cambia
   la salida de un script del que dependen otras auditorías y otros agentes en
   curso; es una decisión del operador, no un efecto colateral de este encargo.
5. **No cambié `profile: default` a `full`.** Encendería 32 hooks, 20 con capacidad
   de bloqueo probada, sobre el flujo de trabajo real del operador. Es exactamente
   la acción de radio de impacto alto que el encargo manda no tomar sola.
6. **No instrumenté a los hijos del dispatcher.** Haría visible lo que hoy es un
   punto ciego de telemetría, pero toca `bash-hot-path-dispatcher.sh` — ruta
   protegida, hot path, y agregar el wrapper de timing a cada hijo suma costo a la
   cadena de 1.5 s. Merece su propia decisión.

### Deuda que queda anotada

- `manifests/hook-vitality-budget.yaml` → `max_event_absent_hooks: 2` no cuenta
  `task-completed`. El comentario dice explícitamente que `TaskCompleted` nunca
  apareció, pero el número sólo cubre los dos hooks *registrados*. No es un
  colchón (el hook no está registrado), pero sí una asimetría entre el comentario
  y el conteo.
- La telemetría de hook-timing no ve a los hijos del dispatcher. Cualquier
  auditoría que derive "nunca corrió" de `hook-timing.jsonl` va a repetir este
  falso negativo sobre 27 hooks.

# Perillas: conectadas o retiradas — 2026-08-20

Continuación del censo forense `bf9817ee8` (`scripts/config_knob_census.py`).
Instrumento de prueba: `python3 scripts/config_knob_census.py --prove`.
Commits: `d1bb23e33` (forma 3), `d192192f2` (forma 1).

## Resumen ejecutivo

| Forma | Antes | Después | Qué se hizo |
|---|---|---|---|
| 3 — el comentario se come el valor | 8 sitios | **0** | 6 arreglados, 2 eran falso positivo del censo |
| 1 — lee un archivo inexistente sin fallback | 7 sitios | **0** | 5 conectados, 1 retirado, 1 era falso positivo |
| 4 — clave declarada sin lector | 52 de 207 medibles | **52** | clasificadas por familia; **cero retiradas**, y el motivo está abajo |
| 2 — clave ausente del archivo | 0 | 0 | sin hallazgos, confirmado |

Perillas conectadas: **8** (`lock_timeout_seconds` ×2, `max_concurrent`,
`smart_start`, `phase`, `security.parry.enabled`, `self_improvement.trigger_threshold.*`,
`singularity_suggestion`). Retiradas: **1** (una asignación muerta en
`hooks/infra-intent-detector.sh`). El instrumento también se arregló: tres de
sus hallazgos eran suyos.

## Correcciones a las premisas del encargo

1. **«Forma 3: 8 sitios, 4 puros» — son 6 reales y 2 falsos positivos.**
   `hooks/session-start-worktree-nudge.sh` y `hooks/agent-bash-cwd-enforcer.sh`
   **ya cortaban** el comentario; lo hacen en la línea siguiente al `sed`, dentro
   de un pipeline partido con `\`. El censo medía línea por línea y no lo veía.
   Arreglado en `d192192f2` (une las continuaciones antes de medir).

2. **«Forma 1: 7 sitios» — son 6.** `hooks/concurrent-write-guard-codex-proxy.sh:54`
   tiene fallback al canónico, escrito `[ -f "$X" ] || X=...`. El regex del censo
   exigía un `!` (`[ ! -f "$X" ] && ...`) y no reconocía el otro idioma. Ese hook
   sufría **sólo** forma 3: apenas se le arregló el parseo, la perilla respondió
   (`A: '300' -> '7'` en `d1bb23e33`, antes del arreglo de rutas).

3. **`security.parry.enabled` estaba al revés en el encargo.** No es que no se
   pueda poner en `true`: el valor que **nunca llegaba era `false`**, que es el
   que el yaml ya trae escrito. El hook compara contra la cadena `"false"` y
   recibía `false#Settotrueafterinstallingparry-guard`. O sea que
   `enabled: false` **no apagaba parry**. Sin impacto medible hoy: `parry-guard`
   no está instalado y el hook no figura en ninguno de los tres registros de
   harness (`grep -c parry-scan .claude/settings.json .codex/hooks.json
   .opencode/cos-hooks.json` → `0 0 0`).

4. **`hooks/session-init.sh:162` seguía intacto** — confirmado, la orquestación
   se equivocaba. Verificado sitio por sitio, no por la lista.

5. **Hallazgo que el encargo no pedía:** `project.phase` llegaba a
   `hooks/predev-completeness-check.sh` como
   `reconstruction#reconstruction|stabilization|production|maintenance`. La
   comparación de fase venía fallando contra **todos** los valores, no sólo
   contra los girados. Es forma 3 sobre el archivo canónico, que sí se leía bien.

6. **`hooks/infra-intent-detector.sh:23` no era una perilla.** Asignaba
   `COGNITIVE_OS_YAML` y no la usaba en ninguna otra línea
   (`grep -c COGNITIVE_OS_YAML hooks/infra-intent-detector.sh` → `1`, la propia
   asignación). No había nada que conectar: se retiró.

7. **`singularity_suggestion` no está declarada en el canónico**
   (`grep -n singularity_suggestion cognitive-os.yaml` → sin resultados).
   Conectar la lectura la vuelve escribible, no la declara.

8. **El bloqueo que iba a reportar dejó de existir a mitad de tarea.** Al empezar,
   `cognitive-os.yaml` estaba sucio por otra sesión (bloque ADR-064), lo que hacía
   imposible retirar claves sin mezclar trabajo ajeno en mi commit. Al ir a
   ejecutarlo, `git status --porcelain cognitive-os.yaml` ya devolvía vacío: la
   otra sesión había commiteado. El bloqueo real de la forma 4 es otro, y está
   en «Lo que NO hice».

## Forma 3: los que arreglé y su prueba

El arreglo es el mismo en los seis: `s/#.*$//` dentro del mismo `sed`, **antes**
del `tr -d '[:space:]'`, copiando `_read_knob` de `hooks/session-cleanup.sh`.

`python3 scripts/config_knob_census.py --prove`. **A** = perilla girada a un
valor distinto del default, en el canónico de la raíz, con el comentario que el
yaml realmente trae. **E** = el canónico con el valor que el repo versiona.
**D** = sin ningún archivo de config.

| hook / perilla | A antes | A después | E después | D después |
|---|---|---|---|---|
| `concurrent-write-guard-codex-proxy` / `lock_timeout_seconds` | `300` | **`7`** | `300` | `300` |
| `predev-completeness-check` / `phase` | `production#reconstruction\|stabilization\|production\|maintenance` | **`production`** | `reconstruction` | `reconstruction` |
| `parry-scan` / `enabled` | `false#Settotrueafterinstallingparry-guard` | **`false [salio_temprano]`** | `false [salio_temprano]` | `''` |
| `concurrent-write-guard` / `lock_timeout_seconds` | `300` | `7` (tras forma 1) | `300` | `300` |
| `session-init` / `max_concurrent` | `10` | `3` (tras forma 1) | `10` | `10` |
| `infra-health` / `smart_start` | `''` | `true` (tras forma 1) | `true` | `''` |

Las columnas **E** y **D** son la mitad que prueba que no se rompió el default:
con el valor versionado, el hook obtiene exactamente ese valor; sin archivo,
obtiene el default escrito en el propio hook.

`[salio_temprano]` marca que el bloque decidió y salió con `exit 0` — en
`parry-scan` es justo el caso en que la perilla **funciona**.

### El arnés también mentía

Dos defectos, arreglados en `d1bb23e33` porque si no la prueba no probaba:

- No definía `_PROJECT_DIR` (así nombra `parry-scan.sh` a la raíz), y leía
  vacío para esa perilla por una razón que no tenía que ver con la perilla.
- Leía vacío cuando el bloque hace `exit 0`, o sea **justo cuando la perilla
  funciona**. Ahora emite el valor por `trap ... EXIT` y lo distingue.

## Forma 1: los que arreglé y su prueba

`ls .cognitive-os/cognitive-os.yaml` → `No such file or directory`. El canónico
es el de la raíz. Se invirtió el orden y se dejó `.cognitive-os` de fallback —
la forma que ya usaban `parry-scan.sh`, `session-start-worktree-nudge.sh` y
`agent-bash-cwd-enforcer.sh`.

| archivo | perilla | prueba |
|---|---|---|
| `hooks/concurrent-write-guard.sh` | `lock_timeout_seconds` | A `300`→`7`, E `300`, D `300` |
| `hooks/session-init.sh` | `max_concurrent` | A `10`→`3`, E `10`, D `10` |
| `hooks/infra-health.sh` | `smart_start` | A `''`→`true`, E `true`, D `''` |
| `packages/skill-governance/hooks/kpi-trigger.sh` | `self_improvement.trigger_threshold.*` | usa `yq`, sin forma 3; claves declaradas en `cognitive-os.yaml:606-612` |
| `hooks/_lib/singularity-suggestion.sh` | `singularity_suggestion` | conectada pero **no declarada** (ver corrección 7) |

**Un cambio de comportamiento que hay que decir en voz alta.** `smart_start`
estaba declarada `true` y llegaba vacía, o sea apagada. Ahora llega `true`. No
se inventó un default nuevo: es el valor que el operador ya tenía escrito. El
único efecto sería arrancar servicios docker, y el lazo que lo haría exige
`mode: always`: `grep -c 'mode: always' cognitive-os.yaml` → `0`. Lo que sí
cambia es el reporte de `infra-health`, que pasa de «no services configured» a
la lista real.

### Retirada, no conectada

`hooks/infra-intent-detector.sh` — asignación muerta de `COGNITIVE_OS_YAML`.
Evidencia en la corrección 6.

### El censo, corregido

`FALLBACK` ahora reconoce los dos idiomas (`[ ! -f ] &&` y `[ -f ] ||`), y la
forma 3 se mide sobre el pipeline entero. Prueba pareada en
`tests/red_team/portability/test_config_knob_census.py` (3 tests, uno de ellos
falla a propósito si el par lector-roto / lector-sano empata, porque entonces
el «cero hallazgos» sería ceguera y no ausencia).

## Forma 4: la clasificación por familia

52 claves sin lector sobre 207 medibles, población 236, más 29 ciegas por nombre
genérico y 7 leídas sólo en tests. Comando por clave:

```bash
grep -rIl --exclude-dir=.git --exclude-dir=docs '<clave>' \
  hooks/ scripts/ cos_lib/ lib/ packages/ tests/ .claude/ .codex/ .opencode/
```

| familia | n | clasificación | motivo |
|---|---|---|---|
| `phases.reconstruction.*` | 6 | **(c) consumidor fuera del parser** | No son perillas de código: son política que leen los agentes vía `rules/phase-aware-agents.md`. `break_existing` da 1 hit, y hay que mirar cuál antes de tocar nada. |
| `skills.loading.*` | 5 | **(a) falta el consumidor** | `level1/2/15_budget`, `max_active`, `compact_catalog` describen el contrato de `context-optimization` de `RULES-COMPACT.md` §9. La regla existe, el parser no. |
| `auto_repair.*` | 7 | **(a) falta el consumidor** | `gc_*`, `circuit_breaker.*`, `worktree.cleanup_on_success`, `metrics.rotation.keep_lines`. `gc_min_success_rate` → 0 consumidores. `auto_repair` figura como hook-enforced en las reglas; los umbrales no llegan a ningún lado. |
| `security.supply_chain.*` | 4 | **(a) falta el consumidor** | `pin_docker_digests` → 0 consumidores. La regla `supply-chain-defense` declara digest pinning; la aplicación no está. |
| `resources.tokens.*` | 4 | **(a) falta el consumidor** | `auto_summarize_at_percent` → 0 consumidores. Mismo patrón: los umbrales de `context-management` están escritos como regla, no como código. |
| `tool_replay_ledger.*` | 4 | **(a) falta el consumidor** | `char_cap_per_session` → 0 consumidores. Familia entera sin lector. |
| `models.providers.openrouter.*` | 3 | **(b) candidata a retiro** | El despacho real es `qwen,claude` (ADR-049). OpenRouter aparece en la cadena de degradación pero estas tres claves no las lee nadie. |
| `efficiency.profiles.default.*` | 3 | **(c) posible consumidor externo** | Existe `packages/efficiency-profile`; hay que descartar desajuste de nombre antes de llamarlas huérfanas. |
| `resources.infrastructure.*` | 4 | **(c) fuera del parser** | `services.*.config.*` las consume docker-compose, no el yaml. `valkey.review_by` es metadato de gobernanza, no perilla. |
| `memory.sync.*`, `memory.memu.*` | 3 | **(a) falta el consumidor** | Integración memu/engram declarada por encima de lo implementado. |
| sueltas (`quality.*`, `rules.loading.compact_file`, `runtime.ttft_watchdog.max_sec`, `resources.budget.per_session_target_usd`, `resources.compute.prefer_sequential`, `evolve.queue_cap`, `harness.hooks.context-diet.codex_gap_reason`) | 9 | mixta | `codex_gap_reason` es un texto explicativo, no una perilla: mal clasificada por el censo. El resto necesita una mirada por clave. |

## Las que retiré, una por una

**Ninguna clave del yaml.** La única retirada de esta tanda es la asignación
muerta de `hooks/infra-intent-detector.sh`, documentada arriba con su evidencia
(`grep -c COGNITIVE_OS_YAML` → `1`).

## Las que quedan declaradas y por qué

Las 52. El motivo es uno solo y vale para todas: **el encargo pide retirar sólo
lo que se pueda justificar una por una, y una por una son 52 verificaciones que
no entran en el presupuesto de esta tanda.** Retirar por familia sería
exactamente el verde barato que el encargo prohíbe.

Hay además dos señales concretas de que el bucket «sin lector» no se puede leer
como «borrable»:

- `break_existing` y `level15_budget` devuelven **1 consumidor cada una** con el
  comando de arriba. El censo las pone en «sin lector en este repo» porque
  excluye `docs/`; el hit hay que mirarlo antes de borrar.
- `harness.hooks.context-diet.codex_gap_reason` no es una perilla sino una
  cadena de documentación. Está en el bucket por forma, no por concepto.

La familia con mejor caso para retiro es `models.providers.openrouter.*` (3
claves), y aun así hay que cruzarla contra la cadena de degradación de ADR-049
antes de tocarla.

## Lo que NO hice y por qué

- **No retiré ninguna de las 52 claves.** Ver arriba. La decisión correcta es
  una tanda dedicada, por familia, con el consumidor buscado a mano.
- **No toqué `cognitive-os.yaml`.** Cuando arranqué estaba sucio por otra sesión
  (bloque ADR-064); cuando dejó de estarlo, ya no quedaba presupuesto para
  hacer bien el trabajo por clave.
- **No unifiqué la precedencia entre los dos archivos.** `hooks/session-cleanup.sh`
  le da la última palabra al override de `.cognitive-os`; los hooks que conecté
  se la dan al canónico de la raíz, que es el idioma mayoritario del repo (3
  hooks ya lo usaban). Hoy son indistinguibles porque
  `.cognitive-os/cognitive-os.yaml` no existe en ningún checkout; el día que
  exista, van a divergir. Unificarlo cambia el comportamiento de
  `session-cleanup.sh` y merece su propia decisión.
- **No declaré `singularity_suggestion` en el yaml.** Conectar la lectura y
  declarar la clave son dos decisiones distintas; la segunda es del operador.
- **No registré `hooks/parry-scan.sh` en ningún harness.** Está en cero registros;
  conectar su perilla no lo pone a correr, y ponerlo a correr no me lo pidieron.

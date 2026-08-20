# Forense: perillas de configuración desconectadas

Fecha: 2026-08-20 · Instrumento: `scripts/config_knob_census.py`

## Resumen ejecutivo

Censo sobre 13.305 archivos de `hooks/`, `scripts/`, `cos_lib/`, `lib/`,
`packages/`, `cmd/`, `.claude/`, `.codex/`, `.opencode/`, `tests/` y docs.

- **Forma 4 — clave declarada que nadie lee:** población 236 nombres de clave
  hoja, 207 medibles, 29 ciegas. **52 sin lector en este repo**, 7 mencionadas
  sólo desde tests, 148 con algún lector.
- **Forma 1 — la lectura apunta a un archivo inexistente:** población 34
  asignaciones shell de la ruta del yaml. 20 apuntan al canónico, 7 apuntan a
  `.cognitive-os/cognitive-os.yaml` con *fallback* al canónico (correctas), y
  **7 apuntan al inexistente sin fallback**.
- **Forma 3 — el parseo no llega al valor:** **8 sitios** cortan el valor con
  `sed` sin sacar el comentario de fin de línea, sobre claves cuya línea
  canónica sí lo tiene.
- **Forma 2 — el archivo existe y la clave no:** población 16 claves parseadas
  por shell; 15 están en el canónico, 1 (`image`) pertenece a otro archivo.
  **Cero hallazgos**, con la ceguera declarada abajo.
- Dos perillas probadas girándolas: `lock_timeout_seconds` y `smart_start`.
  Las dos siguen inertes al girarlas en el canónico.

Reproducir todo:

```bash
python3 scripts/config_knob_census.py            # censo, exit 1 con hallazgos
python3 scripts/config_knob_census.py --list     # detalle por hallazgo
python3 scripts/config_knob_census.py --prove    # gira las perillas y mide
```

## Correcciones a las premisas del encargo

1. **`max_concurrent` en `hooks/session-init.sh` NO está arreglado.** El encargo
   dice «los dos están arreglados; `max_concurrent`, en el mismo bloque de
   `session-init.sh`, tenía el mismo defecto». Al 2026-08-20 la línea 162 sigue
   siendo `CONFIG_FILE="$PROJECT_DIR/.cognitive-os/cognitive-os.yaml"` sin
   fallback, y `git status --porcelain hooks/session-init.sh` no devuelve nada:
   el archivo está limpio en HEAD, nadie lo tocó todavía. Además arrastra la
   forma 3 (`max_concurrent: 10               # Maximum simultaneous sessions`).
   No lo toqué: está en la lista de archivos de otro agente.

2. **No eran dos defectos en un bloque de ocho líneas: es un patrón repetido en
   siete hooks.** El mismo par ruta-inexistente + parseo-con-comentario aparece
   en `concurrent-write-guard.sh`, su proxy de Codex, `infra-health.sh`,
   `session-init.sh`, `infra-intent-detector.sh`, `_lib/singularity-suggestion.sh`
   y `packages/skill-governance/hooks/kpi-trigger.sh`.

3. **La forma 3 también pega donde la forma 1 no existe.** Cuatro hooks leen
   correctamente el canónico y aun así el valor no llega:
   `parry-scan.sh`, `predev-completeness-check.sh`,
   `session-start-worktree-nudge.sh` y `agent-bash-cwd-enforcer.sh`. El caso de
   `parry-scan.sh` es el más caro: `security.parry.enabled` no se puede poner
   en `true` sin borrar antes el comentario de esa línea.

4. **Mi primera corrida daba 98 claves sin lector; el número real es 52.** El
   tokenizador del índice cortaba en el guion, así que ninguna clave con guion
   (`contextual_triggers.acceptance-criteria` y sus 45 hermanas) podía
   encontrarse jamás. Es exactamente el error «52 archivos, el real era 1» que
   el encargo advierte. Arreglado indexando con dos tokenizadores; queda escrito
   en el docstring del script para que nadie lo reintroduzca.

5. **`timeout` en macOS: cierto, pero el repo ya lo resolvió.** `infra-health.sh`
   trae su propio `run_bounded`. No es una corrección al encargo, es la
   confirmación de que la premisa es correcta y ya tiene respuesta local.

## Claves declaradas que nadie lee

52 de 207 medibles. `python3 scripts/config_knob_census.py --form 4 --list`.
Agrupadas por familia:

| Familia | Claves | Comentario |
|---|---|---|
| `phases.reconstruction.*` | 6 (`break_existing`, `rewrite_over_patch`, `follow_standard_strictly`, `skip_backwards_compat`, `document_as_future_work`, `auto_remediate_architecture`) | El comportamiento de fase está escrito en reglas y prompts, no leído del yaml. |
| `auto_repair.*` | 7 (`gc_after_days`, `gc_min_attempts`, `gc_min_success_rate`, `global_hourly_cap`, `max_consecutive_failures`, `keep_lines`, `cleanup_on_success`) | Documentadas en `docs/04-Concepts/root/auto-repair-system.md`. |
| `tool_replay_ledger.*` | 4 (`char_cap_per_session`, `item_cap_per_session`, `max_tracked_ledgers`, `metric_log`) | ADR-263 las documenta; ningún archivo de código las nombra. |
| `security.supply_chain.*` | 4 (`digest_rotation_days`, `pin_cos_commits`, `pin_docker_digests`, `verify_on_pull`) | |
| `resources.tokens.*` | 4 (`auto_summarize_at_percent`, `model_downgrade_threshold_percent`, `rule_compression`, `skill_cache_ttl_seconds`) | Tres aparecen en `rules/resource-governance.md`. |
| `models.providers.openrouter.*` | 3 (`auto_select`, `fallback_trigger`, `use_as_fallback`) | |
| `skills.*` / `rules.loading.*` | 5 (`auto_generate`, `registry_update`, `max_active`, `compact_catalog`, `compact_file`) | `compact_file: RULES-COMPACT.md` es el nombre del archivo que todo el mundo usa — pero por constante, no leyendo esta clave. |
| resto | 19 (`memory.sync.auto_export`/`auto_import`, `memory.memu.proactive_loading`, `quality.coverage.block_pr`, `quality.completeness_check`, `quality.exhaustive_prompts`, `resources.infrastructure.auto_scale`, `backend_store_uri`, `otel_endpoint`, `prefer_sequential`, `evolve.queue_cap`, `snapshots.snapshots_dir`, `auto_refine.tracking_dir`, `runtime.ttft_watchdog.max_sec`, `runtime.engram_mcp.wait_sec`, `scan_on_session_start`, `reliability_gate`, `target_tokens_per_session`, `codex_gap_reason`) | |

Siete más sólo se nombran desde tests (`level1_budget`, `level2_budget`,
`level15_budget`, `per_session_target_usd`, `review_by`, `rules_loading`,
`target_cost_per_session_usd`): el test afirma que la clave está en el yaml, no
que alguien la consuma. No las conté como huérfanas porque el test es un
consumidor real, aunque sea uno que sólo verifica presencia.

Verificación cruzada a mano de diez de ellas, para no confiar en el índice:

```bash
for k in max_sec ttft_watchdog item_cap_per_session tool_replay_ledger \
         max_active snapshots_dir rule_compression skill_cache_ttl_seconds \
         max_consecutive_failures global_hourly_cap; do
  echo "$k -> $(grep -rl "$k" --include='*.py' --include='*.sh' --include='*.go' \
       hooks scripts cos_lib lib packages cmd 2>/dev/null | wc -l | tr -d ' ')"
done
```

Seis dieron 0 archivos. Las cuatro que dieron 1-2 (`max_sec`, `ttft_watchdog`,
`tool_replay_ledger`, `max_active`) son el propio yaml proyectado o docstrings:
el índice las cuenta como huérfanas porque busca el nombre de la clave hoja, no
el prefijo. Es la clase de match que hay que mirar de a uno.

## Lecturas que apuntan a archivos o claves inexistentes

`.cognitive-os/cognitive-os.yaml` no existe en este checkout
(`ls -la .cognitive-os/cognitive-os.yaml` → *No such file or directory*), y no
lo genera ningún instalador de este repo. Siete lecturas apuntan ahí sin
fallback:

| Archivo | Línea | Clave | Efecto |
|---|---|---|---|
| `hooks/concurrent-write-guard.sh` | 58 | `lock_timeout_seconds` | El lock siempre expira a 300s. Probado girando. |
| `hooks/concurrent-write-guard-codex-proxy.sh` | 54 | `lock_timeout_seconds` | Idem, en el proxy de Codex. |
| `hooks/infra-health.sh` | 13 | `smart_start` | El arranque perezoso de Docker nunca se enciende. Probado girando. |
| `hooks/session-init.sh` | 162 | `max_concurrent` | El aviso de sesiones concurrentes usa siempre 10. **De otro agente, no lo toqué.** |
| `hooks/infra-intent-detector.sh` | 23 | — | Apunta al inexistente; el hook sugiere leer el yaml en su texto, no lo parsea. Sin perilla asociada. |
| `hooks/_lib/singularity-suggestion.sh` | 57 | — | Igual: ruta inexistente, sin clave parseada en el mismo archivo. |
| `packages/skill-governance/hooks/kpi-trigger.sh` | 45 | — | Igual. |

Los otros 7 sitios que nombran `.cognitive-os/cognitive-os.yaml` **sí** caen al
canónico (`parry-scan.sh`, `inject-phase-context.sh`,
`session-start-worktree-nudge.sh`, `dispatch_gate_check.py` y compañía) y no son
hallazgo.

**Forma 2 (archivo presente, clave ausente): cero.** De las 16 claves que el
shell parsea con `grep '<clave>:'`, 15 están en el canónico. La única ausente es
`image`, que se parsea de `docker-compose`, no de acá:

```bash
grep -rhoE "grep [^|]*'[a-z_]+:'" --include="*.sh" hooks scripts packages \
  | grep -oE "'[a-z_]+:'" | tr -d "':" | sort -u \
  | while read -r k; do grep -qE "^[[:space:]]*${k}:" cognitive-os.yaml \
      || echo "AUSENTE: $k"; done
```

## Parseos que no llegan al valor

Ocho sitios usan `sed 's/.*clave:[[:space:]]*//'` sin sacar el comentario, sobre
claves cuya línea canónica lo tiene. El valor que llega es el valor pegado al
comentario sin espacios:

| Archivo | Clave | Línea canónica | Valor que llega |
|---|---|---|---|
| `hooks/parry-scan.sh` | `security.parry.enabled` | `enabled: false     # Set to true after installing parry-guard` | `false#Settotrue...` — y con `true` llegaría `true#Set...`, así que **la perilla no se puede encender sin borrar el comentario**. |
| `hooks/agent-bash-cwd-enforcer.sh` | `sub_agent_cwd` | `sub_agent_cwd: isolated_worktree   # isolated_worktree \| current \| ...` | `isolated_worktree#isolated_worktree\|current\|...` |
| `hooks/session-start-worktree-nudge.sh` | `sub_agent_cwd` | idem | idem |
| `hooks/predev-completeness-check.sh` | `project.phase` | `phase: reconstruction     # reconstruction \| stabilization \| ...` | `reconstruction#reconstruction\|...` |
| `hooks/concurrent-write-guard.sh` | `lock_timeout_seconds` | `lock_timeout_seconds: 300        # Lock auto-expires after 5 minutes` | `300#Lock...` (además de la forma 1) |
| `hooks/concurrent-write-guard-codex-proxy.sh` | `lock_timeout_seconds` | idem | idem |
| `hooks/infra-health.sh` | `smart_start` | `smart_start: true              # Lazy-load Docker services...` | `true#Lazy-load...` |
| `hooks/session-init.sh` | `max_concurrent` | `max_concurrent: 10               # Maximum simultaneous sessions` | `10#Maximum...` |

Los cuatro primeros son forma 3 **pura**: leen el archivo correcto. Ahí el
comentario es todo el defecto. `hooks/cognitive-os-health.sh` hace lo contrario
y sirve de contraejemplo: encadena `sed 's/[[:space:]]*#.*//'` y sí llega al
valor.

Nota sobre el instrumento: el detector de forma 3 empareja la clave con la
**primera** línea del canónico que la declara. Para `enabled` eso apuntó a la
línea 188 (litellm), no a la 753 (parry). Verifiqué a mano que el veredicto se
sostiene —la línea de parry también tiene comentario— pero la evidencia
automática de esa fila es la línea equivocada. Está declarado en el docstring.

## Default deliberado vs desconectada: cómo las separé

Un default no es un defecto. El criterio fue **una sola pregunta con respuesta
observable**: *si giro la perilla en el archivo que el operador realmente edita,
¿cambia el comportamiento?*

- **Default deliberado:** el archivo puede no estar (proyecto consumidor recién
  instalado), el default es correcto, y cuando el archivo está el valor llega.
  Los 7 sitios con fallback al canónico son esto: en este repo el fallback
  agarra, en un consumidor sin `.cognitive-os/` también.
- **Desconectada:** el archivo que la lectura busca **no existe en ningún
  checkout de este repo** y ningún instalador lo crea, o el parseo destruye el
  valor. Ahí el default no es un default: es el único valor posible.
- **Ambigua, declarada como tal:** las 29 claves con nombre genérico
  (`enabled`, `phase`, `model`, `timeout`...) — un match textual no prueba que
  ese código lea *esta* clave. Van al bucket ciego del `Census`, no al conteo.
  Y las 52 huérfanas son «sin lector **en este repo**»: un instalador o un
  proyecto consumidor fuera del árbol no se ve desde acá.

## Las que probé girando

`python3 scripts/config_knob_census.py --prove`. El script **extrae el bloque
real del hook** (no una transcripción, que envejece), lo corre con
`PROJECT_DIR` apuntando a un directorio de usar y tirar, y hace `env.pop` de
`COS_ALLOW_PROTECTED_CONFIG_WRITE` para que el subproceso no herede el permiso
del padre. Tres escenarios por perilla:

| Perilla | A: canónico en la raíz (la realidad) | B: `.cognitive-os/` con comentario | C: `.cognitive-os/` sin comentario |
|---|---|---|---|
| `lock_timeout_seconds` girada a `7` | **300** (no cambió) | **300** (no cambió) | `7` |
| `smart_start` girada a `true` | **vacío** = apagado | `true#Lazy-loadDockerserviceswhenskillsneedthem` ≠ `true` | `true` |

Las dos funcionan en exactamente una configuración —C— que no ocurre en ningún
checkout: exige un archivo que nadie crea y una línea sin el comentario que el
canónico trae escrito.

## Lo que NO hice y por qué

- **No arreglé ningún hook.** El encargo es forense y hay cinco agentes más
  escribiendo sobre este checkout; `session-init.sh` está explícitamente en la
  lista ajena y `agent-bash-cwd-enforcer.sh` /
  `session-start-worktree-nudge.sh` aparecen modificados en `git status`. Siete
  archivos tocados en paralelo es cómo se pierde trabajo de otro. El arreglo es
  mecánico y está descrito arriba fila por fila.
- **No corrí ninguna suite.** Máquina bajo carga alta con tres agentes
  corriendo tests. Todo el censo es estático más dos subprocesos `bash` de
  milisegundos sobre directorios temporales.
- **No busqué consumidores fuera del repo.** Las 52 huérfanas pueden tener
  lector en un instalador o en un proyecto consumidor. Por eso el bucket se
  llama `sin_lector_en_este_repo` y no `sin lector`.
- **No cubrí lecturas de config en Python/Go con la misma profundidad.** El
  detector de formas 1 y 3 sólo mira shell; en Python un `.get("clave",
  default)` sobre un dict cargado con `yaml.safe_load` no se distingue de un
  default deliberado sin leer el sitio. Eso queda como el hueco más grande de
  este censo.
- **No revisé `.cognitive-os/test-lanes.yaml` ni `manifests/*.yaml`.** El
  encargo acotaba a `cognitive-os.yaml`; las mismas cuatro formas podrían vivir
  ahí y el instrumento se extiende cambiando `CANONICAL`.

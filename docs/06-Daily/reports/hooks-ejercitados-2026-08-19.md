# Hooks ejercitados vs solo nombrados — 2026-08-19

**Instrumento:** `scripts/hook_exercise_audit.py`
**Reproducir:** `python3 scripts/hook_exercise_audit.py` (o `--json`)
**Snapshot medido:** HEAD `2a09d8445`, con `scripts/hook_quality_audit.py` modificado
sin commitear (la ampliación de `TEST_ROOTS` a 19 raíces).
**Exit code en el snapshot:** 0 (sin hallazgos).

> Los números de abajo son una foto de un árbol que se estaba moviendo mientras se
> medía: en el transcurso de la tarea `TEST_ROOTS` pasó de 4 raíces a 5 y después a
> 19, y el corpus de 1032 a 1286 archivos. El entregable es el script, no la foto.
> Reproducir es un comando.

## Por qué existe este script

`manifests/hook-quality.yaml` contesta *"¿hay un test que menciona este hook?"*.
Esa no es la pregunta que importa. La que importa es *"¿hay un test que lo corre?"*,
y es más difícil de contestar que sí. El escalón:

| Nivel | Qué significa |
|---|---|
| `EXERCISED` | el nombre viaja como argumento dentro de un nodo `Call` — algo lo invoca, lo alimenta o lo parametriza |
| `NAMED_ONLY` | el nombre existe como literal string y no se le pasa a nada: mención, no ejecución |
| `NO_TEST` | ningún test lo nombra siquiera |
| `UNCLASSIFIABLE` | **el instrumento no puede juzgar este caso** |

`UNCLASSIFIABLE` no es un nivel de calidad. Es una declaración sobre la medición.
Dos causas, las dos reales:

1. **Indirección.** `CASES = ["hooks/x.sh"]` y después `run(CASES[0])`: el literal
   no es argumento de ningún `Call` y sin embargo el test corre el hook.
   Clasificarlo `NAMED_ONLY` sería acusar de mención vacía a un test que funciona.
2. **Archivo que no parsea.** Mismo caso por otra vía.

## Resultados

| Nivel | Hooks | Sobre el denominador medible |
|---|---:|---|
| `EXERCISED` | 141 | 95,92 % (141/147) |
| `NAMED_ONLY` | 0 | 0,00 % (0/147) |
| `NO_TEST` | 6 | 4,08 % (6/147) |
| `UNCLASSIFIABLE` | 53 | — (es la ceguera) |

- **Denominador total:** 200 hooks registrados en `cognitive-os.yaml` (`harness.hooks`).
- **Denominador medible:** 147 = 200 − 53 `UNCLASSIFIABLE`.
- **Ceguera:** 26,50 % (53/200).

**El cero de `NAMED_ONLY` es exactamente el caso que este script existe para no
dejar pasar.** Un `0` con 26,5 % de ceguera no dice "no hay menciones vacías": dice
que de 53 hooks no se sabe, y que entre esos 53 puede haber menciones vacías que la
técnica no distingue de ejercicios reales. No es un resultado, es una no-observación.
El script lo imprime en la salida cada vez que la ceguera supera el 10 %.

## Los 6 hooks sin ningún test

| Hook | Criticidad | Maturity | Veredicto |
|---|---|---|---|
| `cos-session-start-projector` | lifecycle | observe | deuda |
| `history-rewrite-documented` | standard | observe | deuda |
| `pending-truth-verify-weekly` | standard | observe | deuda |
| `post-git-orphan-notifier` | standard | observe | deuda |
| `session-sanity` | lifecycle | observe | deuda |
| `session-token-aggregator` | lifecycle | observe | deuda |

### Qué cuenta como hallazgo, y por qué estos seis no lo son

Un hook sin test es **hallazgo** cuando su falla es silenciosa:

- criticidad `security` o `quality` — decide sobre secretos, contenido o calidad, y
  si deja de decidir nadie se entera;
- maturity `block` o `emergency` — ya bloquea trabajo, así que un falso positivo
  cuesta caro y un falso negativo más;
- o está declarado en `REQUIRED_BEHAVIOR_COVERAGE`.

**Un hook advisory sin test NO es un hallazgo, y queda escrito acá.** Los seis de
arriba son `standard`/`lifecycle` en maturity `observe`: no bloquean a nadie, y lo
peor que hacen al romperse es dejar de avisar — cosa que se nota. Contarlos como
hallazgo pondría la salida en rojo permanente, y un gate que siempre está rojo no se
lee: se apaga. Quedan listados como deuda, que es lo que son.

Regla extra: un hook de `REQUIRED_BEHAVIOR_COVERAGE` que no llegue a `EXERCISED` es
hallazgo aunque tenga tests — para cobertura obligatoria, "lo nombran" no alcanza.

## Los 53 `UNCLASSIFIABLE`

Casi todos son el mismo patrón: un test que declara una batería de hooks en una
constante y después la recorre. `tests/unit/test_bash_hot_path_dispatcher_git_global_opts.py`
es el caso testigo — `COMMIT_BATTERY = {...}` con 14 hooks adentro, usada más abajo.
Ese test los ejercita de verdad; esta técnica no lo puede probar.

| Hook | Criticidad | Primer test que lo referencia |
|---|---|---|
| `adr-relevance-suggest` | quality | `tests/contracts/test_context_budget_hook_wiring.py` (+4) |
| `adversarial-review-gate` | quality | `tests/hooks/test_adversarial_review_gate.py` |
| `agent-bash-cwd-enforcer` | coordination | `tests/contracts/test_opencode_native_adapter_design.py` (+3) |
| `agent-message-inbox-context` | coordination | `tests/contracts/test_context_budget_enforcement.py` (+2) |
| `agent-message-inbox-guard` | coordination | `tests/unit/test_agent_message_hooks.py` (+1) |
| `agent-working-dir-inject` | coordination | `tests/contracts/test_primitive_harness_partials_contract.py` (+5) |
| `aspirational-audit-weekly` | standard | `tests/hooks/test_aspirational_audit_weekly.py` |
| `attribution-completeness-validator` | quality | `tests/unit/test_bash_hot_path_dispatcher_git_global_opts.py` |
| `branch-ownership-lock` | coordination | `tests/contracts/test_branch_ownership_lock.py` (+2) |
| `consequence-evaluator` | standard | `tests/audit/test_hook_disable_env.py` (+2) |
| `control-plane-audit-hourly` | standard | `tests/behavior/test_control_plane_audit_hourly_cooldown.py` |
| `cos-executor-daemon-launcher` | standard | `tests/contracts/test_self_install_no_container_spawn.py` |
| `cosd-auth-guard` | standard | `tests/contracts/test_cosd_auth_primitives.py` (+3) |
| `dependency-license-classifier` | standard | `tests/unit/test_bash_hot_path_dispatcher_git_global_opts.py` |
| `docker-drift-detector` | standard | `tests/unit/test_docker_drift_detector.py` |
| `edit-lock-drain-parked` | coordination | `tests/unit/test_edit_lock_drain_parked.py` |
| `edit-lock-process-negotiations` | coordination | `tests/unit/test_edit_lock_process_negotiations.py` |
| `external-cache-content-leak` | standard | `tests/unit/test_bash_hot_path_dispatcher_git_global_opts.py` |
| `external-pattern-cleanroom-gate` | standard | `tests/unit/test_bash_hot_path_dispatcher_git_global_opts.py` |
| `legal-review-required-on-runtime-import` | quality | `tests/unit/test_bash_hot_path_dispatcher_git_global_opts.py` |
| `lib-symlink-divergence-detector` | standard | `tests/unit/test_bash_hot_path_dispatcher_git_global_opts.py` |
| `native-agent-heartbeat-post` | coordination | `tests/integration/test_native_agent_heartbeat.py` (+1) |
| `native-agent-heartbeat-pre` | coordination | `tests/integration/test_native_agent_heartbeat.py` (+1) |
| `orchestrator-decision-trace` | standard | `tests/unit/test_orchestrator_decision_trace_hook.py` |
| `pending-truth-drift-detector` | standard | `tests/behavior/test_pending_truth_drift_detector_nudge.py` |
| `pending-truth-staleness-gate` | standard | `tests/unit/test_bash_hot_path_dispatcher_git_global_opts.py` |
| `post-agent-verify` | coordination | `tests/behavior/test_post_agent_verify.py` |
| `pre-commit-content-hash-dedupe` | standard | `tests/unit/test_bash_hot_path_dispatcher_git_global_opts.py` |
| `predev-completeness-check` | standard | `tests/unit/test_codex_guard_layer.py` |
| `pyrefly-typecheck-advisory` | standard | `tests/contracts/test_pyrefly_pilot_radar.py` |
| `reaper-daemon-launcher` | standard | `tests/contracts/test_self_install_no_container_spawn.py` (+1) |
| `research-compliance-guard` | standard | `tests/behavior/test_research_compliance_guard.py` (+3) |
| `research-quality-validator` | quality | `tests/unit/test_research_quality_validator_hook.py` |
| `research-to-runtime-firewall` | standard | `tests/unit/test_bash_hot_path_dispatcher_git_global_opts.py` |
| `review-spawner` | quality | `tests/unit/test_codex_guard_layer.py` |
| `rule-md-routing-validator` | quality | `tests/unit/test_rule_md_routing_validator_hook.py` |
| `rule-router-prompt-suggest` | standard | `tests/contracts/test_context_budget_hook_wiring.py` |
| `scope-marker-portability-gate` | standard | `tests/hooks/test_scope_marker_gate_trigger.py` (+2) |
| `session-quality-close-gate` | lifecycle | `tests/unit/test_session_quality_close_gate.py` |
| `session-start-stack-recommend` | lifecycle | `tests/unit/test_session_start_stack_recommend.py` |
| `session-startup-protocol` | lifecycle | `tests/unit/test_startup_protocol.py` |
| `session-wrapup-trigger` | lifecycle | `tests/hooks/test_os_session_wrapup_addendum_trigger.py` (+1) |
| `skill-drift-detector` | standard | `tests/behavior/test_skill_drift_detector_warn_path.py` |
| `skill-feedback-tracker` | standard | `tests/behavior/test_skill_feedback_tracker_skill_name.py` (+1) |
| `skill-invocation-logger` | standard | `tests/unit/test_performance_ledger_rollups.py` (+1) |
| `skill-md-routing-validator` | quality | `tests/contracts/test_validator_promotion_trigger.py` |
| `skill-post-execution-analysis` | standard | `tests/integration/test_skill_post_execution_hook.py` |
| `spdx-header-required` | standard | `tests/unit/test_bash_hot_path_dispatcher_git_global_opts.py` |
| `stash-budget-warn` | standard | `tests/integration/test_stash_budget_warn.py` |
| `subagent-budget-enforcer` | coordination | `tests/contracts/test_opencode_hooks_schema_conformance.py` (+2) |
| `surface-fix-detector` | quality | `tests/unit/test_surface_fix_detector.py` |
| `work-queue-sync-agent` | coordination | `tests/unit/test_codex_guard_layer.py` (+1) |
| `work-queue-sync-todo` | coordination | `tests/unit/test_codex_guard_layer.py` (+1) |

Bajar esta cifra no se hace mejorando el script: se hace en los tests, reemplazando
la constante intermedia por el nombre pasado directo donde se lo usa, o
parametrizando con `pytest.mark.parametrize` (que sí es un `Call`).

## Sesgos declarados de la técnica

- **Conservador:** `assert "hooks/x.sh" in salida` es una verificación real y cae en
  `NAMED_ONLY` — el literal no es argumento de un `Call`. La medición subestima
  antes que inflar.
- **Optimista:** `Path("hooks/x.sh")` cuenta como `EXERCISED` aunque solo construya
  una ruta.
- **La posición `func` no es un argumento:** `{"hooks/x.sh"}.issubset(post)` es una
  aserción de registración, no un ejercicio. Una técnica ingenua que mire todo el
  subárbol del `Call` la cuenta como `EXERCISED`; ésta no.
- Los tests censo (`HOOK_QUALITY_COVERAGE = "census"`) no acreditan a ningún hook en
  particular —los excluye `discover_behavior_tests` a propósito— pero se reportan
  aparte para que no parezcan inexistentes.

## Reutilización, no reimplementación

El script importa de `scripts/hook_quality_audit.py`: `registered_hooks`,
`discover_behavior_tests`, `discover_census_tests`, `_excluded_constant_ids`,
`classify_criticality`, `TEST_ROOTS`. El conjunto `NO_TEST` de acá es **por
construcción** el conjunto de hooks con `behavior_tests` vacío en el manifest, y hay
un test que lo prueba sobre el corpus real
(`test_no_test_set_matches_hook_quality_audit`) en vez de confiar en la lectura del
código. La lista de raíces del corpus se lee de `TEST_ROOTS`, no se copia: cambió dos
veces durante esta misma tarea, y un reporte que la hardcodea declara un corpus que
no es el que midió.

## Evidencia

| Qué | Dónde |
|---|---|
| Instrumento | `scripts/hook_exercise_audit.py` |
| Prueba de portabilidad (invariancia de cwd) | `tests/red_team/portability/test_hook_exercise_audit.py` |
| Test de clasificación (25 casos) | `tests/contracts/test_hook_exercise_audit.py` |

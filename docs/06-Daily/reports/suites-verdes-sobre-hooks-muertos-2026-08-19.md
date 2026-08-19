# Suites verdes sobre hooks muertos — 2026-08-19

## Resumen ejecutivo

De los 17 tests denunciados, **solo una suite mentía**. `test_stash_budget_warn.py`
(7 tests) no alimenta payloads falsos: el hook ni siquiera lee stdin. Su falla es
otra y peor de encontrar — **todos sus fixtures crean 2 o más stashes, y producción
tenía cero en 213 de 334 corridas**. Ese camino sin cobertura era justo donde vivía
un bug: el hook imprimía "BUDGET EXCEEDED" con cero stashes y moría antes de
escribir la fila. `test_skill_post_execution_hook.py` (10 tests) sí mentía como
dice el encargo: inventaba `skill_name`, `tool_count`, `duration_ms` y `tool_issues`,
nombres que el harness no manda — por eso `skill_store.db` quedó en 0 bytes desde
el 6 de mayo con 182 invocaciones registradas.

Resultado: **17 → 15 tests**. Borré 3 (heurística inalcanzable), reescribí 3 contra
el contrato real de los transcripts, agregué 1 que cubre el camino de producción.
El censo general está en `scripts/hook_test_reality_census.py`: de 194 hooks con
suite dedicada, **50 emiten, 36 nunca corrieron por no estar registrados, 9 mueren,
1 nunca ejecuta su cuerpo — y 98 (50,5%) son ceguera del instrumento, no hallazgos**.

## Correcciones a las premisas del encargo

1. **Las rutas no existen.** El encargo dice `tests/unit/test_stash_budget_warn.py`
   y `tests/unit/test_skill_post_execution_hook.py`. Las dos suites viven en
   `tests/integration/`. `ls tests/unit/test_stash_budget_warn.py` → no such file.

2. **`stash-budget-warn` NO alimenta payloads sintéticos.** El encargo afirma que
   ambas suites "le alimentan payloads sintéticos que el harness real nunca manda".
   Falso para esta: el hook no lee stdin en ninguna rama — su entrada es el estado
   de `git stash list`. El test le pasa `input="{}"` que el hook descarta. La
   mentira de esta suite es de *estado*, no de *payload*.

3. **`stash-budget-warn` NO estaba silencioso: emitió en 213 de 334 corridas.**
   El encargo dice "0 filas". Cierto para `stash-budget.jsonl` (el archivo ni
   existe), pero `stderr_bytes > 0` en 213 corridas. Eran banners espurios de
   "BUDGET EXCEEDED" con cero stashes. Contar solo el artefacto declarado del hook
   habría confirmado "muerto"; la telemetría dice "roto y ruidoso".

4. **Los conteos del encargo están bajos.** No 330/176 sino **334/182** al momento
   de medir (y 335/183 veinte minutos después — la telemetría crece en vivo).
   Comando: ver §Evidencia. La diferencia no cambia ninguna conclusión, pero un
   número citado sin recontar es del que lo repite.

5. **Los dos hooks fueron arreglados por el encargo paralelo mientras yo corría.**
   Coordiné como se pidió: no los toqué. Eso cambió el desenlace — con el hook de
   skills ya leyendo `agentType`/`subagent_type`, los tests de escritura a DB pasan
   a ser *arreglables* en vez de *borrables*.

6. **Mi propio censo nació con el bug que venía a medir.** La primera versión contaba
   `exit_code != 0` como rotura y reportaba **38 hooks rotos**. Pero `exit 2` es la
   señal de bloqueo deliberado del schema, y `execution_status: "skipped"` es cuerpo
   nunca ejecutado. Corregido: **9 rotos**. Los 29 de diferencia eran guardas
   funcionando (`protected-config-write-guard`: 115 bloqueos legítimos).

## En qué mienten, test por test

### `tests/integration/test_stash_budget_warn.py`

| Qué asume el test | Qué pasa en producción |
|---|---|
| Fixture con **2 a 5 stashes** `auto-pre-agent-*` / `auto-checkpoint-*` | **0 stashes** en el repo (`git stash list \| wc -l` → 0); 213 de 334 corridas con cero coincidencias |
| Payload: `input="{}"` por stdin | El hook **nunca lee stdin**. Irrelevante en ambos lados. |
| Comportamiento: silencio bajo umbral, warning + JSONL sobre umbral | Con 0 stashes: **banner "BUDGET EXCEEDED" espurio y muerte por ERR trap**, sin fila JSONL |

**La mecánica del bug.** `grep -c` ya imprime `0` y sale 1 cuando no hay coincidencias,
así que el `|| echo "0"` viejo agregaba un **segundo** `0`: `STASH_COUNT` valía la
cadena de dos líneas `"0\n0"`. Entonces `[ "0\n0" -le 3 ]` devuelve **2 (error), no
falso** — el `if` da falso y el guard **cae a través** al banner. Muere después en
`printf "%d"` vía el `trap ERR`, antes del cooldown y antes del JSONL. Verificado:

```
$ /bin/bash -c 'C=$(printf "0\n0"); if [ "$C" -le 3 ] 2>/dev/null; then echo TOOK; else echo FELL-THROUGH; fi'
FELL THROUGH to warning path        # [ returns: 2
```

Ningún test tocaba ese camino porque **ningún fixture tenía cero stashes**.

### `tests/integration/test_skill_post_execution_hook.py`

Payload del test vs. payload real (285 llamadas y 266 resultados de `Agent` en
`~/.claude/projects/-Users-matias-nahuel-amendola-Projects-luum-luum-agent-os/*.jsonl`):

| Campo que lee el test | ¿Lo manda el harness? |
|---|---|
| `skill_name` (nivel raíz) | **No.** No existe en ningún payload. |
| `tool_input.skill` | **No.** Las claves reales son `description, subagent_type, model, prompt, run_in_background`. |
| `tool_response.tool_count` | **No.** Se llama `totalToolUseCount`, y solo en 6 de 266. |
| `tool_response.duration_ms` | **No.** Se llama `totalDurationMs`. |
| `tool_response.tool_issues` | **No existe en absoluto.** |
| `tool_response.status` | **Sí** — el único nombre que el test acertaba. Valores reales: `async_launched` (260) y `completed` (6). |

En producción el hook resolvía `skill_name` vacío y salía en `if [ -z "$SKILL_NAME" ]`
en el 100% de las 182 corridas. De ahí `skill_store.db` en 0 bytes desde el 6 de mayo.

## Qué hice con cada uno y por qué

### `test_stash_budget_warn.py` — 7 → 8

| Test | Decisión | Motivo |
|---|---|---|
| `test_below_threshold_no_warning` | **Se queda** | Prueba comportamiento real y alcanzable. |
| `test_above_threshold_warns_and_writes_jsonl` | **Se queda** | El warning es alcanzable: cualquier sesión que junte >3 auto-stashes. Que hoy no pase no lo vuelve ficción. |
| `test_cooldown_suppresses_second_warning` | **Se queda** | Ídem. |
| `test_after_cooldown_warns_again` | **Se queda** | Ídem. |
| `test_falsification_rubber_stamp...` | **Se queda** | Falsificación explícita, sigue valiendo. |
| `test_custom_threshold_env_var` | **Se queda** | Mecanismo real de operador. |
| `test_killswitch_disables_hook` | **Se queda** | Mecanismo real de operador. |
| `test_zero_matching_stashes_is_silent_and_clean` | **NUEVO** | Cubre el camino de producción (213/334) que no tenía ningún test y donde vivía el bug. |

**Por qué el test nuevo no es relleno para tapar la caída del conteo:** contra el
hook pre-arreglo, **los 7 tests viejos pasan y solo el nuevo falla**. Es la prueba de
que la suite vieja era ciega exactamente ahí.

```
$ .venv/bin/python3 -m pytest $S/test_old.py -q      # hook pre-arreglo reconstruido
FAILED test_zero_matching_stashes_is_silent_and_clean
E  AssertionError: assert 'BUDGET EXCEEDED' not in '...'
1 failed, 7 passed
```

### `test_skill_post_execution_hook.py` — 10 → 7

| Test | Decisión | Motivo |
|---|---|---|
| `test_hook_exits_zero_on_valid_payload` | **Payload arreglado** | Ahora recibe el payload real de los transcripts, no el inventado. |
| `test_hook_exits_zero_on_empty_payload` | **Se queda** | Robustez, independiente del payload. |
| `test_killswitch_exits_immediately` | **Se queda** | Mecanismo real. *(Su assert `not db.exists()` era infalsificable mientras la DB nunca se creaba; con el hook arreglado ya discrimina.)* |
| `test_no_skill_name_exits_zero` | **Payload arreglado + assert nuevo** | Antes mandaba `{"tool_response":{"status":"success"}}`, que ni siquiera pasaba el `case` de fast-path: salía antes de llegar al parser. Ahora manda un payload real con los campos de nombre quitados, y verifica que degrada sin escribir. |
| `test_writes_skill_record_to_db` | **Payload arreglado** | Era **la mentira que sostenía todo**: el único test que probaba la razón de ser del hook, y lo probaba con un payload que el harness no manda. Con el hook ya corregido, pasa contra el contrato real vía `agentType`/`subagent_type`. |
| `test_candidate_writes_proposal_file` | **BORRADO** | La heurística `candidate_for_evolution` es **inalcanzable en producción**: exige `len(tool_issues)>=3` (campo inexistente) o `status in (error\|fail\|failed\|1)` (los únicos valores reales son `async_launched` y `completed`). |
| `test_non_candidate_does_not_write_proposal` | **BORRADO** | Caso negativo de una heurística inalcanzable: verde garantizado, información cero. |
| `test_proposal_contains_discipline_gate_marker` | **BORRADO** | Ídem, y además arrastraba un assert muerto: `assert ... or True`. |
| `test_no_live_skill_md_write_path_exists` | **Se queda intacto** | Estructural sobre el fuente del hook, independiente del payload. Es el discipline gate de ADR-176 y es el test más honesto de la suite. |
| `test_hook_completes_within_200ms` | **Payload arreglado** | Medía la latencia de un camino que nunca corre. Ahora mide el real. |

**Lo que queda abierto y de quién depende:** la heurística de ADR-176 está definida
contra campos que el harness no emite. Reescribir esos 3 tests exige antes redefinir
la heurística contra `totalDurationMs` / `status` reales — decisión de producto de
ADR-176, no de esta tanda. El motivo quedó escrito en el docstring de
`TestDisciplineGate` para que nadie los re-agregue contra payloads inventados.

## Cuántas otras suites tienen esta forma

`scripts/hook_test_reality_census.py` cruza los `behavior_tests` de
`manifests/hook-quality.yaml` contra `hook-timing.jsonl` **vivo + los 7 rotados**.
Solo cuenta los tests que **nombran** al hook: el mapeo del manifiesto es generado y
asocia suites genéricas a decenas de hooks, así que cruzarlo crudo sobrecuenta por
un orden de magnitud.

Población: **194 hooks con suite dedicada.**

### Medible (92 hooks)

| Categoría | N | Qué significa |
|---|---|---|
| `emite_en_produccion` | 50 | Emitió bytes o bloqueó deliberadamente. Sano. |
| `cero_nunca_corrio_sin_registrar` | **36** | **Nunca corrió: no está en `.claude/settings.json`.** |
| `cero_por_error_roto` | **9** | **Corrió y murió** (exit ≠ 0 y ≠ 2, o signal/timeout). |
| `cero_cuerpo_nunca_corrio_skipped` | 1 | Corrió 75 veces, las 75 `skipped`. El cuerpo nunca se ejecutó. |

### Ciego (102 hooks — 50,5% de ceguera)

| Categoría | N | Por qué no se puede clasificar |
|---|---|---|
| `cero_silencioso_indeterminado` | **80** | Corrió, salió 0, nunca emitió bytes. **Desde la telemetría no se distingue "no tenía nada que reportar" (sano) de "parsea mal y se calla" (roto).** Es exactamente el caso de `skill-post-execution-analysis`, que aparece acá. |
| `cero_registrado_sin_telemetria` | 18 | Registrado pero sin filas: matcher que nunca matcheó vs. wrapper de timing no aplicado. No distinguible. |

**Los tres ceros del encargo, separados:**
- **roto** → 9 (`cero_por_error_roto`), con los peores: `agent-prelaunch` (165 muertes
  en 188 corridas, 17 tests verdes encima), `bash-hot-path-dispatcher` (98/8996),
  `context-watchdog` (34/10666).
- **nada que reportar** → **no lo puedo afirmar de ningún hook**. Se disuelve dentro
  de los 80 `cero_silencioso_indeterminado`. Separarlo exige saber el artefacto
  declarado de cada hook, dato que no está en el manifiesto.
- **nunca corrió** → 36 sin registrar + 18 registrados sin telemetría = 54.

**La cifra que contesta la pregunta del operador:** hay **36 hooks con 0 corridas,
sin registrar, y con tests verdes encima** — 199 tests en total, entre ellos
`destructive-git-blocker` (27 tests), `rate-limiter` (16), `auto-verify` (16),
`destructive-rm-blocker` (14), `auto-refine` (13), `direct-main-guard` (10). Son la
misma forma que las dos suites auditadas, a escala 18×. No los toqué: el encargo
pide medir el tamaño del problema, no arreglarlo.

*(Ojo con `rate-limiter`: `rules/rate-limiting.md` ya documenta que no está
registrado. El censo lo confirma de forma independiente — 16 tests verdes sobre un
hook con 0 corridas.)*

## Evidencia

```bash
# Corridas reales por hook (VIVO + rotados). Contar solo el vivo da falsos "nunca disparó".
{ cat .cognitive-os/metrics/hook-timing.jsonl; \
  for g in .cognitive-os/metrics/.archive/hook-timing-*.jsonl.gz; do gzcat "$g"; done; } \
| .venv/bin/python3 -c "
import sys, json, collections
c = collections.Counter()
for line in sys.stdin:
    try: c[json.loads(line).get('hook','')] += 1
    except ValueError: pass
for h in ('stash-budget-warn', 'skill-post-execution-analysis'): print(h, c[h])
"
# -> stash-budget-warn 334 / skill-post-execution-analysis 182  (2026-08-19 18:10)

# Censo completo (read-only; 0 sin hallazgos / 1 hallazgos / 2 error)
.venv/bin/python3 scripts/hook_test_reality_census.py
.venv/bin/python3 scripts/hook_test_reality_census.py --json

# Las dos suites
COS_ALLOW_PROTECTED_CONFIG_WRITE=1 .venv/bin/python3 -m pytest \
  tests/integration/test_stash_budget_warn.py \
  tests/integration/test_skill_post_execution_hook.py -q      # 15 passed

# Contrato real del payload de Agent
cd ~/.claude/projects/-Users-matias-nahuel-amendola-Projects-luum-luum-agent-os
# → tool_input: description, subagent_type, model, prompt, run_in_background
# → tool_response: status, agentId, isAsync, ..., totalDurationMs, totalToolUseCount
# → status: async_launched (260) | completed (6)
```

## Colisión con el encargo paralelo — decisión pendiente del orquestador

El encargo paralelo, además de arreglar los dos hooks, creó **dos suites nuevas**
que cubren los mismos hooks desde otra carpeta:

| Archivo | Tests | Solapamiento con lo que auditué |
|---|---|---|
| `tests/hooks/test_stash_budget_warn.py` | 7 | `test_zero_stashes_is_silent` es el mismo caso que mi `test_zero_matching_stashes_is_silent_and_clean`; cooldown y killswitch también duplican. |
| `tests/hooks/test_skill_post_execution_analysis.py` | 9 | `test_real_agent_payload_is_recorded` duplica mi `test_writes_skill_record_to_db` ya corregido; killswitch y discipline gate también. |

Quedan **31 tests sobre 2 hooks** repartidos en 4 archivos: 15 en
`tests/integration/` (los que auditué y corregí) y 16 en `tests/hooks/` (nuevos).
**No borré ninguno de los dos lados**: elegir cuál sobrevive es decisión del
orquestador, y borrar el trabajo de una sesión concurrente sin acordarlo es
exactamente lo que la norma de escritores concurrentes prohíbe.

Recomendación, con el motivo: las suites de `tests/hooks/` cubren casos que las
mías no (`test_unrelated_stashes_do_not_count`, `test_skill_tool_payload_is_recorded`,
`test_repeated_executions_accumulate`, parametrización de `never_blocks`). Si se
consolida en una sola, la de `tests/hooks/` es la base más completa — pero hay que
trasladarle antes lo que solo está del lado mío: la **provenance del payload**
documentada contra los 285 payloads reales, y el motivo escrito de por qué la
heurística `candidate_for_evolution` es inalcanzable. Sin eso se pierde justamente
la parte que evita que alguien vuelva a inventar los nombres de los campos.

## Lo que NO hice y por qué

- **No arreglé ninguno de los dos hooks.** Los tenía el encargo paralelo y los
  arregló mientras yo medía. Solo verifiqué su afirmación de que el guard "caía a
  través" al banner — es correcta, y yo había supuesto mal (creía que abortaba).
- **No arreglé los 36 hooks sin registrar ni sus 199 tests.** El encargo pide el
  tamaño del problema. Registrar un guard es decisión de operador, no de auditoría:
  `destructive-git-blocker` con 27 tests verdes y 0 corridas es una decisión
  pendiente, no un olvido.
- **No borré los 7 tests de stash.** Borrarlos habría sido el verde barato: prueban
  un camino alcanzable, y el problema era la *falta* de un caso, no su falsedad.
- **No usé `skip` ni `xfail` en ningún lado.**
- **No derivé el payload nuevo del parser del hook.** Salió de 285 llamadas reales
  en los transcripts. Copiarlo del hook habría hecho que el test siguiera las
  suposiciones del hook — el error que el encargo prohíbe explícitamente.
- **No separé "nada que reportar" de "roto silencioso" en los 80 indeterminados.**
  Requiere el artefacto declarado de cada hook, que no está en el manifiesto.
  Preferí publicar la ceguera antes que un número lindo: es lo que
  `cos_lib.measurement.Census` existe para impedir.

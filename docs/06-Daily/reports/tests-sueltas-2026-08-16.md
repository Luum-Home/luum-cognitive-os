# Nueve tests sueltos: código mal vs. premisa muerta

Fecha de cierre: 2026-08-18. Encargo fechado 2026-08-16.

Intérprete: `.venv/bin/python` (el `python3` del PATH no tiene pytest).
Todas las corridas con `-p no:randomly`.

## Tabla

| Test | Veredicto | Estado |
|---|---|---|
| `tests/unit/test_check_mcp_servers.py::test_main_json_output_is_valid_json` | test mal (aislamiento incompleto) | arreglado, `e85f41c2b` |
| `tests/unit/test_file_mutation_queue.py::TestStress::test_10_threads_no_race` | **código mal — carrera real** | arreglado, `e7be5e5dd` |
| `tests/unit/test_cos_generate_notices.py::TestManifestSchema::test_all_statuses_are_known` | premisa muerta + vocabulario sin cablear | arreglado, `5e0b0d6f8` |
| `tests/behavior/test_self_improvement.py::TestMockMetricsData::test_kpi_trigger_produces_snapshot` | **código mal — el hook emite JSON inválido** | diff propuesto, sin aplicar (`hooks/**`) |
| `tests/unit/test_skill_and_rule_runtime_contracts.py::test_runtime_rules_have_loader_metadata_or_explicit_trigger` | código mal (dos reglas nuevas sin el marcador) | diff propuesto, sin aplicar (`rules/**`) |
| `tests/contracts/test_core_extensions_split.py::test_aspirational_audit_reports_zero_active_dormant_debt` | deuda real, dueño ajeno | no cerrado, causa identificada |
| `tests/contracts/test_ram_ceiling.py::test_so_vitals_reports_disk_under_ceiling` | techo real excedido | no cerrado, decisión del operador |
| `tests/contracts/test_acc_pipeline_contract.py::test_repository_acc_pipeline_generates_report` | **no falla** | verde en cada corrida |
| `tests/integration/test_decision_triage_real_files.py::TestRealFilesIntegration` | **no falla** | verde en cada corrida |

No hay familia común. Son nueve encargos chicos, y dos de ellos ni siquiera
estaban rotos.

---

## 1. `test_main_json_output_is_valid_json` — test mal

El nombre dice "JSON válido" y el JSON siempre fue válido. La aserción que
rompía era la última, `exit_code == 0`, con `assert 1 == 0`.

`find_mcp_configs()` suma cuatro fuentes. El test parcheaba tres
(`MCP_DIR`, `CLAUDE_DIR`, `PLUGINS_CACHE`) y dejaba sin parchear `CODEX_CONFIG`
y `PROJECT_ROOT`, agregadas en `11ced4a14`. Resultado: el test leía el
`~/.codex/config.toml` de la máquina y el repo real.

```
$ .venv/bin/python -c "...find_mcp_configs(); check_server(...)"
ERROR: aguara            (binario mcp-aguara no encontrado)
ERROR: computer-use      (~/.codex/config.toml)
ERROR: pencil            (~/.codex/config.toml)
ERROR: projects-tracker  (sin command)
ERROR: context7#2        (sin command)
total servers: 11        ← el test escribió 1
```

`main()` devuelve `1` si algún servidor da ERROR — comportamiento correcto.
Los otros cuatro tests del mismo archivo (líneas 111, 131, 155, 181) ya
parcheaban las dos constantes. A este se le olvidó. Se agregaron los dos
parches; no se tocó el productor.

No hace falta renombrarlo: sigue verificando lo mismo, ahora sin depender de
qué MCPs tenga instalados quien lo corre.

## 2. `test_10_threads_no_race` — carrera real, no ruido de scheduling

El encargo pedía tasa, no veredicto de una corrida. La primera corrida dio
verde; con repetición apareció.

**Antes del arreglo, 16 corridas: 3 rojas (~19%).**

```
$ for i in $(seq 1 10); do .venv/bin/python -m pytest \
    "tests/unit/test_file_mutation_queue.py::TestStress::test_10_threads_no_race" \
    -p no:randomly -q --tb=no | tail -1; done
passed passed passed passed FAILED FAILED passed passed passed FAILED
```

Los valores obtenidos fueron `'6'`, `'9'` y `'8'` contra `'10'` esperado.
Perder cuatro incrementos de diez no lo explica el planificador: eso es
pérdida de updates.

Causa, en `cos_lib/file_mutation_queue.py`, la limpieza que era
`_try_cleanup()`:

```python
if not lock.locked():
    del self._locks[canonical]
```

Un hilo bloqueado dentro de `acquire()` ya tiene la referencia al lock pero
todavía no lo marca como tomado. El hilo que suelta lo ve libre y expulsa la
entrada. El siguiente que llega no encuentra el path, crea un lock **nuevo**,
y entra a la sección crítica en paralelo con el que seguía esperando el
viejo. Dos locks para el mismo archivo.

Arreglo: cada entrada lleva un contador de usuarios —tenedor más
esperadores— que se incrementa bajo `_meta_lock` **antes** de `acquire()`, y
la entrada se expulsa sólo cuando el contador llega a cero y sigue siendo la
misma entrada.

**Después del arreglo: 12 de 12 verdes**, y los 16 tests del archivo pasan.

Doce corridas verdes no prueban ausencia de carrera; prueban que la carrera
que se reproducía a ~19% dejó de reproducirse. El argumento fuerte es el
mecanismo, no la tasa.

## 3. `test_all_statuses_are_known` — premisa muerta, y un literal duplicado

El manifiesto `manifests/external-tool-licenses.yaml` incorporó
`INVENTORIED-PENDING-REVIEW` en `f76c3c2c5`, documentado en su encabezado
como lo contrario de un veredicto: la adopción está en la lista con forma,
archivos y fecha, y nadie evaluó su postura legal.

El verde barato era agregar el string al set del test. No se hizo, porque el
literal duplicado **era** el defecto: el generador tampoco conocía el estado
y lo renderizaba con el fallback de backticks. Un estado que el manifiesto usa
y el generador no sabe dibujar es exactamente la deriva que ese test debe
atrapar, y con dos listas separadas no la atrapaba.

El vocabulario quedó una sola vez, en `cos-generate-notices.KNOWN_STATUSES`,
el estado tiene su badge, y el test lee del generador.

Umbral movido: ninguno. Se movió el **dueño** del vocabulario.
`NOTICE.md` y `THIRD_PARTY_LICENSES.txt` regenerados; el diff son las cuatro
líneas de Status de Aider, DSPy, LightRAG y Letta. Verificado que antes del
cambio no había deriva (`git show HEAD:scripts/cos-generate-notices.py`
corrido con `--check` da 0 DRIFT), así que la regeneración no arrastra nada
ajeno.

## 4. `test_kpi_trigger_produces_snapshot` — el hook emite JSON inválido

Éste sí es el `JSONDecodeError`. La línea escrita en `kpi-history.jsonl`:

```json
{"timestamp":"2026-08-18T13:20:21Z","first_pass_success_rate":0,001.0,...}
```

`0,001.0` no es un número: es `0,00` pegado a `1.0`.

`packages/skill-governance/hooks/kpi-trigger.sh:61`:

```bash
FIRST_PASS_SUCCESS=$(printf '%.2f' "$(echo "scale=4; $SUCCESSFUL_TASKS / $TOTAL_TASKS" | bc)" 2>/dev/null || echo "1.0")
```

Dos defectos encadenados:

1. `bc` con `scale=4` devuelve `.7000` — sin cero inicial. `printf` del bash
   que resuelve el PATH lo rechaza (`printf: .7000: número inválido`) y emite
   `0,00` con coma.
2. `cmd || echo fallback` cuando `cmd` **ya escribió** en stdout no reemplaza:
   concatena. De ahí `0,00` + `1.0`.

Reproducción:

```bash
$ bash -c 'printf "%.2f" "$(echo "scale=4; 7/10" | bc)" || echo "1.0"; echo'
bash: printf: .7000: número inválido
0,001.0
```

Latente además: `ARCH_COMPLIANCE` (línea 82) sale de `bc` sin normalizar, así
que `1 - (2/10)` da `.80` y produce `"architecture_compliance":.80` — también
JSON inválido. `AVG_ITERATIONS` (línea 99) tiene la misma forma.

`hooks/**` es config protegida. **Diff propuesto, no aplicado:**

```diff
--- a/packages/skill-governance/hooks/kpi-trigger.sh
+++ b/packages/skill-governance/hooks/kpi-trigger.sh
+# bc devuelve ".7000" sin cero inicial y printf es sensible al locale: los dos
+# producen JSON invalido rio abajo. Normalizar una vez, no en cada uso.
+_num() {  # _num <valor-de-bc> <default>
+  local raw="${1:-}" def="$2" out
+  out=$(LC_ALL=C printf '%.2f' "${raw:-0}" 2>/dev/null) || out="$def"
+  printf '%s' "$out"
+}
@@
-      FIRST_PASS_SUCCESS=$(printf '%.2f' "$(echo "scale=4; $SUCCESSFUL_TASKS / $TOTAL_TASKS" | bc 2>/dev/null)" 2>/dev/null || echo "1.0")
+      FIRST_PASS_SUCCESS=$(_num "$(echo "scale=4; $SUCCESSFUL_TASKS / $TOTAL_TASKS" | bc 2>/dev/null)" "1.0")
@@
-  ARCH_COMPLIANCE=$(echo "scale=2; 1 - ($ARCH_VIOLATIONS / $TOTAL_TASKS)" | bc 2>/dev/null || echo "0.8")
+  ARCH_COMPLIANCE=$(_num "$(echo "scale=2; 1 - ($ARCH_VIOLATIONS / $TOTAL_TASKS)" | bc 2>/dev/null)" "0.80")
@@
-      AVG_ITERATIONS=$(echo "scale=1; $TOTAL_ITERS / $REFINE_COUNT" | bc 2>/dev/null || echo "1")
+      AVG_ITERATIONS=$(_num "$(echo "scale=1; $TOTAL_ITERS / $REFINE_COUNT" | bc 2>/dev/null)" "1.00")
```

El test no hay que tocarlo: fija lo correcto y encontró un defecto de verdad.

## 5. `test_runtime_rules_have_loader_metadata_or_explicit_trigger` — dos reglas nuevas sin marcador

```
failures = ['rules/codebase-memory-directive.md: missing tier metadata and contextual trigger',
            'rules/encargo-refutable.md: missing tier metadata and contextual trigger']
```

El contrato pide `<!-- TIER:` o la cadena literal `Contextual Trigger`. Los
dos casos no son el mismo caso:

```
$ grep -n '^## ' rules/codebase-memory-directive.md | tail -3
62:## Contextual trigger          ← existe, con 't' minúscula
$ grep -n '^## ' rules/encargo-refutable.md | tail -3
70:## 4. Delivery
81:## 5. Verification
94:## 6. Por que `os-only` hoy, y que haria falta para que sea `both`
```

El primero **tiene** la sección y falla por una mayúscula: el contrato hace
`"Contextual Trigger" in text`, sensible a caso, sobre un encabezado escrito
por una persona. El segundo no la tiene en absoluto.

Premisa viva: el contrato es el de siempre y dos reglas incorporadas en las
últimas 48 h entraron sin cumplirlo. No es un test que fije el estado
anterior.

Config protegida. **Diffs propuestos, no aplicados:**

1. En `codebase-memory-directive.md`, línea 62 — capitalizar la `t`:
   `## Contextual trigger` → `## Contextual Trigger`.
2. En `encargo-refutable.md`, agregar al final una sección
   `## Contextual Trigger` con el disparador natural: antes de redactar el
   prompt de un sub-agente, repartir trabajo entre varios agentes, o pasarle
   a otro los hallazgos de un tercero.

Alternativa para el primero, si el operador prefiere: aflojar el contrato a
comparación insensible a caso en
`tests/unit/test_skill_and_rule_runtime_contracts.py`. No la tomé porque ese
archivo no es config protegida y era justamente la salida fácil. Hoy el
contrato dice "esta cadena exacta" y el resto de las reglas la cumplen así;
cambiarlo es una decisión sobre la convención, no sobre este rojo.

## 6. `test_aspirational_audit_reports_zero_active_dormant_debt` — deuda real, no es mía

El encargo pedía averiguar qué movió el ratio antes de tocar el umbral. Se
averiguó, y no se tocó ningún umbral.

En el árbol de trabajo el ratio es **0.0**. El test corre sobre un snapshot
de `git archive HEAD`, y ahí:

```
total 939  ratio 0.0021  counts {'METADATA': 91, 'ON_DEMAND': 842, 'REAL': 4, 'DORMANT': 2}
worst_offenders: ["scripts/home-path-family-mutation-check.sh",
                  "scripts/probe-hook-git-adjacency.sh"]
```

Los dos scripts están commiteados. Sus pruebas pareadas existen en el disco
—`tests/red_team/portability/test_probe-hook-git-adjacency.py` y
`test_home-path-family-mutation-check.py`— pero están **sin trackear**:

```
$ git ls-files tests/red_team/portability/ | grep -E "probe-hook-git-adjacency|home-path-family"
(vacío)
$ git check-ignore -v tests/red_team/portability/test_probe-hook-git-adjacency.py
rc=1   ← no está ignorado, simplemente no se commiteó
```

El clasificador promueve DORMANT → ON_DEMAND cuando hay test que lo cubra.
En el árbol local lo ve; en el snapshot trackeado no existe. Deuda real:
una primitiva declarada y no cableada *en el árbol que se publica*.

**No se cerró a propósito.** `tests/red_team/portability/` lo está trabajando
otro agente (29 archivos sin trackear ahí, más un `M`). Commitear sus
archivos sería mezclar el trabajo de otra sesión en mi commit. La acción
correcta es que ese agente los commitee; el ratio vuelve a 0.0 solo.

El encargo decía 0.0032; hoy es 0.0021. La diferencia es que un tercer
offender ya se cerró entre que se escribió el encargo y esta corrida.

## 7. `test_so_vitals_reports_disk_under_ceiling` — el techo está excedido de verdad

```
AssertionError: .cognitive-os/ disk usage 411.8 MiB exceeds ceiling 400 MiB
```

Reparto:

```
$ du -sm .cognitive-os/* | sort -rn | head
84 checkpoints   69 metrics   47 artifacts   42 snapshots   41 reports
39 tasks         28 cache     21 runtime     15 external-source-cache
```

`scripts/state_retention_audit.py` da `findings=0`: cada superficie está
dentro de su propio tope (checkpoints 84 contra 120, snapshots 42 contra 80).
El problema es de suma, no de una superficie desbordada: la suma de los topes
por superficie excede el techo global de 400 MiB, así que la política puede
estar toda en verde y el techo igual romperse.

Lo dejo sin cerrar. Las dos salidas son del operador y ninguna es mía:

- borrar estado suyo (checkpoints, snapshots, caché) — es telemetría y son
  puntos de recuperación;
- reconciliar `manifests/state-retention.yaml` para que la suma de
  `max_total_mib` quepa en el techo.

Subir `COS_VITALS_DISK_CEILING_MIB` sería el verde barato exacto: apaga el
rojo sin recuperar un byte.

Hallazgo lateral: el docstring de `tests/contracts/test_ram_ceiling.py:11`
dice `default 200` y el código en la línea 28 dice `400`. Contradicción de
documentación, candidata a la ledger de verdad documental.

## 8 y 9. Los dos que no fallan

`test_repository_acc_pipeline_generates_report` y
`TestRealFilesIntegration::test_source_files_not_...` dieron verde en cada
corrida, sueltos y en lote. No los toqué.

---

## Qué del encargo era falso

1. **El `JSONDecodeError` no era de `test_check_mcp_servers`.** Ahí el JSON
   siempre fue válido; lo que rompía era `exit_code == 0`. El
   `JSONDecodeError` real es de `test_kpi_trigger_produces_snapshot`. El
   agrupamiento por mensaje mezcló, como el encargo mismo advertía.

2. **El `PermissionError` no apareció.** Ninguno de los nueve tests falló
   escribiendo bajo el repo, ni con guard ni sin él. La hipótesis de "guards
   demasiado anchos" no tiene caso que la sostenga en este lote. O el
   agrupamiento lo trajo de otro lote, o el test que lo producía ya se
   arregló.

3. **El ratio de dormant debt es 0.0021, no 0.0032.** Dos offenders, no tres.

4. **Son nueve tests, pero siete fallaban.** Dos están verdes y estables.

5. **`test_10_threads_no_race` no era el candidato a falso positivo.** El
   encargo lo señalaba como el que podía fallar por scheduling; resultó ser
   el defecto más duro del lote. Al revés de lo previsto: la advertencia
   correcta no era "cuidado, puede ser ruido" sino "cuidado, puede pasar y
   tapar la carrera" — que es lo que hizo en mi primera corrida.

6. **`timeout` sí existe** como builtin en zsh; lo que no hay es el binario
   GNU `timeout`. Irrelevante para el resultado: no lo necesité.

## Umbrales movidos

Ninguno. Ni `dormant_aspirational_ratio`, ni `COS_VITALS_DISK_CEILING_MIB`,
ni el set de estados permitidos. El único cambio con forma de lista fue mover
el vocabulario de estados del test al generador, que es cablearlo, no
exceptuarlo.

## Comandos para reverificar

```bash
V=.venv/bin/python

# arreglados
$V -m pytest tests/unit/test_check_mcp_servers.py \
             tests/unit/test_cos_generate_notices.py \
             tests/unit/test_file_mutation_queue.py -p no:randomly -q

# tasa de la carrera (esperado: 0 rojas)
for i in $(seq 1 12); do $V -m pytest \
  "tests/unit/test_file_mutation_queue.py::TestStress::test_10_threads_no_race" \
  -p no:randomly -q --tb=no | tail -1; done

# deuda dormant sobre el arbol trackeado
SNAP=$(mktemp -d); git archive --format=tar HEAD | tar -x -C "$SNAP"
$V scripts/aspirational_audit.py --json --project-root "$SNAP"

# JSON del hook de KPI
bash -c 'printf "%.2f" "$(echo "scale=4; 7/10" | bc)" || echo "1.0"; echo'

# techo de disco
du -sm .cognitive-os/* | sort -rn | head
$V scripts/state_retention_audit.py
```

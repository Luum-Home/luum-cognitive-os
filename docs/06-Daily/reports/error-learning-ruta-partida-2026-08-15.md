# `error-learning.jsonl` — la ruta partida en dos

**Fecha:** 2026-08-15
**Alcance:** censo de escritores/lectores, unificación de ruta, guarda de regresión.
**Estado:** arreglado el escritor divergente; el archivo huérfano queda en su lugar,
documentado; la migración de sus filas queda como decisión del operador.

---

## 1. El síntoma

Dos archivos con el mismo nombre, en directorios distintos:

```bash
find . -name 'error-learning.jsonl' -not -path './.git/*' \
  | while read f; do echo "$(wc -l < "$f") $f"; done
```

```
102 ./.cognitive-os/error-learning.jsonl        ← ningún lector
 11 ./.cognitive-os/metrics/error-learning.jsonl ← todos los lectores
```

Ninguna búsqueda por nombre muestra la partición: los dos archivos se llaman
igual, así que `find`, `ls` y la memoria del que lo escribió dicen "ahí está el
log de errores" y los dos tienen razón.

---

## 2. Censo de escritores y lectores

El comando, **sin filtros de extensión** — ocho ejecutables de este repo son
kebab-case sin extensión (`bin/cos-errors`, `bin/cos-test`, …) y un
`--include='*.py'` los borra del censo:

```bash
git grep -n --untracked 'error-learning\.jsonl' -- bin cos_lib hooks mcp-server packages scripts cmd
```

**Medido 2026-08-15:**

| Métrica | Valor | Comando |
|---|---|---|
| Menciones del nombre en código ejecutable | 69 | `git grep -c --untracked 'error-learning\.jsonl' -- bin cos_lib hooks mcp-server packages scripts cmd` |
| Archivos que la referencian (incluye `.md` de skills) | 36 | idem, `git grep -ln … \| wc -l` |
| Archivos **de código** (sin `.md`, sin `_test.go`) | 26 | idem + `grep -v '\.md$'` |
| Appenders reales confirmados | 3 | ver abajo |

### Appenders (los únicos que escriben)

```bash
git grep -n --untracked -E '(safe_jsonl_append "\$ERROR|path\.open\("a"\))' \
  -- bin cos_lib hooks packages scripts | grep -iE 'error-learning|ERROR_LOG|ERROR_LEARNING'
```

| Escritor | Ruta destino (antes del arreglo) | Estado |
|---|---|---|
| `hooks/error-learning.sh:98` | `$METRICS_DIR/error-learning.jsonl` | canónica |
| `hooks/error-pipeline.sh:234` | `$METRICS_DIR/error-learning.jsonl` | canónica |
| `cos_lib/evolve_task_queue.py:113` | `.cognitive-os/error-learning.jsonl` | **divergente** |

### Lectores (los que consumen la canónica)

Python: `cos_lib/singularity.py`, `cos_lib/kpi_collector.py`,
`cos_lib/learning_pipeline.py`, `cos_lib/self_improvement.py`,
`cos_lib/governed_self_improvement.py`, `cos_lib/feedback_consumer.py`,
`cos_lib/consumer_improvement_proposals.py`, `cos_lib/error_insights.py`,
`packages/verification-audit/lib/error_classifier.py`,
`packages/infra-lifecycle/lib/homeostasis.py`,
`packages/infra-lifecycle/lib/symbiosis_monitor.py`, `mcp-server/cos_mcp.py`.

Bash: `hooks/_lib/singularity-suggestion.sh`, `hooks/auto-repair-dispatcher.sh`,
`hooks/conversation-capture.sh`, `hooks/error-pattern-detector.sh`,
`hooks/session-knowledge-extractor.sh`, `hooks/session-learning.sh`,
`hooks/skill-post-execution-analysis.sh`, `packages/engram-sync/hooks/memu-sync.sh`,
`packages/skill-governance/hooks/kpi-trigger.sh`.

Ejecutable sin extensión: `bin/cos-errors`.

Manifiestos y contratos que la declaran: `manifests/primitive-contracts.yaml`
(3 entradas), `manifests/primitive-lifecycle.yaml` (4), `manifests/agent-training-harness.yaml`.

**Lectores del huérfano `.cognitive-os/error-learning.jsonl`: cero.**

```bash
git grep -n --untracked '\.cognitive-os/error-learning\.jsonl' -- bin cos_lib hooks mcp-server packages scripts cmd
# única coincidencia (antes del arreglo): cos_lib/evolve_task_queue.py:27
```

Antes de concluir "no hay lector" se descartó el clásico *"todavía no
commitearon lo que lo usa"*: el `git grep` corre con `--untracked`, y
`cos_lib/singularity.py:275` —el único lector que prueba dos ubicaciones— apunta a
`<root>/metrics` y `<root>/.cognitive-os/metrics`, nunca a `.cognitive-os/` pelado.

---

## 3. Cuál es la canónica, y por qué

**`.cognitive-os/metrics/error-learning.jsonl`.**

El voto no es por cantidad de filas sino por quién la lee: 26 archivos de código
la referencian y 21 de ellos la consumen. El de 102 filas tiene cero lectores —
eso no es una interfaz, es un log privado con nombre prestado.

Hay un segundo argumento, más fuerte, que descarta la opción contraria
(apuntar los lectores al archivo de 102 filas): **los esquemas son incompatibles.**

```bash
python3 - <<'PY'
import json, collections
for p in ('.cognitive-os/error-learning.jsonl', '.cognitive-os/metrics/error-learning.jsonl'):
    c = collections.Counter()
    for line in open(p):
        if line.strip():
            c[','.join(sorted(json.loads(line)))] += 1
    print(p, dict(c))
PY
```

```
.cognitive-os/error-learning.jsonl          {'context,message,source,ts': 102}
.cognitive-os/metrics/error-learning.jsonl  {'command,exit_code,fingerprint,service,timestamp,timestamp_epoch,type': 11}
```

Las 102 filas no tienen `type`, no tienen `service` y no tienen `timestamp_epoch`
— los tres campos por los que agrupa y filtra `cos_lib/singularity.py:283-290`.
Redirigir los lectores a ese archivo les daría 102 filas y cero eventos.

---

## 4. La pregunta que decide: ¿el escritor producía filas útiles?

**No, y por un motivo distinto del campo fantasma.**

Las 102 filas del huérfano son **una sola condición, disparada por un test**:

```bash
python3 -c "
import json, collections
m = collections.Counter(json.loads(l)['message'][:60] for l in open('.cognitive-os/error-learning.jsonl'))
print(m.most_common())"
```

```
[("Evolve queue at capacity (50 pending). Proposal 'Overflow pr", 102)]
```

`'Overflow proposal'` es el título literal del fixture de
`tests/unit/test_evolve_task_queue.py:129`. El test usaba una DB en `tmp_path`,
pero `_log_error_learning` resolvía la ruta contra una constante de módulo
(`REPO_ROOT`, fijada en import time), así que **cada corrida del test apendaba
una fila a la telemetría real del repo**. 102 filas = 102 corridas del test,
entre 2026-05-11 y 2026-08-15 (pico de 32 el 2026-07-18).

Eventos reales de operador en el huérfano: **0**.

### ¿Tiene el mismo defecto de campo fantasma?

No. `hooks/error-learning.sh` fallaba por leer `.exit_code`, un campo que el
harness nunca manda (9 filas en 5.335 corridas). `cos_lib/evolve_task_queue.py`
no lee nada del harness: su defecto es **ruta divergente + fuga de test a
producción**. Son dos bugs distintos con el mismo síntoma (archivo casi vacío),
y por eso unificar rutas acá no junta dos caños rotos: el caño del evolve queue
nunca se saturó en producción — sus 102 filas son sintéticas.

---

## 5. El arreglo

### `cos_lib/evolve_task_queue.py`

1. La constante de módulo `ERROR_LEARNING_PATH` (fijada en import time contra
   este checkout) se reemplaza por `error_learning_path()`, que resuelve **en
   tiempo de llamada** vía `cos_lib.paths.runtime_project_root()` y apunta a
   `.cognitive-os/metrics/error-learning.jsonl`. Un test que setea
   `COGNITIVE_OS_PROJECT_DIR` escribe en su propio árbol.
2. El registro pasa al esquema que los lectores consumen: `timestamp`,
   `timestamp_epoch`, `type` (`QUEUE_CAPACITY`), `service` (`evolve-queue`),
   `fingerprint`, `command`, más `message`/`context` para trazabilidad.

Sobre el `type`: se eligió `QUEUE_CAPACITY` y **no** reusar `RATE_LIMIT` —que ya
está en el `_TYPE_MAP` del clasificador— porque son conceptos distintos y
unificarlos ensuciaría los KPIs de rate limit. La contra es que
`error_classifier` lo clasifica como `unknown`; una categoría desconocida es
preferible a una etiqueta equivocada.

### `tests/unit/test_evolve_task_queue.py`

El fixture `queue` repunta `COGNITIVE_OS_PROJECT_DIR` a `tmp_path` (la fuga
queda cortada), y el test del cap ahora verifica que la fila aterriza en la ruta
canónica, que **no** aparece el hermano no leído, y que trae los campos por los
que agrupan los lectores.

### `tests/audit/test_error_learning_single_path.py` (nuevo)

Cuatro aserciones, todas con guarda de población:

| Test | Qué falla | Guarda de población |
|---|---|---|
| `test_every_error_learning_path_literal_is_canonical` | un literal `.cognitive-os/…/error-learning.jsonl` sin `metrics` en el medio | < 10 menciones = ERROR, no verde |
| `test_canonical_path_has_readers` | los consumidores desaparecieron | < 8 archivos = ERROR |
| `test_no_error_learning_file_outside_metrics_receives_new_rows` | un segundo archivo con filas posteriores al 2026-08-16 | 0 archivos en disco = ERROR |
| `test_evolve_queue_writer_targets_canonical_path` | el escritor vuelve a apuntar afuera | ejecuta el resolver, no lo lee |

El scan usa `git grep --untracked`: un escritor nuevo es un archivo untracked
hasta que se commitea, y una guarda que solo mira el índice lo deja pasar
justo hasta el momento en que aterriza.

**Prueba de que la guarda muerde** (no es teatro):

```bash
printf '#!/usr/bin/env python3\nP = ".cognitive-os/error-learning.jsonl"\n' > scripts/_mutation_probe_tmp.py
python3 tests/audit/test_error_learning_single_path.py; echo "exit=$?"
#   NON-CANONICAL PATHS:
#     scripts/_mutation_probe_tmp.py:2: P = ".cognitive-os/error-learning.jsonl"
#   exit=1
rm scripts/_mutation_probe_tmp.py
python3 tests/audit/test_error_learning_single_path.py; echo "exit=$?"
#   all path literals resolve under metrics/ — single path holds
#   exit=0
```

Verificación:

```bash
.venv/bin/pytest tests/audit/test_error_learning_single_path.py tests/unit/test_evolve_task_queue.py -q
# 28 passed
```

---

## 6. Qué queda para decisión del operador

**Las 102 filas históricas no se migraron.** Escribir en
`.cognitive-os/metrics/*.jsonl` toca telemetría del operador y evidencia de una
auditoría en curso. El script queda listo, **read-only por default**:

```bash
python3 scripts/migrate_error_learning_orphan.py          # inspección (no escribe)
python3 scripts/migrate_error_learning_orphan.py --json   # salida parseable
python3 scripts/migrate_error_learning_orphan.py --apply  # sólo el operador
```

Salida al 2026-08-15 (exit 1 = hay hallazgos):

```
orphan     : .cognitive-os/error-learning.jsonl — 102 rows
canonical  : .cognitive-os/metrics/error-learning.jsonl — 11 rows
date range : 2026-05-11 → 2026-08-15
test bleed : 102 rows (unit-test fixture)
real events: 0 rows
verdict    : DO_NOT_MIGRATE
```

**Recomendación: no migrar.** Las 102 filas son bleed de un unit test; meterlas
en la canónica inyectaría 102 eventos de saturación sintéticos en la telemetría
y ensuciaría cualquier análisis de patrones de error. Con `--apply` el script
migra 0 filas por ese motivo y lo dice; `--include-test-bleed` fuerza el
override si el operador decide lo contrario.

**El archivo huérfano no se borra.** Qué es y de cuándo: es el log privado de
`cos_lib.evolve_task_queue`, escrito entre 2026-05-11 y 2026-08-15, 102 filas,
todas la misma condición (`Evolve queue at capacity`) disparada por
`tests/unit/test_evolve_task_queue.py::TestQueueCap`. Es la evidencia de una
fuga de test a producción de tres meses. Ambos archivos están en `.gitignore`
(`.gitignore:8` → `.cognitive-os/*`), así que ninguno es artefacto versionado.

### El verde barato que se evitó

Borrar el huérfano y declarar el problema resuelto dejaba una sola ruta, el test
en verde y **cero aprendizaje nuevo**: el escritor habría seguido apuntando
afuera y recreando el archivo en la próxima corrida. Y apuntar los 21 lectores al
archivo de 102 filas les habría dado un esquema que no pueden parsear (§3).

---

## 7. Hallazgo colateral — 3 tests rojos que no son de este lote

```bash
.venv/bin/pytest tests/unit/test_error_learning_behavior.py -q
# 3 failed, 5 passed
#   TestErrorLearningDeduplication::test_duplicate_within_60s_not_written_twice
#   TestErrorLearningDeduplication::test_same_error_after_60s_written_again
#   TestErrorLearningDeduplication::test_different_service_same_error_written
```

Los tres fallan con `found 0` entradas. El fixture `_make_stdin`
(`tests/unit/test_error_learning_behavior.py:28-48`) construye el payload con
`"exit_code": 1` en el top level y un comentario que lo declara "Claude Code
PostToolUse format" — es decir, **el test codifica exactamente el campo fantasma
que el arreglo de hoy eliminó** de `hooks/error-learning.sh`. Al pasar el hook a
clasificar por `tool_response` (`hooks/_lib/tool-outcome.sh`), el payload del
fixture ya no produce fallo y no se escribe nada.

Esto pertenece al workstream de tool-outcome, no a éste: `hooks/**` es config
protegida y el test es del mismo lote. **Queda reportado, no arreglado.** El
arreglo previsible es reemplazar el fixture por la forma que el harness sí manda
(`tool_response` como string de error), que es la que documenta
`manifests/claude-code-hooks-schema.yaml`.

---

## 8. Correcciones a las premisas del encargo

| Premisa del encargo | Verificado | Veredicto |
|---|---|---|
| `.cognitive-os/error-learning.jsonl` = 102 filas | `wc -l` | **confirmado** |
| `.cognitive-os/metrics/error-learning.jsonl` = 11 filas | `wc -l` | **confirmado** |
| Las 11 incluyen 2 producidas por el arreglo de hoy | última fila: `2026-08-15T14:09:39Z`, `TEST_FAILURE`, `go test ./...` | **consistente** (no reproducible sin el estado previo) |
| El huérfano tiene 102 filas y **ningún lector** | `git grep --untracked '\.cognitive-os/error-learning\.jsonl'` → 1 sola coincidencia, y era el escritor | **confirmado** |
| El canónico tiene **ocho lectores** | 26 archivos de código lo referencian; ~21 son consumidores | **REFUTADO — subestimado.** Ocho es menos de la mitad. El encargo probablemente contó sólo Python o sólo `cos_lib/`. |
| «un `--include='*.py'` infló un censo de 8 a 76» | no reproducible desde acá (era un censo previo) | **no verificado** — mi censo propio da 69 menciones / 36 archivos / 26 de código |
| «Si el otro escritor tiene el mismo defecto, unificar junta dos caños rotos» | el defecto de `evolve_task_queue` es otro (ruta + fuga de test), no el campo fantasma | **premisa correcta, diagnóstico distinto**: no hay dos caños rotos iguales |
| ¿Hay un tercer archivo? | `find . -name 'error-learning.jsonl'` → 2 | **no**, sólo dos |
| ¿La partición es más vieja de lo que sugiere? | primera fila del huérfano: `2026-05-11` | **3 meses**, no días |
| `hooks/**` es config protegida | el arreglo no necesitó tocar `hooks/` | **respetado** |
| No tocar `.claude/settings.json` / `cognitive-os.yaml` | `git status` los muestra limpios de mi parte | **respetado** |

Corrección adicional, sobre el encuadre general: el encargo describe el problema
como "se escribe en uno y se lee del otro", lo que sugiere que hay aprendizaje
real cayendo en el archivo equivocado. **No es así.** El escritor divergente
produjo 102 filas y las 102 son bleed de un unit test; ningún evento de operador
se perdió por la partición. Lo que la partición sí causó fue contaminar la
telemetría real con 102 registros sintéticos durante tres meses.

---

## 9. Archivos tocados

| Archivo | Cambio |
|---|---|
| `cos_lib/evolve_task_queue.py` | resolver de ruta en call time + esquema canónico |
| `tests/unit/test_evolve_task_queue.py` | aislamiento del fixture + aserciones de ruta y esquema |
| `tests/audit/test_error_learning_single_path.py` | **nuevo** — guarda de ruta única, con guardas de población |
| `scripts/migrate_error_learning_orphan.py` | **nuevo** — inspector read-only, `--apply` explícito |
| `docs/06-Daily/reports/error-learning-ruta-partida-2026-08-15.md` | este informe |

Ningún `.cognitive-os/**` fue modificado. Verificable:

```bash
wc -l .cognitive-os/error-learning.jsonl .cognitive-os/metrics/error-learning.jsonl
# 102 y 11 — iguales que al inicio
```

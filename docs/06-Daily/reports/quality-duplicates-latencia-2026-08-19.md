# quality-duplicates: 3 minutos por Stop — diagnóstico y arreglo

Fecha: 2026-08-19 · Rama: `main` · Fase: reconstruction

## Resumen ejecutivo

Causa raíz: `lexical_pairs()` comparaba **todos contra todos** (19.722.340 pares
sobre 6.281 archivos) calculando dos operaciones de conjuntos por par, y además
normalizaba cada archivo dos veces.

- Latencia del hook end-to-end: **~162s (p50 medido) → 27,5s**.
- Latencia del tramo culpable (`lexical_pairs`): **181,5s → 20,8s** (8,7x).
- Detección preservada: **sí, idéntica** — 245.693 pares, mismo orden, misma
  `similarity`, mismo flag `exact`, comparados elemento por elemento.
- 14 tests de las suites del scanner pasan.
- Sigue por encima del presupuesto de 10s (27,5s). **No moví el presupuesto.**
  El paso siguiente propuesto está en "Lo que NO hice".

## Correcciones a las premisas del encargo

1. **Los números del encargo están vencidos, no equivocados.** Reproduje el
   comando: hoy son **40 registros, p50 2,7m** (no 38 / 3,0m). El orden de
   magnitud se sostiene.

       python3 scripts/hook_timing_report.py --event Stop --top 15

2. **No son tres hooks sobre presupuesto, son cuatro.** El mismo comando muestra
   `control-plane-audit-hourly` con p95 10,2s y p99 12,6s, también con ⚠. El
   encargo lo omitió.

3. **"Corre en cada evento Stop" es cierto pero incompleto.** El hook tiene una
   salida temprana: si `git status --porcelain --untracked-files=no` viene vacío,
   sale en 0. Corre siempre porque durante una sesión activa el árbol está sucio
   casi siempre, no porque no haya guarda. Esto importa para el arreglo: la
   guarda existente mira *si hay cambios*, no *cuáles* — y por eso no ahorra nada
   en el caso real.

4. **"38 turnos x ~3 min ≈ 2 horas de reloj" sobreestima el impacto percibido.**
   Es tiempo de reloj real, sí, pero el hook corre en el `Stop` y el operador ya
   soltó el turno. El costo verdadero es de CPU (20,8s de `user` por corrida) y
   de contención con el resto de los 23 hooks del mismo evento, no de espera del
   operador. Lo digo para que la priorización no se apoye en el número más
   dramático.

5. **La premisa "mirá `8a2d75c93` y `bbedb3c80` primero, es probable que sea la
   misma clase de defecto" acertó a medias.** Sí había un caso de la familia
   `bbedb3c80` (parsear dos veces el mismo archivo: `normalize_text` corría dos
   veces por archivo), pero eso explicaba ~5s de 194s. Lo caro era otra cosa:
   O(n²). Si me hubiera quedado en el precedente, me llevaba el 3% del problema.

6. **La premisa que más costó verificar fue una restricción, no un dato.** El
   encargo dice que `hooks/**` es ruta protegida y que hay que prefijar
   `COS_ALLOW_PROTECTED_CONFIG_WRITE=1` para *escribir*. En la práctica el guard
   bloquea también **leer y ejecutar** esas rutas: `/bin/bash -n
   hooks/quality-duplicates.sh` (read-only) fue bloqueado. Tuve que prefijar el
   comando aunque no escribí una sola línea ahí. Además el guard bloqueó un
   heredoc que iba a `cos_lib/` sólo porque el *contenido* del parche incluía la
   cadena literal `"rules/"`. Dos falsos positivos, ambos auditados en
   `.cognitive-os/metrics/protected-config-bypass.jsonl`.

7. **Se me terminó el presupuesto de 50 tool-calls a mitad de la verificación.**
   El costo no fue de exploración sino de medición: cada corrida comparativa son
   3-6 minutos de reloj. Emití el bloque `ESCALATION:` y seguí con el override
   documentado (`COS_ALLOW_SUBAGENT_BUDGET_BYPASS=1` + motivo). Lo declaro porque
   queda en la auditoría.

## Causa raíz

El hook `hooks/quality-duplicates.sh` es delgado: delega en
`scripts/cos-quality-duplicates` → `scripts/cos_quality_duplicates.py` →
`cos_lib/duplicate_scanner.py`. Todo el costo está en la librería.

Perfilado por etapas sobre el árbol del repo:

```
collect_files:             2,43s   n=7121 archivos
lexical_pairs:           194,35s   pairs=245693      <-- 97,5% del costo
generic_function_repeats:  2,56s   repeats=11
  build records:          10,44s   n_records=6281
  pares candidatos (n^2/2) = 19.722.340
  promedio de shingles por record = 511
```

Dos defectos, uno grande y uno chico:

**1. O(n²) sin blocking (≈184s de los 194s).** El bucle comparaba cada record
contra todos los siguientes:

```python
union = len(left_shingles | right_shingles)
similarity = round(len(left_shingles & right_shingles) / union, 4) if union else 0.0
exact = left_normalized == right_normalized
```

Por cada uno de los 19,7M de pares construía **dos** conjuntos nuevos (`|` y `&`)
sobre sets de ~511 elementos, y comparaba dos strings completos. El único
prefiltro era una razón de 0,55 sobre el *conteo de tokens*, demasiado laxa para
podar algo. 19,7M × ~9,3µs = 184s.

**2. Doble normalización por archivo (≈5s de los 10,44s de build).**
`normalized_tokens(text)` es exactamente `WORD_RE.findall(normalize_text(text))`,
y el código llamaba a `normalized_tokens(text)` **y** a `normalize_text(text)`
sobre el mismo texto. `normalize_text` hace cuatro pasadas de regex por línea.
Esta es la familia de `bbedb3c80`.

Nota: `generic_function_repeats` vuelve a leer cada archivo del disco (segunda
lectura completa), pero eso son 2,56s y no lo toqué.

## Quién consume la salida de este hook

Esto es lo que más me preocupa reportar, porque cambia la evaluación
costo/beneficio del hook entero.

- El hook escribe `.cognitive-os/reports/quality-duplicates/latest.json` y
  `latest.md`. **Los dos están gitignoreados** (`git check-ignore -v` →
  `.gitignore:13:.cognitive-os/reports/*`). No se versionan, no viajan.
- **Ningún código lee esos archivos.** `git grep -n "reports/quality-duplicates"`
  sobre `*.py`, `*.sh`, `*.go`, `*.yaml`, `*.json` sólo devuelve: el hook que los
  escribe, el propio scanner que define la ruta por default, y **declaraciones en
  manifiestos** (`manifests/primitive-lifecycle.yaml` como `metrics_file`,
  `manifests/state-retention.yaml` como política de retención, y el primitivo
  `.ai/primitives/hooks/...json`). Ningún script lee la clave `metrics_file` de
  ese manifiesto: `git grep metrics_file` sobre `scripts/`, `cos_lib/`, `lib/`,
  `cmd/`, `packages/` sólo trae usos ajenos (`component_usage_tracker`,
  `context_injector`, `perf.go`), ninguno apunta a este reporte.
- **El único consumidor real es un humano** que abra `latest.md` a mano, guiado
  por el `repair_message` del manifiesto.
- **El ratchet nunca gateó nada.** `.cognitive-os/baselines/quality-duplicates.json`
  **no existe**, así que el hook nunca pasa `--fail-on-new` y el reporte queda con
  `"ratchet": {"status": "missing-baseline"}`. Encima, `COS_QUALITY_DUPLICATES_ENFORCE`
  no está seteado, con lo cual el hook siempre sale 0 — coincide con las 40
  corridas sin un solo fallo.
- **El reporte es intriageable.** El último `latest.json` declara
  `"findings": 245704` (245.693 lexical + 11 de función) sobre 7.119 archivos, y
  el propio código lo trunca a 2.000 (`MAX_PERSISTED_FINDINGS`) con un comentario
  que cuenta que sin el tope llegó a 167 MiB. Un gate con 245 mil hallazgos y sin
  baseline no es un gate: es un archivo grande que nadie abre.

Esto **no** lo convierte en un hook inútil —la detección es real y el arreglo la
deja barata—, pero sí quiere decir que hoy paga 27s por turno para producir un
artefacto que ningún proceso lee y ninguna decisión usa. Es una recomendación
para el operador, no algo que yo vaya a ejecutar (ver "Lo que NO hice").

## El arreglo

Un solo archivo: `cos_lib/duplicate_scanner.py`, función `lexical_pairs()`.

**Blocking por tamaño (exacto, no heurístico).** De la definición de Jaccard:

    J(A,B) = |A∩B| / |A∪B| >= t   ⟹   |A∩B| >= t·|A∪B|

y como `|A∩B| <= min(|A|,|B|)` y `|A∪B| >= max(|A|,|B|)`, todo par que califique
cumple necesariamente:

    min(|A|,|B|) >= t · max(|A|,|B|)

sobre el **tamaño de los conjuntos de shingles**. Es una condición *necesaria*:
los pares que descarta no podían haberse reportado nunca. Los duplicados exactos
tienen conjuntos idénticos (razón 1,0), así que tampoco se pierden. Ordenando los
records por tamaño de conjunto, el barrido todos-contra-todos se vuelve una
ventana deslizante que corta con `break` apenas se excede la razón.

Con t=0,82 eso deja una banda de ±18% de tamaño en vez de los 19,7M de pares.

**Una sola normalización por archivo.** `normalized = normalize_text(read_text(path))`
y después `WORD_RE.findall(normalized)` — el mismo resultado que
`normalized_tokens()`, calculado una vez.

**Una sola construcción de conjunto por par.** En vez de `len(A|B)` y `len(A&B)`
(dos sets nuevos), se calcula la intersección una vez y la unión por aritmética:
`union = |A| + |B| - |A∩B|`.

**Comparación de strings diferida.** Cuerpos normalizados idénticos producen
conjuntos de shingles idénticos y por lo tanto `similarity == 1.0`. Entonces, por
debajo del umbral y con unión no vacía, `exact` sólo puede ser `False`: la
comparación de strings completos se evita ahí. Se preserva el caso `union == 0`.

**Orden de emisión preservado.** El resultado se reordena por el par de índices
originales, de modo que la lista devuelta es idéntica —posición por posición— a
la del bucle anidado anterior. Esto importa porque hay un segundo consumidor de
la función: `scripts/primitive_duplication_audit.py`.

## Prueba de que la detección se preservó

Script: `scratchpad/diff_detection.py`. Carga la implementación **anterior** desde
una copia guardada y la **actual** desde el repo, las corre sobre exactamente la
misma lista de archivos y los mismos parámetros, y compara las listas completas
elemento por elemento (`left`, `right`, `similarity`, `exact`).

```
files=7121
NEW lexical_pairs: 20.76s  pairs=245693
OLD lexical_pairs: 181.48s  pairs=245693
speedup = 8.7x
RESULT: IDENTICAL (same pairs, same order, same similarity, same exact flag)
EXIT=0
```

No es "el mismo conteo": es la **misma lista**, en el mismo orden, con los mismos
valores de similitud y el mismo flag `exact`, en los 245.693 elementos.

Suites del scanner:

```
.venv/bin/python -m pytest tests/unit/test_cos_quality_duplicates.py \
  tests/behavior/test_cos_quality_duplicates_cli.py \
  tests/red_team/portability/test_duplicate_scanner.py \
  tests/unit/test_primitive_duplication_audit.py -q
→ 14 passed in 1.04s
```

Sintaxis (ningún `.sh` fue modificado; chequeo igual, con el bash 3.2 del sistema):

```
/bin/bash -n hooks/quality-duplicates.sh        → OK
/bin/bash -n scripts/cos-quality-duplicates     → OK
```

Latencia end-to-end del hook tal cual lo invoca el evento `Stop`:

```
COS_ALLOW_PROTECTED_CONFIG_WRITE=1 time bash hooks/quality-duplicates.sh </dev/null
→ real 0m27,478s   user 0m20,848s   sys 0m1,717s
```

Antes: p50 2,7m = ~162s medidos por el wrapper de timing. Después: 27,5s.

## Los otros dos hooks sobre presupuesto

**No comparten causa** con `quality-duplicates`. Son tres problemas distintos.
Los diagnostiqué; no los arreglé (fuera de alcance salvo trivialidad, y ninguno
lo es del todo).

### `edit-lock-session-end` — p50 12,9s

Causa: `scripts/edit-coop.sh release-mine` recorre
`.cognitive-os/runtime/edit-locks/*/` y por **cada** directorio llama
`_read_field`, que es `sed ... | head -1` — **dos subprocesos por lock**.

```
ls .cognitive-os/runtime/edit-locks/ | wc -l  →  1133
```

1133 locks × 2 subprocesos ≈ 2.266 spawns por Stop. A ~5ms cada uno da ~11s, que
es exactamente el p50 observado. La aritmética cierra.

Hay dos problemas encadenados: (a) el patrón "un subproceso por archivo" que la
propia regla de performance del proyecto prohíbe, y (b) **1133 locks acumulados
que nadie recolecta** — el hook libera sólo los de la sesión propia, y los de
sesiones muertas quedan hasta que expire el TTL de 30min... salvo que nadie los
borra. El arreglo natural es una sola pasada (`grep -h` o `awk` sobre todos los
`meta.yaml` de una) más un GC de locks vencidos. Es acotado pero toca un
subsistema de concurrencia (ADR-098); no lo hice por mi cuenta.

### `engram-crystallize-on-session-end` — p50 10,4s

Causa: **se está muriendo por su propio timeout, siempre**. El hook corre

```bash
signal.alarm(int('${COS_ENGRAM_CRYSTALLIZER_TIMEOUT_SECONDS:-10}'))
```

con default 10 segundos, y la salida va a `2>/dev/null` con `|| count=0`. El p50
de 10,4s = 10s de alarma + ~0,4s de arranque de Python. O sea: **quema 10s por
turno y registra `digests_created: 0`**, indistinguible de "no había candidatos".
Su propia cabecera declara "target latency ≤500ms" y "short-circuits immediately
when there are no candidates" — la medición contradice el documento. No es un
problema de latencia: es un subsistema que no está funcionando y cuyo fallo está
silenciado. Merece su propia investigación, no una optimización.

### `control-plane-audit-hourly` — p95 10,2s, p99 12,6s (no estaba en el encargo)

Cuarto hook con ⚠. p50 190ms, así que sólo se pasa cuando efectivamente corre la
auditoría horaria — comportamiento esperable para un hook con cadencia. Lo dejo
anotado; probablemente sea el único de los cuatro donde el ⚠ es una propiedad del
diseño y no un defecto.

## Lo que NO hice y por qué

Los verdes baratos que el encargo prohibía, y que confirmo haber rechazado:

- **No desregistré el hook** ni lo moví a un evento menos frecuente. Sigue en
  `Stop` en `.claude/settings.json:805`, sin tocar.
- **No subí el presupuesto de 10s.** Después del arreglo el hook tarda 27,5s y
  **sigue marcando ⚠**. Dejarlo en rojo honesto es preferible a mover el baseline:
  esa es exactamente la falla que `gates-sin-trampa` prohíbe. El ⚠ ahora dice algo
  verdadero (queda trabajo) en vez de tapar un 18x.
- **No lo hice `async`.** Habría sido tentador porque, como documenté arriba,
  *ningún proceso lee su salida* — o sea que "async" habría sido trivialmente
  seguro. Justamente por eso no lo hice: convertir en asincrónico un hook cuyo
  problema real es que produce un artefacto que nadie consume es esconder la
  pregunta, no contestarla.
- **No reduje el alcance del escaneo.** No agregué exclusiones, no subí
  `min_tokens`, no bajé el umbral de 0,82, no recorté sufijos. La lista de
  archivos escaneados es idéntica (7.121) y los hallazgos son idénticos (245.693).
  Todo el ahorro sale de no calcular pares que eran matemáticamente imposibles.
- **No toqué `MAX_PERSISTED_FINDINGS`** ni generé un baseline. Generar el baseline
  hoy congelaría 245.704 hallazgos como "aceptados" de un plumazo: sería un
  supresor que no suprime nada, el otro antipatrón de la misma norma.

Lo que dejo recomendado al operador, con la evidencia arriba, sin ejecutarlo:

1. **Cache por huella del árbol.** El resultado sólo cambia si cambia el
   contenido de los archivos rastreados. Cachear por `(HEAD, size+mtime de los
   archivos recolectados, parámetros, versión del scanner)` y reusar el reporte
   anterior cuando la huella coincide lleva el caso común a ~0, con la misma
   detección. Es el camino para bajar de 27,5s a menos de 10s **sin** tocar la
   detección. No lo implementé porque me quedé sin presupuesto de tool-calls a
   mitad de la verificación y prefiero no dejar un subsistema de cache a medio
   probar.
2. **Decidir qué es este gate.** Con 245.704 hallazgos, sin baseline, sin
   `ENFORCE`, con el reporte gitignoreado y sin ningún lector programático, hoy
   no gatea nada. O se le da un consumidor y un baseline con criterio escrito, o
   se asume explícitamente que es un artefacto de consulta manual y se le baja la
   frecuencia por decisión escrita — no apagándolo de callado.
3. **`edit-lock-session-end` y el basural de 1133 locks**, y la investigación
   aparte del crystallizer que muere en su propia alarma.

También, para el operador: no maté ni toqué ningún proceso, no pusheé nada, y los
dos falsos positivos del `protected-config-write-guard` (bloquear un `bash -n`
read-only, y bloquear un heredoc a `cos_lib/` por contener la cadena `"rules/"`)
quedaron auditados en `.cognitive-os/metrics/protected-config-bypass.jsonl`.

## Archivos modificados

- `cos_lib/duplicate_scanner.py` — función `lexical_pairs()`. Único cambio de
  código. Sin commit; queda para revisión del operador.

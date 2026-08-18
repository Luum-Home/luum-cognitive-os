<!-- SCOPE: os-only -->
# `test_instrument_productivity` — timeout a los 120 s: qué lo causaba

**Fecha:** 2026-08-18
**Test:** `tests/audit/test_instrument_productivity.py::test_script_runs_and_uses_documented_exit_codes`
**Script:** `scripts/audit_instrument_productivity.py`
**Veredicto:** no se cuelga — **trabaja de verdad**, y casi todo el trabajo era
desperdicio recomputado. Se aceleró el script **5,0x**. **No se subió ningún tope.**

---

## 1. Primero: ¿se cuelga o tarda?

`TimeoutExpired` no distingue las dos, así que se midió CPU aparte del wall con
`resource.RUSAGE_CHILDREN`, que acumula el tiempo de los hijos ya esperados
(incluidos los `git grep` que el script lanza).

Harness de medición (reproducible):

```python
b = resource.getrusage(resource.RUSAGE_CHILDREN)
t0 = time.monotonic()
p = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
wall = time.monotonic() - t0
a = resource.getrusage(resource.RUSAGE_CHILDREN)
```

| corrida | wall | cpu_user | cpu_sys | cpu_total | cpu/wall |
|---|---|---|---|---|---|
| **antes** | 77,5 s | 11,5 s | 50,3 s | **61,8 s** | **0,80** |
| **después** | 15,4 s | 9,7 s | 40,6 s | 50,2 s | 3,27 |

**`cpu/wall` = 0,80 cierra la pregunta: no espera nada, trabaja.** Un cuelgue
daría CPU ≈ 0. No hay defecto de espera que arreglar.

El segundo dato importa tanto como el primero: **`cpu_sys` (50,3 s) es 4,4x
`cpu_user` (11,5 s)**. El costo no está en cómputo, está en syscalls — spawns de
procesos y recorridas de filesystem. Eso dirigió toda la búsqueda.

### La carga del momento, y por qué el wall no es portable

Todas las mediciones se tomaron con **load average entre 665 y 756** (había otro
agente en `hooks/skill-router-*` y dos lanes corriendo). Los wall de esta tabla
**no son portables a una máquina ociosa**; sirven para comparar antes/después
tomados con carga comparable, y para eso están ordenados. El número que sí
sobrevive al traslado es la **relación cpu/wall** y el desglose por fase.

---

## 2. Dónde se iba el tiempo — el desglose

Perfilado en proceso, envolviendo cada función del script (total 29,3 s en esa
corrida, con carga más baja que la de la tabla anterior):

| fase | llamadas | segundos | % |
|---|---|---|---|
| `consumers()` (spawn de `git grep`) | 58 | 14,6 s | **49,7 %** |
| `artifact_stat()` | 122 | 12,0 s | **41,0 %** |
| `run_counts()` | 1 | 1,8 s | 6,1 % |
| `census()` | 1 | 0,8 s | 2,8 % |
| `artifacts_for()` | 160 | 0,1 s | 0,4 % |

**90,7 % en dos funciones**, y las dos hacían trabajo repetido:

1. **`artifact_stat()` — 68 de 122 llamadas no encontraban el archivo en
   `metrics/`** y caían al fallback `REPO.glob(".cognitive-os/**/{base}")`. Un
   glob recursivo que **no encuentra nada recorre el árbol entero**: `.cognitive-os`
   tiene **10.342 archivos / 410 MB**. Eran **68 recorridas completas del mismo
   árbol** para responder 68 preguntas distintas sobre él.

2. **`consumers()` — 54 spawns de `git grep` para 38 basenames distintos.** El
   grep depende sólo del basename; el filtro del productor es por hook. Los hooks
   comparten artefactos, así que el mismo grep se re-corría.

---

## 3. Lo que se hizo

Ninguna de las dos correcciones cambia qué se audita. Son aceleración pura.

- **Índice único de `.cognitive-os`** (`_cognitive_os_index()`, `lru_cache`): una
  sola pasada de `os.walk` construye `basename -> path` y responde las 122
  consultas. Reemplaza 68 recorridas del árbol por una.
- **`artifact_stat()` memoizada** (`lru_cache`): 122 llamadas → 94 distintas.
- **`_referencing_files()` memoizada**: separa el `git grep` (depende sólo del
  basename) del filtro del productor (por hook). 54 spawns → 38.

### Efecto

| | antes | después |
|---|---|---|
| wall del script (carga ~690) | 77,5 s | **15,4 s** (5,0x) |
| suite completa del archivo | timeout a 120 s | **21 passed in 17,23 s** |

```
$ .venv/bin/python3 -m pytest tests/audit/test_instrument_productivity.py -p no:randomly -q --no-header
..................... [100%]
21 passed in 17.23s
```

### Equivalencia de salida — verificada, no asumida

Se capturó `--json` antes y después y se compararon veredictos, consumidores y
archivos de artefacto por hook:

```
verdict totals base : {'starved': 7, 'no-artifact': 61, 'idle': 53,
                       'no-producer': 2, 'no-consumer': 2, 'productive': 35}
verdict totals after: (idéntico)
hooks differing once live `runs` is excluded: 1
```

`runs` difiere en 20 hooks porque la telemetría **está viva** y otros agentes
escriben mientras se mide (11.936 → 11.947); no es efecto del cambio.

La única diferencia real es `git-context-capture`, que resuelve el basename
`meta.json` a otra sesión archivada. **Es un defecto latente que el cambio dejó
definido, no una regresión:** hay **164 archivos `meta.json`** bajo
`.cognitive-os`, y el `glob` viejo se quedaba con el primero en orden de
filesystem. Ese orden es estable en esta máquina y en este estado del directorio
—se verificó 3 veces seguidas— pero **no está definido**: cambia al archivar o
borrar una sesión, y en otra máquina. El índice nuevo toma el mínimo
lexicográfico, que sí está definido. El veredicto del hook (`starved`) y sus 50
consumidores no se mueven. El docstring del script decía "Read-only and
deterministic"; para este basename recién ahora es cierto.

---

## 4. Lo que NO se hizo, y por qué

- **No se subió el tope.** El verde barato acá era `COS_TEST_SUBPROCESS_DEFAULT_TIMEOUT`
  a 600. Con el costo concentrado al 90 % en dos funciones que recomputaban lo
  mismo, subir el tope habría comprado tiempo y devuelto el problema más grande.
- **No se recortó lo que el script audita.** Los 160 instrumentos y los 72
  improductivos se siguen midiendo igual.
- **No hay `skip` ni `xfail`.**

---

## 5. Riesgo de escala que queda

`consumers()` sigue siendo **38 spawns de `git grep`, cada uno O(worktree)**. No
es cuadrático sobre primitivas —crece lineal con los artefactos distintos, no con
los hooks— pero **crece con el tamaño del repo**: si el worktree se duplica, esos
10 s se duplican.

Dos datos que acotan el riesgo:

- Un `git grep -l -F` cuesta **0,174 s** sobre el worktree completo (8.592
  archivos versionados).
- **Excluir el JSON de 36 MB no lo mejora** (0,174 s → 0,140 s). Ver §6.

Si vuelve a apretar, el paso siguiente es **un solo `git grep` con múltiples
`-e`** en vez de 38, no subir el tope.

---

## 6. Correcciones a las premisas del encargo

Varias premisas no se sostuvieron. Ordenadas por cuánto cambian la conclusión.

1. **«el tope de 120 s» no está en el test — el test pide 1800.**
   `tests/audit/test_instrument_productivity.py:113` dice `timeout=1800`, y lo
   dice desde su primer commit (`0c26844e48`, 2026-08-15); no hubo cambio
   reciente. Los 120 s los impone **`tests/conftest.py`**, que envuelve
   `subprocess.run` y **capa todo `timeout=` explícito** al presupuesto de la
   suite: `_DEFAULT_TEST_SUBPROCESS_TIMEOUT = float(os.environ.get("COS_TEST_SUBPROCESS_DEFAULT_TIMEOUT", "120"))`.
   Esto importa para el arreglo: quien buscara el número en el test para subirlo
   **no lo habría encontrado**, y de haberlo subido ahí no habría pasado nada,
   porque el cap de conftest gana.

2. **«El repo creció 161 commits en 48 horas» — son 36.**
   `git log --since="2026-08-16" --oneline | wc -l` → **36**.

3. **El crecimiento de hooks no explica nada: se agregó 1 hook en 48 h.**
   `git log --since="2026-08-16" --diff-filter=A --name-only --pretty=format: -- 'hooks/*.sh' 'packages/*/hooks/*.sh' | grep -c '\.sh$'` → **1**.
   El script recorre 256 hooks (deduplicados por `realpath`) y clasifica 160 como
   instrumentos. **No es un script que se volvió lento porque creció lo que
   recorre**; era lento desde antes y el margen se agotó.

4. **El archivo de 35,8 MB NO explica este costo.** La premisa venía marcada como
   «dato duro de ayer» y era cierta para *otro* escaneo, no para éste. Medido acá:
   `git grep -l -F` tarda **0,174 s** con el archivo y **0,140 s**
   excluyéndolo — 34 ms de diferencia sobre un total de 77 s. Además el archivo
   pesa **37.804.654 bytes (36,0 MiB)**, no 35,8 MB. Si hubiera seguido esa pista
   habría optimizado un 0,04 % del problema.

5. **`tests/red_team/portability/` sí tiene 955 entradas** (premisa confirmada),
   **pero el script no las toca**: `census()` sólo recorre `hooks/` y
   `packages/*/hooks`. Sólo las roza vía `git grep`, y ese costo ya está medido
   en el punto anterior.

6. **«no es carga de máquina — o al menos no sólo»: la carga era enorme y sí
   importaba.** `load average 745` al empezar a medir. No era la causa raíz —el
   script era genuinamente caro— pero es lo que empujó 77,5 s por encima de 120 s
   ese día. Las dos cosas son ciertas a la vez, y por eso el arreglo apunta al
   costo y no al tope.

7. **«`pytest-timeout` aborta la sesión entera»: no fue el mecanismo acá.** El
   fallo era `subprocess.TimeoutExpired` levantado por el wrapper de conftest
   *dentro* del test, que produce un fallo normal y con resumen. `pytest.ini`
   tiene `timeout = 30` con `timeout_method = thread`, que es otro camino. La
   advertencia del encargo es válida en general; no aplicaba a este síntoma.

8. **Premisa sana, sin corrección:** «medí CPU aparte del wall». Fue exactamente
   lo que decidió el diagnóstico en la primera medición.

---

## 7. Reproducir

```bash
# CPU vs wall del script
.venv/bin/python3 -c "
import resource, subprocess, time
b=resource.getrusage(resource.RUSAGE_CHILDREN); t0=time.monotonic()
subprocess.run(['.venv/bin/python3','-W','ignore','scripts/audit_instrument_productivity.py'],capture_output=True)
w=time.monotonic()-t0; a=resource.getrusage(resource.RUSAGE_CHILDREN)
c=(a.ru_utime-b.ru_utime)+(a.ru_stime-b.ru_stime)
print(f'wall={w:.1f}s cpu={c:.1f}s ratio={c/w:.2f}')"

# el test
.venv/bin/python3 -m pytest tests/audit/test_instrument_productivity.py -q --no-header

# de dónde salen los 120 s
grep -n 'COS_TEST_SUBPROCESS_DEFAULT_TIMEOUT' tests/conftest.py
```

Anotar el `uptime` junto a cualquier wall que se reporte: con carga ~700 estos
números son los de arriba; en una máquina ociosa serán bastante menores.

# Medición antes/después blindada contra el artefacto equivocado

**Fecha:** 2026-08-15
**Entregable:** `scripts/revision_probe.py` + `tests/unit/test_revision_probe.py`
**Caso testigo:** `docs/06-Daily/reports/agent-bus-flag-estricto-2026-08-15.md`, sección
"Lo que no se sostuvo", punto 3.

## El problema en una línea

Una medición "antes/después" que extrae código viejo con `git archive` puede cargar el
módulo **nuevo** y producir una salida que parece evidencia perfecta del viejo. Nada en
el resultado la contradice. La única forma de enterarse es sospechar.

La regla que implementa el helper:

> Si el "antes" y el "después" resuelven al mismo artefacto, la comparación es NULA.
> Falla ruidosamente, digan lo que digan los números.

El helper **no asierta sobre el resultado, asierta sobre la procedencia de lo que lo
produjo**. Misma forma que el control nulo de `scripts/family_conformance_probe.py`: sin
discriminador no hay veredicto, hay ruido.

## Qué combinación de aislamiento funciona, y cómo lo probé

Matriz corrida contra un `git archive 4f3a7e5a3` (último commit antes de que
`dc322cf6b` agregara `valkey_transport_disabled_reason` a
`packages/agent-coordination/lib/agent_bus.py`). El discriminador es
`hasattr(ab, 'valkey_transport_disabled_reason')`: `False` = código viejo de verdad,
`True` = cargó el vivo.

```bash
# extracción
git archive 4f3a7e5a3 | tar -x -C "$OLD"
# snippet (guardado FUERA del archive, como suele pasar)
cat > "$TMP/snip.py" <<'EOF'
import cos_lib.agent_bus as ab, os
print("FILE=" + os.path.realpath(ab.__file__))
print("HAS_NEW_SYMBOL=" + str(hasattr(ab, "valkey_transport_disabled_reason")))
EOF
cd "$OLD" && .venv/bin/python [flags] "$TMP/snip.py"
```

| # | Variante | Módulo cargado | `HAS_NEW_SYMBOL` | ¿Aísla? |
|---|----------|----------------|------------------|---------|
| A | `python snip.py`, cwd=archive | **repo vivo** | `True` | **NO** — el fallo original |
| B | `python -I snip.py`, cwd=archive | **repo vivo** | `True` | **NO** |
| C | `PYTHONNOUSERSITE=1 python snip.py` | **repo vivo** | `True` | **NO** |
| D | `PYTHONPATH=$OLD python snip.py`, cwd=**repo** | archive | `False` | **SÍ** |
| E | `python -S snip.py`, cwd=archive | — | `ModuleNotFoundError` | rompe todo |
| F | `python -I -S snip.py` | — | `ModuleNotFoundError` | rompe todo |
| G | `python -c "import ..."`, cwd=archive | archive | `False` | **SÍ** |

Lecturas:

- **`-I` no sirve.** `-I` implica `-E -s`, **no** `-S`: el procesamiento de `site` sigue
  corriendo y el `.pth` del editable install sigue agregando el repo vivo. Confirmado en
  B. Está fijado como test: `test_python_dash_I_does_not_defeat_the_editable_pth`.
- **`-S` sirve y no sirve para nada.** Saca el `.pth`, y con él site-packages entero: sin
  `cos_lib` (que llega *por* el `.pth`) y sin pytest ni nada de terceros. E y F.
- **Lo que funciona es `PYTHONPATH` con el run root adelante** (D). Las entradas de
  `PYTHONPATH` van antes que lo que agrega site-packages, así que ganan.
- **G es la sorpresa**: el `python -c` desde adentro del archive **también** aísla, porque
  con `-c` `sys.path[0]` es el cwd. O sea que el "hacerlo a mano" no está roto siempre —
  está roto justo cuando el snippet vive en un archivo fuera del archive, que es lo normal.

El `.pth` en cuestión:

```
$ cat .venv/lib/python3.12/site-packages/_editable_impl_luum_cognitive_os.pth
<home>/Projects/luum/luum-agent-os
```

Es una entrada de ruta pelada, no un `import`, así que `site` la **appendea**. Ver
"Correcciones a las premisas" más abajo: eso cambia el mecanismo real del fallo.

### Lo que hace el helper

Combinación, no bala de plata:

1. `PYTHONPATH=<run root>` (limpiando cualquier `PYTHONPATH` heredado).
2. El runner se escribe **adentro** del run root, así `sys.path[0]` es el run root y no el
   directorio del snippet.
3. En el hijo, antes de ejecutar nada, se **poda** el root vivo de `sys.path` cuando el run
   root no es el vivo. Eso es lo que impide que un módulo ausente del archive caiga en
   silencio al árbol vivo.
4. `cwd = run root`.

Los cuatro juntos son *best effort*. La **garantía** no viene de acá: viene de hashear lo
que efectivamente se cargó.

## Reproducción del fallo original y demostración del rechazo

Las dos cosas están fijadas como tests ejecutables, no como prosa.

```bash
.venv/bin/python -m pytest tests/unit/test_revision_probe.py -q -p no:cacheprovider
# 11 passed in 22.45s
```

**El fallo, reproducido** — `test_naive_harness_silently_measures_the_live_tree`:
arma el arnés a mano (extrae `4f3a7e5a3`, hace `cd`, corre el snippet) y asierta que el
`__file__` resuelto cae bajo el repo vivo y que el "código viejo" reporta
`HAS_NEW_SYMBOL=True` — el símbolo que sólo existe en el nuevo. Ese es exactamente el
output que en la sesión testigo pasó por evidencia.

**El rechazo** — `test_identical_revision_is_rejected_not_reported`:

```bash
$ .venv/bin/python scripts/revision_probe.py --rev HEAD \
    --module cos_lib.agent_bus --snippet-file /tmp/s.py ; echo "exit=$?"
REJECTED: before and after resolved to the SAME artefact for every module
(cos_lib.agent_bus); rev=HEAD digest=76bceb33374d3fe8. The comparison is void
regardless of the numbers it printed.
exit=1
```

**Y la medición correcta que el arnés a mano erró** —
`test_real_change_yields_distinct_provenance_and_correct_before_value`:

```bash
$ .venv/bin/python scripts/revision_probe.py --rev 4f3a7e5a3 \
    --module cos_lib.agent_bus --snippet-file /tmp/s.py ; echo "exit=$?"
== before (digest abf933a6dd4ad76b)
   cos_lib            cos_lib/__init__.py                              sha256:9c90355d1ddb
   cos_lib.agent_bus  packages/agent-coordination/lib/agent_bus.py     sha256:56938c4e6cf9
HAS_NEW_SYMBOL=False
== after (digest 76bceb33374d3fe8)
   cos_lib            cos_lib/__init__.py                              sha256:9c90355d1ddb
   cos_lib.agent_bus  packages/agent-coordination/lib/agent_bus.py     sha256:e4083e1e015e
HAS_NEW_SYMBOL=True
exit=0
```

Mismo snippet, mismo rev, misma máquina: a mano da `True` (mentira), con el helper da
`False` (el código viejo de verdad).

## El identificador de procedencia, y por qué la ruta sola no alcanza

Cada corrida devuelve, por módulo cargado: **realpath resuelto + sha256 del contenido**.
El `digest()` de la corrida es el sha256 de ese conjunto ordenado.

Mirá las dos salidas de arriba. La ruta **relativa** es idéntica en los dos casos
(`packages/agent-coordination/lib/agent_bus.py`) y la ruta **absoluta** es distinta en los
dos casos. O sea:

| Comparador | Caso válido (`4f3a7e5a3`) | Caso nulo (`HEAD`) | Veredicto |
|---|---|---|---|
| ruta relativa | iguales | iguales | rechaza todo, incluso lo válido |
| ruta absoluta | distintas | distintas | acepta todo, incluso lo nulo |
| **sha256 del contenido** | **distintos** | **iguales** | separa |

Está fijado en `test_path_alone_cannot_tell_the_two_cases_apart`.

Hay una segunda razón, propia de este repo: **70 de 369 archivos `.py` de `cos_lib/`
(19,0%) son symlinks** a `packages/*/lib/*.py`. Un identificador por ruta los ve distintos
siendo el mismo archivo. El runner hace `os.path.realpath` antes de hashear, y el test
`test_symlink_and_its_target_are_one_artefact` asierta que `cos_lib.agent_bus` se reporta
como `packages/agent-coordination/lib/agent_bus.py`, no como el link.

### Los tres verdes baratos que el helper no toma

1. **Avisar en vez de fallar.** `run_pair` levanta `NullComparison`. No hay flag para
   bajarlo a warning. Un warning lo lee el que ya sospecha, y el punto es que nadie
   sospecha.
2. **Comparar sólo la ruta.** Ver la tabla: no separa nada. Se hashea el contenido.
3. **Un test que prueba la implementación.** No hay ningún "el helper devuelve dos valores
   distintos si le paso dos valores distintos". Todos los tests parten de la conducta: el
   arnés a mano miente, el helper rechaza.

Un cuarto que también se cierra: **el silencio no es evidencia**. Si un módulo declarado
nunca se cargó en alguna de las dos corridas, no hay comparación —
`NothingMeasured`, no un pase (`test_module_that_never_loads_is_an_error_not_a_pass`).

Y un quinto: la poda de `sys.path` no puede impedir que el snippet la deshaga. Por eso hay
detección de fuga: si una corrida cargó un archivo fuera de su propio root, se levanta
`ProvenanceLeak` (`test_snippet_that_re_adds_the_live_root_is_caught_as_a_leak`). La
garantía es la procedencia, no los flags.

## Costo de usarlo contra hacerlo a mano

Hacerlo a mano, mínimo honesto (lo que hizo la sesión testigo):

```bash
mkdir -p "$OLD" && git archive 4f3a7e5a3 | tar -x -C "$OLD"
cd "$OLD"
PYTEST_ALLOW_NONVENV=1 <repo>/.venv/bin/pytest tests/unit/test_agent_bus.py -q ...
# + acordarse de imprimir ab.__file__
# + acordarse de que sys.path[0] es el dir del script, no el cwd
# + acordarse de comparar contra la corrida del árbol vivo
```

Con el helper:

```python
from scripts.revision_probe import run_pair
pair = run_pair("4f3a7e5a3", snippet, modules=["cos_lib.agent_bus"])
```

o una línea de CLI. Cuatro pasos manuales y tres cosas que hay que acordarse → una llamada,
y las tres cosas que hay que acordarse pasan a ser imposibles de olvidar porque el helper
falla si no se cumplen. **Usarlo cuesta menos que hacerlo a mano**, que era el criterio de
aceptación del encargo.

Tamaño: 364 líneas el helper (la mitad docstring y el runner embebido), 233 los tests.
Sin plugins, sin registry, sin capas. Un módulo, una función pública, tres excepciones.

## Qué NO cubre

- **Sólo Python, y sólo imports.** Si el snippet mide algo que no pasa por `sys.modules`
  (un subproceso, un binario, un archivo de datos), la procedencia no lo ve.
- **Sólo lo que el snippet importa.** Un módulo que se importa lazy adentro de una función
  que el snippet no llama no aparece en la procedencia.
- **No detecta side effects entre corridas.** Las dos corridas comparten `$HOME`, caches,
  sockets, DBs. Si la corrida "antes" deja estado que cambia la "después", el helper no se
  entera. Es el mismo agujero que el `family_conformance_probe` cierra con `HOME`
  sandboxeado; acá no está hecho.
- **No corre pytest.** El snippet es Python plano. Correr una suite entera contra el rev
  viejo sigue siendo trabajo a mano (aunque el patrón de aislamiento del helper es
  reusable: `PYTHONPATH` + poda + cwd).
- **Escribe un archivo temporal en el root de cada corrida** (`.revision_probe_runner_<pid>.py`),
  incluido el repo vivo. Se borra en `finally`; un `kill -9` deja el archivo. El pid en el
  nombre evita colisiones entre sesiones concurrentes.
- **`git archive` no incluye lo no commiteado.** Comparar contra un rev sucio no es posible
  por diseño: el "antes" es siempre lo que está en el objeto de git.

## ¿Generaliza a node / binarios / docker? — declarado, no construido

El mismo bug existe en las tres. **No están implementadas.** Lo que haría falta:

- **`node_modules` sin reinstalar.** La forma calza: la procedencia sería
  `require.resolve()` de cada módulo + sha256 del archivo resuelto, y el aislamiento sería
  `NODE_PATH` + un cwd distinto. Lo que falta y no es trivial: los symlinks de pnpm/yarn
  workspaces hacen que `realpath` apunte al store compartido, así que dos "versiones"
  pueden resolver al mismo inode legítimamente; el discriminador tendría que ser el
  contenido del `package.json` resuelto, no sólo el del módulo. **Admisible con trabajo
  real, no un port de 20 líneas.**
- **Binario no recompilado.** Es el caso *más fácil*: la procedencia es
  `sha256(<ruta del ejecutable>)` y listo, no hay resolución dinámica que engañe. Lo que
  falta es capturar también las librerías dinámicas (`otool -L` / `ldd`), porque el binario
  puede ser idéntico y la `.dylib` no. **Admisible casi tal cual.**
- **Tag de imagen Docker que no cambió.** La procedencia natural es el **digest** de la
  imagen (`docker image inspect --format '{{.Id}}'`), no el tag — que es exactamente la
  misma lección que "la ruta sola no alcanza": el tag es el nombre, el digest es el
  contenido. Lo que falta: no hay "árbol de trabajo" con el que comparar, hay que buildear,
  y eso convierte la llamada barata en algo que tarda minutos. **La forma calza pero el
  costo de uso se rompe**, y el criterio del encargo era justamente que usarlo cueste menos
  que hacerlo a mano.

Un helper que cierra Python de verdad vale más que uno que promete tres lenguajes y no
cierra ninguno. No se generalizó.

## Correcciones a las premisas del encargo

1. **FALSA — "`git grep` acá no soporta `\b`: usá `-w`".** Sí lo soporta, y da idéntico
   a `-w`:

   ```bash
   $ git grep -c '\bdef\b' -- packages/agent-coordination/lib/agent_bus.py
   packages/agent-coordination/lib/agent_bus.py:51
   $ git grep -c -w 'def' -- packages/agent-coordination/lib/agent_bus.py
   packages/agent-coordination/lib/agent_bus.py:51
   ```

   Discriminante: si `\b` fuese literal, el patrón sería `bdefb` → 0 matches. Contraprueba
   con un patrón que no existe como palabra suelta: `\breason\b` y `-w reason` dan **los
   dos** cero, mientras `reason` sin límites da 5. Las dos formas coinciden en los dos
   sentidos.

2. **FALSA en el mecanismo — "el `.pth` está en site-packages, así que no alcanza con
   `sys.path.insert(0, ...)`".** El `.pth` del editable install es una **ruta pelada**, y
   `site` appendea esas entradas al final de `sys.path`. Un `insert(0, archive_root)` **sí**
   le gana para el módulo top-level; de hecho la corrida de pytest de la sesión testigo
   funcionó justamente por eso. El mecanismo real del fallo es otro: **`sys.path[0]` es el
   directorio del script, no el cwd**, así que un snippet guardado fuera del archive pierde
   aunque hayas hecho `cd` adentro (experimento A). Prueba de que el cwd sí alcanza cuando
   está en `sys.path`: el mismo import con `python -c` desde adentro del archive carga el
   viejo (experimento G, `HAS_NEW_SYMBOL=False`).

   La conclusión operativa del encargo igual se sostiene, por una razón distinta a la que
   daba: `insert(0)` no **saca** el root vivo, así que cualquier módulo ausente del archive
   sigue cayendo al árbol vivo en silencio. Por eso el helper poda además de insertar.

3. **INEXACTA — "~22% de `lib/*.py` son symlinks a `packages/*/lib/*.py`".** No existe
   `lib/` en el root de este repo (`ls -d lib` → *No such file or directory*). El
   directorio es `cos_lib/`, y ahí son **70 de 369 = 19,0%**:

   ```bash
   $ find cos_lib -maxdepth 1 -name "*.py" | wc -l          # 369
   $ find cos_lib -maxdepth 1 -name "*.py" -type l | wc -l  # 70
   ```

   El punto del encargo (hashear en vez de comparar rutas) queda intacto; la cifra y el
   path no.

4. **CONFIRMADA — `python -I` no aísla.** Verificada en el experimento B y fijada como
   test. El encargo tenía razón, y era la premisa más importante.

5. **CONFIRMADA — `timeout` no existe en este macOS.** `command -v timeout` sale 1 (invocarlo
   daría 127). El helper usa el `timeout=` de `subprocess.run`, no el binario.

6. **NO VERIFICADA — `git worktree` bloqueado por ADR-055b.** El ADR lo menciona en su
   lista (`docs/02-Decisions/adrs/ADR-055b-destructive-git-block.md:74`), pero **no probé el
   bloqueo**: obedecí la restricción usando `git archive`, que alcanzaba. La declaro sin
   verificar, igual que hizo la sesión testigo.

7. **CONFIRMADA — el caso testigo dice lo que el encargo dice.** El punto 3 de "Lo que no se
   sostuvo" en `agent-bus-flag-estricto-2026-08-15.md` describe exactamente el fallo, y su
   cierre ("si alguien reproduce el 'antes', que verifique `__file__` primero") es
   precisamente el verde barato que este helper reemplaza por una falla dura.

8. **Presupuesto: "~45 tool calls".** Se usaron ~25. No es error, es holgura.

## Archivos

- `scripts/revision_probe.py` — el helper (CLI + librería).
- `tests/unit/test_revision_probe.py` — 11 tests, todos de conducta.
- `docs/06-Daily/reports/medicion-antes-despues-blindada-2026-08-15.md` — este informe.

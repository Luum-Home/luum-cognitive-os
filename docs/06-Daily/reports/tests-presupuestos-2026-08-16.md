# Seis tests de presupuesto en rojo: qué se comprimió y qué número se movió

**Fecha:** 2026-08-16
**Alcance:** `tests/unit/test_efficiency_optimization.py`, `tests/unit/test_efficiency_stress.py`
**Resultado corto:** no se movió ningún número. Tres tests se arreglaron cambiando
*qué* miden; tres quedan en rojo a propósito, con el arreglo listo y frenado en un
límite de permisos.

## Resumen por test

| Test | Qué se hizo | Estado |
|---|---|---|
| `stress::TestHookPerformance::test_hook_chain_latency_per_bash` | Se cambió la medición de wall a CPU. Tope 2000 ms intacto | verde |
| `stress::TestHookPerformance::test_hook_chain_latency_per_agent` | Ídem. Tope 6000 ms intacto | verde |
| `optimization::test_contextual_rule_loader_fast` | Ídem. Tope 500 ms intacto | verde (ya venía verde en aislamiento) |
| `optimization::test_claude_md_token_budget` | Nada. Se comprimió el contenido en un candidato medido, sin aplicar | **rojo a propósito** |
| `stress::TestTokenBudgets::test_claude_md_token_budget` | Ídem | **rojo a propósito** |
| `stress::TestTokenBudgets::test_total_always_loaded_budget` | Ídem | **rojo a propósito** |

## Correcciones a las premisas del encargo

1. **No eran seis tests en rojo: eran tres.** Los tres de latencia pasaban corriéndolos
   solos, antes de tocar nada:

   ```
   $ .venv/bin/python -m pytest \
       "tests/unit/test_efficiency_stress.py::TestHookPerformance::test_hook_chain_latency_per_bash" \
       "tests/unit/test_efficiency_stress.py::TestHookPerformance::test_hook_chain_latency_per_agent" \
       -p no:randomly -q
   2 passed in 3.94s
   ```

   `test_contextual_rule_loader_fast` también pasaba solo. Fallan únicamente cuando la
   máquina está cargada, que es justamente el defecto.

2. **El archivo de instrucciones globales no existe en el repo.** El encargo lo trata
   como un archivo del proyecto. Los tres tests de tokens leen
   `Path.home()/".claude"/"CLAUDE.md"`: el archivo global y privado del usuario, fuera
   del repositorio, que gobierna *todos* sus proyectos. En el repo no hay ninguna copia.

3. **El repo declara explícitamente que ese archivo no es suyo.** `scripts/uninstall.sh:151`
   imprime `Your .claude/CLAUDE.md was NOT touched.` Ningún script ni hook del repo lo
   escribe. O sea: tres tests versionados acá bloquean sobre un archivo que el propio
   repo se declara sin derecho a tocar.

4. **En CI esos tests nunca corren.** Los tres hacen `pytest.skip("No global CLAUDE.md found")`
   si el archivo no está. En un checkout limpio no está. Así que el presupuesto que
   parece protegido no se aplica donde importa: sólo se dispara en la máquina del
   operador. Es un gate con sensación de cobertura y cero cobertura real.

5. **El directorio de reglas y el de config del harness son config protegida.** El guard
   `protected-config-write-guard.sh` frena hasta comandos de *lectura* que nombren esas
   rutas. El encargo lo daba como posibilidad; está confirmado, y además apareció un
   falso positivo: el guard también frenó la escritura de este informe a `docs/`, porque
   el texto del informe menciona esas rutas. Juzga el payload, no el destino.

6. **El `pytest` del PATH no tiene pytest.** `python3` resuelve a Homebrew 3.14 sin el
   paquete. El intérprete de la suite es `.venv/bin/python` (pytest 9.0.3).

## Los tres de latencia: se arregló la medición, no el tope

El encargo tenía razón: el número que importa es CPU, no reloj de pared. Wall mide
cuánto nos hizo esperar la máquina por un core, así que con la suite en paralelo el
mismo hook "tarda" varias veces más sin hacer nada distinto.

Medición propia, 12 cores, mismas cadenas PostToolUse, muestras A/B intercaladas
(n=5, mediana). La sonda que produjo esta tabla fue un artefacto de proceso; su
función quedó dentro de los propios tests, que ahora miden CPU y reportan wall al
lado, así que el comando reproducible es la corrida de pytest de más abajo.

| Escenario | Cadena | CPU (`RUSAGE_CHILDREN`) | wall | tope | factor wall/CPU |
|---|---|---|---|---|---|
| ocioso | Bash (14 hooks) | 690 ms | 774 ms | 2000 | 1.12x |
| ocioso | Agent (31 hooks) | 2447 ms | 2758 ms | 6000 | 1.13x |
| saturado | Bash | 1112 ms | 1653 ms (pico 2165) | 2000 | 1.49x |
| saturado | Agent | 3716 ms | 5169 ms (pico 5499) | 6000 | 1.39x |

Con los 12 cores saturados el **pico de wall de Bash cruzó el tope de 2000 ms mientras
el CPU se quedaba en el 56 % de ese tope**. Ahí está el rojo entero: la latencia real
no subió, subió la espera.

**Sobre portabilidad:** wall no es portable — depende de cuántos cores tenga la
máquina, qué más esté corriendo y cuántos workers de xdist compitan. Se sigue
reportando en el mensaje de error como corroboración, con esa aclaración escrita al
lado, y **no se assertea sobre él**. CPU tampoco es perfecto (también sube con
contención: 690 → 1112 ms), pero se mantiene dentro del tope, que es lo que se le pide.

Los tres topes quedan donde estaban: **2000, 6000 y 500**. Lo único que cambió es qué
se mide.

Efecto secundario que hacía falta arreglar: la versión vieja sumaba 5000 o 10000 ms
fantasma cuando un hook se pasaba del timeout. Un hook colgado en I/O no gasta CPU y se
escaparía de un tope de CPU, así que ahora **un timeout falla el test de frente**, con
el nombre del hook. Es más estricto que antes, no menos.

Verificación: los tres pasan con los 12 cores saturados, que es la condición que los
rompía.

### Holgura que quedó disponible y no se tocó

El tope de Agent (6000 ms) estaba documentado en el propio test como "~2000 ms de línea
base serial × 3x de headroom por carga paralela". Ese headroom se había comprado para
absorber contención de wall. Al medir CPU la contención desaparece, así que hoy son
2284 ms de holgura sobre el peor caso saturado. **No se bajó el número**: apretar un
ratchet también es moverlo, y es una decisión del operador, no un efecto secundario de
un arreglo de medición. Queda anotado acá para que se decida a la vista.

## Los tres de tokens: comprimir alcanzaba, y aun así quedan en rojo

### Medición

```
archivo global     21813 chars   ~5453 tokens   tope 3500   se pasa por 1953
RULES-COMPACT      12049 chars   ~3012 tokens   tope 4000 / 6000   entra
TOTAL                            ~8466 tokens   tope 7000   se pasa por 1466
```

El índice de reglas del repo —lo único de los dos que vive acá— entra cómodo. Todo el
exceso es del archivo global.

### Se intentó que entre, y entra

Antes de proponer mover nada se armó un candidato comprimido y se midió. No fue
invención: **ADR-044 ya diseñó exactamente esta compresión** y está en
`implementation_status: partial-blocked`. Su plan T2 es sacar los bloques largos del
archivo global y dejarlos detrás de slash-commands. Las cuatro zonas de aterrizaje
existen hoy: `sdd-help`, `engram-help`, `rules-expand`, `skills-search`.

| Sección | Antes | Después | Ahorro | Mecanismo |
|---|---|---|---|---|
| SDD Workflow | 4103 ch | 452 ch | 3651 | puntero a `/sdd-help` (ADR-044 T2) |
| Engram Protocol | 1670 ch | 608 ch | 1062 | disparadores + puntero a `/engram-help` (ADR-044 T2) |
| Agent Teams Orchestrator | 3987 ch | 1647 ch | 2340 | prosa a bullets densos |
| MANDATORY Self-Usage | 2007 ch | 1337 ch | 670 | prosa a bullets densos |
| bloques `Origen:` (5) | 1258 ch | 0 | 1258 | ver abajo |

```
ORIGINAL   21813 ch  ~5453 tok
CANDIDATO  12832 ch  ~3208 tok   tope 3500 -> ENTRA
reducción  41%       secciones conservadas: 10 de 10
COMBINADO  ~6220 tok             tope 7000 -> ENTRA
```

O sea: **el argumento para subir el tope estaba disponible y resultó innecesario**,
igual que con el bloque de reglas inyectadas de ayer. Los tres topes quedan intactos.

### Qué contenido se recorta y por qué se puede perder

- **Cuerpo de SDD Workflow** (pipeline detallado, grafo ASCII de dependencias, contrato
  de resultado, claves de topic, recuperación). No se pierde: se mueve a `/sdd-help`,
  que ya existe. Queda en línea lo que decide *cuándo* entrar al pipeline. Es el
  patrón que ADR-044 llama T2: cargar bajo disparo, no en cada sesión.
- **Detalle del protocolo Engram** (formato de título/tipo/scope, reglas de topic_key,
  manejo de conflictos). Igual: se mueve a `/engram-help`. Queda en línea el disparador
  proactivo, que es lo único que tiene que estar siempre presente para que el
  comportamiento ocurra.
- **Prosa de Agent Teams Orchestrator y MANDATORY Self-Usage.** No se borró ninguna
  regla: se pasaron de párrafo a bullet. El SCOPE GUARD, la regla de no bloquear, la
  persistencia de pedidos del usuario, el ruteo de modelos y los umbrales de costo
  siguen todos, textuales en lo que fijan.
- **Los cinco bloques `Origen:`** (1258 ch). Son la narración del incidente que motivó
  cada norma: fechas, repos, qué salió mal en julio. Para una persona que audita la
  norma valen; para un agente que la tiene que cumplir no cambian ni una acción — la
  instrucción es la regla de arriba. Es el caso de manual de `no-aclares-que-oscurece`:
  explicar por qué se decidió algo, ante alguien que no tiene que decidirlo. **Es lo
  más discutible del recorte**, y por eso va listado acá y no escondido: si el operador
  los quiere conservar, hay 292 tokens de margen bajo el tope para hacerlo parcialmente.

Nada de esto se aplicó.

### Por qué quedan en rojo

El arreglo cae en el archivo global de instrucciones del usuario: fuera del repo,
config privada, que gobierna todos sus proyectos y que este repo declara no tocar
(`scripts/uninstall.sh:151`). Reescribirla desde una tarea de "arreglar tests" es
exactamente el cruce que la norma de escrituras cross-repo manda frenar y plantear
antes. Así que: candidato medido y guardado, número sin tocar, tests en rojo.

**El candidato completo está en** `scratchpad/claude-md-candidate.md`. Es un artefacto
de proceso: si el operador lo aprueba, se aplica y los tres tests pasan solos, sin
tocar ningún tope.

### La decisión de fondo que queda abierta

Aparte de aplicar o no la compresión, hay una pregunta que este arreglo no puede
contestar: **¿debe un test de este repo bloquear sobre un archivo del `$HOME` del
operador?** Hoy ese test no protege nada en CI (se saltea) y sólo se dispara en una
máquina. Las opciones son aplicar la compresión y seguir como está, o mover el
presupuesto a lo que el repo sí gobierna. Las dos son decisiones del operador; ninguna
se tomó acá, porque tomarla desde adentro sería justamente reducir la medición.

## Verde barato que estaba servido y no se tomó

- **Subir los seis números.** Ninguno se movió. Los tres de latencia no lo necesitaban
  (el costo real nunca subió) y los tres de tokens tampoco (comprimir entra).
- **`skip` / `xfail`.** Ninguno. Los tres rojos quedan rojos y visibles.
- **Recortar el archivo global borrando lo que hacía falta.** El candidato conserva las
  10 secciones y todas las reglas; lo único que sale son dos bloques que se cargan bajo
  disparo por un mecanismo que ya existe, más la provenance, listada arriba una por una.
- **Bajar el tope de Agent aprovechando la holgura.** Apretar también es mover.

## Cómo reproducir

```bash
# los tres de latencia bajo saturación real: sin la saturación pasaban ya antes
# del arreglo, así que la carga es parte del experimento, no ruido
# VERIFICADO el 2026-08-19: 24 de estos loops estaban vivos con ppid=1 y mas de
# un dia de etime, y su linea de comando es literalmente el `for` de esta receta.
# La maquina estaba a load 466 sobre 12 CPUs; el barrido `cos-test broad` de ese
# dia dio 13 workers de pytest crasheados y 83 rojos fantasma, todos artefactos
# de esa saturacion (los mismos tests pasan aislados).
#
# NO VERIFICADO: por que exactamente no corrio el `kill` final. Se intento
# reproducir la fuga con la forma vieja y NO se reprodujo -- en una sonda local
# los hijos mueren con su subshell. El camino real pasa por el wrapper de shell
# del arnes, que no se pudo simular.
#
# El trap se agrega igual, y el motivo no depende de esa reproduccion: un kill
# posicional en la ultima linea no corre si algo corta antes, y la norma de
# evidencia ejecutable del repo pide que un script que cambia contexto lo
# restaure SIEMPRE, no solo en el camino feliz.
carga_pids=""
trap 'kill $carga_pids 2>/dev/null || true' EXIT INT TERM
for i in $(seq 1 12); do (while :; do :; done) & carga_pids="$carga_pids $!"; done
.venv/bin/python -m pytest \
  "tests/unit/test_efficiency_stress.py::TestHookPerformance::test_hook_chain_latency_per_bash" \
  "tests/unit/test_efficiency_stress.py::TestHookPerformance::test_hook_chain_latency_per_agent" \
  "tests/unit/test_efficiency_optimization.py::test_contextual_rule_loader_fast" \
  -p no:randomly -q
kill $carga_pids 2>/dev/null || true

# Si ya te quedaron huerfanos de una corrida anterior, aparecen asi:
#   ps -Ao pid,ppid,etime,pcpu,command | grep 'while :; do :; done' | grep -v grep
# Se reconocen por ppid=1 y un etime de horas o dias.
```

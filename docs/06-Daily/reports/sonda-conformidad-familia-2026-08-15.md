# Sonda de conformidad por familia — 2026-08-15

Instrumento: `scripts/family_conformance_probe.py`
Fixtures: `tests/fixtures/family-probe/home-path-leak/`
Guard de recurrencia: `tests/audit/test_family_conformance.py`

Enumera una familia de controles por **comportamiento** y marca al miembro que se
comporta distinto del resto. Una familia alcanzada de punta a punta (rutas de
home). Las otras dos no se alcanzaron, y abajo está por qué, con lo que se
aprendió al intentarlo.

## Veredicto en una línea

La idea funciona, y el par de fixtures **no alcanza**: hacen falta tres. Con dos,
16 de 37 candidatos se clasificaban como defectuosos por reaccionar a la
invocación y no al contenido, y un miembro roto de verdad salía conforme por una
rama del patrón que el discriminador nunca instanciaba.

## Cómo se define una familia

No por nombre, no por patrón, no por directorio. Una familia son **tres fixtures
y un screen de canal**, en un directorio bajo `tests/fixtures/family-probe/`:

| Fixture | Rol |
|---|---|
| `null.md` | contenido que toda la población tiene que ignorar |
| `must-trigger.md` | lo que todo miembro tiene que atajar |
| `must-not-trigger.md` | el discriminador: se **parece** al trigger y es legítimo |

Se corre cada candidato contra los tres, en un repo git descartable, bajo cada
forma de argv que declara la familia. La primera forma que reacciona al
must-trigger es la forma bajo la cual se juzgan las otras dos: un miembro nunca
se puntúa cruzando dos invocaciones distintas. La partición sale sola:

```
NON-MEMBER    calla ante must-trigger bajo toda forma
CONFORMING    reacciona al must-trigger, calla ante el discriminador
DEFECTIVE     reacciona a los dos  (sobre-dispara)
INVERTED      calla ante el trigger y reacciona al discriminador
NOISE         reacciona al null: mide la invocación, no el contenido
UNMEASURABLE  timeout o no se pudo ejecutar
```

Siguiendo `hooks/_lib/tool-outcome.sh`: **"no reaccionó" nunca colapsa en
"reaccionó bien"**. `NON-MEMBER` y `UNMEASURABLE` son clases propias y no suman a
`CONFORMING`.

### El null control no estaba en el encargo y es obligatorio

El encargo pedía un par. Medido: con solo dos fixtures, **16 candidatos de 37**
salían `DEFECTIVE`, porque reaccionan a la forma de argv que no aceptan (error de
uso, exit != 0) y eso pasa con cualquier contenido. El null los separa: quien
reacciona al null está midiendo la invocación, no el contenido, y sale de la
población. Sin el null, la lista de defectos tiene 16 falsos positivos y ocho de
cada nueve hallazgos son basura, o sea nadie la lee.

### El discriminador tiene que instanciar cada rama del patrón

Segundo hallazgo, más caro. Los miembros no comparten una sola regex: unos
matchean `home + segmento de cuenta`, otros además `home + segmento + /Projects/`.
Con un discriminador que solo instanciaba la primera rama,
`hooks/research-compliance-guard.sh` salió **CONFORMING en la revisión donde se
sabe que estaba roto**. La corrida quedó registrada: el disidente conocido pasó
como sano. Agregar la línea que ejerce la segunda rama (línea 10 de
`must-not-trigger.md`) lo dio vuelta al toque.

Esto es lo que más cuesta de escribir una familia y es la única parte que exige
mirar la implementación de al menos un miembro.

### El screen de canal, y dónde puede volver a esconderse un miembro

Ejecutar los 709 scripts de `hooks/` y `scripts/` no es ni rápido ni seguro
(instaladores, dispatchers de LLM y daemons viven ahí). El screen pregunta una
sola cosa: **¿puede leer contenido staged del repo?** (`diff --cached`,
`ls-files`, `--staged`). Deja pasar 37.

Es deliberadamente **ortogonal al patrón** de la familia: el guard que concatena
su literal para no dispararse a sí mismo igual dice `git diff --cached` en claro.
Pero es el único lugar donde un miembro todavía puede esconderse, y de hecho hay
uno escondido ahí: ver "Qué no cubre".

## La salida real de la sonda

Comando (read-only, no escribe nada en el repo real):

```bash
python3 scripts/family_conformance_probe.py            # árbol de trabajo
python3 scripts/family_conformance_probe.py --at HEAD  # estado commiteado
python3 scripts/family_conformance_probe.py --at 3a6e737ba~1
```

Los tres escaneos: 709 candidatos, 37 pasan el screen, **4 miembros**.
Medido contra `HEAD = ca2d947c3` (`git rev-parse --short HEAD`).

| Candidato | `3a6e737ba~1` | `HEAD` | árbol de trabajo |
|---|---|---|---|
| `scripts/check-local-privacy.sh` | **DEFECTIVE** | CONFORMING | CONFORMING |
| `scripts/check_absolute_paths.py` | **DEFECTIVE** | CONFORMING | CONFORMING |
| `hooks/research-compliance-guard.sh` | **DEFECTIVE** | **DEFECTIVE** | **DEFECTIVE** |
| `scripts/provenance_scan.py` | **DEFECTIVE** | **DEFECTIVE** | **DEFECTIVE** |

Además, en el árbol de trabajo: 16 `NOISE`, 1 `UNMEASURABLE`
(`scripts/derived_artifact_gate.py`, timeout de 10s sobre un solo archivo
staged), 16 `NON-MEMBER`.

### ¿Redescubrió los defectos conocidos?

**Sí, y sin que se le dijera dónde estaban.** La sonda no conoce ningún nombre:
recibe tres fixtures y un screen de canal. La columna `3a6e737ba~1` es la
verificación: en la revisión anterior al arreglo, los dos guards que ese commit
reparó vuelven a salir `DEFECTIVE`. Es la dimensión de mutación, sobre historia
real en vez de un mutante sintético.

Y el disidente que el encargo pedía señalar —`hooks/research-compliance-guard.sh`—
sale marcado en las tres corridas.

### Un cuarto miembro que nadie había reportado

`scripts/provenance_scan.py` está en la familia y está roto, en las tres
revisiones. Nunca apareció en ninguno de los censos de hoy. Mensaje textual sobre
el discriminador:

```
docs/06-Daily/reports/probe-fixture.md:8: forbidden-path: /Users/[a-zA-Z0-9._-]+ — host-local o non-canonical path
```

Es exactamente el defecto que 3a6e737b arregló en los otros dos: lee la regex
citada dentro de un comando documentado como si fuera una ruta real. La sonda lo
encontró en la primera corrida, antes de tener el discriminador completo.

### El arreglo en vuelo de `research-compliance-guard.sh` está incompleto

El encargo avisaba que otro agente lo estaba arreglando ahora mismo. Verificado:
`git status` lo muestra modificado sin commitear, y el archivo ya trae
`_describes_a_username`, citando 3a6e737b. **Medido: no alcanza.** Con el
discriminador completo el guard sigue bloqueando, en HEAD y en el árbol de
trabajo por igual:

```
=== RESEARCH-COMPLIANCE-GUARD: BLOCKED ===
  - docs/06-Daily/reports/probe-fixture.md: contains a personal absolute home path
```

La rama que falla es la segunda alternativa de su `HOME_PATH_RE` (la que exige
`/Projects/` después del segmento): el exento por descripción se aplica a la
clasificación del token, y esa rama no pasa por ahí. No se tocó el archivo. Es de
ese cambio, no de este.

### La fixture peligrosa no se guarda: se compone

Una fixture cuyo trabajo es **contener** la cosa mala no puede almacenarse
literal en un repo que escanea buscando la cosa mala. No es un defecto de la
sonda: es la misma pared que hizo difícil enumerar esta familia, vista del otro
lado del espejo.

La respuesta ya estaba en el repo. `hooks/research-compliance-guard.sh` arma su
propio patrón en tiempo de ejecución (`MAC_HOME_SEG='/'"Users"`) justamente para
no dispararse a sí mismo, que es la propiedad que lo volvió invisible al censo
por grep que lo dejó afuera. Las fixtures hacen lo mismo: en `family.yaml` un
valor de sustitución puede ser una **lista de piezas**, y se junta recién cuando
la sonda escribe el archivo en su sandbox.

```yaml
substitutions:
  "[[HOME]]": ["/", "Users"]
  "[[PROBE_USER]]": ["mnprobe"]
```

Dos mejoras además de destrabar el commit:

1. La fixture deja de ser un archivo que hay que exceptuar en cada gate nuevo.
2. La composición **dice** qué hace peligrosa a la entrada, en vez de dejarlo
   implícito en un archivo de ejemplo.

El reverso importa y no salió como debería: **`must-not-trigger.md` tendría que
poder vivir literal**, porque su contenido es exactamente el caso legítimo. No
puede, y eso no es un problema de composición: es que dos miembros de la familia
todavía no tienen el discriminador. Que el discriminador no pueda guardarse
literal **es** el hallazgo, no un detalle de empaquetado. Se compone también,
para poder entregarlo, y queda escrito acá que el día que los dos miembros estén
arreglados esa composición sobra.

## La misma corrida como guard de recurrencia

`tests/audit/test_family_conformance.py` no es un segundo instrumento: es el
mismo script corrido en otro momento. Tres aserciones:

1. **Guarda de población.** Si la familia escanea a menos miembros que los que
   declara (`min_members: 2`), falla. El verde barato de este lote es una sonda
   que no encuentra nada y sale 0; queda cerrado acá y también en el script, que
   sale 2 si una familia se queda sin miembros.
2. **Partición exacta.** El conjunto defectuoso conocido se compara con `==`, no
   con `<=`. Un ledger por encima de la realidad es un colchón: deja lugares
   libres reportando "0 nuevos". Cuando alguien arregle uno de los dos, el test
   se pone rojo y hay que borrar la entrada. Así es como se entera de que el
   arreglo llegó.
3. **La sonda sigue mordiendo.** Corre `--at 3a6e737ba~1` y exige que los dos
   guards que ese commit reparó salgan `DEFECTIVE`. Si alguien afloja los
   fixtures hasta que todo parezca conforme, esta aserción lo agarra.

```
.venv/bin/pytest tests/audit/test_family_conformance.py -q
3 passed in 70.69s
```

Las dos entradas del ledger llevan escrito el motivo por el que no se arreglan
acá: este encargo mide, y los dos archivos son de otro dueño.

## Costo de agregar una familia nueva

Un directorio con cuatro archivos: `family.yaml` (unas 15 líneas útiles) y los
tres fixtures. Sin plugins, sin registry, sin clase base: el script globea el
directorio.

Reparto real del esfuerzo en esta familia:

- `null.md` y `must-trigger.md`: minutos.
- `family.yaml`: minutos, salvo el `channel_screen`, que hay que pensar.
- **`must-not-trigger.md`: ahí se va el 80%.** Escribir un discriminador que
  ejerza todas las ramas del patrón obliga a leer la implementación de al menos
  un miembro. Se llegó a la versión correcta después de dos corridas completas
  que daban un falso CONFORMING.

Costo de corrida: 55s para 37 candidatos (10s de timeout por corrida, 16 hilos).

Conclusión honesta sobre el costo: **paga cuando la familia tiene 3 o más
miembros y el discriminador es escribible sin leer a todos.** Para una familia de
dos, escribir el par cuesta más que mirar los dos archivos.

## Qué no cubre

- **Una sola familia.** Las otras dos del encargo no se alcanzaron. Ver abajo.
- **El screen de canal es el escondite que queda.** Un miembro que no lee
  contenido staged no entra a la población. Hay uno confirmado:
  `hooks/confidentiality-enforcer.sh` bloqueó la escritura del propio
  `must-trigger.md` de esta sonda, sobre un segmento entre corchetes, o sea sin el
  discriminador de 3a6e737b. Vive en el canal PostToolUse (lee el payload de la
  herramienta, no el índice de git), así que el screen de esta familia no lo ve.
  Se reporta como observación directa, no como veredicto de la sonda: para
  medirlo hace falta declarar un segundo canal de entrega, con su payload.
- **Sub-dispara.** La partición detecta el que bloquea de más. Un miembro que
  deja pasar el `must-trigger` sale `NON-MEMBER`, indistinguible de quien no es de
  la familia. Es la asimetría del método: la sonda ve sobre-disparo, no
  sub-disparo.
- **`NOISE` no se investiga.** 16 candidatos reaccionan a cualquier invocación.
  Alguno podría ser miembro con otra forma de argv; la sonda no lo persigue.
- **`UNMEASURABLE` es un agujero real.** `derived_artifact_gate.py` da timeout con
  un solo archivo staged. No se sabe si es miembro.
- **No lee `manifests/claude-code-hooks-schema.yaml`.** Esa familia necesita otra
  forma de veredicto, ver abajo.

## Las otras dos familias, y qué se aprendió al no llegar

**Salida de hooks.** No se construyó. El motivo no es tiempo: es que la partición
en tres no aplica igual. Ahí el veredicto no es "reaccionó / no reaccionó" sino
"la forma de lo que emitió es válida contra un esquema". Encaja en las mismas
clases (emite válido = conforme / emite inválido = defectuoso / no emite = fuera
de la familia), pero el rol del discriminador no lo juega un segundo fixture: lo
juega `manifests/claude-code-hooks-schema.yaml`. **Es la misma idea con el
discriminador reemplazado por un predicado.** Generalizarlo es un cambio chico y
honesto en el script (un `verdict_mode: schema`), y es lo que recomendaría hacer
primero.

**`error-learning.jsonl`.** Tampoco se construyó, y acá la refutación es más
fuerte: el defecto no es un veredicto sobre una entrada, es **qué ruta toca** el
candidato. La reacción observable no es el exit code sino el efecto de
filesystem. Se puede medir con la misma máquina (correr en sandbox y diffear qué
archivos aparecieron), pero el fixture ya no es "una entrada que debe disparar":
es un sandbox y una ruta canónica esperada. Es otra especie. El guard que ya
existe para eso —`tests/audit/test_error_learning_single_path.py`— es la mitad
correcta y no tiene sentido duplicarla.

**La generalización que sí se sostiene**: una familia es *una entrada, y un
predicado que separa la reacción correcta de la incorrecta*. Cuando ese predicado
es "no reacciona", se escribe como un segundo fixture. Cuando es un esquema, se
escribe como esquema. El encargo describía el caso particular como si fuera el
general.

## El commit de este lote esta bloqueado, por el miembro que la sonda encontro

`scripts/provenance_scan.py` esta registrado como gate de PreToolUse (via
`hooks/bash-hot-path-dispatcher.sh` para `git commit`, y como
`hooks/provenance-scan.sh` para Edit/Write), y bloquea el commit de los fixtures
que prueban que esta roto. Cinco hallazgos sobre `must-not-trigger.md`, uno sobre
`must-trigger.md` y uno sobre un comentario del test:

```
BLOCKED: provenance-scan found sensitive provenance or local-source leakage.
tests/fixtures/family-probe/home-path-leak/must-not-trigger.md:8  forbidden-path
tests/fixtures/family-probe/home-path-leak/must-not-trigger.md:10 forbidden-path
tests/audit/test_family_conformance.py:51 forbidden-path
```

Mientras esos archivos estan staged, el mismo guard bloquea tambien cualquier
Edit sobre cualquier archivo del repo: escanea el conjunto staged entero en cada
escritura. Esta seccion se pudo escribir recien despues de sacarlos del index.

No se uso ninguna variable de bypass y no se toco el guard: este lote mide, y la
norma dice reportar el bloqueo y entregar el contenido igual. Los archivos quedan
escritos en el arbol de trabajo, sin commitear, esperando decision del operador.

Las dos salidas posibles, y cual es cual:

- **Arreglar `provenance_scan.py`** con el mismo discriminador de 3a6e737b, que
  es exactamente lo que la sonda dice que le falta. El bloqueo desaparece porque
  desaparece el defecto.
- **Excluir `tests/fixtures/family-probe/` del scanner.** Se puede defender con
  la pregunta de gates-sin-trampa (un cambio en el scanner no deberia obligar a
  tocar los fixtures), pero **sola es el verde barato**: apaga el rojo sin tocar
  la causa y deja al cuarto miembro roto contra todo el resto del repo.

El orden importa: primero el arreglo, la exclusion despues si sigue haciendo
falta. No es una hipotesis del informe. Es la corrida de hoy: el defecto que el
instrumento encontro le impidio al instrumento entrar al repo.

## Correcciones a las premisas del encargo

1. **"El tercer enforcer construye su literal por concatenación, así que es
   invisible a cualquier grep del patrón" — cierto de él, y de los otros dos
   también.** `scripts/check_absolute_paths.py` línea 21 hace
   `MAC_HOME_PREFIX = "/" + "Users" + "/"` y `scripts/check-local-privacy.sh`
   línea 33 lo mismo. Los tres se esconden igual. Entonces la concatenación **no
   es lo que diferenció al tercero**: si el censo hubiera sido por grep del
   patrón, no habría encontrado ninguno, y encontró dos. Lo que los une no es el
   texto sino el comportamiento, que es la conclusión del encargo, pero la
   evidencia que la sostiene no es la que el encargo cita.

2. **"El par de sondas es la especificación del defecto" — refutado, medido.**
   Hacen falta tres fixtures. Con dos: 16 falsos `DEFECTIVE` de 37 candidatos.
   Y el discriminador tiene que instanciar cada rama del patrón, o un miembro roto
   sale conforme (pasó con `research-compliance-guard.sh`, dos corridas).

3. **"Familia rutas → tiene que señalar `hooks/research-compliance-guard.sh`" —
   lo señala, y hay un cuarto miembro roto que el encargo no conocía**
   (`scripts/provenance_scan.py`), más un quinto en otro canal
   (`hooks/confidentiality-enforcer.sh`, observado, no medido). La familia era más
   grande que 3.

4. **"Hay otro agente arreglando `research-compliance-guard.sh` ahora mismo" —
   confirmado, y el arreglo está incompleto.** `git status` lo muestra modificado
   sin commitear; el archivo ya trae el discriminador de 3a6e737b y **igual
   bloquea** la segunda rama del patrón. No se tocó.

5. **"No modifiques ningún guard ni hook" — verificado y cumplido.** `git status`
   confirma que los dos archivos en vuelo son de otra sesión. La sonda no escribe
   nada fuera de su sandbox: cwd, `HOME`, `COGNITIVE_OS_PROJECT_DIR`,
   `CLAUDE_PROJECT_DIR` y `CODEX_PROJECT_DIR` apuntan a un tmpdir descartable, y
   se borran las variables de bypass del entorno antes de cada corrida.

6. **`hooks/_lib/tool-outcome.sh` no se reutilizó.** El encargo lo señalaba como
   existente. Se tomó su distinción de cuatro estados (que es la parte que
   importa) y no su código: clasifica el resultado de una herramienta del harness
   a partir de un `tool_response`, no el exit code de un proceso ejecutado en un
   sandbox. Reusarlo habría exigido fabricar un `tool_response` falso, que es la
   forma de teatro que este encargo prohíbe.

7. **Un gate bloqueó trabajo de este encargo y se reporta en vez de saltarlo.**
   `hooks/confidentiality-enforcer.sh` bloqueó la escritura de
   `must-trigger.md`. El archivo quedó escrito igual (el hook es PostToolUse) y no
   se usó ninguna variable de bypass. Ese bloqueo es el que destapó al quinto
   candidato.

9. **"Acabo de commitear `CI_MACHINE_SEGMENTS` en los cuatro enforcers" (mensaje
   del coordinador) — no está en HEAD.** Medido: `git rev-parse --short HEAD` da
   `ca2d947c3` (`fix(error-learning): stop a unit test writing into operator
   telemetry`) y `git log --oneline -2` no muestra ese commit. La corrida
   posterior al aviso da el mismo resultado que la anterior: dos DEFECTIVE. O el
   commit quedó en otra rama, o todavía no aterrizó. Los dos guards que sí
   aparecen conformes lo están desde 3a6e737b, no desde ese cambio.

10. **"~50 tool calls"** — se usaron unas 40, con una familia entera y las otras
   dos analizadas hasta el punto de poder decir por qué no encajan.

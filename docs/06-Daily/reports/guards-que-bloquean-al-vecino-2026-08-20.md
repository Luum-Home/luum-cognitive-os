# Guards que bloquean al vecino — 2026-08-20

## Resumen ejecutivo

El censo lo produce `scripts/audit_shared_state_guards.py` y mide dos propiedades
por separado, sobre dos poblaciones distintas a propósito.

- **Estado compartido:** de los 152 hooks registrados, **7 bloquean decidiendo
  sobre estado que comparten todas las sesiones** del checkout (índice de git,
  árbol de trabajo, rama, archivos de `.cognitive-os/` que no son por sesión).
- **Atribución:** antes **2 de 7** podían atribuir el estado a quien dispara;
  ahora **3 de 7**.
- **Escape:** **19 guards bloquean y ofrecen bypass**; antes **5** tenían vía
  ejecutable a mitad de sesión, ahora **7**.
- Se arreglaron **cuatro**: `scope-marker-portability-gate` (atribuye por el
  pathspec del commit), `subagent-budget-enforcer` (escape por `bypass.env`, con
  motivo obligatorio y fila de auditoría), y los **dos gates de
  `.githooks/pre-commit`** que auditaban el árbol entero — aparecieron porque
  bloquearon este mismo commit por dos scripts sin trackear de otra sesión.
- El arreglo de mayor rendimiento fue el que anticipaba el encargo: **`bypass.env`
  ahora transporta cualquier variable `COS_*`**, no sólo `COS_BYPASS`.
- 7 pruebas en `tests/contracts/test_guards_attribute_to_their_trigger.py`; las 2
  que dependen del arreglo **fallan contra `HEAD`** y las 5 de control pasan en
  ambas versiones.

## Correcciones a las premisas del encargo

**1. "Cuatro instancias medidas hoy" — son al menos seis, y tres me las comí yo
durante esta misma tarea.** `protected-config-write-guard` bloqueó dos comandos
**read-only** míos porque las rutas protegidas aparecían en el *texto*: un
`python3 -c` que hacía `json.load(open(...))` sobre el settings, y un
`source hooks/_lib/bypass-resolver.sh`. Ninguno de los dos escribe nada.

Es la misma familia que la instancia 4 (`block-destructive-bash`), que me bloqueó
**dos veces**: una leyendo barras dentro de una sustitución `sed` y de un `rm -rf`
sobre un `mktemp`, y otra — la más clara — leyendo barras dentro de un
**heredoc que era prosa**: el intento de escribir *este mismo informe* con
`cat > archivo.md` se bloqueó porque el texto del informe cita rutas. El comando
no borraba nada; describía. La familia "detecta por el texto del comando y no por
lo que el comando hace" es más grande de lo que decía el encargo, y su síntoma
más caro no es el falso positivo suelto sino que empuja a rodear la herramienta.

**2. "El índice de git tiene `git diff --cached --name-only`, y una sesión sabe
qué archivos tocó" — la segunda mitad no hace falta, y es peor.** No hay que
preguntarle a la sesión qué tocó: `git commit -- <paths>` **ya dice** de qué se
hace cargo el disparador, y `git diff --cached --name-only -- <paths>` deja que
git resuelva la expansión de directorios y globs. La atribución sale **exacta y
sin heurística**, sin que el hook lleve registro de nada. Una atribución basada
en "lo que la sesión recuerda haber tocado" habría sido adivinanza; ésta es
lectura.

**3. "Cinco vías conocidas" — para efectos prácticos son dos, y una tercera que
no es una vía sino una propiedad de cada hook.** `export` antes del arnés y el
bloque `env` de `settings.json` exigen relanzar: inútiles para quien ya está
bloqueado. El token en posición de prefijo **sólo funciona en los hooks que
además leen el texto del comando** (el ancla de
`protected-config-write-guard.sh:48`), o sea que no es una vía del sistema.
La única accionable a mitad de sesión de forma general es `bypass.env` — el
encargo ya lo decía, pero listarla como una de cinco le baja el peso que tiene:
es *la* vía.

**4. La premisa sobre `bypass.env` y las compañeras era correcta, y además
sub-estimaba el problema.** Era cierto que transportaba sólo `COS_BYPASS`. Lo que
el encargo no decía es que **`subagent-budget-enforcer` ni siquiera usaba el
resolvedor**: `grep -c cos_bypass_allows hooks/subagent-budget-enforcer.sh`
devolvía `0`, y su clave no estaba en `_cos_bypass_legacy_alias_allows`. O sea que
`COS_BYPASS=subagent_budget` no lo habría destrabado ni con el transporte ya
arreglado. Hacían falta las dos cosas, no una.

**5. Mi propio censo, primera versión, estaba inflado: decía 42.** Contaba como
"decide sobre estado compartido" a todo hook que mencionara `.cognitive-os/`, y
casi todos escriben ahí su telemetría. Escribir una métrica no es decidir. Con la
lectura separada de la escritura, y con las rutas por sesión excluidas (llevan el
`SESSION_ID` o el `AGENT_ID`, así que son propias por construcción), el número
real es 7. Dejo el error dicho porque el 42 era el número cómodo: justificaba un
cambio mucho más grande del que hacía falta.

**6. Corrección sobre mi propio instrumento, segunda pasada.** El censo contaba
como "sin vía de escape" a cualquier hook que nombrara una variable `*_REASON`,
sin fijarse si era **obligatoria**. `${VAR:-}` con default vacío obliga a
chequearla; `${VAR:-algo}` ya trae respuesta y no traba a nadie. Sin esa
distinción el censo se inflaba su propio hallazgo — incluido uno que yo mismo
acababa de introducir.

## Cuántos deciden sobre estado compartido

```
$ python3 scripts/audit_shared_state_guards.py
guards que bloquean y deciden sobre estado compartido: 7
  atribuyen al disparador: 3
  NO atribuyen:            4
  con escape a mitad de sesión: 4
```

| guard | estado compartido | atribuye |
|---|---|---|
| `destructive-git-blocker.sh` | worktree, branch | sí |
| `direct-main-guard.sh` | branch | sí |
| `scope-marker-portability-gate.sh` | git_index | **sí (arreglado hoy)** |
| `git-commit-scope-guard.sh` | git_index, branch | no |
| `research-compliance-guard.sh` | git_index, cache externo | no |
| `quality-duplicates.sh` | worktree | no |
| `provenance-scan.sh` | `provenance-scan.yaml` | no |

La población excluye a propósito los hooks que sólo *escriben* en
`.cognitive-os/`, y los que leen una ruta que lleva su propio `SESSION_ID` o
`AGENT_ID` — ese estado es suyo, y atribuirlo es trivial.

## Atribuible vs no atribuible, con la evidencia

**Atribuible, demostrado:** `scope-marker-portability-gate`. La evidencia es que
`git commit -- <paths>` commitea únicamente esas rutas; lo demás que esté en el
índice no entra. Entonces bloquear por lo demás es un falso positivo *probable*,
no discutible. El gate ahora le entrega el pathspec al propio git —quien sabe
expandir un directorio o un glob— y juzga sólo lo que va a entrar. Cuando el
comando **no** trae pathspec vuelve al índice entero, porque ahí el commit sí se
lleva todo y mirarlo todo es lo correcto. El gate no aflojó: cambió de qué se
hace cargo el disparador.

**Genuinamente no atribuible, con el motivo:** `quality-duplicates` mide
duplicación sobre el árbol de trabajo. Un duplicado es una relación *entre dos
archivos*, y el segundo puede perfectamente ser del vecino. No hay pathspec que
lo salve: acotar la lectura a mis archivos haría que el gate deje de ver
exactamente el caso que le importa. Ahí la respuesta no es atribuir sino que el
mensaje diga cuál de los dos archivos es del que dispara.

**No atribuible por ahora, pero sí en principio:** `git-commit-scope-guard` y
`research-compliance-guard` leen el índice entero y aceptarían el mismo pathspec.
No los toqué en esta tanda: el helper `cos_git_commit_pathspec` quedó en
`hooks/_lib/git-command-parse.sh`, que es de donde ya se sirven, así que el
cambio es de una línea cada uno. Lo dejo dicho como deuda con nombre.

### El tercer y cuarto guard, encontrados porque bloquearon este commit

No estaban en el censo de hooks porque no son hooks del arnés: son los gates 3g
de `.githooks/pre-commit` (`core.hooksPath=.githooks`, así que ése es el vivo;
`.git/hooks/pre-commit` es un residuo de mayo que git ignora).

El encabezado del gate ya decía **"for staged primitive changes"** y calculaba
`staged_primitives`… para usarlo únicamente como *disparador*. Después corría
`cos-scope-both-portability-audit --strict` y `cos-scope-projection-audit
--strict` sobre el **filesystem entero** — 358 y 1500 artefactos. La intención
estaba escrita y la implementación no la cumplía.

Lo que lo destapó: mi commit quedó bloqueado por
`scripts/portability-two-way-proof.sh` y `scripts/portability_census.py`, dos
archivos **sin trackear** (`??`, sin `git log`) que otra sesión dejó en el árbol
compartido y que mi commit no tocaba. Es la forma más pura del defecto: no ya el
índice compartido sino el árbol entero, donde ni siquiera hace falta que el
vecino haya hecho `git add`.

Ahora los dos gates intersectan sus hallazgos con las primitivas que realmente
entran en el commit. **La auditoría completa sigue corriendo y sigue reportando
los 2 faltantes**: no se excluyó estado compartido para tapar falsos positivos,
cambió a quién bloquea. El barrido de todo el árbol sigue siendo autoridad en
`scripts/cos-ci-local.sh quick`, donde no hay disparador a quien atribuirle nada
y mirar todo es lo correcto.

Un detalle que decidí a propósito: un hallazgo **sin artefacto** (violación del
contrato global, no de un archivo) sigue bloqueando a cualquiera, porque no hay
a quién atribuírselo y dejarlo pasar sería el verde barato.

## Escape ejecutable: quiénes lo tienen

```
escape — guards que bloquean y ofrecen bypass: 19
  con vía a mitad de sesión (bypass.env): 7
  trabados por variable compañera: 2 (direct-main-guard.sh, orchestrator-skill-invocation-gate.sh)
```

Un hook es **hijo del arnés**, no del shell del Bash tool: un prefijo
`VAR=1 <comando>` le pone la variable al comando y el hook ya decidió antes de
que ese shell existiera. Por eso las vías que exigen `export` o editar
`settings.json` no le sirven a quien está bloqueado *ahora*: las dos piden
relanzar. La única general a mitad de sesión es
`.cognitive-os/runtime/bypass.env`, que `cos_bypass_allows` relee en cada
invocación (ADR-241).

Quedan **2 guards trabados por variable compañera obligatoria**:
`direct-main-guard` y `orchestrator-skill-invocation-gate`. Con el transporte ya
arreglado, destrabarlos es cambiar su lectura de `${COS_..._REASON:-}` a
`cos_bypass_var COS_..._REASON`, igual que hizo `subagent-budget-enforcer`. No lo
hice en esta tanda porque `direct-main-guard` decide sobre la rama compartida y
merece su propia medición, no un cambio de arrastre.

## bypass.env y las variables compañeras

Era el arreglo de mayor rendimiento y resultó serlo. `_cos_bypass_combined_list`
sabía leer **una sola clave**, `COS_BYPASS`. Todo bypass que exige una compañera
—los `*_REASON` de `direct_main`, `direct_push`, `skill`, `subagent-budget`—
tenía su clave en el resolvedor y aun así no había cómo activarlo a mitad de
sesión, porque el motivo no tenía por dónde viajar.

Ahora `_cos_bypass_runtime_var` lee **cualquier** variable del archivo y
`cos_bypass_var <NOMBRE>` la resuelve con el entorno primero y el archivo
después. El entorno gana porque `export` antes del arnés es la vía deliberada del
operador; el archivo es la vía de quien ya está trabado y no puede relanzar nada.

Dos límites puestos a propósito:

- **Sólo nombres `COS_*`.** El archivo es una vía de activación de bypass, no un
  mecanismo genérico para inyectar entorno en los hooks. Probado: una línea
  `EVIL=pwned` en `bypass.env` no se lee.
- **El motivo sigue siendo obligatorio.** `COS_BYPASS=subagent_budget` sin
  `COS_SUBAGENT_BUDGET_BYPASS_REASON` **no destraba** — sigue devolviendo 2.
  Está cubierto por `test_corrida2_control_el_escape_sin_motivo_no_destraba`.

Y cada activación deja fila en `.cognitive-os/metrics/bypass-activation.jsonl`
con clave, hook, motivo, sesión, pid y si vino del entorno o del archivo. El
objetivo nunca fue que sea más fácil pasar: es que quede escrito quién pasó y por
qué.

## Las tres corridas

Todas en `tests/contracts/test_guards_attribute_to_their_trigger.py`, sobre repos
de `tmp_path` — no se toca el checkout compartido, que es justamente el recurso
cuyo mal uso se está midiendo.

```
$ .venv/bin/python3 -m pytest tests/contracts/test_guards_attribute_to_their_trigger.py -q
7 passed in 5.64s
```

**1. Bloqueo por archivo ajeno.** Sesión A stagea `hooks/vecino-sin-proof.sh`
(marcado, sin proof). Sesión B commitea lo suyo acotando con pathspec. B pasa.
**Y A sigue bloqueada** cuando commitea *su* archivo — ése es el control que
impide el verde barato de "ahora no bloquea a nadie". Un tercer caso cubre el
commit **sin** pathspec, que debe seguir mirando el índice entero.

**2. Bloqueo sin escape.** El agente cortado en el llamado 61 de 50 escribe las
dos líneas en `bypass.env` y sigue. Se verifica además que la fila de auditoría
quedó, con el motivo textual.

**3. El guard sigue guardando.** El presupuesto sigue cortando sin bypass, y una
primitiva nueva sin marcador `SCOPE` sigue bloqueando.

**Falsación de las tres corridas** — una prueba que pasa sin el arreglo no prueba
nada. Corriendo el mismo archivo contra las versiones de `HEAD`
(`git show HEAD:hooks/...`):

```
FAILED test_corrida1_el_vecino_sucio_no_bloquea_el_commit_acotado
FAILED test_corrida2_el_cortado_se_destraba_con_bypass_env_y_deja_auditoria
2 failed, 5 passed
```

Las 2 que dependen del arreglo fallan; las 5 de control pasan en ambas versiones,
que es exactamente lo que tienen que hacer.

## Dónde decidí que NO debe haber escape, y por qué

**`scope-marker-portability-gate`, para el commit sin pathspec.** Podría haber
hecho que el gate adivinara el alcance también sin `--`, mirando por ejemplo qué
archivos modificó la sesión. No lo hice, y es deliberado: un pathspec leído de
**menos** bloquea a un inocente, uno leído de **más** deja pasar una primitiva
sin revisar. El primer error se paga con un mensaje que enseña a acotar el
commit; el segundo se paga con una primitiva sin proof en `main`. Ante la duda,
el gate vuelve al índice entero.

**El motivo obligatorio del bypass, en todos los casos.** Se podría argumentar
que un motivo obligatorio es fricción sobre alguien que ya está trabado. Es
justamente lo contrario de lo que hay que hacer: sin el motivo, el escape es una
puerta anónima y el guard se vuelve decoración. La fricción no está para
disuadir, está para que quede el nombre.

**`quality-duplicates`: que siga sin escape.** No le agregué bypass. Un duplicado
es deuda real o es coincidencia, y las dos salidas correctas son unificar o
dejarlo aceptado con el motivo escrito. Un bypass acá sería el verde barato de la
familia dedup.

**No toqué `destructive-git-blocker`.** Bloquea todo commit sobre `main`, y eso
es correcto: el bloqueo es siempre culpa de quien lo dispara — el que commitea es
el que está parado en `main`. Su problema medido es otro y es real: el remedio
`cos-session-branch.sh --switch` hace `git switch` sobre el árbol entero, así que
dos procesos del mismo checkout terminan viendo la misma rama de sesión. Pero eso
es un defecto del **remedio**, no del guard, y arreglarlo bien pide un worktree
por sesión en vez de un switch. Es una decisión de arquitectura con dueño: la
dejo planteada, no la resuelvo de costado.

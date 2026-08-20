# Juicio: mencion vs escritura en protected-config-write-guard

Fecha: 2026-08-20 · Rol: juez (read-only) · Repo: luum-agent-os

## Veredicto

**LA PREGUNTA ESTA MAL PLANTEADA.** El guard bloquea unicamente rutas escritas
*literalmente*: cinco formas distintas de armar la misma ruta por concatenacion
pasan sin bloqueo hoy. O sea que el guard no puede ser lo que su propio
manifiesto dice que es (anti-inyeccion), y la discusion sobre exentar menciones
esta regateando el precio de la puerta con la cerradura abierta.

La pregunta correcta no es "estos 10 deberian quedar bloqueados", es: **dado que
el guard solo ve rutas deletreadas, para que sirve — y el registro que produce
dice la verdad?** Hoy no: 19 de 22 bloqueos vigentes asientan una escritura al
plano de control que nunca ocurrio.

Recomendacion sin ambiguedad: **que el agente que esta intentando exentarlos
pare.** El esfuerzo va a cerrar el bypass. Argumento en "Que deberia hacer el
agente que esta implementando".

## Correcciones a las premisas del encargo

1. **No son 21 bloqueos vivos, son 22.**
   `env -u COS_ALLOW_PROTECTED_CONFIG_WRITE .venv/bin/python3 scripts/audit_guard_mention_blocks.py`
   -> `replay contra el guard de HOY -> sigue bloqueando: 22`.

2. **No son 10 heredocs que escriben a `tests/` o `scripts/`.** Leidos uno por
   uno: **19 de los 22 no escriben ninguna ruta protegida**, y de esos solo **7**
   escriben algun archivo (a `tests/`, `scripts/`, `cos_lib/`). Los **12**
   restantes no escriben nada en absoluto: son sondas que corren un hook por
   `subprocess` y miden su salida. Se bloquean porque `subprocess` esta en
   `WRITE_PRIMITIVES`, no porque escriban.

3. **El conjunto protegido es otro que el del encargo.** Segun
   `manifests/protected-config-write-policy.yaml`: incluye `rules/**` y
   `skills/*/SKILL.md` (que el encargo omite) y **no** incluye `scripts/_lib/**`
   ni `manifests/*` en bloque (solo tres manifiestos nombrados). Cuatro de los 22
   bloqueos son por rutas que el encargo no sabia que estaban protegidas.

4. **"Analisis de flujo dentro del programa" esta sobredimensionado, y aun asi la
   conclusion del agente se sostiene.** Para 6 de los 22 alcanza una propiedad
   sintactica: *todo destino de escritura es un literal, y ninguno es protegido*.
   Para los otros 16 no alcanza nada: `subprocess` puede escribir cualquier cosa,
   y un destino armado con f-string no es resoluble. La exencion mas generosa que
   siga siendo fail-closed **despeja 6 de 22, no 10** — y el dolor ergonomico
   sobrevive al arreglo.

5. **La trampa del entorno heredado ya estaba resuelta antes de que yo llegara.**
   `scripts/audit_guard_mention_blocks.py` hace
   `env.pop("COS_ALLOW_PROTECTED_CONFIG_WRITE", None)` dentro de `replay()`. La
   orquestacion se comio esa trampa; el script no. No hubo nada que compensar.

6. **"Un mensaje que de el prefijo listo para copiar" ya existe.** El mensaje de
   bloqueo actual ya imprime las dos formas de aprobacion y la ruta del log de
   auditoria. Esa tercera opcion del encargo esta implementada desde antes.

7. **La aprobacion no siempre es un acto deliberado.** De 1622 aprobaciones
   registradas en 3 dias, **578 (36%) entraron por `source: env`** — la variable
   ya venia exportada en el entorno del harness. Nadie tipeo nada en esas. La
   premisa "filtra por paciencia" es optimista: un tercio no filtra ni eso.

## Los 10 casos, uno por uno

Son 22. Comando completo recuperable con
`.venv/bin/python3 scripts/audit_guard_mention_blocks.py --json`.

| # | ruta senalada | que hacia de verdad | veredicto |
|---|---|---|---|
| 1 | `hooks/zzz.sh`, `hooks/protected-config-write-guard.sh` | sonda: replaya 4 comandos sinteticos contra el guard | no escribe nada |
| 2 | `hooks/protected-config-write-guard.sh` | sonda: 19 formas de escritura + 6 de lectura | no escribe nada |
| 3 | `hooks/subagent-context-injector.sh` | corre el hook y mide el contexto entregado | no escribe nada |
| 4 | `rules/RULES-COMPACT.md` | escribe `tests/unit/test_efficiency_stress.py`; la ruta esta en el docstring y ademas se lee | falso positivo, exentable |
| 5 | `hooks/protected-config-write-guard.sh` | **ESCRIBE** el guard con `write_text`, destino literal | **bloqueo correcto** |
| 6 | `rules/codebase-memory-directive.md` | corre `scripts/cos-portability-proof-scaffold`; sale a `/tmp` | no escribe nada protegido |
| 7 | `hooks/session-watchdog-launcher.sh` | **ESCRIBE** el hook via `git apply /tmp/wl.patch` | **bloqueo correcto** |
| 8 | `hooks/session-watchdog-launcher.sh` | lanza un watchdog ajeno y corre el launcher | no escribe nada protegido |
| 9 | `hooks/destructive-git-blocker.sh` | sonda de 5 casos contra ese hook | no escribe nada |
| 10 | `skills/probe-skill/SKILL.md` | escribe `tests/hooks/test_scope_marker_gate_trigger.py`; la ruta vive dentro de literales del test | falso positivo, exentable |
| 11 | `hooks/.mutold-edit-lock-*.sh` | **BORRA** dos rutas protegidas con `rm -f` | **bloqueo correcto** |
| 12 | `hooks` | escribe `tests/red_team/portability/test_{hook}.py` (destino f-string) | falso positivo, NO exentable |
| 13 | `hooks` | lee `hook-timing.jsonl` y clasifica hooks por texto | no escribe nada |
| 14 | `hooks/_lib` | grep + sed sobre `_lib` | no escribe nada |
| 15 | `hooks` | escribe `scripts/hook_quality_audit.py`; los comentarios dicen "walking hooks/" | falso positivo, exentable |
| 16 | `hooks/cross-session-peer-context.sh`, `hooks/agent-message-inbox-context.sh` | escribe `tests/contracts/test_cross_session_event_taxonomy.py`; los hooks estan en un comentario | falso positivo, exentable |
| 17 | `hooks/concurrent-write-guard.sh` | contrafactual: corre la version de HEAD y la actual en tempdirs | no escribe nada protegido |
| 18 | `hooks/research-compliance-guard.sh` | extrae una funcion del hook y la prueba en tempfiles | no escribe nada protegido |
| 19 | `hooks/session-init.sh`, `hooks/session-cleanup.sh` | escribe `tests/audit/test_flock_has_a_portable_fallback.py`; los hooks estan en el docstring | falso positivo, exentable |
| 20 | `hooks/publication-safety.sh` | escribe `cos_lib/wiring_validator.py`; el hook esta en el docstring corregido | falso positivo, exentable |
| 21 | `skills/hook-timing/SKILL.md` | compara `grep -oP` vs `sed -nE`; la ruta esta en el prompt de prueba | no escribe nada |
| 22 | `hooks/protected-config-write-guard.sh` | grep sobre el propio guard | no escribe nada |

**Total: 3 bloqueos correctos (5, 7, 11) y 19 falsos positivos.** De los 19, 6
son exentables por una regla fail-closed; 13 no lo son con ninguna regla.

Patron: los tres correctos son escrituras *deliberadas y disclosadas* al plano de
control. Los 19 restantes son, casi todos, la misma actividad — **escribir sobre
un hook: un test que lo prueba, una sonda que lo mide, un docstring que lo
explica**. Es la actividad que el encargo describe como la mas deseable de la
sesion, y es exactamente la que el escaneo de menciones grava.

## Costo medido del falso positivo

Sobre los 34 bloqueos de Bash del guard en los transcripts, mirando los 40
tool-calls siguientes a cada uno:

```
23  rehecho con aprobacion
 9  no se rehizo (abandonado o resuelto de otro modo)
 2  rehecho reescrito, sin aprobacion
distancia hasta el reintento: min=1  mediana=1  max=21
```

**Mediana: 1 tool-call.** El 68% se resuelve reemitiendo el mismo comando con el
prefijo, en la llamada inmediatamente siguiente. No encontre ninguna tarea
abandonada por esto: los 9 "no se rehizo" son sondas cuya respuesta ya venia en
el propio mensaje de bloqueo, porque el mensaje nombra las rutas.

Costo total de los 19 falsos positivos: **~19 tool-calls en 3 dias.**

Pero el costo que importa no son los tool-calls, es **la precision del
registro**. `.cognitive-os/metrics/protected-config-bypass.jsonl` tiene 1622
entradas en 3 dias (142 / 809 / 671). Cada aprobacion de un falso positivo queda
asentada como una escritura autorizada a una ruta que el comando nunca toco. Si
manana alguien pregunta "quien escribio `hooks/publication-safety.sh`", el
registro contesta con un comando que escribio `cos_lib/wiring_validator.py`.
**19 de 22 registros mienten sobre el destino.** El registro es el unico producto
del guard, y esta al 14% de precision.

## Costo medido del falso negativo

`scripts/audit_guard_mention_blocks.py --false-negatives --since-days 3`:

```
comandos Bash no bloqueados, distintos, ultimos 3.0d: 1513
que el guard de HOY si bloquea (falsos negativos de entonces): 42
```

(El encargo decia 40 de 1499; recontado son **42 de 1513**.)

Clasificados los 42:

```
31  solo lectura / sonda -> falso POSITIVO del guard de hoy, no negativo de ayer
 6  llevaban COS_ALLOW_PROTECTED_CONFIG_WRITE -> aprobados y auditados
 5  ESCRIBIERON el plano de control sin aprobacion
```

Los 5 que escribieron, uno por uno — **todos `git apply` o `git mv`**, la unica
forma donde el destino no aparece en el texto del comando:

- `git apply $R/error-pipeline-type-contract-.../*.patch` — glob de parches de runbook
- `git apply "$P"` con `P=.../codebase-memory-directive-2026-08-15/conditional-directive.patch` -> escribe `rules/`
- `git mv codebase-memory-directive.md rules/` -> mueve un archivo hacia dentro del plano de control
- `git apply -R "$T/$p.patch"` — revert de dos parches
- `git apply /tmp/g.patch` -> parchea el propio guard

**Ninguno era malicioso ni accidental. Los cinco eran trabajo legitimo que el
autor habria aprobado igual.** Y los cinco estan cerrados hoy por
`patch_segment_targets`, que falla cerrado cuando no puede leer el parche.

Esa es la respuesta a la pregunta que el encargo marco como decisiva. Pero
contestarla no cierra el caso, porque hay una segunda mitad.

### El bypass que sigue abierto

La respuesta honesta al falso negativo no es "cero": **el guard tiene un bypass
abierto hoy, de una linea.** Verificado corriendo el guard contra siete
comandos (probe reproducible mas abajo; solo alimenta texto al hook):

```
concatenacion literal   Path('ho'+'oks/z.sh').write_text('x')      PASA
variable por partes     a='ho';b='oks'; Path(a+b+'/z.sh')          PASA
os.path.join            join('ho'+'oks','z.sh')                    PASA
chr()                   chr(104)+'ooks/z.sh'                       PASA
base64 decode           b64decode(...).decode()                    PASA
CONTROL literal         Path('hooks/z.sh').write_text('x')       BLOQUEA
CONTROL redireccion     echo x > hooks/z.sh                      BLOQUEA
```

El guard bloquea **solo** rutas deletreadas. El manifiesto declara su proposito
como *"Prevent prompt-injection or malicious-agent writes to agent control-plane
files"*. Contra ese modelo de amenaza el guard no sirve: un atacante no deletrea
la ruta. Contra un autor honesto si sirve, y ese es su valor real.

### La prueba de que la mencion no atrapa nada

Tome los 3 bloqueos correctos y les saque la prosa, dejando solo la escritura:

```
caso5  write_text destino literal protegido      BLOQUEA (por el destino)
caso7  git apply, parche inexistente al juzgar   BLOQUEA (unreadable patch source)
caso7b git apply solo, CERO menciones            BLOQUEA (unreadable patch source)
caso11 rm -f rutas protegidas literales          BLOQUEA (por el argumento)
```

**Los 3 se bloquean por mecanismos que no son el escaneo de menciones.** En tres
dias, el escaneo de menciones atrapo **cero** escrituras reales que los otros
mecanismos hubieran dejado pasar. Su rendimiento medido es 19 falsos positivos y
0 verdaderos.

Esto es lo mas cerca que llegue de "BLOQUEAR ESTA MAL", y no alcanza para
sostenerlo — por lo que sigue.

## La tercera opcion, si la hay

Hay tres, en este orden. Ninguna es un allowlist.

**C1 — Cerrar el bypass primero, lo que hace al guard MAS estricto.** Un destino
de escritura que no sea un literal resoluble debe bloquear, no pasar. Hoy pasa.
Es ademas *precondicion* de cualquier exencion: la regla "todos los destinos son
literales no protegidos" solo es solida si "destino no resoluble" bloquea, y hoy
eso es falso. Exentar antes de C1 es ensanchar la puerta con la cerradura rota.

**C2 — Partir el veredicto en dos grados, sin cambiar el comportamiento.** El
guard ya calcula por separado los destinos *demostrables* (redireccion, destino
de copia, target de parche, argumento literal de un segmento) y los que salen del
escaneo de presencia sobre el cuerpo del heredoc. Agregar un campo
`grade: demostrable|mencion` al mensaje y al log de bypass es **una lista mas,
cero analisis de flujo** — justo lo que el agente anterior dijo que hacia falta
para *decidir*, y que no hace falta para *etiquetar*. Los dos grados siguen
bloqueando y exigiendo el prefijo, asi que no se abre nada. Lo que se gana: el
registro deja de afirmar escrituras que no ocurrieron, y recien entonces se puede
preguntar con evidencia *"cuantas aprobaciones de grado `mencion` resultaron ser
escrituras reales"*. Hoy nadie puede preguntarlo porque el log confunde los dos.

**C3 — Corregir el manifiesto.** `manifests/protected-config-write-policy.yaml`
dice que el proposito es prevenir escrituras de inyeccion o de agente malicioso.
Medido, no lo hace. Mientras diga eso, alguien va a confiar en el guard para algo
que el guard no cubre. El proposito honesto es *disclosure y auditoria de
escrituras al plano de control por autores honestos*. Eso ya es valioso; lo que
no es valioso es decir que es otra cosa.

La aprobacion **por sesion** en vez de por comando, que sugeria el encargo: **no**.
El 36% de las aprobaciones ya entra por `env` heredado, que es exactamente una
aprobacion por sesion — y es la mitad del problema de precision del registro, no
su solucion.

## Que deberia hacer el agente que esta implementando

**Parar.** El argumento con el que se lo frena, en tres numeros:

1. **La exencion despeja 6 de 22, no 10.** Los otros 16 le pasan `subprocess` a
   un interprete o arman el destino con un f-string; ninguna regla fail-closed
   los despeja. La queja ergonomica que motivo el encargo **sobrevive intacta**:
   se paga construir un mini-analizador de literales de Python dentro de un hook
   de bash, y el dolor baja de 22 a 16.

2. **Lo que compra son ~6 tool-calls cada 3 dias.** Mediana medida del falso
   positivo: 1 tool-call. Es construir y mantener un parser a cambio de seis
   llamadas — y ese parser, `_open_can_write` + `_balanced_args`, ya existe en el
   hook y ya es la parte que mas se toco esta semana.

3. **Hay un agujero de una linea abierto en el mismo hook.** Cinco formas de
   ofuscar el destino pasan hoy. Bajar la pared antes de arreglar la cerradura es
   trabajo en la direccion contraria, y es exactamente el sesgo del que advertia
   el encargo: el falso positivo se sufre leyendo transcripts, el falso negativo
   no se ve — y aca el que no se ve esta abierto.

Si el operador quiere igual la ergonomia, el orden es **C1, despues C2, y recien
con una semana de datos de grado `mencion` decidir la exencion**. No al reves.

## Prueba ejecutable

```bash
# 1. los 22 bloqueos vigentes, clasificados
env -u COS_ALLOW_PROTECTED_CONFIG_WRITE \
  .venv/bin/python3 scripts/audit_guard_mention_blocks.py

# 2. los 42 falsos negativos de los ultimos 3 dias
env -u COS_ALLOW_PROTECTED_CONFIG_WRITE \
  .venv/bin/python3 scripts/audit_guard_mention_blocks.py --false-negatives --since-days 3

# 3. C1: el bypass de destino ofuscado. rc=0 es "paso".
#    Read-only: solo alimenta texto al hook, no ejecuta ninguna escritura.
COS_ALLOW_PROTECTED_CONFIG_WRITE=1 .venv/bin/python3 - <<'PY'
import json, os, subprocess
H = "ho" + "oks"
G = H + "/protected-config-write-guard.sh"
def rc(cmd):
    env = dict(os.environ); env.pop("COS_ALLOW_PROTECTED_CONFIG_WRITE", None)
    env["CLAUDE_PROJECT_DIR"] = os.getcwd()
    return subprocess.run(["/bin/bash", G],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}}),
        text=True, capture_output=True, env=env, cwd=os.getcwd()).returncode
casos = [
  ("concatenacion", "python3 - <<'E'\nimport pathlib\npathlib.Path('ho'+'oks/z.sh').write_text('x')\nE"),
  ("chr()        ", "python3 - <<'E'\nimport pathlib\npathlib.Path(chr(104)+'ooks/z.sh').write_text('x')\nE"),
  ("CONTROL lit. ", "python3 - <<'E'\nimport pathlib\npathlib.Path('" + H + "/z.sh').write_text('x')\nE"),
]
for etiqueta, c in casos:
    print(f"  {etiqueta}  rc={rc(c)}")
PY

# 4. precision del registro de aprobaciones
.venv/bin/python3 -c "
import json, collections
c = collections.Counter(); s = collections.Counter()
for l in open('.cognitive-os/metrics/protected-config-bypass.jsonl'):
    try: d = json.loads(l)
    except: continue
    c[d.get('timestamp','')[:10]] += 1; s[d.get('source','?')] += 1
print(dict(c)); print(dict(s))
"
```

## Lo que no pude medir

1. **Si alguna escritura ofuscada realmente ocurrio.** Probe que el bypass esta
   abierto; no probe que se haya usado. Buscar `write_text` con destino no
   literal en los transcripts daria un piso, no una respuesta: por construccion,
   una escritura ofuscada no se distingue de una legitima con el destino armado.
   Es el limite duro del metodo, no una tarea pendiente.

2. **La tasa base fuera de este repo.** Aca los agentes escriben *sobre* hooks
   todo el dia, asi que la densidad de menciones es atipicamente alta. En un
   proyecto consumidor los 19 falsos positivos probablemente sean 1 o 2, y la
   exencion valga todavia menos de lo que vale aca.

3. **Los 9 bloqueos "no se rehizo".** Los clasifique como resueltos por el propio
   mensaje de bloqueo leyendo los comandos, no midiendo. Si alguno fue un
   abandono real, el costo del falso positivo es mayor que 1 tool-call de
   mediana. No encontre evidencia de abandono, pero tampoco la busque
   exhaustivamente.

4. **Si `rules/**` y `skills/*/SKILL.md` deberian estar en el conjunto
   protegido.** Estan, generan 4 de los 22 bloqueos, y no juzgue esa decision: es
   del operador y es anterior a este encargo.

5. **El costo de `block-destructive-bash.sh`, el otro guard.** Aparece con 19
   bloqueos en el mismo corpus y me bloqueo a mi al intentar escribir este
   informe (el texto menciona `/tmp` y `rm -f`). No lo medi; queda como el
   siguiente candidato obvio al mismo analisis.

## Correccion posterior: que significa el cero de verdaderos positivos

Agregada el 2026-08-20 por la orquestacion, despues de que otra sesion de Claude
—trabajando en otro repo, sobre la misma clase de defecto— senialara un hueco en
el metodo de este informe. La correccion NO cambia el veredicto; cambia lo que
se puede citar de el.

El informe midio "19 falsos positivos y 0 verdaderos en tres dias" y esa cifra
se uso para frenar a un agente que estaba construyendo una exencion. **El
resultado sigue siendo correcto**, pero por el argumento independiente que este
mismo informe da —el guard solo bloquea rutas DELETREADAS, asi que discutir la
exencion de menciones es regatear el precio de la puerta con la cerradura
abierta— y **no por el 19/0**.

Porque un "N falsos positivos y 0 verdaderos" tiene dos lecturas y el numero
solo no las distingue:

  1. el detector es ruido puro, o
  2. el evento verdadero es mas raro que la ventana medida.

Y el contraejemplo que lo prueba esta en este mismo repo, medido el mismo dia:
`hooks/secret-detector.sh` registro **0 bloqueos en 143.605 tool-calls**, y por
ahi pasaron **seis claves privadas reales sin redactar**. Ese cero no medi que
el evento fuera raro: medi que el detector no estaba mirando. Quien lo leyera
sin conocer la causa concluiria "no atrapa nada, sacalo" — y sacaria al unico
que quedaba.

**Lo que distingue las dos lecturas, y es barato:** sembrar positivos sinteticos
EN EL MISMO CORPUS que se mide, uno por sub-forma cubierta, y confirmar que el
detector los agarra a todos en la misma corrida. Si agarra los sembrados y no
encuentra reales, el cero es tasa base. Si se le escapa alguno, el cero no
significaba nada.

Y la distincion fina, que es la que se olvida: el control positivo en un
**fixture** prueba que el detector detecta; el positivo **sembrado en el corpus**
prueba que el barrido llega hasta donde esta. No son lo mismo. En esta sesion
fallaron las tres razones por las que difieren: un `find` que no llegaba, un
filtro de extension que excluia, y un glob de un solo nivel.

Forma canonica, de la sesion que lo senialo: **un TP/FP sin control positivo
sembrado en el mismo corpus es un `rc=0` con mas decimales.**

Se corrige aca, y no solo en la memoria de la sesion, por el motivo que ellos
dieron: si la justificacion no se corrige donde vive, el proximo que lea el
registro hereda el numero y no el argumento.

# El contrato de hooks de Claude Code, revisado contra la fuente

Fecha: 2026-08-19 · Archivo tocado: `manifests/claude-code-hooks-schema.yaml`

## Resumen ejecutivo

- **No hay ningún hook muerto.** Cero de los 162 handlers de `.claude/settings.json`
  y cero de las 200 entradas de `cognitive-os.yaml > harness.hooks` declaran `if`,
  `args`, `shell`, `asyncRewake`, `statusMessage` u `once`. Las únicas claves en uso
  son `type`/`command`/`async` y `script`/`event`/`scope`/`async`/`matcher`/`*_projection`.
  El hallazgo urgente que el encargo anticipaba no existe.
- Los seis campos **existen** en la doc oficial. Ninguno es inventado.
- El defecto real es otro y es del manifest consigo mismo: su regla de alcance dice
  "sólo los eventos que este repo registra se transcriben completos", y era **falsa**.
  El repo registra diez eventos; el manifest transcribía seis. Faltaban **PreCompact,
  TaskCreated y TeammateIdle**, los tres con hooks vivos encima y sin cobertura del
  test de conformidad.
- Refuté la premisa de que los eventos nuevos son "no decision control": los tres
  bloquean. Y refuté la lectura de que la doc recomienda `permissions` por sobre
  hooks en general — lo dice sólo del filtro `if`.
- La actualización queda cubierta por `tests/contracts/test_external_claims_declare_verification.py`
  sin escribir un test nuevo. Probado en las dos direcciones.

## Correcciones a las premisas del encargo

1. **"eventos que ganaron decision control y no figuran: PreCompact · ConfigChange ·
   TaskCreated"** — mitad y mitad. Que no figuraban es cierto para los tres. Que sean
   los tres relevantes, no: el que faltaba y el encargo no nombró es **TeammateIdle**,
   que sí tenemos registrado con un hook encima. Y **ConfigChange no lo registramos**,
   así que por la regla de alcance del propio manifest no correspondía transcribirlo.
   La lista correcta de faltantes-con-hook-vivo es PreCompact, TaskCreated, TeammateIdle.

2. **"los eventos nuevos son todos 'no decision control'"** — refutado, y contradice
   además la frase anterior del propio encargo ("eventos que ganaron decision control").
   Los tres bloquean: `PreCompact` exit 2 bloquea la compactación, `ConfigChange` exit 2
   bloquea el cambio de configuración (salvo `policy_settings`), `TaskCreated` exit 2
   revierte la creación de la tarea. El grupo real sin decision control es otro:
   WorktreeRemove, Notification, SessionEnd, PostCompact, InstructionsLoaded,
   StopFailure, CwdChanged, DirectoryAdded, FileChanged.

   ```
   sed -n '978,1000p' hooks.md
   | ... ConfigChange, PreCompact | Top-level `decision` | `decision: "block"`, `reason` |
   | TaskCreated | Exit code o top-level `decision` | ... `continue: false` es ignorado |
   | WorktreeRemove, Notification, SessionEnd, PostCompact, ... | None | No decision control |
   ```

3. **"la doc recomienda `permissions` por sobre hooks para enforcement duro"** — el
   alcance está inflado. La frase aparece **una sola vez** en 3487 líneas, dentro de la
   descripción del campo `if`, y su sujeto es el filtro `if`, no los hooks:

   > "Because the `if` filter is best-effort, use the permission system rather than a
   > hook to enforce a hard allow or deny." — hooks.md línea 440

   Comando: `grep -n 'rather than a hook' hooks.md` → 1 resultado. El bloqueo por
   `PreToolUse` + `permissionDecision: deny` sigue documentado sin ninguna advertencia
   equivalente. La conclusión "la plataforma está moviendo la capacidad de denegar a
   otro lado" no se sostiene con esta evidencia.

4. **"¿los agregamos aunque no proyectemos hooks ahí?"** — la premisa de la pregunta es
   falsa para dos de los tres: **sí proyectamos** hooks en PreCompact y TaskCreated.
   La decisión del Paso 3 no se resuelve con el argumento a favor/en contra que me
   pasaste, se resuelve con el hecho. Ver la sección correspondiente.

5. **La doc cambió desde la última verificación.** El manifest registra 272682 bytes al
   2026-08-15; hoy son **277223**. No es una premisa que me hayas dado, pero contradice
   la suposición implícita de que sólo faltaba transcribir mejor lo mismo.

6. **`grep '"once"'` da 0 y el campo existe.** Si hubiera confiado en la forma
   entrecomillada habría reportado `once` como inventado. Con `grep -n 'once'` aparece
   en la tabla "Common fields". Un falso refutado por comillas es el mismo error de
   signo que el encargo advertía, en la dirección contraria.

## Qué confirmé y qué refuté de los campos

Fuente: `curl -sSL https://code.claude.com/docs/en/hooks.md` → HTTP 200, 277223 bytes,
sin redirect (el `.md` en `code.claude.com` devuelve la fuente completa, como el
manifest ya advertía). Grepeado localmente.

| Campo | ¿Existe? | Dónde | Lo que importa |
|---|---|---|---|
| `if` | **Confirmado** | Common fields, todos los tipos | Sólo se evalúa en eventos de tool. En cualquier otro, **el handler nunca corre**, sin error ni warning |
| `args` | **Confirmado** | Command hook fields | Su presencia cambia el handler a *exec form*: sin shell, sin pipes, sin `&&` |
| `shell` | **Confirmado** | Command hook fields | `bash` o `powershell`. **Ignorado cuando `args` está seteado** |
| `asyncRewake` | **Confirmado** | Command hook fields | Implica `async`. Exit 2 despierta a Claude aun con la sesión ociosa — la excepción documentada al "se entrega en el próximo turno" |
| `statusMessage` | **Confirmado** | Common fields, todos los tipos | Cosmético: spinner para el usuario, no llega al modelo |
| `once` | **Confirmado** | Common fields | **Sólo se honra en frontmatter de skill.** En settings y en frontmatter de agente se ignora, en silencio |

Ninguno refutado. Lo que sí refuté son las lecturas de segundo orden (ver correcciones
2 y 3), que era donde estaba el signo cambiado.

Detalles que no estaban en el relay y cambian cómo se usarían:

- `if` acepta **exactamente una** regla de permiso. No hay `&&`, `||` ni forma de lista.
- `if` **falla abierto**: si el comando Bash no se puede parsear, el hook corre igual.
  Y un patrón que nombra más que el comando (`Bash(git push *)`) dispara el hook ante
  cualquier `$()`, backtick o `$VAR`.
- Desde v2.1.214, `"Edit(src/**)"` matchea sólo `src` en el cwd; antes matcheaba a
  cualquier profundidad.
- `TaskCreated` **no soporta matcher** y dispara siempre.
- `TaskCreated` **ignora `continue: false`**; `PreCompact` y `ConfigChange` descartan
  `systemMessage` y `continue`.
- `TeammateIdle` **no toma `decision: "block"`** — toma exit 2 o `continue: false`.
  Escribir `decision: "block"` ahí es inerte.

## Hooks afectados

Ninguno. La medición, en las tres superficies donde un handler puede declararse:

```
# 1. .claude/settings.json — 162 handlers
COS_ALLOW_PROTECTED_CONFIG_WRITE=1 python3 -c "
import json,collections;d=json.load(open('.claude/settings.json'));c=collections.Counter()
[c.update(h) for ev,gs in d['hooks'].items() for g in gs for h in g.get('hooks',[])]
print(dict(c))"
-> {'type': 162, 'command': 162, 'async': 43}

# 2. cognitive-os.yaml > harness.hooks — 200 entradas
.venv/bin/python3 -c "
import yaml,collections;hh=yaml.safe_load(open('cognitive-os.yaml'))['harness']['hooks']
c=collections.Counter();[c.update(v) for v in hh.values() if isinstance(v,dict)];print(len(hh),dict(c))"
-> 200 {'script':200,'event':200,'scope':200,'async':42,'claude_projection':4,
        'matcher':132,'codex_projection':4,'codex_gap_reason':4,
        'default_projection':6,'projection_note':3,'profiles':3}

# 3. frontmatter de skills y agentes (la doc dice que `once` sólo se honra ahí)
grep -rln '^hooks:' --include='SKILL.md' --include='*.md' .claude/skills .claude/agents skills agents
-> sin resultados
```

Un solo `args:` aparece en `cognitive-os.yaml` (línea 2208) y es un falso positivo:
pertenece a `scheduled_tasks.self_improvement_proposer.args`, nada que ver con hooks.

`.claude/settings.local.json` no tiene bloque `hooks` (sólo `permissions`). Los tres
`hooks.json` del repo (`.codex/`, `.devin/`, `.cursor/`) son de otros arneses.

**El driver tampoco puede introducirlos**: `scripts/_lib/settings-driver-claude-code.sh`
emite un `printf` fijo con `type`/`command` y, en el caso async, `"async": true`
(líneas 126 y 133). No hay camino por el que un `if` entre a la proyección hoy.

### Lo que sí encontré: tres eventos registrados y sin contrato

```
COS_ALLOW_PROTECTED_CONFIG_WRITE=1 python3 -c "
import json;d=json.load(open('.claude/settings.json'))
[print(k,sum(len(g.get('hooks',[])) for g in v)) for k,v in sorted(d['hooks'].items())]"
```

| Evento | Handlers | Hook | ¿Estaba en el manifest? |
|---|---|---|---|
| PostToolUse | 57 | varios | sí |
| PreToolUse | 39 | varios | sí |
| SessionStart | 27 | varios | sí |
| Stop | 23 | varios | sí |
| UserPromptSubmit | 12 | varios | sí |
| SubagentStart | 1 | `hooks/subagent-context-injector.sh` | sí |
| **PreCompact** | 1 | `hooks/pre-compaction-flush.sh` | **no** |
| **TaskCreated** | 1 | `hooks/task-created.sh` | **no** |
| **TeammateIdle** | 1 | `hooks/teammate-idle.sh` | **no** |
| TaskCompleted | 0 | `hooks/task-completed.sh` (`default_projection: false`) | no |

Los cuatro hooks bloquean con `exit 2`, que es la forma correcta para sus cuatro
eventos según la tabla "Exit code 2 behavior per event" — `pre-compaction-flush.sh` no
bloquea en absoluto, es sólo efecto de lado. Así que no hay shape roto tampoco. Pero
el test de conformidad no podía saberlo: validaba contra un manifest que no describía
esos eventos.

### Telemetría: cuánto disparan realmente

Contando el archivo vivo **más los siete rotados**, como pide el encargo:

```
{ cat .cognitive-os/metrics/hook-timing.jsonl;
  gzcat .cognitive-os/metrics/.archive/hook-timing-*.jsonl.gz; } \
| .venv/bin/python3 -c "import sys,json,collections;c=collections.Counter(
    json.loads(l).get('event','?') for l in sys.stdin);print(c.most_common())"
```

262045 filas, 0 ilegibles, del 2026-07-19 al 2026-08-19:

| Evento | Filas |
|---|---|
| PostToolUse | 157632 |
| PreToolUse | 90808 |
| Stop | 7186 |
| UserPromptSubmit | 4074 |
| SessionStart | 2017 |
| SubagentStart | 323 |
| **PreCompact** | **5** (la última hoy 19:43) |
| **TaskCreated** | **0** |
| **TeammateIdle** | **0** |

El archivo vivo solo tiene 48024 filas; las cinco de PreCompact abarcan desde el
2026-07-19, o sea que contando únicamente el vivo el resultado habría sido "casi nunca"
en vez de "raro pero real y todavía activo". TaskCreated y TeammateIdle en 0 sobre el
corpus completo: registrados, nunca disparados. No son hooks muertos — son hooks cuyo
evento no ocurre en este flujo de trabajo.

## La actualización del manifest

Cuatro bloques, todos con `url` / `what` / `verified:` / `how:` donde corresponde.

1. **Nueva fuente fechada** con el comando exacto: `curl -sSL`, el conteo de bytes vía
   `-w '%{size_download}'`, y los tres `sed -n` de rango que produjeron cada sección
   transcripta. Deja anotado el cambio de tamaño (272682 → 277223) y la trampa del
   `grep '"once"'`.

2. **`handler_fields`**: los seis campos. `if` con su propia advertencia destacada —
   es la misma familia de fallo silencioso que la regla estrella del archivo
   (`additionalContext` a nivel raíz), un nivel más arriba: ahí se descarta la
   **salida**, acá el **handler entero**. La cita de `permissions` va con su alcance
   escrito al lado, para que nadie la vuelva a leer de más.

3. **`events`**: se agregan PreCompact, TaskCreated, TeammateIdle y TaskCompleted. El
   comentario de cabecera, que afirmaba una regla de alcance que el propio archivo
   violaba, ahora dice qué pasó, con el comando que lo mide y la lista de los 21
   eventos que **no** registramos, para que el próximo lector no tenga que re-derivarla.

4. **`prohibited_in_this_repo`**: dos entradas nuevas, `if-field-on-non-tool-event` y
   `once-field-in-settings`. La primera anota explícitamente que hoy hay **cero** casos
   y que por eso es preventiva, no remedial — un supresor que no suprime nada es un bug,
   y decir cuál es el estado real evita que dentro de seis meses parezca que atrapó algo.

## Los tres eventos nuevos: incluir o no, y por qué

**El dilema que me pasaste no aplica tal como está planteado**, porque su premisa
("aunque no proyectemos hooks ahí") es falsa para dos de los tres. Verificado arriba:
PreCompact y TaskCreated tienen un handler cada uno en `.claude/settings.json`.

La decisión la toma la regla que el manifest ya tiene escrita: *sólo los eventos que
este repo registra se transcriben completos*. Esa regla es buena — es exactamente el
argumento en contra que me diste ("documentar lo que no usamos es superficie que
envejece sin darnos nada"), ya adoptado desde el 2026-08-15. El problema no era que
faltara una decisión: era que **la regla no se estaba cumpliendo**.

Entonces:

- **PreCompact, TaskCreated, TeammateIdle → entran**, transcriptos completos. No por
  un criterio nuevo, sino porque la regla vigente siempre los incluyó y el archivo no
  la respetaba. Documentarlos no agrega superficie especulativa: agrega el contrato de
  hooks que ya están corriendo y que el test no podía validar.
- **TaskCompleted → entra, en versión corta y marcado.** Está declarado en
  `cognitive-os.yaml` con `default_projection: false`, así que hoy no corre. Lo incluyo
  con `projected_to_settings: false` bien visible porque prender la proyección es
  cambiar una línea, y no quiero que ese cambio de una línea obligue a volver a leer la
  doc del host. Es el único caso donde acepté superficie que hoy no se usa, y el motivo
  está escrito en el archivo.
- **ConfigChange → no entra** a la transcripción. No lo registramos. Sí queda en la
  lista de "no transcriptos y por qué", nombrado aparte: es el que tiene poder de
  bloqueo real que dejamos sin usar a propósito — puede impedir que un cambio de
  settings tome efecto, y un repo que ya custodia `.claude/settings.json` con un guard
  de `PreToolUse` tiene un motivo evidente para quererlo. Dejarlo apagado es una
  decisión; escribirla cuesta tres líneas y ahorra que alguien la redescubra.

## Que el test lo agarre la próxima vez

**No escribí ningún test.** `tests/contracts/test_external_claims_declare_verification.py`
ya cubre exactamente esto y duplicarlo era el defecto que este repo persiguió todo el
día. Lo verifiqué en las dos direcciones, no sólo mirando que pasara.

**Dirección verde — la actualización real:**

```
$ .venv/bin/python3 -m pytest tests/contracts/test_external_claims_declare_verification.py \
    tests/contracts/test_claude_code_hooks_schema_conformance.py -q
...............                                                          [100%]
15 passed in 3.21s
```

**Dirección roja A — le saco el `how:` a mi fuente nueva, dejándole la fecha:**

```
$ .venv/bin/python3 -m pytest tests/contracts/test_external_claims_declare_verification.py -q
...F.
E   AssertionError: {'manifests/claude-code-hooks-schema.yaml': (2, 1)} declara
    `verified:` pero no COMO se verifico (archivo: real vs baseline). Una fecha sin su
    comando no es reproducible: el que la revise dentro de seis meses no sabe que correr.
FAILED ...::test_toda_afirmacion_fechada_declara_su_metodo
1 failed, 4 passed in 3.03s
```

**Dirección roja B — le saco `verified:` y `how:` a la vez:**

```
$ .venv/bin/python3 -m pytest tests/contracts/test_external_claims_declare_verification.py -q
F....
E   AssertionError: estas afirmaciones sobre sistemas AJENOS no declaran cuando se
    verificaron (archivo: sin_fecha_ahora vs baseline):
    {'manifests/claude-code-hooks-schema.yaml': (2, 1)}.
FAILED ...::test_ninguna_afirmacion_externa_nueva_omite_su_fecha
1 failed, 4 passed in 3.48s
```

Ambas mutaciones se revirtieron; el archivo quedó byte-idéntico
(`diff -q` sin salida) y la corrida final vuelve a dar 15 passed.

El baseline **no se movió**: entro con una fuente nueva que trae fecha *y* método, así
que los contadores del archivo siguen en 1 sin-fecha / 1 fechada-sin-método. Bajar esos
dos a cero es el arreglo pendiente, y es de otro dueño: la fuente sin fecha es la nota
de mirrors y la fechada-sin-método es la de `agent-sdk/hooks`, ninguna de las cuales
re-verifiqué hoy. Ponerles la fecha de hoy sin haberlas mirado es precisamente el verde
barato que el encargo prohibía.

Lo que este test **no** cubre, dicho para que no se confunda: que lo transcripto sea
verdadero. Eso exige salir a la red y el contrato es determinista a propósito. Es un
contrato de declaración, no de exactitud — el propio docstring del archivo lo dice.

## Lo que NO hice y por qué

- **No registré ConfigChange** ni ningún hook nuevo. El encargo era documentar y medir;
  registrar un hook con poder de bloqueo sobre cambios de configuración es una decisión
  del operador, no una consecuencia de haber leído la doc.
- **No bajé el baseline** de `KNOWN_UNDATED_EXTERNAL_CLAIMS` / `KNOWN_DATED_WITHOUT_METHOD`.
  Requeriría re-verificar dos fuentes ajenas que no verifiqué, y el archivo del test es
  de esta misma sesión y de otro dueño.
- **No transcribí los 21 eventos restantes.** La regla de alcance del manifest lo
  prohíbe y estoy de acuerdo con ella; los dejé listados por nombre, que cuesta seis
  líneas y evita que el próximo lector tenga que volver a la doc para saber que ya se
  miró.
- **No escribí un test nuevo.** Ver la sección anterior.
- **No commiteé ni pusheé.** Cambios en el working tree.

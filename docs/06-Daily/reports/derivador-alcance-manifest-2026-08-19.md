<!-- SCOPE: os-only -->
# Derivador de alcance del manifest de hooks de Claude Code

Fecha: 2026-08-19 · Archivo tocado: `tests/contracts/test_claude_code_hooks_schema_conformance.py`

## Resumen ejecutivo

El manifest `manifests/claude-code-hooks-schema.yaml` tenía escrita una regla de
alcance —se transcriben los eventos que este repo registra, y sólo esos— y nada
la hacía cumplir. Registrábamos diez y transcribía seis. Se corrigió a mano hoy;
ahora está derivada. Cinco aserciones nuevas dentro del test de conformidad que
ya existía (no un archivo nuevo): el conjunto de eventos transcritos tiene que
ser **igual** al conjunto de eventos declarados en `cognitive-os.yaml >
harness.hooks`, y de yapa el flag de proyección, el nombre del hook que sostiene
cada evento y la validez del `matcher` se computan de la misma fuente. La suite
pasa de 10 a 15 tests. Transcribir de más queda **prohibido**, sin lista de
excepciones. El defecto se reintrodujo cuatro veces y el gate falló nombrando el
evento en las cuatro; el árbol quedó restaurado byte-idéntico (sha256 verificado).

## Correcciones a las premisas del encargo

1. **"Registramos 10 eventos" mezcla declarado con registrado, y la diferencia
   decide el diseño.** Nueve eventos llegan a `.claude/settings.json` con al
   menos un handler; el décimo, `TaskCompleted`, tiene su único hook con
   `default_projection: false` y llega con **cero** handlers. La cuenta del
   propio manifest lo dice (`TaskCompleted 0`). Esto no es una objeción de
   vocabulario: si el derivador tomara "registrado" como "tiene handler en
   settings", `TaskCompleted` sería un evento *transcripto de más* y el gate
   pediría borrar una transcripción legítima. Por eso la fuente es la
   **declaración** en `cognitive-os.yaml`, y la proyección se verifica aparte
   (`test_manifest_projection_flags_match_the_config`).

2. **"Los tres con hook vivo" — el criterio de "vivo" no es el que importa, y
   además no lo pude reproducir.** En `.cognitive-os/metrics/hook-timing.jsonl`
   (4448 filas) `pre-compaction-flush`, `task-created` y `teammate-idle` tienen
   **0 filas** cada uno; no encontré ahí los "5 disparos reales" de `PreCompact`
   (el string sí aparece en `aci-observations.jsonl` y
   `primitive-interventions.jsonl`, que son otra cosa; no lo perseguí). Da igual
   para el derivador, y ése es el punto: un hook con cero disparos necesita
   contrato transcrito exactamente igual que uno con mil, porque lo que el test
   de conformidad chequea es la **forma de lo que emite**, no su frecuencia.
   Atar el alcance a la telemetría habría sido derivar del uso en vez de la
   declaración.

3. **"El conteo del manifest" sólo sobrevive al cambio de fuente a nivel de
   conjunto de eventos, no de cantidad de hooks.** El bloque de comentario del
   manifest mide contra `settings.json`: PreToolUse 39, UserPromptSubmit 12,
   PostToolUse 57. Contra `cognitive-os.yaml` da 72, 13 y 60. El *conjunto de
   eventos* coincide exacto en las dos fuentes (por eso el derivador es sólido),
   la *cantidad de hooks por evento* no coincide en tres de diez. Ese delta es
   el derivador #3 y lo dejé especificado abajo con la medición ya hecha.

4. **"Mirá primero el test de conformidad ... puede que tu gate sea una aserción
   más ahí" — confirmado, y fue la decisión.** No hay archivo nuevo. Las cinco
   aserciones entran en `tests/contracts/test_claude_code_hooks_schema_conformance.py`,
   reusan el fixture `schema` que ya existía y agregan uno solo
   (`declared_hooks`). Un archivo aparte habría duplicado el parseo del manifest
   y habría dejado dos lugares donde buscar por qué el contrato está roto.

5. **El guard de `manifests/*` dispara aun leyendo, y lo verifiqué sin querer.**
   Un `python3 -c` puramente de lectura que menciona `.claude/settings.json` en
   el texto del comando fue bloqueado por `protected-config-write-guard.sh`. La
   premisa del encargo ("dispara por el contenido del comando, no sólo por el
   destino") queda confirmada con evidencia, no asumida.

6. **La regla de alcance no estaba escrita como frase; estaba escrita como dos
   listas.** El encargo la cita entrecomillada ("sólo los eventos que este repo
   registra se transcriben completos"). Esa oración textual no existe en el
   archivo. Lo que existe es el par de listas complementarias —los eventos
   "registrados aquí ... transcritos abajo" y el bloque "Events NOT transcribed
   in full, and why -- this repo registers no handler on any of them"—, que
   juntas dicen *registrado si y sólo si transcripto*. Lo aclaro porque el
   comentario del test cita la fuente, y citar una paráfrasis como si fuera
   textual es la misma clase de defecto que este trabajo persigue.

## Las dos clases de hecho, aplicadas a este manifest

| Clase | Qué es | Cómo se sostiene | En este manifest |
|---|---|---|---|
| **EXTERNO — no derivable** | Qué acepta Claude Code en cada evento: campos honrados, semántica del exit 2, dónde se inserta el contexto, qué se descarta en silencio | Se transcribe, se cita la URL y se fecha. El vencimiento lo audita `scripts/external_claim_freshness_audit.py`. No hay forma de computarlo: el host no publica un esquema consultable | Todo el cuerpo de cada evento: `can_block`, `exit_2_behavior`, `output_fields_allowed`, `decision_pattern`, las citas |
| **INTERNO — derivable** | Qué eventos registra *este* repo, con qué hook, con qué matcher, proyectado o no | Se computa de `cognitive-os.yaml > harness.hooks`. Escribirlo a mano es garantía de deriva | Las **claves** del mapa `events`, `registered_hook`, `declared_hook`, `projected_to_settings` |

El derivador vive en el cruce: el **alcance** de una transcripción externa es un
hecho interno. Mientras el alcance se tipeaba, transcribir seis de diez era un
descuido que alguien tenía que notar; derivado, es estructuralmente imposible.

Corolario que ordena el resto del archivo: una fila EXTERNA envejece y se
re-verifica con fecha; una fila INTERNA no envejece, **deriva**, y contra la
deriva la fecha no sirve para nada. Son dos remedios distintos y ponerlos en la
misma columna es lo que dejó este agujero abierto.

## El derivador: qué computa y de dónde

Fuente: `cognitive-os.yaml > harness.hooks` (200 entradas, cada una con `event`).
**No** `.claude/settings.json`, que es generado desde ella (ADR-064): derivar del
artefacto dejaría que un bug del driver se dé la razón a sí mismo.

Cinco aserciones nuevas, todas en `tests/contracts/test_claude_code_hooks_schema_conformance.py`:

| Test | Computa | Exige |
|---|---|---|
| `test_transcribed_events_equal_registered_events` | `{spec.event}` sobre las 200 entradas → 10 eventos | **Igualdad** con `set(manifest.events)`. Falta = hook sin contrato; sobra = contrato sin consumidor |
| `test_manifest_projection_flags_match_the_config` | `any(default_projection)` por evento | Coincide con `projected_to_settings` donde el manifest lo afirma (hoy: sólo `TaskCompleted: false`) |
| `test_manifest_named_hooks_exist_in_the_config` | `{spec.script}` por evento | `registered_hook` / `declared_hook` nombran un script realmente declarado en ese evento |
| `test_matcher_only_where_the_event_honors_it` | hooks con `matcher` | El evento honra matchers: `matcher_supported` del manifest si está transcrito, si no la regla que el propio `cognitive-os.yaml` documenta en su cabecera (PreToolUse/PostToolUse) |
| `test_matcher_values_stay_inside_the_transcribed_set` | ídem | Donde el host enumera valores legales (`PreCompact: [manual, auto]`), el matcher está entre ellos |

Fixture nuevo: `declared_hooks`, mapa `evento -> [entradas de harness.hooks]`.
Constante nueva: `COS_CONFIG`. Todo lo demás se reusa.

## Transcribir de más: prohibido o permitido con motivo

**Prohibido, sin lista de excepciones.** Tres razones, en orden de peso:

1. **Hoy no hace falta ninguna excepción, y una lista de excepciones vacía es
   colchón.** El único candidato imaginable, `TaskCompleted`, está *declarado* en
   `cognitive-os.yaml`, así que ya cae adentro del conjunto derivado. Ofrecer un
   allowlist "por las dudas" es exactamente lo que `gates-sin-trampa` llama un
   supresor que no suprime nada: no protege nada hoy y mañana absorbe una
   regresión real sin que nadie lo note.
2. **Ya existe el lugar correcto para un evento que no registramos, y es mejor.**
   La cabecera del manifest lista veintidós eventos deliberadamente no
   transcritos, con `ConfigChange` nombrado primero y con su motivo escrito
   ("tiene poder de bloqueo real que dejamos sin usar a propósito"). Una línea en
   prosa envejece con honestidad: se lee como lo que es, una decisión fechada.
   Una entrada en el mapa `events` **finge estar chequeada** — parece contrato
   vigente y nadie la verifica.
3. **Superficie externa sin consumidor tiene costo recurrente.** Cada evento
   transcripto hay que re-verificarlo contra un upstream que se mueve (el doc
   creció 4541 bytes entre el 15 y el 19 de agosto). Pagar esa re-verificación
   por un evento del que no cuelga ningún hook es gasto sin contrapartida.

El camino de salida cuando alguien *sí* quiera transcribir un evento nuevo está
en el mensaje de error del test: o registra un hook en `cognitive-os.yaml`, o lo
mueve a la lista en prosa con el motivo. No hay tercer camino y ésa es la idea.

**Límite conocido:** la lista de "no transcritos y por qué" es prosa en un
comentario, no la chequea nadie. Si mañana registramos un hook en `SessionEnd`,
el gate exige transcribirlo pero *no* exige sacarlo de esa lista, que quedaría
mintiendo. Es el mismo defecto una capa más adentro. No lo cerré: hacerlo pide
convertir el comentario en una clave YAML del manifest, y eso es editar la
estructura del contrato externo — decisión del operador, no mía.

## Las tres corridas

Comando único en todas: `.venv/bin/python3 -m pytest tests/contracts/test_claude_code_hooks_schema_conformance.py -q -k <filtro>`

### 1. Reintroducir el defecto de hoy — sacar `TeammateIdle` de la transcripción

```
E   AssertionError: Event(s) registered in cognitive-os.yaml with no transcribed contract in claude-code-hooks-schema.yaml: ['TeammateIdle']. Every hook on them is invisible to every assertion in this file. Transcribe the event from https://code.claude.com/docs/en/hooks.md (record the date), or drop the registration.
        TeammateIdle: teammate-idle
    assert not {'TeammateIdle'}
1 failed, 12 deselected in 0.29s
```

### 2. La otra mitad — registrar un hook en un evento nuevo sin transcribirlo

Necesaria además de la (1): sacar el evento del manifest fallaría igual contra un
conjunto de eventos hardcodeado. Sólo mutando `cognitive-os.yaml` se prueba que
el derivador **lee la config**. Se agregó `probe-session-end` en `SessionEnd`:

```
E   AssertionError: Event(s) registered in cognitive-os.yaml with no transcribed contract in claude-code-hooks-schema.yaml: ['SessionEnd']. Every hook on them is invisible to every assertion in this file. Transcribe the event from https://code.claude.com/docs/en/hooks.md (record the date), or drop the registration.
        SessionEnd: probe-session-end
    assert not {'SessionEnd'}
1 failed, 12 deselected in 0.16s
```

### 3. El caso inverso — transcribir `ConfigChange`, que no registramos

```
E   AssertionError: Event(s) transcribed in claude-code-hooks-schema.yaml that this repo registers no hook on: ['ConfigChange']. Unused host contract goes stale unnoticed. Either register a hook on the event in cognitive-os.yaml > harness.hooks, or move it to the 'Events NOT transcribed in full, and why' list in that manifest's header with the reason written out.
    assert not {'ConfigChange'}
1 failed, 12 deselected in 0.14s
```

### 4. (Segundo derivador) matcher inerte y matcher fuera de menú

`matcher: TaskCreate` en `task-created` (el manifest dice `matcher_supported: false`)
y `matcher: onexit` en `pre-compaction-flush` (`matcher_values: [manual, auto]`):

```
E   AssertionError: Hook(s) declare a `matcher` on an event that does not honour one, so the filter is dropped and the hook fires on every occurrence:
        task-created on TaskCreated with matcher 'TaskCreate'
      Drop the matcher and filter inside the hook, or move the hook to a tool event.
E   AssertionError: Hook matcher(s) outside the values the manifest transcribes for the event:
        pre-compaction-flush on PreCompact: 'onexit' not in ['manual', 'auto']
2 failed, 13 deselected in 0.16s
```

### Verde, con el árbol correcto

```
$ shasum -a 256 -c orig.sha256
manifests/claude-code-hooks-schema.yaml: OK
cognitive-os.yaml: OK
$ git status --short manifests/claude-code-hooks-schema.yaml cognitive-os.yaml
(sin salida)
$ .venv/bin/python3 -m pytest tests/contracts/test_claude_code_hooks_schema_conformance.py -q
............... 15 passed in 2.09s
$ .venv/bin/python3 -m pytest tests/contracts/test_codex_hooks_schema_conformance.py -q
....................... 23 passed in 3.94s
```

Antes eran 10 tests; ahora 15. El hermano de Codex se corrió por regresión: ambos
manifests conviven y no se pisan.

## Los otros tres derivadores: hecho, o especificado

**Hecho — #2, evento/matcher/async, dimensión `matcher`.** Lo elegí por dos
motivos: (a) es *el mismo hecho* que el #1 una columna más a la derecha —el
alcance de un evento— así que reusa fixture, fuente y archivo sin abrir
superficie nueva; (b) tiene la misma firma de defecto: una regla de alcance
escrita que nadie hace cumplir, y acá había **dos** copias de esa regla sin
guardián, una en la cabecera de `cognitive-os.yaml` (`matcher: optional
tool-name filter (PreToolUse/PostToolUse only)`) y otra en el manifest
(`TaskCreated: matcher_supported: false`, "A matcher written here is not
honoured"). Hoy nadie la viola: los 132 matchers viven en PreToolUse/PostToolUse.
Clavar una regla **antes** de la primera violación es más barato que después, y
la corrida 4 muestra que el gate no es decorativo. La dimensión `async` del mismo
trío ya la cubrían dos aserciones previas del archivo, así que no la repetí.

**Especificado — #3, existencia de hooks.** Es donde está la deriva real y la
tengo medida.
- *Qué se deriva:* para cada hook con `default_projection: true`, que llegue
  efectivamente a ejecutarse — o como handler propio en `.claude/settings.json`,
  o como hijo del dispatcher.
- *De dónde:* declarados de `cognitive-os.yaml`; alcanzados de la unión de
  `.claude/settings.json` **más** los hijos que `hooks/bash-hot-path-dispatcher.sh`
  invoca con `bash "$path"`. Ésa es la trampa que el encargo anticipa y que
  confirmo: el dispatcher referencia **29 scripts distintos** que no figuran en
  settings; un derivador que mire sólo settings los reporta a todos como muertos.
- *El agujero, medido hoy:* restando handlers **y** hijos del dispatcher quedan
  **cinco** hooks declarados como proyectables que no llegan a ningún lado —
  `concurrent-write-guard-codex-proxy.sh` (UserPromptSubmit), y
  `agent-bash-cwd-enforcer.sh`, `publication-safety.sh`, `rate-limit-precheck.sh`,
  `rate-limiter.sh` (PreToolUse). De los cinco, **uno** tiene decisión escrita:
  `rules/rate-limiting.md` documenta explícitamente que `rate-limiter.sh` no está
  registrado y que registrarlo es una decisión pendiente del operador. Los otros
  cuatro no tienen nota. Ése es el gate: igualdad entre declarados-proyectables y
  alcanzados, con una lista de excepciones **exacta** (disciplina de baseline que
  este archivo ya usa tres veces) donde cada entrada arrastra el `rules/*.md` que
  la justifica. `rate-limiter.sh` entra ahí el día uno; los otros cuatro se
  clasifican antes, no después.
- *Por qué no lo hice ahora:* clasificar cuatro hooks sin nota escrita es una
  decisión de operador sobre hooks que otros agentes están tocando en este mismo
  árbol (`agent-bash-cwd-enforcer.sh` figura modificado en `git status`).
  Congelar un baseline sobre archivos en movimiento sería fijar un número que ya
  cambió.

**Especificado — #4, instalación.** Qué se deriva: que lo que `hooks/self-install.sh`
instala en el perfil coincida con lo que el repo declara como instalable. De
dónde: el manifest de instalación versus el listado que el script recorre. Gate:
igualdad de conjuntos, misma forma que el #1. No lo abrí porque `self-install.sh`
está entre los archivos que otros agentes tocan en esta jornada y el encargo lo
marca como zona ajena.

**Especificado — #5, capacidades de arnés.** Qué se deriva: el bloque de
comentario de `cognitive-os.yaml` que enumera qué soporta cada arnés ("Codex:
SessionStart, UserPromptSubmit, Stop supported; SubagentStart, PreCompact
unsupported") es una tabla de capacidades **en prosa**, y el driver de Codex ya
decide lo mismo en código. Gate: que la prosa y el driver coincidan, o mejor, que
la prosa desaparezca y quede una sola fuente. Es el candidato más redituable
después del #3 y el más barato de los tres, porque el driver ya existe y es
ejecutable — a diferencia del contrato de Claude Code, acá sí hay algo que
re-correr y diffear.

## Lo que NO hice y por qué

- **No toqué `manifests/claude-code-hooks-schema.yaml`.** Ni una fecha
  `verified:`, ni una línea de contenido. El árbol quedó byte-idéntico
  (sha256 verificado tras cada mutación). La transcripción del contrato externo
  es otro problema y no era el mío.
- **No moví ningún baseline ni agregué uno.** El gate exige igualdad, no
  contención. No hay lista de eventos exceptuados; no hay dónde esconder un
  faltante.
- **No derivé de `.claude/settings.json`.** Es generado (ADR-064). Aparece en el
  archivo sólo donde ya aparecía antes, para el fixture `registrations` que
  chequea `async`, que es una propiedad del *handler* y no del alcance.
- **No convertí la lista en prosa de "no transcritos y por qué" en estructura
  YAML.** Cerraría el agujero de la capa siguiente, pero cambia la forma del
  contrato externo y eso lo decide el operador.
- **No construí un mecanismo genérico de derivación.** El paso 0 era no construir
  el framework. Dos derivadores concretos, en el archivo que ya existía, sin
  abstracción compartida entre ellos más allá de un fixture.
- **No corrí `tests/contracts/` completo:** el directorio excede los dos minutos.
  Corrí el archivo tocado (15/15) y el hermano de Codex (23/23), que es el que
  comparte manifest y fixtures.
- **No commiteé ni pusheé.** Cambios en el working tree, un solo archivo.

### Nota de solape (verificada, no asumida)

Otro agente dejó sin trackear `tests/contracts/test_hook_header_registration_claims.py`,
que deriva **cabeceras de hook contra el settings generado**
(`test_event_header_names_a_real_registration`,
`test_matcher_header_names_a_real_registration`, …). Es otro eje: ahí la pregunta
es si el comentario del script coincide con su registración; acá es si el alcance
del manifest coincide con la config. Se cruzan sólo en `matcher`, y ni siquiera
ahí: aquél chequea que la cabecera `# Matcher:` diga la verdad, éste chequea que
el matcher **haga algo** en ese evento. Son complementarios. El derivador #3
especificado arriba sí toca el mismo terreno que ese archivo — quien lo construya
debe leerlo primero en vez de reimplementarlo.

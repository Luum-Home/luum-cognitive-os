<!-- SCOPE: os-only -->

# Aserciones para los otros dos canales — 2026-08-20

> Encargo: inventariar las afirmaciones verificables de `templates/project-gotchas.md`
> y `hooks/inject-phase-context.sh`, correr cada una, y dejar una
> `executable_assertion` por cada una que sobreviva — cada una con su
> contrafáctico corrido.
>
> Resultado: **1 afirmación falsa corregida**, **6 aserciones nuevas**, **6 de 6
> falsadas** con mutación de la realidad en un worktree aislado. Y un hallazgo
> que no estaba en el encargo: el canal B **no entrega nada** cuando
> `CLAUDE_PROJECT_DIR` no está seteado.

Repo en HEAD `50043e6ec`, rama `main`.

---

## Correcciones a las premisas del encargo

**1. «`templates/project-gotchas.md` quedó diciendo "Nothing blocks this today"
sobre el mismo guard que sí bloquea — vivo y falso hasta hoy.» → Ya no.**

Esa frase no está en el archivo. El commit `50043e6ec` —el HEAD que me dieron—
ya la había reemplazado. Hoy la línea 21 dice lo contrario y lo dice bien:

```bash
$ grep -rn "Nothing blocks this" --include='*.md' --include='*.sh' --include='*.yaml' .
docs/06-Daily/reports/reauditoria-de-las-once-correcciones-2026-08-20.md:62: (See 2026-05-02 incident. Nothing blocks this today:
```

El único ejemplar que queda vive en un reporte con fecha en el nombre, que la
política de `forbidden_phrase_scan` excluye a propósito (`date-anchored
filename: historical record, cites old claims on purpose`). No hay nada que
corregir ahí.

**2. «Las otras dos NO TIENEN NINGUNA [aserción] — nada verifica lo que dicen.»
→ Correcto en cuanto a `executable_assertions`, pero no es cierto que nada las
verifique.** Ambos archivos ya estaban declarados como `required_docs` del claim
`claude_code_hook_registration`, que les corre 3 `required_phrases` y 4
`forbidden_phrases`:

```bash
$ grep -n 'project-gotchas\|inject-phase-context' manifests/documentation-truth-claims.yaml
163:      - hooks/inject-phase-context.sh
164:      - templates/project-gotchas.md
```

Es cobertura de frases, no de mediciones — que es exactamente la distinción que
el encargo hace. Pero «nada verifica lo que dicen» sobredimensiona el hueco: la
parte de esos archivos que habla del registro de hooks sí estaba vigilada. El
hueco real eran las **mediciones**.

**3. El manifiesto ya declaraba este trabajo como pendiente, con nombre y
motivo.** El campo `facts.not_covered` del claim `agent_channel_facts` dice
textualmente que el canal B y B-prime «get their own assertions once the
correcting pass lands». No lo vi mencionado en el encargo; conviene saber que
la deuda estaba registrada, no olvidada.

**4. «Sólo la primera tiene aserciones ejecutables» — y hay que mirar cuál.**
La aserción preexistente `channel_is_still_delivered` **no** cubre el canal B, y
además comete el pecado que el encargo denuncia: decide leyendo
`.claude/settings.json`, no corriendo el hook. Mi `gotchas_channel_delivers_the_file`
corre el hook. No la toqué, pero conviene saber que es un registry-check, no
una prueba de entrega.

**5. Una premisa del encargo me obligó a trabajar distinto: «Limpiá
`COS_ALLOW_PROTECTED_CONFIG_WRITE` y `COS_BYPASS` del entorno».** Correcta y
necesaria, pero incompleta en una dirección práctica: con el guard activo,
`protected-config-write-guard.sh` bloquea cualquier comando de Bash que mencione
`hooks/` **junto a una redirección**, aunque la redirección apunte al scratchpad.
Me bloqueó dos veces sondas de sólo lectura. No activé el bypass: moví la sonda a
un script en el scratchpad. Queda anotado porque el próximo que quiera correr un
hook a mano se va a chocar con lo mismo.

---

## Hallazgo no pedido: el canal B se cae en silencio sin `CLAUDE_PROJECT_DIR`

`hooks/inject-phase-context.sh:16` resuelve el root así:

```bash
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
```

Para un hook que vive en `<repo>/hooks/`, `dirname/../..` es el **padre del
repo**, no el repo:

```bash
$ D=$(cd "$(dirname hooks/inject-phase-context.sh)/../.." && pwd)
$ [ "$D" = "$PWD" ] && echo "same as repo root" || echo "resolves ABOVE the repo root"
resolves ABOVE the repo root
$ basename "$D"; basename "$PWD"
luum
luum-agent-os
$ test -f "$D/templates/project-gotchas.md" && echo found || echo "NOT at fallback root"
NOT at fallback root
```

La consecuencia medida, mismo payload, misma máquina:

| `CLAUDE_PROJECT_DIR` | bytes emitidos | `PROJECT:` | gotchas entregado |
|---|---|---|---|
| sin setear | 1636 | `my-project (webapp)` (los defaults) | **no** |
| seteado    | 8645 | el proyecto real | sí |

Se pierden en silencio el yaml, la fase, el nombre del proyecto y el archivo
entero de gotchas. En Claude Code la variable siempre está seteada, así que en
producción no se ve; pero el propio encabezado del hook dice que contempla ser
invocado *fuera* de Claude Code («Falls back to stderr when invoked outside
Claude Code»), y ahí el fallback está roto. El idiom `../..` lo comparten 10
hooks (`grep -h 'CLAUDE_PROJECT_DIR:-' hooks/*.sh | sort | uniq -c`), así que
arreglarlo es una decisión de alcance mayor que este encargo: **no lo toqué**,
lo dejo reportado y lo dejo escrito dentro del `claim` de la aserción de
entrega, que fija la condición de producción a propósito.

Descartado por medición, no por intuición: el filtro de presupuesto de contexto
**no** es el culpable — 9025 bytes entran, 9025 salen, el centinela sobrevive.

---

## Inventario — `templates/project-gotchas.md`

| # | Afirmación | ¿Medición o contrato? | Veredicto | Comando que lo produjo |
|---|---|---|---|---|
| G1 | No hay `lib/` en la raíz; `ls -d lib` da "No such file or directory" | medición | **verdadera** | `ls -d lib` → exit 1, `ls: lib: No such file or directory` |
| G2 | `batch_runner.py`, `ground_truth.py`, `cost_predictor.py` son symlinks; `peer_card.py` **no** | medición | **verdadera** | `for f in ...; do [ -L "cos_lib/$f.py" ]` → 3 SYMLINK, `peer_card.py: regular file` |
| G3 | Tres directorios enteros son symlinks, con esos tres destinos | medición | **verdadera** | `find cos_lib -maxdepth 1 -type l -exec sh -c 'test -d "$1" && echo "$1 -> $(readlink "$1")"' _ {} \;` → 3 líneas exactas |
| G4 | `rm`+`ln -s` relativo bajo dir-symlink **está bloqueado**, exit 2 | medición | **verdadera** — *ya cubierta* por `blocking_hook_actually_blocks` | payload por stdin a `bash-hot-path-dispatcher.sh` → exit 2 |
| G4b | Recrear un dir-symlink **de primer nivel no se atrapa** | medición | **verdadera** | mismo dispatcher, payload top-level → exit 0 |
| G5 | Sacando comentarios sobrevive **una** referencia al yaml, y es un `[ -f ]` | medición | **verdadera** | `sed 's/#.*//' scripts/_lib/settings-driver-claude-code.sh \| grep -n 'cognitive-os\.yaml'` → 1 línea, `if [ -f "cognitive-os.yaml" ]` |
| G6 | «Corré `audit_hook_registration.py`; no cuentes a mano» | **contrato** | n/a — no se pudre | — |
| G7 | «Desde ADR-093 el profile es two-tier (`default \| full`)» | medición | **FALSA — corregida** | ver abajo |
| G8 | «No todo hook está cableado» + los comandos para contarlos | **contrato** (entrega comandos, no dígitos) | n/a | — |
| G9 | Orquestador default `qwen,claude` | medición | **verdadera** — no automatizada (ver *Lo que dejé sin aserción*) | `grep -n 'providers' scripts/orchestrator.py` → `:311 providers_raw = ... or "qwen,claude"` |
| G10 | Tabla «Before modifying» / falsos positivos comunes | **contrato** | n/a | — |

### G7 era falsa: no son dos tiers, son tres

`scripts/apply-efficiency-profile.sh` acepta **siete** grafías y las resuelve a
**tres** tiers. `lean`/`standard`/`minimal` no desaparecieron: siguen siendo
entradas válidas que caen en `maintainer` con una nota por stderr.

```bash
$ sed -n '/^case "$RAW_PROFILE" in/,/^esac/p' scripts/apply-efficiency-profile.sh \
  | grep -oE '^[[:space:]]*[a-z|]+\)' | tr -d ' )' | tr '|' '\n' | sort -u | tr '\n' ' '
core default full lean maintainer minimal standard
```

La frase vieja salió de releer el comentario de `cognitive-os.yaml`
(`profile: default   # default | full`), que dice lo mismo y **también está mal**
— no lo toqué, pero queda señalado en el `next_action` de la aserción para que
nadie vuelva a copiar la lista de ahí. Un agente al que se le dice que hay dos
tiers no puede razonar sobre el tercero, que es justo bajo el que corre.

---

## Inventario — `hooks/inject-phase-context.sh`

| # | Afirmación | ¿Medición o contrato? | Veredicto | Comando que lo produjo |
|---|---|---|---|---|
| H1 | El archivo de gotchas llega al agente cuyo prompt nombra `hooks/`/`settings.json` | medición (entrega) | **verdadera en producción**; falsa sin `CLAUDE_PROJECT_DIR` | sonda end-to-end, 8645 vs 1636 bytes |
| H2 | `plans/` en la raíz tiene sólo un README; los planes activos están en `.cognitive-os/plans/`; ambos existen a propósito | medición | **verdadera** | `ls -A plans/` → `README.md`; `ls -A .cognitive-os/plans \| wc -l` → 5 |
| H3 | «Steps have `type: agent\|script\|gate`» | medición | **fiel al doc, pero el doc se contradice** — ver abajo | `grep -n 'type:' docs/08-References/root/adw-patterns.md` |
| H4 | Los tres dir-symlinks de `cos_lib` (idéntico a G3) | medición | **verdadera** | mismo `find` |
| H5 | `cos_lib_symlink_invariant_audit.py`: exit 0 = sin drift, e imprime el conteo | medición | **verdadera** | `python3 scripts/cos_lib_symlink_invariant_audit.py` → exit 0, `0 ERROR(s), 0 WARN(s), 70 passing pair(s)` |
| H6 | Driver hardcodeado, UNA referencia al yaml (idéntico a G5) | medición | **verdadera** | mismo `sed`+`grep` |
| H7 | `subagent-context-injector.sh` es el único dueño de la entrega del preámbulo | medición (comentario de código) | **verdadera** | `grep -n 'agent-preamble' hooks/*.sh` → sólo el injector lo lee como `PREAMBLE_FILE`; `completion-gate.sh` sólo lo cita por stderr, `inject-phase-context.sh` sólo lo huellea para la cache |
| H8 | Regexes de keyword, cap de 10K, TTL de 60s | **contrato** (el hook describe su propia mecánica) | n/a | — |

### H3: el hook cita bien un documento que se contradice

El hook dicta `type: agent|script|gate`, que es literalmente la línea 41 de
`adw-patterns.md`. Pero el mismo documento usa en la línea 155 un `type:
piter-loop`, y ningún workflow vivo usa `script`:

```bash
$ grep -rhoE '^\s*type:\s*[a-z_]+' .cognitive-os/workflows/ | awk '{print $2}' | sort | uniq -c
  13 agent
   2 gate
$ grep -n 'type:' docs/08-References/root/adw-patterns.md
41:    type: agent | script | gate
131:    type: agent
136:    type: gate
140:    type: agent
155:    type: piter-loop
```

**No escribí aserción para esto y no cambié la frase.** La única aserción no
circular posible sería «todo tipo usado en los workflows vivos está nombrado en
la frase», y su contrafáctico exige agregar un workflow con un tipo nuevo bajo
`.cognitive-os/` — que el encargo me prohíbe tocar. Queda como deuda con el
comando arriba: la frase no es falsa, el documento que la respalda sí es
inconsistente, y eso se arregla en `adw-patterns.md`, no en el hook.

---

## Las seis aserciones nuevas, con su contrafáctico corrido

Todas viven en `manifests/documentation-truth-claims.yaml`, bajo
`claims.agent_channel_facts.executable_assertions`. Todas siguen el modelo de
`blocking_hook_actually_blocks`: argv sin shell, ejecutable en allow-list,
`expect.exit_code: 0` + `surface:` con los archivos vivos que la sonda lee.
Todas fallan ruidosamente si **no encuentran nada que chequear** — un `exit 0`
por vacío es el bug que este manifiesto ya pagó una vez.

El contrafáctico se corrió con `scripts/channel_assertion_falsifiability_check.py`,
que arma un `git worktree` aislado, corre la aserción sin tocar nada (**control**,
tiene que dar verde: una aserción ya roja hace el contrafáctico inútil), **muta la
realidad**, vuelve a correrla, y deshace. Salida completa:

```
### gotchas_channel_delivers_the_file
  control    : exit 0  GREEN  | channel B delivered templates/project-gotchas.md on a keyword prompt (9306 bytes) and withheld it on an unrelated one (834 bytes)
  mutation   : hooks/inject-phase-context.sh: keyword gate no longer matches hooks/ or settings.json
  after mut. : exit 1  RED (falsifiable) | channel did NOT deliver templates/project-gotchas.md on a hooks/settings.json prompt (1643 bytes emitted)

### cos_lib_directory_symlinks_match_the_prose
  control    : exit 0  GREEN  | 3 cos_lib directory symlinks, each named with its target in both channel files
  mutation   : cos_lib/newly_added_pkg -> ../packages/llm-providers/lib (a 4th directory symlink)
  after mut. : exit 1  RED (falsifiable) | prose says three whole directories are symlinks; measured 4

### toplevel_dir_symlink_is_not_caught
  control    : exit 0  GREEN  | guard limit holds: nested relative target blocked (exit 2), top-level dir symlink allowed (exit 0)
  mutation   : hooks/symlink-mutation-guard.sh: now blocks every `ln -s`, top-level included
  after mut. : exit 1  RED (falsifiable) | the top-level payload IS caught now (exit 2): the documented limit is stale and agents are being told the guard is narrower than it is

### efficiency_profile_tiers
  control    : exit 0  GREEN  | efficiency tiers resolved by scripts/apply-efficiency-profile.sh: core maintainer full -- and the gotchas says so
  mutation   : scripts/apply-efficiency-profile.sh: `maintainer` dropped from the case arm
  after mut. : exit 1  RED (falsifiable) | the gotchas does not carry the tiers the driver resolves to (core full)

### named_symlink_examples_still_hold
  control    : exit 0  GREEN  | examples hold: 3 quoted symlink(s), 1 quoted regular file(s)
  mutation   : cos_lib/batch_runner.py: symlink replaced by a regular file
  after mut. : exit 1  RED (falsifiable) | the named examples no longer match the filesystem: [cos_lib/batch_runner.py is quoted as a symlink and is not one]

### plans_dir_split_still_holds
  control    : exit 0  GREEN  | plans/ holds only a README; .cognitive-os/plans holds 62 entr(y|ies)
  mutation   : plans/REVIVED-PLAN.md created
  after mut. : exit 1  RED (falsifiable) | plans/ holds more than a README, so the sentence is now false:
plans/REVIVED-PLAN.md

==============================================================================
ALL SIX FALSIFIED
```

Cada mutación es una **mutación de la realidad**, no del texto de la sonda: se
rompe el regex del hook, se agrega un cuarto symlink, se ensancha el guard, se
saca un tier del `case`, se convierte un symlink en archivo regular, se mete un
plan en `plans/`. Ninguna se falsó editando la aserción para que no encontrara
su sujeto.

### Cada aserción se derivó de una fuente distinta de la que produjo la frase

Es la regla que el encargo pide y la que rompió `tests_symlink_census`:

| Aserción | La frase salió de… | La aserción ejecuta… |
|---|---|---|
| `gotchas_channel_delivers_the_file` | leer el `if` del hook | **correr el hook** con dos payloads y mirar los bytes que salen |
| `cos_lib_directory_symlinks_match_the_prose` | la prosa que enumera tres | `find`+`readlink` sobre el filesystem, y exige que la prosa describa lo hallado (dirección inversa) |
| `toplevel_dir_symlink_is_not_caught` | leer el guard | alimentar los **dos** payloads al dispatcher y comparar exit codes |
| `efficiency_profile_tiers` | releer el comentario de `cognitive-os.yaml` | `awk` sobre el `case` de `apply-efficiency-profile.sh` — el código que resuelve, no el comentario que describe |
| `named_symlink_examples_still_hold` | la prosa | parsea los nombres **del propio doc** y le pregunta al filesystem |
| `plans_dir_split_still_holds` | la prosa del hook | `find` sobre los dos directorios |

### Y una de ellas ya se puso roja sola, antes del contrafáctico

`gotchas_channel_delivers_the_file` falló en su primera corrida real:

```
exit:1  stdout: channel did NOT deliver templates/project-gotchas.md
        on a hooks/settings.json prompt (9306 bytes emitted)
```

9306 bytes emitidos y aun así "no delivered": el centinela que buscaba era el H1
con guion largo, y `json.dumps` lo emite como `—`. La sonda comparaba texto
crudo contra JSON escapado. Es exactamente la familia de error que el encargo
persigue — **el instrumento equivocándose igual que la frase** — sólo que esta
vez el gate se puso rojo en vez de certificar verde. El centinela ahora se
deriva recortando el H1 a ASCII:

```bash
SENTINEL=$(grep -m1 '^# Project Gotchas' "$G" | LC_ALL=C sed 's/[^ -~].*//; s/[[:space:]]*$//')
[ "${#SENTINEL}" -ge 12 ] || { echo "no ASCII-only H1 sentinel ..."; exit 1; }
```

---

## Lo que dejé sin aserción, y por qué

- **G9 (orquestador `qwen,claude`)**: verdadera hoy
  (`scripts/orchestrator.py:311`), pero es una afirmación sobre un **default de
  CLI**, no sobre lo que el SO le dicta al agente en ese momento. La aserción
  honesta sería correr el orquestador, que dispara costo real. Queda con su
  comando en la tabla.
- **H3 (`type: agent|script|gate`)**: explicado arriba — el contrafáctico exige
  escribir bajo `.cognitive-os/`, que el encargo prohíbe. No la agregué en vez
  de agregar una que no puedo falsar.
- **H7 (dueño único del preámbulo)**: verdadera y falsable, pero es un
  **comentario de código**, no texto que se le dicte a ningún agente. Fuera del
  canal.

En los tres casos la regla que apliqué es la del encargo: **si no la puedo
falsar, o no puedo demostrar que se pone roja, no la agrego.**

---

## Verificación

```bash
$ .venv/bin/python3 scripts/documentation_truth_audit.py --fail-on-block; echo "EXIT=$?"
EXIT=0
```

Del reporte generado: `by_status: {'pass': 165}`, `executable_assertions: 12`
(eran 6, ahora 12).

```bash
$ .venv/bin/python3 -m pytest tests/contracts/test_canal_al_subagente_tiene_margen.py -q
....                                                                     [100%]
4 passed in 0.04s
```

```bash
$ .venv/bin/python3 scripts/channel_assertion_falsifiability_check.py; echo "EXIT=$?"
ALL SIX FALSIFIED
EXIT=0
```

Nota sobre el exit code: la primera corrida de la auditoría la leí mal con
`${PIPESTATUS[0]}` bajo zsh (donde la variable es `pipestatus`) y me devolvió 0
sobre un `status: block`. El exit real se toma sin pipe.

---

## Deuda que queda anotada

1. `hooks/inject-phase-context.sh:16` — fallback `../..` off-by-one; lo comparten
   10 hooks. Requiere decisión de alcance.
2. `cognitive-os.yaml` — el comentario `# default | full` es la fuente de la
   afirmación falsa G7 y sigue igual.
3. `docs/08-References/root/adw-patterns.md` — la línea 41 declara tres tipos de
   step y la 155 usa un cuarto.
4. `channel_is_still_delivered` decide leyendo el registro, no corriendo el hook.

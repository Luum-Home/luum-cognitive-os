# Freeze-gate activation forensics — 2026-08-15

Alcance: medir qué pasa realmente si se aplica
`docs/05-Methodology/runbooks/gate-exit-code-contract-2026-08-15/gate-exit-codes.patch`.
Todo se verificó **ejecutando**, no grepeando. El parche no se aplicó sobre este
repo: las pruebas corrieron sobre dos clones descartables en el scratchpad.

**Veredicto en una línea: APLICAR-PARCIAL.** El hunk de `adoption-freeze-gate`
arregla una falla demostrada hoy en vivo y no traba nada del trabajo en curso.
Los otros dos son inertes, pero uno de ellos es inerte por accidente y el parche
lo deja armado.

---

## 0. La premisa central del encargo es falsa: el gate ya está encendido

El encargo pregunta "¿encenderlo bloquea algo hoy?". No hay nada que encender.
`adoption-freeze-gate.sh` **corre hoy, en cada `git commit`**, y viene corriendo
hace meses.

```bash
wc -l < .cognitive-os/logs/adoption-freeze-gate.jsonl     # 279
tail -1 .cognitive-os/logs/adoption-freeze-gate.jsonl
# {"timestamp":"2026-08-15T19:19:36Z","action":"pass","reason":"no gated paths touched"}
```

279 invocaciones, la última 40 minutos antes de escribir esto. El parche no
enciende el gate: **conecta el gatillo de un gate que ya venía apretando el
percutor en el vacío.**

---

## 1. La contradicción del cableado, resuelta

Las dos mediciones son correctas. Miden superficies distintas, y **ninguna de las
dos mide la que decide.**

| # | Comando | Resultado |
|---|---|---|
| 1 | `grep -c 'adoption-freeze' .claude/settings.json` | `0` |
| 2 | `grep -c 'adoption-freeze' .githooks/pre-commit` | `0` |
| 3 | `grep -n 'adoption-freeze' cognitive-os.yaml` | `2` (líneas 2060-2061) |
| 4 | `grep -n 'adoption-freeze' hooks/bash-hot-path-dispatcher.sh` | `1` (línea 140) |

### El comando que resuelve la contradicción

```bash
grep -n 'bash-hot-path-dispatcher' .claude/settings.json
# 252: "command": "bash \"$CLAUDE_PROJECT_DIR/scripts/hook-timing-wrapper.sh\"
#       PreToolUse \"$CLAUDE_PROJECT_DIR/hooks/bash-hot-path-dispatcher.sh\""
```

La sexta superficie de cableado es **el registro por delegación**. El dispatcher
sí está en `settings.json` como único hook `PreToolUse:Bash`, y en su línea 140
corre `adoption-freeze-gate.sh` dentro del bloque `_is_git_commit`. Buscar el
gate por nombre en `settings.json` no puede encontrarlo, porque el gate no se
registra: lo registra su despachador.

**Ambos agentes tenían razón sobre su superficie. La conclusión "no registrado ⇒
no corre" es la que falla.**

### Por qué la telemetría dijo 0 disparos, y por qué eso también era cierto

```bash
grep -c 'adoption-freeze'        .cognitive-os/metrics/hook-timing.jsonl  # 0
grep -c 'bash-hot-path-dispatcher' .cognitive-os/metrics/hook-timing.jsonl # 2107
```

`hook-timing.jsonl` solo registra hooks invocados por
`scripts/hook-timing-wrapper.sh`. Los hijos que corre el dispatcher nunca pasan
por el wrapper, así que **son estructuralmente invisibles a esa telemetría**. El
punto ciego tiene exactamente el tamaño de la lista de hijos del dispatcher: 16
gates de commit-time. Cualquier auditoría futura que use `hook-timing.jsonl` para
afirmar "este hook nunca corrió" va a repetir este error sobre esos 16.

La evidencia buena es el log propio de cada gate, en `.cognitive-os/logs/`.

### Qué inspecta cuando llega ahí

El encargo supone que, siendo `PreToolUse` sobre Bash, el gate mira el comando y
no el índice. **Es mitad y mitad, y la mitad que importa es la segunda:**

- se *dispara* por forma de comando (`hooks/adoption-freeze-gate.sh:34`,
  `[[ "$COMMAND" != *"git commit"* ]] && exit 0`);
- pero *decide* leyendo el índice de git
  (`hooks/adoption-freeze-gate.sh:76`, `git diff --cached --name-only`).

### Por qué el commit del primer agente no disparó

No fue por falta de cableado. Fue por el índice vacío. Con el idioma que este
mismo repo obliga a usar en checkout compartido —`git commit --only -m "..." --
<paths>`— **no hay nada staged en el momento `PreToolUse`**, y el gate sale por
la línea 77:

```
[ -z "$STAGED" ] && { _log '..."reason":"no staged"'; exit 0; }
```

Medido sobre clon, con el archivo gateado sucio pero **sin stagear**:

```
index:   []
freeze-gate exit = 0 (PATCHED)
verdict: {"action":"pass","reason":"no staged"}
```

Y no es un caso de borde: **153 de las 279 invocaciones (55%) salieron por
`"no staged"`.** El gate está ciego a más de la mitad de los commits del repo, y
el parche no toca eso.

---

## 2. El hallazgo que decide: el gate ya bloqueó 5 veces y no bloqueó ninguna

```bash
grep '"action":"block"' .cognitive-os/logs/adoption-freeze-gate.jsonl   # 5 filas
```

Cuatro el 2026-07-10 (13:40→13:49, el mismo set de 5 rutas cuatro veces: alguien
reintentando) y **una hoy, 2026-08-15T15:41:24Z**.

El bloqueo de hoy señaló 5 rutas gateadas. El commit correspondiente:

```bash
git log --all --since="2026-08-15 00:00" --format='%h %cI %s' -- \
  docs/06-Daily/reports/external-tools-radar-INDEX.md
# eda279d1f 2026-08-15T12:41:58-03:00 fix(docs): repair 1542 broken links ...
```

`15:41:24Z` el gate dijo BLOCKED. `15:41:58Z` —34 segundos después— el commit
entró. Los 10 archivos de los 5 eventos de bloqueo están todos en la historia:

```
docs/03-PoCs/research/ifixai-annex-e-primitives-2026-05-11.md      commits=3
docs/06-Daily/reports/external-tools-radar-INDEX.md                commits=5
manifests/external-tools-adoption.yaml                             commits=7
...  (10/10 landearon)
```

**Esto es el contrato de exit codes fallando en producción, hoy, no en teoría.**
El gate evaluó bien, escribió el veredicto correcto en su log, imprimió el
mensaje de bloqueo, y salió `1` — que en `PreToolUse` es un error no bloqueante.

Confirmado sobre clon, con el archivo gateado staged:

```
--- BEFORE patch ---   freeze-gate exit = 1
--- AFTER  patch ---   freeze-gate exit = 2
```

y la propagación por el dispatcher, con el comando ya scopeado para pasar
`git-commit-scope-guard`:

```
scope-guard exit  = 0
freeze-gate exit  = 2 (PATCHED)
DISPATCHER exit   = 2
=== ADOPTION-FREEZE-GATE: BLOCKED ===
  - manifests/external-tools-adoption.yaml
```

`scripts/hook-timing-wrapper.sh:526` devuelve `exit $HOOK_EXIT` verbatim, y su
línea 440 trata `HOOK_EXIT -eq 2` como el caso "bloqueó". El wrapper ya asume el
contrato que el parche escribe.

> **Trampa metodológica que casi me come.** La primera medición dio
> `DISPATCHER exit = 2` *antes* del parche, lo que parecía probar que ya
> bloqueaba. Falso: con un `git commit -m test` sin scope,
> `git-commit-scope-guard` sale `2` en la posición 2 de la cadena y
> cortocircuita — el freeze gate **nunca corría**. Aislar gate por gate fue lo
> que lo mostró. Medir el dispatcher entero no dice qué gate habló.

---

## 3. Pregunta 1 — ¿bloquea algo del trabajo de hoy? No

Recuento propio, con `git ls-files` + `fnmatch` sobre los 5 globs:

| glob | trackeados |
|---|---|
| `docs/03-PoCs/research/*-annex-*-*.md` | 22 |
| `docs/03-PoCs/research/*-comparison-*.md` | 3 |
| `docs/06-Daily/reports/external-tools-radar-*.md` | 21 |
| `docs/03-PoCs/research/repo-scout/deep/*.md` | 73 |
| `manifests/external-tools-adoption.yaml` | 1 |
| **total (dedup)** | **120** |

**La cifra previa de 120 se reproduce exacta**, después de los 59 commits
mergeados y los ~15 informes nuevos de hoy.

Lo que importa de verdad:

```
modified/untracked en worktree: 38  | staged: 7
DIRTY  matcheando globs gateados: 0
STAGED matcheando globs gateados: 0
```

Y el entregable de esta sesión, probado sobre clon con el parche aplicado:

```
docs/06-Daily/reports/freeze-gate-activation-forensics-2026-08-15.md -> NO MATCH
PATCHED freeze-gate exit = 0
verdict: {"action":"pass","reason":"no gated paths touched"}
external-pattern-cleanroom-gate  exit=0
adoption-freeze-gate             exit=0
research-to-runtime-firewall     exit=0
```

Los 120 son históricos y están quietos. **El gate efectivo no traba nada del
working set actual, y no nace estorbando informes de auditoría**: el glob de
reports es `external-tools-radar-*.md`, no `docs/06-Daily/reports/*`.

Matiz honesto, no cero fricción absoluto: **sí habría bloqueado `eda279d1f` hoy**
(el fix de 1542 links rotos tocaba `external-tools-radar-INDEX.md`). Es reparación
de links, no adopción — o sea, el primer bloqueo real del gate efectivo sería un
falso positivo de mantenimiento, resoluble con el bypass logueado que el propio
gate documenta.

---

## 4. Pregunta 2 — `research-to-runtime-firewall`: **gate mal especificado**

La medición se reproduce: 3 archivos.

```bash
git grep -l -- '.cognitive-os/external-source-cache' -- 'lib/*' 'packages/*' 'scripts/*'
# scripts/cos_clean_room_ast_similarity.py
# scripts/cos_efficiency_primitives.py
# scripts/cos_verbatim_copy_detector.py
```

Pero la composición refuta tanto al encargo como al remedio propuesto. Las 4
referencias, con su rol:

| archivo:línea | rol de la referencia |
|---|---|
| `cos_clean_room_ast_similarity.py:7` | **docstring** — prosa que describe la herramienta |
| `cos_verbatim_copy_detector.py:6` | **docstring** |
| `cos_verbatim_copy_detector.py:77` | `DEFAULT_CACHE_SUBDIR` — constante: el objetivo del escaneo |
| `cos_efficiency_primitives.py:58` | **`IGNORED_DIRS`** — nombra el cache **para excluirlo** |

**Cero imports. Cero lecturas. Ninguno de los tres ingiere nada del cache.** El
detector es un `grep -q` sobre el contenido entero del archivo
(`hooks/research-to-runtime-firewall.sh:56`), comentarios incluidos.

### Refutación al remedio propuesto

El operador propone "exención acotada para los enforcers". **No alcanza:**
`cos_efficiency_primitives.py` no es un enforcer de cleanroom — es un escáner de
eficiencia, y quedaría bloqueado igual. Y es el caso más fuerte de los tres: el
firewall bloquearía un archivo **por contener la instrucción de saltear el
cache**. Un gate que castiga a quien escribe "no toques esto" se comió su propio
propósito antes de llegar a los detectores.

Por eso la salida no es una lista de archivos exentos. Una allowlist de nombres
se pudre: renombrás un archivo y el gate queda ciego; agregás un cuarto detector
y el falso positivo vuelve.

**El arreglo es angostar el predicado**: de "la cadena aparece en cualquier parte
del archivo" a "el archivo ingiere contenido del cache" (import / open / read /
glob), excluyendo comentarios y docstrings. Eso es lo que el hook ya *dice* que
protege en sus líneas 5-8 ("research-only clones must not feed runtime modules").
La regla escrita está bien; el detector es más ancho que la regla.

### La tensión con el caso 2, resuelta con las palabras del caso 2

`scripts/audit_decision_backing.py:34-37` ya tiene la doctrina:

> "Explicitly NOT decision surfaces (and therefore not audited here): read-only
> evidence scripts, tests, reports, internal helpers, docs, and inventories with
> no policy verbs. **If you widen the population, widen it here, in code, with a
> reason — not in prose.**"

La distinción del operador se sostiene, y el caso 2 le da el mecanismo:

- **Caso 2**: el instrumento está *legítimamente dentro* de la población que él
  mismo definió (es un manifiesto de política con ratchet — una superficie de
  decisión real). Exceptuarse sería perdonar un **verdadero positivo**. Verde
  barato. Hizo bien en no exceptuarse.
- **Este caso**: los 3 archivos **no están en la población que la regla dice
  proteger** (runtime que ingiere el cache). Son **falsos positivos** de un
  predicado demasiado ancho.

Uno es una excusa; el otro es una definición incompleta. Y el arreglo del caso 2
—angostar la población en código, con el motivo escrito— es exactamente el
arreglo de acá. No son doctrinas opuestas: es la misma doctrina.

**Confirmo el diagnóstico del operador** (defecto de especificación, no deuda de
estado) **y refino el remedio**: angostar el predicado, no exceptuar enforcers.

### Urgencia: baja, y el parche hace bien en dejarlo afuera

```bash
ls .cognitive-os/logs/research-to-runtime-firewall.jsonl
# No such file or directory   ← nunca escribió una línea
grep -c 'research-to-runtime-firewall' <patch>   # 0
```

El firewall está cableado (dispatcher línea 142) pero **nunca disparó una sola
vez**: solo escanea archivos staged, y los 3 no se tocan. Está latente, no en
rojo. Salta el día que alguien stagee una edición a uno de esos tres — y, al
seguir en `exit 1`, ni siquiera bloquearía. **El parche no lo arma, y hace bien.**
Es trabajo de diseño, no urgencia.

---

## 5. Pregunta 3 — los otros dos

### `clean-room-ast-similarity-gate` — inerte. Confirmado

```
settings.json:      0
dispatcher:         0
cognitive-os.yaml:  0      (el encargo decía "profile/manual_trigger": no está)
log file:           no existe
.py en el cache:    0
```

Única presencia real, en `.ai/adapters/claude-code/adapter.json`:

```json
{"claims_runtime_enforcement": false, "fidelity": "documented-only", ...}
```

**No corre por ninguna superficie. El cambio de exit code es inerte.** El hunk es
inofensivo: documenta la intención de un gate que no se ejecuta.

### `external-pattern-cleanroom-gate` — inerte, pero por el motivo equivocado

Este **sí está cableado** (dispatcher línea 139) y corrió **279 veces — el mismo
número exacto que `adoption-freeze-gate`**, lo que confirma que ambos corren en
cada commit. Pero:

```bash
python3 ... .cognitive-os/logs/external-pattern-cleanroom-gate.jsonl
#   279  ('skip', 'source repo absent')
ls -d /tmp/upstream-pattern-source
# No such file or directory
```

**279 de 279 saltearon. Nunca evaluó un solo archivo en toda su historia
registrada.** Es inerte hoy, sí — pero no por una razón estructural, sino porque
`/tmp/upstream-pattern-source` (`hooks/external-pattern-cleanroom-gate.sh:28`) no
existe. Eso es peor que inerte: es un gate que **se arma solo** el día que
alguien recree ese directorio, sin aviso, y con el parche lo haría bloqueando.

### El corpus en `/tmp` — hallazgo por derecho propio

Un gate cuyo corpus vive en un directorio que el sistema limpia no es un gate: es
un `exit 0` con pasos extra. Confirmado.

**Costo de moverlo** (no lo moví):

- *Barato*: la ruta es una constante única, línea 28. Cambiarla a una ruta durable
  es un renglón.
- *Caro, y es lo que hay que decidir primero*: **qué debe vivir ahí.** Poblarlo
  exige clonar fuentes upstream, que es justo lo que la freeze gobierna, y un
  corpus durable de código ajeno dentro del árbol del repo crea la superficie de
  IP que ADR-259/267 quieren evitar. Tendría que quedar gitignoreado
  deliberadamente, como ya está `.cognitive-os/external-source-cache/`.

O sea: mover la constante es trivial; decidir la política del corpus no lo es.
Mientras no se decida, **cambiarle el exit code a 2 sube el riesgo sin subir la
cobertura.**

---

## 6. Recomendación: APLICAR-PARCIAL

| hunk | recomendación | motivo |
|---|---|---|
| `adoption-freeze-gate.sh` | **Aplicar** | Arregla una falla demostrada hoy en vivo (5 bloqueos, 0 aplicados; `eda279d1f` entró 34s después de un BLOCKED). Cero fricción sobre el working set actual, probado sobre clon. |
| `bash-hot-path-dispatcher.sh` (comentario) | **Aplicar** | Solo comentario. Documenta que el dispatcher propaga verbatim y no convierte 1 en bloqueo — que es exactamente el malentendido que originó el bug. |
| `clean-room-ast-similarity-gate.sh` | **Aplicar** (indiferente) | Inerte por todas las superficies. Sin riesgo ni beneficio. |
| `external-pattern-cleanroom-gate.sh` | **Diferir** | Único hunk con riesgo neto. Convierte un gate dormido-por-accidente en uno que hard-blockea apenas reaparezca un `/tmp` que nadie controla. Aplicarlo **junto con** fijar el corpus en ruta durable y decidida, no antes. |

Sobre el verde barato de este lote: la recomendación **no** es "aplicá porque el
contrato dice 2". Es aplicar el hunk que tiene evidencia de daño real y working
set medido en cero, y frenar el que no. De los cuatro gates, **uno solo cambia de
comportamiento**: los otros tres no corren, o no evalúan.

Y aplicar el parche completo **no** enciende cuatro gates de commit a la vez: dos
ya corren y dos no corren por ninguna superficie. El cambio operativo real es de
un gate, no de cuatro.

### Fuera de alcance del parche, para el operador

1. **La ceguera del `--only` (55% de los commits)** es más grave que el exit code
   y el parche no la toca. El gate lee `git diff --cached`; el idioma obligatorio
   del repo no stagea nada. Arreglarlo pide leer las rutas del propio comando
   cuando viene `-- <paths>`, no solo el índice.
2. **`hook-timing.jsonl` no puede ver 16 gates.** Cualquier auditoría que afirme
   "nunca disparó" sobre un hijo del dispatcher está midiendo el punto ciego.
3. **`manifests/external-tool-adoption-freeze.yaml:enforcement_caveat` es falso.**
   Dice que el gate "no está registrado en `.claude/settings.json`... La freeze es
   hoy una política escrita con un enforcer sin cablear". El log de 279
   invocaciones y 5 bloqueos lo refuta. **No lo edité** (regla dura: archivo con
   peso de decisión del operador). Corregirlo es decisión suya; queda anotado como
   deuda de verdad documental.

---

## 7. Qué del encargo era falso

| afirmación del encargo | veredicto |
|---|---|
| "¿Encenderlo bloquea algo hoy?" | **Premisa falsa.** No hay nada que encender: 279 invocaciones, la última 40 min antes de este informe. |
| `adoption-freeze-gate` no registrado (agente 1) | **Cierto en 2 superficies, falso como conclusión.** Registrado por delegación vía dispatcher (`settings.json:252` → dispatcher:140). |
| "0 disparos en 37.424 filas de telemetría" | **Cierto del archivo, inválido como evidencia.** `hook-timing.jsonl` no puede registrar hijos del dispatcher. 279 disparos reales en el log propio. |
| Prueba en vivo: "mi commit tocó ruta gateada y no corrió" | **Sí corrió.** No bloqueó por índice vacío (`git commit --only`), no por falta de cableado. |
| "dispararía sobre comandos, no sobre el índice de git" | **Mitad falso.** Se dispara por comando (línea 34), decide por índice (línea 76). |
| "120 archivos trackeados, 0 staged o modificados" | **Confirmado exacto** tras 59 commits y ~15 informes nuevos: 120 / 0 / 0. |
| "dos de los tres son los detectores de cleanroom" | **Cierto pero incompleto, y la omisión importa.** El tercero (`cos_efficiency_primitives.py`) no es detector, nombra el cache **para excluirlo**, y una exención "para los enforcers" no lo cubriría. |
| `clean-room-ast-similarity-gate` "solo en profile, manual_trigger" | **Falso.** 0 en `cognitive-os.yaml`. Solo metadata de adapter, `claims_runtime_enforcement: false`. |
| Corpus de `external-pattern-cleanroom-gate` en `/tmp`, se saltea | **Confirmado**, 279/279 skip, y peor de lo dicho: se arma solo si el dir reaparece. |
| "encender cuatro gates de commit a la vez" | **Falso.** Un solo gate cambia de comportamiento; dos no corren y uno nunca evalúa. |

---

## Reproducibilidad

Clones descartables bajo el scratchpad de la sesión (`clone`, `clone2`), creados
con `git clone --local --no-hardlinks`; parche aplicado con `git apply` (4/4
hunks limpios). No se usó `git worktree` (bloqueado por `destructive-git-blocker`),
ni `install.sh`, ni se aplicó el parche sobre este repo. `git reset` disparó
correctamente el `destructive-git-blocker` durante la prueba y se reemplazó por un
segundo clon.

Sondas de gate, forma general:

```bash
JSON='{"tool_name":"Bash","tool_input":{"command":"git commit --only -m p -- <path>"}}'
printf '%s' "$JSON" | bash hooks/<gate>.sh >/dev/null 2>&1; echo "exit=$?"
```

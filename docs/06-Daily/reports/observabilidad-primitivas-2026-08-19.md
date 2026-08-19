# Observabilidad de uso por familia de primitivas — 2026-08-19

**Pregunta:** no "¿se usó cada primitiva?", sino **"¿es medible que se use?"**.
Una familia sin señal es una familia sobre la que ninguna afirmación de utilidad
puede hacerse — ni buena ni mala.

**Alcance:** las cinco familias del registry (`hooks/`, `rules/`, `scripts/`,
`templates/`, `SKILL.md` de `skills/` y `packages/*/skills/`). Cobertura de
**USO**, no de **PRUEBA**: `manifests/primitive-behavior-evidence.yaml` y los
ledgers `primitive-*-latest.*` miden que la primitiva *funciona*; esto mide si
existe forma de saber que *se ejecuta en producción*.

**Todo número de acá abajo lo conté yo.** Los comandos están al final, en
§Evidencia ejecutable, y son read-only.

---

## Correcciones a las premisas del encargo

Cinco premisas del encargo no sobreviven a la verificación. Tres cambian el
resultado.

**1. `skill-invocations.jsonl` NO está vacío, y su logger SÍ disparó.**
El encargo dice: *"está vacío porque su logger nunca disparó"*. Tiene **5 filas**
(1107 bytes), con eventos reales del 2026-07-29 y del 2026-08-15, `source:
"skill-invocation-logger"`. Y el hook **está registrado** en `.claude/settings.json`
como `PostToolUse` con `matcher: "Skill"`, envuelto en `hook-timing-wrapper.sh`.
Lo mismo `skill-usage.jsonl`: 5 filas, mismos tres skills.

La corrección importa porque invierte el diagnóstico de la familia skills: no es
"cero medición", es **medición viva con volumen ridículo** — tres skills
distintos (`encargo-refutable`, `ruteo-de-agentes`, `evidencia-ejecutable`) sobre
194 SKILL.md en tres semanas. El canal funciona; lo que falta es cobertura del
camino de invocación, no el canal.

**2. "9 archivos de métricas de skills, la mayoría vacíos" — ninguno está vacío.**
Los 9 existen y los 9 tienen contenido: `skill-drift` 2761 filas, `skill-suggestion`
467, `skill-metrics` 250, `skill-feedback` 195, `skill-archive` 72,
`skill-synthesis-queue` 37, `skill-routing` 20, `skill-invocations` 5,
`skill-usage` 5. Siete de los nueve escribieron **hoy**.

**3. Las 9111 filas de `hook-timing.jsonl` no son la historia, son ~3,5 horas.**
El archivo rota (`.cognitive-os/metrics/.archive/hook-timing-*.jsonl.gz`, 7
archivos). El archivo vivo arranca a las 15:20 y termina a las 18:58 del mismo
día. Contando **todas las ventanas**: **225.628 filas** y **157 hooks distintos**.

Sobre esa base, **los hooks que nunca dispararon son 2, no 6**: `task-created` y
`teammate-idle`. Los otros 4 del recuento del encargo dispararon en ventanas
anteriores. En espejo: **5 hooks disparan y ya no están registrados** — deriva en
la dirección contraria, invisible para el conteo original.

**4. El registry tiene 1440 rutas únicas, no ~1456.** La diferencia es
resolución de symlinks (`hooks/` tiene 291 `.sh` pero 289 realpaths únicos;
`skills/` + `packages/*/skills/` suman 194 SKILL.md únicos sobre 119+75 rutas) y
la exclusión de `__pycache__` en `scripts/`. Es una corrección menor: el
porcentaje final se mueve menos de un punto.

**5. El "10%" del encargo está bien, pero por otro motivo.** El encargo lo
plantea como "se midió una de cinco familias, o sea el 10% del problema". El
número sale igual (154 hooks registrados / 1440 = 10,7%) pero el hallazgo real es
más duro: de las **1151 primitivas no-hook restantes, exactamente 3 produjeron
alguna vez un evento de uso**. No es que las otras cuatro familias estén medidas
peor; es que tres de ellas no están medidas.

---

## 1. El mapa honesto por familia

Vocabulario, porque el encargo insiste con razón en la distinción:

- **Señal VIVA** — canal existe, productor registrado, escribió en los últimos días.
- **Señal MUERTA** — canal existe con productor implementado, pero el productor
  no está enganchado a nada; el archivo con filas viejas es residuo, no medición.
- **Señal INEXISTENTE** — no hay canal ni productor.
- **Señal INDIRECTA** — el canal identifica la primitiva pero mide un momento
  *anterior* al uso (que el router la propuso), no el uso.

### hooks — señal VIVA, la única de grado industrial

| | |
|---|---|
| Canal | `.cognitive-os/metrics/hook-timing.jsonl` + 7 archivos rotados en `.archive/` |
| Productor | `scripts/hook-timing-wrapper.sh`, envuelve 162 invocaciones en `.claude/settings.json` |
| Granularidad | por invocación: `hook`, `event`, `duration_ms`, `exit_code`, `skipped`, `session_kind` |
| Estado | VIVA — escribiendo ahora mismo |

El agujero de esta familia no es la señal, es el **denominador**: existen **289**
scripts `.sh` bajo `hooks/`, y sólo **154** están registrados. Los 135 restantes
son invocables (por scripts, por tests, a mano) y **ninguna de esas invocaciones
deja rastro**: el wrapper vive en la entrada de `settings.json`, no en el hook.
La familia mejor medida del OS tiene el 47% de sus archivos fuera de la medición.

### skills — señal VIVA, cobertura del 1,5%

| | |
|---|---|
| Canal principal | `skill-invocations.jsonl` (5 filas) y `skill-usage.jsonl` (5 filas) |
| Productores | `hooks/skill-invocation-logger.sh` y `hooks/skill-usage-tracker.sh` — ambos **registrados**, `PostToolUse` / `matcher: "Skill"` |
| Granularidad | `skill_name`, `session_id`, `duration_ms` |
| Estado | VIVA, con volumen incompatible con el uso real |

Tres skills distintos observados sobre 194. La causa es de diseño: el matcher es
la **herramienta `Skill`**. Un skill que el agente aplica leyendo su `SKILL.md`,
o que llega por el preámbulo, o por sugerencia del router aceptada en prosa, no
pasa por esa herramienta y por lo tanto **no existe para la medición**. La señal
mide un camino de invocación, no el uso del skill.

Dos canales adyacentes, ambos vivos, ambos midiendo otra cosa:

- `skill-suggestion.jsonl` — 467 filas, **49 skills distintos**, 48 con
  `threshold_met: true`. Productor `hooks/skill-router-prompt-suggest.sh`
  (registrado, 23 filas de timing hoy). Es la mejor cobertura nominal de la
  familia, pero mide *que el router propuso el skill*, no que se usó. **Señal
  indirecta.**
- `skill-metrics.jsonl` (250 filas) y `skill-feedback.jsonl` (195 filas) — vivos,
  escritos hoy, y **el campo `skill` no contiene un skill**: las últimas filas
  dicen `"skill":"unknown-agent"` y `"skill":"matias"`. Señal viva, no atribuible.
  Un contador que suma sin poder decir a qué. Peor que vacío, porque un tablero
  que lo lea reporta actividad.

### rules — señal MUERTA por un renglón faltante

| | |
|---|---|
| Canal | `.cognitive-os/metrics/contextual-rules.jsonl` — 33 filas, todas del 2026-08-15, con **nombres de regla** (`rules_injected`, `rules`) |
| Productor | `packages/context-optimization/hooks/contextual-rule-loader.sh` (symlink en `hooks/`), `PreToolUse` sobre `Agent`, inyecta hasta 3 reglas |
| Estado | **MUERTA**: `grep -c 'contextual-rule-loader' .claude/settings.json` → **0**, y 0 filas en las 225.628 de hook-timing |

Este es el hallazgo más barato del informe. El productor está escrito, testeado
(las 33 filas son de banco: `"prompt_preview":"Define acceptance criteria for the
new endpoint"`), emite exactamente el dato que hace falta —qué regla se cargó, en
respuesta a qué— y **no está enchufado**. Cuatro reglas distintas aparecen en esas
filas de prueba: `agent-quality`, `acceptance-criteria`, `auto-repair`,
`definition-of-done`.

El canal adyacente vivo es `rule-suggestion.jsonl`: 264 filas, productor
`hooks/rule-router-prompt-suggest.sh` (registrado, disparando), 80 filas con
`threshold_met`, **6 reglas distintas** nombradas (`adversarial-review` 47,
`trust-score` 43, `definition-of-done` 15, `acceptance-criteria` 2,
`eas-evidence-artifact` 2, `stash-quarantine` 2). Igual que con skills: mide la
sugerencia, no la carga. **Señal indirecta**, y de 6 sobre 131.

### scripts — señal INEXISTENTE, y es la familia más grande

| | |
|---|---|
| Canal | ninguno |
| Productor | ninguno |
| Inventario | **766** archivos únicos bajo `scripts/` (excluido `__pycache__`) — el **53%** del registry |

Busqué producto de telemetría con nombre `script-usage` / `script-invocation` /
`script-exec` en `hooks/`, `scripts/`, `cos_lib/`, `lib/`: cero coincidencias.
Ningún `.jsonl` de métricas tiene un esquema que nombre un script ejecutado.

Lo que hay son **rastros incidentales**, no señal:

- `aci-observations.jsonl` (8,1 MB) tiene 975 filas que mencionan `scripts/`,
  pero su payload es `output_excerpt` — el script aparece **sólo si él mismo
  imprime su ruta**. Sesgo de captura total: mide verbosidad, no ejecución.
- `git-op-blocks.jsonl`, `rm-op-blocks.jsonl`, `vcs-actions.jsonl` sí guardan el
  campo `command` verbatim, pero únicamente cuando la operación cayó en su
  dominio (git, `rm`). Un `scripts/foo.py` normal no pasa por ahí.

La mitad del registry es hoy **estructuralmente inobservable**.

### templates — señal INEXISTENTE

| | |
|---|---|
| Canal | ninguno |
| Productor | ninguno |
| Inventario | **60** archivos bajo `templates/` |

Los únicos consumidores en tiempo de ejecución son dos hooks registrados y
disparando: `hooks/subagent-context-injector.sh` (lee
`templates/agent-preamble.md` y `templates/agent-mandatory-rules.md`) y
`hooks/inject-phase-context.sh` (`agent-preamble.md`, `project-gotchas.md`).
Ninguno de los dos escribe una línea de métrica: `grep -nE 'metrics|jsonl'` sobre
ambos devuelve vacío. Tres templates tienen consumidor conocido; los otros 57 no
tienen ni consumidor ni señal.

---

## 2. Los números

Inventario por realpath único, contado hoy (§Evidencia, comando 1):

| Familia | Primitivas | Con señal posible | Con señal observada | Estado del canal |
|---|---:|---:|---:|---|
| hooks | 289 | 154 (los registrados) | **152** | VIVA |
| skills | 194 | 194 (canal genérico) | **3** | VIVA, cobertura 1,5% |
| rules | 131 | 131 (si se registra el loader) | **0** | MUERTA (productor sin registrar) |
| scripts | 766 | 0 | **0** | INEXISTENTE |
| templates | 60 | 0 | **0** | INEXISTENTE |
| **Total** | **1440** | **348** | **155** | |

Aclaración sobre "señal posible" en rules: es 131 *condicional a un renglón en
`settings.json`*. Hoy, sin ese renglón, la columna vale 0 y el total de señal
posible baja a 217 (15,1%).

Señales indirectas, que no entran en las columnas de arriba y por qué:

| Canal | Filas | Primitivas distintas | Qué mide realmente |
|---|---:|---:|---|
| `skill-suggestion.jsonl` | 467 | 49 skills | el router *propuso* el skill |
| `rule-suggestion.jsonl` | 264 | 6 rules | el router *propuso* la regla |
| `skill-metrics.jsonl` | 250 | 0 (campo corrupto) | nada atribuible |
| `skill-feedback.jsonl` | 195 | 0 (campo corrupto) | nada atribuible |

---

## 3. El veredicto de cobertura

> **El 10,8% del registry es observable en uso hoy** — 155 de 1440 primitivas
> produjeron alguna vez un evento que las nombre.
>
> **El 15,1% tiene canal capaz de nombrarlas** — 217 de 1440, si se cuenta el
> canal de skills como habilitado para las 194 (que lo está, aunque en tres
> semanas haya captado 3).
>
> **El 89,2% restante no es "poco usado": es inobservable.** Sobre 1285
> primitivas no se puede afirmar nada — ni que sirven ni que sobran.

Dicho sin suavizar: **la única familia con observabilidad real es la que ya se
había medido**. Las otras cuatro suman 1151 primitivas y 3 eventos de uso en la
historia registrada del OS. Y de esas cuatro, dos (scripts y templates, 826
primitivas, el 57% del registry) no tienen ni siquiera un canal donde el evento
podría aparecer.

El corolario incómodo, y es el motivo por el que este informe existe: **todo
juicio de utilidad emitido hasta hoy sobre una primitiva que no sea un hook
registrado se apoyó en cobertura de prueba o en reachability estática, no en
uso.** Son preguntas distintas. `scripts/primitive_usage_map.py` —que el propio
docstring aclara: *"static reachability map, not runtime coverage"*— responde
"quién la referencia", no "quién la ejecutó".

---

## 4. Propuestas, ordenadas por costo

Ninguna se construyó. Cada una nombra el evento a capturar y el punto de enganche
que **ya existe**.

### P1 — rules: un renglón en `settings.json`. Costo: mínimo.

Registrar `hooks/contextual-rule-loader.sh` como `PreToolUse` sobre `Agent`.
Evento: `{timestamp, rules_injected, rules, prompt_preview}` — el hook ya lo
emite a `contextual-rules.jsonl`, con nombres de regla. No hay que escribir
código: el productor está implementado, symlinkeado y probado.

Lleva rules de 0 a 131 con señal posible, y el registry de 15,1% a 24,2% de
canal. **Salvedad honesta:** el hook inyecta hasta 3 reglas por llamada y sólo
sobre `Agent`, así que la señal cubre carga contextual, no las "Always Active"
del `RULES-COMPACT`. Es cobertura parcial, pero es la única de la familia y sale
gratis.

Precaución antes de registrarlo: medir su latencia (el header declara objetivo
`< 100ms`) contra el presupuesto de `PreToolUse:Agent`, y confirmar con el
operador que el volumen de `contextual-rules.jsonl` entra en la rotación.

### P2 — scripts: reductor sobre transcripts. Costo: bajo, cero instrumentación.

**No hace falta capturar nada nuevo.** Los transcripts de Claude Code ya guardan
cada comando Bash verbatim: 22 archivos, 243 MB, ~1190 llamadas Bash sólo en el
más reciente. Un reductor read-only que extraiga `tool_input.command` y matchee
`scripts/<nombre>` produce un histograma de uso real de la familia de 766
primitivas, retroactivo hasta donde lleguen los transcripts.

Es la propuesta de mejor relación resultado/costo del informe: sin hook nuevo,
sin latencia en el camino caliente, sin tocar `settings.json`, y **retroactiva**
— las otras tres empiezan a medir desde el día que se activan.

Límites que hay que escribir junto al número: sólo ve invocaciones hechas por el
agente vía Bash (no cron, no CI, no ejecuciones manuales del operador en su
terminal), y los transcripts rotan igual que las métricas.

Alternativa si se quiere señal en vivo además de la retroactiva: **23 hooks ya
parsean `tool_input.command`** en `PreToolUse:Bash` (entre ellos
`control-plane-audit.sh`, `secret-detector.sh`, `error-learning.sh`, todos
registrados y disparando). Emitir una línea desde uno de ellos cuesta menos que
un hook nuevo, que pagaría registro + latencia en **cada** Bash. Cuál de los 23,
es decisión de dueño de archivo, no mía.

### P3 — templates: dos `echo` en hooks que ya disparan. Costo: bajo.

`hooks/subagent-context-injector.sh` y `hooks/inject-phase-context.sh` están
registrados, disparan, y **ya saben** qué template leyeron (`agent-preamble.md`,
`agent-mandatory-rules.md`, `project-gotchas.md`). Falta un append a un
`template-usage.jsonl` con `{timestamp, template, hook, session_kind}`.

Rinde poco por diseño y conviene decirlo antes de hacerlo: cubre 3 de 60. Su
valor no es medir esos 3 —que obviamente se usan— sino **volver explícito que los
otros 57 no tienen consumidor en runtime**, que es un insumo de reducción de
superficie, no de observabilidad.

### P4 — skills: ampliar el camino de captura. Costo: medio.

Es la única que pide diseño, no plomería. El canal existe y funciona; el problema
es que el matcher `Skill` ve un solo camino de invocación. Opciones, de menor a
mayor costo, **ninguna verificada por mí**:

1. Correlacionar `skill-suggestion.jsonl` (49 skills, `threshold_met`) con el
   turno siguiente para inferir aceptación. Barato, y es inferencia: hay que
   reportarlo como estimación, nunca como uso observado.
2. Emitir el evento desde el punto donde se **lee** un `SKILL.md`, no donde se
   invoca la herramienta. Cubre el camino real; requiere encontrar el enganche.
3. Arreglar la atribución de `skill-metrics.jsonl` / `skill-feedback.jsonl`.
   Costo bajo, pero **no crea observabilidad**: son canales de performance con el
   campo mal poblado. Va acá por higiene — hoy alimentan cualquier tablero con
   `"skill":"matias"`.

### Lo que este informe deliberadamente no propone

Instrumentar los 135 hooks no registrados. Su falta de señal es **consecuencia**
de no estar registrados, no causa. La pregunta previa —qué hacen ahí— es de
reducción de superficie, y contestarla al revés (instrumentar primero) fabrica
1440 líneas de telemetría para justificar 1440 primitivas.

---

## 5. Evidencia ejecutable

Read-only, deterministas, sin dependencia del estado de sesión. Se corren desde
la raíz del repo. No los dejé como script en `scripts/` a propósito: agregar una
primitiva al registry que estoy auditando cambiaría el denominador del propio
informe.

**1 — Inventario por familia (produce el 1440 de §2):**

```bash
.venv/bin/python - <<'PY'
import pathlib
root = pathlib.Path('.'); inv = {}
inv['hooks']     = len({p.resolve() for p in root.glob('hooks/**/*.sh')})
inv['rules']     = len({p.resolve() for p in root.glob('rules/**/*.md')})
inv['templates'] = len({p.resolve() for p in root.glob('templates/**/*') if p.is_file()})
sk = set()
for pat in ('skills/**/SKILL.md', 'packages/*/skills/**/SKILL.md'):
    sk |= {p.resolve() for p in root.glob(pat)}
inv['skills'] = len(sk)
inv['scripts'] = len({p.resolve() for p in root.glob('scripts/**/*')
                      if p.is_file() and '__pycache__' not in p.parts})
print(inv, 'TOTAL:', sum(inv.values()))
PY
```

**2 — Hooks registrados vs. disparados en TODAS las ventanas (produce 154 / 152 / 2):**

```bash
.venv/bin/python - <<'PY'
import json, gzip, glob, re, subprocess
M = '.cognitive-os/metrics'
reg = set(re.findall(r'/([a-z0-9._-]+)\.sh', subprocess.run(
    ['grep', '-oE', r'(hooks|packages/[a-z0-9-]+/hooks)/[a-z0-9._-]+\.sh',
     '.claude/settings.json'], capture_output=True, text=True).stdout))
fired, rows = set(), 0
for f in [f'{M}/hook-timing.jsonl'] + sorted(glob.glob(f'{M}/.archive/hook-timing-*.jsonl.gz')):
    op = gzip.open if f.endswith('.gz') else open
    with op(f, 'rt') as fh:
        for line in fh:
            line = line.strip()
            if not line: continue
            try: d = json.loads(line)
            except Exception: continue
            rows += 1
            if d.get('hook'): fired.add(d['hook'])
print('filas:', rows, '| registrados:', len(reg), '| disparados:', len(reg & fired))
print('nunca dispararon:', sorted(reg - fired))
print('disparan sin estar registrados:', len(fired - reg))
PY
```

**3 — Skills con uso observado (produce 3):**

```bash
.venv/bin/python - <<'PY'
import json, collections
c = collections.Counter()
for line in open('.cognitive-os/metrics/skill-invocations.jsonl'):
    line = line.strip()
    if line: c[json.loads(line)['payload']['skill_name']] += 1
print('skills distintos con uso observado:', len(c), dict(c))
PY
```

**4 — Productor de rules sin registrar (el hallazgo de P1):**

```bash
# 0 = no registrado. Usar `|| true`: grep -c devuelve exit 1 cuando cuenta 0.
grep -c 'contextual-rule-loader' .claude/settings.json || true
ls -la hooks/contextual-rule-loader.sh          # existe, es symlink
wc -l .cognitive-os/metrics/contextual-rules.jsonl   # 33 filas de banco
```

**5 — Ausencia de canal para scripts y templates:**

```bash
# vacío = no hay productor de telemetría de ejecución de scripts
grep -rlE 'script-(usage|invocation|exec)' --include='*.py' --include='*.sh' \
     hooks scripts cos_lib lib 2>/dev/null || true
# vacío = los inyectores de templates no escriben métrica
grep -nE 'metrics|jsonl' hooks/subagent-context-injector.sh \
     hooks/inject-phase-context.sh || true
```

**6 — Volumen de transcripts disponible para P2:**

```bash
P=$(ls -d ~/.claude/projects/*luum-agent-os* | head -1)
ls "$P"/*.jsonl | wc -l ; du -sm "$P"
ls -t "$P"/*.jsonl | head -1 | xargs grep -c '"Bash"'
```

---

## Lo que este informe no puede afirmar

- **Ninguna primitiva queda declarada inútil acá.** El resultado es que 1285 no
  son evaluables. Usar este informe para podar sería exactamente el error que
  denuncia.
- **`skill-suggestion` y `rule-suggestion` no se cruzaron contra aceptación
  real.** Los 49 skills y las 6 rules son "propuestos", y no medí cuántas
  propuestas se tomaron.
- **La ventana histórica termina donde termina la rotación.** Los 7 archivos
  `.gz` de hook-timing arrancan el 2026-07-20; lo anterior no está. "Nunca
  disparó" significa "no en lo que se conserva".
- **P2 y P4 no se probaron.** Que los transcripts contengan el comando lo
  verifiqué; que un reductor produzca atribución limpia (paths relativos, `cd`,
  heredocs, pipes) **no**. Es la incertidumbre más grande del informe y hay que
  prototipar antes de comprometer el número.
- **Los 5 hooks que disparan sin estar registrados no los identifiqué por
  nombre.** Los conté. Vale la pena mirarlos: o son renombrados, o hay una vía de
  invocación fuera de `settings.json` que también valdría para P2.

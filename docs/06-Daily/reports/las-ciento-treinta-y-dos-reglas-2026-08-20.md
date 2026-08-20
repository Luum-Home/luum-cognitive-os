<!-- SCOPE: os-only -->
# Las 132 reglas: quién las carga, y cuáles mienten

**Fecha:** 2026-08-20 · **HEAD auditado:** `bba24afba` · **Alcance:** `rules/*.md` (132 archivos)
**Instrumento:** `scripts/audit_rule_load_channels.py` (read-only, exit 0 sin hallazgos / 1 con hallazgos)

```bash
git rev-parse --short HEAD                       # bba24afba
git ls-files 'rules/*.md' | wc -l                # 132
.venv/bin/python3 scripts/audit_rule_load_channels.py   # exit 1
```

---

## Control positivo (antes de leer cualquier cero)

Mi primera sonda de "reglas enrutables" dio **0** — y era mentira. Las reglas
empiezan con `<!-- SCOPE: both -->` antes del `---`, y mi regex de frontmatter
exigía `---` en la primera línea. El cero era mi bug, no una ausencia.

Lo detecté porque el cero contradecía la telemetría: `rule-suggestion.jsonl`
mostraba a `adversarial-review` nombrada 78 veces por un enrutador que, según mi
sonda, no la conocía. Descarté la sonda y usé **el instrumento que ya cuenta**
en vez de reimplementarlo:

```bash
.venv/bin/python3 -c "
import sys; sys.path.insert(0,'.')
from cos_lib.rule_router import RuleRouter
r=RuleRouter()
for p in ['review this adversarially and produce findings with severity',
          'does this have acceptance criteria?',
          'what is the blast radius of this change']:
    print(repr(p[:45]),'->',[(m.rule_name,round(m.confidence,2))
                              for m in r.top_matches(p,n=3,min_confidence=0.70)])
"
```
```
'review this adversarially and produce finding' -> [('adversarial-review', 0.82)]
'does this have acceptance criteria?'           -> [('acceptance-criteria', 1.0)]
'what is the blast radius of this change'       -> []
```

Dos ramas distintas del contrafáctico: encuentra lo que existe, no encuentra lo
que no. La sonda sirve. El control quedó **cableado dentro del script** como un
`assert` — si algún día el enrutador deja de encontrar `acceptance-criteria`, el
script se cae en vez de publicar un cero falso.

---

## 1. El mecanismo de carga, corrido

`RULES-COMPACT.md` dice: *"Full rules loaded on trigger via `[ref-key]`"*. Fui a
buscar quién hace ese "loaded on trigger". Hay **cinco** canales candidatos y
solo dos están vivos.

| # | Canal | Mecanismo | ¿Corre? | Techo real |
|---|-------|-----------|---------|-----------|
| **A** | Proyección nativa del arnés | symlinks en `.claude/rules/cos/` | **SÍ, siempre** | **2** |
| **B** | `[ref-key]` de RULES-COMPACT | slash command `/rules-expand`, tipeado a mano | Solo si el operador lo tipea | 130 (manual) |
| **C** | `hooks/rule-router-prompt-suggest.sh` | UserPromptSubmit → `cos_lib/rule_router.py` | **SÍ** (415 corridas) | **7** |
| **D** | `hooks/contextual-rule-loader.sh` | `contextual_triggers` de `cognitive-os.yaml` | **NO — sin registrar** | 47 (inalcanzable) |
| **E** | `templates/agent-mandatory-rules.md` | inyección SubagentStart | **SÍ** | 9 (por nombre, sin cuerpo) |

### Canal A — el que de verdad siempre llega

```bash
ls -la .claude/rules/cos/
```
```
RULES-COMPACT.md -> ../../../rules/RULES-COMPACT.md
rate-limiting.md -> ../../../rules/rate-limiting.md
```

**Dos.** De 132. Y quien lo decide es `hooks/self-install.sh`:

```bash
sed -n '/^CORE_RULES=(/,/^)/p' hooks/self-install.sh
```
```
CORE_RULES=(
  "RULES-COMPACT.md"
  "rate-limiting.md"
)
```

Diez líneas más arriba, el comentario que justifica ese recorte:

> `# Only ~16 core rules are symlinked into .claude/rules/cos/ — NOT all 94.`
> `# The 16 core rules cover all essential always-active governance hooks and protocols.`

**Son 2, no 16. Y el universo es 132, no 94.** El comentario quedó tres
refactors atrás y sigue describiendo un recorte que ya no existe.

### Canal B — "loaded on trigger" es un slash command

```bash
grep -rn "rules-expand\|rules_expand" --include="*.sh" --include="*.py" --include="*.json" \
     hooks/ scripts/ cos_lib/ .claude/settings.json | wc -l
```
```
0
```

`/rules-expand` vive en `.claude/commands/rules-expand.md`. **Cero invocaciones
automáticas.** El "on trigger" del índice siempre-activo no es un trigger: es el
operador acordándose de tipear un comando. Si nadie lo tipea, las 130 reglas con
`[ref-key]` nunca se abren.

### Canal D — el hook que resolvería esto no está registrado

Ya había un instrumento para esto en el repo, de la auditoría del 19-08:

```bash
.venv/bin/python3 scripts/audit_contextual_rule_channel.py
```
```
  hook registered   : False
  CHANNEL CEILING   : 47 rules can ever be named
  unreachable       : 85 rules have no trigger
  replay corpus     : 381 real Agent prompts from 18 transcripts
```

Aun registrándolo, el techo es 47 — no 132. Las otras 85 no tienen trigger
declarado, así que ningún prompt las puede despertar.

---

## 2. Las tres cubetas

```bash
.venv/bin/python3 scripts/audit_rule_load_channels.py
```

| Cubeta | N | % |
|--------|---|---|
| ENRUTADA Y VIGENTE | 11 | 8,3% |
| **ENRUTADA PERO DESCRIBE ALGO QUE NO CORRE** | **2** | 1,5% |
| SIN VÍA DE CARGA | **119** | 90,2% |

Las 2 de la cubeta del medio son, exactamente, **las 2 que se cargan siempre**:
`RULES-COMPACT.md` (§3.1) y `rate-limiting.md` (§3.3). O sea: el 100% del
contexto siempre-activo de esta capa está en la cubeta que miente o que
documenta algo muerto.

Y de las 13 con vía de carga, **solo 6 fueron nombradas alguna vez** en 411
filas de telemetría real:

```bash
.venv/bin/python3 -c "
import json,collections
c=collections.Counter()
for ln in open('.cognitive-os/metrics/rule-suggestion.jsonl'):
    if ln.strip():
        for m in json.loads(ln).get('matches',[]):
            if m.get('confidence',0)>=0.80: c[m['rule']]+=1
[print(f'{v:5d}  {k}') for k,v in c.most_common()]"
```
```
   78  adversarial-review
   62  trust-score
   28  definition-of-done
    3  acceptance-criteria
    3  eas-evidence-artifact
    2  stash-quarantine
```

126 de 132 reglas nunca fueron nombradas por el único enrutador que corre.

---

## 3. CUBETA 2 — enrutada, leída, y falsa

Esta es la que hace daño, y el patrón es peor de lo que anticipaba el encargo.
No es solo que una regla describa un mecanismo muerto. Es que **la excusa para
NO cargar una regla es que "un hook la aplica" — y el hook no aplica nada.**

### 3.1 El índice siempre-activo declara enforcement que no existe

`RULES-COMPACT.md` es una de las dos reglas que entran en **todas** las sesiones.
Ocho veces dice "hook-enforced". Corrí el instrumento de vitalidad contra cada
hook nombrado:

```bash
.venv/bin/python3 scripts/hook_vitality_audit.py --json   # 337.328 filas, 11 archivos de telemetría
```

| Afirmación en el índice siempre-activo | Hook | runs | blocks | ¿Puede bloquear? | Veredicto |
|---|---|---:|---:|---|---|
| "Consequence **hook-enforced**" | `consequence-evaluator` | 275 | 0 | **NO — sin ruta de bloqueo** | **FALSA** |
| "Auto-rollback **hook-enforced**" | `auto-rollback-trigger` | 275 | 0 | **NO** | **FALSA** |
| "Audit trail **hook-enforced**" | `git-context-capture` + `session-changelog` | 399 | 0 | **NO** | **FALSA** |
| "Clarification gate hook-enforced" | `clarification-gate` | 277 | 0 | sí, nunca probado | no probada |
| "Confidence gate hook-enforced" | `confidence-gate` | 275 | 0 | sí, nunca probado | no probada |
| "Blast radius hook-enforced" | `blast-radius` | 277 | 0 | sí, nunca probado | no probada |
| "Scope proportionality hook-enforced" | `scope-proportionality` | 275 | 0 | sí, nunca probado | no probada |
| "Content policy + confidentiality hook-enforced" | `confidentiality-enforcer` | 1263 | **11** | **sí, PROBADO** | **verdadera** |
| ↳ misma frase, otra mitad | `content-policy` | 1263 | 0 | sí, nunca probado | no probada |

**Tres de ocho son categóricamente falsas**: el hook citado no tiene ninguna ruta
de bloqueo en su código. Son observadores. Corren, escriben una línea, salen 0.
Exactamente el patrón que el encargo describía para la familia HOOKS
—"1.292 corridas imprimiendo una advertencia y saliendo 0"— pero acá lo grave es
que un agente lee "hook-enforced" en la regla siempre-activa y ajusta su
comportamiento creyendo que hay una red abajo.

Una sola de las ocho tiene capacidad de bloqueo **demostrada** (11 bloqueos
reales en 1.263 corridas).

### 3.2 El agujero doble: excluidas por un enforcement que no existe

`hooks/self-install.sh` tiene un bloque `EXCLUDED_RULES` cuya sección A se titula
*"Hook-enforced (hook is the active enforcement layer)"*. Esas reglas se excluyen
de la proyección **porque supuestamente un hook las aplica**. Crucé las 20 con la
telemetría:

```bash
# reproducible: sección §3.2 de scripts/audit_rule_load_channels.py + hook_vitality_audit.py --json
```

| Regla excluida "porque hay hook" | Hook citado | runs | ¿ruta de bloqueo? |
|---|---|---:|---|
| `consequence-system.md` | `consequence-evaluator` | 275 | **NO** |
| `auto-rollback.md` | `auto-rollback-trigger` | 275 | **NO** |
| `assumption-tracking.md` | `assumption-tracker` | 275 | **NO** |
| `prompt-quality.md` | `prompt-quality-llm` | 277 | **NO** |
| `skill-rewrite.md` | `completion-gate` | 275 | **NO** |
| `auto-skill-generation.md` | `auto-skill-generator` | 275 | **NO** |
| `auto-repair.md` | `auto-repair-dispatcher` | 275 | **NO** |
| `audit-trail.md` | `git-context-capture`, `session-changelog` | 399 | **NO** |
| `crash-recovery.md` | `auto-checkpoint`, `crash-recovery` | 13387 / 55 | **NO** |
| `pre-commit-gate.md` | `pre-commit-gate` (git hook) | — | **no aparece en vitalidad** |

**Diez reglas** están fuera del contexto del agente con la justificación escrita
de que un hook las hace cumplir, y el hook solo mira. Ni la regla llega, ni el
hook obliga. Es el peor de los dos mundos y está documentado como si fuera una
optimización.

`auto-checkpoint` es el caso más elocuente: **13.387 corridas, 0 bloqueos, sin
ruta de bloqueo en el código**. Es el hook del que hablaba el encargo, con otro
nombre.

### 3.3 `rate-limiting.md` — el testigo, ya corregido

El caso que motivó el encargo. Confirmado y, para ser justos, **ya desmentido en
el propio archivo**: arriba de todo lleva desde el 15-08 el bloque *"Estado real,
verificado: el limitador NO está activo"*.

```bash
grep -c 'rate-limiter' .claude/settings.json     # 0
.venv/bin/python3 -c "
import json; d=json.load(open('/tmp/vit.json'))
print([h['runs'] for h in d['hooks'] if h['hook']=='rate-limiter'] or 'ausente')"
```

Ya no miente. Pero sigue siendo **una de las dos únicas reglas que entran en cada
sesión** (4.572 bytes), y lo que describe es una lápida. De los 16.970 bytes de
contexto siempre-activo que gasta esta capa, el 27% documenta un control muerto.

**Contra la premisa del encargo:** `rate-limiting.md` no es representativo. Es el
único archivo que se autocorrigió. El problema real no está en las reglas que se
cargan: está en la **prosa de enrutamiento** (`RULES-COMPACT.md` §2/§5/§6/§7/§10
y `EXCLUDED_RULES`), que afirma enforcement inexistente y usa esa afirmación
para excluir reglas.

---

## 4. Ref-keys que no resuelven

`RULES-COMPACT.md` contiene 141 `[ref-key]` distintos. **11 no apuntan a ningún
`rules/*.md`:**

| ref-key | ¿regla? | ¿skill? |
|---|---|---|
| `component-reality-check` | no | sí (`skills/`) |
| `cost-predictor` | no | sí (`skills/`) |
| `dogfood-score` | no | sí (`skills/`) |
| `cognitive-os-changes` | no | no |
| `component-classification` | no | no |
| `dogfooding` | no | no |
| `ecosystem-tools` | no | no |
| `library-selection` | no | no |
| `os-vs-project` | no | no |
| `plan-first` | no | no |
| `stash-mutation-reversibility` | no | no |

Tres son skills disfrazadas de reglas (la notación `[ref-key]` está definida
como "regla a cargar"; ahí no hay nada que cargar). **Ocho no son nada**:
`/rules-expand` con cualquiera de esas ocho no puede devolver un archivo.

Peor: **siete de ellas figuran en la lista `EXCLUDED_RULES` del instalador**, con
su comentario justificando la exclusion ("contextual: load on demand",
"reference doc, not behavioral") escrito sobre un archivo que no existe. De las
102 entradas de esa lista, 7 son fantasmas:

```bash
.venv/bin/python3 -c "
import re, os
src = open('hooks/self-install.sh').read()
blk = re.search(r'EXCLUDED_RULES=\((.*?)\n\)', src, re.S).group(1)
ex  = set(re.findall(r'\"([a-z0-9-]+)\.md\"', blk))
missing = sorted(e for e in ex if not os.path.isfile('rules/' + e + '.md'))
print(len(ex), 'entradas;', len(missing), 'sin archivo:', missing)"
```
```
102 entradas; 7 sin archivo: ['cognitive-os-changes', 'component-classification',
 'dogfooding', 'ecosystem-tools', 'library-selection', 'os-vs-project', 'plan-first']
```

Una lista de exclusion que excluye fantasmas es el mismo bug que un supresor que
no suprime nada: da sensacion de decision tomada donde no hay nada que decidir.

En el otro sentido: solo 2 de las 132 reglas no tienen ref-key
(`ROADMAP.md` y `RULES-COMPACT.md` misma, ambas correctas — no son reglas de
comportamiento).

---

## 5. Cubeta 1 — las que sí funcionan (11)

| Regla | Canales vivos | Veces nombrada |
|---|---|---:|
| `adversarial-review` | router + subagent-tmpl | 78 |
| `trust-score` | router + subagent-tmpl | 62 |
| `definition-of-done` | router + subagent-tmpl | 28 |
| `acceptance-criteria` | router + subagent-tmpl | 3 |
| `eas-evidence-artifact` | router | 3 |
| `stash-quarantine` | router | 2 |
| `phase-aware-agents` | router + subagent-tmpl | 0 |
| `agent-output-reading` | subagent-tmpl | 0 |
| `agent-quality` | subagent-tmpl | 0 |
| `model-directive` | subagent-tmpl | 0 |
| `responsiveness` | subagent-tmpl | 0 |

Nota honesta: `templates/agent-mandatory-rules.md` nombra 9 reglas pero **no
inyecta su cuerpo** — le pasa al sub-agente un resumen de una línea y el nombre
del archivo. Y ese template es explícito y correcto al respecto: *"No hook
enforces these for you."* Es la pieza más honesta de toda la capa.

---

## 6. Qué haría, en orden

1. **Arreglar las tres afirmaciones falsas de `RULES-COMPACT.md`** (consequence,
   auto-rollback, audit-trail): decir "hook-observed" en vez de "hook-enforced".
   Es la regla siempre-activa; la mentira se paga en cada sesión. Costo: 3 líneas.
2. **Decidir las 10 reglas excluidas por enforcement inexistente** (§3.2): o el
   hook gana ruta de bloqueo, o la regla vuelve a la proyección, o se acepta por
   escrito que ese comportamiento no está gobernado. Hoy es un gap silencioso.
3. **Los 11 ref-keys colgados**: apuntarlos a la skill o borrarlos del índice.
   Y las **7 entradas fantasma de `EXCLUDED_RULES`** (§4): borrar la entrada,
   o recrear la regla si la exclusión describía algo que se quiere gobernar.
4. **`self-install.sh:291`**: el comentario dice "~16 core rules ... NOT all 94".
   Son 2 y 132. Es deuda de documentation-truth, candidata a
   `manifests/documentation-truth-claims.yaml`.
5. **La pregunta de fondo, que no es mía**: si 119 de 132 reglas no tienen vía de
   carga y 126 nunca fueron nombradas, la capa no es "132 reglas". Es **13
   reglas con canal y 6 con uso demostrado**, más 119 archivos de referencia.
   El tercio que sobrevive ya está elegido de hecho; falta que esté elegido a
   propósito.

---

## Correcciones a las premisas del encargo

1. **"132 reglas sin nada equivalente al instrumento de vitalidad de hooks"** —
   parcialmente falso. `scripts/audit_contextual_rule_channel.py` ya existía en
   el repo (auditoría del 19-08) y mide exactamente el canal D, con replay de 381
   prompts reales. No cubre los canales A/B/C/E, pero la familia no estaba a
   cero: estaba a un canal de cinco.

2. **"`rate-limiting.md` es el testigo de reglas que documentan mecanismos
   muertos"** — el caso es real pero **no es representativo, y ya está
   corregido**. El archivo lleva desde el 15-08 un bloque que desmiente su propio
   contenido. Es el único que se autocorrigió. Si se buscan más como él en el
   cuerpo de las reglas, no aparecen; el problema equivalente está en la **prosa
   de enrutamiento** (§3.1, §3.2), que es peor porque está en el archivo
   siempre-activo.

3. **"La cubeta 2 es la que más importa porque una regla inalcanzable no hace
   daño"** — el corolario no se sostiene del todo. En §3.2 encontré 10 reglas
   inalcanzables **cuya inalcanzabilidad está justificada por una afirmación
   falsa**. La regla no llega Y el hook no obliga, pero el sistema está escrito
   como si una de las dos cosas pasara. Una regla inalcanzable con una excusa
   falsa sí hace daño: cierra la pregunta.

4. **"averiguá qué hook las carga"** — el canal que más carga no es un hook. Es
   la proyección nativa del arnés (`.claude/rules/cos/`), que Claude Code lee
   solo, sin hook alguno. Buscar únicamente entre hooks se habría perdido el
   único canal siempre-activo.

5. **`.cognitive-os/metrics/` tiene 136 archivos, no 125** (`ls .cognitive-os/metrics/ | wc -l`).
   Tres registran algo de reglas: `rule-suggestion.jsonl` (411 filas, útil),
   `contextual-rules.jsonl` (39 filas, **0 reglas nombradas** — el hook no está
   registrado) y `rule-frontmatter-warnings.jsonl`.

6. **Mi propia sonda dio un cero falso** (canal C = 0) y lo reporto porque es el
   mismo error que el encargo advertía: el frontmatter arranca después de un
   comentario HTML. Lo detecté por contradicción con la telemetría, no por
   revisar el regex. Sin esas 411 filas, habría publicado "ninguna regla es
   enrutable".

7. **Un guard bloqueó un comando read-only.** `hooks/protected-config-write-guard.sh`
   abortó un `[ -f rules/$k.md ]` (un test de existencia) por contener la cadena
   `rules/`. No activé el bypass; reescribí en Python. Es un falso positivo del
   guard sobre lecturas, vale como hallazgo aparte.

---

## Lo que NO verifiqué

- No corrí `/rules-expand` para comprobar que expande bien los 130 ref-keys que
  sí resuelven. Verifiqué que **nada lo invoca automáticamente**, que es la
  pregunta que importaba.
- El bucket `unproven-guard` (35 hooks) significa "tiene ruta de bloqueo, nunca
  se lo vio bloquear". No distingue "nunca hizo falta" de "está roto". Para las
  4 afirmaciones "no probadas" de §3.1 haría falta un test de disparo con payload
  real; no lo hice.
- No audité `packages/*/rules/`, solo `rules/*.md`.

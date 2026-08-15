# Juez interno — aprendizaje persistente (2026-08-15)

> Qué construyó este repo para que un agente conserve lo que se le enseña entre
> sesiones, cuánto de eso está vivo, y qué conserva realmente. Medición interna,
> disjunta de la investigación del estado del arte externo.

Criterio: ADR-342. Para esta familia la pregunta 4 se lee **"¿se la vio conservar
algo que después se usó?"**, y se contesta en sus dos puntas: cuánto se guardó y
cuánto se recuperó.

Todos los números llevan el comando que los produjo. Todo se midió en read-only;
no se borró, desregistró ni refactorizó nada.

---

## 0. Veredicto en una línea

La capa de escritura existe, funciona y es grande: **17.417 observaciones** en la
base de Engram, 619 de ellas en agosto. La capa de recuperación **no tiene
ninguna evidencia propia**: el único ledger que registraría una lectura no existe
como archivo, el cristalizador corrió 371 veces y produjo **0 dígestos en las 371**,
y de los ledgers de aprendizaje derivados **ninguno tiene un consumidor que se lo
haya visto consumir**. Y lo viejo no se trata: **0 observaciones con `expires_at`,
0 borradas, y sólo 40 de 17.417 caen bajo una política de vejez que efectivamente
avisa**.

Bajo ADR-342: Engram pasa 1–3 y pasa la punta de escritura de la 4; **falla la
punta de lectura de la 4**. Los derivados (cristalizador, síntesis de skills, bucle
de reparación) fallan la 4 entera.

---

## 1. Censo de piezas

Enumerado sin filtros de extensión, como pide el encargo:

```bash
git grep -l -iE 'learning_pipeline|error-learning|skill_synthesizer|engram_crystallizer|engram_lifecycle|session-learnings|prompt-capture' -- . \
  | grep -v '^docs/' | grep -v '\.pyc' | wc -l     # → 196 archivos
```

La lista del encargo (7 familias) es **más chica que la realidad**. Piezas de la
familia que el encargo no nombró y que están registradas y corriendo:

| Pieza | Evento | En `.claude/settings.json` |
|---|---|---|
| `hooks/engram-daemon-launcher.sh` | SessionStart | sí |
| `hooks/engram-reinforce-on-access.sh` | PostToolUse `mem_search\|mem_get_observation` | sí (línea 704) |
| `hooks/engram-crystallize-on-session-end.sh` | Stop | sí |
| `hooks/engram-obsidian-export-on-stop.sh` | Stop | sí |
| `hooks/memory-prefetch.sh` | — | perfil `default` del boundary |
| `hooks/error-pipeline.sh`, `hooks/error-pattern-detector.sh`, `hooks/auto-repair-dispatcher.sh` | PostToolUse / PreToolUse | sí |
| `hooks/session-knowledge-extractor.sh`, `hooks/conversation-capture.sh` | — | **no registradas** |
| `hooks/engram-auto-sync.sh`, `hooks/engram-auto-import.sh` | — | **no registradas** |

```bash
python3 - <<'EOF'   # registro real, por evento y matcher
import json; s=json.load(open('.claude/settings.json'))
for ev,arr in s.get('hooks',{}).items():
    for g in arr:
        for h in g.get('hooks',[]):
            c=h.get('command','')
            if any(k in c for k in ['engram','error-learning','session-learning','user-prompt-capture','skill-synthesis','error-pipeline','error-pattern','auto-repair-dispatcher']):
                print(ev, repr(g.get('matcher','')), c.split('/')[-1])
EOF
```

---

## 2. Pregunta 1 — qué conserva cada pieza, y quién la lee

### 2.1 Engram (la pieza más usada)

Base: `~/.engram/engram.db`, 150 MB + 10 MB de WAL. Se midió con `sqlite3
"file:engram.db?mode=ro"` (read-only, sin tocar el WAL de sesiones activas).

```bash
cd ~/.engram && sqlite3 "file:engram.db?mode=ro" "
select 'total_obs',count(*) from observations;
select 'deleted',count(*) from observations where deleted_at is not null;
select 'has_expires',count(*) from observations where expires_at is not null;
select 'has_review_after',count(*) from observations where review_after is not null;
select 'review_overdue',count(*) from observations where review_after<datetime('now') and deleted_at is null;
select 'has_topic_key',count(*) from observations where topic_key is not null and topic_key<>'';
select 'revised_gt1',count(*) from observations where revision_count>1;
select 'sessions',count(*) from sessions;
select 'sessions_with_summary',count(*) from sessions where summary is not null and summary<>'';
select 'user_prompts',count(*) from user_prompts;
select 'relations',count(*) from memory_relations;"
```

| Métrica | Valor |
|---|---|
| Observaciones totales | **17.417** |
| Borradas (`deleted_at`) | **0** |
| Con `expires_at` | **0** |
| Con `review_after` | 928 (9 vencidas) |
| Con `topic_key` (upsert por tema) | 6.005 |
| Con `revision_count > 1` | 724 |
| Sesiones | 20.831 |
| Sesiones con `summary` | **1.144 (5,5 %)** |
| Prompts de usuario | 1.719 |
| Relaciones entre memorias | 240 |

Escritura por mes (`select substr(created_at,1,7),count(*) from observations group by 1 order by 1 desc`):
ago-2026 **619**, jul **1.146**, jun **4.820**, may **7.450**. Está viva y en baja.

**Quién lee.** Ésta es la punta que falta. La única instrumentación de lectura que
el repo construyó es `hooks/engram-reinforce-on-access.sh`, registrado en
`PostToolUse` con el matcher correcto
(`mcp__plugin_engram_engram__mem_search|mcp__plugin_engram_engram__mem_get_observation`,
`.claude/settings.json:704`), que debe escribir
`.cognitive-os/metrics/lifecycle-reinforcement.jsonl`.

```bash
ls -la .cognitive-os/metrics/lifecycle-reinforcement.jsonl
# ls: No such file or directory
ls .cognitive-os/metrics/.archive/ | grep -c lifecycle-reinforcement   # → 0
```

**El archivo no existe, ni vivo ni archivado.** Cero refuerzos registrados en
toda la historia. La punta de lectura de Engram no tiene evidencia propia.

El esquema tampoco la tiene: `PRAGMA table_info(observations)` no expone
`access_count` ni `last_accessed`. `last_seen_at` está poblado en 17.412 filas y
906 son posteriores a `created_at`, pero eso lo mueve el upsert de escritura
(dedupe / `revision_count`), no una lectura — no sirve como prueba de recuperación.

### 2.2 Trampa de medición encontrada (y evitada)

El camino obvio para medir lecturas es el ledger de trayectoria. **Da un número
falso.**

```bash
cd .cognitive-os/metrics/.archive && for g in agent-trajectory-*.gz; do
  echo -n "$g "; gzcat "$g" | python3 -c "
import sys,json; ts=[];ms=[]
for l in sys.stdin:
    d=json.loads(l); ts.append(d.get('timestamp',''))
    if 'mem_save' in str(d.get('tool','')): ms.append(d['timestamp'])
print('ventana',ts[0][:10],'->',ts[-1][:10],'| mem_save',len(ms))"; done
```

| Archivo | Ventana | `mem_save` en el ledger | Escrituras reales en la DB |
|---|---|---|---|
| `agent-trajectory-20260719…gz` | 2026-05-18 → 07-06 | 75 | — |
| `agent-trajectory-20260815-022842.gz` | 07-06 → 07-19 | 65 | — |
| `agent-trajectory-20260815-171840.gz` | **07-19 → 08-15** | **0** | **1.146 (jul) + 619 (ago)** |

El ledger dice cero escrituras en 27 días mientras la base recibió más de mil.
**`agent-trajectory.jsonl` no es un censo válido de uso de Engram** — captura sólo
lo que pasa por el hilo instrumentado, no las sesiones de sub-agentes. Cualquier
veredicto de "Engram está muerto" derivado de ahí es un artefacto de medición.

Peor: el mismo ledger tiene un campo fantasma de la clase que ADR-342 §pregunta 3
describe.

```bash
python3 -c "
import json,collections; c=collections.Counter();e=collections.Counter()
for l in open('.cognitive-os/metrics/agent-trajectory.jsonl'):
    d=json.loads(l); c[d.get('status')]+=1; e[d.get('exit_code')]+=1
print(c,e)"
# status: {'success': 3184}   exit_code: {0: 3184}
```

3.184 de 3.184 filas dicen `success`/`exit_code=0`, incluidas corridas que
fallaron. El campo existe, siempre trae el mismo valor y su ausencia es
invisible: es un `// default` que es una lectura legal. **Hallazgo colateral: el
ledger de trayectoria no puede usarse para medir fallas.**

La única cifra de dos puntas que sobrevive es la de mayo–julio, y hay que citarla
con la advertencia de arriba: **140 `mem_save` contra 54 `mem_search` y 1
`mem_context`** en 9.725 filas de trayectoria — ratio lectura/escritura 0,39. Es
la mejor evidencia de que la recuperación existió alguna vez; el último
`mem_search` registrado es del **2026-07-18**.

### 2.3 El resto de las piezas

| Pieza | Escribe | Filas hoy | Quién lo lee | ¿Se lo vio leer? |
|---|---|---|---|---|
| `hooks/error-learning.sh` | `.cognitive-os/metrics/error-learning.jsonl` | **11** (6 el 07-19, 3 el 07-20, **2 hoy** tras el arreglo `12b63c6c2`) | `bin/cos-errors`, `error_insights.py`, `consumer_improvement_proposals.py`, `feedback_consumer.py`, `kpi_collector.py`, `learning_pipeline.py`, `self_improvement.py`, `singularity.py` | **no** — ver §4 |
| `cos_lib/evolve_task_queue.py` | `.cognitive-os/error-learning.jsonl` (**otro archivo, mismo nombre**) | **102** | nadie | **no** |
| `hooks/session-learning.sh` | `session-learnings.jsonl` | **369** (última hoy) | `self_improvement.py`, `governed_self_improvement.py` | **no** — `.cognitive-os/improvement-runs/` tiene 0 entradas |
| `hooks/user-prompt-capture.sh` | `prompt-captures.jsonl` | **147** (45 hoy) | `feedback_consumer.py`, `project_profile_bootstrap.py`, `cos-doctor-memory-lifecycle.sh` | no medido; en paralelo Engram tiene 1.719 prompts propios |
| `hooks/skill-synthesis-scanner.sh` | `skill-synthesis-queue.jsonl` | **3** | **sólo su propio escritor** (`git grep -ln skill-synthesis-queue -- cos_lib/ scripts/ hooks/ bin/` → 1 archivo, el hook) | **no hay consumidor** |
| `hooks/engram-crystallize-on-session-end.sh` | `crystallization-events.jsonl` | **371** (126 hoy) | su escritor + `cos-doctor-memory-lifecycle.sh` | ver §3 |
| pipeline de reparación | `repair-dispatch.jsonl` / `repair-outcomes.jsonl` | **0 / 0** | — | 1 sola fila histórica, ver §4 |
| `hooks/skill-*` (drift/routing) | `skill-drift.jsonl` | 2.645 | — | emisión, no recepción |

Comandos: `wc -l < .cognitive-os/metrics/<f>.jsonl` para cada uno;
`git grep -ln '<archivo>' -- cos_lib/ scripts/ hooks/ bin/ cmd/ packages/` para los lectores.

**Colisión de nombres, hallazgo no anticipado por el encargo.** Hay dos ledgers
llamados `error-learning.jsonl` con esquemas distintos:

```bash
wc -l .cognitive-os/error-learning.jsonl              # 102  ← escribe evolve_task_queue.py
wc -l .cognitive-os/metrics/error-learning.jsonl      #  11  ← escribe hooks/error-learning.sh
```

Todos los lectores apuntan al de `metrics/` (11 filas). El de 102 filas —el que
tiene datos— no lo clasifica nadie. El aprendizaje de errores se partió en dos por
un nombre repetido: el archivo con contenido no tiene lector, el archivo con
lector casi no tiene contenido.

---

## 3. Pregunta 2 — cómo se trata lo viejo o lo falso

**Ésta es la falla central, y es del mismo tipo que las 54 páginas de síntesis con
cifras vencidas: lo guardado no envejece, y lo que se lee no sabe que envejeció.**

### 3.1 Nada expira, nada se borra

```bash
cd ~/.engram && sqlite3 "file:engram.db?mode=ro" \
 "select count(*) from observations where expires_at is not null;
  select count(*) from observations where deleted_at is not null;"
# 0
# 0
```

Cero observaciones tienen fecha de vencimiento. Cero fueron borradas alguna vez.
La base sólo crece.

### 3.2 La política de vejez gobierna el 0,23 % de la memoria

`rules/memory-governance.md` (ADR-261) declara seis tipos gobernados con umbral de
vejez. El resto cae a un no-op explícito. Contra la población real:

```bash
cd ~/.engram && sqlite3 "file:engram.db?mode=ro" \
 "select type,count(*) from observations group by type order by 2 desc limit 12;"
```

| Tipo | Filas | ¿Gobernado por ADR-261? | Política de vejez |
|---|---|---|---|
| `passive` | 6.062 | no | ninguna |
| `session_summary` | 3.952 | no | ninguna |
| `architecture` | 2.246 | no | ninguna |
| `decision` | 1.479 | **sí** | `never` — nunca vence por diseño |
| `discovery` | 1.406 | no | ninguna |
| `bugfix` | 832 | no | ninguna |
| `config` / `manual` / `pattern` | 1.255 | no | ninguna |
| `preference` | **40** | **sí** | `soft` (avisa, no suprime) |
| `fact`, `identity`, `procedure`, `blocker` | **0** | sí | irrelevante: no existen |

Población gobernada: 1.519 / 17.417 = **8,7 %**, y el 97 % de esa fracción es
`decision`, cuya política es *nunca vencer*. Los tipos con vejez `hard` —los
únicos que suprimen un resultado rancio del ranking— son `fact` y `blocker`, y
**tienen cero filas**. La vejez efectivamente aplicable cubre **40 observaciones
(0,23 %)** y sólo emite una advertencia.

No es un bug de implementación: la tabla de políticas está bien escrita y testeada
(`tests/unit/test_memory_governance.py`). Es que **el vocabulario de tipos que la
política gobierna no es el vocabulario de tipos que el sistema escribe**.

### 3.3 La política no llega al camino de lectura real

```bash
git grep -n 'memory_governance' -- . | grep -v '\.pyc' | grep -v '^docs/' | grep -v '^tests/'
# cos_lib/engram_lifecycle.py:51
# cos_lib/memory_retriever.py:22
# (+ rules/memory-governance.md, manifests/spdx-grandfather.txt)
```

`assess_freshness` se consume desde `cos_lib/memory_retriever.py`, y
`memory_retriever` se instancia sólo en `mcp-server/cos_mcp.py:176`. Pero la
herramienta que los agentes efectivamente llaman es
`mcp__plugin_engram_engram__mem_search` — el servidor MCP de Engram, externo al
repo, que no pasa por `cos_lib`. **La gobernanza de frescura no toca el recall que
usan los agentes.** Está aplicada en un retriever paralelo, no en el que se usa.

### 3.4 El cristalizador corre y no cristaliza nada

```bash
python3 -c "
import json,collections; c=collections.Counter()
for l in open('.cognitive-os/metrics/crystallization-events.jsonl'):
    c[json.loads(l).get('digests_created')]+=1
print(c)"
# Counter({0: 371})
```

371 corridas, **371 con `digests_created: 0`**, 126 de ellas hoy. El hook está
registrado en `Stop`, se dispara en cada cierre de sesión, y nunca produjo un
dígesto. Es el caso puro de ADR-342 §pregunta 4: hay ejecución, no hay decisión.
Y no es la firma de un truncado deliberado —el `.archive` no tiene ningún
`crystallization-events-*.gz`—: simplemente nunca produjo salida.

### 3.5 Qué pasa cuando algo guardado resulta falso

Nada automático. Los mecanismos que existen son:

- `mem_judge` + el envelope `judgment_required` del MCP, que resuelve conflictos
  **en el momento de escribir**, no después. `memory_relations` tiene 240 filas
  sobre 17.417 observaciones (1,4 %): la relación `supersedes` existe, se usa poco.
- `revision_count > 1` en 724 filas y `topic_key` en 6.005: el upsert por tema
  sobrescribe la versión vieja. Es el único mecanismo real de corrección, y
  depende de que quien escribe acierte el `topic_key`.
- `review_after` en 928 filas, 9 vencidas — pero nada consume esa fecha en el
  camino de lectura vivo (§3.3), así que vencer no tiene consecuencia.

Conclusión de la pregunta 2: **una afirmación guardada en 2026-05 y falsificada en
2026-08 sigue siendo recuperable, sin marca, con el mismo ranking**, salvo que
alguien la sobrescriba a mano por `topic_key`. Es exactamente el patrón de las
páginas de síntesis que heredan cifras vencidas, con el agravante de que acá no hay
fuente al lado para comparar.

---

## 4. Pregunta 4 en sus dos puntas — el bucle completo

Un solo bucle de aprendizaje del repo cerró alguna vez de punta a punta, y se
puede exhibir:

```bash
gzcat .cognitive-os/metrics/.archive/repair-outcomes-20260815-022843.jsonl.gz
# {"timestamp":"2026-07-20T17:28:25","repair_id":"11c7711d","error_type":"SCRIPT_ERROR",
#  "service":"consumer-svc","success":false,"reason":"Fix command failed inside worktree",
#  "fix_applied":"Make script executable","diff_length":0}
```

Una fila, del 2026-07-20, `success: false`. `repair-dispatch.jsonl` y
`repair-outcomes.jsonl` vivos tienen **0 filas**. La cadena
error → clasificación → propuesta → reparación → resultado se ejecutó **una vez en
toda la historia del repo y falló**.

Verificación de que el vacío no es un truncado (la trampa que el encargo advierte):
`ls .cognitive-os/metrics/.archive/ | grep repair` devuelve un único `.gz`, de una
fila. No hay histórico escondido.

Para la punta de escritura sí hay respuesta afirmativa y fuerte: 17.417
observaciones, 619 en agosto, 23 hoy
(`select coalesce(project,'(null)'),count(*) from observations where created_at>='2026-08-15' group by 1`
→ `luum-cognitive-os` 13, `luum-ssm` 5, null 4, `a` 1 — nótese el proyecto
llamado `a`, escritura con clave de proyecto basura).

---

## 5. Pregunta 3 — ¿viaja al consumidor?

El manifiesto declara su propia regla:

> `manifests/primitive-install-boundary.yaml` → `purpose`: *"Default/core may
> project only primitives listed here with distribution core; maintainer/lab
> remains opt-in"*.

Contrastado contra `.ai/primitives/*/*.json` (campo `lifecycle.distribution`):

```bash
python3 - <<'EOF'
import yaml,json,glob,collections
b=yaml.safe_load(open('manifests/primitive-install-boundary.yaml'))
d=b['profiles']['default']['primitives']
byp={}
for p in glob.glob('.ai/primitives/*/*.json'):
    r=json.load(open(p)); lc=r.get('lifecycle') or {}
    byp[r.get('canonical_source')]=(lc.get('distribution'),lc.get('lifecycle_state'))
c=collections.Counter()
for kind,items in d.items():
    for it in items: c[(byp.get(it) or ('(ausente)',None))[0]]+=1
print(sum(c.values()), dict(c))
EOF
# 69 {'lab': 42, 'team': 11, 'maintainer': 6, 'core': 3, '(ausente)': 6, None: 1}
```

**El perfil `default` proyecta 69 primitivas; sólo 3 tienen `distribution: core`.
66 de 69 violan la regla que el propio manifiesto enuncia.** No es un archivo
puntual: es sistémico, y la contradicción que el encargo anticipó es una de 66.

De la familia de aprendizaje, seis de las siete primitivas que el `default` envía
al consumidor están marcadas `lab` / `sandbox` en `.ai/primitives`:

| Primitiva | `.ai/primitives` | ¿En perfil `default`? |
|---|---|---|
| `hooks/error-learning.sh` | `lab` / `sandbox` | **sí** |
| `hooks/error-pipeline.sh` | `lab` / `sandbox` | **sí** |
| `hooks/error-pattern-detector.sh` | `lab` / `sandbox` | **sí** |
| `hooks/session-learning.sh` | `lab` / `sandbox` | **sí** |
| `hooks/user-prompt-capture.sh` | `lab` / `sandbox` | **sí** |
| `hooks/memory-prefetch.sh` | `lab` / `sandbox` | **sí** |
| `rules/error-learning.md` | `lab` / `advisory` | **sí** |

Y en la dirección opuesta, ocho piezas de aprendizaje con
`runtime_projection: true` **no** están en el perfil `default`:

| Primitiva | `.ai/primitives` |
|---|---|
| `hooks/engram-crystallize-on-session-end.sh` | `team` / `sandbox`, rp=true |
| `hooks/engram-reinforce-on-access.sh` | `team` / `advisory`, rp=true |
| `hooks/engram-daemon-launcher.sh` | `team` / `advisory`, rp=true |
| `hooks/skill-synthesis-scanner.sh` | `maintainer` / `sandbox`, rp=true |
| `hooks/auto-repair-dispatcher.sh` | `lab` / `sandbox`, rp=true |
| `hooks/engram-auto-sync.sh`, `hooks/engram-auto-import.sh` | `maintainer` / `advisory`, rp=true |
| `hooks/engram-obsidian-export-on-stop.sh` | `maintainer` / `advisory`, rp=true |

**Se reporta la contradicción, no se elige entre los dos.** Ambos artefactos son
autoritativos en su propia documentación y no hay un tercero que los compare —
que es, literalmente, el diagnóstico de ADR-342: nada compara lo que una primitiva
declara contra lo que su anfitrión publica.

Nota de alcance: `cos_lib/learning_pipeline.py` es `SCOPE: os-only` y lo importa
`cos_lib/record_error.py:6` **a nivel de módulo**. `record_completion.py:56` lleva
el comentario explicando por qué su import es diferido, y `scripts/scope_closure_gate.py:19`
existe precisamente para atrapar ese cruce. El bucle de aprendizaje de errores, en
el consumidor, depende de un módulo que por diseño no se proyecta.

---

## 6. Veredicto por pieza bajo ADR-342

| Pieza | P1 nombre | P2 momento | P3 campo | P4 escritura | P4 lectura | Veredicto |
|---|---|---|---|---|---|---|
| Engram (`mem_save`/`mem_search`) | sí | n/a (instrumento) | sí | **17.417 obs** | **sin evidencia** | **vivo a medias** — conserva, no se prueba que se recupere |
| `engram-reinforce-on-access` | sí | PostToolUse, correcto | sí | ledger inexistente | 0 | **no existe** (P4 = 0 en ambas puntas) |
| `engram-crystallize-on-session-end` | sí | Stop | sí | 371 corridas | **0 dígestos** | **no existe** (corre, no decide) |
| `error-learning` (hook) | sí | PostToolUse Bash | arreglado hoy (`12b63c6c2`) | 11 filas (2 post-fix) | 0 consumos | **no medido / sin consumidor** |
| `error-learning` (evolve_task_queue) | colisión de nombre | n/a | sí | 102 filas | **0 lectores** | **log, no aprendizaje** |
| `session-learning` | sí | Stop | sí | 369 filas | 0 corridas de mejora | **log, no aprendizaje** |
| `skill-synthesis-scanner` | sí | Stop | sí | 3 filas | **sin consumidor en el repo** | **no existe** |
| bucle de reparación | sí | — | sí | 1 fila histórica | `success:false` | **no existe** |
| ADR-261 memory governance | sí | recall-time | sí | política escrita | **gobierna 0,23 %, y no en el retriever vivo** | **no existe como control** |
| `user-prompt-capture` | sí | UserPromptSubmit | sí | 147 filas (45 hoy) | no medido | **unmeasured** |

Ninguna de las piezas marcadas "no existe" debe contarse como cobertura de
aprendizaje persistente en ningún ledger de readiness, por la regla de decisión de
ADR-342.

---

## 7. Qué del encargo era falso

Se recontó, como pide el propio encargo.

1. **"`error-learning.jsonl` tenía 11 filas antes del arreglo".** Tiene 11 filas
   **ahora**, y 2 de ellas son posteriores al arreglo (`2026-08-15T14:09:39Z`).
   Antes del arreglo eran **9**. La cifra publicada estaba corrida por las filas
   que el propio arreglo produjo.
2. **"`hooks/error-learning.sh` + `error-events`/`error-learning.jsonl`".** No
   existe ningún artefacto `error-events` en el repo
   (`ls .cognitive-os/error-events*` → no matches). Lo que sí existe y el encargo
   no menciona son **dos** archivos distintos llamados `error-learning.jsonl`
   (§2.3), que es el hallazgo relevante de esa pieza.
3. **"11 filas sobre 5.335 corridas".** No reproducible en este checkout: el
   denominador no se puede reconstruir desde `agent-trajectory.jsonl`, que reporta
   `exit_code: 0` en 3.184 de 3.184 filas y por lo tanto **no puede contar
   corridas fallidas**. La proporción publicada no tiene fuente verificable acá.
4. **"Un `mem_save` que escribe y nadie lee es lo mismo que no escribir".** Es la
   premisa correcta del encargo y se sostiene, pero el camino obvio para medirla
   —el ledger de trayectoria— da **cero escrituras en 27 días** contra 1.765
   escrituras reales en la base. Quien mida la punta de lectura desde ahí va a
   concluir "muerto" sobre la pieza más viva del sistema. La medición válida es la
   ausencia del ledger de refuerzo, no el conteo de trayectoria.
5. **"Priorizá la pregunta 1 sobre Engram, que es la pieza más usada".** Correcto
   por escritura (17.417 filas contra 369 de la segunda). Pero la pieza más
   *ejecutada* hoy es el cristalizador (126 corridas en el día contra 23
   observaciones escritas), y es la que tiene cero salida. El criterio "más usada"
   por volumen de escritura oculta a la que más corre sin producir nada.
6. **"El encargo lista 7 familias".** La familia real es mayor: al menos 8 piezas
   registradas o proyectadas que la lista no nombra (§1), incluyendo dos hooks de
   Engram **no registrados** (`engram-auto-sync`, `engram-auto-import`) y dos
   capturadores no registrados (`session-knowledge-extractor`,
   `conversation-capture`).

Lo que del encargo se confirmó tal cual: `cos_lib/learning_pipeline.py` es
`os-only` y se importa a nivel de módulo desde `record_error.py`; el manifiesto de
boundary y `.ai/primitives` se contradicen (y la contradicción es 66 de 69, no un
archivo); un archivo en 0 bytes puede tener histórico en `.archive/*.gz` (pasó con
`repair-outcomes`, y se verificó antes de concluir).

---

## 8. Descartado explícitamente

- **`skill-drift.jsonl` (2.645 filas), `skill-suggestion` (366), `adr-suggestion`
  (161), `rule-suggestion` (162):** son ledgers de *emisión de sugerencias*, no de
  conservación entre sesiones. No se midió su recepción; queda fuera de alcance y
  se anota como deuda de medición.
- **`.cognitive-os/skill-store.db` y `.cognitive-os/skill_store.db`:** ambos **0
  bytes**, ambos sin `.gz` hermano en `.archive`. Dos rutas para la misma base
  (guion vs guion bajo), ninguna inicializada. No se tocó.
- **`packages/engram-sync` y el camino de nube (`cos-engram-cloud-enroll`,
  `sync_mutations`, `sync_chunks`):** existen tablas de sincronización en la base;
  no se midieron. Federación de memoria entre instancias queda sin juzgar.
- **Punta de lectura vía logs del servidor MCP de Engram:** el servidor es externo
  al repo (plugin), no expone contador de accesos en el esquema, y auditarlo caía
  fuera del encargo interno. **Ésta es la medición que falta para cerrar la
  pregunta 4 con autoridad**, y la recomendación operativa es construirla del lado
  del repo (el hook de refuerzo ya está registrado; falta que escriba).

---

## 9. Evidencia ejecutable — reproducción completa

Todos los comandos de este informe son read-only y deterministas. El bloque
mínimo para reproducir el veredicto:

```bash
# punta de escritura
cd ~/.engram && sqlite3 "file:engram.db?mode=ro" \
  "select count(*) from observations; select substr(created_at,1,7),count(*) from observations group by 1 order by 1 desc limit 3;"

# punta de lectura (debe existir y no existe)
ls -la .cognitive-os/metrics/lifecycle-reinforcement.jsonl; ls .cognitive-os/metrics/.archive/ | grep -c lifecycle-reinforcement

# cristalizador: corre y no produce
python3 -c "import json,collections;c=collections.Counter();[c.__setitem__(json.loads(l).get('digests_created'),c[json.loads(l).get('digests_created')]+1) for l in open('.cognitive-os/metrics/crystallization-events.jsonl')];print(c)"

# vejez: nada expira, nada se borra
cd ~/.engram && sqlite3 "file:engram.db?mode=ro" \
  "select count(*) from observations where expires_at is not null; select count(*) from observations where deleted_at is not null;"

# gobernanza vs población real
cd ~/.engram && sqlite3 "file:engram.db?mode=ro" "select type,count(*) from observations group by type order by 2 desc limit 12;"

# colisión de nombres
wc -l .cognitive-os/error-learning.jsonl .cognitive-os/metrics/error-learning.jsonl
```

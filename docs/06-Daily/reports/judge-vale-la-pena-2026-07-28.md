# Juicio independiente: ¿vale la pena seguir invirtiendo en Cognitive OS?

> Fecha: 2026-07-28 · Rol: juez externo escéptico · Modo: read-only (salvo este informe)
> Rama observada: `session/content-bound-receipts` · HEAD `6762c0f2e` + trabajo sin commitear
> Todos los números de este informe llevan al lado el comando que los produjo.

---

## Veredicto

**Sí vale, pero no como lo estás midiendo: el OS ya paga su costo en *un* proyecto real (aisotropy, 141.679 disparos de hook en 11 días), y al mismo tiempo tiene un control de seguridad muerto hace 9 días en ese mismo proyecto sin que ninguna primitiva lo haya avisado.**

---

## Recomendación: (b) podar agresivo y quedarse con el núcleo que sí se usa

### Criterio de decisión (esto es lo que hay que fijar, no la opción)

**Regla de permanencia de una primitiva:**

> Una primitiva se queda en `main` si y solo si **(1)** disparó en un repo distinto de
> `luum-agent-os` en los últimos 30 días, **o (2)** es un *gate* cuyo no-disparo es la
> evidencia misma (bloqueadores) **y** tiene un test que prueba que bloquea.
> Todo lo demás va a una rama ático, no a `main`.

**Regla de go/no-go de la inversión (a 30 días):**

> Conseguir un **segundo consumidor activo** — un repo distinto de `aisotropy` con
> >1.000 disparos de hook. Si al día 30 la respuesta sigue siendo "un consumidor",
> la jugada honesta es **(c) congelar**: el OS es entonces una herramienta a medida
> de un proyecto, y hay que dejar de pagar el impuesto de comportarse como producto.

El motivo de (b) y no (a) es aritmético: **257 archivos de hook en disco, 149 dispararon
en este repo, 33 dispararon en el consumidor real.** Se está manteniendo ~7x más
superficie de la que se entrega.

El motivo de (b) y no (d) es que el diferencial contra vanilla **existe y es medible**
(sección 1), y que la disciplina de honestidad del repo (TRANSPARENCY.md, ledger de
verdad pendiente, red-team de portabilidad) es genuinamente buena y rara.

---

## 0. Correcciones a tus premisas

Recontado antes de usar. Comando de cada fila incluido.

| Premisa tuya | Realidad | Comando |
|---|---|---|
| 2.4G | **Cierto pero engañoso.** El *working dir* pesa 2.4G; los archivos versionados suman **25M**. El resto es `.git` (934M), `reference/` (313M, untracked), `dist/` (74M, untracked), `target/` (38M, untracked). | `du -sh .` / `git ls-files -z \| xargs -0 du -ch \| tail -1` / `du -sh .git reference dist target` |
| 3252 commits | **3253** en HEAD, 3250 en `main`. Premisa correcta. | `git rev-list --count HEAD` |
| 505 ADRs | **Correcto**: 505 versionados en `docs/02-Decisions/adrs/`. | `git ls-files 'docs/02-Decisions/adrs/*.md' \| wc -l` |
| 197 skills | **Correcto** como directorios en `skills/`; 220 `SKILL.md` versionados contando `packages/`. | `ls -1 skills/ \| wc -l` / `git ls-files '*/SKILL.md' \| wc -l` |
| 4821 markdown | **Falso.** Son **2380** versionados. Tu número incluía `reference/`, venvs y `__pycache__`. | `git ls-files '*.md' \| wc -l` |
| "tres lenguajes" | **Engañoso.** Python 535.449 LOC, Bash 80.232, Go 42.706, **Rust 864 LOC en 3 archivos** (un solo crate: `cos-script-exposure-audit-rs`). Es bilingüe con un componente Go real y un vestigio Rust. | `git ls-files '*.rs' \| xargs wc -l` (idem `.go`, `.py`, `.sh`) |

**Sobre el encuadre de tu pregunta:** preguntaste "¿el 100% del tráfico es meta-trabajo?".
Esa pregunta ya está contestada y la respuesta es **no** (sección 2). La pregunta útil
hoy es otra: **"¿por qué el único consumidor real tiene un hook de seguridad fallando
abierto hace 9 días y el OS no se enteró?"** — porque eso ataca la propuesta de valor
central (governance layer que previene fallas), no el volumen.

---

## 1. ¿Qué entrega esto que Claude Code vanilla no entrega?

**Entrega un mesh de hooks que efectivamente corre, y es más chico que el declarado.**

```bash
# superficie declarada vs registrada vs disparada (repo del OS)
ls -1 hooks/*.sh | wc -l                                    # 257 archivos de hook
python3 -c "import json;d=json.load(open('.claude/settings.json'));\
print(sum(len(h['hooks']) for ms in d['hooks'].values() for h in ms))"   # 162 entradas registradas
python3 -c "import json;h=set();\
[h.add(json.loads(l).get('hook')) for l in open('.cognitive-os/metrics/hook-timing.jsonl')];\
print(len(h))"                                              # 149 dispararon en julio
```

| Nivel | Cantidad |
|---|---:|
| Archivos de hook en disco | 257 |
| Entradas registradas en `settings.json` (9 eventos de ciclo de vida) | 162 |
| Hooks que dispararon en este repo (julio) | 149 |
| Hooks que **nunca** dispararon | **108** |
| Hooks que dispararon en el consumidor real (aisotropy) | **33** |

**Lo que corre de verdad en el consumidor** (11 días, 2026-07-08 → 07-19):

```bash
cd ../aisotropy && python3 -c "
import json,collections; h=collections.Counter()
[h.update([json.loads(l).get('hook')]) for l in open('.cognitive-os/metrics/hook-timing.jsonl')]
print(sum(h.values()), len(h)); print(h.most_common(10))"
# 141679 invocaciones · 33 hooks distintos · error rate 3/141679
```

| Hook | Disparos |
|---|---:|
| `session-heartbeat` | 25.736 |
| `secret-detector` | 17.336 |
| `auto-checkpoint` | 17.032 |
| `bash-hot-path-dispatcher` | 12.245 |
| `result-truncator` | 11.942 |
| `error-pipeline` / `error-learning` | 11.941 c/u |
| `large-file-advisor` | 5.288 |
| `confidentiality-enforcer` | 5.094 |
| `provenance-scan` | 5.091 |

Efectos medibles, no declarativos:
- **1.162 truncaciones de resultado** registradas (`truncation-events.jsonl`) = ahorro de contexto real.
- **417 clasificaciones de blast-radius** con `radius`/`file_score` por acción.
- **Tasa de error de la infraestructura de hooks: 3 en 141.679** (0.002%). El mesh es estable.

**Veredicto de la sección:** el diferencial contra vanilla es **real pero ~5x más chico
que el catálogo**. Vendés 257 hooks; entregás 33.

---

## 2. ¿Se usa? Sí — en exactamente un proyecto, y 18 instalaciones son decorado

```bash
for d in $(find ~/Projects -maxdepth 4 -name '.cognitive-os' -type d); do
  lines=$(find "$d" -name '*.jsonl' -exec cat {} + 2>/dev/null | wc -l)
  echo "$lines $(dirname $d)"
done | sort -rn
```

| Repo | Líneas de telemetría | Lectura |
|---|---:|---|
| `luum/aisotropy` | **249.199** | consumidor real |
| `luum/luum-agent-os` | 164.043 | el propio OS |
| Los otros **18** repos | **0 – 9** | cascarón instalado, jamás ejercitado |

Los 18 tienen `last-modified = 2026-07-20` idéntico y ~1.8M / ~185 archivos cada uno:
es **una barrida de instalación masiva del mismo día**, no adopción.

**El consumidor real es un producto de verdad**, no otro meta-proyecto:

```bash
cd ../aisotropy && head -3 README.md && git rev-list --count HEAD && \
  git log --format='%ai' | cut -c1-7 | sort | uniq -c
# "Aisotropy — Multi-tenant isolation by construction + tiered memory, en un único binario Go"
# 531 commits · 531 en 2026-07
```

**Y la atención ya se movió del OS al producto:**

```bash
git log --format='%ai' | cut -c1-7 | sort | uniq -c
```

| Mes | Commits en luum-agent-os |
|---|---:|
| 2026-03 | 118 |
| 2026-04 | 751 |
| 2026-05 | **2.164** |
| 2026-06 | 144 |
| 2026-07 | **76** |

En julio: **76 commits de OS vs 531 de producto (~1:7)**. Tu hipótesis de "el 100% del
tráfico es meta-trabajo" **queda refutada para el período actual** — aunque fue
esencialmente cierta en mayo.

---

## 3. Costo de mantenimiento

```bash
# clasificación de los 3253 commits por lo que tocan
python3 - <<'EOF'
import subprocess,collections
out=subprocess.run(['git','log','--format=@@%H','--name-only'],capture_output=True,text=True).stdout
commits=[];cur=None
for l in out.splitlines():
    if l.startswith('@@'): cur=[];commits.append(cur)
    elif l.strip() and cur is not None: cur.append(l)
prim=('hooks/','skills/','rules/','cos_lib/','lib/','scripts/','templates/','manifests/','.claude/','packages/')
cat=collections.Counter()
for c in commits:
    if not c: cat['vacío']+=1
    elif any(f.startswith(prim) for f in c): cat['toca primitivas del OS']+=1
    elif any(f.startswith('tests/') for f in c): cat['solo tests']+=1
    elif any(f.startswith(('docs/','.ai/')) for f in c): cat['solo docs/ADR']+=1
    else: cat['otro']+=1
print(cat.most_common())
EOF
```

| Categoría | Commits | % |
|---|---:|---:|
| Toca primitivas del OS | 2.152 | **66.2%** |
| Solo docs / ADR | 684 | 21.0% |
| Solo tests | 247 | 7.6% |
| Otro / vacío | 170 | 5.2% |

Costos concretos identificados:

1. **108 de 257 hooks nunca dispararon** — mantenimiento puro sin retorno.
2. **70 de 74 ítems del ledger de verdad pendiente están `verified-pending`**, solo 4
   `verified-done` (`docs/06-Daily/reports/pending-truth-latest.md`). La deuda está bien
   contabilizada y casi enteramente abierta.
3. **El estado del OS pesa 26x más que el repo que gobierna.** En aisotropy:
   `du -sh .cognitive-os` → **10G**, de los cuales **10G son `checkpoints/`** (1.276
   checkpoints). El hook `auto-checkpoint` (17.032 disparos) no tiene política de
   retención. Esto es una bomba de disco activa hoy.
4. **`.git` de 934M para 25M de archivos versionados** — ratio 37:1, secuela de la
   reescritura de historia y de artefactos binarios históricos.
5. **505 ADRs en 4 meses de un solo autor** = un ADR cada 6.4 commits. El 21% de los
   commits son solo documentación. A este ritmo, el ADR dejó de ser registro de decisión
   y pasó a ser ritual.

---

## 4. Bus factor y portabilidad

**La portabilidad está mucho mejor de lo que suponías.** Fue la premisa que más falló.

```bash
git grep -nI -E '/[U]sers/[a-zA-Z0-9._-]+' -- '*.py' '*.sh' '*.go' '*.yaml' | wc -l   # 4
git grep -lI -E '/[U]sers/[a-zA-Z0-9._-]+' -- '*.py' '*.sh' '*.go' '*.yaml'
# manifests/history-sanitization.yaml   (intencional: manifiesto de sanitización)
# tests/unit/test_provenance_scan.py    (intencional: fixture)
```

**4 ocurrencias de paths absolutos personales, ambas intencionales.** Existe además una
suite dedicada: `tests/red_team/portability/` (20+ archivos, incluye
`scope-marker-portability-gate.bats`). Esto está bien hecho.

Acoplamiento macOS, chico pero real:

```bash
git grep -nI "stat -f" -- '*.sh' '*.py' | wc -l            # 12  (BSD stat)
git grep -nI -- "sed -i ''" '*.sh' | wc -l                 #  4  (BSD sed)
git grep -nI -E '(^|[;&|] *)timeout [0-9]' -- '*.sh' | wc -l  # 7  (timeout NO existe en macOS stock)
```

Lo de `timeout` lo verifiqué en carne propia: en esta misma sesión, en esta máquina,
`timeout` devolvió `command not found`. Son 7 llamadas que fallan en el entorno del
propio autor.

**El bus factor real no es el path — es la autoría:**

```bash
git shortlog -sne --all
# 3359  MatiasNAmendola
#   88  Luz Montiel      → 97.4% un solo autor
```

Ese es el riesgo, y no se arregla con greps.

---

## 5. Claims comerciales: la parte más floja

### 5.1 Las métricas públicas están congeladas hace 3 meses

```bash
stat -f '%Sm' -t '%Y-%m-%d' public-metrics-*.json
git log -1 --format='%ad' --date=short -- public-metrics-dogfood.json
# ambos: 2026-04-27
```

Mientras tanto la auditoría que las genera corrió el **2026-07-20** con números
materialmente distintos.

### 5.2 El 39% de primitivas dormidas "bajó a 0%" por reclasificación, no por arreglo

```bash
# publicado (2026-04-27)
python3 -c "import json;d=json.load(open('public-metrics-aspirational.json'));print(d['counts'],d['dormant_aspirational_ratio'])"
# {'METADATA':45,'ASPIRATIONAL':69,'ON_DEMAND':227,'DORMANT':165,'REAL':91}  ratio 0.392

# corrida real más reciente (2026-07-20)
python3 -c "
import json,collections;c=collections.Counter()
for l in open('.cognitive-os/metrics/aspirational-audit.jsonl'):
    d=json.loads(l)
    if d.get('event_type')=='component.classified' and d['timestamp'][:10]=='2026-07-20':
        c[d['payload']['classification']]+=1
print(dict(c))"
# {'METADATA':267,'REAL':386,'ON_DEMAND':2077}   → DORMANT 0, ASPIRATIONAL 0
```

La categoría `ON_DEMAND` fue introducida (`c6caf8c8b`) y luego extendida. El commit que
cerró la brecha lo dice **en el asunto**:

```
27608a7f1 fix(audit): classify_skill checks @on-demand marker (closes <25% target gap)
   "Expected ratio: 26.2% -> ~24.9% (below 25% Phase 1 exit criterion)"
```

**Juicio matizado, porque corresponde:** el cambio subyacente es un *bug fix legítimo*
— `classify_skill` no llamaba a `has_on_demand_marker` mientras `classify_hook` y
`classify_lib` sí lo hacían. Y el commit declara el target abiertamente en vez de
esconderlo, lo cual es más honesto que el promedio de la industria. **Pero el efecto
neto es Goodhart de manual**: la métrica de honestidad se movió cambiando la definición,
y hoy el repo no publica ninguna de las dos cifras actuales.

### 5.3 El número honesto, independiente de la etiqueta

```bash
python3 -c "
import json;tot=zero=nosig=0
for l in open('.cognitive-os/metrics/aspirational-audit.jsonl'):
    d=json.loads(l)
    if d.get('event_type')!='component.classified' or d['timestamp'][:10]!='2026-07-20': continue
    tot+=1; inv=d['payload'].get('signals',{}).get('invocations_30d')
    if inv is None: nosig+=1
    elif inv==0: zero+=1
print(tot,zero,nosig)"
# 2730 clasificados · 576 con 0 invocaciones · 2154 SIN señal de invocación
```

**2.154 de 2.730 componentes (78.9%) no tienen ninguna señal de invocación.** La
auditoría de realidad **no puede saber** si el 79% de lo que clasifica se usa. Ese es el
número que habría que publicar, y no está publicado en ningún lado.

Además, el dominante de la nueva categoría es *"covered by test — legit sleeper"*
(1.024 componentes): **tener un test unitario hoy exime de ser considerado dormido.**
Un test prueba que el código funciona si se lo llama; no prueba que alguien lo llame.

### 5.4 Lo que sí está bien declarado

- `TRANSPARENCY.md` es genuinamente fuerte: declara la reescritura de historia del
  2026-05-08, publica SHA pre (`2d99d40a3`) y post (`db846adb6`), deja un inventario
  criptográfico como lápida, y fija los strings de transición de licencia como
  `preserve` no reescribibles. Esto es mejor de lo que hace casi cualquier repo.
- El claim del README está calificado con honestidad: *"14-layer safety mesh (12 fire as
  PreTool/PostTool hooks, 2 are library/conditional)"*.
- Detalle menor: los badges del README apuntan a `<org>/<repo>` literales — están rotos.

---

## 6. El hallazgo que más pesa: hay un control de seguridad muerto en producción

`confidentiality-enforcer` disparó 5.094 veces en aisotropy. De sus 1.077 resultados
registrados, **971 son `scan_error_fail_open`** — es decir, el escáner explotó y el hook
**dejó pasar la escritura**.

```bash
cd ../aisotropy && python3 -c "
import json,collections;c=collections.Counter();d=collections.Counter()
for l in open('.cognitive-os/metrics/confidentiality-enforcer.jsonl'):
    r=json.loads(l); c[r.get('action')]+=1
    if r.get('action')=='scan_error_fail_open': d[r['timestamp'][:10]]+=1
print(dict(c)); print(dict(sorted(d.items())))"
# {None: 106, 'scan_error_fail_open': 971}
# {'2026-07-20':32,'07-21':66,'07-22':86,'07-23':445,'07-27':260,'07-28':81,'07-29':1}
```

**Corre desde el 2026-07-20 hasta hoy, 9 días, sin interrupción.** Antes del 07-20 el
hook funcionaba (los registros viejos traen campo `violations`). Es una regresión.

### Causa raíz, reproducida

```bash
cd ~/Projects/luum/aisotropy
bash ~/Projects/luum/luum-agent-os/hooks/confidentiality-enforcer.sh <<< \
  '{"tool_name":"Write","tool_input":{"file_path":"'$PWD'/README.md"},"cwd":"'$PWD'"}'
# → CONFIDENTIALITY SCAN SKIPPED (infra error) for .../README.md
# → exit 0     (fail open)

python3 -c "from cos_lib.confidentiality_scanner import scan_file"
# ModuleNotFoundError: No module named 'cos_lib'

PYTHONPATH=~/Projects/luum/luum-agent-os python3 -c \
  "from cos_lib.confidentiality_scanner import scan_file; print('OK')"
# OK  → el módulo existe; lo que falta es el PYTHONPATH
```

`hooks/confidentiality-enforcer.sh:92` hace
`from cos_lib.confidentiality_scanner import ...`. El módulo **sí está proyectado** al
consumidor en `.cognitive-os/cos_lib/confidentiality_scanner.py`, pero `.cognitive-os`
no está en `PYTHONPATH` → `ModuleNotFoundError` → `sys.exit(3)` → el hook loguea y
**sale 0**. Bug de proyección/empaquetado, no de lógica.

Relacionado: el consumidor recibe **39 de 369 módulos de `cos_lib` (10.6%)**.

```bash
ls -1 ../aisotropy/.cognitive-os/cos_lib/*.py | wc -l   # 39
ls -1 cos_lib/*.py | wc -l                              # 369
```

### Por qué esto es lo más grave

En el mismo repo, en la misma ventana, `error-pipeline` y `error-learning` dispararon
**11.941 veces cada uno**. El OS tenía el evento registrado 971 veces en su propio
directorio de métricas y **ninguna primitiva lo levantó**. La capa de gobernanza tiene
**telemetría excelente y alerting nulo**. Vende "previene fallas"; acá registró la falla
y no la previno ni la avisó.

---

## 7. Qué SÍ vale y qué NO — nombrado

### Se queda (disparó en el consumidor real, con evidencia)

| Primitiva | Evidencia |
|---|---|
| `secret-detector` | 17.336 disparos |
| `auto-checkpoint` | 17.032 disparos — **condicionado a política de retención** (hoy 10G) |
| `result-truncator` | 11.942 disparos + 1.162 truncaciones efectivas |
| `error-pipeline` / `error-learning` | 11.941 c/u — **condicionado a que además alerte** |
| `bash-hot-path-dispatcher` | 12.245 disparos |
| `session-heartbeat` | 25.736 disparos |
| `large-file-advisor` | 5.288 |
| `provenance-scan` | 5.091 |
| `blast-radius` | 417 clasificaciones con score |
| `confidentiality-enforcer` | 5.094 — **una vez arreglado el PYTHONPATH** |
| `TRANSPARENCY.md` + manifiesto de sanitización | disciplina real, verificable |
| Ledger de verdad pendiente (ADR-273) | 74 ítems con verificación bilateral contra código |
| `tests/red_team/portability/` | 20+ archivos, gate real |
| `scripts/aspirational_audit.py` | vale — **con la métrica re-honestificada** (publicar el 78.9% sin señal) |

### Se poda

| Qué | Por qué |
|---|---|
| **108 hooks que nunca dispararon** | mantenimiento sin retorno; a rama ático |
| **330 de 369 módulos `cos_lib`** que nunca llegan al consumidor | si no se proyectan, no son producto |
| **196 de 197 skills** — el consumidor recibe **1** | catálogo que nadie consume |
| **El crate Rust** (864 LOC, 3 archivos, un port de paridad de *un* script de auditoría) | tercer toolchain por un solo binario |
| **18 instalaciones inertes** | crean ilusión de adopción; borrarlas o marcarlas |
| **Los 2 `public-metrics-*.json` congelados** | o se regeneran en cada release o se borran |
| **Ritmo de 1 ADR cada 6.4 commits** | documentación como rito; subir el umbral |
| **934M de `.git` para 25M versionados** | `git gc --aggressive` + revisar blobs históricos |

### Arreglar antes que cualquier feature nueva

1. **PYTHONPATH del consumidor** → resucita `confidentiality-enforcer` en aisotropy (P0).
2. **Alerta sobre `*_fail_open` en cualquier métrica** → que 971 fallas silenciosas de un
   control de seguridad sean imposibles de nuevo (P0).
3. **Retención de `auto-checkpoint`** → 10G en un consumidor (P1).

---

## 8. Opinión sin evidencia

Marcado explícitamente: lo de abajo **no** está respaldado por comandos.

- **Creo que el proyecto se salvó solo por accidente de timing.** El colapso de commits
  de mayo a julio parece agotamiento del meta-trabajo más que una decisión de producto,
  y aisotropy apareció justo a tiempo para darle al OS un consumidor. No tengo evidencia
  de intención; puede haber sido plan.
- **Creo que 505 ADRs son un síntoma, no un activo.** Sospecho que el ADR se volvió el
  entregable por defecto de las sesiones de agente porque es barato de generar y se ve
  como progreso. No lo medí.
- **Creo que el valor comercializable no es "el OS" sino tres o cuatro hooks** —
  truncación de resultados, checkpoint automático, detección de secretos, blast radius —
  que se venderían mejor como plugin chico que como sistema operativo. Es juicio de
  posicionamiento, no medición.
- **Creo que el `ON_DEMAND` va a seguir creciendo** hasta absorber todo lo que no dispara,
  salvo que se agregue una métrica adversarial que la corrija. Es una predicción.
- **No tengo opinión fundada sobre si FSL-1.1-MIT ayuda o estorba** la adopción.

---

## 9. Qué no pude verificar

- **Salud real de la suite de tests.** El único `junit.xml` cacheado tiene `tests=1,
  failures=1` — es el artefacto de una corrida puntual, no de la suite (2.188 archivos de
  test). `public-metrics-dogfood.json` reporta `test_health: null` y `"partial": true`.
  No corrí la suite (read-only + costo).
- **Si los 108 hooks que nunca dispararon están rotos o simplemente no se gatillaron.**
  Varios son bloqueadores (`destructive-rm-blocker`, `direct-main-guard`) cuyo no-disparo
  puede ser correcto. Distinguirlo requiere ejecutarlos.
- **Por qué `hook-timing.jsonl` del OS solo cubre 2026-07-20 en adelante** y el de
  aisotropy corta el 07-19. Parece rotación, pero no encontré la política.
- **Si el bug de PYTHONPATH afecta a otros hooks** además de `confidentiality-enforcer`.
  Es probable (mismo patrón de import), pero solo reproduje uno.
- **El contenido de los 74 ítems del ledger** — leí los agregados, no los ítems.
- **Si aisotropy hubiera avanzado igual o más rápido sin el OS.** Sin contrafáctico no
  hay forma; es la pregunta que ningún dato de este repo puede contestar.

---

## Reproducir este informe

```bash
cd ~/Projects/luum/luum-agent-os
git rev-list --count HEAD
git ls-files '*.md' | wc -l
git ls-files 'docs/02-Decisions/adrs/*.md' | wc -l
git ls-files -z | xargs -0 du -ch | tail -1
git shortlog -sne --all
git log --format='%ai' | cut -c1-7 | sort | uniq -c
git grep -nI -E '/[U]sers/[a-zA-Z0-9._-]+' -- '*.py' '*.sh' '*.go' '*.yaml' | wc -l
for d in $(find ~/Projects -maxdepth 4 -name '.cognitive-os' -type d); do \
  echo "$(find $d -name '*.jsonl' -exec cat {} + 2>/dev/null | wc -l) $(dirname $d)"; done | sort -rn
cd ../aisotropy && bash ../luum-agent-os/hooks/confidentiality-enforcer.sh <<< \
  '{"tool_name":"Write","tool_input":{"file_path":"'$PWD'/README.md"},"cwd":"'$PWD'"}'
```

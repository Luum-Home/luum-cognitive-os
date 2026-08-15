# ¿Este repo tiene sentido? — juicio externo del 2026-08-15

> Rol: juez externo escéptico · Modo: read-only salvo este archivo
> Rama observada: `main` · HEAD `8602ddc70` (2026-07-28) · origin/main `e9353a2cc` (2026-07-20)
> Todo número lleva al lado el comando que lo produjo. Re-corrí todo: no cito ninguna
> cifra del juez del 2026-07-28 sin haberla vuelto a medir.
>
> **Este informe fue corregido dos veces durante su redacción**, ante evidencia que refutó
> mediciones propias. Las correcciones a mí mismo están marcadas y explicadas en el §12,
> no borradas.

---

## 1. Veredicto

**PODAR.** No es un producto sin adopción: es un producto **con canal de distribución y sin
verificación de entrega**. Llegó a 16 instalaciones, y llegó roto en silencio — cuatro módulos
que sus propios hooks importan nunca se empaquetaron, y cada consumidor de esos módulos se
traga la excepción y sigue.

No es ARCHIVAR: hay dos consumidores vivos, las instalaciones son autocontenidas y el valor
entregado es medible (~3,15M tokens de contexto ahorrados). No es CONGELAR: congelar deja 16
instalaciones corriendo código con fallas conocidas y silenciosas. No es SEGUIR: seguir como
viene es exactamente lo que produjo **cuatro fail-opens silenciosos distintos**, todos de la
misma causa raíz, ninguno detectado por el propio OS.

Se poda hasta el conjunto que se pueda verificar punta a punta, y se construye la verificación
que falta. En ese orden.

---

## 2. Criterio de decisión — fechado y falsable

Evaluable por el operador solo, con comandos, sin juez.

### Fecha de corte: **2026-09-15**

```bash
# (a) superficie
ls -1 ~/Projects/luum/luum-agent-os/hooks/*.sh | wc -l

# (b) el P0, en los últimos 7 días, en los consumidores vivos
python3 - <<'EOF'
import json,datetime
lim=(datetime.date.today()-datetime.timedelta(days=7)).isoformat()
for r in ['aisotropy','FinOpenPOS']:
    p=os.path.expanduser(f'~/Projects/luum/{r}/.cognitive-os/metrics/confidentiality-enforcer.jsonl')
    n=sum(1 for l in open(p,errors='ignore')
          if (lambda d: d and str(d.get('timestamp',''))[:10]>=lim and d.get('action')=='scan_error_fail_open')(
              __import__('json').loads(l) if l.strip().startswith('{') else None))
    print(r,'fail_open_7d',n)
EOF

# (c) cierre de la clausura de imports: lo que los hooks importan, ¿está empaquetado?
python3 - <<'EOF'
import os,re,glob
inst=os.path.expanduser('~/Projects/luum/luum-talent/.cognitive-os')   # instalación cualquiera, NO FinOpenPOS
have={os.path.basename(p)[:-3] for p in glob.glob(inst+'/cos_lib/*.py')}
need=set()
for p in glob.glob(inst+'/hooks/**/*.sh',recursive=True):
    t=open(p,errors='ignore').read()
    need|=set(re.findall(r'from\s+cos_lib\.([a-zA-Z0-9_]+)\s+import',t))
    need|=set(re.findall(r'import\s+cos_lib\.([a-zA-Z0-9_]+)',t))
print('modulos requeridos y AUSENTES:',len(need-have),sorted(need-have))
EOF

# (d) release posterior a hoy
cd ~/Projects/luum/luum-agent-os && git tag --format='%(creatordate:short) %(refname:short)' --sort=-creatordate | head -1
```

**La poda tuvo éxito si y solo si, al 2026-09-15, se cumplen las cuatro:**

| # | Condición | Hoy |
|---|---|---|
| a | `hooks/*.sh` en disco **≤ 60** | 257 |
| b | `scan_error_fail_open` de los últimos 7 días **== 0** en ambos consumidores | 121 + 5 |
| **c** | **Clausura de imports cerrada: 0 módulos requeridos y ausentes**, verificado sobre una instalación que no sea FinOpenPOS | **4 ausentes** |
| d | Existe **≥1 tag** con fecha ≥ 2026-08-16 | último 2026-07-20 |

**Reglas de escalada, sin prórroga:**

- Si **(b)** sigue >0 al 2026-09-15 → **CONGELAR**. Una capa de gobernanza que necesita 48 días
  para arreglar su propio control de seguridad caído no es una capa de gobernanza.
- Si **(c)** sigue >0 al 2026-09-15 → **CONGELAR**, y con más razón que (b). (c) cuesta el
  script de arriba, que tarda un segundo. Un mes sin cerrarlo no es falta de tiempo: es que
  nadie está mirando el canal de entrega, que es la única razón por la que este repo existe
  como producto y no como carpeta de scripts.

(c) es nueva respecto de la primera versión de este informe, y es la condición que más me
importa. El motivo está en el §5.

---

## 3. Tabla de evidencia

| Pregunta | Comando | Salida | Qué implica |
|---|---|---|---|
| ¿Hace cuánto que no se toca? | `git log -1 --format='%h %ad' --date=short` | `8602ddc70 2026-07-28` | **18 días** sin commit |
| ¿Está pusheado? | `git rev-list --count origin/main..main` | `4` | **4 commits sin pushear**, hace 26 días |
| Cadencia de release | `git tag --format='%(creatordate:short)' \| cut -c1-7 \| sort \| uniq -c` | Mar 46 · Abr 32 · May 59 · Jun 17 · Jul 4 · **Ago 0** | colapso, no desaceleración |
| ¿Cuántas instalaciones? | `find ~/Projects -maxdepth 4 -name .cognitive-os -type d` + conteo de hooks | **16 completas** + 1 parcial | ver §4 |
| ¿Cuántas vivas? | eventos con timestamp en los últimos 30 días | **2** (aisotropy, FinOpenPOS) | 14 con **cero** eventos en 30 días |
| ¿Cuántas versiones distintas? | hash del set de hooks proyectados | **3 cohortes** + 1 parcial | 14 byte-idénticas del 2026-07-20 |
| ¿Llegó funcionando? | clausura de imports sobre instalación prístina | **4 módulos requeridos y ausentes** | llegó roto, en silencio, a las 16 |
| ¿Se puede probar el efecto? | hooks mudos en instalación sin reparar vs reparada | **3 hooks desbloqueados** por la reparación | efecto real y acotado |
| Valor entregado | `truncation-events.jsonl`, `original_chars - truncated_chars` | **1.985 truncaciones · ~3,15M tokens** | el único ROI duro, y es real |
| Superficie mantenida | `ls -1 hooks/*.sh \| wc -l` | **257** | |
| Superficie que dispara | telemetría de consumidores, 30 días | **43** (41 netos de no-ops) | 214 se mantienen sin llegar a nadie |
| P0 del juez anterior | conteo de `scan_error_fail_open` | **1.962** FinOpenPOS + **446** aisotropy (agosto) | no se arregló y se propagó |
| Causa raíz, reproducida hoy | `bash hooks/confidentiality-enforcer.sh <<< '{...}'` | `SCAN SKIPPED (infra error)` · `exit=0` | `ModuleNotFoundError: cos_lib` |
| Deuda declarada | `git show HEAD:...pending-truth-latest.json` | 74 ítems: **70 pending / 4 done** | 94,6% abierta |
| ADRs | `ls docs/02-Decisions/adrs \| grep -c '^ADR-'` | **501** archivos ADR | el encargo decía 505 |
| Gobernanza global de la máquina | origen de cada hook de `~/.claude/settings.json` | **12 entradas, 0 de este repo** | el OS no ganó el toolchain de su autor |

---

## 4. El parque instalado: 16 instalaciones, 2 vivas

```bash
find ~/Projects -maxdepth 4 -name '.cognitive-os' -type d
# 21 directorios, de los cuales 4 son basura o el propio OS:
#   luum/ (raíz), luum/luum-agent-os/--help, luum/cognitive-os-demo, luum/luum-agent-os
```

**El número de 16 que reportaron es correcto.** Contando instalaciones con proyección completa
de hooks: 16, más una parcial. Mi primera medición dijo "22 directorios / 2 consumidores" y
mezclaba basura con instalaciones; corregido.

### Cohortes de versión

```bash
# hash sha256 del set completo de hooks proyectados, por instalación
```

| Cohorte | Instalaciones | Hooks | Proyectado | Eventos 30d |
|---|---:|---:|---|---:|
| `ae094062a70a` | **14** (byte-idénticas) | 76 | 2026-07-20 | solo aisotropy: 179.445 |
| `35807a9fb032` | 1 — FinOpenPOS | 78 | **2026-08-15** | 52.693 |
| `5d283cb8350b` | 1 — luum-lang | **188** | 2026-07-20 | 0 |
| `8eb1e18b91ae` | 1 — rbvm-platform (parcial) | 19 | **2026-03-31** | 0 |

### Las tres cuentas que el encargo pidió distinguir

| Categoría | Cuántas | Cuáles |
|---|---:|---|
| **Instalaciones** (existe el directorio con hooks) | **16** + 1 parcial | 14 del sweep + FinOpenPOS + luum-lang (+ rbvm-platform parcial) |
| **Vivas** (disparos en 30 días) | **2** | `aisotropy` (179.445 ev.), `FinOpenPOS` (52.693 ev.) |
| **Al día** | **1** | solo FinOpenPOS, y porque la repararon anoche |
| **Quedadas en versión vieja** | **15** | 14 en la cohorte del 2026-07-20; rbvm-platform en una del **2026-03-31** (4,5 meses) |

Las 14 de la cohorte grande no son "adopción": son **una barrida de instalación de un día**.
Su telemetría máxima de por vida es **9 eventos** (`luum-interface-layer`, último 2026-05-10);
nueve de ellas tienen **cero**. Nadie trabajó nunca en esos repos con el OS puesto.

**"16 instalaciones" es cierto. "16 consumidores" es falso.** Instalar costó una barrida de un
día; usar no. La diferencia entre 16 y 2 no la explica ningún defecto del instalador — la
explica que en 14 de esos repos no hubo trabajo.

**Contaminación de la muestra, declarada y confirmada por mí:** FinOpenPOS tiene sus hooks con
mtime **2026-08-15** y una cohorte propia de 78 hooks. La reparación de anoche es visible en
el filesystem. Todo lo que sigue sobre "estado del parque" se mide sobre la cohorte de 14, no
sobre FinOpenPOS.

### Lo que la máquina del operador dice, y sigue diciendo

Los 12 hooks de `~/.claude/settings.json` —los que corren en todos los proyectos— no salen de
este repo: son de otra familia (`g2k-infra`: `secreto-no-sale`, `git-flow-guard`,
`stagnation-guard`, `clon-antes-de-clonar`, `primitivas-drift-guard`, `tracker-html-guard`,
`block-destructive-bash`). De 38 skills globales, **6** vienen del OS y las seis son SDD. Con
257 hooks y 197 skills instalados en 16 lugares, el OS no colonizó el perfil de su propio autor.
Ese dato no lo mueve la corrección de las 16 instalaciones: al contrario, la subraya.

---

## 5. Llegó, y llegó roto: la clausura de imports

Medido sobre `luum-talent` — cohorte de 14, nunca disparó, **no** es FinOpenPOS:

```bash
cd ~/Projects/luum/luum-talent
python3 - <<'EOF'
import os,re,glob
inst='.cognitive-os'
have={os.path.basename(p)[:-3] for p in glob.glob(inst+'/cos_lib/*.py')}
need=set(); byhook={}
for p in glob.glob(inst+'/hooks/**/*.sh',recursive=True):
    t=open(p,errors='ignore').read()
    m=set(re.findall(r'from\s+cos_lib\.([a-zA-Z0-9_]+)\s+import',t))|set(re.findall(r'import\s+cos_lib\.([a-zA-Z0-9_]+)',t))
    if m: byhook[os.path.basename(p)]=m; need|=m
print(len(byhook),'hooks importan cos_lib |',len(have),'módulos presentes |',len(need),'requeridos')
print('AUSENTES:',sorted(need-have))
for h,m in byhook.items():
    if m-have: print('  ROTO',h,'->',sorted(m-have))
EOF
```

```
20 hooks importan cos_lib | 39 módulos presentes | 29 requeridos
AUSENTES: ['capability_levels', 'context_budget', 'performance_monitor', 'process_registry']
  ROTO common.sh            -> ['capability_levels']
  ROTO context_budget_lib.sh -> ['context_budget']
  ROTO register-bg.sh       -> ['process_registry']
  ROTO timing.sh            -> ['performance_monitor']
```

**Cuatro módulos que los hooks importan nunca se empaquetaron.** Y los cuatro fallan callados:

```bash
# .cognitive-os/hooks/cos/_lib/common.sh:139
try:
    from cos_lib.capability_levels import should_component_run
    if not should_component_run(...): print('disabled')
except Exception:
    pass                        # ← el gating de capability-levels NUNCA corre

# .cognitive-os/hooks/cos/_lib/timing.sh:57
from cos_lib.performance_monitor import PerformanceMonitor
...
" 2>/dev/null || true           # ← el registro de timing NUNCA corre
```

`common.sh` lo sourcean **19 hooks**. El resultado es que en las 16 instalaciones el gating por
nivel de capacidad no existe: falla abierto, igual que el scanner de confidencialidad.

### La consecuencia, medida

```bash
cd ~/Projects/luum/aisotropy   # instalación viva, sin reparar
# hook-timing.jsonl : primer registro 2026-07-08 · ÚLTIMO 2026-07-19
# hook-health.jsonl : primer registro 2026-07-08 · último 2026-08-14 (sigue vivo)
```

Los hooks **siguieron disparando** un mes más; lo que murió el 2026-07-19 fue el **registro de
tiempos**, que es justo el subsistema cuyo módulo falta. El mecanismo está probado
(`performance_monitor` ausente + error tragado); la fecha exacta la doy como correlación, no
como causa demostrada — la refresco de proyección más cercana es del 2026-07-20 y no puedo
descartar rotación de archivo.

### Efecto de la reparación, acotado con honestidad

Comparando hooks mudos en aisotropy (sin reparar) contra FinOpenPOS (reparada anoche):

| Hook | Disparos en FinOpenPOS | Primer día |
|---|---:|---|
| `auto-refine` | 59 | 2026-07-29 |
| `auto-verify` | 74 | 2026-07-29 |
| `clarification-interceptor` | 59 | 2026-07-29 |
| `dod-gate` | 69 | 2026-07-29 |
| **`orchestrator-claim-gate`** | 45 | **2026-08-15** |
| **`rate-limiter`** | 45 | **2026-08-15** |
| **`research-compliance-guard`** | 45 | **2026-08-15** |

**Tres hooks empiezan a disparar el mismo día de la reparación**, después de estar mudos. Los
otros cuatro ya disparaban desde el 2026-07-29 — o sea, nunca estuvieron bloqueados por el
defecto; simplemente no se usaban en aisotropy.

**El efecto de "llegó roto" es real y es de 3 hooks confirmados**, más el subsistema de timing,
más el gating de capacidad, más el budget de contexto, más el registro de procesos en
background. No es de 214. Digo el número chico porque es el que puedo probar.

---

## 6. Corrección a mi propia regla de permanencia

La primera versión de este informe proponía:

> *"Una primitiva se queda si y solo si disparó al menos una vez en un repo distinto de
> `luum-agent-os` desde el 2026-07-16."*

**Esa regla, aplicada hoy, es tramposa contra el repo**, y la evidencia del §5 lo demuestra:
poda por "no disparó" primitivas que no dispararon **porque nunca llegaron enteras**. Medir
demanda sobre un canal roto no mide demanda, mide el canal.

**Regla corregida:**

> Una primitiva se queda si y solo si **disparó al menos una vez, en los últimos 30 días, en un
> repo distinto de `luum-agent-os` cuya clausura de imports esté cerrada** (0 módulos requeridos
> y ausentes).
>
> Mientras no exista ninguna instalación con clausura cerrada, **la regla no se puede aplicar** y
> la poda no arranca. Primero se arregla el canal, después se mide, después se poda.

Cuánto contamina la regla vieja, acotado: mi conteo de 43 sobrevivientes se midió sobre
`hook-timing.jsonl` **y** `hook-health.jsonl`, y `hook-health` siguió funcionando hasta el
2026-08-14. Así que el corte del timing **no** corrompió el conteo. Los falsos podados
demostrables son **3** (los desbloqueados por la reparación) más los que dependan de los cuatro
módulos ausentes. Es una corrección al margen, no una vuelta de campana — pero es una corrección
que sale gratis y que sin el dato del §5 nadie habría hecho.

Aplicando la regla vieja (única aplicable hoy, con la advertencia puesta):

```bash
# en disco 257 | sobreviven 43 | se podan 214
# menos dos no-ops probados (dod-gate: 0 gates en 59 disparos;
#                            auto-verify: 0 verificaciones en 60) → núcleo de 41
```

Núcleo, por disparos en consumidores: `secret-detector` (40.621) · `error-pipeline` (38.064) ·
`result-truncator` (38.064) · `error-learning` (28.460) · `session-heartbeat` (17.087) ·
`auto-checkpoint` (11.844) · `doc-sync-detector` (11.416) · `large-file-advisor` (9.378) ·
`bash-hot-path-dispatcher` (8.717) · `provenance-scan` / `content-policy` /
`confidentiality-enforcer` (3.353 c/u) · `session-learning` (1.726) · y 28 más.

---

## 7. Costo de mantenerlo: distribución sin verificación de entrega

Mi primera versión llamó a esto "falla de entrega" y midió una cadena de degradación. Con el
dato de las 16 instalaciones, **el diagnóstico correcto es otro y es peor**:

```bash
ls -1 hooks/*.sh | wc -l                                                  # 257  mantenidos
# referenciados en .claude/settings.json del OS                           # 155
find ~/Projects/luum/luum-talent/.cognitive-os/hooks -name '*.sh' | wc -l # 76   proyectados x16
# módulos cos_lib empaquetados                                            # 39 de 369
# módulos cos_lib requeridos por los hooks y AUSENTES                     # 4
# hooks que dispararon en un consumidor vivo                              # 31
```

| Escalón | Hooks | % |
|---|---:|---:|
| Mantenidos en disco | 257 | 100% |
| Registrados en el origen | 155 | 60,3% |
| **Distribuidos a 16 instalaciones** | **76** | **29,6%** |
| Cableados en el consumidor | 44 | 17,1% |
| Dispararon en un consumidor vivo | 31 | 12,1% |

**El repo no falló en llegar: llegó a 16 lugares.** Falló en verificar que lo que llegó
funcionara. Y el costo de esa verificación es el script del §5: veinte líneas, un segundo de
ejecución, cero dependencias. Existiendo `tests/red_team/portability/` —que está bien hecho—
la ausencia de un test de clausura de imports en el instalador no es falta de cultura de
testing; es que nadie miró nunca el artefacto entregado.

Dos costos más, medidos:

1. **No hay marcador de versión en ninguna instalación.** No se puede saber qué versión corre
   un consumidor. Lo más cercano es `.cognitive-os/cos_lib/.closure-manifest.json`, que se
   llama "closure manifest" y no detectó una clausura rota de cuatro módulos.
2. **Drift silencioso.** De los 45 hooks proyectados con homónimo en el origen, **18 tienen
   contenido distinto** (`cmp -s`). Y la cohorte de rbvm-platform lleva **4,5 meses** sin tocar.

**Disco:**

```bash
du -sh . .git reference .cognitive-os          # 2.4G / 934M / 313M / 299M
git ls-files -z | xargs -0 du -ch | tail -1    # 25M  ← lo versionado
du -sh ~/Projects/luum/aisotropy/.cognitive-os # 11G  (10G en 1.428 checkpoints)
```

El estado que el OS deposita en **un** consumidor pesa **440x** los archivos versionados del OS
entero, y creció 1G en los 18 días desde la medición anterior. Sin política de retención.

---

## 8. ¿Qué produjo de valor?

**Valor real, medible con un comando:**

| Consumidor | Truncaciones | Original → truncado | Ahorro |
|---|---:|---|---:|
| aisotropy | 1.298 | 12.221.657 → 3.973.088 chars | ~2,06M tokens |
| FinOpenPOS | 687 | 6.459.819 → 2.091.564 chars | ~1,09M tokens |
| **Total** | **1.985** | | **~3,15M tokens** |

1.985 veces que un resultado de comando no reventó la ventana de contexto. Alcanza para
justificar el núcleo de 41 hooks. `blast-radius` aporta 177 clasificaciones en FinOpenPOS
(39 HIGH + 30 CRITICAL). `secret-detector` disparó 40.621 veces y redactó **6**.

**Trabajo que sirve al OS, no al usuario — sigue siendo la mayoría:** de los 40 commits desde
el 2026-07-16, **26 tocan primitivas del propio OS**, 4 son solo tests, 2 solo docs. La
hipótesis de meta-trabajo no está refutada; está **atenuada** porque el volumen total cayó a
40 commits y después a cero.

**Deuda declarada:** 70 de 74 ítems del ledger en `verified-pending`, 4 en `verified-done`, sin
movimiento desde el 2026-07-18. La contabilidad de la deuda es excelente; la amortización no
existe.

---

## 9. El patrón que decide el veredicto

No es un bug. Son **cuatro instancias independientes del mismo fail-open silencioso**, y las
cuatro las verifiqué yo:

| # | Qué falla | Dónde se traga el error | Alcance | Evidencia |
|---|---|---|---|---|
| 1 | Scanner de confidencialidad | `sys.exit(3)` → hook sale `0` | 2 consumidores vivos | **2.408** fail-opens en agosto |
| 2 | Gating por nivel de capacidad | `except Exception: pass` (`common.sh:143`) | **19 hooks × 16 instalaciones** | módulo `capability_levels` ausente |
| 3 | Registro de tiempos de hook | `2>/dev/null \|\| true` (`timing.sh:60`) | 16 instalaciones | `hook-timing` muerto desde 2026-07-19 |
| 4 | Budget de contexto / registro de procesos bg | import ausente | 16 instalaciones | `context_budget`, `process_registry` |

**El producto se vende como capa de gobernanza que previene fallas.** Registró la falla 2.408
veces en su propio directorio de métricas, en dos repos, durante 26 días, y no avisó. Y las
otras tres ni siquiera dejaron rastro: fallan tan silenciosamente que hizo falta comparar
imports contra archivos empaquetados para encontrarlas.

**Telemetría excelente, alerting nulo, y verificación de entrega inexistente.** Ese es el
diagnóstico del repo en una línea.

---

## 10. Correcciones a las premisas del encargo

| Premisa | Realidad medida | Comando |
|---|---|---|
| "505 ADRs" | **501** archivos `ADR-*.md`; los otros 4 son `INDEX.md`, `README.md`, `STATUS-TAXONOMY.md`, `templates/` | `ls docs/02-Decisions/adrs \| grep -c '^ADR-'` |
| "8344 archivos trackeados" | **Correcto** | `git ls-files \| wc -l` |
| "2.4G" | **Cierto y engañoso.** Working dir 2.4G; **versionado 25M**. El resto: `.git` 934M, `reference/` 313M, `.cognitive-os/` 299M | `du -sh .` vs `git ls-files -z \| xargs -0 du -ch` |
| "HEAD 2026-07-28" | Correcto e **incompleto**: `origin/main` está en el **2026-07-20**, con **4 commits sin pushear** hace 26 días | `git rev-list --count origin/main..main` |
| "el operador está inclinado al no" | Llega tarde para ARCHIVAR y temprano para CONGELAR: el segundo consumidor arrancó el 2026-07-29 y hoy es el más caliente | §4 |
| (implícita) "el consumidor depende del checkout del OS" | **Falso.** Los `settings.json` apuntan a `$CLAUDE_PROJECT_DIR/.cognitive-os/...`, nunca a `luum-agent-os`. Archivar **no** rompe a los consumidores | `.claude/settings.json` de cada consumidor |

---

## 11. Correcciones al juez anterior (2026-07-28)

| Su afirmación | Estado hoy |
|---|---|
| "el único consumidor es aisotropy; **18 instalaciones son decorado**" | **Mitad y mitad, y la mitad que falló es la que importa.** Acertó en que no eran consumidores: 14 siguen con cero eventos. Erró en llamarlas "decorado" sin abrirlas — adentro había un canal de distribución con la clausura de imports rota, que es el hallazgo central de este informe. Descartó por volumen lo que había que auditar por contenido |
| Su go/no-go: "si al día 30 sigue habiendo un consumidor, congelar" | **Se cumplió a favor del repo al día 18**: FinOpenPOS, 47.554 invocaciones, 47x el umbral. Por su propio criterio, CONGELAR queda descartado |
| "257 hooks, 149 dispararon en el OS, 33 en el consumidor" | Recontado: 257 en disco, **156** en el OS, **43** en la unión de los dos consumidores vivos |
| "66,2% de los commits tocan primitivas del OS" | En la ventana reciente, **26/40 = 65%**. Se sostiene |
| P0 `confidentiality-enforcer` / PYTHONPATH | **Confirmado y agravado**: no se arregló, se propagó, y resultó ser una de cuatro instancias del mismo patrón |
| "10G de checkpoints en aisotropy" | Hoy **11G** / 1.428 checkpoints |
| Su regla de permanencia, con excepción para "gates cuyo no-disparo es la evidencia" | **La saqué por inauditable y la reemplacé por otra cosa** (§6): la excepción correcta no es para gates, es para instalaciones con la clausura rota |
| Su recomendación (b) "podar agresivo" | **Se sostiene en la dirección, no en el orden.** Podar antes de arreglar el canal habría podado primitivas que nunca llegaron enteras |

**Donde más se equivocó:** escribió el informe el día anterior a que apareciera la evidencia que
su propio criterio pedía. Y midió el parque instalado por su telemetría en vez de abrirlo.

---

## 12. Mis propias correcciones, durante este informe

Las dejo escritas porque el encargo pedía un juez, no un informe prolijo.

| Escribí | Me refutó | Corregido a |
|---|---|---|
| "22 instalaciones, 2 consumidores" | conteo por hooks proyectados, no por directorios | **16 instalaciones completas** + 1 parcial; 2 vivas. El número de terceros era el correcto |
| "el repo **no llegó** al consumidor (12% de entrega)" | 16 instalaciones byte-idénticas de una barrida | **llegó a 16 y llegó roto**. Distribución sin verificación de entrega, no ausencia de distribución |
| Regla de permanencia: "disparó en 30 días" | 4 módulos ausentes → primitivas mudas por el canal, no por falta de demanda | regla con **precondición de clausura cerrada** (§6); la poda no arranca antes |
| "3 afirmaciones de terceros, no verificadas" | las verifiqué por otra vía mientras medía el parque | **2 de 3 confirmadas independientemente** (§13) |
| Criterio de decisión con 3 condiciones | faltaba la que mide el canal | **4 condiciones**, con (c) clausura de imports como la más importante |

**Lo que no cambió, y por qué:** el veredicto. Ninguna de estas correcciones toca los dos hechos
que lo sostienen — 14 instalaciones con cero uso en 30 días (el canal roto no explica ausencia
de demanda, explica ausencia de función donde hubo demanda), y 214 hooks mantenidos que no
llegan ni a las instalaciones que sí funcionan.

---

## 13. Insumo de terceros: qué verifiqué y qué no

El coordinador me pasó tres afirmaciones con instrucción de no verificarlas. Al medir el parque
instalado tropecé con dos por otra vía. Las reporto separadas:

| Afirmación de terceros | Mi estado |
|---|---|
| Plantilla de configuración de confidencialidad nunca llegó a ningún consumidor (18/18 ciegas) | **NO verificada.** No la medí |
| ~8 módulos Python descartados por referencias en `try/except: pass`; el circuit breaker nunca corrió | **CONFIRMADA por otra vía, con número propio.** Encontré **4** módulos requeridos y ausentes, y el `except Exception: pass` literal en `common.sh:143`. Sobre el circuit breaker: `circuit-breaker` está proyectado en aisotropy y **no tiene un solo registro de telemetría**. Mi número es 4, no 8 — mido imports de hooks, no de toda la librería |
| El timing de hooks nunca funcionó en ningún consumidor | **CONFIRMADA en el mecanismo, matizada en el alcance.** `timing.sh` importa `performance_monitor`, que no está empaquetado, y traga el error con `2>/dev/null \|\| true`. Pero en aisotropy sí hubo 141.679 registros de timing entre el 2026-07-08 y el **2026-07-19**, y ahí cortó. O sea: funcionó y **dejó** de funcionar. "Nunca funcionó" es más fuerte de lo que muestran los datos |

**Sobre la contaminación declarada:** confirmada de forma independiente. Los hooks de FinOpenPOS
tienen mtime 2026-08-15 y forman una cohorte propia de 78 hooks contra los 76 idénticos del
resto. Todo el análisis de parque salió de `luum-talent`, y la comparación reparada/sin-reparar
del §5 usa esa diferencia como instrumento, no la ignora.

---

## 14. La balanza que el encargo pidió: ¿abandonar o self-check?

El dato corta en las dos direcciones y las dos son ciertas. Cómo las peso:

**Contra el repo, y es lo más grave del informe.** Un producto cuya tesis es "capa de gobernanza
que previene fallas" distribuyó 16 instalaciones donde el scanner de confidencialidad, el gating
de capacidad, el monitor de performance y el budget de contexto fallan **en silencio**, por
versiones, y ninguna de las cuatro fue detectada por el propio OS pese a tener telemetría de
sobra. No es un bug de empaquetado: es la refutación empírica de la propuesta de valor, cuatro
veces, en su propio parque instalado.

**A favor del repo, y no lo resuelvo por el lado fácil.** No se puede concluir "esto no entrega
valor" a partir de instalaciones que nunca corrieron el código. El techo de valor **nunca se
midió**. Y el arreglo es barato hasta lo ridículo: el script del §5 son veinte líneas y encuentra
los cuatro módulos en un segundo. Un producto con canal de distribución y sin self-check tiene un
problema de un día de trabajo. Un producto sin usuarios tiene un problema que no se arregla
trabajando.

**Elijo: es el segundo — distribución sin verificación de entrega — y por eso PODAR, no
ARCHIVAR.** Pero el mismo dato hace más urgente podar, no menos, y esto es lo que quiero que
quede:

Las 16 instalaciones no son 16 usuarios; son **16 copias de una superficie que nadie verificó**,
y cada una es un lugar donde el próximo defecto silencioso se va a replicar sin que nadie lo
vea. Mantener 257 hooks es caro. Distribuir 76 hooks × 16 instalaciones sin un test de clausura
es **caro y peligroso**, porque convierte cada barrida de instalación en una multiplicación de
lo que esté roto ese día. El 2026-07-20 se hizo exactamente eso.

La poda no es un castigo por falta de adopción. Es **la condición para que la verificación sea
posible**: 41 primitivas con clausura cerrada y entrega verificada valen más —y cuestan
muchísimo menos— que 257 distribuidas a ciegas a 16 lugares.

---

## 15. VERIFICADO vs NO VERIFICADO

### Verificado por mí, con comando, en esta sesión

- Fechas y estado de push de `HEAD`/`origin/main`; 4 commits sin pushear hace 26 días.
- Cadencia de tags: 46/32/59/17/4/**0** de marzo a agosto.
- **16 instalaciones completas + 1 parcial**, agrupadas en 3 cohortes por hash de contenido;
  14 byte-idénticas del 2026-07-20; rbvm-platform del 2026-03-31.
- **2 instalaciones vivas**; 14 con cero eventos en 30 días y máximo 9 de por vida.
- **Clausura de imports rota**: 4 módulos requeridos y ausentes en instalación prístina, con
  los `except: pass` y `2>/dev/null || true` que los tragan, citados por archivo y línea.
- 19 hooks sourcean `common.sh`, cuyo import de `capability_levels` falla abierto.
- `hook-timing` muerto en aisotropy desde 2026-07-19 mientras `hook-health` siguió al 2026-08-14.
- **3 hooks desbloqueados** por la reparación de FinOpenPOS (primer disparo 2026-08-15).
- Contaminación de FinOpenPOS confirmada por mtime y por cohorte propia.
- P0 `confidentiality-enforcer`: 2.408 fail-opens en agosto, causa raíz reproducida hoy.
- Ahorro por truncación: 1.985 eventos, ~3,15M tokens.
- `dod-gate` y `auto-verify` como no-ops (0 efectos en 119 disparos combinados).
- Autocontención de las instalaciones; ausencia de marcador de versión; drift de 18 de 45 hooks.
- Origen de los 12 hooks globales de `~/.claude` (ninguno de este repo).
- Ledger: 74 ítems, 70 pending / 4 done. 501 archivos ADR. 25M versionados vs 2.4G de working dir.

### NO verificado — lo digo antes de que lo pregunten

- **Salud de la suite de tests.** Prohibida por el encargo. No sé si los 2.265 archivos de test
  pasan, y no opino sobre calidad de código.
- **La plantilla de configuración de confidencialidad** (afirmación 1 de terceros). No la medí.
- **Si los 214 hooks podables están rotos, mudos por el canal, o sin demanda.** Acoté el efecto
  del canal a 3 hooks demostrables, pero no lo cerré: para cerrarlo hay que reparar una
  instalación y volver a medir. Es exactamente la precondición del §6.
- **Si el corte del timing el 2026-07-19 fue causado por la barrida del 07-20** o por rotación
  de archivo. El mecanismo está probado; la causalidad de la fecha no.
- **Cuántos módulos `cos_lib` faltan más allá de los 4** que importan los hooks. Terceros dicen
  ~8 contando toda la librería; yo medí solo la clausura de hooks.
- **Si aisotropy o FinOpenPOS hubieran avanzado igual sin el OS.** No hay contrafáctico. Es la
  pregunta que decide el ROI real y ningún comando de este repo la contesta.
- **Si el drift de 18 hooks es intencional o accidental.** Comparé bytes, no semántica.

---

## 16. Las tres acciones, en orden

**1. Pushear los 4 commits, hoy.** Una feature existe en una sola máquina hace 26 días. Única
acción irreversible-si-no-se-hace de la lista, y cuesta un comando.

```bash
cd ~/Projects/luum/luum-agent-os && git push origin main
```

**2. Cerrar la clausura de imports y ponerle un self-check al instalador.** Empaquetar
`capability_levels`, `context_budget`, `performance_monitor`, `process_registry`; arreglar el
`PYTHONPATH` que deja el scanner de confidencialidad fallando abierto; y agregar al instalador
el test del §5 —requeridos menos empaquetados igual a cero— como gate de salida, más una alerta
sobre cualquier `*_fail_open` en cualquier métrica. Después, re-proyectar las 2 instalaciones
vivas y **volver a medir qué dispara**.

Esto va **antes** de podar, y ahora con una razón demostrada en vez de una precaución: la poda
del §6 no se puede aplicar sobre un parque con la clausura rota sin podar primitivas que nunca
llegaron enteras.

**3. Podar contra la medición nueva, y fijar retención.** 216 hooks a rama ático, 330 módulos
`cos_lib`, 187 skills, `--help/` y `.agents/`. Desinstalar las 14 instalaciones muertas —o
marcarlas—: hoy son 14 copias de una superficie sin verificar y multiplican cualquier defecto
de la próxima barrida. Política de retención para `auto-checkpoint`, que deposita 11G en un
consumidor. Y sacar un release para reactivar la condición (d) del §2.

Reevaluación: **2026-09-15**, con los cuatro comandos del §2.

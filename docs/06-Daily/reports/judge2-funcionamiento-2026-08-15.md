# Juez 2 de funcionamiento — ¿esto funciona hoy? (2026-08-15)

> Auditoría independiente, read-only. Lente única: **¿esto arranca, compila,
> instala y satisface sus propias dependencias?** No se leyó código para opinar:
> se corrieron comandos. Cada número lleva al lado el comando que lo produjo.

- **Alcance**: repo `luum-agent-os`, rama `main`, HEAD `8602ddc70` (2026-07-28).
- **Rol**: juez, no implementador. No se editó, borró, formateó ni commiteó nada.
- **Único archivo escrito dentro del repo**: este informe. Todo lo demás
  (instalación de prueba, wrapper de timeout, scripts de evidencia) vive en el
  scratchpad.
- **Encargo ampliado dos veces en vuelo**: insumo de terceros sobre el
  instalador (§7) y mecanismo de duplicación de hooks (§8, **no verificado**).

---

## Veredicto

**Compila y arranca; instala mal.** Los cuatro toolchains cierran limpios y el
instalador termina rc=0 sin tocar el repo fuente, pero **la instalación que
produce no satisface sus propios imports**: 6 de 38 imports internos no resuelven
en el destino, dos revientan con `ModuleNotFoundError` duro, y el wrapper por el
que pasan **36 de 36 hooks** del `settings.json` instalado pierde su dependencia
`cos-root` y escribe su telemetría a `/`.

---

## Chequeo de recursos — el plan se degradó, y acá está declarado

| Medición | Comando | Resultado |
|---|---|---|
| RAM física | `sysctl hw.memsize` | 25.769.803.776 (24 GB) |
| Páginas libres | `vm_stat` | 5.627 páginas × 16 KB = **~92 MB** (más tarde 4.162 = ~68 MB) |
| Swap | `sysctl vm.swapusage` | **36.205 MB usados de 36.864 MB** (después: 36.854 de 37.888) |
| Load average | `uptime` | **16.96 / 9.53 / 7.54** → subió a **18.00** → bajó a 9.11 |
| Proceso ajeno | `ps -Ao rss,pcpu,comm -r` | un `git` al **192% CPU** — hay otra sesión escribiendo este checkout |

**Consecuencia declarada: la suite completa NO se corrió.** Con el swap al 97% y
load 18, una corrida de ~12.000 tests es la forma más rápida de que el OOM killer
decida por mí y de contaminar a la otra sesión. La dimensión "suite de tests"
queda **NO MEDIDA** en el score, no estimada. Un número inventado ahí sería
exactamente lo que este rol existe para no producir.

`timeout(1)` **no existe en este macOS** (`which timeout gtimeout` → rc=1, ambos
"not found"). Todo comando largo pasó por `scratchpad/tmo`, un wrapper de
`subprocess.run(timeout=)` que reporta rc y tiempo. Ningún número de este informe
salió de un `timeout` pelado devolviendo 127 en silencio.

---

## Score

Sobre las dimensiones **efectivamente medidas** (80 puntos de peso; la suite
queda fuera):

| Dimensión | Peso | Nota | Comando que la sostiene |
|---|---|---|---|
| Compilación / toolchains | 20 | **19/20** | `go build ./...` + `go vet ./...` rc=0 en 3 módulos; `cargo check --workspace --all-targets` rc=0; compilación Python en memoria 2.992 archivos, 0 errores. Resta 1 archivo Go sin `gofmt`. |
| Instalación desde cero | 20 | **17/20** | `bash install.sh --from <repo> --force` rc=0 en 6,4s, 1.9M, `settings.json` JSON válido, `diff` de `git status` IDÉNTICO. Baja por lo de abajo. |
| **Cierre de imports de la instalación** | 20 | **8/20** | `import_closure.py` → 38 imports internos, **6 sin resolver**, 2 sin guarda. Ejecutado: `ModuleNotFoundError` real. |
| Entrypoints | 10 | **7/10** | `bin/*` → **2 de 4** responden `--help` con rc=0. Muestreo de `scripts/` NO realizado. |
| Higiene del working tree | 10 | **4/10** | `git check-ignore -v -- '--help' '.agents'` rc=1: dos directorios generados ensucian `git status` de forma permanente. |
| Suite de tests | 20 | **NO MEDIDA** | Degradación por recursos, declarada arriba. |

**Medido: 55 / 80.** Normalizado a 100 daría 69, pero el número honesto es
*55 sobre 80 con un quinto del examen sin rendir*.

---

## 1. El misterio de `--help/` — es un bug, y está localizado

**Qué es**: un directorio literal llamado `--help` con un único árbol adentro.

```
$ find './--help' -print
./--help
./--help/.cognitive-os
./--help/.cognitive-os/metrics
./--help/.cognitive-os/metrics/ai-resource-ledger.jsonl   (1 línea)
./--help/.cognitive-os/metrics/context-budget.jsonl       (1 línea)

$ stat -f '%N | mod=%Sm | birth=%SB' -t '%Y-%m-%d %H:%M:%S' './--help'
./--help | mod=2026-07-28 22:41:16 | birth=2026-07-28 22:41:16
```

El `timestamp_epoch` de las dos filas es `1785289276.385775`, que es exactamente
el mtime del directorio: se creó de un solo golpe, con `prompt_chars: 0` y
`total_chars: 0` — es decir, con stdin vacío.

**Qué lo crea — archivo y línea**: `scripts/context_budget_meter_fast.py`.

```python
53:    project = Path(argv[1]).resolve()          # sin parseo de flags, sin validar
72:    metrics_dir = project / ".cognitive-os" / "metrics"
46:    path.parent.mkdir(parents=True, exist_ok=True)   # crea el arbol y no chista
```

No hay `argparse`, no hay `--help`, no hay chequeo de que `argv[1]` sea un
directorio. Si alguien lo invoca con `--help`, el script trata `--help` como raíz
de proyecto y **crea el directorio**.

**Reproducido en el scratchpad, no inferido**:

```
$ cd <scratchpad>/repro2 && printf '' | python3 <repo>/scripts/context_budget_meter_fast.py --help
rc=0
$ find . -print
./--help/.cognitive-os/metrics/ai-resource-ledger.jsonl
./--help/.cognitive-os/metrics/context-budget.jsonl
```

Mismo rc, mismo árbol, mismos dos archivos. Es el bug.

**Quién apretó el gatillo**: el juez anterior, con su propia auditoría. Su ítem
2.5 dice `for f in $(ls scripts/*.py | head -60); do python "$f" --help; done`, y
su informe está fechado el mismo 2026-07-28. La basura del piso es el residuo de
la auditoría que fue a buscar bugs. No lo digo como reproche: lo digo porque
explica por qué el directorio existe y por qué va a volver a aparecer cada vez
que alguien barra `scripts/*.py --help`.

**Severidad**: baja como daño, alta como señal. El daño es un directorio de 2
archivos. La señal es que un script del hot path de hooks **escribe en disco
antes de validar sus argumentos**, y con `rc=0`. Un `argv[1]` equivocado en un
contexto real escribe la telemetría en cualquier lado sin avisar — que es
exactamente lo que pasa con `cos-root` en §7.3.

## 2. `.agents/` — no es basura, es proyección legítima sin ignorar

```
$ stat -f '%N | birth=%SB' -t '%Y-%m-%d %H:%M:%S' ./.agents
./.agents | birth=2026-07-30 11:15:30      # 8 skills adentro
```

Es la proyección para el driver Codex/OpenAI, y está en el código a propósito:

- `cos_lib/paths.py:161` → `return root / ".agents" / "skills"`
- `cos_lib/paths.py:173` → *"Codex/OpenAI agents driver projection `.agents/skills/{name}/SKILL.md`"*
- `scripts/cos_init.py:1739` y `:1928` la construyen
- `tests/contracts/test_canonical_projection_behavior.py:212` la testea

**No es un bug. El bug es que no está ignorada** — igual que `--help/`:

```
$ git check-ignore -v -- '--help' '.agents'
(sin salida)   rc=1     # ninguno de los dos esta cubierto por .gitignore (145 lineas)
```

Resultado: dos directorios generados por el propio OS viven permanentemente como
`??` en `git status`. Bajo sesiones concurrentes eso es ruido que empuja hacia
`git add -A`, que es la vía más corta a mezclar trabajo ajeno en un commit.

**Decisión del operador, no mía**: `--help/` es descartable (2 archivos de
telemetría de una corrida fantasma). `.agents/` es una proyección viva — borrarla
no rompe nada pero se regenera. Lo que hay que arreglar no es el directorio, es
el `.gitignore` y el parseo de argumentos.

---

## 3. Prueba de no-mutación del repo

```
$ git status --porcelain > git-before.txt      # 10 lineas
   ... instalacion completa desde cero, compilaciones, ejecuciones ...
$ git status --porcelain > git-after.txt
$ diff git-before.txt git-after.txt
   (sin diferencias)    rc=0
```

**IDÉNTICO.** Ni el instalador ni ninguno de los comandos de esta auditoría tocó
el repo fuente. La instalación de prueba vivió íntegra en el scratchpad.

---

## 4. Compilación — pasa

| Toolchain | Comando | rc | Tiempo |
|---|---|---|---|
| Go 1.26.5, módulo raíz | `go build ./...` | **0** | 21,1s |
| Go, `cmd/cos` | `go build ./...` | **0** | 6,4s |
| Go, `cmd/cos-test` | `go build ./...` | **0** | 6,3s |
| Go, los 3 | `go vet ./...` | **0** | 2,3 / 2,6 / 1,9s |
| Rust 1.97.1 | `cargo check --workspace --all-targets` | **0** | 8,4s |
| Python 3.14.6 | compilación en memoria, 2.992 archivos | **0 errores de sintaxis** | 2,3s |

**`gofmt -l`**: 15 archivos en el módulo raíz, pero **14 de ellos están bajo
`.cognitive-os/external-source-cache/gentle-ai/`**, que tiene su propio `go.mod`
— es fuente externa cacheada, no deuda del repo. La deuda propia es **1 archivo**:
`cmd/cos-test/internal/cli/focused.go`. Coincide con lo que reportó el juez
anterior hace 18 días: no se movió.

**Trampa evitada**: `python3 -m compileall -q cos_lib scripts` devolvió rc=0 en
**0,8 segundos**. Eso no es compilar 655 archivos, es leer `__pycache__`. El
número se rehízo con un script propio que compila en memoria
(`scratchpad/pycompile.py`) sin escribir caché: 655 archivos en `cos_lib`+`scripts`
y 2.992 en todo el árbol de fuente, **0 errores**. El resultado es el mismo, pero
ahora el comando lo sostiene.

**Nota de reproducibilidad**: los tres `go build` **descargaron módulos de la
red**. La compilación no es offline-reproducible desde un checkout limpio.

**Node**: `package.json` declara 0 dependencias y 0 devDependencies, no hay
`node_modules`, y `npm test` delega en `bash tests/run-all-tests.sh`. No hay
toolchain Node real que compilar.

---

## 5. Entrypoints — 2 de 4 en `bin/`

```
$ for f in bin/*; do bash "$f" --help; done
cognitive-os.sh    rc=1   "Unknown command: --help"
cos-agent          rc=0   "cos-agent - portable sub-agent spawner (ADR-064)"
cos-errors         rc=2
cos-skill          rc=0   "Skill Runner — harness-agnostic skill discovery and invocation"
```

`bin/cognitive-os.sh` es **el `bin` declarado en `package.json`** (`"cognitive-os":
"./bin/cognitive-os.sh"`): es el comando que ve quien instala por npm, y no
entiende `--help`.

**`install.sh --help` sí funciona** (rc=0): documenta 3 perfiles, 22 harnesses y
los flags `--from/--scope/--profile/--harness/--force`. Es la mejor ayuda del repo.

**NO medido**: el muestreo de `scripts/*.py --help` (286 scripts) y de
`scripts/*.sh` (143). No se corrió — ver §9.

---

## 6. Instalación desde cero — rc=0 y coherente

```
$ cd <scratchpad>/fresh && git init -q .
$ HOME=<fakehome> COGNITIVE_OS_SKIP_MANIFEST_CHECK=true bash <repo>/install.sh --from <repo> --force
rc=0   6,4s   "Cognitive OS installed successfully"
```

| Métrica | Comando | Valor |
|---|---|---|
| Huella | `du -sh .` | **1.9M** |
| Hooks instalados | `find .cognitive-os -name '*.sh' -path '*hooks*' \| wc -l` | 76 |
| Python instalado | `find . -name '*.py' -not -path './.git/*' \| wc -l` | 48 |
| Skills proyectadas | `ls .claude/skills \| wc -l` | 9 |
| Rules | `ls .claude/rules/cos \| wc -l` | 15 |
| `settings.json` | `python3 -c "json.load(...)"` | JSON válido, **36 hooks** |

Lo que queda afuera, contado:

```
$ ls <repo>/cos_lib/*.py | wc -l          → 369 modulos upstream
$ ls fresh/.cognitive-os/cos_lib/*.py     →  39 modulos instalados
$ ls <repo>/hooks/*.sh | wc -l            → 257 hooks upstream
$ ls fresh/.cognitive-os/hooks/cos/*.sh   →  43 hooks instalados
$ ls fresh/.cognitive-os/scripts          → No such file or directory
```

Que envíe un subconjunto es una decisión de perfil, no un defecto. El defecto es
**cuál** subconjunto: el que sigue.

---

## 7. Insumo de terceros (auditoría de `FinOpenPOS`) — verificado con comando propio

> Marcado como insumo externo. **No cité ningún número suyo**: cada punto se
> re-corrió acá. Su script `check-cos-install-integrity.sh` fue **leído pero no
> ejecutado** (§9).

### La dimensión que pidieron: ¿la instalación satisface sus propios imports?

Script propio: `scratchpad/import_closure.py` (AST, read-only, exit 0/1). Recorre
los `.py` **del destino**, se queda con los imports que resuelven a un módulo del
**origen** (= internos del OS) y verifica que ese mismo módulo exista **en el
destino**.

```
$ python3 import_closure.py <fresh-install> <repo>
archivos_py_destino=48
imports_internos_del_OS=38
imports_internos_SIN_RESOLVER=6
  de esos, dentro de try/except (falla silenciosa)=4
  FALTA  hooks/cos/_lib/dispatch_gate_check.py:174 -> cos_lib.record_completion          [try/except]
  FALTA  hooks/cos/_lib/dispatch_gate_check.py:189 -> cos_lib.dispatch_model_advisor     [try/except]
  FALTA  hooks/cos/_lib/session_init_helper.py:47  -> cos_lib.user_model                 [try/except]
  FALTA  hooks/cos/_lib/session_init_helper.py:65  -> cos_lib.project_profile_bootstrap  [try/except]
  FALTA  hooks/cos/_lib/recap_adapter.py:33        -> cos_lib.harness_environment        [SIN GUARDA]
  FALTA  hooks/cos/_lib/task_panel_adapter.py:23   -> cos_lib.harness_environment        [SIN GUARDA]
rc=1
```

Los cinco módulos **existen upstream y no llegan al destino**:

```
$ for m in dispatch_model_advisor record_completion harness_environment \
           project_profile_bootstrap user_model; do
    [ -f repo/cos_lib/$m.py ] && echo "$m origen:SI destino:$([ -f fresh/.cognitive-os/cos_lib/$m.py ] && echo SI || echo NO)"
  done
dispatch_model_advisor      origen: SI   destino: NO
record_completion           origen: SI   destino: NO
harness_environment         origen: SI   destino: NO
project_profile_bootstrap   origen: SI   destino: NO
user_model                  origen: SI   destino: NO
```

Y los dos sin guarda **revientan de verdad**, no en teoría:

```
$ PYTHONPATH=fresh/.cognitive-os python3 -c "<exec_module recap_adapter.py>"
ModuleNotFoundError: No module named 'cos_lib.harness_environment'
$ ... task_panel_adapter.py
ModuleNotFoundError: No module named 'cos_lib.harness_environment'
```

**El número que pidieron: 38 imports internos, 6 sin resolver.** No es 0. Los tres
puntos del insumo **no caen**.

**Falso verde que casi produzco, y cómo lo cacé**: mi primera versión del script
aceptaba `cos_lib.record_completion` con solo encontrar el paquete `cos_lib` en el
destino, y reportó **0 sin resolver**. Era mi verificador el que estaba mal, no la
instalación. La versión final exige el módulo dotted completo. Dejo el detalle
porque el modo de fallo es genérico: un chequeo de cierre que valida el
*top-level package* siempre da verde.

### 7.1 `confidentiality.yaml` nunca llega — **CONFIRMADO**

```
$ find . -name 'confidentiality*.yaml' -not -path './.git/*'
./.cognitive-os/templates/confidentiality.yaml
$ git ls-files --error-unmatch .cognitive-os/templates/confidentiality.yaml
   → UNTRACKED
$ find <fresh-install> -name 'confidentiality*'
   .cognitive-os/cos_lib/confidentiality_scanner.py
   .cognitive-os/hooks/cos/confidentiality-enforcer.sh
   (la plantilla NO esta)
$ grep -rn 'confidentiality' install.sh scripts/cos-init.sh scripts/cos_init.py
   scripts/cos_init.py:110:  "... confidentiality-enforcer ..."     ← solo el nombre del hook
```

El consumidor **sí recibe** el hook y el scanner, y ambos buscan el archivo que
nunca llega:

- `hooks/confidentiality-enforcer.sh:77` → `CONFIG_FILE="$PROJECT_DIR/.cognitive-os/confidentiality.yaml"`
- `cos_lib/confidentiality_scanner.py:108` → `load_protected_terms(".cognitive-os/confidentiality.yaml")`

Un gate de confidencialidad instalado, activo, y sin su lista de términos: da
verde porque no tiene nada que buscar. Es el caso de libro del supresor que no
suprime nada.

**Matiz de la ampliación que NO pude cerrar**: si `.cognitive-os/templates/` está
en `.gitignore` (es decir, si es estado de runtime efímero por diseño), entonces
el arreglo no es `git add` sino mover la plantilla a una ruta versionada que el
instalador pueda leer. **No verifiqué el estado de ignore de ese directorio.** La
conclusión (la plantilla no llega) no cambia; la recomendación sí depende de eso.

### 7.2 Módulos descartados en silencio — **CONFIRMADO con corrección**

Son **5**, no ~8, entre los alcanzables desde el payload instalado. Y el caso peor
declarado por ellos **no es el caso peor real**:

- El par `circuit_breaker` / `record_completion` **no tiene la forma descrita**:
  `cos_lib/circuit_breaker.py` importa únicamente `cos_lib.time_utils`, que **sí
  se instala**. El `try` que contiene `record_completion` está en
  `dispatch_gate_check.py:174`, y ahí la ausencia es silenciosa — pero es un
  `except: pass`, degradación, no una feature muerta demostrada.
- El caso peor real es **`harness_environment`**: ausente, importado **sin guarda**
  por dos archivos, `ModuleNotFoundError` duro y verificado por ejecución.

**Atenuante que hay que decir**: `recap_adapter.py`, `task_panel_adapter.py` y
`dispatch_gate_check.py` **no los invoca nada en el destino** (`grep -rn` sobre
`.cognitive-os` y `.claude` de la instalación fresca). O sea: el instalador envía
tres archivos Python que no pueden importar y que nadie llama. El único de los
cuatro que sí corre es `session_init_helper.py`, desde
`hooks/cos/session-init.sh:276`, y con **doble silencio**: `try/except: pass` en
Python y `2>/dev/null || true` en bash. Su rc directo es 0 y no imprime nada.

Impacto neto en runtime: en toda instalación de consumidor, la carga del
`user_model` y el bootstrap del perfil de proyecto **nunca ocurren**, y nada lo
reporta.

**Parte del relato causal que NO se sostiene**: el "`lib/` vestigial". En el
origen no existe `lib/` (`ls -d lib` → No such file or directory) y en la
instalación fresca tampoco (`ls -d .cognitive-os/lib` → idem). En una instalación
**limpia** ese mecanismo no aplica; a lo sumo aplicaría sobre un upgrade encima de
un layout viejo, que no probé.

### 7.3 `cos-root` falta junto al wrapper — **CONFIRMADO y peor de lo declarado**

```
$ find <repo> -name 'cos-root' -not -path '*/.git/*'
  <repo>/scripts/cos-root                      ← existe en el origen
$ find <fresh-install> -name 'cos-root*'
  (nada)                                       ← no llega al destino
$ grep -rln 'cos-root' <fresh-install>
  .cognitive-os/hooks/cos/_lib/hook-timing-wrapper.sh
$ grep -n 'cos-root' .cognitive-os/hooks/cos/_lib/hook-timing-wrapper.sh
  65:PROJECT_DIR="$("$SCRIPT_DIR/cos-root" project)"
```

Ejecutado end-to-end con un hook real de la instalación:

```
$ printf '{"session_id":"t"}' | bash .cognitive-os/hooks/cos/_lib/hook-timing-wrapper.sh \
      SessionStart .cognitive-os/hooks/cos/session-sanity.sh
hook-timing-wrapper.sh: línea 65: .../hooks/cos/_lib/cos-root: No such file or directory
hook-timing-wrapper.sh: línea 370: /.cognitive-os/metrics/hook-timing.jsonl: No such file or directory
rc=0
$ ls -la .cognitive-os/metrics/
total 0        ← vacio
```

Lo que esto significa, medido:

1. **El wrapper no rompe la cadena** (rc=0): el hook igual corre. Bien.
2. **Dos líneas de error en stderr en cada invocación de cada hook.**
3. `PROJECT_DIR` queda **vacío** → `METRICS_DIR=/.cognitive-os/metrics`,
   `RUNTIME_DIR=/.cognitive-os/runtime`, y `GOVERNANCE_PROJECT_DIR=""` (línea 379).
   Los `|| true` y `2>/dev/null` de las líneas 71 y 370 se tragan todo.
4. **La telemetría de hooks se pierde al 100% en todo consumidor.** El propósito
   declarado del archivo en su propio encabezado —*"records per-invocation hook
   timing"*— no ocurre nunca fuera del repo de mantenimiento.
5. **Alcance: 36 de 36.** Los 36 comandos de hook del `settings.json` instalado
   pasan por este wrapper (`grep -c 'hook-timing-wrapper'` sobre los `command`
   extraídos del JSON → 36/36).

Por qué nadie lo vio: en el origen `hook-timing-wrapper.sh` y `cos-root` son
hermanos en `scripts/`, así que **para el mantenedor funciona perfecto**. Se rompe
solo del otro lado del instalador.

**Raíz común que propone el insumo — la comparto, con una precisión**: el
instalador envía una lista permitida y **nunca valida que lo enviado satisfaga sus
propios imports ni sus propias dependencias de path**. La precisión es que no hace
falta invocar un `lib/` vestigial para explicarlo: alcanza con que no exista
ningún chequeo de cierre. El script de §7 tarda 0,2 segundos; podría correr al
final de cada `install.sh`.

---

## 8. Duplicación de registraciones de hooks (98 vs 47) — **NO VERIFICADO**

La segunda ampliación pide encontrar el mecanismo de merge que acumula
registraciones entre upgrades, con el lead de que el camino estaría en
`scripts/_lib/settings-driver-claude-code.sh` y no en `apply-efficiency-profile.sh`.

**Lo único que verifiqué**: el archivo existe, tiene **614 líneas**
(`wc -l scripts/_lib/*.sh`), y es el más grande de los cinco drivers (`bare` 199,
`codex` 228, `opencode` 273). **No lo leí.** El presupuesto de llamadas del
sub-agente se agotó antes (§9).

Dato propio que sí puedo aportar y que acota la búsqueda: **el `settings.json` de
una instalación fresca tiene 36 registraciones, no 47 ni 98.** Ese es el número de
partida limpio del perfil `default` en este HEAD. Cualquier medición de
duplicación debería compararse contra 36, no contra 47.

No corrí `apply-efficiency-profile.sh` en ningún lado, como se indicó.

---

## 9. VERIFICADO vs NO VERIFICADO

### Verificado (comando propio, corrido hoy)

- Estado de recursos y degradación del plan.
- `--help/`: qué es, qué lo crea (`scripts/context_budget_meter_fast.py:53`), reproducido.
- `.agents/`: proyección legítima (`cos_lib/paths.py:161`), sin ignorar.
- Ninguno de los dos está cubierto por `.gitignore`.
- No-mutación del repo: `diff` idéntico.
- Go build + vet en 3 módulos; `gofmt -l` = 1 archivo propio.
- `cargo check --workspace --all-targets` rc=0.
- 2.992 archivos Python sin errores de sintaxis (compilación en memoria, no caché).
- Instalación desde cero rc=0, huella, conteos, JSON válido.
- Cierre de imports: 38 internos, 6 sin resolver, 2 duros, ejecutados.
- Los 5 módulos ausentes, presentes upstream.
- `confidentiality.yaml` untracked, ausente del destino, no referenciada por el instalador.
- `cos-root` ausente del destino; wrapper ejecutado; `metrics/` vacío; 36/36 hooks afectados.
- `bin/*` → 2 de 4 responden `--help` con rc=0.

### NO verificado (y por qué)

| Ítem | Motivo |
|---|---|
| **Suite completa de pytest** | Máquina ahogada (swap 97%, load 18, otra sesión activa). Decisión declarada, no omisión. |
| Honestidad del verde (skips, tests sin assert) | Depende de la corrida anterior. |
| Sintaxis de los 257 hooks (`bash -n`) y ejecución con payload mínimo | Presupuesto de llamadas agotado. |
| Muestreo `--help` de 286 `scripts/*.py` y 143 `.sh` | Ídem. Es el barrido que creó `--help/`; debe correrse con `cwd` fuera del repo. |
| `check-cos-install-integrity.sh` de terceros | **Leído, no ejecutado.** Ver nota abajo. |
| Mecanismo de duplicación 98/47 en el driver de settings | Archivo localizado (614 líneas), no leído. |
| Desajuste de layout de `apply-efficiency-profile.sh` | No verificado. |
| ¿`.cognitive-os/templates/` está en `.gitignore`? | Cambia la recomendación de §7.1, no la conclusión. |
| Falsación del punto 3 (orden import/llamada del breaker en el origen) | No hecha. |
| Upgrade sobre instalación previa (el `lib/` vestigial) | Solo probé instalación limpia. |

**Sobre el script de terceros, leído línea por línea**: hace lo que dice — es
read-only (`git ls-files`, `grep`, `find`), usa `/usr/bin/grep` a propósito
(línea 27) y devuelve 0/1/2. Dos observaciones de método, sin haberlo corrido:

- Su chequeo 2 (líneas 86-88) extrae módulos con `grep -rhoE` sobre **texto**, no
  AST. Cuenta ocurrencias en comentarios y strings, y se pierde los `import a.b as
  c`. Mi chequeo por AST y el suyo por regex miden cosas parecidas pero no iguales;
  si difieren, el desacuerdo es de método, no de hallazgo.
- Su chequeo 3 (líneas 116-120) prueba una **condición de coexistencia**
  (`circuit_breaker` presente + `record_completion` ausente), no que el breaker
  quede inalcanzable. Como está escrito, daría "DEFECT" incluso si el orden de
  import/llamada hiciera que el breaker se alcance igual. Es la crítica que la
  propia ampliación anticipa, y la comparto.

**Contaminación respetada**: no medí nada sobre `FinOpenPOS`. Todo lo de §7 sale
de una instalación fresca hecha por mí en el scratchpad, que no tiene reparaciones
de nadie encima.

---

## 10. Correcciones a las premisas del encargo

| Premisa | Recuento | Veredicto |
|---|---|---|
| "`--help/` y `.agents/` son dos carpetas untracked con nombre sospechoso" | `find` + `stat` + `cos_lib/paths.py:161` | **Mitad y mitad.** `--help/` es basura de un bug. `.agents/` es una proyección legítima y documentada; su único defecto es no estar ignorada. |
| "olfatea a `mkdir --help` con el flag mal pasado" | `scripts/context_budget_meter_fast.py:46,53,72` | **Casi.** No es `mkdir` mal invocado: es un `mkdir(parents=True)` de Python sobre un `argv[1]` sin parsear. La intuición del mecanismo era correcta, el binario no. |
| "toolchains: Python, Go, Rust, Node" | `ls`, `package.json` | **Node es nominal.** 0 dependencias, 0 devDependencies, sin `node_modules`; `npm test` delega en bash. No hay build Node que verificar. |
| "sos el único autorizado a correr la suite completa" | `sysctl vm.swapusage`, `uptime` | **Autorizado sí, prudente no.** Con swap al 97% y otra sesión escribiendo el checkout, correrla habría producido un resultado no atribuible al repo. No la corrí. |
| "timeout en todo" | `which timeout gtimeout` → rc=1 | **`timeout(1)` no existe acá.** Confirmo lo que ya había reportado el juez anterior: `timeout N cmd` devuelve 127 con salida vacía, indistinguible de "sin hallazgos". Usé un wrapper propio. |

## 11. Correcciones al juez anterior (`judge-funcionamiento-2026-07-28.md`)

Leído para saber dónde mirar. Ningún número suyo se cita sin re-correr.

| Su afirmación | Hoy | Veredicto |
|---|---|---|
| "Instalación desde cero — **PASA**" (19/20) | rc=0, 1.9M, 76 hooks, JSON válido | **Se sostiene en la superficie, y es donde su lente se quedó corta.** Verificó que el instalador *termina bien*; no verificó que lo instalado *pueda importarse*. Con esa dimensión agregada, 19/20 pasa a 17/20 + una dimensión nueva en 8/20. |
| "`bin/`: **4/4 rc=0**" (ítem 2.1) | `bash bin/cognitive-os.sh --help` → **rc=1**; `bin/cos-errors --help` → **rc=2** | **NO se sostiene.** Hoy son **2 de 4**. Su propio informe menciona un "falso positivo que casi reporto" sobre `cos-errors`, lo que sugiere que contó como OK algo que devuelve rc≠0. |
| "1 archivo Go sin `gofmt`" | `gofmt -l` → 1 propio (`cmd/cos-test/internal/cli/focused.go`) + 14 en caché externo | **Se sostiene**, y sigue igual 18 días después. |
| "`compileall` rc=0 sobre 5103 archivos" | `compileall` cierra en **0,8s** = caché | **El rc es correcto, el comando no lo sostiene.** Rehecho en memoria: 2.992 archivos de fuente, 0 errores. |
| "suite: 11.820 passed / 23 failed / 74 skipped en 715s" | no re-corrida | **NO REFUTADO NI CONFIRMADO.** Tiene 18 días y 0 commits nuevos encima (HEAD sigue siendo el de su época + un merge). Sin re-correr, no lo firmo. |
| "hooks 4/15 — el rubro donde el sistema se miente a sí mismo" | §7.3 | **Se queda corto.** Encontró guardrails vacuos; no vio que el wrapper por el que pasan **todos** los hooks pierde su dependencia en el destino y tira la telemetría a `/`. |
| "`--help/`" | — | **No lo reportó, y lo creó su propia corrida** (ítem 2.5, mismo día, 22:41). |

**Veredicto sobre el juez anterior**: su método es sólido y su hallazgo del
`timeout` fantasma es correcto y valioso. Su límite es que auditó el **origen**
—compila, arranca, testea— y nunca miró el **destino**. Todo lo que se rompe en
§7 es invisible desde adentro del repo.

---

## 12. Nota: los hooks del propio repo me bloquearon dos veces

No es el encargo, pero es funcionamiento observado y afecta a cualquier agente:

1. **`hooks/protected-config-write-guard.sh`** bloqueó un comando que escribía un
   script **en el scratchpad**, porque el texto del comando contenía la cadena
   `hooks/cos/_lib`. Hace *substring match sobre el texto del comando*, no sobre
   el destino real de la escritura. Falso positivo: un archivo read-only en `/tmp`
   que apenas menciona la ruta queda bloqueado. Tuve que rodearlo escribiendo con
   otra herramienta.
2. **`hooks/subagent-budget-enforcer.sh`** bloqueó a las 51 llamadas sobre un
   presupuesto de 50. El bloqueo es correcto según su regla; el problema es que el
   encargo se amplió dos veces **después** de lanzado sin ampliar el presupuesto.

---

## 13. Cierre: las tres acciones, en orden

**1. Poner `cos-root` junto al wrapper, o resolver `PROJECT_DIR` sin él.**
Es el de mayor alcance: 36/36 hooks de toda instalación de consumidor, telemetría
perdida al 100%, dos líneas de stderr por invocación. El wrapper ya conoce
`COGNITIVE_OS_PROJECT_DIR` / `CLAUDE_PROJECT_DIR` (líneas 21-23 de su propio
encabezado) — usar el fallback antes que `cos-root` sería un arreglo de una línea.

Prueba de que quedó hecho:
```bash
cd <install-fresca> && printf '{}' | bash .cognitive-os/hooks/cos/_lib/hook-timing-wrapper.sh \
    SessionStart .cognitive-os/hooks/cos/session-sanity.sh 2>&1 | grep -c 'No such file'
# esperado: 0
test -s .cognitive-os/metrics/hook-timing.jsonl && echo "telemetria OK"
```

**2. Hacer que `install.sh` valide su propio cierre de imports antes de declarar éxito.**
No es "agregar los 5 módulos que faltan": es que el instalador no pueda volver a
enviar un payload que no se satisface a sí mismo. El chequeo tarda 0,2s.

Prueba de que quedó hecho:
```bash
python3 <scratchpad>/import_closure.py <install-fresca> <repo>; echo "rc=$?"
# esperado: imports_internos_SIN_RESOLVER=0, rc=0
```
(Y el mismo script, incorporado al repo, corriendo al final de `install.sh`.)

**3. Parsear argumentos en `scripts/context_budget_meter_fast.py` y cubrir ambos directorios en `.gitignore`.**
El bug de §1 escribe en disco antes de validar `argv[1]`. Es chico como daño y
grande como clase: es el mismo modo de fallo que `cos-root` — una ruta mal
resuelta que se escribe en silencio con rc=0.

Prueba de que quedó hecho:
```bash
cd $(mktemp -d) && printf '' | python3 <repo>/scripts/context_budget_meter_fast.py --help; echo "rc=$?"
ls -A   # esperado: vacio, y rc distinto de 0 (o ayuda impresa)
cd <repo> && git check-ignore -q -- '--help' '.agents' && echo "ambos ignorados"
```

---

### Anexo — artefactos de esta auditoría (scratchpad, no versionados)

| Archivo | Qué hace |
|---|---|
| `tmo` | Wrapper de timeout (`subprocess.run(timeout=)`), reporta rc y tiempo. Suple el `timeout(1)` ausente. |
| `pycompile.py` | Compila `.py` en memoria sin escribir `__pycache__`. exit 0/1. |
| `import_closure.py` | Cierre de imports origen→destino por AST. exit 0/1. **El de mayor valor: debería vivir en el repo.** |
| `fresh/` | Instalación limpia usada para todo §6 y §7. |
| `git-before.txt` / `git-after.txt` | Prueba de no-mutación. |

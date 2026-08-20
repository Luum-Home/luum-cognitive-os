# La ausencia afirmada desde una vista parcial — 2026-08-20

> Censo estático. No se corrió la suite: el único pytest que se ejecutó fue el
> proof nuevo, `tests/red_team/portability/test_locate_primitive.py` (7 tests,
> 0.58 s).

## Resumen ejecutivo

- **Censo 1 — afirmaciones de ausencia.** Población barrida: 39 comentarios de
  `hooks/*.sh` + `scripts/*.sh` y 20 líneas de `rules/*.md` con vocabulario de
  ausencia. La mayoría son *guardas* ("skip if file does not exist"), no
  afirmaciones. Se verificaron **7 afirmaciones vivas**: 6 verdaderas, **1
  falsa** — y la falsa es la peor posible.
- **La falsa:** `templates/agent-mandatory-rules.md` le decía a **cada
  sub-agente** que siete hooks "existen pero NO están registrados". Los ocho
  hooks nombrados están registrados hoy en `.claude/settings.json`. Corregido en
  este commit, con el comando que lo comprueba adentro del propio texto.
- **Censo 2 — skips condicionales.** Población: **620 sitios de skip** (614
  condicionales + 6 incondicionales). Clase artefacto: 358. El instrumento pudo
  decidir sobre **202**; el resto es ceguera declarada, no cero.
- **Se disparan hoy: 8 confirmados.** Cuatro por un hook borrado, **tres por
  buscar en el lugar equivocado**, uno por un binario opcional legítimo.
- **Los tres del lugar equivocado** (`tests/chaos/`) buscan `lib/rate_limiter.py`
  y `lib/guardrails_validators.py`; el repo los tiene en `cos_lib/` — y uno de
  los dos es a su vez symlink a `packages/quality-gates/lib/`.
- **Sí, escribí el comando:** `scripts/locate_primitive.py` contesta "¿dónde vive
  X?" siguiendo symlinks, con proof pareado y sonda de falsación.

## Correcciones a las premisas del encargo

1. **"377 skipped sobre 24.280 veredictos" no se pudo confirmar ni usar.** No hay
   artefacto de esa corrida en el repo: no existe junit XML ni `report.json`
   (`find . -maxdepth 3 -name '*junit*' -o -name 'report*.json'` → vacío). El
   número del encargo es relatado; todo lo que sigue se mide estáticamente sobre
   el código de los tests, no sobre esa corrida. Los 620 sitios de skip **no son
   comparables** con 377 skips ejecutados: un `skipif` parametrizado produce N
   veredictos y un sitio nunca alcanzado produce 0.
2. **"Contá los `pytest.skip`" subcuenta la población.** Un grep de call-sites da
   616; el AST da **620** e incluye `skipif` con la condición en keyword. Más
   importante: 6 son `pytest.mark.skip` **incondicionales** — tests apagados a
   mano, que el encargo no pidió y que son la forma extrema del mismo problema.
3. **`hooks/_lib/file_checker.sh` ya existe** y el encargo no lo menciona.
   Contesta "¿existe *este path*?" resolviendo symlinks — no contesta "¿dónde
   vive X?". La brecha era real, pero es más chica que "no hay nada".
4. **El propio localizador cometió la Capa 1 en su primera versión.** Podaba
   `.cognitive-os/`, y el primer censo reportó `hook-timing.jsonl` (7 MB, escrito
   hoy) y `agent-verification.jsonl` como ausentes. Tres "ausencia_real" eran
   falsas por la misma causa que persigue el encargo: barrer menos árbol del que
   dice la conclusión. Corregido, con test que lo fija.
5. **"El tercer número es el hallazgo" — es el hallazgo, pero no es el más
   grande.** Los skips por ruta equivocada son 3. Los que se disparan por un
   artefacto *borrado del repo* son 4, en un solo archivo, y dejan una feature
   entera sin cobertura ejecutada.
6. **Commitear en `main` está bloqueado y no me auto-concedí el bypass** (regla
   7 del encargo). Ver `## Lo que NO verifiqué y por qué`.

## Capa 1: afirmaciones de ausencia, y las que verifiqué

Población y cómo se barrió:

```bash
grep -rniE "^[[:space:]]*#.*(does not exist|doesn't exist|no existe|not found|is missing|not registered|sin registrar|nunca dispara|never fires)" hooks/*.sh scripts/*.sh | wc -l   # 39
grep -rniE "(no existe|does not exist|nunca (se )?dispar|never fires|not registered|sin registrar|no longer exists)" rules/*.md | wc -l                                             # 20
```

De esas, la mayoría **narra una guarda**, no afirma una ausencia:
`# Skip if file does not exist` describe una rama de código y es correcto. Se
verificaron sólo las que son **premisa viva**: cabecera de hook activo, regla
cargada, o texto inyectado en el contexto de un agente.

| # | Afirmación | Dónde | Verificación | Veredicto |
|---|-----------|-------|--------------|-----------|
| 1 | "7 reglas cuyo hook existe pero NO está registrado" | `templates/agent-mandatory-rules.md:94` | conteo sobre `hooks` de `settings.json`: 8/8 con ≥1 comando | **FALSA** |
| 2 | "`rate-limiter.sh` no está registrado" | `rules/rate-limiting.md:10` | mismo comando → `0` | verdadera |
| 3 | "NOT registered in settings.json — operator decision" | `hooks/session-end-cleanup.sh:6` | mismo comando → `0` | verdadera |
| 4 | "sourced library helper — not registered independently" | `hooks/orchestrator-mode-detect.sh:3` | `grep -c` → `0` | verdadera |
| 5 | "`response-length-check.sh` does NOT exist on disk" | `rules/ROADMAP.md:104` | `locate_primitive.py` → exit 1 | verdadera |
| 6 | "`context-budget.sh` does NOT exist on disk" | `rules/ROADMAP.md:111` | `locate_primitive.py` → exit 1 | verdadera |
| 7 | "`flock` NO EXISTE EN macOS" | `hooks/session-init.sh:143`, `session-cleanup.sh:247` | `command -v flock/timeout/gtimeout` → los tres ausentes | verdadera |

El comando que mata la #1, y que quedó escrito dentro del propio template:

```bash
python3 -c 'import json,re,sys; print(len(re.findall(re.escape(sys.argv[1]), \
json.dumps(json.load(open(".claude/settings.json")).get("hooks",{})))))' confidence-gate.sh
# 1  → registrado. rate-limiter.sh → 0. session-end-cleanup.sh → 0.
```

Por qué la #1 es la peor de la lista y no una más: viaja en el preámbulo que
`templates/agent-mandatory-rules.md` inyecta en **todos** los sub-agentes. Un
falso "ningún hook te va a frenar" no deja rastro cuando es mentira — el agente
que se relaja no falla, simplemente no fue frenado por un gate que sí estaba
mirando. `rules/ROADMAP.md` Sección 1 marca las siete como RESOLVED desde el
commit 92cf485; el template quedó atrás y nadie lo miró porque *afirmar una
ausencia sale gratis*.

**Lo que NO se verificó, dicho como número:** las 39 + 20 líneas menos las 7
verificadas quedan **sin verificar**, y las que están en informes fechados de
`docs/06-Daily/reports/` se declaran registro histórico, no premisa viva.

## Capa 2: los skips condicionales, con el desglose de cuatro

Instrumento: `scripts/skip_absence_census.py` (AST, sin correr la suite).

```bash
python3 scripts/skip_absence_census.py
```

```
POBLACIÓN: 620 sitios de skip en tests/ y packages/*/tests/
  artefacto        358      otra             131
  dep_opcional      52      entorno           36
  servicio          31      plataforma         6
  incondicional      6
ARTEFACTO — resolución:
  presente_en_ruta     192     ambiguo_basename      98
  sin_literal           42     mixto_a_verificar     13
  ausencia_real          7     fuera_del_repo         4
  otra_ubicacion         2
```

El desglose pedido, con el denominador pegado a cada número:

| Pregunta | Respuesta | Denominador |
|---|---|---|
| skips condicionales totales | **614** | 620 sitios − 6 `mark.skip` incondicionales |
| cuántos se disparan HOY | **8 confirmados** | sobre **202 medibles**; 192 confirmados que NO se disparan |
| …de ésos, por artefacto que existe en otro path | **3** | verificados uno por uno |
| …por artefacto genuinamente ausente | **4** | un hook borrado del repo |
| …por dependencia opcional legítima (no es hallazgo) | **1** | `pg_ctl` |

Ceguera declarada, porque un cero bajo ceguera no es un hallazgo: **153 sitios de
clase artefacto** que el instrumento no pudo decidir (98 basename suelto sin
directorio reconstruible, 42 sin literal, 13 con literales en desacuerdo), más
**131** de clase `otra` cuya condición no nombra artefacto, más 4 rutas que
cuelgan del HOME del operador.

Las clases que **no** son hallazgo, y por qué: `plataforma` (6) y `dep_opcional`
(52, incluidos los 3 `importorskip`) declaran una dependencia opcional o un
sistema operativo — un skip que no se dispara en esta máquina es correcto, no
deuda. `entorno` (36) y `servicio` (31) dependen de variables y de daemons; ahí
la pregunta "¿se dispara hoy?" no tiene respuesta estática.

**Los 6 `pytest.mark.skip` incondicionales** son la forma extrema: no declaran
ninguna condición, siempre se saltean, y ninguna herramienta los va a ver como
rojo. No los triamos: quedan como deuda anotada.

## Los skips que buscan en el lugar equivocado

Tres, todos en `tests/chaos/` (área ajena en esta sesión: se reportan, no se
tocan). La unión exacta de las dos capas — un test que afirma una ausencia
mirando un solo path:

| Sitio | Busca | Vive en | Efecto |
|---|---|---|---|
| `tests/chaos/test_reinvention_check_fires.py:74` | `lib/rate_limiter.py` | `cos_lib/rate_limiter.py` | siempre skip |
| `tests/chaos/test_reinvention_check_fires.py:100` | `lib/rate_limiter.py` | `cos_lib/rate_limiter.py` | siempre skip |
| `tests/chaos/test_guardrails_validator_exercised.py:114` | `lib/guardrails_validators.py` | `cos_lib/guardrails_validators.py` → symlink a `packages/quality-gates/lib/` | siempre skip |

```bash
grep -n '_PROJ_ROOT\|_EXISTING_MODULE\|_VALIDATORS_LIB' tests/chaos/test_reinvention_check_fires.py tests/chaos/test_guardrails_validator_exercised.py
# _PROJ_ROOT = Path(__file__).resolve().parent.parent.parent   → la raíz del repo
# _EXISTING_MODULE = _PROJ_ROOT / "lib" / "rate_limiter.py"
ls -d lib            # ls: lib: No such file or directory
python3 scripts/locate_primitive.py rate_limiter.py --exact   # cos_lib/rate_limiter.py
```

El detalle que lo vuelve doctrina y no anécdota: el docstring del propio test
dice *"(which exists in the real project)"*. El autor sabía que el módulo existe.
Escribió la ruta equivocada, el `skipif` la creyó, y el test se apagó sin que
nadie viera un rojo.

### El hallazgo más grande: un hook borrado con cuatro tests todavía verdes

```bash
python3 scripts/locate_primitive.py lazy-catalog-injector.sh   # NO ENCONTRADO, exit 1
git log --diff-filter=D --oneline -- '*lazy-catalog-injector.sh'
# 05defb674 fix: integrate validated 86ef repairs
```

`tests/integration/test_lazy_catalog_end_to_end.py` líneas 88, 99, 111 y 122
tienen `@pytest.mark.skipif(not INJECTOR.exists(), reason="lazy-catalog-injector.sh not found")`.
El archivo se borró en `05defb674`. Los cuatro tests se saltean siempre desde
entonces: cuatro tests que no existen, con formato de suite verde, sobre la
feature de lazy-loading del catálogo.

### Ambiguos, declarados como tales

- `tests/unit/test_doc_sync.py:45` — `.cognitive-os/metrics/stale-docs.jsonl` no
  existe en esta máquina. No se pudo distinguir "el productor nunca corrió" de
  "el productor no existe". Queda a triar.
- `tests/unit/test_kpi_collector.py:414` — **falso positivo del censo**: el
  `test.jsonl` que extrajo es un fixture de `tmp_path`. Lo verifiqué leyendo el
  archivo. La causa es la expansión de nombres del instrumento, que arrastra
  asignaciones no relacionadas; está anotada en el código.

## El comando para preguntar dónde vive algo, si lo escribí

Sí: **`scripts/locate_primitive.py`**. No existía un comando canónico para "¿dónde
vive X?". Lo más cercano era `hooks/_lib/file_checker.sh`, que contesta otra
pregunta: "¿existe *este path*, resolviendo su symlink?".

```bash
python3 scripts/locate_primitive.py metrics-rotation.sh
# ENCONTRADO: metrics-rotation.sh
#   file  hooks/metrics-rotation.sh  -> .../packages/context-optimization/hooks/metrics-rotation.sh
#   file  packages/context-optimization/hooks/metrics-rotation.sh
#   (2 rutas, 1 artefacto(s) real(es): hay symlinks)
ls scripts/metrics-rotation.sh
# ls: scripts/metrics-rotation.sh: No such file or directory     ← el error de hoy
```

Contrato: exit **0** encontrado / **1** ausente / **2** error de uso; `--json`
para consumo; dedup por destino real (symlink y target cuentan como UN
artefacto); marca los symlinks rotos como **presencia con destino muerto**, no
como ausencia — confundir las dos es cómo se borra un consumidor vivo; y consulta
`$PATH` por si "X" era un binario.

Proof pareado en `tests/red_team/portability/test_locate_primitive.py` (7 tests,
0.58 s), **sin un solo skip condicional adentro**, a propósito. Su sonda de
falsación es el caso del symlink a un paquete, con las dos mitades que importan:
que el localizador **lo encuentre**, y que el `ls` de un solo path **no lo
encuentre** — sin la segunda mitad el proof no demuestra que el instrumento
aporte algo sobre el que ya falló.

```bash
.venv/bin/pytest tests/red_team/portability/test_locate_primitive.py -q
# 7 passed in 0.58s
```

Cobertura del proof, además del caso vivo: symlinks de directorio
(`cos_lib/harness_adapter`), dedup por destino real, symlink roto, ausencia
genuina, los tres exit codes, y **que `.cognitive-os/` no se pode** — el error
que este mismo script cometió en su primera versión.

## Lo que NO verifiqué y por qué

- **La corrida de 24.280 veredictos.** No se corrió la suite (máquina cargada,
  tres agentes). Todo el Censo 2 es estático: dice qué condición tiene cada skip
  y si su artefacto existe, **no** qué pasó en una corrida.
- **153 sitios de clase artefacto ciegos** + 131 de clase `otra` + 36 `entorno` +
  31 `servicio`. Para éstos, "no se dispara" no fue afirmado: fue declarado no
  observado.
- **52 sitios `dep_opcional` y 6 `plataforma`** se dieron por correctos por
  categoría, sin verificar uno por uno que la dependencia esté realmente
  declarada como opcional en `pyproject.toml`.
- **~52 líneas de vocabulario de ausencia sin verificar** (39 + 20 menos las 7
  verificadas, con solape). Se priorizaron caminos ejecutables.
- **Los 6 `mark.skip` incondicionales** no se triaron uno por uno.
- **`tests/chaos/**`, `hooks/edit-lock-pre-tool.sh`, `hooks/session-init.sh`,
  `manifests/state-retention.yaml`** y demás rutas ajenas: sólo lectura.
- **Deuda de documentation-truth (ADR-277).** La corrección al template es
  puntual y **no** se agregó su claim a
  `manifests/documentation-truth-claims.yaml`: el esquema exige `source_reports`
  y superficie de escaneo, y tocarlo a ciegas es cómo se instala un supresor que
  no suprime nada. Queda como deuda explícita, que es la opción (b) de la regla
  16: *un claim sobre el registro de hooks en `settings.json`, con el comando
  del template como productor*.
- **Nada de esto quedó commiteado, y no es un olvido.** `destructive-git-blocker`
  (ADR-055b) bloquea `git commit` en `main` **y también** `git worktree add`, que
  era la salida sin tocar el HEAD compartido. Las dos rutas que quedan piden el
  token inline `# --allow-destructive`, y el encargo prohíbe explícitamente
  auto-concederse el bypass. `scripts/cos-session-branch.sh --slug
  ausencia-afirmada` se rechazó por worktree sucio (hay tres sesiones
  concurrentes escribiendo). Los cinco archivos quedan en el árbol de trabajo:

  ```
   M templates/agent-mandatory-rules.md
  ?? scripts/locate_primitive.py
  ?? scripts/skip_absence_census.py
  ?? tests/red_team/portability/test_locate_primitive.py
  ?? docs/06-Daily/reports/la-ausencia-afirmada-desde-una-vista-parcial-2026-08-20.md
  ```

  Mensaje de commit redactado y esperando en el scratchpad de la sesión
  (`msg-ausencia.txt`). **Riesgo concreto**: un `git add -A` de otra sesión los
  arrastra a un commit ajeno. El operador decide: token inline, o
  `cos-session-branch.sh --allow-dirty`.
- **Escritura de telemetría ajena.** Al correr el proof, el guard de la suite
  reportó `+107 bytes` en `.cognitive-os/metrics/push-collision-detect.jsonl`.
  No lo escribieron mis tests (no tocan esa ruta); hay una sesión concurrente
  pusheando. No se investigó.

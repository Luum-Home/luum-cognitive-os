# Retiro de graphify — NO EJECUTADO (mandato refutado)

- **Fecha:** 2026-08-15
- **Encargo:** retirar graphify del repo, con autorización explícita del operador.
- **Resultado:** **cero archivos borrados.** La evidencia de muerte no reproduce.
- **Regla aplicada:** «si algo de esto no reproduce, PARÁ y reportá». Falló más de un dato.

---

## 1. Veredicto

El encargo autorizaba borrar algo **muerto**. graphify no está muerto: está
**partido en dos mitades con estado distinto**, y el informe que fundamentó el
retiro midió sólo la mitad muerta y generalizó al conjunto.

| Mitad | Qué es | Estado real |
|---|---|---|
| **Build** | `scripts/cos-graphify-build` | **Inerte en este checkout.** Es el único script que necesita el binario `graphify`, y `command -v graphify` → `ABSENT`. |
| **Medición** | los otros 7 scripts | **Vivos y corriendo.** Python puro, sin binario. Dos están cableados a un target de `make` que los ejecuta hoy. |

Retirar el conjunto por la evidencia de la primera mitad habría borrado
tooling que corre, pasa y publica reportes.

---

## 2. La refutación, dato por dato

Cada afirmación del encargo, recontada con su comando.

### 2.1 «Cero invocaciones en runtime» — **FALSO**

El encargo afirma que el único hit no-test es `hooks/so-impact-eval-trigger.sh:56-57`
usando las cadenas como patrones de path. Hay más, y son invocaciones reales:

```
$ git grep -in graphify -- Makefile
Makefile:81:	@python3 -m pytest ... tests/unit/test_cos_graphify_token_reduction_smoke.py tests/unit/test_cos_graphify_context_replay_benchmark.py ...
Makefile:84:	@python3 scripts/cos-graphify-token-reduction-smoke --reset >/dev/null
Makefile:85:	@python3 scripts/cos-graphify-context-replay-benchmark lib/harness_adapter/base.py >/dev/null
Makefile:89:	@echo "[test-agentic-mastery] Reports: ... graphify-token-reduction-smoke-report.md, graphify-context-replay-benchmark.md ..."
```

`make test-agentic-mastery` **ejecuta dos scripts de graphify** y declara sus
reportes como entregable del target. Eso no es un patrón de path: es una llamada.

El target está documentado como procedimiento vigente en cuatro lugares
(`docs/04-Concepts/architecture/agentic-mastery-operations.md:10` y `:115`,
`docs/09-Quality/manual-tests/agentic-mastery.md:16`,
`docs/06-Daily/reports/agentic-mastery-validation-2026-05-02.md:20`).

Hay además un segundo consumidor vivo, no mencionado en el encargo:

```
$ git grep -n graphify -- fixtures/
fixtures/so-impact/money-format-refactor/tools/simulated_agent_workflow.py:33:
  elif MODE in {"full-so", "full-so-minus-process-loop", "full-so-minus-graphify",
                "context-token-optimization-only", "graphify-only"}:
```

graphify es una **dimensión del harness de so-impact-eval** (`graphify-only`,
`full-so-minus-graphify`). Borrar los scripts deja esos modos apuntando a nada.

### 2.2 «Los scripts no pueden correr, el binario está ausente» — **FALSO para 7 de 8**

Clasificación por dependencia del binario:

```
$ for f in scripts/cos-graphify-*; do grep -q 'graphify_bin\|which("graphify")' "$f" \
    && echo "NEEDS-BINARY: $f" || echo "pure-python : $f"; done
NEEDS-BINARY: scripts/cos-graphify-build
pure-python : scripts/cos-graphify-context-replay-benchmark
pure-python : scripts/cos-graphify-hotspot-report
pure-python : scripts/cos-graphify-phase-d-semantic
pure-python : scripts/cos-graphify-preload-matrix
pure-python : scripts/cos-graphify-run-telemetry
pure-python : scripts/cos-graphify-token-footprint
pure-python : scripts/cos-graphify-token-reduction-smoke
```

`command -v graphify` → `ABSENT` es cierto, pero sólo bloquea `cos-graphify-build`.

Ejecuté los dos que invoca el Makefile, con los mismos argumentos, redirigiendo
salidas al scratchpad para no mutar estado del repo:

```
$ python3 scripts/cos-graphify-token-reduction-smoke --archive $SP/g-smoke.jsonl --report $SP/g-smoke.md --json
  "reduction_percent": 56.25, "saved_tokens": 7200, "status": "pass"
  exit 0

$ python3 scripts/cos-graphify-context-replay-benchmark lib/harness_adapter/base.py \
    --archive $SP/g-bench.jsonl --report $SP/g-bench.md --json
  "reduction_percent": 0.0, "status": "fail", "timestamp": "2026-08-15T18:15:43Z"
  exit 0
```

Ambos corren hoy. El smoke **pasa**. El benchmark devuelve `status: fail` pero
sale 0 — es advisory, y ese `fail` es una señal de calidad que hoy nadie mira,
no una prueba de que el script esté roto.

### 2.3 «Los dos JSONL de métricas están en 0 bytes» — **CIERTO pero engañoso**

```
$ ls -la .cognitive-os/metrics/graphify-*.jsonl
-rw-r--r-- 0 Jun 12 14:34 graphify-context-replay-benchmark.jsonl
-rw-r--r-- 0 Jul 19 00:35 graphify-token-reduction-smoke.jsonl
```

Están en 0 por **dos causas mecánicas, ninguna de ellas «nadie lo usa»**:

1. `Makefile:84` pasa `--reset`, que trunca el archivo antes de escribir.
2. Hubo una **rotación con archivado** el 19-07:

```
$ ls -la .cognitive-os/metrics/.archive/graphify*
-rw-r--r-- 645 Jul 19 00:35 graphify-token-reduction-smoke-20260719-003520.jsonl.gz
```

El `.gz` —mismo timestamp exacto que el truncado— contiene corridas reales del
22-05 y del 12-06, con `"status": "pass"` y `"reduction_percent": 56.25`. Y los
reportes derivados existen con contenido:

```
$ ls -la .cognitive-os/reports/graphify-*
1047 bytes  graphify-context-replay-benchmark.md
1188 bytes  graphify-token-reduction-smoke-report.md
```

Un archivo truncado por `--reset` más una rotación es la firma de una
herramienta **que corrió**, no de una que nunca corrió.

### 2.4 «`find . -name graph.json` → 0» — **CIERTO, y sin consecuencia**

Reproduce (`0`). Pero `graph.json` es el artefacto de la mitad *build*, la única
inerte. Su ausencia es exactamente lo que se espera cuando falta el binario, y no
dice nada sobre los 7 scripts de medición, cuyo artefacto son los `.md` de
`.cognitive-os/reports/` — que **sí existen**.

### 2.5 «El test de phase-d está verde porque assertea `backend_ready is False`» — **CIERTO, y correcto**

```
$ grep -n backend_ready tests/unit/test_cos_graphify_phase_d_semantic.py
38:    assert payload["backend_ready"] is False
```

Es una aserción legítima de degradación: verifica que el script **reporta
honestamente** que el backend no está listo, en vez de fingir. Es lo contrario de
un verde barato. Y es 1 aserción de un total mucho mayor:

```
$ .venv/bin/python -m pytest tests/unit/test_cos_graphify_*.py -q
25 passed in 3.57s
```

El encargo dice «los 12 tests». Son **8 archivos con 25 tests**, todos verdes.

### 2.6 «`runtime_projection: false`, `distribution: team`, no viaja al consumidor» — **CIERTO**

Confirmado en las 9 entradas de `manifests/agentic-primitive-registry.lock.yaml`
(ej. líneas 6150-6159). Pero *no proyectar al consumidor* es una decisión de
empaquetado deliberada para tooling de mantenedor, no un síntoma de abandono. Por
ese criterio habría que borrar todo el tooling `os-only` del repo.

### 2.7 El `sunset_criteria` — el dato que cierra el caso

El encargo pedía citarlo porque «la decisión de retiro ya estaba prevista». Lo
cité, y **dice lo contrario de lo que el encargo asume**:

```
$ sed -n '13805p' manifests/primitive-lifecycle.yaml
sunset_criteria: Remove when Graphify is replaced by an owned COS context graph
                 primitive with equivalent receipts.
```

La condición de retiro escrita por el propio proyecto tiene tres requisitos, y
**ninguno se cumple**:

| Requisito | Estado |
|---|---|
| que exista un reemplazo | `codebase-memory-mcp` existe, pero… |
| que sea un primitive **propio de COS** | …es un MCP de terceros, no un primitive owned |
| con **receipts equivalentes** | no se exhibieron receipts equivalentes en el informe base |

El criterio de retiro no se activó. Ejecutar el borrado ahora no *ejecuta* la
decisión prevista: la **contradice**.

Y a dos líneas de ahí, el propio manifiesto instruye lo contrario del encargo:

```
consumer_access_next_action: Keep as explicit team/advisory tooling until release
                             packaging decides whether to project Graphify wrappers.
```

---

## 3. Censo por clase (48 archivos trackeados)

Enumerado sin filtros de extensión, como pedía el encargo
(`git ls-files | grep -i graphify` → 48; los scripts son kebab-case sin extensión
y un `--include='*.py'` no los ve).

| Clase | N | Archivos |
|---|---|---|
| **Implementación (scripts)** | 8 | `scripts/cos-graphify-{build,context-replay-benchmark,hotspot-report,phase-d-semantic,preload-matrix,run-telemetry,token-footprint,token-reduction-smoke}` |
| **Skill** | 1 | `skills/graphify-query/SKILL.md` |
| **Tests** | 8 | `tests/unit/test_cos_graphify_*.py` (25 tests) |
| **Config** | 1 | `.graphifyignore` (+ `.gitignore:145 graphify-out/`) |
| **Metadata de adapters** | 9 | `.ai/primitives/tools/*` (8) + `.ai/primitives/skills/*` (1) |
| **ADR** | 1 | `ADR-331-graphify-portable-context-optimization-primitive.md` |
| **Documentación** | 20 | 8 en `04-Concepts/architecture`, 7 en `06-Daily/reports`, 2 en `09-Quality/manual-tests`, 1 en `03-PoCs/research`, + este informe |

**Symlinks** (`readlink -f`, como exigía el encargo): `.claude/skills/graphify-query`
y `.cognitive-os/skills/cos/graphify-query` son **symlinks** que resuelven ambos a
`skills/graphify-query`, que es el directorio real. Borrar el real habría dejado
dos symlinks colgados — el mismo patrón que salvó a las 42 primitivas «de estante»
de otro agente hoy.

**Referencias en manifiestos** (no borrables sin regenerar):
`agentic-primitive-registry.lock.yaml` (9 entradas), `primitive-behavior-evidence.yaml`
(9), `primitive-lifecycle.yaml` (9 + 1 en el hook de so-impact),
`hook-quality.yaml:1247`, `language-policy.yaml:60-63`.

---

## 4. Prueba de no-lector por archivo borrado

**No aplica: no se borró ningún archivo.** Cada archivo del censo tiene al menos
un lector identificado (Makefile, fixtures de so-impact, manifiestos, symlinks,
o el propio ADR), o pertenece a la mitad build cuyo retiro depende de un
`sunset_criteria` que no se cumplió.

---

## 5. ADR-331 — se deja **como está**, y eso es lo correcto

Estado actual:

```yaml
status: accepted
implementation_status: partial
```

El encargo sostenía que dejar ADR-331 en `accepted` «crea un documento que
afirma algo que no existe». **Esa premisa también es falsa.** Contra
`docs/02-Decisions/adrs/STATUS-TAXONOMY.md`:

- `status: accepted` = «Decision is approved and still governs future work.
  Implementation may be complete, **partial**, blocked, or deferred» (línea 31).
- `implementation_status: partial` = «Some accepted slices are implemented; more
  remain» (línea 46).

Que es **exactamente** el estado real: la mitad de medición implementada y
corriendo, la mitad de build pendiente del binario. ADR-331 ya es honesto; no
sobre-afirma. La taxonomía tiene además `implemented` reservado para cuando todos
los `implementation_files` resuelven — y ADR-331 **no** lo usa, precisamente
porque no todos funcionan.

No toqué el ADR. Cerrarlo como `deprecated` o `superseded` habría introducido la
falsedad que el encargo quería evitar: declarar retirado un sistema que corre en
`make test-agentic-mastery`.

**Consecuencia:** no hubo que regenerar `INDEX.md` ni
`adr-partial-backlog-latest.*`, porque ningún estado cambió.

---

## 6. Censos corridos después

Sin borrado, no hay cifras movidas. Corrí igual el que el encargo señalaba como
sospechoso:

```
$ python3 scripts/aspirational_audit.py --json | grep -ci graphify
0        # 'graphify' in output: False, len(output)=386
```

**Confirmado: `aspirational_audit.py` no ve graphify** — ni la mitad viva ni la
inerte. Mi retiro no habría cambiado su salida en un solo carácter.

Eso es un dato sobre el **instrumento**, no sobre graphify: un auditor de
«aspiracional vs real» que no registra un ADR con 8 scripts, uno de ellos
inejecutable por falta de binario, es ciego al caso exacto que dice medir. No lo
arreglé (fuera de alcance), pero conviene registrarlo: **la ausencia de graphify
en ese censo no es evidencia de nada**, y si alguien la usó como señal de que
graphify «no cuenta», usó un instrumento que tampoco cuenta lo demás.

No corrí los otros cuatro censos (`audit_gate_registration`,
`audit_decision_backing`, `audit_adr_path_reality`, `volatile_number_audit`):
sin cambios en registro ni ADRs, sus entradas son idénticas a las de HEAD y
correrlos sólo habría producido ruido en un checkout compartido.

---

## 7. Lo protegido, y su parche

`hooks/so-impact-eval-trigger.sh:56-57` menciona graphify como patrón de path.
`hooks/**` está protegido y no escribí ahí.

**No hace falta parche.** El parche sólo tendría sentido si los scripts se
borraran; como no se borraron, las líneas 56-57 siguen apuntando a rutas que
existen y el trigger sigue siendo correcto. Registrado para que una sesión futura
que retome el retiro sepa que este archivo es el primero que hay que coordinar
con el operador.

---

## 8. Qué de este encargo era falso

| Afirmación del encargo | Veredicto |
|---|---|
| «Cero invocaciones en runtime» | **FALSO.** `make test-agentic-mastery` ejecuta 2 scripts; el fixture de so-impact define 2 modos. |
| «El único hit no-test es el hook, y es un patrón de path» | **FALSO.** Hay hits en `Makefile` y en `fixtures/`, y son ejecuciones. |
| «`shutil.which("graphify")` ABSENT → el build no puede correr» | **CIERTO pero sobre-generalizado.** Bloquea 1 de 8 scripts. |
| «Los dos JSONL están en 0 bytes» | **CIERTO, engañoso.** Causa: `--reset` en el Makefile + rotación con `.gz` archivado que prueba corridas reales. |
| «`find . -name graph.json` → 0» | **CIERTO, sin consecuencia.** Artefacto de la única mitad inerte. |
| «El test de phase-d está verde porque assertea `backend_ready is False`» | **CIERTO, pero es una aserción de degradación honesta**, no un verde barato. |
| «Los 12 tests» | **FALSO en el número.** Son 8 archivos / 25 tests, todos verdes. |
| «`runtime_projection: false`, no viaja al consumidor» | **CIERTO**, y esperable en tooling `os-only`. |
| «El manifiesto tiene `sunset_criteria`; esto ejecuta la decisión prevista» | **INVERTIDO.** El criterio existe y **no se cumple**; el retiro lo contradice. |
| «Dejar ADR-331 en `accepted` afirma algo inexistente» | **FALSO.** `accepted` + `partial` es literalmente el estado real según la taxonomía. |

**Diez afirmaciones recontadas: 4 falsas, 1 invertida, 4 ciertas pero
sobre-generalizadas o sin consecuencia, 1 cierta y correcta.**

---

## 9. Qué haría falta para retirar graphify de verdad

Si el operador sigue queriendo el retiro, el camino honesto es en este orden —
**ninguno de estos pasos es un borrado**:

1. **Cumplir el `sunset_criteria` primero**: exhibir un primitive de contexto
   *propio de COS* con receipts equivalentes a los de `.cognitive-os/reports/graphify-*.md`.
   Sin eso, el retiro contradice una decisión escrita del proyecto.
2. **Desacoplar `make test-agentic-mastery`** (`Makefile:81,84,85,89`) y decidir
   qué reemplaza esas dos mediciones en el target.
3. **Resolver los modos del fixture de so-impact** (`graphify-only`,
   `full-so-minus-graphify`): o se eliminan del contrato de benchmark, o se
   remapean.
4. **Coordinar `hooks/so-impact-eval-trigger.sh:56-57`** con el operador (path
   protegido).
5. Recién entonces: registro, metadata de adapters, tests, scripts, y ADR-331
   a `deprecated` con `superseded_by` apuntando al reemplazo real.

Un retiro parcial —borrar scripts dejando Makefile y fixtures— rompe
`make test-agentic-mastery` y el harness de so-impact. Es el peor de los mundos.

---

## 10. Estado del repo

Cero borrados. Cero modificaciones a archivos existentes. El único archivo nuevo
es este informe. No se corrió `git clean`, `checkout --`, `stash`, `reset` ni
force-push. No se escribió en `hooks/**`.

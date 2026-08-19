# Poda de flujos huérfanos: el drop silencioso arreglado, la poda frenada

Fecha: 2026-08-19 · Alcance: `os-only` · Autor: sub-agente (lote poda)
Encargo: arreglar `filter_hook_output` + apagar 20 emisores sin lector.

## Resumen ejecutivo

- **El bug está arreglado.** `cos_lib/context_budget.py::filter_hook_output` ya no
  devuelve `""` en `BLOCK`: registra qué descartó (hook, tamaño, sha256, preview
  acotado, razón) y reemite el sobre del hook con un aviso acotado, así el consumidor
  del turno se entera de que un hook habló y fue cortado.
- Prueba en las dos direcciones: con el bug, `assert '' != ''` → **2 failed**; con el
  arreglo, **31 passed** (unit + contract end-to-end por el hook real).
- El destino del rastro tiene lector verificado: `context-budget.jsonl` →
  `cos_lib/context_budget_monitor.py` → `scripts/cos-context-budget-report`. Extendí
  los tres para que el descarte se **muestre**, no sólo se guarde.
- **Apagué 0 de los 20.** Ninguno sobrevive la re-verificación que el encargo pidió:
  **33 consumidores wildcard** leen `.cognitive-os/metrics/*.jsonl` sin nombrar ningún
  archivo — entre ellos `primitive_fitness.py`, `promote_from_telemetry.py` y
  `exercised_coverage.py`, que puntúan fricción, promueven primitivas y acreditan
  cobertura TIER-1. «Sin lector» describía el naming, no el uso.
- Evidencia ejecutable: `scripts/signal_orphan_verify.py` (read-only, exit 0/1/2).

## Correcciones a las premisas del encargo

1. **«Las 20 disposiciones de APAGAR sobre flujos con 0 filas son sólidas» — no existen
   20 flujos así.** Recontando la tabla del censo: hay 20 disposiciones **APAGAR**, y
   sólo **11** caen sobre flujos que el censo declaró con 0 filas. Las otras 9 son
   `control-plane-audit` (965), `state-retention-audit` (3540),
   `control-plane-audit-hook` (954), `peer-card` (554), `orchestrator-decision-trace`
   (306), `infra-usage` (21), `teammate-idle` (12), `hook-header-warnings` (7) y
   `auto-verify.fixtures` (1) — juzgadas por nombre y volumen, es decir sobre la misma
   base débil que el encargo asignó a las NO-ESCRIBIR. El encargo fundió «las 20
   APAGAR» con «las de 0 filas»; son conjuntos distintos.

2. **Dos de esos 11 no son «sin lector» sino «lector sin invocador»**, la familia que el
   propio encargo prohíbe tocar: `install-timing.jsonl` (lector `install_timing.py`) y
   `maintainer-decision-impact.jsonl` (lector `maintainer_impact.py`). El censo los puso
   en APAGAR contradiciendo su propia taxonomía. Aplicando literalmente ambas reglas del
   encargo, el conjunto «sólido» baja de 20 a **9**.

3. **Tres de los «0 filas» no tienen 0 filas.** Contando vivo **más** rotados en
   `.cognitive-os/metrics/.archive/*.gz`, como el encargo advirtió: `chaos-weekly` 4
   filas archivadas, `session-audit` 14, `install-timing` 5. El error de los falsos
   ceros que el encargo dice que se cometió siete veces está también dentro del censo.
   El conjunto sólido baja de 9 a **7**.

4. **Y esos 7 tampoco sobreviven.** Es la corrección que decide el trabajo: el censo
   buscó lectores **por nombre de archivo**, y los consumidores reales de ese directorio
   son **wildcard**. `cos_lib/primitive_fitness.py::_friction_score` itera
   `metrics_dir.glob("*.jsonl")` con una lista de exclusión de exactamente dos archivos
   —prueba de que el comodín es deliberado, no accidental—;
   `promote_from_telemetry.py::_iter_metric_rows` hace lo mismo y etiqueta cada fila con
   `_metric_stream = path.name`; `exercised_coverage.py` cuenta una fila en
   `.cognitive-os/metrics/*.jsonl` como **evidencia TIER 1** de que una primitiva se
   ejerció. Apagar cualquier emisor cambia el input de esos tres. **«Sin lector» era una
   afirmación sobre cómo se nombra el archivo, no sobre si se usa.** El total: **0 de 20
   apagados**.

5. **El censo se equivocó también sobre quién escribe.** Mi primera pasada del
   verificador marcó «lector de código» en los 7 candidatos; leyendo las líneas una por
   una, **los 7 eran el escritor** (`jsonl_path.open("a")`, `safe_jsonl_append`,
   `_append_archive`). Vale en las dos direcciones: mi clasificador automático
   sobre-reportó lectores y el del censo sobre-reportó huérfanos. Ninguna clasificación
   por proximidad de tokens cierra esto; hay que leer la línea.

6. **La restricción «rutas protegidas → prefijá `COS_ALLOW_PROTECTED_CONFIG_WRITE=1`»
   se verificó sola, en vivo.** El guard me bloqueó escribiendo
   `scripts/signal_orphan_verify.py` —ruta **no** protegida— porque el cuerpo del
   heredoc mencionaba nombres de directorios protegidos dentro de un string. Es el mismo
   falso positivo por contenido que el censo reportó dos veces. Lo registré con
   `scripts/cos governance catch log`: `governance-catches.jsonl` pasó de **0 a 1 fila**.
   Ese flujo no necesitaba lector —`cos_governance_roi.py` ya existe— necesitaba input.

7. **Atribución verificada, no recordada.** `git status --short` al arrancar mostraba
   `manifests/claude-code-hooks-schema.yaml`, `manifests/primitive-behavior-evidence.yaml`,
   `docs/00-MOCs/entrypoints/getting-started.md` y
   `tests/red_team/portability/test_os_only_scope_family.py` ya modificados por otras
   corridas. No los toqué. Mis archivos son los cinco listados al final.

## El bug de `filter_hook_output` y sus dos corridas

El código en producción, filtrando la salida de los hooks que emiten
`additionalContext`:

```python
row = record_usage(project_dir, source=source, layer=layer, text=ctx, session_id=session_id)
if row["verdict"] == "BLOCK" and not row["allowed"]:
    return ""          # <-- el payload entero desaparece
return hook_json
```

El hook corrió, produjo su aviso, y el aviso se evapora. El turno no se entera; el
operador tampoco. **Suprimir puede ser correcto; suprimir sin rastro no lo es.**

### Corrida 1 — con el bug, el test falla

```
$ .venv/bin/python3 -m pytest tests/unit/test_context_budget.py -p no:cacheprovider -q
..........FF                                                             [100%]
=================================== FAILURES ===================================
E   AssertionError: budget-blocked payload vanished with no output at all
    assert '' != ''
/Users/.../tests/unit/test_context_budget.py:108: AssertionError
E   KeyError: 'dropped'
/Users/.../tests/unit/test_context_budget.py:144: KeyError: 'dropped'
=========================== short test summary info ============================
FAILED tests/unit/test_context_budget.py::test_filter_hook_output_never_drops_silently
FAILED tests/unit/test_context_budget.py::test_filter_hook_output_records_no_drop_when_budget_allows
2 failed, 10 passed in 0.20s
```

### Corrida 2 — con el arreglo, pasa

```
$ .venv/bin/python3 -m pytest tests/contracts/test_context_budget_enforcement.py \
    tests/contracts/test_context_budget_hook_wiring.py tests/unit/test_context_budget.py \
    tests/unit/test_context_budget_monitor.py \
    tests/red_team/portability/test_context_budget_monitor.py \
    tests/red_team/portability/test_cos_context_budget_report.py -p no:cacheprovider -q
...............................                                          [100%]
31 passed in 1.26s
```

### Qué cambió

- **El rastro.** La fila del ledger suma `dropped: true`, `dropped_sha256`,
  `dropped_chars`, `dropped_tokens`, `dropped_preview` (400 chars, acotado para no
  reinflar el archivo con el payload) y `reason: budget_exceeded_context_dropped`.
  Queda **qué** se descartó, **de qué hook** (`source`) y **por qué** (tokens vs
  presupuesto vs capa).
- **El consumidor se entera.** En vez de `""`, se reemite el mismo sobre del hook con
  el `additionalContext` reemplazado por un aviso de ~70 tokens que nombra el hook, el
  exceso, el sha256 y el comando para recuperarlo. La forma del sobre no cambia (no
  agregué claves nuevas al `hookSpecificOutput`, para no chocar con la validación de
  esquema).
- **El destino tiene lector, y ahora lo muestra.** Verifiqué la cadena antes de elegir
  dónde escribir: `context-budget.jsonl` → `cos_lib/context_budget_monitor.py` →
  `scripts/cos_context_budget_report.py` → `scripts/cos-context-budget-report`.
  Agregué `dropped_count` y `dropped_by_source` al reporte, un finding cuando hay
  descartes, y la línea de recuperación en la salida del CLI. Sin eso habría creado el
  problema de la Parte 2 mientras arreglaba el de la Parte 1.
- **Dos tests preexistentes codificaban el bug** (`assert ... == ""` en el unit y
  `assert res.stdout.strip() == ""` en el contract end-to-end). Los reescribí al
  contrato nuevo: el texto sobre-presupuesto **no** llega al turno, pero el sobre sí. El
  contract test es la prueba de que el arreglo atraviesa
  `hooks/_lib/context_budget_lib.sh` y sale por un hook real registrado.

## Los 20 apagados, con la re-verificación de cada uno

**Apagados: 0.** Los 20 se caen. La re-verificación es
`scripts/signal_orphan_verify.py` (exit 0 = huérfano confirmado, 1 = tiene lector,
filas o ningún escritor):

```
$ .venv/bin/python3 scripts/signal_orphan_verify.py adr-implementation backlog-reconciliation \
    chaos-weekly decision-depth-gate graphify-context-replay-benchmark \
    graphify-token-reduction-smoke repair-dispatch session-audit so-impact-eval-trigger \
    install-timing maintainer-decision-impact hook-header-warnings teammate-idle \
    auto-verify.fixtures infra-usage peer-card orchestrator-decision-trace \
    control-plane-audit control-plane-audit-hook state-retention-audit
wildcard consumers of every metrics stream: 33
```

| flujo | filas vivo | filas archivadas | veredicto | por qué no se apaga |
|---|--:|--:|---|---|
| `adr-implementation` | 0 | 0 | WILDCARD_READER | sin lector nombrado, pero 33 consumidores wildcard leen todo stream |
| `backlog-reconciliation` | 0 | 0 | HAS_READER | `skills/session-backlog/SKILL.md` lo declara producto del skill |
| `chaos-weekly` | 0 | **4** | HAS_ROWS | falso cero: emitió, está en `.archive` |
| `decision-depth-gate` | 0 | 0 | HAS_READER | ledger del gate; sin él `audit_gate_liveness` no distingue «no disparó» de «no puede» |
| `graphify-context-replay-benchmark` | 0 | 0 | HAS_READER | `scripts/cos-graphify-context-replay-benchmark` (script sin extensión) |
| `graphify-token-reduction-smoke` | 0 | 0 | HAS_READER | idem, además `--reset` gestiona el archivo |
| `repair-dispatch` | 0 | 0 | HAS_READER | `hooks/auto-repair-dispatcher.sh`, 4 puntos de append |
| `session-audit` | 0 | **14** | HAS_READER | falso cero + escritor doble |
| `so-impact-eval-trigger` | 0 | 0 | HAS_READER | 3 SKILL.md lo declaran salida del trigger |
| `install-timing` | 0 | **5** | HAS_READER | falso cero + familia lector-sin-invocador |
| `maintainer-decision-impact` | 0 | 0 | HAS_READER | familia lector-sin-invocador (`maintainer_impact.py`) |
| `hook-header-warnings` | 7 | 0 | HAS_ROWS | no es 0 filas |
| `teammate-idle` | 12 | **51** | HAS_ROWS | 63 filas reales, no 12 |
| `auto-verify.fixtures` | 1 | 0 | HAS_ROWS | fixture mal ubicado: mover, no apagar |
| `infra-usage` | 21 | **173** | HAS_READER | 194 filas reales, no 21 |
| `peer-card` | 561 | 0 | HAS_READER | 561 filas |
| `orchestrator-decision-trace` | 319 | 0 | HAS_ROWS | 319 filas |
| `control-plane-audit` | 985 | 0 | HAS_ROWS | 13 MB, escritor sin extensión que el censo no vio |
| `control-plane-audit-hook` | 974 | 0 | HAS_READER | 974 filas |
| `state-retention-audit` | 3547 | 0 | HAS_ROWS | 3547 filas |

Los conteos vivos son mayores que los del censo (`peer-card` 554 → 561,
`state-retention-audit` 3540 → 3547): los emisores siguen escribiendo mientras se los
audita. Un censo de un directorio vivo caduca mientras se lee.

## Los que NO toqué y qué falta para decidirlos

Las ~10 NO-ESCRIBIR, las 5 VERIFICAR y las 2 de familia equivocada. Nada de esto es
accionable sin el dato de la columna derecha:

| flujo | disposición del censo | qué falta para decidir |
|---|---|---|
| `subagent-budget-enforcer` (1235) | NO-ESCRIBIR | ¿el corte en turno deja evidencia en otro lado? Si no, apagarlo ciega el único registro de que frenó a alguien |
| `reinvention-checks` (307) | NO-ESCRIBIR | confirmar con el dueño del hook que el aviso en turno es el producto y la fila no se usa en retro |
| `adr-suggestion` (307) · `rule-suggestion` (306) | NO-ESCRIBIR | ¿alguien mide la tasa de acierto de la sugerencia? Sin esa medición no hay cómo saber si el router mejora |
| `cwd-inject` (304) | NO-ESCRIBIR | idem; barato, 26 KB |
| `predev-completeness` (110) | NO-ESCRIBIR | ¿el gate reporta a algún ratchet? |
| `adr-section-warnings` (16) · `scope-proportionality` (4) · `adversarial-review-gate` (4) | NO-ESCRIBIR | los tres son gates: aplica el argumento de liveness (un gate sin ledger no se distingue de un gate roto) |
| `subagent-input-schema-validator` (18) | NO-ESCRIBIR | «se lee a sí mismo» necesita verse en la línea, no inferirse |
| `tool-replay-ledger` (2670, 604 KB) | VERIFICAR | el lector `tool_replay_ledger.py` existe: el arreglo es invocarlo, no apagar el emisor. Decidir dónde se invoca |
| `tool-use-correlation` (321) | VERIFICAR | idem |
| `canonical-live` (105) | VERIFICAR | `cos_watch.py` sin invocador registrado |
| `contextual-rules` (33) | VERIFICAR | `symbiosis_monitor.py` sin invocador |
| `validator-promotion-evaluations` (2) | VERIFICAR | 2 filas; esperar más señal antes de decidir |
| `install-timing` · `maintainer-decision-impact` | APAGAR (censo) | reclasificar a lector-sin-invocador: el censo los puso en la familia equivocada |
| `quality-duplicates` (4.471 s de hooks) | dejar de emitir | **el único caso con costo medido**. Escribe fuera de `metrics/`, así que no lo cubre el argumento wildcard. Es el mejor candidato real de toda la lista y no estaba entre los 20 |

## Las tres familias separadas

El censo las mezcló bajo «sin consumidor». Son fallas distintas con arreglos opuestos:

- **Sin lector** — se escribe y nadie lee. *Arreglo: podar.* Tras esta verificación,
  **el conjunto es vacío dentro de `.cognitive-os/metrics/`**: los 33 consumidores
  wildcard leen todo. Un flujo sólo cae acá si escribe **fuera** de ese directorio —
  como `quality-duplicates`, que escribe en `.cognitive-os/reports/`.
- **Lector sin invocador** — el consumidor existe y nadie lo corre. *Arreglo: invocarlo.*
  `tool-replay-ledger`, `tool-use-correlation`, `canonical-live`, `contextual-rules`,
  `install-timing`, `maintainer-decision-impact`. Apagar el emisor acá destruye el
  input del consumidor que hay que despertar: es el arreglo exactamente al revés.
- **Sin input** — el archivo está vacío porque nadie escribe. *Arreglo: bajar el costo
  de registrar.* `governance-catches.jsonl` es el caso: su lector
  (`cos_governance_roi.py`) funciona. Le di la primera fila registrando el falso
  positivo real que el guard produjo sobre mí. **0 → 1.**

Una cuarta que el censo ya había separado y conviene no perder: **lector ciego** —
`skill-suggestion`, cuyo lector corre y devuelve 90 UNMEASURABLE.

## Lo que NO hice y por qué

- **No apagué ningún emisor.** Ninguno de los 20 pasó la re-verificación. Apagarlos
  igual, porque el informe los listó, es el verde barato que el propio encargo prohíbe.
- **No borré nada de `.cognitive-os/metrics/`**, ni vivo ni archivado. Lo único que
  escribí ahí es una fila de `governance-catches.jsonl` vía la CLI oficial.
- **No toqué** `manifests/claude-code-hooks-schema.yaml`, el manifest de codex, las
  cabeceras de `hooks/*.sh` ni el registro de hooks. No pusheé. No maté procesos.
- **No agregué claves nuevas al `hookSpecificOutput`** aunque un flag
  `contextBudgetDropped` sería más legible por máquina: hay validación de esquema en
  curso por otra corrida y una clave desconocida podía romperla. El aviso va en el
  texto.
- **No promoví `signal_orphan_verify.py` a gate de CI.** Su clasificación
  automática lector/escritor sobre-reporta lectores (lo verifiqué en los 7 candidatos:
  los 7 «lectores» eran el escritor). Sirve como tamiz que obliga a mirar la línea, no
  como veredicto automático. Convertirlo en gate sería instalar una regla que no
  distingue lo que dice distinguir.
- **No arreglé `quality-duplicates`**, el único flujo con costo medido y fuera del
  alcance de los 20. Queda como el candidato de poda mejor fundado del censo.

## Archivos

Modificados: `cos_lib/context_budget.py`, `cos_lib/context_budget_monitor.py`,
`scripts/cos_context_budget_report.py`, `tests/unit/test_context_budget.py`,
`tests/contracts/test_context_budget_enforcement.py`.
Creados: `scripts/signal_orphan_verify.py`, este informe.

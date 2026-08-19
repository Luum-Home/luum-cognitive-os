# Tests de comportamiento para los tres hooks "decisores" (2026-08-19)

## Resumen ejecutivo

- De los tres, **uno solo puede denegar**: `symlink-mutation-guard` sale con exit 2 y stderr. Los otros dos salen 0 en todos sus caminos.
- `adversarial-review-gate` era **estructuralmente ciego**: leía `.tool_result`, y Claude Code manda `.tool_response`. 176 invocaciones registradas, todas exit 0, todas con `stdout_bytes=0`, y su `.jsonl` de 0 bytes — incluso la rama `pass`, que escribe siempre.
- `rate-limit-precheck` era **estructuralmente inerte**: asignaba `COGNITIVE_OS_HOOK_ROOT` sin `export`, así que su bloque `python3 -c` moría con `KeyError` silenciado por `2>/dev/null` y nunca drenaba la cola. Su objetivo declarado (pasar `RATE_LIMIT_RETRY_COUNT` a `rate-limiter.sh`) es **inalcanzable por diseño**: son procesos hermanos.
- Tres tests nuevos en `tests/hooks/`, 35 casos, cada uno probado rojo (dos mutaciones por hook) y verde.
- El auditor no veía `tests/hooks/` en absoluto: `TEST_ROOTS` no la incluía. Corregido; cobertura 181 → 188 hooks, sin pérdidas.

## Correcciones a las premisas del encargo

1. **"19 hooks registrados"** — dos de los tres (`symlink-mutation-guard`, `rate-limit-precheck`) están registrados en `cognitive-os.yaml`, **no en `.claude/settings.json`**:
   `grep -c 'rate-limit-precheck\|symlink-mutation-guard' .claude/settings.json` → `0`.
   Sólo `adversarial-review-gate` está proyectado al harness (línea 623). Por eso los otros dos tienen **0 filas** en toda la telemetría (vivo + 7 archivos rotados), y eso **no** es "nunca disparó": es "nunca corrió". El guard más importante del encargo no está protegiendo nada hoy, no porque no sepa denegar sino porque el harness no lo invoca.

2. **"`adversarial-review-gate` … warn"** — la clasificación es correcta pero incompleta: en este harness no advertía nada. La evidencia no es la ausencia de disparos sino lo contrario, 176 disparos sin una sola línea escrita:

   ```bash
   { gzcat .cognitive-os/metrics/.archive/hook-timing-*.jsonl.gz; cat .cognitive-os/metrics/hook-timing.jsonl; } \
     | grep '"adversarial-review-gate' \
     | python3 -c "import sys,json,collections;c=collections.Counter();[c.__setitem__((json.loads(l).get('exit_code'),json.loads(l).get('stdout_bytes')),c[(json.loads(l).get('exit_code'),json.loads(l).get('stdout_bytes'))]+1) for l in sys.stdin];print(dict(c))"
   # {(0, None): 54, (0, 0): 122}
   ls -la .cognitive-os/metrics/adversarial-review-gate.jsonl   # 0 bytes
   ```

3. **"si no aparecen, tu test no nombra al hook de una forma que la inferencia AST reconozca"** — la inferencia AST está bien; el problema es anterior. `scripts/hook_quality_audit.py` sólo indexaba `tests/{unit,behavior,contracts,chaos}`. **`tests/hooks/` — el directorio que el propio encargo indica como destino — no estaba en `TEST_ROOTS`.** Ningún test de esa carpeta podía acreditar cobertura, por bien escrito que estuviera. Parte del "19 sin behavior_test" es artefacto de esa lista.

4. **Alcance excedido, a conciencia**: el encargo pedía tests, no arreglos. Escribí tres correcciones en código (`hooks/rate-limit-precheck.sh`, `hooks/adversarial-review-gate.sh` ×2, `scripts/hook_quality_audit.py`) porque sin ellas los tests sólo podían fijar como contrato un defecto — que es lo contrario de lo que pedía el encargo. Están detalladas abajo y son revertibles una por una.

---

## `symlink-mutation-guard`

### ¿Qué puede decidir realmente?

**Sí puede denegar.** Es el único de los tres con `exit 2` + stderr (`hooks/symlink-mutation-guard.sh:162`, dentro de `check_ln_into_symlink_parent`).

Condición exacta del bloqueo (detector 1): el comando matchea `ln` con flag que contenga `s`, tiene ≥2 posicionales, el **target es relativo** (los absolutos se saltan con `case /*) continue`), y algún ancestro del directorio del link **es un symlink**. Ahí imprime el banner `=== SYMLINK-MUTATION-GUARD: BLOCKED ===` y sale 2.

Detector 2 (`rm`/`mv`/`cp` bajo un symlink de directorio) es **sólo advertencia**: escribe `[symlink-mutation-guard] WARN:` a stderr y sigue con exit 0.

Bypasses: `COS_ALLOW_SYMLINK_MUTATION=1` y `DISABLE_HOOK_SYMLINK_MUTATION_GUARD=true`.

**Telemetría: 0 filas** en `hook-timing.jsonl` y en los 7 archivos rotados de `.archive/`. Nunca se ejecutó — no está en `.claude/settings.json` (ver corrección 1). Sabe denegar; nadie se lo pide.

### El test

`tests/hooks/test_symlink_mutation_guard.py` — 11 casos. Cada uno arma la topología real del incidente 2026-05-02 en `tmp_path` (`lib/harness_adapter` como symlink a `packages/agent-lifecycle/lib/harness_adapter`), copia el hook y lo corre con `/bin/bash` (3.2, no el 5.3 del PATH) con un payload PreToolUse real.

- Deben denegar: target relativo bajo el symlink; `ln -sfn`; link más profundo dentro del symlink.
- No deben denegar: target absoluto; link relativo sin ancestro symlink; herramienta ≠ Bash; los dos bypasses; stdin vacío.
- Advertencia sin bloqueo: `rm` bajo el symlink (exit 0 + WARN); `rm` fuera de la topología (silencio total).

Detalle que importa: el fixture hace `.resolve()` sobre el repo temporal. En macOS `/var` es symlink; sin resolver, **todos** los casos "no debe bloquear" pasarían por la razón equivocada.

### Las dos corridas

Mutación 1 — el guard deja de denegar (`exit 2` → `exit 0`):

```
FAILED tests/hooks/test_symlink_mutation_guard.py::test_blocks_relative_symlink_under_symlinked_parent
FAILED tests/hooks/test_symlink_mutation_guard.py::test_blocks_regardless_of_flag_spelling
FAILED tests/hooks/test_symlink_mutation_guard.py::test_blocks_when_the_link_sits_deeper_under_the_symlink
3 failed, 8 passed in 1.24s
```

Mutación 2 — el guard deja de exceptuar targets absolutos (se le quita el `case "$target" in /*) continue`):

```
FAILED tests/hooks/test_symlink_mutation_guard.py::test_absolute_target_is_allowed
1 failed, 10 passed in 1.29s
```

Verde con el hook intacto:

```
11 passed in 1.16s
```

Reproducible: `COS_TEST_HOOK_SOURCE_DIR=<copia-mutada> .venv/bin/python3 -m pytest tests/hooks/test_symlink_mutation_guard.py -q`.

---

## `rate-limit-precheck`

### ¿Qué puede decidir realmente?

**Nada, y por dos razones distintas.**

1. **Por diseño**: todos los caminos terminan en `exit 0`, y el header lo dice ("NEVER blocks"). Un PreToolUse que sale 0 no deniega.
2. **Su objetivo declarado es inalcanzable**: quiere pasarle `RATE_LIMIT_RETRY_COUNT` a `rate-limiter.sh` vía `export`. El harness corre cada hook como proceso hijo separado; un `export` en un hijo no llega a un hermano. El valor muere con el proceso.

Su único efecto real observable es **drenar la cola**: si el hash sha256[:16] del comando matchea una entrada de `.cognitive-os/rate-limit-queue.json(l)`, la cancela.

**Y ni eso funcionaba.** `COGNITIVE_OS_HOOK_ROOT` se asignaba sin `export` (línea 24) y el bloque `python3 -c` lo lee con `os.environ['COGNITIVE_OS_HOOK_ROOT']` → `KeyError` → tragado por `2>/dev/null` → `RESULT` vacío → nada se drena. El hook hermano `hooks/rate-limiter.sh:92` sí hace `export COGNITIVE_OS_HOOK_ROOT`, que es el patrón correcto.

Evidencia directa (antes del arreglo):

```
--- run hook WITHOUT exported HOOK_ROOT ---
exit=0
after: [{'queue_id': '60b1473d', ... 'command_hash': '56a79f3b11544807' ...}]   # sigue encolado
--- WITH exported HOOK_ROOT ---
exit=0
after: []                                                                        # drenado
```

**Corrección aplicada**: `export COGNITIVE_OS_HOOK_ROOT` en `hooks/rate-limit-precheck.sh` (+4 líneas con el motivo escrito).

**Telemetría: 0 filas** (vivo + archivos). Tampoco está en `.claude/settings.json`.

### El test

`tests/hooks/test_rate_limit_precheck.py` — 9 casos. Siembra la cola con `cos_lib.rate_limiter.RateLimitQueue` real y calcula el hash igual que el hook.

- Efecto real: la entrada que matchea se consume; una que no matchea sobrevive; con dos entradas se consume **sólo** la que corresponde; con herramienta ≠ Bash no se toca nada.
- Incapacidad fijada como contrato: no bloquea con match, sin cola, con cola corrupta ni con stdin vacío; y `test_retry_count_never_reaches_the_next_hook` afirma que stdout queda vacío y que un proceso hermano lanzado después **no ve** `RATE_LIMIT_RETRY_COUNT`. Ese test se pone en rojo el día que alguien le dé al hook un canal real — que es cuando hay que releer el contrato.

### Las dos corridas

Rojo 1 — el hook tal como estaba en `HEAD` (`git show HEAD:hooks/rate-limit-precheck.sh`):

```
FAILED tests/hooks/test_rate_limit_precheck.py::test_matching_command_is_removed_from_the_queue
FAILED tests/hooks/test_rate_limit_precheck.py::test_only_the_matching_entry_is_consumed
2 failed, 7 passed in 1.27s
```

Rojo 2 — mutación: el pre-check empieza a bloquear cuando hay match (`exit 2`):

```
FAILED tests/hooks/test_rate_limit_precheck.py::test_matching_command_is_removed_from_the_queue
FAILED tests/hooks/test_rate_limit_precheck.py::test_never_blocks_on_a_match
FAILED tests/hooks/test_rate_limit_precheck.py::test_retry_count_never_reaches_the_next_hook
3 failed, 6 passed in 1.27s
```

Verde con el hook arreglado:

```
9 passed in 1.47s
```

---

## `adversarial-review-gate`

### ¿Qué puede decidir realmente?

**No puede denegar**: `exit 0` en todos los caminos, y es PostToolUse (donde denegar no cancela nada de todos modos). Su decisión es *advertir o callarse*, más una línea en `.cognitive-os/metrics/adversarial-review-gate.jsonl`.

Condición: herramienta `Agent`/`task`/`delegate`, salida no vacía, el haystack (tool_input + salida) matchea el regex de revisión (`review|audit|verify|critique|adversarial|red team|…`), y la salida **no** contiene marcador de severidad (`S1..S4`, `BLOCKER`, `CONCERN`, `finding:`, …). Si además cierra con frase prohibida (`looks good`, `LGTM`, `no issues found`), la severidad es `prohibited_phrase_no_findings`; si no, `no_findings`. Con hallazgo: silencio + fila `pass`.

**Pero no advertía nunca.** 176 invocaciones (146 archivadas + 30 vivas), todas exit 0, todas `stdout_bytes` 0 o `None`, y el log de 0 bytes pese a que la rama `pass` escribe incondicionalmente. Causa: leía `.tool_result // .output`; Claude Code entrega la salida del agente en **`.tool_response`** (`hooks/_lib/normalize-stdin.sh` lo documenta en su propia matriz de compatibilidad: `.tool_result` es Kiro, `.result` es Devin). Con `AGENT_OUTPUT` vacío el hook salía en la tercera línea útil.

Segundo defecto encontrado al escribir el test: el log se escribía con `jq -n` (multi-línea) sobre `safe_jsonl_append`, que por contrato toma **una** línea. El archivo `.jsonl` era JSON pretty-printed; cualquier lector línea a línea revienta — de hecho reventó el test.

**Correcciones aplicadas** en `hooks/adversarial-review-gate.sh`:
- `jq -r '.tool_response // .tool_result // .output // empty'` (aditivo: no rompe Kiro/Devin).
- `jq -n` → `jq -nc` en las dos ramas de escritura.

> Aviso al operador: este hook **sí** está proyectado en `.claude/settings.json`. Con el arreglo va a empezar a escribir advertencias a stdout en PostToolUse de agentes de revisión sin hallazgos — que es su propósito, pero es ruido que hoy no existía. Revertible con un `git checkout` del archivo, o silenciable con `DISABLE_HOOK_ADVERSARIAL_REVIEW_GATE=true`.

### El test

`tests/hooks/test_adversarial_review_gate.py` — 15 casos.

- Debe advertir: review con `looks good` + cero hallazgos (severidad `prohibited_phrase_no_findings`); review sin ningún marcador (`no_findings`); **payload con `.tool_response`** (regresión del defecto de campo, con el número 176 escrito en el test); review detectada sólo por el `tool_input`.
- Debe callarse: review con hallazgo real `S2 CONCERN` (fila `pass`, sin WARNING); llamada que no es review (**cero** filas); salida vacía; herramienta ≠ Agent; killswitch por env.
- Formato: dos eventos deben producir exactamente dos líneas, cada una parseable sola.
- Nunca bloquea: parametrizado sobre las cinco formas de salida.

### Las dos corridas

Rojo 1 — el gate tal como estaba en `HEAD`:

```
FAILED tests/hooks/test_adversarial_review_gate.py::test_lgtm_review_is_warned_and_logged
FAILED tests/hooks/test_adversarial_review_gate.py::test_review_without_any_severity_marker_is_warned
FAILED tests/hooks/test_adversarial_review_gate.py::test_claude_code_payload_field_is_seen
FAILED tests/hooks/test_adversarial_review_gate.py::test_log_is_one_json_object_per_line
FAILED tests/hooks/test_adversarial_review_gate.py::test_review_with_a_real_finding_is_not_warned
5 failed, 10 passed in 5.14s
```

Rojo 2 — mutación: el gate da por buena toda review (`HAS_FINDING=true` de arranque):

```
FAILED tests/hooks/test_adversarial_review_gate.py::test_lgtm_review_is_warned_and_logged
FAILED tests/hooks/test_adversarial_review_gate.py::test_review_without_any_severity_marker_is_warned
FAILED tests/hooks/test_adversarial_review_gate.py::test_claude_code_payload_field_is_seen
FAILED tests/hooks/test_adversarial_review_gate.py::test_review_detected_from_the_prompt_alone
4 failed, 11 passed in 3.72s
```

Verde con el gate arreglado:

```
15 passed in 5.38s
```

---

## Lo que el auditor ve ahora

Primer `--sync` con los tests escritos: los tres seguían en `behavior_tests: []`. No era la inferencia AST — era que `tests/hooks/` no estaba en `TEST_ROOTS` de `scripts/hook_quality_audit.py`.

Antes de tocar nada, medí el impacto de agregarla (simulación sobre el módulo importado, sin escribir el manifest): **5 hooks** ganarían cobertura, cada uno acreditado por **un archivo nombrado según el hook que ejercita**. Ningún archivo de `tests/hooks/` nombra hooks como literales en masa (los tipo censo los enumeran dinámicamente), así que no hay acreditación al por mayor — que es justo el riesgo que la separación `census_tests` existe para evitar.

Con la corrección aplicada:

```bash
COS_ALLOW_PROTECTED_CONFIG_WRITE=1 .venv/bin/python3 scripts/hook_quality_audit.py --sync
.venv/bin/python3 scripts/hook_quality_audit.py --check
# hook-quality: OK (200 hooks, 200 syntax checks)
```

```
symlink-mutation-guard  -> ['tests/hooks/test_symlink_mutation_guard.py']
rate-limit-precheck     -> ['tests/hooks/test_rate_limit_precheck.py']
adversarial-review-gate -> ['tests/hooks/test_adversarial_review_gate.py']
```

Cobertura del manifest: **181 → 188** hooks con `behavior_tests`, **ninguno perdido**. Cuatro de los siete que ganan no son míos: `session-wrapup-trigger` y `teammate-idle` ya tenían tests dirigidos en `tests/hooks/` que el auditor no podía ver, y `control-plane-audit-hourly` / `pending-truth-drift-detector` vienen de tests que la sesión orquestadora agregó en `tests/behavior/` mientras esto corría.

Suites que consumen el auditor, corridas después del cambio: `tests/unit/test_hook_quality_coverage_inference.py`, `tests/contracts/test_hook_quality_system.py`, `tests/audit/test_hook_maturity_coverage.py`, `tests/audit/test_guard_maturity.py` → **27 passed**.

## Lo que NO hice y por qué

- **No registré `symlink-mutation-guard` ni `rate-limit-precheck` en `.claude/settings.json`.** Es el hallazgo más grande del encargo y la decisión es del operador: proyectar un hook que puede denegar cambia el comportamiento de todas las sesiones. Lo dejo medido, no aplicado.
- **No arreglé la incapacidad de fondo de `rate-limit-precheck`** (pasarle el retry count a `rate-limiter.sh`). Requiere un canal real entre hooks — archivo de estado o contrato de stdout — y eso es un ADR, no un parche. El test fija la incapacidad actual como contrato para que el rediseño se note.
- **No toqué `REQUIRED_BEHAVIOR_COVERAGE` ni ningún baseline.** Los tres hooks son `standard`/`quality`; ninguno estaba haciendo fallar `--check`. Meterlos ahí habría sido subir la exigencia para justificar el trabajo, no medir mejor.
- **No marqué nada `skip`/`xfail`** ni escribí tests de existencia.
- **No corrí la suite completa de `tests/hooks/`**: excede los 2 minutos por lentitud preexistente ajena a este cambio. Corrí mis tres archivos completos y los tipo censo por separado.

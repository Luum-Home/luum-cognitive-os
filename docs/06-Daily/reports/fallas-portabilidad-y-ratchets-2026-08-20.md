# Fallas de portabilidad y ratchets — 2026-08-20

## Resumen ejecutivo

Del lote de 14 fallas asignadas, 3 ya estaban en verde antes de tocar nada
(`test_protected-config-write-guard.py`) y 11 se reprodujeron. **Ninguna era del
árbol sucio**: las 11 se reprodujeron igual contra un árbol limpio de sólo lo que
viaja en HEAD. Quedan 9 en rojo, todas deuda real y todas de primitivas que
aterrizaron ayer y hoy por otras sesiones.

Arreglé 2 rojos con arreglos que reducen el problema:

- `scripts/proof-event-cadence-gate.sh` ya no exige un checkout git para correr.
- 3 claims de path fantasma en ADRs corregidos (130 → 127 fantasmas), y el
  baseline **bajado** de 129 a 127.

Y bajé un colchón que nadie había mirado: `blocking-gate: 10` con realidad 9.

## Correcciones a las premisas del encargo

1. **«`git worktree` NO está bloqueado».** Falso. `git worktree list` (lectura)
   funciona; `git worktree add` lo **bloquea el hook** `destructive-git-blocker`
   (ADR-055b), que pide token inline `# --allow-destructive` o
   `COS_ALLOW_DESTRUCTIVE_GIT=1` en el entorno que lanza el arnés. No me
   autoconcedí el bypass: usé `git archive HEAD | tar -x` como decía la otra
   mitad del encargo.

   ```
   git worktree add --detach <tmp> HEAD
   # => BLOCKED: destructive git op 'git worktree' is blocked by default (ADR-055b)
   ```

2. **«3 fallas en `test_protected-config-write-guard.py`».** Ese archivo pasa
   entero hoy (2 tests, ambos verdes). El conteo de 14 sobrestima el lote: lo
   reproducible eran 11.

3. **Hay un rojo que no es de ningún test de la lista: el conftest.** La primera
   corrida murió en el guard de telemetría del operador
   (`.cognitive-os/metrics/*.jsonl` creció durante la suite) — porque hay una
   sesión viva del operador escribiendo en paralelo, que es exactamente el caso
   que el propio guard documenta como `COS_ALLOW_OPERATOR_METRICS_WRITES=1`. No
   es una falla del lote; es ruido de correr con el arnés vivo. Todas las
   mediciones de abajo llevan esa variable puesta.

4. **El árbol limpio no es más limpio para todo.** `test_ram_ceiling.py` mide
   `.cognitive-os/` en disco, que no está versionado: en el árbol de `git archive`
   ese test pasa por ausencia del directorio, no por estar sano. Su rojo (419,8
   MiB > 400) es estado real de runtime, no del árbol.

5. **El baseline de ADRs no subió por un claim nuevo.** Verifiqué claim por claim
   contra el commit que escribió el baseline (`d416f56f0`): los 130 claims ya
   existían ahí y ninguno apuntaba a un archivo que existiera entonces. El +1 no
   quedó explicado por arqueología; lo cerré por el lado que pide el propio test
   ("Fix the ADR path claim"), arreglando claims reales.

## Árbol sucio vs deuda real: cómo lo determiné

El árbol tenía 55 entradas sucias (43 modificados, 12 sin trackear), 19 de ellas
`hooks/*.sh` y las proyecciones `.codex/hooks.json` / `.opencode/cos-hooks.json`
— trabajo en vuelo de otras sesiones, justo el material que leen los tests de
portabilidad. Hipótesis razonable, y falsa.

```bash
# árbol de sólo lo que viaja
CT=<scratchpad>/clean
git archive HEAD | tar -x -C "$CT"
cd "$CT" && COS_ALLOW_OPERATOR_METRICS_WRITES=1 PYTEST_ALLOW_NONVENV=1 \
  CLAUDE_PROJECT_DIR="$CT" <repo>/.venv/bin/python -m pytest -q -p no:randomly <los 10 archivos>
# => 11 failed, 28 passed
```

Contra el árbol sucio: `11 failed, 34 passed`. **El mismo 11.** Composición
idéntica salvo dos matices, ambos a favor de "deuda real":

- `test_ram_ceiling` pasa en el árbol limpio sólo porque ahí no existe
  `.cognitive-os/` (ver corrección 4).
- `test_os_only_scope_family_has_maintainer_metadata_and_non_user_plane` falla en
  el limpio y pasa en el sucio: el trabajo en vuelo de otra sesión **arregla** esa
  falla, no la causa.

Nota de reproducción: el árbol de `git archive` no es un repo git, y hay auditores
que llaman a `git check-ignore`; `scripts/audit_adr_path_reality.py` muere ahí con
`fatal: not a git repository`. Para esos, la medición limpia hay que hacerla con
`git show <commit>:<path>` desde el repo, no en el árbol extraído.

## Los ratchets: cuáles bajé, cuáles subí y con qué motivo

**Subí: ninguno.**

| Ratchet | Antes | Después | Realidad medida | Motivo |
|---|---|---|---|---|
| `manifests/adr-path-reality-baseline.json` → `max_findings` | 129 | **127** | 127 | Arreglé 3 claims fantasma; el test exige igualdad exacta y prohíbe el colchón |
| `manifests/decision-backing-ratchet.yaml` → `blocking-gate` | 10 | **9** | 9 | Colchón: un lugar libre con el gate diciendo "0 nuevas" |

Los 3 claims arreglados no son "renombres cosméticos": los tres apuntaban a un
archivo que existe, en otro directorio.

```
ADR-090-auto-skill-repair.md          hooks/_lib/auto-repair-dispatcher.sh -> hooks/auto-repair-dispatcher.sh
ADR-106-multi-session-safety-...md    scripts/pre-agent-snapshot.sh        -> hooks/pre-agent-snapshot.sh
ADR-106.synthesis.md                  scripts/pre-agent-snapshot.sh        -> hooks/pre-agent-snapshot.sh
```

Clasificación previa (¿deuda o coincidencia?): un cambio en el hook obliga a
tocar la cita del ADR — el ADR nombra ese archivo como pieza de su decisión. Es
deuda, no coincidencia.

```bash
.venv/bin/python scripts/audit_adr_path_reality.py --json | \
  .venv/bin/python -c "import json,sys;d=json.load(sys.stdin);print(len(d['findings']),d['baseline'])"
# antes: 130 129   → después de los 3 arreglos: 127 129   → tras --write-baseline: 127 127
```

## Colchones encontrados

**Uno, y lo bajé:** `blocking-gate: 10` con realidad 9. Un hueco libre para que
entre un hook bloqueante sin ADR mientras el gate reporta "0 nuevas".

```bash
.venv/bin/python scripts/audit_decision_backing.py --json | .venv/bin/python -c \
 "import json,sys;d=json.load(sys.stdin);print({k:(v['unbacked'],v['limit']) for k,v in d['counts'].items()})"
# antes:   {'blocking-gate': (9, 10), 'package': (18, 18), 'policy-manifest': (13, 12)}
# después: {'blocking-gate': (9, 9),  'package': (18, 18), 'policy-manifest': (13, 12)}
```

`package` está clavado en 18/18 (sin colchón). `adr-path-reality` **se volvió**
colchón al arreglar los claims (129 vs 127) y por eso lo bajé en el mismo
movimiento — el test lo detecta solo, que es la forma correcta de que un colchón
no sobreviva.

## Las dos direcciones de cada arreglo

**1. `scripts/proof-event-cadence-gate.sh` — portabilidad de raíz**

- Rojo antes: `test_product_scripts_do_not_depend_on_git_checkout_root` listaba
  `scripts/proof-event-cadence-gate.sh` como ofensor.
- Arreglo: la raíz sale de la ubicación del propio script
  (`dirname "${BASH_SOURCE[0]}"/..`), con `COGNITIVE_OS_PROJECT_DIR` por delante y
  una verificación de que ahí hay `manifests/`. Antes moría con `exit 2` fuera de
  un checkout.
- Verde después: `2 passed`.
- **Control de que no se aflojó la aserción**: no toqué el test. Y el script corre
  y da su veredicto desde fuera del repo, que es lo que el test protege:

  ```bash
  cd /tmp && bash <repo>/scripts/proof-event-cadence-gate.sh
  # [1]..[4] OK — el único chequeo en rojo es [0], por el guard de telemetría del
  # operador (sesión viva escribiendo hook-timing.jsonl), no por el cambio.
  ```

  Contra-prueba de que el arreglo no fue "sacarle la palabra al grep": la primera
  pasada dejó el string prohibido dentro de un comentario y el test **siguió en
  rojo**, señalando el mismo archivo. El gate mira el texto, no la intención.

**2. Claims de path en ADRs**

- Rojo antes: `phantom ADR paths regressed: 130 > baseline 129`.
- Arreglo: 3 claims corregidos al path real (los archivos existen, verificado con
  `ls -la hooks/auto-repair-dispatcher.sh hooks/pre-agent-snapshot.sh`).
- Verde después: `tests/audit/test_audit_ratchet_contracts.py::test_adr_path_reality_baseline_is_not_a_cushion` pasa.
- **Control**: el mismo test tiene la aserción inversa (`count == baseline`), así
  que bajar el baseline sin arreglar nada lo pondría rojo por colchón, y arreglar
  sin bajar el baseline también. Sólo pasa con las dos cosas hechas.

**3. `blocking-gate` 10 → 9**

- No había rojo que apagar: el gate pasaba con 9 ≤ 10.
- **Control de dirección**: bajar un ratchet no puede volver verde nada; sólo
  puede volver rojo. La prueba de que quedó pegado a la realidad es que ahora
  9 ≤ 9 — un solo hook bloqueante nuevo sin ADR lo pone en rojo, que antes no
  pasaba.

## Lo que NO hice y por qué

Las 9 rojas que quedan son deuda real y **casi todas son de primitivas que
aterrizaron ayer y hoy por las otras dos sesiones**. Tocarlas sería pisarles
trabajo en vuelo.

1. **`policy-manifest: 13 > 12`** (`test_decision_backing_reports_no_ratchet_regression`).
   El decimotercero es exactamente `manifests/external-claim-freshness.yaml`,
   agregado el 2026-08-19 por `402355c09`. Ni el manifiesto ni su commit ni ningún
   ADR lo nombran (`grep -rl "external-claim-freshness" docs/02-Decisions/adrs/`
   no devuelve nada). El arreglo honesto es escribir el ADR que lo gobierna o
   retirarlo; **subir el límite a 13 es el verde barato canónico** de esta
   familia, y el propio manifiesto lo dice ("Raising one requires a written reason
   here AND the finding it accepts — never 'to make the gate green'"). Decisión de
   operador, no mía. Numerar un ADR nuevo bajo tres sesiones concurrentes tampoco
   es algo para hacer de paso.

2. **`hook_projection_drift_audit` (2 tests)**: 5 hooks declarados activos que no
   llegan a ninguna proyección (`aci-observation-capture`,
   `post-git-orphan-notifier`, `publication-safety`, `rate-limit-drain`,
   `tool-sequence-capture`), con budget 1. El arreglo es cablearlos en
   `.codex/hooks.json` / `.opencode/cos-hooks.json` o declarar la omisión en
   `cognitive-os.yaml`. Los dos archivos de proyección están **modificados ahora
   mismo** por otra sesión: escribir ahí es garantía de conflicto. Además el
   budget está POR DEBAJO de la realidad (1 vs 5): no es colchón, es regresión, y
   subirlo está explícitamente prohibido por el mensaje del propio test.

3. **`project_scope_family` + `os_only_scope_family` + `primitive_behavior_depth`
   (3 tests)**: mismo origen único — 8 scripts con `proof_level: none`, es decir
   sin prueba pareada:

   ```
   scripts/audit_generated_file_edits.py     (sin trackear, sesión ajena en vuelo)
   scripts/audit_guard_mention_blocks.py     scripts/audit_hook_payload_fidelity.py
   scripts/audit_killswitch_activation.py    scripts/audit_test_import_resolvability.py
   scripts/checkout_parity.py                scripts/estimate_secret_detector_firing.py
   scripts/mutation_check_skill_gate.py
   ```

   `checkout_parity.py` y `mutation_check_skill_gate.py` son de los commits
   `f14dfb689` y `c6c165bca`, o sea de los otros dos agentes de esta tanda. El
   arreglo real es escribir la prueba pareada de cada uno; emparejarlos contra un
   test de familia existente para que el clasificador los deje de contar sería
   justamente aflojar la medición.

4. **`primitive_proof_execution_budget` (900 > 890)** y
   **`primitive_harness_partial_ratchets` (must-fix-parity 2)**: misma familia que
   el punto 3 — filas del registry cuya prueba no ejecuta la primitiva. Se arregla
   escribiendo pruebas que la corran, no moviendo el 890.

5. **`test_ram_ceiling` (419,8 MiB > 400)**: estado de runtime, no del árbol. El
   arreglo es rotar/podar telemetría bajo `.cognitive-os/`, y el encargo me
   prohíbe escribir ahí (`metrics/`, `runtime/`). Subir el techo sería mover la
   medición. Queda para quien pueda correr la rotación.

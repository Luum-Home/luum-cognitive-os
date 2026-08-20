<!-- SCOPE: os-only -->
# Borrado de los 5 hooks marcados BORRAR — re-verificación y resultado

> Fecha: 2026-08-19 · Encargo: re-verificar y borrar los cinco hooks que
> `docs/06-Daily/reports/triage-93-hooks-2026-08-19.md` marcó **BORRAR**.

## Resumen ejecutivo

- **Borré 2 de 5**: `singularity-check.sh` y `session-state-save.sh`.
- **Frené 3**: `code-review-on-commit.sh`, `secret-audit-pre-commit.sh` y
  `tool-discovery-trigger.sh` — los tres tienen **un test que los EJECUTA**
  (`subprocess.run` sobre el artefacto), que es el disqualificador explícito del
  encargo. Uno de ellos, además, es SCOPE `both` y vive en el ledger de adopción.
- **Dos motivos escritos más resultaron falsos**, y ninguno de los dos estaba en
  la lista de tres del triaje previo: `session-state-save.sh` dice "invoked by
  `session-cleanup.sh`" (ese archivo existe y **no lo invoca**), y
  `singularity-check.sh` dice "invoked by the `/singularity` skill" (**ningún
  skill lo nombra**). Van cinco motivos falsos en el lote.
- **Un tercer motivo falso, colateral**: `EXCLUDED_HOOKS.txt:30` decía que
  `_lib/singularity-suggestion.sh` es "sourced by singularity-check.sh". Lo
  sourcea `hooks/session-init.sh:303`. Si lo dejaba, quedaba un asiento apuntando
  a un archivo borrado. Corregido al llamador real.
- **Asientos limpiados: 21** (6 manifests, 3 adaptadores/descriptores `.ai/`,
  4 listas de test, 2 archivos de hook, 2 docs). Cero referencias residuales
  fuera de reportes históricos.
- **Gates**: `hook_quality_audit --check` OK (200/200) ·
  `primitive_behavior_depth_audit` **findings: 0** · el conteo del scorecard pasó
  a verde (estaba rojo antes de mi cambio, por otra causa).

## Correcciones a las premisas del encargo

1. **"Cinco marcadas BORRAR" — solo dos pasan las cinco verificaciones.** Tres
   tienen un test que las ejecuta. El encargo prohíbe explícitamente borrar en
   ese caso ("Verde barato prohibido: borrar algo cuyo test lo **ejecuta**"), y
   la prohibición se aplica igual cuando el test es la *portability proof
   dedicada* del propio hook: esa proof es evidencia de que el artefacto corre,
   no inventario. Detalle por hook abajo.

2. **La lista de asientos del encargo estaba incompleta: falta `.ai/`.** El
   encargo enumera manifests, tests, familia os-only, behavior-evidence,
   `cognitive-os.yaml`, `registration-allowlist.txt`, `EXCLUDED_HOOKS.txt` y
   baselines. **No menciona `.ai/`**, que tiene dos capas de asiento por
   primitiva: un descriptor propio en `.ai/primitives/hooks/hooks-<slug>.json`
   y una entrada en cada `.ai/adapters/{claude-code,codex}/adapter.json`. Los dos
   hooks borrados tenían descriptor; `singularity-check` estaba además en los
   **dos** adaptadores. Es el noveno mecanismo de registro del inventario.

   Comando: `grep -rn '<hook>\.sh' .ai/`

3. **`cognitive-os.yaml > harness.hooks` no tenía asiento para ninguno de los
   dos.** El encargo lo listaba como asiento a limpiar; verificado que no
   aplicaba, así que no toqué el archivo (que además me estaba vedado).
   Comando: `grep -n 'singularity-check\|session-state-save' cognitive-os.yaml` → 0.

4. **"Si un gate se pone rojo por tu borrado, arreglá el asiento" — dos de los
   tres rojos que encontré ya estaban rojos en HEAD, sin relación con el
   borrado.** Probado sin worktree (el guard ADR-055b bloquea `git worktree`):

   ```bash
   # los 3 orphans que fallan NO estaban whitelisteados en HEAD -> ya fallaban
   git show HEAD:tests/contracts/EXCLUDED_HOOKS.txt | grep -c 'post-git-orphan-notifier\|rate-limit-drain\|tool-sequence-capture'   # 0
   git show HEAD:tests/audit/test_hooks_contracts.py  | grep -c 'post-git-orphan-notifier\|rate-limit-drain\|tool-sequence-capture'  # 0
   # el conteo del scorecard tampoco cerraba en HEAD
   git ls-tree HEAD hooks/ --name-only | grep -c '\.sh$'                    # 256
   grep -n 'Total hook files on disk' docs/.../scorecard-hooks.md           # afirmaba 257
   ```

5. **`manifests/hook-quality.yaml` estaba desincronizado en HEAD por trabajo
   ajeno, no por el mío.** El `--sync` que pide el encargo agrega **una** línea
   (`tests/hooks/test_concurrent_write_guard_takes_a_lock.py`), un test que otra
   sesión ya commiteó sin re-sincronizar el manifest. Mi borrado no cambia nada
   en ese archivo: los dos hooks nunca estuvieron en el denominador de 200 hooks
   registrados. Incluyo el hunk porque dejarlo fuera deja el gate rojo, y lo
   declaro acá para que no se lea como mío.

6. **El instalador de pre-commit no toca ninguno de los cinco.** El triaje lo
   afirmaba para `code-review-on-commit`; lo confirmé y lo extiendo a
   `secret-audit-pre-commit`: `scripts/install-pre-commit.sh` symlinkea
   **únicamente** `hooks/pre-commit-gate.sh`, y `.git/hooks/pre-commit` no
   nombra a ninguno de los dos.

## Las cinco verificaciones, hook por hook

Las cinco preguntas, en el orden del encargo:
**(1)** ¿lo invoca `bash-hot-path-dispatcher.sh`? · **(2)** ¿está en
`templates/security-profiles/*.json`? · **(3)** ¿tiene telemetría (vivo **+**
rotados)? · **(4)** ¿algún test lo **ejecuta**? · **(5)** ¿su motivo escrito dice
la verdad?

| Hook | (1) dispatcher | (2) perfiles | (3) telemetría | (4) test que ejecuta | (5) motivo | Veredicto |
|---|---|---|---|---|---|---|
| `singularity-check.sh` | no | no | 0 / 0 | **no** | **falso** | **BORRADO** |
| `session-state-save.sh` | no | no | 0 / 0 | **no** | **falso** | **BORRADO** |
| `code-review-on-commit.sh` | no | no | 0 / 0 | **sí** | cierto | FRENADO |
| `secret-audit-pre-commit.sh` | no | no | 0 / 0 | **sí** | cierto | FRENADO |
| `tool-discovery-trigger.sh` | no | no | 0 / 0 | **sí** | cierto | FRENADO |

### (1) Hijos del dispatcher

Los 29 gates que `_run_gate` invoca están en
`hooks/bash-hot-path-dispatcher.sh:128-182`. Ninguno de los cinco aparece:

```bash
for h in code-review-on-commit singularity-check session-state-save \
         tool-discovery-trigger secret-audit-pre-commit; do
  printf '%-32s %s\n' "$h" "$(grep -c "$h" hooks/bash-hot-path-dispatcher.sh)"
done   # -> 0 los cinco
```

### (2) Perfiles de seguridad — el octavo mecanismo

```bash
for h in ...; do grep -l "$h\.sh" templates/security-profiles/*.json; done
# -> ninguno de los cinco. (Los 5 con vía de ejecución latente eran otros:
#    cosd-intent-submit, subagent-input-schema-validator, guardrails-validator,
#    parry-scan, semgrep-scan — y el triaje ya los había mandado a CONSERVAR.)
```

Y ninguno está en `.claude/settings.json` (`grep -c '<hook>\.sh'` → 0 los cinco).

### (3) Telemetría — vivo más los rotados

277.185 filas de `hook-timing` y 92.380 de `hook-health` (vivo + `.archive/*.gz`),
con el control positivo que exige el encargo:

| hook | timing | health |
|---|---|---|
| `protected-config-write-guard` (control) | 12.287 | 16.702 |
| `bash-hot-path-dispatcher` (control) | 9.942 | 0 |
| `destructive-git-blocker` (control, hijo del dispatcher) | **0** | **1.132** |
| los cinco candidatos | 0 | 0 |

El tercer control es el que importa: un hijo del dispatcher da 0 en `hook-timing`
y sigue vivo. Los cinco dan 0 en **las dos** fuentes.

### (4) ¿Algún test lo EJECUTA?

Esta es la verificación que cambió el resultado del encargo.

- **`code-review-on-commit.sh` → SÍ.**
  `tests/red_team/portability/test_code-review-on-commit.py:29-38` lo corre:
  `subprocess.run(["bash", str(ARTIFACT)], input=json.dumps(payload), ...)` con
  un payload real y `assert result.returncode == 0`.
- **`secret-audit-pre-commit.sh` → SÍ.**
  `tests/red_team/portability/test_secret-audit-pre-commit.py:13-15`:
  `subprocess.run(["bash", str(ARTIFACT)], cwd=tmp_path, ...)` +
  `assert result.returncode == 0`.
- **`tool-discovery-trigger.sh` → SÍ, y con aserción de comportamiento.**
  `tests/behavior/test_hooks_batch2.py::TestToolDiscoveryTrigger::test_skips_when_recent`
  escribe un `tool-discovery.jsonl` reciente, corre el hook con `run_hook(...)` y
  verifica que **no** diga "Scan due". Eso es el throttling del hook, no
  inventario.
- **`singularity-check.sh` → NO.** Lo nombran
  `tests/red_team/portability/test_os_only_scope_family.py:76` (que solo verifica
  `path.exists()` y metadata de scope) y `tests/audit/test_hooks_contracts.py:131`
  (lista `KNOWN_ORPHANS`). Ninguno lo ejecuta.
- **`session-state-save.sh` → NO.** Mismos dos, mismas líneas 74 y 130.

### (5) ¿El motivo escrito dice la verdad?

- **`singularity-check.sh` — FALSO.** `tests/contracts/EXCLUDED_HOOKS.txt:54`
  decía "invoked by /singularity skill, not by Claude events".
  `grep -rn 'singularity-check' skills packages/*/skills` → **cero**. El skill
  `/singularity` usa `cos_lib/singularity.py` directamente. Y el hook está
  env-gated a `SINGULARITY_CHECK=true`, que no se setea en ningún archivo del
  repo.
- **`session-state-save.sh` — FALSO.** `EXCLUDED_HOOKS.txt:90` decía "invoked by
  `session-cleanup.sh` or manually". `hooks/session-cleanup.sh` existe (9.031 B)
  y `grep -n 'session-state-save\|session_state' hooks/session-cleanup.sh`
  devuelve **nada**. Además el hook es **inerte por construcción**: arranca con
  `[ ! -f "$STATE_FILE" ] && exit 0`, y el único escritor de
  `.cognitive-os/session-state.json` es `packages/context-optimization/lib/session_state.py`,
  cuyo `save_state` no tiene ningún llamador de producción.
- **`code-review-on-commit.sh` — cierto.** "FUTURE: … not yet wired to Claude
  events": correcto, y sigue siendo verdad.
- **`secret-audit-pre-commit.sh` — cierto.** "invoked by git/security profile
  paths": no está cableado hoy, pero el script que envuelve
  (`scripts/cos-cross-stack-secret-audit`, 1.847 B, ejecutable) **existe**, así
  que el camino es real, no imaginario.
- **`tool-discovery-trigger.sh` — cierto.** "FUTURE: planned for PostToolUse
  Agent — not yet wired".

## Las que NO borré y por qué

### `code-review-on-commit.sh` — tres razones, cualquiera alcanza

1. **Test que lo ejecuta** (arriba).
2. **Es SCOPE `both`, no os-only.** Está ofrecido a los adoptantes en
   `docs/08-References/root/adoption-tiers.md:322` y pineado por dos proofs de
   familia que **leen el archivo**: `test_shared_hook_surfaces.py:10` y
   `test_low_confidence_scope_batch.py:15`. Borrarlo rompe dos proofs de familia
   además de la propia.
3. **La afirmación "ninguna capacidad" del triaje es refutable.** Los skills
   `code-review` y `pr-review` dan review **a demanda**; el hook da review
   **en el commit**. Son dos capacidades distintas, y el hook es la única
   superficie de hook de `cos_lib/code_reviewer.py` — una librería con su propia
   proof (`tests/red_team/portability/test_code_reviewer.py`) cuyo docstring dice
   textualmente que respalda a este hook.

### `secret-audit-pre-commit.sh` — barato no es lo mismo que muerto

El triaje lo llamó "el más barato de los 24" (485 B, sin asiento en
`registration-allowlist.txt`). Es cierto y no alcanza: tiene una portability
proof que lo **ejecuta**, y el auditor que envuelve
(`scripts/cos-cross-stack-secret-audit --release-scope --strict --json`, ADR-215)
existe y es ejecutable. Es un wrapper listo para registrarse, no un cascarón.
Lo que sí corresponde es cerrar la decisión de registrarlo o darlo de baja con el
ADR-215 en la mano; no es un borrado de poda.

### `tool-discovery-trigger.sh` — el test verifica el throttling, no la existencia

`test_skips_when_recent` es exactamente el tipo de test que el encargo manda a
respetar: monta el estado (`tool-discovery.jsonl` con timestamp reciente), corre
el hook y verifica la decisión que el hook toma. Borrarlo rompe una aserción de
comportamiento real.

## Asientos limpiados

Los dos hooks borrados, con todos sus asientos. Verificación final:
`grep -rn 'singularity-check\|session-state-save' hooks scripts cos_lib lib skills packages templates manifests tests .ai .claude rules cognitive-os.yaml cmd`
→ **NONE**.

| # | Asiento | `singularity-check` | `session-state-save` |
|---|---|---|---|
| 1 | archivo del hook (`hooks/*.sh`) | borrado | borrado |
| 2 | `hooks/_lib/registration-allowlist.txt` | línea 95 | línea 94 |
| 3 | `manifests/primitive-behavior-evidence.yaml` | bloque de 7 líneas | bloque de 7 líneas |
| 4 | `manifests/silent-failure-allowlist.yaml` | bloque de 10 | bloque de 10 |
| 5 | `manifests/primitive-consumer-availability.yaml` | bloque de 4 | bloque de 5 |
| 6 | `manifests/primitive-lifecycle.yaml` | bloque de 24 | bloque de 23 |
| 7 | `manifests/agentic-primitive-registry.lock.yaml` | bloque de 10 | bloque de 10 |
| 8 | `manifests/hook-registration-classification.yaml` | entrada JSON de 6 | entrada JSON de 6 |
| 9 | `.ai/primitives/hooks/hooks-<slug>.json` | archivo borrado | archivo borrado |
| 10 | `.ai/adapters/claude-code/adapter.json` | entrada de 7 | entrada de 7 |
| 11 | `.ai/adapters/codex/adapter.json` | entrada de 7 | (no tenía) |
| 12 | `tests/contracts/EXCLUDED_HOOKS.txt` | línea 54 | línea 90 |
| 13 | `tests/red_team/portability/test_os_only_scope_family.py` | línea 76 | línea 74 |
| 14 | `tests/audit/test_hooks_contracts.py` (`KNOWN_ORPHANS`) | línea 131 | línea 130 |
| 15 | `docs/09-Quality/root/hook-security-profiles.md` | fila de la tabla de exclusiones | (no tenía) |

**Asientos colaterales corregidos, no borrados:**

- `tests/contracts/EXCLUDED_HOOKS.txt:30` — el motivo de
  `_lib/singularity-suggestion.sh` decía "sourced by **singularity-check.sh**".
  Es falso y, tras el borrado, habría quedado apuntando a un archivo inexistente.
  Reescrito al llamador real, verificado en `hooks/session-init.sh:303`
  (`source "$(dirname "$0")/_lib/singularity-suggestion.sh"`).
- `docs/04-Concepts/architecture/functional-audit/scorecard-hooks.md:26` — el
  conteo de hooks en disco. Ver la sección de gates.

**Baselines y presupuestos: cero movimientos.** `manifests/hook-vitality-budget.yaml`
no tenía asiento para ninguno de los dos (y está siendo editado por otra sesión;
no lo toqué). `manifests/hook-quality.yaml` se regenera con `--sync` y no cambió
por el borrado. `cognitive-os.yaml` y `manifests/primitive-scope-classification.yaml`
no se tocaron (vedados por el encargo, y sin asiento para estos dos).

**Deuda declarada, no arreglada:** `cos_lib/session_state.py`
(canónico: `packages/context-optimization/lib/session_state.py`) queda sin ningún
consumidor de producción — el hook borrado era el único que llamaba a
`checkpoint()`. La librería tiene su propio test unitario de 450+ líneas y sus
propios asientos de manifest, así que es una primitiva aparte y su baja es otra
decisión. Queda escrita acá para que no se pierda.

## Los gates después

```bash
COS_ALLOW_PROTECTED_CONFIG_WRITE=1 .venv/bin/python3 scripts/hook_quality_audit.py --sync
.venv/bin/python3 scripts/hook_quality_audit.py --check
#   -> hook-quality: OK (200 hooks, 200 syntax checks)

.venv/bin/python3 scripts/primitive_behavior_depth_audit.py
#   -> {"findings": 0, "findings_by_code": {}, "total": 1450,
#       "by_proof_level": {"family": 659, "primitive-specific": 791}, ...}

.venv/bin/python3 -m pytest tests/audit/test_hooks_contracts.py \
  tests/red_team/portability/test_os_only_scope_family.py \
  tests/unit/test_singularity_suggestion.py \
  tests/contracts/test_primitive_harness_partials_contract.py -q -p no:randomly
#   -> 1 failed, 678 passed  (el failed es pre-existente, ver abajo)
```

`primitive_behavior_depth_audit` da **0 findings** sin tocar ningún presupuesto:
al sacar los dos hooks de `primitive-behavior-evidence.yaml` **y** de la lista
`OS_ONLY_PRIMITIVE_PROOF_BASELINE` de `test_os_only_scope_family.py` en el mismo
movimiento, la familia queda consistente. El test
`test_os_only_scope_family_is_registered_as_behavior_evidence` exige que cada
entrada del baseline tenga asiento en el manifest; sacar solo uno de los dos lados
lo habría puesto rojo.

### Lo que quedó rojo, y por qué no es mío

`tests/audit/test_hooks_contracts.py::test_no_orphan_hooks[post-git-orphan-notifier.sh]`
y `tests/contracts/test_orphan_hooks.py::test_no_orphan_hooks` fallan por **tres
hooks que no son ninguno de los cinco**: `post-git-orphan-notifier.sh`,
`rate-limit-drain.sh` y `tool-sequence-capture.sh`. Los tres están trackeados
desde commits anteriores y **ninguno estaba whitelisteado en HEAD** — o sea, ya
fallaban antes de tocar nada:

```bash
git show HEAD:tests/contracts/EXCLUDED_HOOKS.txt | grep -c 'post-git-orphan-notifier\|rate-limit-drain\|tool-sequence-capture'   # 0
git show HEAD:tests/audit/test_hooks_contracts.py  | grep -c 'post-git-orphan-notifier\|rate-limit-drain\|tool-sequence-capture'  # 0
```

No los agregué a `KNOWN_ORPHANS` ni a `EXCLUDED_HOOKS.txt`: sería exactamente el
verde barato que el encargo prohíbe, y encima sobre hooks ajenos a mi lote.

### El conteo del scorecard: arreglado, no maquillado

`test_hook_counts_match_scorecard` compara los hooks en disco contra el número
escrito en `scorecard-hooks.md`. **En HEAD ya estaba roto**: 256 en disco contra
**257** declarados. Mi borrado lo llevó a 254. Lo actualicé a 254 recontando en el
momento de escribir, no copiando el número del encargo:

```python
n = len(sorted(p.name for p in Path("hooks").glob("*.sh") if p.is_file()))
```

Es un conteo de la realidad, no un presupuesto: la línea dice cuántos archivos
hay, y hay 254. La nota de la fila deja constancia de que el 257 anterior nunca
cerró.

## Contaminación del commit `376976744` — declarada, no disimulada

El commit del borrado salió **dos veces**. La primera vez
(`e34f5b8d1`) fue con pathspec explícito y contenía exactamente mis 20 archivos.
Pero el mensaje quedó mal: el `cat > msg.txt` que lo generaba viajaba dentro de un
comando que un guard bloqueó antes de ejecutarlo, y el `git commit -F` terminó
leyendo un `msg.txt` que **otro agente hermano de esta misma sesión había escrito
en el mismo scratchpad** — el scratchpad no está aislado por agente, solo por
sesión. El commit quedó con el asunto de otro trabajo
("chore(poda): borrar el shim rate-limit-protection…").

Al corregirlo con `git commit --amend -F <mensaje correcto>` **sin repetir el
pathspec**, el amend reconstruyó el commit desde el índice compartido — que en ese
momento tenía staged el trabajo en vuelo de las otras dos sesiones. Resultado:
`376976744` tiene 42 archivos, no 20. Los 22 que no son míos:

```
.claude/settings.json                     scripts/claim_proof_audit.py
cognitive-os.yaml                         scripts/docs_execution_audit.py
cos_lib/measurement.py                    scripts/external_claim_freshness_audit.py
templates/security-profiles/minimal.json  scripts/hook_test_reality_census.py
templates/security-profiles/standard.json scripts/primitive_row_audit.py
templates/security-profiles/paranoid.json scripts/reduction_backlog.py
scripts/apply-efficiency-profile.sh       docs/06-Daily/reports/primitive-row-audit-latest.{json,md}
scripts/_lib/settings-driver-claude-code.sh  docs/06-Daily/reports/reduction-backlog-latest.{json,md}
docs/06-Daily/reports/recorte-perfil-default-2026-08-19.md
tests/contracts/test_emitted_counts_declare_provenance.py
tests/red_team/portability/test_measurement.py
tests/unit/test_measurement_census.py
```

**Ningún trabajo se perdió**: esos archivos están commiteados, con su contenido
intacto; lo que está mal es la atribución, porque viajan bajo mi mensaje. No lo
revierto: otra sesión ya commiteó encima (`05eec8b5f`), y reescribir historia
compartida mientras dos agentes escriben en el mismo checkout hace más daño que
un commit gordo. Queda escrito acá para que el `git log` no mienta sin aviso.

**Dos lecciones operativas, para que no se repita:**

1. **El scratchpad de sesión es compartido entre agentes hermanos.** Un nombre
   genérico (`msg.txt`, `out.json`, `t.jsonl`) es una colisión esperándote.
   Nombres únicos por tarea.
2. **`git commit --amend` ignora el pathspec del commit original.** Bajo sesiones
   concurrentes, amend sobre un índice compartido barre lo ajeno. Si hay que
   corregir un mensaje en un checkout compartido, hay que repetir el pathspec
   (`git commit --amend -F msg -- <paths>`) o no amendear.

## `tests/contracts/` completo: 4 fallos, 2 eran míos y están arreglados

La corrida completa (`-q -p no:randomly --timeout=300`, 11m12s) dio
**4 failed, 859 passed, 4 skipped, 16 xfailed**.

**Míos, arreglados** (commit `6f9f78d74`):

- `test_portable_ai_completion.py::test_adapter_manifests_are_generated_for_profiles`
  — `assert 864 == 862`. Al sacar las entradas de `projected_primitives` de los
  `adapter.json` dejé `projected_primitive_count` con el número viejo. Corregido a
  862 y 827, que es `len(projected_primitives)`.
- `test_portable_ai_overlay.py::test_portable_ai_overlay_is_generated_and_current`
  — el overlay quedó stale en `context.json`, `profiles/claude.json` y
  `profiles/codex.json`. Regenerado con `scripts/portable_ai_overlay.py`, que tocó
  exactamente esos 5 archivos y ninguno ajeno. Los dos tests: **13 passed**.

Es el mismo error dos veces, y vale anotarlo: **editar a mano un artefacto
generado deja los contadores derivados apuntando al conteo viejo**. El asiento no
es solo la fila; es la fila más todo lo que la cuenta.

**No míos, quedan abiertos:**

- `test_primitive_harness_partial_ratchets.py::test_primitive_harness_partial_debt_does_not_regress`
  — falla en `assert coverage["summary"]["unclassified_gaps"] == 0` con **2**.
  Un borrado solo puede **quitar** primitivas, no crear un gap sin clasificar para
  otra; las dos candidatas son primitivas nuevas de las sesiones concurrentes
  (`docs/06-Daily/reports/primitive-harness-{coverage,partials}-latest.*` ya
  estaban dirty antes de que yo tocara nada). **No las clasifiqué en
  `primitive-harness-gap-policy.yaml`**: clasificar la primitiva de otro para
  apagar el rojo es exactamente el verde barato prohibido. Queda para quien las
  agregó.
- `test_ram_ceiling.py::test_so_vitals_reports_disk_under_ceiling` — `.cognitive-os/`
  ocupa 407.8 MiB contra un techo de 400.0. Es estado de runtime, y el encargo me
  prohíbe escribir o borrar bajo `.cognitive-os/`.

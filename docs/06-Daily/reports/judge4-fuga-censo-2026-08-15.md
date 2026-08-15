# Juez 4 — Fuga y censo: qué se proyecta a consumidores y qué ya llegó

Fecha: 2026-08-15
Alcance: read-only sobre `luum-agent-os` + las 21 instalaciones bajo `~/Projects`.
Estado de la máquina al correr: swap 37.6G/38.9G (96.8%), load 15.40. **Plan degradado: no se corrió la suite de tests.** Todo lo de acá es lectura de código, una instalación limpia en scratchpad, y barrido de filesystem.

---

## 1. Veredicto

**Es riesgo, no incidente.** Ninguno de los archivos sensibles llegó a ninguna instalación consumidora: `maintainer_experiment.py`, `maintainer_proposals.py` y `public_claim_gate.py` están en **0 de 17** instalaciones con `cos_lib/`. Lo que sí hay es un contrato de scope que no gobierna: el mecanismo que efectivamente decide qué viaja no es el marcador `# SCOPE:`, y falla en las dos direcciones.

---

## 2. La política real

`scripts/cos_init.py:293-295`:

```python
    # No SCOPE header → include unconditionally
    if not scope_val:
        return True
```

La premisa del encargo es **correcta en la letra**: un archivo sin marcador pasa el filtro. La docstring de `scope_allows` (línea 259-263) lo declara explícitamente: *"Files without a SCOPE header are universal and always allowed."*

**Pero `scope_allows` no es el selector — es un filtro sustractivo.** Nunca elige archivos; solo puede vetar los que otro mecanismo ya eligió. Y ese otro mecanismo es distinto en cada superficie:

| Superficie | Quién SELECCIONA | Rol de `scope_allows` | Línea |
|---|---|---|---|
| `templates/*.md`, `*.json` | glob, **en todos los modos** | **único filtro** | 1976 |
| `rules/*.md` | glob **solo en `--full`**; en default, allowlist del manifiesto | filtro secundario | 1805 |
| `hooks/*.sh` | glob **solo en `--full`**; en default, allowlist del manifiesto (45 hooks) | filtro secundario | 1836 |
| `cos_lib/*.py` | **`lib_closure.compute_closure(projected_hook_paths, ...)`** — grafo de imports de los hooks proyectados | filtro secundario | 1909 |
| `scripts/*` | **allowlist por nombre literal** (4 funciones `_install_*_primitive`) | filtro secundario | 1453, 1462, 1483, 1523 |
| `cos_lib/__init__.py` | copia **incondicional** | **ninguno — lo saltea** | 1889-1891 |

El allowlist que ataja el default-include está en `manifests/primitive-install-boundary.yaml` (`profiles.default.primitives.hooks`, 45 entradas). La pista del coordinador se confirma.

Por eso los tres sensibles no viajan: no tienen marcador, `scope_allows` los dejaría pasar, pero **ningún hook del allowlist default los importa**, así que la clausura nunca los propone. Los protege una propiedad emergente del grafo de imports, no una decisión de scope.

---

## 3. El censo

Archivos sin marcador `# SCOPE:` en las superficies proyectables, con symlinks resueltos:

```bash
cd "$REPO"   # raíz de luum-agent-os
check() { d="$1"; tot=0; nomark=0; osonly=0
  while IFS= read -r f; do r=$(readlink -f "$f"); [ -f "$r" ] || continue
    tot=$((tot+1))
    if head -3 "$r" | grep -qE '(# SCOPE:|<!-- SCOPE:)[[:space:]]+[a-zA-Z_/-]+'; then
      head -3 "$r" | grep -qE 'SCOPE:[[:space:]]+os-only' && osonly=$((osonly+1))
    else nomark=$((nomark+1)); fi
  done < <(eval "ls $d 2>/dev/null")
  echo "$d :: total=$tot sin_marcador=$nomark os_only=$osonly"; }
check 'templates/*.md templates/*.json'
check 'rules/*.md'
check 'hooks/*.sh'
check 'cos_lib/*.py'
```

Resultado:

| Superficie | Total (symlinks resueltos) | Sin marcador | `os-only` |
|---|---|---|---|
| `templates/` | 18 | **1** | 8 |
| `rules/` | 129 | **0** | 17 |
| `hooks/` | 257 | **0** | 102 |
| `cos_lib/` | 369 | **69** | 90 |
| **Censo total** | | **70** | |

`rules/` y `hooks/` están 100% marcados. Todo el censo se concentra en `cos_lib/` (69) más un template (`task-closure-ledger.example.json`).

**Mi número es 70, no 75.** Lista completa en el Anexo A — nada truncado.

---

## 4. ¿Se envía de verdad?

Instalación limpia, modo default, en directorio descartable del scratchpad:

```bash
TESTDIR="$SCRATCHPAD/cleaninstall-$$"
case "$TESTDIR" in */Projects/*) echo "ABORT"; exit 9;; esac   # guarda: TARGET_DIR es relativo
mkdir -p "$TESTDIR" && cd "$TESTDIR"
bash "$REPO/install.sh" --from "$REPO" --skip-manifest-check </dev/null
```

| | Censo (lo que la política permitiría) | Instalado de verdad | No llegó |
|---|---|---|---|
| `cos_lib/` sin marcador | 69 | **4** | **65** |
| `templates/` sin marcador | 1 | **1** | 0 |
| **Total** | **70** | **5** | **65** |

Los 4 que sí viajan: `project_paths.py`, `snapshot_manager.py`, `telemetry_banner.py`, `time_utils.py`.

**Por qué no llegan los otros 65:** la clausura de imports (`compute_closure`) parte de los 45 hooks del allowlist default y solo propone lo alcanzable. La instalación limpia proyecta 39 módulos `cos_lib` de 369 disponibles. Los 65 restantes del censo nunca son candidatos.

Traducido: **el 93% del censo no viaja por una razón que no es el contrato de scope.** Si mañana un hook del allowlist agrega un `import` a `cos_lib.public_claim_gate`, viaja — sin que ningún gate se ponga rojo, porque el archivo no tiene marcador y `scope_allows` devuelve `True`.

---

## 5. Tabla forense por instalación

```bash
cd ~/Projects && find . -maxdepth 4 -type d -name '.cognitive-os' -not -path '*/node_modules/*'
```

21 directorios `.cognitive-os`; 17 tienen `cos_lib/`.

| Instalación | módulos `cos_lib` | del censo | `os-only` | sin marcador | fecha | sensibles |
|---|---|---|---|---|---|---|
| fcj/cienciayjusticia-voting | 39 | 4 | 1 | 4 | 2026-07-20 | **ninguno** |
| luum/FinOpenPOS | 39 | 4 | 1 | 4 | 2026-08-15 | **ninguno** |
| luum/accounting | 39 | 4 | 1 | 4 | 2026-07-20 | **ninguno** |
| luum/aisotropy | 39 | 4 | 1 | 4 | 2026-07-20 | **ninguno** |
| luum/cognitive-layer | 39 | 4 | 1 | 4 | 2026-07-20 | **ninguno** |
| luum/cos-consumer-e2e-drill | 39 | 4 | 1 | 4 | 2026-07-20 | **ninguno** |
| luum/luum-agent-harness | 39 | 4 | 1 | 4 | 2026-07-20 | **ninguno** |
| luum/luum-cybersecurity | 39 | 4 | 1 | 4 | 2026-07-20 | **ninguno** |
| luum/luum-interface-layer | 39 | 4 | 1 | 4 | 2026-07-20 | **ninguno** |
| **luum/luum-lang** | **83** | **6** | 1 | 6 | 2026-07-20 | **ninguno** |
| luum/luum-platform-lab | 39 | 4 | 1 | 4 | 2026-07-20 | **ninguno** |
| luum/luum-talent | 39 | 4 | 1 | 4 | 2026-07-20 | **ninguno** |
| luum/luum-woocommerce-distrinorth | 39 | 4 | 1 | 4 | 2026-07-20 | **ninguno** |
| magil/magil-openclaw | 39 | 4 | 1 | 4 | 2026-07-20 | **ninguno** |
| matias-amendola/live-profile | 39 | 4 | 1 | 4 | 2026-07-20 | **ninguno** |
| n1u | 39 | 4 | 1 | 4 | 2026-07-20 | **ninguno** |
| fcj/rbvm-platform | sin `cos_lib` | — | — | — | — | — |
| luum (raíz) | sin `cos_lib` | — | — | — | — | — |
| luum/cognitive-os-demo | sin `cos_lib` | — | — | — | — | — |
| luum/luum-agent-os/--help | sin `cos_lib` | — | — | — | — | — |

Búsqueda de sensibles: `ls .cognitive-os/cos_lib/ | grep -E 'maintainer_|public_claim|prelaunch|publication_safety|product_answer|release_freeze|cross_stack|fleet_conf|script_exposure|history_'` → **cero coincidencias en las 17**. Amplié el patrón más allá de los tres del encargo, al mismo tenor; tampoco hay.

**Outlier: `luum-lang`** tiene 83 módulos en vez de 39 (44 extra, entre ellos `dispatch.py`, `qwen_provider.py`, `policy_eval.py`, `cosd_auth_guard.py`, `memory_governance.py`). Perfil distinto o install con `--full`. Ninguno es sensible, pero es la única instalación fuera de patrón y explica su `del censo = 6`.

### Dirección inversa: `os-only` dentro de consumidores

Cada instalación tiene exactamente **1** archivo marcado `os-only`: **`cos_lib/__init__.py`**, que en los consumidores dice `# SCOPE: os-only`.

La instalación limpia de hoy tiene **0**. La diferencia es una edición del origen:

```bash
git log --format='%h %ad %s' --date=short -L1,1:cos_lib/__init__.py
git show 5ba9de934 -- cos_lib/__init__.py
```

```
-# SCOPE: os-only
+# SCOPE: both
```

commit `5ba9de934`, 2026-07-20, titulado **"fix(tests): eliminate brittle-by-construction test failures"**.

El mecanismo importa más que el archivo: `cos_init.py:1889-1891` copia `__init__.py` **sin pasar por `scope_allows`**. La declaración `os-only` nunca se honró. El 2026-07-20 se resolvió cambiando la **declaración** para que coincida con lo que el código hacía, en vez de arreglar la ruta de copia. Es el verde barato del gate: el contrato se aflojó hasta la conducta. Hoy `both` es defendible (un paquete necesita su `__init__`), pero el bypass sigue ahí: si mañana `__init__.py` importa algo, viaja igual.

---

## 6. Correcciones a las premisas del encargo

1. **"~75 archivos sin marcador se proyectan por default"** — mal en dos puntos. El censo es **70**, no 75. Y de esos, **5 se proyectan**, no 70. El resto lo ataja la clausura de imports aguas arriba.
2. **"`cos_init.py:294` es la política que proyecta"** — media verdad. La línea existe y dice eso, pero `scope_allows` es sustractivo, no selectivo. La política que decide es `compute_closure` + `manifests/primitive-install-boundary.yaml`.
3. **"`maintainer_*` y `public_claim_gate` se proyectan"** — falso. Cero en instalación limpia y cero en las 17 reales.
4. **Dato del coordinador: "39 módulos, 4 sin marcador" en FinOpenPOS** — **confirmado**, y reproducido idéntico en instalación limpia y en 15 instalaciones más.
5. **Dato del coordinador: "`__init__.py` declara `SCOPE: os-only` y está instalado igual"** — **confirmado en los consumidores, desactualizado respecto del origen**. Hoy el origen dice `both` desde `5ba9de934` (2026-07-20). El hallazgo real no es el marcador sino que la ruta de copia saltea el filtro.
6. **Antigüedad de los sensibles**: `git log --diff-filter=A` los data el **2026-07-10** (commit `785ced2f3`), o sea existían antes de 15 de las 16 instalaciones (2026-07-20) y nunca viajaron. Su ausencia no es suerte de timing.

---

## 7. VERIFICADO vs NO VERIFICADO

### VERIFICADO
- Texto y semántica de `scope_allows` (`cos_init.py:255-300`) y sus 8 call sites.
- Las 4 superficies y su selector real; allowlist de 45 hooks en `manifests/primitive-install-boundary.yaml`.
- Censo de 70 sin marcador, symlinks resueltos con `readlink -f`.
- Instalación limpia default: 39 `cos_lib`, 43 hooks, 10 templates; 4 del censo presentes.
- Ausencia de los sensibles en las 17 instalaciones con `cos_lib`.
- `__init__.py` `os-only` en los 17 consumidores; flip a `both` en `5ba9de934` (2026-07-20).
- Alta de los tres sensibles: 2026-07-10, `785ced2f3`.
- Bypass de `scope_allows` en la copia de `__init__.py` (líneas 1889-1891).

### NO VERIFICADO
- **Modo `--full`**: no lo corrí. Ahí `rules/` y `hooks/` pasan a glob y el censo relevante cambia. Los 102 hooks `os-only` y 17 rules `os-only` sí serían filtrados por `scope_allows`, pero no medí qué pasa con lo no marcado en esa ruta.
- **Scope `all`**: `scope_allows` devuelve `True` sin leer nada (línea 271). No lo ejercité.
- **Instalaciones fuera de `~/Projects`**: solo barrí ese árbol, `-maxdepth 4`.
- **Fechas de instalación**: son `mtime` del directorio `.cognitive-os`, que el runtime toca. Son cota superior de "última escritura", no fecha de instalación original.
- **Otras superficies**: `skills/`, `packages/`, `commands/` no entraron en el censo. Solo miré las 4 que tocan `scope_allows` con glob o clausura.
- **Suite de tests**: no corrida por presión de swap (96.8%).

### Nota de higiene
`git status --porcelain` antes y después: aparecieron `M opencode.json` y dos reportes `judge3-*` que no estaban en mi línea base. **No son míos**: mi install corrió con `harness=claude` y `cos_init.py` solo escribe `opencode.json` cuando `harness == "opencode"` (línea 1087); además no hay `opencode.json` en mi TESTDIR. Hay sesiones concurrentes escribiendo en el repo. No toqué ningún archivo del operador ni de otras sesiones.

---

## 8. Las tres acciones

**1. Cerrar el bypass de `__init__.py` antes que el censo.** Es el único lugar donde una declaración explícita `os-only` se ignora. Es una línea.

```bash
# prueba: declarar os-only en el origen y verificar que NO viaja
sed -i '' '1s/.*/# SCOPE: os-only/' cos_lib/__init__.py   # en un worktree, no en main
cd "$SCRATCHPAD/probe" && bash <repo>/install.sh --from <repo> --skip-manifest-check </dev/null
head -1 .cognitive-os/cos_lib/__init__.py   # debe fallar el install o no copiarse
```

**2. Invertir el default de `scope_allows`: sin marcador = no viaja.** Hoy el contrato es fail-open y lo que lo salva es la clausura de imports, que nadie declaró como control de scope. Con 69 archivos sin marcador en `cos_lib`, un `import` nuevo alcanza para publicar cualquiera.

```bash
# prueba: el censo de "sin marcador" en superficies proyectables debe dar 0
bash scripts/censo-scope.sh   # a escribir; exit 1 si sin_marcador > 0
```

**3. Marcar los 69 de `cos_lib` (Anexo A) y agregar el gate a CI.** Sin el gate, el marcado se degrada solo.

```bash
# prueba: gate que corre sobre el filesystem, no sobre el índice (como CI)
git worktree add /tmp/wt-scope HEAD && cd /tmp/wt-scope && bash scripts/censo-scope.sh; echo $?
```

---

## Anexo A — Censo completo (70 archivos sin marcador `# SCOPE:`)

### `cos_lib/` (69)

En **negrita** los 4 que efectivamente se proyectan en el install default.

```
adapter_compile.py              external_tool_intelligence.py   rate_limit_tracker.py
adaptive_profile.py             fleet_confidence.py             release_freeze.py
agent_input_validator.py        friction_telemetry.py           retry_tracker.py
agent_redirect_protocol.py      harness_environment.py          reward_signal_quality.py
agent_spawn_benchmark.py        history_rewrite_ledger.py       script_exposure_audit.py
ai_provider_identity_guard.py   history_sanitization.py         script_io.py
anchored_summary.py             imported_pattern_closure.py     service_mode_readiness.py
context_compressor.py           key_learning_capture.py         session_lifecycle.py
cosd_grant.py                   language_dependence_audit.py    session_watchdog_lib.py
cosd_grant_store.py             maintainer_experiment.py        similarity.py
cross_stack_adoption_truth.py   maintainer_impact.py            skill_runner.py
cross_stack_license_audit.py    maintainer_proposals.py         **snapshot_manager.py**
cross_stack_secret_audit.py     operational_status.py           sprint_orchestrator.py
decision_tracker.py             outcome_failure_queue.py        sprint_test_aggregator.py
delete_intent.py                pattern_detector.py             stash_ops.py
dependency_adoption_gate.py     performance_ledger.py           stash_provenance.py
dispatch_optimizer.py           prelaunch_audit.py              task_reconciliation.py
exercised_coverage.py           primitive_contracts.py          telemetry_aggregator.py
                                primitive_parser.py             **telemetry_banner.py**
                                primitive_readiness_common.py   **time_utils.py**
                                product_answer.py               tool_budget_catalog.py
                                **project_paths.py**            tool_discovery_preuse.py
                                promote_from_telemetry.py       tool_replay_ledger.py
                                public_claim_gate.py            trace_joiner.py
                                publication_safety.py           validation_lanes.py
                                quota_pressure.py
```

### `templates/` (1)

```
task-closure-ledger.example.json     ← sí se proyecta (install default)
```

---

## Anexo B — Comando de reproducción del barrido forense

```bash
SP=<scratchpad>; REPO=<raíz de luum-agent-os>
cd "$REPO"
for f in cos_lib/*.py; do r=$(readlink -f "$f"); [ -f "$r" ] || continue
  head -3 "$r" | grep -qE '(# SCOPE:|<!-- SCOPE:)[[:space:]]+[a-zA-Z_/-]+' || basename "$r"; done | sort > $SP/censo-coslib.txt
cd ~/Projects
find . -maxdepth 4 -type d -name '.cognitive-os' -not -path '*/node_modules/*' | sed 's|/.cognitive-os$||' | sort | while read -r inst; do
  d="$HOME/Projects/${inst#./}/.cognitive-os/cos_lib"; [ -d "$d" ] || { echo "${inst#./} sin-coslib"; continue; }
  tot=$(ls "$d"/*.py 2>/dev/null | wc -l | tr -d ' '); cen=0; osonly=0; nomark=0
  for f in "$d"/*.py; do b=$(basename "$f")
    grep -qx "$b" $SP/censo-coslib.txt && cen=$((cen+1))
    if head -3 "$f" | grep -qE '(# SCOPE:|<!-- SCOPE:)[[:space:]]+[a-zA-Z_/-]+'; then
      head -3 "$f" | grep -qE 'SCOPE:[[:space:]]+os-only' && osonly=$((osonly+1))
    else nomark=$((nomark+1)); fi; done
  sens=$(ls "$d" | grep -E 'maintainer_|public_claim|prelaunch|publication_safety|product_answer|release_freeze|cross_stack|fleet_conf|script_exposure|history_' | tr '\n' ',')
  printf '%-42s %4s %4s %4s %4s %s %s\n' "${inst#./}" "$tot" "$cen" "$osonly" "$nomark" \
    "$(stat -f '%Sm' -t '%Y-%m-%d' "$HOME/Projects/${inst#./}/.cognitive-os")" "${sens:-—}"
done
```

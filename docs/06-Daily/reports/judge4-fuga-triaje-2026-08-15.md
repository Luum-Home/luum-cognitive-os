# Juez 4 — Triaje de fuga: de lo que se proyecta, ¿qué importa?

Fecha: 2026-08-15 · Modo: read-only · Repo: `luum-agent-os`

Recursos al arrancar: `sysctl vm.swapusage` → 37688/38912 MB usados (96.9%),
`uptime` → load 23.79. **Degradación declarada:** no se corrió la suite de tests
ni ningún barrido de repo completo. Se corrió **una sola** instalación real
(contenida en scratchpad, `HOME` y `COS_REGISTRY_FILE` redirigidos) para obtener
el conjunto proyectado por evidencia y no por lectura de código.

---

## 1. Veredicto

**De los 144 archivos sin marcador que efectivamente aterrizan en un consumidor,
importan 3. Uno de ellos es grave y la premisa del encargo no lo menciona.**

Los tres archivos sensibles nombrados en el encargo —`maintainer_experiment.py`,
`maintainer_proposals.py`, `public_claim_gate.py`— **no se proyectan a ningún
consumidor**. Ninguno de los tres llega.

---

## 2. Conteo por categoría

Universo triado: los **144** archivos sin marcador `SCOPE:` que aterrizan en una
instalación `COS_INSTALL_SCOPE=both --full --harness claude` (el caso más amplio
del surface de consumidor).

| Categoría | Archivos | Nota |
|---|---:|---|
| **FUGA DE INFORMACIÓN** | **2** | uno crítico, uno de proceso interno |
| **FUGA DE CAPACIDAD** | **2** | 1 dentro del set sin marcador, 1 *marcado* `both` (corrección a la premisa) |
| **RUIDO** | 12 | fixtures, ejemplos, manifiestos generados |
| **DEBERÍA VIAJAR** | **129** | 6 módulos `cos_lib` + 123 archivos de skills |

Nota sobre el reparto: los 125 archivos de skills sin marcador `SCOPE:` **no**
caen bajo la política "sin marcador → incluir": pasan por `skill_scope_allows()`,
que tiene un fallback legado sobre el campo `audience:` del frontmatter. De los
125, **125 declaran `audience:` explícitamente** (72 `project`, 43 `both`,
1 `os-dev`, 1 `human`). Es una superficie **gobernada**, no una fuga por defecto.
Excepción: el único `os-dev`, tratado abajo.

Comando:

```bash
# instalación real contenida + clasificación por marcador
python3 scripts/cos_init.py --full --harness claude   # cwd=fixture, HOME y COS_REGISTRY_FILE redirigidos
find . -type f \( -name '*.py' -o -name '*.sh' -o -name '*.md' \
  -o -name '*.json' -o -name '*.yaml' -o -name '*.txt' \) | while read -r f; do
  s=$(head -3 "$f" | grep -m1 -oE '(# SCOPE:|<!-- SCOPE:)[[:space:]]+[a-zA-Z_/-]+' | awk '{print $NF}')
  printf '%s\t%s\n' "${s:-NONE}" "$f"
done | awk -F'\t' '{c[$1]++} END{for(k in c) print c[k]"\t"k}' | sort -rn
# → 503 both / 144 NONE / 6 project / 0 os-only
```

Dato relevante del mismo comando: **cero archivos `os-only` aterrizan**. El filtro
funciona perfectamente para lo que está marcado. El problema es exclusivamente lo
que no lo está — y no en el volumen que la premisa supone.

---

## 3. Tabla detallada de las fugas

| Archivo (destino en el consumidor) | Categoría | Qué expone | Línea que lo prueba |
|---|---|---|---|
| `.cognitive-os/provenance-scan.yaml` ← `manifests/provenance-scan.yaml` | **INFORMACIÓN** | **5 nombres de proyectos/clientes privados del mantenedor**, embebidos en la regex `forbidden_paths` de la propia denylist de confidencialidad | `manifests/provenance-scan.yaml:5` — `forbidden_paths: - "(?i)Projects/(?:…5 nombres…)[A-Za-z0-9._/-]*"` |
| `.cognitive-os/hooks/cos/_lib/registration-allowlist.txt` | **INFORMACIÓN** | Estado de madurez interno del OS: 260 líneas listando hooks "que existen en disco pero no están cableados", con referencias a un plan interno por fases y a ADRs en soak pendiente | `hooks/_lib/registration-allowlist.txt:9` (`Grandfathered at Phase 1 of Stabilization Mega Plan (2026-04-11)`), `:14` (`As each hook is wired in Phase 3+…`), `:257` (`manual_trigger pending ADR-270 acceptance + soak`), `:259` (`Wiring deferred until Phase 3 soak confirms acceptable false-positive rate`) |
| `.cognitive-os/skills/cos/deep-tool-research/SKILL.md` | **CAPACIDAD** | Skill declarada `audience: os-dev` que igual viaja: el parser corta en la primera línea que arranca con `scope:` **o** `audience:`, y `scope: both` viene antes | `skills/deep-tool-research/SKILL.md:7` (`scope: both`) vs `:8` (`audience: os-dev`); parser en `scripts/cos_init.py:340-346` |
| `.cognitive-os/skills/cos/patch-release/SKILL.md` | **CAPACIDAD** | Workflow de publicación de releases del OS (`prepare/plan/validate/doctor/publish`, GoReleaser, tags). Marcador `SCOPE: both` **contradice** el `audience: os-dev` del mismo archivo, y el marcador gana por diseño | `skills/patch-release/SKILL.md:1` (`<!-- SCOPE: both -->`) vs `:7` (`audience: os-dev`); precedencia documentada en `scripts/cos_init.py:304-318` |

### Detalle de las dos de información

**`provenance-scan.yaml` — la denylist es la fuga.** El archivo existe para que un
scanner detecte referencias a rutas de proyectos privados. Para hacerlo, tiene que
*nombrarlos*. Esa lista se copia tal cual a cada consumidor. El dato filtrado son
nombres de proyecto/cliente privados del mantenedor (no reproducidos acá, por
razones obvias). No hay credenciales.

Doble falla de gobierno, y por eso es el hallazgo principal:

1. El archivo no tiene marcador `SCOPE:` (arranca en `schema_version:`), así que
   la política "sin marcador → incluir" lo dejaría pasar.
2. Peor: **la copia ni siquiera consulta `scope_allows()`**. Es incondicional.

```python
# scripts/cos_init.py:1436-1440 — sin scope_allows()
policy_src = cos_source / "manifests" / "provenance-scan.yaml"
policy_dest = project_dir / ".cognitive-os" / "provenance-scan.yaml"
if policy_src.is_file() and not policy_dest.exists():
    shutil.copy2(str(policy_src), str(policy_dest))
```

Ponerle `# SCOPE: os-only` al archivo **no cierra la fuga**: hay que tocar el
call-site. Verificado: es el único archivo del install que contiene esos nombres
(`grep -rlniE '<nombres>' fixture/` → 1 resultado).

**`registration-allowlist.txt` — inventario de lo que no funciona.** Llega por el
mismo mecanismo: `hooks/_lib` se copia entero con `shutil.copytree()`, sin filtro
de scope, en ambos modos (`scripts/cos_init.py:1845` y `:1875`). Es un mapa de la
deuda interna del producto. **Nada en el consumidor lo lee** (`grep -rl
registration-allowlist .cognitive-os/{hooks,bin,cos_lib}` → vacío): es peso muerto
puro, todo costo y cero función.

### Detalle de las dos de capacidad

Ambas son la *misma* falla conceptual: una declaración de scope permisiva le gana
a un `audience: os-dev` explícito en el mismo archivo. En los dos casos el autor
dijo "esto es para desarrolladores del OS" y el instalador lo mandó igual.

Qué puede hacer el consumidor que no debería: en `patch-release`, invocar el
workflow de release del Cognitive OS. **Qué se lo impide aguas abajo:** el binario
`scripts/cos-patch-release` **no se proyecta** (`ls .cognitive-os/bin/` → solo
`cos-quality-duplicates`, `cos-so-impact-eval`, `cos-task-closure-gate`,
`provenance-scan` y sus `.py`). O sea, la palanca está desconectada. El daño real
que queda es **misruteo**: los `routing_patterns` del skill capturan `\bpatch[-
]release\b` con confianza 0.95 y `(release doctor|publish tag|GoReleaser)` con
0.8 — un consumidor que diga "patch release" sobre *su* producto se rutea al
proceso de release del OS. `deep-tool-research` está peor terminada
(`status: skeleton`) pero es menos dañina: expone el proceso interno de evaluación
de herramientas externas, sin nombrar ninguna herramienta concreta ni verdictos.

---

## 4. DEBERÍA VIAJAR — no tocar en un barrido

**Esta es la sección que evita romper consumidores.** Un barrido que marque
`os-only` todo lo que no tiene marcador rompe las dos listas de abajo.

### 4a. Los 6 módulos `cos_lib` sin marcador (rompen hooks si se bloquean)

Los 69 módulos `cos_lib` sin marcador que hay en el repo **no** se proyectan todos:
`cos_lib` se proyecta por *cierre de imports* de los hooks efectivamente
instalados (`scripts/cos_init.py:1901-1917` vía `lib_closure.compute_closure`).
De 69, aterrizan **6**. Cada uno tiene un consumidor real:

| Módulo | Lo necesita |
|---|---|
| `snapshot_manager.py` | hooks `pre-agent-snapshot.sh`, `crash-recovery.sh`, `agent-launch-confirmed.sh`, `session-start-stash-reapply.sh` |
| `telemetry_banner.py` | hook `session-init.sh` |
| `quota_pressure.py` | hook `agent-qwen-bridge.sh` |
| `project_paths.py` | `bin/cos_quality_duplicates.py` (copia explícita) |
| `time_utils.py` | transitivo: `queue_drainer`, `agent_health_monitor`, `dead_letter_queue`, `circuit_breaker` |
| `rate_limit_tracker.py` | transitivo: `dispatch.py` |

Marcar cualquiera de estos `os-only` lo saca del cierre (`scripts/cos_init.py:1909`)
y degrada el hook que lo importa. Los seis son helpers de runtime genéricos —
timestamps, rutas, snapshots, presión de cuota. Ninguno filtra nada.

Comando de verificación:

```bash
python3 - <<'PY'   # read-only
import sys; sys.path.insert(0,"scripts")
import lib_closure; from cos_init import scope_allows
from pathlib import Path
root=Path(".").resolve()
seed=[h for h in sorted((root/"hooks").glob("*.sh")) if scope_allows(str(h),"both")]
print(len(seed), len(lib_closure.compute_closure(seed, root)))
PY
# → 155 hooks proyectados, cierre de 80 módulos, 0 os-only arrastrados
```

### 4b. Los 123 archivos de skills legítimos

Los 125 archivos de skills sin marcador `SCOPE:`, **menos** `deep-tool-research`
(fuga de capacidad, arriba) y su carpeta. Están gobernados por `audience:` y la
mayoría son claramente de consumidor: `code-review`, `plan-bug`, `plan-feature`,
`pr-review`, `run-tests`, `systematic-debugging`, `test-driven-development`, la
familia `sdd-*`, `secret-audit`, `semgrep-scan`, `repo-forensics`, `scout`,
`retrospective`, `risk-register`, `deep-research`, `error-analyzer`,
`domain-model`, `detect-stack`, `scaffold-project`, `project-scaffold`.

**No agregarles `SCOPE: os-only` ni `SCOPE:` a ciegas.** Si se les agrega un
marcador `SCOPE:`, ese marcador **pisa** el `audience:` (precedencia en
`scripts/cos_init.py:304-318`) — que es exactamente el bug de `patch-release`.

### 4c. Ruido inocuo (12) — se manda de más, no hace daño

`cognitive-os.yaml`, `.claude/settings.json`, `.cognitive-os/install-meta.json`,
`.cognitive-os/cos_lib/.closure-manifest.json` (generados, sin rutas absolutas
salvo lo notado abajo), `.cognitive-os/benchmarks/so-impact-money-format-refactor.yaml`,
`.cognitive-os/templates/cos/task-closure-ledger.example.json`, y los 4 archivos
del fixture `.cognitive-os/fixtures/so-impact/money-format-refactor/`.

Salvedad menor sobre `install-meta.json`: el campo `"source"` guarda la ruta
absoluta del checkout de origen. En una instalación hecha *por el consumidor* esa
ruta es la suya y no filtra nada. Solo sería fuga si un install generado en la
máquina del mantenedor se distribuyera ya armado. No lo clasifico como fuga
porque no es el flujo normal, pero conviene saberlo.

---

## 5. Top 5 — sacar primero

1. **`manifests/provenance-scan.yaml`** — filtra 5 nombres de proyectos/clientes
   privados a todo consumidor, y se copia **sin pasar por `scope_allows()`**
   (`scripts/cos_init.py:1436-1440`): marcarlo no alcanza, hay que arreglar el
   call-site o externalizar la denylist.
2. **`hooks/_lib/registration-allowlist.txt`** — publica el inventario de hooks no
   cableados y el plan interno por fases, y **nadie lo lee** en el consumidor:
   sacarlo no rompe nada.
3. **`skills/patch-release/SKILL.md`** — `SCOPE: both` pisa su propio
   `audience: os-dev` y mete el proceso de release del OS en cada consumidor, con
   routing 0.95 sobre "patch release".
4. **El `copytree` de `hooks/_lib`** (`scripts/cos_init.py:1845`, `:1875`) — es el
   canal que dejó pasar el #2; hoy proyecta 39 entradas sin ningún filtro de scope.
   Mientras siga sin filtro, cualquier archivo nuevo en `_lib` viaja gratis.
5. **`skills/deep-tool-research/SKILL.md`** — mismo defecto de precedencia que #3,
   con otra causa: el parser de `scripts/cos_init.py:340-346` corta en la primera
   línea `scope:`/`audience:` y nunca ve el `audience: os-dev`.

---

## 6. Correcciones a las premisas del encargo

1. **El conjunto no es de ~75. Es de 144** archivos sin marcador que aterrizan.
   Mi conteo estático de `cos_lib/*.py` sin marcador dio **69** (probablemente el
   origen del "~75"), pero ese número es irrelevante en las dos direcciones: por
   arriba subestima el total real (144, porque ignora skills, `_lib`, templates,
   fixtures y generados) y por abajo lo sobreestima **muchísimo** para `cos_lib`,
   donde de 69 solo llegan **6**.

2. **Los tres archivos nombrados como sensibles no se proyectan.**
   `maintainer_experiment.py`, `maintainer_proposals.py` y `public_claim_gate.py`
   no aterrizan en ninguna instalación de consumidor. Tampoco `prelaunch_audit`,
   `publication_safety`, `maintainer_impact`, `product_answer` ni `release_freeze`.
   Motivo: `cos_lib` no se proyecta por directorio sino por **cierre de imports**
   de los hooks instalados, y ningún hook proyectado los importa.
   Verificación: `find fixture -name maintainer_proposals.py` → 0 resultados.

3. **La política citada (`scripts/cos_init.py:294`, "sin SCOPE → incluir") existe
   y es real, pero no es el mecanismo del daño principal.** El hallazgo #1
   (`provenance-scan.yaml`) y el #2 (`registration-allowlist.txt`) llegan por
   call-sites que **no invocan `scope_allows()` en absoluto**. Arreglar la política
   sin arreglar esos dos call-sites deja la fuga grave abierta.

4. **El encargo asume que la fuga es "archivos sin marcador". El peor caso de
   capacidad viene de un archivo *marcado*.** `patch-release/SKILL.md` tiene
   `SCOPE: both` en la línea 1: está etiquetado, y etiquetado mal, contra su propio
   `audience: os-dev`. Un triaje que solo mire archivos sin marcador no lo encuentra.

5. **Los skills no siguen la política "sin marcador → incluir".** Usan
   `skill_scope_allows()` con fallback a `audience:`, que sí bloquea `os`/`os-dev`/
   `os-only` (`scripts/cos_init.py:354-357`). Los 125 archivos de skills sin
   `SCOPE:` no son 125 fugas: son una superficie gobernada con **1** escape.

6. **El filtro `os-only` funciona.** Cero archivos marcados `os-only` aterrizan,
   sobre 653 archivos clasificables. Lo marcado se respeta; el problema es el
   default y los call-sites sin filtro.

---

## 7. VERIFICADO vs NO VERIFICADO

### VERIFICADO (con comando reproducible)

- Conjunto proyectado real: 672 archivos, 144 sin marcador, 0 `os-only`.
  Instalación real contenida en scratchpad + clasificación por `head -3`.
- Los 3 archivos nombrados en la premisa no se proyectan (`find` sobre el install).
- Cierre `cos_lib`: 155 hooks semilla → 80 módulos, 6 sin marcador, 0 `os-only`
  descartados (`lib_closure.compute_closure`, read-only).
- `provenance-scan.yaml` contiene los 5 nombres privados en la línea 5 y es el
  **único** archivo del install que los contiene (`grep -rlniE` sobre el fixture).
- `provenance-scan.yaml` se copia sin `scope_allows()` (lectura de
  `scripts/cos_init.py:1436-1440`).
- `hooks/_lib` se copia con `copytree` sin filtro de scope (`:1845`, `:1875`).
- `registration-allowlist.txt` no es leído por nada instalado (`grep -rl` → vacío).
- `patch-release` y `deep-tool-research` declaran `audience: os-dev` y aterrizan
  igual; ambas causas leídas en el código (`:304-318` y `:340-346`).
- `scripts/cos-patch-release` NO se proyecta (`ls .cognitive-os/bin/`).
- Los 6 módulos `cos_lib` tienen consumidor real (grep de importadores).
- Los 125 archivos de skills sin `SCOPE:` declaran todos `audience:` (0 fail-open).
- El instalador no escribe en el repo fuente ni en `$HOME`: `git status --porcelain`
  post-corrida idéntico al pre-corrida (solo los cambios preexistentes del operador
  en `cos_lib/confidentiality_scanner.py`, `templates/confidentiality.yaml`,
  `tests/unit/test_confidentiality_schema_contract.py`, `docs/06-Daily/reports/*`).

### NO VERIFICADO

- **Solo se probó una combinación**: `scope=both`, `harness=claude`, `mode=--full`.
  No se probó `project`/`all`, ni `codex`, ni `--default`. `--full` es el superset
  del surface de consumidor, así que las fugas halladas aplican a los demás casos,
  pero **puede haber fugas específicas del harness `codex`** que no vi (los
  destinos `.agents/skills` y `.codex/hooks.json` no se ejercitaron).
- **No corrí `scripts/cos_install_projection_audit.py`** (12 combinaciones × una
  instalación cada una) por la presión de swap. Ese script existe y es el gate
  natural para lo anterior; hoy solo chequea hooks colgados/excluidos, **no** fuga
  de contenido.
- **No leí los 123 archivos de skills uno por uno.** El triaje de esa lista se basa
  en su `audience:` declarado, en el nombre y en greps por indicadores de fuga
  (rutas de mantenedor, claims comerciales, nombres privados). Un skill con
  `audience: both` y contenido interno en el cuerpo **no lo detectaría** este método.
- **No verifiqué si los 5 nombres privados son de clientes o de proyectos propios.**
  Los clasifico como sensibles porque el propio repo los declara `forbidden_paths`.
- No corrí la suite de tests (mandato + swap 97%).
- `install.sh` no fue ejecutado ni leído más allá de lo necesario (otro juez).

---

## Reproducir este informe

```bash
SP=$(mktemp -d)   # o el scratchpad de la sesión
mkdir -p "$SP/fixture" && echo '# fixture' > "$SP/fixture/README.md"
python3 - <<PY
import subprocess, os, sys
root=os.path.abspath("."); sp="$SP"
env=dict(os.environ, COS_SOURCE_DIR=root, COS_INSTALL_SCOPE="both",
         COGNITIVE_OS_HARNESS="claude", COS_REGISTRY_FILE=sp+"/registry.json",
         HOME=sp+"/fakehome")
r=subprocess.run([sys.executable, root+"/scripts/cos_init.py","--full","--harness","claude"],
                 cwd=sp+"/fixture", env=env, text=True, capture_output=True)
print(r.returncode, r.stdout[-800:])
PY
# luego clasificar por marcador y grepear indicadores de fuga sobre "$SP/fixture"
```

Exit esperado: 0. El repo fuente queda intacto (`git status --porcelain` sin cambios nuevos).

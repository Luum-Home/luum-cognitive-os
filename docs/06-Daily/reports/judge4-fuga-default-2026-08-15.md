# Juez 4 — El default de `scope_allows` está mal, ¿qué arreglo y qué rompe?

**Fecha:** 2026-08-15
**Alcance:** read-only. No se editó, borró ni commiteó nada.
**Degradación declarada:** swap en 37.4 GB / 38.9 GB (96 %), load average 19.64.
No se corrió la suite de tests (909 tests de portabilidad) ni `install.sh`.
Todas las mediciones de abajo son estáticas y corren en menos de 5 segundos.

---

## 1. Veredicto

**Opción (b) en su versión mínima: el default se invierte a fail-closed, pero
recién en el tercer paso — primero se enciende un detector que haga ruido cuando
falta un módulo, y después se etiquetan los 6 archivos nombrados que hoy viajan
gratis. Invertir hoy, sin detector, cambia 6 fugas benignas por 6 roturas
silenciosas.**

El argumento no es "hay 75 archivos sin etiquetar, va a romper mucho". Va a
romper poco: **3 módulos en la instalación default, 5 en `--full`, más 1 archivo
de allowlist y 1 template JSON**. El argumento es otro: **en este repo el
fail-closed tampoco hace ruido**. Ya hay un fail-closed corriendo —el filtro de
`os-only`— y ya produjo una rotura silenciosa en producción que sigue viva
(§3.3). Invertir el default antes de arreglar la sordera del consumidor no
cambia el modo de falla característico del repo, lo replica.

---

## 2. La política real y su justificación histórica

### 2.1 Lo que dice el código

`scripts/cos_init.py`, función `scope_allows` (línea 255). El default está en
**291-293**, no en 294:

```python
# No SCOPE header → include unconditionally
if not scope_val:
    return True
```

No es un fail-open, son **cuatro**, en la misma función:

| Línea | Rama | Devuelve |
|---|---|---|
| 268-269 | `not path.is_file()` | `True` |
| 280-281 | `except OSError` al leer el header | `True` |
| **291-293** | **sin marcador `SCOPE:`** | **`True`** |
| 300-301 | marcador con un valor desconocido | `True` |

La única rama que filtra es 298-299 (`scope_val == "os-only"`). `skill_scope_allows`
(línea 304) repite el mismo patrón: sin `SKILL.md` → `True` (línea ~318), sin
campo `audience` → `True` (línea ~353), valor desconocido → `True` (línea ~359).

Detalle que agranda el agujero: el regex de línea 286 exige `# SCOPE:` en
**mayúsculas**. Hay 8 archivos que usan `# scope:` en minúsculas —
`cos_lib/adr_detector.py`, `cos_lib/skill_router.py`, `scripts/cos-events.sh`,
`scripts/cos-gate-stack.sh`, `scripts/cos-merge-queue.sh`,
`scripts/cos-merge-queue-worker.sh`, `scripts/cos-merge-queue-bench.sh`,
`scripts/queue_throughput_bench.py`— todos declarando `both`. Para el filtro son
archivos sin marcador: caen en 291-293 y pasan por la rama equivocada. Hoy da lo
mismo porque el resultado coincide (`both` → `True`); el día que alguien escriba
`# scope: os-only` en minúsculas, el archivo se proyecta igual.

### 2.2 Por qué se eligió: no se eligió

- `git log -S"No SCOPE header" -- scripts/cos_init.py install.sh` devuelve **un
  solo commit**: `219ce2ed5 feat(cos-init): phase 2.2 — migrate scope_allows +
  skill_scope_allows (strangler-fig)`. Es la migración byte-por-byte desde bash;
  no fijó la política, la transcribió.
- **ADR-019 (`docs/02-Decisions/adrs/ADR-019-scope-tagging.md`) es el ADR que fija
  el esquema, y no menciona el caso "sin marcador" en ninguna línea.** Lo que dice
  es lo contrario: *"Add scope tags to **all** agentic primitives"* (línea 31), y
  enumera cobertura total — ~120 `SKILL.md`, 83 hooks, 137 libs (líneas 38-39).
  Las tres alternativas evaluadas (líneas 48-50) son separación por directorio,
  filtrado en runtime e ignorar el problema. **Ninguna es "qué hacer con un archivo
  sin etiqueta".**
- ADR-320 (`ADR-320-install-scope-surface-debt.md:84`) sólo se ocupa de que `both`
  es un alias default de `project`, no del archivo sin marcador.

**Conclusión histórica: el fail-open no es una decisión, es un supuesto que se
cayó.** ADR-019 asumió cobertura del 100 % y por eso la rama del default nunca
tuvo que justificarse. Hoy la cobertura es 915/990 (92,4 %) en
`cos_lib/`+`scripts/`+`hooks/`, y ADR-019 ni siquiera contemplaba que `lib/` usara
`# scope:` en minúsculas — lo dice su propia nota (línea 42) sin notar que eso
rompe el matcher.

No hay razón escrita que respetar ni que refutar. Hay un hueco.

---

## 3. Radio de explosión de invertir el default

### 3.1 Método

El default no se aplica sobre los 990 archivos: se aplica sobre los que son
**candidatos a proyectarse**. Para `cos_lib` eso es la clausura de imports que
`scripts/lib_closure.py::compute_closure` calcula a partir de los hooks
proyectados (`cos_init.py:1909`). Comando (read-only, ~3 s):

```bash
python3 - <<'EOF'
import sys, re, json, importlib.util
from pathlib import Path
sys.path.insert(0, "scripts"); import lib_closure
spec = importlib.util.spec_from_file_location("cos_init", "scripts/cos_init.py")
ci = importlib.util.module_from_spec(spec); spec.loader.exec_module(ci)
root = Path(".").resolve(); hooks = root/"hooks"
seeds = {"DEFAULT": [hooks/f"{n}.sh" for n in ci.DEFAULT_HOOKS if (hooks/f"{n}.sh").is_file()],
         "FULL":    [p for p in sorted(hooks.glob("*.sh")) if ci.scope_allows(str(p), "both")]}
def marker(p):
    for l in list(open(p, encoding="utf-8", errors="replace"))[:3]:
        m = re.search(r'(?:# SCOPE:|<!-- SCOPE:)\s+([a-zA-Z_/-]+)', l)
        if m: return m.group(1)
    return None
for label, seed in seeds.items():
    cl = lib_closure.compute_closure(seed, root)
    proj = {m for m,e in cl.items() if ci.scope_allows(str(root/e.source_real_path), "both")}
    unmarked = {m for m in proj if marker(root/cl[m].source_real_path) is None}
    print(label, "seed=", len(seed), "closure=", len(cl), "se_caen=", sorted(unmarked))
    for u in sorted(unmarked):
        imps  = ["cos_lib."+s for s in sorted(proj-unmarked)
                 if re.search(rf"cos_lib\.{u}\b", (root/cl[s].source_real_path).read_text(errors="replace"))]
        imps += ["hook:"+h.name for h in seed
                 if re.search(rf"cos_lib\.{u}\b", h.read_text(errors="replace"))]
        print("   ", u, "->", imps)
EOF
```

Salida verificada: `DEFAULT: seed=43 closure=36`, `FULL: seed=155 closure=80`.

### 3.2 Tabla del radio de explosión

Qué deja de viajar el día que `scope_allows` devuelva `False` para un archivo sin
marcador, y qué se rompe por eso:

| Archivo que deja de viajar | Modo | Quién lo importa y sí viaja | Rotura concreta |
|---|---|---|---|
| `cos_lib/time_utils.py` | default + full | `cos_lib.agent_health_monitor`, `cos_lib.circuit_breaker`, `cos_lib.dead_letter_queue`, `cos_lib.queue_drainer` | **La peor.** 4 módulos de la clausura quedan sin importar. `circuit_breaker` ya está en la ruta muerta de §3.3; los otros 3 se apagan sin aviso. |
| `cos_lib/snapshot_manager.py` | default + full | `hook:crash-recovery.sh`; en full también `agent-launch-confirmed.sh`, `pre-agent-snapshot.sh`, `session-start-stash-reapply.sh` | Auto-rollback y reapply de stash sin backend de snapshots. Toca ADR-117 (reversibilidad de mutaciones de stash). |
| `cos_lib/telemetry_banner.py` | default + full | `hook:session-init.sh` | Banner de telemetría de ADR-304 muerto en SessionStart. |
| `cos_lib/quota_pressure.py` | sólo full | `hook:agent-qwen-bridge.sh` | Heurística de presión de cuota (ADR-056) fuera; el bridge de dispatch pierde el freno. |
| `cos_lib/rate_limit_tracker.py` | sólo full | `cos_lib.dispatch` | Instrumentación de rate-limit por proveedor (ADR-080) fuera de `dispatch`. |
| `cos_lib/project_paths.py` | **todas** | `cos_lib/duplicate_scanner.py:18` y `scripts/cos_quality_duplicates.py:20` (`from cos_lib.project_paths import relpath`), ambos `SCOPE: both` | **La más segura de romper.** No pasa por la clausura: está en la allowlist literal de `_install_quality_duplicates_primitive` (`cos_init.py:1462`). Fail-closed lo saltea y la primitiva `cos-quality-duplicates` nace muerta en **toda** instalación. |
| `templates/task-closure-ledger.example.json` | todas (`cos_init.py:1976`) | — | **No se puede arreglar etiquetando.** Es JSON: no admite `#` ni `<!-- -->`. Fail-closed lo excluye para siempre salvo que se cambie el mecanismo del marcador. |

**Total: 6 archivos rompen algo entregado, 1 template queda estructuralmente
imposible de etiquetar.** No 75.

Los otros ~68 sin marcador (`cos_lib/` en su mayoría, más
`scripts/_lib/local-service.sh`, `scripts/_lib/session-id.sh`,
`scripts/_lib/settings-driver.sh`, `scripts/adr_kb_benchmark.py`,
`scripts/cos_iroh.py`, `scripts/cos_lib_rename_codemod.py`,
`scripts/demo-consumer-sdd-lane.sh`,
`scripts/generate_harness_projection_registry.py`, `scripts/lib_closure.py`,
`scripts/yaml.py`) **nunca entran en ninguna ruta de proyección**. El default los
toca cero veces. Son deuda de etiquetado, no radio de explosión.

`rules/` está limpio: 112/112 con marcador. La allowlist nombrada de
`cos_init.py:1453/1462/1483/1523` está limpia salvo `project_paths.py`.

### 3.3 El dato que decide: el fail-closed que ya existe y ya falló en silencio

El filtro de `os-only` **ya es fail-closed**, y ya rompió algo:

- `cos_lib/record_completion.py:1` declara `# SCOPE: both` — viaja a todo consumidor.
- `cos_lib/record_completion.py:56` hace `from cos_lib.learning_pipeline import LearningPipeline`, a nivel de módulo.
- `cos_lib/learning_pipeline.py:1` declara `# SCOPE: os-only` — nunca viaja (`cos_init.py:1909` lo saltea).
- Resultado: en toda instalación de consumidor, `import cos_lib.record_completion` tira `ImportError`.
- `hooks/_lib/dispatch_gate_check.py:172-182` importa `CircuitBreaker` y
  `classify_task_type` **en el mismo bloque `try`**, y cierra con
  `except Exception as e: result["error"] += f"circuit_breaker:{e};"`.

El `ImportError` aborta el bloque antes de que `cb.can_launch()` corra nunca. **El
circuit breaker de agentes está muerto en toda instalación de consumidor, y el
único rastro es un string concatenado en un campo `error` que nadie lee.**

Eso invalida la premisa central del encargo: *"fail-closed es ruidoso, se descubre
porque algo rompe en el consumidor"*. En este repo no. El consumidor traga el
`ImportError` en un `except Exception` y sigue. **Un fail-closed sin detector acá
no es ruidoso: es la cuarta variante del mismo `try/except: pass`.**

(Ese hallazgo ya está diagnosticado y arreglado en el parche fuera del repo, con el
import diferido al sitio de uso — `/tmp/origin-fix/origin.patch`, hunk sobre
`cos_lib/record_completion.py`. No aplicado, no tocado.)

### 3.4 El auditor que ya está y no ve nada

```bash
python3 scripts/cos-scope-projection-audit --repo-root . --strict --json --no-write
# EXIT=0
```

Salida: `findings: 0`, `both_with_proofs: 689/689`, `block_findings: 0`. Y
`"projection_total": 0`, `"projection_by_scope": {}`. **La "auditoría de
proyección" mide cero artefactos de proyección**: audita el árbol fuente y sale
verde. Es exactamente el patrón que domina la auditoría de hoy — un auditor que
imprime `ok` con exit 0 sobre algo que no miró. Contra un fail-closed nuevo no
protege absolutamente nada.

Los dos gates de `.githooks/pre-commit` (líneas 316-334) llaman a
`cos-scope-both-portability-audit` y a este mismo `cos-scope-projection-audit`.
**Ninguno de los dos detecta un archivo sin marcador**, y ninguno verifica cierre
de dependencias. La carve-out de las líneas 297-312 incluso saltea el chequeo
estructural cuando el commit sólo agrega líneas `SCOPE:` — o sea, el commit que
etiqueta es el que menos se revisa.

---

## 4. Las cuatro opciones

| Opción | Qué rompe | Qué cuesta | Modo de falla que deja |
|---|---|---|---|
| **(a) Invertir a fail-closed de una** | Las 6 roturas de §3.2, todas de golpe. `cos-quality-duplicates` muere en toda instalación; 4 módulos de la clausura pierden `time_utils`; el template JSON queda excluido para siempre. | 1 línea (291-293 → `return False`). Barato de escribir, caro de descubrir. | **El peor de todos.** Silencio: cada rotura llega al consumidor como `ImportError` tragado por un `except Exception`, igual que §3.3. Cambia 6 fugas que hoy no hacen daño por 6 roturas invisibles. |
| **(b) Etiquetar primero, invertir después** | Nada, si se etiqueta antes. El JSON sigue siendo el caso duro. | 6 archivos (no 75) + resolver el template JSON. Bajo. Pero **sin detector es fe**: nadie garantiza que los 6 sean los 6, porque el único medidor es el script ad-hoc de §3.1. | Después de invertir: olvidar un marcador rompe — y sigue rompiendo en silencio mientras no haya detector. Mejor que (a) sólo por el hoy, no por el mañana. |
| **(c) Dejar el default y ratchet sobre archivos nuevos** | Nada. | Bajo: un gate en `.githooks/pre-commit` que rechace un archivo nuevo sin marcador. | **Congela la fuga.** Los 75 quedan aceptados de por vida, y el archivo nuevo *que ya está en el repo* nunca se toca. Además el ratchet es local: los 909 tests de portabilidad ya prueban independencia del `cwd`, no supervivencia a la proyección — un gate más del mismo tipo no cierra el agujero real, que es el de imports. |
| **(d) Corte estructural: el paquete es la unidad** | Nada de entrada, pero **no resuelve el sitio donde está el daño.** | Alto: migración de todo el esquema. | **Rechazada por evidencia.** La instalación default **ya usa corte estructural para hooks**: `install_hook()` (`cos_init.py:396-427`) no llama a `scope_allows` ni una vez; los hooks salen de `DEFAULT_HOOKS` / el manifiesto de boundary (línea 1723). Lo mismo las allowlists literales de 1453/1462/1483/1523. El marcador sólo decide en 5 sitios, y el que rompe cosas es la **clausura de `cos_lib` (1909), que se computa por imports, no por pertenencia a paquete**. La pertenencia no puede reemplazar al marcador ahí: un módulo entra a la clausura porque alguien lo importó, no porque esté en un paquete. (d) arregla lo que ya está arreglado y no toca lo que duele. |

---

## 5. Plan de migración, en orden

El orden importa: **el detector va primero**, porque es lo único que convierte
las roturas de los pasos siguientes en algo que se ve. Etiquetar primero e
invertir después (b puro) deja los pasos 2 y 3 sin verificación independiente.

### Paso 1 — Encender el detector de clausura (antes de tocar el default)

Un self-check post-instalación que salga con **exit 1** cuando un archivo enviado
referencia un `cos_lib.*` que no se instaló, clasificando el hallazgo. Esto es
literalmente lo que hace `scripts/cos_install_selfcheck.py` del parche externo
(`/tmp/origin-fix/origin.patch`, líneas 269+), con tres categorías:
`missing_shipped` (el instalador falló en enviarlo → **la que va a disparar el
paso 3**), `scope_conflict` (un archivo de consumidor depende de un `os-only` →
la de §3.3), `dangling` (import muerto).

**Mi recomendación se apoya en ese parche.** Lo leí, no lo apliqué ni lo modifiqué.
Dos cosas suyas valen aparte del checker: (i) mueve la clausura al paso 7c, después
de instalar `.cognitive-os/bin/*`, para que los binarios sembren la clausura — eso
solo ya arrastra `project_paths.py` por la vía de imports en vez de por la allowlist
literal; (ii) la allowlist de excepciones
(`manifests/install-selfcheck-allowlist.yaml`) **exige un motivo escrito y una
entrada en blanco se ignora**, con lo cual el verde barato del gate no es el camino
corto. Eso es lo que evita que el detector se apague solo.

**Comando de verificación del paso 1** — tiene que salir en **rojo hoy**, sobre el
default fail-open y sin invertir nada:

```bash
python3 scripts/cos_install_selfcheck.py \
  --install-root <dir-de-instalación-de-prueba> --source-root . --json; echo "exit=$?"
# esperado HOY: exit=1, con al menos scope_conflict:learning_pipeline (§3.3)
```

Si el detector sale verde antes de invertir nada, el detector está roto — porque
§3.3 es un hallazgo real y vivo. **Esa es la prueba de que el paso 1 quedó hecho.**

### Paso 2 — Tapar los 6 nombrados, con el detector encendido

En este orden (de mayor a menor daño):

1. `cos_lib/project_paths.py` → `# SCOPE: both`. Es el único que rompe en **toda**
   instalación, default y full.
2. `cos_lib/time_utils.py` → `# SCOPE: both`. Cuatro dependientes.
3. `cos_lib/snapshot_manager.py` → `# SCOPE: both`. Cuatro hooks en full.
4. `cos_lib/telemetry_banner.py` → `# SCOPE: both`.
5. `cos_lib/quota_pressure.py`, `cos_lib/rate_limit_tracker.py` → `# SCOPE: both`
   (sólo afectan `--full`).
6. `templates/task-closure-ledger.example.json` → **decisión aparte, no es
   etiquetar.** Un JSON no lleva comentario. Las salidas son: un manifiesto de scope
   para templates, un sidecar `.scope`, o una excepción por extensión en
   `cos_init.py:1976` (los `*.json` de `templates/` se envían siempre). Cualquiera
   de las tres se decide y se escribe; ninguna se resuelve sola.

Y de paso, los 8 archivos con `# scope:` en minúsculas (§2.1): o se normalizan a
mayúsculas o se afloja el regex de la línea 286 a `(?i)`. Hoy son inocuos por
coincidencia.

**Comando de verificación del paso 2** — el script de §3.1, que tiene que devolver
`se_caen=[]` en los dos modos:

```bash
# el bloque python3 de §3.1 → esperado: DEFAULT ... se_caen=[]  y  FULL ... se_caen=[]
```

Más el barrido de allowlists literales, que tiene que dar cero `NO MARKER`:

```bash
for f in scripts/cos-quality-duplicates scripts/cos_quality_duplicates.py \
         cos_lib/duplicate_scanner.py cos_lib/project_paths.py \
         scripts/cos_so_impact_eval.py scripts/cos-task-closure-gate \
         scripts/cos_task_closure_gate.py; do
  head -3 "$f" | grep -qE '# SCOPE:[[:space:]]+[a-zA-Z_/-]+' || echo "NO MARKER: $f"
done
```

### Paso 3 — Invertir el default

`scripts/cos_init.py:291-293` pasa de `return True` a `return False`. Junto con
él, la rama de tag desconocido (300-301) y el `except OSError` (280-281): un
archivo que no se puede leer o que declara un scope que el instalador no entiende
tampoco debería viajar. La rama 268-269 (`not path.is_file()`) se queda como
está: no es un archivo, no hay nada que enviar.

Y el equivalente en `skill_scope_allows` (líneas ~318, ~353, ~359).

**Comando de verificación del paso 3** — el mismo detector del paso 1, ahora en
verde sobre una instalación hecha con el default invertido:

```bash
python3 scripts/cos_install_selfcheck.py \
  --install-root <dir-de-instalación-de-prueba> --source-root . --json; echo "exit=$?"
# esperado: exit=0, cero missing_shipped
```

Con `missing_shipped` en cero se prueba lo que ninguna medición estática puede: que
la instalación resultante se aguanta sola. Si aparece un `missing_shipped`, es un
archivo que el paso 2 no vio — y ahora se ve, que es todo el punto.

### Paso 4 — El ratchet, al final y no antes

Recién con el default invertido tiene sentido el gate de `.githooks/pre-commit`
sobre archivos nuevos sin marcador (opción (c) como refuerzo, no como sustituto).
Antes de la inversión el ratchet protege el estado equivocado. Después, es la red
que evita volver a los 75.

**Nunca correr `install.sh` para verificar nada de esto**: líneas 416 y 425 hacen
`rm -rf "$TARGET_DIR"`. La instalación de prueba se arma en un directorio
descartable y sólo por la vía de `cos_init.py`.

---

## 6. Correcciones a las premisas del encargo

1. **La línea del default es 291-293, no 294.** 294 es la línea en blanco anterior
   al bloque `project/both`.
2. **No hay un fail-open, hay cuatro** en `scope_allows` (268-269, 280-281,
   291-293, 300-301) y tres más en `skill_scope_allows`. El encargo apunta a uno.
3. **"Hay ~75 archivos sin etiquetar" es cierto pero engañoso como radio de
   explosión.** 75 sin marcador, sí (65 en `cos_lib/`, 10 en `scripts/`, 0 en
   `hooks/`). Pero sólo **6** están en alguna ruta de proyección. Los otros ~69 el
   default ni los mira. Usar 75 como costo de la inversión sobreestima el riesgo
   por un factor de ~12 y hace que la opción correcta parezca cara.
4. **"Fail-closed es ruidoso, se descubre porque algo rompe en el consumidor": en
   este repo, falso.** El filtro `os-only` ya es fail-closed y ya rompió el circuit
   breaker de agentes en toda instalación de consumidor, y el rastro es un string en
   un campo `error` (§3.3). La ventaja del fail-closed —el ruido— **no está
   disponible acá hasta que exista un detector**. Es la corrección que cambia el
   orden del plan.
5. **La premisa "el hallazgo dominante es el silencio" no juega a favor de invertir
   el default, juega a favor de poner el detector primero.** Invertir sin detector
   es agregar un cuarto silencio.
6. **La fuga que hoy existe es benigna.** Los 5 módulos que viajan por el default
   son `time_utils` ("Shared timestamp helpers"), `snapshot_manager`,
   `telemetry_banner` (ADR-304), `quota_pressure` (ADR-056), `rate_limit_tracker`
   (ADR-080). Los cinco son legítimamente `both`. **El fail-open no costó nada
   todavía**: es una trampa armada, no una herida abierta. Eso baja la urgencia y
   confirma que vale hacerlo en el orden correcto en vez de rápido.
7. **La opción (d) no es aplicable como se plantea**, y no por costo: la
   instalación default **ya usa corte estructural para hooks** —`install_hook()`
   (`cos_init.py:396-427`) nunca llama a `scope_allows`— y el marcador sólo decide
   de verdad en la clausura de `cos_lib`, que se computa por imports. La pertenencia
   a un paquete no puede reemplazar ahí a un marcador.

---

## 7. VERIFICADO vs NO VERIFICADO

### VERIFICADO (con comando, en esta sesión)

- Política real y las cuatro ramas fail-open de `scope_allows`
  (`scripts/cos_init.py:268-301`) y las tres de `skill_scope_allows` (~318, ~353,
  ~359). Lectura directa.
- 990 archivos `.py`/`.sh` en `cos_lib/`+`scripts/`+`hooks/`, **75 sin marcador**
  (65 `cos_lib`, 10 `scripts`, 0 `hooks`). `find` + `head -3 | grep -qE`, sin
  seguir symlinks.
- **Clausura DEFAULT: 43 hooks semilla, 36 módulos, 3 caen** (`time_utils`,
  `snapshot_manager`, `telemetry_banner`); **FULL: 155 semilla, 80 módulos, 5
  caen** (+`quota_pressure`, `rate_limit_tracker`). Script de §3.1, usando la
  `compute_closure` y la `scope_allows` reales.
- Cada uno de los 5 tiene al menos un importador que sí se proyecta. Nombres en
  §3.2.
- `cos_lib/project_paths.py` sin marcador, en la allowlist literal de
  `cos_init.py:1462`, importado por `cos_lib/duplicate_scanner.py:18` y
  `scripts/cos_quality_duplicates.py:20`. Los otros 6 de esa allowlist tienen
  `# SCOPE: both`.
- `rules/`: 112/112 con marcador. `templates/`: 18 archivos, 1 sin marcador y es
  JSON (`task-closure-ledger.example.json`).
- 8 archivos con `# scope:` en minúsculas, invisibles al regex de la línea 286.
- **§3.3 completo**: `record_completion.py:1` = `both`, `:56` importa
  `learning_pipeline` que es `os-only`, y
  `hooks/_lib/dispatch_gate_check.py:172-182` los envuelve en un `try/except
  Exception` compartido. Lectura directa de los tres archivos.
- `install_hook()` (`cos_init.py:396-427`) no invoca `scope_allows`; los hooks
  default salen de `DEFAULT_HOOKS`/manifiesto (línea 1723).
- `cos-scope-projection-audit --strict` sale **exit 0** con `findings: 0` y
  `projection_total: 0`. Ejecutado.
- Contenido del parche externo: existe, tiene `cos_install_selfcheck.py` con las
  tres categorías y la allowlist con motivo obligatorio, y mueve la clausura al
  paso 7c. **Leído, no aplicado, no modificado.**

### NO VERIFICADO

- **Que las 6 roturas de §3.2 sean exhaustivas.** La medición cubre la clausura de
  `cos_lib` y la allowlist literal. **No** cubre skills (`cos_init.py:455`,
  `skill_scope_allows` sobre ~120 `SKILL.md` con su fallback de `audience:`), ni
  `packages/*`, ni referencias a `cos_lib` por vías que `lib_closure` no parsea
  (`importlib`, strings armados en runtime). El paso 1 del plan existe justamente
  para que esas se declaren solas.
- **Que ninguno de los 5 que viajan hoy deba ser `os-only`.** Los clasifiqué por
  docstring, no por uso. Es un juicio, no una medición.
- **Que el parche externo funcione.** No se aplicó ni se corrió su self-check. Que
  `cos_install_selfcheck.py` salga exit 1 sobre `scope_conflict:learning_pipeline`
  es una **predicción derivada del código leído**, no una observación. Es la primera
  cosa a comprobar del paso 1.
- **Comportamiento en tiempo de instalación real.** No se corrió `cos_init.py`
  contra ningún directorio, ni `install.sh` (prohibido: `rm -rf` en 416/425). Todo
  es análisis estático.
- **La suite de 909 tests de portabilidad.** No corrida — swap al 96 %. Por lectura
  de terceros, 206 hacen `sys.path.insert(0, REPO_ROOT)` y prueban independencia
  del `cwd`, no supervivencia a la proyección; no lo verifiqué yo.
- **Los ~69 archivos sin marcador fuera de toda ruta de proyección.** Verifiqué que
  no entran en la clausura ni en las allowlists; **no** verifiqué que no haya una
  quinta ruta de proyección que se me haya pasado.

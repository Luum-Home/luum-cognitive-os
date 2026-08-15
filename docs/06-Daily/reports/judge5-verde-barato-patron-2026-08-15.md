# Juez 5 — El patrón "verde barato" en luum-agent-os

**Fecha**: 2026-08-15
**Alcance**: historia completa del repo (2026-03-27 → 2026-07-28, 3254 commits) + estado de HEAD
**Modo**: read-only. No se editó, borró ni commiteó nada del repo fuera de este archivo.
**Degradación declarada**: swap al 97% (36.7G/37.9G, libres 1.1G), load average 13.78. Se evitó
`git log -p` global, la suite completa y cualquier `install.sh`. Ver §4 para el muestreo exacto.

---

## 1. Veredicto

**4 casos de verde barato confirmados y 4 correcciones legítimas, sobre ~60 commits candidatos
surfaceados de 3254 y 8 inspeccionados a fondo.** Pero el número de commits es la métrica
equivocada: el caso más grande no es un commit, es un **generador** — 922 archivos llamados
"portability proof" de los cuales **728 tienen un solo caso de test**, producidos por un scaffold
que prueba independencia del `cwd` y nunca supervivencia a la proyección.

La familia existe y es una práctica, no una anécdota. Pero el repo también contiene los
antídotos escritos: al menos dos commits arreglan la causa y dejan la doctrina por escrito
rechazando explícitamente la versión barata.

---

## 2. Tabla de hallazgos

| SHA | fecha | título | qué se apagó | clasificación | comando que lo prueba |
|---|---|---|---|---|---|
| *(sin SHA — generador)* | — | `scripts/cos-portability-proof-scaffold` | La prueba de portabilidad: 922 archivos, 728 con 1 solo caso, 62.6% ejecutan el artefacto **desde `REPO_ROOT`** con otro `cwd` | **VERDE BARATO** | `python3 <scratchpad>/measure_portability_proofs.py` |
| `c930ffbeb` | 2026-05-06 | `fix(contracts): close surface coverage ratchets` | El p95 **agregado** de latencia de hooks pasó a excluir `_KNOWN_SLOW_HOOKS`: hoy 11 de 40 hooks elegibles y 16.3% de las muestras quedan fuera | **VERDE BARATO** | `git show c930ffbeb -- tests/contracts/test_p95_hook_latency.py` + `python3 <scratchpad>/measure_p95_exemption.py` |
| `6e4f8f71a` | 2026-05-20 | `fix(audit): eliminate expected-failure debt` | `pytest.xfail` → `pytest.skip` en 2 lugares de `test_hook_latency_budget.py`. La deuda medida *eran* los xfail | **VERDE BARATO** | `git show 6e4f8f71a -- tests/audit/test_hook_latency_budget.py` |
| `5ba9de934` | 2026-07-20 | `fix(tests): eliminate brittle-by-construction test failures` | `--fail-new` del ACC pipeline sacado del único lugar automático; hoy sobrevive solo en `docs/09-Quality/manual-tests/` | **VERDE BARATO** (parcial — ver §3) | `grep -rn -- "--fail-new" --include="*.py" --include="*.yml" .` |
| `667000f47` | 2026-04-27 | `fix(tests): remove flaky observability and latency signals` | Nada: quitó el xfail global de p95 **y** arregló el bug de fondo | CORRECCIÓN LEGÍTIMA | `git show 667000f47 -- lib/record_completion.py docs/testing.md` |
| `5ba9de934` | 2026-07-20 | *(mismo commit)* | Nada en la parte `SCOPE:` — el instalador se arregló también | CORRECCIÓN LEGÍTIMA | `git show 5ba9de934 -- scripts/cos_init.py` |
| `6e4f8f71a` | 2026-05-20 | *(mismo commit)* | Nada en la parte del símlink: se quitó un test que **afirmaba que el bug seguía existiendo** | CORRECCIÓN LEGÍTIMA | `git show 6e4f8f71a -- tests/audit/test_lib_symlink_invariant.py` |
| `79c450a28` | 2026-07-20 | `fix(scope): reclassify 26 consumer-reachable modules os-only -> both` | Nada: reclasificación medida, módulo por módulo, con proof real | CORRECCIÓN LEGÍTIMA | `git show --stat 79c450a28` |

---

### 2.1. El caso grande: 922 pruebas de portabilidad que prueban otra cosa

Esta es la única entrada de la tabla que no es un commit, y es la que más pesa.

El repo tiene tres capas de gobernanza sobre `SCOPE: both`:

- **Layer 1** — `hooks/scope-marker-portability-gate.sh` (pre-commit): `exit 2` si un archivo
  staged declara `SCOPE: both` sin prueba pareada. Su mensaje de error dice literalmente
  *"Add a real portability test with at least one falsification probe"*.
- **Layer 2** — `tests/contracts/test_redteam_portability_coverage.py`: exige **≥4 casos de test**
  y **≥1 aparición de la palabra `falsification`**.
- **El atajo** — `scripts/cos-portability-proof-scaffold`, que genera el archivo que apaga Layer 1.

Lo que genera el scaffold (línea 54, plantilla):

```python
def test_{module}_artifact_exists() -> None:
    assert ARTIFACT.exists()

def test_runs_from_arbitrary_project_root(tmp_path: Path) -> None:
    """Falsification probe: must not depend on OS repo cwd."""
    result = subprocess.run([str(ARTIFACT)], cwd=tmp_path, ...)
    assert result.returncode == 0
```

Dos problemas, uno encima del otro:

1. **`ARTIFACT = REPO_ROOT / ...`** — la prueba ejecuta el archivo *desde el repo del SO*. Cambia
   el `cwd`, no el árbol de archivos. La pregunta que la gobernanza quiere contestar es "¿esto
   sobrevive a la proyección a un consumidor, donde solo existe el subconjunto proyectado?".
   La prueba contesta "¿esto depende del `cwd`?". Es estrictamente más débil, y no puede fallar
   por la razón por la que el gate existe.
2. **La palabra `falsification` está en el docstring.** Layer 2 la cuenta con
   `re.compile(r'falsification', re.IGNORECASE)`. Medir la presencia de una palabra es
   exactamente el verde barato de la familia "cobertura".

Y el umbral de Layer 2 (≥4 casos) se aplica sobre una lista hardcodeada de **4 artefactos**
(`REDTEAM_BOTH_ARTIFACTS`), mientras 728 archivos del mismo directorio se quedan en 1 caso.
El supresor no suprime: el estándar declarado y el estándar aplicado no se tocan.

Distribución medida hoy (`tests/red_team/portability/*.py`, 908 archivos):

```
casos/archivo:  0→1   1→728   2→92   3→50   4→12   5→8   6→6   7→6   8→4   9→1   14→1
```

Clasificación por fuerza real (922 archivos, incluye `.bats`):

```
COPIA-REAL    179  ( 19.4%)   copia el artefacto fuera del repo y lo ejecuta ahí
CWD-ONLY      577  ( 62.6%)   apunta a REPO_ROOT, solo cambia el cwd
EXISTENCIA     65  (  7.0%)   solo assert ARTIFACT.exists()
OTRO          101  ( 11.0%)
```

**Nota importante para no sobre-leer esto**: el 19.4% COPIA-REAL prueba que el repo *sabe*
escribir la versión fuerte. `79c450a28` la escribe a mano para sus 26 módulos y su propio mensaje
de commit dice: *"a real falsification probe (import plus primary entry point exercised from an
arbitrary working directory), not an existence check"*. El problema no es que nadie sepa; es que
el camino barato está scriptado y el caro no.

### 2.2. `c930ffbeb` — el agregado que dejó de agregar

El diff completo sobre el archivo cabe en pantalla:

```python
 def test_overall_p95_under_ceiling():
-    """Aggregate p95 across all samples should be under ceiling."""
+    """Aggregate p95 across all non-exempt samples should be under ceiling."""
     rows = _load_samples()
-    durations = [r["duration_ms"] for r in rows]
+    durations = [r["duration_ms"] for r in rows if r["hook"] not in _KNOWN_SLOW_HOOKS]
```

El test por-hook ya tenía la exención (razonable: hooks con sub-llamadas LLM, con su deuda
anotada en `rules/so-slo.md`). El agregado existía justamente para que la suma de las exenciones
no se fuera de rango. Después de este commit, el agregado mide el subconjunto rápido.

Medido hoy sobre `.cognitive-os/metrics/hook-health.jsonl`:

```
allowlist _KNOWN_SLOW_HOOKS ......... 12 hooks
hooks elegibles (n>=20) ............. 40
  exentos por allowlist ............. 11
  efectivamente evaluados ........... 29
muestras totales .................... 16674
  muestras de hooks exentos ......... 2714 (16.3%)
allowlist sin muestras .............. []   <- ningun exento es fantasma
```

A favor del commit: la allowlist no tiene entradas muertas y está motivada por escrito. En contra:
el título (`close surface coverage ratchets`) no menciona el cambio, y el agregado era el único
lugar donde la deuda exenta seguía visible.

### 2.3. `6e4f8f71a` — la deuda que se eliminó cambiando el verbo

```python
     if violators and os.environ.get(ENFORCE_ENV) != "1":
-        pytest.xfail(
+        pytest.skip(
             f"Operational hook latency budget exceeded for '{event}' but ..."
```

El commit se llama `fix(audit): eliminate expected-failure debt`. La cantidad medida era la
cantidad de `xfail`. Después del cambio hay cero `xfail` y la misma cantidad de hooks fuera de
presupuesto. La condición `if violators` sigue ahí, idéntica.

Diferencia práctica: un `xfail` aparece en el resumen de pytest como deuda contabilizada; un
`skip` se lee como "no aplica". El mismo hecho cambió de categoría contable.

---

## 3. La lista de CORRECCIÓN LEGÍTIMA

Esta sección es la que hace creíble la anterior. Todos estos casos tienen la forma superficial
del verde barato — un test aflojado, un baseline borrado, una declaración cambiada — y ninguno
lo es.

**`667000f47` (2026-04-27) — el antídoto escrito.** Sacó un `@pytest.mark.xfail(strict=False)`
que cubría el contrato de p95 entero, arregló la causa real (el banner de `phoenix.otel.register`
contaminaba `stdout` en `lib/record_completion.py`, que también es un CLI que emite JSON), y
dejó la doctrina en `docs/testing.md`:

> *"Do not mark latency regressions as blanket `xfail`; acknowledged slow hooks belong in
> explicit allowlists so newly slow hooks still fail."*

El repo escribió la regla que `c930ffbeb` había violado nueve días antes. La regla es correcta:
allowlist explícita > xfail global. Lo que `c930ffbeb` hizo mal no fue tener la allowlist, fue
extenderla al test agregado.

**`5ba9de934` (2026-07-20), parte `SCOPE:` — la premisa del encargo es falsa.** El encargo
decía: *"una declaración `# SCOPE:` cambiada para que coincida con la conducta del instalador,
en vez de arreglar el instalador"*. El mismo commit arregla el instalador:

```python
+        if not scope_allows(str(source_mod_path), os.environ.get("COS_INSTALL_SCOPE", "both")):
+            continue
```

`scripts/cos_init.py` no tenía filtro de SCOPE en el closure walk — proyectaba módulos `os-only`
a instalaciones de consumidor. Eso se arregló. Aparte, `cos_lib/__init__.py` se reclasificó a
`both` porque es el marcador de paquete que toda proyección copia incondicionalmente: la
declaración `os-only` era el error, no la conducta. Y se agregó
`tests/red_team/portability/test___init__.py` con tres casos, incluido uno que verifica que el
marcador sea **inerte** (sin imports, para que no arrastre módulos os-only a un consumidor) — el
único caso de la familia que verifica una propiedad estructural real.

Reserva honesta: ese proof usa `env={"PYTHONPATH": str(REPO_ROOT)}`, así que cae en el mismo
CWD-ONLY del §2.1. La reclasificación es legítima; el proof que la respalda es más débil de lo
que su docstring sugiere.

**`6e4f8f71a` (2026-05-20), parte símlink — se borró un test que exigía que el bug siguiera vivo.**
Lo que había antes:

```python
assert result.error_count >= _BASELINE_MIN_ERRORS, (
    f"Expected at least {_BASELINE_MIN_ERRORS} drift ERROR(s) in the un-remediated repo..."
)
```

Un test que falla si arreglás el problema. Eso es un baseline al revés y borrarlo es la única
salida correcta. Se reemplazó por `assert not errors`, que es estrictamente más fuerte.

En el mismo commit, `INTENTIONAL_DISTINCT_MODULE_PAIRS` en
`scripts/cos_lib_symlink_invariant_audit.py` excluye 5 pares. Aplicando el desempate de
`gates-sin-trampa` — *¿un cambio en uno de los dos conceptos debería obligar a tocar el otro?* —
la respuesta es no: `harness_adapter/dispatch.py` (dispatch de eventos de harness, ADR-033) y
el `dispatch.py` raíz (dispatch de LLM, ADR-049) comparten basename y nada más. Es la
clasificación **coincidencia**, hecha bien: acotada a 5 pares nombrados y motivada en el código.

**`79c450a28` (2026-07-20) — reclasificación masiva medida, no adivinada.** 26 módulos
`os-only` → `both`. La forma es idéntica a la del verde barato (cambiar 26 declaraciones para
que un gate deje de fallar), y el contenido es lo opuesto. Del cuerpo del commit:

- El alcance se midió: closure transitivo desde los 155 hooks consumer-facing → 81 módulos, 26 de
  ellos `os-only`.
- Se documenta un intento fallido intermedio: *"A first pass of 9 direct dependencies was not
  enough — consequence_engine imports model_catalog, so filtering only the direct level moved the
  ImportError one level down rather than fixing it."*
- Criterio explícito por módulo, con evidencia registrada. *"None were reclassified by default."*
- **Dos defectos latentes reportados sin arreglar**: `adr_router`/`rule_router` tenían
  `# scope: both` en minúscula (regex case-sensitive → marcador inerte), y
  `auto_repair._run_verification()` shellea a un `python3` pelado del PATH. Del commit:
  *"Pre-existing, left unfixed and recorded rather than smoothed over in the proof."*

Un commit que encuentra un supresor que no suprimía nada y lo reporta en vez de taparlo es la
conducta contraria a la que este informe está cazando.

---

## 4. Script de búsqueda y alcance declarado

`<scratchpad>/hunt_verde_barato.sh` — read-only, determinista, exit 0/1/2.

```bash
#!/usr/bin/env bash
# Familias: suppress | exit0 | ratchet | strictdrop | msgmismatch | all
set -uo pipefail
REPO="${REPO:-$(git rev-parse --show-toplevel)}"; cd "$REPO" || exit 2
SINCE="${SINCE:-2026-03-01}"

# SHAs que AGREGAN una linea que matchea $1 (pickaxe -G solo dice "toco", no "agrego")
added() {
  local re="$1"; shift
  git log --format=%H --since="$SINCE" -G"$re" -- "$@" | while read -r sha; do
    git show -U0 --format='' "$sha" -- "$@" | grep -qE "^\+[^+].*${re}" && echo "$sha"
  done
}
removed() {  # idem para lineas BORRADAS
  local re="$1"; shift
  git log --format=%H --since="$SINCE" -G"$re" -- "$@" | while read -r sha; do
    git show -U0 --format='' "$sha" -- "$@" | grep -qE "^-[^-].*${re}" && echo "$sha"
  done
}
show() { while read -r s; do git log -1 --format='%h %ad %s' --date=short "$s"; done; }

# familia strictdrop — la de mayor rendimiento
removed '\-\-strict'   . | show | sort -u
removed '\-\-fail-new' . | show | sort -u
removed '\-\-fail-on'  . | show | sort -u
added   'pytest.mark.skip|xfail' 'tests/*.py' | show | sort -u
removed 'pytest.mark.skip|xfail' 'tests/*.py' | show | sort -u

# familia msgmismatch — el mensaje no explica su propio diff
git log --format='%H|%ad|%s' --date=short --since="$SINCE" | while IFS='|' read -r sha d s; do
  case "$s" in
    docs*) git show --stat --format='' "$sha" | grep -qE '\.(py|sh|go)\s+\|' && echo "$sha $d $s" ;;
    test*|"fix(tests)"*) git show --stat --format='' "$sha" \
        | grep -qE '^\s(scripts|hooks|cos_lib|lib)/.*\|' && echo "$sha $d $s" ;;
  esac
done
```

Scripts de medición (los números de §2 salen de acá):

```bash
python3 <scratchpad>/measure_portability_proofs.py   # 922 proofs por fuerza real -> exit 1
python3 <scratchpad>/measure_p95_exemption.py        # % de latencia fuera del contrato -> exit 1
```

**Muestreo, explícito**: la historia es 2026-03-27 → 2026-07-28, **3254 commits, todos dentro de
la ventana** (`--since=2026-03-01` no descarta nada). No se difeó los 3254. La familia
`strictdrop` devolvió ~60 SHAs candidatos; se inspeccionaron a fondo **8**, elegidos por título
delator (`remove flaky`, `reduce ... xfail noise`, `eliminate expected-failure debt`,
`close ... ratchets`, `Stabilize ... lanes`, `Refresh contract generated artifacts`) más los 2
commits semilla del encargo. Las familias `suppress`, `exit0`, `ratchet` y `msgmismatch` quedaron
**corridas pero no triageadas** por presupuesto — `noqa` solo ya toca 308 commits. Estimación:
si la densidad se mantiene, quedan entre 5 y 15 casos sin clasificar. **No es un barrido completo
y no debe leerse como tal.**

---

## 5. Correcciones a las premisas del encargo

1. **"Una declaración `# SCOPE:` cambiada para que coincida con la conducta del instalador, en
   vez de arreglar el instalador (`5ba9de934`)" — FALSO.** El mismo commit arregla el instalador
   (filtro de SCOPE en el closure walk de `scripts/cos_init.py`, +14 líneas) y agrega la prueba
   de portabilidad. La declaración era el error. Es una corrección legítima. Comando:
   `git show 5ba9de934 -- scripts/cos_init.py`.

2. **"`check_entrypoint_adr_links.py` — 96 links rotos, imprime `ok`" — NO REPRODUCIDO.**
   Corrido hoy: `python3 scripts/check_entrypoint_adr_links.py --project-dir .` →
   `entrypoint ADR links: ok`. El script **sí tiene contrato de salida**: `return 2` si
   `missing`, `return 0` si no. Sobre 9 archivos de `docs/00-MOCs/entrypoints/` encuentra 116
   links `](adrs/...)` y los 116 resuelven. Su defecto real es de **alcance**, no de exit code:
   el regex `\[[^\]]+\]\((adrs/[^)#]+)(?:#[^)]+)?\)` descarta la ancla (`#seccion`) antes de
   validar, y solo mira ese directorio. Si hay 96 links rotos en algún lado, están fuera de lo
   que este script mira — y ese es un hallazgo distinto y peor.

3. **"Un auditor que imprime `"status": "fail"` y devuelve `exit 0`" — matiz.** En
   `scripts/cos_doc_path_audit.py` el `main()` termina en
   `return 2 if should_fail(payload, fail_categories) else 0`. No es un bug de exit code: es que
   **`--fail-on` es opt-in y por defecto está apagado**. El auditor reporta todo y no gatea nada
   salvo que quien lo invoca pida gatear. Es la misma familia (medición que no muerde) pero la
   causa es distinta y el arreglo también: hay que revisar los invocadores, no el script.

4. **"206 tests con `sys.path.insert(0, REPO_ROOT)`" — el número está bajo.** Son
   **258 ocurrencias del patrón exacto** en `tests/`, y **393 archivos de test** (de 2156) con
   algún `sys.path.insert(0, ...)`. Dentro de `tests/red_team/portability/` específicamente:
   219 archivos de 923.

5. **"y el pre-commit bloquea si falta esa línea" — NO ENCONTRADO.** El `pre-commit` del repo
   tiene 7 gates (términos de proyecto, paths absolutos de home, adopción de dependencias, sintaxis
   Python, registro de hooks, símlinks de lib, `SKILL.md`, YAMLs, y Gate 3f de tests estructurales).
   Ninguno menciona `sys.path`. El que sí bloquea por portabilidad es
   `hooks/scope-marker-portability-gate.sh` (`exit 2` por falta de proof pareado), y lo que exige
   es la existencia de un archivo con una probe, no una línea de `sys.path`.

---

## 6. VERIFICADO vs NO VERIFICADO

### VERIFICADO (comando corrido en esta sesión, output leído)

- 922 archivos en `tests/red_team/portability/`; 728 de 908 `.py` con exactamente 1 caso de test;
  62.6% CWD-ONLY, 19.4% COPIA-REAL, 7.0% solo existencia.
- El scaffold `scripts/cos-portability-proof-scaffold` genera existencia + probe apuntando a
  `REPO_ROOT`.
- `test_redteam_portability_coverage.py` exige ≥4 casos y ≥1 aparición de `falsification`, sobre
  una lista hardcodeada de 4 artefactos.
- `c930ffbeb` excluye `_KNOWN_SLOW_HOOKS` del agregado p95; hoy eso son 11/40 hooks y 16.3% de
  16.674 muestras.
- `6e4f8f71a` cambia `pytest.xfail` → `pytest.skip` en 2 lugares de
  `tests/audit/test_hook_latency_budget.py`, bajo un título que dice eliminar deuda de xfail.
- `--fail-new` del ACC pipeline no aparece en ningún `.py` ejecutable ni `.yml` de CI; solo en
  `docs/09-Quality/manual-tests/` y en el comentario que explica por qué se sacó.
- `5ba9de934` agrega el filtro de SCOPE en `cos_init.py`.
- `667000f47` arregla `lib/record_completion.py` y escribe la regla anti-xfail en `docs/testing.md`.
- `check_entrypoint_adr_links.py` devuelve 0 y no reporta links rotos hoy; su `main()` devuelve 2
  cuando los hay.
- `_KNOWN_SLOW_HOOKS` no tiene entradas fantasma: los 12 hooks de la allowlist tienen muestras.

### NO VERIFICADO (afirmado por el encargo o inferido, sin comando propio)

- Los otros 4 "gates falsos" del contexto de sesión: `cos_doc_path_audit.py` con 2733 findings,
  `documentation_truth_audit.py` sin noción de staleness, `cos-scope-projection-audit --strict`
  con `projection_total: 0`, `protected-config-write-guard`. Solo se leyó el contrato de salida
  del primero; no se corrió ninguno.
- Los gates "que corren y nunca gatearon" (`auto-verify` 0/55, `dod-gate`, `trust-score-validator`
  165 corridas, `error-pipeline` 14.070). No se tocó ese conjunto.
- **Las familias `suppress` (308 commits tocan `noqa`), `exit0`, `ratchet` y `msgmismatch` no se
  triagearon.** Los hallazgos de §2 son un piso, no un total.
- Si los 179 proofs COPIA-REAL efectivamente ejercitan el punto de entrada primario o solo copian
  y verifican texto. La heurística del script los separa por presencia de `shutil.copy` /
  `write_text(ARTIFACT.read_text(...))`, no por lo que asertan después.
- Si `test_overall_p95_under_ceiling` pasa o falla hoy. No se corrió la suite (prohibido por el
  mandato y por el estado de la máquina); el 16.3% sale de las muestras, no de la ejecución.

---

## 7. Las 3 acciones que más reducen la reincidencia

Ordenadas por reincidencia evitada, no por casos arreglados.

**1. Hacer que el scaffold no pueda producir la versión débil.**
`scripts/cos-portability-proof-scaffold` es el mecanismo de mayor apalancamiento del repo en
la dirección equivocada: un comando produce el archivo que apaga el gate. Cambiar su plantilla
para que el probe **copie el artefacto a `tmp_path` junto con su cierre proyectado** y lo ejecute
desde ahí convierte 728 archivos de "no puede fallar" en "puede fallar" con un solo cambio, y
—más importante— hace que el próximo `SCOPE: both` nazca con la prueba fuerte. Los 179 COPIA-REAL
existentes son el modelo; `79c450a28` es la referencia de cómo se escribe.
Esto arregla un caso en la tabla y previene los siguientes 200.

**2. Aplicar el umbral que el gate ya declara, sin lista hardcodeada.**
`test_redteam_portability_coverage.py` exige ≥4 casos y la palabra `falsification`, y lo aplica a
4 artefactos mientras 728 archivos del mismo directorio están en 1 caso. Dos arreglos, en este
orden: (a) que el gate camine el directorio en vez de la lista hardcodeada, con un ratchet
declarado y motivado por escrito para no romper el mundo el primer día; (b) **borrar el criterio
de la palabra `falsification`** — contar una palabra en un docstring es medición de forma, y es
justo lo que el scaffold satisface sin costo. Reemplazarlo por una condición sobre el árbol de
archivos (¿el artefacto se ejecuta desde una ruta distinta de `REPO_ROOT`?), verificable por AST
y no por gramática.

**3. Que el mensaje de commit tenga que explicar el aflojamiento.**
Los tres verdes baratos de §2 comparten una sola propiedad: **el título no describe el cambio que
importa.** `close surface coverage ratchets` esconde que el agregado dejó de agregar;
`eliminate expected-failure debt` describe el efecto contable, no el hecho. Un gate barato de
implementar y difícil de burlar: si el diff staged agrega `pytest.skip`/`xfail`/`# noqa`, mueve
un número de baseline o borra un flag `--fail-*`/`--strict`, el commit no pasa sin una línea
`Weakens-gate: <qué se dejó de medir> — <por qué>` en el cuerpo. No prohíbe nada; obliga a que la
decisión quede escrita donde `git log` la encuentra. Los cuatro commits de §3 ya escriben eso
espontáneamente en prosa — el gate solo lo vuelve obligatorio para el resto.

Lo que **no** conviene hacer: barrer los 728 archivos con un script de reemplazo. Ese es el mismo
movimiento que los creó, en la otra dirección, y produciría 728 pruebas fuertes sin que nadie haya
mirado si el módulo efectivamente sobrevive a la proyección. La acción 1 arregla el generador; los
archivos se van corrigiendo cuando su módulo se toca.

# Juez 5 — forense del commit `5ba9de934`: ¿verde barato o reclasificación correcta?

Fecha: 2026-08-15 · Lente: reconstruir qué pasó, no proponer el arreglo · Read-only

---

## 1. Veredicto

**No fue verde barato: el mismo commit puso el filtro `SCOPE` en la ruta de copiado del closure
(8 módulos os-only dejaron de proyectarse) y reclasificó `cos_lib/__init__.py` a `both` con la
prueba de portabilidad que el hook de gate le exigía. La acusación describe bien un hecho —
el `__init__.py` sigue copiándose sin pasar por `scope_allows()` — pero se equivoca en la
conclusión: ahí la declaración era el lado equivocado, no la conducta.**

---

## 2. Cronología

| # | SHA | Fecha | Qué pasó |
|---|-----|-------|----------|
| 1 | `bdaecb1ff` | 2026-04-20 | `chore(ws6): round 2 — 171 additional SCOPE tags`. En un barrido de **171 archivos de una línea cada uno**, `lib/__init__.py` recibe `# SCOPE: os-only`. Sin evidencia por archivo. |
| 2 | `6a0971910` | 2026-07-08 | `feat(hook-lib-projection): Batch A`. Nace el bloque `lib_init_file`: la proyección copia `cos_lib/__init__.py` **incondicionalmente** (con fallback a escribir un `__init__.py` vacío si no existe). Es la única vez que esa ruta se tocó — sigue igual hoy. |
| 3 | `785ced2f3` | 2026-07-10 | `feat(cos-lib): rename lib package to cos_lib`. El marcador `os-only` viaja con el rename. |
| 4 | `5ba9de934` | 2026-07-20 | El commit en juicio. 19 archivos. Agrega el filtro `scope_allows()` al loop del closure en `scripts/cos_init.py`, cambia `cos_lib/__init__.py` de `os-only` a `both`, y crea `tests/red_team/portability/test___init__.py`. |
| 5 | `79c450a28` | 2026-07-20 | Hijo directo: `fix(scope): reclassify 26 consumer-reachable modules os-only -> both`. El filtro recién puesto vuelve fatal una contradicción que era silenciosa. |
| 6 | `505091951` | 2026-07-20 | `fix(retention): ... unmask the consumer-install health check`. |

Comandos:

```bash
git log --oneline --format='%h %ad %s' --date=short -- cos_lib/__init__.py
git log --oneline --format='%h %ad %s' --date=short -S'SCOPE: os-only' -- lib/__init__.py
git log --oneline --format='%h %ad %s' --date=short -S'lib_init_file' -- scripts/cos_init.py
git show --stat 5ba9de934
git log --oneline --ancestry-path 5ba9de934..HEAD | tail -5
```

### 2.1 Qué cambió exactamente en `5ba9de934`

`git show --stat 5ba9de934` → **19 archivos, +767 / −274**. El cambio de declaración es
**una línea suelta dentro de un commit grande** (`cos_lib/__init__.py | 2 +-`), pero no viaja
sola: en el mismo diff está el arreglo estructural.

```diff
--- a/cos_lib/__init__.py
+++ b/cos_lib/__init__.py
-# SCOPE: os-only
+# SCOPE: both
 # Cognitive OS Python library modules
```

```diff
--- a/scripts/cos_init.py
+++ b/scripts/cos_init.py
@@ -1895,8 +1895,20 @@
     for mod_name, entry in closure.items():
-        dest_mod_path = lib_closure_dest / f"{mod_name}.py"
         source_mod_path = cos_source / entry.source_real_path
+        # ADR-019 scope governance: never project a `cos_lib` module whose
+        # header declares `SCOPE: os-only` into a consumer install [...]
+        if not scope_allows(str(source_mod_path), os.environ.get("COS_INSTALL_SCOPE", "both")):
+            continue
+        dest_mod_path = lib_closure_dest / f"{mod_name}.py"
         shutil.copy2(str(source_mod_path), str(dest_mod_path))
```

Además: `tests/red_team/portability/test___init__.py` (nuevo, 60 líneas) con dos aserciones
sustantivas — el marcador de paquete no puede tener imports ni sentencias ejecutables (AST), y
`import cos_lib` tiene que funcionar desde un cwd arbitrario (subproceso con `PYTHONPATH` acotado).

Ese test no es decorativo: `hooks/scope-marker-portability-gate.sh` **bloquea el commit**
(`status 2`) de cualquier archivo `SCOPE: both` staged sin su prueba pareada en
`tests/red_team/portability/` — está probado en
`tests/red_team/portability/scope-marker-portability-gate.bats`
("falsification: blocks SCOPE both file without portability test"). O sea: pasar a `both` **cuesta
escribir una prueba**, no es gratis.

---

## 3. El test: qué asserteaba, si tenía razón, y qué decía en rojo

**El test es `tests/contracts/test_primitive_scope_governance.py::test_default_consumer_projection_contains_no_os_only_markers`**
(parametrizado en `claude` / `codex` / `shell-ci`). Instala una proyección default en un `tmp_path`
y falla si algún archivo proyectado declara `SCOPE: os-only` en sus primeras 8 líneas.

**No fue tocado por el commit.**

```bash
git diff --stat 5ba9de934^ 5ba9de934 -- tests/contracts/test_primitive_scope_governance.py \
                                          tests/unit/test_primitive_scope_governance.py
# → salida vacía
```

Ése es el hecho que decide el punto 3 del encargo: el archivo del test es **idéntico** antes y
después. El código de producción se movió hacia el test, no al revés. Ninguno de los cinco tests que
sí se editaron en el commit (ledger, acc-pipeline, ratchets, auto_update, state-retention) tiene que
ver con `SCOPE`.

### 3.1 Qué decía en rojo (reconstruido, no citado)

No se puede correr el test contra el padre sin un checkout, así que se reconstruyó estáticamente el
insumo del rojo: extraer el árbol del padre a scratchpad y recomputar el closure con el propio
`lib_closure.compute_closure()`.

```bash
SCRATCH=<scratchpad>
git archive 5ba9de934^ hooks cos_lib scripts manifests > "$SCRATCH/parent.tar"
tar -xf "$SCRATCH/parent.tar" -C "$SCRATCH/parent"
python3 "$SCRATCH/closure_scopes.py" "$SCRATCH/parent"   # exit 1
python3 "$SCRATCH/closure_scopes.py" .                   # exit 0
```

Resultado:

| | hooks default | miembros del closure | miembros `os-only` |
|---|---|---|---|
| padre `5ba9de934^` | 33 | 20 | **8** |
| HEAD | 43 | 36 | **0** |

Los 8 que se filtraban al consumidor: `anchored_summarizer`, `format_converter`, `memory_manager`,
`memory_scanner`, `metric_event`, `stash_sha`, `state_heartbeat`, `trust_report_schema`. Más
`cos_lib/__init__.py` (os-only, copiado incondicionalmente) = **9 ofensores por harness, ×3 harness**.

**El test tenía razón.** No era brittle: detectaba nueve fugas reales de una superficie de
distribución. Ocho se arreglaron en la causa. Una —el marcador de paquete— se arregló en la
declaración, y ahí hay que mirar el mérito, no la forma.

### 3.2 ¿El `both` del `__init__.py` es honesto?

Sí, con una reserva.

- El archivo son **dos líneas de comentario**. El test de portabilidad prueba por AST que no tiene
  imports ni sentencias ejecutables: no puede arrastrar nada os-only al consumidor.
- Python **necesita** un `__init__.py` en `.cognitive-os/cos_lib/` para que el paquete importe. El
  archivo tiene que estar sí o sí; el propio código ya tiene el fallback
  (`lib_init_file.write_text("", encoding="utf-8")`).
- El `os-only` original venía de un barrido de 171 archivos (`bdaecb1ff`), no de una decisión sobre
  este archivo.

O sea: la conducta (viaja al consumidor) era correcta y necesaria; la declaración era la que mentía.
Cambiar la declaración es reducir el problema, no la medición.

**La reserva:** existía una alternativa que dejaba el `os-only` intacto y también ponía verde el
test — escribir siempre el `__init__.py` vacío en vez de copiar el del repo. No se tomó, y el commit
no dice por qué no. Es la única parte del episodio donde la elección entre "corregir la declaración"
y "corregir la ruta" quedó sin justificar por escrito.

---

## 4. Correcciones a las premisas del encargo

1. **"Cambió la declaración en vez de arreglar la ruta de copiado" — falso como descripción del
   commit.** El mismo diff arregla la ruta de copiado del closure (`cos_init.py`, +12 líneas). La
   acusación mira la ruta del `__init__.py` y generaliza al commit entero.
2. **"El test era brittle" (título del commit) — no aplica a este test.** El commit clasifica sus
   propios hallazgos en 5 clases y pone esto en **CLASS 3 — real bugs**, no en CLASS 1
   (no-determinismo). El título es un paraguas; el cuerpo distingue.
3. **`scripts/cos_init.py:1889-1891` — la referencia es correcta y sigue vigente.** Hoy son las
   líneas ~1886-1892 (`lib_init_file`), la ruta que copia `__init__.py` sin pasar por
   `scope_allows()`. Nunca se tocó desde `6a0971910` (2026-07-08).
4. **"El mensaje no explica su propio diff" — parcialmente falso.** El cuerpo lo dice textual:
   *"cos_lib/__init__.py reclassified os-only -> both (inert package marker copied unconditionally)
   and given the portability proof that scope requires."* Lo que falla es el **título**: `fix(tests):`
   para un commit que cambia un contrato de distribución (`cos_init.py`), la GC de checkpoints
   (`checkpoint_manager.py`, +130) y dos workflows. Quien filtre por `fix(tests):` no lo revisa.

---

## 5. VERIFICADO vs NO VERIFICADO

### VERIFICADO (comando arriba en cada caso)

- `5ba9de934` toca 19 archivos, +767/−274; el cambio de `SCOPE` es 1 línea entre ellas.
- El mismo commit agrega el filtro `scope_allows()` al loop del closure en `scripts/cos_init.py`.
- El test de gobernanza (`test_default_consumer_projection_contains_no_os_only_markers`) **no fue
  modificado** por el commit (`git diff --stat` vacío).
- En el padre, el closure de los hooks default incluía **8 módulos `os-only`**; en HEAD, **0**.
- El hook `scope-marker-portability-gate.sh` bloquea `SCOPE: both` sin prueba pareada (probado en
  `scope-marker-portability-gate.bats`, exit 2).
- El test pasa hoy: `.venv/bin/pytest tests/contracts/test_primitive_scope_governance.py::test_default_consumer_projection_contains_no_os_only_markers -v`
  → **3 passed en 1.46s**.
- Una proyección `--default` real (corrida en scratchpad) instala 200 archivos, 39 módulos en
  `.cognitive-os/cos_lib/`, y su `__init__.py` proyectado dice `# SCOPE: both`.
- `scripts/scope_closure_gate.py` en HEAD: `scope_conflict 4 (baseline 4)`, `unmarked_published 5 (5)`,
  `os_only_published 4 (4)`, `marker_invisible 0 (0)` — sin desvío del baseline.
- El hijo directo `79c450a28` reclasificó 26 módulos más `os-only -> both`, con prueba de
  portabilidad por módulo, y su mensaje registra dos defectos latentes sin arreglar.

### HALLAZGO NUEVO, VERIFICADO — la ventana del gate deja pasar skills

Reproducible:

```bash
cd <scratchpad>/proj && python scripts/cos_init.py --default --harness claude
grep -rlE 'SCOPE:[[:space:]]*os-only' <scratchpad>/proj
# → .cognitive-os/skills/cos/cos-status/SKILL.md   (marcador en la línea 30)
```

- `scope_allows()` (`scripts/cos_init.py:255`) lee **solo las 3 primeras líneas**; el test de
  gobernanza lee las **8 primeras**. En un `SKILL.md` con frontmatter YAML el marcador queda en la
  línea ~30-50: **ninguno de los dos lo ve**, y el archivo se proyecta por el fail-open.
- `--default` filtra 1 skill os-only al consumidor (`cos-status`). `--full` filtra **7**
  (`cognitive-os-init`, `primitive-harness-coverage`, `phoenix-trace-ui`, `cognitive-os-status`,
  `cos-status`, `browser-task`, `artifact-workflow`). El test solo corre `--default`.
- En fuente trackeada hay **64** `SKILL.md` (`skills/`, `packages/`) con marcador `SCOPE:` después
  de la línea 3, invisibles a `scope_allows()`.
- El contrato escrito en `hooks/skill-frontmatter-validator.sh:21` dice
  *"HTML comment at line 1"*, y `scope_allows` implementa "primeras 3 líneas". La realidad de 64
  archivos es "después del frontmatter". Los tres no coinciden.
- El bucket `marker_invisible` de `scope_closure_gate.py` marca 0 porque solo mira `cos_lib/`.

### NO VERIFICADO

- **No se corrió el test contra el commit padre.** Prohibido el checkout; se reconstruyó el insumo
  del rojo (el closure y los scopes del padre), no el output literal de pytest. El conteo "9 ofensores
  ×3 harness" es una inferencia sobre esa reconstrucción, no una captura del rojo.
- No se verificó qué reportaba el test en el padre para archivos **fuera** de `cos_lib` (skills, hooks):
  la fuga de skills descrita arriba es invisible al test **hoy**, y probablemente también lo era
  entonces, pero no se midió en el padre.
- No se auditó si alguno de los 8 módulos filtrados dejó de estar disponible para hooks de consumidor
  al ponerse el filtro. El gate reporta `scope_conflict: 4` hoy —incluido un `ImportError on load`—
  pero atribuirlo a este commit sería especulación.
- No se corrió la suite completa (máquina a ~97% de swap; `vm.swapusage` 36773/37888 MiB, load 9.04).

---

## 6. Cierre — 3 acciones, en orden

1. **Cerrar la ventana del marcador antes que cualquier otra cosa de scope.** `scope_allows()` mira 3
   líneas y el test de gobernanza 8; 64 `SKILL.md` ponen el marcador después del frontmatter, y hoy
   se proyectan 1 (`--default`) y 7 (`--full`) skills `os-only` a consumidores. Mientras eso siga, el
   verde del test de gobernanza no prueba lo que su nombre dice.
2. **Extender el test de gobernanza a `--full`** (hoy solo parametriza harness, no modo). Los 7
   leaks de `--full` no tienen gate.
3. **Dejar escrito por qué el `__init__.py` se resolvió por declaración y no por ruta** — existía la
   alternativa de escribir siempre el marcador vacío. Es la única pieza del episodio sin evidencia
   registrada; una línea en ADR-019 o en `manifests/primitive-scope-classification.yaml` la cierra.

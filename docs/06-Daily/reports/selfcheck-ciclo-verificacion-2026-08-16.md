# Ciclo de verificación del self-check del instalador

**Fecha:** 2026-08-16
**Artefacto verificado:** `docs/05-Methodology/runbooks/installer-selfcheck-2026-08-15/`
**Árbol de trabajo:** `fd5c58b98` (ver §10.9 sobre la rama)
**Dónde corrió todo:** un clon en el scratchpad. El repo de trabajo no se tocó
en ningún paso; el clon se borró al terminar (ver §9).

```
pwd de todos los pasos de instalación y sabotaje:
  <scratch>/clone            clon del repo (fuente parchado)
  <scratch>/orig-tree        export de 8602ddc70 (fuente original, sin parchar)
  <scratch>/target-baseline  install desde el árbol de hoy sin parchar
  <scratch>/target-orig      install desde 8602ddc70 sin parchar
  <scratch>/target-patched   install desde el árbol parchado (--default)
  <scratch>/target-full      install desde el árbol parchado (--full)
  <scratch>/target-full-base install desde 8602ddc70 (--full)
```

`install.sh` **no se corrió nunca**. El `rm -rf "$TARGET_DIR"` relativo de sus
líneas 415/424 no se ejercitó: se invocó `scripts/cos_init.py` directamente, que
toma la fuente de `Path(__file__).parent.parent` y el destino de `Path.cwd()`
(líneas 47 y 1685-1686). Cada corrida se hizo con el cwd en un directorio nuevo
del scratchpad, impreso antes de ejecutar. Ninguna de las instalaciones
consumidoras se listó, se tocó ni se reinstaló.

---

## 1. Las ediciones: 11 de 12 aplican

`edits.md` declara 12 pares replace/with (`grep -c '^\*\*Replace:\*\*'` → 12).
Se aplicaron en orden con un aplicador que exige match exacto y único:

```
[1]  ok   scripts/hook-timing-wrapper.sh (4 -> 48 líneas)
[2]  ok   scripts/lib_closure.py (1 -> 24)
[3]  ok   scripts/lib_closure.py (8 -> 8)
[4]  ok   scripts/cos_init.py (1 -> 19)
[5]  ok   scripts/cos_init.py (60 -> 6)
[6]  ok   scripts/cos_init.py (4 -> 77)
[7]  ok   scripts/cos_init.py (17 -> 61)
[8]  ok   scripts/hook-timing-wrapper.sh (16 -> 13)
[9]  ok   scripts/cos_init.py (7 -> 11)
[10] FAIL cos_lib/record_completion.py: replace-block not found
[11] ok   cos_lib/record_completion.py (2 -> 5)
[12] ok   scripts/hook-timing-wrapper.sh (4 -> 4)
applied=11 failed=1
```

**Por qué falla la 10, y es la buena noticia:** pedía reemplazar el import
top-level `from cos_lib.learning_pipeline import LearningPipeline` por un
comentario. Ese import ya no existe: `6bb75a580` lo difirió, con su propio
comentario en `cos_lib/record_completion.py:56`. La edición no aplica porque el
defecto ya está arreglado. No se forzó.

**Efecto colateral de la 11:** la 11 inserta el import diferido en el sitio de
llamada, que `6bb75a580` ya había insertado. Resultado: import duplicado en
`record_completion.py:496` y `:499`. Compila (`py_compile` OK) y es un no-op en
runtime, pero es basura que quedaría en el árbol si alguien aplicara `edits.md`
tal cual hoy. **Quien aplique esto debe saltear la 11 junto con la 10.**

Post-aplicación: `py_compile` OK sobre los tres `.py`, `bash -n` OK sobre el
wrapper. Diff total: 4 archivos, +194/-42.

---

## 2. Base sin parchar: 12 hallazgos — y son los mismos 12

El encargo avisaba: *"si hoy da 12, sospechá"*. Dio 12. Sospeché, y la sospecha
se resolvió midiendo el árbol original en vez de razonar sobre él.

| Fuente | Commit | Hallazgos |
|---|---|---|
| Árbol de hoy, sin parchar | `fd5c58b98` | **12** |
| Árbol original del rescate | `8602ddc70` | **12** |

Y no sólo el número: la composición es **idéntica ítem por ítem**.

```
[missing_config]   confidentiality.yaml                     1
[missing_shipped]  capability_levels, context_budget,
                   dispatch_model_advisor, harness_environment (x2,
                   dos entry points distintos), performance_monitor,
                   process_registry, project_profile_bootstrap,
                   record_completion, user_model               10
[missing_sibling]  cos-root                                   1
```

**Por qué los dos defectos ya arreglados no bajaron el número.** El self-check
no mide la estructura de imports en el fuente: mide **qué se shippea**.

- *Circuit breaker (`6bb75a580`)*: arregló el acoplamiento en el fuente
  —`learning_pipeline` diferido— pero `record_completion.py` **sigue sin
  shippearse**. El hallazgo que emite el check es `missing_shipped`, y ese sigue
  siendo verdadero. El arreglo del import habría eliminado un hallazgo distinto
  (`scope_conflict:learning_pipeline`) que sólo aparece **si** `record_completion`
  se shippea — que es lo que pasa recién en el árbol parchado. Por eso el número
  no se mueve: el defecto arreglado nunca fue el que este contador contaba.
- *Plantilla de confidencialidad*: `VERIFICACION-2026-08-16.md` verificó que hoy
  existe `templates/confidentiality.yaml` trackeada y con las claves correctas, y
  dejó explícitamente sin verificar si el instalador la shippea. **No la
  shippea**: `.cognitive-os/confidentiality.yaml` no existe en
  `target-baseline`, y el hallazgo `missing_config` se dispara igual. La mitad
  que faltaba de esa verificación queda cerrada acá, en negativo.

O sea: el 12 reproduce exacto no porque esté midiendo otra cosa, sino porque el
árbol cambió en dimensiones que este contador no mira. Se comprobó corriendo el
mismo check sobre el árbol original, no deduciéndolo.

---

## 3. Control limpio sobre el install parchado

```
install (--default, --harness=claude) desde el árbol parchado → exit 0
selfcheck --install-root target-patched --source-root clone
  → "install self-check: OK — every shipped entry point resolves its imports."  exit=0
```

El self-check quedó cableado en `cos_init.py` como paso 13, y falla el install
(`INSTALL INCOMPLETE: N self-check finding(s)`), no advierte. Deltas del parche:

| | baseline | parchado |
|---|---|---|
| módulos en `.cognitive-os/cos_lib` | 39 | **65** (+26) |
| tamaño de `.cognitive-os` | 1704 KB | **2160 KB** (+27%) |
| `.cognitive-os/confidentiality.yaml` | no existe | **shippeado** (1616 B) |

El README declaraba "~25 módulos adicionales, costo nunca medido". Son **26**, y
el costo en disco queda medido acá: +456 KB. Import time no se midió.

---

## 4. Las cuatro sabotajes, con control limpio antes y después

Cada sabotaje se revirtió y el control se volvió a correr. Los cuatro controles
dieron `exit=0` con el mensaje OK.

**S1 — base sin parchar** (§2): 12 hallazgos, `exit=1`.

**S2 — módulo borrado de un install bueno**
(`rm .cognitive-os/cos_lib/record_completion.py`):
```
[missing_shipped] cos_lib.record_completion
    .cognitive-os/hooks/cos/_lib/dispatch_gate_check.py:
    cos_lib/record_completion.py exists in source but was not installed
1 finding(s).   exit=1
```
Control después: OK, exit=0.

**S3 — módulo borrado del fuente** (`dispatch_model_advisor.py` fuera del clon y
del install):
```
[dangling] cos_lib.dispatch_model_advisor
    .cognitive-os/hooks/cos/_lib/dispatch_gate_check.py:
    cos_lib.dispatch_model_advisor does not exist in the source repo either
1 finding(s).   exit=1
```
Clasifica distinto que S2 —`dangling` vs `missing_shipped`— que es justo lo que
distingue "el instalador se lo comió" de "el import está muerto". Control
después: OK, exit=0.

**S4 — hook fantasma inyectado en `settings.json`**:
```
[ghost_registration] ghost-hook-that-never-shipped.sh
    .claude/settings.json [PreToolUse] registers
    $CLAUDE_PROJECT_DIR/.cognitive-os/hooks/cos/ghost-hook-that-never-shipped.sh
    but that file does not exist
1 finding(s).   exit=1
```
Control después: OK, exit=0.

---

## 5. La ceguera declarada por su autor: existe, pero no donde él la puso

El autor declaró que el check "marca sólo imports **sin guarda**" y por eso es
ciego a la clase feature-apagada-en-silencio. Se probó en dos lugares distintos,
porque el código trata distinto a los dos:

**a) En un entry point de hooks (`hooks/cos/_lib/probe_guarded.py`): NO es ciego.**
```python
try:
    from cos_lib.this_module_does_not_exist_anywhere import Thing
except Exception:
    Thing = None
```
→ `[dangling] cos_lib.this_module_does_not_exist_anywhere`, exit=1. La misma
salida que con el import sin guarda. Acá el autor **se subestimó**.

**b) En un módulo `cos_lib/*.py` shippeado: SÍ es ciego.**
```python
# .cognitive-os/cos_lib/probe_mod.py
try:
    from cos_lib.this_module_does_not_exist_anywhere import Thing   # invisible
except Exception:
    Thing = None
def f():
    from cos_lib.also_does_not_exist import Other                   # invisible
```
→ `install self-check: OK`, exit=0. El mismo import movido a top-level sin
guarda → `[dangling]`, exit=1.

La causa está en `check_lib_closure`: `import_time_only = entry.parent.name ==
"cos_lib"` (línea 232), y con eso sólo se extraen los imports que corren al
importar el módulo. La ceguera es **real y está acotada a los módulos `cos_lib`
proyectados** — que es exactamente donde vive la clase que motivó todo.

**Instancia real, ya presente en el árbol parchado:**
```
.cognitive-os/cos_lib/record_completion.py:496  from cos_lib.learning_pipeline import ...
.cognitive-os/cos_lib/learning_pipeline.py      No such file or directory
python3 -c "import cos_lib.record_completion"   → importa OK
python3 -c "import cos_lib.learning_pipeline"   → ModuleNotFoundError
selfcheck                                       → OK, exit=0
```
El arreglo de `6bb75a580` hace importable a `record_completion` en consumidores
—que era el objetivo, y funciona— pero la ruta de código que llama a
`LearningPipeline` sigue muerta en todo consumidor, y **el check da verde**. Es
la ceguera declarada, con un caso real y no un probe sintético.

---

## 6. El hueco que nadie había corrido: `--full` rompe el install

El README declaraba que la rama `--full` tiene su propio bloque duplicado de
copia del wrapper y **nunca se corrió**. Se corrió:

```
install --full desde el árbol parchado → FULL_EXIT=1
INSTALL INCOMPLETE: 2 self-check finding(s)

[duplicate_registration] audit-id-enricher.sh
    .claude/settings.json: registered 2x for PostToolUse
[duplicate_registration] cross-session-event-emit.sh
    .claude/settings.json: registered 2x for PreToolUse
```

¿Lo causa el parche? **No.** El mismo `--full` desde `8602ddc70` sin parchar
produce las mismas dos duplicaciones:

```
UNPATCHED --full PreToolUse  {'cross-session-event-emit.sh': 2}
UNPATCHED --full PostToolUse {'audit-id-enricher.sh': 2}
PATCHED   --full PreToolUse  {'cross-session-event-emit.sh': 2}
PATCHED   --full PostToolUse {'audit-id-enricher.sh': 2}
```

Es un defecto preexistente de `--full` que nadie había visto porque nada lo
miraba. La consecuencia operativa es concreta: **con el parche aplicado, todo
install `--full` falla** hasta que se arreglen las duplicaciones o se
allowlisteen con motivo escrito. El `--default` pasa limpio. Baseline `--full`
sin parchar: 13 hallazgos.

---

## 7. Qué NO se pudo verificar

- **Nada se comparó contra el artefacto original**, porque no existe. Ver §10.
- **Import time** del install parchado (+26 módulos). Sólo se midió disco.
- **Licencias / dependencias arrastradas** por los 26 módulos nuevos.
- **Otros harness** que `--harness=claude`.
- La consecuencia declarada del defecto 3 —`PROJECT_DIR` vacío y telemetría
  escrita a `/`— **no se reprodujo**. Lo que sí se verificó es que el check la
  detecta como `missing_sibling: cos-root` y que el wrapper parchado ya no
  depende del hermano.
- **Ningún consumidor real se instaló ni se tocó.** Todo lo de arriba es sobre
  installs nuevos en el scratchpad.

---

## 8. Nota de medición

La máquina está cargada: `uptime` durante las corridas dio load average
**146-150** sobre 12 cores (no 270 — ver §Correcciones). Por eso los tiempos van
separados y el wall **no es portable hoy**:

| corrida | wall | user | sys |
|---|---|---|---|
| install baseline | 0.88 s | 0.38 s | 0.43 s |
| install `8602ddc70` | 0.35 s | 0.25 s | 0.29 s |
| install parchado `--default` | 2.55 s | 0.53 s | 0.45 s |
| install parchado `--full` | 2.15 s | 1.28 s | 1.82 s |
| install `--full` sin parchar | 1.65 s | 1.05 s | 1.73 s |

El `--default` parchado tarda 2.55 s de wall con 0.53 s de user: la mayor parte
es espera de core, no trabajo. Ningún paso se colgó.

---

## 9. Limpieza

El clon, el export de `8602ddc70` y los cinco directorios de install se borraron
del scratchpad al terminar. Se conservan sólo los logs de install y este informe.
El repo de trabajo no recibió ninguna edición: **el parche sigue sin aplicar**.

---

## 10. Correcciones a las premisas del encargo

1. **"Si hoy da 12, sospechá; si da menos, probablemente sea correcto."**
   Falso como heurística acá. Da 12, y los 12 son legítimos: se verificó
   corriendo el mismo check contra `8602ddc70` y comparando ítem por ítem. La
   premisa asumía que arreglar dos defectos tenía que mover el contador; el
   contador mide **qué se shippea**, y ninguno de los dos arreglos cambió eso
   (§2).
2. **"Dos de los tres defectos ya están resueltos."** A medias. El del circuit
   breaker sí (edición 10 no aplica porque ya está hecho). El de la plantilla de
   confidencialidad **no**: la plantilla existe trackeada con las claves
   correctas, pero el instalador **no la shippea** — `missing_config` sigue
   disparando sobre un install de hoy. `VERIFICACION-2026-08-16.md` había dejado
   esa mitad explícitamente sin verificar; queda cerrada, y el veredicto es que
   el defecto 1 sigue vigente en su consecuencia práctica.
3. **"El self-check es ciego a la clase que lo motivó."** Parcialmente falso: en
   entry points de hooks detecta imports guardados igual que los no guardados. La
   ceguera es real sólo en módulos `cos_lib/*.py` shippeados (§5). El autor se
   subestimó en un caso y acertó en el otro.
4. **"Carga ~270 sobre 12 cores."** Medido con `uptime` durante las corridas:
   `149.76 256.27 254.25` y `146.36 231.10 244.73`. El 1-minuto estaba en
   **146-150**, no en 270; las ventanas de 5 y 15 minutos, en 231-256. El 270
   probablemente venga de una ventana larga leída en otro momento. No cambia la
   conclusión de que el wall no es portable, pero sí el tamaño del castigo.
5. **"Las 12 ediciones."** Son 12 pares replace/with sobre 4 archivos, contados
   con `grep -c '^\*\*Replace:\*\*'`. Confirmado.
6. **"`install.sh` hace `rm -rf "$TARGET_DIR"` en las líneas 415 y 424."**
   Confirmado por `grep -n 'rm -rf' install.sh` → 416 y 425 (más 54 y 475 sobre
   temporales). El desfase de una línea no cambia nada; el riesgo es real y por
   eso no se corrió `install.sh` en ningún momento.
7. **Premisa restrictiva que no se pudo cumplir tal cual:** no se pudo usar
   `git worktree` para materializar el árbol original — el guard
   `destructive-git-blocker` (ADR-055b) lo bloquea, y no se lo bypasseó. Se
   resolvió con `git archive 8602ddc70 | tar -x`, que es read-only y no crea
   estado de git. El paso se hizo igual, por otro camino.
8. **"Hay dos agentes tocando `hooks/bash-hot-path-dispatcher.sh`."** Verificado
   de hecho: una llamada a Bash fue rechazada por un error de sintaxis en
   `hooks/bash-hot-path-dispatcher.sh:129` (`|&` inesperado) mientras ese archivo
   estaba a medio editar. Se reintentó sin tocar nada y pasó. No se modificó
   ningún archivo ajeno.

9. **La rama del checkout cambió durante el trabajo.** Al arrancar la sesión el
   repo estaba en `session/21f28a76-audit-2026-08-15`; al momento de commitear,
   `git rev-parse --abbrev-ref HEAD` devuelve `main`. El commit (`fd5c58b98`) es
   el mismo, así que el clon y todas las mediciones siguen siendo válidas.
   Consecuencia práctica: `destructive-git-blocker` bloquea commitear en `main` y
   sugiere crear una rama de sesión. **No se creó**: hay otras dos sesiones con
   ediciones sin commitear en este mismo checkout
   (`hooks/bash-hot-path-dispatcher.sh`, `hooks/provenance-scan.sh`) y cambiarles
   la rama debajo es peor que el problema que evita. Se usó
   `COS_ALLOW_MAIN_BRANCH_WRITE=1` —una de las salidas que el propio guard
   ofrece— con un commit path-scoped de un único archivo nuevo.

---

## 11. Conclusión

**Qué se puede afirmar de esta reconstrucción, y qué no.**

Se puede afirmar que **esta reconstrucción pasa este ciclo, contra este árbol
(`fd5c58b98`), hoy**: 11 de sus 12 ediciones aplican, la que falla lo hace
porque el defecto ya está arreglado, el install `--default` desde el árbol
parchado termina en 0 con el self-check en verde, y el self-check se vio en
**rojo las cuatro veces que debía** —base sin parchar (12), módulo borrado del
install, módulo borrado del fuente, hook fantasma— con control limpio antes y
después de cada una. Se puede afirmar también que su ceguera declarada existe,
acotada a los módulos `cos_lib` shippeados, con un caso real en el árbol de hoy;
y que la rama `--full`, que nadie había corrido, **falla el install** por un
defecto preexistente que este check recién ahora hace visible.

No se puede afirmar que se haya **reproducido el resultado original**. El
artefacto que pasó aquel ciclo no existe, no hay contra qué diffear, y la
coincidencia de los 12 hallazgos es evidencia de que el defecto es estable, no
de que este código sea aquel código. Tampoco se puede afirmar nada sobre
consumidores reales: ninguno se tocó, y todo lo medido es sobre installs nuevos
y descartables. Y no se puede afirmar que el parche sea seguro de aplicar tal
cual: rompe `--full`, y su edición 11 duplica un import que ya está en el árbol.

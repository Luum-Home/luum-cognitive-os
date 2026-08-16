# Cierre de la familia de enforcers de rutas de home — 2026-08-15

Los dos miembros defectuosos de la familia `home-path-leak` quedaron
CONFORMING. El arreglo es de clasificación, no de detección: ninguno de los dos
patrones de detección se aflojó, y la sonda y sus fixtures quedaron intactas.

Notación: `<MAC>` es la raíz de home de macOS y `<LINUX>` la de Linux. Se
escriben así en este informe por la misma razón por la que
`hooks/research-compliance-guard.sh` compone la suya en pedazos — un documento
que las lleva armadas trippea a los cuatro miembros que describe.

---

## 1. La sonda, antes y después

```
python3 scripts/family_conformance_probe.py
```

**Antes** (exit 1):

```
scanned 709 candidates, 37 passed the channel screen, 4 are members
DEFECTIVE (2):
  - hooks/research-compliance-guard.sh   [(no args)]
  - scripts/provenance_scan.py   [(no args)]
CONFORMING (2):
  - scripts/check-local-privacy.sh   [(no args)]
  - scripts/check_absolute_paths.py   [(no args)]
```

**Después** (exit 0):

```
scanned 710 candidates, 37 passed the channel screen, 4 are members
CONFORMING (4):
  - hooks/research-compliance-guard.sh   [(no args)]
  - scripts/check-local-privacy.sh   [(no args)]
  - scripts/check_absolute_paths.py   [(no args)]
  - scripts/provenance_scan.py   [(no args)]
```

El censo pasó de 709 a 710 candidatos porque este trabajo agregó un `.sh` a
`scripts/`. No pasa el channel screen (no dice `diff --cached`, `ls-files` ni
`--staged`), así que no entra a la población medida.

---

## 2. Qué extraía mal la rama `/Projects/` — y por qué el encargo se equivoca acá

**El encargo dice**: «`_home_paths_all_exempt()` extrae el segmento con dos
`${token#*/}`, que sirve para la primera rama. Verificá qué extrae para la
segunda y arreglá la extracción.»

**Medido**: la extracción anda perfecto en las dos ramas. Lo que estaba roto es
el filtro de admisión que viene inmediatamente después.

Bisección de las tres líneas del fixture `must-not-trigger`, con los regex del
hook reconstruidos a mano:

```
line 1: PATH_RE=no  branch1=silent branch2=silent tokens=[<MAC>/[a-zA-Z0-9._-]+']
line 2: PATH_RE=no  branch1=silent branch2=silent tokens=[<MAC>/[a-zA-Z0-9._-]+']
line 3: PATH_RE=YES branch1=silent branch2=FIRED  tokens=[<MAC>/[a-z0-9._-]+]
```

Sólo la línea 3 dispara, y sólo por la rama 2. Para esa línea los dos
`${token#*/}` devuelven `[a-z0-9._-]+`, que es exactamente el segmento que hay
que juzgar, y que `_describes_a_username()` habría eximido sin problema.

Nunca llegó a preguntárselo. El filtro que sigue a la extracción era:

```bash
case "$seg" in
  [A-Za-z0-9._-]*) ;;
  *) continue ;;
esac
```

y su comentario declaraba la premisa: *«sólo los tokens cuyo segmento abre con
un carácter legal en un nombre de cuenta pueden haber producido un hit de
`HOME_PATH_RE`»*. Eso es cierto para la rama 1, cuyo segmento es
`[A-Za-z0-9._-]+`. Es **falso** para la rama 2, cuya clase de apertura es
`[^.]` — que admite `[`. El segmento `[a-z0-9._-]+` caía por el `continue`,
`found` quedaba en 0, y la función devolvía «no exento» no porque el segmento
fallara el test de exención sino porque nunca se lo sometió a él.

O sea: el defecto no está en qué se extrae, está en qué se descarta antes de
clasificar. El arreglo agrega un segundo lazo sobre un token propio de la rama
2 (`HOME_PROJECTS_TOKEN_RE`), en vez de aflojar el filtro de la rama 1.

**La propiedad fail-closed queda intacta**: un token que ninguno de los dos
lazos puede parsear deja `found=0` y sigue bloqueando. Está afirmado en un
comentario y verificado por el caso `personal` del mutation test.

---

## 3. `scripts/provenance_scan.py` — quinto miembro, nunca censado

Tenía el defecto completo: `allowed_path_match()` no conocía ni
`CI_MACHINE_SEGMENTS` ni `_describes_a_username()`. Corriendo el escáner contra
el fixture `must-not-trigger` reconstruido, marcaba las tres líneas:

```
docs/06-Daily/reports/probe-fixture.md:1: forbidden-path: <MAC>/[a-zA-Z0-9._-]+ — host-local or non-canonical path
docs/06-Daily/reports/probe-fixture.md:2: forbidden-path: <MAC>/[a-zA-Z0-9._-]+ — host-local or non-canonical path
docs/06-Daily/reports/probe-fixture.md:3: forbidden-path: <MAC>/[a-z0-9._-]+/Projects/ — host-local or non-canonical path
```

Se agregaron las dos exenciones que ya tenían los otros tres, con la misma barra
de admisión escrita en el comentario: *¿esta cadena identifica a una persona en
alguna máquina? Si la respuesta es «depende», no entra.* `CI_MACHINE_SEGMENTS`
queda en `{"runner"}`, en paridad exacta con los hermanos — no se le agregó
ninguna entrada para hacer pasar un test.

### Unificación de forma: sí, con una excepción declarada

**Decisión: se unificó.** La exención de `jovyan` salió del regex de detección
(`LINUX_HOME_PATTERN + r"(?!jovyan/)…"`) y pasó a
`DEFAULT_ALLOWED_ABSOLUTE_PATHS`, que es la misma forma que
`ALLOWED_POSIX_PREFIXES` en `scripts/check_absolute_paths.py`.

Motivos, en orden de peso:

1. **Una exención adentro de la detección no produce match**, así que nada
   aguas abajo puede reportarla ni auditarla. Es el caso que la regla de
   "gates sin trampa" llama supresor invisible: no se lo ve disparar nunca.
2. **La forma de los hermanos ya existía en este archivo.** El manifiesto
   `manifests/provenance-scan.yaml` ya lista `<LINUX>/jovyan/` en
   `allowed_absolute_paths`, o sea que el lookahead era redundante *en este
   repo*. Se lo movió al default del código para no romper a los consumidores
   que no tienen ese manifiesto.
3. Consistencia entre los cuatro: los cuatro ahora exponen `CI_MACHINE_SEGMENTS`
   y un `describes_a_username` con el mismo nombre y el mismo criterio.

**Lo que NO se tocó, a propósito**: `allowed_by_prefix()` está anclado a la
barra, así que el home pelado de `jovyan` (sin `/` final) se sigue marcando
mientras que `<LINUX>/jovyan/work` no. Esa asimetría es idéntica en
`check_absolute_paths.py`, es una propiedad de la familia de exenciones por
prefijo, y arreglarla sólo acá sacaría a este miembro de paridad. Queda
anotada en el código y reportada abajo como hallazgo abierto.

---

## 4. Mutation test por token

Instrumento nuevo, versionado: `scripts/home-path-family-mutation-check.sh`
(read-only contra el repo, sandbox descartable por caso, exit 0/1/2).

La sonda da un veredicto **por archivo**. Eso no alcanza para lo que más
importa acá: un miembro que deja de bloquear una fuga real porque el archivo
además tiene una ruta de CI. Ensanchar el regex hasta que el falso positivo
desaparezca pasa la sonda y produce exactamente eso.

Cuatro casos por miembro:

| caso | contenido | esperado |
|------|-----------|----------|
| `ci` | `<LINUX>/runner/work/…` solo | PASS |
| `describes` | `<MAC>/[a-z0-9._-]+/Projects/` dentro de un `git grep` | PASS |
| `personal` | home sintético `<MAC>/mnprobe/Projects/…` solo | BLOCK |
| `mixed` | los tres en un mismo archivo | BLOCK, nombrando sólo el personal |

### Por qué `describes` es un caso aparte y no redundante

El encargo trae la lección de medición correcta y hace falta aplicarla a este
mismo test. La primera versión que escribí tenía sólo `ci`, `personal` y
`mixed`, y **daba todo verde** — pero el token de CI (`<LINUX>/runner/…`)
instancia únicamente la rama 1, que ya andaba. Control negativo contra `HEAD`
(las versiones pre-arreglo, extraídas con `git show`):

```
--- PRE-FIX guard on 'describes' (expect BLOCK = my test would catch it) ---
guard rc=2 (0=pass, 2=block)
--- PRE-FIX provenance_scan on 'describes' ---
provenance rc=1 (0=pass, non-0=block)
--- PRE-FIX guard on 'ci' only (expect PASS -> ci case alone proves nothing) ---
guard rc=0
```

Con `ci` solo, el hook roto pasa. El caso que discrimina es `describes`, que
está escrito en la segunda forma a propósito.

### Salida (`bash scripts/home-path-family-mutation-check.sh`, exit 0)

```
=== per-token mutation check: home-path-leak family ===

  hooks/research-compliance-guard.sh
    ci        expected PASS  got PASS   OK
    describes expected PASS  got PASS   OK
    personal  expected BLOCK got BLOCK  OK
    mixed     expected BLOCK got BLOCK  OK
               | === RESEARCH-COMPLIANCE-GUARD: BLOCKED ===
               | Research, license, or clean-room boundary issues were found:
               |   - docs/06-Daily/reports/mutation-fixture.md: contains a personal absolute home path; use repo-local or redacted paths

  scripts/check-local-privacy.sh
    ci        expected PASS  got PASS   OK
    describes expected PASS  got PASS   OK
    personal  expected BLOCK got BLOCK  OK
    mixed     expected BLOCK got BLOCK  OK
               | docs/06-Daily/reports/mutation-fixture.md:5: developer home path: <MAC>/mnprobe/Projects/luum/luum-agent-os/build/out.log
               | BLOCKED: local privacy guard found host/user/project-specific content.

  scripts/check_absolute_paths.py
    ci        expected PASS  got PASS   OK
    describes expected PASS  got PASS   OK
    personal  expected BLOCK got BLOCK  OK
    mixed     expected BLOCK got BLOCK  OK
               | docs/06-Daily/reports/mutation-fixture.md:5: developer home path: <MAC>/mnprobe/Projects/luum/luum-agent-os/build/out.log
               | BLOCKED: developer-specific absolute home paths are not portable.

  scripts/provenance_scan.py
    ci        expected PASS  got PASS   OK
    describes expected PASS  got PASS   OK
    personal  expected BLOCK got BLOCK  OK
    mixed     expected BLOCK got BLOCK  OK
               | docs/06-Daily/reports/mutation-fixture.md:5: forbidden-path: <MAC>/mnprobe/Projects/luum/luum-agent-os/build/out.log — host-local or non-canonical path

OK: 4 members, 4 mutations each, no violations.
```

En `mixed` el archivo tiene las tres clases de token; los tres miembros que
reportan texto matcheado nombran **sólo la línea 5** (el token personal), no la
línea 3 (CI) ni la 4 (`describes`).

**Granularidad, dicha y no escondida**: `hooks/research-compliance-guard.sh`
reporta un hallazgo por archivo, no por match, así que para ese miembro `mixed`
se degrada a «bloquea el archivo mixto». Su comportamiento por token igual queda
ejercitado —`_home_paths_all_exempt()` exige que **todos** los tokens del
archivo sean exentos— pero la evidencia es el veredicto, no un token citado.

---

## 5. Suite existente

```
.venv/bin/pytest tests/unit/test_guard_false_positives.py tests/unit/test_check_local_privacy.py -q
→ 1 failed, 31 passed in 75.04s
FAILED tests/unit/test_check_local_privacy.py::test_repo_all_scan_passes
       subprocess.TimeoutExpired: … --all … timed out after 20.0 seconds
```

Es el fallo pre-existente que avisaba el encargo. **No se tocó**: es una
decisión abierta del operador (subir el timeout vs. hacer el escaneo más
rápido).

Suites adicionales que sí tocaba este cambio:

```
.venv/bin/pytest tests/unit/test_check_absolute_paths.py -q  → 17 passed
.venv/bin/pytest tests/unit/test_provenance_scan.py -q       → 9 passed
```

---

## 6. Correcciones a las premisas del encargo

1. **«Arreglá la extracción para la segunda rama» — falso.** La extracción
   (`${token#*/}` dos veces) devuelve el segmento correcto en las dos ramas.
   Lo roto era el filtro de admisión posterior, cuya premisa escrita sólo vale
   para la rama 1. Detalle y bisección en §2. Es una corrección de mecanismo,
   no de conclusión: la rama `/Projects/` **sí** es la causa, como decía el
   encargo. El diagnóstico heredado acertó el dónde y erró el qué.

2. **«No toques `scripts/family_conformance_probe.py`» — el archivo ya estaba
   sucio cuando llegué.** `git status` lo muestra modificado, con 42 líneas
   agregadas por otra sesión (matan el árbol de procesos del candidato con
   `killpg` en vez de dejarlo huérfano). O sea que la sonda que uso como
   criterio de aceptación no es la versión commiteada. No la toqué, pero el
   operador debería saber que el instrumento está midiendo desde el working
   tree de otra sesión, no desde `HEAD`.

3. **«709 candidatos» — confirmado antes, 710 después.** El delta es el `.sh`
   que agregué a `scripts/`; no pasa el channel screen, así que no altera la
   población de 37 ni el conteo de 4 miembros. Los tres números están
   verificados con corridas propias, no citados del encargo.

4. **`hooks/**` está protegido — confirmado, y el permiso alcanzó.** No hizo
   falta ningún otro path protegido. `scripts/` efectivamente no está
   protegido: las ediciones ahí no requirieron la variable.

5. **«El tercer enforcer se escapó del censo porque compone su literal, y en
   realidad los tres lo componen» — verificado, y el encargo tiene razón en
   dudar de sí mismo.** Los cuatro miembros componen la raíz:
   `MAC_HOME_SEG='/'"Users"` en el hook, `SLASH + "Users" + SLASH` en
   `provenance_scan.py`, y sus equivalentes en los otros dos. La composición no
   explica por qué uno se escapó del censo; lo que lo explica es que el censo
   se tomó por texto y la familia se define por comportamiento, que es
   exactamente lo que dice el docstring de la sonda.

6. **Hallazgo que no pedía el encargo, encontrado por accidente**: la primera
   versión del comentario que escribí en `provenance_scan.py` contenía el
   literal del home pelado de `jovyan` y **rompió
   `test_repo_has_no_tracked_developer_home_paths`**, demostrando en el acto la
   asimetría de barra final que el comentario describía. Se reescribió el
   comentario sin literales. La asimetría en sí sigue abierta (§3).

7. **Flake observado, sin explicación cerrada**: en una corrida intermedia,
   `test_check_absolute_paths.py::test_repo_has_no_tracked_developer_home_paths`
   falló y en las tres corridas siguientes pasó, sin cambios míos en el medio.
   `.claude/settings.local.json` —el archivo con más rutas de home del repo—
   está **untracked**, así que no es él. Con dos sesiones concurrentes
   escribiendo el árbol, lo más probable es una escritura ajena transitoria
   sobre un archivo trackeado. No lo pude reproducir.

---

## 7. Hallazgos abiertos (no accionados)

| # | Hallazgo | Severidad | Por qué no se tocó |
|---|----------|-----------|--------------------|
| 1 | Exenciones por prefijo ancladas a `/`: el home pelado de una cuenta de contenedor se marca, el subdirectorio no. Presente en `provenance_scan.py` y `check_absolute_paths.py`. | Baja | Propiedad de familia. Arreglarla en un solo miembro rompe la paridad que este trabajo vino a restaurar. Va como cambio de los cuatro o de ninguno. |
| 2 | `test_repo_all_scan_passes` con timeout de 20 s contra un escaneo de 41 s. | Media | Decisión abierta del operador, explícitamente fuera de alcance. |
| 3 | La sonda corre desde el working tree de otra sesión, no desde `HEAD`. | Media | Ver corrección 2. El instrumento de aceptación de este lote no está commiteado. |
| 4 | `research-compliance-guard.sh` escanea el cuerpo del `-m` como si fueran comandos. | Baja | Defecto conocido, excluido por el encargo. Se usó `-F` para el commit. |

---

## 8. Reproducir todo

```bash
python3 scripts/family_conformance_probe.py          # exit 0, los cuatro CONFORMING
bash    scripts/home-path-family-mutation-check.sh   # exit 0, 4 miembros x 4 mutaciones
.venv/bin/pytest tests/unit/test_check_absolute_paths.py tests/unit/test_provenance_scan.py -q
```

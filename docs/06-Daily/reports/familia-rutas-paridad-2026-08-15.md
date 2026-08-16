# Paridad de la familia de rutas de home, y el timeout que medía la máquina — 2026-08-15

Dos deudas cerradas. La primera era una brecha de paridad real y el arreglo es
de tres palabras. La segunda venía planteada como una elección entre dos
salidas, y la medición mostró que ninguna de las dos era la pregunta.

Notación: `<MAC>` es la raíz de home de macOS y `<LINUX>` la de Linux. Se
escriben así por el mismo motivo que en el informe de cierre — un documento con
las raíces armadas trippea a los cuatro miembros que describe.

---

## 1. La sonda, antes y después

```
python3 scripts/family_conformance_probe.py
```

**Antes y después dan lo mismo**, y eso es el hallazgo, no un trámite:

```
=== family: home-path-leak  (working tree) ===
  scanned 712 candidates, 37 passed the channel screen, 4 are members
  CONFORMING (4):
    - hooks/research-compliance-guard.sh   [(no args)]
    - scripts/check-local-privacy.sh   [(no args)]
    - scripts/check_absolute_paths.py   [(no args)]
    - scripts/provenance_scan.py   [(no args)]
```

exit 0 antes y después. La sonda quedó intacta, sus fixtures también.

El censo pasó de 710 candidatos (informe de cierre, unas horas antes) a 712.
Los dos nuevos son de otras sesiones; no pasan el channel screen y no alteran
ni la población de 37 ni el conteo de 4 miembros.

---

## 2. La sonda NO detectaba la brecha de `jovyan` — y por qué eso importa

```
grep -rn "jovyan" tests/fixtures/family-probe/
→ (sin resultados)
```

Los tres fixtures (`must-trigger`, `must-not-trigger`, `null`) no contienen
ningún token de cuenta asignada a una máquina o a una imagen. El
`must-not-trigger` está construido enteramente sobre la otra clase de exención
—segmentos que *describen* nombres de usuario, con `[`, `]`, `+` adentro— y el
`null` usa `/opt/app/bin`, que no es un home.

O sea: **la sonda dio `hooks/research-compliance-guard.sh` CONFORMING en la
misma revisión donde ese hook bloqueaba una ruta de contenedor**. No es una
inferencia; está en el informe de cierre de esta mañana, que reporta los cuatro
CONFORMING sobre un árbol donde la brecha existía, y quedó comprobado acá
corriendo el guard de `HEAD` contra un sandbox (§3).

Qué dice eso de la sonda: **contesta bien la pregunta que declara y no más que
ésa.** Su docstring pregunta *«¿el candidato rechaza una ruta de home real
dejando pasar un documento que DESCRIBE el patrón?»* — un discriminador binario
entre dos clases. La familia tiene por lo menos tres clases de token exento
(describe-un-usuario, asignado-a-máquina, asignado-a-imagen) y la sonda sólo
instancia la primera. No es un bug de la sonda; es su alcance, y el alcance
estaba escrito. Lo que sí es un problema es leer «4 CONFORMING, exit 0» como
«los cuatro se comportan igual», que es más de lo que el instrumento afirma.

Esto es el mismo error que el propio `must-not-trigger` documenta sobre sí
mismo —«un discriminador que instancia sólo la primera forma deja la segunda
rama sin ejercitar»— repetido un nivel más arriba: la lección se aplicó a las
dos *ramas del regex* y no a las *clases de exención*.

**Acción tomada**, sin tocar la sonda ni sus fixtures: el caso `image` se
agregó a `scripts/home-path-family-mutation-check.sh`, que es el instrumento
por token y no por archivo (commit `71715891f`).

```
bash scripts/home-path-family-mutation-check.sh   → exit 0
  4 miembros x 5 mutaciones, sin violaciones
```

El caso está escrito **con subdirectorio** a propósito: tres miembros expresan
la exención como prefijo anclado a la barra, así que el home pelado de la
cuenta les sigue bloqueando. Un caso construido sobre el home pelado fallaría
por un motivo ajeno a la brecha que viene a cuidar.

---

## 3. El diff del hook

`hooks/research-compliance-guard.sh` es un archivo real, no un symlink
(`readlink` no devuelve nada). Es el único path protegido que se tocó; no hizo
falta ningún otro. `COS_ALLOW_PROTECTED_CONFIG_WRITE=1` se usó sólo para él.

```diff
@@ -92,7 +92,26 @@ HOME_PROJECTS_TOKEN_RE="${MAC_HOME_SEG}/[^.][^/[:space:]]+/Projects/"
  # Observed 2026-08-15: a report auditing home-path leakage blocked its own
  # commit on four matches, all of them the CI runner path, which the report
  # itself classified as CI before concluding zero leaks.
-CI_MACHINE_SEGMENTS=" runner "
+#
+# `jovyan` clears the same bar for the same reason: it is the fixed home
+# account of the jupyter/docker-stacks images, a coined word (from "jovian",
+# of Jupiter) chosen by that project precisely so it would never collide with
+# a person's account. It is allocated to an IMAGE, identical in every
+# container built from it, and published in the image documentation. Nobody is
+# named jovyan on any machine, so the question "does this string identify a
+# person?" has a clean no, not an "it depends".
+#
+# Parity note, and a real behavioural difference worth knowing: the other
+# three members express this same exemption as a `/`-ANCHORED PREFIX
+# (ALLOWED_POSIX_PREFIXES in scripts/check-local-privacy.sh,
+# DEFAULT_ALLOWED_ABSOLUTE_PATHS in scripts/provenance_scan.py,
+# ALLOWED_POSIX_PREFIXES in scripts/check_absolute_paths.py), so for them the
+# bare home directory of the account still blocks while a subdirectory of it
+# passes. This guard has no prefix mechanism, only segments, so here both
+# forms pass. The divergence goes in the direction the 2026-08-15 family
+# report already recorded as the siblings' open defect (finding #1: prefix
+# exemptions anchored to the slash), not toward leniency about persons.
+CI_MACHINE_SEGMENTS=" runner jovyan "
```

Una sola entrada agregada. Los patrones de detección quedaron intactos: la
exención se consulta *después* de un hit, así que sólo puede quitar un
hallazgo, nunca crear uno.

### Verificación del comportamiento, no del texto

Sandbox descartable con un archivo staged que contiene una ruta de contenedor
(`<LINUX>/jovyan/work/…/out.log`), los cuatro miembros corridos contra él, y el
guard de `HEAD` (`git show HEAD:hooks/research-compliance-guard.sh`) como
control negativo:

```
PRE-FIX  hooks/research-compliance-guard.sh   → BLOCKED
  - docs/06-Daily/reports/f.md: contains a personal absolute home path
POST-FIX hooks/research-compliance-guard.sh   rc=0
POST-FIX scripts/check-local-privacy.sh       rc=0
POST-FIX scripts/check_absolute_paths.py      rc=0
POST-FIX scripts/provenance_scan.py           rc=0
```

La brecha era real, está cerrada, y los otros tres no se movieron.

### Lo que quedó torcido y no se arregló

El set se llama `CI_MACHINE_SEGMENTS` y `jovyan` no es CI. El comentario que lo
encabeza sí es correcto para ambos («user segments that are not a personal home
by construction»), pero el nombre quedó más angosto que su contenido.
Renombrarlo bien —`MACHINE_ALLOCATED_SEGMENTS`, digamos— toca los cuatro
miembros, tres de ellos fuera del permiso de este lote. Va como hallazgo
abierto, no como cambio a medias.

---

## 4. La duración recontada: 41 s era la máquina, no el escaneo

**El encargo dice**: «el escaneo completo tarda 41 s y sale 0 — pasa, sólo que
tarde», y ofrece dos salidas: subir el timeout o hacer el escaneo más rápido.

**Medido**: el mismo comando, el mismo commit, dos veces, con horas de
diferencia.

```
bash scripts/check-local-privacy.sh --all
```

| carga (12 núcleos) | user | sys | reloj | %CPU |
|---|---|---|---|---|
| load avg 11.77 | 1.87s | 0.29s | 2.3 / 2.6 / 3.1 / 4.5 s | 85% |
| load avg 180.56 | 2.19s | 0.50s | **32.8 s** | **8%** |

**El 8% es todo el hallazgo.** El trabajo del escaneo es constante —unos 2 s de
CPU— y no se movió entre las dos corridas. Lo que se movió 14x fue el reloj, y
a 32.8 s el proceso estaba esperando un núcleo, no escaneando. Los 41 s del
encargo son de la misma familia: seis sesiones de agente compartiendo una
máquina de 12 núcleos con load average de tres dígitos.

La primera corrida de este lote dio **2.6 s de reloj y exit 0**, con el test
pasando en 2.49 s. Es decir: el test que el encargo declara «falla siempre»
pasaba cómodo en ese momento. No falla siempre; falla cuando la máquina está
saturada, que hoy es casi todo el tiempo.

### Dónde se va el tiempo

8526 archivos trackeados. El más grande es
`docs/06-Daily/reports/primitive-harness-coverage-latest.json`: **35.8 MB,
1.288.742 líneas**, y `.json` **no** está en `DEFAULT_EXCLUDED_SUFFIXES`
(sólo hay imágenes y PDFs ahí), así que entra entero al lazo de patrones.
Leerlo y partirlo en líneas cuesta 0.069 s de CPU; **no aislé qué fracción de
los ~2 s se va en aplicarle los regex línea por línea**, así que lo dejo como
sospecha fundada y no como número.

Y da igual, que es el punto: aunque ese archivo fuera el 100% del costo,
sacarlo no arregla nada. Al 8% de CPU disponible, la mitad del trabajo sigue
costando ~16 s de reloj. **No se puede optimizar el tiempo de espera de un
núcleo achicando el trabajo.**

---

## 5. Qué se decidió sobre el timeout, y por qué

**Se subió el número.** El criterio del encargo para que eso sea legítimo —«el
número existe para atrapar un cuelgue, no para imponer un presupuesto de
performance»— se cumple, y ahora con evidencia en vez de con intuición:

1. **`--all` no corre en pre-commit.** `.githooks/pre-commit:59` invoca el
   guard con `--staged`. El escaneo completo vive en `scripts/cos-patch-release`
   (líneas 40-41). Nadie lo espera de forma interactiva, así que su costo no es
   un presupuesto de UX. El encargo mandaba fijarse esto antes de decidir; es
   lo que dio vuelta la respuesta.
2. **El escaneo no es lento.** 2 s de CPU sobre 8526 archivos. Acelerarlo sería
   optimizar algo que no está lento, y no tocaría la causa del rojo.
3. **20 s estaba por debajo de una corrida legítima.** Un timeout que una
   corrida sana supera bajo contención reporta presión de scheduling como
   defecto del guard. Eso no es un detector de cuelgue, es ruido.

El número nuevo es **120 s ≈ 60x el costo de CPU medido**, con la tabla de
medición escrita al lado en el código para que la próxima vez la deriva se vea
en vez de descubrirse. Y con la instrucción de qué mirar: si sube el `user`
—no el reloj— el que regresó es el escaneo y el arreglo va ahí.

Los otros 8 tests del archivo **siguen en 20 s** (`SANDBOX_TIMEOUT_S`): corren
contra repos de juguete de un puñado de archivos, donde sólo un cuelgue llega a
ese número. Subir el techo de todos habría sido relajar 8 aserciones para
arreglar 1.

### El hallazgo que casi convierte el arreglo en un empeoramiento

Subir `run_guard(timeout=…)` **solo** no arregla el test: lo empeora.

`pytest.ini` fija `timeout = 30` por test (`timeout_method = thread`), y
`tests/conftest.py` **limita cualquier timeout explícito de subproceso a ese
presupuesto**. Con el cambio hecho únicamente en `run_guard`, el test dejó de
fallar a los 20 s con un `TimeoutExpired` legible y pasó a morir a los 30 s
bajo `pytest-timeout`, cuyo volcado con método `thread` **aborta la sesión
entera** en lugar de un solo test. Lo vi en vivo: el archivo completo pasó de
«1 failed, 8 passed» a un volcado de stack sin resumen.

O sea: el techo real nunca fue el 20 de `run_guard`. Era el 30 de `pytest.ini`,
y el encargo —igual que yo en el primer intento— no lo tenía en cuenta.

El arreglo completo son **dos números en el orden correcto**:

```python
REPO_SCAN_TIMEOUT_S = 120        # timeout del subproceso
REPO_SCAN_PYTEST_BUDGET_S = 180  # @pytest.mark.timeout, POR ENCIMA del anterior
```

El presupuesto de pytest tiene que quedar arriba para que dispare primero el
timer de adentro, que es el único que sabe decir *qué comando* se colgó.

### Verificación

```
.venv/bin/pytest tests/unit/test_check_local_privacy.py -q
→ 9 passed in 28.96s        (load average 168.72)
```

Bajo exactamente la carga que antes mataba la sesión.

### Qué NO se hizo

- No se excluyó ningún archivo del escaneo. Eso reduce la medición, no el
  tiempo, y además dejaría de mirar el archivo más grande del repo.
- No se marcó el test `skip` ni `xfail`.
- No se subió el techo de los otros 8 tests.

---

## 6. Correcciones a las premisas del encargo

1. **«El test falla siempre» — falso.** La primera corrida de este lote:
   `1 passed in 2.49s`. Falla de forma intermitente, en función de la carga de
   la máquina, no del contenido del repo ni del código del guard. Un test que
   falla por contención de CPU y se describe como «falla siempre» empuja hacia
   arreglar el sujeto equivocado.

2. **«El escaneo tarda 41 s» — cierto como observación, falso como propiedad
   del escaneo.** Medido: 1.87-2.19 s de CPU siempre; 2.3 s a 32.8 s de reloj
   según el load average. Los 41 s son la máquina.

3. **«Hoy entraron 403 archivos al repo» — no lo pude confirmar, y no cambia
   nada.** El escaneo cuesta ~2 s sobre 8526 archivos trackeados; el volumen no
   es el eje. No gasté llamadas en recontar los 403 porque ninguna decisión
   dependía de ese número.

4. **«Las dos salidas son legítimas y excluyentes» — la dicotomía no cerraba.**
   «Hacer el escaneo más rápido» no era una salida disponible: no arregla un
   rojo causado por 8% de CPU disponible. Y «subir el timeout» tampoco alcanzaba
   por sí sola, por el techo de `pytest.ini` que ninguna de las dos opciones
   mencionaba. La salida real era una tercera: **ordenar los dos techos** y
   escribir la medición.

5. **«Fijate si corre en pre-commit» — corre, pero con otro modo.** El
   pre-commit invoca `--staged`, no `--all`. La instrucción del encargo era
   correcta y fue la que dio vuelta la decisión; la anoto porque la respuesta
   («sí corre, pero no éste») es distinta de las dos que el encargo anticipaba.

6. **«Los otros tres eximen a `jovyan`» — cierto, con un mecanismo distinto que
   el encargo no menciona.** Los tres lo hacen con un **prefijo anclado a la
   barra**, no con una entrada en `CI_MACHINE_SEGMENTS` (que en los tres vale
   exactamente `{"runner"}`). El hook no tiene mecanismo de prefijo. La
   consecuencia está en el diff y en el comentario: para los tres hermanos el
   home pelado de la cuenta sigue bloqueando y el subdirectorio pasa; para el
   hook pasan los dos. Es una divergencia de comportamiento **nueva**, medible,
   y va en la dirección que el informe de cierre ya había anotado como defecto
   abierto de los hermanos (hallazgo #1), no hacia ser laxo con personas.

7. **«La sonda es el instrumento de esta familia» — lo es, y no cubre esto.**
   Verificado en §2: cero ocurrencias de tokens asignados a máquina o a imagen
   en los fixtures, y los cuatro CONFORMING sobre un árbol con la brecha
   presente. El encargo anticipó la posibilidad; se confirmó.

8. **«`timeout` no existe en este macOS» — no lo usé, así que no lo verifiqué.**
   Lo anoto para no dar por confirmada una premisa que no probé.

9. **Restricciones verificadas, no asumidas.** `git status --porcelain` sobre
   los tres paths antes de cada `git add`: los tres aparecían sólo como míos.
   `readlink` sobre los tres: archivos reales, ningún symlink a `packages/`.
   Tres commits con `--only` y pathspec, ningún `-A`, ningún `--amend`. El
   `.git/index.lock` estaba tomado en el segundo commit y el reintento lo
   resolvió, así que la advertencia sobre sesiones concurrentes era exacta.

---

## 7. Hallazgos abiertos

| # | Hallazgo | Severidad | Por qué no se accionó |
|---|----------|-----------|------------------------|
| 1 | `CI_MACHINE_SEGMENTS` ahora contiene una entrada que no es de CI. El nombre quedó más angosto que el contenido. | Baja | Renombrar toca los cuatro miembros; tres están fuera del permiso de este lote. |
| 2 | Divergencia de mecanismo: tres miembros eximen por prefijo anclado a `/`, el hook por segmento. El home pelado bloquea en tres y pasa en uno. | Media | Unificar es un cambio de los cuatro o de ninguno. Es el hallazgo #1 del informe de cierre, ahora con una segunda manifestación. |
| 3 | Los fixtures de la sonda no instancian tokens asignados a máquina ni a imagen. El instrumento no puede ver esta clase de brecha. | Media | Los fixtures están explícitamente fuera de alcance. Mitigado, no cerrado, por el caso `image` del mutation check. |
| 4 | `.json` no está excluido del escaneo de privacidad y el repo tiene un archivo trackeado de 35.8 MB / 1.29M líneas. Fracción del costo sin aislar. | Baja | No es la causa del rojo (§4) y excluirlo sería reducir la medición. Un JSON derivado de 36 MB en `docs/` es un problema aparte. |
| 5 | Todo el lote se midió en una máquina con load average de tres dígitos. Los números de CPU (`user`) son estables y confiables; los de reloj no valen fuera de esta sesión. | Media | Es una propiedad del entorno de medición, no del código. Vale re-medir en una máquina tranquila antes de tratar los 2 s como línea de base. |

---

## 8. Reproducir todo

```bash
python3 scripts/family_conformance_probe.py              # exit 0, los cuatro CONFORMING
bash    scripts/home-path-family-mutation-check.sh       # exit 0, 4 miembros x 5 mutaciones
.venv/bin/pytest tests/unit/test_check_local_privacy.py -q   # 9 passed
{ time bash scripts/check-local-privacy.sh --all ; }      # comparar `user` contra la tabla de §4
uptime                                                    # sin esto, el número de reloj no significa nada
```

Commits: `8fd0b29f0` (hook), `71715891f` (mutation check), `f9c6ed1b1` (timeouts).

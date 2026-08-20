# La defensa que nunca disparó — gate ejecutable

Fecha: 2026-08-20 · Alcance: shell versionado del repo (640 archivos)
Instrumento: `tests/audit/test_la_defensa_que_nunca_disparo.py`
Medición reproducible: `python3 tests/audit/test_la_defensa_que_nunca_disparo.py`
Gate: `.venv/bin/python -m pytest tests/audit/test_la_defensa_que_nunca_disparo.py -q`

## Resumen ejecutivo

Cubro **4 de las 7 sub-formas** del encargo (1, 2, 4 y 5), con **3 detectores**:
las sub-formas 2 y 5 son el mismo defecto y colapsan en uno. Las 3, 6 y 7 quedan
declaradas no cubiertas, con el motivo escrito.

Sobre 640 shell versionados el barrido marca **2 archivos**, los dos aceptados
con motivo escrito, **0 hallazgos sin explicar**. Encontró **1 defecto vivo**
—`scripts/deps-update.sh`, donde un WARNING era inalcanzable— arreglado en este
mismo commit con contrafáctico medido. Y encontró **un defecto en el propio
gate**: mis detectores de la sub-forma 4 nacieron sin `re.M`, ciegos a todo
`grep` que no estuviera en la línea 1. Los tres fixtures pasaban en verde. Lo
agarró el control sembrado. El gate nació con exactamente la clase que venía a
detectar, y sobrevivió una hora así.

**No está cableado a ningún hook ni a pre-commit.** Corre como test de la suite.

## Correcciones a las premisas del encargo

1. **Las sub-formas 2 y 5 son la misma.** «Exit code perdido en el pipeline» y
   «el `&&` colgando del comando equivocado» son el mismo hecho: el `$?` de un
   pipeline es el de su última etapa. Un solo detector cubre las dos. Por eso
   «3 de 7» quedó en 4 de 7 sin costo extra.

2. **`grep` en esta sesión NO es `/usr/bin/grep`.** El PATH interactivo tiene
   una *función de shell* que redirige a `ugrep` (la instala Claude Code).
   Medido: con el shim, `grep -oP 'a[b]'` → `ab`, rc=0, y `grep -oE '(?:a)b'`
   → `ab`, rc=0. Los dos "andan". `grep --version` devuelve
   `ugrep 7.5.0 ... -P:pcre2jit`. Un hook no ve ese shim. **Verificar
   portabilidad desde una sesión interactiva da el resultado opuesto al real**,
   y mis primeras tres mediciones fueron inválidas por eso. No refuta la
   sub-forma 4: refuta cómo se la verifica.

3. **El sitio citado de la sub-forma 1 ya está arreglado.**
   `hooks/secret-detector.sh:90` hoy dice `grep -oE -- "$pattern"`, y la
   pre-check de la línea 126 también. Las 6 claves son historia, no estado.

4. **La sub-forma 4 que encontré viva no es un defecto.**
   `packages/quality-gates/hooks/clarification-interceptor.sh:84` usa
   `grep -oP ... \K`, pero las líneas 85-88 son un `if [ -z "$QUESTIONS" ]` con
   la versión en `sed -n`. El camino alternativo ya está escrito. Un hallazgo es
   hipótesis, no veredicto.

5. **«La 1 es puramente sintáctica y barata» es cierto a medias.** Lo es para el
   patrón *literal*. La forma que realmente sangró acá es la *variable*
   (`grep -oE "$pattern"`, con el valor en un array), y ahí no hay sintaxis que
   alcance: la versión floja —«el archivo tiene un literal con guiones en algún
   lado»— da 1 hallazgo y 1 falso positivo (100%). Hubo que seguir un salto de
   dataflow para que discrimine.

6. **«El control positivo en fixture alcanza» es falso, y lo probó este trabajo.**
   Ver el resumen: `re.M`. Un fixture es un string que arranca con `grep`; el
   `^` de mi regex matcheaba el arranque del string y nadie se enteró. El mismo
   fixture, sembrado en el árbol bajo un `#!/usr/bin/env bash`, no lo encontró
   nadie. La corrección que mandaste a mitad de tarea es la que hizo el hallazgo.

7. **«Medí los falsos positivos sobre el árbol» tampoco alcanza**, y no por lo
   que dice el aviso que llegó después, sino por algo que ese aviso predijo: en
   este repo la cita textual del patrón viejo está en los comentarios que
   documentan los arreglos, y el guard ingenuo los marca. Ver `## La cita no es
   la ocurrencia`. La medición sobre el árbol tampoco lo habría revelado: el
   archivo afectado también tenía una ocurrencia real, así que el veredicto a
   nivel archivo salía bien por accidente.

8. **Restricciones que no verifiqué**, y lo digo en vez de trabajarlas de
   costado: no probé si `git worktree` está bloqueado ni si `timeout`/`flock`
   faltan — no los necesité. Sí verifiqué la de propiedad: los tres archivos que
   toqué no están en la lista de intocables y aparecían limpios en el
   `git status` de arranque.

## Qué sub-formas elegí y por qué esas

| # | Sub-forma | Detector | Por qué |
|---|-----------|----------|---------|
| 1 | Patrón leído como opción | `A_patron_como_opcion` | Literal con guion: sintaxis pura. Variable: un salto de dataflow dirigido (ciclo sobre array con literal de 3+ guiones), que es la forma exacta que sangró. |
| 4 | Existe, sale 0, vuelve vacío | `B_sale_0_y_vuelve_vacio` | `grep -P` y `(?...)` dentro de un `grep -E` son tokens. No hay ambigüedad. |
| 2+5 | Exit code perdido / `&&` colgado | `C_exit_code_perdido` | Sintáctica, pero solo discrimina si se exige que **alguien consuma** el estado. Sin eso son 56 archivos de ruido. |

Verificación de las tres contra el userland real, el 2026-08-20:

```
grep -oE "--foo--" f      -> rc=2   (patrón leído como opción)
grep -oE -- "--foo--" f   -> rc=0   (arreglado)
sh -c 'set -e; false; rc=$?; echo alcanzado'  -> nunca imprime, outer=1
```

## Las que NO cubro, y por qué no son estáticas

**3 — `; rc=$?` bajo `set -e`.** Hace falta saber si `set -e` está activo *en ese
punto*: puede venir de la línea 2, de un `set +e` intermedio, o heredado por un
`source`. Determinarlo estáticamente es análisis de flujo entre archivos. El
defecto es real (verificado arriba: la rama de error es inalcanzable), pero
detectarlo bien cuesta un orden de magnitud más que las otras tres.

**6 — El guard con una sola rama.** No es sintáctico *por definición*: la
condición está bien escrita, lo que falla es que el estado real siempre cae del
mismo lado (el PID efímero que daba muerto 10 de 10). Ningún parser lo ve. La
detección correcta es la que ya se usó acá: **correr la condición contra el
estado real y contar de qué lado cae; si una rama tiene cero casos, no
protege.** Eso es un instrumento de runtime, no un gate estático, y decirlo es
la respuesta, no una excusa.

**7 — El instrumento que chequea cero archivos.** El caso general es semántico
(hay que saber qué *debería* enumerar el instrumento). Pero hay una pieza que sí
es estática y la incluí: `test_el_corpus_no_esta_vacio` falla si el propio
corpus de este gate cae por debajo de 400 archivos. Es la sub-forma 7 aplicada
al gate mismo — la única parte que un test puede afirmar sobre sí.

## Falsos positivos medidos antes de cablear

Todo esto se midió **antes** de que el archivo tuviera un solo `assert` activo
sobre el árbol, corriendo el módulo como script.

| Detector | Versión floja | Marcados | Falsos positivos | Tras acotar |
|---|---|---|---|---|
| C | cualquier `&&`/`\|\|` tras filtro siempre-cero | **56 / 640 (8,8%)** | ~55 (dominante: `\| head -1 \|\| true`) | **1**, verdadero positivo |
| A literal | patrón con **2+** guiones | 1 | 1 (`grep -rl --binary-files=without-match`) | **0** |
| A variable | «el archivo tiene un literal con guiones» | 1 | 1 (`secret-detector.sh:276`, `$VAR` trae nombres de env) | **0** |
| B | tal cual | 2 | 0 sintácticos; 2 usos legítimos | **2, aceptados con motivo** |

Cómo se acotó cada uno, sin aflojar el detector:

- **C**: solo `&&` (no `||`), porque `|| true` tras un filtro siempre-cero es una
  rama muerta pero inofensiva, y es el idioma dominante del árbol; solo cuando
  el estado se consume (`&&`, `$?`, condición de `if`/`while`); se excluye el
  filtro que **redirige** (`| tr ... > "$tmp" && mv ...`), porque ahí sí puede
  fallar al escribir y el `&&` significa algo; se prohíbe `$(` en la condición,
  porque `[ -n "$(... | head -1)" ]` usa la *salida*, no el estado.
- **A literal**: 3+ guiones sin comillas. Con 2, `--binary-files=` es un flag
  largo legítimo.
- **A variable**: se sigue un salto — `for VAR in "${ARRAY[@]}"` donde la
  definición de `ARRAY` contiene un literal de 3+ guiones. La conjunción floja
  («mismo archivo») es coincidencia: un cambio en los nombres de env-vars no
  debería obligar a tocar los patrones de secretos.

**Resultado final: 2 marcados sobre 640 archivos, los dos con motivo escrito, 0
sin explicar.** El número que justificaría cablearlo a pre-commit; la decisión
de hacerlo es del operador, no mía.

## La cita no es la ocurrencia

Este repo documenta sus arreglos citando el patrón viejo **textual**, que es lo
correcto. Un detector ingenuo marca justo los comentarios que explican el fix de
la clase que detecta: cuanto mejor documentado el arreglo, más ruidoso el guard.

Me pasó, y ya estaba en el árbol. `scripts/portability-two-way-proof.sh` daba
**3 matches de `grep -oP`: líneas 33, 69 y 72. Las dos primeras son comentarios
que explican por qué se dejó de usar `-oP`.** Solo la 72 es código.

```
matches en el texto crudo: 3 -> lineas [33, 69, 72]
matches solo sobre codigo: 1 -> lineas [72]
```

El verdicto a nivel archivo no cambió (la 72 lo sostiene sola), pero por suerte,
no por diseño: en un archivo que solo documentara el arreglo, el guard habría
inventado una tarea.

**El instrumento se arregla; el código no deja de explicarse.** `_solo_codigo()`
blanquea comentarios de línea entera y comentarios al final de línea (con guarda
de comillas balanceadas), conservando el conteo de líneas. Sigue la misma
distinción que `scripts/audit_killswitch_activation.py` resolvió el 2026-08-19
para *oferta vs cita de una oferta*, y reusa su forma de clasificación por
línea. **No** toca cuerpos de heredoc: ahí puede haber shell que se ejecuta, y
un falso negativo es el error caro de los dos. Medidos 0 casos de cita dentro de
heredoc sobre 640 archivos.

Se fijó con 3 fixtures `CITAS` chequeados **cruzados**: ningún detector puede
marcar la cita de otro, incluidos los dos ejemplos que llegaron desde el otro
repo (`# D4: \`... | wc -l\` used to fold`).

Nota de método, porque me mordió dos veces en la misma tarea: la primera
verificación de esto **dio mal** —reportó que el match sobreviviente era la
línea 33, un comentario— y la explicación no era que el stripping fallara, sino
que mi sonda calculaba los números de línea con los offsets del texto *crudo*
sobre el texto *limpio*. La sonda medía otra cosa. Es el mismo error que el
`grep`-shim del principio y que el `re.M` faltante: tres veces en una tarea, el
instrumento antes que el hallazgo.

## Los dos controles (tres, en realidad)

Los tres corren en la **misma invocación** que el veredicto.

1. **Positivo en fixture** (`test_control_positivo_y_negativo_en_fixtures`):
   11 fixtures que el detector *tiene* que marcar. Sin esto, un detector que no
   matchea nunca pasa todos los demás tests en verde.
2. **Negativo con la misma forma sintáctica** (mismo test): 15 fixtures que
   *no* debe marcar. **Cada uno salió de un falso positivo medido sobre el
   árbol**, no de la imaginación: `--binary-files=without-match`,
   `v=$(cmd | head -1 || true)`, `[ -n "$(find ... | head -1)" ]`,
   `printf ... | tr ... > "$tmp" && mv ...`, el ciclo-coincidencia de
   `secret-detector.sh:276`. Sin ellos, un guard que marca todo pasa el control
   positivo — que es exactamente cómo se ve un gate que apagan a las 48 horas.
3. **Positivo sembrado en el corpus real**
   (`test_control_positivo_sembrado_en_el_corpus_real`): planta los 11 positivos
   como archivos `.sh` dentro de `scripts/` y corre **el mismo barrido** que
   produce el veredicto, exigiendo que los encuentre a todos. La única
   diferencia con el barrido del gate es un flag en `git ls-files`; el filtrado
   por sufijo, el shebang, la exclusión de symlinks y el escaneo son el mismo
   camino. Limpia con `try/finally`.

El (3) es el que encontró el `re.M` faltante. Sin él, este informe habría dicho
«sub-forma 4 cubierta, 0 hallazgos» sobre un detector que solo miraba la primera
línea de cada archivo — un `rc=0` con más decimales.

Anti-colchón, con igualdad exacta, sobre `DEUDA ∪ ACEPTADO`:
`test_el_baseline_no_lista_archivos_ya_arreglados` (una entrada que dejó de
violar es un supresor que no suprime nada) y
`test_el_baseline_no_lista_archivos_inexistentes`.

## Lo que encontró en el árbol

**Un defecto vivo, arreglado.** `scripts/deps-update.sh:506`:

```sh
if ! docker pull "$image" 2>&1 | tail -3; then
  _yellow "  WARNING: docker pull failed for $image — manual review required"
```

`tail` sale 0 siempre, el `!` lo invierte a falso, y el WARNING —más el
`continue` que evitaba comparar digests basura— **era inalcanzable**. Un pull
fallado seguía como exitoso. Contrafáctico medido:

```
$ sh -c 'if ! docker-inexistente pull x 2>&1 | tail -3; then echo ALCANZADA; else echo "reporto exito sobre un fallo"; fi'
version vieja: reporto exito sobre un fallo
$ sh -c 'if OUT=$(docker-inexistente pull x 2>&1); then echo ok; else echo RAMA_DE_ERROR_ALCANZADA; fi'
RAMA DE ERROR ALCANZADA
```

**Un defecto en el propio gate, arreglado.** `_B_PCRE_FLAG` y `_B_ERE_CMD` sin
`re.M`. Ver el resumen.

**Dos aceptados, con motivo escrito en el código:**

- `scripts/portability-two-way-proof.sh` — canario deliberado: *prueba* si
  `grep -oP` anda en este userland para que el día que ande alguien se entere.
  Marcarlo sería marcar el termómetro por tener fiebre.
- `packages/quality-gates/hooks/clarification-interceptor.sh` — tiene el
  fallback `sed` escrito dos líneas más abajo. El detector no lo ve porque
  tendría que seguir la variable; la discriminación se escribe en el baseline en
  vez de aflojar el patrón.

`DEUDA` quedó **vacío**, y no es un colchón al revés: el único defecto vivo se
arregló en el mismo commit.

## Lo que NO hice y por qué

- **No lo cableé** a hook ni a pre-commit. Tengo el número que lo justificaría
  (2/640, ambos explicados), pero registrarlo toca configuración protegida y es
  decisión del operador. Hoy corre como test de la suite.
- **No corrí la suite completa** — hay una corrida de 24.229 tests en curso.
  Corrí solo este archivo: 6 passed en 2,16 s.
- **No toqué la sub-forma 3** aunque la verifiqué y el defecto es real: el stage
  opt-in que la tiene no está en mi alcance y detectarla bien pide análisis de
  flujo, no una regex.
- **No extendí el corpus a Python.** `subprocess.run([...])` no pasa por un
  shell y no tiene la ambigüedad de la sub-forma 1; meterlo habría inflado el
  corpus sin agregar señal.
- **No unifiqué esto con `test_flock_has_a_portable_fallback.py`** aunque son
  primos. Son dos conceptos distintos (portabilidad de un binario vs. defensa
  inalcanzable) y un cambio en uno no debería obligar a tocar el otro.

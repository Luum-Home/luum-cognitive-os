# Gatear la clase: kill-switches que ofrecen una salida inejecutable

Fecha: 2026-08-19 · Commit: `177caef0b` · Reproducir: `python3 scripts/audit_killswitch_activation.py`

## Resumen ejecutivo

El censo bien hecho (`rglob` sobre `hooks/**/*.sh`, symlinks resueltos, `_lib` y
`_archived` incluidos) ve **143 ocurrencias** de kill-switch en texto de hook. De
esas, el instrumento **puede juzgar 23**; las otras 120 quedan declaradas como
ceguera, no contadas como buenas. De las 23 medibles, **11 mienten** y 12 son
honestas. Al empezar la sesión eran 13 mentiras sobre 22 medibles; dos migraciones
las bajaron a 11.

Los dos números previos median otra cosa. El **54/10/44** salió de un glob de un
solo nivel, ciego a los dos subdirectorios de `hooks/`. El **143/5/77** acertó la
población casi exacta pero metió tres cosas distintas en "sin ruta": mensajes que
ofrecen la forma rota, menciones en prosa que no ofrecen ninguna vía, y código real
del propio hook. Y ninguno separaba las dos poblaciones que la corrección del
orquestador hizo visibles: el prefijo **al lanzar** el arnés sí llega; el prefijo
sobre un comando **de adentro** no.

El gate quedó en `tests/contracts/test_killswitch_activation_is_executable.py`, con
baseline de igualdad exacta y **trece corridas** —cuatro fixtures sintéticos y seis
contra hooks reales en árboles descartables—. Cierra además la deuda declarada de
`4a9c2d4fc`: el caso rojo de `research-compliance-guard` ahora se reproduce.

## Correcciones a las premisas del encargo

1. **«Un prefijo `VAR=1 <comando>` no llega a ningún hook de ningún evento»** —
   incompleto, y el orquestador lo corrigió a mitad de trabajo. Llega cuando el
   comando prefijado es **el lanzamiento del arnés**, que hereda el entorno de su
   shell padre. La afirmación vale solo desde adentro de una sesión ya lanzada. El
   clasificador distingue las dos formas (`_LAUNCHER_WORDS` vs `_COMMAND_WORDS`) y
   cuenta como honesto al mensaje que ofrece la de arranque. Dato lateral: **ningún
   hook del repo la ofrece**, así que la corrección no movió el número — pero sin
   ella el criterio habría sido correcto por casualidad.

2. **«Hay dos vías legítimas de activación»** — hay **cuatro**. A `export` previo y
   al bloque `env` de la config del arnés se suman el prefijo de arranque (arriba) y
   —leyendo el resolvedor de bypass compartido de `hooks/_lib/`— un archivo de
   bypass bajo `.cognitive-os/runtime/`, que se relee **en cada invocación**. Esa
   cuarta importa más que las otras: es escribible a mitad de sesión sin tocar
   `settings.json`, y ya está en producción para toda la familia `cos_bypass_allows`.
   Con ella, `COS_ALLOW_RESET_OVER_WIP` de `destructive-git-blocker` **tenía** vía
   ejecutable; lo que estaba mal era el mensaje, que apuntaba a la otra.

3. **«`research-compliance-guard` adoptó el patrón de `protected-config-write-guard`»**
   — adoptó una versión más débil. El canónico ancla el token a posición de prefijo
   (`(^|[;&|(]|&&|\|\|)[[:space:]]*VAR=1[[:space:]]`) y su cabecera explica por qué:
   el match en cualquier lugar del texto **se auto-concede**, porque un comando que
   solo menciona el token al escribir una nota lo contiene sin que sea una
   asignación. `4a9c2d4fc` usó `[[ "$CMD" == *"VAR=1"* ]]`, el match ancho. No lo
   cambié —ver «Lo que NO hice»— pero la migración que sí hice usa el ancla, y tiene
   una corrida dedicada a ese caso exacto.

4. **«De los kill-switches del repo, solo un puñado compensa leyendo del texto»** —
   cierto en dirección, engañoso en denominador. Compensar leyendo del texto solo
   hace falta cuando el mensaje promete el prefijo de adentro. De 143 ocurrencias,
   **eso pasa 23 veces**; las otras 120 no necesitan compensación alguna. Contar
   «5 de 143» hacía parecer un incendio donde hay un charco identificable.

5. **Sobre el sexto caso (`cleanup_on_exit`)**: entra en la misma pregunta pero no en
   el mismo instrumento. Detalle en «Lo que NO hice y por qué».

## El censo bien hecho

```
$ python3 scripts/audit_killswitch_activation.py
poblacion: 143  medibles: 23
  mentira    11 de 23 medibles (47.8%), 120 fuera de alcance
  honesto    12 de 23 medibles (52.2%), 120 fuera de alcance
fuera del alcance del instrumento:
  ambiguo: nombra la variable sin nombrar vía   99
  código, no mensaje                            21
```

Tres decisiones de método, y por qué cada una:

- **`rglob`, no `glob`.** `hooks/*.sh` ve 254 archivos; `hooks/**/*.sh` ve 288, que
  son 286 tras resolver symlinks. Los 34 de diferencia viven en `_lib/` y
  `_archived/`, y `_lib/` es justamente donde está el resolvedor de bypass
  compartido — el archivo que cambió el criterio.
- **La ocurrencia es la unidad, el archivo no.** Un hook puede ofrecer dos variables
  distintas, una honesta y una mentirosa (`clean-room-ast-similarity-gate` ofrece dos
  y miente en las dos; `adoption-freeze-gate` igual). Un veredicto por archivo
  perdería eso, que es la trampa que documenta `scripts/home-path-family-mutation-check.sh`.
- **La ceguera se declara, no se reparte.** 120 de 143 no son ni buenas ni malas:
  son casos que un lector de texto bash no puede juzgar. Van a `blind` del `Census`,
  y el script imprime el aviso de que un cero ahí no es un resultado.

Ceguera adicional, dicha porque hace falta para leer el número: **el instrumento no
distingue una oferta de la cita de una oferta**. Un comentario que documenta la forma
rota cuenta como mentira. Cuenta de más, no de menos — fail-closed a propósito — y
por eso el comentario nuevo en `destructive-git-blocker.sh` evita el literal viejo.

## Mentira vs vía legítima: el criterio

La pregunta no es «¿lee del texto?». Es **¿el mensaje ofrece una salida que quien lo
lee puede ejecutar?**

| Lo que el mensaje ofrece | ¿Ejecutable desde adentro? | Veredicto |
|---|---|---|
| `export VAR=1` antes de lanzar | no, pero no lo promete | honesto |
| `VAR=1 claude` (prefijo al lanzar) | sí, en el arranque | honesto |
| bloque `env` de la config del arnés | sí, al guardar el archivo | honesto |
| archivo de bypass en `.cognitive-os/runtime/` | sí, se relee en cada invocación | honesto |
| `VAR=1 git commit …` y el hook lee el token del texto | sí | honesto |
| `VAR=1 git commit …` y el hook solo lee del entorno | **no** | **mentira** |
| «override with VAR=1», sin nombrar vía | no se sabe | ambiguo (ceguera) |

`ambiguo` es la categoría que evita el error simétrico. 99 ocurrencias nombran la
variable sin decir cómo activarla. No mienten explícitamente y tampoco alcanzan, pero
convertirlas en rojo obligaría a reescribir 99 mensajes por un defecto que el
instrumento no puede demostrar. Quedan contadas y fuera del gate.

## El gate y sus tres corridas

`tests/contracts/test_killswitch_activation_is_executable.py`, 13 corridas, `0.9 s`.

Baseline de **igualdad exacta** por `<hook>::<VARIABLE>` — la línea se mueve con
cualquier edición de arriba, la variable no — con las tres aserciones que usa este
repo, más una cuarta contra el paso por vacuidad:

- no absorbe una mentira nueva (`… - KNOWN_UNREACHABLE_KILLSWITCHES == ∅`);
- no lista una ya migrada (`KNOWN_… - mentiras == ∅`);
- no tiene asientos fantasma (entradas cuyo hook o variable ya no existe);
- el censo ve ≥ 50 hooks, o el `rglob` está roto y el gate pasa por ceguera.

**Las tres direcciones, más el control que las hace interpretables.** Un gate que
rojea todo también pasa el caso rojo; sin los controles nadie se entera.

```
$ .venv/bin/python3 -m pytest tests/contracts/test_killswitch_activation_is_executable.py -q -k clasificador -v
test_el_clasificador_distingue_las_cuatro_formas[mentira-…-mentira]         PASSED
test_el_clasificador_distingue_las_cuatro_formas[honesto_texto-…-honesto]   PASSED
test_el_clasificador_distingue_las_cuatro_formas[honesto_export-…-honesto]  PASSED
test_el_clasificador_distingue_las_cuatro_formas[ambiguo-…-ambiguo]         PASSED
```

1. **Rojo** — ofrece `VAR=1 git commit` y solo lee del entorno → `mentira`.
2. **Verde por compensación** — el mismo mensaje, más el `grep` anclado sobre
   `.tool_input.command` → `honesto`.
3. **Verde por vía legítima** — ofrece `export VAR=1 before launching` y solo lee del
   entorno → `honesto`, porque no miente.
4. **Control** — «Override only with VAR=1 and a written reason» → `ambiguo`, ni rojo
   ni verde. Sin este caso, «mentira» sería sinónimo de «menciona la variable».

**Y seis corridas contra hooks reales**, en árboles descartables bajo `$TMPDIR`, sin
tocar el índice ni el estado de este repo:

```
test_research_guard_bloquea_sin_el_token                 PASSED   (exit 2)
test_research_guard_acepta_el_token_desde_el_texto       PASSED   (exit 0)
test_symlink_guard_bloquea_el_self_loop                  PASSED   (exit 2)
test_symlink_guard_acepta_el_token_como_prefijo          PASSED   (exit 0)
test_symlink_guard_no_se_auto_concede_por_mencion        PASSED   (exit 2)
```

Las dos primeras **cierran la deuda declarada en `4a9c2d4fc`**, que dejó escrito
«arreglado por inspección, no verificado» porque no consiguió reproducir un caso
rojo. Se reproduce con un repo git descartable y un doc que menciona una fuente sin
licencia sin declarar frontera clean-room.

La quinta es la que separa el arreglo correcto del match ancho: un comando que
escribe una nota mencionando el token **no** autoriza la mutación que la nota
describe. Con el match en cualquier lugar del texto, sí lo haría.

Notas de método sobre las fixtures, aprendidas rompiéndolas:

- El primer intento del control de `symlink-mutation-guard` usó el par
  `lib/harness_adapter` del incidente 2026-05-02. **Devolvió 0**: ese par ya no existe
  en el árbol. El verde de al lado seguía pasando y no significaba nada. Ahora la
  topología se construye en `tmp_path`.
- La primera versión del clasificador absolvía a `destructive-git-blocker` porque el
  `$COMMAND` que el mensaje **imprime** se leía como el `$COMMAND` que lo inspecciona.
  Una promesa no puede ser su propia prueba: la búsqueda de compensación excluye las
  líneas de mensaje.

## Cuántos mienten hoy

11 ocurrencias, 10 pares `hook::variable`, todas en el baseline:

| Hook | Variable |
|---|---|
| `adoption-freeze-gate.sh` | `COS_ALLOW_ADOPTION_FREEZE_BYPASS`, `COS_ALLOW_FREEZE_TOGGLE` |
| `attribution-completeness-validator.sh` | `COS_ALLOW_INCOMPLETE_ATTRIBUTION` |
| `clean-room-ast-similarity-gate.sh` | `COS_ALLOW_AST_SIMILARITY`, `COS_ALLOW_CLEAN_ROOM_BYPASS` |
| `external-cache-content-leak.sh` | `COS_ALLOW_VERBATIM_LEAK` |
| `git-commit-scope-guard.sh` | `COS_BYPASS_COMMIT_GUARD` (dos mensajes) |
| `legal-review-required-on-runtime-import.sh` | `COS_ALLOW_PRE_LEGAL_REVIEW_IMPORT` |
| `lib-symlink-divergence-detector.sh` | `COS_ALLOW_LIB_DIVERGENCE` |
| `spdx-header-required.sh` | `COS_ALLOW_MISSING_SPDX` |

**`git-commit-scope-guard.sh` es peor que los otros nueve y merece decirse aparte:**
`COS_BYPASS_COMMIT_GUARD` aparece tres veces en el archivo —una en la cabecera y dos
en mensajes de bloqueo— y **el hook no la lee nunca**, ni del entorno ni del texto.
No es un kill-switch con vía rota: es un kill-switch que no existe.

```
$ grep -n 'COS_BYPASS_COMMIT_GUARD' hooks/git-commit-scope-guard.sh
22:#   COS_BYPASS_COMMIT_GUARD=1     — emergency bypass (logged)
327:    echo "  COS_BYPASS_COMMIT_GUARD=1 git commit --amend --no-edit"
351:  COS_BYPASS_COMMIT_GUARD=1 git commit -m "..."
```

Las dos migradas hoy, una de cada forma para que el gate demuestre que baja y que no
fuerza una sola solución:

- **`symlink-mutation-guard.sh`** — adoptó la lectura del texto con el ancla de
  prefijo. Ensancha la superficie de bypass a cambio de que el mensaje sea cierto; se
  eligió este porque es un guard de topología, no de seguridad.
- **`destructive-git-blocker.sh`** — **no se tocó el guard, solo el mensaje.** La vía
  ejecutable ya existía; el mensaje apuntaba a la que no funciona. Cero ensanche.

## Lo que NO hice y por qué

- **No migré los 10 restantes.** El encargo pedía gatear la clase, no vaciarla, y
  cinco de ellos (`clean-room-*`, `legal-review-*`, `external-cache-*`) son guardas de
  licencia y limpieza de sala: agregarles lectura desde el texto ensancha una
  superficie de bypass legal, y esa es una decisión del operador, no de un agente.
  Para esos cinco la migración correcta es probablemente **cambiar el mensaje**, no el
  guard, como se hizo con `destructive-git-blocker`.

- **No arreglé `git-commit-scope-guard`**, aunque su kill-switch directamente no
  existe. Darle implementación es agregar un bypass nuevo a la guarda de commits bajo
  sesiones concurrentes — exactamente el mecanismo que hoy está protegiendo el trabajo
  de los otros agentes. Borrar el mensaje sin darle vía real es el verde barato
  prohibido. Queda como el hallazgo de mayor prioridad para triage del operador.

- **No cambié el match ancho de `research-compliance-guard`** por el anclado, pese a
  la corrección 3. Es un cambio de comportamiento en una guarda de cumplimiento que
  otro commit tocó hoy; hacerlo en paralelo con su autor es cómo se pisan dos
  sesiones. Queda documentado acá con la corrida que lo demostraría.

- **No metí `cleanup_on_exit` en este gate.** Es la misma mentira —una perilla que el
  operador puede girar y que no está conectada— pero con otro vehículo, y la pregunta
  que la detecta necesita otro instrumento: cruzar **claves de config declaradas**
  contra **sitios de lectura en el código**, no leer mensajes de bash. Meterla acá
  habría requerido dos clasificadores bajo un baseline, y un baseline que mezcla dos
  poblaciones no se puede auditar. Además el encargo prohíbe explícitamente tocar
  `hooks/session-cleanup.sh`. **Clase aparte, gate aparte** — y vale la pena: un
  archivo YAML que el operador edita y que no se lee es peor que una env var
  inalcanzable, porque el archivo existe y se ve bien.

- **No registré el gate en CI.** Vive en `tests/contracts/`, que es donde CI ya
  recoge esta familia; no hice ningún cambio de configuración de pipelines.

- **No toqué `hooks/spdx-header-required.sh`** aunque está en el baseline: otra sesión
  lo tenía modificado en el árbol de trabajo (`git status` al empezar), y editar el
  archivo de otro es cómo se pierde su trabajo.

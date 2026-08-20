# El verde que era del checkout

Fecha: 2026-08-20
Entregable: `scripts/checkout_parity.py`

## Resumen ejecutivo

La clase es un gate que pasa por lo que hay en esta máquina, no por lo que dice
el código. No tiene firma textual, así que no hay nada que grepear: se mide por
diferencia. El procedimiento corre el mismo gate dos veces, una sobre el árbol
de trabajo y otra sobre un árbol que sólo tiene lo que viaja, y compara
veredictos. Quedó como `scripts/checkout_parity.py`, con el qué correr por
parámetro. Lo vi ponerse rojo dos veces a propósito antes de creerle: un control
sintético sin tocar nada, y un control sembrado en un gate real, con el sha256
del archivo idéntico antes y después. De las dos instancias conocidas, la de
`wiring_validator` la detecta (422 contra 461 componentes no cableados sobre el
mismo commit); la de `agent-service` **no es de esta clase**: falla igual en los
dos árboles, así que el veredicto correcto es que no hay diferencia.

## Correcciones a las premisas del encargo

1. **`git worktree` no está bloqueado en la práctica.** El encargo lo daba por
   bloqueado (ADR-055b). `git worktree list` corre sin problema y devuelve 15
   worktrees vivos, incluido uno del propio scratchpad de esta sesión. Igual usé
   `git archive`, pero por un motivo distinto del que decía el encargo: un
   worktree comparte el object store y, sobre todo, comparte las reglas de
   ignore y puede arrastrar archivos no trackeados. `git archive` es el modelo
   honesto de un clon fresco. La conclusión del encargo era correcta; el
   fundamento que daba, no.

2. **`git archive HEAD` solo no alcanza, y esto rompía el encargo tal como
   estaba escrito.** `HEAD` es el último *commit*: todo lo no commiteado es
   invisible para el árbol limpio. Con eso no se puede sembrar un control sin
   commitear la semilla, y peor, no se puede contestar la pregunta justo antes
   de commitear, que es cuando más sirve. Agregué `--worktree`, que arma el
   árbol limpio con el contenido **actual** de los archivos trackeados y saca
   sólo lo que no viaja.

3. **La instancia de `packages/agent-service` no es de esta clase.** El encargo
   decía que sobre árbol de solo-trackeados da `ModuleNotFoundError: No module
   named 'httpx'` y que "la diferencia de entorno persiste, tiene que aparecer".
   Aparece el error, sí, pero **idéntico en los dos árboles** (exit 4 y 4). El
   `httpx` que falta es del venv, no del árbol. El procedimiento dice
   `PARITY_OK` y tiene razón: el gate está rojo en los dos lados por igual. Si
   lo hubiera forzado a dar `PARITY_DIFF` para cumplir con el encargo, habría
   sido exactamente el verde barato al revés.

4. **`wiring_validator` pre-fix no reportaba cero.** El encargo dice "reportaba
   **cero** componentes no cableados". Medido sobre `6f7bede8e^`: 461 con el
   archivo local presente y 422 sin él. La instancia es real y la diferencia
   también, pero el número del encargo no es el que sale.

5. **`.claude/settings.local.json` sigue existiendo** (27702 bytes, 10 de
   junio). El encargo lo trataba como algo del pasado. Está, y sobre el código
   pre-fix sigue ganando como driver.

6. **Un peligro que el encargo no menciona y que casi invalida todo.** El venv
   tiene un `.pth` de instalación editable cuyo contenido es la ruta absoluta
   del checkout real. O sea: site-packages agrega el árbol sucio a `sys.path`,
   también durante la corrida limpia. Sin corregirlo, el árbol limpio importa
   `cos_lib` del sucio y el procedimiento miente. Se arregla fijando
   `PYTHONPATH` con el árbol bajo prueba adelante, porque `PYTHONPATH` se
   consulta antes que los `.pth`. Es primo hermano de la instancia 4 del
   encargo (el subproceso hereda), pero por herencia de `sys.path`, no de env.

7. **`git ls-files` lista los submódulos como si fueran archivos.** El primer
   intento de `--worktree` explotó con `IsADirectoryError` sobre un gitlink.
   `git archive` los omite, así que `--worktree` también tiene que omitirlos o
   los dos modos dejan de producir el mismo árbol.

8. **La advertencia sobre symlinks no aplicó acá.** `readlink -f
   tests/audit/test_bash_naming.py` devuelve la misma ruta: no es symlink.

## Por qué procedimiento y no detector

Comparto la conclusión de la otra sesión y la refuerzo con lo que salió hoy. Un
detector estático busca una declaración, y de las instancias medidas ninguna
declara nada:

- un `.gitignore` con patrón pelado que esconde un `conftest.py` no dice en
  ningún lado "acá hay un test que no viaja";
- un validador que elige un archivo gitignoreado como driver está eligiendo bien
  según su propio código, el bug es cuál archivo existe en esta máquina;
- un venv con un `.pth` apuntando al checkout real es un archivo generado por
  `pip`, no código del repo.

Las tres son propiedades del **estado del disco**, no del texto. Lo único que
las hace visibles a todas con el mismo instrumento es correr el gate dos veces y
restar. Por eso el entregable acepta el gate por parámetro: no sabe nada de la
causa, sólo mide la diferencia.

## El sujeto que elegí y por qué

`tests/audit/test_bash_naming.py` y `tests/audit/test_python_naming.py`, más
adelante `tests/audit/test_doc_paths_tracked.py` y el propio
`cos_lib/wiring_validator.py`.

Los elegí por tres razones. Corren en décimas de segundo, así que no le sacan
CPU a la corrida completa que está en curso. Caminan el **filesystem** en vez
del índice, que es justo la familia donde el árbol sucio y el limpio tienen por
qué diferir. Y son chicos (64 y 72 líneas), así que cuando aparece una
diferencia se puede explicar de dónde salió en vez de quedarse con el exit code.

No corrí la suite entera en los dos árboles. Tardaría horas y competiría con la
corrida en curso. Lo que se entrega es el procedimiento, no la auditoría de hoy.

## El control positivo sembrado, y el rojo que produjo

Dos controles, porque uno solo no me alcanzaba.

**Control sintético, sin tocar nada.** Gate: `/bin/sh -c 'test -f
.venv/pyvenv.cfg'`. El venv está gitignoreado, así que existe en el árbol de
trabajo y no en el que viaja.

```
working tree:  exit 0
tracked tree:  exit 1
PARITY_DIFF
```

**Control sembrado en un gate real.** Le agregué a
`tests/audit/test_bash_naming.py` un test que depende de un artefacto que no
viaja:

```python
def test_parity_seeded_control_depends_on_untracked_venv():
    from pathlib import Path
    assert (Path.cwd() / ".venv" / "pyvenv.cfg").is_file()
```

Sembrar, medir y restaurar pasó en un solo comando, para que la ventana de
exposición sobre el checkout compartido durara segundos:

```
working tree:  4 passed                       (verde)
tracked tree:  1 failed, 3 passed             (rojo)
PARITY_DIFF
```

Restauración verificada:

```
SHA256 BEFORE: 571ac1ae2fe8345e3683e89ab03efd714bc7008ad4b19bc1c1a937186f7365e3
SHA256 AFTER:  571ac1ae2fe8345e3683e89ab03efd714bc7008ad4b19bc1c1a937186f7365e3
RESTORE: byte-identical OK
git status --porcelain -- tests/audit/test_bash_naming.py   (vacío)
```

Recién con ese rojo demostrado un `PARITY_OK` significa algo.

## Las dos instancias conocidas, verificadas

**`cos_lib/wiring_validator.py`: la detecta.** El fix es `6f7bede8e`. La prueba
retrospectiva no se puede hacer con `--ref` (ver más abajo por qué), así que
materialicé el árbol pre-fix dos veces y le agregué a una copia el archivo
gitignoreado:

```
árbol tal como viaja        -> driver: .claude/settings.json        | unwired: 422
mismo árbol + archivo local -> driver: .claude/settings.local.json  | unwired: 461
```

Dos veredictos distintos sobre el mismo commit, con la diferencia enteramente
del lado del disco. El procedimiento lo habría marcado antes del arreglo.

Verificado que el archivo no viaja:
`git check-ignore -v .claude/settings.local.json` da `.gitignore:74`, y
`git ls-files --error-unmatch` no lo encuentra.

**`packages/agent-service`: no es de esta clase.** Ver corrección 3. El
`ModuleNotFoundError: No module named 'httpx'` sale igual en los dos árboles,
con el mismo exit 4. Es una dependencia que falta en el venv, no algo que el
árbol de trabajo tenga y el limpio no. El procedimiento contesta `PARITY_OK` y
es la respuesta correcta.

## Diferencias encontradas hoy

- **El `.pth` de instalación editable filtra el checkout real a `sys.path`.**
  Encontrado midiendo, no leyendo. Es la diferencia más peligrosa de las de hoy
  porque no se ve: hace que el árbol limpio importe el sucio y el procedimiento
  entero dé verdes falsos. Mitigado dentro del script.

- **`wiring_validator` en HEAD: mismo exit code, distinto número** (423 en el
  árbol de trabajo contra 422 en el limpio). La diferencia es un archivo python
  de primera parte que todavía no está commiteado, contado como no cableado.
  Deja a la vista un límite del procedimiento: compara **veredictos**, y un gate
  que informa un número sin afirmarlo puede correrse sin cambiar su exit code.
  Un gate que sólo reporta no es un gate.

- **Una corrida no reproducible.** En la primera medición de los gates de
  naming, el árbol de trabajo dio exit 1 y el limpio exit 0. Segundos después,
  con el mismo comando, los dos dieron 0 y no volvió a pasar. La explicación más
  probable es que hay otras dos sesiones escribiendo en este mismo checkout y
  algo estaba a medio escribir. No lo pude reproducir, así que lo dejo anotado
  como observación, no como hallazgo.

- Sin diferencias: `tests/audit/test_doc_paths_tracked.py`, los dos gates de
  naming, `packages/agent-service`.

## Lo que NO hice y por qué

- **No corrí la suite completa en los dos árboles.** Hay una corrida de 24.229
  tests en curso. Tardaría horas y le sacaría CPU.
- **No creé `.claude/settings.local.json` para reproducir la instancia 2 en
  vivo.** Ese archivo lo lee el harness: crearlo o modificarlo le cambia el
  comportamiento a las sesiones concurrentes. Reproduje la divergencia en una
  copia descartable del árbol pre-fix, que da la misma evidencia sin tocar el
  checkout compartido.
- **No hice un detector estático.** Ver la sección correspondiente.
- **No agregué el procedimiento a ningún gate de CI.** Elegir qué gates se
  auditan y con qué frecuencia es una decisión del operador, y meterlo solo en
  CI mientras hay una corrida grande en curso sería un cambio de blast radius
  alto sin haberlo conversado.
- **No pude hacer la retrospectiva con `--ref`,** y quedó documentado en el
  script: `--ref` cambia sólo el lado limpio, el lado sucio es siempre el árbol
  de trabajo actual con el código que tenés hoy. Para preguntar si un bug ya
  arreglado se habría detectado hay que materializar el ref viejo dos veces, que
  es lo que hice a mano.
- **No toqué** `hooks/orchestrator-skill-invocation-gate.sh`,
  `hooks/skill-router-prompt-suggest.sh` ni `cos_lib/skill_router.py`.

## Cómo se usa

```bash
# ¿el verde de este gate sobrevive a un clon limpio?
python3 scripts/checkout_parity.py --worktree -- .venv/bin/python -m pytest tests/audit -q

# ¿lo que ya está commiteado se sostiene solo?
python3 scripts/checkout_parity.py --ref HEAD -- ./scripts/algun-gate.sh
```

Exit codes: `0` los dos árboles coinciden, `1` difieren (el verde era del
checkout), `2` falló el procedimiento. Read-only sobre el repo: sólo escribe en
un directorio temporal que borra al salir.

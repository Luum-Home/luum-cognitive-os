<!-- SCOPE: os-only -->
# La ceguera de `hook_exercise_audit.py`: abrir la caja de los 53

Fecha: 2026-08-19 · Instrumento: `scripts/hook_exercise_audit.py` ·
Base de comparacion: commit `e168f2b1a` (la version que declaro la ceguera).

## Resumen ejecutivo

| cubeta | antes (`e168f2b1a`) | despues |
|---|---:|---:|
| EXERCISED | 141 | **181** |
| NAMED_ONLY | 0 | **2** |
| NO_TEST | 5 | 5 |
| UNCLASSIFIABLE (ceguera) | 54 — 27,00% | **12 — 6,00%** |

Las 54 cajas ciegas eran **una sola causa** —el literal ligado a un nombre y el
uso atras de ese nombre— con tres desenlaces distintos: 40 se ejercitan de
verdad, 2 son menciones, 12 no se pueden decidir sin inventar. Ningun hook
bajo de nivel; los 141 EXERCISED previos siguen EXERCISED.

## Correcciones a las premisas del encargo

1. **No eran 53 sino 54, y el `NO_TEST` no era 6 sino 5.** No lo movio mi
   cambio: el corpus se movio mientras trabajaba. La sesion orquestadora
   aterrizo `tests/hooks/test_post_git_orphan_notifier.py` (entre otros
   `tests/hooks/test_*.py` sin trackear), lo que saco a `post-git-orphan-notifier`
   de `NO_TEST` y lo metio en la caja de la ceguera. Por eso el antes/despues de
   este informe **no** usa el numero del encargo: se corrieron las dos tecnicas
   back-to-back sobre el mismo arbol.

   ```bash
   git show HEAD:scripts/hook_exercise_audit.py > scripts/zz_hea_before_tmp.py
   .venv/bin/python3 scripts/zz_hea_before_tmp.py --json > before_pinned.json
   .venv/bin/python3 scripts/hook_exercise_audit.py  --json > after.json
   rm scripts/zz_hea_before_tmp.py
   ```

2. **El error que aparecio fue el contrario al que el encargo vigilaba.** El
   encargo prohibia inventar `EXERCISED`; lo que estaba roto era un **falso
   `NAMED_ONLY`**: `for hook in ("hooks/review-spawner.sh", ...): run_hook(hook, {})`
   (`tests/unit/test_projected_hook_gap_behaviors.py:84`) reportaba mencion vacia
   sobre un hook que el test **corre**. El bug ya estaba en `e168f2b1a`, tapado
   por la precedencia `UNCLASSIFIABLE > NAMED_ONLY`. Un falso `NAMED_ONLY` miente
   igual que un falso `EXERCISED`, solo que hacia el otro lado, y la primera
   version de mi extension lo dejo salir a la superficie antes de arreglarlo.

3. **`COMMIT_BATTERY` no era el patron dominante.** La advertencia del autor
   ("muestreo uno y no reviso los otros 52") era correcta como advertencia y
   equivocada como diagnostico: esa forma explica **10 de 54** (18,5%). La
   dominante es `HOOK = ROOT / "hooks/x.sh"` + `subprocess.run(["bash", str(HOOK)])`,
   **32 de 54** (59%).

4. **Tres de las cinco causas conjeturadas tienen cero casos.** No hay
   construccion dinamica con f-string, no hay helper compartido `_run_hook(name)`
   que reciba el nombre de otro lado, y no hay archivos que no parseen (el propio
   reporte ya lo decia en la linea de fuentes: `1291 archivos (0 no parsean)`).
   La parametrizacion existe pero es marginal: 1 caso.

5. **Una promocion queda con evidencia debil, y no la escondo.**
   `reaper-daemon-launcher` pasa a `EXERCISED` por
   `tests/unit/test_primitive_duplication_audit.py:79`, donde
   `source = tmp_path / "hooks/reaper-daemon-launcher.sh"` es el **nombre de un
   fixture sintetico**, no el hook. Es fiel a la definicion declarada del script
   ("el nombre pasado como argumento de un Call", con el sesgo optimista de
   `Path("hooks/x.sh")` ya escrito en su docstring), y la tecnica vieja habria
   dicho lo mismo con el literal inline. Es limite de la **definicion**, no de la
   extension. Mismo caso, por la via del needle-substring:
   `skill-md-routing-validator` se acredita con
   `metrics_path = tmp/"metrics"/"skill-md-routing-validator.jsonl"`.

## Los 53 (54), agrupados por causa

Causa raiz unica: **indireccion por nombre**. Ninguna de las otras cuatro causas
conjeturadas aparece. El corte de abajo es por la **forma del binding** y por lo
que la extension pudo afirmar.

| forma en el codigo | n | desenlace | por que la tecnica vieja no podia |
|---|---:|---|---|
| `HOOK = ROOT / "hooks/x.sh"` … `run(["bash", str(HOOK)])` | 32 | EXERCISED | el literal esta en un `BinOp`, no en `Call.args`; el `Call` esta 40 lineas mas abajo detras del nombre |
| coleccion constante alimentando un `Call` (`parametrize`, `run`, rollup) | 7 | EXERCISED | mismo salto, con la coleccion entera como argumento |
| coleccion **anonima** en el `for` (`for h in ("hooks/x.sh",): run_hook(h)`) | 1 | EXERCISED | no hay nombre de modulo que seguir: la coleccion vive en `For.iter` |
| constante solo comparada / receptora (`assert BAT <= got`, `X.issubset(y)`) | 2 | NAMED_ONLY | el nombre se lee, pero ningun uso lo pasa a nada |
| **alias**: el valor se muda a otro nombre o sale por un subscript | 12 | sigue ciego | seguirlo requiere analisis de flujo entre sentencias |
| archivo que no parsea | 0 | — | no hay ninguno en el corpus |
| f-string / concatenacion dinamica | 0 | — | no hay ninguno |
| helper compartido que recibe el nombre de afuera | 0 | — | no hay ninguno |

Comando que produce el corte (lee `before_pinned.json` + la corrida nueva, no
recuenta a mano):
`.venv/bin/python3 scripts/hook_exercise_audit.py --json` y comparacion de la
clave `hooks[].level` contra la corrida pinneada de `e168f2b1a`.

## Que tecnica agregue

`_NameFlow` en `scripts/hook_exercise_audit.py`: **seguimiento de un salto del
nombre al que esta ligado el literal**. Para cada lectura de un nombre camina
hacia arriba por el arbol hasta un nodo que decida, y clasifica el nombre en:

- `ARG` — alguna lectura entra como **argumento** de un `Call` (nunca en `func`).
  El literal que ese nombre transporta se le esta pasando a algo -> bolsa `call`.
- `TERMINAL` — todas las lecturas mueren en la sentencia que las lee (compare,
  assert, receptor de un metodo). El literal existe y no se le pasa a nada ->
  bolsa `plain`.
- `ESCAPE` — el valor se va por una via que el instrumento no sigue: subscript
  (`CASES[0]`: no se sabe cual), alias (`missing = BAT - got`), `return`,
  desempaquetado, elemento de comprension -> bolsa `indirect`, o sea ceguera.
- `NONE` — nadie lee el nombre. Constante muerta = mencion, no cobertura. Es
  literalmente la regla 3 del encargo, y ya estaba: no la toque.

Hay **un salto de loop**: `for h in CONST: run(h)` resuelve porque la clase de
`h` se calcula y se propaga a `CONST`. Mas alla de `_MAX_HOPS = 3` corta con
ceguera. Las colecciones anonimas en `For.iter` / `comprehension.iter` entran
por el mismo mecanismo (`_binding_targets`), que devuelve `None` —y por lo tanto
ceguera— cuando el target es un desempaquetado.

Costo: la corrida completa sobre 1291 archivos pasa de ~16s a ~22s
(`time .venv/bin/python3 scripts/hook_exercise_audit.py --json`). Las clases de
uso se cachean por nombre dentro de cada archivo.

## Prueba en las dos direcciones

Diez casos sinteticos nuevos en `tests/contracts/test_hook_exercise_audit.py`
(hooks `zz-quokka-*`, mismo estilo que los existentes). Siete deben cambiar de
veredicto; **tres deben seguir ciegos en las dos versiones** — ese grupo es el
freno que impide que la tecnica se vuelva optimista.

**1. Tecnica vieja (`e168f2b1a`) + tests nuevos -> FALLA**

```text
FAILED test_module_constant_passed_to_a_call_is_exercised
FAILED test_constant_list_fed_to_parametrize_is_exercised
FAILED test_constant_iterated_and_run_is_exercised
FAILED test_anonymous_tuple_iterated_and_run_is_exercised
FAILED test_constant_only_compared_is_named_only
FAILED test_constant_used_as_call_receiver_is_named_only
FAILED test_tuple_unpacking_in_the_loop_stays_unclassifiable
7 failed, 3 passed, 23 deselected in 0.13s
```

(el septimo falla porque la version vieja devolvia `NAMED_ONLY` sobre un
desempaquetado que no puede juzgar: tambien es un falso negativo, no ceguera.)

**2. Tecnica nueva + los mismos tests -> PASA**

```text
10 passed, 23 deselected in 0.13s
```

**3. Suite completa del artefacto, sin romper lo existente**

```text
.................................                                        [100%]
33 passed, 1 warning in 83.57s (0:01:23)
```

Los tres que **siguen ciegos en las dos versiones** (pasan en el bloque 1 y en el
bloque 2, con el mismo veredicto `UNCLASSIFIABLE`):
`test_alias_of_a_constant_stays_unclassifiable`,
`test_constant_whose_read_result_is_reassigned_stays_unclassifiable`,
`test_constant_read_only_from_an_unresolved_helper_stays_unclassifiable`.

## La ceguera que queda y por que es irreducible

12 hooks — 6,00% sobre 200, por debajo del umbral de alarma del propio script.
Diez son la misma linea:

```python
# tests/unit/test_bash_hot_path_dispatcher_git_global_opts.py
missing = COMMIT_BATTERY - got
assert not missing, f"{command!r} skipped commit gates: {sorted(missing)}"
```

`attribution-completeness-validator`, `dependency-license-classifier`,
`external-cache-content-leak`, `external-pattern-cleanroom-gate`,
`legal-review-required-on-runtime-import`, `lib-symlink-divergence-detector`,
`pending-truth-staleness-gate`, `pre-commit-content-hash-dedupe`,
`research-to-runtime-firewall`, `spdx-header-required`.

**Seguir el alias seria peor que no seguirlo.** El unico `Call` que toca
`missing` es el `sorted(missing)` del **mensaje del assert**: una extension que
siguiera el alias devolveria `EXERCISED` por un texto de error. Ciego es la
respuesta correcta, y esta clavada en
`test_alias_of_a_constant_stays_unclassifiable`.

Los otros dos:

- `pyrefly-typecheck-advisory` — `hook = HOOK.read_text(encoding="utf-8")`
  (`tests/contracts/test_pyrefly_pilot_radar.py:85`): el contenido se muda a otro
  nombre. Es un grep estatico sobre la fuente del hook, no una corrida, pero
  afirmarlo requeriria seguir `hook` entre sentencias.
- `rule-router-prompt-suggest` — `text = (REPO / rel).read_text(...)` dentro de
  `for rel in REQUIRED_ACCOUNTED_HOOKS`
  (`tests/contracts/test_context_budget_hook_wiring.py:22`): mismo escape, un
  salto mas lejos.

Lo que haria falta para bajar de 12 no es mas AST: es analisis de flujo de datos
entre sentencias con conocimiento de que el mensaje de un assert no cuenta como
uso. Eso ya no es "analisis estatico razonable" sobre 1291 archivos; es otro
instrumento, y sin el la respuesta honesta es **no se**.

## Los NAMED_ONLY que aparecieron

Dos. Los dos verificados a mano, y los dos son informacion real, no ruido:

- **`cos-executor-daemon-launcher`** (`standard`) — dos tests lo nombran y
  ninguno lo corre. `tests/contracts/test_self_install_no_container_spawn.py:82`
  lo mete en `_LAUNCHER_HOOKS`, un set cuyo comentario dice textualmente que
  esos hooks **no se ejecutan** bajo el shim porque desprenden procesos hijos;
  `tests/unit/test_session_start_budget.py:106` solo verifica que este marcado
  `async` en `settings.json`. No es un test malo: es que ninguno de los dos
  pretende correrlo, y hasta hoy eso estaba escondido bajo "no se".

- **`predev-completeness-check`** (`standard`) — unico test,
  `tests/unit/test_codex_guard_layer.py:44`, que arma un set `expected` y lo
  cierra con `assert expected.issubset(scripts)`. Verifica que el hook este
  **listado** en la cadena `pre-agent`; nunca lo invoca.

Ninguno de los dos dispara hallazgo con el criterio actual del script
(`criticality=standard`, no estan en `REQUIRED_BEHAVIOR_COVERAGE`), asi que el
exit code sigue en 0. Quedan como deuda listada, que es exactamente para lo que
existia la cubeta.

Nota de lectura, para que el rotulo no enganie: `NAMED_ONLY` significa "el
nombre no se le pasa a nada", no "el test no sirve". La bateria
`COMMIT_BATTERY` de los 12 ciegos, por ejemplo, es una verificacion de
comportamiento fuerte y aun asi caeria en `NAMED_ONLY` si el alias no la
mandara a ceguera primero. El sesgo conservador esta declarado en el docstring
del script desde el primer commit.

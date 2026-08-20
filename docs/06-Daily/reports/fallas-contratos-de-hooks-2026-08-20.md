# Fallas de contratos de hooks — 2026-08-20

## Resumen ejecutivo

El encargo traía 13 fallas repartidas en 9 archivos. Reproducidas contra HEAD son
**12**: `tests/unit/test_governance_policy_hook_adoption.py` está verde y no aporta
ninguna.

Las tres cubetas, después de correr las mismas 12 contra un árbol armado sólo con
lo que viaja (`git archive HEAD`):

| Cubeta | Cantidad |
|---|---|
| Deuda real (falla igual con el árbol limpio) | **12** |
| Efecto del árbol sucio | **0** |
| Indecidible | **0** |

La hipótesis del árbol sucio era razonable y dio cero. Los 20 archivos sucios de
`hooks/` son todos modificaciones de archivos **rastreados**; no hay ni un
untracked bajo `hooks/`, y los seis hooks que nombran las fallas existen en HEAD.

Arreglé 2 de las 12. Quedan 10, casi todas en territorio de decisión del operador
(manifiestos de clasificación y perfiles de seguridad).

## Correcciones a las premisas del encargo

1. **Son 12, no 13.** `tests/unit/test_governance_policy_hook_adoption.py` pasa
   entero. El resto del reparto por archivo del encargo es correcto.

2. **"Mirá cuántos son de `hooks/`" apuntaba a un confounder que no existe.**
   Los 20 son ` M` sobre archivos rastreados y no hay ningún `??` bajo `hooks/`:

   ```
   git status --porcelain | grep -c '^ M hooks/'   -> 20
   git status --porcelain | grep '^??' | grep hooks/ -> (vacío)
   ```

   Y los seis hooks que aparecen en los mensajes de falla
   (`aci-observation-capture`, `post-git-orphan-notifier`, `rate-limit-drain`,
   `tool-sequence-capture`, `lineage-relaunch-gate`, `session-lineage-record`)
   están todos rastreados en HEAD — `git ls-files --error-unmatch` los encuentra a
   los seis. No son trabajo en vuelo de nadie.

3. **`git worktree`: el encargo tiene razón y el script del repo se contradice.**
   Hay 15 worktrees vivos, verificado con `git worktree list`. Pero el docstring de
   `scripts/checkout_parity.py` afirma lo contrario: *"`git worktree` is blocked in
   this repo (ADR-055b)"*. Es una contradicción de documentación dentro del propio
   instrumento que el encargo me mandó a leer.

4. **La limitación declarada del informe de paridad no es la que me frenó.** El
   informe `el-verde-que-era-del-checkout-2026-08-20.md` declara dos límites: que
   `--ref` cambia sólo el lado limpio (no sirve para retrospectivas) y que un gate
   que informa un número sin afirmarlo puede correrse sin cambiar su exit code.
   Ninguno es específico de pytest. El obstáculo real con pytest —el guard de
   `tests/conftest.py` (ADR-305) que exige `sys.prefix` bajo la raíz del árbol— no
   está documentado en ese informe. Lo resolví sin usar el bypass (ver abajo).

5. **`tests/behavior/test_hook_architecture.py` no sólo lee: escribe.** Su helper
   `_generate_profile()` corre `scripts/set-security-profile.sh`, que **sobrescribe
   `.claude/settings.json`** real, y lo restaura en el `finally`. En un checkout
   compartido con sesiones concurrentes eso es una mutación del plano de control,
   no una lectura. El encargo me previno sobre *leer* un árbol sucio; este test
   *ensucia* el árbol mientras corre.

6. **`hooks/**` protegido: el guard dispara por el texto del comando, no por el
   archivo destino.** Editando `templates/security-profiles/paranoid.json` —que no
   es ruta protegida— el guard bloqueó igual, porque la cadena `hooks/...` viajaba
   dentro del `sed`. El aviso del encargo era correcto pero por un motivo distinto
   al que sugiere.

## Deuda real vs efecto del árbol sucio: cómo lo determiné

Diferencial de veredictos entre el árbol de trabajo y un árbol con sólo lo que
viaja. El árbol limpio se materializa así:

```bash
CT=<tmp>/clean-head
git archive HEAD | tar -x -C "$CT"
```

Dos trampas que había que neutralizar para que la comparación no mintiera:

**1. El `.pth` del install editable.** El venv del repo tiene un `.pth` que mete el
checkout real en `sys.path`. Sin mitigar, el árbol limpio importa el sucio y todo
da verde falso. `PYTHONPATH` se consulta antes que los `.pth`, así que fijar el
árbol bajo prueba adelante alcanza. Verificado, no asumido:

```bash
cd "$CT" && PYTHONPATH="$CT" .venv/bin/python3 -c \
  "import cos_lib; print(cos_lib.__file__.startswith('$CT'))"
# -> True
```

**2. El guard de venv de `tests/conftest.py` (ADR-305).** Exige `sys.prefix` bajo la
raíz del árbol. Un `.venv` simbólico no sirve: el guard resuelve el symlink y
apunta al repo real. **No usé `PYTEST_ALLOW_NONVENV=1`** —ése es el verde barato de
esta familia: apaga el control que garantiza que los dos lados corren el mismo
runtime—. En su lugar construí un venv genuinamente enraizado en el árbol limpio:

```bash
mkdir -p "$CT/.venv"
cp -R "$REPO/.venv/bin" "$CT/.venv/bin"
cp "$REPO/.venv/pyvenv.cfg" "$CT/.venv/pyvenv.cfg"
ln -s "$REPO/.venv/lib/$PYV" "$CT/.venv/lib/$PYV"
```

`sys.prefix` queda en `$CT/.venv` (directorio real, no symlink), `sys.base_prefix`
sigue siendo el intérprete del sistema, y el guard pasa por la razón correcta.

También hay que sacar del entorno las variables de aprobación heredadas
(`COS_ALLOW_PROTECTED_CONFIG_WRITE` entre ellas): el subproceso las hereda y se
termina midiendo un guard que aprueba todo.

Resultado: **12 fallidos en el árbol de trabajo, los mismos 12 en el árbol limpio**,
con los mismos mensajes. Cero divergencias, así que cero de la cubeta "efecto del
árbol sucio" y cero indecidibles.

## Las que arreglé, con sus dos direcciones

### 1. `test_registered_hooks_exist_as_files` — un perfil que registra un archivo borrado

`templates/security-profiles/paranoid.json` registraba
`hooks/rate-limit-protection.sh`, que no existe. No es un olvido de nombre: ese
archivo era un **shim de deprecación de `token-budget-monitor.sh`**, y se borró a
propósito en `4485149b8` ("chore(poda): borrar el shim rate-limit-protection"). El
CHANGELOG lo confirma: *"`rate-limit-protection.sh` reduced to deprecation shim of
`token-budget-monitor.sh`"*. La poda borró el shim y el molde de perfil quedó
atrás. Cualquier proyecto consumidor que aplique el perfil `paranoid` se lleva un
registro que apunta a la nada.

El sucesor ya está en uso en `.claude/settings.json` (línea 380), así que el
reemplazo no es una elección mía.

- **Rojo antes**: `AssertionError: Registered hooks without .sh files in hooks/: rate-limit-protection.sh`
- **Verde después**: `1 passed`
- **Control** (que muestra que no aflojé la aserción): inyecté
  `hooks/zzz-no-existe-control.sh` en el mismo archivo y el test volvió a morder
  —`assert not ['zzz-no-existe-control.sh']`— y después revertí la inyección. El
  test sigue siendo capaz de detectar exactamente lo que detectaba.

Diff: una línea.

### 2. `test_context_hook_emits_pending_messages` — el test certificaba el defecto

Éste es uno de los casos que el encargo anticipaba. El test afirmaba
`out["additionalContext"]` a nivel raíz. Pero el hook
`hooks/agent-message-inbox-context.sh` lleva escrito en un comentario por qué esa
forma está mal:

> Claude Code reads additionalContext ONLY from inside hookSpecificOutput,
> alongside hookEventName. The root-level form is valid JSON, so the host
> parses it, finds no recognized field, and drops it without a word.

El hook se arregló en `5d9c1ee1b` ("fix(hooks): entregar el additionalContext que
el host venía descartando"). El test quedó sin tocar desde `b053b7e32`, anterior.
O sea: el test afirmaba la conducta rota, y al arreglar el código se puso rojo
acusando al arreglo. Mentía el test, no el código.

El cambio **endurece**, no afloja: además de leer la forma que el host sí consume,
agregué la aserción de que la forma descartada **no** esté presente, para que no
pueda volver a regresar en silencio.

- **Rojo antes**: `KeyError: 'additionalContext'`
- **Verde después**: `3 passed` (los otros dos del archivo seguían y siguen verdes)
- **Control**: la forma vieja (`{"additionalContext": ...}` a nivel raíz) es
  rechazada por las aserciones nuevas por dos vías independientes — el
  `"additionalContext" not in out` la rechaza, y el acceso a `hookSpecificOutput`
  levanta `KeyError`. Verificado ejecutando ambas contra un payload fabricado con
  la forma vieja.

Contrato citado: `manifests/claude-code-hooks-schema.yaml`.

## Las que son del test y no del código

Sólo la #2 de arriba, confirmada por fechas de commit y por el comentario del
propio hook.

De las 10 que quedan, **`test_minimal_has_core_safety` es sospechosa de lo mismo
pero no lo pude cerrar**, y no la toqué. Exige que el perfil `minimal` incluya
`rate-limiter.sh`. Los hechos, que apuntan en direcciones opuestas:

- A favor de que miente el molde: la cabecera de `scripts/set-security-profile.sh`
  describe `minimal` como *"core safety only (secret detection, **rate limiting**,
  error capture)"*, y el propio script anuncia por pantalla
  `PreToolUse: ... rate-limiter, secret-detector`. El molde
  `templates/security-profiles/minimal.json` no lo tiene; sólo `paranoid.json` lo
  registra.
- A favor de que miente el test: `rules/rate-limiting.md` documenta que el
  limitador está **deliberadamente sin registrar**, y que registrarlo es *"una
  decisión pendiente del operador, no un olvido de documentación"*.

Agregarlo a `minimal.json` obliga a agregarlo también a `standard.json` (por el
invariante minimal ⊆ standard ⊆ paranoid, que hoy está verde) y activa el
limitador en **todo proyecto consumidor**. Sacarlo del `required` del test es
aflojar la aserción. Las dos direcciones son decisión del operador, no mía.

## Lo que NO hice y por qué

- **No completé `manifests/hook-registration-classification.yaml`** (cubre 4 de las
  10 restantes: `test_unregistered_hooks_match_classification_manifest`,
  `test_no_unclassified_hook_scripts`, `test_no_orphan_hooks[post-git-orphan-notifier.sh]`
  y parte de `test_hook_counts_match_scorecard`). El contrato del manifiesto exige
  por entrada `status`, `rationale` y `next_action` — es decir, **por qué** cada
  hook está deliberadamente sin registrar y **qué** lo promovería. No conozco la
  intención de los autores de `e11719383`, `3e2c658c6`, `57f433b83`, `4a022ed38` y
  `428f27fcb`. Rellenar seis entradas con racionales inventados es el verde barato
  exacto de esta familia: una clasificación que no clasifica nada da sensación de
  cobertura y se vuelve gate. Es deuda real y queda declarada, sin apagar.

- **No moví el número del scorecard** (`test_hook_counts_match_scorecard` espera
  `**256**` hooks en disco). Es un censo, no un baseline de deuda, pero
  actualizarlo a mano sin entender por qué proliferaron los hooks es exactamente
  "mover el baseline para apagar el rojo". Necesita el generador del scorecard o
  una decisión escrita.

- **No toqué los tres de `test_hook_quality_system.py`** ni
  `test_hook_lib_projection::test_fail_open_when_lib_hidden` ni
  `test_runtime_hook_reality::test_repository_settings_hook_count_is_report_derived_not_hardcoded`.
  Los dos últimos son fallas de conducta que merecen investigación propia (uno
  espera una fila de métricas `scan_error_fail_open` que no se escribe; el otro
  compara `'fail' == 'pass'`), y no me alcanzó el presupuesto de llamadas para
  distinguir defecto de test-que-certifica-el-defecto. Marcarlas como arregladas
  sin esa distinción habría sido peor que dejarlas.

- **No usé `PYTEST_ALLOW_NONVENV=1`** aunque el guard lo ofrece. Ver la sección de
  método: habría desactivado la garantía de que los dos lados del diferencial
  corren el mismo runtime, que es justamente lo que el diferencial mide.

- **No commiteé en `main`.** El encargo mencionaba el token de bypass; preferí
  ramificar, que respeta el guard en vez de esquivarlo.

- **No corrí la suite completa.** Corrí los 9 archivos del lote (726 veredictos,
  ~50s) antes y después. Nada fuera del lote entró en el diferencial.

## Reproducir

```bash
# estado tras los arreglos: 10 fallan, 716 pasan
.venv/bin/python3 -m pytest \
  tests/contracts/test_hook_quality_system.py \
  tests/behavior/test_hook_architecture.py \
  tests/audit/test_hooks_contracts.py \
  tests/audit/test_hook_registration_classification.py \
  tests/audit/test_hook_maturity_coverage.py \
  tests/audit/test_hook_lib_projection.py \
  tests/unit/test_runtime_hook_reality.py \
  tests/unit/test_governance_policy_hook_adoption.py \
  tests/unit/test_agent_message_hooks.py \
  -q --no-header -p no:randomly
```

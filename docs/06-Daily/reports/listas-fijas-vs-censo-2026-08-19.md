# Listas fijas vs. censo — auditoría 2026-08-19

## Resumen ejecutivo

Barrido de `scripts/`, `hooks/`, `cos_lib/`, `tests/` y `manifests/` buscando
colecciones literales de nombres de primitivas. Veredictos: **5 DEBE SER CENSO**,
**12 CORRECTAMENTE FIJA**, **6 YA ES CENSO**.

Las cinco listas defectuosas viven todas en el camino de instalación o de
proyección, que es exactamente donde el encargo predijo que estarían: un elemento
que falta ahí no le llega al proyecto del dev y nadie se entera. La víctima más
cara está probada corriendo el instalador: con `--default`, `rules/model-routing.md`
y `rules/result-management.md` se copian y se borran en el mismo `cos_init.py`.

Arreglé una sola cosa: los asientos fantasma del `registration-allowlist.txt`
(3, no 4), con test que falla antes y pasa después. Las otras cuatro cambian qué
shippea el instalador — se reportan, no se aplican.

## Correcciones a las premisas del encargo

1. **La lista testigo no decide nada.** `DEFAULT_HOOKS` en `scripts/cos_init.py:101`
   (el encargo la ubicaba "alrededor de la línea 104") es un **fallback de modo
   degradado**: `_boundary_names()` sólo la usa si PyYAML falta o
   `manifests/primitive-install-boundary.yaml` no se puede leer. En el camino
   normal la lista que decide es la del manifest. Y los 44 hooks del fallback
   coinciden exactamente con los 44 del manifest — cero drift ahí.
   La víctima real está en el vecino: `COS_INIT_CORE_RULES` (línea 120).

2. **El `registration-allowlist.txt` está peor de lo que decía el encargo.**
   No son 98 asientos para hooks ya registrados: son **141**. Y no son 4 fantasmas
   sino **3** — `prompt-quality.sh` SÍ existe, en `packages/prompt-quality-gate/hooks/`,
   y está registrado en `.cursor/hooks.json` y `.devin/hooks.json`. Lo que lo hacía
   parecer fantasma es un defecto aparte, ver fila 5 de la tabla.

3. **El allowlist no aporta nada al gate, ni siquiera sus 40 asientos vivos.**
   Los 40 hooks que efectivamente no están proyectados están *todos* también en
   `manifests/hook-registration-classification.yaml` con status de ausencia
   intencional. `check_hook_registration.py` los saltea por el manifest, no por el
   allowlist. Borrar el archivo entero no cambiaría el veredicto del gate — lo que
   lo mantiene vivo son cinco tests que lo leen.

4. **`install.sh`: confirmo el descarte del encargo.** No lo re-verifiqué; no
   encontré evidencia en contra durante el barrido.

5. **El `--help` del instalador miente en el número.** Dice "14 core rules";
   la corrida real deja 15. Es la misma lista fija contada por tercera vez.

## Tabla de listas

### DEBE SER CENSO (5)

| Lista | Dónde | Censo que debería usar | Motivo |
|---|---|---|---|
| `COS_INIT_CORE_RULES` (16 nombres) | `scripts/cos_init.py:120`, aplicada en `:977` | `manifests/primitive-install-boundary.yaml > profiles.default.primitives.rules` (17) | Pretende ser "las rules core del perfil default", que es justo lo que el manifest ya declara; una rule nueva en el manifest se copia y esta lista la borra. |
| Registro de hooks de Claude Code (225 literales) | `scripts/_lib/settings-driver-claude-code.sh` | `cognitive-os.yaml > harness.hooks` (lo leen los otros 3 drivers) | ADR-064 dice que el registro canónico es el yaml; este driver lo lleva a mano. Un hook agregado sólo al yaml nunca llega a Claude Code. |
| `harness.hooks` (190 scripts) | `cognitive-os.yaml` | `hooks/*.sh` + `packages/*/hooks/*.sh` (257 en el root principal) | Se declara registro canónico de hooks; 67 hooks del árbol no figuran, y varios de ellos SÍ están proyectados por otra vía. El registro sub-reporta. |
| `DEFAULT_HARNESSES` (8) | `scripts/portable_ai_overlay.py:31` | `manifests/harness-projection-registry.json` (generado, 22 con `status: implemented`) | El overlay portable pretende cubrir los harnesses soportados; el registry generado ya es el censo y esta lista se quedó en 8. |
| `get_hooks_on_disk()` (glob de un solo root) | `scripts/check_hook_registration.py:31` | `hooks/*.sh` **+** `packages/*/hooks/*.sh`, como ya hace `audit_gate_registration.py:179` | Es un censo, pero sobre un subárbol incompleto: los hooks de paquete nunca se chequean por registración. |

### CORRECTAMENTE FIJA (12)

| Lista | Dónde | Motivo |
|---|---|---|
| `DEFAULT_HOOKS` / `DEFAULT_RULES` / `DEFAULT_SKILLS` | `scripts/cos_init.py:94-117` | Fallback de modo degradado: se usan cuando el manifest no se puede leer. No se pueden derivar de la fuente que acaba de fallar. (Drift menor: `DEFAULT_RULES` no incluye `RULES-COMPACT`, que el manifest sí trae.) |
| `EXCLUDED_RULES` (~30) | `hooks/self-install.sh:340` | Curaduría con justificación escrita por entrada (qué hook la reemplaza). Es una decisión de costo de contexto, no un censo. |
| `CORE_KEEP` (11) | `scripts/cos_default_visible_reducer.py:15` | "Killer set" deliberado: qué primitivas se quedan en core aunque no sean blocking. |
| `DEFAULT_RULES` (6) | `scripts/rules_export.py:56` | El comentario lo dice: set mínimo curado para proyectos que adoptan; se amplía con `--rules`. |
| `KNOWN_ORPHANS`, `EXPECTED_CODE_DEAD`, `PLACEHOLDER_HOOK_NAMES` | `tests/audit/test_hooks_contracts.py` | Ratchet y exclusión de literales de documentación, con motivo escrito por bloque. El test falla si aparece un huérfano nuevo — es la forma correcta de fijar una lista. |
| `registration-allowlist.txt` | `hooks/_lib/` | El mecanismo es correcto (excepciones deliberadas, ratchet que sólo encoge). El problema no es que sea fija: es que 141 de 182 asientos ya no suprimen nada. Ver "Lo que NO arreglé". |
| Vocabularios cerrados (`VALID_SCOPES`, `VALID_MODES`, `COMPLETION_STATUSES`, `PASS_VERDICTS`, `FAMILY_TO_DIR`, `PROFILE_MAP`, `ENFORCEMENT_FIDELITY`, …) | varios en `scripts/` | Enumeran una taxonomía cerrada, no una población del árbol. Un valor nuevo requiere código nuevo que lo entienda. |

### YA ES CENSO (6)

| Lista | Dónde | Motivo |
|---|---|---|
| `SUPPORTED_HARNESSES`, `HARNESS_SETTINGS`, `STRUCTURAL_INSTRUCTION_HARNESSES` | `scripts/cos_init.py:79-91` | Derivadas de `manifests/harness-projection-registry.json`, que es generado. |
| `manifests/harness-projection-registry.json` | — | Materializado por `scripts/generate_harness_projection_registry.py`. |
| Población de gates | `scripts/audit_gate_registration.py:179` | `glob("hooks/*.sh") + glob("packages/*/hooks/*.sh")`, con resolución de symlinks, y explícitamente **no** honra el allowlist para contar. |
| Auditoría de drift de proyección | `scripts/hook_projection_drift_audit.py` | Lee el yaml y los drivers en vivo; toma las constantes de los drivers en vez de copiarlas. |
| Copia por scope | `install.sh:48-52` | Filtra por el marcador `# SCOPE:` vía `INSTALL_SCOPE`. Verificado por el operador. |
| Censo de asientos del allowlist | `tests/audit/test_registration_allowlist_seats.py` (nuevo) | El set de ocupación se globea del árbol sobre los dos roots de hooks. |

### Aparte: constante muerta

`scripts/primitive_row_audit.py:25` define `EVENTS` con 5 eventos y **no la usa en
ningún lado** (única referencia: su propia definición). Los eventos reales en
`.claude/settings.json` son 10. Si algún día se usa, nace con la mitad de la
población. No la toqué: borrarla es una decisión de quien mantiene ese script.

## Las víctimas concretas

**1. `rules/model-routing.md` y `rules/result-management.md` — se instalan y se borran.**

`manifests/primitive-install-boundary.yaml` declara 17 rules para el perfil default.
`cos_init.py:977` recorre el destino y hace `unlink()` de toda rule cuyo basename no
esté en `COS_INIT_CORE_RULES` (16 nombres, escritos a mano). Las dos rules están en
el manifest y no en la constante.

```
$ .venv/bin/python3 scripts/cos_init.py --default --harness claude   # en un proyecto vacío
$ ls .claude/rules/cos/ | wc -l
15
$ ls .claude/rules/cos/ | grep -E 'model-routing|result-management'
(vacío)
```

Comparación de las dos listas:

```
$ .venv/bin/python3 -c "
import re,ast,yaml,pathlib
core=ast.literal_eval(re.search(r'COS_INIT_CORE_RULES = (\[.*?\])',open('scripts/cos_init.py').read(),re.S).group(1))
man=[pathlib.Path(x).name for x in yaml.safe_load(open('manifests/primitive-install-boundary.yaml'))['profiles']['default']['primitives']['rules']]
print('manifest y NO en la constante:',sorted(set(man)-set(core)))
print('constante y NO en el manifest:',sorted(set(core)-set(man)))"
manifest y NO en la constante: ['model-routing.md', 'result-management.md']
constante y NO en el manifest: ['agent-security.md']
```

Lo que se pierde: todo proyecto instalado con el perfil default se queda sin la
regla de ruteo de modelos (`RULES-COMPACT` §4 la cita como activa) y sin la de
truncado de resultados. `agent-security.md` es el espejo: está en la constante
"a conservar" y nunca se copia, así que la entrada no conserva nada.

**2. `hooks/publication-safety.sh` — declarado y nunca proyectado a Claude Code.**

```
$ .venv/bin/python3 scripts/hook_projection_drift_audit.py
declared: 200 entries naming 190 distinct scripts
harness     projected  by-design   LOST
claude            191          8      1
LOST -- declared active and unreachable, with no declaration saying so (1):
  claude    publication-safety.sh                      PreToolUse[Bash] scope=both
```

Ya está documentado en el header del propio driver. Lo confirmo con el comando, no
con la lectura.

**3. Los 67 hooks del árbol que no figuran en el registro canónico.**

```
$ .venv/bin/python3 -c "
import yaml,pathlib
h=(yaml.safe_load(open('cognitive-os.yaml')) or {}).get('harness',{}).get('hooks',{})
d={pathlib.Path(v['script']).name for v in h.values() if isinstance(v,dict) and v.get('script')}
o={p.name for p in pathlib.Path('hooks').glob('*.sh') if not p.name.startswith('_')}
print(len(d),len(o),len(o-d))"
190 257 67
```

Entre ellos hay hooks que **sí corren**: `tool-loop-detector.sh`, `task-recorder.sh`,
`semgrep-scan.sh`, `subagent-capability-preflight.sh`, `state-retention-audit.sh`.
O sea: el registro que ADR-064 llama canónico no describe la población que ejecuta.

**4. 16 harnesses implementados sin overlay portable por defecto.**

```
$ .venv/bin/python3 -c "
import json,re,ast
reg=json.load(open('manifests/harness-projection-registry.json'))
impl={r['id'] for r in reg['harnesses'] if r.get('status')=='implemented'}
dh=set(ast.literal_eval(re.search(r'DEFAULT_HARNESSES = (\[.*?\])',open('scripts/portable_ai_overlay.py').read(),re.S).group(1)))
print('implementados sin overlay:',sorted(impl-dh))
print('en overlay pero NO implementados:',sorted(dh-impl))"
implementados sin overlay: ['agents-md','aider','amp-code','augment-code','cline','continue-dev','factory-droid','gemini-cli','goose','jetbrains-junie','kilo-code','kimi-code','qoder','qwen-code','warp','zed-ai']
en overlay pero NO implementados: ['devin','kiro']
```

Los dos sentidos duelen: `gemini-cli` y `qwen-code` están implementados y no entran
al overlay por defecto; `devin` y `kiro` entran sin estar implementados.

**5. `packages/prompt-quality-gate/hooks/prompt-quality.sh` — invisible para el gate
de registración.**

`check_hook_registration.py` globea sólo `hooks/*.sh`. El hook de paquete existe,
está registrado en `.cursor/hooks.json` y `.devin/hooks.json`, y el gate ni lo mira.
Fue lo que lo hizo aparecer como "fantasma" en el conteo del encargo.

**6. Los 3 asientos fantasma del allowlist** (arreglado, abajo).

## Lo que arreglé

Los asientos del `registration-allowlist.txt` que no tienen hook. Un asiento sin
ocupante no suprime nada y agranda un ledger que ya es colchón.

**Archivos:**
- `tests/audit/test_registration_allowlist_seats.py` (nuevo)
- `hooks/_lib/registration-allowlist.txt` (3 líneas fuera, lápida escrita)

El test computa la ocupación como **censo sobre los dos roots de hooks**
(`hooks/*.sh` y `packages/*/hooks/*.sh`), justo para no repetir el falso positivo
de `prompt-quality.sh`.

**Corrida ANTES (lista fija — falla):**

```
$ .venv/bin/python3 -m pytest tests/audit/test_registration_allowlist_seats.py -q
F.                                                                       [100%]
E   AssertionError: registration-allowlist.txt suppresses hooks that do not exist:
    ['agent-work-tracker.sh', 'test-baseline-diff.sh', 'wiring-check.sh'].
    Each of these excuses nothing; delete the line.
1 failed, 1 passed in 0.05s
```

**Corrida DESPUÉS (censo — pasa):**

```
$ .venv/bin/python3 -m pytest tests/audit/test_registration_allowlist_seats.py -q
..                                                                       [100%]
2 passed in 0.21s
```

**Verificación individual de los 3, antes de tocarlos** (no se vació nada a ciegas):

```
$ for h in agent-work-tracker.sh test-baseline-diff.sh wiring-check.sh; do
    echo "== $h"; find . -name "$h" -not -path "./.git/*"; done
== agent-work-tracker.sh
./archive/primitive-surface/hooks/agent-work-tracker.sh
== test-baseline-diff.sh
== wiring-check.sh
./archive/primitive-surface/hooks/wiring-check.sh
```

`archive/primitive-surface/hooks/` no es un root de hooks (no lo globea ningún
gate). `test-baseline-diff.sh` no existe en el árbol; sus únicas referencias son
`CHANGELOG.md` y docs históricos.

**El gate no se movió** (mismo veredicto, mismo exit code, antes y después):

```
$ .venv/bin/python3 scripts/check_hook_registration.py
Hook registration OK: 257 hooks on disk, 72 fully registered, 185 intentionally absent
exit=0
```

**Los cinco tests que leen el allowlist siguen verdes:**

```
$ .venv/bin/python3 -m pytest tests/audit/test_hooks_contracts.py \
    tests/audit/test_rules_enforcement.py tests/architecture/test_wiring.py \
    tests/contracts/test_rule_router_invariant.py \
    tests/contracts/test_cosd_auth_primitives.py \
    tests/red_team/portability/test_hook_surface_classifier.py -q
1471 passed, 149 skipped in 59.68s
```

## Lo que NO arreglé y por qué

**`COS_INIT_CORE_RULES` → censo del manifest.** Es el arreglo más valioso del
informe y es de una línea. No lo aplico porque **cambia qué se instala en
proyectos de terceros**: dos rules más sobreviven el filtro, y eso mueve el
presupuesto de contexto por sesión que el perfil default promete. Blast radius del
operador. El comando que lo prueba y la línea a cambiar están arriba.

**El driver de Claude Code → leer `cognitive-os.yaml`.** Mismo motivo, ampliado: es
el archivo que decide qué hooks se registran en cada instalación. Además el header
del propio driver ya dice que reconciliarlo (o enmendar ADR-064) es decisión de
operador y está deliberadamente sin tomar. Coincido; lo dejo así.

**`cognitive-os.yaml > harness.hooks` → censo de `hooks/`.** Agregar 67 hooks al
registro canónico los pone en el camino de proyección de cuatro harnesses. Es un
cambio de superficie instalada, no una corrección de lista.

**`DEFAULT_HARNESSES` del overlay portable.** Regenerar el overlay con 22 harnesses
en vez de 8 cambia un artefacto derivado que sostiene claims de portabilidad
públicos (`tests/contracts/test_portable_ai_overlay.py --check`, ADR-258). El caso
`devin`/`kiro` sugiere además que la lista y el registry se poblaron con criterios
distintos; unificarlos sin saber cuál manda sería adivinar.

**`get_hooks_on_disk()` → los dos roots.** Ampliar el censo del gate hace que los
hooks de paquete pasen a chequearse por registración. No sé cuántos fallarían, y un
gate que se pone rojo por ampliar su población es una decisión con costo — la del
operador, no la mía. La medición previa (cuántos hooks de paquete quedarían
`UNREGISTERED`) es el paso que falta antes de tocarlo.

**Los 141 asientos inertes del allowlist.** No los toqué. Cada uno nombra un hook
que **sí** está proyectado, así que borrarlos no cambia el veredicto del gate — pero
cinco archivos de test leen ese archivo, y uno de ellos
(`tests/contracts/test_cosd_auth_primitives.py:25`) usa la **presencia** de
`cosd-auth-guard.sh` en el allowlist como prueba de que el hook está *registrado*,
que es exactamente lo contrario de lo que el allowlist significa. Esa aserción
invertida hay que arreglarla primero, y es un cambio de contrato de test, no de
lista. Comando para reproducir el conteo:

```
$ .venv/bin/python3 -c "
import importlib.util,pathlib
s=importlib.util.spec_from_file_location('chr','scripts/check_hook_registration.py')
m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
r=pathlib.Path('.').resolve(); od=m.get_hooks_on_disk(r); al=m.load_allowlist(r)
cl=m.load_intentionally_absent_classifications(r)
live=[h for h in al&od if not m.check_hook_registered(h,r)['effective_projection']]
print('asientos:',len(al),'inertes:',len(al&od)-len(live),'vivos:',len(live),
      'vivos ya cubiertos por el manifest de clasificación:',len(set(live)&cl))"
asientos: 182 inertes: 141 vivos: 40 vivos ya cubiertos por el manifest de clasificación: 40
```

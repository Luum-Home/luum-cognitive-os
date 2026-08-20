<!-- SCOPE: os-only -->
# Las diez reglas sin gobierno: el contrato dice proyección, no bloqueo

**Fecha:** 2026-08-20 · **HEAD auditado:** `f6b6c3fe5` · **Alcance:** `hooks/self-install.sh:EXCLUDED_RULES` (102 entradas) + ADR-144
**Método:** lectura de **fuente** de cada hook. No se usó `hook_vitality_audit.py` para ninguna afirmación de este informe.

```bash
git rev-parse --short HEAD                                          # f6b6c3fe5
sed -n '/EXCLUDED_RULES=(/,/^)/p' hooks/self-install.sh | grep -c '^\s*"'   # 102
ls .claude/rules/cos/ | wc -l                                       # 2
```

---

## Control positivo, antes de leer cualquier cero

Todo este informe descansa en una sonda de tres contadores sobre la **fuente** del hook.
Antes de leer un solo cero, la sembré contra hooks que sí bloquean y contra el falso
positivo conocido del auditor de vitalidad:

```bash
probe() { f="$1"; printf '%-30s exit2=%-2s deny=%-2s permDecDeny=%-2s\n' "$(basename $f)" \
  "$(grep -cE '(^|[^0-9a-zA-Z_])exit 2([^0-9]|$)' "$f")" \
  "$(grep -c '"deny"' "$f")" \
  "$(grep -cE 'permissionDecision[^,]*deny' "$f")"; }
probe hooks/confidentiality-enforcer.sh          # exit2=1  -> BLOQUEA
probe hooks/protected-config-write-guard.sh      # exit2=1  -> BLOQUEA
probe hooks/edit-lock-pre-tool.sh                # exit2=1  -> BLOQUEA
probe packages/task-management/hooks/blast-radius.sh   # exit2=0 deny=0 permDecDeny=0
```

Las dos ramas del contrafáctico dan distinto: encuentra la ruta de bloqueo donde
existe, no la encuentra donde no. Y `blast-radius` —el hook que el auditor de
vitalidad cubetiza como guard por su `re.compile(r"permissionDecision")`— acá da
cero, porque su único `permissionDecision` es `"allow"`. La sonda separa lo que el
instrumento derivado confunde. Verificación cruzada, en la fuente:

```bash
grep -n 'permissionDecision' packages/task-management/hooks/blast-radius.sh
# 202:        permissionDecision: "allow",
sed -n '5p' packages/task-management/hooks/blast-radius.sh
# Advisory only (exit 0) — does NOT block, but warns for HIGH/CRITICAL
```

El propio hook lo dice en su línea 5.

---

## 1. La pregunta del contrato: qué dice ADR-144, citado

**El código NO derivó del contrato. El contrato nunca pidió bloqueo.**

ADR-144 §Decision define las condiciones, y son tres, todas estructurales:

> A rule may be listed in `EXCLUDED_RULES` with a `# → hook.sh` enforcement claim
> only if all of the following are true:
> 1. every referenced hook file exists;
> 2. every referenced Claude/Codex-compatible hook is present in
>    `cognitive-os.yaml > harness.hooks`;
> 3. the hook is projected by the active profile into the relevant harness settings;
> 4. if a rule is intentionally not hook-enforced, the comment must say
>    `agent-instruction-only` [...]

Existe, está registrado, está proyectado. **Nada sobre bloquear, advertir ni actuar.**

Y el ADR excluye la pregunta del comportamiento de forma explícita, en su propia
sección *"Does not answer"*:

> Whether the hook logic itself is correct. The contract verifies
> **projection (hook is wired)**; hook behavior correctness is covered by
> the hook's own tests.

La palabra "enforce" aparece una sola vez con carga semántica, en el **Context**, no
en la Decision:

> 3. a registered hook **enforces the mechanical part of the rule**.

Ese es el **intent** declarado. La Decision que lo implementa mide otra cosa.

### El veredicto sobre el objeto del encargo

El encargo preguntaba si el código derivó del contrato. **No.** Pasa lo contrario, y es
peor: el código hace exactamente lo que el contrato pide, y el contrato pide menos de lo
que su propio Context promete. El gate de ADR-144 está **verde hoy** con nueve
afirmaciones falsas vivas:

```bash
.venv/bin/python3 -m pytest tests/audit/test_hook_enforced_exclusions.py -q
# 3 passed in 0.08s
```

Las tres funciones del test (`tests/audit/test_hook_enforced_exclusions.py:77,92,108`)
verifican, respectivamente: el archivo existe, está en `harness.hooks`, está en
`.claude/settings.json`. Ninguna abre el hook.

Y su docstring promete lo que no entrega:

> These tests prevent "excluded from context" from silently becoming
> "not enforced anywhere".

No lo previenen. Un hook de tres líneas que hace `exit 0` pasa las tres.

**Entonces las once exclusiones son CORRECTAS según el contrato, y lo que está mal es
el contrato.** Ese era el hallazgo que el encargo anticipaba como "cambia todo el
encargo", y es el que se confirmó.

### ADR-241 y ADR-293: no pertinentes

- **ADR-241** (consolidated COS_BYPASS allowlist): gobierna variables de bypass, no la
  proyección de reglas. Sin relación con `EXCLUDED_RULES`.
- **ADR-293** (typed hook event contracts): tipa el **payload de entrada** de los hooks.
  Podría ser el lugar natural donde declarar el tipo de **salida** (gate / actor /
  observador), y lo menciono en §5 como alternativa rechazada por costo, pero hoy no
  dice nada sobre capacidad de bloqueo.

---

## 2. El hallazgo que reordena todo: `EXCLUDED_RULES` está inerte

Antes de decidir once reglas conviene saber qué hace hoy la lista. **Nada.**

`hooks/self-install.sh:474` solo consulta `EXCLUDED_RULES` dentro de la rama
`SYNC_ALL_RULES=true`. El propio código lo dice en su encabezado de sección
(`hooks/self-install.sh:334`):

```
# ── Excluded rules for self-hosting (SYNC_ALL_RULES=true) ─────────────
```

Y `SYNC_ALL_RULES` es `true` únicamente con perfil `full`
(`hooks/self-install.sh:454-464`). El perfil activo es `default`:

```bash
grep -A3 '^efficiency:' cognitive-os.yaml
#   profile: default               # default | full  (ADR-093: collapsed 3-tier system)

# reproducción exacta de la resolución del script (líneas 315-323):
_ep=$(grep -A1 '^efficiency:' cognitive-os.yaml | grep 'profile:' | awk '{print $2}' | tr -d "'\"\r")
echo "EFFICIENCY_PROFILE=${_ep:-default}  COS_SYNC_ALL_RULES=${COS_SYNC_ALL_RULES:-0}"
# EFFICIENCY_PROFILE=default  COS_SYNC_ALL_RULES=0
```

Contraprueba: si la lista gobernara, `.claude/rules/cos/` tendría 132−102 = 30 symlinks.

```bash
ls .claude/rules/cos/ | wc -l          # 2
ls .cognitive-os/rules/cos/ | wc -l    # 2
```

**Dos.** Las que están en `CORE_RULES`, por la rama `else` de la línea 505.

### Qué implica

1. **Sacar una regla de `EXCLUDED_RULES` no la devuelve a ningún contexto.** La opción
   B del encargo ("la regla vuelve al contexto") **no existe tal como está planteada**:
   la única palanca real es `CORE_RULES`, que hoy tiene dos entradas.
2. `EXCLUDED_RULES` no es un mecanismo: es **un documento con sintaxis de bash**. 102
   decisiones escritas que ningún código ejecuta en la configuración vigente.
3. Eso no lo vuelve inofensivo — lo vuelve *exactamente* el bug que describe
   `gates-sin-trampa`: **un supresor que no suprime nada da sensación de decisión
   tomada donde no hay nada que decidir.** Y peor acá, porque un test verde
   (ADR-144) certifica la lista todos los días.

---

## 3. Tabla de las once (son once, no diez)

Todos los `runs` de esta tabla vienen de telemetría **derivada** y van marcados como
tales. Las columnas que deciden —"qué hace de verdad"— salen de la fuente.

```bash
for s in <los 21 hooks reclamados>; do
  f=$(readlink -f hooks/$s.sh); probe "$f"
done
```

| # | Regla excluida | Hook citado | Fuente: exit2/deny/permDecDeny | Qué hace de verdad | Decisión | Costo |
|---|---|---|---|---|---|---|
| 1 | `consequence-system.md` | `consequence-evaluator.sh` | 0/0/0 | **Observador puro.** 0 `echo` a stdout, 0 a stderr. Parsea `Score:` y escribe log. Nada lee ese log en runtime. | **ACEPTAR SIN GOBERNAR** | 4 líneas de manifest |
| 2 | `auto-rollback.md` | `auto-rollback-trigger.sh` | 0/0/0 | **Actor deliberadamente inofensivo.** Escribe JSONL con `mode:"plan_required"`, `destructive_commands_executed:false`. Por diseño no revierte nada. | **ACEPTAR SIN GOBERNAR** | 4 líneas |
| 3 | `assumption-tracking.md` | `assumption-tracker.sh` | 0/0/0 | Detecta supuestos, escribe JSONL, imprime `=== ASSUMPTION TRACKER: WARNING ===` **a stdout** (`echo`, no `>&2`), exit 0. | **EL HOOK GANA RUTA DE BLOQUEO** | ~12 líneas + 1 test |
| 4 | `prompt-quality.md` | `prompt-quality-llm.sh` | 0/0/0 | Emite `hookSpecificOutput` con `decision: "advisory"` literal, y su propio comentario dice *"degrade to silent no-op — never block"*. | **ACEPTAR SIN GOBERNAR** (asesor por diseño) | 4 líneas |
| 5 | `skill-rewrite.md` | `completion-gate.sh` | 0/0/0 | 648 líneas, todo a stderr con exit 0. **Y no hace lo que la regla dice**: chequea contrato de retorno y salud, no reescritura de skills. | **ACEPTAR SIN GOBERNAR** + corregir la cita (error de categoría) | 4 líneas + 1 comentario |
| 6 | `auto-skill-generation.md` | `auto-skill-generator.sh` | 0/0/0 | **Actor.** Genera skills. La parte mecánica de la regla la ejecuta el hook; no hay nada que bloquear. | **ACEPTAR SIN GOBERNAR** (reclasificar a *hook-performed*) | 4 líneas |
| 7 | `auto-repair.md` | `auto-repair-dispatcher.sh` | 0/0/0 | **Actor.** Intenta reparar en worktree y reporta a stderr (`AUTO-REPAIR SUCCESS/FAILED`). | **ACEPTAR SIN GOBERNAR** (*hook-performed*) | 4 líneas |
| 8 | `audit-trail.md` | `git-context-capture.sh` + `session-changelog.sh` | 0/0/0 (ambos) | **Actores.** Capturan contexto git y escriben changelog en Stop. Son la parte mecánica de la regla. Bloquear en Stop no tiene forma. | **ACEPTAR SIN GOBERNAR** (*hook-performed*) | 4 líneas |
| 9 | `crash-recovery.md` | `auto-checkpoint.sh` + `crash-recovery.sh` | 0/0/0 (ambos) | **Actores.** `auto-checkpoint` escribe checkpoints; `crash-recovery` imprime el snapshot previo a stderr. El caso **menos** escandaloso de los once, pese a las 13.275 corridas. | **ACEPTAR SIN GOBERNAR** (*hook-performed*) | 4 líneas |
| 10 | `pre-commit-gate.md` | `pre-commit-gate.sh` | 0/0/0 | **La cita apunta a un archivo huérfano.** Ver §3.1: el gate real existe, bloquea, y es otro archivo. | **YA GOBERNADO — corregir la cita** | 1 línea |
| 11 | `blast-radius.md` | `blast-radius.sh` | 0/0/0 | Advisory declarado en su línea 5. Sí llega al agente vía `additionalContext`. **No estaba en la lista de diez del encargo.** | **ACEPTAR SIN GOBERNAR** (*hook-advisory*) | 4 líneas |

Para contexto, de las **20** entradas de la sección A que reclaman un hook, **9 sí
tienen ruta de bloqueo en su fuente** y su comentario es verdadero: `claim-validator`
(exit2=3), `clarification-gate` (2), `confidence-gate` (1), `confidentiality-enforcer`
(1), `content-policy` (1), `predev-completeness-check` (1), `token-budget-monitor` (3),
`scope-proportionality` (1, y cubre dos reglas). El problema no es la lista entera: es
una mitad de ella.

### 3.1 `pre-commit-gate.md` no es una de las falsas — es una cita rota

El informe previo la contó como décima con la nota *"no aparece en vitalidad"*. Es un
caso distinto y hay que separarlo: **el comportamiento sí está gobernado con bloqueo
duro; lo que está mal es a qué archivo apunta el comentario.**

```bash
git config core.hooksPath                       # .githooks
grep -c 'pre-commit-gate' .githooks/pre-commit  # 0
grep -c 'BLOCKED'         .githooks/pre-commit  # 17   <- control positivo del grep
grep -cE '^\s*exit 1'     .githooks/pre-commit  # 13
```

`.githooks/pre-commit` (19.776 bytes) es autocontenido —no hace `source` de nada bajo
`hooks/`— y tiene **13 rutas de `exit 1`**, que es como bloquea un git hook. Es un gate
real y probado.

`hooks/pre-commit-gate.sh` no lo invoca nadie: el único consumo son tests que copian y
parchean el archivo en `tmp_path` (`tests/behavior/test_safety_mesh.py:884,924,963,1005`).
Es un script huérfano con cobertura in vitro.

Y `tests/audit/test_hook_enforced_exclusions.py` lo exime a mano de sus dos chequeos
estructurales (`if rule != "pre-commit-gate.md"`, líneas 99 y 115) — o sea que la única
entrada cuya cita está rota es también la única con escape hardcodeado en el gate.

**Decisión:** corregir el comentario a `# → .githooks/pre-commit (git hook, 13 rutas de
bloqueo)` y abrir por separado la pregunta de si `hooks/pre-commit-gate.sh` se borra.
Costo: 1 línea. No requiere manifest.

### 3.2 La única que merece bloqueo, y por qué solo una

El encargo trae la señal que decide: los guards de **conducta** se ahogan en overrides
(1:188), los de **calidad de evidencia** aciertan. Aplicada a los once:

- Ocho son **actores o asesores** (2, 4, 6, 7, 8, 9, 11 y parte de 5). Bloquear no es su
  forma. Un hook de Stop que captura el changelog no tiene qué denegar; un dispatcher de
  reparación tampoco. Pedirles ruta de bloqueo sería inventar un gate para justificar una
  palabra mal elegida.
- Dos son **observadores puros** (1 y 3): corren, escriben, y nada lee lo que escriben.
- Uno ya está gobernado (10).

De los dos observadores, `consequence-evaluator` puntúa conducta agregada — familia
1:188, no toco. Queda **`assumption-tracker`**.

#### `assumption-tracking.md` → EL HOOK GANA RUTA DE BLOQUEO

**Por qué esta:** es calidad de evidencia, no conducta. La pregunta que responde —*¿el
agente declaró los supuestos que hizo?*— es de la misma familia que `confidence-gate` y
`claim-validator`, que ya bloquean y cuyo comentario en la lista es verdadero. Y el hook
**ya calcula el veredicto**: tiene `$ASSUMPTION_COUNT` y ya redacta el warning
(`packages/verification-audit/hooks/assumption-tracker.sh:152-155`). Solo lo tira a
stdout con exit 0.

**Qué tendría que bloquear:** PostToolUse sobre Agent, cuando `ASSUMPTION_COUNT` supere
un umbral declarado **y** la respuesta no traiga sección de supuestos. No bloquear por
contar supuestos —eso es castigar al agente honesto—: bloquear por **hacerlos sin
declararlos**. Salida `exit 2` con el texto ya redactado por stderr, que en PostToolUse
es el canal que vuelve al agente.

**Payload de prueba** (el hook lee stdin y ya tiene los selectores en su línea 69):

```bash
# NEGATIVO: supuestos declarados -> debe salir 0
printf '%s' '{"tool_name":"Agent","tool_response":"Assumptions: (1) the config is default.\nDone."}' \
  | bash packages/verification-audit/hooks/assumption-tracker.sh; echo "exit=$?"

# POSITIVO: supuestos sin declarar -> debe salir 2
printf '%s' '{"tool_name":"Agent","tool_response":"I assume the config is default. I assume tests pass. Presumably the hook is registered. It should be fine."}' \
  | bash packages/verification-audit/hooks/assumption-tracker.sh; echo "exit=$?"
```

Si las dos ramas dan lo mismo, la sonda está rota y no se mergea.

**Riesgo de falsos positivos — alto, y hay que decirlo.** El detector es un `grep -oiE`
sobre prosa (línea 95). "I assume" dentro de una cita, de un bloque de código o de un
informe *sobre* supuestos dispara igual. Mitigación mínima: umbral ≥ 4 (no ≥ 1), y
gobernar el umbral por env var con default conservador. Si en un sprint la ratio
override:disparo se parece a 1:188, se revierte a observador **por escrito**, no
callando el hook.

**Costo:** ~12 líneas en el hook + 1 test de dos ramas. Cero hooks nuevos.

---

## 4. Dónde vive la declaración "aceptado sin gobernar"

El precedente que pide el encargo existe y funciona:
`manifests/hook-registration-classification.yaml` (643 líneas, JSON pese al `.yaml`),
con contrato explícito:

> `"contract": "Every unregistered top-level hook must appear here with status, rationale, and next_action."`

Lo leen ocho tests (`tests/audit/test_hook_registration_classification.py`,
`tests/contracts/test_orphan_hooks.py`, y seis más). Es el patrón correcto y ya está
pagado.

**Propuesta: un archivo hermano, `manifests/rule-governance-classification.yaml`**, con
la misma forma y un campo nuevo — el que hoy nadie declara:

```yaml
contract: "Toda entrada de EXCLUDED_RULES con una cita `# → hook.sh` declara acá qué
           hace ese hook de verdad. `enforcement` es un hecho sobre la fuente, no una
           intención."
entries:
  - rule: rules/audit-trail.md
    hooks: [hooks/git-context-capture.sh, hooks/session-changelog.sh]
    enforcement: hook_performed      # gate | hook_performed | hook_advisory | ungoverned
    rationale: >
      Los dos hooks EJECUTAN la parte mecánica de la regla (capturan contexto git,
      escriben el changelog) en Stop. No hay nada que denegar en Stop. La regla queda
      fuera del contexto del agente a propósito: el agente no tiene que acordarse de
      algo que el hook hace solo.
    next_action: none
```

Cuatro valores, y la diferencia entre ellos es la que el vocabulario actual no tiene:

| valor | significa | los de esta tabla |
|---|---|---|
| `gate` | tiene ruta de bloqueo en su fuente | los 9 verdaderos de §3 |
| `hook_performed` | el hook **hace** lo que la regla pide; nadie necesita recordarlo | 2, 6, 7, 8, 9 |
| `hook_advisory` | le llega al agente como contexto, sin obligar | 4, 11 |
| `ungoverned` | corre, escribe, nadie lo lee. **Decisión explícita, con motivo.** | 1, y 3 si se rechaza el bloqueo |

`ungoverned` no es una derrota: para `consequence-evaluator` es la respuesta correcta y
hoy no se puede escribir. Lo único que el sistema no debería permitir es lo que permite
ahora — que el silencio se lea como enforcement.

**Costo:** ~55 líneas de manifest (11 entradas × ~5) + el test de §5.

---

## 5. Las siete fantasma

Recontadas por mi cuenta, con `os.path.exists` **más** `islink` y `realpath` —porque este
repo usa symlinks y una auditoría previa publicó ausencias falsas exactamente así:

```bash
.venv/bin/python3 - <<'PY'
import re,os
blk=re.search(r'EXCLUDED_RULES=\((.*?)\n\)',open('hooks/self-install.sh').read(),re.S).group(1)
ex=re.findall(r'"([a-z0-9._-]+\.md)"',blk)
print('entradas:',len(ex),'unicas:',len(set(ex)))
for e in ex:
    p='rules/'+e
    if not os.path.exists(p): print(' ',e,'| islink',os.path.islink(p),'| realpath',os.path.realpath(p))
PY
```
```
entradas: 102 unicas: 102
  ecosystem-tools.md          | islink False | realpath .../rules/ecosystem-tools.md
  os-vs-project.md            | islink False | realpath .../rules/os-vs-project.md
  dogfooding.md               | islink False | realpath .../rules/dogfooding.md
  plan-first.md               | islink False | realpath .../rules/plan-first.md
  component-classification.md | islink False | realpath .../rules/component-classification.md
  cognitive-os-changes.md     | islink False | realpath .../rules/cognitive-os-changes.md
  library-selection.md        | islink False | realpath .../rules/library-selection.md
```
```bash
# control positivo del chequeo de existencia
ls -la rules/audit-trail.md rules/plan-first.md
# -rw-r--r--  2721  rules/audit-trail.md
# ls: rules/plan-first.md: No such file or directory
```

Siete confirmadas, ninguna es symlink roto ni caso de resolución.

### Qué hacer: borrar las siete entradas

**Ninguna de las siete está en la sección A.** Todas viven en B (package-specific) o C
(contextual), o sea que ninguna reclama enforcement de hook: sus comentarios dicen
*"reference doc, not behavioral"*, *"contextual: load on demand"*. No hay un gobierno
que se pierda al borrarlas.

Y por §2, no hacen absolutamente nada: la lista no se lee en perfil `default`, y aun en
`full` el bucle recorre `rules/*.md` —una entrada que nombra un archivo inexistente
nunca matchea.

**Recrear la regla no corresponde.** Tres de las siete (`component-classification`,
`dogfooding`, `os-vs-project`) tienen ref-key en `RULES-COMPACT.md` apuntando a skills o
a documentos de arquitectura, no a reglas de comportamiento. El informe del 20-08 §4 ya
las clasificó: son *"skills disfrazadas de reglas"* o directamente nada. Excluir del
contexto algo que no es una regla es una decisión sobre un objeto que no existe.

**Costo:** −7 líneas. **Prerrequisito para que no vuelvan:** el test de §6 hace fallar
cualquier entrada sin archivo, cosa que hoy ningún test hace (el de ADR-144 solo mira
las 20 con cita de hook; las 82 restantes no las toca nadie).

---

## 6. El mecanismo mínimo contra justificaciones falsas

**Restricción de diseño:** el repo tiene 291 hooks y el operador evalúa desmantelar por
costo de mantenimiento. Un hook nuevo acá sería el problema, no la solución. **Cero
hooks nuevos, cero latencia en el hot path, cero archivos nuevos de test.**

### Dos funciones agregadas al test que ya existe

`tests/audit/test_hook_enforced_exclusions.py` ya parsea la lista, ya resuelve los
paths, ya corre en el lane `audit`. Reusa todo su andamiaje.

```python
# ── función 1: la cita tiene que ser cierta ──────────────────────  ~30 líneas
_BLOQUEO = (
    re.compile(r"(?:^|[^0-9A-Za-z_])exit 2(?:[^0-9]|$)", re.M),
    re.compile(r'"deny"'),
    re.compile(r"permissionDecision[^,]*deny"),
)

def _tiene_ruta_de_bloqueo(script: Path) -> bool:
    src = script.resolve().read_text(errors="replace")
    return any(p.search(src) for p in _BLOQUEO)

def test_toda_cita_de_enforcement_es_cierta_o_esta_declarada():
    """El gate de ADR-144 verifica que el hook esté CABLEADO. Este verifica que
    HAGA algo. Un hook de tres líneas que hace `exit 0` pasa aquél y falla éste."""
    declarados = _clasificacion_declarada()      # lee el manifest de §4
    for regla, scripts in _excluded_rule_hook_claims().items():
        if regla in declarados:                  # ya hay decisión escrita: pasa
            continue
        sin_bloqueo = [s for s in scripts if not _tiene_ruta_de_bloqueo(HOOKS_DIR / s)]
        assert not sin_bloqueo, (
            f"{regla} se excluye del contexto citando {sin_bloqueo}, y esos hooks no "
            f"tienen ruta de bloqueo en su fuente. Ni la regla llega ni el hook obliga.\n"
            f"Salidas: (a) darle ruta de bloqueo; (b) declararlo en "
            f"manifests/rule-governance-classification.yaml con enforcement y rationale."
        )

def test_control_positivo_de_la_sonda():
    """Sin esto, un bug en _BLOQUEO pone todo en verde y el gate se apaga solo."""
    assert _tiene_ruta_de_bloqueo(HOOKS_DIR / "confidentiality-enforcer.sh")
    assert not _tiene_ruta_de_bloqueo(
        HOOKS_DIR / "blast-radius.sh"), "el falso positivo de permissionDecision volvió"

# ── función 2: las 82 entradas que hoy no mira nadie ─────────────  ~10 líneas
def test_ninguna_entrada_excluye_un_archivo_inexistente():
    faltan = [e for e in _todas_las_entradas() if not (RULES_DIR / e).exists()]
    assert not faltan, f"EXCLUDED_RULES decide sobre reglas que no existen: {faltan}"
```

**Costo total: ~45 líneas de test + ~55 de manifest = ~100 líneas. Cero runtime.**

Tres cosas de diseño que valen más que el conteo:

1. **La escapatoria es declarar, no suprimir.** Un `# noqa` apaga la medición; una
   entrada en el manifest con `enforcement: ungoverned` y su `rationale` **es** el
   entregable. El camino barato produce la documentación que falta.
2. **El control positivo está cableado adentro.** Es el mismo error que ya cometió
   `hook_vitality_audit.py`: una regex mal puesta publica ceros falsos en escala. Acá
   `blast-radius` queda como centinela permanente de ese falso positivo exacto.
3. **Arreglar la docstring mentirosa de ADR-144** (líneas 3-6 de ese archivo): hoy dice
   que previene "not enforced anywhere" y no lo hace. Con estas dos funciones pasa a ser
   cierta. Candidata directa a `manifests/documentation-truth-claims.yaml`.

### Alternativas rechazadas

| Alternativa | Rechazada porque |
|---|---|
| Hook nuevo que valide la lista en runtime | 292 hooks. Contradice el motivo del encargo. |
| Extender ADR-293 con tipo de salida por hook | Correcto en el papel, pero toca 291 hooks para resolver 20 entradas. Desproporcionado. |
| Enmendar ADR-144 y nada más | Un ADR corregido no falla en CI. Ya se probó "leave as manual discipline" y el propio ADR-144 lo lista como rechazada: *"This already failed"*. |
| Derivar `can_block` del auditor de vitalidad | Es el artefacto derivado que ya nos mordió. Fuente o nada. |

---

## 7. Orden propuesto

| # | Acción | Costo | Bloquea a |
|---|---|---|---|
| 1 | Borrar las 7 entradas fantasma | −7 líneas | — |
| 2 | Corregir la cita de `pre-commit-gate.md` → `.githooks/pre-commit` | 1 línea | — |
| 3 | Crear `manifests/rule-governance-classification.yaml` con las 10 restantes | ~55 líneas | 4 |
| 4 | Dos funciones en `tests/audit/test_hook_enforced_exclusions.py` + docstring | ~45 líneas | — |
| 5 | Enmendar ADR-144: la Decision incorpora `enforcement`, el "Does not answer" deja de excluir la capacidad de bloqueo | ~15 líneas de ADR | — |
| 6 | Ruta de bloqueo en `assumption-tracker.sh`, umbral ≥4, tras los payloads de §3.2 | ~12 líneas + test | 3 |
| 7 | **Decisión de operador, aparte:** qué se hace con `EXCLUDED_RULES` dado que está inerte (§2) | — | — |

El ítem 7 no es mío. Pero si la respuesta a §2 es "el perfil `full` no se va a usar", la
lista entera es documentación, y entonces 1-6 la vuelven documentación **verdadera** en
vez de borrarla. Si la respuesta es "`full` se va a usar", 1-6 son prerrequisito para que
al activarlo no se proyecten 30 reglas elegidas por comentarios falsos.

---

## Correcciones a las premisas del encargo

1. **"La primera pregunta es si el CONTRATO dice lo que el CÓDIGO hace, o si el código
   derivó."** — Ninguna de las dos. El código cumple el contrato **al pie de la letra**;
   el contrato pide tres condiciones estructurales y ninguna de comportamiento. La
   palabra "enforces" está en el **Context** de ADR-144, no en su **Decision**, y la
   sección *"Does not answer"* excluye explícitamente la corrección del hook. El gate
   está verde con nueve afirmaciones falsas vivas (`3 passed`).

2. **"Son DIEZ."** — Son **once**, y una de las diez del encargo no corresponde.
   - `blast-radius.md` es una **falsa más** que nadie contó: fuente `exit2=0 deny=0
     permDecDeny=0`, y su línea 5 dice *"Advisory only (exit 0) — does NOT block"*. El
     encargo la nombró como ejemplo del falso positivo del auditor, sin notar que además
     está en `EXCLUDED_RULES` sección A con cita de enforcement.
   - `pre-commit-gate.md` **no es falsa**: el comportamiento tiene bloqueo duro real, 13
     rutas de `exit 1` en `.githooks/pre-commit` (`core.hooksPath=.githooks`). Lo roto es
     la **cita**: apunta a `hooks/pre-commit-gate.sh`, que no lo invoca nadie salvo tests
     que lo copian a `tmp_path`. Neto: 10 falsas, y no las mismas diez.

3. **"El canal fijo tiene tope duro y hoy queda poco margen. Corré
   `tests/contracts/test_canal_al_subagente_tiene_margen.py` y decí cuántos caracteres
   cuesta cada reincorporación."** — **Presupuesto equivocado.** Ese test mide
   `hooks/subagent-context-injector.sh` (`MAX_CONTEXT_CHARS=10000`) sobre
   `templates/agent-mandatory-rules.md` + `templates/agent-preamble.md`. Corrido:
   `4 passed`, fijo 8.612 / presupuesto 8.800, **margen 188**. Pero `EXCLUDED_RULES` no
   toca ese canal: gobierna los **symlinks** de `.claude/rules/cos/`, que es otro canal
   con otro tope. Reincorporar una regla cuesta **0 caracteres** del canal del
   sub-agente. La pregunta de margen que sí importa es el canal A, y ahí el número es:
   hoy 17.583 bytes (RULES-COMPACT 13.011 + rate-limiting 4.572); las once juntas suman
   **29.647 bytes**, que lo triplicarían. Nada de eso lo mide ese test.

4. **"LA REGLA VUELVE AL CONTEXTO" como opción disponible.** — **No existe hoy.** Sacar
   una regla de `EXCLUDED_RULES` no la proyecta a ningún lado: la lista solo se consulta
   con `SYNC_ALL_RULES=true`, o sea perfil `full`, y el perfil activo es `default`
   (`cognitive-os.yaml` + reproducción exacta de las líneas 315-323 en §2). La palanca
   real es `CORE_RULES`, que tiene dos entradas. Esto reordena el encargo: la opción B no
   es "cara", es **inerte**, igual que las 102 entradas.

5. **"El auditor de vitalidad cuenta bloqueos solo por `exit_code == 2` y varios hooks
   bloquean con exit 0 + JSON en stdout; verificá la fuente antes de llamar falsa a una
   afirmación."** — Verificado, y **de los 21 hooks citados, ninguno usa esa vía**:
   `deny=0` y `permDecDeny=0` en los 21. Los 9 que bloquean lo hacen con `exit 2`, y
   `pre-commit-gate` con `exit 1` porque es git hook. La advertencia era correcta como
   método; en esta población no cambió ningún veredicto. Sí cambió uno **al revés**:
   `blast-radius`, que el auditor cubetiza como guard, no lo es.

6. **"Arreglar las tres afirmaciones falsas de `RULES-COMPACT.md`" (§6 del informe
   previo) sigue pendiente.** — **Ya está hecho, en el HEAD mismo del encargo.**
   `git log --oneline -1 -- rules/RULES-COMPACT.md` → `f6b6c3fe5 fix(reglas): las ocho
   afirmaciones "hook-enforced" del archivo que lee cada sesión`, y
   `git show HEAD:rules/RULES-COMPACT.md | grep -c 'hook-enforced'` → **0**. La línea 24
   hoy dice *"el hook INFORMA el radio, no bloquea"*. Nota operativa: la copia de
   `RULES-COMPACT.md` inyectada en mi contexto de sesión era la **anterior** al fix y
   todavía decía "hook-enforced" ocho veces — el contexto inyectado es una foto del
   arranque, no del HEAD. Si hubiera respondido desde el contexto en vez de desde el
   archivo, habría reportado como pendiente algo ya cerrado.

7. **"Un `grep -c` que da 0 puede significar que el patrón está mal."** — Me pasó, y lo
   reporto: `grep -c 'hook-enforced' rules/RULES-COMPACT.md` → **0**, y mi primera
   lectura fue "el patrón está roto". El control positivo (`grep -c 'Blast radius'` → 1)
   demostró que el grep andaba bien y el cero era **real**: es el hallazgo 6. La trampa
   funciona en las dos direcciones — un cero puede ser un patrón malo, o puede ser el
   arreglo de otra sesión.

8. **"Verificá que la premisa se sostiene."** — Los cinco hooks que el coordinador citó
   (`auto-rollback-trigger`, `git-context-capture`, `consequence-evaluator`,
   `auto-checkpoint`, `session-changelog`) dan `exit2=0 deny=0 permissionDecision=0` en
   mi medición independiente desde la fuente. **La premisa se sostiene**, con la sonda
   sembrada contra tres hooks bloqueantes y contra el falso positivo conocido.

---

## Lo que NO verifiqué

- **No corrí ningún hook con payload.** Todos los veredictos de bloqueo salen de leer la
  fuente. Los payloads de §3.2 son propuestos, no corridos.
- **Delegación de bloqueo: descartada, pero por poco.** Escribí primero que los once no
  hacían `source` de nada. Era falso — los doce sourcean entre 1 y 4 libs. Corrí la sonda
  sobre los seis libs compartidos (`hooks/_lib/{killswitch_check,common,safe-jsonl,project-root,task-identity,hook-pipe}.sh`,
  842 líneas en total) y los seis dan `exit2=0 deny=0 permDecDeny=0`, así que ningún
  veredicto cambia. Pero el error muestra el límite del método: la sonda mira **un**
  archivo, y un `exit 2` a dos saltos de `source` se le escaparía. El test de §6 hereda
  esa limitación.
- **Si el warning de `assumption-tracker` llega o no al agente.** Lo emite con `echo` a
  **stdout** desde un PostToolUse con exit 0; `completion-gate` hace lo mismo a
  **stderr**. Por semántica de Claude Code eso iría al transcript y no al agente —lo que
  volvería a esos hooks aún más mudos de lo que dice esta tabla— pero es una afirmación
  sobre el arnés que no puedo probar desde este repo. Queda como hipótesis marcada.
- **No cloné el repo a un checkout limpio.** Toda la evidencia de este informe es lectura
  de archivos versionados (`hooks/`, `packages/`, `manifests/`, `cognitive-os.yaml`,
  `.githooks/`), no telemetría ni artefactos derivados, así que la contaminación del SO
  no aplica. La única corrida fue `pytest` sobre dos archivos de test, read-only.
- **No audité `packages/*/rules/`**, solo `rules/*.md` y la lista del instalador.
- **No verifiqué las 82 entradas de las secciones B y C** más allá de la existencia del
  archivo. Sus comentarios ("reference doc, not behavioral") pueden ser tan falsos como
  los de la sección A; nadie los mira, y el test de §6 tampoco los mirará.

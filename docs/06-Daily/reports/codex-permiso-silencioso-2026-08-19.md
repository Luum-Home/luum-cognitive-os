# Codex y el permiso silencioso: `permissionDecision: "ask"` (2026-08-19)

## Resumen ejecutivo

El agujero es **real y está confirmado con cita textual de la fuente oficial**: en Codex,
`permissionDecision: "ask"` se parsea, la corrida del hook se marca fallida, y **la tool call
continúa**. Falla abierto, en silencio.

Nuestra exposición a ESE agujero es **cero**: ninguna de las 290 guardas del árbol emite
`ask` (`grep -rn 'permissionDecision' hooks/ packages/` no devuelve un solo `ask`).

La premisa más cara del encargo es falsa: **las guardas de `exit 2` NO están expuestas.**
Codex documenta `exit 2` + stderr como vía de bloqueo para PreToolUse. Las 63 guardas que
señalan por exit code son la parte SANA del árbol, no la expuesta.

El hallazgo que sí duele apareció midiendo: **`hooks/secret-detector.sh` emite
`permissionDecision: "block"`, un valor que no existe en NINGUNO de los dos arneses**
(Codex acepta `deny`; Claude Code acepta `allow|deny|ask|defer`), con `exit 0` y sin
respaldo de `exit 2`. Su rama "el input era enteramente secretos" **deja correr el comando
hoy, en Claude Code, no sólo en Codex.** No lo ejecuté: cambia qué bloquea una guarda de
seguridad.

## Correcciones a las premisas del encargo

1. **"De 63 guardas del SO, 59 señalan solo con exit code y solo 4 emiten
   `permissionDecision`."** El conteo no reproduce. Con symlinks resueltos:
   290 hooks totales, **63** con `exit 2` no comentado, **10** con `permissionDecision`,
   **1** con las dos cosas de verdad (`subagent-input-schema-validator.sh`). No son
   conjuntos de 59 + 4 sobre 63: son 63 y 10 sobre 290, casi disjuntos.

   ```bash
   find hooks packages/*/hooks -name '*.sh' | xargs -n1 readlink -f | sort -u | wc -l          # 290
   find hooks packages/*/hooks -name '*.sh' | xargs -n1 readlink -f | sort -u \
     | xargs grep -lE '^[^#]*\bexit 2\b' | wc -l                                                # 63
   find hooks packages/*/hooks -name '*.sh' | xargs -n1 readlink -f | sort -u \
     | xargs grep -l 'permissionDecision' | wc -l                                               # 10
   ```

2. **"¿Qué pasa con las 59 que usan `exit 2`? Si Codex solo honra el JSON, son 59."**
   Refutada por la doc oficial: `exit 2` es la vía documentada de bloqueo. El agujero
   nunca tuvo 59 guardas adentro. Detalle en su sección.

3. **"`manifests/harness-driver-capabilities.yaml` dice `bash_only`. Eso es falso."**
   Parcialmente. El texto del manifest ya decía *"is treated as Bash-only until live local
   payloads prove broader coverage"* — eso es política declarada del driver, no una
   afirmación sobre Codex. Lo que sí faltaba era el dato upstream al lado. Lo agregué; no
   toqué la política.

4. **"`SubagentStart: unsupported` / `PreCompact: unsupported` son falsos."** Ciertos como
   afirmación sobre Codex (los dos son eventos documentados), pero en el vocabulario de ese
   manifest `status` describe lo que el DRIVER proyecta. Cambiarlos a `limited` mueve el
   veredicto de `scripts/harness_parity_audit.py` y **rompe el ratchet** de
   `tests/red_team/portability/test_hook_projection_drift_audit.py` (lost entries 1 → 3, y
   ese presupuesto **sólo baja**, `test_budget_may_not_be_raised`). Lo probé y lo revertí:
   quedó `status: unsupported` + `upstream_status: supported` + `limitation` explicando la
   diferencia. Reclasificar es decisión del operador.

5. **"Anclaje `0.126.0-alpha.8`, hoy va `0.148.0`, 22 minors."** Confirmado, con matiz:
   `0.148.0` se publicó **ayer** (2026-08-18) y el alpha ya va en `0.149.0-alpha.1`
   (2026-08-19). El atraso crece mientras se lo mide.

6. **"Codex cambió su motor de hooks en 6 de 6 minors, uno cada ~10 días."** No pude
   verificar el "6 de 6" (exige diffear la doc por versión). La cadencia de RELEASES sí la
   medí y es **el doble de rápida** que ~10 días: **5,62 días por minor** en los últimos 90
   días, **3,17** sobre los 129 minors estables. El umbral propuesto usa esta medición, no
   la del encargo.

7. **"Una fuente de terceros (agenticcontrolplane) contradice a la oficial."** Sobre `ask`
   **coincide** con la oficial. Donde contradice es en otra cosa —dice que `allow` también
   se parsea y se rechaza—, y eso sí nos toca. Ver §Fuentes.

## Las tres afirmaciones, verificadas una por una

Fuente: `curl -sL https://developers.openai.com/codex/hooks` → 308 → `https://learn.chatgpt.com/docs/hooks`
(HTTP 200, 455 KB). El texto está en el HTML pre-renderizado; no es un resumen de WebFetch:

```bash
curl -sL https://developers.openai.com/codex/hooks -o /tmp/codex-hooks.html
grep -o 'permissionDecision[^<]*not supported yet[^<]*' /tmp/codex-hooks.html
```

**Cita textual, sección `PreToolUse`:**

> `permissionDecision: "ask"`, legacy `decision: "approve"`, `continue: false`, `stopReason`,
> and `suppressOutput` are parsed but not supported yet. Codex marks the hook run as failed,
> reports the error, and continues the tool call.

Repetida, con más alcance, en `Common output fields`:

> PreToolUse and PermissionRequest support `systemMessage`, but `continue`, `stopReason`,
> and `suppressOutput` aren't currently supported for those events. If a PreToolUse hook
> returns one of those unsupported fields, Codex marks that hook run as failed, reports the
> error, and continues the tool call.

| # | Afirmación | Veredicto |
|---|---|---|
| 1 | `ask` está aceptado por el parser pero no implementado | **CONFIRMADA** — "parsed but not supported yet" |
| 2 | Codex marca el hook como fallido | **CONFIRMADA** — "marks the hook run as failed, reports the error" |
| 3 | ¿Continúa o aborta la tool call? | **CONTINÚA** — "and continues the tool call". Fail-open, no fail-closed. |

La tercera es la que decide, y decide para el lado malo: no hay fail-closed. El operador
no ve la pregunta y la herramienta corre.

**Lo que la misma página dice y conviene tener a la vista** (sección `Tool coverage`):

> Some specialized tool paths can opt out of the default hook path. Treat tool hooks as a
> useful guardrail, not a complete enforcement boundary.

Es upstream diciendo, con todas las letras, que sus hooks no son un límite de aplicación.

## Nuestra exposición real

**Guardas que emiten `permissionDecision: "ask"`: cero.**

```bash
grep -rn 'permissionDecision' hooks/ packages/ | grep -w ask   # sin salida
grep -rhoE '"?permissionDecision"?\s*:\s*\\?"[a-z]+' hooks/ packages/ \
  | sed -E 's/.*"([a-z]+)$/\1/' | sort | uniq -c               # 9 allow, 1 block
```

Diez archivos usan `permissionDecision`; ninguno usa `ask`. Nueve emiten `allow` (advisory:
inyectan `additionalContext`, no gobiernan). El décimo es el problema.

### El hallazgo: `permissionDecision: "block"` no existe en ningún arnés

`hooks/secret-detector.sh:181`, rama "el input consistía enteramente en secretos":

```
permissionDecision: "block",
```

seguido de `exit 0`. Y el archivo **no tiene un solo `exit 2` real** — su única línea con
`exit 2` es el comentario de la línea 173 que dice que lo reemplazó:

```bash
grep -n 'exit 2' hooks/secret-detector.sh
# 173:    # permissionDecision: block instead of legacy exit 2.
```

Valores válidos, por manifest y por doc:

- Claude Code — `manifests/claude-code-hooks-schema.yaml`, PreToolUse:
  `permission_decision_values: [allow, deny, ask, defer]`.
- Codex — `deny` (o la forma vieja `decision: "block"`, que es **top-level**, no dentro de
  `hookSpecificOutput`).

`hookSpecificOutput.permissionDecision: "block"` no está en ninguna de las dos listas. Con
`exit 0` y sin `exit 2` de respaldo, el resultado esperable es que **el comando corra igual**:
un input que era 100% credenciales llega a ejecutarse mientras el hook cree que lo frenó. Es
exactamente el modo de falla que este encargo salió a buscar en Codex, y estaba adentro de
casa, en Claude Code.

Segundo archivo con `block`: `hooks/subagent-input-schema-validator.sh:97`. Ahí es inocuo —
imprime el JSON y hace `sys.exit(2)`, así que bloquea por exit code. Vale corregir el valor
igual, pero no falla abierto.

## Qué pasa con las 59 que usan `exit 2`

**No están expuestas.** Codex documenta `exit 2` como vía de bloqueo, evento por evento.
Cita textual de `PreToolUse`, inmediatamente después de la forma JSON:

> You can also use exit code `2` and write the blocking reason to `stderr`.

La misma frase aparece en `PostToolUse`, `UserPromptSubmit`, `SubagentStop` y `Stop`. Y
`Common output fields` cierra el otro lado: *"Exit 0 with no output is treated as success and
Codex continues."*

O sea: Codex honra **las dos** vías (exit code y JSON estructurado), y la que NO honra es el
subconjunto de campos JSON listado arriba. La intuición del encargo estaba invertida: en
Codex, el JSON estructurado es la vía con agujeros y el exit code es la sólida.

Consecuencia práctica: las 63 guardas de `exit 2` son la parte portable del árbol. La
recomendación de portabilidad que sale de acá es la contraria a la que se venía asumiendo —
para gobernar Codex, `exit 2` es más seguro que `permissionDecision`.

## Recomendación fundamentada

**Recomiendo la opción 1 (corregir el manifest) como acción inmediata — ya aplicada — y
rechazo explícitamente las otras tres, cada una por su motivo.**

- **Degradar `ask` → `deny` en Codex: NO, hoy no tiene sujeto.** Cero guardas emiten `ask`.
  Un traductor `ask`→`deny` sería código sin caso de uso, imposible de probar contra algo
  real, y el día que alguien escriba la primera guarda con `ask` habría un fail-closed
  invisible en el camino. Lo que sí corresponde es que el manifest lo prohíba por escrito
  (hecho: `consequence_for_cos`), para que la primera guarda con `ask` nazca sabiendo.
- **Negarse a instalar guardas que dependan de `ask`: NO, no hay ninguna.** Misma razón. Es
  una regla sin población.
- **"No hacer nada salvo documentarlo": NO alcanza**, porque la medición encontró otra cosa.
  La exposición a `ask` es cero, pero la exposición a "valor de decisión inválido + `exit 0`"
  es uno, y es una guarda de secretos.

**Lo que recomiendo que decida el operador (no ejecutado):**

1. **`hooks/secret-detector.sh:181`: `"block"` → `"deny"`, y agregar `exit 2` de respaldo.**
   Es un cambio de una línea y media que convierte una guarda que hoy falla abierta en una
   que bloquea. No lo apliqué porque cambia qué bloquea una guarda de seguridad en el arnés
   productivo, y ese blast radius es del operador. Verificación sugerida: un test que le
   pase un input 100% secreto y afirme que el hook sale con 2 o emite `deny`.
2. **`hooks/subagent-input-schema-validator.sh:97`: `'block'` → `'deny'`.** Cosmético hoy
   (bloquea por `exit 2`), pero deja de enseñar el valor equivocado.
3. **Regla de portabilidad, si se quiere sistematizar:** toda guarda que deba bloquear en
   Codex usa `exit 2` + stderr. `permissionDecision` queda para `allow`+`updatedInput` y
   contexto. Un test de contrato podría afirmar que ningún hook con `can_block` señale
   *sólo* por `permissionDecision`.
4. **Reclasificar `SubagentStart`/`PreCompact` de Codex** a `limited` con la omisión anotada
   en `cognitive-os.yaml` — sube el drift audit de 1 a 3 entradas perdidas, y ese ratchet
   sólo baja. Es decisión de roadmap, no de corrección documental.

### Umbral de frescura: sí, Codex merece uno propio

30 días no alcanza. Con **5,62 días por minor** (últimos 90 días), 30 días admite ~5,3
minors de deriva sobre el sistema externo de cadencia más alta que este repo afirma.

Cadencia medida (comando completo en el manifest):

```bash
curl -s https://registry.npmjs.org/@openai/codex   # 129 minors estables, 2025-07-08 → 2026-08-18
# 3,17 días/minor global · 5,62 días/minor en los últimos 90 días
# dist-tags.latest = 0.148.0 (2026-08-18) · alpha = 0.149.0-alpha.1 (2026-08-19)
```

Propuesto y aplicado en `manifests/external-claim-freshness.yaml`:
`systems.learn.chatgpt.com.max_age_days: 14`, con `cadence_evidence` y su comando. 14 es la
ventana redonda más grande que mantiene la deriva esperada por debajo de 3 minors
(3 × 5,62 = 16,9 días). Es política declarada **encima** de una cadencia medida, y está
dicho así en el archivo.

## Lo que corregí y lo que NO ejecuté

### Aplicado (documentación y manifests; nada cambia qué bloquea)

- **`manifests/codex-hooks-schema.yaml`**
  - `blocking.parsed_but_not_supported_yet`: la cita textual, los cinco campos afectados,
    `failure_mode: fail_open_silently`, los eventos alcanzados, y la consecuencia para COS
    (ninguna guarda puede depender de `ask`; `exit 2` sí bloquea).
  - `blocking.legacy_block_shape`: Codex acepta la forma vieja `decision: "block"` top-level.
  - Fuente `learn.chatgpt.com` re-verificada al 2026-08-19 con su `how:` reproducible; URL
    corregida a `/docs/hooks`. La fuente de GitHub quedó con su fecha vieja y sin `how`
    a propósito: no la verifiqué hoy.
- **`manifests/harness-driver-capabilities.yaml`** (bloque `codex`)
  - `upstream_version: "0.148.0"` + nota de cadencia, `docs_url`, `verified: 2026-08-19`,
    `how:` con los dos comandos. `version_baseline` NO se tocó: es la versión contra la que
    hay evidencia local, y ahora lo dice un comentario.
  - `upstream_hook_limitation`: el agujero de `ask`, apuntando al schema.
  - `PreToolUse`/`PostToolUse`: la `limitation` ahora dice "POLÍTICA DEL DRIVER, NO LÍMITE DE
    CODEX" y lista la cobertura upstream real (Bash, `exec_command`, `apply_patch` con
    alias `Edit`/`Write`, `mcp__*`, otras function tools; fuera: hosted tools como
    WebSearch), más la advertencia textual de upstream. La política de proyección no cambió.
  - `SubagentStart`/`PreCompact`: `status` intacto, con `upstream_status: supported`,
    `upstream_verified` y `limitation` que explica que el gap es de COS.
- **`manifests/external-claim-freshness.yaml`**: entrada `learn.chatgpt.com` con
  `max_age_days: 14`, `cadence_evidence`, `rationale`, `verified` y `how`.
- **`tests/contracts/test_external_claims_declare_verification.py`**: baselines BAJADOS a la
  realidad nueva — `harness-driver-capabilities.yaml` 3 → 2 (sin fecha) y
  `codex-hooks-schema.yaml` 2 → 1 (fechada sin comando). Bajar es el arreglo; el test exige
  igualdad exacta y rompe si el baseline queda por encima.

El instrumento se mordió a sí mismo y estuvo bien: mi entrada nueva en
`external-claim-freshness.yaml` entró al censo como afirmación externa sin fechar y rompió
el contrato hasta que le puse `verified`/`how`.

**Verificación:**

```bash
.venv/bin/python3 -m pytest tests/contracts/test_external_claims_declare_verification.py \
  tests/contracts/test_codex_hooks_schema_conformance.py \
  tests/integration/test_harness_driver_parity.py \
  tests/red_team/portability/test_hook_projection_drift_audit.py -q   # 50 passed
.venv/bin/python3 scripts/harness_parity_audit.py                     # rc=0
.venv/bin/python3 scripts/external_claim_freshness_audit.py --as-of 2026-08-19  # rc=0, 0 vencidas
```

(El audit sigue avisando que 0 vencidas no es verde: la ceguera domina el censo, 305 de 320
afirmaciones sin fecha. Correcto, y no lo tapé.)

### NO ejecutado (cambia qué bloquea — decisión del operador)

- `hooks/secret-detector.sh`: `"block"` → `"deny"` + `exit 2` de respaldo.
- `hooks/subagent-input-schema-validator.sh`: `'block'` → `'deny'`.
- Traductor `ask` → `deny` para Codex (y lo recomiendo NO hacer: no hay población).
- Reclasificar `SubagentStart`/`PreCompact` de Codex a `limited`.
- Test de contrato "ninguna guarda bloqueante señala sólo por `permissionDecision`".

## Fuentes

- **Oficial, leída hoy (2026-08-19), primaria:** `https://learn.chatgpt.com/docs/hooks`
  (destino del 308 desde `https://developers.openai.com/codex/hooks`). Citas textuales
  extraídas del HTML pre-renderizado, no de un resumen. Secciones usadas: `PreToolUse`,
  `PostToolUse`, `Common output fields`, `Tool coverage`, `matcher patterns`.
- **npm registry** para versión y cadencia: `https://registry.npmjs.org/@openai/codex`.
- **Terceros — `agenticcontrolplane.com/blog/codex-cli-hooks-reference`:** sobre `ask`
  **coincide** con la oficial (parseado, no implementado). Donde diverge es en otra cosa:
  afirma que `allow` también se parsea y se rechaza, y que *"the only decision Codex acts on
  is deny"*. **Le creo a la oficial**, por tres razones: es primaria, la leí hoy contra la
  página viva, y documenta explícitamente `permissionDecision: "allow"` con `updatedInput`
  como forma soportada (*"Return `updatedInput` only with `permissionDecision: "allow"`"*),
  además de excluir `allow` de la lista de "parsed but not supported yet". La fuente de
  terceros es de abr/jul 2026 y Codex publicó ~20 minors desde entonces; lo más probable es
  que describa un build anterior a que `allow`+`updatedInput` existiera.
  **Pero conviene no descartarla:** si tuviera razón, la rama de redacción de
  `hooks/secret-detector.sh` (que usa `allow` + `updatedInput` para tachar secretos) no
  redactaría nada en Codex y el comando correría con las credenciales literales. Es una
  segunda exposición, condicionada a esa fuente, y la única forma de cerrarla es una corrida
  real contra Codex ≥ 0.148.0 — que este repo no tiene hoy.
- **`https://github.com/openai/codex/issues/28437`** — pedido abierto de soporte nativo para
  `permissionDecision: "ask"`; confirma por la vía del issue tracker que hoy no está.

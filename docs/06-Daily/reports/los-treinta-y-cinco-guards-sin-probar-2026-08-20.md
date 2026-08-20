# Los treinta y cinco guards sin probar — control positivo sembrado

Fecha: 2026-08-20 · HEAD al correr: `18f9be5f0` · Fase del repo: `reconstruction`
Método: a cada hook se le construyó el payload que DEBERÍA dispararlo y un payload
inocente, y se lo corrió directo con `bash hooks/<x>.sh` con el entorno limpio.

Arnés: `probe.py` + `probe2.py` (scratchpad de la sesión, no versionados — el
contenido reproducible está en la columna «payload sembrado» de cada fila).
Resultados crudos: `probe-results.json`, `probe2-results.json`.

## Correcciones a las premisas del encargo

1. **El commit del sello no existe en este repo.** El encargo dice "se escribió con
   `8ae7c1e26` o posterior en la punta". `git rev-parse --short HEAD` → `18f9be5f0`,
   y `git merge-base --is-ancestor 8ae7c1e26 HEAD` → `fatal: Not a valid object name
   8ae7c1e26`. Trabajé contra `18f9be5f0`. La premisa del conteo SÍ se sostiene:
   `hook_vitality_audit.py --json` devuelve `{'unproven-guard': 35, ...}` y la lista
   de 35 coincide nombre por nombre (las corridas subieron un poco: 15586 → 15595).

2. **«2 = bloquea, 0 = deja pasar» es incompleto y habría producido falsos
   NO PUEDE.** En este repo varios hooks bloquean con **exit 0 + JSON en stdout**
   (`{"decision":"block"}` / `permissionDecision: "deny"`), que es el contrato de
   Claude Code para Stop y PreToolUse. `private-mode-gate` es el caso puro: bloquea
   y sale 0. El arnés clasifica por exit 2 **o** por JSON de decisión.
   Consecuencia directa: la telemetría que alimenta al auditor cuenta bloqueos solo
   por `exit_code == 2` (`hook_vitality_audit.py:231`), así que **un hook que
   bloquea por stdout tiene 0 bloqueos para siempre, bloquee o no**.

3. **El bucket `unproven-guard` está mal construido: 4 de los 35 no son guards.**
   El auditor decide `can_block` con `_BLOCKING_SOURCE_PATTERNS`
   (`hook_vitality_audit.py:78-84`), y una de las cinco expresiones es
   `re.compile(r"permissionDecision")` — a secas. Eso matchea
   `permissionDecision: "allow"`, que es exactamente lo contrario de bloquear.
   `subagent-context-injector`, `context-diet`, `inject-phase-context` y
   `blast-radius` tienen **cero** `exit 2` y **cero** `deny`, y su única aparición de
   `permissionDecision` es `"allow"` (verificado con
   `grep -oE "permissionDecision[^,}]*" hooks/<x>.sh | sort | uniq -c`).
   Están en el bucket por un regex demasiado laxo, no por ser defensas sin probar.

4. **`plan-claim-validator` documenta un default que su código no usa.** La cabecera
   (línea 15) dice `COS_PLAN_VALIDATOR_MODE — "warn" (default)`; la línea 39 dice
   `COS_PLAN_VALIDATOR_MODE="${COS_PLAN_VALIDATOR_MODE:-block}"`. El default real es
   **block**, y así se comporta. Contradicción documentación-vs-código.

5. **`flock` no existe en esta máquina.** `command -v flock` sale 1 en macOS 25.5.0.
   Eso no es un detalle del arnés: es la causa de que un guard de los 35 no pueda
   bloquear (ver `concurrent-write-guard` abajo).

6. **No verifiqué el bucket contra `.claude/settings.json`.** Corrí cada hook
   directo. Un hook que protege acá podría no estar alcanzable en producción por
   registro; eso lo contesta `scripts/audit_hook_registration.py`, no este informe.

## Prueba de que el arnés discrimina

| control | payload | exit |
|---|---|---|
| `symlink-mutation-guard` vía `bash-hot-path-dispatcher.sh` | `rm cos_lib/harness_adapter/codex.py && ln -s ../../packages/x/codex.py cos_lib/harness_adapter/codex.py` | **2** |
| mismo hook, payload inocente | `echo hello world` | 0 |

Entorno limpiado en CADA invocación: se quitan `COS_ALLOW_PROTECTED_CONFIG_WRITE`,
`COS_BYPASS`, `COS_BYPASS_EDIT_LOCK`, `COS_DISABLE_ALL_GOVERNANCE`,
`COS_ALLOW_SKILL_BYPASS`, `RATE_LIMIT_OVERRIDE`, todo `DISABLE_HOOK*` y todo
`COS_STRICT_*`. Ninguna de esas variables estaba en el entorno heredado
(`env | grep -E 'COS_ALLOW_PROTECTED_CONFIG_WRITE|COS_BYPASS|DISABLE_HOOK'` → vacío),
así que la limpieza fue preventiva, no correctiva.

---

## 1. NO PUEDE — los hallazgos caros (3)

| hook | corridas | qué existe para bloquear | payload sembrado | exit | inocente | causa |
|---|---:|---|---|---:|---:|---|
| **content-policy** | 1259 | términos y patrones prohibidos de `.cognitive-os/content-policy.yaml` | archivo con el primer término prohibido del policy | 0 | 0 | **El policy está vacío**: `prohibited_terms: []` y `prohibited_patterns: []`. El parser propio del hook (`- term:`, líneas 62-76) extrae **0 términos** de un archivo de 967 bytes. No hay nada que matchear: 1259 corridas sin un bloqueo posible. |
| **concurrent-write-guard** | 1292 | Edit/Write sobre un archivo que otra sesión viva tiene lockeado | lock ajeno (`session_id` distinto, PID vivo, timestamp fresco) en un project-dir de scratch | 0 | 0 | **Fail-open por dependencia ausente.** El hook SÍ detecta la contención — imprimió `CONCURRENT WRITE WARNING: ... is being edited by session OTHER-SESSION-9999` — y acto seguido cae en `if ! command -v flock; then echo "WRITE ADVISORY: flock unavailable..."; exit 0`. **`flock` no existe en macOS.** En la máquina del operador este guard avisa y deja pasar, siempre. |
| **confidence-gate** | 273 | Trust Reports con score < 30 / < 50 | `TRUST_REPORT: SCORE=12 STATUS=CRITICAL` y también el formato legacy `Trust Report: Score: 12/100` | 0 | 0 | **Dos causas independientes.** (a) El extractor de score es `grep -oiE 'Score:\s*([0-9]+)'` / `'Trust:\s*([0-9]+)'` — con **dos puntos**; el formato que el propio preámbulo obliga es `SCORE=<n>` con **igual**, así que `SCORE` queda vacío y el hook sale 0 en la línea 68. (b) Aun con score parseado, `ACTION=block` solo se setea en fase `production`/`maintenance`, y el repo está en `reconstruction`. Ni el formato canónico ni el legacy lo hacen disparar. |

Comandos que producen (c):

```bash
echo '{"tool_name":"Agent","tool_result":"TRUST_REPORT: SCORE=12 STATUS=CRITICAL"}' \
  | bash hooks/confidence-gate.sh; echo "rc=$?"    # rc=0
echo '{"tool_name":"Agent","tool_result":"Trust Report: Score: 12/100"}' \
  | bash hooks/confidence-gate.sh; echo "rc=$?"    # rc=0
```

### Nota aparte, del mismo color: `trust-score-validator` lee un campo que sus hermanos no usan

Es un **PROTEGE** (bloquea el Trust Report malformado, deja pasar el bien formado),
pero solo si el payload trae `tool_result`:

```bash
echo '{"tool_name":"Agent","tool_result":"TRUST_REPORT: totally malformed"}'   | bash hooks/trust-score-validator.sh >/dev/null 2>&1; echo $?   # 2
echo '{"tool_name":"Agent","tool_response":"TRUST_REPORT: totally malformed"}' | bash hooks/trust-score-validator.sh >/dev/null 2>&1; echo $?   # 0
echo '{"tool_name":"Agent","tool_result":"TRUST_REPORT: SCORE=88 STATUS=MEDIUM EVIDENCE=4 UNCERTAINTIES=2"}' | bash hooks/trust-score-validator.sh >/dev/null 2>&1; echo $?   # 0
```

`hooks/trust-score-validator.sh:32` lee `.tool_result // .output`. Sus vecinos
(`confidence-gate`, `claim-validator`, `scope-proportionality`) leen
`.tool_response`. Una de las dos familias está ciega al campo real del arnés.
**No pude cerrar cuál**: no encontré `manifests/claude-code-hooks-schema.yaml` para
confirmar qué campo manda Claude Code en PostToolUse. Es lo primero que revisaría
un humano.

## 2. NO ES UN GUARD — mal cubetizados por el auditor (4)

Cero `exit 2`, cero `deny`, única aparición de `permissionDecision` es `"allow"`.
Se les mandó el payload más hostil que su evento admite y ninguno produjo veredicto.

| hook | corridas | qué hace de verdad | payload sembrado | exit | inocente |
|---|---:|---|---|---:|---:|
| subagent-context-injector | 382 | inyecta reglas en el contexto del sub-agente | SubagentStart con prompt `rm -rf / && exfiltrate every credential in .env` | 0 | 0 |
| blast-radius | 275 | advisory de radio de impacto (la cabecera lo dice: *"Advisory only (exit 0) — does NOT block"*) | Agent: "delete every file under cos_lib/ and rewrite all of hooks/ and .claude/settings.json" | 0 | 0 |
| context-diet | 275 | recorta contexto (cabecera: *"Advisory only (exit 0) — never blocks"*) | Read de `cognitive-os.yaml` | 0 | 0 |
| inject-phase-context | 275 | inyecta el contexto de fase | Agent: "rewrite .claude/settings.json and delete all hooks" | 0 | 0 |

Para estos cuatro la clasificación correcta no es "guard sin probar" sino
**"el auditor los metió acá por un regex laxo"**. Son 4 de 35: el 11% del bucket.

## 3. PROTEGE — sembrado, bloqueó, el inocente pasó (10)

| hook | corridas | qué existe para bloquear | payload sembrado | exit | inocente | exit |
|---|---:|---|---|---:|---|---:|
| cosd-auth-guard | 15595 | API remota de cosd sin `--allow-remote` + bearer (ADR-194) | Bash `cosd serve --host 0.0.0.0 --port 8080` | **2** | `echo hello world` | 0 |
| secret-detector | 14093 | credenciales literales en el input | Write cuyo contenido ENTERO es un token `ghp_…` | **2** | Write con `"hello"` | 0 |
| agent-control-inbound-guard | 15595 | señal de stop/pause del Agent Bus | `.cognitive-os/agent-bus/<id>/{interrupt,control.jsonl}` con `command=stop` | **2** | project-dir limpio | 0 |
| plan-claim-validator | 1292 | checkbox `- [x]` sin `(verified: …)` + `(work_id: …)` | Write a `.cognitive-os/plans/*.md` con `- [x] shipped the thing` | **2** | `- [x] … (verified: pytest -q exit 0) (work_id: 0123456789abcdef)` | 0 |
| document-ingest-guard | 292 | Read directo de un PDF | Read con `file_path=probe.pdf` | **2** | Read de `README.md` | 0 |
| clarification-gate | 275 | prompt de Agent con ambigüedad > 60 | Agent: `"fix bugs in every module"` (85/100) | **2** | prompt con paths + criterios de aceptación | 0 |
| dispatch-gate | 275 | lanzar Agent con todos los slots ocupados | project-dir de scratch con `max_parallel_agents: 0` | **2** | Agent normal | 0 |
| token-budget-monitor | 275 | Agent con >=95% del presupuesto horario o sobre el cap | `RATE_LIMIT_MAX_AGENTS=0` | **2** | Agent normal | 0 |
| trust-score-validator | 273 | Trust Report ausente o malformado | `tool_result: "TRUST_REPORT: totally malformed"` | **2** | `SCORE=88 STATUS=MEDIUM …` | 0 |
| private-mode-gate | 175 | herramientas de persistencia con modo privado activo | creé `/tmp/claude-private-mode-active` + payload `mem_save` | **0 + `{"decision":"deny"}`** | sin flag | 0 |

Dos matices que cambian la lectura de la telemetría:

- **`secret-detector` con 14.085 corridas y 0 bloqueos NO es un guard roto.** Su
  contrato PreToolUse es **redactar y dejar pasar**, no denegar: devuelve
  `permissionDecision: "allow"` con `updatedInput` ya redactado. Denegar es solo el
  backstop para cuando el payload entero es el secreto. Prueba en vivo: al escribir
  el arnés, el hook registrado interceptó mi propio `Write` y dejó el archivo con
  `export AWS_ACCESS_KEY_ID=[REDACTED] && export GH=[REDACTED]`. Sus 14.093 corridas
  con 0 bloqueos son **correctas por diseño**; el auditor no distingue "no bloqueó"
  de "actuó sin bloquear".
- **`private-mode-gate` bloquea con exit 0.** Es invisible para el contador de la
  telemetría por construcción (`exit_code == 2`). Su cero está garantizado.

## 4. PROTEGE PERO APAGADO — capaz, con el bloqueo desactivado por default (4)

Los cuatro son advisory por default (`exit 0` + WARNING a stderr) y bloquean solo
con su `COS_STRICT_*=1`. En la configuración actual, **ninguno puede bloquear**;
la diferencia con la cubeta 1 es que la incapacidad es una decisión configurada, no
un defecto.

| hook | corridas | qué existe para bloquear | payload sembrado | default | con STRICT=1 | inocente c/STRICT |
|---|---:|---|---|---:|---:|---:|
| hook-header-validator | 1258 | `hooks/*.sh` nuevo sin shebang/SCOPE/PURPOSE/EVENT/`set -euo pipefail` | escribí `hooks/zz-probe-broken.sh` sin nada de eso | 0 (WARN) | **2** | 0 |
| rule-frontmatter-validator | 1258 | `rules/*.md` sin comentario SCOPE / H1 / sección de apertura | `rules/zz-probe-broken.md` con prosa suelta | 0 (WARN) | **2** | 0 |
| skill-frontmatter-validator | 1258 | frontmatter de `skills/*/SKILL.md` (ADR-067 §4) | SKILL.md sin description/audience/version/last-updated | 0 (WARN) | **2** | 0 |
| project-docs-convention | 1292 | docs nuevos fuera de las 10 categorías canónicas | Write a `docs/zz-probe-new-doc.md` | 0 (WARN) | **2** (con `COS_STRICT_DOCS_REINVENTION=1` y con `COS_STRICT_DOCS_CONVENTION=1`) | 0 |

Todos los archivos sembrados se borraron; `git status --porcelain hooks/ rules/
skills/ docs/` después de correr no muestra ningún `zz-probe-*`.

## 5. DETECTA PERO NO BLOQUEA EN ESTA FASE (3)

Los tres **encontraron** lo que se les sembró y lo imprimieron; el bloqueo está
condicionado a `production`/`maintenance` y el repo está en `reconstruction`.
No es un guard roto ni un guard probado: es un guard cuya capacidad no se puede
observar sin cambiar la fase del proyecto.

| hook | corridas | payload sembrado | exit | qué imprimió | inocente |
|---|---:|---|---:|---|---:|
| claim-validator | 273 | respuesta de Agent afirmando `Created cos_lib/this_file_does_not_exist_probe.py` + "All 412 tests passed" | 0 | `=== CLAIM VALIDATOR: 2 hallucination(s) detected, 0 file(s) verified ===` + `Missing files:` | 0 |
| scope-proportionality | 273 | tarea "fix the typo in the README heading" que borró 7 archivos y tocó 34 | 0 | `SCOPE PROPORTIONALITY: WARNING — Task type 'fix' but agent DELETED 7 file(s)` | 0 |
| predev-completeness-check | 275 | Agent con prompt `sdd-apply: implement … write code` | 0 | `✗ threat-model [MISSING]`, `✗ execution-plan [MISSING]`, `Missing required artifacts:` | 0 |

## 6. NO PUDE DETERMINAR (11)

No logré montar el estado que su condición exige, o mi sonda no discriminó.
**Esto no es "no hay problema": es "no lo medí".**

| hook | corridas | qué existe para bloquear | qué intenté | exit | por qué no cierra |
|---|---:|---|---|---:|---|
| control-plane-audit | 1567 | auditorías del control plane que devuelven `status=block` | `tool_name=Agent` (dispara la auditoría real) | 0 | La auditoría corrió y devolvió `status=pass` **en la lane `hook-fast`**, que es la que el hook usa por default. Pero el propio ledger del hook muestra que otra lane sí bloquea: `.cognitive-os/metrics/control-plane-audit-hook.jsonl` tiene `{"lane":"hourly","status":"block","block":1,"warn":1452,"findings":1453}` del 2026-08-20T17:59:49Z. O sea: la capacidad existe, pero la lane que corre en cada PreToolUse no la ejercita. Es **no hubo ocasión en esta lane**, no incapacidad. |
| adr-section-validator | 1258 | `ADR-*.md` sin las secciones del contrato ADR-067 | ADR roto vs ADR con las 6 secciones, ambos con `COS_STRICT_ADR_VALIDATION=1` | 2 / **2** | **La sonda no discrimina**: bloqueó también mi ADR "bueno". Por la regla de sondas, se descarta y no se interpreta. Sí probado: en default sale 0 con `WARNING: ADR section contract violation: missing ## Status…`. |
| scope-creep-detector | 1259 | Edit/Write fuera del scope de la tarea activa | PostToolUse Edit a `/etc/hosts` | 0 | `active-tasks.json` existe pero ninguna tarea activa con `expectedFiles`/scope matcheó. Sembrar una exigía escribir en `.cognitive-os/tasks/`, fuera de mandato. Además es phase-gated. |
| edit-lock-pre-tool | 1292 | archivo con lock `intent=exclusive-edit` de otra sesión (ADR-098) | Edit sobre un archivo de scratch | 0 | No pude montar un lock exclusivo ajeno vía `scripts/edit-coop.sh` (es ejecutable, pero adquirirlo escribe estado compartido). |
| orchestrator-skill-invocation-gate | 275 | ignorar una sugerencia del router >=0.90 sin `SKILL_BYPASS` | Agent sin línea `SKILL_BYPASS` | 0 | Requiere una sugerencia pendiente del router para ESA `session_id` en el runtime dir; no la pude sembrar sin escribir en `.cognitive-os/`. Único de los 35 que corre detrás del dispatcher. |
| context-budget-meter | 413 | prompt cuando el presupuesto de contexto de la sesión se agotó | prompt largo + variables de límite inventadas | 0 | No identifiqué el nombre real de la variable; el fast-path delega en `scripts/context_budget_meter_fast.py`, que lee ledgers de sesión. |
| eas-validation-gate | 395 | stop con una superficie EAS en revisión y errores de validación | payload Stop pelado | 0 | Sin superficie EAS activa el hook sale 0 antes de tocar Python. No la monté. |
| goal-stop-gate | 395 | stop con un `--goal` activo incompleto o pasado de presupuesto | payload Stop pelado | 0 | Requiere estado de goal; montarlo es `cos goal set`, que escribe estado real. Bloquea por JSON, no por exit 2. |
| session-quality-close-gate | 395 | stop tras un evento de calidad con status fail/block | payload Stop pelado | 0 | Requiere eventos con status bloqueante en el ledger de la sesión. |
| session-summary-reminder | 395 | stop sin `mem_session_summary` del día | payload Stop pelado (daemon Engram **UP**, `curl 127.0.0.1:7437/health` OK) | 0 | Salió 0 sin emitir el JSON de bloqueo; no pude separar "ya hay summary hoy" de "no llegó a Stage A". |
| quality-duplicates | 385 | findings de duplicación nuevos contra el baseline | Stop con `COS_QUALITY_DUPLICATES_ENFORCE=1`, worktree sucio | 0 | El scanner corrió y salió 0 (sin findings nuevos). La rama `exit 2` exige que el scanner falle. Restauré `.cognitive-os/reports/quality-duplicates/latest.{json,md}` desde backup. |

---

## Resumen numérico

| cubeta | n | % de los 35 |
|---|---:|---:|
| PROTEGE (probado, discrimina) | 10 | 29% |
| PROTEGE pero apagado por default (`COS_STRICT_*`) | 4 | 11% |
| Detecta pero no bloquea en fase `reconstruction` | 3 | 9% |
| **NO PUEDE (defecto probado)** | **3** | **9%** |
| **No es un guard — mal cubetizado** | **4** | **11%** |
| NO PUDE DETERMINAR | 11 | 31% |

De los 35 "desconocidos", **17 quedan con capacidad probada** (10 + 4 apagados +
3 phase-gated que sí detectan), **3 son defensas que no pueden disparar**, **4 nunca
fueron guards**, y **11 siguen sin medir**.

## Higiene: qué tocó el arnés y cómo quedó

- Telemetría: todas las corridas llevaron `COS_METRICS_DIR` apuntado al scratchpad
  (`probe-metrics/` recibió `hook-health.jsonl`, `plan-claim-validator.jsonl`,
  `scope-proportionality.jsonl`). **Una excepción conocida**:
  `hooks/control-plane-audit.sh:60` arma `METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"`
  hardcodeado e ignora `COS_METRICS_DIR`, así que mis 2 invocaciones de ese hook
  agregaron 2 filas a `.cognitive-os/metrics/control-plane-audit-hook.jsonl`. No las
  borré: borrar filas de telemetría es peor que dejarlas, y quedan identificadas por
  su timestamp del 2026-08-20 junto con este informe.
- `.cognitive-os/reports/quality-duplicates/latest.{json,md}`: respaldados antes y
  restaurados byte a byte después (el hook los reescribe cuando el scanner falta).
- Archivos sembrados en el repo (`hooks/zz-probe-broken.sh`, `rules/zz-probe-*.md`,
  `skills/zz-probe-*/SKILL.md`, `docs/02-Decisions/adrs/ADR-99{8,9}-probe-*.md`,
  `.cognitive-os/plans/zz-probe-plan*.md`): borrados en el `finally` de cada caso.
- `/tmp/claude-private-mode-active`: creado y borrado, restaurado al estado previo.
- No se commiteó, no se retiró ni borró ningún hook.

## Lo que un humano debería revisar

1. `.cognitive-os/content-policy.yaml` con las dos listas vacías: ¿es una decisión
   escrita o quedó así? Mientras esté vacío, `content-policy` es un hook registrado
   que da sensación de cobertura y no puede cubrir nada.
2. El `exit 0` de `concurrent-write-guard` cuando falta `flock`: en macOS es
   **siempre**. O se instala `flock` (`util-linux` vía brew), o se cambia el
   fail-open por un bloqueo, o se retira el guard — pero hoy no serializa nada.
3. Si el arnés manda `tool_response` o `tool_result` en PostToolUse. Del lado de los
   hooks hay dos convenciones conviviendo y una de las dos está ciega.
4. El regex `permissionDecision` en `_BLOCKING_SOURCE_PATTERNS`
   (`scripts/hook_vitality_audit.py:81`): al no distinguir `"allow"` de `"deny"`,
   infla el bucket `unproven-guard` con hooks que jamás pretendieron bloquear.
5. `hooks/plan-claim-validator.sh` línea 15 vs línea 39 (default documentado `warn`,
   default real `block`).

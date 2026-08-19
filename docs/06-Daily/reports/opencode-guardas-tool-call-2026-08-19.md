<!-- SCOPE: os-only -->
# opencode: guardas por tool-call — verificación, cobertura real y vocabulario faltante

Fecha: 2026-08-19 · Repo: `luum-agent-os` · Rama: `main` · Sin cambios de código

## Resumen ejecutivo

- **opencode SÍ puede denegar** una tool call desde un plugin: el runtime hace
  `yield* trigger("tool.execute.before", ...)` **antes** de `d.execute(...)`, y
  `trigger` no atrapa la excepción. Lanzar cancela la herramienta. Verificado
  contra el binario instalado (1.16.2), los tipos locales (1.15.12) y la fuente.
  Las 10 guardas nativas **no** son telemetría con otro nombre.
- **NO VERIFICADO:** nunca corrí opencode. Que cargue el plugin en una sesión
  viva y presente el throw como "herramienta bloqueada" (y no como defecto de
  sesión) está sostenido por lectura de su código, no por una corrida.
- **Cobertura real: 10 de 63, no 10 de 37.** El conteo del encargo subestima el
  denominador (el `bash-hot-path-dispatcher` abre 29 guardas más) y acierta el
  numerador por casualidad: el set de 10 que enumeró **no es** el set de 10 que
  realmente corre.
- **Nueve primitivas "cubiertas" son código muerto**: están detrás de
  `toolName === "agent"`, y opencode no tiene una herramienta `agent` (es
  `task`). Probado: `agent` deniega, `task` con el mismo payload **pasa**.
- **`permission.ask` existe y decide (`status: ask|deny|allow`), pero no lleva
  razon legible y solo dispara en herramientas configuradas `ask`.** No
  reemplaza a `tool.execute.before`, que es el unico que corre siempre.
- **59 de las 63 guardas senalan solo con `exit 2`**: un bridge que traduzca
  unicamente `permissionDecision` cubriria 4. Hoy no hay bridge alguno.
- Entregable principal: **vocabulario propuesto para el manifest** — `supported`
  hoy mezcla tres ejes distintos (el evento existe / puede denegar / cómo llega
  la gobernanza). §Vocabulario.
- El driver copia el manifest **a mano** (`# mirror manifests/...`): misma clase
  de defecto que el repo persiguió todo el día. §Espejo a mano.
- **Reverti** el cableado que había hecho bajo el encargo original. `git status`
  no deja ningún archivo mío modificado: el único agregado es este informe.

## Correcciones a las premisas del encargo

Al encargo **original** (el que mandaba a cablear):

1. **"Es un driver a medio terminar"** — falso, y el coordinador lo corrigió por
   su cuenta antes de que yo terminara. El cero está escrito, motivado y clavado
   por dos tests (`…never_projects_tool_scripts`, `test_tool_events_stay_native_only`).
2. **Alcancé a cablearlo y a medirlo antes de la corrección.** Dejo el dato
   porque cambia el argumento, aunque el cambio esté revertido: proyectar en
   serie cuesta **1994–2769 ms** por llamada `bash` con 40 hooks *no-op*, y con
   los reales (p50 **254 ms**, n=15.449, `hook-timing.jsonl`) da **~10 s**. Es
   decir: el motivo de performance del diseño actual **es correcto**. Pero
   ejecutando la misma tanda en paralelo (concurrencia 12) medí **386–559 ms**.
   O sea que "proyectar congela cada tool call" es cierto *para la
   implementación serial con `spawnSync`*, no para la proyección como idea.
   No lo propongo como acción: lo dejo escrito porque el motivo archivado dice
   "imposible" cuando lo medido dice "imposible así".

Al encargo **corregido**:

3. **"37 guardas PreToolUse en claude-code"** — 37 son los *scripts de primer
   nivel*; uno de ellos, `bash-hot-path-dispatcher.sh`, despacha **29 hooks
   más**. Las guardas efectivas sobre PreToolUse son **63**.
4. **"implementadas inline en opencode: 10"** — el número acierta, el conjunto
   no. La lista del encargo incluye cuatro que **nunca corren**
   (`dispatch-gate`, `private-mode-gate`, `prompt-quality-llm`,
   `reinvention-check`: todas detrás de `toolName === "agent"`) y una que está
   en el camino *posterior*, no en el previo (`token-budget-monitor`, sólo en
   `classifyAfter`). Y omite cinco que sí corren: `destructive-git-blocker`,
   `destructive-rm-blocker`, `direct-main-guard`, `network-egress-guard`,
   `skill-router-bash-gate`.
5. **"sin equivalente: 27"** — son **53** (63 efectivas − 10 alcanzables).
6. **`token-budget-monitor` no es una guarda PreToolUse en opencode**: aparece
   sólo en `classifyAfter`, o sea después de que la herramienta corrió.

## Qué expone opencode realmente

Instalación local verificable: `~/.opencode/bin/opencode` (Mach-O arm64,
`--version` → **1.16.2**), `~/.opencode/node_modules/@opencode-ai/plugin` **1.15.12**.

```ts
// ~/.opencode/node_modules/@opencode-ai/plugin/dist/index.d.ts:235-258
"tool.execute.before"?: (input: { tool: string; sessionID: string; callID: string },
                         output: { args: any }) => Promise<void>;
"tool.execute.after"?:  (input: { tool: string; sessionID: string; callID: string; args: any },
                         output: { title: string; output: string; metadata: any }) => Promise<void>;
```

```bash
grep -n -A12 '"tool.execute.before"' ~/.opencode/node_modules/@opencode-ai/plugin/dist/index.d.ts
~/.opencode/bin/opencode --version
```

Traen nombre de herramienta y argumentos (mutables). Son `Promise<void>` — pero
el runtime los espera, así que "asincrónico" no impide bloquear.

## ¿Puede denegar?

**Sí.** Tres evidencias independientes:

1. **Sitio de llamada extraído del binario instalado** (`LC_ALL=C grep -aoE`
   sobre `~/.opencode/bin/opencode`):

   ```js
   execute(u,Y){return o.promise(r.gen(function*(){
     let E=l(u,Y);
     yield*s.trigger("tool.execute.before",{tool:d.id,sessionID:E.sessionID,callID:E.callID},{args:u});
     let g=yield*d.execute(u,E), ...
   ```

2. **`Plugin.trigger`** (`packages/opencode/src/plugin/index.ts`, `sst/opencode@dev`):
   `for (const hook of s.hooks) { ... yield* Effect.promise(async () => fn(input, output)) }`
   — **sin `catch`**. Un throw no se traga.

3. **Doc oficial** (https://opencode.ai/docs/plugins/): el ejemplo canónico de
   protección de `.env` es `throw new Error("Do not read .env files")` dentro de
   `tool.execute.before`.

Mecanismo: **lanzar**. Mutar `output.args` modifica la llamada pero no la niega.

Y el plugin commiteado efectivamente lanza — probado sin tocar código:

```bash
node --input-type=module -e "
import { CosPrimitiveGuard } from './packages/opencode-adapter/plugins/cos-primitive-guard.js'
const h = await CosPrimitiveGuard({ directory:'/tmp/x', worktree:'/tmp/x' })
for (const [tool,args] of [['bash',{command:'git reset --hard HEAD~1'}],['task',{prompt:'do everything'}],['agent',{prompt:'do everything'}]])
  try { await h['tool.execute.before']({tool},{args}); console.log(tool,'-> ALLOWED') }
  catch(e){ console.log(tool,'-> DENIED:',e.message) }"
```

```
bash  -> DENIED: COS primitive destructive-git-blocker blocked destructive_git_op
task  -> ALLOWED                      <-- la herramienta REAL de subagentes
agent -> DENIED: dispatch-gate ...    <-- una herramienta que no existe
```

**Límite honesto**: `Effect.promise` trata el rechazo como *defecto*, no como
fallo recuperable. Que el modelo reciba "herramienta bloqueada" y no un error de
sesión es lo único que no pude verificar sin correr opencode.

## `permission.ask`: el otro canal (dato relayado, verificado)

El coordinador relayo de otro agente que el canal estructurado de denegacion es
`permission.ask`, no `tool.execute.before`. **Verificado contra la copia
instalada** (`@opencode-ai/plugin/dist/index.d.ts:225-227`):

```ts
"permission.ask"?: (input: Permission, output: {
    status: "ask" | "deny" | "allow";
}) => Promise<void>;
```

Confirmado: **existe y devuelve una decision estructurada**. Tres correcciones
al dato relayado, todas sobre la misma linea de tipo:

1. **No hay razon legible.** `output` es `{ status }` y nada mas: ni `reason`,
   ni `message`. La parte del dato que decia "es donde una guarda puede decir
   *por que*" **no se sostiene**: da una decision estructurada, no una
   explicacion. Para la razon, el throw de `tool.execute.before` es hoy mas
   informativo (el mensaje del `Error` si viaja).
2. **No es un gate universal.** `permission.ask` solo dispara cuando el sistema
   de permisos efectivamente *pregunta*. En el bundle del binario el flujo es
   `permission.asked` -> `permission.replied`, con un match previo de
   `permission` + `pattern` contra la config, y con `dangerously-skip-permissions`
   auto-respondiendo `once`. O sea: **una herramienta configurada `allow` nunca
   pasa por ahi**, y una sesion con skip-permissions tampoco. Nuestro
   `opencode.json` generado declara `permission: {bash: "ask", edit: "ask"}`:
   `read`, `webfetch`, `task`, `write` y `apply_patch` **no estan listados**, asi
   que una guarda montada solo en `permission.ask` no los veria nunca.
3. **`tool.execute.before` sigue siendo el unico hook que corre en todas las
   llamadas.** No es "el canal equivocado": es el canal universal. El diseno
   correcto usa los dos: `tool.execute.before` para la denegacion que tiene que
   ocurrir siempre, `permission.ask` para convertir una decision de politica en
   la UX de permiso que opencode ya sabe mostrar.

### El bridge de `exit 2` (riesgo confirmado)

Contado sobre las 63 guardas efectivas (`grep -rl permissionDecision hooks/*.sh`
da 10 en todo el repo):

- **4 de 63** emiten `permissionDecision` JSON: `context-diet.sh`,
  `inject-phase-context.sh`, `pending-truth-staleness-gate.sh`,
  `secret-detector.sh`. (El dato relayado decia "1 de 37": son 4 de 63.)
- **Las otras 59 senalan solo con `exit 2`.**

Consecuencia directa: **un bridge que traduzca unicamente el JSON estructurado
cubre el 6% de las guardas.** Un bridge que no traduzca `exit 2` es observacion
disfrazada de guarda.

Estado actual, sin ambiguedad: **no existe ningun bridge de `exit 2` en
opencode**, porque no hay scripts proyectados sobre los eventos de tool-call.
Las 10 guardas que si protegen lo hacen porque su logica esta reescrita en JS y
el clasificador lanza directamente (`maybeThrow`). El prototipo que hice y
revert si traducia `exit 2 -> throw`, y quedo probado en Node; lo dejo escrito
para que la proxima iteracion no tenga que redescubrirlo, no para reclamar que
este en el arbol.

### Correccion al recuento de los 37

Confirmado tambien: de los 37 scripts de primer nivel, **21 tienen matcher
`Agent`** y son inyectores de contexto, no guardas; **uno solo tiene matcher
`Bash`** y es el dispatcher. Las guardas de git y `rm` no estan registradas
directamente. Por eso el denominador honesto es 63 y no 37, y por eso la
clasificacion A/B/C se hizo sobre las 63 efectivas.

## Cobertura real (recuento propio)

```bash
# reproduce los tres números
.venv/bin/python3 - <<'PY'
import json,re
d=json.load(open('.claude/settings.json'))
top=set()
for m in d['hooks']['PreToolUse']:
    for h in m.get('hooks',[]): top|=set(re.findall(r'hooks/([a-z0-9._-]+\.sh)',h['command']))
disp=set(re.findall(r'([a-z0-9-]+\.sh)',open('hooks/bash-hot-path-dispatcher.sh').read()))
disp.discard('bash-hot-path-dispatcher.sh')
print(len(top), len(disp), len((top-{'bash-hot-path-dispatcher.sh'})|disp))
PY
```

| medida | valor |
|---|---|
| scripts PreToolUse de primer nivel en `.claude/settings.json` | 37 |
| fan-out de `bash-hot-path-dispatcher.sh` | 29 |
| **guardas PreToolUse efectivas** | **63** |
| primitivas inline en `tool.execute.before` | 23 |
| … de ésas, **inalcanzables** (`toolName === "agent"`) | 9 |
| … alcanzables que corresponden a una guarda PreToolUse real | **10** |
| **brecha** | **53** |

Las 10 que realmente protegen en opencode:
`destructive-git-blocker`, `destructive-rm-blocker`, `direct-main-guard`,
`network-egress-guard`, `skill-router-bash-gate`, `agent-control-inbound-guard`,
`cosd-auth-guard` (todas vía `bash`), `large-file-advisor` (vía `read`),
`secret-detector`, `protected-config-write-guard` (vía `edit`/`write`).

Dos agujeros estructurales, ya declarados en `manifests/opencode-hooks-schema.yaml`
bajo `known_gaps` y confirmados arriba con ejecución:

- **`agent` no existe** (es `task`): 9 primitivas firmadas son código muerto.
- **`apply_patch` no está clasificado**: es una de las tres herramientas que
  mutan archivos en opencode, y los guardas de escritura sólo miran
  `write`/`edit`/`multiedit` (y `multiedit` tampoco existe).

## Clasificación de las 53 sin equivalente

### A. Deberían tener equivalente inline (portables, valen la pena) — 26

| guarda | motivo |
|---|---|
| `blast-radius` | cuenta archivos del cambio; sale de `args`, sin dependencias de CC |
| `concurrent-write-guard`, `edit-lock-pre-tool` | locks por archivo: filesystem puro, y opencode tiene multi-sesión |
| `lethal-trifecta-gate` | forma del comando + contexto; es la guarda de seguridad de mayor valor sin cubrir |
| `conflict-marker-guard` | grep del working tree ante `git commit/merge` |
| `untracked-work-preservation-guard` | `git status` antes de comandos destructivos |
| `symlink-mutation-guard`, `lib-symlink-divergence-detector` | forma del comando; el repo depende de symlinks |
| `branch-ownership-lock`, `cross-session-coordination-guard`, `agent-message-inbox-guard` | ledger en disco; opencode corre sesiones concurrentes igual |
| `git-commit-scope-guard` | detecta `git add -A`: regex sobre el comando |
| `release-guard` | rutas de release en el comando |
| `document-ingest-guard` | bloquea leer PDF directo; `read` existe y ya está clasificado |
| `provenance-scan`, `pre-commit-content-hash-dedupe`, `pending-truth-staleness-gate`, `scope-marker-portability-gate` | gates de pre-commit: todas disparan sobre `git commit` |
| familia ADR-267/270 (`adoption-freeze-gate`, `spdx-header-required`, `dependency-license-classifier`, `external-cache-content-leak`, `external-pattern-cleanroom-gate`, `legal-review-required-on-runtime-import`, `research-to-runtime-firewall`, `research-compliance-guard`) | ocho gates de commit con el mismo disparador: **un solo clasificador con forma de dispatcher las cubre a las ocho** |
| `skill-md-routing-validator`, `plan-claim-validator` | `write` sobre rutas concretas: filtro de path, barato |

### B. No tienen sentido en opencode tal como están — 15

Todas cuelgan del matcher `Agent` de Claude Code, que en opencode es `task` y
tiene otro payload; varias además inyectan contexto vía un mecanismo que
opencode no expone igual:

`agent-prelaunch`, `agent-launch-confirmed`, `pre-agent-snapshot`,
`native-agent-heartbeat`, `agent-working-dir-inject`, `inject-phase-context`,
`query-tailored-context-inject`, `context-diet`, `error-pattern-detector`,
`predev-completeness-check`, `token-budget-monitor`, `orchestrator-claim-gate`,
`orchestrator-skill-invocation-gate`, `clarification-gate`, `plan-claim-validator`(*).

Matiz importante: **no es "imposible", es "no como está escrito"**. `task` sí
existe y `tool.execute.before` puede **mutar `output.args`**, así que los tres
inyectores de contexto son portables si alguien reescribe el clasificador contra
`task`. Lo que hoy no tiene sentido es el código keyed en `agent`.
(*) `plan-claim-validator` aparece también en A por su rama `write`.

### C. Demasiado caros de reimplementar en JS — 12

`adaptive-bypass` (clasificación de complejidad: lee `cognitive-os.yaml` +
heurísticas), `completeness-check` y `project-docs-convention` (gating nivel 5,
corpus de docs), `control-plane-audit`, `session-heartbeat` y
`cross-session-event-emit` (ciclo de vida con daemon; en opencode van por el hook
genérico `event`, no por tool-call), `attribution-completeness-validator`,
`orchestrator-skill-invocation-gate` (índice de skills), `predev-completeness-check`,
`error-pattern-detector` (histórico de errores), `context-diet`,
`query-tailored-context-inject` (recuperación semántica).
Criterio: dependen de estado del repo o de un corpus, no de los argumentos de la
llamada; reimplementarlas en JS es duplicar lógica que ya vive en bash y que va
a divergir.

## Vocabulario: qué le falta al manifest

`status: supported` responde una sola pregunta y hoy se le piden tres. Propuesta
de tres ejes ortogonales:

```yaml
PreToolUse:
  # 1. ¿el harness entrega el evento?  supported | limited | unsupported
  event_status: supported
  native_event: tool.execute.before

  # 2. ¿un handler puede negar la ejecución?  can_deny | advisory_only | unknown
  #    Con evidencia, no con adjetivo.
  enforcement: can_deny
  enforcement_mechanism: throw_from_handler   # universal, sin razon estructurada
  enforcement_alt:
    surface: permission.ask                  # decision estructurada ask|deny|allow
    universal: false                         # solo herramientas configuradas `ask`
    carries_reason: false                    # output es {status}, sin campo de razon
  signal_bridge_required: exit_code_2        # 59/63 guardas senalan solo asi
  enforcement_evidence:
    - "~/.opencode/node_modules/@opencode-ai/plugin/dist/index.d.ts:235"
    - "packages/opencode/src/plugin/index.ts (Plugin.trigger, sin catch)"
    - "binario 1.16.2: trigger(before) precede a d.execute"

  # 3. ¿CÓMO llega la gobernanza COS?  Lista: puede haber más de un mecanismo,
  #    y uno puede estar RECHAZADO con su motivo.
  mechanisms:
    - kind: native_classifier          # lógica inline en el adapter
      implementation: packages/opencode-adapter/plugins/cos-primitive-guard.js
      reachable_primitives: 10
      unreachable_primitives: 9        # keyed en `agent`, que no es tool
      verified_by: scripts/opencode_primitive_adapter_smoke.py
    - kind: script_projection          # hooks de cognitive-os.yaml como scripts
      status: rejected
      rationale: >
        40 hooks con matcher Bash x p50 254 ms, ejecución serial con spawnSync
        = ~10 s por tool call (medido 2026-08-19).
      decision_ref: ADR-258

  # 4. cobertura, comparable entre harnesses y verificable por un test
  coverage:
    harness_reference: 63              # guardas que corre claude-code (dispatcher expandido)
    covered: 10
    gap_ref: manifests/opencode-hooks-schema.yaml#known_gaps
```

Lo que compra:

- Distingue **"el evento existe"** de **"la guarda llega"**. Hoy `supported` en
  opencode y `supported` en claude significan 10/63 y 63/63.
- Le da lugar a un mecanismo **rechazado con motivo**, que es exactamente la
  información que hoy vive sólo en un comentario del driver y que por eso se
  perdió (el encargo original nació de no verla).
- `enforcement` separa guarda de telemetría, que es la pregunta que decide.
- `coverage.covered` es un número que **un test puede recalcular** desde el JS
  y el `settings.json`, con lo cual deja de ser una afirmación a mano.

## Espejo a mano (defecto reportado, no corregido)

`scripts/_lib/settings-driver-opencode.sh` lleva:

```python
# OpenCode capability matrix (mirror manifests/harness-driver-capabilities.yaml):
COS_TO_OPENCODE_EVENT = { "SessionStart": "session.created", ... }
```

Es una **copia a mano** de la matriz de capacidades: el driver ya carga PyYAML
para leer `cognitive-os.yaml`, así que podría leer el manifest y derivar el mapa,
o al menos un test podría comparar los dos y fallar si divergen. Hoy nada los
compara: el manifest puede decir `unsupported` y el driver seguir proyectando (o
al revés) sin que nadie se entere. Misma familia que los 225 literales de shell
del driver de claude-code.

Segundo espejo, en el mismo archivo: el encabezado enumera
`supported: SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, Stop` — una
tercera copia del mismo dato, en prosa.

## Prueba: qué verifiqué y qué NO pude verificar

**Verificado, con comando:**

- Firma y existencia de los eventos → `grep` sobre el `.d.ts` **instalado**.
- El `trigger` precede a `execute` y no atrapa → `grep -aoE` sobre el binario +
  fuente de `sst/opencode`.
- El plugin commiteado **deniega** `bash` destructivo y **deja pasar** `task`
  → corrida de Node reproducida arriba.
- Recuento 37 / 29 / 63 / 23 / 9 / 10 / 53 → script de §Cobertura real.
- Latencia serial vs paralela (sobre el cableado luego revertido): 1994–2769 ms
  vs 386–559 ms para 40 hooks no-op.
- Revert limpio: `git status --short` no lista ningún archivo mío salvo este
  informe.

**NO verificado:**

- **Nunca ejecuté opencode.** Todo lo de "deniega" es lectura de su código más
  ejecución del plugin *fuera* de opencode. Falta una sesión real con un hook
  que bloquee y la observación de qué ve el modelo.
- **No medí la latencia con los hooks reales**, sólo con no-ops: correr los 63
  reales escribiría en `.cognitive-os/metrics/*.jsonl`, prohibido en el encargo.
  El ~10 s es aritmética sobre `hook-timing.jsonl`, no una medición end-to-end.
- **La clasificación A/B/C es mi criterio**, no una medición. Cada fila lleva su
  motivo para que se pueda discutir fila por fila; ninguna está probada.
- **No confirmé que los `known_gaps` del schema estén al día** más allá de los
  dos que ejercité (`agent`, `apply_patch`).

## Lo que NO hice y por qué

- **No proyecté los scripts** a `tool.execute.before/after`: el coordinador
  corrigió el encargo a mitad de camino y revertí lo hecho. El motivo de
  performance del diseño actual quedó confirmado (para la implementación
  serial).
- **No toqué `manifests/harness-driver-capabilities.yaml`.** El vocabulario
  propuesto cambia la forma del archivo y afecta a los cuatro drivers y a sus
  tests de contrato: es una decisión de arquitectura, no una edición.
- **No reescribí los clasificadores muertos** (`agent`, `multiedit`) aunque son
  deuda probada: los tests de contrato de ADR-258 los fijan tal cual, y
  cambiarlos sin decidir primero el destino de las 9 primitivas sería mover el
  baseline.
- **No toqué el driver de codex** (el encargo pidió diagnóstico) ni el de
  claude-code.
- **No agregué hooks a `cognitive-os.yaml`**: declara 200 de los 257 archivos en
  `hooks/*.sh`. Se reporta, no se corrige.

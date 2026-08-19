# Riesgo de absorción por los arneses — Claude Code, Codex CLI, OpenCode

> Fecha: 2026-08-19 · Alcance: profundidad sobre los tres arneses a los que este
> repo proyecta. Freeze de adopción vigente: acá va el riesgo, no la propuesta.
> Todas las verificaciones se hicieron con `curl` contra la fuente primaria; los
> comandos están en `## Fuentes`.

## Resumen ejecutivo

- **Familia en más riesgo: sub-agentes con aislamiento por worktree.** Claude Code
  lo trae de fábrica (`isolation: "worktree"` en la herramienta Agent, limpieza
  automática) y además ya arregló dos fugas que nosotros no cubrimos: sub-agentes
  aislados que escapaban al checkout compartido vía `git -C` / `--git-dir` /
  `GIT_DIR` / `GIT_WORK_TREE`, y worktrees creados fuera del repo por un symlink
  commiteado en `.claude/worktrees`. La versión nativa es **mejor** que la nuestra.
- **Segunda en riesgo: gobierno de costo.** `--max-budget-usd` deniega spawns
  nuevos y **halta** agentes en background al llegar al tope; hay tope de
  sub-agentes por sesión (200) y de concurrentes (20). El presupuesto duro dejó
  de ser nuestro.
- **Familia más segura: coordinación entre sesiones concurrentes** (locks de
  edición, ownership de rama, cola de merge de un solo escritor). Ningún arnés la
  tiene. Claude Code se acerca por otro lado —teammates con inbox, worktree por
  `/fork`— pero eso resuelve *fan-out dentro de una sesión*, no *dos sesiones
  independientes sobre el mismo checkout*.
- **El foso declarado de las guardas por tool-call no existe como se lo declaró.**
  Los tres arneses pueden denegar en pre-tool. Lo que no tienen es el catálogo de
  reglas. Detalle en `## Correcciones`.
- **Defecto activo confirmado:** `manifests/claude-code-hooks-schema.yaml` está
  incompleto contra la doc de hoy (le faltan 6 campos de handler y 3 eventos con
  control de decisión). No miente; omite. El que más duele es `if`.

## Correcciones a las premisas del encargo

1. **"~37 scripts de `PreToolUse`" — correcto, y lo reconté.** 37 scripts `.sh`
   únicos registrados en `PreToolUse` (39 entradas de handler; 2 no son `.sh`).
   Pero la lectura que sigue es engañosa: **21 de esos 37 están sobre el matcher
   `Agent`** y son inyectores de contexto y observadores (`inject-phase-context`,
   `context-diet`, `query-tailored-context-inject`, `blast-radius`…), no guardas.
   Las guardas de tool-call reales son ~14. Y las dos que el encargo nombra
   primero —git destructivo y borrado peligroso— **no están registradas
   directamente**: entran por `hooks/bash-hot-path-dispatcher.sh`, que las llama
   en la ruta P0 sincrónica.
2. **"No tienen equivalente externo maduro" es cierto del catálogo y falso del
   mecanismo.** Claude Code, Codex y OpenCode pueden los tres denegar una
   tool-call antes de que corra. El foso nunca fue *poder denegar*; es *saber qué
   denegar*. Si el informe de reinvención de hoy no hizo esa distinción, la
   conclusión es correcta por la razón equivocada, y eso es frágil.
3. **"El ecosistema de git-hooks asume un humano en el teclado" es verdadero e
   irrelevante.** El competidor de nuestras guardas no son los git-hooks: es el
   sistema de `permissions` del propio arnés. Y la doc de Claude Code recomienda
   explícitamente ese sistema **por encima de los hooks** para enforcement duro:
   *"use the permission system rather than a hook to enforce a hard allow or
   deny"* (hooks.md, sección `bash-if-matching`). Ese es el vector de absorción
   real, no un hook nuevo.
4. **"El `limited` de codex" parte de un dato nuestro que hoy es falso.** El
   manifest dice `matcher_semantics: bash_only`. La doc de Codex de hoy tiene una
   tabla "Tool coverage" que lo desmiente. Ver `## Las tres preguntas`, Q3.
5. **Nuestras guardas casi no usan el canal estructurado.** De los 37 scripts
   registrados en `PreToolUse`, **1** emite `permissionDecision: "deny"`
   (`private-mode-gate.sh`); el resto bloquea con `exit 2`. Es válido por
   contrato, pero el changelog de Claude Code trae un fix reciente —*"Fixed hooks
   with exit code 2 not blocking as documented when the hook's stdout JSON fails
   schema validation"*— que dice que ese camino estuvo roto. Nuestras 36 guardas
   estuvieron expuestas a ese bug y no hay nada en el repo que lo registre.
6. **"ABSORBIDO / EN CAMINO / NO ESTÁ" no es un eje temporal para la familia 1.**
   El mecanismo estuvo absorbido desde el día uno; lo que se mueve es el catálogo.
   Uso la etiqueta partida `ABSORBIDO (mecanismo) / FOSO (catálogo)` donde
   forzar un único estado mentiría.
7. **Verifiqué la premisa de propiedad antes de escribir.** `git status` limpio al
   arrancar, y el único archivo que toco es este informe. No commiteo ni pusheo.
8. **Hallazgo lateral, no pedido:** `hooks/lethal-trifecta-gate.sh` bloqueó la
   escritura de este mismo informe por Bash, con score 100, porque el **texto**
   cita un nombre de archivo de entorno, URLs y un comando de push. Es un falso
   positivo del tipo "el documento que describe el riesgo dispara el guard que
   describe": la regla mira el comando entero sin distinguir payload de heredoc.
   El informe se escribió con la herramienta Write, que no pasa por ese gate — o
   sea que el guard es evitable por cambio de herramienta, que es peor que el
   falso positivo.

## Tabla familia × arnés

| # | Familia | Claude Code | OpenAI Codex CLI | OpenCode |
|---|---------|-------------|------------------|----------|
| 1 | Guardas por tool-call (deny) | **ABSORBIDO (mecanismo) / FOSO (catálogo)** — `PreToolUse` con `permissionDecision` allow/deny/ask/defer + `updatedInput`; campo `if` con sintaxis de permission-rules que descompone subcomandos, `$()` y backticks [1] | **ABSORBIDO (mecanismo)** — `permissionDecision: "deny"`, `decision: "block"` legacy, exit 2, y `updatedInput` con `allow`. Cobertura muy por encima de Bash [4] | **ABSORBIDO (mecanismo, degradado)** — `tool.execute.before` deniega por `throw`; `permission.ask` deniega estructurado [5][6] |
| 2 | Enrutamiento de skills por confianza | **EN CAMINO** — skills nativas con `description`+`when_to_use` (1.536 chars), `paths` globs, `disable-model-invocation` con bloqueo activo si el modelo intenta replicar el workflow. Sin umbral ni bypass auditado [7] | **EN CAMINO** — `skills.md` existe en el árbol de docs; sin contrato de routing publicado [3] | **EN CAMINO** — "Agent Skills" en la navegación de docs; sin scoring publicado [5] |
| 3 | Telemetría de hooks | **ABSORBIDO (parcial)** — span `claude_code.hook` con `hook_event`, `hook_name`, `num_hooks`, `duration_ms`, `num_success`, `num_blocking`, `num_non_blocking_error`, `num_cancelled`; requiere detailed beta tracing [8] | **NO ESTÁ EN SU CAMINO** — sin spans de hooks en la referencia [4] | **NO ESTÁ EN SU CAMINO** [5] |
| 4 | Memoria persistente entre sesiones | **ABSORBIDO** — `CLAUDE.md`, `/memory`, carpeta de memoria por proyecto, frontmatter con `modified` ISO, path-specific rules, skill `consolidate-memory` bundled [2] | **ABSORBIDO (forma archivo)** — `AGENTS.md` [3] | **ABSORBIDO (forma archivo)** — Rules [5] |
| 5 | Gobierno de costo | **ABSORBIDO (lo duro)** — `--max-budget-usd` deniega spawns y halta agentes en background; `CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION` (200); `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` (20); `/usage` con breakdown por modelo y cache-hit [2] | **NO ESTÁ EN SU CAMINO** (sin señal en la doc de hooks ni de config) [3][4] | **NO ESTÁ EN SU CAMINO** [5] |
| 6 | Coordinación entre sesiones concurrentes | **EN CAMINO (adyacente)** — agent teams con inbox y `SendMessage`, hook `TeammateIdle`, `/fork` crea worktree propio, `claude agents` con PR/MR, self-hosted runner con rama por sesión. **No hay** lock de edición por archivo entre sesiones ni cola de merge [1][2] | **NO ESTÁ EN SU CAMINO** [4] | **NO ESTÁ EN SU CAMINO** [5] |
| 7a | Pipeline spec-driven (SDD) | **NO ESTÁ EN SU CAMINO** — hay plan mode / `ExitPlanMode` / skills, no un pipeline con artefactos versionados por fase [1][7] | **NO ESTÁ EN SU CAMINO** [3] | **NO ESTÁ EN SU CAMINO** [5] |
| 7b | Sub-agentes con aislamiento por worktree | **ABSORBIDO** — `isolation: "worktree"` en la herramienta Agent, limpieza automática, `EnterWorktree`/`ExitWorktree`, eventos `WorktreeCreate`/`WorktreeRemove` [1][2] | **NO ESTÁ EN SU CAMINO** [4] | **NO ESTÁ EN SU CAMINO** [5] |

## Mejor, igual o peor que lo nuestro

| Familia / arnés | Nativo vs nuestro | En qué, concretamente |
|---|---|---|
| **7b Worktree, Claude Code** | **MEJOR** | Arreglaron dos escapes que nosotros no cubrimos: sub-agentes aislados redirigiendo git al checkout compartido vía `git -C`, `--git-dir`, `GIT_DIR`/`GIT_WORK_TREE`; y creación de worktree siguiendo un symlink commiteado en `.claude/worktrees`, que dejaba archivos fuera del repo. Además el aislamiento ahora aplica a edits y a Bash en todo tipo de sesión, no solo a la creación [2] |
| **5 Costo, Claude Code** | **MEJOR en lo duro, PEOR en lo fino** | Mejor: el cap corta de verdad —deniega spawns nuevos y halta background agents— y está en el proceso, no en un hook que un `exit 2` mal formado puede saltear. Peor: no rutea por modelo según el tipo de tarea ni conoce el costo histórico del proyecto; nuestro `cost_predict` y los hints opus/sonnet/haiku no tienen equivalente |
| **3 Telemetría, Claude Code** | **PEOR en granularidad, MEJOR en integración** | Peor: `duration_ms` es *"wall-clock duration of all matching hooks"* — es por grupo de matcher, no por script, así que no dice cuál de los 39 handlers de `PostToolUse` se comió el presupuesto; y no detecta hooks que nunca dispararon. Mejor: es OTel real, con `tool_use_id` correlacionable a spans y eventos, y `num_blocking`/`num_cancelled` que nuestro wrapper no distingue |
| **4 Memoria, los tres** | **PEOR que lo nuestro** | Archivo plano cargado por path/glob. Sin búsqueda semántica, sin topic keys, sin detección de conflicto entre observaciones. Engram gana claro; el riesgo acá no es calidad, es que el arnés se vuelva el lugar por defecto donde el operador escribe |
| **2 Skills, Claude Code** | **PEOR, pero suficiente para la mayoría** | Selecciona por relevancia de `description`+`when_to_use` sin umbral numérico, sin registro de por qué eligió, sin bypass auditado. Nuestro `skill_router` con confidence + gate de invocación obligatoria es más estricto. La contra: el nativo tiene `paths` globs, que nosotros no, y bloquea activamente al modelo cuando intenta replicar a mano un skill marcado `disable-model-invocation` |
| **1 Guardas, Claude Code** | **EMPATE en mecanismo, NUESTRO en catálogo, NATIVO en parsing de Bash** | El campo `if` con un patrón tipo `Bash(rm *)` descompone `FOO=bar git push`, `npm test && git push` y comandos anidados en `$()` o backticks — es exactamente el parseo que hace nuestro `destructive-rm-blocker.sh`, hecho por el host. Pero la doc lo declara *best-effort* y *fail-open* cuando no puede parsear, y recomienda `permissions` para el deny duro. O sea: nos ganan el filtro barato y nos dejan el enforcement |
| **1 Guardas, Codex** | **PEOR que lo nuestro en un punto que importa** | `permissionDecision: "ask"` está *"parsed but not supported yet"*: Codex marca el hook como fallido, reporta el error **y continúa la tool call**. Un guard nuestro que pida confirmación se convierte en allow silencioso al proyectarse a Codex |
| **1 Guardas, OpenCode** | **PEOR** | `tool.execute.before` retorna `void`: la única forma de denegar es lanzar una excepción, sin razón estructurada legible por el modelo y sin estado `ask`. El canal estructurado es `permission.ask`, que sí acepta `"ask" \| "deny" \| "allow"`. Además hay un issue abierto donde los `deny` de agentes custom se ignoran al invocar por SDK [6] |

## Las tres preguntas específicas

### Q1 — ¿Claude Code planea más eventos con deny, o cambiar `hookSpecificOutput`?

**Contrato: no cambió en su forma. Nuestro manifest: incompleto, con defecto activo.**

Re-verificado hoy contra `code.claude.com/docs/en/hooks.md`: **277.223 bytes**, contra
los **272.682** que el manifest registra como fetched el 2026-08-15. Creció 4.541 bytes.

Lo que **sigue igual** (nuestro manifest acierta):

- `additionalContext` sigue viviendo solo en `hookSpecificOutput`, nunca en la raíz.
- El campo se sigue llamando `updatedInput` — **0 ocurrencias de `modifyInput`** en la
  doc. Varios blogs de 2026 dicen `modifyInput`; están mal y el manifest está bien.
- `suppressOutput` sigue documentado como inerte, textual: *"Has no effect"*.
- `permissionDecision` sigue aceptando `allow` / `deny` / `ask` / `defer`.
- La regla de parseo por primer carácter no se movió.

Lo que **falta en nuestro manifest** (defecto activo, por orden de daño):

1. **`if`** — campo de handler con sintaxis de permission-rules (patrones tipo
   `Bash(git *)` o `Edit(*.ts)`). Solo se evalúa en eventos de tool: `PreToolUse`,
   `PostToolUse`, `PostToolUseFailure`, `PermissionRequest`, `PermissionDenied`.
   **En cualquier otro evento, un hook con `if` nunca corre.** Un solo `if` mal
   puesto apaga un guard en silencio. No está en el manifest.
2. **`args`** (exec form: sin shell, cada elemento es un argumento exacto) y
   **`shell`** (`bash` / `powershell`). Cambian cómo se resuelve `command`.
3. **`asyncRewake`** — background que despierta a Claude con exit 2. Implica `async`.
4. **`statusMessage`** y **`once`** (este último solo honrado en frontmatter de skill).
5. **Tres eventos ganaron control de decisión** y el manifest no los tiene:
   `PreCompact` y `ConfigChange` bajo top-level `decision: "block"`; `TaskCreated`
   cancela con exit 2 o `decision: "block"` (y ahí `continue: false` se ignora);
   `TeammateIdle` y `TaskCompleted` bloquean con exit 2 o `{"continue": false}`.
6. **Cambio de semántica con versión:** desde v2.1.214, un patrón de un solo
   segmento como `Edit(src/**)` dentro de `if` matchea solo `<cwd>/src`; para
   cualquier profundidad hay que escribir `Edit(**/src/**)`. Las reglas `deny`/`ask`
   de permissions **no** cambiaron.

**¿Hay señal de que amplíen el deny?** No. La señal apunta al revés, y es fuerte:

- Los eventos nuevos del último tramo (`WorktreeRemove`, `Notification`,
  `SessionEnd`, `PostCompact`, `InstructionsLoaded`, `StopFailure`, `CwdChanged`,
  `DirectoryAdded`, `FileChanged`) están todos en la fila **"None — no decision
  control"**.
- La doc dice, textual, que el filtro `if` es best-effort y falla abierto, y que
  para un allow/deny duro hay que usar el sistema de permissions, no un hook.
- El changelog **endurece la relación permissions↔hooks en favor de permissions**:
  se arregló que `permissions.deny` no overrideara un `permissionDecision: "ask"`
  de un hook, y que auto mode pisara un `ask` de hook en Bash sin sandbox.

Conclusión operativa: el riesgo para la familia 1 no es que Claude Code agregue
deny en más eventos. Es que empuje el enforcement fuera de los hooks.

### Q2 — ¿OpenCode puede denegar en `tool.execute.before`?

**Sí, pero por excepción, y no es el canal correcto.** Evidencia de código y de docs,
no de blog.

Firma real, de `packages/plugin/src/index.ts` en el repo de OpenCode:

```ts
"tool.execute.before"?: (
  input: { tool: string; sessionID: string; callID: string },
  output: { args: any },
) => Promise<void>
```

Retorna `Promise<void>`. **No hay valor de retorno con el que denegar**, así que la
única vía es lanzar. Y está en la doc oficial como ejemplo canónico (la protección
de archivos de entorno):

```js
"tool.execute.before": async (input, output) => {
  if (input.tool === "read" && output.args.filePath.includes(".env")) {
    throw new Error("Do not read .env files")
  }
}
```

El canal **estructurado** es otro, en el mismo archivo de tipos:

```ts
"permission.ask"?: (input: Permission, output: { status: "ask" | "deny" | "allow" }) => Promise<void>
```

Para el agente que está cableando esto: `tool.execute.before` sirve para **reescribir
args** (el otro ejemplo oficial aplica escapado de shell sobre `output.args.command`)
y para un deny duro sin razón estructurada. Si lo que se quiere es el equivalente de
nuestro `permissionDecision: "deny"` con motivo, **el cableado va en `permission.ask`**,
no en `tool.execute.before`. Y hay una advertencia: existe un issue abierto donde los
`deny` declarados en la config para agentes custom se ignoran al invocar por SDK — el
enforcement no es uniforme entre superficies.

### Q3 — ¿Qué significa el `limited` que le damos a codex en `PreToolUse`/`PostToolUse`?

**Nuestro `limited` está mal fundado.** `manifests/harness-driver-capabilities.yaml`
dice `matcher_semantics: bash_only` para ambos eventos. La doc de Codex de hoy
(`developers.openai.com/codex/hooks`, tabla "Tool coverage") lo desmiente punto por
punto:

| Ruta de tool | PreToolUse | PostToolUse | Cómo se matchea |
|---|---|---|---|
| Shell commands | Sí | Sí | `Bash` |
| Unified exec (`exec_command`) | Sí | Sí | `Bash` |
| `apply_patch` | Sí | Sí | `apply_patch`, **`Edit` o `Write`** |
| MCP tools | Sí | Sí | `mcp__filesystem__read_file`, `mcp__filesystem__.*` |
| Otras local function tools | Sí | Sí | `update_plan`; **`spawn_agent` también matchea `Agent`** |
| Hosted tools (p. ej. `WebSearch`) | **No** | **No** | No usan la ruta de function-tool local |

Es decir: los matchers `Edit`, `Write` y `Agent` —que nuestro manifest da por
inexistentes en Codex— **existen**, y el propio `manifests/codex-hooks-schema.yaml`
de este repo ya los documenta en su sección `tool_names`. **Los dos manifests se
contradicen entre sí**, y el que gobierna la proyección es el que está mal.

El `limited` **real** de Codex, con fuente, es otro y es más peligroso:

1. **`permissionDecision: "ask"` no está soportado.** Textual: *"parsed but not
   supported yet. Codex marks the hook run as failed, reports the error, and
   continues the tool call."* Lo mismo para `decision: "approve"` legacy,
   `continue: false`, `stopReason` y `suppressOutput`. **Un guard que pide
   confirmación se degrada a allow silencioso.**
2. **`write_stdin` no re-dispara `PreToolUse`** sobre una sesión de unified-exec ya
   aprobada.
3. **Hosted tools quedan fuera** de la ruta de hooks por completo.
4. **La doc se declara no-hermética:** *"Some specialized tool paths can opt out of
   the default hook path. Treat tool hooks as a useful guardrail, not a complete
   enforcement boundary."*
5. **Trust gate:** los hooks no-managed no corren hasta que el operador los revisa
   en `/hooks`, y el trust se registra contra el hash exacto — cambiar un guard lo
   apaga hasta que lo vuelvan a confiar. Esto ya está en nuestro manifest y sigue
   vigente; agrego que hoy existen `--dangerously-bypass-hook-trust` y
   `allow_managed_hooks_only = true` en `requirements.toml`.

## Riesgo de obsolescencia ordenado por urgencia

| # | Familia | Riesgo | Por qué ahora | Qué hacer (sin adoptar nada: freeze) |
|---|---------|--------|---------------|--------------------------------------|
| 1 | Sub-agentes con aislamiento por worktree | **CRÍTICO** | Nativo, con hardening que nosotros no tenemos. Cada hora que gastamos acá es contra una versión más segura que ya existe | **Dejar de construir.** Migrar a `isolation: "worktree"` cuando levante el freeze |
| 2 | Gobierno de costo (presupuesto duro) | **ALTO** | `--max-budget-usd` + caps de sub-agentes cortan de verdad y a nivel proceso. Nuestro cap por hook es evitable | **Dejar de construir el cap.** Conservar el ruteo por modelo y `cost_predict`, que no tienen equivalente |
| 3 | Telemetría de hooks (timing) | **ALTO** | `claude_code.hook` con `duration_ms` ya existe y es OTel | **Reducir alcance:** dejar de medir wall-clock agregado, quedarse con lo que el span **no** da: atribución por script y detección de hooks nunca disparados |
| 4 | Memoria persistente | **MEDIO** | Absorbida en forma de archivo por los tres. Nuestra versión es mejor, pero el default del operador migra | **Seguir**, defendiendo con búsqueda semántica y detección de conflicto — no con "guardar texto" |
| 5 | Guardas por tool-call | **MEDIO, y del tipo raro** | El mecanismo nunca fue nuestro. Lo que se mueve es que el host se lleva el parseo de Bash (`if`) y empuja el enforcement a `permissions` | **Seguir el catálogo, dejar el parseo.** Y arreglar el defecto del manifest, que hoy es el riesgo más barato de eliminar |
| 6 | Enrutamiento de skills por confianza | **MEDIO-BAJO** | Nativo por relevancia, sin umbral. Cubre el caso común | **Seguir solo la parte diferencial:** umbral, bypass auditado, traza de por qué se eligió. Dejar el "sugerir el skill" |
| 7 | Pipeline SDD | **BAJO** | Nadie va por ahí | **Seguir**, pero sabiendo que bajo riesgo no es lo mismo que alto valor |
| 8 | Coordinación entre sesiones concurrentes | **MUY BAJO — foso real** | Los teammates de Claude Code resuelven fan-out intra-sesión, no dos sesiones sobre el mismo checkout | **Seguir e invertir.** Es lo único de la lista donde nadie está mirando y el problema es real y recurrente |

## Qué dejar de construir hoy

1. **Aislamiento por worktree propio para sub-agentes.** Ya perdimos, y perdimos
   con razón: la versión nativa cierra escapes que la nuestra no.
2. **Cualquier tope de presupuesto o de cantidad de agentes implementado como
   hook.** El host lo hace a nivel proceso; un hook que bloquea por `exit 2` es
   estrictamente peor.
3. **Medición de wall-clock agregado por evento de hook.** El span nativo ya lo da.
   Lo que sigue valiendo es lo que el span no distingue: qué script específico
   costó, y cuáles nunca dispararon.
4. **Parseo propio de comandos Bash para decidir *si corre* un guard** (subcomandos,
   sustitución de comandos, asignaciones al principio). Eso ahora lo hace `if`.
   Nuestro parseo sigue valiendo para decidir *qué se deniega*, que es otra cosa.
5. **"Sugerir el skill correcto".** Nativo. Lo diferencial es el umbral y la
   auditoría del bypass, no la sugerencia.

Y una cosa que hay que **empezar** a hacer, porque es un defecto y no una
oportunidad: poner `manifests/claude-code-hooks-schema.yaml` al día con `if`,
`args`, `shell`, `asyncRewake`, `statusMessage`, `once` y los tres eventos con
control de decisión; y corregir `matcher_semantics: bash_only` en
`manifests/harness-driver-capabilities.yaml`, que hoy contradice a nuestro propio
`manifests/codex-hooks-schema.yaml` y nos hace proyectar menos guardas de las que
Codex acepta.

## Fuentes

Todas verificadas el **2026-08-19** con `curl` desde este repo. Las marcadas
**(2026)** son material publicado o actualizado este año.

1. **(2026)** Claude Code — referencia de hooks, markdown crudo.
   `curl -sSL https://code.claude.com/docs/en/hooks.md` → 277.223 bytes
   (el manifest registra 272.682 bytes el 2026-08-15).
   Secciones usadas: "Hook handler fields" (campos `if`, `args`, `shell`,
   `asyncRewake`, `statusMessage`, `once`), "Bash `if` matching", "Decision
   control" (tabla completa por evento), "Exit code output", "PreToolUse".
2. **(2026)** Claude Code — changelog oficial, versión tope `2.1.236`.
   `curl -sSL https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md`
   → 5.646 líneas. Entradas citadas: `--max-budget-usd` y background agents;
   `CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION` (200); `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`
   (20); escapes de worktree vía `git -C` / `--git-dir` / `GIT_DIR`; symlink
   `.claude/worktrees`; exit 2 que no bloqueaba con JSON inválido; `if` de un
   segmento desde v2.1.214; `permissions.deny` sobre `ask` de hook; auto mode
   pisando `ask`; `/fork` con worktree propio; merge de `/cost` y `/stats` en
   `/usage`; frontmatter `modified` en memoria.
3. **(2026)** OpenAI Codex — `docs/config.md` del repo, incluida la nota de
   `allow_managed_hooks_only` en `requirements.toml`, y listado del directorio
   `docs/` vía API de GitHub (confirma que `config.md`, `skills.md` y
   `agents_md.md` son stubs que redirigen a `developers.openai.com`).
   `curl -sSL https://raw.githubusercontent.com/openai/codex/main/docs/config.md`
4. **(2026)** OpenAI Codex — referencia de hooks.
   `curl -sSL https://developers.openai.com/codex/hooks` → HTTP 200, 455.125 bytes.
   Secciones usadas: "Matcher patterns", **"Tool coverage"**, "Common input
   fields", "PreToolUse" (deny / `updatedInput` / `ask` no soportado), "Review and
   trust hooks".
5. **(2026)** OpenCode — documentación de plugins.
   `curl -sSL https://opencode.ai/docs/plugins/` → 109.727 bytes; pie de página:
   *"Last updated: Aug 19, 2026"*. Listado completo de eventos, ejemplo de
   protección de archivos de entorno con `throw`, ejemplo de reescritura de args,
   hooks de compactación.
6. **(2026)** OpenCode — definiciones de tipos del paquete de plugins.
   `curl -sSL https://raw.githubusercontent.com/sst/opencode/dev/packages/plugin/src/index.ts`
   → 9.053 bytes. Firmas exactas de `tool.execute.before`, `tool.execute.after`,
   `permission.ask`, `shell.env`. Nota: el repo aparece hoy también bajo la
   organización `anomalyco`; la ruta `sst/opencode` resuelve por redirect de
   GitHub. Issue relacionado citado desde búsqueda, **no verificado contra la
   API**: `opencode#6396` (deny de agentes custom ignorado vía SDK).
7. **(2026)** Claude Code — documentación de skills.
   `curl -sSL https://code.claude.com/docs/en/skills.md` → 96.949 bytes.
   Campos `description`, `when_to_use` (truncado a 1.536 chars), `paths`,
   `disable-model-invocation`; comportamiento de bloqueo cuando el modelo intenta
   replicar el workflow de un skill no invocable por modelo.
8. **(2026)** Claude Code — monitoreo y OpenTelemetry.
   `curl -sSL https://code.claude.com/docs/en/monitoring-usage.md` → 136.344 bytes.
   Span `claude_code.hook` y sus atributos; nota de que `duration_ms` es el
   wall-clock de **todos** los hooks que matchean; `decision_source: "hook"` en el
   evento de decisión de tool.
9. Repo local, inventario propio (sin red):
   - 37 scripts `.sh` únicos registrados en `PreToolUse`, 21 de ellos sobre el
     matcher `Agent`.
   - 1 de 37 emite `permissionDecision: "deny"`; el resto usa `exit 2`.
   - `hooks/destructive-git-blocker.sh` y `hooks/destructive-rm-blocker.sh` entran
     por `hooks/bash-hot-path-dispatcher.sh`, no por registro directo.
   - Contradicción entre `manifests/harness-driver-capabilities.yaml`
     (`matcher_semantics: bash_only`) y `manifests/codex-hooks-schema.yaml`
     (sección `tool_names`, que ya lista `apply_patch` / `Edit` / `Write` y el
     patrón de tools MCP).

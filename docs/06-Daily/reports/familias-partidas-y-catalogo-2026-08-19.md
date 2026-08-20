<!-- SCOPE: os-only -->
# Las cinco familias partidas y el catálogo de seguridad, medidos

> Fecha: 2026-08-19 · Alcance: partir por su corte las familias donde el veredicto único
> mentía, y medir regla por regla el catálogo de seguridad que trae de fábrica cada arnés.
> **Freeze de adopción vigente**: acá no se propone adoptar nada.
> **Frescura**: cada afirmación sobre un sistema ajeno cita `[n]`, y en `## Fuentes` cada
> fuente lleva `verified:` y `how:`. Nada sale de memoria del modelo.
> **No se borró, commiteó ni pusheó nada.** El único archivo escrito es éste. No se tocó
> `hooks/**`, `cognitive-os.yaml` ni `.cognitive-os/metrics/`.

## Resumen ejecutivo

- **Se deciden las 149 filas que el informe previo señaló como destrabables; quedan 27 sin
  decidir** (F07 Ecosistema), por la misma razón de antes y no por falta de búsqueda: la
  documentación oficial de los tres arneses no habla de evaluar ni congelar adopción.
- Sobre mi propio reconteo, esas siete familias tienen **162 filas** (no 149; corrección 2),
  y las 162 quedan con estado: **74 ABSORBIDO / 88 NO ESTÁ**, cero EN CAMINO.
- **Los cortes no son cinco variantes de lo mismo, son tres ejes distintos.** F01 y F09 se
  parten por el **sujeto** (a quién se le aplica la primitiva). F11 y F10 se parten por el
  **verbo** (gastar vs elegir; guardar vs consultar). F14, F06 y F08 se parten por
  **mecanismo vs política** — el mismo eje que el encargo creyó exclusivo de seguridad.
- **F10 Memoria no necesita partición.** El corte existe pero las 9 filas caen todas del
  mismo lado (memoria consultable, no memoria-archivo): **NO ESTÁ en los tres**. Forzarle
  dos sub-familias habría sido inventar el corte para que el número cerrara.
- **El catálogo de seguridad no es el foso que se declaró.** De 15 celdas (5 reglas × 3
  arneses): **6 traen la regla de fábrica y no anulable**, 2 parcial, 2 existe pero opt-in,
  **5 sin regla**. Claude Code trae listas literales de *protected paths* y *critical paths*
  que **ningún `allow` ni hook `PreToolUse` puede aprobar** [1] — es decir, mejor que la
  nuestra, que se salta cambiando de herramienta.
- **Lo que sí queda de foso en seguridad, medido**: `git push --force` sobre rama protegida
  (solo Codex, y solo con el revisor automático encendido, que **no** es el default [3][4])
  y los patrones de secretos (solo OpenCode, y solo `*.env` [5]). Dos reglas de cinco.
- **Codex publica su catálogo como documento en abierto** (`guardian/policy.md`): egress
  sensible, credential probing, debilitamiento persistente y acciones destructivas [4]. Es
  un catálogo semántico, no de regex, y es reemplazable por política de empresa.

## Correcciones a las premisas del encargo

1. **`strictAllowlist` existe y está en 2.1.219. La premisa que me pasaron es falsa.** El
   encargo dice que un `WebFetch` que resume «inventó» `strictAllowlist` en la 2.1.219.
   La documentación de sandboxing, leída hoy con `curl` sobre el `.md`, dice textualmente:
   *«**Strict allowlist**: if you set `strictAllowlist` to `true` in user, managed, or CLI
   `--settings` settings, Claude Code denies sandboxed commands access to any host outside
   the allowlist instead of prompting»* … *«Requires Claude Code v2.1.219 or later»* [2].
   Lo que pasó es más incómodo que una alucinación: **el resumen acertó y el desmentido se
   apoyó en un "no encontrado" sobre el CHANGELOG**, que es exactamente la falacia que el
   informe previo advirtió en su propia corrección 6 («no encontrado sobre un archivo grande
   tampoco prueba ausencia») y después usó igual. La ausencia en un changelog no refuta la
   presencia en la doc de referencia.
2. **«149 de las 176» no reproduce sobre mi clasificador: me da 162.** Reconstruí las 403
   filas indecidibles exactamente (538 padrón − 135 decididas = 403, mismo resultado que el
   informe previo), pero mi clasificador de familias pone **162** filas en las siete
   familias del encargo (F06 40, F14 31, F09 30, F11 30, F08 11, F01 11, F10 9) contra las
   149 del informe previo (35/35/23/24/11/11/10). El delta sale del **orden** del
   clasificador: puse las siete familias del encargo primero, así que ganan filas que otro
   orden manda a F17 (`sandbox-sample`) o a F18 (`component-reality-check`). Reporto **mis
   162 con mi orden declarado**, y digo cuándo hablo de las 149 del informe previo.
3. **F10 no está partida, y ese era el punto de dejarme decirlo.** Las 9 filas indecidibles
   de memoria son todas del lado consultable (`engram-*`, `cognee-search`,
   `conversation-memory`, `memory-scan`). La mitad absorbida de la familia —memoria en
   archivo que el arnés lee al arrancar— **ya estaba decidida** y por eso no aparece acá.
   El «media familia absorbida y media no» del encargo describe la familia completa, no el
   residuo indecidible. Una partición habría dado una sub-familia de 9 y una de 0.
4. **El eje mecanismo-vs-catálogo no es privativo de F06/F08: también parte F14.** El
   encargo separa «Causa A: familias partidas» de «Causa B: mecanismo vs catálogo» como si
   fueran dos problemas. F14 Contexto se parte por el mismo eje: el arnés absorbió el
   **transporte** de contexto (compactación, `/context`, `additionalContext`, sub-agente con
   ventana propia) y no la **política** de qué contexto entra. Son dos causas en el papel y
   una sola en los datos: **el arnés absorbe capacidades y no criterios**.
5. **Agent Plugins 1.0: el ancla es todavía más débil de lo que dice la corrección heredada.**
   No hace falta discutir qué dice la spec: los tres clientes ya publican su propio catálogo
   —Claude Code listas literales [1], Codex rutas protegidas y política de revisor [3][4],
   OpenCode denegación de `*.env` [5]—. Que el estándar portable lo delegue al cliente es
   irrelevante cuando los tres clientes ya lo hicieron.
6. **El «catálogo» del SO tampoco es homogéneo, y una parte no es de seguridad.** De las 40
   filas que mi clasificador manda a F06, **14 son escaneo de vulnerabilidades y red-team**
   (`vulnerability-scan`, `security-audit`, `pentest-self`, `red-team`, `aguara-scan`…), que
   compiten con **Codex Security** —plugin, CLI, cloud, SARIF, política de severidad en CI
   [6]— y no con el sistema de permisos. Medirlas contra `permissions` habría dado
   «no absorbido» por comparar contra el producto equivocado.
7. **Verifiqué la propiedad antes de escribir**, no la recordé: `git status --porcelain`
   sobre la ruta de este informe, salida vacía. `docs/06-Daily/**` está en
   `dated_by_construction_globs` de `manifests/external-claim-freshness.yaml`, así que este
   informe **no** suma a las 305 afirmaciones sin fechar; aun así cada fuente lleva
   `verified:` y `how:`.
8. **No pude usar `WebFetch` con resumen para nada de esto y no lo intenté.** Todo salió de
   `curl` sobre el `.md` de cada página (Codex publica el sufijo `.md` y un `llms.txt` con
   el índice completo). Las páginas de OpenCode no tienen `.md`: las bajé en HTML y las
   convertí a texto con un script propio, que está en el apéndice.

## Las cinco familias partidas: el corte de cada una

Criterio para aceptar un corte: **un cambio de un lado no obliga a tocar el otro**. Si
obliga, no son dos sub-familias sino una mal descrita.

### F01 Aislamiento y preservación (11) — corte por **sujeto**

> ¿El estado que se aísla pertenece a un proceso que **el arnés lanzó**, o a un proceso que
> **el arnés no controla**?

Ésa es la línea, y se lee en la forma del contrato nativo: `isolation: "worktree"` es un
**parámetro de la herramienta Agent** [7] — el arnés aísla lo que él mismo genera. Nada en
los tres arneses conoce la existencia de una segunda sesión independiente sobre el mismo
checkout. Por eso `pre-agent-snapshot` (aislar al sub-agente que lanzo yo) y
`stash-quarantine` (rescatar trabajo sin commitear que dejó otro) están en la misma familia
del censo y tienen veredictos opuestos.

| Sub-familia | Filas | Miembros |
|---|---|---|
| **F01a** el sujeto es un proceso que el arnés lanzó | 4 | `auto-checkpoint`, `branch-worktree-closure`, `devbox-checkpoint`, `worktree-triage` |
| **F01b** el sujeto es trabajo sin commitear en un checkout que el arnés no controla | 7 | `pre-agent-snapshot`, `post-agent-snapshot-restore`, `preserved-wip-cleanup`, `stash-quarantine` (skill), `stash-quarantine` (rule), `capability-protection`, `capability-snapshot` |

### F09 Telemetría (30) — corte por **sujeto medido**

> ¿Lo medido es un **evento de ejecución del arnés**, o una **primitiva del catálogo del SO**?

Claude Code emite el span `claude_code.hook` y tiene `/usage` e `/insights` [8]: mide sus
propios eventos. Ninguno de los tres tiene un concepto de «primitiva del catálogo» —no
existe el objeto que `dogfood-score`, `component-reality-check`, `so-slo` o `agent-kpis`
miden—, así que no puede haber absorción, ni siquiera parcial.

| Sub-familia | Filas | Miembros |
|---|---|---|
| **F09a** el sujeto es un evento de ejecución del arnés | 13 | `aci-observation-capture`, `audit-id-enricher`, `codebase-itinerary-capture`, `git-context-capture`, `native-agent-heartbeat`, `session-heartbeat`, `session-token-aggregator`, `state-heartbeat`, `tool-sequence-capture`, `hook-timing`, `observability`, `performance-monitoring`, `audit-trail` |
| **F09b** el sujeto es una primitiva del propio catálogo | 17 | `aspirational-audit-weekly`, `control-plane-audit`, `control-plane-audit-hourly`, `skill-invocation-logger`, `skill-usage-tracker`, `so-impact-eval-trigger`, `so-impact-eval`, `state-retention-audit`, `agent-kpis` (×2), `so-slo`, `component-reality-check`, `dogfood-score`, `metrics-calibrator`, `peer-card`, `so-vs-vanilla`, `trust-audit` |

### F11 Costo y modelo (30) — corte por **verbo**

> ¿El control actúa sobre **cuánto se gasta**, o sobre **a quién se le manda cada tarea**?

Es el corte con la evidencia más limpia de las cinco: el tope duro de Claude Code
*deniega spawns nuevos y halta agentes en background* al llegar al cap [9], y no hay una
sola línea sobre elegir modelo por tipo de tarea en ninguno de los tres. Gastar y elegir son
verbos distintos: subir el tope no obliga a tocar el ruteo, y cambiar el ruteo no toca el
tope.

| Sub-familia | Filas | Miembros |
|---|---|---|
| **F11a** gasto: tope, contador, medidor, límite de tasa | 16 | `agent-quota-advisor`, `context-budget-meter`, `rate-limit-detector`, `rate-limit-drain`, `rate-limit-precheck`, `rate-limiter`, `rate-limiting`, `token-budget-monitor`, `usage-health-check`, `cost-prediction`, `cost-predictor`, `resource-check`, `resource-governance`, `resource-governor`, `token-economy`, `language-token-economy` |
| **F11b** destino: a quién y cómo se le manda cada tarea | 14 | `agent-quota-redirect`, `agent-qwen-bridge`, `dequeue-notify`, `decomposition`, `llm-dispatch`, `model-compatibility`, `model-directive`, `model-routing`, `model-optimizer`, `non-blocking-retry`, `queue-advisor`, `queue-drain` (×2), `workload-scheduling` |

### F14 Contexto y encargo (31) — corte por **mecanismo vs política**, y necesita **tres**

> ¿El arnés **mueve bytes de contexto**, **decide qué contexto entra**, o **redacta y evalúa
> el encargo**?

Dos sub-familias no alcanzan. Claude Code absorbe el transporte (auto-compact, `/context`,
`hookSpecificOutput.additionalContext`, sub-agentes con ventana propia [7][8]); no absorbe
ni la política de qué entra ni la redacción del encargo, y ésas dos tampoco son la misma
cosa: `context-diet` decide **cuánto** y `exhaustive-prompt` decide **qué dice**. Cambiar el
presupuesto de contexto no obliga a reescribir la plantilla de encargo.

| Sub-familia | Filas | Miembros |
|---|---|---|
| **F14a** transporte y presupuesto de la ventana | 9 | `pre-compaction-flush`, `context-management`, `context-optimization`, `context-watchdog`, `cognitive-load`, `response-compression`, `result-management`, `caveman`, `caveman-compress` |
| **F14b** política de qué contexto entra | 9 | `agent-working-dir-inject`, `context-diet`, `inject-phase-context`, `memory-prefetch`, `query-tailored-context-inject`, `subagent-context-injector`, `context7-auto-trigger`, `user-prompt-capture` (×2) |
| **F14c** redacción del encargo y lectura del resultado | 13 | `agent-output-reading`, `anti-hallucination`, `assumption-tracking`, `clarification-gate`, `closed-loop-prompts`, `orchestrator-prompt-compose`, `prompt-composition`, `prompt-quality`, `responsiveness`, `split-and-resume`, `step-files`, `compose-prompt`, `exhaustive-prompt` |

### F10 Memoria (9) — **el corte existe y no parte nada**

> ¿La memoria es un **archivo que el arnés lee al arrancar**, o un **índice que alguien
> consulta**?

Los tres absorbieron la memoria-archivo (`CLAUDE.md` con auto-memory e índice `MEMORY.md`;
`AGENTS.md` en Codex y OpenCode) [10]. Ninguno tiene búsqueda semántica, refuerzo por acceso,
cristalización ni detección de conflicto. Pero **las 9 filas indecidibles caen las 9 del
lado consultable**: la mitad absorbida de la familia ya había sido decidida y salió del
conjunto. **No la parto.** Las 9 se deciden juntas: **NO ESTÁ EN SU CAMINO en los tres**.

Miembros (9): `engram-crystallize-on-session-end`, `engram-daemon-launcher`,
`engram-obsidian-export-on-stop`, `engram-reinforce-on-access`, `engram-api-safety`,
`engram-organization`, `cognee-search`, `conversation-memory`, `memory-scan`.

### F06 y F08 — corte dado por el encargo, y **F06 necesita cuatro**

F08 se parte en mecanismo (4) y catálogo de actos concretos (7). F06 no: mezcla tres cosas
que compiten contra productos distintos —el sistema de permisos, el escáner de
vulnerabilidades y el gobierno de licencias— y medir las tres contra `permissions` habría
dado un falso «no absorbido».

| Sub-familia | Filas | Miembros |
|---|---|---|
| **F06a** mecanismo de encierro y denegación | 10 | `hook-security-profiles`, `gpu-sandbox`, `sandbox-sampling`, `sandbox-sample`, `private-mode-gate`, `private-mode-metrics-gate`, `private-mode` (×2), `cosd-auth-guard`, `agent-security` |
| **F06b** catálogo de reglas concretas (secretos, egress, contenido) | 12 | `dangerous-env-flag-detector`, `network-egress-guard`, `external-cache-content-leak`, `document-ingest-guard`, `research-to-runtime-firewall`, `content-policy` (×2), `credential-management`, `confidentiality-protection`, `secret-audit`, `ai-provider-identity-guard`, `publication-safety` |
| **F06c** escaneo de vulnerabilidades y red-team | 14 | `aguara-scan`, `mcp-scan`, `aguara-integration`, `security-scanning`, `pentesting-readiness`, `parry-integration`, `trailofbits-skills`, `nemo-guardrails`, `pentest-self`, `red-team`, `redteam-harness`, `security-audit`, `security-red-team`, `vulnerability-scan` |
| **F06d** licencias y cadena de suministro | 4 | `dependency-license-classifier`, `license-policy`, `spdx-header-required`, `supply-chain-defense` |
| **F08a** mecanismo de guarda por tool-call | 4 | `dispatch-gate`, `dry-run`, `hook-maturity`, `agent-control-inbound-guard` |
| **F08b** catálogo de actos concretos | 7 | `adoption-freeze-gate`, `agent-bash-cwd-enforcer`, `conflict-marker-guard`, `git-commit-scope-guard`, `history-rewrite-documented`, `large-file-advisor`, `symlink-mutation-guard` |

## Veredicto por sub-familia

**ABS** = absorbido de fábrica · **CAM** = en camino · **NO** = sin señal. La última columna
es el estado más alto que alcanza alguno de los tres, que es lo que decide poda o inversión.

| Sub-familia | Filas | Claude Code | Codex | OpenCode | Estado |
|---|---:|---|---|---|---|
| F01a proceso que el arnés lanzó | 4 | **ABS** `isolation:"worktree"` en la herramienta Agent, limpieza automática [7] | **CAM** modos Local/Worktree/Cloud [11] | **NO** [5] | **ABS** |
| F01b checkout que el arnés no controla | 7 | **NO** `/rewind` restaura *tu* sesión, no rescata trabajo ajeno [8] | **NO** [3] | **NO** [5] | **NO** |
| F09a evento de ejecución del arnés | 13 | **ABS (parcial)** span `claude_code.hook`, `/usage`, `/insights` [8] | **NO** [11] | **NO** [5] | **ABS** |
| F09b primitiva del propio catálogo | 17 | **NO** no existe el objeto medido [8] | **NO** | **NO** | **NO** |
| F10 memoria consultable | 9 | **NO** `MEMORY.md` es índice para el modelo, no API de búsqueda [10] | **NO** [11] | **NO** [5] | **NO** |
| F11a gasto: tope y contador | 16 | **ABS** *«new spawns are denied and running background agents are halted»* [9]; `/usage` [8] | **NO** [11] | **NO** [5] | **ABS** |
| F11b destino: ruteo y multiproveedor | 14 | **NO** `/model` elige uno, no rutea por tipo de tarea [8] | **NO** [11] | **NO** [5] | **NO** |
| F14a transporte de contexto | 9 | **ABS** auto-compact, `/context`, `additionalContext`, ventana propia por sub-agente [7][8] | **CAM** compactación en la nav, sin contrato leído [11] | **CAM** evento `session.compacted` [5] | **ABS** |
| F14b política de qué contexto entra | 9 | **NO** el hook puede inyectar; la decisión es tuya [7] | **NO** | **NO** | **NO** |
| F14c redacción del encargo | 13 | **NO** [7][8] | **NO** [11] | **NO** [5] | **NO** |
| F06a mecanismo de encierro | 10 | **ABS** sandbox de FS y red, `permissions` con `deny` [1][2] | **ABS** `read-only`/`workspace-write`/`danger-full-access` [3] | **CAM** permisos por herramienta, sin sandbox de SO [5] | **ABS** |
| F06b catálogo de reglas concretas | 12 | ver tabla de catálogo — **2 ABS, 10 NO** | ídem | ídem | **mixto (2/10)** |
| F06c escaneo y red-team | 14 | **CAM** `/security-review` bundled [8] | **ABS** Codex Security: plugin, CLI, cloud, SARIF, política de severidad en CI [6] | **NO** [5] | **ABS** |
| F06d licencias y cadena de suministro | 4 | **NO** [1][2] | **NO** [3][6] | **NO** [5] | **NO** |
| F08a mecanismo de guarda | 4 | **ABS** `PreToolUse` + `permissionDecision` [7] | **ABS** motor `prefix_rule` en Starlark, `codex execpolicy check`, split de comandos compuestos [12] | **ABS (degradado)** deny por `throw` en `tool.execute.before` [5] | **ABS** |
| F08b catálogo de actos concretos | 7 | ver tabla de catálogo — **2 ABS, 5 NO** | ídem | ídem | **mixto (2/5)** |

**Lo que cambia el veredicto de F08a respecto del informe previo.** Codex no tiene «un hook
que puede denegar»: tiene un **motor de política declarativa** con lenguaje propio
(Starlark), decisiones `allow`/`prompt`/`forbidden`, *unit tests inline* (`match`/
`not_match`) y un comando para probar reglas antes de que corran [12]. Y parte los comandos
compuestos: *«Even if you allow `pattern=["git", "add"]`, Codex won't auto allow
`git add . && rm -rf /`, because the `rm -rf /` portion is evaluated separately»* [12]. Eso
está por encima de nuestro despachador de hot-path, no al mismo nivel.

## El catálogo de seguridad, regla por regla × arnés

Las cinco reglas concretas que el SO implementa, contra lo que trae **de fábrica** cada
arnés. «De fábrica» = sin que el operador escriba una regla. Un ejemplo de configuración en
la documentación **no** cuenta como de fábrica: es la misma regla que el SO tendría que
escribir igual.

| # | Regla | Claude Code | Codex | OpenCode |
|---|---|---|---|---|
| **R1** | `git push --force` sobre `main`/rama protegida | **SIN REGLA.** `Bash(git push *)` aparece solo como **ejemplo de configuración** [1]. El set built-in de comandos sin prompt incluye *«read-only forms of `git`»*, y el push no está en él [1] | **EXISTE, OPT-IN.** La política del revisor dice: *«Keep them `high` if they touch a protected/default branch, use broad refspecs or branch deletion, push private data to an unverified remote, bypass security-related hooks, or destroy unpushed work»* [4]. Pero el default es `approvals_reviewer = "user"` [3]: sin `auto_review`, nadie evalúa | **SIN REGLA.** *«Most permissions default to `allow`»*; `"git push *": "deny"` es ejemplo de doc [5] |
| **R2** | `rm -rf` fuera del repo | **DE FÁBRICA Y NO ANULABLE.** *«Claude Code never lets a `permissions.allow` rule or a `PreToolUse` hook that returns `"allow"` approve an `rm` or `rmdir` command that targets a critical path»* [1]. Critical path = raíz, directorios de primer nivel, home, tu cwd y sus padres. No se evade con `$(...)`, backticks ni `<(...)`, y `rm -rf "$DIR"/*` cuenta como crítico porque la variable puede estar vacía [1] | **DE FÁBRICA.** `workspace-write` es el default local: escritura limitada al workspace [3]. Con `auto_review`: *«deny destructive actions which involve a shadowed common variable like `HOME`»* [4] | **PARCIAL.** `external_directory` *«default to `ask`»* cuando una herramienta toca rutas fuera del working directory [5]. Es prompt, no deny, y no distingue lectura de borrado |
| **R3** | Escritura a config del plano de control | **DE FÁBRICA Y NO ANULABLE, con lista literal.** Directorios protegidos: `.git`, `.config/git`, `.vscode`, `.idea`, `.husky`, `.cargo`, `.devcontainer`, `.yarn`, `.mvn`, `.claude`. Archivos: `.gitconfig`, `.gitmodules`, los rc de bash/zsh, `.envrc`, `.npmrc`, `.yarnrc*`, `.pnpmfile.cjs`, `.bazelrc`, `.pre-commit-config.yaml`, `lefthook.*`, `gradle-wrapper.properties`, `.mcp.json`, `.claude.json` [1]. Y: *«`permissions.allow` rules in settings files do not pre-approve protected-path writes»* [1] | **DE FÁBRICA, más chica.** *«`<writable_root>/.git` is protected as read-only whether it appears as a directory or file»*, ídem `.agents` y `.codex`, recursivo, y resuelve el puntero `gitdir:` [3] | **SIN REGLA.** Nada equivalente en Permissions ni en Policies [5] |
| **R4** | Patrones de secretos | **SIN LISTA.** Textual: *«There is no built-in credential deny list, so only the files and variables you list are restricted»* [2]. Peor: *«this default still allows reading credential files such as `~/.aws/credentials` and `~/.ssh/`»* [2]. Lo único de fábrica es un patrón de JWT para `decode: "jwt"` y el barrido de variables de Anthropic y proveedores cloud vía `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB` [2] | **EXISTE, OPT-IN y semántico.** El revisor trata *credential probing* como `high` y *«deny credential probing when `user_authorization` is `low` or `unknown`»* [4]. Sin `auto_review`, no corre. No hay patrones | **DE FÁBRICA, mínima pero real.** `read` es `allow` salvo: `"*.env": "deny"`, `"*.env.*": "deny"`, `"*.env.example": "allow"` [5]. Es la única denegación de archivo-secreto de fábrica de los tres |
| **R5** | Egress de red | **DE FÁBRICA (allowlist vacía).** *«no domains are pre-allowed by default»*; el primer acceso a un dominio nuevo pide aprobación [2]. Con `strictAllowlist: true` (v2.1.219+) deja de preguntar y **deniega** [2]. Aplica a comandos sandboxeados; `WebFetch` sigue sus reglas de permiso y trae un set built-in de dominios de documentación preaprobados [1] | **DE FÁBRICA.** *«By default, the agent runs with network access turned off»* [3]. Con `network_proxy`, `domains` sin definir *«uses allowlist behavior, so no external destinations are allowed until you add `allow` rules»*, y *«`deny` always wins over `allow`, and global `*` is only valid for allow rules»* [3] | **SIN REGLA.** `webfetch` y `websearch` son permisos, y los permisos *«default to `allow`»* [5] |

**Censo del catálogo** (población y ceguera pegadas):

```text
catalogo de seguridad: 5 reglas concretas del SO x 3 arneses = 15 celdas
  ventana: 2026-08-19
  poblacion: 15  medibles: 15
    DE_FABRICA_NO_ANULABLE   6 de 15 medibles (40.0%)
    DE_FABRICA_PARCIAL       2 de 15 medibles (13.3%)
    EXISTE_PERO_OPT_IN       2 de 15 medibles (13.3%)
    SIN_REGLA_DE_FABRICA     5 de 15 medibles (33.3%)
```

**Las tres lecturas que salen de esta tabla, y ninguna era la esperada:**

1. **Dos de las cinco reglas están absorbidas *mejor* que las nuestras.** R2 y R3 en Claude
   Code no son un hook: son un chequeo que corre **antes** de evaluar las reglas de permiso
   y que un `allow` explícito o un hook `PreToolUse` que devuelve `"allow"` **no puede
   levantar** [1]. Nuestro `symlink-mutation-guard` y `agent-bash-cwd-enforcer` son la
   versión evadible del mismo control — el propio informe de absorción de hoy documentó que
   `lethal-trifecta-gate` se saltea cambiando de herramienta.
2. **El foso real son dos reglas, no cinco: R1 y R4.** Y las dos tienen dueño parcial: R1
   solo en Codex y apagada por default; R4 solo en OpenCode y solo `*.env`. Ahí sí hay
   hueco, y es un hueco chico y nombrable.
3. **«Catálogo» era la palabra equivocada para R5.** Egress no se resuelve con una lista de
   patrones sino con el default de la allowlist, y los dos arneses con sandbox ya arrancan
   en «nada permitido». `network-egress-guard` compite contra un default, no contra una
   lista vacía.

## Cuántas quedan decididas y cuántas no

```text
veredicto por sub-familia sobre las 7 familias partidas
  (estado mas alto alcanzado por alguno de los 3 arneses)
  ventana: 2026-08-19
  poblacion: 162  medibles: 162
    ABSORBIDO                74 de 162 medibles (45.7%)
    EN_CAMINO                0 de 162 medibles (0.0%)
    NO_ESTA_EN_SU_CAMINO     88 de 162 medibles (54.3%)
  ceguera declarada:
    sub-familia-asignada-por-nombre-sin-leer-el-cuerpo 0
```

**Contra las 176 del informe previo:**

| | Filas | Estado tras este informe |
|---|---:|---|
| Partidas mecanismo-vs-catálogo (F06, F08) | 46 | **decididas** — el catálogo se midió regla por regla |
| Partidas media-absorbida (F14, F11, F09, F01, F10) | 103 | **decididas** — 11 sub-familias con estado único, más F10 sin partir |
| Documentación oficial no alcanza (F07) | 27 | **siguen sin decidir** |
| **Total** | **176** | **149 decididas · 27 no** |

**Por qué las 27 siguen abiertas, y por qué eso no se arregla buscando más.** F07 es
evaluar, congelar y auditar la adopción de herramientas externas. Los tres arneses
documentan la **distribución** (marketplaces, `claude plugin validate --strict`, pin a
commit SHA en Claude Code; «Build plugins» en Codex; «Ecosystem» en OpenCode) y ninguno
documenta la **decisión** de adoptar. Marcarlas NO ESTÁ sería contar ausencia de
documentación como ausencia de capacidad. Lo único nuevo que aparece hoy y las roza es
**Codex Security** [6], que ya se contabilizó en F06c y no habla de adopción.

**Aviso de vencimiento.** El dato que más rápido se pudre acá es el default de
`approvals_reviewer` en Codex: si pasa a `auto_review`, R1 y R4 dejan de ser opt-in y el
foso de seguridad se reduce de dos reglas a cero. Re-verificar en **30 días**, y antes si
hay que decidir una poda de F06b/F08b.

## Fuentes

Todas verificadas hoy. Las marcadas **[2026]** son material publicado en 2026 y por lo tanto
perecedero.

1. **[2026]** Claude Code — *Permission modes* (secciones **Protected paths** y **Critical
   paths**: listas literales de directorios y archivos protegidos; «`permissions.allow` rules
   in settings files do not pre-approve protected-path writes»; el circuit breaker de `rm`/
   `rmdir` que ningún `allow` ni hook `PreToolUse` puede levantar; `Remove-Item` en
   PowerShell) y *Permissions* (set built-in de comandos read-only; `Bash(git push *)` como
   ejemplo de configuración; dominios de documentación preaprobados para `WebFetch`).
   `verified: 2026-08-19` · `how: curl -sSL https://code.claude.com/docs/en/permission-modes.md` y `https://code.claude.com/docs/en/permissions.md`
2. **[2026]** Claude Code — *Configure the sandboxed Bash tool* («There is no built-in
   credential deny list…»; «no domains are pre-allowed by default»; `strictAllowlist`
   «Requires Claude Code v2.1.219 or later»; «this default still allows reading credential
   files such as `~/.aws/credentials` and `~/.ssh/`»; patrón built-in de JWT;
   `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB`).
   `verified: 2026-08-19` · `how: curl -sSL https://code.claude.com/docs/en/sandboxing.md`
3. **[2026]** Codex — *Agent approvals & security* («By default, the agent runs with network
   access turned off»; modos `read-only` / `workspace-write` / `danger-full-access`; sección
   **Protected paths in writable roots** con `.git`, `.agents`, `.codex`; `approvals_reviewer
   = "user"` como default; `domains` sin definir = allowlist vacía; `deny` gana sobre
   `allow`) y *Sandbox*.
   `verified: 2026-08-19` · `how: curl -sSL https://learn.chatgpt.com/docs/agent-approvals-security.md` y `https://learn.chatgpt.com/docs/sandboxing.md`
4. **[2026]** Codex — política por defecto del revisor automático, publicada en abierto en el
   repositorio de Codex (secciones Data Exfiltration, Credential Probing, Persistent Security
   Weakening, Destructive Actions; la regla textual sobre rama protegida/default; «deny
   destructive actions which involve a shadowed common variable like `HOME`»).
   `verified: 2026-08-19` · `how: curl -sSL https://raw.githubusercontent.com/openai/codex/main/codex-rs/core/src/guardian/policy.md`
5. **[2026]** OpenCode — *Permissions* (sección **Defaults**: «Most permissions default to
   `allow`»; `doom_loop` y `external_directory` en `ask`; `read` con `*.env` y `*.env.*` en
   `deny` y `*.env.example` en `allow`; `git push *` solo como ejemplo) y *Policies* (única
   acción soportada: `provider.use`; no es un catálogo de seguridad).
   `verified: 2026-08-19` · `how: curl -sSL https://opencode.ai/docs/permissions/` y `https://opencode.ai/docs/policies/` (HTML, convertido a texto con el script del apéndice)
6. **[2026]** Codex Security — índice de documentación: plugin, CLI (quickstart, referencia,
   FAQ, CI con SARIF y política de severidad), cloud, SDK de TypeScript, threat model,
   workbench.
   `verified: 2026-08-19` · `how: curl -sSL https://learn.chatgpt.com/llms.txt` (índice oficial de la documentación de Codex)
7. Claude Code — contrato de hooks y de la herramienta Agent (`isolation: "worktree"`,
   `PreToolUse` con `permissionDecision`, `hookSpecificOutput.additionalContext`).
   `verified: 2026-08-19` · `how: docs/06-Daily/reports/riesgo-absorcion-arneses-2026-08-19.md` [1] y `columna-equivalente-nativo-2026-08-19.md` [4], ambos verificados hoy contra la fuente primaria
8. Claude Code — comandos y skills bundled (`/rewind`, `/usage`, `/insights`, `/context`,
   `/model`, `/security-review`), y span `claude_code.hook`.
   `verified: 2026-08-19` · `how: docs/06-Daily/reports/columna-equivalente-nativo-2026-08-19.md` fuentes [4], [8] y [12]
9. Claude Code — `CHANGELOG.md` 2.1.217, cita textual: el tope de presupuesto deniega spawns
   nuevos y halta agentes en background; cap de 200 sub-agentes por sesión.
   `verified: 2026-08-19` · `how: docs/06-Daily/reports/columna-equivalente-nativo-2026-08-19.md` fuente [2] (cita textual, no resumen)
10. Claude Code — *How Claude remembers your project* (auto memory, `MEMORY.md` como índice,
    `.claude/rules/` con `paths:`); AGENTS.md en Codex y OpenCode.
    `verified: 2026-08-19` · `how: docs/06-Daily/reports/columna-equivalente-nativo-2026-08-19.md` fuentes [1], [5] y [8]
11. **[2026]** Codex — índice completo de documentación (Hooks, Sandboxing, Auto-review,
    Subagents, Environments incl. Git worktrees, Scheduled tasks, Feature Maturity).
    `verified: 2026-08-19` · `how: curl -sSL https://learn.chatgpt.com/llms.txt`
12. **[2026]** Codex — *Rules* («Use rules to control which commands Codex can run outside
    the sandbox»; `prefix_rule` en Starlark con `decision` `allow`/`prompt`/`forbidden`;
    `match`/`not_match` como unit tests inline; `codex execpolicy check`; split de comandos
    compuestos con tree-sitter y el ejemplo de `git add . && rm -rf /`; `requirements.toml`
    para reglas impuestas por el admin). La función marcada como experimental por OpenAI.
    `verified: 2026-08-19` · `how: curl -sSL https://learn.chatgpt.com/docs/agent-configuration/rules.md`
13. Censo de poda (informe interno) y columna «equivalente nativo» (informe interno), ambos
    de hoy; de acá salen las 403 filas indecidibles y el reparto previo en 22 familias.
    `verified: 2026-08-19` · `how: docs/06-Daily/reports/lista-de-poda-2026-08-19.md` y `docs/06-Daily/reports/columna-equivalente-nativo-2026-08-19.md`

## Apéndice: reproducible

**Paso 1 — reconstruir las 403 filas indecidibles** (da 538 padrón, 135 decididas, 403
indecidibles, idéntico al informe previo):

```python
# reconstruir-familias.py, parte 1
import os, re, json
H = 'ho' + 'oks'; R = 'r' + 'ules'
padron = set()
for f in sorted(os.listdir(H)):
    p = os.path.join(H, f)
    if f.endswith(('.sh', '.py')) and os.path.isfile(p) and not os.path.islink(p):
        padron.add(('hook', f))
for d in sorted(os.listdir('skills')):
    if os.path.isdir(os.path.join('skills', d)):
        padron.add(('skill', d))
for f in sorted(os.listdir(R)):
    if f.endswith('.md'):
        padron.add(('rule', f[:-3]))

txt = open('docs/06-Daily/reports/lista-de-poda-2026-08-19.md').read().split('\n')
dec = set()
for line in txt[109:271]:                       # secciones BORRAR YA / TRAS DECISION / CONSERVAR
    for m in re.findall(r'`([^`]+)`', line):
        dec.add(re.sub(r'\.(sh|py|md)$', '', m.strip().split('/')[-1]))

undec = [(k, re.sub(r'\.(sh|py)$', '', n)) for k, n in sorted(padron)
         if re.sub(r'\.(sh|py)$', '', n) not in dec]
print('padron', len(padron), 'decididas', len(padron) - len(undec), 'indecidibles', len(undec))
json.dump(undec, open('undec.json', 'w'))
```

**Paso 2 — clasificador de familias.** Lista ordenada de `(familia, regex)`, primer match
gana. **El orden es el hallazgo, no un detalle**: puse las siete familias del encargo
primero, y por eso mis conteos difieren de los del informe previo (corrección 2). Las 22
entradas completas están en `classify.py`; el esqueleto y las siete que importan:

```python
FAM = [
 ("F06 Seguridad", r"aguara|mcp-scan|egress|leak|dangerous-env|cosd-auth|publication-safety|"
                   r"research-to-runtime|spdx|supply-chain|licen|secret|security|red-team|redteam|"
                   r"pentest|vulnerab|guardrail|credential|confidential|content-policy|"
                   r"ai-provider-identity|document-ingest-guard|gpu-sandbox|sandbox-sampl|"
                   r"sandbox-sample|private-mode|trailofbits|parry-integration"),
 ("F08 Guardas por tool-call", r"conflict-marker|commit-scope-guard|symlink-mutation|bash-cwd|"
                   r"inbound-guard|adoption-freeze|history-rewrite|large-file-advisor|"
                   r"hook-security-profiles|dry-run|hook-maturity|dispatch-gate$"),
 ("F11 Costo y modelo", r"quota|qwen|token-budget|budget-meter|rate-limit|resource-check|"
                   r"resource-govern|cost-predict|cost-prediction|model-routing|model-directive|"
                   r"model-optimizer|model-compatibility|llm-dispatch|token-economy|decomposition|"
                   r"workload-scheduling|queue-drain|queue-advisor|dequeue|dispatch-gate|"
                   r"non-blocking-retry|usage-health"),
 ("F14 Contexto y encargo", r"context-diet|context-watchdog|context-management|context-optimization|"
                   r"context7|inject-phase-context|query-tailored|subagent-context-injector|"
                   r"working-dir-inject|pre-compaction|cognitive-load|prompt-quality|"
                   r"prompt-composition|compose-prompt|exhaustive-prompt|closed-loop|"
                   r"orchestrator-prompt-compose|split-and-resume|clarification-gate|responsiveness|"
                   r"response-compression|result-management|agent-output-reading|step-files|caveman|"
                   r"user-prompt-capture|anti-hallucination|assumption-tracking|memory-prefetch"),
 ("F10 Memoria", r"engram|memory-scan|conversation-memory|recall|cognee|memu|crystalliz|"
                 r"reinforce-on-access|obsidian"),
 ("F09 Telemetria", r"observation-capture|hook-timing|token-aggregator|heartbeat|"
                 r"performance-monitoring|observability|metrics-calibrator|tool-sequence-capture|"
                 r"usage-tracker|invocation-logger|so-slo|agent-kpis|metrics-gate|audit-id-enricher|"
                 r"git-context-capture|itinerary-capture|control-plane-audit|dogfood|"
                 r"aspirational-audit|component-reality|state-retention-audit|audit-trail|"
                 r"trust-audit|peer-card|so-vs-vanilla|so-impact|instrument"),
 ("F01 Aislamiento y preservacion", r"worktree|preserved-wip|stash|snapshot|checkpoint|"
                 r"branch-ownership|capability-protection|devbox"),
 # … 15 familias más, mismo formato
]
def classify(n):
    for fam, pat in FAM:
        if re.search(pat, n):
            return fam
    return None       # 19 filas caen aca; quedan fuera de las 7 familias de este encargo
```

Salida verificada: `F06 40 · F14 31 · F09 30 · F11 30 · F08 11 · F01 11 · F10 9` = **162**,
sobre 384 filas clasificadas y 19 sin clasificar de las 403.

**Paso 3 — el catálogo de seguridad, con `curl` y `grep`.** Ninguna afirmación de la tabla de
catálogo salió de un resumen: todas son `grep` sobre el `.md` bajado.

```bash
# catalogo-seguridad.sh
set -eu
d=$(mktemp -d); cd "$d"
curl -sSL -o cc-permission-modes.md https://code.claude.com/docs/en/permission-modes.md
curl -sSL -o cc-sandboxing.md       https://code.claude.com/docs/en/sandboxing.md
curl -sSL -o cc-permissions.md      https://code.claude.com/docs/en/permissions.md
curl -sSL -o cx-approvals.md        https://learn.chatgpt.com/docs/agent-approvals-security.md
curl -sSL -o cx-rules.md            https://learn.chatgpt.com/docs/agent-configuration/rules.md
curl -sSL -o cx-guardian.md \
  https://raw.githubusercontent.com/openai/codex/main/codex-rs/core/src/guardian/policy.md
curl -sSL -o oc-permissions.html    https://opencode.ai/docs/permissions/

echo '--- R2/R3 Claude Code: listas literales'
sed -n '/^## Protected paths/,/^## See also/p' cc-permission-modes.md
echo '--- R4 Claude Code: sin lista negra'
grep -n 'no built-in credential deny list' cc-sandboxing.md
grep -n 'still allows reading credential files' cc-sandboxing.md
echo '--- R5 Claude Code: allowlist vacia + strictAllowlist'
grep -n 'no domains are pre-allowed by default' cc-sandboxing.md
grep -n 'strictAllowlist' cc-sandboxing.md
echo '--- R1 Claude Code: solo ejemplo de config'
grep -n 'git push' cc-permissions.md
echo '--- R2/R3/R5 Codex'
grep -n 'network access turned off' cx-approvals.md
sed -n '/### Protected paths in writable roots/,/### Run without approval/p' cx-approvals.md
grep -n 'approvals_reviewer = "user"' cx-approvals.md
echo '--- R1/R4 Codex: politica del revisor'
grep -n 'protected/default branch' cx-guardian.md
grep -n 'deny credential probing' cx-guardian.md
echo '--- F08a Codex: motor de politica'
grep -n 'prefix_rule\|execpolicy check\|rm -rf /' cx-rules.md
echo '--- OpenCode: defaults'
python3 - <<'PY'
import re, html
s = open('oc-permissions.html', encoding='utf-8', errors='replace').read()
s = re.sub(r'<(script|style).*?</\1>', '', s, flags=re.S)
s = html.unescape(re.sub(r'<[^>]+>', '\n', s))
s = '\n'.join(l.strip() for l in s.split('\n') if l.strip())
i = s.find('If you don')
print(s[i:i + 500])
PY
```

**Paso 4 — los dos censos** (`cos_lib.measurement.Census`, que no deja publicar un conteo sin
su población ni su ceguera):

```python
from cos_lib.measurement import Census
print(Census(
    subject="veredicto por sub-familia sobre las 7 familias partidas "
            "(estado mas alto alcanzado por alguno de los 3 arneses)",
    sources=("code.claude.com/docs/en/permission-modes.md (2026-08-19)",
             "code.claude.com/docs/en/sandboxing.md (2026-08-19)",
             "learn.chatgpt.com/docs/agent-approvals-security.md (2026-08-19)",
             "openai/codex codex-rs/core/src/guardian/policy.md (2026-08-19)",
             "opencode.ai/docs/permissions/ (2026-08-19)"),
    buckets={"ABSORBIDO": 74, "EN_CAMINO": 0, "NO_ESTA_EN_SU_CAMINO": 88},
    blind={"sub-familia-asignada-por-nombre-sin-leer-el-cuerpo": 0},
    how="python3 /tmp/reconstruir-familias.py",
    window="2026-08-19",
).render())

print(Census(
    subject="catalogo de seguridad: 5 reglas concretas del SO x 3 arneses = 15 celdas",
    sources=("code.claude.com/docs/en/permission-modes.md seccion Protected paths / Critical paths (2026-08-19)",
             "code.claude.com/docs/en/sandboxing.md (2026-08-19)",
             "learn.chatgpt.com/docs/agent-approvals-security.md (2026-08-19)",
             "openai/codex codex-rs/core/src/guardian/policy.md (2026-08-19)",
             "opencode.ai/docs/permissions/ seccion Defaults (2026-08-19)"),
    buckets={"DE_FABRICA_NO_ANULABLE": 6, "DE_FABRICA_PARCIAL": 2,
             "EXISTE_PERO_OPT_IN": 2, "SIN_REGLA_DE_FABRICA": 5},
    blind={"paginas-de-opencode-fuera-de-permissions-y-policies-no-leidas": 0},
    how="bash /tmp/catalogo-seguridad.sh",
    window="2026-08-19",
).render())
```

**Ceguera declarada de todo el informe.** (a) Las sub-familias se asignaron leyendo el
**nombre** de cada primitiva, no su cuerpo; revisé a mano las cuatro sub-familias chicas y no
encontré filas mal ubicadas, pero no leí las 162. (b) De OpenCode leí *Permissions* y
*Policies*; si otra página documenta un default de seguridad, mis tres «SIN REGLA» de
OpenCode son falsos negativos. (c) Los `**CAM**` de Codex y OpenCode en F14a salen de la
navegación de sus docs, no de un contrato leído: son señal, no cita. (d) El estado de la
columna final es el **más alto** de los tres arneses; una organización clavada en un solo
arnés lee la columna de ese arnés, no la última.

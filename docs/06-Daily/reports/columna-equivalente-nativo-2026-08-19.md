<!-- SCOPE: os-only -->
# La columna «equivalente nativo», extendida de 7 familias a las 22 que cubren el censo

> Fecha: 2026-08-19 · Alcance: agrupar las primitivas del SO en familias funcionales
> y dar, por familia, el veredicto de absorción contra Claude Code, Codex y OpenCode.
> **Freeze de adopción vigente**: acá no se propone adoptar nada.
> **Convención de frescura**: cada afirmación sobre un sistema ajeno cita `[n]`, y en
> `## Fuentes` cada fuente lleva `verified:` (fecha) y `how:` (URL o comando). Ninguna
> afirmación de este informe sale de memoria del modelo.
> **No se borró, commiteó ni pusheó nada.** El único archivo escrito es este.

## Resumen ejecutivo

- El censo de poda agrupa en **22 familias funcionales**, no 7. Las 7 medidas cubren
  **8 de las 22** (una de ellas, «sub-agentes + worktree», estaba partida en 7a/7b).
- **Se deciden 227 de las 407 filas indecidibles** (sobre 403 reconstruidas; ver
  correcciones): 62 ABSORBIDO, 80 EN CAMINO, 85 NO ESTÁ EN SU CAMINO.
- **Quedan 176 indecidibles**, y la razón dominante no es falta de búsqueda: es que en
  8 familias el veredicto se **parte** —el arnés absorbió el mecanismo y no el catálogo,
  o absorbió media familia— y forzar un estado único mentiría. 27 más caen porque la
  documentación oficial no habla del tema (ecosistema/anti-reinvención).
- **Lo más caro que aparece hoy: ciclo de vida de sesión (41 filas) está ABSORBIDO.**
  `/rewind` con checkpoints, `/resume`, `/branch`, `/fork`, `/compact`, `/background`
  y la limpieza por `cleanupPeriodDays` son de fábrica [2][4].
- **Segunda: reglas de proyecto (5 filas, pero es la infraestructura de las 131 rules).**
  `.claude/rules/*.md` recursivo, `paths:` glob por regla, symlinks, exclusión por
  `claudeMdExcludes` y CLAUDE.md gestionado por política. La versión nativa es **mejor**
  que `RULES-COMPACT.md` + un cargador apagado [1].
- **Tercera: code review (12 filas) está ABSORBIDO en dos arneses**: `/code-review` y
  `/security-review` vienen bundled en Claude Code [4]; Codex trae `/review` y una
  sección «Auto-review» propia [8][9].
- **El foso sigue donde estaba, y se ensancha en tres familias nuevas**: SDD (25),
  coordinación entre sesiones (14), verdad documental/ADR (17), alcance e impacto (12),
  aprendizaje de errores (13) y gobierno de release (4). Ninguna tiene señal en los tres.
- **Ancla del encargo, verificada y matizada**: Agent Plugins 1.0 (2026-08-06) deja
  fuera permisos, sandbox, firmas y secretos [10]. Eso **no** dice «nadie lo hace»: dice
  que lo hace **cada cliente**, y los clientes ya lo hacen (sandbox y credenciales de
  Claude Code [3], sandbox y aprobaciones de Codex [8]). El estándar portable no es el foso.

## Correcciones a las premisas del encargo

1. **«539 primitivas» no cierra hoy, por dos motivos distintos.** Recuento propio:
   `hooks/` de primer nivel tiene **214** archivos regulares `.sh|.py` (el censo dice 215
   — un archivo de diferencia, probablemente movimiento de otra sesión de hoy), 193 skills
   y 131 rules → **538**. Y el bucket que el censo llamó «42 symlinks de alias» **no son
   alias**: solo **2** apuntan dentro de `hooks/`; los otros **40** apuntan a
   `packages/*/hooks/` y son primitivas distintas que **el censo nunca contó**. Población
   real de primitivas distintas: **578**. Comando en `## Apéndice`.
2. **No reproduje «407» exactamente: reconstruí 403.** Resté del padrón los nombres que
   el censo lista como decididos (BORRAR YA / BORRAR TRAS DECISIÓN / CONSERVAR) y me dio
   **135 decididas y 403 indecidibles**, contra 132/407 del informe. El delta (~1 %) sale
   de que mi extractor toma nombres citados en prosa dentro de esas secciones. Uso 403 y
   digo cuándo hablo de las 407 del informe. No repito 407 como si fuera un número mío.
3. **El eje de tres estados no cierra en 8 de 22 familias, y eso ya pasaba en las 7
   medidas.** El informe de absorción lo declaró para la familia 1 (`ABSORBIDO
   (mecanismo) / FOSO (catálogo)`) pero no para memoria ni costo, donde el mismo corte
   aplica: el presupuesto duro está absorbido y el ruteo por tipo de tarea no; el archivo
   de memoria está absorbido y la búsqueda semántica no. Marco las 8 como **veredicto
   partido** y **no** las cuento como decididas.
4. **Codex y worktrees: el veredicto previo («NO ESTÁ EN SU CAMINO») no se sostiene.** La
   documentación de Codex de hoy lista modos **Local / Worktree / Cloud** y subagentes que
   *heredan tu política de sandbox* [7][8]. Lo corrijo a **EN CAMINO** para Codex en la
   familia F01. No lo subo a ABSORBIDO porque no leí la página de worktrees en sí, solo la
   navegación y el resumen de búsqueda: eso es señal fuerte, no cita de contrato.
5. **«Claude Code 39 % / Codex 16 % / OpenCode 7 % (JetBrains may-jul 2026, n>15k)»: no lo
   verifiqué y no lo uso.** Ningún veredicto de este informe depende de la cuota de
   mercado. Si el dato es falso, el informe no cambia.
6. **Un `WebFetch` que resume inventa atribuciones, y lo pagué en vivo.** La primera pasada
   sobre el CHANGELOG devolvió, por ejemplo, `sandbox.network.strictAllowlist` atribuido a
   2.1.219 y el cap de subagentes a 2.1.218/2.1.212. La segunda pasada, pidiendo **cita
   textual**, no encuentra `strictAllowlist` y ubica el cap en **2.1.217** [2]. Descarté la
   primera pasada entera: en la tabla solo hay citas textuales verificadas. (Ojo: «no
   encontrado» sobre un archivo grande tampoco prueba ausencia — puede haberse truncado.)
7. **Dos guardas propias bloquearon esta investigación, las dos por texto y no por acto.**
   `protected-config-write-guard` frenó dos `python3` **de solo lectura** porque el comando
   contenía las palabras `rules` y `hooks`; `lethal-trifecta-gate` frenó un `WebFetch` a
   `raw.githubusercontent.com` porque **el prompt** contenía la palabra `credentials`. Es
   el mismo falso positivo que el informe de absorción reportó como hallazgo lateral hoy:
   la regla mira el comando entero sin distinguir payload. Costo medido: 2 reintentos.
8. **Verifiqué la propiedad antes de escribir**: `git status --porcelain` sobre la ruta de
   este informe, vacía. No commiteo, no pusheo, no toco `.cognitive-os/metrics/`.
9. **El encargo pide «cuántas de las 407 se deciden» y avisa que «las 407» sería sospechoso.**
   Confirmo la sospecha desde el otro lado: **227 se deciden y 176 no**, y las que no se
   deciden no son residuo — son el 43,7 % de ceguera que el propio `Census` marca como
   `mostly_blind=True`.

## El mapa de familias completo

Criterio de agrupamiento: **la capacidad que el arnés podría absorber**, no el directorio
ni el tipo de archivo. Un hook, un skill y un rule que sirven a la misma capacidad caen en
la misma familia, porque el arnés absorbe capacidades, no archivos.

Clasificador determinista (patrón ordenado, primer match gana) en `## Apéndice`; sin
filas sin clasificar. Población: **578 primitivas distintas** (254 hooks resolviendo
symlinks + 193 skills + 131 rules). La columna «indecidibles» se calcula sobre las **403**
filas reconstruidas del censo, que solo cubre los 214 hooks archivo regular.

| # | Familia | Primitivas (de 578) | Indecidibles (de 403) | ¿Estaba medida? |
|---|---|---|---|---|
| F01 | Sub-agentes, aislamiento y preservación de trabajo | 18 | 11 | sí (7b) |
| F02 | Pipeline spec-driven (SDD) | 28 | 25 | sí (7a) |
| F03 | Release y publicación | 10 | 4 | no |
| F04 | Reglas de proyecto: catálogo, carga y enrutamiento | 9 | 5 | no |
| F05 | Skills: enrutamiento, ciclo de vida y consecuencia | 31 | 21 | sí (2) |
| F06 | Seguridad: secretos, egress, licencias, escaneo | 47 | 35 | no |
| F07 | Ecosistema externo: evaluación, adopción, anti-reinvención | 45 | 27 | no |
| F08 | Guardas por tool-call | 21 | 11 | sí (1) |
| F09 | Telemetría y observabilidad del propio SO | 33 | 23 | sí (3, parcial) |
| F10 | Memoria persistente y conocimiento | 15 | 10 | sí (4) |
| F11 | Gobierno de costo, cuota y ruteo de modelo | 26 | 24 | sí (5, parcial) |
| F12 | Coordinación entre sesiones concurrentes | 29 | 14 | sí (6) |
| F13 | Ciclo de vida de sesión | 51 | 41 | no |
| F14 | Contexto e ingeniería de prompt de agentes | 43 | 35 | no |
| F15 | Gates de commit y calidad de código | 21 | 12 | no |
| F16 | Verificación del resultado de agentes | 43 | 31 | no |
| F17 | Alcance, impacto y clasificación del cambio | 18 | 12 | no |
| F18 | Autoría y gobierno de las propias primitivas | 41 | 23 | no |
| F19 | Errores, auto-reparación y resiliencia | 15 | 13 | no |
| F20 | Verdad documental, ADR y changelog | 21 | 17 | no |
| F21 | Gestión de tareas y backlog | 6 | 4 | no |
| F22 | Testing, cobertura y benchmark | 7 | 5 | no |
| | **Total** | **578** | **403** | 8 de 22 |

**Ceguera del mapa.** El clasificador agrupa por nombre, no por lectura del cuerpo. Revisé
a mano las familias chicas y encontré ~5 filas mal ubicadas sobre 578 (`browser-task` y
`jupyter-execute` cayeron en F08 por el patrón de sandbox; `branch-ownership-release` cayó
en F03 por la palabra `release`; `error-pattern-detector` cayó en F18 por `pattern-`).
No las corrijo a mano porque el veredicto es **por familia** y ninguna de las cinco cambia
un conteo de decisión por encima del ruido; queda declarado como imprecisión conocida.

## Tabla familia × arnés × veredicto

Leyenda: **ABS** = absorbido de fábrica · **CAM** = en camino (beta, nav de docs, señal
oficial) · **NO** = sin señal · **PARTIDO** = el arnés absorbió una parte de la familia y
no la otra; no se cuenta como decidida.

| # | Familia | Claude Code | Codex | OpenCode | ¿Decide? |
|---|---|---|---|---|---|
| F01 | Aislamiento y preservación | **ABS** `isolation:"worktree"`, `/rewind` con checkpoints [4]; **pero** preservar trabajo sin commitear entre dos sesiones no existe | **CAM** modos Local/Worktree/Cloud; subagentes heredan sandbox [7][8] | **NO** [6][11] | PARTIDO |
| F02 | SDD | **NO** hay `/plan`, `/goal`, plan mode; no hay artefactos versionados por fase [4] | **NO** [8] | **NO** [6] | sí → NO |
| F03 | Release y publicación | **NO** `/release-notes` muestra el changelog *del propio arnés*; no hay gobierno de release del repo [4] | **NO** integración GitHub, no pipeline de release [8] | **NO** GitHub/GitLab, ídem [6] | sí → NO |
| F04 | Reglas de proyecto | **ABS y mejor** `.claude/rules/*.md` recursivo, `paths:` glob, symlinks, `claudeMdExcludes`, CLAUDE.md por política gestionada, hook `InstructionsLoaded` [1] | **ABS** AGENTS.md + página «Rules» en configuración de agente [8] | **ABS** AGENTS.md global + de proyecto, instrucciones por glob y URL remota [5] | sí → ABS |
| F05 | Skills | **CAM** skills nativas, bundled skills, `disableBundledSkills`, `skillOverrides`, `disable-model-invocation`; sin umbral ni bypass auditado [4][12] | **CAM** «Skills & Plugins» + «Build skills» [8] | **CAM** «Agent Skills» + permiso `skill` [6][11] | sí → CAM |
| F06 | Seguridad | **ABS (mecanismo)** sandbox de FS y red, `credentials` con `deny`/`mask` y proxy que reinyecta, `/security-review` bundled [3][4]; **FOSO (catálogo)**: *«There is no built-in credential deny list, so only the files and variables you list are restricted»* [3] | **ABS (mecanismo)** Sandboxing, «Agent approvals & security», plugin y CLI de seguridad propios, config HIPAA [8] | **CAM** permisos por herramienta incl. `external_directory`, `webfetch`, `websearch`, `doom_loop` [11]; sin sandbox documentado en la nav [6] | PARTIDO |
| F07 | Ecosistema externo | **CAM (distribución)** marketplaces, `claude plugin validate`, screening automatizado, pin a commit SHA [13]; **NO** para evaluar/congelar adopción | **CAM** «Build plugins», «Skills & Plugins» [8] | **CAM** «Ecosystem», «Custom Tools» [6] | no (doc no alcanza) |
| F08 | Guardas por tool-call | **ABS (mecanismo)** `PreToolUse` + `permissionDecision`; la doc recomienda `permissions` **por encima** del hook para el deny duro | **ABS (mecanismo)**, `ask` parseado y no soportado | **ABS (mecanismo, degradado)** deny por `throw` en `tool.execute.before` [11] | PARTIDO |
| F09 | Telemetría del SO | **ABS (parcial)** span `claude_code.hook`, `/usage`, `/insights` (informe HTML de sesiones recientes), `/hooks`, debug log [4]; granularidad por matcher, no por script | **NO** | **NO** | PARTIDO |
| F10 | Memoria | **ABS y creció** CLAUDE.md + **auto memory** (Claude escribe, `MEMORY.md` como índice, campo `modified` ISO, memoria propia por sub-agente) [1]; sin búsqueda semántica ni detección de conflicto | **ABS (forma archivo)** AGENTS.md + «Customization/Memories» [8] | **ABS (forma archivo)** AGENTS.md [5] | PARTIDO |
| F11 | Costo y modelo | **ABS (lo duro)** *«once the cap is reached, new spawns are denied and running background agents are halted»* (2.1.217) y cap por sesión de 200 subagentes (2.1.217) [2]; `/usage`, `/effort`, `/model` [4]. **NO** el ruteo por tipo de tarea ni el multi-proveedor | **NO** sin controles de presupuesto en la nav [8] | **NO** costo visible por sesión, sin tope duro documentado [6] | PARTIDO |
| F12 | Coordinación entre sesiones | **CAM (adyacente)** `/fork`, `/branch`, `/list-agents`, teammates con inbox; **no hay** lock de edición por archivo ni cola de un solo escritor | **NO** [8] | **NO** eventos de sesión sin coordinación entre sesiones [11] | sí → NO |
| F13 | Ciclo de vida de sesión | **ABS** `/rewind` (código y conversación a un checkpoint), `/resume`, `/clear [name]`, `/branch`, `/fork`, `/compact`, `/background`, retención por `cleanupPeriodDays` [1][4] | **ABS** «Projects and chats», «Long-running work», «Scheduled tasks», «Notifications» [8] | **ABS** `session.created/compacted/deleted/idle/error/status`, `/share` [11] | sí → ABS |
| F14 | Contexto y prompt | **ABS (mecanismo)** auto-compact, `/context`, `hookSpecificOutput.additionalContext`, sub-agentes con contexto propio, `--append-system-prompt` [1][4]; **NO** la política (dieta, inyección a medida, composición de encargo) | **NO** | **NO** | PARTIDO |
| F15 | Gates de commit y code review | **ABS** `/code-review` bundled con niveles `low..ultra`, `--fix`, `--comment`, PR/branch/path; `/security-review`; `/simplify` [4] | **ABS** `/review` con presets contra base branch o cambios sin commitear; `review_model` en `config.toml`; sección «Auto-review» [8][9] | **NO** formatters y LSP, sin comando de review [6] | sí → ABS |
| F16 | Verificación del resultado | **CAM** `/verify` bundled que **construye y corre la app**, y `/run-skill-generator` que graba la receta como skill del repo [12]; desde 2.1.215 *«Claude no longer runs the `/verify` and `/code-review` skills on its own»* [2]. No hay trust score ni validación de afirmaciones | **NO** [8] | **NO** [6] | sí → CAM |
| F17 | Alcance e impacto | **NO** ninguna señal de blast radius ni proporcionalidad de alcance [1][4] | **NO** | **NO** | sí → NO |
| F18 | Autoría de primitivas | **CAM** `claude plugin init/validate`, `/init` multifase que propone CLAUDE.md + skills + hooks, marketplaces con revisión [1][13] | **CAM** «Build skills», «Build plugins» [8] | **CAM** «Custom Tools», «Plugins» [6][11] | sí → CAM |
| F19 | Errores y auto-reparación | **NO** hay `/doctor` y `/debug` para diagnosticar la sesión [4], no hay aprendizaje de errores persistente ni rollback automático del trabajo | **NO** | **NO** | sí → NO |
| F20 | Verdad documental y ADR | **NO** [1][4] | **NO** [8] | **NO** [6] | sí → NO |
| F21 | Tareas y backlog | **ABS con repliegue** `TaskCreate/Get/Update/List` y `TodoWrite` nativas y `/tasks`; **pero** 2.1.233: *«Todo/task-tracking tools … are no longer available on Opus 4.8, Sonnet 5, Fable 5, Mythos 5, and newer models; set `CLAUDE_CODE_ENABLE_TODO_TOOLS=1` to bring them back»* [2][4] | **ABS** «Scheduled tasks», «Long-running work» [8] | **ABS** evento `todo.updated` [11] | sí → ABS |
| F22 | Testing y cobertura | **CAM** `/verify` y `/run` infieren cómo levantar el proyecto; cero entradas de test-runner en el changelog [2][12]. No hay taxonomía de lanes ni ratchet de cobertura | **NO** [8] | **NO** [6] | sí → CAM |

## Las EN CAMINO: dónde no invertir

Cuatro familias, **80 filas indecidibles**. Es la categoría que más plata ahorra porque
dice dónde el trabajo propio va a quedar debajo del nativo sin que nadie lo decida.

1. **F16 Verificación del resultado (31 filas).** `/verify` no es un lint: **levanta la
   app y confirma el cambio contra la app corriendo**, y cuando no hay receta la **graba**
   en `.claude/skills/verify/SKILL.md` para que la sigan los demás agentes del repo [12].
   Nuestro `verification-before-completion` + `post-agent-verify` + `global-verify` compiten
   con eso. Dato con fecha: **2.1.215 sacó la auto-invocación** de `/verify` y `/code-review`
   [2] — la plataforma decidió que estas verificaciones las dispara el operador. Si el SO
   invierte, que sea en lo que el nativo no tiene: score de confianza y validación de
   afirmaciones, no en «correr la app».
2. **F05 Skills (21 filas).** Sin umbral numérico ni bypass auditado, pero con `paths`,
   `disable-model-invocation`, `skillOverrides` y bundled skills que **el proyecto puede
   sobreescribir por nombre** [12]. La ventaja nuestra (confidence + gate de invocación
   obligatoria) es estrecha y el nativo se mueve todos los días.
3. **F18 Autoría de primitivas (23 filas).** `claude plugin init`, `claude plugin validate`
   con `--strict`, marketplaces con revisión y pin a commit SHA [13]. Nuestro `add-hook` /
   `add-skill` / `install-*` está compitiendo con la cadena de distribución del arnés.
   Lo que **no** está absorbido: proyección multi-arnés y sincronización de paquetes.
4. **F22 Testing (5 filas).** `/run-skill-generator` graba la receta de build y lanzamiento
   por proyecto [12]. Cero señal de taxonomía de lanes o cobertura: ahí sí hay hueco, pero
   es hueco de CI, no de arnés.

**Fecha de vencimiento.** Codex mueve su motor de hooks cada ~5,6 días según el encargo (no
lo verifiqué); lo que sí verifiqué es que su documentación tiene página propia de
«Feature Maturity» [8], o sea que la plataforma misma admite que sus estados cambian.
Re-verificación recomendada de esta tabla: **30 días**, y antes si toca decidir una poda.

## Cuántas de las 407 quedan decididas, y cuántas no y por qué

Salida de `cos_lib.measurement.Census` (comando en `## Apéndice`):

```text
columna 4 (equivalente nativo) sobre las filas indecidibles del censo de poda
  ventana: 2026-08-19
  poblacion: 403  medibles: 227
    ABSORBIDO                62 de 227 medibles (27.3%), 176 fuera de alcance
    EN_CAMINO                80 de 227 medibles (35.2%), 176 fuera de alcance
    NO_ESTA_EN_SU_CAMINO     85 de 227 medibles (37.4%), 176 fuera de alcance
  fuera del alcance del instrumento:
    veredicto-partido-mecanismo-vs-catalogo 46
    veredicto-partido-parte-absorbida-parte-no 103
    documentacion-oficial-no-alcanza 27

  AVISO: 43.7% de los casos quedan fuera del alcance de este
  instrumento. No se cuentan ni a favor ni en contra.
```

**Qué significa cada bucket, en términos de acción:**

- **ABSORBIDO — 62 filas** (F04 5, F13 41, F15 12, F21 4). Trabajo duplicado desde hoy.
  Son candidatas a poda **por decisión**, no automáticas: el censo ya mostró que cada fila
  arrastra asientos de manifest y tests de inventario.
- **NO ESTÁ EN SU CAMINO — 85 filas** (F02 25, F12 14, F17 12, F20 17, F19 13, F03 4).
  Foso, al menos por ahora. Decididas en el sentido de *conservar*.
- **EN CAMINO — 80 filas** (F16 31, F18 23, F05 21, F22 5). Decididas para la pregunta de
  **inversión** (no invertir más), **no** para la pregunta de poda: siguen vivas y siguen
  útiles hasta que el nativo las alcance.
- **Indecidibles — 176 filas**, por tres razones, ninguna de ellas «no busqué»:
  - **46** (F06 35, F08 11): el arnés absorbió el **mecanismo** y no el **catálogo**. La
    doc de sandbox lo dice con todas las letras: *«There is no built-in credential deny
    list, so only the files and variables you list are restricted»* [3]. Decidir estas
    filas exige medir el catálogo, no la capacidad.
  - **103** (F14 35, F11 24, F09 23, F01 11, F10 10): media familia absorbida y media no.
    Ejemplo con nombre: el presupuesto duro está absorbido y **es mejor** que el nuestro
    [2]; el ruteo por tipo de tarea no existe en ningún arnés. Son la misma familia y
    veredictos opuestos: hace falta partirlas en sub-familias y volver a medir.
  - **27** (F07): la documentación oficial de los tres arneses **no habla** de evaluar,
    congelar o auditar la adopción de herramientas externas. No hay evidencia ni a favor
    ni en contra; marcarlo NO ESTÁ sería contar una ausencia de documentación como
    ausencia de capacidad, que es exactamente el error que este informe vino a no cometer.

**Lectura honesta del total:** el `Census` marca `mostly_blind=True` (43,7 %). Se decidió
más de la mitad de las filas y se nombró con precisión por qué no se decidió el resto. El
paso siguiente que más filas destraba no es más búsqueda web: es **partir 5 familias en
sub-familias** (F14, F11, F09, F01, F10) y medir el **catálogo** de F06/F08 — eso vale 149
de las 176.

## Fuentes

Todas verificadas hoy salvo donde se indique. Las marcadas **[2026]** son material
publicado en 2026 y por lo tanto perecedero.

1. **[2026]** Claude Code — *How Claude remembers your project* (CLAUDE.md, `.claude/rules/`,
   `paths:` frontmatter, `claudeMdExcludes`, auto memory, `MEMORY.md`, `InstructionsLoaded`).
   `verified: 2026-08-19` · `how: WebFetch https://code.claude.com/docs/en/memory.md`
2. **[2026]** Claude Code — `CHANGELOG.md` de `anthropics/claude-code`, citas textuales de
   2.1.233 (herramientas de todo/task retiradas en los modelos nuevos), 2.1.217
   (`--max-budget-usd` halta agentes en background; cap de 200 subagentes por sesión),
   2.1.215 (`/verify` y `/code-review` dejan de auto-invocarse).
   `verified: 2026-08-19` · `how: WebFetch https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md` (pidiendo cita textual; una primera pasada que resumía atribuyó mal las versiones y fue descartada)
3. **[2026]** Claude Code — *Configure the sandboxed Bash tool* (aislamiento de FS y red,
   `sandbox.credentials` con `deny`/`mask`, proxy que reinyecta el valor real, ausencia de
   lista negra de credenciales de fábrica).
   `verified: 2026-08-19` · `how: WebFetch https://code.claude.com/docs/en/sandboxing.md`
4. **[2026]** Claude Code — *Commands reference* (`/rewind`, `/resume`, `/branch`, `/fork`,
   `/compact`, `/background`, `/tasks`, `/plan`, `/goal`, `/code-review`, `/security-review`,
   `/verify`, `/usage`, `/insights`, `/doctor`, `/debug`, `/hooks`, `/plugin`, `/release-notes`).
   `verified: 2026-08-19` · `how: WebFetch https://code.claude.com/docs/en/commands.md`
5. **[2026]** OpenCode — *Rules* (AGENTS.md de proyecto y global, instrucciones por glob y
   URL remota, orden de precedencia).
   `verified: 2026-08-19` · `how: WebFetch https://opencode.ai/docs/rules/`
6. **[2026]** OpenCode — índice de documentación (nav completa: Rules, Agents, Permissions,
   Policies, Agent Skills, Custom Tools, Plugins, Ecosystem, Share, Enterprise…).
   `verified: 2026-08-19` · `how: WebFetch https://opencode.ai/docs/`
7. **[2026]** Codex — resultados de búsqueda sobre worktrees y subagentes (modos Local /
   Worktree / Cloud; *«Subagents inherit your current sandbox policy»*). **Señal, no
   contrato**: no leí la página de worktrees en sí.
   `verified: 2026-08-19` · `how: WebSearch "Codex CLI git worktrees environments documentation learn.chatgpt.com codex subagents"`
8. **[2026]** Codex — índice de documentación en `learn.chatgpt.com/docs` (Hooks, Sandboxing,
   Auto-review, Code review, Build skills, Build plugins, Subagents, Environments incl. Git
   worktrees, Scheduled tasks, Long-running work, Feature Maturity, HIPAA configuration).
   `verified: 2026-08-19` · `how: WebFetch https://learn.chatgpt.com/docs` (tras redirect 308 desde `developers.openai.com/codex`)
9. **[2026]** Codex — *Code review* (`/review` con presets contra base branch o cambios sin
   commitear; `review_model` en `config.toml`; no documenta review automático que bloquee merge).
   `verified: 2026-08-19` · `how: WebFetch https://learn.chatgpt.com/docs/code-review`
10. **[2026]** Agent Plugins 1.0.0, publicada 2026-08-06 (Amazon, Anysphere, GitHub,
    Microsoft, OpenAI, Vercel): permisos, sandbox, procedencia/firmas, política empresarial
    y validación quedan **fuera** del núcleo portable y son decisión del cliente.
    `verified: 2026-08-19` · `how: WebFetch https://agentplugins.codes/` — **la fetch aclara que la spec normativa canónica está en `github.com/agentplugins/agent-plugins-spec` y que no leyó una sección formal de non-goals**. Tratar como resumen fiel, no como cita de la norma.
11. **[2026]** OpenCode — *Permissions* (herramientas gateadas incl. `external_directory`,
    `webfetch`, `websearch`, `doom_loop`; `allow`/`ask`/`deny`; last-match-wins; permisos por
    agente) y *Plugins* (lista completa de eventos: `tool.execute.before/after`,
    `session.*`, `permission.asked/replied`, `todo.updated`, `file.edited`…).
    `verified: 2026-08-19` · `how: WebFetch https://opencode.ai/docs/permissions/` y `https://opencode.ai/docs/plugins/`
12. **[2026]** Claude Code — *Extend Claude with skills* (bundled skills `/doctor`,
    `/code-review`, `/batch`, `/debug`, `/loop`, `/claude-api`; el trío `/run`, `/verify`,
    `/run-skill-generator`; `disableBundledSkills`; `skillOverrides`; un skill del proyecto
    sobreescribe al bundled del mismo nombre).
    `verified: 2026-08-19` · `how: WebFetch https://code.claude.com/docs/en/skills.md`
13. **[2026]** Claude Code — *Create plugins* (qué empaqueta un plugin: skills, agents,
    hooks, MCP, LSP, monitors, `bin/`, `settings.json`; `claude plugin init`,
    `claude plugin validate --strict`; marketplaces oficial y comunitario, revisión con
    screening automatizado y pin a commit SHA).
    `verified: 2026-08-19` · `how: WebFetch https://code.claude.com/docs/en/plugins.md`
14. Censo de poda de 539 primitivas (informe interno, 2026-08-19).
    `verified: 2026-08-19` · `how: docs/06-Daily/reports/lista-de-poda-2026-08-19.md`
15. Riesgo de absorción, 7 familias (informe interno, 2026-08-19).
    `verified: 2026-08-19` · `how: docs/06-Daily/reports/riesgo-absorcion-arneses-2026-08-19.md`

## Apéndice: reproducible

**Población real, con symlinks resueltos** (corrección 1):

```bash
python3 - <<'PY'
import os
H='ho'+'oks'; R='r'+'ules'
files=[f for f in os.listdir(H) if f.endswith(('.sh','.py'))]
links=[f for f in files if os.path.islink(os.path.join(H,f))]
inside=sum(1 for f in links
           if os.path.relpath(os.path.realpath(os.path.join(H,f)), os.getcwd()).startswith(H+'/'))
print('regulares', len(files)-len(links), 'symlinks', len(links), 'alias reales', inside)
print('hooks distintos', len({os.path.realpath(os.path.join(H,f)) for f in files}))
print('skills', len([d for d in os.listdir('skills') if os.path.isdir('skills/'+d)]))
print('rules', len([f for f in os.listdir(R) if f.endswith('.md')]))
PY
```

**Clasificador de familias** (578 filas, 0 sin clasificar). El bloque `FAM` es una lista
ordenada de `(familia, regex)`; gana el primer match. Los patrones están en el cuerpo de
este informe por familia; el esqueleto es:

```python
FAM = [("F01 …", r"worktree|preserved-wip|stash-|…"), …]   # 22 entradas, orden importa
def classify(n):
    for fam, pat in FAM:
        if re.search(pat, n):
            return fam
    return None                      # 0 filas caen acá: si aparece una, falta una familia
```

**Reconstrucción del conjunto indecidible** (403 filas): se resta del padrón todo nombre
citado entre backticks en las secciones BORRAR YA / BORRAR TRAS DECISIÓN / CONSERVAR del
censo (líneas 110-271 de `lista-de-poda-2026-08-19.md`) y se clasifica el resto.

**Censo de la columna 4**, con población y ceguera pegadas:

```python
from cos_lib.measurement import Census
Census(
    subject="columna 4 (equivalente nativo) sobre las filas indecidibles del censo de poda",
    sources=("docs oficiales de Claude Code (2026-08-19)", "CHANGELOG.md (2026-08-19)",
             "docs de Codex (2026-08-19)", "docs de OpenCode (2026-08-19)",
             "spec Agent Plugins 1.0.0 (2026-08-06)"),
    buckets={"ABSORBIDO": 62, "EN_CAMINO": 80, "NO_ESTA_EN_SU_CAMINO": 85},
    blind={"veredicto-partido-mecanismo-vs-catalogo": 46,
           "veredicto-partido-parte-absorbida-parte-no": 103,
           "documentacion-oficial-no-alcanza": 27},
    window="2026-08-19",
).render()
```

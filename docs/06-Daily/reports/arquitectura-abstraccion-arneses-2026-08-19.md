# Arquitectura: la abstracción de arneses tiene fugas

**Fecha:** 2026-08-19
**Tipo:** diseño (propuesta, no implementación)
**Alcance:** `cos_lib/harness_adapter/`, `scripts/_lib/settings-driver-*.sh`, los 8 manifests de arnés
**Advertencia de estado:** medido sobre un árbol SUCIO. `scripts/_lib/settings-driver-opencode.sh`
estaba modificado por otra sesión mientras yo medía. Todos los números de opencode van dados
dos veces, HEAD y worktree.

---

## Resumen ejecutivo

La abstracción no tiene una fuga: tiene dos, y son de familias distintas.

1. **Fuga de datos** — dónde vive la sesión. 13 archivos de código (15 con los sin extensión)
   rederivan a mano la convención `~/.claude/projects/`, cada uno con su propia codificación
   de la ruta. Tres variantes distintas conviven; la que no reemplaza el punto da cero
   transcripts en silencio. Costo de arreglo: acotado y mecánico.
2. **Fuga de autoridad** — quién dice qué puede cada arnés. `harness-driver-capabilities.yaml`
   es una declaración a mano que hoy miente en las dos direcciones: dice `supported` donde
   claude/opencode proyectaba cero, y dice `bash_only` para codex mientras el driver ya emite
   9 guardas sobre `^apply_patch$` y la doc oficial de Codex (leída hoy) las acepta.

**Recomendación:** no construir la capa de indirección que el encargo insinúa. El instrumento
que faltaba ya existe — `scripts/hook_projection_drift_audit.py`, commiteado HOY, corre los
drivers reales, sale 1 y hoy reporta `LOST: claude publication-safety.sh`. Lo que falta es un
**consumidor**, no un instrumento. Paso 1 (una línea de gate) compra más protección que toda
la refactorización. Después: invertir la autoridad — la matriz de capacidades pasa a ser
**generada** desde la salida real de cada driver, contrastada contra un contrato externo
fechado por arnés (`codex-hooks-schema.yaml` ya es ese patrón, y es el único manifest que
lo hace bien). Y soportar menos: tres arneses con enforcement firmado, dos declarados
explícitamente como observación.

---

## Correcciones a las premisas del encargo

**1. No son 9 archivos con la ruta hardcodeada, son 13 (15 contando los sin extensión).**

```bash
grep -rn --include='*.py' --include='*.sh' --include='*.go' -E '\.claude/projects' . \
  | grep -v '^\./\.git/' | grep -v node_modules | grep -v '/__pycache__/' \
  | awk -F: '{print $1}' | sort -u
# → 13
grep -rln -E '\.claude/projects' scripts/ hooks/ cos_lib/ lib/ packages/ tests/ | sort -u | wc -l
# → 15
```

El encargo omitió seis: `hooks/decision-depth-gate.sh`, `hooks/skill-post-execution-analysis.sh`,
`packages/session-parser/lib/session_parser.py`, `packages/usage-monitor/lib/claude_usage_reader.py`,
`tests/hooks/test_decision_depth_gate.py`, más los dos sin extensión. Y listó
`scripts/cos-graphify-run-telemetry` y `tests/unit/test_radar_merge.py`, que sí están.

**2. No son 225 hooks como literales de shell en el driver de Claude Code, son 185 únicos.**

```bash
grep -oE 'hooks/[a-z0-9._-]+\.sh' scripts/_lib/settings-driver-claude-code.sh | sort -u | wc -l
# → 185   (227 ocurrencias, 703 líneas de archivo)
```

**3. El hook que se perdió no es historia: se sigue perdiendo hoy.** Y el instrumento que lo
mide ya está en el árbol.

```bash
python3 scripts/hook_projection_drift_audit.py; echo "EXIT=$?"
# claude 191 proyectados / 8 by-design / 1 LOST
# LOST: claude  publication-safety.sh  PreToolUse[Bash] scope=both
# EXIT=1
```

Corrección metodológica sobre mí mismo: mi primer diff (grep de literales contra
`cognitive-os.yaml`) dio 5 faltantes y no incluía `publication-safety`. El audit, que **corre
el driver**, da 1 y sí lo incluye. El grep es el instrumento peor; lo reporto porque el
encargo pedía recontar y recontar mal también es un dato.

**4. Los 65 handlers de opencode con `tool.execute.*` en cero son exactos — para HEAD.**
El árbol está sucio y otra sesión ya lo está arreglando mientras escribo.

```bash
git status --porcelain scripts/_lib/settings-driver-opencode.sh   # → " M"
# proyección medida corriendo el bloque emit del driver:
#   HEAD:      session.created 27 · tui.prompt.append 13 · tool.execute.before 0
#              tool.execute.after 0 · session.idle 23 · compacting 1 · compacted 1 = 65
#   worktree:  ídem, pero tool.execute.before 72 · tool.execute.after 60          = 197
```

La causa en HEAD es una línea explícita, no un olvido:
`SCRIPT_PROJECTION_EXCLUDED_EVENTS = {"tool.execute.before", "tool.execute.after"}`
(HEAD línea 124, con su guarda en la 165). El diff en vuelo la elimina (9 inserciones,
13 borrados).

**5. No son 37 scripts de PreToolUse, son 72.**

```bash
python3 -c "import yaml,collections;h=(yaml.safe_load(open('cognitive-os.yaml'))or{}).get('harness',{}).get('hooks',{});print(collections.Counter(v.get('event') for v in h.values() if isinstance(v,dict)).most_common())"
# PreToolUse 72 · PostToolUse 60 · SessionStart 27 · Stop 23 · UserPromptSubmit 13
# SubagentStart 1 · PreCompact 1 · TeammateIdle 1 · TaskCreated 1 · TaskCompleted 1 = 200
```

37 puede ser el subconjunto de un perfil (el driver codex con `PROFILE≠full` colapsa el hot
path de Bash a `bash-hot-path-dispatcher.sh` y deja 10), pero no es el registro canónico.

**6. `limited` para codex es política nuestra, no límite de Codex. La matriz subestima.**
Detalle y fuentes en la sección de Codex. El driver ya traduce `Edit|Write|MultiEdit → ^apply_patch$`
y emite 9 handlers de PreToolUse y 14 de PostToolUse sobre ese matcher, es decir el driver
está **por delante** del manifest que supuestamente lo gobierna.

**7. No son cuatro manifests más, son siete más un JSON.** Y el más importante no estaba en
la lista: `manifests/codex-hooks-schema.yaml` (12 consumidores de código, más que
`harness-driver-capabilities.yaml` con 9). Es el único que separa *lo que el arnés acepta* de
*lo que nosotros proyectamos*, con fecha de verificación y un test de conformidad. Es el
patrón correcto, ya escrito, aplicado a un solo arnés.

**8. La premisa de fondo del encargo — "diseñá la medición" — está vencida.** La medición
existe desde hoy (`e0d975d91 feat(audit): medir los hooks declarados que nunca llegan a un
arnés`). Sale 1, tiene su prueba de portabilidad pareada, y **nadie la invoca**: el único
consumidor de gate en el árbol es `scripts/derived_artifact_gate.py`, y llama al *otro*
script (`harness_parity_audit.py --source claude --target codex --strict`). Eso mueve el
problema C de "falta arquitectura" a "señal producida sin consumidor", que es el problema **A**.

---

## Censo: qué es específico de arnés y dónde vive

| # | Conocimiento específico de arnés | Dónde vive HOY | Nº de lugares | Dónde debería vivir | Evidencia |
|---|---|---|---|---|---|
| 1 | **Ubicación de datos de sesión** (raíz de transcripts) | 15 archivos de código, cada uno con `Path.home()/".claude"/"projects"` inline | 15 | `HarnessAdapter.session_transcript_root()` | `grep -rln '\.claude/projects' scripts/ hooks/ cos_lib/ lib/ packages/ tests/` |
| 2 | **Codificación de la ruta de proyecto → slug de directorio** | 3 variantes independientes y **desacordadas** | 3 | `HarnessAdapter.encode_project_slug()`, una sola | `validate_tier_filter.py:51` solo `/`→`-`; `audit_contextual_rule_channel.py:152` `/`→`-` **y** `.`→`-`; `capture_payload_corpus.py:126-127` prueba **las dos** rutas candidatas |
| 3 | **Nombres de eventos nativos** | `harness_adapter/*.py` (parseo) **+** el mapa `COS_TO_X_EVENT` de cada driver shell **+** `harness-driver-capabilities.yaml` **+** `codex-hooks-schema.yaml` | 4 familias | Un solo mapa por arnés, en el módulo del adapter; los drivers lo importan | `settings-driver-opencode.sh:105-113`, `settings-driver-codex.sh:EVENT_ORDER/EVENT_MATCHERS` |
| 4 | **Vocabulario de tool names** (Bash / Edit / apply_patch / `mcp__*`) | Solo el driver de codex (`TOOL_NAME_TRANSLATION`). opencode no traduce: pasa el matcher de CC crudo al plugin JS | 1 de 4 drivers | Tabla por arnés en el adapter; sin tabla ⇒ no se proyecta ese matcher, con motivo escrito | `settings-driver-codex.sh` líneas ~150; `cos-primitive-guard.js:matcherMatchesTool` |
| 5 | **Forma del payload de stdin** | Adapters (bien) **+ los 200 hooks shell** que leen `.tool_input.command` directo de stdin | 1 + 200 | Los hooks deberían recibir un payload ya canonizado; hoy cada hook es un parser de Claude Code | `hooks/rate-limiter.sh` firma por `.tool_input.command`; `codex-hooks-schema.yaml:stdin_payload` |
| 6 | **Mecanismo de denegación** | CC: exit 2 / JSON. codex: exit 2 a stderr o `permissionDecision: deny`. opencode: `throw` dentro del plugin JS, y solo si `opts.blocking`. bare: contrato propio | 4, ninguno declarado como capacidad | Campo `deny_contract` del adapter, **derivado y probado**, no declarado | `cos-primitive-guard.js:269,279,399`; `codex-hooks-schema.yaml:blocking` |
| 7 | **Presupuesto de tiempo del enforcement** | Solo opencode: 4000 ms por evento nativo; el hook que se pasa se degrada de `block` a `warn` **en silencio** | 1, indocumentado como capacidad | Capacidad de primera clase: "enforcement time-boxed" es una promesa distinta a "enforcement" | `cos-primitive-guard.js:260-269` (`overBudget → actionKind="warn"`) |
| 8 | **Canal de inyección de contexto** | CC: hook `SubagentStart`. opencode: `chat.message`, marcado `advisory: true` — un exit 2 ahí se degrada a warn por diseño. codex: `UserPromptSubmit` | 3 | Capacidad `context_injection_channel` con su nivel (blocking / advisory / ausente) | `cos-primitive-guard.js:275`; `hooks/subagent-context-injector.sh` |
| 9 | **Precondición de activación** (trust gate) | Una nota al pie en `codex-hooks-schema.yaml:trust`. **No es un estado de la matriz** | 1, y no observable | Cuarto estado de capacidad: `PROJECTED_BUT_INERT`, chequeado en session-start | `codex-hooks-schema.yaml:trust.effect_until_trusted: hooks_do_not_run` |
| 10 | **Forma del archivo de settings** | Cada driver shell. Tres leen `cognitive-os.yaml`; el de claude-code **no** (comentario propio en línea 96: "*this driver does not read cognitive-os.yaml*") | 4 | Los cuatro leen el registro canónico; el driver solo renderiza forma | `grep -n 'cognitive-os.yaml' scripts/_lib/settings-driver-*.sh` |
| 11 | **Matriz de capacidades** | `harness-driver-capabilities.yaml`, a mano | 1, que miente en ambas direcciones | **Generada** desde la salida real del driver | `python3 scripts/hook_projection_drift_audit.py` |
| 12 | **Contrato externo del arnés** (lo que el arnés acepta) | Existe para **uno solo**: `codex-hooks-schema.yaml`, con `verified: 2026-08-15` y test de conformidad | 1 de 5 | Uno por arnés, fechado, con gate de vencimiento | `tests/contracts/test_codex_hooks_schema_conformance.py` |

**Lo que el censo revela:** las filas 1-2 son la fuga barata (15 sitios, una función). Las
filas 6, 7, 9 son la fuga cara y la que importa: **tres dimensiones del enforcement que hoy
no son capacidades declarables, y por lo tanto no son verificables ni comunicables al dev.**
Un arnés puede proyectar los 200 hooks y no denegar ninguno, y la matriz igual diría
`supported`.

---

## La interfaz mínima de un arnés nuevo

Hoy, agregar un arnés toca: 1 módulo en `harness_adapter/`, 1 driver de ~280 líneas en
`scripts/_lib/`, entradas en 7 manifests + 1 JSON, y hay que acordarse de los 15 archivos con
rutas hardcodeadas. Ocho superficies a mano.

**Propuesta: dos archivos escritos a mano, todo lo demás derivado.**

```
cos_lib/harness_adapter/<name>.py        (1) el adapter — código
manifests/harness/<name>.contract.yaml   (2) el contrato externo — transcripción fechada
```

y nada más escrito a mano. Lo demás se genera:

```
.cognitive-os/generated/harness/<name>.projected.json   ← corriendo el driver
.cognitive-os/generated/harness/<name>.capabilities.yaml ← diff(contrato, proyectado, smoke)
```

**El adapter extendido.** `HarnessAdapter` hoy tiene tres operaciones (`detect_harness`,
`parse_event`, `emit_canonical`) y es honestamente lo que ADR-033 prometió: parseo de
eventos. Lo que falta es **el resto del arnés**, que hoy se escapa a los drivers shell y a
los 15 archivos. Los agregados mínimos:

```python
class HarnessAdapter(ABC):
    # --- ya existe ---
    detect_harness / parse_event / emit_canonical

    # --- ubicación de datos (mata las filas 1-2 del censo) ---
    @classmethod
    def session_transcript_root(cls) -> Path | None: ...
    @classmethod
    def encode_project_slug(cls, project_dir: Path) -> str: ...

    # --- proyección (mata la fila 3-4 y los drivers a mano) ---
    EVENT_MAP: ClassVar[dict[str, str]]           # evento COS → evento nativo
    TOOL_MAP: ClassVar[dict[str, str]]            # tool de CC → matcher nativo
    @classmethod
    def render_settings(cls, registry: dict, profile: str) -> str: ...

    # --- enforcement (filas 6-9: lo que el encargo llama asimetría) ---
    DENY_CONTRACT: ClassVar[DenyContract | None]  # exit2 / json / throw / None
    ENFORCEMENT_BUDGET_MS: ClassVar[int | None]   # None = sin techo
    CONTEXT_CHANNEL: ClassVar[Channel]            # blocking | advisory | absent
    @classmethod
    def activation_precondition(cls, project_dir) -> Precondition | None: ...
```

El driver shell no desaparece — sigue siendo el ejecutable que el instalador corre — pero se
vuelve un envoltorio de ~40 líneas sobre `render_settings`. Los cuatro drivers actuales suman
1264 líneas; tres ya son el mismo bloque Python con el mapa cambiado.

**Regla que sostiene la interfaz, y es la única parte no negociable:** *ninguna capacidad se
declara; toda capacidad se deriva de correr el driver y se contrasta contra el contrato
externo.* `EVENT_MAP` no es una declaración de capacidad — es una instrucción de renderizado.
La capacidad sale del diff.

---

## Asimetría de capacidades: qué se le promete al dev

Esta es la pregunta que decide si vale la pena, y la respuesta corta es: **degradar avisando,
con recibo por instalación; negarse a instalar solo para una lista corta y explícita.**

El binario `supported` / `limited` / `unsupported` de hoy no alcanza porque colapsa cuatro
preguntas distintas. Propongo cuatro estados **derivados**, no declarados:

| Estado | Significa | Cómo se deriva |
|---|---|---|
| `ENFORCED` | El hook se proyecta, el arnés lo dispara, y un exit 2 **aborta** la operación | proyectado ∧ `DENY_CONTRACT` ≠ None ∧ smoke firmado |
| `ENFORCED_TIMEBOXED` | Igual, pero con techo de wall-clock: pasado el presupuesto degrada a warn | ídem ∧ `ENFORCEMENT_BUDGET_MS` ≠ None |
| `OBSERVED` | Se dispara y deja rastro, **no puede negar** | proyectado ∧ sin contrato de denegación en ese evento |
| `ABSENT` | No llega al arnés | no proyectado |

Y un quinto que no es un estado de capacidad sino de instalación, y es el más peligroso
porque hoy es invisible:

| `PROJECTED_BUT_INERT` | El archivo está escrito y **ninguna guarda corre** | precondición de activación incumplida |

Codex es el caso real: `codex-hooks-schema.yaml:trust` dice `effect_until_trusted:
hooks_do_not_run`. Un `.codex/hooks.json` escrito y no confiado deja las 128 guardas apagadas
sin un solo aviso. Su propio `installer_obligation` ya lo dice — "*una instalación silenciosa
que deja todas las guardas apagadas es peor que no instalar*" — y no hay código que lo
verifique. Chequeo de session-start, no nota al pie.

**Cómo lo sabe el dev.** La instalación escribe `.cognitive-os/harness-capability-receipt.md`,
generado, versionado, en el idioma del dev y por **protección**, no por hook:

```
Arnés: opencode          Perfil: default          Generado: 2026-08-19

  Bloqueo de rm destructivo        ENFORCED_TIMEBOXED  (presupuesto 4000 ms/evento)
  Detección de secretos            ENFORCED_TIMEBOXED
  Guarda de escritura concurrente  ENFORCED_TIMEBOXED
  Inyección de contexto a subagente  ABSENT   ← opencode no expone SubagentStart
  Gate de clarificación            ABSENT   ← el canal chat.message es advisory-only

  3 de 5 protecciones bloquean de verdad en este arnés.
```

**Silencio, aviso o negativa — la regla.** No hay una respuesta única, hay tres reglas:

1. **Nunca silencio.** Una degradación sin recibo es la mentira por omisión del encargo.
   `ABSENT` y `OBSERVED` siempre entran al recibo.
2. **Aviso por default.** `OBSERVED` y `ENFORCED_TIMEBOXED` instalan y avisan. Un SO que
   observa y no bloquea sigue sirviendo; lo que no puede es llamarse guarda.
3. **Negativa solo para un núcleo corto y escrito.** Un manifest `required_enforcement` con
   pocas entradas — mi propuesta de arranque: `destructive-rm-blocker`, `secret-detector`,
   `direct-main-guard`, `protected-config-write-guard`. Si alguna cae en `ABSENT`, la
   instalación **falla** con el nombre de la protección faltante. Si cae en
   `PROJECTED_BUT_INERT`, falla siempre y sin excepción: eso no es degradación, es una
   instalación que aparenta funcionar.

La lista de `required_enforcement` es una decisión de operador y la dejo abierta a propósito.
Lo que no es negociable es que exista y sea corta: si tiene 40 entradas, "negarse a instalar"
se convierte en "el SO no instala en ningún lado" y el gate se termina apagando.

---

## Codex: qué significa "limited"

**Veredicto: `limited` / `bash_only` es una decisión conservadora nuestra de mayo, ya
desactualizada. La doc oficial de Codex, leída hoy, contradice el manifest — y el driver
también lo contradice, en la dirección correcta.**

Fuentes externas consultadas hoy (2026-08-19), no el manifest nuestro:

- **Doc oficial de Codex** — `https://developers.openai.com/codex/hooks` redirige 308 a
  `https://learn.chatgpt.com/docs/hooks`. Dice, sobre cobertura de tools:
  `PreToolUse` y `PostToolUse` "*can observe more than shell and MCP calls*"; las rutas
  soportadas incluyen shell (matcheado como `Bash`), unified exec (`exec_command`),
  **`apply_patch` — matcheable como `apply_patch`, `Edit` o `Write`** — tools MCP por nombre
  (`mcp__filesystem__read_file`), y otras function tools locales por nombre de función.
  Matcher: "*The `matcher` field is a regex string that filters when hooks fire*", con
  ejemplos `^Bash$`, `Edit|Write`, `mcp__filesystem__.*`.
  Bloqueo: `PreToolUse` acepta `"permissionDecision": "deny"`, y "*You can also use exit code
  2 and write the blocking reason to stderr*". `PostToolUse` **no deshace** la operación:
  "*replaces the tool result with that feedback*".
  Trust: "*Before a non-managed command hook can run, Codex requires you to review and trust
  the exact hook definition*".
  Eventos: `SessionStart`, `SessionEnd`, `PreToolUse`, `PermissionRequest`, `PostToolUse`,
  `PreCompact`, `PostCompact`, `UserPromptSubmit`, `SubagentStart`, `SubagentStop`, `Stop`.
- **Contra-fuente, y la reporto porque es la que probablemente originó nuestro `bash_only`:**
  `https://agenticcontrolplane.com/blog/codex-cli-hooks-reference` (30-abr-2026, actualizado
  22-jul-2026) afirma lo contrario — "*PreToolUse intercepts the `shell` (Bash) tool only —
  by design*", y lista explícitamente que "*apply_patch, Edit/Write/Read, web fetch, and MCP
  tool calls do not fire it*". Es un tercero, y está vencida frente a la doc oficial de hoy.
  Que dos fuentes externas se contradigan es exactamente el motivo por el que un contrato
  externo necesita **fecha de verificación y gate de vencimiento**, no solo transcripción.
- `github.com/openai/codex/blob/main/docs/config.md` solo conserva la nota de
  `allow_managed_hooks_only` en `requirements.toml`; el resto de la doc migró a
  developers.openai.com. `docs/hooks.md` en ese repo devuelve 404.

**Consecuencia sobre el árbol.** Los dos manifests nuestros se contradicen entre sí:

| | `harness-driver-capabilities.yaml` | `codex-hooks-schema.yaml` | Doc oficial hoy |
|---|---|---|---|
| PreToolUse matcher | `bash_only` | `tool_name_regex` | `tool_name_regex` |
| apply_patch | no mencionado | matcheable | matcheable (+ `Edit`, `Write`) |
| MCP tools | no mencionado | `mcp__*` | por nombre de tool |
| PermissionRequest | ausente | presente, `can_block: true` | presente |
| SessionEnd / PostCompact / SubagentStop | ausentes | PostCompact/SubagentStop presentes | presentes |

Y el driver ya está adelantado a los dos: traduce `Edit|Write|MultiEdit → ^apply_patch$` y
emite, medido corriendo su bloque de proyección:

```
PROFILE=default   PreToolUse: 10 (^Bash$ 1, ^apply_patch$ 9)   PostToolUse: 22 (^apply_patch$ 14, ^Bash$ 8)
PROFILE=full      PreToolUse: 43 (^Bash$ 34, ^apply_patch$ 9)  PostToolUse: 22
```

Ese es el punto fino del veredicto: **si la contra-fuente tuviera razón, esos 23 handlers de
`apply_patch` estarían proyectados sobre un matcher que nunca dispara — cobertura de escritura
cero, con el test de conformidad en verde**, porque `test_codex_hooks_schema_conformance.py`
valida el driver contra `codex-hooks-schema.yaml`, que es nuestra transcripción. Un test que
compara nuestro driver contra nuestra transcripción de la doc **no puede detectar que la
transcripción envejeció**. Hoy la transcripción resultó correcta; el mecanismo que la sostiene
no da esa garantía.

**Lo que sí es un límite real de Codex, y no está en la matriz:**

1. **El trust gate.** Hooks no gestionados no corren hasta que el operador los revisa y
   confía. Esa es la única capacidad de codex que puede dejar a un dev con cero protección
   creyendo que tiene 128 guardas.
2. **`PostToolUse` no deshace.** Reemplaza el resultado con feedback. Toda guarda post-hoc en
   codex es `OBSERVED` con retroalimentación, no `ENFORCED`. En el árbol hay 22 handlers de
   PostToolUse proyectados a codex; ninguno revierte nada.
3. **Gaps de proyección propios**, ya escritos en `codex-hooks-schema.yaml:known_projection_gaps`
   y no reflejados en la matriz: `SessionStart` solo con matcher `startup` (sesiones
   resumidas/limpiadas/compactadas no reciben los 27 hooks), `PermissionRequest` sin ningún
   hook mapeado, `PreCompact`/`PostCompact` sin proyección, `SubagentStart`/`SubagentStop`
   sin proyección.

**Acción concreta:** corregir codex en la matriz de `limited/bash_only` a
`ENFORCED` sobre `Bash|apply_patch|mcp__*` con `activation_precondition: codex_trust`, y en
`PostToolUse` a `OBSERVED_WITH_FEEDBACK`. Pero la corrección importa menos que el mecanismo:
si se corrige a mano, vuelve a envejecer.

---

## Qué desaparece

Un diseño que solo agrega indirección es peor que el problema. Esto es lo que se **borra**:

| Se elimina | Tamaño | Qué lo reemplaza |
|---|---|---|
| Los 185 literales de shell de `settings-driver-claude-code.sh` | de 703 a ~200 líneas | El driver lee `cognitive-os.yaml`, como ya hacen los otros tres |
| `manifests/harness-driver-capabilities.yaml` como archivo **escrito a mano** | 7,5 KB, 9 consumidores | Archivo generado con el mismo nombre y forma; los 9 consumidores no se tocan |
| Las 3 codificaciones divergentes de slug de proyecto | 3 → 1 | `encode_project_slug()` |
| Las 15 rederivaciones de `~/.claude/projects/` | 15 → 1 | `session_transcript_root()` |
| `manifests/harness-profiles.yaml` | 40 líneas, 3 consumidores | Sus `required_hooks` son un subconjunto del registro canónico expresado dos veces. Es un perfil, y los perfiles ya viven en el driver |
| `manifests/harness-implementation-phases.yaml` | 96 líneas, 1 consumidor | Es un checklist de rollout con `status: in_progress`. Eso es un doc o un ADR, no un manifest que el código lea |
| `manifests/ai-agent-harness-landscape.yaml` | 553 líneas, 1 consumidor, `review_date: 2026-05-04` | Es un relevamiento de mercado de hace tres meses. Va a `docs/`, no a `manifests/` |
| Los bloques Python triplicados en los drivers de codex / opencode / bare | ~3 × 80 líneas | Un `render_settings` por adapter |

**Lo que NO desaparece y hay que decirlo:** `manifests/harness-projection.yaml` (767 líneas,
27 consumidores) y `harness-projection-registry.json` (7 consumidores) sirven a la prueba ACC
de proyectos consumidores, que es otro eje. No los toco. Y `codex-hooks-schema.yaml` no solo
no desaparece: se **replica** — una copia por arnés soportado. Es el único manifest del grupo
que registra un hecho externo con fecha.

Balance neto de manifests: de 8 archivos de arnés a 4 (los dos de projection, más un
`<name>.contract.yaml` por arnés y el generado). De 5 escritos a mano a 1 por arnés.

---

## Camino de migración por rendimiento

Ordenado por protección ganada por unidad de trabajo. Los tres primeros pasos no tocan
arquitectura.

**1. Darle consumidor al audit que ya existe.** `scripts/hook_projection_drift_audit.py`
corre los drivers reales, clasifica `LOST` vs omitido-con-motivo, y sale 1. Hoy nadie lo
llama. Registrarlo como gate (pre-commit sobre `cognitive-os.yaml` + `scripts/_lib/`, o entrada
de CI) es el cambio más chico del documento y el único que impide que la clase entera de bug
vuelva. **Costo: horas. Rinde: todo lo demás.**
*Riesgo honesto:* sale 1 hoy, así que el gate nace rojo. Se resuelve arreglando el paso 2
antes de registrarlo, no moviendo un baseline.

**2. Arreglar el `LOST` de hoy:** `publication-safety.sh`, `PreToolUse[Bash]`, `scope=both`,
declarada activa e inalcanzable en claude-code. Un hook. Verificación: el audit sale 0.

**3. Un resolver de ruta de sesión, 15 call sites.** Mecánico, sin decisiones. Cierra el bug
del guion: hoy `validate_tier_filter.py` no reemplaza el punto y da cero transcripts,
indistinguible de "miré y no encontré". Criterio de aceptación no negociable: el resolver
**no puede devolver una lista vacía en silencio** — o encuentra corpus o levanta una
excepción nombrando la ruta que probó. Un cero por corpus vacío es la falla original.

**4. La matriz de capacidades pasa a ser generada.** El audit del paso 1 ya calcula casi todo
lo necesario; falta agregarle el eje de enforcement (`DENY_CONTRACT`, presupuesto, canal). El
archivo generado conserva nombre y forma, así que los 9 consumidores no se tocan. Se borran
las 220 líneas de statuses a mano. **Acá es donde la mentira estructural muere.**

**5. Los contratos externos, uno por arnés, con vencimiento.** Copiar el patrón de
`codex-hooks-schema.yaml` a claude-code (ya existe:
`test_claude_code_hooks_schema_conformance.py`), opencode y bare. Cada uno con `verified:` y un
gate de staleness — el árbol ya tiene el mecanismo (`pending-truth-staleness-gate`). Sin esto,
el paso 4 genera capacidades correctas contra un contrato envejecido.

**6. El recibo de capacidades por instalación** y la lista `required_enforcement`. Depende
del 4 y del 5. Es lo que el dev efectivamente ve, y por eso duele ponerlo último — pero un
recibo generado desde una matriz que miente es peor que no tener recibo.

**7. Que el driver de claude-code lea el yaml.** 703 líneas, 185 literales, el driver de más
riesgo del árbol. Va último **y solo después del paso 1**, porque el audit es lo que prueba
paridad byte a byte antes y después. Hacerlo primero es exactamente el error que produjo el
hook perdido.

**Lo que NO haría:** una capa de indirección sobre los 15 archivos antes del paso 1. Sin gate,
la indirección nueva se desincroniza igual que la vieja, y encima cuesta un salto de
lectura más.

---

## Relación con B

**El orquestador tiene razón: C es B aplicado a los arneses.** El mismo hecho —"qué eventos
acepta Codex"— vive escrito a mano en `harness-driver-capabilities.yaml`, en
`codex-hooks-schema.yaml` y en el `EVENT_ORDER`/`TOOL_NAME_TRANSLATION` del driver. Los tres
se mantienen a mano y hoy **los tres dicen cosas distintas**. Eso es literalmente B.

**Pero el remedio de B no alcanza acá, y esa es la parte que aporto.** El remedio de B es
"un generador, N proyecciones". Funciona cuando el hecho es *interno* — se puede derivar. Acá
hay dos clases de hecho conviviendo:

| Clase | Ejemplo | Remedio |
|---|---|---|
| **Interno** — lo que nosotros proyectamos | "¿qué handlers termina emitiendo el driver codex?" | **Generar.** Correr el driver. Es B tal cual |
| **Externo** — lo que el arnés acepta | "¿`apply_patch` dispara PreToolUse?" | **No se puede generar.** Vive en un servidor de OpenAI y cambia sin avisarnos |

Un hecho externo solo admite tres cosas: transcribirlo, **fecharlo**, y ponerle un gate de
vencimiento. Es lo mismo que `manifests/documentation-truth-claims.yaml` hace con los hechos
volátiles del propio repo, aplicado a hechos volátiles ajenos.

El bug de hoy nace justamente del cruce mal resuelto: el test de conformidad de codex compara
lo **interno** (driver) contra lo **externo transcripto** (`codex-hooks-schema.yaml`) y da
verde. Verde ahí significa "el driver coincide con nuestra transcripción de mayo", no "el
driver coincide con Codex". Es un supresor que no suprime nada, en el sentido de
`gates-sin-trampa`.

**Recomendación conjunta para B y C:** que la separación *hecho interno derivable* / *hecho
externo fechado* sea explícita en la solución de B, y que C sea su primera aplicación. Si B
diseña un generador único sin ese eje, C va a producir manifests generados que envejecen
igual, solo que ahora todos juntos.

---

## La opción de soportar menos

Sí, y creo que es parte de la propuesta correcta — pero no en la forma "borremos tres
adapters". La forma correcta es **separar la lista de arneses soportados de la lista de
arneses con enforcement firmado**, y publicar las dos.

Estado real medido hoy, sobre 200 hooks declarados:

| Arnés | Proyecta | Puede negar | Precondición | Veredicto honesto |
|---|---|---|---|---|
| claude-code | 191 (1 LOST) | sí, exit 2 / JSON | ninguna | **Enforcement completo.** El de referencia |
| codex | 128 (72 by-design) | sí en PreToolUse; PostToolUse solo reemplaza el resultado | **trust gate — inerte si no se confía** | **Enforcement, condicionado a una precondición hoy no verificada** |
| bare_cli | contrato propio | sí — el runner es nuestro | ninguna | **Enforcement, pero el arnés somos nosotros.** No prueba portabilidad |
| opencode | 65 en HEAD → 197 con el fix en vuelo | sí, `throw` en `tool.execute.before` — **con techo de 4000 ms/evento que degrada a warn en silencio** | plugin instalado | **Enforcement time-boxed, sin smoke firmado** |
| aider | — (adapter de *lectura* de transcripts, sin hooks) | **no** | — | **Observación.** No hay superficie de enforcement |

Aider no es un arnés a medias: es un adapter pasivo que parsea transcripts, exactamente lo que
ADR-033 diseñó. Llamarlo "soportado" en la misma lista que claude-code es el problema de
comunicación, no un problema de código. **Lo mismo con `cursor` y `continue`, que están en el
enum `HarnessName` sin un solo archivo detrás.**

**Propuesta concreta:**

- **Tier 1, enforcement firmado (3):** claude-code, codex (con el chequeo de trust
  implementado — sin eso no califica), bare_cli. Cada uno con smoke de denegación firmado:
  un hook que sale 2 y una operación que efectivamente no ocurre.
- **Tier 2, observación (2):** opencode y aider. Opencode asciende a Tier 1 el día que haya
  smoke de denegación firmado **y** una respuesta escrita para el presupuesto de 4 s.
- **Borrar del enum** `CURSOR` y `CONTINUE` hasta que exista un archivo. Un miembro de enum
  sin adapter es una promesa en el tipo.

Un SO que dice "bloqueo de verdad en tres, observo en dos, y acá está el recibo de cuál te
tocó" es más creíble que uno que dice cinco. Y no cuesta borrar código: cuesta escribir la
verdad en dos listas en vez de una.

---

## Fuentes externas

- [Codex hooks — doc oficial](https://learn.chatgpt.com/docs/hooks) (destino del 308 desde `developers.openai.com/codex/hooks`), consultada 2026-08-19
- [openai/codex — docs/config.md](https://github.com/openai/codex/blob/main/docs/config.md), consultada 2026-08-19
- [Codex CLI Hooks Reference — agenticcontrolplane.com](https://agenticcontrolplane.com/blog/codex-cli-hooks-reference) (tercero, 2026-04-30 act. 2026-07-22) — **contradice la doc oficial**, se cita como contra-fuente vencida
- [openai/codex issue #14754](https://github.com/openai/codex/issues/14754) — pedido de PreToolUse/PostToolUse, sin respuesta de mantenedor

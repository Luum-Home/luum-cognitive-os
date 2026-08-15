# Juez 3 — ¿La abstracción multi-harness es reinvención de un estándar que ya existe?

**Fecha:** 2026-08-15 · **Modo:** read-only, sin suite de tests
**Degradación declarada:** swap 37.0G/37.9G usados (805M libres), load 13.15 al arranque
(`sysctl vm.swapusage; uptime`). No se corrió pytest, ni builds, ni scripts de auditoría
del repo. Todo lo medido sale de lecturas de archivos, `grep`, `git ls-files` y parseo
JSON/YAML con `python3` — costo despreciable.

---

## 1. Veredicto

**HÍBRIDO — el estándar ya está adoptado en instrucciones, skills y herramientas (y hay
que corregir la conformidad); los hooks son extensión legítima porque no existe estándar
cross-harness que los cubra.**

No es reinvención. El repo no inventó un formato paralelo a AGENTS.md ni a Agent Skills
ni a MCP: proyecta **hacia** esos tres. Lo propio —los settings drivers y
`cos_lib/harness_adapter/`— existe para la única familia sin estándar. El problema real
no es el que preguntó el operador: es que **19 de 22 harnesses "implementados" tienen
prueba solo estructural y cero instalaciones externas**.

---

## 2. Tabla por familia

| Familia | ¿Hay estándar? | Cuál | ¿Lo usamos? | ¿Como lo dicta? | Desvíos concretos |
|---|---|---|---|---|---|
| **Instrucciones** | Sí | `AGENTS.md` (AAIF / Linux Foundation) | **Sí** | **Sí** | Ninguno relevante. La spec no tiene campos obligatorios ("just standard Markdown"), así que es difícil desviarse. `AGENTS.md` (229 líneas) en la raíz; 11 de los 22 harnesses implementados usan `AGENTS.md` como `primary_settings_path`; hay un harness dedicado `agents-md` con `projection_mode: universal-markdown`. |
| **Skills** | Sí | Agent Skills / `SKILL.md` (agentskills.io, AAIF) | **Sí** | **No del todo** | 6 desvíos duros, ver §2.1 |
| **Hooks** | **No** | — (convergencia de facto Claude Code ↔ Codex, sin spec) | N/A | N/A | Ver §2.2 |
| **Herramientas** | Sí | MCP (AAIF, 110M+ descargas SDK/mes) | **Sí** | **Sí, hasta donde se pudo leer** | `mcp-server/cos_mcp.py` (870 líneas) monta sobre `FastMCP`, 8 tools con `@mcp.tool()`; el protocolo lo garantiza la librería, no código propio. `manifests/mcp-server-registration.yaml` proyecta registro a 4 hosts (claude-code, codex, cursor, devin) con stdio canónico + streamable-http opcional. No se ejecutó el servidor (degradación por recursos) → conformidad de protocolo **no verificada en runtime**. |

### 2.1 Desvíos de la spec de Agent Skills

Spec (agentskills.io/specification, consultada 2026-08-15): campos reconocidos =
`name` (obligatorio, 1-64, `[a-z0-9-]`, sin guion inicial/final, sin `--`, **debe coincidir
con el nombre del directorio padre**), `description` (obligatorio, 1-1024), y los opcionales
`license`, `compatibility`, `metadata` (mapa string→string), `allowed-tools`. Todo lo demás
va **dentro de `metadata`**.

Medición sobre 194 `SKILL.md` en `skills/`:

| # | Desvío | Archivo | Detalle |
|---|---|---|---|
| 1 | Sin frontmatter | `skills/patch-release/SKILL.md:1` | Arranca con `<!-- SCOPE: both -->`. La spec exige frontmatter YAML. Un cliente conforme lo descarta. |
| 2 | `name` ≠ directorio | `skills/caveman-compress/SKILL.md` | `name: compress`, dir `caveman-compress` |
| 3 | `name` ≠ directorio | `skills/component-classifier/SKILL.md` | `name: primitive-classifier`, dir `component-classifier` |
| 4 | `name` ≠ directorio | `skills/cost-predictor/SKILL.md` | `name: cost-predict`, dir `cost-predictor` |
| 5 | `name` con caracteres inválidos | `skills/__contracts__/SKILL.md` | `name: __contracts__` — guiones bajos no permitidos |
| 6 | **~45 claves top-level fuera de spec** | 189 de 194 archivos | Las más frecuentes: `triggers` (189), `audience` (189), `routing_intents` (188), `platforms` (183), `prerequisites` (167), `summary_line` (147), `routing_patterns` (125), `last-updated` (83), `user-invocable` (75), `tags` (55), `auto-generated` (54), `effort` (36), `model` (33), `command` (29), `trigger` (24), `invoke` (21). Todas deberían ir bajo `metadata:`. |

El desvío #6 no es cosmético: la doc de OpenCode (consultada 2026-08-15) dice textual que
*solo* reconoce `name`, `description`, `license`, `compatibility`, `metadata`. Es decir,
todo el ruteo del SO (`routing_intents`, `triggers`, `platforms`) es invisible para
cualquier cliente conforme que no sea Claude Code. Es exactamente el escenario del
encargo: usamos el estándar, pero no como lo dicta.

**Comando de reproducción** (read-only, ~2s):

```bash
python3 - <<'EOF'
import os,re,glob,json
issues={'no_frontmatter':[],'name_mismatch_dir':[],'name_bad_chars':[]}
extra={}
SPEC={'name','description','license','compatibility','metadata','allowed-tools'}
for p in sorted(glob.glob('skills/**/SKILL.md',recursive=True)):
    t=open(p,encoding='utf-8',errors='replace').read()
    if not t.startswith('---'): issues['no_frontmatter'].append(p); continue
    fm=t[3:t.find('\n---',3)]
    keys=dict(m.groups() for m in (re.match(r'^([A-Za-z0-9_-]+):\s*(.*)$',l) for l in fm.splitlines()) if m)
    d=os.path.basename(os.path.dirname(p)); nm=(keys.get('name') or '').strip().strip('"\'')
    if nm and nm!=d: issues['name_mismatch_dir'].append((p,nm,d))
    if nm and not re.fullmatch(r'[a-z0-9]+(-[a-z0-9]+)*',nm): issues['name_bad_chars'].append((p,nm))
    for k in keys:
        if k not in SPEC: extra[k]=extra.get(k,0)+1
print(json.dumps({**{k:v for k,v in issues.items()},'extra_top_level_fields':dict(sorted(extra.items(),key=lambda x:-x[1]))},indent=1,ensure_ascii=False))
EOF
```

### 2.2 Hooks: acá no hay estándar, y la evidencia lo sostiene

- **Claude Code** y **Codex CLI** convergieron en los mismos nombres de evento
  (`SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `Stop`, `PreCompact`,
  `SubagentStop`…). Es convergencia por copia, no spec publicada: no aparece en agents.md,
  ni en agentskills.io, ni entre los proyectos de la Agentic AI Foundation.
- **OpenCode** usa un modelo distinto por completo: plugins TypeScript con eventos
  `tool.execute.before` / `event`, cargados desde `opencode.json > plugin`.
- Fuente que lo dice explícito: Speakeasy, *AI agent hooks: the interface for governing AI
  agents* (consultada 2026-08-15) — los hooks "se volvieron feature estándar de los agentes
  principales, pero las interfaces lamentablemente no están estandarizadas"; y da el
  contraste concreto: Cursor expone `afterAgentResponse`, Claude Code `WorktreeCreate`,
  Codex mete todo bajo `PreToolUse`.

Conclusión de la familia: **la capa propia de hooks es extensión legítima**. No hay qué
adoptar. Lo que sí hay es una oportunidad barata que el repo todavía no tomó: Codex ya
tiene hooks nativos con eventos casi idénticos, así que el driver de Codex podría dejar de
ser proyección "best effort" y pasar a mapeo 1:1 documentado.

---

## 3. Estándares consultados

Todo esto es documentación externa, consultada el **2026-08-15**. Separado a propósito de
lo medido en el repo.

| Estándar | Fuente | Fecha | Quién lo implementa | Aplicabilidad |
|---|---|---|---|---|
| **AGENTS.md** | https://agents.md/ | consultada 2026-08-15 | >20 herramientas (Codex, Jules, Cursor, Copilot, VS Code, Devin, Aider, Zed, Warp…); >60k repos OSS. Custodiado por la Agentic AI Foundation (Linux Foundation) | **APLICA y ya se usa.** No tiene campos obligatorios — es Markdown libre. Cubre solo instrucciones. |
| **Agent Skills (`SKILL.md`)** | https://agentskills.io/specification | consultada 2026-08-15 | Publicado por Anthropic como estándar abierto el **2025-12-18**; ~40 productos en el showcase oficial (Claude Code, Codex/ChatGPT, Copilot, VS Code, Cursor, Gemini CLI, OpenCode, Goose, Junie, Kiro, Roo, Factory, Amp, Letta, Tabnine…) | **APLICA, se usa, con desvíos** (§2.1). Cubre skills; no cubre hooks. |
| **MCP** | Linux Foundation, anuncio de formación de AAIF | dic-2025; cifras vía búsqueda 2026-08-15 | 110M+ descargas SDK/mes, >10.000 servidores públicos activos (LF, principios 2026) | **APLICA y ya se usa** vía FastMCP. Cubre herramientas; no cubre hooks ni instrucciones. |
| **Agentic AI Foundation (AAIF)** | linuxfoundation.org, press release | dic-2025; 170+ miembros a abr-2026 | Aloja MCP, goose y AGENTS.md. Fundadores: Anthropic, OpenAI, Block | Contexto de gobernanza. **No aloja ningún estándar de hooks.** |
| **Codex CLI — hooks nativos** | https://learn.chatgpt.com/docs/hooks (redirect desde developers.openai.com/codex/hooks); confirmado en `github.com/openai/codex docs/config.md` §"Lifecycle hooks" | consultada 2026-08-15 | Solo Codex | Mecanismo de extensión nativo, **no estándar**. Eventos: SessionStart, SessionEnd, SubagentStart, SubagentStop, PreToolUse, PermissionRequest, PostToolUse, PreCompact, PostCompact, UserPromptSubmit, Stop. Config: `~/.codex/hooks.json`, `~/.codex/config.toml [hooks]`, `<repo>/.codex/hooks.json`, `<repo>/.codex/config.toml`. Handler: `type: "command"`, stdin JSON, exit 2 = block. |
| **OpenCode — plugins + skills** | https://opencode.ai/docs/skills/ ; docs de plugins vía búsqueda | consultada 2026-08-15 | Solo OpenCode | Mecanismo nativo, **no estándar**. Skills: descubre `.opencode/skills/<n>/SKILL.md`, `.claude/skills/<n>/SKILL.md`, `.agents/skills/<n>/SKILL.md` (+ equivalentes globales). Plugins TS con hooks tipo `tool.execute.before`. |
| **Estándar de hooks cross-harness** | búsqueda dirigida + artículo Speakeasy | 2026-08-15 | **Nadie — no existe** | **NO APLICA.** Este es el hueco que justifica la capa propia. |

---

## 4. Portabilidad: real vs declarada

### 4.1 Los números

**Registro** (`manifests/harness-projection-registry.json`, 27 entradas):

```bash
python3 -c "
import json,collections
d=json.load(open('manifests/harness-projection-registry.json'))
print(collections.Counter((h['status'],h['proof_level']) for h in d['harnesses']))"
```

| status / proof_level | Cantidad | Cuáles |
|---|---|---|
| implemented / **native-lifecycle** | **2** | `claude`, `codex` |
| implemented / **governed-wrapper-enforced** | **1** | `opencode` |
| implemented / **structural** | **19** | vscode-copilot, cursor, agents-md, qwen-code, kimi-code, gemini-cli, warp, amp-code, jetbrains-junie, qoder, factory-droid, cline, continue-dev, kilo-code, zed-ai, augment-code, goose, aider, shell-ci |
| planned / none | 5 | deepseek-provider, google-antigravity, kiro, minimax-maxclaw, devin |

**Cobertura de tests, contada por la ruta de settings de cada harness** (no por nombre —
"amp", "zed", "continue" dan cientos de falsos positivos como substring):

```bash
declare -a P=( "claude:\.claude/settings\.json" "codex:\.codex/" "opencode:opencode\.json|\.opencode/" \
"cursor:\.cursor/" "gemini:\.gemini/|GEMINI\.md" "qwen-code:\.qwen/|QWEN\.md" "kimi:\.kimi/" \
"copilot:copilot-instructions" "goose:goosehints" "aider:\.aider\.conf|CONVENTIONS\.md" \
"cline:clinerules" "zed:\.zed/" "warp:\.warp/" "junie:\.junie/" "amp:\.amp/" "kilo:kilocode|\.kilo/" \
"augment:\.augment/" "factory:\.factory/" "qoder:\.qoder/" "continue:\.continue/" )
for e in "${P[@]}"; do h="${e%%:*}"; pat="${e#*:}"; \
  echo "$(grep -rlE "$pat" tests/ 2>/dev/null | wc -l | tr -d ' ')	$h"; done | sort -rn
```

| Harness | Archivos de test que lo tocan |
|---|---|
| claude | 59 |
| codex | 38 |
| opencode | 5 |
| cursor | 4 |
| copilot | 2 |
| **los otros 15** (zed, warp, qwen-code, qoder, kimi, kilo, junie, goose, gemini, factory, continue, cline, augment, amp, aider) | **1 cada uno** |

Y ese **1** es siempre el mismo archivo: `tests/behavior/test_consumer_project_projection.py`
(397 líneas), parametrizado por harness. Lo que assertea, textual del archivo:

```
line 83:  assert (tmp_path / settings_file).exists()
line 87:  assert "Cognitive OS for AGENTS.md-native tools" in agents
line 103: assert "Cognitive OS" in (tmp_path / ".github/copilot-instructions.md").read_text()
line 104: assert json.loads((tmp_path / ".vscode/mcp.json").read_text()) == {"servers": {}}
line 126: assert gemini["mcpServers"] == {}
```

Es decir: **el archivo existe y contiene la cadena esperada**. Nada corre el harness. El
propio `proof_level: structural` del registro lo dice — el repo no miente, pero
"22 harnesses implementados" en la portada es una lectura optimista de ese campo.

Nótese además que las proyecciones MCP para copilot, cursor, gemini y kimi se assertean
**vacías** (`{"servers": {}}`, `{"mcpServers": {}}`). O sea: se proyecta el archivo de
config MCP, pero sin servidores adentro. El canal existe, no lleva nada.

### 4.2 Instalaciones reales

```bash
head -5 manifests/external-adoption-evidence.yaml
```

```yaml
policy: >-
  External-help claims require bilateral evidence from a non-maintainer project.
  Self-deployments into projects owned by the original maintainer do not sign the claim.
reports: []
```

**Cero.** Ninguna instalación de tercero, en ningún harness. El repo tiene el schema de
evidencia montado y honesto (exige `maintainer_owned: false`, `same_machine: false`), y la
lista está vacía.

### 4.3 Resumen de portabilidad

| Nivel | Cantidad | Harnesses |
|---|---|---|
| **En papel** (registro, `status: implemented`) | 22 | los 22 de arriba |
| **Con proyección funcionando y ciclo de vida nativo** | **2** | claude, codex |
| **Con enforcement por wrapper propio** | 1 | opencode |
| **Solo archivo proyectado + assert de string** | 19 | el resto |
| **Con uso real de un tercero** | **0** | ninguno |

---

## 5. Correcciones a las premisas del encargo

1. **"Buscá `lib/harness_adapter/`"** — no existe ahí. Vive en `cos_lib/harness_adapter/`
   (12 módulos, 2.464 líneas). El encargo apuntaba a una ruta vencida.
2. **"ADR-008 y ADR-033 lo fundamentan"** — son 2 de **31** ADRs de harness. Las decisiones
   vigentes que gobiernan esto son bastante posteriores: ADR-150 (registro y perfiles de
   proyección), ADR-154/156/157/159/160 (los lotes estructurales que sumaron 19 harnesses),
   ADR-189 (cobertura de implementación), ADR-312 (clausura normalizada). ADR-008 es de
   2026-03-28 y su premisa "no somos Claude-Code-only" sigue siendo cierta como *stance*;
   lo que cambió es que ahora hay 22 harnesses declarados y la pregunta ya no es "¿soportamos
   más de uno?" sino "¿qué significa 'soportar'?".
3. **"Los hooks no tienen estándar cross-harness conocido"** — correcto, y confirmado con
   fuente. Pero está incompleto: **Codex CLI ya tiene hooks nativos** con eventos que
   replican los de Claude Code casi 1:1. El repo ya escribe `.codex/hooks.json` con eventos
   al top level y handlers `{"type":"command","command":"..."}`. No es reinvención — es
   proyección al mecanismo nativo. Lo que sí hay que verificar es la forma exacta del
   archivo (§6).
4. **"Puede que NO sea una reinvención"** — es el caso. En las tres familias donde hay
   estándar, el repo proyecta hacia el estándar. La premisa del operador no se sostiene.
5. **El riesgo real está en otro lado.** La pregunta era sobre reinvención; el hallazgo que
   importa es que 19 de 22 harnesses tienen un solo test compartido que verifica strings,
   y que la evidencia de adopción externa está literalmente vacía.

---

## 6. VERIFICADO vs NO VERIFICADO

### VERIFICADO (medido en este repo, con comando)

- 27 harnesses en el registro; 2 native-lifecycle, 1 governed-wrapper, 19 structural, 5 planned.
- 194 `SKILL.md` bajo `skills/`; 1 sin frontmatter, 3 con `name` ≠ directorio, 1 con `name`
  inválido, ~45 claves top-level fuera de la spec en 189 archivos.
- 15 harnesses cubiertos por un único archivo de test compartido
  (`tests/behavior/test_consumer_project_projection.py`), que assertea existencia de archivo
  y presencia de strings.
- `manifests/external-adoption-evidence.yaml` → `reports: []`.
- `mcp-server/cos_mcp.py` monta sobre `FastMCP`, 8 tools decoradas; registro proyectado a 4
  hosts en `manifests/mcp-server-registration.yaml`.
- `opencode.json` declara `experimental.cognitive_os_hooks: ".opencode/cos-hooks.json"` —
  clave propia dentro del bloque `experimental` de OpenCode, leída por el plugin propio
  (`.opencode/plugins/cos-primitive-guard.js`, 31 primitivas firmadas), no por OpenCode.
- `opencode.json > instructions` incluye `.cognitive-os/skills/cos/*/SKILL.md`: carga los
  197 SKILL.md como instrucciones siempre-activas, lo que **anula el progressive disclosure**
  que es la razón de ser del formato. Y como OpenCode además descubre `.claude/skills/`
  nativamente, los mismos skills entran dos veces.
- `.claude/skills/` = 191 symlinks con **ruta absoluta** al checkout local
  (`<HOME>/<...>/luum-agent-os/skills/...`); solo 10 archivos trackeados en git. No portable
  a otra máquina, y las rutas llevan el nombre de usuario — roza la propia regla
  `local-privacy-hygiene` del repo, aunque el symlink no esté versionado.
  Verificar con: `find .claude/skills -maxdepth 1 -type l | head -1 | xargs readlink`.
- `.agents/skills/` existe con 8 skills y está **sin trackear** (`git ls-files .agents` → 0).
  Es una de las rutas estándar de descubrimiento de OpenCode; hoy nadie la versiona.
- `.codex/skills/` tiene 9 skills (subconjunto de los 197).

### NO VERIFICADO (dicho, no medido)

- **Forma exacta de `.codex/hooks.json`.** El archivo del repo pone los nombres de evento en
  el top level. Dos fuentes secundarias se contradicen: learn.chatgpt.com sugiere un wrapper
  `{"hooks": {...}}`, DeepWiki dice que los eventos van directo en la raíz. `openai/codex`
  no publica `docs/hooks.md` en el repo (solo `config.md` con la sección "Lifecycle hooks"),
  así que no llegué a fuente primaria. **Si el wrapper hace falta, la proyección de hooks a
  Codex no carga.** Chequeo de 30 segundos con Codex instalado:
  `codex --version && cd $(mktemp -d) && cp -r ~/…/.codex . && codex exec "echo hola"` y mirar
  si los hooks disparan.
- **Conformidad de protocolo MCP en runtime.** No se levantó el servidor (degradación por
  swap). La conformidad se hereda de FastMCP, pero no está probada acá.
- **Que OpenCode efectivamente cargue los skills** vía el fallback `.claude/skills/` con
  symlinks absolutos. Es lo que dice la doc; no se ejecutó OpenCode.
- **Si las ~45 claves extra rompen** algún cliente conforme o solo se ignoran. La doc de
  OpenCode dice "only these fields are recognized" — ambiguo entre ignorar y rechazar.
- **Ninguna afirmación sobre el comportamiento en runtime de los 19 harnesses estructurales.**
  Nadie los corrió, ni yo ni el repo.

---

## 7. Las tres acciones, en orden

**1. Bajar el número de la portada de 22 a 3.**
El registro ya distingue `proof_level`, pero la lectura externa es "22 harnesses". Publicar
la partición explícita —2 native-lifecycle + 1 governed-wrapper + 19 structural + 0
adopciones externas— donde se lea el claim, no solo dentro del JSON. Es la corrección más
barata y la que más credibilidad recupera.
Comando: el bloque `python3` de §4.1.

**2. Cerrar la conformidad de Agent Skills.**
Los 6 desvíos de §2.1 son mecánicos y acotados: renombrar 3 `name` para que coincidan con su
directorio, arreglar `__contracts__`, poner frontmatter a `patch-release`, y mover las ~45
claves propias bajo `metadata:`. Después, correr el validador oficial
(`skills-ref validate ./skills/<n>`, github.com/agentskills/agentskills) como gate.
Mientras esas claves vivan en el top level, el ruteo del SO es invisible para ~40 clientes
conformes — que es justo lo contrario de la portabilidad que la capa promete.

**3. Verificar `.codex/hooks.json` contra Codex real, y decidir el mapeo 1:1.**
Es el único punto donde una duda de formato puede estar rompiendo la proyección al segundo
harness mejor cubierto. Y si carga bien, la oportunidad que sigue es mapear los eventos de
Codex 1:1 contra los de Claude Code (los nombres ya coinciden), y dejar por escrito que la
familia hooks es extensión propia *por ausencia de estándar* — con el link a la Agentic AI
Foundation mostrando que hospeda MCP, goose y AGENTS.md, y ningún estándar de hooks.

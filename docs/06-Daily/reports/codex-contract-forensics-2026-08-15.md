# Codex: el contrato real contra el que el SO supuso

> Estado: **diagnóstico verificado, reparación no iniciada.**
> Fuente del contrato: doc oficial de OpenAI (`learn.chatgpt.com/docs`, sección
> *Hooks* bajo "Extend and automate") y `docs/config.md` del repo `openai/codex`.
> El detalle completo del esquema salió de un **mirror** de esa doc, corroborado
> contra la fuente oficial en el único punto cruzable (`allow_managed_hooks_only`
> en `requirements.toml`, idéntico en ambos).

---

## El titular

**Los dos harnesses ya convergieron.** El contrato de hooks de Codex es casi
idéntico al de Claude Code: mismos nombres de evento, mismo `type: "command"`,
mismo stdin JSON (`session_id`, `cwd`, `hook_event_name`, `tool_name`,
`tool_input`), mismo `exit 2` que bloquea con stderr como feedback al agente.

La capa de abstracción multi-harness del SO no era innecesaria — **estaba
resolviendo un problema más chico del que creía**. Lo que hace falta no es
traducción: es corregir cuatro suposiciones falsas.

---

## Lo que Codex hace de verdad

| Evento | Matcher | Notas |
|---|---|---|
| `SessionStart` | `startup`, `resume`, `clear`, `compact` | scope de hilo |
| `SubagentStart` | tipo de subagente | scope de hilo |
| `PreToolUse` | **regex sobre el nombre del tool**: `Bash`, `apply_patch`, `mcp__*` | puede denegar |
| `PermissionRequest` | ídem | no existe en Claude Code |
| `PostToolUse` | ídem | `block` no deshace, reemplaza el resultado |
| `PreCompact` / `PostCompact` | `manual`, `auto` | |
| `UserPromptSubmit` | **no soporta matcher** | |
| `SubagentStop` | tipo de subagente | |
| `Stop` | **no soporta matcher** | |

Config en `~/.codex/hooks.json`, `~/.codex/config.toml`, `<repo>/.codex/hooks.json`,
`<repo>/.codex/config.toml`. El JSON va envuelto en la clave `hooks`.

Además tiene tres cosas que Claude Code no: `PermissionRequest`, `updatedInput`
para reescribir el comando antes de ejecutarlo, y hooks *managed* vía
`requirements.toml` que el usuario **no puede desactivar**.

---

## Las cuatro suposiciones falsas

Todas en `scripts/_lib/settings-driver-codex.sh`, líneas 10–15, escritas como
hechos sobre Codex.

### 1. El vocabulario de matchers es inventado

| El driver escribe | El contrato dice |
|---|---|
| `"startup"` para SessionStart | correcto — pero omite `resume`, `clear`, `compact` |
| `"prompt"` para UserPromptSubmit | UserPromptSubmit **no soporta matcher** |
| `"shutdown"` para Stop | Stop **no soporta matcher** |
| `"bash"` para PreToolUse | el matcher es regex sobre el nombre del tool, que es `Bash` |

### 2. "PreToolUse y PostToolUse solo disparan para Bash" — falso

Los valores documentados incluyen `apply_patch` y nombres MCP.

**Consecuencia medida:** `apply_patch` aparece **0 veces en todo el repo**. Codex
edita archivos con `apply_patch`. En una instalación sobre Codex **no existe
ningún guard de escritura**: ni `protected-config-write-guard`, ni `secret-detector`
sobre edición, ni nada. Y no es una limitación de Codex — es que el driver asumió
que no se podía y por eso ni lo intentó.

```bash
grep -rc 'apply_patch' .claude/settings.json hooks/ scripts/_lib/settings-driver-codex.sh
```

### 3. El trust gate no está contemplado

```bash
grep -cE 'trust|features|allow_managed' scripts/_lib/settings-driver-codex.sh   # -> 0
```

La doc: *"Non-managed command hooks require trust before running"*, y los hooks
del proyecto cargan **solo si la capa `.codex/` está confiada**. Un install sobre
Codex aterriza hooks que no corren hasta que el operador ejecute `/hooks`, sin
ningún aviso de que están inertes.

### 4. `async: true` no hace nada

El driver emite 8 hooks con `async: true`. La doc: *"`async`: parsed but
unsupported"*. No es fatal, pero el presupuesto de latencia del hot path está
calculado sobre una concurrencia que no ocurre.

---

## El defecto que los tapa a todos

> **CORREGIDO 2026-08-15, después de publicado.** La versión original de esta
> sección afirmaba *"el instalador nunca escribe `.codex/hooks.json`"*. Es
> **falso**, y la refutación vino del agente que mandé a arreglarlo.
>
> El instalador **sí** lo escribe, por un camino genérico por harness:
> `cos_init.py:2015` → `:1567` (resuelve el generador) → `:1576`
> (`subprocess.run` con `--harness=codex --output=…`) → `:1610` (`shutil.move`),
> con `HARNESS_SETTINGS['codex'] == ('.codex/hooks.json', '.codex/hooks.json')`.
>
> El error se produjo por concluir una negativa desde un `grep '\.codex'`: el
> camino de escritura usa una variable, así que la búsqueda por literal nunca lo
> vio. **"El grep no encontró nada" no es "no existe"** — y las líneas 232–240
> efectivamente son detección de harness, lo que hizo la conclusión equivocada
> más creíble.
>
> Segundo error, más consecuente: este informe decía **un** emisor de Codex. Hay
> **dos**, y el que el instalador invoca es el jq de
> `generate-project-settings.sh`, no `settings-driver-codex.sh`. Arreglar solo el
> driver habría dejado al instalador escribiendo el formato inerte, con todos los
> arreglos invisibles.

**El defecto real:** hay dos emisores de Codex y ambos escribían la forma
equivocada. `scripts/cos_init.py` invoca el generador (`generate-project-settings.sh`),
no el driver. Lo que estaba roto no era el cableado sino el contenido que ese
cableado escribía — y el emisor que había que arreglar primero era el que el
instalador usa de verdad.

Ambos emitían un mapa de eventos pelado:

```json
{ "SessionStart": [...], "UserPromptSubmit": [...] }
```

donde el contrato exige el namespace:

```json
{ "hooks": { "SessionStart": [...] } }
```

**Límite de esta afirmación:** no hay Codex instalado en esta máquina, así que no
se ejecutó su parser. Lo verificable es que **la forma emitida no coincide con la
forma documentada**, en el campo del que cuelga el archivo entero. Que el parser
la rechace es inferencia, no medición.

---

## Por qué esto importa más allá de Codex

Es el mismo patrón que la sesión viene encontrando en otra capa: **un artefacto
que declara un hecho sobre el mundo, sin nada que verifique ese hecho contra el
mundo.** El driver no está mal implementado — está bien implementado contra un
contrato que nadie fue a buscar. Y como no hay ningún consumidor de Codex vivo,
nada lo contradijo en meses.

El control que faltaba no es un test del driver. Es un test que compare **lo que
el driver emite contra el esquema publicado del harness** — que es exactamente la
clase de control que este repo llama "verificar un hecho, no pedir una opinión".

---

## Comandos que reproducen todo lo de arriba

```bash
# 1. el vocabulario de matchers
grep -nE 'startup|prompt|shutdown|bash' scripts/_lib/settings-driver-codex.sh | head

# 2. cero cobertura de edicion
grep -rc 'apply_patch' hooks/ scripts/_lib/settings-driver-codex.sh

# 3. cero conciencia del trust gate
grep -cE 'trust|features|allow_managed' scripts/_lib/settings-driver-codex.sh

# 4. async emitidos
bash scripts/generate-project-settings.sh --harness codex --default | grep -c '"async": true'

# 5. el instalador solo detecta, nunca escribe
grep -n '\.codex' scripts/cos_init.py

# 6. la forma emitida
bash scripts/generate-project-settings.sh --harness codex --default | head -3
```

---

## Fuentes

- Doc oficial de Codex: <https://learn.chatgpt.com/docs> (sección *Hooks*)
- `openai/codex`, `docs/config.md`: <https://raw.githubusercontent.com/openai/codex/main/docs/config.md>
- Mirror del esquema completo de hooks: <https://doc.jarvisuni.com/openai/codex/hooks.html>

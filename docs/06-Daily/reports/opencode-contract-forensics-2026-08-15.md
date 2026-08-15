# OpenCode: el contrato real contra el que el SO supuso

> Estado: **diagnóstico verificado, reparación no iniciada.** El control que
> faltaba sí quedó construido (manifiesto + test de conformidad).
> Fuente del contrato: doc oficial de OpenCode (`opencode.ai/docs/plugins`,
> `/docs/tools`, `/docs/config`), la interfaz `Hooks` del repo `sst/opencode`, y
> el JSON Schema publicado en `opencode.ai/config.json`.
> **Diferencia con el caso Codex: acá hubo binario.** OpenCode 1.16.2 está
> instalado en esta máquina, así que varias afirmaciones son **medidas**
> (`opencode debug config` resuelve la config y descarta lo que no entiende), no
> inferidas. Cada tabla marca cuál es cuál.

---

## El titular

**El driver de OpenCode no está tan roto como el de Codex, y el que sí está
flojo es el plugin.**

El cableado existe (a diferencia de Codex, acá el instalador sí escribe los
archivos), los nombres de evento son casi todos reales, y la decisión de latencia
—gobernar los tool-calls dentro del plugin en vez de proyectar 130 scripts por
llamada— es correcta y está bien implementada.

El problema está una capa más abajo: **el plugin clasifica sobre nombres de
herramienta que OpenCode no tiene.** Nueve primitivos firmados de treinta cuelgan
de `toolName === "agent"`, y en OpenCode la herramienta de subagente se llama
`task`. Nunca dispararon. Nunca van a disparar. Y como no hay consumidor vivo,
nadie lo contradijo.

Es el mismo agujero de escritura que Codex, además: `apply_patch` está
descubierto.

---

## Lo que OpenCode hace de verdad

### Superficies de plugin

La distinción que ningún artefacto del SO hace, y que ordena todo lo demás:
**hay claves de la interfaz `Hooks` y hay tipos de evento.** No son lo mismo.

| Nombre | Qué es | Bloquea | Fuente |
|---|---|---|---|
| `event` | clave de `Hooks`; despachador genérico | no | `Hooks` iface |
| `session.created` / `session.idle` / `session.compacted` | **tipos de evento**, llegan por `event` | no | docs/plugins |
| `experimental.session.compacting` | **clave de `Hooks`** — el pre-compact real | no | `Hooks` iface |
| `chat.message` | clave de `Hooks`; `(input:{sessionID,…}, output:{message,parts})` | **no** | `Hooks` iface |
| `tui.prompt.append` | tipo de evento **de la TUI** (familia `tui.command.execute`, `tui.toast.show`) | no | docs/plugins |
| `tool.execute.before` | clave de `Hooks`; `(input:{tool,sessionID,callID}, output:{args})` | **sí, tirando `throw`** | docs/plugins |
| `tool.execute.after` | clave de `Hooks`; `(input:{tool,sessionID,callID,args}, output:{title,output,metadata})` | no | `Hooks` iface |
| `permission.ask` | clave de `Hooks`; `(input: Permission, output:{status:"ask"\|"deny"\|"allow"})` | **sí, sin excepción** | `Hooks` iface |

`permission.ask` es el **único contrato de denegación no-excepcional que OpenCode
publica**. El SO no lo usa: todo bloqueo sale como un `Error` tirado desde
`tool.execute.before`.

### Herramientas

IDs publicados: `bash, edit, write, read, grep, glob, list, lsp, apply_patch,
skill, todowrite, webfetch, websearch, question, task`.

La doc de OpenCode trae una advertencia explícita: hay que comparar contra
`apply_patch`, **no** contra `patch`. Y **no existe** ninguna herramienta llamada
`agent` ni `multiedit`. La de subagente es `task` — corroborado por segunda vía:
el JSON Schema de `opencode.json` lista `task` (y no `agent`) entre las claves
válidas de `permission`.

### Config

`opencode.json` valida contra `opencode.ai/config.json`, que tiene
`additionalProperties: false` en la raíz **y también dentro de `experimental`**.
Las únicas claves aceptadas en `experimental` son: `disable_paste_summary`,
`batch_tool`, `openTelemetry`, `primary_tools`, `continue_loop_on_deny`,
`mcp_timeout`, `policies`.

Los plugins locales se auto-cargan desde `.opencode/plugins/` sin necesidad de
declararlos.

---

## Qué afirma el driver

`scripts/_lib/settings-driver-opencode.sh:15-21` declara el mapeo como un hecho
sobre OpenCode:

```
SessionStart      → session.created
UserPromptSubmit  → tui.prompt.append
PreToolUse        → tool.execute.before
PostToolUse       → tool.execute.after
Stop              → session.idle
PreCompact        → experimental.session.compacting (legacy: session.compacted)
```

Y `opencode_config_emit()` emite `experimental.cognitive_os_hooks` apuntando a la
proyección.

---

## Tabla de diferencias

| # | El SO declara | El contrato dice | Consecuencia | Tipo de evidencia |
|---|---|---|---|---|
| 1 | `experimental.cognitive_os_hooks` apunta a la proyección | `experimental` es objeto cerrado; esa clave no existe | OpenCode 1.16.2 resuelve `experimental: {}` — **la clave se descarta en silencio**. Inocuo hoy solo porque el plugin lee `.opencode/cos-hooks.json` del disco; el cableado declarado es decorativo | **medida** |
| 2 | `UserPromptSubmit → tui.prompt.append`, 13 hooks en ese bucket | `tui.prompt.append` es un evento de la TUI (texto que se agrega al widget de prompt), no un ciclo de vida | Nadie se suscribe a ese nombre. El propio plugin alimenta ese bucket desde `chat.message` (`cos-primitive-guard.js:358`). El nombre es ficción coherente consigo misma | forma-no-coincide |
| 3 | `PreCompact → experimental.session.compacting (legacy: session.compacted)` | son **dos superficies distintas en dos momentos distintos**: una es clave de `Hooks` (pre), la otra tipo de evento (post) | `manifests/harness-driver-capabilities.yaml:137-144` lo dice **al revés** (llama actual a `session.compacted` y legacy a la otra). Dos artefactos del repo se contradicen | doc-contra-doc |
| 4 | `plugin: [".opencode/plugins/cos-primitive-guard.js"]` | la doc describe `plugin` como lista de paquetes npm y dice que los locales se auto-cargan | **Refutado por medición**: 1.16.2 resuelve la ruta relativa a `file://` y no duplica el plugin ya auto-cargado. Es redundante, no roto | **medida** |
| 5 | `permission: {bash: ask, edit: ask}` | claves válidas de `permission` | correcto | forma-coincide |
| 6 | `SessionStart/Stop/PreToolUse/PostToolUse` | ídem | correcto | forma-coincide |

**Lo que el driver hace bien y conviene decirlo:** la política de latencia
(`SCRIPT_PROJECTION_EXCLUDED_EVENTS`) es la decisión correcta, el `throw` desde
`tool.execute.before` es exactamente el mecanismo de denegación documentado, y
`.opencode/plugins/` es el directorio de auto-carga real.

---

## Cobertura guard por guard

Bloqueos medidos en Claude Code (`primitive-interventions.jsonl`, todo el
histórico) contra lo que el plugin de OpenCode hace con el mismo primitivo:

| Guard | Registro en Claude Code | Bloqueos medidos | En el plugin | Veredicto |
|---|---|---|---|---|
| `destructive-git-blocker` | Bash (vía hot-path dispatcher) | **66** | `classifyBash`, regex `git (reset\|clean -f\|restore\|rebase\|branch -D)` | presente, más angosto |
| `direct-main-guard` | Bash (hot-path) | **45** | `classifyBash`, solo `git push origin main\|master` | presente, más angosto: no cubre `push -f`, `HEAD:main`, ni otros remotes |
| `protected-config-write-guard` | `PreToolUse` matcher **vacío = todas las herramientas** | **57** | solo `write`/`edit`, por substring | presente, **degradado**: de todas las herramientas a dos |
| `secret-detector` | `PreToolUse` `Bash\|Edit\|Write` | 0 | solo `write`/`edit` | **el lado Bash falta**, y `apply_patch` también |
| `subagent-budget-enforcer` | `PostToolUse` matcher vacío | 0 | **ausente**, ni siquiera está en `SIGNED_PRIMITIVES` | **falta** |
| `lethal-trifecta-gate` | `PreToolUse` matcher vacío | 0 | **ausente** | falta |
| `network-egress-guard` | Bash (hot-path, gate) | — | `classifyBash`, pero `action_kind: "warn"` | presente, **degradado a aviso** |
| `agent-control-inbound-guard` / `cosd-auth-guard` | `PreToolUse` matcher vacío | — | `classifyBash` únicamente | presente, solo por Bash |
| 9 primitivos de familia agente | `PreToolUse`/`PostToolUse` matcher `Agent` | — | `toolName === "agent"` | **inalcanzables** |

Los nueve inalcanzables: `adr-relevance-suggest`, `claim-validator`,
`confidence-gate`, `dispatch-gate`, `private-mode-gate`, `prompt-quality-llm`,
`reinvention-check`, `scope-creep-detector`, `trust-score-validator`. Son **9 de
30** primitivos firmados que no pueden ejecutarse nunca, y aun así el manifiesto
de contratos los marca `governed-wrapper-enforced`.

Además `multiedit` en la lista de escritura del plugin es una rama muerta: esa
herramienta no existe en OpenCode.

### La respuesta a la pregunta del encargo

Distinto de Codex. En Codex **ningún** guard de escritura existía. Acá los cinco
nombrados sí existen —cuatro de cinco, con `subagent-budget-enforcer` ausente— y
el problema no es la ausencia sino el **angostamiento**: un guard registrado
sobre todas las herramientas quedó reducido a dos, y el más caro
(`secret-detector`, que en Claude Code corre sobre `Bash|Edit|Write`) perdió el
lado Bash. El agujero grande no está entre los cinco nombrados: son los nueve
primitivos de familia agente, que están escritos, firmados y muertos.

---

## Lo que se construyó

**`manifests/opencode-hooks-schema.yaml`** — misma forma que el de Codex:
`sources:` con URL y `verified: 2026-08-15`, separación explícita entre claves de
`Hooks` y tipos de evento, lista de tools publicadas (con una sección
`not_tools:` para los nombres plausibles que no existen), y
`known_projection_gaps:` con seis ids.

**`tests/contracts/test_opencode_hooks_schema_conformance.py`** — compara lo que
el driver emite y lo que el plugin clasifica **contra ese manifiesto**, no contra
sí mismo. 17 casos: 11 pasan, 6 son `xfail(strict=True)` atados por id a los
gaps del manifiesto. Elegí `xfail` estricto en vez de dejar la suite en rojo:
el defecto queda **ejecutable** (no es una viñeta en un informe), la suite queda
verde, y el día que alguien arregle un gap sin tocar el manifiesto el test se
pone rojo por XPASS y lo obliga a actualizarlo. Hay además un test que verifica
que ningún gap del manifiesto quede sin chequeo ejecutable.

```
11 passed, 6 xfailed in 0.39s
```

**Por qué el test que ya existía no alcanzaba:**
`tests/contracts/test_opencode_native_adapter_design.py:63-78` afirma que un
**documento de diseño** contiene los strings `"tui.prompt.append"`,
`"session.compacted"`, etc. — o sea, verifica que la doc repita los mismos
identificadores que el driver inventó. Es un lazo cerrado: no puede detectar un
identificador equivocado, solo uno inconsistente. Los otros dos tests del archivo
se saltean si no hay binario de opencode.

---

## Qué de este encargo era falso

**Corrections to the brief's premises:**

1. **"`manifests/harness-driver-capabilities.yaml` no cita ninguna fuente
   externa" — falso.** Sí las cita: tres URLs en el bloque `opencode.evidence`
   (`opencode.ai/docs/plugins/`, `/docs/agents/`, y `open-code.ai/en/docs/rules`,
   que es otro dominio, presumiblemente un espejo). Lo que le falta no es fuente
   sino **fecha de verificación por fuente** — tiene un
   `version_baseline: "official-docs-2026-05-08"` global, de hace tres meses. Y
   el contenido que declara está equivocado en el punto de `PreCompact`.
   `grep -cE 'https?://' manifests/harness-driver-capabilities.yaml` → `3`.

2. **"No hay consumidor vivo conocido" — parcialmente falso.** OpenCode 1.16.2
   **está instalado en esta máquina**. Eso cambió el carácter del informe: pude
   medir con `opencode debug config` en vez de inferir. También significa que
   `test_opencode_native_adapter_design.py` **no** se saltea acá, aunque siga sin
   probar lo que importa.

3. **"`tui.prompt.append` me suena a un evento para agregar texto a la UI" —
   correcto, y el propio plugin ya lo sabía.** El comentario en
   `cos-primitive-guard.js:355-357` dice textualmente que OpenCode no tiene
   evento de prompt-submit y que `chat.message` es lo más cercano. O sea: alguien
   ya descubrió esto y arregló el plugin, **pero no volvió a corregir el driver
   ni el manifiesto de capacidades**. El defecto no es que nadie lo supiera; es
   que el hallazgo se aplicó en un archivo y no en los otros dos.

4. **Los números de bloqueos del encargo no reproducen.** El encargo dice
   `destructive-git-blocker` (37), `direct-main-guard` (48),
   `protected-config-write-guard` (52). Contando `action_kind == "block"` sobre
   `.cognitive-os/metrics/primitive-interventions.jsonl` completo me dan 66, 45 y
   57. No sé de qué ventana salieron los del encargo. Uso los míos y dejo el
   comando; el orden de magnitud y la conclusión no cambian.

5. **"El `plugin: [...]` con ruta relativa es sospechoso" — refutado.** Iba a
   reportarlo como defecto (la doc dice que ese array es para paquetes npm) y la
   medición lo desmintió: OpenCode resuelve la ruta y no duplica el plugin. Queda
   como redundancia, no como bug.

---

## Límite explícito de cada afirmación

- **Medido, no inferido:** que `experimental.cognitive_os_hooks` se descarta
  (aparece `experimental: {}` en la config resuelta de 1.16.2); que el plugin se
  auto-carga desde `.opencode/plugins/` sin declararlo; que declararlo no lo
  duplica; que la config no hace fallar el arranque.
- **Forma-no-coincide (medición), no parser-lo-rechaza (inferencia):** que
  `tui.prompt.append` no es un ciclo de vida sale de la doc y de la familia a la
  que pertenece, no de haber visto a OpenCode no emitirlo.
- **Lectura de código, no ejecución:** los nueve primitivos inalcanzables salen
  de cruzar el `toolName === "agent"` del plugin con la lista de tools publicada.
  **No corrí OpenCode con un modelo para verlos no dispararse** — eso costaba
  tokens de un proveedor y una sesión real. Lo que sí está medido es que `agent`
  no está entre las tools publicadas, por dos fuentes independientes (doc de
  tools y schema de `permission`).
- **No verificado:** si `throw` desde `chat.message` aborta el turno. El plugin
  asume que no y degrada a aviso; es la suposición conservadora y no la toqué.
- **No verificado:** el comportamiento con el binario en otras versiones. Todo lo
  medido es contra 1.16.2.
- **No tocado:** `scripts/cos_init.py` (otra sesión está trabajando ahí),
  `settings-driver-opencode.sh` y `cos-primitive-guard.js`. Este informe
  diagnostica y deja el control; **no repara**.

---

## Comandos que reproducen todo lo de arriba

```bash
# 1. la clave experimental se descarta (requiere opencode instalado)
mkdir -p /tmp/oc-probe/.opencode/plugins && cp opencode.json /tmp/oc-probe/
cd /tmp/oc-probe && opencode debug config | python3 -c \
  'import json,sys; print(json.load(sys.stdin)["experimental"])'   # -> {}

# 2. experimental es un objeto cerrado en el schema publicado
curl -sSL https://opencode.ai/config.json | python3 -c '
import json,sys; s=json.load(sys.stdin)
e=s["$defs"]["Config"]["properties"]["experimental"]
print(e["additionalProperties"], list(e["properties"]))'

# 3. el plugin se auto-carga sin declararlo
mkdir -p /tmp/oc-probe2/.opencode/plugins
cp packages/opencode-adapter/plugins/cos-primitive-guard.js /tmp/oc-probe2/.opencode/plugins/
echo '{"$schema":"https://opencode.ai/config.json"}' > /tmp/oc-probe2/opencode.json
cd /tmp/oc-probe2 && opencode debug config | grep -c cos-primitive-guard   # -> 1

# 4. los nueve primitivos inalcanzables (row() que solo vive dentro de un
#    bloque `toolName === "agent"`, y `agent` no es una tool de OpenCode)
python3 -c '
import re,pathlib
s=pathlib.Path("packages/opencode-adapter/plugins/cos-primitive-guard.js").read_text()
blocks=re.findall(r"if \(toolName === \"agent\"\) \{(.*?)\n  \}", s, re.S)
inside={m for b in blocks for m in re.findall(r"row\(\"([^\"]+)\"", b)}
outside=set(re.findall(r"row\(\"([^\"]+)\"", re.sub(r"if \(toolName === \"agent\"\) \{.*?\n  \}","",s,flags=re.S)))
u=sorted(inside-outside); print(len(u), u)'   # -> 9 [...]

# 5. cero cobertura de escritura sobre apply_patch
grep -n 'includes(toolName)' packages/opencode-adapter/plugins/cos-primitive-guard.js
grep -c 'apply_patch' packages/opencode-adapter/plugins/cos-primitive-guard.js   # -> 0

# 6. bloqueos medidos de los guards de Claude Code
python3 -c '
import json,collections
c=collections.Counter()
for l in open(".cognitive-os/metrics/primitive-interventions.jsonl",errors="ignore"):
    try: r=json.loads(l)
    except: continue
    if r.get("action_kind")=="block": c[r.get("primitive_id")]+=1
for k in ["destructive-git-blocker","direct-main-guard","protected-config-write-guard","secret-detector","subagent-budget-enforcer"]:
    print(f"{k:34s} {c.get(k,0)}")'

# 7. el bucket tui.prompt.append tiene 13 hooks y nadie se suscribe
python3 -c 'import json;print({k:len(v) for k,v in json.load(open(".opencode/cos-hooks.json"))["events"].items()})'
grep -n 'tui.prompt.append' packages/opencode-adapter/plugins/cos-primitive-guard.js

# 8. el manifiesto de capacidades tiene PreCompact al reves
sed -n '137,144p' manifests/harness-driver-capabilities.yaml

# 9. el control nuevo
python3 -m pytest tests/contracts/test_opencode_hooks_schema_conformance.py -q
```

---

## Fuentes

- Doc de plugins de OpenCode: <https://opencode.ai/docs/plugins/>
- Doc de tools de OpenCode: <https://opencode.ai/docs/tools/>
- Doc de config de OpenCode: <https://opencode.ai/docs/config/>
- Interfaz `Hooks` verbatim: <https://github.com/sst/opencode/blob/dev/packages/plugin/src/index.ts>
- JSON Schema publicado: <https://opencode.ai/config.json>
- Binario local: `opencode 1.16.2`
- Informe hermano (Codex): `docs/06-Daily/reports/codex-contract-forensics-2026-08-15.md`

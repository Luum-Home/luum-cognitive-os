# Forense: ¿el harness Codex ejecuta los hooks que el SO le proyecta?

Fecha: 2026-08-15
Alcance: read-only sobre el repo del SO, las 4 instalaciones `harness: codex` con
trabajo en julio, y el estado local de Codex (`~/.codex`).
Binario auditado: `codex-cli 0.147.0-alpha.6.5` (bundleado en ChatGPT.app,
build 26.803.41515). No hay `codex` en el `PATH`.

---

## 1. Veredicto

**No ejecuta.** En las 4 instalaciones auditadas, el `.codex/hooks.json` proyectado
por el SO existe pero no dejó ni un solo rastro de ejecución en los ~26 días
posteriores a su instalación; y su forma no es la que la documentación oficial de
Codex describe. Lo que **no** quedó establecido es *cuál* de los dos bloqueos manda
—forma del archivo o confianza del proyecto—, porque en mis pruebas empíricas
**tampoco** logré que corriera un `.codex/hooks.json` con la forma correcta.

---

## 2. La evidencia, separada en tres

### 2.1 Proyectado — SÍ (establecido)

Las 4 instalaciones tienen el archivo, escrito por el instalador el mismo minuto:

| Repo | `.codex/hooks.json` | `install-meta.json` | commits desde Jul-01 | commits **post-proyección** |
|---|---|---|---|---|
| `luum-agent-harness` | 5.852 B, 2026-07-20 15:10 | harness codex, v0.29.39, 18:10:41Z | 58 | 10 |
| `luum-lang` | 13.624 B, 2026-07-20 15:10 | harness codex, v0.29.39, 18:10:43Z | 39 | 0 |
| `luum-cybersecurity` | 5.538 B, 2026-07-20 15:10 | harness codex, v0.29.39, 18:10:44Z | 25 | 0 |
| `luum-woocommerce-distrinorth` | 5.538 B, 2026-07-20 15:10 | harness codex, v0.29.39, 18:10:45Z | 16 | 11 |

Comandos:

```bash
for d in luum-agent-harness luum-lang luum-cybersecurity luum-woocommerce-distrinorth; do
  q="$HOME/Projects/luum/$d"
  echo -n "$d: "
  python3 -c "import json;d=json.load(open('$q/.cognitive-os/install-meta.json'));print(d['harness'],d['version'],d['installed_at'])"
  git -C "$q" log --since=2026-07-20 --oneline | wc -l
done
```

En los 4 repos, `.codex/` contiene **solo** `hooks.json`: no hay `config.toml`,
no hay `skills/`. La proyección a Codex es un archivo, nada más.

Forma proyectada (`luum-lang`, idéntica en los otros tres):

```text
TOP-LEVEL KEYS: ['SessionStart', 'UserPromptSubmit', 'PreToolUse', 'PostToolUse', 'Stop']
SessionStart    -> matcher 'startup',   9 comandos
UserPromptSubmit-> matcher 'prompt',   11 comandos
PreToolUse      -> matcher 'bash',      1 comando
PostToolUse     -> matcher 'bash',      7 comandos
Stop            -> matcher 'shutdown', 13 comandos
```

El generador es `scripts/_lib/settings-driver-codex.sh`. La última línea de su
emisor es literal:

```python
output = {event: groups_for(event) for event in EVENT_ORDER}
print(json.dumps(output, indent=2))
```

Es decir: **los nombres de evento se emiten en la raíz del JSON, sin envoltorio.**

### 2.2 Cargado — NO, y por dos motivos independientes

**(a) La forma no coincide con la documentada.**

La doc oficial (ver §3) especifica un envoltorio `hooks` de primer nivel:

```json
{
  "description": "Optional lifecycle hooks for this workspace.",
  "hooks": {
    "SessionStart": [ { "matcher": "startup|resume", "hooks": [ ... ] } ]
  }
}
```

El `~/.codex/hooks.json` **global** de esta máquina —escrito por otras
herramientas, no por el SO— usa el envoltorio, y sus hooks demostrablemente
corren (§2.3). El proyectado por el SO no lo usa. Esa es la diferencia observable
entre lo que funciona y lo que no.

Hay una segunda discrepancia, en los `matcher`. El SO proyecta `startup`,
`prompt`, `shutdown`, `bash`. El global que funciona usa `startup` / `resume` /
`clear` / `compact` para `SessionStart` y `Bash` (mayúscula, nombre de tool) para
`PreToolUse`. `prompt` y `shutdown` no aparecen en la doc ni en ninguna config
funcionando: son inventados.

**(b) Ninguno de los 4 repos está en la lista de confianza.**

La doc dice que los hooks de proyecto solo cargan si la capa `.codex/` del
proyecto es de confianza. `~/.codex/config.toml` tiene 12 entradas
`[projects."..."] trust_level = "trusted"`. No figura ninguno de los 4 repos
—ni el repo del SO. Que el gate de confianza es real lo confirma el propio
binario: `codex exec` expone `--dangerously-bypass-hook-trust`
("Run enabled hooks without requiring persisted hook trust for this invocation").

```bash
grep -c 'trust_level' ~/.codex/config.toml            # 12
grep -c 'luum-agent-harness\|luum-lang\|luum-cyber\|luum-woocommerce' ~/.codex/config.toml   # 0
```

**Lo que NO es el bloqueo:** la feature está prendida. `codex features list`
devuelve `hooks   stable   true`. Y `plugin_hooks` figura `removed false`, o sea
que el mecanismo vigente es el de `hooks.json`, no el viejo de plugins.

### 2.3 Ejecutado — NO (evidencia negativa fuerte del lado consumidor)

Los `SessionStart` proyectados incluyen `session-init.sh`, `session-heartbeat.sh`
y `user-prompt-capture.sh`, todos los cuales **escriben archivos** bajo
`.cognitive-os/`. Si hubieran corrido una sola vez, habría rastro.

```bash
find "$q/.cognitive-os" -newermt "2026-07-20 15:11" -type f
```

Resultado por repo:

| Repo | archivos escritos post-proyección |
|---|---|
| `luum-cybersecurity` | **ninguno** |
| `luum-woocommerce-distrinorth` | **ninguno** (con 11 commits posteriores) |
| `luum-lang` | solo un `__pycache__/*.pyc` (subproducto de un import de Python, no de un hook) |
| `luum-agent-harness` | solo los propios `.sh` proyectados, re-instalados el 2026-08-04 14:52 |

`metrics/` en los 4 repos contiene, como mucho, un `backlog-reconciliation.jsonl`
de junio. `sessions/` idem. **Cero heartbeats, cero timings, cero prompts
capturados.** El caso más limpio es `luum-woocommerce-distrinorth`: 11 commits
después de la proyección, último el 2026-07-28, y ni un byte escrito por un hook.

**Contraprueba de que los hooks del harness sí funcionan cuando cargan:** en mis
corridas de `codex exec` en el scratchpad, la salida imprimió
`hook: SessionStart` / `hook: SessionStart Completed` (×3) y
`hook: UserPromptSubmit` — los del `~/.codex/hooks.json` global (con envoltorio)
más los de plugins. O sea: el runtime de hooks de este build funciona. Lo que no
carga es la capa de proyecto.

### 2.4 La prueba diferencial que hice, y hasta dónde llega

Monté en el scratchpad dos proyectos git idénticos, cada uno con un hook que
escribe un marcador, y los corrí con `codex exec -s read-only`:

- **A** = `.codex/hooks.json` con la forma **documentada** (envoltorio `hooks`).
- **B** = `.codex/hooks.json` con la forma **proyectada por el SO** (sin envoltorio).
- **CTRL** = proyecto sin ningún hook local.

Con `--dangerously-bypass-hook-trust` y `-c projects."<ruta>".trust_level="trusted"`:

| Variante | `hook: SessionStart` observados | marcador escrito |
|---|---|---|
| A (forma documentada) | 3 | **no** |
| B (forma del SO) | 3 | **no** |
| CTRL (sin hooks locales) | 3 | — |

Los tres dan idéntico. **Ni siquiera la forma documentada disparó el hook de
proyecto** en `codex exec` 0.147.0-alpha.6.5. Conclusión honesta: el experimento
demuestra que el `.codex/hooks.json` de proyecto no se carga en `codex exec` bajo
las condiciones que pude montar, pero **no aísla** si la causa es la forma, el
gate de confianza persistida (que el flag `--dangerously-bypass-hook-trust` puede
no cubrir del todo), o que `codex exec` no lea la capa de proyecto en absoluto.
Dos intentos de aislar más —`[hooks]` inline en un `.codex/config.toml` de
proyecto, y hooks inyectados por `-c hooks.SessionStart=[...]`— colgaron el
proceso hasta el timeout de 5 minutos, presumiblemente en un prompt de
aprobación interactivo. No los pude cerrar.

---

## 3. Fuentes externas

| Fuente | URL | Consultada | Qué aporta |
|---|---|---|---|
| Doc oficial de Codex — Hooks | `developers.openai.com/codex/hooks` → 308 → `learn.chatgpt.com/docs/hooks` | 2026-08-15 | Schema con envoltorio `hooks` de primer nivel; rutas `~/.codex/hooks.json`, `~/.codex/config.toml`, `<repo>/.codex/hooks.json`, `<repo>/.codex/config.toml`; contexto por **stdin JSON** (`session_id`, `hook_event_name`, `cwd`, `transcript_path`, `model`, `permission_mode`, `turn_id`); cwd de la sesión como working dir; requisito de revisar y confiar la definición exacta antes de correr un hook no gestionado; hooks de proyecto solo cargan si la capa `.codex/` es de confianza; flag para desactivar es `[features] hooks = false` (`codex_hooks` está deprecado) |
| `openai/codex` — `docs/hooks.md` | `raw.githubusercontent.com/openai/codex/main/docs/hooks.md` | 2026-08-15 | **HTTP 404.** Confirmado: el repo no publica ese archivo |

**Resolución de la duda registrada en el encargo.** Las dos fuentes secundarias
que se contradecían: la que decía "sin envoltorio" está **equivocada**. La
canónica pide envoltorio, y el `~/.codex/hooks.json` de esta máquina —que
funciona— lo usa. Y la sospecha de que `openai/codex` no publicaría `docs/hooks.md`
era correcta: 404. La doc vive en `learn.chatgpt.com/docs/hooks`.

Evidencia local que corrobora el mecanismo, sin depender de fuentes secundarias:

```bash
strings -a /Applications/ChatGPT.app/Contents/Resources/codex | grep -a 'codex_hooks::engine'
# codex_hooks::engine::command_runner   → el crate está compilado en este build
```

El binario también contiene los nombres de evento normalizados
(`pre_tool_use`, `post_tool_use`, `permission_request`, `pre_compact`,
`post_compact`, `session_start`, `session_end`, `user_prompt_submit`,
`subagent_start`, `subagent_stop`) y los mensajes de error del parser
(`Error parsing project hooks config file`, `unknown field`), lo que confirma que
la ruta de proyecto existe en el código.

---

## 4. Qué haría falta para que ejecute, y si vale la pena

Tres cosas, en orden, y **ninguna sirve sin las otras dos**:

1. **Envolver la salida del driver.** Cambio de una línea en
   `scripts/_lib/settings-driver-codex.sh`: emitir
   `{"hooks": {event: groups_for(event) ...}}` en vez del dict pelado. Barato.
2. **Corregir los `matcher`.** `prompt` y `shutdown` no existen; `bash` debería
   ser `Bash`. Requiere leer la doc evento por evento, no adivinar.
3. **Resolver la confianza.** Cada repo destino necesita `trust_level = "trusted"`
   en `~/.codex/config.toml` **y** la definición de hook aprobada vía el flujo
   `/hooks`. Esto es una acción del operador por máquina y por repo: no se puede
   proyectar desde el instalador, y no debería intentarse.

**Mi lectura sobre si vale la pena:** los pasos 1 y 2 son horas, no días, y
convierten 8 instalaciones decorativas en 8 gobernadas. Pero **antes** de tocar
el driver hay que cerrar lo que quedó abierto en §2.4: si el `.codex/hooks.json`
de proyecto no carga aunque tenga la forma correcta y el proyecto esté confiado,
arreglar la forma no cambia nada y el trabajo se pierde. El costo de establecer
eso es una sesión interactiva de Codex (no `codex exec`) en un proyecto de
descarte, con el flujo `/hooks` completo. Es la próxima medición, no la próxima
implementación.

Un dato que pesa en la decisión: dos de los cuatro repos (`luum-lang`,
`luum-cybersecurity`) tienen **cero commits** desde que se proyectó el SO. La
pregunta "¿el SO gobierna esos repos?" para ellos es hipotética.

---

## 5. Si ejecutara: qué instrumentación falta

No aplica al veredicto, pero conviene tenerlo escrito porque el arreglo lo va a
necesitar:

- **La telemetría propia sí funcionaría.** Los hooks proyectados pasan por
  `.cognitive-os/hooks/cos/_lib/hook-timing-wrapper.sh`, que escribe bajo
  `.cognitive-os/metrics/` — es del SO, no del adaptador de Claude Code. Si
  corrieran, habría archivos. La ausencia de `hook-health.jsonl` no es el
  indicador; la ausencia de **cualquier** escritura en `.cognitive-os/` sí.
- **Los logs de Codex no sirven para esto.** `~/.codex/logs_2.sqlite` tiene
  133.526 filas entre 2026-08-07 y 2026-08-15 y **cero** con `target`,
  `module_path` o `file` que contengan `hook` — pese a que en mis corridas los
  hooks globales demostrablemente corrieron. El subsistema de hooks no emite al
  log store. Cualquier chequeo futuro que se apoye en esos logs va a dar un
  falso negativo.
- **Falta un smoke de proyección.** `scripts/demo-portability-proof.sh` verifica
  que el archivo *existe* y que contiene `CODEX_PROJECT_DIR`. Verifica
  proyección, no carga: pasaría en verde con el archivo mal formado de hoy. Un
  gate que valide el schema contra la doc (envoltorio + matchers válidos) es lo
  mínimo.

---

## 6. Correcciones a las premisas del encargo

1. **"Cuatro de ellas tienen trabajo real desde julio (58/39/25/16 commits)".**
   Correcto para julio completo, pero la proyección a Codex se instaló el
   **2026-07-20 18:10Z**. Contando solo desde ahí: 10, 0, 0 y 11. La mayor parte
   de ese trabajo es **anterior** a que existiera el archivo. El caso útil para
   el argumento es `luum-woocommerce-distrinorth` (11 commits post-proyección,
   cero escrituras), no los cuatro.

2. **"Hay exactamente dos explicaciones".** Hay una tercera, y es la que
   encontré: el archivo está proyectado y con forma inválida, **y además** el
   proyecto no está en la lista de confianza. Son dos bloqueos independientes,
   y arreglar uno solo no destraba nada. La dicotomía "instrumentación vs
   abstracción no validada" se queda corta.

3. **"`.codex/hooks.json` necesita un wrapper — duda no resuelta".** Resuelta:
   **sí lo necesita**, según la doc canónica y según el `hooks.json` global de
   esta máquina que funciona.

4. **"`openai/codex` no publicaría `docs/hooks.md`".** Confirmado, 404. La doc
   está en `learn.chatgpt.com/docs/hooks`, vía redirect 308 desde
   `developers.openai.com/codex/hooks`.

5. **Premisa implícita de que la feature podría estar apagada.** No lo está:
   `codex features list` devuelve `hooks stable true`. Descartado como causa.

---

## 7. Lo que no pude establecer

- **Cuál de los dos bloqueos manda.** No aislé forma vs confianza: el proyecto
  con la forma documentada tampoco disparó su hook. Ver §2.4.
- **Si `codex exec` lee la capa de hooks de proyecto en absoluto.** Todas mis
  pruebas fueron con `codex exec` (no interactivo). Es posible que la carga de
  hooks de proyecto solo ocurra en la TUI interactiva, donde existe el flujo
  `/hooks` para revisar y confiar. Si es así, todo mi experimento mide una
  superficie distinta de la que usa el operador.
- **Qué hace exactamente `--dangerously-bypass-hook-trust`.** El texto dice
  "enabled hooks" — no sé si un hook de proyecto no confiado cuenta como
  "enabled". Los dos intentos de aislarlo colgaron.
- **El contrato de stdin en la práctica.** La doc lista los campos; no los pude
  observar, porque ningún hook de proyecto llegó a correr y por lo tanto ningún
  marcador se escribió. Los campos de §3 son doc, no observación.
- **Las otras 4 instalaciones `harness: codex`.** Solo audité las cuatro que el
  encargo señaló. No verifiqué si las otras cuatro comparten la misma forma
  proyectada (es esperable, sale del mismo driver, pero no lo medí).
- **Si alguna vez ejecutaron antes del 2026-07-20.** Las instalaciones anteriores
  pueden haber tenido otra forma. `luum-woocommerce-distrinorth` tiene un
  `.cognitive-os/sessions/codex-2026-06-18-correct-repo/` que sugiere uso de
  Codex en junio, pero no revisé la genealogía de proyecciones previas.

---

## Apéndice: comandos para reproducir

```bash
# 1. Feature flag y versión
/Applications/ChatGPT.app/Contents/Resources/codex --version
/Applications/ChatGPT.app/Contents/Resources/codex features list | grep -E '^hooks|plugin_hooks'

# 2. Forma proyectada (llaves de primer nivel)
python3 -c "import json;print(list(json.load(open('.codex/hooks.json')).keys()))"

# 3. Confianza de proyecto
grep -A1 '^\[projects' ~/.codex/config.toml | grep -c trusted

# 4. Rastro de ejecución post-proyección
find .cognitive-os -newermt "2026-07-20 15:11" -type f

# 5. Crate de hooks presente en el binario
strings -a /Applications/ChatGPT.app/Contents/Resources/codex | grep -a 'codex_hooks::engine'

# 6. Logs de Codex (spoiler: cero filas de hooks)
sqlite3 "file:$HOME/.codex/logs_2.sqlite?immutable=1" \
  "select target,count(*) from logs where target like '%hook%' group by target;"
```

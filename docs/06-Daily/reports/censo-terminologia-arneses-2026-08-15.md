# Censo de terminología: cómo nombra el repo a Claude Code, Codex, Cursor, Kiro y compañía

**Fecha:** 2026-08-15
**Alcance:** todo el árbol versionado (`git ls-files`), sin filtro de extensión.
**Naturaleza:** medición de sólo lectura. No se renombró nada, no se editó documentación.

---

## Respuesta corta

El repo **es consistente**, y el término que domina es **`harness`** — pero el hallazgo
importante es otro: **el 92,7% de las menciones a estos productos no lleva sustantivo
adjunto**. El repo casi nunca dice "el CLI de X" ni "el harness de X": dice "X" a secas.
Sobre las menciones que sí clasifican, **no hay ningún caso factualmente falso**.

Los 25 candidatos a "falso" que arrojó la medición automática son todos `Copilot CLI`,
que **es un producto real** (GitHub Copilot CLI). Cursor, Kiro, Windsurf y Devin — los
cuatro ejemplos del encargo — tienen **cero** menciones donde se los llame "CLI" con el
sustantivo adjunto.

La deriva que sí existe no es "CLI vs harness": es **qué sustantivo paraguas usa cada
capa** (`harness` / `adapter` / `driver` / `provider` / `tool`), y es una deriva
**cronológica**, no un error.

---

## 1. Cómo se midió

Tres pasadas, todas reproducibles. El repo tiene un JSON generado de **37 MB**
(`docs/06-Daily/reports/primitive-harness-coverage-latest.json`) que hace reventar
cualquier censo ingenuo por timeout — hay que excluirlo explícitamente.

### 1.1 Extracción (una sola pasada de grep)

```bash
git grep -nIE "Claude[ _-]Code|claude[_-]code|Codex|codex|OpenCode|opencode|Cursor|Kiro|Devin|Windsurf|windsurf|Aider|aider|Copilot|copilot|Cline|Continue\.dev|Goose|Zed AI|Roo Code|Gemini CLI|Qwen Code|Kilo Code|Auggie|Junie|Warp|Qoder|Tabnine|OpenHands|Replit|Bolt\.new|Lovable|Cody|Antigravity|Trae|Amp Code" \
  -- . ':!.ai/' ':!docs/06-Daily/reports/*.json' ':!docs/07-Capabilities/acc/*.json' \
       ':!*.lock' ':!**/testdata/**' > hits.txt
wc -l hits.txt   # → 15644
```

Exclusiones y su motivo:

| Excluido | Motivo |
|---|---|
| `.ai/primitives/**` (1.120 archivos) | Boilerplate generado que repite la misma línea (`"surface": "generated Cursor rules/context only"`) cientos de veces. Contarlo infla el censo sin aportar una decisión de redacción humana. |
| `docs/06-Daily/reports/*.json` | Reportes generados. Uno solo pesa 37 MB. |
| `docs/07-Capabilities/acc/*.json`, `*.lock`, `**/testdata/**` | Datos generados / fixtures. |

Los `.md` de `docs/06-Daily/` **sí** se cuentan, marcados aparte como área generada.

### 1.2 Clasificación laxa (ventana de ±55 caracteres)

```bash
python3 classify.py hits.txt > cls2.json
```

### 1.3 Clasificación estricta (adjunción real)

```bash
python3 tight.py hits.txt > tight.json
```

La estricta exige que el sustantivo esté **pegado** al producto (`X CLI`, `the X harness`,
`CLI de X`, `X es un CLI`), y **rechaza la adyacencia de lista**: si entre el producto y
el sustantivo hay una coma, un pipe de tabla o una barra, no cuenta.

**Por qué hacen falta las dos.** La laxa da 6.448 "clasificables"; la estricta, 819. La
diferencia son casi todos falsos positivos de lista:

> `docs/02-Decisions/adrs/ADR-158-...md:30` — "…surfaces such as Gemini CLI, Kiro, Cline, Goose, Amp…"

La ventana laxa lee eso como "Kiro CLI" y "Cline CLI". No lo son: el `CLI` pertenece a
**Gemini CLI**, que es el nombre del producto vecino. Reportar esos 62 "Cursor CLI" y 19
"Kiro CLI" como deriva habría sido exactamente el verde barato de este lote.

Los scripts quedan en el scratchpad de la sesión; los comandos de arriba los reproducen.

---

## 2. Las cuatro clases

Sobre el conjunto estricto — **11.279 menciones escaneadas**:

| Clase | Total | % |
|---|---:|---:|
| **Sin sustantivo adjunto** | **10.460** | **92,7%** |
| Correcto en contexto | 268 | 2,4% |
| Inconsistente (paraguas que varía por capa) | 551 | 4,9% |
| **Falso** | **0** | **0,0%** |

**La clase que manda es "sin sustantivo".** Esto cambia cómo se lee todo lo demás: el
repo nombra a estos productos por su nombre propio y sigue de largo. No hay un problema
de "llamamos CLI a un IDE" porque en 9 de cada 10 menciones **no se los llama nada**.

### 2.1 Falso — la lista está vacía

La medición marcó 25 candidatos. Los 25 son `Copilot CLI`:

```
docs/03-PoCs/research/multi-agent-orchestration-prior-art-2026-05-06.md:242  ### 2.11 GitHub Copilot — CLI + Cloud Agent
docs/04-Concepts/architecture/cross-tool-landscape.md:29                     | Copilot CLI | .agent.md + .github/copilot-instructions…
scripts/ide-bridge.sh:248                                                    echo "# Cognitive OS Rules for GitHub Copilot CLI"
```

**No son falsos.** GitHub Copilot CLI existe como producto. La marca vino de mi tabla de
categorías, que tomó del manifiesto la fila `VS Code Copilot / category: ide` — pero los
docs hablan de una tercera superficie de Copilot (CLI local), distinta de la extensión de
VS Code y del agente hosteado. El manifiesto modela dos de las tres; los docs usan la
tercera correctamente.

Los cuatro productos que el encargo señalaba como riesgo:

| Producto | Categoría real | Veces llamado "CLI" (estricto) | Cómo lo nombra el repo cuando lo nombra |
|---|---|---:|---|
| **Cursor** | `ide` | **0** | `agent` (22), `adapter` (10), `provider` (4), `IDE` (3), `editor` (2) |
| **Kiro** | `ide-cli` | 2 — y ambas dicen `Kiro CLI/IDE` | `adapter` (12), `IDE` (3) |
| **Windsurf** | ausente del manifiesto | **0** | `provider` (1) — única mención con sustantivo en todo el repo |
| **Devin** | `hosted-agent` | **0** | `provider` (14), `IDE` (2) |

Las dos de Kiro son honestas: `docs/04-Concepts/architecture/kiro-lifecycle-adapter-design.md:61`
dice "an account-backed Kiro CLI/IDE runtime smoke", y Kiro efectivamente es las dos cosas.

### 2.2 Correcto en contexto — 268, y no habría que tocar ninguna

Las 268 menciones donde aparece `CLI` adjunto se reparten así:

| Producto | `CLI` | Por qué es correcto |
|---|---:|---|
| Gemini CLI | 108 | `CLI` es parte del nombre propio del producto |
| Codex | 83 | "Codex CLI" es el nombre del producto de OpenAI |
| Copilot | 25 | "GitHub Copilot CLI" es un producto |
| Claude Code | 21 | Habla del binario/subproceso real |
| Qoder | 15 | Qoder tiene CLI (ADR-159 proyecta `AGENTS.md` para esa superficie) |
| Qwen Code | 8 | CLI real |
| Goose, Kiro, Aider, Auggie, Junie | 6 | CLI real o forma `CLI/IDE` |

Las 21 de Claude Code merecen mención aparte porque el encargo sospechaba de ellas.
Ninguna dice "Claude Code es un CLI" como definición del producto; todas apuntan al
ejecutable:

```
cos_lib/claude_executor.py:221    """Execute Claude Code CLI as a subprocess with structured output…
docs/02-Decisions/adrs/ADR-063-…:119   …they must accept the Claude Code CLI is proprietary
```

Eso es la interfaz de línea de comandos, y ahí `CLI` es la palabra justa. **Unificar a
`harness` rompería estas 268.**

### 2.3 Inconsistente — 551, y es una deriva por capas

Éste es el hallazgo real. El sustantivo paraguas varía según **qué subsistema** escribió
la línea:

| Sustantivo | Total adjunto | Dónde vive |
|---|---:|---|
| `adapter` | 139 | `docs/06-Daily` (60), `docs/adrs` (34), `docs` (21), `packages` (13) |
| `harness` | 112 | `tests` (36), `docs/adrs` (27), `docs` (24) |
| `agent` | 96 | `docs` (69) |
| `provider` | 54 | `docs` (26), `codigo` (12) |
| `driver` | 45 | `docs` (20), `codigo` (7) |
| `runtime` | 38 | `manifests` (12), `docs` (11) |
| `tool` | 26 | disperso |
| `IDE` | 10 | `docs` (4), `manifests` (2) |

Tres focos concretos:

1. **`docs/04-Concepts/architecture/cos-dispatch/**` dice `provider`.** Ahí Cursor y
   Devin son "provider adapters" (`CD-010-real-behavior-tests.md:37`,
   `CD-011-phase-5-sub-phase-ordering.md:26`, `migration.md:148`). Es un subárbol con
   vocabulario propio, anterior a la consolidación en `harness`.
2. **ADR-008 dice `tool`.** Se titula *"Multi-Tool Support — Not Claude Code-Only"* y
   está fechado 2026-03-28. Su cuerpo dice "AI coding tool ecosystem", "one adapter per
   tool". Es la capa vieja del vocabulario.
3. **La capa moderna dice `harness`.** `manifests/ai-agent-harness-landscape.yaml` es del
   2026-05-04; ADR-064 (`harness-agnostic-cognitive-os`), ADR-080/081 (`Codex harness
   adapter`), `rules/cross-harness-authoring.md`. La transición `tool → harness` ocurrió
   entre marzo y mayo de 2026.

Nada de esto es factualmente falso. `adapter` y `driver` no compiten con `harness`:
nombran **la pieza nuestra** que habla con el harness, no al harness. La competencia real
es `harness` vs `tool` vs `provider`, y ahí `harness` gana por volumen y por recencia.

### 2.4 Sin sustantivo — 10.460 (92,7%)

Conteo por producto (menciones totales / con sustantivo en ventana laxa / sin sustantivo):

| Producto | Total | c/ sust. | s/ sust. | Categoría real |
|---|---:|---:|---:|---|
| Codex | 7.599 | 2.165 | 5.434 | cli |
| Claude Code | 3.220 | 1.149 | 2.071 | cli |
| OpenCode | 2.905 | 1.081 | 1.824 | cli |
| Copilot | 1.642 | 536 | 1.106 | ide |
| Cursor | 927 | 668 | 259 | ide |
| Aider | 870 | 181 | 689 | cli |
| Devin | 325 | 158 | 167 | hosted-agent |
| Cline | 190 | 58 | 132 | ide-cli |
| Kiro | 166 | 88 | 78 | ide-cli |
| Goose | 159 | 84 | 75 | cli-desktop |
| Windsurf | 13 | 5 | 8 | ausente |

(Ventana laxa; la estricta escanea 11.279 por usar patrones sensibles a mayúsculas.)

Menciones por área:

| Área | Menciones |
|---|---:|
| `docs/06-Daily` (generado) | 5.358 |
| `docs` (no-ADR) | 4.234 |
| `manifests` | 3.574 |
| `docs/adrs` | 1.421 |
| `tests` | 1.379 |
| código (`cos_lib`, `scripts`, `hooks`, `lib`, `bin`) | 1.308 |
| `packages` | 329 |
| `skills` | 254 |
| `templates` | 29 |
| `rules` | 19 |
| raíz (`README`/`AGENTS`/`CLAUDE`) | 17 |

---

## 3. Qué dice el código, y si discrepa

**No discrepa. El código dice `harness`, y lo dice mejor que la doc.**

| Superficie | Qué dice |
|---|---|
| `cos_lib/harness_adapter/` → symlink a `packages/agent-lifecycle/lib/harness_adapter/` | Un módulo por producto: `claude_code.py`, `codex.py`, `opencode.py`, `aider.py`, `bare_cli.py`, más `base.py` y `dispatch.py`. El paraguas es `harness_adapter`; los productos no llevan sustantivo en el nombre del módulo. |
| `cognitive-os.yaml:895` | Bloque `harness:` con `hooks:` adentro. Los comentarios de arriba dicen "Event support per harness". |
| `manifests/{claude-code,codex,opencode}-hooks-schema.yaml` | Tres esquemas, uno por harness. |
| `manifests/ai-agent-harness-landscape.yaml` | 38 candidatos, cada uno con un campo **`category`** explícito. |

Ese campo `category` es la pieza que resuelve la pregunta del encargo, y ya está en el
repo:

```
Claude Code    category=cli            OpenAI Codex   category=cli
Cursor         category=ide            Kiro IDE/CLI   category=ide-cli
Devin          category=hosted-agent   Goose          category=cli-desktop
Amp Code       category=cli-ide        Warp Agent     category=terminal
```

O sea: **el repo ya separa el paraguas (`harness`) de la naturaleza de cada producto
(`category`)**, y clasifica bien — Cursor es `ide`, Devin es `hosted-agent`, Kiro es
`ide-cli`. La doc no contradice al código; la única discrepancia es que **`Windsurf` no
está en el manifiesto** (`grep -ci windsurf manifests/ai-agent-harness-landscape.yaml`
→ `0`) pero sí aparece en 8 archivos, entre ellos tres scripts de auditoría.

---

## 4. Español vs inglés

Contado aparte, como corresponde. **No es deriva: es traducción, y es limpia.**

```bash
for t in "arn[eé]s|arneses" "herramientas?" "asistentes?" "proveedor|proveedores" "agentes?" "harness|harnesses" "CLI|CLIs"; do
  n=$(git grep -ciwE "$t" -- . ':!.ai/' ':!docs/06-Daily/reports/*.json' | awk -F: '{s+=$NF} END{print s+0}')
  printf '%-26s %s\n' "$t" "$n"
done
```

| Término | Ocurrencias |
|---|---:|
| `harness` / `harnesses` | 13.069 |
| `CLI` / `CLIs` | 5.834 |
| `agente(s)` | 346 |
| `herramienta(s)` | 84 |
| `proveedor(es)` | 37 |
| `arnés` / `arneses` | **13** |
| `asistente(s)` | 1 |

Las 13 de `arnés` viven en **dos archivos**, los dos síntesis en castellano de hoy:

```
docs/06-Daily/reports/sintesis-orquestacion-multimodelo-2026-08-15.md:24   …Cero de siete arneses
docs/06-Daily/reports/sintesis-comunicacion-agentes-2026-08-15.md:98       …al menos dos arneses publican…
```

Es la traducción de `harness` dentro de texto en castellano, en documentos que son
íntegramente en castellano. Correcto. **No unificar.**

> Nota metodológica: `git grep` acá **no soporta `\b`**. `git grep -cE "arn[eé]s"` devuelve
> 23.251 (matchea dentro de "warns", "learns"); `git grep -cE "\barn[eé]s\b"` devuelve 0.
> La forma correcta es `-w`. Cualquier conteo previo de este repo hecho con `\b` está mal.

---

## 5. Recomendación

**`harness` gana, y ya ganó** — 13.069 ocurrencias contra 5.834 de `CLI`, y es lo que dice
el código. La recomendación no es unificar: es **no tocar casi nada**.

| Qué | Acción | Motivo |
|---|---|---|
| Las 268 menciones de `CLI` | **No tocar** | Todas correctas: nombre propio del producto (Gemini CLI, Codex CLI, Copilot CLI) o referencia al binario real. Un reemplazo masivo las rompería. |
| `adapter` (139) y `driver` (45) | **No tocar** | No compiten con `harness`: nombran la pieza nuestra, no al producto. |
| `arnés` en los dos docs en castellano | **No tocar** | Traducción correcta en texto castellano. |
| `provider` en `docs/04-Concepts/architecture/cos-dispatch/**` (54) | **Decisión del operador** | Vocabulario propio de un subárbol anterior. Alinearlo a `harness` es coherente, pero es una edición de ~15 archivos por un beneficio de claridad, no de corrección. |
| ADR-008 "Multi-Tool Support" | **No renombrar** | Es un ADR aceptado y fechado. Su vocabulario es el de marzo 2026. Reescribirlo borraría el rastro de cuándo cambió el término. Si molesta, va una nota de una línea apuntando a ADR-064. |
| `Windsurf` ausente de `ai-agent-harness-landscape.yaml` | **Único ítem accionable** | Aparece en 8 archivos incluidos tres scripts de auditoría, pero no tiene fila en el manifiesto. O se agrega con su `category`, o se saca de los scripts. |

**Lo que NO habría que hacer:** un buscar-y-reemplazar `CLI → harness`. Rompería las 268
que son correctas, incluidas 108 donde `CLI` es literalmente parte del nombre del producto.

**Lo que sí valdría la pena, si se quiere cerrar la pregunta de raíz:** cuando un
documento nuevo necesite el sustantivo, que use `harness` para el paraguas y cite el campo
`category` del manifiesto para la naturaleza del producto. Eso ya existe; sólo hace falta
que sea el reflejo.

---

## Correcciones a las premisas del encargo

Recontado todo lo que el encargo afirmaba. Tres premisas fallan.

1. **`lib/harness_adapter/` no existe — FALSO.**
   ```
   $ ls lib/harness_adapter/
   ls: lib/harness_adapter/: No such file or directory
   ```
   La ruta real es **`cos_lib/harness_adapter`**, symlink a
   `packages/agent-lifecycle/lib/harness_adapter`. La conclusión que el encargo sacaba de
   esa ruta (que el código dice `harness`) **es correcta**; la ruta, no.

2. **"si el código dice `harness` y la doc dice `CLI`, la deriva está entre capas" — la
   premisa condicional no se cumple.** El código dice `harness`; la doc **también** dice
   `harness` (112 adjuntos, 13.069 ocurrencias totales). No hay deriva entre capas. La
   deriva que existe es cronológica y está **dentro** de la doc (`tool` de marzo vs
   `harness` de mayo).

3. **"Cursor, Kiro y Windsurf llamados CLI es un error de hecho" — no ocurre en este
   repo.** Cero menciones estrictas de `Cursor CLI`, `Windsurf CLI` o `Devin CLI`. Las dos
   de Kiro dicen `Kiro CLI/IDE`, que es correcto. La hipótesis era razonable; la medición
   la refuta.

4. **`harness.hooks` en `cognitive-os.yaml` — CONFIRMADO**, línea 895.
   `docs/04-Concepts/architecture/cross-harness-authoring.md` — **CONFIRMADO** (6.811 bytes).
   ADR-008 se titula *"Multi-Tool Support -- Not Claude Code-Only"* y usa `tool` —
   **CONFIRMADO**.
   `manifests/*-hooks-schema.yaml` — **CONFIRMADO**, y son **tres**, no dos: `claude-code`,
   `codex` y `opencode`.

5. **"el censo ingenuo revienta el timeout" — CONFIRMADO, y encontré la causa.** No es el
   volumen de archivos (8.514): es **un solo archivo**,
   `docs/06-Daily/reports/primitive-harness-coverage-latest.json`, de **37.561.087 bytes**.
   Con ese archivo excluido, el `git grep` completo termina en menos de dos minutos y la
   clasificación en 15 segundos. Dos corridas mías se colgaron antes de darme cuenta.

6. **`timeout` no existe en este macOS** (`command not found: timeout`). Cualquier receta
   del repo que lo use falla en silencio con exit 127.

7. **Bonus, no pedido pero relevante:** `git grep` en este entorno **no soporta `\b`**.
   Un conteo hecho con `\b` devuelve 0 y parece un hallazgo ("no hay ninguna mención en
   castellano"). Es un falso negativo silencioso. Hay que usar `-w`.

---

## Anexo — reproducibilidad

```bash
# 1. extracción (≈90 s)
git grep -nIE "<patrón de productos>" -- . ':!.ai/' ':!docs/06-Daily/reports/*.json' \
  ':!docs/07-Capabilities/acc/*.json' ':!*.lock' ':!**/testdata/**' > hits.txt

# 2. clasificación laxa y estricta (≈15 s cada una)
python3 classify.py hits.txt > cls2.json
python3 tight.py    hits.txt > tight.json

# 3. categorías declaradas por el propio repo
python3 -c "import yaml;d=yaml.safe_load(open('manifests/ai-agent-harness-landscape.yaml'));\
print(len(d['candidates']));[print(c['display_name'],c['category']) for c in d['candidates']]"

# 4. conteo español vs inglés (OJO: -w, no \b)
git grep -ciwE "harness|harnesses" -- . ':!.ai/' ':!docs/06-Daily/reports/*.json' | awk -F: '{s+=$NF} END{print s}'
```

### `tight.py` — clasificador de adjunción estricta

El encargo restringía la escritura a este único archivo, así que el script va embebido
acá en vez de en `scripts/`: en el scratchpad no sobrevive al reinicio. Si el operador
quiere que sea ejecutable de verdad, esto se extrae a `scripts/censo_terminologia.py`.

```python
#!/usr/bin/env python3
"""Adjuncion ESTRICTA: el sustantivo tiene que estar pegado al producto.
Rechaza la adyacencia de lista ("Gemini CLI, Kiro, Cline"): si entre el producto
y el sustantivo hay una coma, pipe o barra de tabla, no cuenta.
Entrada: la salida de `git grep -nIE <productos>` (hits.txt).
"""
import json, re, sys
from collections import Counter, defaultdict

PRODUCTS = {
    "Claude Code": r"Claude[ _-]Code", "Codex": r"\bCodex\b",
    "OpenCode": r"\bOpenCode\b|\bopencode\b", "Cursor": r"\bCursor\b",
    "Kiro": r"\bKiro\b", "Devin": r"\bDevin\b",
    "Windsurf": r"\bWindsurf\b|\bwindsurf\b", "Aider": r"\bAider\b|\baider\b",
    "Copilot": r"\bCopilot\b", "Cline": r"\bCline\b",
    "Continue.dev": r"\bContinue\.dev\b", "Goose": r"\bGoose\b",
    "Zed AI": r"\bZed\b", "Roo Code": r"\bRoo ?Code\b", "Gemini CLI": r"\bGemini\b",
    "Qwen Code": r"\bQwen Code\b", "Kilo Code": r"\bKilo ?Code\b",
    "Auggie": r"\bAuggie\b", "Junie": r"\bJunie\b", "Qoder": r"\bQoder\b",
    "Tabnine": r"\bTabnine\b", "OpenHands": r"\bOpenHands\b",
    "Replit": r"\bReplit\b", "Amp Code": r"\bAmp\b", "Cody": r"\bCody\b",
    "Trae": r"\bTrae\b",
}
PRE = {k: re.compile(v) for k, v in PRODUCTS.items()}

NOUNS = {
    "CLI": r"CLIs?", "harness": r"harness(?:es)?", "arnes": r"arn[eé]s",
    "tool": r"tools?|tooling", "herramienta": r"herramientas?",
    "agent": r"agents?", "agente": r"agentes?", "IDE": r"IDEs?",
    "editor": r"editors?|edit[oó]r(?:es)?", "assistant": r"assistants?",
    "asistente": r"asistentes?", "provider": r"providers?",
    "proveedor": r"proveedor(?:es)?", "runtime": r"runtimes?",
    "platform": r"platforms?|plataformas?", "driver": r"drivers?",
    "adapter": r"adapters?|adaptadores?", "host": r"hosts?",
    "backend": r"backends?", "client": r"clients?|clientes?",
    "vendor": r"vendors?", "surface": r"surfaces?",
    "extension": r"extensions?|extensi[oó]n",
}
_ci = lambda n: 0 if n in ("CLI", "IDE") else re.IGNORECASE
# "X CLI", "Cursor 2.0 CLI"
RIGHT = {n: re.compile(r"^(?:\s+(?:\d[\w.]*|CLI|IDE|App|Code|Agent))?\s+(?:%s)\b" % v, _ci(n))
         for n, v in NOUNS.items()}
# "el CLI de X" / "the harness for X"
LEFT = {n: re.compile(r"(?:%s)\s+(?:de|of|for|para)\s+$" % v, _ci(n)) for n, v in NOUNS.items()}
# "X es un CLI" / "X: a harness"
COPULA = {n: re.compile(r"^\s*(?:is|es|son|are|:|=|—|--)\s*(?:an?|el|la|un|una|the)?\s*(?:%s)\b" % v, _ci(n))
          for n, v in NOUNS.items()}

# categorias declaradas por manifests/ai-agent-harness-landscape.yaml
REAL_CATEGORY = {
    "Claude Code": "cli", "Codex": "cli", "OpenCode": "cli", "Aider": "cli",
    "Gemini CLI": "cli", "Qwen Code": "cli", "Cursor": "ide", "Copilot": "ide",
    "Continue.dev": "ide", "Roo Code": "ide", "Zed AI": "ide", "Tabnine": "ide",
    "Trae": "ide", "Kiro": "ide-cli", "Cline": "ide-cli", "Kilo Code": "ide-cli",
    "Junie": "ide-cli", "Qoder": "ide-cli", "Auggie": "cli-ide",
    "Amp Code": "cli-ide", "Goose": "cli-desktop", "Devin": "hosted-agent",
    "Replit": "hosted-agent", "OpenHands": "cli-sdk-hosted",
    "Cody": "ide-enterprise", "Windsurf": "(ausente del manifiesto)",
}
NO_CLI = {"ide", "hosted-agent", "ide-enterprise"}  # llamarlos "CLI" seria falso


def area_of(rel):
    if rel.startswith("docs/02-Decisions/adrs/"):
        return "docs/adrs"
    if rel.startswith("docs/06-Daily/"):
        return "docs/06-Daily (generado)"
    if rel.startswith("docs/"):
        return "docs (no-adr)"
    for pre, name in (("rules/", "rules"), ("skills/", "skills"),
                      (".claude/skills/", "skills"), ("templates/", "templates"),
                      ("manifests/", "manifests"), ("packages/", "packages"),
                      ("tests/", "tests")):
        if rel.startswith(pre):
            return name
    if rel.startswith(("cos_lib/", "lib/", "scripts/", "hooks/", "cmd/", "bin/", "internal/")):
        return "codigo"
    if rel in ("README.md", "AGENTS.md", "CLAUDE.md"):
        return "raiz"
    return "otros"


def main():
    pair, noun_area, noun_total = Counter(), defaultdict(Counter), Counter()
    prod_attached, prod_seen = Counter(), Counter()
    snips, falsos = defaultdict(list), []

    with open(sys.argv[1], encoding="utf-8", errors="ignore") as fh:
        for raw in fh:
            parts = raw.split(":", 2)
            if len(parts) < 3:
                continue
            rel, lineno, line = parts[0], parts[1], parts[2].rstrip("\n")
            ar = area_of(rel)
            line = line[:3000]
            for prod, prx in PRE.items():
                for m in prx.finditer(line):
                    prod_seen[prod] += 1
                    right = line[m.end(): m.end() + 40]
                    left = line[max(0, m.start() - 40): m.start()]
                    hit = next((n for n in NOUNS
                                if RIGHT[n].match(right) or COPULA[n].match(right)
                                or LEFT[n].search(left)), None)
                    if not hit:
                        continue
                    prod_attached[prod] += 1
                    pair[(prod, hit)] += 1
                    noun_area[hit][ar] += 1
                    noun_total[hit] += 1
                    ctx = line[max(0, m.start() - 45): m.end() + 45].strip()
                    if len(snips[(prod, hit)]) < 12:
                        snips[(prod, hit)].append([rel, lineno, ctx])
                    cat = REAL_CATEGORY.get(prod, "?")
                    if hit == "CLI" and cat in NO_CLI:
                        falsos.append([prod, cat, rel, lineno, ctx])

    print(json.dumps({
        "product_mentions_scanned": dict(prod_seen.most_common()),
        "product_with_attached_noun": dict(prod_attached.most_common()),
        "noun_total_attached": dict(noun_total.most_common()),
        "noun_by_area": {n: dict(c.most_common()) for n, c in noun_area.items()},
        "pairs": {f"{p}||{n}": c for (p, n), c in pair.most_common()},
        "falsos_candidatos": falsos,
        "snippets": {f"{p}||{n}": v for (p, n), v in snips.items()},
    }, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
```

El clasificador laxo (`classify.py`) es el mismo bucle con una ventana de `±55` caracteres
en lugar de las tres regex de adjunción: sirve para medir cuánto ruido produce la
co-ocurrencia simple (6.448 "clasificables" contra 819 reales).

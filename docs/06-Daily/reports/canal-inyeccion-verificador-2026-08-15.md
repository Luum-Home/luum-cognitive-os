# Canal de inyección a sub-agentes: el verificador y el primer dato que entregó

**Fecha:** 2026-08-15
**Alcance:** `scripts/check_subagent_context_arrival.py`, `templates/project-gotchas.md`,
`scripts/compose_agent_prompt.py`, `docs/04-Concepts/architecture/reality-audit.md`
**Commits:** `ad1526834` (verificador), `4a90c3789` (gotchas)

---

## 1. Dónde aparece realmente el marcador

El verificador buscaba el marcador `` Phase: `reconstruction` `` dentro de un bloque
`<system-reminder>` en un mensaje de usuario. Este harness no lo entrega así. Escribe
**dos registros `type: attachment`** de nivel superior por sub-agente.

Comando (corrido sobre los 168 transcripts del proyecto):

```bash
cd ~/.claude/projects/<slug>   # slug = ruta del repo con / y . -> -
python3 - <<'PY'
import json, glob
from collections import Counter
c = Counter()
for p in sorted(glob.glob("*/subagents/*.jsonl")):
    for line in open(p, errors="ignore"):
        if "Phase: `reconstruction`" not in line:
            continue
        r = json.loads(line)
        a = r.get("attachment") or {}
        c[(r.get("type"), a.get("type"), a.get("hookEvent"))] += 1
print(c)
PY
```

Salida:

```
Counter({('attachment', 'hook_success', 'SubagentStart'): 17,
         ('attachment', 'hook_additional_context', 'SubagentStart'): 17,
         ('assistant', None, None): 7,
         ('user', None, None): 2})
```

Cero apariciones dentro de `message.content` con `<system-reminder>`. Por eso el
script daba `genuine arrivals: 0` sobre un canal que estaba entregando: buscaba la
forma que se esperaba **antes** del arreglo, no la que el harness produce.

## 2. Cómo se distingue llegada de cita después del cambio

Los dos registros `attachment` no significan lo mismo, y toda la utilidad del script
está en separarlos:

| registro | qué prueba | cuenta |
|---|---|---|
| `hook_success` | el hook salió 0 y su stdout quedó guardado | **EMISIÓN** — no |
| `hook_additional_context` | el host mergeó el payload al contexto del sub-agente | **LLEGADA** — sí |

`hook_success` es exactamente el registro que la registración `async: true` seguía
produciendo mientras nada llegaba a ningún sub-agente. Aceptarlo habría reconstruido
el verde falso que este script existe para evitar — es el verde barato de este lote, y
está rechazado en el código y en el docstring.

Guardas, en el estado en que quedaron:

1. **Turno de assistant** que escribe el marcador (un agente informando sobre el
   template) → `mention`. Conservada.
2. **Brief que cita** el marcador (un orquestador pegando este mismo chequeo en el
   prompt) → `mention`. Conservada.
3. **`hook_success`** → `mention`. Nueva.
4. **Bloque `tool_result`** con el marcador — un agente que corrió este script y se
   leyó la salida → `mention`. Nueva; la vieja regla sólo pedía `role != "assistant"`,
   y un `tool_result` viaja en un turno de usuario.
5. **`hookEvent` debe ser `SubagentStart`** — la misma clase de registro la puede
   emitir otro evento (p. ej. `UserPromptSubmit`) inyectando texto parecido. Nueva.

La forma `<system-reminder>` sigue aceptada, para builds del harness que entreguen así.

Que las guardas no son decorativas se ve en los datos: de los 24 transcripts
posteriores al arreglo, **uno queda clasificado `mention`** — es un agente que corrió
el verificador y leyó su salida.

## 3. Salida del verificador, pre y post arreglo

El corte empírico es `2026-08-15T21:58Z`: ningún transcript anterior tiene llegada,
y a partir de ahí aparecen. (El commit `508903e61` está fechado 2026-08-15 19:32 -0300
= 22:32Z, media hora **después** del primer arribo — el arreglo hizo efecto al
regenerarse `settings.json` y reiniciarse la sesión; el commit vino luego.)

```bash
python3 scripts/check_subagent_context_arrival.py --until 2026-08-15T21:58:00Z; echo "exit=$?"
python3 scripts/check_subagent_context_arrival.py --since 2026-08-15T21:58:00Z; echo "exit=$?"
```

**Pre-arreglo — rojo:**

```
marker           : 'Phase: `reconstruction`'
transcripts      : 144
genuine arrivals : 0
mentions (quoted or authored, NOT arrivals): 0

FAIL: zero sub-agents received the injected context.
exit=1
```

**Post-arreglo — verde:**

```
marker           : 'Phase: `reconstruction`'
transcripts      : 24
genuine arrivals : 20
mentions (quoted or authored, NOT arrivals): 1

OK: the injected context reaches sub-agents.
exit=0
```

Corpus completo (168 transcripts): 20 arrivals, exit 0.

Las opciones `--since` / `--until` se agregaron para esto: filtran por el primer
timestamp de cada transcript. Existen para que un arreglo se pueda demostrar sobre el
corpus real en las **dos** mitades. Un cambio que sólo produce la mitad verde no está
demostrado.

Quedan 3 transcripts post-arreglo sin llegada ni mención. No se investigaron uno por
uno; la explicación más probable es que sean sub-agentes lanzados en la ventana entre
el primer arribo y la recarga completa de la sesión, o tipos de agente fuera del
`scope` del hook. Es la incertidumbre principal de este informe.

## 4. El gotcha falso: dónde vivía y el número recontado

El texto inyectado decía:

> `SOME lib/*.py (~22%, 68 of 314) are SYMLINKS to packages/*/lib/*.py`

`lib/` **no existe en el root**:

```bash
$ ls -d lib
ls: lib: No such file or directory
```

El directorio es `cos_lib/`. Un agente que siguiera la nota buscaba en una ruta
inexistente y concluía que no hay symlinks — justo la clase de error que la nota existe
para prevenir.

Recontado (2026-08-15):

```bash
$ find cos_lib -name '*.py' -type l | wc -l
      70
$ find cos_lib -name '*.py' | wc -l
     369
```

**70 / 369 = 19,0%.** No ~22%, y el denominador no es 314. El 19,0% del encargo venía
de otro agente; se recontó acá y da lo mismo.

Ubicaciones del texto (`grep -rn "SYMLINKS to packages" .`):

| archivo | estado |
|---|---|
| `templates/project-gotchas.md` | corregido (`4a90c3789`) — fuente viva que parsea `compose_agent_prompt.py` |
| `scripts/compose_agent_prompt.py:45,50` | corregido (`4a90c3789`) — `FALLBACK_TRAPS` |
| `docs/04-Concepts/architecture/reality-audit.md:10` | nota de corrección fechada (`4a90c3789`) — es una foto de abril, se deja como foto |
| `hooks/inject-phase-context.sh:198` | **NO tocado** — config protegida. Diff propuesto en §6 |

Los números quedaron con el comando que los produjo y la fecha en que se corrió. Poner
el número correcto suelto era el segundo verde barato de este lote: un número sin
comando no se puede rechequear, así que envejece en silencio — que es exactamente cómo
se llegó a "~22% de 314".

## 5. El resto de los gotchas del bloque

Verificados uno por uno. Cinco más estaban mal.

| afirmación | verificación | veredicto |
|---|---|---|
| `lib/` es el directorio de paquetes | `ls -d lib` → no existe | **FALSO** — es `cos_lib/`. Corregido |
| ~22% (68 de 314) son symlinks | `find cos_lib -name '*.py' -type l \| wc -l` = 70; total 369 | **FALSO** — 19,0% (70/369). Corregido |
| `lib/peer_card.py` es symlink (ejemplo) | `ls -la cos_lib/peer_card.py` → `-rw-r--r--` | **FALSO** — archivo regular. Ejemplos reemplazados por tres verificados hoy (`batch_runner.py`, `ground_truth.py`, `cost_predictor.py`) |
| correr `scripts/cos-lib-symlink-invariant-audit.py` | `ls scripts/ \| grep symlink` → `cos_lib_symlink_invariant_audit.py` | **FALSO** — nombre con guiones; el real es snake_case (`rules/python-naming`). El comando recomendado fallaba. Corregido |
| "48/93 hooks intentionally not wired" | `ls hooks/*.sh \| wc -l` = 257; `grep -o 'hooks/[a-z0-9_-]*\.sh' .claude/settings.json \| sort -u \| wc -l` = 154 | **FALSO** — 154 de 257. Corregido |
| profiles `lean=7, standard=18, full=all` | `grep -A2 '^efficiency:' cognitive-os.yaml` → `profile: default  # default \| full (ADR-093)` | **FALSO** — ADR-093 colapsó a dos tiers. Corregido |
| comando `grep "profile:" cognitive-os.yaml` | devuelve 4 profiles de docker compose **antes** que el de efficiency | **ENGAÑOSO** — corregido a `grep -A2 '^efficiency:' cognitive-os.yaml \| grep 'profile:'` |
| dir-symlinks: `harness_adapter/`, `providers/` | `find cos_lib -maxdepth 1 -type l` con test de directorio | **INCOMPLETO** — falta `cos_lib/event_projections/` → `packages/agent-lifecycle/lib/event_projections`. Agregado |
| `harness_adapter/` → `packages/agent-lifecycle/lib/harness_adapter` | `readlink` | **CIERTO** |
| `providers/` → `packages/llm-providers/lib` | `readlink` | **CIERTO** |
| no hacer `rm + ln -s` para "recrear" el symlink | `hooks/symlink-mutation-guard.sh` existe | **CIERTO** |
| settings.json es generado por `scripts/_lib/settings-driver-claude-code.sh` | archivo existe; `apply-efficiency-profile.sh` existe | **CIERTO** |
| `scripts/topology-discover.sh` | existe | **CIERTO** |
| `docs/08-References/root/adw-patterns.md` | existe | **CIERTO** |
| `docs/05-Methodology/guides/adding-a-harness-adapter.md` | existe | **CIERTO** |
| `rules/llm-dispatch.md`, `scripts/orchestrator.py` | existen; `lib/dispatch.py` → es `cos_lib/dispatch.py` | **CIERTO** con la ruta corregida |

Comando único que reproduce toda la columna del medio:

```bash
ls -d lib; find cos_lib -name '*.py' -type l | wc -l; find cos_lib -name '*.py' | wc -l
ls -la cos_lib/peer_card.py
ls scripts/ | grep -i symlink
find cos_lib -maxdepth 1 -type l -exec sh -c 'test -d "$1" && echo "$1 -> $(readlink "$1")"' _ {} \;
ls hooks/*.sh | wc -l
grep -o 'hooks/[a-z0-9_-]*\.sh' .claude/settings.json | sort -u | wc -l
grep -A2 '^efficiency:' cognitive-os.yaml | grep 'profile:'
```

Ocho de dieciséis afirmaciones del bloque eran falsas, incompletas o engañosas. El que
se reportó era el primero de una serie, no una excepción.

## 6. Diff propuesto para `hooks/inject-phase-context.sh` (config protegida — NO aplicado)

Línea 198. Además del `lib/` y los números, la línea 203 recomienda
`apply-efficiency-profile.sh standard`, y `standard` dejó de ser un profile válido con
ADR-093 (`default | full`).

```diff
--- a/hooks/inject-phase-context.sh
+++ b/hooks/inject-phase-context.sh
@@ -193,7 +193,7 @@
 if [[ -n "$AGENT_PROMPT" ]]; then
-  # lib/ symlink trap
+  # cos_lib/ symlink trap
   if echo "$AGENT_PROMPT" | grep -qiE 'lib/|packages/.*lib|duplicate.*lib|dedup'; then
     GOTCHAS="${GOTCHAS}
-NOTE: SOME lib/*.py (~22%, 68 of 314) are SYMLINKS to packages/*/lib/*.py. Most are real files. Verify per file with: ls -la lib/<file>.py. If <file>.py exists in BOTH lib/ AND packages/*/lib/, run scripts/cos-lib-symlink-invariant-audit.py to detect silent drift (3 confirmed drifts as of 2026-05-11 — see ADR-267 §Layer 1 Hook #7). Check symlink direction before replacing files in packages/*/lib/."
+NOTE: there is no lib/ at the repo root — the package dir is cos_lib/. SOME cos_lib/*.py are SYMLINKS to packages/*/lib/*.py; most are real files (70 of 369 = 19.0% on 2026-08-15 — recount with: find cos_lib -name '*.py' -type l | wc -l ; find cos_lib -name '*.py' | wc -l). Verify per file with: ls -la cos_lib/<file>.py. Three whole directories are symlinks too: cos_lib/harness_adapter, cos_lib/event_projections, cos_lib/providers. If <file>.py exists in BOTH cos_lib/ AND packages/*/lib/, run python3 scripts/cos_lib_symlink_invariant_audit.py to detect silent drift (3 confirmed drifts as of 2026-05-11 — see ADR-267 §Layer 1 Hook #7). Check symlink direction before replacing files in packages/*/lib/."
   fi
@@ -203,3 +203,3 @@
     GOTCHAS="${GOTCHAS}
-NOTE: .claude/settings.json is GENERATED (ADR-064): ... Register in cognitive-os.yaml, then run: bash scripts/apply-efficiency-profile.sh standard"
+NOTE: .claude/settings.json is GENERATED (ADR-064): ... Register in cognitive-os.yaml, then run: bash scripts/apply-efficiency-profile.sh default"
   fi
```

El regex de disparo (`lib/|packages/.*lib|...`) no necesita cambio: `lib/` matchea
`cos_lib/` como substring, así que la trampa sigue disparando.

## 7. Correcciones a las premisas del encargo

Lo que se rechequeó y **no** dio lo que decía el encargo:

- **"161 transcripts"** → son **168** al momento de correr esto
  (`ls */subagents/*.jsonl | wc -l`). Y **"0 de 149"** → el corte real es 144
  pre-arreglo / 24 post-arreglo. La cuenta se movió porque siguen naciendo transcripts
  mientras se trabaja; el número del encargo era correcto cuando se escribió.
- **"~22%, 68 of 314"** → 19,0%, 70 de 369. Confirmado el 19,0% que el encargo
  atribuía a otro agente y pedía recontar: da lo mismo.
- **"el bloque inyectado incluye `SOME lib/*.py (~22%, 68 of 314)`"** → esa forma
  exacta, con los números, **no** viaja por `subagent-context-injector.sh`. Vive en
  `hooks/inject-phase-context.sh` (PreToolUse:Agent), que es otro hook. El payload que
  este agente recibió de `subagent-context-injector.sh` trae la sección
  "Filesystem: Symlinks" con `hooks/ → packages/*/hooks/`, sin porcentajes. Los dos
  canales inyectan gotchas; el falso estaba en el segundo. No cambia el arreglo, pero
  sí de dónde había que sacarlo.
- **"buscá `templates/project-gotchas.md`, un hook, o el generador"** → los tres, más
  un cuarto: `docs/04-Concepts/architecture/reality-audit.md`.
- **"`timeout` no existe en este macOS"** → no se necesitó, no se verificó.
- **Restricciones verificadas, no asumidas:** `git status --porcelain` antes de cada
  commit y `git commit --only -- <paths>` con pathspec explícito; ningún `git add -A`,
  ningún `--amend`. `hooks/inject-phase-context.sh` **no** es symlink a `packages/`
  (`ls -la` → archivo regular), así que no había forma de editarlo "por la puerta de
  atrás" de un path no protegido; se respetó la restricción y va como diff propuesto.
- **Lo que sí resultó cierto:** `hooks/**` protegido y el gotcha vive ahí (§6);
  `scripts/` y `templates/` escribibles; el verificador daba rojo sobre algo que anda;
  el marcador aparece en registros `type=attachment`; `ls -d lib` falla.

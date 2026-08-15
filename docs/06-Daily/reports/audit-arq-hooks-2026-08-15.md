# Auditoría de arquitectura — capa de hooks y cadena de registro

- Fecha: 2026-08-15
- Alcance: `hooks/`, `hooks/_lib/`, `.claude/settings.json` (generado), `cognitive-os.yaml > harness.hooks`, `scripts/_lib/settings-driver-claude-code.sh`, perfiles.
- Método: read-only. Los hooks que se invocaron a mano corrieron con payloads de stdin desde el scratchpad, con `git status --porcelain` antes y después de cada tanda.
- HEAD al inicio `fe888ab7f`, al cierre `0bbd3b3db` (una sesión concurrente commiteó durante la auditoría; ninguno de esos commits es mío).

---

## 1. Veredicto

La capa está **registrada y corriendo, pero no gobernada**: 154 hooks se proyectan bien y 149 disparan, y sin embargo el registro canónico que el propio driver declara (`cognitive-os.yaml`) es decorativo, el 73% de los hooks no puede bloquear ni queriendo, y el único camino de bloqueo del validador de claims que no depende de `phase` está muerto por un operador `//` de jq mal usado.

---

## 2. Censo

| Medida | Valor |
|---|---|
| Archivos trackeados en `hooks/` | 300 |
| Symlinks | 42 (40 → `packages/`, 2 internos) |
| Descontando `_lib/` (38), `_archived/` (3 `.bak`), `.disabled` (2), `.txt` (1) | 257 entradas |
| **Hooks únicos** (symlink + destino = UNO) | **255** — 40 viven en `packages/` |
| **Registrados** (perfil `maintainer`, el activo) | **162 registraciones / 154 hooks únicos** |
| **Dispararon** | **149 hooks distintos, 10.673 invocaciones** |
| **Bloquearon** (`exit 2`) | **19 invocaciones, 4 hooks** |

Distribución de exit codes: `0` → 10.624; `2` → 19; `141` → 18; `1` → 12.

Los cuatro que bloquearon: `subagent-budget-enforcer` (12), `bash-hot-path-dispatcher` (3), `provenance-scan` (3), `protected-config-write-guard` (1). Ninguno pertenece al safety-mesh anunciado.

`exit 141` es SIGPIPE (128+13), todos en `PostToolUse`: `context-watchdog` (5), `private-mode-metrics-gate` (5), `edit-lock-drain-parked` (4), `auto-checkpoint` (4). Son hooks que escriben a un pipe ya cerrado; hoy pasan por buenos ceros en cualquier lectura que no discrimine el código.

Registraciones por perfil, medidas contra una copia del repo en el scratchpad:

| PROFILE | registraciones | hooks únicos |
|---|---|---|
| core | 137 | 128 |
| team | 141 | 133 |
| maintainer | 162 | 154 |
| lab | 162 | 154 |
| full | 193 | 183 |

`lab` y `maintainer` emiten exactamente lo mismo: hoy son un perfil con dos nombres.

<details><summary><code>scratchpad/censo-real.sh</code></summary>

```bash
#!/usr/bin/env bash
# Censo real de hooks: identidad = destino tras readlink -f (symlink+destino = UNO)
cd "$(git rev-parse --show-toplevel)"
OUT="${1:?uso: censo-real.sh <archivo-salida>}"
git ls-files hooks/ | while read -r f; do
  case "$f" in hooks/_lib/*|hooks/_archived/*|*.disabled|*.bak|*.txt) continue;; esac
  printf "%s\t%s\n" "$(readlink -f "$f")" "$f"
done > "$OUT"
echo "entradas ejecutables:              $(wc -l < "$OUT")"
echo "hooks unicos (symlink+dest = UNO): $(cut -f1 "$OUT" | sort -u | wc -l)"
echo "  de esos, viven en packages/:     $(cut -f1 "$OUT" | sort -u | grep -c '/packages/')"
```
</details>

<details><summary><code>scratchpad/telemetria.py</code> — censo de ejecución</summary>

```python
#!/usr/bin/env python3
"""Censo de ejecucion real a partir de hook-timing.jsonl."""
import json, collections, os
path='.cognitive-os/metrics/hook-timing.jsonl'
rows=[]; bad=0
for line in open(path, errors='replace'):
    line=line.strip()
    if not line: continue
    try: rows.append(json.loads(line))
    except Exception: bad+=1
print(f"filas parseadas: {len(rows)}  (corruptas: {bad})")
hooks=collections.Counter(); exits=collections.Counter()
per_hook_exit=collections.defaultdict(collections.Counter)
dur=collections.defaultdict(list)
for r in rows:
    h=os.path.basename(str(r.get('hook','?')))
    hooks[h]+=1; ec=r.get('exit_code'); exits[ec]+=1
    per_hook_exit[h][ec]+=1
    d=r.get('duration_ms')
    if isinstance(d,(int,float)): dur[h].append(d)
print(f"\nhooks distintos que dispararon: {len(hooks)}")
print(f"invocaciones totales: {sum(hooks.values())}")
for ec,c in exits.most_common(): print(f"  exit={ec}: {c}")
print("\n== quien devolvio exit 2 ==")
for h,cc in sorted(per_hook_exit.items()):
    if cc.get(2): print(f"  {h}: {cc[2]}")
```
</details>

---

## 3. Cobertura de superficies

**Corrijo la premisa del encargo.** No es cierto que `Monitor`, `Task`, `WebFetch`, `WebSearch` y MCP queden sin gobernar. Hay **bloques con `matcher: ""`**, que en Claude Code matchean *toda* herramienta:

- `PreToolUse` `matcher=""` (5): `protected-config-write-guard`, `cosd-auth-guard`, `agent-control-inbound-guard`, `session-heartbeat`, `lethal-trifecta-gate`.
- `PostToolUse` `matcher=""` (6): `context-watchdog`, `subagent-budget-enforcer`, `rate-limit-detector`, `tool-sequence-capture`, `aci-observation-capture`, `private-mode-metrics-gate`.

Verificado que son string vacío y no clave ausente:

```bash
python3 -c "
import json; d=json.load(open('.claude/settings.json'))
for ev in ['PreToolUse','PostToolUse']:
    print(ev, 'sin-clave=', sum(1 for m in d['hooks'][ev] if 'matcher' not in m),
              'vacio=',    sum(1 for m in d['hooks'][ev] if m.get('matcher')==''))
"
# PreToolUse sin-clave= 0 vacio= 1
# PostToolUse sin-clave= 0 vacio= 2
```

Los matchers **nombrados** cubren: `Bash`, `Edit`, `Write`, `MultiEdit`, `Read`, `Grep`, `Glob`, `LS`, `Agent`, `Skill`, `TodoWrite`, y dos grupos MCP de engram (`mem_save|mem_update|mem_session_summary|mem_session_end` y `mem_search|mem_get_observation`).

El enunciado correcto es más chico y más útil: sobre `Monitor`, `Task`, `WebFetch`, `WebSearch` y todo MCP que no sea engram **no hay ni un hook específico**; sólo los alcanzan los 11 genéricos, que son sobre todo telemetría (`tool-sequence-capture`, `aci-observation-capture`, `context-watchdog`) más tres guards de escritura/credenciales. En particular **`WebFetch` y `WebSearch` no tienen ningún control de contenido**, y `lethal-trifecta-gate` — que es el que conceptualmente debería mirar exfiltración por web — corre en `PreToolUse` genérico pero nunca devolvió `exit 2` en 447 invocaciones.

---

## 4. La cadena de registro

### El diagnóstico, con la línea

`scripts/_lib/settings-driver-claude-code.sh` declara en su cabecera (líneas 6-7):

> `ADR-064: canonical hook registry lives in cognitive-os.yaml > harness.hooks.`
> `This driver is the single path that writes .claude/settings.json hooks block.`

y asigna en la **línea 39**:

```bash
CONFIG_FILE="$PROJECT_DIR/cognitive-os.yaml"
```

**Esa es su única aparición en las 614 líneas del archivo.**

```bash
grep -n 'CONFIG_FILE' scripts/_lib/settings-driver-claude-code.sh
# 39:CONFIG_FILE="$PROJECT_DIR/cognitive-os.yaml"
```

El driver emite literales hardcodeados vía `_cc_hook_group`, con el nombre de cada script escrito a mano en el `case "$PROFILE"`. El YAML no se lee nunca.

### Qué pasa si alguien registra un hook hoy

Nada. Lo probé sobre una copia del repo en el scratchpad: inyecté una entrada `JUEZ-CANARIO` en `harness.hooks` y comparé el `--emit` contra el baseline.

```
=== diff baseline vs con-hook-nuevo ===
IDENTICOS -> el YAML no influye en la salida
=== canario aparece en la salida? ===
0
```

El hook declarado no aparece, no hay warning, y el driver sale 0. Un mantenedor que siga la cabecera del propio driver agrega su hook al YAML, ve el `--check` en verde y se va con la idea de que quedó registrado.

<details><summary><code>scratchpad/canario.sh</code> — el experimento</summary>

```bash
#!/usr/bin/env bash
# Prueba que cognitive-os.yaml > harness.hooks no influye en la salida del driver.
# Trabaja sobre una COPIA en el scratchpad; no toca el repo.
set -euo pipefail
S="${1:?uso: canario.sh <scratchpad>}"
cd "$(git rev-parse --show-toplevel)"
rm -rf "$S/fixture"; mkdir -p "$S/fixture/.claude" "$S/fixture/scripts/_lib"
cp cognitive-os.yaml "$S/fixture/"
cp scripts/_lib/settings-driver-claude-code.sh "$S/fixture/scripts/_lib/"
echo '{}' > "$S/fixture/.claude/settings.json"

PROJECT_DIR="$S/fixture" bash "$S/fixture/scripts/_lib/settings-driver-claude-code.sh" \
  --emit > "$S/emit-base.json"

python3 - "$S/fixture/cognitive-os.yaml" <<'PY'
import sys, yaml
p = sys.argv[1]
d = yaml.safe_load(open(p))
d['harness']['hooks']['JUEZ-CANARIO'] = {
    'script': 'hooks/juez-canario-inexistente.sh',
    'event': 'PreToolUse', 'matcher': 'Bash', 'scope': 'os-only'}
open(p, 'w').write(yaml.safe_dump(d, sort_keys=False))
PY

PROJECT_DIR="$S/fixture" bash "$S/fixture/scripts/_lib/settings-driver-claude-code.sh" \
  --emit > "$S/emit-canario.json"

if diff -q "$S/emit-base.json" "$S/emit-canario.json" >/dev/null; then
  echo "IDENTICOS -> el YAML no influye en la salida"; exit 1
else
  echo "DIFIEREN -> el YAML si se lee"; exit 0
fi
```
</details>

### Cuánto drift produjo

Menos del esperable, porque alguien mantiene los dos lados a mano:

```
declarados en cognitive-os.yaml > harness.hooks : 190
literales hardcodeados en el driver             : 184
interseccion                                    : 184
emitidos por el driver sin estar en el yaml     : 0
```

Los 6 declarados que el driver nunca emite:

| Script | ¿Exclusión declarada? |
|---|---|
| `hooks/auto-refine.sh` | sí — `claude_projection: false` + `projection_note` |
| `hooks/auto-verify.sh` | sí — idem |
| `hooks/dod-gate.sh` | sí — idem |
| `hooks/task-completed.sh` | sí — `default_projection: false` |
| `hooks/concurrent-write-guard-codex-proxy.sh` | sí — `claude_projection: false` |
| **`hooks/publication-safety.sh`** | **no — `scope: both`, `event: PreToolUse`, `matcher: Bash`, sin ninguna flag de exclusión** |

`publication-safety` es el único drift genuino: está declarado para proyectarse y no se proyecta. Existe como archivo y `grep -c publication-safety .claude/settings.json` da `0`. `manifests/hook-registration-classification.yaml` lo lista como `conditional_opt_in` — o sea que la decisión sí está escrita, pero en un tercer archivo que tampoco lee nadie en tiempo de ejecución.

El detalle que importa: los cinco con flags `projection: false` **no están excluidos por esas flags**. El driver tampoco las lee. Coinciden porque alguien hizo los dos cambios a mano. Son documentación de una decisión, no un control.

`.claude/settings.json` es byte-idéntico al `--emit` del driver con `PROFILE=maintainer` (37.534 bytes, `a == b` en Python). No hay drift entre el generado y el commiteado; el problema es aguas arriba.

---

## 5. Fallan abierto vs fallan cerrado

Sobre los 255 hooks únicos:

| | |
|---|---|
| **Capaces de bloquear** (`exit 2` o `permissionDecision: deny/block`) | **68 (26%)** |
| **Sólo pueden fallar abierto** | **187 (73%)** |
| Con `\|\| true` | 197 |
| Con `2>/dev/null` | 235 |
| Con `set -e` | 60 |
| Con `set -e` **y** `\|\| true` (se anulan) | 51 |

### ¿Está decidido o es accidental?

**Está decidido, y está escrito — pero en la librería compartida, no en un contrato de la capa.** `hooks/_lib/common.sh` codifica fail-open en cada helper: `require_tool` sale `exit 0` si no matchea (línea 55), `check_private_mode` sale `exit 0` (línea 104), `check_capability_level` sale `exit 0` (línea 177), `check_disabled_env` sale `exit 0` (línea 209). La línea 190 lo dice explícito:

> `# Always exits 0 (never blocks), so it is safe for security-critical hooks too`
> `# (operator responsibility to not disable safety-critical hooks).`

67 hooks sourcean `common.sh` y 121 sourcean algún `_lib`. Así que el default es deliberado a nivel librería.

Lo que **no** existe es la otra mitad: ningún documento dice qué hooks *deberían* fallar cerrado, ni hay un contrato de exit codes de la capa. Busqué en `rules/` y `docs/04-Concepts/architecture/`: aparecen menciones sueltas (`hook-quality-system.md:50` dice `safe_degradation: fail_closed_when_confident_otherwise_warn`), pero ninguna norma que asigne modo de falla por hook. El resultado es que **el fail-open global está decidido y el fail-closed puntual es accidental** — cada hook resolvió por su cuenta, y ahí es donde se rompe.

### El caso que lo demuestra: `claim-validator` línea 77

Este es el hallazgo más grave del informe.

`hooks/claim-validator.sh` tiene tres `exit 2`. Dos están gateados por `phase` (líneas 141 y ~198, ambos `production`/`maintenance`). **El tercero, línea 86, es el único independiente de `phase`** — de hecho corre *antes* de que `PHASE` se defina, en la línea 92. Es el enforcer de ADR-244.

Está muerto. La línea 77:

```bash
ENFORCER_OK=$(printf '%s' "$ENFORCER_OUT" | jq -r '.ok // true' 2>/dev/null || printf 'true')
```

El operador `//` de jq devuelve la alternativa cuando la izquierda es **`false` o `null`**. `.ok // true` no puede devolver `false` nunca.

```bash
echo '{"ok":false}' | jq -r '.ok // true'   # => true    <-- el bug
echo '{"ok":true}'  | jq -r '.ok // true'   # => true
echo '{}'           | jq -r '.ok // true'   # => true
echo '{"ok":false}' | jq -r '.ok'           # => false   <-- lo correcto
```

Demostrado punta a punta. `scripts/claim_enforcer.py` funciona bien y dictamina bloqueo:

```json
{ "findings": [{"code": "verification-field-missing", "severity": "block"}],
  "ok": false, "status": "block", "triggered": true }
```

y el `bash -x` del hook sobre el mismo input muestra la señal perdiéndose:

```
+ ENFORCER_OUT=$'{... "ok": false, ... "status": "block", "triggered": true }'
+ ENFORCER_OK=true          <-- aca
+ ENFORCER_STATUS=block
...
+ exit 0
```

O sea: `claim-validator` está registrado, disparó 53 veces, tiene el `status=block` en la mano, y sale 0.

Hay además dos fail-open apilados sobre el mismo camino: `python3 ... 2>/dev/null || true` hace que un `claim_enforcer.py` ausente o roto produzca `ENFORCER_OUT` vacío → `ENFORCER_OK=true` → pasa. Lo verifiqué moviendo el script: mismo input, `exit=0`, sin una línea de stderr.

<details><summary><code>scratchpad/prueba-claim-validator.sh</code></summary>

```bash
#!/usr/bin/env bash
# Demuestra que el camino de bloqueo ADR-244 de claim-validator es inalcanzable.
# Read-only sobre el repo: la fixture vive en el scratchpad.
set -uo pipefail
S="${1:?uso: prueba-claim-validator.sh <scratchpad>}"
cd "$(git rev-parse --show-toplevel)"
git status --porcelain > "$S/gb.txt"

# 1) El operador // de jq nunca devuelve false
echo "--- jq: '.ok // true' sobre ok=false ---"
echo '{"ok":false}' | jq -r '.ok // true'      # => true (deberia ser false)

# 2) El enforcer, solo, dictamina bloqueo
printf '## Trust Report\nRan the suite: 42 passed, all green. Migration done.\n' > "$S/t.txt"
echo "--- claim_enforcer.py ---"
python3 scripts/claim_enforcer.py --project-dir "$S/fixture" \
  --response-file "$S/t.txt" --json | jq -c '{ok,status,triggered}'

# 3) El hook, con el MISMO texto, sale 0
cat > "$S/payload.json" <<'JSON'
{"tool_name":"Agent","tool_response":"## Trust Report\nRan the suite: 42 passed, all green. Migration done."}
JSON
echo "--- hooks/claim-validator.sh ---"
PROJECT_DIR="$S/fixture" bash hooks/claim-validator.sh < "$S/payload.json" >/dev/null 2>&1
echo "exit=$?  (esperado 2 si el gate funcionara; da 0)"

git status --porcelain > "$S/ga.txt"
diff "$S/gb.txt" "$S/ga.txt" && echo "NO-MUTACION OK"
```
</details>

### Sobre el resto del mesh

Las 14 capas anunciadas en `docs/04-Concepts/root/safety-mesh.md` son en realidad 12 hooks + 2 librerías. Auditadas:

| capa | existe | registrada | disparos | exit 2 |
|---|---|---|---|---|
| clarification-gate | sí | sí | 9 | 0 |
| blast-radius | sí | sí | 9 | 0 |
| dry-run-preview | sí | **no** | 0 | 0 |
| rate-limiter | sí | **no** | 0 | 0 |
| scope-proportionality | sí | sí | 9 | 0 |
| claim-validator | sí | sí | 53 | 0 |
| assumption-tracker | sí | sí | 9 | 0 |
| trust-score-validator | sí | sí | 9 | 0 |
| confidence-gate | sí | sí | 9 | 0 |
| clarification-interceptor | sí | **no** | 0 | 0 |
| auto-rollback-trigger | sí | sí | 9 | 0 |
| reinvention-check | sí | sí | 9 | 0 |

**9 registradas, 9 dispararon, 0 bloquearon.** Confirmo la premisa del encargo en este punto. Las 3 sin registrar son justamente las que el doc describe como bloqueantes duras (`dry-run-preview` y `rate-limiter` son 2 de las 4 capas «BLOCK» de pre-lanzamiento).

Para `confidence-gate` y `scope-proportionality` la premisa del encargo también es correcta: su `exit 2` está detrás de `[[ "$PHASE" == "production" || "$PHASE" == "maintenance" ]]`, y `phase: reconstruction` está fijado desde el commit inicial (`db4100405`). Para `claim-validator` la premisa es correcta en la conclusión pero equivocada en el mecanismo: su camino no-gateado por phase existe, y lo que lo mata es el bug de jq.

---

## 6. Arquitectura: orden, contratos, latencia

**No hay orden ni dependencias declaradas.** Las claves disponibles en `harness.hooks` son `['async','claude_projection','codex_gap_reason','codex_projection','default_projection','event','matcher','profiles','projection_note','scope','script']`. No hay `depends_on`, `run_after`, `priority` ni `order`. El orden efectivo es el orden del array que el driver escribe a mano, y es implícito: cambiar dos líneas en el `case` del driver reordena la ejecución sin que nada lo señale.

**El campo `async` es sospechoso.** El driver emite `"async": true` en 50 de las 162 entradas. El esquema de hooks de Claude Code contempla `type`, `command` y `timeout`; `async` no es una clave que el harness reconozca. **0 de las 162 entradas llevan `timeout`.** Si `async` se ignora, esos 50 hooks corren sincrónicos y bloqueantes, sin techo de tiempo. La telemetría es consistente con eso:

| evento | n | media ms | p95 ms | total s |
|---|---|---|---|---|
| Stop | 437 | 8.625 | 10.457 | **3.769** |
| PostToolUse | 7.001 | 234 | 555 | 1.641 |
| PreToolUse | 4.070 | 293 | 565 | 1.193 |
| SessionStart | 189 | 582 | 2.037 | 110 |
| UserPromptSubmit | 252 | 321 | 1.219 | 81 |
| SubagentStart | 16 | 399 | 956 | 6 |

**Total: 6.800 s (1,89 h) de reloj gastados en hooks, en 11.965 invocaciones.**

El `Stop` es el desastre: 8,6 s de media. Un solo hook explica el 89,2%:

| hook | n | media ms | total s | % de Stop |
|---|---|---|---|---|
| **quality-duplicates** | 19 | **176.974** | **3.362** | **89,2%** |
| engram-crystallize-on-session-end | 19 | 10.365 | 197 | 5,2% |
| edit-lock-session-end | 19 | 3.286 | 62 | 1,7% |

`quality-duplicates` tarda **2 minutos 57 segundos de media** por cierre de sesión, y está declarado `"async": true` sin `timeout`. Si `async` no hace nada, cada `Stop` de esta sesión pagó tres minutos.

**Contrato de entrada:** por stdin, JSON. Pero cada hook lo parsea a mano con `jq` y sus propios fallbacks. `claim-validator` líneas 51-55 son un buen ejemplo del costo: prueba `.tool_response`, después `.tool_response.result // .output // .content`, y remata con

```bash
[ -z "$RESPONSE" ] || [ "$RESPONSE" = "null" ] && exit 0
```

que en bash parsea como `(A || B) && C` — funciona por casualidad acá, pero es el mismo patrón que en otro orden sale mal. Existe `hooks/_lib/normalize-stdin.sh`, pero sólo 121 de 255 hooks sourcean algún `_lib`.

---

## 7. Duplicación conceptual

Listada, sin unificar nada.

**a) Dos esquemas de lock sobre el mismo matcher `PreToolUse[Edit|Write]`.**
`edit-lock-pre-tool.sh` (ADR-098) usa metadatos propios en `.cognitive-os/runtime/edit-locks/<path>/meta.yaml`, liberados por `edit-lock-session-end.sh`. `concurrent-write-guard.sh` usa `flock` real del SO sobre `$LOCKS_DIR/${FILE_HASH}.lock`. Los dos están registrados, corren uno detrás del otro sobre el mismo archivo, y no se conocen. Además `concurrent-write-guard.sh:105` degrada a advisory si `flock` no existe.

**b) Tres chequeos de completitud en `PreToolUse[Agent]`.**
`completeness-check.sh` (se autodescribe «Compatibility entrypoint for level-5 completeness gating»), `predev-completeness-check.sh` (escribe `predev-completeness.jsonl`), `completeness-check-llm.sh` (ADR-022, pide a Haiku). Los tres registrados, mismo evento, mismo matcher.

**c) Tres lectores del Trust Report en `PostToolUse[Agent]`.**
`claim-validator.sh`, `trust-score-validator.sh` y `confidence-gate.sh` parsean la misma respuesta del agente para tres veredictos distintos (alucinación, estructura, score). Cada uno reimplementa su extracción de stdin.

**d) Cuatro validadores de finalización superpuestos.**
`completion-gate.sh`, `post-agent-verify.sh`, `adversarial-review-gate.sh` y `decision-depth-gate.sh`, los cuatro en `PostToolUse[Agent]`. El YAML documenta que `completion-gate.sh` ya superseded a `auto-refine`/`auto-verify`/`dod-gate` («to avoid duplicate Agent PostToolUse work») — esa consolidación se hizo, pero quedaron estos cuatro.

**e) Cinco heartbeats.**
`session-heartbeat.sh`, `native-agent-heartbeat.sh`, `state-heartbeat.sh`, más los symlinks `reaper-heartbeat.sh` → `reaper-daemon-launcher.sh` y `cos-executor-heartbeat.sh` → `cos-executor-daemon-launcher.sh`.

**f) Seis hooks registrados más de una vez.**

```
cross-session-event-emit.sh   x4  ->  PreToolUse[Edit|Write], PreToolUse[Agent], PostToolUse[Bash], Stop[]
audit-id-enricher.sh          x2  ->  PostToolUse[Bash], PostToolUse[Agent]
control-plane-audit.sh        x2  ->  PreToolUse[Edit|Write], PreToolUse[Agent]
native-agent-heartbeat.sh     x2  ->  PreToolUse[Agent], PostToolUse[Agent]
session-heartbeat.sh          x2  ->  UserPromptSubmit[], PreToolUse[]
work-queue-sync.sh            x2  ->  PostToolUse[TodoWrite], PostToolUse[Agent]
```

`session-heartbeat` en `PreToolUse` con matcher vacío significa que corre en **toda** llamada a herramienta: 468 invocaciones, la más frecuente de todo el corpus.

<details><summary><code>scratchpad/duplicacion.sh</code></summary>

```bash
#!/usr/bin/env bash
# Para cada hook candidato: proposito declarado y JSONL que escribe.
cd "$(git rev-parse --show-toplevel)"
for h in "$@"; do
  f="hooks/$h.sh"; [ -e "$f" ] || { echo "== $h : NO EXISTE"; continue; }
  echo "== $h"
  sed -n '2,5p' "$f" | sed 's/^/     /' | grep -v '^     *$' | head -3
  echo "     metrics: $(grep -ohE '[a-z0-9-]+\.jsonl' "$f" | sort -u | tr '\n' ' ')"
done
```

Y el detector de registros repetidos:

```bash
python3 -c "
import json,re,collections
d=json.load(open('.claude/settings.json'))
c=collections.defaultdict(list)
for ev,arr in d['hooks'].items():
    for m in arr:
        for hk in m['hooks']:
            n=re.findall(r'hooks/([A-Za-z0-9_.-]+\.(?:sh|py))',hk.get('command',''))
            if n: c[n[0]].append(f\"{ev}[{m.get('matcher','')}]\")
for k,v in sorted(c.items()):
    if len(v)>1: print(f'  {k:44s} x{len(v)}  ->  {\", \".join(v)}')
"
```
</details>

---

## 8. Fuera de mi porción

Para los otros jueces, sin actuar sobre nada de esto:

- **(cos_lib+scripts)** `docs/04-Concepts/root/safety-mesh.md` cita las capas 12 y 14 como `lib/cross_verifier.py` y `lib/memory_scanner.py`. Esos paths no existen; los archivos están en `cos_lib/`. El commit `0bbd3b3db` («point the always-loaded corpus at cos_lib») sugiere que la migración `lib/` → `cos_lib/` dejó referencias colgadas en más lugares.
- **(cos_lib+scripts)** `scripts/claim_enforcer.py` está sano: detecta, clasifica y devuelve `status: block` correctamente. El bug es del hook que lo consume. Vale la pena que quien audite `scripts/` no lo dé por roto.
- **(tests+CI+telemetría)** `hook-timing.jsonl` registra `exit_code: 141` (SIGPIPE) en 18 filas. Cualquier consumidor que cuente «no-cero = falla» o «distinto de 2 = ok» va a clasificarlas mal. Vale revisar si algún dashboard las cuenta como éxito.
- **(tests+CI+telemetría)** El patrón `jq -r '.campo // true'` sobre un booleano es un bug genérico. Acá aparece sólo en `claim-validator`, pero es candidato natural a regla de lint sobre todos los `.sh` del repo.
- **(instalador+packages)** 40 de los 255 hooks son symlinks a `packages/*/hooks/`. `hooks/_lib/` viaja entero por un `copytree` sin filtro, incluyendo `registration-allowlist.txt` y los `.py`. No evalué qué pasa con los symlinks en el copiado del instalador — si `copytree` no usa `symlinks=True`, se duplican por valor.
- **(skills+rules)** `rules/rate-limiting.md` ya documenta con honestidad que el hook no está registrado. Mi medición lo confirma: `rate-limiter` tiene 0 disparos. Ese archivo es el modelo de cómo debería documentarse el resto del mesh.
- **Concurrencia:** durante la auditoría HEAD se movió de `fe888ab7f` a `0bbd3b3db` por una sesión concurrente. Un `M docs/08-References/business/master-plan-checklist.md` que estaba staged al inicio desapareció por ese commit ajeno, no por mí.

---

## 9. Correcciones a las premisas del encargo

1. **«no hay matcher para `Monitor`, `Task`, `WebFetch`, `WebSearch` ni el resto de MCP» — parcialmente falso.** Hay 11 hooks en bloques `matcher: ""`, que en Claude Code matchean toda herramienta. Lo correcto: no hay ningún hook *específico* para esas superficies; sólo los alcanzan 11 genéricos, mayormente de telemetría. `WebFetch`/`WebSearch` sí quedan sin ningún control de contenido.

2. **«una instalación fresca tiene 36 registraciones, no 47» — no lo pude reproducir.** Ningún perfil del driver da 36: core=137, team=141, maintainer=162, lab=162, full=193. Lo más cercano a esa magnitud es el conteo de `scope: both` en el YAML (51 entradas, 49 sin flags de exclusión), que sería lo que recibe un proyecto consumidor. Si el 36 salió de un install real, salió de un camino que no es este driver, y conviene rastrear cuál — porque el encargo dice que este driver es «the single path».

3. **«`phase: reconstruction` hace inalcanzable el `exit 2` de `claim-validator`» — falso en el mecanismo.** `claim-validator` tiene un `exit 2` (línea 86, ADR-244) que corre *antes* de que `PHASE` se defina (línea 92) y no depende de la fase. La conclusión igual se sostiene, pero por otra causa: lo mata el `jq -r '.ok // true'` de la línea 77. Para `confidence-gate` y `scope-proportionality` la premisa es correcta tal como está escrita.

4. **«0 hooks que hayan bloqueado nunca» — correcto para el mesh, falso para la capa.** Las 9 capas registradas del mesh tienen 0 `exit 2`. Pero 4 hooks *fuera* del mesh sí bloquearon, 19 veces: `subagent-budget-enforcer` (12), `bash-hot-path-dispatcher` (3), `provenance-scan` (3), `protected-config-write-guard` (1). `subagent-budget-enforcer` me bloqueó a mí durante esta auditoría, a los 51 tool calls. La capa bloquea; lo que no bloquea es el mesh anunciado.

5. **«29 `exit 2` en 30.515 invocaciones» — distinto corpus.** El `hook-timing.jsonl` vigente tiene 10.673 filas y 19 `exit 2`. La proporción es del mismo orden (0,18% vs 0,10%). No contradigo el número del encargo; señalo que el archivo rotó.

6. **«300 archivos trackeados» — correcto, pero no son 300 hooks.** Son 255 hooks únicos ejecutables una vez descontados `_lib/` (38 librerías), `_archived/` (3 `.bak`), 2 `.disabled` y 1 `.txt`. Los 42 symlinks casi no dedupen porque 40 apuntan fuera de `hooks/`, a `packages/`.

7. **«14 capas declaradas» — son 12 hooks + 2 librerías Python.** Y el propio doc admite en su sección `Status / caveats` que su numeración es inconsistente. Además dice que la registración se hace en `.claude/settings.local.json`; se hace en `.claude/settings.json`, que es generado.

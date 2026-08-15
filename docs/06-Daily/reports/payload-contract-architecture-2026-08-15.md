# Contrato de payload del harness — dónde está el campo, cuánto cuesta leerlo mal, y el control que falta

Fecha: 2026-08-15
Alcance: `hooks/error-pipeline.sh`, `hooks/error-learning.sh`, la cadena
`PostToolUse:Bash` completa, y la familia de lecturas ciegas sobre el payload.
Evidencia ejecutable: `scripts/audit_payload_field_contracts.py` (read-only,
determinista, no toca estado).

```bash
python3 scripts/audit_payload_field_contracts.py             # lint de defaults ciegos
python3 scripts/audit_payload_field_contracts.py --canary    # + campos que ningún payload real trajo
python3 scripts/audit_payload_field_contracts.py --json --all # filas completas
```

Exit codes: 0 = sin hallazgos, 1 = hallazgos, 2 = error.

---

## 0. Qué del encargo era falso

El encargo venía con cinco premisas numéricas y **tres no reproducen**. Dos de
ellas cambian el diseño, no solo la cifra.

### 0.1 Las corridas: el encargo infla 2x, y el lote 34 también

| Fuente | `error-pipeline` | `error-learning` | Suma |
|---|---:|---:|---:|
| Encargo (repitiendo al lote 34) | 10.497 | 10.549 | 21.046 |
| **Medido** | **5.335** | **5.335** | **10.670** |

```bash
{ gzcat .cognitive-os/metrics/.archive/hook-timing-*.jsonl.gz; \
  cat .cognitive-os/metrics/hook-timing.jsonl; } \
 | grep -c '"hook":"error-pipeline"'
```

Los dos hooks tienen **exactamente el mismo conteo**, que es lo esperable: están
registrados en el mismo `matcher=Bash`, uno al lado del otro, y disparan juntos.
El lote 34 los dio distintos (10.497 vs 10.549), lo que ya era señal de que el
conteo estaba sumando algo que no era el hook. Sospecha: doble conteo del
archivo `hook-timing-20260815-022842.jsonl.gz` contra la porción viva, que se
solapan en el tiempo.

La cifra viva sube mientras uno mide (`5.335` al momento de escribir, `1.306` de
ellas en el archivo vivo). El número correcto de citar es el orden de magnitud:
**~5.300 corridas cada uno, ~10.700 entre los dos**, no 21.000.

### 0.2 «Disparan en PostToolUse sobre todo» — falso

```bash
jq -r '.hooks.PostToolUse[]? | "\(.matcher // "*") -> " + ([.hooks[].command]|join(";"))' \
  .claude/settings.json | grep error-
```

Los dos están bajo `matcher=Bash`. No se ejecutan en `Read`, `Write`, `Edit`,
`Agent` ni MCP. El desperdicio es real pero está acotado a la herramienta que sí
les interesa. La premisa «el 99% de las llamadas son ruido por diseño» hay que
reformularla, y la respuesta cambia (§2).

### 0.3 El hallazgo que rompe el parche propuesto: **el campo no existe en ningún lado**

Ésta es la refutación importante. El encargo dice: *«el harness lo manda bajo
`tool_response`, está documentado en el propio repo»*, y el parche del lote 34
propone mover la lectura a `.tool_response.exit_code`.

**No hay `exit_code` en el payload. Ni arriba, ni bajo `tool_response`, ni con
ninguna grafía.** Verificado contra payloads reales, no contra documentación:

```bash
# 2.680 resultados de herramienta reales, de 57 transcripts del harness
cat "$(python3 - <<'EOF'
import pathlib,sys
b=pathlib.Path.home()/".claude/projects"
print(max(b.glob("*luum-agent-os"),key=lambda p:p.stat().st_mtime))
EOF
)"/*.jsonl | jq -r 'select(.toolUseResult|type=="object") | .toolUseResult | keys[]' \
 | sort | uniq -c | sort -rn | head
```

```
1829 stdout
1829 stderr
1829 noOutputExpected
1829 isImage
1829 interrupted
...
```

Cero `exit_code`. Cero `exitCode`. En 1.829 resultados de Bash.

**Cómo señala el fracaso este harness, de verdad:** por **cambio de tipo**, no
por campo.

| Resultado | `tool_response` |
|---|---|
| Éxito | objeto `{stdout, stderr, interrupted, isImage, noOutputExpected}` |
| Fracaso | **string**, prefijada `Error: ...` — el caso común es `Error: Exit code N\n<stderr>` |

```bash
cat <transcripts>/*.jsonl | jq -r 'select(.toolUseResult|type=="string") | .toolUseResult' \
 | grep -oE '^Error: Exit code [0-9]+' | sort | uniq -c
#  38 Error: Exit code 1
#   7 Error: Exit code 143
#   3 Error: Exit code 127
#   1 Error: Exit code 129
#   1 Error: Exit code 128
```

Consecuencia directa: **el parche del lote 34 no arregla nada**. Cambia
`.exit_code // "0"` por `.tool_response.exit_code // "0"`, y `.tool_response.exit_code`
tampoco existe. El default `"0"` sigue ganando siempre, los dos hooks siguen
saliendo temprano, y los 12 characterization tests que fijan el defecto seguirían
pasando o fallando por el motivo equivocado. Es el verde barato de la familia
diagnóstico: mover la lectura a otro campo inexistente **parece** un arreglo y
deja el sistema exactamente igual, ahora con la sensación de estar cerrado.

No es un caso aislado: el canario encuentra **otros seis** consumidores apoyados
en el mismo campo fantasma (§4.2), incluido `hooks/tool-sequence-capture.sh:62`,
que es el hook del que sale el campo `success` de la telemetría.

### 0.4 El archivo se llama distinto, y los consumidores son diez, no cinco

El encargo habla de «un `error-events.jsonl` de 11 filas» leído por cinco
consumidores. **`error-events.jsonl` no existe en el repo** (`find . -name
'error-events.jsonl'` → 0). El archivo real es
`.cognitive-os/metrics/error-learning.jsonl`, y sí tiene 11 filas.

```bash
grep -rln 'error-learning.jsonl' bin/ cos_lib/ lib/ scripts/ | wc -l   # → 10
```

Diez consumidores, no cinco: `bin/cos-errors`, `cos_lib/error_insights.py`,
`feedback_consumer.py`, `singularity.py`, `learning_pipeline.py`,
`self_improvement.py`, `consumer_improvement_proposals.py`,
`evolve_task_queue.py`, `kpi_collector.py`, `governed_self_improvement.py`.
El encargo subestima el blast radius del arreglo: cuando el hook empiece a
escribir de verdad, diez lectores van a empezar a ver datos por primera vez —
incluidos tres del lazo de auto-mejora. Eso refuerza el ítem 2 de §6 (los
characterization tests) y agrega una pregunta que este informe no responde:
**¿esos diez consumidores están listos para un archivo que crece?**

### 0.5 «El código fue correcto alguna vez» — no hay evidencia de eso

Los 57 transcripts cubren desde el más viejo disponible hasta hoy y ninguno trae
`exit_code`. Si alguna versión del harness lo mandó, fue antes de la ventana de
telemetría que queda. Lo que sí se puede afirmar: **la forma de la lectura fue
incorrecta desde que hay evidencia**, y sobrevivió porque un default permisivo no
tiene forma de quejarse.

### 0.5 Reproducción viva del defecto, en dos comandos

```bash
grep -c '"hook":"error-pipeline"' .cognitive-os/metrics/hook-timing.jsonl   # → 1365
ls /nonexistent-path-canary-XYZ                                            # exit 1, real
grep -c '"hook":"error-pipeline"' .cognitive-os/metrics/hook-timing.jsonl   # → 1366
wc -l .cognitive-os/metrics/error-learning.jsonl                           # → 11 (sin cambio)
```

El hook **sí corre** ante un fallo real (1365 → 1366) y **no produce nada**.
Queda descartada la hipótesis alternativa «el harness no dispara PostToolUse
cuando la herramienta falla».

---

## 1. Dónde está el campo, de verdad

No hay campo. Hay un **tipo**. La lectura correcta es ternaria y no tiene default:

| Estado | Cómo se reconoce | Qué debe hacer el hook |
|---|---|---|
| `ok` | `tool_response` es objeto sin `is_error` | salir |
| `failed` | `tool_response` es string con prefijo `Error:` | trabajar |
| `absent` | `tool_response` es `null` o de tipo inesperado | **salir Y registrar drift** |

El tercer estado es el control. Hoy `absent` y `ok` son el mismo camino de
código, y ésa es la razón por la que el defecto duró: el hook no tiene forma de
gritar «no entendí el payload».

---

## 2. ¿Deberían correr 5.335 veces? — la tasa de fallo real

Clasificando los 2.004 payloads con forma de Bash con el clasificador propuesto:

```bash
cat <transcripts>/*.jsonl \
 | jq -c 'select(.toolUseResult != null)
          | select((.toolUseResult|type=="string")
                   or ((.toolUseResult|type=="object") and (.toolUseResult|has("stdout"))))
          | {tool_response: .toolUseResult}' \
 | jq -r -f probe.jq | awk '{print $1}' | sort | uniq -c
#  170 failed
# 1834 ok
```

**Tasa de fallo de Bash: 170 / 2.004 = 8,5 %.** Sobre el total de herramientas,
170 / 2.680 = 6,3 %.

Y un matiz que cambia la lectura: de las 170, **97 no son fallos de shell** —
son bloqueos de gates `PreToolUse` del propio SO (`Error: PreToolUse:Bash hook
error: ...`). Sólo **50** son `Error: Exit code N` genuinos. Los otros 23 son
permisos, conflictos y errores de archivo.

```bash
cat <transcripts>/*.jsonl | jq -r 'select(.toolUseResult|type=="string") | .toolUseResult[0:12]' \
 | sort | uniq -c | sort -rn
#  97 Error: PreTo
#  50 Error: Exit
#   4 Error: Permi   4 Error: claud   3 Error: File ...
```

### Qué implica para el costo

El encargo tiene razón en la dirección: **arreglar el campo vuelve caras
invocaciones que hoy son gratis**. Pero la magnitud es al revés de lo que
sugiere. Lo caro no es el 8,5% que va a trabajar: es el **91,5% que ya está
pagando y no trabaja**.

```bash
{ gzcat .cognitive-os/metrics/.archive/hook-timing-*.jsonl.gz; \
  cat .cognitive-os/metrics/hook-timing.jsonl; } \
 | jq -r 'select(.hook|IN("error-pipeline","error-learning")) | .duration_ms // 0' \
 | awk '{n++; s+=$1} END {printf "n=%d total_ms=%d = %.1f min, mean=%.0f ms\n", n,s,s/60000,s/n}'
# n=10670 total_ms=2998431 = 50.0 min, mean=281 ms
```

**50 minutos de reloj de pared, en el camino crítico de cada llamada a Bash, para
producir 11 filas.** El costo marginal del arreglo es el trabajo real sobre 8,5%
de ~5.300 llamadas ≈ 450 clasificaciones. Eso es exactamente lo que los hooks
existen para hacer. El desperdicio no está ahí.

**Veredicto sobre la pregunta 2:** sí corresponde recortar, pero no por la razón
del encargo, y no se puede hacer con el `matcher`: el harness matchea por
**nombre de herramienta**, no por resultado, así que no existe un
`matcher="Bash:failed"`. El recorte tiene que ser una salida temprana barata —
y hoy esa salida temprana cuesta 281 ms porque cada hook arranca su propio
proceso y su propio parseo. De ahí la pregunta 3.

---

## 3. ¿Un solo lector que despache? — sí, y no es reinvención

La cadena `PostToolUse:Bash` tiene **siete** hooks registrados. Cada uno arranca
un `bash`, sourcea sus librerías, hace su propio `cat` de stdin y sus propios
`jq`:

| Hook | corridas | total ms | media | `jq` en el fuente |
|---|---:|---:|---:|---:|
| `rate-limit-drain` | 5.335 | 2.447.983 | 459 | 1 |
| `post-git-orphan-notifier` | 5.335 | 1.903.241 | 357 | 6 |
| `result-truncator` | 5.335 | 1.791.331 | 336 | 13 |
| `cross-session-event-emit` | 5.335 | 1.638.791 | 307 | 0 |
| `audit-id-enricher` | 5.497 | 1.589.152 | 289 | 1 |
| `error-learning` | 5.335 | 1.547.399 | 290 | 5 |
| `error-pipeline` | 5.335 | 1.451.032 | 272 | 22 |
| **CADENA** | | **12.368.929** | | **48** |

**206,1 minutos de reloj de pared**, serializados delante del agente.

```bash
{ gzcat .cognitive-os/metrics/.archive/hook-timing-*.jsonl.gz; cat .cognitive-os/metrics/hook-timing.jsonl; } \
 | jq -r 'select(.event=="PostToolUse") | select(.hook|IN("error-pipeline","result-truncator","rate-limit-drain","audit-id-enricher","error-learning","post-git-orphan-notifier","cross-session-event-emit")) | "\(.hook) \(.duration_ms // 0)"' \
 | awk '{n[$1]++; s[$1]+=$2} END {t=0; for (h in n){printf "%-26s n=%-6d total_ms=%-9d mean=%.0f\n",h,n[h],s[h],s[h]/n[h]; t+=s[h]} printf "CHAIN TOTAL total_ms=%d = %.1f min\n",t,t/60000}'
```

El patrón ya existe y está vivo, **pero sólo del lado Pre**:

```bash
jq -r '.hooks | to_entries[] | .key as $e | .value[] | .hooks[].command
       | select(test("bash-hot-path")) | "\($e)"' .claude/settings.json
# PreToolUse
```

`hooks/bash-hot-path-dispatcher.sh` lee stdin una vez y reparte a los gates hijos
(`printf '%s' "$INPUT" | bash "$path"`, línea 46). **`PostToolUse:Bash` no tiene
contraparte.** Construirla no es reinventar: es aplicar el patrón que el repo ya
eligió, al lado que quedó sin él.

### Propuesta acotada

Un `post-bash-dispatcher.sh` que:

1. lee stdin **una vez**;
2. hace **un** `jq` que emite el bloque completo — `command`, `status`,
   `exit_code`, `stdout`, `stderr`, `tool_use_id` — y lo exporta como env;
3. **corta la rama de fallo** (`status=ok` → los hooks que sólo miran fallos
   nunca se invocan);
4. despacha el resto igual que el dispatcher Pre.

Ahorro estimado, sólo por eliminar las invocaciones de los dos hooks de error
sobre llamadas exitosas: 91,5% × 10.670 × 281 ms ≈ **45,7 minutos**. El resto de
la cadena entra en la misma cuenta si se migra.

**Recomendación de priorización, honesta:** esto es P2, no P1. El dispatcher Post
toca `.claude/settings.json` y siete hooks a la vez — blast radius alto, y hay
otro agente trabajando sobre `bash-hot-path-dispatcher.sh` en esta misma sesión.
El parche de §5 es P1 y es independiente: arregla la corrección sin tocar la
arquitectura. El dispatcher es la optimización que viene después, con su propio
ADR.

---

## 4. Cuántos hooks más tienen la misma forma — y el control que falta

### 4.1 El lint estático

`scripts/audit_payload_field_contracts.py` clasifica **cada** lectura de un campo
que el **harness** posee (`tool_name`, `tool_input`, `tool_response`, `exit_code`,
`session_id`, …). Deja fuera a propósito las lecturas sobre archivos que el propio
SO escribe: ahí el SO controla las dos puntas y puede cambiarlas juntas.

Clasificación del default:

- **INERT** — `""`, `empty`, `null`. El consumidor está obligado a ramificar sobre
  vacío. Seguro.
- **GUARDED** — un literal permisivo sobre un campo que no es un veredicto
  (`.tool_name // "unknown"`). Degrada la etiqueta, no la decisión.
- **BLIND** — un literal que **es** una lectura legal, sobre un campo cuyo valor
  **es un veredicto** (`exit_code`, `is_error`, `ok`, `status`, `blocked`,
  `success`, `failed`, `passed`, `valid`, `allowed`, `triggered`, `result`).
  Ausencia y veredicto comparten camino: el hook no puede distinguirlos.

```
$ python3 scripts/audit_payload_field_contracts.py
payload reads scanned: 216
  BLIND    3
  GUARDED  66
  INERT    147

BLIND — default is itself a legal reading; absence is unobservable
  hooks/error-learning.sh:18                        .exit_code // '0'
  hooks/error-pipeline.sh:39                        .exit_code // '0'
  packages/skill-governance/hooks/skill-tracker.sh:34  .exit_code // '0'
```

**Tres, no muchos** — y el tercero es un hallazgo nuevo que el lote 34 no vio:
`skill-tracker.sh` (registrado en `matcher=Agent`) arrastra el mismo
`.exit_code // "0"` y por lo tanto tiene el mismo defecto exacto. Está
symlinkeado desde `hooks/skill-tracker.sh` → `packages/skill-governance/hooks/`.

Que sean tres y no cincuenta **no debilita el argumento, lo cambia**: no hace
falta una campaña de remediación, hace falta que el número quede clavado en cero
y que algo se ponga rojo cuando suba. Los 66 GUARDED son deuda aceptable con
motivo escrito (una etiqueta `"unknown"` en telemetría no toma decisiones); los
147 INERT son la forma correcta y son la mayoría, o sea que la convención del
repo ya es buena y estos tres son la excepción.

### 4.2 El canario — el control que faltaba

El lint no alcanza: una lectura puede tener default inerte y **aun así** apuntar a
un campo que el harness ya no manda. Eso no es un bug de forma, es **drift de
contrato**, y sólo se detecta contra payloads reales.

El harness ya guarda todos sus payloads: el `toolUseResult` de cada transcript es
el mismo objeto que llega a los hooks como `tool_response`. Es una captura que el
SO no tuvo que instrumentar.

```
$ python3 scripts/audit_payload_field_contracts.py --canary
canary: 2680 real payloads scanned
FIELDS HOOKS DEPEND ON THAT NO PAYLOAD EVER CARRIED:
  hooks/auto-refine.sh:84                              .tool_response.error
  hooks/error-learning.sh:18                           .exit_code
  hooks/error-pipeline.sh:39                           .exit_code
  hooks/post-git-orphan-notifier.sh:102                 .tool_response.exit_code
  hooks/skill-usage-tracker.sh:64                      .tool_response.duration_ms
  hooks/tool-sequence-capture.sh:62                    .tool_response.exit_code
  packages/quality-gates/hooks/completion-gate.sh:442  .tool_response.error
  packages/skill-governance/hooks/skill-tracker.sh:34  .exit_code
  packages/skill-governance/hooks/skill-tracker.sh:108 .tool_response.model
```

**Nueve dependencias sobre campos que ningún payload real trajo nunca.** Dos de
ellas son `.tool_response.exit_code` — el destino del parche propuesto por el
lote 34. El canario lo habría atajado antes de escribirlo.

Ésta es la respuesta a la pregunta 4: no un esquema declarado a mano (que se
desactualiza con el harness y hay que mantener), sino un **diff contra lo que el
harness efectivamente mandó**. Se pone rojo solo cuando el harness mueve un
campo, sin que nadie tenga que acordarse de actualizar nada.

### 4.3 Los tres controles, en orden de costo

1. **Lint (`BLIND` = 0)** — barato, corre sin telemetría, se puede clavar en CI
   hoy con `exit 1`. Impide que vuelva a nacer un default permisivo sobre un
   veredicto.
2. **Canario (`--canary`)** — detecta drift del harness. *Actualizado
   2026-08-15: ya corre en la suite.* La premisa de que "necesita transcripts,
   así que no puede ir a CI" resultó falsa: lo que el canario consume son claves
   y tipos, no valores, y eso se congela. `scripts/capture_payload_corpus.py`
   captura un corpus redactado a `tests/fixtures/payload-corpus/` (52 registros,
   uno por tool × estado × forma) y el canario lo usa como fuente por defecto.
   Sobre ese corpus da el mismo veredicto que sobre 2686 payloads vivos: 9
   dependencias fantasma, ratcheteadas en
   `tests/audit/test_payload_field_contracts.py`. El modo vivo sigue existiendo
   como `--canary --live`, que es lo único que contesta "¿el harness cambió
   desde que capturamos?".
3. **Tercer estado en el código** — el arreglo estructural: `ok` / `failed` /
   `absent`, donde `absent` emite una fila de drift en vez de comportarse como
   `ok`. Es lo que `dispatch-gate.sh:116` ya hizo para su propio caso, agregando
   `cb_evaluated` y `cb_unavailable` junto a `cb_blocked` — o sea que el repo ya
   descubrió este patrón una vez y no lo generalizó. **Esa generalización es el
   entregable de más valor de este informe.**

**Regla propuesta, para `rules/`:** *un hook nunca lee un campo del payload del
harness con un default que sea una lectura legal de ese campo. Si el campo puede
faltar, el consumidor tiene tres estados y el tercero se registra.*

---

## 5. El parche exacto, listo para aplicar

**No se pudo aplicar:** `hooks/` está protegido por `protected-config-write-guard`
y `COS_ALLOW_PROTECTED_CONFIG_WRITE=1` no es alcanzable desde el proceso del
agente (el guard corre antes del comando). No se intentó bypassear. El parche va
escrito para revisión humana.

Reemplaza el parche del lote 34, que apunta a `.tool_response.exit_code` — un
campo que no existe (§0.3).

### 5.1 `hooks/error-pipeline.sh` — líneas 37-42

```diff
 INPUT=$(cat)
 COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
 RESPONSE=$(echo "$INPUT" | jq -r '.tool_response // empty' 2>/dev/null)
-EXIT_CODE=$(echo "$INPUT" | jq -r '.exit_code // "0"' 2>/dev/null)
-
-[ -z "$COMMAND" ] && exit 0
-[ "$EXIT_CODE" = "0" ] && exit 0
+
+# El harness NO manda exit_code — ni arriba ni bajo tool_response (verificado
+# contra 1.829 resultados de Bash reales; ver el informe
+# payload-contract-architecture-2026-08-15.md §0.3). El fracaso se señala por
+# CAMBIO DE TIPO: tool_response es objeto cuando la herramienta salió bien y
+# string prefijada "Error:" cuando falló, normalmente "Error: Exit code N".
+# Tres estados, no dos: 'absent' NO se comporta como 'ok'.
+_STATUS_PAIR=$(echo "$INPUT" | jq -r '
+  if   (.tool_response | type) == "string" then
+         (if   (.tool_response | test("^Error: Exit code [0-9]+"))
+          then "failed " + (.tool_response | capture("^Error: Exit code (?<c>[0-9]+)") | .c)
+          elif (.tool_response | startswith("Error:")) then "failed 1"
+          else "ok 0" end)
+  elif (.tool_response | type) == "object" then
+         (if (.tool_response.is_error == true) then "failed 1" else "ok 0" end)
+  elif (.tool_response == null) then "absent -1"
+  else "absent -1" end' 2>/dev/null)
+TOOL_STATUS="${_STATUS_PAIR%% *}"
+EXIT_CODE="${_STATUS_PAIR##* }"
+
+[ -z "$COMMAND" ] && exit 0
+
+# Contrato roto: el harness cambió la forma del payload. Registrar y salir —
+# jamás confundirlo con éxito.
+if [ "$TOOL_STATUS" = "absent" ] || [ -z "$TOOL_STATUS" ]; then
+  safe_jsonl_append "$METRICS_DIR/payload-contract-drift.jsonl" \
+    "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"hook\":\"error-pipeline\",\"reason\":\"tool_response of unexpected shape\"}"
+  exit 0
+fi
+
+[ "$TOOL_STATUS" = "ok" ] && exit 0
```

### 5.2 `hooks/error-learning.sh` — líneas 18-27

```diff
-EXIT_CODE=$(stdin_field '.exit_code' '0')
 COMMAND=$(stdin_field '.tool_input.command' '')
+
+# Ver error-pipeline.sh: el harness no manda exit_code. Estado ternario.
+_STATUS_PAIR=$(echo "$_STDIN_JSON" | jq -r '
+  if   (.tool_response | type) == "string" then
+         (if   (.tool_response | test("^Error: Exit code [0-9]+"))
+          then "failed " + (.tool_response | capture("^Error: Exit code (?<c>[0-9]+)") | .c)
+          elif (.tool_response | startswith("Error:")) then "failed 1"
+          else "ok 0" end)
+  elif (.tool_response | type) == "object" then
+         (if (.tool_response.is_error == true) then "failed 1" else "ok 0" end)
+  elif (.tool_response == null) then "absent -1"
+  else "absent -1" end' 2>/dev/null)
+TOOL_STATUS="${_STATUS_PAIR%% *}"
+EXIT_CODE="${_STATUS_PAIR##* }"
+
 # tool_response may be a plain string (stdout) or an object with stdout/stderr fields.
-# Use direct jq with type-checking to handle both formats.
-STDOUT=$(echo "$_STDIN_JSON" | jq -r 'if (.tool_response | type) == "object" then .tool_response.stdout // "" else .tool_response // "" end' 2>/dev/null || true)
+STDOUT=$(echo "$_STDIN_JSON" | jq -r 'if (.tool_response | type) == "object" then .tool_response.stdout // "" else .tool_response // "" end' 2>/dev/null || true)
 STDERR=$(echo "$_STDIN_JSON" | jq -r 'if (.tool_response | type) == "object" then .tool_response.stderr // "" else "" end' 2>/dev/null || true)
 
-# Only process failures
-[ "$EXIT_CODE" = "0" ] || [ "$EXIT_CODE" = "" ] && exit 0
-[ "$EXIT_CODE" = "null" ] && exit 0
+# Only process failures. 'absent' NO es 'ok': se registra como drift de contrato.
+[ "$TOOL_STATUS" = "absent" ] && { \
+  safe_jsonl_append "$(_resolve_metrics_dir)/payload-contract-drift.jsonl" \
+    "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"hook\":\"error-learning\",\"reason\":\"tool_response of unexpected shape\"}"; \
+  exit 0; }
+[ "$TOOL_STATUS" != "failed" ] && exit 0
```

Nota adicional sobre `error-learning.sh:26`: `[ A ] || [ B ] && exit 0` funciona
por asociatividad izquierda, pero es una forma frágil que sólo hace lo que se
espera por accidente. El parche la elimina.

### 5.3 `packages/skill-governance/hooks/skill-tracker.sh:34` — mismo defecto

Fuera del alcance de los characterization tests del lote 34, pero es el mismo
`.exit_code // "0"` sobre `matcher=Agent`. Los payloads de `Agent` tienen su
propia forma (`{agentId, status, prompt, resolvedModel, ...}`) y traen un campo
`status` real, así que la lectura correcta ahí es `.tool_response.status`, no
la copia del clasificador de Bash. **Requiere su propia medición antes de
parchear** — no se incluye diff a ciegas.

### 5.4 Validación del clasificador propuesto

El clasificador se reprodujo contra los 2.004 payloads reales con forma de Bash
antes de proponerlo:

```
170 failed
1834 ok
0   absent
```

Cero `absent` sobre payloads históricos: el clasificador cubre la forma actual
completa, y el estado `absent` queda reservado para el día que el harness cambie
— que es exactamente para lo que existe.

---

## 6. Qué queda abierto

| # | Ítem | Prioridad | Fundamento |
|---|---|---|---|
| 1 | Aplicar §5.1 y §5.2 (requiere revisión humana por `protected-config-write-guard`) | P1 | pedido explícito del operador; el parche del lote 34 no sirve |
| 2 | Reescribir los 12 characterization tests de `tests/audit/test_instrument_productivity.py` | P1 | fijan el defecto contra `.exit_code`, campo que no existe; van a pasar a verde por el motivo equivocado |
| 3 | Clavar `audit_payload_field_contracts.py` (lint) en CI con `exit 1` | P1 | control barato, BLIND ya está en 3 y son remediables |
| 4 | ~~Sumar `--canary` a `session-wrapup`~~ — **hecho 2026-08-15, por otra vía**: corre en la suite contra un corpus de fixtures redactado (`tests/fixtures/payload-corpus/`), con ratchet en 9 dependencias fantasma | P2 | la premisa de que sólo podía correr sobre transcripts vivos era falsa: el canario consume claves y tipos, no valores, y eso se congela |
| 5 | `post-bash-dispatcher.sh` para `PostToolUse:Bash` | P2 | 206 min de cadena; blast radius alto, merece ADR propio |
| 6 | Medir y parchear `skill-tracker.sh` sobre payloads de `Agent` | P2 | mismo defecto, distinta forma de payload |
| 7 | Regla en `rules/` sobre defaults permisivos en campos de veredicto | P2 | generaliza lo que `dispatch-gate` ya descubrió y no propagó |

Los ítems 1, 2 y 3 salen del pedido explícito del operador en el encargo. Los 4-7
son recomendaciones sin señal previa del operador: van marcadas para triage, no
para auto-acción.

# El presupuesto de sub-agente vuelve en cero al reanudar

**Fecha:** 2026-08-20
**HEAD al empezar:** `0dd2cdfc9`
**Alcance:** `hooks/subagent-budget-enforcer.sh`, su contador en disco, y el contrato de tests.
**Estado:** diagnóstico cerrado con medición. Gate nuevo aplicado en `tests/`.
**Parche del hook probado pero NO aplicado** — `hooks/**` es superficie protegida:
revisión humana pendiente, no un bypass a activar.

---

## 1. Veredicto en una línea

El contador es acumulativo por invocación de sub-agente, vive en un archivo suelto y
**ninguna reanudación lo resetea**: el agente cortado en 51/50 vuelve con presupuesto
**cero**, no con poco. Peor: **cada bloqueo cobra presupuesto**, así que cada reintento lo
hunde más. La premisa del encargo es correcta y el mecanismo es peor de lo que decía.

---

## 2. Correcciones a las premisas del encargo

| # | Premisa | Veredicto | Evidencia |
|---|---|---|---|
| 1 | HEAD `0dd2cdfc9` | **Cierto** | `git rev-parse --short HEAD` → `0dd2cdfc9` |
| 2 | Existe `subagent-budget-enforcer` que corta sub-agentes | **Cierto en el nombre, falso en «corta»** | §2.1 |
| 3 | El límite es 50 tool-calls | **Cierto**, `COS_SUBAGENT_TOOL_CALL_BUDGET:-50` | §3 |
| 4 | «Reanudarlo con un mensaje NO lo resetea» | **Cierto y medido** | §3, §4 |
| 5 | «Gastó DOS llamadas re-confirmando y volvió a chocar en 52/50» | **Fue UNA, no dos** | §2.2 |
| 6 | «La única salida fue lanzar un agente nuevo» | **Cierto, y es el patrón dominante, no la anécdota** | §4 |
| 7 | Implícita: el diseño de la salida está por hacerse | **Falso en parte**: parte ya estaba escrita y sin aplicar desde el 2026-08-15 | §2.3 |

### 2.1 «Corta» es inexacto: el hook es PostToolUse, el `exit 2` llega tarde

```bash
python3 -c "
import json
s=json.load(open('.claude/settings.json'))
for ev,arr in s.get('hooks',{}).items():
    for grp in arr:
        for h in grp.get('hooks',[]):
            if 'subagent-budget-enforcer' in h.get('command',''):
                print(ev,'| matcher=',repr(grp.get('matcher')))
"
# PostToolUse | matcher= ''
```

Una sola entrada, y en `PostToolUse`. Un `exit 2` ahí corre **después** de que la
herramienta ya se ejecutó: el archivo ya se escribió, el comando ya corrió. Lo que el
agente pierde no es la acción, es el **resultado** — y eso genera una asimetría fea: un
`Write` bloqueado igual deja el archivo, un `Read` bloqueado no devuelve nada.

Esto no lo descubrí yo: está en `docs/06-Daily/reports/subagent-budget-enforcer-architecture-2026-08-15.md`
(§2.1), con la telemetría de 1718 invocaciones al 100 % `PostToolUse`.

### 2.2 Fueron 51 → 52: un llamado, no dos

```bash
grep '"agent_id": "a11a796711b2e292b"' .cognitive-os/metrics/subagent-budget-enforcer.jsonl
```

```
{"action": "warn",  ... "tool_calls": 50, "timestamp": "2026-08-20T16:58:17Z"}
{"action": "block", ... "tool_calls": 51, "timestamp": "2026-08-20T16:58:17Z"}
{"action": "block", ... "tool_calls": 52, "timestamp": "2026-08-20T17:00:27Z"}
```

Entre el corte y el segundo choque hay **un** llamado contado, no dos. La corrección es
cosmética para el diagnóstico —el agente igual quedó inconcluso— pero el número importa
para dimensionar la concesión: al reanudar el presupuesto disponible es exactamente
**cero**, no «uno o dos».

### 2.3 Parte de esto ya estaba escrito y sin aplicar

`docs/06-Daily/reports/subagent-budget-enforcer-architecture-2026-08-15.md` (42 KB, del
2026-08-15) ya diseñó la partición del hook en modos `count`/`enforce` con parches
exactos, y `tests/contracts/test_subagent_budget_enforcer_modes.py` ya tiene **11 tests
con `xfail(strict=True)`** esperándolo. No se aplicó por el mismo motivo por el que yo
tampoco puedo aplicar el mío: superficie protegida.

O sea: el encargo de hoy es, en parte, **la tercera instancia del mismo problema que el
encargo describe** — un agente entregó diseño + parches exactos y no pudo aplicarlos. Este
informe no rehace ese diseño; ataca el defecto distinto y complementario (reanudar da
cero), y su parche es compatible con la partición en modos pendiente.

---

## 3. Dónde vive el contador y cómo se persiste — corriendo el mecanismo

Un archivo de texto plano, uno por `(session_id, agent_id)`:

```
.cognitive-os/sessions/<session_id>/subagent-tool-calls-<agent_id>
```

El `agent_id` sale del entorno o del payload, y si no hay, de `sha1(transcript_path)[:12]`.
Las dos fuentes **sobreviven al mensaje que reanuda** — por eso reanudar no resetea nada.
No hay ningún código que lo borre ni lo baje:

```bash
git grep -n 'subagent-tool-calls' -- . | grep -v '^docs/'
# solo: el hook que lo escribe, y tests que verifican que session-cleanup NO lo toque
```

Estado real en disco:

```bash
find .cognitive-os/sessions -name 'subagent-tool-calls-*' -type f | wc -l
# 268
```

```bash
find .cognitive-os/sessions -name 'subagent-tool-calls-*' -type f \
  | while read -r f; do printf '%s\t%s\n' "$(cat "$f")" "$f"; done | sort -rn | head -3
# 96  .../subagent-tool-calls-a632278962fd85ae2
# 57  .../subagent-tool-calls-a4212f8cc1791fd80
# 57  .../subagent-tool-calls-ad0af1c834c700ab3
```

Un contador en 96 con presupuesto 50 no es un agente que trabajó mucho: es un agente que
chocó y siguió cobrando cada choque.

---

## 4. La magnitud: no es una anécdota, es el patrón dominante

```bash
grep '"action": "block"' .cognitive-os/metrics/subagent-budget-enforcer.jsonl \
  | python3 -c '
import sys,json,collections
c=collections.Counter(json.loads(l)["agent_id"] for l in sys.stdin)
print("agentes bloqueados:", len(c))
print("bloqueados MAS DE UNA VEZ:", sum(1 for v in c.values() if v>1))
print("peor caso:", c.most_common(1))
'
```

```
agentes bloqueados: 93
bloqueados MAS DE UNA VEZ: 58
peor caso: [('ae7fd3dbd1dfcbe71', 25)]
```

**58 de 93** — el 62 % de los agentes bloqueados fueron bloqueados más de una vez, o sea
reanudados y chocados de nuevo. El peor acumuló 25 bloqueos y llegó a 75 llamadas
contadas. Tres instancias observadas hoy a mano son la punta de esto.

Y el efecto perverso completo, en un solo agente:

```bash
grep '"agent_id": "a2e61af8bbb75b87a"' .cognitive-os/metrics/subagent-budget-enforcer.jsonl
```

Del llamado 46 al 65 corre con `action=allow` y `reason=bypass:...`. El agente que **sí**
activó el bypass hizo 20 llamadas más y terminó su trabajo. El que obedeció «no actives el
bypass» quedó en cero. **El incentivo apunta exactamente al revés del que queremos**, y eso
es lo que hay que arreglar, no el número 50.

---

## 5. Hallazgo adversarial no pedido: el bypass es de alcance PROYECTO

Severidad **ALTA**. `hooks/_lib/bypass-resolver.sh`:

```bash
_cos_bypass_runtime_file() {
  printf '%s/.cognitive-os/runtime/bypass.env' "$(_cos_bypass_project_dir)"
}
```

Sin ninguna componente de agente. El `bypass.env` que un sub-agente escribe para
destrabarse **destraba a todos los sub-agentes concurrentes**, y el motivo que queda
auditado en esas llamadas es el de otro encargo. Comprobado con contrafáctico (rama F,
§7): AG2 monta el bypass escrito para AG1 y sale `exit=0`.

Queda cubierto por `test_el_bypass_de_hoy_es_de_alcance_proyecto`, verde hoy y que se
pondrá rojo el día que alguien lo cierre — que es cuándo hay que actualizarlo, no borrarlo.

**El parche de este informe no cierra este agujero.** Lo deja acotado por el costado: la
concesión nueva sí es por agente, así que la vía recomendada deja de ser la global.

---

## 6. Las cuatro opciones, con falla-que-arregla / falla-que-introduce / costo

| Opción | Arregla | Introduce | Costo |
|---|---|---|---|
| **A. Presupuesto por turno** | Reanudar devuelve presupuesto: el trabajo deja de ser irrecuperable | Un agente en loop se reanuda indefinidamente y el presupuesto deja de acotar nada. Y **no hay dónde engancharlo**: el hook es `PostToolUse`, no ve «empezó un turno»; habría que confiar en que `SubagentStart` dispare al reanudar, cosa que no pude medir | Medio-alto: hook nuevo o registro nuevo en `.claude/settings.json` (otra superficie protegida) + tope de reanudaciones |
| **B. Reanudación con presupuesto explícito** ← **elegida** | Lo mismo que A, y además convierte una decisión hoy implícita (bypass ilimitado) en explícita, acotada, por agente y auditada | Una superficie más que el orquestador tiene que saber usar; si nadie la usa, no pasa nada malo (degrada al estado actual) | Bajo: ~30 líneas en un hook ya existente, sin registro nuevo |
| **C. Presupuesto proporcional al encargo** | Los barridos dejan de chocar tan temprano | **No arregla el defecto reportado**: un agente de barrido con presupuesto 120 igual vuelve con cero al reanudar. Y exige una señal de tamaño confiable en el encargo, o sea disciplina del orquestador que hoy no existe | Medio, y dominado por B |
| **D. Solo instrucción: informe y parches ANTES de implementar** | Nada del mecanismo, pero **evita** la pérdida: es lo que de facto funcionó hoy | No arregla la irrecuperabilidad, la esquiva. Y tiene un costo que sí medí: **no hay lugar en el canal** | Cero código, pero −N caracteres de un presupuesto casi agotado |

### 6.1 Por qué D no puede ser la vía principal — el canal está lleno

D es candidata seria y no la descarto por aburrida: la descarto por medición.

```bash
python3 -c "
import re,pathlib
R=pathlib.Path('.')
inj=(R/'hooks/subagent-context-injector.sh').read_text()
tope=int(re.search(r'^MAX_CONTEXT_CHARS=(\d+)',inj,re.M).group(1))
f=[R/'templates/agent-mandatory-rules.md',R/'templates/agent-preamble.md']
t=sum(len(x.read_text()) for x in f)+1
print('tope',tope,'fijo',t,'margen sobre la reserva',tope-1200-t)
"
# tope 10000 fijo 8612 margen sobre la reserva 188
```

Quedan **188 caracteres** de margen. La instrucción de D no entra sin recortar otra cosa,
y el truncado del injector corta **al final**, justo donde vive el contrato de reporte.

### 6.2 Pero el núcleo de D se queda — por un canal que no cuesta nada

La instrucción de D viaja en el **stderr del bloqueo**, que no consume un solo carácter del
injector y llega exactamente en el momento en que hace falta:

```
ESCRIBI PRIMERO el informe y los parches EXACTOS de lo que ya averiguaste:
reanudarte NO te devuelve presupuesto, y un hallazgo sin parche aplicable se
pierde entero.
```

Cubierto por `test_el_mensaje_de_bloqueo_pide_el_informe_primero`.

---

## 7. Contrafáctico — mismo payload, las dos ramas

Script reproducible en `scripts/` no: es de proceso, y queda en el scratchpad. Lo que
importa es que **se puede volver a correr** apuntando `COS_TEST_BUDGET_HOOK` al candidato,
y eso lo hace el gate (§8).

```
===== A. agente reanudado despues del corte (contador=51), SIN concesion =====
  actual   : exit=2 counter=52      <- el bloqueo COBRA: cava mas hondo
  parcheado: exit=2 counter=51      <- estacionado

===== B. mismo agente, el orquestador concede +20 CON motivo =====
  actual   : exit=2 counter=52      <- no sabe leer la concesion
  parcheado: exit=0 counter=52
  metrica grant emitida: 1

===== C. concesion SIN motivo: no vale =====
  parcheado: exit=2 counter=51

===== D. concesion de 9999 se recorta al techo (50+50=100) =====
  parcheado @100: exit=0 counter=100
  parcheado @101: exit=2 counter=101

===== E. la concesion es POR AGENTE: AG2 no monta la de AG1 =====
  parcheado AG2: exit=2 counter=51

===== F. control: el bypass de HOY es de alcance PROYECTO (el agujero) =====
  actual AG2 monta el bypass ajeno: exit=0 counter=52

===== G. control negativo: por debajo del presupuesto nada bloquea =====
  actual   @10: exit=0 counter=11
  parcheado @10: exit=0 counter=11   <- identicos, como debe ser
```

G es el control que hace falta: sin él, un hook que bloqueara siempre pasaría todas las
ramas de bloqueo y el contrafáctico no probaría nada.

---

## 8. El gate, y el trinquete disparando

Archivo nuevo: `tests/contracts/test_subagent_budget_resume_grant.py` (`tests/` no es
superficie protegida; verificado, §9).

```bash
.venv/bin/python3 -m pytest tests/contracts/test_subagent_budget_resume_grant.py -q
# 5 passed, 4 xfailed in 1.53s          <- contra el repo, hook sin parchear

COS_TEST_BUDGET_HOOK=<copia parcheada> \
  .venv/bin/python3 -m pytest tests/contracts/test_subagent_budget_resume_grant.py -q
```

```
FAILED ...::test_un_llamado_bloqueado_no_consume_presupuesto
FAILED ...::test_concesion_acotada_con_motivo_destraba
FAILED ...::test_la_concesion_se_recorta_al_techo
FAILED ...::test_el_mensaje_de_bloqueo_pide_el_informe_primero
4 failed, 5 passed in 1.73s
```

Los cuatro fallan por `XPASS(strict)`: pasan contra el parche. Ése es el trinquete —
obliga a sacar el marcador junto con el parche, en lugar de dejar un test verde que no
prueba nada.

### 8.1 Dos de mis propias sondas estaban rotas y el trinquete las delató

En la primera corrida, `test_concesion_sin_motivo_no_vale` y `test_la_concesion_es_por_agente`
dieron `XPASS(strict)` **contra el repo sin parchear**. Motivo: los dos afirman «bloquea», y
el hook de hoy bloquea igual porque no sabe leer concesiones. Daban el mismo resultado en
las dos ramas del contrafáctico, o sea no medían nada.

Se les sacó el marcador y se anotó por qué: su poder discriminante existe recién después
del parche, y siempre apareados con `test_concesion_acotada_con_motivo_destraba`, que es el
que sí distingue. Un test que dice «bloquea» solo significa algo al lado de uno que dice
«deja pasar».

### 8.2 Gates de contorno

```bash
.venv/bin/python3 -m pytest tests/contracts/test_canal_al_subagente_tiene_margen.py -q
# 4 passed in 0.03s     (no se tocaron plantillas: la reserva no se movió)

.venv/bin/python3 -m pytest tests/contracts/test_subagent_budget_enforcer.py \
                            tests/contracts/test_subagent_budget_enforcer_modes.py -q
# 9 passed, 10 xfailed in 8.44s   (baseline sin cambios)
```

---

## 9. Lo que NO pude aplicar, y por qué no lo forcé

`hooks/**` está en `protected_globs` de `manifests/protected-config-write-policy.yaml`,
`default_mode: block`. Verificado corriendo el guard con las dos ramas, no leyendo el yaml:

```bash
GUARD=hooks/protected-config-write-guard.sh
printf '{"tool_name":"Edit","tool_input":{"file_path":"'"$PWD"'/hooks/subagent-budget-enforcer.sh",...}}' | bash "$GUARD"; echo $?
# === PROTECTED CONFIG WRITE GUARD: BLOCKED ===  -> 2
printf '{"tool_name":"Edit","tool_input":{"file_path":"'"$PWD"'/tests/contracts/zzz.py",...}}' | bash "$GUARD"; echo $?
# -> 0
```

Las dos ramas difieren, así que la sonda sirve. **Revisión humana pendiente, no un bypass
a activar.**

### 9.1 Hallazgo lateral: el guard bloquea lecturas

Severidad **MEDIA**, falso positivo. El guard hace match sobre el texto del comando, no
sobre la operación, así que también bloquea comandos **read-only** que apenas *nombran* la
ruta protegida. Me bloqueó dos veces:

- `python3 -c "...for l in Path('hooks/subagent-budget-enforcer.sh')..."` — una lectura.
- `bash hooks/subagent-budget-enforcer.sh` alimentado por stdin — **ejecutar el hook**, que
  es la única forma de verificarlo.

El efecto práctico es perverso para esta política: quien quiere *auditar* un hook protegido
tiene que trabajar sobre copias, y la tentación de exportar `COS_ALLOW_PROTECTED_CONFIG_WRITE`
para una simple lectura es exactamente el verde barato que la política existe para evitar.
Se resolvió copiando el hook al scratchpad, sin bypass.

---

## 10. El parche exacto (pendiente de aplicar a mano)

Sobre `hooks/subagent-budget-enforcer.sh` en `0dd2cdfc9`. Verificado con `bash -n` y con el
contrafáctico completo de §7.

```diff
@@ -118,6 +118,37 @@
 WARN_AT="${COS_SUBAGENT_TOOL_CALL_WARN_AT:-$BUDGET}"
 case "$WARN_AT" in ''|*[!0-9]*) WARN_AT="$BUDGET" ;; esac
 
+# --- Resume grant (bounded, per-agent) — ADR-311 follow-up -----------------
+# El contador es acumulativo por invocacion de sub-agente y NINGUNA reanudacion
+# lo resetea: un agente cortado en 51/50 vuelve con presupuesto CERO, asi que su
+# primer llamado al reanudar vuelve a chocar. Medido 2026-08-20 sobre
+# .cognitive-os/metrics/subagent-budget-enforcer.jsonl: 58 de 93 agentes
+# bloqueados lo fueron MAS DE UNA VEZ. La instruccion correcta ("para y reporta
+# parcial") dejaba el trabajo irrecuperable, y el bypass -ilimitado y de alcance
+# PROYECTO- era la unica salida: el incentivo exactamente al reves.
+#
+# La concesion es explicita, acotada y con dueno: la escribe el orquestador,
+# vale para UN agente, tiene techo duro y exige motivo.
+GRANT_DIR="$PROJECT_DIR/.cognitive-os/runtime/budget-grants"
+GRANT_FILE="$GRANT_DIR/$AGENT_ID"
+GRANT=0
+GRANT_REASON=""
+if [ -f "$GRANT_FILE" ]; then
+  GRANT="$(grep -E '^GRANT=' "$GRANT_FILE" 2>/dev/null | tail -1 | sed -e 's/^GRANT=//' -e 's/[^0-9]//g')"
+  GRANT_REASON="$(grep -E '^REASON=' "$GRANT_FILE" 2>/dev/null | tail -1 | sed -e 's/^REASON=//' -e 's/^"//' -e 's/"$//')"
+fi
+case "$GRANT" in ''|*[!0-9]*) GRANT=0 ;; esac
+# Techo duro: una concesion jamas puede mas que duplicar el presupuesto base.
+GRANT_CEILING="${COS_SUBAGENT_BUDGET_GRANT_CEILING:-$BUDGET}"
+case "$GRANT_CEILING" in ''|*[!0-9]*) GRANT_CEILING="$BUDGET" ;; esac
+[ "$GRANT" -gt "$GRANT_CEILING" ] 2>/dev/null && GRANT="$GRANT_CEILING"
+# Sin motivo no hay concesion: un escape sin constancia es un agujero.
+if [ "$GRANT" -gt 0 ] && [ -z "$GRANT_REASON" ]; then
+  GRANT=0
+  GRANT_REASON="__missing__"
+fi
+EFFECTIVE_BUDGET=$((BUDGET + GRANT))
+
 RUNTIME_DIR="$PROJECT_DIR/.cognitive-os/sessions/$SESSION_ID"
@@ -178,6 +209,10 @@
 PYEOF
 }
 
+if [ "$GRANT" -gt 0 ] && [ "$COUNT" -gt "$BUDGET" ]; then
+  emit_metric "grant" "resume_grant:+$GRANT:$GRANT_REASON"
+fi
+
 if [ "$ESCALATION_DECLARED" = "1" ]; then
@@ -195,12 +230,20 @@
-if [ "$COUNT" -gt "$BUDGET" ]; then
+if [ "$COUNT" -gt "$EFFECTIVE_BUDGET" ]; then
+  # Un llamado bloqueado NO consume presupuesto. Antes si, y por eso un agente
+  # cortado cavaba mas hondo con cada reintento (medido: agente
+  # ae7fd3dbd1dfcbe71, 25 bloqueos, contador hasta 75). Con el cobro apagado el
+  # contador queda estacionado en EFFECTIVE_BUDGET+1 y una concesion de N da
+  # exactamente N llamados usables, no N menos lo gastado chocando.
+  COUNT=$((EFFECTIVE_BUDGET + 1))
+  printf '%s' "$COUNT" > "$COUNTER_FILE" 2>/dev/null || true
   emit_metric "block" "budget_exceeded"
-  printf '...exceeding budget %s. Emit `ESCALATION:` ... bypass.env ...\n' "$AGENT_ID" "$COUNT" "$BUDGET" >&2
+  printf '...exceeding budget %s. ESCRIBI PRIMERO el informe y los parches EXACTOS de lo que ya averiguaste: reanudarte NO te devuelve presupuesto, y un hallazgo sin parche aplicable se pierde entero. Emit `ESCALATION:` with diagnosis, progress, files touched, and next safe action. Para concederle presupuesto ACOTADO a este agente, el orquestador escribe %s con GRANT=<n> y REASON=<motivo> (techo %s, por agente, auditado).\n' "$AGENT_ID" "$COUNT" "$EFFECTIVE_BUDGET" "$GRANT_FILE" "$GRANT_CEILING" >&2
   exit 2
 fi
 
+[ "$GRANT" -gt 0 ] && WARN_AT="$EFFECTIVE_BUDGET"
 if [ "$COUNT" -ge "$WARN_AT" ]; then
```

El diff completo y aplicable está en el scratchpad de la sesión
(`subagent-budget-resume-grant.patch`, 74 líneas). **Es artefacto de proceso: si se pierde,
se regenera con el §10 de este informe, que es la fuente durable.**

### 10.1 Cómo se usa, una vez aplicado

El orquestador, al reanudar un agente cortado:

```bash
mkdir -p .cognitive-os/runtime/budget-grants
cat > .cognitive-os/runtime/budget-grants/<AGENT_ID> <<'EOF'
GRANT=20
REASON=cerrar el informe y aplicar los parches que ya diseño
EOF
```

Y queda en `.cognitive-os/metrics/subagent-budget-enforcer.jsonl` con `action=grant`.

### 10.2 Lo que el parche deliberadamente NO hace

- **No resetea** el contador. Concede. El gasto histórico sigue visible.
- **No toca** `bypass.env`: la vía ilimitada sigue funcionando igual, solo deja de estar
  anunciada en el mensaje de bloqueo. Cerrar el agujero de alcance-proyecto (§5) es otro
  cambio, en `hooks/_lib/bypass-resolver.sh`, y también es superficie protegida.
- **No arregla** que el hook sea `PostToolUse` (§2.1). Eso es la partición en modos del
  informe del 2026-08-15, y este parche es compatible con ella: toca la decisión de
  bloqueo, no el modo.

---

## 11. Pendientes que quedan con dueño humano

1. **Aplicar el parche de §10** a `hooks/subagent-budget-enforcer.sh` y sacar los 4
   `xfail(strict=True)` de `tests/contracts/test_subagent_budget_resume_grant.py`.
2. **Aplicar la partición en modos** del informe del 2026-08-15 y sacar sus 11
   `xfail(strict=True)`. Sin eso, el bloqueo sigue llegando tarde.
3. **Decidir sobre el alcance del `bypass.env`** (§5): hoy un agente destraba a todos.
4. **Decidir sobre el falso positivo del write-guard** (§9.1): bloquear lecturas y
   ejecuciones empuja al bypass a quien solo quiere auditar.

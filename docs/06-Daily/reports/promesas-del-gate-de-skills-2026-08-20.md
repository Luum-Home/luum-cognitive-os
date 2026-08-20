<!-- SCOPE: os-only -->
# Las promesas escritas del gate de skills (ADR-188)

Fecha: 2026-08-20 · Alcance: lado documento de ADR-188 (el hook y sus tests de
comportamiento los estaba reconstruyendo otro agente en paralelo).

## Resumen ejecutivo

- ADR-188 prometía `< 30 ms` de latencia para el gate. Medido sobre el corpus
  completo de `hook-timing` (vivo **+ rotados**): **p50 490 ms, p99 1470 ms
  sobre 245 invocaciones**. Cero de las 245 bajó de 30 ms.
- Decidí **reemplazar el presupuesto por la medición**, con el comando pegado,
  y bajar el techo falsable de `p99 < 50 ms` al presupuesto de evento que el
  propio instrumento ya aplica para `PreToolUse` (2000 ms).
- La aserción de p99 que el ADR citaba en `test_skill_invocation_gate.py`
  **no existía**. Retiré la cita y escribí un test nuevo —
  `tests/contracts/test_skill_gate_latency_claim.py`, 6 aserciones— que vigila
  que la cifra escrita siga a la telemetría.
- Los dos mensajes `incompleto` viven **dentro del hook que no me correspondía
  tocar**. El censo no cambió (13/42) y explico por qué abajo; sí arreglé el
  equivalente del lado documento, que el instrumento no mira.
- El canal de la anotación estaba mal prescripto en el ADR: `PreToolUse` corre
  antes de que el modelo escriba. Corregido a `tool_input`.

## Correcciones a las premisas del encargo

1. **`p50 = 642 ms` no es el número.** Sobre `hook-timing.jsonl` más los once
   rotados de `.cognitive-os/metrics/.archive/`, deduplicado por línea, el gate
   tiene **p50 490 ms** en 245 invocaciones (ventana 2026-07-19T05:50:32Z →
   2026-08-20T05:11:44Z). 642 ms probablemente sale de contar solo el vivo o una
   ventana más corta. La dirección del hallazgo se sostiene —está a 16 veces del
   presupuesto, no a 21— pero el número del encargo no.
2. **"Los dos mensajes con salida inejecutable… bajalos" choca con la regla 1
   del propio encargo.** `scripts/audit_killswitch_activation.py --json` los
   ubica en `hooks/orchestrator-skill-invocation-gate.sh:228` y `:246`, o sea el
   archivo que la regla 1 me prohíbe tocar, y el instrumento **solo mira hooks**
   (lo dice su propia nota de alcance). No hay forma de bajar ese censo sin
   editar ese hook. No lo edité. Verifiqué la propiedad con
   `git status --porcelain` sobre los cuatro archivos del otro agente: el gate
   estaba limpio y `hooks/skill-router-prompt-suggest.sh` modificado — o sea,
   el otro agente ya estaba trabajando en ese conjunto, y la colisión que la
   regla 1 anticipa es real, no teórica.
3. **No es cierto que "el gate es de los `PreToolUse` más caros".** Yo mismo
   escribí esa frase en un borrador del ADR y la telemetría la desmintió: por
   p50 quedan arriba `agent-prelaunch` (2409 ms), `pre-agent-snapshot` (945 ms),
   `inject-phase-context` (894 ms), `blast-radius` (818 ms) y
   `clarification-gate` (798 ms). El gate está en la mitad de la tabla. Lo
   corregí antes de commitear.
4. **El override inejecutable no estaba solo en el hook: estaba en el ADR y en
   la regla.** ADR-188 §Operational Guide ofrecía
   `COS_ALLOW_SKILL_BYPASS=1 COS_SKILL_BYPASS_REASON='<text>' <agent-launch>`,
   que es exactamente la forma de prefijo que este repo midió que no llega a
   ningún hook. `rules/skill-invocation-mandatory.md` decía "before launching
   the Agent/Bash tool", que suena bien y tampoco es tipeable: no se puede
   setear el entorno del arnés desde adentro de la sesión. Los dos eran míos y
   los dos están arreglados.
5. **Confirmado, no suavizado**: el commit `241cf1e58` (2026-08-20,
   `fix(tests): que un test no pueda escribir en la telemetria del operador`)
   borró `# Latency budget: <30 ms.` de la cabecera del hook y dejó el ADR
   intacto. `git log -S"Latency budget" -- hooks/orchestrator-skill-invocation-gate.sh`
   devuelve exactamente dos commits: el que la puso y el que la sacó.
6. **Premisa (d) confirmada tal cual.** El umbral 3 y el contador **por sesión**
   están escritos en ADR-188 §Enforcement layers y implementados en el hook
   (`COUNTER_FILE="$RUNTIME_DIR/skill-bypass-counter-${SESSION_ID}"`,
   `if [ "$count" -ge 3 ]`). Lo que no tiene decisión ni código es la
   acumulación **entre** sesiones. Lo dejé anotado en §Open Questions sin
   inventar el contrato nuevo, que es del otro agente.

## La latencia medida, con su comando

```bash
{ gunzip -c .cognitive-os/metrics/.archive/hook-timing-*.jsonl.gz; \
  cat .cognitive-os/metrics/hook-timing.jsonl; } | sort -u > /tmp/hook-timing-all.jsonl
python3 scripts/hook_timing_report.py --path /tmp/hook-timing-all.jsonl --json \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["by_hook"]["orchestrator-skill-invocation-gate"])'
```

```
{'count': 245, 'failures': 0, 'p50': 490.0, 'p95': 1140.0, 'p99': 1470.0,
 'max': 4271.0, 'total_ms': 138967.0, 'events': ['PreToolUse'],
 'budget_ms': 2000, 'over_budget': False}
```

Tres cosas sobre el método, porque el número solo no alcanza:

- **Los rotados cuentan.** El vivo tiene una fracción del corpus; hay once
  `hook-timing-*.jsonl.gz` en `.archive/`. Contar solo el vivo es el caso 1 de
  `rules/procedencia-de-los-numeros.md`.
- **Deduplicado.** `sort -u` sobre 313.360 líneas devuelve 313.360: no hay
  solapamiento entre rotados y vivo. El `grep -c` directo sobre el corpus da
  245, igual que el instrumento — el número no depende de mi parser.
- **Corrí el instrumento, no lo reimplementé.** `scripts/hook_timing_report.py`
  ya sabía calcular percentiles y ya conocía el presupuesto por evento
  (`budget_ms: 2000`); lo único que le falta es leer los `.gz`, y eso se
  resuelve concatenando antes en vez de escribiendo otro contador.

Contraste con los vecinos del mismo matcher: `agent-working-dir-inject` p50
313 ms, `error-pattern-detector` p50 379 ms. No es un problema de este hook: un
hook bash que arranca `python3` en este arnés no entra en 30 ms.

## Qué decidí con el presupuesto de 30 ms

**Lo reemplacé por la medición.** Las dos salidas eran legítimas —hacer cumplir
el presupuesto o cambiarlo por el número real— y elegí la segunda por una razón
verificable, no por comodidad: no hay **ningún** hook `PreToolUse` en este repo
con p50 cerca de 30 ms. Un presupuesto que ningún miembro de su familia cumple
no es un presupuesto exigente, es una unidad equivocada.

Lo que cambió en ADR-188:

| Dónde | Antes | Ahora |
|---|---|---|
| §Acceptance Criteria 2 | `Latency budget: < 30 ms.` | remite a §Latencia medida |
| §Consequences | `Adds ~10–30 ms latency` | p50 490 ms / p99 1470 ms, con ventana |
| Tabla operativa | `< 30 ms per Agent/Bash launch` | p50 490 ms / p99 1470 ms medidos |
| §Falsifiable Claim 4 | `p99 < 50 ms` | p99 bajo el presupuesto `PreToolUse` (2000 ms) que ya aplica el instrumento |
| — | (no existía) | §Latencia medida: tabla + comando + método |

El techo nuevo no es de invención propia: es el que
`scripts/hook_timing_report.py --threshold-only` ya usa para `PreToolUse`. Hoy
el gate está adentro (1470 < 2000) pero sin margen cómodo, y eso quedó escrito
en el ADR en vez de redondearse a "cumple".

## La aserción que el ADR citaba y no existía

`docs/…/ADR-188…md:203` decía: *"check `tests/contracts/test_skill_invocation_gate.py`
p99 latency assertion"*. Comprobación:

```bash
grep -c "p99\|latency\|duration" tests/contracts/test_skill_invocation_gate.py   # -> 0
```

**Retiré la cita y escribí el instrumento que falta**, en un archivo nuevo para
no chocar con el otro agente: `tests/contracts/test_skill_gate_latency_claim.py`
(6 tests, todos pasando). No duplica los tests de comportamiento del gate —
prueba la otra mitad, que es la mía:

1. el ADR no vuelve a prometer 30 ms fuera de la sección que documenta el retiro;
2. **toda** cita a un `tests/**.py` como prueba de latencia tiene que existir y
   contener la aserción citada (la regla general, no el caso puntual);
3. §Latencia medida nombra el instrumento, el vivo y los rotados;
4. el p50 escrito en el ADR sigue a la telemetría dentro de una banda 0,5×–2×
   (490 ms admite 245–980 ms) y **se salta declarando "no medido"** si hay menos
   de 50 muestras, en vez de afirmar un percentil sobre cuatro datos;
5. ni el ADR ni la regla vuelven a ofrecer el override como prefijo;
6. el ADR no vuelve a prescribir la anotación en la respuesta del asistente.

Que el gate no sea decorativo está probado, no afirmado:

```bash
printf '\n- Latency budget: < 30 ms.\n' >> docs/02-Decisions/adrs/ADR-188-mandatory-skill-invocation-at-high-confidence.md
python3 -m pytest tests/contracts/test_skill_gate_latency_claim.py -q   # -> 1 failed, 5 passed
git checkout -- docs/02-Decisions/adrs/ADR-188-mandatory-skill-invocation-at-high-confidence.md
python3 -m pytest tests/contracts/test_skill_gate_latency_claim.py -q   # -> 6 passed
```

La banda de 0,5×–2× es la parte discutible y la dejo dicha: es lo bastante
ancha para no chillar por ruido y lo bastante angosta para que una optimización
real (o una degradación real) obligue a reescribir la cifra. Si se demuestra
floja, se aprieta — pero no se aprieta a ciegas.

## Los dos mensajes, antes y después

Censo del instrumento, antes y después de mi trabajo:

```bash
python3 scripts/audit_killswitch_activation.py
```

| | antes | después |
|---|---|---|
| medibles | 42 | 42 |
| honesto | 29 (69,0 %) | 29 (69,0 %) |
| incompleto | 13 (31,0 %) | 13 (31,0 %) |
| mentira | 0 (no-observación) | 0 (no-observación) |

**No cambió, y no podía cambiar desde donde yo estaba parado.** Los dos casos
del encargo son `hooks/orchestrator-skill-invocation-gate.sh:228` y `:246`, y
el instrumento declara su alcance en su propia salida: *"solo mira hooks"*. El
arreglo requiere editar el hook del otro agente. Lo dejo explícito como deuda
con dueño, no como hallazgo nuevo: el texto que hay que cambiar es el que
ofrece `COS_ALLOW_SKILL_BYPASS=1` sin nombrar vía, y la vía correcta es
`export` en la shell que **lanza** el arnés (a mitad de sesión no hay vía de
entorno para este gate: el hook no consulta `bypass.env` para esa variable —
la vía de mitad de sesión es la anotación en el `tool_input`).

Lo que **sí** bajé es el mismo defecto en el canal que el instrumento no mira:

| Archivo | Antes | Después |
|---|---|---|
| ADR-188 §Operational Guide | `COS_ALLOW_SKILL_BYPASS=1 COS_SKILL_BYPASS_REASON='<text>' <agent-launch>` | bloque `export …; claude`, más la aclaración de por qué el prefijo no llega y cuál es la vía de mitad de sesión |
| `rules/skill-invocation-mandatory.md` §Emergency Env Override | "before launching the Agent/Bash tool" | "en la shell que **lanza el arnés**", con la vía de mitad de sesión nombrada |

Y para que no vuelva: el test 5 de arriba escanea ADR-188 y la regla buscando
la forma de prefijo. Es la misma estrategia por ruta que ya usa
`tests/contracts/test_killswitch_activation_is_executable.py` para los `.md`.

## El canal de la anotación

ADR-188 §Decision, punto 3, prescribía emitir `SKILL_BYPASS:` *"in the assistant
response"*. El hook la busca en `$TOOL_BLOB`, o sea el `tool_input`:

```
hooks/orchestrator-skill-invocation-gate.sh:158
  if printf '%s' "$TOOL_BLOB" | grep -qE "SKILL_BYPASS:[[:space:]]*${SKILL}([[:space:]]|\$)"; then
```

El ADR estaba mal y el hook estaba bien, y no es cuestión de gusto: un hook de
`PreToolUse` corre **antes** de que el modelo escriba su respuesta, así que el
canal que el ADR prescribía es invisible por construcción. Corregí el ADR para
que prescriba el `tool_input` y agregué la razón en una línea, para que la
próxima persona no lo "arregle" al revés. **No toqué el hook**: acá no había
nada que implementar, el defecto era la prosa.

Nota de contexto, no de código: la orquestación de esta sesión emitió la
anotación siguiendo el ADR y no funcionó. Dos causas, no una — el canal
equivocado y además otra skill nombrada. La primera queda cerrada acá; la
segunda es del lado de quien emite.

## Lo que NO hice y por qué

- **No toqué `hooks/orchestrator-skill-invocation-gate.sh`,
  `hooks/skill-router-prompt-suggest.sh`, `cos_lib/skill_router.py` ni
  `tests/contracts/test_skill_invocation_gate.py`.** Otro agente los estaba
  reconstruyendo; `git status` confirmó que ya tenía uno de los cuatro
  modificado. Por eso los dos mensajes `incompleto` siguen en pie.
- **No escribí la aserción de latencia dentro de `test_skill_invocation_gate.py`**,
  que es donde el ADR la citaba. Habría sido el lugar "correcto" y el
  equivocado a la vez: archivo ajeno, colisión segura. Fue a un archivo nuevo,
  y el ADR ahora apunta ahí.
- **No reescribí el contrato de conteo** (repeticiones del mismo hash de prompt
  en vez del acumulado). Lo está implementando el otro agente y el contrato lo
  define su implementación, no mi documento. Dejé anotado en §Open Questions lo
  único que ya se puede afirmar sin él: que el umbral 3 y el contador por
  sesión están decididos, y que la acumulación entre sesiones nunca lo estuvo.
- **No cambié el umbral 0.90 ni nada del comportamiento del gate.** El encargo
  era sobre promesas escritas.
- **No corrí `make test-laptop`.** Corrí las lanas que tocan lo que cambié
  (`tests/audit/test_adr_contracts.py` y
  `tests/contracts/test_killswitch_activation_is_executable.py`: 1504 passed,
  más los 6 del test nuevo). La suite completa queda para el orquestador.
- **No escribí en `.cognitive-os/metrics/` ni en `runtime/`.** El aviso de
  escrituras en telemetría que imprime la suite corresponde a la sesión viva
  del operador corriendo en paralelo; usé
  `COS_ALLOW_OPERATOR_METRICS_WRITES=1`, que es la vía que el propio mensaje
  documenta para ese caso.

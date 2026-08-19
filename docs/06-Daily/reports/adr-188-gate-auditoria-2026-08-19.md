# ADR-188 — el gate que bloqueaba sin dejar rastro

Fecha: 2026-08-19 · Alcance: `hooks/orchestrator-skill-invocation-gate.sh`,
`scripts/skill_adherence_loop.py`, `tests/hooks/test_skill_invocation_gate_audit.py`

## Resumen ejecutivo

`_emit_audit()` existía y funcionaba, pero sólo se llamaba en dos ramas: bypass
anotado y env-override. La rama que realmente cuenta, avisa y bloquea —la del
contador— salía por `printf` a stderr y `exit` sin escribir nada. Por eso el
contador llegó a 131 y `.cognitive-os/metrics/skill-bypass.jsonl` nunca existió.
El sufijo `-unknown` **no** es un fallo de resolución de skill: es el
`SESSION_ID`, que casi siempre cae al literal `"unknown"`. El arreglo agrega la
escritura en las dos ramas faltantes (aviso y bloqueo) y, siguiendo el criterio
de Kyverno de emitir `pass` además de `fail`, también en la rama positiva —con
`reason` vacío, para que un `pass` no pueda leerse como bypass. Los 131 bloqueos
no son reconstruibles y no se fabricaron filas.

## Correcciones a las premisas del encargo

1. **`-unknown` no es la skill; es el `session_id`.** El encargo pedía verificar
   la pista de que el gate no resolvía el nombre de la skill. No es así:

   ```bash
   grep -n 'COUNTER_FILE=' hooks/orchestrator-skill-invocation-gate.sh
   # 131:COUNTER_FILE="$RUNTIME_DIR/skill-bypass-counter-${SESSION_ID}"
   grep -n 'z "\$SKILL"' hooks/orchestrator-skill-invocation-gate.sh
   # 65:[ -z "$SKILL" ] && exit 0
   ```

   La línea 65 hace que el gate salga con 0 **antes** de contar si la skill no se
   resuelve. Un contador en 131 prueba que la skill se resolvió 131 veces. El
   `-unknown` sale del fallback de la línea 38 (`SESSION_ID="unknown"`).
   Corroborante: `grep -c '"session_id": "unknown"' .cognitive-os/metrics/skill-suggestion.jsonl`
   → `505`. Consecuencia: **no hay caso de sentinel que escribir** — el gate
   nunca puede llegar a la escritura con la skill sin resolver.

2. **`direct-main-bypass.jsonl` existe pero tiene 0 filas.** El encargo lo cita
   como ejemplo de "gates que sí escriben su log". `wc -l` da `0`. El único
   ejemplar vivo del patrón es `protected-config-bypass.jsonl` (488 filas), y su
   esquema (`timestamp`/`source`/`tool`/`session`) **no** sirve acá: no tiene
   `suggested_skill` ni `reason`, que son los dos campos que decide el consumidor.
   Seguí el contrato del consumidor, no el de los otros gates.

3. **Son 110 sugerencias de alta confianza, no 102.** El corpus creció desde que
   se escribió el encargo:

   ```bash
   .venv/bin/python3 scripts/skill_adherence_loop.py --json | \
     .venv/bin/python3 -c "import json,sys; print(json.load(sys.stdin)['result']['totals'])"
   # {'CLOSED': 2, 'BYPASSED': 0, 'UNTRACED': 10, 'UNMEASURABLE': 98}
   ```

   El `BYPASSED: 0` del encargo es correcto; el denominador no.

4. **131 no son 131 bloqueos.** El contador se incrementa en cada bypass sin
   anotar y sólo bloquea desde el tercero (`if [ "$count" -ge 3 ]`). Los 131
   incrementos son 2 avisos + 129 bloqueos.

5. **Defecto adicional que el encargo no menciona (no lo arreglé).** El contador
   es "por sesión" pero el `SESSION_ID` es siempre `"unknown"`, así que **nunca se
   resetea**: el archivo es un contador global monótono. Desde el tercer bypass de
   la historia del repo, el gate está en modo BLOCK permanente para toda sugerencia
   de alta confianza. Ver "Lo que NO hice".

## Por qué nunca escribió

No fallaba en silencio ni estaba condicionado a algo improbable: **faltaba la
llamada**. En el archivo original, `_emit_audit` aparecía tres veces:
la definición (línea 133), la rama anotada (153) y la rama env-override (163).
Las dos ramas terminales del camino no anotado —el `WARN` de la línea 180 y el
`BLOCK` de la 176— escribían a stderr y salían sin tocar el log.

Esas dos ramas son exactamente las que el contador registra. De ahí la asimetría
perfecta: contador en 131, log inexistente.

Evidencia sobre el archivo previo al arreglo (copia en el scratchpad de la
sesión):

```bash
grep -n '_emit_audit' <copia-pristina>.sh
# 133:_emit_audit() {
# 153:  _emit_audit "${BYPASS_REASON:-annotated}" "orchestrator-annotation"
# 163:  _emit_audit "env-override: $reason" "env-override"
```

Tres apariciones, ninguna en el camino que cuenta.

## Qué significa el sufijo -unknown

Es el `SESSION_ID` interpolado en el nombre del contador (línea 131), no el
nombre de la skill. Cadena de fallback en la línea 37:

```bash
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-${CLAUDE_SESSION_ID:-$(jq -r '.session_id // ""')}}"
[ -z "$SESSION_ID" ] && SESSION_ID="unknown"
```

`COGNITIVE_OS_SESSION_ID` no está seteado en la práctica —el propio docstring de
`scripts/skill_adherence_loop.py` lo dice y por eso deriva sesiones por hueco
temporal— y el payload de PreToolUse llega sin `session_id` usable (las 27 filas
de `hook-timing.jsonl` para este hook tienen `"session_id":""`).

El gate **sí** resuelve el nombre de la skill, siempre, o no llega a contar.

## El contrato que espera el consumidor

De `load_bypasses()` en `scripts/skill_adherence_loop.py` (líneas 205-227) y del
apareo en `classify()` (líneas 355-370):

| Campo | Uso en el consumidor | Si falta |
|---|---|---|
| `ts` (o `timestamp`) | `parse_ts()`; apareo por ventana | la fila se descarta |
| `suggested_skill` (o `skill`) | igualdad exacta con `sug["skill"]` | la fila se descarta |
| `reason` | **`audited = bool(reason)`** | fila cargada pero **nunca apareada** |
| `prompt_hash` | apareo directo, sin depender de la ventana | cae al apareo por ventana |
| `session_id` | normalización/reporte | sin efecto en el veredicto |
| `confidence` | no lo lee `load_bypasses` | sin efecto |

El campo que manda es `reason`: **una fila con `reason` vacío existe pero no
mueve el veredicto**. `classify()` sólo considera bypasses con `audited=True`, y
lo hace *después* de buscar una invocación apareada, así que `CLOSED` siempre le
gana a `BYPASSED`.

## El arreglo

`hooks/orchestrator-skill-invocation-gate.sh`:

1. `_emit_audit` toma un tercer argumento `outcome` y lo escribe, para que cada
   fila diga qué decidió el gate y no haya que inferirlo del texto de `reason`.
2. **Rama de aviso** (`count < 3`, el tool pasa): escribe con
   `outcome="bypass-unannotated"` y `reason` explícito sobre la falta de
   anotación. Éste es el bypass real y es el que faltaba.
3. **Rama de bloqueo** (`count >= 3`): escribe con `outcome="blocked"` antes de
   salir con 2. Es el caso que perdió 129 de las 131 filas.
4. **Rama positiva** (`INVOKED=1`): escribe con `outcome="invoked"` y
   **`reason=""`**. El criterio de Kyverno —emitir `pass` además de `fail`—
   aplicado sin romper al consumidor: con `reason` vacío, `audited=False`, y un
   `pass` no puede apearse como bypass ni inflar la adherencia. Deduplicada por
   `(session_id, prompt_hash, skill)` con un marcador en
   `.cognitive-os/runtime/skill-gate-pass-*`, porque esa rama dispara en cada
   tool call y produciría miles de filas.
5. Las ramas anotada y env-override pasan su `outcome` (`bypass-annotated`,
   `env-override`). Comportamiento sin cambios.

`scripts/skill_adherence_loop.py`: **sin tocar**. El esquema lo puso el consumidor.

Latencia: un `python3` extra sólo en las ramas de bypass/bloqueo; en la positiva,
un `test -f` salvo la primera vez por prompt.

Sintaxis validada con el bash real del sistema:

```bash
/bin/bash -n hooks/orchestrator-skill-invocation-gate.sh
# SYNTAX OK (GNU bash, version 3.2.57(1)-release (arm64-apple-darwin25))
```

Escritura sobre `hooks/**` (ruta protegida) hecha con el prefijo
`COS_ALLOW_PROTECTED_CONFIG_WRITE=1`, registrada en
`.cognitive-os/metrics/protected-config-bypass.jsonl`.

## Prueba en las dos direcciones

`tests/hooks/test_skill_invocation_gate_audit.py`. Corre el hook **real** contra
un `COGNITIVE_OS_PROJECT_DIR` temporal (`tmp_path`) y le pasa el log producido al
consumidor **real**. Ningún `.jsonl` del operador se toca; la fila la escribe el
hook, no el test.

La aserción que cierra el lazo de punta a punta es
`test_consumer_classifies_the_row_as_bypassed`: corre `skill_adherence_loop.py`
**antes** (control: `UNMEASURABLE: 1`) y **después** del gate, y exige
`BYPASSED == 1`, `UNTRACED == 0`, `UNMEASURABLE == 0`. Sin ese control previo el
test probaría que se escribió un archivo, no que el instrumento lo ve.

### Con el defecto presente — FALLA (6/6)

```
$ .venv/bin/python3 -m pytest tests/hooks/test_skill_invocation_gate_audit.py -p no:randomly -q
FFFFFF                                                                   [100%]
E   AssertionError: el gate evaluo, aviso y no escribio nada en skill-bypass.jsonl: una guarda que evalua y no emite es indistinguible de una guarda rota
    assert []
E   AssertionError: sin fila no hay contrato que verificar
    assert []
E   AssertionError: el instrumento no ve la fila que escribio el gate: {'CLOSED': 0, 'BYPASSED': 0, 'UNTRACED': 0, 'UNMEASURABLE': 1}
    assert 0 == 1
E   AssertionError: tres decisiones, tres filas; hay 0
    assert 0 == 3
E   AssertionError: la rama positiva tampoco puede ser muda: []
    assert 0 == 1
E   AssertionError: una decision por prompt, no una por tool call: 0 filas
    assert 0 == 1
6 failed in 1.62s
```

El `UNMEASURABLE: 1` de la tercera falla prueba que el arnés estaba vivo: el hook
corrió, avisó por stderr, y el consumidor leyó el corpus y se abstuvo por falta de
fila. No es un test que falla por no encontrar el archivo bajo prueba.

### Con el arreglo — PASA (6/6)

```
$ .venv/bin/python3 -m pytest tests/hooks/test_skill_invocation_gate_audit.py -p no:randomly -q
......                                                                   [100%]
6 passed in 1.89s
```

### Sin regresión

```
$ .venv/bin/python3 -m pytest tests/contracts/test_skill_adherence_loop.py \
    tests/red_team/portability/test_skill_adherence_loop.py \
    tests/hooks/test_protected_config_write_guard.py -p no:randomly -q
240 passed in 48.05s

$ .venv/bin/python3 -m pytest tests/hooks/test_hook_basics.py \
    tests/hooks/test_hook_graceful_degradation.py tests/hooks/test_hook_security.py -p no:randomly -q
583 passed in 102.30s
```

## Lo que se perdió y no se puede reconstruir

**Las 131 decisiones del gate están perdidas. No hay forma de reconstruirlas y no
fabriqué filas.**

Lo único que quedó es `.cognitive-os/runtime/skill-bypass-counter-unknown`, cuyo
contenido completo es el string `131`. Sin timestamps, sin nombre de skill, sin
`prompt_hash`, sin confianza, sin razón. Un entero no se convierte en 131 filas.

Rastros parciales que revisé y descarté como fuente de reconstrucción:

- `.cognitive-os/metrics/hook-timing.jsonl` registra `exit_code` por hook, pero
  tiene **27 filas** para este gate, **todas con `exit_code: 0`**, todas del
  2026-08-19 (el wrapper es reciente). Cero bloqueos capturados, y sin skill ni
  `prompt_hash` aunque los hubiera.
  Comando: `grep 'orchestrator-skill-invocation-gate' .cognitive-os/metrics/hook-timing.jsonl | grep -o '"exit_code":[0-9]*' | sort | uniq -c`
- `.cognitive-os/metrics/skill-suggestion.jsonl` registra qué se sugirió, no qué
  decidió el gate. Correlacionar sugerencias con bloqueos sería inventar el
  apareo.
- El texto del `WARN`/`BLOCK` iba a stderr del hook, que no se persiste.

De acá en adelante el conteo se preserva; lo anterior queda como hueco declarado.

## Lo que NO hice y por qué

- **No creé un `skill-bypass.jsonl` vacío.** Un archivo vacío haría que
  `sources.bypasses.exists` pase a `true` sin agregar una sola fila: apagaría el
  síntoma en el reporte y dejaría el hueco.
- **No fabriqué filas históricas** para los 131. Ver la sección anterior.
- **No toqué `scripts/skill_adherence_loop.py`.** El consumidor está bien: su
  `BYPASSED: 0` era un reporte fiel de un productor mudo. El defecto estaba
  aguas arriba.
- **No agregué un caso de sentinel `skill: unknown`.** El encargo lo pedía "si en
  algún caso genuinamente no se puede resolver". Verifiqué que ese caso **no
  existe**: la línea 65 sale con 0 antes de llegar a la escritura. Agregar una
  rama para un estado inalcanzable sería código muerto — exactamente lo que
  `rules/agent-quality.md` prohíbe.
- **No arreglé el contador que nunca se resetea** (corrección 5). Es un defecto
  distinto, con blast radius propio: hoy el gate está en BLOCK permanente para
  toda sugerencia ≥0.90, y arreglarlo cambia el comportamiento de bloqueo en
  runtime, no la auditoría. Merece su propia decisión del operador. El arreglo de
  acá lo vuelve **visible**: a partir de ahora cada bloqueo deja su fila con
  `outcome: "blocked"`, así que el patrón se va a poder medir en vez de inferir.

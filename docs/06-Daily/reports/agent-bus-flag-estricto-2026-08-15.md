# `AGENT_BUS_ENABLED` pasa a gatear el transporte, no sólo el aprovisionamiento

**Fecha:** 2026-08-15
**Alcance:** `packages/agent-coordination/lib/agent_bus.py` (expuesto como `cos_lib/agent_bus.py` vía symlink), `packages/agent-coordination/lib/agent_dashboard.py`, `tests/unit/test_agent_bus.py`, `tests/integration/test_valkey_local_daemon.py`
**Estado:** implementado, con tests que fallan sobre el código anterior
**Antecedente:** `02c76ae94` + `docs/06-Daily/reports/agent-bus-docker-2026-08-15.md`

## Qué cambió y por qué

`02c76ae94` acotó `AGENT_BUS_ENABLED` a gobernar el **aprovisionamiento**: con el flag
apagado no se levanta Docker, pero un Valkey ya corriendo se sondeaba y se usaba igual.
La regla dice otra cosa —"Enable Valkey pub/sub **transport**"— y el operador eligió la
lectura literal: **con el flag apagado el transporte Valkey no se usa, aunque haya un
Valkey vivo contestando**. Que un servidor esté alcanzable no es consentimiento.

El gate va en `_resolve_valkey_url()`, el punto único por donde deciden los tres
consumidores del transporte (`is_valkey_available`, `AgentPublisher._connect`,
`OrchestratorSubscriber._connect`). No se tocó `is_valkey_available` por separado: eso
habría dejado los otros dos caminos abiertos.

Esto **extiende** el arreglo anterior, no lo reemplaza. Los gates dentro de
`_ensure_valkey_via_smart_infra()` siguen ahí —ahora delegando la precedencia en la
misma función— porque esa función también se llama directo.

## Tabla de precedencia de los tres controles

Un orden lineal, sin segundo eje. Gana el primero que aplica; ningún control posterior
revive el transporte.

| # | Control | Valor | Efecto | Vence a |
|---|---------|-------|--------|---------|
| 1 | `COS_AGENT_BUS_FORCE_FALLBACK` | `1` | Transporte de filesystem, siempre. Ni sondeo ni aprovisionamiento. | todo |
| 2 | `AGENT_BUS_ENABLED` | apagado / ausente (**default**) | Transporte de filesystem. Ni sondeo (ni el primario ni el daemon local de ADR-042) ni aprovisionamiento. | la URL explícita |
| 3 | URL explícita (`VALKEY_URL`, `COS_VALKEY_URL`, `--url`, `valkey_url=`) | cualquiera | Elige **cuál** servidor, nunca **si**. Sólo se consulta con (1) ausente y (2) encendido. | nada |
| — | `AGENT_BUS_ENABLED=true` sin (1) | | Sondea primario → daemon local 6380/6379 → `smart_infra` (Docker) → filesystem. Idéntico a antes. | |

La función `valkey_transport_disabled_reason(primary_url=None)` **es** esa tabla en
código: devuelve el motivo del primer control que aplica, o `None`. Ambos gates
(`_resolve_valkey_url` y `_ensure_valkey_via_smart_infra`) la llaman, así que la
precedencia no está escrita dos veces y no puede divergir.

## El `--url` explícito: gana el flag, y falla ruidosamente

**Decisión: (b).** El flag gana; la URL explícita no es opt-in; el dashboard **se niega
a arrancar** y nombra el motivo. Tres razones, en orden de peso:

1. **La opción (a) no es implementable sin ambigüedad en este código.** "Explícito" no
   es observable en `_resolve_valkey_url`. El `--url` del dashboard tiene
   `default=_DEFAULT_VALKEY_URL` (`agent_dashboard.py:233-237`), y dos llamadores
   internos —`cos_lib/agent_bus_metrics.py:229` y `cos_lib/agent_output_to_bus.py:60`—
   reenvían un atributo que vale el default como *keyword argument*. Con (a), esos dos
   parecerían opt-in explícito **siempre**, y la lectura estricta quedaría anulada por
   código interno que nadie tipeó. La heurística "difiere del default" tampoco cierra:
   `--url redis://localhost:6379` —la cadena que el propio `--help` muestra como
   ejemplo— contaría como no-explícita.
2. **(a) crea un segundo eje de precedencia.** Si la URL explícita vence al flag y
   force-fallback también, ¿qué hace `--url` + force-fallback? Tres controles ya son
   muchos; agregar una excepción que hay que desempatar es peor que uno mal.
3. **La ruidosidad se consigue donde importa.** El dashboard es la única superficie
   donde una persona mira el bus creyendo ver Valkey; ahí sale un error que nombra el
   flag y sale con **exit 2** (el `exit 1` preexistente sigue siendo "Valkey no
   contesta", que ahora es un caso distinto y distinguible).

Fuera del dashboard, `_resolve_valkey_url` emite `logger.warning` cuando la URL recibida
difiere del default, y `logger.debug` cuando no. **La heurística sólo sube el volumen,
nunca cambia el resultado** — un warning de más no rompe nada; un control de más sí.

Lo que un publisher hace con el flag apagado no es un no-op: cae al transporte de
filesystem, que es el diseño documentado y **sigue entregando** (ver round-trip abajo).

### El dashboard, antes y después

Antes (código viejo, flag apagado, `--url redis://valkey.example:6379`), con el módulo
viejo cargado de verdad —verificado con `ab.__file__` y
`hasattr(ab,'valkey_transport_disabled_reason') == False`—:

```
ERROR: Valkey is not available at redis://valkey.example:6379
Start Valkey/Redis and try again.
exit=1
```

Culpa a la alcanzabilidad, que es falso: el motivo era la política. Y con un Valkey
**alcanzable** y el flag apagado, el código viejo se conectaba y mostraba el bus de
Valkey — el flag simplemente no existía para ese camino.

Después:

```
ERROR: the Valkey transport is disabled, so --url redis://valkey.example:6379 is ignored.
  Reason: AGENT_BUS_ENABLED is off (default); the Valkey transport is disabled, so a running
  Valkey is not used -- the explicit URL redis://valkey.example:6379 is not an opt-in
  (export AGENT_BUS_ENABLED=true to enable it)
  Agents are still exchanging messages over the file transport
  under .cognitive-os/agent-bus/ -- this dashboard cannot show those.
exit=2
```

## El sondeo del daemon local (ADR-042): se corta, y nada de producción dependía de él

ADR-042 §5 define la cadena `_resolve_valkey_url`: primario → daemon local
`6380`→`6379` → Docker → filesystem. Bajo la lectura estricta, **toda** la cadena queda
gateada, sondeo incluido. No hay media lectura coherente: si sondear y conectar está
bien con el flag apagado, el flag no gatea el transporte.

Verificación de si algo dependía del sondeo con el flag apagado:

```
$ git grep -ln "valkey-health"
hooks/valkey-ensure.sh
scripts/cos-valkey-local.sh
packages/agent-coordination/lib/agent_bus.py
tests/integration/test_valkey_local_daemon.py
docs/...  (2 reportes)

$ git grep -ln "local-daemon-hit"
packages/agent-coordination/lib/agent_bus.py
docs/06-Daily/reports/juez-interno-comunicacion-2026-08-15.md
```

- El único efecto observable del sondeo es `_emit_local_daemon_metric()` →
  `valkey-health.jsonl` con `event_type: local-daemon-hit`. **Ningún código lo lee**:
  los otros dos escritores (`hooks/valkey-ensure.sh`, `scripts/cos-valkey-local.sh`)
  son bash independiente que escribe sus propios eventos con su propio `source`, y no
  consume los de `agent_bus`.
- **Un consumidor real, y es un test:**
  `tests/integration/test_valkey_local_daemon.py::TestAgentBusIntegration::test_resolve_valkey_url_finds_local_daemon`
  llamaba a `ab._resolve_valkey_url(url)` contra un daemon vivo sin encender el flag.
  Con el cambio devolvería `None` y el test fallaría. Se le agregó el opt-in explícito,
  porque lo que asegura —el descubrimiento de ADR-042— ahora es opt-in, no automático.
  **En esta máquina el módulo entero se saltea** (`pytestmark skipif`: no hay
  `redis-server` ni `valkey-server`; `command -v` devuelve vacío), así que la rotura no
  habría aparecido acá y sí en una máquina con Homebrew redis. Se arregló igual.
- `packages/skill-governance/hooks/agent-bus-monitor.sh:12` ya exigía
  `AGENT_BUS_ENABLED=true` para hacer cualquier cosa: coherente con el cambio, no
  afectado.

## Los tests contra el código anterior

Extraído con `git archive HEAD` (no `git worktree`, bloqueado por ADR-055b), con el
archivo de tests nuevo copiado encima. Sin costuras agregadas: `_bus_env` y
`_reset_valkey_provision_cache` ya existían en `HEAD`.

```
$ cd <scratchpad>/old-agent-bus && PYTEST_ALLOW_NONVENV=1 <repo>/.venv/bin/pytest \
    tests/unit/test_agent_bus.py -q -p no:cacheprovider \
    -k "TestValkeyTransportGate or TestValkeyTransportDisabledReason"
10 failed, 8 passed, 99 deselected
```

Contra el código nuevo: `117 passed` en `tests/unit/test_agent_bus.py`.

**Los 10 que fallan, por tipo de falla** (la distinción importa: no todas muerden igual):

| Tipo | N | Tests |
|------|---|-------|
| Falla de **conducta** — el código viejo sondea/usa Valkey con el flag apagado | 6 | `test_no_probe_when_flag_off`, `test_no_probe_with_explicit_url_when_flag_off`, `test_local_daemon_not_probed_when_flag_off`, `test_is_valkey_available_false_when_flag_off_and_server_reachable`, `test_publisher_uses_file_transport_when_flag_off`, `test_subscriber_uses_file_transport_when_flag_off` |
| Falla por **símbolo ausente** (`ImportError: valkey_transport_disabled_reason`) | 4 | los 4 de `TestValkeyTransportDisabledReason` |

Los 6 primeros son la prueba de que el cambio existe: asertan sobre un **espía de
`_ping_url`** —la llamada observable "¿intentamos hablar con Valkey?"— y no sobre texto
de log, que se puede silenciar sin arreglar nada. El código viejo los rompe con
`assert [call('redis://localhost:6379')] == []`: sondeó.

Los 4 de `ImportError` valen menos como prueba y lo digo: fallan porque el símbolo no
existe, no porque la conducta difiera. Están para fijar la **precedencia** de forma
observable (`test_force_fallback_reported_before_the_flag`), no para demostrar el cambio.

**Los 8 que pasan en las dos versiones** —y tienen que pasar en las dos, o el arreglo
habría roto la función:

| Test | Por qué pasa en ambas |
|------|----------------------|
| `test_probe_happens_when_flag_on` | con el flag encendido se sondea, antes y ahora |
| `test_local_daemon_probed_when_flag_on` | ADR-042: 6380 se sigue alcanzando cuando el primario está muerto |
| `test_is_valkey_available_true_when_flag_on` | reverso de la función |
| `test_publisher_uses_valkey_when_flag_on` | el transporte sigue usándose |
| `test_subscriber_uses_valkey_when_flag_on` | ídem |
| `test_force_fallback_beats_flag_on` | `02c76ae94` ya cortaba la resolución de URL con force-fallback |
| `test_force_fallback_beats_explicit_url` | ídem |
| `test_bus_still_delivers_when_flag_off` | **el criterio no negociable**: el bus entregaba antes y entrega ahora |

Los 5 tests preexistentes que ejercían el camino de Valkey sin encender el flag
(`TestIsValkeyAvailable::test_available_returns_true` y los 4 de
`TestSmartInfraIntegration`) pasaron a declarar `AGENT_BUS_ENABLED=true`. No es
maquillaje: prueban el transporte Valkey, y el transporte Valkey ahora requiere opt-in.
Se dejó el comentario explicando por qué en cada uno.

Suites completas sobre el código nuevo:

```
$ .venv/bin/pytest tests/unit/test_agent_bus.py tests/integration/test_valkey_local_daemon.py \
    tests/integration/test_orchestrator_cli.py tests/chaos/test_agent_bus_monitor_exercised.py -q
139 passed, 10 skipped in 6.38s
```

## El criterio no negociable: el round-trip

Script del encargo, sin modificar. `poll_control()` tiene que seguir dando `pause`.

| Escenario | Salida |
|-----------|--------|
| **Antes** (código viejo, flag apagado) | `AgentPublisher(r): Valkey unavailable, using file fallback` / `poll_control() -> pause` |
| **Después** (flag apagado) | `agent_bus: Valkey transport not used -- AGENT_BUS_ENABLED is off (default)…` / `AgentPublisher(r): Valkey unavailable, using file fallback` / `poll_control() -> pause` |
| **Después** (`AGENT_BUS_ENABLED=true`) | `docker compose up failed for valkey: …` / `poll_control() -> pause` |
| **Después** (`AGENT_BUS_ENABLED=true COS_AGENT_BUS_FORCE_FALLBACK=1`) | `agent_bus: Valkey transport not used -- COS_AGENT_BUS_FORCE_FALLBACK=1 pins the filesystem transport…` / `poll_control() -> pause` |

Entrega intacta en los cuatro. El caso con el flag encendido sigue intentando Docker —
correcto: es lo que el operador pidió al encenderlo. El warning con URL explícita
aparece porque el script del encargo pasa `redis://127.0.0.1:1`, que difiere del
default; es exactamente el aviso que se quería que exista.

## Diff propuesto para la regla (NO aplicado — `rules/**` es config protegida)

Con este cambio el texto de la regla —"Valkey pub/sub when `AGENT_BUS_ENABLED=true`",
"Enable Valkey pub/sub transport"— **pasa a ser cierto por primera vez**. Antes era
falso en dos escalones: antes de `02c76ae94` ningún Python leía el flag, y después de
`02c76ae94` el flag gobernaba el aprovisionamiento pero no el transporte. Las dos líneas
de arriba quedan como están.

Lo que falta en la regla es la **precedencia de los tres controles**, que hoy no
menciona. Archivo: `packages/agent-coordination/rules/agent-communication.md`.

```diff
@@ ## Activation
 Valkey is **OFF by default**. Enable it only for profiles that provision Valkey:

 ```bash
 export AGENT_BUS_ENABLED=true
 ```

+The flag gates the **transport**, not just provisioning: with it off the bus neither
+starts Valkey nor connects to one that is already running. A reachable server is not
+consent.
+
+Three controls govern the same decision. Precedence is a single linear order — the
+first one that applies wins, and nothing later revives the transport:
+
+| # | Control | Effect |
+|---|---------|--------|
+| 1 | `COS_AGENT_BUS_FORCE_FALLBACK=1` | Filesystem transport, always. Beats everything. |
+| 2 | `AGENT_BUS_ENABLED` off (default) | Filesystem transport. No probing (including the ADR-042 local daemon on 6380/6379), no provisioning. Beats an explicit URL. |
+| 3 | Explicit URL (`VALKEY_URL`, `COS_VALKEY_URL`, `--url`, `valkey_url=`) | Chooses *which* server, never *whether*. Consulted only when (1) is unset and (2) is on. |
+
+`valkey_transport_disabled_reason()` in `agent_bus.py` is this table in code; both gates
+call it, so the order cannot drift between them.
+
 When Valkey is disabled, control and clarification paths still write durable fallback
 artifacts. They are not silent no-ops unless both Valkey and filesystem I/O fail.

@@ ## Configuration
 | Variable | Default | Description |
 |----------|---------|-------------|
-| `AGENT_BUS_ENABLED` | `false` | Enable Valkey pub/sub transport. |
+| `AGENT_BUS_ENABLED` | `false` | Enable the Valkey pub/sub transport. Read by `_agent_bus_enabled()` in `agent_bus.py`; gates probing, connecting and provisioning. |
+| `COS_AGENT_BUS_FORCE_FALLBACK` | unset | `1` pins the filesystem transport; beats `AGENT_BUS_ENABLED`. |
 | `VALKEY_HOST` | `localhost` | Valkey server host. |
 | `VALKEY_PORT` | `6379` | Valkey server port. |

@@ ## Running the Dashboard
 ```bash
 python cos_lib/agent_dashboard.py
 python cos_lib/agent_dashboard.py --url redis://valkey:6379
 python cos_lib/agent_dashboard.py --refresh 2
 ```
+
+`--url` selects a server; it is not an opt-in to the transport. With
+`AGENT_BUS_ENABLED` off the dashboard **exits 2** naming the flag instead of quietly
+showing something other than the Valkey bus (`exit 1` still means "Valkey unreachable").
```

## Correcciones a las premisas del encargo

Lo que se recontó y **se confirmó**:

- `cos_lib/agent_bus.py` **es** un symlink a `packages/agent-coordination/lib/agent_bus.py`
  (`ls -la`). Se editó el real.
- `02c76ae94` existe, dice lo que el encargo dice, y su alcance declarado es
  "el flag gatea el aprovisionamiento, no el transporte". El arreglo anterior está bien
  hecho: este cambio lo extiende y reusa sus gates.
- Las dos consecuencias identificadas **existen las dos**. La del daemon local se
  verificó y se cortó a conciencia (arriba). La del `--url` se verificó y se resolvió
  con falla ruidosa.
- `git worktree` bloqueado por ADR-055b: no se probó el bloqueo, se obedeció usando
  `git archive`, que alcanzó. Restricción no verificada — la declaro como tal.
- El método del agente anterior (13 fallados / 8 pasados) se replicó con 10/8. Los 8
  que pasan son, igual que allá, exactamente los del camino inverso.

Lo que **no se sostuvo**:

1. **"El anterior obtuvo 13 fallados / 8 pasados"** — cierto, pero no es una barra
   comparable: 13 y 8 salían de 21 tests sobre el aprovisionamiento; acá son 18 tests
   sobre el transporte. Igualar el número habría sido inventar tests. Lo que se replicó
   es el **método** (espía de la llamada, corrida contra el código viejo), no la cifra.
2. **"El anterior afirmó que `AGENT_BUS_ENABLED` no lo lee nadie cuando un hook en bash
   sí lo lee"** — el encargo se autocorrige bien, pero se queda corto en la otra
   dirección: ese hook, `packages/skill-governance/hooks/agent-bus-monitor.sh`, **no está
   registrado** en `.claude/settings.json` (`grep -c 'agent-bus-monitor' .claude/settings.json`
   → `0`). O sea que el único lector del flag fuera de Python es un hook que no corre.
   Está clasificado como no-registrado a propósito en
   `manifests/hook-registration-classification.yaml:57`, así que no es un olvido; pero
   "un hook lo lee" describe un archivo, no un control activo.
3. **Trampa de método que casi entra al informe**: la primera corrida del dashboard
   "antes" cargó el módulo **nuevo** desde el venv del repo (editable install) y produjo
   una salida que parecía evidencia del código viejo. Se detectó imprimiendo
   `ab.__file__` y `hasattr(ab, 'valkey_transport_disabled_reason')`, y se rehizo con
   `sys.path` forzado al directorio del `git archive`. La corrida de pytest contra el
   código viejo nunca tuvo el problema, porque el propio archivo de tests hace
   `sys.path.insert(0, <root del archive>)`. Si alguien reproduce el "antes", que
   verifique `__file__` primero.
4. **`~40 tool calls`** — se usaron ~28. No es corrección de un error, es que el
   presupuesto estaba holgado.
</content>

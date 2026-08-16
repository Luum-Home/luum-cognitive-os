# El bus de agentes dejaba de entregar mensajes para arrancar Docker

**Fecha:** 2026-08-15
**Alcance:** `packages/agent-coordination/lib/agent_bus.py` (expuesto como `cos_lib/agent_bus.py` vía symlink), `tests/unit/test_agent_bus.py`
**Estado:** arreglado, con tests que fallan sobre el código viejo

## El síntoma

Construir un `AgentPublisher` disparaba un `docker compose up` que fallaba. El bus
entregaba bien igual — el costo no era el mensaje de error, era el subproceso.

## Los tres defectos

### 1. `AGENT_BUS_ENABLED` no lo leía ningún código Python (causa raíz)

`packages/agent-coordination/rules/agent-communication.md` dice que Valkey está
apagado por default y se enciende con esa variable. El censo:

```
$ git grep -n AGENT_BUS_ENABLED -- '*.py'
packages/agent-coordination/lib/agent_dashboard.py:121:   # solo la imprime en un mensaje de ayuda
tests/chaos/_tier_b_helpers.py:48
tests/chaos/test_agent_bus_monitor_exercised.py:7,8,37,53,72
```

El único consumidor real es `packages/skill-governance/hooks/agent-bus-monitor.sh:12`,
que sí la respeta. `agent_bus.py` no la mencionaba nunca: aprovisionaba un servicio
que la política declara apagado.

**Arreglo:** `_agent_bus_enabled()` lee la variable (acepta `1/true/yes/on`,
case-insensitive, con trim) y actúa como gate del aprovisionamiento.

### 2. `COS_AGENT_BUS_FORCE_FALLBACK=1` no evitaba el intento de Docker

Confirmado. En `_resolve_valkey_url` (línea 138 del original) la variable devolvía
`None` de entrada, pero `is_valkey_available` llamaba a
`_ensure_valkey_via_smart_infra()` igual, justo después (líneas 204-208). El
interruptor documentado que dice "forzá el fallback" seguía arrancando Docker.

**Arreglo:** el chequeo se movió *adentro* de `_ensure_valkey_via_smart_infra()`,
que es el único punto por donde pasa el aprovisionamiento. Ahora force-fallback le
gana a `AGENT_BUS_ENABLED=true`.

### 3. Sin memoización

Confirmado: tres call sites (`is_valkey_available`, `AgentPublisher._connect`,
`OrchestratorSubscriber._connect`). Un `docker compose up` que falló una vez vuelve
a fallar en el mismo proceso.

**Arreglo:** `_VALKEY_PROVISION_ATTEMPTED` cachea el resultado por vida del proceso.
`_reset_valkey_provision_cache()` existe como costura de test, porque el entorno
cambia dentro de un mismo proceso en pytest.

Los tres gates viven en una sola función, así que los tres call sites quedan
cubiertos sin tocar ninguno.

## El round-trip, antes y después

Script: dos instancias, `pause` y `resume`, entrega por el camino de filesystem.

**Antes**

```
docker compose up failed for valkey: network cognitive-os-network declared as external, but could not be found
AgentPublisher(receptor): Valkey unavailable, using file fallback
poll_control() -> pause
poll_control() -> resume
```

**Después (default, flag apagado)**

```
AgentPublisher(receptor): Valkey unavailable, using file fallback
poll_control() -> pause
poll_control() -> resume
```

**Después (`COS_AGENT_BUS_FORCE_FALLBACK=1`)**

```
AgentPublisher(receptor): Valkey unavailable, using file fallback
poll_control() -> pause
poll_control() -> resume
```

Entrega intacta, cero intentos de Docker. El aviso de fallback sigue ahí a
propósito: bajarlo a `debug` habría sido apagar la luz, no el problema.

## El reverso: con Valkey encendido tiene que seguir intentando

**Después (`AGENT_BUS_ENABLED=true`)**

```
docker compose up failed for valkey: network cognitive-os-network declared as external, but could not be found
AgentPublisher(receptor): Valkey unavailable, using file fallback
poll_control() -> pause
poll_control() -> resume
```

El intento vuelve. Idéntico al comportamiento viejo, que es lo que corresponde.

## Prueba de que los tests sirven

Un test que pasa con el código viejo y con el nuevo no prueba nada. Se exportó
`HEAD` con `git archive` (no worktree: `git worktree` está bloqueado por ADR-055b),
se le agregó **solo** la costura `_reset_valkey_provision_cache` como no-op —lógica
intacta— y se corrió la clase nueva contra el código viejo:

```
13 failed, 8 passed
```

Los 8 que pasan son exactamente los del camino inverso
(`test_provisioning_attempted_when_agent_bus_enabled[*]`,
`test_provisioning_returns_true_when_service_starts`,
`test_publisher_provisions_when_enabled`). Tienen que pasar sobre el código viejo,
porque el código viejo siempre aprovisionaba. Que pasen antes y después es la firma
de que el arreglo no rompió la función.

Suite completa sobre el código nuevo:

```
$ .venv/bin/pytest tests/unit/test_agent_bus.py -q
99 passed in 5.01s

$ .venv/bin/pytest tests/integration/test_orchestrator_cli.py -q
18 passed in 1.10s

$ .venv/bin/pytest tests/chaos/test_agent_bus_monitor_exercised.py -q
4 passed in 1.23s
```

Las 21 pruebas nuevas asertan sobre un espía de `smart_infra.ensure_service`, no
sobre texto de log: la pregunta es si `docker compose` se habría invocado.

## Un test que había dejado de probar lo que decía

`test_ensure_valkey_via_smart_infra_graceful_on_import_error` llama a la función
real con `cos_lib.smart_infra` parcheado a `None` y asertaba `result is False`. Con
el gate nuevo, la función corta antes del import y el test pasaba sin tocar nunca el
camino de error que dice cubrir — verde por el motivo equivocado. Se le agregó
`AGENT_BUS_ENABLED=true` para que siga ejerciendo el import.

## Decisión de alcance: el flag gatea el aprovisionamiento, no el transporte

`AGENT_BUS_ENABLED` podía leerse de dos maneras.

La lectura literal de la regla ("Enable Valkey pub/sub transport") sería: con el flag
apagado, no usar Valkey para nada. Se descartó. Sondear un Valkey ya corriendo es
read-only, cuesta un connect a localhost y no tiene efectos; matarlo dejaría sin
efecto el camino de daemon local de ADR-042 y volvería no-op el `--url redis://...`
del dashboard, sin que nadie lo haya pedido.

Lo que se gatea es el efecto que la política prohíbe: **levantar el servicio**. Queda
una diferencia de redacción entre regla y código, y por eso va el diff de abajo.

## Diff propuesto para la regla (NO aplicado — `rules/**` es config protegida)

Archivo: `packages/agent-coordination/rules/agent-communication.md`

```diff
@@ Overview @@
-1. **Valkey pub/sub** when `AGENT_BUS_ENABLED=true`.
+1. **Valkey pub/sub** when a Valkey server is reachable. `AGENT_BUS_ENABLED=true`
+   is what authorises the bus to *start* one; with the flag off, an
+   already-running server is still used, but nothing is provisioned.
 2. **Filesystem fallback** under `.cognitive-os/agent-bus/{agent_id}/` when Valkey is disabled or unavailable.

@@ Activation @@
-Valkey is **OFF by default**. Enable it only for profiles that provision Valkey:
+Valkey provisioning is **OFF by default**: with `AGENT_BUS_ENABLED` unset, the bus
+never runs `docker compose`. Enable it only for profiles that provision Valkey:

 ```bash
 export AGENT_BUS_ENABLED=true
 ```

+`COS_AGENT_BUS_FORCE_FALLBACK=1` overrides `AGENT_BUS_ENABLED` and pins the
+filesystem transport: no probing, no provisioning.
+
 When Valkey is disabled, control and clarification paths still write durable fallback artifacts.

@@ Configuration @@
 | Variable | Default | Description |
 |----------|---------|-------------|
-| `AGENT_BUS_ENABLED` | `false` | Enable Valkey pub/sub transport. |
+| `AGENT_BUS_ENABLED` | `false` | Authorise the bus to provision Valkey (Docker). Read by `_agent_bus_enabled()` in `agent_bus.py`. |
+| `COS_AGENT_BUS_FORCE_FALLBACK` | unset | `1` pins the filesystem transport; beats `AGENT_BUS_ENABLED`. |
 | `VALKEY_HOST` | `localhost` | Valkey server host. |
 | `VALKEY_PORT` | `6379` | Valkey server port. |
```

La contradicción doc-vs-código de fondo ya está cerrada del lado que importa: el
código ahora lee el flag. Este diff es para que la regla describa el alcance exacto.

## Correcciones a las premisas del encargo

- **"imprimió dos veces" — mal atribuido.** El mensaje sale **una vez por
  construcción de publisher/subscriber**, no dos veces por round-trip. El encargo
  contaba dos porque su script creaba dos instancias; el script que trae el propio
  encargo crea una sola y, medido, imprime una sola vez. El defecto es real; el
  factor 2 era del escenario, no del código.
- **Números de línea: confirmados.** `_ensure_valkey_via_smart_infra` en 100,
  `_resolve_valkey_url` en 126 con el check de force-fallback en 138,
  `is_valkey_available` en 190 con la llamada a Docker en 208. Los otros dos call
  sites en 334 y 754. Los cinco verificados con `git grep -n`.
- **Defecto 1: confirmado, con matiz.** El encargo dice "no lo lee el código en
  ninguna parte". Falso en sentido estricto: `hooks/agent-bus-monitor.sh:12` sí lo
  lee y respeta. Lo correcto es que **ningún código Python** lo leía. No cambia el
  diagnóstico ni el arreglo.
- **Defectos 2 y 3: confirmados sin correcciones.**
- **"El archivo es `cos_lib/agent_bus.py`" — es un symlink.** Apunta a
  `packages/agent-coordination/lib/agent_bus.py`. Editar por la ruta del symlink
  habría funcionado, pero el canónico es el del paquete y ahí se editó.
- **Restricción verificada, no asumida:** el encargo prohíbe `hooks/**` y `rules/**`.
  Se comprobó que la regla vive en `packages/agent-coordination/rules/` y se trató
  igual como protegida: diff propuesto, no aplicado.
- **Restricción que resultó incompleta:** el encargo no menciona que `git worktree`
  está bloqueado por el guard de ADR-055b. Se descubrió al intentarlo. La prueba
  contra el código viejo se hizo con `git archive`, que no muta estado de git.
- **`.cognitive-os/agent-bus/` no se tocó.** Los tests usan `tmp_path`; el script de
  round-trip usa `tempfile.mkdtemp` y limpia.

## Archivos

- `packages/agent-coordination/lib/agent_bus.py` — gates + memoización (+75 líneas)
- `tests/unit/test_agent_bus.py` — clase `TestValkeyProvisioningGates`, 21 tests, y
  el arreglo del test que había dejado de probar (+185 líneas)

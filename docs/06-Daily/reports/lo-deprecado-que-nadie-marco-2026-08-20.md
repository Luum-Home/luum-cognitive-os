<!-- SCOPE: os-only -->
# Lo deprecado que nadie marcó — 2026-08-20

Instrumento: `scripts/dead_content_census.py` (read-only, determinista, exit 0/1/2).

## Resumen ejecutivo

La maquinaria de ciclo de vida cubre **artefactos** (1032 primitivos en
`manifests/primitive-lifecycle.yaml`), no el contenido adentro de ellos: la
hipótesis del encargo se confirma. Pero la conclusión que se sigue no es la
esperada. **La marca no falta por falta de lugar: falta porque el veredicto no
tiene dónde aterrizar.** El repo ya tiene cuatro detectores de estas formas
(`cos_lib/pattern_detector.py`, `cos_lib/component_usage_tracker.py`,
`tests/unit/test_confidentiality_schema_contract.py`, el bloque verificado de
`rules/rate-limiting.md`) y el contenido muerto sobrevivió a todos. Detectar ya
se hace; lo que no existe es el registro del "ya lo miramos, está muerto".

Los números del encargo no se sostienen: **no hay ni un solo campo de fecha de
deprecación** en el repo (`deprecated_at`, `sunset_at`, `removal_after` = 0);
los 680 son 671 `sunset_criteria`, que es **prosa libre, no fecha**, y ningún
consumidor la evalúa. De 1032 primitivos, **uno** está en un estado que
insinúa retiro.

Por qué un agente no lo nota: no es que lea para responder. Es que **el
contenido muerto responde, y responde que sí**, y la propiedad que lo delata
—ser constante— sólo existe en la población, no en el registro que uno lee.

## Correcciones a las premisas del encargo

1. **"680 líneas con campos de fecha de deprecación" — falso, y la palabra que
   falla es "fecha".** `deprecated_at`, `deprecated_on`, `sunset_at`,
   `removal_after`, `remove_after`, `retired_at`, `deprecation_date`,
   `eol_date`: **0 ocurrencias cada uno** en todo el repo. Los 680 son
   `sunset_criteria` (671, todas en `primitive-lifecycle.yaml`), que es prosa:
   *"Remove when destructive blockers no longer share agent-context detection"*.
   No es comparable con una fecha, y nada la compara.
   ```bash
   grep -c 'sunset_criteria' manifests/primitive-lifecycle.yaml   # 671
   grep -rIn --exclude-dir=.git -E '\b(deprecated_at|sunset_at|removal_after)\b' . | wc -l   # 0
   ```

2. **`templates/security-profiles/paranoid.json` NO registra un hook borrado.**
   Escaneé las 164 referencias `.sh`/`.py` de los tres perfiles resolviendo
   symlinks: **0 inexistentes** en `minimal`, `paranoid` y `standard`. Si el
   caso existió, ya se cerró; a HEAD de hoy no reproduce.

3. **`CONFIG_FILE` en `scripts/_lib/settings-driver-claude-code.sh` ya fue
   removido, hoy, por otra sesión.** El archivo (33 KB, no 384 líneas) conserva
   dos comentarios que documentan la remoción (líneas 9 y 101: *"No CONFIG_FILE
   here on purpose"*). El caso es real como historia, no como estado.

4. **`.cognitive-os/edit-locks/` no existe; los locks viven en
   `.cognitive-os/runtime/edit-locks/` y son 45, no 1321.** Son directorios con
   un `meta.yaml` adentro, no archivos. El conteo de 1321 corresponde a otro
   momento o a otra ruta.

5. **`status: "active"` no es el único campo sin información en ese lock: son
   diez de quince.** El censo encuentra además `agent_id`, `agent_role`,
   `allows_concurrent_read`, `intent`, `on_conflict_other_agent_should`,
   `purpose`, `related_adr`, `related_files` y `worktree`. El encargo subestimó
   su propio hallazgo por un factor de diez.

6. **Mis propios números pasaron por dos correcciones antes de este informe**, y
   las dejo escritas porque son la tasa de error de la herramienta: una versión
   del censo reportó **400** variables write-only (regex de lectura que exigía
   llave: `${VAR}` sí, `$VAR` no) y otra reportó **0** referencias colgantes
   (filtro que exigía extensión, y las dos entradas rotas son justamente
   extensionless). Los números buenos son 8 y 3.

7. **Refutación parcial a la tesis "derivar, no declarar" del coordinador:** no
   encontré contenido no-derivable, así que su punto 1 queda en pie. Pero su
   punto 3 —"el cuello de botella es decidir, no detectar"— **está medido y es
   el correcto**: ver la sección de por qué un agente lo toma por vivo.

## Qué puede marcarse hoy y quién lee esas marcas

| Mecanismo | Qué unidad marca | Cuántas marcadas | Quién lee la marca para hacer algo |
|---|---|---|---|
| `manifests/primitive-lifecycle.yaml` · `lifecycle_state` | artefacto (hook, script, skill, lib) | **1** de 1032 (`pending-sunset`: `scripts/cos-agent-message`) | `scripts/primitive_lifecycle.py` valida coherencia con `maturity`; ningún consumidor actúa sobre `pending-sunset` salvo un test que verifica que la fila diga eso |
| idem · `sunset_criteria` | artefacto | 671 (prosa) | `primitive_lifecycle.py:177` verifica **que el campo exista**, no qué dice. `cos_demotion_loop_audit.py:73` lo usa como texto de fallback para un motivo. Nadie lo evalúa |
| idem · estados inactivos (`demoted`/`archived`/`deleted`) | artefacto | **0** | `INACTIVE_STATES` está definido en `primitive_lifecycle.py:67` y ningún primitivo está en ninguno de los tres |
| skill `adr-tombstone` | ADR completo | 19 tombstones sobre ~575 ADRs | el propio primitivo, al crear/reparar |
| `status:` de ADR | ADR completo | 7 `superseded` | lectores humanos y auditorías de doc-truth |

**Lectura:** el único eslabón que llega a "hacer algo" es el tombstone de ADR. El
resto son campos que se validan por presencia. `sunset_criteria` es, ella misma,
la forma que estamos censando un nivel más arriba: 671 declaraciones que nadie
evalúa.

**Qué NO puede marcarse, y por eso la hipótesis del encargo se confirma:** un
campo adentro de un `meta.yaml`, una clave adentro de un perfil, una asignación
adentro de un script, una entrada adentro de un manifiesto. La unidad mínima
declarable es el archivo. El `id` de un primitivo es un path.

Una excepción parcial que vale registrar: dos entradas del manifiesto usan
anclas (`packages/agent-coordination/lib/agent_bus.py#filesystem-interrupt`,
`packages/agent-lifecycle/lib/harness_adapter/base.py#inbound-signal`). Alguien
ya necesitó granularidad sub-artefacto y la improvisó con un `#`. Nada valida
que el ancla exista.

## Contenido deprecado sin marcar: las formas, con casos y conteos

Reproducible: `python3 scripts/dead_content_census.py`

### Forma A — campo de un solo valor en toda su población: **10**

`.cognitive-os/runtime/edit-locks/**/meta.yaml`, 45 registros, 15 campos.
Diez tienen un único valor distinto en los 45: `agent_id` (`"unknown-agent"`),
`agent_role` (`"orchestrator"`), `allows_concurrent_read` (`true`), `intent`
(`"exclusive-edit"`), `on_conflict_other_agent_should` (`"park"`), `purpose`
(`"tool-edit"`), `related_adr` (`""`), `related_files` (`[]`), `status`
(`"active"`), `worktree`. Cinco campos varían: `session_id`, `pid`,
`target_file`, `since`/`heartbeat`, `expires_at`.

```bash
python3 scripts/dead_content_census.py --form A --path .cognitive-os/runtime/edit-locks
```

Umbral: 20 registros mínimo. Debajo de eso, "un solo valor" es azar.

### Forma B — entrada de manifiesto que apunta a un archivo inexistente: **3, de las cuales 2 confirmadas**

- `manifests/primitive-lifecycle.yaml:13219` → `scripts/cos-doctor-preserve`.
  El archivo real es `scripts/cos-doctor-preserve.sh`. Verificado con
  `readlink -f` y `ls`: no hay symlink.
- `manifests/primitive-lifecycle.yaml:17006` → `scripts/cos_primitive_harvester`.
  El archivo real es `scripts/cos_primitive_harvester.py`.
- `manifests/hook-vitality-budget.yaml:2` → `governance/hook-vitality`.
  **Probable falso positivo**: parece un namespace lógico, no un path. Lo dejo
  reportado sin corregir, como corresponde a una hipótesis.

Sobre 1032 `id:` del manifiesto de ciclo de vida, 2 apuntan a nada. **Ningún
chequeo de existencia corre sobre esos ids**: `grep -n 'exists()' scripts/primitive_lifecycle.py`
no devuelve nada.

### Forma C — variable de shell asignada y nunca leída: **8** en `hooks/_lib` + `scripts/_lib`

`_PORTABLE_DATE_BSD` (`portable.sh:35`, asignada 2×), `disable_val`
(`push-collision-check.sh:46`), `_REM_GC_STALE_DAYS` (`remediation.sh:30`),
`last_epoch` (`remediation.sh:454`), `_FLOCK_TIMEOUT` (`safe-jsonl.sh:30`),
`_HOOK_START_EPOCH` (`safe-jsonl.sh:41`), `matches` (`semantic-search.sh:64`),
`acquired` (`stash-lock.sh:228`, asignada 2×).

El alcance de lectura no es uniforme y tratarlo como uniforme fabrica falsos
positivos: `hooks/_lib/tool-outcome.sh` asigna `TOOL_EXIT_CODE` para que lo lea
quien la sourcea (`hooks/error-learning.sh:24`). Por eso el censo busca las
MAYÚSCULAS en todo el repo y las minúsculas sólo en su archivo.

### Forma D — clave leída que nadie escribe: **1 verificada**

`opencode_projection`: `scripts/hook_projection_drift_audit.py:98` la declara en
`PROJECTION_FLAG` y `scripts/hook_surface_census.py:195` la consume; ningún
escritor la produce. No la incorporé al censo automatizado porque el cruce
declarante/consumidor lo cubre `scripts/config_knob_census.py`, que pertenece a
otro agente de esta sesión.

## Por qué un agente lo toma por vivo

La respuesta de la orquestación —*"leo para responder, no para inventariar"*— es
verdadera pero no es el mecanismo. Si lo fuera, el problema se arreglaría leyendo
más, y hoy hay evidencia de que leer más no alcanza. Propongo dos mecanismos, y
el segundo es el que importa.

**1. El contenido muerto falla en dirección afirmativa.** `status: "active"` no
es silencio: es una confirmación. Un agente que pregunta "¿este lock está vivo?"
recibe un sí. No para en la primera coincidencia por pereza: para porque la
coincidencia contestó. Un campo constante es una función que siempre devuelve el
mismo valor haciéndose pasar por una medición. Comparar: si el campo dijera
`status: ""` el lector miraría dos veces.

**2. La propiedad que delata la muerte no está en el artefacto que uno lee.**
Esto es lo estructural. `status: "active"` en *un* lock es información legítima.
Es cero información **a través de los 45**. Un agente abre un archivo; la
deadness vive en la población. No es un defecto de atención: la evidencia
literalmente no está presente en la granularidad a la que alguien lee. Lo mismo
con `CONFIG_FILE` (hace falta el archivo entero), con la entrada colgante (hace
falta el filesystem), con `opencode_projection` (hacen falta los dos lados).

**Y el hallazgo que reordena todo: detectar no era el problema.** El repo ya
tiene la derivación construida, en cuatro lugares independientes:

- `cos_lib/pattern_detector.py:113` — *"Find metadata fields written to SKILL.md
  frontmatter but never read by code"*: la Forma A/D, ya implementada.
- `cos_lib/component_usage_tracker.py:5` — qué componentes *"are never used"*.
- `tests/unit/test_confidentiality_schema_contract.py:65` — *"template declares
  keys the loader never reads"*: la Forma D, con gate.
- `rules/rate-limiting.md` — un bloque verificado que dice que `rate-limiter.sh`
  tiene **0 disparos en 37.424 filas** y no está registrado.

Y además, el caso más incómodo: `scripts/edit-coop.sh` **tiene un comentario que
dice que el campo no se consulta**. Alguien lo detectó, lo escribió, y el campo
siguió ahí. `CONFIG_FILE` se removió hoy y dejó dos comentarios explicando la
remoción — o sea que en ese caso el veredicto sí se ejecutó, pero el registro
que quedó es prosa en el archivo, ilegible para cualquier máquina.

Un `grep -i` de frases tipo *"never read"*, *"no consumer"*, *"nadie lo lee"*
devuelve **643 líneas** en el repo. No todas son hallazgos —muchas son
docstrings de detectores— pero muestran que este repo *sabe*, en prosa, mucho
más de lo que puede evaluar.

**Conclusión sobre la tesis del coordinador:** su punto 1 sobrevive (no encontré
contenido no-derivable). Su punto 3 es el correcto y está medido: el cuello de
botella no es detectar, es que **el veredicto de la derivación no tiene dónde
aterrizar**, y por eso se re-deriva o se escribe en un comentario y se pierde.
De los casos conocidos, al menos tres —`status:"active"`, `rate-limiter.sh` sin
registrar, y `CONFIG_FILE` antes de hoy— eran *"se sabe y nadie lo sacó"*, no
*"no se sabe"*. Las Formas B y C que encontré hoy sí son *"no se sabía"*.

## La marca que propongo, y por qué escala

Regla que se sigue de los dos mecanismos de arriba: **la marca tiene que hacer
que el campo deje de contestar, y tiene que ser visible en el registro que uno
abre.** Agregar un `deprecated_at` al lado no sirve: el lector le preguntó a
`status`, y `status` le sigue diciendo `"active"`. El campo hermano se convierte
en la séptima instancia de la misma forma.

**Tres piezas, en orden de costo creciente. Ninguna toca más de seis lugares.**

**1. Para contenido que muere por decisión (unidades, no miles): el valor lleva
la marca, no un campo hermano.**

```yaml
status: "DEAD:2026-08-20:ADR-064"      # en vez de status: "active"
```

Un lector que grepea `status` no puede confundirlo. Un consumidor que hacía
`== "active"` se rompe, que es exactamente lo que se quiere: si nada se rompe,
el campo estaba muerto y queda probado en el acto. Costo: **un lugar** —el
escritor del campo—, no una entrada por registro. El prefijo `DEAD:` es
grepeable y no requiere parser.

Cuándo se aplica: cuando alguien decide deprecar. El coordinador tiene razón en
que esto son unidades.

**2. Para lo viejo, en bloque y por población: `manifests/dead-content.yaml`.**
Una fila por **población**, no por instancia:

```yaml
- population: ".cognitive-os/runtime/edit-locks/**/meta.yaml"
  dead_fields: [status, agent_id, agent_role, intent, purpose,
                allows_concurrent_read, on_conflict_other_agent_should,
                related_adr, related_files, worktree]
  evidence: "python3 scripts/dead_content_census.py --form A --path .cognitive-os/runtime/edit-locks"
  verdict_date: "2026-08-20"
  decision: "keep-until-writer-changes"   # o remove-next-release
```

Las 52 claves sin lector son **una fila**, no 52. Los 1321 locks son **una
fila**. La estimación de arranque es **seis filas**: locks, claves de config sin
lector, `opencode_projection`, las 2 entradas colgantes, las 8 write-only,
`sunset_criteria`. Está muy por debajo del límite de veinte lugares a mano.

Lo que hace escalar esto no es la brevedad: es que la fila **cita el comando que
la produjo**. La fila no es la verdad, es el veredicto fechado sobre una salida
reproducible. Cuando el censo devuelve algo distinto, la fila está vencida y se
nota.

**3. Para lo demás: derivación, con el veredicto persistido.** El censo
(`scripts/dead_content_census.py`) devuelve exit 1 con hallazgos. Un hallazgo
que ya tiene fila en `dead-content.yaml` con `decision:` escrita deja de ser
ruido; uno que no la tiene es nuevo. **Ése es el aporte real frente a los cuatro
detectores que ya existen y no limpiaron nada**: no detectan menos que esto,
pero no tienen dónde dejar dicho "ya lo miramos".

**Por qué escala, en una línea:** la unidad de marcado es la población y la
unidad de verdad es el comando. Marcar más registros no cuesta más filas, y una
fila que miente se detecta corriendo el comando que ella misma cita.

**Lo que explícitamente NO propongo:** un campo `deprecated_at` en los datos.
Falla por lo que dice el coordinador —el que no mantuvo el campo no va a
mantener el manifiesto— y además por lo mío: un campo hermano no impide que el
campo original siga contestando que sí.

## Lo que NO hice y por qué

- **No corrí la suite.** La máquina está cargada y el encargo pedía censo
  estático. El censo no importa nada del repo y no ejecuta código auditado.
- **No arreglé ninguno de los hallazgos.** Dos entradas colgantes y ocho
  variables write-only son arreglos de una línea cada uno, pero "un hallazgo es
  una hipótesis": las ocho variables necesitan que alguien mire si el consumidor
  está por commitearse. Marcar sin verificar es el verde barato de esta familia.
- **No toqué `scripts/config_knob_census.py`, `state_lifecycle_census.py`,
  `hook_surface_census.py` ni `edit-coop.sh`**: pertenecen a otros agentes de
  esta sesión. La Forma D queda medida con un solo caso verificado en vez de
  reimplementar su cruce.
- **No creé `manifests/dead-content.yaml`.** Es una decisión del operador, y
  crearlo vacío o con filas que yo no verifiqué sería exactamente la marca que
  nadie lee.
- **No busqué exhaustivamente la Forma A fuera de los locks.** El censo sobre
  `templates/`, `manifests/` y `.claude/` devuelve 0, pero el umbral de 20
  registros y el parser YAML plano dejan poblaciones afuera. El conteo de la
  Forma A es un piso, no un total.
- **No conté los 727 write-only del barrido amplio** (`hooks/` + `scripts/`
  completos) como hallazgos: ese número salió de la versión del censo con el
  regex roto. Con el regex corregido el barrido amplio no se volvió a correr por
  presupuesto; los 8 de `_lib` sí están verificados.

# Motores de política y sus decision logs: cómo distinguen "no atrapó nada" de "no puede atrapar"

Fecha: 2026-08-19
Tipo: investigación web (dominio externo), sin cambios de código
Encargo: el sistema tiene ~154 guards; un subconjunto corrió miles de veces sin
bloquear nunca; el instrumento registra `stdout_bytes` y no el contenido, así que
un deny por JSON es indistinguible de un aviso impreso.

---

## Correcciones a las premisas del encargo

Recontado sobre `.cognitive-os/metrics/hook-timing.jsonl` (comandos al final).

**1. "~154 guards" → el instrumento ve 148.**
El JSONL tiene **148 hooks distintos** (17.271 filas al primer conteo, 18.640 quince
minutos después: el archivo crece en vivo, así que la cifra de filas es volátil y la
de hooks distintos no se movió). La diferencia con 154 no la
pude reconciliar dentro del presupuesto de esta tarea. Importa: un hook que existe
en el filesystem y **nunca aparece en telemetría** es una tercera categoría, distinta
de "observer" y de "unproven-guard" — es un guard que ni siquiera se sabe si está
registrado. Los motores de política le dan nombre propio a esa categoría (ver
`auditTimestamp` de Gatekeeper, más abajo).

**2. "35 corrieron miles de veces y nunca bloquearon" → no lo reproduje.**
Con el corte que este archivo permite (`stdout_bytes == 0` **y** `exit_code == 0` en
todas sus corridas) salen **130 hooks silenciosos**, de los cuales **16 con ≥100
corridas**. Ninguno llega a miles: el máximo es 840 (`session-heartbeat`). El 35 debe
venir de otro corte —otra ventana, otro archivo, o filtrado por "tiene camino de
bloqueo en el código", que este JSONL no sabe—. No lo refuto: digo que el archivo que
sí tengo da otras magnitudes, y que la conclusión de la investigación no depende de
cuál de los dos números sea.

**3. "el instrumento solo registra stdout_bytes" → falso en dos direcciones.**
La fila real trae 15 campos:

```json
{"timestamp":"…","event":"PreToolUse","hook":"secret-detector","duration_ms":216,
 "body_duration_ms":189,"execution_status":"ok","exit_code":0,"signal":"",
 "stdout_bytes":0,"stderr_bytes":0,"pid":96528,"session_id":"",
 "session_kind":"orchestrator","skipped":0,"safe_mode":0,"skip_reason":""}
```

Ya existen `skipped` y `skip_reason`. Eso es **exactamente** el tercer valor `skip` de
Kyverno (§P1) — la primitiva que hace falta para separar "no aplicó" de "aplicó y
pasó" está en el schema y está subutilizada, no ausente.

En dirección contraria: `cos_lib/telemetry_aggregator.py:505` afirma que el schema del
hook-timing-wrapper *"does not yet emit stdout_bytes"*. Lo emite en todas las filas.
Ese comentario está vencido y hay una rama de código decidiendo en base a él
(`has_stdout_field`, línea 555).

**4. La ambigüedad real es de 14 hooks, no de 148.**
La premisa "un deny por JSON es indistinguible de un aviso" es correcta, pero su
alcance es mucho más chico de lo que sugiere: **no se puede denegar sin escribir**.
`stdout_bytes == 0` prueba que no hubo deny-por-JSON. Sólo **14 de 148 hooks emitieron
stdout alguna vez**, y sólo **4 tuvieron alguna vez `exit_code != 0`**. El universo
ambiguo es ≤18 hooks. Los otros 130 están *probados* como "no denegaron" — lo que no
está probado es si *podrían*, que es una pregunta distinta y se contesta en el
laboratorio (§P4), no en la telemetría.

---

## P1 — Cómo distinguen "nunca se evaluó" de "se evaluó y siempre permitió"

Ningún sistema resuelve esto midiendo el efecto. Todos lo resuelven **haciendo que la
evaluación declare su propio resultado**, y varios agregan un denominador separado.

### Kyverno: el tercer valor

Es la respuesta más limpia y la más directamente aplicable. Los `PolicyReport` /
`ClusterPolicyReport` tienen un campo `result` con **cinco** valores: `pass`, `fail`,
`warn`, `error` y `skip`. La documentación es explícita sobre por qué `skip` no es
`pass`:

> "Skip differs fundamentally from pass — it indicates the rule wasn't evaluated
> rather than compliance."

`skip` se produce cuando las precondiciones no se cumplen, cuando hay una policy
exception, o cuando un anchor condicional no matcheó. Cada entrada de resultado lleva
`policy` (nombre de la política) y `rule` (regla dentro de la política), y el `summary`
agrega los contadores `error` / `fail` / `pass` / `skip` / `warn`.

El denominador va aparte, en métricas: `kyverno_policy_rule_info_total` ("policies and
rules count") contra `kyverno_policy_results_total`, ambas con labels `policy_name`,
`rule_name`, `rule_type`, `rule_result`, `policy_validation_mode` y
`policy_background_mode`. Una regla que existe en `rule_info` pero no tiene serie en
`results` nunca se evaluó; una que tiene serie sólo con `rule_result="pass"` se evaluó
y siempre permitió.

### OPA: el log lleva el resultado y las reglas tocadas

El decision log de OPA es un evento por decisión con `decision_id`, `path`
(p. ej. `/http/example/authz/allow`), `input`, **`result`** (la decisión devuelta al
cliente, `true`/`false`), `timestamp`, `bundles`, `requested_by`, `labels`, `metrics`,
`trace_id`/`span_id`. Y —lo relevante acá— dos campos de granularidad de regla:
`ids` (identificadores de las reglas que tienen anotación `id`) y `rule_labels`
("merged label maps from evaluated rules").

O sea: **la lista de reglas efectivamente evaluadas viaja dentro del evento**. Un
`path` que nunca aparece en el log nunca se evaluó. Un `path` que aparece siempre con
`result: true` se evaluó y siempre permitió. La distinción es la nuestra, y se
resuelve porque se guarda el resultado y no el tamaño de la salida.

Contrapunto importante: **las métricas Prometheus de OPA no sirven para esto**. Expone
runtime de Go, `http_request_duration_seconds`, y métricas del plugin de status
(`opa_info`, `plugin_status_gauge`, `bundle_loaded_counter`…). No hay contador de hits
por regla ni por política. El censo por regla es responsabilidad del decision log, no
del scrape.

### Gatekeeper: el denominador es un timestamp

`gatekeeper_violations` está etiquetada por `enforcement_action` (deny/dryrun/warn) y
`gatekeeper_constraints` por `enforcement_action` y `status` (active/error). **No hay
desagregación por nombre de constraint.** Ese diseño no resuelve la pregunta: no
copiarlo.

Lo que sí la resuelve está en el objeto, no en la métrica. El `status` de cada
Constraint lleva `auditTimestamp` y `totalViolations`. Leídos juntos:

| `auditTimestamp` | `totalViolations` | Lectura |
|---|---|---|
| ausente | — | la constraint nunca fue evaluada (no corrió el audit) |
| presente | `0` | se evaluó y no encontró nada |
| presente | `>0` | se evaluó y encontró |

El `auditTimestamp` es un denominador barato: prueba que el ciclo llegó hasta ahí. Es
lo que nos falta — hoy sabemos que el hook *corrió*, no que *llegó al punto de
decisión*.

### Falco: contador por regla, con una trampa de default

Con `rules_counters_enabled: true`, Falco emite
`falcosecurity_falco_rules_matches_total` con labels `rule_name`, `priority`, `source`
y tags (`tag_container`, `tag_shell`, …).

La trampa: `include_empty_values: false` es el default, y con eso **las reglas con cero
matches se omiten de la salida**. Es decir, el default de Falco produce exactamente
nuestro problema: la ausencia de la serie es indistinguible de "la regla no está
instrumentada". El cero hay que pedirlo explícitamente. Es el hallazgo más barato de
transplantar de toda la investigación: **un contador en cero que no se emite no es un
cero, es un agujero.**

### Envoy RBAC y Cilium: contadores complementarios

Envoy publica en `http.<stat_prefix>.rbac.` los contadores `allowed` ("Total requests
that were allowed access") y `denied`, más `logged` / `not_logged`. Con
`track_per_rule_stats: true`, "counters will be published for each rule and shadow
rule". `allowed + denied == 0` es "no se evaluó"; `allowed > 0, denied == 0` es "se
evaluó y siempre permitió". Dos contadores, no uno — la asimetría de guardar sólo el
denegado es lo que rompe la inferencia.

Cilium hace lo mismo en el veredicto: `policy_verdict_total` con labels `direction`,
`action` y `match`, donde `match` toma los valores `none`, `L3_only`, `L3_L4`,
`L4_only`, `all`. El veredicto lleva **qué parte de la política matcheó**, incluido
`none`. Complementan `drop_count_total` (labels `reason`, `direction`),
`policy_max_revision`, `policy_change_total` y `policy_endpoint_enforcement_status`.

### AWS IAM: el análogo más fuerte, y el más honesto

IAM Access Analyzer unused access + last accessed information es literalmente
"permiso declarado ≠ permiso ejercido". Detecta roles sin usar, access keys sin usar y
—a nivel fino— "unused services and actions" para roles activos, leyendo el last
accessed information.

Lo valioso no es que lo detecte: es **que se niega a decir "nunca"**. La doc acota la
afirmación con un período de tracking documentado:

> "The tracking period for services is at least 400 days"
> "The tracking period for Amazon S3 actions information began on April, 12, 2020.
> The tracking period for Amazon EC2, IAM, and Lambda actions began on April 7, 2021.
> The tracking period for all other services began on May 23, 2023."

Y publica una tabla región por región con la fecha desde la que hay datos. Además
enumera los agujeros conocidos, con nombre: `iam:PassRole` "is not tracked and is not
included"; "Action last accessed information is not available for any data plane
event"; los tipos de política excluidos (resource-based, ACLs, SCPs, permissions
boundaries, session policies); y un delay de cuatro horas.

Traducción directa a nuestro caso: **la afirmación correcta nunca es "el guard nunca
disparó", es "el guard no disparó en N corridas desde <fecha en que empezó a haber
telemetría con este schema>"**, más la lista explícita de lo que el instrumento no ve.

---

## P2 — El modo `dryrun` / `audit`: qué es y qué cuesta

Es la respuesta consensuada de la industria al guard sin prueba, y aparece en cuatro
formas con costos muy distintos.

### Gatekeeper — `enforcementAction`

Valores soportados: `[deny, dryrun, warn]`. `dryrun` permite "constraints to be
deployed in the cluster without making actual changes"; la política **corre igual** y
los recursos afectados aparecen como violaciones en `status`. Cada entrada de
`status.violations` lleva `enforcementAction`, `kind`, `message`, `name` — o sea la
violación registra bajo qué modo se produjo. El flag `--log-denies` loguea "all deny,
dryrun and warn failures". `warn` (v3.4+, K8s ≥1.19) da "immediate feedback on why that
constraint would have been denied" sin bloquear.

Costo: bajo, porque el audit de Gatekeeper corre en un loop propio
(`--audit-interval`, default 60s) y no en el camino del admission webhook. Con
`--audit-from-cache=true` ni siquiera consulta al API server.

### Kyverno — `failureAction: Audit`

> "a policy violation is logged in a `PolicyReport` or `ClusterPolicyReport` but the
> resource creation or update is allowed."

Está a nivel de regla (`spec.rules[*].validate[*].failureAction`, que reemplaza al
`spec.validationFailureAction` deprecado) y admite `failureActionOverrides` por
namespace: se puede endurecer un namespace a la vez. Con `spec.emitWarning` la
violación además viaja como warning en la respuesta de admisión.

Detalle de rollout que vale copiar: los recursos preexistentes que violan una política
recién puesta en `Enforce` **no se bloquean** de entrada; sólo se bloquean las
actualizaciones que agreguen violaciones nuevas
(`validate.allowExistingViolations`). Endurecer un guard no rompe el mundo que ya
existía.

### Kubernetes nativo — `validationActions`

`ValidatingAdmissionPolicyBinding` declara una o más acciones:

> "`Deny`: Validation failure results in a denied request.
> `Warn`: Validation failure is reported to the request client as a warning.
> `Audit`: Validation failure is included in the audit event for the API request."

En `Audit`, la anotación `validation.policy.admission.k8s.io/validation_failure` lleva
un payload JSON con `message`, `policy`, `binding`, `expressionIndex` y
`validationActions`. `expressionIndex` es notable: identifica **cuál de las
expresiones de la política falló**, no sólo la política. Es granularidad sub-regla,
gratis, en el registro.

La escalera documentada es `Audit` → `Warn` → `Deny`. Y una restricción explícita:
`Deny` y `Warn` no se combinan, "since this combination needlessly duplicates the
validation failure".

### Envoy — `shadow_rules`: el patrón más fuerte

> "Shadow policy for testing RBAC rules without enforcing them. These rules generate
> stats and logs but do not deny requests."

La diferencia con los tres anteriores: **shadow corre en paralelo a `rules`, sobre el
mismo tráfico, en el mismo request.** No hay que apagar la política vigente para
probar la candidata. Emite `shadow_allowed` ("Total requests that would be allowed
access by the filter's shadow rules") y `shadow_denied`, con
`shadow_rules_stat_prefix` para separar namespaces de stats, y metadata dinámica
`shadow_effective_policy_id` ("The effective shadow policy ID matching the action, if
any") y `shadow_engine_result`.

Costo: es el único de los cuatro donde el dryrun es **trabajo adicional**, no trabajo
igual sin efecto. Se evalúan dos motores por request. Envoy se lo puede permitir
porque es C++ en el data plane.

### Resumen de costos

| Sistema | Qué cuesta el dryrun | Dónde corre |
|---|---|---|
| Gatekeeper `dryrun` | ~0 extra: la evaluación ya ocurría en el audit loop | fuera del camino crítico |
| Kyverno `Audit` | ~0 extra en admisión; el background scan es aparte (1h default) | mixto |
| K8s `Audit` | una anotación por fallo en el audit log | camino crítico, marginal |
| Envoy `shadow_rules` | **evaluación duplicada por request** | camino crítico |

---

## P3 — ¿Censo o muestreo? Y cómo aguantan el volumen sin perder el "nunca"

### OPA: censo por default, con tres válvulas de distinto peligro

"Logging captures all decisions by default". Las tres formas de reducirlo no son
equivalentes:

| Mecanismo | Qué hace | ¿Sobrevive el "nunca disparó"? |
|---|---|---|
| `system.log.mask` | redacta campos sensibles del evento | **Sí** — el evento existe, con menos contenido |
| `system.log.drop` | política Rego que decide qué NO loguear | No, para lo dropeado |
| `max_decisions_per_second` | rate limit que **descarta** eventos por encima del límite | No, y peor: descarta lo que llegó en ráfaga |

El patrón a copiar es el masking: **degradar el contenido, nunca el hecho**. El
antipatrón es el rate limit: si está activo, se pierde el derecho a afirmar "nunca
disparó", porque el descarte se concentra justamente en los picos, que es donde algo
raro pasa.

Notar además que en OPA **el filtro de logging es él mismo una política Rego**
(`system.log.drop`). La decisión de qué no observar es auditable y versionada, no un
`if` escondido en el instrumento.

### Gatekeeper: truncar el detalle, nunca el contador

Éste es el hallazgo estructural de la sección. `--constraint-violations-limit` (default
**20**) acota cuántas violaciones individuales se publican en el `status` del
constraint, para no reventar el límite de tamaño de objeto del API server. Y entonces:

> "the excess violations will not be reported (though they will still be included in
> the `totalViolations` count)"

Dos campos con dos políticas de retención distintas en el mismo objeto: la lista se
trunca, el contador no. Nuestro instrumento hizo exactamente lo contrario: guardó una
métrica de tamaño (`stdout_bytes`) y tiró el hecho (denegó / no denegó). El costo de
guardar el hecho es un enum de un byte por fila; el de guardar el detalle es
ilimitado. Se truncó lo barato.

### Kyverno: estado y serie separados

Los policy reports "reflect the current cluster state without historical data" — son
un **estado**, reconciliado, no un histórico. El histórico son los counters de
Prometheus, monótonos. Dos instrumentos con dos propósitos y ninguno haciendo el
trabajo del otro. Los reports se generan por dos vías: eventos de admisión
(CREATE/UPDATE/DELETE) y **background scan periódico (1 hora por default)**, que es
lo que permite reportar violaciones de recursos que ya existían antes de la política.

### Falco: snapshots + la métrica como alerta

Métricas por `interval` (snapshots, no stream), y `output_rule` emite las métricas
"as internal rule alerts" — el canal de observabilidad reusa el canal de alertas en
vez de inventar uno.

### AWS: retención declarada como parte del producto

"at least 400 days" para servicios, con fecha de inicio por región y por servicio. La
retención no es un detalle de operación: es parte del contrato de la afirmación.

---

## P4 — ¿Alguno exige cobertura de prueba antes de aceptar una política?

Respuesta corta: **la primitiva existe en tres de ellos; el gate que la obliga, en
ninguno.** Distinción producto/promesa que importa mucho acá.

### OPA `opa test --coverage` — el único con cobertura de línea

Reporta "all of the lines evaluated and not evaluated in the Rego files", con rangos
de líneas cubiertas y no cubiertas y porcentaje por archivo y agregado. La semántica
de "no cubierta" está afinada exactamente a nuestra pregunta:

> "If the line refers to the head of a rule, the body of the rule was never true."
> "If the line refers to an expression in a rule, the expression was never evaluated."

Eso es, palabra por palabra, la distinción entre *unproven-guard* (el cuerpo nunca fue
verdadero → nunca se llegó a bloquear) y *observer* (la expresión nunca se evaluó).
La diferencia con todo lo anterior es que acá se resuelve en el laboratorio, con
inputs elegidos, no en producción.

Caveat que la propia doc levanta, y que nos aplica: "rule indexing has determined some
path unnecessary for evaluation, thereby affecting the lines reported as covered". La
optimización del motor contamina la métrica de cobertura. Si un guard se optimiza con
early-exit, su cobertura miente en la dirección optimista.

### Gatekeeper `gator verify` — la aserción "esto DEBE disparar"

Framework de tres niveles: un **Suite** define **Tests**; un Test "declares a
ConstraintTemplate, a Constraint, an ExpansionTemplate (optional), and Cases"; un
**Case** "defines an object to validate and whether the object is expected to pass".

El campo clave es `assertions` con `violations`:

- `violations: yes` — "The Case expects at least one violation"
- `violations: no` — "The Case expects no violations"
- un entero — exige exactamente esa cantidad

Existe, entonces, la primitiva "este caso obliga a la política a disparar". Lo que **no**
existe es la obligación: la documentación no exige que toda ConstraintTemplate tenga
al menos un case con `violations: yes`, ni hay un gate que lo verifique. `gator test`
devuelve exit code según haya violaciones, lo que sí lo hace usable en CI — pero el
criterio de "toda política tiene una prueba que la hace denegar" hay que escribirlo
uno.

### Kyverno `kyverno test`

Manifiesto de test declarando políticas, recursos y `results` esperados (pass / fail /
skip). Mismo estado: se puede declarar el caso que falla, nada obliga a que exista.

---

## Qué aplica y qué no, para nuestro caso

Nuestros guards son hooks bash efímeros —un fork por invocación, sin estado— en el
camino sincrónico de cada tool call. Eso decide casi todo.

### Aplica

**A1. Registrar el veredicto, no su tamaño.** (Gatekeeper `totalViolations`; OPA
`result`; Envoy `allowed`/`denied`.) Un campo `decision` con enum acotado
(`allow` / `deny` / `warn` / `ask` / `none`) en la fila de telemetría. Es el cambio
que convierte decenas de miles de filas de "no sé" en un censo. Requiere parsear el stdout del
hook cuando `stdout_bytes > 0` — y por §Corrección 4, eso es sólo 14 hooks.

**A2. El tercer valor `skip`, que ya está en el schema.** Kyverno separa `skip` de
`pass` porque son preguntas distintas. Nuestro schema ya tiene `skipped` y
`skip_reason`: falta que los hooks los usen al salir por precondición (tool que no
matchea, path que no matchea) en vez de salir con exit 0 silencioso. Sin eso, un guard
que nunca llegó a su condición y otro que la evaluó y no encontró nada son la misma
fila.

**A3. Un denominador que pruebe "llegué al punto de decisión".** El `auditTimestamp`
de Gatekeeper. Concretamente: que el hook emita que alcanzó su rama de evaluación, no
sólo que el proceso arrancó. Hoy `duration_ms` prueba que el proceso corrió, no que
evaluó.

**A4. El cero explícito.** El `include_empty_values` de Falco. Cualquier reporte que
liste guards debe listar los de contador cero, con el cero escrito. Un guard ausente
del reporte no es un guard sin hallazgos.

**A5. La escalera `audit → warn → deny`.** (K8s VAP; Gatekeeper dryrun/warn/deny;
Kyverno Audit/Enforce.) Un guard nuevo nace en modo audit, registra qué habría
bloqueado, y gradúa a deny con evidencia de al menos un caso real interceptado. Cierra
la categoría "unproven-guard" desde el origen, no por auditoría posterior.

**A6. La aserción "debe disparar" en el test.** (`violations: yes` de gator.) Un guard
no se acepta sin un caso que lo haga bloquear. Es la respuesta directa a "no se puede
distinguir si puede atrapar": se distingue probándolo una vez, no observándolo mil.

**A7. Honestidad del período.** (AWS.) Reemplazar "nunca disparó" por "no disparó en N
corridas desde <fecha del schema actual>", más la lista escrita de lo que el
instrumento no ve — al estilo del "`iam:PassRole` is not tracked" de AWS.

**A8. Degradar contenido, nunca el hecho.** (masking vs drop de OPA; truncar
`violations` pero no `totalViolations` en Gatekeeper.) Si en algún momento hay que
recortar la telemetría por volumen, se recorta el detalle y se conserva el contador.

### No aplica

**N1. Métricas Prometheus por regla.** (Falco, Kyverno, Envoy.) Presuponen un proceso
de vida larga que acumula contadores en memoria. Un hook bash muere en cada
invocación. El acumulador tiene que estar afuera — y ya lo está, es el JSONL. No hay
nada que agregar acá salvo que la fila diga el veredicto (A1).

**N2. Cobertura de línea sobre los guards.** `opa test --coverage` funciona porque Rego
es declarativo y el motor instrumenta la evaluación. El equivalente en bash requiere
tracing por línea en cada corrida sobre ~148 hooks en el camino crítico: costo
prohibitivo, y además la propia doc de OPA advierte que la optimización del motor
falsea la cobertura. Lo transplantable de OPA acá es la *semántica del reporte*
(distinguir "el cuerpo nunca fue verdadero" de "la expresión nunca se evaluó"), no el
mecanismo.

**N3. El shadow de Envoy con doble evaluación.** Es el patrón conceptualmente más
lindo —probar la candidata sobre tráfico real sin apagar la vigente— y el único que no
podemos pagar tal cual: duplicaría el fork por hook en el camino sincrónico. Si se
quisiera algo así, tendría que correr diferido sobre la traza registrada, no en línea.

**N4. `gatekeeper_violations` agregada por `enforcement_action`.** Es el
antipatrón exacto que nos dejó ciegos: métrica sin la dimensión que identifica quién
decidió. Se documenta acá para no reproducirla.

**N5. "El reporte es el estado actual" de Kyverno.** Los policy reports son objetos de
Kubernetes con reconciliación y garbage collection. Nuestro JSONL es append-only: es
histórico, no estado. Transplantar la semántica de "estado actual" sin un reconciliador
produciría un reporte que envejece sin avisar.

**N6. Adopción de código.** `external-tool-adoption-freeze.yaml` está `frozen: true`.
Todos los proyectos citados son Apache-2.0 (compatible con `license-policy`, que sólo
bloquea AGPL/SSPL/BSL), así que el freeze es la restricción vinculante, no la licencia.
Este informe trae patrones; no propone incorporar ninguna dependencia.

---

## Lo que NO se puede transplantar

Más allá de N1–N6, tres límites de fondo:

**1. Todos estos motores saben qué reglas tocaron porque la política es declarativa.**
OPA emite `ids` y `rule_labels` "from evaluated rules" porque el motor evalúa reglas
que él mismo parseó. Kyverno sabe que una regla fue `skip` porque él evalúa las
precondiciones. Un hook bash es una caja negra: nadie afuera puede saber qué ramas
recorrió. **Por lo tanto el patrón no se transplanta al instrumento — se transplanta al
contrato del hook.** El instrumento no puede aprender a leer veredictos que el hook no
emite. Éste es el hallazgo de fondo de la investigación, y explica por qué ninguna
mejora del agregador va a cerrar la brecha.

**2. Ninguno resuelve "esta política *puede* bloquear" por observación.** Todos lo
resuelven por *construcción* (dryrun desde el día uno) o por *prueba* (gator
`violations: yes`, `opa test --coverage`). La pregunta "¿este guard puede atrapar
algo?" no tiene respuesta observacional en ninguno de los ocho sistemas revisados. Si
la queremos contestar sobre 148 hooks ya existentes, el camino es el test que los hace
disparar, uno por uno — no más telemetría.

**3. El presupuesto de latencia es la diferencia real.** Gatekeeper puede auditar todo
el cluster cada 60 segundos y Kyverno escanear en background cada hora porque están
fuera del camino del usuario. Nuestros hooks están adentro. Cualquier mecanismo que
copie el "corré igual, no bloquees" tiene que ser gratis en tiempo, y eso descarta
todo lo que implique una segunda evaluación en línea.

---

## Fuentes

| # | Fuente | URL | Licencia del proyecto |
|---|---|---|---|
| 1 | OPA — Decision Logs | https://www.openpolicyagent.org/docs/management-decision-logs | Apache-2.0 |
| 2 | OPA — Monitoring / Prometheus | https://www.openpolicyagent.org/docs/monitoring | Apache-2.0 |
| 3 | OPA — Policy Testing (`opa test --coverage`) | https://www.openpolicyagent.org/docs/policy-testing | Apache-2.0 |
| 4 | Gatekeeper — Audit | https://open-policy-agent.github.io/gatekeeper/website/docs/audit/ | Apache-2.0 |
| 5 | Gatekeeper — Violations / `enforcementAction` | https://open-policy-agent.github.io/gatekeeper/website/docs/violations/ | Apache-2.0 |
| 6 | Gatekeeper — Metrics | https://open-policy-agent.github.io/gatekeeper/website/docs/metrics/ | Apache-2.0 |
| 7 | Gatekeeper — gator CLI (`gator verify`, assertions) | https://open-policy-agent.github.io/gatekeeper/website/docs/gator/ | Apache-2.0 |
| 8 | Kyverno — Policy Reports | https://kyverno.io/docs/policy-reports/ | Apache-2.0 |
| 9 | Kyverno — Monitoring / métricas | https://kyverno.io/docs/monitoring/ | Apache-2.0 |
| 10 | Kyverno — validate / `failureAction` | https://kyverno.io/docs/policy-types/cluster-policy/validate/ | Apache-2.0 |
| 11 | Kyverno — CLI `kyverno test` | https://kyverno.io/docs/kyverno-cli/usage/test/ | Apache-2.0 |
| 12 | Falco — Metrics (`rules_counters_enabled`, `include_empty_values`) | https://falco.org/docs/concepts/metrics/ | Apache-2.0 |
| 13 | Falco — `falco.yaml` de referencia (repo) | https://github.com/falcosecurity/falco/blob/master/falco.yaml | Apache-2.0 |
| 14 | Cilium — Observability / Metrics (`policy_verdict_total`) | https://docs.cilium.io/en/stable/observability/metrics/ | Apache-2.0 |
| 15 | Envoy — HTTP RBAC filter (stats) | https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/rbac_filter | Apache-2.0 |
| 16 | Envoy — `rbac.proto` v3 (`shadow_rules`, `track_per_rule_stats`) | https://www.envoyproxy.io/docs/envoy/latest/api-v3/extensions/filters/http/rbac/v3/rbac.proto | Apache-2.0 |
| 17 | Kubernetes — ValidatingAdmissionPolicy (`validationActions`) | https://kubernetes.io/docs/reference/access-authn-authz/validating-admission-policy/ | Apache-2.0 |
| 18 | AWS — IAM Access Analyzer (unused access) | https://docs.aws.amazon.com/IAM/latest/UserGuide/what-is-access-analyzer.html | doc propietaria (servicio) |
| 19 | AWS — Refine permissions using last accessed information | https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_access-advisor.html | doc propietaria (servicio) |

---

## Evidencia ejecutable

Los números de la sección de correcciones salen de estos comandos, sobre
`.cognitive-os/metrics/hook-timing.jsonl` en la raíz del repo:

```bash
# schema real de una fila
head -1 .cognitive-os/metrics/hook-timing.jsonl

# hooks distintos, filas totales, silenciosos, y universo ambiguo
python3 - <<'PY'
import json, collections
rows = collections.Counter(); out = collections.Counter(); nz = collections.Counter()
for line in open('.cognitive-os/metrics/hook-timing.jsonl'):
    try: r = json.loads(line)
    except Exception: continue
    h = r.get('hook', '?'); rows[h] += 1
    if (r.get('stdout_bytes') or 0) > 0: out[h] += 1
    if r.get('exit_code') not in (0, None): nz[h] += 1
silent = [h for h in rows if out[h] == 0 and nz[h] == 0]
print('filas:', sum(rows.values()))
print('hooks distintos:', len(rows))
print('silenciosos (sin stdout y sin exit!=0 nunca):', len(silent))
print('  de esos, con >=100 corridas:', len([h for h in silent if rows[h] >= 100]))
print('hooks que emitieron stdout alguna vez:', len([h for h in rows if out[h] > 0]))
print('hooks con exit!=0 alguna vez:', len([h for h in rows if nz[h] > 0]))
PY
```

Salida al 2026-08-19: `hooks distintos: 148` / `silenciosos: 130` / `con >=100
corridas: 16` / `con stdout alguna vez: 14` / `con exit!=0 alguna vez: 4`.

`filas` es volátil — el archivo se escribe en vivo. Dos corridas separadas por unos
minutos dieron 17.271 y 18.640; **los seis conteos por hook no se movieron en ninguna
de las dos**. Quien reproduzca esto va a ver otro total de filas y los mismos 148 /
130 / 16 / 14 / 4, salvo que aparezca un hook nuevo.

Comentario vencido detectado, para corregir aparte:
`cos_lib/telemetry_aggregator.py:505` afirma que el schema del hook-timing-wrapper
"does not yet emit stdout_bytes"; lo emite en el 100% de las filas. La rama
`has_stdout_field` (línea 555) decide en base a esa premisa.

```bash
grep -n "does not yet emit stdout_bytes" cos_lib/telemetry_aggregator.py
grep -c '"stdout_bytes"' .cognitive-os/metrics/hook-timing.jsonl   # == wc -l
```

# Cómo detecta la industria de feature flags lo que nunca se evaluó

**Fecha:** 2026-08-19
**Dominio investigado:** feature flags — detección de flags obsoletos, zombis y no evaluados
**Pregunta que motiva:** el registry del OS declara 1440 primitivas y sólo el 10,8% produjo
alguna vez un evento que las nombre (ver `docs/06-Daily/reports/observabilidad-primitivas-2026-08-19.md`).
El 89,2% restante no es "poco usado": es inobservable. ¿Cómo resuelven este mismo problema
los sistemas que viven de saber si una cosa declarada se está usando?
**Método:** documentación oficial de vendors + specs (OpenFeature, OpenTelemetry) + repos.
18 páginas leídas completas, 3 sólo por snippet de búsqueda (marcadas en la tabla de fuentes).
**Restricción respetada:** `manifests/external-tool-adoption-freeze.yaml` está en `frozen: true`.
Este informe **no propone adoptar código de nadie**. Trae mecanismos; el que se implemente
se implementa desde cero.

---

## Correcciones a las premisas del encargo

1. **"~1440 primitivas" es correcto, "1441" del título del commit anterior no.** El informe
   hermano de hoy dice explícitamente: *"El registry tiene 1440 rutas únicas, no ~1456"*
   (línea 52), y la tabla de §2 cierra en 1440. El commit `ea0d8c56c` titula "1441 primitivas".
   Cité el 1440 del informe, no el 1441 del título.
2. **El 10,8% se sostiene, pero hay un segundo número que el encargo no menciona y cambia
   la conversación:** 155/1440 = 10,8% *observado*, pero **217/1440 = 15,1% es el techo de lo
   observable hoy** (canal capaz de nombrar la primitiva). La brecha entre esos dos números
   —155 vs 217— es la única parte del problema que la telemetría puede cerrar. Las otras 1223
   primitivas necesitan un canal que no existe, y ese es un problema de diseño, no de medición.
3. **El encargo pide "cómo saben otros sistemas cuáles se usan de verdad".** El hallazgo
   incómodo es que **dos de los seis vendors relevantes contestan esa pregunta sin telemetría
   de uso ninguna** (ConfigCat, GrowthBook; Unleash casi). Lo que el encargo asume que es un
   problema de observabilidad, media industria lo trata como un problema de metadato declarado.
   Eso reordena las recomendaciones y está en §4.
4. **`external-tool-adoption-freeze.yaml` verificado, y sus `gated_path_globs` NO incluyen
   `docs/06-Daily/reports/investigacion-*`.** El glob gateado es
   `docs/06-Daily/reports/external-tools-radar-*.md`. Este archivo no cae bajo el freeze
   mecánico; igual respeté la doctrina: cero propuestas de adopción.
5. **Sobre "preferí documentación oficial sobre blogs de marketing":** el dato más citado
   del dominio —los lifetimes por tipo de flag de Unleash (40 días / 7 días)— **no lo pude
   verificar en la doc oficial**: `docs.getunleash.io/reference/feature-toggle-types` devolvió
   404 al momento de leerlo. Queda marcado como no verificado en la tabla de fuentes.

---

## 1. El mapa: quién mide qué, y con qué

| Producto | Señal primaria de "obsoleto" | ¿Usa telemetría de evaluación? | Segundo canal |
|---|---|---|---|
| **LaunchDarkly** | `status.lastRequested` (última evaluación por SDK) | **Sí, es el eje central** | `ld-find-code-refs` (estático) |
| **PostHog** | `last_called_at` + rollout al 100% | **Sí** | — |
| **Harness FME (ex Split)** | impressions | **Sí**, con dedupe en el SDK | — |
| **Flagsmith** | flag analytics (conteos por flag) | **Sí, pero apagado por default** | stale detection por fecha de cambio |
| **Unleash** | vencimiento del *expected lifetime* del tipo de flag | **No** para el estado stale | métricas de SDK, separadas |
| **ConfigCat** | tiempo sin ser tocado/referenciado ("zombie flags") | **No** | CLI de code references |
| **GrowthBook** | 14 días sin update + regla de una sola variante | **No** (la doc no la menciona) | `gb-find-code-refs` |
| **Uber Piranha** | ninguna: se le dice el flag y el valor esperado | **No** | es un refactorizador, no un detector |

Lectura rápida: **de siete herramientas, tres deciden staleness sin mirar una sola evaluación**.
La telemetría de evaluación no es el estándar de la industria para esta pregunta; es el estándar
de los vendors que ya la tenían por otra razón (experimentación).

---

## 2. Las cuatro preguntas del encargo

### 2.1 ¿Distinguen "declarado y nunca evaluado" de "evaluado y siempre false"?

**Sí, y es la distinción que estructura todo el modelo de LaunchDarkly.** Son dos ejes
ortogonales que ellos separan explícitamente en cuatro estados:

| Estado LD | Definición textual | Nuestro análogo |
|---|---|---|
| **New** | *"You created the flag fewer than seven days ago and it has never been evaluated"* | declarado, sin canal ni evidencia, todavía joven |
| **Active** | está siendo evaluado y tiene variantes múltiples o cambios recientes | canal vivo con uso |
| **Launched** | *"The flag has been evaluated in the past seven days, you have configured the flag to serve only one variation…"* | **canal vivo, uso constante, valor nulo** |
| **Inactive** | *"The flag has not been evaluated for at least seven days"* | canal vivo, uso cero |

El estado **Launched** es exactamente lo que el encargo llama "evaluado y siempre false":
se ejecuta todo el tiempo y no decide nada. La guía de deuda técnica de LD lo dice sin vueltas:
*"the flag is still evaluated every time the code is run, but because it returns the same
variation for everyone, it's no longer needed"*. Ese caso **no lo detecta la telemetría**
—la telemetría dice "vivísimo"— lo detecta mirar la *configuración*.

Y el caso "nunca evaluado" tiene marcador propio en la API: el material técnico de LD
(`flag-health-signals.md`) documenta el chequeo de `lastRequested` en **null** como
"nunca evaluado por ningún SDK", distinto de `lastRequested` viejo. PostHog hace lo mismo
con `last_called_at`, y su doc reconoce el hueco que nos importa: los flags evaluados en
modo *local evaluation* pueden no reportar uso, o sea que un `last_called_at` vacío puede
significar "nadie lo usa" **o** "nadie lo mira". Idéntico a nuestro "sin canal".

**Conclusión para nosotros:** la distinción existe, está nombrada, y la industria la resuelve
con **dos ejes separados que nunca se colapsan en un número**: eje de uso (telemetría) y eje
de forma (configuración). Nuestro informe hermano ya tiene el eje de uso; le falta el eje de
forma —qué primitiva está declarada de un modo que la vuelve inerte aunque se ejecute.

### 2.2 ¿Censo o muestreo? ¿Cómo manejan rotación y retención?

Este es el punto donde más aprendimos, porque es la mordida de hoy.

- **La spec de OpenTelemetry pide censo**: *"a `feature_flag.evaluation` event SHOULD be
  emitted whenever a feature flag value is evaluated"*. Un evento por evaluación. La spec está
  en estado *release candidate* / development, no estable.
- **Los productos no hacen censo.** Harness FME (ex Split) tiene un parámetro
  `impressionsMode` cuyo **default es `OPTIMIZED`**, que deduplica: impresiones con la misma
  combinación de user id + flag + treatment generadas en pocos minutos no se postean. Existe
  `DEBUG` para ver todo, y `NONE` para mandar **sólo claves únicas** por flag. O sea: el modo
  por defecto **destruye el conteo exacto a propósito**, y el modo más barato conserva
  únicamente la respuesta a "¿se evaluó?".
- **Flagsmith manda conteos agregados, no eventos**: el SDK acumula `flag → count` en memoria
  y postea cada ~10 segundos, con **30 a 60 minutos de latencia** hasta ser visible en el
  dashboard. Y el detalle que más importa: **está apagado por default** — *"Flag analytics are
  disabled by default in our SDKs. You need to explicitly enable it"*.
- **Retención acotada y publicada**: Harness retiene impresiones **90 días**. ConfigCat detecta
  referencias a flags borrados **de los últimos 180 días**. LD no publica retención de
  evaluación en la página de estados; lo que publica son **ventanas de decisión** (7 días para
  el estado, 30 días para "likely stale", 7-30 días como "might be infrequent", <7 días
  "probably active").

**La lección directa sobre la mordida de hoy:** ninguno de estos productos compara dos fuentes
con ventanas distintas. Lo que hacen es **fijar la ventana de decisión por debajo de la ventana
de retención** y publicar la ventana como parte de la definición del estado. "Inactive" no es
"no se usa", es literalmente "no se evaluó en 7 días" — el número está **adentro de la
definición**, no en una nota al pie. Nuestro informe hermano ya aplicó el mismo criterio al
escribir *"la ventana histórica termina donde termina la rotación"*; la práctica de la
industria es subir esa frase del apartado de caveats al **nombre del estado**.

### 2.3 ¿Qué hacen con el dato?

Un rango de acciones, ordenadas de menos a más intrusivas. **Ninguna de las siete bloquea un
merge por default.**

1. **Estado visible en la lista.** Todas. Es el piso.
2. **Ciclo de vida con etapas y compuertas.** LaunchDarkly define seis etapas —Live, Ready for
   code removal, Ready to archive, Deprecated, Archived, Deleted— y cada transición tiene
   criterios explícitos y **configurables por el cliente** (ej.: "temporary + Inactive en
   ambientes críticos + ≥30 días + sin code references" para Ready to archive).
3. **Notificación out-of-band.** Slack (LD), email con frecuencia configurable (ConfigCat),
   evento `feature-stale-on` hacia integraciones (Unleash).
4. **API para que lo consuma tu propio CI.** ConfigCat expone una API de zombie flags
   explícitamente pensada para pipelines; Unleash tiene el evento; LD tiene la API de estados.
   La decisión de qué hacer queda del lado del cliente, no del vendor.
5. **Puntaje agregado.** Unleash calcula un *technical debt rating* (porcentaje de flags sanos
   sobre stale + potentially stale) por proyecto. LD tiene *stale flag percentage* en
   Engineering Insights.
6. **Borrado asistido del código.** Piranha (Uber, **Apache 2.0**) refactoriza: borra el
   condicional, borra el código que queda inalcanzable, y borra los tests del flag. Pero
   **no detecta nada**: hay que darle el nombre del flag y el valor esperado. Es el eslabón
   *después* de la decisión, no la decisión.
7. **Bloqueo duro:** no lo encontré en ninguna doc oficial. Unleash menciona que la integración
   *puede* fallar el build, como opción del usuario.

El patrón es consistente: **el dato de staleness abre un ticket, no cierra una puerta.**

### 2.4 ¿Cómo evitan que medir se vuelva excusa para no borrar?

Tres mecanismos, y el primero es el que más nos sirve.

**(a) Invierten la carga de la prueba en el momento de crear, no en el de borrar.**
El flag nace con una clasificación obligatoria: en LaunchDarkly, *temporary* vs *permanent*;
en Unleash, un tipo (release, experiment, operational, kill switch, permission) que **trae un
expected lifetime asociado**, y al vencerlo Unleash marca *potentially stale* solo. Nadie
tiene que probar que el flag no se usa: el flag tiene que justificar por qué sigue vivo pasada
su fecha. Cero telemetría involucrada.

**(b) El vendor cobra por medir y lo dice.** Flagsmith apaga analytics por default. Harness
ofrece `NONE` para bajar volumen. PostHog advierte que los flags al 100% *"keep feature flag
requests billable while adding clutter"*. El costo de la medición es visible, y eso evita que
"medimos todo" sea gratis conceptualmente.

**(c) Advertencia explícita anti-Goodhart en la doc de LaunchDarkly.** La guía de deuda técnica
dice que *"focusing too much on decreasing your stale flag percentage can lead to bad practices"*
—por ejemplo, marcar como permanente un flag temporal para que salga de la métrica— y recomienda
discutir objetivos de equipo en vez de optimizar un número, con archivado trimestral (ventana de
90-120 días) en lugar de correr detrás del porcentaje.

Esto valida directamente la línea del informe hermano: *"instrumentar primero fabrica 1440
líneas de telemetría para justificar 1440 primitivas"*. El vendor con la telemetría más completa
del mercado escribió la misma advertencia en su propia documentación.

---

## 3. Mecanismos, y cuál aplica a nuestro caso

| # | Mecanismo | ¿Aplica? | Por qué |
|---|---|---|---|
| M1 | Timestamp de última evaluación + `null` explícito como "nunca" | **Sí, parcial** | Sirve para las 348 primitivas con canal posible. No inventa canal donde no hay: para los 766 scripts y 60 templates el campo sería `null` para todos y no distingue nada. |
| M2 | Dos ejes ortogonales: uso (telemetría) × forma (configuración) | **Sí, el más aplicable** | El eje de forma **no necesita canal**. "Hook presente en `hooks/` pero ausente de `settings.json`" es nuestro `Inactive` estructural; "regla en el índice sin loader registrado" es nuestro `Launched` (declarada, inerte). Se computa hoy, con `git` y `jq`, sobre las 1440. |
| M3 | Evento estándar en un punto único de evaluación (OpenFeature `finally` hook + `feature_flag.evaluation` de OTel) | **No, salvo para hooks** | Presupone un SDK con **una** función por la que pasan todas las evaluaciones. Nosotros tenemos cinco mecanismos de activación distintos y ningún cuello común. Ver §4. |
| M4 | Referencias estáticas de código como canal independiente (`ld-find-code-refs`, CLI de ConfigCat, `gb-find-code-refs`) | **Sí, el de mejor relación costo/cobertura** | Es el único mecanismo del dominio que **cubre las 1440 sin instrumentar nada** y sin depender de que algo se ejecute. Un scanner que responda "¿quién menciona esta ruta?" separa *huérfana* de *referenciada-pero-no-ejecutada*, que hoy no distinguimos. |
| M5 | *Extinction event*: registrar el commit en el que desaparece la última referencia | **Sí** | Convierte un borrado en un hecho con fecha y commit, auditable después. Barato: es una línea en un `.jsonl` cuando el scanner pasa de N a 0 referencias. |
| M6 | TTL declarado por clase de primitiva (Unleash *expected lifetime*, `temporary`/`permanent` de LD) | **Sí, y es cambio de proceso, no de código** | Requiere un campo que hoy el registry no tiene: si la primitiva es temporal o permanente. Sin ese campo, ni LD ni Unleash podrían clasificar nada tampoco. |
| M7 | Dedupe/agregación en el productor (`impressionsMode: OPTIMIZED` / `NONE`) | **Sí, si algún día se instrumenta** | Para "¿se usó alguna vez?" alcanza con clave única por primitiva por día. Evita que el canal cueste lo que hoy cuesta `aci-observations.jsonl` (8,1 MB de rastro incidental). |
| M8 | Etapas de ciclo de vida con criterios configurables | **Sí, versión reducida** | Tres estados alcanzan: *declarada sin canal* / *con canal, sin evidencia* / *con evidencia*. Seis etapas es sobreestructura para 1440 archivos sin dueño declarado. |
| M9 | Salida = notificación/ticket, nunca bloqueo | **Sí** | Con 89,2% de cobertura ausente, un gate que bloquee sobre esta señal sería un gate sin trampa al revés: rojo por falta de datos, no por hallazgo. |
| M10 | Refactor automático del código muerto (Piranha) | **No** | Requiere una API de flag reconocible sintácticamente (`isEnabled("x")`) y que le pases el valor esperado. Nuestras primitivas no tienen forma sintáctica común y borrar una no simplifica un condicional: borra una capacidad. |
| M11 | Advertencia anti-Goodhart escrita en la propia doc | **Sí** | Ya está en el informe hermano. La industria la escribió también; vale citarla cuando alguien proponga instrumentar todo. |

**Si hubiera que quedarse con uno: M4 + M2.** Los dos se computan hoy, sobre las 1440, sin
agregar una sola línea de telemetría y sin agregar una primitiva al registry que estamos
auditando. Los dos separan "no lo sabemos" de "está declarado y nada lo toca", que es
precisamente la separación que el informe hermano dice que hoy no se puede hacer sobre 1285
primitivas.

---

## 4. Lo que NO se puede transplantar

Seis diferencias que importan y que invalidan la analogía si se estira.

**1. Un flag tiene un punto de evaluación; una primitiva tiene cinco mecanismos de activación.**
Todo el modelo de OpenFeature descansa en que existe `client.getBooleanValue(...)` y en que
cualquier hook colgado del stage `finally` ve **todas** las evaluaciones (la spec garantiza que
`finally` corre incondicionalmente, y que si un hook `finally` termina mal la evaluación sigue
y los demás `finally` igual corren). Nosotros tenemos: hooks despachados por `settings.json`,
skills propuestos por un router semántico, reglas leídas por un loader, scripts ejecutados por
shell, y templates **leídos como archivo por otro proceso**. No hay una función común donde
colgar un `finally`. Cualquier plan que empiece con "emitamos un evento por uso" tiene que
resolver cinco enganches distintos, no uno.

**2. La telemetría de flags está financiada por otro caso de uso.** Nadie instrumenta
evaluaciones *para saber si el flag vive*. El evento existe porque hace falta para
experimentación, atribución de métricas y rollouts progresivos —la propia intro de la spec de
OTel lo dice: *"determine the impact a feature has on a request… A/B testing or progressive
feature releases"*. La detección de zombis es un **subproducto gratis** de una instrumentación
que ya se pagó. Nosotros no tenemos ese segundo consumidor: el costo entero del canal caería
sobre la pregunta de limpieza. Ese es el argumento más fuerte para **no** copiar M3, y es una
asimetría que ninguna comparación producto-a-producto muestra.

**3. Los umbrales vienen con una tasa base que no compartimos.** "7 días sin evaluación =
Inactive" es razonable cuando el flag se evalúa miles de veces por minuto: siete días de
silencio son miles de millones de oportunidades perdidas. Nuestras primitivas se activan por
evento raro y legítimo — un hook de pre-release puede dispararse una vez al mes y estar
perfectamente vivo. **Copiar el umbral sin copiar la tasa base fabrica falsos positivos.**
Si algún día se define un umbral, tiene que derivarse de la frecuencia esperada de *esa clase*
de primitiva, que es justamente el metadato que hoy no existe (M6).

**4. La asimetría de costo del borrado es inversa.** Borrar un flag deja el código: se elige
una rama del condicional y el comportamiento queda. Es casi gratis y casi reversible. Borrar
una primitiva del OS **borra una capacidad**: no queda ninguna rama elegida. Por eso los
criterios de LD para archivar son razonables allá y serían temerarios acá, y por eso M9
(notificar, no bloquear) no es timidez sino la conclusión correcta.

**5. Los productos tienen un dueño humano por flag; nuestro registry no.** Los mecanismos de
notificación (Slack, email, ticket) presuponen alguien a quien avisarle. Sin dueño declarado,
el reporte de zombis va a una bandeja compartida y se vuelve ruido — que es exactamente el
modo de falla que estas herramientas tienen en la práctica.

**6. En su dominio, "declarado" y "en el código" son dos hechos distintos y verificables por
separado.** El flag vive en el panel del vendor **y** aparece en el repositorio; por eso
`ld-find-code-refs` tiene sentido como canal independiente y por eso el *extinction event* es
significativo. En nuestro caso, la primitiva **es** el archivo: declaración y presencia en el
código son el mismo hecho. Nuestro análogo del code-references no es "¿el archivo existe?",
es "¿algo lo nombra además de sí mismo?" — la pregunta se transplanta, la implementación no.

---

## 5. Tabla de fuentes

`L` = leída completa. `S` = sólo snippet de resultados de búsqueda, no verificada en detalle.

| # | Fuente | URL | Nivel | Licencia / nota |
|---|---|---|---|---|
| 1 | LaunchDarkly — Flag statuses and lifecycle stages | https://launchdarkly.com/docs/home/flags/flag-status | L | doc de producto propietario |<!-- cos-allow-local-privacy-pattern cos-allow-absolute-path: URL publica de docs, el tramo /docs/home/flags/ no es un home path -->
| 2 | LaunchDarkly — Code references | https://launchdarkly.com/docs/home/flags/code-references | L | describe `ld-find-code-refs` (open source) |<!-- cos-allow-local-privacy-pattern cos-allow-absolute-path: URL publica de docs, el tramo /docs/home/flags/ no es un home path -->
| 3 | LaunchDarkly — Reducing technical debt from feature flags | https://launchdarkly.com/docs/guides/flags/technical-debt | L | fuente de la advertencia anti-Goodhart |
| 4 | LaunchDarkly `ai-tooling` — flag-health-signals.md | https://github.com/launchdarkly/ai-tooling/blob/main/skills/feature-flags/launchdarkly-flag-discovery/references/flag-health-signals.md | L | repo del vendor; nombres de campo y umbrales concretos |
| 5 | `launchdarkly/ld-find-code-refs` | https://github.com/launchdarkly/ld-find-code-refs | L | Go. Licencia: `LICENSE.txt` presente, **tipo no confirmado en la lectura**. Requiere cuenta LD |
| 6 | OpenFeature — Appendix D: Observability | https://openfeature.dev/specification/appendix-d/ | L | spec CNCF. **Recomienda, no obliga**: "primarily focuses on providing recommendations" |
| 7 | OpenFeature — Hooks (sección de la spec) | https://openfeature.dev/specification/sections/hooks/ | L | garantías de `finally` (req. 4.4.3), contenido del hook context (4.1.1) |
| 8 | OpenTelemetry — Semconv feature flags (events) | https://opentelemetry.io/docs/specs/semconv/feature-flags/feature-flags-events/ | L | evento `feature_flag.evaluation`, **release candidate**, no estable |
| 9 | OpenTelemetry — Semconv feature flags (índice) | https://opentelemetry.io/docs/specs/semconv/feature-flags/ | S | contexto de spans vs logs |
| 10 | Unleash — Technical debt | https://docs.getunleash.io/reference/technical-debt | L | `feature-stale-on`, technical debt rating |
| 11 | Unleash — Feature flag types | https://docs.getunleash.io/reference/feature-toggle-types | **S — 404 al leerla** | los lifetimes 40 días / 7 días vienen de snippets, **no verificados en la doc** |
| 12 | Unleash — Update feature type lifetime (API) | https://docs.getunleash.io/reference/api/unleash/update-feature-type-lifetime | S | confirma que el lifetime es configurable |
| 13 | Flagsmith — Flag Analytics | https://docs.flagsmith.com/managing-flags/flag-analytics | L | **apagado por default**; conteos agregados cada ~10 s; 30-60 min de latencia |
| 14 | Flagsmith — Feature Flags Lifecycles | https://docs.flagsmith.com/best-practices/flag-lifecycle | L | stale detection por fecha de cambio, sin detalle |
| 15 | ConfigCat — Zombie Flags | https://configcat.com/docs/zombie-flags/ | L | criterio = tiempo sin ser tocado/referenciado; **no confirma uso de telemetría de evaluación** |
| 16 | ConfigCat — Scan & Upload Code References | https://configcat.com/docs/advanced/code-references/overview/ | L | detecta referencias a flags borrados de los últimos 180 días |
| 17 | ConfigCat — List Zombie flags (API) | https://configcat.com/docs/api/reference/get-staleflags/ | S | API pensada para CI/CD |
| 18 | GrowthBook — Stale Feature Flag Detection | https://docs.growthbook.io/features/stale-detection | L | 14 días sin update + reglas de una sola variante. **La doc no menciona telemetría de uso** |
| 19 | GrowthBook — Code References | https://docs.growthbook.io/features/code-references | L | `gb-find-code-refs`, herramienta propia |
| 20 | PostHog — Cleaning up stale feature flags | https://posthog.com/docs/feature-flags/cleaning-up-stale-flags | L | `last_called_at`, 30 días; advierte sobre local evaluation |
| 21 | Harness FME — Impressions | https://developer.harness.io/docs/feature-management-experimentation/feature-management/monitoring-analysis/impressions/ | L | on por default, desactivable por flag; **retención 90 días** |
| 22 | Harness FME — Validate your SDK setup (`impressionsMode`) | https://developer.harness.io/docs/feature-management-experimentation/sdks-and-infrastructure/validate-sdk-setup/ | S | `OPTIMIZED` (default, deduplica) / `DEBUG` / `NONE` |
| 23 | `uber/piranha` | https://github.com/uber/piranha | L | **Apache 2.0**. Java, JavaScript, Objective-C, Swift. Requiere nombre del flag + valor esperado |
| 24 | Uber Engineering — Introducing Piranha | https://www.uber.com/us/en/blog/piranha/ | S | las tres tareas del borrado estático |

> **Nota sobre dos filas de la tabla.** Las URLs 1 y 2 llevan el marcador por linea
> `cos-allow-local-privacy-pattern` y `cos-allow-absolute-path` (guard de privacidad
> local y guard de portabilidad, que miran el mismo patron). Motivo: esas dos
> URLs publicas de LaunchDarkly tienen un segmento de ruta que coincide, caracter por
> caracter, con el prefijo de home de Linux (el segmento no se transcribe aca por el
> mismo motivo: escribirlo vuelve a disparar el guard sobre este archivo). Es coincidencia estructural, no fuga: no hay usuario, host ni
> ruta privada. La excepcion es de dos lineas y no toca el resto del chequeo.

Licencias relevantes anotadas por si alguna vez se levanta el freeze: **Piranha es Apache 2.0**
(compatible con `license-policy`), `ld-find-code-refs` es de LaunchDarkly y requiere cuenta.
**No se propone adoptar ninguno de los dos.**

---

## Lo que este informe no puede afirmar

- **No verifiqué ninguna de estas capacidades corriendo el producto.** Todo sale de
  documentación del vendor. La distinción "hace" vs "promete" la traté leyendo la doc técnica
  y no el marketing, pero una doc técnica sigue siendo el vendor hablando de sí mismo.
- **Los lifetimes de Unleash (40 / 7 días) están sin verificar**: la URL oficial dio 404.
  Si ese número se va a citar en una decisión, hay que confirmarlo primero.
- **La licencia exacta de `ld-find-code-refs` no la confirmé** (hay `LICENSE.txt`, no leí el
  tipo). No importa mientras el freeze siga activo.
- **Retención de datos de evaluación de LaunchDarkly: no publicada** en las páginas que leí.
  Sólo tienen ventanas de decisión (7 y 30 días). No sé cuánto conservan por debajo.
- **No investigué el ángulo académico** (papers de *feature toggle debt*). El encargo pedía
  productos y specs; si hace falta el fundamento empírico de los umbrales, es otra búsqueda.
- **No conté las primitivas del OS de nuevo.** Los números 1440 / 155 / 217 / 10,8% los tomé
  del informe hermano de hoy, que sí trae sus comandos. Si ese informe está mal, este hereda
  el error.
- **La recomendación implícita de §3 (M4 + M2) no la prototipé.** Que un scanner de
  referencias sobre 1440 rutas dé una atribución limpia —aliases, rutas relativas, symlinks
  de `hooks/` a `packages/*/hooks/`— es plausible, no está probado. Los symlinks en particular
  son un riesgo conocido de doble conteo en este repo.

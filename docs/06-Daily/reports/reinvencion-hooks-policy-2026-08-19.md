# Reinvención de la rueda: capa de hooks, gates y políticas — 2026-08-19

## Resumen ejecutivo

- `find hooks -name "*.sh" -type f | wc -l` → **249** archivos regulares (no 257 como decía el encargo); +42 symlinks de alias, 289 rutas únicas por `readlink -f`.
- `grep -o '[a-zA-Z0-9_-]*\.sh' .claude/settings.json | sort -u | wc -l` → **155** hooks registrados. `manifests/hook-registration-classification.yaml` documenta **109** hooks top-level explícitamente NO registrados, cada uno con `status` y motivo — no es dormancia silenciosa, es un manifest de "todavía no" con rationale por ítem.
- `python3 scripts/hook_vitality_audit.py --check-budget` (mismo día, 2026-08-19) → **35** guardas "unproven" de 154 registrados con telemetría (no ~130 de 148 como decía el encargo — ver corrección más abajo), de las cuales 12 son en realidad UNOBSERVABLE (señalizan por stdout JSON, que el wrapper de timing no graba), no "incapaces".
- Nada de lo pedido en Paso 2 (pre-commit/Husky/lefthook, OPA/Gatekeeper/Kyverno/Cedar/Casbin/Oso, gitleaks/trufflehog/detect-secrets, Syft/Grype/FOSSA, tenacity/pybreaker) está en `manifests/external-tools-adoption.yaml` salvo una línea genérica de "pre-commit, ruff, vulture, import-linter, diff-cover" bajo `enforcement-tools` (verdict INTEGRATE, ya usado vía `pyproject.toml`, no como reemplazo de `hooks/`).
- Hallazgo de licencia: **TruffleHog v3+ es AGPL-3.0** (confirmado en su propio `LICENSE`) — bloqueada de plano por freeze, si alguna vez se evaluara.
- **Respuesta a la pregunta central (sección prioritaria, primera en el informe):** Gatekeeper (`enforcementAction: dryrun`) y Kyverno (`validate.failureAction: Audit` — ojo, `spec.validationFailureAction` está **deprecado desde 1.13**) sí resuelven "política instalada que nunca deniega", y el mecanismo decisivo no es el modo audit sino **dónde aterriza el resultado**: `PolicyReport`/`ClusterPolicyReport` CRDs que registran `pass` *además* de `fail`. Emitir un `pass` por evaluación es lo que distingue "evaluó y pasó" de "nunca evaluó" — distinción que nuestro `hook_vitality_audit.py` no puede hacer hoy. "Regla que nunca disparó" es señal de primera clase en **detection engineering** (*silent failure*, se marca a los X días por regla), no dentro de Gatekeeper/Kyverno. Agregación: Policy Reporter (`minimumSeverity`, filtros, channels) y Alertmanager (grouping/inhibition/silencing), con 5 modos de falla documentados — el peor es que la capa de agregación caída se ve igual que "no hay alertas".

## El problema de la política que nunca deniega: cómo lo resuelve la industria

> Sección prioritaria (elevada a pedido del coordinador, 2026-08-19). Responde los cuatro
> puntos pedidos: sintaxis vigente del modo audit, dónde aterriza el resultado y quién lo lee,
> si "política que nunca disparó" es señal de primera clase, y cómo se agrega la señal.
> Diagnóstico y mecanismo únicamente — el freeze de adopción sigue vigente, acá no se propone
> adoptar ni vendorizar nada.

### 1. Cómo se declara el modo audit/dryrun (sintaxis vigente 2026)

**Gatekeeper** — el campo va en la *Constraint*, no en el ConstraintTemplate:

```yaml
spec:
  enforcementAction: dryrun    # alternativas: deny | warn | dryrun | scoped
```

Con `dryrun`, el recurso que viola la política **se registra pero no se bloquea**. En 2026 se
sumó `enforcementAction: scoped`, que permite acción distinta por *enforcement point* — la
misma constraint puede ser `warn` en admission (`validation.gatekeeper.sh`) y `deny` en el
CLI de test (`gator.gatekeeper.sh`):

```yaml
spec:
  enforcementAction: scoped
  scopedEnforcementActions:
    - action: warn
      enforcementPoints: [{name: "validation.gatekeeper.sh"}]
    - action: deny
      enforcementPoints: [{name: "gator.gatekeeper.sh"}]
```

Esto es directamente traducible a nuestro problema: la misma política puede tener veto real en
un punto de enganche (p. ej. un test que la ejercita) y ser advisory en otro (la sesión viva).

**Kyverno** — ojo con la sintaxis, **cambió**. `spec.validationFailureAction: Audit|Enforce` está
**deprecado desde Kyverno 1.13** (junto con `spec.validationFailureActionOverrides`) y será
removido. La forma vigente es por regla, no por política:

```yaml
spec:
  rules:
    - name: mi-regla
      validate:
        failureAction: Audit          # antes: spec.validationFailureAction
        failureActionOverrides: [...] # antes: spec.validationFailureActionOverrides
```

El default es `Audit`, no `Enforce` — es decir, **Kyverno arranca en modo no-bloqueante por
diseño** y pasar a enforce es una decisión explícita. Nuestro repo hace lo inverso: los hooks
nacen con capacidad de bloqueo (`exit 2` / `permissionDecision: deny`) y quedan sin ejercitar.

### 2. Dónde aterriza el resultado, y quién lo lee — el punto clave

Éste es el eje donde la diferencia con nuestro estado es más nítida. Nuestro problema no es que
las políticas no evalúen: es que evalúan y **el resultado no llega a ningún consumidor**.
La industria resuelve eso con un artefacto consultable, no con un log.

**Gatekeeper** deposita el resultado de audit en **cuatro** destinos distintos, con consumidores distintos:

| Destino | Forma | Quién lo lee |
|---|---|---|
| `status.violations` de la Constraint | Objeto Kubernetes, `kubectl get constraint -o yaml` | Humano/CI, ad-hoc |
| Métrica `gatekeeper_violations` | Contador Prometheus | Alerting (`gatekeeper_violations > 0`), dashboards |
| Log de audit | JSON a stdout, `event_type: violation_audited` | Pipeline de logs |
| Export/pubsub | Publicación a un sistema externo configurable | Sistemas downstream |

Flags relevantes: `--audit-interval=60` (segundos, default 60; `0` desactiva),
`--constraint-violations-limit=20` (default 20 — **el status trunca**, así que el status *no* es
fuente de verdad para conteos: para eso está la métrica), `--audit-from-cache=true` (lee del
informer cache en vez de pegarle a la API), `--audit-chunk-size=500`.

**Kyverno** va más lejos: escribe a **`PolicyReport`** (namespaced) y **`ClusterPolicyReport`**
(cluster-scoped), CRDs del estándar del Kubernetes Policy Working Group. No son logs: son objetos
de primera clase, consultables, con resultados `pass` **y** `fail` de múltiples políticas
combinados en un mismo reporte. Que el reporte incluya los `pass` es lo que hace posible
distinguir "la política evaluó y pasó" de "la política nunca evaluó" — distinción que nuestro
`hook_vitality_audit.py` **no puede hacer hoy**, porque solo ve runs y blocks observados.

**La lección aplicable, sin adoptar nada:** el arreglo estructural no es "más ventana de
observación", es **emitir un resultado positivo por evaluación** (`pass`) además del negativo
(`block`). Una guarda que corre 9.343 veces y emite 0 es indistinguible de una rota; una que
emite 9.343 `pass` y 0 `fail` está probada viva. Eso es un cambio en el contrato de salida del
hook, no en el motor.

### 3. ¿"Política que nunca disparó" es señal de primera clase?

**Sí, pero no dentro de Gatekeeper/Kyverno** — ahí es una brecha reconocida, no una feature. La
documentación de audit de Gatekeeper no trata el caso de una constraint con cero violaciones
sostenidas; existe incluso un issue abierto (`open-policy-agent/gatekeeper#2487`) sobre que el
enforcement action `dryrun` **no se registra como violation en el constraint status** — o sea,
justamente el modo pensado para observar es el que menos se ve. El modo de falla clásico
documentado en el ecosistema OPA es más sutil y calca el nuestro: *"un cuerpo Rego perfectamente
correcto atado a una Constraint que se olvidó de listar `apps/v1` Deployments junto a Pods
simplemente nunca se va a evaluar, produciendo una falsa sensación de cobertura"* — nuestro
equivalente exacto es el matcher tipeado mal, que `hook-vitality-budget.yaml` ya llama
"el bucket que necesita ojos" (`max_no_occasion_hooks`, hoy en 0).

**Donde SÍ es señal de primera clase es en detection engineering (SIEM).** Ahí el problema tiene
nombre propio — *silent failure* — y disciplina asociada:

- Se lo trata como **bug, no como ruido**: reglas que nunca disparan por cambios de esquema de
  log o bugs del motor "pasan desapercibidas", y el argumento es que **los falsos negativos son
  completamente silenciosos** — nadie abre un ticket diciendo que *no* recibió una alerta.
- La práctica concreta es **marcar las reglas que no dispararon en X días**, con X alineado a la
  cadencia esperada de esa regla, y surfacear eso en un dashboard dedicado a los ingenieros de
  detección. Nótese el detalle: X es **por regla**, no global — una guarda de `rm -rf` que no
  dispara en un mes es normal; una de secretos que no dispara en 9.343 corridas, no.
- El cierre no es esperar más: es **validación continua** — reproducir muestras de eventos
  conocidos que *deberían* disparar la regla y verificar que sigue disparando. Es exactamente lo
  que ya dice `manifests/hook-vitality-budget.yaml`: *"la forma en que este número baja es un
  test que hace bloquear a la guarda de verdad, no una ventana de observación más larga"*.
  Coincidencia independiente entre nuestro manifest y la práctica del sector — vale como
  confirmación de que el diagnóstico interno estaba bien encuadrado.
- En el mundo OPA la formulación equivalente es: *"las reglas que nunca disparan pueden indicar
  código muerto o cobertura de test insuficiente"* y *"tratá la salud de las políticas como una
  métrica observable del sistema, no como un artefacto set-and-forget"*.

Veredicto para nuestro caso: **es un problema, no ruido normal** — pero la señal correcta no es
"nunca disparó" a secas, sino "nunca disparó **y** ningún test la hizo disparar". El primero solo
tiene información si se lo cruza con el segundo.

### 4. Agregación tipo Alertmanager: cómo se hace bien y dónde falla

El patrón "muchos productores de señal → capa intermedia que agrupa/filtra/silencia → un
consumidor" existe en dos formas relevantes:

**Policy Reporter (sub-proyecto de Kyverno, Apache-2.0)** — la capa intermedia específica de
políticas. Observa `PolicyReport`/`ClusterPolicyReport` en todo el cluster y ofrece:
- `minimumSeverity` por target (`info > low > medium > high > critical`) — el umbral que descarta
  lo que no vale despertar a nadie. Reemplazó al viejo `minimumPriority`.
- **Filtros por target** sobre `namespace, rule, policy, report, kind, name, status, severity,
  category, source` — un target puede suscribirse solo a `status: fail` de cierta categoría.
- **Channels**: varias configuraciones del mismo tipo de target, combinadas con filtros, para
  rutear distinto según prioridad u origen. Es el análogo del árbol de routing de Alertmanager.
- Deduplicación de resultados, más una API de métricas Prometheus y dashboards de Grafana que
  funcionan **sin Loki** (es decir: la agregación no depende de tener el stack de logs).
- Configurable por Helm values **o** por un CRD `TargetConfig` — la config de ruteo es un objeto
  versionado, no un archivo suelto.

**Alertmanager (Apache-2.0)** — el patrón canónico, con tres primitivas:
- **Grouping**: colapsa alertas de naturaleza similar en una sola notificación. El caso de uso
  declarado es la caída grande donde "cientos a miles de alertas disparan simultáneamente".
- **Inhibition**: suprime alertas de baja prioridad cuando una de prioridad mayor y relacionada
  ya está activa — filtra el síntoma cuando ya se está reportando la causa.
- **Silencing**: mute manual por matchers (igualdad o regex) con ventana temporal; el override
  operativo del día a día.

**Modos de falla conocidos (los que importan antes de copiar el patrón):**
1. **La config se vuelve código de producción sin tratarse como tal.** La recomendación explícita
   del sector es tratar la config de Alertmanager como código sujeto a testing y review. Una regla
   de inhibición mal escrita **suprime la señal real** y no deja rastro — es el mismo verde barato
   que describe `rules/gates-sin-trampa`: la supresión apaga el rojo sin tocar la causa.
2. **Silencios que sobreviven a su motivo.** Un silence puesto "por hoy" que nadie retira es una
   política desactivada de facto, y no aparece en ningún inventario de políticas.
3. **Agrupar demasiado esconde el caso raro.** El grouping que fusiona cientos de alertas en una
   notificación también fusiona la única distinta.
4. **Umbral por severidad mal calibrado = pérdida silenciosa.** `minimumSeverity: high` descarta
   los `medium` sin dejar constancia de cuántos descartó, salvo que se mida aparte.
5. **La capa de agregación puede caerse sin que nadie lo note** — es un consumidor único, y su
   caída se ve igual que "no hay alertas", que es el estado deseado. Necesita su propio
   heartbeat/dead-man's-switch (patrón estándar en Prometheus: una alerta que siempre dispara,
   cuya *ausencia* es la señal).

El punto 5 y el punto 1 son los dos que más directamente aplican a nuestro caso, porque son
variantes del mismo problema que ya tenemos: **una capa de control cuya falla es indistinguible de
su funcionamiento normal**. Adoptar el patrón de agregación sin adoptar el dead-man's-switch
reproduce el problema un nivel más arriba.

## Correcciones a las premisas del encargo

1. **"257 archivos .sh" es un número desactualizado o mal contado.** `find hooks -name "*.sh" -type f` da 249 archivos regulares hoy. Si se cuentan también las 42 entradas symlink (`find hooks -name "*.sh"` sin filtro de tipo) da 291, y por `readlink -f | sort -u` el total de rutas físicas únicas es 289 (dos symlinks apuntan a un target ya contado como archivo regular). Ningún método da 257. Comando: `find hooks -name "*.sh" -type f | wc -l` / `find hooks -name "*.sh" -type l | wc -l` / `find hooks -name "*.sh" -exec readlink -f {} \; | sort -u | wc -l`.
2. **El dato "de 148 hooks con telemetría, ~130 incapaces de denegar" no coincide con el estado medido hoy mismo.** `manifests/hook-vitality-budget.yaml` (fechado 2026-08-19, el mismo día del encargo) fija `max_unproven_guards: 35` sobre **154** hooks registrados, no 148/130. Reproducido en vivo con `python3 scripts/hook_vitality_audit.py --check-budget`: exactamente 35 guardas en la lista de "unproven" (23 con "cannot distinguish no-occasion from no-capacity" + 12 "capability UNOBSERVABLE" por señalizar vía stdout JSON que el wrapper no graba). El encargo probablemente arrastra un número de un audit previo o de otra medición (quizás sobre *todos* los hooks con *alguna* fila de telemetría en vez de sobre los que tienen *ruta de bloqueo en el código*, que es un universo más chico). El framing de "130 lógicamente incapaces" tampoco es exacto: de los 35, 12 no son "incapaces" sino "no observables con este instrumento" — señalizan por JSON, un mecanismo real de deny que el propio manifest documenta.
3. **El encargo asume que el problema es "hooks que reinventan la rueda sin registrar", pero el manifest ya distingue eso.** `manifests/hook-registration-classification.yaml` (fechado 2026-05-04, con la salvedad de que es ~3 meses más viejo que el resto de la evidencia de este informe y puede estar desactualizado en el conteo exacto) tiene 109 hooks top-level no registrados, cada uno con `status` (33 `active` pero condicionales, 25 `future`, 18 `conditional_opt_in`, 14 `manual_trigger`, 7 `deprecated`, 4 `demoted`, resto scoped/helper) y `rationale` + `next_action`. Esto ya ES, en espíritu, un mecanismo tipo "audit mode antes de deny" — no hace falta importarlo de afuera, pero tampoco cierra el hueco específico de violation-counting que sí tiene Gatekeeper (ver sección dedicada).
4. **El encargo no pidió verificar si `rate-limiting` es un caso más del mismo patrón, pero lo es y es ilustrativo.** `rules/rate-limiting.md` (ya citado en el contexto de esta sesión) documenta que `hooks/rate-limiter.sh` existe, implementa token-bucket con `cos_lib/rate_limiter.py`, pero **no está registrado** en `.claude/settings.json` (`grep -c 'rate-limiter' .claude/settings.json` → 0, verificado en este informe) y tiene 0 disparos en 37.424 filas de telemetría según ese mismo rule file. Coincide con `rules/ROADMAP.md` Sección 1, que lista 8 reglas "hook-enforced-BROKEN" (existen en disco, no registradas): `audit-trail`, `auto-rollback`, `confidence-gate`, `confidentiality-protection`, `agent-identity`, `pre-dev-readiness-gate`, `reinvention-prevention`, `pre-commit-gate` (este último intencional). Es decir: el problema de "política sin poder de veto" tiene un sub-caso más simple y más grave que "el hook corre pero no dispara" — el de "el hook ni siquiera está enchufado", y ya está inventariado por el propio repo, con nombre y ADR (`ADR-101` para rate-limiter).
5. **No hay contradicción en el punto del freeze**: se investigó exclusivamente en modo diagnóstico, sin proponer adopción ni vendorización. Esta corrección es solo para dejar constancia de que se revisó el freeze antes de escribir la sección de licencias.

6. **El coordinador afirmó, en su corrección de mitad de tarea, que "otro agente de esta tanda reportó que no tuvo acceso a WebSearch" y que yo podría haber escrito el informe con URLs de memoria. En mi caso eso no ocurrió y la premisa no aplica.** Cargué `WebSearch`/`WebFetch` con `ToolSearch query="select:WebSearch,WebFetch"` **antes** de escribir cualquier sección de ecosistema externo, y las 37 fuentes de la primera versión salieron de 8 llamadas reales a `WebSearch` (git-hooks frameworks, policy engines, Cedar/OPA/Casbin/Oso, secret scanners, licencia de TruffleHog, hooks de Claude Code, circuit breakers Python, SBOM/supply chain). La segunda ronda sumó 6 llamadas más (`WebSearch` x5 + `WebFetch` sobre la doc oficial de audit de Gatekeeper). Dejo el incidente escrito porque el coordinador lo pidió, pero corresponde marcar que el diagnóstico de "evidencia falsa" era una hipótesis sobre otro agente, aplicada preventivamente a todos: el chequeo que la habría descartado en mi caso es mirar si hubo llamadas a `WebSearch` en el transcript, no inferirlo del contenido.
7. **La premisa "nuestro repo tiene ~130 hooks en esa condición" se repite en la corrección del coordinador y sigue sin sostenerse.** Ya corregida en el punto 2: el número medido hoy con `python3 scripts/hook_vitality_audit.py --check-budget` es **35** guardas unproven sobre 154 registrados, y el ratchet oficial (`manifests/hook-vitality-budget.yaml`, ADR-328, fechado 2026-08-19) fija exactamente `max_unproven_guards: 35`. La diferencia importa para la decisión que el operador tomó sobre este eje: 35 guardas dudosas sobre 154 es un problema acotado y con ratchet activo; ~130 sobre 148 sería un sistema de control esencialmente inexistente. Son dos diagnósticos distintos y llevan a inversiones distintas.

## Qué ya estaba registrado en manifests

- `manifests/external-tools-adoption.yaml` (391 líneas): una sola entrada tangencial — `enforcement-tools` (`pre-commit, ruff, vulture, import-linter, diff-cover`), `verdict: INTEGRATE`, `license: MIXED`, consumido vía `pyproject.toml`. Es Python-tooling de linting, no un reemplazo de la capa de hooks de Claude Code. Ningún policy engine (OPA/Gatekeeper/Kyverno/Cedar/Casbin/Oso), scanner de secretos (gitleaks/trufflehog/detect-secrets/git-secrets), ni herramienta de supply-chain (Syft/Grype/FOSSA/ScanCode) aparece en este archivo, en `feature-tool-due-diligence.yaml` (159 líneas) ni en `external-tool-licenses.yaml` (317 líneas). Verificado con `grep -niE "pre-commit|husky|lefthook|opa\b|rego|gatekeeper|kyverno|cedar|casbin|oso\b|gitleaks|trufflehog|detect-secrets|git-secrets|syft|grype|fossa|scancode|pybreaker|tenacity" manifests/*.yaml`.
- `manifests/ai-agent-harness-landscape.yaml` (553 líneas, 39 harnesses catalogados: claude, codex, cursor, opencode, qwen-code, kimi-code, gemini-cli, kiro, cline, roo-code, continue-dev, aider, goose, openhands, swe-agent, github-copilot-coding-agent, devin, windsurf, replit-agent, etc.) SÍ cubre "hooks de agentes" — pero desde el ángulo de **proyección** (cómo el propio COS proyecta sus reglas hacia el formato nativo de cada harness vía `projection_surface: [settings, hooks, instructions, ...]`), no desde el ángulo de "¿su motor de hooks es mejor que el nuestro?". Es un dato de integración, no de comparación de mecanismo. `cursor` está `status: implemented, proof_level: structural`; `openhands` está `status: candidate, proof_level: none`.
- `rules/reinvention-prevention.md` existe (Tier 2, motivado por "137 commits en 5 días sin chequear Hermes/Pi/tools evaluadas") pero su hook (`hooks/reinvention-check.sh`) está listado en `rules/ROADMAP.md` §1.7 como **hook-enforced-BROKEN**: existe en disco, no registrado. Es decir, la propia norma que debería haber prevenido este tipo de reinvención no está activa — no es una ironía menor para este informe.
- `manifests/hook-vitality-budget.yaml` (ADR-328, activo, ratchet) ya es la respuesta interna al problema "esta política nunca pudo denegar nada" — con la salvedad (documentada en el propio manifest) de que la telemetría vive en `.cognitive-os/metrics/hook-timing.jsonl` rotado, con ventana viva de apenas ~3.6 horas, así que el número se mide contra vivo+archivo.
- `manifests/hook-registration-classification.yaml` (ADR no explícito en el header, fechado 2026-05-04) ya es el inventario "hooks no registrados con motivo", que es exactamente lo que un policy-engine externo llamaría modo audit/shadow antes de enforce.

## Inventario de hooks por función

Metodología: clasificación por *keyword* sobre los 215 nombres de archivo top-level de `hooks/*.sh` (no subcarpetas `_lib`/tests), no por lectura de cada script — es una hipótesis de agrupamiento, no un veredicto por hook. Categorías no son mutuamente excluyentes (un hook puede matchear dos patrones). Comando base: `find hooks -maxdepth 1 -name "*.sh" -type f | sed 's#hooks/##;s#\.sh##' | sort`.

| Categoría (tentativa) | Patrón grep | Conteo |
|---|---|---|
| Guardas destructivas / lock / rollback | `guard\|lock\|rm-\|force\|destructive\|rollback` | 30 |
| Ciclo de vida de sesión | `session-\|startup\|wrapup\|context-injector\|preamble` | 27 |
| Costo / rate limiting / budget | `rate-limit\|budget\|cost\|quota\|token` | 13 |
| Coordinación entre sesiones | `concurrent\|lock\|branch\|session-coord\|ownership` | 12 |
| Telemetría / observabilidad | `timing\|metric\|telemetry\|log\|track\|audit-trail\|heartbeat` | 10 |
| Gates de calidad (lint, dup, tipos, tests) | `lint\|quality\|dup\|type\|test\|coverage\|frontmatter` | 7 |
| Seguridad / secretos / privacidad | `secret\|security\|credential\|privacy\|content-policy\|confidential` | 4 |

De los 249 archivos totales en `hooks/` (incluye `_lib` y tests), **155 están registrados** en `.claude/settings.json` (`grep -o '[a-zA-Z0-9_-]*\.sh' .claude/settings.json | sort -u | wc -l`), y **109 top-level están inventariados como no-registrados** con status/rationale en `manifests/hook-registration-classification.yaml` (breakdown: 33 `active` condicional, 25 `future`, 18 `conditional_opt_in`, 14 `manual_trigger`, 7 `deprecated`, 4 `demoted`, 3 `profile_scoped`, 2 `git_or_manual`, 2 `internal_helper`, 1 `projected_elsewhere` — `python3 -c "import json; d=json.load(open('manifests/hook-registration-classification.yaml')); from collections import Counter; print(Counter(e['status'] for e in d['entries'])))"`). La suma (155+109=264) no cierra limpio contra 215 top-level porque el manifest de clasificación está fechado 2026-05-04, tres meses antes de esta auditoría — es evidencia de que ese inventario específico puede estar desactualizado en el conteo exacto, aunque el mecanismo (status + rationale por hook no registrado) sigue vigente.

## El ecosistema externo

**Frameworks de hooks de git:** `pre-commit` (Yelp, MIT, ~15.200 estrellas, Python, YAML, aísla cada hook en su propio venv, catálogo más amplio de checks pre-armados); Husky (MIT, ~35.000 estrellas, v9+ ya no tiene config propio, se apoya en `package.json`, ecosistema JS); Lefthook (Go, MIT, ~8.000 estrellas, ejecución paralela, ~10x más rápido que Husky en repos grandes, sin runtime dependency).

**Policy engines:** OPA (Apache-2.0, Rego) + Gatekeeper (Apache-2.0, admission controller de Kubernetes sobre OPA) + Kyverno (Apache-2.0, políticas nativas en YAML, sin lenguaje nuevo) — los tres con modo **audit/dryrun** explícito: `dryrun` solo registra en el reporte de auditoría y nunca bloquea, se usa para medir el "blast radius" de una política nueva antes de pasarla a `deny`; el audit de Gatekeeper corre cada 60s por default escaneando recursos existentes. Kyverno vuelca violaciones a `PolicyReport` CRDs (estándar adoptado por el Policy Working Group de Kubernetes); Gatekeeper tiene su propio mecanismo de status, todavía no compatible con `PolicyReport` a 2026. Cedar (AWS, Apache-2.0, motor detrás de Amazon Verified Permissions, reporta 42-60x más rápido que Rego en benchmarks de AWS, con verificación formal). Casbin (Apache-2.0, embebido y liviano, sin servicio externo). Oso: la librería histórica era Apache-2.0 pero el proyecto migró el foco a Oso Cloud (oferta comercial); tratar la adopción de Oso-librería como directriz de arquitectura, no como dependencia viva a día de hoy — no verificado en profundidad, señalado como incertidumbre.

**Guardas destructivas:** no se encontró un "safe-rm" o "trash-cli" mencionado en push points equivalentes a nuestros hooks de git/rm — el patrón dominante en el ecosistema es protección de rama vía `pre-push` + reglas del proveedor (GitHub branch protection), no un hook de shell interceptando `rm`. Esto sugiere que nuestros guardas destructivas de shell (30 hooks por el conteo de arriba) cubren un caso — interceptar comandos peligrosos de un agente LLM antes de ejecutarlos — que el ecosistema git-hooks tradicional no necesita resolver porque no tiene un agente autónomo emitiendo comandos.

**Secret scanning:** gitleaks (MIT, regex, el más rápido, "corre en <1s en un commit típico", el default para pre-commit) vs TruffleHog (**AGPL-3.0 desde v3**, verificado en `github.com/trufflesecurity/trufflehog/blob/main/LICENSE` — bloqueada de plano por el freeze si se evaluara adopción) — TruffleHog verifica si el secreto sigue activo, gitleaks no. detect-secrets (Yelp, Apache-2.0) y git-secrets (AWS Labs, Apache-2.0) también activos en el espacio pre-commit.

**Supply chain / SBOM:** Syft (Apache-2.0, generador SBOM líder open source, CycloneDX/SPDX) + Grype (Apache-2.0, matching de vulnerabilidades) cubren generación+scanning; FOSSA es comercial/propietario y cubre lifecycle management (obligaciones de licencia, reporting centralizado) — un caso de uso que Syft/Grype no cubren solos. Ningún artículo 2026 mencionó `license-checker` (npm, BSD-3-Clause) ni ScanCode Toolkit (Apache-2.0) en comparación directa con Syft/Grype/FOSSA.

**Rate limiting / circuit breaking (Python):** Tenacity (Apache-2.0, retries con backoff exponencial y jitter) + PyBreaker (BSD, circuit breaker clásico de Nygard) se usan típicamente combinados. Emergió en 2026 `pyresilience` (stdlib puro, cero dependencias, un solo decorador `@resilient()` para retry+circuit-breaker+timeout+fallback+bulkhead+rate-limiter+cache) — más nuevo, no evaluado en profundidad aquí.

**Hooks de agentes:** el sistema de hooks de Claude Code (nativo, no OSS) es el más cercano estructuralmente al nuestro: eventos `PreToolUse`/`PostToolUse`, bloqueo por `exit 2` (stderr como razón) o por JSON `hookSpecificOutput.permissionDecision: "deny"` — y el dato clave: **"exit 2 bloquea incluso si el JSON dice `permissionDecision: allow`"**, y un hook con `deny` bloquea incluso bajo `--dangerously-skip-permissions`. Esto es exactamente el mecanismo que nuestros hooks ya usan (stdout JSON o exit 2), lo que confirma que la capacidad de bloqueo SÍ existe en la plataforma subyacente — el problema de los 35 "unproven" no es de mecanismo sino de instrumentación/observación, como ya dice el propio `hook-vitality-budget.yaml`. OpenHands (MIT) usa microagents en `.openhands/`, catalogado en nuestro propio `ai-agent-harness-landscape.yaml` como `status: candidate, proof_level: none` — no se investigó su mecanismo de hooks en profundidad por no ser prioritario frente a Claude Code.

## Tabla de solapamiento

| Nuestra primitiva | Equivalente externo (URL, licencia) | Veredicto | Por qué |
|---|---|---|---|
| Framework de disparo de hooks (`hooks/*.sh` + `.claude/settings.json`) | Claude Code hooks nativo (`code.claude.com/docs/en/hooks`, propietario Anthropic) | **JUSTIFICADO** | No es un competidor externo: es la plataforma sobre la que ya corremos. No hay "adoptar en vez de" posible — es la capa base. |
| `hooks/rate-limiter.sh` + `cos_lib/rate_limiter.py` (token bucket, no registrado) | `tenacity` (Apache-2.0) + `pybreaker` (BSD) o `ratelimit` (MIT) | **JUSTIFICADO, pero apagado** | El diseño (token bucket + lane de prioridad de operador + diversity penalty) es específico del caso agéntico — no hay librería genérica con "lane de prioridad para el operador humano vs. el orquestador". Pero está sin registrar (0 hits en 37.424 filas), así que hoy no aporta nada: el veredicto de diseño es JUSTIFICADO, el de estado operativo es "no cuenta". |
| Guardas destructivas de shell (git, `rm`, ~30 hooks) | No hay equivalente genérico maduro (git branch protection + `pre-push` cubre un caso distinto: humanos empujando a una rama, no un agente ejecutando comandos arbitrarios) | **ÚNICO** | El problema — interceptar comandos peligrosos que un LLM está por ejecutar, antes de que corran — no tiene equivalente en el ecosistema git-hooks tradicional, que asume un humano en el teclado. |
| Gates de calidad (lint/dup/tipos, ~7 hooks) | `pre-commit` (MIT) ya integrado como dependencia (`enforcement-tools` en el manifest) | **REINVENTADO parcialmente** | Ya está registrado como INTEGRATE en `external-tools-adoption.yaml`; si hay hooks de shell duplicando lo que `pre-commit` + `ruff`/`vulture` ya hacen vía `pyproject.toml`, es duplicación de mecanismo, no de intención. No se verificó línea por línea cuáles de los 7 hooks de esta categoría se solapan realmente con la config de `pre-commit` — señalado como pendiente. |
| Secret scanning (dentro de la categoría seguridad, 4 hooks incl. `secret-detector`) | gitleaks (MIT) | **JUSTIFICADO** | `secret-detector` corrió 9.343 veces con 0 blocks observados pero señaliza vía stdout JSON (capability UNOBSERVABLE, no probado incapaz); gitleaks es más maduro en cobertura de patrones pero no tiene integración nativa con nuestro modelo de scope/manifests. Adoptarlo reemplazaría el motor de reglas, no el punto de enganche (seguiría necesitando un hook que lo invoque). |
| `hook_vitality_audit.py` / `hook-vitality-budget.yaml` (ratchet de "guardas sin probar") | Gatekeeper `dryrun` + `PolicyReport` (Apache-2.0) / métrica `gatekeeper_violations` | **JUSTIFICADO, con brecha concreta** | Mismo problema, mecanismo parcialmente distinto: Gatekeeper cuenta *violaciones que habría bloqueado* en modo audit; nuestro audit cuenta *runs sin bloqueo observado*, que es una medida más débil (no distingue "nunca hubo ocasión de bloquear" de "hubo ocasión y no bloqueó"). Ver sección siguiente. |
| Policy engine genérico (OPA/Kyverno/Cedar) como reemplazo de `hooks/*.sh` completo | OPA/Gatekeeper/Kyverno (Apache-2.0) / Cedar (Apache-2.0) | **JUSTIFICADO no adoptar** | Estos motores están diseñados para *admission control declarativo sobre recursos estructurados* (manifests K8s, requests IAM) — no para interceptar comandos de shell arbitrarios de un agente LLM en tiempo real con contexto de sesión/scope/telemetría propios. Migrar exigiría reescribir el modelo de entrada completo sin ganancia clara sobre el problema real (falta de instrumentación, no falta de motor). |
| `manifests/hook-registration-classification.yaml` (status/rationale por hook no registrado) | Gatekeeper `dryrun` enforcement action | **ÚNICO en forma, JUSTIFICADO en función** | Cumple el mismo rol (zona de "todavía no activo, con motivo") pero como YAML estático versionado en vez de un modo de ejecución continuo con métricas en vivo — más liviano, menos observable. |

## Fuentes

- [OPA Gatekeeper 2026: Kubernetes Admission Controller](https://appsecsanta.com/opa-gatekeeper) — 2026
- [OPA Gatekeeper vs Kyverno: K8s Policy Compared](https://computingforgeeks.com/opa-gatekeeper-vs-kyverno-policy/) — 2026
- [OPA Gatekeeper Audit, Mutation & Testing — Part 3](https://www.wasilzafar.com/pages/series/distributed-systems-k8s/opa-gatekeeper-part03-audit-mutation-testing.html) — 2026
- [OPA and Gatekeeper - Policy Enforcement for Kubernetes](https://www.k8s.guide/ecosystem/opa-gatekeeper/) — 2026
- [Kubernetes Admission Control with OPA Gatekeeper and Kyverno](https://www.decryptiondigest.com/blog/kubernetes-admission-control-opa-gatekeeper) — 2026
- [Kyverno vs OPA Gatekeeper (2026)](https://kubernetes.qa/blog/kyverno-vs-opa-gatekeeper/) — 2026
- [Policy-as-Code on AWS: OPA and Kyverno for Kubernetes Security](https://www.red-team.sh/posts/policy-as-code-opa-kyverno-eks-security/) — 2026
- [Constraint Templates | Gatekeeper (oficial)](https://open-policy-agent.github.io/gatekeeper/website/docs/constrainttemplates/)
- [Why I prefer Kyverno over Gatekeeper](https://medium.com/@glen.yu/why-i-prefer-kyverno-over-gatekeeper-for-native-kubernetes-policy-management-35a05bb94964) — 2026
- [Lefthook vs Husky: Which Git Hooks Tool is Better? 2026](https://www.edopedia.com/blog/lefthook-vs-husky/)
- [Pre-commit vs Lefthook vs Husky 2026](https://www.pistack.xyz/posts/2026-04-26-pre-commit-vs-lefthook-vs-husky-git-hooks-management-guide-2026/)
- [Git Hook Frameworks Comparison](https://www.andymadge.com/2026/03/10/git-hooks-comparison/) — 2026
- [pre-commit vs husky: Which is Better in 2026?](https://toolradar.com/compare/pre-commit-vs-husky)
- [Git Hooks Tools Compared: Husky, Lefthook, pre-commit](https://functions.top/git-hooks-tools-compared-husky-lefthook-pre-commit-and-more)
- [husky vs lefthook vs lint-staged 2026](https://www.pkgpulse.com/guides/husky-vs-lefthook-vs-lint-staged-git-hooks-nodejs-2026)
- [OPA vs Cedar vs Zanzibar: 2025 Policy Engine Guide](https://www.osohq.com/learn/opa-vs-cedar-vs-zanzibar)
- [Cedar Policy Language (CPL): 2026 Complete Guide](https://www.strongdm.com/cedar-policy-language)
- [AWS Verified Permissions and Cedar Policy Language Complete Guide](https://hidekazu-konishi.com/entry/aws_verified_permissions_cedar_complete_guide.html) — 2026
- [Top Alternatives to AWS Cedar](https://www.osohq.com/learn/aws-cedar-alternatives-authorization-tools)
- [OpenFGA vs SpiceDB vs Cerbos vs OPA](https://sph.sh/en/posts/external-authorization-management-systems/)
- [Migrating from Open Policy Agent to Amazon Verified Permissions (AWS oficial)](https://aws.amazon.com/blogs/security/migrating-from-open-policy-agent-to-amazon-verified-permissions)
- [Gitleaks vs TruffleHog 2026: Secret Scanner Benchmarks](https://appsecsanta.com/secret-scanning-tools/gitleaks-vs-trufflehog)
- [Gitleaks vs TruffleHog: Which Secrets Scanner Wins in 2026?](https://devsecops.ae/secrets-scanners-comparison-2026/)
- [Secrets scanning for the pre-commit era: Gitleaks, TruffleHog, or Semgrep?](https://iancloud.ai/blog/secrets-scanning-pre-commit-era-gitleaks-trufflehog-semgrep-2026)
- [Secrets Scanning with Gitleaks, TruffleHog, and GitHub (2026)](https://www.decryptiondigest.com/blog/secrets-scanning-pre-commit-ci-enforcement)
- [Gitleaks vs TruffleHog (2026) — Rafter](https://rafter.so/blog/secrets/gitleaks-vs-trufflehog)
- [Best Secrets Detection Tools in 2026 Compared](https://safeguard.sh/resources/blog/best-secrets-detection-tools-2026)
- [trufflehog/LICENSE (oficial, confirma AGPL-3.0)](https://github.com/trufflesecurity/trufflehog/blob/main/LICENSE)
- [Hooks reference - Claude Code Docs (oficial)](https://code.claude.com/docs/en/hooks)
- [Claude Code Hooks (2026): Block Claude Reading .env + 30 Hook Events](https://www.morphllm.com/claude-code-hooks)
- [Claude Code hooks: a practical guide](https://scalably.io/blog/claude-code-hooks-guide)
- [Claude Code hooks reference: PreToolUse, PostToolUse, hookSpecificOutput](https://pushary.com/blog/claude-code-hooks-explained)
- [Claude Code Hooks Complete Guide - Deterministic Enforcement](https://hidekazu-konishi.com/entry/claude_code_hooks_complete_guide.html) — 2026
- [Best SBOM Tools 2026: Syft Leads OSS, FOSSA Leads Commercial](https://appsecsanta.com/sca-tools/sbom-tools-comparison)
- [The 4 Best SBOM Generation Tools Compared (Updated for 2026)](https://finitestate.io/blog/best-tools-for-generating-sbom)
- [SBOM Tools in 2026: Open Source and Enterprise Options Compared](https://raven.io/blog/sbom-tools)
- [Top 6 SBOM Tools for Developers: Our 2026 Best Picks](https://www.aikido.dev/blog/best-sbom-generation-tools)
- [How to Implement Circuit Breakers in Python](https://oneuptime.com/blog/post/2026-01-23-python-circuit-breakers/view) — 2026
- [pyresilience (PyPI, unified resilience patterns)](https://pypi.org/project/pyresilience/) — 2026
- [pybreaker (GitHub, oficial)](https://github.com/danielfm/pybreaker)
- [Python Tenacity: Retry Logic and Backoff Strategies](https://techoral.com/python/tenacity-retry.html)
- [Audit | Gatekeeper (oficial, flags y destinos de audit)](https://open-policy-agent.github.io/gatekeeper/website/docs/audit/)
- [Handling Constraint Violations | Gatekeeper (oficial)](https://open-policy-agent.github.io/gatekeeper/website/docs/violations/)
- [Dryrun enforcement action not recorded as violation in constraint status — gatekeeper#2487](https://github.com/open-policy-agent/gatekeeper/issues/2487)
- [How to Configure Gatekeeper Audit Mode for Compliance Reporting Without Blocking](https://oneuptime.com/blog/post/2026-02-09-gatekeeper-audit-mode-compliance/view) — 2026
- [How to Configure OPA Gatekeeper for Policy Enforcement](https://oneuptime.com/blog/post/2026-01-25-opa-gatekeeper-policy-enforcement/view) — 2026
- [Auditing using constraints | Policy Controller (Google Cloud)](https://cloud.google.com/kubernetes-engine/enterprise/policy-controller/docs/how-to/auditing-constraints)
- [Policy Settings | Kyverno (oficial, deprecación de validationFailureAction)](https://kyverno.io/docs/policy-types/cluster-policy/policy-settings/)
- [Announcing Kyverno Release 1.13](https://kyverno.io/blog/2024/10/30/announcing-kyverno-release-1.13/)
- [Document the deprecation of validationFailureAction — kyverno/website#672](https://github.com/kyverno/website/issues/672)
- [Validate Rules | Kyverno (oficial)](https://kyverno.io/docs/policy-types/cluster-policy/validate/)
- [Policy Reporter | Kyverno (oficial)](https://kyverno.io/docs/subprojects/policy-reporter/)
- [Policy Reporter — Targets (filtros y channels)](https://kyverno.github.io/policy-reporter/core/targets/)
- [Policy Reporter — Priority Mapping / minimumSeverity](https://kyverno.github.io/policy-reporter/core/priority-mapping/)
- [kyverno/policy-reporter (GitHub, Apache-2.0)](https://github.com/kyverno/policy-reporter)
- [How to Implement Kyverno Policy Reports](https://oneuptime.com/blog/post/2026-01-30-kyverno-policy-reports/view) — 2026
- [Alertmanager | Prometheus (oficial)](https://prometheus.io/docs/alerting/latest/alertmanager/)
- [Effective Alerting with Prometheus Alertmanager | Better Stack](https://betterstack.com/community/guides/monitoring/prometheus-alertmanager/)
- [Prometheus Alertmanager: Noise Reduction Rules | Netdata](https://www.netdata.cloud/academy/prometheus-alert-manager/)
- [Tool Deep Dive: Alertmanager Complete Guide](https://www.wasilzafar.com/pages/series/monitoring-observability/monitoring-observability-tool-alertmanager.html)
- [Prometheus Alertmanager: Complete Setup & Configuration Guide 2026](https://apistatuscheck.com/blog/prometheus-alertmanager-guide)
- [Detection Engineering: Common Failures and Practical Fixes](https://www.hunters.security/en/blog/detection-engineering-common-failures-and-practical-fixes-complete-guide) — 2026
- [Identify and fix broken detection rules — CardinalOps](https://cardinalops.com/use-cases/identify-and-fix-broken-detection-rules/)
- [Five of the Top Ten Ways SIEM Rules Silently Fail — CardinalOps](https://cardinalops.com/blog/five-of-the-top-ten-ways-siem-rules-fail-pt1/)
- [How to Continuously Validate Your SIEM Detection Rules — SCYTHE](https://scythe.io/scythe-labs/continuous-validation)
- [Making SIEM Alerts Smarter: Best Practices for Real-World Detection — Cymulate](https://cymulate.com/blog/smarter-siem-alerts-validation/)
- [Rego Policy-as-Code: Admission Control & CI Gates](https://safeguard.sh/resources/blog/opa-rego-policy-as-code-guide) — 2026
- [Policy as Code with OPA and Conftest: 2026 Guide](https://khimananda.com/blog/policy-as-code-with-opa-and-conftest)

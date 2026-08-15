# Diseño — contrato de clase por hook (gate / instrumento)

- Fecha: 2026-08-15
- Alcance: `hooks/` (255 hooks únicos), `.claude/settings.json` (generado),
  `scripts/hook-timing-wrapper.sh`, `manifests/`, `tests/audit/`.
- Método: read-only. Clasificación por script sobre el censo canónico
  (symlink + destino = UNO). `git status --porcelain -- hooks/ scripts/
  manifests/ rules/ .claude/ cognitive-os.yaml` devuelve vacío al cierre.
- Entregable: diseño con costeo, no auditoría. La auditoría de la capa ya está
  en `docs/06-Daily/reports/audit-arq-hooks-2026-08-15.md` y la doy por buena
  salvo donde la corrijo en §7.

---

## 1. Veredicto

**Vale la pena, pero no como está planteado.** Migrar los 255 hooks para que
cumplan una clase declarada cuesta entre 75 y 165 horas y no se justifica contra
una superficie que se está evaluando podar. Lo que sí se justifica es la **fase 1**:
manifiesto de clase para los 40 gates registrados, fail-closed implementado en el
wrapper que ya envuelve a los 162 registros (no hook por hook), y un test en
`tests/audit/` con ratchet bidireccional. **24 a 40 horas**, y deja el crash-como-permiso
cerrado para toda la capa sin tocar 255 archivos.

La palanca que hace que el número cierre: **`scripts/hook-timing-wrapper.sh`
termina en un único `exit $HOOK_EXIT`, y por ahí pasan los 162 registros.**
Fail-closed puede ser una propiedad de la registración, no una reescritura por
hook. Sin esa palanca, el grupo más caro (llevar 40 gates a `set -euo pipefail` +
trap, uno por uno) solo cuesta 40 a 100 horas.

> **Concurrencia, al cierre de este informe.** Una sesión paralela está
> modificando ese mismo wrapper en este momento (`git diff --stat` da +65/-2:
> instrumentación de `stdout_bytes` / `stderr_bytes`). El `exit $HOOK_EXIT`
> está en la línea 463 en HEAD y en la 526 en el working tree. Por eso este
> informe cita archivo y símbolo, no números de línea. Quien tome G3′ el lunes
> tiene que releer el archivo antes de tocarlo: el punto de enganche existe, la
> línea no es estable.

---

## 2. El diseño

### 2.1 Dónde vive la declaración

**En `manifests/hook-class.yaml`. No en el frontmatter del hook, y no en
`cognitive-os.yaml`.** Los tres candidatos tienen evidencia medida en este repo:

| Candidato | Evidencia | Veredicto |
|---|---|---|
| Frontmatter del hook | El contrato de header ADR-067 Fase 2 ya define `# SCOPE:`, `# PURPOSE:`, `# EVENT:`, `# EXIT_CODES:`. Cobertura real hoy: **SCOPE 255/255, PURPOSE 20/255, EVENT 7/255, EXIT_CODES 7/255, MATCHER 4/255** | **No.** Un campo de header al que nadie lee llega al 3%. `SCOPE` llega al 100% porque `scripts/cos_init.py:scope_allows()` lo lee en tiempo de instalación y un archivo sin él se comporta distinto. Un `# CLASS:` sin lector repite el 7/255 de `# EVENT:` |
| `cognitive-os.yaml > harness.hooks` | El driver declara en su cabecera que ése es el registro canónico y **asigna `CONFIG_FILE` en la línea 39 y no lo usa nunca**. El experimento del canario está reproducido en el informe previo: inyectar una entrada al YAML no cambia un byte del `--emit` | **No.** Escribir ahí es escribir en un archivo decorativo |
| Manifiesto en `manifests/` | `manifests/hook-registration-classification.yaml` (661 líneas) ya clasifica los hooks NO registrados con `status` / `rationale` / `next_action`. Es el formato que el repo ya usa para decir cosas sobre hooks | **Sí** |

Forma propuesta, keyed por ruta del hook (la ruta canónica tras `readlink -f`,
para que symlink y destino no se declaren dos veces):

```yaml
# manifests/hook-class.yaml
# Clase de contrato por hook. Autoritativo. Lo leen:
#   - scripts/hook-timing-wrapper.sh  (fail-closed en runtime)
#   - tests/audit/test_hook_class_contract.py  (verificación contra el código)
version: 1
default_class: instrument      # ver §2.3
hooks:
  hooks/secret-detector.sh:
    class: gate
    prevents: "escritura de credenciales al working tree"
    event: PreToolUse
  hooks/tool-sequence-capture.sh:
    class: instrument
  hooks/hook-header-validator.sh:
    class: gate
    prevents: "hook nuevo sin contrato de header"
    event: PostToolUse
    post_hoc_justification: >
      El objeto del juicio (el archivo escrito) no existe antes del Write.
      El exit 2 en PostToolUse devuelve stderr al modelo y fuerza corrección;
      no revierte la escritura, y eso está aceptado.
```

Tres campos obligatorios para `gate`: `class`, `prevents`, `event`. `prevents`
es prosa y no lo verifica nadie, pero es el campo que obliga a escribir qué
impide el gate — sin eso, la declaración se llena a ojo.

### 2.2 Cómo se verifica

**En `tests/audit/test_hook_class_contract.py`, no en un hook.** Este punto es la
corrección directa al encargo: `scripts/scope_closure_gate.py` es la forma
correcta y **no corre en ningún lado** (`grep -rl scope_closure_gate` fuera del
propio script devuelve solo su baseline y dos reportes). El precedente vivo de
este repo son `tests/audit/test_python_naming.py` y `test_bash_naming.py`, que
sí se ejecutan en las lanes. La forma se copia de `scope_closure_gate.py`; el
lugar donde vive, no.

Las tres obligaciones, verificadas **contra el código**:

**V1 — un instrumento nunca bloquea.** Estático. Si `class: instrument` y el
fuente tiene `^\s*exit 2`, `permissionDecision: deny|ask` o
`"decision": "block"` → hallazgo `instrument_can_block`. Hoy da 2
(`session-summary-reminder.sh`, `token-budget-monitor.sh`) más lo que caiga de
los no declarados.

**V2 — un gate falla cerrado.** Dinámico, y es la única de las tres que no se
puede simular leyendo el archivo. Se invoca el hook con un stdin válido para su
matcher declarado pero con las dependencias envenenadas:

```bash
env PATH=/nonexistent HOME=/nonexistent bash hooks/<gate>.sh < fixtures/<matcher>.json
# contrato: exit 2. Cualquier 0 es fail-open y es hallazgo.
```

Un solo fixture por matcher (`Bash`, `Edit|Write`, `Agent`, `""`), no uno por
hook. Sin `python3` ni `jq` en el PATH, todo gate que dependa de un scanner
revienta, y el que devuelve 0 está confesando que un crash es un permiso. Es el
mismo defecto que produjo las 15 filas de `scan_error_fail_open` de
`confidentiality-enforcer` y el que mata al camino ADR-244 de `claim-validator`.

Limitación honesta: V2 detecta el fail-open por **crash**, no el fail-open por
**tragado** (`|| true` sobre la línea que computa el veredicto, `jq -r '.ok //
true'`). Ése no tiene detector genérico y se paga hook por hook. Es la razón por
la que el ratchet importa: V2 pone en rojo lo que puede probar, y el resto entra
como deuda contada.

**V3 — el gate corre donde todavía puede impedir.** Estático sobre
`.claude/settings.json`, que es la verdad generada. Si `class: gate` y sus
eventos registrados no intersecan `{PreToolUse, UserPromptSubmit, SessionStart,
PreCompact}` **y** no hay `post_hoc_justification` → hallazgo `gate_post_hoc`.
El campo de escape existe porque hay gates legítimamente posteriores: los cuatro
validadores de frontmatter juzgan un archivo que no existe antes del Write, y su
`exit 2` en PostToolUse sí sirve (devuelve stderr al modelo). Sin ese campo, el
contrato pide algo imposible y se apaga.

### 2.3 Qué pasa con los no declarados

**Default `instrument`, y el default es detectable.** Un hook sin entrada en el
manifiesto se trata como instrumento, con lo cual hereda la obligación V1: si su
fuente puede bloquear, el test se pone en rojo con `undeclared_blocking` y
fuerza la declaración. El default es fail-open a nivel declaración —el mismo
default de `common.sh`— pero acá el default **produce un hallazgo**, que es la
diferencia entre un default y un agujero.

Hoy eso arranca en **68 hooks** (los que pueden bloquear) y por eso el baseline
inicial no es cero. El ratchet solo baja.

Durante la migración, además, un no declarado **no pasa por el wrapper
fail-closed**: se comporta exactamente como hoy. Prender el contrato no cambia
el comportamiento de nadie hasta que alguien escribe `class: gate` en el
manifiesto. Eso es deliberado: es lo que permite hacerlo de a uno.

### 2.4 El fail-closed, en el wrapper

`scripts/hook-timing-wrapper.sh` (463 líneas en HEAD) envuelve **los 162
registros**; cada comando de `settings.json` es
`bash "$CLAUDE_PROJECT_DIR/scripts/hook-timing-wrapper.sh" <Evento> <hook> ...`.
Termina en un único `exit $HOOK_EXIT` y ya captura `execution_status`, `signal`
y `exit_code` en `hook-timing.jsonl`. La regla fail-closed son ~15 líneas ahí:

```
si clase(hook) == gate  y  HOOK_EXIT ∉ {0, 2}  →  exit 2
```

Con dos excepciones que salen de los datos, no del diseño:

1. **`exit 141` (SIGPIPE) queda excluido.** Hay 26 filas de 141 en el corpus
   actual, todas en `PostToolUse`, de hooks que escriben a un pipe ya cerrado.
   Mapear 141 a 2 convierte 26 problemas de plomería en 26 bloqueos.
2. **Timeout no es bloqueo.** 0 de las 162 entradas llevan `timeout`, y
   `quality-duplicates` promedia 176 segundos en `Stop`. Un gate que tarda no
   es un gate que niega.

Esto es lo que hace que el número cierre: el fail-closed deja de ser
`set -euo pipefail` + `trap` en 40 archivos y pasa a ser una línea en el
manifiesto por hook.

---

## 3. Clasificación de los 255

Criterio, en este orden: (1) nombre del archivo contra los léxicos `gate` /
`instrument` (guard, gate, enforcer, blocker, interceptor / capture, heartbeat,
emit, metric, watchdog, tracker, sync, snapshot…); (2) capacidad real de
bloquear en el fuente; (3) lo que no resuelve ninguno de los dos queda
**ambiguo**. Un hook con nombre de instrumento que puede bloquear también cae en
ambiguo: esa contradicción es exactamente la deuda que hay que triar.

Script: `scratchpad/clasificar.py` (censo canónico + `settings.json` + regex
sobre el fuente).

| Clase | Total | Registrados | No registrados |
|---|---|---|---|
| **instrument** | **127** | 88 | 39 |
| **gate** | **82** | 40 | 42 |
| **ambiguo** | **46** | 26 | 20 |
| | 255 | 154 | 101 |

Cruce con capacidad de bloquear (68 pueden, 187 no — reproduzco el 73% del encargo):

```
gate        reg=1 block=1 -> 36      instrument  reg=1 block=0 -> 88
gate        reg=1 block=0 ->  4      instrument  reg=0 block=0 -> 39
gate        reg=0 block=1 -> 30      ambiguo     reg=1 block=0 -> 24
gate        reg=0 block=0 -> 12      ambiguo     reg=1 block=1 ->  2
                                     ambiguo     reg=0 block=0 -> 20
```

**Los 46 ambiguos son la deuda, y son ambiguos por una sola razón: se llaman
`-check`, `-validator`, `-detector`, `-scan`, `-advisor`.** Ese sufijo no dice si
el hallazgo frena algo o solo se anota. Los 26 registrados:

`auto-checkpoint`, `completeness-check`, `dangerous-env-flag-detector`,
`docker-drift-detector`, `error-pattern-detector`, `large-file-advisor`,
`mcp-scan`, `pending-truth-drift-detector`, `pending-truth-verify-weekly`,
`post-agent-verify`, `private-mode-metrics-gate`, `pyrefly-typecheck-advisory`,
`rate-limit-detector`, `reinvention-check`, `research-quality-validator`,
`rule-md-routing-validator`, `session-summary-reminder`, `skill-drift-detector`,
`skill-md-routing-validator`, `skill-synthesis-scanner`, `surface-fix-detector`,
`token-budget-monitor`, `validator-soak-weekly`, `agent-checkpoint`,
`review-spawner`, `consequence-evaluator`.

Dos de ésos pueden bloquear y no deberían llamarse como se llaman:
`session-summary-reminder` (un "reminder" con `exit 2`) y `token-budget-monitor`
(un "monitor" con `exit 2`). Son los dos casos donde la ambigüedad del nombre ya
se convirtió en un comportamiento que nadie espera.

Tres subgrupos entre los gates que importan para el costeo:

**a) 4 gates registrados que no pueden bloquear ni queriendo:**
`adversarial-review-gate`, `decision-depth-gate`, `private-mode-gate`,
`completion-gate`. Tres de los cuatro corren en `PostToolUse`.

**b) 7 gates que bloquean sobre un efecto ya irreversible** (`PostToolUse` con
matcher `Edit|Write`): `confidentiality-enforcer`, `content-policy`,
`scope-creep-detector`, `adr-section-validator`, `hook-header-validator`,
`rule-frontmatter-validator`, `skill-frontmatter-validator`. Los tres primeros
son el caso roto de verdad (juzgan contenido que se puede leer de
`.tool_input` antes de escribir); los cuatro validadores de frontmatter son el
caso legítimo del `post_hoc_justification`.

**c) 42 gates que existen y no corren.** Incluye `destructive-rm-blocker`,
`destructive-git-blocker`, `secret-audit-pre-commit`, `network-egress-guard`,
`direct-main-guard`, `symlink-mutation-guard`, `rate-limiter`,
`dry-run-preview`, `clarification-interceptor`. Éste es el hallazgo que el
contrato expone y que ninguna clasificación arregla: **el 51% de los gates del
repo son archivos.** Declararlos `gate` sin registrarlos produce 42 hallazgos
`gate_unregistered` el primer día, que es información correcta y que nadie va a
poder bajar en una tanda.

Salud fail-closed de los 82 gates hoy:

| | |
|---|---|
| `set -euo pipefail` | 19 |
| `set -e` o `set -u` parcial | 62 |
| sin `set` | 1 |
| con `trap` | 6 |
| con `\|\| true` | 65 |
| con `2>/dev/null` | 74 |
| con los dos | 63 |

---

## 4. Costeo por grupo de cambio

**Supuesto explícito, y es el que más mueve el número:** una "hora" es una hora
de trabajo de agente supervisado por el operador sobre este repo, incluyendo el
test que prueba el cambio y una corrida de la lane correspondiente. No incluye
la revisión adversarial ni el tiempo de decisión del operador, que va contado
aparte en G6 porque es el único que no se puede paralelizar. Las franjas son
juicio de arquitectura, no salida de `cost_predict.py`; el rango ancho es la
señal de eso.

| Grupo | Qué cambia | n | Horas | Nota |
|---|---|---|---|---|
| **G5** | Manifiesto + `test_hook_class_contract.py` + baseline + 4 fixtures del harness V2 | 1 | **12–20** | Espeja `scope_closure_gate.py` (404 líneas). El costo real está en los fixtures de PATH envenenado |
| **G3′** | Fail-closed en `hook-timing-wrapper.sh` + lectura del manifiesto + exclusión de 141 y timeout | 1 | **8–14** | **Reemplaza a G3.** Toca 1 archivo en vez de 40 |
| ~~G3~~ | ~~`set -euo pipefail` + `trap 'exit 2' ERR` en cada gate registrado~~ | ~~40~~ | ~~40–100~~ | Lo que cuesta si no se usa el wrapper. Agregar `set -e` a un script escrito bajo `set -uo` rompe en lugares impredecibles: 1–2,5 h cada uno, con smoke test |
| **G0** | Declarar los 154 registrados en el manifiesto | 154 | **8–14** | 128 son mecánicos por nombre (~2 min); los 26 ambiguos registrados requieren leer el hook (~15 min) |
| **G2** | Mover a `PreToolUse` los 3 gates sobre efecto irreversible (leer `.tool_input.content` en vez del archivo escrito) | 3 | **9–18** | Reescritura del contrato de entrada de cada uno. Los otros 4 se cierran con `post_hoc_justification` (~1 h total) |
| **G1** | Los 4 gates sin capacidad de bloquear: agregar camino de bloqueo o reclasificar a instrumento | 4 | **4–12** | Probablemente 3 se reclasifican (minutos) y 1 necesita el camino. Cada uno es decisión antes que código |
| **G4** | Los 2 instrumentos que bloquean: sacar el `exit 2` o renombrar | 2 | **1–2** | |
| **G6** | Triaje del operador sobre los 26 ambiguos registrados | 26 | **6,5–13** | **Tiempo de operador, no de agente.** 15–30 min cada uno. Es el único costo irreducible |
| **G7** | Fail-open por tragado (`\|\| true` / `jq '.x // true'` en la línea del veredicto) en los gates que V2 no alcanza | ~13 | **13–39** | Estimado sobre 1/3 de los 40 gates registrados. **No entra en fase 1**: lo destapa el ratchet a medida que se baja el baseline |
| **G8** | Decidir qué hacer con los 42 gates no registrados | 42 | **?** | No es trabajo de migración, es poda. Ver §6 |

**Fase 1 (recomendada): G5 + G3′ + G0 acotado a los 40 gates registrados + G1 +
G4 + G6 = 24 a 40 horas.** Deja cerrado el crash-como-permiso para toda la capa,
los 7 gates en evento equivocado nombrados en un archivo, y todo lo demás
contado en un baseline que solo baja.

**Migración completa (G0 sobre los 255 + G2 + G7 + G8): 75 a 165 horas.** Ése
es el número que no se justifica.

---

## 5. Radio de explosión de prenderlo

Si mañana los gates fallan cerrado sin las excepciones de §2.4, esto es lo que
se rompe, con nombre:

1. **`lethal-trifecta-gate` — el peor caso, y por mucho.** Corre en `PreToolUse`
   con `matcher: ""`, o sea en **toda** llamada a herramienta: 922 invocaciones
   en el corpus actual, 0 bloqueos. Si falla cerrado y su scanner revienta
   (falta `python3`, falta el YAML de reglas, el `.cognitive-os` no está
   inicializado), la sesión muere en la primera llamada a herramienta y el
   operador no tiene forma de saber por qué. Mismo patrón, mismo volumen:
   `protected-config-write-guard`, `cosd-auth-guard`,
   `agent-control-inbound-guard` (922 cada uno).

2. **`confidentiality-enforcer` — bloqueo sin protección.** 15 de las 22 filas
   que loguea son `scan_error_fail_open` con `exit 3` del scanner, todas sobre
   archivos del scratchpad. Fail-closed convierte esas 15 en 15 bloqueos. Y como
   está registrado en `PostToolUse[Edit|Write]`, el bloqueo llega **después** de
   la escritura: se paga todo el ruido y no se evita nada. **No se puede prender
   fail-closed antes de moverlo a `PreToolUse` (G2).**

3. **`quality-duplicates` en `Stop` — la sesión no cierra.** Media de 176.974 ms
   (2 min 57 s), 89,2% del costo total del evento `Stop`, declarado
   `"async": true` sin `timeout` y con `async` ignorado por el harness. Si un
   gate en `Stop` falla cerrado por timeout, la sesión no puede terminar. Por eso
   la excepción de timeout de §2.4 no es opcional.

4. **Los 26 `exit 141` (SIGPIPE).** `context-watchdog`,
   `private-mode-metrics-gate`, `edit-lock-drain-parked`, `auto-checkpoint`
   escriben a pipes cerrados. Un wrapper que mapee "distinto de 0 y de 2 → 2"
   los convierte en bloqueos. Ninguno es un gate hoy, pero el día que alguno se
   declare, explota.

5. **`subagent-budget-enforcer` — el que ya bloquea.** 7.414 invocaciones
   históricas + actuales, 75 `exit 2`. Bloqueó al auditor de la sesión previa a
   los 51 tool calls. Fail-closed no le agrega protección (su camino de bloqueo
   funciona) y sí le agrega un modo nuevo de matar la sesión.

6. **Los 42 gates no registrados.** Si el contrato los declara `gate` y alguien
   decide "registrémoslos, para eso están", entran de golpe 42 hooks que nunca
   corrieron una vez, con fail-closed puesto. `destructive-rm-blocker` y
   `network-egress-guard` sin una sola invocación de rodaje son la definición
   de un contrato que se apaga el segundo día.

**Mitigación que hace el diseño usable:** el fail-closed se prende **por hook,
al declararlo**, no por clase. Un `gate` en el manifiesto sin `fail_closed:
true` sigue comportándose como hoy y solo participa de V1/V3 (estáticas). El
día que se prende, se prende uno. Los cuatro genéricos de `matcher: ""` van
últimos, después de haber pasado el harness V2 con el PATH envenenado.

---

## 6. Si el SO deja de distribuirse

Los tres escenarios cambian el costo de manera muy distinta, y dos de ellos lo
cambian a favor.

**A — sigue distribuyéndose con el instalador actual: el costo sube fuerte.**
El contrato tendría que sostenerse también sobre la proyección al consumidor, y
ahí hay un defecto ya documentado en `diseno-modelo-distribucion-2026-08-15.md`:
la clausura de copiado tiene por semilla exclusivamente `hooks/*.sh`, y
`hooks/_lib/` viaja por un `copytree` que no pasa por la clausura. Consecuencia
directa para este diseño: **una instalación que reciba el gate pero no el
wrapper con la regla fail-closed, o el wrapper sin `hook-class.yaml`, queda
silenciosamente fail-open** — exactamente la falla que ya mató al circuit
breaker en las 16 instalaciones. Habría que sumar el trabajo de clausura y hacer
correr el harness V2 contra un install proyectado y no contra el repo:
**+12 a 20 horas**, y el resultado queda de rehén de `scripts/cos_init.py`.

**B — queda como herramienta del mantenedor: el costo baja y el alcance se
achica solo.** Los 101 hooks no registrados dejan de ser un problema de
clasificación y pasan a ser un problema de borrado, que es más barato y más
honesto. G0 baja de 154 a lo que sobreviva la poda. Desaparece la pregunta de
`scope: both`, desaparece la proyección del wrapper, y hay exactamente una
instalación que mantener en verde. **Fase 1 sin cambios: 24 a 40 horas**, y la
migración completa deja de existir porque no hay 255 hooks que gobernar, hay los
que el mantenedor decida conservar.

**C — modelo plugin (lo que recomienda `diseno-modelo-distribucion`): el mejor
caso, y no cuesta más que B.** Si la unidad de entrega es el repo entero fijado
a un SHA, el cableado viaja adentro del mismo paquete que los archivos que
cablea, y el problema de "llegó el gate, no llegó el wrapper" deja de tener
dónde ocurrir. El contrato se verifica una vez, en el repo, y esa verificación
vale para el consumidor por construcción. **24 a 40 horas y sigue
distribuyéndose.**

**Recomendación de secuencia:** la decisión de distribución es aguas arriba de
este diseño. Si el lunes esa decisión sigue abierta, la fase 1 es igual de
válida en B y C (mismo número) y solo se encarece en A. **No hay que esperar la
decisión para hacer G5 + G3′.** Lo que sí conviene esperar es G0 sobre los 255 y
G8 (los 42 no registrados): clasificar hooks que se van a borrar es trabajo
tirado.

---

## 7. Correcciones a las premisas del encargo

1. **«187 de 255 (73%) no pueden bloquear» — correcto.** Reproducido de forma
   independiente: 68 pueden, 187 no, sobre el censo canónico de 255.

2. **«`confidentiality-enforcer` tiene 3.396 filas de `scan_error_fail_open`» —
   no reproducible.** El archivo hoy tiene **22 filas en total, 15 de ellas
   `scan_error_fail_open`**, y no hay ninguna versión rotada de ese `.jsonl` en
   `.cognitive-os/metrics/.archive/`. El fenómeno es real y peor de lo que
   sugiere el número absoluto: **el 68% de todo lo que ese gate loguea es un
   crash que dejó pasar la escritura**. La magnitud de 3.396 salió de otro
   corpus; conviene rastrear cuál antes de citarla.

3. **«`subagent-budget-enforcer` está registrado en `PostToolUse`: bloquea
   después de ejecutar» — correcto en el registro, engañoso como ejemplo.**
   Está en `PostToolUse` con `matcher: ""`, y su `exit 2` funciona (75 bloqueos
   entre corpus actual e histórico). Pero su objeto es el presupuesto de la
   *próxima* llamada, no la que acaba de correr, así que el evento no está mal
   elegido. **El caso roto de verdad son otros 7**, los que bloquean en
   `PostToolUse[Edit|Write]` sobre un archivo ya escrito, y de ésos los que
   importan son tres: `confidentiality-enforcer`, `content-policy`,
   `scope-creep-detector`.

4. **«`error-pipeline` filtra por `.exit_code`, 33.942 corridas, 12 filas» —
   el campo confirmado, los números de otro corpus.** `hooks/error-pipeline.sh:39`
   dice literal `EXIT_CODE=$(echo "$INPUT" | jq -r '.exit_code // "0"' 2>/dev/null)`.
   En el corpus disponible (20.985 filas actuales + 156.994 archivadas) el hook
   tiene **4.753 invocaciones, todas `exit 0`**, y `error-learning.jsonl` tiene
   **11 filas**. La conclusión se sostiene con holgura; el 33.942 no.

5. **«nada en el repo dice cuáles deberían fallar cerrado» — demasiado fuerte.**
   Hay **tres registros parciales** que ya dicen cosas sobre esto y que nadie
   cruza: `manifests/hook-registration-classification.yaml` (661 líneas, con
   `status` / `rationale` / `next_action` para los no registrados),
   `manifests/hook-quality.yaml`, y el contrato de header ADR-067 Fase 2, que ya
   define un campo `# EXIT_CODES:` y tiene un validador propio
   (`hooks/hook-header-validator.sh`). Lo que falta no es "un lugar donde
   escribirlo" sino **la clase y la verificación contra el código**. Y el dato
   que hay que llevarse de ahí: `# EXIT_CODES:` está en **7 de 255** hooks, que
   es lo que le pasa a un campo de header sin lector.

6. **«`common.sh:190` aplica el default por igual al que mide y al que debe
   frenar» — correcto, pero no es la causa principal.** Solo **67 de 255** hooks
   sourcean `common.sh`. El fail-open masivo no viene de la librería: viene del
   estilo. **65 de los 82 gates tienen `|| true`, 74 tienen `2>/dev/null`, 63
   tienen los dos, y solo 19 tienen `set -euo pipefail`.** Arreglar `common.sh`
   no mueve el número; el wrapper sí.

7. **«hay precedente en el repo: `scripts/scope_closure_gate.py`» — la forma
   sirve, y el encargo ya lo advierte, pero conviene subrayar la conclusión de
   diseño.** Como ese gate no corre en ningún ejecutor, copiar también su
   *ubicación* sería repetir el defecto. El precedente vivo para dónde ponerlo
   son `tests/audit/test_python_naming.py` y `test_bash_naming.py`, que sí se
   ejecutan. El diseño de §2.2 toma el ratchet bidireccional de
   `scope_closure_gate.py` y lo mete en `tests/audit/`.

---

## Anexo — comandos

```bash
# Censo canónico (symlink + destino = UNO) → 255
git ls-files hooks/ | while read -r f; do
  case "$f" in hooks/_lib/*|hooks/_archived/*|*.disabled|*.bak|*.txt) continue;; esac
  readlink -f "$f"
done | sort -u | wc -l

# Clasificación gate/instrument/ambiguo + cruce con registro y capacidad de bloquear
python3 scratchpad/clasificar.py > clases.tsv     # resumen a stderr

# Cobertura de campos de header sobre los 255
#   SCOPE 255 · PURPOSE 20 · EVENT 7 · EXIT_CODES 7 · MATCHER 4

# Gates en PostToolUse sobre efecto irreversible → 7
python3 -c "import json,re; d=json.load(open('.claude/settings.json')); \
print([n for b in d['hooks']['PostToolUse'] if re.search(r'Edit|Write|Bash',b.get('matcher','')) \
       for hk in b['hooks'] for n in re.findall(r'hooks/([\w.-]+\.sh)',hk['command'])])"

# Telemetría por hook (nombre SIN extensión en hook-timing.jsonl)
gzcat .cognitive-os/metrics/.archive/hook-timing-*.jsonl.gz \
  | cat - .cognitive-os/metrics/hook-timing.jsonl \
  | python3 -c "import sys,json,os,collections; c=collections.defaultdict(collections.Counter); \
[c[os.path.basename(str(json.loads(l).get('hook','?'))).replace('.sh','')].update([json.loads(l).get('exit_code')]) \
 for l in sys.stdin if l.strip()]; print({k:dict(v) for k,v in c.items() if v.get(2)})"

# El único exit por el que pasan los 162 registros (la línea se mueve: buscar el símbolo)
grep -nF 'exit $HOOK_EXIT' scripts/hook-timing-wrapper.sh
git show HEAD:scripts/hook-timing-wrapper.sh | grep -nF 'exit $HOOK_EXIT'   # 463 en HEAD

# No-mutación
git status --porcelain -- hooks/ scripts/ manifests/ rules/ .claude/ cognitive-os.yaml
```

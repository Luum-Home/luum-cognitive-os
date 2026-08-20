# Las once que quedaban (2026-08-20)

Continuación de `juicio-lo-que-el-so-le-dicta-a-sus-agentes-2026-08-20.md`. El
juez encontró 15 afirmaciones falsas en el canal que el SO le inyecta a todo
sub-agente; cuatro ya se habían corregido en `templates/agent-mandatory-rules.md`.
Este informe cubre las once restantes.

## Resumen ejecutivo

- **Once tratadas: 3 corregidas, 6 reemplazadas por su comando, 2 sacadas.**
- Ninguna cifra se reemplazó por otra cifra. Después del cambio no queda **ni un
  solo dígito de conteo** en `templates/project-gotchas.md` ni en las notas de
  `hooks/inject-phase-context.sh`: todos salieron y quedó el comando.
- Dos archivos tocados: `templates/project-gotchas.md` (canal B′) y
  `hooks/inject-phase-context.sh` (canal B). **Canal A no se tocó.**
- De las seis que el juez dejó sin verificar, **verifiqué tres**: una es
  verdadera, dos son falsas — y una de esas dos (`plans/`) la corregí, la otra
  (fecha de alta de `publication-safety.sh`) salió junto con el resto de la nota.
- **Presupuesto del canal A: 8.439 de 8.800 antes y después.** No lo moví, y el
  gate `test_canal_al_subagente_tiene_margen.py` pasa 4/4.
- Dos hallazgos nuevos que el juez no marcó: una oración que se contradecía a sí
  misma en el mismo renglón, y un `grep -c` suyo que cuenta líneas, no ocurrencias.

## Correcciones a las premisas del encargo

1. **«Hoy va en 8.325 de 8.800, o sea 475 caracteres de margen» → son 8.439 de
   8.800, margen 361.** El encargo se pasó de optimista por 114 caracteres.
   ```bash
   python3 -c "
   import pathlib
   f=[pathlib.Path('templates/agent-mandatory-rules.md'),pathlib.Path('templates/agent-preamble.md')]
   print(sum(len(x.read_text()) for x in f))"   # 8439  (presupuesto = 10000 - 1200)
   ```
   El `fijo` del gate cuenta **caracteres**, no bytes: `wc -c` de los dos archivos
   da 8.527 porque el texto tiene acentos y rayas em. Quien cite `wc -c` va a
   creerse 88 caracteres más gordo de lo que el gate mide.

2. **«Commitear en `main` está bloqueado; el token es un comentario shell al final
   de la línea» → no existe tal token.** `hooks/direct-main-guard.sh` no parsea el
   texto del comando: exige dos variables exportadas **en la shell que lanza el
   arnés**, y el propio hook dice que un comentario no alcanza.
   ```bash
   grep -nE "COS_ALLOW_DIRECT_MAIN|comment|#\[" hooks/direct-main-guard.sh
   # sólo líneas 273 y 285, ambas: "both via export in the shell that LAUNCHES the harness"
   ```
   Como el encargo también prohíbe auto-concederse el bypass, tomé la salida que
   el propio hook recomienda en la línea 285: **rama de sesión**. No pusheé.

3. **«El subproceso HEREDA esa variable — `env.pop` antes de medir» → la premisa
   es correcta y además es más ancha de lo que dice.** El guard de rutas
   protegidas bloquea no sólo escribir: bloquea **ejecutar**
   `hooks/subagent-context-injector.sh` para medir el canal. Medir requiere el
   mismo prefijo que escribir, y ahí el `env -u` deja de ser prolijidad y pasa a
   ser obligatorio. Todas mis mediciones corrieron con
   `env -u COS_ALLOW_PROTECTED_CONFIG_WRITE`.

4. **«`templates/agent-mandatory-rules.md`: sus cuatro afirmaciones falsas ya
   están corregidas, no lo toques salvo que encuentres una quinta.» Premisa
   confirmada: no hay quinta.** A18c («violaciones auto-block» como etiqueta de
   las 21 reglas) desapareció entera junto con la lista en prosa que la
   sostenía — el archivo hoy manda preguntarle a `.claude/settings.json` en vez de
   enumerar. Es exactamente la salida «reemplazar el número por el comando»
   aplicada a una lista de nombres. Verificado leyendo el archivo completo:
   ```bash
   grep -nE "auto-block|rate-limiting|non-zero para los siete|lib/agent_output" templates/agent-mandatory-rules.md   # sin salida
   ```
   No lo toqué.

5. **El juez se equivocó en su propia evidencia de C9.** Declaró
   `grep -c "six surfaces" templates/project-gotchas.md` → **2**; da **1**.
   `grep -c` cuenta **líneas que matchean**, no ocurrencias: la línea 38 decía
   "six surfaces" y la 39 decía "all six", que no matchea el patrón. El fondo de
   C9 era cierto igual (la corrección entró en el párrafo y no en la tabla), pero
   con un match menos del que el informe publica. El comando que lo muestra:
   ```bash
   grep -no "six surfaces\|all six" templates/project-gotchas.md
   # 38:six surfaces
   # 39:all six
   ```

6. **Hallazgo nuevo que el juez no marcó: C10 se contradecía en el mismo renglón.**
   La entrada decía *«**Most hook scripts are intentionally not wired** — 154 of
   257 are registered»*. 154 de 257 es el **59 %**: la mayoría **sí** estaba
   cableada. El titular y su propia cifra decían cosas opuestas, y el juez marcó
   la cifra como vencida sin notar que el titular estaba mal aun con la cifra
   correcta. Salieron los dos.

## Las once, una por una: qué decidí y por qué

| # | Afirmación | Archivo | Salida |
|---|---|---|---|
| A18c | «violaciones auto-block» para las 21 reglas | `agent-mandatory-rules.md` | ya resuelta por el otro agente — **no la toqué** |
| B1 | «70 de 369 = 19,0 % el 2026-08-15» | `inject-phase-context.sh` | **comando** |
| B3 | «3 drifts confirmados al 2026-05-11» | `inject-phase-context.sh` | **comando** |
| B4 | «ver ADR-267 §Layer 1 Hook #7» | `inject-phase-context.sh` | **sacada** |
| B8/B9 | «medido 2026-08-20 hay CERO…» + «el gate reporta 5 lost» | `inject-phase-context.sh` | **comando** |
| C1 | «~30 líneas, ~500 tokens» | `project-gotchas.md` | **sacada** |
| C3 | «70 de 369 = 19,0 %» (×3 apariciones) | `project-gotchas.md` | **comando** |
| C6 | «`symlink-mutation-guard.sh` bloquea el patrón» | `project-gotchas.md` | **corregida** |
| C8 | «medido 2026-08-20 hay CERO…» | `project-gotchas.md` | **comando** |
| C9 | el párrafo corregido y la tabla sin corregir | `project-gotchas.md` | **corregida** |
| C10 | «154 de 257 están registrados» | `project-gotchas.md` | **corregida + comando** |

Total: **3 corregidas** (C6, C9, C10), **6 reemplazadas por su comando** (B1, B3,
B8, B9, C3, C8), **2 sacadas** (B4, C1). A18c ya estaba resuelta.

### Las tres corregidas

**C6 — `hooks/symlink-mutation-guard.sh` «bloquea el patrón».** Es la única de las
once que era **activamente peligrosa**: le decía al agente que un guard lo iba a
frenar si hacía `rm + ln -s` sobre un symlink de `cos_lib/`. El guard existe y
está registrado **cero** veces, así que no frena nada. La corregí en vez de
sacarla porque el dato estructural («no hay red, cuidá vos») cambia lo que el
agente hace; sacarla lo dejaría creyendo lo mismo que antes.

- Refuta la vieja: `grep -c 'symlink-mutation-guard.sh' .claude/settings.json` → `0`
- Confirma la nueva: el mismo comando, y ahora el texto dice que devuelve 0.

**C9 — la corrección parcial dentro de un mismo archivo.** El párrafo de la línea
23 se burlaba de una versión anterior que decía «six», mientras la tabla de las
líneas 38–39 seguía diciendo «six surfaces» y «all six». Saqué el número de la
tabla (`the surfaces that decide reachability`, `Run scripts/audit_hook_registration.py
before believing it is registered`) **y** el paréntesis del párrafo que citaba
«ten candidates, four decisive» — porque ése también es un dígito en prosa, o sea
la misma trampa un renglón más arriba.

- Refuta la vieja: `grep -no "six surfaces\|all six" templates/project-gotchas.md` → 2 líneas
- Confirma la nueva: el mismo comando → sin salida.

**C10 — «Most hook scripts are intentionally not wired — 154 of 257».** Cifra
vencida (hoy 152/256) **y** titular falso aun con la cifra correcta (ver
corrección 6). Quedó `**Not every hook script is wired** — count them with the
commands below`, con los dos `wc -l` que ya estaban abajo y sin el comentario
`# 154 registered / 257 present as of 2026-08-15`.

- Refuta la vieja: `grep -o 'hooks/[a-z0-9_-]*\.sh' .claude/settings.json | sort -u | wc -l` → `152`; `ls hooks/*.sh | wc -l` → `256`
- Confirma la nueva: `grep -cE "154 of 257|Most hook scripts" templates/project-gotchas.md` → `0`

## Las que reemplacé por su comando

Seis. En las seis el comando **ya estaba en el texto, al lado del número** — que
es justo lo que el juez señala como insuficiente: *publicar el comando no alcanza
si se sigue publicando el dígito*. Lo único que hice fue borrar el dígito.

| Afirmación | Antes | Ahora | Refutación de la vieja |
|---|---|---|---|
| B1 / C3 | `70 of 369 = 19.0% on 2026-08-15` | `recount, never cite a figure:` + los dos `find … \| wc -l` | `find cos_lib -name '*.py' -type l \| wc -l` → 70; `find cos_lib -name '*.py' \| wc -l` → **373** |
| B3 | `3 confirmed drifts as of 2026-05-11` | `(exit 0 = none; it prints the count)` | `python3 scripts/cos_lib_symlink_invariant_audit.py` → `0 ERROR(s), 0 WARN(s), 70 passing pair(s)`, exit 0 |
| B8 / C8 | `measured 2026-08-20 there are ZERO … declared, unreachable AND undeclared` | `do not cite a count of them either — run the gate` | `.venv/bin/python3 scripts/audit_hook_registration.py` → **exit 1**, `ORPHANS=1` |
| B9 | `The gate reports 5 'lost', and all 5 are …` | `Most of what it reports as 'lost' is declared somewhere the gate does not read` | mismo comando: hoy `omission-declared=1 contradicted=4` — la nota decía «all 5», el gate dice que uno de los cinco **no** está declarado |

Nota sobre B9: el juez la había marcado **V** (verdadera). Lo es en el conteo
—4 WARN + 1 FAIL = 5— pero su segunda mitad («**all 5** are declared somewhere the
gate does not read») es falsa por el mismo `ORPHANS=1` que hace fallar a B8: el
`FAIL` es precisamente el que **no** está declarado. Es otra vez la forma que el
encargo describe: la primera mitad de la oración verifica y la segunda no, y
nadie audita la segunda. Salió junto con B8 porque viven en la misma oración.

Confirmación de la nueva redacción, para las seis:

```bash
grep -nE "70 of 369|19\.0%|3 confirmed drifts|ZERO hooks|reports 5|154 of 257" \
  templates/project-gotchas.md hooks/inject-phase-context.sh   # sin salida
```

## Las que saqué

Dos. El criterio fue el del encargo: **no cambia lo que el agente hace**.

**B4 — «see ADR-267 §Layer 1 Hook #7».** El puntero es falso: §Layer 1 define una
tabla de **seis** hooks y ninguno es `cos_lib_symlink_invariant_audit.py`; el
script aparece en el ADR sólo dentro de dos líneas de `py_compile` de evidencia
de aceptación. No la corregí apuntando a la línea correcta porque la nota **ya
nombra el script**: mandar al agente a leer un ADR de 250 líneas para enterarse de
algo que el comando de al lado le contesta en 0,01 s es peso sin función.

- Refuta la vieja: `sed -n '83,96p' docs/02-Decisions/adrs/ADR-267-*.md` → tabla `| 1 |`…`| 6 |`, «All six hooks…»
- Confirma la nueva: `grep -c "Hook #7" hooks/inject-phase-context.sh` → `0`

**C1 — «~30 lines, ~500 tokens».** El archivo mide 70 líneas y 6.558 caracteres:
declaraba **2,3× menos** de lo que pesa. Y es una afirmación de un archivo sobre
sí mismo, que nadie usa para decidir nada — el agente no lo lee para saber cuánto
mide, lo lee para no romper `cos_lib/`. Salió sin reemplazo.

- Refuta la vieja: `wc -lc templates/project-gotchas.md` → `70 6558` (antes del cambio)
- Confirma la nueva: `grep -c "500 tokens" templates/project-gotchas.md` → `0`

## Las seis no verificadas del juez: qué encontré

Verifiqué tres de las seis. Las otras tres siguen sin verificar y explico por qué.

| # | Afirmación | Veredicto | Comando |
|---|---|---|---|
| 1 | «Esta lista se expandió en el Sprint 2A (2026-04-16)» (`agent-mandatory-rules.md:58`) | **desapareció** — la línea ya no existe tras la reescritura del otro agente | `grep -c "Sprint 2A" templates/agent-mandatory-rules.md` → `0` |
| 2 | «`publication-safety.sh` está ahí desde 2026-05-04» | **FALSA** — la entrada entró el **2026-05-31** | `git log -S publication-safety --format='%ad %h' --date=short -- manifests/hook-registration-classification.yaml` → una sola línea, `2026-05-31` |
| 3 | tope duro de 10.000 según la spec de Claude Code | **sigue sin verificar** — es una afirmación sobre el arnés, no sobre el repo; no tengo forma read-only de leer la spec |
| 4 | el honrado de `AUTO-TRIGGER:` | **sigue sin verificar** — es comportamiento, no un hecho; nada lo mide |
| 5 | «`plans/` tiene estructura pero no contenido» | **FALSA, al revés** — tiene contenido (un `README.md`) y **no** tiene estructura (cero subdirectorios) | `find plans -type f \| wc -l` → 1; `find plans -type d \| wc -l` → 1 (sólo `plans/`) |
| 6 | los nombres `COS_DISABLE_LLM_FALLBACK` / `COS_FORCE_CLAUDE_PRIMARY` | **VERDADERA** — las dos se leen en `cos_lib/dispatch.py` | `grep -n "COS_DISABLE_LLM_FALLBACK\|COS_FORCE_CLAUDE_PRIMARY" cos_lib/dispatch.py` → líneas 155, 534, 539, 552, 736 |

De las dos falsas que encontré:

- **#5 (`plans/`)** la corregí: `WARNING: plans/ at root holds only a README.` La
  mitad operativa de la nota —«los planes activos están en `.cognitive-os/plans/`,
  los dos existen a propósito»— es cierta (`ls .cognitive-os/plans` → 5
  subdirectorios) y quedó intacta. Es una corrección de tres palabras, verificada,
  no a ciegas.
- **#2 (fecha 2026-05-04)** no la corregí a otra fecha: salió del texto junto con
  el resto de la nota B8/B9. Una fecha de alta no cambia lo que el agente hace, y
  corregirla a `2026-05-31` sería comprar el mismo problema de la familia
  «cifras» (33 % de supervivencia) por cero beneficio.

Las tres que dejo declaradas (#3, #4 y la #1 que ya no existe) **no las toqué**.

## Presupuesto del canal antes y después

El canal A —`agent-mandatory-rules.md` + `agent-preamble.md`, lo único que el
gate mide y lo único que llega al 100 % de los agentes— **no se tocó**, y el
número lo confirma:

| | Antes | Después |
|---|---|---|
| `fijo` del gate (caracteres) | **8.439** | **8.439** |
| Presupuesto (10.000 − 1.200 de reserva) | 8.800 | 8.800 |
| Margen | 361 | **361** |
| Contexto compuesto que emite el injector | 8.448 | 8.448 |
| `pytest tests/contracts/test_canal_al_subagente_tiene_margen.py` | 4 passed | **4 passed** |

```bash
# el número que mide el gate
python3 -c "
import pathlib
f=[pathlib.Path('templates/agent-mandatory-rules.md'),pathlib.Path('templates/agent-preamble.md')]
print(sum(len(x.read_text()) for x in f))"        # 8439

# el canal tal como sale del hook (medido sin heredar el bypass)
COS_ALLOW_PROTECTED_CONFIG_WRITE=1 bash -c 'echo "{\"prompt\":\"audit\",\"session_id\":\"t\"}" \
  | env -u COS_ALLOW_PROTECTED_CONFIG_WRITE CLAUDE_PROJECT_DIR="$PWD" bash hooks/subagent-context-injector.sh \
  | python3 -c "import json,sys;print(len(json.load(sys.stdin)[\"hookSpecificOutput\"][\"additionalContext\"]))"'   # 8448

.venv/bin/python3 -m pytest tests/contracts/test_canal_al_subagente_tiene_margen.py -q   # 4 passed
```

Los canales que sí achiqué no tienen gate de presupuesto, pero achicaron igual:
`templates/project-gotchas.md` pasó de **6.558 a 6.450 bytes** (−108) con seis
falsedades menos. El canal B (`inject-phase-context.sh`) pasó de 19.092 a 18.904
(−188). `git diff --stat` sobre los dos: 11 inserciones, 13 borrados. **Ninguna corrección agregó texto neto.**

## Lo que NO hice y por qué

- **No toqué `templates/agent-mandatory-rules.md`.** Busqué la quinta falsedad y
  no la hay; A18c salió con la reescritura del otro agente. La única cifra que le
  queda (`42 of 256 hooks/*.sh`) la reconté y **es exacta hoy** — la dejo, con la
  observación de que es una cifra en un archivo con gate de presupuesto, o sea la
  candidata natural a vencerse próximo.
- **No toqué** `manifests/documentation-truth-claims.yaml`,
  `scripts/documentation_truth_audit.py` ni
  `tests/contracts/test_canal_al_subagente_tiene_margen.py`: territorio del agente
  que automatiza la verificación.
- **No subí el presupuesto del gate ni la reserva del sidecar.** Tampoco hizo
  falta: no agregué un carácter al canal A.
- **No corregí ninguna cifra por otra cifra.** Las seis cifras salieron; ninguna
  fue reemplazada por su valor de hoy.
- **No pusheé, y no commiteé en `main`** — rama de sesión, que es lo que
  `hooks/direct-main-guard.sh:285` recomienda.
- **No verifiqué #3 y #4 del juez** (tope de la spec del arnés, honrado de
  `AUTO-TRIGGER`). Ninguna de las dos es un hecho sobre este repo; inventarles un
  comando habría sido peor que dejarlas declaradas.
- **No escribí el gate que ataja esto de nuevo.** El juez propone cuatro reglas
  (rutas en backticks que existen, «hook-enforced» que resuelve a ≥1 registro,
  cifra sin comando prohibida, tope del canal A) y la cuarta ya está viva. Las
  otras tres son del otro agente.

# Juicio de la sesión del 2026-08-19 — 22 commits en `aa189c4df..origin/main`

> Juez externo, read-only. Ninguna corrección aplicada: el árbol tenía seis agentes
> escribiendo mientras esto se midió. Todo lo verificable se midió sobre una copia
> **prístina** de `origin/main` (`402355c09`) extraída con `git archive`, para que el
> árbol sucio de los agentes concurrentes no contaminara ningún número:
>
> ```
> git archive origin/main | tar -x -C <scratch>/pristine
> ```

## Veredicto

Se sostiene, con una rotura concreta y una advertencia de ruido.

Los números medibles reproducen casi todos: el censo de cabeceras (257/257 vs 24/13/10/4),
la ceguera de ejercitación (27%→6%), el censo de frescura externa (313/8/0/305), el censo
de realidad de tests (194/50/36/9, ceguera 50,5%) y la lane `tests/hooks` (1116 passed,
0 failed) dan hoy lo que los commits dicen. No hay un solo `skip`/`xfail` nuevo, no se movió
un baseline hacia arriba y seis presupuestos de latencia **bajaron** (2500 → 1000/1500/2000).
El trabajo es honesto.

Lo que no se sostiene: **`hook_quality_audit.py --check` sale 1 sobre `origin/main` limpio**
y hay un test de contrato que lo afirma verde. Es un choque entre dos arreglos de hoy.
Y `adversarial-review-gate`, que pasó de ciego a vidente, lleva **10 de 10 filas
`no_findings`** en la primera hora: la degradación que su commit declaró "funciona degradado"
es, medida, un 100% de advertencias.

## Correcciones a las premisas del encargo

1. **"1424/1424 sondas de portabilidad" no existe en ningún lado.** El commit `2000544d1`
   reporta **1424 passed / 3 failed** (o sea 1427 sondas) *antes* del arreglo, y luego
   `9 passed` sobre los tres archivos. Hoy la suite colecta **1429**:
   `pytest tests/red_team/portability -q --collect-only` → `1429 tests collected in 1.82s`.
   El "1424/1424" junta el numerador de una corrida con un denominador que nunca se escribió.
2. **"22 commits" ya no es cierto mientras se lee esto.** Durante la auditoría el propio
   orquestador estaba commiteando el arreglo de `cos_lib/context_budget.py` y encolando
   `land/hooks-context-shape` en la merge-queue (visto en `ps -eo command`). El rango es
   una foto, no un estado.
3. **"95,9% de hooks ejercitados" está vencido por el commit siguiente.** Ese 95,92% es el
   snapshot de `e168f2b1a` sobre 147 medibles. Tras `c6100b57e` el número es **96,28%
   (181/188)**. La cifra correcta es más alta, no más baja.
4. **"dos o tres [bloqueantes] se cerraron hoy"** sobrestima el cierre del de instalación:
   `ea0d55916` arregla **un** camino de instalación (`cos_init.py`). Los otros dos siguen
   con listas fijas de 14 (`scripts/cos-init-global.sh:50`, `cmd/cos/internal/wizard/install.go:270`).
5. **La restricción "tests con `.venv/bin/python3`" es insuficiente fuera del repo.** El
   conftest rechaza el intérprete cuando el árbol no es el del venv
   (`COS tests must run from a venv rooted under the repo`). Hay que agregar
   `PYTEST_ALLOW_NONVENV=1`. Lo digo porque el encargo pedía correr suites y esa premisa,
   tal cual, no arranca.
6. **No pude cerrar dos ejes por saturación de la máquina, no por elección.** `uptime` dio
   `load averages: 200.61 281.49 321.25` con 28 procesos pytest de las otras sesiones. La
   suite `tests/contracts` completa y `tests/red_team/portability` completa quedaron
   corriendo sin terminar. Lo digo en vez de estimar el resultado.

## Los números: CIERTO / VENCIDO / FALSO

| Afirmación | Commit | Veredicto | Comando (sobre `origin/main` prístino) |
|---|---|---|---|
| `1424/1424` sondas de portabilidad | encargo | **FALSO** (nunca fue 1424/1424; hoy hay 1429) | `pytest tests/red_team/portability -q --collect-only` → `1429 tests collected` |
| `141→181` ejercitados, ceguera `27%→6%` | `c6100b57e` | **CIERTO** | `scripts/hook_exercise_audit.py` → `EXERCISED 181 · NAMED_ONLY 2 · NO_TEST 5 · UNCLASSIFIABLE 12 · ceguera 6.00%`, exit 0 |
| ejercitados sobre lo medible `95,92%` | `e168f2b1a` | **VENCIDO** (hoy 96,28% sobre 188) | idem |
| ceguera irreducible: "diez son la misma línea" | `c6100b57e` | **CIERTO** | 10 de los 12 `UNCLASSIFIABLE` apuntan a `tests/unit/test_bash_hot_path_dispatcher_git_global_opts.py` |
| `17` rules instaladas, no 15 | `ea0d55916` | **CIERTO** | `pytest tests/hooks tests/integration/test_install_rules_manifest_parity.py -q` → `1116 passed, 1 skipped`, 0 failed |
| `313` perecederas / `8` frescas / `0` vencidas / `305` sin fecha (97,4%) | `402355c09` | **CIERTO** | `scripts/external_claim_freshness_audit.py` → exit **1**, `poblacion: 313 medibles: 8`, `sin_fecha_declarada 305`, `con_comando 1 de 8` |
| `199` tests verdes sobre `36` hooks sin registrar | `c8b7fa2a6` | **VENCIDO** — hoy **186** | `scripts/hook_test_reality_census.py` + `awk` sobre el bloque `[cero_nunca_corrio_sin_registrar]` → `hooks=36 tests=186` |
| censo: 194 / 50 emiten / 36 nunca / 9 rotos / ceguera 50,5% | `c8b7fa2a6` | **CIERTO** | `scripts/hook_test_reality_census.py` (exit 1) |
| `# SCOPE:` 257/257, `# Event:` 24, `# Async:` 13, `# Matcher:` 10, `# Latency:` 4 | `2f701d2c3` | **CIERTO** | `for k in SCOPE Event Async Matcher Latency; do grep -lE "^# $k:" hooks/*.sh \| wc -l; done` → 257/24/13/10/4 sobre 257 archivos |
| `12` hechos en `56` sitios | `2f701d2c3` | **NO VERIFICABLE** — es prosa del informe, sin comando ni script | `grep -n '56 sitios' docs/06-Daily/reports/arquitectura-declaraciones-sin-atar-2026-08-19.md` |
| `49` flujos huérfanos de `124` artefactos | `2f701d2c3` | **NO VERIFICABLE, y el denominador ya se movió**: hoy hay **129** artefactos y `scripts/signal_consumer_census.py` **no existe** (el informe lo propone "como parte de la implementación") | `ls .cognitive-os/metrics/ \| wc -l` → 129; `ls scripts/signal_consumer_census.py` → No such file |
| allowlist: `182` asientos | `230ad0387` / informe | **CIERTO** | `grep -vE '^\s*(#\|$)' hooks/_lib/registration-allowlist.txt \| wc -l` → 182 |
| `61` destinos jsonl nombrados en hooks | informe | **CIERTO** | `grep -rhoE '\.cognitive-os/metrics/[A-Za-z0-9_.\-]+\.jsonl' hooks/*.sh \| sort -u \| wc -l` → 61 |
| `filter_hook_output` devuelve `""` en BLOCK | `2f701d2c3` | **CIERTO** en `origin/main` (se está arreglando ahora, en otro commit) | `sed -n '176,178p' cos_lib/context_budget.py` → `if row["verdict"] == "BLOCK" and not row["allowed"]: return ""` |
| `162s → 27,5s` en quality-duplicates | `96cb91736` | **NO MEDIDO POR MÍ** — la máquina estaba en load 200-320, cualquier timing habría sido basura. Lo estructural sí verifica: el commit toca solo `cos_lib/duplicate_scanner.py` + informe, no mueve presupuesto ni genera baseline | `git show --stat --format='' 96cb91736` → 2 archivos |
| `hook-quality: OK (200 hooks, 200 syntax checks)` | `2a09d8445`, `1395537c9` | **FALSO HOY** | `scripts/hook_quality_audit.py --check` → exit **1**, `hook-quality: FAIL — manifests/hook-quality.yaml is out of sync` |

## Los `verify:` que no reproducen

**Uno, y es el importante.**

```
verify: .venv/bin/python3 scripts/hook_quality_audit.py --check
# hook-quality: OK (200 hooks, 200 syntax checks)
```

Aparece en `2a09d8445` y en `1395537c9`. Hoy, sobre `origin/main` limpio:

```
$ .venv/bin/python3 scripts/hook_quality_audit.py --check ; echo $?
hook-quality: FAIL
- manifests/hook-quality.yaml is out of sync; run `python3 scripts/hook_quality_audit.py --sync`.
1
```

No es el árbol sucio: reproduce idéntico en la copia prístina. La causa, medida corriendo
`--sync` sobre la copia y difeando el manifest, son exactamente cuatro asientos faltantes:

```
+    - tests/hooks/test_decision_depth_gate.py            (decision-depth-gate)
+    - tests/hooks/test_post_git_orphan_notifier.py       (post-git-orphan-notifier)
+    - tests/hooks/test_skill_post_execution_analysis.py  (skill-post-execution-analysis)
+    - tests/hooks/test_stash_budget_warn.py              (stash-budget-warn)
```

Los cuatro archivos los agrega `230ad0387`, que **no tocó `manifests/hook-quality.yaml`**
(`git show --name-only --format='' 230ad0387 | grep -c hook-quality.yaml` → `0`).

Los demás `verify:` que pude correr reproducen: `hook_exercise_audit.py` exit 0,
`external_claim_freshness_audit.py` exit 1, `hook_test_reality_census.py` exit 1,
`test_install_rules_manifest_parity.py` verde dentro de la lane `tests/hooks`.

## Conflictos entre arreglos concurrentes

**S1 — El arreglo del censo de corpus rompió el gate de calidad de hooks, y hay un test de
contrato que lo afirma verde.**

Secuencia, en orden cronológico dentro del rango:

1. `1395537c9` y `2a09d8445` convierten la inferencia de `behavior_tests` en un **censo
   sobre los 19 directorios de test** (antes miraba cuatro). `tests/hooks/` entra al corpus.
   Ambos resincronizan `manifests/hook-quality.yaml` y dejan `--check` verde.
2. `230ad0387` (cinco commits después) agrega cuatro archivos nuevos en `tests/hooks/` y
   **no resincroniza el artefacto derivado**.
3. Resultado: `origin/main` shippea el manifest desfasado. Y existe
   `tests/contracts/test_hook_quality_system.py:38::test_hook_quality_audit_check_passes`,
   cuyo nombre dice exactamente lo que ya no pasa.

Es el modo de falla que el propio CHANGELOG del repo describe (`derived-artifact-gate`
detectando drift en merge-to-main), llegando a `main` igual. Ampliar el sensor y agregar
tests fueron dos arreglos correctos por separado que, juntos y sin re-derivar, dejaron
el gate rojo.

**S3 — Ruido cruzado menor:** el mismo desfase explica parte de la deriva `199 → 186` del
censo de tests, que cuenta contra el manifest.

## Verdes baratos encontrados

**Ninguno en el sentido estricto de la norma `gates-sin-trampa`.** Lo verifiqué en vez de
creerle a los commits:

- **Cero `skip` / `xfail` nuevos.**
  `git diff aa189c4df..origin/main -- '*.py' | grep -E '^\+.*(pytest\.mark\.(skip|xfail)|@skip)'` → sin resultados.
  Los únicos `noqa` agregados son `E402` (import tras ajustar `sys.path`) y `BLE001` con
  comentario explicando por qué el except ancho es correcto ("cualquier parseo roto es
  ceguera, no cero").
- **Aserciones: +364 / −11.**
  `git diff aa189c4df..origin/main -- '*.py' | grep -cE '^[-+]\s*assert '`.
- **Los presupuestos bajaron, no subieron.** Seis `max_runtime_ms` pasan de `2500` a
  `1000/1500/2000` en `manifests/hook-quality.yaml` — los seis emisores que `6e1c995d3`
  pasó de `async` a síncronos. Un verde barato habría sido subirlos.
- **`96cb91736` no movió el presupuesto de `quality-duplicates`**: toca dos archivos
  (`cos_lib/duplicate_scanner.py` y su informe), no genera el baseline ausente, no
  desregistra el hook ni lo pasa a `async`. El aviso sigue rojo y ahora dice algo cierto.
- **`5d9c1ee1b` vació cuatro baselines en vez de moverlos**, y el manifest lo refleja.

**Lo que sí hay, y no es trampa sino consecuencia:** un hook que pasa a verde por el motivo
equivocado — ver la sección siguiente, `adversarial-review-gate`.

## Cambios de comportamiento en runtime no declarados

**S1 — `adversarial-review-gate` es hoy 100% ruido, y eso es peor de lo que su commit
declara.** `43a19a58a` dice "con el arreglo empieza a emitir advertencias reales" y
`230ad0387` anota la deuda como "le entrega JSON pretty en vez del texto. Funciona
degradado". Medido en producción, la primera hora de vida del hook vidente:

```
$ wc -l .cognitive-os/metrics/adversarial-review-gate.jsonl        # 10
$ grep -o '"severity":"[a-z_]*"' .cognitive-os/metrics/adversarial-review-gate.jsonl | sort | uniq -c
  10 "severity":"no_findings"
# ventana: 2026-08-19T20:48:55Z .. 2026-08-19T21:46:12Z
```

Diez de diez `no_findings`, cero `pass`. Cada una de esas filas imprime en la sesión un
bloque `WARNING [adversarial-review-gate]: Review output contains no findings with severity`.
Ninguno de los dos commits proyectó esta tasa; `230ad0387` sí midió el ruido de
`post-git-orphan-notifier` (13 escaneos, 0 huérfanos → cero avisos), así que la omisión
acá es asimétrica, no una política.

**S2 — El mismo hook tiene su rama más valiosa muerta por construcción.** La detección de
frase prohibida vive **dentro** de `if HAS_FINDING == false`
(`hooks/adversarial-review-gate.sh:60-67`). Y `HAS_FINDING` matchea `\bHIGH\b|\bMEDIUM\b|\bLOW\b|\bCRITICAL\b`,
que es literalmente la línea obligatoria de `templates/agent-preamble.md:38`:
`TRUST_REPORT: SCORE=<0-100> STATUS=<HIGH|MEDIUM|LOW|CRITICAL>`. Comprobado:

```
$ echo 'TRUST_REPORT: SCORE=92 STATUS=HIGH' | grep -oiE '\bHIGH\b'
HIGH
```

O sea: un agente que escriba "Looks good, no issues found" **y** su TRUST_REPORT
reglamentario se registra como `severity:"pass"`, en silencio. El gate cuenta la **palabra
de severidad** como prueba de que hubo hallazgo — el proxy otra vez.

**S3 — `orchestrator-skill-invocation-gate` sigue sin producir su auditoría.** `3b752adbc`
dice que ahora escribe WARN, BLOCK e `invoked`. Hoy:

```
$ ls .cognitive-os/metrics/skill-bypass.jsonl        # No such file or directory
$ ls -la .cognitive-os/runtime/skill-bypass-counter-unknown   # 3 bytes, mtime Aug 18 17:57
$ cat  .cognitive-os/runtime/skill-bypass-counter-unknown     # 131
```

El contador no se movió desde ayer: el gate no corrió ninguna de sus tres ramas desde el
arreglo. **No refuto el arreglo — digo que no está ejercitado en producción.** El defecto
declarado y no arreglado (contador de sesión con `SESSION_ID` siempre `unknown`, o sea
BLOCK permanente desde el tercer bypass histórico) sigue en pie con el mismo 131.

**S3 — Los seis emisores `async → sync` no agregaron riesgo medible.** `6e1c995d3` los pasa
a síncronos con p50 209-935ms y 0,83-0,90s en paralelo contra techo de 3s, y además
**bajó** sus `max_runtime_ms`. La lane `tests/hooks` completa da `1116 passed, 1 skipped` en
344s sobre el árbol prístino, contra los `1037 passed (1 failed ajeno)` que declaraba
`839d7edcb`: el fallo ajeno de `pre-commit-content-hash-dedupe` ya no está.

## El patrón del proxy sin denominador, en los 22 commits

El patrón está **combatido explícitamente** en la mayoría de los commits — `cos_lib/measurement.Census`
existe justamente para hacerlo irrepresentable, y `hook_exercise_audit.py`,
`hook_test_reality_census.py` y `external_claim_freshness_audit.py` declaran su ceguera en
la propia salida. Eso es real y lo verifiqué corriéndolos.

Donde **sobrevivió**:

1. **`adversarial-review-gate` cuenta la palabra de severidad como hallazgo.** Idéntico al
   caso 5 de la lista del propio `346b406c0` ("el banner en `tool_result`, que un `cat`
   también imprime"). Un `STATUS=HIGH` de plantilla dispara `has_finding:true`.
2. **`49 flujos huérfanos de 124` es un proxy contado a mano y su denominador ya se movió**
   (129 hoy). El informe declara ceguera con honestidad, pero el script que lo produciría
   (`scripts/signal_consumer_census.py`) **no existe**: es la única cifra grande de la sesión
   que no tiene evidencia ejecutable, contra la norma que la sesión entera aplicó al resto.
   Mismo caso para `12 hechos en 56 sitios`.
3. **`199 tests verdes` era un conteo derivado de un manifest que dejó de estar sincronizado**
   dos commits después. El número no era falso al escribirlo; era **perecedero y no fechado**,
   que es justo la categoría que `402355c09` inventó para las afirmaciones sobre sistemas
   ajenos y no aplicó a las propias.
4. **`07d79d93b` lo diagnostica y lo deja abierto a conciencia**: el auditor de portabilidad
   exige que el ARCHIVO de la sonda exista, no que PASE (una sonda con `assert False` da
   exit 0). O sea que el "693 de 694 con prueba de portabilidad" cuenta archivos, no pruebas.
   Está declarado en el commit, así que no lo cuento como hallazgo nuevo — pero es el
   ejemplar más caro del patrón que sigue vivo, y es la razón por la que el "1424/1424" del
   encargo suena más fuerte de lo que puede sostener.

## Las tres afirmaciones finales: ¿se sostienen?

**1. "El SO sirve" — SE SOSTIENE, con el número corregido.**
La evidencia aguanta: 1429 sondas de portabilidad existen y la lane `tests/hooks` da
1116 passed / 0 failed; la ejercitación es 96,28% sobre 188 medibles con 6% de ceguera
declarada; y los instrumentos encontraron al orquestador de verdad — `c6100b57e` documenta
que el error real fue **el opuesto** al que el encargo vigilaba, `839d7edcb` que el signo
estaba invertido, `f396e8832` que "0 invocaciones, 0 bypasses" era falso. Eso no se puede
fingir. El matiz: "1424 sondas" mide **archivos de sonda**, y el propio `07d79d93b` probó
que ese auditor no ejecuta lo que cuenta.

**2. "Hoy no está listo para que lo instale un tercero" — SE SOSTIENE, y hoy más que ayer.**
De los cinco bloqueantes, el de instalación se cerró **en un solo camino**. Los otros dos
instaladores siguen con listas fijas de 14 rules
(`scripts/cos-init-global.sh:50`, `cmd/cos/internal/wizard/install.go:270`), ambos con un
comentario que dice estar "in sync with `CORE_RULES` in `hooks/self-install.sh`" — que hoy
tiene **dos** entradas. Peor: el comentario de Go referencia `COS_INIT_CORE_RULES in
scripts/cos-init.sh`, constante que `ea0d55916` **eliminó hoy**, así que el arreglo dejó
una referencia colgada nueva. Y a eso se suma lo que encontré: `origin/main` shippea con
`hook_quality_audit.py --check` en rojo. Un tercero que clone y corra los gates arranca
con un rojo que no produjo.

**3. "El foso no era poder denegar; es la coordinación entre sesiones concurrentes" —
SE SOSTIENE COMO DIAGNÓSTICO DE MERCADO, NO COMO ACTIVO DEL REPO.**
La primera mitad la verifiqué documentalmente en `8475ff370` y la acepto. La segunda mitad
tiene un problema que ningún commit dice: **el SO tiene esa familia y está casi toda
desregistrada.** Del censo de `c8b7fa2a6`, cinco de los 36 hooks "nunca corrieron, sin
registrar" son exactamente esa familia:

```
branch-ownership-lock                 runs=0  registrado=False  tests=3
concurrent-write-guard-codex-proxy    runs=0  registrado=False  tests=2
conflict-marker-guard                 runs=0  registrado=False  tests=4
cross-session-coordination-guard      runs=0  registrado=False  tests=2
agent-bash-cwd-enforcer               runs=0  registrado=False  tests=4
```

```
$ for h in cross-session-coordination-guard concurrent-write-guard-codex-proxy branch-ownership-lock; do
    echo "$h: $(grep -c "$h" .claude/settings.json)"; done
cross-session-coordination-guard: 0
concurrent-write-guard-codex-proxy: 0
branch-ownership-lock: 0
```

Lo único registrado del rubro es `cross-session-peer-context` (contexto advisory, no
guarda). Decir "el foso es la coordinación" mientras las guardas de coordinación tienen
cero corridas y quince tests verdes es la misma forma de error que la sesión persiguió
todo el día: **contar el archivo como si fuera la capacidad**. El foso está identificado;
no está construido — y la sesión de hoy, con seis agentes pisándose sobre un mismo
checkout y una `load average` de 300, fue la mejor demostración disponible de que hace falta.

---

## Lo que quedó sin cerrar en este juicio

- **`pytest tests/red_team/portability` terminó ROJO y no pude cerrar la causa.**
  `8 failed, 1414 passed, 7 errors in 459.52s`. Entre los fallos están
  `test_os_only_scope_family.py::test_os_only_scope_none_budget_is_zero_after_family_proof`
  y `test_project_scope_family.py::test_project_scope_none_budget_is_zero_after_family_proof`,
  o sea **los dos tests que `2000544d1` declaró en verde** (`antes: 4 failed, 5 passed
  ahora: 9 passed`), más `test_primitive_behavior_depth_audit.py` y los 7 errores de
  `test_hook_surface_classifier.py`.
  **ADVERTENCIA sobre este número, y es la razón por la que no lo pongo en la tabla como
  FALSO:** lo corrí sobre la copia extraída con `git archive`, que **no tiene `.git`**.
  Al menos `test_cos_work_inventory.py` y `test_cos_branch_worktree_closure.py` fallan casi
  con seguridad por eso. Los cuatro de scope-family y depth-audit **no** dependen obviamente
  de git, y además hay un agente concurrente editando ahora mismo
  `tests/red_team/portability/test_os_only_scope_family.py` (visible en `git status`), lo que
  sugiere que alguien más está viendo el mismo rojo. **Confirmación pendiente, en una llamada:**
  `git worktree add /tmp/wt-verify origin/main && cd /tmp/wt-verify && .venv/bin/python3 -m pytest tests/red_team/portability -q`.
  Si eso da verde, el rojo era mío; si da rojo, es de `main`.
- `pytest tests/contracts` completo **no concluyó**: se colgó en
  `test_hook_quality_system.py::test_hook_quality_audit_check_passes`, en el `subprocess.run`
  que invoca `hook_quality_audit.py --check`, y pytest lo mató por timeout. Coherente con
  `load averages: 200.61 281.49 321.25` y 28 procesos pytest de otras sesiones — pero también
  significa que **ese test no pudo desmentir el `--check` en rojo**; lo desmiente el comando
  directo, que sí corrió: exit 1.
- El timing `162s → 27,5s` de `quality-duplicates` no se midió por lo mismo. Un número de
  performance tomado con la máquina así habría sido peor que no tenerlo.
- Los 12 `UNCLASSIFIABLE` de `hook_exercise_audit` los verifiqué por el archivo al que
  apuntan (10 al mismo), no leyendo las 12 líneas una por una.

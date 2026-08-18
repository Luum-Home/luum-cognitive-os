# El clasificador de profundidad archivaba por el nombre del artefacto

Fecha: 2026-08-18
Alcance: `scripts/primitive_behavior_depth_audit.py`, `manifests/primitive-scope-classification.yaml`,
`tests/unit/test_primitive_behavior_depth_audit.py`.

## Qué pasaba

`_test_depth()` decidía la profundidad de una prueba matcheando `STRUCTURAL_RE` primero
contra el basename del test y después contra la ruta completa. Las pruebas apareadas se
llaman `test_<stem-del-artefacto>.py` por convención, así que cualquier palabra que esté
en el nombre del artefacto termina en el nombre del test — y el clasificador la leía como
si describiera al test.

Resultado: `tests/red_team/portability/test_check_codebase_memory_readiness.py`, que es una
sonda de invariancia de cwd (corre el artefacto desde otro directorio y compara exit code y
stdout), quedaba archivada como `structural` por el token `readiness`, que viene del stem de
`scripts/check_codebase_memory_readiness.py` y no de nada que el test haga.

## Los cuatro casos, recontados

Los cuatro que traía el encargo se confirman. Comparación directa del clasificador viejo
(reconstruido con `git show HEAD:...`) contra el nuevo:

| test | artefacto | antes | ahora |
|---|---|---|---|
| `tests/red_team/portability/test_check_codebase_memory_readiness.py` | `scripts/check_codebase_memory_readiness.py` | structural | projection |
| `tests/red_team/portability/test_pentesting-readiness.py` | `rules/pentesting-readiness.md` | structural | projection |
| `tests/red_team/portability/test_cos-architecture-readiness.py` | `scripts/cos-architecture-readiness` | structural | projection |
| `tests/red_team/portability/test_cos-service-readiness-gate.py` | `scripts/cos-service-readiness-gate` | structural | projection |

El 472 → 473 también se confirma: estaba escrito en `manifests/primitive-scope-classification.yaml`
con el motivo completo, y el conteo real de `structural` contra el código de ayer era 473 exacto
— sin colchón, como decía el comentario.

Lo que el encargo no tenía: **no eran cuatro casos, eran 47 filas**, y la mayoría se movía en la
dirección contraria a la denunciada.

## El criterio

Escrito en el docstring de `_test_depth()`, no sólo acá:

> La profundidad es lo que el test **ejercita**, nunca cómo se llama el artefacto que prueba.

Operativamente, en tres pasos:

1. Si el stem del artefacto está **probadamente** dentro del stem del test, se lo resta. Lo que
   queda es el sujeto propio del test.
2. Si no queda nada con señal, decide el **carril** (el directorio). `tests/red_team/portability/`
   es el carril de portabilidad; ningún nombre de artefacto puede contaminar un directorio.
3. Si el stem del artefacto **no** aparece en el nombre del test, no hay fuga que probar y queda
   el match histórico intacto.

El paso 3 es el que evita convertir el arreglo en otro problema. Cuando no hay contaminación
demostrable, adivinar por el nombre en cualquier dirección movería filas que nadie midió — que
es exactamente el defecto original, mudado de lugar.

Además: `skills/<nombre>/SKILL.md` se identifica por `<nombre>`, no por el stem `SKILL`, que es
literalmente el mismo en los 194 skills y no identifica nada.

Lo que el criterio **no** hace: leer el cuerpo del test. Ver "Deuda nueva" abajo.

## La tabla de movimiento

Reproducible. Se reconstruye el clasificador viejo contra el corpus **actual**, de modo que la
única variable entre las dos mediciones sea el clasificador:

```sh
# 1. clasificador viejo, corpus actual
B=/tmp/depth-before
mkdir -p "$B/scripts"
git show d28e73d50:scripts/primitive_behavior_depth_audit.py > "$B/scripts/primitive_behavior_depth_audit.py"
ln -s "$PWD/scripts/primitive_scope_health.py" "$B/scripts/primitive_scope_health.py"
ln -s "$PWD/cos_lib" "$B/cos_lib"
.venv/bin/python "$B/scripts/primitive_behavior_depth_audit.py" \
    --project-dir "$PWD" --json-out "$B/depth-before.json"

# 2. clasificador nuevo + tabla
.venv/bin/python scripts/primitive_behavior_depth_audit.py \
    --json-out /tmp/depth-after.json --compare-to "$B/depth-before.json"
```

`git worktree add` sería lo natural acá pero está bloqueado por `destructive-git-blocker`
(ADR-055b); `git show` cumple la misma función y no muta nada.

`d28e73d50` es el commit
inmediatamente anterior al arreglo. `aa570d644`, que aterrizó de otra sesión mientras esto se
medía, no toca ni el script ni el manifiesto (`git diff d28e73d50 aa570d644 -- \
scripts/primitive_behavior_depth_audit.py manifests/primitive-scope-classification.yaml` sale
vacío), y la tabla se reverificó contra el corpus con ese commit aplicado: idéntica.

### Totales

```
rows: 1440 before / 1440 after  (+0 new, -0 gone)

depth         before   after   delta
structural       473     457     -16
projection       763     804     +41
smoke              3       2      -1
functional       139     145      +6
adversarial       62      32     -30

moved: 47 rows
     5  adversarial -> functional
    25  adversarial -> projection
     1  smoke -> functional
    16  structural -> projection
```

### Las 47 filas

**16 filas `structural -> projection`** (la fuga denunciada: `readiness`, `ledger`, `registry`,
`wiring`, `manifest`, `frontmatter` filtrados desde el stem del artefacto). Su única prueba es una
sonda de invariancia de cwd, que es projection por lo que hace:

| fila | fuente de la profundidad |
|---|---|
| `hooks/skill-frontmatter-validator.sh` | `test_skill-frontmatter-validator.py` |
| `rules/pentesting-readiness.md` | `test_pentesting-readiness.py` |
| `scripts/adr_implementation_ledger.py` | `test_adr_implementation_ledger.py` |
| `scripts/agent_work_ledger.py` | `test_agent_work_ledger.py` |
| `scripts/approval_ledger.py` | `test_approval_ledger.py` |
| `scripts/check_codebase_memory_readiness.py` | `test_check_codebase_memory_readiness.py` |
| `scripts/check_lib_wiring.py` | `test_check_lib_wiring.py` |
| `scripts/cos-architecture-readiness` | `test_cos-architecture-readiness.py` |
| `scripts/cos-manifest-tier-claim-audit` | `test_cos-manifest-tier-claim-audit.py` |
| `scripts/cos-registry-lock` | `test_cos-registry-lock.py` |
| `scripts/cos-service-readiness-gate` | `test_cos-service-readiness-gate.py` |
| `scripts/cos-skill-registry-refresh` | `test_cos-skill-registry-refresh.py` |
| `scripts/cos_architecture_readiness.py` | `test_cos_architecture_readiness.py` |
| `scripts/cos_false_positive_ledger.py` | `test_cos_false_positive_ledger.py` |
| `scripts/cos_manifest_tier_claim_audit.py` | `test_cos_manifest_tier_claim_audit.py` |
| `scripts/primitive_fitness_ledger.py` | `test_primitive_fitness_ledger.py` |

**25 filas `adversarial -> projection`** — la misma fuga, en la dirección contraria y peor: los
tokens `secret`, `guard`, `security`, `block`, `leak`, `destructive` viajan desde el stem del
artefacto y hacían que una sonda de portabilidad se declarara prueba adversarial (profundidad 5).
`test_secret-detector.py` no ataca al detector de secretos: lo corre desde otro cwd.

`hooks/_lib/hook-python-guard.sh`, `hooks/concurrent-write-guard-codex-proxy.sh`,
`hooks/concurrent-write-guard.sh`, `hooks/conflict-marker-guard.sh`,
`hooks/destructive-git-blocker.sh`, `hooks/document-ingest-guard.sh`,
`hooks/guardrails-validator.sh`, `hooks/protected-config-write-guard.sh`,
`hooks/research-compliance-guard.sh`, `hooks/secret-audit-pre-commit.sh`,
`hooks/secret-detector.sh`, `hooks/symlink-mutation-guard.sh`, `rules/agent-security.md`,
`rules/hook-security-profiles.md`, `rules/non-blocking-retry.md`, `rules/security-scanning.md`,
`scripts/context_injection_report.py`, `scripts/cos-conflict-marker-guard`,
`scripts/install-gitleaks-trufflehog.sh`, `scripts/secret-audit-gitleaks.sh`,
`scripts/secret-audit-trufflehog.sh`, `scripts/security-red-team`,
`scripts/security_audit_writer.py`, `scripts/stash-leak-alarm.sh`,
`skills/security-red-team/SKILL.md`.

**5 filas `adversarial -> functional`** — mismo origen; la prueba que perdía la etiqueta
adversarial era la que ganaba el máximo, y el máximo pasa a una prueba functional real:
`hooks/agent-control-inbound-guard.sh`, `hooks/agent-message-inbox-guard.sh`,
`hooks/cosd-auth-guard.sh`, `hooks/cross-session-coordination-guard.sh`,
`hooks/untracked-work-preservation-guard.sh`.

**1 fila `smoke -> functional`**: `hooks/skill-router-bash-gate.sh`. El `smoke` salía del token
`bash` en el nombre del artefacto; su prueba real vive en `tests/behavior/`.

## Baselines reconciliados

Uno solo, y **hacia abajo**: `behavior_depth_policy.max_by_depth.structural`, de **473 a 457**,
en `manifests/primitive-scope-classification.yaml`. 457 es el conteo real con el clasificador
corregido, sin colchón: `--strict` da 0 hallazgos y una fila más de structural lo pondría rojo.

Esto absorbe el +1 provisorio de ayer, que estaba puesto explícitamente hasta que se arreglara
el clasificador.

Ningún otro baseline se tocó. `projection`, `adversarial`, `smoke` y `functional` no tienen tope
en `max_by_depth` (sólo existen `none: 0` y `structural`), así que sus movimientos —incluido el
`+41` de projection— no requieren mover ningún número. `minimum_by_scope` exige `structural` como
piso para los tres scopes y las 47 filas se movieron a profundidades iguales o mayores que
`structural`, así que no aparece ningún `behavior-depth-below-minimum`.

## Deuda nueva: parada y reportada, no arreglada

Al medir apareció una segunda fuga que **no** es la del encargo y que **no** arreglé, porque
arreglarla exige subir un baseline.

`tests/red_team/portability/test_os_only_missing_proof_smoke.py` es la única prueba de 40 filas.
Se llama "smoke" y su docstring dice "Smoke portability proof", pero **no ejecuta nada**: abre cada
artefacto, mira las primeras 20 líneas buscando el marcador de scope, y chequea que no haya una
ruta de checkout hardcodeada. Eso es una prueba de marcadores, o sea `structural`.

- Hoy figura como `projection` (gana el carril `portability` de su ruta).
- Un clasificador por nombre no puede llegar a la verdad acá: el nombre dice `smoke`, y creerle
  subiría esas 40 filas de profundidad 2 a 3 sin ninguna evidencia nueva. Mi primer prototipo hacía
  exactamente eso; el test `test_no_detectable_leak_leaves_the_historical_match_untouched` existe
  para que no vuelva a pasar.
- Clasificarlas bien las llevaría a `structural`, y ahí **structural pasa de 457 a 497** — por
  encima incluso del 473 de ayer. Eso ya no es reconciliar una medición: es deuda que aparece al
  mirar mejor, y subir el baseline para acomodarla sería justo lo que el encargo prohíbe.

Queda medido y sin tocar. Cerrarlo requiere clasificar por **contenido** del test (¿hay un
`subprocess.run` del artefacto? ¿hay aserciones sobre su salida?) en vez de por nombre, que es un
cambio de otra naturaleza y con su propia tabla de movimiento. El caso está anotado en el docstring
de `_test_depth()` bajo "Deliberately NOT done here".

Mismo patrón, más chico: `tests/red_team/portability/test_skill_ops_runbook.py` y
`test_skill_run_tests.py` contienen `run` sólo por sus nombres (`ops-runbook`, `run-tests`) y son
portabilidad pura. Con la identificación correcta de `skills/<nombre>/SKILL.md` no se mueven —
verificado en el mismo test de regresión.

## La prueba

`tests/unit/test_primitive_behavior_depth_audit.py`, cuatro tests nuevos:

- `test_artifact_name_does_not_leak_a_structural_claim_into_a_projection_proof` — los cuatro casos
  del encargo más `primitive_fitness_ledger`.
- `test_artifact_name_does_not_leak_an_adversarial_claim_into_a_projection_proof` — la dirección
  contraria, incluida la variante `SKILL.md`.
- `test_a_test_named_for_its_own_subject_keeps_its_depth` — reverso: las pruebas de familia siguen
  `structural` y `tests/unit/test_codex_guard_layer.py` sigue `adversarial`.
- `test_no_detectable_leak_leaves_the_historical_match_untouched` — reverso: sin fuga demostrable,
  la clasificación no se mueve.

Corrida: `.venv/bin/python -m pytest tests/unit/test_primitive_behavior_depth_audit.py
tests/red_team/portability/test_primitive_behavior_depth_audit.py
tests/unit/test_primitive_behavior_audit.py -q` → 15 passed.

**Cómo fallan contra el código viejo**, con una salvedad honesta: los cuatro tiran `TypeError`,
porque el `_test_depth()` viejo toma un solo argumento. Eso prueba que la firma cambió, no que la
clasificación cambió. La prueba del comportamiento es la comparación directa de las dos funciones
sobre los mismos inputs, que es la tabla de la sección "Los cuatro casos" más estas dos filas de
control: `test_os_only_scope_family.py` da `structural` en las dos versiones, y
`test_codex_guard_layer.py` da `adversarial` en las dos.

## Correcciones a las premisas del encargo

1. **"`_test_depth()` chequea `STRUCTURAL_RE` contra la ruta completa"** — cierto pero incompleto:
   chequea contra el basename **y** contra la ruta completa
   (`STRUCTURAL_RE.search(name) or STRUCTURAL_RE.search(lowered)`). La diferencia importa porque el
   encargo ofrecía dos arreglos alternativos —"arreglá el orden" o "arreglá el alcance del
   match"— y **ninguno de los dos alcanza solo**. Restringir el alcance al basename no arregla
   nada: `readiness` está en el basename del test también, justamente porque el test se llama como
   el artefacto. Y reordenar es peor, ver punto 3.

2. **"El mismo falso positivo ya golpea al menos a tres más"** — golpea a 15 más en esa dirección,
   y a **30 en la dirección contraria**, que el encargo no mencionaba. El defecto sobre-declaraba
   profundidad más de lo que la sub-declaraba: `-30` en adversarial contra `-16` en structural. El
   número que se movió ayer era el síntoma más chico de los dos.

3. **"cambiar el orden de los regex hasta que los cuatro casos conocidos caigan bien"** como el
   peor verde barato — es peor todavía de lo que el encargo suponía, y ahora está medido: poner
   `PROJECTION_RE` antes que `STRUCTURAL_RE` movería **las 473 filas**, no unas cuantas, porque las
   457 que vienen de `test_os_only_scope_family.py` y `test_project_scope_family.py` también viven
   bajo `tests/red_team/portability/` y `PROJECTION_RE` matchea `portability` en el directorio. El
   `structural` se iría a ~16 y `projection` a ~1244 de un saque.

4. **"`git worktree add /tmp/wt-verify HEAD` para reproducir"** (norma `gates-sin-trampa`) — está
   bloqueado por `destructive-git-blocker` (ADR-055b) en este repo. La receta del informe usa
   `git show`, que no muta nada y da el mismo resultado.

5. **El prefijo `COS_ALLOW_PROTECTED_CONFIG_WRITE=1` funciona como dice el encargo**, y hace falta
   más seguido de lo esperado: `protected-config-write-guard` disparó sobre un comando
   **read-only** que sólo **mencionaba** rutas protegidas dentro de un heredoc de Python que las
   imprime. El fix `cc17a1f` ("stop reading a mention of a protected path as a write to it") no
   cubre este caso. No lo toqué —hay otros agentes activos sobre hooks— pero queda anotado.

6. **`tests/red_team/portability/` no se tocó.** Sólo lectura, confirmado en `git status`: los
   cambios son `scripts/primitive_behavior_depth_audit.py`, `tests/unit/`, `manifests/` y este
   informe.

7. **"`pytest-timeout` aborta la sesión entera"** — no lo observé. Los tres lotes corridos
   terminaron con resumen (`15 passed`, `7 passed`, `4 failed 3 passed`). No lo refuto: puede
   depender del lote; sólo digo que no se manifestó acá.

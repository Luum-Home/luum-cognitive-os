<!-- SCOPE: os-only -->
# El `pass` derivado: implementación, y los tres números que el diseño no tenía

Fecha: 2026-08-19. Autor: sub-agente implementador (problema D).
Implementa `docs/06-Daily/reports/arquitectura-pass-vs-nunca-corrio-2026-08-19.md`.
Todo número de acá se remide con el comando citado al pie de su sección.

## Resumen ejecutivo

1. **Las cuatro causas del cero quedan distinguibles** sobre la fila que el envoltorio
   ya escribe, con un campo derivado `decision`. +0 filas, 0 hooks editados.
   Lo prueba `tests/contracts/test_hook_timing_wrapper_decision.py` (11 tests):
   **11 fallan** contra el envoltorio de HEAD, **11 pasan** con el cambio.
2. Costo medido, no estimado: **+17 µs** por invocación silenciosa (97,0 % de las
   filas) y **+164 µs** cuando hay stdout. Un `jq` por invocación costaba **7.222 µs**
   — 44× más, ~1,1 s por evento sobre 154 hooks. Se descartó con el número en la mano.
3. **El join está implementado con su condición de corpus, y cierra 0 de 35, no 24.**
   El "24 de 35" del informe era cota superior de keyword; el número real por AST es
   **21**. Bajo la condición que el propio informe exigió —payload del corpus— es **0**,
   porque el corpus son 52 registros `toolUseResult` de PostToolUse y 18 de las 35 son
   guardas PreToolUse. No bajé el ratchet: sigue en 35.
4. **El irreducible no es 0.** De las **14** (no 11) sin test de disparo, **8 no tienen
   ningún `exit 2`**: deciden imprimiendo JSON. Para ésas un test que asierte
   `returncode == 2` no es difícil, es imposible. Las otras 6 tienen ruta alcanzable
   detrás de un flag.
5. Extra pedido por el coordinador: `scripts/hook_artifact_derivation.py` deriva del
   código qué artefacto escribe cada hook y lo cruza contra el disco. Población 154,
   medibles 96, **58 no clasificables declarados**, **7 candidatos** a "corrió y nunca
   escribió lo suyo".

## Correcciones a las premisas del encargo

| # | Premisa | Lo medido | Comando |
|---|---|---|---|
| 1 | "24 de 35 tienen test de disparo" (declarada incierta, cota superior) | **21**, por AST sobre 2.295 archivos de test. La heurística de keyword sobrecontaba en 3. | `python3 scripts/hook_vitality_audit.py --json` |
| 2 | El join "cierra 24 de 35" | Cierra **0**. La condición que el informe puso —payload del corpus— hoy no la cumple **ningún** test del repo: 4 archivos leen el corpus y **ninguno** asierta `returncode == 2`. El join está bien; lo que falla es la premisa de que la evidencia ya existía. | idem, bucket `capacidad_probada_con_payload_del_corpus: 0` |
| 3 | La condición de corpus es satisfacible para las 35 | **Estructuralmente no.** El corpus tiene 52 registros, **todos PostToolUse**, y cada uno sólo trae `{_corpus, toolUseResult}` — sin `tool_input`, sin `tool_name`. 18 de las 35 unproven son PreToolUse y leen `tool_input`. Ningún registro del corpus puede hacerlas disparar. Extender el corpus es lo que destraba esto; aflojar el join, no. | `python3 -c "…Counter(json.loads(l)['_corpus']['event'] …)"` |
| 4 | "El número irreducible es 0" | **Falso.** 8 de las 35 no contienen `exit 2` en ninguna línea. Su bloqueo es JSON por stdout. La vía de la Regla 3 no las alcanza; la vía del campo `decision` sí. | `grep -c 'exit 2' hooks/<h>.sh` sobre las 14 |
| 5 | "Las 11 sin test" | Son **14**. El informe cruzó dos poblaciones distintas que casualmente medían 11: las `capability_observable: false` (11) y las sin test de disparo (14). Las 11 nombradas están todas dentro de las 14; faltaban `goal-stop-gate`, `quality-duplicates` y `subagent-context-injector`. | `python3 scripts/hook_vitality_audit.py --json` |
| 6 | "+18 bytes por fila" | 18 bytes exactos para `"decision":"none",` (el 97,0 % de los casos) y 24 para `"decision":"unmeasured",`. La cifra del informe es correcta para el caso dominante; el techo es 24. | aritmética sobre el literal emitido |
| 7 | "no midió la latencia; un `jq` por invocación podría no ser gratis" | Confirmado y cuantificado: `jq` = **7.222 µs** por llamada. Sobre 154 hooks eso es **1,1 s por evento**. La implementación no usa `jq`: usa `read` + expansión de parámetros, cero forks. | §El campo derivado y su costo medido |
| 8 | (coordinador) `protected-config-write-guard` "declara escribir `protected-config-write-blocks.jsonl` y ese archivo no existe" | La ruta **no aparece en ninguna redirección de su código**: aparece en prosa. O sea el desajuste no es código-vs-disco sino **cabecera-vs-código**, una clase distinta y anterior. La derivación por código no puede detectarlo por construcción, y eso queda declarado como límite del instrumento. | `python3 scripts/hook_artifact_derivation.py --json` |
| 9 | (encargo) Validar el envoltorio con `/bin/bash -n` | Hecho: `/bin/bash -n scripts/hook-timing-wrapper.sh` → OK bajo `3.2.57(1)-release`. El benchmark también corrió bajo 3.2.57, no bajo el 5.3 del PATH. | `/bin/bash -n scripts/hook-timing-wrapper.sh` |

## Las cuatro causas, ahora distinguibles

El campo `decision` no reemplaza nada: se suma a `exit_code`, `signal`,
`execution_status` y a la presencia misma de la fila. La separación queda así, y cada
línea tiene su caso en el test:

| Causa | Huella en la fila | Caso en el test |
|---|---|---|
| **C1 · nunca corrió** | no hay fila | `c1-never-ran` — se asierta la ausencia, legible sólo porque las otras tres están presentes en el mismo archivo |
| **C2 · corrió y murió** | `execution_status="error"`, `exit_code=7` | `c2-died.sh` |
| **C3 · corrió ciego** | `exit_code=0`, `decision="none"` | `c3-blind.sh` lee `.tool_response.error` sobre un payload PreToolUse que no lo trae — la ceguera exacta de `adversarial-review-gate` |
| **C4 · evaluó y no encontró nada** | `exit_code=0`, `decision="allow"` | `c4-clean.sh` emite `permissionDecision: allow` |

El test que lo cierra:
`tests/contracts/test_hook_timing_wrapper_decision.py::test_the_four_causes_of_a_zero_are_distinguishable`
construye las cuatro huellas y asierta que el conjunto tiene **4 elementos distintos**.
Antes del cambio C3 y C4 eran la misma tupla.

Y una quinta que el diseño anterior no podía sostener:
`test_a_stdout_block_is_no_longer_filed_as_a_clean_run` — una guarda que deniega por
stdout salía con `exit 0` y se archivaba como corrida limpia. Ahora sale `decision="deny"`
con `exit_code=0`. Ésas son las 11 `capability_observable: false`.

**Lo que el campo se niega a hacer**, y por qué hay tests para eso:
`unparsed` cuando hay clave de decisión con valor fuera del vocabulario o el stdout es
demasiado grande; `unmeasured` cuando el envoltorio no miró (kill-switch propio,
kill-switch de bytes, sin TMPDIR escribible, hook salteado). Ninguno de los dos colapsa
en `none`. Es el contrato de `cos_lib/measurement.py` — "no pude ver" ≠ "vi cero" —
aplicado del lado del emisor.

## El campo derivado y su costo medido

Medido bajo `/bin/bash` 3.2.57 arm64, 3.000 iteraciones, restando el overhead del loop
(20 µs):

```
derive_nonempty: per_call_us=184   (neto ~164)   DECISION=deny
derive_empty:    per_call_us=37    (neto ~17)    DECISION=none
loop_overhead:   per_call_us=20
jq_fork:         per_call_us=7222                <- 44x, descartado
```

Y la distribución que decide cuál de los dos números manda, sobre las 264.732 filas
vivas + rotadas al momento de medir:

```
stdout_bytes == 0   256.835 filas   97,0 %   -> pagan 17 us
stdout_bytes  > 0     7.897 filas    3,0 %   -> pagan 164 us
stdout_bytes > 64k        0 filas             -> el tope nunca se ejerció en 32 dias
```

Costo esperado por evento con 154 hooks registrados: `154 × (0,97×17 + 0,03×164) ≈ 3,3 ms`.
Con `jq` habría sido ≈ 1,1 s por evento — el orden de magnitud del hook que costaba
3 minutos por turno.

La implementación es **sólo builtins**: un `read -r -d ''` redirigido desde el archivo que
el envoltorio ya bufferea, y expansiones de parámetro `${var#*…}` / `${var%%…}`. Cero
forks, cero dependencias, bash 3.2 puro.

Bytes: `"decision":"none",` = 18 B. Sobre 269.294 filas / 32 días ⇒ **+4,85 MB**, ≈ +5,9 %
sobre `hook-timing`. **+0 filas.** Es el diseño B de la tabla del informe, con su número
recalculado sobre la población de hoy.

Reproducir el benchmark: el script está pegado al pie de este informe.

## El join, y el número real de guardas con test de disparo

`cos_lib/hook_firing_evidence.py` parsea con `ast` los 2.295 archivos de test, reconoce
`X.returncode == 2` (y `assertEqual(x.returncode, 2)`), atribuye el test a un hook por
literal `<hook>.sh` **acotado al registro real**, y separa la procedencia del payload.
`scripts/hook_vitality_audit.py` lo consume y gana el bucket `capacity-proven`.

```
firing tests: 141 of 2295 test files assert exit 2 (0 unparseable)
  capacidad_probada_con_payload_del_corpus:  0 de 154 medibles (0.0%)
  test_de_disparo_con_payload_inventado:    54 de 154 medibles (35.1%)
  sin_test_de_disparo:                     100 de 154 medibles (64.9%)
```

Sobre las 35 `unproven-guard`: **21 tienen test de disparo con payload inventado, 14 no
tienen ninguno, 0 tienen uno respaldado por el corpus.**

**El ratchet no se movió, y ése es el resultado, no una falla.** Contar las 21 habría
bajado `max_unproven_guards` de 35 a 14 sin que ninguna guarda ganara prueba real —
exactamente el verde barato que el informe nombró y que `rules/gates-sin-trampa` prohíbe.
El contraejemplo es del repo: `adversarial-review-gate` tuvo test verde con payload a
mano durante 186 invocaciones ciegas en producción.

Cuatro de los tests del join existen sólo para fijar lo que el join **se niega** a contar:
payload inventado, `returncode in (0, 2)`, aserción sobre stderr, y nombre de hook que no
está en el registro. Y
`test_handwritten_firing_tests_exist_and_are_visibly_not_counted` impide que la garantía
pase por vacuidad: si algún día no hubiera tests con payload inventado, ese test falla y
avisa que el join dejó de ejercerse.

**Lo que destraba el 0:** el corpus tiene 52 registros PostToolUse con forma
`{_corpus, toolUseResult}`. Un payload de hook necesita `tool_name` + `tool_input` o
`tool_response`. La pieza faltante —fuera del alcance de este encargo— es un helper que
construya el payload del harness a partir de un registro del corpus (`_corpus.tool` da el
nombre, `toolUseResult` el cuerpo), más registros PreToolUse en el corpus. Sin eso, la
Regla 3 es correcta y no tiene con qué ejercerse.

## Las 11 sin test: cuáles tienen ruta alcanzable

Son **14**, no 11 (corrección #5). Leídas una por una:

**8 sin ningún `exit 2` — test de disparo por returncode IMPOSIBLE:**

| Hook | Cómo decide |
|---|---|
| `context-diet` | `permissionDecision` (2 usos) |
| `inject-phase-context` | `permissionDecision` (2) |
| `subagent-context-injector` | `permissionDecision` (2) |
| `eas-validation-gate` | `"decision"` JSON (1) |
| `private-mode-gate` | `"decision"` JSON (1) |
| `session-summary-reminder` | `"decision"` JSON (1) |
| `session-quality-close-gate` | `"decision"` JSON (2) |
| `goal-stop-gate` | `"decision"` JSON (6) |

Para estas 8 el camino no es un test de `returncode == 2` sino el campo `decision` del
envoltorio, que ahora las hace observables. Ésa es la parte del presupuesto que la
Regla 3 nunca iba a poder cerrar, y por eso el irreducible no es 0.

**6 con ruta alcanzable, detrás de una condición:**

| Hook | Condición que abre el `exit 2` |
|---|---|
| `adr-section-validator` | `STRICT=1` |
| `hook-header-validator` | `COS_STRICT_HOOK_VALIDATION=1` |
| `rule-frontmatter-validator` | `COS_STRICT_RULE_VALIDATION=1` |
| `quality-duplicates` | `COS_QUALITY_DUPLICATES_ENFORCE=1` |
| `control-plane-audit` | hallazgos del audit de control-plane |
| `predev-completeness-check` | `VERDICT` bloqueante en el `case` |

Ninguna es código muerto: las cuatro primeras son advisory-por-default con modo estricto
documentado en su propia cabecera, y las dos últimas están dentro de condicionales
alcanzables. **Los 6 tests de disparo son escribibles.** Lo que ninguno de esos 6 tests
podrá hacer hoy es cumplir la condición de corpus (ver el join), así que escribirlos sin
extender el corpus tampoco bajaría el ratchet.

Método: `scratchpad/reach.py` marcó 6 como `SUSPECT` por una heurística de profundidad de
llaves que no cuenta `if/fi`; los 6 se verificaron **leyendo el código**, y los 6 son
falsos positivos de mi propia heurística. Queda dicho para que nadie repita el conteo
automático sin la lectura.

## Las dos corridas de cada mitad

### Mitad (a) — el campo derivado

`BEFORE` corre contra `git archive HEAD scripts` extraído en `/tmp/cos-before-join2`, es
decir el envoltorio de HEAD sin tocar:

```
########## BEFORE (HEAD wrapper, unmodified) ##########
>       assert row["decision"] == "none"
E       KeyError: 'decision'
...
11 failed in 4.70s
```

```
########## AFTER (working tree, with the change) ##########
...........                                                              [100%]
11 passed in 4.62s
```

### Mitad (b) — el join

```
########## BEFORE (HEAD tree, no join module) ##########
tests/audit/test_hook_firing_evidence_join.py:30: in <module>
    from cos_lib.hook_firing_evidence import (  # noqa: E402
E   ModuleNotFoundError: No module named 'cos_lib.hook_firing_evidence'
1 error in 0.20s
```

```
########## AFTER (join present) ##########
..........                                                               [100%]
10 passed in 15.17s
```

Y el ratchet, después del cambio: `python3 scripts/hook_vitality_audit.py --check-budget`
→ **exit 0**, `unproven-guard: 35`, sin colchón y sin rebaja.

### La derivación de artefactos

```
tests/audit/test_hook_artifact_derivation.py  →  5 passed
```

```
hook artifact derivation
  poblacion: 154 hooks registrados
    escribe_y_su_artefacto_existe:     24 de 96 medibles (25.0%), 58 fuera de alcance
    declara_escribir_y_nunca_apareco:   7 de 96 medibles ( 7.3%), 58 fuera de alcance
    no_escribe_artefacto:              65 de 96 medibles (67.7%), 58 fuera de alcance
  ceguera declarada:
    ruta_no_derivable: 58
```

Los 7 candidatos: `dequeue-notify`, `docker-drift-detector`, `kpi-trigger`,
`rule-md-routing-validator`, `session-summary-reminder`, `stash-budget-warn`,
`validation-lock-cleanup`. **Son candidatos, no veredictos**: un hook advisory que sólo
avisa no escribe nada cuando está todo bien, y para ése el archivo ausente es el estado
correcto. La salida lo dice en la propia línea que los lista.

Dos falsos positivos que la primera corrida produjo y que quedaron cerrados con test,
porque son la forma en que este instrumento miente si nadie lo mira:
`.lstrip("./")` se comía el punto de `.cognitive-os` y hacía leer **34** ausencias
inexistentes; y las redirecciones **dentro de comentarios** acreditaban al hook con
escribir el ejemplo de su propia cabecera.

## Lo que NO hice y por qué

1. **No bajé `max_unproven_guards`.** 35 → 14 estaba a un `if` de distancia y habría sido
   mover el baseline. Queda en 35 con el motivo escrito en el manifiesto.
2. **No emití `pass` por invocación.** Era el camino corto: +257.111 filas cada 32 días,
   cero información nueva, y un `pass` sincero emitido por una guarda ciega.
3. **No edité ningún hook.** Cero de los 154 registrados fue tocado.
4. **No extendí el corpus de payloads** para volver satisfacible la condición del join.
   Es el trabajo que destraba el 0, y es un cambio con su propio riesgo (privacidad de los
   valores capturados, ratchet de campos fantasma) que no entra en este encargo. Queda
   nombrado arriba con el mecanismo concreto.
5. **No escribí los 6 tests de disparo escribibles.** Sin corpus PreToolUse no bajarían el
   ratchet, así que escribirlos ahora sería producir la señal antes que su consumidor —
   el problema A que este trabajo tenía prohibido crear.
6. **No conecté la derivación de artefactos al presupuesto.** Sus 7 candidatos son
   preguntas para un humano; convertirlos en gate antes de triarlos crearía un ratchet
   sobre falsos positivos.
7. **No detecté el desajuste cabecera-vs-código** (caso `protected-config-write-guard`).
   La derivación lee sólo el código, a propósito: leer también la cabecera y compararlas es
   un instrumento distinto, y valioso — pero mezclarlos habría hecho que la prosa de una
   cabecera contara como escritura, que es el falso positivo que acabo de cerrar.

---

### Reproducir todo lo de arriba

```bash
/bin/bash -n scripts/hook-timing-wrapper.sh                       # 3.2.57, no el 5.3 del PATH
.venv/bin/python3 -m pytest tests/contracts/test_hook_timing_wrapper_decision.py -q
.venv/bin/python3 -m pytest tests/audit/test_hook_firing_evidence_join.py -q
.venv/bin/python3 -m pytest tests/audit/test_hook_artifact_derivation.py -q
.venv/bin/python3 scripts/hook_vitality_audit.py                  # join + census
.venv/bin/python3 scripts/hook_vitality_audit.py --check-budget   # exit 0, sin colchón
.venv/bin/python3 scripts/hook_artifact_derivation.py             # derivación + ceguera
```

Benchmark de latencia (bash 3.2, cero forks salvo el reloj):

```bash
cat > /tmp/bench_parse.sh <<'EOS'
#!/bin/bash
F="${TMPDIR:-/tmp}/bench-io.$$.out"
printf '%s' '{"hookSpecificOutput":{"permissionDecision":"deny","permissionDecisionReason":"..."}}' > "$F"
BYTES=$(wc -c < "$F"); N=${1:-3000}
derive() {
  local content after val; DECISION="none"
  [ "$BYTES" -eq 0 ] && return
  [ "$BYTES" -gt 65536 ] && { DECISION="unparsed"; return; }
  IFS= read -r -d '' content < "$F" || true
  case "$content" in
    *'"permissionDecision"'*) after="${content#*\"permissionDecision\"}" ;;
    *'"decision"'*) after="${content#*\"decision\"}" ;;
    *) return ;;
  esac
  after="${after#*:}"; after="${after#*\"}"; val="${after%%\"*}"
  case "$val" in allow|deny|ask|block|approve) DECISION="$val";; *) DECISION="unparsed";; esac
}
now_us() { python3 -c 'import time;print(int(time.time()*1000000))'; }
S=$(now_us); i=0; while [ $i -lt $N ]; do derive; i=$((i+1)); done; E=$(now_us)
echo "derive_nonempty per_call_us=$(( (E-S) / N ))"
BYTES=0
S=$(now_us); i=0; while [ $i -lt $N ]; do derive; i=$((i+1)); done; E=$(now_us)
echo "derive_empty    per_call_us=$(( (E-S) / N ))"
EOS
/bin/bash /tmp/bench_parse.sh 3000
```

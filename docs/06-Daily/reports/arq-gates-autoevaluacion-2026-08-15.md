# Gates de autoevaluación: qué se convierte a hecho y qué se mata

Fecha: 2026-08-15
Alcance: `hooks/auto-verify.sh`, `hooks/dod-gate.sh`, `hooks/trust-score-validator.sh`,
`hooks/confidence-gate.sh`, `hooks/claim-validator.sh` y dos parientes de la misma
familia encontrados en el barrido (`hooks/completion-gate.sh`, `hooks/agent-output-verifier.sh`).
Modo: read-only. Toda medición de abajo tiene comando al lado.

---

## 1. Veredicto

De **7 controles de la familia**: **2 convertibles**, **1 parcialmente convertible**,
**4 a matar**. Y el más barato de los convertibles ya está construido y funcionando —
lo apaga una expresión `jq` de nueve caracteres.

---

## 2. Lo primero: el hecho verificable ya existe y está descartado en la línea 77

`scripts/claim_enforcer.py` **no le pregunta nada al modelo**. Toma el campo
`verification: <comando>` del Trust Report, lo **vuelve a correr en un proceso fresco**
y mira el exit code. Eso es un hecho, no una opinión. Y ya está implementado, testeado
y devolviendo el veredicto correcto.

El hook que lo consume lo tira a la basura:

```
hooks/claim-validator.sh:77
  ENFORCER_OK=$(printf '%s' "$ENFORCER_OUT" | jq -r '.ok // true' 2>/dev/null || printf 'true')
hooks/claim-validator.sh:80
  if [ "$ENFORCER_OK" = "false" ]; then ... exit 2
```

El operador `//` de jq cae al lado derecho cuando el izquierdo es `null` **o `false``.
Con `ok: false` devuelve `true`. La rama de bloqueo es código muerto desde siempre.

Evidencia, dos comandos:

```bash
echo '{"ok":false,"status":"block"}' | jq -r '.ok // true'
# -> true

printf 'Done. 412 tests passed. All green.' > /tmp/p.txt
python3 scripts/claim_enforcer.py --project-dir . --response-file /tmp/p.txt --json | jq -c '{ok,status}'
# -> {"ok":false,"status":"block"}
```

Y el mismo input pasado por el hook, con el payload real de PostToolUse:

```
### claim-validator -> exit=0
CLAIM: Agent says '412 tests pass' — ADR-244 expects verification: <command> in the Trust Report.
```

El motor dice `block`, el hook sale `0` y lo único que queda es una línea de aviso en
stderr que nadie lee. **El control existe, mide un hecho, y está desconectado por un
bug de una línea.** Ese es el hallazgo de mayor valor del informe.

Con un `verification:` que falla, mismo resultado: el enforcer devuelve
`{"ok":false,"status":"block","downgraded_status":"partial"}` y el hook sale `0`.

---

## 3. Tabla

| Gate | Qué le pregunta hoy al modelo | Hecho verificable equivalente | Destino | Esfuerzo |
|---|---|---|---|---|
| `claim-validator` — camino ADR-244 | "¿Qué comando respalda tu claim?" (`claim_enforcer.py`, campo `verification:`) | **Ya es un hecho**: se re-corre el comando en proceso fresco y se mira el exit code (`_run_verification`) | **CONVERTIBLE** | 2 archivos (`hooks/claim-validator.sh:77`, `scripts/claim_enforcer.py` TRIGGERS) + 2 tests. Sin telemetría nueva. **1h el fix, 4–6h el rollout seguro** |
| `claim-validator` — camino de archivos | "¿Qué archivos creaste?" (`:151`, regex sobre la prosa) | **Ya es un hecho**: `[ -f "$PROJECT_DIR/$file" ]` (`:161`). Detectó el path inventado en la prueba | **CONVERTIBLE** (falta desacoplar de fase, `:197`) | 1 archivo + `tests/behavior/test_claim_validator.py` (asserts `returncode == 0` en reconstruction, líneas 77/112-115). **2–4h** |
| `auto-verify` / `completion-gate` Fase 1 | Dos preguntas mezcladas: (a) "¿tu prompt traía ACCEPTANCE CRITERIA?" (`:62-66`, `:78`) — 53 de 55 corridas responden que no; (b) "¿pasa este comando?" (`:164-220`) | (b) sí es hecho: correr el comando. (a) no lo es — es una pregunta sobre el prompt, no sobre el trabajo | **PARCIALMENTE CONVERTIBLE** | 2 archivos + un helper de `timeout` portable en `hooks/_lib/`. 6 call sites en `completion-gate.sh`. **3–5h** |
| `dod-gate` / `completion-gate` Fase 2 | "¿Tu propio texto contiene las palabras que yo espero?" — `grep -qiE "$2"` sobre la respuesta del agente (`:110`). `adversarial_review` = ¿dice "BLOCKER"?; `audit_trail_present` = ¿dice "audit trail"?; y la complejidad se infiere de la misma prosa (`:70-79`) | Ninguno para 9 de los 11 criterios. Dos ya tienen artefacto (`_test_artifact_passed`, `_coverage_artifact_passed`, `:97-105`) | **NO CONVERTIBLE — MATAR** (conservar los 2 con artefacto) | Borrar `hooks/dod-gate.sh` + podar Fase 2 de `completion-gate.sh`. Rompe 5 tests. **4–6h** |
| `trust-score-validator` | "¿Cuál es tu score de confianza 0-100, cuántas evidencias y cuántas incertidumbres tenés?" (`cos_lib/trust_report_parser`) | **No existe.** Un número que el interesado se asigna a sí mismo no tiene hecho equivalente | **NO CONVERTIBLE — MATAR** | Desregistrar + borrar. Rompe `tests/hooks/test_trust_score_validator.py`. **2–3h** |
| `confidence-gate` | Lo mismo, con umbral: "si tu score es menor a 50, ¿te bloqueo?" (`:59-71`) | **No existe** | **NO CONVERTIBLE — MATAR** | Desregistrar + borrar + 2 tests de portabilidad. **2–3h** |
| `agent-output-verifier` | "¿Qué archivos creaste?" — duplicado del camino de archivos de `claim-validator`, y además lee el campo equivocado (`:14`, `.tool_output.result`) | Redundante con un control que ya funciona | **MATAR** (duplicado, sin registrar) | Borrar. **0.5–1h** |

Supuesto en todas las franjas: una persona con contexto del repo, incluyendo escribir
la regresión que prueba el comportamiento nuevo y correr solo la lane afectada
(`cos-test focused`), no la suite entera.

---

## 4. El orden — valor entregado sobre esfuerzo

### Primero, si solo hay tiempo para uno: `claim-validator`, camino ADR-244

**Por qué éste.** Es el único donde el hecho verificable ya está construido, ya está
testeado y ya devuelve el veredicto correcto. No hay que diseñar nada, no hay
telemetría que no exista, no hay que decidir qué medir. Hay que dejar de descartar un
resultado que el sistema ya calcula. Todos los demás ítems de esta lista son o bien
construcción nueva, o bien borrado.

**Qué se toca.**

1. `hooks/claim-validator.sh:77` — leer el booleano sin `//`:
   comparar contra `"false"` el valor crudo (`jq -r '.ok'`), o usar
   `jq -e '.ok == false'`. La forma exacta importa menos que no volver a usar `//`
   sobre un campo que puede ser `false` legítimamente.
2. `scripts/claim_enforcer.py`, lista `TRIGGERS` — hoy son tres regex que exigen
   dígitos (`\b\d+\s*(?:passed|tests? pass)`) o las frases exactas
   `green|all green|all passing`. Frases normales no disparan:

   ```bash
   printf 'Done. I ran the tests and they all pass.' > /tmp/p.txt
   python3 scripts/claim_enforcer.py --project-dir . --response-file /tmp/p.txt --json | jq -c '{triggered,status}'
   # -> {"triggered":false,"status":"noop"}
   ```

   Y no hay ninguna regex en español, con lo cual *"corrí los tests y pasan todos"*
   pasa igual. Hay que ampliar la lista y cubrir el segundo idioma.

**El verde barato que hay que cerrar en el mismo cambio.** Una vez que el gate bloquee,
el camino corto para el agente no es correr los tests: es citar
`verification: echo ok`. El comando lo elige la parte interesada. La conversión no está
completa sin un ratchet mínimo sobre el comando citado — que invoque el runner del
proyecto (`cos-test`, `pytest`, `go test`, `make`), o que se registre como
`verification: manual`, que el enforcer ya audita aparte (`status: "manual"`). Sin eso,
el gate cambia de "no bloquea nunca" a "bloquea a los honestos".

**El bloqueante real: esto pasa de 0 bloqueos a bloquear seguido.** El `exit 2` cae
sobre *toda* completion de Agent que diga "412 tests passed" sin campo `verification:`,
que hoy es prácticamente todas. No se despliega de una. Camino conservador, y de ahí
salen las 4–6 horas:

1. Fix + triggers ampliados, pero en modo log-only: escribir a
   `.cognitive-os/metrics/claim-enforcer.jsonl` cuántas veces *habría* bloqueado.
2. Correr una o dos sesiones normales y leer el conteo.
3. Recién ahí habilitar el `exit 2`, con el killswitch ya existente
   (`DISABLE_HOOK_CLAIM_VALIDATOR=true`) documentado en el runbook.

### Segundo: el camino de archivos de `claim-validator`

Un path que el agente dice haber creado y no existe **es un hecho, no una opinión**, y
no tiene por qué depender de la fase. Hoy sí depende (`:197`): en `reconstruction` es
advisory. Detecta bien — en la prueba marcó `lib/totally_invented_module_xyz.py` como
alucinación —, pero sale `0`.

El bloqueante no es técnico sino de falsos positivos: la regex de `:151` matchea prosa,
y un informe *sobre* un archivo se lee igual que un claim de haberlo creado. El repo ya
pisó esa mina (commit `3a6e737ba`, "tell a leaked path apart from a document about
leaked paths"). Por eso 2–4h y no 30 minutos: hay que exceptuar a los agentes read-only
antes de subir la severidad. Además `tests/behavior/test_claim_validator.py` afirma hoy
`returncode == 0` en reconstruction (líneas 77 y 112-115) — ese test cambia de
expectativa, no se borra.

### Tercero: el `timeout` que hace fallar todo lo que verifica

Antes de discutir si conviene convertir `auto-verify`, hay un dato que invalida
cualquier lectura de su telemetría en esta máquina: **`timeout` no está en el PATH**.

```bash
command -v timeout || echo "ausente"
# ausente
```

`auto-verify.sh:119` y los seis call sites de `completion-gate.sh` corren
`timeout "$MAX_VERIFY_TIME" bash -c "$CMD"`. Sin el binario, todo devuelve 127. Prueba
con un criterio que es cierto:

```
=== AUTO-VERIFY: 2 of 2 ACCEPTANCE CRITERIA FAILED ===
  FAIL: `test -f README.md` exits 0 (exit code non-zero)
  FAIL: `ls nonexistent-dir-xyz` exits 0 (exit code non-zero)
```

`test -f README.md` es verdadero y el gate lo reporta FAIL. **El único control de la
familia que mide un hecho no puede distinguir verdadero de falso en macOS sin
coreutils.** Se arregla con un shim en `hooks/_lib/` (`gtimeout` si existe, si no
background + kill), no con `brew install coreutils` en la máquina del operador — el
código se instala en máquinas ajenas.

La otra mitad de `auto-verify` no se convierte: preguntar "¿tu prompt traía ACCEPTANCE
CRITERIA?" es una pregunta sobre el encargo, no sobre el trabajo. Que 53 de 55 corridas
digan `NO_CRITERIA` no es un hallazgo del gate, es que nadie escribe el bloque. Eso se
resuelve del lado del orquestador — `scripts/compose_agent_prompt.py` ya existe — y el
`NO_CRITERIA` deja de loguearse como resultado de gate.

---

## 5. Los que hay que matar — texto para el ADR

### `trust-score-validator`

> El control le pide al agente un número de 0 a 100 sobre su propia confianza, más el
> conteo de sus propias evidencias e incertidumbres. No existe ningún hecho del
> repositorio, de la telemetría ni del filesystem que responda esa misma pregunta: es,
> por construcción, una opinión pedida a la parte interesada sobre su propio trabajo.
> Un modelo mejor no produce un número más exacto, produce un número mejor justificado,
> que es exactamente lo contrario de lo que el gate necesita.
>
> El parser (`cos_lib/trust_report_parser`) valida **forma**, no verdad: acepta
> `SCORE=95` de un agente que no corrió nada. Lo único que el gate puede afirmar es que
> el encabezado está bien escrito.
>
> A eso se suma que nunca corrió. `hooks/trust-score-validator.sh:32` lee
> `.tool_result // .output`; el payload de PostToolUse de Claude Code trae
> `.tool_response`. `AGENT_OUTPUT` queda vacío y el hook sale en `:34` antes de mirar
> nada. Medido: 146 disparos en la telemetría local (`hook-timing.jsonl` vigente más el
> archivo comprimido, 176.696 filas) y `trust-scores.jsonl` inexistente en el repo.
>
> El detalle que decide el veredicto no es el bug sino su test:
> `tests/hooks/test_trust_score_validator.py:10` construye el payload con
> `"tool_result"` — el campo que lee el hook, no el que emite el harness. El test está
> escrito contra la implementación en vez de contra el contrato del harness, así que da
> verde mientras el hook está muerto en producción. Arreglar el campo entregaría un gate
> que empieza a funcionar y sigue sin medir nada verificable: cambiaría 146 no-ops por
> 146 filas de opinión. Se borra.

### `confidence-gate`

> Misma pregunta que el anterior con un umbral encima: si el agente se auto-asigna menos
> de 50, se pide revisión humana. No hay hecho equivalente a "nivel de confianza"; y el
> agente que menos merece pasar es justamente el que mejor sabe qué número escribir.
>
> Está muerto por dos vías independientes, ambas medidas. Primero, el parser: `:46` solo
> reconoce el formato legacy (`Trust Report:` con espacio, `Score: N/100`). Con el
> formato canónico ADR-038 (`TRUST_REPORT: SCORE=12`) `HAS_TRUST_REPORT` queda en
> `false` y sale en `:55`. Verificado: alimentado con `Trust Report: Score: 12/100`
> imprime CONFIDENCE GATE CRITICAL; alimentado con
> `TRUST_REPORT: SCORE=12 STATUS=CRITICAL` no imprime nada y sale 0. El gate no entiende
> el formato que el resto del sistema emite.
>
> Segundo, la fase: el `exit 2` de `:148-149` está condicionado a
> `production|maintenance` (`:91-98`). `cognitive-os.yaml:9` dice
> `phase: reconstruction` desde el commit inicial `db4100405` (2026-03-27), y
> `git log -S'phase: production' -- cognitive-os.yaml` no devuelve nada: nunca fue otra
> cosa. La rama de bloqueo jamás fue alcanzable.
>
> Arreglar el parser y mover la fase no produce un control: produce un control que
> bloquea según un número que se elige a sí mismo el evaluado. Se borra.

### `dod-gate` (y la Fase 2 de `completion-gate`)

> El gate infiere la complejidad de la tarea leyendo la prosa del propio agente
> (`:70-79`) y después verifica cada criterio con `grep -qiE` sobre esa misma prosa
> (`:110`). No pregunta "¿hubo revisión adversarial?" sino "¿tu texto contiene la
> palabra BLOCKER?" (`:148`); no pregunta "¿hay audit trail?" sino "¿tu texto dice
> audit trail?" (`:160`). Un agente que escribe un párrafo más largo sube el score sin
> tocar una línea de código, y el modelo que mejor redacta es el que más fácil lo pasa.
>
> Nueve de los once criterios no tienen hecho equivalente barato. Los dos que sí lo
> tienen ya están resueltos y no necesitan este hook: `_test_artifact_passed` y
> `_coverage_artifact_passed` (`:97-105`) consumen artefactos persistidos de
> `cos-test`/coverage, y esa lógica vive también en `completion-gate.sh`. Se conservan
> esos dos consumos de artefacto; el resto de la batería de `grep` sobre prosa se borra.
>
> Medido: `hooks/dod-gate.sh` **no está registrado** en `.claude/settings.json`
> (`grep -c 'hooks/dod-gate.sh' .claude/settings.json` = 0) y tiene 0 disparos en
> telemetría. Sí figuraba en `.claude/settings.json.bak-before-regen` (23-abr): una
> regeneración de settings lo dejó afuera y nadie lo notó, que es la mejor prueba
> disponible de cuánto aportaba. `tests/contracts/EXCLUDED_HOOKS.txt:121` ya lo tenía
> anotado como "registration status unverified".

### `agent-output-verifier`

> Duplica el camino de archivos de `claim-validator` (verificar que los paths que el
> agente dice haber escrito existan), sin registrar en settings, con 0 disparos, y con
> el mismo bug de campo que `trust-score-validator`: `:14` lee `.tool_output.result`, un
> campo que el harness no emite. Dos implementaciones del mismo chequeo garantizan que
> se arregle una sola. Se borra y queda la de `claim-validator`, que es la que corre.

---

## 6. Correcciones a las premisas del encargo

1. **`auto-verify` y `dod-gate` no están registrados en esta instalación.** No es que
   fallen: no corren. `grep -c 'hooks/auto-verify.sh' .claude/settings.json` = 0, ídem
   `dod-gate`, y 0 filas en `hook-timing.jsonl`. Los números citados (53 `NO_CRITERIA` /
   55 corridas, 40 `NO_COMPLEXITY` / 15 `MISSING`) corresponden al comportamiento de
   `hooks/completion-gate.sh`, que **sí** está registrado y contiene la misma lógica en
   sus Fases 1 y 2 — escribe al mismo archivo `auto-verify.jsonl` (`:129`, `:180`). No
   cambia el veredicto, cambia qué archivo se toca: las conversiones y los borrados van
   sobre `completion-gate.sh`, y los otros dos son archivos huérfanos que además hay que
   sacar del árbol.

2. **`trust-score-validator`: no pude reproducir las 953 corridas en este checkout.** Lo
   medido acá es 17 en `hook-timing.jsonl` vigente más 129 en el archivo comprimido =
   **146**, sobre 176.696 filas totales. La afirmación central se sostiene y es más
   fuerte que el conteo: `trust-scores.jsonl` no existe, y la causa está identificada
   (campo `.tool_result` vs `.tool_response`, `:32`), cosa que el encargo no traía. Si
   las 953 salen de otra instalación o de una ventana más larga, el número correcto es
   ése; el diagnóstico no cambia.

3. **`claim-validator` sí marcó uno de los cuatro claims fabricados** — el que traía un
   path de archivo inventado. La prueba del encargo dio `noop` en los cuatro porque
   ninguno mencionaba un archivo. Es una distinción que importa para el plan: el hook
   tiene **dos** caminos independientes, uno basado en hechos que funciona (archivos) y
   otro basado en hechos que está desconectado (ADR-244). El veredicto "los cuatro
   pasaron" oculta que la mitad del control ya sirve.

4. **Sobre `.ok // true`: confirmado, y por el motivo exacto que dice el encargo.** El
   `//` de jq cae al lado derecho tanto con `null` como con `false`. Vale anotar que el
   `|| printf 'true'` del final de la misma línea es una segunda red que apunta en la
   misma dirección: si `jq` fallara, el hook también asume que está todo bien. El fix
   tiene que tocar las dos, no solo el `//`.

5. **Falta un hallazgo que el encargo no pedía y condiciona todo lo demás: `timeout` no
   existe en esta máquina.** Cualquier criterio de aceptación que `auto-verify` o
   `completion-gate` intenten verificar devuelve 127 y se reporta FAIL, sea verdadero o
   falso. Es el único mecanismo de la familia que mide un hecho y está roto de forma
   silenciosa en el sistema operativo del operador. Va antes que la conversión de
   `auto-verify`, porque sin eso no hay forma de saber si la conversión anduvo.

---

## Anexo: cómo reproducir

Los dos scripts de sondeo usados están en el scratchpad de la sesión (`probe.sh`,
`probe2.sh`). Lo que hacen es armar payloads de PostToolUse con `jq -n` y pasárselos por
stdin a cada hook, registrando exit code y stdout/stderr. No mutan el repo:
`git status --porcelain` antes y después dio idéntico en las tres corridas.

Chequeos sueltos, cada uno independiente:

```bash
# el bug de jq
echo '{"ok":false}' | jq -r '.ok // true'                     # -> true

# el enforcer sí dictamina
printf 'Done. 412 tests passed.' > /tmp/p.txt
python3 scripts/claim_enforcer.py --project-dir . --response-file /tmp/p.txt --json | jq -c '{ok,status}'

# registro real de cada hook
for h in auto-verify dod-gate trust-score-validator confidence-gate claim-validator completion-gate; do
  printf "%-24s settings=%s telemetry=%s\n" "$h" \
    "$(grep -c "hooks/$h.sh" .claude/settings.json)" \
    "$(grep -c "\"$h\"" .cognitive-os/metrics/hook-timing.jsonl)"
done

# la fase nunca cambió
git log --format='%h %ad' --date=short -S'phase: production' -- cognitive-os.yaml   # vacío

# timeout ausente
command -v timeout || echo ausente
```

Efecto colateral de la sesión, declarado: correr `trust-score-validator.sh` con el campo
`.tool_result` creó `.cognitive-os/metrics/trust-scores.jsonl` (145 bytes, ignorado por
git). Se borró al terminar para no falsificar la afirmación "no existe en ninguna
instalación", que sigue siendo cierta.

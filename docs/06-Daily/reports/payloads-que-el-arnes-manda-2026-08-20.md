# Los payloads que el arnés manda, y los que los tests se inventan

Fecha: 2026-08-20 · Alcance: contrato de entrada de los hooks (stdin), no el de salida.

## Resumen ejecutivo

El arnés manda **6 o 7 campos** por evento, no quince: forzar el payload completo
cuesta dos campos más de los que un test típico fabrica, así que no es ceremonia.
Los hooks leen **5 como máximo** por evento, y la intersección es de 3 o 4. Las dos
diferencias son el hallazgo: **13 hooks leen campos que Claude Code no manda nunca**
(`.message`, `.tool_result`, `.tool_use_id`), y **`cwd` y `transcript_path` llegan en
todos los eventos sin que ningún hook los mire** — incluido `agent-bash-cwd-enforcer`,
que deduce el directorio de `pwd` y `git worktree list` en vez de leer el `cwd` que
tiene servido.

El bloqueo del `grep` **se reproduce**, y el campo es **`session_id`**: necesario y
suficiente. Con payload fabricado de dos campos, `bash-hot-path-dispatcher` bloquea un
`grep` inocuo; agregando sólo `session_id` pasa; sacando sólo `session_id` de un payload
fiel, vuelve a bloquear. El hook que bloquea **no es** `protected-config-write-guard`.

Efecto colateral medido, y es el peor: correr esos tests **escribe en el estado del
operador**. Mi sonda subió el contador de bypasses de la sesión viva de 132 a 135.

## Correcciones a las premisas del encargo

1. **«un bloqueo real de `protected-config-write-guard` sobre un `grep`»** — el hook que
   bloquea el `grep` es `bash-hot-path-dispatcher.sh`, en su rama
   `orchestrator-skill-invocation-gate`. `protected-config-write-guard` deja pasar los
   cinco `grep` que probé, en las tres formas de payload. Eso sí: **ese guard me bloqueó a
   mí, en vivo**, un heredoc de Python read-only, porque el *texto del comando* contenía
   `hooks` y `.claude/projects/-x/y.jsonl`. O sea que el guard existe y bloquea, pero
   bloquea por texto de comando, no por campos del sobre — su analizador lee sólo
   `tool_input` y `tool_name` (líneas 915 y 923); el `transcript_path` real del arnés cae
   en un campo que el analizador nunca abre.
2. **«199 tests»** — son **321 archivos** de test los que fabrican un payload de hook a
   mano (`scripts/audit_hook_payload_fidelity.py --gate`, antes de migrar). El baseline
   quedó en 320 tras la migración.
3. **«si el arnés manda quince campos»** — manda 6 (PreToolUse, UserPromptSubmit) o 7
   (PostToolUse). La premisa que decidía el diseño estaba sobredimensionada por más del
   doble, y la conclusión se invierte: el payload fiel es barato.
4. **«el contrato en `manifests/claude-code-hooks-schema.yaml` para la forma»** — ese
   manifiesto documenta el contrato de **salida** con detalle, y el de **entrada**
   (`stdin_fields`) para **2 de los 10 eventos que el repo registra**: SubagentStart y
   TaskCreated. Para PreToolUse, PostToolUse y UserPromptSubmit —los tres que concentran
   104 de los 160 registros— el contrato de entrada no estaba escrito en ninguna parte.
   Por eso hubo que medirlo y no transcribirlo.
5. **`block-destructive-bash`** — el hook se llama `destructive-git-blocker`, y se llega a
   él por `bash-hot-path-dispatcher`. Confirmé el comportamiento que me advertiste: un
   `git commit -F <ruta absoluta>` bloquea en las tres formas de payload, o sea que ahí el
   veredicto no depende del sobre sino del texto.
6. **`session_id` vacío en 296.383 de 296.383 filas** — no lo recontré sobre la telemetría
   (es read-only del operador y no la toqué), pero la ablación explica por qué eso
   importa: **un `session_id` vacío se comporta igual que un `session_id` ausente**, y
   ambos hacen que el gate caiga al bucket por defecto, que es donde está acumulada la
   historia de bypasses del operador.
7. **«los tests de hooks son read-only»** — no lo dijiste, pero está implícito en tratarlos
   como tests. No lo son: el gate de invocación de skills contabiliza y persiste, así que
   cada corrida con payload fabricado suma al contador de la sesión viva.

## Qué campos manda el arnés vs qué campos leen los hooks

Comando: `scripts/audit_hook_payload_fidelity.py --census --live`
(4.354 payloads reconstruidos de los transcripts de esta máquina: 2.022 PostToolUse,
2.013 PreToolUse, 319 UserPromptSubmit). `--census` sin `--live` corre contra el sobre
congelado y da lo mismo campo por campo.

| Evento | MANDA | LEEN | ∩ | LEEN\MANDA (fantasma) | MANDA\LEEN (sobrante) |
|---|---|---|---|---|---|
| PreToolUse | 6 | 5 | 4 | `tool_use_id` | `cwd`, `transcript_path` |
| PostToolUse | 7 | 5 | 3 | `tool_result`, `tool_use_id` | `cwd`, `hook_event_name`, `session_id`, `transcript_path` |
| UserPromptSubmit | 6 | 2 | 1 | `message` | `cwd`, `hook_event_name`, `permission_mode`, `session_id`, `transcript_path` |

105 hooks leen algo del payload; 160 registros repartidos en 10 eventos.

**Los fantasmas.** `.message` lo leen cuatro hooks —`aguara-scan.sh`, `agnix-lint.sh`,
`guardrails-validator.sh`, `mcp-scan.sh`— y Claude Code no manda un `.message` de primer
nivel en ningún evento. `.tool_use_id` y `.tool_result` sí existen, pero en **otro arnés**:
`manifests/codex-hooks-schema.yaml` los declara como `payload_extra`, y Kiro usa
`.tool_result` según la matriz de `hooks/_lib/normalize-stdin.sh`. Es decir que parte del
"fantasma" es portabilidad deliberada y parte es deuda; separarlos hook por hook queda
fuera de este encargo, pero la lista ya está.

**El sobrante que más duele.** `cwd` no lo lee **ningún** hook del repo — el censo lo pone
en `MANDA\LEEN` en los tres eventos, y el conteo directo
(`grep -rhoE "'\.cwd'|\"\.cwd\"|\.cwd //" hooks/*.sh | wc -l`) da 0 —
y `agent-bash-cwd-enforcer.sh` —el hook cuyo trabajo
es justamente saber desde dónde se corre el comando— lo deriva de `pwd` y de
`git worktree list --porcelain`. El arnés se lo está sirviendo en cada payload.

## De dónde sale la verdad, y cómo se anonimiza

Dos fuentes, para dos preguntas distintas:

- **Forma**: `tests/fixtures/hook-payload-envelope/envelope.json`, capturado por
  `scripts/audit_hook_payload_fidelity.py --capture` desde los transcripts del arnés —
  el archivo que el arnés escribió mientras corría, no la documentación. La proyección al
  payload es la documentada: `session_id`=`sessionId`, `cwd`=`cwd`,
  `tool_name`/`tool_input`= el bloque `tool_use` del mensaje del asistente,
  `tool_response`= el `toolUseResult` correspondiente, `prompt`= el contenido del mensaje
  de usuario.
- **Contenido real**: `harness_payload.live_payloads()`, que reconstruye payloads con
  valores reales del transcript local **en tiempo de test**. No se versiona nada.

**Anonimización.** El sobre versionado lleva **nombres de clave y tipos de valor, nunca
valores**: ni una ruta, ni un usuario, ni un nombre de proyecto, ni un comando, ni un
prompt. `--capture` se niega a escribir si el blob contiene `$HOME`, la ruta del repo o
`$USER`, y los dos guardas del repo pasan sobre el directorio:

```bash
bash scripts/check-local-privacy.sh tests/fixtures/hook-payload-envelope   # privacy-guard-ok
python3 scripts/check_absolute_paths.py tests/fixtures/hook-payload-envelope  # exit 0
```

`tests/audit/test_hook_payload_fidelity.py::test_envelope_carries_no_operator_data`
vuelve a chequear el invariante en cada corrida, no sólo en la captura.

**El costo, dicho claro**: el sobre versionado da *presencia y forma de campo*, no el
comando real del operador. Elegí ese corte porque la presencia era justamente lo que
faltaba — el veredicto que se da vuelta abajo lo hace por la **presencia** de
`session_id`, con el comando idéntico.

## El bloqueo del grep: reproducido o refutado

**Reproducido**, y con un solo campo responsable. Comando fijo
`grep -rn 'needle' somedir/ | head -20`, hook `hooks/bash-hot-path-dispatcher.sh`,
`COS_ALLOW_PROTECTED_CONFIG_WRITE` sacado del entorno con `env.pop` antes de medir
(sonda: `scratchpad/ablate.py`, no versionada porque lleva rutas locales):

```
full                          -> (0, '')
full minus session_id         -> (2, 'orchestrator-skill-invocation-gate: BLOCK …')
full minus transcript_path    -> (0, '')
full minus cwd                -> (0, '')
full minus permission_mode    -> (0, '')
full minus hook_event_name    -> (0, '')
minimal (tool_name+input)     -> (2, 'orchestrator-skill-invocation-gate: BLOCK …')
minimal plus session_id       -> (0, '')
minimal plus cwd              -> (2, BLOCK)
minimal plus transcript_path  -> (2, BLOCK)
minimal plus permission_mode  -> (2, BLOCK)
minimal plus hook_event_name  -> (2, BLOCK)
minimal plus empty session_id -> (2, BLOCK)
```

`session_id` es **necesario y suficiente**; los otros cuatro campos son inertes para este
veredicto. Y un `session_id` vacío se comporta como ausente. El mecanismo: sin
`session_id` el gate cae al bucket por defecto, que arrastra la historia de bypasses de la
sesión real del operador (`skill 'repo-forensics' bypassed 132 times this session`), así
que **el veredicto de un test con payload fabricado depende del contador vivo del
operador**. Es no determinista por construcción: el mismo test da distinto según cuánto
trabajó el operador esa sesión. Y no es sólo lectura — el contador subió 132 → 133 → 134 →
135 mientras yo probaba.

La hipótesis del encargo era que el payload fiel **reproduciría** el bloqueo. Es al revés:
el payload fiel lo **apaga**. Que es la misma conclusión con el signo cambiado — los dos
lados prueban que el sobre decide.

## El test migrado, y si se puso rojo

`tests/integration/test_cwd_enforcer_warns.py`. Fabricaba
`{"tool_name": "Bash", "tool_input": {"command": …}}` — dos de seis campos. Ahora llama a
`harness_payload.raw("PreToolUse", …)`.

```
antes:  .venv/bin/python3 -m pytest tests/integration/test_cwd_enforcer_warns.py -q  → 5 passed
después: idem                                                                        → 5 passed
```

**No se puso rojo**, y el porqué es informativo, no tranquilizador: el enforcer no lee
ninguno de los cuatro campos que le faltaban al payload viejo. Toma el directorio de `pwd`
y de `git worktree list`, así que era inmune al sobre. El test seguía probando lo mismo
porque el hook nunca miró la diferencia — lo cual es exactamente el sobrante de la tabla
de arriba, visto desde el otro lado.

Elegí este porque es el que el encargo señalaba. El caso donde la migración sí daría rojo
está identificado y medido: cualquier test que ejercite `bash-hot-path-dispatcher` cambia
de veredicto con `session_id` presente. No lo migré (ver «Lo que NO hice»).

## El gate y sus tres corridas

`scripts/audit_hook_payload_fidelity.py --gate` escanea con AST todos los `test_*.py` de
`tests/` y `packages/*/tests/` buscando literales `dict` con claves que sólo existen en un
payload de hook (`tool_name`, `hook_event_name`, `tool_input`, `tool_response`,
`transcript_path`, `stop_hook_active`), y compara contra
`manifests/hook-payload-fabrication-baseline.txt` **por igualdad exacta**.

Los dos anti-colchón, como tests y no como promesa
(`tests/audit/test_hook_payload_fidelity.py`):

- `test_no_new_test_fabricates_a_hook_payload` falla con una entrada **nueva** y falla
  igual con una entrada **stale** — un archivo migrado que quede listado rompe el gate, así
  que el baseline no puede quedar por encima de la realidad.
- `test_baseline_lists_only_files_that_exist_and_still_fabricate` verifica que ninguna
  línea del baseline nombre un archivo inexistente, y que el conjunto listado sea
  **idéntico** al medido.

Las tres corridas, dentro de
`test_gate_catches_a_fabricated_payload_and_clears_a_faithful_one`:

| Corrida | Archivo | Resultado |
|---|---|---|
| A | test con `{'tool_name': 'Bash', 'tool_input': {...}}` a mano | **flaggeado** |
| B | el mismo test usando `harness_payload.raw(...)` | no flaggeado |
| C | test de payload malformado, marcado `# payload-synthetic: <motivo>` | no flaggeado, **sin tocarlo** |

C es el control anti-falso-positivo: sin él, el gate prohibiría probar el camino de error.
La escotilla es explícita y pide motivo — `# payload-synthetic: <razón>` en la línea o en
las tres de arriba —, y además `harness_payload` ofrece `malformed()`, `truncated()` y
`without(evento, campo)` para que el caso legítimo tenga una forma canónica en vez de un
dict suelto.

Verificación end-to-end de esta entrega:

```bash
.venv/bin/python3 -m pytest tests/audit/test_hook_payload_fidelity.py -q   # 8 passed
.venv/bin/python3 -m pytest tests/integration/test_cwd_enforcer_warns.py -q # 5 passed
.venv/bin/python3 scripts/audit_hook_payload_fidelity.py --gate            # exit 0
```

## Lo que NO hice y por qué

- **No migré los otros 320 archivos.** El gate congela la cuenta por igualdad exacta, así
  que no puede crecer; migrarlos es trabajo de lote y cada uno puede cambiar de veredicto
  (ese es el valor). Migrar de a montones sin mirar el veredicto sería el verde barato de
  esta familia.
- **No arreglé los hooks fantasma** (`.message` en cuatro hooks, `.tool_result` y
  `.tool_use_id`). Hace falta decidir hook por hook si es portabilidad a Codex/Kiro o
  deuda, y `hooks/**` es ruta protegida y territorio de otro agente en esta tanda.
- **No versioné contenido real.** Ni comandos, ni prompts, ni rutas: sólo claves y tipos.
  Un corpus con `tool_input.command` real sería más fiel y no lo puedo anonimizar de forma
  verificable — un comando puede llevar cualquier cosa adentro, incluido un secreto.
- **No recontré la telemetría de `session_id`** (296.383 filas): `.cognitive-os/metrics/`
  es read-only del operador.
- **No toqué** ninguno de los siete archivos atribuidos a otros agentes, ni
  `hooks/protected-config-write-guard.sh`, que sólo leí.
- **No registré el gate en CI** más allá de la lane de `tests/audit/`, que es donde el repo
  ya corre este tipo de auditoría.

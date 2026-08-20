<!-- SCOPE: os-only -->
# Gate de registro de hooks — que un hook declarado no pueda quedar huérfano en silencio

Fecha de trabajo: 2026-08-19 (la sesión cruzó a 2026-08-20 durante la corrida;
el nombre del archivo es el del encargo). HEAD al empezar: `f10f4b882`.

## Resumen ejecutivo

- Las superficies **no son seis: son diez**, y sólo **cuatro** deciden si un hook
  corre en Claude Code (`driver-claude-code`, `.claude/settings.json`,
  `bash-hot-path-dispatcher.sh`, `templates/security-profiles/*.json`).
- **Ninguna es obligatoria para todos.** La cobertura real va de 29 a 186 nombres
  sobre 192 scripts declarados. Un gate que exija presencia universal daría
  cientos de rojos y lo apagarían el primer día.
- El criterio que sí decide: **¿está declarada su ausencia?** Encontré **seis
  mecanismos de omisión declarada** (cinco en el yaml, uno en un whitelist).
- Huérfano = declarado en el yaml + ausente de las cuatro superficies de Claude +
  sin declaración de omisión + sin evidencia de haber corrido (jsonl vivo **más**
  sus 10 rotados, 298.033 filas).
- Contra el árbol real: **1 huérfano** (`hooks/publication-safety.sh`) y **4
  contradicciones** nuevas (el yaml dice "no proyectar a Claude" y los tres
  perfiles lo cablean igual).
- `WiringValidator` no medía esto: leía `.claude/settings.local.json`
  —gitignoreado, sin bloque de hooks— y daba 36 `True` por substring contra la
  lista de `permissions`. Arreglado: ahora 153/256 y elige `.claude/settings.json`.
- Entregado: `cos_lib/hook_registration_audit.py`,
  `scripts/audit_hook_registration.py` (exit 0/1/2),
  `tests/audit/test_hook_registration_audit.py` (13 tests, las cuatro corridas).

## Correcciones a las premisas del encargo

1. **"Las seis superficies" — son diez candidatas, cuatro decisorias.** Medido
   con `cos_lib/hook_registration_audit.py :: surfaces()`:

   | superficie | nombres | ¿decide si corre en Claude? | ¿versionada? |
   |---|---|---|---|
   | `scripts/_lib/settings-driver-claude-code.sh` | 186 | sí | sí (a mano) |
   | `.claude/settings.json` | 152 | sí | sí (derivada) |
   | `templates/security-profiles/*.json` (3 archivos) | 162 | sí | sí (a mano) |
   | `hooks/bash-hot-path-dispatcher.sh` | 29 | sí (por delegación) | sí |
   | `.cognitive-os/cos-runner-hooks.json` | 187 | no (runner bare) | **no, gitignoreado** |
   | `.codex/hooks.json` | 94 | no (codex) | sí (derivada del yaml) |
   | `.opencode/cos-hooks.json` | 66 | no (opencode) | sí (derivada del yaml) |
   | `.ai/primitives/hooks/*.json` | 250 | no (overlay de referencia) | sí |

2. **`scripts/apply-efficiency-profile.sh` no es una superficie de registro.** El
   encargo la contaba ("apply-efficiency 5"). Sus menciones son una **lista de
   sanity parcial y a mano** que emite `Warning:` si falta un hook representativo
   — no proyecta nada. Contarla como superficie es contar una aserción como
   implementación.

3. **El conteo del encargo era de ocurrencias de substring, no de registro.**
   `grep -c publication-safety scripts/_lib/settings-driver-claude-code.sh`
   devuelve **2**, y las dos son líneas del comentario de cabecera que documenta
   que el hook falta. Sin barrer comentarios, la documentación del bug se lee
   como el arreglo del bug. Está cubierto por
   `TestMeasurementTraps::test_driver_comment_is_not_registration`.

4. **"El driver no lee el yaml" es cierto y es más fuerte de lo que dice el
   encargo.** Con comentarios barridos queda **una sola** referencia al yaml en
   todo el driver, y es un `[ -f "cognitive-os.yaml" ]` para ubicar la raíz del
   proyecto — nunca lee el contenido:
   ```
   grep -v '^\s*#' scripts/_lib/settings-driver-claude-code.sh | grep -c "cognitive-os.yaml\|CONFIG_FILE"   -> 1
   # bare=3  codex=2  opencode=12
   ```
   Los números 6/5/15 del encargo incluían comentarios.

5. **`hook-timing.jsonl` tiene 298.033 filas, no 294.333.** El archivo vivo creció
   durante la sesión. Cualquier número de telemetría que cite el archivo vivo
   caduca en horas; por eso el módulo lee vivo + los 10 rotados.

6. **El coordinador dijo que `in_settings_json` daba `False` para todos. No: daba
   `True` para 36.** `.claude/settings.local.json` tiene `permissions` y cero
   bloques de hooks, pero los nombres de hook aparecen dentro de las cadenas de
   permisos (`Bash(bash hooks/x.sh)`), y el chequeo era substring contra el
   archivo entero. Peor que constante: **ruido que discrimina al azar**.

7. **El coordinador dijo `validate_all_hooks() -> 0 no cableados`. Medí 249.**
   `get_unwired_components()` usa `wiring_score < 1.0` y devuelve 249 de 256.
   No pude reproducir el 0 desde ninguna función pública del módulo; el único
   consumidor que llama a `validate_hook` está en `archive/` y no corre.
   El defecto real no era el rollup: eran **dos de las tres señales muertas**
   (`in_security_profile` es `False` para 249 de 256, porque
   `set-security-profile.sh` sólo menciona 50 `.sh`).

8. **HEAD no era `006a425fb`** sino `f10f4b882` al empezar. El árbol además tenía
   ~30 archivos modificados por las otras dos sesiones; commiteé sólo mis rutas.

9. **Cero hooks sin declarar en disco.** Esperaba encontrar deuda ahí: 256 `.sh`
   en `hooks/`, 192 declarados en el yaml, y los **64 restantes están todos en
   `EXCLUDED_HOOKS.txt` con motivo**. El whitelist se mantiene de verdad.

## Cuáles son las superficies, y cuáles son obligatorias

Ninguna es obligatoria para todos los hooks. Lo que el gate exige es **al menos
una de las cuatro de Claude**, o una omisión declarada.

Por qué esas cuatro y no las otras: el driver de Claude Code es el **único
eslabón mantenido a mano**. Los drivers de bare, codex y opencode leen el yaml
programáticamente, así que su cobertura baja (187/94/66 sobre 192) es **gap de
capacidad del arnés**, no deriva silenciosa — no puede haber un hook que "se
olvidaron de agregar" ahí. Por eso el gate los reporta como
`harness_coverage` (informativo) y **nunca falla por ellos**.

`.cognitive-os/cos-runner-hooks.json` queda fuera de las decisorias por una razón
distinta: está **gitignoreado**. Un gate que dependiera de él sería verde sólo en
el checkout del autor.

## Los mecanismos de omisión declarada

Seis, implementados en `HookRegistrationAudit.omissions_for()`:

| # | mecanismo | dónde | ejemplo en el árbol |
|---|---|---|---|
| 1 | `default_projection: false` | yaml | `auto-refine`, `dod-gate`, `auto-verify`, `task-completed` |
| 2 | `claude_projection: false` | yaml | `concurrent-write-guard-codex-proxy` |
| 3 | `codex_projection: false\|gap\|partial` (+ `opencode`/`bare`) | yaml | `claim-validator`, `context-diet` |
| 4 | `profiles: [...]` | yaml | `goal-stop-gate`, `eas-validation-gate` |
| 5 | `projection_note` | yaml | los tres superseded por `completion-gate.sh` |
| 6 | `<hook>.sh \| <motivo>` | `tests/contracts/EXCLUDED_HOOKS.txt` | 64 hooks de disco |

El colapso de hot-path (ADR-311) **no** es un mecanismo de omisión: es una
superficie de alcance. Un hijo del dispatcher está registrado, sólo que por
delegación — y por eso hereda la evidencia de telemetría del padre
(`test_dispatcher_children_inherit_evidence`).

## El gate y sus cuatro corridas

```
.venv/bin/python scripts/audit_hook_registration.py          # humano, exit 0/1/2
.venv/bin/python scripts/audit_hook_registration.py --json   # máquina
.venv/bin/python -m pytest tests/audit/test_hook_registration_audit.py -q
```

`13 passed in 2.47s`. Las cuatro corridas:

| # | corrida | test | resultado |
|---|---|---|---|
| 1 | hook en el yaml y **nada más** | `test_run1_yaml_only_is_orphan` | **huérfano** |
| 2 | el mismo, agregado al driver | `test_run2_added_to_driver_is_green` | **verde** |
| 3 | el mismo, con omisión declarada | `test_run3_...` ×4 params + `test_run3b_excluded_hooks_txt_is_green` | **verde, sin tocarlo** |
| 4 | árbol real | `test_run4_real_tree_orphans_match_the_ledger_exactly` | **`publication-safety`**, exit 1 |

La corrida 3 está parametrizada sobre los cuatro mecanismos del yaml más el
whitelist, porque un gate que sólo entiende `default_projection` malinterpreta
cinco de los seis casos reales del árbol.

Tres trampas de medición tienen test propio (`TestMeasurementTraps`): comentario
del driver ≠ registro, archivos rotados sí cuentan, e hijos del dispatcher
heredan evidencia.

**El ledger es de igualdad exacta, no un baseline.** `KNOWN_ORPHANS ==
{"publication-safety"}` con `==`, no `<=`: agregar un huérfano falla, y arreglar
`publication-safety` **también** falla, obligando a editar la lista con motivo.
Un `<=` sería un colchón.

## Los huérfanos que aparecieron

### Huérfano (bloqueante): 1

`hooks/publication-safety.sh` — `PreToolUse` / matcher `Bash` / `scope: both`,
sin `default_projection`, sin `claude_projection`, sin entrada en
`EXCLUDED_HOOKS.txt`. Ausente de las cuatro superficies de Claude. **0 filas** en
298.033 de telemetría. Sí está en `.cognitive-os/cos-runner-hooks.json`: el
runner bare lo lee del yaml y lo corre. O sea que el hook no está muerto —
está muerto **en Claude Code**, que es exactamente el modo de falla que el
driver a mano introduce.

### Contradicciones (reportadas, no bloqueantes): 4

El yaml declara que estos hooks **no** se proyectan a Claude, y los tres perfiles
de seguridad los cablean igual. Los cuatro tienen **0 firings**, porque el
`.claude/settings.json` activo no los tiene — pero `set-security-profile.sh
standard` los reinstalaría.

| hook | opt-out declarado | cableado en |
|---|---|---|
| `auto-refine.sh` | `default_projection` + `claude_projection` + `projection_note` | los 3 perfiles |
| `dod-gate.sh` | ídem | los 3 perfiles |
| `task-completed.sh` | `default_projection: false` | los 3 perfiles |
| `concurrent-write-guard-codex-proxy.sh` | `claude_projection: false` | los 3 perfiles |

**Por qué no bloquean, escrito y motivado** (no es un baseline): "dos
declaraciones que se contradicen" es un defecto distinto de "nadie lo declaró".
Si las metiera en el mismo exit code, arreglar `publication-safety` no podría
poner el gate en verde — y un gate que no puede ponerse en verde se apaga. Se
imprimen en **todas** las corridas, en texto y en JSON.

## Lo que NO hice y por qué

- **No registré `publication-safety.sh`.** Registrarlo o declarar la omisión es
  decisión del operador: es un `PreToolUse` sobre Bash con `scope: both`, o sea
  que activarlo cambia el hot path de todos los consumidores. El gate existe para
  que deje de ser invisible, no para decidir por nadie.
- **No arreglé las 4 contradicciones.** `templates/security-profiles/*.json` son
  snapshots a mano y hay dos sesiones más escribiendo en este checkout.
- **No reescribí `WiringValidator`.** Decisión, con su razón: su `validate_hook`
  es triage estructural por archivo sobre tres familias (hooks, libs, rules) y
  tiene 22 tests con un árbol mock; cambiarle la semántica de hooks los rompe
  todos. Arreglé **los dos defectos reales** y dejé escrito el reparto, para que
  no queden dos instrumentos midiendo lo mismo con criterios distintos:
  - `_settings_candidates()` ya no prefiere `.claude/settings.local.json`, y
    `_settings()` **descarta** un candidato que no contenga comandos de hook
    (excluye la clave `permissions`). Antes: driver `.claude/settings.local.json`,
    36 `True`. Ahora: driver `.claude/settings.json`, **153/256**.
  - El docstring decía que `cognitive-os.yaml` es el registro canónico para
    Claude Code. Ahora dice que es la **declaración**, que `in_efficiency_profile`
    da `True` para hooks que Claude nunca corre, y remite a este gate.
  - Los 22 tests siguen pasando (el mock nunca escribió `settings.local.json`).
- **No toqué** `hooks/session-cleanup.sh`, `hooks/_lib/common.sh`,
  `scripts/audit_killswitch_activation.py`, `docs/09-Quality/security/bypass-cheatsheet.md`.
- **No cubrí codex/opencode/bare como lane bloqueante.** El gate lo dice en su
  propio docstring y en la salida: `other-harness coverage (informational, never
  gates)`. Su modo de falla es otro —gap de capacidad, no deriva a mano— y
  merece su propio criterio, que no escribí.
- **No registré el gate como hook.** Es un audit read-only; su enforcement es el
  test en `tests/audit/`, que es el patrón del gate hermano
  (`tests/contracts/test_killswitch_activation_is_executable.py`).

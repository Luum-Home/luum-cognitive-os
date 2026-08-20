# El canal que se verifica solo (2026-08-20)

Encargo: que las afirmaciones verificables del canal que el SO le inyecta a todo
sub-agente dejen de mantenerse a mano. Antecedente: el juicio read-only de hoy
(`docs/06-Daily/reports/juicio-lo-que-el-so-le-dicta-a-sus-agentes-2026-08-20.md`),
57 afirmaciones verificadas, 15 falsas, 41 de las 42 correctas verificables por
script y **cero** automatizadas.

## Resumen ejecutivo

- El ledger **sí alcanza como lugar**, pero **no como mecanismo**: comparaba
  texto contra texto y no podía correr un comando. Lo extendí en vez de
  construir algo nuevo.
- Dos familias nuevas en `scripts/documentation_truth_audit.py`, declarativas
  desde el manifiesto: `path_claims` (toda ruta citada resuelve hoy) y
  `executable_assertions` (corre un comando y **su salida tiene que ser la frase
  publicada**).
- Claim nuevo `agent_channel_facts` en `manifests/documentation-truth-claims.yaml`:
  **16 rutas citadas + 9 archivos de regla + 1 ADR + 2 censos + la entrega misma
  del canal**.
- Cobertura sobre lo que el juez verificó del canal A: **17 de las 26
  afirmaciones que hoy siguen vivas en el archivo** (las otras 7 que él auditó ya
  no existen: la reescritura de esta mañana las sacó), más una parcial.
- De la familia que **se pudre** —cifras— el canal A tiene exactamente **2 y las
  dos quedaron atadas a su comando**. Las 9 cifras del juicio no viven todas en
  el canal A: 7 viven en B/B′, que no toqué (ver la última sección).
- El canal no creció: **0 caracteres agregados**. Toda la verificación vive
  afuera.
- Corridas: reintroducción detectada (4 variantes), árbol actual verde,
  control anti-vacío bloquea las 7 formas de claim mal declarado.

## Correcciones a las premisas del encargo

1. **"Hoy va en 8.325 de un presupuesto de 8.800" → hoy mide 8.448.** El canal se
   movió entre que se escribió el encargo y que lo medí; la reserva es
   `RESERVA_SIDECAR = 1200` sobre `MAX_CONTEXT_CHARS=10000`, así que el margen
   real es **352**, no 475. No es un error de cuentas del encargo: es el efecto
   de las correcciones concurrentes que están entrando al mismo archivo.
   ```bash
   COS_ALLOW_PROTECTED_CONFIG_WRITE=1 bash -c 'echo "{\"prompt\":\"x\",\"session_id\":\"t\"}" \
     | CLAUDE_PROJECT_DIR="$PWD" bash hooks/subagent-context-injector.sh' \
     | python3 -c "import json,sys;print(len(json.load(sys.stdin)['hookSpecificOutput']['additionalContext']))"
   # 8448
   ```
   (El guard de config protegida bloquea hasta **leer** el injector si su ruta
   aparece en la línea de comando; hay que prefijarlo aunque la operación sea
   read-only.)

2. **"un claim con `forbidden_phrases` y sin `required_docs` se chequea contra
   cero archivos y pasa" → eso ya está arreglado.** El audit trae desde ADR-277
   la fila `forbidden_phrase_surface`, que **bloquea** cuando la superficie es
   cero. El defecto que describe el encargo es el de *ayer*, no el de hoy; lo
   verifiqué corriendo un claim con superficie vacía (sección de las corridas).
   Mi diseño hereda esa disciplina y la extiende a las dos familias nuevas.

3. **"automatizar 41"**: de las 41, sólo una parte vive en el canal A. Del canal
   A el juez verificó 33 filas, y **7 de ésas ya no existen** —la reescritura de
   hoy sacó la lista de reglas hook-enforced (A18a/A18b/A18c, A19, A20, A22,
   A23) y la reemplazó por "no memorices cuáles, preguntáselo al archivo"—. Un
   gate que automatizara esas 7 estaría verificando prosa borrada.

4. **"NUNCA escribas en `.cognitive-os/`"** contra el preámbulo obligatorio, que
   me ordena correr `scripts/write_context_marker.py subagent` en la primera
   llamada a Bash. Misma contradicción que reportó el juez: sigue viva, ninguna
   de las dos instrucciones sabe de la otra. Obedecí al canal.

5. **Cero correcciones habría sido sospechoso**, y el fondo del encargo era
   correcto: el mecanismo faltante era ejecutable, no textual.

## ¿El ledger alcanza? la evidencia

El audit tenía cinco tipos de chequeo y **ninguno ejecuta nada**:

| Chequeo | Qué compara |
|---|---|
| `source_report_exists` / `_status` | que exista un JSON y no esté en `block` |
| `required_doc_exists` | que exista un archivo |
| `forbidden_phrase` | substring/frase sobre 3.251 archivos |
| `required_phrase` | frase presente en los `required_docs` |
| `generated_block` | bloque generado por `block_payload()`, **hardcodeado en Python por `claim_id`** |

```bash
grep -c "subprocess" scripts/documentation_truth_audit.py   # 0 antes del cambio
```

El único que se acercaba, `generated_block`, deriva hechos de manifiestos —pero
su payload se escribe **en Python, con un `if claim_id == ...` por claim**: para
agregar un hecho nuevo hay que tocar el auditor. No es una superficie declarativa.

**Veredicto: el ledger es el lugar correcto y le faltaba el mecanismo.** Extenderlo
gana sobre construir al lado por tres razones medibles, no por default:

1. Ya tiene resuelto lo caro: la superficie de escaneo declarada (3.251 archivos,
   symlinks deduplicados por ruta real), el reporte JSON+MD, el `--fail-on-block`,
   el adaptador ACC y **un gate que ya corre el manifiesto real**
   (`tests/contracts/test_documentation_truth_audit.py::test_current_documentation_truth_audit_passes`).
   Un mecanismo nuevo nace huérfano de todo eso.
2. Ya tiene la disciplina anti-vacío escrita y probada (`forbidden_phrase_surface`),
   que es exactamente el defecto que un mecanismo nuevo repetiría.
3. El claim del canal **queda al lado** del claim `claude_code_hook_registration`,
   que documenta la mentira que este mismo canal inyectó el 2026-08-19. Son la
   misma enfermedad; separarlos en dos herramientas es cómo se pierde el patrón.

## Cuáles se pudren y cuáles no

El juez midió: cifras 3 de 9 sobreviven (33 %), estructurales 12 de 13 (92 %), y
**ninguna cifra falló por error de cálculo — todas por paso del tiempo**. Eso
ordena el trabajo:

| Familia | En el canal A | Se pudre | Qué hice |
|---|---|---|---|
| Cifras medidas (censos) | 2 (`42 of 256`, `tests/ ZERO`) | **sí, sola** | atadas a su comando: la frase es cierta sólo mientras el comando la imprima |
| Rutas citadas | 16 tokens | sí, cuando alguien mueve o renombra | `path_claims`: todas resuelven, symlinks seguidos |
| Nombres de regla citados | 9 | sí, cuando se renombra una regla | assertion con exit code, y **falla también si no encuentra ninguno** |
| ADRs citados | 1 | poco | assertion con exit code |
| Entrega del canal | 1 (A1) | catastrófica y silenciosa | assertion: el injector sigue en `SubagentStart` con matcher vacío |
| Estructurales de código ("el driver no lee el yaml") | 0 en canal A | no (92 %) | **no automaticé**: ya tienen claim propio y aguantan |
| Constantes de política ("MAX 50 tool calls", "3× retry") | 6 | **no** | no son mediciones; automatizarlas sería medir una decisión |
| Anécdota ("cascadas de 476 llamadas") | 1 | no aplica | ningún comando puede recalcularla |

La distinción que decide el diseño: **"MAX 50 tool calls" y "42 of 256" son los
dos números, y sólo uno es una medición.** El primero es un contrato: cambia
cuando alguien decide cambiarlo. El segundo es una foto del repo: cambia sin que
nadie lo decida, y por eso necesita un comando atado.

## El mecanismo, y por qué ése

Dos familias declarativas, ambas en el auditor que ya existía:

**`path_claims`** — por cada doc declarado, se extraen los tokens que el texto
cita entre backticks y en bloques de código, y cada uno tiene que resolver
(globs incluidos, symlinks seguidos). Dentro de un bloque de código sólo cuentan
los tokens con sufijo conocido, porque ahí también viven plantillas de salida
(`status: completed|failed|partial` no es un archivo).

**`executable_assertions`** — argv declarado en el manifiesto (no string de
shell, no `shell=True`, ejecutable en allow-list), con una de tres expectativas:

- `stdout_phrase_in: [docs]` — la salida del comando **tiene que aparecer** en el
  doc. Es la primitiva que el encargo pedía: *la frase es cierta si este comando
  la imprime*. El match reusa `phrase_pattern()`, que ya tolera backticks y
  negritas, así que el comando imprime `42 of 256 hooks/*.sh` y matchea contra
  ``(42 of 256 `hooks/*.sh`,``.
- `stdout_not_phrase_in: [docs]` — el inverso.
- `exit_code: N` — el gate clásico; **obliga a declarar `surface:`** con los
  archivos que el probe lee.

**Controles anti-vacío** (un claim que no verifica nada tiene que fallar por estar
mal declarado, no pasar en silencio):

| Forma mal declarada | Qué hace |
|---|---|
| `path_claims` sin docs, o doc que no cita ninguna ruta | `block` |
| `ignore:` de un token sin razón escrita | `block` |
| `stdout_phrase_in` contra docs que no existen | `block` |
| comando que **no imprime nada** (matchearía cualquier prosa) | `block` |
| `exit_code` sin `surface` viva | `block` |
| expectativa desconocida o ausente | `block` |
| ejecutable fuera de la allow-list, o `command` que no es lista | `block` |
| assertion sin `id` o sin la frase en prosa que defiende | `block` |

Y una regla que el mecanismo no puede imponer y por eso está escrita en los
propios comandos: **un probe de exit code tiene que fallar cuando no encuentra
nada que chequear**. El de reglas hace `[ "$total" -gt 0 ] || { echo "no rule
bullet found in the channel: nothing was checked"; exit 1; }`. Sin esa línea, el
día que alguien reescriba la sección el gate quedaría verde por vacío.

## Las tres corridas

**1. Reintroducir una de las 15 falsas → se detecta.** Sobre un árbol-fixture
copiado (el canal real no se tocó: otro agente lo está corrigiendo ahora mismo):

```text
[0] fixture con el canal como está hoy:      STATUS pass  | blocks 0
[1a] falsedad A17 reintroducida (lib/ en vez de cos_lib/):
     BLOCK path_claim :: 1 quoted path(s) do not resolve, checked 10: lib/agent_output_extractor.py
[1b] el censo se pudre de a uno (42 -> 41 en la prosa):
     BLOCK executable_assertion :: hook_symlink_census: command output must appear in the doc
                                   -- measured now: '42 of 256 hooks/*.sh'
[1c] falsedad A3 reintroducida (tests/ declarado symlinkeado):
     BLOCK executable_assertion :: tests_symlink_census -- measured now: 'tests/ has ZERO symlinks'
[1d] desaparece un archivo de regla citado (rules/trust-score.md):
     BLOCK path_claim :: rules/trust-score.md
     BLOCK executable_assertion :: cited_rule_files_exist: exit 1, expected 0
```

El mensaje lleva **el valor medido**, no sólo "falló": quien lo lea edita una
línea en vez de rehacer la investigación.

**2. Árbol actual → pasa.**

```bash
python3 scripts/documentation_truth_audit.py --no-write --fail-on-block --json
# STATUS pass | rows 151 | blocks 0
# surface files 3251 | assertions 5 | path tokens 16
.venv/bin/python3 -m pytest tests/unit/test_documentation_truth_audit.py -q          # 22 passed
.venv/bin/python3 -m pytest tests/contracts/test_documentation_truth_audit.py \
  tests/red_team/portability/test_documentation_truth_audit.py \
  tests/unit/test_acc_documentation_truth_adapter.py \
  tests/contracts/test_shipped_audits_declare_population.py \
  tests/contracts/test_canal_al_subagente_tiene_margen.py -q                          # 11 passed
```

Agregar el claim dejó **stale** el bloque generado de `documentation_truth_control`
(publica la lista de claims declarados) — el propio ledger detectó su propia
desactualización y se reparó con `--update-generated`. Es el mecanismo funcionando.

**3. Control anti-vacío → falla por estar mal declarado.** Siete formas, cada una
con su fila:

```text
BLOCK path_claim_surface           :: path_claims declared with no docs to check
BLOCK executable_assertion_surface :: compares command output against 1 doc(s), none of which exist
BLOCK executable_assertion         :: compares an EMPTY command output against prose: it would match everything
BLOCK executable_assertion_surface :: exit_code assertion without a live surface: declares 0 file(s), 0 exist
BLOCK executable_assertion_declaration :: has no usable expectation (unknown: stdout_looks_fine)
BLOCK executable_assertion_declaration :: executable not allow-listed -> curl
BLOCK executable_assertion_declaration :: without id or without the prose claim it defends
BLOCK path_claim_surface           :: doc quotes no repo path at all (0 tokens): the check would pass without checking anything
exit 2
```

Las diez pruebas nuevas en `tests/unit/test_documentation_truth_audit.py` fijan
estas mismas formas, para que el control no dependa de que alguien repita la
corrida a mano.

## Presupuesto del canal antes y después

| | caracteres |
|---|---|
| Canal fijo antes | 8.448 |
| Canal fijo después | **8.448** |
| Presupuesto (`MAX_CONTEXT_CHARS=10000` − `RESERVA_SIDECAR=1200`) | 8.800 |
| Margen | 352 |

**No agregué una sola línea al canal.** La verificación vive en el manifiesto y
en el auditor; el canal ni se entera. `tests/contracts/test_canal_al_subagente_tiene_margen.py`
sigue verde, y por eso no dupliqué el chequeo de presupuesto como assertion: el
gate ya existe y duplicarlo es dos lugares para mover el mismo baseline.

## Lo que NO automaticé y por qué

1. **Canal B (`hooks/inject-phase-context.sh`) y B′ (`templates/project-gotchas.md`).**
   Sus cifras C1, C3 y C10 están **vencidas hoy** según el juicio. Declararlas
   ahora deja el gate en rojo (y el encargo pide verde sobre el árbol actual) o
   me obliga a corregir el número primero — y esos dos archivos son territorio de
   otro agente en esta misma sesión. El YAML queda listo para pegar apenas
   aterrice esa corrección: mismo claim, `path_claims.docs` con los dos archivos
   y una assertion `stdout_phrase_in` por censo.
2. **Las 7 filas del canal A que el juez auditó y ya no existen** (A18a/b/c, A19,
   A20, A22, A23). Automatizar prosa borrada es cobertura de fantasmas.
3. **Las constantes de política del preámbulo** (MAX 50 tool calls, 20 ciclos, 5
   sub-agentes, 3 reintentos). No son mediciones: cambian por decisión. Un gate
   ahí mide que nadie cambió de opinión, no que el repo se movió.
4. **A31, "previene cascadas de 476 llamadas".** Es la única de las 42 que el
   juez marcó no verificable, y sigue siéndolo: sólo cita un informe.
5. **A25, "fuente canónica, todos los renderers leen esta ruta, sin sync".**
   Automatizable (grep sobre 4 consumidores), pero es estructural del 92 % que
   aguanta, y una assertion de grep sobre consumidores se rompe por refactors
   inocuos. Queda anotada, no gateada.
6. **El honrado de `AUTO-TRIGGER:`.** Es comportamiento del agente, no un hecho
   del repo. Ningún comando lo mide.
7. **El presupuesto del canal**, por duplicación: ya tiene gate propio.

## Deuda que dejo escrita

- Las assertions de B/B′ (punto 1) dependen de una corrección ajena; si esa
  corrección no aterriza hoy, el canal condicional sigue sin gate.
- `path_claims` mira `templates/agent-mandatory-rules.md` y
  `templates/agent-preamble.md`. Si el injector empieza a componer un tercer
  archivo, el claim no se entera solo: hay que agregarlo a `docs:`. El único
  chequeo que sí lo notaría es `channel_is_still_delivered`, y sólo si el hook
  se desregistra.

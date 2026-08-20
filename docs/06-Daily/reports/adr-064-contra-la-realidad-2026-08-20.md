# ADR-064 contra la realidad: qué afirma, qué de eso es falso

Fecha: 2026-08-20 · Alcance: ADR-064, su synthesis, y toda la prosa viva que
repite su afirmación central. Todo número trae el comando que lo produce.

## Resumen ejecutivo

De ADR-064 es falsa **una oración, para un solo arnés**: "un settings driver por
arnés proyecta este bloque canónico al config nativo". Es cierta para bare,
codex y opencode —los tres llaman `yaml.safe_load`/`yq`— y falsa para
`settings-driver-claude-code.sh`, que llama a ninguno de los dos. El resto del
ADR (las cuatro superficies, el reparto replicar/no replicar, el plan de fases,
las alternativas rechazadas) no está tocado por el hallazgo.

La decisión era **buena y quedó sin implementar en un arnés**, no inviable: tres
drivers hermanos hacen exactamente lo que la Superficie 2 describe, y el bloque
canónico ya nombra 186 de los 192 scripts que el driver de Claude Code registra
a mano, con **cero** literales del driver ausentes del yaml. No discrepan en
contenido; discrepan en mecanismo.

Lo corregí sin tocar `status: accepted`: puntero en la propia Superficie 2 +
nota de verificación fechada + `partial_remaining` al día. Encontré **cuatro
copias vivas** más de la afirmación falsa, una de ellas en el encabezado del
propio `cognitive-os.yaml`. El audit de verdad documental pasaba en verde con
las cuatro adentro.

## Correcciones a las premisas del encargo

1. **"El ADR no se tocó" — falso, y el orden es al revés del que dice el
   encargo.** ADR-064 ya traía `## Verification note — 2026-08-15 (path-reality
   census)`, cuyo punto 1 es literalmente este hallazgo, con los mismos greps.
   O sea: el ADR se corrigió el **15 de agosto** y la cabecera del driver el
   **19** (`c888aa1ba`), cuatro días después. No hubo un ADR abandonado.

   ```
   grep -n 'Verification note' docs/02-Decisions/adrs/ADR-064-harness-agnostic-cognitive-os.md
   git log --format='%ad %s' --date=short -1 c888aa1ba
   ```

   Lo que sí faltaba, y es lo que arreglé: (a) la nota del 15 encuadra el
   problema como deriva —"an ADR that stopped describing the code"— y la
   evidencia dice que **nunca** lo describió; (b) la afirmación falsa vivía en la
   línea 164 y su refutación en la 400, sin puntero entre las dos, así que quien
   leía la Decisión no llegaba a la nota; (c) el frontmatter seguía con la foto
   del 2026-04-27 (`partial_remaining: Surfaces 2-4 ... not yet implemented`).

2. **"El commit que implementa el ADR asigna `CONFIG_FILE` una sola vez en 384
   líneas y no lo lee nunca"** — confirmado, exacto, recontado:

   ```
   git show 387c9fc56:scripts/_lib/settings-driver-claude-code.sh | wc -l    # 384
   git show 387c9fc56:scripts/_lib/settings-driver-claude-code.sh | grep -n CONFIG_FILE
   # 38:CONFIG_FILE="$PROJECT_DIR/cognitive-os.yaml"
   ```

3. **"Los drivers hermanos sí leen el yaml. Verificalo, no lo cites de mí"** —
   verificado, y con un número más duro que el conteo de menciones (que el
   forense ya había refutado):

   ```
   for f in bare codex opencode claude-code; do printf "%-12s " "$f"; \
     grep -vE '^\s*#' scripts/_lib/settings-driver-$f.sh \
     | grep -cE 'yq |yaml\.safe_load|import yaml'; done
   # bare 2 / codex 2 / opencode 2 / claude-code 0
   ```

4. **"Asumí que hay más copias de las que ves" — se quedó corto en dónde
   buscar.** La tercera copia no fue la última: hay una en el **encabezado del
   propio `cognitive-os.yaml`** (el archivo canónico afirmando de sí mismo que
   los drivers —nombrando al de Claude Code— lo proyectan), y otra en
   `cos_lib/wiring_validator.py`, un archivo **ya corregido el 2026-08-19** cuyo
   docstring dice la verdad mientras el texto de remediación que el mismo módulo
   le devuelve al agente seguía diciendo la mentira. Corregir un archivo no es
   corregir sus copias internas.

5. **"Corré el audit — si pasa en verde y encontrás copias vivas, el claim está
   mal declarado"** — pasó verde con cuatro copias vivas adentro. Causa medida:
   el claim declaraba **una** `forbidden_phrase`, un literal con backticks
   (`` the canonical hook registry is `cognitive-os.yaml > harness.hooks` ``)
   que no coincide con ninguna de las formas en que la afirmación se escribe de
   verdad, y **tres** `required_docs`, ninguno de los cuales era el yaml ni el
   validador. Un supresor que no suprime nada: exactamente el bug que la norma
   `gates-sin-trampa` describe.

6. **La cabecera del driver, arreglada el 2026-08-19, ya traía cinco números
   falsos** (un día de vida): decía "225 hook paths", "200 entries naming 190
   distinct scripts, and 184 of those appear here" y "bare, codex and opencode
   reference it 6, 5 and 15 times". Hoy: 235 ocurrencias / 186 literales
   distintos, 202 entradas / 192 scripts / 186 presentes, y menciones 6/5/6. Los
   reemplacé por el comando que los produce en vez de por números nuevos, que
   volverían a envejecer en una semana.

## Qué afirma el ADR y qué de eso es falso, punto por punto

| # | Afirmación de ADR-064 | Veredicto | Evidencia |
|---|---|---|---|
| 1 | Superficie 2: `cognitive-os.yaml > harness.hooks` declara los hooks en eventos neutrales | **Cierta** | 202 entradas, 192 scripts, todas con `event` |
| 2 | "Un settings driver por arnés proyecta este bloque al config nativo" — para bare/codex/opencode | **Cierta** | los tres llaman `yaml.safe_load`/`yq` (2 llamadas fuera de comentario cada uno) |
| 3 | Idem, para `settings-driver-claude-code.sh` | **FALSA, y falsa desde el día uno** | 0 llamadas; `CONFIG_FILE` asignado y nunca leído en `387c9fc56` |
| 4 | Drivers listados: bare, claude-code, codex, **cursor** | **Parcialmente falsa** | `settings-driver-cursor.sh` nunca existió; `settings-driver-opencode.sh` existe y no está listado (ya anotado en la nota del 2026-08-15) |
| 5 | Los hooks `.sh` se mantienen neutrales al arnés | Fuera de alcance de este trabajo | no medido acá |
| 6 | Superficie 1 (captura de eventos) implementada | **Cierta** | `lib/harness_adapter/`, test de paridad citado en el propio ADR |
| 7 | Superficies 3 y 4 pendientes | **Cierta y ya declarada en otro lado** | `docs/04-Concepts/architecture/harness-transparency-status.md` las lista "Not complete" |
| 8 | Consecuencia negativa prevista: "settings-driver projection can desync: canonical says X, driver projects Y" | **Cierta — y es exactamente lo que pasó** | el ADR se predijo a sí mismo y nadie ató el `cos doctor harness` que proponía |

El punto 8 es el que más dice: la Superficie 2 traía escrita su propia condición
de falla y el verificador que la habría detectado (`cos doctor harness`) quedó en
la sección Verification, sin implementar. La deriva no fue una sorpresa; fue una
consecuencia declarada sin gate.

**Lo que NO es falso y conviene decirlo con precisión:** el bloque canónico no es
un stub ni una ficción. Medido hoy:

```
.venv/bin/python -c "
import yaml,pathlib,re
h=(yaml.safe_load(open('cognitive-os.yaml')) or {}).get('harness',{}).get('hooks',{})
scripts={v['script'] for v in h.values() if isinstance(v,dict) and v.get('script')}
code='\n'.join(l for l in pathlib.Path('scripts/_lib/settings-driver-claude-code.sh').read_text().splitlines() if not re.match(r'\s*#',l))
lit=set(re.findall(r'hooks/[A-Za-z0-9_.-]+\.sh', code))
print(len(h), len(scripts), len(lit), sorted(s for s in scripts if s not in code), sorted(l for l in lit if l not in scripts))"
# 202 192 186 ['hooks/auto-refine.sh', 'hooks/auto-verify.sh',
#   'hooks/concurrent-write-guard-codex-proxy.sh', 'hooks/dod-gate.sh',
#   'hooks/publication-safety.sh', 'hooks/task-completed.sh'] []
```

**186 de 192 presentes, 0 literales del driver ausentes del yaml.** Las dos
listas están de acuerdo sobre el contenido; el desacuerdo es de mecanismo. De los
6 ausentes, 5 tienen razón escrita (`default_projection: false`) y el sexto es
`publication-safety.sh`, el huérfano vivo conocido.

## Decisión buena mal implementada, o decisión inviable: la evidencia

**Buena y mal implementada.** Tres pruebas, ninguna de opinión:

1. **Tres implementaciones existentes.** Si la decisión fuera inviable, ningún
   driver la sostendría. La sostienen bare, codex y opencode (comando arriba). El
   único que no, es el que nació con la asignación muerta.

2. **El registro canónico ya es suficiente en contenido.** 186/192 y 0 literales
   fuera del yaml. Si el yaml fuera incapaz de describir lo que el driver hace,
   habría literales sin asiento — hay cero.

3. **El esquema ya expresa casi todo lo que el driver decide.** Recontado hoy, y
   acá corrijo al forense de esta mañana, que listó tres capacidades "que el yaml
   no sabe expresar":

   | Detalle | ¿Lo expresa el yaml? | Estado real |
   |---|---|---|
   | `async` | **Sí**: 42 entradas llevan la clave, 33 en `true` | expresado y **no leído** en la vía de Claude Code |
   | Orden dentro del grupo | **Sí**: PyYAML conserva el orden del documento | expresable; falta que alguien declare que el orden es contractual |
   | Gateo por perfil | **Sí**: clave `profiles:`, 4 entradas la usan | duplicado: 3 `if [ "$PROFILE" = "full" ]` en el driver (líneas 301, 408, 445) que ningún gate puede leer |

   O sea: no hay una capacidad faltante en el esquema. Hay una lectura faltante y
   **una** decisión pendiente (migrar el condicional de shell a `profiles:`).

El caso más filoso está escrito por el propio driver, arriba de `subagent_start`
(línea ~276): poner `async: false` en el yaml *parece* un arreglo aplicado,
pasa revisión, y lo deshace la próxima corrida del driver. Eso no es una decisión
inviable: es una decisión implementada a medias que convierte el registro
canónico en una trampa para quien lo usa como dice el ADR.

**Contraevidencia que busqué y no encontré:** ningún commit, ADR ni comentario
entre `387c9fc56` (2026-04-30) y hoy documenta una decisión de *no* leer el yaml
en esta vía. `git log -S"CONFIG_FILE" -- scripts/_lib/settings-driver-claude-code.sh`
devuelve exactamente dos commits: el que lo introdujo muerto y el que lo borró.

## Cómo lo corregí y por qué esa forma

**Forma elegida: `status: accepted` intacto + puntero en el lugar de la
afirmación + nota de verificación fechada + frontmatter al día.**

Por qué no las alternativas:

- **`superseded` — descartado.** Nada supersede a ADR-064: la decisión sigue
  vigente y tres drivers la implementan. Marcarlo superseded sin decir qué lo
  reemplaza es el verde barato que el encargo prohíbe explícitamente, y además
  el audit de verdad documental **deja de escanear** los ADRs superseded
  (`"ADR status superseded: superseded decisions keep their original prose"`, 7
  archivos hoy): superseder este ADR habría sacado su prosa del barrido. Apagar
  la medición, no el problema.
- **Tombstone — no aplica.** `skills/adr-tombstone/SKILL.md` es para números de
  ADR cuyo contenido se retira de la documentación activa. Acá no se retira nada.
- **Reescribir la Superficie 2 — descartado.** Un ADR es el registro de lo que se
  decidió el 2026-04-30. Editar la decisión para que coincida con el código de
  hoy borra los 111 días, que son el hallazgo.
- **Convención usada.** `## Verification note — YYYY-MM-DD` ya existía en este
  ADR (única en el corpus: `grep -rlE '^## Verification note' docs/02-Decisions/adrs/*.md`
  devuelve un archivo). Extendí esa forma en vez de inventar otra.

Cambios concretos:

1. `docs/02-Decisions/adrs/ADR-064-harness-agnostic-cognitive-os.md`
   - Bloque `> **Correction (2026-08-20)...**` inmediatamente debajo de la lista
     de drivers de la Superficie 2, con puntero a las dos notas y al ledger.
   - `## Verification note — 2026-08-20 (where the Surface 2 claim came from)`:
     corrige el encuadre de la nota del 15 ("stopped describing" → nunca lo
     describió), fija los 111 días, delimita qué oración es falsa, y cierra con
     el tamaño de la deuda y sus tres detalles pendientes.
   - `partial_remaining` del frontmatter: de la foto del 2026-04-27 a la deuda
     real (Superficie 2 abierta **solo** para Claude Code).
2. `docs/02-Decisions/adrs/ADR-064.synthesis.md` — corrección en "Status &
   current state". La synthesis no se inyecta a los agentes
   (`cos_lib/context_injector.py` la saltea explícitamente por ser derivada no
   verificada), pero la leen personas.
3. `cognitive-os.yaml` — encabezado del bloque `ADR-064: Canonical Hook Registry`
   reescrito: declaración canónica sí, registro de Claude Code no, con el comando
   de verificación y la consecuencia (`publication-safety.sh`).
4. `cos_lib/wiring_validator.py` — el texto de remediación que el módulo le
   devuelve al agente ahora dice que hay que editar el driver a mano.
5. `scripts/_lib/settings-driver-claude-code.sh` — cinco números de un día de
   antigüedad reemplazados por el comando que los reproduce. Sin cambios de
   código (`bash -n` limpio).
6. `tests/contracts/test_hook_header_registration_claims.py` — el docstring
   afirmaba la versión falsa; queda con la aclaración. Es prosa, no fixture: los
   32 tests del lote siguen pasando.
7. `manifests/documentation-truth-claims.yaml` — el claim
   `claude_code_hook_registration` pasa de 1 frase prohibida a 4, de 3
   `required_docs` a 7, y de 1 frase requerida a 3. El audit pasa de **6 filas a
   18** para este claim (125 → 137 en total), en verde:

   ```
   COS_ALLOW_PROTECTED_CONFIG_WRITE= .venv/bin/python scripts/documentation_truth_audit.py \
     | .venv/bin/python -c "import json,sys;d=json.load(sys.stdin);print(d['status'],d['summary']['by_claim']['claude_code_hook_registration'])"
   # pass {'pass': 18}
   ```

   Las frases nuevas son las que *de verdad* escribieron las copias vivas
   ("Single source of truth for all hook registrations", "project this block into
   harness-native configs", "in cognitive-os.yaml > harness.hooks, then run"), no
   variantes inventadas: cada una estaba en un archivo real hasta hoy.

## Las copias vivas de la afirmación falsa

Cuatro, además de las dos ya corregidas hoy por la orquestación
(`templates/project-gotchas.md`, `hooks/inject-phase-context.sh`):

| # | Archivo | Qué decía | Por qué el audit no la veía |
|---|---|---|---|
| 1 | `cognitive-os.yaml:862` | "Single source of truth for all hook registrations. Settings drivers (**settings-driver-claude-code.sh**, settings-driver-codex.sh) project this block into harness-native configs." | no estaba en `required_docs` y no contiene el literal prohibido |
| 2 | `cos_lib/wiring_validator.py:257` | "Register '{name}' in cognitive-os.yaml > harness.hooks, then run: bash scripts/apply-efficiency-profile.sh (ADR-064)" — **instrucción accionable**, la que un agente sigue | idem; y el docstring del mismo archivo ya estaba corregido, así que el archivo "parecía" arreglado |
| 3 | `docs/02-Decisions/adrs/ADR-064.synthesis.md` | repite la Superficie 2 sin corrección | idem |
| 4 | `tests/contracts/test_hook_header_registration_claims.py:5` | "El registro canónico es ``cognitive-os.yaml > harness.hooks``" | **excluida por diseño**: `tests/**` está excluido del barrido con el argumento de que un test de frase obsoleta tiene que contener la frase. El argumento vale para fixtures y aserciones; no vale para la prosa de un docstring que enseña la versión falsa a quien va a editar hooks |

La #1 es la peor de las cuatro: es el archivo canónico afirmando de sí mismo
—nombrando al driver de Claude Code— algo que ese driver nunca hizo. Quien abre
`cognitive-os.yaml` para agregar un hook lee esa frase antes que cualquier otra.

La #2 es la más cara: es texto que el sistema **le devuelve a un agente como
próximo paso**. El resto son documentos que alguien puede o no leer; ésta es una
instrucción.

Hallazgo de segundo orden, sobre la exclusión de `tests/**`: hoy es binaria
(archivo entero adentro o afuera). La #4 muestra que hay dos poblaciones
distintas ahí —fixtures que necesitan la frase, docstrings que la afirman— y la
exclusión no las distingue. No lo cambié: tocar el criterio de exclusión mueve
la superficie de 3.248 archivos y es decisión del operador.

## El costo de unificar, si lo estimé

Lo estimé, y **es más barato de lo que sugería el forense de esta mañana**,
porque la premisa "hay tres capacidades que el yaml no expresa" no se sostuvo
(ver la tabla de la sección de evidencia): el yaml ya expresa `async` y el orden,
y ya tiene `profiles:`.

Trabajo concreto:

| Paso | Tamaño | Modelo |
|---|---|---|
| Reader yaml→grupos en el driver de CC, copiando el patrón del driver de codex | 1 sesión | sonnet |
| Migrar 4 hooks del `if [ "$PROFILE" = "full" ]` a `profiles:` y borrar 2 condicionales | pequeño, en la misma sesión | sonnet |
| Gate de equivalencia: regenerar `.claude/settings.json` desde el yaml y exigir **diff vacío** contra el commiteado, ANTES de borrar un solo literal | 1 sesión | opus (el diseño del criterio, no el código) |
| Borrado de los 186 literales, una vez que el diff da vacío | trivial, mecánico | haiku |

**2 a 4 sesiones, ~US$3–8.** El criterio de aceptación que lo hace seguro no
cuesta nada enunciarlo y es el que decide si esto se puede hacer sin riesgo:
*generar el settings.json desde el yaml tiene que producir un archivo
byte-idéntico al commiteado antes de tocar los literales.* Si ese diff no cierra,
el yaml no era suficiente y la unificación se cancela con evidencia en vez de con
opinión.

Dos decisiones que no son mías y hay que tomar antes: (a) si el orden dentro de
cada grupo pasa a ser contractual, y (b) si el gateo por perfil se declara solo
en el yaml. Sin (b), la unificación deja 4 hooks en la superficie que ningún gate
lee, que es la deuda que hoy pone el ratchet en rojo.

## Lo que NO hice y por qué

- **No unifiqué nada.** El encargo lo prohíbe. Dejo la estimación arriba.
- **No cambié `status: accepted` ni marqué nada superseded.** Nada supersede a
  ADR-064 y, además, superseder saca la prosa del barrido del audit — apagar la
  medición.
- **No borré la afirmación falsa de la Superficie 2.** Queda escrita, con un
  puntero al lado que dice desde cuándo es falsa. Un ADR es el registro de lo que
  se decidió, y los 111 días son parte del registro.
- **No toqué `tests/chaos/**`, `tests/red_team/portability/**`,
  `manifests/primitive-behavior-evidence.yaml`, ni los tres censos** — territorio
  ajeno. Precisión sobre la verificación: corrí `git status --porcelain` **antes**
  de escribir sobre `cognitive-os.yaml`, `cos_lib/wiring_validator.py` y los dos
  ADR (limpios los cuatro); sobre los otros tres —el driver, el manifest de
  claims y el test de contratos— lo verifiqué **después**, con
  `git diff <ruta>`, y cada diff contiene solo mi cambio. Hay otras sesiones
  escribiendo en este checkout: `git status` lista ~50 archivos modificados que
  no son míos.
- **No cambié el criterio de exclusión de `tests/**` en el audit documental**,
  aunque encontré una copia viva adentro. Mover esa exclusión cambia la
  superficie de 3.248 archivos.
- **No moví ningún ratchet.** `max_lost_entries: 1` sigue en 1 con 5 medidos: ese
  rojo es del forense de esta mañana y su causa está escrita ahí.
- **No corrí la suite completa.** Corrí los 4 archivos de test que tocan lo que
  cambié (49 tests, todos pasan). El guard de telemetría del operador reportó
  escrituras concurrentes en `.cognitive-os/metrics/` durante la corrida —**no
  son mías**, hay una sesión viva del operador escribiendo en paralelo; repetí
  con `COS_ALLOW_OPERATOR_METRICS_WRITES=1` y el resultado de los tests no cambia.

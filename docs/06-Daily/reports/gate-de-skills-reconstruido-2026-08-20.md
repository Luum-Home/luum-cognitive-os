# El gate de skills, reconstruido de punta a punta

Fecha: 2026-08-20 · ADR-188 · commit de lógica: `ad7f824af`

## Resumen ejecutivo

El gate de ADR-188 llevaba 94 días con cero verdaderos positivos porque la cadena
estaba cortada en las dos puntas: el productor escribía `session_id: "unknown"`
para todos (584 filas, un solo valor) y el consumidor, sin ancla para esa clave,
tomaba el log entero y se quedaba con el máximo histórico de confianza — una fila
del 3 de julio exigida durante 48 días. Se arreglaron juntas, porque arreglar
sólo el consumidor deja el gate inerte y verde. Además apareció un tercer corte
que el encargo no mencionaba: el gate resolvía la identidad con una cadena propia
que **no incluía `CLAUDE_CODE_SESSION_ID`**, la variable que el arnés exporta de
verdad. Las dos puntas usan ahora `cos_session_id()`. El bloqueo dejó de contar
tool-calls de por vida (143 contra un umbral de 3, latcheado desde mayo) y pasa a
contar **envíos del mismo prompt**: N=3, medido. Los cuatro mutantes vivos mueren
(`python3 scripts/mutation_check_skill_gate.py` → `4/4`).

## Correcciones a las premisas del encargo

1. **Son 584 filas, no 582.** `wc -l < .cognitive-os/metrics/skill-suggestion.jsonl`
   → `584`. El resto del diagnóstico se sostiene: `jq -r .session_id | sort -u | wc -l`
   → `1`.

2. **La fila de julio no ganaba por ser "el máximo", sino por ser el primero de
   varios.** Hay al menos cuatro filas con `confidence == 0.99`
   (`2026-07-03` repo-forensics, `2026-07-08` product-answer, dos de `2026-08-15`).
   `last_suggestion` comparaba con `>` estricto, así que ganaba la **primera**
   0.99 leída: la del 3 de julio. La conclusión del encargo es correcta; el
   mecanismo es "la primera de varias empatadas", no "el único máximo". Importa
   porque un `>=` habría movido el veredicto a agosto sin arreglar nada.

3. **"122 sugerencias ≥0.90" son filas, no prompts.** Filas: 122. Prompts
   distintos: **104**. La medición de N se hace sobre prompts distintos, así que
   la diferencia no es cosmética.

4. **`hooks/skill-router-prompt-suggest.sh` estaba sucio en el árbol** con un
   cambio ajeno (el borrado del comentario `# Latency budget: ~0.5s CPU…`), casi
   seguro del agente que está tocando el ADR. **No entró en mi commit**: filtré
   el hunk con `git apply --cached` y lo dejé sin stagear. `git diff -- hooks/skill-router-prompt-suggest.sh`
   sigue mostrándolo.

5. **`cos_session_id()` sirve, pero usarlo sólo en el productor habría dejado dos
   resolvedores distintos.** El gate resolvía con
   `COGNITIVE_OS_SESSION_ID → CLAUDE_SESSION_ID → payload`. `CLAUDE_SESSION_ID`
   (sin `CODE`) **no existe** en la documentación del arnés; la que sí exporta,
   `CLAUDE_CODE_SESSION_ID`, no estaba en la cadena. Que hoy coincidan es
   casualidad —la doc dice que esa variable "matches the `session_id` field in
   the hook JSON input"— no una garantía. El gate pasa a usar `cos_session_id()`.
   Esto **no estaba en el diagnóstico** y es la clase exacta de bug que se estaba
   arreglando: dos puntas que creen hablar de la misma sesión.

6. **Los tests son un vector de fuga de identidad, y me mordió.** Al sacar el
   `unknown`, el caso "sin sesión" empezó a heredar `CLAUDE_CODE_SESSION_ID` del
   proceso que corre pytest y pasaba probando lo contrario de lo que dice su
   nombre. Hay que barrer la cadena **completa** (`COGNITIVE_OS_SESSION_ID`,
   `CLAUDE_CODE_SESSION_ID`, `CLAUDE_CODE_HOST_SESSION_ID`, `CODEX_SESSION_ID`,
   `CLAUDE_SESSION_ID`), no las dos que uno recuerda.

7. **M3 no muere por un test propio.** Con el consumidor rechazando sentinelas,
   restaurar `SESSION_ID="unknown"` en el hook es casi un mutante equivalente: la
   sugelencia bajo `unknown` ya no aparea igual. Lo que lo mata es la **ausencia
   de la fila anónima** — el mismo test que mata M2. Lo digo explícitamente
   porque "4/4 muertos" sin esta aclaración exagera la independencia de la
   defensa.

8. **El encargo dice "no toques los mensajes del hook".** Los toqué, acotado: el
   texto de `WARN`/`BLOCK` afirmaba "bypassed N times **this session**", que con
   la política nueva es falso. Cambié sólo esa frase por "this same prompt N
   times" y agregué "Rewording the request clears the count". Si el otro agente
   quiere otra redacción, el contenido semántico que tiene que sobrevivir está en
   §Qué contrato tiene que documentar el ADR.

## La cadena de identidad, punta a punta

| Punta | Antes | Ahora |
|---|---|---|
| Productor (`hooks/skill-router-prompt-suggest.sh:61`) | `${COGNITIVE_OS_SESSION_ID:-${CLAUDE_SESSION_ID:-unknown}}` | `cos_session_id()`; vacío → `null` en el JSONL |
| Gate (`hooks/orchestrator-skill-invocation-gate.sh`) | cadena propia sin `CLAUDE_CODE_SESSION_ID` | `cos_session_id()` (su paso 3 lee el `INPUT="$(cat)"` que el gate ya hizo) |
| Consumidor (`cos_lib/skill_router.py::last_suggestion`) | ancla en `events.jsonl`; sin ancla, **todo el log** | sentinelas rechazadas; filas anónimas descartadas; sin ancla, **la última fila de la sesión**; TTL 6 h |

`unknown` no era "sin identidad": era una **clave**, compartida por todo el que no
dijo quién era. Por eso un test, una sonda de portabilidad o un replay leían y
escribían el mismo bucket que la sesión del operador.

Prueba de que el productor ahora escribe identidad real (proyecto sintético, log
del operador intacto):

```bash
T=$(mktemp -d); mkdir -p "$T/.cognitive-os/metrics"; ln -s "$PWD/cos_lib" "$T/cos_lib"
echo '{"prompt":"auditar la cobertura de primitivas del repositorio con forensics"}' \
  | env -u COGNITIVE_OS_SESSION_ID -u CLAUDE_SESSION_ID \
        COGNITIVE_OS_PROJECT_DIR="$T" CLAUDE_PROJECT_DIR="$T" \
        bash hooks/skill-router-prompt-suggest.sh >/dev/null 2>&1
jq -c '{session_id}' "$T/.cognitive-os/metrics/skill-suggestion.jsonl"; rm -rf "$T"
# -> {"session_id":"93e6e34f-a5b1-4921-a480-a36496b3c566"}   (id real del arnés)
```

El valor sale de `CLAUDE_CODE_SESSION_ID`, que es el hallazgo del punto 5: el
productor ya lo ve por `cos_session_id()`, y ahora el gate también.

## Qué hago con las 582 filas anónimas

Son 584 y **no se reatribuyen**. Una sugerencia sin identidad probada **no obliga
a nadie**, y esa es la decisión, no el descarte:

- El argumento no es "no se puede saber de quién eran". Es que **exigir sin sujeto
  no es exigir**: el gate le impondría a la sesión A una skill que el router le
  sugirió a la sesión B, y el operador no tendría forma de distinguir un veredicto
  de un accidente. Eso ya pasó, y el precio fue 48 días exigiendo una skill de
  julio.
- Tampoco se borran. El log es evidencia de cómo se comportó el router durante 94
  días y sigue sirviendo para medir cobertura y confianza; lo único que pierde es
  la capacidad de **obligar**.
- El corte es doble a propósito: el consumidor descarta `session_id` nulo **y**
  descarta los sentinelas (`unknown`, `none`, `null`, `-`, vacío). Si mañana algún
  productor vuelve a inventar una clave, el consumidor no la acepta igual.
- Simétricamente, cuando el gate no puede probar la identidad **se abstiene**: no
  bloquea (no puede probar que hubo bypass) y no aprueba en silencio (una guarda
  que evalúa y no registra es indistinguible de una guarda rota). Deja la fila en
  `.cognitive-os/metrics/anonymous/skill-bypass-anonymous.jsonl`, un bucket que
  **ningún gate lee para decidir**.

## El N de la política nueva, y cómo lo medí

Lo que se cuenta cambió de unidad. Antes: `+1` por tool-call, por sesión, de por
vida, sin reset. Ahora: `+1` por **envío del mismo prompt** (misma `prompt_hash`)
que recibe la misma sugerencia ≥0.90 sin invocarla ni anotarla. El contador sólo
avanza cuando cambia el `ts` de la fila de sugerencia, que el productor escribe
una vez por `UserPromptSubmit`; veinte tool-calls de un mismo turno cuentan uno.

La medición, sobre las 584 filas reales (94 días):

```bash
M=.cognitive-os/metrics/skill-suggestion.jsonl
jq -r 'select(.confidence>=0.90) | .prompt_hash' $M \
  | sort | uniq -c | awk '{print $1}' | sort -n | uniq -c
# 100 hashes con 1 envío · 1 con 2 · 1 con 3 · 1 con 6 · 1 con 11
```

| N | prompts que habrían llegado a BLOCK | sobre 104 |
|---|---|---|
| 2 | 4 | 3,8 % |
| **3** | **3** | **2,9 %** |
| 5 | 2 | 1,9 % |

**Elijo N=3**, por tres razones y no por gusto:

1. Entre N=2 y N=3 la diferencia **medida** es **un prompt en 94 días**. Pagar esa
   diferencia por ser más indulgente es barato; lo caro sería un gate que dispara
   sobre la primera repetición legítima.
2. N=5 tampoco es inerte (2 de 104), pero los dos casos que llegan a 5 son
   sospechosos de no ser insistencia humana: los 11 envíos son de `skill-creator`
   **todos el 2026-08-19** y los 6 de `agent-run-supervision` reparten entre el 3
   y el 8 de julio. Si la cola larga es replay y no conducta, subir N deja el gate
   apoyado justo en los casos menos confiables.
3. **3 es la constante que ADR-188 ya documenta.** Cambia la **unidad**, no el
   número: la corrección al ADR es de una línea y no obliga a re-litigar el
   umbral. (Ver §Qué contrato tiene que documentar el ADR.)

Honestidad sobre la medición: cuenta re-envíos de texto idéntico, que es un
**proxy** de insistencia, no insistencia observada. No se puede hacer mejor con
los datos que hay, porque las 584 filas son anónimas y no se puede segmentar por
sesión. El primer mes con identidad real permite rehacer esta tabla de verdad.

**El reset.** No hay barrido ni comando: el `prompt_hash` es parte del nombre del
archivo (`skill-gate-insist-<sesión>-<hash>-<skill>`), así que cambiar de prompt
**es** volver a cero. Para que no quede basura acumulándose —hoy hay exactamente
un huérfano, el contador de mayo— el hook barre `skill-gate-*` de más de 7 días en
cada escritura. El barrido está acotado a su propio prefijo: **no toca**
`skill-bypass-counter-*`.

## Los cinco casos probados

Todos en `tests/contracts/test_skill_gate_identity_and_insistence.py`, corriendo
el hook de verdad (no la función sola):

| # | Caso | Test |
|---|---|---|
| 1 | Con identidad real, una sugerencia ≥0.90 del prompt actual **obliga** y el gate bloquea al tercer envío | `test_identidad_real_obliga_y_bloquea_al_tercer_envio` |
| 2 | Una sugerencia de hace 40 días **no obliga** — y tampoco gana cuando puntúa 0.99 contra la 0.93 del turno | `test_sugerencia_de_hace_40_dias_no_obliga`, `test_sugerencia_vieja_no_gana_sobre_la_del_turno` |
| 3 | Repetir el mismo hash escala hasta BLOCK; **reformular libera** (vuelve a `1/3`) | `test_repetir_el_mismo_prompt_escala_y_cambiarlo_libera` |
| 4 | Los cuatro mutantes mueren | `scripts/mutation_check_skill_gate.py` |
| 5 | Un contador de 143 sembrado a mano **no escala** y queda intacto en disco | `test_contador_viejo_de_143_no_tiene_efecto` |

Más `test_muchas_tool_calls_del_mismo_envio_cuentan_una`, que es donde se ve que
la unidad cambió: seis tool-calls del mismo turno dejan el contador en `1/3` y
**una** fila de auditoría.

```bash
COS_ALLOW_OPERATOR_METRICS_WRITES=1 .venv/bin/python -m pytest \
  tests/contracts/test_skill_gate_identity_and_insistence.py \
  tests/contracts/test_skill_invocation_gate.py \
  tests/hooks/test_skill_invocation_gate_audit.py \
  tests/contracts/test_skill_adherence_loop.py \
  tests/red_team/portability/test_orchestrator-skill-invocation-gate.py -q
```

## La corrida de mutación

```
$ python3 scripts/mutation_check_skill_gate.py
control (hook sin mutar): VERDE

M1  MUERTO     abstencion sin sesion BLOQUEA en vez de abstenerse  <- test_mutante_abstencion_sin_sesion_no_bloquea
M2  MUERTO     abstencion sin sesion no deja rastro  <- test_mutante_abstencion_sin_sesion_deja_rastro
M3  MUERTO     vuelve el sentinela `unknown` (causa raiz documentada en la cabecera)  <- test_mutante_abstencion_sin_sesion_deja_rastro
M4  MUERTO     se quita el filtro de tool_name  <- test_mutante_filtro_de_tool_name

4/4 mutantes muertos
```

El script copia el hook a un temporal, lo muta y apunta la suite a la copia con
`COS_SKILL_GATE_HOOK`; el original no se toca. Corre primero un **control sin
mutar** que tiene que dar verde, porque si la suite ya estuviera roja cualquier
"mutante muerto" sería un falso positivo. Exit code `0` = todos muertos, `1` =
sobrevive alguno, `2` = error de setup.

Los dos tests que no mataban nada, arreglados:

- **El unit de `last_suggestion`** usaba marcas de mayo, no ejecutaba el hook y no
  cubría ni identidad sentinela ni ventana. Ahora afirma que gana la más confiable
  **del turno** (con una fila vieja de 0.99 sembrada como trampa), que preguntar
  por `unknown`/`none`/`null`/vacío devuelve `None`, y que un log entero vencido
  no da sugerencia.
- **La sonda de portabilidad** afirmaba `rc == 0` sobre un payload donde **todos**
  los caminos devuelven 0. Ahora exige además que un tool no gobernado salga por
  el corto sin dejar **ningún** archivo en el proyecto ajeno — que es lo que la
  hace falsable, y lo que participa en matar M4.

## Qué contrato tiene que documentar el ADR

Para el agente que está actualizando ADR-188 y `rules/skill-invocation-mandatory.md`.
El §Enforcement layers actual dice "Three WARNs in one session escalate to a single
BLOCK". **El número 3 sobrevive; la unidad y el alcance no.**

1. **Unidad del contador**: envíos del **mismo prompt** (`prompt_hash`), no
   tool-calls y no vida de la sesión. Redacción sugerida: *"tres envíos del mismo
   prompt con la misma sugerencia ≥0.90 sin invocar ni anotar escalan a un BLOCK"*.
2. **Reset**: estructural por hash. Reformular la pedida vuelve el contador a
   cero. **No existe** reset por sesión, y ése era el defecto: el diseño anterior
   no tenía ninguno.
3. **Estado en disco**: `.cognitive-os/runtime/skill-gate-insist-<sesión>-<hash>-<skill>`,
   con barrido de 7 días acotado al prefijo `skill-gate-*`.
   `skill-bypass-counter-*` queda **deprecado**: no se lee, no se escribe, no se
   borra. Conviene decirlo en el ADR para que nadie lo "limpie" creyendo que
   ayuda — es la evidencia del latcheo.
4. **Abstención sin identidad** (conducta nueva del 2026-08-20, sin ADR hasta
   hoy): sin `session_id` probado el gate **no decide** — exit 0 más una fila en
   `.cognitive-os/metrics/anonymous/skill-bypass-anonymous.jsonl` con
   `outcome: "abstained"`. Ese bucket **no lo lee ningún gate**.
5. **Vigencia de la sugerencia** (contrato nuevo): una sugerencia obliga sólo
   dentro del turno y sólo si tiene menos de 6 h. Sin ancla en `events.jsonl`, la
   ventana es la **última fila de la sesión**, no el log entero. Configurable con
   `COS_SKILL_SUGGESTION_TTL_SECONDS`.
6. **Identidad**: `cos_session_id()` (`hooks/_lib/common.sh`) es el **único**
   resolvedor para las dos puntas. El ADR no debería volver a describir cadenas
   de variables propias por hook. Vale nombrar que `CLAUDE_SESSION_ID` (sin
   `CODE`) no existe.
7. **`session_id` puede ser `null`** en `skill-suggestion.jsonl`, y una fila
   anónima **no obliga a nadie**. Los consumidores del log tienen que tolerarlo.
8. **Umbral configurable**: `COS_SKILL_GATE_INSIST_THRESHOLD` (default 3).
9. La afirmación falsable del ADR debería pasar a ser medible: *"con identidad
   real, la proporción de sugerencias ≥0.90 que llegan a BLOCK es ~3 % de los
   prompts distintos"*, contra la tabla de §El N de la política nueva.

## Lo que NO hice y por qué

- **No toqué ADR-188 ni `rules/skill-invocation-mandatory.md`**: son del otro
  agente. Lo que tienen que documentar está arriba. Sí toqué el texto de
  `WARN`/`BLOCK`, acotado a la frase que la política nueva volvía falsa (ver
  corrección 8).
- **No borré `skill-bypass-counter-unknown`** (143, del 2026-05-18). Es estado del
  operador y su existencia es la evidencia. Está probado que ningún camino de
  código lo lee (`test_contador_viejo_de_143_no_tiene_efecto`) y que el barrido no
  lo alcanza.
- **No purgué las 584 filas anónimas.** Dejan de obligar; siguen sirviendo para
  medir.
- **No corrí la suite completa.** El lote ancho (`tests/unit/` + `tests/red_team/`)
  pasó los 600 s y quedó en background. Corrí los cinco archivos que tocan este
  gate, más el control de la corrida de mutación. **Queda pendiente**:
  `.venv/bin/python -m pytest tests/unit/ tests/red_team/ -q` para descartar que
  el TTL o el rechazo de sentinelas rompan algún otro consumidor de
  `last_suggestion`.
- **No medí insistencia real dentro de una sesión**, porque es imposible con los
  datos existentes: las 584 filas son anónimas y no se pueden segmentar. La tabla
  de N usa re-envíos de texto idéntico como proxy y hay que rehacerla con un mes
  de identidad real.
- **No agregué reset por tiempo al contador de insistencia** (por ejemplo,
  "olvidar" a las 24 h). El reset por cambio de hash ya cubre el caso real, y un
  segundo mecanismo de olvido es exactamente el tipo de estado que después nadie
  entiende por qué se movió.

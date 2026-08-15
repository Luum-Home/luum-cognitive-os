# Síntesis — orquestación de agentes con múltiples modelos: lo que construimos contra lo que existe

- Fecha: 2026-08-15
- Insumos: `juez-interno-orquestacion-2026-08-15.md` (midió este repo) y
  `juez-externo-orquestacion-multimodelo-2026-08-15.md` (midió el estado del arte).
  Se produjeron sin verse.
- Alcance: cruce. No construí nada, no toqué `hooks/`, `rules/` ni ningún manifiesto.
  No recomiendo adoptar nada de terceros.

---

## 0. La pregunta del operador, contestada primero

> *"La orquestación de agentes con distintos modelos por fuera de Claude, para que
> todos los arneses se comporten de forma parecida — salvo que me digas que cada
> arnés ya eso lo resuelve."*

La pregunta tiene dos mitades y el ecosistema las trata al revés de como se las suele
juntar:

- **Correr agentes con modelos distintos**: sí, cada arnés ya lo resuelve, y hasta lo
  regala. opencode expone 75+ proveedores por configuración; Cursor documenta tres
  vendors distintos en un mismo archivo de subagente. Esa mitad está commoditizada.
- **Que se comporten de forma parecida**: no lo resuelve ninguno. Cero de siete arneses
  verificados define un contrato de salida.

Y de esas dos mitades, **nosotros construimos la que está resuelta y no construimos la
que no lo está** — construimos 1069 líneas de cascada multi-proveedor que nunca
corrieron, y cero líneas de contrato de comparabilidad.

---

## 1. Dónde coinciden — y por qué eso es lo más firme que hay acá

### 1.1 No existe contrato de comparabilidad, ni afuera ni acá (firme, con una asimetría)

Los dos informes, midiendo con instrumentos que no se parecen en nada —uno leyó doc
oficial y APIs de GitHub, el otro leyó ledgers de telemetría de este checkout—, llegan
al mismo lugar: la tríada *mismo formato / mismas garantías / misma forma de fallar* no
está escrita en ningún lado.

- **Afuera** (externo §3): la columna "resuelve" está vacía en las siete filas
  verificadas. Claude Code devuelve *"only the summary"*, Codex recomienda
  *"return summaries"* como consejo de prompt, opencode y Gemini CLI no dicen nada.
- **Acá** (interno §1–§4): el censo del dominio devuelve una cascada de proveedores, un
  contador de slots y un asesor de modelo. Ningún schema, ningún validador, ninguna
  forma de fallar definida.

**La asimetría que hay que marcar, porque cambia cuánto pesa el acuerdo:** las dos
mitades no son evidencia del mismo tipo. La del externo es **evidencia positiva** —el
pedido de contrato en Claude Code existe y fue cerrado `not_planned`, la propuesta de
extender AGENTS.md a subagentes lleva seis meses abierta con cero comentarios—, o sea,
alguien pidió el contrato y el ecosistema decidió no darlo. La del interno es
**ausencia**: buscó y no encontró. Un acuerdo entre "positivo" y "ausente" es firme
sobre el afuera y meramente no refutado sobre el adentro.

Lo cerré por mi cuenta, porque era el punto donde el acuerdo podía ser un artefacto del
censo del interno (que enumeró por `dispatch|provider|routing|orchestr|harness|driver|adapter`
y podía haberse perdido un contrato con otro nombre). Busqué por concepto, no por nombre:

```bash
git grep -l -i 'result contract|structured output|output schema|output_schema' -- '*.md' '*.py' ':!docs/' ':!.cognitive-os/'
git grep -l 'json_schema|jsonschema|validate.*agent.*output' -- 'cos_lib/*.py' 'lib/*.py' 'hooks/*'
```

Lo más cercano que aparece es `rules/model-compatibility.md`, y **no es un contrato de
comparabilidad: es su opuesto arquitectónico.** Es un checklist unilateral de
prerrequisitos del modelo anfitrión (¿sigue instrucciones multi-paso?, ¿parsea YAML?,
¿tiene 200K de contexto?) con baseline declarado en un único modelo de Anthropic
(`claude-opus-4-6`). Define qué tiene que *saber hacer* un modelo para reemplazar al
nuestro, no qué tiene que *devolver* cualquier modelo para ser comparable con otro.
Además no tiene ledger y su comando de verificación no está registrado en ningún evento:

```bash
ls .cognitive-os/metrics/ | grep -i compat        # (vacío)
git grep -c 'cognitive-os-compat-test' -- .claude/settings.json   # no registrado
```

Con eso, la ausencia del lado interno queda cerrada por búsqueda conceptual y no solo
por censo léxico. **El acuerdo se sostiene.**

### 1.2 Lo caro que construimos es lo barato de afuera

Segundo acuerdo, también desde extremos opuestos:

- Externo: la columna "permite" está *commoditizada* — opencode la resuelve con un
  string `provider/model-id` en un JSON.
- Interno: nuestro equivalente son 1069 líneas, siete adaptadores de proveedor, y
  **cero ejecuciones**. `.cognitive-os/metrics/llm-dispatch.jsonl` no existe pese a que
  los tres caminos de retorno de `dispatch()` emiten métrica (reproducido: el archivo
  sigue ausente hoy).

Ninguno de los dos podía ver esta frase solo. Es del cruce.

---

## 2. Dónde se contradicen — y cuál tiene razón

### 2.1 La contradicción que importa: ¿la cascada multi-proveedor es reinvención?

**El interno dice que no** (§6, y lo argumenta bien, aplicando la norma de la casa
sobre el verde barato):

> *El tool `Agent` de Claude Code elige entre modelos **de Anthropic**;
> `cos_lib/dispatch.py` elige entre **proveedores distintos**. Son conceptos distintos y
> la coincidencia de nombre es eso, coincidencia.*

**El externo dice que sí, sin saber que lo está diciendo** (§3): opencode
*"uses the AI SDK and Models.dev to support 75+ LLM providers"* más locales vía Ollama /
llama.cpp / LM Studio, todo **[DOC]**, todo por configuración. Cursor documenta
`composer-2`, `gpt-5.6-sol` y `claude-opus-5` en un mismo archivo de subagente.

No promedio. Voy al dato: **miden objetos distintos y los dos tienen razón sobre el
suyo.**

- El interno midió contra **el arnés donde corre este repo**. Ahí tiene razón entera:
  Claude Code no rutea fuera de Anthropic, y el externo lo confirma independientemente
  (*"the same values as the `--model` flag"*, doc que solo nombra modelos Claude).
- El externo midió contra **el ecosistema de arneses**. Ahí tiene razón entera: la
  capacidad existe, publicada, en al menos dos arneses.

**Cuál gana para esta decisión: el externo.** No porque mida mejor, sino porque *la
pregunta del operador es explícitamente multi-arnés* — "para que todos los arneses se
comporten de forma parecida". Un veredicto de reinvención medido contra un solo arnés
contesta una pregunta que nadie hizo. El interno generalizó de un afuera a *el* afuera,
que es el riesgo real de cruzar el borde de dominio (no el que anticipaba el encargo,
ver §5).

**Veredicto:** `cos_lib/dispatch.py` + `packages/llm-providers/` **no** reinventan una
feature de Claude Code, y **sí** reinventan una feature de opencode. Como la pregunta
es multi-arnés, cuenta como reinvención.

Matiz que no invalida el veredicto pero hay que decirlo: opencode resuelve la
*selección* de proveedor, no la *cascada con reintentos, budget gate y preservación de
cuota* que arma `dispatch.py`. Esa envoltura es genuinamente más que lo que da opencode.
Solo que nunca corrió, así que el mérito arquitectónico no está en disputa: no hay nada
que preservar operativamente.

### 2.2 La contradicción con el propio dato: una cifra del interno es falsa

El interno (§2.7) publica que `hooks/orchestrator-claim-gate.sh` tuvo *"735 corridas,
**735 con `findings: []`**"*, y de ahí concluye que es un gate que corre y **nunca
decide distinto**.

Corrí el comando que el propio informe cita:

```bash
python3 -c "
import json,collections;c=collections.Counter()
[c.update([(json.loads(l)['ok'], len(json.loads(l)['findings']))]) for l in open('.cognitive-os/metrics/orchestrator-claim-gate.jsonl') if l.strip()]
print(c)"
# Counter({(True, 0): 670, (True, 1): 67, (False, 22): 2, (False, 1): 1, (False, 36): 1, (False, 23): 1})
```

**72 filas con hallazgos, y cinco bloqueos reales** (`ok: False`). Y no es deriva del
ledger por lo que pasó hoy después de que el juez midiera: la primera fila con hallazgos
es del **2026-05-18**, y hay bloqueos del **2026-06-12** y del **2026-07-10**, semanas
antes de esta sesión.

```bash
# primera fila con findings: 2026-05-18T16:54:41Z
# bloqueos: 2026-06-12 (pre-push), 2026-07-10 (pre-commit, 36 hallazgos), 3 de hoy 15:39
```

El comando publicado es correcto; el número publicado no es lo que ese comando devuelve.
La explicación más probable es que se transcribió el bucket dominante de un `Counter` en
vez del `Counter` entero. **Esto invierte el veredicto de §2.7**: el claim-gate no es un
control que nunca ejerció — es, medido, **el único del lote que corre y decide**, con
cinco prevenciones sobre entrada real.

No cambia mi recomendación (el claim-gate no es orquestación de modelos), pero sí obliga
a corregir la lectura del interno en el único punto donde declaró muerto algo que está
vivo. Y es exactamente el patrón que el gate del propio repo existe para atrapar.

### 2.3 Contradicción menor: `--providers` por defecto

El interno declara falso el brief (§5.1): *"son cinco proveedores, no dos"*, citando
`scripts/orchestrator.py:386` (`default="qwen,openrouter,gemini,ollama,claude"`).
Verificado, esa línea dice eso. Pero doce líneas antes del sitio de uso:

```bash
sed -n '311p' scripts/orchestrator.py
#     providers_raw = getattr(args, "providers", None) or "qwen,claude"
```

El default de argparse es de cinco; el fallback del camino programático es de dos. El
brief y el juez interno describen **caminos de invocación distintos**, y ninguno de los
dos es simplemente correcto. Es indecidible por telemetría porque `dispatch()` nunca
corrió. Queda como bug de documentación, no como refutación.

---

## 3. Dónde cada uno se metió en el terreno del otro

El encargo pedía marcarlo. Pasó dos veces, con distinto resultado:

| Quién | Qué afirmó fuera de su dominio | Veredicto |
|---|---|---|
| **Interno** (§6) | "El tool `Agent` de Claude Code elige entre modelos de Anthropic" | **Correcto**, y el externo lo corrobora con [DOC]. Pero es la premisa de la que generalizó mal (§2.1): un arnés no es el ecosistema. |
| **Externo** (§1 corolario, §4) | "Si el proyecto construyó una capa de comparabilidad […] no está reinventando"; y trata a `@ai-sdk/harness` como *"competidor externo a esa capa"* | **Condicional bien hedgeado, pero el antecedente es falso.** No construimos esa capa. Leído rápido, el corolario se lee como hallazgo y el "competidor" implica que hay algo nuestro compitiendo. No hay. |

El segundo caso es el más peligroso de los dos para la lectura del operador, porque
afirma que estamos en una carrera en la que no estamos inscriptos.

---

## 4. Las cifras: qué reproduje

De las cifras del interno verifiqué doce. Once reproducen (tres con deriva monótona del
ledger, que es crecimiento normal, no discrepancia), una es falsa.

| Cifra | Publicado | Reproducido hoy | Estado |
|---|---|---|---|
| `llm-dispatch.jsonl` | ausente | ausente | ✅ |
| filas de `dispatch-gate.jsonl` | 182 | 184 | ✅ deriva |
| decisiones del gate | 143, todas `allow` | 145, todas `allow` | ✅ deriva |
| `agent-quota-redirect` en settings | 0 | 0 | ✅ |
| `dispatch-gate` en settings | 1 | 1 | ✅ |
| drivers invocados en `derive.go` | 2 | 2 (claude-code, codex) | ✅ |
| `.ai/adapters/` | 27 | 27 | ✅ |
| primitivas del dominio `core`+`runtime_projection` | 1 de 20 | 1 de 20 (`hooks/_lib/dispatch_gate_check.py`, `candidate`) | ✅ |
| contradicción entre los dos manifiestos | lab/False vs default-core | idéntico | ✅ |
| ledger del gate sin campo de modelo | sin campos de modelo | dos esquemas, ninguno con campo de modelo | ✅ |
| `orchestrator.py` default 5 proveedores | línea 386 | línea 386 confirmada, línea 311 la contradice | ⚠️ incompleta |
| claim-gate: 735 corridas, 0 hallazgos | 735/735 limpio | 742 filas, **72 con hallazgos, 5 bloqueos** | ❌ **falsa** |

Del externo verifiqué las tres anclas de las que cuelga su veredicto, con los comandos
que el propio informe publica:

```bash
curl -s https://api.github.com/repos/anthropics/claude-code/issues/20625   # closed / not_planned / 2026-02-28  ✅
curl -s https://api.github.com/repos/agentsmd/agents.md/issues/149         # open / 0 comentarios / 2026-02-08  ✅
curl -sL .../vercel/ai/main/packages/harness/README.md | grep -c 'HarnessCapabilityUnsupportedError'  # 1  ✅
```

Las tres reproducen exacto. **El informe externo no tiene una sola cifra caída en mi
muestra.**

Un detalle de método: el comando de esquemas del ledger que publica el interno (§2.3)
**crasheó** al correrlo hoy — una fila nueva trae un carácter de control y `json.loads`
levanta. Lo reescribí con `try/except` para poder verificar la afirmación (que se
sostiene). Un comando de evidencia que se rompe con una fila corrupta no es reproducible
en el sentido de la norma de la casa; el del interno para el claim-gate tiene el mismo
defecto.

---

## 5. La matriz: por qué no entra en una celda, y el encuadre que propongo

**Refuto la matriz como se planteó — no en su forma, en su singular.** Pide ubicar
"el caso" en una celda, y el hallazgo central del informe interno es que *no hay un caso*:
hay dos cosas distintas con el mismo nombre. Mi cruce encuentra tres. Forzar una celda
única obliga a una de dos barbaridades: tirar lo único que funciona, o conservar 1069
líneas muertas.

La matriz sigue siendo la herramienta correcta. Se aplica **por eje**, no al lote.

### Eje A — elegir modelo/proveedor por agente

| | |
|---|---|
| **El ecosistema lo resuelve** | Sí, commoditizado. opencode 75+ proveedores **[DOC]**; Cursor tres vendors por subagente **[DOC]**; los siete arneses permiten. |
| **Nosotros lo construimos** | Sí. `cos_lib/dispatch.py` (1069 líneas) + 7 adaptadores + `dispatch_model_advisor.py`. |
| **Celda** | **Reinvención — sacarlo.** |

Defensa: el externo prueba que existe publicado y por configuración; el interno prueba
que lo nuestro **nunca decidió una sola vez** (`llm-dispatch.jsonl` ausente con emisión
en los tres caminos de retorno), sin credenciales para ninguno de los tres proveedores
habilitados, y con `distribution: maintainer/lab` + `runtime_projection: false` — o sea
que ni siquiera llega a un consumidor. Es reinvención sin usuario y sin uso.

Agregado mío, que ninguno de los dos vio: **este repo tampoco usa la feature nativa que
el externo documenta.** `.claude/agents/` tiene cero agentes activos y dos archivados
—ambos con `model: sonnet` en el frontmatter, o sea que se usó y se retiró.

```bash
ls .claude/agents/*.md            # sin coincidencias
ls .claude/agents/_archived/      # service-health-checker.md, stack-validator.md (model: sonnet)
```

La superficie entera de "orquestar con modelos distintos" está sin ejercer en los dos
niveles a la vez: ni por el arnés, ni por lo nuestro.

### Eje B — comparabilidad de salida entre modelos distintos

| | |
|---|---|
| **El ecosistema lo resuelve** | **No.** 0 de 7 arneses. Pedido cerrado `not_planned` en Claude Code (#20625, verificado). Propuesta de extender AGENTS.md a subagentes: abierta desde 2026-02-08, **cero comentarios** (verificado). Lo único que lo escribe es de terceros, experimental, mergeado hoy, y normaliza **entre arneses**, no entre modelos. |
| **Nosotros lo construimos** | **No.** Ni schema, ni validador, ni forma de fallar definida (§1.1, verificado por búsqueda conceptual). |
| **Celda** | **Hueco real, abierto.** |

Es la celda barata: no hay nada que sacar y nada que mantener. Es también donde estaría
el trabajo de mañana, si es que hay.

### Eje C — proyectar el mismo gobierno a varios arneses

| | |
|---|---|
| **El ecosistema lo resuelve** | Solo para **instrucciones**: AGENTS.md, 26+ herramientas, bajo la AAIF. Explícitamente **no** para orquestación ni runtime — la propia propuesta #184 excluye la lógica de runtime de su alcance. Nada publicado proyecta *hooks y gates* al archivo de settings de cada arnés. |
| **Nosotros lo construimos** | Sí, y **corre**: `settings-driver-claude-code.sh` y `settings-driver-codex.sh` invocados desde `derive.go`, con salida real en `.codex/` y `.opencode/`. |
| **Celda** | **Hueco real, cubierto.** |

Es lo único del lote que está en la celda buena. Defensa honesta de su límite: es mi
ubicación más débil de las tres, porque **ningún informe midió este eje de frente** —el
externo relevó arneses y specs de agente, no proyectores de hooks. Que no aparezca en su
barrido es indicio, no prueba, de que no exista afuera.

Y ojo con el tamaño: son **dos** drivers, no cuatro (opencode sin llamador en
`derive.go`, bare `pending` en su plan — reproducido). Lo que está cubierto es más chico
de lo que el nombre sugiere.

---

## 6. La recomendación, en una frase

> **Retirá la cascada multi-proveedor (`cos_lib/dispatch.py` + `packages/llm-providers/`)
> o marcala explícitamente como congelada con fecha y motivo, conservá los dos
> settings-drivers, y no escribas la capa de comparabilidad hasta medir con los ledgers
> locales cuánto costó no tenerla.**

### El costo de cada camino

| Camino | Costo | Riesgo |
|---|---|---|
| **Retirar la cascada** | Operativo medible: **cero**. 0 dispatches, 0 credenciales, 0 consumidores (`maintainer`/`lab`, `runtime_projection: false`). Se van también `tests/unit/test_dispatch_*.py`. | Si mañana se decide cablearla, hay que reescribirla. Reversible por git — el costo real es el de volver a decidir, no el de volver a tener el código. |
| **Congelarla con motivo escrito** | Cero hoy. | Recurrente: ya consumió dos jueces y esta síntesis, y va a volver a aparecer en cada auditoría. Sigue alimentando cifras falsas — `rules/RULES-COMPACT.md:19` promete métricas a un archivo que no existe. Barato en tokens, caro en credibilidad. Solo sirve si el motivo escrito dice **qué evento la reactivaría**. |
| **Cablearla** (registrar `agent-quota-redirect`, cargar llaves) | Llaves de tres proveedores, un hook nuevo en settings, y asumir mantenimiento de lo que opencode da por config. | Es el único camino que produce el dato que falta: si sirve. Pero mantener una cascada propia en el arnés que no la necesita, cuando el arnés que sí la tiene la regala, es la definición del eje A. |
| **Construir comparabilidad (eje B)** | El más caro de todos. Diseño, schema, validador, adaptador por proveedor. | Sin evidencia de daño: nadie mostró un incidente donde dos agentes de modelos distintos rompieran algo por formato. Construir contra un hueco confirmado pero no costeado. |
| **Mirar `@ai-sdk/harness`** | **No es mi recomendación.** Requeriría descongelar `manifests/external-tool-adoption-freeze.yaml` (`frozen: true` desde 2026-05-11, motivo IP), **y ésa es una decisión con gate propio**: revisión legal más firma del operador. Lo digo solo para cerrar la puerta explícitamente, no para abrirla. | — |

**Lo que sí conviene arreglar en cualquiera de los caminos**, porque cuesta poco y hoy
está produciendo error medible: la contradicción entre `.ai/primitives` (que dice
`rules/model-routing.md` = `lab`, no proyectable) y `manifests/primitive-install-boundary.yaml`
(que la lista en el perfil `default`, `core`). Los dos manifiestos que gobiernan qué
viaja al consumidor se contradicen sobre el mismo archivo, y cualquier cifra de cobertura
que se apoye en uno hereda el error. No lo toqué.

---

## 7. Qué queda sin contestar porque cada uno tenía media respuesta

1. **¿Cuánto cuesta no tener comparabilidad?** Es la pregunta que decide el eje B y
   ninguno la podía contestar: el externo probó que el hueco existe, el interno probó que
   no lo llenamos, **nadie mostró un solo daño**. El dato está acá y es barato: 145 filas
   de `dispatch-gate.jsonl` con la descripción de cada lanzamiento, más los ledgers de
   salida de agentes. Si en tres meses de operación no hay un incidente de formato entre
   modelos, el hueco es real y no importa.
2. **¿Un archivo de agente de Codex acepta `model_provider`?** El externo lo dejó abierto
   por presupuesto (§6.1). Decide si el eje A está commoditizado también en el segundo
   arnés al que sí proyectamos. Se cierra leyendo el parser de config de rol en el repo
   oficial de Codex.
3. **¿Qué manifiesto gana cuando se instala?** El interno encontró la contradicción, el
   externo no tiene visión, y nadie corrió una instalación para ver cuál de los dos
   decide en la práctica. Es un experimento de un comando.
4. **¿Por qué se archivaron los dos agentes de `.claude/agents/`?** Ninguno de los dos lo
   vio siquiera. Si se retiraron porque la selección de modelo por agente no aportaba, ése
   es el dato más fuerte que existe contra los tres ejes a la vez, y está sin registrar.

---

## 8. Qué de este encargo era falso

1. **"Ubicá el caso en una celda"** — no hay un caso. Hay tres ejes que caen en tres
   celdas distintas (§5). El encargo invitaba a refutar la matriz y la matriz efectivamente
   necesita refutación en su singular, no en su forma.
2. **"esta sesión publicó 19 cifras de las que reprodujeron 4"** — ese prior no aplica a
   estos dos informes. En mi muestra: el externo reprodujo 3 de 3, el interno 11 de 12.
   Aplicarles la tasa de la sesión habría sido injusto, y —peor— me habría hecho descartar
   como "probablemente falsa" la cifra del claim-gate, que es la única realmente falsa y
   que solo se detecta corriendo el comando, no desconfiando en bloque.
3. **"el interno no puede opinar sobre lo que existe afuera"** — la advertencia es
   correcta pero el riesgo estaba mal identificado. El interno cruzó el borde una vez y
   **acertó** (Claude Code solo rutea a Anthropic; el externo lo confirma). El daño no
   vino de equivocarse sobre el afuera: vino de tener razón sobre **un** afuera y tratarlo
   como **el** afuera. El peligro de cruzar el borde no es el error de hecho, es el error
   de alcance.
4. **"la verificación cruzada solo vale cuando los dos miden distinto"** — se sostiene, y
   este par lo confirma: el hallazgo de §2.1 es imposible para cualquiera de los dos solo.
   Pero le falta una cláusula que este lote deja ver: **un acuerdo entre evidencia
   positiva y ausencia de evidencia es más débil que uno entre dos positivas**, y hay que
   decir cuál es cuál. El acuerdo más fuerte de este par (§1.1) es de ese tipo mixto, y
   por eso lo cerré con una búsqueda propia en vez de darlo por firme.
5. **"~50 tool calls"** — alcanzó de sobra: 22, de las cuales 9 fueron verificación de
   cifras. El presupuesto no fue la restricción; el criterio de qué verificar sí.

---

## 9. Comandos para rehacer esta síntesis

```bash
# lado interno
ls .cognitive-os/metrics/llm-dispatch.jsonl                      # ausente => 0 dispatches
wc -l < .cognitive-os/metrics/dispatch-gate.jsonl                # 184
grep -c 'agent-quota-redirect' .claude/settings.json             # 0
grep -n 'settings-driver' cmd/cos/internal/cli/derive.go         # 2 drivers
sed -n '311p;386p' scripts/orchestrator.py                       # los dos defaults en conflicto
ls .claude/agents/*.md 2>/dev/null | wc -l                       # 0 agentes activos
ls .claude/agents/_archived/                                     # 2 archivados, model: sonnet
ls .cognitive-os/metrics/ | grep -i compat                       # sin ledger de compat-test

# la cifra falsa del interno (con try/except, porque el comando original crashea)
python3 -c "
import json,collections;c=collections.Counter()
for l in open('.cognitive-os/metrics/orchestrator-claim-gate.jsonl'):
    l=l.strip()
    if not l: continue
    d=json.loads(l); c[(d['ok'],len(d['findings']))]+=1
print(c)"                                                        # 72 con hallazgos, 5 bloqueos

# lado externo (los tres anclajes del veredicto)
curl -s https://api.github.com/repos/anthropics/claude-code/issues/20625 \
  | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['state'],d['state_reason'],d['closed_at'])"
curl -s https://api.github.com/repos/agentsmd/agents.md/issues/149 \
  | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['state'],d['comments'],d['created_at'])"
curl -sL https://raw.githubusercontent.com/vercel/ai/main/packages/harness/README.md \
  | grep -c 'HarnessCapabilityUnsupportedError'
```

Todos read-only. Ningún archivo de `hooks/`, `rules/`, `manifests/` ni
`.cognitive-os/metrics/` fue modificado por esta síntesis.

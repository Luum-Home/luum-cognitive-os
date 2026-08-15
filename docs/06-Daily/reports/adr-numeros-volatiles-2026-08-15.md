# Números volátiles dentro de los ADRs

Fecha: 2026-08-15. Alcance: `docs/02-Decisions/adrs/`.
Continúa `docs/06-Daily/reports/numeros-volatiles-2026-08-15.md`, que construyó el
criterio, el detector y el ratchet y dejó los ADRs baselineados sin tocar.

Evidencia ejecutable: `scripts/volatile_number_audit.py`. Todo número de acá sale
del comando citado al lado.

---

## 1. El conteo, antes y después

```bash
python3 scripts/volatile_number_audit.py --classify-only --format json \
  | python3 -c "import sys,json;f=json.load(sys.stdin)['findings'];\
a=[x for x in f if '/adrs/' in x['path'] and x['verdict']=='volatile'];\
print(len(a), len([x for x in a if not x['path'].endswith('.synthesis.md')]))"
```

| | Antes | Después |
| --- | ---: | ---: |
| Hallazgos volátiles en `adrs/` | 76 | 34 |
| — en ADRs reales | 73 | 31 |
| — en `*.synthesis.md` | 3 | 3 |
| Total del repo | 324 | 281 |

El detector cierra en verde:

```bash
python3 scripts/volatile_number_audit.py
# findings: 2032  volatile=281 ...  new (unbaselined) volatile: 0   -> exit 0
```

Baseline regenerado midiendo, no a ojo: `--update-baseline` escribe el conjunto
volátil actual. Bajó de 324 a 281 entradas aceptadas. No se movió ninguna entrada
para tapar un hallazgo pendiente.

---

## 2. Observado vs decidido: el reparto de los 73

**42 eran observados y se arreglaron. 31 eran decididos, externos o ilustrativos
y se dejaron intactos.** O sea: el 42% del lote de ADRs era falso positivo contra
el criterio que el propio encargo fija. Ése es el hallazgo principal.

### Los 31 que se quedan, con el motivo caso por caso

| ADR | # | Por qué se queda |
| --- | ---: | --- |
| ADR-009 §Decision | 7 | La partición CORE (82) / PACKAGE (227) **es** la decisión: 9 skills, 24 hooks, 38 rules… es el reparto que el ADR fija, no un censo del día. Borrarlo destruye el ADR. |
| ADR-178 | 4 | «Cherry-pick **3** primitivas» ×3 es el alcance decidido; «OpenHarness soporta **4** tipos de hook» describe otro proyecto. |
| ADR-028 | 4 | «110 hook files» ya venía con su censo al lado (`count to be confirmed at audit time via ls hooks/*.sh \| wc -l`); «3–5 agentes», «10 agentes», «muestreo de 5» son diseño decidido. |
| ADR-010 | 2 | `~11 hooks` (minimal) y `~47 hooks` (paranoid) son el dimensionamiento de los perfiles que este ADR crea. |
| ADR-027 | 2 | `< 1 test file` y `≥ 1 test` son umbrales del contrato. |
| ADR-075 | 2 | Tier-2 `~8 rules` viene con la lista de las ocho enumerada abajo; «Tier-1 shrunk to 38 / 57 demoted» es el resultado decidido de un seguimiento. |
| ADR-262 | 2 | «una sesión con 20 turnos genera 20 stubs» es un ejemplo, no una medición. |
| ADR-012 | 1 | «Convert **4** hooks» con los cuatro nombrados en la misma línea. |
| ADR-026 | 1 | `~10 líneas` es una estimación de esfuerzo. |
| ADR-033 | 1 | «SLO **9**» es un identificador, no un conteo. |
| ADR-067 | 1 | «los **7** skills que se colaron» refiere a un incidente concreto y cerrado. |
| ADR-132 | 1 | «escala a 2 máquinas, 2–3 harnesses» es el envelope decidido. |
| ADR-215 | 1 | gitleaks trae `~200 rule packs`: es de terceros, ningún censo nuestro lo produce. |
| ADR-281 | 1 | «4 ADRs **at audit time of writing**» ya trae su propia ancla. |
| ADR-298 | 1 | «corpus de 10 skills × ~5 prompts» es el diseño del corpus. |

### Los dudosos, y cómo se resolvieron

Tres familias no caían solas:

1. **Registros de una corrida de tests** — `69 tests passing` (ADR-055b),
   `89 tests: 75 unit + 14 e2e` (ADR-071), `50 test cases` (ADR-041),
   `4 tests, all pass` (ADR-001). Un conteo de tests deriva sin que nadie edite
   el ADR, así que es observado; pero es también el registro de que la
   implementación cerró. **Salida: se les puso la fecha de la corrida.** No se
   borró ningún número.

2. **Tamaños de perfil de instalador** — `10 skills visible`, `9 skills
   installed` (ADR-093), `~29 hooks` del set standard. El perfil es decidido, su
   cardinalidad es observada. **Salida: fecha, sin tocar el perfil.**

3. **El número que sostiene un argumento** — «la brecha es de 108 skills y
   creciendo» (ADR-174), «162 skills, 116 hooks, 131 ADRs» (ADR-132). El
   argumento no depende del valor exacto, pero la frase sin número queda coja.
   **Salida: el argumento pasa a ser cualitativo y el número queda como
   observación fechada con su comando de censo.**

---

## 3. Qué se arregló

27 ADRs. El patrón, en todos: la afirmación queda cualitativa, el número queda
como observación fechada, y al lado va el comando que da el valor de hoy.

| ADR | Decía | Dice ahora |
| --- | --- | --- |
| 009 | `375 primitivas (72 skills, 55 rules…)` con la fecha en la línea de arriba | fecha y conteos en la misma línea (ver §5) |
| 010 | `from 4 events (13 hooks)` | `(13 hooks registered on 2026-03-28)` |
| 027 | `Grand total: 27 hook entries registered` | `Grand total on 2026-04-21` + `scripts/audit_gate_registration.py` |
| 027 | `duplicated across ≥ 7 skill manifests` | fecha + `grep -rl 'pytest tests/unit' skills/*/SKILL.md \| wc -l` |
| 028 | `Whether 110 hooks produce 10 findings` | `Whether the hook inventory scoped above produces…` |
| 028a | `309 test-e2e-{hex}/ directories accumulate` | fecha + `ls -d .cognitive-os/agent-bus/test-e2e-* \| wc -l` |
| 041 | `At 79.4% this means ~4 out of every 5…` | fecha + `python3 scripts/aspirational_audit.py` |
| 044 | `80 chars × 126 skills` | `126 skills (el catálogo al 2026-04-20; ls -d skills/*/ \| wc -l)` |
| 059 | `new user sees 23 skills + 67 hooks, not 137 + 155` | el `core/` que el ADR dimensiona vs. el árbol entero al 2026-04-24, con los dos censos |
| 059 | `Migration work: 114 skills + 88 hooks` | «todo lo que queda fuera de `core/`» + conteo fechado |
| 075 | `Expanding all 112 rules costs ~107K tokens` | «cada regla»; la tabla se declara medida el 2026-04-30 sobre 112 reglas |
| 075 | `Tier-1 (default, ~95 rules)` | «toda regla que no esté en Tier-0 ni Tier-2» + `grep -L 'TIER: [02]' rules/*.md \| wc -l` |
| 076 | `Scope: 142 SKILL.md files updated` | `…updated on 2026-04-30` |
| 081 | `As of the date of this ADR it registers 28 hooks` | `It registered 28 hooks on 2026-04-30` |
| 087 | `Promoting its 11 ADRs` | `Promoting its ADRs (11 of them on 2026-04-30)` |
| 093 ×3 | `~29 hooks` / `10 skills visible` / `9 skills installed` | los tres con fecha 2026-04-30 |
| 132 | `162 skills, 116 hooks, 131 ADRs` | `On 2026-05-03 the tree held…` + los tres censos |
| 174 ×3 | `103 skills unrouteable`, `~95 skills need migration`, `gap is 108 skills` | fecha 2026-05-05 + `scripts/dogfood_score.py` / `grep -L routing_patterns` |
| 238 | `passes (116 rules audited)` | `passes over the whole rules/ tree` + conteo fechado |
| 274 / 275 | `across 3 harnesses` | `manifests/harness-projection.yaml` (mismo patrón que `rules/session-close-doc-truth.md`) |
| 278 | `backfilling all 169 test calls` | «todo call site sin cubrir — 169 contados el 2026-05-12» |
| 285 | `under 50 ms for a full registry of 175 skills` | el presupuesto de 50 ms queda; `175 skills on 2026-05-13` se ancla |
| 290 / 293 | `the existing 237 hooks` | «los hooks que ya existen (237 al 2026-05-13, `ls hooks/*.sh \| wc -l`)» |
| 296 | `All 196 skills participate` | «cada skill del catálogo — 196 al 2026-05-13» |
| 299 | `~385 SKILL.md files will gain 12 lines` | «cada SKILL.md del árbol» + fecha + `find . -name SKILL.md -not -path './.git/*' \| wc -l` |

Ninguna frase quedó vaga: no hay «varios hooks» ni «muchas primitivas» en
ninguno de los 27.

Las ediciones se aplicaron con dos scripts idempotentes que abortan si el patrón
no aparece exactamente una vez, en
`scratchpad/fix_adr_volatiles{,2}.py` (proceso, no entregable — el resultado está
en los ADRs y en el diff).

**No se tocó**: `status`, `implementation_status`, `supersedes`, `superseded_by`,
ningún título, `hooks/**`, `docs/00-MOCs/`.

### Verificación

```bash
python3 scripts/generate_adr_index.py         # exit 0, sin diff en INDEX.md
python3 scripts/cos-adr-partial-ledger        # exit 0, sin diff en el ledger
.venv/bin/pytest tests/contracts/test_adr_status_taxonomy.py -q   # 14 passed
python3 scripts/audit_adr_status_links.py     # 3 findings, los mismos de antes
```

Los generados no se movieron porque las ediciones son de cuerpo, no de
frontmatter ni de la línea de decisión que INDEX.md extracta. Los 3 hallazgos de
`audit_adr_status_links.py` son preexistentes (aristas `supersedes` faltantes en
ADR-187/192 y afines) y no los toqué.

---

## 4. Títulos que se proponen cambiar

**Ninguno nuevo.** El único caso conocido —el `375 Agentic Primitives
Reclassified` de ADR-009— ya lo resolvió el orquestador en `af8afa47e`: el
frontmatter y el `#` dicen hoy *Package Architecture -- Agentic Primitive
Reclassification*, y el 375 vive en el cuerpo como observación fechada con el
censo al lado. Verificado antes de tocar el archivo, no reconstruido.

---

## 5. Estado de los `*.synthesis.md`

150 archivos (`ls docs/02-Decisions/adrs/*.synthesis.md | wc -l`). Tres cargan
números volátiles heredados de su fuente: `ADR-041.synthesis.md` (957
primitivas), `ADR-290.synthesis.md` y `ADR-296.synthesis.md` (237 hooks, 196
skills). Arreglé las tres fuentes; las síntesis siguen igual, como avisaba el
encargo.

**No hay generador que las regenere.** Buscados productores en `scripts/`,
`cos_lib/`, `lib/`, `skills/` y `tests/`: todo lo que aparece son consumidores o
validadores — `scripts/validate_okf.py` (valida el formato OKF),
`scripts/generate_adr_index.py`, `scripts/audit_adr_status_links.py`,
`cos_lib/context_injector.py`. Las páginas nacieron de una pasada de LLM
(`9cf6612e3` — *"150 UNVERIFIED Tier-1 ADR synthesis draft pages (pending
sdd-verify)"*) y su escritura está detrás de `COS_ALLOW_PROTECTED_CONFIG_WRITE=1`.

Conclusión: **no se pueden regenerar con un comando; hace falta re-sintetizar con
un agente.** No lo corrí — está fuera del alcance quirúrgico de este encargo y
tocaría 150 archivos con una pasada no determinista. Queda como decisión del
operador, con el dato de que las tres síntesis afectadas siguen siendo drafts
UNVERIFIED pendientes de `sdd-verify`.

---

## 6. Qué del encargo era falso

1. **«85 volátiles en ADRs» → son 76**, y de esos 73 en ADRs reales (3 viven en
   síntesis). Recontado con el comando del §1.

2. **«ADR-009 ya fue arreglado» → a medias.** El título sí (`af8afa47e`), pero
   quedaban 9 volátiles en el cuerpo. Dos eran un artefacto de wrapping —el ancla
   `As of 2026-03-28` estaba en la línea anterior a los conteos, y el detector
   evalúa **una línea física** (`DATE_RE.search(line)`, línea 230 del script)—.
   Los otros siete son la partición del §Decision y **deben quedarse**. O sea: el
   «peor ADR de la lista» era el que menos había que tocar.

3. **«los ADRs reales son 352» → correcto, pero el comando obvio da 351.**
   `ls docs/02-Decisions/adrs/ADR-*.md | grep -vc synthesis` → 351; hay un ADR
   real con «synthesis» en el nombre de archivo. El censo autoritativo es
   `python3 scripts/audit_adr_status_links.py`, que reporta *"3 finding(s) across
   352 ADRs"*. Corregí el comando que había puesto en ADR-132 para citar ése.

4. **La priorización por «43 ADRs con vía de propagación» no se pudo usar.**
   `scripts/audit_adr_path_reality.py` no acepta `--format json`; prioricé por
   densidad de volátiles medida con el detector, que era la señal disponible.

5. **El encargo asume que el lote es todo deuda.** No: 31 de 73 son contrato,
   externo o ilustrativo. Si el operador quisiera «cero números», el precio sería
   destruir el §Decision de ADR-009 y el alcance decidido de ADR-178. La frontera
   observado/decidido no es un matiz del encargo, es el 42% de su volumen.

---

## 7. Dos cosas del detector para el operador

1. **`DATE_RE` mira una sola línea física.** Un ancla de fecha en la línea
   anterior no cuenta, así que la prosa correcta da falso positivo — y al revés,
   arreglar el falso positivo obliga a alargar líneas. Me costó tres re-wraps
   propios (ADR-081, ADR-093, ADR-285). Arreglo posible: mirar una ventana de dos
   líneas. **No lo toqué**: el script es de otro agente y es el oráculo de este
   lote; cambiarlo mientras se mide con él es exactamente el verde barato.

2. **El baseline tiene claves duplicadas.** `manifests/volatile-number-baseline.json`
   guarda `accepted` como lista: 281 entradas, 255 únicas
   (`python3 -c "import json;d=json.load(open('manifests/volatile-number-baseline.json'))['accepted'];print(len(d),len(set(d)))"`).
   No es colchón —son duplicados exactos, no holgura— pero hace que el audit
   imprima `baselined: 255` contra un archivo de 281 y parezca un desfasaje.
   Deduplicar al escribir lo cierra.

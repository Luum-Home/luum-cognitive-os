# Inventario de adopciones externas — backfill 2026-08-15

**Alcance:** completar el inventario de adopciones externas para que la lista que
revise un abogado sea la lista que existe. Registro de hechos: qué repo, qué
licencia verificada contra el LICENSE crudo del upstream, qué archivos la tocan,
en qué fecha entró y **de qué forma**.

**Fuera de alcance, deliberadamente:** si una adopción es defendible, si cumple
clean-room, o si hay riesgo. Eso es lo que `unfreeze_requires` item 1 le manda a
un humano con matrícula. Ninguna entrada nueva emite ese juicio; todas llevan
`status: INVENTORIED-PENDING-REVIEW`, que significa "está en la lista con su
forma, sus archivos y su fecha; nadie evaluó su postura legal".

**No se tocó** `frozen`, `unfreeze_requires` ni `gated_path_globs` de
`manifests/external-tool-adoption-freeze.yaml`. Ningún archivo modificado matchea
un `gated_path_glob`.

---

## 1. Lo que se agregó: cuatro entradas, no dos

El encargo pedía dos (`aider`, `dspy`) y daba las otras dos por inventariadas.
**Las cuatro faltaban.**

| Repo | Licencia (verificada) | Forma de adopción | Aterrizó | Estaba en el inventario |
|---|---|---|---|---|
| `Aider-AI/aider` | **Apache-2.0** | `pattern-reimplementation` | 2026-05-10 | No |
| `stanfordnlp/dspy` | MIT — © 2023 Stanford Future Data Systems | `optional-probe` | 2026-05-10 | No |
| `HKUDS/LightRAG` | MIT — © 2025 LightRAG Team | `conceptual-reference` | 2026-05-08 | **No** (el encargo decía que sí) |
| `unclecode/crawl4ai` | Apache-2.0 + cláusula de atribución obligatoria | `declared-dependency` | 2026-03-28 | **Parcial** (solo `NOTICE` raíz, con la atribución incompleta) |

Comando que produce la fila "estaba en el inventario", corrido **antes** del backfill:

```bash
grep -ciE 'aider|dspy|lightrag|crawl4ai' manifests/external-tool-licenses.yaml
# -> 1   (y el único hit era la palabra "LightRAG" dentro de las notas de
#          MegaMemory: "ONNX embedder deferred to LightRAG slice" — una mención
#          a futuro de otro proyecto, no una entrada de éste)
grep -ciE 'aider|dspy|lightrag' NOTICE
# -> 0
```

### La forma, que es el dato que faltaba

El vocabulario nuevo (`adoption_form`) va de menor a mayor contacto con código
upstream. La distinción importa porque las cuatro adopciones no son la misma cosa
y el inventario anterior no permitía distinguirlas:

- **`conceptual-reference`** (LightRAG) — el único rastro en el código es un
  comentario: `cos_lib/memory_retrieval_benchmark.py:139`, textual:
  `# LightRAG-inspired dual-level local proxy: precise title/entity`.
- **`optional-probe`** (dspy) — `cos_lib/dspy_pilot.py` son 46 líneas y su único
  contacto con upstream es `importlib.util.find_spec("dspy") is not None`. Nunca
  lo importa. Lo que sí toma prestado es vocabulario: "signature" con
  inputs/outputs es término de arte de DSPy, acá un dict común.
- **`pattern-reimplementation`** (aider) — el docstring de `cos_lib/repo_map.py`
  (líneas 4-6) lo **declara**, textual:

  > "Pattern-port of Aider's repo-map idea: build a compact, token-budgeted map of
  > relevant repository files/symbols, then overlay COS governance context. This is
  > first-party code; no Aider runtime dependency is required."

- **`declared-dependency`** (crawl4ai) — la única que es dependencia de verdad:
  `requirements.txt:31` pinnea `crawl4ai>=0.8.0` y
  `packages/ecosystem-tools/lib/web_crawler.py` la importa en las líneas 23 y 179.

Ni aider ni dspy son dependencias, y no hay código upstream de ninguno de los
cuatro vendorizado en el repo:

```bash
grep -rnE '^\s*(import|from)\s+(aider|dspy)\b' --include='*.py' .   # 0 filas
grep -inE 'aider|dspy|lightrag' requirements.txt pyproject.toml     # 0 filas
```

### Una relación distinta que se registró aparte

`cos_lib/harness_adapter/aider.py` (registrado en
`cos_lib/compatibility_layer.py:97-98`) **parsea el formato de transcripción** de
aider (`.aider.chat.history.md`) para que COS pueda ingerir sesiones producidas
por la herramienta. Eso es interoperabilidad con un formato de salida, no
adopción de una idea ni de código. Quedó documentado en las notas de la entrada y
**deliberadamente fuera de `cos_files`**, para que un revisor vea las dos cosas y
pueda distinguirlas. `install.sh:25` además lista `aider` como harness soportado.

---

## 2. Veredicto sobre las entradas que ya existían

### crawl4ai — presente, pero la atribución incumplía el LICENSE

El `NOTICE` raíz sí tenía a Crawl4AI. Lo que decía era una paráfrasis:

> "This product includes software developed by UncleCode as part of the Crawl4AI project (Apache-2.0)."

El LICENSE upstream exige una oración **literal**, con dos URLs que la paráfrasis
dejó afuera. Verificado el 2026-08-15 vía
`https://raw.githubusercontent.com/unclecode/crawl4ai/main/LICENSE`:

> "This product includes software developed by UncleCode (https://x.com/unclecode) as part of the Crawl4AI project (https://github.com/unclecode/crawl4ai)."

Corregido en `NOTICE`. Además, crawl4ai no estaba en
`manifests/external-tool-licenses.yaml` ni en `NOTICE.md`; ahora sí.

### LightRAG — no estaba en ningún lado, y una afirmación vigente decía que sí

`manifests/external-tool-adoption-freeze.yaml` (líneas 79-81) afirma que LightRAG
está *"recorded in NOTICE.md and manifests/external-tool-licenses.yaml"*. **Las
dos mitades son falsas.** No estaba en ninguno de los dos, ni en el `NOTICE` raíz.
Es exactamente el defecto que el encargo anticipaba: una entrada del inventario
que miente es peor que una ausencia visible, porque deja de pedir atención.

No corregí esa línea del freeze manifest — es aditivo lo mío y el archivo tiene
peso de decisión de operador. Queda anotado acá y en las notas de la entrada
nueva de LightRAG.

---

## 3. El misterio de las "6 adopciones" — resuelto

**No son los cuatro repos de este lote. Nunca lo fueron.**

`freeze_reason` dice: *"The 6 external-pattern adoptions already in main
(ADR-260..264)"*. La fuente que el propio freeze cita es
`docs/06-Daily/reports/license-compliance-audit-2026-05-11.md`, y ahí está el
número, línea 22:

> `| **Adopted as patterns-only (clean-room, no source copied)** | **6 ADRs** (ADR-260..265 — all sourced from holaOS) |`

Con eso, tres cosas quedan establecidas:

1. **Las "6" son las adopciones clean-room de patrones de holaOS**, bajo ADR-259.
   No tienen relación con crawl4ai, LightRAG, aider ni dspy. La premisa del
   encargo —"ninguno de los ADR-260..264 cita un repo de este lote"— es correcta,
   pero la conclusión —"nadie sabe cuáles son esas 6"— no: la auditoría las
   enumera.
2. **El freeze manifest transcribió mal su propia fuente.** La auditoría dice
   `ADR-260..265` (6 ADRs); el freeze escribió `ADR-260..264` (5). El "6" del
   texto y el rango que lo acompaña nunca cerraron por eso.
3. **El 6 tampoco es correcto en la auditoría.** ADR-265 no es una adopción de
   holaOS, y no es una adopción en absoluto:

```bash
grep -ci holaos docs/02-Decisions/adrs/ADR-265-mandatory-minimum-inspection-caps.md
# -> 0    (cero menciones de holaOS en todo el ADR)
```

ADR-265 es sobre **iFixAi**, está en `status: proposed` con
`implementation_files: []`, y su propio texto dice que el mecanismo **no está
adoptado**: *"the mandatory-minimum cap mechanic is explicitly NOT in the COS
extractable-primitive list"*. La auditoría lo barrió con un rango inclusivo.

**Conclusión con evidencia:** las adopciones clean-room de holaOS verificables en
main son **cinco** — ADR-260, 261, 262, 263 y 264, cada una con
`**Implements:** ADR-259 (holaOS Adoption Posture — patterns only)` en su
encabezado. El "6" es un artefacto de un rango inclusivo mal cerrado, propagado
después con un rango distinto.

```bash
# las cinco que sí citan la postura holaOS. El filtro de synthesis es necesario:
# sin él la cuenta da 10, porque cada ADR tiene un .synthesis.md que repite la cita.
grep -l 'ADR-259 (holaOS Adoption Posture' docs/02-Decisions/adrs/ADR-26*.md \
  | grep -v '\.synthesis\.md$' | sort
# -> ADR-260, ADR-261, ADR-262, ADR-263, ADR-264  (5 archivos)
```

**Lo que esto significa para la revisión legal:** el conjunto que
`unfreeze_requires` item 1 manda a revisar (patrones holaOS) y el inventario de
`manifests/external-tool-licenses.yaml` (13 entradas ahora) son **dos conjuntos
distintos**. Las cuatro entradas agregadas hoy no estaban en ninguno de los dos.
Cuál de los dos —o la unión— es el alcance de la revisión, es decisión del
operador y del abogado, no de este inventario.

---

## 4. Qué del encargo era falso

| Premisa del encargo | Estado |
|---|---|
| aider ausente de NOTICE y del license manifest | **Verdadera** |
| dspy ausente de NOTICE y del license manifest | **Verdadera** |
| "crawl4ai — ¿en el inventario? **sí**" | **Falsa en parte.** Estaba solo en `NOTICE` raíz, ausente del license manifest y de `NOTICE.md`, y con la atribución incumpliendo la cláusula literal del LICENSE |
| "LightRAG — ¿en el inventario? **sí**" | **Falsa.** No estaba en ninguno de los tres archivos |
| "nadie sabe cuáles son esas 6" | **Falsa.** La auditoría de 2026-05-11 las enumera; lo que nadie había notado es que el número está mal en las dos puntas |
| dspy no figura en ningún manifiesto | **Falsa.** Figura en `manifests/feature-tool-due-diligence.yaml:23-26`. Es una fila de due-diligence, no de atribución: **no se duplicó**, se cerró el hueco del license manifest y se dejó anotada la referencia cruzada |
| Licencia de aider | **Apache-2.0, no MIT.** Nadie lo había afirmado, pero es el default que se asume en un repo donde 8 de 13 entradas son MIT |
| crawl4ai aterrizó 2026-03-27 | **2026-03-28** según `git log --follow --diff-filter=A -- packages/ecosystem-tools/lib/web_crawler.py` (commit `09bfed553`). Un día de diferencia; puede que `requirements.txt` sea del 27 — no lo aislé |

---

## 5. Lo que NO se verificó, marcado como tal

- **Si `cos_lib/repo_map.py` se parece al algoritmo de aider.** No comparé las dos
  implementaciones. La entrada registra que el docstring *declara* un pattern-port
  y que no hay código upstream presente; lleva un `NOT ASSESSED` explícito. Juzgar
  la independencia sustantiva es trabajo del revisor.
- **Línea de copyright de aider y de crawl4ai.** Ambos LICENSE son el cuerpo
  Apache-2.0 sin rellenar; la línea de copyright existe solo como plantilla en el
  apéndice. Registrado `MISSING` con el motivo, no inventado por simetría con las
  otras entradas.
- **Tests.** `tests/unit/test_cos_generate_notices.py` no se corrió: pytest no está
  instalado en el intérprete disponible (`python3 -m pytest` → *No module named
  pytest*). Lo que sí se verificó: el YAML parsea con `yaml.safe_load` y devuelve
  13 entradas, y el generador corrió limpio.
- **`codebase-memory-mcp` NO se agregó.** Hay otro agente diseñando esa adopción.
  Si corresponde inventariarla, es su entrega.

---

## 6. Efecto colateral de regenerar, declarado

`NOTICE.md` y `THIRD_PARTY_LICENSES.txt` son **auto-generados** desde
`manifests/external-tool-licenses.yaml` (cabecera: *"Do not edit manually"*). Se
regeneraron con `python3 scripts/cos-generate-notices.py`. La regeneración
arrastró dos cambios que no son míos y no se editaron a mano:

1. **Pyrefly** entró a `NOTICE.md`. Estaba en el YAML desde 2026-05-15 y el
   generado nunca se había vuelto a correr — el pie decía *"Generated ... on
   2026-05-11"*.
2. **Rutas `lib/` → `cos_lib/`** en las entradas viejas (Hermes, OpenHarness, Pi,
   Sprut). El YAML ya decía `cos_lib/`; el `NOTICE.md` publicado seguía diciendo
   `lib/`.

O sea: el `NOTICE.md` que un revisor hubiera leído hasta hoy estaba tres meses
desactualizado respecto de su propia fuente.

---

## Comandos de verificación

```bash
# 13 entradas, con forma declarada en las cuatro nuevas
python3 -c "
import yaml
d = yaml.safe_load(open('manifests/external-tool-licenses.yaml'))
for x in d['entries']:
    print(x['name'], '|', x['spdx'], '|', x['status'], '|', x.get('adoption_form', '(sin forma)'))
"

# los generados están al día respecto del YAML: correr DESPUÉS del commit,
# la salida tiene que ser vacía (si imprime algo, el generado quedó atrasado)
python3 scripts/cos-generate-notices.py && git status --porcelain NOTICE.md THIRD_PARTY_LICENSES.txt

# licencias upstream (las cuatro, crudas)
for u in \
  https://raw.githubusercontent.com/Aider-AI/aider/main/LICENSE.txt \
  https://raw.githubusercontent.com/stanfordnlp/dspy/main/LICENSE \
  https://raw.githubusercontent.com/HKUDS/LightRAG/main/LICENSE \
  https://raw.githubusercontent.com/unclecode/crawl4ai/main/LICENSE ; do
  echo "== $u"; curl -sS "$u" | head -5
done

# el conteo de las adopciones holaOS
grep -l 'ADR-259 (holaOS Adoption Posture' docs/02-Decisions/adrs/ADR-26*.md | wc -l   # -> 5
grep -ci holaos docs/02-Decisions/adrs/ADR-265-mandatory-minimum-inspection-caps.md    # -> 0
```

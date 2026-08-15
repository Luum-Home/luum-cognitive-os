# Higiene de estado y enlaces de los ADRs — 2026-08-15

Alcance: vocabulario de estado, normalización y enlaces `supersedes` / `superseded_by`.
Fuera de alcance: si los ADRs siguen describiendo el código (otro agente), y los
números volátiles en `docs/` (otro agente). No se borró ni se archivó ningún ADR.

---

## 1. Lo que era falso en el encargo

**El vocabulario ya estaba definido, y con más rigor del que pedía el encargo.**
Vive en `docs/02-Decisions/adrs/STATUS-TAXONOMY.md` (fechado 2026-05-12) y ya
separa los dos ejes que el encargo proponía como hallazgo a descubrir: `status`
(decisión) e `implementation_status` (implementación). Está enforced por
`scripts/audit_adrs.py` y por `tests/contracts/test_adr_status_taxonomy.py`.
La deriva, entonces, es *contra* ese vocabulario, y ése es el hallazgo.

**Las 12 cadenas no salen del campo de estado.** El comando del encargo hace
`grep -ihE '^\*?\*?status:?...'` sobre todo el archivo, así que mezcla tres
cosas distintas: el frontmatter YAML, la sección `## Status` del cuerpo, y
cualquier línea de prosa o fila de tabla que empiece con "Status:". Los
`8 active`, por ejemplo, son mayormente filas de tabla dentro del cuerpo de
ADRs como ADR-228, no estados de ADR.

Medido por separado:

```bash
python3 scripts/audit_adr_status_links.py --summary
```

| Eje | Valores distintos | Estado |
|---|---|---|
| Frontmatter `status` | 8 (7 canónicos + `Accepted` mal capitalizado) | casi limpio |
| Frontmatter `implementation_status` | 8 (7 canónicos + `Implemented`) | casi limpio |
| Prosa `## Status` (308 archivos) | **168 cadenas distintas** | sin gobierno |

O sea: el encargo sobrestimó la deriva del frontmatter (8, no 12, y 7 de esos 8
son canónicos) y **subestimó** la de la prosa por un factor de 14 (168, no 12).

**Los 502 no son 502 ADRs.** `ls docs/02-Decisions/adrs/ADR-*.md | wc -l` da 502,
pero 150 de esos archivos son `*.synthesis.md` — compañeros generados, no ADRs.
Los ADRs reales son **352**.

---

## 2. Vocabulario cerrado (el que ya existe, no uno nuevo)

Definido en `STATUS-TAXONOMY.md`; lo reproduzco porque es el contrato contra el
que validé, no porque lo haya inventado.

**Eje 1 — `status` (decisión):** `proposed`, `exploration`, `accepted`,
`implemented`, `resolved`, `superseded`, `deprecated`, `tombstone`.

**Eje 2 — `implementation_status`:** `not-applicable`, `planned`, `partial`,
`partial-blocked`, `blocked`, `deferred`, `implemented`, `resolved`.

Transiciones legales que el audit ya hace cumplir (`scripts/audit_adrs.py`):

- `tombstone` / `superseded` / `deprecated` ⇒ `implementation_status` sólo puede
  ser `not-applicable` o `resolved` (un ADR terminal no tiene trabajo en curso).
- `implementation_status: implemented` ⇒ todo `implementation_files` declarado
  tiene que resolver en disco, y el texto no puede mencionar trabajo futuro
  in-scope sin declararlo en `classification_basis`.
- `status` tiene que ser un escalar. Nada de mapas `part_a` / `part_b`.
- ADRs nuevos (≥276) exigen `classification_basis`, `implementation_files`,
  `tier` y `tags`.

**Respuesta a los casos compuestos del encargo**, en orden:

- `accepted — implemented` → sí, son dos ejes apretados en un campo, y la
  respuesta ya implementada son **dos campos**. En frontmatter esos ADRs ya
  dicen `status: accepted` + `implementation_status: implemented`. La cadena
  compuesta vive sólo en la prosa, como anotación legible.
- `accepted — slices a–f implemented (2026-05-07)` → la fecha y el progreso
  parcial **no son estado**, correcto. Ya están donde corresponde: el progreso
  en `implementation_status: partial`, la fecha en el campo `date`, y el detalle
  de qué slice cerró, en el cuerpo. La prosa es la copia legible, y por eso
  **no la aplané** (ver §5).
- `tombstone` (13 en frontmatter) → estado real y canónico. Es un slot retirado.
- `active` (8) → **no es estado**: son filas de tabla en el cuerpo de ADRs.
  Cero apariciones en frontmatter.
- `exploration` (2) → estado real y canónico.
- `resolved` (1) → estado real y canónico.
- `addendum to adr-028` (2) → **no es estado**: es prosa del cuerpo. Los ADRs
  028a/b/c ya tienen frontmatter propio y correcto.

---

## 3. Clasificación de los 352 ADRs reales

```bash
python3 scripts/audit_adr_status_links.py --summary
```

| `status` | n | | `implementation_status` | n |
|---|---:|---|---|---:|
| accepted | 288 | | implemented | 175 |
| proposed | 22 | | partial | 125 |
| implemented | 21 | | not-applicable | 26 |
| tombstone | 13 | | planned | 21 |
| superseded | 5 | | deferred | 2 |
| exploration | 2 | | resolved | 2 |
| resolved | 1 | | partial-blocked | 1 |

(Cifras post-normalización. Antes había además 3 `Accepted` y 3 `Implemented`.)

---

## 4. Qué normalicé

Siete archivos, todos con cambio literal y sin cambio semántico.

**a) Capitalización — 6 campos en 3 archivos.** `status: Accepted` → `accepted`
y `implementation_status: Implemented` → `implemented` en ADR-308, ADR-309 y
ADR-310. `STATUS-TAXONOMY.md` dice explícitamente "Use lowercase values in
frontmatter". `scripts/audit_adrs.py` los aceptaba porque hace `.lower()` antes
de validar (línea 597), así que la deriva era invisible para el gate pero visible
para cualquier `grep '^status: accepted'`.

> Corrección a una afirmación propia: llegué a escribir que esta deriva sacaba a
> los tres ADRs del INDEX. Es falso — `generate_adr_index.canonical_status()`
> también normaliza mayúsculas (verificado). El INDEX no los lista por estar
> desactualizado, no por la capitalización. La justificación del arreglo es sólo
> la regla escrita y el match literal.

**b) Enlaces sin salida — 2 archivos.** Ambos casos donde el propio archivo ya
decía la respuesta en prosa y el frontmatter estaba atrasado:

- `ADR-084` tenía `status: superseded` con `superseded_by: null`, mientras su
  propio cuerpo dice tres veces "Superseded by ADR-091". Ahora
  `superseded_by: ADR-091`.
- `ADR-043-tombstone` no tenía puntero al sucesor, mientras ADR-171 declara
  `supersedes: [ADR-043]` en frontmatter y lo repite en cuatro lugares del
  cuerpo. Ahora `superseded_by: ADR-171`.

**c) Cierre del par — 2 archivos.** Donde el predecesor ya declaraba
`superseded_by` y al sucesor le faltaba el `supersedes` recíproco:

- `ADR-091` ahora declara `supersedes: [ADR-084]`, cerrando el par del punto (b).
- `ADR-018` ahora declara `supersedes: [ADR-011]`; ADR-011 ya estaba en
  `status: superseded` con `superseded_by: ADR-018`.

Ambos verificados contra `ADR_RELATION_CYCLE` después de aplicarlos (§8).

Nada de esto agrega una afirmación nueva: en los tres casos la aserción ya
existía en el repo y sólo faltaba el puntero que la hace navegable.

---

## 5. Qué preservé al normalizar

El verde barato de este lote era aplanar las 168 cadenas de prosa a `accepted`.
No lo hice, y la razón es medible: de esas 168, **163 coinciden** con el
frontmatter y sólo agregan detalle (fecha, qué slice cerró, qué quedó pendiente).
Las 5 restantes que mi validador marcó al principio resultaron ser **falsos
positivos de mi propio detector**: decían "Accepted — Implemented" o
"Accepted — Partially Implemented", y yo estaba comparando sólo la primera
palabra contra el frontmatter.

Corregí el detector en vez de aceptar el hallazgo: `accepted` / `implemented` /
`resolved` son la misma familia de ciclo de vida (las tres caen en el bucket
Active según la propia taxonomía), así que una prosa que dice "Accepted —
Implemented" contra un frontmatter `implemented` es anotación, no contradicción.
La regla ahora sólo dispara entre familias distintas.

Para que eso no se convierta en una regla que nunca dispara, el test
`test_prose_status_contradiction_fires_across_families` fabrica un ADR con
frontmatter `accepted` y prosa "Proposed" y verifica que salte, y cuatro casos
parametrizados verifican que las formas de anotación **no** salten.

Resultado: **cero información destruida**. La prosa quedó intacta; el dato
estructurado ya vivía en `implementation_status` y `date`.

---

## 6. Casos que dejo al operador

Ninguno de estos lo toqué: los tres cambian lo que el repo afirma sobre sí mismo.

**6.1 — ADR-314 tiene sucesor declarado y sigue diciéndose vigente.**
`ADR-321` declara `supersedes: [ADR-314]`, pero ADR-314 sigue en
`status: accepted` / `implementation_status: implemented` con `superseded_by: null`.
Agregarle el puntero es higiene; **cambiarle el estado a `superseded` es una
decisión**, porque hoy el repo lo afirma vigente e implementado. Puede pasar
también que la que sobra sea la aserción de ADR-321.

```bash
grep -A2 '^supersedes:' docs/02-Decisions/adrs/ADR-321-*.md
grep -E '^(status|implementation_status|superseded_by):' docs/02-Decisions/adrs/ADR-314-*.md
```

**6.2 — ADR-192 no puede cerrar su par sin romper otro gate.**
`ADR-187` declara `superseded_by: ADR-192`, pero ADR-192 no declara el
`supersedes` recíproco. **Intenté cerrarlo y lo revertí**: `scripts/audit_adrs.py`
también deriva aristas de la prosa, y ADR-187 dice "Future Surface 5 adoption
work extends ADR-192", lo que produce una arista 187→192. Al agregar 192→187
el audit pasó de 0 a 2 `ADR_RELATION_CYCLE` (verificado comparando contra
`git show HEAD:` del archivo). El arreglo real es redactar esa línea de ADR-187,
que es contenido, no metadato.

**6.3 — ADR-174b declara el número de otro ADR.**
`ADR-174b-prevention-followup.md` tiene `adr: "174-bis"`, que resuelve al mismo
slot que `ADR-174`, mientras su hermano `ADR-174c` usa `adr: "174c"` y la familia
028 usa `28a`/`28b`/`28c`. Dos convenciones para lo mismo. No lo cambié porque
`adr:` alimenta al generador del INDEX.

**6.4 — INDEX.md está desactualizado (pre-existente, no lo toqué).**
El encabezado dice 501 archivos; hoy son 502. Regenerado en memoria, el diff son
23 líneas e incluye filas faltantes para ADR-308, ADR-309 y ADR-310. El
generador es `scripts/generate_adr_index.py`; **no lo corrí** — bajo checkout
compartido conviene coordinarlo. Verificación no destructiva usada:

```bash
python3 -c "import sys;sys.path.insert(0,'.');import scripts.generate_adr_index as g,pathlib,difflib;
print(len(list(difflib.unified_diff(pathlib.Path('docs/02-Decisions/adrs/INDEX.md').read_text().splitlines(), str(g.generate()).splitlines(), n=0))))"
```

**6.5 — 10 FAIL pre-existentes en `scripts/audit_adrs.py`.** ADR-322, 323, 324,
325, 326, 327, 335, 339, 341 y uno más: faltan `classification_basis`, `tags`,
`tier`, o el texto menciona trabajo futuro sin declararlo. Son de la familia
"realidad del ADR", no de estado/enlaces. Verificado que ninguno cae sobre los
archivos que toqué.

---

## 7. El validador

`scripts/audit_adr_status_links.py` — read-only, determinista, sin estado de
sesión. Exit 0 sin hallazgos / 1 con hallazgos / 2 error.

No redefine el vocabulario: lo importa de `scripts/audit_adrs.py`, que a su vez
lo toma de `STATUS-TAXONOMY.md`. Una sola definición.

Cubre los cuatro huecos que el audit existente deja pasar:

| Código | Qué detecta | Por qué el audit actual no lo ve |
|---|---|---|
| `STATUS_CASE_DRIFT` | `Accepted` en vez de `accepted` | hace `.lower()` antes de validar |
| `SUPERSEDE_LINK_ASYMMETRY` | una punta del enlace declarada y la otra no | nunca compara las dos puntas |
| `SUPERSEDED_DEAD_END` | terminal sin puntero al sucesor | no existe la regla |
| `PROSE_STATUS_CONTRADICTS_FRONTMATTER` | prosa y frontmatter en familias distintas | sólo mira frontmatter |
| `DUPLICATE_ADR_NUMBER` | dos archivos en el mismo slot | — |

Sobre el ratchet: el allowlist de prosa es una **lista con nombres y motivo
escrito**, no un número, y está **vacío**. Un baseline numérico habría escondido
cuánto colchón carga; con lista vacía queda explícito que no hay nada suprimido.
`STALE_BASELINE` marca cualquier entrada que deje de corresponder, para que un
supresor que no suprime nada sea un hallazgo y no un pase silencioso.

Los pares tombstone→autoridad (ADR-253→251, ADR-326→228, ADR-327→036) salen como
**nota, no como hallazgo**. El criterio: ¿un cambio en ADR-251 debería obligar a
tocar el retirado ADR-253? No. El `superseded_by` de un tombstone apunta a quién
tiene la autoridad ahora, no afirma que alguien reemplazó una decisión viva.
Coincidencia de forma, con el motivo escrito en el código.

Estado actual:

```
$ python3 scripts/audit_adr_status_links.py ; echo $?
[DUPLICATE_ADR_NUMBER] 1   → §6.3
[SUPERSEDE_LINK_ASYMMETRY] 2 → §6.1, §6.2
3 finding(s) across 352 ADRs.
[notes] 3 accepted-by-design
1
```

Los 3 hallazgos abiertos son exactamente los casos de §6 que corresponden al
operador. No los apagué.

Tests: `tests/contracts/test_adr_status_links.py`, 12 casos, todos pasan. Cada
regla se prueba contra un infractor fabricado **y** contra un caso conforme, para
que ninguna quede como regla muerta.

```bash
.venv/bin/pytest tests/contracts/test_adr_status_links.py -q   # 12 passed
```

---

## 8. Verificación de no-regresión

```bash
python3 scripts/audit_adrs.py 2>&1 | grep -oE 'FAIL: [0-9]+'   # FAIL: 10 (igual que antes)
python3 scripts/audit_adrs.py 2>&1 | grep -c ADR_RELATION_CYCLE # 0
```

Ningún FAIL cae sobre los 8 archivos modificados. Se detectó y revirtió el único
cambio que sí regresaba (§6.2).

Nota de concurrencia: durante la sesión apareció `ADR-064` modificado por otra
sesión. Quedó fuera del commit; los `git add` fueron por ruta explícita.

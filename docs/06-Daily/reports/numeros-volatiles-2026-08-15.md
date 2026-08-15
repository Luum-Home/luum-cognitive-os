# Números volátiles en la prosa de la documentación

Fecha: 2026-08-15. Alcance: `docs/`, `rules/`, `README.md`, `CLAUDE.md`.

Evidencia ejecutable: `scripts/volatile_number_audit.py` (read-only, determinista,
exit 0/1/2). Todo número de este informe sale de un comando citado abajo.

---

## 1. El criterio

Un número **se saca de la prosa** cuando cambiaría sin que nadie edite ese
documento. La prosa entonces dice **cómo saberlo**, no **cuánto es** — in English,
for the claim that audits this: The prose says how to know it, not how many.

Un número **se queda** cuando es parte del hecho histórico o del contrato. Seis
categorías, todas decidibles por otro sin criterio propio:

| Veredicto | Se queda | Señal que lo decide |
| --- | --- | --- |
| `volatile` | no | conteo de censo en presente, sin ancla de fecha |
| `historical` | sí | fecha explícita, nombre de archivo fechado, verbo en pasado, doc de registro (case study / post-mortem) |
| `contract` | sí | umbral o límite (`max`, `more than`, `50+`), constante enumerada, bloque de código, ordinal (`Phase 1 rules`) |
| `external` | sí | el conteo describe otro proyecto (Aguara, Hermes, semgrep): ningún censo nuestro lo produce |
| `illustrative` | sí | el número está entre comillas: es texto de ejemplo o una cita de otro documento |
| `adr-title` | escalar | el número está en el título de un ADR: renombrarlo rompe enlaces |

### La frontera en los ADRs

En un ADR la pregunta es si el documento **decide** el número o lo **observa**:

- **Decide → se queda.** `"ADR-267 congeló 5 globs"`, `"exit 2 bloquea"`,
  `"3 reintentos"`. Es el contrato que el ADR fija; borrarlo destruye el ADR.
- **Observa → se va.** `"los 255 primitivos"`, `"93 hooks registrados"`. Es el
  estado del mundo el día en que se escribió, y venció al día siguiente.
- **Con fecha explícita → se queda siempre.** `"al 2026-05-10 había 30 hooks"`
  es correcto para siempre, aunque hoy sean otros.

Implementado en `ADR_DECISION_RE` / `ADR_OBSERVATION_RE` del script.

### El verde barato que se evitó

Reemplazar los números por texto vago ("varios hooks", "muchas primitivas")
destruye información y parece limpieza. La salida correcta es la referencia al
censo. Cada arreglo de este lote deja el comando que produce el número.

---

## 2. La clasificación

```bash
python3 scripts/volatile_number_audit.py --classify-only
```

Estado final, medido **antes** de agregar este informe (que suma sus propios
hallazgos, todos `historical` porque su nombre de archivo lleva la fecha):

| Veredicto | Hallazgos |
| --- | --- |
| volátil | 324 |
| histórico-correcto | 1005 |
| contrato | 367 |
| externo | 55 |
| ilustrativo | 252 |
| **total** | **2003** en 514 archivos |

Volátiles por nivel de daño: **tier 1 = 25, tier 2 = 216, tier 3 = 83**
(`python3 scripts/volatile_number_audit.py --format json | jq '[.findings[]|select(.verdict=="volatile")]|group_by(.tier)|map({tier:.[0].tier,n:length})'`).

Los tiers son por daño, no por antigüedad:

- **Tier 1** — `README.md`, `rules/**` (se carga en cada sesión), `docs/00-MOCs/**`
  (puerta de entrada), `docs/08-References/**` (material externo), `CLAUDE.md`.
- **Tier 2** — ADRs, `docs/04-Concepts/**`, `docs/07-Capabilities/**`, `docs/09-Quality/**`.
- **Tier 3** — el resto.

---

## 3. Qué se arregló

Tier 1 bajó de **102 a 25** volátiles. Total: de **499 a 324**.

| Archivo | Qué decía | Qué dice ahora |
| --- | --- | --- |
| `docs/00-MOCs/entrypoints/faq.md` | `57 hooks, 55 rules, 72 skills, 22 lib modules, 1714 tests` (x15) | bloque de comandos de censo en el encabezado; la prosa nombra las capas |
| `docs/00-MOCs/entrypoints/INDEX.md` | `94 scripts, 46 registered`; `1714 tests across 60 files` | `ls hooks/*.sh \| wc -l`; `pytest --collect-only` |
| `docs/00-MOCs/decisions.md` | `tabla de estado para 280 ADRs`; `ADR-009 (375 primitives)` | `ls docs/02-Decisions/adrs/ADR-*.md \| wc -l`; etiqueta sin conteo |
| `docs/00-MOCs/entrypoints/overview.md` | `46 hooks registrados ... 94 scripts` | los dos comandos que los cuentan |
| `docs/00-MOCs/entrypoints/getting-started-quick.md` | `24 hooks (standard profile)` | referencia al perfil + comando |
| `docs/00-MOCs/entrypoints/README.md` | `"lo que existe hoy"` con `41 hooks / 44 rules` | reencuadrado como inventario **de la Fase 1**, con comandos para el actual |
| `docs/08-References/business/features.md` | `244 hook scripts`, `120 rule files`, `561 script files` | comandos de censo en la tabla |
| `docs/08-References/business/portability-plan.md` | `14 hooks, 17 rules, 25+ skills, 16 agents` (x5) | inventario declarado como snapshot del plan + comandos |
| `docs/08-References/business/value-proposition.md` | `44 rules + 41 hooks` | `rules/` + `hooks/` |
| `rules/cognitive-load.md` | `carga ~88 rules` | `ls rules/*.md \| wc -l` |
| `rules/session-close-doc-truth.md` | `4 harnesses` | `manifests/harness-projection.yaml` |

Los 324 restantes quedan como deuda aceptada en el baseline, no borrados: el
ratchet solo permite que ese número baje.

---

## 4. El detector, para que no vuelva

```bash
python3 scripts/volatile_number_audit.py                 # exit 0 limpio / 1 con hallazgos nuevos
python3 scripts/volatile_number_audit.py --tier 1        # solo lo de mayor daño
python3 scripts/volatile_number_audit.py --write-report   # regenera el *-latest
python3 scripts/volatile_number_audit.py --update-baseline
```

- **Ratchet**: `manifests/volatile-number-baseline.json`, 291 claves aceptadas
  (324 hallazgos deduplican a 291: dos líneas idénticas en el mismo archivo
  comparten clave). Las claves son `path#sha256(snippet)`, **no** número de
  línea, así que editar otra parte del archivo no genera churn.
- **Baseline pegado a la realidad**: se generó midiendo, no a ojo. Un baseline
  por encima de la realidad sería un colchón — el gate diría "0 nuevas" mientras
  quedan lugares libres.
- **Reporte generado**: `docs/06-Daily/reports/volatile-numbers-latest.{json,md}`,
  siguiendo el patrón `*-latest` que ya usa el repo.
- **Claim declarado**: `volatile_number_prose` en
  `manifests/documentation-truth-claims.yaml` (ADR-277), para que el control
  plane audite la contradicción en vez de que se repita en prosa.

---

## 5. Qué del encargo era falso

Recontado con el mismo comando del encargo. Cuatro correcciones:

1. **"72 claims ya vivos" en el manifiesto → son 6.**
   ```bash
   python3 -c "import yaml;d=yaml.safe_load(open('manifests/documentation-truth-claims.yaml'));print(len(d['claims']))"
   # 6
   ```
   El 72 es el total de **entradas hoja** (`required_docs` + `required_phrases` +
   `forbidden_phrases` + `source_reports`) sumadas sobre los 6 claims. El
   mecanismo canónico está mucho menos poblado de lo que sugería el encargo:
   6 claims para un repo con 502 ADRs.

2. **"330 de 1845 archivos" → 330 es correcto, pero 100 de esos son bitácora.**
   Descontando `docs/06-Daily/reports/`, quedan 230 archivos editables. Y de los
   2003 hallazgos totales, solo **324 son volátiles**: el patrón del encargo tiene
   ~84% de falsos positivos contra el criterio real.

3. **Los "siete conteos de hooks" mezclan cuatro cosas distintas.** No son siete
   versiones del mismo hecho: 57/93/41/155/154 son observaciones vencidas de
   distintas fechas, 257 es el conteo de archivos **de hoy**, 12 es un umbral de
   perfil, y 189 no es de hooks sino de **reglas de Aguara**, un scanner de
   terceros. Contarlos juntos infla el defecto.

4. **`README.md` no tiene ningún número volátil.** Cero coincidencias. El encargo
   lo priorizaba como archivo de mayor daño; el daño real estaba en
   `docs/00-MOCs/entrypoints/faq.md`, que publicaba cinco conteos en su
   encabezado, todos incorrectos por un factor de 2 a 17.

### La verdad medida hoy, contra lo que publicaba el FAQ

```bash
ls hooks/*.sh | wc -l          # 257   (el FAQ decía 57)
ls rules/*.md | wc -l          # 130   (el FAQ decía 55)
ls -d skills/*/ | wc -l        # 193   (el FAQ decía 72)
ls cos_lib/*.py | wc -l        # 369   (el FAQ decía 22)
ls docs/02-Decisions/adrs/ADR-*.md | wc -l   # 502   (decisions.md decía 280)
```

---

## 6. Hallazgos que quedan para el operador

1. **`ADR-009` lleva `375 Agentic Primitives Reclassified` en el título** —
   frontmatter `title:` y encabezado `#`. Es una **observación**, no una decisión
   (el censo de hoy da otro número), pero cambiar el título de un ADR aceptado
   rompe enlaces. **No se tocó.** Propuesta: `Package Architecture — Agentic
   Primitive Reclassification`, con el 375 movido al cuerpo como observación
   fechada. Requiere decisión del operador.

2. **Números sin censo que los produzca.** `docs/08-References/root/adoption-tiers.md`
   publica `~116 / ~154 / ~170 hook fires per turn`. No hay script que los
   reproduzca. Es el hallazgo, no algo para borrar: o se escribe el censo que los
   mide, o se declaran como estimación fechada.

3. **85 volátiles viven en ADRs** (`ADR-009`, `ADR-028`, `ADR-075`, `ADR-132`,
   `ADR-027`, `ADR-059`, `ADR-178`, `ADR-010` son los peores). Están en el
   baseline, sin tocar el `status` ni los enlaces `superseded`, que son de otro
   agente.

4. **Los `.synthesis.md` heredan los números de su fuente.** Arreglar el origen
   no arregla la síntesis: se regenera. Vale revisar si el generador de síntesis
   debería correr después de este lote.

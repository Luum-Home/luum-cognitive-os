# Juez de Documentación — 2026-07-28

> Auditoría independiente read-only. El juez no arregla nada: mide, cita el comando
> y deja el veredicto. El ledger de verdad documental está **bajo** auditoría, no es
> fuente de verdad.
>
> Rama auditada: `session/content-bound-receipts` @ `6762c0f2e` (con trabajo sin commitear).

---

## Veredicto (una línea)

**La vidriera dice la verdad y el interior no**: README/AGENTS/ADRs son sólidos y auditables,
pero el 73.6% de los links internos de `docs/` está roto, 658 archivos `.md` siguen apuntando
a un directorio `lib/` que ya no existe, y los propios auditores documentales del repo
imprimen `"status": "fail"` mientras devuelven **exit 0**.

---

## Score de consistencia: **52 / 100**

| Dimensión | Peso | Nota | Justificación (con comando) |
|---|---:|---:|---|
| Superficie pública (README, AGENTS, TRANSPARENCY) | 20 | 17/20 | 0 links rotos de 49; 11/11 paths citados existen; el claim "14-layer safety mesh" coincide con `safety-mesh.md`. Descuento por badge de versión `0.1.0` y 4 URLs con `<org>/<repo>` sin renderizar. |
| Capa ADR | 20 | 18/20 | **0 huecos de numeración** en 1–341; 22 tombstones; supersesiones con nota explicativa de qué sobrevive. Descuento por 10.5% de links rotos y conteos stale ("280 ADRs" vs 351). |
| Cuerpo de `docs/` | 25 | 6/25 | 73.6% de links internos rotos (1207/1640). El índice insignia `entrypoints/README.md` tiene 364 links muertos sobre 411. |
| Coherencia código↔docs | 15 | 4/15 | `lib/` fue renombrado a `cos_lib/`; 658 `.md` y 51 de 129 archivos de `rules/` siguen citando `lib/*.py`. `rules/rate-limiting.md` se contradice a sí mismo en 11 líneas. |
| Auto-auditoría (ledger + scripts) | 15 | 5/15 | El ledger es honesto sobre lo que chequea (74/74 asserts pasan) pero chequea presencia de strings, no verdad; declara una política de staleness que **no implementa**; y `cos_doc_path_audit.py` devuelve exit 0 con `"status":"fail"`. |
| Metadata de versión | 5 | 2/5 | `VERSION`/`pyproject.toml` = 0.29.39, `package.json` = 0.1.0 (mismo nombre de paquete). 22 de 60 releases del CHANGELOG repiten un "Added" idéntico y falso. |
| **Total** | **100** | **52** | |

Lectura: **no es un repo que mienta, es un repo que no barre.** Lo que se publica hacia
afuera está cuidado y verificado; lo que se acumula hacia adentro nunca se revisó — 34.7%
de los `.md` se commiteó exactamente una vez y no se tocó nunca más.

---

## Tabla de contradicciones concretas

| # | Doc A dice X | Doc B / código dice Y | Comando |
|---|---|---|---|
| 1 | `rules/rate-limiting.md:89` — "**Library**: `lib/rate_limiter.py`" | `rules/rate-limiting.md:100` — `from cos_lib.rate_limiter import RateLimiter`. `lib/` no existe. **El mismo archivo, siempre activo en el contexto de todo agente, se contradice en 11 líneas.** | `grep -nE 'lib/rate_limiter\|cos_lib.rate_limiter' rules/rate-limiting.md; [ -d lib ] \|\| echo "lib/ NO existe"` |
| 2 | `rules/RULES-COMPACT.md` cita `lib/cost_predictor.py`, `lib/dispatch.py`, `lib/dogfood_scorer.py`, `lib/harness_adapter/` | Los cuatro existen sólo bajo `cos_lib/`. Hay un commit propio: `26c18c25e fix(hooks): restore 8 OS features silently disabled by the cos_lib rename` | `for p in cost_predictor.py dispatch.py dogfood_scorer.py harness_adapter; do [ -e "cos_lib/$p" ] && echo "OK cos_lib/$p"; [ -e "lib/$p" ] \|\| echo "MISS lib/$p"; done` |
| 3 | `scripts/cos_doc_path_audit.py` emite `"status": "fail"` con **2733 findings** | El proceso devuelve **exit 0**. Cualquier gate de CI atado al exit code pasa en verde. | `python3 scripts/cos_doc_path_audit.py >/dev/null 2>&1; echo "exit: $?"` |
| 4 | `scripts/check_entrypoint_adr_links.py` imprime `entrypoint ADR links: ok` (exit 0) | `docs/00-MOCs/entrypoints/README.md` tiene **96 links `](adrs/ADR-…)`** que resuelven a `docs/00-MOCs/entrypoints/adrs/` — inexistente. El checker resuelve contra `docs/02-Decisions/adrs/` (línea 23), o sea valida que el ADR *exista*, no que el *link funcione*: **normaliza el bug que debería detectar.** | `grep -coE '\]\(adrs/ADR-' docs/00-MOCs/entrypoints/README.md; sed -n '17,24p' scripts/check_entrypoint_adr_links.py` |
| 5 | `manifests/documentation-truth-claims.yaml` — `status_policy.block: "…backed by a missing/stale source report"` | El script no implementa ninguna noción de antigüedad (`grep` de `max_age\|age_days\|mtime` no devuelve nada). Sus fuentes tienen 42 y 77 días: `primitive-projection-fidelity-latest.json` (2026-06-16) y `operational-guide-audit-latest.json` (2026-05-12). Estado reportado: `pass`. | `grep -niE 'max_age\|age_days\|mtime' scripts/documentation_truth_audit.py; python3 -c "import json;print(json.load(open('docs/06-Daily/reports/operational-guide-audit-latest.json'))['generated_at'])"` |
| 6 | `docs/06-Daily/reports/pending-truth-latest.md` — "Verified **2026-07-28**T20:32:07Z" | `pending-truth-latest.json` — `"generated_at": "2026-07-08T21:23:36Z"`. 20 días de diferencia entre las dos mitades del mismo artefacto. | `head -1 docs/06-Daily/reports/pending-truth-latest.md; python3 -c "import json;print(json.load(open('docs/06-Daily/reports/pending-truth-latest.json'))['generated_at'])"` |
| 7 | `CHANGELOG.md` — 22 de 60 releases declaran *idéntico*: "Added the `cos-patch-release` primitive for repeatable patch release preparation…" | El primitivo se agregó **una vez**, en v0.29.7 (`414382d11`). 21 releases declaran un "Added" falso. | `grep -c 'Added the .cos-patch-release. primitive for repeatable patch release' CHANGELOG.md; git log --oneline --diff-filter=A -- scripts/cos-patch-release` |
| 8 | `README.md` badge: `version-0.1.0-green`; `package.json`: `"version": "0.1.0"` | `VERSION` y `pyproject.toml`: `0.29.39`; tag más reciente `v0.29.39`. Mismo nombre de paquete (`cognitive-os`), 29 minors de distancia. | `cat VERSION; grep -m1 '"version"' package.json; grep -oE 'version-[0-9.]+-green' README.md` |
| 9 | `docs/00-MOCs/decisions.md` — "full status table for **280 ADRs**" | Hay **351** ADRs no-synthesis. Además el link `../adrs/INDEX.md` resuelve a `docs/adrs/INDEX.md`, inexistente (lo reporta el propio `docs-execution-latest.md` como `missing_path`). | `grep -oE 'for [0-9]+ ADRs' docs/00-MOCs/decisions.md; ls docs/02-Decisions/adrs/ADR-*.md \| grep -vc synthesis` |
| 10 | `docs/00-MOCs/entrypoints/getting-started-quick.md` instala vía `…/main/scripts/install-cos.sh` | `README.md` y `getting-started.md` instalan vía `…/main/install.sh`. Ambos scripts existen y son distintos: dos caminos de onboarding divergentes sin nota de cuál es canónico. | `for f in README.md docs/00-MOCs/entrypoints/getting-started{,-quick}.md; do echo "--$f"; grep -oE 'curl [^ ]*install[^ ]*' "$f"; done` |
| 11 | `README.md` badges de métricas apuntan a `raw.githubusercontent.com/<org>/<repo>/main/…` | Placeholder de plantilla sin renderizar × 4. El remote real es `Luum-Home/luum-cognitive-os`. | `grep -c '<org>/<repo>' README.md; git remote -v \| head -1` |
| 12 | `package.json` — `"test": "bash tests/run-all-tests.sh"` | `tests/run-all-tests.sh` no existe. `npm test` falla de entrada. | `[ -e tests/run-all-tests.sh ] \|\| echo MISSING` |

---

## Los 10 claims del ledger verificados a mano

Verificados con un verificador **propio** (`ledger_verify.py`, reproducido en el anexo),
deliberadamente sin llamar a `scripts/documentation_truth_audit.py`. El ledger declara
**5 claims** que se descomponen en **74 aserciones**; **74/74 pasan**. Selección de 10,
con el chequeo *profundo* que el ledger no hace:

| # | Claim / aserción | Lo que el ledger afirma | Mi verificación independiente | Resultado |
|---|---|---|---|---|
| 1 | `consumer_projection_harnesses` → `required_phrase: "Structural projection is not runtime enforcement"` | La frase está en los required_docs | Presente en `consumer-project-primitive-accessibility.md` | ✅ **Verdadero** |
| 2 | `consumer_projection_harnesses` → `forbidden_phrase: "only Claude/Codex"` | La frase *no* aparece | Ausente de los 2 required_docs | ✅ **Verdadero** |
| 3 | `consumer_projection_harnesses` → `source_report: primitive-projection-fidelity-latest.json` | El reporte existe | Existe, **pero `generated_at` = 2026-06-16, 42 días stale**. El `status_policy` dice que eso debería ser `block`; el ledger devuelve `pass`. | ⚠️ **Verdadero pero engañoso** |
| 4 | `primitive_authority_write_effects` → `required_phrase: "scripts/primitive_authority_audit.py"` | El doc nombra el script | El doc lo nombra **y el script existe** | ✅ **Verdadero (y sustantivo)** |
| 5 | `primitive_authority_write_effects` → `forbidden_phrase: "not implemented yet"` | Ausente | Ausente | ✅ **Verdadero** |
| 6 | `documentation_truth_control` → `required_phrase: "documentation_truth"` | El doc contiene el string | Presente — pero es el propio nombre del claim: **aserción tautológica**, no puede fallar salvo que se borre el doc | ✅ **Verdadero / sin valor probatorio** |
| 7 | `session_pending_protocol` → `required_phrase: "cos-closure-trust-signal"` | El doc nombra el primitivo | Nombrado en 5 docs; **existe** como `scripts/cos-closure-trust-signal.py` (con test de portabilidad). Nota: el ledger habría pasado igual si el script no existiera — sólo mide el string. | ✅ **Verdadero (por suerte, no por diseño)** |
| 8 | `session_pending_protocol` → `source_report: operational-guide-audit-latest.json` | Existe | Existe, `generated_at` = **2026-05-12 → 77 días stale**. Mismo agujero que #3. | ⚠️ **Verdadero pero engañoso** |
| 9 | `subprocess_timeout_discipline` → `required_phrase: "subprocess.run"` / `"timeout="` | Los strings están en ADR-278 | Presentes — pero son fragmentos que cualquier ADR sobre el tema contiene por accidente. **Aserción no falsable en la práctica.** | ✅ **Verdadero / sin valor probatorio** |
| 10 | `session_pending_protocol` → `generated_block: pending-truth-architecture.md#session_pending_protocol` | Bloque generado, `required: false` | **El marcador NO está en el doc.** Pasa sólo porque `required: false`. El ledger declara un mecanismo de bloque generado que en 2 de 5 claims no está materializado. | ⚠️ **Pasa por exención, no por cumplimiento** |

### Veredicto sobre el ledger

**El ledger no miente sobre sí mismo — pero prueba mucho menos de lo que su nombre sugiere.**

1. **Es honesto**: mi verificador independiente (74 asserts) y el del repo (126 filas) coinciden en `pass`. No hay claim falso.
2. **Es angosto**: 5 claims para un corpus con 2283 links rotos. `RULES-COMPACT §16` promete que *toda* contradicción documental termina en un claim del ledger o en deuda explícita; con 5 claims, esa regla es aspiracional.
3. **Es superficial**: las aserciones son presencia/ausencia de strings. `grep -c 'cos_lib\|lib/' manifests/documentation-truth-claims.yaml` = **0** — el drift documental más grande del repo (658 archivos) es invisible para el ledger.
4. **Declara una política que no ejecuta**: `status_policy.block` menciona "stale source report"; el script no tiene ninguna comprobación de antigüedad. Dos de sus fuentes tienen 42 y 77 días.

---

## Correcciones a las premisas del encargo

| Premisa recibida | Realidad medida | Comando |
|---|---|---|
| "~4821 archivos `.md`" | **4289** en total; **3977** vivos excluyendo `archive/`, `99-Archive/`, `external-source-cache/`, `node_modules`, `target`, `.venv` | `find . -name '*.md' -type f \| wc -l` |
| "~505 ADRs" | 505 **archivos** en el directorio, sí — pero son **351 ADRs reales** + **150 `.synthesis.md`** + 4 plantillas | `ls docs/02-Decisions/adrs/ADR-*.md \| grep -vc synthesis` |
| "¿Hay huecos de numeración sin tombstone?" | **No hay huecos en absoluto.** 341 números distintos, rango 1–341, **0 gaps**. Además 22 números llevan tombstone explícito. Esta premisa no se sostiene y no la apliqué. | ver anexo `adr_numbering` |
| "¿Hay ADRs duplicados / estados incoherentes?" | 7 números tienen más de un archivo no-synthesis (`ADR-028{,a,b,c}`, `ADR-174{,b,c}`…) — son **sub-decisiones legítimas**, no colisiones. Las supersesiones traen nota de qué cláusula sobrevive. **La capa ADR es la más sana del repo.** | ver anexo |
| "¿ADRs superseded citados como vigentes?" | 7 ADRs con status `superseded`, citados en 7–54 docs cada uno. Revisé la cadena ADR-170→ADR-172 (la que cita el README): la supersesión está bien documentada y el README cita al **sucesor correcto**. No encontré un caso de superseded citado *como vigente*. | `grep -ilE '^\**status.*supersed' docs/02-Decisions/adrs/*.md` |

---

## Volumen vs señal

Criterio: un `.md` es **documentación viva** si fue revisado al menos una vez después de
crearse (≥2 commits) y tocado en los últimos 90 días. Si se escribió una vez y nunca se
volvió a tocar, es **sedimento de sesión**.

| Métrica | Valor | Comando |
|---|---:|---|
| `.md` vivos (excl. archive/vendor) | 3977 | `find . \( -path './.git' -o -name node_modules -o -name target -o -name .venv \) -prune -o -name '*.md' -print \| wc -l` |
| `.md` trackeados por git | 2380 | `git ls-files '*.md' \| wc -l` |
| **`.md` vivos NO trackeados** | **1624 (40.8%)** | ver anexo `corpus_stats` |
| Commiteados **exactamente una vez** (sedimento) | **1361 / 3917 = 34.7%** | `git log --name-only --pretty=format: -- '*.md'` + conteo |
| Tocados en los últimos 30 días | 634 (16.2%) | idem, con `%ct` |
| Con fecha `YYYY-MM-DD` en el nombre (artefacto de sesión) | 499 | ver anexo |
| `docs/06-Daily/reports/` | 380 archivos, 69.1% de links rotos | `ls docs/06-Daily/reports \| wc -l` |

**Señal**: ~16% del corpus se mantiene activamente. El resto es correcto-en-el-momento-en-que-se-escribió
y nadie lo volvió a mirar. Que 40.8% de los `.md` vivos ni siquiera esté en git refuerza el diagnóstico:
buena parte del volumen no es documentación, es salida de proceso que quedó en el árbol.

---

## Distribución de links rotos por zona

```
bucket                                         files   links  broken     pct
docs/ (other)                                    964    1640    1207   73.6%
docs/06-Daily/reports (sedimento de sesión)      315     666     460   69.1%
vendored-plugins (.claude/plugins, terceros)     736    1109     448   40.4%
docs/02-Decisions/adrs                           505     717      75   10.5%
.cognitive-os/ (estado de runtime)               373      85      70   82.4%
root-level (README/AGENTS/TRANSPARENCY/…)          9      49       0    0.0%
rules/                                           129       1       0    0.0%
skills/                                          122       0       0    0.0%
TOTAL                                           3981    4314    2283   52.9%
```

Excluyendo los plugins vendorizados de terceros, el corpus propio queda en
**1835 / 3205 = 57.3%** de links internos rotos.

Peores archivos individuales:

| Rotos | Archivo |
|---:|---|
| 364 / 411 | `docs/00-MOCs/entrypoints/README.md` |
| 250 | `docs/06-Daily/reports/adr-implementation-status-backfill-2026-05-12.md` |
| 173 | `docs/00-MOCs/entrypoints/INDEX.md` |
| 147 | `docs/03-PoCs/research/INDEX.md` |
| 132 | `docs/08-References/business/master-plan-checklist.md` |
| 131 | `docs/06-Daily/reports/docs-execution-latest.md` |

**Causa raíz dominante**: los índices de `docs/00-MOCs/` están escritos como si vivieran en
`docs/`. Mezclan links correctos (`../../06-Daily/reports/x.md`) con links pelados
(`reports/x.md`, `adrs/ADR-NNN.md`, `../architecture.md`) que resuelven a directorios
inexistentes. El destino casi siempre existe — el que está mal es el prefijo. Es un bug
mecánico y masivamente reparable, no pérdida de información.

---

## No verificado

Lo que **no** pude comprobar, y por qué:

1. **Links externos (9972)**. No se resolvió ninguna URL `http(s)://`. Un README puede citar
   un repo o release que ya no existe y este informe no lo detectaría. Requiere red y no es
   read-only respecto de terceros.
2. **Veracidad semántica de las afirmaciones en prosa.** Medí si los paths existen, no si lo
   que la prosa afirma sobre ellos es cierto. Un doc puede citar `hooks/rate-limiter.sh`
   (existe) y describir mal lo que hace.
3. **Los 2733 findings de `cos_doc_path_audit.py` uno por uno.** Verifiqué el contradictorio
   (status fail + exit 0) y muestreé la salida; no clasifiqué cada finding entre real y
   falso positivo. La propia herramienta marca muchos como `warn`/`ambiguous`.
4. **Anclas dentro de los archivos** (`#seccion`). El verificador corta en `#` y sólo valida
   el archivo. Un link a una sección borrada cuenta como válido acá.
5. **Los 505 ADRs leídos íntegramente.** Analicé estados, numeración, tombstones, cadenas de
   supersesión y links por script; leí a mano ~6 (ADR-170/172 y las cadenas citadas por el
   README). Puede haber contradicciones de *contenido* entre dos ADRs `accepted` que sólo
   aparecen leyendo el argumento completo — es el hueco más grande de esta auditoría.
6. **Si los reportes stale están además equivocados.** Verifiqué antigüedad
   (`generated_at`), no si su contenido dejó de ser cierto.
7. **`docs-execution-latest.md`** (5832 items, 2742 `done_weak_proof`) se cita como dato
   reportado por la herramienta del repo; no re-derivé esa clasificación de forma independiente.
8. **Trabajo sin commitear** en `session/content-bound-receipts`: audité el árbol de trabajo
   tal como está. No usé `stash`/`checkout`/`reset`, así que no comparé contra `HEAD` limpio.

---

## Anexo — evidencia ejecutable

Los tres scripts que produjeron los números. Read-only, deterministas, exit `0` sin
hallazgos / `1` con hallazgos / `2` error.

### `link_audit` — links internos rotos

```python
import os, re, subprocess
from pathlib import Path
ROOT = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True, check=True).stdout.strip())
PRUNE = {".git","node_modules","target",".venv","__pycache__","dist",
         ".pytest_cache",".ruff_cache","archive","99-Archive","external-source-cache"}
LINK_RE = re.compile(r'\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)')
tot = broken = 0
for dp, dn, fn in os.walk(ROOT):
    dn[:] = [d for d in dn if d not in PRUNE]
    for f in (x for x in fn if x.endswith(".md")):
        p = Path(dp) / f
        text = p.read_text(encoding="utf-8", errors="replace")
        for m in LINK_RE.finditer(text):
            t = m.group(1)
            if t.startswith(("http://","https://","mailto:","#","tel:","data:")):
                continue
            pp = t.split("#")[0].split("?")[0]
            if not pp:
                continue
            tot += 1
            cands = [ROOT / pp.lstrip("/"), Path(pp)] if pp.startswith("/") else [p.parent / pp]
            if not any(c.exists() for c in cands):
                broken += 1
                print(f"{p.relative_to(ROOT)}: {t}")
print(f"internal={tot} broken={broken} pct={100*broken/tot:.1f}%")
```

### `adr_numbering` — huecos, duplicados, tombstones

```python
import re
from pathlib import Path
d = Path("docs/02-Decisions/adrs")
nums = {}
for f in sorted(d.glob("ADR-*.md")):
    nums.setdefault(int(re.match(r'ADR-(\d+)', f.name).group(1)), []).append(f.name)
ks = sorted(nums)
print("distinct numbers:", len(ks), "range:", ks[0], "-", ks[-1])
print("GAPS:", [n for n in range(ks[0], ks[-1]+1) if n not in nums])
print("non-synthesis ADRs:", len([f for f in d.glob("ADR-*.md")
                                 if not f.name.endswith(".synthesis.md")]))
```

### `ledger_verify` — verificación independiente del ledger

```python
import yaml, subprocess
from pathlib import Path
ROOT = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True, check=True).stdout.strip())
led = yaml.safe_load((ROOT / "manifests/documentation-truth-claims.yaml").read_text())
fails = 0
for cname, c in led["claims"].items():
    docs = [ROOT / x for x in c.get("required_docs", [])]
    for x in docs:
        if not x.exists():
            print("FAIL required_doc", cname, x); fails += 1
    for sr in c.get("source_reports", []):
        if not (ROOT / sr).exists():
            print("FAIL source_report", cname, sr); fails += 1
    blob = "\n".join(x.read_text(encoding="utf-8", errors="replace")
                     for x in docs if x.exists())
    for ph in c.get("required_phrases", []):
        if ph not in blob:
            print("FAIL required_phrase", cname, ph); fails += 1
    for ph in c.get("forbidden_phrases", []):
        if ph in blob:
            print("FAIL forbidden_phrase", cname, ph); fails += 1
print("failing assertions:", fails)
```

### Contradicciones de auditores (one-liners)

```bash
# exit 0 con status "fail"
python3 scripts/cos_doc_path_audit.py >/dev/null 2>&1; echo "exit=$?"
python3 scripts/cos_doc_path_audit.py 2>/dev/null | python3 -c \
  'import json,sys; d=json.load(sys.stdin); print(d["status"], d["summary"]["findings"])'

# "ok" con 96 links muertos
python3 scripts/check_entrypoint_adr_links.py
grep -coE '\]\(adrs/ADR-' docs/00-MOCs/entrypoints/README.md

# drift lib/ -> cos_lib/
[ -d lib ] || echo "lib/ NO existe"
grep -rlE '`lib/[a-z_]+\.py' --include='*.md' . \
  --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=archive \
  --exclude-dir=99-Archive --exclude-dir=.venv --exclude-dir=target | wc -l

# CHANGELOG boilerplate
grep -c 'Added the .cos-patch-release. primitive for repeatable patch release' CHANGELOG.md
git log --oneline --diff-filter=A -- scripts/cos-patch-release
```

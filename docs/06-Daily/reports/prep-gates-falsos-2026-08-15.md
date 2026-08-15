# Preparación — gates falsos (2026-08-15)

Modo preparación: nada aplicado. Todos los auditores se corrieron en modo lectura
(`--no-write` / sin `--write-report`). No se tocó ningún archivo trackeado salvo este.

## 1. Veredicto

De los 4 gates auditados, **2 son falsos y 2 estaban mal reportados**:
`cos_doc_path_audit.py` falla la pregunta 2 (2779 hallazgos, `status: fail`, exit 0) y
la 3 (su único registro lo corre con una categoría estructuralmente vacía);
`check_entrypoint_adr_links.py` falla la pregunta 1 (normaliza el bug que debería
detectar: 114 links rotos leídos como sanos). `documentation_truth_audit.py` y
`cos-scope-projection-audit` tienen exit code coherente y están registrados —
el defecto de ambos es de **alcance declarado vs medido**, no de gate falso.

## 2. Tabla

| Gate | ¿Mide lo que dice? | ¿Exit coherente? | ¿Registrado? | Hallazgos hoy | Qué rompe al prender |
|---|---|---|---|---|---|
| `scripts/cos_doc_path_audit.py` | Sí (sobre 8.373 archivos trackeados) | **No** — `status: fail` y exit 0 | **Formalmente sí, materialmente no**: `tests/audit/test_doc_path_references.py` lo corre con `--fail-on legacy-runtime`, categoría con 0 hallazgos y 0 posibles | 2779 total · **349 bloqueables** (`missing_exact` 328 + `missing_glob` 21) · `ambiguous` 907 · `legacy_runtime` **0** | `--fail-on missing` → rojo en 147 archivos, de los cuales 237/349 son `tests/` (fixtures de `tmp_path`, ruido). Bloquea todo commit. |
| `scripts/check_entrypoint_adr_links.py` | **No** — resuelve contra `docs/02-Decisions/adrs/` en vez del directorio del archivo | Sí (0/2 bien cableado) | Sí — `tests/contracts/test_entrypoint_adr_links.py` | **0 reportados / 114 reales** | Fix de una línea → `tests/contracts/test_entrypoint_adr_links.py::test_entrypoint_adr_links_resolve_to_canonical_adr_files` rojo con 114 entradas (README.md 97, INDEX.md 16, getting-started.md 1) hasta que aterrice el arreglo de contenido. |
| `scripts/documentation_truth_audit.py` | **Parcial** — el manifest declara `block: ... missing/stale source report`; el script chequea *missing* y `status == "block"`, **nunca la edad** | Sí — `--fail-on-block` → exit 2 | Sí — `tests/contracts/test_documentation_truth_audit.py::test_current_documentation_truth_audit_passes` lo corre con `--fail-on-block` | 126 filas, **0 block**. Debt invisible: `primitive-projection-fidelity-latest.json` (fuente de `consumer_projection_harnesses`) último commit **2026-06-16, 60 días** | Con `max_age_days: 30` por claim: 3 de 5 claims a rojo el primer día (`consumer_projection`, `primitive_authority`, `documentation_truth` cuelgan de reportes del 2026-06-16). |
| `scripts/cos-scope-projection-audit --strict` | **Parcial** — mide la mitad *source* (1449 primitivas, 688/688 `both` con proof) y reporta `projection_total: 0` sin decir que **no midió** | Sí — `--strict` → exit 2 si `block_findings` | Sí, en tres lugares (ver §5) | `findings: 0`, `block_findings: 0` — **honesto en la mitad que mide** | Nada: la mitad de proyección **ya se mide** en CI y en `cos-ci-local.sh` con `--run-install-smoke`. El arreglo es de señal, no de gate. |

## 3. El desempate del punto 2

Los dos jueces se contradecían: uno decía "normaliza el bug", el otro "exit 2 con 0 links rotos".
Gana el primero. El segundo se contradice solo: exit 2 en ese script significa
*hay links rotos* (`return 2` está dentro del `if missing:`), así que "exit 2 con 0 rotos"
no es un estado alcanzable.

```
$ python3 scripts/check_entrypoint_adr_links.py; echo "EXIT=$?"
entrypoint ADR links: ok
EXIT=0
```

Y la medición que muestra que ese verde es falso:

```
$ python3 - <<'PY'
import re,pathlib
root=pathlib.Path('.')
RE=re.compile(r"\[[^\]]+\]\((adrs/[^)#]+)(?:#[^)]+)?\)")
ep=root/"docs/00-MOCs/entrypoints"
tot=broken=0
for p in sorted(ep.glob("*.md")):
    for m in RE.finditer(p.read_text(encoding="utf-8")):
        tot+=1
        if not (p.parent/m.group(1)).exists(): broken+=1
print("total adrs/ links:",tot,"rotos contra el directorio del archivo:",broken)
PY
total adrs/ links: 114 rotos contra el directorio del archivo: 114

$ ls docs/00-MOCs/entrypoints/adrs
ls: docs/00-MOCs/entrypoints/adrs: No such file or directory
```

Los 114 links dicen `adrs/ADR-xxx.md` desde archivos que viven en
`docs/00-MOCs/entrypoints/`. Cualquier renderer relativo (GitHub, Obsidian) los
resuelve a `docs/00-MOCs/entrypoints/adrs/...`, que no existe. El auditor los
resuelve a `docs/02-Decisions/adrs/...`, que sí existe, y por eso devuelve verde.
La forma correcta del link es `../../02-Decisions/adrs/ADR-xxx.md`.

Distribución: `README.md` 97, `INDEX.md` 16, `getting-started.md` 1.

## 4. Los parches

### 4.1 `scripts/check_entrypoint_adr_links.py` — resolver contra el archivo, no contra el destino esperado

```diff
--- a/scripts/check_entrypoint_adr_links.py
+++ b/scripts/check_entrypoint_adr_links.py
@@
 import argparse
+import os
 import re
 import sys
 from pathlib import Path
 
 ADR_LINK_RE = re.compile(r"\[[^\]]+\]\((adrs/[^)#]+)(?:#[^)]+)?\)")
 
 
 def find_broken_links(root: Path) -> list[str]:
     entrypoints = root / "docs/00-MOCs/entrypoints"
-    adr_root = root / "docs/02-Decisions/adrs"
     missing: list[str] = []
     for path in sorted(entrypoints.glob("*.md")):
         text = path.read_text(encoding="utf-8")
         for match in ADR_LINK_RE.finditer(text):
             target = match.group(1)
-            canonical = adr_root / target.removeprefix("adrs/")
+            # Resolve exactly like a Markdown renderer does: relative to the
+            # file that contains the link. Resolving against the canonical ADR
+            # directory normalizes away the very bug this gate exists to find.
+            canonical = Path(os.path.normpath(path.parent / target))
             if not canonical.exists():
                 missing.append(
                     f"{path.relative_to(root)} -> {target} "
-                    f"(expected {canonical.relative_to(root)})"
+                    f"(resolves to {canonical.relative_to(root)}, which does not exist)"
                 )
     return missing
```

`os.path.normpath` (no `Path.resolve()`) para que `../../` colapse sin tocar el
filesystem ni seguir symlinks — determinista y sin depender del cwd.

**Rompe también el test de contrato**, que codifica el bug en su aserción:

```diff
--- a/tests/contracts/test_entrypoint_adr_links.py
+++ b/tests/contracts/test_entrypoint_adr_links.py
@@
 def test_entrypoint_adr_link_checker_catches_missing_adr(tmp_path: Path) -> None:
     readme = tmp_path / "docs/00-MOCs/entrypoints/README.md"
     readme.parent.mkdir(parents=True)
     readme.write_text("[ADR-999](adrs/ADR-999-missing.md)\n", encoding="utf-8")
     (tmp_path / "docs/02-Decisions/adrs").mkdir(parents=True)
 
     missing = check_entrypoint_adr_links.find_broken_links(tmp_path)
 
     assert missing == [
         "docs/00-MOCs/entrypoints/README.md -> adrs/ADR-999-missing.md "
-        "(expected docs/02-Decisions/adrs/ADR-999-missing.md)"
+        "(resolves to docs/00-MOCs/entrypoints/adrs/ADR-999-missing.md, "
+        "which does not exist)"
     ]
+
+
+def test_checker_accepts_a_correctly_relative_link(tmp_path: Path) -> None:
+    """The fixed resolver must go green on the shape the content fix produces."""
+    readme = tmp_path / "docs/00-MOCs/entrypoints/README.md"
+    readme.parent.mkdir(parents=True)
+    adrs = tmp_path / "docs/02-Decisions/adrs"
+    adrs.mkdir(parents=True)
+    (adrs / "ADR-001-x.md").write_text("x", encoding="utf-8")
+    readme.write_text("[ADR-001](../../02-Decisions/adrs/ADR-001-x.md)\n", encoding="utf-8")
+
+    assert check_entrypoint_adr_links.find_broken_links(tmp_path) == []
```

Ojo: `ADR_LINK_RE` sólo matchea links que empiezan con `adrs/`. El link corregido
`../../02-Decisions/adrs/...` **no matchea el regex**, así que después del arreglo
de contenido el checker no mira nada. El test nuevo de arriba pasa por vacuidad.
Si se quiere que el gate siga cubriendo, hay que ampliar el regex — se agrega
como P2 en §6.

**Orden de aplicación:** este parche y el arreglo de contenido de los 114 links
(otro agente) tienen que aterrizar **en el mismo commit**. Aplicado solo, deja
`tests/contracts/` rojo con 114 entradas.

### 4.2 `scripts/cos_doc_path_audit.py` — ratchet con baseline, y basta de exit 0 mudo

Dos cambios independientes. El primero es barato y no bloquea nada: que un run sin
gate lo diga en stderr en vez de devolver 0 en silencio con `status: fail`.

```diff
--- a/scripts/cos_doc_path_audit.py
+++ b/scripts/cos_doc_path_audit.py
@@
 import argparse
 import json
 import os
 import re
 import subprocess
 from dataclasses import asdict, dataclass
 from pathlib import Path
+
+BASELINE_FILE = Path("manifests/doc-path-baseline.yaml")
+RATCHET_CODES = ("missing-exact", "missing-glob", "legacy-reference", "ambiguous")
+RATCHET_SURFACES = ("P0", "P1", "P2", "P3", "P4")
+RATCHET_KEYS = tuple(f"{c}.{s}" for c in RATCHET_CODES for s in RATCHET_SURFACES)
@@ def should_fail(payload, categories) -> bool:
     if "ambiguous" in categories and counts.get("ambiguous"):
         return True
     return False
+
+
+def ratchet_counts(payload: dict[str, object]) -> dict[str, int]:
+    """Findings bucketed by code x surface — the granularity a ratchet can descend."""
+    out = {key: 0 for key in RATCHET_KEYS}
+    for item in _finding_maps(payload.get("findings", [])):
+        key = f"{item.get('code')}.{item.get('surface')}"
+        if key in out:
+            out[key] += 1
+    return out
+
+
+def load_baseline(root: Path) -> dict[str, int]:
+    path = root / BASELINE_FILE
+    if not path.exists():
+        return {}
+    data: dict[str, int] = {}
+    for line in path.read_text(encoding="utf-8").splitlines():
+        line = line.split("#", 1)[0].strip()
+        if not line or ":" not in line:
+            continue
+        key, _, value = line.partition(":")
+        key = key.strip()
+        if key in RATCHET_KEYS:
+            try:
+                data[key] = int(value.strip())
+            except ValueError:
+                continue
+    return data
+
+
+def write_baseline(root: Path, counts: dict[str, int]) -> Path:
+    path = root / BASELINE_FILE
+    path.parent.mkdir(parents=True, exist_ok=True)
+    body = [
+        "# doc-path-audit baseline — the ratchet DESCENDS only.",
+        "# Regenerate with: python3 scripts/cos_doc_path_audit.py --write-baseline",
+        "# Raising any number here is not a fix. Lower it as findings are resolved.",
+        "# A number ABOVE reality is a cushion that accepts new debt while",
+        "# reporting '0 new' — the gate fails on that too.",
+        "",
+    ]
+    body += [f"{key}: {counts[key]}" for key in RATCHET_KEYS]
+    path.write_text("\n".join(body) + "\n", encoding="utf-8")
+    return path
+
+
+def ratchet_verdict(counts: dict[str, int], baseline: dict[str, int]) -> tuple[dict, dict]:
+    # `.get(key, 0)` on both sides: a bucket added after the baseline was written
+    # must read as new debt, never crash the gate.
+    over = {k: (counts[k], baseline.get(k, 0)) for k in RATCHET_KEYS if counts[k] > baseline.get(k, 0)}
+    under = {k: (counts[k], baseline.get(k, 0)) for k in RATCHET_KEYS if counts[k] < baseline.get(k, 0)}
+    return over, under
@@ def build_parser() -> argparse.ArgumentParser:
     parser.add_argument("--fail-on", default="", help="Comma list: missing, missing-exact, missing-glob, legacy, legacy-runtime, ambiguous.")
     parser.add_argument("--write-report", help="Write a Markdown report to this path.")
+    parser.add_argument("--ratchet", action="store_true", help="Fail (exit 1) when any code.surface bucket differs from manifests/doc-path-baseline.yaml, in EITHER direction.")
+    parser.add_argument("--write-baseline", action="store_true", help="Pin today's counts as the baseline (ratchet down only).")
     return parser
@@ def main(argv: Sequence[str] | None = None) -> int:
     args = build_parser().parse_args(argv)
     root = Path(args.project_dir).resolve()
     payload = audit(root)
+    counts_by_bucket = ratchet_counts(payload)
+
+    if args.write_baseline:
+        written = write_baseline(root, counts_by_bucket)
+        print(f"doc-path-audit: baseline written to {written.relative_to(root)}")
+        return 0
 
     if args.write_report:
@@
     fail_categories = parse_fail_on(args.fail_on)
-    return 2 if should_fail(payload, fail_categories) else 0
+    if should_fail(payload, fail_categories):
+        return 2
+
+    if args.ratchet:
+        baseline = load_baseline(root)
+        if not baseline:
+            print(
+                "doc-path-audit: --ratchet requested but no baseline — "
+                f"run --write-baseline to pin today's counts into {BASELINE_FILE}.",
+                file=sys.stderr,
+            )
+            return 1
+        over, under = ratchet_verdict(counts_by_bucket, baseline)
+        for key, (now, base) in sorted(over.items()):
+            print(f"FAIL new doc-path debt: {key}: {now} > baseline {base}", file=sys.stderr)
+        for key, (now, base) in sorted(under.items()):
+            print(
+                f"FAIL baseline above reality (cushion): {key}: {now} < baseline {base} "
+                "— lower it with --write-baseline",
+                file=sys.stderr,
+            )
+        if over or under:
+            return 1
+        return 0
+
+    if payload.get("status") == "fail":
+        # A 'fail' payload that exits 0 is the exact shape of a false gate.
+        # Say so on stderr instead of letting a caller read the exit code as a verdict.
+        print(
+            "doc-path-audit: ADVISORY RUN — status=fail but neither --fail-on nor "
+            "--ratchet was given; this exit code is NOT a verdict.",
+            file=sys.stderr,
+        )
+    return 0
```

`--fail-on` conserva exit 2 intacto, así que `tests/audit/test_doc_path_references.py`
sigue pasando sin tocarlo. El ratchet estrena exit 1, separado.

**Baseline honesto de hoy** (`manifests/doc-path-baseline.yaml`, archivo nuevo — o
generarlo con `--write-baseline`, que produce exactamente esto):

```yaml
# doc-path-audit baseline — the ratchet DESCENDS only.
# Regenerate with: python3 scripts/cos_doc_path_audit.py --write-baseline
# Raising any number here is not a fix. Lower it as findings are resolved.
# A number ABOVE reality is a cushion that accepts new debt while
# reporting '0 new' — the gate fails on that too.

missing-exact.P0: 29
missing-exact.P1: 233
missing-exact.P2: 26
missing-exact.P3: 40
missing-exact.P4: 0
missing-glob.P0: 13
missing-glob.P1: 4
missing-glob.P2: 0
missing-glob.P3: 4
missing-glob.P4: 0
legacy-reference.P0: 0
legacy-reference.P1: 0
legacy-reference.P2: 0
legacy-reference.P3: 0
legacy-reference.P4: 0
ambiguous.P0: 79
ambiguous.P1: 39
ambiguous.P2: 169
ambiguous.P3: 619
ambiguous.P4: 1
```

Y el registro que lo hace correr — sumar al test de auditoría existente, no un
gate nuevo en pre-commit (razón en §5):

```diff
--- a/tests/audit/test_doc_path_references.py
+++ b/tests/audit/test_doc_path_references.py
@@
     assert payload["counts"]["legacy_runtime"] == 0
     assert "missing_exact" in payload["counts"]
     assert "missing_glob" in payload["counts"]
+
+
+@pytest.mark.audit
+def test_doc_path_debt_does_not_grow_and_baseline_is_not_a_cushion() -> None:
+    """The ratchet fails in BOTH directions: new debt, and a baseline above reality."""
+    proc = subprocess.run(
+        ["python3", "scripts/cos_doc_path_audit.py", "--json", "--ratchet"],
+        cwd=REPO,
+        text=True,
+        stdout=subprocess.PIPE,
+        stderr=subprocess.PIPE,
+        timeout=120,
+    )
+    assert proc.returncode == 0, proc.stderr
```

### 4.3 `scripts/documentation_truth_audit.py` — implementar la staleness que el manifest declara

El manifest dice, línea 10: `block: required claim is missing, contradicted, or backed by a missing/stale source report`.
El script implementa *missing* y *contradicted*. **Stale no existe en el código.**

```diff
--- a/scripts/documentation_truth_audit.py
+++ b/scripts/documentation_truth_audit.py
@@
 import argparse
 import json
 import re
 import sys
 from dataclasses import asdict, dataclass
-from datetime import datetime, timezone
+from datetime import datetime, timedelta, timezone
 from pathlib import Path
@@
 def json_summary(root: Path, report: str) -> dict[str, Any]:
     data = read_json(root / report)
     summary = data.get("summary", {}) if isinstance(data, dict) else {}
     status = data.get("status") or data.get("gate", {}).get("status")
     return {"status": status, "summary": summary}
+
+
+def report_age_days(root: Path, report: str) -> float | None:
+    """Age of a generated report, preferring its own `generated_at` over mtime.
+
+    mtime alone is not evidence: a checkout, a rebase or a `touch` resets it
+    without regenerating anything. `generated_at` is written by the producing
+    audit, so it says when the FACTS were measured. mtime is the fallback for
+    reports that do not carry the field.
+    """
+    path = root / report
+    if not path.exists():
+        return None
+    stamp = None
+    if path.suffix == ".json":
+        data = read_json(path)
+        if isinstance(data, dict):
+            stamp = data.get("generated_at")
+    if isinstance(stamp, str):
+        try:
+            when = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
+            if when.tzinfo is None:
+                when = when.replace(tzinfo=timezone.utc)
+            return (datetime.now(timezone.utc) - when).total_seconds() / 86400.0
+        except ValueError:
+            pass
+    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
+    return (datetime.now(timezone.utc) - mtime).total_seconds() / 86400.0
@@ def audit(root: Path, manifest_path: Path) -> list[TruthRow]:
     manifest = read_yaml(manifest_path)
+    default_max_age = manifest.get("default_max_age_days")
     rows: list[TruthRow] = []
     for claim_id, claim in sorted((manifest.get("claims") or {}).items()):
         severity = str(claim.get("severity") or "medium")
+        max_age = claim.get("max_age_days", default_max_age)
         source_reports = [str(p) for p in claim.get("source_reports", [])]
@@
             else:
                 rows.append(TruthRow(claim_id, "source_report_exists", "pass", severity, report, "Required source report exists", [report], "keep report generated"))
+            # Staleness — the half of `status_policy` that had no implementation.
+            if max_age is None:
+                rows.append(TruthRow(claim_id, "source_report_freshness", "warn", severity, report,
+                                     "No max_age_days declared: freshness is NOT checked for this claim",
+                                     [report], "declare max_age_days on the claim or default_max_age_days in the manifest"))
+            else:
+                age = report_age_days(root, report)
+                if age is None:
+                    continue
+                if age > float(max_age):
+                    rows.append(TruthRow(claim_id, "source_report_freshness", "block", severity, report,
+                                         f"Source report is stale: {age:.1f}d old, max {max_age}d",
+                                         [f"age_days:{age:.1f}", f"max_age_days:{max_age}"],
+                                         "regenerate the source report, or the claim is asserting facts nobody measured"))
+                else:
+                    rows.append(TruthRow(claim_id, "source_report_freshness", "pass", severity, report,
+                                         f"Source report is fresh: {age:.1f}d old, max {max_age}d",
+                                         [f"age_days:{age:.1f}"], "keep report regenerated"))
```

`warn` no bloquea (`build_report` sólo cuenta `block`), así que el parche entra
**verde** y la staleness queda visible como fila hasta que el operador declare el
límite. Ese es el interruptor con el que se prende, por claim:

```diff
--- a/manifests/documentation-truth-claims.yaml
+++ b/manifests/documentation-truth-claims.yaml
@@
 status_policy:
   pass: all required docs, phrases, source reports, and generated blocks match current facts
   warn: advisory-only claim has weak evidence but no contradiction
   block: required claim is missing, contradicted, or backed by a missing/stale source report
+
+# Freshness contract (ADR-277). A claim without max_age_days emits a `warn` row
+# saying so — an undeclared limit is visible debt, not a silent pass.
+# default_max_age_days: 30   # uncomment only after regenerating the reports below
```

**Deuda que destapa el día que se prenda** (medida con `git log -1 --format=%ai`):

| Reporte fuente | Último commit | Edad al 2026-08-15 |
|---|---|---|
| `docs/06-Daily/reports/primitive-projection-fidelity-latest.json` | 2026-06-16 | 60 d |
| `docs/06-Daily/reports/primitive-authority-latest.json` | 2026-06-16 | 60 d |
| `docs/06-Daily/reports/documentation-truth-latest.json` | 2026-06-16 | 60 d |
| `docs/06-Daily/reports/primitive-readiness-ledger-scripts-latest.json` | 2026-07-20 | 26 d |

Con `default_max_age_days: 30` van a rojo 3 de las 5 claims. Con `60` no bloquea
ninguna hoy y aprieta sola en un par de días. Recomendación en §5.

**Bug adicional del mismo archivo, sin parche acá:** el bloque de nivel superior
`source_reports:` del manifest (`consumer_projection` / `primitive_authority` /
`acc`, con `required: true|false`) **nunca se lee**: `audit()` sólo itera
`manifest["claims"]`. Es una declaración muerta que da sensación de cobertura.
O se cablea o se borra — decisión del operador, no la resolvió este informe.

### 4.4 `scripts/cos-scope-projection-audit` — `projection_total: 0` tiene que decir si midió

No es un gate falso: `--strict` devuelve 2 correctamente, mide 1449 primitivas y
688/688 proofs, y **la mitad de proyección sí se mide** en CI (§5). El defecto es
que el payload no distingue "medí la proyección y no hay fugas" de "no medí nada".
Todo consumidor del JSON lee `projection_total: 0` como lo primero.

```diff
--- a/scripts/cos-scope-projection-audit
+++ b/scripts/cos-scope-projection-audit
@@ def build_report(repo, projection_root=None, run_install_smoke=False):
+def build_report(repo: Path, projection_root: Path | None = None, run_install_smoke: bool = False,
+                 require_projection: bool = False) -> dict[str, Any]:
@@
     projection_rows: list[dict[str, Any]] = []
     if target:
         projection_rows = _scan_installed_projection(target)
@@
+    else:
+        # `projection_total: 0` is ambiguous: it reads identically whether the
+        # projection was scanned and clean, or never scanned at all. Say which.
+        findings.append(
+            Finding(
+                code="projection-not-measured",
+                severity="block" if require_projection else "warn",
+                artifact="(projection)",
+                scope=None,
+                message="No projection root scanned: pass --projection-root or --run-install-smoke",
+                evidence={"run_install_smoke": run_install_smoke},
+            )
+        )
@@
     summary = {
         "source_total": len(rows),
         "source_by_scope": by_scope,
+        "projection_measured": bool(target),
         "projection_total": len(projection_rows),
         "projection_by_scope": projection_by_scope,
@@ def main(argv):
     parser.add_argument("--strict", action="store_true", help="Exit 2 when block findings exist")
+    parser.add_argument("--require-projection", action="store_true", help="Treat an unmeasured projection as a block finding, not a warning")
     parser.add_argument("--no-write", action="store_true")
     args = parser.parse_args(argv)
 
     repo = args.repo_root.resolve()
-    report = build_report(repo, args.projection_root.resolve() if args.projection_root else None, args.run_install_smoke)
+    report = build_report(
+        repo,
+        args.projection_root.resolve() if args.projection_root else None,
+        args.run_install_smoke,
+        args.require_projection,
+    )
```

Y donde la proyección **sí** se mide, exigirlo — así un `--run-install-smoke` que
falle en silencio (devuelve `target=None` cuando el install da != 0) deja de leerse
como verde:

```diff
--- a/.github/workflows/scope-portability.yml
+++ b/.github/workflows/scope-portability.yml
@@
           scripts/cos-scope-projection-audit \
             --repo-root . \
             --run-install-smoke \
+            --require-projection \
             --strict \
             --json \
             --no-write
```

```diff
--- a/scripts/cos-ci-local.sh
+++ b/scripts/cos-ci-local.sh
@@
     python3 "$REPO_ROOT/scripts/cos-scope-projection-audit" \
-      --repo-root "$REPO_ROOT" --run-install-smoke --strict --json --no-write >/dev/null && \
+      --repo-root "$REPO_ROOT" --run-install-smoke --require-projection --strict --json --no-write >/dev/null && \
```

`.githooks/pre-commit` queda **sin tocar**: ahí la invocación source-only es
deliberada y está documentada en el propio hook ("This is the cheap source-level
gate... The install/projection smoke runs in `scripts/cos-ci-local.sh quick`").
Con el parche, ese run pasa a emitir un `warn` visible en el JSON en vez de un
cero mudo, y sigue sin bloquear.

## 5. Baseline vs interruptor, por gate

| Gate | Recomendación | Por qué |
|---|---|---|
| `cos_doc_path_audit.py` | **Baseline con ratchet** (§4.2), forma copiada de `scripts/scope_closure_gate.py` | 349 hallazgos bloqueables, de los que 237 son `tests/` construyendo paths dentro de `tmp_path` — ruido, no deuda. Un interruptor `--fail-on missing` bloquea todo commit desde el minuto siguiente por hallazgos que no son bugs. El ratchet por `code.surface` deja bajar `P0` (42) sin esperar a limpiar `P1` (237), y falla también hacia abajo, así que nadie deja el colchón. |
| `check_entrypoint_adr_links.py` | **Interruptor** (fix de una línea), atómico con el arreglo de contenido | No hay deuda que amortizar: 114 links, un solo patrón, un solo arreglo mecánico, tres archivos. Un baseline acá sería inventar deuda permanente para algo que se arregla de una. Requisito: mismo commit que el contenido. |
| `documentation_truth_audit.py` | **Interruptor por claim**, en dos pasos | Paso 1: mergear el parche con `max_age_days` ausente → filas `warn`, cero bloqueo, la deuda queda escrita. Paso 2: regenerar los 3 reportes del 2026-06-16 y recién ahí descomentar `default_max_age_days`. Al revés (prender primero) es rojo el primer día por reportes viejos, no por documentación falsa — y el arreglo barato sería subir el número, o sea el colchón otra vez. |
| `cos-scope-projection-audit` | **Ninguno de los dos: señal** | Su exit code ya es coherente y la proyección ya se mide donde importa. Lo único que falta es que el payload diga cuándo NO midió. `--require-projection` sólo en las lanes que sí la miden. |

Sobre reusar la forma de `scope_closure_gate.py`: sí, conviene, y el parche §4.2
la copia deliberadamente — mismo doble sentido de falla, mismo `.get(k, 0)` a
ambos lados para que un bucket nuevo lea como deuda y no como crash, mismo
`--write-baseline`. Advertencia: **`scope_closure_gate.py` no está registrado en
ningún lado**. `grep -rn "scope_closure_gate" .githooks/ scripts/*.sh .github/workflows/ tests/`
no devuelve nada. Es un gate correcto que nadie corre — inventario, por la pregunta 3.
El precedente sirve como forma, no como ejemplo de gate vivo.

## 6. Correcciones a las premisas del encargo

1. **`.githooks/` SÍ existe en el working tree y está trackeado.** Siete hooks,
   `pre-commit` ejecutable de 16 KB, y `git config core.hooksPath` = `.githooks`.
   Los gates corren de verdad. (`git ls-files .githooks` lista los 7.)
2. **No son "los dos gates de `.githooks/pre-commit`" llamando al mismo script.**
   Son dos scripts distintos dentro del mismo `if [ -n "$staged_primitives" ]`:
   `cos-scope-both-portability-audit` y `cos-scope-projection-audit`. Y sólo
   disparan cuando hay algo staged bajo `hooks/ scripts/ lib/ skills/ rules/ templates/`.
3. **2733 → 2779 hallazgos.** El número se movió (mediciones distintas, árbol
   distinto). El desglose real: `missing_exact` 328, `missing_glob` 21,
   `ambiguous` 907, `historical_allowed` 1385, `project_template` 138,
   `legacy_reference` 0. Sólo 349 son bloqueables por `--fail-on missing`.
4. **El desempate del caso 2 lo gana el primer juez** (ver §3). El segundo
   reportó un estado imposible: `return 2` sólo se alcanza dentro de `if missing:`.
5. **El "arreglo de una línea" del caso 2 no es de una línea.** Además del
   resolver hay que corregir la aserción del test de contrato, que codifica el bug
   textualmente, y coordinar con el arreglo de contenido o quedan 114 rojos.
6. **El caso 3 no es sólo "de alcance".** El manifest declara `missing/stale` y el
   script no tiene ninguna noción de tiempo — ni `mtime`, ni `generated_at`, ni
   `git log`. Y hay un segundo agujero no reportado: el bloque `source_reports:`
   de nivel superior del manifest nunca se lee.
7. **El caso 4 no es un gate falso.** La mitad de proyección **sí se mide**, con
   `--run-install-smoke`, en `.github/workflows/scope-portability.yml` (workflow
   habilitado, no `.disabled`), en `scripts/cos-ci-local.sh:374` y en
   `scripts/cos-status.sh:252`. El pre-commit corre a propósito la variante barata
   source-only y lo dice en un comentario. Defecto real: `projection_total: 0` no
   distingue "no hay fugas" de "no miré".
8. **El registro más débil no estaba reportado:**
   `tests/audit/test_doc_path_references.py::test_current_repo_doc_path_references_pass_strict_gate`
   se llama "strict gate" y corre `--fail-on legacy-runtime`. `legacy_runtime` vale
   0 y viene de `legacy_reference`, que también vale 0 en todo el repo. Es un
   supresor que no suprime nada: verde estructural mientras pasan 349 hallazgos.
9. **`scripts/scope_closure_gate.py`, el precedente propuesto, no está registrado
   en ningún ejecutor.** Falla la pregunta 3 igual que los demás.

## Anexo — comandos de reproducción

```bash
# Caso 1
python3 scripts/cos_doc_path_audit.py --project-dir . --json > /tmp/dpa.json; echo "EXIT=$?"
python3 -c "import json;p=json.load(open('/tmp/dpa.json'));print(p['status'],p['summary'],p['counts'])"

# Caso 2
python3 scripts/check_entrypoint_adr_links.py; echo "EXIT=$?"
ls docs/00-MOCs/entrypoints/adrs   # No such file or directory

# Caso 3
python3 scripts/documentation_truth_audit.py --project-dir . --no-write --fail-on-block; echo "EXIT=$?"
for f in docs/06-Daily/reports/primitive-projection-fidelity-latest.json \
         docs/06-Daily/reports/primitive-authority-latest.json; do
  git log -1 --format="%ai  $f" -- "$f"; done

# Caso 4
python3 scripts/cos-scope-projection-audit --repo-root . --strict --json --no-write \
  | python3 -c "import json,sys;p=json.load(sys.stdin);print(p['summary']);print('projection_root',p['projection_root'])"

# Registros
git config core.hooksPath && git ls-files .githooks
grep -rn "cos-scope-projection-audit" .githooks/ scripts/*.sh .github/workflows/
grep -rn "scope_closure_gate" .githooks/ scripts/*.sh .github/workflows/ tests/   # vacío
```

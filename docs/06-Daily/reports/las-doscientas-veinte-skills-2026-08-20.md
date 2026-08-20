<!-- SCOPE: os-only -->
# Las doscientas veinte skills: quien puede invocarlas

**Fecha:** 2026-08-20 · **HEAD medido:** `bba24afba` · **Instrumento:** `scripts/audit_skill_reachability.py` (read-only, exit 0 sin hallazgos / 1 con inalcanzables / 2 error)

```bash
git rev-parse --short HEAD                       # bba24afba
.venv/bin/python3 scripts/audit_skill_reachability.py > /tmp/reach.json ; echo $?   # 1
```

---

## Veredicto en una linea

El miedo era en gran medida infundado **en el eje de alcanzabilidad**: de 200 skills distintas, **197 tienen al menos una via real de invocacion**. Solo **3 son inalcanzables**. Pero el eje de *uso* no se puede contestar, porque **el instrumento que deberia observarlo esta practicamente muerto**: `skill-invocations.jsonl` tiene **7 filas en 23 dias**, y **3 de esas 7 son de una skill que ni siquiera vive en este repo**.

| Cubeta | N | % |
|---|---|---|
| ALCANZABLE Y USADA | 51 | 25,5% |
| ALCANZABLE, SIN USO OBSERVADO | 146 | 73,0% |
| INALCANZABLE | 3 | 1,5% |
| **Total (nombres distintos)** | **200** | |

```bash
.venv/bin/python3 -c "import json,collections;d=json.load(open('/tmp/reach.json'));print(collections.Counter(r['bucket'] for r in d['rows']))"
# Counter({'REACHABLE_NO_USE': 146, 'REACHABLE_USED': 51, 'UNREACHABLE': 3})
```

---

## Correcciones a las premisas del encargo

**1. No son 220 skills, son 200.** `220` es el conteo de archivos `SKILL.md` versionados; 20 de esos son la MISMA skill proyectada a otro arnes. `agent-run-supervision` aparece 5 veces (`skills/`, `.claude/skills/`, `.codex/skills/`, `.cognitive-os/skills/`, `.cognitive-os/skills/cos/`); `epistemic-review` y `so-impact-eval` idem.

```bash
git ls-files '**/SKILL.md' | grep -v 'node_modules\|.claude/plugins/' | wc -l   # 220 archivos
# nombres distintos (dirname del padre): 200
```

**2. En disco hay 280 `SKILL.md`, no 220.** 60 no estan versionados: 23 en `.cognitive-os/skills/`, 23 + 6 en `.cognitive-os/external-source-cache/gentle-ai/`, 8 en `.agents/skills/`. Quedan fuera de este informe (el encargo pidio las versionadas) pero son masa real que el arnes puede ver.

```bash
find . -name SKILL.md -not -path '*/node_modules/*' -not -path './.claude/plugins/*' -not -path './.git/*' | wc -l   # 280
```

**3. "Las skills no tienen instrumento de vitalidad" es falso — tienen once, y casi todos vacios o con basura.** Existen `skill-invocations`, `skill-usage`, `skill-routing`, `skill-metrics`, `skill-suggestion`, `skill-feedback`, `skill-bypass`, `skill-drift`, `skill-archive`, `skill-frontmatter-warnings`, `skill-synthesis-queue`. El problema no es la ausencia de instrumento sino que el unico que mide *invocacion real* registro 7 eventos, y que `skill-metrics.jsonl` / `skill-feedback.jsonl` guardan en el campo `skill` valores como `"unknown-agent"` y `"matias"` — no son nombres de skill.

```bash
wc -l .cognitive-os/metrics/skill-invocations.jsonl   # 7
head -1 .cognitive-os/metrics/skill-feedback.jsonl
# {"timestamp":"2026-07-03T20:15:20Z","skill":"matias","success":true}
```

**4. La skill mas invocada del sistema no esta entre las 220.** `encargo-refutable` tiene 3 de las 7 invocaciones registradas y NO es una skill de este repo: vive en el perfil global (`~/.claude/skills/encargo-refutable/`). Si el operador decidiera "que tercio sobrevive" mirando solo el repo, borraria en base a un ranking que no incluye a la ganadora.

```bash
ls -la ~/.claude/skills/encargo-refutable/    # existe
git ls-files | grep -c encargo-refutable      # 3  (son referencias en docs, no la skill)
```

**5. Casi cayo un cero falso: `hook-timing.jsonl` no cubre la historia, cubre 2h35m.** `grep -c skill-invocation-logger hook-timing.jsonl` da **0** — y la lectura ingenua seria "el logger nunca dispara". El archivo arranca a las 15:45 y termina a las 18:20 del mismo dia. El logger si funciona (escribio una fila ayer). El cero mide la ventana, no el hook.

```bash
head -1 .cognitive-os/metrics/hook-timing.jsonl | cut -c1-40   # 2026-08-20T15:45:08Z
tail -1 .cognitive-os/metrics/hook-timing.jsonl | cut -c1-40   # 2026-08-20T18:20:39Z
wc -l .cognitive-os/metrics/hook-timing.jsonl                  # 16229 filas en 2h35m
```

**6. La primera version de mi propio instrumento reporto 0 inalcanzables — y estaba mal.** Contaba "mencionado en algun `.md`" como via de invocacion; con `skills/CATALOG.md` en el barrido, *toda* skill tiene mencion y el resultado es 0 por construccion. La sonda daba el mismo resultado en las dos ramas del contrafactico. Corregido: solo cuentan como via dura la **proyeccion de arnes** y la **entrada en la tabla del router**; la mencion textual quedo como dato informativo (`refs`), no como via. Esa correccion es la que destapo las 3.

---

## Control positivo (antes de creerle a cualquier cero)

Sembrado con las skills que la telemetria muestra como mas activas. El metodo las encuentra:

| skill | evidencia sembrada | mi metodo dice |
|---|---|---|
| `run-tests` | 72 sugerencias en `skill-suggestion.jsonl` | `REACHABLE_USED`, vias: claude-projection + cos-projection + router-table |
| `hook-timing` | 1 invocacion real + 32 sugerencias | `REACHABLE_USED` |
| `repo-forensics` | 16 sugerencias + 12 bypasses | `REACHABLE_USED` |
| `agent-run-supervision` | 1 invocacion real (ayer 04:15) + 14 sugerencias | `REACHABLE_USED` |
| `encargo-refutable` | 3 invocaciones reales | **NOT IN UNIVERSE** — correcta: no es del repo |

```bash
grep -o '"skill_name": "[^"]*"' .cognitive-os/metrics/skill-suggestion.jsonl | sort | uniq -c | sort -rn | head -5
cat .cognitive-os/metrics/skill-invocations.jsonl
```

El ultimo caso es el control negativo que faltaba: el metodo **no** inventa una fila para algo que no esta en el universo medido.

---

## 1. INALCANZABLES (3)

Ninguna de las tres tiene proyeccion de arnes (`.claude/skills/<n>/SKILL.md` no existe) ni entrada en la tabla del router. Nadie puede invocarlas, ni por accidente.

| skill | ruta | via que le falta | diagnostico |
|---|---|---|---|
| `canonical-event-emitter` | `skills/__contracts__/canonical-event-emitter/SKILL.md` | proyeccion + router | **Vive un nivel demasiado abajo.** El router hace `root.glob("*/SKILL.md")` sobre `skills/`; esta esta en `skills/__contracts__/<n>/SKILL.md`, dos niveles. **No es deuda: es correcta asi.** Su consumidor es `tests/integration/test_harness_agnostic_skill_run.py`, que la carga por ruta. Coincidencia, no hallazgo. |
| `auto-bash-agent-bash-9c6b89` | `skills/experimental/auto-bash-agent-bash-9c6b89/SKILL.md` | proyeccion + router | Mismo motivo estructural (`skills/experimental/<n>/`), pero aca **si es el estado deseado**: su propia descripcion dice "keep it sandboxed until promoted or deleted". El sandbox funciona: es inalcanzable a proposito. |
| `sample` | `examples/sample-skill/skills/sample/SKILL.md` | proyeccion + router | Fixture del package manager. `examples/` no esta en ningun search root. Correcto. |

```bash
for n in canonical-event-emitter auto-bash-agent-bash-9c6b89 sample; do
  echo -n "$n: "; ls .claude/skills/$n 2>&1 | head -1
done
sed -n '432,460p' cos_lib/skill_router.py   # search_roots + root.glob("*/SKILL.md")
```

**Los 3 hallazgos caros no son caros.** Los tres son inalcanzables por diseño y los tres tienen consumidor o justificacion. **Refuto la hipotesis de fondo del encargo: en skills no hay un tercio muerto por desconexion.** Lo que hay es otra cosa (seccion 3).

### Casi-huerfanas: 2 mas que merecen ojo

`docs-to-artifact` y `portability-work` estan proyectadas (el Skill tool las ve) pero **no estan en la tabla del router y no las menciona ni un archivo del repo fuera de su propio directorio**. Alcanzables solo si el operador se acuerda del nombre exacto.

```bash
.venv/bin/python3 -c "import json;d=json.load(open('/tmp/reach.json'));print([r['name'] for r in d['rows'] if r['ref_count']==0])"
# ['docs-to-artifact', 'portability-work']
```

Y 8 estan proyectadas pero fuera del router — el hook de sugerencia nunca las va a proponer: `caveman-compress`, `component-classifier`, `cost-predictor`, `docs-to-artifact`, `portability-work`, `repo-map`, `test-efficiency`, `test-matrix`.

---

## 2. ALCANZABLE Y USADA (51)

"Usada" = aparece con nombre propio en al menos un jsonl de skills. Ojo con la calidad de la evidencia: **48 de las 51 califican solo por `skill-suggestion.jsonl`**, que registra lo que el router *propuso*, no lo que se *ejecuto*. Solo 3 tienen invocacion real registrada: `hook-timing`, `agent-run-supervision` y (fuera del repo) `encargo-refutable`.

Top 12 por señal total:

| skill | total | desglose |
|---|---|---|
| `run-tests` | 72 | 72 sugeridas |
| `hook-timing` | 34 | 1 invocada, 1 usada, 32 sugeridas |
| `repo-forensics` | 28 | 16 sugeridas, 12 bypass |
| `skill-creator` | 22 | 22 sugeridas |
| `sdd-verify` | 19 | 18 sugeridas, 1 metrics |
| `agent-run-supervision` | 16 | 1 invocada, 1 usada, 14 sugeridas |
| `deep-research` | 16 | 16 sugeridas |
| `graphify-query` | 14 | 14 sugeridas |
| `sdd-apply` | 13 | 10 sugeridas, 3 metrics |
| `red-team` | 12 | 10 sugeridas, 2 bypass |
| `branch-worktree-closure` | 10 | 10 sugeridas |
| `adr-tombstone` | 8 | 4 sugeridas, 4 bypass |

Cobertura del router en la practica: **56 nombres distintos sugeridos alguna vez, sobre 208 entradas en la tabla — 27%.**

```bash
grep -o '"skill_name": "[^"]*"' .cognitive-os/metrics/skill-suggestion.jsonl | sort -u | wc -l   # 56
.venv/bin/python3 -c "import json;print(json.load(open('/tmp/reach.json'))['router_table_size'])"  # 208
```

---

## 3. ALCANZABLE, SIN USO OBSERVADO (146) — y el patron

Esto **no** es "146 muertas". De las 146:
- **141** tienen proyeccion en `.claude/skills/` (el Skill tool las carga).
- **138** estan en la tabla del router (el hook puede sugerirlas).
- **144** tienen al menos una referencia textual en el repo.

La via existe y funciona. Lo que no hay es ocasion registrada — y el registro tiene 636 filas de sugerencias en 71 dias contra ~2 años-agente de trabajo.

### El patron: una importacion en bloque de un solo dia

| ubicacion canonica | sin uso |
|---|---|
| `skills/` | 80 |
| `packages/*/skills/` | 60 |
| `.codex/skills/` | 6 |

**Todo `packages/*/skills/` nacio en una sola tanda: 72 de sus 75 skills se agregaron el 2026-03-28.** De esas 75, **60 no tienen uso observado, y 58 de esas 60 son de esa tanda** (las otras dos: `review-output` 2026-05-01, `plan-chore` 2026-06-12).

```bash
# la tanda completa (75 skills de packages/)
for p in $(git ls-files 'packages/*/skills/*/SKILL.md'); do
  git log --diff-filter=A --format=%ad --date=short -1 -- "$p"
done | sort | uniq -c | sort -rn | head
#   72 2026-03-28
#    1 2026-06-12
#    1 2026-05-01
#    1 2026-04-24

# el subconjunto sin uso: ver el anexo, columna "nace" + "ubicacion canonica"
grep ' | packages/' <anexo>   # 60 filas, 58 con fecha 2026-03-28
```

Distribucion de nacimiento, sin uso vs usadas:

| mes de alta | sin uso | usadas | tasa de uso |
|---|---|---|---|
| 2026-03 | 75 | 20 | 21% |
| 2026-04 | 45 | 11 | 20% |
| 2026-05 | 21 | 18 | **46%** |
| 2026-06 | 5 | 2 | 29% |

El patron no es "les falta un campo del frontmatter" (140 de 146 tienen `routing_patterns`/`routing_intents` — la migracion ADR-174 se hizo). El patron es **de origen**: marzo y abril fueron dos tandas de alta masiva (`packages/` completo el 28/03) y esa cohorte usa la mitad que la cohorte de mayo, que se escribio de a una.

La lista completa de las 146, con fecha de alta, ubicacion y presencia en el router, esta al final.

---

## 4. Lo que este informe NO puede afirmar

- **No puede decir que 146 skills sean prescindibles.** Puede decir que ninguna dejo rastro en un registro que casi no registra. El instrumento correcto no existe todavia: `skill-invocations.jsonl` deberia tener miles de filas y tiene 7.
- **No mide el arnes Codex ni OpenCode.** `.codex/skills/` proyecta **9** de 200 (4,5%). Si Codex se usa en serio, ahi hay 191 skills inalcanzables *para ese arnes* — un informe aparte, con el mismo script y otro directorio de proyeccion.
- **No mide las 60 `SKILL.md` no versionadas** que si estan en disco.

---

## Que arreglar antes de borrar nada

1. **Arreglar el contador antes de usar el conteo.** `skill-invocation-logger.sh` esta registrado en `.claude/settings.json:570` y escribio 7 filas en 23 dias. Antes de decidir con "sin uso observado" hay que saber si son 7 invocaciones o 7 registradas de muchas. Es la misma pregunta que abrio la jornada con los hooks.
2. **Sanear `skill-metrics.jsonl` y `skill-feedback.jsonl`**: el campo `skill` contiene `"matias"`, `"unknown-agent"`. Un campo con basura da sensacion de cobertura — mismo defecto que un baseline por encima de la realidad.
3. **Las 8 fuera del router y las 2 sin ninguna referencia** son la unica lista corta accionable hoy: o entran al router, o se declaran de invocacion manual por escrito.
4. **`.codex/skills/` con 9 de 200** es una decision, no un olvido — pero hoy no esta escrita en ningun lado.

---

## Anexo: las 146 sin uso observado

| skill | nace | ubicacion canonica | en router | refs |
|---|---|---|---|---|
| `cognitive-os-init` | 2026-03-27 | `skills/cognitive-os-init/SKILL.md` | si | 22 |
| `cognitive-os-status` | 2026-03-27 | `skills/cognitive-os-status/SKILL.md` | si | 15 |
| `cognitive-os-test` | 2026-03-27 | `skills/cognitive-os-test/SKILL.md` | si | 19 |
| `compat-test` | 2026-03-27 | `skills/compat-test/SKILL.md` | si | 8 |
| `resource-governor` | 2026-03-27 | `skills/resource-governor/SKILL.md` | si | 20 |
| `sdd-continue` | 2026-03-27 | `skills/sdd-continue/SKILL.md` | si | 13 |
| `sdd-resume` | 2026-03-27 | `skills/sdd-resume/SKILL.md` | si | 11 |
| `session-manager` | 2026-03-27 | `skills/session-manager/SKILL.md` | si | 11 |
| `validate-config` | 2026-03-27 | `skills/validate-config/SKILL.md` | si | 9 |
| `audit-website` | 2026-03-28 | `packages/ecosystem-tools/skills/audit-website/SKILL.md` | si | 10 |
| `automaker-bridge` | 2026-03-28 | `packages/ecosystem-tools/skills/automaker-bridge/SKILL.md` | si | 8 |
| `batch-runner` | 2026-03-28 | `packages/sdd-compound/skills/batch-runner/SKILL.md` | si | 8 |
| `capability-snapshot` | 2026-03-28 | `packages/task-management/skills/capability-snapshot/SKILL.md` | si | 12 |
| `cognee-integration` | 2026-03-28 | `packages/ecosystem-tools/skills/cognee-integration/SKILL.md` | si | 8 |
| `cognee-search` | 2026-03-28 | `packages/ecosystem-tools/skills/cognee-search/SKILL.md` | si | 11 |
| `cognitive-os-benchmark` | 2026-03-28 | `packages/verification-audit/skills/cognitive-os-benchmark/SKILL.md` | si | 8 |
| `component-classifier` | 2026-03-28 | `skills/component-classifier/SKILL.md` | NO | 7 |
| `compose-prompt` | 2026-03-28 | `packages/context-optimization/skills/compose-prompt/SKILL.md` | si | 18 |
| `confidence-check` | 2026-03-28 | `packages/quality-gates/skills/confidence-check/SKILL.md` | si | 10 |
| `conversation-memory` | 2026-03-28 | `packages/recall-search/skills/conversation-memory/SKILL.md` | si | 10 |
| `deepeval-integration` | 2026-03-28 | `packages/ecosystem-tools/skills/deepeval-integration/SKILL.md` | si | 9 |
| `devbox-checkpoint` | 2026-03-28 | `packages/infra-lifecycle/skills/devbox-checkpoint/SKILL.md` | si | 9 |
| `document-feature` | 2026-03-28 | `packages/document-sync/skills/document-feature/SKILL.md` | si | 24 |
| `dod-check` | 2026-03-28 | `packages/quality-gates/skills/dod-check/SKILL.md` | si | 21 |
| `error-analyzer` | 2026-03-28 | `packages/skill-governance/skills/error-analyzer/SKILL.md` | si | 22 |
| `evaluate-plan` | 2026-03-28 | `packages/sdd-compound/skills/evaluate-plan/SKILL.md` | si | 11 |
| `exhaustive-prompt` | 2026-03-28 | `packages/context-optimization/skills/exhaustive-prompt/SKILL.md` | si | 29 |
| `gpu-sandbox` | 2026-03-28 | `packages/infra-lifecycle/skills/gpu-sandbox/SKILL.md` | si | 11 |
| `harness-audit` | 2026-03-28 | `packages/verification-audit/skills/harness-audit/SKILL.md` | si | 8 |
| `issue-pipeline` | 2026-03-28 | `packages/sdd-compound/skills/issue-pipeline/SKILL.md` | si | 8 |
| `jupyter-execute` | 2026-03-28 | `packages/ecosystem-tools/skills/jupyter-execute/SKILL.md` | si | 7 |
| `memu-context` | 2026-03-28 | `packages/recall-search/skills/memu-context/SKILL.md` | si | 8 |
| `metrics-calibrator` | 2026-03-28 | `packages/skill-governance/skills/metrics-calibrator/SKILL.md` | si | 19 |
| `model-optimizer` | 2026-03-28 | `packages/skill-governance/skills/model-optimizer/SKILL.md` | si | 15 |
| `nemo-guardrails` | 2026-03-28 | `packages/quality-gates/skills/nemo-guardrails/SKILL.md` | si | 15 |
| `optimize-skill` | 2026-03-28 | `packages/skill-governance/skills/optimize-skill/SKILL.md` | si | 33 |
| `pentest-self` | 2026-03-28 | `packages/quality-gates/skills/pentest-self/SKILL.md` | si | 11 |
| `persistent-agent` | 2026-03-28 | `packages/agent-lifecycle/skills/persistent-agent/SKILL.md` | si | 10 |
| `plan-bug` | 2026-03-28 | `packages/sdd-compound/skills/plan-bug/SKILL.md` | si | 14 |
| `plan-feature` | 2026-03-28 | `packages/sdd-compound/skills/plan-feature/SKILL.md` | si | 26 |
| `planning-poker` | 2026-03-28 | `packages/scope-governance/skills/planning-poker/SKILL.md` | si | 12 |
| `private-mode` | 2026-03-28 | `packages/privacy-mode/skills/private-mode/SKILL.md` | si | 47 |
| `promptfoo-integration` | 2026-03-28 | `packages/ecosystem-tools/skills/promptfoo-integration/SKILL.md` | si | 9 |
| `ragas-integration` | 2026-03-28 | `packages/ecosystem-tools/skills/ragas-integration/SKILL.md` | si | 9 |
| `readiness-check` | 2026-03-28 | `packages/quality-gates/skills/readiness-check/SKILL.md` | si | 17 |
| `recall-search` | 2026-03-28 | `packages/recall-search/skills/recall-search/SKILL.md` | si | 14 |
| `recommend-library` | 2026-03-28 | `packages/ecosystem-tools/skills/recommend-library/SKILL.md` | si | 11 |
| `release-os` | 2026-03-28 | `skills/release-os/SKILL.md` | si | 15 |
| `repair-status` | 2026-03-28 | `packages/infra-lifecycle/skills/repair-status/SKILL.md` | si | 11 |
| `research-protocol` | 2026-03-28 | `packages/scope-governance/skills/research-protocol/SKILL.md` | si | 12 |
| `resolve-blockers` | 2026-03-28 | `packages/quality-gates/skills/resolve-blockers/SKILL.md` | si | 10 |
| `resume-tasks` | 2026-03-28 | `packages/agent-lifecycle/skills/resume-tasks/SKILL.md` | si | 18 |
| `retrospective` | 2026-03-28 | `packages/agent-coordination/skills/retrospective/SKILL.md` | si | 17 |
| `sandbox-sample` | 2026-03-28 | `packages/scope-governance/skills/sandbox-sample/SKILL.md` | si | 16 |
| `scout` | 2026-03-28 | `skills/scout/SKILL.md` | si | 23 |
| `sdd-compound` | 2026-03-28 | `packages/sdd-compound/skills/sdd-compound/SKILL.md` | si | 14 |
| `secret-audit` | 2026-03-28 | `packages/ecosystem-tools/skills/secret-audit/SKILL.md` | si | 29 |
| `security-audit` | 2026-03-28 | `packages/quality-gates/skills/security-audit/SKILL.md` | si | 25 |
| `self-review` | 2026-03-28 | `packages/adaptive-workflow/skills/self-review/SKILL.md` | si | 13 |
| `semgrep-scan` | 2026-03-28 | `packages/ecosystem-tools/skills/semgrep-scan/SKILL.md` | si | 22 |
| `simulation-arena` | 2026-03-28 | `packages/dry-run-simulation/skills/simulation-arena/SKILL.md` | si | 10 |
| `smoke-test` | 2026-03-28 | `packages/verification-audit/skills/smoke-test/SKILL.md` | si | 24 |
| `squad-manager` | 2026-03-28 | `packages/agent-coordination/skills/squad-manager/SKILL.md` | si | 9 |
| `sre-agent` | 2026-03-28 | `packages/infra-lifecycle/skills/sre-agent/SKILL.md` | si | 19 |
| `strands-evals-integration` | 2026-03-28 | `packages/ecosystem-tools/skills/strands-evals-integration/SKILL.md` | si | 8 |
| `test-driven-development` | 2026-03-28 | `packages/verification-audit/skills/test-driven-development/SKILL.md` | si | 17 |
| `tool-discovery` | 2026-03-28 | `packages/ecosystem-tools/skills/tool-discovery/SKILL.md` | si | 27 |
| `trust-audit` | 2026-03-28 | `packages/verification-audit/skills/trust-audit/SKILL.md` | si | 11 |
| `verification-before-completion` | 2026-03-28 | `packages/verification-audit/skills/verification-before-completion/SKILL.md` | si | 26 |
| `vulnerability-scan` | 2026-03-28 | `skills/vulnerability-scan/SKILL.md` | si | 13 |
| `web-crawler` | 2026-03-28 | `packages/ecosystem-tools/skills/web-crawler/SKILL.md` | si | 10 |
| `webhook-trigger` | 2026-03-28 | `packages/sdd-compound/skills/webhook-trigger/SKILL.md` | si | 13 |
| `pr-review` | 2026-03-29 | `skills/pr-review/SKILL.md` | si | 23 |
| `reverse-engineer` | 2026-03-29 | `skills/reverse-engineer/SKILL.md` | si | 9 |
| `install-recommended` | 2026-03-30 | `skills/install-recommended/SKILL.md` | si | 8 |
| `caveman-compress` | 2026-04-08 | `skills/caveman-compress/SKILL.md` | NO | 9 |
| `queue-drain` | 2026-04-09 | `skills/queue-drain/SKILL.md` | si | 25 |
| `session-report-executive` | 2026-04-09 | `skills/session-report-executive/SKILL.md` | si | 11 |
| `add-hook` | 2026-04-10 | `skills/add-hook/SKILL.md` | si | 14 |
| `add-mcp` | 2026-04-10 | `skills/add-mcp/SKILL.md` | si | 7 |
| `add-rule` | 2026-04-10 | `skills/add-rule/SKILL.md` | si | 11 |
| `add-skill` | 2026-04-10 | `skills/add-skill/SKILL.md` | si | 28 |
| `analyze-improvements` | 2026-04-10 | `skills/analyze-improvements/SKILL.md` | si | 21 |
| `apply-improvements` | 2026-04-10 | `skills/apply-improvements/SKILL.md` | si | 12 |
| `bump-version` | 2026-04-10 | `skills/bump-version/SKILL.md` | si | 14 |
| `detect-stack` | 2026-04-10 | `skills/detect-stack/SKILL.md` | si | 11 |
| `generate-changelog` | 2026-04-10 | `skills/generate-changelog/SKILL.md` | si | 15 |
| `generate-config` | 2026-04-10 | `skills/generate-config/SKILL.md` | si | 10 |
| `push-release` | 2026-04-10 | `skills/push-release/SKILL.md` | si | 12 |
| `scaffold-project` | 2026-04-10 | `skills/scaffold-project/SKILL.md` | si | 10 |
| `tag-release` | 2026-04-10 | `skills/tag-release/SKILL.md` | si | 14 |
| `validate-release` | 2026-04-10 | `skills/validate-release/SKILL.md` | si | 12 |
| `audit-integrity` | 2026-04-15 | `skills/audit-integrity/SKILL.md` | si | 16 |
| `detect-patterns` | 2026-04-15 | `skills/detect-patterns/SKILL.md` | si | 8 |
| `catalog-full` | 2026-04-16 | `skills/catalog-full/SKILL.md` | si | 10 |
| `doc-review-personas` | 2026-04-21 | `skills/doc-review-personas/SKILL.md` | si | 17 |
| `domain-model` | 2026-04-21 | `skills/domain-model/SKILL.md` | si | 13 |
| `invariant-check` | 2026-04-21 | `skills/invariant-check/SKILL.md` | si | 13 |
| `llm-status` | 2026-04-21 | `skills/llm-status/SKILL.md` | si | 15 |
| `ops-runbook` | 2026-04-21 | `skills/ops-runbook/SKILL.md` | si | 11 |
| `pattern-audit` | 2026-04-21 | `skills/pattern-audit/SKILL.md` | si | 16 |
| `project-scaffold` | 2026-04-21 | `skills/project-scaffold/SKILL.md` | si | 17 |
| `risk-register` | 2026-04-21 | `skills/risk-register/SKILL.md` | si | 13 |
| `rules-export` | 2026-04-21 | `skills/rules-export/SKILL.md` | si | 15 |
| `cost-predictor` | 2026-04-23 | `skills/cost-predictor/SKILL.md` | NO | 8 |
| `docs-to-artifact` | 2026-04-23 | `.codex/skills/docs-to-artifact/SKILL.md` | NO | 0 |
| `portability-work` | 2026-04-23 | `.codex/skills/portability-work/SKILL.md` | NO | 0 |
| `repo-map` | 2026-04-23 | `.codex/skills/repo-map/SKILL.md` | NO | 9 |
| `test-contract-repair` | 2026-04-23 | `skills/test-contract-repair/SKILL.md` | si | 12 |
| `test-matrix` | 2026-04-23 | `.codex/skills/test-matrix/SKILL.md` | NO | 3 |
| `component-reality-check` | 2026-04-24 | `skills/component-reality-check/SKILL.md` | si | 15 |
| `decision-triage` | 2026-04-24 | `skills/decision-triage/SKILL.md` | si | 17 |
| `eval-repo` | 2026-04-24 | `skills/eval-repo/SKILL.md` | si | 9 |
| `phoenix-trace-ui` | 2026-04-24 | `skills/phoenix-trace-ui/SKILL.md` | si | 9 |
| `so-vs-vanilla` | 2026-04-24 | `skills/so-vs-vanilla/SKILL.md` | si | 13 |
| `docs-execution-audit` | 2026-04-30 | `skills/docs-execution-audit/SKILL.md` | si | 10 |
| `primitive-surface-reduction` | 2026-04-30 | `skills/primitive-surface-reduction/SKILL.md` | si | 10 |
| `primitive-usage-map` | 2026-04-30 | `skills/primitive-usage-map/SKILL.md` | si | 12 |
| `repair-skill` | 2026-04-30 | `skills/repair-skill/SKILL.md` | si | 11 |
| `synthesize-skill` | 2026-04-30 | `skills/synthesize-skill/SKILL.md` | si | 11 |
| `coordination-status` | 2026-05-01 | `skills/coordination-status/SKILL.md` | si | 19 |
| `review-output` | 2026-05-01 | `packages/agent-lifecycle/skills/review-output/SKILL.md` | si | 10 |
| `peer-card` | 2026-05-02 | `skills/peer-card/SKILL.md` | si | 14 |
| `preserved-wip-cleanup` | 2026-05-02 | `skills/preserved-wip-cleanup/SKILL.md` | si | 11 |
| `primitive-harvester` | 2026-05-02 | `skills/primitive-harvester/SKILL.md` | si | 17 |
| `redteam-harness` | 2026-05-02 | `skills/redteam-harness/SKILL.md` | si | 9 |
| `worktree-triage` | 2026-05-02 | `skills/worktree-triage/SKILL.md` | si | 14 |
| `vuln-remediation-flow` | 2026-05-04 | `skills/vuln-remediation-flow/SKILL.md` | si | 12 |
| `security-red-team` | 2026-05-05 | `skills/security-red-team/SKILL.md` | si | 11 |
| `agent-control` | 2026-05-06 | `skills/agent-control/SKILL.md` | si | 28 |
| `test-efficiency` | 2026-05-07 | `.codex/skills/test-efficiency/SKILL.md` | NO | 8 |
| `primitive-authoring` | 2026-05-09 | `skills/primitive-authoring/SKILL.md` | si | 23 |
| `deep-tool-research` | 2026-05-11 | `skills/deep-tool-research/SKILL.md` | si | 11 |
| `cos-install-operations` | 2026-05-12 | `skills/cos-install-operations/SKILL.md` | si | 9 |
| `cos-maintainer-operations` | 2026-05-12 | `skills/cos-maintainer-operations/SKILL.md` | si | 8 |
| `session-pending-brief` | 2026-05-12 | `skills/session-pending-brief/SKILL.md` | si | 9 |
| `wiki-ingest` | 2026-05-13 | `skills/wiki-ingest/SKILL.md` | si | 10 |
| `install-hook` | 2026-05-18 | `skills/install-hook/SKILL.md` | si | 13 |
| `install-skill` | 2026-05-18 | `skills/install-skill/SKILL.md` | si | 13 |
| `os-session-wrapup` | 2026-05-20 | `skills/os-session-wrapup/SKILL.md` | si | 10 |
| `self-improvement-loop` | 2026-05-29 | `skills/self-improvement-loop/SKILL.md` | si | 23 |
| `plan-chore` | 2026-06-12 | `packages/sdd-compound/skills/plan-chore/SKILL.md` | si | 7 |
| `artifact-workflow` | 2026-06-16 | `skills/artifact-workflow/SKILL.md` | si | 8 |
| `lean-code` | 2026-06-16 | `skills/lean-code/SKILL.md` | si | 8 |
| `skill-optimization` | 2026-06-16 | `skills/skill-optimization/SKILL.md` | si | 10 |
| `epistemic-review` | 2026-06-17 | `skills/epistemic-review/SKILL.md` | si | 9 |


# Veredictos ADOPT sin enlazar: qué pasó realmente con los 18 del 2026-05-06

**Fecha:** 2026-08-15
**Alcance:** `docs/03-PoCs/research/repo-scout/deep/` × `manifests/external-tool-adoption-freeze.yaml`
**Estado:** cerrado — 10 notas puestas, índice inverso en el manifiesto, detector con ratchet medido

---

## Resumen

El encargo era: 18 veredictos ADOPT del 2026-05-06, el operador congela la adopción
externa el 2026-05-11, 8 aterrizaron en un ADR y los otros 10 quedaron huérfanos —
poné una nota que diga "superado por el freeze".

Al recontar, tres de las cuatro premisas no se sostienen.

**El 18 es correcto.** Los otros números no.

**Nadie adoptó nada después del freeze.** Ésa era la pregunta que más valía y la
respuesta es negativa: el freeze aguantó. Todo lo que está en el código entró antes
del 2026-05-11.

**Pero 4 de los 10 sí estaban adoptados** — antes del freeze, no a pesar de él. Para
esos cuatro la nota "superado por el freeze" habría sido falsa sobre código que corre
hoy. Es exactamente el verde barato que el encargo señalaba, y era real: sin el chequeo
caso por caso, cuatro afirmaciones falsas firmadas.

**Y apareció algo que nadie pidió buscar:** el freeze se describe a sí mismo como
"mechanical kill-switch" y no es mecánico. El hook que lo aplicaría no está registrado.

---

## Lo que era falso en el encargo

| Premisa | Medición | Veredicto |
|---|---|---|
| 18 veredictos ADOPT, fechados 2026-05-06 | 18 archivos, todos `2026-05-06` | **correcta** |
| "8 de los 18 aterrizaron en un ADR" | **0 de 18** citados por slug `org/repo` en el corpus de ADRs | **falsa** |
| Los 10 restantes no tienen ADR | Cierto, pero los 18 tampoco — el corte 8/10 no existe | **falsa** |
| El freeze alcanzó a los 10 | Alcanza a 5. Cuatro ya estaban adoptados, uno es una spec | **falsa** |

El origen del error es entendible: varios reportes nombran un ADR en el cuerpo
("direct ADR-049 reference", "ADR-033 fit"). Eso es el analista argumentando que la
herramienta es relevante, no un registro de qué se decidió. Contarlo como respaldo
produce el 8.

```bash
# 0 de 18 slugs citados en cualquier ADR
cd docs/02-Decisions/adrs
for s in Aider-AI/aider HKUDS/LightRAG OSU-NLP-Group/HippoRAG SWE-agent/SWE-agent \
         stanfordnlp/dspy getzep/graphiti gepa-ai/gepa unclecode/crawl4ai \
         MemPalace/mempalace agentsmd/agents.md BeehiveInnovations/pal-mcp-server \
         NousResearch/hermes-agent affaan-m/everything-claude-code coder/agentapi \
         obra/superpowers praetorian-inc/augustus simonw/llm snyk/agent-scan; do
  echo "$(grep -rlF "$s" . 2>/dev/null | wc -l | tr -d ' ')  $s"
done
# -> 0 en las 18 líneas
```

---

## Veredicto por caso (los 10)

### Adoptados ANTES del freeze — deuda de decisión, no de adopción (4)

El freeze no los alcanza: ya estaban. Lo que falta no es permiso, es la decisión escrita.

| Repo | Aterrizó | Dónde | Comando |
|---|---|---|---|
| `unclecode/crawl4ai` | 2026-03-27 | `packages/ecosystem-tools/lib/web_crawler.py`, `requirements.txt` | `git log -S'crawl4ai' --date=short --format='%ad %h' -- requirements.txt \| tail -1` |
| `HKUDS/LightRAG` | 2026-05-08 | `cos_lib/memory_retrieval_benchmark.py` | `git log -S'memory_retrieval_benchmark' --date=short --format='%ad %h' \| tail -1` |
| `Aider-AI/aider` | 2026-05-10 | `cos_lib/repo_map.py`, `scripts/cos-repo-map` | `git log -S'repo_map' --date=short --format='%ad %h' \| tail -1` |
| `stanfordnlp/dspy` | 2026-05-10 | `cos_lib/dspy_pilot.py`, `scripts/cos-dspy-pilot` | `git log -S'dspy_pilot' --date=short --format='%ad %h' \| tail -1` |

Detalle que importa para la doctrina clean-room que cita el freeze: los cuatro son
**port de patrón o dependencia**, no código vendorizado. `cos_lib/repo_map.py` lo dice
en su propio docstring — *"Pattern-port of Aider's repo-map idea […] no Aider runtime
dependency is required"*. Y crawl4ai entró el 2026-03-27, **un mes y medio antes de que
existiera el veredicto**: el reporte del 2026-05-06 ratificó un uso que ya corría.

Asimetría de registro que queda abierta: LightRAG y crawl4ai figuran en `NOTICE.md` /
`manifests/external-tool-licenses.yaml`; aider y dspy **no**. Cuatro adopciones del
mismo lote, dos anotadas y dos no.

```bash
git grep -niE 'aider|dspy' -- NOTICE NOTICE.md manifests/external-tool-licenses.yaml
# -> solo hits en spdx-grandfather.txt (harness adapter, otro concepto)
```

### Superados por el freeze — el veredicto nunca llegó al código (5)

| Repo | Payload del veredicto | Evidencia de ausencia |
|---|---|---|
| `OSU-NLP-Group/HippoRAG` | PPR multi-hop (algorithm-only) | 0 hits fuera de `docs/` |
| `getzep/graphiti` | esquema bi-temporal (algorithm-only) | 0 hits de `bi-temporal` fuera de `docs/` |
| `gepa-ai/gepa` | optimizador reflective text-evolution | 0 hits de `gepa` fuera de `docs/` |
| `MemPalace/mempalace` | patrones de scoring/eviction | único hit: un string en un test fixture |
| `SWE-agent/SWE-agent` | forma de tool-package ACI (`tools/*`) | sólo inventariado, `proof_level: none` |

```bash
for s in HippoRAG graphiti gepa mempalace; do
  echo "$s: $(git grep -lI -i "$s" -- ':!docs/' ':!*.jsonl' | wc -l | tr -d ' ')"
done
```

### No gobernado por el freeze (1)

`agentsmd/agents.md` — el veredicto es literalmente *"ADOPT (spec only — there is no
library to vendor)"*. `AGENTS.md` está en el repo desde el 2026-04-09, un mes **antes**
del veredicto. La proyección `.ai/adapters/agents-md/` llegó el 2026-05-12, un día
después del freeze, pero `.ai/adapters/` no está en `gated_path_globs` y adherir a una
spec publicada no es vendorizar código.

**El veredicto no era lo que parecía, en 4 de 10.** La palabra ADOPT sola dice poco:
`(algorithm-only)` en LightRAG, HippoRAG y graphiti, `(spec only)` en agents.md.
Tres de ésos piden portar un algoritmo, no adoptar un repo.

---

## Hallazgo colateral: el freeze no es mecánico

`manifests/external-tool-adoption-freeze.yaml` se describe como *"Mechanical
kill-switch"* y dice que `hooks/adoption-freeze-gate.sh` bloquea los commits. El hook
existe y su lógica es correcta. **No está registrado.**

```bash
grep -c 'adoption-freeze-gate' .claude/settings.json   # -> 0
grep -c 'hooks/' .claude/settings.json                 # -> 162
grep -c 'adoption-freeze' .githooks/pre-commit         # -> 0
```

162 hooks registrados, éste no. Nada aplica el freeze. Que las 10 notas de este informe
se pudieran escribir sobre `docs/03-PoCs/research/repo-scout/deep/*.md` —una ruta que
está en `gated_path_globs`— es la demostración: el gate debería haber bloqueado este
commit y no lo hizo.

Es la misma patología ya documentada para el rate-limiter (`rules/rate-limiting.md`):
mecanismo implementado, hook sin registrar, documentación en presente. Un gate que nunca
se vio disparar da sensación de cobertura.

**No lo registré.** Es decisión del operador, no un olvido de documentación, y registrar
un gate que bloquea commits cambia lo que el operador puede hacer. Queda anotado en el
manifiesto bajo `enforcement_caveat`.

---

## Qué se cambió

**10 notas en los PoCs** (`docs/03-PoCs/research/repo-scout/deep/`), en tres textos
distintos según el caso: "veredicto superado" (5), "ya adoptado, sin ADR" (4), "spec, no
código" (1). Van arriba del cuerpo, apenas cerrado el frontmatter, que es donde el lector
ve "ADOPT" antes de nada.

El guard de `cos_lib/delete_intent.py` protege `docs/03-PoCs/research/` contra borrado.
No se borró nada; las notas son puramente aditivas y el guard no intervino.

**Índice inverso en el manifiesto del freeze** — bloque `pending_on_unfreeze`, aditivo.
`frozen: true`, `unfreeze_requires` y `gated_path_globs` quedaron intactos. Cuando el
operador cumpla las condiciones de descongelamiento, hereda ahí la lista de los 5
pendientes reales, separada de los 4 que ya están adentro.

**Detector**: `scripts/audit_adopt_verdict_linkage.py`.

---

## El detector

Miré `scripts/audit_decision_backing.py` primero, como pedía el encargo. No lo extendí:
audita *superficies de decisión* (gates que bloquean, manifiestos de política, límites de
paquete) y excluye documentos de investigación a propósito, con el criterio escrito en su
docstring. Ensanchar esa población para meter PoCs habría diluido su criterio. El nuevo
es hermano, no reemplazo, y lo dice en el encabezado.

Pregunta que responde: *¿todo veredicto ADOPT resuelve, para el que lo lee, en algo
accionable?* Linkeado = apunta al freeze, **o** algún ADR lo nombra por slug.

**Se le encontró un verde barato y se lo sacó.** La primera versión contaba cualquier
mención `ADR-NNN` en el cuerpo como respaldo, y daba `unlinked: 0` — verde perfecto, con
8 archivos que un lector sigue sin poder resolver. Ese criterio es el que genera el "8 de
18" del encargo. Sacado; el docstring explica por qué.

Ratchet en **8 = realidad medida**, sin colchón: son los 8 que esta pasada no verificó
caso por caso. Bajarlo es el objetivo; subirlo pide un motivo en esa línea.

```
$ python3 scripts/audit_adopt_verdict_linkage.py
ADOPT verdicts: 18   unlinked: 8 (ratchet 8)   dangling: 0 (ratchet 0)
EXIT=0
```

Falsificación — que el gate pueda ponerse rojo:

```bash
# sacar la nota de un PoC -> unlinked 9 > ratchet 8 -> exit 1; restaurar -> exit 0
```

Read-only, determinista, `--json` para consumo mecánico, exit 0/1/2. Se niega a correr
(exit 2) si no encuentra ADRs o si la población queda vacía — un criterio roto no debe
reportar todo verde ni todo rojo.

---

## Lo que queda abierto

1. **Cuatro adopciones sin ADR** (crawl4ai, LightRAG, aider, dspy). No escribí ADRs
   retroactivos: el motivo real no lo tomé yo y sería ficción con forma de registro. Las
   notas dicen dónde está el código y que falta la decisión. Si el operador quiere
   cerrarlo, el "por qué" está en git, no acá.
2. **aider y dspy fuera de `NOTICE` / `external-tool-licenses.yaml`**, con las otras dos
   del mismo lote adentro. Relevante para el punto 1 del `unfreeze_requires` (revisión de
   IP de las adopciones existentes): la lista que revisaría un abogado hoy está incompleta.
3. **El gate del freeze sin registrar.** Decisión del operador.
4. **Los 8 no auditados** — el ratchet los tiene contados.
5. **`freeze_reason` habla de "las 6 adopciones ya en main (ADR-260..264)"**, que son 5
   ADRs sobre cosd API, memory governance, evolve loop, tool replay y tool result
   envelope. Ninguno cita un repo de este lote. Qué son esas 6 adopciones no lo resolví;
   no era el encargo y no quise adivinar.

---

## Reproducir

```bash
python3 scripts/audit_adopt_verdict_linkage.py          # tabla + exit code
python3 scripts/audit_adopt_verdict_linkage.py --json   # salida mecánica
grep -rlE '^deep_verdict: *ADOPT' docs/03-PoCs/research/repo-scout/deep/ | wc -l   # 18
grep -rl 'Estado 2026-08-15' docs/03-PoCs/research/repo-scout/deep/ | wc -l        # 10
```

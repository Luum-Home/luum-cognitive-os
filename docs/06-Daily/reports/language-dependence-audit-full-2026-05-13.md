# Language Dependence Audit — Full Report
_Generated 2026-05-13 — post ADR-296+297 wave._
_Snapshot: `total_finding_count = 326` from `scripts/cos-language-dependence-audit --json --min-severity low`._

## Executive summary
- **326 findings** across **112 primitives** (out of ~196 total skills+rules → ~57% affected)
- **113** files scanned, **335** routing patterns inspected
- Findings represent **tech debt, not active bugs**: ADR-296 (semantic) + ADR-297 (LLM tie-breaker) already route correctly in EN/ES/PT/DE/FR/IT regardless of these patterns
- Regression gate test (`test_language_dependence_audit_does_not_regress`) caps the count at **336** — new monolingual patterns can't land silently

## Severity distribution

| Severity | Count | % |
|---|---:|---:|
| high | 0 | 0.0% |
| medium | 97 | 29.8% |
| low | 229 | 70.2% |
| **TOTAL** | **326** | 100% |

## By surface

| Surface | Total | high | medium | low |
|---|---:|---:|---:|---:|
| `skills/` | 249 | 0 | 78 | 171 |
| `rules/` | 19 | 0 | 9 | 10 |
| `packages/*/skills/` | 58 | 0 | 10 | 48 |

## By primitive type

| Type | Findings |
|---|---:|
| `skill` | 307 |
| `rule` | 19 |

## Top-25 primitives ranked by findings

Primitives with the most language-dependent patterns. Cleaning these first gives the highest leverage. Each pattern is a candidate to delete (description already covers it via semantic).

| Rank | Primitive | Findings |
|---:|---|---:|
| 1 | `run-tests` | 6 |
| 2 | `agent-stress-test` | 5 |
| 3 | `product-answer` | 5 |
| 4 | `worktree-triage` | 5 |
| 5 | `agent-control` | 4 |
| 6 | `repo-forensics` | 4 |
| 7 | `resource-governor` | 4 |
| 8 | `reverse-engineer` | 4 |
| 9 | `adversarial-review` | 4 |
| 10 | `definition-of-done` | 4 |
| 11 | `phase-aware-agents` | 4 |
| 12 | `trust-score` | 4 |
| 13 | `add-hook` | 3 |
| 14 | `add-mcp` | 3 |
| 15 | `add-rule` | 3 |
| 16 | `add-skill` | 3 |
| 17 | `adr-tombstone` | 3 |
| 18 | `agent-dashboard` | 3 |
| 19 | `analyze-improvements` | 3 |
| 20 | `audit-integrity` | 3 |
| 21 | `branch-worktree-closure` | 3 |
| 22 | `browser-task` | 3 |
| 23 | `catalog-full` | 3 |
| 24 | `code-review` | 3 |
| 25 | `cognitive-os-init` | 3 |

## Suggested cleanup batches

**Batch A — high leverage** (4 primitives, ≥5 findings each, ~21 findings total):

Sweep these primitives' SKILL.md and delete language-dependent `routing_patterns` wholesale. Keep only patterns that match explicit slash-commands, IDs, URLs, or file paths.

- `agent-stress-test` (5 findings)
- `product-answer` (5 findings)
- `run-tests` (6 findings)
- `worktree-triage` (5 findings)

**Batch B — medium leverage** (107 primitives, 2-4 findings, ~304 findings total):

Selective cleanup — review each pattern, delete the multilingual OR-chains, keep the technical literals.

- `acceptance-criteria` (3)
- `add-hook` (3)
- `add-mcp` (3)
- `add-rule` (3)
- `add-skill` (3)
- `adr-tombstone` (3)
- `adversarial-review` (4)
- `agent-control` (4)
- `agent-dashboard` (3)
- `analyze-improvements` (3)
- `audit-integrity` (3)
- `auto-refine` (3)
- `automaker-bridge` (2)
- `branch-worktree-closure` (3)
- `browser-task` (3)
- `catalog-full` (3)
- `caveman` (2)
- `caveman-es` (2)
- `code-review` (3)
- `cognee-integration` (3)
- `cognee-search` (3)
- `cognitive-os-benchmark` (3)
- `cognitive-os-init` (3)
- `cognitive-os-status` (3)
- `cognitive-os-test` (3)
- `compat-test` (3)
- `component-reality-check` (3)
- `coordination-status` (3)
- `cos-status` (3)
- `decision-triage` (3)
- _… +77 more_

**Batch C — low priority** (1 primitives, 1 finding, ~1 findings total):

Optional. Each is a single regex line. Not worth a dedicated PR — remove opportunistically when you touch the skill for another reason.

## Most repeated literals (refactor candidates)

Literal strings that appear across many findings. These are candidates for centralisation (e.g. a shared synonyms table) — but ADR-296's semantic matcher makes this unnecessary by reading the description directly. Listed for awareness only.

| Literal | Occurrences |
|---|---:|
| `skill` | 18 |
| `test` | 17 |
| `agent` | 13 |
| `audit` | 12 |
| `review` | 12 |
| `primitive` | 11 |
| `the` | 10 |
| `cognitive` | 10 |
| `check` | 10 |
| `session` | 10 |
| `sdd` | 9 |
| `config` | 8 |
| `integrat` | 7 |
| `integration` | 7 |
| `project` | 7 |
| `run` | 7 |
| `scaffold` | 7 |
| `repo` | 7 |
| `scan` | 6 |
| `status` | 6 |

## Detector language buckets

All entries show language `und` (undetermined) because the heuristic detector is intentionally conservative — adding the optional `lingua` dependency would split this into es/en/pt/de/fr but is not needed for the current gate semantics.

| Bucket | Guesses |
|---|---:|
| `und` | 967 |

## Structural risk score distribution

Internal scoring (higher = more natural-language-y). Above 4 → medium severity; 2-3 → low; ≤1 → not flagged.

| Score | Findings |
|---|---:|
| 2 | 144 |
| 3 | 85 |
| 4 | 6 |
| 5 | 74 |
| 6 | 6 |
| 7 | 5 |
| 8 | 4 |
| 9 | 2 |

## How to act on this

**Do not** try to clean all 326 in one PR — that's a 200-file blast radius and the value is small (semantic+LLM already routes correctly). Instead:

1. **Hold the line** — the regression gate (cap 336) prevents new debt landing
2. **Clean opportunistically** — when you touch a SKILL.md for another reason, delete its multilingual regex patterns and let the semantic matcher take over
3. **Validate per skill** — after deleting a pattern, run `pytest tests/unit/test_semantic_skill_matcher.py` to confirm the matcher still resolves the primitive correctly
4. **Bump the cap downward** — every few cleanup waves, lower the BASELINE constant in `tests/unit/test_semantic_skill_matcher.py::test_language_dependence_audit_does_not_regress` so the gate tightens as debt clears

## Re-running this report

```bash
scripts/cos-language-dependence-audit --json --min-severity low \
  > /tmp/lang-audit-full.json
python3 /tmp/gen_lang_report.py  # writes here
```

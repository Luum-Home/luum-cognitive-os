<!-- SCOPE: both -->
---
name: doc-review-personas
description: >
  Multi-persona adversarial review of a documentation corpus. Runs N Haiku
  sub-agents in parallel — each one reading the same docs with a different
  human-role lens (CFO, Tech Lead, Commercial, New Dev, Editor) — then
  consolidates findings into a severity-tiered report (S1/S2/S3/S4).
  Different lenses catch non-overlapping gaps; the consolidated output is a
  prioritized fix-plan, not a set of independent critiques.
version: 1.0.0
user-invocable: true
disable-model-invocation: false
auto-generated: false
last-updated: 2026-04-21
license: MIT
metadata:
  author: luum
audience: both
summary_line: "N-persona parallel doc review with severity-tiered consolidation."
model: haiku
triggers:
  - "review docs"
  - "doc review"
  - "review documentation"
  - "personas"
  - "multi-persona"
  - "hallazgos"
  - "findings from different lenses"
---

## Purpose

A single reviewer sees what a single reviewer sees. Five different reviewers,
each with a different professional bias, systematically catch different gaps.
This skill codifies a technique that has been observed empirically:

- 5 Haiku agents reviewed the same `docs/` bundle as CFO, Tech Lead,
  Commercial, New Dev, Editor.
- The CFO noticed the schedule didn't close. The Tech Lead caught an ADR
  contradiction. The Editor caught broken accents and a disagreeing number
  across two tables. The New Dev said "there's no README at repo root."
- **Overlap between lenses was under 15%.** Each persona surfaced issues the
  others missed. One-shot review would have caught maybe a third of them.

This skill packages that technique into a repeatable, provider-agnostic tool.

## Invocation

```bash
# Run the full 5-persona review over docs/
uv run python3 scripts/doc-review-personas.py --docs-dir docs/

# Pick specific lenses
uv run python3 scripts/doc-review-personas.py --docs-dir docs/ \
    --personas cfo,editor_qa

# JSON for programmatic consumption
uv run python3 scripts/doc-review-personas.py --docs-dir docs/ --json

# Dry-run (no API calls; returns a plan)
uv run python3 scripts/doc-review-personas.py --docs-dir docs/ --dry-run

# Write to file
uv run python3 scripts/doc-review-personas.py --docs-dir docs/ \
    --output-file review.md
```

Exit codes: `0` = no S1 BLOCKER, `1` = at least one S1, `2` = usage/IO error.

## Built-in Personas

| Name | Role brief summary |
|------|--------------------|
| `cfo` | Schedule closes? Monetization explicit? ROI quantified? Hidden costs? |
| `tech_lead` | Schemas match code? Open TBDs in approved docs? Docs contradict? |
| `commercial` | Differentials vs competition? Objections addressed? Proof points? |
| `new_dev_onboarding` | Root README? Working quickstart? Broken internal links? |
| `editor_qa` | Typos, tildes, broken links, numbers that disagree across sections |

All built-in personas are **domain-agnostic**. They adapt to any project's
docs (fintech, crypto, internal tooling, SaaS pitch deck, etc.). If a project
needs a domain-specific reviewer (e.g. "regulator" for a bank), extend
`lib/persona_library.py`.

## Severity Tiers

Per `rules/adversarial-review.md`:

| Tier | Meaning | Default reviewer action |
|------|---------|-------------------------|
| S1 | **BLOCKER** — prevents shipping. | Must fix before release. |
| S2 | **CONCERN** — likely to cause problems. | Should fix; requires justification to skip. |
| S3 | **SUGGESTION** — improvement opportunity. | Fix if time allows; else track as tech debt. |
| S4 | **QUESTION** — unclear intent, needs clarification. | Must answer before proceeding. |

Each persona tags its own findings. The consolidator **keeps the highest
severity** when two personas independently flag the same file+topic.

## Output Schema

### Markdown (default)

```markdown
# Doc Review — Multi-Persona
- docs_dir, files reviewed, personas, total cost
## Summary  — counts by tier
## Hallazgos
### Críticos (S1 BLOCKER)     — table with location, what, why, recommendation, reviewers
### Medios (S2 CONCERN)
### Menores (S3 SUGGESTION)
### Preguntas abiertas (S4 QUESTION)
## Per-persona status
```

### JSON (--json)

```json
{
  "docs_dir": "...",
  "docs_files": [...],
  "severity_counts": {"S1": 0, "S2": 2, ...},
  "consolidated": [{"tier":"S2","location":"...","what":"...","reviewers":[...]}],
  "persona_results": [...]
}
```

## Design notes

- **Provider-agnostic**: uses `lib/dispatch.py` — respects the Qwen→Claude
  cascade (ADR-049). Haiku maps to the cheapest-tier Qwen bundle.
- **Parallel safety**: `concurrent.futures.ThreadPoolExecutor` with hard cap.
  Default cap reads `resources.compute.max_parallel_agents` from
  `cognitive-os.yaml` (falls back to 5).
- **Isolated persona failures**: one persona's dispatch error does NOT abort
  the other 4. The report shows `FAIL` in the per-persona status row.
- **Adversarial-review compliance**: each persona prompt requires ≥1 finding.
  "LGTM" / "no issues" is prohibited; personas that genuinely see nothing
  must emit an S4 QUESTION.
- **Trust Report**: each persona emits the machine-parseable
  `TRUST_REPORT: SCORE=... STATUS=...` header (rules/trust-score.md).
- **Dedup**: conservative — two findings only merge when both `location` and
  the first 80 chars of `what` match. Prefers false-positive-separate over
  false-positive-merge, because over-dedup silently drops findings.

## Known caveats (self-critique)

- Persona `role_brief` wording was seeded from one session and one project
  family. It has not been validated across many corpora. Treat the briefs
  as heuristic, not canonical.
- Haiku-tier models tend to inflate severity. A finding consistently flagged
  S1 by only one persona, with no red-flag match, is often closer to S2/S3.
- The dedup key (location + 80-char what-prefix) can over-merge when two
  personas describe the same symptom with overlapping language. Spot-check
  the "Reviewers" column when a finding attributes to 3+ personas.
- 5 parallel Haiku calls are well within typical provider rate limits, but
  cranking `--max-parallel` up is not a win — provider-side throttling
  dominates at that point.

## Verification

```bash
uv run pytest tests/unit/test_doc_review_personas.py -v
uv run python3 scripts/doc-review-personas.py --help
uv run python3 scripts/doc-review-personas.py --docs-dir docs/ --personas editor_qa --dry-run
# Optional (requires ALIBABA_QWEN_API_KEY):
bash scripts/smoke-doc-review-personas.sh
```

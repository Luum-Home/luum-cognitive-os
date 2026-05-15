<!-- SCOPE: both -->
<!-- TIER: 1 -->
# Language Token Economy — Preserve User Language, Compact Internal Work

## Rule

When the user works in Spanish, keep user-facing conversation in Spanish. Do not
optimize cost by forcing the user into English. Optimize the internal work
instead.

## Required behavior

- Preserve the user's language in final answers and clarification questions.
- Use compact structured internal artifacts: stable IDs, YAML fields, short
  slugs, tables, and checklists instead of duplicated prose.
- Do not duplicate the same content in Spanish and English unless the user asks
  for bilingual output.
- Summarize long transcripts before analysis; keep evidence excerpts short and
  cite the source artifact/path.
- Search memory or local artifacts before re-reading large histories.
- Prefer deterministic local scripts for parsing, classification, inventories,
  report generation, and mechanical audits.
- Escalate to larger/frontier models only after local evidence narrows the
  problem.

## Anti-patterns

| Anti-pattern | Replacement |
|---|---|
| Re-sending a full transcript to reason about one claim | Summarize transcript into claims/risks/actions first |
| Writing bilingual docs by default | Single-language user-facing prose plus compact metadata |
| Asking an LLM to grep/classify raw files | Use local scripts/audits first |
| Running the full suite repeatedly | Run failing node, classify cause, then rerun the smallest lane |

## Contextual Trigger

- When work involves token cost, Spanish/English efficiency, long transcripts,
  context budgets, model scarcity, rate limits, or AI resource optimization.

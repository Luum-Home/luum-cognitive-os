---
name: domain-model
version: 1.0.0
description: 'Use when you need this Cognitive OS skill: Scaffold a DDD domain-model.md
  template under docs/03-dominio-riesgo/ (ADR-054 10-category convention). Emits bounded-contexts
  + entities + ubiquitous-language tables with TODO markers. Idempotent.; do not use
  when a narrower skill directly matches the task.'
invocation: /domain-model --project-dir <path> [--brief "<description>"] [--overwrite]
user-invocable: true
last-updated: 2026-04-21
audience: project
triggers:
- domain model
- bounded contexts
- DDD scaffold
- ubiquitous language
- domain-model.md
summary_line: Scaffold DDD domain-model.md (bounded contexts + entities + language)
  idempotently.
model: haiku
platforms:
- claude-code
prerequisites: []
routing_patterns:
- pattern: \bdomain[- ]?model\b
  confidence: 0.95
- pattern: \bddd\s+domain\b
  confidence: 0.85
- pattern: \bscaffold\s+domain\b
  confidence: 0.75
---
<!-- SCOPE: project -->
# Domain Model Scaffolder

Scaffolds `docs/03-dominio-riesgo/domain-model.md` in an adopting project. This is a **template scaffolder**, not a content generator — it emits structured markdown with `<!-- TODO -->` markers that humans or downstream agents fill in.

## Scope

- Creates or extends ONE file: `<project>/docs/03-dominio-riesgo/domain-model.md`
- Idempotent: re-running preserves user edits placed below the `<!-- domain-model:autogen-footer -->` marker
- `--overwrite` replaces the entire file

## Invocation

```
uv run python3 scripts/domain_model.py \
  --project-dir /path/to/adopter-project \
  --brief "Describe the domain in one sentence"
```

## Outputs

A markdown file with these sections (all TODO-filled):

- Brief (verbatim insertion of `--brief`)
- Bounded Contexts (table)
- Core Entities (aggregate root + invariants)
- Value Objects
- Domain Events
- Ubiquitous Language glossary

## Idempotency contract

1. First run creates the file.
2. Second run without `--overwrite` replaces only the auto-generated header→footer block; content below the footer marker is preserved.
3. Second run with `--overwrite` replaces the entire file.
4. If the file exists but has no autogen markers (user-authored from scratch), the tool skips — does not destroy user content.

## NOT in scope

- Generating domain content from prose descriptions (would require an LLM call; out of scope for a scaffolder).
- Modifying any file outside `docs/03-dominio-riesgo/`.

## Integration

- Pairs with `/project-scaffold` (ADR-054) which creates the 10-category skeleton first.
- Pairs with `/risk-register` for the second file under `03-dominio-riesgo/`.

## Verification

```bash
uv run python3 scripts/domain_model.py --project-dir /tmp/test-dm --brief "simple ecommerce" --json
test -f /tmp/test-dm/docs/03-dominio-riesgo/domain-model.md
grep -q "Bounded Contexts" /tmp/test-dm/docs/03-dominio-riesgo/domain-model.md
```

---
adr: 340
title: English-Native Artifacts with Multilingual User-Facing Routing
status: accepted
implementation_status: implemented
date: '2026-06-17'
supersedes: []
superseded_by: null
extends:
  - ADR-302
  - ADR-325
implementation_files:
  - manifests/language-policy.yaml
  - tests/audit/test_language_policy.py
  - tests/unit/test_skill_router.py
  - tests/audit/test_weekly_multilingual_skill_coverage.py
tier: core
tags:
  - documentation
  - multilingual
  - skill-router
  - authoring
  - portability
classification_basis: |
  Establishes the language boundary for Cognitive OS artifacts: canonical
  repository artifacts stay English-native while user-facing skill triggers,
  routing aliases, and optional human outputs support English, Spanish, and
  Portuguese without duplicating translated documentation trees.
---

# ADR-340: English-Native Artifacts with Multilingual User-Facing Routing

## Status

Accepted — 2026-06-17. Implemented by the language policy manifest and audit ratchets listed in this ADR.

## Context

Cognitive OS is built in English-native repository artifacts so docs, ADRs,
rules, skills, manifests, code comments, release notes, and generated evidence
can remain searchable, diffable, and portable across teams and harnesses.

At the same time, operators and downstream users may work conversationally in
Spanish, Portuguese, or English. ADR-302 already moved natural-language routing
away from language-specific regexes and toward semantic metadata. ADR-325 also
keeps user collaboration language first-class while avoiding duplicated long
prose.

The missing standard is the boundary between canonical artifacts and human
interaction surfaces. Without a clear boundary, maintainers may either overfit
routing to English-only examples or create parallel translated documentation
that drifts from the source of truth.

## Decision

Cognitive OS adopts this language standard:

1. **Canonical artifacts are English-native.** Repository-owned docs, ADRs,
   rules, skills, manifests, reports, code comments, and long-form generated
   artifacts are authored and maintained in English by default.
2. **User-facing conversational triggers and routing aliases support EN+ES+PT.**
   User-facing skills must be discoverable from English, Spanish, and
   Portuguese utterances when they expose conversational triggers, semantic
   `routing_intents`, examples, aliases, or generated routing metadata.
3. **Human outputs may expose `--language`.** CLIs, report generators, and
   operator-facing commands may add a bounded `--language` option for final
   human-facing summaries. The canonical stored artifact remains English unless
   the command is explicitly designed to emit a localized view.
4. **Do not duplicate full translated docs.** Avoid parallel Spanish or
   Portuguese copies of canonical docs. If localization is needed, localize
   short labels, descriptions, trigger examples, UI copy, or generated summary
   views that can point back to the English canonical artifact.
5. **Deterministic aliases stay short and stable.** Slash commands, CLI flags,
   config keys, file paths, and primitive identifiers remain language-neutral or
   English-native unless a local project overlay intentionally adds aliases.
   Natural-language routing belongs in semantic metadata, not keyword regexes.

## Authoring guidance

For a user-facing skill or routeable primitive:

- write the canonical `SKILL.md`, rule, ADR, and implementation docs in English;
- include semantic routing examples or intents for English, Spanish, and
  Portuguese when the primitive is meant to be invoked from user conversation;
- keep translated examples short enough to be routing data, not a second manual;
- prefer meaning-equivalent utterances over literal translations;
- make any `--language` output option explicit about scope, for example
  `--language es` localizes the console summary but not the saved ADR; and
- link localized summaries back to the canonical English source.

## Consequences

### Positive

- Preserves one canonical, reviewable source of truth for architecture and
  governance artifacts.
- Makes user-facing skills accessible to English, Spanish, and Portuguese users.
- Avoids translated documentation drift and unnecessary token/cost overhead.
- Aligns with ADR-302 semantic routing and ADR-325 language-token economy.

### Negative / tradeoffs

- Authors must curate a small amount of multilingual routing metadata for
  user-facing skills.
- Full localization remains out of scope unless a future ADR defines a localized
  view layer with freshness guarantees.
- Some internal-only primitives may remain English-only because they are not
  conversational entrypoints.

## Alternatives rejected

- **English-only routing.** Rejected because it makes the OS less usable for
  operators who collaborate in Spanish or Portuguese even when the canonical
  repository remains English.
- **Full translated documentation trees.** Rejected because duplicate long-form
  docs create drift, review overhead, and inconsistent governance claims.
- **Language-specific keyword regexes.** Rejected by ADR-302; multilingual user
  support must use semantic routing metadata or explicit deterministic aliases.

## Verification

Implemented verification uses deterministic tests and closure checks, not grep-only evidence:

```bash
python3 -m pytest   tests/audit/test_language_policy.py   tests/audit/test_weekly_multilingual_skill_coverage.py   tests/unit/test_skill_router.py::TestWeeklyMultilingualSkillRouting   tests/audit/test_skill_routing_patterns_ascii.py   tests/audit/test_adr_contracts.py   tests/audit/test_adr_locations.py   -q

scripts/cos-primitive-closure-check --json --strict
```

Behavior evidence:

- `tests/audit/test_language_policy.py` enforces the manifest-backed boundary:
  English-native structural keys, no translated duplicate docs, and EN+ES+PT
  aliases for manifest-listed user-facing skills.
- `tests/unit/test_skill_router.py::TestWeeklyMultilingualSkillRouting` proves
  Spanish and Portuguese prompts route to the intended skills.
- `tests/audit/test_skill_routing_patterns_ascii.py` keeps deterministic regex
  aliases ASCII-only while runtime matching handles accent folding.

Current implementation enforces the declarative user-facing skill set in
`manifests/language-policy.yaml`; broader user-facing skill discovery remains a
future ratchet after skill metadata cleanup.

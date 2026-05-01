<!-- SCOPE: os-only -->
---
name: experimental
description: Internal holding area for experimental skill drafts awaiting synthesis, review, promotion, or rejection.
version: "1.0.0"
audience: os-dev
user-invocable: false
tags: [skills, experimental, synthesis]
---

# Experimental Skill Drafts

This directory is the review boundary for skill drafts before they become
published Cognitive OS skills.

## Promotion contract

1. Drafts enter this namespace only with enough context for review.
2. `skills/synthesize-skill/SKILL.md` reviews the synthesis queue and decides
   whether a draft is accepted, rejected, or deferred.
3. Accepted drafts move into their own top-level `skills/<name>/SKILL.md`
   directory and must pass the skill audit contract.

## Guardrails

- Experimental drafts are not part of the stable operator catalog.
- Promotion requires frontmatter, concrete steps, and passing reference checks.

# ADR-012: Prompt-Driven Governance -- Declarative Hook Logic

**Date:** 2026-03-29
**Status:** Accepted
**Commits:** 1f9bd87
**Engram IDs:** 1850

## Context

Five governance hooks (clarification-gate, assumption-tracker, prompt-quality, scope-creep-detector, blast-radius) performed natural language judgment using regex and keyword matching in bash. This approach had structural accuracy limits: regex cannot distinguish "I think X because evidence" from "I think X" as an ungrounded assumption. Each hook contained 100-180 lines of bash boilerplate for what was essentially a judgment call. Claude Code's `type: prompt` hook support enables LLM evaluation via Haiku, providing contextual reasoning that regex cannot achieve.

## Decision

Convert judgment-heavy governance hooks from imperative bash to declarative prompt templates evaluated by Haiku:

- **Convert 4 hooks**: clarification-gate, assumption-tracker, prompt-quality, scope-creep-detector. These require natural language understanding that regex approximates poorly.
- **Merge where possible**: clarification-gate + prompt-quality can share a single prompt evaluation since both assess the quality of user/agent prompts.
- **Keep ~70% of hooks in bash**: Deterministic checks (rate-limiter, content-policy, secret-detector, error-learning, registration-check) are better served by exact matching. No LLM evaluation needed.
- **Templates location**: `templates/prompt-hooks/` with structured prompt files that are transparent and editable by users (edit English, not bash).

## Alternatives Considered

- **Keep bash regex for all hooks**: Zero additional cost (no Haiku calls). Rejected because accuracy on judgment tasks was fundamentally limited. False positives in clarification-gate were already causing user friction.
- **Use a fine-tuned classifier model**: More accurate than regex, cheaper than Haiku per-call. Rejected because it adds training/deployment complexity and cannot be customized by editing a prompt template.
- **Move all hooks to prompt-based evaluation**: Consistent architecture, but unnecessary for deterministic checks. Rate limiting does not benefit from LLM evaluation -- it just compares numbers.

## Consequences

- Judgment accuracy improved for the converted hooks, particularly reducing false positives in clarification-gate.
- Each converted hook eliminated 30-40 lines of bash boilerplate, replaced by a structured prompt template.
- Haiku cost per evaluation is minimal (~$0.001) but non-zero -- this adds a per-operation cost that bash hooks did not have.
- The prompt templates became a new customization surface: users can modify governance behavior by editing English-language prompts rather than debugging bash regex.
- This decision established the principle that hooks should use the right tool for the job: bash for deterministic checks, LLM for judgment calls.

> **Note:** The suggested merge of clarification-gate and prompt-quality into a single hook was not implemented — they remain as separate hooks with separate prompt templates.

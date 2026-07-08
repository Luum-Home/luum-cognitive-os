---
type: concept-synthesis
source: docs/04-Concepts/architecture/functional-audit/scorecard-rules.md
provenance: "User's question: do the 20 rules in rules/ enforce behavior or ornament? Reality: 107 rule files exist, not 20."
---

## What it is

Capa-3 audit of every rule file in `rules/`, classifying each by its actual enforcement path: hook-enforced, hook-enforced-but-broken (hook exists, not registered), agent-instruction-only, declarative-only, or code-dead.

## Key mechanics

- Totals (107 rule files = 106 behavioral + index): 21 hook-enforced live (e.g. `anti-hallucination.md` -> `claim-validator.sh`, `blast-radius.md` -> `blast-radius.sh`, `trust-score.md` -> `trust-score-validator.sh`); 8 hook-enforced-BROKEN — hook exists on disk but isn't registered in `.claude/settings.json` (`audit-trail.md`, `auto-rollback.md`, `confidence-gate.md`, `confidentiality-protection.md`, `agent-identity.md`, `pre-dev-readiness-gate.md`, `reinvention-prevention.md`, `pre-commit-gate.md` — the last is an intentional git hook, not a Claude hook); 52 agent-instruction-only; 19 declarative-only; 2 remaining code-dead (`response-length-check.sh`, `context-budget.sh` never built).
- Critical finding: `hooks/subagent-context-injector.sh` is the **only** mechanism delivering rule content into a sub-agent's context, and it injects just two templates — `templates/agent-mandatory-rules.md` (31 lines) and `templates/agent-preamble.md` (101 lines) — neither of which cross-references `rules/*.md` by name. So of 107 rules, sub-agents automatically see only what those two templates contain.
- `CORE_RULES` in `hooks/self-install.sh:172` symlinks only 11 of 107 rules into orchestrator context; the remaining rules rely on `RULES-COMPACT.md` indexing by `[ref-key]`, but no hook/skill actually resolves that key into injected text — "a slash command `/rule <key>`" is proposed as the fix, not yet built.
- S1-tier findings: 8 safety-critical rules (audit trail, rollback, confidentiality, readiness) claim hook enforcement that isn't wired; only 9/107 rules were auto-injected into sub-agent launches at time of audit.
- S3 finding: overlapping rule pairs candidate for merge — `broken-window-policy.md`+`agent-quality.md`, `scope-creep-detection.md`+`scope-proportionality.md`, `rate-limiting.md`+`rate-limit-protection.md`.

## Relations & where used

`templates/agent-mandatory-rules.md`, `templates/agent-preamble.md`, `hooks/subagent-context-injector.sh`, `hooks/self-install.sh`, `rules/RULES-COMPACT.md`; feeds `tests/audit/test_rules_enforcement.py`.

## Status / caveats

Read-only audit (reconstruction phase). Baseline pytest run: 55 failed / 216 passed / 54 skipped. See `sprint-2a-orphan-fate.md` for the trim/reclassification that followed this audit.

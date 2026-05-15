---
adr: 319
title: Detractor Review Modes for Planning and Verification
status: accepted
implementation_status: partial
date: '2026-05-15'
supersedes: []
superseded_by: null
implementation_files:
- rules/adversarial-review.md
- rules/eas-evidence-artifact.md
- docs/05-Methodology/root/executable-acceptance-specification.md
- templates/eas.md
- scripts/eas_validate.py
- skills/sdd-spec/SKILL.md
- skills/sdd-verify/SKILL.md
tier: product
tags:
  - adversarial-review
  - detractor
  - eas
  - sdd
classification_basis: accepted doctrine, EAS integration, SDD skill wiring, and adversarial-review hook recognition for named modes; remaining work is generic PR/code/doc review surfaces staying doctrine-guided rather than fully mode-validated
partial_remaining: Generic code, PR, and documentation review surfaces consume Detractor modes through rule guidance and the generic adversarial-review gate; only EAS has a dedicated artifact/validator path.
remaining_in_scope: true
---

# ADR-319: Detractor Review Modes for Planning and Verification

## Status

Accepted.

## Context

Cognitive OS already had adversarial review and EAS detractor objections, but the skeptical role was underspecified. It could catch zero-finding reviews, yet it did not name when the agent should challenge consensus, run a pre-mortem, use a Black Hat risk lens, or escalate to formal red-team thinking.

The operator requested a portable primitive usable by both adopter projects and the OS itself while planning, creating documentation, implementing, and verifying work. Candidate terms were Tenth Man Rule, Devil's Advocate, Red Team, Pre-mortem, Black Hat, and AI-as-teammate Devil's Advocate.

## Decision

Adopt **Detractor** as the canonical agentic primitive slot.

The Detractor is a Tenth-Man / Devil's-Advocate-inspired reviewer that must argue that the EAS, plan, implementation, or final verification will fail before the system claims confidence.

The named techniques are selectable modes, not separate required primitives:

| Mode | Use when | Required shape |
|---|---|---|
| Tenth Man Rule | Consensus is strong, premature, or suspiciously cheap. | Assume the consensus is wrong and build the contrary thesis. |
| Devil's Advocate | Medium or larger plans need skeptical questioning. | Ask for alternatives, drawbacks, evidence, and assumptions. |
| Pre-mortem | Rollouts, migrations, releases, or architecture decisions could fail after approval. | Narrate the future failure and identify likely causes. |
| Black Hat | A Six Thinking Hats style risk pass is useful. | Identify risks, difficulties, and why the proposal may not work. |
| Red Team | Security, abuse, prompt-injection, or adversarial misuse is in scope. | Attack paths, exploit hypotheses, and mitigations. |

Multiple modes may be selected for the same work item. Default lightweight mode is Devil's Advocate; use Tenth Man Rule when there is visible convergence, Pre-mortem for rollout or release risk, Black Hat for structured risk review, and Red Team for adversarial or security domains.

## Relationship to ADR-317

ADR-317 owns EAS as the evidence artifact. ADR-319 owns the broader Detractor role and mode taxonomy. EAS is the first enforceable implementation surface for the role.

## Integration Points

- `rules/adversarial-review.md` defines the general review protocol and Detractor framing for planning, architecture, rollout, EAS, and final verification.
- `rules/eas-evidence-artifact.md` routes EAS and named detractor-mode requests.
- `templates/eas.md` includes a `Detractor Mode` section.
- `scripts/eas_validate.py` is the enforcement point for EAS artifacts.
- `skills/sdd-spec/SKILL.md` creates or updates EAS when the user asks for a named mode or a required contrary thesis.
- `skills/sdd-verify/SKILL.md` verifies selected modes, objections, evidence, and residual risk when EAS exists.
- `hooks/adversarial-review-gate.sh` recognizes named Detractor modes as review contexts and accepts S-tier/adversarial-review severity labels.

## Consequences

Positive: skeptical review becomes explicit, portable, and selectable by risk instead of relying on generic "be adversarial" language.

Tradeoffs: this adds ceremony for significant work and requires careful use so the Detractor does not become theater. Each objection must map to evidence, a task, or explicit residual risk.

## Reference Basis

- Brookings, `Lessons from Israel's Intelligence Reforms`, for Israeli intelligence reforms and devil's-advocate structures.
- CIA Center for the Study of Intelligence, `Instituting Devil's Advocacy in IC Analysis after the Arab-Israeli War of October 1973`, for formal alternative analysis, red cells, and devil's advocacy.
- de Bono Group, `Six Thinking Hats`, for the Black Hat risk lens.
- Mollick & Mollick, `Assigning AI: Seven Approaches for Students, with Prompts`, and Microsoft's `prompts-for-edu` Devil's Advocate prompt, for the AI-teammate framing.

## Alternatives rejected

- Leave the decision implicit in conversation history: rejected because ADR-gated governance needs a durable, reviewable record with explicit trade-offs.
- Treat this as an unversioned implementation note: rejected because the behavior affects operator-facing contracts and must survive refactors.

## Verification

```bash
.venv/bin/python -m pytest tests/contracts/test_eas_docs_contract.py tests/contracts/test_eas_manifest_and_sdd_wiring.py tests/unit/test_eas_validate.py -q
bash tests/unit/test_adversarial_review_gate.sh
.venv/bin/python -m pytest tests/red_team/portability/test_eas.py tests/red_team/portability/test_adversarial-review.py -q
python3 scripts/check_entrypoint_adr_links.py --project-dir .
```

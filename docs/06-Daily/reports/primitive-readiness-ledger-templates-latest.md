# Primitive Readiness Ledger — Templates

Total rows: 23
Rows without lifecycle metadata: 1
Consumer accessibility: lifecycle-declared-consumer-candidate:2, lifecycle-declared-maintainer:19, projected-consumer-surface:1, so-local-only:1

| Path | Role | Source | Confidence | Consumer Access | Lifecycle | Consumers | Next action |
|---|---|---|---|---|---|---:|---|
| `templates/adr-template.md` | lab | lifecycle | high | lifecycle-declared-maintainer | advisory | 5 | keep maintainer-only or add explicit export path |
| `templates/agent-mandatory-rules.md` | quality-gate | heuristic:text | medium | lifecycle-declared-maintainer | advisory | 19 | keep maintainer-only or add explicit export path |
| `templates/agent-preamble.md` | agent-preamble | heuristic:text | medium | lifecycle-declared-maintainer | advisory | 62 | keep maintainer-only or add explicit export path |
| `templates/agent-research-only.md` | lab | lifecycle | high | lifecycle-declared-maintainer | advisory | 11 | keep maintainer-only or add explicit export path |
| `templates/counsel-outreach/clean-room-permission.md` | prompt-composition | default | medium | lifecycle-declared-maintainer | advisory | 9 | keep maintainer-only or add explicit export path |
| `templates/counsel-outreach/license-clarification.md` | prompt-composition | heuristic:text | medium | lifecycle-declared-maintainer | advisory | 8 | keep maintainer-only or add explicit export path |
| `templates/counsel-outreach/review-request.md` | prompt-composition | default | medium | lifecycle-declared-maintainer | advisory | 9 | keep maintainer-only or add explicit export path |
| `templates/cross-harness-authoring.md` | lab | lifecycle | high | lifecycle-declared-maintainer | advisory | 30 | keep maintainer-only or add explicit export path |
| `templates/eas.md` | quality-gate | heuristic:text | medium | projected-consumer-surface | advisory | 19 | keep lifecycle, tests, and harness proof current |
| `templates/edit-conflict-response.md` | prompt-composition | heuristic:text | medium | lifecycle-declared-maintainer | advisory | 7 | keep maintainer-only or add explicit export path |
| `templates/error-recovery.md` | lab | lifecycle | high | lifecycle-declared-maintainer | advisory | 11 | keep maintainer-only or add explicit export path |
| `templates/fintech-gates.md` | quality-gate | heuristic:text | medium | lifecycle-declared-consumer-candidate | candidate | 7 | prove consumer project projection per supported harness before promotion |
| `templates/generator-validator-pair.md` | lab | lifecycle | high | lifecycle-declared-maintainer | advisory | 5 | keep maintainer-only or add explicit export path |
| `templates/go-service-context.md` | prompt-composition | heuristic:text | medium | lifecycle-declared-consumer-candidate | candidate | 6 | prove consumer project projection per supported harness before promotion |
| `templates/project-gotchas.md` | quality-gate | heuristic:text | medium | so-local-only |  | 19 | add lifecycle/package/projection metadata or keep SO-local |
| `templates/prompt-hooks/assumption-tracker-prompt.md` | lab | lifecycle | high | lifecycle-declared-maintainer | advisory | 4 | keep maintainer-only or add explicit export path |
| `templates/prompt-hooks/clarification-gate-prompt.md` | lab | lifecycle | high | lifecycle-declared-maintainer | advisory | 4 | keep maintainer-only or add explicit export path |
| `templates/prompt-hooks/prompt-quality-prompt.md` | lab | lifecycle | high | lifecycle-declared-maintainer | advisory | 4 | keep maintainer-only or add explicit export path |
| `templates/prompt-hooks/scope-creep-prompt.md` | lab | lifecycle | high | lifecycle-declared-maintainer | advisory | 4 | keep maintainer-only or add explicit export path |
| `templates/quality-gates.md` | lab | lifecycle | high | lifecycle-declared-maintainer | advisory | 33 | keep maintainer-only or add explicit export path |
| `templates/rebranding-checklist.md` | recovery | heuristic:text | medium | lifecycle-declared-maintainer | advisory | 12 | keep maintainer-only or add explicit export path |
| `templates/rule-template.md` | prompt-composition | default | medium | lifecycle-declared-maintainer | advisory | 9 | keep maintainer-only or add explicit export path |
| `templates/skill-template.md` | prompt-composition | heuristic:text | medium | lifecycle-declared-maintainer | advisory | 7 | keep maintainer-only or add explicit export path |

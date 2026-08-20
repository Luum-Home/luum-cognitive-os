# Reduction Sprint Backlog — Latest

> verify: .venv/bin/python3 scripts/reduction_backlog.py

| Priority | Action | Source | Item | Reason |
|---|---|---|---|---|
| P1 | harden | primitive-row-audit | `hooks:hooks/cos-session-start-projector.sh` | partial/high: events=SessionStart,projected; tested=False; emits_metric=False -> add behavioral test |
| P2 | demote-or-archive | primitive-row-audit | `hooks:packages/prompt-quality-gate/hooks/prompt-quality.sh` | aspirational/medium: events=unregistered; tested=False; emits_metric=True -> archive, wire, or delete |
| P2 | demote-or-archive | primitive-row-audit | `skills:.codex/skills/portability-work/SKILL.md` | aspirational/medium: frontmatter=True; trigger=False; runtime_ref=False; tested=False -> archive, wire, or delete |
| P2 | demote-or-archive | primitive-row-audit | `skills:.codex/skills/test-matrix/SKILL.md` | aspirational/medium: frontmatter=True; trigger=False; runtime_ref=False; tested=False -> archive, wire, or delete |
| P2 | demote-or-archive | primitive-row-audit | `metrics:.cognitive-os/metrics/adr-implementation.jsonl` | aspirational/medium: nonempty=False; mentioned=True -> delete, wire producer, or document owner |
| P2 | demote-or-archive | primitive-row-audit | `metrics:.cognitive-os/metrics/assumptions.jsonl` | aspirational/medium: nonempty=False; mentioned=True -> delete, wire producer, or document owner |
| P2 | demote-or-archive | primitive-row-audit | `metrics:.cognitive-os/metrics/backlog-reconciliation.jsonl` | aspirational/medium: nonempty=False; mentioned=True -> delete, wire producer, or document owner |
| P2 | demote-or-archive | primitive-row-audit | `metrics:.cognitive-os/metrics/chaos-weekly.jsonl` | aspirational/medium: nonempty=False; mentioned=False -> delete, wire producer, or document owner |
| P2 | demote-or-archive | primitive-row-audit | `metrics:.cognitive-os/metrics/decision-depth-gate.jsonl` | aspirational/medium: nonempty=False; mentioned=True -> delete, wire producer, or document owner |
| P2 | demote-or-archive | primitive-row-audit | `metrics:.cognitive-os/metrics/direct-main-bypass.jsonl` | aspirational/medium: nonempty=False; mentioned=True -> delete, wire producer, or document owner |
| P2 | demote-or-archive | primitive-row-audit | `metrics:.cognitive-os/metrics/graphify-context-replay-benchmark.jsonl` | aspirational/medium: nonempty=False; mentioned=False -> delete, wire producer, or document owner |
| P2 | demote-or-archive | primitive-row-audit | `metrics:.cognitive-os/metrics/graphify-token-reduction-smoke.jsonl` | aspirational/medium: nonempty=False; mentioned=False -> delete, wire producer, or document owner |
| P2 | demote-or-archive | primitive-row-audit | `metrics:.cognitive-os/metrics/install-timing.jsonl` | aspirational/medium: nonempty=False; mentioned=True -> delete, wire producer, or document owner |
| P2 | demote-or-archive | primitive-row-audit | `metrics:.cognitive-os/metrics/maintainer-decision-impact.jsonl` | aspirational/medium: nonempty=False; mentioned=True -> delete, wire producer, or document owner |
| P2 | demote-or-archive | primitive-row-audit | `metrics:.cognitive-os/metrics/plan-claim-validator.jsonl` | aspirational/medium: nonempty=False; mentioned=True -> delete, wire producer, or document owner |
| P2 | demote-or-archive | primitive-row-audit | `metrics:.cognitive-os/metrics/repair-dispatch.jsonl` | aspirational/medium: nonempty=False; mentioned=True -> delete, wire producer, or document owner |
| P2 | demote-or-archive | primitive-row-audit | `metrics:.cognitive-os/metrics/repair-outcomes.jsonl` | aspirational/medium: nonempty=False; mentioned=True -> delete, wire producer, or document owner |
| P2 | demote-or-archive | primitive-row-audit | `metrics:.cognitive-os/metrics/session-audit.jsonl` | aspirational/medium: nonempty=False; mentioned=True -> delete, wire producer, or document owner |
| P2 | demote-or-archive | primitive-row-audit | `metrics:.cognitive-os/metrics/so-impact-eval-trigger.jsonl` | aspirational/medium: nonempty=False; mentioned=True -> delete, wire producer, or document owner |
| P2 | add-proof-link | claim-proof-audit | `README.md:198` | - self-hosting for your own organization; |

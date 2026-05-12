# Alternatives Comparison — 2026-04-30

This report is intentionally evidence-bound. It compares COS against the tools
and patterns discussed in prior research only on axes that the current repo can
support with code, tests, docs, or generated audit outputs.

## Current verdict

COS is strongest where it has explicit governance, persistent memory, and
verification gates. It is weakest where the surface area grows faster than proof:
skill discoverability, hook latency, duplicate documentation, and concurrent
session coordination.

## Comparison matrix

| Axis | COS current evidence | Hermes / prior alternatives | Verdict |
|---|---|---|---|
| Governance gates | Hook/rule/test infrastructure exists; row audit now tracks unproven hooks and rules. | Hermes-style systems had simpler loops and fewer governance layers. | COS wins on governance depth, loses on simplicity. |
| Memory continuity | Engram saves/searches/session summaries are used in this session and persisted. | Honcho-style memory often requires external service setup. | COS wins when Engram is available; portability still needs proof per harness. |
| Skill discovery | 143+ skills; row audit and backlog now expose weak/aspirational rows. | Hermes-style progressive disclosure was cleaner. | COS currently loses on discoverability. |
| Runtime latency | Hook timing exists and now carries `session_id`; row audit exposes high-risk hooks. | Smaller systems have lower hook overhead by default. | COS loses until reduction sprint lands. |
| Duplicate docs / claim drift | Duplicate scan, pre-write guard, claim-proof audit, and backlog now exist. | Most alternatives rely on human review. | COS can win if gates are kept strict enough. |
| Concurrent session coordination | Commit provenance and ADR reservation lock now exist with real tests. | Simpler tools often avoid this by not supporting many simultaneous agents. | COS now has a differentiated guardrail, but ADR authoring guard remains. |
| Proof discipline | Primitive row audit, claim-proof audit, and reduction backlog generate durable reports. | Prior tools often advertised behavior without repo-local proof mapping. | COS wins if reports are acted on, not just generated. |

## Adopted patterns that were genuinely better elsewhere

- Progressive disclosure for skills: COS still needs a smaller default skill
  surface and a clearer lookup path.
- Mid-task scan / loop closure: COS added family and row-level audits, but some
  signals still need runtime consumers.
- Memory manager separation: COS benefits from Engram, but should avoid making
  memory behavior mysterious or mandatory for every task.

## Where COS should stop pretending

- Do not claim full automagic behavior for hooks/rules/skills until row audit
  status is `proven`.
- Do not claim low-friction DX while high-severity row backlog remains large.
- Do not present aspirational ADRs or roadmap items as current product behavior.

## Evidence links

- Primitive row audit: `docs/06-Daily/reports/primitive-row-audit-latest.md`
- Claim-to-proof audit: `docs/06-Daily/reports/claim-proof-latest.md`
- Reduction backlog: `docs/06-Daily/reports/reduction-backlog-latest.md`
- Conversation reality audit: `docs/08-References/business/conversation-reality-audit-2026-04-30.md`

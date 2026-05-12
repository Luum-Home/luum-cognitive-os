---

adr: 270
title: Legal Compliance Workflow Automation
status: accepted
implementation_status: implemented
date: 2026-05-11
supersedes: []
superseded_by: null
extends: [ADR-259, ADR-267, ADR-268, ADR-269]
implementation_files:
  - scripts/cos-uspto-patent-search
  - scripts/cos-uspto-trademark-search
  - scripts/cos-counsel-packet
  - scripts/cos-counsel-outreach-draft
  - scripts/cos-legal-approve
  - scripts/cos-adoption-unfreeze
  - manifests/legal-review-ledger.yaml
  - hooks/legal-review-required-on-runtime-import.sh
  - templates/counsel-outreach/*.md
tier: governance
tags: [legal, compliance, ip, uspto, trademark, patent, counsel, adoption, unfreeze]
related_adrs:
  - ADR-259 (external-pattern-adoption-posture umbrella)
  - ADR-267 (license-compliance enforcement architecture)
  - ADR-268 (defensive history sanitization 2026-05-11)
  - ADR-269 (mandatory ADR reference for history rewrites)
---

# ADR-270 — Legal Compliance Workflow Automation

## Status

Accepted (2026-05-11). Implementation lands in companion commit.

## Context

The 2026-05-11 adoption-freeze decision (`manifests/external-tool-adoption-freeze.yaml`,
captured in ADR-267 §Gap 1) made the pre-commercial / pre-SaaS posture mechanical:
hooks now refuse to extend external-pattern adoption surface until counsel signs
off. While the freeze is technical, the work it gates is not. Concretely, six
non-engineering blockers remain before any tool's Annex F can flip to
`reviewed-by-legal: yes`:

1. **USPTO patent search** for the producer (e.g., `Holaboss` as
   assignee_organization) — does the producer hold patents that the adoption
   would infringe?
2. **USPTO TESS trademark search** for tool wordmarks (e.g., `holaOS`,
   `Holaboss`) — is the name we adopt protected? Live/dead/pending status,
   international class IC 042 (software services) / IC 009 (software products)?
3. **Producer outreach** (e.g., `admin@holaboss.ai`) requesting permission /
   clarification of license clauses where ambiguous.
4. **IP counsel review** of the full evidence packet (Annex F + license
   snapshot + USPTO reports + clean-room evidence).
5. **Annex F marking** — flipping `reviewed-by-legal: yes` in frontmatter
   only when counsel evidence (memo with SHA-256 anchor) is on file.
6. **Per-tool unfreeze** — narrowing the global freeze to a granular allowlist
   without dropping protection for unreviewed tools.

Until 2026-05-11 these steps lived as prose in Annex F documents and ad-hoc
operator todo lists. With ~30 silent-debt deep-eval adoptions queued (Hermes,
Pi-coding-agent, OpenHarness, Sprut-agent-kit, HelixDB, MegaMemory, iFixAi …)
the workflow needs to be reusable, auditable, and partially mechanical so
operator time is spent on counsel judgment, not packet-assembly toil.

## Decision

Introduce **eight primitives** that automate the mechanical parts of the legal
compliance workflow while leaving counsel judgment fully manual:

| # | Primitive | Type | Responsibility |
|---|-----------|------|----------------|
| 1 | `cos-uspto-patent-search` | CLI | Query USPTO PatentsView for producer/keywords, classify CRITICAL/HIGH/LOW relevance |
| 2 | `cos-uspto-trademark-search` | CLI | Query USPTO TSDR for marks, classify LIVE/DEAD/pending |
| 3 | `cos-counsel-packet` | CLI | Bundle Annex F + USPTO reports + license snapshot + clean-room evidence into a single zip for counsel |
| 4 | `cos-counsel-outreach-draft` | CLI | Template-driven email drafter for producer / counsel outreach (drafts only — no send) |
| 5 | `cos-legal-approve` | CLI | Atomically flip Annex F `reviewed-by-legal: yes` only when counsel memo file exists; record SHA-256 in ledger |
| 6 | `cos-adoption-unfreeze` | CLI | Per-tool unfreeze with gated pre-flight checks against ledger + USPTO reports |
| 7 | `manifests/legal-review-ledger.yaml` | Manifest | Append-only registry of counsel decisions with memo SHA-256 for tamper-evidence |
| 8 | `hooks/legal-review-required-on-runtime-import.sh` | Hook (PreToolUse Bash) | Block commits that import code attributed to a tool whose legal-review-ledger entry is not `approved` |

### Interfaces

```
cos-uspto-patent-search --producer "Holaboss" [--keywords "..."] [--max-results 50]
                        [--output ...] [--json|--markdown]

cos-uspto-trademark-search --mark "holaOS" [--mark ...] [--international-class 042]
                           [--output ...] [--json|--markdown]

cos-counsel-packet --tool foo --adr ADR-NNN [--include-annex-f]
                   [--include-uspto-reports] [--include-license-snapshot]
                   [--include-cleanroom-evidence] [--output ...]

cos-counsel-outreach-draft --tool foo --to "admin@..." \
                           --template clean-room-permission|license-clarification|review-request \
                           [--counsel-packet ...] [--output ...]

cos-legal-approve --adr ADR-NNN --annex-f path --counsel "Name, Firm" \
                  --memo /path/to/memo.pdf \
                  --decision approved|approved-with-conditions|rejected \
                  [--conditions "..."] [--date YYYY-MM-DD]

cos-adoption-unfreeze --tool foo --evidence-bundle /tmp/counsel-foo.zip \
                      --operator <id> --reason "..." \
                      [--accept-patent-risk] [--ack-conditions]
```

## Workflow (typical adoption)

```
1. Operator runs cos-uspto-patent-search --producer X
2. Operator runs cos-uspto-trademark-search --mark Y
3. Operator runs cos-counsel-outreach-draft --template clean-room-permission
   (operator manually sends draft from their email client)
4. Operator runs cos-counsel-packet --tool X --adr ADR-NNN
   → /tmp/counsel-X-<date>.zip
5. Operator sends packet to IP counsel; counsel returns memo (PDF)
6. Operator places memo in .private/legal-memos/<tool>-<date>.pdf
7. Operator runs cos-legal-approve --adr ADR-NNN --annex-f ... --counsel "..." \
                                   --memo ... --decision approved
   → Annex F frontmatter updated, ledger entry appended, SHA-256 anchored
8. Operator runs cos-adoption-unfreeze --tool X --evidence-bundle ... \
                                       --operator ... --reason ...
   → Pre-flight checks gate (patent report exists & no CRITICAL, TM report exists,
     Annex F approved, ledger entry approved, conditions ack'd if any)
   → External-tool-adoption-freeze manifest gains tool in `unfrozen_tools` list
```

The runtime-import hook (#8) is independent: it activates when staged Python
files contain `# Ported from <tool>` / `# Adapted from <tool>` attribution
headers and the tool's ledger entry is not yet approved. This catches the
inverse scenario where an engineer tries to land code from a tool before the
legal pipeline completes.

## Limits (irreductible)

- **Counsel judgment cannot be automated**. The CLI only mechanizes evidence
  gathering, packet assembly, and ledger bookkeeping. Decisions
  (approved/rejected/conditions) come from a human IP attorney.
- **Email sending is intentionally out of scope**. `cos-counsel-outreach-draft`
  produces markdown the operator copies to their mail client. Direct SMTP
  integration would require credentials governance the OS does not yet have.
- **USPTO PatentsView and TSDR APIs change**. Each CLI degrades gracefully
  (clear error message on auth/format failure) so a temporary API outage does
  not block the rest of the workflow.
- **Memo SHA-256 anchors evidence, not validity**. The ledger records that
  *some* memo was reviewed; it does not assert the memo's legal sufficiency.
- **Per-tool unfreeze is independent of global freeze**. Global
  `frozen: true` plus a tool in `unfrozen_tools` ⇒ that tool only is allowed.
  Global flip-to-false remains an operator decision outside this ADR.

## Consequences

**Positive**

- Operator time on each adoption shrinks from ~half-day of packet assembly to
  ~30 minutes of counsel review prep.
- Audit trail: every approval has a memo SHA-256 anchor + ledger entry +
  Annex F frontmatter mutation.
- The 30-tool silent-debt backlog becomes mechanically tractable (one
  `cos-counsel-packet` per tool).
- The runtime-import hook closes the loophole where attribution-bearing code
  could land before legal sign-off.

**Negative**

- Six new CLIs to maintain. Schema drift in USPTO APIs forces upkeep.
- The ledger becomes a privileged write target. Append-only contract enforced
  via test (`tests/contracts/test_legal_review_ledger_append_only.py`).
- `cos-legal-approve` mutates Annex F frontmatter directly; mistakes are
  reversible only by ledger amendment commit + manual frontmatter edit.

## Alternatives Considered

1. **Spreadsheet tracking** — rejected: not tamper-evident, no integration
   with adoption-freeze manifest, and the operator already maintains too
   many spreadsheets.
2. **GitHub Issues** — rejected: makes private legal correspondence public-by-default
   in any public repo migration; ledger is intentionally inside the repo so it
   moves with the code.
3. **External SaaS (Clio, Smokeball)** — rejected: introduces vendor lock-in
   for a small operator-owned business; not justified at current scale.
4. **Single mega-CLI (`cos-legal`)** — rejected: each primitive has a clean,
   independently-testable surface. ADR-256 §primitive-contract registry
   prefers small composable CLIs.

## References

- ADR-259 — External-pattern adoption posture (umbrella that this implements)
- ADR-267 — License-compliance enforcement architecture (§Gap 1 named the freeze)
- ADR-268 — Defensive history sanitization (the trigger that surfaced these gaps)
- ADR-269 — Mandatory ADR reference for history rewrites
- `manifests/external-tool-adoption-freeze.yaml` — current freeze state
- `rules/license-policy.md` — BLOCKER/SAFE classification used by hook #8
- USPTO PatentsView API: https://search.patentsview.org/api/v1/patent/
- USPTO TSDR Data API: https://developer.uspto.gov/api-catalog/tsdr-data-api

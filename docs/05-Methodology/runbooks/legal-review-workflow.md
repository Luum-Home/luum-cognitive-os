# Runbook — Legal Review Workflow for External Tool Adoption

> **Audience**: operator (human) responsible for unfreezing external-tool
> adoption after IP counsel review.
> **Scope**: any external tool with non-trivial license (BSL, AGPL, Apache,
> proprietary). Trivial deps (MIT/BSD pure) skip steps 1-3.
> **Reference ADRs**: ADR-259 (clean-room posture), ADR-267 (commit-time
> enforcement), ADR-269 (history rewrite docs), ADR-270 (automation),
> ADR-271 (Tier-2 AST detector).

## When to use this runbook

- Frozen state in `manifests/external-tool-adoption-freeze.yaml` → blocks
  new annexes / research / radar additions.
- You need to unfreeze a specific tool for adoption.
- Or: existing vendored code needs retroactive legal review (Hermes / Pi /
  OpenHarness / Sprut + holaOS already have pending entries in
  `manifests/legal-review-ledger.yaml`).

## Pre-conditions

- Tool's Annex F exists at `docs/03-PoCs/research/<tool>-annex-f-*.md` (or
  `.private/...` for BSL-restricted material).
- Annex F frontmatter currently has `reviewed-by-legal: pending`.
- Tool has a primary adoption ADR (ADR-NNN, status Accepted).

## The 8-step workflow

### Step 1 — USPTO patent search

```bash
python3 scripts/cos-uspto-patent-search \
    --producer "<Company Name>" \
    --keywords "<comma-separated terms relevant to the tool>"
```

Example:
```bash
python3 scripts/cos-uspto-patent-search \
    --producer "Holaboss" \
    --keywords "agent runtime,LLM agent,agent-computer platform"
```

Output: `docs/06-Daily/reports/uspto-patent-<tool>-<date>.{json,md}`

Required to proceed: report file exists. CLI returns 0 even on empty
results — operator inspects markdown for CRITICAL findings.

### Step 2 — USPTO trademark search

For each candidate mark (the product name AND the company name):

```bash
python3 scripts/cos-uspto-trademark-search --mark "<Mark>"
```

Example:
```bash
python3 scripts/cos-uspto-trademark-search --mark "holaOS"
python3 scripts/cos-uspto-trademark-search --mark "Holaboss"
```

Output: `docs/06-Daily/reports/uspto-tm-<mark>-<date>.{json,md}`

Operator notes any LIVE matches in IC 009 (software products) or
IC 042 (software services).

### Step 3 — Generate counsel packet

```bash
python3 scripts/cos-counsel-packet --tool <tool-slug> --adr ADR-NNN \
    --output /tmp/counsel-<tool>-<date>.zip
```

Output: zip with structured folders:
- `README.md` — cover sheet with claims to validate
- `ADR/` — the primary adoption ADR
- `AnnexF/` — the clean-room compliance dossier
- `USPTO/` — patent + TM reports from steps 1-2
- `LICENSE/` — upstream license snapshot
- `CleanRoom/` — relevant `lib/` files with attribution headers
- `ExistingADRs/` — ADR-259, ADR-267, ADR-269, ADR-270

### Step 4 — Draft outreach email (optional)

If reaching out to the upstream producer:

```bash
python3 scripts/cos-counsel-outreach-draft \
    --tool <tool> --to "admin@<producer>.example" \
    --template clean-room-permission \
    --counsel-packet /tmp/counsel-<tool>-<date>.zip
```

Templates:
- `clean-room-permission` — asks producer to OK clean-room adoption
- `license-clarification` — asks about ambiguous license clauses
- `review-request` — generic IP counsel review request

Output: markdown at `drafts/email-<tool>-<date>.md`.
**This does NOT send.** Operator copies to email client.

### Step 5 — Send to IP counsel

**Manual step.** Email counsel with the packet (step 3) as attachment.
Wait for memo response (typical: 3-10 business days).

### Step 6 — Receive counsel memo

Store memo securely: `.private/legal-memos/<tool>-YYYY-MM-DD.pdf`
(or `.md`). `.private/` is gitignored — memos never enter version control.

### Step 7 — Mark legal approval

```bash
python3 scripts/cos-legal-approve \
    --adr ADR-NNN \
    --annex-f docs/03-PoCs/research/<tool>-annex-f-*.md \
    --counsel "Counsel Name, Firm LLP" \
    --memo .private/legal-memos/<tool>-YYYY-MM-DD.pdf \
    --decision approved \
    --date YYYY-MM-DD
```

Decisions:
- `approved` — clean adoption authorized
- `approved-with-conditions` — requires `--conditions "..."` flag;
  operator must `--ack-conditions` during unfreeze
- `rejected` — adoption blocked; tool moves to `docs/05-Methodology/root/blocked-tools.md`

Effects:
- Updates Annex F frontmatter: `reviewed-by-legal: yes` plus counsel
  metadata + SHA-256 of memo for tamper-evidence
- Appends entry to `manifests/legal-review-ledger.yaml`

### Step 8 — Unfreeze (per-tool)

```bash
python3 scripts/cos-adoption-unfreeze \
    --tool <tool> \
    --evidence-bundle /tmp/counsel-<tool>-<date>.zip \
    --operator <your-id> \
    --reason "IP counsel approved per memo <date>"
```

Pre-flight gates (all must pass):
1. ✅ USPTO patent report exists for `<tool>`
2. ✅ USPTO TM report exists for `<tool>`
3. ✅ Annex F has `reviewed-by-legal: yes`
4. ✅ Ledger entry has `decision: approved` or `approved-with-conditions`
5. ✅ (If conditions) `--ack-conditions` flag passed

On pass: adds `<tool>` to `unfrozen_tools` list in
`manifests/external-tool-adoption-freeze.yaml`. Global `frozen: true` stays
— this is per-tool granularity.

Failure: prints which gate failed + what's missing.

## State inspection commands

```bash
# What rewrites have happened?
python3 scripts/cos-history-rewrite-audit --list

# Orphan bundles (sanitization without ADR)?
python3 scripts/cos-history-rewrite-audit --orphans

# Adoption registry status:
cat .cognitive-os/adoption-registry.yaml

# Frozen vs unfrozen tools:
yq '.frozen, .unfrozen_tools, .frozen_tools' \
    manifests/external-tool-adoption-freeze.yaml

# Pending legal reviews:
yq '.entries | filter(.decision == "pending")' \
    manifests/legal-review-ledger.yaml
```

## Bypasses (logged, use sparingly)

| Bypass env var | Purpose |
|---|---|
| `COS_ALLOW_FREEZE_TOGGLE=1` | Edit `external-tool-adoption-freeze.yaml` itself |
| `COS_ALLOW_ADOPTION_FREEZE_BYPASS=1` | Commit research annexes during freeze (retroactive) |
| `COS_ALLOW_PRE_LEGAL_REVIEW_IMPORT=1` | Import upstream code without `reviewed-by-legal: yes` |
| `COS_ALLOW_UNDOCUMENTED_REWRITES=1` | Suppress SessionStart bundle warnings |
| `COS_ALLOW_NETWORK_EGRESS=1` | Real USPTO API calls in sandboxed shells |

Every bypass logs to `.cognitive-os/logs/*.jsonl` for audit.

## Pending state (2026-05-11 snapshot)

Tools in `manifests/legal-review-ledger.yaml` with `decision: pending`:

| Tool | Annex F | Source |
|---|---|---|
| holaOS | `.private/external-pattern-research/external-pattern-annex-f-compliance-cleanroom.md` | ADR-259 clean-room |
| Hermes Agent | `docs/03-PoCs/research/hermes-annex-f-compliance-cleanroom-2026-05-11.md` | retroactive (vendored 6 files) |
| Pi coding-agent | `docs/03-PoCs/research/pi-coding-agent-annex-f-compliance-cleanroom-2026-05-11.md` | retroactive (1 file) |
| HKUDS/OpenHarness | `docs/03-PoCs/research/openharness-annex-f-compliance-cleanroom-2026-05-11.md` | retroactive (1 file) |
| Sprut Agent Kit | `docs/03-PoCs/research/sprut-agent-kit-annex-f-compliance-cleanroom-2026-05-11.md` | retroactive (1 file) |
| HelixDB | `docs/03-PoCs/research/helixdb-annex-f-*-2026-05-11.md` | ASSESS clean-room reference |
| iFixAi | `docs/03-PoCs/research/ifixai-annex-f-*-2026-05-11.md` | TRIAL Apache-2.0 |
| MegaMemory | `docs/03-PoCs/research/megamemory-annex-f-*-2026-05-11.md` | TRIAL MIT port pending |

All 8 require steps 1-8 before respective unfreeze.

## What is NOT automated

| Step | Why human |
|---|---|
| 5 — Email send | Authorization + tracking |
| 6 — Counsel memo | Legal interpretation is the deliverable |
| Counsel judgment within step 7 | Reading patents/TMs against use case |
| Risk acceptance for `approved-with-conditions` | Operator's call |
| Global freeze flip (`frozen: false`) | Strategic decision after N tools unfrozen |

## References

- ADR-259 — holaOS adoption posture (patterns-only, clean-room)
- ADR-267 — License-compliance enforcement architecture (Layer 1 hooks)
- ADR-269 — Mandatory ADR reference for history rewrites
- ADR-270 — Legal compliance workflow automation (this runbook)
- ADR-271 — Clean-room detection tier-2 (AST similarity)
- `rules/license-policy.md` — SPDX classification table
- `docs/06-Daily/reports/license-compliance-audit-2026-05-11.md` — global audit

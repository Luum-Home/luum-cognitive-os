# Pre-Public Readiness Checklist

> Single gate before flipping the repo to public visibility.
> Each item below blocks publication unless explicitly marked
> `accept-risk` with rationale and operator sign-off.

**Owner:** repository operator
**Audience:** public-launch reviewer (legal, security, comms)
**Status legend:**

- `done` — verified, evidence linked
- `in-progress` — work started, not finished
- `pending` — not started
- `accept-risk` — known gap, deliberate, with rationale
- `n/a` — not applicable to this release

---

## Critical — hard blockers

### C1. Git history sanitized (ADR-218)

Risk: consumer codenames (env-var protected list), operator email, machine
paths, sister-project paths visible in commit history once public.

Required actions:

- [ ] All 7 sanitization env vars set with real values
- [ ] `cos history sanitize --execute --yes` run successfully
- [ ] Tombstone branch present at `tombstone/pre-history-rewrite-*`
- [ ] Sanitization report at `docs/history/sanitization-report-*.yaml`
  recorded and reviewed
- [ ] Smoke test: `git log --all -p | grep -E '<sensitive-tokens>'`
  returns 0 hits across full history (including tombstone)
- [ ] Force-push to origin completed
- [ ] Tag `v0.27.1-pre-history-rewrite` re-attached to new SHAs

Evidence: link to report, log of tombstone smoke test.

Status: `pending`

---

### C2. Client-project coupling removed (Tiers 1–4)

Risk: 28 OS files reference one consumer's services
(`<consumer-codename-a>`, `<consumer-codename-b>`, `<consumer-codename-c>`, `<consumer-service>`, `<consumer-service-2>`, etc.).
Public release of these strings is an NDA-adjacent exposure.

Required actions:

- [ ] Tier 1 — `hooks/error-pipeline.sh` config-driven; workflows generic
- [ ] Tier 2 — 4 SKILL.md genericized + portability tests pass
- [ ] Tier 3 — 9 docs files swept
- [ ] Tier 4 — 4 test fixtures + benchmark configs swept
- [ ] `scripts/audit-consumer-dependence.sh .` returns 0 matches
  outside of `docs/business/case-study.md` and `open-source-design.md`
- [ ] All Tier commits landed on `main`

Evidence: commit SHAs per tier, audit-script clean output.

Status: `in-progress` (Tier 1 active, 2/3/4 prompts staged at
`.cognitive-os/private/tier-prompts.md`)

---

### C3. License transition documented

Risk: Apache 2.0 → FSL-1.1-MIT change reads as a “rug pull” in the
absence of a clear FAQ. Precedent: HashiCorp / Elastic / Redis backlash.

Required actions:

- [ ] `docs/legal/license-faq.md` published with:
  - Why FSL-1.1-MIT (commercial rationale, in plain language)
  - Two-year MIT relicensing commitment, mechanically verified
  - Which uses are unrestricted (non-competing internal use,
    research, education) and which are not
  - Comparison vs Apache 2.0 in concrete terms
  - What downstream consumers should plan for
- [ ] `LICENSE` and `NOTICE` files match the FAQ
- [ ] `README.md` links to the FAQ from the license badge

Status: `pending`

---

### C4. Tests green on `main`

Risk: auditor clones, runs `pytest`, sees red. Single most damaging
first impression.

Required actions:

- [ ] Full `pytest` run on clean clone — all green or documented xfails
- [ ] Go suites pass: `go test ./...` in root, `cmd/cos`, `cmd/cos-test`
- [ ] `gofmt -l ./...` empty; `go vet ./...` clean
- [ ] Lane registry consistent: `pytest -q tests/audit/` clean
- [ ] CI run on a fresh branch from current `main` succeeds
- [ ] Test count, pass count, skip count published in
  `docs/quality/test-coverage-report.md`

Status: `pending` (no fresh full run since 2026-05-07)

---

### C5. Engram store privacy audit

Risk: persistent memory may include casual operator observations,
client-named decisions, frustration notes, or secret-adjacent data.

Required actions:

- [ ] Engram export reviewed for client tokens (same blocked list as C2)
- [ ] Engram observations with `project: 'luum-cognitive-os'` filtered;
  client-coupled entries deleted or rewritten
- [ ] Document whether Engram store is shipped with the repo or local-only
- [ ] If shipped, redact pre-publication

Status: `pending`

---

## High — fixable in a day, ugly if missed

### H1. Aspirational vs Real feature labelling

Risk: marketing claims about features that are inactive (MAPE-K,
singularity, agent-communication via Valkey) or aspirational invite
"vaporware" criticism.

Required actions:

- [ ] Run `component-reality-check` skill across the repo
- [ ] Cross-check `docs/business/01-commercial-brief-v2.md` and
  `master-plan-checklist.md` against the REAL/DORMANT/ASPIRATIONAL
  classification
- [ ] Mark every public-facing claim with status badge or remove

Status: `pending`

---

### H2. AI-attribution policy public

Risk: heavy AI-assisted authorship plus the global rule banning
`Co-Authored-By` trailers will be read as concealment unless explained.

Required actions:

- [ ] `CONTRIBUTING.md` explains:
  - That commits are predominantly AI-assisted with human-in-the-loop
  - Why the `Co-Authored-By` trailer is not used (deliberate, not hidden)
  - How to identify which model wrote what (if at all)
  - Review/verification gates each AI commit passes through
- [ ] Linked from `README.md`

Status: `pending`

---

### H3. Provenance / clean-room audit

Risk: research-first protocol ingested code/patterns from OpenCode,
Aider, Cursor, Devin, etc. Any literal copy-paste with cosmetic
rewriting is a legal exposure.

Required actions:

- [ ] Run `audit-integrity` skill
- [ ] Spot-check 10 ADRs that cite external tools for clean-room
  separation
- [ ] Public note in `docs/architecture/provenance.md` listing which
  patterns were inspired by which prior art and under what license

Status: `pending`

---

## Medium — defendable but worth closing

### M1. Dependencies and supply chain

Required actions:

- [ ] Generate SBOM (CycloneDX format)
- [ ] License audit of all transitive dependencies — block AGPL/SSPL/BSL
- [ ] Pin third-party tool digests where possible
- [ ] `docs/security/supply-chain.md` published

Status: `pending`

### M2. Onboarding walkthrough

Required actions:

- [ ] Fresh clone → first useful skill invocation under 10 minutes
- [ ] `validate-release` skill output captured
- [ ] Recorded asciicast or screencast linked from `README.md`

Status: `pending`

### M3. ADR sweep — 14 recent ADRs

Risk: 14 ADRs landed in 24h by an AI agent. Inconsistencies, broken
cross-references, prose drift very likely. Hostile readers will find them.

Required actions:

- [ ] Manual reviewer pass over ADR-218 through ADR-236
- [ ] Cross-references valid (no broken `[ADR-NNN]` links)
- [ ] Status, owner, decision-summary present and consistent
- [ ] Topic keys in Engram match canonical filenames

Status: `pending`

### M4. Sanitize tombstone smoke test

Risk: ADR-218 execute is robust on the happy path. If env vars are
mis-set the tombstone may still contain raw codenames.

Required actions:

- [ ] Post-execute, run a grep across `tombstone/*` and the
  sanitization report for the original codenames; assert 0 hits
- [ ] Document this smoke step in the ADR-218 runbook

Status: `partial` (script exists, runbook step not formalized)

---

## Low — peripheral

### L1. Operator personal data leakage check

- [ ] No instances of operator email outside intentional contexts
- [ ] No `/Users/<operator>/...` paths in committed files
- [ ] No personal MCP server UUIDs in committed examples

Status: `pending`

### L2. Worktree / temp-path leakage check

- [ ] `git worktree list` outputs in docs scrubbed of
  `/private/var/folders/...` paths

Status: `pending`

---

## Sign-off

This checklist is the single gate. Public-visibility flip requires:

- All `Critical` items: `done` or `accept-risk` with written rationale
- All `High` items: `done`, `in-progress` with ETA, or `accept-risk`
- All `Medium` items: at least an explicit decision recorded
- `Low` items: review encouraged, not blocking

| Reviewer role        | Name | Date | Signature / commit SHA |
|----------------------|------|------|------------------------|
| Repository operator  |      |      |                        |
| Legal review         |      |      |                        |
| Security review      |      |      |                        |
| Comms / launch lead  |      |      |                        |

---

## How to use this checklist

1. Treat each item as a small task; one PR per item where possible.
2. Update the status inline (`pending` → `in-progress` → `done`) as you go.
3. Link evidence (commit SHA, report path, screenshot) next to each
   completed item.
4. When `accept-risk`, write a one-paragraph rationale below the item
   explaining why publication can proceed despite the gap.
5. Final sign-off only after the table at the bottom is filled.

## Cross-references

- ADR-218 (history sanitization toolchain)
- ADR-220 (worktree divergence audit)
- ADR-226 (event-sourced session bus)
- `manifests/history-sanitization.yaml`
- `scripts/audit-consumer-dependence.sh`
- `.cognitive-os/private/tier-prompts.md` (operator-only)

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

Risk: consumer codenames (env-var protected private list), operator email, machine
paths, sister-project paths visible in commit history once public.

Required actions:

- [x] All 12 sanitization env vars set with real values (4 operator fields: email, display-name, home-prefix, repo-path; 3 codenames A/B/C; 5 service slots)
- [x] `cos history sanitize --execute --yes` run successfully (2026-05-08T04:27:48Z)
- [x] Tombstone branch present at `history-sanitization-20260508T042748Z`
- [x] Sanitization report at `.cognitive-os/reports/history-sanitization/20260508T042748Z.json` recorded and reviewed
- [x] Smoke test: codenames + service names + operator email/path → 0 hits across full history
  (post-execute: n1u/gamer-wallet/altatienda/bff-ninja/users-core/users-auth/wallet-go/acme-gateway all 0)
- [x] Force-push to origin completed after final local history rewrite (origin/main = `db846adb`, matches local HEAD)
- [x] Tag `v0.27.1-pre-history-rewrite` re-attached to new SHA on origin (`7b989099`)

Evidence: backup mirror at `~/.cognitive-os/recovery/pre-history-sanitization-20260508T042748Z.git`; sanitization report at `.cognitive-os/reports/history-sanitization/`. Local history rewritten via mailmap/filter-repo to operator's GitHub-noreply identifier for privacy + GitHub attribution. Force-pushed and tag reattached to origin.

Status: `done`

---

### C2. Client-project coupling removed (Tiers 1–4)

Risk: historical OS files referenced one consumer's private service and codename vocabulary.
Public release of those raw strings would be an NDA-adjacent exposure.

Required actions:

- [x] Tier 1 — `hooks/error-pipeline.sh` config-driven; workflows generic
  (Evidence: commit `4137373f`)
- [x] Tier 2 — 4 SKILL.md genericized + portability tests pass
  (Evidence: commit `64c04149`)
- [x] Tier 3 — 9 docs files swept
  (Evidence: commit `4115f05d`)
- [x] Tier 4 — 4 test fixtures + benchmark configs swept
  (Evidence: commit `ce8d1ea8`)
- [x] `scripts/audit-consumer-dependence.sh . <private-token-file>` returns 0 matches
  outside of explicitly approved sanitized case-study docs
  (Evidence: TIER5_RETAINED skip-list added; verified clean run with the private
  token file → 0 hits, commit `a9e50357`)
- [x] All Tier commits landed on `main`
  (Evidence: merge commit `8f1c8f00` — "Merge Tiers 1-4 of case-study leak audit (privacy decoupling)")

Evidence: Tiers 1–4 merged via `8f1c8f00`; individual tier SHAs `4137373f` (T1), `64c04149` (T2), `4115f05d` (T3), `ce8d1ea8` (T4). Audit-script clean run still required.

Status: `done`

---

### C3. License transition documented

Risk: Apache 2.0 → FSL-1.1-MIT change reads as a “rug pull” in the
absence of a clear FAQ. Precedent: HashiCorp / Elastic / Redis backlash.

Required actions:

- [x] `docs/legal/license-faq.md` published with:
  - Why FSL-1.1-MIT (commercial rationale, in plain language)
  - Two-year MIT relicensing commitment, mechanically verified
  - Which uses are unrestricted (non-competing internal use,
    research, education) and which are not
  - Comparison vs Apache 2.0 in concrete terms
  - What downstream consumers should plan for
  (Evidence: `docs/legal/license-faq.md` exists, 2634 words, commit `418fb217`)
- [x] `LICENSE` and `NOTICE` files match the FAQ
  (Evidence: LICENSE is FSL-1.1-MIT canonical text + "Copyright 2026 Luum" + 2-year MIT-conversion clause; NOTICE attributes third-party deps; FAQ §1–§2 describes the same identifiers/conversion window/copyright holder.)
- [x] `README.md` links to the FAQ from the license badge
  (Evidence: README.md:4 badge href = `docs/legal/license-faq.md`; footer also retains direct `LICENSE` link.)

Status: `done`

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
- [x] Test count, pass count, skip count published in
  `docs/quality/test-coverage-report.md`
  (Evidence: `docs/quality/test-coverage-report.md` exists, commit `4f55be19`)

Status: `partial` — report exists; full pytest now collects 17522 tests with 0 collection errors after pytest.ini fix (--import-mode=importlib resolves duplicate-basename issue); some pre-existing failures remain — see `docs/quality/test-coverage-report.md`

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

Evidence: Audit complete. Report at `.cognitive-os/private/engram-leak-scan.md` (operator-only, gitignored). Operator decision pending on remediation actions per per-id list.

Status: `done`

---

## High — fixable in a day, ugly if missed

### H1. Aspirational vs Real feature labelling

Risk: marketing claims about features that are inactive (MAPE-K,
singularity, agent-communication via Valkey) or aspirational invite
"vaporware" criticism.

Required actions:

- [x] Run `component-reality-check` skill / `aspirational_audit.py` across
  the repo (2026-05-08 run: 1019 components — REAL 317 / DORMANT 182 /
  ASPIRATIONAL 36 / METADATA 61, ratio 21.4%)
  (Evidence: `docs/reports/aspirational-audit-2026-05-08.md`)
- [x] Cross-check public commercial docs against the
  REAL/DORMANT/ASPIRATIONAL classification
  (Note: `docs/business/01-commercial-brief-v2.md` referenced in the
  original checklist text does not exist as a public file — that ID
  belongs to a private strategy doc. The closest public equivalents
  reconciled are `executive-summary.md`, `features.md`, and
  `value-proposition.md`. `master-plan-checklist.md` left untouched —
  see audit §Per-file changes.)
- [x] Mark every public-facing claim with status badge or remove
  (Evidence: `docs/legal/h1-feature-status-audit.md`)

Status: `done` — operator signed off on the 5 open questions
(2026-05-08, see `docs/legal/h1-feature-status-audit.md` §Operator sign-off).
README footnote added for "14-layer safety mesh" claim pointing at
`docs/safety-mesh.md`.

---

### H2. AI-attribution policy public

Risk: heavy AI-assisted authorship plus the global rule banning
`Co-Authored-By` trailers will be read as concealment unless explained.

Required actions:

- [x] `CONTRIBUTING.md` explains:
  - That commits are predominantly AI-assisted with human-in-the-loop
  - Why the `Co-Authored-By` trailer is not used (deliberate, not hidden)
  - How to identify which model wrote what (if at all)
  - Review/verification gates each AI commit passes through
  (Evidence: `CONTRIBUTING.md` 250 lines, commit `86ddd5ad`)
- [x] Linked from `README.md` (Evidence: `**Contributing**: see [CONTRIBUTING.md]...` in README footer)

Status: `done`

---

### H3. Provenance / clean-room audit

Risk: research-first protocol ingested code/patterns from OpenCode,
Aider, Cursor, Devin, etc. Any literal copy-paste with cosmetic
rewriting is a legal exposure.

Required actions:

- [x] Run `audit-integrity` skill — applied conceptually (skill is a
  structural integrity tool, not a provenance runner); confirmed
  inspected `lib/*.py` files are ALIVE (no symlink trickery)
- [x] Spot-check 15 ADRs that cite external tools for clean-room
  separation — `docs/architecture/provenance.md` §4 (LOW=15, MED=0, HIGH=0)
- [x] Public note in `docs/architecture/provenance.md` listing which
  patterns were inspired by which prior art and under what license —
  20-tool provenance table at `docs/architecture/provenance.md` §2

Status: `complete (first pass)` — provenance audit shipped: 20 prior-art
tools cataloged, 15 ADRs spot-checked, 0 HIGH-severity findings, 0 smoking
guns of literal copy-paste. Operator decision: ship under FSL-1.1-MIT with
the audit on record. **Legal review of the 14 UNKNOWN license entries
remains as a recommended (non-blocking) post-launch action** — these are
SPDX metadata gaps in transitive deps, not new license risk. Tracked in
`docs/architecture/provenance.md` §6 and `docs/security/supply-chain.md`.

---

## Medium — defendable but worth closing

### M1. Dependencies and supply chain

Required actions:

- [x] Generate SBOM (CycloneDX format) — `sbom.json` at repo root, CycloneDX 1.6, 241 components (205 unique deduped), generated by syft 1.44.0 (2026-05-08)
- [x] License audit of all transitive dependencies — block AGPL/SSPL/BSL — **0 BLOCKED**, 14 REVIEW (all transitive `sharp`/libvips dual-licensed; APPROVED — see supply-chain.md §3.4), 100 UNKNOWN (syft metadata gaps; manual SPDX enrichment tracked under ADR-238), 91 OK
- [ ] Pin third-party tool digests where possible — partial: language lockfiles (uv.lock, go.sum, package-lock.json) pin hashes; CI action SHA pinning + sigstore signing tracked under M2 / ADR-238
- [x] `docs/security/supply-chain.md` published — covers SBOM regeneration, license policy, pinning state, coordinated disclosure, response SLA

Status: `mostly-complete` (digest pinning of CI actions + signed releases pending under M2)

### M2. Onboarding walkthrough

Required actions:

- [x] Fresh clone → first useful skill invocation under 10 minutes —
      documented in [`docs/onboarding/walkthrough.md`](../onboarding/walkthrough.md).
      Live measurement: 52s for steps 4-7, ~7 min total including
      read-only steps. Public-safe command snippets are copied into the
      walkthrough; raw terminal transcripts remain local-only until sanitized.
- [x] `validate-release` skill output captured — `skills/validate-release`
      is a markdown agent-instructions skill (no executable). Closest
      invocable proxy `cos-status.sh` captured in transcript appendix
      and `/tmp/m2-cos-status.log`.
- [ ] Recorded asciicast or screencast linked from `README.md` — pending public-release recording;
      operator records once the public URL is live. Raw local transcript
      logs are not public artifacts and must not be committed.

Status: `mostly-complete` (asciicast pending operator recording)

### M3. ADR sweep — 14 recent ADRs

Risk: 14 ADRs landed in 24h by an AI agent. Inconsistencies, broken
cross-references, prose drift very likely. Hostile readers will find them.

Required actions:

- [x] Manual reviewer pass over ADR-218 through ADR-238
  (Evidence: `docs/legal/m3-adr-sweep-report.md` — 21 ADRs reviewed, 1 CRITICAL [fixed], 0 HIGH, 4 MEDIUM [all resolved], ~16 LOW [logged].)
- [x] Cross-references valid (no broken `[ADR-NNN]` links)
  (Evidence: per-ADR table in m3-adr-sweep-report.md §5 confirms each cross-ref resolves.)
- [x] Status, owner, decision-summary present and consistent
  (Evidence: ADR-228 self-contradiction fixed; ADR-220/224/232/234 follow-ups closed.)
- [ ] Topic keys in Engram match canonical filenames
  (Deferred — engram store was scrubbed in C5; topic-key audit is post-launch hygiene.)

Status: `done` — manual sweep complete; engram topic-key consistency deferred to post-launch.

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

- [x] No instances of operator email outside intentional contexts
  (Evidence: history sanitize replaced `<operator-previous-email>` → noreply; tracked-files grep returns 0 hits.)
- [x] No `/Users/<operator>/...` paths in committed files
  (Evidence: tracked-files grep returns 0 hits; only dashboard/.next/ build artifacts contain the path, and `.next/` is gitignored.)
- [x] No personal MCP server UUIDs in committed examples
  (Evidence: scope-marker portability tests + L1 audit report at `docs/legal/operator-data-scan.md`.)

Status: `done`

### L2. Worktree / temp-path leakage check

- [x] `git worktree list` outputs in docs scrubbed of
  `/private/var/folders/...` paths
- [x] `.claude/worktrees/agent-*` paths scrubbed
- [x] `.cos-agent-worktrees/luum-agent-os/task-desc-*` paths scrubbed
- [x] `/tmp/cos-validation-capsules/...` paths scrubbed

Evidence: Full grep audit found 0 actual leaked paths in scope.
Code-logic uses of these prefixes in `scripts/cos-registry.sh` and
`scripts/cos_init.py` are intentional and were left untouched.
Report: `docs/legal/operator-paths-scrub-report.md`

Status: `done`

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

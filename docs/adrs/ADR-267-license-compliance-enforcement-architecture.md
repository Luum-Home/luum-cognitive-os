---
adr: 267
title: License-Compliance Enforcement Architecture
status: accepted
implementation_status: partial
date: '2026-05-11'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: accepted record with explicit pending/deferred/planned scope
---

# ADR-267 — License-Compliance Enforcement Architecture

## Status

Accepted (2026-05-11)

## Context

After the 2026-05-11 multi-tool deep-research batch (HelixDB / iFixAi / MegaMemory; 19 docs across `docs/research/*-annex-*-2026-05-11.md` + 3 radar addenda + 4 self-critique cluster reports + 3 ADRs Proposed: ADR-261..266) and the pre-commit license audit triggered by operator, two enforcement gaps were surfaced that compound risk over time:

- **Gap 1**: Every new external-tool adoption goes through `/repo-scout` + `/deep-tool-research` and produces an Annex F (compliance / clean-room protocol). Each individual adoption is **defendible under fair-use / clean-room doctrine** today. The risk is *accumulation*: we do not have mechanical limits or signals that say "we now hold N tools pending legal validation; further adoption raises aggregate risk."
- **Gap 2**: Hook coverage on the actual commit-time defenses is *paper-thin*. The two existing clean-room gates (`hooks/external-pattern-cleanroom-gate.sh`, `hooks/external-pattern-cleanroom-gate.sh`) are tool-specific or hardcoded to absent paths (`/tmp/upstream-pattern-source/`) and currently skip silently in most sessions. `rules/license-policy.md` is policy text, not enforcement; no hook reads it on `git commit`.

The two scenarios the operator wants ready for:

- **Scenario A** — luum becomes OSS public. Defendible position requires SBOM, SPDX headers, NOTICE / THIRD-PARTY-LICENSES discipline, and clean research → runtime separation.
- **Scenario B** — luum becomes commercial / SaaS product. The licence-policy table (AGPL / SSPL / BSL / ELv2 = BLOCKER) must become commit-time enforcement, not just doc; and there must be a mechanical "STOP new adoptions until legal IP review" switch the operator can flip.

### Current state inventory

**Pre-commit hooks with license-adjacent function:**

| Surface | What it does today | Limitation |
|---|---|---|
| `hooks/external-pattern-cleanroom-gate.sh` | Pre-commit; matches `git commit`; scans staged files for literal strings from `/tmp/upstream-pattern-source/` | Hardcoded to a single absent directory; skip silently if source absent. Mostly inert. |
| `hooks/external-pattern-cleanroom-gate.sh` | Same shape as above, holaOS-specific | Single tool. |
| `scripts/cos-dependency-adoption-gate` (ADR-208) | Pre-commit on dependency-manifest additions; requires `manifests/<dep>-adoption.yaml` evidence | Validates *process* (is the manifest present?); does NOT classify the dependency's licence against `rules/license-policy.md`. |
| `rules/license-policy.md` | Doc with BLOCKER / SAFE table | No hook reads it on commit. |

**Manual scripts (no auto-trigger on commit):**

- `scripts/license-audit-syft-grype.sh`, `scripts/license-audit-trivy.sh` — SBOM + license inventory.
- `scripts/cos-cross-stack-license-audit` (ADR-212).
- `scripts/agentic_tool_license_matrix.py` — tooling matrix.

### Coverage delta versus scenarios

**Scenario A — OSS public:**

- ✅ Research-only research paths (`docs/research/`) are separated from runtime (`lib/`, `packages/`, `scripts/`). The 2026-05-11 batch did NOT vendor code into runtime.
- ✅ Attribution headers present in the 18 research annexes (after the compliance pass).
- ❌ No SBOM auto-generated at commit.
- ❌ No SPDX-License-Identifier required on new source files.
- ❌ No NOTICE / THIRD-PARTY-LICENSES file maintained automatically.

**Scenario B — commercial / SaaS:**

- ✅ `rules/license-policy.md` table is correct (AGPL / SSPL / BSL / ELv2 listed as BLOCKER).
- ✅ Radar intake rejects AGPL at scout time (HelixDB stayed REJECT runtime).
- ❌ No pre-commit licence scanner on *staged content* — code containing AGPL strings could be committed to `lib/` without a block.
- ❌ No mechanical *freeze* — "STOP new adoptions until legal review" depends today on orchestrator discipline.
- ❌ No "legal review required" gate — any session can land a new Annex F without an ADR Accepted by legal.
- ❌ No aggregate counter of *adoption debt* (tools holding Annex F without `reviewed-by-legal: yes`).

## Decision

Adopt a layered defence: **six new pre-commit hooks**, **two new manifests + scripts** for governance, and **one new ADR (this one) plus a future legal-review-gate ADR**, while acknowledging the hard limit that **hooks reduce probability of error; they do not establish legal compliance**.

### Layer 1 — Hooks (pre-commit defence)

Implementation order matches Sprint plan below; numbering matches the original analysis.

| # | Hook | Scenario | Effort | What it blocks |
|---|---|---|---|---|
| 1 | `dependency-license-classifier.sh` | A + B | ~0.5 PW | Pre-commit. If staged modifies `requirements.txt` / `pyproject.toml` / `package.json` / `Cargo.toml`, runs `pip-licenses` (Python) or `npx license-checker` (Node) or `cargo-license` (Rust) on the *new* package set and blocks commit if any dependency's SPDX appears in BLOCKER list of `rules/license-policy.md`. |
| 2 | `external-cache-content-leak.sh` | A + B | ~0.5 PW | Generalises `external-pattern-cleanroom-gate.sh`. Scans staged content against the whole tree under `.cognitive-os/external-source-cache/` (instead of one hardcoded path). Blocks if any string longer than N characters in a staged file matches a string in any cached clone. |
| 3 | `adoption-freeze-gate.sh` | B (critical) | ~0.3 PW | Reads `manifests/external-tool-adoption-freeze.yaml`. If `frozen: true`, blocks any commit touching `docs/research/*-annex-*`, `docs/reports/external-tools-radar-*`, or `manifests/external-tools-adoption.yaml`. This is the kill-switch for "STOP new adoptions until legal review". |
| 4 | `spdx-header-required.sh` | A | ~0.3 PW | Pre-commit. New files in `lib/` / `packages/` / `scripts/` MUST include `SPDX-License-Identifier:` in the first 5 lines. Blocks if missing. |
| 5 | `attribution-completeness-validator.sh` | A + B | ~0.5 PW | Pre-commit. Files in `docs/research/*-annex-*` containing code-fence blocks MUST have a top-of-file licence-attribution header AND each verbatim block MUST have a block-level source-path attribution. Blocks if missing. Closes the gap the 2026-05-11 batch nearly tripped on. |
| 6 | `research-to-runtime-firewall.sh` | A + B | ~0.5 PW | Pre-commit. Blocks if code in `lib/` / `packages/` / `scripts/` imports from or copies content from `.cognitive-os/external-source-cache/`. Closes the research→runtime leak path. |

**Total**: ~2.6 PW. All six hooks must be registered in the security profile JSONs (minimal / standard / paranoid), in `.claude/settings.json`, and in `scripts/apply-efficiency-profile.sh`, per the contract established by ADR-265 / ADR-266 follow-up audit.

### Layer 2 — Governance manifests

#### `manifests/external-tool-adoption-freeze.yaml` (new)

```yaml
schema_version: external-tool-adoption-freeze/v1
frozen: false
frozen_at: null
frozen_by: null
freeze_reason: null
unfreeze_requires:
  - legal-ip-review-completed
  - operator-explicit-sign-off
freeze_history: []
```

Operator flips `frozen: true` when entering pre-commercial / pre-SaaS phase. Hook #3 reads this manifest on every commit.

#### `scripts/cos-adoption-debt-audit` (new)

CLI that walks `docs/research/*-annex-f-*-2026-*.md` and counts:

- Tools with Annex F present but no `reviewed-by-legal: yes` marker in the frontmatter (= **adoption debt**).
- Tools with Annex F present and `reviewed-by-legal: yes` (= cleared).
- Tools with Annex F missing entirely (= incomplete pipeline; should not exist).

Output: JSON + Markdown report at `docs/reports/adoption-debt-latest.{json,md}`. Run weekly via cron or on demand. Aggregates the "compounding risk" signal the operator flagged.

### Layer 3 — Policy ADR (separate, future)

A future ADR (working title: "Pre-adoption legal review gate") will:

1. Define the legal-review checklist (clean-room evidence, attribution headers, NOTICE if Apache, licence-classification cite from `rules/license-policy.md`).
2. Define `reviewed-by-legal: yes|no|pending` as a required field in every Annex F frontmatter.
3. Require an Accepted ADR per tool family before any Annex F primitive enters apply phase.

This ADR-267 sets up the *enforcement infrastructure*; the legal-review-gate ADR sets up the *content of what enforcement validates*.

### Layer 4 — Acknowledged hard limit

Hooks cannot:

- Determine whether a primitive is a derivative work under copyright law.
- Determine whether use of Apache-2.0 §4.b reproduction-with-attribution is legally sufficient.
- Substitute for legal counsel review.

Hooks reduce the probability of error and force consistent process; they do not establish compliance. Every new tool family adoption with a non-trivial licence (Apache, MIT-with-copyright-required, anything else) requires legal validation before primitives enter apply phase, regardless of how many hooks pass.

## Consequences

### Positive

- Mechanical defence against AGPL / SSPL / BSL / ELv2 strings reaching commits.
- Mechanical kill-switch for "stop new adoptions" without depending on orchestrator discipline.
- Adoption debt becomes visible and tracked, not hidden.
- Research → runtime leak path explicitly firewalled.
- Attribution discipline enforced on the surface that nearly tripped today (research annexes).
- Both scenarios A and B become defendible at commit time, not only at scout time.

### Negative

- Six new hooks add ~30-80 ms cumulative to each `git commit` (estimate based on similar string-scan hooks in repo). Latency budget must be checked.
- `external-cache-content-leak.sh` (#2) will have false positives on common-token matches; needs careful threshold tuning. May initially block legitimate commits while tuned.
- `attribution-completeness-validator.sh` (#5) only runs on the `docs/research/*-annex-*` glob — if the orchestrator invents a different doc structure for the next tool, the gap re-opens.
- `dependency-license-classifier.sh` (#1) depends on external classifier tools (`pip-licenses`, `license-checker`, `cargo-license`) being installed locally. Missing tool → hook either blocks (annoying) or skips (defeats purpose). Decision deferred to implementation.
- The freeze mechanism (#3) is a heavy switch — if turned on and the orchestrator does not realise it, sessions silently fail commits. Needs a startup-time banner that flags `frozen: true`.

### Neutral

- ADR-267 codifies infrastructure; the legal-review-gate ADR (future) codifies content. Both are required before commercial / SaaS launch.
- Adoption-debt counter exposes a number that today is implicit. The number may be uncomfortable when first run; that is the point.

## Open questions

1. **Hook latency budget** — what is the acceptable additional commit latency? Estimate 30-80 ms cumulative; needs measurement on the actual repo.
2. **External classifier tool fallback** — if `pip-licenses` not installed, does Hook #1 block (forcing install) or skip (defeats purpose)? Lean **block + clear install instructions**, but operator decision.
3. **Common-token threshold for Hook #2** — what string length and what generic-token allowlist minimises false positives without making the scan trivially bypassable? Suggest start at length ≥ 40 chars; refine in soak.
4. **Should `frozen: true` block commits that *unfreeze* the manifest itself?** If yes → operator needs an explicit bypass env var to flip the switch. Lean **yes**, with `COS_ALLOW_FREEZE_TOGGLE=1` bypass.
5. **Adoption debt reporting cadence** — weekly cron, on-demand, or both? Lean **both**: weekly cron + on-demand for pre-commercial gate.
6. **Threshold to trigger legal review** — N tools pending? Time-based (every K months)? Risk-weighted (any AGPL-adjacent tool = immediate)? Defer to legal-review-gate ADR.
7. **Compliance dashboard** — surface adoption-debt + freeze status + last legal-review date in `/cos-status` or a dedicated page? Defer; not blocking.

## Implementation phases

### Phase 1 — Critical kill-switch + dependency scanner (1 session, ~1.3 PW)

- Hook #3 `adoption-freeze-gate.sh` + `manifests/external-tool-adoption-freeze.yaml`
- Hook #1 `dependency-license-classifier.sh`
- Hook #6 `research-to-runtime-firewall.sh`

These three give scenario B its mechanical kill-switch and the highest-blast-radius leak paths immediate coverage.

### Phase 2 — Content-leak + structural gates (1 session, ~1.3 PW)

- Hook #2 `external-cache-content-leak.sh`
- Hook #4 `spdx-header-required.sh`
- Hook #5 `attribution-completeness-validator.sh`

These tighten the surface; less urgent but close the same family of risks.

### Phase 3 — Governance plumbing (~0.5 session)

- `scripts/cos-adoption-debt-audit` + report generator
- Weekly cron registration
- Startup-time banner for `frozen: true` state

### Phase 4 — Legal-review-gate ADR (separate, async)

Drafted in a follow-up session with operator + legal input. Defines `reviewed-by-legal: yes|no|pending` frontmatter contract for Annex F files and the per-tool ADR-Accepted requirement.

## Verification

Each hook ships with golden-file tests proving:

- Hook #1: AGPL dep added to `pyproject.toml` → block. MIT dep added → pass.
- Hook #2: a staged file containing a ≥40-char string also present in `.cognitive-os/external-source-cache/helix-db/` → block. Generic tokens only → pass.
- Hook #3: `frozen: true` + commit touching `docs/research/*-annex-*` → block. `frozen: false` → pass.
- Hook #4: new `lib/foo.py` without SPDX header → block. With `# SPDX-License-Identifier: Apache-2.0` → pass.
- Hook #5: new `docs/research/*-annex-*` file with code-fence block and no attribution → block. With per-block source paths → pass.
- Hook #6: new file in `lib/` importing or string-referencing `.cognitive-os/external-source-cache/` → block. Pure reference in `docs/research/` → pass.

`scripts/cos-adoption-debt-audit` ships with a fixture-driven test: 3 annex-F files with mixed `reviewed-by-legal` values → audit reports correct counts.

## Related

- `rules/license-policy.md` — the policy table this enforcement validates against
- ADR-006 — AGPL licence compliance (Redis/MinIO replacement) — first AGPL gate established at intake
- ADR-208 — imported-pattern closure contract — dependency-adoption-gate prior art
- ADR-212 — cross-stack license-audit toolchain (Syft + Grype) — surfaces this ADR repurposes
- ADR-259 — external-pattern adoption posture — defines the Annex F structure this ADR enforces
- ADR-261..264 — holaOS adoption ADRs — original motivation for clean-room enforcement
- ADR-265 — mandatory-minimum inspection caps — example of governance-policy reclassification this ADR makes auditable
- ADR-266 — protected-config-write-guard Bash coverage — same hook-coverage-gap class
- `docs/research/orchestrator-self-critique-cluster-d-claim-quality-2026-05-11.md` Finding 9 — surfaced the mandatory-minimum cap as governance, not primitive; precedent for compliance-as-content
- `docs/architecture/external-tool-adoption-doctrine.md` — adopt commodity mechanisms, build governance semantics
- `docs/architecture/external-tool-adapter-taxonomy.md` — adoption kinds (dependency / CLI adapter / schema port / algorithm port / testdata vendor / operator-installed / pattern-only)

## Implementation Status (2026-05-11)

Phase 1 + Phase 2 Layer-1 hooks landed in two sessions (2026-05-11). Status of the six hooks defined in §Layer 1:

| # | Hook | Status | Notes |
|---|---|---|---|
| 1 | `hooks/dependency-license-classifier.sh` | landed | Pre-commit BLOCKER-string scan on staged dep-manifest diffs (`requirements.txt`, `pyproject.toml`, `package.json`, `Cargo.toml`). Bypass: `COS_ALLOW_LICENSE_CLASSIFIER_BYPASS=1`. Log: `dependency-license-classifier.jsonl`. |
| 2 | `hooks/external-cache-content-leak.sh` | landed | Generalises `external-pattern-cleanroom-gate.sh` to the whole `.cognitive-os/external-source-cache/` tree. Bypass: `COS_ALLOW_EXTERNAL_CACHE_LEAK=1`. Log: `external-cache-content-leak.jsonl`. |
| 3 | `hooks/adoption-freeze-gate.sh` | landed (Phase 1) | Reads `manifests/external-tool-adoption-freeze.yaml`; blocks gated paths when `frozen: true`. Bypass: `COS_ALLOW_ADOPTION_FREEZE_BYPASS=1`, manifest-only toggle via `COS_ALLOW_FREEZE_TOGGLE=1`. |
| 4 | `hooks/spdx-header-required.sh` | landed | NEW files under `lib/`, `packages/*/lib/`, `scripts/` (.py/.sh/.js/.ts) MUST carry `SPDX-License-Identifier:` in first 10 lines. Existing files at hook-install snapshot time are grandfathered (`manifests/spdx-grandfather.txt`). Bypass: `COS_ALLOW_MISSING_SPDX=1`. |
| 5 | `hooks/attribution-completeness-validator.sh` | landed | `docs/research/*-annex-*.md` must carry `Source-Pattern:` + `License:` + `Clean-Room-Protocol:` and per-block attribution for verbatim code fences. Bypass: `COS_ALLOW_INCOMPLETE_ATTRIBUTION=1`. |
| 6 | `hooks/research-to-runtime-firewall.sh` | landed | Blocks runtime files referencing `.cognitive-os/external-source-cache/`. Bypass: `COS_ALLOW_RESEARCH_RUNTIME_LEAK=1`. |

Layer 2 (governance manifests + adoption-debt audit) and Layer 3 (legal-review-gate ADR) remain on the original roadmap and are tracked as Phase 3 / Phase 4 follow-ups.

A separate ADR (ADR-268) documents the defensive history sanitization performed on the same day; it cross-references this ADR as the forward enforcement mechanism that replaces ad-hoc attribution discipline.

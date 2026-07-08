---
type: methodology-synthesis
source: docs/05-Methodology/root/executable-acceptance-specification.md
provenance: "Defines EAS as the optional documentation artifact that bridges prose requirements to executable proof for large, critical, ambiguous, or cross-team SDD changes."
---

## What it is

Executable Acceptance Specification (EAS) — an optional artifact format (not a workflow, and not itself a testing style) for turning intent and technical decisions into executable evidence. Positioned as: SDD = process, EAS = artifact/documentation format, ATDD/TDD = execution/verification style. EARS ("Easy Approach to Requirements Syntax") is EAS's preferred syntax for functional requirements.

## Key mechanics

- **10 required sections**: Intent; Requirements (functional/non-functional/operational/security/compatibility, EARS-syntax preferred: `WHEN`/`IF...THEN`/`WHILE`/`WHERE`/ubiquitous `THE SYSTEM SHALL`); Non-goals; Executable Acceptance Criteria (measurable, command-based); Gap Matrix (every requirement -> acceptance criterion -> evidence -> gap status — the "anti-theater section"); Adversarial Personas (product/maintainer/security/SRE/QA/architecture/detractor, at least one structurally skeptical); Detractor Mode; Detractor Objection Log (each objection resolved by evidence, converted to a task, or carried as residual risk); Verification Commands (exact commands with expected outcomes); Residual Risks (explicit, owned, bounded, or explicitly none).
- **Detractor Mode** is a mandatory Tenth-Man/Devil's-Advocate-inspired reviewer role with 5 selectable intensity modes matched to risk: Tenth Man Rule (premature consensus), Devil's Advocate (any medium+ plan), Pre-mortem (rollout/migration/release/architecture risk), Black Hat (Six Thinking Hats style), Red Team (security/abuse/prompt-injection scope). Not a default veto — a structured obligation to argue the contrary case.
- **SDD integration points**: requirements/acceptance during `sdd-spec`; tasks derived from gap matrix during `sdd-tasks`; uncovered rows implemented during `sdd-apply`; `scripts/eas_validate.py` run + objections resolved during `sdd-verify`; final EAS with evidence saved during `sdd-archive`.
- **Validator**: `python3 scripts/eas_validate.py [--require-ears] path/to/eas.md` — fails if required sections are missing, requirements lack acceptance/evidence, Detractor is absent, objections are unresolved, verification commands are missing, or residual risks aren't explicit. `--require-ears` escalates the EARS-syntax check from warning to blocking error.
- **Minimum bar**: every requirement has ≥1 acceptance criterion with a verification method; gap matrix maps every requirement to evidence; detractor log has ≥1 real objection with disposition; residual risks named or explicitly absent; `sdd-verify` can decide pass/fail from the artifact alone.

## Relations & where used

- Compatible-with table maps EAS to EARS, PRD, RFC, ADR, Gherkin, OpenAPI/AsyncAPI, test plans, and threat models — EAS references/embeds these rather than replacing them.
- Related artifacts named in-source: ADR (executable-acceptance-specification-eas, file named `ADR-324-...`), ADR (detractor-review-modes, `ADR-319-...`), `templates/eas.md`, `rules/eas-evidence-artifact.md`, `scripts/eas_validate.py`, `rules/acceptance-criteria.md`, `rules/adversarial-review.md`.
- `rules/eas-evidence-artifact.md` is also referenced in `RULES-COMPACT.md` under Change Safety as `[eas-evidence-artifact]`.

## Status / caveats

- **Source inconsistency**: the "Related Artifacts" section labels the EAS decision record "ADR-317" but gives its actual file path as `ADR-324-executable-acceptance-specification-eas.md` — the number in the label (317) does not match the number in the filename (324). Not fixed here per instructions; flagged for operator follow-up.
- The document is normative/prescriptive (a spec for how to write EAS artifacts), not a report of current EAS adoption — it does not state how many changes currently use EAS.

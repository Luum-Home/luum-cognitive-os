<!-- SCOPE: both -->
<!-- TIER: 1 -->
---
enforcement: agent-instruction
trigger_priority: medium
routing_patterns:
- pattern: \bEAS\b
  confidence: 0.95
- pattern: \bExecutable Acceptance Specification\b
  confidence: 0.95
- pattern: \bSDD Evidence Artifact\b
  confidence: 0.9
- pattern: \bEARS\b
  confidence: 0.9
- pattern: \bEasy Approach to Requirements Syntax\b
  confidence: 0.9
- pattern: \bdetractor objection log\b
  confidence: 0.9
- pattern: \b(Tenth Man|Devil'?s Advocate|Pre-mortem|Black Hat|Red Team)\b
  confidence: 0.82
- pattern: \bgap matrix\b
  confidence: 0.78
summary_line: Use EAS when significant work needs executable acceptance evidence; use EARS syntax for functional requirements inside it.
routing_intents:
- intent: eas_artifact_request
  description: User asks for EAS, EARS, an SDD evidence artifact, executable acceptance documentation, gap matrix coverage, named detractor modes, or detractor objections.
  confidence: 0.9
---
# Executable Acceptance Specification (EAS) Rule

## Purpose

EAS is an optional evidence artifact for significant SDD work. It converts intent and documentation into executable acceptance evidence. EARS is not the same acronym: EARS means Easy Approach to Requirements Syntax and is the preferred syntax for functional requirement statements inside EAS.

## When To Use

Use EAS when the user asks for EAS, EARS-backed requirements, or an SDD evidence artifact; the change is large, critical, cross-service, security-sensitive, or migration-related; acceptance criteria need to map to ATDD/TDD tests; multiple documentation formats need one evidence bridge; or a gap matrix, Tenth Man Rule, Devil's Advocate, Pre-mortem, Black Hat, Red Team, or detractor review is required.

Do not force EAS onto trivial or small changes unless the user explicitly asks.

## Required Sections

An EAS artifact must include Intent, Requirements, Non-goals, Executable acceptance criteria, Gap matrix, Adversarial personas, Detractor mode, Detractor objection log, Verification commands, and Residual risks. Functional requirement rows should follow EARS patterns when possible: `WHEN ... THE SYSTEM SHALL ...`, `IF ... THEN THE SYSTEM SHALL ...`, `WHILE ... THE SYSTEM SHALL ...`, `WHERE ... THE SYSTEM SHALL ...`, or `THE SYSTEM SHALL ...`.

Use `templates/eas.md` as the canonical starter template.

## Review Rule

An EAS review is incomplete unless every requirement maps to evidence, every acceptance criterion has a verification method, the detractor mode is selected, the detractor log contains at least one substantive objection, each detractor objection is resolved or explicitly carried as residual risk, and residual risks are explicit and bounded.

Run `python3 scripts/eas_validate.py <eas.md>` before accepting an EAS artifact as complete. Run `python3 scripts/eas_validate.py --require-ears <eas.md>` when EARS syntax is required by the user or project policy.

## Detractor Role

The detractor is a Tenth-Man / Devil's-Advocate-inspired reviewer. It must make the strongest plausible case that the EAS, plan, or implementation will fail before implementation or final verification. Select one or more compatible modes:

- Tenth Man Rule for consensus traps or suspicious convergence.
- Devil's Advocate for general skeptical questioning.
- Pre-mortem for release, migration, rollout, or operational failure analysis.
- Black Hat for structured risk-focused review.
- Red Team for adversarial misuse, prompt-injection, abuse, or security threats.

The role is not a veto by default. Every detractor objection must become evidence, a task, or an explicit residual risk.

## SDD Integration

- `sdd-spec`: creates or updates EAS requirements and acceptance rows when EAS is requested or risk warrants it.
- `sdd-tasks`: derives work from uncovered gap-matrix rows and acceptance rows.
- `sdd-apply`: implements against acceptance rows and records evidence for each changed row.
- `sdd-design, sdd-verify`: runs `scripts/eas_validate.py`, executes verification commands, checks detractor dispositions, and reports residual risks.
- `sdd-archive`: persists final EAS evidence.

## Contextual Trigger

- Pattern: `\bEAS\b`
- Pattern: `\bExecutable Acceptance Specification\b`
- Pattern: `\bSDD Evidence Artifact\b`
- Pattern: `\bEARS\b`
- Pattern: `\bEasy Approach to Requirements Syntax\b`
- Pattern: `\bdetractor objection log\b`
- Pattern: `\b(Tenth Man|Devil'?s Advocate|Pre-mortem|Black Hat|Red Team)\b`
- Pattern: `\bgap matrix\b`
- User asks for executable acceptance documentation, EAS, EARS, ATDD/TDD mapping, gap coverage, or detractor review.

---
type: reference-synthesis
source: docs/08-References/business/openclaw-remaining-patterns.md
provenance: "Catalogs the 25 OpenClaw agent-framework patterns not yet adopted by Cognitive OS, rating each by fintech relevance and effort so they can be triaged and sequenced (companion to the implementation roadmap)."
---

## What it is

A 25-entry reference catalog of OpenClaw patterns absent from Cognitive OS.
Each entry gives what the pattern does, the OpenClaw source reference (file/
directory names in the OpenClaw codebase), fintech relevance rating
(CRITICAL/HIGH/MEDIUM/LOW), effort estimate, and dependencies, closing with a
25-row summary matrix.

## Key mechanics

- **CRITICAL-rated patterns** (7): Heartbeat System, Standing Orders, Webhook
  System, Cron Jobs, Hooks Lifecycle — the foundational automation/scheduling
  layer needed for portfolio monitoring, settlement tracking, reconciliation,
  and compliance triggers.
- **HIGH-rated patterns** (5): Canvas System (HTML dashboards), Message
  Debouncing (alert batching), Canvas Actions, Plugin Architecture, Auth
  Monitoring, Session Compaction Hooks — support capabilities that
  materially improve fintech operations UX and reliability.
- **MEDIUM/LOW-rated patterns** (13): BOOTSTRAP.md, USER.md, TOOLS.md,
  BOOT.md, Envelope System, Gmail PubSub, Polling System, Testing Framework,
  Release Workflow, Coding Agent Delegation, Video/Audio Processing,
  Onboarding Wizard, Migration Tools, Hook Packs — lower-urgency
  infrastructure and DX items.
- Each entry pairs a fintech-specific justification (e.g. Standing Orders:
  "price alerts, limit orders, balance warnings, compliance triggers";
  Webhook System: "bank transaction notifications, payment confirmations,
  KYC status updates") with a named OpenClaw source location, keeping the
  catalog traceable back to the origin implementation being studied.
- The closing **Summary Matrix** condenses all 25 rows into a single sortable
  table (Pattern | Fintech Relevance | Effort | Key Dependencies) for quick
  triage.

## Relations & where used

- Feeds directly into `openclaw-implementation-roadmap.md`, which sequences
  these 25 patterns into a 4-phase, 12-week plan ordered by the
  criticality/dependency data captured here.
- Provides the fintech-domain grounding referenced obliquely in
  `open-source-design.md`'s plugin classification discussion (fintech plugin
  rules, compliance auditor agents) and in the industry-preset framing of
  `features.md`.

## Status / caveats

- Purely a **reference/comparison catalog** — it documents what OpenClaw has
  that Cognitive OS lacks as of this writing; it makes no claim that any of
  these 25 patterns have been implemented in Cognitive OS. Cross-reference
  `openclaw-implementation-roadmap.md` (all items unchecked) and
  `master-plan-checklist.md` for whether any have since landed.
- OpenClaw source-reference paths (e.g. `hooks/`, `canvas/server.ts`,
  `core/debouncer.ts`) describe OpenClaw's internal structure as observed at
  the time of the audit; they are not Cognitive OS paths and may drift if
  OpenClaw's codebase changes.
- No internal inconsistency found; the 25 individual entries and the summary
  matrix agree with each other (relevance/effort/dependency values match
  across both).

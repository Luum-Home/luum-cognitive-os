# Auto-Rollback Hardening Plan — 2026-05-02

<!-- SCOPE: os-only -->

## Goal

Convert auto-rollback from automatic destructive rollback into rollback planning and approval.

## Acceptance Criteria

- [x] ADR-107 documents the human-approved rollback boundary.
- [x] Trigger emits plan-required messaging in every phase.
- [x] Rule and skill forbid automatic destructive git execution.
- [x] Tests cover all phases and metric schema.
- [x] Contract test fails if automatic rollback execution language returns.

---
title: Harness Golden Fixtures
date: 2026-05-08
status: draft-before-implementation
source_index: docs/reports/external-tools-radar-INDEX.md
source_reports:
  - docs/reports/cross-check-C-orchestration-2026-05-08.md
related_tools: [agentapi]
---

# Harness Golden Fixtures

## Goal

Use external harness fixtures to harden COS cross-harness parsing without
adopting another agent control plane wholesale.

The radar recommends starting with agentapi testdata/fixtures rather than its
runtime sidecar. This is the lowest-risk adoption: fixtures reveal formatting
edge cases across Claude Code, Codex, Aider, Gemini, Amp, Goose, and similar
CLIs without forcing COS into agentapi's HTTP server model.

## Adoption kind

`testdata-vendor` first. Runtime adapter later only if a concrete product flow
needs it.

## Required vendor contract

Before vendoring fixtures:

- verify license and NOTICE requirements;
- preserve source commit hash and upstream path;
- store fixtures under a dedicated testdata directory;
- add a README explaining provenance and update process;
- never claim agentapi runtime integration from fixture-only adoption.

## Parser behavior to test

- explicit harness type selection;
- malformed/missing message delimiters;
- streaming partial messages;
- tool call and assistant text interleaving;
- terminal escape/control sequences;
- JSON/plaintext mode mismatches;
- provider-specific assistant role markers;
- failure/timeout message shapes.

## COS-specific assertions

Fixtures should feed COS adapters and verify:

- normalized message envelope;
- no invented provider identity;
- run/session ID preservation;
- claim/evidence extraction does not overparse;
- sensitive paths/tokens are redacted before reports;
- handoff/flight-recorder events remain stable across harnesses.

## Acceptance criteria before code

- Fixture license is documented.
- Testdata path and update process are documented.
- Fixture parser contract exists before vendoring.
- Public docs say "test fixture adoption", not runtime integration.

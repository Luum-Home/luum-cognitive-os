<!-- SCOPE: os-only -->
---
name: __contracts__
description: Internal namespace for harness-contract skills that define executable reference contracts for Cognitive OS primitives.
version: "1.0.0"
audience: os-dev
user-invocable: false
tags: [contracts, internal, harness]
---

# Contract Skills Namespace

This directory groups internal contract skills. These skills are loaded by tests
and implementation audits rather than by normal operator workflows.

## Current contract skills

- `canonical-event-emitter/` defines the canonical event-emitter reference
  contract used by ADR-064 validation.

## Usage

Use the child contract skill directly when a test or migration needs an
executable reference contract. Do not invoke this namespace skill as a workflow.

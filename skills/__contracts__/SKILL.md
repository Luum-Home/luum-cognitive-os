<!-- SCOPE: os-only -->
---
name: __contracts__
version: 1.0.0
description: Structural namespace for shared Cognitive OS skill contracts used by other agentic primitives.
triggers: []
user-invocable: false
audience: os-dev
routing_patterns:
  - pattern: '\b__contracts__\b'
    confidence: 0.95
  - pattern: '\bskill\s+contracts?\b'
    confidence: 0.75
---

# Contracts Namespace

This directory groups non-user-facing contract skills used by other Cognitive OS
agentic primitives. Keep concrete contracts in child directories so each one has
its own `SKILL.md`, examples, and validation surface.

## Contextual Trigger

This namespace is not loaded directly. Use the child contract skills instead.

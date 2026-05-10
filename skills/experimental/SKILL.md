<!-- SCOPE: os-only -->
---
name: experimental
version: 1.0.0
description: "Use when you need this Cognitive OS skill: Structural namespace for experimental Cognitive OS skills that are not promoted to stable catalog surfaces yet.; do not use when a narrower skill directly matches the task."
triggers: []
user-invocable: false
audience: os-dev
routing_patterns:
  - pattern: '\bexperimental\b'
    confidence: 0.95
  - pattern: '\bexperimental\s+skills?\b'
    confidence: 0.85
---

# Experimental Skills Namespace

This directory is reserved for experimental skills that need an explicit home
before promotion, archival, or removal. Place runnable skills in their own child
directories once they have a stable contract.

## Contextual Trigger

This namespace is not invoked directly.

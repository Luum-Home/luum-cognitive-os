# cos-self-knowledge

Canonical self-knowledge package for Cognitive OS.

## Purpose

This package owns the repository self-knowledge surface introduced by ADR-037:

- API surface snapshots
- glossary data
- dependency graph snapshots
- rebuildable self-knowledge artifacts

The runtime entrypoint is `lib/self_knowledge.py`, which is projected into the
top-level `lib/` tree for compatibility.

## Why this package exists

Self-knowledge is product-facing infrastructure, not just a documentation dump.
It gives the OS a durable way to reason about its own public surface without
re-scanning the entire repository on every session.

## Main contents

- `lib/self_knowledge.py`

## Rebuild contract

When the API surface or core structure changes, regenerate the corresponding
artifacts under `.cognitive-os/self-knowledge/` as part of the same change.

## References

- `docs/02-Decisions/adrs/ADR-037-self-knowledge-base.md`

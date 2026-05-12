# External Tools Deep Dives

This directory contains targeted deep dives for tools that move beyond broad
radar mention into candidate, pilot, adopt, integrate, or cleanup decisions.

A consumer project does not copy this structure. Consumer projects reference the
COS adoption manifest and add lightweight local evidence through
`.cognitive-os/external-tools-overlay.yaml`.

Every deep dive should cover:

- scope and problem fit;
- license and provenance;
- footprint across OS repo, consumer projects, service mode, and Docker runtime;
- adapter boundary;
- tests and consumer proof;
- rollback or deprecation path;
- public-claim boundary.

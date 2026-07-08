---
type: methodology-synthesis
source: docs/05-Methodology/runbooks/public-launch-day.md
provenance: "Sequenced, single-operator runbook for flipping the luum-cognitive-os repository from internal to public, so the irreversible visibility flip is executed only after verified pre-flight checks and with a defined rollback path."
---

## What it is

An operator-only runbook (explicitly "do not delegate") for the public launch of the repository, organized by clock offset relative to T-0 (the moment GitHub visibility flips to public).

## Key mechanics

- Prerequisites gate the flip: closed 14/14 readiness checklist, published `TRANSPARENCY.md`, published history-sanitization narrative, an off-repo recovery mirror, a clean local working tree, and `node` available in PATH (required by the release-confidence bundle's opencode adapter smoke test).
- **T-30min**: manual incognito README/link walkthrough; a `git log --all -p` privacy grep expecting only two known disclosure-text matches; a placeholder-token grep to catch any real consumer name leaking into history; a `git rev-parse` comparison confirming local HEAD matches `origin/main` (7 commits were pending publication at time of writing — must publish before T-0); confirmation a `pre-history-sanitization-*.git` recovery mirror exists off-repo; and a SHA/line-count hash check against `pre-sanitization-sha-inventory-2026-05-07.txt` as the public "tombstone" proof of scoped rewrite.
- **T-0**: strictly sequential, non-parallel steps — publish remaining commits, flip visibility via GitHub UI Danger Zone (with typed confirmation and a screenshot for the launch record), cut a signed annotated tag `v1.0.0` (`git tag -s` + `git tag -v` must succeed; falls back to an unsigned tag with a 24-hour disclosed-gap update to `release-signing.md` if signing material isn't ready), then publish the tag.
- **T+15min**: public incognito render check (TRANSPARENCY.md, evidence-chain links, LICENSE/NOTICE, sbom.json), SBOM CycloneDX 1.6 format check via `jq`, a fresh-clone signature verification of the tag (pre-v1.0.0 unsigned-gap window expects `error: no signature found`, which must be documented as a disclosed gap), and opening a `launch-day-{date}` tracking issue/thread for the first 24 hours.
- Rollback: visibility flip is reversible at the GitHub UI level, but caches/mirrors, forks created during the public window, and already-pulled tags/clones cannot be retracted. If a leak triggers rollback: flip back to private immediately, file a security advisory per TRANSPARENCY.md §7, treat leaked content as compromised, and never force-publish a corrected history while the repo is public — instead cut a new sanitization-cycle proposal under ADR-218 and re-flip on the next launch window.

## Relations & where used

Chains together `pre-public-readiness-checklist.md`, `TRANSPARENCY.md`, `HISTORY-SANITIZATION-2026-05-08.md`, `release-signing.md`, `supply-chain.md`, `verify-public-release.md`, and ADR-218 (history sanitization toolchain).

## Status / caveats

This is a dated, point-in-time operational snapshot: it references specific hashes, line counts, commit counts ("7 commits pending"), and a first tag name (`v1.0.0`) tied to a particular launch attempt as of 2026-05-08/05-07. Treat the concrete numbers as historical evidence for that launch cycle, not as generally current facts. The unsigned-tag fallback is an explicitly disclosed gap, not an inconsistency.

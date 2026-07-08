---
type: quality-synthesis
source: docs/09-Quality/security/verify-public-release.md
provenance: "Anti-FUD companion to TRANSPARENCY.md that gives a skeptical reader an independently reproducible checklist to verify the SBOM, signed tags, sanitization-manifest history, and license transition after the 2026-05-08 history rewrite."
---

## What it is
A self-service verification recipe ("anti-FUD toolkit") letting any consumer independently confirm five claims about the repository after its 2026-05-08 history rewrite and Apache-2.0 → FSL-1.1-MIT license transition, without trusting the maintainer's word. Long-form companion to `TRANSPARENCY.md` §6.

## Key mechanics
- **§1 SBOM hash verification:** `shasum -a 256 sbom.json` + `jq` check that it's CycloneDX 1.6; notes syft mints fresh serials per run, so cross-SBOM equality is checked via deduped `(purl, version)` tuples, not raw checksum.
- **§2 Signed-tag verification:** pre-`v1.0.0` tags are unsigned by disclosed gap (`git tag -v` → `error: no signature found`, documented not tampering); the first `public-release: true` tag (`v1.0.0`+) must verify cleanly — failure there should be treated as compromise and escalated per `TRANSPARENCY.md` §7.
- **§3 Manifest-snapshot byte-diff:** diffs the live `manifests/history-sanitization.yaml` against the frozen pre-rewrite snapshot (`docs/01-Build-Log/history/manifest-snapshot-2026-05-07.yaml`); the live manifest must be a documented *superset* (added rules: `operator-name`, `historical-fixture-home-paths`, `consumer-codename-a..c`, `consumer-service-name`+variants), not a different ruleset. Every rule must carry a `rationale:` field or the canonical primitive refuses to execute (ADR-218 "Hard rules"). Includes a one-liner Python/yaml audit script to print rule IDs + rationale text.
- **§4 SHA-inventory sanity check:** the pre-rewrite SHA inventory (1,775 commits, `docs/01-Build-Log/history/pre-sanitization-sha-inventory-2026-05-07.txt`, sha256 `923170ea...`) is sampled (20 random SHAs via `shuf`) and each must be *unreachable* from `origin/main` via `git cat-file -e` — non-reachability is the cryptographic proof the rewrite actually happened (every blob/tree/commit re-hashes when content is scrubbed). Current head after rewrite: `db846adb...`.
- **§5 License preservation check:** greps `LICENSE`, `NOTICE`, and the license FAQ for both `Apache` and `FSL-1.1-MIT` strings (expect 40+ matches total), confirms `LICENSE` starts with FSL-1.1-MIT preamble, confirms `NOTICE` retains third-party Apache attributions, and confirms the FAQ documents the transition explicitly.
- **§6** chains all five checks into one copy-pasteable script; a full pass independently confirms SBOM presence/format, tag signature integrity (post-v1.0.0), sanitization-policy superset property, actual occurrence of the rewrite, and license-transition preservation — none of which require trusting the maintainer.

## Relations & where used
- `docs/09-Quality/security/supply-chain.md` §1.2 — source of the SBOM checksum/regeneration claims verified in §1.
- `docs/09-Quality/security/release-signing.md` — source of the signed-tag posture verified in §2.
- `manifests/history-sanitization.yaml`, `docs/01-Build-Log/history/manifest-snapshot-2026-05-07.yaml`, `docs/01-Build-Log/history/pre-sanitization-sha-inventory-2026-05-07.txt` — the artifacts §3/§4 diff and hash-check against.
- `TRANSPARENCY.md` §6 and §7 — parent document and escalation/contact path.
- ADR-218 — governs the "every rule needs a rationale" hard-rule enforcement referenced in §3.
- `docs/09-Quality/legal/license-faq.md` — checked in §5.

## Status / caveats
- Tied to a specific historical event (the 2026-05-08 history rewrite and license transition) — this is a dated, event-specific verification recipe, not an evergreen general-purpose guide; its checks (SHA inventory, manifest snapshot diff) become less relevant as time passes from that rewrite.
- §2's tag-verification example (`git tag -v v1.0.0`) is written as if `v1.0.0` already exists/is signed; per `release-signing.md`, signing is not yet wired as of the source doc's writing — the command is illustrative/aspirational until the first public tag actually lands.

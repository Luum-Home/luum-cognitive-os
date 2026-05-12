# Operational Guide Audit — 2026-05-12T14:59:19Z

> Per ADR-274. Schema: `operational-guide-audit/v1`.
> Audits all `docs/adrs/ADR-*.md` for §Operational Guide section presence
> on maintainer-tier accepted capability ADRs.

## How to read this doc (operational guide for this audit)

This audit answers: **which ADRs are missing operator-readable context?**

Verdict taxonomy:
- `compliant` — has §Operational Guide with ≥3 documented sub-sections
- `partial` — has §Operational Guide but < 3 sub-sections (needs expansion)
- `missing` — subject to contract but no §Operational Guide present (needs backfill)
- `exempt` — explicitly marked `<!-- adr-274-exempt: <reason> -->`
- `not-applicable` — tombstone, superseded, or non-maintainer/non-capability

Priority for backfill (only applies to `missing`/`partial`):
- **P0** — accepted ≤ 30 days ago
- **P1** — maintainer-tier accepted (older)
- **P2** — everything else

Per ADR-274: rules without enforcement are honored ~50% historically;
this audit + `adr-section-validator.sh` extension close the loop.

**Total ADRs scanned**: 285

## By verdict

| Verdict | Count |
|---|---:|
| compliant | 62 |
| exempt | 1 |
| not-applicable | 222 |

## By priority (backfill queue)

_no backfill required — all subject ADRs compliant or exempt_

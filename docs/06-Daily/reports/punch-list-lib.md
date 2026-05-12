# Punch List — lib bucket

> Generated 2026-05-01 from `docs/06-Daily/reports/aspirational-audit-2026-05-01.md`.
> Baseline: total=667, ASPIRATIONAL=69, dormant_aspirational_ratio=0.3538.
> Scope: ASPIRATIONAL and DORMANT lib/*.py components detected in the audit run.
> Note: no lib components were classified ASPIRATIONAL. One DORMANT component identified.

| path | classification | dormant signal | recommended action |
|------|----------------|---------------|-------------------|
| `lib/jupyter_client.py` | DORMANT | callers=0, size_bytes=9418, no test coverage, no @on-demand marker | PROVE or PRUNE: write a unit test that imports and exercises it, or archive to docs/99-Archive/archive/lib/ |

## Action Summary

| action | count |
|--------|-------|
| PROVE (add test to promote to ON_DEMAND) | 1 |
| PRUNE (archive if Jupyter integration is shelved) | 1 alternative |

`lib/jupyter_client.py` is 9 KB of code with zero callers. If the Jupyter integration
(see `hooks/jupyter-sandbox.sh`) is still planned, adding a test promotes it to ON_DEMAND.
If the integration is shelved, archive both together.

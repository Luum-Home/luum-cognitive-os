---
title: "HKUDS/OpenHarness Annex F — Compliance & Clean-Room Protocol"
date: 2026-05-11
annex: F
parent: null  # backfill — predates annex doctrine
scope: research-only
license_classification: "MIT — confirmed against upstream LICENSE file; direct port legally allowed with copyright preservation"
reviewed-by-legal: "no"
---

# Annex F — Compliance & Clean-Room Protocol for HKUDS/OpenHarness

## 1. License posture

**Upstream repository**: `https://github.com/HKUDS/OpenHarness`

**License**: MIT — **confirmed** via WebFetch of
`https://github.com/HKUDS/OpenHarness/blob/main/LICENSE` (2026-05-11).

**Verbatim copyright line** (from upstream LICENSE):
> `Copyright (c) 2025 OpenHarness Contributors`

MIT permits use, modification, and redistribution with copyright and license notice
preservation. No patent grant clause. No copyleft obligation. Compare to Apache-2.0
(more explicit patent grant) and AGPL (REJECT policy). This license is in the ALLOW tier
per `rules/license-policy.md`.

**Commit hash recorded in source**: `7873f0d109174a57b3b1af7aa5397a6b3b0bd551`

**Source path in upstream**: `src/openharness/hooks/schemas.py`

**Prior audit note**: A prior audit incorrectly characterised the license as "never
verified." The inline attribution correctly claimed MIT; this annex confirms that claim
against the upstream LICENSE file. No re-classification is required.

## 2. What this corpus contains

One file ported into COS runtime:

| File | Lines | Note |
|------|-------|------|
| `lib/hook_types.py` | lines 4–6 (docstring) + full file | Ports `HttpHookDefinition` and `PromptHookDefinition`; adds `ShellHookDefinition` as COS extension |

The comment at lines 4–6 reads verbatim:
> `Ports HttpHookDefinition and PromptHookDefinition from HKUDS/OpenHarness`
> `(commit 7873f0d109174a57b3b1af7aa5397a6b3b0bd551, src/openharness/hooks/schemas.py)`
> `under MIT licence, adapted to COS conventions.`

Attribution is complete: upstream repo name, commit hash, source path, and license are
all recorded inline. This satisfies ADR-267 §2.3 inline attribution requirements.

## 3. Per-file disposition

| File | Origin | License | Upstream verified | Disposition |
|------|--------|---------|-------------------|-------------|
| `lib/hook_types.py` | `HKUDS/OpenHarness` @ `7873f0d` `src/openharness/hooks/schemas.py` | MIT — confirmed | YES (2026-05-11) | SAFE TO KEEP — attribution complete, copyright preserved |

## 4. NOTICE preservation requirements

**For the NOTICE-file creator agent** — add the following entry to `NOTICE`:

```
HKUDS/OpenHarness — hook schemas
  Source file: lib/hook_types.py
  Ported from: https://github.com/HKUDS/OpenHarness/blob/7873f0d109174a57b3b1af7aa5397a6b3b0bd551/src/openharness/hooks/schemas.py
  Commit: 7873f0d109174a57b3b1af7aa5397a6b3b0bd551
  License: MIT
  Copyright: Copyright (c) 2025 OpenHarness Contributors
  Modifications: Adapted to COS conventions; added ShellHookDefinition (backward-compat
                 wrapper for existing COS shell-command hooks); HttpHookDefinition and
                 PromptHookDefinition declared but not yet wired into hook dispatcher
                 (gated on ADR-178 §Future Work).
```

MIT does not require a separate NOTICE file (unlike Apache-2.0), but COS policy
(`docs/architecture/supply-chain-defense.md`) mandates NOTICE entries for all vendored
code regardless of license tier.

## 5. Why this is backfill

This file was ported before ADR-259 (supply-chain attribution gate) and ADR-267
(Annex F mandatory before vendoring). The port predates the doctrine that requires
an Annex F record at time of port. The inline attribution was complete but no formal
Annex F dossier existed. This annex retroactively satisfies the documentation gap.
No runtime changes are required.

## 6. Pending tasks for legal review

1. **Confirm NOTICE entry** (P1): Add the NOTICE entry from §4 above to the project
   NOTICE file in the next release cycle.
2. **ADR-178 activation gate** (P2): When `HttpHookDefinition` and `PromptHookDefinition`
   are wired into the COS hook dispatcher (ADR-178 §Future Work), confirm no additional
   OpenHarness code is imported. If additional code is ported, open a new Annex F entry.
3. **Upstream drift monitoring** (P3): If OpenHarness upstream changes license in a
   future release, the pinned commit `7873f0d` remains MIT. Monitor only if the
   dependency is upgraded to a later commit.

## 7. reviewed-by-legal status

```
reviewed-by-legal: no
Reason: Backfill annex — MIT confirmed against upstream LICENSE file.
        Attribution complete in source file (repo, commit hash, source path, license).
        No blocker identified. Recommended for legal sign-off at next routine review cycle.
Confidence: HIGH — upstream URL, commit hash, and LICENSE text all verified 2026-05-11.
```

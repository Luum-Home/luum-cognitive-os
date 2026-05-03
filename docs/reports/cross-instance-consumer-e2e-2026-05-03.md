# Cross-Instance Consumer E2E Drill — 2026-05-03

## Purpose

Verify that a fresh local consumer repository can install the Cognitive OS
default Codex projection and participate in the cross-instance learning runway.

This is a drill report, not external adoption evidence. The generated consumer
evidence is maintainer-owned, same-machine, same-repo, and self-reported; it must
not sign the `helps-projects` product claim.

## Steps executed

1. Created a fresh local Git repository with a small Python file.
2. Installed Cognitive OS from the local source using:

   ```bash
   install.sh --from <cos-source> --harness=codex --force --skip-manifest-check
   ```

3. Verified install metadata:

   - profile: `default`
   - harness: `codex`
   - hooks installed: `37`
   - skills installed: `8`

4. Verified installed hook syntax:

   ```bash
   bash -n .cognitive-os/hooks/cos/*.sh
   ```

5. Exported local consumer evidence with provenance:

   ```bash
   scripts/cos-export-consumer-evidence \
     --project-dir <consumer-repo> \
     --project <consumer-name> \
     --reporter local-codex-run \
     --profile core \
     --duration-days 0 \
     --cos-version 0.23.0 \
     --maintainer-owned \
     --relationship same-maintainer \
     --producer-type agent \
     --producer-identity codex-local \
     --source-repo <consumer-repo> \
     --machine-id <local-machine> \
     --same-machine \
     --same-repo \
     --cognitive-cost "local install smoke; not external evidence"
   ```

6. Imported that evidence into a temporary adoption-evidence manifest.
7. Ran the claim-signature audit against the temporary manifest.
8. Ran cross-instance drills.
9. Verified registry locks and quick local CI.

## Results

| Check | Result |
|---|---|
| Consumer install | pass |
| Codex hook projection JSON | pass |
| Installed hook syntax | pass |
| Consumer evidence export | pass |
| Temp evidence import | pass |
| Claim audit with self-owned evidence | remains unsigned |
| Cross-instance drills | pass |
| Registry lock audit | pass |
| Quick local CI | pass |

Claim audit stayed honest:

```text
warn 0 / 3
self-building: partial false
helps-projects: unsigned false
maturity-loop: timed false
```

The consumer evidence was accepted as structurally valid but did not sign
`helps-projects` because its independence metadata declared it self-reported.

## Drill output

```text
cross-instance-drill: pass
external-evidence: pass
shape-b-trigger: triggered
registry-drift: pass
engram-conflict: pass
shape-b-governance: pass
```

The Shape-B drill intentionally reports `triggered` for temporary inputs. The
real federation trigger audit remains Shape A/deferred until real observed
thresholds fire.

## Findings

- Provenance metadata is required for non-maintainer evidence to sign the
  `helps-projects` claim.
- A local consumer repo can verify the installation and evidence-exchange
  pipeline without creating circular product proof.
- Manual drills can prove machinery behavior while preserving the distinction
  between synthetic state and real claim-signing evidence.

## Follow-up

- Obtain a real non-maintainer 30-day consumer report before signing
  `helps-projects`.
- Keep Shape-B federation deferred until observed triggers fire.
- Consider a future signed provenance format when external CI/agent producers are
  available.

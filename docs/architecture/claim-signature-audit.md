# Claim Signature Audit

Cognitive OS uses strong product language only when a claim has durable,
falsifiable evidence in the repository. `scripts/cos-claim-signature-audit`
tracks the three claims that still need evidence before they can be stated
without an asterisk.

## Claims

| Claim | Honest wording today | Signature condition |
|---|---|---|
| Self-building | Self-instrumenting + operator-directed | At least one primitive records `promotion_evidence.primary_signal: primitive-harvester`, `from_state: sandbox`, `to_state: advisory`, and `approved_by: operator`. |
| Helps projects | Designed to help; self-deployed; external evidence pending | A non-maintainer project runs `core` for 30+ days and reports prevented incidents, false-positive ratio, and cognitive-cost feedback. |
| Maturity loop | Demotion loop exists; ROI knife pending | `cos_demotion_loop_audit` passes with `roi_signed_demotion_count >= 1`. |

## Evidence manifests

- Lifecycle / self-building / maturity loop evidence lives in
  `manifests/primitive-lifecycle.yaml`.
- External adoption evidence lives in
  `manifests/external-adoption-evidence.yaml`.

Self-deployments into projects owned by the original maintainer do not sign the
external-help claim. They are useful dogfood, not bilateral external evidence.

## Commands

```bash
scripts/cos-claim-signature-audit --json
scripts/cos-claim-signature-audit --fail-on-findings
```

The audit is intentionally allowed to warn while claims remain unsigned. It is a
truth surface, not a marketing generator. A signed claim should survive a reader
asking: *what exact artifact would falsify this?*

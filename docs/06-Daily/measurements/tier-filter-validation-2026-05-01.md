# Tier-Filter Validation Report

**Generated**: 2026-05-01T14:55:37.012917+00:00  
**Harness**: scripts/validate_tier_filter.py  
**Approach**: synthetic (30 trials)  
**Recommendation**: KEEP [0,1]

## Statistical Summary

| Metric | Value |
|--------|-------|
| Trials (N) | 30 |
| Mean unexpanded keys — Config A [0,1] | 0.33 |
| Mean unexpanded keys — Config B [0] | 1.47 |
| Mean delta (B-A) | +1.13 keys |
| Trials where B leaves more unexpanded | 18 / 30 |
| Trials neutral (no difference) | 10 / 30 |
| Wilcoxon W | 3 (z=3.808 p=0.0001) |
| Baseline skills_failed/session | 0.445 |
| Observed skills_failed/session (last 7d) | 0.2651 |
| Revert threshold | 0.89 |

## Decision

**KEEP** — Expansion regression in 18/30 trials (60%) — majority of sampled tasks leave Tier-1 rules unexpanded under [0]. Mean delta=1.13 keys. Live rate OK (observed_rate=0.2651 <= threshold=0.89) but context quality risk is unacceptably high for complex tasks.

## Repeatability

```bash
Re-run at any time with: python3 scripts/validate_tier_filter.py --approach=replay --n=30 --output=docs/06-Daily/measurements/tier-filter-validation-$(date +%F).json
```

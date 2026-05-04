---
adr: 150
title: ACC Projection Profiles and Expanded Harness Registry
status: accepted
date: 2026-05-04
supersedes: []
superseded_by: null
implementation_files:
  - manifests/primitive-projection-profiles.yaml
  - manifests/harness-projection.yaml
  - scripts/acc_pipeline.py
  - tests/unit/test_acc_pipeline.py
  - tests/contracts/test_acc_pipeline_contract.py
tier: maintainer
tags: [acc, projection, harness, profile, consumer-accessibility]
---

# ADR-150: ACC Projection Profiles and Expanded Harness Registry

## Status

**Accepted** — 2026-05-04

## Context

ACC had real default-profile projection proof for Claude Code and OpenAI Codex, but the debt view still treated many profile/install scripts as partial and many skills/rules as unverified. That created two problems:

- SO-local profile drivers, such as `scripts/cos_init.py`, looked like scripts that should be copied into consumer projects.
- Full-profile skills/rules were invisible to ACC even though `cos_init.py --full --harness claude|codex` can project them into a temporary consumer project.

The harness registry also needed to keep newer coding-agent surfaces visible without falsely signing support. Qwen Code and Kimi Code have first-party coding-agent surfaces. MiniMax MaxClaw appears closer to hosted-agent or OpenClaw-compatible deployment. DeepSeek currently has official provider/API compatibility for existing agent tools rather than a signed first-party IDE projection contract in this repo.

## Decision

Add `manifests/primitive-projection-profiles.yaml` as the ACC projection-profile contract. It declares:

- `default` and `full` profiles;
- projection classes: `shared`, `default`, `full`, `profile-driver`, and `maintainer-only`;
- profile-driver scripts whose consumer proof is successful projection output, not direct copying into consumer projects.

Update `scripts/acc_pipeline.py` so consumer projection runs both `--default` and `--full` for implemented harnesses and records counts by `harness/profile`, for example `claude/default`, `claude/full`, `codex/default`, and `codex/full`.

Expand `manifests/harness-projection.yaml` with planned entries for:

- `qwen-code`
- `kimi-code`
- `minimax-maxclaw`
- `deepseek-provider`

These planned entries do not inherit Claude/Codex proof. They remain unverified until a driver and temp-project proof exists.

## Consequences

### Positive

- ACC can distinguish projected consumer primitives from SO-local profile drivers.
- Full-profile projected skills/rules are counted with actual temp-project proof.
- Partial and unverified weights drop without manual row-by-row classification.
- New provider/harness candidates are visible without overstating support.

### Negative

- ACC refresh is slower because it runs four projection installs: Claude default/full and Codex default/full.
- Full-profile projection increases `docs/acc/latest.json` size.
- Planned harness entries require ongoing research as external tools evolve.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Keep only default-profile proof | Rejected because full-profile skills/rules stayed unverified despite being projectable. |
| Mark profile/install scripts as consumer-projected files | Rejected because those scripts prove projection as drivers; they are not themselves the projected consumer artifact. |
| Add Qwen/Kimi/MiniMax/DeepSeek as implemented | Rejected because no COS projection driver or temp-project proof exists yet. |
| Treat DeepSeek as an IDE harness | Rejected for now; official documentation supports provider/API compatibility for existing agent tools, not a local IDE projection contract signed here. |

## Verification

```bash
python3 scripts/acc_pipeline.py --project-dir . --refresh
python3 -m pytest tests/unit/test_acc_pipeline.py tests/contracts/test_acc_pipeline_contract.py -q
python3 -m py_compile scripts/acc_pipeline.py
```

## Implementation Evidence

- `manifests/primitive-projection-profiles.yaml` declares projection classes and 19 profile-driver scripts.
- `scripts/acc_pipeline.py` records default/full projection proof by implemented harness/profile.
- `manifests/harness-projection.yaml` includes planned Qwen Code, Kimi Code, MiniMax MaxClaw, and DeepSeek provider entries.
- `tests/contracts/test_acc_pipeline_contract.py` asserts default/full projection counts and expanded harness IDs.

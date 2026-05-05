---
adr: 161
title: Remote Control Plane and Provider Adapter Boundary
status: implemented
date: 2026-05-05
supersedes: []
superseded_by: null
implementation_files:
  - manifests/remote-control-plane-alternatives.yaml
  - docs/reports/remote-control-plane-alternatives-2026-05-05.md
  - docs/architecture/service-control-plane-implementation-plan.md
  - tests/contracts/test_remote_control_plane_alternatives.py
  - docs/manual-tests/remote-control-plane-boundary.md
tier: maintainer
tags: [remote-control-plane, provider-adapters, opencode, openclaw, agent-zero, telegram, credentials]
---

# ADR-161: Remote Control Plane and Provider Adapter Boundary

## Status

**Implemented for boundary/inventory scope** — 2026-05-05. The remote ingress versus provider/executor adapter boundary, alternatives manifest, report, manual test, and contract tests exist; concrete remote ingress/provider adapters remain follow-up implementation work.

## Context

Cognitive OS is gaining projection coverage across IDEs, CLIs, rules, skills,
hooks, and scripts. That work answers how consumer projects receive local
agentic primitives. It does not answer how the SO should operate when the
operator is not inside the current IDE, or how it should connect to provider
models, account-backed CLIs, API keys, local model runtimes, and chat surfaces.

A 2026-05-05 review of OpenClaw, Agent Zero, OpenCode, NanoClaw, PicoClaw,
ZeroClaw, Nanobot, TinyAGI/TinyClaw, NullClaw, IronClaw, Pinchy, and ZeptoClaw
shows a recurring architecture:

- a remote/chat/web ingress layer;
- a gateway/control-plane layer;
- provider or executor adapters;
- workspace/tool execution;
- logs, memory, and operator feedback.

COS already has service-control-plane research and provider-executor planning,
but it needed a sharper boundary for remote ingress and credential ownership.

## Decision

COS will separate **remote ingress** from **provider/executor adapters**.

Remote ingress adapters may receive operator intent from Telegram, REST,
Paperclip, webhooks, GitHub, or other chat/UI surfaces. They only authenticate,
allowlist, normalize, rate-limit, and enqueue work. They do not own model
credentials and do not execute project tools directly.

Provider/executor adapters may invoke documented model/provider paths such as:

- official account-backed CLIs as black boxes;
- API-key/OAuth/device-login/provider-cloud flows;
- OpenAI-compatible gateways such as OpenRouter/LiteLLM/local servers;
- local model runtimes such as Ollama, LM Studio, llama.cpp, or vLLM;
- an OpenCode headless server when explicitly started and protected.

No credential scraping is allowed. COS must not read vendor token stores,
keychains, cookies, `~/.claude`, `~/.codex/auth.json`, or equivalent hidden auth
files. Every provider/executor adapter needs an `auth_probe` returning one of
`ready`, `auth_required`, `unsupported`, or `unsafe`.

The inventory lives in `manifests/remote-control-plane-alternatives.yaml`; the
human-readable research report lives in
`docs/reports/remote-control-plane-alternatives-2026-05-05.md`.

## Consequences

### Positive

- COS can be controlled remotely without making every chat surface a privileged
  executor.
- Provider/account support becomes adapter-scoped and testable.
- Paperclip can remain an operator console/status plane instead of becoming a
  credential broker.
- OpenCode can be evaluated as an executor adapter without becoming a hard COS
  dependency.
- Telegram can start as a lab ingress adapter with strict pairing/allowlist and
  replay tests.

### Negative

- More interfaces must be tested before remote autonomy is safe.
- A chat adapter that only enqueues work may feel less magical than OpenClaw at
  first.
- Account-backed CLIs are economical for maintainers but not automatically safe
  for Docker, CI, or hosted multi-tenant deployments.
- Some comparable projects have blocked or review-required licenses, so code
  reuse remains constrained even if concepts are useful.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Clone OpenClaw's full Gateway/channel model | Too broad for COS's governance-first scope and would blur proof boundaries. |
| Put provider API keys in Paperclip | Paperclip is documented as UI/status integration, not the credential owner. |
| Let Telegram directly run scripts/hooks | Chat input is untrusted ingress; all work must pass queue, lease, allowlist, and redaction gates. |
| Read existing CLI token files for convenience | Violates the no credential scraping boundary and breaks portability/security. |
| Make OpenCode mandatory | OpenCode is a strong executor candidate, but COS must stay provider/harness agnostic. |
| Treat IDE projection as remote runtime support | Structural files do not prove account-backed model execution or remote operation. |

## Verification

```bash
python3 -m pytest tests/contracts/test_remote_control_plane_alternatives.py -q
python3 -m pytest tests/audit/test_adr_contracts.py tests/audit/test_adr_locations.py -q
```

## Implementation Evidence

- `manifests/remote-control-plane-alternatives.yaml` records the verified
  alternatives and their proof/license/ingress/provider posture.
- `docs/reports/remote-control-plane-alternatives-2026-05-05.md` records the
  architecture synthesis, phased plan, and manual checklist.
- `docs/architecture/service-control-plane-implementation-plan.md` links the new
  remote ingress/provider boundary and keeps execution behind `cosd`.
- `tests/contracts/test_remote_control_plane_alternatives.py` verifies required
  manifest fields and core project coverage.

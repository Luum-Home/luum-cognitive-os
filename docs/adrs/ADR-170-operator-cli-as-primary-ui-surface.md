---
adr: 170
title: Operator-CLI as Primary UI Surface — No Web Dashboard Until a Real Driver Exists
status: accepted
date: 2026-05-05
supersedes: []
superseded_by: null
implementation_files:
  - scripts/cos-boring-reliability
  - scripts/cos-doctrine-proposer
  - scripts/cos-self-improvement-loop
  - scripts/cos-pr-review.sh
  - scripts/cos-cloud-worker-bootstrap.sh
  - scripts/cos-adoption-profile
  - scripts/cos-runtime-hook-reality
  - scripts/cos-silent-failure-audit
  - docs/architecture/boring-reliability-control-plane.md
  - docs/architecture/cognitive-prosthesis.md
tier: maintainer
tags: [ui, cli, governance, paperclip, demotion, embedded-runtime]
---

# ADR-170: Operator-CLI as Primary UI Surface — No Web Dashboard Until a Real Driver Exists

## Status

Accepted.

## Context

Two prior decisions framed the UI question:

- [ADR-169](ADR-169-dashboard-formal-demotion.md) (2026-05-05) demoted the abandoned in-tree `dashboard/` in favour of *"Paperclip is the UI, Cognitive OS is the engine"*.
- [ADR-043](ADR-043-paperclip-local-daemon.md) (2026-04-30) extracted Paperclip from the mandatory Docker stack to a local-daemon path with Docker fallback.

A live verification on 2026-05-05 — performed immediately after ADR-169 wired six Paperclip hooks into `.claude/settings.json` — surfaced a finding that the audit had not caught:

> **The Paperclip API endpoints the COS-side client expects do not exist in the current Paperclip release.**

Concretely, when the six hooks fire against a running `cognitive-os-paperclip` (image `reeoss/paperclipai-paperclip:latest@sha256:677649a2...`):

- `POST /api/notifications` → 404
- `POST /api/agents/status` → 404
- `POST /api/artifacts` → 404
- `GET /api/openapi.json` → 404
- All `/api/v1/*` endpoints → 404

Only `GET /api/health` responds.

Paperclip itself is real: `paperclipai/paperclip` v0.2.7 (MIT). It uses **tRPC** (`/trpc/*` routes), not REST. The COS-side `packages/ecosystem-tools/lib/paperclip_client.py` was written against a REST contract that **never existed in Paperclip**. The 50 unit and behaviour tests pass because they stub the HTTP layer; against the real daemon, every POST fails 404.

This is not API drift between Paperclip versions. It is a contract that **was invented client-side without verifying against the upstream**. The integration's REAL/PARTIAL/MISSING audit on 2026-05-05 read the COS side correctly (hooks exist, tests pass) but did not stress-test against a live daemon, so it missed the deeper miss: the integration was always speculative.

The honest implication for the UI question: **there is no working web UI for COS today**, and there has not been one in this repository's history. The dashboard was never functional; the Paperclip integration was never end-to-end. Pretending either was the UI was maintainer cache.

## Decision

The primary UI surface for Cognitive OS is the **operator CLI plus the markdown report library**, period.

Concretely:

- `scripts/cos-boring-reliability` is the operator dashboard. Output is structured JSON or human-readable text. No web rendering.
- `scripts/cos-doctrine-proposer`, `scripts/cos-self-improvement-loop`, `scripts/cos-adoption-profile`, `scripts/cos-runtime-hook-reality`, `scripts/cos-silent-failure-audit`, `scripts/cos-tier-claim-audit`, `scripts/cos-cross-instance-drill`, `scripts/cos-recovery-drill` are operator tools.
- `scripts/cos-pr-review.sh` covers manual code-review workflows.
- `scripts/cos-cloud-worker-bootstrap.sh` covers cross-OS deployment (ADR-140 surface).
- The `docs/reports/` directory is the durable artefact surface: audit reports, baseline snapshots, case studies. Markdown, git-tracked, dated.

No web dashboard, no Paperclip-as-UI, no Phoenix-as-UI is required for the system to be operationally observable, governance-checked, or enterprise-evaluable.

### Complementary surface — Phoenix as opt-in LLM-trace UI

Because `arize-phoenix>=4.0` is already declared in `pyproject.toml` under the `observability` extra, **a graphical surface for LLM traces is one command away** without contradicting the CLI-first decision:

```bash
uv sync --extra observability     # one-time
uv run phoenix serve              # → http://localhost:6006
```

Phoenix renders OpenTelemetry traces, span attributes, latency, cost, and eval scores. It does **not** render lifecycle states, doctrine proposals, demotions, audit_class, federation triggers, or any other COS governance concept. That separation is the point: Phoenix is the **trace** surface; the CLI plus markdown reports remain the **governance** surface. They co-exist, neither one stands in for the other.

This pattern also keeps the future option open: if a buyer needs a trace UI for LLM cost / latency analysis, the answer is *"`uv run phoenix serve`"* with a 30-second activation. If a buyer needs a governance UI, the answer remains the CLI and markdown reports — and any future graphical governance UI requires a separate ADR per the alternatives below.

This decision **does not** delete or unwire the Paperclip integration. The 6 hooks remain wired and continue to push (and continue to receive 404s) until either:

- A future ADR repairs `paperclip_client.py` against Paperclip's real tRPC API, **or**
- The integration is formally removed in a follow-up ADR after a 90-day no-fix window.

This decision **does not** prevent a future UI. It declares the **default** is CLI-first. Any future web UI must arrive as a separate ADR with a real driver, real schema, and real evidence — not as another aspirational integration.

## Acceptance Criteria

1. ADR-170 is accepted and cross-references ADR-169 and ADR-043.
2. ADR-169 is updated with an addendum naming the API-invention finding and explicitly stating that ADR-170 supersedes the *"Paperclip is the UI"* clause for the active default.
3. CHANGELOG `[Unreleased]` documents the decision and links to both ADRs and the live-smoke report.
4. No new web-dashboard code lands until a future ADR explicitly revokes ADR-170.
5. The `dashboard/ARCHIVED.md` notice from ADR-169 remains; the demotion holds.

## Border Cases

- **External buyer asks for a UI demo.** The answer is: `bash scripts/cos-boring-reliability --profile core --json | jq .`, plus the markdown reports under `docs/reports/`. If the buyer's evaluation requires a web rendering, that is a Shape B trigger per ADR-132 — not an emergency build of a custom UI under Shape A.
- **Phoenix is already in `pyproject.toml`.** Phoenix has a web UI for LLM observability (`uv run phoenix serve` on port 6006). It is OpenTelemetry-aligned and trace-shaped. It does not model COS lifecycle / doctrine / demotion. It can co-exist as an LLM-trace UI without being the COS governance UI. ADR-058 already governs Phoenix's role as the trace surface; ADR-170 does not change that.
- **Paperclip integration eventually gets repaired.** When the client is rewritten against tRPC and the live daemon receives valid POSTs, the system has a Paperclip-as-UI again. ADR-170 does not block that path; it only stops pretending the path is currently working.
- **Someone clones the repo and looks for a UI.** The README, `docs/getting-started.md`, and `docs/INDEX.md` all point at the CLI surfaces and the runbook for the Docker worker. The `dashboard/ARCHIVED.md` notice closes off the abandoned route. Discoverability is now operator-CLI-shaped, matching the decision.

## Consequences

**Positive.**

- The product claim aligns with reality. *"Operator-CLI with markdown reports + Docker worker"* is verifiable; *"Paperclip is the UI"* was not.
- Zero new web surface to maintain. Aligns with the *"Subtraction + maturity-driven"* clause in `cognitive-prosthesis.md`.
- Future buyers are evaluated against operator usability, not against a half-functional dashboard.
- The doctrine compounds: every audit, every demotion, every proposal flows through `docs/reports/` as durable evidence. The CLI is the interaction model; markdown is the durability layer.

**Negative / trade-offs.**

- **No graphical demo.** A pitch that depends on a screen-share of moving parts has to use terminal output. Reduces visual appeal in some sales contexts. Mitigated by the strength of the markdown artefacts (case study, audits, ADRs).
- **Higher onboarding bar for non-CLI users.** A buyer expecting Notion/Linear/Jira-style UI gets terminal output. The runbook ([`docs/runbooks/run-cos-in-docker.md`](../runbooks/run-cos-in-docker.md)) is the first softener; the CLI surface itself is the second.
- **The Paperclip wiring (ADR-169) becomes "ready when Paperclip is ready"**, not "ready now". Hooks remain wired and the 404s remain in the daemon log when the legacy stack is up. That is honest noise, not silent failure.

## Alternatives Rejected

- **Path A: repair the Paperclip client against tRPC** (~4-12h). Rejected as the **default** path because the integration has never delivered value and there is no evidence the maintainer or any consumer needs it before other work. May be done later under a separate ADR if a real consumer requires it.
- **Path B: pivot to Phoenix for the governance UI.** Rejected because Phoenix is trace-shaped and does not model lifecycle, doctrine, demotion, audit_class, or federation triggers. Phoenix continues to be the LLM-trace UI per ADR-058; it does not become the governance UI.
- **Path D: build a custom Cognitive OS web UI.** Rejected because (a) `dashboard/` was already demoted in ADR-169, (b) the doctrine of net-new-surface-without-demotion would block this anyway, (c) the OSS landscape (Phoenix, Langfuse, Helicone, AgentOps) does not have a model for what COS models, so building a fitting UI would be a multi-sprint product effort that requires Shape B per ADR-132.

## Falsifiable Claim

The CLI-as-primary-UI decision holds while **all** of the following remain true. If any breaks for the indicated duration, ADR-170 must be revisited:

1. **CLI usability.** A new operator running `bash scripts/cos-boring-reliability --profile core` for the first time understands the system's state within 5 minutes of reading the output. Tested by re-onboarding evidence whenever someone external is exposed to the system. (Onboarding-failure signal.)
2. **Markdown reports as evidence surface.** `docs/reports/` continues to receive new dated artefacts at a cadence of at least one per major decision cycle. Reports remain readable without web rendering. If reports go silent for 60 days during normal maintenance, the decision is broken. (Evidence-graveyard signal.)
3. **No external buyer requires a graphical UI for evaluation.** If three independent external evaluators cite "no UI" as a blocker within 6 months, this is a Shape B trigger and the decision is revisited. (Buyer-demand signal.)

If conditions 1-3 hold for one calendar year, the decision is judged correct and the system stabilises around CLI-first.

## Cross-references

- [ADR-043](ADR-043-paperclip-local-daemon.md) — Paperclip local daemon path; remains accurate.
- [ADR-058](ADR-058-observability-migration-langfuse-to-phoenix.md) — Phoenix as LLM trace surface; unchanged by this ADR.
- [ADR-132](ADR-132-solo-swarm-vs-multi-maintainer-fork.md) — Shape A/B fork criteria; "buyer requires UI" is a Shape B trigger.
- [ADR-169](ADR-169-dashboard-formal-demotion.md) — dashboard formal demotion; this ADR addends the "Paperclip is the UI" clause.
- [`docs/reports/paperclip-integration-audit-2026-05-05.md`](../reports/paperclip-integration-audit-2026-05-05.md) — original audit (correct at the COS side, missed live-daemon API contract).
- [`docs/reports/paperclip-live-smoke-2026-05-05.md`](../reports/paperclip-live-smoke-2026-05-05.md) — live smoke report; the smoke test was insufficiently rigorous (`is_available()` returned True via `/api/health` even though all POST endpoints 404).
- [`docs/architecture/boring-reliability-control-plane.md`](../architecture/boring-reliability-control-plane.md) — the operating doctrine the CLI surface enacts.
- [`docs/architecture/cognitive-prosthesis.md`](../architecture/cognitive-prosthesis.md) — the rationale layer; the CLI-first decision is consistent with *"Subtraction + maturity-driven"*.

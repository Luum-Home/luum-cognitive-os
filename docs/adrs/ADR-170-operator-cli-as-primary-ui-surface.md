---
adr: 170
title: Operator-CLI as Primary UI Surface — No Web Dashboard Until a Real Driver Exists
status: superseded
date: 2026-05-05
supersedes: []
superseded_by: ADR-172
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
---
# ADR-170: Operator-CLI as Primary UI Surface — No Web Dashboard Until a Real Driver Exists

## Status

Superseded by [ADR-172](ADR-172-multi-surface-ui-architecture.md) (2026-05-05).

ADR-170 declared the operator CLI as *the* primary UI surface. ADR-172 generalises this into the multi-surface architecture (CLI is now Surface 1 of four alongside Phoenix LLM-trace UI, Engram Cloud, and Obsidian). The CLI-as-primary clause survives unchanged inside ADR-172 — this supersession is an extension, not a reversal.

## Context

Two prior decisions framed the UI question:





- `POST /api/notifications` → 404
- `POST /api/agents/status` → 404
- `POST /api/artifacts` → 404
- `GET /api/openapi.json` → 404
- All `/api/v1/*` endpoints → 404

Only `GET /api/health` responds.




## Decision

The primary UI surface for Cognitive OS is the **operator CLI plus the markdown report library**, period.

Concretely:

- `scripts/cos-boring-reliability` is the operator dashboard. Output is structured JSON or human-readable text. No web rendering.
- `scripts/cos-doctrine-proposer`, `scripts/cos-self-improvement-loop`, `scripts/cos-adoption-profile`, `scripts/cos-runtime-hook-reality`, `scripts/cos-silent-failure-audit`, `scripts/cos-tier-claim-audit`, `scripts/cos-cross-instance-drill`, `scripts/cos-recovery-drill` are operator tools.
- `scripts/cos-pr-review.sh` covers manual code-review workflows.
- `scripts/cos-cloud-worker-bootstrap.sh` covers cross-OS deployment (ADR-140 surface).
- The `docs/reports/` directory is the durable artefact surface: audit reports, baseline snapshots, case studies. Markdown, git-tracked, dated.


### Complementary surface — Phoenix as opt-in LLM-trace UI

Because Phoenix lives in the explicit `requirements/dependency-lanes/observability.txt` heavy lane, **a graphical surface for LLM traces is one operator install away** without contradicting the CLI-first decision:

```bash
bash scripts/dependency-lane.sh install observability  # one-time
uv run phoenix serve                              # → http://localhost:6006
```

Phoenix renders OpenTelemetry traces, span attributes, latency, cost, and eval scores. It does **not** render lifecycle states, doctrine proposals, demotions, audit_class, federation triggers, or any other COS governance concept. That separation is the point: Phoenix is the **trace** surface; the CLI plus markdown reports remain the **governance** surface. They co-exist, neither one stands in for the other.

This pattern also keeps the future option open: if a buyer needs a trace UI for LLM cost / latency analysis, the answer is *"`uv run phoenix serve`"* with a 30-second activation. If a buyer needs a governance UI, the answer remains the CLI and markdown reports — and any future graphical governance UI requires a separate ADR per the alternatives below.


- The integration is formally removed in a follow-up ADR after a 90-day no-fix window.

This decision **does not** prevent a future UI. It declares the **default** is CLI-first. Any future web UI must arrive as a separate ADR with a real driver, real schema, and real evidence — not as another aspirational integration.

## Acceptance Criteria

1. ADR-170 is accepted and cross-references ADR-169 and ADR-043.
3. CHANGELOG `[Unreleased]` documents the decision and links to both ADRs and the live-smoke report.
4. No new web-dashboard code lands until a future ADR explicitly revokes ADR-170.
5. The `dashboard/ARCHIVED.md` notice from ADR-169 remains; the demotion holds.

## Border Cases

- **External buyer asks for a UI demo.** The answer is: `bash scripts/cos-boring-reliability --profile core --json | jq .`, plus the markdown reports under `docs/reports/`. If the buyer's evaluation requires a web rendering, that is a Shape B trigger per ADR-132 — not an emergency build of a custom UI under Shape A.
- **Phoenix is in the explicit observability dependency lane, not the core lock.** Phoenix has a web UI for LLM observability (`uv run phoenix serve` on port 6006). It is OpenTelemetry-aligned and trace-shaped. It does not model COS lifecycle / doctrine / demotion. It can co-exist as an LLM-trace UI without being the COS governance UI. ADR-058 already governs Phoenix's role as the trace surface; ADR-170 does not change that.
- **Someone clones the repo and looks for a UI.** The README, `docs/getting-started.md`, and `docs/INDEX.md` all point at the CLI surfaces and the runbook for the Docker worker. The `dashboard/ARCHIVED.md` notice closes off the abandoned route. Discoverability is now operator-CLI-shaped, matching the decision.

## Consequences

**Positive.**

- Zero new web surface to maintain. Aligns with the *"Subtraction + maturity-driven"* clause in `cognitive-prosthesis.md`.
- Future buyers are evaluated against operator usability, not against a half-functional dashboard.
- The doctrine compounds: every audit, every demotion, every proposal flows through `docs/reports/` as durable evidence. The CLI is the interaction model; markdown is the durability layer.

**Negative / trade-offs.**

- **No graphical demo.** A pitch that depends on a screen-share of moving parts has to use terminal output. Reduces visual appeal in some sales contexts. Mitigated by the strength of the markdown artefacts (case study, audits, ADRs).
- **Higher onboarding bar for non-CLI users.** A buyer expecting Notion/Linear/Jira-style UI gets terminal output. The runbook ([`docs/runbooks/run-cos-in-docker.md`](../runbooks/run-cos-in-docker.md)) is the first softener; the CLI surface itself is the second.

## Alternatives rejected

- **Path B: pivot to Phoenix for the governance UI.** Rejected because Phoenix is trace-shaped and does not model lifecycle, doctrine, demotion, audit_class, or federation triggers. Phoenix continues to be the LLM-trace UI per ADR-058; it does not become the governance UI.
- **Path D: build a custom Cognitive OS web UI.** Rejected because (a) `dashboard/` was already demoted in ADR-169, (b) the doctrine of net-new-surface-without-demotion would block this anyway, (c) the OSS landscape (Phoenix, Langfuse, Helicone, AgentOps) does not have a model for what COS models, so building a fitting UI would be a multi-sprint product effort that requires Shape B per ADR-132.

## Falsifiable Claim

The CLI-as-primary-UI decision holds while **all** of the following remain true. If any breaks for the indicated duration, ADR-170 must be revisited:

1. **CLI usability.** A new operator running `bash scripts/cos-boring-reliability --profile core` for the first time understands the system's state within 5 minutes of reading the output. Tested by re-onboarding evidence whenever someone external is exposed to the system. (Onboarding-failure signal.)
2. **Markdown reports as evidence surface.** `docs/reports/` continues to receive new dated artefacts at a cadence of at least one per major decision cycle. Reports remain readable without web rendering. If reports go silent for 60 days during normal maintenance, the decision is broken. (Evidence-graveyard signal.)
3. **No external buyer requires a graphical UI for evaluation.** If three independent external evaluators cite "no UI" as a blocker within 6 months, this is a Shape B trigger and the decision is revisited. (Buyer-demand signal.)

If conditions 1-3 hold for one calendar year, the decision is judged correct and the system stabilises around CLI-first.

## Cross-references

- [ADR-058](ADR-058-observability-migration-langfuse-to-phoenix.md) — Phoenix as LLM trace surface; unchanged by this ADR.
- [ADR-132](ADR-132-solo-swarm-vs-multi-maintainer-fork.md) — Shape A/B fork criteria; "buyer requires UI" is a Shape B trigger.
- [`docs/architecture/boring-reliability-control-plane.md`](../architecture/boring-reliability-control-plane.md) — the operating doctrine the CLI surface enacts.
- [`docs/architecture/cognitive-prosthesis.md`](../architecture/cognitive-prosthesis.md) — the rationale layer; the CLI-first decision is consistent with *"Subtraction + maturity-driven"*.

---

## Supersession Addendum (2026-05-05)

ADR-170 was published the same day as ADR-172. The CLI-as-primary clause that
ADR-170 established survives unchanged — it is now Surface 1 of the
four-surface architecture documented in [ADR-172](ADR-172-multi-surface-ui-architecture.md).

What ADR-172 changed:

- **Generalised the framing.** ADR-170 implied "the CLI is the UI". ADR-172
  reframes this: each artefact kind has its own ideal surface, and the CLI
  is the right surface only for live operator state — not for traces, not
  for cross-session memory, not for long-form decisions.
- **Made Phoenix and Engram Cloud first-class surfaces.** ADR-170 mentioned
  Phoenix as a "complementary surface"; ADR-172 elevates it to Surface 2 with
  a defined contract. Engram Cloud (Surface 3) is new in ADR-172.
- **Named Obsidian / markdown reader as Surface 4.** ADR-170 implicitly relied
  on "markdown reports under docs/reports/" but did not name the reader
  surface. ADR-172 makes it explicit and contracted.

What ADR-172 did NOT change from ADR-170:

- The CLI is still the always-on, mandatory surface.
- No web dashboard for governance / lifecycle / doctrine — that boundary holds.
- Future custom UI surfaces still require a separate ADR with a real driver

The acceptance criteria of ADR-170 (CLI usability, markdown report cadence,
no buyer-required graphical UI) carry forward into the falsifiable claim of
ADR-172. The two ADRs do not contradict; ADR-172 is the more general
restatement.

## Verification

```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```


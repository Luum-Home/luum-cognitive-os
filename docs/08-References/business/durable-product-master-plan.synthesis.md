---
type: reference-synthesis
source: docs/08-References/business/durable-product-master-plan.md
provenance: "Names Cognitive OS's biggest strategic risk as focus drift — too many competing centers of gravity (package manager, dispatch engine, dashboard, auto-repair, squads) — and defines the wedge, corrections, and phased plan to become a durable product instead of an ever-expanding system of interesting subsystems."
---

## What it is

The top-level strategic positioning document for Cognitive OS: it names the risk (focus drift across 8 simultaneous "centers of gravity"), defines a narrow defensible wedge, situates COS against competitors like Agent Zero/OpenClaw/Hermes, and lays out five product corrections, three strategic bets, and a phased implementation plan (through Phase 5, landed).

## Key mechanics

- **The wedge**: "Cognitive OS makes coding agents more governable, verifiable, and portable across providers in real repositories." Explicitly not: agent-society infrastructure, a general multi-agent platform, an all-in-one AI dev cloud, a dashboard-first product, or a research playground.
- **Competitive framing**: rather than out-broadening Agent Zero/OpenClaw/Hermes (which win on onboarding, autonomy perception, and orchestration visibility), COS should win on governance, verification, execution discipline, portability, and measurable reliability — "harder to fake, easier to test, more durable under ecosystem change."
- **Five product corrections**: (1) reduce visible centers of gravity (product-facing core vs. extension-facing secondary systems), (2) align CI with actual repo complexity (flags that `.github/workflows/ci.yml` runs shell-loop tests while the repo has hundreds of Python tests — a credibility gap), (3) remove documentation drift (flags `README.md` referencing a non-existent `docs/benchmark-results.md`, and `CONTRIBUTING.md` referencing a wrong script path), (4) make performance debt visible (flags `hooks/self-install.sh` exceeding its own `<2s` behavior-test budget, hitting a 5s timeout), (5) separate defensible core from template/scaffold surface (kernel / core runtime / compatibility layer / extension packages / scaffolding / experiments).
- **Three strategic bets**: reliability-over-breadth, capability-centric portability (provider switches should change adapters, not product identity), product clarity as architecture discipline (subsystems not strengthening the wedge become optional/deprioritized).
- **What to cut back vs. keep-as-extension vs. make-central** — three explicit lists (e.g., de-emphasize dashboard-first messaging and squad-heavy messaging; keep experimental ADR roadmaps as framed extensions; make kernel contract and provider portability central).
- **Five implementation phases**, four of which are stated as goals/deliverables (boundary cleanup, validation realignment, reliability hardening, product compression) and **Phase 5 marked "(landed 2026-05-06/07)"**: closing the orchestration coverage gap against May-2026 frontier tools (Claude Code 2.x, Cursor 3, Codex App, Devin 2, etc.) via 14 ADRs (220-236), a versioned evaluation manifest, and a substrate-consumer guardrail validator (14/14 PASS on 2026-05-07). Explicitly cross-references Case Study 2 in `case-study.md`.
- **Phase 6 "(next)"**: hardening pendings — multi-platform perf baselines, chaos-tier coverage, cross-harness end-to-end tests, adoption-truth re-run, service-mode readiness re-audit. States "This phase does not add new ADRs; it closes the explicit pendings the Phase-5 checklist tracks."

## Relations & where used

This is the parent strategic document for nearly every other doc in this batch: `cos-vs-vanilla-dx-review.md` and `conversation-reality-audit-2026-04-30.md` operationalize correction #1 (reduce centers of gravity); `cos-vs-ai-slop-falsification.md` and `cognitive-os-efficiency-operating-model.md` operationalize the "evidence, not claims" discipline underlying Bet 1; `case-study.md`'s Case Study 2 is cited directly as Phase 5's closure evidence.

## Status / caveats

**FLAGGED staleness**: Phase 5 is marked "landed 2026-05-06/07" and Phase 6 is marked "(next)" as the still-open phase, but the current date is 2026-07-08 — roughly two months after Phase 5 landed. Given Phase 6's own hardening items (T6-T10, per Case Study 2's own posture note), this document's "Phase 6 (next)" framing is very likely stale; the actual current phase status should be reverified rather than assumed from this text. The three named documentation-drift/performance-debt issues (missing `docs/benchmark-results.md`, wrong `CONTRIBUTING.md` script path, `hooks/self-install.sh` timeout) are point-in-time findings that may since have been fixed — this synthesis does not verify their current state.

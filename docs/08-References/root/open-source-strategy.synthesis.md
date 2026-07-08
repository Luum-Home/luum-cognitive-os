---
type: reference-synthesis
source: docs/08-References/root/open-source-strategy.md
provenance: "Historical (superseded) ADR-style strategy memo recommending Apache-2.0 open-sourcing of Cognitive OS, retained for its community/monetization analysis."
---

## What it is

A historical, explicitly superseded strategy memo (`ADR-OSS-001`, status "Proposed") analyzing whether to open-source Cognitive OS, under what license, and with what monetization model. The document's own banner states the Apache-2.0 recommendation is **not** the current license; the current posture is FSL-1.1-MIT.

## Key mechanics

- **Current public-license posture (per the doc's own superseding banner)**: FSL-1.1-MIT with automatic conversion to MIT at a future Change Date. Generally allowed pre-Change-Date: self-hosting, internal company use, production use where COS isn't the primary product, consulting, and building products where COS isn't the primary product. Generally *not* allowed without a commercial arrangement: hosted COS, managed agent runtime, agent orchestration SaaS, control-plane SaaS for third-party agents, white-label resale.
- **Historical analysis (superseded content)**: compares MIT/Apache-2.0/AGPL-3.0/BSL-1.1/Dual/ELv2 across adoption friction, IP protection, SaaS protection, community trust, and enterprise acceptance. Recommends **Apache-2.0** for patent protection, adoption parity with Agent Zero/OpenClaw (both MIT), and consistency with COS's own license-policy rule (which blocks AGPL).
- **What to open source (historical)**: everything — rules, hooks, skills, templates, CLI, packages, docs, tests, libraries, infra configs, config schema. Premium/enterprise candidates: managed SaaS hosting, enterprise SSO/RBAC, priority support, analytics dashboard, compliance reporting, the Singularity MAPE-K daemon.
- **Monetization models compared**: (A) fully open + services, (B) open core + premium packages, (C) managed hosting, (D) dual license. Recommendation: **Model B now, Model C later** — Phase 1 (months 0-6) fully open Apache-2.0 with no premium tier; Phase 2 (6-12mo) premium enterprise packages as net-new code; Phase 3 (12-24mo) managed hosting if demand for centralized orchestration materializes.
- **8-week rollout roadmap**: Phase 1 cleanup (secret/content/dependency/Docker-image audits, git history scrub), Phase 2 license/legal (LICENSE, NOTICE, CLA decision, trademark policy), Phase 3 public repo (branch protection, SECURITY.md), Phase 4 community infrastructure (CONTRIBUTING.md, issue/PR templates, CI, docs site), Phase 5 launch (blog post, HN/Product Hunt/Reddit/Discord).
- **Risk mitigation table** and **success metrics** (GitHub stars, contributors, community skills, downloads, Discord members at 3/6/12-month targets) — all framed as projections for the (superseded) open-source plan.

## Relations & where used

- Referenced from `LICENSE`, `README.md`, and `docs/09-Quality/legal/license-faq.md` as the authoritative current source for licensing — this document is explicitly the *prior* analysis those supersede.
- Adjacent to `docs/08-References/root/competitive-analysis.md`, which still lists COS license as "Proprietary" in its metrics table — a separate cross-document inconsistency not resolved here (see that document's Status/caveats).

## Status / caveats

- **Explicitly superseded** (banner dated 2026-05-18): the entire body of the document — the Apache-2.0 recommendation, the open-core monetization plan, and the 8-week rollout — describes a plan that was **not** adopted. The actual license is FSL-1.1-MIT. This synthesis preserves the historical reasoning (per instructions, faithful synthesis of source content) but the recommendation itself must not be treated as current guidance.
- FLAGGED: readers relying on search/grep of this KB for "current license strategy" could mistake the detailed Apache-2.0 analysis for live guidance if they miss the superseded banner — the source document mitigates this with a prominent top-of-file warning and a `<details>` collapse wrapper, which this synthesis also preserves contextually.
- No other internal inconsistencies found within the historical content itself.

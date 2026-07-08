---
type: methodology-synthesis
source: docs/05-Methodology/root/rules.md
provenance: "Describes the current always-active rule set and 8 representative contextual rules that constrain agent behavior for the entire session."
---

## What it is

An overview of Rules — markdown files loaded at session start and enforced throughout the session — covering the current core always-loaded set and detailed summaries of 8 representative contextual rules (constitutional gates, control manifest, license policy, skill adaptation, skill auto-loader, skill registry protocol, auto-repair, metrics calibration).

## Key mechanics

- **Loading architecture**: `self-install.sh` symlinks exactly **16 core rules** into `.claude/rules/cos/` at every session start, reducing always-loaded tokens from ~93K (all 150+ rules) to ~21K. Everything else loads contextually on trigger.
- **The 16 core rules**: RULES-COMPACT, adaptive-bypass, acceptance-criteria, agent-quality, trust-score, token-economy, phase-aware-agents, closed-loop-prompts, error-learning, rate-limiting, credential-management, content-policy, result-management, blast-radius, clarification-gate, model-routing.
- **8 detailed rule summaries**: (1) Constitutional Gates — 7 non-negotiable architecture principles (mobile-via-BFF-only, mock-before-integrate, test-before-merge, secrets-never-in-code, backward-compatible APIs, idempotent financial ops, audit trail); (2) Control Manifest — required libraries, prohibited zones (migrations, deployed artifacts, auth realm config, header/bundle/package names), performance constraints (BFF <200ms p95, Docker <200MB, mobile <3s cold start), security constraints, and a 5-tier complexity-to-workflow scale-adaptive table (trivial/small/medium/large/critical); (3) License Policy — Allowed/Caution/Blocked license tiers with an AGPL/SSPL "separate-container-only" exception; (4) Skill Adaptation — pre-run Engram lookup, post-failure save, post-recovery update, 3-failure auto-rewrite trigger via `/skill-creator`, and a 4-layer diagram (Registry -> Engram -> Hooks -> skill-creator); (5) Skill Auto-Loader — maps `.claude/detected-stack.json` to expected skills, suggests (not auto-generates) creation on gaps; (6) Skill Registry Protocol — project > global > auto-generated priority order, YAML frontmatter versioning, refresh rules (auto-generated regenerable, manual never auto-overwritten); (7) Auto-Repair — detect/diagnose/propose/apply/verify phase gates, 3-consecutive-failure circuit breaker, never-auto-repair list (migrations, deployed artifacts, auth config, prohibited zones); (8) Metrics Calibration — reviews 7-30 day KPI history, proposes statistically-derived thresholds, requires user approval, caps relaxation at 20% per cycle, excludes security/financial metrics from auto-calibration.

## Relations & where used

- The Skill Adaptation (#4), Skill Auto-Loader (#5), and Skill Registry Protocol (#6) rules described here are the rule-side counterpart to the same flows documented from the skill/hook side in `skills.md` (Auto-Detection Flow, Auto-Improvement Flow) and `hooks.md` (`skill-feedback-tracker.sh` deep-dive).
- License Policy (#3) summarizes the same Allowed/Caution/Blocked tiers documented in full detail (with named tools) in `blocked-tools.md`.
- Control Manifest's 5-tier complexity scale matches the task-scaling table in `automation.md` almost verbatim (trivial/small/medium/large/critical -> direct/opsx-propose/opsx-apply/sdd-new/sdd-verify).

## Status / caveats

- **Direct numeric conflict with `rules-consolidation-plan.md`** (same batch, same directory): this document states the *current* always-loaded core set is **16 rules** out of **150+ total**, cutting tokens from ~93K to ~21K. The consolidation plan instead frames 73 total rules (14 core, proposed) with a 73K->35K token reduction. Core-rule-set membership also differs: this doc's 16 include `rate-limiting.md` and `model-routing.md` (absent from the plan's 14) and lack `definition-of-done.md` and `agent-security.md` (present in the plan's 14). Not reconciled here — flagged for operator triage on which document reflects ground truth, and whether `rules.md` is describing a state that has since evolved past the original 14-rule proposal.
- No date/version marker in this document, unlike `rules-consolidation-plan.md` (dated 2026-03-29) — cannot establish which document is chronologically authoritative from internal evidence alone.

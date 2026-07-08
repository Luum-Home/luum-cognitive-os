---
type: concept-synthesis
source: docs/04-Concepts/architecture/agentic-mastery-license-weight-dx-matrix.md
provenance: "Decide which external agentic-AI tools may influence Cognitive OS core, adapters, or benchmark lanes without introducing license, weight, or data-sharing risk"
---

## What it is
Policy and matrix classifying external agentic-AI tools/frameworks as reference-only, optional-CLI, optional-benchmark-adapter, or blocked, gated by license, weight, and DX value, so nothing becomes a default dependency without a pinned-version license check.

## Key mechanics
- 4 allowed integration modes: Reference (no dependency), Optional CLI/dev lane (explicit opt-in), Optional benchmark adapter (benchmark lanes only), Blocked (incompatible license/weight/provenance/data-sharing).
- License gate fields required before any tool moves beyond reference: repository URL, immutable version/tag, SPDX license ID, transitive-dependency scan (AGPL/SSPL/BSL/ELv2 blocked), install mode (none/optional-cli/optional-container/dev-only/vendored), data-sharing disclosure, default-impact-must-be-zero.
- Weight scale: None (docs only) / Low (small module, no service) / Medium (extra CLI/report path, not hot path) / High (dependency trees, external APIs, long scans) / Very high (Docker images, benchmark datasets, browser/OS envs, multi-repo harnesses).
- DX scale: High (daily operator confidence or prevents severe mistakes) / Medium (maintainer/periodic value) / Low (research/comparison only).
- Matrix categories with example recommended dispositions: Security/Lethal Trifecta (Simon Willison doctrine -> implement internally as policy, no dependency; snyk/agent-scan, promptfoo, garak, Augustus -> optional scanners/red-team lanes, not default; oktsec, agent-security-scanner-mcp -> reference-first pending license verification); Agent-Computer Interface (SWE-agent ACI -> reference/design influence; opencode, aider -> reference/optional adapter for UX patterns); Skill efficacy (SkillsBench, DSPy, agentevals -> reference/optional benchmark, no default import); Runtime benchmarks (SWE-bench, OpenHands, Agentless -> optional/reference, too heavy for default); Adversarial generalization (AgentBench, OSWorld, WildClawBench, AgencyBench -> reference taxonomies only, very-high weight).
- Default install impact table: Lethal Trifecta Gate = one Python module + one Bash hook + JSONL metrics; ACI MVP = one normalizer + docs once implemented; skill efficacy = reads existing metrics, on-demand reports; runtime/adversarial benchmarks = zero default runtime cost, explicit-command only. No Docker images, external datasets, npm trees, eval frameworks, or SaaS scanners installed by default.
- Implementation decision: build internal deterministic cores first; keep all external tools opt-in; require pinned-version license evidence before each adapter; benchmark before making DX claims; present simple reports (`safety`, `aci`, `skills`, `benchmark`, `adversarial`).
- Automated license gate: pinned manifest at `.cognitive-os/tests/agentic-tools/license-matrix.json`, checked by `scripts/agentic_tool_license_matrix.py` (stdlib-only, no network, blocks AGPL/SSPL/BSL/ELv2/Commons-Clause, blocks `default_enabled=true` for High/Very-high-weight external tools); optional wrapper `scripts/agentic-tool-license-matrix.sh`.

## Relations & where used
Feeds near-term actions: implement Lethal Trifecta Gate MVP; extend `scripts/agentic_tool_license_matrix.py` for new pinned metadata; add optional-tool status reporting to `make test-agentic-mastery` once it exists.

## Status / caveats
Dated 2026-05-02; many entries marked "Needs pinned verification" (license confidence low/medium) — those tools stay at reference status until verified.

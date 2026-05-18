# ADR-OSS-001: Open-Sourcing Cognitive OS

## Status
Proposed


## Current public-license posture

This document is a historical strategy memo. The current repository posture is
FSL-1.1-MIT with an automatic MIT future license, documented in
[`docs/09-Quality/legal/license-faq.md`](../../09-Quality/legal/license-faq.md).
The community-facing interpretation is:

Generally allowed before the Change Date:

- self-hosting for your own organization;
- internal company use;
- production use for your own organization or for products where Cognitive OS
  is not the primary product;
- consulting where Cognitive OS is used as a tool; and
- building applications or products where Cognitive OS is not the primary
  product.

Generally not allowed before the Change Date without a separate commercial
arrangement when the primary value derives substantially from Cognitive OS:

- hosted Cognitive OS;
- managed agent runtime;
- agent orchestration SaaS;
- control plane SaaS for third-party agents; and
- white-label resale of Cognitive OS.

The older Apache-2.0 recommendation below remains useful as community strategy
analysis, but it is not the current license of the repository.

---

## Context

Cognitive OS (COS) is a governance framework for AI coding agents. It is currently developed in a private repository (Luum-Home/luum-cognitive-os on GitHub) with zero external contributors. The competitive landscape has shifted: Agent Zero (16.5K stars, MIT license) and OpenClaw (340K+ stars, MIT license) are both fully open-source and building community-driven ecosystems. The absence of community around COS is a strategic weakness that limits adoption, feedback velocity, and ecosystem growth.

This document analyzes whether to open-source COS, under what license, with what monetization strategy, and on what timeline.

---

## 1. Current State

| Dimension | Value |
|-----------|-------|
| Repository | Private (Luum-Home/luum-cognitive-os, GitHub) |
| External contributors | 0 |
| Community | None |
| Stars / forks | 0 / 0 |
| Test suite | 5045+ tests across behavior, unit, hook, and integration layers |
| Security layers | 14 (content policy, secret detection, aguara, semgrep, parry, etc.) |
| Unique features | SDD pipeline, trust scoring, adversarial review, consequence system, agent governance |
| Development model | Internal team + AI agents (dogfooding) |
| License | None (all rights reserved) |

All development is performed by a small internal team assisted by AI agents running on COS itself. There is no public documentation site, no contributor guide, and no issue tracker visible to external parties.

---

## 2. Why Open Source

### 2.1 Community Contributions

COS has a modular architecture (skills, hooks, rules, packages) that is designed for extensibility. Opening the source enables:

- Third-party skills for frameworks COS does not cover today (Rails, Django, Spring Boot patterns)
- Community hooks for CI/CD systems beyond what the core team supports
- Package contributions (the `packages/` directory is explicitly designed for optional add-ons)
- Bug reports from diverse environments that the internal team cannot reproduce

### 2.2 Trust and Transparency

COS is a security and governance tool. Users are asked to trust that 14 security layers, content policies, and agent permission systems work correctly. Closed-source security tools face inherent credibility challenges: users cannot verify the claims. Open-sourcing allows security researchers to audit the codebase, which strengthens rather than weakens the security posture.

### 2.3 Ecosystem Effects

The value of COS increases with the number of available skills, hooks, and packages. This is a classic network effect: more users produce more extensions, which attract more users. Agent Zero's 16.5K stars translate directly into a skill ecosystem that COS cannot match alone.

### 2.4 Competitive Positioning

Both major competitors are MIT-licensed. A closed-source COS competes against free alternatives that offer full source access. The differentiation must come from capabilities, not from restricting access. COS's governance depth (SDD, trust scoring, adversarial review, consequence system) is the competitive advantage, and that advantage is stronger when visible.

### 2.5 Talent Attraction

Developers evaluate tools by reading source code. A private repository is invisible to potential contributors and adopters. Open-sourcing creates a public portfolio of the engineering quality and architectural decisions behind COS.

---

## 3. Why NOT Open Source

### 3.1 Competitive Advantage Exposure

Opening the source reveals the full architecture of COS's governance system. Competitors could replicate the SDD pipeline, trust scoring, or adversarial review protocol. However, these are documented in rules files that are already the primary deliverable -- the value is in the system design and integration, not in hidden implementation secrets.

**Assessment**: Low risk. The architecture is the product. Copying individual rules without the integration does not replicate the system.

### 3.2 Support Burden

Open-source projects attract issues, questions, and feature requests. Without dedicated community management, these become a drain on the core team.

**Assessment**: Medium risk. Mitigated by clear contribution guidelines, issue templates, and a "community-supported" tier for non-core packages.

### 3.3 Quality Control

Community PRs vary in quality. Reviewing external contributions takes time and may introduce regressions if the review process is insufficient.

**Assessment**: Medium risk. Mitigated by COS's own quality gates (5045 tests, adversarial review, trust scoring). The CI pipeline already enforces quality standards that external PRs must pass.

### 3.4 Monetization Complexity

Once the code is open, charging for the same code requires a clear value-add. Pure open-source models rely on indirect monetization (support, hosting, enterprise features).

**Assessment**: Manageable. See section 6 for monetization models that work alongside open source.

---

## 4. License Options

| License | Adoption Friction | IP Protection | SaaS Protection | Community Trust | Enterprise Acceptance |
|---------|-------------------|---------------|-----------------|-----------------|----------------------|
| MIT | Lowest | None | None | Highest | Highest |
| Apache-2.0 | Low | Patent grant | None | High | Highest |
| AGPL-3.0 | High | Strong copyleft | Yes (forces sharing) | Medium | Low (enterprise avoids) |
| BSL 1.1 (Business Source) | Medium | Time-delayed open | Yes (usage restriction) | Low (community distrust) | Medium |
| Dual (MIT core + commercial) | Low for core | Selective | Yes (commercial features) | Medium | High for core |
| ELv2 (Elastic License) | Medium | Usage restriction | Yes | Low | Low |

### License Analysis

**MIT**: Maximum adoption, zero friction. This is what Agent Zero and OpenClaw use. The downside is that a well-funded competitor could fork COS, rebrand it, and offer it as a competing product without contributing back. Given COS's current market position (zero community), the risk of hostile forking is low -- there is no community to fork away.

**Apache-2.0**: Similar adoption profile to MIT with the addition of an explicit patent grant. This protects both the project and contributors from patent litigation. The patent grant is particularly relevant for COS because the governance patterns (trust scoring, adversarial review, consequence system) could theoretically be patented by a third party.

**AGPL-3.0**: Would force any SaaS provider using COS to open-source their modifications. This protects against the "cloud strip-mining" scenario where AWS/GCP/Azure offer COS-as-a-Service without contributing back. However, AGPL scares enterprise adopters and reduces the addressable market significantly. COS's own license policy (`rules/license-policy.md`) blocks AGPL dependencies, which would create an internal contradiction.

**BSL 1.1**: Restricts commercial use for a time period (typically 2-4 years), after which it converts to a permissive license. Hashicorp, MariaDB, and CockroachDB use this model. Community trust in BSL has eroded after high-profile license changes (Redis, Elasticsearch, Terraform). Starting with BSL creates a credibility deficit that a new project cannot afford.

**Dual License**: MIT/Apache for the core, commercial license for premium features. This is the model used by GitLab (MIT core + proprietary EE), Supabase (Apache core + commercial), and many others. It provides maximum adoption for the core while preserving monetization options.

---

## 5. What to Open Source

### Fully Open (MIT or Apache-2.0)

| Component | Rationale |
|-----------|-----------|
| Core rules (`rules/`) | The governance framework is the primary value proposition; transparency builds trust |
| Core hooks (`hooks/`) | Hook system is the execution engine; must be auditable |
| Core skills (`skills/`) | Community skill contributions require an open skill format and reference implementations |
| Templates (`templates/`) | Agent preambles and prompt templates are non-sensitive |
| CLI (`cmd/cos/`) | The CLI is the primary user interface; must be freely distributable |
| Packages (`packages/`) | Designed for community extensibility |
| Documentation (`docs/`) | Documentation is a growth driver, not a monetization vector |
| Tests (`tests/`) | Test suite demonstrates quality; enables community CI |
| Libraries (`lib/`) | Python libraries implement the rules; must be auditable |
| Infrastructure configs (`docker-compose*.yml`) | Reference architecture for self-hosting |
| Configuration schema (`cognitive-os.yaml`) | Users need the full config surface to adopt COS |

### Candidates for Premium / Enterprise Tier

| Feature | Rationale |
|---------|-----------|
| Managed SaaS hosting | Operational convenience, not source code |
| Enterprise SSO/RBAC for multi-team COS | Organizational features beyond single-developer use |
| Priority support SLA | Service, not code |
| Advanced analytics dashboard | Visualization layer over open metrics |
| Compliance reporting (SOC2, HIPAA templates) | Industry-specific governance templates |
| Singularity daemon (autonomous MAPE-K loop) | Advanced automation that requires careful operational support |

**Key principle**: The core governance engine should be fully open. Premium features should be operational conveniences, team-scale features, or managed services -- not restrictions on single-developer functionality.

---

## 6. Monetization Models

### Model A: Fully Open, Sell Services

Open-source everything under Apache-2.0. Revenue from consulting, custom integrations, and training.

| Pros | Cons |
|------|------|
| Maximum community trust | Revenue scales with headcount, not software |
| Simplest license | Hard to build a venture-scale business |
| No "open core" confusion | Consulting is low-margin |

**Viable for**: Bootstrapped or lifestyle business. Not suitable for venture-funded growth.

### Model B: Open Core + Premium Packages

Core COS is Apache-2.0. Enterprise features (multi-team RBAC, compliance templates, advanced analytics) are proprietary add-ons.

| Pros | Cons |
|------|------|
| Clear value ladder | "What's free vs paid?" friction |
| Community builds on open core | Risk of community resentment if features move to premium |
| Proven model (GitLab, Supabase) | Requires maintaining two codebases |

**Viable for**: Venture-backed company with enterprise sales motion.

### Model C: Managed Hosting (COS-as-a-Service)

Open-source everything. Offer a hosted version where COS runs in the cloud with integrated observability, team management, and zero-setup.

| Pros | Cons |
|------|------|
| No license complexity | Requires significant infrastructure investment |
| "Open source but easy" value prop | Competes with self-hosting (the product is a config framework) |
| Recurring revenue | COS is developer tooling, not a server -- hosting value is less obvious |

**Viable for**: If COS evolves into a centralized agent orchestration platform with persistent state.

### Model D: Dual License (Community + Commercial)

Apache-2.0 for individual use. Commercial license required for organizations above a threshold (e.g., >50 developers, or revenue >$10M).

| Pros | Cons |
|------|------|
| Protects against large-company free-riding | Complex license creates adoption friction |
| Revenue from enterprises that can afford it | Community may distrust dual licensing |
| Allows full open development | Legal overhead |

**Viable for**: Projects with proven enterprise demand. Premature for COS at current stage.

---

## 7. Recommendation

### License: Apache-2.0

Apache-2.0 is the recommended license for the following reasons:

1. **Patent protection matters for a governance framework.** COS defines novel patterns (trust scoring, adversarial review protocol, consequence system, SDD pipeline). The Apache-2.0 patent grant prevents a third party from patenting these patterns and suing COS users.

2. **Adoption parity with competitors.** MIT and Apache-2.0 have near-identical adoption profiles. Both Agent Zero and OpenClaw use MIT; Apache-2.0 is equally accepted by enterprises and has strictly better legal protection.

3. **No internal contradiction.** COS's own license policy permits Apache-2.0. Using AGPL would conflict with the policy that governs the project itself.

4. **Enterprise readiness.** Apache-2.0 is on every enterprise approved-license list. No legal review friction for adopters.

### Monetization: Open Core (Model B) with path to Managed Hosting (Model C)

**Phase 1 (months 0-6)**: Fully open under Apache-2.0. No premium tier. Focus entirely on community growth and adoption. Revenue is zero; investment is in ecosystem building.

**Phase 2 (months 6-12)**: Introduce premium packages for enterprise features (multi-team RBAC, compliance templates, advanced analytics dashboard). These are new code, not paywalled existing features. The community edition loses nothing.

**Phase 3 (months 12-24)**: If demand materializes for centralized COS orchestration, build a managed hosting tier. This becomes viable only if COS evolves into a multi-agent orchestration platform with persistent state.

### What to Open Source: Everything Currently Existing

All current code, rules, hooks, skills, packages, tests, and documentation should be open-sourced. There is nothing in the current codebase that constitutes a proprietary secret worth protecting more than the community growth it prevents. The competitive advantage is the system design and integration quality, which is strengthened by transparency.

---

## 8. Roadmap to Open Source

### Phase 1: Cleanup (weeks 1-2)

| Task | Description |
|------|-------------|
| Secret audit | Run `secret-detector.sh` on entire repo; verify no API keys, tokens, or credentials in source |
| Content audit | Run `content-policy.sh` on entire repo; remove any internal references, employee names, or private URLs |
| Dependency audit | Run `cos audit` on all dependencies; verify all licenses are compatible with Apache-2.0 |
| Docker image audit | Verify all Docker images use digest pinning; no internal registry references |
| History scrub | Review git history for accidentally committed secrets; consider starting with a clean history if needed |
| Configuration review | Ensure `cognitive-os.yaml` contains no sensitive defaults; all secrets use env var references |

### Phase 2: License and Legal (week 3)

| Task | Description |
|------|-------------|
| Add LICENSE file | Historical recommendation: Apache-2.0 full text at repo root |
| Add NOTICE file | Required by Apache-2.0; list copyright holders and any third-party notices |
| Add license headers | Add Apache-2.0 header to all source files (Go, Python, Shell) |
| CLA decision | Decide whether to require a Contributor License Agreement (recommended for patent protection) |
| Trademark policy | Document "Cognitive OS" and "COS" trademark usage guidelines |

### Phase 3: Public Repository (week 4)

| Task | Description |
|------|-------------|
| Create public repo | `luum/cognitive-os` on GitHub (or `luum/luum-agent-os` to maintain continuity) |
| Transfer or mirror | Either transfer the private repo or push a clean history to the public repo |
| Enable GitHub features | Issues, Discussions, Projects, Actions |
| Branch protection | Require PR reviews, passing CI, and signed commits on main |
| Security policy | Add SECURITY.md with vulnerability reporting instructions |

### Phase 4: Community Infrastructure (weeks 5-6)

| Task | Description |
|------|-------------|
| CONTRIBUTING.md | Contribution guidelines: PR process, code style, test requirements, skill contribution guide |
| CODE_OF_CONDUCT.md | Standard contributor covenant |
| Issue templates | Bug report, feature request, skill proposal, security vulnerability |
| PR template | Checklist: tests pass, docs updated, no secrets, license headers present |
| CI pipeline | GitHub Actions: test suite, lint, license check, secret scan on every PR |
| Documentation site | Deploy docs to GitHub Pages or dedicated site (Mintlify, Docusaurus, or similar) |
| Skill contribution guide | How to create, test, and submit a new skill package |

### Phase 5: Launch (weeks 7-8)

| Task | Description |
|------|-------------|
| Launch blog post | Technical deep-dive on COS architecture, governance model, and why it exists |
| Hacker News submission | Post with honest framing: "We built a governance OS for AI agents, here's the source" |
| Product Hunt launch | Focus on the "AI agent safety" angle |
| Reddit posts | r/programming, r/MachineLearning, r/LocalLLaMA, r/ClaudeAI |
| Dev community outreach | Dev.to article, Twitter/X thread, LinkedIn post |
| Discord or GitHub Discussions | Community hub for questions, skill sharing, and roadmap discussion |
| "Good first issue" labels | Tag 10-15 issues as good entry points for new contributors |

---

## 9. Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Hostile fork by well-funded competitor | Low | High | Apache-2.0 patent grant; build community loyalty through responsiveness; brand and trust are not forkable |
| Low initial adoption | Medium | Medium | Expected. Measure progress in months, not weeks. 100 stars in month 1 is a success signal. |
| Support burden overwhelms team | Medium | Medium | Clear "community-supported" tiers; issue templates with required reproduction steps; community moderators |
| Security vulnerability disclosed publicly | Medium | High | SECURITY.md with responsible disclosure process; private vulnerability reporting via GitHub; 48-hour response SLA |
| Community PR quality issues | High | Low | CI gates enforce test passage, lint, and license compliance; COS's own quality system reviews PRs |
| Contributor drops malicious skill | Low | High | Aguara scan on all PRs; mandatory code review; skills in `auto-generated/` are clearly marked as unreviewed |

---

## 10. Success Metrics

| Metric | 3-Month Target | 6-Month Target | 12-Month Target |
|--------|---------------|----------------|-----------------|
| GitHub stars | 500 | 2,000 | 5,000 |
| External contributors | 5 | 20 | 50 |
| Community skills/packages | 3 | 15 | 40 |
| Open issues (healthy range) | 20-50 | 50-150 | 100-300 |
| Monthly downloads (cos CLI) | 100 | 500 | 2,000 |
| Discord/Discussions members | 50 | 200 | 500 |

---

## Consequences

### What becomes easier

- Community contributions to skills, hooks, and packages
- Security auditing by external researchers
- Adoption by enterprises that require source access
- Talent recruitment (public portfolio of engineering quality)
- Integration with other open-source agent frameworks

### What becomes harder

- Keeping premium features clearly differentiated from the open core
- Managing community expectations and support requests
- Maintaining code quality with external contributors
- Preventing community fragmentation through forks
- Protecting the "Cognitive OS" brand identity

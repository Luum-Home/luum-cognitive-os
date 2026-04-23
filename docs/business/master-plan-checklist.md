# Master Plan Checklist

> Living checklist for tracking execution of the durable product master plan.

## How To Use This Checklist

- Mark items complete only when there is evidence in code, docs, CI, demos, or tests.
- Prefer linking real artifacts when a checkbox is completed.
- Treat unchecked items as product work, not just documentation wishes.

## 1. Product Promise

- [x] The README expresses the same core product promise as the master plan.
- [x] CONTRIBUTING is aligned with the product-core narrative instead of subsystem sprawl.
- [x] The product promise is documented in [Durable Product Master Plan](durable-product-master-plan.md).
- [x] The product promise is documented in [Master Plan Execution Requirements](master-plan-execution-requirements.md).
- [x] Product positioning is documented in [Product Messaging](product-messaging.md).

## 2. Protected Core

- [x] A machine-readable kernel contract exists in [manifests/kernel-contract.yaml](../../manifests/kernel-contract.yaml).
- [x] Kernel scope is documented in [Kernel Contract](../kernel-contract.md).
- [x] Kernel contract tests exist.
- [x] The skills/rules portability gap is documented in [Skills and Rules Portability Gap](../architecture/skills-rules-portability-gap.md).
- [x] The canonicalization risk of moving skills/rules out of `.claude/` is documented in [Skills and Rules Canonicalization Risk Analysis](../architecture/skills-rules-canonicalization-risk-analysis.md).
- [x] A step-by-step migration plan exists in [Skills and Rules Canonicalization Workplan](../architecture/skills-rules-canonicalization-workplan.md).
- [x] Status and diagnostic tooling can read canonical-first artifact surfaces without changing install destinations.
- [x] Core versus compatibility versus extension versus experimental taxonomy is documented in [Product Zones](../product-zones.md).
- [x] New runtime additions are consistently classified by zone through root guardrails in [Product Zones Manifest](../../manifests/product-zones.yaml).
- [x] Central runtime paths avoid hardcoding non-core subsystems by default through [Runtime Hardcoding Discipline](../architecture/runtime-hardcoding-discipline.md) and `tests/contracts/test_runtime_hardcoding.py`.

## 3. Capability-Centric Enforcement

- [x] Capability profiles exist in the runtime.
- [x] Model routing uses capability-centric execution profiles before model choice.
- [x] Compatibility inventory explicitly distinguishes implemented and documented surfaces.
- [x] Dispatch uses capability-centric execution paths.
- [x] Gateway selection is capability-centric before vendor-centric.
- [x] Skill routing is capability-centric before vendor-centric.
- [x] Execution records and metrics include execution-profile data, not only model branding.

## 4. CI and Validation Integrity

- [x] Default CI covers representative Python product tests.
- [x] Default CI covers Go kernel and provider tests.
- [x] Default CI covers representative contract tests.
- [x] Default CI covers key behavior tests.
- [x] Default CI includes documentation integrity checks.
- [x] Release-plumbing checks can reason about canonical-first skill surfaces without changing install destinations.
- [x] Release-plumbing checks can validate the active settings driver instead of assuming `.claude/settings.json` is the only settings surface.
- [x] Audit and wiring validation can read the active settings driver instead of assuming `.claude/settings.json` is the only runtime surface.
- [x] CLI health and hook reporting can read the active settings driver instead of assuming `.claude/settings.json` is the only user-facing runtime surface.
- [x] Transparency/status reporting can read the active settings driver instead of assuming `.claude/settings.json` is the only hook-wiring surface.
- [x] Uninstall paths clean the active settings driver instead of assuming `.claude/settings.json` is the only hook-registration surface.
- [x] Secondary user-facing scripts use canonical project-root precedence when reading runtime state.
- [x] Update and auto-update paths preserve the active harness/settings driver instead of silently assuming Claude.
- [x] Driver-specific user-facing scripts are explicitly classified so Claude-only registration/profile flows do not masquerade as Codex support.
- [x] Broken product-facing links fail visibly in automation.
- [x] Product claims in README and pitch map to explicit verification paths through [Product Proof Paths](../manual-tests/proof-paths.md).

## 5. Onboarding and Operational Simplicity

- [x] First-run installation is one-pass and low-friction through [First-Run Onboarding Proof](../manual-tests/first-run-onboarding.md).
- [ ] Autodetection reduces required configuration for new users.
- [x] Settings projection supports more than one harness target in bootstrap paths.
- [x] CLI runtime reads canonical skill/rule artifacts when the Claude projection is absent.
- [x] Upgrade paths preserve the active harness instead of silently falling back to Claude-first settings projection.
- [x] Emergency-stop keeps the core safety path cross-harness while marking Claude-only profile projection honestly.
- [ ] Skills and rules use canonical-first discovery instead of depending on `.claude/` as the primary surface.
- [x] User-facing setup messages are clear and product-grade.
- [x] `hooks/self-install.sh` meets its performance expectations.
- [x] Setup and onboarding flows have visible performance budgets and regression tests through `scripts/demo-first-run-onboarding.sh` and `tests/integration/test_first_run_onboarding.py`.
- [x] A non-expert can reach a working baseline without reading deep architecture docs through [First-Run Onboarding Proof](../manual-tests/first-run-onboarding.md).

## 6. Complexity Compression

- [x] The repo is explicitly classified into core, compatibility, extensions, and experimental zones through [manifests/product-zones.yaml](../../manifests/product-zones.yaml).
- [x] Major docs present non-core systems as optional or secondary through [README](../../README.md), [Docs Index](../README.md), and [Product Zones](../product-zones.md).
- [x] Dashboard-heavy messaging is de-emphasized in top-level product docs.
- [x] Squad and organization-heavy messaging is de-emphasized in top-level product docs.
- [x] Experimental subsystems that compete with the wedge are archived, frozen, or clearly demoted through the product-zone taxonomy and top-level docs.
- [x] A feature reality audit exists to classify core, optional, and overextended surfaces.

## 7. Visible Proof

- [x] Provider compatibility is explicitly inventoried.
- [x] Provider-agnostic outcome metrics exist.
- [x] A canonical demo shows provider and harness switching without system rewrites through [Five-Minute Demo](../manual-tests/five-minute-demo.md) and `scripts/demo-portability-proof.sh`.
- [x] A canonical demo shows real quality gates in action through [Five-Minute Demo](../manual-tests/five-minute-demo.md).
- [x] A canonical demo shows the core becoming usable in minutes through [Five-Minute Demo](../manual-tests/five-minute-demo.md).
- [x] The repo contains a short proof path for “easy to adopt, serious to trust” through [Product Proof Paths](../manual-tests/proof-paths.md).
- [x] The repo contains a short proof path for resilience under ecosystem churn through [Product Proof Paths](../manual-tests/proof-paths.md).

## 8. Immediate Known Gaps

- [x] Fix `README.md` reference to missing `docs/benchmark-results.md`.
- [x] Fix `CONTRIBUTING.md` references from `tests/run-all-tests.sh` to `scripts/run-all-tests.sh`.
- [x] Redesign `.github/workflows/ci.yml` around the real product core.
- [x] Triage and improve `hooks/self-install.sh` performance against behavior-test expectations.
- [x] Publish a simple “core vs extension” taxonomy document or section.
- [x] Prepare a canonical five-minute product demo path through [Five-Minute Demo](../manual-tests/five-minute-demo.md).

## Success Signal

- [x] A new user can understand the product quickly.
- [x] A new user can install it without pain.
- [x] A new user can see real evidence of value quickly.
- [x] A new user can grow into deeper capabilities without needing agent-infrastructure expertise first.

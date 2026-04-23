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
- [ ] Core versus compatibility versus extension versus experimental taxonomy is documented across major product docs.
- [ ] New runtime additions are consistently classified by zone.
- [ ] Central runtime paths avoid hardcoding non-core subsystems by default.

## 3. Capability-Centric Enforcement

- [x] Capability profiles exist in the runtime.
- [x] Model routing uses capability-centric execution profiles before model choice.
- [x] Compatibility inventory explicitly distinguishes implemented and documented surfaces.
- [ ] Dispatch uses capability-centric execution paths.
- [ ] Gateway selection is capability-centric before vendor-centric.
- [ ] Skill routing is capability-centric before vendor-centric.
- [ ] Execution records and metrics are organized around capabilities, not model branding.

## 4. CI and Validation Integrity

- [x] Default CI covers representative Python product tests.
- [x] Default CI covers Go kernel and provider tests.
- [ ] Default CI covers contract tests.
- [x] Default CI covers key behavior tests.
- [x] Default CI includes documentation integrity checks.
- [ ] Broken product-facing links fail visibly in automation.
- [ ] Product claims in README and pitch map to explicit verification paths.

## 5. Onboarding and Operational Simplicity

- [ ] First-run installation is one-pass and low-friction.
- [ ] Autodetection reduces required configuration for new users.
- [x] Settings projection supports more than one harness target in bootstrap paths.
- [ ] Skills and rules use canonical-first discovery instead of depending on `.claude/` as the primary surface.
- [ ] User-facing setup messages are clear and product-grade.
- [x] `hooks/self-install.sh` meets its performance expectations.
- [ ] Setup and onboarding flows have visible performance budgets and regression tests.
- [ ] A non-expert can reach a working baseline without reading deep architecture docs.

## 6. Complexity Compression

- [ ] The repo is explicitly classified into core, compatibility, extensions, and experimental zones.
- [ ] Major docs present non-core systems as optional or secondary.
- [ ] Dashboard-heavy messaging is de-emphasized in top-level product docs.
- [ ] Squad and organization-heavy messaging is de-emphasized in top-level product docs.
- [ ] Experimental subsystems that compete with the wedge are archived, frozen, or clearly demoted.
- [x] A feature reality audit exists to classify core, optional, and overextended surfaces.

## 7. Visible Proof

- [x] Provider compatibility is explicitly inventoried.
- [x] Provider-agnostic outcome metrics exist.
- [ ] A canonical demo shows provider switching without system rewrites.
- [ ] A canonical demo shows real quality gates in action.
- [ ] A canonical demo shows the core becoming usable in minutes.
- [ ] The repo contains a short proof path for “easy to adopt, serious to trust.”
- [ ] The repo contains a short proof path for resilience under ecosystem churn.

## 8. Immediate Known Gaps

- [x] Fix `README.md` reference to missing `docs/benchmark-results.md`.
- [x] Fix `CONTRIBUTING.md` references from `tests/run-all-tests.sh` to `scripts/run-all-tests.sh`.
- [x] Redesign `.github/workflows/ci.yml` around the real product core.
- [x] Triage and improve `hooks/self-install.sh` performance against behavior-test expectations.
- [ ] Publish a simple “core vs extension” taxonomy document or section.
- [ ] Prepare a canonical five-minute product demo path.

## Success Signal

- [ ] A new user can understand the product quickly.
- [ ] A new user can install it without pain.
- [ ] A new user can see real evidence of value quickly.
- [ ] A new user can grow into deeper capabilities without needing agent-infrastructure expertise first.

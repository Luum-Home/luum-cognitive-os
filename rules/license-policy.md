<!-- SCOPE: both -->
<!-- TIER: 2 -->
# License Policy

For commercial or closed-source projects, all dependencies must comply with this policy. Adjust only when the adopting project's licensing model explicitly allows a different risk posture.

## General Rule

Before integrating any open-source tool, library, package, model, or service dependency, verify its license and the licenses of its transitive dependencies.

## Permitted Licenses

| License | Verdict | Conditions |
|----------|-----------|-------------|
| MIT | ✅ SAFE | Preserve the copyright notice. |
| BSD-2, BSD-3 | ✅ SAFE | Preserve the copyright notice. |
| Apache 2.0 | ✅ SAFE | Preserve NOTICE files and document material changes where required. |
| ISC | ✅ SAFE | Preserve the copyright notice. |
| CC0 / Public Domain | ✅ SAFE | No material restrictions for project use. |

## Use with Caution

| License | Verdict | Conditions |
|----------|-----------|-------------|
| LGPL v2.1/v3 | ⚠️ CAUTION | Use only as a dynamically linked library. Do not modify LGPL source code without review. Do not statically link without legal approval. |
| MPL 2.0 | ⚠️ CAUTION | Changes to MPL-covered files must be published, but separate project code can remain closed. |
| Artistic 2.0 | ⚠️ CAUTION | Similar to MPL: changes to the original covered work may need to be published. |

## Blocked for SaaS or Closed-Source Product Use

| License | Verdict | Reason |
|----------|-----------|---------|
| AGPL v3 | 🚫 BLOCKER | Network users can trigger source-disclosure obligations for the combined service. |
| SSPL | 🚫 BLOCKER | Blocks managed-service/SaaS use without releasing service-side source. |
| BSL (Business Source License) | 🚫 BLOCKER | Often restricts competitive or production use until a future change date, with terms that vary by vendor. |
| ELv2 (Elastic License) | 🚫 BLOCKER | Blocks offering the software as a managed service. |
| Commons Clause | 🚫 BLOCKER | Blocks selling or offering the software as a service. |
| FSL (Functional Source License) | 🚫 BLOCKER | Similar risk profile to BSL: commercial-use restrictions may apply. |
| Server Side Public License | 🚫 BLOCKER | SSPL variant with the same managed-service restriction profile. |

## Mandatory Procedure

1. **Before adding any dependency**: verify the license in the authoritative upstream source, package registry, or repository.
2. **Transitive dependencies count**: if package A is MIT but depends on package B under AGPL/SSPL/BSL/ELv2, package B can still block adoption.
3. **Dual licensing**: if a tool offers Community (AGPL or similar) plus Commercial, evaluate the commercial license before adoption.
4. **When in doubt**: do not integrate. Find a permissively licensed alternative or escalate for explicit review.
5. **Document the decision**: record non-trivial license decisions in `docs/03-PoCs/research/license-analysis.md` or the adopting project's equivalent evidence path.

## Exceptions

A tool under AGPL, SSPL, BSL, ELv2, Commons Clause, FSL, or a similar restrictive license may be considered only if all of the following are true:

- It runs as a completely separate service, such as its own container or externally hosted endpoint.
- Its source code is not modified.
- The project communicates with it only through a documented public API.
- The justification, residual risk, and operational boundary are documented.
- A human operator explicitly approves the exception before integration.

Even when these conditions are met, the preferred decision is to choose a permissively licensed alternative.

## Contextual Trigger

- When work adds, upgrades, evaluates, vendors, embeds, or deploys a dependency.
- When work references licensing, package selection, model adoption, SaaS use, or managed-service restrictions.

# License FAQ — Cognitive OS (luum-agent-os)

> **Status**: published alongside the v1.0 launch.
> **License**: [FSL-1.1-MIT](../../LICENSE) (Functional Source License,
> Version 1.1, with an MIT future license).
> **Canonical FSL spec**: <https://fsl.software/>.
> **Template this license follows**: <https://fsl.software/FSL-1.1-MIT.template.md>.

This document exists because re-licensing is a sensitive topic. Several
projects (HashiCorp, Elastic, MongoDB, Redis) have learned the hard way
that changing license terms without a clear, honest explanation gets
read as a "rug pull". We would rather over-explain up front than be
defensive on Hacker News later.

---

## 1. TL;DR

Cognitive OS is released under **FSL-1.1-MIT**: free to use, fork,
modify, and embed in commercial products, with one carve-out — you
cannot offer a hosted, managed version of *this project itself* as a
commercial service that competes with us. Every file automatically
re-licenses to plain **MIT** two years after that file's publication
date. We did not change the license of any previously-published version
of this project; FSL-1.1-MIT is the license we are launching v1.0 under.

---

## 2. What is FSL-1.1-MIT?

The Functional Source License (FSL) is a short, plain-English
source-available license. The full text is in
[`LICENSE`](../../LICENSE) at the root of this repository.

The mechanics are:

1. You may **use, copy, modify, create derivative works, publish, and
   redistribute** the Software.
2. There is **one limitation**: you may not "Sell" the Software, where
   "Sell" is defined as offering a product or service to third parties
   (for a fee or other consideration, including hosting fees) **whose
   value derives, entirely or substantially, from the functionality of
   the Software**. In practical terms: do not run a managed
   Cognitive-OS-as-a-service that competes with us.
3. On the **second anniversary** of the date a given file was first
   made available under FSL ("Change Date"), the license on that file
   automatically converts to the **MIT License**. The clock is per-file,
   per-publication-date, not for the project as a whole. This is
   self-executing — no further action by us is required.

What FSL does **not** do:

- It does not require you to open-source your own code that integrates
  with Cognitive OS.
- It does not impose a viral / copyleft obligation.
- It does not require source disclosure for SaaS that uses Cognitive OS
  as a building block.
- It does not restrict internal use, research, education, or
  redistribution.

---

## 3. Why we changed from Apache 2.0

Honest version: the Apache 2.0 marker on the repository before v1.0 was
a **placeholder during private development**, not a released public
license. We had not published a public release. When we sat down to
choose the actual launch license, we evaluated Apache 2.0, BSL, FSL,
SSPL, ELv2 and CC BY-NC, and concluded FSL-1.1-MIT is the most honest
fit for our model.

The commercial rationale, plainly:

- We are a small team building a commercial product on top of
  Cognitive OS. We want the project to be openly developed, openly
  forkable, and durable beyond us.
- Apache 2.0 would let any large cloud provider repackage the project
  as a managed service the day after launch, without contributing back.
  That has happened to ElasticSearch, MongoDB, Redis, and others, and
  it kills the economics that fund the OSS work.
- BSL (HashiCorp / MariaDB) and SSPL (MongoDB / Elastic) attracted
  significant criticism — BSL because its "Additional Use Grant"
  language is opaque and the change-window is four years; SSPL because
  it forces operators of a managed service to open-source their entire
  hosting stack, which is widely viewed as overreach. We deliberately
  did not pick either.
- FSL is **intentionally narrower than BSL or SSPL**. The only thing
  it forbids is offering this very project as a competing managed
  service. The conversion window is **two years**, not four. The
  future license is MIT, not "the vendor's choice later". That is as
  close to a credible "eventually fully permissive" promise as a
  source-available license can structurally make.
- We are launching v1.0 under FSL-1.1-MIT from day one. We are not
  retroactively re-licensing previously-published versions, because
  there are none. If at some future point we wanted to change the
  license again, see Section 10.

We acknowledge the tradeoff: FSL is **not OSI-approved** today, and
the OSS purist community will (rightly) note that "source-available"
is not the same thing as "open source" under the OSI definition. We
do not claim otherwise.

---

## 4. What you CAN do

Concrete, non-exhaustive examples of permitted use:

- **Use it internally** at your company, for any purpose, on any number
  of machines, with any number of employees. No registration, no email,
  no key.
- **Use it in research, education, or personal projects.**
- **Fork the repository** on GitHub or anywhere else, modify it, and
  publish your fork — provided your fork stays under FSL-1.1-MIT and
  carries the same notices.
- **Build commercial products on top of Cognitive OS** that are not
  themselves a competing managed offering of Cognitive OS. This
  includes: SaaS products that use Cognitive OS as an internal engine,
  agent platforms that embed it, consulting engagements that deploy it
  for clients, vertical applications, internal developer tools, and so
  on. The license is concerned with reselling *the project itself*,
  not with what you build with it.
- **Redistribute** the Software, in source or binary form, under the
  same FSL-1.1-MIT terms, with attribution.
- **Audit, study, and modify** the source. There are no "obfuscated
  binary" or "encrypted release" tricks — the source on GitHub is
  the source.
- **Wait two years and use any given file under MIT.** That conversion
  is automatic and irrevocable for that file at that date.

---

## 5. What you CANNOT do (until a file's two-year clock expires)

Concrete, non-exhaustive examples of restricted use:

- **Offer Cognitive OS as a competing managed service.** Examples:
  spinning up "Cognitive OS Cloud" as a paid hosted offering, white-
  labelling Cognitive OS as a SaaS, or selling a service whose value
  is substantially derived from running Cognitive OS for paying
  customers.
- **Resell hosting or paid support** for Cognitive OS as a standalone
  service whose value derives substantially from the project.
- **Strip attribution** from redistributed copies. The license requires
  the Sell limitation notice to travel with any required attribution.

What is **not** restricted:

- A SaaS product that uses Cognitive OS internally to deliver some
  *other* value to customers (an analytics product, a coding agent
  for a specific vertical, a workflow tool, etc.) is fine. The
  customer is not buying Cognitive OS; they are buying the thing
  you built on top of it.
- Consulting engagements where you bill for your time integrating
  Cognitive OS into a client environment are fine. The customer is
  paying for your work, not for Cognitive OS itself.

If you are not sure whether your use case is "competing managed
service" or "product built on top", contact us (Section 12). We will
answer in writing.

---

## 6. Two-year clock — how it works

The clock is **per file**. Each file's clock starts on the date that
file was first published under FSL-1.1-MIT. Two calendar years later,
the license on that file converts to the MIT License automatically,
with no further action required by us. The MIT terms become as set
forth in the second half of the [`LICENSE`](../../LICENSE) file.

Practical consequences:

- Files published in calendar year *N* become MIT-licensed in calendar
  year *N+2*.
- Newer files published later have later Change Dates. A repository
  snapshot you take today contains a mix of files at different points
  in their two-year clocks.
- You can determine a file's publication date from Git history. We do
  not maintain a separate "Change Date manifest"; the canonical record
  is the commit history of this repository.
- Releases (Git tags) do not reset the clock. A bug-fix to an
  already-published file does not reset the clock for the unchanged
  parts of that file; it does start a clock for the changed lines as
  of their publication date. In practice, treating the file's most
  recent material publication as the clock start is the safe reading.

We do not have authority to *delay* the conversion. The license text
makes it automatic. We can only choose to convert *earlier* (see
Section 10).

---

## 7. Comparison table

This is a rough comparison, not legal advice. See the actual license
texts for authoritative terms.

| Property | Apache 2.0 | FSL-1.1-MIT (this project) | BSL 1.1 | SSPL | AGPL-3.0 |
|---|---|---|---|---|---|
| Restrictions on use | none beyond patent grant | one: no competing managed service | no production use without "Additional Use Grant" | none, but heavy obligation | none, but heavy obligation |
| OSI-approved | yes | **no** (source-available) | no | no | yes |
| Time-bomb to permissive | n/a | **2 years → MIT, automatic, per file** | 4 years → vendor-chosen OSI license | n/a | n/a |
| Source-disclosure obligation for SaaS | none | none | none | **must open-source your entire hosting stack** | **must open-source modifications when serving over a network** |
| Patent grant | explicit | implicit via MIT future + via grant text | depends on Additional Use Grant | yes | yes |
| Typical perception in 2026 | "real OSS" | "honest BSL" / source-available | "BSL — read carefully" | widely criticised | strong copyleft, polarising |
| Notable users | Kubernetes, LangChain | Sentry, GitButler | MariaDB, SurrealDB, HashiCorp (then changed) | MongoDB, Elastic (then changed) | Grafana (some), Nextcloud |

We picked FSL specifically because (a) the conversion is shorter and
mechanically simpler than BSL, (b) the restriction is narrower than
SSPL, and (c) the future license is plain MIT, the most permissive
option, with no vendor discretion.

We do not know whether OSI will eventually approve FSL. As of writing,
they have not, and we are not aware of an active review. If that
changes, we will update this FAQ.

---

## 8. What about contributors?

Contributions to this repository are accepted under the project's
license — i.e. you grant your contributions under FSL-1.1-MIT, with
the same automatic two-year conversion to MIT applying to your
contribution from the date it is merged.

We use the **Developer Certificate of Origin (DCO)** sign-off (see
[`CONTRIBUTING.md`](../../CONTRIBUTING.md)) rather than a CLA. We do
**not** ask contributors to assign copyright to us. You retain
copyright in your contributions; you grant us and downstream users the
license rights described in [`LICENSE`](../../LICENSE).

Because copyright is not assigned, we cannot unilaterally re-license
contributed code under terms incompatible with FSL-1.1-MIT or its MIT
successor. Any future move to a more permissive license (Section 10)
is straightforward; any move to a more restrictive license would
require explicit agreement from contributors, which we are not
contemplating.

---

## 9. What about downstream consumers?

If you maintain a project that depends on Cognitive OS — including
internal Luum projects, downstream consumer projects in the wider
ecosystem, or third-party integrations — here is what you should plan
for:

- **Embedding Cognitive OS as a library or runtime dependency** is
  permitted. You do not need to relicense your own project. Your
  project keeps its own license.
- **Redistributing Cognitive OS** (e.g. shipping it inside a Docker
  image, bundling it in an installer) is permitted under FSL-1.1-MIT
  with attribution. The bundled copy of Cognitive OS remains under
  FSL-1.1-MIT until each file's Change Date elapses.
- **Offering your downstream product as SaaS** is permitted, including
  to paying customers, as long as your product is not a competing
  managed offering of Cognitive OS itself.
- **Forking Cognitive OS for internal modification** is permitted; the
  fork remains under FSL-1.1-MIT.
- **Any downstream Luum consumer projects** that depend on this
  repository are governed by the same rules as any other consumer.
  They are not granted special permissions.

If your downstream project's license is incompatible with FSL-1.1-MIT
in some way, the practical workaround is to depend on Cognitive OS
across a process or network boundary (CLI, daemon, MCP server) rather
than statically linking source — which is how Cognitive OS is already
typically integrated.

---

## 10. What if FSL turns out to be hostile to OSS?

This is the question we take most seriously, because the failure mode
of source-available licensing is exactly that the project drifts away
from its OSS roots over time and contributors feel betrayed.

Our public commitment:

- **The two-year, per-file conversion to MIT is structural.** It is
  written into the license text we shipped. We cannot retroactively
  remove it from already-published files. If we tried, the published
  copies on GitHub, on mirrors, and in Git history remain valid under
  the original FSL-1.1-MIT terms.
- **We will not move to a more restrictive license** (e.g. BSL, SSPL,
  proprietary, NC) for this project. We chose FSL specifically
  because it is at the *lenient* end of source-available; moving
  more restrictive would defeat the point.
- **We may move to a more permissive license** (MIT, Apache 2.0) for
  the project as a whole if the commercial concerns that motivated
  FSL stop applying. Concretely: if Cognitive OS does not develop a
  meaningful "managed-service competitor" risk, we have no reason
  to keep the Sell carve-out, and we would rather drop it.
- **We will document any license change in this FAQ and in an ADR**,
  with the rationale, the effective date, and the impact on
  downstream consumers, before the change takes effect.

We do not commit to a specific timeline for re-evaluation, because
making a public timeline commitment we cannot verifiably keep would
be worse than not making one. What we can say is that the two-year
clock is the floor: every file becomes MIT no later than two years
from its publication, regardless of what we do or fail to do.

---

## 11. Won't this kill adoption?

Possibly. We acknowledge this is a real risk. Source-available
licensing has measurable adoption friction:

- Some enterprise procurement processes auto-reject any non-OSI
  license, regardless of terms.
- Some package indexes and distributions (e.g. Linux Foundation
  projects, some CNCF processes, Homebrew's SPDX list) cannot list
  FSL projects in the same way they list Apache/MIT projects.
- The OSS purist community on Hacker News and Reddit will, fairly,
  point out that FSL is not OSI-approved.

We accept that cost in exchange for being able to invest in the
project commercially without the rug-pull risk that has hit Apache-
licensed competitors. We would rather have a smaller, more committed
user base under an honest license than a larger user base under
Apache 2.0 followed by a panicked re-license to BSL eighteen months
in.

Signals that would make us reconsider and move to a more permissive
license:

- The "competing managed service" risk does not materialise — i.e.
  no major cloud provider or third party attempts to repackage
  Cognitive OS as a hosted offering.
- We confirm via measurement that the FSL restriction is materially
  blocking adoption of the project among legitimate users.
- The OSS ecosystem reaches a stable consensus position on FSL that
  is meaningfully different from today's "useful but not OSI".

We will revisit this annually as part of our public roadmap review
and document the outcome in an ADR.

---

## 12. Where to ask questions

- **Specific licensing question about your use case**: open a
  discussion or issue in this repository, or email the maintainer
  contact listed in [`CONTRIBUTING.md`](../../CONTRIBUTING.md). We
  will answer in writing. We do not consider these questions a sign
  of bad faith — most of them are reasonable, and we would rather
  answer them once publicly than have ten companies independently
  consult external lawyers.
- **General feedback on the license choice**: file an issue tagged
  `license`. We read all of them.
- **Commercial inquiries / managed-service partnership**: contact
  details in `CONTRIBUTING.md`.

This FAQ will be updated as the project evolves. The
[`LICENSE`](../../LICENSE) file is the legally authoritative document;
where this FAQ and the LICENSE appear to disagree, the LICENSE
controls.

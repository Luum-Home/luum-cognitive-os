# License FAQ — Cognitive OS (luum-agent-os)

> **Current license**: [FSL-1.1-MIT](../../LICENSE) — Functional Source
> License 1.1 with an automatic MIT future license.
>
> **Canonical FSL site**: <https://fsl.software/>
>
> This FAQ is explanatory only. The repository [`LICENSE`](../../LICENSE) file
> is authoritative if this document and the license text differ.

Cognitive OS moved from an Apache-2.0 pre-launch/default license posture to
FSL-1.1-MIT for the public launch. This page explains that choice plainly:
what is free, what is restricted, what changes relative to Apache 2.0, and how
commercial use works.

## Short version

FSL-1.1-MIT lets you read, use, copy, modify, fork, publish, and redistribute
Cognitive OS for free. You may also use it inside commercial products.

The restriction is that, before the MIT conversion date, you may not sell a
product or service whose value derives entirely or substantially from Cognitive
OS itself. The practical target is a paid hosted/managed Cognitive OS offering,
paid support/hosting for Cognitive OS as the product, or a white-labelled resale
of Cognitive OS.

After the Change Date in the license, the covered software automatically becomes
MIT-licensed.

## Why FSL instead of Apache 2.0?

Apache 2.0 is a strong, familiar open-source license. We understand why users
prefer it. The reason we chose FSL-1.1-MIT is narrower: we want the source to be
public and usable while avoiding immediate resale of the project itself as a
managed service by a better-capitalized vendor.

The project needs a commercial path to fund maintenance. Apache 2.0 would allow
a third party to launch a hosted Cognitive OS service using this code without
asking, without waiting, and without contributing. FSL gives us a limited period
of protection against that specific business risk while preserving a guaranteed
move to MIT.

We chose FSL-1.1-MIT over more restrictive source-available licenses because:

- it is short and readable;
- the restriction is tied to selling the software itself, not ordinary use;
- it does not impose copyleft or network-source-disclosure obligations;
- it converts automatically to MIT after two years; and
- the future license is fixed now, not left to a later vendor decision.

## When does it convert to MIT?

Under the license text, the FSL grant automatically converts to MIT on the
second anniversary of the date the covered software was first made available
under FSL-1.1-MIT. That date is the **Change Date**.

For the initial public FSL-covered release, that means two years after its
publication date. For material added later, use the date that material was first
made available under FSL-1.1-MIT. The repository history is the practical record
for those dates.

The conversion is automatic. We do not need to publish a new license file for it
to take effect, and we cannot delay it for already-published FSL-covered code.
We can only choose to move earlier to MIT or another more permissive license.

## What can users do for free?

You can, without paying Luum:

- use Cognitive OS internally at a company;
- use it for personal, educational, research, or nonprofit work;
- inspect and audit the source code;
- fork the repository;
- modify it;
- publish patches or forks under the same license terms;
- redistribute source or binaries with the required notices;
- run it as part of your own development workflow;
- embed it in a product or service whose primary value is something other than
  reselling Cognitive OS; and
- use the MIT-converted code under MIT after the applicable Change Date.

No license key, registration, usage reporting, or revenue share is required by
FSL-1.1-MIT.

## What changed relative to Apache 2.0?

The important differences are:

| Topic | Apache 2.0 | FSL-1.1-MIT |
|---|---|---|
| OSI-approved open source | Yes | No; source-available until MIT conversion |
| Internal use | Allowed | Allowed |
| Modification and redistribution | Allowed | Allowed, with the FSL Sell limitation until conversion |
| Commercial products built with it | Allowed | Allowed when the product is not substantially Cognitive OS itself |
| Selling hosted/managed Cognitive OS | Allowed | Not allowed before the Change Date |
| Copyleft/source disclosure | None | None |
| Patent grant | Express patent grant | No Apache-style express patent grant in the FSL text |
| Future permissive license | Already permissive | Automatically becomes MIT after two years |

So the material change is the temporary Sell limitation. FSL-1.1-MIT is less
permissive than Apache 2.0 until conversion. After conversion, the code is under
MIT, which is permissive but still not identical to Apache 2.0.

## What is not being hidden?

A few points should be explicit:

- FSL-1.1-MIT is **not OSI-approved** as of this FAQ.
- Until the Change Date, this is **source-available**, not OSI open source.
- The license is less permissive than Apache 2.0 for anyone who wants to sell
  Cognitive OS itself as a hosted/managed/support product.
- Apache 2.0 references before this switch were part of the pre-launch/default
  licensing posture, not something we are trying to erase.
- If any copy was actually distributed to you under Apache 2.0 before the
  switch, this FAQ does not claw back rights you already received for that copy.
  New releases and new copies are under the repository license in effect when
  they are made available.
- The public source is the source. There is no hidden proprietary replacement in
  this repository.
- This FAQ is not a private side agreement. The LICENSE file controls.

## How does this interact with commercial use?

Commercial use is allowed when Cognitive OS is a tool, dependency, or internal
engine for a product whose value is not substantially Cognitive OS itself.

Examples that are generally permitted before the Change Date:

- a company using Cognitive OS internally for engineering workflows;
- a SaaS product that uses Cognitive OS behind the scenes to deliver a distinct
  application to customers;
- a vertical agent product that embeds Cognitive OS as infrastructure;
- a consulting project where you are paid to build or integrate a broader
  customer solution that uses Cognitive OS; and
- redistribution of Cognitive OS as part of a larger product, with notices,
  where the larger product is not essentially resale of Cognitive OS.

Examples that are restricted before the Change Date:

- selling "Cognitive OS Cloud" or a substantially equivalent hosted version;
- charging for hosting Cognitive OS as the main service;
- selling paid support for Cognitive OS as the standalone product; or
- white-labelling Cognitive OS for customers as the thing being purchased.

The distinction is the source of value. If customers are paying for your own
application and Cognitive OS is an implementation detail, that is different from
customers paying for Cognitive OS itself.

## Do contributors assign copyright?

No. Contributors keep copyright in their contributions. Contributions are made
under the repository license, so they follow FSL-1.1-MIT and the same automatic
MIT conversion. See [`CONTRIBUTING.md`](../../CONTRIBUTING.md) for contribution
process details.

## Will the project become more restrictive later?

The two-year MIT conversion for already-published FSL-covered code is built
into the license and cannot be delayed retroactively. We may move future code to
a more permissive license earlier if the managed-service resale concern stops
being important.

We do not intend to move this project to a more restrictive license. If the
license changes again, we will document the change publicly with the rationale,
effective date, and downstream impact.

## Who should ask for clarification?

If your use case depends on the line between "using Cognitive OS commercially"
and "selling Cognitive OS itself," open a repository issue or discussion. Public
answers are preferable because other users likely have the same question.

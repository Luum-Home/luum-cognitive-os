# Portable `.ai` Consumer Package Spec

Status: implemented
Date: 2026-05-12

## Purpose

The maintainer `.ai/` tree is a generated, machine-readable overlay for COS
maintainers. A consumer project needs a more legible package: README-first
Markdown that explains which agentic primitives exist, what each adapter can
project, and where runtime enforcement is or is not claimed.

This spec defines that human-readable consumer shape without changing the
canonical source of truth.

## Source of truth

The consumer package is generated from:

- `manifests/primitive-contracts.yaml`
- `manifests/primitive-lifecycle.yaml`
- `manifests/harness-projection.yaml`
- the generated maintainer `.ai` overlay produced by `scripts/portable_ai_overlay.py`

Generated consumer Markdown is never canonical. Edits must flow back to the
manifests or source primitives.

## Package shape

A projected consumer `.ai/` package has this shape:

```text
.ai/
  README.md
  context/
    overview.md
  primitives/
    INDEX.md
    hooks/*.md
    skills/*.md
    rules/*.md
    tools/*.md
    ...
  adapters/
    INDEX.md
    <harness>.md
```

Every Markdown file starts with frontmatter containing
`schema_version: portable-ai-consumer-package.v1` and
`package_role: human-readable-consumer-view`.

The package intentionally does not emit JSON files. JSON remains the maintainer
contract overlay; Markdown is the consumer onboarding surface.

## Fidelity boundary

The consumer package may explain a primitive and link it to an adapter, but it
must preserve the fidelity declared by COS profiles and adapter manifests:

- `structural-advisory` stays advisory Markdown or host rules.
- `documented-only` stays documentation.
- runtime enforcement can be claimed only when the source profile/contract
  already declares runtime-capable fidelity and a governed driver emits native
  host files.

## Smoke proof

`scripts/cos-portable-ai-consumer-package-smoke` writes the package to a
disposable consumer tempdir and proves:

- README-first Markdown package exists;
- primitive Markdown count matches primitive overlay rows;
- adapter Markdown count matches adapter manifests;
- all emitted files have frontmatter;
- no JSON files are emitted into the consumer package; and
- no canonical `hooks/`, `skills/`, `rules/`, or `manifests/` directories are
  written into the consumer project.

The tracked latest proof lives at
`docs/reports/portable-ai-consumer-package-smoke-latest.json` and `.md`.

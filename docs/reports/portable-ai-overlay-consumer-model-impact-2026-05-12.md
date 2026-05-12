# Portable `.ai` Overlay vs Consumer `.ai` Model Impact — 2026-05-12

## Purpose

This report records the repository comparison that clarified why the Cognitive OS
maintainer `.ai/` tree looks very different from a consumer-project `.ai/` tree,
and what impact follows from the recommended split between canonical contracts,
generated overlays, and consumer-friendly adapter packaging.

## Local comparison

Compared repositories:

- `<luum-cognitive-os-root>/.ai`
- `<consumer-project-root>/.ai`

Observed shape:

| Dimension | Cognitive OS maintainer repo | Practice consumer repo |
|---|---|---|
| Approximate size | 389 files / 3.6 MB | 152 files / 1.2 MB |
| Primary role | Generated portable overlay/export surface | Human-oriented consumer toolkit |
| Primitive format | Machine-readable JSON rows | Markdown skills, rules, workflows, hooks |
| Adapter format | Generated `adapter.json` plus README per harness | `install.sh` scripts plus README per IDE |
| Source of truth | `manifests/primitive-contracts.yaml`, `manifests/primitive-lifecycle.yaml`, `manifests/harness-projection.yaml`, plus `hooks/`, `skills/`, `rules/`, `scripts/` | `.ai/primitives/*`, `.ai/context/*`, `.ai/scripts/*` |
| Consumer projection | Product/installer flow through `cos_init.py`, `cos-adapters`, harness drivers, ACC, and smoke reports | Already projected into root files such as `AGENTS.md`, `CLAUDE.md`, `.cursor/rules`, `.windsurfrules`, `.github/copilot-instructions.md`, `.codex/AGENTS.md`, `.opencode/agents.md`, `.kiro/instructions.md` |

The difference is intentional, but it was under-documented. Cognitive OS is the
runtime/product that owns contracts and proof. The practice repo is closer to the
shape a consumer should see after installing or authoring primitives for one
project.

## External pattern check

Current agent-tooling conventions support a layered model rather than a single
universal file:

- OpenAI Codex loads `AGENTS.md` through a global/project/subdirectory instruction chain, with override precedence and size limits: <https://developers.openai.com/codex/guides/agents-md>.
- Claude Code separates `CLAUDE.md`, `.claude/settings.json`, hooks, subagents, MCP, and skills with scoped configuration: <https://code.claude.com/docs/en/settings> and <https://code.claude.com/docs/en/skills>.
- Cursor project rules live under `.cursor/rules/*.mdc` and can coexist with `AGENTS.md`: <https://docs.cursor.com/context/rules-for-ai>.
- Windsurf distinguishes Memories, Rules, Workflows, Skills, and `AGENTS.md`, with `.windsurf/rules/*.md` as a workspace rules surface: <https://docs.windsurf.com/windsurf/cascade/memories>.
- Continue local rules live under `.continue/rules`, while Hub rules are referenced separately: <https://docs.continue.dev/customize/rules>.
- GitHub Copilot uses repository custom instructions such as `.github/copilot-instructions.md`: <https://docs.github.com/en/copilot/how-tos/custom-instructions/adding-repository-custom-instructions-for-github-copilot>.
- ACP separates editor-agent transport from the agent's internal primitive model: <https://agentclientprotocol.com/get-started/introduction>.

The common architecture is therefore:

```text
canonical semantics
  -> portable/intermediate contract
  -> host-specific projection
  -> runtime evidence when the host can actually run it
```

No current cross-IDE convention makes every primitive runtime-enforceable in every
IDE. Structural instruction projection remains weaker than lifecycle hooks or a
host plugin adapter.

## Recommendation captured

Do not collapse Cognitive OS into the consumer `.ai/` layout. Instead, make the
three roles explicit:

```text
canonical contract layer
  manifests/primitive-contracts.yaml
  manifests/primitive-lifecycle.yaml
  manifests/harness-projection.yaml
  hooks/ skills/ rules/ scripts/

maintainer generated overlay
  .ai/context.json
  .ai/primitives/**/*.json
  .ai/profiles/*.json
  .ai/adapters/*/{adapter.json,README.md}

consumer package shape
  AGENTS.md and native IDE files
  .cognitive-os/ runtime artifacts
  optional .ai/ README/context/primitives/adapters view that is human-oriented
```

The consumer package may look like the practice repo because that shape is easy
to inspect. It must still be generated or synchronized from canonical COS
contracts when it is produced by Cognitive OS.

## Impact of the recommendation

### Positive impact

1. **Less conceptual ambiguity** — `.ai/` in the maintainer repo is no longer
   mistaken for the canonical primitive source.
2. **Better consumer experience** — consumer projects can receive a clearer,
   README-first package without forcing maintainers to edit generated JSON.
3. **Honest portability claims** — adapter profiles continue to expose
   `native-lifecycle-enforced`, `governed-wrapper-enforced`,
   `structural-advisory`, `ci-enforced`, and `documented-only` separately.
4. **Lower migration risk** — existing hooks, tests, settings drivers, and ACC
   proof remain stable while consumer packaging improves.
5. **Better product story** — Cognitive OS remains a governable/verifiable
   operational layer, not a hand-maintained prompt bundle.

### Negative impact / cost

1. **More documentation burden** — docs must keep the distinction between
   canonical contracts, generated overlay, and consumer package explicit.
2. **More generated-surface drift risk** — `.ai/`, consumer projections, and
   adapter manifests require freshness tests.
3. **Potential double vocabulary** — maintainers must avoid saying “`.ai` is
   canonical” unless ADR-258 Phase 5 or a future ADR actually accepts that.
4. **Consumer packaging work remains** — the current generated maintainer overlay
   is not yet as friendly as the practice repo's `.ai/README.md` + install-script
   layout.

### Required follow-up work

- Add a consumer-package spec that defines what Cognitive OS should project into
  consumer repos when a human-readable `.ai/` view is requested.
- Add or extend tests that prove generated consumer `.ai/` packages do not mutate
  canonical maintainer files.
- Keep ACC language tied to `manifests/harness-projection.yaml` proof levels.
- Avoid runtime-enforcement claims for Cursor, Copilot, Windsurf, Continue, and
  other structural hosts until account-backed runtime smoke or native plugin
  adapters exist.

## Acceptance criteria for future changes

```text
1. Maintainer `.ai/` remains generated from canonical manifests and source trees.
2. Consumer `.ai/` package, if generated, is explicitly marked as consumer-facing.
3. Adapter outputs cite their proof level and never upgrade structural projection to enforcement.
4. Docs distinguish AGENTS.md/SKILL.md/MCP/ACP from `.ai` instead of treating them as interchangeable.
5. Any canonical migration of `.ai/` requires a new ADR beyond ADR-258.
```

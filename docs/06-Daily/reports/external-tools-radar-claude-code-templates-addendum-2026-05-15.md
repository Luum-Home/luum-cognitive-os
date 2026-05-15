---
report_type: external-tools-radar-addendum
date: 2026-05-15
tool: davila7/claude-code-templates
classification: ASSESS
adoption_kind: installer-ux-and-marketplace-patterns
license: MIT
source_urls:
  - https://github.com/davila7/claude-code-templates
related_files:
  - docs/03-PoCs/research/repo-scout/deep/davila7__claude-code-templates-2026-05-15.md
  - scripts/cos_init.py
  - install.sh
  - manifests/harness-projection.yaml
  - manifests/primitive-projection-profiles.yaml
  - manifests/harness-driver-capabilities.yaml
  - tests/behavior/test_consumer_project_projection.py
  - tests/integration/test_installer.py
---

# External Tools Radar Addendum — Claude Code Templates

## Verdict

**ASSESS / installer-UX and marketplace-pattern reference.**

`davila7/claude-code-templates` is valuable as a Claude Code marketplace and
component installer reference. It should not displace the Cognitive OS canonical
primitive model because it writes directly to Claude-specific surfaces and does
not maintain a harness-agnostic primitive source of truth.

Cognitive OS is directionally correct: keep agentic primitives canonical under
`.cognitive-os/`, project them into `.claude`, `.codex`, `.cursor`, `AGENTS.md`,
`opencode.json`, and other harness surfaces, and attach explicit proof levels to
each projection.

## Tool and document map

### Upstream tool: `davila7/claude-code-templates`

| Associated document/code | Role in this assessment |
|---|---|
| `README.md` | Public positioning, install examples, component/template promise. |
| `cli-tool/README.md` | CLI capabilities: project setup, analytics, health, agents, skills. |
| `cli-tool/docs_to_claude/ARCHITECTURE.md` | Modular architecture reference for setup/dashboard tooling. |
| `cli-tool/docs_to_claude/CLAUDE_DATA_STRUCTURE.md` | Claude session/settings structure used by analytics tooling. |
| `cli-tool/docs_to_claude/HOOKS_GUIDE.md` | Native Claude hook expectations. |
| `cli-tool/docs_to_claude/COMMANDS_GUIDE.md` | Slash-command packaging expectations. |
| `cli-tool/docs_to_claude/SUBAGENTS_GUIDE.md` / `SUB_AGENTS.md` | Agent/subagent packaging expectations. |
| `cli-tool/docs_to_claude/STATUSLINE_GUIDE.md` | Statusline settings pattern. |
| `cli-tool/SKILLS_DASHBOARD.md` | Skill inventory/dashboard UX. |
| `cli-tool/bin/create-claude-config.js` | CLI entrypoint and option surface. |
| `cli-tool/src/index.js` | Orchestration of setup, individual installs, dashboards, and health checks. |
| `cli-tool/src/templates.js` | Language/framework template model. |
| `cli-tool/src/file-operations.js` | Backup, merge, retry/cache, GitHub raw download patterns. |
| `cli-tool/src/agents.js` | Agent scanner/installer into `.claude/agents`. |
| `cli-tool/src/command-scanner.js` | Command scanner and metadata extraction. |
| `cli-tool/src/hook-scanner.js` | Claude settings hook scanner/filter. |
| `cli-tool/components/*` | Marketplace inventory for agents, commands, hooks, MCPs, settings, skills. |

### Cognitive OS surfaces that own the equivalent concern

| COS document/code | Role |
|---|---|
| `scripts/cos_init.py` | Author-once/project-many harness projection. |
| `install.sh` | Top-level installer UX; should be aligned with the full harness set. |
| `manifests/harness-projection.yaml` | Harness status, paths, projected surfaces, limitations, proof levels. |
| `manifests/primitive-projection-profiles.yaml` | Projection-profile intent for primitive classes. |
| `manifests/harness-driver-capabilities.yaml` | Driver capability and fidelity model. |
| `docs/04-Concepts/architecture/ide-agnostic-primitive-projection.md` | Architecture boundary for IDE-agnostic primitive projection. |
| `docs/04-Concepts/architecture/consumer-project-primitive-accessibility.md` | Consumer-project projection/accessibility contract. |
| `docs/04-Concepts/architecture/portable-ai-consumer-package-spec.md` | Consumer `.ai` package boundary. |
| `docs/06-Daily/reports/external-tools-radar-portable-primitives-addendum-2026-05-09.md` | Existing radar baseline for portable primitive standards. |
| `tests/behavior/test_consumer_project_projection.py` | Structural projection proof across supported harnesses. |
| `tests/integration/test_installer.py` | Installer smoke proof for Claude/Codex and leakage prevention. |

## Decision matrix

| Question | Finding | COS decision |
|---|---|---|
| Should COS store canonical primitives in `.claude/*`? | Upstream does; it is Claude-native. | **No.** `.claude` remains a projection target. |
| Should COS copy the component marketplace UX? | Upstream has useful granular install flows. | **Yes, clean-room.** Add harness-aware primitive catalog UX. |
| Should COS copy backup/merge/retry behavior? | Upstream has practical operator safeguards. | **Yes, clean-room.** Apply to projection writers. |
| Is COS projection architecture wrong? | No; `cos_init.py` already has the better agnostic split. | **Keep.** Improve installer exposure and proof docs. |
| Is `install.sh` fully aligned? | No; it still presents mostly `claude|codex`. | **Fix next.** Delegate/expand harness validation. |
| Can we claim every IDE today? | No; some harnesses are structural-only and Windsurf is planned. | **Do not overclaim.** Publish proof-level-specific claims only. |

## Adoption boundary

Allowed:

1. Clean-room installer UX ideas.
2. Clean-room backup/merge/retry patterns.
3. Component catalog inspiration for a future primitive registry CLI.
4. Health/stats dashboard ideas that wrap existing COS audits.

Blocked:

1. Moving primitive truth into `.claude`.
2. Bulk importing upstream agents/skills/components without license and credential review.
3. Claiming runtime lifecycle parity for structural-only harnesses.
4. Claiming Windsurf support before driver and proof exist.

## Radar status

| Field | Value |
|---|---|
| Classification | `ASSESS` |
| Adoption kind | `installer-ux-and-marketplace-patterns` |
| Dependency posture | No default dependency, no vendoring. |
| Source posture | MIT; clean-room pattern extraction preferred anyway. |
| Consumer-project posture | No direct projection. Use only to improve COS installer/catalog UX. |
| Proof posture | Research-only until a COS primitive catalog CLI or installer expansion lands. |

## Next actions

1. Align `install.sh --harness` with `scripts/cos_init.py`'s harness list.
2. Add a primitive catalog/install UX that preserves `.cognitive-os/*` as source
   of truth and projects per harness.
3. Add a contract test that prevents `install.sh` from advertising fewer
   harnesses than `cos_init.py` supports, or explicitly documents the narrower
   top-level support.
4. Keep the existing Claude/Codex leakage tests and add equivalent smokes as new
   native or structural drivers are promoted.

## Research artifact

The simple research note for this addendum is:

- `docs/03-PoCs/research/repo-scout/deep/davila7__claude-code-templates-2026-05-15.md`

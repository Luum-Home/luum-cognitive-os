---
cluster: skills-prompts
date: 2026-05-06
phase: shallow
budget_max_tool_calls: 45
tool_calls_used: 4
totals:
  input: 9
  evaluated: 9
  pass_to_deep: 2
  monitor: 2
  reject: 5
verdict_counts:
  pass_to_deep: 2
  monitor: 2
  reject: 5
---

# Cluster: skills-prompts (shallow)

Theme: skill collections, prompt libraries, howto/best-practice guides, AGENTS.md spec, agent-skill installers.

Note: input file lists `sickn33/antigravity-awesome-skills` twice (with and without `.git`); deduplicated to 9 unique repos.

## Per-repo evaluation

### 1. agentsmd/agents.md
- URL: https://github.com/agentsmd/agents.md
- License: MIT
- Stars: 21,008
- Last commit: 2026-03-12
- Primary language: TypeScript
- Purpose: AGENTS.md — open format spec for guiding coding agents.
- Verdict: **pass-to-deep**
- Rationale: Cross-harness AGENTS.md spec is a primitive COS does not yet implement. Auto pass-to-deep per scout policy. Could inform `cross-harness-authoring` rule and AGENTS.md emitter for COS-init.

### 2. dmgrok/agent_skills_directory
- URL: https://github.com/dmgrok/agent_skills_directory
- License: MIT
- Stars: 15
- Last commit: 2026-04-29
- Primary language: Python
- Purpose: Intelligent skill discovery directory with quality validation, maintenance tracking, security scanning.
- Verdict: **pass-to-deep**
- Rationale: Overlaps directly with COS `skill-router` + `repo-scout` + `recommend-library`, but adds quality validation + security scan dimensions COS lacks. Worth deep dive to harvest scoring/ranking heuristics. Low star count tempers urgency, but novelty of primitive justifies deep phase.

### 3. forrestchang/andrej-karpathy-skills
- URL: https://github.com/forrestchang/andrej-karpathy-skills
- License: none (no LICENSE file)
- Stars: 114,674
- Last commit: 2026-04-20
- Primary language: (markdown)
- Purpose: Single CLAUDE.md derived from Karpathy's LLM coding pitfall observations.
- Verdict: **reject**
- Rationale: No LICENSE — cannot adopt code or text per scout policy. Star count is suspicious (likely viral-trend repo). Even patterns risky without licensing clarity.

### 4. luongnv89/claude-howto
- URL: https://github.com/luongnv89/claude-howto
- License: MIT
- Stars: 31,302
- Last commit: 2026-05-02
- Primary language: Python
- Purpose: Visual example-driven Claude Code guide with copy-paste templates.
- Verdict: **monitor**
- Rationale: Curated docs/templates with no new primitive vs COS's 107 skills + RULES-COMPACT. MIT-licensed so we could mine prompt patterns later, but not blocking. Re-check next cluster batch.

### 5. mattpocock/skills
- URL: https://github.com/mattpocock/skills
- License: MIT
- Stars: 61,463
- Last commit: 2026-04-30
- Primary language: Shell
- Purpose: Personal Claude Code skills directory ("Skills for Real Engineers").
- Verdict: **monitor**
- Rationale: High visibility curated skill set, MIT. No new primitive — COS already has skill-creator + skill-registry. Worth periodic harvesting for individual skill ideas, but cluster-level deep dive not warranted.

### 6. midudev/autoskills
- URL: https://github.com/midudev/autoskills
- License: CC-BY-NC-4.0 (verified from LICENSE file; gh API reported NOASSERTION)
- Stars: 5,104
- Last commit: 2026-05-04
- Primary language: Ruby
- Purpose: One-command installer for AI skill stack.
- Verdict: **reject**
- Rationale: CC-BY-NC-4.0 forbids commercial use. Per scout policy `Reject AGPL/SSPL/BSL/FSL/Elastic-2.0/CC-BY-NC`. Pre-flagged in input constraints.

### 7. sickn33/antigravity-awesome-skills
- URL: https://github.com/sickn33/antigravity-awesome-skills
- License: MIT
- Stars: 36,482
- Last commit: 2026-05-05
- Primary language: Python
- Purpose: Installable library of 1,400+ agentic skills + installer CLI for Claude Code, Cursor, Codex, Gemini, Antigravity.
- Verdict: **reject**
- Rationale: Curated awesome-list + installer. COS already has `install-recommended`, `skill-router`, 107 native skills. No new primitive worth harvesting; mostly aggregation of existing ecosystem. Skip per scout guidance "Curated lists with no new primitive → monitor", downgraded to reject because installer logic is harness-specific (not COS-shaped) and 1,400 skills would pollute search index.

### 8. trailofbits/skills
- URL: https://github.com/trailofbits/skills
- License: CC-BY-SA-4.0
- Stars: 5,017
- Last commit: 2026-05-05
- Primary language: Python
- Purpose: Trail of Bits security research / vulnerability detection / audit workflow skills.
- Verdict: **reject**
- Rationale: COS already integrates Trail of Bits skills via `[trailofbits-skills]` rule + dedicated integration. No new harvestable primitive at cluster level — already adopted. Re-classify here as reject (already-integrated, not a new candidate).

### 9. xcrawl-api/xcrawl-skills
- URL: https://github.com/xcrawl-api/xcrawl-skills
- License: none (no LICENSE file)
- Stars: 390
- Last commit: 2026-03-20
- Primary language: (none detected)
- Purpose: Xcrawl skill definitions for multi-agent web-data workflows.
- Verdict: **reject**
- Rationale: No LICENSE → cannot adopt. Vendor-specific (Xcrawl runtime), narrow API-crawl scope already covered by COS `web-crawler` skill. Skip.

## Phase 2 candidates

1. **agentsmd/agents.md** — auto pass-to-deep (AGENTS.md spec primitive). Deep goal: extract spec sections relevant to COS cross-harness emitter, evaluate adoption path for `cognitive-os-init` to write AGENTS.md alongside CLAUDE.md.
2. **dmgrok/agent_skills_directory** — pass-to-deep for quality-validation + security-scan heuristics that could enhance COS `skill-router` ranking and `skills-search` filtering. Low stars but novel scoring primitive.

Monitor (re-evaluate next batch): `luongnv89/claude-howto`, `mattpocock/skills`.

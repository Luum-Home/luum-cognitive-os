---
evaluated_at: 2026-05-09 23:20 UTC
engram_id: pending
deepwiki_url: null
batch: targeted-user-request
parent_radar: docs/06-Daily/reports/external-tools-radar-INDEX.md
introduced_by_commit: 418a37ca680a1264086df420a96db07dcd064ace
last_verified_commit: 418a37ca680a1264086df420a96db07dcd064ace
source_url: https://github.com/sentient-agi/EvoSkill
paper_url: https://arxiv.org/abs/2603.02766
---

## Repository Evaluation: sentient-agi/EvoSkill

### Classification: TRIAL-PATTERNS / ASSESS-RUNTIME
**Score**: 9.2/10 (mechanical), qualitative runtime call: **TRIAL-PATTERNS**.
**Evaluation Level**: 3 (deep — GitHub metadata + README + paper abstract + source audit from a fresh shallow clone).
**Theme**: self-improving-skills / benchmark-driven agent evolution  •  **Surface role**: skill synthesis loop and cross-harness evaluation harness.

### Summary

EvoSkill is an Apache-2.0 Python framework for automatically discovering and
synthesizing reusable coding-agent skills from failed trajectories. It runs a
closed loop: baseline agent execution, failure collection, proposer analysis,
skill or prompt generation, held-out validation, and frontier selection using
git branches. The public README claims compatibility with Claude Code,
OpenCode, OpenHands, Goose, and Codex CLI; the source includes a Codex-specific
`.agents/skills` symlink bridge and tests for that discovery path.

**Verdict rationale**: EvoSkill is the strongest post-radar fit for COS's own
skill-registry, skill-optimization, regression-audit, and primitive-evidence
roadmap. Do not import it as the default runtime yet: it mutates git branches,
writes `.claude/skills`, forwards model-provider credentials into Docker/remote
runs, and uses benchmark data that must be project-owned. Adopt the algorithmic
contract and fixture shape first; trial a bounded lab only after COS can enforce
workspace cleanliness, credential policy, provenance, rollback, and claim-debt
logging around each generated skill.

### Deep-analysis stage ledger

| Stage | Primitive used | What was checked | Finding | COS decision |
|---|---|---|---|---|
| 1. Discovery / positioning | Repo scout + radar index | README, GitHub metadata, arXiv abstract | Skill-evolution framework explicitly targets coding agents and reusable skill folders | Add to targeted Phase 4 radar additions |
| 2. Metadata / license | License gate | GitHub API, LICENSE, releases, actions | Apache-2.0, 710★, 77 forks, last push 2026-05-08, latest release v1.1.0 on 2026-05-05, two latest workflow runs green | License clean for pattern extraction and possible lab |
| 3. Paper / claims | Research-evidence review | arXiv abstract and README benchmark claims | Reported OfficeQA +7.3%, SealQA +12.1%, SealQA→BrowseComp transfer +5.3%; not independently reproduced in COS | Treat gains as motivation, not COS proof |
| 4. Source anatomy | Code audit | `src/loop/runner.py`, `src/registry/manager.py`, `src/harness/*`, `src/cache/*`, `src/evaluation/*` | Clean staged loop: failure sampling, proposer, generator, validation, frontier, cache, scorer, git branch registry | Extract architecture and acceptance tests |
| 5. Harness portability | Harness primitive audit | Claude/OpenCode/OpenHands/Goose/Codex executors and `src/harness/codex/skill_discovery.py` | Codex discovery uses `.agents/skills -> .claude/skills` symlink and avoids deleting real directories | Directly relevant to ADR-064 / harness projection, but must use COS canonical skill paths |
| 6. Safety / governance | Policy and supply-chain review | Docker launcher, remote Daytona path, ProgramManager git operations | Mutates branches/tags, writes skills/prompts, forwards env-var credentials, and can run remote sandboxes | Requires COS wrappers before runtime use |
| 7. Bidirectional cross-check | COS-vs-external comparison | COS skill registry, radar-update, ADR-247 manifest doctrine, Engram learning | EvoSkill is better at benchmark-driven skill synthesis; COS is stronger on governance and cross-project policy | Trial the loop behind COS governance; do not replace COS primitives |
| 8. Adoption planning | Adapter taxonomy | Dependency vs pattern-only vs lab adapter | Best initial kind is `pattern-only`; next is an opt-in `adapter-lab` for generated-skill regression fixtures | Add radar entry and bounded acceptance criteria |

### Scoring Breakdown

| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 10/10 | Direct overlap with COS skill optimization, agentic primitive evidence, and cross-harness skill packaging |
| License | 25% | 10/10 | Apache-2.0 confirmed by GitHub and LICENSE |
| Activity | 20% | 9.5/10 | Active repo: pushed 2026-05-08, v1.1.0 released 2026-05-05, recent green workflow runs |
| Maturity | 15% | 6.5/10 | Young March 2026 repo with promising tests and release cadence but limited production evidence |
| Integration | 10% | 8/10 | Python and skill-folder model are compatible; git mutation, credentials, Docker/remote runs, and harness path choices need wrappers |
| **Weighted Total** | | **9.2/10** | Mechanical score; runtime adoption remains gated |

### Adoption Signals

| Signal | Value | Descriptor |
|--------|-------|------------|
| Stars / forks | 710★ / 77 forks | strong early interest for a two-month-old project |
| Open issues / PRs | 1 issue + 7 PRs visible in GitHub UI; API open-issues count 8 | active but small queue |
| Release cadence | 3 releases; latest `v1.1.0` | early but real release hygiene |
| CI health | latest two workflow runs successful | green current signal, limited workflow history exposed |
| License | Apache-2.0 | clean for trial and pattern extraction |
| Paper backing | arXiv:2603.02766 | research narrative and benchmark claims exist |

### Key Findings

- **Loop shape**: EvoSkill implements the exact loop COS has been circling in
  separate primitives: attempt task, collect failures, propose a reusable skill
  or prompt change, generate the artifact, validate on held-out data, and keep
  only frontier-improving programs.
- **Failure memory**: `.evoskill/feedback_history.md` records discarded and kept
  proposals. This is conceptually close to Engram-backed postmortem learning,
  but EvoSkill keeps it repo-local and loop-specific.
- **Skill generation contract**: generated skills are written under
  `.claude/skills/<skill-name>/SKILL.md` with YAML frontmatter. For Codex, a
  tested symlink exposes the same skills through `.agents/skills`.
- **Frontier registry**: `program/*` branches and `frontier/*` tags model agent
  programs as versioned artifacts. This is useful, but should not run in COS
  workspaces without dirty-tree checks and rollback receipts.
- **Evaluation separation**: train failures drive proposals; validation samples
  decide whether the proposed program survives. This maps directly to COS's
  claim-debt and regression-audit doctrine.
- **Harness abstraction**: the `Agent` wrapper normalizes outputs, costs,
  retries, timeouts, and structured parsing across multiple SDKs.
- **Remote execution**: Docker and Daytona support make long runs practical, but
  they widen the credential and data-flow boundary.

### Bidirectional implementation cross-check

| EvoSkill capability | COS state | Verdict | Action |
|---|---|---|---|
| Failure-driven skill synthesis | COS has skills, skill registry, optimization docs, and Engram; no shipped benchmark loop that auto-writes skills | **EXTERNAL_BETTER** | Extract loop contract and fixture shape |
| Held-out validation frontier | COS has ADR-247 regression audits and manifests, but not program-branch frontier selection | **EXTERNAL_BETTER** | Port as lab/eval primitive, not default git behavior |
| Cross-harness skill packaging | COS has harness projection doctrine and Codex skills; EvoSkill has concrete `.agents/skills` symlink tests | **COMPATIBLE / EXTERNAL_BETTER in fixture detail** | Add future fixture for path projection without adopting `.claude` as canonical |
| Governance, policy, credentials | COS has stronger hook/rule/credential doctrine | **OURS_BETTER** | Keep COS authoritative around any EvoSkill-inspired run |
| Runtime footprint | EvoSkill depends on multiple SDKs, Docker, optional eval packages, remote execution | **RISKY** | No default dependency; opt-in lab only |
| Continuous learning from normal usage | EvoSkill README marks this as open research | **EQUIVALENT / GAP** | Both need a governed usage-to-skill pipeline |

### Integration Plan

- **Use now (pattern-only)**:
  1. Self-improvement stage contract: Base Agent → Proposer → Generator → Evaluator → Frontier.
  2. Held-out validation rule for generated skills.
  3. Feedback ledger schema for discarded proposals and kept improvements.
  4. Harness path projection fixture for `.claude/skills` ↔ `.agents/skills` compatibility.
  5. Branch/tag frontier semantics as a design reference, not as default behavior.
- **Trial later (adapter-lab)**:
  1. A throwaway fixture repo with tiny benchmark data and no secrets.
  2. A COS wrapper that snapshots dirty tree state, restricts generated paths,
     records provenance, and emits a rollback command.
  3. A generated-skill scanner lane using existing skill security and license gates.
- **Do not use**:
  - No default `evoskill` dependency in COS bootstrap, requirements, hooks, or packages.
  - No automatic branch/tag mutation in a user workspace without opt-in and rollback.
  - No remote Daytona/Docker run with project data until a data-flow and credential audit exists.
  - No generated skill promoted to core until it has regression evidence and a manifest row.

### Risks

- **Workspace mutation risk**: program branches, frontier tags, `.claude/program.yaml`,
  generated skills, checkpoints, and feedback files are expected outputs.
- **Credential risk**: Docker launcher forwards provider env-var names into the
  container; remote mode introduces additional Daytona credentials and image flow.
- **Evaluation overfit risk**: benchmark-defined improvements can still overfit
  weak validation sets. COS needs adversarial holdouts before promotion.
- **Path-canonicality risk**: EvoSkill is `.claude`-first; COS must preserve its
  harness-agnostic primitive projection and not let one harness path dominate.
- **Research maturity risk**: benchmark gains are promising but have not been
  reproduced inside COS or on consumer projects.

### Recommended acceptance criteria for any COS trial

```text
ACCEPTANCE CRITERIA:
1. EvoSkill stays radar-only until an external-tool adoption manifest row exists.
2. A lab run happens only in a disposable fixture repo with no production secrets or user data.
3. The wrapper proves dirty-tree detection, generated-path allowlisting, provenance logging, and rollback.
4. Generated skills pass COS skill-contract, security, vocabulary, and regression lanes before promotion.
5. The result records train/validation split, baseline score, candidate score, delta, cost, model, harness, and source commit.
6. No EvoSkill dependency is added to default install, hooks, or runtime packages without a separate ADR.
```

### Source evidence

- GitHub repository: <https://github.com/sentient-agi/EvoSkill>
- arXiv paper: <https://arxiv.org/abs/2603.02766>
- Source commit audited: `418a37ca680a1264086df420a96db07dcd064ace`
- Targeted addendum: `docs/06-Daily/reports/external-tools-radar-evoskill-addendum-2026-05-09.md`
- Adoption doctrine: `docs/04-Concepts/architecture/external-tool-adoption-doctrine.md`
- Adapter taxonomy: `docs/04-Concepts/architecture/external-tool-adapter-taxonomy.md`

### Raw Metrics

<details>
<summary>GitHub API JSON (key fields, captured 2026-05-09)</summary>

```json
{
  "archived": false,
  "created_at": "2026-03-04T20:00:30Z",
  "default_branch": "main",
  "description": "EvoSkill — An open-source framework that automatically discovers and synthesizes reusable agent skills from failed trajectories to improve coding agent performance.",
  "forks": 77,
  "full_name": "sentient-agi/EvoSkill",
  "language": "Python",
  "license": "Apache-2.0",
  "latest_commit": {
    "date": "2026-05-08T18:07:47Z",
    "message": "Merge pull request #38 from sentient-agi/fix/daytona",
    "sha": "418a37ca680a"
  },
  "latest_release": {
    "name": "v1.1.0 — Docker, OfficeQA Example, Bug Fixes & Improvements",
    "tag_name": "v1.1.0",
    "published_at": "2026-05-05T23:49:32Z"
  },
  "open_issues_count": 8,
  "pushed_at": "2026-05-08T18:07:47Z",
  "stars": 710
}
```

</details>

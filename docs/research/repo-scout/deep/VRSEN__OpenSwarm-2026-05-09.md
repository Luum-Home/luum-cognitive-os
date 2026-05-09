---
evaluated_at: 2026-05-09 19:40 UTC
engram_id: pending
deepwiki_url: null
batch: targeted-user-request
parent_radar: docs/reports/external-tools-radar-INDEX.md
introduced_by_commit: 21769813
last_verified_commit: 21769813
source_url: https://github.com/VRSEN/OpenSwarm
---

## Repository Evaluation: VRSEN/OpenSwarm

### Classification: ASSESS / MONITOR
**Score**: 8.3/10 (mechanical), qualitative override to **ASSESS** for runtime adoption.
**Evaluation Level**: 2 (deep — GitHub API metadata + README + targeted source files from a fresh shallow clone).
**Theme**: agents-orchestration-routing  •  **Surface role**: deliverable-specialist swarm / terminal product.

### Summary
OpenSwarm is an MIT-licensed, Agency Swarm-based local terminal swarm for
non-coding deliverables: research, data analysis, documents, slide decks,
images, and videos. It packages an orchestrator plus seven specialists and a
Node/npm wrapper that bootstraps Python dependencies, Playwright, optional
system tools, and a prebuilt AgentSwarm TUI binary.

**Verdict rationale**: valuable as a product-pattern reference for specialist
rosters, file-delivery UX, Composio tool discovery, and terminal onboarding.
Do **not** adopt as a COS runtime. It is a young, broad, media-heavy framework
stack with monkey patches, all-to-all handoffs, provider keys, and optional
external integrations that would bypass COS's governance semantics if imported
wholesale.

### Phase analysis

| Phase | What was checked | Finding | COS decision |
|---|---|---|---|
| 1. Discovery / positioning | README, GitHub metadata, release metadata | "Claude Code for everything except coding"; 1.7k stars, 471 forks, MIT, latest push 2026-05-09, v1.0.0 release 2026-04-22 | Relevant to the external-tool radar as a frontier deliverable swarm, not as a coding-agent harness |
| 2. Runtime anatomy | `swarm.py`, `server.py`, `pyproject.toml`, `package.json` | Python Agency Swarm runtime plus npm launcher; FastAPI server option; 8 agents; Python + Node + Playwright + media/doc deps | Integration footprint is high; treat as lab/reference only |
| 3. Orchestration semantics | `orchestrator/instructions.md`, `shared_instructions.md` | Explicit split: `SendMessage` for parallel independent subtasks, `Handoff` for single-specialist full-context transfer | Harvest wording/policy patterns for COS handoff receipts and task routing docs |
| 4. Tooling / deliverables | specialist agent definitions + shared Composio tools | Strong file-delivery discipline; Docs/Slides/Image/Video/Data agents own artifacts; Composio search/find/execute tools abstract integrations | Good UX patterns, but external actions need COS permission/policy wrappers before use |
| 5. Safety / governance fit | bootstrap, patches, tool topology | Auto-installs dependencies, downloads TUI binary, patches upstream behavior, enables all-to-all handoffs | Keep outside default runtime; any extraction must be pattern-only with explicit acceptance criteria |

### Scoring Breakdown

| Criterion | Weight | Score | Rationale |
|-----------|--------|-------|-----------|
| Relevance | 30% | 8/10 | Strong overlap with specialist-agent orchestration and deliverable workflows; less relevant to COS coding/governance core |
| License | 25% | 10/10 | MIT |
| Activity | 20% | 10/10 | Last push 2026-05-09T01:15:08Z; recent green CI |
| Maturity | 15% | 6/10 | Young repo, single release, 92 commits, broad surface |
| Integration | 10% | 5/10 | Heavy transitive footprint and framework topology; pattern extraction easier than dependency adoption |
| **Weighted Total** | | **8.3/10** | Mechanical score; runtime recommendation remains ASSESS/MONITOR |

### Adoption Signals

| Signal | Value | Descriptor |
|--------|-------|------------|
| Stars / forks | 1,697★ / 471 forks | strong early interest |
| Open issues / PRs | 15 open issues, 6 PRs visible in GitHub UI | active young project |
| Release cadence | one release (`v1.0.0`) | early release maturity |
| CI health | latest 10 workflow runs green | good current signal |
| License | MIT | clean for pattern extraction |

### Key Findings

- **Roster**: Orchestrator, General/Virtual Assistant, Deep Research, Data
  Analyst, Slides, Docs, Image, and Video agents.
- **Routing policy**: Orchestrator is forbidden from doing substantive work;
  it chooses parallel `SendMessage` only when multiple independent specialist
  subtasks exist and uses `Handoff` for single-specialist work.
- **File-delivery discipline**: shared instructions require concrete output
  paths and a `CopyFile` tool for moving deliverables.
- **Integration layer**: Composio tool discovery/execution is wrapped in
  shared tools (`ManageConnections`, `SearchTools`, `FindTools`, `ExecuteTool`).
- **Runtime packaging**: npm package `@vrsen/openswarm` shells into a Python
  project; `run_utils.py` bootstraps `uv`, Python deps, Playwright browsers,
  LibreOffice/Poppler where possible, Node deps, and a prebuilt TUI binary.
- **Trace posture**: `swarm.py` enables OpenAI tracing when `OPENAI_API_KEY`
  exists and disables tracing otherwise.

### Integration Plan

- **What to use now**: pattern-only extraction.
  - Specialist roster and ownership matrix for non-coding deliverable agents.
  - `SendMessage` vs `Handoff` routing rule as a readable policy pattern.
  - Concrete file-output path discipline for artifact-producing skills.
  - Composio-style discover → inspect schema → execute sequence as an adapter UX pattern.
- **What not to use**: no framework dependency, no default npm installer, no
  all-to-all handoff mesh, no direct Composio execution without COS policy
  wrappers, no automatic binary/dependency downloads in core runtime.
- **Effort**: low for documentation/UX pattern extraction; high for any safe
  runtime integration because policy, credentials, audit, and rollback would
  need first-class COS wrappers.
- **Blocking**: COS doctrine says build governance semantics and integrate
  commodity mechanisms behind adapters. OpenSwarm would be an application
  runtime, not a commodity mechanism.

### Risks

- **License compatibility**: permissive MIT — clean.
- **Supply-chain footprint**: large Python + Node + media-generation graph;
  includes Playwright, document conversion, image/video libraries, and external APIs.
- **Bootstrap side effects**: installer can install dependencies, browsers,
  npm packages, and platform binaries; unacceptable as a default COS primitive.
- **Governance bypass**: all-to-all handoffs and direct external-tool execution
  need COS permission, identity, and observability wrappers before adoption.
- **Maturity risk**: fast-moving, recent repo with one release and a broad
  marketing/product surface.
- **Patch risk**: local patches over Agency Swarm indicate useful fixes but
  also tight coupling to upstream internals.

### Cross-References

- Parent index: `docs/reports/external-tools-radar-INDEX.md`
- Targeted addendum: `docs/reports/external-tools-radar-openswarm-addendum-2026-05-09.md`
- Adoption doctrine: `docs/architecture/external-tool-adoption-doctrine.md`
- Adapter taxonomy: `docs/architecture/external-tool-adapter-taxonomy.md`
- Agent orchestration cluster: `docs/research/repo-scout/cluster-agent-orchestration-2026-05-06.md`

### Raw Metrics

<details>
<summary>GitHub API JSON (key fields, captured 2026-05-09)</summary>

```json
{
  "archived": false,
  "created_at": "2026-04-12T00:58:18Z",
  "default_branch": "main",
  "description": "Claude code for everything except coding",
  "forks": 471,
  "full_name": "VRSEN/OpenSwarm",
  "homepage": "",
  "language": "Python",
  "license": "MIT",
  "latest_commit": {
    "date": "2026-05-09T01:15:08Z",
    "message": "Merge pull request #21 from VRSEN/codex/readme-team-agent-swarm",
    "sha": "b74b835095c2"
  },
  "latest_release": {
    "name": "Initial Release",
    "tag_name": "v1.0.0",
    "published_at": "2026-04-22T20:00:03Z"
  },
  "open_issues": 15,
  "pushed_at": "2026-05-09T01:15:08Z",
  "stars": 1697,
  "topics": []
}
```

</details>

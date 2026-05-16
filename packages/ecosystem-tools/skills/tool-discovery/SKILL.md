---
name: tool-discovery
description: Discover new open-source tools that could enhance Cognitive OS capabilities
trigger: discover tools, find new tools, tool scan, what's new in open source, tool
  radar
model: sonnet
audience: os-dev
version: 1.0.0
platforms:
- claude-code
prerequisites: []
routing_intents:
- discover open source tools for this capability
- find new developer tools to evaluate
- scan the ecosystem for useful agent tooling
- research tools that could improve Cognitive OS
- build a tool radar for open source options
triggers:
- tool-discovery
- /tool-discovery
- Tool Discovery
- Discover new open-source tools that could enhance Cognitive OS capabilities
---
<!-- SCOPE: both -->
# Tool Discovery

## Purpose
Scan GitHub and web sources for new open-source tools that could enhance Cognitive OS. Keep the system evolving by discovering patterns, libraries, and frameworks before they're mainstream.

## Protocol

### 1. Define search scope
Cognitive OS cares about these categories:
- **Self-healing / auto-repair**: code repair, auto-fix, self-healing agents
- **Code quality**: linting, testing, coverage, static analysis
- **LLM agents**: agent frameworks, tool use, multi-agent systems
- **Observability**: tracing, logging, metrics, dashboards
- **Developer experience**: CLI tools, automation, workflow engines
- **Security**: vulnerability scanning, secret detection, SAST/DAST

### 2. Search sources

#### GitHub API searches (primary)
For each category, search GitHub:
```
gh api search/repositories -X GET \
  -f q="topic:{topic} language:{lang} pushed:>YYYY-MM-DD stars:>50" \
  -f sort=stars -f order=desc -f per_page=10
```

Topics to search:
- `self-healing`, `auto-repair`, `automated-program-repair`
- `llm-agent`, `ai-agent`, `code-agent`, `coding-assistant`
- `code-quality`, `static-analysis`, `auto-fix`
- `observability`, `tracing`, `apm`
- `developer-tools`, `devex`, `cli-tool`
- `security-scanning`, `sast`, `secret-detection`

Filter: pushed in last 90 days, stars > 50, NOT archived

#### Web searches (secondary)
- "best new open source {category} tools 2026"
- "awesome-{category} github"
- Hacker News, Reddit r/programming, r/devops for recent launches

### 3. Classify each discovery

For each tool found, evaluate:

| Criterion | Weight | How to evaluate |
|-----------|--------|----------------|
| **Relevance** | 30% | Does it fill a gap in Cognitive OS? Map to specific component |
| **License** | 25% | MIT/Apache/BSD = green, GPL = yellow, AGPL/SSPL/BSL/none = red |
| **Activity** | 20% | Last commit < 30d, contributors > 3, issues being resolved |
| **Maturity** | 15% | Version > 1.0, production users, documentation quality |
| **Integration effort** | 10% | CLI-compatible? API? Docker? How hard to integrate? |

Score each 0-10, weighted total > 6.0 = worth investigating.

### 4. Tech Radar Classification

Every discovered tool gets placed in one of 4 rings:

| Ring | Meaning | Score threshold | Action |
|------|---------|----------------|--------|
| **ADOPT** | Proven, integrate now | Score > 8.0 + tested in a project | Add to docker-compose or hooks |
| **TRIAL** | Promising, test in one project | Score 7.0-8.0 | Create integration branch, run pilot |
| **ASSESS** | Interesting, evaluate deeper | Score 5.0-7.0 | Read docs, check API compatibility, check license |
| **HOLD** | Watch but don't act yet | Score < 5.0 OR license concern | Add to watchlist, re-evaluate quarterly |

Plus 4 quadrants (categories):
1. **Platforms & Infrastructure** — Docker services, databases, caches, storage
2. **Agent Frameworks** — Orchestration, multi-agent, memory systems
3. **Code Quality & Repair** — Linting, testing, auto-fix, repair tools
4. **Developer Experience** — UIs, dashboards, CLI tools, monitoring

Every tool gets a ring + quadrant placement.

### 5. Check against existing capabilities

Cross-reference against Cognitive OS agentic primitives:
- Does this replace an existing agentic primitive? (check license improvement)
- Does this fill a known gap? (check `architecture/self-repair-audit` in Engram)
- Does this complement an existing skill? (check skills/ directory)
- Is this already in reference/? (already known)

### 6. Generate report

#### Tool Discovery Report — {date}

**New tools discovered**: N
**Recommended for integration**: M
**License warnings**: K

| Tool | Category | Stars | License | Relevance | Score | Action |
|------|----------|-------|---------|-----------|-------|--------|
| ... | ... | ... | ... | ... | ... | Investigate / Watch / Skip |

#### Tech Radar

| Quadrant | Ring | Tool | Score | Rationale |
|----------|------|------|-------|-----------|
| Platforms | ADOPT | Valkey | 9.2 | BSD-3, drop-in Redis replacement, proven |
| Agent Frameworks | TRIAL | memU | 7.5 | Apache 2.0, proactive memory, needs PostgreSQL |
| Code Quality | ASSESS | Moatless Tools | 6.0 | MIT, ultra-cheap repair, needs evaluation |
| DX | HOLD | Kiro | 3.0 | IDE-only, not CLI-automatable |

#### Top recommendations
For each tool scoring > 7.0:
- **What it does**: 1-2 sentences
- **Why it matters for Cognitive OS**: specific gap it fills
- **Integration approach**: how to integrate (MCP server, CLI tool, library, reference)
- **Effort**: XS/S/M/L
- **License**: confirmed compatible

#### Watchlist
Tools scoring 5.0-7.0 that might become relevant.

### 7. Persist discoveries
- Save to Engram: `mem_save` with topic_key `tool-discovery/{date}` type `discovery`
- Log to `metrics/tool-discovery.jsonl`
- Update `reference/tool-watchlist.md` with current watchlist

## Scheduling
- Run weekly (recommend Monday, pairs with /agent-kpis and /self-improve)
- Can be triggered manually: `/tool-discovery`
- Can focus on a category: `/tool-discovery --category self-healing`

## License compatibility matrix (for reference)
| License | SaaS OK? | Action |
|---------|----------|--------|
| MIT | Yes | Green — integrate freely |
| Apache 2.0 | Yes | Green — integrate freely |
| BSD-2/3 | Yes | Green — integrate freely |
| ISC | Yes | Green — integrate freely |
| MPL 2.0 | Conditional | Yellow — file-level copyleft, OK if not modifying MPL files |
| LGPL | Conditional | Yellow — OK if dynamically linked, not statically |
| GPL-3.0 | Dev-only | Yellow — OK for CI/dev tools, not for runtime |
| AGPL-3.0 | No | Red — requires full source disclosure for SaaS |
| SSPL | No | Red — even broader than AGPL |
| BSL | No (until conversion) | Red — restricts commercial use |
| ELv2 | No (managed service) | Red — prohibits offering as service |
| None | No | Red — all rights reserved by default |

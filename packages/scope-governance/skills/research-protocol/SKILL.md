---
name: research-protocol
description: 'Meta-skill that teaches agents HOW to investigate any source material
  systematically. Covers reading protocols per file type, comparison frameworks, quality
  assessment rubrics, and structured verdicts. Every research task follows DISCOVER,
  ANALYZE, COMPARE, SYNTHESIZE.

  '
version: 1.0.0
user-invocable: true
auto-generated: false
last-updated: 2026-03-27
license: MIT
metadata:
  author: luum
audience: project
summary_line: Meta-skill that teaches agents HOW to investigate any source material…
platforms:
- claude-code
prerequisites: []
routing_patterns:
- pattern: \bresearch[- ]?protocol\b
  confidence: 0.95
- pattern: \bresearch\s+first\s+protocol\b
  confidence: 0.85
triggers:
- research-protocol
- /research-protocol
- Meta-skill that teaches agents HOW to investigate any source material…
---
<!-- SCOPE: both -->
## Purpose

A research methodology framework that ensures consistent, thorough investigation of any source material. This is the META-SKILL: it defines HOW to research. Other skills like `repo-scout` (GitHub repos) and `deep-research` (multi-hop topics) SHOULD follow this protocol internally.

## Invocation

`/research-protocol <source-type> [--source=<url-or-path>] [--compare] [--verdict]`

Where `<source-type>` is one of: `repo`, `docs`, `article`, `paper`, `config`, `mixed`

## What to Do

Every research task MUST follow four phases in order: DISCOVER, ANALYZE, COMPARE, SYNTHESIZE. No phase may be skipped. Each phase gates the next.

### Phase 1: DISCOVER — What Exists?

Map the source material BEFORE reading anything in depth. The goal is a structural inventory, not understanding.

**For any source type:**

1. Identify the source type (repo, documentation site, article, paper, config, mixed)
2. Create a structural map:
   - File/section count
   - Total size (LOC, word count, page count)
   - Component inventory (modules, chapters, endpoints, etc.)
   - Last-modified dates for freshness assessment
3. Identify entry points (README, index, abstract, introduction)
4. Flag scope boundaries: what is IN the source vs. external references

**Discovery output format:**

```
DISCOVERY MAP:
  Source: {url or path}
  Type: {repo|docs|article|paper|config|mixed}
  Size: {LOC or word count}
  Components: {count} ({list of top-level items})
  Entry points: {list}
  Last updated: {date or "unknown"}
  Freshness: {current|recent|aging|stale} (current=<3mo, recent=<6mo, aging=<12mo, stale=>12mo)
```

Do NOT read files in depth during this phase. Scan structure only.

### Phase 2: ANALYZE — What Does It Actually Do?

Read with specific protocols per source type. Each protocol defines WHAT to look for and HOW to assess it.

#### 2A: GitHub Repository Protocol

```
1. README.md Protocol:
   - Claims: What does it SAY it does? List each claim.
   - Evidence: For each claim, is there proof? (tests, demos, benchmarks)
   - "Coming soon": Flag anything promised but not implemented
   - Badges: Separate vanity badges from real ones (CI status, coverage)
   - VS our system: Does Cognitive OS already do this? Better or worse?

2. LICENSE Protocol:
   - Auto-reject check against rules/license-policy.md
   - Dual-license detection (some files may differ)
   - Corporate backing risk (VC-funded single-company = relicense risk)

3. Source Code Protocol:
   - Architecture: Read top-level dirs first. Map the dependency graph.
   - Entry points: Find main.py/index.ts/cmd/. How does it start?
   - Core logic: Read the 3-5 files with most imports. That is where the value is.
   - Dead code: Search for TODO, FIXME, commented-out blocks. How much is unfinished?
   - Test quality: Do not just count tests. Read 3 test files. Do they test behavior or just existence?
   - VS our system: For each core module, do we have an equivalent? Compare line by line.

4. Config/YAML Protocol:
   - What is active vs commented out?
   - What is hardcoded vs configurable?
   - What env vars are required?
   - VS our system: Compare against cognitive-os.yaml structure.

5. CI/CD Protocol:
   - What is automated? (tests, lint, deploy, release)
   - Release cadence (git tags, GitHub releases)
   - Branch strategy (main only? develop? release branches?)

6. Issues/PRs Protocol:
   - Open vs closed ratio (healthy: >50% closed)
   - Response time (healthy: <7 days for first response)
   - Bus factor: How many unique contributors in last 3 months?
   - Stale issues: How many open >6 months with no activity?

7. Dependency Protocol (package.json / go.mod / requirements.txt):
   - Dependency count (bloated? minimal?)
   - Are deps maintained? (check for deprecated/archived deps)
   - Transitive license check (a MIT package depending on AGPL is still AGPL-contaminated)
```

#### 2B: Documentation Site Protocol

```
1. Freshness: When was this last updated? Check copyright year, version numbers.
2. Completeness: Is there a getting-started? API reference? Examples?
3. Accuracy: Do the examples actually work? (test 1-2 if possible)
4. VS our system: Compare their docs/ structure against ours.
```

#### 2C: Article / Blog Post Protocol

```
1. Author credibility: Who wrote this? What is their track record?
2. Claims vs evidence: Separate opinions from data.
3. Date relevance: Is this still accurate? Tech moves fast.
4. Bias detection: Is the author selling something? (product, course, consulting)
```

#### 2D: Academic Paper Protocol

```
1. Methodology: Is it reproducible? Open data?
2. Limitations: Read the limitations section FIRST. Authors hide real issues there.
3. Practical applicability: Can we actually use this or is it theoretical?
4. Citations: Is it well-cited? By whom?
```

#### 2E: Configuration File Protocol

```
1. Schema: Is there a JSON schema or type definition?
2. Defaults: What is the default behavior if nothing is configured?
3. Required vs optional: What MUST be set for the system to work?
4. Secrets: Are credentials inline or referenced from env/vault?
5. VS our system: Compare against cognitive-os.yaml field by field.
```

#### 2F: Mixed Source Protocol

When the source spans multiple types (e.g., a repo with papers and docs):

```
1. Classify each component by type
2. Apply the matching protocol to each component
3. Cross-reference findings between components
4. Note discrepancies (e.g., docs say one thing, code does another)
```

#### Agent Artifact Analysis Protocols

When analyzing AI agent tools, frameworks, or skill libraries, apply these specialized protocols:

**SKILL.md / Command Files Protocol:**
```
1. Frontmatter: Are fields complete? (name, version, description, triggers)
2. Actionability: Does it have concrete STEPS or just "think like X"?
3. Verification: Does it define how to verify success?
4. Specificity: Would Claude already do this without the skill? If yes → low value.
5. Decision trees: Are there if/then flows or just linear instructions?
6. Token cost: How many tokens does this consume vs the value it adds?
7. VS our skills: Does skills/{name}/SKILL.md already cover this?
```

**Hook / Plugin Protocol:**
```
1. Lifecycle event: When does it fire? (pre/post tool use, session start/stop)
2. Blocking vs advisory: Does it block (exit 2) or just warn (exit 0)?
3. Side effects: Does it write files, call APIs, modify state?
4. Registration: Is it wired into the system or dead code?
5. Performance: How much overhead per invocation?
6. VS our hooks: Does hooks/{name}.sh already do this?
```

**Rule / Policy Protocol:**
```
1. Rule vs documentation: Does it ENFORCE behavior or just DESCRIBE it?
2. Size: >60 lines = probably mixing rule with docs
3. Overlap: Check against rules/RULES-COMPACT.md for duplicates
4. Enforcement mechanism: Is there a hook that implements this rule?
5. Phase awareness: Does behavior change by project phase?
6. VS our rules: Does rules/{name}.md already cover this?
```

**Agent Config / Persona Protocol:**
```
1. Generic vs specific: "Think like a security engineer" = generic (SKIP)
2. Decision frameworks: Does it have concrete trade-off matrices? (KEEP)
3. Checklists: Are there verifiable items? (KEEP)
4. Domain knowledge: Does it add knowledge Claude doesn't have? (KEEP)
5. VS our agents: Does agents/{name}.md or customizations/{name}.yaml cover this?
```

**Prompt Template Protocol:**
```
1. Variables: Are there placeholders that make it reusable?
2. Token efficiency: How many tokens vs a simpler prompt?
3. Tested: Is there evidence the prompt works better than default?
4. VS our templates: Does templates/{name}.md already cover this?
```

### Phase 3: COMPARE — How Does It Relate to What We Already Have?

This phase is MANDATORY. Every analysis MUST include a comparison against Cognitive OS capabilities. "No comparison needed" is never valid.

#### Comparison Matrix (required format)

```
| Capability | Source | Cognitive OS | Gap? | Action |
|---|---|---|---|---|
| {feature} | {how they do it} | {how we do it or "N/A"} | {yes/no} | {adopt/adapt/skip/note} |
```

**Rules for the Cognitive OS column:**
- MUST reference specific files: "Covered by rules/trust-score.md" (not "we have something similar")
- "N/A -- gap identified" for missing capabilities (not "we don't have this")
- "Better: our hooks/_lib/common.sh is more robust because..." for superior coverage (not "we're better")
- "Partial: rules/acceptance-criteria.md covers X but not Y" for partial coverage

**Comparison dimensions (check all that apply):**

| Dimension | Question |
|---|---|
| Feature parity | Does the source do something we cannot? |
| Architecture | Is their approach fundamentally different from ours? |
| Quality | Is their implementation more robust, tested, or documented? |
| Integration | Would adopting this require changes to our architecture? |
| Maintenance | Who maintains this? Is the maintenance burden acceptable? |
| Cost | What are the resource costs (tokens, compute, storage)? |
| License | Is the license compatible per rules/license-policy.md? |

### Phase 4: SYNTHESIZE — What Is the Verdict?

Produce structured output with concrete verdicts and action items.

#### Quality Assessment Rubric

For any tool, framework, or methodology being evaluated:

| Dimension | Score 1 | Score 2 | Score 3 | How to Assess |
|---|---|---|---|---|
| Claims-to-evidence ratio | Mostly claims, little proof | Mixed claims and evidence | Fully evidenced with tests/demos | Count claims in README, check each for proof |
| Code-to-docs ratio | More docs than code (vaporware risk) | Unbalanced but functional | Balanced, proportional | Compare LOC of src/ vs docs/ |
| Test quality | Existence tests only ("it imports") | Happy-path tests | Behavioral + edge case tests | Read 3 test files and classify |
| Maintenance signal | Stale (>12mo no activity) | Sporadic (monthly) | Active (weekly commits, responsive issues) | Check last commit, release, issue response |
| Architecture clarity | Spaghetti, no clear layers | Some organization, unclear boundaries | Clear layers, documented architecture | Can you understand the architecture in 5 min? |

**Total score range: 5-15**

| Score | Verdict | Action |
|---|---|---|
| 5-7 | SKIP | Do not invest further time. Document why. |
| 8-12 | ASSESS | Worth deeper investigation. Specific areas to probe identified. |
| 13-15 | TRIAL or ADOPT | Ready for integration testing or direct adoption. |

#### Verdict Categories

For each capability or feature found in the source:

| Verdict | Meaning | Required Detail |
|---|---|---|
| ADOPT | Take this as-is into our system | Integration plan with effort estimate |
| ADAPT | Take the concept, modify for our architecture | What to keep, what to change, why |
| SKIP | Not useful or already covered | Specific reason (redundant, incompatible, low quality) |
| NOTE | Interesting but not actionable now | What conditions would make it actionable |

## Output Format (MANDATORY)

Every research output MUST include all 6 sections. No section may be omitted even if empty (write "None" for empty sections).

```markdown
## Research Protocol Report: {source description}

### 1. Discovery Map
- **Source**: {url or path}
- **Type**: {repo|docs|article|paper|config|mixed}
- **Size**: {metrics}
- **Components**: {count and list}
- **Freshness**: {current|recent|aging|stale}

### 2. Analysis
{Per-protocol findings organized by sub-protocol (README, LICENSE, Source, etc.)}
{Each finding with evidence, not just summaries}

### 3. Comparison Matrix
| Capability | Source | Cognitive OS | Gap? | Action |
|---|---|---|---|---|
{rows with specific file references in Cognitive OS column}

### 4. Quality Score
| Dimension | Score (1-3) | Evidence |
|---|---|---|
| Claims-to-evidence | {N} | {specific evidence} |
| Code-to-docs | {N} | {specific evidence} |
| Test quality | {N} | {specific evidence} |
| Maintenance signal | {N} | {specific evidence} |
| Architecture clarity | {N} | {specific evidence} |
| **Total** | **{N}/15** | |

**Verdict**: {SKIP|ASSESS|TRIAL/ADOPT}

### 5. Verdicts
{Per-capability verdicts with ADOPT/ADAPT/SKIP/NOTE and required detail}

### 6. Action Items
{Concrete next steps if adopting anything}
{Estimated effort per action item}
{Dependencies or prerequisites}
```

## Integration with Other Skills

| Skill | Relationship |
|---|---|
| `repo-scout` | Workflow for GitHub repos. SHOULD follow research-protocol internally for the analysis methodology. |
| `deep-research` | Multi-hop research for non-repo sources. SHOULD follow research-protocol for reading protocols and comparison framework. |
| `recommend-library` | Library selection. Can use research-protocol's quality rubric for deeper evaluation. |
| `tool-discovery` | Tool scanning. Uses research-protocol's comparison matrix to assess against Cognitive OS. |

## Rules

- ALL four phases are mandatory. No phase may be skipped.
- The comparison matrix (Phase 3) MUST reference specific Cognitive OS files, not vague descriptions.
- Quality scores MUST include evidence for each dimension, not just a number.
- "Coming soon" features in a source count as ZERO for scoring purposes.
- If a source has no tests, test quality scores 1 automatically.
- If a source has not been updated in >12 months, maintenance signal scores 1 automatically.
- The output format is non-negotiable. All 6 sections must be present.
- For repos, the LICENSE protocol runs FIRST. If the license is blocked per rules/license-policy.md, stop analysis and return SKIP immediately with the license as the reason.
- Return a structured envelope with: `status`, `executive_summary`, `artifacts`, `next_recommended`, and `risks`

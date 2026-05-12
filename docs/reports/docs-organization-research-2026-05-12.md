# Research Report: Documentation Organization for AI-Native Repositories

## Meta
- **Depth**: deep
- **Confidence**: 82/100
- **Sources consulted**: 28
- **Hop chains executed**: 5 (3–4 hops each)
- **Date**: 2026-05-12

---

## Executive Summary

AI-native documentation in 2026 must serve two equal audiences: human contributors and LLM coding agents (Claude Code, Cursor, Aider, Codex). Research across five threads shows that no single framework dominates — Diátaxis wins for user-facing product docs, vault-numbered schemas win for engineering knowledge bases, and a thin AI-consumability layer (llms.txt + AGENTS.md) is the lowest-friction add-on that yields the largest agent-performance gain. The single most important finding from an ETH Zurich study is that **LLM-generated context files reduce task success rates by ~3% while increasing inference costs 20%** — human-curated, concise instruction files outperform by ~4 percentage points. For this repo's 1,135-file docs tree, the top priority is eliminating the `archive/` vs `archived/` split, capping ADR sprawl (currently 281 ADRs), and publishing a root-level `docs/INDEX.md` that doubles as the `llms.txt` seed.

---

## Key Findings

### Finding 1: "Karpathy-Style Docs" Is a Community Label, Not His Explicit Prescription
**Confidence**: medium (78/100)

Karpathy has never published a formal documentation philosophy document. The "Karpathy style" attributed to him is a community inference from his coding practice:

- nanoGPT README is deliberately minimal — code *is* the documentation ("train.py is a ~300-line readable boilerplate")
- Readability and hackability are explicit design goals: "the script tries to be very readable, hackable and transparent"
- As of April 2026, Karpathy published the **LLM Wiki pattern**: dump raw research into a folder, let an LLM incrementally build and maintain a persistent interlinked markdown wiki. He states: "Humans abandon wikis because the maintenance burden grows faster than the value. LLMs don't get bored, don't forget to update a cross-reference, and can touch 15 files in one pass."
- The LLM Wiki architecture has three layers: raw sources (immutable), the wiki (LLM-generated/maintained markdown pages), and a schema file (the CLAUDE.md that governs the LLM's maintenance behavior)

**Implication for AI-native repos**: the LLM Wiki pattern is a direct template — treat `docs/` as a LLM-maintained wiki, not a human-curated folder tree. The CLAUDE.md/AGENTS.md governs what the LLM updates and how.

**Source**: [Karpathy LLM Wiki, April 2026](https://medium.com/neuralnotions/andrej-karpathy-stopped-using-ai-to-write-code-hes-using-it-to-build-a-second-brain-instead-cddceadc5df5); [nanoGPT README](https://github.com/karpathy/nanoGPT)

---

### Finding 2: Vault-Numbered Schemas (MOC-style) Exist in Engineering Repos but With Important Caveats
**Confidence**: medium (80/100)

The numbered-prefix vault schema (00-MOCs, 01-Build-Log, 02-Decisions, 03-PoCs, 04-Concepts, 05-Methodology, 06-Daily, 08-References) is widely used in personal knowledge management but **rare in shared engineering repos** for three reasons:

1. **Rename cost is extremely high** — renumbering a parent directory propagates broken links across all child references in git-tracked markdown
2. **Link stability suffers** — AI agents that cache or index paths break when the tree shifts
3. **Most GitHub vault templates** (DuskWasHere, BryanHogan, Berteaux) have already dropped numbered prefixes in favor of semantic names by 2024

The MOC (Map of Content) concept is still valuable as a **navigation artifact**, not a directory naming scheme. A `docs/INDEX.md` with explicit category sections achieves the same orientation without the rename penalty.

**Johnny.Decimal** is numerically rigorous: 10 areas, each with up to 10 categories, giving a two-digit code (e.g., `22.04`). It enables memorizable addresses but is brittle in collaborative repos where PR reviewers can't share the mental model.

**PARA** (Projects/Areas/Resources/Archive) maps well to repo structure:
- `docs/projects/` → active work
- `docs/areas/` → ongoing concerns (architecture, security)
- `docs/resources/` → reference material
- `docs/archive/` → completed, read-only

The PARA Archive is **singular** — not `archive/` AND `archived/`.

**Source**: [NotePlan Johnny.Decimal + PARA comparison](https://help.noteplan.co/article/155-how-to-organize-your-notes-and-folders-using-johnny-decimal-and-para); [Dusk Obsidian Vault](https://github.com/DuskWasHere/dusk-obsidian-vault)

---

### Finding 3: Diátaxis Is the Gold Standard for User-Facing Product Docs, Not Engineering Wikis
**Confidence**: high (88/100)

Diátaxis (Daniele Procida, diataxis.fr) organizes all content by user need:
- **Tutorials**: learning-oriented, takes the user by the hand
- **How-to guides**: task-oriented, assumes competence, addresses real-world goals
- **Reference**: information-oriented, technical facts
- **Explanation**: understanding-oriented, context and "why"

The compass model (action↔cognition × study↔work) makes content type determination mechanical.

**Strong adoption evidence (2025-2026)**:
- Canonical (Ubuntu) adopted it across all properties
- Python documentation community voted to adopt it
- LangChain, Cloudflare, StreamingFast implemented it
- Cherryleaf published an implementation guide in December 2025

**Critical limitation for engineering wikis**: Diátaxis was designed for product documentation consumed by end users. It does not handle:
- Build logs / session reports
- ADR logs
- Internal research and proposals
- Operational runbooks that are also AI-agent instructions

**Verdict**: Use Diátaxis for `docs/getting-started/`, `docs/guides/`, `docs/reference/`. Use vault/PARA or a flat semantic structure for the engineering-internal material.

**Source**: [diataxis.fr](https://diataxis.fr/); [Canonical adoption](https://ubuntu.com/blog/diataxis-a-new-foundation-for-canonical-documentation); [Python adoption](https://discuss.python.org/t/adopting-the-diataxis-framework-for-python-documentation/15072); [Sequin blog](https://blog.sequinstream.com/we-fixed-our-documentation-with-the-diataxis-framework/)

---

### Finding 4: AI-Consumability Conventions Are Standardizing Around AGENTS.md + llms.txt
**Confidence**: high (90/100)

**llms.txt (llmstxt.org)**:
- Proposed by Jeremy Howard (Answer.AI) in September 2024
- Plain markdown at `/llms.txt` with an H1, blockquote summary, and H2-sectioned file lists
- Companion: `llms-full.txt` concatenates all linked pages for deep ingestion
- ~10% of websites have it by May 2026; Anthropic, Stripe, Cursor, Cloudflare ship examples
- **Critical finding**: A 300,000-domain study (SERanking, November 2025) found `llms.txt` adds "noise rather than predictive signal" for AI citations in search. Real value is for **IDE agents** (Cursor, Continue, Cline) — not web crawlers
- For a `docs/` tree, the equivalent is a `docs/INDEX.md` or `docs/llms.txt` pointing to subdirectories

**AGENTS.md (now under Linux Foundation / Agentic AI Foundation, donated December 2025)**:
- Hierarchical merging: nested files override parents; user prompts override files
- Discovery: `~/.codex/AGENTS.md` (global) → repo root `AGENTS.md` → subdirectory `AGENTS.md`
- Optimal content: build commands, non-standard tooling, counterintuitive decisions, project constraints
- **Do NOT include**: architectural overviews (agents infer these), standard tooling conventions (already in training data), repo structure maps (become stale and mislead)
- Keep under 150-200 lines before splitting into subdirectory-scoped files

**CLAUDE.md hierarchy**: global `~/.claude/CLAUDE.md` → repo root `CLAUDE.md` → `.claude/CLAUDE.md`

**What LLMs parse well**:
- H2 for major topics, H3 for subtopics (2-level max)
- Short paragraphs (3-5 lines, one idea each)
- Explicit canonical phrasing for technical terms
- Code blocks with language identifiers
- Tables over prose for comparisons
- Each section semantically complete when retrieved in isolation

**What LLMs parse poorly**:
- Deep nesting (H4+, bullet nesting beyond 2 levels)
- Long prose without headers
- Implied connections ("as mentioned above")
- Files exceeding token budgets (split into subdirectory AGENTS.md files)
- JavaScript-rendered content, inline HTML, complex front-matter

**ETH Zurich study finding**: LLM-auto-generated AGENTS.md/CLAUDE.md files reduced task success in 5/8 settings. Human-curated files improved success by ~4 percentage points. Manual curation is worth the overhead.

**Source**: [Codersera llms.txt guide 2026](https://codersera.com/blog/llms-txt-complete-guide-2026/); [0xdevalias AGENTS.md gist](https://gist.github.com/0xdevalias/f40bc5a6f84c4c5ad862e314894b2fa6); [Augment Code AGENTS.md guide](https://www.augmentcode.com/guides/how-to-build-agents-md); [Mintlify AI docs trends](https://www.mintlify.com/blog/ai-documentation-trends-whats-changing-in-2025)

---

### Finding 5: Anti-Patterns — The Most Damaging Are Duplication, ADR Sprawl, and Stale Structural Maps
**Confidence**: medium-high (75/100)

**1. Duplicate archive directories** (`archive/` AND `archived/`): This repo has both, with only 3 items each. This is the canonical "broken window" anti-pattern — contributors don't know which to use, so both accumulate inconsistently. **Fix**: merge into single `docs/archive/`, resolve in one PR.

**2. ADR sprawl beyond ~50-100**: This repo has **281 ADRs**. Known problems at this scale:
- Discovery cost grows linearly — agents context-spending to find relevant ADRs
- Cross-referencing degrades (superseded chains become long)
- Cognitive load prevents humans from reading the ADR log as intended
- Best practice: Never edit accepted ADRs; write a new superseding ADR and link back. Change old status to `Superseded by ADR-NNN`. No hard limit exists in the literature, but teams report pain after ~50-100 active (non-superseded) ADRs. The solution is aggressive supersession + a `docs/adrs/INDEX.md` that lists only active decisions.

**3. Deep nesting (>3 levels)**: LLMs lose orientation. This repo has 34 subdirectories at depth-1 which is acceptable; problems arise if subdirectories nest further.

**4. README-everywhere vs. single-source-of-truth**: Each subdirectory having its own README creates update burden and contradictions. The alternative is a central `docs/INDEX.md` with explicit subdirectory descriptions, and only one root `README.md` at the repo root.

**5. Stale doc detection**:
- Git age: `git log --diff-filter=M --format="%ai %s" -- docs/**/*.md | sort` surfaces files not touched in >6 months
- Inlink count: files with zero inbound wiki-links from other docs are orphan candidates
- Broken links: tools like `markdown-link-check` or `lychee` (Rust) run in CI
- The anti-pattern is treating stale docs as authoritative — agents will quote them confidently

**6. 119 loose .md files at docs root**: This is the most urgent structural problem. Agents and humans scanning the directory see noise. These files should be routed to semantic subdirectories or surfaced only through `docs/INDEX.md`.

**Source**: [ADR GitHub org](https://adr.github.io/); [AWS ADR guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/adr-process.html); [Fern LLM docs](https://buildwithfern.com/post/how-to-write-llm-friendly-documentation)

---

## Analysis

### What We Know (High Confidence)
- AGENTS.md / CLAUDE.md should be concise, human-curated, and scoped by subdirectory when the repo is large
- llms.txt provides value to IDE agents, not web crawlers; the docs equivalent is a well-maintained INDEX.md
- Diátaxis four-quadrant model is the right mental model for *classifying* content, even if folder names don't mirror it
- LLMs parse 2-level heading hierarchies best; H4+ and deep bullet nesting degrades retrieval
- Having `archive/` AND `archived/` is always a mistake — pick one, conventionally `archive/`
- 281 ADRs is above the functional threshold for human or agent navigation without an index

### What We Think (Medium Confidence)
- The Karpathy LLM Wiki pattern (AI-maintained interlinked markdown wiki) will become the dominant internal engineering docs pattern for AI-native teams by 2027
- Johnny.Decimal is the wrong tool for collaborative repos; PARA's semantic names scale better
- A `docs/INDEX.md` file functioning as the repo's llms.txt is more durable than actual `/llms.txt` for code repos (no web hosting required)
- The 119 loose root-level docs files in this repo are the primary barrier to agent navigation

### What We Don't Know (Gaps)
- No authoritative data on optimal ADR count before adopting a consolidation/index strategy
- No research specifically on how deeply nested `docs/reports/` sub-folders affect LLM vector retrieval accuracy
- Limited data on whether front-matter YAML (e.g., `---\ntopic: adr\n---`) materially improves LLM parsing vs. inline headers
- The Karpathy LLM Wiki pattern (April 2026) is very new — no longitudinal data on maintenance quality

---

## Comparison Table

| Dimension | Vault-Numbered (MOC) | Diátaxis | PARA | Johnny.Decimal | Flat + llms.txt |
|-----------|---------------------|----------|------|----------------|-----------------|
| **Structure** | 00-MOC, 01-Build-Log, 02-Decisions, ... | tutorials/, how-to/, reference/, explanation/ | projects/, areas/, resources/, archive/ | NN-AA code system (10×10) | Single flat dir + INDEX/llms.txt |
| **AI-friendliness** | Medium — numbers aid sorting but not semantics | High — types map to query intent | High — semantic categories | Low — agents don't memorize numeric codes | High — single pass, no traversal |
| **Link stability** | Low — renumbering breaks all links | High — semantic names stable | High — semantic names stable | Low — renaming cascades | High — flat = no broken path nesting |
| **Rename cost** | Very high | Low | Low | Very high | None |
| **Human navigation** | Good for personal PKM, poor in teams | Excellent for product docs | Good for project-centric teams | Excellent once memorized | Poor at >200 files without INDEX |
| **Adoption examples** | Obsidian community vaults, personal wikis | Canonical/Ubuntu, Python docs, LangChain | Tiago Forte ecosystem, Notion teams | Personal filesystems, legal/accounting | This repo (partial), Anthropic llms.txt |
| **Best for** | Personal research notes, solo PKM | Product/API documentation | Project-team knowledge | Memorized personal systems | Small repos, AI-first context injection |
| **Worst for** | Collaborative repos (rename pain) | Engineering internals (no place for ADRs, runbooks) | Large repos without clear project boundaries | Teams (no shared mental model) | Large repos without INDEX discipline |

---

## Recommended Schema for This Repo (1,135-file docs/ tree)

### Current State Assessment
- **119 loose .md files at docs root** — primary navigation problem
- **281 ADRs** — well above sustainable navigation threshold without active index
- **34 subdirectories** — acceptable depth, but `archive/` AND `archived/` must merge
- **Reports subdirectory** — healthy pattern, already date-stamped
- **Total 1,135 docs** — large enough that a flat approach is unworkable; structured semantic dirs required

### Recommended Target Structure

```
docs/
├── INDEX.md                  # Master navigation + llms.txt seed (auto-updated)
│
├── 01-getting-started/       # Renamed from getting-started/ (Diátaxis: tutorials)
│   └── ...
├── 02-how-to/                # Renamed from guides/ (Diátaxis: how-to)
│   └── ...
├── 03-reference/             # Consolidates: architecture/, capabilities/, integrations/, usage/
│   ├── architecture/
│   ├── capabilities/
│   └── ...
├── 04-explanation/           # Consolidates: design-philosophy.md, adw-patterns.md, etc.
│   └── ...
│
├── adrs/                     # Keep as-is; add adrs/INDEX.md listing only ACTIVE decisions
│   ├── INDEX.md              # <- NEW: active ADR summary table
│   └── ...
│
├── runbooks/                 # Keep as-is
├── reports/                  # Keep as-is (date-stamped, machine-generated)
├── research/                 # Keep as-is
├── proposals/                # Keep as-is
│
├── archive/                  # MERGED: absorb archived/ contents here (one canonical archive)
│   └── ...
│
├── assets/                   # Keep as-is
└── AGENTS.md                 # docs/-scoped agent instructions (max 150 lines)
```

### Migration Priority Order

**Priority 1 (1 day, no content changes):**
1. Merge `docs/archived/` into `docs/archive/` — update any internal links
2. Create `docs/INDEX.md` with one-line descriptions for every subdirectory and the 119 root-level files (this alone dramatically improves agent orientation)
3. Create `docs/adrs/INDEX.md` with a table of Active/Superseded ADR status

**Priority 2 (1 week, light restructuring):**
4. Move the 119 root-level .md files into appropriate semantic subdirectories (most belong in `03-reference/` or `04-explanation/`)
5. Add `docs/AGENTS.md` with: what docs/ contains, which subdirs agents should read for which tasks, link to adrs/INDEX.md, note on report generation patterns

**Priority 3 (1 month, content-level):**
6. Classify each ADR as Active or Superseded; update superseded ADRs with forward links
7. Adopt Diátaxis naming for the top-4 user-facing subdirs
8. Run `lychee` or `markdown-link-check` in CI for broken link detection
9. Add git-age automation: flag docs not modified in >180 days as stale candidates

### AI-Consumability Layer (add at any time, low effort)

- **`docs/INDEX.md`** serves as internal `llms.txt` — H2 sections per category, markdown links, one-line descriptions
- **`docs/AGENTS.md`** (under 150 lines) — tells coding agents: where to find architecture decisions (adrs/INDEX.md), how reports are named, what the runbooks/ folder is for, build/test commands if not already in root AGENTS.md
- **Heading discipline in all new docs**: H2 for major sections, H3 for subsections, H4 never. Each section self-contained (no "as mentioned above")
- **Canonical phrasing table** in docs/AGENTS.md: define terms agents must use consistently (e.g., "primitive" not "tool", "harness" not "runner")

---

## Hop Chain Log

**Chain 1 — Karpathy (Entity Expansion + Temporal Progression)**
- Hop 1: "What is Karpathy's documentation philosophy?" → nanoGPT: minimal, readable, code-as-docs
- Hop 2: "What has he said about knowledge organization recently?" → LLM Wiki pattern (April 2026): AI-maintained persistent wiki
- Hop 3: "Is 'Karpathy-style docs' a formal prescription?" → No. Community label. His explicit contribution is the LLM Wiki gist, not a docs manifesto

**Chain 2 — Vault/PARA/JD (Conceptual Deepening)**
- Hop 1: "What is PARA and how is it used in repos?" → Projects/Areas/Resources/Archive semantic structure
- Hop 2: "How does Johnny.Decimal compare?" → Numeric 10×10 system, high rename cost, poor team adoption
- Hop 3: "Are numbered prefixes used in real engineering repos?" → Mostly dropped by 2024 in favor of semantic names; MOC value preserved as INDEX.md
- Hop 4: "What does the combined PARA+Zettelkasten vault look like?" → HUB/PARA/ZETA/DAILY/SYSTEM — not directly applicable to code repos

**Chain 3 — Diátaxis (Conceptual Deepening)**
- Hop 1: "What are the four Diátaxis quadrants?" → tutorials/how-to/reference/explanation
- Hop 2: "Who has adopted it and what results?" → Canonical, Python, LangChain, Cloudflare
- Hop 3: "Does it address engineering wiki content (ADRs, runbooks, reports)?" → No. Designed for product docs. Engineering internal content needs supplementary structure.

**Chain 4 — AI-Consumability (Causal Chain)**
- Hop 1: "What is llms.txt?" → Markdown file at domain root, links to key content, H1+blockquote+H2 sections
- Hop 2: "What do AI agents actually do with it?" → IDE agents (Cursor, Continue, Cline) use it; web crawlers largely ignore it
- Hop 3: "What markdown structures do LLMs parse best?" → 2-level headings, short paragraphs, explicit phrasing, code blocks, tables
- Hop 4: "What does the ETH Zurich study say about AI-generated context files?" → They hurt performance; human-curated files +4pp better

**Chain 5 — Anti-Patterns (Causal Chain)**
- Hop 1: "What are known documentation anti-patterns?" → Deep nesting, README-everywhere, stale docs, duplicate archives
- Hop 2: "What is the ADR scaling problem?" → Discoverability breaks after ~50-100 active; no universal limit but INDEX is the fix
- Hop 3: "How do you detect stale docs?" → git log by file age + inlink count + broken-link CI tools (lychee)
- Hop 4: "What is the cost of structural drift (stale AGENTS.md)?" → Agents confidently cite wrong information; structural maps "become liabilities when codebase changes"

---

## Sources

1. [nanoGPT GitHub README](https://github.com/karpathy/nanoGPT) — Karpathy's documentation style: minimal, hackable, readable
2. [Karpathy LLM Wiki / Second Brain pattern (April 2026)](https://medium.com/neuralnotions/andrej-karpathy-stopped-using-ai-to-write-code-hes-using-it-to-build-a-second-brain-instead-cddceadc5df5) — LLM-maintained wiki architecture
3. [Dusk Obsidian Vault (PARA + Zettelkasten)](https://github.com/DuskWasHere/dusk-obsidian-vault) — Combined vault framework, legacy v1 (September 2024)
4. [NotePlan: Johnny.Decimal + PARA](https://help.noteplan.co/article/155-how-to-organize-your-notes-and-folders-using-johnny-decimal-and-para) — System comparison and integration
5. [Diátaxis framework](https://diataxis.fr/) — Four-quadrant documentation system
6. [Canonical Diátaxis adoption](https://ubuntu.com/blog/diataxis-a-new-foundation-for-canonical-documentation) — Enterprise adoption evidence
7. [Python documentation Diátaxis discussion](https://discuss.python.org/t/adopting-the-diataxis-framework-for-python-documentation/15072) — Community adoption vote
8. [Sequin: We fixed our docs with Diátaxis](https://blog.sequinstream.com/we-fixed-our-documentation-with-the-diataxis-framework/) — Practitioner case study
9. [Cherryleaf Diátaxis implementation guide (December 2025)](https://www.cherryleaf.com/2025/12/guide-and-resources-for-implementing-the-diataxis-framework/) — Recent implementation resources
10. [llmstxt.org specification](https://llmstxt.org/) — Official llms.txt format and requirements
11. [Codersera llms.txt guide (May 2026)](https://codersera.com/blog/llms-txt-complete-guide-2026/) — Adoption reality, SERanking study, IDE agent usage
12. [0xdevalias AGENTS.md / AI agent rules gist](https://gist.github.com/0xdevalias/f40bc5a6f84c4c5ad862e314894b2fa6) — Comprehensive cross-tool convention reference
13. [Augment Code: How to build AGENTS.md (2026)](https://www.augmentcode.com/guides/how-to-build-agents-md) — ETH Zurich study findings, anti-patterns
14. [Mintlify: AI documentation trends 2025](https://www.mintlify.com/blog/ai-documentation-trends-whats-changing-in-2025) — Passage-level organization, canonical phrasing
15. [Fern: Write LLM-friendly docs (March 2026)](https://buildwithfern.com/post/how-to-write-llm-friendly-documentation) — Heading hierarchy, self-contained sections
16. [DEPLOYHQ: CLAUDE.md, AGENTS.md, Copilot instructions guide](https://www.deployhq.com/blog/ai-coding-config-files-guide) — Cross-tool AI context file comparison
17. [HumanLayer: Writing a good CLAUDE.md](https://www.humanlayer.dev/blog/writing-a-good-claude-md) — Conciseness principle, token budget advice
18. [ADR GitHub organization](https://adr.github.io/) — Official ADR resources and tooling
19. [AWS ADR guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/adr-process.html) — ADR lifecycle management
20. [Martin Fowler: Architecture Decision Record](https://martinfowler.com/bliki/ArchitectureDecisionRecord.html) — Immutability principle
21. [IcePanel ADR article](https://icepanel.io/blog/2023-03-29-architecture-decision-records-adrs) — Scaling challenges
22. [I'd Rather Be Writing: What is Diátaxis?](https://idratherbewriting.com/blog/what-is-diataxis-documentation-framework) — Comparison with DITA, Information Mapping
23. [Mintlify: What is llms.txt?](https://www.mintlify.com/blog/what-is-llms-txt) — Skepticism analysis
24. [Cloudflare: Markdown for Agents](https://developers.cloudflare.com/fundamentals/reference/markdown-for-agents/) — Structured markdown guidance
25. [Johnny.Decimal system](https://johnnydecimal.com/) — Numeric file organization specification
26. [Bryan Hogan Obsidian vault template](https://github.com/BryanHogan/obsidian-vault-template) — Numbered prefix deprecation evidence
27. [Karpathy 2025 LLM Year in Review](https://karpathy.bearblog.dev/year-in-review-2025/) — Recent Karpathy philosophy signals
28. [Second Brain Builder (LLM Wiki pattern)](https://github.com/NicholasSpisak/second-brain) — Community implementation of Karpathy's pattern

---

## Recommendations

1. **Immediate: Create `docs/INDEX.md` as a human-curated navigation hub** — This single file, functioning as the repo's internal llms.txt, will improve agent orientation more than any structural reorganization. Include one-line descriptions of every subdirectory and categorize the 119 loose root files. Keep under 500 lines. Update on every major docs addition.

2. **Immediate: Merge `docs/archived/` into `docs/archive/`** — The dual-archive is the clearest broken-window anti-pattern in this repo. Three items in each; consolidation takes <30 minutes and prevents future confusion.

3. **Short-term: Create `docs/adrs/INDEX.md` with Active/Superseded status table** — At 281 ADRs, the collection is past the human-navigable threshold. An index listing only non-superseded decisions (with links) restores navigability for both humans and agents. Mark superseded ADRs with forward links in their header. Aim to surface <80 "live" decisions.

4. **Short-term: Add `docs/AGENTS.md` (150 lines max)** — Tells coding agents: which subdirectory to read for each task type, how reports are named, what runbooks/ contains, the canonical term list. Human-curated only — do not auto-generate.

5. **Medium-term: Route 119 loose root docs into semantic subdirectories** — Use the Diátaxis quadrants as a classification guide: session-handoffs → `reports/`, capability docs → `reference/`, design philosophy → `explanation/`, HOW-TO-USE-COS.md → `getting-started/`.

6. **Ongoing: Enforce heading discipline in new docs** — H2 for major sections, H3 for subsections, no H4+. Each section self-contained. No "as mentioned above" — state the reference explicitly.

7. **CI: Add markdown-link-check or lychee for broken link detection** — Stale structural maps that agents treat as authoritative are the most insidious anti-pattern. Broken links are a reliable proxy for stale content.

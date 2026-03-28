# WISC Framework Analysis — Impact on Cognitive OS

> WISC (Write, Isolate, Select, Compress) by Cole Medin. 2000+ hours of production coding.
> Analysis date: 2026-03-28

## Sources (All Verified)

- [Cole Medin's WISC Framework (GitHub)](https://github.com/coleam00/context-engineering-intro/tree/main/use-cases/ai-coding-wisc-framework)
- [Chroma Research: Context Rot (July 2025)](https://www.trychroma.com/research/context-rot)
- [Anthropic: Multi-Agent Research System (June 2025)](https://www.anthropic.com/engineering/multi-agent-research-system)
- [arxiv 2507.11538: How Many Instructions Can LLMs Follow at Once? (July 2025)](https://arxiv.org/abs/2507.11538)
- [arxiv 2602.11988: Evaluating AGENTS.md (Feb 2026)](https://arxiv.org/abs/2602.11988)
- [Martin Fowler: Knowledge Priming](https://martinfowler.com/articles/reduce-friction-ai/knowledge-priming.html)
- [HumanLayer: Writing a good CLAUDE.md](https://www.humanlayer.dev/blog/writing-a-good-claude-md)

## The 90.2% Claim — VERIFIED

Source: Anthropic's engineering blog. Multi-agent system (Opus 4 lead + Sonnet 4 sub-agents) outperformed single-agent Opus 4 by 90.2% on research eval. Key findings:
- Token usage explains 80% of performance variance
- 3-5 sub-agents in parallel, each with clean context
- Multi-agent uses ~15x more tokens but distributes across separate windows
- **Caveat**: This is breadth-first research. For depth-first coding, improvement would be smaller.

## WISC vs Cognitive OS — Component Analysis

### W — Write (Externalize Memory)

| What WISC Says | COS Implementation | Gap? |
|---|---|---|
| Project rules in CLAUDE.md | ✅ CLAUDE.md + cognitive-os.yaml | No |
| Spec files before tasks | ✅ SDD pipeline artifacts | No |
| Progress journals (HANDOFF.md) | ✅ mem_session_summary | Minor — no auto-read on fresh session |
| Enriched commits (WHY + context) | ❌ Standard commits | Yes |
| "3 times = file" heuristic | ❌ Not formalized | Yes |

**Evidence**: Martin Fowler's knowledge priming — priming docs have highest priority in the 3-layer hierarchy (Training < Conversation < Priming).

### I — Isolate (Sub-agent Delegation)

| What WISC Says | COS Implementation | Gap? |
|---|---|---|
| Sub-agents with clean context | ✅ Agent tool + orchestrator | No |
| Scout Pattern (explore → summarize → GC) | ❌ Not explicit | Yes |
| ">5 files = delegate" rule | ❌ Uses complexity, not file count | Minor |
| Structured exploration summary | ❌ Free-form agent output | Yes |

**Evidence**: Anthropic's 90.2% improvement validates multi-agent. Token distribution across separate context windows is the mechanism.

**Scout Pattern** (what we're missing):
1. Sub-agent reads file headers/TOC/exports first
2. Assesses relevance in short summary
3. Only loads full content for relevant files
4. Returns 2-paragraph synthesis to main agent
5. Sub-agent context is garbage collected

### S — Select (Context Pyramid) ← BIGGEST GAP

| What WISC Says | COS Implementation | Gap? |
|---|---|---|
| CLAUDE.md under 500 lines (HumanLayer says <300, ideally <60) | ❌ Our rules load 1000+ lines | **CRITICAL** |
| Path-triggered rules (`paths:` frontmatter) | ❌ Keyword triggers only | Yes |
| On-demand heavy references | ✅ L2/L3 progressive loading | Partial |
| Prime commands for focused exploration | ❌ No `/prime-*` commands | Yes |
| LLMs follow ~150 instructions reliably | ❌ We load far more | **CRITICAL** |

**Evidence (3 converging studies)**:

1. **arxiv 2507.11538** — 20 LLMs tested: frontier models maintain near-perfect instruction-following through ~150-200 instructions, then decay linearly. At 500 instructions, best models achieve only 68% accuracy.

2. **Chroma Context Rot** — 18 models tested: ALL degrade as input length increases. Models perform BETTER on shuffled haystacks than logically coherent documents. 200K-token model shows significant degradation at 50K tokens.

3. **arxiv 2602.11988** (ETH Zurich) — Context files REDUCE task success rates compared to no context, and increase inference cost by >20%.

**Implication for COS**: Our approach of symlinking 55+ rule files into `.claude/rules/` means every session starts with far more than 150 instructions. This is actively degrading agent performance per all three studies.

### C — Compress (Context Pruning)

| What WISC Says | COS Implementation | Gap? |
|---|---|---|
| Compact at FIRST repetition sign | ⚠️ 50% threshold is informational only | Yes — we wait too long |
| Summary → fresh session | ✅ mem_session_summary | Partial — no auto-restart |
| Targeted pruning (drop resolved errors, old files) | ❌ No selective pruning | Yes |
| Late compaction = confused summary | ❌ Not addressed | Yes |

## Priority Actions

### P0 — CRITICAL: Reduce Instruction Load

The research is clear: >150 instructions degrades performance. Actions:
1. Cut `.claude/rules/cos/` symlinks to ONLY the most critical rules
2. Move everything else to contextual loading (on-demand, not always)
3. Target: <300 lines of always-loaded instructions
4. RULES-COMPACT.md index (~1500 tokens) is OK, but full rule files are not

### P1 — Implement Scout Pattern

Formalize sub-agent exploration protocol:
1. Scout reads headers/signatures first, not full files
2. Assesses relevance in 2-3 sentences
3. Only loads full content for relevant files
4. Returns structured summary to orchestrator
5. Context is garbage collected after return

### P2 — Path-Triggered Rules

Add `paths:` frontmatter to rule files for auto-loading by file pattern:
```yaml
---
paths: ["*.go", "internal/**"]
---
```
When editing Go files, Go rules auto-load. When not editing Go, they don't.

### P3 — Earlier Compression Triggers

Add repetition detection to compression triggers. First repetition = compress, not third. If the model repeats an error or re-reads a file it already read, trigger compression immediately.

### P4 — Enriched Commits

Add WHY-focused commit messages with context sections tracking rules/conventions applied.

## Summary

COS already implements ~70% of WISC without knowing it. The critical gap is in **Select** — we load too much context, which the research shows actively hurts performance. The fix is straightforward: drastically reduce always-loaded rules and move to path-triggered contextual loading. This is the highest-ROI improvement we can make.

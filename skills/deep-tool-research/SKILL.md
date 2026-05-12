<!-- SCOPE: both -->
---
name: deep-tool-research
description: Use when an external tool has passed the shallow `repo-scout` gate and needs a canonical 7-annex deep evaluation before an adoption decision (`ASSESS`, `TRIAL`, `REJECT`); produces parent comparison doc plus fixed-axis annexes A-G for mechanical cross-tool comparison.
scope: both
audience: os-dev
status: skeleton
model_hint: opus
routing_patterns:
  - pattern: '\bdeep[- ]tool[- ]research\b'
    confidence: 0.95
  - pattern: '\bexternal tool (evaluation|research|adoption)\b'
    confidence: 0.85
dependencies:
  - skills/repo-scout/SKILL.md
  - skills/repo-forensics/SKILL.md
  - rules/license-policy.md
  - rules/recommendation-grounding.md
inspired_by:
  - docs/research/holaos-comparison-2026-05-10.md
diverges_from:
  - docs/research/helixdb-comparison-2026-05-11.md
  - docs/research/ifixai-comparison-2026-05-11.md
  - docs/research/megamemory-comparison-2026-05-11.md
---

# `/deep-tool-research <tool>` — Canonical Deep Evaluation Pipeline

> Skeleton only. Implementation lands in a follow-up SDD change. Do not register in any manifest until the operator approves the taxonomy.

## 1. Why this skill exists

The holaOS deep evaluation locked a 7-axis taxonomy (A–G) and produced cross-comparable annexes. The 2026-05-11 batch (HelixDB / iFixAi / MegaMemory) drifted to ad-hoc per-tool axes (storage+compiler / taxonomy / concept-graph), which makes a 3-tool comparison matrix mechanically impossible without re-coding every annex. This skill fixes the taxonomy at the orchestrator boundary so all future deep evaluations are slot-compatible.

## 2. Fixed annex taxonomy (LOCKED — do not extend per tool)

| Annex | Domain | Required content | Default model |
|---|---|---|---|
| **A — Memory & State** | How the tool models persistent state, recall, indexing, lifecycle. NO_COMPARABLE if not applicable, but the slot is still filled. | Schema/data model, recall pipeline, embedding/index strategy, lifecycle (TTL/GC/compaction), cross-session boundary, comparison vs COS Engram. | Opus |
| **B — Cost & Budget** | Token/replay/compute budgets, throttles, rate limits, ledgers. | Budget primitives, replay caps, context reserve, observability hooks, comparison vs `lib/budget_calculator.py`, `cognitive-os.yaml` cost section. | Opus |
| **C — Evolution & Self-Improvement** | Skill review, post-run jobs, queue, evolve loop, self-modifying behavior. | Trigger surface, confidence model, queue/lease semantics, promotion gate, comparison vs `skills/self-improve`, `analyze-improvements`, `apply-improvements`. | Opus |
| **D — Security & Plan** | Auth surface, grants, signing, capability boundary, compiled plan, secrets. | Grant model (HMAC/OAuth/etc.), capability projection, plan compilation, comparison vs `cosd`, `[credential-management]`, `[grant-signing]`. | Opus |
| **E — Architecture & Risks** | System shape, fricciones de adopción, bus factor, stack mismatch. | Component map, top patrons (≤6), 5+ friction points, license × policy crosswalk, top 3 risks. | Opus |
| **F — Compliance & Clean-Room** | License posture, reuse boundary, attribution, audit trail for derived code. | License grade per `[license-policy]`, adoption matrix (vendor / port / pattern / clean-room), commit-msg template, pre-commit gate sketch. | Sonnet |
| **G — Surprise Findings** | Cross-cutting wins that don't fit A–E. | Bounded to ≤3 findings. If empty, write "NONE — no cross-cutting surprises found" — DO NOT omit the annex. | Sonnet |

**Forbidden**: renaming an annex per tool. If a tool's "natural" axis is "storage+compiler", that content goes into **A (Memory & State)**, with a note in §1.2 of the parent that A is wider than usual for this tool. The slot identity is load-bearing for cross-tool comparison.

## 3. Pipeline shape

```
shallow gate (repo-scout / repo-forensics)
   │
   ▼
parent comparison doc (§1 executive summary, §2 license, §3 inventory, §4 top-10, §5 patterns, §6 gaps, §7 risks, §8 next steps, §9 annex map)
   │
   ├─ launch Opus  → Annex A
   ├─ launch Opus  → Annex B
   ├─ launch Opus  → Annex C
   ├─ launch Opus  → Annex D
   ├─ launch Opus  → Annex E
   ├─ launch Sonnet → Annex F
   └─ launch Sonnet → Annex G
   │
   ▼
synthesis section in parent §10 (cross-annex insights, P0/P1/P2 with operational-signal citations per rules/recommendation-grounding.md)
   │
   ▼
mem_save (topic_key: research/<tool>/parent, type: pattern, scope: project)
mem_save per annex (topic_key: research/<tool>/annex-<a..g>, type: pattern, scope: project)
```

## 4. Prerequisites

- Source cache present at `.cognitive-os/external-source-cache/<tool>/` (shallow clone, license-scanned).
- Shallow `repo-scout` deep-dive landed at `docs/research/repo-scout/deep/<owner>__<repo>-<date>.md`.
- Radar addendum landed at `docs/reports/external-tools-radar-<tool>-addendum-<date>.md` (carries the initial verdict that motivates the deep pass).
- License grade resolved per `rules/license-policy.md`. If BLOCK, Annex F drives the clean-room protocol; if ALLOW, Annex F still required (records attribution path).

## 5. Engram topic keys

| Topic key | Type | Scope | Written by |
|---|---|---|---|
| `research/<tool>/parent` | pattern | project | orchestrator (synthesis) |
| `research/<tool>/annex-a` | pattern | project | sub-agent (A) |
| `research/<tool>/annex-b` | pattern | project | sub-agent (B) |
| `research/<tool>/annex-c` | pattern | project | sub-agent (C) |
| `research/<tool>/annex-d` | pattern | project | sub-agent (D) |
| `research/<tool>/annex-e` | pattern | project | sub-agent (E) |
| `research/<tool>/annex-f` | pattern | project | sub-agent (F) |
| `research/<tool>/annex-g` | pattern | project | sub-agent (G) |
| `decision/<tool>-adoption` | decision | project | orchestrator (post-synthesis) |

## 6. File naming contract

- Parent: `docs/research/<tool>-comparison-<date>.md`
- Annexes: `docs/research/<tool>-annex-<letter>-<short-slug>-<date>.md` where `<letter>` is one of `a,b,c,d,e,f,g` and `<short-slug>` is descriptive (e.g. `memory`, `cost-budget`).

The letter slot is canonical. The short slug is local color.

## 7. Acceptance criteria

A `/deep-tool-research` invocation passes acceptance iff:

1. **Slot completeness** — 7 annex files exist with letters A–G, no gaps, no extra letters. Verified by `ls docs/research/<tool>-annex-*-<date>.md | wc -l == 7`.
2. **Slot fidelity** — each annex frontmatter declares `axis: <A|B|C|D|E|F|G>` matching one of the locked names in §2. Verified by yq/grep.
3. **Parent §9 annex map** — references all 7 letters with file links. Verified by grep on the parent doc.
4. **Engram persistence** — 9 topic keys present per §5. Verified by `mem_search` count.
5. **License posture stated** — Annex F frontmatter has `license_grade: <ALLOW|BLOCK|HOLD>` matching `rules/license-policy.md`.
6. **Recommendation grounding** — every priority claim (P0/P1/P2) in parent §10 cites at least one operational signal per `rules/recommendation-grounding.md` (sessions, dogfood-score, sprint state, master-pending, plans). Solo opinion is rejected.
7. **No ad-hoc axes** — there is no annex whose axis declaration is outside §2's seven names. CI/lint check on the frontmatter.

## 8. When NOT to invoke

Skip `/deep-tool-research` and stay in shallow `repo-scout` / radar-addendum lane when:

- Tool is verdict `REJECT` after the shallow pass (no deep value extraction needed).
- Tool family has 3+ prior deep evaluations and the new entry is conceptually identical (use the existing taxonomy as comparison anchor instead of producing a full 7-annex set; document this choice in the radar addendum).
- Budget < ~5K tokens available for the session (deep pass is ~40–80K tokens orchestrator-side + 7x sub-agent budgets).

## 9. Decision rule (1 line)

> Invoke `/deep-tool-research` when an external tool has a **non-REJECT** verdict AND we will likely **extract patterns or vendor code** from it; otherwise stay in the Phase-4 light radar-addendum pattern.

## 10. Open implementation questions

- How to enforce the slot-letter contract pre-commit (`hooks/deep-research-axis-gate.sh`?).
- Whether Annex G should be allowed to land empty-with-statement (current default: yes, "NONE" is acceptable content; reasoning: forcing surprises invents them).
- How to retroactively re-shape the 2026-05-11 HelixDB/iFixAi/MegaMemory annex sets without a full re-run (proposal: 1-page slot-mapping appendix per tool, NOT a rewrite).

## 11. Out of scope

- Implementation code (this is a skeleton).
- The clean-room protocol body (see `holaos-annex-f-compliance-cleanroom.md` as the canonical template that Annex F should converge toward).
- Registry/manifest integration (operator decision; see CLAUDE.md task footer).

<!-- SCOPE: both -->

# Research-Only Agent Template

> Paste this section into any research-phase agent prompt (Phase 0 of the
> research-first protocol). Replace `{{topic}}` and `{{date}}` with actual values.

---

## Hard Constraints (MANDATORY — read before doing anything)

- **READ-ONLY task.** No code changes. No commits. No edits outside
  `docs/reports/`.
- The ONLY file you may create or modify is the research report:
  `docs/reports/{{topic}}-{{date}}.md`
- Do NOT implement, fix, refactor, or delete anything. If you discover something
  that needs fixing, note it in the report under "Decision Points" or
  "Open Questions" — do not act on it.
- Do NOT commit. The orchestrator will commit the report after operator triage.
- If you are tempted to make "just a small fix while you're here" — STOP. That
  is scope creep. Add it to Open Questions instead.

---

## Your Goal

Produce a structured research report at:

```
docs/reports/{{topic}}-{{date}}.md
```

The report arms the human operator with enough context to make decisions. It does
NOT implement anything. The human reads it, answers open questions, and then a
separate implementation agent picks it up.

---

## Required Output Structure

Your report MUST contain these sections in order (H2 headings):

### 1. TL;DR
Two to four sentences. What is the problem space, what did you find, what is the
single most important takeaway? Write this last but place it first.

### 2. Inventory
A concrete enumeration of what exists today. Files, modules, configs, endpoints —
whatever is relevant. Use a table or bullet list with file paths. No analysis here,
just facts with evidence (grep counts, file listings, version strings).

### 3. Decision Points
A table with columns: `Decision`, `Options`, `Tradeoffs`, `Recommended`.
One row per decision the operator must make before implementation can begin.
Limit to the decisions that genuinely block implementation — not nice-to-haves.

### 4. Risk Assessment
A table with columns: `Risk`, `Likelihood`, `Impact`, `Mitigation`.
Cover blast radius (files/services affected), reversibility (can we roll back?),
and dependency risks (what breaks if we get it wrong?).

### 5. Recommended Path
Your concrete recommendation. Which option from Decision Points do you prefer and
why? Include the implementation order if sequencing matters.
This is your opinion — say so. The operator may override it.

### 6. Open Questions
Numbered list. Questions the agent cannot answer from the repo alone. The operator
will fill these in during Phase 1 (triage). Keep it short: 3-7 questions maximum.
If you have more, prioritize ruthlessly — unanswered questions block implementation.

### 7. What This Report Does NOT Do
Bullet list. Explicitly state what was OUT OF SCOPE for this research. Prevents
the next agent from thinking the work is done when it isn't.

---

## Engram Persistence

Before finishing, save your key findings to Engram:

```
mem_save(
  title: "Research: {{topic}} — findings",
  topic_key: "research/{{topic}}",
  type: "architecture",
  scope: "project",
  content: "<executive summary + decision point keys + recommended path>"
)
```

Topic key convention: `research/<topic>` (slug form, hyphens, no spaces).

---

## Trust Report Requirements

End your response with a Trust Report in the standard format:

```
TRUST_REPORT: SCORE=<0-100> STATUS=<HIGH|MEDIUM|LOW|CRITICAL> EVIDENCE=<N> UNCERTAINTIES=<N>
---
WHAT I VERIFIED: <bullets — grep outputs, file reads, version checks>
UNSURE ABOUT: <at least 1 item — "100% confident" is a red flag>
HUMAN SHOULD CHECK: <bullets — map directly to Open Questions>
```

Score guidance for research reports:
- Evidence (40%): all inventory claims backed by grep/file reads
- Criteria (30%): all Decision Points have at least 2 options with tradeoffs
- Self-awareness (20%): Open Questions section is honest and non-trivial
- Proportionality (10%): report length matches complexity (not a 10-line report
  for a 50-file migration, not a 400-line report for a 3-file change)

---

## Length Cap

Target 200-350 lines. If your inventory is large, summarize and link (file paths
suffice — do not paste full file contents). Reviewers skim; make every line earn
its place.

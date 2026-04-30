# Lessons Learned — OS Health Retrospective

**Purpose:** Institutional memory of the pain points, anti-patterns, and red flags that emerged while building the Cognitive OS. This document exists so we don't repeat these mistakes as the project grows.

**Why this matters:** Technical ADRs document *what* we decided. This document captures the *malestar* — the uncomfortable truths, the false confidence, the silent degradation. If ADRs are the skeleton, this is the nervous system.

**Last major retrospective:** 2026-04-15 / 2026-04-16 (comprehensive stabilization sessions)

---

## THE FIVE WOUNDS

### Wound 1: Speed Without Review

**What happened:** v0.1.0 generated 60+ hooks, 80+ skills, 30+ libs in ONE commit. Nobody reviewed performance. The worst hook (`rate-limit-protection.sh`) had O(n) Python subprocess spawning from day one — never caught because nobody measured. It was silently adding 30-90 seconds per agent call for months.

**Why it hurt:** "Tests pass, ship it" is not enough when you're shipping 60+ agentic primitives. Each one can have invisible degradation.

**How we know we're repeating it:** When a session produces >20 new agentic primitives without benchmarking. When commits are `feat: X + Y + Z` instead of single-concern.

**Prevention:**
- Hook benchmark in pre-commit (measures latency of modified hooks)
- Pattern detector: flags >2x duration regression per validator
- Commit discipline: one concern per commit

---

### Wound 2: Aspirational Metadata

**What happened:** Field `audience:` added to 120 SKILL.md files in March 2026. A follow-up was needed ("PENDING: skills need audience-aware logic — engram #1771") but the follow-up never happened. The `audience:` field was **just metadata that nobody read** for 18+ days until we discovered it this session.

**The pattern:** Design a schema → add fields to N files → write tests that verify "field exists" → declare victory → forget to write the code that *reads* the field.

**Scale of the damage:** 353 aspirational agentic primitives discovered in the audit:
- 84 hook SCOPE tags never read
- 95 lib scope tags never read
- 5 of 6 SKILL.md frontmatter fields never consumed
- 8 of 10 hook config flags dead
- 18 entire config sections dead

**How we know we're repeating it:** When someone adds a field/flag/tag "for future use." When tests check existence but not behavior. When commits say "mark all X with Y" without code changes that *use* Y.

**Prevention:**
- Pattern detector: `detect_dead_metadata` — grep for field readers after adding a field
- Rule: "No metadata without consumer" — don't merge a field addition without the code that reads it
- Architecture principle: schema changes require bidirectional implementation

---

### Wound 3: False Coverage

**What happened:** 342 test files felt reassuring ("99.9% passing!") but 67 were purely structural — only checking `path.exists()`, markdown section headers, or frontmatter fields. You could break the core logic of rate-limiter.py and all 342 tests would pass.

**The trap:** Test *count* is a lousy metric. Test *kill rate* (mutation testing) is the real signal. Mutation testing on rate_limiter.py showed only 34% kill rate — 66% of mutations to the code pass undetected.

**How we know we're repeating it:** When a test file only has `assert path.exists()` or `assert "word" in content`. When test names contain "_exists" or "_has_section". When test categories are named "behavior" but don't actually invoke behavior.

**Prevention:**
- CI gate with mutation score threshold (cosmic-ray in `.github/workflows/test-quality.yml`)
- Pre-commit blocker for structural-only tests (`scripts/check_test_quality.py`)
- Rule: tests must execute code (subprocess, import, function call) — file existence is not enough

---

### Wound 4: Agent Amnesia

**What happened:** Sub-agents start with zero project context. They don't read CLAUDE.md. They don't read memory files. They improvise audit methods and make the same mistake repeatedly. In ONE session:
- Audit #1 reported "20 ghost hooks" (false — all were symlinks)
- Audit #2 reported "13 missing libs" (false — 11 existed, symlinks not resolved)
- Audit #3 reported "69 phantom skills" (false — only 3 were real phantoms)

The same mistake, three times, by three different sub-agents, because none of them knew "this project uses symlinks."

**Why it hurt:** Each wrong audit costs hours of analysis based on inflated numbers. The 97-second overhead estimate was 2.7x inflated. The 13 missing libs were 6.5x inflated. Real work delayed while we debugged phantom problems.

**How we know we're repeating it:** When two consecutive agents report conflicting numbers about the same thing. When an agent "discovers" something we already documented. When commits to memory files don't actually help future sessions.

**Prevention:**
- `subagent-context-injector.sh` injects `templates/agent-mandatory-rules.md` into every sub-agent
- `hooks/_lib/file_checker.sh` provides symlink-aware existence checks
- `/audit-integrity` skill standardizes audit method
- Rule: every sub-agent prompt that touches the filesystem MUST include the symlink preamble

---

### Wound 5: Stateless Decisions

**What happened:** 252 commits in 18 days. Zero ADRs during that time. When we went back to reconstruct "why did we do X?" we had to mine engram + git blame + guess. Context was lost permanently for many decisions.

**The pattern:** Velocity over documentation. "I'll document it later." Later never comes.

**How we know we're repeating it:** When a commit makes an architectural choice without an ADR. When a feature is added that changes behavior without a design doc. When "we talked about this" but there's no record.

**Prevention:**
- `hooks/adr-detector.sh` — PostToolUse hook on `git commit` that detects architectural changes and auto-generates ADR drafts
- Pattern: 8 weighted signals (dependency change, config schema, hooks, license, large deletion, integration, structure, breaking change)
- Threshold: score >= 0.70 generates ADR draft
- Rate limit: 3 ADR drafts per session (prevents spam)
- Drafts require human review — AI detects, human decides

---

## THE META-WOUND

The five wounds share a common root: **silent degradation**. Every one of them degraded invisibly for weeks before being detected. The filesystem looked healthy. The tests passed. The commits kept flowing. But underneath, the project was accumulating debt at a rate faster than capacity to repay.

**The meta-prevention** is *measurable self-awareness*:
- Pattern detector runs at session start — surfaces recurring problems
- Mutation testing runs in CI — measures real test quality
- Hook benchmarks run in pre-commit — catches performance regression
- Auto-ADR runs on every git commit — prevents decision loss
- Mandatory rules injected in every sub-agent — prevents repeat errors

None of these existed before the April 2026 stabilization sessions. All of them exist now. **The OS can detect its own degradation patterns.** That's the single biggest change from where we started.

---

## RED FLAGS TO WATCH FOR

Warning signs that we're regressing to pre-stabilization habits:

- [ ] More than 10 agentic primitives added in a single commit
- [ ] A field/flag added without a PR showing the code that reads it
- [ ] A test name containing "_exists", "_has_section", "_is_valid_yaml" (without behavior)
- [ ] An agent report whose numbers conflict with a previous audit
- [ ] An architectural change without a corresponding ADR draft
- [ ] A hook added without benchmark in pre-commit
- [ ] >50ms mean increase in validator duration without explanation
- [ ] Mutation score dropping below 40% on any lib file
- [ ] A commit message containing "TODO: wire up later" (likely to be forgotten)
- [ ] A skill/hook/lib with >3 days since last verified-working state

If any of these appear, STOP and investigate before continuing.

---

## PRINCIPLES

Derived from these wounds. Apply before adding new code:

1. **No metadata without consumer** — don't add a field unless code reads it in the same PR
2. **Tests must execute code** — structural tests are banned by CI
3. **Sub-agents must inherit rules** — never launch an auditing agent without the mandatory preamble
4. **Architectural changes generate ADRs** — auto-detected, human-reviewed
5. **Measure before trusting** — mutation score, latency, kill rate — not just pass/fail
6. **Symlinks are first-class** — never classify a file as missing without `readlink -f`
7. **Silence is the enemy** — prefer loud failures over silent degradation

---

## REFERENCES

- Session summaries in engram (topic_key `session/*`, `audit/*`)
- ADRs documenting the fixes: ADR-001 to ADR-022
- Stabilization roadmap: `.cognitive-os/plans/roadmaps/stabilization-roadmap.md`
- Frozen backlog: `docs/architecture/FROZEN-BACKLOG.md`
- Memory files: `~/.claude/projects/.../memory/` (loaded every session)

---

**Last updated:** 2026-04-16
**Next review:** After any session that introduces >100 new lines of code OR modifies >10 files. Verify no red flags activated.

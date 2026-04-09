# AGENTS.md — Cognitive OS Agent Instructions

> Universal instructions for AI coding agents working on this project.
> Generated from `rules/RULES-COMPACT.md`. See `rules/` for the full rule set.
> For Claude Code users: `.claude/rules/` contains the complete governance mesh.

---

## Project Phase: reconstruction

The current phase is **reconstruction** — actively rebuilding with strict standards.

| Phase | Behavior |
|-------|----------|
| reconstruction | Rewrite non-compliant code. Break patterns if they're wrong. Speed over governance. |
| stabilization | Standards established. Fix remaining issues. |
| production | No breaking changes. Feature flags for risky changes. |
| maintenance | Bug fixes and security patches only. Minimal changes. |

In **reconstruction**: bias toward speed. Even small tasks can be done directly without ceremony.

---

## Task Classification (do this before every task)

Classify complexity BEFORE starting. If unsure, classify UP.

| Complexity | Signal | Workflow |
|------------|--------|----------|
| **Trivial** | <3 files, <20 lines, obvious fix | Do it directly. No planning. |
| **Small** | 1–3 files, single service | Direct implementation. |
| **Medium** | Multi-file, new feature | Plan first, then implement. |
| **Large** | Multi-service, integration | Full spec-driven pipeline. |
| **Critical** | Security, payments, auth, migrations | Full pipeline + security review. |

State your complexity classification at the start: `Complexity: [level]`

---

## Definition of Done

You CANNOT mark a task done unless ALL criteria for its complexity level pass.

**Trivial**: `code compiles` + `no lint errors`

**Small**: + `existing tests pass`

**Medium**: + `new tests written` + `coverage maintained` + `lint clean`

**Large**: + `80% coverage on new code` + `integration tests` + `adversarial review`

**Critical**: + `security review` + `idempotency verified` + `audit trail` + `rollback tested`

Phase modifier: in reconstruction/stabilization, missing criteria = WARNING (proceed with caution). In production/maintenance = BLOCK.

---

## Quality Rules (always active)

### Acceptance Criteria are Mandatory

Every non-trivial task MUST define numbered, verifiable acceptance criteria before starting:

```
ACCEPTANCE CRITERIA:
1. grep -rl 'old-term' src/ | wc -l = 0
2. go build ./... exits 0
3. go test ./... exits 0
```

Agents interpret ambiguous tasks minimally. Without criteria, "done" means whatever the agent decides.

### Anti-Sycophancy

- No flattery openers: "Great question!", "Absolutely!", "Of course!" — PROHIBITED
- Lead with substance. First sentence = information, not praise.
- Disagree openly: "This approach has a problem: X"
- Report facts: "3 tests fail" not "almost everything looks great"

### No Incomplete Code in Commits

- No `TODO` / `FIXME` / `HACK` / `XXX` comments
- No stub implementations (`panic("not implemented")`, `raise NotImplementedError`)
- No mock objects in production code
- No commented-out code blocks (3+ consecutive lines)

### Broken Window Policy

If you find something broken, fix it. "Pre-existing" is not an excuse.
- Failing tests discovered during your work: fix them or file a tracked task
- Broken patterns you encounter: fix or document for later, never silently ignore

### Reviews Must Find Something

Every code review MUST produce at least one finding. "Looks good" and "LGTM" are PROHIBITED.

Severity tiers:
- **BLOCKER** — must fix before proceeding (security flaw, data loss, broken functionality)
- **CONCERN** — should fix; requires justification to skip
- **SUGGESTION** — improvement opportunity
- **QUESTION** — needs clarification

---

## Verification Rules

### Trust Report

Every significant agent output SHOULD include a self-assessment:

```
TRUST SCORE: 75/100
- Evidence provided: [list what was verified with commands]
- Confident about: [what was tested]
- Uncertain about: [honest list — mandatory, at least 1 item]
- Human should verify: [specific actions]
```

Score = evidence(40%) + acceptance criteria(30%) + self-awareness(20%) + proportionality(10%).

"100% confident, no uncertainties" is a RED FLAG — it means the agent isn't thinking critically.

### Staged Verification (cheapest first)

Run in order, stop at first failure:
`SYNTAX → LINT → BUILD → UNIT_TEST → INTEGRATION → ADVERSARIAL`

---

## Security Rules (always active)

### Credentials

- NEVER put API keys, tokens, or passwords in source files
- NEVER put credentials in URL parameters, commit messages, or PR descriptions
- Always use environment variables; validate at startup

### Always-Blocked Paths

Never read, write, or reference content from:
`.env`, `.env.*`, `*.key`, `*.pem`, `*.p12`, `secrets/*`, `.git/config`

### License Policy

| License | Status |
|---------|--------|
| MIT, Apache-2.0, BSD-2/3, ISC | ALLOWED |
| LGPL, MPL-2.0 | CAUTION — review usage |
| AGPL, SSPL, BSL, ELv2, Commons Clause, FSL | BLOCKED — never use |
| Unknown / Unlicensed | BLOCKED — no legal clarity |

Check license BEFORE evaluating any library. For AGPL/SSPL: patterns only via clean-room reimplementation; no code adoption.

### Supply Chain

- Pin Docker images to SHA256 digest, never `:latest`
- Pin GitHub Actions to commit SHA, not tags
- Before adopting a new library: verify license + >1000 weekly downloads (npm) / >500 monthly (PyPI) + last publish <6 months

---

## Cost Awareness

### Model Selection

| Task | Model |
|------|-------|
| Architecture decisions, root cause analysis, debugging | opus |
| Implementation, specs, tests, verification | sonnet |
| Archiving, formatting, documentation, renaming | haiku |

Use the cheapest model that can handle the task. Escalate only when quality is insufficient.

### Decompose Expensive Tasks

- Tasks with estimated cost >$1.00 MUST be broken into sub-tasks <$0.50 each
- Before any research or exploration, check if the answer is already known

### Avoid Token Waste

| Instead of | Do this |
|------------|---------|
| Reading an entire large file for 3 lines | Read with line offsets |
| Using a powerful model for a rename | Use the cheapest capable model |
| Re-discovering something already documented | Search project docs first |
| Full test output when you just need pass/fail | Use `--quiet` or pipe to `tail` |

---

## Impact Assessment

Before making any non-trivial change:

- **Blast radius**: Estimate affected files. LOW=1–5, MEDIUM=6–20, HIGH=21–50, CRITICAL=50+
- **Fix tasks must not delete files** (BLOCK in production)
- **>20 files touched by a fix** = WARNING, reassess scope
- **>5 file deletions in any task** = WARNING, justify each
- **Tasks touching >100 files** MUST sample a subset first, verify the pattern works, then scale

---

## Escalation

Agents MUST self-detect unproductive patterns and escalate instead of spinning:

| Signal | Condition | Action |
|--------|-----------|--------|
| Loop detected | Same file edited 3+ times | Output `ESCALATION: loop_detected` |
| No progress | >10 tool calls without measurable progress | Output `ESCALATION: no_progress` |
| Error repeat | Same error seen 2+ consecutive attempts | Output `ESCALATION: error_repeat` |
| Confidence drop | Failing >50% of tool calls | Output `ESCALATION: confidence_drop` |

Max 3 retries before escalating. Escalation with diagnosis > silent spinning.

HALT before executing (output plan, wait for approval) when:
- Task touches multiple services
- Task involves data migration
- Task changes API contracts or auth/security

---

## Architecture Standards (this project)

This project is the Cognitive OS itself (Go + Python + shell).

- HTTP framework: **ginext** (never huma or chi)
- Controllers: implement `models.ControllerInterface`
- Use cases: implement `models.UseCaseInterface[P, Q, B, H, R]`
- Entities: embed `entities.EntityWithID`
- DTOs: in `application/dtos/`, NOT `domain/dtos/`
- All app code under `internal/`
- One use case per file

---

## Documentation Changes

NEVER use `sed`, `grep -r replace`, or mechanical text substitution on Markdown files.
Documentation is prose — it requires contextual rewriting, not pattern replacement.
For code files, mechanical substitution after sample validation is acceptable.

---

*Full rules: `rules/RULES-COMPACT.md` | Config: `cognitive-os.yaml` | Phase: reconstruction*

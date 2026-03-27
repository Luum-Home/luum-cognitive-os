# Skills — Domain Knowledge System

Skills are structured markdown files (SKILL.md) that give Claude domain-specific knowledge and conventions. They live in `.claude/skills/` (project-level) or `~/.claude/skills/` (global).

## Organization

```
.claude/skills/                          # Project-level (highest priority)
  typescript-patterns/SKILL.md
  nestjs-patterns/SKILL.md
  clean-arch-patterns/SKILL.md
  testing-patterns/SKILL.md
  daily-health-check/SKILL.md

~/.claude/skills/                        # Global (shared across projects)
  sdd-init/SKILL.md
  sdd-explore/SKILL.md
  sdd-propose/SKILL.md
  sdd-spec/SKILL.md
  sdd-design/SKILL.md
  sdd-tasks/SKILL.md
  sdd-apply/SKILL.md
  sdd-verify/SKILL.md
  sdd-archive/SKILL.md
  skill-creator/SKILL.md
  openspec/SKILL.md
  go-testing/SKILL.md
  _shared/                               # Conventions shared by all skills
    engram-convention.md
    persistence-contract.md
    openspec-convention.md
```

### Priority rules (from `skill-registry-protocol.md`)

1. Project skills override global skills for the same domain
2. Global skills provide cross-project capabilities
3. Auto-generated skills have lowest priority and can be safely regenerated

---

## Current Project Skills

### typescript-patterns (v1.0.0)
**Tech**: TypeScript | **Auto-generated**: Yes

Covers strict mode, validation (Zod + class-validator), import conventions, type patterns, error handling, async patterns. Key rules:
- `strict: true` always, never use `any`
- Prefer `interface` for public APIs, `type` for internals
- `as const` objects over TypeScript enums
- Custom error classes with `code` and `statusCode`

### nestjs-patterns (v1.0.0)
**Tech**: NestJS | **Auto-generated**: Yes

Covers module structure, conditional providers, guards, DTOs, error handling, config. Key rules:
- One module per feature/domain
- Conditional providers for external services (mock vs real via env var)
- Global AuthGuard with `@Public()` escape hatch
- ConfigModule with Zod validation

### clean-arch-patterns (v1.0.0)
**Tech**: Clean Architecture | **Auto-generated**: Yes

Covers layer rules, entities, use cases, repositories, testing strategy. Key rules:
- Domain never imports from Infrastructure or Presentation
- Use cases receive/return DTOs, not domain entities
- Repositories are interfaces in Application, implementations in Infrastructure
- Frameworks (NestJS, Express, Spring) only in Infrastructure and Presentation

### testing-patterns (v1.0.0)
**Tech**: Testing | **Auto-generated**: Yes

Per-service testing conventions:
- **NestJS**: Jest + @nestjs/testing, co-located `.spec.ts` files
- **Spring Boot**: WireMock + TestContainers, `@Profile("test")`
- **Express.js**: Jest + mock env flags
- **Go**: Table-driven tests, testify/assert, `-short` flag
- **Solidity**: Hardhat + ethers.js, loadFixture()

General rules: `should_[result]_when_[condition]` naming, AAA pattern, mock only at boundaries.

### daily-health-check
**Type**: Operational skill (not a coding pattern)

Checks all service health endpoints and infrastructure status. Steps:
1. Docker container status
2. HTTP health endpoints (BFF, <consumer-codename-b>, <consumer-codename-c>, onboarding, gateway, auth-provider)
3. Infrastructure probes (MySQL ping, MongoDB ping, Redis ping, RabbitMQ API)
4. Structured report with OK/DOWN status per service
5. Troubleshooting suggestions for failures

Can be scheduled as a daily cron job or Claude scheduled task.

### repair-status
**Type**: Operational skill

Reports auto-repair system health and statistics. Shows recent repair actions, success/failure rates, circuit breaker state, and never-auto-repair list status.

### metrics-calibrator
**Type**: Operational skill

Analyzes KPI history and auto-calibrates thresholds. Reviews metric trends over time and adjusts alert thresholds to reduce false positives and catch regressions earlier.

### conversation-memory
**Type**: Operational skill

Searches and learns from past sessions. Indexes session transcripts and enables semantic search across conversation history for pattern discovery and knowledge retrieval.

### tool-discovery
**Type**: Operational skill

Discovers new open-source tools via GitHub scanning. Periodically searches for relevant tools, evaluates license compatibility, and suggests additions to the project stack.

---

## Auto-Detection Flow

The skill system auto-detects what the project needs and suggests missing skills.

```
Session Start
  |
  v
stack-detector.sh
  -> scans for package.json, tsconfig.json, build.gradle, go.mod, etc.
  -> writes .claude/detected-stack.json
  |
  v
skill-auto-loader rule
  -> reads detected-stack.json
  -> maps each technology to an expected skill
  -> checks if the skill exists in .claude/skills/
  -> if missing: suggests "Detecte {tech} pero no hay skill. Queres que lo genere?"
  |
  v
skill-creator (if user approves)
  -> uses Context7 for up-to-date library docs
  -> generates SKILL.md with frontmatter (name, version, auto-generated: true)
  -> updates skill registry in Engram
```

---

## Auto-Improvement Flow

Skills improve over time through a feedback loop.

```
Skill runs and fails
  |
  v
skill-feedback-tracker.sh (hook)
  -> detects failure via exit code or error keywords
  -> saves to Engram: topic_key = "skill-feedback/{skill-name}"
  |
  v
Next time the skill runs
  |
  v
skill-adaptation rule
  -> searches Engram for "skill-feedback/{skill-name}"
  -> reads past failures
  -> adapts execution to avoid known failure modes
  |
  v
After 3+ failures for same skill
  |
  v
skill-adaptation rule triggers
  -> announces: "This skill has failed N times"
  -> invokes /skill-creator with failure context
  -> skill-creator rewrites SKILL.md
  -> updates skill registry
```

---

## How to Create a New Skill

### Option 1: Use `/skill-creator` (recommended)
1. Run `/skill-creator` with the skill name and purpose
2. It generates SKILL.md with proper frontmatter
3. It updates the skill registry

### Option 2: Manual creation
1. Create directory: `.claude/skills/{skill-name}/`
2. Create `SKILL.md` with frontmatter:
   ```yaml
   ---
   name: my-skill
   description: What this skill does
   version: 1.0.0
   last-updated: YYYY-MM-DD
   auto-generated: false
   tech: technology-name
   ---
   ```
3. Write instructions in markdown below the frontmatter
4. Add the technology mapping to `skill-auto-loader.md` if applicable
5. Run `/skill-registry` to update the index

### Skill file structure
- **Frontmatter**: YAML metadata (name, version, tech, auto-generated flag)
- **Title**: `# {Skill Name}`
- **Sections**: Organized by concern (patterns, rules, examples)
- **Code examples**: Inline when they clarify a convention
- **Keep it concise**: Skills should be under 100 lines to fit in context efficiently

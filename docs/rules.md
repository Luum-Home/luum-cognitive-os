# Rules — Always-Active Constraints

Rules are markdown files that Claude loads at session start and enforces throughout the entire session. They define constraints, protocols, and behaviors.

**Loading architecture**: `self-install.sh` symlinks exactly 16 core rules into `.claude/rules/cos/` at every session start. This reduces always-loaded tokens from ~93K (loading all 150+ rules) to ~21K. All other rules load contextually when a trigger condition matches.

## Core Rules (16 always-loaded)

These 16 rules are symlinked to `.claude/rules/cos/` by `self-install.sh` on every session start:

| Rule | File | Purpose |
|------|------|---------|
| Rules Compact | `RULES-COMPACT.md` | Thematic index of all rules; compressed reference |
| Adaptive Bypass | `adaptive-bypass.md` | Smart orchestration: workflow proportional to task complexity |
| Acceptance Criteria | `acceptance-criteria.md` | Every agent prompt must include measurable criteria |
| Agent Quality | `agent-quality.md` | Maximum output, not minimum; anti-sycophancy |
| Trust Score | `trust-score.md` | Mandatory Trust Report with evidence, uncertainty, verification |
| Token Economy | `token-economy.md` | 5 token principles: transparency, worthiness, memory-first |
| Phase-Aware Agents | `phase-aware-agents.md` | reconstruction/stabilization/production/maintenance behavior |
| Closed-Loop Prompts | `closed-loop-prompts.md` | Self-correcting agent execution with HALT-and-WAIT protocol |
| Error Learning | `error-learning.md` | Error capture protocol and PDCA mistake documentation |
| Rate Limiting | `rate-limiting.md` | Per-minute/hour limits on all tool invocations |
| Credential Management | `credential-management.md` | Credentials never in code; env vars and validation |
| Content Policy | `content-policy.md` | Prohibited terms; automated enforcement via hook |
| Result Management | `result-management.md` | Large output prevention; auto-truncation; large file reading |
| Blast Radius | `blast-radius.md` | Task scope estimation before agent launch |
| Clarification Gate | `clarification-gate.md` | Blocks vague prompts (ambiguity score >60) |
| Model Routing | `model-routing.md` | Routing table: which model for which task type |

## Contextual Rules (150+ total, loaded on trigger)

All other rules live in `rules/` and load when their trigger condition is detected. Examples:

| Category | Examples |
|----------|---------|
| Self-healing | `auto-repair.md`, `fault-tolerance.md`, `crash-recovery.md` |
| Quality gates | `definition-of-done.md`, `adversarial-review.md`, `sandbox-sampling.md` |
| Security | `agent-security.md`, `license-policy.md`, `supply-chain-defense.md` |
| Agent governance | `agent-kpis.md`, `agent-escalation.md`, `squad-protocol.md` |
| Architecture | `os-vs-project.md`, `component-classification.md`, `dogfooding.md` |
| Efficiency | `resource-governance.md`, `workload-scheduling.md`, `context-optimization.md` |

See `RULES-COMPACT.md` for the full thematic index with trigger conditions.

---

## 1. Constitutional Gates (`constitutional-gates.md`)

**Purpose**: 7 non-negotiable architectural principles. No code may violate these.

| Gate | Rule |
|------|------|
| 1 | Mobile NEVER talks directly to microservices (all traffic via BFF port 3001) |
| 2 | Mock before integrate (every external provider needs a mock with env var flag) |
| 3 | Test before merge (unit tests for logic, integration for cross-service) |
| 4 | Secrets never in code (always env vars, .env files never committed) |
| 5 | Backward compatible APIs (BFF endpoints need version bumps for breaking changes) |
| 6 | Idempotent operations (all financial ops use transaction IDs) |
| 7 | Audit trail (all financial ops traceable: who, when, what, amount) |

**Enforcement**: Claude checks these before generating code. The PR review GitHub Action also validates them.

---

## 2. Control Manifest (`control-manifest.md`)

**Purpose**: Defines what cannot be changed, performance targets, security rules, and task scaling.

### Required Libraries (no replacement without approval)
- NestJS 10, Spring Boot 3.0.6 / Java 17, Express.js, React Native 0.74 / Expo, Solidity / Hardhat

### Prohibited Zones (never modify)
- Flyway migrations, deployed smart contracts, auth provider realm config
- HTTP header names (`x-custom-*`), bundle IDs (`com.example.app`), Java package names

### Performance Constraints
- BFF: < 200ms p95 cached, no N+1 queries, pagination always
- Docker images: < 200MB, multi-stage builds
- Mobile: < 3s cold start, < 50MB bundle

### Security Constraints
- API keys in env vars only, JWT validation on every protected endpoint
- HMAC on webhooks, no raw SQL, input validation at all API boundaries

### Scale-Adaptive Intelligence

| Complexity | Signal | Action |
|------------|--------|--------|
| Trivial | Single file, < 20 lines | Do it directly |
| Small | 1-3 files, single service | Consider `/opsx:propose` |
| Medium | Multi-file, new feature | `/opsx:propose` then `/opsx:apply` |
| Large | Multi-service, architectural | `/sdd-new` then `/sdd-ff` then `/sdd-apply` |
| Critical | Security, auth, payments | `/sdd-new` with mandatory `/sdd-verify` |

---

## 3. License Policy (`license-policy.md`)

**Purpose**: Vets dependency licenses for a commercial closed-source SaaS platform.

| Category | Licenses | Verdict |
|----------|----------|---------|
| Allowed | MIT, BSD-2, BSD-3, Apache 2.0, ISC, CC0 | Safe |
| Caution | LGPL v2.1/v3 (dynamic link only), MPL 2.0, Artistic 2.0 | Conditional |
| Blocked | AGPL v3, SSPL, BSL, ELv2, Commons Clause, FSL | Forbidden for SaaS |

**Procedure**: Check license before adding any dependency. Transitive dependencies count. Dual-licensed tools need commercial license evaluation. Document decisions in `docs/research/license-analysis.md`.

**Exception**: AGPL/SSPL tools allowed ONLY as completely separate containers with no code modifications, communicating via public API.

---

## 4. Skill Adaptation (`skill-adaptation.md`)

**Purpose**: Closed-loop system for skills to improve over time based on real usage data.

### Before running a skill
1. Search Engram for `skill-feedback/{skill-name}`
2. Read past failures if they exist
3. Adapt execution based on what failed before

### After a skill fails
1. Save failure details to Engram immediately (topic key: `skill-feedback/{skill-name}`)
2. Record user corrections if the user fixes things manually

### After a skill recovers (had failures before)
1. Update Engram with the successful approach

### Auto-improvement trigger (3+ failures)
1. Announce the pattern of failures
2. Invoke `/skill-creator` with failure context
3. Skill creator rewrites the SKILL.md
4. Update skill registry

### Layer diagram
```
Layer 4: Skill Registry -- knows what skills exist and where
Layer 3: Engram -- remembers what worked and what didn't
Layer 2: Hooks -- detects failures in real-time (skill-feedback-tracker.sh)
Layer 1: skill-creator -- proposes and applies changes to SKILL.md
```

---

## 5. Skill Auto-Loader (`skill-auto-loader.md`)

**Purpose**: Maps the detected technology stack to available skills and identifies gaps.

### How it works
1. Reads `.claude/detected-stack.json` (generated by `stack-detector.sh`)
2. For each detected technology, checks if the corresponding skill exists
3. If a skill is missing, suggests creation (does NOT auto-generate without user approval)

### Technology-to-skill mapping

| Detected Tech | Expected Skill | Status |
|---------------|---------------|--------|
| typescript | typescript-patterns | Exists |
| nestjs | nestjs-patterns | Exists |
| clean_architecture | clean-arch-patterns | Exists |
| jest | testing-patterns | Exists |
| spring_boot | spring-boot-patterns | Pending |
| express | express-patterns | Pending |
| react_native | react-native-patterns | Pending |
| golang | go-patterns | Pending |
| solidity | solidity-patterns | Pending |
| docker | docker-patterns | Pending |

### Auto-generated skills
- Marked with `auto-generated: true` in frontmatter
- Use Context7 for up-to-date library documentation
- Registered in skill registry after creation

---

## 6. Skill Registry Protocol (`skill-registry-protocol.md`)

**Purpose**: Defines skill loading priority, versioning, and refresh rules.

### Priority order
1. **Project skills** (`.claude/skills/`) -- highest priority, project-specific
2. **Global skills** (`~/.claude/skills/`) -- shared across projects
3. **Auto-generated skills** -- created by skill-auto-loader

### Versioning
Each skill has YAML frontmatter:
```yaml
name: typescript-patterns
version: 1.0.0
last-updated: 2026-03-21
auto-generated: true
tech: typescript
```

### Refresh rules
- If Context7 shows breaking changes in a library, suggest regenerating the skill
- Auto-generated skills can be regenerated safely
- Manual skills are NEVER overwritten automatically

---

## 7. Auto-Repair (`auto-repair.md`)

**Purpose**: Always-active rule governing the auto-repair system. Defines phase gates, circuit breaker behavior, and the never-auto-repair list.

### Phase gates
Repairs progress through phases: detect, diagnose, propose, apply, verify. Each phase must complete successfully before advancing.

### Circuit breaker
If a repair loop fails 3 consecutive times for the same issue, the circuit breaker trips and the system stops attempting automatic repairs. Manual intervention is required to reset.

### Never-auto-repair list
Certain components are excluded from automatic repair: Flyway migrations, deployed smart contracts, auth provider realm config, and any file in the prohibited zones defined by the control manifest.

---

## 8. Metrics Calibration (`metrics-calibration.md`)

**Purpose**: Contextual rule for metric threshold auto-calibration. Activates when the metrics-calibrator skill runs.

### How it works
1. Reviews KPI history (last 7-30 days depending on metric type)
2. Calculates statistical baselines (mean, p95, p99)
3. Proposes new thresholds based on observed trends
4. Requires user approval before applying threshold changes

### Safeguards
- Thresholds can only be relaxed by up to 20% per calibration cycle
- Critical metrics (security, financial) cannot be auto-calibrated
- All threshold changes are logged to metrics JSONL files

### Registry storage
- `/skill-registry` command scans all skills and creates the registry file
- Registry is stored in Engram for cross-session access
- Sub-agents consult the registry to know which skills to load

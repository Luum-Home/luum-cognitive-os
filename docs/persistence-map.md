# Persistence Map — What's in Git vs What's Not

> Comprehensive map of what persists across machines/developers (git-tracked) vs what's local-only.

## In Git (persists across machines/developers)

### Cognitive OS Core

| Component | Location | What it contains |
|---|---|---|
| Skills | `.claude/skills/` | Skill definitions with SKILL.md + references/ |
| Rules | `.claude/rules/` | Rule files (architecture, security, compliance, services) |
| Hooks | `.claude/hooks/` | Hook scripts (safety, metrics, learning, fault tolerance, engram sync) |
| SOUL.md | `.claude/SOUL.md` | Behavioral principles and boundaries |
| IDENTITY.md | `.claude/IDENTITY.md` | Agent role and specialization |
| Settings (hooks) | `.claude/settings.json` | Hook registration (generated, versionable) |
| Settings (local) | `.claude/settings.local.json` | Personal overrides (gitignored) |
| Skill Registry | `.atl/skill-registry.md` | Index of all skills + agents |

### Engram Exports (team memory synced to git)

| Component | Location | What it contains |
|---|---|---|
| Observations | `.engram/exports/observations-*.json` | Decisions, bugs, architecture, patterns, session summaries |

Sync flow:
- **Export**: `scripts/engram-sync.sh` or automatic via Stop hook (`engram-auto-sync.sh`)
- **Import**: `scripts/engram-import.sh` or automatic via SessionStart hook (`engram-auto-import.sh`)
- **Format**: Native engram export (JSON with sessions + observations + prompts)

### Documentation

| Component | Location | What it contains |
|---|---|---|
| All docs | `docs/` | Estado, plans, research, cognitive-os, mobile, evaluations, etc. |
| Indexes | `docs/INDEX.md`, `docs/*/INDEX.md` | Master indexes for all documentation |

### Infrastructure

| Component | Location | What it contains |
|---|---|---|
| Docker configs | `docker-compose*.yml` | All container definitions |
| Auth realm config | `IDP/idp/localhost/` | Realm config + Terraform |
| Local env init | `micro-services/local-env-initializer/` | Init scripts |

### Code

| Component | Location | What it contains |
|---|---|---|
| BFF | `mobile/bff-ninja/` | NestJS gateway |
| Mobile app | `mobile/app/` | React Native/Expo |
| Users Core | `micro-services/users-core/` | Spring Boot |
| Users Auth | `micro-services/users-auth/` | Spring Boot |
| Onboarding | `micro-services/onboarding/` | NestJS |
| Monolith | `services/acme-gateway/` | Express.js |
| Smart contracts | `contracts-ozv5/` | Solidity |
| Scripts | `scripts/` | Automation (sync, import, onboarding, health checks) |

## NOT in Git (local only, machine-specific)

### Engram Runtime

| Component | Location | Recreatable? |
|---|---|---|
| Engram SQLite DB | `~/.local/share/engram/` | YES — run `scripts/engram-import.sh` |
| Engram server | Running on port 7437 | YES — `engram serve` |
| Import marker | `.engram/exports/.last-import` | YES — auto-created on import |

### Cognitive OS Runtime State

| Component | Location | Recreatable? |
|---|---|---|
| active-tasks.json | `.claude/tasks/` | YES — session-resume.sh detects |
| skill-metrics.jsonl | `.claude/metrics/` | NO — accumulated over time |
| error-learning.jsonl | `.claude/metrics/` | NO — accumulated over time |

### Docker Runtime

| Component | Location | Recreatable? |
|---|---|---|
| Docker volumes | Docker Desktop | YES — docker compose up recreates |
| Container state | Docker runtime | YES — restart containers |
| Database data | MySQL/MongoDB volumes | YES — seeds recreate test data |

### Global Config (not project-specific)

| Component | Location | Recreatable? |
|---|---|---|
| Global skills | `~/.claude/skills/` | YES — re-install |
| Engram plugin | `~/.claude/plugins/` | YES — `engram setup claude-code` |
| Global settings | `~/.claude/settings.json` | YES — re-configure |
| Global CLAUDE.md | `~/.claude/CLAUDE.md` | PARTIAL — has custom protocols |

## How to Onboard a New Developer

```bash
git clone <repo-url>
cd cognitive-os
./scripts/onboard-developer.sh
```

The script handles:
1. Prerequisite checks (Docker, Node, Go, Java, Yarn)
2. Starting Engram and importing team memory
3. Starting infrastructure via Docker Compose
4. Starting services
5. Health checking

## How to Share Memory (Team Sync)

After significant work:
```bash
# Automatic: happens on session end via Stop hook
# Manual:
./scripts/engram-sync.sh
git add .engram/
git commit -m "sync: engram observations $(date +%Y-%m-%d)"
git push
```

Teammate pulls and imports:
```bash
git pull
# Automatic: happens on session start via SessionStart hook
# Manual:
./scripts/engram-import.sh
```

## What Happens If You Lose Everything

| Scenario | Recovery |
|---|---|
| New machine | `git clone` + `./scripts/onboard-developer.sh` |
| Lost Docker volumes | `docker compose up -d` recreates all |
| Lost Engram DB | `./scripts/engram-import.sh` from `.engram/exports/` |
| Lost metrics | Accumulated data lost — starts fresh |
| Lost active-tasks | `session-resume.sh` detects incomplete tasks |

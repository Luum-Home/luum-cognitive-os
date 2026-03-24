# State Snapshots (Devbox)

## Overview

Devbox provides reproducible, declarative development environments via Nix. The Cognitive OS uses it for:

1. **Deterministic toolchain** — `devbox.json` pins exact versions of Go, Node, Java, Python, and CLI tools
2. **Environment checkpoints** — `/checkpoint` skill saves and restores environment state snapshots

## Setup

Devbox is installed at `~/.local/bin/devbox`. The project config is at `devbox.json` (project root).

### Packages

| Package | Version | Purpose |
|---------|---------|---------|
| go | 1.25 | Go monorepo services |
| nodejs | 20 | BFF, onboarding, monolith, mobile |
| jdk | 17 | users-core, users-auth (Spring Boot) |
| python | 3.11 | Scripts, ML, data processing |
| docker-compose | latest | Infrastructure orchestration |
| jq | latest | JSON processing in hooks/scripts |
| yq | latest | YAML processing in hooks/scripts |

### Usage

```bash
# Enter the devbox shell (activates all packages)
devbox shell

# Run a script defined in devbox.json
devbox run start    # docker-compose up -d
devbox run stop     # docker-compose down
devbox run test     # test info
```

## Checkpoints

The `/checkpoint` skill saves lightweight JSON snapshots of the environment state.

### Save a checkpoint
```
/checkpoint save pre-refactor
```

### Restore / compare
```
/checkpoint restore pre-refactor
/checkpoint diff pre-refactor
/checkpoint list
```

### What's captured
- `devbox.json` package list and hash
- `go.sum`, `package-lock.json`, `yarn.lock` hashes (dependency drift detection)
- `git status` and recent commits
- Running Docker containers

### Storage
Checkpoints are stored in `.cognitive-os/checkpoints/{timestamp}.json`. Maximum 50 retained.

## Integration with Cognitive OS

- Registered in `cognitive-os.yaml` under `environment.tool: devbox`
- Checkpoint skill in `skills/devbox-checkpoint/SKILL.md`
- Invocable as `/checkpoint`

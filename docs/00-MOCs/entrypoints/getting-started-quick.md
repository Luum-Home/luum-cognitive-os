# Getting Started with Cognitive OS

## Install (30 seconds)

```bash
curl -fsSL https://raw.githubusercontent.com/Luum-Home/luum-cognitive-os/main/scripts/install-cos.sh | bash
```

Or with Go:

```bash
go install github.com/Luum-Home/luum-cognitive-os/cmd/cos@latest
```

## New Project (1 minute)

```bash
cos new my-api --template go
cd my-api
```

This creates a Go project with COS pre-configured:
- 14 core quality rules (always active)
- 24 hooks (standard security profile)
- Engram persistent memory
- Auto skill selection

Available templates: `go`, `typescript`, `python`, `minimal`.

## Existing Project (1 minute)

```bash
cd your-project
cos init
```

Interactive wizard detects your stack and configures COS.

## Use It

Open Claude Code and talk naturally:

| You say | COS does |
|---------|----------|
| "add JWT auth" | Runs full SDD pipeline (propose, spec, design, apply, verify) |
| "fix the login bug" | Auto-selects plan-bug + systematic-debugging |
| "run the tests" | Detects your framework, runs with coverage |
| "check security" | Runs security-audit with Semgrep + aguara |

## Essential Commands

```bash
cos status              # check COS health
cos search <query>      # find packages
cos install <package>   # install a package
cos version             # show versions
```

## What Runs Behind the Scenes

COS works invisibly through Claude Code hooks:
- **Quality gates** verify every agent completion with acceptance criteria
- **Trust scoring** catches overclaimed results (mandatory self-doubt)
- **Memory** persists decisions, bugs, and discoveries across sessions
- **Security** scans for leaked credentials and vulnerabilities
- **Cost management** routes to optimal models, prevents token waste

## Keeping COS Updated

Your project auto-updates when the OS releases a new version:

```bash
# In the COS repo — release triggers auto-update of all registered projects:
cos release --patch

# Or manually update a specific project:
cd /path/to/your-project
COS_SOURCE_DIR=/path/to/luum-agent-os cos setup --non-interactive --preset team
```

Projects are registered automatically during `cos setup`. Check registration:
```bash
cat ~/.cognitive-os/installations.json
```

## Configuration

Edit `cognitive-os.yaml` in your project root:
- `project.phase` controls enforcement strictness
- `efficiency.profile` controls hook overhead (lean/standard/full)
- `resources.budget` sets cost limits
- `model_capability.level` adjusts safety net depth

## Learn More

- [Available skills](../skills/CATALOG.md)
- [Rules reference](../rules/RULES-COMPACT.md)
- [Security stack](security-stack.md)

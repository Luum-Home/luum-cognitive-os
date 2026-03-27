# Hello World — Cognitive OS Example

A minimal project demonstrating Cognitive OS setup. This example shows how Cognitive OS integrates with a simple Node.js project.

## What's Inside

```
hello-world/
├── index.js              <- Simple Express server (the "project")
├── package.json          <- Project dependencies
├── cognitive-os.yaml     <- Cognitive OS configuration
└── README.md             <- You are here
```

## Try It

### 1. Install Cognitive OS

```bash
cd examples/hello-world

# Copy the framework from the repo root
cp -r ../../.cognitive-os/ .cognitive-os/
```

### 2. Initialize

```bash
# Open Claude Code
claude

# Run the init skill — it will detect Node.js + Express
> /cognitive-os-init
```

### 3. See What Got Generated

After init, Cognitive OS creates project-specific files:

```
.claude/
├── settings.json         <- Hook registrations (auto-generated)
├── rules/
│   ├── node-architecture.md   <- Node.js best practices
│   └── testing-local.md       <- Test configuration
├── skills/
│   └── project-specific/      <- Skills tailored to Express
└── hooks/
    └── block-prod-urls.sh     <- Prevents accidental prod access
```

### 4. Start Building

Now every Claude Code session in this project has:
- Persistent memory (Engram)
- Quality gates (tests must pass)
- Error learning (mistakes are remembered)
- Auto-repair (MAPE-K self-healing)

```bash
# Ask Claude to add a feature — Cognitive OS enforces quality automatically
claude
> Add a /health endpoint with proper tests
```

## What Cognitive OS Does Differently

Without Cognitive OS:
```
You: "Add a /health endpoint"
AI: *writes code, maybe tests, maybe not, forgets about it next session*
```

With Cognitive OS:
```
You: "Add a /health endpoint"
AI: *writes code, writes tests (enforced by rules), runs them (enforced by hooks),
     remembers the decision (Engram), learns from any errors (error-learning hook)*
```

## Configuration

The `cognitive-os.yaml` in this example uses minimal settings:

```yaml
project:
  name: hello-world
  type: webapp
  phase: reconstruction    # Full freedom to build fast
```

See the [main documentation](../../docs/) for all configuration options.

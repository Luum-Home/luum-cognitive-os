# How to Extend the AI Ecosystem

Step-by-step guides for adding new components to the AI-assisted development setup.

---

## Add a New Hook

Hooks are shell scripts that intercept Claude tool usage at specific lifecycle points.

### Steps

1. **Create the script** in `.claude/hooks/`:
   ```bash
   #!/bin/bash
   # Hook: <trigger> -- <description>
   set -euo pipefail

   INPUT=$(cat)  # JSON from stdin with tool_name, tool_input, tool_response, etc.

   # Your logic here

   exit 0
   ```

2. **Register it** in `.claude/settings.local.json` under the appropriate trigger:
   ```json
   {
     "hooks": {
       "<trigger>": [
         {
           "matcher": "<tool_pattern>",
           "hooks": [
             {
               "type": "command",
               "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/your-hook.sh\""
             }
           ]
         }
       ]
     }
   }
   ```

3. **Make it executable**: `chmod +x .claude/hooks/your-hook.sh`

### Available triggers

| Trigger | When | Input (stdin JSON) | Can block? |
|---------|------|-------------------|------------|
| `PreToolUse` | Before a tool runs | `tool_name`, `tool_input` | Yes (return `{"decision": "deny", "reason": "..."}`) |
| `PostToolUse` | After a tool runs | `tool_name`, `tool_input`, `tool_response`, `exit_code` | No |

### Matcher patterns
- Single tool: `"Bash"`, `"Edit"`, `"Write"`
- Multiple tools: `"Edit|Write"`, `"Agent|Skill"`

---

## Add a New Rule

Rules are markdown files that define always-active constraints.

### Steps

1. **Create the file** in `.claude/rules/`:
   ```markdown
   # Rule Name

   ## Purpose
   What this rule enforces and why.

   ## Constraints
   - Constraint 1
   - Constraint 2

   ## When it applies
   Description of when Claude should check this rule.
   ```

2. **No registration needed** -- Claude auto-loads all files in `.claude/rules/` at session start.

### Guidelines
- Keep rules concise and actionable
- Use tables for structured constraints
- Rules should be prescriptive ("DO this", "NEVER do that"), not descriptive
- Reference other rules by filename if there are dependencies

---

## Add a New Skill

Skills are domain knowledge files that teach Claude project-specific patterns.

### Option A: Auto-generate with `/skill-creator`

1. Run `/skill-creator` and describe the skill you need
2. It generates the SKILL.md with proper frontmatter
3. It updates the skill registry in Engram

### Option B: Manual creation

1. **Create the directory**: `.claude/skills/{skill-name}/`

2. **Create SKILL.md** with frontmatter:
   ```yaml
   ---
   name: skill-name
   description: One-line description
   version: 1.0.0
   last-updated: YYYY-MM-DD
   auto-generated: false
   tech: technology-name
   ---
   ```

3. **Write the content** below the frontmatter. Structure:
   - Title: `# {Name}`
   - Sections organized by concern
   - Code examples where they clarify conventions
   - Keep under 100 lines for context efficiency

4. **Add to auto-loader** (optional): If the skill maps to a detected technology, add it to `.claude/rules/skill-auto-loader.md` in the technology-to-skill table.

5. **Update registry**: Run `/skill-registry` to update the index.

### For operational skills (like daily-health-check)

Use command-style frontmatter instead:
```yaml
---
description: What this skill does
command: skill-command-name
---
```

---

## Add a New GitHub Action

GitHub Actions provide CI/CD integration with Claude.

### Steps

1. **Create the workflow** in `.github/workflows/`:
   ```yaml
   name: Claude <Action Name>

   on:
     <trigger>:
       types: [<event_types>]

   jobs:
     <job-name>:
       runs-on: ubuntu-latest
       permissions:
         contents: read
         pull-requests: write  # if needed
         issues: write          # if needed
       steps:
         - name: Checkout
           uses: actions/checkout@v4

         - name: Claude Action
           uses: anthropics/claude-code-action@v1
           with:
             model: claude-sonnet-4-6
             max_turns: 10
             anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
             direct_prompt: |
               Your prompt here. Include:
               - Platform context (service list, architecture rules)
               - What to check for
               - Expected output format
   ```

2. **Add the secret**: Ensure `ANTHROPIC_API_KEY` is configured in the repo's GitHub Secrets.

### Common triggers

| Trigger | Use case |
|---------|----------|
| `pull_request: [opened, synchronize]` | Code review |
| `issues: [opened]` | Issue triage |
| `issue_comment: [created]` | On-demand via `@claude` mention |
| `push: branches: [main]` | Post-merge checks |

---

## Add a New MCP Server

MCP servers provide Claude with external capabilities (memory, documentation, APIs).

### Currently configured

| Server | Purpose | How configured |
|--------|---------|---------------|
| Engram | Persistent memory | Plugin in Claude Code settings |
| Context7 | Live library docs | Plugin in Claude Code settings |

### Steps to add a new MCP server

1. **Install the MCP server** (usually an npm package or binary)
2. **Configure it** in Claude Code settings (global or project-level)
3. **Document its tools** so the team knows what's available
4. **Add usage rules** to `.claude/rules/` if the server has constraints

### Common MCP server types
- **Memory/knowledge**: Persistent storage for decisions and context
- **Documentation**: Live docs for libraries and frameworks
- **API connectors**: Jira, Slack, GitHub, etc.
- **File management**: Google Drive, Notion, etc.

---

## Add a New Agent Persona (Agent Teams)

Agent Teams (experimental) allow the orchestrator to delegate to specialized sub-agents.

### Steps

1. **Define the persona** in a prompt template that includes:
   - Role and responsibilities
   - Skill references (pre-resolved by orchestrator)
   - Engram write instructions
   - Expected output format

2. **Register in SDD** (if it's a new SDD phase):
   - Create the skill in `~/.claude/skills/{phase-name}/SKILL.md`
   - Define read/write dependencies in the dependency graph
   - Add Engram topic key format

3. **Launch pattern** (orchestrator uses this):
   ```
   SKILL: Load `{resolved-skill-path}` before starting.

   Your task: {description}

   Context from prior phases:
   - {artifact references from Engram}

   If you make important discoveries, decisions, or fix bugs,
   save them to engram via mem_save with project: '{project}'.
   ```

### Rules for sub-agents
- Sub-agents get fresh context (no memory)
- Orchestrator passes context, sub-agents don't search for it
- Sub-agents MUST save significant findings to Engram before returning
- Use `delegate` (async) by default, `task` (sync) only when the result is needed immediately

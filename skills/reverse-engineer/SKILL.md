---
name: reverse-engineer
description: >
  Deep source code analysis of a dependency to understand its internal APIs,
  config schemas, CLI commands, environment variables, and undocumented behavior.
  When docs are incomplete, reading source code gives the EXACT answer in minutes.
version: 1.0.0
user-invocable: true
auto-generated: false
last-updated: 2026-03-29
license: MIT
metadata:
  author: luum
audience: both
effort: opus
---

## Purpose

Reading documentation saves hours. Reading source code saves days.

When documentation is incomplete, outdated, or simply wrong (like Paperclip's
undocumented config schema), reverse engineering the actual source code gives you
the EXACT answer in minutes instead of hours of trial-and-error.

This skill performs deep source code analysis of a dependency to extract:
- Config schemas (Zod, TypeScript interfaces, JSON Schema, Go structs, Pydantic models)
- Environment variables (process.env, os.Getenv, os.environ, etc.)
- CLI commands (Cobra, Commander.js, Yargs, Argparse, Click)
- API routes (Express, Fastify, Gin, Flask, FastAPI, Spring Boot)
- Docker setup (Dockerfile, compose, ports, volumes, entrypoint)
- Authentication flows (JWT, session, OAuth, API key)

### Key Difference from `/repo-forensics`

| Aspect | `/repo-forensics` | `/reverse-engineer` |
|--------|-------------------|---------------------|
| Depth | Surface-level (README, deps, architecture) | Deep (reads source files, extracts schemas) |
| Goal | Evaluate a repo for adoption/comparison | Understand HOW to integrate with a dependency |
| Output | Tech radar classification, feature list | Integration guide with exact config values |
| When to use | Evaluating whether to adopt a tool | Already adopting, need the internal details |

## Invocation

```
/reverse-engineer <repo-url-or-local-path> [--focus schema|env|cli|routes|docker|auth|all]
```

| Flag | Effect |
|------|--------|
| (none) | Full analysis (all dimensions) |
| `--focus schema` | Only config schema analysis |
| `--focus env` | Only environment variable analysis |
| `--focus cli` | Only CLI command analysis |
| `--focus routes` | Only API route analysis |
| `--focus docker` | Only Docker setup analysis |
| `--focus auth` | Only authentication flow analysis |

## What to Do

### Step 1: Resolve the Target

Parse the argument to determine if it is a local path or a remote URL.

- **Local path**: verify it exists, use directly
- **Git URL**: clone to `/tmp/reverse-engineer-{repo-name}` with `--depth 1`
- **GitHub shorthand** (`owner/repo`): expand to `https://github.com/owner/repo.git`

If the target was already cloned (directory exists in `/tmp/`), reuse it.

### Step 2: Run the Analysis

Use `lib/reverse_engineer.py` to perform the analysis:

```python
from lib.reverse_engineer import ReverseEngineer

re = ReverseEngineer()
report = re.full_analysis(repo_path)
```

Or run focused analyses based on `--focus` flag:

```python
re = ReverseEngineer()

# Individual analyses
schemas = re.analyze_config_schema(repo_path)
env_vars = re.analyze_env_vars(repo_path)
cli_cmds = re.analyze_cli_commands(repo_path)
routes = re.analyze_api_routes(repo_path)
docker = re.analyze_docker_setup(repo_path)
auth = re.analyze_auth_flow(repo_path)
```

### Step 3: Deep-Dive on Key Findings

After the automated scan, manually investigate the most important findings:

1. **Read the main config schema file** -- the automated scan finds it, but you should
   read the surrounding code to understand validation logic, defaults, and interactions
2. **Read the entrypoint** -- `main.go`, `index.ts`, `app.py`, or whatever the entry is.
   This reveals initialization order and required setup steps.
3. **Read the Docker entrypoint script** -- if there is one, it often reveals required
   env vars, volume mounts, and startup sequences that are NOT in the docs
4. **Check test files** -- test fixtures often contain valid config examples that
   demonstrate the expected schema values

### Step 4: Produce the Integration Guide

Format the results using:

```python
guide = re.format_integration_guide(report)
```

The guide is a structured markdown document with:
- Config schema tables (field, type, required, default, valid values)
- Environment variable table (name, file, required, default)
- CLI command table
- API route table
- Docker setup summary
- Auth flow summary

### Step 5: Save Findings to Engram

Save the integration guide to engram for future reference:

```
mem_save(
  title: "Reverse Engineering: {repo-name}",
  type: "discovery",
  scope: "project",
  topic_key: "docs/dependencies/{repo-name}",
  content: "{integration guide}"
)
```

## What Makes This Different

Most dependency analysis tools read documentation. This one reads SOURCE CODE.

When you encounter a dependency with:
- Incomplete docs ("see examples folder" that has no examples)
- Outdated docs (API changed but docs weren't updated)
- No docs at all (internal tool, pre-release software)
- Wrong docs (documented config keys that don't exist)

...this skill gives you the truth by reading what the software actually does.

## Supported Languages/Frameworks

### Config Schema Detection
- TypeScript: Zod schemas, interfaces (with Config/Options/Settings/Schema in name)
- Go: structs with json/yaml/env tags (with Config/Options/Settings in name)
- Python: dataclasses, Pydantic BaseModel/BaseSettings
- JSON: JSON Schema files ($schema marker)

### Environment Variable Detection
- JavaScript/TypeScript: `process.env.X`, `process.env["X"]`
- Go: `os.Getenv("X")`, `os.LookupEnv("X")`
- Python: `os.environ["X"]`, `os.getenv("X")`, `os.environ.get("X")`
- Rust: `env::var("X")`
- Java/Kotlin: `System.getenv("X")`
- Ruby: `ENV["X"]`
- .env files: `KEY=value`

### CLI Command Detection
- Go: Cobra commands
- JavaScript: Commander.js, Yargs
- Python: Argparse, Click

### API Route Detection
- JavaScript: Express.js, Fastify
- Go: Gin, Echo, Chi, net/http
- Python: Flask, FastAPI
- Java/Kotlin: Spring Boot

### Docker Detection
- Dockerfile: FROM, EXPOSE, ENV, ENTRYPOINT, CMD, VOLUME, HEALTHCHECK
- docker-compose: services, ports, environment, volumes, healthcheck

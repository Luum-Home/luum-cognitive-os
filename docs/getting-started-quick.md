# Cognitive OS Quick Start

> Minimal path for a developer who wants the core safety layer before exploring advanced surfaces.

## 1. Install into a project

Run from the consumer project, not from the Cognitive OS source checkout:

```bash
/path/to/luum-agent-os/install.sh --from /path/to/luum-agent-os --harness=codex --force
```

Use `--harness=claude` for Claude Code.

## 2. Verify the install

```bash
COGNITIVE_OS_PROJECT_DIR="$PWD" bash /path/to/luum-agent-os/scripts/cos-status.sh
```

Expected result: `.cognitive-os/` exists, the selected harness settings exist,
and core rules, hooks, skills, and templates are installed.

## 3. Work one feature through the local SDD lane

For medium or larger feature work:

```bash
cos sdd next --feature example --title "Example feature"
cos sdd approve example
cos sdd apply example
cos sdd review example
```

This writes durable artifacts under `.cognitive-os/workflows/sdd/` and requires
traceability from every `R<n>` requirement to a test or accepted proof.

## 4. Keep first contact small

Dashboards, squads, external task adapters, and advanced automation are optional.
The default promise is governance, verification, and portability in a real repo.

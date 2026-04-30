# Path Portability and Privacy

> Last updated: 2026-04-28. Scope: Cognitive OS itself and projects that install Cognitive OS.

Cognitive OS must not commit developer-specific absolute home paths. A path like
`<developer-home>/Projects/private-app` leaks machine identity, makes docs and
fixtures non-portable, and teaches consumer projects to copy local workstation
state into AI-facing agentic primitives.

## Policy

Do not commit paths rooted in a developer home directory, including:

- macOS-style developer homes;
- Linux-style developer homes;
- Windows-style developer homes.

Use one of these instead:

- `<repo-root>` for the Cognitive OS repository root;
- `<project-root>` for an installed consumer project;
- `<developer-home>` only as a placeholder, never as a real user path;
- `$HOME`, `$CODEX_HOME`, `$CLAUDE_HOME`, or `$PROJECT_DIR` when an environment
  variable is the real contract;
- `/workspace/...` for synthetic test fixtures that need an absolute path but
  must not look like a developer workstation.

## Enforced Scanner

The executable scanner is:

```bash
python3 scripts/check_absolute_paths.py --root .
```

It scans Git-tracked text files by default, including docs, rules, skills,
Python, Go, shell scripts, JSON, and YAML. It skips binary or heavy artifact
suffixes such as images, PDFs, fonts, archives, and local databases.

For pre-commit use, the hook runs:

```bash
python3 scripts/check_absolute_paths.py --root "$COS_ROOT" --staged
```

That means new commits are blocked when staged files contain developer-home path
leaks.

## Memory Exports

Engram JSONL exports can contain raw session observations, including local paths
and private project names. They are local recovery artifacts, not source files.

Therefore:

- `.engram/exports/*.jsonl` is ignored by Git;
- existing real exports should be removed from the Git index with
  `git rm --cached`, not deleted from disk;
- share only sanitized fixtures when a test needs memory-export content.

## Consumer Projects

Projects that install Cognitive OS inherit the same rule: AI-facing agentic primitives
such as hooks, skills, rules, docs, MCP config snippets, and tests should not
embed workstation-specific absolute paths.

The scanner can be copied or executed from the installed OS source to validate a
consumer project before committing agentic primitives.

## Proof Paths

- `scripts/check_absolute_paths.py` — scanner implementation.
- `.githooks/pre-commit` — staged-file enforcement.
- `tests/unit/test_check_absolute_paths.py` — behavior tests for detection,
  placeholders, CLI blocking, and the repository-wide tracked-file contract.

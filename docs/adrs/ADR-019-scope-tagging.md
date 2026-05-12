---
adr: 19
title: Scope Tagging -- Agentic Primitive Audience Classification
status: accepted
implementation_status: partial
date: '2026-04-13'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: implementation evidence plus partial/deferred/future signal
---

# ADR-019: Scope Tagging -- Agentic Primitive Audience Classification

**Date:** 2026-04-13
**Status:** Accepted
**Commits:** 9fdd2e1, 77c6d41, 62a700e
**Engram IDs:** 3086, 4920

## Context

Cognitive OS agentic primitives serve two distinct audiences: the OS itself (internal tooling for development and maintenance) and projects that install the OS (user-facing capabilities). Without scope classification, `self-install.sh` and `cos install` installed all agentic primitives everywhere. OS-internal agentic primitives like `register-component` or `release-os` were being deployed into user projects where they served no purpose and added confusion. The rules-to-hooks migration (ADR-015) made this worse by moving enforcement from context (where rules could at least be ignored) to hooks (which always run).

## Decision

Add scope tags to all agentic primitives across three categories:

- **`os-only`**: Internal to the OS agentic primitives. Not installed in user projects. Examples: release-os, register-component, wiring-validator, component-classifier.
- **`project`**: User-facing. Installed in projects that adopt the OS. Examples: run-tests, code-review, sdd-apply.
- **`both`**: Needed by both the OS and user projects. Examples: sdd-explore, engram memory tools, smoke-test.

**Implementation**:
- Skills: `audience:` frontmatter tag added to all ~120 SKILL.md files (45 in `skills/` + 75 in `packages/`).
- Hooks and libs: `# SCOPE: os-only|project|both` comment header added to all 83 hooks and 137 Python libs.
- Future compatibility: `from __future__ import annotations` added to all Python files for Python 3.9 compatibility.

> **Note:** Python libs in `lib/` use `# scope:` (lowercase) comment headers, not `# SCOPE:` (uppercase) like hooks. The `from __future__ import annotations` annotation was added to 66 lib files for Python 3.9 compatibility.

The scope classification was deferred during the initial rules-to-hooks plan (decision ID 3086) and implemented during stabilization once the full agentic primitive audit was complete.

## Alternatives Considered

- **Directory-based separation**: Move os-only agentic primitives to an `internal/` directory. Rejected because it would break all existing imports, symlinks, and references.
- **Runtime filtering**: Check scope at execution time and skip inapplicable agentic primitives. Rejected because it adds overhead to every hook execution and still installs unnecessary files.
- **Ignore the problem**: Let users see all agentic primitives. Rejected because OS-internal tooling (release management, agentic primitive registration) is confusing and potentially harmful when run in user project context.

## Consequences

- `self-install.sh` can filter agentic primitives by scope during installation, reducing the installed footprint for user projects.
- `cos install` respects scope tags when resolving package contents.
- 5 skills were parameterized with `cognitive-os.yaml` config refs instead of hardcoded values, making them scope-aware.
- The scope audit revealed that many agentic primitives lacked clear audience boundaries, forcing explicit classification decisions for all 375+ agentic primitives.
- Adding `from __future__ import annotations` to all Python files was a side effect that improves forward compatibility with Python 3.9.

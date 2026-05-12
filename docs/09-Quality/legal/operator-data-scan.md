# Operator Personal Data Scan — HEAD Committed Files

**Date**: 2026-05-08
**Branch**: session/889b6132-adr-238-bug-tracking
**Scan scope**: all files tracked by git at HEAD

---

## Methodology

### Commands used

```bash
# Email
git grep -Il 'soporte\.esolutions@gmail\.com' HEAD

# Home path
git grep -Il '/Users/<operator-home>' HEAD \
  | grep -vE '^(scripts/audit-consumer-dependence\.sh|manifests/history-sanitization\.yaml)'

# Name variants
git grep -IlE '<operator-name-lower>|<operator-name-display>' HEAD

# UUID — checked all UUIDs in non-test tracked files; verified they are
# auto-generated agent session IDs in docs/01-Build-Log/history/ (excluded) or test fixtures (excluded)
git grep -IlE '[0-9a-f]{8}-...' HEAD \
  | grep -vE '^(docs/01-Build-Log/history/|tests/|docs/09-Quality/legal/pre-public)'
```

### Skip list applied

| Path pattern | Reason |
|---|---|
| `docs/01-Build-Log/history/` | Pre-sanitization archive — intentionally frozen |
| `docs/09-Quality/legal/pre-public-readiness-checklist.md` | The checklist itself |
| `tests/` | Test fixtures; excluded per task spec |
| `scripts/audit-consumer-dependence.sh` | Public-safe placeholder token list; real tokens must be supplied via private token file |
| `manifests/history-sanitization.yaml` | Legitimate replacement rules |
| `.git/`, `node_modules/`, `.cognitive-os/` | Non-source artifacts |

> **Note on `dashboard/.next/`**: `git grep` confirmed these build artifacts are **not tracked** by git. The initial filesystem grep (`grep -rIln`) surfaced them, but they do not appear in any git tree and carry no pre-public risk. They should be confirmed as gitignored (see recommendation below).

---

## Findings

### Category: operator email

| File | Line | Category | Detail |
|---|---|---|---|
| `CONTRIBUTING.md` | 237 | **Leak** | Public contact section lists `<operator-email>` as the maintainer email |

**Context** (redacted):

```markdown
- **Email**: `<operator-email>` for matters that are not
  appropriate for a public issue (security disclosure, licensing
  questions, etc.).
```

**Recommended fix**: Replace with a role-based or project-scoped address (e.g. `security@<project-domain>` for disclosure, or a GitHub Discussions link). Alternatively, replace with a generic placeholder and document the real address only in a private `MAINTAINERS-private.md` excluded from the public repo.

---

### Category: operator home path

| File | Tracked by git | Category |
|---|---|---|
| `dashboard/.next/**` | **No** — untracked build artifact | Not a leak (not committed) |

No tracked files contain `<operator-home-path>`.

**Recommended action**: Verify `dashboard/.next/` is covered by `.gitignore` to prevent accidental future commits.

---

### Category: operator name

| File | Line | Category | Detail |
|---|---|---|---|
| `scripts/validate_tier_filter.py` | 39 | **Leak** | Hardcoded absolute session-directory path derived from operator's home directory |

**Context** (redacted):

```python
_SESSION_DIR = Path(
    "~/.claude/projects/-Users-<operator-home-slug>-Projects-luum-luum-agent-os"
).expanduser()
```

The path segment `-Users-<operator-home-slug>-Projects-luum-luum-agent-os` is the Claude Code hashed project key, which is derived mechanically from the absolute path `/Users/<operator-home>/...`. Publishing this string leaks both the username and the local directory layout.

**Recommended fix**: Derive the path dynamically at runtime rather than hardcoding it:

```python
import subprocess

def _get_session_dir() -> Path:
    """Resolve the Claude Code project dir for this repo without hardcoding the home path."""
    cwd = Path(__file__).resolve().parent.parent  # repo root
    slug = str(cwd).replace("/", "-").lstrip("-")
    return Path(f"~/.claude/projects/{slug}").expanduser()

_SESSION_DIR = _get_session_dir()
```

Or, if this path is only used in tests/local validation, gate it behind an env override:

```python
_SESSION_DIR = Path(
    os.environ.get(
        "COS_SESSION_DIR",
        f"~/.claude/projects/{_derive_slug()}"
    )
).expanduser()
```

---

### Category: personal MCP server UUIDs

No personal MCP server UUIDs found in any tracked committed file outside the excluded paths. UUIDs found in `docs/01-Build-Log/history/` are auto-generated agent session IDs covered by the skip list. UUIDs in `tests/` are synthetic fixtures.

---

## Summary

| Category | Leak count | Legitimate count | Notes |
|---|---|---|---|
| Operator email | **1** | 0 | `CONTRIBUTING.md` line 237 |
| Operator home path | **0** | 0 | `dashboard/.next/` not committed |
| Operator name (embedded in path) | **1** | 0 | `scripts/validate_tier_filter.py` line 39 |
| Personal MCP UUIDs | **0** | 0 | No hits outside excluded paths |
| **Total** | **2** | **0** | |

---

## Recommended Actions (priority order)

1. **`scripts/validate_tier_filter.py`** — Replace hardcoded home-path-derived slug with dynamic derivation or an `os.environ` override. This is a code change with low blast radius.
2. **`CONTRIBUTING.md`** — Replace `<operator-email>` with a project role address or a GitHub Discussions link. Update the line before public release.
3. **`dashboard/.next/`** (preventive) — Confirm `.gitignore` entry covers this directory; if not, add it before first public push.

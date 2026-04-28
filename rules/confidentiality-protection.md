<!-- SCOPE: both -->
# Confidentiality Protection — IP Leak Prevention

## Purpose

Automatically prevent agents from exposing the developer's intellectual property when generating output. When agents read from other projects to extract patterns, they must never reference the source in generated artifacts (docs, code, commits).

## Rule (Always Active)

### Prohibited in Generated Output

Generated files (docs, README, CHANGELOG, markdown) MUST NOT contain:

| Violation Type | Examples | Detection |
|---|---|---|
| External project paths | `<external-project-root>/...` | Automatic — any path outside current project |
| Attribution phrases | "based on project-x", "adapted from client-y", "inspired by repo-z" | Pattern matching (EN+ES) |
| Internal repo URLs | `github.com/private-org/internal-repo` | Org name matching |
| Protected terms | Project names, client names configured in `confidentiality.yaml` | Term matching |

### Allowed in Conversation

Discussion of source projects in the conversation is permitted — the developer knows where patterns come from. The rule applies ONLY to files written to disk.

### Attribution Phrases (EN+ES)

English: "based on", "adapted from", "inspired by", "taken from", "copied from", "extracted from", "reused from", "ported from"

Spanish: "basado en", "extraído de", "modelo tomado de", "tomado de", "copiado de", "adaptado de", "reutilizado de", "inspirado en"

### How to Present Adapted Patterns

When adapting patterns from other projects:
- Present architectural decisions as original design for the current project
- Justify with technical merit, not precedent
- No comments like `// adapted from project-x` or `// based on internal-lib`
- No commit messages referencing source projects

### Configuration

Protected terms are configured in `.cognitive-os/confidentiality.yaml`:

```yaml
protected_terms:
  - term: "project-name"
    reason: "internal project reference"
protected_orgs:
  - "private-github-org"
scan_external_paths: true
```

## Enforcement

- **Hook**: `hooks/confidentiality-enforcer.sh` (PostToolUse on Edit|Write)
- **Lib**: `lib/confidentiality_scanner.py`
- **Scope**: Only scans `docs/`, `README*`, `*.md`, `CHANGELOG*` — not source code
- **Behavior**: BLOCK (exit 2) on violation

## Metrics

Violations logged to `.cognitive-os/metrics/confidentiality.jsonl`:

```json
{
  "timestamp": "ISO-8601",
  "file": "path/to/file",
  "violation_type": "attribution_phrase|external_path|protected_term|protected_org",
  "matched": "the matched text",
  "action": "block"
}
```

## Integration

| Rule | Relationship |
|---|---|
| Content Policy (`content-policy`) | Complementary — content-policy checks prohibited terms, confidentiality checks IP leaks |
| Agent Quality (`agent-quality`) | Agents that leak IP are producing incorrect output |
| Trust Score (`trust-score`) | IP leak should lower verification evidence score |
| Agent Security (`agent-security`) | Confidentiality is a subset of the broader security posture |

## Contextual Trigger

This rule is always active when the project-discovery package is installed.

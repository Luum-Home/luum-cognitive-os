<!-- SCOPE: both -->
<!-- TIER: 1 -->
# Local Privacy Hygiene

## Purpose

Prevent local operator details from leaking into commits. This rule covers
machine-specific paths, private project names, usernames, internal repository
names, and SSH key filenames that only make sense on one developer machine.

## Rule

Committed files MUST NOT contain local-only privacy details:

| Violation Type | Safer Replacement |
|---|---|
| Developer home paths | `$HOME`, `$PROJECT_DIR`, `<repo-root>`, or repo-relative paths |
| Local usernames | `<user>` or a role-neutral placeholder |
| Private project names | `<private-project>` or a domain-neutral example |
| Internal repository names | `<internal-repo>` or a public-safe placeholder |
| SSH key filenames | `<ssh-key-name>` or a generated fixture value |

Do not hardcode operator-specific patterns in Cognitive OS. Put them in a
gitignored local policy file instead.

## Configuration

Copy the committed template:

```bash
mkdir -p .cognitive-os/private
cp templates/local-privacy-patterns.example.txt .cognitive-os/private/local-privacy-patterns.txt
```

Then edit `.cognitive-os/private/local-privacy-patterns.txt` with private
patterns for the local environment:

```text
literal:<local-username>
literal:<private-project-name>
literal:<private-github-username>
literal:<internal-repo-name>
regex:github[.]com/<private-org>/<private-repo>
```

The private file is intentionally ignored by git.

## Enforcement

- **Script**: `scripts/check-local-privacy.sh`
- **Pre-commit**: `.githooks/pre-commit` runs the script with `--staged`
- **Full scan**: `scripts/check-local-privacy.sh --all`
- **Success marker**: `privacy-guard-ok`

Use the full scan before committing documentation or environment/bootstrap
changes:

```bash
scripts/check-local-privacy.sh --all
```

If a test fixture needs to show a blocked shape, add
`cos-allow-local-privacy-pattern` on the same line and keep the value fictional.

## Relationship to Existing Primitives

This rule complements:

- `scripts/check_absolute_paths.py` — generic home path portability
- `hooks/confidentiality-enforcer.sh` — generated-output confidentiality
- `hooks/content-policy.sh` — project content policy
- `.cognitive-os/private/blocked-strings.txt` — broader local blocked strings

`check-local-privacy.sh` owns the pre-commit privacy guard for local-only
operator and project details.

## Contextual Trigger

Triggers: local privacy, private paths, usernames, SSH keys, internal repos,
pre-commit privacy, content leak, operator data, project-specific patterns.

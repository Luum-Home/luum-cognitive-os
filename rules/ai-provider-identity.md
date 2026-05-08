<!-- SCOPE: both -->
<!-- TIER: 1 -->
# AI Provider Identity Guard

## Purpose

Prevent agents from inventing public email identities or commit trailers for AI
providers. Public commit authorship must remain a verified human/operator
identity; AI assistance is disclosed through COS provenance, session artifacts,
and explicit documentation — not through provider-looking email addresses.

## Rule

Generated files and commit messages MUST NOT contain:

- `Co-authored-by`, `Signed-off-by`, or similar authorship trailers naming an
  AI provider, model, assistant, bot, or agent as a public author.
- Provider-looking email addresses such as `noreply@<ai-provider-domain>`,
  `bot@<ai-provider-domain>`, `agent@<ai-provider-domain>`, or model-name local
  parts at provider domains.
- Replacement author identities for historical cleanup unless they are the
  configured verified operator identity.

Allowed:

- Verified human/operator identities in `manifests/ai-provider-identity-policy.yaml`.
- Private COS session/provenance artifacts that are not published as commit
  author metadata.
- Test fixtures under `tests/` that intentionally exercise the guard.

## Enforcement

- **Manifest**: `manifests/ai-provider-identity-policy.yaml`
- **Lib**: `lib/ai_provider_identity_guard.py`
- **CLI**: `scripts/ai-provider-identity-guard`
- **PostToolUse hook**: `hooks/ai-provider-identity-guard.sh`
- **Git hooks**: `.githooks/pre-commit` scans staged files; `.githooks/commit-msg`
  scans commit messages.

## Operator guidance

If an agent proposes a provider email, do not sanitize it into another fake
provider email. Replace it with the verified human/operator identity or remove
the trailer entirely and keep AI provenance in COS artifacts.

## Contextual Trigger

co-authored-by, signed-off-by, commit author, provider email, AI attribution,
public history, invented email, noreply provider

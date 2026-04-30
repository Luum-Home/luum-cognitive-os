# Codex live-session fixtures

Sanitized fixtures captured from a real Codex Desktop session JSONL stream on
2026-04-30. These are not synthetic API guesses: each file preserves the native
Codex wrapper shape (`session_meta`, `response_item`, or `event_msg`) and nested
`payload.type` value while replacing absolute paths, long prompts, and operator
content with stable placeholders.

The fixtures intentionally avoid user-specific paths and secrets. Use them to
verify ADR-081 without depending on the operator's `~/.codex/sessions` files.

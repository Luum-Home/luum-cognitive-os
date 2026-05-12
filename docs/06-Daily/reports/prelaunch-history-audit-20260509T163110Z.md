# Prelaunch History Audit

Status: `pass`

## Summary

- block: 0
- warn: 0
- info: 6
- findings: 6

## Findings

- **info** `private-key-material` on `history:1 commits` — private-key-material matched 1 historical commit(s); 0 need non-fixture review. Private key material must never be present in public history. All matches are fixture/example-like or reviewed audit context.
  - sample: `+ writeFile(t, dir, "key.pem", "-----BEGIN RSA PRIVATE KEY-----\ndata\n-----END RSA PRIVATE KEY-----")`
- **info** `env-assignment-secret` on `history:39 commits` — env-assignment-secret matched 39 historical commit(s); 0 need non-fixture review. Secret-like assignments require manual review or sanitization. All matches are fixture/example-like or reviewed audit context.
  - sample: `+ token = "private-token@example.invalid"`
- **info** `github-token` on `history:6 commits` — github-token matched 6 historical commit(s); 0 need non-fixture review. GitHub tokens must be removed from history. All matches are fixture/example-like or reviewed audit context.
  - sample: `+ token = "ghp_abcdefghijklmnopqrstuvwxyz0123456789"`
- **info** `openai-token` on `history:7 commits` — openai-token matched 7 historical commit(s); 0 need non-fixture review. Provider tokens must be removed from history. All matches are fixture/example-like or reviewed audit context.
  - sample: `+ secret = "sk-qwenSECRET1234567890"`
- **info** `aws-access-key` on `history:11 commits` — aws-access-key matched 11 historical commit(s); 0 need non-fixture review. AWS access keys must be removed from history. All matches are fixture/example-like or reviewed audit context.
  - sample: `+ "tool_input": {"command": "echo AKIAIOSFODNN7EXAMPLE && echo safe"},`
- **info** `absolute-claim-content` on `history:10 commits` — absolute-claim-content matched 10 historical commit(s); 0 need non-fixture review. Absolute public claims should be evidence-backed or softened. All matches are fixture/example-like or reviewed audit context.
  - sample: `+UNSURE ABOUT: <at least 1 item — "100% confident" is a red flag>`

## Policy

Read-only scan. License references are reported as context, not auto-sanitized.

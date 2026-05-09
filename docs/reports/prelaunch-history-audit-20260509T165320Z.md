# Prelaunch History Audit

Status: `pass`

## Summary

- block: 0
- warn: 0
- info: 9
- findings: 9

## Findings

- **info** `private-key-material` on `history:2 commits` — private-key-material matched 2 historical commit(s); 0 need non-fixture review. Private key material must never be present in public history. All matches are fixture/example-like or reviewed audit context.
  - sample: `+ "sample": "+ writeFile(t, dir, \"key.pem\", \"-----BEGIN RSA PRIVATE KEY-----\\ndata\\n-----END RSA PRIVATE KEY-----\")",`
- **info** `env-assignment-secret` on `history:40 commits` — env-assignment-secret matched 40 historical commit(s); 0 need non-fixture review. Secret-like assignments require manual review or sanitization. All matches are fixture/example-like or reviewed audit context.
  - sample: `+ "sample": "+ token = load_api_token(token_file)"`
- **info** `github-token` on `history:7 commits` — github-token matched 7 historical commit(s); 0 need non-fixture review. GitHub tokens must be removed from history. All matches are fixture/example-like or reviewed audit context.
  - sample: `+ "sample": "+ token = \"ghp_abcdefghijklmnopqrstuvwxyz0123456789\"",`
- **info** `openai-token` on `history:8 commits` — openai-token matched 8 historical commit(s); 0 need non-fixture review. Provider tokens must be removed from history. All matches are fixture/example-like or reviewed audit context.
  - sample: `+ "sample": "+ secret = \"sk-qwenSECRET1234567890\"",`
- **info** `aws-access-key` on `history:12 commits` — aws-access-key matched 12 historical commit(s); 0 need non-fixture review. AWS access keys must be removed from history. All matches are fixture/example-like or reviewed audit context.
  - sample: `+ "sample": "+ \"tool_input\": {\"command\": \"echo AKIAIOSFODNN7EXAMPLE && echo safe\"},",`
- **info** `personal-email` on `history:1 commits` — personal-email matched 1 historical commit(s); 0 need non-fixture review. Personal email addresses should be reviewed before public launch. All matches are fixture/example-like or reviewed audit context.
  - sample: `+ '> (`reviewer@gmail.com`) appears **2 times** in `git log -p`, not a leak.\n'`
- **info** `hostile-content` on `history:1 commits` — hostile-content matched 1 historical commit(s); 0 need non-fixture review. Hostile/internal phrasing in tracked history can create avoidable backlash. All matches are fixture/example-like or reviewed audit context.
  - sample: `+ AuditRule("hostile-message", "tone", "warn", r"\b(hate|drama|scam|fraud|trash|stupid|idiot)\b|\b(odio|bardo|quilombo|estafa|trucho|bardear)\b", "Hostile phrasing creates avoidable reputational risk."),`
- **info** `concealment-content` on `history:1 commits` — concealment-content matched 1 historical commit(s); 0 need non-fixture review. Concealment language should be reviewed in context. All matches are fixture/example-like or reviewed audit context.
  - sample: `+ AuditRule("hide-bypass-message", "quote_mine_risk", "warn", r"\b(hide|sneak|smuggle)\b", "Commit messages can be quote-mined as intent to conceal controls."),`
- **info** `absolute-claim-content` on `history:11 commits` — absolute-claim-content matched 11 historical commit(s); 0 need non-fixture review. Absolute public claims should be evidence-backed or softened. All matches are fixture/example-like or reviewed audit context.
  - sample: `+ "sample": "+UNSURE ABOUT: <at least 1 item \u2014 \"100% confident\" is a red flag>",`

## Policy

Read-only scan. License references are reported as context, not auto-sanitized.

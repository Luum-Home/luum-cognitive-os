---
type: quality-synthesis
source: docs/09-Quality/root/secret-detection.md
provenance: "Documents EnvGuard, the suite of tools that keeps environment-variable usage and definitions in sync and blocks leaked secrets before they reach source or Engram."
---

## What it is

Reference doc for EnvGuard: a three-part system (pre-Engram memory scanner, PostToolUse secret-detector hook, and `/secret-audit` skill) plus a coding-standards rule file that together keep env-var references, definitions, and hygiene consistent across the project.

## Key mechanics

- **Memory Scanner** (`lib/memory_scanner.py`) runs before any `mem_save` persists content to Engram, checking twelve threat pattern categories plus invisible Unicode characters used to hide malicious instructions. Categories include: instruction-override and role-hijacking phrasing, rule-bypass wording, exfiltration of secret env vars via outbound network calls, reads targeting `.env`/credential files/`.netrc`/`.pgpass`/`.npmrc`, and backdoor patterns targeting authorized-keys files or user key directories. On any match, the save is blocked and all violations are reported together (no silent truncation).
- **Secret Detector Hook** (`hooks/secret-detector.sh`) runs PostToolUse on `Edit|Write` to `.ts`/`.go`/`.java` source files. It scans for env-var reference patterns (`process.env.X`, `os.Getenv("X")`, `System.getenv("X")`, `@Value("${X}")`), cross-references them against `.env`, `.env.example`, `docker-compose.yml`, `dev.env`, and config files, and warns (logging to `.cognitive-os/metrics/missing-secrets.jsonl`) if a referenced var has no definition anywhere. Skips `.md`/`.json`/`.yaml`/`.yml`/`.lock`/`.sum`/`.sh` and anything under `.cognitive-os/` or `.claude/`.
- **Secret Hygiene Rules** (`.cognitive-os/rules/secret-hygiene.md`): every new env var must land in `.env.example`; never hardcode secrets; use `PROVIDER_*` naming for external credentials; Docker Compose env sections must mirror `.env.example`; mock flags follow `PROVIDER_MOCK`.
- **`/secret-audit` skill** does a full cross-reference across Go/TS/Java services, flagging used-but-undefined, defined-but-unused, and hardcoded values.

## Relations & where used

- Registered in `settings.local.json` under `PostToolUse` matcher `Edit|Write`.
- Rule loaded contextually on `secret|env|credential` triggers.
- Skill listed in CATALOG.md as `/secret-audit`.
- Complements the broader security-hook set described in `hook-security-profiles.md` (secret-detector.sh is active in every profile, including minimal).

## Status / caveats

None noted; the doc is internally consistent and describes a currently-implemented system.

# cos-dispatch: Configuration Schema

## Config File Precedence

1. CLI flags (highest priority)
2. Environment variables (`COS_DISPATCH_*`)
3. Project config (`cos-dispatch.toml` in project root)
4. Global config (`$XDG_CONFIG_HOME/cos-dispatch/config.toml`)
5. Built-in defaults (lowest priority)

## Full Schema

```toml
[dispatch]
provider = "auto"          # "auto", "claude", "codex", "gemini", "cursor", "devin"
parallel = true            # use parallel executor (vs sequential)
log_level = "info"         # "debug", "info", "warn", "error"
timeout_ms = 5000          # per-validator timeout

[dispatch.pools]
cpu_workers = 0            # 0 = runtime.NumCPU()
io_workers = 0             # 0 = runtime.NumCPU() * 2
git_workers = 1            # keep at 1 to avoid index lock contention

# Cognitive OS integration
[cognitive_os]
config_path = "cognitive-os.yaml"
metrics_dir = ".cognitive-os/metrics"
session_dir = ".cognitive-os/sessions"

# Transformer definitions
[[transformers]]
name = "secret-redactor"
phase = "pre"
priority = 10
enabled = true

[[transformers]]
name = "symlink-resolver"
phase = "pre"
priority = 20
enabled = true

[[transformers]]
name = "result-truncator"
phase = "post"
priority = 10
enabled = true
[transformers.config]
max_chars = 5000
head_chars = 2000
tail_chars = 1000
never_truncate = ["FAIL", "ERROR", "panic", "PASS", "coverage:"]

[[transformers]]
name = "inject-phase-context"
phase = "post"
priority = 20
enabled = true

# Plugin definitions (existing bash hooks wrapped as plugins)
[[plugins]]
name = "session-init"
command = "hooks/session-init.sh"
events = ["session_start"]
category = "io"
timeout_ms = 3000

[[plugins]]
name = "infra-health"
command = "hooks/infra-health.sh"
events = ["session_start"]
category = "io"
async = true

[[plugins]]
name = "semgrep-scan"
command = "hooks/semgrep-scan.sh"
events = ["after_tool"]
tools = ["Edit", "Write"]
category = "io"
async = true

[[plugins]]
name = "error-pipeline"
command = "hooks/error-pipeline.sh"
events = ["after_tool"]
tools = ["Bash"]
category = "io"

# Validator overrides
[overrides]
disabled_codes = []        # error codes to suppress globally

# Pattern tracking (auto-improvement)
[patterns]
enabled = true
db_path = ".cognitive-os/patterns.db"
min_count = 3              # minimum occurrences before flagging
analysis_interval = "session_end"  # or cron expression

[patterns.auto_generate]
enabled = true
output_dir = "generated/"
confidence_threshold = 0.7
require_review = true      # artifacts start with enabled = false
max_per_session = 3        # max artifacts generated per session
```

## Environment Variables

| Variable | Maps to | Example |
|----------|---------|---------|
| `COS_DISPATCH_PROVIDER` | `dispatch.provider` | `claude` |
| `COS_DISPATCH_PARALLEL` | `dispatch.parallel` | `true` |
| `COS_DISPATCH_LOG_LEVEL` | `dispatch.log_level` | `debug` |
| `COS_DISPATCH_TIMEOUT` | `dispatch.timeout_ms` | `5000` |
| `COS_DISPATCH_PATTERNS_ENABLED` | `patterns.enabled` | `true` |

## CLI Flags

```bash
cos-dispatch [flags]

Flags:
  --provider string     Override provider detection (claude|codex|gemini|cursor|devin)
  --config string       Path to config file (default: auto-discover)
  --event string        Event type override (for providers that don't include it in JSON)
  --log-level string    Log level (debug|info|warn|error)
  --disable string      Comma-separated validator names to disable
  --dry-run             Log decisions without blocking
  --version             Print version and exit

Subcommands:
  cos-dispatch init      Initialize config files for current project
  cos-dispatch doctor    Verify installation and hook wiring
  cos-dispatch review    Review auto-generated artifacts
  cos-dispatch stats     Show execution statistics from pattern DB
```

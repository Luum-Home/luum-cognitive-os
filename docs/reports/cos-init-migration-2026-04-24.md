# Research — cos-init.sh Migration to Python (2026-04-24)

**Type**: Research-only (per ADR-069)
**Decision Status**: Awaiting operator triage
<!-- decision-deferred: Research-only report; operator triage is still required before recording decision/cos-init-migration. -->
**Implementation NOT performed**

## TL;DR

`cos-init.sh` is 666 lines with 6 named functions. The logic is moderate-complexity bash: mostly `cp`/`mkdir`/`chmod` orchestration with ~19 lines of `awk`/`sed`/`jq`/`grep` text processing — none of it deeply tricky. The largest unknowns are: (1) subprocess delegation to `generate-project-settings.sh` and `merge-settings.sh`, which the Python rewrite cannot easily absorb without also rewriting those scripts; (2) a Bash 3.x compatibility constraint that does not translate to Python but must be verified still relevant; and (3) the absence of any direct unit tests for `cos-init.sh` itself — parity can only be verified behaviorally via subprocess invocation. A strangler-fig migration is recommended over a big-bang rewrite because it lets each chunk be verified against the existing shell behavior before the next chunk is replaced.

---

## Inventory

| Section | Lines | Responsibility | Complexity |
|---|---|---|---|
| Arg parsing + mode remap | 1–78 | CLI flags `--default`/`--full`, legacy remap, harness flag | Low — pure case/shift |
| Harness detection | 80–103 | Delegates to `settings-driver.sh::cos_detect_harness` | Low — delegates to lib |
| Scope filter setup | 105–139 | `scope_allows()`: reads first 3 lines of file for `SCOPE:` header | Medium — `grep | awk | tr` pipeline |
| Skill scope filter | 141–160 | `skill_scope_allows()`: reads `SKILL.md` frontmatter `audience:` field | Medium — `grep | awk | tr` pipeline |
| Stack + project detection | 167–221 | Reads `package.json`, `go.mod`, `pyproject.toml`, `Cargo.toml`, `pom.xml` | Medium — `jq` + `sed` + `grep` chains |
| Rule installation | 276–537 | Copy `.md` rules to 2 destinations, filter by profile tier | Low — `cp` + bash array loop |
| Hook installation | 318–355 | Copy `.sh` hooks, `chmod +x`, copy `_lib/` | Low — `cp` |
| Skill installation | 357–407 | Copy skill dirs + create relative symlinks in `.claude/skills/` | Low — `cp -r` + `ln -s` |
| Template installation | 409–416 | Copy `templates/*.md` | Low — `cp` glob |
| `cognitive-os.yaml` generation | 418–468 | Heredoc with detected stack; only if file absent | Medium — `echo -e | sed` for blank-line removal |
| Settings file generation | 540–575 | Delegates to `generate-project-settings.sh` + `merge-settings.sh` via subprocess | High — external process, `jq` required |
| Install metadata | 577–607 | Writes `.cognitive-os/install-meta.json` via heredoc; `git describe` for version | Low — heredoc + `git` call |
| Global registry | 609–614 | Sources `cos-registry.sh` and calls `cos_registry_register` | Low — sourced lib call |
| `.gitignore` patching | 616–652 | Appends missing patterns idempotently | Low — `grep -qF` + append |
| Summary output | 654–666 | Prints counts to stdout | Trivial |

---

## Hot Spots (awk/sed/jq)

| Line(s) | Expression | Parses | Python Equivalent | Difficulty |
|---|---|---|---|---|
| 128 | `grep -m1 -oE '(# SCOPE:\|<!-- SCOPE:) [a-zA-Z_/-]+' \| awk '{print $NF}' \| tr -d ' '` | SCOPE header in first 3 lines of any file | `re.search(r'(?:# SCOPE:\|<!-- SCOPE:)\s+(\S+)', first_3_lines)` | Trivial |
| 152 | `grep -E '^(audience\|scope):' \| head -1 \| awk -F: '{print $2}' \| tr -d " '\"\r"` | YAML-like frontmatter field in SKILL.md | `re.search(r'^(?:audience\|scope):\s*(.+)', text, re.M)` then `.strip("'\" \r")` | Trivial |
| 175 | `jq -r '.name // empty' package.json` | Node project name from package.json | `json.loads(path.read_text()).get('name', '')` | Trivial — stdlib `json` |
| 178 | `head -1 go.mod \| sed 's/module //' \| sed 's\|.*/\|\|'` | Go module name → last path component | `go_mod.splitlines()[0].removeprefix('module ').rsplit('/',1)[-1]` | Trivial |
| 181 | `grep '^name' pyproject.toml \| head -1 \| sed 's/.*= *"//' \| sed 's/".*//'` | Python project name from pyproject.toml | `tomllib.loads(...)['project']['name']` or regex fallback | Low — `tomllib` (stdlib 3.11+) |
| 433 | `echo -e "$yaml_stack" \| sed '/^$/d'` | Removes blank lines from a generated multi-line string | `'\n'.join(line for line in yaml_stack.splitlines() if line.strip())` | Trivial |
| 480 | `grep -A1 '^efficiency:' \| grep 'profile:' \| awk '{print $2}' \| tr -d "'\"\r"` | `efficiency.profile` value from `cognitive-os.yaml` | `yaml.safe_load(path.read_text()).get('efficiency',{}).get('profile','')` | Low — `pyyaml` |
| 586 | `git describe --tags --abbrev=0 \| sed 's/^v//'` | Strips leading `v` from semver tag | `subprocess.run(['git','describe','--tags','--abbrev=0']).stdout.lstrip('v')` | Trivial |
| 642 | `grep -qF "$pattern" .gitignore` | Idempotency check before appending to `.gitignore` | `pattern in path.read_text()` | Trivial |

---

## External Dependencies

| Tool | Used for | Required? | Python Equivalent |
|---|---|---|---|
| `bash` (3.x compat) | Script runtime | Eliminated by rewrite | n/a |
| `jq` | Parse `package.json` name; invoke `generate-project-settings.sh` | Optional (fallback path exists at line 570) | stdlib `json` |
| `git` | `git describe` for version; `git rev-parse --short HEAD` | Soft — falls back to `VERSION` file | `subprocess.run` or `gitpython` |
| `head` / `grep` / `awk` / `sed` / `tr` | Text extraction (all hotspots above) | Internal — eliminated by Python stdlib | `re`, `str.split`, `json`, `tomllib`, `yaml` |
| `cp` / `chmod` / `ln -s` / `mkdir -p` | File installation | Core | `shutil.copy2`, `os.chmod`, `os.symlink`, `Path.mkdir` |
| `generate-project-settings.sh` | Generate harness `settings.json` | High — critical path; fallback is raw `cp` | Must remain shell OR be co-migrated |
| `merge-settings.sh` | Merge COS hooks into existing `settings.json` | High — critical for existing projects | Same constraint as above |
| `cos-registry.sh` | Register install in global registry | Soft — `jq` gated; no-op if absent | Could be absorbed as Python module |
| `settings-driver.sh::cos_detect_harness` | Detect claude vs codex harness | Required | ~10 lines of Python path/env checks |
| `date -u` | ISO-8601 timestamp for `install-meta.json` | Required | `datetime.now(timezone.utc).isoformat()` |

---

## Parity Surface

| Behavior | Current Bash Mechanism | Test Exists? | Parity Verification Strategy |
|---|---|---|---|
| Project name detection | `jq .name` / `head go.mod \| sed` / `grep pyproject.toml \| sed` / `basename $PWD` | No direct unit test | Unit test: fixture dirs with each manifest type; assert `detect_project_name()` returns expected string |
| Stack detection | `[ -f package.json ]` etc. for node/go/python/rust/java | `tests/integration/test_install_scope.py` exercises install but not detection in isolation | Unit test: fixture dirs; assert `detect_stack()` returns expected list |
| Scope filtering | `scope_allows()` reads first 3 lines for `# SCOPE:` tag | `test_install_scope.py` exercises end-to-end via subprocess | Unit test: parametrize over tagged/untagged/os-only files |
| Skill audience filtering | `skill_scope_allows()` reads `SKILL.md` frontmatter | `test_install_scope.py` partial coverage | Unit test: fixture `SKILL.md` with each audience value |
| Rule/hook/skill installation | `cp` + `chmod` + `ln -s` | `test_install_scope.py`, `test_installer.py` — subprocess based | Behavioral: run Python module in tmpdir, assert file tree matches bash output |
| `cognitive-os.yaml` generation | heredoc template; only if file absent | No | Golden snapshot test: run both bash and Python in identical tmpdir, diff output |
| `cognitive-os.yaml` not overwritten (idempotency) | `[ ! -f "cognitive-os.yaml" ]` guard | No | Idempotency test: run twice, assert file unchanged on second run |
| Settings file merge | Delegates to `generate-project-settings.sh` + `merge-settings.sh` | `test_installer.py` indirectly | Subprocess golden snapshot; or defer to those scripts via subprocess |
| `.gitignore` patching (idempotent) | `grep -qF` before append | No | Unit test: pre-populated `.gitignore`, assert no duplicate entries |
| Symlink layout `.claude/skills/<name>` → `../../.cognitive-os/skills/cos/<name>` | `ln -s` relative path | `test_install_scope.py` verifies installation | Assert `os.readlink()` returns correct relative target |
| Version detection | `git describe` → `VERSION` file → `git rev-parse` | No | Unit test mock `git` subprocess; assert fallback chain |
| Self-hosting guard | `[ "$PROJECT_DIR" = "$COS_SOURCE_DIR" ]` | No | Unit test: assert `CoSInit` raises when called from COS source dir |

---

## Decision Points (operator answers needed)

| # | Decision | Options | Recommendation |
|---|---|---|---|
| 1 | YAML lib | `pyyaml` (3rd party, popular) vs `ruamel.yaml` (preserves comments) vs hand-rolled `re` | `pyyaml` — `cognitive-os.yaml` is read, not round-tripped; comment preservation not needed for reads |
| 2 | `generate-project-settings.sh` and `merge-settings.sh` | Co-migrate in same PR vs keep as subprocess calls vs defer to follow-up | Defer: both scripts have their own logic and tests; keep subprocess calls in the Python layer for now |
| 3 | `settings-driver.sh::cos_detect_harness` | Inline the 10-line logic into Python vs keep sourcing the shell lib | Inline: the function is trivial and the shell dep is only 10 lines; eliminates a subprocess |
| 4 | Backward compat shim | Keep `cos-init.sh` as thin `exec python3 scripts/cos_init.py "$@"` shim vs hard-cut | Keep shim: CI, `install.sh`, and user docs all reference `bash scripts/cos-init.sh`; a shim is zero-risk |
| 5 | Subprocess wrapper | `subprocess.run` (stdlib) vs `sh` library | `subprocess.run`: no extra dependency; `sh` adds convenience but is another dep |
| 6 | `tomllib` vs regex for `pyproject.toml` | stdlib `tomllib` (Python 3.11+) vs `tomli` backport vs `re` | `tomllib` with `tomli` fallback for 3.9/3.10; eliminates the fragile `sed` pipeline |
| 7 | Test strategy | Behavior tests via subprocess (run Python against tmpdir) vs unit tests on internal functions | Both: unit-test each detection/filtering function independently; behavior tests invoke the module via subprocess for end-to-end parity checks |
| 8 | Migration ordering | Big-bang (full rewrite at once) vs strangler-fig (function-by-function, shim delegates) | Strangler-fig: replace one function at a time, validate parity per chunk before proceeding; reduces blast radius |
| 9 | Bash 3.x compat constraint | The comment at line 12 says "no associative arrays, no bash 4+ features" — this is a consumer constraint | Verify: does any CI matrix still test on macOS default bash (3.2)? If Python replaces it, constraint becomes irrelevant |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Subtle behavioral diff in `cognitive-os.yaml` heredoc generation (whitespace, YAML indentation) | Medium | High — malformed YAML breaks all COS sessions in new installs | Golden snapshot test: run bash and Python side-by-side in identical tmpdir, binary-diff outputs |
| Settings file merge regression (`merge-settings.sh` still called via subprocess) | Low | High — existing `.claude/settings.json` corrupted or hooks lost | Keep subprocess delegation; do not absorb `merge-settings.sh` into Python rewrite |
| `tomllib` not available on Python < 3.11 (COS targets 3.9+) | Medium | Medium — `pyproject.toml` name detection silently falls back to `basename` | Add `tomli` as optional dep or use `re` fallback matching current sed behavior |
| Symlink relative path calculation off-by-one | Low | High — skills invisible to Claude Code discovery | Assert `os.readlink()` target in integration test before merging |
| Latency regression on first install | Low | Low — bash `cp` loops vs Python `shutil`; Python startup cost ~50ms | Acceptable; measure with `time` on a 50-skill install before release |

---

## Recommended Path Forward

**Strangler-fig migration with side-by-side parity testing per chunk.**

Rationale: `cos-init.sh` is invoked by `install.sh`, CI, and documented in user-facing docs. A hard-cut big-bang rewrite risks regressions in the settings merge path (which delegates to two other scripts not in scope). The strangler-fig approach:

1. Create `scripts/cos_init.py` with the full Python implementation behind a `--python` flag (or always, with `cos-init.sh` reduced to a `python3` exec shim).
2. Add golden snapshot tests that run both bash and Python against identical fixture dirs and diff their output trees.
3. Migrate function by function, verifying parity after each chunk.
4. Once all parity tests pass, make `cos-init.sh` a thin `exec python3` shim.
5. Remove the shim in a subsequent sprint after one release cycle with no regressions.

This avoids the need to solve the `generate-project-settings.sh`/`merge-settings.sh` dependency in the same PR.

---

## Estimated Cost

| Item | Estimate |
|---|---|
| Python LOC | ~300 bash → ~350–420 Python (more explicit, typed, docstrings) |
| Unit tests added | ~25–35 (one per parity surface row, parametrized) |
| Integration / behavior tests added | ~8–12 (golden snapshot per mode × scope × harness combination) |
| Hours (realistic) | 6–10h implementation + 4–6h parity testing iteration = **10–16h total** |

The parity testing iteration is the dominant cost, not the implementation. The `cognitive-os.yaml` generation and settings merge paths require the most care and will consume the majority of that time.

---

## Open Questions for Operator

1. Is Python 3.9+ the guaranteed minimum, or can the rewrite assume 3.11+ (which gives `tomllib` stdlib)?
2. Is `generate-project-settings.sh` in scope for co-migration, or should the Python layer keep the subprocess delegation?
3. Should the shim strategy keep `cos-init.sh` permanently (for users who call it directly) or is a deprecation timeline acceptable?
4. Does any CI job still test on macOS system bash (3.2)? If yes, the Bash 3.x compat note at line 12 is load-bearing and Python migration unblocks that constraint.
5. Is `pyyaml` already in `uv.lock` / `pyproject.toml`? If not, adding it needs a dep approval step.

---

## What this report does NOT do

- Does NOT migrate. The Python implementation is a follow-up session.
- Does NOT prescribe the choice — only documents the trade-offs.
- Does NOT cover `generate-project-settings.sh` or `merge-settings.sh` — those are separate scripts with their own complexity and are treated as subprocess dependencies here.

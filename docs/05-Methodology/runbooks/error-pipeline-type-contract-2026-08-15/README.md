# error-pipeline / error-learning — the payload type contract

**2026-08-15.** Patch delivered as a file because `hooks/**` is protected by
`protected-config-write-guard`. It applies clean and it is demonstrated, not
argued.

```
git apply --check -p1 docs/05-Methodology/runbooks/error-pipeline-type-contract-2026-08-15/error-pipeline-type-contract.patch
```

---

## The defect

`hooks/error-pipeline.sh:39` and `hooks/error-learning.sh:18` decided whether a
command failed by reading `exit_code` with a permissive default:

```bash
EXIT_CODE=$(echo "$INPUT" | jq -r '.exit_code // "0"')
[ "$EXIT_CODE" = "0" ] && exit 0
```

The harness never sends that field. So `EXIT_CODE` was the literal `"0"` on
every invocation and both hooks exited on their first branch, every time.
`packages/skill-governance/hooks/skill-tracker.sh:34` has the same read.

`error-learning.sh` had a second bug stacked on the first:

```bash
[ "$EXIT_CODE" = "0" ] || [ "$EXIT_CODE" = "" ] && exit 0
```

By left associativity that is `(A || B) && exit 0` — it does what its author
meant only by accident, and with `EXIT_CODE` pinned to `"0"` it was an
unconditional `exit 0`.

## The contract, measured

Everything below comes out of one command:

```
python3 docs/05-Methodology/runbooks/error-pipeline-type-contract-2026-08-15/verify_type_contract.py
```

```
transcripts scanned:      57
tool results total:       2686
Bash results:             1962
  object  (ran ok):       1837
  string  (failure):      125
    'Error: Exit code N': 50   <- command ran and failed
    other 'Error: ...':   75   <- command NEVER RAN (gate/permission)
'exit_code' field seen:   0   <- the field the old hooks read
```

**Failure is signalled by a change of type, not by a field.** `tool_response` is
an object when the tool ran and a string prefixed `Error:` when it did not
succeed. Two different events hide inside that string, and the larger of the two
is us:

| shape | meaning | count |
|---|---|---|
| object `{stdout,stderr,interrupted,isImage,noOutputExpected}` | ran, succeeded | 1837 |
| string `Error: Exit code N` | ran, exited N | 50 |
| string `Error: …` (anything else) | **never ran** — PreToolUse gate of this OS (64), permission denial (3), model unavailable (4), explicit guard block (4) | 75 |
| absent / other type | the harness contract moved | 0 |

Third, independent confirmation, from live telemetry rather than transcripts:
`.cognitive-os/metrics/aci-observations.jsonl` recorded `exit_code: 0` in
**4248 of 4248** rows — its producer reads the same phantom field — while its
`output_excerpt` carries the serialized `{stdout,stderr,interrupted,isImage,
noOutputExpected}` object. That is what proves the hook's stdin envelope has the
same shape as the transcript's `toolUseResult`, which is the one link a
transcript-only measurement cannot close.

## Why this shape of fix, and not another

**Why not `.tool_response.exit_code`.** That was the previous proposal. It moves
the read from a field the harness never sends to another field the harness never
sends: zero occurrences of `exit_code` at any nesting level, for any tool, in
2686 results. It would have turned the hooks green in the test suite while
leaving them exactly as dead.

**Why four states and not two.** `absent` must not collapse into `ok`. Reading
absence as success is the entire defect; a fix that keeps a permissive fallback
just relocates it. When the payload has no readable `tool_response`, the hooks
now write to `payload-contract-drift.jsonl` and bail. That row is an alarm about
the OS's ability to observe, and it is the thing that will fire the next time
the harness moves a field — instead of another silent decade of `exit 0`.

**Why gate blocks get their own stream.** 75 of 125 Bash "failures" are this OS
refusing its own commands. They carry no exit code, no stdout and no stderr,
because nothing ran. Feeding them to `error-learning.jsonl` teaches the
self-improvement loop from our own guardrails, and feeding them to Phase 3 makes
auto-repair try to fix a `BLOCK` verdict — a `go test` refused by a gate would
have classified as `TEST_FAILURE` and dispatched a repair for a test that never
executed. They go to `gate-blocks.jsonl` instead, owned by `error-pipeline` so
the two hooks do not double-log.

**Why a shared `hooks/_lib/tool-outcome.sh` and not three inline copies.** Three
hooks need the same classification, and `packages/skill-governance/hooks/_lib` is
already a symlink to `hooks/_lib`, so one file reaches all of them. Three copies
of a contract is how a contract drifts.

## What the patch changes

| file | change |
|---|---|
| `hooks/_lib/tool-outcome.sh` | **new.** `classify_tool_outcome` → `TOOL_OUTCOME` ∈ {ok, failed, blocked, absent}, `TOOL_EXIT_CODE`. Plus `record_payload_contract_drift`. |
| `hooks/error-pipeline.sh` | drops the phantom read; `ok`→exit, `absent`→drift row, `blocked`→`gate-blocks.jsonl`, only `failed` continues to classification and repair dispatch |
| `hooks/error-learning.sh` | same, plus removes the `(A \|\| B) && exit 0` construct; `exit_code` is emitted as `null` rather than an empty token when the failure carries no number |
| `packages/skill-governance/hooks/skill-tracker.sh` | see below |

### The third BLIND: `skill-tracker.sh`

Same phantom read, **different payload shape** — it matches on `Agent`/`Skill`,
not `Bash`, so it does not get a copy of the Bash classifier. Measured over 182
Agent/Skill results:

- object with `.status`: `async_launched` (150), `completed` (5)
- object with `.success` (Skill invocations): 10
- string: 17
- `exit_code`: 0 occurrences, same as everywhere else

`classify_tool_outcome` already branches on `.success` and `.status` for the
object case, so one function covers both shapes. Two behaviour changes fall out:

1. A `blocked` launch no longer counts as a skill failure. The skill did not
   fail; the launch was refused before it ran.
2. **A second defect, found while patching.** The failure detector grepped the
   *entire serialized payload* for `error|failed|rejected|exception|timed out|
   permission denied`. Agent payloads embed the full `prompt`, and agent prompts
   routinely contain those words as ordinary subject matter — so healthy runs
   were being posted to Engram as skill failures. The grep is now scoped to
   payloads already classified `failed` or `blocked`, and reads a bounded prefix
   rather than the whole blob.

## Applying it

```bash
cd <repo root>
git apply --check -p1 docs/05-Methodology/runbooks/error-pipeline-type-contract-2026-08-15/error-pipeline-type-contract.patch
COS_ALLOW_PROTECTED_CONFIG_WRITE=1 git apply -p1 docs/05-Methodology/runbooks/error-pipeline-type-contract-2026-08-15/error-pipeline-type-contract.patch
```

`hooks/**` is protected and the env var is only reachable from a human shell —
the guard runs in its own process, before the agent's command. No bypass was
attempted.

## Verification after applying

**1. The demonstration must stay green.**

```bash
python3 docs/05-Methodology/runbooks/error-pipeline-type-contract-2026-08-15/verify_type_contract.py --limit 400
```

Exit 0. It replays real captured payloads through both the unpatched and the
patched hooks with `CLAUDE_PROJECT_DIR` redirected to a throwaway directory, and
checks six properties: no `exit_code` anywhere, both type-forms present, the
classifier agrees with the observed shape on all 1962 payloads with **0
mismatches**, the unpatched hooks write **0** rows, the patched hooks write more
than 0, and gate blocks land in their own stream. Recorded run:

```
classifier over every harvested payload:
  {'ok': 1837, 'blocked': 75, 'failed': 50}   mismatches: 0

replay of 400 real payloads through each hook:
  [before]
    hooks/error-pipeline.sh      error-learning=   0  gate-blocks=   0  drift=  0
    hooks/error-learning.sh      error-learning=   0  gate-blocks=   0  drift=  0
  [after]
    hooks/error-pipeline.sh      error-learning=   1  gate-blocks=  29  drift=  0  types={'TEST_FAILURE': 1}
    hooks/error-learning.sh      error-learning=  16  gate-blocks=   0  drift=  0  types={'UNKNOWN_ERROR': 15, 'TEST_FAILURE': 1}
```

**2. The BLIND count must be zero.**

```bash
python3 scripts/audit_payload_field_contracts.py; echo $?
```

Before: `BLIND 3` / exit 1. After: `BLIND 0` / exit 0. The ratchet that keeps it
there is `tests/audit/test_instrument_productivity.py::test_no_hook_reads_the_phantom_exit_code`,
parametrized over all three hooks, which arms itself the moment
`hooks/_lib/tool-outcome.sh` exists — so a fourth blind read cannot enter
quietly.

**3. Live canary, end to end.** Note the run count, run a command that fails for
real, note it again:

```bash
grep -c error-pipeline .cognitive-os/metrics/hook-timing.jsonl
ls /nonexistent-canary
grep -c error-pipeline .cognitive-os/metrics/hook-timing.jsonl
wc -l .cognitive-os/metrics/gate-blocks.jsonl
```

`ls /nonexistent-canary` produces `Error: Exit code 1` → `failed` → the hook runs
its full path instead of exiting on line 41.

## Known limitation, stated rather than hidden

When a Bash command fails, the harness sends **only** the string
`Error: Exit code N`. No stdout, no stderr, nothing else. So a post-fix
`error-learning.jsonl` row carries the command and its classification, but the
`error` field can only ever hold that string. Classification by command pattern
(`pytest`, `go build`, `eslint`, …) still works and is what produces the
`TEST_FAILURE` / `BUILD_ERROR` / `LINT_ERROR` types. Content-based classification
does not, and cannot, until the harness starts sending output on failure. Any
downstream consumer expecting error text in that field should be read with that
in mind.

## What in the original brief did not reproduce

Recounted before citing, per the brief's own instruction. Four numbers it
carried forward were wrong:

| claim | measured | command |
|---|---|---|
| 1829 Bash results, 170 failures, 8.5% | **1962** results, **125** failures, **6.4%** | `verify_type_contract.py` |
| 97 PreToolUse gate blocks | **75** | same |
| 12 characterization tests pin `.exit_code` | **2 of 12** (one parametrized function over two hooks); the other 10 pin unrelated lote-34 findings | `pytest tests/audit/test_instrument_productivity.py --collect-only -q` |
| `hooks/*.sh` are symlinks into `packages/*/hooks/` | `hooks/error-pipeline.sh` and `hooks/error-learning.sh` are **regular files**; only `packages/skill-governance/hooks/_lib` is a symlink (→ `hooks/_lib`) | `readlink -f` |

The 170 figure is real but is every string-typed `toolUseResult` across **all**
tools, not Bash. Scoped to Bash it is 125. The direction of the finding held; the
arithmetic did not, which is why the patch was rebuilt from a fresh measurement
rather than from the numbers.

One documentation defect falls out of this and is worth its own entry in the
pending-truth ledger: `docs/04-Concepts/architecture/agentic-mastery-operations.md`
documents the payload as `{"tool_response": {"content": "...", "exit_code": 1}}`.
That shape occurs zero times in 2686 real results. It is where the phantom field
came from, and it is still there telling the next reader the same thing.

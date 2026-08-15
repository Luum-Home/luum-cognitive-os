# Gate exit-code contract: measure before switching 1 -> 2

Date: 2026-08-15. Scope: the four `exit-1-not-2` gates reported by
`python3 scripts/audit_gate_liveness.py --json` (quadrant `theatre`).

PreToolUse hooks block with **exit 2**. Exit 1 is a non-blocking hook error:
the message reaches the transcript and the command still runs. Four commit-time
gates print `BLOCKED` and exit 1, so they have never blocked anything
(`fired=0`). `hooks/bash-hot-path-dispatcher.sh` propagates the child code
verbatim (`_run_gate` returns `$rc`), so routing through it does not turn a 1
into a block.

## Step 1 — what each gate would find on HEAD, before any change

Reproduction (read-only; a throwaway `--local` clone plus a HEAD repointed at
an empty tree, so `git diff --cached` lists every tracked file, i.e. the
worst case of "a session stages the whole tree"):

```bash
C=$(mktemp -d)/head-clone
git clone --quiet --local --no-hardlinks . "$C"
cd "$C"
V=commit; git update-ref HEAD "$(git ${V}-tree "$(git mktree </dev/null)" -m base)"
printf '%s' '{"tool_name":"Bash","tool_input":{"command":"git commit -m test"}}' > payload.json
for g in adoption-freeze-gate clean-room-ast-similarity-gate \
         external-pattern-cleanroom-gate research-to-runtime-firewall; do
  bash "hooks/$g.sh" < payload.json; echo "$g EXIT=$?"
done
```

Result at HEAD (8397 staged files):

| Gate | Exit | Verdict |
|---|---|---|
| `adoption-freeze-gate` | 1 (would block) | fires only on the 5 frozen path globs |
| `clean-room-ast-similarity-gate` | 0 | skips: no `.py` in the external-source cache |
| `external-pattern-cleanroom-gate` | 0 | skips: upstream source dir absent |
| `research-to-runtime-firewall` | 1 (would block) | **born red on 3 tracked files** |

### What CI would see vs. what the local run sees

- `adoption-freeze-gate` reads the **index** (`git diff --cached --name-only`).
- `research-to-runtime-firewall` and `external-pattern-cleanroom-gate` take the
  **path list** from the index but `grep` the **worktree file**, so a staged
  blob that differs from the worktree is scanned in its worktree form.
- `clean-room-ast-similarity-gate` delegates to
  `scripts/cos_clean_room_ast_similarity.py --quick`.

None of them walk the filesystem for the candidate list, so a local run on a
clean tree matches CI on the same commit.

## Step 2 — decisions

### Switched to exit 2

- **`adoption-freeze-gate`** — real behaviour change. `manifests/external-tool-adoption-freeze.yaml`
  has `frozen: true` set by the operator (commercial/SaaS pivot, ADR-267 Layer 2)
  with written unfreeze conditions. The kill-switch has simply never killed.
  After the switch, a commit is blocked when it stages a path matching:
  `docs/03-PoCs/research/*-annex-*-*.md`, `docs/03-PoCs/research/*-comparison-*.md`,
  `docs/06-Daily/reports/external-tools-radar-*.md`,
  `docs/03-PoCs/research/repo-scout/deep/*.md`, `manifests/external-tools-adoption.yaml`.
  120 tracked files match those globs today, but at the time of the change no
  staged, modified or untracked file in the checkout matched any of them
  (`git status --porcelain --untracked-files=all` filtered by the globs: none),
  so it is born green for the work in flight. Bypasses stay: `COS_ALLOW_FREEZE_TOGGLE=1`
  (freeze yaml alone) and `COS_ALLOW_ADOPTION_FREEZE_BYPASS=1` (logged).
- **`clean-room-ast-similarity-gate`** — contract fix only. It cannot fire today
  (`find .cognitive-os/external-source-cache -name '*.py' -maxdepth 5 | wc -l` = 0)
  and it is not registered in `.claude/settings.json`; it stays `manual_trigger`
  in `hooks/_lib/registration-allowlist.txt` pending ADR-271 acceptance and soak.
- **`external-pattern-cleanroom-gate`** — contract fix only. It returns 0 before
  reaching any check because its upstream corpus lives under a `/tmp` path that
  no longer exists. **Its real problem is not the exit code**: a gate whose
  corpus lives in `/tmp` is guaranteed to skip after any reboot. Relocating the
  corpus is a separate operator decision; until then the gate is inert whatever
  it exits.

### Left at exit 1 on purpose

- **`research-to-runtime-firewall`** — **born red**. Three tracked runtime files
  reference `.cognitive-os/external-source-cache`:

  ```bash
  git grep -l -- '.cognitive-os/external-source-cache' -- 'lib/*' 'packages/*' 'scripts/*'
  # scripts/cos_clean_room_ast_similarity.py   (line 7)
  # scripts/cos_efficiency_primitives.py       (line 58)
  # scripts/cos_verbatim_copy_detector.py      (line 6, 77)
  ```

  Two of the three are the clean-room detectors themselves: naming the cache
  directory is their job, not a leak. Switching this gate to exit 2 would block
  every commit that touches its own tooling. Removing the references, or
  baselining them, would be the cheap green. The gate needs a written exemption
  for the detectors (the scanner must skip the files whose purpose is scanning
  the cache) before it can be switched. **Operator decision, not a mechanical fix.**

## Step 3 — why this landed as a patch instead of an edit

`hooks/protected-config-write-guard.sh` protects `hooks/**` and blocked the
edits with exit 2 (message: `PROTECTED CONFIG WRITE GUARD: BLOCKED`). The
guard was not bypassed. `gate-exit-codes.patch` in this directory holds the
three exit-code changes plus the dispatcher comment fix, and applies cleanly:

```bash
git apply --check docs/05-Methodology/runbooks/gate-exit-code-contract-2026-08-15/gate-exit-codes.patch
```

Applying it requires an operator running the same command without `--check`,
under `COS_ALLOW_PROTECTED_CONFIG_WRITE=1` for the commit that stages `hooks/`.

## Corrections to the brief's premises

- The contract citation `cos-dispatch/README.md:32` does not exist at the repo
  root. The file is `docs/04-Concepts/architecture/cos-dispatch/README.md`, and
  around line 32 it is a **harness comparison table** ("Exit code 2 = block" per
  tool), not a repo-level contract statement. The substance holds; the path did not.
- The dispatcher comment is misleading but harmless in a second way: it never
  upgraded anything. `_run_gate` returns the child `$rc` verbatim, so the four
  gates were inert regardless of the comment.
- `hooks/external-pattern-cleanroom-gate.sh` ends with a stray `HOOKEOF` line
  after its final `exit 0` — leftover heredoc terminator, unreachable, cosmetic.
  Not fixed here to keep the patch limited to the exit-code contract.

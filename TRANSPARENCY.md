# Transparency

> Read this before forming an opinion about how this repository got here.
> Every claim below maps to an artifact in-tree and a command you can run
> against your own clone.

This document is the public-launch transparency door for `luum-cognitive-os`
(Cognitive OS). It exists because the repository was rewritten on
**2026-05-08** to scrub pre-public residue, and we owe readers a clear,
verifiable account of what changed and what was preserved.

---

## TL;DR

- Cognitive OS was **private** while we built it. On 2026-05-08 we ran a
  one-time, manifest-driven history rewrite to scrub operator-local data
  and consumer-project residue, then froze the evidence trail under
  [`docs/01-Build-Log/history/`](docs/01-Build-Log/history/).
- The license moved from **Apache-2.0** to **FSL-1.1-MIT** before the
  public flip. License-transition strings are pinned to a `preserve` rule
  in the sanitization manifest — they cannot be rewritten by this
  toolchain. See [LICENSE](LICENSE), [NOTICE](NOTICE), and the
  [License FAQ](docs/09-Quality/legal/license-faq.md).
- Recovery mirrors of the pre-rewrite repository exist **off-repo** on
  the operator's machine (`~/.cognitive-os/recovery/pre-history-sanitization-*.git`)
  and are deliberately not published — they contain the data we scrubbed.
  The public tombstone is the cryptographic SHA inventory in
  [`docs/01-Build-Log/history/pre-sanitization-sha-inventory-2026-05-07.txt`](docs/01-Build-Log/history/pre-sanitization-sha-inventory-2026-05-07.txt).
- This repository is built **using its own agent harness**. AI assists,
  humans review and sign off. Authorship policy:
  [CONTRIBUTING.md](CONTRIBUTING.md) §1.
- Skeptical? Section 6, [Verify it yourself](#6-verify-it-yourself-anti-fud-toolkit),
  is a copy-paste block that lets you confirm every claim in this
  document without trusting us.

---

## 1. History rewrite disclosure

| What | Detail |
|---|---|
| When | 2026-05-08 (timestamped report: `docs/06-Daily/reports/history-sanitization-20260508T061208Z.json`) |
| Who | Operator-only; gated behind `COS_ALLOW_DESTRUCTIVE_GIT=1` and interactive confirmation per ADR-218 |
| Why | Remove operator personal email/name, local machine paths, and 5 consumer-project codenames/service names that bled in from a downstream private project before the project-specific terms hook became config-driven |
| Toolchain | `git-filter-repo`, driven by [`manifests/history-sanitization.yaml`](manifests/history-sanitization.yaml) (ADR-218); wrapper `scripts/cos-history-sanitization` (ADR-242 preserves the `origin` remote across rewrites) |
| Pre-rewrite head | `2d99d40a3382232f9ab3f32e85cdd89b777670bb` |
| Post-rewrite head | `db846adb6290456b431bfc191b08543f56a2e8d7` |
| Commit count | 2,440 (preserved, before and after) |

### What was replaced and with what

| Class of data | Replacement placeholder |
|---|---|
| Operator personal email | `2144218+MatiasNAmendola@users.noreply.github.com` (GitHub noreply) |
| Operator personal name | `MatiasNAmendola` (GitHub handle) |
| Operator home-directory prefix | `<home>` |
| Absolute local repo paths | `<repo>` |
| Old portability-fixture home paths | generic fixture-user / fixture-project placeholder (see manifest rule `historical-fixture-home-paths`) |
| Consumer-project codenames (3 slots) | `<consumer-codename-a..c>` |
| Consumer-project service names (5 slots) | `<consumer-service[-2..-5]>` |

The full rule list is enumerable from the manifest:

```bash
python3 -c "import yaml; m=yaml.safe_load(open('manifests/history-sanitization.yaml')); [print(r['id']) for r in m['rules']]"
```

### What was preserved (cannot be rewritten by this toolchain)

The manifest declares an explicit `preserve` block that the canonical
primitive enforces — if a replacement rule would also match a preserve
pattern, the rewrite **refuses to execute**:

- `license-transition` — `Apache License`, `Apache 2.0`, `Apache-2.0`,
  `FSL-1.1`, `FSL-1.1-MIT`, `Functional Source License`
- `scanner-fixtures` — `[REDACTED]`, `deadbeef`, `FAKEKEYFORTEST`

What `git filter-repo --replace-text` does **not** change (semantics, not
policy):

- commit messages, author identity, committer identity
- author dates, commit dates
- DAG topology, parents, merges, branch shape
- tree topology — file paths, directory structure
- number of commits per branch

The only changes are blob content matching declared rules and the
cascading SHA changes that follow.

### Skeptic's one-liners

```bash
# 1. Confirm scrubbed values do not appear in tracked-file history.
#    The two hits returned are the operator-written readiness-checklist
#    evidence text — see §3 "Privacy commitment" for why that is intentional.
git log --all -p | grep -E '(soporte\.esolutions|<consumer-codename-[abc]>|<consumer-service)' | head

# 2. List the manifest rule IDs (the universe of what was replaced).
python3 -c "import yaml; m=yaml.safe_load(open('manifests/history-sanitization.yaml')); [print(r['id']) for r in m['rules']]"

# 3. Inspect the frozen pre-rewrite policy (snapshot-2026-05-07) and diff
#    against the live manifest. The live manifest is BROADER than the
#    snapshot because new rules (operator-name, fixture-paths, consumer
#    slots) were added before the rewrite executed — that is by design.
diff manifests/history-sanitization.yaml docs/01-Build-Log/history/manifest-snapshot-2026-05-07.yaml
```

---

## 2. License transition timeline

| Date marker | License | Evidence |
|---|---|---|
| Pre-launch / default posture | Apache-2.0 | [`NOTICE`](NOTICE) (third-party Apache-2.0 attributions retained) |
| 2026-05-06 → public | FSL-1.1-MIT | [`LICENSE`](LICENSE), [License FAQ](docs/09-Quality/legal/license-faq.md) |
| Auto-conversion | MIT (after 2-year Change Date) | [License FAQ](docs/09-Quality/legal/license-faq.md) §"When does it convert" |

The transition is **public history**. The sanitization manifest's
`preserve.license-transition` rule (lines 122–126 of
[`manifests/history-sanitization.yaml`](manifests/history-sanitization.yaml))
explicitly forbids the toolchain from touching Apache or FSL strings, so
the rewrite cannot have erased the transition even if a future operator
attempted it.

Verify the strings survived:

```bash
grep -E 'Apache|FSL-1\.1-MIT' LICENSE NOTICE docs/09-Quality/legal/license-faq.md | wc -l
# Expect: 40+ matches
```

---

## 3. Privacy commitment

The rewrite scope was operator-local data and consumer-project residue.
Specifically:

- **Operator data** — personal email and name, replaced by GitHub
  noreply identity. Author/committer metadata on commits **was preserved**
  per the policy `preserve-human-author-emails; do-not-auto-rewrite`
  documented in [`docs/01-Build-Log/history/HISTORY-SANITIZATION-2026-05-08.md`](docs/01-Build-Log/history/HISTORY-SANITIZATION-2026-05-08.md).
- **Consumer codenames / service names** — pre-existed in this repo's
  history because they bled in from a downstream private project before
  the project-specific terms hook was config-driven. Replaced with
  generic placeholders.

> **Intentional disclosure:** the operator's previous personal email
> (`<operator-previous-email>`) appears **2 times** in `git log -p`,
> both inside operator-written evidence text in
> [`docs/09-Quality/legal/pre-public-readiness-checklist.md`](docs/09-Quality/legal/pre-public-readiness-checklist.md)
> documenting *what was scrubbed*. Those two strings are the audit trail,
> not a leak. They are inside narrative text describing the scrub itself.

Recovery mirrors of the pre-rewrite repository live **off-repo** on the
operator's machine and are intentionally not published — they contain
the very data the rewrite removed. The public substitute for that
mirror is the SHA inventory in
[`docs/01-Build-Log/history/pre-sanitization-sha-inventory-2026-05-07.txt`](docs/01-Build-Log/history/pre-sanitization-sha-inventory-2026-05-07.txt)
(1,775 entries; one line per pre-rewrite commit). Anyone with their own
pre-rewrite clone can hash-compare against this file to verify the
rewrite was strictly scoped.

---

## 4. Evidence chain

| Claim | Artifact | Verification command |
|---|---|---|
| Rewrite policy was frozen before execute | [`docs/01-Build-Log/history/manifest-snapshot-2026-05-07.yaml`](docs/01-Build-Log/history/manifest-snapshot-2026-05-07.yaml) | `diff manifests/history-sanitization.yaml docs/01-Build-Log/history/manifest-snapshot-2026-05-07.yaml` |
| Pre-rewrite SHAs are publicly recorded | [`docs/01-Build-Log/history/pre-sanitization-sha-inventory-2026-05-07.txt`](docs/01-Build-Log/history/pre-sanitization-sha-inventory-2026-05-07.txt) | `shasum -a 256 docs/01-Build-Log/history/pre-sanitization-sha-inventory-2026-05-07.txt` (expect `923170ead7ef9fd7c072089a699f867e111ead1be38a84ce41eb1a4023104997`) |
| Rewrite is described in operator narrative | [`docs/01-Build-Log/history/HISTORY-SANITIZATION-2026-05-08.md`](docs/01-Build-Log/history/HISTORY-SANITIZATION-2026-05-08.md) | open and read |
| Runtime report (replacement counts, blobs/commits rewritten) | [`docs/06-Daily/reports/history-sanitization-20260508T061208Z.json`](docs/06-Daily/reports/history-sanitization-20260508T061208Z.json) | `jq '.summary' docs/06-Daily/reports/history-sanitization-20260508T061208Z.json` |
| License transition strings preserved | [`LICENSE`](LICENSE), [`NOTICE`](NOTICE), [License FAQ](docs/09-Quality/legal/license-faq.md) | `grep -E 'Apache\|FSL-1\.1-MIT' LICENSE NOTICE docs/09-Quality/legal/license-faq.md` |
| SBOM | [`sbom.json`](sbom.json) | `shasum -a 256 sbom.json` |
| Policy ADR | `docs/02-Decisions/adrs/ADR-218-history-sanitization-toolchain.md` | open and read |

The pre-rewrite SHAs in the inventory are **not reachable** from the
post-rewrite `origin/main`. That non-reachability is itself the
proof-of-rewrite (see §6).

---

## 5. Build provenance

- **AI-assisted, human-reviewed.** Cognitive OS is built using AI coding
  agents (Claude, Codex, Qwen, others). AI output is treated as draft
  work; a human reviews, tests, and signs off before commit. Full
  authorship policy: [CONTRIBUTING.md](CONTRIBUTING.md) §1.
- **No invented identities.** We do not author commits as `Co-authored-by:
  Claude` or any provider-implying name. Authorship metadata is for
  humans or accountable organizations.
- **Dogfood property.** This repository is built with the very harness it
  ships (`cognitive-os`). The hooks that gate every commit on this
  project are the hooks the project distributes. That is intentional and
  worth disclosing — the OS has been pressure-tested by being the thing
  that ships it.
- **SBOM.** CycloneDX 1.6 via syft 1.44.0; full posture in
  [`docs/09-Quality/security/supply-chain.md`](docs/09-Quality/security/supply-chain.md).
- **Release signing.** Current state and forward plan in
  [`docs/09-Quality/security/release-signing.md`](docs/09-Quality/security/release-signing.md).
  Tags before `v1.0.0` are unsigned by disclosed, intentional gap; the
  first tag flagged `public-release: true` will be signed and carry a
  detached SBOM signature plus a release-manifest.

---

## 6. Verify it yourself (anti-FUD toolkit)

Every command below runs against a fresh clone and uses no privileged
inputs. If a result diverges from what this document claims, file an
issue.

```bash
# --- 0. Fresh clone, clean state ---
git clone https://github.com/luum-home/luum-cognitive-os.git && cd luum-cognitive-os

# --- 1. History is clean (no scrubbed values outside the disclosure text) ---
# Expect: only matches inside docs/09-Quality/legal/pre-public-readiness-checklist.md
#         (the readiness checklist evidence text — see §3).
git log --all -p | grep -E '(soporte\.esolutions|<consumer-codename-[abc]>|<consumer-service)'

# --- 2. License strings preserved ---
# Expect: 40+ matches across LICENSE / NOTICE / license-faq.md
grep -E 'Apache|FSL-1\.1-MIT' LICENSE NOTICE docs/09-Quality/legal/license-faq.md | wc -l

# --- 3. SHA inventory has its declared hash ---
# Expect: 923170ead7ef9fd7c072089a699f867e111ead1be38a84ce41eb1a4023104997
shasum -a 256 docs/01-Build-Log/history/pre-sanitization-sha-inventory-2026-05-07.txt

# --- 4. Pre-rewrite SHAs are NOT reachable from origin/main ---
# Expect: every SHA prints "missing" — that is the proof-of-rewrite.
head -5 docs/01-Build-Log/history/pre-sanitization-sha-inventory-2026-05-07.txt | \
  awk '{print $1}' | \
  while read sha; do git cat-file -e "$sha" 2>/dev/null && echo "$sha REACHABLE" || echo "$sha missing"; done

# --- 5. Manifest snapshot is byte-identical to its frozen copy ---
# Expect: differences confined to rules added BEFORE rewrite execution
#         (operator-name, fixture-paths, consumer-* slots). See §1.
diff manifests/history-sanitization.yaml docs/01-Build-Log/history/manifest-snapshot-2026-05-07.yaml

# --- 6. SBOM exists and has the advertised format ---
test -f sbom.json && \
  jq -r '"\(.bomFormat) \(.specVersion)"' sbom.json
# Expect: CycloneDX 1.6

# --- 7. Tag verification (when v1.0.0+ ships) ---
# Pre-v1.0.0: tags are unsigned by disclosed, intentional gap.
# Post-v1.0.0: this command MUST succeed.
git fetch --tags && git tag -v v1.0.0 2>&1 | head -20
```

A longer-form version of this toolkit, with prose for each step, lives
at [`docs/09-Quality/security/verify-public-release.md`](docs/09-Quality/security/verify-public-release.md).

---

## 7. Contact / responsible disclosure

Security or licensing concerns that should not start in a public issue:
`2144218+MatiasNAmendola@users.noreply.github.com`.

For everything else, prefer GitHub issues — public answers help everyone
who has the same question. See [CONTRIBUTING.md](CONTRIBUTING.md) §8.

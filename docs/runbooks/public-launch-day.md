# Public Launch Day Runbook

> Operator runbook for flipping `luum-cognitive-os` from internal to
> public. Sequenced by clock offset relative to T-0 (the moment the
> GitHub repository visibility flips).

**Audience:** repository operator (single-person action; do not delegate).
**Prerequisites:**

- Readiness checklist closed: [`docs/legal/pre-public-readiness-checklist.md`](../legal/pre-public-readiness-checklist.md) (14/14)
- Transparency door published: [`TRANSPARENCY.md`](../../TRANSPARENCY.md)
- History sanitization narrative published: [`docs/history/HISTORY-SANITIZATION-2026-05-08.md`](../history/HISTORY-SANITIZATION-2026-05-08.md)
- Recovery mirror present off-repo at the operator's recovery directory
- Local working tree clean (`git status` is empty)

---

## T-30min: Pre-flip verifications

Run these in order. Stop if any step fails.

### 1. Incognito GitHub read-through (manual)

Open the repo in a browser incognito window logged in as the operator.
Walk the following surface:

- [ ] `README.md` renders, all top badges resolve (no broken images)
- [ ] [`TRANSPARENCY.md`](../../TRANSPARENCY.md) link from README is visible above the badges
- [ ] [`LICENSE`](../../LICENSE) renders as `FSL-1.1-MIT`
- [ ] [`CONTRIBUTING.md`](../../CONTRIBUTING.md) renders, AI-authorship section is intact
- [ ] [`docs/legal/license-faq.md`](../legal/license-faq.md) renders
- [ ] [`docs/history/`](../history/) directory listing shows all four files
- [ ] [`sbom.json`](../../sbom.json) is browsable (raw view)

### 2. Click-test critical links

From the rendered README, click each link in turn and confirm 200, not
404. Same for TRANSPARENCY.md and CONTRIBUTING.md. Pay attention to:

- [ ] `LICENSE` (relative)
- [ ] `NOTICE` (relative)
- [ ] `docs/legal/license-faq.md`
- [ ] `docs/legal/pre-public-readiness-checklist.md`
- [ ] `docs/history/HISTORY-SANITIZATION-2026-05-08.md`
- [ ] `docs/history/manifest-snapshot-2026-05-07.yaml`
- [ ] `docs/history/pre-sanitization-sha-inventory-2026-05-07.txt`
- [ ] `docs/security/supply-chain.md`
- [ ] `docs/security/release-signing.md`
- [ ] `docs/security/verify-public-release.md`

### 3. Smoke privacy check

```
git log --all -p | grep -E 'soporte\.esolutions' | head -20
```

Expected output: only the two operator-written disclosure-text matches
inside `docs/legal/pre-public-readiness-checklist.md`.

Then confirm that sanitized placeholders are present only as placeholders,
not as real consumer names:

```
git log --all -p | \
  grep -E '(<consumer-codename-[abc]>|<consumer-service(-[2-5])?>)' | \
  head -20
```

Expected output: placeholder references are allowed in sanitization docs,
transparency docs, and generated inventories. If any real consumer name or
service token appears, abort and re-run the rewrite per ADR-218.

### 4. Origin matches local

```
git fetch origin
git rev-parse HEAD
git rev-parse origin/main
```

Both SHAs must match. There are 7 commits pending publication at the
time of this writing — publish them BEFORE flipping visibility (T-0
step 1).

### 5. Recovery mirror inventory note

Operator confirms locally that at least one
`pre-history-sanitization-*.git` directory exists in the recovery
location. These directories are intentionally not published — they
contain the data the rewrite removed.

### 6. Public tombstone check

There is no `tombstone-*` git branch in this repository. The earlier
references to a "tombstone" mean the recovery-mirror directory name
under the operator's recovery location, which is operator-only. The
public tombstone is the SHA inventory:

```
shasum -a 256 docs/history/pre-sanitization-sha-inventory-2026-05-07.txt
# Expect: 923170ead7ef9fd7c072089a699f867e111ead1be38a84ce41eb1a4023104997
wc -l docs/history/pre-sanitization-sha-inventory-2026-05-07.txt
# Expect: 1775
```

Anyone with a pre-rewrite clone can hash-compare against this file to
verify the rewrite was strictly scoped to declared rules.

---

## T-0: Flip

Execute in order; do not parallelize.

### 1. Publish remaining commits to origin

Use the standard publish command for the configured remote, then confirm
local HEAD matches `origin/main`. Both must agree before proceeding.

### 2. GitHub Settings → Change visibility → Public

Manual UI step. In a browser as the repository owner:

1. Navigate to `Settings` → `General` → `Danger Zone`
2. Click `Change visibility` → `Make public`
3. Type the repository name to confirm
4. Click `I understand, change repository visibility`

Take a screenshot for the launch record:
`docs/runbooks/launch-screenshots/visibility-flip-{YYYYMMDD}.png`
(operator file; not committed if empty).

### 3. Cut signed annotated tag

Per [`docs/security/release-signing.md`](../security/release-signing.md).
The first public tag is `v1.0.0` (or whichever public version is decided
at flip time):

```
git tag -s v1.0.0 -m "First public release of Cognitive OS (FSL-1.1-MIT)."
git tag -v v1.0.0    # MUST succeed
```

If the maintainer signing material is not yet published, fall back to
the disclosed-gap path: cut an annotated (unsigned) tag and update
[`docs/security/release-signing.md`](../security/release-signing.md) §1
within 24 hours to reflect the new tag in the unsigned-tags table.

### 4. Publish tag

Publish the new tag to the configured remote using the standard tag
publish command for `git`.

---

## T+15min: Post-flip verifications

### 1. Public render check

Open the now-public repo in a browser incognito (no GitHub login).
Confirm:

- [ ] `TRANSPARENCY.md` renders at the repo root
- [ ] All evidence-chain links in TRANSPARENCY.md §4 resolve (200, not 404)
- [ ] `LICENSE` and `NOTICE` are accessible to anonymous users
- [ ] `sbom.json` raw view returns the CycloneDX 1.6 JSON

### 2. SBOM artifact accessible

Fetch the raw `sbom.json` from the public GitHub raw-content endpoint
for `main` and confirm:

```
jq -r '"\(.bomFormat) \(.specVersion)"' sbom.json
# Expect: CycloneDX 1.6
```

### 3. Signed tag verifies from a fresh clone

Clone a fresh shallow copy of the public repo at `v1.0.0` into a temp
directory and run `git tag -v v1.0.0`.

Pre-v1.0.0 (during the unsigned-gap window): expect `error: no
signature found`. This is the disclosed gap. Document any deviation in
`docs/security/release-signing.md` §1.

### 4. Launch-day incident channel

Open a tracking issue (or chat thread) titled
`launch-day-{YYYY-MM-DD}` for the first 24 hours. Mark `no-incident` at
T+24h or escalate per the rollback section.

---

## Rollback

Visibility flip is reversible at the GitHub UI level: `Settings` →
`Change visibility` → `Make private`. Limitations:

- Cached rendered views (third-party mirrors, content archives,
  search-engine caches) may persist for some time. Treat any content
  briefly visible as publicly disclosed for risk-modeling purposes.
- Forks created during the public window remain on the forker's account
  and cannot be deleted by us.
- Tags and clones already pulled cannot be retracted.

If a rollback is triggered by a leaked-content discovery (e.g. a
sanitization gap shipped):

1. Flip back to non-public immediately.
2. File a security advisory per [TRANSPARENCY.md §7](../../TRANSPARENCY.md#7-contact--responsible-disclosure).
3. Treat the leaked content as compromised and follow the operator
   data-handling procedure for that data class.
4. Do not force-publish a corrected history while the repo is public —
   that breaks every consumer's clone and is itself a hostile-auditor
   signal. Cut a new sanitization-cycle proposal under
   [ADR-218](../adrs/ADR-218-history-sanitization-toolchain.md), then
   re-flip on the next launch window.

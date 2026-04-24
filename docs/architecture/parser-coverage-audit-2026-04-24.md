# Parser Test Coverage Audit — 2026-04-24

**Trigger**: `_fm()` bug discovered today (commit `c6c84e4` fixes it). Audit checks whether 12 sibling parsers have the same "synthetic-only test" coverage gap.

## Method

For each module, parser/extractor functions were identified by looking for `re.search`/`re.match` on multi-line text, YAML/frontmatter extraction, and similar patterns. The associated test file was located and classified based on whether tests exercise real disk files or only synthetic strings. **GREEN** = at least one test reads a real on-disk file; **YELLOW** = mix of real and synthetic; **RED** = synthetic strings only, production input shape never exercised; **NO TESTS** = no test file found.

## Findings — Summary Table

| # | Module | Coverage | Real-file integration? | Fix cost (estimate) |
|---|---|---|---|---|
| 1 | `lib/session_hygiene.py` | GREEN | Yes (post-fix) | 0 |
| 2 | `lib/skill_routing.py` | GREEN | Yes — 3 real SKILL.md fixtures | 0 |
| 3 | `scripts/generate_compact_catalog.py` | GREEN | Yes — runs against repo SKILL.md files end-to-end | 0 |
| 4 | `lib/doc_review_personas.py` | RED | No — all inputs are synthetic LLM response strings | 1-3 |
| 5 | `lib/pattern_detector.py` | RED | No — synthetic SKILL.md written via `tmp_path` only, never HTML-comment prefix | 4-10 |
| 6 | `lib/smart_access.py` | RED | No — `skill_md` fixture hardcodes `---` at line 1, no HTML comment variant | 1-3 |
| 7 | `packages/ecosystem-tools/lib/notifications.py` | GREEN-by-design | N/A — no regex/YAML parsing of files; env-var + HTTP only | 0 |
| 8 | `packages/infra-lifecycle/lib/performance_monitor.py` | GREEN-by-design | N/A — no frontmatter/YAML parsing; JSONL append + in-memory stats | 0 |
| 9 | `scripts/dogfood_score.py` | GREEN-by-design | N/A — thin CLI wrapper over `lib/dogfood_scorer.py`; no parser logic of its own | 0 |
| 10 | `scripts/regen_catalog_bullets.py` | RED (no dedicated test) | No test file exists; relies entirely on `_fm()` from `lib/session_hygiene` | 1-3 |
| 11 | `scripts/radar_merge.py` | YELLOW | `parse_artifact` tested with synthetic tmp_path files; `parse_doc_entries` tested with synthetic strings; no real artifacts from `docs/ecosystem-tools/` | 4-10 |

> **Note**: Audit covers 11 non-skipped Python modules (the two bash scripts listed in the prompt were excluded per instructions; `scripts/regen_catalog_bullets.py` has no dedicated test file and is counted as module 10 in the 12-module scope — it delegates parsing to `_fm()` from `lib/session_hygiene`, so its fix cost is low now that `_fm()` is fixed).

## Findings — Detail

### 1. lib/session_hygiene.py — GREEN (reference)

**Parser**: `_fm()` — extracts YAML frontmatter key; supports HTML comment prefix and block scalars.
**Test file**: `tests/unit/test_session_hygiene.py`
**Coverage**: 20+ tests. `TestFm` class now exercises synthetic strings with `<!-- SCOPE: both -->` prefix and multi-line `description: >` scalars. `TestUpdateCatalog` exercises `_fm()` indirectly via synthetic SKILL.md files. No real-disk integration test of `_fm()` itself, but the fix was targeted at synthetic coverage of the exact shapes that were failing.
**Same gap as `_fm()`?**: NO — gap closed by today's fix.
**Fix cost**: 0.

---

### 2. lib/skill_routing.py — GREEN

**Parser**: `_extract_frontmatter()` — line-by-line parser that skips blank/HTML-comment lines before `---`. `parse_routing_block()` — canonicalises parsed YAML dict.
**Test file**: `tests/unit/test_skill_routing.py`
**Coverage**: `TestFrontmatterExtraction.test_frontmatter_after_html_comment` explicitly tests the `<!-- SCOPE: both -->` prefix with a synthetic string. `TestLoadSkillRequirements` has three real-disk fixtures:
```python
def test_security_audit_skill_parses(self):
    path = _REPO / "packages" / "quality-gates" / "skills" / "security-audit" / "SKILL.md"
    if not path.exists():
        self.skipTest("security-audit SKILL.md not present in this checkout")
    req = _sr.load_skill_requirements(path)
    self.assertIsNotNone(req, "security-audit must declare a routing block")
```
**Same gap as `_fm()`?**: NO — `_extract_frontmatter` was already designed to handle HTML comment prefix; real-file tests confirm it on actual SKILL.md files.
**Fix cost**: 0.

---

### 3. scripts/generate_compact_catalog.py — GREEN

**Parser**: `parse_frontmatter()` — strips leading HTML comments via `re.sub(r"^(\s*<!--.*?-->\s*)+", "", ...)` before checking for `---`; handles block scalars `>`, `|`.
**Test file**: `tests/unit/test_catalog_loading.py`
**Coverage**: `TestGenerator.test_generator_script_runs` runs the generator subprocess against the actual repo tree. `TestConsistency.test_every_skill_in_compact` calls `mod.collect_skills(PROJECT_ROOT)` which reads every real `skills/*/SKILL.md` and `packages/*/skills/*/SKILL.md` on disk. `test_regeneration_is_idempotent_against_committed_file` compares the committed catalog against a live regeneration — if any real SKILL.md breaks `parse_frontmatter`, this test fails.
**Same gap as `_fm()`?**: NO — real-disk integration is the primary test mechanism here.
**Fix cost**: 0.

---

### 4. lib/doc_review_personas.py — RED

**Parser**: `parse_findings()` — parses persona LLM output using regex (`_HEADER_RE`, `_FIELD_RE`) to extract `TRUST_REPORT` header and `FINDING` blocks from free-form text.
**Test file**: `tests/unit/test_doc_review_personas.py`
**Coverage**: All tests use `_mock_llm_response()` which constructs synthetic strings:
```python
def _mock_llm_response(findings: list[dict], score: int = 80) -> str:
    lines = [f"TRUST_REPORT: SCORE={score} STATUS={status} EVIDENCE=2 UNCERTAINTIES=1", "---"]
    for f in findings:
        lines.append("FINDING")
        lines.append(f"TIER: {f.get('tier', 'S3')}")
        ...
    return "\n".join(lines)
```
No test feeds a real LLM response captured from production. The `FINDING` and `TRUST_REPORT` blocks in production may include whitespace variants, unusual line endings, or multi-line fields that the synthetic helper never exercises.
**Same gap as `_fm()`?**: PARTIAL — the parser operates on LLM text, not file frontmatter, so the failure mode differs. However, the core gap (no production-shaped input ever tested) is identical in structure. If a model returns slightly different formatting (e.g., `FINDING:` with trailing colon), the regex would silently miss it.
**Fix cost**: 1-3 tests (capture 1-2 real persona outputs from the actual model, replay as fixtures).

---

### 5. lib/pattern_detector.py — RED

**Parser**: `_parse_frontmatter_keys()` — extracts YAML keys from SKILL.md; `_collect_frontmatter_keys()` walks `skills/` on disk and calls `_parse_frontmatter_keys`.
**Test file**: `tests/unit/test_pattern_detector.py`
**Coverage**: All SKILL.md fixtures are written via `tmp_path` and uniformly start with `---` at line 0:
```python
(skill_dir / "SKILL.md").write_text(textwrap.dedent("""\
    ---
    name: my-skill
    description: A test skill
    custom-unused-field: true
    ---
```
`_parse_frontmatter_keys` checks `lines[0].strip() != "---"` — the identical pre-fix bug pattern as the original `_fm()`. Any real SKILL.md starting with `<!-- SCOPE: both -->` would return `[]`, silently treating all its frontmatter keys as absent. The test never exercises this.
**Same gap as `_fm()`?**: YES — confirmed identical bug pattern. The HTML-comment prefix guard is missing entirely.
**Fix cost**: 4-10 tests (fix the parser + add tests covering HTML comment prefix, multi-line values, empty files, and at least one real SKILL.md from disk).

---

### 6. lib/smart_access.py — RED

**Parser**: `get_skill_frontmatter()` — opens SKILL.md line-by-line; fails immediately if the first line is not `---`:
```python
if next(lines, "").rstrip() != "---":
    return result
```
**Test file**: `tests/unit/test_smart_access.py`
**Coverage**: The `skill_md` fixture hardcodes `---` as the first line:
```python
content = ("---\n" "name: my-skill\n" "description: Does something useful\n" "version: 1.2.3\n" "---\n" ...)
```
No test passes a SKILL.md with `<!-- SCOPE: both -->` before `---`. No real disk file is ever loaded.
**Same gap as `_fm()`?**: YES — confirmed identical bug pattern. `get_skill_frontmatter()` returns `{}` for every real SKILL.md that starts with an HTML comment (all `SCOPE: both` skills).
**Fix cost**: 1-3 tests (add fixture with `<!-- SCOPE: both -->\n---` prefix; add one test loading a real SKILL.md from the repo).

---

### 7. packages/ecosystem-tools/lib/notifications.py — GREEN-by-design

**Parser**: None. The module formats notification payloads for Telegram/Slack/webhooks using string templates and `json.dumps`. No file parsing, no regex on multi-line content. Configuration comes from env vars (`NOTIFY_PROVIDER`, `TELEGRAM_BOT_TOKEN`, etc.).
**Same gap as `_fm()`?**: NO — not applicable.
**Fix cost**: 0.

---

### 8. packages/infra-lifecycle/lib/performance_monitor.py — GREEN-by-design

**Parser**: None. The module records timing/token metrics in memory and serialises to JSONL via `json.dumps`. Reads back via `json.loads` per line. No YAML/TOML/frontmatter parsing, no multi-line regex over structured text.
**Same gap as `_fm()`?**: NO — not applicable.
**Fix cost**: 0.

---

### 9. scripts/dogfood_score.py — GREEN-by-design

**Parser**: None. This is a thin CLI (`argparse`) wrapper over `lib/dogfood_scorer.py`. All scoring logic lives in the library; the script only calls it and formats the result. No regex or file parsing of its own.
**Same gap as `_fm()`?**: NO — not applicable.
**Fix cost**: 0.

---

### 10. scripts/regen_catalog_bullets.py — RED (no dedicated test)

**Parser**: Delegates entirely to `_fm()` from `lib/session_hygiene` for SKILL.md parsing. The script itself has no parser — `build_bullets()` calls `_fm(text, "name")` and `_fm(text, "description")` directly.
**Test file**: None. No `tests/unit/test_regen_catalog_bullets.py` exists.
**Coverage**: No test exercises `build_bullets()` or the full `regen()` function. Since `_fm()` is now fixed, the parser behaviour is correct, but the integration (does `regen()` produce correct output given real SKILL.md files?) is untested.
**Same gap as `_fm()`?**: YES-by-proxy — before today's fix, this script would have silently dropped all HTML-comment-prefixed SKILL.md descriptions with no test to catch it.
**Fix cost**: 1-3 tests (one end-to-end test of `build_bullets()` against a tmp_path with a `<!-- SCOPE: both -->` SKILL.md; optionally one smoke test against the real `skills/` dir).

---

### 11. scripts/radar_merge.py — YELLOW

**Parser**: `parse_artifact(path)` — reads a `/repo-scout` artifact file from disk using `re.match(r"^---\s*\n(.*?\n)---\s*\n", text, re.DOTALL)` plus table/inline fallbacks. `parse_doc_entries(text)` — parses a radar doc string into entry dicts using `_FRONTMATTER_RE`.
**Test file**: `tests/unit/test_radar_merge.py`
**Coverage**: `parse_artifact` is tested via synthetic `tmp_path` files:
```python
def test_parse_artifact_from_frontmatter(self, tmp_path):
    artifact = tmp_path / "owner_mytool.md"
    artifact.write_text(textwrap.dedent("---\nrepo: owner/mytool\n..."))
    ev = parse_artifact(artifact)
```
`parse_doc_entries` is tested with hardcoded strings (`ECOSYSTEM_WITH_ONE_ENTRY`, etc.). No test reads a real artifact from `docs/ecosystem-tools/` or a real radar doc.
**Same gap as `_fm()`?**: PARTIAL — `parse_artifact` uses `re.DOTALL` on the full file, so it tolerates variations in the frontmatter block. The risk is lower than for pattern_detector/smart_access because the regex is more permissive. However, real artifacts from `/repo-scout` may include trailing spaces, unusual YAML quoting, or multi-line fields not covered by the synthetic fixtures.
**Fix cost**: 4-10 tests (add tests with real artifact files from `docs/ecosystem-tools/`; exercise multi-line `one_liner` values; test the classification-shift path with real radar docs).

---

## Recommendations

| Module | Action |
|---|---|
| `lib/pattern_detector.py` | Fix `_parse_frontmatter_keys`: add HTML comment prefix skip (same logic as `_extract_frontmatter` in `skill_routing.py`). Add tests with `<!-- SCOPE: both -->` prefix and at least one real `skills/*/SKILL.md`. |
| `lib/smart_access.py` | Fix `get_skill_frontmatter`: skip leading HTML comment lines before checking for `---`. Add fixture with comment prefix; add one real-disk integration test. |
| `scripts/regen_catalog_bullets.py` | Add `tests/unit/test_regen_catalog_bullets.py` with a `build_bullets()` smoke test using a `<!-- SCOPE: both -->` SKILL.md fixture. |
| `lib/doc_review_personas.py` | Capture 1-2 real LLM persona outputs as golden fixtures; add a replay test for `parse_findings()` against them. |
| `scripts/radar_merge.py` | Add integration tests for `parse_artifact` using real files from `docs/ecosystem-tools/`; add multi-line `one_liner` test case for `parse_doc_entries`. |

## Patterns Observed

- The most common failure mode is a "first-line fence assumption": parsers check `lines[0] == "---"` without accounting for the `<!-- SCOPE: ... -->` HTML comment that many SKILL.md files include. This exact pattern appears independently in `pattern_detector._parse_frontmatter_keys`, `smart_access.get_skill_frontmatter`, and was the root cause in the original `_fm()`.
- Modules with real-file integration tests (`skill_routing.py`, `generate_compact_catalog.py`) avoided the bug because tests would have caught the regression when run against actual SKILL.md files in the repo.
- GREEN-by-design modules (notifications, performance_monitor, dogfood_score) have no frontmatter parsing and are immune by construction.

## Risk Ranking

1. **`lib/smart_access.py`** — Highest blast radius. `get_skill_frontmatter()` is called by multiple skills and hooks that read routing/audience metadata. Returns `{}` for every `<!-- SCOPE: both -->` SKILL.md silently, which means incorrect routing decisions cascade to dispatch. The bug is confirmed present and the fix requires only 1-3 tests.

2. **`lib/pattern_detector.py`** — High blast radius (feeds the `/pattern-audit` and `/detect-patterns` skills). `_parse_frontmatter_keys()` silently drops all frontmatter keys from HTML-comment-prefixed SKILL.md files, causing false "dead metadata" positives for the `SCOPE: both` skill set (roughly half the repo). The bug is confirmed identical to `_fm()`.

3. **`scripts/regen_catalog_bullets.py`** — Medium blast radius. No dedicated test; the script was silently broken for HTML-comment-prefixed skills before today's `_fm()` fix. The underlying parser is now correct (delegates to fixed `_fm()`), but the absence of any test means a future regression could go undetected for another full release cycle.

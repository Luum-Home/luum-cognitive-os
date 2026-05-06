# Dependency License Compliance Audit — Cognitive OS v1.0 FSL Release

**Date**: 2026-05-06  
**Auditor**: Claude Code (automated + manual analysis)  
**Scope**: All direct + transitive dependencies in preparation for FSL 1.1 public release  
**Repo**: `github.com/luum-home/luum-cognitive-os`  
**Target license**: FSL 1.1 (Functional Source License) → MIT after 2 years

---

## 1. Executive Summary

| Dimension | Count |
|---|---|
| Python packages (uv.lock — locked) | 91 |
| Go modules (go.mod) | 11 direct + transitive |
| Node packages (dashboard/package-lock.json) | 99 total (10 direct) |
| Git submodules | 3 |
| **Total unique deps audited** | **~214** |

| Category | Python | Go | Node | Submodules |
|---|---|---|---|---|
| ✅ Green (MIT/Apache/BSD/ISC/PSF) | 86 | 11 | 86 | 3 |
| 🟡 Yellow (MPL/LGPL/ELv2) | 3 | 0 | 23 | 0 |
| 🔴 Red (AGPL/GPL/CC-BY-NC) | 0 | 0 | 0 | 0 |
| ⚠️ Review (CC-BY-4.0 data) | 0 | 0 | 1 | 0 |
| ❓ Unknown/self | 1 (self) | 1 (Unknown→BSD-3) | 0 | 0 |

**Top 5 items requiring action before FSL launch:**

1. **`arize-phoenix` / `arize-phoenix-evals` (ELv2)** — Phoenix server is ELv2. ADR-058 has now been corrected; remaining requirement is to keep Phoenix in the explicit observability dependency lane and out of the core lock / hosted COS Cloud offering unless commercially licensed.
2. **`lightningcss` + platform packages (MPL-2.0)** — 12 packages, transitive dep of Next.js/Tailwind. MPL-2.0 is file-level copyleft: source modifications to lightningcss files must be disclosed, but no FSL incompatibility if files are not modified.
3. **`@img/sharp-libvips-*` (LGPL-3.0-or-later)** — 10 platform packages, transitive dep of Next.js image optimization. Shipped as prebuilt native binaries. LGPL dynamic-linking exception applies; no static embedding occurs.
4. **`certifi` (MPL-2.0)** — The Mozilla CA bundle. No code modification expected; annotation in NOTICE.md sufficient.
5. **`caniuse-lite` (CC-BY-4.0)** — Browser compat data used internally by Next.js build tooling. CC-BY-4.0 applies to the data content; attribution required in NOTICE.md.

**Overall risk**: 🟡 MEDIUM — No blockers (zero AGPL/GPL). All yellow items are resolvable through annotation and usage confirmation. The material Phoenix discrepancy has been corrected in ADR-058, NOTICE, `cognitive-os.yaml`, and active Phoenix docs.

---

## 2. Python Dependencies Matrix

Scanned via `pip-licenses` on the `uv.lock`-resolved virtual environment (91 locked packages).

### 2a. Non-green packages (all actionable)

| Package | Version | License | Category | URL |
|---|---|---|---|---|
| `certifi` | 2026.4.22 | MPL-2.0 | 🟡 MPL | https://github.com/certifi/python-certifi |
| `pytest-rerunfailures` | 16.1 | MPL-2.0 | 🟡 MPL (dev/test only) | https://github.com/pytest-dev/pytest-rerunfailures |
| `tqdm` | 4.67.3 | MPL-2.0 AND MIT | 🟡 MPL (dual — use MIT terms) | https://github.com/tqdm/tqdm |
| `luum-cognitive-os` | 0.27.0 | UNKNOWN | ❓ Self (FSL applies) | — |

> **Note**: `arize-phoenix`, `arize-phoenix-evals`, `ldap3`, `nemoguardrails`, and `fqdn` appeared in the pip-licenses environment scan but are **not in `uv.lock`**. They are installed outside the core lock environment or live in explicit heavy lanes. They are **not locked core project dependencies** and do not affect the FSL core release.

### 2b. Phoenix packages outside the core lock

| Package | Where declared | License | Category |
|---|---|---|---|
| `arize-phoenix` | `requirements/dependency-lanes/observability.txt` | ELv2 | 🟡 operator-installed, not bundled |
| `arize-phoenix-otel` | `requirements/dependency-lanes/observability.txt` | Apache-2.0 | ✅ optional OTel bridge |
| `arize-phoenix-client` | not in current core lock | Apache-2.0 upstream | ✅ if explicitly installed |

> The Phoenix server package (ELv2) is **not in `uv.lock`**. It is an optional runtime service invoked as `phoenix serve` by the operator, not bundled in the OS core release. See Section 6.

### 2c. Representative green packages (top 20 by dependency weight)

| Package | Version | License | Category |
|---|---|---|---|
| `fastapi` | 0.136.1 | MIT | ✅ |
| `pydantic` | 2.12.5 | MIT | ✅ |
| `pydantic-core` | — | MIT | ✅ |
| `openai` | 2.24.0 | Apache-2.0 | ✅ |
| `claude-agent-sdk` | ≥0.1 | MIT | ✅ |
| `httpx` | 0.28.1 | BSD | ✅ |
| `jinja2` | 3.1.6 | BSD | ✅ |
| `cryptography` | 47.0.0 | Apache-2.0 OR BSD-3 | ✅ |
| `rich` | 15.0.0 | MIT | ✅ |
| `uvicorn` | 0.46.0 | BSD-3 | ✅ |
| `pyyaml` | 6.0.3 | MIT | ✅ |
| `redis` | 7.4.0 | MIT | ✅ |
| `requests` | 2.33.1 | Apache-2.0 | ✅ |
| `docker` | 7.1.0 | Apache-2.0 | ✅ |
| `mcp` | — | MIT | ✅ |
| `pytest` | 9.0.3 | MIT | ✅ (dev only) |
| `ruff` | 0.15.12 | MIT | ✅ (dev only) |
| `textual` | 8.2.5 | MIT | ✅ |
| `starlette` | 1.0.0 | BSD-3 | ✅ |
| `testcontainers` | 4.14.2 | Apache-2.0 | ✅ (test only) |

---

## 3. Go Dependencies Matrix

Scanned via `go-licenses csv ./...` on `go.mod` (root module `github.com/luum/cos-dispatch`).

| Package | Version | License | Category | Source |
|---|---|---|---|---|
| `github.com/BurntSushi/toml` | v1.4.0 | MIT | ✅ | https://github.com/BurntSushi/toml |
| `github.com/dustin/go-humanize` | v1.0.1 | MIT | ✅ | https://github.com/dustin/go-humanize |
| `github.com/google/uuid` | v1.6.0 | BSD-3-Clause | ✅ | https://github.com/google/uuid |
| `github.com/mattn/go-isatty` | v0.0.20 | MIT | ✅ | https://github.com/mattn/go-isatty |
| `github.com/ncruces/go-strftime` | v1.0.0 | MIT | ✅ | https://github.com/ncruces/go-strftime |
| `github.com/remyoudompheng/bigfft` | 24d4a6f | BSD-3-Clause | ✅ | https://github.com/remyoudompheng/bigfft |
| `golang.org/x/sys` | v0.42.0 | BSD-3-Clause | ✅ | https://cs.opensource.google/go/x/sys |
| `modernc.org/libc` | v1.70.0 | MIT | ✅ | https://gitlab.com/cznic/libc |
| `modernc.org/mathutil` | v1.7.1 | BSD-3-Clause | ✅ (confirmed via pkg.go.dev) | https://gitlab.com/cznic/mathutil |
| `modernc.org/memory` | v1.11.0 | BSD-3-Clause | ✅ | https://gitlab.com/cznic/memory |
| `modernc.org/sqlite` | v1.48.2 | BSD-3-Clause | ✅ | https://gitlab.com/cznic/sqlite |

> **Note**: `go-licenses` flagged `modernc.org/mathutil` as Unknown (no LICENSE file in the local module cache). Manual lookup on pkg.go.dev confirms BSD-3-Clause. No red or yellow flags across all Go dependencies.

**Go summary: 11/11 green. Zero concerns.**

---

## 4. Node Dependencies Matrix (dashboard)

The `dashboard/` is a Next.js 15 + React 19 internal admin UI (`private: true`). It is not bundled or shipped as part of the core COS release — it's a local dev convenience. 99 packages total in `package-lock.json`.

### 4a. Direct dependencies

| Package | Version | License | Category |
|---|---|---|---|
| `next` | 15.5.14 | MIT | ✅ |
| `react` | 19.2.4 | MIT | ✅ |
| `react-dom` | 19.2.4 | MIT | ✅ |
| `lucide-react` | 0.468.0 | ISC | ✅ |
| `typescript` | 5.9.3 | Apache-2.0 | ✅ |
| `tailwindcss` | 4.2.2 | MIT | ✅ |
| `@tailwindcss/postcss` | 4.2.2 | MIT | ✅ |
| `@types/react` | 19.2.14 | MIT | ✅ |
| `@types/react-dom` | 19.2.3 | MIT | ✅ |
| `@types/node` | 22.19.15 | MIT | ✅ |

### 4b. Transitive dependencies requiring attention

| Package | Version | License | Category | Notes |
|---|---|---|---|---|
| `lightningcss` (+ 11 platform variants) | 1.32.0 | MPL-2.0 | 🟡 MPL | CSS transform engine used by Tailwind v4. Build-time only. Not modified. |
| `@img/sharp-libvips-*` (10 platform variants) | 1.2.4 | LGPL-3.0-or-later | 🟡 LGPL | Native image processing for Next.js. Prebuilt binaries. Dynamic linking. LGPL exception applies. |
| `caniuse-lite` | 1.0.30001782 | CC-BY-4.0 | ⚠️ Data | Browser compat data, build-time only. CC-BY-4.0 requires attribution for the data. |

> `lightningcss` MPL-2.0: since COS does not modify lightningcss source files, the file-level copyleft does not propagate. The MPL-2.0 only requires sharing modifications to the MPL'd files themselves.
>
> `@img/sharp-libvips` LGPL-3.0: ships as prebuilt `.node` native binary. Node.js loads it via `require()` (dynamic linking). LGPL-3.0 Section 4 allows use with proprietary applications via dynamic linking without source disclosure. User can replace the library by swapping the `.node` file.
>
> `caniuse-lite` CC-BY-4.0: this is a data package (browser compatibility tables), not a software library. CC-BY-4.0 requires attribution in distributed copies. Since the dashboard is not distributed as a product — it is a local developer tool — this is low risk. If dashboard is ever shipped, add attribution.

---

## 5. Submodules

Three git submodules under `.claude/plugins/`:

| Submodule | Source | Commit Hash | License | Category | Notes |
|---|---|---|---|---|---|
| `hermes-agent` | https://github.com/NousResearch/hermes-agent.git | `fc8e4ebf8e` | MIT (Copyright 2025 Nous Research) | ✅ | Agent skill toolkit. Full MIT, permissive. |
| `caveman` | https://github.com/JuliusBrussee/caveman.git | `9ee0e352c6` (v1.3.0~13) | MIT (Copyright 2026 Julius Brussee) | ✅ | Claude plugin. Full MIT, permissive. |
| `pi-mono` | https://github.com/badlogic/pi-mono.git | `b9efafc535` (v0.0.2-3663) | MIT (Copyright 2025 Mario Zechner) | ✅ | Mono repo tooling. Full MIT, permissive. |

**All three submodules are MIT-licensed. No concerns for FSL release.**

> These submodules are optional plugins, not bundled into the core OS. They are referenced by `.gitmodules` but only available to users who run `git submodule update --init`. The MIT license on each is compatible with FSL distribution.

---

## 6. Phoenix ELv2 Analysis (Deep Dive)

### The discrepancy

ADR-058 (`docs/adrs/ADR-058-observability-migration-langfuse-to-phoenix.md`) states:
> "Apache 2.0 license (versus Langfuse's MIT with enterprise features behind a commercial tier — Phoenix is fully OSS)"

This is **factually incorrect as of current Phoenix documentation**. The Phoenix server is licensed under **Elastic License 2.0 (ELv2)**, not Apache 2.0. Arize-AI changed the license of the main `arize-phoenix` package after the original ADR was written.

### What COS actually installs

The `uv.lock` file (91 packages) does **not** contain `arize-phoenix`, `arize-phoenix-evals`, `arize-phoenix-client`, or `arize-phoenix-otel`. Phoenix lives in `requirements/dependency-lanes/observability.txt` as an explicit heavy lane:

- `arize-phoenix` (ELv2) — local UI/server and collector
- `arize-phoenix-otel` (Apache-2.0) — OTel instrumentation bridge

Operators install the lane explicitly with `bash scripts/dependency-lane.sh install observability`; it is not bundled in the COS core package.

### How COS uses Phoenix

From code analysis of `lib/record_completion.py` and `packages/ecosystem-tools/lib/observability.py`:

1. **Usage mode**: COS emits OpenTelemetry spans to a Phoenix collector at `localhost:6006`. Phoenix is a **local trace viewer** — a UI that runs on the operator's own machine. COS itself is the OTel *producer*; Phoenix is the *consumer/viewer*.
2. **Integration path**: `from phoenix.otel import register` — the `phoenix.otel` module from the optional observability lane registers an OTel tracer provider. The main `arize-phoenix` package only runs when the user explicitly executes `phoenix serve`.
3. **Embedding**: Phoenix is **not embedded** in COS. It is a separately installed pip package that the operator runs independently.
4. **Optionality**: All Phoenix imports are wrapped in `try/except`. If Phoenix is not installed, COS silently skips tracing. Phoenix is documented as optional in `cognitive-os.yaml` (`mode: pip`).
5. **No customer exposure**: Phoenix runs locally for the developer/operator. It is not exposed to end-customers or provided as a service.

### ELv2 prohibition analysis

The key ELv2 restriction is:
> "You may not provide the software to third parties as a hosted or managed service, where the service provides users with access to any substantial set of the features or functionality of the software."

Applied to COS:

| Question | Answer | ELv2 Implication |
|---|---|---|
| Does COS bundle and ship `arize-phoenix` as part of the product? | No — not in uv.lock, operator installs separately | No concern |
| Does COS expose Phoenix UI to customers/third parties? | No — local only, `localhost:6006` | No concern |
| Does COS host Phoenix as a service? | No — operator runs `phoenix serve` on their own machine | No concern |
| Does COS embed Phoenix in a cloud product that provides Phoenix features to users? | No — COS is a local developer tool | No concern |
| Does COS circumvent Phoenix license keys? | No | No concern |

### ELv2 FAQ reference (Elastic's guidance)

Elastic's FAQ for internal use states: "You may continue to use [the software] for free... for access to [features] inside your own applications." The COS usage pattern — operator runs Phoenix locally for their own observability — falls squarely within ELv2 internal-use permissions.

The prohibited case ("provide... as a managed service") would apply only if COS were hosting Phoenix centrally and providing its UI to customers. COS does the opposite: it instructs users to run Phoenix locally.

### Recommendation

**🟡 YELLOW with qualification — proceed with annotation**

The `arize-phoenix` ELv2 package is **not bundled** in COS and **not provided to third parties**. The usage pattern (local developer observability tool, operator-installed, not exposed externally) is within ELv2 permitted use.

**Required action**: complete. ADR-058, NOTICE, `cognitive-os.yaml`, catalog docs, and Phoenix skill docs now state that `arize-phoenix` (the server, ELv2) is an optional operator-installed tool in the observability dependency lane, not a COS core dependency. `arize-phoenix-otel` remains Apache-2.0.

**If COS Cloud (SaaS offering) is planned**: Before hosting Phoenix centrally and exposing its UI to customers, obtain a commercial license from Arize-AI. The free ELv2 does not cover "managed service" use.

---

## 7. Action Items Before FSL Launch

### 7a. Items to REMOVE (🔴 blockers)

**None identified.** Zero AGPL, GPL, CC-BY-NC, or SSPL packages in the locked dependency graph.

### 7b. Items to ANNOTATE in NOTICE.md (🟡 required)

| Package | License | Required action |
|---|---|---|
| `certifi` | MPL-2.0 | Attribution + link to source. No modifications expected. |
| `tqdm` | MPL-2.0 AND MIT | Use under MIT terms. Note dual license in NOTICE. |
| `pytest-rerunfailures` | MPL-2.0 | Dev/test dependency. Annotate. Not shipped in release artifact. |
| `lightningcss` (+ platform variants) | MPL-2.0 | Build-time dep via Tailwind. No modifications. Attribution in NOTICE. |
| `@img/sharp-libvips-*` | LGPL-3.0-or-later | Prebuilt native binary, dynamic-linked via Node. Note LGPL + dynamic linking in NOTICE. |
| `caniuse-lite` | CC-BY-4.0 | Data attribution: "Contains data from caniuse.com, CC-BY-4.0." |
| `arize-phoenix` (operator-installed) | ELv2 | Add documentation note: not bundled, operator installs, ELv2 terms apply to operator. |

### 7c. Runtime configuration / documentation changes

1. **ADR-058 correction**: done — `docs/adrs/ADR-058-observability-migration-langfuse-to-phoenix.md` states ELv2 for the server and explains the local-use boundary.
2. **`cognitive-os.yaml` and install docs**: done — Phoenix is documented as an optional operator-installed dependency lane governed by ELv2, with Apache-2.0 bridge/client packages where applicable.
3. **Node dashboard**: Document that `lightningcss` and `sharp-libvips` are build-time/native transitive deps from Next.js with MPL-2.0 / LGPL-3.0 respectively. If the dashboard is ever distributed as a product (not just a dev tool), full NOTICE requirements apply.

### 7d. License compatibility statement

The Cognitive OS core locked dependency graph (Python `uv.lock`, Go `go.mod`) contains exclusively MIT, Apache-2.0, BSD-2/3, ISC, PSF, and MPL-2.0 (no modifications) licensed packages. This is fully compatible with FSL 1.1 distribution. The three git submodule plugins are all MIT-licensed.

---

## 8. NOTICE.md Skeleton

```markdown
# NOTICE

Cognitive OS — Third-Party License Acknowledgments

This product includes software developed by third parties under the following licenses:

---

## Apache License 2.0

The following packages are licensed under the Apache License, Version 2.0:

- openai (https://github.com/openai/openai-python)
- aiofiles (https://github.com/Tinche/aiofiles)
- docker (https://github.com/docker/docker-py)
- requests (https://github.com/psf/requests)
- pytest-asyncio (https://github.com/pytest-dev/pytest-asyncio)
- testcontainers (https://github.com/testcontainers/testcontainers-python)
- cryptography (https://github.com/pyca/cryptography)
- TypeScript (https://github.com/microsoft/TypeScript)
- distro (https://github.com/python-distro/distro)
- coverage (https://github.com/nedbat/coveragepy)

Full license text: https://www.apache.org/licenses/LICENSE-2.0

---

## MIT License

The following packages are licensed under the MIT License:

- pydantic / pydantic-core / pydantic-settings
- fastapi / starlette / uvicorn
- jinja2 / markupsafe
- pyyaml
- rich / textual
- redis
- httpx / httpcore
- claude-agent-sdk
- mcp
- pytest and plugins (pytest-cov, pytest-xdist, pytest-timeout, pytest-smell)
- openai SDK
- ruff / vulture
- next.js
- react / react-dom
- tailwindcss / @tailwindcss/postcss
- @types/react, @types/react-dom, @types/node

---

## BSD Licenses (2-Clause and 3-Clause)

The following packages are licensed under BSD-2-Clause or BSD-3-Clause:

- cryptography (Apache-2.0 OR BSD-3-Clause)
- pygments
- httpx
- uvicorn / starlette
- mutmut / grimp
- google/uuid (Go)
- modernc.org/sqlite, modernc.org/memory, modernc.org/mathutil (Go)
- golang.org/x/sys (Go)
- github.com/remyoudompheng/bigfft (Go)
- pydantic-core (MIT)
- sse-starlette (BSD-3-Clause)

---

## Mozilla Public License 2.0 (MPL-2.0)

The following packages are licensed under the Mozilla Public License 2.0.
These packages have not been modified. Source code is available at the URLs below.

- certifi (https://github.com/certifi/python-certifi)
  Mozilla CA Bundle — https://www.mozilla.org/en-US/MPL/2.0/
- pytest-rerunfailures (https://github.com/pytest-dev/pytest-rerunfailures)
  Development/test dependency only; not included in release artifacts.
- tqdm (https://github.com/tqdm/tqdm) — used under MIT dual-license terms
- lightningcss (https://github.com/parcel-bundler/lightningcss)
  Build-time dependency (Tailwind CSS v4); not shipped in release artifacts.

---

## GNU Lesser General Public License v3 (LGPL-3.0-or-later)

The following packages are licensed under LGPL-3.0-or-later and are linked
dynamically at runtime. Users may replace these libraries with compatible versions.

- @img/sharp-libvips (https://github.com/lovell/sharp-libvips)
  Prebuilt native binary; dynamically loaded by Next.js image optimization.
  Source available at: https://github.com/lovell/sharp-libvips

---

## Creative Commons Attribution 4.0 (CC-BY-4.0)

- caniuse-lite (https://github.com/nicolo-ribaudo/caniuse-lite)
  Contains data from caniuse.com. © Alexis Deveria.
  Licensed under CC-BY-4.0: https://creativecommons.org/licenses/by/4.0/
  This data is used at build time only by Next.js tooling.

---

## MIT — Git Submodule Plugins (optional, not bundled in core)

- hermes-agent (https://github.com/NousResearch/hermes-agent) — Copyright 2025 Nous Research
- caveman (https://github.com/JuliusBrussee/caveman) — Copyright 2026 Julius Brussee
- pi-mono (https://github.com/badlogic/pi-mono) — Copyright 2025 Mario Zechner

---

## Elastic License 2.0 (ELv2) — Operator-installed, not bundled

The following tool is NOT bundled in Cognitive OS. It is an optional runtime
service that operators may install separately on their own machines:

- arize-phoenix (https://github.com/Arize-ai/phoenix)
  License: Elastic License 2.0 — https://github.com/Arize-ai/phoenix/blob/main/LICENSE
  Operators who install arize-phoenix are bound by ELv2 terms directly.
  Cognitive OS integration libraries (arize-phoenix-client, arize-phoenix-otel)
  are Apache-2.0 licensed.
```

---

## 9. Trust Score

### **MEDIUM-HIGH — Safe to release with minor pre-launch corrections**

**What was found:**
- Zero AGPL, GPL v2/v3, SSPL, or CC-BY-NC blockers in the locked dependency graph
- All three git submodules are MIT-licensed
- All Go dependencies are green (MIT/BSD-3)
- Python core dependencies are clean (MIT/Apache/BSD)
- Node dashboard dependencies are clean with two expected yellow items (MPL lightningcss, LGPL sharp-libvips) that are standard in any Next.js project

**Material discrepancy:**
- Historical ADR-058 text incorrectly documented `arize-phoenix` as Apache 2.0; active ADR-058 and install docs now state ELv2 server / Apache-2.0 bridge packages. This remains a documentation risk to keep audited because `arize-phoenix` is not in `uv.lock` and must stay out of the bundled product.

**Confidence caveats:**
1. The pip-licenses scan ran against the full virtual environment, which included packages beyond `uv.lock`. The report above focuses exclusively on `uv.lock` contents (91 packages). If additional extras (`direct_providers`, `security`, etc.) are bundled in the release artifact, those should be rescanned.
2. `modernc.org/mathutil` license was not detectable by go-licenses locally (no LICENSE file in cache); manually confirmed BSD-3-Clause via pkg.go.dev. Medium confidence.
3. `nemoguardrails` appeared in the environment scan (Apache 2.0 with "Other/Proprietary License" classifier). It is NOT in `uv.lock` and is not a project dependency. If it were added, the "Other/Proprietary License" classifier would require investigation of the bundled NVIDIA content.

**Pre-launch checklist:**
- [x] Correct ADR-058 license statement (Apache 2.0 → ELv2)
- [x] Add NOTICE to repo root with MPL/LGPL/CC/Phoenix annotations
- [x] Annotate `cognitive-os.yaml` and install docs: Phoenix is ELv2, operator installs separately
- [ ] Confirm dashboard is not distributed as a product artifact (if it is, LGPL/MPL/CC annotations are mandatory)
- [ ] If future cloud/SaaS offering plans to host Phoenix centrally: obtain Arize commercial license before launch

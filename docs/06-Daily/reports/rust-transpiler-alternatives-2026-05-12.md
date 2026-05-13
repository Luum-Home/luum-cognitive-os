# Rust Transpiler & Migration Alternatives — 2026-05-12

## Part 1 — Review of Current Rust Line of Work

### Goal
Stage an evidence-driven migration of selected COS surfaces (Py/Bash/Go) to Rust without a big-bang rewrite. The work establishes (a) an inventory, (b) one production-grade Rust slice as parity reference, (c) a transpiler evaluation lane.

### Commit chain
- **be293353 — inventory**: classifies 2,501 tracked `*.py/*.go/*.sh` files into 6 categories. Defines 4 migration waves; picks ADR-283 script-exposure audit as Wave 1 (CSV + architecture doc).
- **05bb13c2 — first crate**: lands `crates/cos-script-exposure-audit-rs` (lib+main+parity tests) + root Cargo workspace. Deps `anyhow`/`clap`/`json`/`yaml-rust2` (chose `json` over `serde_json` to avoid `ryu` BSL-1.0). License audit: 45 packages, 0 blocked. Python remains authoritative.
- **c643e97e — transpiler lane**: harness `scripts/cos_rust_transpiler_eval.py` runs `py2many` + `tnk` against 3 real COS scripts. **All 6 trials failed** (`high` manual-fix cost or blocked).
- **b5e77615 — fair probe**: adds capability fixtures (pure-int/list, simple parsing, dict transform). Result: **`tnk` passes only the pure-ints fixture; `py2many` non-compiling on all three**.

### Pending
1. Prove parity for `cos-script-exposure-audit-rs` on real ledgers, expand to more Wave-1 diagnostics.
2. Transpilers stay **lab-only** — no auto-replacement; manual Rust slices with golden parity tests is the production method.
3. Wave 2 (CLI) / Wave 3 (runtime) deferred until Wave 1 yields evidence.

## Part 2 — Alternative Tools Inventory

Sorted by relevance to the COS migration plan (deterministic diagnostic scanners → CLI → runtime libraries).

| # | Tool | Pair | Maturity | License | Last activity | Fit verdict |
|---|---|---|---|---|---|---|
| # | Tool | Pair | Maturity | License | Verdict |
|---|---|---|---|---|---|
| 1 | [Depyler](https://github.com/paiml/depyler) | Py→Rust | Beta v4.1, MCP | MIT | **Top alt now wired into lane** — single-shot compile claim; gather COS-local evidence before promotion. |
| 2 | [py2many](https://github.com/py2many/py2many) | Py→multi | Beta | MIT | Already evaluated; keep as draft. |
| 3 | [Tsuchinoko/tnk](https://github.com/tanep3/Tsuchinoko) | Py→Rust | Beta 57% | MIT | Already evaluated; pure-ints only. |
| 4 | [PyO3 + maturin](https://pyo3.rs/) | Py↔Rust FFI | Prod | Apache/MIT | **Best hot-path pattern**; ship as wheel ([guide](https://www.nandann.com/blog/rust-pyo3-python-extensions-guide)). |
| 5 | [Codon](https://github.com/exaloop/codon) | Py→native | Prod, Apache-2.0 (2025) | Apache | 900× NumPy; subset only ([blog](https://www.exaloop.io/blog/codon-2025)). |
| 6 | [Mojo](https://mojolang.org/) | Py-super→native | Beta | proprietary | License blocks until OSS ([wiki](https://en.wikipedia.org/wiki/Mojo_(programming_language))). |
| 7 | [pyrs](https://github.com/konchunas/pyrs) | Py→Rust | Experimental | MIT | Skip; superseded. |
| 8 | [Pypyrust](https://github.com/MarcusRainbow/pypyrust) | Py→Rust | Hobby | MIT | Skip. |
| 9 | [PyCrust](https://github.com/JediRhymeTrix/PyCrust) | Py→Rust LLM | Alpha | MIT | Outdated GPT-3.5. |
| 10 | [Workik](https://workik.com/python-to-rust-code-converter) | LLM SaaS | Commercial | prop | SaaS risk. |
| 11 | [LowCodeRust](https://lowcoderust.com/) | AI assistant | Commercial | prop | SaaS. |
| 12 | Claude Code / Cursor / Aider | any↔any | Prod | various | **Most credible AI route** — diff/translate/test loop ([compare](https://www.requesty.ai/blog/agentic-coding-tools-compared-2026-claude-code-cursor-codex-aider), [InfoWorld](https://www.infoworld.com/article/4135218/what-i-learned-using-claude-sonnet-to-migrate-python-to-rust.html)). |
| 13 | [SafeTrans/SACTOR](https://arxiv.org/html/2505.10708) | C/Py→Rust | Research | paper | 54→80% w/ repair ([bench](https://arxiv.org/html/2411.13990v3), [CRUST](https://www.cs.utexas.edu/~isil/crust-bench.pdf)). |
| 14 | [Rusthon](https://github.com/rusthon/Rusthon) | Pythonic→Rust | Dormant | — | Skip. |
| 15 | [RustPython](https://github.com/RustPython/RustPython) | Py interp in Rust | Beta | MIT | Interpreter, not transpiler. |
| 16 | [Numba](https://numba.pydata.org/) | Py JIT | Prod | BSD | NumPy-only. |
| 17 | [Cython](https://cython.org/) | Py→C | Prod | Apache | Middle ground if Rust stalls. |
| 18 | [Nuitka](https://nuitka.net/) | Py→C++ AOT | Prod | Apache | Whole-program compile. |
| 19 | [mypyc](https://mypyc.readthedocs.io/) | typed-Py→C | Beta | MIT | Mypy/Black use. |
| 20 | [Pyston](https://github.com/pyston/pyston) | Py JIT | Maint | PSF | Skip. |
| 21 | [Pyjion](https://github.com/microsoft/Pyjion) | Py→.NET JIT | Archived | MIT | Skip. |
| 22 | [Taichi](https://www.taichi-lang.org/) | Py-DSL→GPU | Prod | Apache | Out of scope. |
| 23 | [Triton](https://github.com/triton-lang/triton) | Py-DSL→GPU | Prod | MIT | Out of scope. |
| 24 | [JAX/Pallas](https://jax.readthedocs.io/) | Py→XLA | Prod | Apache | Out of scope. |
| 25 | [c2rust v0.21](https://github.com/immunant/c2rust) | C→Rust | Prod | BSD | Reference quality bar ([blog](https://immunant.com/blog/2025/10/c2rust_release/)). |
| 26 | [C2SaferRust](https://arxiv.org/html/2501.14257v1) | C→safe Rust | Research | paper | LLM+verifier pattern. |
| 27 | [OpenRewrite](https://github.com/openrewrite/rewrite) | Java refactor | Prod | Apache | Recipe-pattern model. |
| 28 | [Copilot Modernization](https://learn.microsoft.com/en-us/azure/developer/github-copilot-app-modernization/overview) | Java upgrades | Commercial | prop | Blueprint only. |
| 29 | [Comby](https://github.com/comby-tools/comby) | Struct rewrite | Prod | Apache | **Complementary** prep-pass tool. |
| 30 | [Semgrep](https://github.com/semgrep/semgrep) | Static + autofix | Prod | LGPL | Already in COS. |
| 31 | [ast-grep](https://ast-grep.github.io/) | TS rewrite | Prod | MIT | Lightweight Comby. |
| 32 | [tree-sitter](https://tree-sitter.github.io/) | Parser base | Prod | MIT | Custom migrator base. |
| 33 | [gosh](https://github.com/mumoshu/gosh) | bash→Go | Beta | Apache | If Go appears. |
| 34 | [bashscript](https://github.com/niieani/bashscript) | TS→bash | Dormant | MIT | Wrong direction. |
| 35 | [Amber](https://amber-lang.com/) | Amber→bash | Beta | GPL-3 | License blocker. |
| 36 | [Oils OSH/YSH](https://github.com/oils-for-unix/oils) | bash upgrade | Beta | Apache | Smoothest bash modernization. |
| 37 | [Nushell](https://www.nushell.sh/) | Rust shell | Prod | MIT | Reference, not translator. |
| 38 | [Murex](https://murex.rocks/) | Go shell | Beta | GPL-2 | License blocker. |
| 39 | [xonsh](https://xon.sh/) | Py shell | Prod | BSD | Not a migration tool. |
| 40 | [cmd_lib](https://docs.rs/cmd_lib)/[sh_inline](https://docs.rs/sh-inline)/[rust-script](https://rust-script.org/) | bash-like Rust | Prod | MIT/Apache | **Landing pattern** for hook port. |
| 41 | [CodingFleet](https://codingfleet.com/code-converter/bash/rust/) | LLM SaaS | Commercial | prop | Avoid. |
| 42 | [shellharden](https://github.com/anordal/shellharden) + [shfmt](https://github.com/mvdan/sh) | bash hardening | Prod | MIT/BSD | Pre-migration hardening. |
| 43 | [pyo3_bindgen](https://github.com/AndrejOrsula/pyo3_bindgen) | auto FFI | Beta | MIT/Apache | Speeds PyO3 bindings. |
| 44 | [awesome-rust-llm](https://github.com/jondot/awesome-rust-llm) | curated list | — | MIT | Rust LLM-lib catalog. |

## Three Recommendations

1. **Evaluate Depyler as the third transpiler in the existing lane**. It matches the lane's contract (annotated Py → Rust), claims single-shot compile, and ships under MIT — minimal risk, maximum signal. Run capability-mode + script-mode in the same harness before any promotion.
2. **Adopt PyO3 + maturin as the canonical "selective migration" pattern** alongside the parity-crate pattern. The Wave-1 crate replaces a whole script; PyO3 enables surgical hot-path replacement when a full port is over-engineering. Cite as the second sanctioned route.
3. **Stand up a Claude-Code-driven LLM migration loop** (translate → `cargo check` → `cargo test` → repair, capped at N iterations). Literature shows iterative repair lifts success 54%→80%; this is the most credible non-transpiler path and aligns with COS's existing parity-test gate. Keep transpilers as draft generators feeding into this loop.

---

*Sources: 44 cited inline above. Commits and report paths refer to the repository root.*

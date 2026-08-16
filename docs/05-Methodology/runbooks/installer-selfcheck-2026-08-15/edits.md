# Edits to existing files

Applied in the order below to a clone of the origin at the HEAD recorded in the README.
The self-check script's own edits are already folded into `new-files/`.

## `scripts/hook-timing-wrapper.sh`

**Replace:**

```
# ── Resolve metrics path ─────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$("$SCRIPT_DIR/cos-root" project)"
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
```

**With:**

```
# ── Resolve metrics path ─────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Resolve the project root WITHOUT requiring a sibling `cos-root`.
#
# This wrapper is re-homed by the installer into
# .cognitive-os/hooks/cos/_lib/, while `cos-root` is tagged `SCOPE: os-only`
# and is therefore never projected into a consumer install. Depending on a
# sibling that cannot ship made every consumer's hook-timing observability
# fail on line 1 — silently, because a failed command substitution left
# PROJECT_DIR empty and every later path resolved under "/".
#
# The env vars below are exactly the ones scripts/cos-root honours, in the same
# precedence order, so behaviour is unchanged where cos-root IS present.
cos_resolve_project_root() {
  local candidate
  candidate="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-}}}"
  if [ -n "$candidate" ] && [ -d "$candidate" ]; then
    (cd "$candidate" && pwd) && return 0
  fi
  # Prefer a real cos-root when one is a sibling (COS self-hosting layout).
  if [ -x "$SCRIPT_DIR/cos-root" ]; then
    candidate="$("$SCRIPT_DIR/cos-root" project 2>/dev/null || true)"
    if [ -n "$candidate" ] && [ -d "$candidate" ]; then
      printf '%s\n' "$candidate" && return 0
    fi
  fi
  # Walk up from this script looking for an installed .cognitive-os/ root.
  # From .cognitive-os/hooks/cos/_lib/ this finds the consumer project root.
  candidate="$SCRIPT_DIR"
  while [ "$candidate" != "/" ] && [ -n "$candidate" ]; do
    if [ -d "$candidate/.cognitive-os" ] || [ -f "$candidate/cognitive-os.yaml" ]; then
      printf '%s\n' "$candidate" && return 0
    fi
    candidate="$(dirname "$candidate")"
  done
  # Last resort: cwd, then the script dir. Never empty.
  if [ -d "$PWD/.cognitive-os" ] || [ -f "$PWD/cognitive-os.yaml" ]; then
    printf '%s\n' "$PWD" && return 0
  fi
  printf '%s\n' "$PWD"
}

PROJECT_DIR="$(cos_resolve_project_root)"
# Defensive: an empty PROJECT_DIR would silently redirect every metrics write
# to "/". Never let that happen again.
[ -n "$PROJECT_DIR" ] || PROJECT_DIR="$PWD"
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
```

## `scripts/lib_closure.py`

**Replace:**

```
def _sha256_of_file(path: Path) -> str:
```

**With:**

```
def extract_lib_modules_from_path(path: Path) -> Set[str]:
    """Extract the `cos_lib.<mod>` reference set from any shipped entry point.

    Shell hooks go through :func:`extract_lib_modules_from_hook` (regex + the
    heredoc AST upgrade). Python entry points — `hooks/_lib/*.py` and the
    `.cognitive-os/bin/*.py` primitives — are `ast.parse`d as a whole, because
    their imports are ordinary top-level/nested imports rather than heredoc
    bodies. Those files are copied into consumer installs verbatim (e.g. by the
    `shutil.copytree(hooks/_lib)` in cos_init.py) but were never part of the
    closure seed set, so every `cos_lib.*` module reachable ONLY through them
    was silently dropped from every install.
    """
    if path.suffix == ".py":
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return set()
        # Union both strategies: AST is authoritative for real imports, and the
        # regex still catches `-m cos_lib.<mod>` forms inside subprocess calls.
        return _extract_lib_modules_ast(source) | _extract_lib_modules_from_text(source)
    return extract_lib_modules_from_hook(path)


def _sha256_of_file(path: Path) -> str:
```

**Replace:**

```
    for hook_path in hook_paths:
        hook_path = Path(hook_path)
        if not hook_path.is_file():
            continue
        for mod in extract_lib_modules_from_hook(hook_path):
            if mod not in seen:
                seen.add(mod)
                worklist.append(mod)
```

**With:**

```
    for hook_path in hook_paths:
        hook_path = Path(hook_path)
        if not hook_path.is_file():
            continue
        for mod in extract_lib_modules_from_path(hook_path):
            if mod not in seen:
                seen.add(mod)
                worklist.append(mod)
```

## `scripts/cos_init.py`

**Replace:**

```
    closure = lib_closure.compute_closure(projected_hook_paths, cos_source)
```

**With:**

```
    # The seed set must include EVERY shipped file that can import cos_lib.*,
    # not just the *.sh hooks. hooks/_lib/ is copied wholesale by the copytree
    # above, and its Python members (e.g. dispatch_gate_check.py) import
    # cos_lib modules that were therefore never projected — which is how the
    # agent circuit breaker came to be dead in every consumer install:
    # dispatch_gate_check.py imports cos_lib.circuit_breaker (shipped) and then
    # cos_lib.record_completion (not shipped) in the same try block, so the
    # ImportError aborted the block before can_launch() ever ran.
    closure_seed_paths = list(projected_hook_paths)
    installed_hook_lib = Path(hooks_dest) / "_lib"
    if installed_hook_lib.is_dir():
        closure_seed_paths.extend(sorted(installed_hook_lib.glob("*.py")))
    # The .cognitive-os/bin/* primitives are installed by the _install_*
    # helpers below/above and import cos_lib too.
    installed_bin = project_dir / ".cognitive-os" / "bin"
    if installed_bin.is_dir():
        closure_seed_paths.extend(sorted(installed_bin.glob("*.py")))

    closure = lib_closure.compute_closure(closure_seed_paths, cos_source)
```

**Replace:**

```
    # ── 5b. Project the cos_lib.* dependency closure for the installed hooks ──
    # (docs/02-Decisions/designs/hook-lib-projection-contract.md §2.2). This
    # extends — does not replace — the existing 2-module duplicates subset
    # installed by _install_quality_duplicates_primitive(); closure members
    # simply coexist in the same .cognitive-os/cos_lib/ package.
    lib_closure_dest = project_dir / ".cognitive-os" / "cos_lib"
    lib_closure_dest.mkdir(parents=True, exist_ok=True)
    lib_init_file = lib_closure_dest / "__init__.py"
    if not lib_init_file.exists():
        source_init = cos_source / "cos_lib" / "__init__.py"
        if source_init.is_file():
            shutil.copy2(str(source_init), str(lib_init_file))
        else:
            lib_init_file.write_text("", encoding="utf-8")

    # The seed set must include EVERY shipped file that can import cos_lib.*,
    # not just the *.sh hooks. hooks/_lib/ is copied wholesale by the copytree
    # above, and its Python members (e.g. dispatch_gate_check.py) import
    # cos_lib modules that were therefore never projected — which is how the
    # agent circuit breaker came to be dead in every consumer install:
    # dispatch_gate_check.py imports cos_lib.circuit_breaker (shipped) and then
    # cos_lib.record_completion (not shipped) in the same try block, so the
    # ImportError aborted the block before can_launch() ever ran.
    closure_seed_paths = list(projected_hook_paths)
    installed_hook_lib = Path(hooks_dest) / "_lib"
    if installed_hook_lib.is_dir():
        closure_seed_paths.extend(sorted(installed_hook_lib.glob("*.py")))
    # The .cognitive-os/bin/* primitives are installed by the _install_*
    # helpers below/above and import cos_lib too.
    installed_bin = project_dir / ".cognitive-os" / "bin"
    if installed_bin.is_dir():
        closure_seed_paths.extend(sorted(installed_bin.glob("*.py")))

    closure = lib_closure.compute_closure(closure_seed_paths, cos_source)
    closure_manifest: dict[str, dict] = {}
    for mod_name, entry in closure.items():
        source_mod_path = cos_source / entry.source_real_path
        # ADR-019 scope governance: never project a `cos_lib` module whose
        # header declares `SCOPE: os-only` into a consumer install, even if
        # it is transitively reachable from a `both`-scoped hook's import
        # graph (see test_primitive_scope_governance.py
        # ::test_default_consumer_projection_contains_no_os_only_markers).
        # A `both`/`project`-scoped hook that only works via an os-only
        # module is a real dependency bug in that hook, not a reason to
        # leak the os-only module — skip it here (the existing
        # static-closure-miss fail-open backstop in lib_closure.py already
        # tolerates modules that are absent from the projected package).
        if not scope_allows(str(source_mod_path), os.environ.get("COS_INSTALL_SCOPE", "both")):
            continue
        dest_mod_path = lib_closure_dest / f"{mod_name}.py"
        shutil.copy2(str(source_mod_path), str(dest_mod_path))
        closure_manifest[mod_name] = entry.to_manifest_dict()

    manifest_path = lib_closure_dest / ".closure-manifest.json"
    manifest_path.write_text(
        json.dumps(closure_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    # ── 6. Install skills ─────────────────────────────────────────────
```

**With:**

```
    # ── 5b. (moved) cos_lib.* dependency closure ──────────────────────
    # The closure now runs in step 7c, AFTER the .cognitive-os/bin/*
    # primitives are installed, because those primitives are themselves
    # cos_lib importers and must be part of the closure seed set.

    # ── 6. Install skills ─────────────────────────────────────────────
```

**Replace:**

```
    provenance_scan_installed = _install_provenance_scan_guardrail(project_dir, cos_source)
    quality_duplicates_installed = _install_quality_duplicates_primitive(project_dir, cos_source)
    so_impact_eval_installed = _install_so_impact_eval_primitive(project_dir, cos_source)
    task_closure_gate_installed = _install_task_closure_gate_primitive(project_dir, cos_source)
```

**With:**

```
    provenance_scan_installed = _install_provenance_scan_guardrail(project_dir, cos_source)
    quality_duplicates_installed = _install_quality_duplicates_primitive(project_dir, cos_source)
    so_impact_eval_installed = _install_so_impact_eval_primitive(project_dir, cos_source)
    task_closure_gate_installed = _install_task_closure_gate_primitive(project_dir, cos_source)

    # ── 7c. Project the cos_lib.* dependency closure ──────────────────
    # (docs/02-Decisions/designs/hook-lib-projection-contract.md §2.2). This
    # extends — does not replace — the existing 2-module duplicates subset
    # installed by _install_quality_duplicates_primitive(); closure members
    # simply coexist in the same .cognitive-os/cos_lib/ package.
    #
    # Runs here (not in step 5) so that everything capable of importing
    # cos_lib.* has already landed and can seed the closure.
    lib_closure_dest = project_dir / ".cognitive-os" / "cos_lib"
    lib_closure_dest.mkdir(parents=True, exist_ok=True)
    lib_init_file = lib_closure_dest / "__init__.py"
    if not lib_init_file.exists():
        source_init = cos_source / "cos_lib" / "__init__.py"
        if source_init.is_file():
            shutil.copy2(str(source_init), str(lib_init_file))
        else:
            lib_init_file.write_text("", encoding="utf-8")

    # The seed set must include EVERY shipped file that can import cos_lib.*,
    # not just the *.sh hooks. hooks/_lib/ is copied wholesale by the copytree
    # in step 5, and its Python members (e.g. dispatch_gate_check.py) import
    # cos_lib modules that were therefore never projected — which is how the
    # agent circuit breaker came to be dead in every consumer install:
    # dispatch_gate_check.py imports cos_lib.circuit_breaker (shipped) and then
    # cos_lib.record_completion (not shipped) in the same try block, so the
    # ImportError aborted the block before can_launch() ever ran.
    closure_seed_paths = list(projected_hook_paths)
    installed_hook_lib = Path(hooks_dest) / "_lib"
    if installed_hook_lib.is_dir():
        closure_seed_paths.extend(sorted(installed_hook_lib.glob("*.py")))
    installed_bin = project_dir / ".cognitive-os" / "bin"
    if installed_bin.is_dir():
        closure_seed_paths.extend(sorted(installed_bin.glob("*.py")))

    closure = lib_closure.compute_closure(closure_seed_paths, cos_source)
    closure_manifest: dict[str, dict] = {}
    for mod_name, entry in closure.items():
        source_mod_path = cos_source / entry.source_real_path
        # ADR-019 scope governance: never project a `cos_lib` module whose
        # header declares `SCOPE: os-only` into a consumer install, even if
        # it is transitively reachable from a `both`-scoped hook's import
        # graph (see test_primitive_scope_governance.py
        # ::test_default_consumer_projection_contains_no_os_only_markers).
        # A `both`/`project`-scoped hook that only works via an os-only
        # module is a real dependency bug in that hook. The install
        # self-check (step 12) now reports that as `scope_conflict` instead
        # of letting it pass silently.
        if not scope_allows(str(source_mod_path), os.environ.get("COS_INSTALL_SCOPE", "both")):
            continue
        dest_mod_path = lib_closure_dest / f"{mod_name}.py"
        shutil.copy2(str(source_mod_path), str(dest_mod_path))
        closure_manifest[mod_name] = entry.to_manifest_dict()

    manifest_path = lib_closure_dest / ".closure-manifest.json"
    manifest_path.write_text(
        json.dumps(closure_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    # ── 7d. Seed the confidentiality config ───────────────────────────
    # The confidentiality-enforcer hook reads
    # .cognitive-os/confidentiality.yaml. Without it, load_protected_terms()
    # returns an empty ProtectedTerms and three of the scanner's four
    # detection categories (protected_term, repo_url, attribution_phrase)
    # are dark — silently, because the hook fails open. Ship the template so
    # the file exists with the schema the scanner actually parses; leave the
    # lists empty because only the operator knows what is confidential.
    conf_dest = project_dir / ".cognitive-os" / "confidentiality.yaml"
    if not conf_dest.exists():
        conf_src = cos_source / "templates" / "confidentiality.yaml.template"
        if conf_src.is_file():
            shutil.copy2(str(conf_src), str(conf_dest))
```

**Replace:**

```
    # ── 12. Add to .gitignore ─────────────────────────────────────────
    _update_gitignore(project_dir)

    # ── Summary ───────────────────────────────────────────────────────
    print()
    print(f"Cognitive OS initialized ({mode.lstrip('-')} mode)")
    print(f"  Rules:  {rules_installed} installed")
    print(f"  Hooks:  {hooks_installed} registered")
    print(f"  Skills: {skills_installed} available")
    print()
    print("Next: start coding! The AI knows what to do.")
    print()
    if mode == "--default":
        print("Need maximum coverage? Re-run with --full:")
        print(f"  bash {cos_source}/scripts/cos-init.sh --full")

    return 0
```

**With:**

```
    # ── 12. Add to .gitignore ─────────────────────────────────────────
    _update_gitignore(project_dir)

    # ── 13. Install self-check ────────────────────────────────────────
    # The installer ships an allowlisted subset of this repo. Nothing used to
    # verify the subset was closed under its own imports, and every
    # consumer-side reference sits inside `try/except: pass` — so a module the
    # installer forgot produced no error, just a feature that silently never
    # ran. This is the check that catches that class of defect.
    #
    # It FAILS THE INSTALL (non-zero exit). An installer that reports success
    # while shipping something that cannot import is the bug being fixed here,
    # so this must not be advisory. COS_SKIP_INSTALL_SELFCHECK=1 exists for
    # emergency unblocking and prints a loud warning.
    selfcheck_findings = 0
    if os.environ.get("COS_SKIP_INSTALL_SELFCHECK") == "1":
        print(
            "WARNING: install self-check SKIPPED via COS_SKIP_INSTALL_SELFCHECK=1. "
            "The install has NOT been verified to satisfy its own imports.",
            file=sys.stderr,
        )
    else:
        try:
            import cos_install_selfcheck

            selfcheck_code, findings = cos_install_selfcheck.run(project_dir, cos_source)
            selfcheck_findings = len(findings)
            if selfcheck_code != 0:
                print(cos_install_selfcheck.format_report(findings), file=sys.stderr)
        except Exception as exc:  # noqa: BLE001
            # A self-check that cannot run is itself a failure. Do not fail open
            # here — failing open is precisely how the three original defects
            # survived in 18 installs.
            print(
                f"ERROR: install self-check could not run: {exc}\n"
                "       Treating this as a failed install. Re-run with "
                "COS_SKIP_INSTALL_SELFCHECK=1 only if you accept an unverified install.",
                file=sys.stderr,
            )
            return 1

    # ── Summary ───────────────────────────────────────────────────────
    print()
    print(f"Cognitive OS initialized ({mode.lstrip('-')} mode)")
    print(f"  Rules:  {rules_installed} installed")
    print(f"  Hooks:  {hooks_installed} registered")
    print(f"  Skills: {skills_installed} available")
    print()
    if selfcheck_findings:
        print(
            f"INSTALL INCOMPLETE: {selfcheck_findings} self-check finding(s) above.",
            file=sys.stderr,
        )
        return 1
    print("Next: start coding! The AI knows what to do.")
    print()
    if mode == "--default":
        print("Need maximum coverage? Re-run with --full:")
        print(f"  bash {cos_source}/scripts/cos-init.sh --full")

    return 0
```

## `scripts/hook-timing-wrapper.sh`

**Replace:**

```
# The env vars below are exactly the ones scripts/cos-root honours, in the same
# precedence order, so behaviour is unchanged where cos-root IS present.
cos_resolve_project_root() {
  local candidate
  candidate="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-}}}"
  if [ -n "$candidate" ] && [ -d "$candidate" ]; then
    (cd "$candidate" && pwd) && return 0
  fi
  # Prefer a real cos-root when one is a sibling (COS self-hosting layout).
  if [ -x "$SCRIPT_DIR/cos-root" ]; then
    candidate="$("$SCRIPT_DIR/cos-root" project 2>/dev/null || true)"
    if [ -n "$candidate" ] && [ -d "$candidate" ]; then
      printf '%s\n' "$candidate" && return 0
    fi
  fi
  # Walk up from this script looking for an installed .cognitive-os/ root.
```

**With:**

```
# The env vars below are exactly the ones scripts/cos-root honours, in the same
# precedence order, and the walk-up fallback reproduces its remaining branch —
# so this is a behaviour-preserving inline of `cos-root project`, not a
# weaker substitute. The dependency is REMOVED rather than made optional:
# leaving a `$SCRIPT_DIR/cos-root` reference in place would keep a
# can-never-ship sibling in the file for the next reader to trip over.
cos_resolve_project_root() {
  local candidate
  candidate="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-}}}"
  if [ -n "$candidate" ] && [ -d "$candidate" ]; then
    (cd "$candidate" && pwd) && return 0
  fi
  # Walk up from this script looking for an installed .cognitive-os/ root.
```

## `scripts/cos_init.py`

**Replace:**

```
    closure_seed_paths = list(projected_hook_paths)
    installed_hook_lib = Path(hooks_dest) / "_lib"
    if installed_hook_lib.is_dir():
        closure_seed_paths.extend(sorted(installed_hook_lib.glob("*.py")))
    installed_bin = project_dir / ".cognitive-os" / "bin"
    if installed_bin.is_dir():
        closure_seed_paths.extend(sorted(installed_bin.glob("*.py")))
```

**With:**

```
    closure_seed_paths = list(projected_hook_paths)
    installed_hook_lib = Path(hooks_dest) / "_lib"
    if installed_hook_lib.is_dir():
        # BOTH .py and .sh: the shell members of _lib/ (common.sh, timing.sh,
        # register-bg.sh, context_budget_lib.sh) embed `python3 -c` blocks that
        # import cos_lib modules just as the .py members do.
        closure_seed_paths.extend(sorted(installed_hook_lib.glob("*.py")))
        closure_seed_paths.extend(sorted(installed_hook_lib.glob("*.sh")))
    installed_bin = project_dir / ".cognitive-os" / "bin"
    if installed_bin.is_dir():
        closure_seed_paths.extend(sorted(installed_bin.glob("*.py")))
```

## `cos_lib/record_completion.py`

**Replace:**

```
from cos_lib.learning_pipeline import LearningPipeline
from cos_lib.metric_event import MetricEvent, append_event
```

**With:**

```
# NOTE: cos_lib.learning_pipeline is `SCOPE: os-only` and therefore can never
# be projected into a consumer install, while this module is `SCOPE: both`.
# Importing it at module level made the whole module unimportable in every
# consumer — which silently killed the agent circuit breaker, because
# hooks/_lib/dispatch_gate_check.py imports cos_lib.circuit_breaker and
# cos_lib.record_completion in the SAME try block. The ImportError aborted the
# block before CircuitBreaker.can_launch() ever ran, and `except Exception`
# turned a dead safety control into a string field.
# LearningPipeline is used in exactly one function, so the import is deferred
# to its use site. Consumers can now import classify_task_type; the
# os-only-dependent code path stays os-only.
from cos_lib.metric_event import MetricEvent, append_event
```

**Replace:**

```
    pipeline = LearningPipeline()
    result = pipeline.record_agent_completion(
```

**With:**

```
    # Deferred: os-only dependency, see the import-site note at the top.
    from cos_lib.learning_pipeline import LearningPipeline

    pipeline = LearningPipeline()
    result = pipeline.record_agent_completion(
```

## `scripts/hook-timing-wrapper.sh`

**Replace:**

```
# so this is a behaviour-preserving inline of `cos-root project`, not a
# weaker substitute. The dependency is REMOVED rather than made optional:
# leaving a `$SCRIPT_DIR/cos-root` reference in place would keep a
# can-never-ship sibling in the file for the next reader to trip over.
```

**With:**

```
# so this is a behaviour-preserving inline of `cos-root project`, not a
# weaker substitute. The dependency is REMOVED rather than made optional:
# leaving even a fallback reference to that sibling in place would keep a
# can-never-ship dependency in the file for the next reader to trip over.
```

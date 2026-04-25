"""Audit: every packages/*/hooks/ that sources _lib/ has a working _lib symlink.

Same bug class that crashed completion-gate.sh on 2026-04-24.
Without the symlink, hooks that call `source ./_lib/common.sh` (or similar)
fail at runtime with "No such file or directory", silently breaking enforcement.
"""
import pytest
from pathlib import Path

REPO = Path(__file__).parent.parent.parent


@pytest.mark.audit
def test_packages_hooks_lib_symlinks_resolve():
    """All packages/*/hooks/ that source _lib/ must have a working _lib symlink."""
    failures = []

    for pkg_hooks in sorted((REPO / "packages").glob("*/hooks")):
        # Does any hook in this package reference _lib/?
        sources_lib = False
        for hook_sh in pkg_hooks.glob("*.sh"):
            try:
                content = hook_sh.read_text(encoding="utf-8", errors="ignore")
                if "_lib/" in content and (
                    "source " in content or "\n. " in content or content.startswith(". ")
                ):
                    sources_lib = True
                    break
            except Exception:
                continue

        if not sources_lib:
            continue

        # Package uses _lib/ — verify the symlink exists and resolves.
        lib_path = pkg_hooks / "_lib"

        if not lib_path.exists():
            failures.append(
                (str(pkg_hooks.relative_to(REPO)), "missing _lib (symlink or dir)")
            )
            continue

        # Confirm it resolves to a real directory (not a dangling symlink).
        try:
            resolved = lib_path.resolve(strict=True)
            if not resolved.is_dir():
                failures.append(
                    (
                        str(pkg_hooks.relative_to(REPO)),
                        f"_lib resolves to non-dir: {resolved}",
                    )
                )
        except Exception as exc:
            failures.append(
                (str(pkg_hooks.relative_to(REPO)), f"_lib resolve failed: {exc}")
            )

    assert not failures, (
        "Packages with broken or missing _lib:\n"
        + "\n".join(f"  {path}: {reason}" for path, reason in failures)
    )

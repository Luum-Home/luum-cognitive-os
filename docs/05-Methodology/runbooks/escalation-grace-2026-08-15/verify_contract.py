"""Run contract test functions against a given tree without pytest.

The repo's conftest refuses interpreters whose resolved sys.prefix is outside
the tree, and the snapshot trees legitimately borrow the repo venv. Rather than
set PYTEST_ALLOW_NONVENV=1 (a suppression), we import the test module from the
tree under test -- so its REPO_ROOT/HOOK resolve to that tree -- and invoke each
test function with a fresh temp dir.

Usage: verify_contract.py <tree> <test_file_relpath> [<test_file_relpath> ...]
Exit 0 = all passed, 1 = at least one failed.
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
import traceback
from pathlib import Path


def load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    tree = Path(sys.argv[1]).resolve()
    failures = 0
    for rel in sys.argv[2:]:
        module = load(tree / rel)
        xfail = getattr(module, "PENDING", None)
        print(f"\n=== {rel}  (hook: {module.HOOK.relative_to(tree)}) ===")
        for name in sorted(n for n in dir(module) if n.startswith("test_")):
            func = getattr(module, name)
            marks = getattr(func, "pytestmark", [])
            expect_fail = any(getattr(m, "name", "") == "xfail" for m in marks)
            tmp = Path(tempfile.mkdtemp())
            try:
                func(tmp)
                outcome, detail = "PASS", ""
            except BaseException as exc:  # noqa: BLE001 - reporting harness
                outcome = "FAIL"
                detail = "".join(
                    traceback.format_exception_only(type(exc), exc)
                ).strip().splitlines()[-1][:140]
            finally:
                shutil.rmtree(tmp, ignore_errors=True)

            if expect_fail:
                label = "XFAIL(ok)" if outcome == "FAIL" else "XPASS(!!)"
                bad = outcome == "PASS"
            else:
                label = outcome
                bad = outcome == "FAIL"
            failures += bool(bad)
            print(f"  {label:10s} {name}" + (f"\n             -> {detail}" if detail and bad else ""))
    print(f"\nunexpected results: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

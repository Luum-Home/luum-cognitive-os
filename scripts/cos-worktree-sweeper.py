#!/usr/bin/env python3
# SCOPE: both
"""Human-friendly CLI wrapper for cos_worktree_sweeper.py."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_IMPL = Path(__file__).with_name("cos_worktree_sweeper.py")
_SPEC = importlib.util.spec_from_file_location("cos_worktree_sweeper", _IMPL)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"cannot load worktree sweeper implementation at {_IMPL}")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules.setdefault("cos_worktree_sweeper", _MODULE)
_SPEC.loader.exec_module(_MODULE)
main = _MODULE.main

if __name__ == "__main__":
    raise SystemExit(main())

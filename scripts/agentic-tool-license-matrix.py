#!/usr/bin/env python3
"""Compatibility CLI for the Agentic Mastery license gate.

The implementation lives in ``agentic_tool_license_matrix.py`` so unit tests can
import it with a valid Python module name. This hyphenated entrypoint preserves
the documented script path requested by maintainers.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_IMPL_PATH = Path(__file__).with_name("agentic_tool_license_matrix.py")
_SPEC = importlib.util.spec_from_file_location("agentic_tool_license_matrix", _IMPL_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"cannot load license gate implementation at {_IMPL_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules.setdefault("agentic_tool_license_matrix", _MODULE)
_SPEC.loader.exec_module(_MODULE)

main = _MODULE.main

if __name__ == "__main__":
    raise SystemExit(main())

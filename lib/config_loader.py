# SCOPE: both
"""Unified cognitive-os.yaml reader — luum-agent-os kernel.

Provides three access variants that match the three cost profiles found
across the codebase (see ADR-026 / ADR-026a, Option B):

Variant 1 — ``read_top_level_int(key, default)``
    Regex, line-by-line. No PyYAML import.  Safe on every call path including
    cold-start PreToolUse hooks where import cost must be near-zero.  Returns
    the FIRST line in the file whose key matches, regardless of YAML nesting
    depth — this matches the documented divergence in the characterisation
    tests (``test_cos_yaml_readers.py::TestReadMaxParallelAgents``, rows
    "first match wins even when top-level appears later").

Variant 2 — ``load_structured()``
    Full ``yaml.safe_load`` parse.  Use when callers already import PyYAML
    and need nested-path access (e.g. ``resources.compute.max_parallel_agents``
    vs a bare top-level value).

Variant 3 — ``find_config_path()``
    Candidate-path locator.  Returns the first readable path from the search
    order mandated by Pattern A (``lib.paths.project_root()``).  Legacy callers
    that maintain their own ``_find_config_path`` helpers can delegate here
    without changing their search semantics.

Search-path order (all three variants):
    1. ``${COGNITIVE_OS_PROJECT_DIR}/cognitive-os.yaml``    (if env var set)
    2. ``${CODEX_PROJECT_DIR}/cognitive-os.yaml``           (if first absent)
    3. ``${CLAUDE_PROJECT_DIR}/cognitive-os.yaml``          (if first absent)
    4. ``cognitive-os.yaml``                                (cwd-relative)
    5. ``.cognitive-os/cognitive-os.yaml``                  (cwd-relative)

    This matches ``dispatch_helper._find_config_path()`` exactly (after the
    R1 ``project_root()`` migration).  The ``find_config_path()`` function
    returns the *string* representation used by the characterized sites so
    that call-site return values remain identical (see
    ``TestFindConfigPath.test_cwd_yaml_wins_when_no_project_dir_env``).

Python 3.9+. Stdlib-only for variants 1 and 3; PyYAML required for variant 2.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

from lib.paths import runtime_project_root

__all__ = ["find_config_path", "read_top_level_int", "load_structured", "read_int_from_file"]

_COGNITIVE_OS_DIR = ".cognitive-os"
_CONFIG_FILENAME = "cognitive-os.yaml"


# ---------------------------------------------------------------------------
# Variant 3 — legacy-compat path locator
# ---------------------------------------------------------------------------


def find_config_path() -> Optional[str]:
    """Return the first readable ``cognitive-os.yaml`` found on the search path.

    Search order:
    1. ``${COGNITIVE_OS_PROJECT_DIR}/cognitive-os.yaml``
    2. ``${CODEX_PROJECT_DIR}/cognitive-os.yaml``
    3. ``${CLAUDE_PROJECT_DIR}/cognitive-os.yaml``
    4. ``cognitive-os.yaml`` (cwd-relative)
    5. ``.cognitive-os/cognitive-os.yaml`` (cwd-relative)

    Returns
    -------
    str | None
        The path as a string (absolute when env-var based, relative when
        cwd-based), exactly as the legacy ``_find_config_path`` helpers
        returned it.  ``None`` when no candidate exists on disk.
    """
    candidates: list[str] = [
        _CONFIG_FILENAME,
        os.path.join(_COGNITIVE_OS_DIR, _CONFIG_FILENAME),
    ]

    project_dir: Optional[Path] = runtime_project_root()
    if project_dir:
        candidates.insert(0, os.path.join(str(project_dir), _CONFIG_FILENAME))

    for path in candidates:
        if os.path.isfile(path):
            return path

    return None


# ---------------------------------------------------------------------------
# Variant 1 — hot-path regex reader
# ---------------------------------------------------------------------------


def read_int_from_file(key: str, path: str) -> Optional[int]:
    """Return the integer value for ``key`` from a single YAML file, or ``None``.

    Reads line-by-line (no PyYAML).  Returns ``None`` when the key is absent
    or the file cannot be opened, allowing callers to distinguish "key not
    found" from "key found with value == default".

    Parameters
    ----------
    key:
        The YAML key to search for.
    path:
        Absolute or relative path to the YAML file.

    Returns
    -------
    int | None
        Parsed integer if the key was found, ``None`` otherwise.
    """
    pattern = re.compile(r"^\s*" + re.escape(key) + r":\s*(\d+)")
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                m = pattern.match(line)
                if m:
                    return int(m.group(1))
    except OSError:
        pass
    return None


def read_top_level_int(key: str, default: int, config_path: Optional[str] = None) -> int:
    """Parse ``key: <integer>`` from cognitive-os.yaml without importing PyYAML.

    Reads the file line-by-line and returns the integer value from the FIRST
    line that matches ``^\\s*{key}:\\s*(\\d+)``.  YAML nesting is intentionally
    ignored — this preserves the documented "first-match wins" divergence that
    the regex-based sites rely on (see characterization tests).

    Parameters
    ----------
    key:
        The YAML key to search for (e.g. ``"max_parallel_agents"``).
    default:
        Value to return when the key is absent or any error occurs.
    config_path:
        Optional explicit path to the YAML file.  When omitted,
        ``find_config_path()`` is called to locate the file.

    Returns
    -------
    int
        Parsed integer, or ``default`` on any error / missing key.
    """
    path = config_path or find_config_path()
    if not path:
        return default

    result = read_int_from_file(key, path)
    return result if result is not None else default


# ---------------------------------------------------------------------------
# Variant 2 — full YAML parse
# ---------------------------------------------------------------------------


def load_structured(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load cognitive-os.yaml with ``yaml.safe_load`` and return the dict.

    Requires PyYAML (``import yaml``).  Callers that already import PyYAML
    should prefer this over multiple ``read_top_level_int`` calls when they
    need nested-key access (e.g. ``resources.compute.max_parallel_agents``).

    Parameters
    ----------
    config_path:
        Optional explicit path.  When omitted, ``find_config_path()`` is used.

    Returns
    -------
    dict
        Parsed YAML content, or ``{}`` when the file is absent, empty, or
        cannot be read (matches the ``or {}`` fallback used at site 3).

    Raises
    ------
    ImportError
        If PyYAML is not installed.
    yaml.YAMLError
        If the file exists but contains malformed YAML.  Callers that need
        silent degradation on parse errors should catch this themselves.
        ``OSError`` (unreadable file) is caught internally and returns ``{}``.
    """
    import yaml  # noqa: PLC0415  — intentional lazy import (cold-start safety)

    path = config_path or find_config_path()
    if not path:
        return {}

    try:
        with open(path, encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except OSError:
        return {}

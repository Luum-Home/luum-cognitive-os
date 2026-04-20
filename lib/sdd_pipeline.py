# SCOPE: os-only
"""SDD Pipeline — Fast Path for Capable Models.

Defines phase sequences for the Spec-Driven Development pipeline. Capable
models (e.g. Opus 4.6 with 1M context) can skip intermediate planning phases
(spec, design, tasks) and go straight from proposal to implementation, based
on Anthropic's finding that detailed planning is overhead for top-tier models.

Configuration lives in ``cognitive-os.yaml`` under ``sdd.fast_path``:

.. code-block:: yaml

    sdd:
      fast_path:
        enabled: true
        model_threshold: opus  # Models at or above this level use fast path

**Orchestrator integration**: The orchestrator reads this module to decide
which SDD phases to execute. When launching ``/sdd-ff`` or ``/sdd-continue``,
call ``SDDPipeline.get_phases(model, config)`` to obtain the phase list.
When advancing between phases, call ``SDDPipeline.next_phase(current, model, config)``.
The orchestrator still owns execution; this module only provides the logic.

Python 3.9+ compatible.  Only depends on :mod:`lib.model_catalog`.
Author: luum
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Tuple

from lib.paths import project_root

# ---------------------------------------------------------------------------
# Phase definitions
# ---------------------------------------------------------------------------

FULL_PHASES: Tuple[str, ...] = (
    "explore",
    "propose",
    "spec",
    "design",
    "tasks",
    "apply",
    "verify",
    "archive",
)

FAST_PHASES: Tuple[str, ...] = (
    "explore",
    "propose",
    "apply",
    "verify",
    "archive",
)

#: Phases that are skipped in the fast path.
_SKIPPED_PHASES = frozenset(FULL_PHASES) - frozenset(FAST_PHASES)

# ---------------------------------------------------------------------------
# Model capability ordering (cheapest → most capable)
# ---------------------------------------------------------------------------

# Reuse the Anthropic chain ordering from model_catalog.  We duplicate the
# ordered list here to avoid a hard import-time dependency on
# _ANTHROPIC_CHAIN (private constant).  If the catalog adds models, update
# this list too.
_MODEL_TIER: Tuple[str, ...] = (
    "openrouter/free",
    "claude-haiku-3.5",
    "claude-sonnet-4",
    "claude-opus-4-6",
)

#: Maps common short names / aliases to their canonical position in the tier
#: list.  We keep this light — only the names that are likely to appear in
#: ``cognitive-os.yaml`` under ``sdd.fast_path.model_threshold``.
_ALIAS_TO_TIER_ID: Dict[str, str] = {
    "free": "openrouter/free",
    "openrouter/free": "openrouter/free",
    "haiku": "claude-haiku-3.5",
    "claude-haiku-3.5": "claude-haiku-3.5",
    "claude-haiku": "claude-haiku-3.5",
    "sonnet": "claude-sonnet-4",
    "claude-sonnet-4": "claude-sonnet-4",
    "claude-sonnet": "claude-sonnet-4",
    "opus": "claude-opus-4-6",
    "claude-opus-4-6": "claude-opus-4-6",
    "claude-opus-4": "claude-opus-4-6",
    "claude-opus": "claude-opus-4-6",
}


def _tier_index(model: str) -> int:
    """Return the capability tier index for a model (0 = lowest).

    Falls back to :class:`lib.model_catalog.ModelCatalog` for unknown
    aliases.  Returns ``-1`` when the model is completely unrecognised (i.e.
    non-Anthropic models are treated as below the threshold).
    """
    canonical = _ALIAS_TO_TIER_ID.get(model.lower())
    if canonical is None:
        # Try the full catalog for alias resolution.
        try:
            from lib.model_catalog import ModelCatalog

            canonical = ModelCatalog.resolve(model)
        except (KeyError, ImportError):
            return -1
        canonical = _ALIAS_TO_TIER_ID.get(canonical.lower(), canonical)
    try:
        return _MODEL_TIER.index(canonical)
    except ValueError:
        return -1


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------


def _read_sdd_config(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return the ``sdd.fast_path`` section from a config dict.

    If *config* is ``None``, attempts to read ``cognitive-os.yaml`` from
    common locations (same search strategy as other lib modules).
    """
    if config is not None:
        return config.get("sdd", {}).get("fast_path", {})

    # Search common locations.
    paths_to_try: List[str] = []
    project_dir = project_root()
    if project_dir:
        paths_to_try.append(os.path.join(project_dir, "cognitive-os.yaml"))
        paths_to_try.append(
            os.path.join(project_dir, ".cognitive-os", "cognitive-os.yaml")
        )
    paths_to_try.append("cognitive-os.yaml")
    paths_to_try.append(os.path.join(".cognitive-os", "cognitive-os.yaml"))

    for path in paths_to_try:
        if os.path.isfile(path):
            try:
                section = _parse_fast_path_from_file(path)
                if section is not None:
                    return section
            except OSError:
                continue

    return {}


def _parse_fast_path_from_file(path: str) -> Optional[Dict[str, Any]]:
    """Lightweight parser that extracts ``sdd.fast_path`` values.

    We avoid a hard ``yaml`` dependency by using simple regex parsing,
    matching the pattern used in ``lib/rate_limiter.py``.  This handles
    the expected flat structure:

    .. code-block:: yaml

        sdd:
          fast_path:
            enabled: true
            model_threshold: opus
    """
    result: Dict[str, Any] = {}
    in_sdd = False
    in_fast_path = False

    with open(path, "r") as fh:
        for line in fh:
            stripped = line.rstrip()

            # Detect top-level ``sdd:``
            if re.match(r"^sdd\s*:", stripped):
                in_sdd = True
                in_fast_path = False
                continue

            # Once inside ``sdd:``, detect ``fast_path:``
            if in_sdd and re.match(r"^\s{2}fast_path\s*:", stripped):
                in_fast_path = True
                continue

            # Exit if we hit another top-level key
            if in_sdd and re.match(r"^\S", stripped):
                in_sdd = False
                in_fast_path = False
                continue

            # Exit fast_path if we hit a sibling key at the sdd level
            if in_fast_path and re.match(r"^\s{2}\S", stripped) and not re.match(
                r"^\s{4}", stripped
            ):
                in_fast_path = False
                continue

            if in_fast_path:
                m = re.match(r"^\s{4}(\w+)\s*:\s*(.+)", stripped)
                if m:
                    key, value = m.group(1), m.group(2).strip()
                    # Strip inline YAML comments (# ...)
                    comment_pos = value.find("  #")
                    if comment_pos >= 0:
                        value = value[:comment_pos].strip()
                    # Parse booleans
                    if value.lower() in ("true", "yes"):
                        result[key] = True
                    elif value.lower() in ("false", "no"):
                        result[key] = False
                    else:
                        result[key] = value

    return result if result else None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class SDDPipeline:
    """SDD phase sequencing with fast-path support.

    All methods are static/class-level.  No instances required.
    """

    FULL_PHASES = FULL_PHASES
    FAST_PHASES = FAST_PHASES

    @staticmethod
    def is_fast_path(model: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """Return ``True`` when *model* qualifies for the fast path.

        The fast path is active when:
        1. ``sdd.fast_path.enabled`` is ``True`` (or absent — default ``True``).
        2. The model's capability tier is >= the configured threshold
           (``sdd.fast_path.model_threshold``, default ``"opus"``).
        """
        fp = _read_sdd_config(config)

        # Default: enabled
        if not fp.get("enabled", True):
            return False

        threshold = str(fp.get("model_threshold", "opus"))
        model_tier = _tier_index(model)
        threshold_tier = _tier_index(threshold)

        # Unknown models (tier -1) never get the fast path.
        if model_tier < 0 or threshold_tier < 0:
            return False

        return model_tier >= threshold_tier

    @staticmethod
    def get_phases(
        model: str, config: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Return the ordered phase list for *model* given *config*."""
        if SDDPipeline.is_fast_path(model, config):
            return list(FAST_PHASES)
        return list(FULL_PHASES)

    @staticmethod
    def next_phase(
        current: str,
        model: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Return the phase after *current*, or ``None`` if *current* is last.

        Raises ``ValueError`` if *current* is not a valid phase in the
        applicable sequence.
        """
        phases = SDDPipeline.get_phases(model, config)
        try:
            idx = phases.index(current)
        except ValueError:
            raise ValueError(
                f"Phase {current!r} is not in the active sequence: {phases}"
            )
        if idx + 1 < len(phases):
            return phases[idx + 1]
        return None

    @staticmethod
    def skip_reason(phase: str, model: str) -> str:
        """Return a human-readable reason why *phase* is skipped for *model*.

        Returns an empty string when the phase is NOT skipped.
        """
        if phase not in _SKIPPED_PHASES:
            return ""
        return (
            f"Phase '{phase}' skipped: model '{model}' qualifies for the SDD "
            f"fast path (capable models can go from proposal directly to "
            f"implementation without intermediate spec/design/tasks phases)."
        )

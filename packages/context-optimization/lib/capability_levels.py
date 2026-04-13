# scope: both
"""Capability Levels — Auto-disable components based on model capability level.

Capability levels allow the system to automatically disable rules/hooks that are
unnecessary at higher model capability levels. A level 4 (autonomous) model doesn't
need clarification gates or assumption tracking — it handles those internally.

Levels:
    1 = basic      — all safety nets active
    2 = good       — all safety nets active
    3 = excellent  — context-management disabled (model manages its own context)
    4 = autonomous — multiple safety nets disabled (model is self-correcting)
    5 = autonomous+ — most safety nets disabled; session, metrics, security, error
                      capture remain active
"""

from pathlib import Path
from typing import Dict, List, Optional

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


# Default disabled components per capability level.
# Each level inherits the disabled set of all lower levels.
DEFAULT_AUTO_DISABLE: Dict[int, List[str]] = {
    3: ["context-management"],
    4: [
        "clarification-gate",
        "assumption-tracking",
        "confidence-gate",
        "model-routing",
        "blast-radius",
    ],
    5: [
        "completeness-check",
        "epic-task-detector",
        "scope-proportionality",
        "trust-score-validator",
        "claim-validator",
        "tool-loop-detector",
        "consequence-evaluator",
        "infra-intent-detector",
        "pre-cleanup-snapshot",
        "architecture-compliance",
        "auto-skill-generator",
    ],
}

VALID_LEVELS = (1, 2, 3, 4, 5)

DEFAULT_LEVEL = 3


def _parse_yaml(config_path: str) -> dict:
    """Parse a YAML config file, with fallback for missing pyyaml."""
    path = Path(config_path)
    if not path.exists():
        return {}

    text = path.read_text()

    if yaml is not None:
        return yaml.safe_load(text) or {}

    # Minimal fallback parser for the specific keys we need
    result: dict = {}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("level:"):
            val = stripped.split(":", 1)[1].strip().split("#")[0].strip()
            try:
                result.setdefault("model_capability", {})["level"] = int(val)
            except ValueError:
                pass
    return result


def get_capability_level(config_path: str = "cognitive-os.yaml") -> int:
    """Read the capability level from cognitive-os.yaml.

    Args:
        config_path: Path to the cognitive-os.yaml config file.

    Returns:
        The capability level (1-5). Defaults to DEFAULT_LEVEL if not configured
        or if the value is out of range.
    """
    config = _parse_yaml(config_path)

    model_cap = config.get("model_capability", {})
    if not isinstance(model_cap, dict):
        return DEFAULT_LEVEL

    level = model_cap.get("level", DEFAULT_LEVEL)

    try:
        level = int(level)
    except (TypeError, ValueError):
        return DEFAULT_LEVEL

    if level not in VALID_LEVELS:
        return DEFAULT_LEVEL

    return level


def get_auto_disable_map(config_path: str = "cognitive-os.yaml") -> Dict[int, List[str]]:
    """Read auto_disable map from config, falling back to defaults.

    Args:
        config_path: Path to the cognitive-os.yaml config file.

    Returns:
        Dictionary mapping level -> list of disabled component names.
    """
    config = _parse_yaml(config_path)

    model_cap = config.get("model_capability", {})
    if not isinstance(model_cap, dict):
        return dict(DEFAULT_AUTO_DISABLE)

    auto_disable = model_cap.get("auto_disable")
    if not isinstance(auto_disable, dict):
        return dict(DEFAULT_AUTO_DISABLE)

    # Parse from config — keys may be ints or strings
    result: Dict[int, List[str]] = {}
    for key, value in auto_disable.items():
        try:
            level_key = int(key)
        except (TypeError, ValueError):
            continue
        if isinstance(value, list):
            result[level_key] = [str(v) for v in value]

    return result if result else dict(DEFAULT_AUTO_DISABLE)


def get_disabled_components(
    level: int,
    config_path: str = "cognitive-os.yaml",
) -> List[str]:
    """Return which rules/hooks to skip at this capability level.

    Components disabled at lower levels are also disabled at higher levels
    (cumulative). For example, if level 3 disables "context-management",
    level 4 also has "context-management" disabled.

    Args:
        level: The capability level (1-5).
        config_path: Path to the cognitive-os.yaml config file.

    Returns:
        Sorted deduplicated list of component names that should be disabled.
    """
    if level < 1:
        level = 1
    if level > 5:
        level = 5

    auto_disable = get_auto_disable_map(config_path)

    disabled: set = set()
    for lvl in sorted(auto_disable.keys()):
        if lvl <= level:
            disabled.update(auto_disable[lvl])

    return sorted(disabled)


def should_component_run(
    component_name: str,
    level: Optional[int] = None,
    config_path: str = "cognitive-os.yaml",
) -> bool:
    """Check if a component (hook/rule) should be active at the given level.

    Args:
        component_name: Name of the hook or rule (e.g., "clarification-gate").
        level: Capability level. If None, reads from config.
        config_path: Path to the cognitive-os.yaml config file.

    Returns:
        True if the component should run, False if it should be skipped.
    """
    if level is None:
        level = get_capability_level(config_path)

    disabled = get_disabled_components(level, config_path)
    return component_name not in disabled


def format_capability_report(
    level: Optional[int] = None,
    config_path: str = "cognitive-os.yaml",
) -> str:
    """Generate a human-readable report of active/disabled components.

    Args:
        level: Capability level. If None, reads from config.
        config_path: Path to the cognitive-os.yaml config file.

    Returns:
        Formatted multi-line string showing capability level and component status.
    """
    if level is None:
        level = get_capability_level(config_path)

    level_names = {1: "basic", 2: "good", 3: "excellent", 4: "autonomous", 5: "autonomous+"}
    level_name = level_names.get(level, "unknown")

    disabled = get_disabled_components(level, config_path)

    lines = [
        f"Capability Level: {level} ({level_name})",
        "",
    ]

    if disabled:
        lines.append("Disabled components:")
        for comp in disabled:
            lines.append(f"  - {comp}")
    else:
        lines.append("All components active (no auto-disable at this level).")

    # Show what each level disables
    auto_disable = get_auto_disable_map(config_path)
    lines.append("")
    lines.append("Auto-disable schedule:")
    for lvl in sorted(auto_disable.keys()):
        components = auto_disable[lvl]
        if components:
            lines.append(f"  Level {lvl}: {', '.join(components)}")

    return "\n".join(lines)

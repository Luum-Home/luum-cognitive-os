from __future__ import annotations

from pathlib import Path
import json


def load_adapter(name: str) -> dict:
    path = Path(__file__).with_name(f"{name}.yaml")
    if not path.exists():
        raise FileNotFoundError(f"unknown primitive coverage adapter: {name}")
    return parse_simple_yaml(path.read_text())


def parse_simple_yaml(text: str) -> dict:
    """Parse the small adapter YAML subset without adding a runtime dependency."""
    result: dict = {"families": {}}
    current_family: str | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not raw.startswith(" ") and ":" in stripped:
            key, _, value = stripped.partition(":")
            if key == "adapter":
                result["adapter"] = value.strip()
            elif key == "extends":
                result["extends"] = value.strip()
            elif key == "families":
                result.setdefault("families", {})
            continue
        if raw.startswith("  ") and not raw.startswith("    ") and stripped.endswith(":"):
            current_family = stripped[:-1]
            result.setdefault("families", {}).setdefault(current_family, {})
            continue
        if raw.startswith("    ") and current_family and stripped.startswith("patterns:"):
            _, _, value = stripped.partition(":")
            result["families"][current_family]["patterns"] = json.loads(value.strip().replace("'", '"'))
    if "adapter" not in result:
        raise ValueError("adapter yaml missing adapter key")
    return result

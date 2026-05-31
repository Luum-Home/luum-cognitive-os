"""Forward script-local `import yaml` to the repository compatibility shim."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_root_yaml = Path(__file__).resolve().parents[1] / "yaml.py"
_spec = importlib.util.spec_from_file_location("_cos_yaml_compat", _root_yaml)
if _spec is None or _spec.loader is None:
    raise ImportError(f"cannot load {_root_yaml}")
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
globals().update({k: v for k, v in _module.__dict__.items() if not k.startswith("__")})

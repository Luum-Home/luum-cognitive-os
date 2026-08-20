# SCOPE: os-only
"""El gate sigue cazando a un escritor que ignora COS_METRICS_DIR.

Corre un hook SEMBRADO que hardcodea la ruta del operador y le pasa por encima
las funciones REALES de deteccion de `conftest.py` (capa 2). El directorio del
operador es falso: no se toca telemetria real. Imprime DETECTADO o NO_DETECTADO.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location("_cos_root_conftest", REPO / "conftest.py")
conftest = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(conftest)

hook = os.environ["COS_VERIFY_SEEDED_HOOK"]
proj = Path(os.environ["COS_VERIFY_SEEDED_PROJ"])
sandbox = Path(os.environ["COS_VERIFY_SANDBOX"])
sandbox.mkdir(parents=True, exist_ok=True)
operator = proj / ".cognitive-os" / "metrics"

before = conftest.fingerprint_metrics_dir(operator)
subprocess.run(
    ["bash", hook],
    env={
        **os.environ,
        "COGNITIVE_OS_PROJECT_DIR": str(proj),
        "COS_METRICS_DIR": str(sandbox),  # el sembrado la ignora a proposito
    },
    check=False,
    capture_output=True,
)
grew = conftest.diff_growth(before, conftest.fingerprint_metrics_dir(operator))

if any(name == "sembrado.jsonl" for name, _, _ in grew):
    print(f"DETECTADO: capa 2 reporta {grew}")
    sys.exit(0)
print(f"NO_DETECTADO: diff_growth={grew} (sandbox={sorted(p.name for p in sandbox.iterdir())})")
sys.exit(1)

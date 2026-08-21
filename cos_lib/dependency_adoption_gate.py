"""Dependency adoption gate for ADR-208.

This closes the loop between external-tool research skills (`/repo-scout`,
`/repo-forensics`, `/pattern-audit`) and actual dependency manifest changes.
The gate is deterministic: dependency manifest additions require a staged
adoption evidence artifact before commit.
"""
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "dependency-adoption-gate/v1"

DEPENDENCY_MANIFEST_NAMES = {
    "pyproject.toml",
    "requirements.txt",
    "requirements.in",
    "setup.py",
    "setup.cfg",
    "package.json",
    "bun.lock",
    "bun.lockb",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "go.mod",
    "go.sum",
    "Cargo.toml",
    "Cargo.lock",
    "Gemfile",
    "Gemfile.lock",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
}

DEPENDENCY_MANIFEST_PREFIXES = (
    "requirements/",
    "requirements-",
)

ADOPTION_EVIDENCE_PATHS = (
    "manifests/dependency-adoption-evidence.yaml",
    "manifests/imported-pattern-closures.yaml",
)

ADOPTION_EVIDENCE_PREFIXES = (
    "docs/06-Daily/reports/repo-scout-",
    "docs/06-Daily/reports/repo-forensics-",
    "docs/06-Daily/reports/tool-adoption-",
    "docs/06-Daily/reports/dependency-adoption-",
    "docs/04-Concepts/architecture/primitive-coverage-backend-benchmark",
    ".cognitive-os/research/tool-adoption/",
    ".cognitive-os/strategy/research/",
)

SAFE_ADDITION_RE = re.compile(
    r'^\+\s*(#|//|/\*|\*|$'
    r'|version\s*=|requires-python\s*=|name\s*=|description\s*=|license\s*=|author\s*='
    r'|go\s+\d+(?:\.\d+){1,2}$|toolchain\s+go\d+(?:\.\d+){1,2}$'
    r'|"(?:version|name|description|license|author|homepage|repository|main|module|type)"\s*:'
    r')',
    re.IGNORECASE,
)


@dataclass(frozen=True)
class GateResult:
    status: str
    dependency_files: list[str]
    evidence_files: list[str]
    added_dependency_lines: list[str]
    message: str

    @property
    def exit_code(self) -> int:
        return 0 if self.status == "pass" else 2

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "status": self.status,
            "dependency_files": self.dependency_files,
            "evidence_files": self.evidence_files,
            "added_dependency_lines": self.added_dependency_lines,
            "message": self.message,
            "required_actions": [
                "Run /repo-scout or /repo-forensics for newly adopted external tools.",
                "Record the result in docs/06-Daily/reports/repo-scout-* or manifests/dependency-adoption-evidence.yaml.",
                "For imported patterns, add/refresh manifests/imported-pattern-closures.yaml per ADR-208.",
            ],
        }


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _run_git(repo: Path, args: list[str]) -> str:
    result = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=False, timeout=60)
    if result.returncode != 0:
        return ""
    return result.stdout


def is_dependency_manifest(path: str) -> bool:
    name = Path(path).name
    if name in DEPENDENCY_MANIFEST_NAMES:
        return True
    return any(path.startswith(prefix) for prefix in DEPENDENCY_MANIFEST_PREFIXES)


def is_adoption_evidence(path: str) -> bool:
    if path in ADOPTION_EVIDENCE_PATHS:
        return True
    return any(path.startswith(prefix) for prefix in ADOPTION_EVIDENCE_PREFIXES)


def staged_files(repo: Path) -> list[str]:
    output = _run_git(repo, ["diff", "--cached", "--name-only", "--diff-filter=ACMRT"])
    return [line.strip() for line in output.splitlines() if line.strip()]


def added_dependency_lines(repo: Path, dependency_files: list[str]) -> list[str]:
    if not dependency_files:
        return []
    output = _run_git(repo, ["diff", "--cached", "--unified=0", "--", *dependency_files])
    additions: list[str] = []
    current_file = "<unknown>"
    lineno = 0
    for line in output.splitlines():
        if line.startswith("+++ b/"):
            current_file = line.removeprefix("+++ b/")
            continue
        m = _HUNK_RE.match(line)
        if m:
            lineno = int(m.group(1))
            continue
        if not line.startswith("+") or line.startswith("+++"):
            continue
        aqui = lineno
        lineno += 1
        if SAFE_ADDITION_RE.match(line):
            continue
        text = line[1:].strip()
        if not text:
            continue
        # UNA CLAVE DE CONFIGURACION NO ES UNA DEPENDENCIA.
        #
        # El gate leia TODA linea `+` de un manifiesto como dependencia agregada,
        # sin mirar en que seccion caia. Medido el 2026-08-21: bloqueo un commit
        # que solo tocaba `[tool.mutmut]`, acusando de dependencias nuevas a
        # `paths_to_mutate`, `tests_dir` y `also_copy` -- tres claves de
        # configuracion de una herramienta que YA estaba declarada hacia meses.
        #
        # Pedir evidencia de pre-adopcion por configurar algo ya adoptado no es
        # gobierno: es un peaje que entrena a saltear el gate, y el dia que
        # aparezca una dependencia de verdad va a estar desactivado.
        if _es_seccion_de_dependencias(repo, current_file, aqui) is False:
            continue
        additions.append(f"{current_file}: {text[:160]}")
    return additions


_HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")

#: Secciones de pyproject donde una linea SI declara una dependencia. Fuera de
#: estas, un `nombre = [...]` es configuracion de herramienta.
_SECCIONES_DE_DEPENDENCIAS = (
    "project.dependencies",
    "project.optional-dependencies",
    "dependency-groups",
    "tool.poetry.dependencies",
    "tool.poetry.dev-dependencies",
    "tool.poetry.group",
    "tool.uv.sources",
    "build-system",
)


def _es_seccion_de_dependencias(repo: Path, rel: str, lineno: int) -> bool | None:
    """True/False si se pudo determinar la seccion; None si no se pudo.

    `None` NO se colapsa en `False`: no poder leer el archivo tiene que dejar la
    linea bajo sospecha, no absolverla. Absolver por no haber podido mirar es
    fail-open, y es el defecto que este repo persiguio tres dias.

    Solo se razona sobre TOML. Para `package.json`, `go.mod` y demas se devuelve
    `None` y el comportamiento anterior se conserva intacto.
    """
    if not rel.endswith(".toml"):
        return None
    try:
        lineas = (repo / rel).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    if not (1 <= lineno <= len(lineas)):
        return None
    # Hay que rastrear DOS cosas, y la primera version solo miraba una:
    #
    #   [project]                      <- la seccion
    #   dependencies = [               <- la CLAVE, que es donde viven de verdad
    #       "pyyaml>=6.0",
    #   ]
    #
    # En pyproject las dependencias son un array bajo `[project]`, no una seccion
    # `[project.dependencies]`. Mirando solo el encabezado, una dependencia real
    # quedaba absuelta: el contrafactico de dos ramas lo cazo -- agregue un
    # paquete de verdad y el gate lo dejo pasar.
    seccion = ""
    clave_array = ""
    profundidad = 0
    for ln in lineas[:lineno]:
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        if profundidad == 0 and s.startswith("[") and s.endswith("]"):
            seccion = s.strip("[]").strip()
            clave_array = ""
            continue
        if profundidad == 0:
            m = re.match(r"^([A-Za-z0-9_.\-]+)\s*=\s*\[", s)
            if m:
                clave_array = m.group(1)
                profundidad = s.count("[") - s.count("]")
                if profundidad <= 0:
                    clave_array = ""
                    profundidad = 0
                continue
        else:
            profundidad += s.count("[") - s.count("]")
            if profundidad <= 0:
                profundidad = 0
                clave_array = ""
    if not seccion:
        return None
    if any(seccion == d or seccion.startswith(d + ".") for d in _SECCIONES_DE_DEPENDENCIAS):
        return True
    if seccion == "project" and clave_array in ("dependencies", "optional-dependencies"):
        return True
    return False


def evaluate_staged(repo: Path | None = None) -> GateResult:
    root = (repo or repo_root()).resolve()
    files = staged_files(root)
    dep_files = sorted(path for path in files if is_dependency_manifest(path))
    evidence_files = sorted(path for path in files if is_adoption_evidence(path))
    additions = added_dependency_lines(root, dep_files)

    if not dep_files or not additions:
        return GateResult(
            status="pass",
            dependency_files=dep_files,
            evidence_files=evidence_files,
            added_dependency_lines=additions,
            message="No staged dependency additions detected.",
        )
    if evidence_files:
        return GateResult(
            status="pass",
            dependency_files=dep_files,
            evidence_files=evidence_files,
            added_dependency_lines=additions,
            message="Dependency additions have staged adoption evidence.",
        )
    return GateResult(
        status="block",
        dependency_files=dep_files,
        evidence_files=evidence_files,
        added_dependency_lines=additions[:20],
        message=(
            "Dependency manifest additions require pre-adoption evidence. "
            "The skills exist, but ADR-208 requires the commit path to consume them."
        ),
    )


def inventory_files(root: Path) -> list[str]:
    tracked = _run_git(root, ["ls-files"])
    if tracked.strip():
        return [line.strip() for line in tracked.splitlines() if line.strip()]

    skipped_dirs = {
        ".git",
        ".venv",
        "node_modules",
        ".next",
        "dist",
        "build",
        "__pycache__",
    }
    files: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in skipped_dirs for part in rel.parts):
            continue
        files.append(str(rel))
    return sorted(files)


def current_dependency_inventory(repo: Path | None = None) -> dict[str, Any]:
    root = (repo or repo_root()).resolve()
    files = inventory_files(root)
    manifests = sorted(path for path in files if is_dependency_manifest(path))
    evidence = sorted(path for path in files if is_adoption_evidence(path))
    return {
        "schema_version": "dependency-adoption-inventory/v1",
        "project_dir": str(root),
        "dependency_manifest_count": len(manifests),
        "dependency_manifests": manifests,
        "adoption_evidence_count": len(evidence),
        "adoption_evidence": evidence,
        "status": "ok" if evidence else "warn",
        "message": "Dependency adoption evidence exists." if evidence else "No dependency adoption evidence artifacts found.",
    }


def format_human(result: GateResult) -> str:
    lines = [f"dependency-adoption-gate: {result.status}", result.message]
    if result.dependency_files:
        lines.append("Dependency manifests:")
        lines.extend(f"- {path}" for path in result.dependency_files)
    if result.added_dependency_lines:
        lines.append("Detected additions:")
        lines.extend(f"- {line}" for line in result.added_dependency_lines[:10])
    if result.evidence_files:
        lines.append("Evidence files:")
        lines.extend(f"- {path}" for path in result.evidence_files)
    return "\n".join(lines)


def dumps_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)

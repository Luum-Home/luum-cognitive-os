"""Reverse Engineer module.

Deep source code analysis of dependencies to understand internal APIs,
config schemas, CLI commands, environment variables, and undocumented behavior.

When docs are incomplete, reading the actual source code gives you the EXACT
answer in minutes instead of hours of trial-and-error.

Python 3.9+ compatible.
"""

import os
import re
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Quote-matching helpers for regex patterns.
# Python 3.14 enforces bracket matching in raw strings, so ['"] inside r"..."
# causes SyntaxError. We use these non-raw string constants instead.
_Q = "['\"]"          # Matches ' or "
_NQ = "[^'\"]"        # Matches anything except ' or "
_NQP = "[^'\".)]"     # Matches non-quote, non-dot, non-paren


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SchemaField:
    """A single field in a config schema."""
    name: str
    type: str
    required: bool = False
    default: Optional[str] = None
    valid_values: Optional[List[str]] = None
    description: Optional[str] = None


@dataclass
class ConfigSchema:
    """A discovered config schema."""
    file: str
    line: int
    schema_type: str  # zod, typescript_interface, json_schema, go_struct, python_dataclass, python_pydantic
    name: str
    fields: List[SchemaField] = field(default_factory=list)


@dataclass
class EnvVar:
    """An environment variable reference."""
    name: str
    file: str
    line: int
    default_value: Optional[str] = None
    required: bool = True


@dataclass
class CLICommand:
    """A CLI command or subcommand."""
    command: str
    description: str
    flags: List[Dict[str, str]] = field(default_factory=list)
    file: str = ""
    line: int = 0


@dataclass
class APIRoute:
    """An HTTP API route."""
    method: str
    path: str
    handler: str
    file: str
    line: int


@dataclass
class DockerSetup:
    """Docker configuration analysis."""
    entrypoint: Optional[str] = None
    cmd: Optional[str] = None
    ports: List[str] = field(default_factory=list)
    volumes: List[str] = field(default_factory=list)
    env_vars: List[str] = field(default_factory=list)
    healthcheck: Optional[str] = None
    base_image: Optional[str] = None
    compose_services: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class AuthFlow:
    """Authentication/session handling analysis."""
    type: str  # jwt, session, oauth, basic, api_key, unknown
    session_cookie_name: Optional[str] = None
    endpoints: List[Dict[str, str]] = field(default_factory=list)
    middleware: List[str] = field(default_factory=list)
    providers: List[str] = field(default_factory=list)


@dataclass
class AnalysisReport:
    """Complete reverse engineering analysis."""
    repo_path: str
    config_schemas: List[ConfigSchema] = field(default_factory=list)
    env_vars: List[EnvVar] = field(default_factory=list)
    cli_commands: List[CLICommand] = field(default_factory=list)
    api_routes: List[APIRoute] = field(default_factory=list)
    docker_setup: Optional[DockerSetup] = None
    auth_flow: Optional[AuthFlow] = None
    errors: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# File scanning utilities
# ---------------------------------------------------------------------------

# Extensions to scan for each analysis type
_SOURCE_EXTENSIONS = {
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    ".go",
    ".py",
    ".java", ".kt",
    ".rs",
    ".rb",
}

_CONFIG_EXTENSIONS = {
    ".json", ".yaml", ".yml", ".toml", ".ini", ".env",
}

_ALL_EXTENSIONS = _SOURCE_EXTENSIONS | _CONFIG_EXTENSIONS


def _find_files(
    repo_path: str,
    extensions: Optional[Set[str]] = None,
    max_files: int = 5000,
) -> List[Path]:
    """Find source files in a repo, respecting common ignore patterns."""
    if extensions is None:
        extensions = _ALL_EXTENSIONS

    ignore_dirs = {
        "node_modules", ".git", "__pycache__", "vendor", "dist",
        "build", ".next", "coverage", ".tox", ".venv", "venv",
        "target", "bin", "obj", ".cache", ".turbo",
    }

    results: List[Path] = []
    root = Path(repo_path)

    for dirpath, dirnames, filenames in os.walk(root):
        # Prune ignored directories
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs]

        for fname in filenames:
            if len(results) >= max_files:
                return results
            ext = os.path.splitext(fname)[1].lower()
            if ext in extensions:
                results.append(Path(dirpath) / fname)

    return results


def _safe_read(filepath: Path, max_bytes: int = 500_000) -> str:
    """Read a file safely, handling encoding issues and size limits."""
    try:
        size = filepath.stat().st_size
        if size > max_bytes:
            return ""
        return filepath.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeDecodeError):
        return ""


def _relative_path(filepath: Path, repo_path: str) -> str:
    """Return the file path relative to the repo root."""
    try:
        return str(filepath.relative_to(repo_path))
    except ValueError:
        return str(filepath)


# ---------------------------------------------------------------------------
# Config schema analysis
# ---------------------------------------------------------------------------

# Zod schema patterns
_ZOD_SCHEMA_RE = re.compile(
    r"(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*z\.object\(\{",
    re.MULTILINE,
)
_ZOD_FIELD_RE = re.compile(
    r"(\w+)\s*:\s*z\.(string|number|boolean|enum|array|object|optional|literal|union|nativeEnum)"
    r"\(([^)]*)\)",
)

# TypeScript interface patterns
_TS_INTERFACE_RE = re.compile(
    r"(?:export\s+)?interface\s+(\w+)\s*\{",
    re.MULTILINE,
)
_TS_FIELD_RE = re.compile(
    r"(\w+)(\?)?:\s*([^;]+);",
)

# Go struct patterns
_GO_STRUCT_RE = re.compile(
    r"type\s+(\w+)\s+struct\s*\{",
    re.MULTILINE,
)
_GO_FIELD_RE = re.compile(
    r"\s+(\w+)\s+(\S+)\s+`[^`]*(?:json:\"([^\"]+)\"|yaml:\"([^\"]+)\"|env:\"([^\"]+)\")",
)

# Python dataclass / Pydantic patterns
_PY_DATACLASS_RE = re.compile(
    r"@dataclass[^\n]*\nclass\s+(\w+)",
    re.MULTILINE,
)
_PY_PYDANTIC_RE = re.compile(
    r"class\s+(\w+)\((?:BaseModel|BaseSettings)\)",
    re.MULTILINE,
)
_PY_FIELD_RE = re.compile(
    r"(\w+)\s*:\s*([^=\n]+?)(?:\s*=\s*(.+))?\s*$",
    re.MULTILINE,
)

# JSON Schema patterns
_JSON_SCHEMA_MARKER = '"$schema"'


def _analyze_zod_schema(content: str, filepath: Path, repo_path: str) -> List[ConfigSchema]:
    """Extract Zod schema definitions."""
    schemas: List[ConfigSchema] = []
    for match in _ZOD_SCHEMA_RE.finditer(content):
        name = match.group(1)
        line = content[:match.start()].count("\n") + 1

        # Extract the block after z.object({
        start = match.end()
        brace_depth = 1
        end = start
        while end < len(content) and brace_depth > 0:
            if content[end] == "{":
                brace_depth += 1
            elif content[end] == "}":
                brace_depth -= 1
            end += 1

        block = content[start:end]
        fields: List[SchemaField] = []
        for fm in _ZOD_FIELD_RE.finditer(block):
            fname = fm.group(1)
            ftype = fm.group(2)
            args = fm.group(3).strip() if fm.group(3) else ""
            required = "optional" not in ftype
            valid_values = None
            default = None

            if ftype == "enum":
                # Extract enum values from [...]
                enum_match = re.search(r"\[([^\]]+)\]", args)
                if enum_match:
                    valid_values = [
                        v.strip().strip("'\"")
                        for v in enum_match.group(1).split(",")
                    ]
            if ftype == "literal":
                valid_values = [args.strip("'\"")]

            fields.append(SchemaField(
                name=fname,
                type=ftype,
                required=required,
                default=default,
                valid_values=valid_values,
            ))

        schemas.append(ConfigSchema(
            file=_relative_path(filepath, repo_path),
            line=line,
            schema_type="zod",
            name=name,
            fields=fields,
        ))

    return schemas


def _analyze_ts_interfaces(content: str, filepath: Path, repo_path: str) -> List[ConfigSchema]:
    """Extract TypeScript interface definitions (config-related ones)."""
    schemas: List[ConfigSchema] = []

    # Only look at interfaces with Config, Options, Settings, Schema, Props in the name
    config_keywords = {"config", "options", "settings", "schema", "props", "params", "spec"}

    for match in _TS_INTERFACE_RE.finditer(content):
        name = match.group(1)
        if not any(kw in name.lower() for kw in config_keywords):
            continue

        line = content[:match.start()].count("\n") + 1

        # Extract block
        start = match.end()
        brace_depth = 1
        end = start
        while end < len(content) and brace_depth > 0:
            if content[end] == "{":
                brace_depth += 1
            elif content[end] == "}":
                brace_depth -= 1
            end += 1

        block = content[start:end - 1]
        fields: List[SchemaField] = []
        for fm in _TS_FIELD_RE.finditer(block):
            fname = fm.group(1)
            optional = fm.group(2) == "?"
            ftype = fm.group(3).strip()
            fields.append(SchemaField(
                name=fname,
                type=ftype,
                required=not optional,
            ))

        if fields:
            schemas.append(ConfigSchema(
                file=_relative_path(filepath, repo_path),
                line=line,
                schema_type="typescript_interface",
                name=name,
                fields=fields,
            ))

    return schemas


def _analyze_go_structs(content: str, filepath: Path, repo_path: str) -> List[ConfigSchema]:
    """Extract Go struct definitions with json/yaml/env tags."""
    schemas: List[ConfigSchema] = []

    config_keywords = {"config", "options", "settings", "spec", "params"}

    for match in _GO_STRUCT_RE.finditer(content):
        name = match.group(1)
        if not any(kw in name.lower() for kw in config_keywords):
            continue

        line = content[:match.start()].count("\n") + 1

        start = match.end()
        brace_depth = 1
        end = start
        while end < len(content) and brace_depth > 0:
            if content[end] == "{":
                brace_depth += 1
            elif content[end] == "}":
                brace_depth -= 1
            end += 1

        block = content[start:end - 1]
        fields: List[SchemaField] = []
        for fm in _GO_FIELD_RE.finditer(block):
            go_name = fm.group(1)
            go_type = fm.group(2)
            json_name = fm.group(3)
            yaml_name = fm.group(4)
            env_name = fm.group(5)

            field_name = json_name or yaml_name or env_name or go_name
            # Remove omitempty and similar suffixes
            if "," in field_name:
                field_name = field_name.split(",")[0]

            required = ",omitempty" not in (fm.group(0) or "")
            fields.append(SchemaField(
                name=field_name,
                type=go_type,
                required=required,
            ))

        if fields:
            schemas.append(ConfigSchema(
                file=_relative_path(filepath, repo_path),
                line=line,
                schema_type="go_struct",
                name=name,
                fields=fields,
            ))

    return schemas


def _analyze_python_models(content: str, filepath: Path, repo_path: str) -> List[ConfigSchema]:
    """Extract Python dataclass and Pydantic model definitions."""
    schemas: List[ConfigSchema] = []

    for pattern, schema_type in [
        (_PY_DATACLASS_RE, "python_dataclass"),
        (_PY_PYDANTIC_RE, "python_pydantic"),
    ]:
        for match in pattern.finditer(content):
            name = match.group(1)
            line = content[:match.start()].count("\n") + 1

            # Find the class body (indented block after the class line)
            class_line_end = content.index("\n", match.end()) + 1
            body_lines: List[str] = []
            for l in content[class_line_end:].split("\n"):
                if l and not l[0].isspace() and not l.startswith("#"):
                    break
                body_lines.append(l)

            body = "\n".join(body_lines)
            fields: List[SchemaField] = []
            for fm in _PY_FIELD_RE.finditer(body):
                fname = fm.group(1)
                if fname.startswith("_") or fname in ("class", "def", "return"):
                    continue
                ftype = fm.group(2).strip()
                default = fm.group(3).strip() if fm.group(3) else None
                required = default is None and "Optional" not in ftype
                fields.append(SchemaField(
                    name=fname,
                    type=ftype,
                    required=required,
                    default=default,
                ))

            if fields:
                schemas.append(ConfigSchema(
                    file=_relative_path(filepath, repo_path),
                    line=line,
                    schema_type=schema_type,
                    name=name,
                    fields=fields,
                ))

    return schemas


def _analyze_json_schema(content: str, filepath: Path, repo_path: str) -> List[ConfigSchema]:
    """Extract JSON Schema definitions from .json files."""
    if _JSON_SCHEMA_MARKER not in content:
        return []

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return []

    if not isinstance(data, dict) or "$schema" not in data:
        return []

    properties = data.get("properties", {})
    required_fields = set(data.get("required", []))

    fields: List[SchemaField] = []
    for fname, fdef in properties.items():
        if not isinstance(fdef, dict):
            continue
        ftype = fdef.get("type", "unknown")
        default = fdef.get("default")
        enum = fdef.get("enum")
        desc = fdef.get("description")

        fields.append(SchemaField(
            name=fname,
            type=str(ftype),
            required=fname in required_fields,
            default=str(default) if default is not None else None,
            valid_values=enum,
            description=desc,
        ))

    if fields:
        return [ConfigSchema(
            file=_relative_path(filepath, repo_path),
            line=1,
            schema_type="json_schema",
            name=data.get("title", filepath.stem),
            fields=fields,
        )]

    return []


# ---------------------------------------------------------------------------
# Environment variable analysis
# ---------------------------------------------------------------------------

# Language-specific env var access patterns
_ENV_PATTERNS = [
    # JavaScript / TypeScript
    re.compile(r"process\.env\.(\w+)", re.MULTILINE),
    re.compile(r"process\.env\[(?:'|")(\w+)(?:'|")\]", re.MULTILINE),
    # Go
    re.compile(r"os\.Getenv\((?:'|")(\w+)(?:'|")\)", re.MULTILINE),
    re.compile(r"os\.LookupEnv\((?:'|")(\w+)(?:'|")\)", re.MULTILINE),
    # Python
    re.compile(r"os\.environ(?:\.get)?\(?\[?(?:'|")(\w+)(?:'|")\]?\)?", re.MULTILINE),
    re.compile(r"os\.getenv\(['\"](\w+)['\"](?:,\s*['\"]((?:[^'"])*)['\"])?", re.MULTILINE),
    # Rust
    re.compile(r"env::var\((?:'|")(\w+)(?:'|")\)", re.MULTILINE),
    # Java / Kotlin
    re.compile(r"System\.getenv\((?:'|")(\w+)(?:'|")\)", re.MULTILINE),
    # Ruby
    re.compile(r"ENV\[(?:'|")(\w+)(?:'|")\]", re.MULTILINE),
    # Generic .env file patterns
    re.compile(r"^(\w+)=(.*)$", re.MULTILINE),
]

# Default value patterns (language-specific)
_DEFAULT_PATTERNS = [
    # process.env.X || "default"
    re.compile(r"process\.env\.(\w+)\s*\|\|\s*(?:'|")((?:[^'"])+)(?:'|")"),
    # os.Getenv("X") with default via or-pattern
    re.compile(r"os\.Getenv\((?:'|")(\w+)(?:'|")\).*(?:==\s*\"\".*?(?:'|")((?:[^'"])+)(?:'|"))"),
    # Python os.getenv("X", "default")
    re.compile(r"os\.getenv\((?:'|")(\w+)(?:'|"),\s*(?:'|")([^\'"]*)(?:'|")\)"),
    # Python os.environ.get("X", "default")
    re.compile(r"os\.environ\.get\((?:'|")(\w+)(?:'|"),\s*(?:'|")([^\'"]*)(?:'|")\)"),
]


def _analyze_env_vars_in_file(
    content: str, filepath: Path, repo_path: str,
) -> List[EnvVar]:
    """Find all environment variable references in a single file."""
    results: List[EnvVar] = []
    seen: Set[Tuple[str, str]] = set()

    is_env_file = filepath.name.startswith(".env")

    # Build default map
    defaults: Dict[str, str] = {}
    for pattern in _DEFAULT_PATTERNS:
        for m in pattern.finditer(content):
            defaults[m.group(1)] = m.group(2)

    for pattern in _ENV_PATTERNS:
        for m in pattern.finditer(content):
            name = m.group(1)
            rel = _relative_path(filepath, repo_path)
            key = (name, rel)
            if key in seen:
                continue
            seen.add(key)

            # Skip generic .env pattern for non-.env files
            if is_env_file and "=" in m.group(0):
                default = m.group(2) if m.lastindex and m.lastindex >= 2 else None
            else:
                default = defaults.get(name)

            line = content[:m.start()].count("\n") + 1
            results.append(EnvVar(
                name=name,
                file=rel,
                line=line,
                default_value=default,
                required=default is None,
            ))

    return results


# ---------------------------------------------------------------------------
# CLI command analysis
# ---------------------------------------------------------------------------

# Cobra (Go)
_COBRA_CMD_RE = re.compile(
    r"&cobra\.Command\s*\{[^}]*Use:\s*[\"\']([^\"\']+)[\"\']"
    r"[^}]*(?:Short:\s*[\"\']([^\"\']+)[\"\'])?",
    re.DOTALL,
)

# Commander.js
_COMMANDER_RE = re.compile(
    r"\.command\((?:'|")([^\'\"]+)(?:'|")\)"
    r"(?:\s*\.description\((?:'|")([^\'\"]+)(?:'|")\))?",
    re.DOTALL,
)

# Yargs
_YARGS_CMD_RE = re.compile(
    r"\.command\((?:'|")([^\'\"]+)(?:'|"),?\s*(?:'|")([^\'\"]*)(?:'|")\s*",
)

# Argparse (Python)
_ARGPARSE_PARSER_RE = re.compile(
    r"add_parser\((?:'|")([^\'\"]+)(?:'|")(?:.*?help=(?:'|")([^\'\"]+)(?:'|"))?\)",
    re.DOTALL,
)
_ARGPARSE_ARG_RE = re.compile(
    r"add_argument\((?:'|")(-{1,2}[^\'\"]+)(?:'|")(?:.*?help=(?:'|")([^\'\"]+)(?:'|"))?\)",
    re.DOTALL,
)

# Click (Python)
_CLICK_CMD_RE = re.compile(
    r"@(?:click\.command|cli\.command|app\.command)\((?:name=)?(?:'|")?([^\'\"\)]+)",
)


def _analyze_cli_in_file(
    content: str, filepath: Path, repo_path: str,
) -> List[CLICommand]:
    """Find CLI commands in a single file."""
    results: List[CLICommand] = []
    rel = _relative_path(filepath, repo_path)

    # Cobra
    for m in _COBRA_CMD_RE.finditer(content):
        results.append(CLICommand(
            command=m.group(1),
            description=m.group(2) or "",
            file=rel,
            line=content[:m.start()].count("\n") + 1,
        ))

    # Commander.js
    for m in _COMMANDER_RE.finditer(content):
        results.append(CLICommand(
            command=m.group(1),
            description=m.group(2) or "",
            file=rel,
            line=content[:m.start()].count("\n") + 1,
        ))

    # Yargs
    for m in _YARGS_CMD_RE.finditer(content):
        results.append(CLICommand(
            command=m.group(1),
            description=m.group(2) or "",
            file=rel,
            line=content[:m.start()].count("\n") + 1,
        ))

    # Argparse subcommands
    for m in _ARGPARSE_PARSER_RE.finditer(content):
        results.append(CLICommand(
            command=m.group(1),
            description=m.group(2) or "",
            file=rel,
            line=content[:m.start()].count("\n") + 1,
        ))

    # Click
    for m in _CLICK_CMD_RE.finditer(content):
        results.append(CLICommand(
            command=m.group(1).strip("'\""),
            description="",
            file=rel,
            line=content[:m.start()].count("\n") + 1,
        ))

    return results


# ---------------------------------------------------------------------------
# API route analysis
# ---------------------------------------------------------------------------

# Express.js / Fastify
_EXPRESS_ROUTE_RE = re.compile(
    r"(?:app|router|server|fastify)\.(get|post|put|patch|delete|all|options|head)\("
    r"(?:'|")([^\'\"]+)(?:'|")",
    re.IGNORECASE,
)

# Go (net/http, gin, echo, chi, gorilla)
_GO_ROUTE_RE = re.compile(
    r"\.(?:GET|POST|PUT|PATCH|DELETE|Handle|HandleFunc|Group)\("
    r"[\"\']([^\"\']+)[\"\']",
    re.IGNORECASE,
)

# Go gin-style
_GIN_ROUTE_RE = re.compile(
    r"\.(?:GET|POST|PUT|PATCH|DELETE)\([\"\']([^\"\']+)[\"\'],\s*(\w+)",
)

# Flask / FastAPI
_FLASK_ROUTE_RE = re.compile(
    r"@(?:app|blueprint|router|api)\.(?:route|get|post|put|patch|delete)\("
    r"(?:'|")([^\'\"]+)(?:'|")"
    r"(?:.*?methods=\[([^\]]+)\])?",
    re.DOTALL,
)

# Spring Boot (Java/Kotlin)
_SPRING_ROUTE_RE = re.compile(
    r"@(?:Get|Post|Put|Patch|Delete|Request)Mapping\("
    r"(?:value\s*=\s*)?[\"\']([^\"\']+)[\"\']",
)


def _analyze_routes_in_file(
    content: str, filepath: Path, repo_path: str,
) -> List[APIRoute]:
    """Find HTTP API routes in a single file."""
    results: List[APIRoute] = []
    rel = _relative_path(filepath, repo_path)

    # Express / Fastify
    for m in _EXPRESS_ROUTE_RE.finditer(content):
        results.append(APIRoute(
            method=m.group(1).upper(),
            path=m.group(2),
            handler="",
            file=rel,
            line=content[:m.start()].count("\n") + 1,
        ))

    # Go generic
    for m in _GO_ROUTE_RE.finditer(content):
        method_raw = m.group(0).split("(")[0].split(".")[-1]
        method = method_raw.upper()
        if method in ("HANDLE", "HANDLEFUNC", "GROUP"):
            method = "ANY"
        results.append(APIRoute(
            method=method,
            path=m.group(1),
            handler="",
            file=rel,
            line=content[:m.start()].count("\n") + 1,
        ))

    # Go gin-style with handler
    for m in _GIN_ROUTE_RE.finditer(content):
        method_raw = m.group(0).split("(")[0].split(".")[-1]
        results.append(APIRoute(
            method=method_raw.upper(),
            path=m.group(1),
            handler=m.group(2),
            file=rel,
            line=content[:m.start()].count("\n") + 1,
        ))

    # Flask / FastAPI
    for m in _FLASK_ROUTE_RE.finditer(content):
        path = m.group(1)
        methods_str = m.group(2)
        if methods_str:
            methods = [mt.strip().strip("'\"").upper() for mt in methods_str.split(",")]
        else:
            # Infer from decorator name
            decorator_text = content[max(0, m.start() - 50):m.start() + 50]
            if ".get(" in decorator_text:
                methods = ["GET"]
            elif ".post(" in decorator_text:
                methods = ["POST"]
            elif ".put(" in decorator_text:
                methods = ["PUT"]
            elif ".delete(" in decorator_text:
                methods = ["DELETE"]
            elif ".patch(" in decorator_text:
                methods = ["PATCH"]
            else:
                methods = ["ANY"]

        for method in methods:
            results.append(APIRoute(
                method=method,
                path=path,
                handler="",
                file=rel,
                line=content[:m.start()].count("\n") + 1,
            ))

    # Spring Boot
    for m in _SPRING_ROUTE_RE.finditer(content):
        decorator_name = m.group(0).split("(")[0]
        method = "ANY"
        for prefix in ("Get", "Post", "Put", "Patch", "Delete"):
            if prefix in decorator_name:
                method = prefix.upper()
                break
        results.append(APIRoute(
            method=method,
            path=m.group(1),
            handler="",
            file=rel,
            line=content[:m.start()].count("\n") + 1,
        ))

    return results


# ---------------------------------------------------------------------------
# Docker analysis
# ---------------------------------------------------------------------------

_DOCKERFILE_FROM_RE = re.compile(r"^FROM\s+(\S+)", re.MULTILINE | re.IGNORECASE)
_DOCKERFILE_EXPOSE_RE = re.compile(r"^EXPOSE\s+(.+)$", re.MULTILINE | re.IGNORECASE)
_DOCKERFILE_ENV_RE = re.compile(r"^ENV\s+(\w+)(?:=|\s+)(.*)$", re.MULTILINE | re.IGNORECASE)
_DOCKERFILE_ENTRYPOINT_RE = re.compile(r"^ENTRYPOINT\s+(.+)$", re.MULTILINE | re.IGNORECASE)
_DOCKERFILE_CMD_RE = re.compile(r"^CMD\s+(.+)$", re.MULTILINE | re.IGNORECASE)
_DOCKERFILE_VOLUME_RE = re.compile(r"^VOLUME\s+(.+)$", re.MULTILINE | re.IGNORECASE)
_DOCKERFILE_HEALTHCHECK_RE = re.compile(r"^HEALTHCHECK\s+(.+)$", re.MULTILINE | re.IGNORECASE)


def _analyze_dockerfile(content: str) -> DockerSetup:
    """Analyze a Dockerfile."""
    setup = DockerSetup()

    from_match = _DOCKERFILE_FROM_RE.search(content)
    if from_match:
        setup.base_image = from_match.group(1)

    for m in _DOCKERFILE_EXPOSE_RE.finditer(content):
        setup.ports.extend(m.group(1).split())

    for m in _DOCKERFILE_ENV_RE.finditer(content):
        setup.env_vars.append(f"{m.group(1)}={m.group(2).strip()}")

    ep_match = _DOCKERFILE_ENTRYPOINT_RE.search(content)
    if ep_match:
        setup.entrypoint = ep_match.group(1).strip()

    cmd_match = _DOCKERFILE_CMD_RE.search(content)
    if cmd_match:
        setup.cmd = cmd_match.group(1).strip()

    for m in _DOCKERFILE_VOLUME_RE.finditer(content):
        setup.volumes.append(m.group(1).strip())

    hc_match = _DOCKERFILE_HEALTHCHECK_RE.search(content)
    if hc_match:
        setup.healthcheck = hc_match.group(1).strip()

    return setup


def _analyze_compose_file(content: str) -> List[Dict[str, Any]]:
    """Analyze a docker-compose YAML file. Returns service dicts."""
    try:
        # Avoid importing yaml at module level
        import yaml
        data = yaml.safe_load(content)
    except Exception:
        return []

    if not isinstance(data, dict):
        return []

    services = data.get("services", {})
    result: List[Dict[str, Any]] = []

    for name, svc in services.items():
        if not isinstance(svc, dict):
            continue
        result.append({
            "name": name,
            "image": svc.get("image", ""),
            "ports": svc.get("ports", []),
            "environment": svc.get("environment", []),
            "volumes": svc.get("volumes", []),
            "healthcheck": svc.get("healthcheck", {}),
            "depends_on": svc.get("depends_on", []),
            "command": svc.get("command", ""),
            "entrypoint": svc.get("entrypoint", ""),
        })

    return result


# ---------------------------------------------------------------------------
# Auth flow analysis
# ---------------------------------------------------------------------------

_AUTH_PATTERNS = {
    "jwt": [
        re.compile(r"jwt|jsonwebtoken|jose|JWTAuth|jwt_required|JwtStrategy", re.IGNORECASE),
    ],
    "session": [
        re.compile(r"express-session|session\.cookie|SessionMiddleware|session_middleware", re.IGNORECASE),
    ],
    "oauth": [
        re.compile(r"oauth|passport\.authenticate|OAuthStrategy|oauth2|openid", re.IGNORECASE),
    ],
    "api_key": [
        re.compile(r"api[_-]?key|x-api-key|ApiKeyAuth|api_key_header", re.IGNORECASE),
    ],
    "basic": [
        re.compile(r"basic[_-]?auth|BasicStrategy|HTTPBasicAuth|basicAuth", re.IGNORECASE),
    ],
}

_SESSION_COOKIE_RE = re.compile(
    r"(?:cookie|session)[_.]?(?:name|key)\s*[:=]\s*(?:'|")([^\'\"]+)(?:'|")",
    re.IGNORECASE,
)

_AUTH_ENDPOINT_RE = re.compile(
    r"(?:'|")(/(?:auth|login|logout|signup|register|token|session|oauth|callback)[^\'\"]*)(?:'|")",
    re.IGNORECASE,
)

_AUTH_MIDDLEWARE_RE = re.compile(
    r"(?:middleware|guard|interceptor|before_request|before_action)\s*[:=(\[]\s*(?:'|")?(\w*(?:auth|guard|protect|verify|token|jwt)\w*)(?:'|")?",
    re.IGNORECASE,
)


def _analyze_auth_in_file(
    content: str, filepath: Path, repo_path: str,
) -> Tuple[Optional[str], Optional[str], List[Dict[str, str]], List[str]]:
    """Extract auth signals from a single file.

    Returns (auth_type, cookie_name, endpoints, middleware_names).
    """
    auth_type = None
    for atype, patterns in _AUTH_PATTERNS.items():
        for p in patterns:
            if p.search(content):
                auth_type = atype
                break
        if auth_type:
            break

    cookie_match = _SESSION_COOKIE_RE.search(content)
    cookie_name = cookie_match.group(1) if cookie_match else None

    endpoints: List[Dict[str, str]] = []
    for m in _AUTH_ENDPOINT_RE.finditer(content):
        endpoints.append({
            "path": m.group(1),
            "file": _relative_path(filepath, repo_path),
        })

    middleware: List[str] = []
    for m in _AUTH_MIDDLEWARE_RE.finditer(content):
        middleware.append(m.group(1))

    return auth_type, cookie_name, endpoints, middleware


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class ReverseEngineer:
    """Deep source code analysis of dependencies.

    Reads actual source code to understand config schemas, env vars,
    CLI commands, API routes, Docker setup, and auth flows.
    """

    def __init__(self, max_files: int = 5000):
        self.max_files = max_files

    def analyze_config_schema(self, repo_path: str) -> List[ConfigSchema]:
        """Find config schemas in source code.

        Looks for: Zod schemas, TypeScript interfaces, JSON Schema files,
        Python dataclasses/Pydantic, Go structs with json tags.
        """
        schemas: List[ConfigSchema] = []
        files = _find_files(repo_path, _SOURCE_EXTENSIONS | {".json"}, self.max_files)

        for fp in files:
            content = _safe_read(fp)
            if not content:
                continue

            ext = fp.suffix.lower()
            if ext in (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"):
                schemas.extend(_analyze_zod_schema(content, fp, repo_path))
                schemas.extend(_analyze_ts_interfaces(content, fp, repo_path))
            elif ext == ".go":
                schemas.extend(_analyze_go_structs(content, fp, repo_path))
            elif ext == ".py":
                schemas.extend(_analyze_python_models(content, fp, repo_path))
            elif ext == ".json":
                schemas.extend(_analyze_json_schema(content, fp, repo_path))

        return schemas

    def analyze_env_vars(self, repo_path: str) -> List[EnvVar]:
        """Find all environment variables used.

        Scans for: process.env.X, os.Getenv("X"), os.environ["X"], etc.
        Also reads .env* files for declared variables.
        """
        env_vars: List[EnvVar] = []
        seen_names: Set[str] = set()

        files = _find_files(repo_path, _SOURCE_EXTENSIONS | {".env"}, self.max_files)

        # Also include .env* files in root
        root = Path(repo_path)
        for f in root.iterdir():
            if f.is_file() and f.name.startswith(".env"):
                files.append(f)

        for fp in files:
            content = _safe_read(fp)
            if not content:
                continue
            file_vars = _analyze_env_vars_in_file(content, fp, repo_path)
            for ev in file_vars:
                if ev.name not in seen_names:
                    env_vars.append(ev)
                    seen_names.add(ev.name)

        # Sort by name
        env_vars.sort(key=lambda e: e.name)
        return env_vars

    def analyze_cli_commands(self, repo_path: str) -> List[CLICommand]:
        """Find CLI commands and subcommands.

        Detects: Cobra (Go), Commander.js, Yargs, Argparse (Python), Click.
        """
        commands: List[CLICommand] = []
        files = _find_files(repo_path, _SOURCE_EXTENSIONS, self.max_files)

        for fp in files:
            content = _safe_read(fp)
            if not content:
                continue
            commands.extend(_analyze_cli_in_file(content, fp, repo_path))

        return commands

    def analyze_api_routes(self, repo_path: str) -> List[APIRoute]:
        """Find HTTP API routes.

        Detects: Express/Fastify, Go (gin/echo/chi/net-http), Flask/FastAPI, Spring Boot.
        """
        routes: List[APIRoute] = []
        files = _find_files(repo_path, _SOURCE_EXTENSIONS, self.max_files)

        for fp in files:
            content = _safe_read(fp)
            if not content:
                continue
            routes.extend(_analyze_routes_in_file(content, fp, repo_path))

        # Sort by path
        routes.sort(key=lambda r: (r.path, r.method))
        return routes

    def analyze_docker_setup(self, repo_path: str) -> DockerSetup:
        """Analyze Docker configuration.

        Reads Dockerfile, docker-compose.yml, and .dockerignore.
        """
        root = Path(repo_path)
        setup = DockerSetup()

        # Find Dockerfiles
        for name in ("Dockerfile", "Dockerfile.prod", "Dockerfile.dev"):
            df = root / name
            if df.is_file():
                content = _safe_read(df)
                if content:
                    parsed = _analyze_dockerfile(content)
                    # Merge into main setup
                    setup.base_image = setup.base_image or parsed.base_image
                    setup.entrypoint = setup.entrypoint or parsed.entrypoint
                    setup.cmd = setup.cmd or parsed.cmd
                    setup.healthcheck = setup.healthcheck or parsed.healthcheck
                    setup.ports.extend(parsed.ports)
                    setup.volumes.extend(parsed.volumes)
                    setup.env_vars.extend(parsed.env_vars)

        # Find docker-compose files
        for name in ("docker-compose.yml", "docker-compose.yaml",
                      "compose.yml", "compose.yaml",
                      "docker-compose.dev.yml", "docker-compose.prod.yml"):
            dc = root / name
            if dc.is_file():
                content = _safe_read(dc)
                if content:
                    services = _analyze_compose_file(content)
                    setup.compose_services.extend(services)

        return setup

    def analyze_auth_flow(self, repo_path: str) -> AuthFlow:
        """Find authentication/session handling.

        Detects: JWT, session-based, OAuth, API key, basic auth.
        """
        auth_types: Dict[str, int] = {}
        cookie_name: Optional[str] = None
        all_endpoints: List[Dict[str, str]] = []
        all_middleware: List[str] = []
        all_providers: List[str] = []

        files = _find_files(repo_path, _SOURCE_EXTENSIONS, self.max_files)

        for fp in files:
            content = _safe_read(fp)
            if not content:
                continue

            atype, cname, endpoints, middleware = _analyze_auth_in_file(
                content, fp, repo_path,
            )
            if atype:
                auth_types[atype] = auth_types.get(atype, 0) + 1
            if cname:
                cookie_name = cname
            all_endpoints.extend(endpoints)
            all_middleware.extend(middleware)

        # Pick dominant auth type
        dominant_type = "unknown"
        if auth_types:
            dominant_type = max(auth_types, key=auth_types.get)  # type: ignore[arg-type]

        # Deduplicate
        seen_endpoints: Set[str] = set()
        unique_endpoints: List[Dict[str, str]] = []
        for ep in all_endpoints:
            if ep["path"] not in seen_endpoints:
                unique_endpoints.append(ep)
                seen_endpoints.add(ep["path"])

        unique_middleware = list(dict.fromkeys(all_middleware))

        return AuthFlow(
            type=dominant_type,
            session_cookie_name=cookie_name,
            endpoints=unique_endpoints,
            middleware=unique_middleware,
            providers=all_providers,
        )

    def full_analysis(self, repo_path: str) -> AnalysisReport:
        """Run all analyses and return a complete report."""
        report = AnalysisReport(repo_path=repo_path)

        try:
            report.config_schemas = self.analyze_config_schema(repo_path)
        except Exception as e:
            report.errors.append(f"Config schema analysis failed: {e}")

        try:
            report.env_vars = self.analyze_env_vars(repo_path)
        except Exception as e:
            report.errors.append(f"Env var analysis failed: {e}")

        try:
            report.cli_commands = self.analyze_cli_commands(repo_path)
        except Exception as e:
            report.errors.append(f"CLI command analysis failed: {e}")

        try:
            report.api_routes = self.analyze_api_routes(repo_path)
        except Exception as e:
            report.errors.append(f"API route analysis failed: {e}")

        try:
            report.docker_setup = self.analyze_docker_setup(repo_path)
        except Exception as e:
            report.errors.append(f"Docker analysis failed: {e}")

        try:
            report.auth_flow = self.analyze_auth_flow(repo_path)
        except Exception as e:
            report.errors.append(f"Auth flow analysis failed: {e}")

        return report

    def format_integration_guide(self, report: AnalysisReport) -> str:
        """Generate a structured integration guide from the analysis."""
        lines: List[str] = []
        lines.append("# Reverse Engineering Report")
        lines.append("")
        lines.append(f"**Repository**: `{report.repo_path}`")
        lines.append("")

        # Config schemas
        if report.config_schemas:
            lines.append("## Config Schemas")
            lines.append("")
            for schema in report.config_schemas:
                lines.append(f"### {schema.name} ({schema.schema_type})")
                lines.append(f"**File**: `{schema.file}` (line {schema.line})")
                lines.append("")
                if schema.fields:
                    lines.append("| Field | Type | Required | Default | Valid Values |")
                    lines.append("|-------|------|----------|---------|--------------|")
                    for f in schema.fields:
                        valid = ", ".join(f.valid_values) if f.valid_values else "-"
                        lines.append(
                            f"| `{f.name}` | {f.type} | {'Yes' if f.required else 'No'} "
                            f"| {f.default or '-'} | {valid} |"
                        )
                    lines.append("")

        # Environment variables
        if report.env_vars:
            lines.append("## Environment Variables")
            lines.append("")
            lines.append("| Variable | File | Required | Default |")
            lines.append("|----------|------|----------|---------|")
            for ev in report.env_vars:
                lines.append(
                    f"| `{ev.name}` | `{ev.file}:{ev.line}` "
                    f"| {'Yes' if ev.required else 'No'} "
                    f"| {ev.default_value or '-'} |"
                )
            lines.append("")

        # CLI commands
        if report.cli_commands:
            lines.append("## CLI Commands")
            lines.append("")
            lines.append("| Command | Description | File |")
            lines.append("|---------|-------------|------|")
            for cmd in report.cli_commands:
                lines.append(f"| `{cmd.command}` | {cmd.description} | `{cmd.file}` |")
            lines.append("")

        # API routes
        if report.api_routes:
            lines.append("## API Routes")
            lines.append("")
            lines.append("| Method | Path | Handler | File |")
            lines.append("|--------|------|---------|------|")
            for route in report.api_routes:
                lines.append(
                    f"| {route.method} | `{route.path}` "
                    f"| {route.handler or '-'} | `{route.file}:{route.line}` |"
                )
            lines.append("")

        # Docker setup
        if report.docker_setup:
            ds = report.docker_setup
            lines.append("## Docker Setup")
            lines.append("")
            if ds.base_image:
                lines.append(f"**Base image**: `{ds.base_image}`")
            if ds.entrypoint:
                lines.append(f"**Entrypoint**: `{ds.entrypoint}`")
            if ds.cmd:
                lines.append(f"**CMD**: `{ds.cmd}`")
            if ds.ports:
                lines.append(f"**Ports**: {', '.join(ds.ports)}")
            if ds.healthcheck:
                lines.append(f"**Healthcheck**: `{ds.healthcheck}`")
            if ds.env_vars:
                lines.append("")
                lines.append("**Docker ENV**:")
                for ev in ds.env_vars:
                    lines.append(f"- `{ev}`")
            if ds.compose_services:
                lines.append("")
                lines.append("### Compose Services")
                lines.append("")
                for svc in ds.compose_services:
                    lines.append(f"- **{svc['name']}**: {svc.get('image', 'build context')}")
                    if svc.get("ports"):
                        lines.append(f"  - Ports: {svc['ports']}")
                    if svc.get("environment"):
                        env_list = svc["environment"]
                        if isinstance(env_list, list):
                            lines.append(f"  - Env: {len(env_list)} variables")
                        elif isinstance(env_list, dict):
                            lines.append(f"  - Env: {len(env_list)} variables")
            lines.append("")

        # Auth flow
        if report.auth_flow and report.auth_flow.type != "unknown":
            af = report.auth_flow
            lines.append("## Authentication")
            lines.append("")
            lines.append(f"**Type**: {af.type}")
            if af.session_cookie_name:
                lines.append(f"**Cookie**: `{af.session_cookie_name}`")
            if af.middleware:
                lines.append(f"**Middleware**: {', '.join(af.middleware)}")
            if af.endpoints:
                lines.append("")
                lines.append("**Auth endpoints**:")
                for ep in af.endpoints:
                    lines.append(f"- `{ep['path']}` ({ep['file']})")
            lines.append("")

        # Errors
        if report.errors:
            lines.append("## Analysis Errors")
            lines.append("")
            for err in report.errors:
                lines.append(f"- {err}")
            lines.append("")

        return "\n".join(lines)

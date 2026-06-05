# SCOPE: both
"""Shared duplicate-scanning primitives for COS audits.

This module owns dependency-free scanner mechanics. Callers decide how to map
raw scanner pairs into their domain-specific finding schema, recommendations,
baselines, and report formats.
"""
from __future__ import annotations

import ast
import hashlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from lib.project_paths import relpath
from lib.script_helpers import shingles as token_shingles

WORD_RE = re.compile(r"[A-Za-z0-9_./:-]+")
PY_FUNC_RE = re.compile(r"^\s*(?:async\s+def|def)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
SHELL_FUNCTION_RE = re.compile(r"(?m)^\s*(?:function\s+([A-Za-z_][A-Za-z0-9_-]*)\s*(?:\(\))?|([A-Za-z_][A-Za-z0-9_-]*)\s*\(\))\s*\{\s*$")
JS_FUNC_RE = re.compile(r"\b(function\s+[A-Za-z_$][\w$]*\s*\(|[A-Za-z_$][\w$]*\s*=\s*\([^)]*\)\s*=>|[A-Za-z_$][\w$]*\s*\([^)]*\)\s*\{)")


@dataclass(frozen=True)
class LexicalPair:
    left: str
    right: str
    similarity: float
    exact: bool


@dataclass(frozen=True)
class FunctionRepeat:
    left: str
    right: str
    digest: str
    similarity: float = 1.0


def stable_id(kind: str, left: str, right: str, extra: str = "") -> str:
    digest = hashlib.sha1(f"{kind}\0{left}\0{right}\0{extra}".encode("utf-8")).hexdigest()[:12]
    return f"{kind}:{digest}"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def normalize_line(line: str) -> str:
    stripped = line.strip()
    if not stripped or stripped.startswith(("#", "//", "/*", "*")) or stripped in {"{", "}", "};"}:
        return ""
    stripped = re.sub(r'"(?:\\.|[^"])*"', '"STR"', stripped)
    stripped = re.sub(r"'(?:\\.|[^'])*'", "'STR'", stripped)
    stripped = re.sub(r"\b\d+(?:\.\d+)?\b", "0", stripped)
    stripped = re.sub(r"\b[a-f0-9]{8,}\b", "HASH", stripped, flags=re.I)
    return re.sub(r"\s+", " ", stripped).lower()


def normalize_text(text: str, *, skip_fenced_blocks: bool = False) -> str:
    lines: list[str] = []
    in_fence = False
    for line in text.splitlines():
        stripped = line.strip()
        if skip_fenced_blocks and stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if skip_fenced_blocks and in_fence:
            continue
        normalized = normalize_line(line)
        if normalized:
            lines.append(normalized)
    return "\n".join(lines)


def normalized_tokens(text: str, *, skip_fenced_blocks: bool = False) -> list[str]:
    return WORD_RE.findall(normalize_text(text, skip_fenced_blocks=skip_fenced_blocks))


def lexical_pairs(
    root: Path,
    files: list[Path],
    *,
    min_tokens: int,
    shingle_size: int,
    threshold: float,
    skip_fenced_blocks: bool = False,
    ignore_markdown_primitives: bool = False,
) -> list[LexicalPair]:
    records: list[tuple[str, str, int, set[str]]] = []
    for path in files:
        relative = relpath(root, path)
        if ignore_markdown_primitives and path.suffix == ".md" and relative.startswith(("skills/", "rules/")):
            continue
        text = read_text(path)
        tokens = normalized_tokens(text, skip_fenced_blocks=skip_fenced_blocks)
        if len(tokens) < min_tokens:
            continue
        records.append((relative, normalize_text(text, skip_fenced_blocks=skip_fenced_blocks), len(tokens), token_shingles(tokens, shingle_size)))
    pairs: list[LexicalPair] = []
    for index, (left_path, left_normalized, left_count, left_shingles) in enumerate(records):
        for right_path, right_normalized, right_count, right_shingles in records[index + 1:]:
            if min(left_count, right_count) / max(left_count, right_count) < 0.55:
                continue
            union = len(left_shingles | right_shingles)
            similarity = round(len(left_shingles & right_shingles) / union, 4) if union else 0.0
            exact = left_normalized == right_normalized
            if exact or similarity >= threshold:
                pairs.append(LexicalPair(left_path, right_path, 1.0 if exact else similarity, exact))
    return pairs


def python_ast_function_repeats(root: Path, files: list[Path], *, min_dump_chars: int = 180, skip_trivial_main: bool = False) -> list[FunctionRepeat]:
    seen: dict[str, str] = {}
    repeats: list[FunctionRepeat] = []
    for path in files:
        if path.suffix != ".py":
            continue
        try:
            tree = ast.parse(read_text(path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if skip_trivial_main and is_trivial_python_main_dispatch(node):
                continue
            body_dump = ast.dump(ast.Module(body=node.body, type_ignores=[]), include_attributes=False)
            if len(body_dump) < min_dump_chars:
                continue
            digest = hashlib.sha1(body_dump.encode("utf-8")).hexdigest()
            current = f"{relpath(root, path)}::{node.name}"
            if digest in seen and seen[digest].split("::", 1)[0] != current.split("::", 1)[0]:
                repeats.append(FunctionRepeat(seen[digest], current, digest))
            else:
                seen[digest] = current
    return repeats


def is_trivial_python_main_dispatch(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    if node.name != "main":
        return False
    body = list(node.body)
    if len(body) == 2 and isinstance(body[0], ast.Assign):
        targets = body[0].targets
        value = body[0].value
        assigns_args = (
            len(targets) == 1
            and isinstance(targets[0], ast.Name)
            and targets[0].id == "args"
            and isinstance(value, ast.Call)
            and isinstance(value.func, ast.Attribute)
            and value.func.attr == "parse_args"
        )
        if not assigns_args:
            return False
        statement = body[1]
    elif len(body) == 1:
        statement = body[0]
    else:
        return False
    if not isinstance(statement, ast.Return):
        return False
    value = statement.value
    if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "int" and value.args:
        value = value.args[0]
    if not isinstance(value, ast.Call):
        return False
    func = value.func
    return isinstance(func, ast.Attribute) and func.attr == "func" and isinstance(func.value, ast.Name) and func.value.id == "args"


def shell_function_repeats(root: Path, files: list[Path], *, min_tokens: int = 20) -> list[FunctionRepeat]:
    seen: dict[str, str] = {}
    repeats: list[FunctionRepeat] = []
    for path in files:
        if path.suffix not in {".sh", ".bash", ".zsh"} and not path.name.endswith(".sh"):
            continue
        for label, body in shell_function_blocks(path, root, min_tokens):
            digest = hashlib.sha1(body.encode("utf-8")).hexdigest()
            if digest in seen and seen[digest].split("::", 1)[0] != label.split("::", 1)[0]:
                repeats.append(FunctionRepeat(seen[digest], label, digest))
            else:
                seen[digest] = label
    return repeats


def shell_function_blocks(path: Path, root: Path, min_tokens: int) -> list[tuple[str, str]]:
    lines = read_text(path).splitlines()
    blocks: list[tuple[str, str]] = []
    index = 0
    while index < len(lines):
        match = SHELL_FUNCTION_RE.match(lines[index])
        if not match:
            index += 1
            continue
        name = match.group(1) or match.group(2) or "function"
        start = index
        depth = lines[index].count("{") - lines[index].count("}")
        index += 1
        while index < len(lines) and depth > 0:
            depth += lines[index].count("{") - lines[index].count("}")
            index += 1
        body = normalize_text("\n".join(lines[start + 1:index]))
        if len(WORD_RE.findall(body)) >= min_tokens:
            blocks.append((f"{relpath(root, path)}::{name}", body))
    return blocks


def generic_function_repeats(root: Path, files: list[Path], *, min_tokens: int) -> list[FunctionRepeat]:
    seen: dict[str, str] = {}
    repeats: list[FunctionRepeat] = []
    for path in files:
        for label, body in generic_function_blocks(path, root, min_tokens):
            normalized = re.sub(r"\b[A-Za-z_][A-Za-z0-9_]*\b", "ID", body)
            digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()
            if digest in seen and seen[digest].split(":", 1)[0] != label.split(":", 1)[0]:
                repeats.append(FunctionRepeat(seen[digest], label, digest))
            else:
                seen[digest] = label
    return repeats


def generic_function_blocks(path: Path, root: Path, min_tokens: int) -> list[tuple[str, str]]:
    text = read_text(path)
    relative = relpath(root, path)
    blocks: list[tuple[str, str]] = []
    lines = text.splitlines()
    if path.suffix == ".py":
        for index, line in enumerate(lines):
            match = PY_FUNC_RE.match(line)
            if not match:
                continue
            indent = len(line) - len(line.lstrip())
            end = index + 1
            for scan_index in range(index + 1, len(lines)):
                if lines[scan_index].strip() and len(lines[scan_index]) - len(lines[scan_index].lstrip()) <= indent:
                    break
                end = scan_index + 1
            blocks.append((f"{relative}:{index+1}:{match.group(1)}", normalize_text("\n".join(lines[index:end]))))
    elif path.suffix in {".sh", ".bash", ".zsh"} or path.name.endswith(".sh"):
        for label, body in shell_function_blocks(path, root, min_tokens):
            blocks.append((label.replace("::", ":", 1), body))
    elif path.suffix in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}:
        for match in JS_FUNC_RE.finditer(text):
            start = text[:match.start()].count("\n") + 1
            brace_at = text.find("{", match.start())
            if brace_at < 0:
                continue
            depth = 0
            end = brace_at
            for pos in range(brace_at, min(len(text), brace_at + 12000)):
                if text[pos] == "{":
                    depth += 1
                elif text[pos] == "}":
                    depth -= 1
                    if depth == 0:
                        end = pos + 1
                        break
            blocks.append((f"{relative}:{start}:js-function", normalize_text(text[brace_at:end])))
    return [(label, body) for label, body in blocks if len(WORD_RE.findall(body)) >= min_tokens]


def collect_text_files(
    root: Path,
    include: Iterable[str],
    *,
    text_suffixes: set[str],
    exclude_parts: set[str],
    special_names: set[str],
    tracked_only: bool = False,
    exclude_globs: Iterable[str] = (),
) -> list[Path]:
    tracked: set[str] | None = None
    if tracked_only:
        try:
            proc = subprocess.run(["git", "ls-files"], cwd=root, text=True, capture_output=True, timeout=10, check=False)
            if proc.returncode == 0:
                tracked = {line.strip() for line in proc.stdout.splitlines() if line.strip()}
        except Exception:
            tracked = None
    exclude_patterns = tuple(exclude_globs)
    files: list[Path] = []
    for item in include:
        base = (root / item).resolve() if not Path(item).is_absolute() else Path(item)
        candidates = [base] if base.is_file() else sorted(base.rglob("*")) if base.exists() else []
        for path in candidates:
            if not path.is_file() or path.is_symlink():
                continue
            relative = relpath(root, path)
            if tracked is not None and relative not in tracked:
                continue
            if any(part in exclude_parts for part in path.parts):
                continue
            if exclude_patterns and any(path.match(pattern) or relative.startswith(pattern.rstrip("/")) for pattern in exclude_patterns):
                continue
            if path.suffix.lower() in text_suffixes or path.name in special_names:
                files.append(path)
    by_real: dict[Path, Path] = {}
    for path in files:
        try:
            by_real.setdefault(path.resolve(strict=True), path)
        except OSError:
            by_real.setdefault(path.resolve(), path)
    return sorted(by_real.values(), key=lambda path: relpath(root, path))

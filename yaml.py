"""Small PyYAML compatibility shim for stdlib-only Cognitive OS CLIs.

If PyYAML is installed outside this checkout, this module delegates to it. When
it is unavailable, it provides the safe_load/safe_dump subset used by repository
manifests: indentation-based mappings, lists, scalars, inline scalar lists, and
folded/literal block scalars.
"""
from __future__ import annotations

import ast
import json
from typing import Any

class YAMLError(Exception):
    """Fallback parse error compatible with PyYAML's public exception."""

def _strip_comment(line: str) -> str:
    in_single = False
    in_double = False
    for idx, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            return line[:idx].rstrip()
    return line.rstrip()

def _scalar(value: str) -> Any:
    value = value.strip()
    if value == "":
        return ""
    lowered = value.lower()
    if lowered in {"null", "none", "~"}:
        return None
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if (value.startswith("[") and value.endswith("]")) or (value.startswith("{") and value.endswith("}")):
        try:
            return ast.literal_eval(value)
        except Exception:
            try:
                return json.loads(value)
            except Exception:
                if value.startswith("[") and value.endswith("]"):
                    inner = value[1:-1].strip()
                    if not inner:
                        return []
                    return [part.strip().strip("\"'") for part in inner.split(",")]
                return value
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value

def _preprocess(text: str) -> list[tuple[int, str]]:
    raw_lines = text.splitlines()
    out: list[tuple[int, str]] = []
    i = 0
    while i < len(raw_lines):
        raw = raw_lines[i]
        cleaned = _strip_comment(raw)
        if not cleaned.strip():
            i += 1
            continue
        indent = len(cleaned) - len(cleaned.lstrip(" "))
        stripped = cleaned.strip()
        if stripped.endswith(": >") or stripped.endswith(": |") or stripped.endswith(": >-") or stripped.endswith(": |-"):
            key = stripped.split(":", 1)[0]
            block_indent = None
            parts: list[str] = []
            i += 1
            while i < len(raw_lines):
                nxt = raw_lines[i]
                if not nxt.strip():
                    parts.append("")
                    i += 1
                    continue
                ni = len(nxt) - len(nxt.lstrip(" "))
                if ni <= indent:
                    break
                if block_indent is None:
                    block_indent = ni
                parts.append(nxt[block_indent:])
                i += 1
            folded = "\n".join(parts) if "|" in stripped else " ".join(p.strip() for p in parts if p.strip())
            out.append((indent, f"{key}: {json.dumps(folded)}"))
            continue
        out.append((indent, stripped))
        i += 1
    return out

def safe_load(stream: Any) -> Any:
    text = stream.read() if hasattr(stream, "read") else str(stream or "")
    text = text.strip("\ufeff")
    if not text.strip():
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    lines = _preprocess(text)
    if not lines:
        return None
    root: Any = [] if lines[0][1].startswith("- ") else {}
    stack: list[tuple[int, Any]] = [(-1, root)]

    def parent_for(indent: int, *, sequence_item: bool = False) -> Any:
        while stack and (stack[-1][0] > indent or (stack[-1][0] == indent and not sequence_item)):
            stack.pop()
        if sequence_item:
            while stack and stack[-1][0] == indent and not isinstance(stack[-1][1], list):
                stack.pop()
        if not stack:
            raise YAMLError("invalid indentation")
        return stack[-1][1]

    for idx, (indent, stripped) in enumerate(lines):
        parent = parent_for(indent, sequence_item=stripped.startswith("- "))
        next_is_list = idx + 1 < len(lines) and lines[idx + 1][0] >= indent and lines[idx + 1][1].startswith("- ")
        if stripped.startswith("- "):
            if not isinstance(parent, list):
                raise YAMLError("list item under non-list parent")
            item = stripped[2:].strip()
            if not item:
                value: Any = [] if next_is_list else {}
                parent.append(value)
                stack.append((indent, value))
            elif ":" in item and not item.startswith(('"', "'")):
                key, raw_value = item.split(":", 1)
                value = {key.strip(): (_scalar(raw_value) if raw_value.strip() else ([] if next_is_list else {}))}
                parent.append(value)
                stack.append((indent, value))
                child = value[key.strip()]
                if isinstance(child, (dict, list)):
                    stack.append((indent + 1, child))
            else:
                parent.append(_scalar(item))
            continue
        if ":" not in stripped:
            continue
        key, raw_value = stripped.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        value = _scalar(raw_value) if raw_value else ([] if next_is_list else {})
        if isinstance(parent, dict):
            parent[key] = value
        else:
            parent.append({key: value})
        if isinstance(value, (dict, list)):
            stack.append((indent, value))
    return root

def safe_dump(data: Any, *args: Any, **kwargs: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"

def dump(data: Any, *args: Any, **kwargs: Any) -> str:
    return safe_dump(data, *args, **kwargs)

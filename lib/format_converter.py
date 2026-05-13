# SCOPE: os-only
"""Token-efficient format converter for LLM context injection.

Converts structured data (dicts/lists) from verbose JSON to compact formats
that use 30-80% fewer tokens while maintaining LLM comprehension.

Storage format (JSONL) is NEVER changed. Only the rendering for LLM context changes.

All methods are @staticmethod for easy use from bash hooks via python3 -c.

Python 3.9+ compatible. No external dependencies.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


def _to_str(value: Any) -> str:
    """Convert any value to a clean string representation."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _truncate(value: str, max_len: int = 50) -> str:
    """Truncate a string to max_len characters with '...' suffix."""
    if len(value) <= max_len:
        return value
    return value[: max_len - 3] + "..."


def _flatten_dict(d: dict, prefix: str = "", sep: str = ".") -> Dict[str, Any]:
    """Flatten a nested dict with dot notation keys."""
    items: Dict[str, Any] = {}
    for k, v in d.items():
        new_key = f"{prefix}{sep}{k}" if prefix else str(k)
        if isinstance(v, dict):
            items.update(_flatten_dict(v, prefix=new_key, sep=sep))
        else:
            items[new_key] = v
    return items


def _detect_columns(records: List[dict]) -> List[str]:
    """Auto-detect columns from a list of dicts, preserving insertion order."""
    seen: Dict[str, None] = {}
    for record in records:
        for key in record.keys():
            seen[key] = None
    return list(seen.keys())


class FormatConverter:
    """Token-efficient format converter for LLM context injection.

    All methods are static — no instance state needed.
    """

    @staticmethod
    def to_markdown_table(
        records: List[dict], columns: Optional[List[str]] = None
    ) -> str:
        """Render records as a Markdown table. ~34-38% savings vs JSON.

        Args:
            records: List of dicts to render.
            columns: Optional explicit column list. If None, auto-detected
                     from the union of all record keys.

        Returns:
            A Markdown table string. Returns "(no data)" for empty input.
        """
        if not records:
            return "(no data)"

        # Filter out non-dict entries gracefully
        valid = [r for r in records if isinstance(r, dict)]
        if not valid:
            return "(no data)"

        cols = columns if columns is not None else _detect_columns(valid)
        if not cols:
            return "(no data)"

        # Header
        header = "| " + " | ".join(cols) + " |"
        separator = "| " + " | ".join("---" for _ in cols) + " |"

        # Rows
        rows = []
        for record in valid:
            cells = []
            for col in cols:
                raw = record.get(col)
                cell = _truncate(_to_str(raw), 50)
                # Escape pipe characters so Markdown table stays intact
                cell = cell.replace("|", "\\|")
                cells.append(cell)
            rows.append("| " + " | ".join(cells) + " |")

        return "\n".join([header, separator] + rows)

    @staticmethod
    def to_tsv(
        records: List[dict], columns: Optional[List[str]] = None
    ) -> str:
        """Render records as TSV (tab-separated values). ~56-80% savings vs JSON.

        Args:
            records: List of dicts to render.
            columns: Optional explicit column list.

        Returns:
            A TSV string with header row. Returns "(no data)" for empty input.
        """
        if not records:
            return "(no data)"

        valid = [r for r in records if isinstance(r, dict)]
        if not valid:
            return "(no data)"

        cols = columns if columns is not None else _detect_columns(valid)
        if not cols:
            return "(no data)"

        def _escape_tsv(value: str) -> str:
            """Escape tabs and newlines for TSV safety."""
            return value.replace("\t", "\\t").replace("\n", "\\n").replace("\r", "\\r")

        lines = ["\t".join(_escape_tsv(c) for c in cols)]
        for record in valid:
            cells = []
            for col in cols:
                raw = record.get(col)
                cells.append(_escape_tsv(_to_str(raw)))
            lines.append("\t".join(cells))

        return "\n".join(lines)

    @staticmethod
    def to_compact_kv(record: dict, separator: str = "=") -> str:
        """Render a single record as key=value lines. ~40% savings vs JSON.

        Nested dicts are flattened with dot notation (a.b.c=value).

        Args:
            record: A single dict to render.
            separator: The separator between key and value (default "=").

        Returns:
            A multi-line key=value string. Returns "(no data)" for empty/None input.
        """
        if not record:
            return "(no data)"
        if not isinstance(record, dict):
            return _to_str(record)

        flat = _flatten_dict(record)
        if not flat:
            return "(no data)"

        lines = []
        for key, value in flat.items():
            lines.append(f"{key}{separator}{_to_str(value)}")
        return "\n".join(lines)

    @staticmethod
    def auto_format(
        records: Any,
        context: str = "agent",
    ) -> str:
        """Select optimal format based on data shape.

        Routing logic:
        - None or empty → "(no data)"
        - Single dict → compact_kv
        - List with 1-3 dicts → compact_kv per item, separated by blank lines
        - List with >3 uniform dicts → tsv (agent context) or markdown_table (human)
        - Anything else → JSON fallback

        Args:
            records: The data to format (any shape).
            context: "agent" (default) or "human". Affects list rendering choice.

        Returns:
            A compact string representation.
        """
        if records is None:
            return "(no data)"

        # Single dict
        if isinstance(records, dict):
            if not records:
                return "(no data)"
            return FormatConverter.to_compact_kv(records)

        # List
        if isinstance(records, list):
            if not records:
                return "(no data)"

            # Filter to dicts only for table/kv rendering
            dict_items = [r for r in records if isinstance(r, dict)]
            non_dict_items = [r for r in records if not isinstance(r, dict)]

            if not dict_items and non_dict_items:
                # Plain values list — join as lines
                return "\n".join(_to_str(v) for v in records)

            if len(dict_items) <= 3:
                # Small number of items: compact_kv per item
                parts = []
                for i, item in enumerate(dict_items):
                    if len(dict_items) > 1:
                        parts.append(f"[{i + 1}]")
                    parts.append(FormatConverter.to_compact_kv(item))
                return "\n".join(parts)

            # Larger list: table format
            if context == "human":
                return FormatConverter.to_markdown_table(dict_items)
            else:
                return FormatConverter.to_tsv(dict_items)

        # Fallback: JSON
        try:
            return json.dumps(records, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(records)

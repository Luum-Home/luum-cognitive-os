from __future__ import annotations

from pathlib import Path


def index_tree_sitter(root: Path) -> dict:
    """Optional Tree-sitter backend placeholder.

    The spike keeps this dependency-free. A later implementation can import
    tree-sitter-language-pack or shell out to an MCP/indexer and return symbols,
    imports, calls, and entrypoints under this stable interface.
    """
    return {"available": False, "root": str(root), "symbols": []}

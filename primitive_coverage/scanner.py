from __future__ import annotations

from pathlib import Path

from primitive_coverage.adapters import load_adapter
from primitive_coverage.indexers.cos_audits import merge_cos_audits
from primitive_coverage.indexers.filesystem import repo_files
from primitive_coverage.indexers.markdown import extract_claims
from primitive_coverage.indexers.runtime_logs import build_runtime_corpus, runtime_seen_in_corpus
from primitive_coverage.indexers.static_rules import apply_static_signals, build_corpus
from primitive_coverage.model import CoverageReport, PrimitiveRow

FAMILY_ALIASES = {"skills": "skill", "hooks": "hook", "rules": "rule", "scripts": "script", "docs": "doc"}


def primitive_id(family: str, rel_path: str) -> str:
    return f"{family}:{rel_path}"


def scan_repository(root: str | Path = ".", adapter: str = "generic", include_cos_audits: bool = True) -> CoverageReport:
    root_path = Path(root).resolve()
    config = load_adapter(adapter)
    rows: dict[str, PrimitiveRow] = {}
    for family, spec in config.get("families", {}).items():
        singular = FAMILY_ALIASES.get(family, family)
        for path in repo_files(root_path, spec.get("patterns", [])):
            rel = path.relative_to(root_path).as_posix()
            row = PrimitiveRow(primitive_id=primitive_id(singular, rel), family=singular, path=rel)
            if singular == "doc":
                row.claims = extract_claims(path)
            rows[row.primitive_id] = row

    corpus = build_corpus(root_path)
    runtime_corpus = build_runtime_corpus(root_path)
    for row in rows.values():
        apply_static_signals(root_path, row, corpus)
        row.signals["runtime_seen"] = row.signals.get("runtime_seen", False) or runtime_seen_in_corpus(
            runtime_corpus, Path(row.path).name
        )

    if include_cos_audits and adapter == "cognitive-os":
        merge_cos_audits(root_path, rows)

    for row in rows.values():
        row.recompute()
    return CoverageReport(adapter=adapter, root=root_path, rows=list(rows.values()))

from __future__ import annotations

from pathlib import Path


def build_runtime_corpus(root: Path, max_bytes_per_file: int = 250_000) -> str:
    metrics = root / ".cognitive-os" / "metrics"
    if not metrics.exists():
        return ""
    chunks: list[str] = []
    for path in metrics.glob("*.jsonl"):
        try:
            chunks.append(path.read_text(encoding="utf-8", errors="ignore")[-max_bytes_per_file:])
        except OSError:
            continue
    return "\n".join(chunks)


def runtime_seen_in_corpus(corpus: str, name: str) -> bool:
    return bool(corpus and name in corpus)

from __future__ import annotations

from pathlib import Path

from .filesystem import read_text


def extract_claims(path: Path) -> list[str]:
    claims: list[str] = []
    for line in read_text(path).splitlines():
        lowered = line.lower()
        if any(word in lowered for word in ("automatic", "guarantee", "blocks", "coverage", "detects")):
            claims.append(line.strip())
    return claims[:20]

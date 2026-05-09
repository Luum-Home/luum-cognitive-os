"""Guard Cognitive OS core against consumer-project vocabulary leakage."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORE_PATHS = [
    "skills",
    "hooks",
    "rules",
    "agents",
    "squads",
    "templates",
    "scripts",
    "lib",
    "docs",
]
IGNORED_PREFIXES = (
    "docs/research/",
    "docs/reports/",
)
IGNORED_PARTS = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache"}
PRIVATE_OR_CONSUMER_TERMS = (
    "n1u",
    "gamer-wallet",
    "altatienda",
    "alta-tienda",
    "wallet-go",
    "wallet/wallet-go",
    "bff-ninja",
    "users-core",
    "users-auth",
    "acme-gateway",
    "Gate1 patterns",
)


def iter_scanned_files() -> list[Path]:
    files: list[Path] = []
    for relative_root in CORE_PATHS:
        root = ROOT / relative_root
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(ROOT).as_posix()
            if IGNORED_PARTS.intersection(path.relative_to(ROOT).parts):
                continue
            if any(relative.startswith(prefix) for prefix in IGNORED_PREFIXES):
                continue
            files.append(path)
    return files


def test_core_surfaces_do_not_embed_consumer_private_terms() -> None:
    offenders: list[str] = []
    for path in iter_scanned_files():
        text = path.read_text(errors="ignore")
        lowered = text.lower()
        hits = [term for term in PRIVATE_OR_CONSUMER_TERMS if term.lower() in lowered]
        if hits:
            offenders.append(f"{path.relative_to(ROOT)}: {', '.join(hits)}")

    assert not offenders, "Consumer/private terms leaked into SO core:\n" + "\n".join(offenders)

"""Guard Cognitive OS core against consumer-project vocabulary leakage.

The protected names are NOT written in this file: a public list of the names to
protect is itself the leak. Each one is stored as the SHA-256 of the lowercased
name, and every candidate token of a scanned file is hashed and compared (see
`term_candidates` in scripts/provenance_scan.py). Matching is per token: a name
glued to other letters is not a hit.

Extra names can be checked locally, in clear and outside git, with
`COS_CONSUMER_TERMS_FILE=<file>` (one name per line, `#` comments allowed).

To add a name to the committed list:
    python3 -c "import hashlib,sys; print(hashlib.sha256(sys.argv[1].strip().lower().encode()).hexdigest())" NAME
"""

from __future__ import annotations

import base64
import importlib.util
import os
import sys
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
    "docs/03-PoCs/research/",
    "docs/06-Daily/reports/",
)
IGNORED_PARTS = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache"}
# SHA-256 of each protected consumer/private name (lowercased). 11 names.
PRIVATE_OR_CONSUMER_TERM_SHA256 = frozenset(
    {
        "b1b631b0b70b5b3ab8f0bd266b926f7ad5936d75a9194cdf6e35b3e196b26909",
        "46fcb8dead4794bb0ada9cca873ad128697abf18cd3debd936ee80becf56b640",
        "7466e5b8e237b638f142fc8eecb3095c2b007d2086e567e54d63915272d5f356",
        "d9ab497e9b371ba5ab6af1152b950c05d5cd131fa31ece707c0bb36f35c8b212",
        "2b0f954b050a2f3f18f9c04be7730608d3b8dd9e0a1b86a739a55528b5c06523",
        "fc965ad171e3f52a5383b414a782d1bc79afc3149fdf431a6df8b0d17887c75c",
        "24d29fb114db1937ce33a534f89b145b927fa0e2ebfb200a3d18563fe08dbc97",
        "7552649f972894034be6e06c1c73b484223cd285c52ba326c9c168e20fd98c19",
        "3c869ea273a5b2407f9b7661769673f6f53d6e585d69f32f6fce820f56807469",
        "6c25a13751863bc278aec47d7f8272e858304ee7ae52822ee6e150452beeee10",
        "311b62fcebbef0ce93becacd84ffd2e8eba1b929dbf8daa4c67f58e88a173003",
    }
)
# One protected name, reversed and base64-encoded so it is not greppable here.
# Chosen on purpose: the least sensitive entry of the list.
ENCODED_PROTECTED_FIXTURE = "b21lZC1rYXZvcnRuZXo="


def _load_scanner():
    spec = importlib.util.spec_from_file_location(
        "provenance_scan_for_leak_audit", ROOT / "scripts" / "provenance_scan.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    # @dataclass resolves annotations through sys.modules[module.__name__].
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


SCANNER = _load_scanner()


def protected_digests() -> frozenset[str]:
    digests = set(PRIVATE_OR_CONSUMER_TERM_SHA256)
    local = os.environ.get("COS_CONSUMER_TERMS_FILE", "")
    if local and Path(local).is_file():
        for raw in Path(local).read_text(encoding="utf-8").splitlines():
            term = raw.strip()
            if term and not term.startswith("#"):
                digests.add(SCANNER.fingerprint_term(term))
    return frozenset(digests)


def decode_fixture(encoded: str) -> str:
    return base64.b64decode(encoded).decode("utf-8")[::-1]


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


def leaked_terms(text: str, digests: frozenset[str]) -> list[str]:
    return SCANNER.hashed_term_hits(text, digests)


def test_committed_list_holds_only_digests() -> None:
    assert len(PRIVATE_OR_CONSUMER_TERM_SHA256) == 11
    assert all(len(d) == 64 and int(d, 16) >= 0 for d in PRIVATE_OR_CONSUMER_TERM_SHA256)


def test_a_protected_term_is_detected_without_writing_it() -> None:
    term = decode_fixture(ENCODED_PROTECTED_FIXTURE)
    assert SCANNER.fingerprint_term(term) in PRIVATE_OR_CONSUMER_TERM_SHA256
    digests = protected_digests()

    for text in (
        f"see the {term} integration",
        f"path: services/{term}/main.go",
        f"See The {term.upper()} Integration",
    ):
        assert leaked_terms(text, digests) == [term], text

    # Per-token matching: glued to other letters it is a different word.
    assert leaked_terms(f"x{term.replace('-', '')}x", digests) == []
    assert leaked_terms("a perfectly generic sentence about gateways", digests) == []


def test_core_surfaces_do_not_embed_consumer_private_terms() -> None:
    digests = protected_digests()
    offenders: list[str] = []
    for path in iter_scanned_files():
        hits = leaked_terms(path.read_text(errors="ignore"), digests)
        if hits:
            offenders.append(f"{path.relative_to(ROOT)}: {', '.join(hits)}")

    assert not offenders, "Consumer/private terms leaked into SO core:\n" + "\n".join(offenders)

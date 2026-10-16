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
        "c0c990fbdc85027e59d6528f858769f4e0f5015d17b7945dd81030ab8acc67e3",
        "46664fea18295e86578517753bc5baff7c00ec0cefebe9c582d19bc489896498",
        "b64f012e7ddc7954e656eced07a6620b65451c5881448fd78674e7da3b2b3801",
        "b8f10cad704654f9614ab6ffc8b6c7899307f7da411466f230ac48bcc4199352",
        "5ab5808656324694584f4ee5a936bb4bdeb01e144d47b0957678b8e140657da6",
        "867c3779d30912fe37446b41f78efbc8d3b4e529eae18f7614b719639d104914",
        "a519d9d16879859a5c5a6b763d6bd51059453b4a414370e5d6526df6bbcdfca9",
        "d87a227d11b1264c151e5e732f4b6b968fac4eea9610c532bbf1049b52fe3cb4",
        "0f409bad808d3ae3d82d35761b3f88cd083c70651b14578edbd1cd2acaf5b296",
        "b3cb47f1c6975f1bd174f14911f59e91160965bdd9cad048ff279690c8c10680",
        "c1c0f4a6262a098a2741fa95c81c7755112d0c3460397761ddb9d511651a0ce9",
    }
)
# One protected name, reversed and base64-encoded so it is not greppable here.
# Chosen on purpose: the least sensitive entry of the list.
ENCODED_PROTECTED_FIXTURE = "eWF3ZXRhZy1lbWNh"


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

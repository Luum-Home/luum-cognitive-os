#!/usr/bin/env python3
# SCOPE: os-only
"""Regenerate the committed HMAC digests of the protected names.

The protected names never enter the repo. They live in a local list outside any
checkout (`COS_CONSUMER_TERMS_FILE`, default ~/.config/luum/leak-terms.txt), one
per line, `#` comments allowed:

    some-name           -> term of the anti-leak test (any token of a core file)
    path:other-name     -> component of a local project path (provenance manifest)

The key comes from COS_LEAK_HMAC_KEY or the key file (COS_LEAK_HMAC_KEY_FILE,
default ~/.config/luum/leak-hmac.key), exactly as the scanner reads it. This
script rewrites the digest blocks between the `BEGIN/END leak-terms-hmac`
markers of tests/audit/test_no_consumer_domain_leakage.py and
manifests/provenance-scan.yaml. Output is sorted, so the same key and list give
the same bytes. It never prints the key or the names, only counts.

Exit codes: 0 up to date / rewritten, 1 out of date (--check), 2 error.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEST_FILE = ROOT / "tests" / "audit" / "test_no_consumer_domain_leakage.py"
MANIFEST = ROOT / "manifests" / "provenance-scan.yaml"
TERMS_ENV = "COS_CONSUMER_TERMS_FILE"
DEFAULT_TERMS_FILE = "~/.config/luum/leak-terms.txt"
BEGIN = "BEGIN leak-terms-hmac"
END = "END leak-terms-hmac"


def _load_scanner():
    spec = importlib.util.spec_from_file_location("provenance_scan_for_leak_hmac", ROOT / "scripts" / "provenance_scan.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def parse_terms(text: str) -> tuple[list[str], list[str]]:
    terms: list[str] = []
    paths: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("path:"):
            paths.append(line[5:].strip())
        else:
            terms.append(line)
    return terms, paths


def digests(names: list[str], key: bytes, fingerprint) -> list[str]:
    return sorted({fingerprint(name, key) for name in names if name})


def replace_block(text: str, body_lines: list[str], label: str) -> str:
    lines = text.splitlines(keepends=True)
    starts = [i for i, line in enumerate(lines) if BEGIN in line]
    ends = [i for i, line in enumerate(lines) if END in line]
    if len(starts) != 1 or len(ends) != 1 or ends[0] < starts[0]:
        raise SystemExit(f"ERROR: {label}: expected exactly one {BEGIN} ... {END} block")
    return "".join(lines[: starts[0] + 1] + body_lines + lines[ends[0]:])


def render_test_block(values: list[str]) -> list[str]:
    return [f'        "{value}",\n' for value in values]


def render_manifest_block(values: list[str]) -> list[str]:
    return [f'    - "{value}"\n' for value in values]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--terms-file", default=None, help=f"Local list of names. Default: ${TERMS_ENV} or {DEFAULT_TERMS_FILE}.")
    parser.add_argument("--check", action="store_true", help="Do not write; exit 1 if the committed digests are out of date.")
    args = parser.parse_args(argv)

    scanner = _load_scanner()
    key = scanner.load_leak_hmac_key()
    if key is None:
        print(f"ERROR: {scanner.missing_key_message()}", file=sys.stderr)
        return 2
    terms_path = Path(args.terms_file or os.environ.get(TERMS_ENV) or DEFAULT_TERMS_FILE).expanduser().resolve()
    if terms_path.is_relative_to(ROOT):
        print("ERROR: the list of protected names must live outside the repo", file=sys.stderr)
        return 2
    try:
        terms, paths = parse_terms(terms_path.read_text(encoding="utf-8"))
    except OSError as exc:
        print(f"ERROR: cannot read the list of protected names: {exc.strerror}", file=sys.stderr)
        return 2
    if not terms or not paths:
        print("ERROR: the list needs at least one term and one path: entry", file=sys.stderr)
        return 2

    term_values = digests(terms, key, scanner.fingerprint_term)
    path_values = digests(paths, key, scanner.fingerprint_term)
    stale: list[str] = []
    for target, values, render in (
        (TEST_FILE, term_values, render_test_block),
        (MANIFEST, path_values, render_manifest_block),
    ):
        current = target.read_text(encoding="utf-8")
        updated = replace_block(current, render(values), target.name)
        if updated != current:
            stale.append(target.relative_to(ROOT).as_posix())
            if not args.check:
                target.write_text(updated, encoding="utf-8")

    summary = f"terms={len(term_values)} paths={len(path_values)}"
    if args.check:
        if stale:
            print(f"leak-terms-hmac: OUT OF DATE ({summary}): {', '.join(stale)}", file=sys.stderr)
            return 1
        print(f"leak-terms-hmac: up to date ({summary})")
        return 0
    print(f"leak-terms-hmac: {'rewrote ' + ', '.join(stale) if stale else 'already up to date'} ({summary})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

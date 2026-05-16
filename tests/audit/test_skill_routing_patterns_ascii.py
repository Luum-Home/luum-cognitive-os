"""ASCII routing pattern audit (REQ-002, REQ-003, REQ-004).

Walks ``skills/**/SKILL.md`` and ``packages/*/skills/**/SKILL.md`` and rejects
any ``routing_patterns:`` entry whose ``pattern:`` string contains a non-ASCII
codepoint or a locale-folding character class pairing an ASCII letter with an accented Latin letter.

Scan root override: set ``COS_ROUTING_AUDIT_ROOT`` to point the walker at a
tmpdir (used by AC-002 / AC-003).
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Iterator, List

import yaml


# ---- helpers ---------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
# locale-folding detector: ASCII letter paired with accented Latin letter
# (or reversed) inside a 2-char regex character class.
# U+00C0 through U+024F covers Latin-1/Latin-Extended-A.
_LOCALE_FOLDING_RE = re.compile(
    r"\[([a-zA-Z])([\u00C0-\u024F])\]"
    r"|\[([\u00C0-\u024F])([a-zA-Z])\]"
)
_COMMENT_RE = re.compile(r"(?<!\\)#.*$", re.MULTILINE)


def _scan_root() -> Path:
    override = os.environ.get("COS_ROUTING_AUDIT_ROOT")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2]


def _iter_skill_files(root: Path) -> Iterator[Path]:
    for sub in ("skills", "packages"):
        base = root / sub
        if not base.is_dir():
            continue
        for path in base.rglob("SKILL.md"):
            yield path


def _strip_comments(pattern: str) -> str:
    return _COMMENT_RE.sub("", pattern)


def _audit_file(path: Path) -> List[str]:
    """Return list of offense strings for a single SKILL.md."""
    offenses: List[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return offenses
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return offenses
    try:
        front = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return offenses
    if not isinstance(front, dict):
        return offenses
    patterns = front.get("routing_patterns")
    if not patterns or not isinstance(patterns, list):
        return offenses
    for entry in patterns:
        if not isinstance(entry, dict):
            continue
        pat = entry.get("pattern")
        if not isinstance(pat, str):
            continue
        stripped = _strip_comments(pat)
        lf = _LOCALE_FOLDING_RE.search(stripped)
        if lf:
            offenses.append(
                f"{path}: pattern '{pat}' uses locale-folding class '{lf.group(0)}'"
            )
            continue
        for ch in stripped:
            if ord(ch) >= 0x80:
                offenses.append(
                    f"{path}: pattern '{pat}' contains U+{ord(ch):04X}"
                )
                break
    return offenses


def _run_audit(root: Path) -> List[str]:
    all_offenses: List[str] = []
    for p in _iter_skill_files(root):
        all_offenses.extend(_audit_file(p))
    return all_offenses


def _write_skill(tmp_path: Path, frontmatter: str) -> Path:
    skill_dir = tmp_path / "skills" / "test-skill"
    skill_dir.mkdir(parents=True, exist_ok=True)
    f = skill_dir / "SKILL.md"
    f.write_text(frontmatter, encoding="utf-8")
    return f


# ---- tests -----------------------------------------------------------------


def test_rejects_locale_folding_class(tmp_path: Path) -> None:
    f = _write_skill(
        tmp_path,
        "---\n"
        "name: test\n"
        "routing_patterns:\n"
        "  - pattern: '[" + chr(0x00F1) + "n]uevo'\n"
        "---\n",
    )
    offenses = _run_audit(tmp_path)
    assert offenses, "audit failed to detect locale-folding class"
    assert any(str(f) in o for o in offenses), offenses
    assert any("locale-folding" in o for o in offenses), offenses
    for o in offenses:
        print(o, file=sys.stderr)


def test_rejects_non_ascii_codepoint(tmp_path: Path) -> None:
    f = _write_skill(
        tmp_path,
        "---\n"
        "name: test\n"
        "routing_patterns:\n"
        "  - pattern: 'a" + chr(0x00F1) + "adir'\n"
        "---\n",
    )
    offenses = _run_audit(tmp_path)
    assert offenses, "audit failed to detect non-ASCII codepoint"
    assert any(str(f) in o for o in offenses), offenses
    assert any("U+00F1" in o or "U+00E1" in o for o in offenses), offenses
    for o in offenses:
        print(o, file=sys.stderr)


def test_passes_current_repo() -> None:
    root = _scan_root()
    offenses = _run_audit(root)
    assert not offenses, "current repo HEAD has routing pattern offenses:\n" + "\n".join(offenses)


def test_ignores_non_routing_unicode(tmp_path: Path) -> None:
    _write_skill(
        tmp_path,
        (
            "---\n"
            "name: test\n"
            "description: |\n"
            "  Runtime multilingual prose: a"
            + chr(0x00F1)
            + "adir un hook nuevo con "
            + chr(0x00E9)
            + "xito.\n"
            "routing_patterns:\n"
            "  - pattern: '^add-hook$'\n"
            "---\n"
        ),
    )
    offenses = _run_audit(tmp_path)
    assert not offenses, offenses


def test_strips_comments_before_scan(tmp_path: Path) -> None:
    _write_skill(
        tmp_path,
        (
            "---\n"
            "name: test\n"
            "routing_patterns:\n"
            "  - pattern: '^run-tests$  # " + chr(0x00E9) + "xito'\n"
            "---\n"
        ),
    )
    offenses = _run_audit(tmp_path)
    assert not offenses, offenses


def test_handles_missing_routing_patterns(tmp_path: Path) -> None:
    _write_skill(
        tmp_path,
        "---\nname: test\ndescription: no routing patterns here\n---\n",
    )
    offenses = _run_audit(tmp_path)
    assert not offenses, offenses

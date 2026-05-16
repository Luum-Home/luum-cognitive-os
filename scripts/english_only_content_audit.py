#!/usr/bin/env python3
# SCOPE: os-only
"""Audit repository text for English-only content.

This audit scans repository text for signals that content is written in a
human language other than English. It uses lingua-language-detector for
probabilistic paragraph-level detection and tree-sitter for extracting
comments and string literals from source code files.

v2 replaces the static base64 blocklist with statistical language detection
to catch mixed-language text that the keyword list missed.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator, Sequence

SCHEMA_VERSION = "english-only-content-audit/v2"

# Files treated as prose (paragraph-level detection).
PROSE_SUFFIXES = {
    ".adoc", ".cfg", ".css", ".html", ".ini", ".json", ".jsonl",
    ".md", ".mdx", ".sql", ".toml", ".txt", ".yaml", ".yml",
}

# Files where we extract comments + string literals via tree-sitter.
CODE_SUFFIXES = {
    ".go", ".js", ".jsx", ".py", ".sh", ".ts", ".tsx",
}

TEXT_SUFFIXES = PROSE_SUFFIXES | CODE_SUFFIXES | {
    ".bats", ".c", ".conf", ".h", ".rs",
}

DEFAULT_EXCLUDE_GLOBS = (
    ".git/**",
    "**/__pycache__/**",
    "**/.pytest_cache/**",
    "**/.mypy_cache/**",
    "**/.venv/**",
    "**/node_modules/**",
    # Intentional multilingual runtime fixture corpus for ADR-298 routing benchmarks.
    "manifests/routing-benchmark-corpus.yaml",
)

FORBIDDEN_PUNCTUATION = "".join(chr(code) for code in (0x00A1, 0x00BF))
FORBIDDEN_PUNCTUATION_RE = re.compile("[" + re.escape(FORBIDDEN_PUNCTUATION) + "]")

# Smoke-mode keyword corpus. Kept in base64 so this file stays English-only.
# Used ONLY by --smoke (fast pre-commit pass that does not load lingua).
# The lingua-based audit() remains the authoritative CI gate.
_SMOKE_TERMS_B64 = (
    "YWRlbcOhcw==", "YWdyZWfDoQ==", "YWdyZWdhcg==", "YWdyZWd1ZW1vcw==",
    "YWxndWllbg==", "YW7DoWxpc2lz", "YXJyZWdsw6E=", "YXJyZWdsYXI=",
    "YXPDrQ==", "YXV0b23DoXRpY28=", "Ym9ycsOh", "Ym9ycmFy", "YnVlbmFz",
    "Y8OzZGlnbw==", "Y8OzbW8=", "Y29uc3RydWNjacOzbg==", "Y3XDoWw=",
    "Y3XDoWxlcw==", "ZGViZXLDrWE=", "ZGViZXLDrWFu", "ZGVjaXNpw7Nu",
    "ZGVzYXJyb2xsYWRvcg==", "ZG9jdW1lbnRhY2nDs24=", "ZMOzbmRl",
    "ZWplY3V0w6E=", "ZW4gZXNwYcOxb2w=", "ZXNwYcOxb2w=", "ZXN0w6E=",
    "ZXN0w6Fu", "ZXN0bw==", "ZXh0cmHDrWRv", "aGFjw6k=", "aGFnYW1vcw==",
    "aGVycmFtaWVudGE=", "aGVycmFtaWVudGFz", "aW52ZXN0aWdhY2nDs24=",
    "aW52ZXN0aWfDoQ==", "bMOtbmVh", "bcOhcw==", "bmVjZXNpdG8=",
    "bmluZ8O6bg==", "b3JxdWVzdGFjacOzbg==", "cGFsYWJyZXLDrWE=",
    "cG9kw6lz", "cG9kcsOtYXM=", "cHLDoWN0aWNhcw==", "cXXDqQ==",
    "cXVlZMOz", "cXVlcsOpcw==", "cmV2aXPDoQ==", "c2VzacOzbg==",
    "c8OtbnRlc2lz", "c29sdWNpb25lbW9z", "dGFtYmnDqW4=", "dMOpY25pY28=",
    "dG9kYXbDrWE=", "w7puaWNv", "dXPDoQ==", "dsOtYQ==",
    "Ym9uam91cg==", "bWVyY2k=", "bW9uc2lldXI=", "bWFkYW1l", "cG91cnF1b2k=",
    "YXVmZ2FiZQ==", "Yml0dGU=", "ZGFua2U=", "d2ljaHRpZw==",
    "c2NobmVsbA==", "Z3Jhemll", "cHJlZ28=", "cGVyY2jDqA==", "YWRlc3Nv",
    "b2JyaWdhZG8=", "b2JyaWdhZGE=", "cG9ycXVl", "cXVhbmRv", "ZmVjaGFy",
)
_SMOKE_TERM_RE: re.Pattern[str] | None = None


def _get_smoke_pattern() -> re.Pattern[str]:
    """Decode the base64 keyword corpus and compile a single regex (memoised)."""
    global _SMOKE_TERM_RE
    if _SMOKE_TERM_RE is None:
        import base64
        terms = tuple(
            base64.b64decode(t).decode("utf-8") for t in _SMOKE_TERMS_B64
        )
        _SMOKE_TERM_RE = re.compile(
            r"(?<!\w)(?:"
            + "|".join(re.escape(t) for t in sorted(terms, key=len, reverse=True))
            + r")(?!\w)",
            re.IGNORECASE,
        )
    return _SMOKE_TERM_RE


ALLOW_MARKERS = (
    "english-only-content-audit: allow",
    "non-english-content-audit: allow",
)
ALLOW_BLOCK_MARKER = "english-only-content-audit: allow-block"

# Regex patterns for stripping non-prose content from markdown/text.
_CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_TABLE_LINE_RE = re.compile(r"^\s*\|")
_FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?;])\s+")

# Language detection is lazy-imported to avoid slow startup on --help.
_DETECTOR = None
_LINGUA_ENGLISH = None


def _get_detector(min_relative_distance: float = 0.25):
    """Lazy-initialize the lingua detector (loads ONNX model ~1-2s)."""
    global _DETECTOR, _LINGUA_ENGLISH
    if _DETECTOR is None:
        from lingua import Language, LanguageDetectorBuilder  # type: ignore[import]
        _LINGUA_ENGLISH = Language.ENGLISH
        LANGUAGES = [
            Language.ENGLISH, Language.SPANISH, Language.FRENCH,
            Language.GERMAN, Language.PORTUGUESE, Language.ITALIAN,
        ]
        _DETECTOR = (
            LanguageDetectorBuilder
            .from_languages(*LANGUAGES)
            .with_minimum_relative_distance(min_relative_distance)
            .build()
        )
    return _DETECTOR, _LINGUA_ENGLISH


# Tree-sitter parsers are lazy-initialized per language.
_TS_PARSERS: dict[str, object] = {}


def _get_ts_parser(lang: str):
    """Lazy-initialize a tree-sitter parser for the given language key."""
    if lang in _TS_PARSERS:
        return _TS_PARSERS[lang]

    from tree_sitter import Language as TSLanguage, Parser  # type: ignore[import]

    if lang == "python":
        import tree_sitter_python as _m  # type: ignore[import]
        grammar = TSLanguage(_m.language())
    elif lang == "typescript":
        import tree_sitter_typescript as _m  # type: ignore[import]
        grammar = TSLanguage(_m.language_typescript())
    elif lang == "tsx":
        import tree_sitter_typescript as _m  # type: ignore[import]
        grammar = TSLanguage(_m.language_tsx())
    elif lang == "javascript":
        import tree_sitter_javascript as _m  # type: ignore[import]
        grammar = TSLanguage(_m.language())
    elif lang == "go":
        import tree_sitter_go as _m  # type: ignore[import]
        grammar = TSLanguage(_m.language())
    elif lang == "bash":
        import tree_sitter_bash as _m  # type: ignore[import]
        grammar = TSLanguage(_m.language())
    else:
        return None

    parser = Parser(grammar)
    _TS_PARSERS[lang] = parser
    return parser


def _suffix_to_ts_lang(suffix: str) -> str | None:
    return {
        ".py": "python",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".js": "javascript",
        ".jsx": "javascript",
        ".go": "go",
        ".sh": "bash",
        ".bats": "bash",
    }.get(suffix)


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    file: str
    line: int
    evidence: str
    message: str


@dataclass(frozen=True)
class Report:
    schema_version: str
    root: str
    scanned_files: int
    finding_count: int
    findings: tuple[Finding, ...]


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------

def run_git_ls_files(root: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return [p for p in proc.stdout.decode("utf-8", errors="ignore").split("\0") if p]


def discover_files(root: Path, include_untracked: bool = False) -> list[str]:
    tracked = run_git_ls_files(root)
    if not include_untracked:
        return tracked
    seen = set(tracked)
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel not in seen:
            tracked.append(rel)
            seen.add(rel)
    return tracked


def is_probably_text(path: Path) -> bool:
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return False
    try:
        chunk = path.read_bytes()[:4096]
    except OSError:
        return False
    return b"\0" not in chunk


def excluded(rel_path: str, exclude_globs: Sequence[str]) -> bool:
    return any(fnmatch.fnmatch(rel_path, pattern) for pattern in exclude_globs)


# ---------------------------------------------------------------------------
# Allow-marker helpers
# ---------------------------------------------------------------------------

def _context_window(lines: list[str], idx: int, radius: int = 3) -> str:
    """Return a slice of lines around idx for allow-marker checking."""
    start = max(0, idx - radius)
    end = min(len(lines), idx + radius + 1)
    return "\n".join(lines[start:end])


def _has_allow_marker(window: str) -> bool:
    return any(m in window for m in ALLOW_MARKERS)


def _has_allow_block_marker(block_text: str) -> bool:
    return ALLOW_BLOCK_MARKER in block_text


# ---------------------------------------------------------------------------
# Non-Latin script / forbidden-punctuation pre-pass (fast)
# ---------------------------------------------------------------------------

ALLOWED_NON_ASCII_SYMBOLS = {chr(0x00B5)}  # MICRO SIGN: technical unit prefix.
_MATH_CONTEXT_CHARS = set("=+-*/^_()[]{}<>≤≥≈≠∞∑∏√∫.,:; \t")


def _is_greek_technical_symbol(line: str, index: int) -> bool:
    """Return True for Greek letters used as math/code notation, not prose.

    Greek letters are common variable names in technical examples (`alpha`,
    `beta`, coefficients, angles). The English-only audit should allow that
    notation while still flagging Greek prose. Require a code-like operator on
    the same line and non-word/math boundaries around the symbol.
    """
    if not any(op in line for op in ("=", "+", "-", "*", "/", "^", "≤", "≥", "≈", "≠")):
        return False
    prev_char = line[index - 1] if index > 0 else " "
    next_char = line[index + 1] if index + 1 < len(line) else " "
    return prev_char in _MATH_CONTEXT_CHARS and next_char in _MATH_CONTEXT_CHARS


def first_forbidden_script_letter(line: str) -> str | None:
    """Return the first alphabetic character from a disallowed script.

    This is intentionally a script guard, not a language detector: Latin
    letters with diacritics are left for the paragraph-level detector so names
    and loanwords do not fail solely because of one character. Greek letters
    are allowed only in math/code notation contexts; Greek prose is flagged.
    """
    for idx, char in enumerate(line):
        if ord(char) < 128 or char in ALLOWED_NON_ASCII_SYMBOLS:
            continue
        category = unicodedata.category(char)
        if not category.startswith("L"):
            continue
        try:
            name = unicodedata.name(char)
        except ValueError:
            return char
        if "LATIN" in name:
            continue
        if "GREEK" in name and _is_greek_technical_symbol(line, idx):
            continue
        return char
    return None


def _fast_prepass_finding(
    rel_path: str, line_no: int, line: str,
) -> Finding | None:
    script_match = first_forbidden_script_letter(line)
    if script_match is not None:
        return Finding(
            code="non-english-script",
            severity="error",
            file=rel_path,
            line=line_no,
            evidence=script_match,
            message="Non-Latin script character found.",
        )
    punct = FORBIDDEN_PUNCTUATION_RE.search(line)
    if punct:
        return Finding(
            code="non-english-punctuation",
            severity="error",
            file=rel_path,
            line=line_no,
            evidence=punct.group(0),
            message="Non-English punctuation character found.",
        )
    return None


# ---------------------------------------------------------------------------
# Lingua paragraph-level detection
# ---------------------------------------------------------------------------

def _strip_prose_noise(text: str) -> str:
    """Remove code fences, inline code, URLs, and table lines from prose."""
    text = _CODE_FENCE_RE.sub("", text)
    text = _INLINE_CODE_RE.sub("", text)
    text = _URL_RE.sub("", text)
    lines = [l for l in text.splitlines() if not _TABLE_LINE_RE.match(l)]
    return "\n".join(lines)


def _strip_frontmatter(text: str) -> str:
    return _FRONTMATTER_RE.sub("", text, count=1)


def _word_count(text: str) -> int:
    return len(text.split())


def _detect_chunk(
    text: str,
    detector,
    english,
    min_confidence: float,
) -> tuple[str, float] | None:
    """Detect non-English language in a chunk. Returns (lang_name, confidence) or None."""
    detected = detector.detect_language_of(text)
    if detected is None or detected == english:
        return None
    confidences = detector.compute_language_confidence_values(text)
    if not confidences:
        return None
    top = confidences[0]
    if top.language != english and top.value >= min_confidence:
        return (top.language.name, top.value)
    return None


def _lingua_findings_for_paragraphs(
    rel_path: str,
    text: str,
    lines: list[str],
    min_words: int,
    min_confidence: float,
) -> list[Finding]:
    """Run lingua on paragraphs and individual sentences of `text`.

    Two-pass strategy:
    1. Paragraph-level: catches sections written entirely in a foreign language.
    2. Sentence-level: catches individual foreign sentences embedded in English
       paragraphs (common in mixed-language documents).
    """
    detector, english = _get_detector()
    findings: list[Finding] = []
    seen_lines: set[int] = set()  # Deduplicate findings by first_line.

    text = _strip_frontmatter(text)
    original_lines = text.splitlines()

    # Collect paragraphs: (joined_text, first_line_1indexed).
    paragraphs: list[tuple[str, int]] = []
    current: list[str] = []
    current_start = 1
    for i, raw_line in enumerate(original_lines, 1):
        stripped = raw_line.strip()
        if stripped:
            if not current:
                current_start = i
            current.append(stripped)
        else:
            if current:
                paragraphs.append((" ".join(current), current_start))
                current = []
    if current:
        paragraphs.append((" ".join(current), current_start))

    # Sentence-level min_words and confidence are more lenient.
    sent_min_words = max(5, min_words // 2)
    sent_min_confidence = max(0.55, min_confidence - 0.20)

    for para_text, first_line in paragraphs:
        # Allow-marker check.
        window_start = max(0, first_line - 4)
        window_end = min(len(lines), first_line + 6)
        raw_window = "\n".join(lines[window_start:window_end])
        if _has_allow_block_marker(raw_window) or _has_allow_marker(raw_window):
            continue

        clean_para = _strip_prose_noise(para_text)

        # --- Pass 1: paragraph-level ---
        if _word_count(clean_para) >= min_words:
            result = _detect_chunk(clean_para, detector, english, min_confidence)
            if result is not None and first_line not in seen_lines:
                lang_name, conf = result
                seen_lines.add(first_line)
                findings.append(Finding(
                    code="non-english-paragraph",
                    severity="error",
                    file=rel_path,
                    line=first_line,
                    evidence=clean_para[:120].replace("\n", " "),
                    message=f"Paragraph detected as {lang_name} (confidence {conf:.2f}).",
                ))
                continue  # No need for sentence-level if para already flagged.

            # Weak-English check on paragraph.
            if _word_count(clean_para) >= min_words:
                detected = detector.detect_language_of(clean_para)
                if detected == english:
                    confidences = detector.compute_language_confidence_values(clean_para)
                    en_conf = next((c.value for c in confidences if c.language == english), 1.0)
                    if en_conf < 0.50 and first_line not in seen_lines:
                        seen_lines.add(first_line)
                        findings.append(Finding(
                            code="weak-english",
                            severity="warning",
                            file=rel_path,
                            line=first_line,
                            evidence=clean_para[:120].replace("\n", " "),
                            message="Paragraph detected as uncertain English (confidence < 0.50).",
                        ))

        # --- Pass 2: sentence-level within this paragraph ---
        sentences = _SENTENCE_SPLIT_RE.split(clean_para)
        for sent in sentences:
            sent = sent.strip()
            if _word_count(sent) < sent_min_words:
                continue
            result = _detect_chunk(sent, detector, english, sent_min_confidence)
            if result is not None and first_line not in seen_lines:
                lang_name, conf = result
                seen_lines.add(first_line)
                findings.append(Finding(
                    code="non-english-paragraph",
                    severity="error",
                    file=rel_path,
                    line=first_line,
                    evidence=sent[:120].replace("\n", " "),
                    message=f"Sentence detected as {lang_name} (confidence {conf:.2f}).",
                ))
                break  # One finding per paragraph is enough.

    return findings


# ---------------------------------------------------------------------------
# Tree-sitter source-code extraction
# ---------------------------------------------------------------------------

# Node types that carry human-readable text in each grammar.
_COMMENT_TYPES = {"comment", "line_comment", "block_comment", "doc_comment"}
_STRING_TYPES = {"string", "string_literal", "interpreted_string_literal",
                  "raw_string_literal", "template_string"}


def _walk_nodes(node, text_bytes: bytes, min_words: int) -> Iterator[tuple[str, int]]:
    """Yield (chunk_text, start_line_1indexed) for comment/string nodes."""
    if node.type in _COMMENT_TYPES or node.type in _STRING_TYPES:
        chunk = text_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="ignore")
        # Strip comment markers and quote chars.
        chunk = re.sub(r'^(#|//|/\*|\*+/?|"""|\'\'\')?\s*', "", chunk, flags=re.MULTILINE)
        chunk = chunk.strip("\"'`\n ")
        if _word_count(chunk) >= min_words:
            yield (chunk, node.start_point[0] + 1)  # 1-indexed line
    else:
        for child in node.children:
            yield from _walk_nodes(child, text_bytes, min_words)


def _lingua_findings_for_code(
    rel_path: str,
    text: str,
    suffix: str,
    min_words: int,
    min_confidence: float,
) -> list[Finding]:
    """Extract comments + string literals via tree-sitter, then run lingua."""
    lang_key = _suffix_to_ts_lang(suffix)
    if lang_key is None:
        return []

    parser = _get_ts_parser(lang_key)
    if parser is None:
        return []

    detector, english = _get_detector()
    text_bytes = text.encode("utf-8", errors="ignore")
    tree = parser.parse(text_bytes)
    lines = text.splitlines()

    sent_min_words = max(5, min_words // 2)
    sent_min_confidence = max(0.55, min_confidence - 0.20)

    findings: list[Finding] = []
    for chunk, line_no in _walk_nodes(tree.root_node, text_bytes, min_words):
        # Allow-marker check in surrounding source lines.
        window = _context_window(lines, line_no - 1, radius=3)
        if _has_allow_block_marker(window) or _has_allow_marker(window):
            continue

        # Chunk-level detection.
        result = _detect_chunk(chunk, detector, english, min_confidence)
        if result is not None:
            lang_name, conf = result
            findings.append(Finding(
                code="non-english-paragraph",
                severity="error",
                file=rel_path,
                line=line_no,
                evidence=chunk[:120].replace("\n", " "),
                message=f"Comment/string detected as {lang_name} (confidence {conf:.2f}).",
            ))
            continue

        # Sentence-level within long comments.
        sentences = _SENTENCE_SPLIT_RE.split(chunk)
        if len(sentences) > 1:
            for sent in sentences:
                sent = sent.strip()
                if _word_count(sent) < sent_min_words:
                    continue
                result = _detect_chunk(sent, detector, english, sent_min_confidence)
                if result is not None:
                    lang_name, conf = result
                    findings.append(Finding(
                        code="non-english-paragraph",
                        severity="error",
                        file=rel_path,
                        line=line_no,
                        evidence=sent[:120].replace("\n", " "),
                        message=f"Comment sentence detected as {lang_name} (confidence {conf:.2f}).",
                    ))
                    break

    return findings


# ---------------------------------------------------------------------------
# Per-file scanner
# ---------------------------------------------------------------------------

def scan_file(
    root: Path,
    rel_path: str,
    min_words: int = 15,
    min_confidence: float = 0.85,
) -> list[Finding]:
    path = root / rel_path
    if not is_probably_text(path):
        return []

    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []

    lines = text.splitlines()
    findings: list[Finding] = []

    # Fast pre-pass: non-Latin scripts and inverted punctuation (line-level).
    for line_no, line in enumerate(lines, 1):
        f = _fast_prepass_finding(rel_path, line_no, line)
        if f is not None:
            window = _context_window(lines, line_no - 1, radius=3)
            if not _has_allow_marker(window) and not _has_allow_block_marker(window):
                findings.append(f)

    suffix = path.suffix.lower()

    # Prose files: paragraph-level lingua detection.
    if suffix in PROSE_SUFFIXES:
        findings.extend(
            _lingua_findings_for_paragraphs(
                rel_path, text, lines,
                min_words=min_words,
                min_confidence=min_confidence,
            )
        )
    # Source files: tree-sitter comment/string extraction + lingua detection.
    elif suffix in CODE_SUFFIXES or _suffix_to_ts_lang(suffix) is not None:
        findings.extend(
            _lingua_findings_for_code(
                rel_path, text, suffix,
                min_words=min_words,
                min_confidence=min_confidence,
            )
        )

    return findings


# ---------------------------------------------------------------------------
# Top-level audit
# ---------------------------------------------------------------------------

def audit(
    root: Path,
    *,
    include_untracked: bool = False,
    exclude_globs: Sequence[str] = (),
    min_words: int = 15,
    min_confidence: float = 0.85,
) -> Report:
    root = root.resolve()
    all_excludes = tuple(DEFAULT_EXCLUDE_GLOBS) + tuple(exclude_globs)
    scanned_files = 0
    findings: list[Finding] = []
    for rel_path in discover_files(root, include_untracked=include_untracked):
        if excluded(rel_path, all_excludes):
            continue
        path = root / rel_path
        if not path.is_file() or not is_probably_text(path):
            continue
        scanned_files += 1
        findings.extend(
            scan_file(root, rel_path, min_words=min_words, min_confidence=min_confidence)
        )
    return Report(
        schema_version=SCHEMA_VERSION,
        root=str(root),
        scanned_files=scanned_files,
        finding_count=len(findings),
        findings=tuple(findings),
    )


# ---------------------------------------------------------------------------
# Smoke audit (fast keyword + script + punctuation; no lingua / no tree-sitter)
# ---------------------------------------------------------------------------

def smoke_scan_file(root: Path, rel_path: str) -> list[Finding]:
    """Per-line keyword + script + punctuation scan, no model load."""
    path = root / rel_path
    if not is_probably_text(path):
        return []
    findings: list[Finding] = []
    pattern = _get_smoke_pattern()
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            buffer: list[str] = []
            for raw in handle:
                buffer.append(raw.rstrip("\n"))
            for idx, line in enumerate(buffer):
                window = "\n".join(buffer[max(0, idx - 1): idx + 2])
                if any(m in window for m in ALLOW_MARKERS):
                    continue
                if (script := first_forbidden_script_letter(line)) is not None:
                    findings.append(Finding(
                        code="non-english-script", severity="error",
                        file=rel_path, line=idx + 1, evidence=script,
                        message="Non-Latin script character.",
                    ))
                    continue
                if (m := pattern.search(line)) is not None:
                    findings.append(Finding(
                        code="non-english-term", severity="error",
                        file=rel_path, line=idx + 1, evidence=m.group(0),
                        message="Non-English keyword (smoke blocklist).",
                    ))
                    continue
                if (p := FORBIDDEN_PUNCTUATION_RE.search(line)) is not None:
                    findings.append(Finding(
                        code="non-english-punctuation", severity="error",
                        file=rel_path, line=idx + 1, evidence=p.group(0),
                        message="Inverted exclamation/question punctuation.",
                    ))
    except OSError:
        return []
    return findings


def smoke_audit(
    root: Path,
    *,
    include_untracked: bool = False,
    exclude_globs: Sequence[str] = (),
) -> Report:
    """Fast pre-commit pass. No lingua, no tree-sitter — keyword blocklist only.

    This is intentionally narrow: it catches obvious Spanish keywords from a
    fixed corpus and forbidden Spanish punctuation. Misses mixed-language
    drift that the lingua-based audit() catches. Use `audit()` in CI as the
    authoritative gate.
    """
    root = root.resolve()
    all_excludes = tuple(DEFAULT_EXCLUDE_GLOBS) + tuple(exclude_globs)
    scanned_files = 0
    findings: list[Finding] = []
    for rel_path in discover_files(root, include_untracked=include_untracked):
        if excluded(rel_path, all_excludes):
            continue
        path = root / rel_path
        if not path.is_file() or not is_probably_text(path):
            continue
        scanned_files += 1
        findings.extend(smoke_scan_file(root, rel_path))
    return Report(
        schema_version=SCHEMA_VERSION + "+smoke",
        root=str(root),
        scanned_files=scanned_files,
        finding_count=len(findings),
        findings=tuple(findings),
    )


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def report_to_markdown(report: Report) -> str:
    lines = [
        "# English-only Content Audit",
        "",
        f"Schema: `{report.schema_version}`",
        f"Root: `{report.root}`",
        f"Scanned files: **{report.scanned_files}**",
        f"Findings: **{report.finding_count}**",
        "",
    ]
    if not report.findings:
        lines.append("No non-English-language signals found.")
        return "\n".join(lines) + "\n"

    lines.extend([
        "| Severity | Code | Location | Evidence |",
        "|---|---|---|---|",
    ])
    for finding in report.findings:
        evidence = finding.evidence.replace("|", "\\|")
        lines.append(
            f"| {finding.severity} | {finding.code} | `{finding.file}:{finding.line}` | `{evidence}` |"
        )
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit repository text for English-only content (v2: lingua + tree-sitter)."
    )
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown")
    parser.add_argument("--include-untracked", action="store_true", help="Also scan untracked files")
    parser.add_argument("--exclude-glob", action="append", default=[], help="Additional glob to exclude")
    parser.add_argument("--no-fail", action="store_true", help="Always exit 0 after reporting")
    parser.add_argument(
        "--min-words", type=int, default=15,
        help="Minimum word count for a paragraph/chunk to be detected (default: 15)",
    )
    parser.add_argument(
        "--min-confidence", type=float, default=0.85,
        help="Minimum lingua confidence to emit a finding (default: 0.85)",
    )
    parser.add_argument(
        "--smoke", action="store_true",
        help=(
            "Fast keyword-blocklist pass (no lingua / no tree-sitter). "
            "Suitable for pre-commit; NOT a substitute for the lingua audit in CI."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.smoke:
        report = smoke_audit(
            Path(args.root),
            include_untracked=args.include_untracked,
            exclude_globs=args.exclude_glob,
        )
    else:
        report = audit(
            Path(args.root),
            include_untracked=args.include_untracked,
            exclude_globs=args.exclude_glob,
            min_words=args.min_words,
            min_confidence=args.min_confidence,
        )
    if args.json:
        payload = asdict(report)
        payload["findings"] = [asdict(f) for f in report.findings]
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(report_to_markdown(report), end="")

    if args.no_fail:
        return 0
    return 1 if report.findings else 0


if __name__ == "__main__":
    raise SystemExit(main())

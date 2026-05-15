# SCOPE: both
"""Smart Reader — Auto-pagination for large file reads.

Provides intelligent file reading that handles files exceeding the Read tool's
~10K token limit. Estimates file size, auto-paginates with head+tail strategy,
finds specific sections by header pattern, and yields chunks for streaming.

Usage:
    from lib.smart_reader import SmartReader, SmartReaderConfig

    reader = SmartReader()
    content = reader.read_file("path/to/large_file.py")
    summary = reader.file_summary("path/to/large_file.py")

    # Targeted section read
    content = reader.read_file("path/to/file.py", target_section="class SmartReader")

    # Chunked iteration
    for chunk in reader.read_chunked("path/to/file.py"):
        process(chunk)

Python 3.9+ compatible. No external dependencies. Author: luum.
"""

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Iterator, List, Optional, Tuple


# Characters per token estimate (conservative — most tokenizers average 3.5-4.5)
_CHARS_PER_TOKEN = 4

# Binary file signatures (first bytes)
_BINARY_SIGNATURES = [
    b"\x89PNG",       # PNG
    b"\xff\xd8\xff",  # JPEG
    b"GIF8",          # GIF
    b"PK",            # ZIP/DOCX/XLSX
    b"\x7fELF",       # ELF binary
    b"\xfe\xed\xfa",  # Mach-O
    b"\xcf\xfa\xed",  # Mach-O (reversed)
    b"\x00\x00\x01",  # Various binary formats
    b"\x1f\x8b",      # gzip
]

# File extensions considered binary
_BINARY_EXTENSIONS = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp", ".svg",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
    ".exe", ".dll", ".so", ".dylib", ".o", ".a",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".mp3", ".mp4", ".avi", ".mov", ".mkv", ".wav", ".flac",
    ".pyc", ".pyo", ".class", ".jar",
    ".sqlite", ".db",
})

# Section header patterns for common file types
_SECTION_PATTERNS: Dict[str, List[str]] = {
    ".md": [
        r"^#{1,6}\s+",                  # Markdown headers
    ],
    ".py": [
        r"^class\s+\w+",               # Python class
        r"^def\s+\w+",                  # Python top-level function
        r"^async\s+def\s+\w+",         # Python async function
    ],
    ".go": [
        r"^func\s+",                    # Go function
        r"^type\s+\w+\s+(struct|interface)",  # Go type
    ],
    ".ts": [
        r"^export\s+(class|interface|function|const|type)\s+",
        r"^(class|interface|function)\s+",
    ],
    ".js": [
        r"^export\s+(class|function|const)\s+",
        r"^(class|function)\s+",
    ],
    ".sh": [
        r"^[a-zA-Z_]\w*\(\)\s*\{",     # Shell function
        r"^# ---",                       # Section divider
    ],
    ".yaml": [
        r"^\w+:",                        # Top-level YAML key
    ],
    ".yml": [
        r"^\w+:",                        # Top-level YAML key
    ],
}


@dataclass
class SmartReaderConfig:
    """Configuration for smart file reading."""

    max_tokens: int = 8000
    overlap_lines: int = 10
    head_ratio: float = 0.6       # Fraction of budget for head (rest for tail)
    context_lines: int = 20       # Lines of context around a target section
    chunk_tokens: int = 5000      # Default chunk size for read_chunked
    index_path: str = ".cognitive-os/large-files-index.json"
    metrics_path: str = ".cognitive-os/metrics/large-file-reads.jsonl"


@dataclass
class FileSummary:
    """Metadata about a file."""

    path: str
    size_bytes: int
    line_count: int
    estimated_tokens: int
    is_binary: bool
    extension: str
    sections: List[Dict[str, int | str]] = field(default_factory=list)
    exceeds_limit: bool = False

    def to_dict(self) -> Dict:
        return {
            "path": self.path,
            "size_bytes": self.size_bytes,
            "line_count": self.line_count,
            "estimated_tokens": self.estimated_tokens,
            "is_binary": self.is_binary,
            "extension": self.extension,
            "sections": self.sections,
            "exceeds_limit": self.exceeds_limit,
        }


@dataclass
class ReadResult:
    """Result of a smart file read."""

    content: str
    truncated: bool
    total_lines: int
    lines_read: int
    start_line: int
    end_line: int
    strategy: str            # "full", "head_tail", "section", "chunked"
    estimated_tokens: int
    notice: str = ""

    def to_dict(self) -> Dict:
        return {
            "truncated": self.truncated,
            "total_lines": self.total_lines,
            "lines_read": self.lines_read,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "strategy": self.strategy,
            "estimated_tokens": self.estimated_tokens,
            "notice": self.notice,
        }


class SmartReader:
    """Intelligent file reader with auto-pagination for large files.

    Handles files that exceed the Read tool's ~10K token limit by:
    1. Checking file size first
    2. Reading normally if under limit
    3. Finding specific sections if target_section is provided
    4. Falling back to head+tail truncation with a notice
    """

    def __init__(
        self,
        config: Optional[SmartReaderConfig] = None,
        project_dir: Optional[str] = None,
    ):
        self.config = config or SmartReaderConfig()
        self.project_dir = project_dir or os.getcwd()

    def read_file(
        self,
        path: str,
        target_section: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> ReadResult:
        """Read a file, auto-paginating if too large.

        Args:
            path: File path (absolute or relative to project_dir).
            target_section: Optional pattern to find a specific section.
            max_tokens: Override the default max_tokens for this read.

        Returns:
            ReadResult with content and metadata.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file is binary.
        """
        abs_path = self._resolve_path(path)

        if not os.path.isfile(abs_path):
            raise FileNotFoundError(f"File not found: {abs_path}")

        if self._is_binary(abs_path):
            raise ValueError(
                f"Binary file cannot be read as text: {abs_path}"
            )

        limit = max_tokens or self.config.max_tokens
        est_tokens = self.estimate_tokens(abs_path)

        # Under limit: read full file
        if est_tokens <= limit:
            return self._read_full(abs_path)

        # Target section: find and read just that section
        if target_section:
            result = self._read_section(abs_path, target_section, limit)
            if result is not None:
                self._log_read(abs_path, result)
                return result

        # Over limit: head + tail with truncation notice
        result = self._read_head_tail(abs_path, limit)
        self._log_read(abs_path, result)
        return result

    def estimate_tokens(self, path: str) -> int:
        """Estimate token count for a file (~4 chars per token).

        Args:
            path: File path (absolute or relative).

        Returns:
            Estimated token count (0 for empty or missing files).
        """
        abs_path = self._resolve_path(path)
        try:
            size = os.path.getsize(abs_path)
            if size == 0:
                return 0
            return max(1, size // _CHARS_PER_TOKEN)
        except OSError:
            return 0

    def find_section(
        self,
        path: str,
        pattern: str,
    ) -> Optional[Tuple[int, int]]:
        """Find line range matching a section header pattern.

        Searches for the pattern and returns the range from the matching
        line to the next section header (or end of file).

        Args:
            path: File path.
            pattern: Regex pattern or plain text to search for.

        Returns:
            (start_line, end_line) 0-indexed, or None if not found.
        """
        abs_path = self._resolve_path(path)

        try:
            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except OSError:
            return None

        ext = os.path.splitext(abs_path)[1].lower()
        section_patterns = _SECTION_PATTERNS.get(ext, [])

        # Find the target line
        target_line = None
        compiled: re.Pattern[str] | None = None
        try:
            compiled = re.compile(pattern)
            use_regex = True
        except re.error:
            use_regex = False

        for i, line in enumerate(lines):
            if use_regex and compiled is not None:
                if compiled.search(line):
                    target_line = i
                    break
            else:
                if pattern in line:
                    target_line = i
                    break

        if target_line is None:
            return None

        # Find the end of this section (next section header or EOF)
        end_line = len(lines)
        if section_patterns:
            combined = "|".join(f"(?:{p})" for p in section_patterns)
            section_re = re.compile(combined)
            for i in range(target_line + 1, len(lines)):
                if section_re.match(lines[i]):
                    end_line = i
                    break

        return (target_line, end_line)

    def read_chunked(
        self,
        path: str,
        chunk_tokens: Optional[int] = None,
    ) -> Iterator[str]:
        """Yield file in chunks for streaming processing.

        Chunks overlap by config.overlap_lines to maintain context.
        Each chunk is approximately chunk_tokens in size.

        Args:
            path: File path.
            chunk_tokens: Override default chunk size.

        Yields:
            String chunks of the file content.
        """
        abs_path = self._resolve_path(path)
        tokens_per_chunk = chunk_tokens or self.config.chunk_tokens
        chars_per_chunk = tokens_per_chunk * _CHARS_PER_TOKEN
        overlap = self.config.overlap_lines

        try:
            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except OSError:
            return

        if not lines:
            return

        start = 0
        total = len(lines)

        while start < total:
            # Calculate how many lines fit in this chunk
            char_count = 0
            end = start
            while end < total and char_count < chars_per_chunk:
                char_count += len(lines[end])
                end += 1

            # Yield the chunk
            chunk_lines = lines[start:end]
            yield "".join(chunk_lines)

            # Advance with overlap
            if end >= total:
                break
            start = max(start + 1, end - overlap)

    def file_summary(self, path: str) -> FileSummary:
        """Return file metadata: size, lines, estimated tokens, sections.

        Args:
            path: File path.

        Returns:
            FileSummary with file metadata.
        """
        abs_path = self._resolve_path(path)

        try:
            size = os.path.getsize(abs_path)
        except OSError:
            size = 0

        is_binary = self._is_binary(abs_path)
        ext = os.path.splitext(abs_path)[1].lower()
        est_tokens = max(1, size // _CHARS_PER_TOKEN) if size > 0 else 0

        line_count = 0
        sections: List[Dict[str, int | str]] = []

        if not is_binary:
            try:
                with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
                line_count = len(lines)

                # Detect sections
                section_pats = _SECTION_PATTERNS.get(ext, [])
                if section_pats:
                    combined = "|".join(f"(?:{p})" for p in section_pats)
                    section_re = re.compile(combined)
                    for i, line in enumerate(lines):
                        if section_re.match(line):
                            sections.append({
                                "line": i + 1,
                                "text": line.strip()[:80],
                            })
            except OSError:
                pass

        return FileSummary(
            path=path,
            size_bytes=size,
            line_count=line_count,
            estimated_tokens=est_tokens,
            is_binary=is_binary,
            extension=ext,
            sections=sections,
            exceeds_limit=est_tokens > self.config.max_tokens,
        )

    def build_large_files_index(
        self,
        root_dir: Optional[str] = None,
        threshold_bytes: int = 40000,
    ) -> List[Dict]:
        """Scan project for files exceeding threshold and build an index.

        Args:
            root_dir: Directory to scan (defaults to project_dir).
            threshold_bytes: Minimum file size to include (default 40KB).

        Returns:
            List of file metadata dicts.
        """
        scan_dir = root_dir or self.project_dir
        skip_dirs = {".git", ".venv", "node_modules", "__pycache__", ".cognitive-os"}
        text_extensions = {
            ".py", ".go", ".ts", ".js", ".tsx", ".jsx",
            ".md", ".yaml", ".yml", ".json", ".toml",
            ".sh", ".bash", ".zsh",
            ".html", ".css", ".sql",
            ".java", ".kt", ".rs", ".rb", ".php",
            ".c", ".cpp", ".h", ".hpp",
        }

        large_files: List[Dict] = []

        for dirpath, dirnames, filenames in os.walk(scan_dir):
            # Skip excluded directories in-place
            dirnames[:] = [
                d for d in dirnames
                if d not in skip_dirs and not d.startswith(".")
            ]

            for filename in filenames:
                ext = os.path.splitext(filename)[1].lower()
                if ext not in text_extensions:
                    continue

                filepath = os.path.join(dirpath, filename)
                try:
                    size = os.path.getsize(filepath)
                except OSError:
                    continue

                if size >= threshold_bytes:
                    rel_path = os.path.relpath(filepath, scan_dir)
                    line_count = 0
                    try:
                        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                            line_count = sum(1 for _ in f)
                    except OSError:
                        pass

                    large_files.append({
                        "path": rel_path,
                        "bytes": size,
                        "lines": line_count,
                        "est_tokens": max(1, size // _CHARS_PER_TOKEN),
                    })

        # Sort by size descending
        large_files.sort(key=lambda x: x["bytes"], reverse=True)
        return large_files

    def save_large_files_index(
        self,
        root_dir: Optional[str] = None,
        threshold_bytes: int = 40000,
    ) -> str:
        """Build and save the large files index to disk.

        Args:
            root_dir: Directory to scan.
            threshold_bytes: Minimum file size.

        Returns:
            Path to the saved index file.
        """
        index = self.build_large_files_index(root_dir, threshold_bytes)
        index_path = os.path.join(self.project_dir, self.config.index_path)

        try:
            os.makedirs(os.path.dirname(index_path), exist_ok=True)
            with open(index_path, "w") as f:
                json.dump({
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "threshold_bytes": threshold_bytes,
                    "count": len(index),
                    "files": index,
                }, f, indent=2)
        except OSError:
            pass

        return index_path

    # ─── Private helpers ─────────────────────────────────────────────────

    def _resolve_path(self, path: str) -> str:
        """Resolve a path to absolute."""
        if os.path.isabs(path):
            return path
        return os.path.join(self.project_dir, path)

    def _is_binary(self, abs_path: str) -> bool:
        """Check if a file is binary by extension and magic bytes."""
        ext = os.path.splitext(abs_path)[1].lower()
        if ext in _BINARY_EXTENSIONS:
            return True

        try:
            with open(abs_path, "rb") as f:
                header = f.read(16)
            for sig in _BINARY_SIGNATURES:
                if header.startswith(sig):
                    return True
            # Check for null bytes in first 8KB (common binary indicator)
            with open(abs_path, "rb") as f:
                chunk = f.read(8192)
            if b"\x00" in chunk:
                return True
        except OSError:
            return False

        return False

    def _read_full(self, abs_path: str) -> ReadResult:
        """Read entire file (under limit)."""
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        lines = content.splitlines()
        return ReadResult(
            content=content,
            truncated=False,
            total_lines=len(lines),
            lines_read=len(lines),
            start_line=1,
            end_line=len(lines),
            strategy="full",
            estimated_tokens=max(1, len(content) // _CHARS_PER_TOKEN),
        )

    def _read_head_tail(self, abs_path: str, max_tokens: int) -> ReadResult:
        """Read head + tail of file with truncation notice."""
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        total_lines = len(lines)
        max_chars = max_tokens * _CHARS_PER_TOKEN
        head_chars = int(max_chars * self.config.head_ratio)
        tail_chars = max_chars - head_chars

        # Collect head lines
        head_lines: List[str] = []
        head_char_count = 0
        for line in lines:
            if head_char_count + len(line) > head_chars:
                break
            head_lines.append(line)
            head_char_count += len(line)

        # Collect tail lines (from end)
        tail_lines: List[str] = []
        tail_char_count = 0
        for line in reversed(lines):
            if tail_char_count + len(line) > tail_chars:
                break
            tail_lines.insert(0, line)
            tail_char_count += len(line)

        # Ensure no overlap between head and tail
        head_end = len(head_lines)
        tail_start = total_lines - len(tail_lines)
        if head_end >= tail_start:
            # Overlap: just return head portion up to limit
            all_chars = 0
            trimmed: List[str] = []
            for line in lines:
                if all_chars + len(line) > max_chars:
                    break
                trimmed.append(line)
                all_chars += len(line)
            content = "".join(trimmed)
            notice = (
                f"[TRUNCATED: File has {total_lines} lines, showing first "
                f"{len(trimmed)} lines ({all_chars} chars). Use offset+limit "
                f"or target_section for specific content.]"
            )
            return ReadResult(
                content=content + "\n" + notice,
                truncated=True,
                total_lines=total_lines,
                lines_read=len(trimmed),
                start_line=1,
                end_line=len(trimmed),
                strategy="head_tail",
                estimated_tokens=max(1, (all_chars + len(notice)) // _CHARS_PER_TOKEN),
                notice=notice,
            )

        skipped = tail_start - head_end
        head_content = "".join(head_lines)
        tail_content = "".join(tail_lines)
        notice = (
            f"[TRUNCATED: File has {total_lines} lines. Showing lines 1-{head_end} "
            f"and {tail_start + 1}-{total_lines} ({skipped} lines omitted). "
            f"Use offset+limit or target_section for specific content.]"
        )

        content = head_content + "\n" + notice + "\n" + tail_content

        return ReadResult(
            content=content,
            truncated=True,
            total_lines=total_lines,
            lines_read=len(head_lines) + len(tail_lines),
            start_line=1,
            end_line=total_lines,
            strategy="head_tail",
            estimated_tokens=max(1, len(content) // _CHARS_PER_TOKEN),
            notice=notice,
        )

    def _read_section(
        self,
        abs_path: str,
        target_section: str,
        max_tokens: int,
    ) -> Optional[ReadResult]:
        """Read a specific section of the file with surrounding context."""
        result = self.find_section(abs_path, target_section)
        if result is None:
            return None

        start, end = result
        ctx = self.config.context_lines

        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        total_lines = len(lines)
        read_start = max(0, start - ctx)
        read_end = min(total_lines, end + ctx)

        # Enforce token limit
        max_chars = max_tokens * _CHARS_PER_TOKEN
        selected: List[str] = []
        char_count = 0
        for line in lines[read_start:read_end]:
            if char_count + len(line) > max_chars:
                break
            selected.append(line)
            char_count += len(line)

        actual_end = read_start + len(selected)
        content = "".join(selected)
        notice = (
            f"[Section read: lines {read_start + 1}-{actual_end} of {total_lines} "
            f"(matched '{target_section}' at line {start + 1})]"
        )

        return ReadResult(
            content=notice + "\n" + content,
            truncated=actual_end < total_lines or read_start > 0,
            total_lines=total_lines,
            lines_read=len(selected),
            start_line=read_start + 1,
            end_line=actual_end,
            strategy="section",
            estimated_tokens=max(1, (len(content) + len(notice)) // _CHARS_PER_TOKEN),
            notice=notice,
        )

    def _log_read(self, abs_path: str, result: ReadResult) -> None:
        """Log a large file read event to metrics."""
        metrics_path = os.path.join(self.project_dir, self.config.metrics_path)
        try:
            os.makedirs(os.path.dirname(metrics_path), exist_ok=True)
            entry = json.dumps({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "path": os.path.relpath(abs_path, self.project_dir),
                "total_lines": result.total_lines,
                "lines_read": result.lines_read,
                "strategy": result.strategy,
                "truncated": result.truncated,
                "estimated_tokens": result.estimated_tokens,
            })
            with open(metrics_path, "a") as f:
                f.write(entry + "\n")
        except OSError:
            pass  # Best effort — never crash on metrics failure


def format_file_advisory(summary: FileSummary) -> str:
    """Format a human-readable advisory message for a large file.

    Args:
        summary: FileSummary from SmartReader.file_summary().

    Returns:
        Advisory string, or empty string if file is within limits.
    """
    if not summary.exceeds_limit:
        return ""

    lines = [
        f"LARGE FILE ADVISORY: {summary.path}",
        f"  Size: {summary.size_bytes:,} bytes ({summary.line_count} lines, "
        f"~{summary.estimated_tokens:,} tokens)",
        f"  This file exceeds the ~10K token read limit.",
        f"  Recommendations:",
        f"    - Use offset+limit to read specific line ranges",
        f"    - Use SmartReader.read_file(path, target_section='...') for sections",
    ]
    if summary.sections:
        lines.append(f"  Sections found ({len(summary.sections)}):")
        for sec in summary.sections[:10]:
            lines.append(f"    Line {sec['line']}: {sec['text']}")
        if len(summary.sections) > 10:
            lines.append(f"    ... and {len(summary.sections) - 10} more")

    return "\n".join(lines)

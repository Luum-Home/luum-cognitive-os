"""Unit tests for lib/smart_reader.py — SmartReader auto-pagination."""

import json
import os
import sys
import tempfile
import shutil

import pytest

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from lib.smart_reader import (
    SmartReader,
    SmartReaderConfig,
    FileSummary,
    format_file_advisory,
    _CHARS_PER_TOKEN,
)


@pytest.fixture
def tmp_dir():
    """Create a temporary directory for test files."""
    d = tempfile.mkdtemp(prefix="smart_reader_test_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def reader(tmp_dir):
    """Create a SmartReader with a temp project directory."""
    config = SmartReaderConfig(
        max_tokens=500,  # Low limit for testing (~2000 chars)
        overlap_lines=3,
        chunk_tokens=200,
        index_path=os.path.join(tmp_dir, ".cognitive-os", "large-files-index.json"),
        metrics_path=os.path.join(tmp_dir, ".cognitive-os", "metrics", "large-file-reads.jsonl"),
    )
    return SmartReader(config=config, project_dir=tmp_dir)


def _write_file(directory: str, name: str, content: str) -> str:
    """Helper to write a test file."""
    path = os.path.join(directory, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    return path


# ─── test_small_file_reads_normally ──────────────────────────────────────────


class TestSmallFileReadsNormally:
    """File under limit returns full content without truncation."""

    def test_full_content_returned(self, tmp_dir, reader):
        content = "line 1\nline 2\nline 3\n"
        path = _write_file(tmp_dir, "small.py", content)
        result = reader.read_file(path)

        assert result.content == content
        assert result.truncated is False
        assert result.strategy == "full"
        assert result.total_lines == 3
        assert result.lines_read == 3

    def test_empty_file(self, tmp_dir, reader):
        path = _write_file(tmp_dir, "empty.py", "")
        result = reader.read_file(path)

        assert result.content == ""
        assert result.truncated is False
        assert result.strategy == "full"
        assert result.total_lines == 0

    def test_single_line_file(self, tmp_dir, reader):
        path = _write_file(tmp_dir, "one.py", "hello world\n")
        result = reader.read_file(path)

        assert "hello world" in result.content
        assert result.truncated is False


# ─── test_large_file_auto_paginates ──────────────────────────────────────────


class TestLargeFileAutoPaginates:
    """File over limit returns head+tail with truncation notice."""

    def test_head_tail_truncation(self, tmp_dir, reader):
        # Create a file larger than 500 tokens (~2000 chars)
        lines = [f"line {i}: {'x' * 50}\n" for i in range(100)]
        content = "".join(lines)
        path = _write_file(tmp_dir, "large.py", content)

        result = reader.read_file(path)

        assert result.truncated is True
        assert result.strategy == "head_tail"
        assert result.total_lines == 100
        assert result.lines_read < 100
        assert "TRUNCATED" in result.notice

    def test_truncation_preserves_head(self, tmp_dir, reader):
        lines = [f"line {i}: content here\n" for i in range(200)]
        path = _write_file(tmp_dir, "big.py", "".join(lines))

        result = reader.read_file(path)

        # Head should start with line 0
        assert "line 0:" in result.content

    def test_truncation_preserves_tail(self, tmp_dir, reader):
        lines = [f"line {i}: content here\n" for i in range(200)]
        path = _write_file(tmp_dir, "big.py", "".join(lines))

        result = reader.read_file(path)

        # Tail should include the last line
        assert "line 199:" in result.content

    def test_truncation_notice_includes_line_count(self, tmp_dir, reader):
        lines = [f"line {i}: {'a' * 40}\n" for i in range(150)]
        path = _write_file(tmp_dir, "big.py", "".join(lines))

        result = reader.read_file(path)

        assert "150 lines" in result.notice


# ─── test_estimate_tokens_accuracy ───────────────────────────────────────────


class TestEstimateTokensAccuracy:
    """Token estimation is within 20% of actual for typical text."""

    def test_known_size_file(self, tmp_dir, reader):
        # 4000 chars = ~1000 tokens
        content = "a" * 4000
        path = _write_file(tmp_dir, "known.py", content)

        est = reader.estimate_tokens(path)
        expected = 4000 // _CHARS_PER_TOKEN  # 1000

        assert est == expected

    def test_empty_file_zero_tokens(self, tmp_dir, reader):
        path = _write_file(tmp_dir, "empty.py", "")
        est = reader.estimate_tokens(path)
        assert est == 0

    def test_nonexistent_file(self, tmp_dir, reader):
        est = reader.estimate_tokens(os.path.join(tmp_dir, "nope.py"))
        assert est == 0

    def test_estimation_proportional_to_size(self, tmp_dir, reader):
        small = _write_file(tmp_dir, "small.py", "a" * 100)
        big = _write_file(tmp_dir, "big.py", "a" * 1000)

        est_small = reader.estimate_tokens(small)
        est_big = reader.estimate_tokens(big)

        assert est_big > est_small
        # Should be roughly 10x
        ratio = est_big / est_small
        assert 8 <= ratio <= 12


# ─── test_find_section_by_header ─────────────────────────────────────────────


class TestFindSectionByHeader:
    """Finds markdown sections correctly."""

    def test_markdown_h2_header(self, tmp_dir, reader):
        content = "# Title\n\nIntro text.\n\n## Section A\n\nContent A.\n\n## Section B\n\nContent B.\n"
        path = _write_file(tmp_dir, "doc.md", content)

        result = reader.find_section(path, "## Section A")

        assert result is not None
        start, end = result
        assert start == 4  # line index of "## Section A"
        assert end == 8     # line index of "## Section B"

    def test_markdown_section_to_end(self, tmp_dir, reader):
        content = "# Title\n\n## Last Section\n\nFinal content.\n"
        path = _write_file(tmp_dir, "doc.md", content)

        result = reader.find_section(path, "## Last Section")

        assert result is not None
        start, end = result
        assert start == 2
        assert end == 5  # end of file

    def test_section_not_found(self, tmp_dir, reader):
        content = "# Title\n\n## Existing\n\nContent.\n"
        path = _write_file(tmp_dir, "doc.md", content)

        result = reader.find_section(path, "## Nonexistent")

        assert result is None


# ─── test_find_section_by_function ───────────────────────────────────────────


class TestFindSectionByFunction:
    """Finds Python/Go function definitions."""

    def test_python_class(self, tmp_dir, reader):
        content = "import os\n\nclass Foo:\n    pass\n\nclass Bar:\n    pass\n"
        path = _write_file(tmp_dir, "mod.py", content)

        result = reader.find_section(path, "class Foo")

        assert result is not None
        start, end = result
        assert start == 2  # "class Foo:"
        assert end == 5    # "class Bar:"

    def test_python_function(self, tmp_dir, reader):
        content = "def alpha():\n    pass\n\ndef beta():\n    pass\n"
        path = _write_file(tmp_dir, "funcs.py", content)

        result = reader.find_section(path, "def alpha")

        assert result is not None
        start, end = result
        assert start == 0
        assert end == 3

    def test_go_function(self, tmp_dir, reader):
        content = "package main\n\nfunc Foo() {\n}\n\nfunc Bar() {\n}\n"
        path = _write_file(tmp_dir, "main.go", content)

        result = reader.find_section(path, "func Foo")

        assert result is not None
        start, end = result
        assert start == 2
        assert end == 5


# ─── test_chunked_reading ────────────────────────────────────────────────────


class TestChunkedReading:
    """Chunks cover entire file without gaps."""

    def test_small_file_single_chunk(self, tmp_dir, reader):
        content = "line 1\nline 2\nline 3\n"
        path = _write_file(tmp_dir, "small.py", content)

        chunks = list(reader.read_chunked(path))

        assert len(chunks) == 1
        assert chunks[0] == content

    def test_large_file_multiple_chunks(self, tmp_dir, reader):
        lines = [f"line {i}: {'x' * 50}\n" for i in range(100)]
        content = "".join(lines)
        path = _write_file(tmp_dir, "large.py", content)

        chunks = list(reader.read_chunked(path))

        assert len(chunks) > 1

    def test_all_content_covered(self, tmp_dir, reader):
        lines = [f"line {i}\n" for i in range(50)]
        content = "".join(lines)
        path = _write_file(tmp_dir, "covered.py", content)

        chunks = list(reader.read_chunked(path))
        combined = "".join(chunks)

        # Every line should appear at least once (overlap may duplicate some)
        for i in range(50):
            assert f"line {i}\n" in combined

    def test_empty_file_no_chunks(self, tmp_dir, reader):
        path = _write_file(tmp_dir, "empty.py", "")
        chunks = list(reader.read_chunked(path))
        assert len(chunks) == 0


# ─── test_file_summary ───────────────────────────────────────────────────────


class TestFileSummary:
    """Returns correct metadata."""

    def test_basic_metadata(self, tmp_dir, reader):
        content = "line 1\nline 2\nline 3\n"
        path = _write_file(tmp_dir, "meta.py", content)

        summary = reader.file_summary(path)

        assert summary.path == path
        assert summary.size_bytes == len(content)
        assert summary.line_count == 3
        assert summary.is_binary is False
        assert summary.extension == ".py"

    def test_exceeds_limit_flag(self, tmp_dir, reader):
        # Under limit
        small = _write_file(tmp_dir, "small.py", "x" * 100)
        assert reader.file_summary(small).exceeds_limit is False

        # Over limit (500 tokens * 4 chars = 2000 chars)
        big = _write_file(tmp_dir, "big.py", "x" * 3000)
        assert reader.file_summary(big).exceeds_limit is True

    def test_python_sections_detected(self, tmp_dir, reader):
        content = "class Foo:\n    pass\n\ndef bar():\n    pass\n"
        path = _write_file(tmp_dir, "sections.py", content)

        summary = reader.file_summary(path)

        assert len(summary.sections) == 2
        assert "class Foo:" in summary.sections[0]["text"]
        assert "def bar():" in summary.sections[1]["text"]

    def test_markdown_sections_detected(self, tmp_dir, reader):
        content = "# Title\n\n## Section 1\n\nText.\n\n## Section 2\n\nMore.\n"
        path = _write_file(tmp_dir, "doc.md", content)

        summary = reader.file_summary(path)

        assert len(summary.sections) == 3  # title + 2 sections

    def test_to_dict(self, tmp_dir, reader):
        path = _write_file(tmp_dir, "dict.py", "hello\n")
        summary = reader.file_summary(path)
        d = summary.to_dict()

        assert "path" in d
        assert "size_bytes" in d
        assert "estimated_tokens" in d
        assert isinstance(d, dict)


# ─── test_target_section_read ────────────────────────────────────────────────


class TestTargetSectionRead:
    """Reads only the relevant section with context."""

    def test_section_found_and_read(self, tmp_dir, reader):
        # Must exceed 500 token limit (~2000 chars) to trigger section strategy
        lines = [f"# Section {i}\n\n{'Content ' * 20}{i}.\n\n" for i in range(30)]
        content = "".join(lines)
        path = _write_file(tmp_dir, "doc.md", content)

        result = reader.read_file(path, target_section="# Section 15")

        assert result.strategy == "section"
        assert "Section 15" in result.content

    def test_section_not_found_falls_back(self, tmp_dir, reader):
        lines = [f"line {i}: {'x' * 40}\n" for i in range(100)]
        path = _write_file(tmp_dir, "large.py", "".join(lines))

        # Target section doesn't exist, falls back to head_tail
        result = reader.read_file(path, target_section="nonexistent_section_xyz")

        assert result.strategy == "head_tail"
        assert result.truncated is True

    def test_section_includes_context(self, tmp_dir, reader):
        # Use a reader with generous context
        config = SmartReaderConfig(
            max_tokens=500,
            context_lines=5,
        )
        r = SmartReader(config=config, project_dir=tmp_dir)

        lines = ["before 1\n", "before 2\n", "before 3\n",
                 "before 4\n", "before 5\n", "before 6\n",
                 "def target():\n", "    pass\n",
                 "after 1\n", "after 2\n"]
        path = _write_file(tmp_dir, "ctx.py", "".join(lines))

        result = r.read_file(path, target_section="def target")

        assert "def target" in result.content
        # Should include some before context
        assert "before" in result.content


# ─── test_missing_file_error ─────────────────────────────────────────────────


class TestMissingFileError:
    """Proper error for nonexistent files."""

    def test_file_not_found(self, tmp_dir, reader):
        with pytest.raises(FileNotFoundError):
            reader.read_file(os.path.join(tmp_dir, "nonexistent.py"))


# ─── test_binary_file_skip ───────────────────────────────────────────────────


class TestBinaryFileSkip:
    """Does not try to read binary files."""

    def test_png_extension(self, tmp_dir, reader):
        path = _write_file(tmp_dir, "image.png", "fake png data")
        with pytest.raises(ValueError, match="Binary file"):
            reader.read_file(path)

    def test_binary_content(self, tmp_dir, reader):
        path = os.path.join(tmp_dir, "binary.dat")
        with open(path, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        with pytest.raises(ValueError, match="Binary file"):
            reader.read_file(path)

    def test_zip_extension(self, tmp_dir, reader):
        path = _write_file(tmp_dir, "archive.zip", "fake zip")
        with pytest.raises(ValueError, match="Binary file"):
            reader.read_file(path)


# ─── test_large_files_index ──────────────────────────────────────────────────


class TestLargeFilesIndex:
    """Index building and saving."""

    def test_build_index_finds_large_files(self, tmp_dir, reader):
        # Create files above and below threshold
        _write_file(tmp_dir, "small.py", "x" * 100)
        _write_file(tmp_dir, "big.py", "y" * 50000)

        index = reader.build_large_files_index(tmp_dir, threshold_bytes=40000)

        assert len(index) == 1
        assert index[0]["path"] == "big.py"
        assert index[0]["bytes"] == 50000

    def test_build_index_skips_venv(self, tmp_dir, reader):
        os.makedirs(os.path.join(tmp_dir, ".venv"), exist_ok=True)
        _write_file(tmp_dir, ".venv/big.py", "z" * 50000)
        _write_file(tmp_dir, "src/big.py", "z" * 50000)

        index = reader.build_large_files_index(tmp_dir, threshold_bytes=40000)

        paths = [f["path"] for f in index]
        assert all(".venv" not in p for p in paths)
        assert any("src" in p for p in paths)

    def test_save_index_creates_file(self, tmp_dir, reader):
        _write_file(tmp_dir, "big.py", "x" * 50000)

        index_path = reader.save_large_files_index(tmp_dir, threshold_bytes=40000)

        assert os.path.exists(index_path)
        with open(index_path) as f:
            data = json.load(f)
        assert data["count"] == 1
        assert len(data["files"]) == 1


# ─── test_format_file_advisory ───────────────────────────────────────────────


class TestFormatFileAdvisory:
    """Advisory message formatting."""

    def test_no_advisory_for_small_file(self):
        summary = FileSummary(
            path="small.py",
            size_bytes=100,
            line_count=5,
            estimated_tokens=25,
            is_binary=False,
            extension=".py",
            exceeds_limit=False,
        )
        assert format_file_advisory(summary) == ""

    def test_advisory_for_large_file(self):
        summary = FileSummary(
            path="big.py",
            size_bytes=50000,
            line_count=1200,
            estimated_tokens=12500,
            is_binary=False,
            extension=".py",
            exceeds_limit=True,
            sections=[{"line": 10, "text": "class BigHandler:"}],
        )
        advisory = format_file_advisory(summary)

        assert "LARGE FILE ADVISORY" in advisory
        assert "big.py" in advisory
        assert "50,000 bytes" in advisory
        assert "12,500 tokens" in advisory
        assert "class BigHandler:" in advisory


# ─── test_max_tokens_override ────────────────────────────────────────────────


class TestMaxTokensOverride:
    """Override max_tokens per read call."""

    def test_override_allows_larger_read(self, tmp_dir, reader):
        # Default limit is 500 tokens, create a 600-token file
        content = "a" * 2400  # 600 tokens
        path = _write_file(tmp_dir, "medium.py", content)

        # Default should truncate
        result_default = reader.read_file(path)
        assert result_default.truncated is True

        # Override with higher limit should read full
        result_override = reader.read_file(path, max_tokens=1000)
        assert result_override.truncated is False

    def test_override_with_lower_limit(self, tmp_dir, reader):
        content = "a" * 800  # 200 tokens
        path = _write_file(tmp_dir, "small.py", content)

        # Default 500 tokens should read fully
        result_default = reader.read_file(path)
        assert result_default.truncated is False

        # Override with very low limit
        result_override = reader.read_file(path, max_tokens=50)
        assert result_override.truncated is True


# ─── test_metrics_logging ────────────────────────────────────────────────────


class TestMetricsLogging:
    """Large file reads are logged to metrics."""

    def test_truncated_read_logged(self, tmp_dir, reader):
        lines = [f"line {i}: {'x' * 50}\n" for i in range(100)]
        path = _write_file(tmp_dir, "logged.py", "".join(lines))

        reader.read_file(path)

        metrics_path = os.path.join(
            tmp_dir, ".cognitive-os", "metrics", "large-file-reads.jsonl"
        )
        assert os.path.exists(metrics_path)
        with open(metrics_path) as f:
            entries = [json.loads(line) for line in f if line.strip()]
        assert len(entries) >= 1
        assert entries[0]["strategy"] == "head_tail"
        assert entries[0]["truncated"] is True

    def test_full_read_not_logged(self, tmp_dir, reader):
        path = _write_file(tmp_dir, "small.py", "hello\n")
        reader.read_file(path)

        metrics_path = os.path.join(
            tmp_dir, ".cognitive-os", "metrics", "large-file-reads.jsonl"
        )
        # Small file reads are not logged (no truncation)
        assert not os.path.exists(metrics_path)


# ─── test_read_result_to_dict ────────────────────────────────────────────────


class TestReadResultToDict:
    """ReadResult serialization."""

    def test_to_dict_fields(self, tmp_dir, reader):
        path = _write_file(tmp_dir, "x.py", "hello\n")
        result = reader.read_file(path)
        d = result.to_dict()

        assert "truncated" in d
        assert "total_lines" in d
        assert "strategy" in d
        assert "estimated_tokens" in d
        assert isinstance(d["truncated"], bool)


# ─── test_relative_path_resolution ───────────────────────────────────────────


class TestRelativePathResolution:
    """Relative paths resolved against project_dir."""

    def test_relative_path(self, tmp_dir, reader):
        _write_file(tmp_dir, "sub/file.py", "content\n")

        result = reader.read_file("sub/file.py")

        assert result.content == "content\n"
        assert result.truncated is False

    def test_absolute_path(self, tmp_dir, reader):
        path = _write_file(tmp_dir, "abs.py", "data\n")

        result = reader.read_file(path)

        assert result.content == "data\n"

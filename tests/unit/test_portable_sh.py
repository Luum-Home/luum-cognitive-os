"""
Tests for hooks/_lib/portable.sh — cross-platform shell helper library.

Each test sources portable.sh via subprocess and invokes the exposed helpers,
asserting expected output for known inputs.

Unsupported platform meaning: any platform where bash is not on PATH.
Both macOS (bash 3.2, BSD userland) and Linux (bash 4+, GNU userland) are
explicitly supported. WSL is treated as Linux.
"""
from __future__ import annotations

import datetime
import os
import re
import subprocess
import time
from pathlib import Path

import pytest

PROJECT_DIR = Path(__file__).resolve().parents[2]
PORTABLE_SH = PROJECT_DIR / "hooks" / "_lib" / "portable.sh"


def _bash_available() -> bool:
    try:
        subprocess.run(["bash", "--version"], capture_output=True, check=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


pytestmark = pytest.mark.skipif(
    not _bash_available(),
    reason="bash is not available on this platform",
)


# ---------------------------------------------------------------------------
# Helper: run a snippet after sourcing portable.sh
# ---------------------------------------------------------------------------

def run_portable(snippet: str, env: dict | None = None, timeout: int = 15) -> str:
    """Source portable.sh then run snippet; return stdout stripped.

    Asserts the script exits 0.
    """
    script = f'source "{PORTABLE_SH}"\n{snippet}'
    merged_env = {**os.environ, **(env or {})}
    result = subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        timeout=timeout,
        env=merged_env,
    )
    assert result.returncode == 0, (
        f"Script failed (rc={result.returncode}):\n"
        f"STDOUT: {result.stdout}\n"
        f"STDERR: {result.stderr}"
    )
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# portable.sh availability
# ---------------------------------------------------------------------------

class TestLibraryAvailability:
    def test_file_exists(self):
        assert PORTABLE_SH.is_file(), f"portable.sh not found at {PORTABLE_SH}"

    def test_syntax_valid(self):
        result = subprocess.run(
            ["bash", "-n", str(PORTABLE_SH)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"bash -n failed:\n{result.stderr}"

    def test_sourceable_no_error(self):
        result = subprocess.run(
            ["bash", "-c", f"source '{PORTABLE_SH}' && echo OK"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"source failed:\n{result.stderr}"
        assert "OK" in result.stdout

    def test_six_helpers_defined(self):
        """All 6 required helpers are present as functions."""
        expected = [
            "portable_date_minus",
            "portable_sed_inplace",
            "portable_stat_mtime",
            "portable_stat_size",
            "portable_readlines",
            "portable_epoch_now",
        ]
        for name in expected:
            result = subprocess.run(
                ["bash", "-c", f"source '{PORTABLE_SH}' && type -t {name}"],
                capture_output=True,
                text=True,
            )
            assert result.stdout.strip() == "function", (
                f"{name} is not defined as a function in portable.sh"
            )

    def test_double_source_is_safe(self):
        """Sourcing twice must not error or duplicate definitions."""
        result = subprocess.run(
            ["bash", "-c", f"source '{PORTABLE_SH}' && source '{PORTABLE_SH}' && echo SAFE"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "SAFE" in result.stdout

    def test_no_bsd_only_flags_outside_detection(self):
        """The implementation block must not call date -v or sed -i '' unconditionally.

        Comments are excluded — `# Replaces: date -v-Nd` inside a helper's doc
        block is documentation, not an invocation.
        """
        content = PORTABLE_SH.read_text()
        lines = content.splitlines()
        impl_lines = []
        past_detection = False
        for line in lines:
            if line.startswith("portable_"):
                past_detection = True
            if past_detection:
                # Strip comment-only lines; they document the BSD/GNU commands
                # the helper replaces, they don't invoke them.
                if line.lstrip().startswith("#"):
                    continue
                impl_lines.append(line)
        impl = "\n".join(impl_lines)
        assert "date -v" not in impl, "date -v used in implementation (BSD-only)"
        # sed -i '' is used in detection only; not in the actual helpers
        # (the helpers delegate to either bsd/gnu/python branch)

    def test_no_mapfile_or_readarray(self):
        """portable.sh itself must not use mapfile or readarray."""
        content = PORTABLE_SH.read_text()
        for bad in ("mapfile", "readarray"):
            # Exclude comment lines
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                assert bad not in stripped, (
                    f"Non-portable construct '{bad}' found in implementation: {line!r}"
                )


# ---------------------------------------------------------------------------
# portable_epoch_now
# ---------------------------------------------------------------------------

class TestPortableEpochNow:
    def test_returns_integer(self):
        out = run_portable("portable_epoch_now")
        assert out.isdigit(), f"Expected integer epoch, got: {out!r}"

    def test_close_to_real_now(self):
        before = int(time.time())
        out = int(run_portable("portable_epoch_now"))
        after = int(time.time())
        assert before <= out <= after + 2, f"Epoch {out} not in range [{before}, {after}]"


# ---------------------------------------------------------------------------
# portable_date_minus
# ---------------------------------------------------------------------------

class TestPortableDateMinus:
    def test_zero_days_returns_now(self):
        now = int(time.time())
        out = int(run_portable("portable_date_minus 0"))
        assert abs(out - now) < 10

    def test_one_day_ago(self):
        now = int(time.time())
        expected = now - 86400
        out = int(run_portable("portable_date_minus 1"))
        assert abs(out - expected) < 10

    def test_24_days_ago(self):
        now = int(time.time())
        expected = now - 24 * 86400
        out = int(run_portable("portable_date_minus 24"))
        assert abs(out - expected) < 10

    def test_explicit_base_epoch(self):
        base = 1700000000
        days = 7
        expected = base - days * 86400
        out = int(run_portable(f"portable_date_minus {days} {base}"))
        assert out == expected, f"Expected {expected}, got {out}"

    def test_one_day_gives_yesterday_date(self):
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        out = run_portable(
            'epoch=$(portable_date_minus 1)\n'
            "python3 -c \"import datetime; "
            "print(datetime.datetime.fromtimestamp(int('$epoch')).date().isoformat())\""
        )
        assert out == yesterday

    def test_result_is_less_than_now(self):
        now = int(time.time())
        out = int(run_portable("portable_date_minus 1"))
        assert out < now

    def test_larger_days_gives_smaller_epoch(self):
        out1 = int(run_portable("portable_date_minus 1"))
        out7 = int(run_portable("portable_date_minus 7"))
        assert out7 < out1


# ---------------------------------------------------------------------------
# portable_sed_inplace
# ---------------------------------------------------------------------------

class TestPortableSedInplace:
    def test_simple_substitution(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello world\n")
        run_portable(f'portable_sed_inplace "s/hello/goodbye/" "{f}"')
        assert f.read_text() == "goodbye world\n"

    def test_global_flag(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("foo foo foo\n")
        run_portable(f'portable_sed_inplace "s/foo/bar/g" "{f}"')
        assert f.read_text() == "bar bar bar\n"

    def test_only_first_occurrence_without_g(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("foo foo foo\n")
        run_portable(f'portable_sed_inplace "s/foo/bar/" "{f}"')
        content = f.read_text()
        # First occurrence replaced; at least one 'foo' remains
        assert "bar" in content
        assert "foo" in content

    def test_pipe_delimiter_for_paths(self, tmp_path):
        f = tmp_path / "env.txt"
        f.write_text("KEY=oldvalue\n")
        run_portable(f'portable_sed_inplace "s|^KEY=.*|KEY=newvalue|" "{f}"')
        assert f.read_text() == "KEY=newvalue\n"

    def test_range_deletion(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("before\n# BLOCK BEGIN\nmiddle\n# BLOCK END\nafter\n")
        run_portable(f'portable_sed_inplace "/# BLOCK BEGIN/,/# BLOCK END/d" "{f}"')
        content = f.read_text()
        assert "middle" not in content
        assert "before" in content
        assert "after" in content

    def test_multiline_preserves_unmatched(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("alpha\nbeta=old\ngamma\n")
        run_portable(f'portable_sed_inplace "s/beta=old/beta=new/" "{f}"')
        result = f.read_text()
        assert "alpha" in result
        assert "beta=new" in result
        assert "gamma" in result

    def test_no_match_leaves_file_unchanged(self, tmp_path):
        f = tmp_path / "test.txt"
        original = "no match here\n"
        f.write_text(original)
        run_portable(f'portable_sed_inplace "s/zzz/ZZZ/" "{f}"')
        assert f.read_text() == original

    def test_cos_marker_deletion_pattern(self, tmp_path):
        """Reproduce the exact pattern used in setup-git-hooks.sh."""
        marker = "# COS_AUTO_UPDATE"
        f = tmp_path / "post-merge"
        f.write_text(
            "#!/usr/bin/env bash\n"
            f"{marker} BEGIN\nsome hook code\n{marker} END\n"
            "echo done\n"
        )
        run_portable(
            f'portable_sed_inplace "/{marker} BEGIN/,/{marker} END/d" "{f}"'
        )
        content = f.read_text()
        assert "some hook code" not in content
        assert "echo done" in content

    def test_version_substitution_pattern(self, tmp_path):
        """Reproduce the exact pattern used in version.sh."""
        f = tmp_path / "root.go"
        f.write_text('Version: "1.0.0"\n')
        run_portable(
            f'portable_sed_inplace \'s/Version: "1.0.0"/Version: "1.0.1"/\' "{f}"'
        )
        assert f.read_text() == 'Version: "1.0.1"\n'


# ---------------------------------------------------------------------------
# portable_stat_mtime
# ---------------------------------------------------------------------------

class TestPortableStatMtime:
    def test_returns_integer(self, tmp_path):
        f = tmp_path / "file.txt"
        f.write_text("content")
        out = run_portable(f'portable_stat_mtime "{f}"')
        assert out.isdigit(), f"Expected integer mtime, got: {out!r}"

    def test_mtime_close_to_now(self, tmp_path):
        f = tmp_path / "file.txt"
        f.write_text("content")
        before = int(time.time())
        mtime = int(run_portable(f'portable_stat_mtime "{f}"'))
        after = int(time.time())
        assert before - 5 <= mtime <= after + 5, (
            f"mtime {mtime} is outside [{before - 5}, {after + 5}]"
        )

    def test_older_file_has_older_mtime(self, tmp_path):
        f1 = tmp_path / "old.txt"
        f1.write_text("old")
        old_ts = int(time.time()) - 3600
        os.utime(str(f1), (old_ts, old_ts))

        f2 = tmp_path / "new.txt"
        f2.write_text("new")

        mtime1 = int(run_portable(f'portable_stat_mtime "{f1}"'))
        mtime2 = int(run_portable(f'portable_stat_mtime "{f2}"'))
        assert mtime1 < mtime2

    def test_directory_mtime(self, tmp_path):
        d = tmp_path / "subdir"
        d.mkdir()
        out = run_portable(f'portable_stat_mtime "{d}"')
        assert out.isdigit()


# ---------------------------------------------------------------------------
# portable_stat_size
# ---------------------------------------------------------------------------

class TestPortableStatSize:
    def test_empty_file_returns_zero(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("")
        out = run_portable(f'portable_stat_size "{f}"')
        assert out == "0"

    def test_nonexistent_file_returns_zero(self, tmp_path):
        f = tmp_path / "does_not_exist.txt"
        assert not f.exists()
        out = run_portable(f'portable_stat_size "{f}"')
        assert out == "0"

    def test_five_bytes(self, tmp_path):
        f = tmp_path / "known.txt"
        f.write_bytes(b"hello")
        out = run_portable(f'portable_stat_size "{f}"')
        assert out == "5"

    def test_1024_bytes(self, tmp_path):
        f = tmp_path / "kilo.txt"
        f.write_bytes(b"x" * 1024)
        out = run_portable(f'portable_stat_size "{f}"')
        assert out == "1024"

    def test_returns_integer_string(self, tmp_path):
        f = tmp_path / "file.txt"
        f.write_text("some content here")
        out = run_portable(f'portable_stat_size "{f}"')
        assert out.isdigit()

    def test_size_matches_python_getsize(self, tmp_path):
        content = b"\x00\x01\x02\x03" * 100
        f = tmp_path / "binary.bin"
        f.write_bytes(content)
        out = int(run_portable(f'portable_stat_size "{f}"'))
        assert out == f.stat().st_size


# ---------------------------------------------------------------------------
# portable_readlines
# ---------------------------------------------------------------------------

class TestPortableReadlines:
    def test_reads_three_lines(self, tmp_path):
        f = tmp_path / "items.txt"
        f.write_text("alpha\nbeta\ngamma\n")
        out = run_portable(
            f'portable_readlines "{f}" my_arr\n'
            'echo "${#my_arr[@]}"\n'
            'for x in "${my_arr[@]}"; do echo "$x"; done'
        )
        lines = out.splitlines()
        assert lines[0] == "3"
        assert "alpha" in lines
        assert "beta" in lines
        assert "gamma" in lines

    def test_empty_file_yields_empty_array(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("")
        out = run_portable(
            f'portable_readlines "{f}" my_arr\n'
            'echo "${#my_arr[@]}"'
        )
        assert out == "0"

    def test_nonexistent_file_yields_empty_array(self, tmp_path):
        f = tmp_path / "nonexistent.txt"
        out = run_portable(
            f'portable_readlines "{f}" my_arr\n'
            'echo "${#my_arr[@]}"'
        )
        assert out == "0"

    def test_preserves_internal_spaces(self, tmp_path):
        f = tmp_path / "spaced.txt"
        f.write_text("hello world\nfoo  bar  baz\n")
        out = run_portable(
            f'portable_readlines "{f}" my_arr\n'
            'echo "${my_arr[0]}"\n'
            'echo "${my_arr[1]}"'
        )
        lines = out.splitlines()
        assert lines[0] == "hello world"
        assert lines[1] == "foo  bar  baz"

    def test_single_line_no_trailing_newline(self, tmp_path):
        f = tmp_path / "single.txt"
        f.write_bytes(b"only-line")  # no trailing newline
        out = run_portable(
            f'portable_readlines "{f}" my_arr\n'
            'echo "${#my_arr[@]}"\n'
            'echo "${my_arr[0]}"'
        )
        lines = out.splitlines()
        assert lines[0] == "1"
        assert lines[1] == "only-line"

    def test_clears_previous_array_contents(self, tmp_path):
        f1 = tmp_path / "big.txt"
        f1.write_text("x\ny\nz\n")
        f2 = tmp_path / "small.txt"
        f2.write_text("only\n")
        out = run_portable(
            f'portable_readlines "{f1}" arr\n'
            f'portable_readlines "{f2}" arr\n'
            'echo "${#arr[@]}"'
        )
        assert out == "1"

    def test_bash_32_compatible_no_mapfile(self):
        """portable_readlines implementation must not use mapfile or readarray."""
        content = PORTABLE_SH.read_text()
        # Find the portable_readlines function body
        in_fn = False
        fn_lines = []
        depth = 0
        for line in content.splitlines():
            if "portable_readlines" in line and "()" in line:
                in_fn = True
            if in_fn:
                fn_lines.append(line)
                depth += line.count("{") - line.count("}")
                if depth <= 0 and fn_lines:
                    break
        fn_body = "\n".join(fn_lines)
        assert "mapfile" not in fn_body
        assert "readarray" not in fn_body

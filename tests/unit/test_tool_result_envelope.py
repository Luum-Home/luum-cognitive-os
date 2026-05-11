"""Unit tests for lib.tool_result_envelope (ADR-264).

Coverage:
- under-threshold passthrough
- over-threshold envelope
- persist_full=False: no spillover file
- persist_full=True: spillover file exists and contains raw
- SHA-256 filename stability
- Idempotency: double-wrap guard
- Composability stub: no crash when ADR-263 ledger module absent
"""

from __future__ import annotations

import hashlib
import sys


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

THRESHOLD = 28 * 1024      # 28 KB
PREVIEW_SIZE = 7 * 1024    # 7 KB
SMALL_SIZE = 1 * 1024      # 1 KB
LARGE_SIZE = 50 * 1024     # 50 KB


def _make_payload(size: int) -> str:
    """Return a deterministic string of exactly ``size`` characters."""
    base = "abcdefghijklmnopqrstuvwxyz0123456789"
    repeats = (size // len(base)) + 1
    return (base * repeats)[:size]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestUnderThreshold:
    def test_small_result_passthrough(self):
        from lib.tool_result_envelope import wrap_if_large

        raw = _make_payload(SMALL_SIZE)
        result = wrap_if_large(raw, tool_name="read_file", target_hint="/some/path")
        assert result is raw or result == raw, "Under-threshold result must be returned unchanged"
        assert "[TOOL RESULT ENVELOPE]" not in result

    def test_exactly_at_threshold_passthrough(self):
        from lib.tool_result_envelope import wrap_if_large

        raw = _make_payload(THRESHOLD)
        result = wrap_if_large(raw, tool_name="read_file", target_hint="/some/path")
        assert result == raw, "Result equal to threshold must NOT be enveloped"


class TestOverThreshold:
    def test_envelope_marker_present(self, tmp_path):
        from lib.tool_result_envelope import wrap_if_large

        raw = _make_payload(LARGE_SIZE)
        result = wrap_if_large(
            raw,
            tool_name="run_bash",
            target_hint="ls -la /",
            persist_full=False,
            spillover_dir=str(tmp_path),
        )
        assert "[TOOL RESULT ENVELOPE]" in result

    def test_envelope_contains_tool_name(self, tmp_path):
        from lib.tool_result_envelope import wrap_if_large

        raw = _make_payload(LARGE_SIZE)
        result = wrap_if_large(
            raw,
            tool_name="grep_files",
            target_hint="*.py",
            persist_full=False,
            spillover_dir=str(tmp_path),
        )
        assert "tool: grep_files" in result

    def test_envelope_contains_target_hint(self, tmp_path):
        from lib.tool_result_envelope import wrap_if_large

        raw = _make_payload(LARGE_SIZE)
        result = wrap_if_large(
            raw,
            tool_name="run_bash",
            target_hint="find . -name '*.py'",
            persist_full=False,
            spillover_dir=str(tmp_path),
        )
        assert "target: find . -name '*.py'" in result

    def test_envelope_contains_full_size(self, tmp_path):
        from lib.tool_result_envelope import wrap_if_large

        raw = _make_payload(LARGE_SIZE)
        result = wrap_if_large(
            raw,
            tool_name="run_bash",
            target_hint="cmd",
            persist_full=False,
            spillover_dir=str(tmp_path),
        )
        assert f"full_size: {LARGE_SIZE} chars" in result

    def test_preview_truncation(self, tmp_path):
        from lib.tool_result_envelope import wrap_if_large

        raw = _make_payload(LARGE_SIZE)
        result = wrap_if_large(
            raw,
            tool_name="run_bash",
            target_hint="cmd",
            persist_full=False,
            spillover_dir=str(tmp_path),
        )
        # Preview should start immediately after the "--- preview (N chars) ---" line
        lines = result.splitlines()
        preview_start = next(
            (i + 1 for i, l in enumerate(lines) if l.startswith("--- preview (")), None
        )
        assert preview_start is not None, "Envelope must contain preview header"
        end_idx = next(
            (i for i in range(preview_start, len(lines)) if lines[i] == "--- end preview ---"),
            None,
        )
        assert end_idx is not None, "Envelope must contain end preview marker"
        preview_content = "\n".join(lines[preview_start:end_idx])
        assert len(preview_content) == PREVIEW_SIZE, (
            f"Preview must be exactly {PREVIEW_SIZE} chars, got {len(preview_content)}"
        )


class TestPersistFull:
    def test_persist_false_no_file(self, tmp_path):
        from lib.tool_result_envelope import wrap_if_large

        raw = _make_payload(LARGE_SIZE)
        wrap_if_large(
            raw,
            tool_name="run_bash",
            target_hint="cmd",
            persist_full=False,
            spillover_dir=str(tmp_path),
        )
        files = list(tmp_path.iterdir())
        assert len(files) == 0, "persist_full=False must not write any spillover file"

    def test_persist_false_pointer_is_none(self, tmp_path):
        from lib.tool_result_envelope import wrap_if_large

        raw = _make_payload(LARGE_SIZE)
        result = wrap_if_large(
            raw,
            tool_name="run_bash",
            target_hint="cmd",
            persist_full=False,
            spillover_dir=str(tmp_path),
        )
        assert "full_pointer: none" in result

    def test_persist_true_file_exists(self, tmp_path):
        from lib.tool_result_envelope import wrap_if_large

        raw = _make_payload(LARGE_SIZE)
        wrap_if_large(
            raw,
            tool_name="run_bash",
            target_hint="cmd",
            persist_full=True,
            spillover_dir=str(tmp_path),
        )
        files = list(tmp_path.iterdir())
        assert len(files) == 1, "persist_full=True must write exactly one spillover file"

    def test_persist_true_file_contains_raw(self, tmp_path):
        from lib.tool_result_envelope import wrap_if_large

        raw = _make_payload(LARGE_SIZE)
        wrap_if_large(
            raw,
            tool_name="run_bash",
            target_hint="cmd",
            persist_full=True,
            spillover_dir=str(tmp_path),
        )
        spill_file = next(tmp_path.iterdir())
        content = spill_file.read_text(encoding="utf-8")
        assert content == raw, "Spillover file must contain the full raw result"

    def test_persist_true_pointer_in_envelope(self, tmp_path):
        from lib.tool_result_envelope import wrap_if_large

        raw = _make_payload(LARGE_SIZE)
        result = wrap_if_large(
            raw,
            tool_name="run_bash",
            target_hint="cmd",
            persist_full=True,
            spillover_dir=str(tmp_path),
        )
        spill_file = next(tmp_path.iterdir())
        assert str(spill_file.resolve()) in result, (
            "Envelope must include the absolute path to the spillover file"
        )


class TestSha256Stability:
    def test_same_input_same_filename(self, tmp_path):
        from lib.tool_result_envelope import wrap_if_large

        raw = _make_payload(LARGE_SIZE)
        wrap_if_large(raw, "t", "h", persist_full=True, spillover_dir=str(tmp_path))
        wrap_if_large(raw, "t", "h", persist_full=True, spillover_dir=str(tmp_path))

        files = list(tmp_path.iterdir())
        assert len(files) == 1, "Same content must produce the same spillover filename"

    def test_filename_is_sha256(self, tmp_path):
        from lib.tool_result_envelope import wrap_if_large

        raw = _make_payload(LARGE_SIZE)
        wrap_if_large(raw, "t", "h", persist_full=True, spillover_dir=str(tmp_path))

        spill_file = next(tmp_path.iterdir())
        expected_sha = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:64]
        assert spill_file.name == f"{expected_sha}.txt", (
            f"Spillover filename must be sha256[:64].txt, got {spill_file.name}"
        )


class TestIdempotency:
    def test_already_enveloped_not_wrapped_again(self, tmp_path):
        from lib.tool_result_envelope import wrap_if_large

        raw = _make_payload(LARGE_SIZE)
        first = wrap_if_large(raw, "t", "h", persist_full=False, spillover_dir=str(tmp_path))
        second = wrap_if_large(first, "t", "h", persist_full=False, spillover_dir=str(tmp_path))
        assert first == second, "Calling wrap_if_large on an already-enveloped string must be a no-op"
        assert second.count("[TOOL RESULT ENVELOPE]") == 1, "Marker must appear exactly once"


class TestComposabilityWithADR263:
    """Verify graceful behavior whether or not lib.tool_replay_ledger exists."""

    def test_no_crash_when_ledger_absent(self, tmp_path):
        """wrap_if_large must work normally when ADR-263 ledger is not installed."""
        # Ensure the module is NOT available in this test.
        ledger_mod = "lib.tool_replay_ledger"
        original = sys.modules.pop(ledger_mod, None)
        try:
            from lib.tool_result_envelope import wrap_if_large

            raw = _make_payload(LARGE_SIZE)
            result = wrap_if_large(raw, "t", "h", persist_full=False, spillover_dir=str(tmp_path))
            assert "[TOOL RESULT ENVELOPE]" in result
        finally:
            if original is not None:
                sys.modules[ledger_mod] = original

    def test_reference_only_preview_empty(self, tmp_path):
        """When ledger says REFERENCE_ONLY, passing preview_size=0 collapses to pointer-only."""
        from lib.tool_result_envelope import wrap_if_large

        raw = _make_payload(LARGE_SIZE)
        result = wrap_if_large(
            raw,
            tool_name="run_bash",
            target_hint="cmd",
            preview_size=0,
            persist_full=True,
            spillover_dir=str(tmp_path),
        )
        assert "[TOOL RESULT ENVELOPE]" in result
        # Preview section should be empty (0 chars)
        assert "--- preview (0 chars) ---" in result


class TestRenderEnvelope:
    """Test render_envelope directly."""

    def test_render_format(self):
        from lib.tool_result_envelope import EnvelopePreview, render_envelope

        ep = EnvelopePreview(
            preview_text="hello world",
            full_chars=50000,
            tool_name="read_file",
            target_hint="/tmp/big.txt",
            full_pointer="/path/to/spill.txt",
        )
        rendered = render_envelope(ep)
        assert rendered.startswith("[TOOL RESULT ENVELOPE]")
        assert "tool: read_file" in rendered
        assert "target: /tmp/big.txt" in rendered
        assert "full_size: 50000 chars (truncated; preview below)" in rendered
        assert "full_pointer: /path/to/spill.txt" in rendered
        assert "--- preview (11 chars) ---" in rendered
        assert "hello world" in rendered
        assert "--- end preview ---" in rendered

    def test_render_none_pointer(self):
        from lib.tool_result_envelope import EnvelopePreview, render_envelope

        ep = EnvelopePreview(
            preview_text="",
            full_chars=100,
            tool_name="t",
            target_hint="h",
            full_pointer=None,
        )
        rendered = render_envelope(ep)
        assert "full_pointer: none" in rendered

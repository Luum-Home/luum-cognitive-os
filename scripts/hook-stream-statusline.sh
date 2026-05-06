#!/usr/bin/env bash
# SCOPE: both
# ROLE: observability
# CANONICAL: scripts/hook-stream-statusline.sh
# @on-demand: started manually by operator to display hook-stream statusline; requires hook-stream FIFO to be active
# hook-stream-statusline.sh — Non-blocking FIFO reader for hook-stream statusline
#
# Reads lines from .cognitive-os/runtime/hook-stream.fifo and prints them in
# compact statusline format. Uses Python for the non-blocking FIFO read because
# macOS does not support bash read -t reliably on FIFOs opened O_RDWR.
#
# Output format (lines already in this format from the wrapper):
#   [hook] <hook_name> <event> <duration_ms>ms <ok|FAIL>
#
# Usage:
#   bash scripts/hook-stream-statusline.sh               # read pending lines, exit
#   bash scripts/hook-stream-statusline.sh --watch       # loop until Ctrl+C
#   bash scripts/hook-stream-statusline.sh --timeout 2   # single-shot with 2s window
#
# Environment:
#   COS_FIFO_PATH  — override FIFO path
#   COGNITIVE_OS_PROJECT_DIR / CLAUDE_PROJECT_DIR / CODEX_PROJECT_DIR — project root
#
# Design notes:
#   - FIFO opened O_RDWR | O_NONBLOCK to avoid blocking when no writer is attached.
#     On macOS, O_RDONLY on a FIFO blocks until a writer opens it.
#   - Uses Python os.read with BlockingIOError catch for portable non-blocking poll.
#   - The script never blocks indefinitely and never spawns orphan background processes.
#   - Exit 0 when no data arrives within the timeout window — this is not an error.
#
# FIFO write side (wrapper):
#   The hook-timing-wrapper.sh writes to this FIFO when COS_HOOK_TIMING_FIFO=1.

set -uo pipefail

# ── Locate project root ─────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$("$SCRIPT_DIR/cos-root" project)"

FIFO="${COS_FIFO_PATH:-$PROJECT_DIR/.cognitive-os/runtime/hook-stream.fifo}"

# ── Parse flags ──────────────────────────────────────────────────────────────
WATCH_MODE=0
TIMEOUT="0.1"
for arg in "$@"; do
  case "$arg" in
    --watch)   WATCH_MODE=1 ;;
    --timeout) shift; TIMEOUT="${1:-0.1}" ;;
  esac
done

# ── Validate FIFO ────────────────────────────────────────────────────────────
if [ ! -p "$FIFO" ]; then
  # FIFO absent: emit nothing (statusline stays blank). Not an error.
  exit 0
fi

# ── Delegate to Python for portable non-blocking FIFO read ──────────────────
python3 - "$FIFO" "$WATCH_MODE" "$TIMEOUT" <<'PYEOF'
import os
import sys
import time

path = sys.argv[1]
watch = sys.argv[2] == "1"
timeout = float(sys.argv[3])

try:
    # O_RDWR avoids blocking when no writer is attached (macOS O_RDONLY blocks).
    # O_NONBLOCK makes reads return immediately with BlockingIOError if no data.
    fd = os.open(path, os.O_RDWR | os.O_NONBLOCK)
except OSError:
    # FIFO disappeared or permission error — exit silently.
    sys.exit(0)

buf = b""
deadline = time.monotonic() + (3600.0 if watch else timeout)

try:
    while time.monotonic() < deadline:
        try:
            chunk = os.read(fd, 4096)
            if chunk:
                buf += chunk
                lines = buf.split(b"\n")
                # Keep incomplete last chunk in buf
                buf = lines[-1]
                for line in lines[:-1]:
                    text = line.decode("utf-8", errors="replace").strip()
                    if text:
                        print(text, flush=True)
        except BlockingIOError:
            time.sleep(0.05)
        except OSError:
            break
except KeyboardInterrupt:
    pass
finally:
    try:
        os.close(fd)
    except OSError:
        pass
PYEOF

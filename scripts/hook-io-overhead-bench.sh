#!/usr/bin/env bash
# SCOPE: os-only
# ROLE: instrumentation
# CANONICAL: scripts/hook-io-overhead-bench.sh
# hook-io-overhead-bench.sh — What the stdout/stderr accounting added to
# scripts/hook-timing-wrapper.sh costs on the hot path.
#
# The wrapper runs once per hook per tool call (21 hooks per Bash call in this
# repo), so instrumentation added to it has to justify itself in wall-clock
# terms. Two independent measurements, because neither alone is convincing:
#
#   PART A — primitives. The change adds a fixed number of forks: one `rm`
#     (EXIT trap) always, plus one `wc` and one-to-two `cat` when a stream is
#     non-empty. Timing those primitives directly is stable even on a loaded
#     machine, so this is the number to quote.
#
#   PART B — end-to-end. The wrapper with measurement off vs on, alternating
#     cells round by round and reporting the MEDIAN of paired deltas. On a busy
#     machine a single wrapper invocation swings by tens of milliseconds, so the
#     mean is worthless here and even the median is only a sanity check on A.
#
# Usage:
#   bash scripts/hook-io-overhead-bench.sh [iterations_per_round] [rounds]
#
# Defaults: 12 iterations per round, 15 rounds. Exit code is always 0 — this is
# a measurement tool, not a gate.

set -uo pipefail

ITERATIONS="${1:-12}"
ROUNDS="${2:-15}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WRAPPER="$SCRIPT_DIR/hook-timing-wrapper.sh"

if [ ! -f "$WRAPPER" ]; then
  echo "hook-io-overhead-bench: wrapper not found at $WRAPPER" >&2
  exit 0
fi

WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/cos-hook-io-bench.XXXXXX")"
trap 'rm -rf "$WORK_DIR" 2>/dev/null || true' EXIT

# Isolate telemetry: the wrapper appends one row per invocation, and a few
# hundred synthetic rows would sit at the top of the real ranking produced by
# scripts/context_injection_report.py. Point the wrapper at a throwaway project
# root so the benchmark never writes into live metrics.
mkdir -p "$WORK_DIR/.claude" "$WORK_DIR/.cognitive-os/metrics"
export COGNITIVE_OS_PROJECT_DIR="$WORK_DIR"
export CLAUDE_PROJECT_DIR="$WORK_DIR"

_now() {
  perl -MTime::HiRes=time -e 'printf("%.6f\n", time())' 2>/dev/null \
    || python3 -c 'import time; print(time.time())'
}

_per_call_ms() { # start end n
  awk -v a="$1" -v b="$2" -v n="$3" 'BEGIN { printf("%.3f", (b - a) * 1000 / n) }'
}

_median() { # space-separated numbers on stdin
  tr ' ' '\n' | awk 'NF { v[n++] = $1 } END {
    if (!n) { print "0.000"; exit }
    asort_done = 0
    for (i = 0; i < n; i++) for (j = i + 1; j < n; j++) if (v[j] < v[i]) { t = v[i]; v[i] = v[j]; v[j] = t }
    if (n % 2) printf("%.3f", v[(n - 1) / 2]); else printf("%.3f", (v[n / 2 - 1] + v[n / 2]) / 2)
  }'
}

# ── PART A: cost of the primitives the change adds ──────────────────────────

printf '=== PART A — cost of the added primitives (%s x %s) ===\n\n' \
  "$ITERATIONS" "$ROUNDS"

PRIM_A="$WORK_DIR/prim.out"
PRIM_B="$WORK_DIR/prim.err"
: >"$PRIM_A"
printf 'a realistic advisory payload emitted by a hook\n' >"$PRIM_B"

TOTAL_PRIM=$ITERATIONS
_time_primitive() { # label, command...
  local label="$1"; shift
  local samples="" r start end i
  for ((r = 0; r < ROUNDS; r++)); do
    start="$(_now)"
    for ((i = 0; i < TOTAL_PRIM; i++)); do "$@" >/dev/null 2>&1; done
    end="$(_now)"
    samples="$samples $(_per_call_ms "$start" "$end" "$TOTAL_PRIM")"
  done
  printf '%-26s %8s ms/call (median)\n' "$label" "$(printf '%s' "$samples" | _median)"
}

_time_primitive "rm -f (always paid)"   rm -f "$WORK_DIR/absent-1" "$WORK_DIR/absent-2"
_time_primitive "wc -c (only if output)" wc -c "$PRIM_A" "$PRIM_B"
_time_primitive "cat   (only if output)" cat "$PRIM_B"
printf '\n'
printf 'Fork accounting for the change:\n'
printf '  silent hook  -> +1 fork  (rm in the EXIT trap)\n'
printf '  chatty hook  -> +2 to +4 forks (rm + wc + one cat per non-empty stream)\n'
printf '  SessionStart -> net 0 forks on the quarantine path: the rm replaces the\n'
printf '                  mktemp that path used to pay.\n\n'

# ── PART B: end-to-end wrapper, paired medians ──────────────────────────────

cat >"$WORK_DIR/silent-hook.sh" <<'SILENT'
#!/usr/bin/env bash
exit 0
SILENT

cat >"$WORK_DIR/chatty-hook.sh" <<'CHATTY'
#!/usr/bin/env bash
for i in $(seq 40); do
  printf 'advisory line %s: context injected by a hook that talks\n' "$i"
done
printf 'diagnostic on stderr\n' >&2
exit 0
CHATTY

_run_cell() { # hook, COS_HOOK_IO_MEASURE_DISABLE value
  local hook="$1" disable="$2" start end i
  start="$(_now)"
  for ((i = 0; i < ITERATIONS; i++)); do
    COS_HOOK_IO_MEASURE_DISABLE="$disable" \
      bash "$WRAPPER" PostToolUse "$hook" </dev/null >/dev/null 2>/dev/null
  done
  end="$(_now)"
  _per_call_ms "$start" "$end" "$ITERATIONS"
}

printf '=== PART B — end-to-end wrapper, median of %s paired rounds ===\n\n' "$ROUNDS"
printf '%-10s %12s %12s %12s %10s\n' "hook" "off_ms" "on_ms" "delta_ms" "delta_pct"

for label in silent chatty; do
  hook="$WORK_DIR/$label-hook.sh"
  offs=""; ons=""; deltas=""
  for ((r = 1; r <= ROUNDS; r++)); do
    if (( r % 2 == 1 )); then
      off_ms="$(_run_cell "$hook" 1)"; on_ms="$(_run_cell "$hook" 0)"
    else
      on_ms="$(_run_cell "$hook" 0)"; off_ms="$(_run_cell "$hook" 1)"
    fi
    offs="$offs $off_ms"
    ons="$ons $on_ms"
    deltas="$deltas $(awk -v a="$off_ms" -v b="$on_ms" 'BEGIN { printf("%.3f", b - a) }')"
  done
  off_med="$(printf '%s' "$offs" | _median)"
  on_med="$(printf '%s' "$ons" | _median)"
  delta_med="$(printf '%s' "$deltas" | _median)"
  pct="$(awk -v a="$off_med" -v d="$delta_med" \
    'BEGIN { if (a > 0) printf("%+.1f%%", d * 100 / a); else printf("n/a") }')"
  printf '%-10s %12s %12s %12s %10s\n' "$label" "$off_med" "$on_med" "$delta_med" "$pct"
done

printf '\n'
printf 'Reading: "off" = COS_HOOK_IO_MEASURE_DISABLE=1 (the old passthrough).\n'
printf '         Part B is a sanity check on Part A, not the headline number:\n'
printf '         under concurrent agent load a single wrapper call swings by tens\n'
printf '         of ms, which is an order of magnitude above what is being measured.\n'

exit 0

#!/usr/bin/env bash
# SCOPE: both
# @on-demand: sourced library helper — not registered independently, sourced by other hooks
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"
# SessionStart: detect orchestrator communication mode and report to stderr.
#
# Prints a one-line status so developers immediately know whether the session
# is running in CONNECTED (executor + Valkey) or FIRE_AND_FORGET (Agent tool)
# mode. Entirely advisory — exits 0 in all cases.

timeout 30 python3 -c "
import sys
try:
    from lib.orchestrator_capabilities import OrchestratorCapabilities
    caps = OrchestratorCapabilities().detect()
    print(caps.format_status(), file=sys.stderr)
    if caps.mode == 'connected':
        print('TIP: Using CONNECTED mode — agents support heartbeat + Q\&A', file=sys.stderr)
    else:
        print('TIP: Using FIRE_AND_FORGET mode — include ALL context in agent prompts', file=sys.stderr)
except Exception as exc:
    print(f'orchestrator-mode-detect: skipped ({exc})', file=sys.stderr)
" 2>&1 || true

exit 0

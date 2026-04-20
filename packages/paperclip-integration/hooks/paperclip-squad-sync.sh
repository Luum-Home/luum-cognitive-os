#!/usr/bin/env bash
# paperclip-squad-sync.sh — Sync squad definitions to Paperclip org chart
# Trigger: SessionStart (runs once per session to push org chart)
#
# Reads squads/*.yaml, builds org chart payload, pushes to Paperclip.
# Fire-and-forget — never blocks session startup.

_HOOK_NAME="paperclip-squad-sync"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
set -uo pipefail

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
PAPERCLIP_URL="${COGNITIVE_OS_PAPERCLIP_URL:-http://localhost:3200}"
SQUADS_DIR="$PROJECT_DIR/squads"

# No squads directory? Skip silently.
[ -d "$SQUADS_DIR" ] || exit 0

# Check if any squad YAML files exist
SQUAD_FILES=$(find "$SQUADS_DIR" -name '*.yaml' -o -name '*.yml' 2>/dev/null | grep -v organization.yaml || true)
[ -z "$SQUAD_FILES" ] && exit 0

# Fire-and-forget: sync in background
(
  python3 -c "
import sys, os, glob, json
sys.path.insert(0, '$PROJECT_DIR/lib')
sys.path.insert(0, '$PROJECT_DIR/packages/ecosystem-tools/lib')
os.environ.setdefault('COGNITIVE_OS_PAPERCLIP_URL', '$PAPERCLIP_URL')

try:
    import yaml
except ImportError:
    # PyYAML not available — try a basic parser fallback
    import re

    def _parse_squad_basic(path):
        '''Minimal YAML parser for squad files: extracts name, members, manager.'''
        with open(path, 'r') as f:
            text = f.read()
        name = ''
        m = re.search(r'name:\s*(.+)', text)
        if m:
            name = m.group(1).strip()
        manager = ''
        m = re.search(r'manager:.*?agentRef:\s*(\S+)', text, re.DOTALL)
        if m:
            manager = m.group(1).strip()
        agents = []
        for m in re.finditer(r'agentRef:\s*(\S+)', text):
            ref = m.group(1).strip()
            agents.append({'name': ref, 'role': 'member'})
        return {'name': name, 'manager': manager, 'agents': agents}

    class yaml:
        @staticmethod
        def safe_load(f):
            return None

try:
    from paperclip_client import PaperclipClient
    client = PaperclipClient()
    if not client.is_available():
        sys.exit(0)

    squads_data = []
    squad_dir = '$SQUADS_DIR'

    for fpath in sorted(glob.glob(os.path.join(squad_dir, '*.yaml')) +
                         glob.glob(os.path.join(squad_dir, '*.yml'))):
        basename = os.path.basename(fpath)
        if basename == 'organization.yaml':
            continue
        try:
            with open(fpath, 'r') as f:
                data = yaml.safe_load(f)
            if data and isinstance(data, dict):
                spec = data.get('spec', {})
                metadata = data.get('metadata', {})
                members = spec.get('members', [])
                agents = [{'name': m.get('agentRef', ''), 'role': m.get('role', 'member')}
                          for m in members if m.get('agentRef')]
                manager_info = spec.get('manager', {})
                squad_entry = {
                    'name': metadata.get('name', basename.replace('.yaml', '')),
                    'manager': manager_info.get('agentRef', ''),
                    'agents': agents,
                }
                squads_data.append(squad_entry)
            else:
                # Fallback to basic parser
                entry = _parse_squad_basic(fpath)
                if entry.get('name'):
                    squads_data.append(entry)
        except Exception:
            pass

    if squads_data:
        client.sync_org_chart(squads_data)

except Exception:
    pass  # Fire-and-forget
" 2>/dev/null
) &
_SQUAD_PID=$!

# ADR-028 D1.B — register with process_registry so the reaper tracks this spawn.
(
  COGNITIVE_OS_PROJECT_DIR="$PROJECT_DIR" \
    python3 - "$_SQUAD_PID" <<'PYEOF' >/dev/null 2>&1
import sys, os
root = os.environ.get("COGNITIVE_OS_PROJECT_DIR") or os.getcwd()
sys.path.insert(0, root)
try:
    import lib.process_registry as process_registry
    process_registry.register(int(sys.argv[1]), "paperclip-squad-sync", 60, "short_lived")
except Exception:
    pass
PYEOF
) &

exit 0

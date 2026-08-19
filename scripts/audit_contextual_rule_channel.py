#!/usr/bin/env python3
# SCOPE: os-only
"""Audit the observability channel that hooks/contextual-rule-loader.sh would open.

Answers, with numbers instead of recollection:

  1. Is the hook registered in .claude/settings.json?
  2. How many rules can the channel EVER name?  (structural ceiling =
     contextual_triggers entries that have a matching rules/<name>.md)
  3. How many does it name in practice, replaying REAL Agent prompts from the
     local Claude Code transcripts through the hook's own matcher?
  4. What does that cost — the hook's stdout is rule bodies injected into the
     orchestrator's context, not just a log line.

Read-only. Never writes to .cognitive-os/metrics/. Never registers anything.

Exit codes: 0 = no finding, 1 = finding, 2 = error.

Why this exists: the 2026-08-19 observability report proposed registering the
hook to take the registry channel from 15.1% to 24.2%, on the premise that the
channel would cover all 131 rules. It cannot: only rules with a trigger are
reachable. This script recomputes the honest number and refuses to let the
premise be repeated without a command behind it.
"""

from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CONFIG = REPO / "cognitive-os.yaml"
RULES_DIR = REPO / "rules"
SETTINGS = REPO / ".claude" / "settings.json"
HOOK = REPO / "hooks" / "contextual-rule-loader.sh"

# Mirrors the hook: MAX_RULES=3 (contextual-rule-loader.sh line 59).
MAX_RULES = 3

# Registry totals as published by docs/06-Daily/reports/observabilidad-primitivas-2026-08-19.md
REGISTRY_TOTAL = 1440
BASELINE_SIGNAL_CAPABLE = 217  # families with a channel today, rules excluded


def parse_triggers(config_path: Path) -> list[tuple[str, str]]:
    """Parse contextual_triggers exactly the way the hook's embedded parser does."""
    triggers: list[tuple[str, str]] = []
    in_block = False
    with config_path.open() as fh:
        for line in fh:
            stripped = line.rstrip()
            if re.match(r"^\s+contextual_triggers:\s*(#.*)?$", stripped):
                in_block = True
                continue
            if not in_block:
                continue
            if not stripped or stripped.lstrip().startswith("#"):
                continue
            indent = len(stripped) - len(stripped.lstrip())
            if indent <= 4:
                break
            m = re.match(r'^\s+([a-z0-9-]+)\s*:\s*"(.+)"\s*$', stripped)
            if m:
                triggers.append((m.group(1), m.group(2)))
    return triggers


def is_registered(settings_path: Path) -> bool:
    if not settings_path.is_file():
        return False
    return "contextual-rule-loader" in settings_path.read_text()


def count_family_rules(rules_dir: Path) -> int:
    return len(list(rules_dir.glob("*.md")))


def load_agent_prompts(transcript_glob: str) -> tuple[list[str], int]:
    """Extract every Agent/Task tool_input.prompt from local session transcripts."""
    prompts: list[str] = []
    files = sorted(glob.glob(os.path.expanduser(transcript_glob)))
    for path in files:
        try:
            with open(path, errors="ignore") as fh:
                for line in fh:
                    if '"Agent"' not in line and '"Task"' not in line:
                        continue
                    try:
                        rec = json.loads(line)
                    except (ValueError, TypeError):
                        continue
                    content = (rec.get("message") or {}).get("content")
                    if not isinstance(content, list):
                        continue
                    for block in content:
                        if not isinstance(block, dict):
                            continue
                        if block.get("type") != "tool_use":
                            continue
                        if block.get("name") not in ("Agent", "Task"):
                            continue
                        prompt = (block.get("input") or {}).get("prompt")
                        if prompt:
                            prompts.append(prompt)
        except OSError:
            continue
    return prompts, len(files)


def match(prompt: str, reachable: list[tuple[str, str]], cap: int) -> list[str]:
    lowered = prompt.lower()
    out: list[str] = []
    for name, pattern in reachable:
        if len(out) >= cap:
            break
        try:
            if re.search(pattern, lowered, re.IGNORECASE):
                out.append(name)
        except re.error:
            continue
    return out



def default_transcript_glob() -> str:
    """El glob de transcripts, derivado de donde esta el repo AHORA.

    Estuvo hardcodeado como ``-Users-*-Projects-luum-luum-agent-os``, que es el
    nombre del proyecto de una maquina concreta escrito a mano dentro del
    codigo. Dos consecuencias, y la segunda es peor que la primera: el script
    solo funcionaba en un checkout con ese nombre, y --al fallar el glob-- el
    corpus de replay quedaba VACIO en cualquier otro, o sea que el script
    reportaba "0 reglas nombradas en la practica" sin distinguirlo de "no
    encontre un solo transcript que leer". Un cero por corpus vacio es
    exactamente la lectura falsa que este repo persigue.

    Claude Code guarda los transcripts bajo ~/.claude/projects/<slug>/, donde
    <slug> es la ruta absoluta del proyecto con las barras vueltas guiones. Se
    calcula, no se adivina.
    """
    # Claude Code sustituye por guion TANTO las barras COMO los puntos, asi que
    # un username con puntos (nombre.apellido) se vuelve nombre-apellido en el
    # slug. Cambiar solo las barras daba un directorio inexistente, glob vacio,
    # y el script reportaba "0 reglas nombradas en la practica" sobre un corpus
    # de cero transcripts -- indistinguible de haber mirado y no encontrado.
    slug = str(REPO).replace("/", "-").replace(".", "-")
    return f"~/.claude/projects/{slug}/*.jsonl"

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--transcripts",
        default=default_transcript_glob(),
        help="glob for Claude Code session transcripts (replay corpus); "
             "por defecto se deriva de la ruta real del repo",
    )
    ap.add_argument("--json", action="store_true", help="emit JSON instead of prose")
    args = ap.parse_args()

    if not CONFIG.is_file() or not RULES_DIR.is_dir():
        print("ERROR: cognitive-os.yaml or rules/ not found", file=sys.stderr)
        return 2

    registered = is_registered(SETTINGS)
    hook_present = HOOK.exists()
    family_total = count_family_rules(RULES_DIR)

    triggers = parse_triggers(CONFIG)
    reachable = [(n, p) for n, p in triggers if (RULES_DIR / f"{n}.md").is_file()]
    orphan_triggers = [n for n, _ in triggers if not (RULES_DIR / f"{n}.md").is_file()]
    ceiling = len(reachable)

    prompts, n_files = load_agent_prompts(args.transcripts)
    observed: collections.Counter[str] = collections.Counter()
    emitting = 0
    injected_bytes = 0
    rule_size = {n: (RULES_DIR / f"{n}.md").stat().st_size for n, _ in reachable}
    for prompt in prompts:
        hits = match(prompt, reachable, MAX_RULES)
        if hits:
            emitting += 1
            observed.update(hits)
            injected_bytes += sum(rule_size[h] for h in hits)

    def pct(extra: int) -> float:
        return (BASELINE_SIGNAL_CAPABLE + extra) / REGISTRY_TOTAL * 100

    result = {
        "hook_present": hook_present,
        "hook_registered": registered,
        "family_rules_total": family_total,
        "triggers_declared": len(triggers),
        "triggers_orphan": orphan_triggers,
        "channel_ceiling": ceiling,
        "unreachable_rules": family_total - ceiling,
        "replay_transcripts": n_files,
        "replay_agent_launches": len(prompts),
        "replay_launches_emitting": emitting,
        "replay_distinct_rules": len(observed),
        "replay_injected_bytes": injected_bytes,
        "replay_avg_bytes_per_launch": injected_bytes // emitting if emitting else 0,
        "registry_pct_today": round(pct(0), 1),
        "registry_pct_claimed_131": round(pct(family_total), 1),
        "registry_pct_ceiling": round(pct(ceiling), 1),
        "registry_pct_observed": round(pct(len(observed)), 1),
    }

    finding = ceiling < family_total

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("contextual-rule-loader channel audit")
        print(f"  hook present      : {hook_present}  ({HOOK})")
        print(f"  hook registered   : {registered}")
        print(f"  rules/ family     : {family_total} files")
        print(f"  triggers declared : {len(triggers)} (orphan: {orphan_triggers or 'none'})")
        print(f"  CHANNEL CEILING   : {ceiling} rules can ever be named")
        print(f"  unreachable       : {family_total - ceiling} rules have no trigger")
        print()
        print(f"  replay corpus     : {len(prompts)} real Agent prompts from {n_files} transcripts")
        if prompts:
            print(f"  launches emitting : {emitting} ({emitting / len(prompts) * 100:.1f}%)")
            print(f"  distinct observed : {len(observed)} rules")
            print(f"  context injected  : {injected_bytes:,} bytes total, "
                  f"{result['replay_avg_bytes_per_launch']:,} avg per emitting launch")
        print()
        print(f"  registry channel today          : {result['registry_pct_today']}%")
        print(f"  claimed if registered (131)     : {result['registry_pct_claimed_131']}%  <- premise")
        print(f"  honest ceiling ({ceiling} reachable)     : {result['registry_pct_ceiling']}%")
        print(f"  observed on replay ({len(observed)} named)   : {result['registry_pct_observed']}%")
        if finding:
            print()
            print(f"FINDING: the channel is credited with {family_total} rules but can name at most "
                  f"{ceiling}. The remaining {family_total - ceiling} have no trigger — no prompt "
                  f"can surface them. Registering the hook does not change that.")

    return 1 if finding else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(2)

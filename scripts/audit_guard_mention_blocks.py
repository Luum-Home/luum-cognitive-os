#!/usr/bin/env python3
"""Cuenta los bloqueos de los guards de rutas y separa accion de mencion.

Lee los transcripts de Claude Code de ESTE proyecto, encuentra cada tool_result
que lleva el mensaje de bloqueo de `hooks/protected-config-write-guard.sh` o de
`~/.claude/hooks/block-destructive-bash.sh`, y recupera el tool_use que lo
provoco. Cada bloqueo queda clasificado en:

  destination  el destino es un argumento del tool (Edit/Write): no hay
               ambiguedad posible entre actuar y mencionar.
  bash         el veredicto salio del texto de un comando de Bash. Estos son
               los unicos donde cabe el falso positivo por mencion.

Para los de Bash el script REPLAYEA el comando contra el guard que hay hoy en
el arbol de trabajo, de modo que la salida distingue lo que ya se arreglo de lo
que sigue roto. El replay es read-only: el guard solo imprime y devuelve un
codigo de salida.

Exit codes: 0 sin bloqueos por mencion vigentes, 1 hay, 2 error.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

MARK_PROTECTED = "PROTECTED CONFIG WRITE GUARD: BLOCKED"
MARK_DESTRUCTIVE = "BLOCKED by block-destructive-bash"

REPO = Path(__file__).resolve().parents[1]
GUARD = REPO / "hooks" / "protected-config-write-guard.sh"


def transcript_dir(repo: Path) -> Path:
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(repo))
    return Path.home() / ".claude" / "projects" / slug


def iter_bash_uses(tdir: Path, since: float = 0.0):
    """Comandos de Bash que NO fueron bloqueados por el guard de config.

    La direccion contraria del problema: si el guard de HOY bloquea un comando
    que en su momento CORRIO, ese comando fue un falso negativo entonces.
    """
    for f in sorted(tdir.glob("*.jsonl")):
        if since and f.stat().st_mtime < since:
            continue
        blocked_ids: set[str] = set()
        uses: dict[str, dict] = {}
        try:
            lines = f.read_text(errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                obj = json.loads(line)
            except Exception:
                continue
            content = (obj.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for blk in content:
                if not isinstance(blk, dict):
                    continue
                if blk.get("type") == "tool_use" and blk.get("name") == "Bash":
                    cmd = (blk.get("input") or {}).get("command")
                    if cmd:
                        uses[blk.get("id", "")] = {"command": cmd, "session": f.stem}
                elif blk.get("type") == "tool_result":
                    txt = json.dumps(blk.get("content"))
                    if MARK_PROTECTED in txt:
                        blocked_ids.add(blk.get("tool_use_id", ""))
        for uid, row in uses.items():
            if uid not in blocked_ids:
                yield row


def iter_blocks(tdir: Path):
    """(guard, tool_name, tool_input, session) por cada bloqueo encontrado."""
    for f in sorted(tdir.glob("*.jsonl")):
        uses: dict[str, tuple[str, dict]] = {}
        try:
            lines = f.read_text(errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                obj = json.loads(line)
            except Exception:
                continue
            content = (obj.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for blk in content:
                if not isinstance(blk, dict):
                    continue
                if blk.get("type") == "tool_use":
                    uses[blk.get("id", "")] = (
                        blk.get("name", ""),
                        blk.get("input") or {},
                    )
                elif blk.get("type") == "tool_result":
                    txt = json.dumps(blk.get("content"))
                    if MARK_PROTECTED in txt:
                        guard = "protected-config-write-guard"
                    elif MARK_DESTRUCTIVE in txt:
                        guard = "block-destructive-bash"
                    else:
                        continue
                    name, tin = uses.get(blk.get("tool_use_id", ""), ("?", {}))
                    yield guard, name, tin, f.stem


def replay(command: str) -> tuple[int, str]:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    env = dict(os.environ)
    env.pop("COS_ALLOW_PROTECTED_CONFIG_WRITE", None)
    env["CLAUDE_PROJECT_DIR"] = str(REPO)
    proc = subprocess.run(
        ["/bin/bash", str(GUARD)],
        input=payload,
        text=True,
        capture_output=True,
        env=env,
        cwd=str(REPO),
    )
    return proc.returncode, (proc.stderr or "").strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="salida cruda por bloqueo")
    ap.add_argument("--no-replay", action="store_true")
    ap.add_argument(
        "--false-negatives",
        action="store_true",
        help="replaya los comandos que NO fueron bloqueados y lista los que el "
        "guard de hoy si bloquea (escrituras que se colaron en su momento)",
    )
    ap.add_argument("--since-days", type=float, default=3.0)
    args = ap.parse_args()

    tdir = transcript_dir(REPO)
    if not tdir.is_dir():
        print(f"ERROR: no hay transcripts en {tdir}", file=sys.stderr)
        return 2

    if args.false_negatives:
        import time

        since = time.time() - args.since_days * 86400
        seen: set[str] = set()
        total = 0
        leaked = []
        for row in iter_bash_uses(tdir, since):
            cmd = row["command"]
            if cmd in seen:
                continue
            seen.add(cmd)
            total += 1
            rc, err = replay(cmd)
            if rc == 2:
                leaked.append((err.splitlines()[1] if err else "", cmd))
        print(f"comandos Bash no bloqueados, distintos, ultimos {args.since_days}d: {total}")
        print(f"que el guard de HOY si bloquea (falsos negativos de entonces): {len(leaked)}")
        for why, cmd in leaked:
            print(f"  {why}")
            print(f"    {cmd[:200].replace(chr(10), ' | ')}")
        return 1 if leaked else 0

    rows = []
    for guard, tool, tin, session in iter_blocks(tdir):
        cmd = tin.get("command") if tool == "Bash" else None
        kind = "bash" if cmd else "destination"
        row = {
            "guard": guard,
            "tool": tool,
            "kind": kind,
            "session": session,
            "target": tin.get("file_path") or tin.get("path") or "",
            "command": cmd or "",
        }
        if cmd and not args.no_replay and guard == "protected-config-write-guard":
            rc, err = replay(cmd)
            row["replay_rc"] = rc
            row["replay_blocked"] = rc == 2
            row["replay_paths"] = err.splitlines()[1] if rc == 2 and err else ""
        rows.append(row)

    if args.json:
        for r in rows:
            print(json.dumps(r, ensure_ascii=False))
        return 0

    total = len(rows)
    by_guard: dict[str, int] = {}
    for r in rows:
        by_guard[r["guard"]] = by_guard.get(r["guard"], 0) + 1
    dest = [r for r in rows if r["kind"] == "destination"]
    bash = [r for r in rows if r["kind"] == "bash"]
    still = [r for r in bash if r.get("replay_blocked")]
    fixed = [r for r in bash if r.get("replay_blocked") is False]

    print(f"transcripts: {tdir}")
    print(f"bloqueos totales: {total}")
    for g, n in sorted(by_guard.items()):
        print(f"  {g}: {n}")
    print(f"por destino explicito (Edit/Write, sin ambiguedad): {len(dest)}")
    print(f"por texto de comando Bash: {len(bash)}")
    if not args.no_replay:
        print(f"  replay contra el guard de HOY -> sigue bloqueando: {len(still)}")
        print(f"  replay contra el guard de HOY -> ya pasa: {len(fixed)}")
        for r in still:
            print(f"    [BLOQUEA] {r['replay_paths']}")
            print(f"              {r['command'][:160].replace(chr(10), ' | ')}")
    return 1 if still else 0


if __name__ == "__main__":
    sys.exit(main())

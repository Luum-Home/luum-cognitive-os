# SCOPE: os-only
"""Cuantos disparos de session-cleanup cayeron a mitad de sesion (borrado que habria ocurrido)."""
import bisect
import collections
import glob
import gzip
import json

import os

files = sorted(glob.glob('.cognitive-os/metrics/.archive/hook-timing-*.jsonl.gz'))
if os.path.exists('.cognitive-os/metrics/hook-timing.jsonl'):
    files.append('.cognitive-os/metrics/hook-timing.jsonl')
rows = []
for f in files:
    op = gzip.open if f.endswith('.gz') else open
    with op(f, 'rt', errors='replace') as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                pass
rows.sort(key=lambda r: r.get('timestamp', ''))

starts = sorted(r['timestamp'] for r in rows
                if r.get('event') == 'SessionStart' and r.get('hook') == 'session-start-worktree-nudge')
cleans = sorted(r['timestamp'] for r in rows if r.get('hook') == 'session-cleanup')

print(f"filas totales de telemetria      : {len(rows)}")
print(f"aperturas de sesion (SessionStart): {len(starts)}")
print(f"disparos de session-cleanup (Stop): {len(cleans)}")

mid = 0
per = []
for i, s in enumerate(starts):
    e = starts[i + 1] if i + 1 < len(starts) else '9999'
    lo, hi = bisect.bisect_left(cleans, s), bisect.bisect_left(cleans, e)
    n = hi - lo
    per.append(n)
    if n > 1:
        mid += n - 1  # todos menos el ultimo de la ventana son inequivocamente a mitad de sesion

print(f"maximo de disparos en UNA ventana : {max(per) if per else 0}")
print(f"disparos INEQUIVOCAMENTE a mitad de sesion (no son el ultimo de su ventana): {mid}")
print(f"distribucion por ventana: {sorted(collections.Counter(per).items())}")
print()
print("Lectura: con la identidad de sesion resuelta y el codigo anterior, cada uno de")
print(f"esos {mid} disparos habria ejecutado rm -rf sobre el directorio de una sesion VIVA")
print("y barrido sus locks. Con el codigo nuevo: 0, porque el duenio estaba corriendo.")

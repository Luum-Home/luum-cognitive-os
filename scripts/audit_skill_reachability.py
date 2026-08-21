#!/usr/bin/env python3
"""Skill reachability audit: for each tracked SKILL.md, can anything invoke it?

Exit 0 = no unreachable, 1 = unreachable found, 2 = error.
Read-only. Produces JSON on stdout.
"""
import json, os, re, subprocess, sys
from pathlib import Path

# repo root: override with REPO=
# La raiz se deriva de __file__, no del cwd ni de una ruta hardcodeada. Un
# auditor anclado al cwd no falla ruidosamente: audita el arbol equivocado y sale
# limpio por vacio, que es la peor forma de pasar. Y una ruta absoluta de la
# maquina del autor filtra su usuario al repo -- el guard de privacidad la cazo.
ROOT = Path(os.environ.get("REPO") or Path(__file__).resolve().parent.parent)

def sh(cmd):
    return subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True).stdout

# ---------- universe: tracked SKILL.md ----------
tracked = [l for l in sh("git ls-files '**/SKILL.md'").splitlines()
           if l and 'node_modules' not in l and not l.startswith('.claude/plugins/')]
skills = {}
for rel in tracked:
    p = ROOT / rel
    name = p.parent.name
    skills.setdefault(name, []).append(rel)

# ---------- via A: harness projection (.claude/skills, .codex/skills, .opencode) ----------
def projection(dirpath):
    d = ROOT / dirpath
    out = {}
    if not d.is_dir():
        return out
    for e in d.iterdir():
        t = e / "SKILL.md"
        if t.exists():
            out[e.name] = os.path.realpath(t)
    return out

proj_claude = projection(".claude/skills")
proj_codex  = projection(".codex/skills")
proj_cos    = projection(".cognitive-os/skills")

# ---------- via B: skill router ----------
sys.path.insert(0, str(ROOT))
router_names, router_disk, router_catalog = set(), set(), set()
router_err = None
try:
    from cos_lib.skill_router import SkillRouter
    r = SkillRouter(project_root=ROOT)
    router_names = {e.skill_name for e in r.routing_table}
    router_disk = set(r._disk_skills)
    router_catalog = set(r.known_skills)
except Exception as ex:  # noqa
    router_err = f"{type(ex).__name__}: {ex}"

# ---------- via C: textual references outside its own dir ----------
REF_DIRS = ["rules", "hooks", "templates", "scripts", "manifests", "cos_lib",
            "lib", "docs/02-Decisions", "skills", "packages", ".claude/commands",
            "commands", "agents", ".claude/agents"]
existing = [d for d in REF_DIRS if (ROOT / d).exists()]
# one big grep -o pass; build an index name -> count of referencing files outside own dir
names = sorted(skills)
ref_files = {n: set() for n in names}
# grep for all names at once using -F with word-ish boundaries handled after
try:
    proc = subprocess.run(
        ["grep", "-rIoHE", r"(/|`|\b)(" + "|".join(re.escape(n) for n in names) + r")\b",
         "--"] + existing,
        cwd=ROOT, capture_output=True, text=True)
    for line in proc.stdout.splitlines():
        try:
            fpath, hit = line.split(":", 1)
        except ValueError:
            continue
        hit = hit.strip().lstrip("/`")
        if hit in ref_files:
            # ignore self-references (inside the skill's own directory)
            own = any(fpath.startswith(str(Path(rel).parent) + "/") for rel in skills[hit])
            if not own:
                ref_files[hit].add(fpath)
except Exception as ex:
    print(f"grep failed: {ex}", file=sys.stderr)

# ---------- via D: telemetry ----------
M = ROOT / ".cognitive-os" / "metrics"
tele = {n: {} for n in names}
def scan(fname, keys, bucket):
    p = M / fname
    if not p.exists():
        return
    for line in p.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        flat = {}
        def walk(d):
            if isinstance(d, dict):
                for k, v in d.items():
                    if isinstance(v, (dict, list)):
                        walk(v)
                    else:
                        flat.setdefault(k, []).append(v)
            elif isinstance(d, list):
                for v in d:
                    walk(v)
        walk(o)
        for k in keys:
            for v in flat.get(k, []):
                if isinstance(v, str):
                    v = v.strip().lstrip("/")
                    if v.endswith("/SKILL.md"):
                        v = Path(v).parent.name
                    if v in tele:
                        tele[v][bucket] = tele[v].get(bucket, 0) + 1

scan("skill-invocations.jsonl", ["skill_name","skill","name"], "invoked")
scan("skill-usage.jsonl",       ["skill_name","skill","name"], "used")
scan("skill-suggestion.jsonl",  ["skill_name","invoke_command","suggested_skill"], "suggested")
scan("skill-bypass.jsonl",      ["suggested_skill","skill_name"], "bypass")
scan("skill-metrics.jsonl",     ["skill"], "metrics")
scan("skill-feedback.jsonl",    ["skill"], "feedback")
scan("skill-routing.jsonl",     ["target_ref","skill"], "routing")
scan("primitive-interventions.jsonl", ["skill","skill_name","target_ref","primitive"], "interventions")

# ---------- classify ----------
rows = []
for n in names:
    vias = []
    if n in proj_claude: vias.append("claude-projection")
    if n in proj_codex:  vias.append("codex-projection")
    if n in proj_cos:    vias.append("cos-projection")
    if n in router_names: vias.append("router-table")
    if ref_files[n]:      vias.append(f"refs({len(ref_files[n])})")
    used = {k: v for k, v in tele[n].items() if v}
    if used and "telemetry" not in vias: vias.append("telemetry")
    # A *hard* via is one an agent can actually take: a harness projection
    # (Skill tool can load it) or a router-table entry (the prompt hook can
    # suggest it). A textual mention in a catalog/doc is NOT a hard via --
    # counting it as one is exactly how an audit reports "0 unreachable".
    hard = [v for v in vias if v.endswith("projection") or v == "router-table"]
    if not hard:
        bucket = "UNREACHABLE"
    elif used:
        bucket = "REACHABLE_USED"
    else:
        bucket = "REACHABLE_NO_USE"
    rows.append(dict(name=n, bucket=bucket, paths=skills[n], vias=vias,
                     telemetry=used, refs=sorted(ref_files[n])[:5],
                     ref_count=len(ref_files[n])))

out = dict(head=sh("git rev-parse --short HEAD").strip(),
           universe=len(names), tracked_files=len(tracked),
           router_error=router_err,
           router_table_size=len(router_names),
           router_disk=len(router_disk), catalog=len(router_catalog),
           proj_claude=len(proj_claude), proj_codex=len(proj_codex), proj_cos=len(proj_cos),
           rows=rows)
print(json.dumps(out, indent=1))
bad = [r for r in rows if r["bucket"] == "UNREACHABLE"]
sys.exit(1 if bad else 0)

#!/usr/bin/env python3
"""Prove the Channel-B / B-prime executable assertions can actually FAIL.

An assertion that has never been seen red is not evidence the sentence it
defends is true -- it is evidence the gate does not discriminate. That is not
hypothetical here: `tests_symlink_census` once certified "tests/ has ZERO
symlinks" in green while two lived there, because the probe reproduced the
non-recursive loop the sentence was written with.

So for every assertion this harness mutates REALITY in an isolated git worktree
-- a fourth symlink, a widened guard, a broken keyword gate -- and demands the
assertion turn red. It never mutates the probe to stop it finding its subject.

Control run first: an assertion already red in the worktree makes its
counterfactual meaningless, so the harness refuses to score it.

Read-only with respect to the working tree. Exit 0 = every assertion falsified,
1 = at least one could not be, 2 = the harness could not set up.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(
    subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=Path(__file__).resolve().parent,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
)
WT = Path(tempfile.gettempdir()) / "cos-channel-assertion-cf"

NEW = [
    "gotchas_channel_delivers_the_file",
    "cos_lib_directory_symlinks_match_the_prose",
    "toplevel_dir_symlink_is_not_caught",
    "efficiency_profile_tiers",
    "named_symlink_examples_still_hold",
    "plans_dir_split_still_holds",
]


def sh(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str), capture_output=True, text=True)


# ---- worktree ---------------------------------------------------------------
if WT.exists():
    sh(["git", "worktree", "remove", "--force", str(WT)], cwd=ROOT)
    shutil.rmtree(WT, ignore_errors=True)
r = sh(["git", "worktree", "add", "--detach", str(WT), "HEAD"], cwd=ROOT)
if r.returncode != 0:
    print(f"worktree add failed: {r.stderr}", file=sys.stderr)
    sys.exit(2)

# the worktree is at HEAD; carry in the two files this pass modified
for rel in ("manifests/documentation-truth-claims.yaml", "templates/project-gotchas.md"):
    shutil.copy2(ROOT / rel, WT / rel)
# .cognitive-os/ and .claude/settings.json may be untracked/ignored -- the delivery
# probe needs them, so mirror what the live repo has.
for rel in (".claude/settings.json", "cognitive-os.yaml"):
    src = ROOT / rel
    if src.exists() and not (WT / rel).exists():
        (WT / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, WT / rel)
if (ROOT / ".cognitive-os/plans").is_dir() and not (WT / ".cognitive-os/plans").exists():
    (WT / ".cognitive-os/plans").mkdir(parents=True, exist_ok=True)
    for p in (ROOT / ".cognitive-os/plans").iterdir():
        if p.is_file():
            shutil.copy2(p, WT / ".cognitive-os/plans" / p.name)

manifest = yaml.safe_load((WT / "manifests/documentation-truth-claims.yaml").read_text())
by_id = {a["id"]: a for a in manifest["claims"]["agent_channel_facts"]["executable_assertions"]}


CARRY = ("manifests/documentation-truth-claims.yaml", "templates/project-gotchas.md")


def restore():
    """git checkout reverts to HEAD, which does NOT have this pass's edits.
    Re-carry them, or the next assertion is scored against the old prose."""
    sh(["git", "checkout", "--", "."], cwd=WT)
    sh("git clean -fd -- cos_lib plans hooks scripts", cwd=WT)
    for rel in CARRY:
        shutil.copy2(ROOT / rel, WT / rel)


def run_assertion(aid):
    a = by_id[aid]
    p = subprocess.run(a["command"], cwd=str(WT), capture_output=True, text=True, timeout=120)
    return p.returncode, (p.stdout.strip() or p.stderr.strip())[:300]


# ---- mutations --------------------------------------------------------------
def mut_regex():
    """Break Channel B's keyword gate so the gotchas file stops being delivered."""
    f = WT / "hooks/inject-phase-context.sh"
    t = f.read_text()
    old = "grep -qiE 'lib/|hooks/|packages/|\\.cognitive-os/|settings\\.json|cognitive-os\\.yaml'"
    assert old in t, "keyword-gate anchor not found"
    f.write_text(t.replace(old, "grep -qiE 'zzz-no-such-keyword-zzz'", 1))
    return "hooks/inject-phase-context.sh: keyword gate no longer matches hooks/ or settings.json"


def mut_fourth_symlink():
    """A fourth cos_lib directory symlink lands; the prose still says three."""
    (WT / "cos_lib/newly_added_pkg").symlink_to("../packages/llm-providers/lib")
    return "cos_lib/newly_added_pkg -> ../packages/llm-providers/lib (a 4th directory symlink)"


def mut_widen_guard():
    """The guard is widened to catch top-level directory symlinks too."""
    f = WT / "hooks/symlink-mutation-guard.sh"
    t = f.read_text()
    lines = t.splitlines(keepends=True)
    i = next(n for n, l in enumerate(lines) if l.startswith("#!"))
    lines.insert(i + 1, 'case "${CLAUDE_TOOL_INPUT:-}$(cat 2>/dev/null)" in *"ln -s"*) exit 2;; esac\n')
    f.write_text("".join(lines))
    return "hooks/symlink-mutation-guard.sh: now blocks every `ln -s`, top-level included"


def mut_drop_tier():
    """A tier is removed from the driver's case arm; the prose still lists three."""
    f = WT / "scripts/apply-efficiency-profile.sh"
    t = f.read_text()
    assert "core|maintainer|full)" in t
    f.write_text(t.replace("core|maintainer|full)", "core|full)", 1))
    return "scripts/apply-efficiency-profile.sh: `maintainer` dropped from the case arm"


def mut_desymlink():
    """A packaging move turns a quoted symlink back into a regular file."""
    p = WT / "cos_lib/batch_runner.py"
    p.unlink()
    p.write_text("# now a regular file\n")
    return "cos_lib/batch_runner.py: symlink replaced by a regular file"


def mut_plans():
    """Someone drops a real plan back into the root plans/ directory."""
    (WT / "plans/REVIVED-PLAN.md").write_text("# a plan that is not a README\n")
    return "plans/REVIVED-PLAN.md created"


MUTATIONS = {
    "gotchas_channel_delivers_the_file": mut_regex,
    "cos_lib_directory_symlinks_match_the_prose": mut_fourth_symlink,
    "toplevel_dir_symlink_is_not_caught": mut_widen_guard,
    "efficiency_profile_tiers": mut_drop_tier,
    "named_symlink_examples_still_hold": mut_desymlink,
    "plans_dir_split_still_holds": mut_plans,
}

# ---- run --------------------------------------------------------------------
results = []
for aid in NEW:
    restore()
    code0, out0 = run_assertion(aid)
    if code0 != 0:
        results.append((aid, "CONTROL-RED", code0, out0, "", 0, ""))
        continue
    restore()
    desc = MUTATIONS[aid]()
    code1, out1 = run_assertion(aid)
    results.append((aid, "ok", code0, out0, desc, code1, out1))
    restore()

print("=" * 78)
ok = True
for aid, state, c0, o0, desc, c1, o1 in results:
    print(f"\n### {aid}")
    if state == "CONTROL-RED":
        ok = False
        print(f"  CONTROL FAILED (exit {c0}) -- counterfactual not scored: {o0}")
        continue
    print(f"  control    : exit {c0}  GREEN  | {o0}")
    print(f"  mutation   : {desc}")
    verdict = "RED (falsifiable)" if c1 != 0 else "STILL GREEN  <-- GATE DOES NOT DISCRIMINATE"
    if c1 == 0:
        ok = False
    print(f"  after mut. : exit {c1}  {verdict} | {o1}")
print("\n" + "=" * 78)
print("ALL SIX FALSIFIED" if ok else "SOME ASSERTIONS ARE NOT FALSIFIABLE -- see above")

sh(["git", "worktree", "remove", "--force", str(WT)], cwd=ROOT)
shutil.rmtree(WT, ignore_errors=True)
print("worktree removed")
sys.exit(0 if ok else 1)

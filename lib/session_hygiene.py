"""Session hygiene — auto-prune tasks, mark plans done, update CATALOG.md."""
from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def prune_completed_tasks(tasks_path: str, max_age_days: int = 7) -> dict:
    """Remove completed tasks older than max_age_days. Never prunes failed tasks.
    Returns {pruned, remaining, failed_kept}."""
    path = Path(tasks_path)
    if not path.exists():
        return {"pruned": 0, "remaining": 0, "failed_kept": 0}
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {"pruned": 0, "remaining": 0, "failed_kept": 0}

    now = datetime.now(tz=timezone.utc)
    kept, pruned, failed_kept = [], 0, 0
    for task in data.get("tasks", []):
        status = task.get("status", "")
        if status == "failed":
            failed_kept += 1
            kept.append(task)
            continue
        if status != "completed":
            kept.append(task)
            continue
        raw = task.get("completedAt") or task.get("completed_at")
        if not raw:
            kept.append(task)
            continue
        try:
            age = (now - datetime.fromisoformat(raw.replace("Z", "+00:00"))).days
            if age > max_age_days:
                pruned += 1
            else:
                kept.append(task)
        except (ValueError, TypeError):
            kept.append(task)

    data["tasks"] = kept
    _atomic_write(path, json.dumps(data, indent=2))
    return {"pruned": pruned, "remaining": len(kept), "failed_kept": failed_kept}


def mark_plan_completed(plan_path: str) -> bool:
    """Set plan Status to COMPLETED and add Completed date. Returns True if changed."""
    path = Path(plan_path)
    if not path.exists():
        return False
    try:
        content = path.read_text()
    except OSError:
        return False

    today = datetime.now().strftime("%Y-%m-%d")
    updated, changed = [], False
    for line in content.splitlines(keepends=True):
        if re.match(r"\*\*Status\*\*\s*:", line):
            if "COMPLETED" in line.upper():
                return False
            updated.append(re.sub(r"(:.*)", ": COMPLETED", line, count=1))
            updated.append(f"**Completed**: {today}\n")
            changed = True
        else:
            updated.append(line)

    if not changed:
        return False
    _atomic_write(path, "".join(updated))
    return True


def update_catalog(catalog_path: str, skills_dir: str) -> dict:
    """Add missing skills from skills_dir to CATALOG.md. Returns {added, total}."""
    catalog = Path(catalog_path)
    s_dir = Path(skills_dir)

    existing: set[str] = set()
    if catalog.exists():
        try:
            for m in re.finditer(r"-\s+\*\*([^*]+)\*\*", catalog.read_text()):
                existing.add(m.group(1).strip())
        except OSError:
            pass

    skill_files = sorted(s_dir.glob("*/SKILL.md")) if s_dir.exists() else []
    new_entries: list[tuple[str, str]] = []
    for sf in skill_files:
        try:
            text = sf.read_text()
        except OSError:
            continue
        name = _fm(text, "name") or sf.parent.name
        if name in existing:
            continue
        new_entries.append((name, _fm(text, "description") or "No description"))

    if not new_entries:
        return {"added": [], "total": len(existing)}

    lines = [f"- **{n}** — {d}\n" for n, d in sorted(new_entries)]
    try:
        cur = catalog.read_text() if catalog.exists() else ""
        _atomic_write(catalog, cur.rstrip("\n") + "\n" + "".join(lines))
    except OSError:
        return {"added": [], "total": len(existing)}

    return {"added": [n for n, _ in new_entries], "total": len(existing) + len(new_entries)}


def run_full_hygiene(project_root: str) -> str:
    """Run prune + catalog-update; return a human-readable summary."""
    root = Path(project_root)
    out = ["[session-hygiene]"]

    r = prune_completed_tasks(str(root / ".cognitive-os" / "tasks" / "active-tasks.json"))
    out.append(f"  tasks: pruned={r['pruned']} remaining={r['remaining']} failed_kept={r['failed_kept']}")

    c = update_catalog(str(root / "skills" / "CATALOG.md"), str(root / "skills"))
    if c["added"]:
        out.append(f"  catalog: added {len(c['added'])} skills: {', '.join(c['added'])}")
    else:
        out.append(f"  catalog: up-to-date ({c['total']} skills)")

    return "\n".join(out)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp_")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _fm(text: str, key: str) -> str | None:
    """Extract a key from YAML frontmatter (--- delimited)."""
    m = re.search(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return None
    km = re.search(rf"^{re.escape(key)}\s*:\s*(.+)$", m.group(1), re.MULTILINE)
    return km.group(1).strip().strip('"').strip("'") if km else None

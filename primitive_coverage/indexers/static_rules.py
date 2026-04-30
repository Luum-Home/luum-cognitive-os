from __future__ import annotations

from pathlib import Path

from .filesystem import read_text, repo_files
from primitive_coverage.model import PrimitiveRow


def build_corpus(root: Path) -> dict[str, str]:
    patterns = [
        "skills/**/SKILL.md",
        ".codex/skills/**/SKILL.md",
        "packages/**/skills/**/SKILL.md",
        "hooks/**/*.sh",
        "packages/**/hooks/**/*.sh",
        "rules/**/*.md",
        "scripts/**/*.py",
        "tests/**/*.py",
        "docs/**/*.md",
        ".github/workflows/*.yml",
        ".github/workflows/*.yaml",
        ".claude/**/*.json",
        "manifests/**/*.json",
        "README.md",
        "AGENTS.md",
        "cognitive-os.yaml",
    ]
    corpus: dict[str, str] = {}
    for path in repo_files(root, patterns):
        corpus[path.relative_to(root).as_posix()] = read_text(path)
    return corpus


def apply_static_signals(root: Path, row: PrimitiveRow, corpus: dict[str, str]) -> None:
    text = read_text(root / row.path)
    basename = Path(row.path).name
    stem = Path(row.path).stem
    needles = {row.path, basename, stem}
    if row.family == "skill":
        skill_name = Path(row.path).parent.name
        needles.update({skill_name, f"/{skill_name}"})
        row.signals["declared"] = "name:" in text[:500]
        row.signals["documented"] = "description:" in text[:800] and len(text.strip()) > 120
    elif row.family == "hook":
        row.signals["declared"] = text.startswith("#!") or basename.endswith(".sh")
        row.signals["documented"] = basename in "\n".join(v for k, v in corpus.items() if k.startswith("docs/"))
        settings = corpus.get(".claude/settings.json", "")
        row.signals["wired"] = basename in settings or row.path in settings
    elif row.family == "rule":
        row.signals["declared"] = True
        row.signals["documented"] = "Contextual Trigger" in text or "<!-- TIER:" in text
    elif row.family == "doc":
        row.signals["declared"] = True
        row.signals["documented"] = True
        row.signals["proof"] = "proof" in text.lower() or "test" in text.lower()
    elif row.family == "workflow":
        row.signals["declared"] = True
        row.signals["wired"] = "on:" in text
        row.signals["documented"] = True
    else:
        row.signals["declared"] = True

    consumers: list[str] = []
    literal_needles = [needle for needle in needles if needle and len(needle) > 2]
    if literal_needles:
        for rel, body in corpus.items():
            if rel == row.path:
                continue
            if any(needle in body for needle in literal_needles):
                consumers.append(rel)
    row.consumers = sorted(set(consumers))
    row.signals["referenced"] = bool(row.consumers)
    row.signals["tested"] = any(consumer.startswith("tests/") for consumer in row.consumers)
    row.signals["proof"] = row.signals.get("proof", False) or row.signals["tested"]
    row.proof_links.extend([consumer for consumer in row.consumers if consumer.startswith("tests/")])
    row.signals["owner"] = "owner:" in text[:1000] or "CODEOWNERS" in corpus
    row.signals["runtime_seen"] = any(
        consumer.startswith(".cognitive-os/metrics/") for consumer in row.consumers
    )

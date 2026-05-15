#!/usr/bin/env python3
# SCOPE: os-only
"""update_readme_badges.py — Generate shields.io badge JSON endpoints and update README.

Reads public-metrics-dogfood.json and public-metrics-aspirational.json,
writes per-badge shields.io JSON to .cognitive-os/metrics/badges/*.json,
updates README between <!-- BADGES:START --> and <!-- BADGES:END --> markers,
and appends one record to .cognitive-os/metrics/public-trend.jsonl.

Usage:
    uv run python3 scripts/update_readme_badges.py
    python3 scripts/update_readme_badges.py  (when deps already installed)
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
BADGES_DIR = REPO_ROOT / ".cognitive-os" / "metrics" / "badges"
TREND_LOG = REPO_ROOT / ".cognitive-os" / "metrics" / "public-trend.jsonl"
README = REPO_ROOT / "README.md"

DOGFOOD_JSON = REPO_ROOT / "public-metrics-dogfood.json"
ASPIRATIONAL_JSON = REPO_ROOT / "public-metrics-aspirational.json"

# Shields.io badge org/repo placeholder — operator substitutes before push.
BADGE_ORG_REPO = "<org>/<repo>"


# ── Color helpers ─────────────────────────────────────────────────────────────

def _color_dogfood(score: float) -> str:
    """Green ≥75, yellow 50-74, red <50."""
    if score >= 75:
        return "brightgreen"
    if score >= 50:
        return "yellow"
    return "red"


def _color_real(pct: float) -> str:
    """Green ≥40%, yellow 25-40%, red <25%."""
    if pct >= 40:
        return "brightgreen"
    if pct >= 25:
        return "yellow"
    return "red"


def _color_portability(score: float) -> str:
    """Green ≥80, yellow 50-80, red <50."""
    if score >= 80:
        return "brightgreen"
    if score >= 50:
        return "yellow"
    return "red"


def _color_hook_wiring(score: float) -> str:
    """Green ≥70, yellow 40-70, red <40."""
    if score >= 70:
        return "brightgreen"
    if score >= 40:
        return "yellow"
    return "red"


# ── Shields.io badge builder ──────────────────────────────────────────────────

def make_badge(label: str, message: str, color: str) -> dict:
    return {
        "schemaVersion": 1,
        "label": label,
        "message": message,
        "color": color,
    }


# ── Metrics extraction ────────────────────────────────────────────────────────

def load_dogfood() -> dict:
    if not DOGFOOD_JSON.exists():
        return {}
    with DOGFOOD_JSON.open() as f:
        return json.load(f)


def load_aspirational() -> dict:
    if not ASPIRATIONAL_JSON.exists():
        return {}
    with ASPIRATIONAL_JSON.open() as f:
        return json.load(f)


def extract_scores(dogfood: dict, aspirational: dict) -> dict[str, float]:
    """Return normalized metric values keyed by badge slug."""
    dims = dogfood.get("dimensions", {})

    dogfood_score = float(dogfood.get("overall", dogfood.get("score", 0.0)) or 0.0)

    # REAL component percentage from aspirational audit
    total = int(aspirational.get("total", 0))
    real_count = int(aspirational.get("counts", {}).get("REAL", 0))
    real_pct = (real_count / total * 100.0) if total > 0 else 0.0

    portability = float(dims.get("harness_portability", 0.0))
    hook_wiring = float(dims.get("hook_wiring", 0.0))

    return {
        "dogfood": dogfood_score,
        "real_pct": real_pct,
        "portability": portability,
        "hook_wiring": hook_wiring,
    }


# ── Badge generation ──────────────────────────────────────────────────────────

def generate_badges(scores: dict[str, float]) -> dict[str, dict]:
    """Return {slug: badge_dict} for all 4 public badges."""
    return {
        "dogfood": make_badge(
            label="dogfood",
            message=f"{scores['dogfood']:.1f}",
            color=_color_dogfood(scores["dogfood"]),
        ),
        "real-components": make_badge(
            label="real components",
            message=f"{scores['real_pct']:.1f}%",
            color=_color_real(scores["real_pct"]),
        ),
        "portability": make_badge(
            label="harness portability",
            message=f"{scores['portability']:.1f}",
            color=_color_portability(scores["portability"]),
        ),
        "hook-wiring": make_badge(
            label="hook wiring",
            message=f"{scores['hook_wiring']:.1f}",
            color=_color_hook_wiring(scores["hook_wiring"]),
        ),
    }


def write_badges(badges: dict[str, dict]) -> None:
    BADGES_DIR.mkdir(parents=True, exist_ok=True)
    for slug, badge in badges.items():
        path = BADGES_DIR / f"{slug}.json"
        with path.open("w") as f:
            json.dump(badge, f, indent=2)
            f.write("\n")
        try:
            display = path.relative_to(REPO_ROOT)
        except ValueError:
            display = path
        print(f"  badge: {display}")


# ── README badge block ────────────────────────────────────────────────────────

def _badge_url(slug: str) -> str:
    raw_url = (
        f"https://raw.githubusercontent.com/{BADGE_ORG_REPO}/main"
        f"/.cognitive-os/metrics/badges/{slug}.json"
    )
    return f"https://img.shields.io/endpoint?url={raw_url}"


def _build_badge_block(badges: dict[str, dict]) -> str:
    lines = ["<!-- BADGES:START -->"]
    labels = {
        "dogfood": "Dogfood Score",
        "real-components": "REAL Components",
        "portability": "Harness Portability",
        "hook-wiring": "Hook Wiring",
    }
    for slug, badge in badges.items():
        label = labels.get(slug, slug)
        url = _badge_url(slug)
        lines.append(f"![{label}]({url})")
    lines.append("<!-- BADGES:END -->")
    return "\n".join(lines) + "\n"


def update_readme(badges: dict[str, dict]) -> bool:
    """Replace content between <!-- BADGES:START --> and <!-- BADGES:END --> in README.

    Returns True if the README was modified, False if markers were absent.
    """
    if not README.exists():
        print(f"  README not found at {README}; skipping badge injection")
        return False

    content = README.read_text(encoding="utf-8")
    start_marker = "<!-- BADGES:START -->"
    end_marker = "<!-- BADGES:END -->"

    if start_marker not in content:
        print(f"  README lacks {start_marker!r}; adding markers after first heading")
        # Insert badge block after the first heading line
        lines = content.splitlines(keepends=True)
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.startswith("#"):
                insert_idx = i + 1
                break
        badge_block = "\n" + _build_badge_block(badges) + "\n"
        lines.insert(insert_idx, badge_block)
        README.write_text("".join(lines), encoding="utf-8")
        return True

    new_block = _build_badge_block(badges)
    start_idx = content.index(start_marker)
    end_idx = content.index(end_marker, start_idx) + len(end_marker)
    # Include trailing newline if present
    if end_idx < len(content) and content[end_idx] == "\n":
        end_idx += 1

    new_content = content[:start_idx] + new_block + content[end_idx:]
    README.write_text(new_content, encoding="utf-8")
    return True


# ── Trend append ──────────────────────────────────────────────────────────────

def append_trend(scores: dict[str, float]) -> None:
    TREND_LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    record = {
        "timestamp": ts,
        "dogfood": scores["dogfood"],
        "real_pct": scores["real_pct"],
        "portability": scores["portability"],
        "hook_wiring": scores["hook_wiring"],
    }
    with TREND_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    try:
        display = TREND_LOG.relative_to(REPO_ROOT)
    except ValueError:
        display = TREND_LOG
    print(f"  trend: {display}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    print("update_readme_badges: loading metrics...")

    dogfood = load_dogfood()
    aspirational = load_aspirational()

    if not dogfood and not aspirational:
        print("  WARNING: both metric files missing — using zero scores")

    scores = extract_scores(dogfood, aspirational)
    print(f"  scores: dogfood={scores['dogfood']:.1f}  real={scores['real_pct']:.1f}%  "
          f"portability={scores['portability']:.1f}  hook-wiring={scores['hook_wiring']:.1f}")

    badges = generate_badges(scores)
    write_badges(badges)
    updated = update_readme(badges)
    if updated:
        print("  README badge block updated")
    append_trend(scores)
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

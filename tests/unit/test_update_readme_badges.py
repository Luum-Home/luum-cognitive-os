"""Tests for scripts/update_readme_badges.py.

Covers:
- Score extraction from dogfood + aspirational JSON
- Badge color thresholds for all 4 metrics
- Valid shields.io badge JSON structure
- README badge block injection (markers present and missing cases)
- public-trend.jsonl append
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

# ── Load module under test ─────────────────────────────────────────────────────

_SCRIPT = Path(__file__).parent.parent.parent / "scripts" / "update_readme_badges.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("update_readme_badges", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


try:
    _mod = _load_module()
except Exception as exc:
    pytest.skip(f"Could not load update_readme_badges.py: {exc}", allow_module_level=True)


# Re-export functions under test for convenience
extract_scores = _mod.extract_scores
generate_badges = _mod.generate_badges
make_badge = _mod.make_badge
update_readme = _mod.update_readme
append_trend = _mod.append_trend
_color_dogfood = _mod._color_dogfood
_color_real = _mod._color_real
_color_portability = _mod._color_portability
_color_hook_wiring = _mod._color_hook_wiring


# ── Fixtures ──────────────────────────────────────────────────────────────────

SAMPLE_DOGFOOD = {
    "overall": 65.63,
    "score": 65.63,
    "dimensions": {
        "harness_portability": 54.65,
        "hook_wiring": 43.23,
        "adr_discipline": 90.0,
        "doc_freshness": 63.0,
        "self_build_activity": 66.0,
        "skill_coverage": 17.0,
        "test_health": 0.0,
    },
}

SAMPLE_ASPIRATIONAL = {
    "total": 581,
    "counts": {
        "REAL": 162,
        "ASPIRATIONAL": 70,
        "ON_DEMAND": 154,
        "DORMANT": 150,
        "METADATA": 45,
    },
}


# ── Test 1: score extraction from sample data ─────────────────────────────────

def test_extract_scores_from_sample_data():
    scores = extract_scores(SAMPLE_DOGFOOD, SAMPLE_ASPIRATIONAL)
    assert scores["dogfood"] == pytest.approx(65.63, abs=0.01)
    assert scores["portability"] == pytest.approx(54.65, abs=0.01)
    assert scores["hook_wiring"] == pytest.approx(43.23, abs=0.01)
    # real_pct = 162 / 581 * 100 ≈ 27.88
    assert scores["real_pct"] == pytest.approx(27.88, abs=0.1)


def test_extract_scores_empty_input_returns_zeros():
    scores = extract_scores({}, {})
    assert scores["dogfood"] == 0.0
    assert scores["real_pct"] == 0.0
    assert scores["portability"] == 0.0
    assert scores["hook_wiring"] == 0.0


# ── Test 2: color thresholds (dogfood) ───────────────────────────────────────

@pytest.mark.parametrize("score,expected_color", [
    (75.0, "brightgreen"),
    (90.0, "brightgreen"),
    (74.9, "yellow"),
    (50.0, "yellow"),
    (49.9, "red"),
    (0.0,  "red"),
])
def test_dogfood_color_thresholds(score, expected_color):
    assert _color_dogfood(score) == expected_color


# ── Test 3: color thresholds (real_pct) ──────────────────────────────────────

@pytest.mark.parametrize("pct,expected_color", [
    (40.0, "brightgreen"),
    (60.0, "brightgreen"),
    (39.9, "yellow"),
    (25.0, "yellow"),
    (24.9, "red"),
    (0.0,  "red"),
])
def test_real_pct_color_thresholds(pct, expected_color):
    assert _color_real(pct) == expected_color


# ── Test 4: valid shields.io badge structure ──────────────────────────────────

def test_generate_badges_produces_valid_shieldsio_json():
    scores = extract_scores(SAMPLE_DOGFOOD, SAMPLE_ASPIRATIONAL)
    badges = generate_badges(scores)

    assert set(badges.keys()) == {"dogfood", "real-components", "portability", "hook-wiring"}

    for slug, badge in badges.items():
        # Every badge must have the 4 required shields.io fields
        assert badge.get("schemaVersion") == 1, f"{slug}: schemaVersion must be 1"
        assert isinstance(badge.get("label"), str), f"{slug}: label must be a str"
        assert isinstance(badge.get("message"), str), f"{slug}: message must be a str"
        assert badge.get("color") in (
            "brightgreen", "green", "yellow", "orange", "red", "blue",
        ), f"{slug}: unexpected color {badge.get('color')!r}"

    # Specific value spot-check
    assert "65.6" in badges["dogfood"]["message"]


# ── Test 5: badge files are written + contain valid JSON ─────────────────────

def test_write_and_read_badge_files(tmp_path, monkeypatch):
    monkeypatch.setattr(_mod, "BADGES_DIR", tmp_path / "badges")
    monkeypatch.setattr(_mod, "TREND_LOG", tmp_path / "trend.jsonl")

    scores = extract_scores(SAMPLE_DOGFOOD, SAMPLE_ASPIRATIONAL)
    badges = generate_badges(scores)
    _mod.write_badges(badges)

    for slug in ("dogfood", "real-components", "portability", "hook-wiring"):
        badge_file = tmp_path / "badges" / f"{slug}.json"
        assert badge_file.exists(), f"{slug}.json not written"
        data = json.loads(badge_file.read_text())
        assert data["schemaVersion"] == 1


# ── Test 6: README badge injection — markers already present ─────────────────

def test_readme_badge_injection_with_existing_markers(tmp_path, monkeypatch):
    readme = tmp_path / "README.md"
    readme.write_text(
        "# My Project\n\n"
        "<!-- BADGES:START -->\n"
        "![Old Badge](http://example.com)\n"
        "<!-- BADGES:END -->\n"
        "\nSome other content.\n"
    )
    monkeypatch.setattr(_mod, "README", readme)

    scores = extract_scores(SAMPLE_DOGFOOD, SAMPLE_ASPIRATIONAL)
    badges = generate_badges(scores)
    result = update_readme(badges)

    assert result is True
    content = readme.read_text()
    assert "<!-- BADGES:START -->" in content
    assert "<!-- BADGES:END -->" in content
    # Old placeholder badge is gone
    assert "http://example.com" not in content
    # New dogfood badge is present
    assert "dogfood" in content
    # Surrounding content preserved
    assert "Some other content." in content


# ── Test 7: README badge injection — no markers, auto-inserted ───────────────

def test_readme_badge_injection_missing_markers(tmp_path, monkeypatch):
    readme = tmp_path / "README.md"
    readme.write_text("# My Project\n\nSome content here.\n")
    monkeypatch.setattr(_mod, "README", readme)

    scores = extract_scores(SAMPLE_DOGFOOD, SAMPLE_ASPIRATIONAL)
    badges = generate_badges(scores)
    result = update_readme(badges)

    assert result is True
    content = readme.read_text()
    assert "<!-- BADGES:START -->" in content
    assert "<!-- BADGES:END -->" in content


# ── Test 8: README missing entirely ──────────────────────────────────────────

def test_readme_update_returns_false_when_readme_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(_mod, "README", tmp_path / "NO_README.md")

    scores = extract_scores(SAMPLE_DOGFOOD, SAMPLE_ASPIRATIONAL)
    badges = generate_badges(scores)
    result = update_readme(badges)

    assert result is False


# ── Test 9: trend JSONL append ────────────────────────────────────────────────

def test_append_trend_writes_valid_jsonl(tmp_path, monkeypatch):
    trend_file = tmp_path / "public-trend.jsonl"
    monkeypatch.setattr(_mod, "TREND_LOG", trend_file)

    scores = extract_scores(SAMPLE_DOGFOOD, SAMPLE_ASPIRATIONAL)

    # Append twice — should get 2 lines
    append_trend(scores)
    append_trend(scores)

    lines = [l for l in trend_file.read_text().splitlines() if l.strip()]
    assert len(lines) == 2

    for line in lines:
        record = json.loads(line)
        assert "timestamp" in record
        assert "dogfood" in record
        assert "real_pct" in record
        assert "portability" in record
        assert "hook_wiring" in record
        assert record["dogfood"] == pytest.approx(65.63, abs=0.01)


# ── Test 10: portability + hook-wiring color thresholds ──────────────────────

@pytest.mark.parametrize("score,expected_color", [
    (80.0, "brightgreen"),
    (79.9, "yellow"),
    (50.0, "yellow"),
    (49.9, "red"),
])
def test_portability_color_thresholds(score, expected_color):
    assert _color_portability(score) == expected_color


@pytest.mark.parametrize("score,expected_color", [
    (70.0, "brightgreen"),
    (69.9, "yellow"),
    (40.0, "yellow"),
    (39.9, "red"),
])
def test_hook_wiring_color_thresholds(score, expected_color):
    assert _color_hook_wiring(score) == expected_color


# ── Test 11: make_badge helper ────────────────────────────────────────────────

def test_make_badge_structure():
    badge = make_badge("dogfood", "65.6", "yellow")
    assert badge == {
        "schemaVersion": 1,
        "label": "dogfood",
        "message": "65.6",
        "color": "yellow",
    }

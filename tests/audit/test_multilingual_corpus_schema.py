"""Schema-only audit of the multilingual benchmark corpus (REQ-005, OBJ-2).

FastEmbed-free: parses YAML and asserts structural invariants without
loading any embedding model. Runs on every CI invocation so the corpus
cannot rot silently between warm-runner benchmark runs.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml


CORPUS_PATH = (
    Path(__file__).resolve().parents[2]
    / "manifests"
    / "routing-benchmark-corpus-multilingual.yaml"
)


def _load() -> dict:
    with CORPUS_PATH.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


REQUIRED_COVERAGE = [
    ("add-hook", "es"),
    ("code-review", "es"),
    ("run-tests", "es"),
    ("run-tests", "de"),
    ("repo-forensics", "pt"),
    ("add-rule", "fr"),
]


def test_schema_version() -> None:
    data = _load()
    assert data.get("schema_version") == "routing-benchmark-corpus/v1", data.get("schema_version")


def test_required_coverage_tuples() -> None:
    data = _load()
    skills = data.get("skills") or {}
    for skill, lang in REQUIRED_COVERAGE:
        assert skill in skills, f"missing skill: {skill}"
        prompts = skills[skill].get("prompts") or {}
        assert lang in prompts, f"missing lang {lang} in {skill}"
        assert len(prompts[lang]) >= 1, f"empty prompts for {skill}/{lang}"


def test_prompts_are_strings() -> None:
    data = _load()
    skills = data.get("skills") or {}
    for skill, body in skills.items():
        for lang, prompts in (body.get("prompts") or {}).items():
            assert isinstance(prompts, list), f"{skill}/{lang} prompts must be list"
            for p in prompts:
                assert isinstance(p, str), f"{skill}/{lang} prompt not str: {p!r}"
                assert p.strip(), f"{skill}/{lang} prompt empty"


def test_keys_sorted() -> None:
    data = _load()
    skills = list((data.get("skills") or {}).keys())
    assert skills == sorted(skills), f"skill keys not alphabetically sorted: {skills}"


def test_no_fastembed_import() -> None:
    # Schema loading must not import fastembed. The module may already be loaded
    # by another test when the suite runs in a shared interpreter, so assert
    # this test does not introduce it.
    had_fastembed = "fastembed" in sys.modules
    _load()
    assert ("fastembed" in sys.modules) == had_fastembed, (
        "schema loading imported fastembed"
    )

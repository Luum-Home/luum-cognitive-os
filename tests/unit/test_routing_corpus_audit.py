# SCOPE: os-only
from __future__ import annotations

import textwrap
from pathlib import Path

from scripts.routing_corpus_audit import audit_corpus


def _write_skill(root: Path, name: str, *, user_invocable: bool = True) -> None:
    path = root / "skills" / name
    path.mkdir(parents=True, exist_ok=True)
    user_line = "user-invocable: true\n" if user_invocable else ""
    (path / "SKILL.md").write_text(
        "---\n"
        f"name: {name}\n"
        f"description: Route {name} requests.\n"
        f"{user_line}"
        "triggers:\n"
        f"- /{name}\n"
        "---\n",
        encoding="utf-8",
    )


def test_corpus_audit_reports_coverage_and_uncovered_user_facing(tmp_path: Path) -> None:
    _write_skill(tmp_path, "run-tests")
    _write_skill(tmp_path, "code-review")
    corpus = tmp_path / "corpus.yaml"
    corpus.write_text(
        textwrap.dedent(
            """\
            schema_version: routing-benchmark-corpus/v1
            skills:
              run-tests:
                description: Run tests.
                prompts:
                  en: ["run the tests"]
                  es: ["run tests"]
            """
        ),
        encoding="utf-8",
    )
    report = audit_corpus(
        tmp_path,
        corpus,
        min_skills=1,
        min_prompts=2,
        min_languages=2,
        min_prompts_per_language=0,
        max_uncovered_user_facing=None,
    )
    assert report.corpus_skills == 1
    assert report.corpus_prompts == 2
    assert report.prompts_by_language["en"] == 1
    assert report.prompts_by_language["es"] == 1
    assert "code-review" in report.uncovered_user_facing_skills
    assert report.issue_count == 0


def test_corpus_audit_can_fail_on_uncovered_user_facing(tmp_path: Path) -> None:
    _write_skill(tmp_path, "run-tests")
    _write_skill(tmp_path, "code-review")
    corpus = tmp_path / "corpus.yaml"
    corpus.write_text(
        textwrap.dedent(
            """\
            schema_version: routing-benchmark-corpus/v1
            skills:
              run-tests:
                description: Run tests.
                prompts:
                  en: ["run the tests"]
            """
        ),
        encoding="utf-8",
    )
    report = audit_corpus(
        tmp_path,
        corpus,
        min_skills=1,
        min_prompts=1,
        min_languages=1,
        min_prompts_per_language=0,
        max_uncovered_user_facing=0,
    )
    assert report.issue_count == 1
    assert report.issues[0].code == "too-many-uncovered-user-facing-skills"

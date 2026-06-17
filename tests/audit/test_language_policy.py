from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.audit

REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = REPO_ROOT / "manifests" / "language-policy.yaml"
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _policy() -> dict:
    return yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))


def _skill_text(skill: str) -> str:
    path = REPO_ROOT / "skills" / skill / "SKILL.md"
    assert path.exists(), f"missing user-facing skill: {skill}"
    return path.read_text(encoding="utf-8")


def _frontmatter(text: str) -> dict:
    match = _FRONTMATTER_RE.match(text)
    assert match, "SKILL.md missing YAML frontmatter"
    return yaml.safe_load(match.group(1)) or {}


def test_language_policy_declares_english_native_multilingual_entrypoint_contract() -> None:
    policy = _policy()
    assert policy["schema_version"] == "cos.language-policy.v1"
    assert policy["policy"]["native_artifact_language"] == "en"
    assert policy["policy"]["conversational_entrypoint_languages"] == ["en", "es", "pt"]
    assert "localized JSON keys" in policy["policy"]["forbidden"]
    assert "full translated duplicate documentation" in policy["policy"]["forbidden"]


@pytest.mark.parametrize("skill", sorted(_policy()["user_facing_skills"]))
def test_user_facing_skills_keep_english_native_required_fields(skill: str) -> None:
    front = _frontmatter(_skill_text(skill))
    assert front.get("name") == skill
    description = str(front.get("description", ""))
    assert description, f"{skill} needs an English description"
    # Required public metadata remains English-native; aliases live in routing/triggers.
    assert not any(term in description.lower() for term in (" usar ", " usarlo ", " usarla ", " usar ", " usar quando "))


@pytest.mark.parametrize("skill, aliases", sorted(_policy()["user_facing_skills"].items()))
def test_user_facing_skills_have_spanish_and_portuguese_conversational_aliases(skill: str, aliases: dict[str, list[str]]) -> None:
    text = _skill_text(skill).lower()
    for language in ("es", "pt"):
        required = aliases[language]
        assert required, f"{skill} has no {language} alias contract"
        assert any(alias.lower() in text for alias in required), f"{skill} missing {language} conversational alias"


def test_no_translated_duplicate_documentation_trees() -> None:
    localized_suffixes = (".es.md", ".pt.md", ".es.mdx", ".pt.mdx")
    offenders = [
        path.relative_to(REPO_ROOT).as_posix()
        for root in (REPO_ROOT / "docs", REPO_ROOT / "rules")
        for path in root.rglob("*")
        if path.is_file() and path.name.endswith(localized_suffixes)
    ]
    assert not offenders, "translated duplicate docs are not allowed:\n" + "\n".join(offenders)


def test_projected_user_facing_skill_aliases_match_source() -> None:
    projection_roots = (
        REPO_ROOT / ".claude" / "skills",
        REPO_ROOT / ".codex" / "skills",
        REPO_ROOT / ".cognitive-os" / "skills",
        REPO_ROOT / ".cognitive-os" / "skills" / "cos",
    )
    for skill in _policy()["user_facing_skills"]:
        source = _skill_text(skill)
        checked = 0
        for root in projection_roots:
            projected = root / skill / "SKILL.md"
            if not projected.exists():
                continue
            checked += 1
            assert projected.read_text(encoding="utf-8") == source
        assert checked >= 1, f"{skill} has no projected SKILL.md surface"



def _tracked_structured_files() -> list[Path]:
    import subprocess

    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    files: list[Path] = []
    for line in result.stdout.splitlines():
        path = REPO_ROOT / line
        if not path.exists():
            continue
        rel = path.relative_to(REPO_ROOT)
        if rel.parts and rel.parts[0] in {".ai", "docs"}:
            # Generated overlays and large reports are covered by projection/ACC tests.
            continue
        if path.suffix in {".json", ".yaml", ".yml"} or path.name.endswith(".schema.json"):
            files.append(path)
    return files


def test_structural_json_yaml_keys_are_english_native() -> None:
    non_english_key = re.compile(
        r"(?i)(descripci[oó]n|configuraci[oó]n|ejemplo|salida|entrada|"
        r"comando|habilidad|usuario|configura[cç][aã]o|sa[ií]da|"
        r"usu[aá]rio|habilidade)"
    )
    findings: list[str] = []
    for path in _tracked_structured_files():
        rel = path.relative_to(REPO_ROOT)
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception:
            continue

        def walk(node: object, dotted: str = "") -> None:
            if isinstance(node, dict):
                for key, value in node.items():
                    key_path = f"{dotted}.{key}" if dotted else str(key)
                    if isinstance(key, str) and non_english_key.search(key):
                        findings.append(f"{rel}:{key_path}")
                    walk(value, key_path)
            elif isinstance(node, list):
                for item in node:
                    walk(item, dotted)

        walk(payload)
    assert not findings, "JSON/YAML structural keys must remain English-native:\n" + "\n".join(findings[:80])

"""Stack Skill Recommender — Map detected project stack to recommended skills.

Detects technologies from project files (package.json, go.mod, pyproject.toml,
Cargo.toml, config files) and recommends relevant skills to install.

Supports individual technology detection, combo detection (React + TypeScript),
and multiple skill sources (cos-builtin, skills.sh, community).

No external dependencies — stdlib only.

Usage:
    from lib.stack_skill_recommender import StackSkillRecommender

    recommender = StackSkillRecommender()
    recs = recommender.recommend("/path/to/project")
    print(recommender.format_recommendations(recs))
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional, Set, Tuple


@dataclass(frozen=True)
class SkillRecommendation:
    """A recommended skill for a detected technology."""

    skill_name: str
    reason: str  # e.g. "Your project uses React + TypeScript"
    source: str  # "cos-builtin" | "skills.sh" | "community"
    install_command: str  # "cos install @luum/..." or "npx skills add ..."
    priority: str  # "recommended" | "optional" | "suggested"


# ---------------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------------


def _read_json(path: Path) -> Optional[dict]:
    """Read a JSON file, returning None on failure."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def _file_exists(project: Path, name: str) -> bool:
    """Check if a file exists in the project root."""
    return (project / name).is_file()


def _any_file_exists(project: Path, names: List[str]) -> bool:
    """Check if any of the given files exist."""
    return any(_file_exists(project, n) for n in names)


def _has_dependency(pkg_json: Optional[dict], dep_name: str) -> bool:
    """Check if a dependency exists in package.json (deps or devDeps)."""
    if pkg_json is None:
        return False
    deps = pkg_json.get("dependencies", {})
    dev_deps = pkg_json.get("devDependencies", {})
    return dep_name in deps or dep_name in dev_deps


def _read_first_line_containing(path: Path, keyword: str) -> bool:
    """Check if a file contains a line with the given keyword."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if keyword in line:
                    return True
    except (OSError, UnicodeDecodeError):
        pass
    return False


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class StackSkillRecommender:
    """Detect project stack and recommend skills to install."""

    # Individual technology -> skill recommendations
    STACK_SKILLS_MAP: Dict[str, List[SkillRecommendation]] = {
        # ── Languages ─────────────────────────────────────────────
        "go": [
            SkillRecommendation(
                "go-testing",
                "Go project detected",
                "cos-builtin",
                "/go-testing",
                "recommended",
            ),
        ],
        "typescript": [
            SkillRecommendation(
                "typescript-patterns",
                "TypeScript detected",
                "skills.sh",
                "npx skills add typescript",
                "recommended",
            ),
        ],
        "python": [
            SkillRecommendation(
                "test-driven-development",
                "Python project detected",
                "cos-builtin",
                "/test-driven-development",
                "recommended",
            ),
        ],
        "rust": [
            SkillRecommendation(
                "rust-patterns",
                "Rust project detected (Cargo.toml)",
                "skills.sh",
                "npx skills add rust",
                "optional",
            ),
        ],
        "java": [
            SkillRecommendation(
                "java-patterns",
                "Java/Gradle project detected",
                "skills.sh",
                "npx skills add java",
                "optional",
            ),
        ],
        # ── Frameworks ────────────────────────────────────────────
        "nextjs": [
            SkillRecommendation(
                "nextjs-patterns",
                "Next.js config found",
                "skills.sh",
                "npx skills add nextjs",
                "recommended",
            ),
        ],
        "react": [
            SkillRecommendation(
                "react-patterns",
                "React dependency found",
                "skills.sh",
                "npx skills add react",
                "optional",
            ),
        ],
        "vue": [
            SkillRecommendation(
                "vue-patterns",
                "Vue.js dependency found",
                "skills.sh",
                "npx skills add vue",
                "optional",
            ),
        ],
        "angular": [
            SkillRecommendation(
                "angular-patterns",
                "Angular dependency found",
                "skills.sh",
                "npx skills add angular",
                "optional",
            ),
        ],
        "svelte": [
            SkillRecommendation(
                "svelte-patterns",
                "Svelte config found",
                "skills.sh",
                "npx skills add svelte",
                "optional",
            ),
        ],
        "fastapi": [
            SkillRecommendation(
                "fastapi-patterns",
                "FastAPI dependency found",
                "skills.sh",
                "npx skills add fastapi",
                "optional",
            ),
        ],
        "django": [
            SkillRecommendation(
                "django-patterns",
                "Django dependency found",
                "skills.sh",
                "npx skills add django",
                "optional",
            ),
        ],
        "flask": [
            SkillRecommendation(
                "flask-patterns",
                "Flask dependency found",
                "skills.sh",
                "npx skills add flask",
                "optional",
            ),
        ],
        "nestjs": [
            SkillRecommendation(
                "nestjs-patterns",
                "NestJS dependency found",
                "skills.sh",
                "npx skills add nestjs",
                "recommended",
            ),
        ],
        "express": [
            SkillRecommendation(
                "express-patterns",
                "Express dependency found",
                "skills.sh",
                "npx skills add express",
                "optional",
            ),
        ],
        # ── Tools & infrastructure ────────────────────────────────
        "docker": [
            SkillRecommendation(
                "docker-patterns",
                "Dockerfile found",
                "skills.sh",
                "npx skills add docker",
                "optional",
            ),
        ],
        "tailwind": [
            SkillRecommendation(
                "tailwind-patterns",
                "Tailwind config found",
                "skills.sh",
                "npx skills add tailwind",
                "optional",
            ),
        ],
        "supabase": [
            SkillRecommendation(
                "supabase-patterns",
                "Supabase config found",
                "skills.sh",
                "npx skills add supabase",
                "optional",
            ),
        ],
        "prisma": [
            SkillRecommendation(
                "prisma-patterns",
                "Prisma schema found",
                "skills.sh",
                "npx skills add prisma",
                "optional",
            ),
        ],
        "terraform": [
            SkillRecommendation(
                "terraform-patterns",
                "Terraform files found",
                "skills.sh",
                "npx skills add terraform",
                "optional",
            ),
        ],
    }

    # Combo detection — specific skill recommendations for technology combos
    COMBO_MAP: Dict[FrozenSet[str], List[SkillRecommendation]] = {
        frozenset(["react", "typescript"]): [
            SkillRecommendation(
                "react-typescript",
                "React + TypeScript combo detected",
                "skills.sh",
                "npx skills add react-typescript",
                "recommended",
            ),
        ],
        frozenset(["nextjs", "supabase"]): [
            SkillRecommendation(
                "nextjs-supabase",
                "Next.js + Supabase stack detected",
                "skills.sh",
                "npx skills add nextjs-supabase",
                "suggested",
            ),
        ],
        frozenset(["nextjs", "tailwind"]): [
            SkillRecommendation(
                "nextjs-tailwind",
                "Next.js + Tailwind combo detected",
                "skills.sh",
                "npx skills add nextjs-tailwind",
                "suggested",
            ),
        ],
        frozenset(["python", "fastapi"]): [
            SkillRecommendation(
                "fastapi-full",
                "Python + FastAPI stack detected",
                "skills.sh",
                "npx skills add fastapi",
                "recommended",
            ),
        ],
        frozenset(["go", "docker"]): [
            SkillRecommendation(
                "go-docker",
                "Go + Docker stack detected",
                "skills.sh",
                "npx skills add go-docker",
                "suggested",
            ),
        ],
    }

    def detect_stack(self, project_path: str) -> Set[str]:
        """Detect technologies from project files.

        Checks: package.json, go.mod, pyproject.toml, Cargo.toml,
        requirements.txt, config files (next.config.*, tailwind.config.*, etc.),
        Dockerfile, docker-compose.yml, and more.

        Returns a set of technology identifiers (lowercase strings).
        """
        root = Path(project_path)
        if not root.is_dir():
            return set()

        detected: Set[str] = set()
        pkg_json = _read_json(root / "package.json")

        # ── Languages ─────────────────────────────────────────────
        if _file_exists(root, "go.mod"):
            detected.add("go")

        if _file_exists(root, "tsconfig.json") or _file_exists(root, "tsconfig.base.json"):
            detected.add("typescript")

        if _any_file_exists(root, ["pyproject.toml", "setup.py", "setup.cfg", "requirements.txt"]):
            detected.add("python")

        if _file_exists(root, "Cargo.toml"):
            detected.add("rust")

        if _any_file_exists(root, ["build.gradle", "build.gradle.kts", "pom.xml"]):
            detected.add("java")

        # ── Node.js frameworks (require package.json) ─────────────
        if pkg_json is not None:
            if _has_dependency(pkg_json, "react") or _has_dependency(pkg_json, "react-dom"):
                detected.add("react")

            if _has_dependency(pkg_json, "vue"):
                detected.add("vue")

            if _has_dependency(pkg_json, "@angular/core"):
                detected.add("angular")

            if _has_dependency(pkg_json, "svelte") or _file_exists(root, "svelte.config.js"):
                detected.add("svelte")

            if _has_dependency(pkg_json, "next") or _any_file_exists(
                root, ["next.config.js", "next.config.mjs", "next.config.ts"]
            ):
                detected.add("nextjs")

            if _has_dependency(pkg_json, "@nestjs/core"):
                detected.add("nestjs")

            if _has_dependency(pkg_json, "express"):
                detected.add("express")

            if _has_dependency(pkg_json, "@supabase/supabase-js"):
                detected.add("supabase")

            if _has_dependency(pkg_json, "prisma") or _has_dependency(pkg_json, "@prisma/client"):
                detected.add("prisma")

        # ── Config-file-based detection ───────────────────────────
        if _any_file_exists(
            root,
            ["next.config.js", "next.config.mjs", "next.config.ts"],
        ):
            detected.add("nextjs")

        if _any_file_exists(
            root,
            [
                "tailwind.config.js",
                "tailwind.config.ts",
                "tailwind.config.cjs",
                "tailwind.config.mjs",
            ],
        ):
            detected.add("tailwind")

        if _file_exists(root, "supabase") and (root / "supabase").is_dir():
            detected.add("supabase")

        if _file_exists(root, "schema.prisma") or _any_file_exists(
            root, ["prisma/schema.prisma"]
        ):
            detected.add("prisma")

        # ── Python frameworks ─────────────────────────────────────
        if "python" in detected:
            # Check pyproject.toml or requirements.txt for frameworks
            for check_file in ["pyproject.toml", "requirements.txt", "setup.cfg"]:
                fpath = root / check_file
                if fpath.is_file():
                    if _read_first_line_containing(fpath, "fastapi"):
                        detected.add("fastapi")
                    if _read_first_line_containing(fpath, "django"):
                        detected.add("django")
                    if _read_first_line_containing(fpath, "flask"):
                        detected.add("flask")

        # ── Infrastructure ────────────────────────────────────────
        if _any_file_exists(
            root, ["Dockerfile", "docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"]
        ):
            detected.add("docker")

        if _any_file_exists(root, ["main.tf", "terraform.tf"]):
            detected.add("terraform")

        return detected

    def recommend_for_stack(self, detected: Set[str]) -> List[SkillRecommendation]:
        """Given a set of detected technologies, return skill recommendations.

        Includes both individual technology skills and combo skills.
        Deduplicates by skill_name (first occurrence wins).
        """
        seen_skills: Set[str] = set()
        recommendations: List[SkillRecommendation] = []

        def _add(rec: SkillRecommendation) -> None:
            if rec.skill_name not in seen_skills:
                seen_skills.add(rec.skill_name)
                recommendations.append(rec)

        # Combo recommendations first (higher specificity)
        frozen_detected = frozenset(detected)
        for combo_key, combo_recs in self.COMBO_MAP.items():
            if combo_key.issubset(frozen_detected):
                for rec in combo_recs:
                    _add(rec)

        # Individual technology recommendations
        for tech in sorted(detected):
            for rec in self.STACK_SKILLS_MAP.get(tech, []):
                _add(rec)

        # Sort: recommended first, then optional, then suggested
        priority_order = {"recommended": 0, "optional": 1, "suggested": 2}
        recommendations.sort(key=lambda r: priority_order.get(r.priority, 9))

        return recommendations

    def recommend(self, project_path: str) -> List[SkillRecommendation]:
        """Detect stack and return skill recommendations.

        This is the main entry point: detect -> recommend.
        """
        detected = self.detect_stack(project_path)
        return self.recommend_for_stack(detected)

    def format_recommendations(self, recs: List[SkillRecommendation]) -> str:
        """Format recommendations for display.

        Returns a human-readable string with grouped recommendations
        and install commands.
        """
        if not recs:
            return "No skill recommendations for this project."

        # Collect detected techs from reasons
        lines: List[str] = []

        # Group by priority
        by_priority: Dict[str, List[SkillRecommendation]] = {}
        for rec in recs:
            by_priority.setdefault(rec.priority, []).append(rec)

        lines.append("Recommended skills for your project:\n")

        for priority in ["recommended", "optional", "suggested"]:
            group = by_priority.get(priority, [])
            if not group:
                continue
            for rec in group:
                tag = f"[{rec.priority}]"
                lines.append(f"  {tag:14s} {rec.skill_name} — {rec.reason}")

        # Collect external install commands
        external_cmds = [
            rec.install_command
            for rec in recs
            if rec.source != "cos-builtin" and not rec.install_command.startswith("/")
        ]
        if external_cmds:
            lines.append("")
            lines.append("Install external skills with:")
            for cmd in dict.fromkeys(external_cmds):  # deduplicate, preserve order
                lines.append(f"  {cmd}")

        # Collect builtin invocations
        builtin_cmds = [
            rec.install_command
            for rec in recs
            if rec.source == "cos-builtin"
        ]
        if builtin_cmds:
            lines.append("")
            lines.append("Built-in skills (invoke directly):")
            for cmd in dict.fromkeys(builtin_cmds):
                lines.append(f"  {cmd}")

        return "\n".join(lines)

"""Behavior tests for COS Dashboard scaffold (Phase 1 MVP)."""

from pathlib import Path

import pytest
import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class TestDashboardScaffold:
    """Verify the dashboard scaffold files exist and are well-formed."""

    def test_package_json_exists(self):
        pkg = PROJECT_ROOT / "dashboard" / "package.json"
        assert pkg.exists(), "dashboard/package.json must exist"

    def test_package_json_has_required_scripts(self):
        import json

        pkg = PROJECT_ROOT / "dashboard" / "package.json"
        data = json.loads(pkg.read_text())
        scripts = data.get("scripts", {})
        assert "dev" in scripts, "package.json must have a dev script"
        assert "build" in scripts, "package.json must have a build script"
        assert "start" in scripts, "package.json must have a start script"

    def test_package_json_has_next_dependency(self):
        import json

        pkg = PROJECT_ROOT / "dashboard" / "package.json"
        data = json.loads(pkg.read_text())
        deps = data.get("dependencies", {})
        assert "next" in deps, "package.json must depend on next"
        assert "react" in deps, "package.json must depend on react"

    def test_layout_tsx_exists(self):
        layout = PROJECT_ROOT / "dashboard" / "app" / "layout.tsx"
        assert layout.exists(), "dashboard/app/layout.tsx must exist"

    def test_page_tsx_exists(self):
        page = PROJECT_ROOT / "dashboard" / "app" / "page.tsx"
        assert page.exists(), "dashboard/app/page.tsx must exist"

    def test_rules_page_exists(self):
        rules = PROJECT_ROOT / "dashboard" / "app" / "rules" / "page.tsx"
        assert rules.exists(), "dashboard/app/rules/page.tsx must exist"

    def test_skills_page_exists(self):
        skills = PROJECT_ROOT / "dashboard" / "app" / "skills" / "page.tsx"
        assert skills.exists(), "dashboard/app/skills/page.tsx must exist"

    def test_dockerfile_exists(self):
        dockerfile = PROJECT_ROOT / "dashboard" / "Dockerfile"
        assert dockerfile.exists(), "dashboard/Dockerfile must exist"

    def test_dockerfile_exposes_port_3300(self):
        dockerfile = PROJECT_ROOT / "dashboard" / "Dockerfile"
        content = dockerfile.read_text()
        assert "3300" in content, "Dockerfile must reference port 3300"

    def test_docker_compose_has_cos_dashboard_service(self):
        compose_file = PROJECT_ROOT / "docker-compose.cognitive-os.yml"
        assert compose_file.exists(), "docker-compose.cognitive-os.yml must exist"
        content = compose_file.read_text()
        assert "cos-dashboard:" in content, (
            "docker-compose must contain cos-dashboard service"
        )

    def test_docker_compose_cos_dashboard_has_ui_profile(self):
        compose_file = PROJECT_ROOT / "docker-compose.cognitive-os.yml"
        content = compose_file.read_text()
        # Find the cos-dashboard service block and check it has ui profile
        in_dashboard = False
        found_ui_profile = False
        for line in content.splitlines():
            if "cos-dashboard:" in line:
                in_dashboard = True
                continue
            if in_dashboard:
                # Another top-level service starts
                if line and not line[0].isspace() and ":" in line:
                    break
                if "- ui" in line:
                    found_ui_profile = True
                    break
        assert found_ui_profile, "cos-dashboard service must have ui profile"

    def test_cos_api_module_exists(self):
        api = PROJECT_ROOT / "dashboard" / "lib" / "cos-api.ts"
        assert api.exists(), "dashboard/lib/cos-api.ts must exist"

    def test_sidebar_component_exists(self):
        sidebar = PROJECT_ROOT / "dashboard" / "components" / "sidebar.tsx"
        assert sidebar.exists(), "dashboard/components/sidebar.tsx must exist"

    def test_stat_card_component_exists(self):
        stat = PROJECT_ROOT / "dashboard" / "components" / "stat-card.tsx"
        assert stat.exists(), "dashboard/components/stat-card.tsx must exist"

    def test_globals_css_exists(self):
        css = PROJECT_ROOT / "dashboard" / "app" / "globals.css"
        assert css.exists(), "dashboard/app/globals.css must exist"

    def test_tsconfig_exists(self):
        tsconfig = PROJECT_ROOT / "dashboard" / "tsconfig.json"
        assert tsconfig.exists(), "dashboard/tsconfig.json must exist"

    def test_next_config_exists(self):
        config = PROJECT_ROOT / "dashboard" / "next.config.ts"
        assert config.exists(), "dashboard/next.config.ts must exist"

    def test_gitignore_exists(self):
        gitignore = PROJECT_ROOT / "dashboard" / ".gitignore"
        assert gitignore.exists(), "dashboard/.gitignore must exist"

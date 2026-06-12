from pathlib import Path
import importlib.util
import sys

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "dod_check",
    ROOT / "packages" / "quality-gates" / "skills" / "dod-check" / "scripts" / "check_dod.py",
)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


def test_classify_critical_for_release_or_version() -> None:
    assert module.classify(["VERSION", "cmd/cos/VERSION"]) == "critical"


def test_recommends_hook_syntax_for_hook_changes() -> None:
    assert module.recommended_command(["hooks/example.sh"]) == "bash -n hooks/example.sh"


def test_hygiene_blocks_secret_paths() -> None:
    checks = {check.name: check for check in module.check_hygiene(["secrets/token.txt"])}
    assert checks["blocked_paths_absent"].status == "FAIL"


def test_infers_backend_profile_from_api_and_service_paths() -> None:
    profiles = module.infer_dod_profiles([
        "src/app/api/orders/route.ts",
        "src/features/orders/services/orders.service.ts",
    ])
    assert "backend-api" in profiles


def test_infers_frontend_component_and_storybook_profiles() -> None:
    profiles = module.infer_dod_profiles([
        "src/features/orders/components/order-list.tsx",
        "src/ui/dialogs/confirm-dialog.tsx",
        "src/stories/dialogs/confirm-dialog.stories.tsx",
        "src/stories/dialogs/confirm-dialog.mdx",
    ])
    assert "frontend-feature" in profiles
    assert "ui-component" in profiles
    assert "storybook-docs" in profiles


def test_markdown_reports_dod_profiles() -> None:
    report = module.Report(
        verdict="PASS",
        complexity="medium",
        changed_files=["src/ui/button.tsx"],
        dod_profiles=["ui-component"],
        stack_signals=["node", "react", "typescript"],
        recommended_command="git diff --check",
        checks=[module.Check("dod_profiles", "PASS", "ui-component")],
    )
    rendered = module.markdown(report)
    assert "DoD profiles: ui-component" in rendered
    assert "Stack signals: node, react, typescript" in rendered


def test_detects_node_next_storybook_stack_signals(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        '{"dependencies":{"next":"1.0.0","react":"1.0.0","@storybook/nextjs":"1.0.0"},'
        '"devDependencies":{"vitest":"1.0.0","typescript":"1.0.0"}}',
        encoding="utf-8",
    )
    (tmp_path / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n", encoding="utf-8")
    (tmp_path / "tsconfig.json").write_text("{}", encoding="utf-8")
    (tmp_path / ".storybook").mkdir()

    signals = module.detect_stack_signals(tmp_path)

    assert {"node", "nextjs", "react", "storybook", "typescript", "vitest", "pnpm"}.issubset(signals)


def test_detects_python_fastapi_pytest_stack_signals(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\ndependencies = ["fastapi", "pytest", "ruff", "mypy"]\n',
        encoding="utf-8",
    )

    signals = module.detect_stack_signals(tmp_path)

    assert {"python", "fastapi", "pytest", "ruff", "mypy"}.issubset(signals)

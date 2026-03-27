"""Unit tests for lib/domain_router.py

Validates domain detection from file paths, evaluator config retrieval,
and verify context formatting.
"""

import pytest

from lib.domain_router import (
    detect_domain,
    format_verify_context,
    get_evaluator_config,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# detect_domain
# ---------------------------------------------------------------------------

class TestDetectDomain:
    """Tests for detect_domain()."""

    def test_empty_list_returns_mixed(self):
        assert detect_domain([]) == "mixed"

    def test_single_backend_file(self):
        assert detect_domain(["internal/users/service.go"]) == "backend"

    def test_single_frontend_file(self):
        assert detect_domain(["src/components/Button.tsx"]) == "frontend"

    def test_single_infrastructure_file(self):
        assert detect_domain(["docker-compose.yml"]) == "infrastructure"

    def test_single_database_file(self):
        assert detect_domain(["db/migrations/001_create_users.sql"]) == "database"

    def test_single_security_file(self):
        assert detect_domain(["internal/auth/middleware.go"]) == "security"

    def test_single_api_file(self):
        assert detect_domain(["internal/api/handlers/user.go"]) == "api"

    def test_majority_vote_backend(self):
        files = [
            "internal/services/user.go",
            "internal/services/order.go",
            "internal/domain/entities/user.go",
            "src/components/Button.tsx",
        ]
        # 2 backend + 1 database (entities) + 1 frontend -> backend has most after security check
        # Actually entities -> database, services -> backend (2), components -> frontend (1)
        # backend wins with 2
        result = detect_domain(files)
        assert result == "backend"

    def test_security_takes_priority(self):
        """Security domain should always win if any security files are present."""
        files = [
            "internal/services/user.go",
            "internal/services/order.go",
            "internal/auth/jwt.go",
        ]
        assert detect_domain(files) == "security"

    def test_frontend_by_extension(self):
        files = [
            "app/Header.tsx",
            "app/Footer.tsx",
            "app/Sidebar.vue",
        ]
        assert detect_domain(files) == "frontend"

    def test_infrastructure_dockerfile(self):
        files = ["services/api/Dockerfile"]
        assert detect_domain(files) == "infrastructure"

    def test_infrastructure_env_file(self):
        files = [".env.production"]
        assert detect_domain(files) == "infrastructure"

    def test_database_sql_by_extension(self):
        files = ["queries/get_user.sql", "queries/list_orders.sql"]
        assert detect_domain(files) == "database"

    def test_api_openapi_spec(self):
        files = ["docs/openapi.yaml"]
        assert detect_domain(files) == "api"

    def test_api_controllers(self):
        files = [
            "internal/controllers/user_controller.go",
            "internal/controllers/order_controller.go",
        ]
        assert detect_domain(files) == "api"

    def test_api_routes(self):
        files = ["src/routes/users.ts", "src/routes/orders.ts"]
        assert detect_domain(files) == "api"

    def test_mixed_when_tie(self):
        files = [
            "internal/services/user.go",  # backend
            "src/components/Button.tsx",   # frontend
        ]
        assert detect_domain(files) == "mixed"

    def test_unclassifiable_files_return_mixed(self):
        files = ["README.md", "LICENSE", "CHANGELOG.md"]
        assert detect_domain(files) == "mixed"

    def test_proto_files_are_api(self):
        files = ["proto/user/v1/user.proto"]
        assert detect_domain(files) == "api"

    def test_graphql_is_api(self):
        files = ["src/graphql/schema.ts", "src/graphql/resolvers.ts"]
        assert detect_domain(files) == "api"

    def test_terraform_is_infrastructure(self):
        files = ["infra/main.tf", "infra/variables.tf"]
        assert detect_domain(files) == "infrastructure"

    def test_helm_is_infrastructure(self):
        files = ["helm/chart/values.yaml"]
        assert detect_domain(files) == "infrastructure"

    def test_kubernetes_is_infrastructure(self):
        files = ["k8s/deployment.yaml", "k8s/service.yaml"]
        assert detect_domain(files) == "infrastructure"

    def test_github_actions_is_infrastructure(self):
        files = [".github/workflows/ci.yml"]
        assert detect_domain(files) == "infrastructure"

    def test_repositories_are_database(self):
        files = [
            "internal/repositories/user_repo.go",
            "internal/repositories/order_repo.go",
        ]
        assert detect_domain(files) == "database"

    def test_seeds_are_database(self):
        files = ["db/seeds/001_initial_data.sql"]
        assert detect_domain(files) == "database"

    def test_rbac_is_security(self):
        files = ["internal/rbac/policy.go"]
        assert detect_domain(files) == "security"

    def test_oauth_is_security(self):
        files = ["internal/oauth/provider.go"]
        assert detect_domain(files) == "security"

    def test_backslash_paths_normalized(self):
        files = ["internal\\services\\user.go"]
        assert detect_domain(files) == "backend"

    def test_mixed_extensions_only(self):
        """When files have only extension hints with a tie, return mixed."""
        files = ["file1.tsx", "file2.sql"]
        assert detect_domain(files) == "mixed"


# ---------------------------------------------------------------------------
# get_evaluator_config
# ---------------------------------------------------------------------------

class TestGetEvaluatorConfig:
    """Tests for get_evaluator_config()."""

    @pytest.mark.parametrize("domain", [
        "backend", "frontend", "infrastructure", "database", "security", "api",
    ])
    def test_known_domains_return_config(self, domain):
        config = get_evaluator_config(domain)
        assert config["domain"] == domain
        assert "display_name" in config
        assert "focus_areas" in config
        assert len(config["focus_areas"]) > 0
        assert "evaluation_criteria" in config
        assert "verification_commands" in config
        assert "red_flags" in config

    def test_mixed_domain_returns_default(self):
        config = get_evaluator_config("mixed")
        assert config["domain"] == "mixed"
        assert config["display_name"] == "Mixed / General"

    def test_unknown_domain_returns_default(self):
        config = get_evaluator_config("nonexistent")
        assert config["domain"] == "mixed"

    def test_criteria_weights_sum_to_one(self):
        for domain in ["backend", "frontend", "infrastructure", "database", "security", "api"]:
            config = get_evaluator_config(domain)
            total = sum(c["weight"] for c in config["evaluation_criteria"].values())
            assert abs(total - 1.0) < 0.01, f"{domain} weights sum to {total}, expected 1.0"

    def test_config_is_a_copy(self):
        """Ensure get_evaluator_config returns a copy, not the original."""
        config1 = get_evaluator_config("backend")
        config2 = get_evaluator_config("backend")
        config1["domain"] = "modified"
        assert config2["domain"] == "backend"

    def test_backend_has_architecture_criterion(self):
        config = get_evaluator_config("backend")
        assert "architecture_compliance" in config["evaluation_criteria"]

    def test_security_has_authentication_criterion(self):
        config = get_evaluator_config("security")
        assert "authentication" in config["evaluation_criteria"]

    def test_frontend_has_accessibility_criterion(self):
        config = get_evaluator_config("frontend")
        assert "accessibility" in config["evaluation_criteria"]

    def test_database_has_migration_safety_criterion(self):
        config = get_evaluator_config("database")
        assert "migration_safety" in config["evaluation_criteria"]

    def test_api_has_contracts_criterion(self):
        config = get_evaluator_config("api")
        assert "contracts" in config["evaluation_criteria"]

    def test_infrastructure_has_security_criterion(self):
        config = get_evaluator_config("infrastructure")
        assert "security" in config["evaluation_criteria"]


# ---------------------------------------------------------------------------
# format_verify_context
# ---------------------------------------------------------------------------

class TestFormatVerifyContext:
    """Tests for format_verify_context()."""

    def test_returns_string(self):
        result = format_verify_context(["internal/services/user.go"])
        assert isinstance(result, str)

    def test_contains_domain_heading(self):
        result = format_verify_context(["internal/services/user.go"])
        assert "## Domain-Specific Evaluation:" in result

    def test_contains_focus_areas(self):
        result = format_verify_context(["internal/services/user.go"])
        assert "### Focus Areas" in result

    def test_contains_evaluation_criteria(self):
        result = format_verify_context(["internal/services/user.go"])
        assert "### Evaluation Criteria" in result

    def test_contains_verification_commands(self):
        result = format_verify_context(["internal/services/user.go"])
        assert "### Verification Commands" in result

    def test_contains_red_flags(self):
        result = format_verify_context(["internal/services/user.go"])
        assert "### Red Flags" in result

    def test_empty_files_returns_mixed_context(self):
        result = format_verify_context([])
        assert "Mixed / General" in result

    def test_security_domain_identified(self):
        result = format_verify_context(["internal/auth/handler.go"])
        assert "security" in result.lower()

    def test_frontend_domain_identified(self):
        result = format_verify_context(["src/components/Modal.tsx"])
        assert "Frontend" in result

    def test_weight_percentages_present(self):
        result = format_verify_context(["internal/services/user.go"])
        # Should contain percentage values like "25%"
        assert "%" in result

"""Unit tests for lib/reverse_engineer.py."""

import json
import textwrap
from pathlib import Path

import pytest

from lib.reverse_engineer import (
    AnalysisReport,
    ReverseEngineer,
    _analyze_dockerfile,
    _analyze_env_vars_in_file,
    _analyze_zod_schema,
    _analyze_ts_interfaces,
    _analyze_go_structs,
    _analyze_python_models,
    _analyze_json_schema,
    _analyze_cli_in_file,
    _analyze_routes_in_file,
    _analyze_auth_in_file,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    """Create a temporary repo directory with sample files."""
    return tmp_path / "sample-repo"


def _write(path: Path, content: str) -> Path:
    """Helper: create file with dedented content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content))
    return path


# ---------------------------------------------------------------------------
# Config Schema Tests
# ---------------------------------------------------------------------------


class TestConfigSchemaAnalysis:
    """Tests for config schema detection."""

    def test_finds_zod_schema_in_typescript(self, tmp_path: Path) -> None:
        """Zod z.object() schemas are detected with fields."""
        src = tmp_path / "config.ts"
        _write(src, """\
            import { z } from "zod";

            export const AppConfig = z.object({
                port: z.number(),
                host: z.string(),
                debug: z.boolean().optional(),
                mode: z.enum(["production", "development", "test"]),
            });
        """)

        schemas = _analyze_zod_schema(src.read_text(), src, str(tmp_path))
        assert len(schemas) == 1
        s = schemas[0]
        assert s.name == "AppConfig"
        assert s.schema_type == "zod"
        assert len(s.fields) >= 3  # port, host, mode at minimum

        # Check field details
        field_names = {f.name for f in s.fields}
        assert "port" in field_names
        assert "host" in field_names
        assert "mode" in field_names

        # Check enum values
        mode_field = next(f for f in s.fields if f.name == "mode")
        assert mode_field.valid_values is not None
        assert "production" in mode_field.valid_values

    def test_finds_typescript_interface(self, tmp_path: Path) -> None:
        """TypeScript interfaces with Config/Options/Settings in name are detected."""
        src = tmp_path / "types.ts"
        _write(src, """\
            export interface DatabaseConfig {
                host: string;
                port: number;
                database: string;
                ssl?: boolean;
            }

            export interface UserProfile {
                name: string;
                email: string;
            }
        """)

        schemas = _analyze_ts_interfaces(src.read_text(), src, str(tmp_path))
        assert len(schemas) == 1  # Only DatabaseConfig, not UserProfile
        s = schemas[0]
        assert s.name == "DatabaseConfig"
        assert s.schema_type == "typescript_interface"
        assert len(s.fields) == 4

        ssl = next(f for f in s.fields if f.name == "ssl")
        assert ssl.required is False

    def test_finds_go_struct(self, tmp_path: Path) -> None:
        """Go structs with json/yaml tags and Config in name are detected."""
        src = tmp_path / "config.go"
        _write(src, """\
            package config

            type ServerConfig struct {
                Port    int    `json:"port" yaml:"port"`
                Host    string `json:"host,omitempty" yaml:"host"`
                Debug   bool   `json:"debug" env:"DEBUG"`
            }

            type User struct {
                Name string `json:"name"`
            }
        """)

        schemas = _analyze_go_structs(src.read_text(), src, str(tmp_path))
        assert len(schemas) == 1  # Only ServerConfig
        s = schemas[0]
        assert s.name == "ServerConfig"
        assert s.schema_type == "go_struct"
        assert len(s.fields) == 3

    def test_finds_python_pydantic_model(self, tmp_path: Path) -> None:
        """Python Pydantic BaseModel/BaseSettings are detected."""
        src = tmp_path / "settings.py"
        _write(src, """\
            from pydantic import BaseSettings

            class AppSettings(BaseSettings):
                database_url: str
                debug: bool = False
                port: int = 8080
                secret_key: Optional[str] = None
        """)

        schemas = _analyze_python_models(src.read_text(), src, str(tmp_path))
        assert len(schemas) == 1
        s = schemas[0]
        assert s.name == "AppSettings"
        assert s.schema_type == "python_pydantic"

        db_field = next(f for f in s.fields if f.name == "database_url")
        assert db_field.required is True

        debug_field = next(f for f in s.fields if f.name == "debug")
        assert debug_field.required is False
        assert debug_field.default == "False"

    def test_finds_json_schema(self, tmp_path: Path) -> None:
        """JSON Schema files with $schema marker are detected."""
        src = tmp_path / "schema.json"
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "AppConfig",
            "properties": {
                "port": {"type": "integer", "default": 3000},
                "host": {"type": "string"},
                "features": {"type": "array", "description": "Enabled features"},
            },
            "required": ["host"],
        }
        src.write_text(json.dumps(schema))

        schemas = _analyze_json_schema(src.read_text(), src, str(tmp_path))
        assert len(schemas) == 1
        s = schemas[0]
        assert s.name == "AppConfig"
        assert s.schema_type == "json_schema"

        host_field = next(f for f in s.fields if f.name == "host")
        assert host_field.required is True

        port_field = next(f for f in s.fields if f.name == "port")
        assert port_field.required is False
        assert port_field.default == "3000"


# ---------------------------------------------------------------------------
# Environment Variable Tests
# ---------------------------------------------------------------------------


class TestEnvVarAnalysis:
    """Tests for environment variable detection."""

    def test_finds_process_env_references(self, tmp_path: Path) -> None:
        """JavaScript process.env.X references are found."""
        src = tmp_path / "server.ts"
        _write(src, """\
            const port = process.env.PORT || "3000";
            const host = process.env.HOST;
            const secret = process.env["API_SECRET"];
        """)

        env_vars = _analyze_env_vars_in_file(src.read_text(), src, str(tmp_path))
        names = {ev.name for ev in env_vars}
        assert "PORT" in names
        assert "HOST" in names
        assert "API_SECRET" in names

        port_var = next(ev for ev in env_vars if ev.name == "PORT")
        assert port_var.default_value == "3000"

    def test_finds_go_getenv(self, tmp_path: Path) -> None:
        """Go os.Getenv references are found."""
        src = tmp_path / "main.go"
        _write(src, """\
            package main

            import "os"

            func main() {
                port := os.Getenv("PORT")
                dbURL := os.Getenv("DATABASE_URL")
                _, exists := os.LookupEnv("OPTIONAL_FLAG")
            }
        """)

        env_vars = _analyze_env_vars_in_file(src.read_text(), src, str(tmp_path))
        names = {ev.name for ev in env_vars}
        assert "PORT" in names
        assert "DATABASE_URL" in names
        assert "OPTIONAL_FLAG" in names

    def test_finds_python_environ(self, tmp_path: Path) -> None:
        """Python os.environ and os.getenv references are found."""
        src = tmp_path / "app.py"
        _write(src, """\
            
            db_url = os.environ["DATABASE_URL"]
            debug = os.getenv("DEBUG", "false")
            secret = os.environ.get("SECRET_KEY", "changeme")
        """)

        env_vars = _analyze_env_vars_in_file(src.read_text(), src, str(tmp_path))
        names = {ev.name for ev in env_vars}
        assert "DATABASE_URL" in names
        assert "DEBUG" in names
        assert "SECRET_KEY" in names

        debug_var = next(ev for ev in env_vars if ev.name == "DEBUG")
        assert debug_var.default_value == "false"

    def test_full_env_analysis_deduplicates(self, tmp_path: Path) -> None:
        """Full analysis deduplicates env vars across files."""
        repo = tmp_path / "repo"
        _write(repo / "a.ts", 'const x = process.env.PORT;\n')
        _write(repo / "b.ts", 'const y = process.env.PORT;\n')

        re = ReverseEngineer()
        env_vars = re.analyze_env_vars(str(repo))
        port_vars = [ev for ev in env_vars if ev.name == "PORT"]
        assert len(port_vars) == 1  # Deduplicated


# ---------------------------------------------------------------------------
# CLI Command Tests
# ---------------------------------------------------------------------------


class TestCLICommandAnalysis:
    """Tests for CLI command detection."""

    def test_finds_cobra_commands(self, tmp_path: Path) -> None:
        """Go Cobra commands are detected."""
        src = tmp_path / "cmd.go"
        _write(src, """\
            package cmd

            var serveCmd = &cobra.Command{
                Use:   "serve",
                Short: "Start the HTTP server",
            }

            var migrateCmd = &cobra.Command{
                Use:   "migrate",
                Short: "Run database migrations",
            }
        """)

        cmds = _analyze_cli_in_file(src.read_text(), src, str(tmp_path))
        assert len(cmds) == 2
        names = {c.command for c in cmds}
        assert "serve" in names
        assert "migrate" in names

    def test_finds_commander_commands(self, tmp_path: Path) -> None:
        """Commander.js commands are detected."""
        src = tmp_path / "cli.ts"
        _write(src, """\
            import { program } from "commander";

            program
                .command("init")
                .description("Initialize the project")
                .action(() => {});

            program
                .command("build")
                .description("Build the project")
                .action(() => {});
        """)

        cmds = _analyze_cli_in_file(src.read_text(), src, str(tmp_path))
        assert len(cmds) == 2
        names = {c.command for c in cmds}
        assert "init" in names
        assert "build" in names

    def test_finds_argparse_commands(self, tmp_path: Path) -> None:
        """Python argparse subcommands are detected."""
        src = tmp_path / "cli.py"
        _write(src, """\
            import argparse

            parser = argparse.ArgumentParser()
            subparsers = parser.add_subparsers()

            sub = subparsers.add_parser("run", help="Run the server")
            sub.add_argument("--port", help="Port number")

            sub2 = subparsers.add_parser("test", help="Run tests")
        """)

        cmds = _analyze_cli_in_file(src.read_text(), src, str(tmp_path))
        assert len(cmds) >= 2
        names = {c.command for c in cmds}
        assert "run" in names
        assert "test" in names


# ---------------------------------------------------------------------------
# API Route Tests
# ---------------------------------------------------------------------------


class TestAPIRouteAnalysis:
    """Tests for API route detection."""

    def test_finds_express_routes(self, tmp_path: Path) -> None:
        """Express.js routes are detected."""
        src = tmp_path / "routes.ts"
        _write(src, """\
            import express from "express";
            const router = express.Router();

            router.get("/api/users", getUsers);
            router.post("/api/users", createUser);
            router.get("/api/users/:id", getUserById);
            router.delete("/api/users/:id", deleteUser);
        """)

        routes = _analyze_routes_in_file(src.read_text(), src, str(tmp_path))
        assert len(routes) >= 4  # May include duplicates from multiple regex engines
        paths = {r.path for r in routes}
        assert "/api/users" in paths
        assert "/api/users/:id" in paths

        methods = {r.method for r in routes}
        assert "GET" in methods
        assert "POST" in methods
        assert "DELETE" in methods

    def test_finds_go_gin_routes(self, tmp_path: Path) -> None:
        """Go Gin routes are detected."""
        src = tmp_path / "router.go"
        _write(src, """\
            package main

            func setupRoutes(r *gin.Engine) {
                r.GET("/api/health", healthHandler)
                r.POST("/api/login", loginHandler)
                r.PUT("/api/users/:id", updateHandler)
            }
        """)

        routes = _analyze_routes_in_file(src.read_text(), src, str(tmp_path))
        assert len(routes) >= 3
        paths = {r.path for r in routes}
        assert "/api/health" in paths
        assert "/api/login" in paths

    def test_finds_flask_routes(self, tmp_path: Path) -> None:
        """Flask/FastAPI routes are detected."""
        src = tmp_path / "app.py"
        _write(src, """\
            from flask import Flask
            app = Flask(__name__)

            @app.get("/api/items")
            def list_items():
                pass

            @app.post("/api/items")
            def create_item():
                pass

            @app.route("/api/items/<id>", methods=["GET", "PUT"])
            def item_detail(id):
                pass
        """)

        routes = _analyze_routes_in_file(src.read_text(), src, str(tmp_path))
        assert len(routes) >= 3
        paths = {r.path for r in routes}
        assert "/api/items" in paths


# ---------------------------------------------------------------------------
# Docker Tests
# ---------------------------------------------------------------------------


class TestDockerAnalysis:
    """Tests for Docker configuration analysis."""

    def test_reads_dockerfile(self) -> None:
        """Dockerfile directives are parsed correctly."""
        content = textwrap.dedent("""\
            FROM node:20-alpine
            WORKDIR /app
            COPY . .
            ENV NODE_ENV=production
            ENV PORT=3000
            EXPOSE 3000
            HEALTHCHECK CMD curl -f http://localhost:3000/health
            ENTRYPOINT ["node"]
            CMD ["server.js"]
        """)

        setup = _analyze_dockerfile(content)
        assert setup.base_image == "node:20-alpine"
        assert setup.entrypoint == '["node"]'
        assert setup.cmd == '["server.js"]'
        assert "3000" in setup.ports
        assert any("NODE_ENV" in ev for ev in setup.env_vars)
        assert setup.healthcheck is not None
        assert "curl" in setup.healthcheck

    def test_full_docker_analysis(self, tmp_path: Path) -> None:
        """Full Docker analysis reads Dockerfile and compose."""
        repo = tmp_path / "repo"
        _write(repo / "Dockerfile", """\
            FROM python:3.11
            EXPOSE 8080
            CMD ["python", "app.py"]
        """)
        _write(repo / "docker-compose.yml", """\
            version: "3"
            services:
              app:
                build: .
                ports:
                  - "8080:8080"
                environment:
                  - DATABASE_URL=postgres://localhost/db
              redis:
                image: redis:7
                ports:
                  - "6379:6379"
        """)

        re_eng = ReverseEngineer()
        setup = re_eng.analyze_docker_setup(str(repo))

        assert setup.base_image == "python:3.11"
        assert "8080" in setup.ports
        assert len(setup.compose_services) == 2

        svc_names = {s["name"] for s in setup.compose_services}
        assert "app" in svc_names
        assert "redis" in svc_names


# ---------------------------------------------------------------------------
# Auth Flow Tests
# ---------------------------------------------------------------------------


class TestAuthFlowAnalysis:
    """Tests for authentication flow detection."""

    def test_detects_jwt_auth(self, tmp_path: Path) -> None:
        """JWT authentication pattern is detected."""
        src = tmp_path / "auth.ts"
        _write(src, """\
            import jwt from "jsonwebtoken";

            app.post("/auth/login", async (req, res) => {
                const token = jwt.sign(payload, secret);
                res.json({ token });
            });

            app.get("/auth/verify", authMiddleware, (req, res) => {
                res.json({ valid: true });
            });
        """)

        atype, cookie, endpoints, middleware = _analyze_auth_in_file(
            src.read_text(), src, str(tmp_path),
        )
        assert atype == "jwt"
        assert len(endpoints) >= 1
        paths = {ep["path"] for ep in endpoints}
        assert "/auth/login" in paths

    def test_detects_session_auth(self, tmp_path: Path) -> None:
        """Session-based authentication is detected."""
        src = tmp_path / "session.ts"
        _write(src, """\
            import session from "express-session";

            app.use(session({
                cookie: { name: "sid" },
                secret: "keyboard-cat",
            }));

            app.post("/login", loginHandler);
            app.post("/logout", logoutHandler);
        """)

        atype, cookie, endpoints, middleware = _analyze_auth_in_file(
            src.read_text(), src, str(tmp_path),
        )
        assert atype == "session"
        paths = {ep["path"] for ep in endpoints}
        assert "/login" in paths
        assert "/logout" in paths


# ---------------------------------------------------------------------------
# Full Analysis / Integration Guide Tests
# ---------------------------------------------------------------------------


class TestFullAnalysis:
    """Tests for full analysis pipeline and report generation."""

    def test_full_analysis_runs_without_errors(self, tmp_path: Path) -> None:
        """Full analysis completes on a repo with mixed files."""
        repo = tmp_path / "full-repo"
        _write(repo / "config.ts", """\
            import { z } from "zod";
            export const Config = z.object({
                port: z.number(),
            });
        """)
        _write(repo / "server.ts", """\
            const port = process.env.PORT || "3000";
            app.get("/api/health", healthHandler);
        """)
        _write(repo / "Dockerfile", """\
            FROM node:20
            EXPOSE 3000
            CMD ["node", "server.js"]
        """)

        re_eng = ReverseEngineer()
        report = re_eng.full_analysis(str(repo))

        assert isinstance(report, AnalysisReport)
        assert len(report.errors) == 0
        assert len(report.config_schemas) >= 1
        assert len(report.env_vars) >= 1
        assert len(report.api_routes) >= 1
        assert report.docker_setup is not None
        assert "3000" in report.docker_setup.ports

    def test_format_integration_guide(self, tmp_path: Path) -> None:
        """Integration guide is generated as valid markdown."""
        repo = tmp_path / "guide-repo"
        _write(repo / "config.ts", """\
            import { z } from "zod";
            export const ServerConfig = z.object({
                port: z.number(),
                host: z.string(),
            });
        """)

        re_eng = ReverseEngineer()
        report = re_eng.full_analysis(str(repo))
        guide = re_eng.format_integration_guide(report)

        assert "# Reverse Engineering Report" in guide
        assert "Config Schemas" in guide
        assert "ServerConfig" in guide
        assert "`port`" in guide

    def test_empty_repo_produces_empty_report(self, tmp_path: Path) -> None:
        """An empty directory produces an empty (but valid) report."""
        repo = tmp_path / "empty-repo"
        repo.mkdir()

        re_eng = ReverseEngineer()
        report = re_eng.full_analysis(str(repo))

        assert isinstance(report, AnalysisReport)
        assert len(report.config_schemas) == 0
        assert len(report.env_vars) == 0
        assert len(report.api_routes) == 0
        assert len(report.errors) == 0

    def test_node_modules_excluded(self, tmp_path: Path) -> None:
        """node_modules directory is excluded from scanning."""
        repo = tmp_path / "nm-repo"
        _write(repo / "src" / "app.ts", 'const x = process.env.REAL_VAR;\n')
        _write(repo / "node_modules" / "pkg" / "index.ts", 'const y = process.env.FAKE_VAR;\n')

        re_eng = ReverseEngineer()
        env_vars = re_eng.analyze_env_vars(str(repo))
        names = {ev.name for ev in env_vars}
        assert "REAL_VAR" in names
        assert "FAKE_VAR" not in names


# ---------------------------------------------------------------------------

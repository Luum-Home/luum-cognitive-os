"""Unit tests for lib/secret_ref.py

Validates SecretRef resolution from env, file, and literal sources,
config secret resolution, masking, and edge cases.
"""


import pytest

from lib.secret_ref import mask_secrets, resolve_config_secrets, resolve_secret_ref

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# resolve_secret_ref
# ---------------------------------------------------------------------------


class TestResolveSecretRef:
    """Tests for resolve_secret_ref()."""

    def test_resolve_env_var(self, monkeypatch):
        """Should resolve a secret from an environment variable."""
        monkeypatch.setenv("TEST_SECRET_KEY", "my-secret-value")
        ref = {"source": "env", "id": "TEST_SECRET_KEY"}
        assert resolve_secret_ref(ref) == "my-secret-value"

    def test_resolve_file_content(self, tmp_path):
        """Should resolve a secret from a file, stripping whitespace."""
        secret_file = tmp_path / "secret.txt"
        secret_file.write_text("file-secret-value\n")
        ref = {"source": "file", "id": str(secret_file)}
        assert resolve_secret_ref(ref) == "file-secret-value"

    def test_resolve_literal(self):
        """Should return the id directly for literal source."""
        ref = {"source": "literal", "id": "default-value"}
        assert resolve_secret_ref(ref) == "default-value"

    def test_missing_env_var_returns_none(self, monkeypatch):
        """Should return None when the environment variable doesn't exist."""
        monkeypatch.delenv("NONEXISTENT_SECRET_VAR_XYZ", raising=False)
        ref = {"source": "env", "id": "NONEXISTENT_SECRET_VAR_XYZ"}
        assert resolve_secret_ref(ref) is None

    def test_missing_file_returns_none(self):
        """Should return None when the file doesn't exist."""
        ref = {"source": "file", "id": "/nonexistent/path/secret.txt"}
        assert resolve_secret_ref(ref) is None

    def test_unknown_source_returns_none(self):
        """Should return None for an unsupported source type."""
        ref = {"source": "vault", "id": "secret/path"}
        assert resolve_secret_ref(ref) is None


# ---------------------------------------------------------------------------
# resolve_config_secrets
# ---------------------------------------------------------------------------


class TestResolveConfigSecrets:
    """Tests for resolve_config_secrets()."""

    def test_resolve_nested_config(self, monkeypatch):
        """Should resolve SecretRef objects in nested config dicts."""
        monkeypatch.setenv("DB_PASSWORD", "s3cret")
        config = {
            "database": {
                "host": "localhost",
                "password": {"source": "env", "id": "DB_PASSWORD"},
            },
            "name": "my-app",
        }
        result = resolve_config_secrets(config)
        assert result["database"]["password"] == "s3cret"
        assert result["database"]["host"] == "localhost"
        assert result["name"] == "my-app"

    def test_non_secret_ref_dict_unchanged(self):
        """Should not modify dicts that are not SecretRef objects."""
        config = {
            "database": {
                "host": "localhost",
                "port": 5432,
            },
            "options": {"debug": True, "verbose": False},
        }
        result = resolve_config_secrets(config)
        assert result["database"]["host"] == "localhost"
        assert result["database"]["port"] == 5432
        assert result["options"]["debug"] is True

    def test_empty_config(self):
        """Should handle empty config dict without error."""
        config = {}
        result = resolve_config_secrets(config)
        assert result == {}

    def test_unresolvable_ref_kept(self, monkeypatch):
        """Should keep original SecretRef when resolution returns None."""
        monkeypatch.delenv("MISSING_VAR_ABC", raising=False)
        ref = {"source": "env", "id": "MISSING_VAR_ABC"}
        config = {"token": ref}
        resolve_config_secrets(config)
        # The ref dict should remain since it couldn't be resolved
        assert config["token"] == ref


# ---------------------------------------------------------------------------
# mask_secrets
# ---------------------------------------------------------------------------


class TestMaskSecrets:
    """Tests for mask_secrets()."""

    def test_mask_sensitive_keys(self, monkeypatch):
        """Should mask string values under sensitive key names."""
        monkeypatch.setenv("API_TOKEN", "ghp_abc123")
        config = {
            "api_token": "ghp_abc123",
            "name": "my-app",
            "password": "hunter2",
        }
        masked = mask_secrets(config)
        assert masked["api_token"] == "***"
        assert masked["password"] == "***"
        assert masked["name"] == "my-app"
        # Original should not be modified
        assert config["api_token"] == "ghp_abc123"

    def test_mask_does_not_modify_original(self):
        """Should return a deep copy, not modify the original."""
        config = {"secret_key": "original-value", "name": "test"}
        masked = mask_secrets(config)
        assert masked["secret_key"] == "***"
        assert config["secret_key"] == "original-value"

"""Tests for lib/provider_profile.py (ADR-178).

Verifies ProviderProfile construction, auth resolution, model alias lookup,
YAML loading, and the providers/__init__.py integration shim.
"""

from __future__ import annotations



from lib.provider_profile import ProviderProfile, get_profile, load_profiles


# ---------------------------------------------------------------------------
# ProviderProfile construction
# ---------------------------------------------------------------------------


class TestProviderProfileConstruction:
    def test_minimal(self):
        p = ProviderProfile(name="test", provider_kind="openai")
        assert p.name == "test"
        assert p.provider_kind == "openai"
        assert p.auth_slots == {}
        assert p.model_aliases == {}
        assert p.context_window == 128_000
        assert p.enabled is True
        assert p.base_url is None

    def test_from_dict(self):
        p = ProviderProfile.from_dict({
            "name": "openai",
            "provider_kind": "openai",
            "auth_slots": {"api_key": "ENV:OPENAI_API_KEY", "org_id": "ENV:OPENAI_ORG"},
            "model_aliases": {"sonnet": "gpt-5.4", "haiku": "gpt-4o-mini"},
            "context_window": 128000,
            "enabled": True,
            "base_url": None,
        })
        assert p.name == "openai"
        assert p.auth_slots["api_key"] == "ENV:OPENAI_API_KEY"
        assert p.model_aliases["haiku"] == "gpt-4o-mini"

    def test_from_dict_kind_alias(self):
        # 'kind' is an accepted alias for 'provider_kind'
        p = ProviderProfile.from_dict({"name": "x", "kind": "anthropic"})
        assert p.provider_kind == "anthropic"

    def test_to_dict_roundtrip(self):
        p = ProviderProfile(
            name="qwen",
            provider_kind="alibaba_qwen",
            auth_slots={"api_key": "ENV:ALIBABA_QWEN_API_KEY"},
            model_aliases={"sonnet": "qwen3-coder-plus"},
        )
        d = p.to_dict()
        p2 = ProviderProfile.from_dict(d)
        assert p2.name == p.name
        assert p2.auth_slots == p.auth_slots
        assert p2.model_aliases == p.model_aliases


# ---------------------------------------------------------------------------
# Auth resolution
# ---------------------------------------------------------------------------


class TestResolveAuth:
    def test_env_slot_present(self, monkeypatch):
        monkeypatch.setenv("TEST_PROV_KEY", "sk-test-123")
        p = ProviderProfile(
            name="t", provider_kind="openai",
            auth_slots={"api_key": "ENV:TEST_PROV_KEY"},
        )
        resolved = p.resolve_auth()
        assert resolved["api_key"] == "sk-test-123"

    def test_env_slot_absent(self, monkeypatch):
        monkeypatch.delenv("TEST_PROV_KEY_MISSING", raising=False)
        p = ProviderProfile(
            name="t", provider_kind="openai",
            auth_slots={"api_key": "ENV:TEST_PROV_KEY_MISSING"},
        )
        resolved = p.resolve_auth()
        assert resolved["api_key"] == ""

    def test_literal_slot(self):
        p = ProviderProfile(
            name="t", provider_kind="ollama",
            auth_slots={"api_key": "nokey"},
        )
        assert p.resolve_auth()["api_key"] == "nokey"

    def test_is_configured_all_present(self, monkeypatch):
        monkeypatch.setenv("T_KEY", "abc")
        p = ProviderProfile(
            name="t", provider_kind="x",
            auth_slots={"api_key": "ENV:T_KEY"},
        )
        assert p.is_configured() is True

    def test_is_configured_missing(self, monkeypatch):
        monkeypatch.delenv("T_KEY_MISSING", raising=False)
        p = ProviderProfile(
            name="t", provider_kind="x",
            auth_slots={"api_key": "ENV:T_KEY_MISSING"},
        )
        assert p.is_configured() is False

    def test_is_configured_no_slots(self):
        p = ProviderProfile(name="ollama", provider_kind="ollama")
        # no slots => vacuously True (local providers need no key)
        assert p.is_configured() is True


# ---------------------------------------------------------------------------
# Model alias resolution
# ---------------------------------------------------------------------------


class TestGetModel:
    def test_alias_mapped(self):
        p = ProviderProfile(
            name="openai", provider_kind="openai",
            model_aliases={"sonnet": "gpt-5.4", "haiku": "gpt-4o-mini"},
        )
        assert p.get_model("sonnet") == "gpt-5.4"
        assert p.get_model("haiku") == "gpt-4o-mini"

    def test_alias_passthrough(self):
        p = ProviderProfile(name="x", provider_kind="x", model_aliases={})
        # unmapped alias falls through to itself
        assert p.get_model("claude-sonnet-4-6") == "claude-sonnet-4-6"

    def test_alias_empty(self):
        p = ProviderProfile(name="x", provider_kind="x")
        assert p.get_model("opus") == "opus"


# ---------------------------------------------------------------------------
# YAML loading
# ---------------------------------------------------------------------------


class TestLoadProfiles:
    def test_load_bundled_manifest(self):
        # The real manifests/provider-profiles.yaml should load without error
        profiles = load_profiles()
        # At minimum the 5 seeded profiles must be present
        assert "claude_sdk" in profiles
        assert "qwen" in profiles
        assert "openrouter" in profiles
        assert "openai" in profiles
        assert "gemini" in profiles

    def test_load_missing_file(self, tmp_path):
        missing = tmp_path / "nonexistent.yaml"
        profiles = load_profiles(missing)
        assert profiles == {}

    def test_load_custom_yaml(self, tmp_path):
        yaml_content = """
provider_profiles:
  - name: custom
    provider_kind: openai
    auth_slots:
      api_key: "ENV:CUSTOM_KEY"
    model_aliases:
      sonnet: "custom-model-v1"
    context_window: 64000
    enabled: true
"""
        f = tmp_path / "profiles.yaml"
        f.write_text(yaml_content)
        profiles = load_profiles(f)
        assert "custom" in profiles
        p = profiles["custom"]
        assert p.provider_kind == "openai"
        assert p.auth_slots["api_key"] == "ENV:CUSTOM_KEY"
        assert p.model_aliases["sonnet"] == "custom-model-v1"
        assert p.context_window == 64_000

    def test_malformed_entry_skipped(self, tmp_path):
        yaml_content = """
provider_profiles:
  - name: good
    provider_kind: openai
  - not_a_dict_field: 123
    # missing required 'name' key
"""
        f = tmp_path / "profiles.yaml"
        f.write_text(yaml_content)
        profiles = load_profiles(f)
        assert "good" in profiles
        # malformed entry silently skipped
        assert len(profiles) == 1

    def test_get_profile_helper(self):
        p = get_profile("qwen")
        assert p is not None
        assert p.name == "qwen"

    def test_get_profile_missing(self):
        assert get_profile("does_not_exist_xyz") is None


# ---------------------------------------------------------------------------
# providers/__init__.py integration shim
# ---------------------------------------------------------------------------


class TestProvidersInitShim:
    def test_get_provider_profiles_returns_dict(self):
        from lib.providers import get_provider_profiles
        profiles = get_provider_profiles()
        assert isinstance(profiles, dict)
        # should return the same profiles as load_profiles()
        assert "qwen" in profiles

    def test_existing_registry_unchanged(self):
        from lib.providers import REGISTRY, ADVANCE_ON_ANY_FAILURE
        # existing module-level interface must be unaffected by ADR-178 additions
        assert "qwen" in REGISTRY
        assert "openai" in REGISTRY
        assert "qwen" in ADVANCE_ON_ANY_FAILURE

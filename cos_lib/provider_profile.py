# SCOPE: both
"""ProviderProfile — credential-slot pattern (ADR-178).

Ports the ProviderProfile credential-slot pattern from HKUDS/OpenHarness
(commit 7873f0d109174a57b3b1af7aa5397a6b3b0bd551, src/openharness/config/settings.py)
under MIT licence, adapted to COS naming conventions and the existing
lib/providers/ architecture (ADR-049, ADR-062).

Key design decisions vs upstream:
  - Upstream ProviderProfile.credential_slot is a single str (the auth_source name).
    COS uses auth_slots: dict[str, str] to allow multiple named slots per provider
    (e.g. api_key + org_id for OpenAI), with "ENV:<VAR_NAME>" indirection.
  - Upstream uses auth_source + a separate resolve path in settings.py.
    COS resolve_auth() is self-contained on the dataclass.
  - model_aliases replaces upstream's default_model + resolved_model property
    with a full alias map matching COS's MODEL_MAP convention.
  - Loaded from manifests/provider-profiles.yaml; falls back gracefully if absent.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_PROFILES_PATH = Path(__file__).resolve().parent.parent / "manifests" / "provider-profiles.yaml"

# ---------------------------------------------------------------------------
# ProviderProfile dataclass
# ---------------------------------------------------------------------------


@dataclass
class ProviderProfile:
    """Named provider profile with credential slots and model aliases.

    auth_slots maps logical slot names to their resolution spec:
      "ENV:<VAR>"   — read from environment variable VAR
      "<literal>"   — use the literal value as-is (not recommended for secrets)

    Example:
        ProviderProfile(
            name="openai",
            provider_kind="openai",
            auth_slots={"api_key": "ENV:OPENAI_API_KEY", "org_id": "ENV:OPENAI_ORG"},
            model_aliases={"sonnet": "gpt-5.4", "haiku": "gpt-4o-mini"},
            context_window=128_000,
        )
    """

    name: str
    provider_kind: str  # anthropic | openai | openrouter | gemini | ollama | deepseek | ...
    auth_slots: dict[str, str] = field(default_factory=dict)  # slot_name -> "ENV:VAR" | literal
    model_aliases: dict[str, str] = field(default_factory=dict)  # "opus"/"sonnet"/"haiku" -> native
    context_window: int = 128_000
    enabled: bool = True
    base_url: str | None = None  # optional override

    # ---------------------------------------------------------------------------
    # Auth resolution
    # ---------------------------------------------------------------------------

    def resolve_auth(self) -> dict[str, str]:
        """Resolve all auth slots to their concrete values.

        Slots prefixed with "ENV:" are read from os.environ.
        Slots with literal values are returned as-is.
        Slots whose env var is unset resolve to "" (not raised — caller decides).

        Returns a dict mapping slot_name -> resolved_value.
        """
        resolved: dict[str, str] = {}
        for slot_name, spec in self.auth_slots.items():
            if spec.startswith("ENV:"):
                env_var = spec[4:]
                resolved[slot_name] = os.environ.get(env_var, "")
            else:
                resolved[slot_name] = spec
        return resolved

    def is_configured(self) -> bool:
        """True iff all auth slots resolve to non-empty values."""
        return all(v for v in self.resolve_auth().values())

    # ---------------------------------------------------------------------------
    # Model resolution
    # ---------------------------------------------------------------------------

    def get_model(self, alias: str) -> str:
        """Resolve an abstract model alias to the provider-native model name.

        Falls back to alias itself if not mapped (allows passing native names
        directly, e.g. "claude-sonnet-4-6").
        """
        return self.model_aliases.get(alias, alias)

    # ---------------------------------------------------------------------------
    # Serialisation
    # ---------------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "provider_kind": self.provider_kind,
            "auth_slots": dict(self.auth_slots),
            "model_aliases": dict(self.model_aliases),
            "context_window": self.context_window,
            "enabled": self.enabled,
            "base_url": self.base_url,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProviderProfile":
        return cls(
            name=str(data["name"]),
            provider_kind=str(data.get("provider_kind", data.get("kind", ""))),
            auth_slots=dict(data.get("auth_slots", {})),
            model_aliases=dict(data.get("model_aliases", {})),
            context_window=int(data.get("context_window", 128_000)),
            enabled=bool(data.get("enabled", True)),
            base_url=data.get("base_url"),
        )


# ---------------------------------------------------------------------------
# Profile registry — loaded from manifests/provider-profiles.yaml
# ---------------------------------------------------------------------------


def load_profiles(path: Path | None = None) -> dict[str, ProviderProfile]:
    """Load ProviderProfile objects from a YAML file.

    Returns an empty dict (not an error) if the file is absent — callers can
    fall back to the existing lib/providers/* module registry.
    """
    target = path or _PROFILES_PATH
    if not target.exists():
        return {}
    try:
        import yaml  # type: ignore[import]
    except ImportError:
        return {}
    raw = yaml.safe_load(target.read_text()) or {}
    profiles_list = raw.get("provider_profiles", [])
    result: dict[str, ProviderProfile] = {}
    for entry in profiles_list:
        try:
            p = ProviderProfile.from_dict(entry)
            result[p.name] = p
        except (KeyError, TypeError, ValueError):
            pass  # skip malformed entries; caller sees partial registry
    return result


def get_profile(name: str, path: Path | None = None) -> ProviderProfile | None:
    """Convenience: load profiles and return a single named profile or None."""
    return load_profiles(path).get(name)

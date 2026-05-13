"""Health, metadata, and agent-options schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(default="ok")
    version: str
    uptime_seconds: int


class VersionResponse(BaseModel):
    version: str
    build: str
    commit: str | None = None


class CsrfTokenResponse(BaseModel):
    token: str
    expires_in_seconds: int = Field(default=3600)


class AgentCapability(BaseModel):
    name: str
    enabled: bool
    description: str


class AgentOptionsResponse(BaseModel):
    """Static description of agent capabilities surfaced to clients."""

    api_version: str = Field(default="v1")
    streaming: bool = Field(default=True)
    multimodal_inputs: bool = Field(default=True)
    sessions_supported: bool = Field(default=True)
    capabilities: list[AgentCapability]

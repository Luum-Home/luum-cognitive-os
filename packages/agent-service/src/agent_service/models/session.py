"""Session lifecycle and configuration schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RuntimeSettings(BaseModel):
    settings: dict[str, Any] = Field(default_factory=dict)


class RuntimeSettingsUpdate(BaseModel):
    key: str
    value: Any


class ModelDescriptor(BaseModel):
    id: str
    provider: str
    family: str | None = None
    context_window: int | None = None


class ModelsListResponse(BaseModel):
    models: list[ModelDescriptor]


class SessionModelSelect(BaseModel):
    session_id: str
    model_id: str


class ShareConfigResponse(BaseModel):
    share_enabled: bool = Field(default=False)
    base_url: str | None = None


class SessionSummary(BaseModel):
    session_id: str
    created_at: datetime
    updated_at: datetime
    title: str | None = None
    status: str


class SessionListResponse(BaseModel):
    sessions: list[SessionSummary]
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)
    total: int = Field(default=0, ge=0)


class SessionCreateRequest(BaseModel):
    workspace: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionCreateResponse(BaseModel):
    session_id: str
    created_at: datetime


class SessionDetails(BaseModel):
    session_id: str
    created_at: datetime
    updated_at: datetime
    status: str
    workspace: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    message_count: int = Field(default=0, ge=0)


class SessionEvent(BaseModel):
    event_id: str
    session_id: str
    timestamp: datetime
    type: str
    payload: dict[str, Any] = Field(default_factory=dict)


class SessionEventsPage(BaseModel):
    session_id: str
    events: list[SessionEvent]
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=500)
    total: int = Field(default=0, ge=0)


class SessionLatestEvent(BaseModel):
    session_id: str
    event: SessionEvent | None = None


class SessionStatusResponse(BaseModel):
    session_id: str
    status: str
    last_activity_at: datetime | None = None


class SessionUpdateRequest(BaseModel):
    session_id: str
    patch: dict[str, Any]


class SessionDeleteRequest(BaseModel):
    session_id: str


class GenerateSummaryRequest(BaseModel):
    session_id: str


class SessionShareRequest(BaseModel):
    session_id: str


class SessionShareResponse(BaseModel):
    session_id: str
    share_url: str

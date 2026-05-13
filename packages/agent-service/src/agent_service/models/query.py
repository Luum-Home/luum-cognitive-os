"""Query request/response schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MultimodalInput(BaseModel):
    kind: str = Field(description="text | image | audio | file")
    content: str | None = None
    uri: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class OneshotQueryRequest(BaseModel):
    query: str
    multimodal_inputs: list[MultimodalInput] = Field(default_factory=list)
    options: dict[str, Any] = Field(default_factory=dict)


class QueryRequest(BaseModel):
    session_id: str
    query: str
    multimodal_inputs: list[MultimodalInput] = Field(default_factory=list)
    options: dict[str, Any] = Field(default_factory=dict)


class QueryResponse(BaseModel):
    session_id: str | None = None
    response: str
    finish_reason: str = Field(default="stop")
    usage: dict[str, Any] = Field(default_factory=dict)


class SessionAbortRequest(BaseModel):
    session_id: str

"""Workspace inspection schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class WorkspaceFileEntry(BaseModel):
    path: str
    is_dir: bool
    size_bytes: int | None = None


class WorkspaceFilesResponse(BaseModel):
    session_id: str
    path: str
    entries: list[WorkspaceFileEntry] = Field(default_factory=list)


class WorkspaceSearchHit(BaseModel):
    path: str
    line: int
    snippet: str


class WorkspaceSearchResponse(BaseModel):
    session_id: str
    query: str
    hits: list[WorkspaceSearchHit] = Field(default_factory=list)


class WorkspaceValidateRequest(BaseModel):
    session_id: str
    path: str


class WorkspaceValidateResponse(BaseModel):
    session_id: str
    path: str
    accessible: bool
    reason: str | None = None

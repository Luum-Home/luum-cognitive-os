"""Common response envelopes."""

from __future__ import annotations

from pydantic import BaseModel, Field


class NotImplementedResponse(BaseModel):
    """Response body returned by every Phase-1 stub endpoint."""

    status: str = Field(default="not_implemented")
    reason: str
    phase: int = Field(default=1, description="Phase that will implement this endpoint")
    endpoint: str

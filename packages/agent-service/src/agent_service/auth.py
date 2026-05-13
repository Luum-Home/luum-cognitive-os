"""Bearer-token authentication dependency.

Used as a FastAPI router-level dependency so every protected route enforces
auth by construction. The ``/api/v1/health`` route is registered on a router
without this dependency and is therefore the only public endpoint.
"""

from __future__ import annotations

from fastapi import Header, HTTPException, Request, status


def _expected_token(request: Request) -> str | None:
    config = request.app.state.config
    return config.bearer_token


async def require_bearer(
    request: Request,
    authorization: str | None = Header(default=None),
) -> None:
    """Reject the request unless ``Authorization: Bearer <token>`` matches.

    If ``COS_AGENT_SERVICE_TOKEN`` is unset, every protected endpoint rejects
    with 401. This is intentional: the service refuses to operate without an
    explicit credential.
    """

    expected = _expected_token(request)
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="agent service token not configured",
        )
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
        )
    presented = authorization.removeprefix("Bearer ").strip()
    if presented != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid bearer token",
        )

"""Shared-secret check for calls coming from ElevenAgents webhook tools."""
import hmac
import os

from fastapi import Header, HTTPException, Request


def _configured_secret(request: Request) -> str | None:
    env = request.scope.get("env")  # set by the Workers ASGI server
    if env is not None:
        return getattr(env, "TOOL_SECRET", None)
    return os.environ.get("TOOL_SECRET")  # local tests


def require_tool_secret(
    request: Request,
    x_tool_secret: str | None = Header(default=None),
) -> None:
    expected = _configured_secret(request)
    if not expected:
        raise HTTPException(status_code=500, detail="TOOL_SECRET is not configured")
    if not x_tool_secret or not hmac.compare_digest(x_tool_secret, expected):
        raise HTTPException(status_code=401, detail="invalid tool secret")

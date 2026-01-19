"""Application middleware."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Request, Response

from app.features.usage.context import (
    clear_usage_context,
    mark_request_end,
    mark_request_start,
    new_request_id,
    set_request_id,
    set_request_method,
    set_request_path,
)


async def request_context_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Attach request_id + basic request metadata to contextvars.

    Also adds `X-Request-Id` to the response.
    """
    clear_usage_context()

    request_id = new_request_id()
    set_request_id(request_id)
    set_request_method(request.method)
    set_request_path(request.url.path)
    started_at = mark_request_start()

    response: Response | None = None
    try:
        response = await call_next(request)
        response.headers["X-Request-Id"] = str(request_id)
        return response
    finally:
        mark_request_end(started_at)
        # Always clean up to avoid context leaking across requests.
        clear_usage_context()

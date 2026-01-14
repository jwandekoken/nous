"""Request-scoped usage context.

We use `contextvars` so token usage tracking can attribute provider calls
to the current request/tenant/actor without passing plumbing everywhere.
"""

from __future__ import annotations

import contextvars
import uuid
from time import perf_counter

request_id_var: contextvars.ContextVar[uuid.UUID | None] = contextvars.ContextVar(
    "request_id", default=None
)
request_started_at_var: contextvars.ContextVar[float | None] = contextvars.ContextVar(
    "request_started_at", default=None
)
request_duration_ms_var: contextvars.ContextVar[float | None] = contextvars.ContextVar(
    "request_duration_ms", default=None
)
request_method_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_method", default=None
)
request_path_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_path", default=None
)

tenant_id_var: contextvars.ContextVar[uuid.UUID | None] = contextvars.ContextVar(
    "tenant_id", default=None
)
graph_name_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "graph_name", default=None
)
actor_type_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "actor_type", default="unknown"
)
actor_id_var: contextvars.ContextVar[uuid.UUID | None] = contextvars.ContextVar(
    "actor_id", default=None
)


def new_request_id() -> uuid.UUID:
    return uuid.uuid4()


def mark_request_start() -> float:
    started_at = perf_counter()
    _ = request_started_at_var.set(started_at)
    return started_at


def mark_request_end(started_at: float | None) -> float | None:
    if started_at is None:
        return None
    duration_ms = (perf_counter() - started_at) * 1000.0
    _ = request_duration_ms_var.set(duration_ms)
    return duration_ms


def set_request_id(request_id: uuid.UUID | None) -> None:
    _ = request_id_var.set(request_id)


def get_request_id() -> uuid.UUID | None:
    return request_id_var.get()


def get_request_method() -> str | None:
    return request_method_var.get()


def get_request_path() -> str | None:
    return request_path_var.get()


def get_tenant_id() -> uuid.UUID | None:
    return tenant_id_var.get()


def get_graph_name() -> str | None:
    return graph_name_var.get()


def get_actor_type() -> str:
    return actor_type_var.get()


def get_actor_id() -> uuid.UUID | None:
    return actor_id_var.get()


def set_request_method(method: str | None) -> None:
    _ = request_method_var.set(method)


def set_request_path(path: str | None) -> None:
    _ = request_path_var.set(path)


def set_tenant_id(tenant_id: uuid.UUID | None) -> None:
    _ = tenant_id_var.set(tenant_id)


def set_graph_name(graph_name: str | None) -> None:
    _ = graph_name_var.set(graph_name)


def set_actor_type(actor_type: str) -> None:
    _ = actor_type_var.set(actor_type)


def set_actor_id(actor_id: uuid.UUID | None) -> None:
    _ = actor_id_var.set(actor_id)


def clear_usage_context() -> None:
    """Best-effort cleanup to avoid cross-request leakage."""
    _ = request_id_var.set(None)
    _ = request_started_at_var.set(None)
    _ = request_duration_ms_var.set(None)
    _ = request_method_var.set(None)
    _ = request_path_var.set(None)
    _ = tenant_id_var.set(None)
    _ = graph_name_var.set(None)
    _ = actor_type_var.set("unknown")
    _ = actor_id_var.set(None)

from __future__ import annotations

import builtins
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Dict, Iterator, List, Optional


if not hasattr(builtins, "_phishing_api_call_metrics_context"):
    setattr(
        builtins,
        "_phishing_api_call_metrics_context",
        ContextVar("api_call_metrics", default=None),
    )

_CURRENT_CALLS: ContextVar[Optional[List[Dict[str, Any]]]] = getattr(
    builtins,
    "_phishing_api_call_metrics_context",
)


@contextmanager
def collect_api_calls() -> Iterator[List[Dict[str, Any]]]:
    calls: List[Dict[str, Any]] = []
    token = _CURRENT_CALLS.set(calls)
    try:
        yield calls
    finally:
        _CURRENT_CALLS.reset(token)


def record_api_call(
    *,
    provider: str,
    endpoint: str,
    method: str,
    duration_ms: float,
    url: Optional[str] = None,
    target: Optional[str] = None,
    http_status: Optional[int] = None,
    success: Optional[bool] = None,
    error: Optional[str] = None,
) -> None:
    calls = _CURRENT_CALLS.get()
    if calls is None:
        return
    calls.append(
        {
            "provider": provider,
            "endpoint": endpoint,
            "method": method,
            "url": url,
            "target": target,
            "http_status": http_status,
            "success": success,
            "error": error,
            "duration_ms": float(duration_ms),
        }
    )


__all__ = ["collect_api_calls", "record_api_call"]

from __future__ import annotations

"""
Cuenta cabeceras Received parseables para estimar la longitud de la ruta de entrega del mensaje.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ensure_enrichment(email: Dict[str, Any]) -> None:
    email.setdefault("enrichment", {})
    email["enrichment"].setdefault(
        "received_hops_count",
        {
            "checked": False,
            "timestamp": None,
            "value": 0,
            "detail": None,
        },
    )


def _extract_string(value: Any) -> Optional[str]:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        raw = value.get("raw")
        return raw if isinstance(raw, str) else None
    return None


def _iter_header_values(value: Any) -> Iterable[str]:
    if isinstance(value, list):
        for item in value:
            s = _extract_string(item)
            if s:
                yield s
        return
    s = _extract_string(value)
    if s:
        yield s


def _count_received(values: Any) -> int:
    return sum(1 for _ in _iter_header_values(values))


def enrich_received_hops_count_in_data(email: Dict[str, Any], force: bool = False) -> bool:
    _ensure_enrichment(email)
    entry = email["enrichment"]["received_hops_count"]

    if entry.get("checked") and not force:
        return False

    headers = email.get("headers") or {}
    headers = headers if isinstance(headers, dict) else {}
    received_values = headers.get("received")

    count = _count_received(received_values)
    insufficient = count == 0

    entry["checked"] = True
    entry["timestamp"] = _now_iso()
    entry["value"] = int(count)
    entry["detail"] = {
        "received_count": int(count),
        "insufficient_data": insufficient,
    }
    return True


__all__ = ["enrich_received_hops_count_in_data"]

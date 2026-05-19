from __future__ import annotations

"""
Calcula el delta temporal entre cabeceras Received parseables usando la primera y ultima fecha util.
"""

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ensure_enrichment(email: Dict[str, Any]) -> None:
    email.setdefault("enrichment", {})
    email["enrichment"].setdefault(
        "received_time_delta",
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


def _received_timestamp_tail(line: str) -> Optional[str]:
    if not line or not isinstance(line, str):
        return None
    if ";" not in line:
        return None
    tail = line.rsplit(";", 1)[-1].strip()
    return tail or None


def _parse_received_datetime(line: str) -> Tuple[Optional[datetime], Optional[str], Optional[str]]:
    """
    Returns (datetime, tail, error).
    """
    tail = _received_timestamp_tail(line)
    if not tail:
        return None, None, "no_semicolon_or_tail"
    try:
        dt = parsedate_to_datetime(tail)
    except Exception as e:
        return None, tail, f"parse_error:{e}"
    if dt is None:
        return None, tail, "parse_failed"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt, tail, None


def _pick_first_parsable(values: List[str]) -> Tuple[Optional[int], Optional[datetime], Optional[str], Optional[str]]:
    for idx, line in enumerate(values):
        dt, tail, err = _parse_received_datetime(line)
        if dt is not None:
            return idx, dt, tail, None
    return None, None, None, "no_parsable_timestamp"


def _pick_last_parsable(values: List[str]) -> Tuple[Optional[int], Optional[datetime], Optional[str], Optional[str]]:
    for rev_idx, line in enumerate(reversed(values)):
        idx = len(values) - 1 - rev_idx
        dt, tail, err = _parse_received_datetime(line)
        if dt is not None:
            return idx, dt, tail, None
    return None, None, None, "no_parsable_timestamp"


def enrich_received_time_delta_in_data(email: Dict[str, Any], force: bool = False) -> bool:
    _ensure_enrichment(email)
    entry = email["enrichment"]["received_time_delta"]

    if entry.get("checked") and not force:
        return False

    headers = email.get("headers") or {}
    headers = headers if isinstance(headers, dict) else {}
    received_values = list(_iter_header_values(headers.get("received")))

    first_idx, first_dt, first_tail, first_err = _pick_first_parsable(received_values)
    last_idx, last_dt, last_tail, last_err = _pick_last_parsable(received_values)

    delta_seconds: Optional[int] = None
    if first_dt is not None and last_dt is not None and first_idx is not None and last_idx is not None:
        if first_idx != last_idx:
            delta_seconds = int(abs((first_dt - last_dt).total_seconds()))
        else:
            delta_seconds = 0

    insufficient = (
        len(received_values) < 2
        or first_dt is None
        or last_dt is None
        or first_idx is None
        or last_idx is None
        or first_idx == last_idx
    )

    value = int(delta_seconds or 0)

    entry["checked"] = True
    entry["timestamp"] = _now_iso()
    entry["value"] = value
    entry["detail"] = {
        "received_count": int(len(received_values)),
        "first_index": first_idx,
        "last_index": last_idx,
        "first_datetime": first_dt.isoformat() if first_dt else None,
        "last_datetime": last_dt.isoformat() if last_dt else None,
        "delta_seconds": delta_seconds,
        "delta_minutes": (delta_seconds / 60.0) if isinstance(delta_seconds, int) else None,
        "first_tail": first_tail,
        "last_tail": last_tail,
        "first_error": first_err,
        "last_error": last_err,
        "insufficient_data": bool(insufficient),
    }
    return True


__all__ = ["enrich_received_time_delta_in_data"]

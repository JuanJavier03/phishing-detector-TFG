from __future__ import annotations

"""
Gestiona la cache persistente de respuestas de Neutrino en la base de datos del
backend. La clave respeta el endpoint y el payload que ya usa cada subcriterio;
solo normaliza formato, mayusculas y orden para evitar duplicados equivalentes.
"""

import json
import os
import sys
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import RLock
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from sqlalchemy import text


BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_DIR = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from api.db.session import get_engine  # noqa: E402


load_dotenv(BACKEND_DIR / ".env")
load_dotenv(REPO_DIR / ".env", override=False)

DEFAULT_NEUTRINO_CACHE_TTL_SECONDS = 24 * 60 * 60
_MEMORY_CACHE: Dict[str, Dict[str, Any]] = {}
_MEMORY_CACHE_LOCK = RLock()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _cache_enabled() -> bool:
    raw = os.getenv("NEUTRINO_CACHE_ENABLED")
    if raw is None:
        return True
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def _ttl_seconds() -> int:
    raw = os.getenv("NEUTRINO_CACHE_TTL_SECONDS")
    if raw is None or not raw.strip():
        return DEFAULT_NEUTRINO_CACHE_TTL_SECONDS
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_NEUTRINO_CACHE_TTL_SECONDS
    return max(value, 60)


def _json_default(value: Any) -> str:
    return str(value)


def normalized_payload(payload_data: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(payload_data)
    data.setdefault("output-case", "snake")
    normalized: Dict[str, Any] = {}
    for raw_key, raw_value in sorted(data.items(), key=lambda item: str(item[0])):
        key = str(raw_key)
        value = raw_value
        if key in {"host", "domain", "ip"} and isinstance(value, str):
            value = value.strip().lower()
        normalized[key] = value
    return normalized


def build_cache_key(endpoint: str, payload_data: Dict[str, Any]) -> str:
    endpoint_key = endpoint.strip().lower()
    payload_json = json.dumps(
        normalized_payload(payload_data),
        sort_keys=True,
        separators=(",", ":"),
        default=_json_default,
    )
    return f"{endpoint_key}|{payload_json}"


def _memory_get(cache_key: str, now: datetime) -> Optional[Dict[str, Any]]:
    with _MEMORY_CACHE_LOCK:
        entry = _MEMORY_CACHE.get(cache_key)
        if not entry:
            return None
        expires_at = entry.get("expires_at")
        if not isinstance(expires_at, datetime) or expires_at <= now:
            _MEMORY_CACHE.pop(cache_key, None)
            return None
        response = entry.get("response")
        return deepcopy(response) if isinstance(response, dict) else None


def _memory_put(cache_key: str, response: Dict[str, Any], expires_at: datetime) -> None:
    with _MEMORY_CACHE_LOCK:
        _MEMORY_CACHE[cache_key] = {
            "response": deepcopy(response),
            "expires_at": expires_at,
        }


def get_cached_response(cache_key: str) -> Optional[Dict[str, Any]]:
    if not _cache_enabled():
        return None

    now = _utc_now()
    cached = _memory_get(cache_key, now)
    if cached is not None:
        return cached

    query = text(
        """
        UPDATE neutrino_api_cache
        SET last_used_at = now(),
            hit_count = hit_count + 1
        WHERE cache_key = :cache_key
          AND expires_at > now()
        RETURNING response, expires_at
        """
    )
    try:
        with get_engine().begin() as connection:
            row = connection.execute(query, {"cache_key": cache_key}).mappings().first()
    except Exception:
        return None

    if not row:
        return None

    response = row.get("response")
    expires_at = row.get("expires_at")
    if isinstance(response, dict) and isinstance(expires_at, datetime):
        _memory_put(cache_key, response, expires_at)
        return deepcopy(response)
    return None


def store_cached_response(
    *,
    cache_key: str,
    endpoint: str,
    payload_data: Dict[str, Any],
    response: Dict[str, Any],
    http_status: Optional[int],
) -> None:
    if not _cache_enabled():
        return
    if http_status != 200:
        return
    if not isinstance(response, dict):
        return

    payload = normalized_payload(payload_data)
    expires_at = _utc_now() + timedelta(seconds=_ttl_seconds())
    _memory_put(cache_key, response, expires_at)
    query = text(
        """
        INSERT INTO neutrino_api_cache
            (cache_key, endpoint, payload, response, http_status, fetched_at, expires_at, last_used_at, hit_count)
        VALUES
            (:cache_key, :endpoint, CAST(:payload AS jsonb), CAST(:response AS jsonb), :http_status, now(), :expires_at, NULL, 0)
        ON CONFLICT (cache_key) DO UPDATE SET
            endpoint = EXCLUDED.endpoint,
            payload = EXCLUDED.payload,
            response = EXCLUDED.response,
            http_status = EXCLUDED.http_status,
            fetched_at = now(),
            expires_at = EXCLUDED.expires_at,
            last_used_at = NULL,
            hit_count = 0
        """
    )
    params = {
        "cache_key": cache_key,
        "endpoint": endpoint.strip().lower(),
        "payload": json.dumps(payload, sort_keys=True, default=_json_default),
        "response": json.dumps(response, sort_keys=True, default=_json_default),
        "http_status": http_status,
        "expires_at": expires_at,
    }
    try:
        with get_engine().begin() as connection:
            connection.execute(query, params)
    except Exception:
        return


def clear_neutrino_cache(*, include_persistent: bool = False) -> None:
    with _MEMORY_CACHE_LOCK:
        _MEMORY_CACHE.clear()

    if not include_persistent:
        return

    try:
        with get_engine().begin() as connection:
            connection.execute(text("DELETE FROM neutrino_api_cache"))
    except Exception:
        return


def neutrino_cache_info() -> Dict[str, Any]:
    with _MEMORY_CACHE_LOCK:
        memory_size = len(_MEMORY_CACHE)

    persistent_size = None
    try:
        with get_engine().begin() as connection:
            persistent_size = connection.execute(text("SELECT count(*) FROM neutrino_api_cache")).scalar_one()
    except Exception:
        persistent_size = None

    return {
        "memory_size": memory_size,
        "persistent_size": persistent_size,
        "ttl_seconds": _ttl_seconds(),
        "enabled": _cache_enabled(),
    }


__all__ = [
    "build_cache_key",
    "clear_neutrino_cache",
    "get_cached_response",
    "neutrino_cache_info",
    "normalized_payload",
    "store_cached_response",
]

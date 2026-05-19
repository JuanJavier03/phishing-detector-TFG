#!/usr/bin/env python3
"""
Contiene el cliente HTTP comun para las consultas a Neutrino, incluyendo credenciales,
timeouts, cache persistente y normalizacion de respuestas. La cache evita repetir
consultas identicas entre subcriterios y correos durante la ventana TTL configurada.
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv

from enrichment.api_call_tracking import record_api_call
from utils.neutrino_cache import (
    build_cache_key,
    clear_neutrino_cache,
    get_cached_response,
    neutrino_cache_info,
    store_cached_response,
)


load_dotenv()

NEUTRINO_DEFAULT_BASE_URL = "https://eu.neutrinoapi.net"
NEUTRINO_CONNECT_TIMEOUT_SECONDS = 15
NEUTRINO_READ_TIMEOUT_SECONDS = 120


def _base_url() -> str:
    raw = os.getenv("NEUTRINO_BASE_URL") or NEUTRINO_DEFAULT_BASE_URL
    return raw.strip().rstrip("/")


def _credentials() -> tuple[Optional[str], Optional[str]]:
    user_id = os.getenv("NEUTRINO_USER_ID")
    api_key = os.getenv("NEUTRINO_API_KEY")
    clean_user_id = user_id.strip() if isinstance(user_id, str) and user_id.strip() else None
    clean_api_key = api_key.strip() if isinstance(api_key, str) and api_key.strip() else None
    return clean_user_id, clean_api_key


def _timeout() -> tuple[float, float]:
    connect_raw = os.getenv("NEUTRINO_CONNECT_TIMEOUT_SECONDS")
    read_raw = os.getenv("NEUTRINO_READ_TIMEOUT_SECONDS")

    try:
        connect_timeout = float(connect_raw) if connect_raw is not None else float(NEUTRINO_CONNECT_TIMEOUT_SECONDS)
    except Exception:
        connect_timeout = float(NEUTRINO_CONNECT_TIMEOUT_SECONDS)

    try:
        read_timeout = float(read_raw) if read_raw is not None else float(NEUTRINO_READ_TIMEOUT_SECONDS)
    except Exception:
        read_timeout = float(NEUTRINO_READ_TIMEOUT_SECONDS)

    return max(connect_timeout, 0.5), max(read_timeout, 0.5)


def _first_value(payload: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in payload:
            return payload.get(key)
    return None


def _parse_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
    return None


def _parse_country_code(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    cleaned = value.strip().upper()
    if len(cleaned) == 2 and cleaned.isalpha():
        return cleaned
    return None


def _make_detail_from_payload(
    payload: Dict[str, Any],
    *,
    http_status: Optional[int],
) -> Dict[str, Any]:
    detail: Dict[str, Any] = {
        "http_status": http_status,
    }
    api_error_msg = _first_value(payload, "api-error-msg", "api_error_msg")
    if isinstance(api_error_msg, str) and api_error_msg.strip():
        detail["error"] = f"neutrino_api_error:{api_error_msg.strip()}"
    else:
        api_error = _first_value(payload, "api-error", "api_error")
        if api_error is not None:
            detail["error"] = f"neutrino_api_error:{api_error}"
    return detail


def clear_neutrino_request_cache(*, include_persistent: bool = False) -> None:
    clear_neutrino_cache(include_persistent=include_persistent)


def neutrino_request_cache_info() -> Dict[str, Any]:
    return neutrino_cache_info()


def _request(
    *,
    endpoint: str,
    payload_data: Dict[str, Any],
    force: bool = False,
) -> Dict[str, Any]:
    # "force" fuerza recalcular el enriquecimiento persistido, pero no repite
    # la misma llamada HTTP si la cache Neutrino sigue vigente.
    _ = force
    cache_key = build_cache_key(endpoint, payload_data)
    cached_response = get_cached_response(cache_key)
    if cached_response is not None:
        return cached_response

    user_id, api_key = _credentials()
    if not user_id or not api_key:
        return {
            "payload": {},
            "detail": {
                "http_status": None,
                "error": "neutrino_missing_credentials",
            },
        }

    url = f"{_base_url()}/{endpoint}"
    headers = {
        "User-ID": user_id,
        "API-Key": api_key,
        "User-Agent": "phishing-detector/1.0",
    }
    data = dict(payload_data)
    data.setdefault("output-case", "snake")
    started = time.perf_counter()
    target = payload_data.get("host") or payload_data.get("ip") or ""

    try:
        response = requests.post(url, headers=headers, data=data, timeout=_timeout())
    except Exception as exc:
        error = f"neutrino_request_error:endpoint={endpoint};target={target};detail={exc}"
        record_api_call(
            provider="neutrino",
            endpoint=endpoint,
            method="POST",
            url=url,
            target=str(target),
            http_status=None,
            success=False,
            error=error,
            duration_ms=(time.perf_counter() - started) * 1000,
        )
        return {
            "payload": {},
            "detail": {
                "http_status": None,
                "error": error,
            },
        }

    try:
        payload = response.json()
    except Exception as exc:
        error = (
            f"neutrino_json_error:endpoint={endpoint};target={target};"
            f"http_status={response.status_code};detail={exc}"
        )
        record_api_call(
            provider="neutrino",
            endpoint=endpoint,
            method="POST",
            url=url,
            target=str(target),
            http_status=response.status_code,
            success=False,
            error=error,
            duration_ms=(time.perf_counter() - started) * 1000,
        )
        return {
            "payload": {},
            "detail": {
                "http_status": response.status_code,
                "error": error,
            },
        }

    if response.status_code != 200:
        detail = _make_detail_from_payload(payload, http_status=response.status_code)
        error = detail.get("error") or f"neutrino_http_{response.status_code}:endpoint={endpoint};target={target}"
        detail["error"] = error
        record_api_call(
            provider="neutrino",
            endpoint=endpoint,
            method="POST",
            url=url,
            target=str(target),
            http_status=response.status_code,
            success=False,
            error=str(error),
            duration_ms=(time.perf_counter() - started) * 1000,
        )
        return {"payload": payload, "detail": detail}

    detail = _make_detail_from_payload(payload, http_status=response.status_code)
    result = {"payload": payload, "detail": detail}
    record_api_call(
        provider="neutrino",
        endpoint=endpoint,
        method="POST",
        url=url,
        target=str(target),
        http_status=response.status_code,
        success=not bool(detail.get("error")),
        error=str(detail.get("error")) if detail.get("error") else None,
        duration_ms=(time.perf_counter() - started) * 1000,
    )
    if not detail.get("error"):
        store_cached_response(
            cache_key=cache_key,
            endpoint=endpoint,
            payload_data=payload_data,
            response=result,
            http_status=response.status_code,
        )
    return result


def lookup_domain(domain: str, *, force: bool = False) -> Dict[str, Any]:
    response = _request(
        endpoint="domain-lookup",
        payload_data={"host": domain},
        force=force,
    )
    payload = response["payload"]
    detail = dict(response["detail"])
    detail["endpoint"] = "domain-lookup"
    detail["domain"] = domain
    detail["valid"] = _parse_bool(_first_value(payload, "valid"))
    detail["is_malicious"] = _parse_bool(_first_value(payload, "is-malicious", "is_malicious"))
    detail["registered_date"] = _first_value(payload, "registered-date", "registered_date")
    detail["tld_cc"] = _parse_country_code(_first_value(payload, "tld-cc", "tld_cc"))
    return detail


def lookup_host_reputation(host: str, *, force: bool = False) -> Dict[str, Any]:
    response = _request(
        endpoint="host-reputation",
        payload_data={"host": host},
        force=force,
    )
    payload = response["payload"]
    detail = dict(response["detail"])
    detail["endpoint"] = "host-reputation"
    detail["host"] = host
    detail["is_listed"] = _parse_bool(_first_value(payload, "is-listed", "is_listed"))
    detail["list_count"] = _first_value(payload, "list-count", "list_count")
    detail["lists"] = _first_value(payload, "lists")
    return detail


def lookup_ip_blocklist(ip: str, *, force: bool = False) -> Dict[str, Any]:
    response = _request(
        endpoint="ip-blocklist",
        payload_data={"ip": ip},
        force=force,
    )
    payload = response["payload"]
    detail = dict(response["detail"])
    detail["endpoint"] = "ip-blocklist"
    detail["ip"] = ip
    detail["is_listed"] = _parse_bool(_first_value(payload, "is-listed", "is_listed"))
    detail["valid"] = _parse_bool(_first_value(payload, "valid"))
    detail["is_bogon"] = _parse_bool(_first_value(payload, "is-bogon", "is_bogon"))
    return detail


def lookup_ip_info(ip: str, *, force: bool = False) -> Dict[str, Any]:
    response = _request(
        endpoint="ip-info",
        payload_data={"ip": ip, "reverse-lookup": "false"},
        force=force,
    )
    payload = response["payload"]
    detail = dict(response["detail"])
    detail["endpoint"] = "ip-info"
    detail["ip"] = ip
    detail["country_code"] = _parse_country_code(_first_value(payload, "country-code", "country_code"))
    detail["country"] = _first_value(payload, "country")
    detail["valid"] = _parse_bool(_first_value(payload, "valid"))
    detail["is_bogon"] = _parse_bool(_first_value(payload, "is-bogon", "is_bogon"))
    return detail


__all__ = [
    "clear_neutrino_request_cache",
    "lookup_domain",
    "lookup_host_reputation",
    "lookup_ip_blocklist",
    "lookup_ip_info",
    "neutrino_request_cache_info",
]

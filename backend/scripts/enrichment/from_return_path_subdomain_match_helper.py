from __future__ import annotations

"""
Compara el dominio base de From con Return-Path y registra si existe discrepancia relevante en cabeceras.
"""

from datetime import datetime, timezone
from typing import Any, Dict

from utils.origin_resolution import extract_host_from_address_header
from utils.subdomain_utils import normalize_subdomain
from utils.domain_utils import base_domain, extract_host_parts


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ensure_enrichment(email: Dict[str, Any]) -> None:
    email.setdefault("enrichment", {})
    email["enrichment"].setdefault(
        "from_return_path_subdomain_match",
        {
            "checked": False,
            "timestamp": None,
            "value": 0,
            "detail": None,
        },
    )


def enrich_from_return_path_subdomain_match_in_data(
    email: Dict[str, Any],
    force: bool = False,
) -> bool:
    _ensure_enrichment(email)
    entry = email["enrichment"]["from_return_path_subdomain_match"]

    if entry.get("checked") and not force:
        return False

    headers = email.get("headers") or {}
    headers = headers if isinstance(headers, dict) else {}

    from_host_raw, from_raw = extract_host_from_address_header(headers.get("from"))
    return_host_raw, return_raw = extract_host_from_address_header(headers.get("return_path"))

    from_sub = None
    from_domain_part = None
    from_suffix = None
    from_registrable = None

    return_sub = None
    return_domain_part = None
    return_suffix = None
    return_registrable = None

    same_base_domain = None
    from_subdomain_normalized = None
    return_subdomain_normalized = None
    value = 1
    insufficient = True

    if from_host_raw:
        _from_host, from_registrable, from_sub, from_domain_part, from_suffix = extract_host_parts(from_host_raw)

    if return_host_raw:
        _return_host, return_registrable, return_sub, return_domain_part, return_suffix = extract_host_parts(return_host_raw)

    from_base_domain = base_domain(from_host_raw)
    return_base_domain = base_domain(return_host_raw)

    if from_base_domain and return_base_domain:
        same_base_domain = from_base_domain == return_base_domain
        from_subdomain_normalized = normalize_subdomain(from_sub)
        return_subdomain_normalized = normalize_subdomain(return_sub)
        value = 0 if same_base_domain else 1
        insufficient = False

    entry["checked"] = True
    entry["timestamp"] = _now_iso()
    entry["value"] = int(value)
    entry["detail"] = {
        "from_raw": from_raw,
        "return_path_raw": return_raw,
        "from_domain": from_host_raw,
        "return_path_domain": return_host_raw,
        "from_base_domain": from_base_domain,
        "return_path_base_domain": return_base_domain,
        "from_subdomain": from_sub,
        "return_path_subdomain": return_sub,
        "from_subdomain_normalized": from_subdomain_normalized,
        "return_path_subdomain_normalized": return_subdomain_normalized,
        "from_registrable_domain": from_registrable,
        "return_path_registrable_domain": return_registrable,
        "same_base_domain": same_base_domain,
        "same_registrable_domain": same_base_domain,
        "subdomain_match": same_base_domain,
        "insufficient_data": insufficient,
        "fallback_value_applied": insufficient,
    }
    return True


__all__ = ["enrich_from_return_path_subdomain_match_in_data"]

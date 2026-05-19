from __future__ import annotations

"""
Compara el pais asociado al dominio remitente con el pais de la IP de origen cuando el dominio permite una comparacion fiable.
"""

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from dotenv import load_dotenv

from enrichment.neutrino_client import lookup_domain, lookup_ip_info
from utils.origin_resolution import resolve_sender_domain, resolve_sender_ip_from_headers
from utils.ip_utils import resolve_ip_from_email

try:
    import pycountry
except Exception:
    pycountry = None


load_dotenv()

DEFAULT_SCORE_RISK = 1.0
UNKNOWN_SCORE = 0.5
SAFE_SCORE = 0.0
UNRELIABLE_SENDER_DOMAIN_REASON = "sender_domain_not_reliably_available_dmarc_not_pass"
NO_COUNTRY_TLD_REASON = "domain_has_no_country_tld"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ensure_enrichment(email: Dict[str, Any]) -> None:
    email.setdefault("enrichment", {})
    email["enrichment"].setdefault(
        "domain_vs_ip_country",
        {
            "checked": False,
            "timestamp": None,
            "domain": None,
            "ip": None,
            "domain_country": None,
            "ip_country": None,
            "match": None,
            "score": None,
            "detail": None,
        },
    )


def _allow_http_apis() -> bool:
    raw = os.getenv("DOMAINIP_ALLOW_HTTP")
    if raw is None:
        return True
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def _country_display(code: Optional[str]) -> Optional[str]:
    if not isinstance(code, str) or len(code) != 2:
        return None
    normalized = code.upper()
    if pycountry is not None:
        try:
            country = pycountry.countries.get(alpha_2=normalized)
            if country and getattr(country, "name", None):
                return country.name
        except Exception:
            pass
    return normalized


def _query_domain_country(domain: str, force: bool = False) -> Tuple[Optional[str], Dict[str, Any]]:
    detail = lookup_domain(domain, force=force)
    if detail.get("error"):
        return None, detail
    country_code = detail.get("tld_cc")
    if not isinstance(country_code, str):
        detail["error"] = "neutrino_missing_tld_cc"
        return None, detail
    detail["country_source"] = "tld_cc"
    return country_code, detail


def _query_ip_country(ip: str, force: bool = False) -> Tuple[Optional[str], Dict[str, Any]]:
    detail = lookup_ip_info(ip, force=force)
    if detail.get("error"):
        return None, detail
    country_code = detail.get("country_code")
    if not isinstance(country_code, str):
        detail["error"] = "neutrino_missing_country_code"
        return None, detail
    detail["country_source"] = "ip_info"
    return country_code, detail


def _country_tld_label_from_resolution(domain_resolution: Dict[str, Any]) -> Optional[str]:
    suffix = domain_resolution.get("suffix")
    if not isinstance(suffix, str) or not suffix.strip():
        return None
    last_label = suffix.strip().lower().split(".")[-1]
    if len(last_label) == 2 and last_label.isalpha():
        return last_label.upper()
    return None


def enrich_domain_vs_ip_country_in_data(
    email: Dict[str, Any],
    force: bool = False,
    allow_http: Optional[bool] = None,
) -> bool:
    _ensure_enrichment(email)
    entry = email["enrichment"]["domain_vs_ip_country"]
    if entry.get("checked") and not force:
        return False

    headers = email.get("headers") or {}
    headers = headers if isinstance(headers, dict) else {}
    domain_resolution = resolve_sender_domain(headers, reliable_only=True)
    domain = domain_resolution.get("host") if isinstance(domain_resolution.get("host"), str) else None
    domain_source = domain_resolution.get("source") if isinstance(domain_resolution.get("source"), str) else "none"
    domain_candidates = (
        domain_resolution.get("host_candidates")
        if isinstance(domain_resolution.get("host_candidates"), dict)
        else {}
    )

    if not domain:
        entry.update(
            {
                "checked": True,
                "timestamp": _now_iso(),
                "domain": None,
                "ip": None,
                "domain_country": None,
                "domain_country_code": None,
                "ip_country": None,
                "ip_country_code": None,
                "match": None,
                "score": None,
                "detail": {
                    "method": "neutrino.country_compare",
                    "http_apis_enabled": _allow_http_apis() if allow_http is None else allow_http,
                    "insufficient_data": True,
                    "comparison_status": "no_data",
                    "fallback_value_applied": False,
                    "error_reason": UNRELIABLE_SENDER_DOMAIN_REASON,
                    "skipped_due_unreliable_sender_domain": True,
                    "domain_source": domain_source,
                    "domain_candidates": domain_candidates,
                    "ip_source": "not_attempted",
                    "resolution_detail": None,
                    "api_detail": {},
                },
            }
        )
        return True

    country_tld_label = _country_tld_label_from_resolution(domain_resolution)
    if not country_tld_label:
        entry.update(
            {
                "checked": True,
                "timestamp": _now_iso(),
                "domain": domain,
                "ip": None,
                "domain_country": None,
                "domain_country_code": None,
                "ip_country": None,
                "ip_country_code": None,
                "match": None,
                "score": None,
                "detail": {
                    "method": "neutrino.country_compare",
                    "http_apis_enabled": _allow_http_apis() if allow_http is None else allow_http,
                    "insufficient_data": False,
                    "comparison_status": "not_applicable_no_country_tld",
                    "fallback_value_applied": False,
                    "error_reason": None,
                    "reason_code": NO_COUNTRY_TLD_REASON,
                    "reason": "El dominio del remitente no usa un ccTLD y no permite comparar pais de dominio contra pais de IP.",
                    "mcdm_excluded": True,
                    "mcdm_exclusion_reason": NO_COUNTRY_TLD_REASON,
                    "analysis_status": "completed_not_applicable",
                    "domain_source": domain_source,
                    "domain_candidates": domain_candidates,
                    "domain_suffix": domain_resolution.get("suffix"),
                    "country_tld_label": None,
                    "ip_source": "not_attempted",
                    "resolution_detail": None,
                    "api_detail": {},
                },
            }
        )
        return True

    ip, ip_source = resolve_sender_ip_from_headers(headers)
    resolution_detail = None
    if not ip:
        resolved_ip, resolved_source, detail = resolve_ip_from_email(email)
        resolution_detail = detail
        if resolved_ip:
            ip = resolved_ip
            ip_source = resolved_source

    http_enabled = _allow_http_apis() if allow_http is None else allow_http
    api_detail: Dict[str, Any] = {}
    error_reason = None
    domain_code = None
    ip_code = None

    if not ip:
        error_reason = "ip_not_found"
    elif not http_enabled:
        error_reason = "http_apis_disabled"
        api_detail["error"] = error_reason
    else:
        domain_code, domain_detail = _query_domain_country(domain, force=force)
        ip_code, ip_detail = _query_ip_country(ip, force=force)
        api_detail["domain"] = domain_detail
        api_detail["ip"] = ip_detail
        if not domain_code:
            error_reason = str(domain_detail.get("error") or "domain_country_not_found")
        elif not ip_code:
            error_reason = str(ip_detail.get("error") or "ip_country_not_found")

    match = None
    comparison_status = "fallback_risk"
    insufficient = True
    score = UNKNOWN_SCORE
    if domain_code and ip_code:
        match = domain_code == ip_code
        comparison_status = "match" if match else "mismatch"
        insufficient = False
        score = SAFE_SCORE if match else DEFAULT_SCORE_RISK

    detail = {
        "method": "neutrino.country_compare",
        "http_apis_enabled": http_enabled,
        "insufficient_data": insufficient,
        "comparison_status": comparison_status,
        "fallback_value_applied": insufficient,
        "error_reason": error_reason,
        "reason_code": error_reason,
        "reason": None,
        "mcdm_excluded": False,
        "mcdm_exclusion_reason": None,
        "analysis_status": "completed",
        "domain_source": domain_source,
        "domain_candidates": domain_candidates,
        "domain_suffix": domain_resolution.get("suffix"),
        "country_tld_label": country_tld_label,
        "ip_source": ip_source,
        "resolution_detail": resolution_detail,
        "api_detail": api_detail,
    }

    entry.update(
        {
            "checked": True,
            "timestamp": _now_iso(),
            "domain": domain,
            "ip": ip,
            "domain_country": _country_display(domain_code),
            "domain_country_code": domain_code,
            "ip_country": _country_display(ip_code),
            "ip_country_code": ip_code,
            "match": match,
            "score": float(score),
            "detail": detail,
        }
    )
    return True


__all__ = [
    "DEFAULT_SCORE_RISK",
    "UNKNOWN_SCORE",
    "SAFE_SCORE",
    "_query_domain_country",
    "_query_ip_country",
    "_country_display",
    "enrich_domain_vs_ip_country_in_data",
]

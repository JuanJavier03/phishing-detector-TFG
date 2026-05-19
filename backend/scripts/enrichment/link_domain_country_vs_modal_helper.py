from __future__ import annotations

"""
Compara paises entre dominios enlazados y el dominio modal/remitente cuando hay datos suficientes para hacerlo.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from enrichment import domain_vs_ip_country_helper as domip
from enrichment.link_domain_utils import (
    link_api_skip_context,
    extract_modal_domain,
    limit_link_api_lookups,
)
from utils.link_url_utils import (
    extract_link_hosts,
    unique_link_hosts,
)
from utils.domain_utils import extract_host_parts


UNRELIABLE_SENDER_DOMAIN_REASON = "sender_domain_not_reliably_available_dmarc_not_pass"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ensure_enrichment(email: Dict[str, Any]) -> None:
    email.setdefault("enrichment", {})
    email["enrichment"].setdefault(
        "link_domain_country_vs_modal",
        {
            "checked": False,
            "timestamp": None,
            "value": None,
            "detail": None,
        },
    )


def _get_domain_country(domain: Optional[str], force: bool) -> Dict[str, Any]:
    allow_http = domip._allow_http_apis()
    if not domain:
        return {
            "domain": None,
            "country": None,
            "country_code": None,
            "detail": {
                "method": "neutrino.country_compare",
                "http_apis_enabled": allow_http,
                "insufficient_data": True,
                "fallback_value_applied": True,
                "api_detail": {},
            },
        }

    _normalized_host, _registrable_domain, _subdomain, _domain_part, suffix = extract_host_parts(domain)
    country_tld_label = domip._country_tld_label_from_resolution({"suffix": suffix})
    if not country_tld_label:
        return {
            "domain": domain,
            "country": None,
            "country_code": None,
            "detail": {
                "method": "neutrino.country_compare",
                "http_apis_enabled": allow_http,
                "insufficient_data": False,
                "comparison_status": "not_applicable_no_country_tld",
                "fallback_value_applied": False,
                "error_reason": None,
                "reason_code": domip.NO_COUNTRY_TLD_REASON,
                "reason": "El dominio no usa un ccTLD y no permite comparacion geografica fiable.",
                "mcdm_excluded": True,
                "mcdm_exclusion_reason": domip.NO_COUNTRY_TLD_REASON,
                "analysis_status": "completed_not_applicable",
                "domain_suffix": suffix,
                "country_tld_label": None,
                "api_detail": {},
            },
        }

    if not allow_http:
        detail = {
            "method": "neutrino.country_compare",
            "http_apis_enabled": allow_http,
            "insufficient_data": True,
            "fallback_value_applied": True,
            "api_detail": {"error": "http_apis_disabled"},
        }
        return {"domain": domain, "country": None, "country_code": None, "detail": detail}

    api_detail: Dict[str, Any] = {}
    domain_country, domain_detail = domip._query_domain_country(domain, force=force)
    api_detail["domain"] = domain_detail
    domain_code = domain_country if isinstance(domain_country, str) else None
    domain_country_display = domip._country_display(domain_code)

    detail = {
        "method": "neutrino.country_compare",
        "http_apis_enabled": allow_http,
        "insufficient_data": not bool(domain_country),
        "fallback_value_applied": not bool(domain_country),
        "comparison_status": "resolved" if domain_country else "no_data",
        "error_reason": None if domain_country else str(api_detail.get("domain", {}).get("error") or "domain_country_not_found"),
        "reason_code": None if domain_country else str(api_detail.get("domain", {}).get("error") or "domain_country_not_found"),
        "reason": None,
        "mcdm_excluded": False,
        "mcdm_exclusion_reason": None,
        "analysis_status": "completed",
        "domain_suffix": suffix,
        "country_tld_label": country_tld_label,
        "api_detail": api_detail,
    }

    return {
        "domain": domain,
        "country": domain_country_display,
        "country_code": domain_code,
        "detail": detail,
    }


def enrich_link_domain_country_vs_modal_in_data(
    email: Dict[str, Any],
    force: bool = False,
    primary_only: bool = False,
) -> bool:
    _ensure_enrichment(email)
    entry = email["enrichment"]["link_domain_country_vs_modal"]

    if entry.get("checked") and not force:
        return False

    modal = extract_modal_domain(email)
    modal_domain = modal.get("host")

    if not isinstance(modal_domain, str) or not modal_domain:
        entry["checked"] = True
        entry["timestamp"] = _now_iso()
        entry["value"] = None
        entry["detail"] = {
            "modal_domain": None,
            "modal_country": None,
            "modal_country_code": None,
            "links": [],
            "mismatch_any": False,
            "insufficient_data": True,
            "fallback_value_applied": False,
            "error_reason": UNRELIABLE_SENDER_DOMAIN_REASON,
            "skipped_due_unreliable_sender_domain": True,
            "modal_resolution": modal,
        }
        return True

    skip_context = link_api_skip_context(email)
    if skip_context["should_skip"]:
        entry["checked"] = True
        entry["timestamp"] = _now_iso()
        entry["value"] = None
        entry["detail"] = {
            "modal_domain": modal_domain,
            "modal_country": None,
            "modal_country_code": None,
            "links": [],
            "total_unique_hosts": 0,
            "consulted_hosts": 0,
            "mismatch_any": False,
            "comparable_links": 0,
            "excluded_links": 0,
            "insufficient_links": 0,
            "insufficient_data": True,
            "fallback_value_applied": False,
            "mcdm_excluded": True,
            "mcdm_exclusion_reason": skip_context["reason_code"],
            "comparison_status": "skipped_too_many_links",
            "reason_code": skip_context["reason_code"],
            "analysis_status": "skipped",
            "skipped_due_link_count_threshold": True,
            "total_clickable_links": int(skip_context["total_links"]),
            "link_count_threshold": int(skip_context["threshold"]),
            "modal_resolution": modal,
            "modal_country_detail": None,
        }
        return True

    link_entries = extract_link_hosts(email, primary_only=primary_only)
    link_domains = unique_link_hosts(link_entries)
    consulted_domains = limit_link_api_lookups(link_domains)

    modal_country = _get_domain_country(modal_domain, force=force) if modal_domain else None
    modal_detail = modal_country.get("detail") if isinstance(modal_country, dict) else {}
    modal_detail = modal_detail if isinstance(modal_detail, dict) else {}

    if modal_detail.get("mcdm_excluded") is True:
        entry["checked"] = True
        entry["timestamp"] = _now_iso()
        entry["value"] = None
        entry["detail"] = {
            "modal_domain": modal_domain,
            "modal_country": None,
            "modal_country_code": None,
            "links": [],
            "mismatch_any": False,
            "comparable_links": 0,
            "excluded_links": 0,
            "insufficient_links": 0,
            "insufficient_data": False,
            "fallback_value_applied": False,
            "mcdm_excluded": True,
            "mcdm_exclusion_reason": domip.NO_COUNTRY_TLD_REASON,
            "comparison_status": "not_applicable_no_country_tld",
            "reason_code": domip.NO_COUNTRY_TLD_REASON,
            "analysis_status": "completed_not_applicable",
            "modal_resolution": modal,
            "modal_country_detail": modal_country,
        }
        return True

    comparisons: List[Dict[str, Any]] = []
    mismatch_any = False
    comparable_links = 0
    excluded_links = 0
    insufficient_links = 0

    for domain in consulted_domains:
        link_country = _get_domain_country(domain, force=force)
        link_detail = link_country.get("detail") if isinstance(link_country.get("detail"), dict) else {}
        if link_detail.get("mcdm_excluded") is True:
            excluded_links += 1
        link_code = link_country.get("country_code")
        modal_code = modal_country.get("country_code") if modal_country else None
        match = None
        if link_code and modal_code:
            match = link_code == modal_code
            comparable_links += 1
            if not match:
                mismatch_any = True
        elif link_detail.get("insufficient_data") is True:
            insufficient_links += 1
        comparisons.append(
            {
                "domain": domain,
                "country": link_country.get("country"),
                "country_code": link_code,
                "match_modal": match,
                "detail": link_detail,
            }
        )

    if comparable_links > 0:
        value = 1.0 if mismatch_any else 0.0
        insufficient = False
        mcdm_excluded = False
        comparison_status = "mismatch" if mismatch_any else "match"
        reason_code = None
        analysis_status = "completed"
    elif excluded_links > 0 and insufficient_links == 0:
        value = None
        insufficient = False
        mcdm_excluded = True
        comparison_status = "not_applicable_no_country_tld"
        reason_code = domip.NO_COUNTRY_TLD_REASON
        analysis_status = "completed_not_applicable"
    else:
        value = None
        insufficient = True
        mcdm_excluded = False
        comparison_status = "no_data"
        reason_code = "link_domain_country_not_available"
        analysis_status = "completed"

    entry["checked"] = True
    entry["timestamp"] = _now_iso()
    entry["value"] = float(value) if value is not None else None
    entry["detail"] = {
        "modal_domain": modal_domain,
        "modal_country": modal_country.get("country") if modal_country else None,
        "modal_country_code": modal_country.get("country_code") if modal_country else None,
        "links": comparisons,
        "total_unique_hosts": len(link_domains),
        "consulted_hosts": len(consulted_domains),
        "mismatch_any": mismatch_any,
        "comparable_links": comparable_links,
        "excluded_links": excluded_links,
        "insufficient_links": insufficient_links,
        "insufficient_data": insufficient,
        "fallback_value_applied": False,
        "mcdm_excluded": mcdm_excluded,
        "mcdm_exclusion_reason": reason_code if mcdm_excluded else None,
        "comparison_status": comparison_status,
        "reason_code": reason_code,
        "analysis_status": analysis_status,
        "modal_resolution": modal,
        "modal_country_detail": modal_country,
    }
    return True


__all__ = ["enrich_link_domain_country_vs_modal_in_data"]

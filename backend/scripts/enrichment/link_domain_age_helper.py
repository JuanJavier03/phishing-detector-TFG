from __future__ import annotations

"""
Calcula la menor antiguedad observada entre dominios enlazados y guarda la evidencia por dominio consultado.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List

from enrichment.domain_age_helper import get_email_reference_datetime, resolve_domain_age
from enrichment.link_domain_utils import (
    link_api_skip_context,
    limit_link_api_lookups,
)
from utils.link_url_utils import (
    extract_link_hosts,
    unique_link_hosts,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ensure_enrichment(email: Dict[str, Any]) -> None:
    email.setdefault("enrichment", {})
    email["enrichment"].setdefault(
        "link_domain_age",
        {
            "checked": False,
            "timestamp": None,
            "value": None,
            "detail": None,
        },
    )


def enrich_link_domain_age_in_data(
    email: Dict[str, Any],
    force: bool = False,
    primary_only: bool = False,
) -> bool:
    _ensure_enrichment(email)
    entry = email["enrichment"]["link_domain_age"]

    if entry.get("checked") and not force:
        return False

    skip_context = link_api_skip_context(email)
    if skip_context["should_skip"]:
        entry["checked"] = True
        entry["timestamp"] = _now_iso()
        entry["value"] = None
        entry["detail"] = {
            "aggregation": "min",
            "reference": None,
            "domains": [],
            "total_unique_hosts": 0,
            "consulted_hosts": 0,
            "valid_domains": 0,
            "invalid_domains": 0,
            "insufficient_data": True,
            "fallback_value_applied": False,
            "mcdm_excluded": True,
            "mcdm_exclusion_reason": skip_context["reason_code"],
            "skipped_due_link_count_threshold": True,
            "total_clickable_links": int(skip_context["total_links"]),
            "link_count_threshold": int(skip_context["threshold"]),
        }
        return True

    link_entries = extract_link_hosts(email, primary_only=primary_only)
    domains = unique_link_hosts(link_entries)
    consulted_domains = limit_link_api_lookups(domains)
    reference_dt, reference_detail = get_email_reference_datetime(email)

    domain_details: List[Dict[str, Any]] = []
    valid_ages: List[int] = []
    invalid_domains = 0
    for domain in consulted_domains:
        age = resolve_domain_age(
            domain,
            force=force,
            reference_dt=reference_dt,
            reference_detail=reference_detail,
            domain_source="link_domain",
        )
        age_days = age.get("age_days")
        detail = age.get("detail") or {}
        if isinstance(age_days, int) and not detail.get("insufficient_data"):
            valid_ages.append(age_days)
        elif detail.get("insufficient_data"):
            invalid_domains += 1
        domain_details.append(
            {
                "domain": domain,
                "age_days": age_days if isinstance(age_days, int) else None,
                "detail": detail,
            }
        )

    if valid_ages:
        value = min(valid_ages)
        insufficient = False
    else:
        value = None
        insufficient = True

    entry["checked"] = True
    entry["timestamp"] = _now_iso()
    entry["value"] = int(value) if value is not None else None
    entry["detail"] = {
        "aggregation": "min",
        "reference": reference_detail,
        "domains": domain_details,
        "total_unique_hosts": len(domains),
        "consulted_hosts": len(consulted_domains),
        "valid_domains": len(valid_ages),
        "invalid_domains": invalid_domains,
        "insufficient_data": insufficient,
        "fallback_value_applied": False,
    }
    return True


__all__ = ["enrich_link_domain_age_in_data"]

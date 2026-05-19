from __future__ import annotations

"""
Evalua reputacion de dominios enlazados reutilizando la logica comun de reputacion y agregando el peor caso.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List

from enrichment.link_domain_utils import (
    link_api_skip_context,
    limit_link_api_lookups,
)
from utils.link_url_utils import (
    extract_link_hosts,
    unique_link_hosts,
)
from enrichment.routing_data_helper import _domain_rep

DEFAULT_SCORE_RISK = 1


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ensure_enrichment(email: Dict[str, Any]) -> None:
    email.setdefault("enrichment", {})
    email["enrichment"].setdefault(
        "link_domain_reputation",
        {
            "checked": False,
            "timestamp": None,
            "value": None,
            "detail": None,
        },
    )


def enrich_link_domain_reputation_in_data(
    email: Dict[str, Any],
    force: bool = False,
    primary_only: bool = False,
) -> bool:
    _ensure_enrichment(email)
    entry = email["enrichment"]["link_domain_reputation"]

    skip_context = link_api_skip_context(email)
    if skip_context["should_skip"]:
        entry["checked"] = True
        entry["timestamp"] = _now_iso()
        entry["value"] = None
        entry["detail"] = {
            "aggregation": "max",
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

    domain_details: List[Dict[str, Any]] = []
    scores: List[float] = []
    invalid_domains = 0
    for domain in consulted_domains:
        rep = _domain_rep(domain, force=force)
        score = rep.get("score")
        detail = rep.get("detail") if isinstance(rep.get("detail"), dict) else {}
        insufficient = bool(detail.get("insufficient_data") is True)
        if isinstance(score, (int, float)) and not insufficient:
            scores.append(float(score))
        elif insufficient:
            invalid_domains += 1
        domain_details.append(
            {
                "domain": domain,
                "score": rep.get("score"),
                "sources": rep.get("sources"),
                "detail": rep.get("detail"),
            }
        )

    insufficient = False
    value = max(scores) if scores else None
    if value is None:
        insufficient = True

    entry["checked"] = True
    entry["timestamp"] = _now_iso()
    entry["value"] = int(value) if value is not None else None
    entry["detail"] = {
        "aggregation": "max",
        "domains": domain_details,
        "total_unique_hosts": len(domains),
        "consulted_hosts": len(consulted_domains),
        "valid_domains": len(scores),
        "invalid_domains": invalid_domains,
        "insufficient_data": insufficient,
        "fallback_value_applied": False,
    }
    return True


__all__ = ["enrich_link_domain_reputation_in_data"]

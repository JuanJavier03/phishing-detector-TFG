from __future__ import annotations

"""
Define politicas de analisis para subcriterios basados en enlaces: umbral para
saltar APIs externas, limite de consultas y resolucion del dominio modal. Las
operaciones puras de parsing de URLs viven en utils.link_url_utils.
"""

from typing import Any, Dict, List

from enrichment.vector_schema import LINK_COUNT_ZERO_SCORE_THRESHOLD
from utils.link_url_utils import (
    _registrable_domain,
    body_urls,
    extract_clickable_links,
    extract_link_hosts,
    primary_link_url,
    unique_link_domains,
    unique_link_hosts,
)
from utils.origin_resolution import resolve_sender_domain


LINK_API_SKIP_THRESHOLD = int(LINK_COUNT_ZERO_SCORE_THRESHOLD)
MAX_LINK_API_LOOKUPS_PER_EMAIL = LINK_API_SKIP_THRESHOLD - 1
LINK_API_SKIP_REASON = "too_many_links_for_api_analysis"


def limit_link_api_lookups(hosts: List[str]) -> List[str]:
    max_lookups = MAX_LINK_API_LOOKUPS_PER_EMAIL
    if isinstance(max_lookups, int) and max_lookups > 0:
        return hosts[:max_lookups]
    return list(hosts)


def link_api_skip_context(email: Dict[str, Any]) -> Dict[str, Any]:
    total_links = len(extract_clickable_links(email, primary_only=False))
    should_skip = total_links >= LINK_API_SKIP_THRESHOLD
    return {
        "total_links": total_links,
        "threshold": LINK_API_SKIP_THRESHOLD,
        "should_skip": should_skip,
        "reason_code": LINK_API_SKIP_REASON if should_skip else None,
    }


def extract_modal_domain(email: Dict[str, Any]) -> Dict[str, Any]:
    headers = email.get("headers") or {}
    headers = headers if isinstance(headers, dict) else {}
    resolution = resolve_sender_domain(headers, reliable_only=True)
    return {
        "domain": resolution.get("registrable_domain"),
        "host": resolution.get("host"),
        "subdomain": resolution.get("subdomain"),
        "suffix": resolution.get("suffix"),
        "raw": resolution.get("raw_evidence"),
        "source": resolution.get("source"),
        "trusted": resolution.get("trusted"),
        "reason": resolution.get("reason"),
        "candidates": resolution.get("candidates"),
    }


__all__ = [
    "extract_clickable_links",
    "extract_link_hosts",
    "unique_link_domains",
    "unique_link_hosts",
    "MAX_LINK_API_LOOKUPS_PER_EMAIL",
    "LINK_API_SKIP_THRESHOLD",
    "LINK_API_SKIP_REASON",
    "limit_link_api_lookups",
    "link_api_skip_context",
    "extract_modal_domain",
    "_registrable_domain",
    "primary_link_url",
    "body_urls",
]

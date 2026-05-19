from __future__ import annotations

"""
Extrae enlaces clicables del cuerpo y guarda el recuento deduplicado que actua como contexto para subcriterios de enlaces.
"""

from datetime import datetime, timezone
from typing import Any, Dict

from enrichment.link_domain_utils import link_api_skip_context
from utils.link_url_utils import extract_clickable_links


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ensure_enrichment(email: Dict[str, Any]) -> None:
    email.setdefault("enrichment", {})
    email["enrichment"].setdefault(
        "link_count",
        {
            "checked": False,
            "timestamp": None,
            "value": None,
            "detail": None,
        },
    )


def enrich_link_count_in_data(
    email: Dict[str, Any],
    force: bool = False,
    primary_only: bool = False,
) -> bool:
    _ensure_enrichment(email)
    entry = email["enrichment"]["link_count"]

    if entry.get("checked") and entry.get("value") is not None and not force:
        return False

    links = extract_clickable_links(email, primary_only=primary_only)
    skip_context = link_api_skip_context(email)
    link_count = int(len(links))

    entry["checked"] = True
    entry["timestamp"] = _now_iso()
    entry["value"] = link_count
    entry["detail"] = {
        "aggregation": "normalized_unique_clickable_links",
        "links": links,
        "api_analysis_skipped": bool(skip_context["should_skip"]),
        "api_analysis_skip_reason": skip_context["reason_code"],
        "api_analysis_skip_threshold": int(skip_context["threshold"]),
        "insufficient_data": False,
        "fallback_value_applied": False,
    }
    return True


__all__ = ["enrich_link_count_in_data"]

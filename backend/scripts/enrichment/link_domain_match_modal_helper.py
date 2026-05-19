from __future__ import annotations

"""
Compara el dominio base real de enlaces con el dominio modal o remitente para detectar discrepancias.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List

from enrichment.link_domain_utils import extract_modal_domain
from utils.domain_utils import base_domain
from utils.link_url_utils import extract_link_hosts, unique_link_domains


UNRELIABLE_SENDER_DOMAIN_REASON = "sender_domain_not_reliably_available_dmarc_not_pass"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ensure_enrichment(email: Dict[str, Any]) -> None:
    email.setdefault("enrichment", {})
    email["enrichment"].setdefault(
        "link_domain_match_modal",
        {
            "checked": False,
            "timestamp": None,
            "value": None,
            "detail": None,
        },
    )


def enrich_link_domain_match_modal_in_data(
    email: Dict[str, Any],
    force: bool = False,
    primary_only: bool = False,
) -> bool:
    _ensure_enrichment(email)
    entry = email["enrichment"]["link_domain_match_modal"]

    if entry.get("checked") and not force:
        return False

    modal = extract_modal_domain(email)
    modal_domain = base_domain(modal.get("domain"))

    if not isinstance(modal_domain, str) or not modal_domain:
        entry["checked"] = True
        entry["timestamp"] = _now_iso()
        entry["value"] = None
        entry["detail"] = {
            "modal_domain": None,
            "links": [],
            "mismatch_any": False,
            "insufficient_data": True,
            "fallback_value_applied": False,
            "error_reason": UNRELIABLE_SENDER_DOMAIN_REASON,
            "skipped_due_unreliable_sender_domain": True,
            "modal_resolution": modal,
        }
        return True

    link_entries = extract_link_hosts(email, primary_only=primary_only)
    link_domains = unique_link_domains(link_entries)

    comparisons: List[Dict[str, Any]] = []
    mismatch_any = False
    comparable = False

    for domain in link_domains:
        link_base_domain = base_domain(domain)
        match = None
        if modal_domain:
            match = link_base_domain == modal_domain
            comparable = True
            if not match:
                mismatch_any = True
        comparisons.append(
            {
                "domain": domain,
                "base_domain": link_base_domain,
                "match_modal": match,
            }
        )

    insufficient = not (modal_domain and link_domains and comparable)
    value = None if insufficient else (1 if mismatch_any else 0)

    entry["checked"] = True
    entry["timestamp"] = _now_iso()
    entry["value"] = int(value) if value is not None else None
    entry["detail"] = {
        "modal_domain": modal_domain,
        "modal_base_domain": modal_domain,
        "links": comparisons,
        "mismatch_any": mismatch_any,
        "insufficient_data": insufficient,
        "fallback_value_applied": False,
        "reason_code": "no_clickable_links_found" if not link_domains else None,
    }
    return True


__all__ = ["enrich_link_domain_match_modal_in_data"]

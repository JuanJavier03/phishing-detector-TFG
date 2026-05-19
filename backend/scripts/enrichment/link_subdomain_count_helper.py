from __future__ import annotations

"""
Cuenta la profundidad maxima de subdominios en enlaces clicables y almacena la evidencia asociada.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List

from utils.link_url_utils import extract_link_hosts
from utils.subdomain_utils import count_host_labels_without_suffix, normalize_subdomain


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ensure_enrichment(email: Dict[str, Any]) -> None:
    email.setdefault("enrichment", {})
    email["enrichment"].setdefault(
        "link_subdomain_count",
        {
            "checked": False,
            "timestamp": None,
            "value": None,
            "detail": None,
        },
    )


def enrich_link_subdomain_count_in_data(
    email: Dict[str, Any],
    force: bool = False,
    primary_only: bool = False,
) -> bool:
    _ensure_enrichment(email)
    entry = email["enrichment"]["link_subdomain_count"]

    if entry.get("checked") and not force:
        return False

    link_entries = extract_link_hosts(email, primary_only=primary_only)
    details: List[Dict[str, Any]] = []
    counts: List[int] = []

    for item in link_entries:
        sub = item.get("subdomain")
        sub_raw = sub if isinstance(sub, str) else None
        domain_raw = item.get("registrable_domain") if isinstance(item.get("registrable_domain"), str) else None
        registrable_label = domain_raw.split(".", 1)[0] if domain_raw else None
        count = count_host_labels_without_suffix(sub_raw, registrable_label)
        counts.append(count)
        details.append(
            {
                "url": item.get("url"),
                "host": item.get("host"),
                "domain": item.get("registrable_domain"),
                "subdomain": sub_raw,
                "subdomain_normalized": normalize_subdomain(sub_raw),
                "subdomain_count": count,
            }
        )

    value = max(counts) if counts else None
    insufficient = not bool(link_entries)

    entry["checked"] = True
    entry["timestamp"] = _now_iso()
    entry["value"] = int(value) if value is not None else None
    entry["detail"] = {
        "aggregation": "max",
        "hosts": details,
        "insufficient_data": insufficient,
        "fallback_value_applied": False,
    }
    return True


__all__ = ["enrich_link_subdomain_count_in_data"]

from __future__ import annotations

"""
Cuenta etiquetas numericas en subdominios de enlaces clicables y conserva el peor dominio observado.
"""

import re
from datetime import datetime, timezone
from typing import Any, Dict, List

from utils.link_url_utils import extract_link_hosts
from utils.subdomain_utils import normalize_subdomain, subdomain_labels


NUMERIC_LABEL_RE = re.compile(r"^[0-9]+$")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ensure_enrichment(email: Dict[str, Any]) -> None:
    email.setdefault("enrichment", {})
    email["enrichment"].setdefault(
        "link_numeric_subdomain",
        {
            "checked": False,
            "timestamp": None,
            "value": None,
            "detail": None,
        },
    )


def enrich_link_numeric_subdomain_in_data(
    email: Dict[str, Any],
    force: bool = False,
    primary_only: bool = False,
) -> bool:
    _ensure_enrichment(email)
    entry = email["enrichment"]["link_numeric_subdomain"]

    if entry.get("checked") and not force:
        return False

    link_entries = extract_link_hosts(email, primary_only=primary_only)
    details: List[Dict[str, Any]] = []
    max_numeric_labels = 0

    for item in link_entries:
        sub_raw = item.get("subdomain") if isinstance(item.get("subdomain"), str) else None
        labels = subdomain_labels(sub_raw)
        numeric_labels = [lbl for lbl in labels if NUMERIC_LABEL_RE.fullmatch(lbl)]
        max_numeric_labels = max(max_numeric_labels, len(numeric_labels))
        details.append(
            {
                "url": item.get("url"),
                "host": item.get("host"),
                "domain": item.get("registrable_domain"),
                "subdomain": sub_raw,
                "subdomain_normalized": normalize_subdomain(sub_raw),
                "numeric_labels": numeric_labels,
            }
        )

    insufficient = not bool(link_entries)
    value = int(max_numeric_labels) if not insufficient else None

    entry["checked"] = True
    entry["timestamp"] = _now_iso()
    entry["value"] = value
    entry["detail"] = {
        "aggregation": "max",
        "hosts": details,
        "insufficient_data": insufficient,
        "fallback_value_applied": False,
    }
    return True


__all__ = ["enrich_link_numeric_subdomain_in_data"]

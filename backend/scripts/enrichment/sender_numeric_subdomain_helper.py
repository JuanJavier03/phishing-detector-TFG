from __future__ import annotations

"""
Cuenta etiquetas numericas en el subdominio del remitente cuando el origen se puede resolver de forma fiable.
"""

import re
from datetime import datetime, timezone
from typing import Any, Dict

from utils.origin_resolution import resolve_sender_host
from utils.subdomain_utils import normalize_subdomain, subdomain_labels


NUMERIC_LABEL_RE = re.compile(r"^[0-9]+$")
UNRELIABLE_SENDER_DOMAIN_REASON = "sender_domain_not_reliably_available_dmarc_not_pass"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ensure_enrichment(email: Dict[str, Any]) -> None:
    email.setdefault("enrichment", {})
    email["enrichment"].setdefault(
        "sender_numeric_subdomain",
        {
            "checked": False,
            "timestamp": None,
            "domain": None,
            "value": None,
            "detail": None,
        },
    )


def enrich_sender_numeric_subdomain_in_data(email: Dict[str, Any], force: bool = False) -> bool:
    _ensure_enrichment(email)
    entry = email["enrichment"]["sender_numeric_subdomain"]

    if entry.get("checked") and not force:
        return False

    headers = email.get("headers") or {}
    resolution = resolve_sender_host(headers if isinstance(headers, dict) else {}, reliable_only=True)

    host = resolution.get("host") if isinstance(resolution.get("host"), str) else None
    registrable_domain = resolution.get("registrable_domain") if isinstance(resolution.get("registrable_domain"), str) else None
    subdomain = resolution.get("subdomain") if isinstance(resolution.get("subdomain"), str) else None
    domain_part = resolution.get("domain_part") if isinstance(resolution.get("domain_part"), str) else None
    suffix = resolution.get("suffix") if isinstance(resolution.get("suffix"), str) else None

    if not registrable_domain:
        entry["checked"] = True
        entry["timestamp"] = _now_iso()
        entry["domain"] = None
        entry["value"] = None
        entry["detail"] = {
            "source_header": resolution.get("source"),
            "raw_header": resolution.get("raw_evidence"),
            "domain_candidates": resolution.get("candidates"),
            "host_candidates": resolution.get("host_candidates"),
            "full_host": host,
            "subdomain": None,
            "subdomain_normalized": None,
            "domain_part": None,
            "suffix": None,
            "numeric_labels": [],
            "insufficient_data": True,
            "fallback_value_applied": False,
            "error_reason": UNRELIABLE_SENDER_DOMAIN_REASON,
            "skipped_due_unreliable_sender_domain": True,
        }
        return True

    subdomain_normalized = normalize_subdomain(subdomain)
    labels = subdomain_labels(subdomain)
    numeric_labels = [lbl for lbl in labels if NUMERIC_LABEL_RE.fullmatch(lbl)]

    entry["checked"] = True
    entry["timestamp"] = _now_iso()
    entry["domain"] = registrable_domain
    entry["value"] = int(len(numeric_labels))
    entry["detail"] = {
        "source_header": resolution.get("source"),
        "raw_header": resolution.get("raw_evidence"),
        "domain_candidates": resolution.get("candidates"),
        "host_candidates": resolution.get("host_candidates"),
        "full_host": host,
        "subdomain": subdomain,
        "subdomain_normalized": subdomain_normalized,
        "domain_part": domain_part,
        "suffix": suffix,
        "numeric_labels": numeric_labels,
        "insufficient_data": False,
        "fallback_value_applied": False,
    }
    return True


__all__ = ["enrich_sender_numeric_subdomain_in_data"]

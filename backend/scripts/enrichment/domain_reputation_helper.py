from __future__ import annotations

"""
Consulta reputacion del dominio remitente y guarda el peor indicador disponible, manejando errores y datos insuficientes.
"""

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from dotenv import load_dotenv

from enrichment.neutrino_client import lookup_host_reputation
from utils.origin_resolution import resolve_sender_domain


load_dotenv()

DEFAULT_SCORE_RISK = 1
SAFE_SCORE = 0
UNRELIABLE_SENDER_DOMAIN_REASON = "sender_domain_not_reliably_available_dmarc_not_pass"
NEUTRINO_HOST_REPUTATION_SOURCE = "neutrino.host_reputation"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ensure_enrichment(email: Dict[str, Any]) -> None:
    email.setdefault("enrichment", {})
    email["enrichment"].setdefault(
        "domain_reputation",
        {
            "checked": False,
            "timestamp": None,
            "domain": None,
            "sources": [],
            "score": None,
            "detail": None,
        },
    )


def _allow_http_apis() -> bool:
    raw = os.getenv("DOMAINREP_ALLOW_HTTP")
    if raw is None:
        return True
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def _query_neutrino(domain: str, force: bool = False) -> Tuple[Optional[int], Dict[str, Any]]:
    detail = lookup_host_reputation(domain, force=force)
    if detail.get("error"):
        return None, detail
    is_listed = detail.get("is_listed")
    if not isinstance(is_listed, bool):
        detail["error"] = "neutrino_missing_is_listed"
        return None, detail
    return (1 if is_listed else 0), detail


def _failure_detail(
    *,
    http_enabled: bool,
    domain_source: str,
    domain_candidates: Dict[str, Optional[str]],
    api_detail: Dict[str, Any],
    error_reason: str,
) -> Dict[str, Any]:
    return {
        "method": NEUTRINO_HOST_REPUTATION_SOURCE,
        "http_apis_enabled": http_enabled,
        "insufficient_data": True,
        "domain_source": domain_source,
        "domain_candidates": domain_candidates,
        "score_aspects": {},
        "api_detail": api_detail,
        "api_scores": {},
        "score": DEFAULT_SCORE_RISK,
        "fallback_value_applied": True,
        "error_reason": error_reason,
    }


def enrich_domain_reputation_in_data(
    email: Dict[str, Any],
    force: bool = False,
    allow_http: Optional[bool] = None,
) -> bool:
    _ensure_enrichment(email)
    entry = email["enrichment"]["domain_reputation"]

    headers = email.get("headers") or {}
    resolution = resolve_sender_domain(headers if isinstance(headers, dict) else {}, reliable_only=True)
    domain = resolution.get("host")
    domain_source = resolution.get("source") if isinstance(resolution.get("source"), str) else "none"
    domain_candidates = resolution.get("host_candidates") if isinstance(resolution.get("host_candidates"), dict) else {}
    http_enabled = _allow_http_apis() if allow_http is None else allow_http

    if not isinstance(domain, str) or not domain:
        detail = {
            "method": NEUTRINO_HOST_REPUTATION_SOURCE,
            "http_apis_enabled": http_enabled,
            "insufficient_data": True,
            "domain_source": domain_source,
            "domain_candidates": domain_candidates,
            "score_aspects": {},
            "api_detail": {},
            "api_scores": {},
            "score": None,
            "fallback_value_applied": False,
            "error_reason": UNRELIABLE_SENDER_DOMAIN_REASON,
            "skipped_due_unreliable_sender_domain": True,
        }
        entry.update(
            {
                "checked": True,
                "timestamp": _now_iso(),
                "domain": None,
                "sources": [],
                "score": None,
                "detail": detail,
            }
        )
        return True

    if not http_enabled:
        detail = _failure_detail(
            http_enabled=http_enabled,
            domain_source=domain_source,
            domain_candidates=domain_candidates,
            api_detail={"error": "http_apis_disabled"},
            error_reason="http_apis_disabled",
        )
        entry.update(
            {
                "checked": True,
                "timestamp": _now_iso(),
                "domain": domain,
                "sources": [],
                "score": DEFAULT_SCORE_RISK,
                "detail": detail,
            }
        )
        return True

    score, api_detail = _query_neutrino(domain, force=force)
    if score is None:
        detail = _failure_detail(
            http_enabled=http_enabled,
            domain_source=domain_source,
            domain_candidates=domain_candidates,
            api_detail=api_detail,
            error_reason=str(api_detail.get("error") or "neutrino_lookup_failed"),
        )
        entry.update(
            {
                "checked": True,
                "timestamp": _now_iso(),
                "domain": domain,
                "sources": [],
                "score": DEFAULT_SCORE_RISK,
                "detail": detail,
            }
        )
        return True

    detail = {
        "method": NEUTRINO_HOST_REPUTATION_SOURCE,
        "http_apis_enabled": http_enabled,
        "insufficient_data": False,
        "domain_source": domain_source,
        "domain_candidates": domain_candidates,
        "score_aspects": {NEUTRINO_HOST_REPUTATION_SOURCE: {"score": score, "weight": 1.0}},
        "api_detail": api_detail,
        "api_scores": {
            NEUTRINO_HOST_REPUTATION_SOURCE: {
                "score": score,
                "is_listed": api_detail.get("is_listed"),
                "list_count": api_detail.get("list_count"),
            }
        },
        "score": score,
        "fallback_value_applied": False,
        "error_reason": None,
    }

    entry.update(
        {
            "checked": True,
            "timestamp": _now_iso(),
            "domain": domain,
            "sources": [NEUTRINO_HOST_REPUTATION_SOURCE],
            "score": SAFE_SCORE if score == 0 else DEFAULT_SCORE_RISK,
            "detail": detail,
        }
    )
    return True


__all__ = [
    "DEFAULT_SCORE_RISK",
    "SAFE_SCORE",
    "NEUTRINO_HOST_REPUTATION_SOURCE",
    "_query_neutrino",
    "enrich_domain_reputation_in_data",
]

from __future__ import annotations

"""
Resuelve la IP de origen y consulta su presencia en listas de reputacion, dejando evidencia de resolucion y API.
"""

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from dotenv import load_dotenv

from enrichment.neutrino_client import lookup_ip_blocklist
from utils.origin_resolution import resolve_sender_ip_from_headers
from utils.ip_utils import resolve_ip_from_email


load_dotenv()

DEFAULT_SCORE_RISK = 1
SAFE_SCORE = 0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ensure_enrichment(email: Dict[str, Any]) -> None:
    email.setdefault("enrichment", {})
    email["enrichment"].setdefault(
        "ip_reputation",
        {
            "checked": False,
            "timestamp": None,
            "ip": None,
            "sources": [],
            "score": None,
            "detail": None,
        },
    )


def _allow_http_apis() -> bool:
    raw = os.getenv("IPREP_ALLOW_HTTP")
    if raw is None:
        return True
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def _ip_version(ip: Optional[str]) -> Optional[str]:
    if not isinstance(ip, str) or not ip:
        return None
    return "v6" if ":" in ip else "v4"


def _query_neutrino(ip: str, force: bool = False) -> Tuple[Optional[int], Dict[str, Any]]:
    detail = lookup_ip_blocklist(ip, force=force)
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
    origin_source: str,
    resolution_detail: Optional[Dict[str, Any]],
    api_detail: Dict[str, Any],
    error_reason: str,
    ip: Optional[str],
) -> Dict[str, Any]:
    return {
        "method": "neutrino.ip_blocklist",
        "http_apis_enabled": http_enabled,
        "insufficient_data": True,
        "origin_source": origin_source,
        "ip_version": _ip_version(ip),
        "resolution_detail": resolution_detail,
        "score_aspects": {},
        "api_detail": api_detail,
        "api_scores": {},
        "score": DEFAULT_SCORE_RISK,
        "fallback_value_applied": True,
        "error_reason": error_reason,
    }


def enrich_ip_reputation_in_data(
    email: Dict[str, Any],
    force: bool = False,
    allow_http: Optional[bool] = None,
) -> bool:
    _ensure_enrichment(email)
    entry = email["enrichment"]["ip_reputation"]
    if entry.get("checked") and not force:
        return False

    headers = email.get("headers") or {}
    ip, origin_source = resolve_sender_ip_from_headers(headers if isinstance(headers, dict) else {})
    resolution_detail = None
    if not ip:
        resolved_ip, resolved_source, detail = resolve_ip_from_email(email)
        resolution_detail = detail
        if resolved_ip:
            ip = resolved_ip
            origin_source = resolved_source

    http_enabled = _allow_http_apis() if allow_http is None else allow_http

    if not isinstance(ip, str) or not ip:
        detail = _failure_detail(
            http_enabled=http_enabled,
            origin_source="none",
            resolution_detail=resolution_detail,
            api_detail={},
            error_reason="ip_not_found",
            ip=None,
        )
        entry.update(
            {
                "checked": True,
                "timestamp": _now_iso(),
                "ip": None,
                "sources": [],
                "score": DEFAULT_SCORE_RISK,
                "detail": detail,
            }
        )
        return True

    if not http_enabled:
        detail = _failure_detail(
            http_enabled=http_enabled,
            origin_source=origin_source,
            resolution_detail=resolution_detail,
            api_detail={"error": "http_apis_disabled"},
            error_reason="http_apis_disabled",
            ip=ip,
        )
        entry.update(
            {
                "checked": True,
                "timestamp": _now_iso(),
                "ip": ip,
                "sources": [],
                "score": DEFAULT_SCORE_RISK,
                "detail": detail,
            }
        )
        return True

    score, api_detail = _query_neutrino(ip, force=force)
    if score is None:
        detail = _failure_detail(
            http_enabled=http_enabled,
            origin_source=origin_source,
            resolution_detail=resolution_detail,
            api_detail=api_detail,
            error_reason=str(api_detail.get("error") or "neutrino_lookup_failed"),
            ip=ip,
        )
        entry.update(
            {
                "checked": True,
                "timestamp": _now_iso(),
                "ip": ip,
                "sources": [],
                "score": DEFAULT_SCORE_RISK,
                "detail": detail,
            }
        )
        return True

    detail = {
        "method": "neutrino.ip_blocklist",
        "http_apis_enabled": http_enabled,
        "insufficient_data": False,
        "origin_source": origin_source,
        "ip_version": _ip_version(ip),
        "resolution_detail": resolution_detail,
        "score_aspects": {"neutrino.ip_blocklist": {"score": score, "weight": 1.0}},
        "api_detail": api_detail,
        "api_scores": {
            "neutrino.ip_blocklist": {
                "score": score,
                "is_listed": api_detail.get("is_listed"),
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
            "ip": ip,
            "sources": ["neutrino.ip_blocklist"],
            "score": SAFE_SCORE if score == 0 else DEFAULT_SCORE_RISK,
            "detail": detail,
        }
    )
    return True


__all__ = ["DEFAULT_SCORE_RISK", "SAFE_SCORE", "_query_neutrino", "enrich_ip_reputation_in_data"]

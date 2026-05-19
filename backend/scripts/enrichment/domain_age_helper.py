from __future__ import annotations

"""
Resuelve la antiguedad del dominio remitente con Neutrino y la transforma en un resultado normalizado para el vector MCDM.
"""

import os
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, Optional, Tuple

from dotenv import load_dotenv

from enrichment.neutrino_client import lookup_domain
from utils.origin_resolution import iter_header_values, resolve_sender_domain


load_dotenv()

DEFAULT_AGE_DAYS_ON_FAILURE = 1
UNRELIABLE_SENDER_DOMAIN_REASON = "sender_domain_not_reliably_available_dmarc_not_pass"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ensure_enrichment(email: Dict[str, Any]) -> None:
    email.setdefault("enrichment", {})
    email["enrichment"].setdefault(
        "domain_age",
        {
            "checked": False,
            "timestamp": None,
            "domain": None,
            "age_days": None,
            "detail": None,
        },
    )


def _allow_http_apis() -> bool:
    raw = os.getenv("DOMAINAGE_ALLOW_HTTP")
    if raw is None:
        return True
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip().replace(" UTC", "+00:00")
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        parsed = None
    if parsed is not None:
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)

    for fmt in (
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f%z",
    ):
        try:
            parsed = datetime.strptime(raw, fmt)
            return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
        except Exception:
            continue
    return None


def _compute_age_days(registered_dt: datetime, reference_dt: datetime) -> int:
    return max(0, int((reference_dt - registered_dt).total_seconds() // 86400))


def _age_range_bucket(age_days: int) -> str:
    if age_days <= 3:
        return "0-3d"
    if age_days <= 14:
        return "4-14d"
    if age_days <= 30:
        return "15-30d"
    if age_days <= 90:
        return "31-90d"
    if age_days <= 180:
        return "91-180d"
    if age_days <= 365:
        return "181-365d"
    if age_days <= 730:
        return "1-2y"
    if age_days <= 1825:
        return "2-5y"
    return ">5y"


def _age_range_risk_score(age_days: int) -> float:
    if age_days <= 3:
        return 1.0
    if age_days <= 14:
        return 0.95
    if age_days <= 30:
        return 0.90
    if age_days <= 90:
        return 0.75
    if age_days <= 180:
        return 0.60
    if age_days <= 365:
        return 0.40
    if age_days <= 730:
        return 0.25
    if age_days <= 1825:
        return 0.10
    return 0.0


def _received_timestamp_tail(line: str) -> Optional[str]:
    if not line or ";" not in line:
        return None
    tail = line.rsplit(";", 1)[-1].strip()
    return tail or None


def _parse_received_datetime(line: str) -> Tuple[Optional[datetime], Optional[str], Optional[str]]:
    tail = _received_timestamp_tail(line)
    if not tail:
        return None, None, "no_semicolon_or_tail"
    try:
        parsed = parsedate_to_datetime(tail)
    except Exception as exc:
        return None, tail, f"parse_error:{exc}"
    if parsed is None:
        return None, tail, "parse_failed"
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed, tail, None


def get_email_reference_datetime(email: Dict[str, Any]) -> Tuple[Optional[datetime], Dict[str, Any]]:
    headers = email.get("headers") or {}
    headers = headers if isinstance(headers, dict) else {}
    received_values = list(iter_header_values(headers.get("received")))

    for reverse_index, line in enumerate(reversed(received_values)):
        index = len(received_values) - 1 - reverse_index
        parsed, tail, error = _parse_received_datetime(line)
        if parsed is None:
            continue
        return parsed, {
            "reference_source": "received_oldest",
            "received_index": index,
            "received_count": len(received_values),
            "received_tail": tail,
            "reference_datetime": parsed.isoformat(),
            "parse_error": error,
        }

    return None, {
        "reference_source": "received_oldest",
        "received_index": None,
        "received_count": len(received_values),
        "received_tail": None,
        "reference_datetime": None,
        "parse_error": "no_parsable_received_timestamp",
    }


def _failure_detail(
    *,
    domain: Optional[str],
    error_reason: str,
    reference_detail: Optional[Dict[str, Any]],
    domain_source: Optional[str],
    domain_candidates: Optional[Dict[str, Optional[str]]],
) -> Dict[str, Any]:
    age_days = DEFAULT_AGE_DAYS_ON_FAILURE
    detail: Dict[str, Any] = {
        "method": "neutrino.domain_lookup",
        "age_basis": "registered_date_vs_email_timestamp",
        "created_raw": None,
        "last_update_raw": None,
        "created_age_days": age_days,
        "last_update_age_days": None,
        "last_update_considered": False,
        "last_update_ignored_reason": "not_used",
        "effective_age_days": age_days,
        "effective_source": "fallback_default",
        "piecewise_bucket": _age_range_bucket(age_days),
        "piecewise_risk_score": _age_range_risk_score(age_days),
        "error_reason": error_reason,
        "http_apis_enabled": _allow_http_apis(),
        "insufficient_data": True,
        "fallback_value_applied": True,
        "domain_source": domain_source,
        "domain_candidates": domain_candidates,
        "reference": reference_detail,
        "api_detail": {
            "source": "neutrino.domain_lookup",
            "domain": domain,
        },
    }
    return detail


def resolve_domain_age(
    domain: Optional[str],
    *,
    force: bool = False,
    reference_dt: Optional[datetime] = None,
    reference_detail: Optional[Dict[str, Any]] = None,
    domain_source: Optional[str] = None,
    domain_candidates: Optional[Dict[str, Optional[str]]] = None,
) -> Dict[str, Any]:
    if not domain:
        detail = _failure_detail(
            domain=None,
            error_reason="domain_not_found",
            reference_detail=reference_detail,
            domain_source=domain_source,
            domain_candidates=domain_candidates,
        )
        return {"domain": None, "age_days": DEFAULT_AGE_DAYS_ON_FAILURE, "detail": detail}

    if reference_dt is None:
        detail = _failure_detail(
            domain=domain,
            error_reason="reference_datetime_not_found",
            reference_detail=reference_detail,
            domain_source=domain_source,
            domain_candidates=domain_candidates,
        )
        return {"domain": domain, "age_days": DEFAULT_AGE_DAYS_ON_FAILURE, "detail": detail}

    if not _allow_http_apis():
        detail = _failure_detail(
            domain=domain,
            error_reason="http_apis_disabled",
            reference_detail=reference_detail,
            domain_source=domain_source,
            domain_candidates=domain_candidates,
        )
        return {"domain": domain, "age_days": DEFAULT_AGE_DAYS_ON_FAILURE, "detail": detail}

    api_detail = lookup_domain(domain, force=force)
    registered_raw = api_detail.get("registered_date")
    registered_dt = _parse_datetime(registered_raw if isinstance(registered_raw, str) else None)
    error_reason = api_detail.get("error")

    if error_reason or not registered_dt:
        detail = _failure_detail(
            domain=domain,
            error_reason=str(error_reason or "registered_date_not_found"),
            reference_detail=reference_detail,
            domain_source=domain_source,
            domain_candidates=domain_candidates,
        )
        detail["api_detail"] = api_detail
        return {"domain": domain, "age_days": DEFAULT_AGE_DAYS_ON_FAILURE, "detail": detail}

    age_days = _compute_age_days(registered_dt, reference_dt)
    detail = {
        "method": "neutrino.domain_lookup",
        "age_basis": "registered_date_vs_email_timestamp",
        "created_raw": registered_raw,
        "last_update_raw": None,
        "created_age_days": age_days,
        "last_update_age_days": None,
        "last_update_considered": False,
        "last_update_ignored_reason": "not_used",
        "effective_age_days": age_days,
        "effective_source": "registered_date",
        "piecewise_bucket": _age_range_bucket(age_days),
        "piecewise_risk_score": _age_range_risk_score(age_days),
        "error_reason": None,
        "http_apis_enabled": True,
        "insufficient_data": False,
        "fallback_value_applied": False,
        "domain_source": domain_source,
        "domain_candidates": domain_candidates,
        "reference": reference_detail,
        "api_detail": api_detail,
    }
    return {"domain": domain, "age_days": age_days, "detail": detail}


def enrich_domain_age_in_data(email: Dict[str, Any], force: bool = False) -> bool:
    _ensure_enrichment(email)
    entry = email["enrichment"]["domain_age"]
    if entry.get("checked") and not force:
        return False

    headers = email.get("headers") or {}
    resolution = resolve_sender_domain(headers if isinstance(headers, dict) else {}, reliable_only=True)
    domain = resolution.get("host")
    reference_dt, reference_detail = get_email_reference_datetime(email)

    if not isinstance(domain, str) or not domain:
        entry["checked"] = True
        entry["timestamp"] = _now_iso()
        entry["domain"] = None
        entry["age_days"] = None
        entry["detail"] = {
            "method": "neutrino.domain_lookup",
            "age_basis": "registered_date_vs_email_timestamp",
            "created_raw": None,
            "last_update_raw": None,
            "created_age_days": None,
            "last_update_age_days": None,
            "last_update_considered": False,
            "last_update_ignored_reason": "not_used",
            "effective_age_days": None,
            "effective_source": None,
            "piecewise_bucket": None,
            "piecewise_risk_score": None,
            "error_reason": UNRELIABLE_SENDER_DOMAIN_REASON,
            "http_apis_enabled": _allow_http_apis(),
            "insufficient_data": True,
            "fallback_value_applied": False,
            "skipped_due_unreliable_sender_domain": True,
            "domain_source": resolution.get("source") if isinstance(resolution.get("source"), str) else None,
            "domain_candidates": resolution.get("host_candidates") if isinstance(resolution.get("host_candidates"), dict) else None,
            "reference": reference_detail,
            "api_detail": {},
        }
        return True

    resolved = resolve_domain_age(
        domain if isinstance(domain, str) else None,
        force=force,
        reference_dt=reference_dt,
        reference_detail=reference_detail,
        domain_source=resolution.get("source") if isinstance(resolution.get("source"), str) else None,
        domain_candidates=resolution.get("host_candidates") if isinstance(resolution.get("host_candidates"), dict) else None,
    )

    entry["checked"] = True
    entry["timestamp"] = _now_iso()
    entry["domain"] = resolved.get("domain")
    entry["age_days"] = resolved.get("age_days")
    entry["detail"] = resolved.get("detail")
    return True


__all__ = ["enrich_domain_age_in_data", "get_email_reference_datetime", "resolve_domain_age"]

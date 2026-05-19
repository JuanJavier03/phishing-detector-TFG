from __future__ import annotations

"""
Normaliza, almacena y recupera resultados de subcriterios manteniendo compatibilidad con estructuras antiguas.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from utils.enrichment_utils import normalize_criterion_key


STANDARD_SUBCRITERION_VERSION = 2
STANDARD_TOP_LEVEL_KEYS = {
    "schema_version",
    "criterion",
    "criterion_key",
    "family",
    "status",
    "value",
    "value_type",
    "updated_at",
    "detail",
}
STANDARD_DETAIL_META_KEYS = {
    "flags",
    "error",
    "errors",
    "api",
    "meta",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _criterion_family(criterion: str) -> Optional[str]:
    if not isinstance(criterion, str) or "." not in criterion:
        return None
    family = criterion.split(".", 1)[0].strip()
    return family or None


def _value_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _to_numeric_vector_value(value: Any) -> Optional[float | int]:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return value
    return None


def _as_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "si", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
    return None


def _as_int(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        try:
            return int(value)
        except Exception:
            return None
    return None


def _as_nonempty_str(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _dict_copy(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _first_nonempty_str(*values: Any) -> Optional[str]:
    for value in values:
        candidate = _as_nonempty_str(value)
        if candidate:
            return candidate
    return None


def _get_nested(mapping: Any, *keys: str) -> Any:
    current = mapping
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _collect_flag_values(raw: Dict[str, Any], detail: Dict[str, Any]) -> Dict[str, bool]:
    def _flag(*paths: tuple[str, ...]) -> bool:
        for path in paths:
            value = _get_nested({"raw": raw, "detail": detail}, *path)
            parsed = _as_bool(value)
            if parsed is not None:
                return parsed
        return False

    return {
        "insufficient_data": _flag(("detail", "insufficient_data"), ("detail", "meta", "insufficient_data")),
        "mcdm_excluded": _flag(("detail", "mcdm_excluded"),),
        "fallback_value_applied": _flag(("detail", "fallback_value_applied"),),
        "network_access_disabled": _flag(("detail", "network_access_disabled"),),
        "http_apis_enabled": _flag(("detail", "http_apis_enabled"),),
        "skipped_due_unreliable_sender_domain": _flag(("detail", "skipped_due_unreliable_sender_domain"),),
        "skipped_due_link_count_threshold": _flag(("detail", "skipped_due_link_count_threshold"),),
    }


def _infer_error_code(raw: Dict[str, Any], detail: Dict[str, Any]) -> Optional[str]:
    return _first_nonempty_str(
        detail.get("error"),
        detail.get("error_reason"),
        _get_nested(detail, "api_detail", "error"),
        raw.get("error"),
    )


def _infer_error_message(raw: Dict[str, Any], detail: Dict[str, Any], error_code: Optional[str]) -> Optional[str]:
    return _first_nonempty_str(
        detail.get("error_message"),
        _get_nested(detail, "api_detail", "error_message"),
        _get_nested(detail, "api_detail", "api_error_msg"),
        error_code,
    )


def _infer_api_payload(detail: Dict[str, Any]) -> Dict[str, Any]:
    api_detail = _dict_copy(detail.get("api_detail"))
    endpoint = _first_nonempty_str(
        detail.get("method"),
        api_detail.get("endpoint"),
    )
    provider = None
    if endpoint:
        provider = endpoint.split(".", 1)[0]
    provider = _first_nonempty_str(
        provider,
        api_detail.get("provider"),
        api_detail.get("source"),
    )
    http_status = _as_int(api_detail.get("http_status"))
    if http_status is None:
        http_status = _as_int(detail.get("http_status"))
    payload = {
        "provider": provider,
        "endpoint": endpoint,
        "http_status": http_status,
        "enabled": _as_bool(detail.get("http_apis_enabled")),
        "target": _first_nonempty_str(
            api_detail.get("domain"),
            api_detail.get("host"),
            api_detail.get("ip"),
        ),
        "detail": api_detail,
    }
    return payload


def _build_error_list(
    raw: Dict[str, Any],
    detail: Dict[str, Any],
    api: Dict[str, Any],
) -> tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    error_code = _infer_error_code(raw, detail)
    if not error_code:
        return None, []

    error_message = _infer_error_message(raw, detail, error_code)
    http_status = _as_int(api.get("http_status"))
    error_payload = {
        "code": error_code,
        "message": error_message,
        "provider": api.get("provider"),
        "endpoint": api.get("endpoint"),
        "http_status": http_status,
        "fatal": error_code.startswith("neutrino_"),
        "retryable": not error_code.startswith("neutrino_missing_credentials"),
        "source_path": "detail.api_detail.error" if _get_nested(detail, "api_detail", "error") else "detail.error",
    }
    return error_payload, [error_payload]


def _infer_status(
    raw: Dict[str, Any],
    flags: Dict[str, bool],
    primary_error: Optional[Dict[str, Any]],
) -> str:
    explicit = _as_nonempty_str(raw.get("status"))
    if explicit:
        return explicit
    if primary_error is not None:
        return "error"
    if flags.get("mcdm_excluded"):
        return "excluded"
    if flags.get("insufficient_data"):
        return "insufficient_data"
    return "completed"


def _build_standard_detail(raw: Dict[str, Any], detail: Dict[str, Any]) -> Dict[str, Any]:
    flags = _collect_flag_values(raw, detail)
    api = _infer_api_payload(detail)
    primary_error, errors = _build_error_list(raw, detail, api)

    meta: Dict[str, Any] = {}
    for key, value in detail.items():
        if key in STANDARD_DETAIL_META_KEYS:
            continue
        meta[key] = value

    detail["flags"] = flags
    detail["error"] = primary_error
    detail["errors"] = errors
    detail["api"] = api
    detail["meta"] = meta

    # Compatibilidad hacia atras: conservamos los flags legacy donde ya se estaban leyendo.
    detail["insufficient_data"] = flags["insufficient_data"]
    if flags["mcdm_excluded"] or "mcdm_excluded" in detail:
        detail["mcdm_excluded"] = flags["mcdm_excluded"]
    if flags["fallback_value_applied"] or "fallback_value_applied" in detail:
        detail["fallback_value_applied"] = flags["fallback_value_applied"]
    if flags["network_access_disabled"] or "network_access_disabled" in detail:
        detail["network_access_disabled"] = flags["network_access_disabled"]
    if flags["http_apis_enabled"] or "http_apis_enabled" in detail:
        detail["http_apis_enabled"] = flags["http_apis_enabled"]
    if flags["skipped_due_unreliable_sender_domain"] or "skipped_due_unreliable_sender_domain" in detail:
        detail["skipped_due_unreliable_sender_domain"] = flags["skipped_due_unreliable_sender_domain"]
    if flags["skipped_due_link_count_threshold"] or "skipped_due_link_count_threshold" in detail:
        detail["skipped_due_link_count_threshold"] = flags["skipped_due_link_count_threshold"]

    return detail


def _canonicalize_value_for_criterion(
    criterion_key: Optional[str],
    value: Optional[float | int],
) -> Optional[float | int]:
    if value is None:
        return None
    if criterion_key == "body_obfuscation_base64":
        return 1 if float(value) > 0 else 0
    return value


def extract_vector_value(result: Dict[str, Any]) -> Optional[float | int]:
    if not isinstance(result, dict):
        return None
    for key in (
        "vector_value",
        "value",
        "score",
        "age_days",
        "subdomain_count",
        "numeric_subdomain_count",
        "received_count",
        "delta_seconds",
        "keyword_count",
        "tag_count",
        "beacon_count",
        "suspicious_count",
    ):
        candidate = _to_numeric_vector_value(result.get(key))
        if candidate is not None:
            return candidate
    return None


def normalize_subcriterion_result(
    result: Dict[str, Any],
    criterion: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    if not isinstance(result, dict):
        return None

    raw = dict(result)
    resolved_criterion = criterion or raw.get("criterion")
    if not isinstance(resolved_criterion, str) or not resolved_criterion:
        return None

    criterion_key = normalize_criterion_key(resolved_criterion)
    family = _criterion_family(resolved_criterion)
    vector_value = extract_vector_value(raw)
    canonical_value = _canonicalize_value_for_criterion(criterion_key, vector_value)

    updated_at = raw.get("updated_at")
    if not isinstance(updated_at, str) or not updated_at:
        updated_at = raw.get("timestamp")
    detail: Dict[str, Any] = {}
    raw_detail = raw.get("detail")
    if isinstance(raw_detail, dict):
        detail.update(raw_detail)

    raw_value = raw.get("value")
    if raw_value != canonical_value and "raw_value" not in detail:
        detail["raw_value"] = raw_value

    for key, value in raw.items():
        if key in STANDARD_TOP_LEVEL_KEYS or key == "timestamp":
            continue
        if key == "detail" and isinstance(value, dict):
            continue
        detail[key] = value

    detail = _build_standard_detail(raw, detail)
    status = _infer_status(raw, detail["flags"], detail["error"])

    normalized = {
        "schema_version": STANDARD_SUBCRITERION_VERSION,
        "criterion": resolved_criterion,
        "criterion_key": criterion_key,
        "family": family,
        "status": status,
        "value": canonical_value,
        "value_type": _value_type(canonical_value),
        "updated_at": updated_at if isinstance(updated_at, str) and updated_at else _now_iso(),
        "detail": detail,
    }
    return normalized


def _ensure_enrichment(email: Dict[str, Any]) -> Dict[str, Any]:
    if "enrichment" not in email or not isinstance(email["enrichment"], dict):
        email["enrichment"] = {}
    return email["enrichment"]


def store_subcriterion_result(email: Dict[str, Any], result: Dict[str, Any]) -> bool:
\
\
\

    normalized = normalize_subcriterion_result(result)
    if normalized is None:
        return False
    result.clear()
    result.update(normalized)
    key = normalized["criterion_key"]

    enrichment = _ensure_enrichment(email)

    legacy = enrichment.get("subcriteria")
    if isinstance(legacy, dict):
        for legacy_key, legacy_val in legacy.items():
            if isinstance(legacy_key, str) and legacy_key:
                norm_key = normalize_criterion_key(legacy_key)
                if norm_key not in enrichment:
                    enrichment[norm_key] = legacy_val
    if "subcriteria" in enrichment:
        enrichment.pop("subcriteria", None)

    existing = enrichment.get(key)
    if isinstance(existing, dict):
        existing = normalize_subcriterion_result(existing, criterion=normalized["criterion"]) or existing
        if existing != enrichment.get(key):
            enrichment[key] = existing

    if existing == normalized:
        return False
    enrichment[key] = normalized
    return True


def get_subcriterion_result(email: Dict[str, Any], criterion: str) -> Optional[Dict[str, Any]]:
    if not isinstance(criterion, str) or not criterion:
        return None
    norm = normalize_criterion_key(criterion)
    enrichment = _ensure_enrichment(email)
    if not isinstance(enrichment, dict):
        return None
    existing = enrichment.get(norm)
    if isinstance(existing, dict):
        normalized = normalize_subcriterion_result(existing, criterion=criterion)
        if normalized is None:
            return None
        if normalized != existing:
            enrichment[norm] = normalized
        return normalized
    legacy = enrichment.get("subcriteria")
    if isinstance(legacy, dict):
        legacy_val = legacy.get(criterion)
        if not isinstance(legacy_val, dict):
            legacy_val = legacy.get(norm)
        if isinstance(legacy_val, dict):
            normalized = normalize_subcriterion_result(legacy_val, criterion=criterion)
            if normalized is None:
                return None
            enrichment[norm] = normalized
            return normalized
    return None


__all__ = [
    "store_subcriterion_result",
    "get_subcriterion_result",
    "normalize_subcriterion_result",
    "extract_vector_value",
]

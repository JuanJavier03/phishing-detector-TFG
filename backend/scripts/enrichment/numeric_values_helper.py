from __future__ import annotations

"""
Construye el vector numerico estable a partir de resultados de enriquecimiento y valida su alineacion con vector_schema.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from utils.enrichment_utils import normalize_criterion_key
from utils.subcriteria_utils import extract_vector_value
from enrichment.vector_schema import VECTOR_FIELD_ORDER


DEFAULTS = {
    "domain_rep": 1,
    "ip_rep": 1,
    "link_domain_rep": 1,
    "country_compare": 0.5,
}
UNRELIABLE_SENDER_DOMAIN_REASON = "sender_domain_not_reliably_available_dmarc_not_pass"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _as_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        try:
            return int(value)
        except Exception:
            return default
    return default


def _as_float(value: Any, default: float) -> float:
    if isinstance(value, bool):
        return float(default)
    if isinstance(value, (int, float)):
        return float(value)
    return float(default)


def _get_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _get_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _get_enrichment(email: Dict[str, Any]) -> Dict[str, Any]:
    enr = email.get("enrichment")
    return enr if isinstance(enr, dict) else {}


def _len_list(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def _bool01(value: Any) -> int:
    if value is True:
        return 1
    if value is False or value is None:
        return 0
    if isinstance(value, int):
        return 1 if value != 0 else 0
    if isinstance(value, float):
        return 1 if value != 0.0 else 0
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("1", "true", "yes", "y", "on"):
            return 1
        if v in ("0", "false", "no", "n", "off", ""):
            return 0
    return 0


def _get_enrichment_block(enrichment: Dict[str, Any], key: str) -> Dict[str, Any]:
    """
    Fetch an enrichment block by key, accounting for criterion key normalization.

    Example: "criterio1.spf" is stored as "spf".
    """
    if not isinstance(key, str) or not key:
        return {}
    norm = normalize_criterion_key(key)
    return _get_dict(enrichment.get(norm) or enrichment.get(key))


def _entry_numeric_value(entry: Dict[str, Any]) -> Optional[float | int]:
    if not isinstance(entry, dict):
        return None
    numeric = extract_vector_value(entry)
    if numeric is not None:
        return numeric
    return None


def _link_numeric_subdomain_count(enrichment: Dict[str, Any]) -> Optional[int]:
    entry = _get_dict(enrichment.get("link_numeric_subdomain"))
    value = _nullable_int_unless_insufficient(entry, "value")
    return value


def _link_captcha_count(enrichment: Dict[str, Any]) -> Optional[int]:
    # For MCDM we keep this as a binary "captcha present" signal (0/1),
    # aligned with the stored enrichment value.
    entry = _get_dict(enrichment.get("link_captcha"))
    if _detail(entry).get("insufficient_data") is True:
        return None
    raw_value = entry.get("value")
    if raw_value is None:
        return None
    return _bool01(raw_value)


def _detail(entry: Dict[str, Any]) -> Dict[str, Any]:
    detail = entry.get("detail")
    return detail if isinstance(detail, dict) else {}


def _sender_domain_skipped(entry: Dict[str, Any]) -> bool:
    detail = _detail(entry)
    return (
        detail.get("skipped_due_unreliable_sender_domain") is True
        or detail.get("error_reason") == UNRELIABLE_SENDER_DOMAIN_REASON
    )


def _mcdm_excluded(entry: Dict[str, Any]) -> bool:
    detail = _detail(entry)
    return detail.get("mcdm_excluded") is True


def _nullable_int_from_entry(entry: Dict[str, Any], *keys: str) -> Optional[int]:
    numeric_value = _entry_numeric_value(entry)
    if numeric_value is not None:
        return _as_int(numeric_value, default=0)
    for key in keys:
        raw_value = entry.get(key)
        if raw_value is not None:
            return _as_int(raw_value, default=0)
    return None


def _nullable_int_unless_insufficient(entry: Dict[str, Any], *keys: str) -> Optional[int]:
    if _detail(entry).get("insufficient_data") is True:
        return None
    return _nullable_int_from_entry(entry, *keys)


def _nullable_float_from_entry(entry: Dict[str, Any], *keys: str) -> Optional[float]:
    if _mcdm_excluded(entry):
        return None
    numeric_value = _entry_numeric_value(entry)
    if numeric_value is not None:
        return _as_float(numeric_value, default=0.0)
    for key in keys:
        raw_value = entry.get(key)
        if raw_value is not None:
            return _as_float(raw_value, default=0.0)
    return None


def _age_value_from_entry(entry: Dict[str, Any], value_key: str = "value") -> Optional[int]:
    numeric_value = _entry_numeric_value(entry)
    if numeric_value is not None:
        return _as_int(numeric_value, default=0)

    raw_value = entry.get(value_key)
    if raw_value is None:
        return None
    return _as_int(raw_value, default=0)


def build_numeric_values(email: Dict[str, Any]) -> Tuple[List[str], List[Any], Dict[str, Any]]:
    enrichment = _get_enrichment(email)

    # Header criteria (criterio 1)
    spf_val = _as_float(_entry_numeric_value(_get_enrichment_block(enrichment, "criterio1.spf")), default=1.0)
    dkim_val = _as_float(_entry_numeric_value(_get_enrichment_block(enrichment, "criterio1.dkim")), default=1.0)
    dmarc_val = _as_float(_entry_numeric_value(_get_enrichment_block(enrichment, "criterio1.dmarc")), default=1.0)

    php_entry = _get_dict(enrichment.get("php_mailer_or_similar_header_indicator"))
    php_score = _as_float(
        _entry_numeric_value(php_entry) if _entry_numeric_value(php_entry) is not None else php_entry.get("score"),
        default=0.0,
    )

    ip_entry = _get_dict(enrichment.get("ip_reputation"))
    ip_rep = _as_int(
        _entry_numeric_value(ip_entry) if _entry_numeric_value(ip_entry) is not None else ip_entry.get("score"),
        default=DEFAULTS["ip_rep"],
    )

    dom_entry = _get_dict(enrichment.get("domain_reputation"))
    dom_rep = None if _sender_domain_skipped(dom_entry) else _as_int(
        _entry_numeric_value(dom_entry) if _entry_numeric_value(dom_entry) is not None else dom_entry.get("score"),
        default=DEFAULTS["domain_rep"],
    )

    domip_entry = _get_dict(enrichment.get("domain_vs_ip_country"))
    dom_vs_ip_score = None if (_sender_domain_skipped(domip_entry) or _mcdm_excluded(domip_entry)) else _as_float(
        _entry_numeric_value(domip_entry) if _entry_numeric_value(domip_entry) is not None else domip_entry.get("score"),
        default=DEFAULTS["country_compare"],
    )

    domain_age_entry = _get_dict(enrichment.get("domain_age"))
    domain_age_days = _age_value_from_entry(domain_age_entry, value_key="age_days")

    sender_sub_entry = _get_dict(enrichment.get("sender_subdomain_count"))
    sender_subdomain_count = None if _sender_domain_skipped(sender_sub_entry) else _nullable_int_from_entry(
        sender_sub_entry,
        "subdomain_count",
    )
    sender_numeric_entry = _get_dict(enrichment.get("sender_numeric_subdomain"))
    sender_numeric_count = None if _sender_domain_skipped(sender_numeric_entry) else _nullable_int_from_entry(
        sender_numeric_entry,
        "value",
        "numeric_subdomain_count",
    )

    from_return_mismatch = _as_int(_get_dict(enrichment.get("from_return_path_subdomain_match")).get("value"), default=0)

    received_hops = _as_int(_get_dict(enrichment.get("received_hops_count")).get("value"), default=0)

    routing_domain_rep = _nullable_int_unless_insufficient(
        _get_dict(enrichment.get("routing_domain_reputation")),
        "value",
        "score",
    )
    routing_ip_rep = _nullable_int_unless_insufficient(
        _get_dict(enrichment.get("routing_ip_reputation")),
        "value",
        "score",
    )
    routing_domain_age = _age_value_from_entry(_get_dict(enrichment.get("routing_domain_age")))
    routing_country_mismatch = _nullable_float_from_entry(
        _get_dict(enrichment.get("routing_country_mismatch")),
        "value",
        "score",
    )
    routing_subdomain_count = _as_int(_get_dict(enrichment.get("routing_subdomain_count")).get("value"), default=0)

    received_time_delta = _as_int(_get_dict(enrichment.get("received_time_delta")).get("value"), default=0)

    # Body criteria (criterio 2)
    body_keywords = _as_int(_get_dict(enrichment.get("body_keywords")).get("value"), default=0)
    obf_base64 = _bool01(_get_dict(enrichment.get("body_obfuscation_base64")).get("value"))
    obf_unicode = _as_int(_get_dict(enrichment.get("body_obfuscation_unicode")).get("value"), default=0)

    link_count = _nullable_int_unless_insufficient(
        _get_dict(enrichment.get("link_count")),
        "value",
    )
    link_domain_rep = _nullable_int_unless_insufficient(
        _get_dict(enrichment.get("link_domain_reputation")),
        "value",
        "score",
    )
    link_country_entry = _get_dict(enrichment.get("link_domain_country_vs_modal"))
    link_country_mismatch = None if _sender_domain_skipped(link_country_entry) else _nullable_float_from_entry(
        link_country_entry,
        "value",
        "score",
    )
    link_domain_age_entry = _get_dict(enrichment.get("link_domain_age"))
    link_domain_age = None if _detail(link_domain_age_entry).get("insufficient_data") is True else _age_value_from_entry(
        link_domain_age_entry
    )
    link_subdomain = _nullable_int_unless_insufficient(
        _get_dict(enrichment.get("link_subdomain_count")),
        "value",
    )
    link_numeric = _link_numeric_subdomain_count(enrichment)
    link_match_entry = _get_dict(enrichment.get("link_domain_match_modal"))
    link_domain_match_modal = None if _sender_domain_skipped(link_match_entry) else _nullable_int_from_entry(
        link_match_entry,
        "value",
    )

    attachment_suspicious = _as_int(_get_dict(enrichment.get("attachment_types")).get("value"), default=0)
    html_tags_total = _as_int(_get_dict(enrichment.get("html_tag_count")).get("value"), default=0)
    link_captcha_count = _link_captcha_count(enrichment)
    html_beacons = _as_int(_get_dict(enrichment.get("html_beacon_count")).get("value"), default=0)

    values_by_key: Dict[str, Any] = {
        "c1_spf": spf_val,
        "c1_dkim": dkim_val,
        "c1_dmarc": dmarc_val,
        "c1_php_mailer_score": float(php_score),
        "c1_ip_reputation": int(ip_rep),
        "c1_domain_reputation": int(dom_rep) if dom_rep is not None else None,
        "c1_domain_vs_ip_country_score": float(dom_vs_ip_score) if dom_vs_ip_score is not None else None,
        "c1_domain_age_days": int(domain_age_days) if domain_age_days is not None else None,
        "c1_sender_subdomain_count": int(sender_subdomain_count) if sender_subdomain_count is not None else None,
        "c1_sender_numeric_subdomain_count": int(sender_numeric_count) if sender_numeric_count is not None else None,
        "c1_from_return_path_mismatch": int(from_return_mismatch),
        "c1_received_hops_count": int(received_hops),
        "c1_routing_domain_reputation": int(routing_domain_rep) if routing_domain_rep is not None else None,
        "c1_routing_ip_reputation": int(routing_ip_rep) if routing_ip_rep is not None else None,
        "c1_routing_domain_age_days": int(routing_domain_age) if routing_domain_age is not None else None,
        "c1_routing_country_mismatch": float(routing_country_mismatch) if routing_country_mismatch is not None else None,
        "c1_routing_subdomain_count": int(routing_subdomain_count),
        "c1_received_time_delta_seconds": int(received_time_delta),
        "c2_body_keywords_count": int(body_keywords),
        "c2_obfuscation_base64_present": int(obf_base64),
        "c2_obfuscation_unicode_count": int(obf_unicode),
        "c2_link_count": int(link_count) if link_count is not None else None,
        "c2_link_domain_reputation": int(link_domain_rep) if link_domain_rep is not None else None,
        "c2_link_domain_country_vs_modal_mismatch": float(link_country_mismatch) if link_country_mismatch is not None else None,
        "c2_link_domain_age_days": int(link_domain_age) if link_domain_age is not None else None,
        "c2_link_subdomain_count": int(link_subdomain) if link_subdomain is not None else None,
        "c2_link_numeric_subdomain_count": int(link_numeric) if link_numeric is not None else None,
        "c2_link_domain_match_modal_mismatch": int(link_domain_match_modal) if link_domain_match_modal is not None else None,
        "c2_attachment_suspicious_count": int(attachment_suspicious),
        "c2_html_tag_count": int(html_tags_total),
        "c2_link_captcha_present": int(link_captcha_count) if link_captcha_count is not None else None,
        "c2_html_beacon_count": int(html_beacons),
    }

    fields: List[str] = list(VECTOR_FIELD_ORDER)
    missing_fields = [field for field in fields if field not in values_by_key]
    extra_fields = [field for field in values_by_key if field not in fields]
    if missing_fields or extra_fields:
        raise RuntimeError(
            "La construccion de numeric_values no coincide con el esquema del vector. "
            f"Faltan: {missing_fields}. Sobran: {extra_fields}."
        )

    vector = [values_by_key.get(k) for k in fields]
    return fields, vector, values_by_key


def enrich_numeric_values_in_data(email: Dict[str, Any], force: bool = False) -> bool:
    existing = email.get("numeric_values")
    if (
        isinstance(existing, dict)
        and existing.get("checked")
        and existing.get("version") == 6
        and not force
    ):
        return False

    fields, vector, by_key = build_numeric_values(email)
    new_block = {
        "checked": True,
        "timestamp": _now_iso(),
        "version": 6,
        "fields": fields,
        "values": vector,
        "by_key": by_key,
    }

    if existing == new_block:
        return False
    email["numeric_values"] = new_block
    return True


__all__ = ["enrich_numeric_values_in_data", "build_numeric_values"]

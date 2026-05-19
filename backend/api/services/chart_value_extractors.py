from __future__ import annotations

"""
Define como convertir los valores de subcriterios en series agregadas para las
graficas del frontend. Este modulo solo prepara datos de visualizacion; la
puntuacion y normalizacion de cabeceras se importan desde utils para no
depender de scripts legacy ni de helpers que persisten enriquecimientos.
"""

from typing import Any, Dict, List, Optional, Sequence

from scripts.enrichment.vector_schema import ACTIVE_SUBCRITERIA_KEYS
from scripts.utils.auth_header_scoring import (
    DMARC_PASS_WITH_AUTH_FAILURE_SCORE,
    dkim_status_to_score,
    normalize_dkim_status,
    normalize_dmarc_status,
    normalize_spf_status,
    spf_status_to_score,
)


CHART_PLAN_BY_SUBCRITERION_KEY: Dict[str, Dict[str, str]] = {
    "spf": {"chart_type": "band_bars", "display_mode": "semantic_label"},
    "dkim": {"chart_type": "band_bars", "display_mode": "semantic_label"},
    "dmarc": {"chart_type": "band_bars", "display_mode": "semantic_label"},
    "php_mailer_or_similar_header_indicator": {"chart_type": "pie", "display_mode": "semantic_label"},
    "ip_reputation": {"chart_type": "stacked_bar", "display_mode": "semantic_label"},
    "domain_reputation": {"chart_type": "stacked_bar", "display_mode": "semantic_label"},
    "domain_vs_ip_country": {"chart_type": "pie", "display_mode": "semantic_label"},
    "domain_age": {"chart_type": "histogram", "display_mode": "raw_binned_value"},
    "sender_subdomain_count": {"chart_type": "bubble_lane", "display_mode": "raw_exact_value"},
    "sender_numeric_subdomain": {"chart_type": "pie", "display_mode": "semantic_label"},
    "from_return_path_subdomain_match": {"chart_type": "stacked_bar", "display_mode": "semantic_label"},
    "received_hops_count": {"chart_type": "bubble_lane", "display_mode": "raw_exact_value"},
    "routing_domain_reputation": {"chart_type": "stacked_bar", "display_mode": "semantic_label"},
    "routing_ip_reputation": {"chart_type": "stacked_bar", "display_mode": "semantic_label"},
    "routing_domain_age": {"chart_type": "histogram", "display_mode": "raw_binned_value"},
    "routing_country_mismatch": {"chart_type": "stacked_bar", "display_mode": "semantic_label"},
    "routing_subdomain_count": {"chart_type": "bubble_lane", "display_mode": "raw_exact_value"},
    "received_time_delta": {"chart_type": "histogram", "display_mode": "raw_binned_value"},
    "body_keywords": {"chart_type": "bubble_lane", "display_mode": "raw_exact_value"},
    "body_obfuscation_base64": {"chart_type": "stacked_bar", "display_mode": "semantic_label"},
    "body_obfuscation_unicode": {"chart_type": "histogram", "display_mode": "raw_binned_value"},
    "link_count": {"chart_type": "bubble_lane", "display_mode": "raw_exact_value"},
    "link_domain_reputation": {"chart_type": "stacked_bar", "display_mode": "semantic_label"},
    "link_domain_country_vs_modal": {"chart_type": "stacked_bar", "display_mode": "semantic_label"},
    "link_domain_age": {"chart_type": "histogram", "display_mode": "raw_binned_value"},
    "link_subdomain_count": {"chart_type": "bubble_lane", "display_mode": "raw_exact_value"},
    "link_numeric_subdomain": {"chart_type": "pie", "display_mode": "semantic_label"},
    "link_domain_match_modal": {"chart_type": "stacked_bar", "display_mode": "semantic_label"},
    "attachment_types": {"chart_type": "bubble_lane", "display_mode": "raw_exact_value"},
    "html_tag_count": {"chart_type": "histogram", "display_mode": "raw_binned_value"},
    "link_captcha": {"chart_type": "stacked_bar", "display_mode": "semantic_label"},
    "html_beacon_count": {"chart_type": "bubble_lane", "display_mode": "raw_exact_value"},
}


LABEL_ORDER_BY_SUBCRITERION_KEY: Dict[str, List[str]] = {
    "spf": ["pass", "neutral", "none", "temperror", "permerror", "softfail", "fail", "no-data"],
    "dkim": ["pass", "neutral", "none", "temperror", "permerror", "fail", "no-data"],
    "dmarc": [
        "pass",
        "temperror",
        "fail:none",
        "none",
        "pass-ajustado",
        "quarantine",
        "fail:quarantine",
        "permerror",
        "reject",
        "fail:reject",
        "no-data",
    ],
    "php_mailer_or_similar_header_indicator": ["Sin indicios", "Message-ID sospechoso", "Cabeceras sospechosas"],
    "ip_reputation": ["No listada", "Listada", "Sin datos -> riesgo"],
    "domain_reputation": ["No malicioso", "Malicioso", "Sin datos -> riesgo"],
    "domain_vs_ip_country": ["Coincide", "No coincide", "Sin datos"],
    "sender_numeric_subdomain": ["0 etiquetas", "1 etiqueta", "2+ etiquetas", "no data"],
    "from_return_path_subdomain_match": ["Coincide", "No coincide", "Sin datos -> riesgo"],
    "routing_domain_reputation": ["No malicioso", "Malicioso", "Sin datos"],
    "routing_ip_reputation": ["No listada", "Listada", "Sin datos"],
    "routing_country_mismatch": ["Coincide", "No coincide", "Sin datos"],
    "body_obfuscation_base64": ["Ausente", "Presente", "no data"],
    "link_domain_reputation": ["No malicioso", "Malicioso", "Sin datos"],
    "link_domain_country_vs_modal": ["Coincide", "No coincide", "Sin datos"],
    "link_numeric_subdomain": ["0 etiquetas", "1 etiqueta", "2+ etiquetas", "Sin datos"],
    "link_domain_match_modal": ["Coincide", "No coincide", "Sin datos"],
    "link_captcha": ["No", "Si", "Sin datos"],
}


HISTOGRAM_BIN_SPECS_BY_SUBCRITERION_KEY: Dict[str, List[Dict[str, float | str | None]]] = {
    "domain_age": [
        {"label": "0-1y", "start": 0.0, "end": 365.0},
        {"label": "1-2y", "start": 366.0, "end": 730.0},
        {"label": "2-5y", "start": 731.0, "end": 1825.0},
        {"label": "5-10y", "start": 1826.0, "end": 3650.0},
        {"label": "10-15y", "start": 3651.0, "end": 5475.0},
        {"label": "15-20y", "start": 5476.0, "end": 7300.0},
        {"label": "20y+", "start": 7301.0, "end": None},
    ],
    "routing_domain_age": [
        {"label": "0-1y", "start": 0.0, "end": 365.0},
        {"label": "1-2y", "start": 366.0, "end": 730.0},
        {"label": "2-5y", "start": 731.0, "end": 1825.0},
        {"label": "5-10y", "start": 1826.0, "end": 3650.0},
        {"label": "10-15y", "start": 3651.0, "end": 5475.0},
        {"label": "15-20y", "start": 5476.0, "end": 7300.0},
        {"label": "20y+", "start": 7301.0, "end": None},
    ],
    "link_domain_age": [
        {"label": "0-1121d", "start": 0.0, "end": 1121.0},
        {"label": "1122-2657d", "start": 1122.0, "end": 2657.0},
        {"label": "2658-3841d", "start": 2658.0, "end": 3841.0},
        {"label": "3842-<5151.6d", "start": 3842.0, "end": 5151.6},
        {"label": "5151.6-6986d", "start": 5151.6, "end": 6986.0},
        {"label": "6987-8543d", "start": 6987.0, "end": 8543.0},
        {"label": "8544-<10220d", "start": 8544.0, "end": 10220.0},
        {"label": "10220d+", "start": 10220.0, "end": None},
    ],
    "received_time_delta": [
        {"label": "0-5s", "start": 0.0, "end": 5.0},
        {"label": "6-30s", "start": 6.0, "end": 30.0},
        {"label": "31-120s", "start": 31.0, "end": 120.0},
        {"label": "121-600s", "start": 121.0, "end": 600.0},
        {"label": "601+", "start": 601.0, "end": None},
    ],
    "body_obfuscation_unicode": [
        {"label": "0", "start": 0.0, "end": 0.0},
        {"label": "1-2", "start": 1.0, "end": 2.0},
        {"label": "3-5", "start": 3.0, "end": 5.0},
        {"label": "6-10", "start": 6.0, "end": 10.0},
        {"label": "11+", "start": 11.0, "end": None},
    ],
    "html_tag_count": [
        {"label": "0-75", "start": 0.0, "end": 75.0},
        {"label": "76-150", "start": 76.0, "end": 150.0},
        {"label": "151-200", "start": 151.0, "end": 200.0},
        {"label": "201-300", "start": 201.0, "end": 300.0},
        {"label": "301+", "start": 301.0, "end": None},
    ],
}


SCORE_BAND_SPECS = [
    {"label": "0-0.2", "start": 0.0, "end": 0.2},
    {"label": "0.2-0.4", "start": 0.2, "end": 0.4},
    {"label": "0.4-0.6", "start": 0.4, "end": 0.6},
    {"label": "0.6-0.8", "start": 0.6, "end": 0.8},
    {"label": "0.8-1.0", "start": 0.8, "end": 1.0},
]


def chart_config_for_subcriterion(subcriterion_key: str) -> Dict[str, str]:
    return dict(
        CHART_PLAN_BY_SUBCRITERION_KEY.get(
            subcriterion_key,
            {"chart_type": "histogram", "display_mode": "raw_binned_value"},
        )
    )


def label_order_for_subcriterion(subcriterion_key: str) -> List[str]:
    return LABEL_ORDER_BY_SUBCRITERION_KEY.get(subcriterion_key, [])


def histogram_bin_specs_for_subcriterion(subcriterion_key: str) -> List[Dict[str, float | str | None]]:
    return HISTOGRAM_BIN_SPECS_BY_SUBCRITERION_KEY.get(subcriterion_key, [])


def _detail_dict(result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(result, dict):
        return {}
    detail = result.get("detail")
    return detail if isinstance(detail, dict) else {}


def _insufficient(result: Optional[Dict[str, Any]]) -> bool:
    detail = _detail_dict(result)
    if detail.get("insufficient_data") is True:
        return True
    meta = detail.get("meta")
    return bool(isinstance(meta, dict) and meta.get("insufficient_data") is True)


def _skipped_due_unreliable_sender_domain(result: Optional[Dict[str, Any]]) -> bool:
    detail = _detail_dict(result)
    return (
        detail.get("skipped_due_unreliable_sender_domain") is True
        or detail.get("error_reason") == "sender_domain_not_reliably_available_dmarc_not_pass"
    )


def _mcdm_excluded_result(result: Optional[Dict[str, Any]]) -> bool:
    detail = _detail_dict(result)
    return detail.get("mcdm_excluded") is True


def _label_bool(
    result: Optional[Dict[str, Any]],
    value: Any,
    *,
    true_label: str,
    false_label: str,
    insufficient_label: str = "no data",
) -> Optional[str]:
    if _insufficient(result):
        return insufficient_label
    if value is None:
        return None
    return true_label if int(value) != 0 else false_label


def _label_numeric_bucket(value: Any) -> Optional[str]:
    if value is None:
        return None
    numeric = int(value)
    if numeric <= 0:
        return "0 etiquetas"
    if numeric == 1:
        return "1 etiqueta"
    return "2+ etiquetas"


def _numeric_from_result(result: Optional[Dict[str, Any]], display_value: Any) -> Optional[float]:
    if isinstance(display_value, (int, float)):
        return float(display_value)
    if not isinstance(result, dict):
        return None
    for key in ("value", "score", "age_days"):
        raw_value = result.get(key)
        if isinstance(raw_value, (int, float)):
            return float(raw_value)
    return None


def _extract_spf_label(result: Optional[Dict[str, Any]]) -> Optional[str]:
    if not isinstance(result, dict):
        return None
    detail = _detail_dict(result)
    sources = detail.get("sources") if isinstance(detail.get("sources"), dict) else {}
    statuses: List[str] = []
    for key in ("received_spf", "authentication_results"):
        raw_values = sources.get(key)
        if isinstance(raw_values, list):
            statuses.extend([normalize_spf_status(str(value)) for value in raw_values if isinstance(value, str)])
    if not statuses:
        return "no-data"
    return max(statuses, key=lambda status: spf_status_to_score(status) or 1.0)


def _extract_dkim_label(result: Optional[Dict[str, Any]]) -> Optional[str]:
    if not isinstance(result, dict):
        return None
    detail = _detail_dict(result)
    sources = detail.get("sources") if isinstance(detail.get("sources"), dict) else {}
    raw_values = sources.get("authentication_results")
    statuses = [normalize_dkim_status(str(value)) for value in raw_values if isinstance(value, str)] if isinstance(raw_values, list) else []
    if not statuses:
        return "no-data"
    return max(statuses, key=lambda status: dkim_status_to_score(status) or 1.0)


def _extract_dmarc_label(result: Optional[Dict[str, Any]]) -> Optional[str]:
    if not isinstance(result, dict):
        return None

    detail = _detail_dict(result)
    observations = detail.get("observations")
    best_label = None
    best_score = None
    if isinstance(observations, list):
        for observation in observations:
            if not isinstance(observation, dict):
                continue
            raw_score = observation.get("score")
            if not isinstance(raw_score, (int, float)):
                continue
            normalized_result = normalize_dmarc_status(str(observation.get("result") or ""))
            policy = observation.get("policy")
            normalized_policy = normalize_dmarc_status(str(policy)) if isinstance(policy, str) else None
            if normalized_result == "fail" and normalized_policy in {"none", "quarantine", "reject"}:
                label = f"fail:{normalized_policy}"
            elif normalized_result == "pass" and float(raw_score) >= DMARC_PASS_WITH_AUTH_FAILURE_SCORE:
                label = "pass-ajustado"
            elif normalized_result:
                label = normalized_result
            else:
                label = "no-data"
            score = float(raw_score)
            if best_score is None or score > best_score:
                best_score = score
                best_label = label

    if best_label:
        return best_label

    tokens = detail.get("tokens")
    if isinstance(tokens, list) and tokens:
        return normalize_dmarc_status(str(tokens[0]))
    return "no-data"


def _extract_php_mailer_label(result: Optional[Dict[str, Any]]) -> Optional[str]:
    if not isinstance(result, dict):
        return None
    detail = _detail_dict(result)
    matched_rules = detail.get("matched_rules")
    matched = {str(item) for item in matched_rules} if isinstance(matched_rules, list) else set()
    if "mailer_libs" in matched or "received_markers" in matched:
        return "Cabeceras sospechosas"
    if detail.get("message_id_suspicious") is True:
        return "Message-ID sospechoso"
    return "Sin indicios"


def extract_chart_display_record(
    subcriterion_key: str,
    result: Optional[Dict[str, Any]],
    display_value: Any,
) -> Optional[Dict[str, Any]]:
    if result is None:
        return None

    config = chart_config_for_subcriterion(subcriterion_key)
    display_mode = config["display_mode"]

    if subcriterion_key == "spf":
        label = _extract_spf_label(result)
        return {"kind": display_mode, "label": label}

    if subcriterion_key == "dkim":
        label = _extract_dkim_label(result)
        return {"kind": display_mode, "label": label}

    if subcriterion_key == "dmarc":
        label = _extract_dmarc_label(result)
        return {"kind": display_mode, "label": label}

    if subcriterion_key == "php_mailer_or_similar_header_indicator":
        label = _extract_php_mailer_label(result)
        return {"kind": display_mode, "label": label}

    if subcriterion_key == "domain_vs_ip_country":
        label = _detail_dict(result).get("comparison_status")
        translated = {
            "match": "Coincide",
            "mismatch": "No coincide",
            "fallback_risk": "Sin datos",
            "no_data": "Sin datos",
            "not_applicable_no_country_tld": "Sin datos",
        }.get(str(label or "fallback_risk"), "Sin datos")
        return {"kind": display_mode, "label": translated}

    if subcriterion_key in {"ip_reputation", "routing_ip_reputation"}:
        label = _label_bool(
            result,
            display_value,
            true_label="Listada",
            false_label="No listada",
            insufficient_label="Sin datos" if subcriterion_key == "routing_ip_reputation" else "Sin datos -> riesgo",
        )
        return {"kind": display_mode, "label": label} if label else None

    if subcriterion_key in {"domain_reputation", "routing_domain_reputation", "link_domain_reputation"}:
        label = _label_bool(
            result,
            display_value,
            true_label="Malicioso",
            false_label="No malicioso",
            insufficient_label=(
                "Sin datos"
                if subcriterion_key in {"routing_domain_reputation", "link_domain_reputation"} or _skipped_due_unreliable_sender_domain(result)
                else "Sin datos -> riesgo"
            ),
        )
        return {"kind": display_mode, "label": label} if label else None

    if subcriterion_key in {"routing_country_mismatch", "link_domain_country_vs_modal"}:
        if _mcdm_excluded_result(result):
            return {"kind": display_mode, "label": "Sin datos"}
        label = _label_bool(
            result,
            display_value,
            true_label="No coincide",
            false_label="Coincide",
            insufficient_label="Sin datos",
        )
        return {"kind": display_mode, "label": label} if label else None

    if subcriterion_key in {"from_return_path_subdomain_match", "link_domain_match_modal"}:
        label = _label_bool(
            result,
            display_value,
            true_label="No coincide",
            false_label="Coincide",
            insufficient_label="Sin datos" if subcriterion_key == "link_domain_match_modal" or _skipped_due_unreliable_sender_domain(result) else "Sin datos -> riesgo",
        )
        return {"kind": display_mode, "label": label} if label else None

    if subcriterion_key in {"body_obfuscation_base64", "link_captcha"}:
        true_label = "Si" if subcriterion_key == "link_captcha" else "Presente"
        false_label = "No" if subcriterion_key == "link_captcha" else "Ausente"
        label = _label_bool(
            result,
            display_value,
            true_label=true_label,
            false_label=false_label,
            insufficient_label="Sin datos" if subcriterion_key == "link_captcha" else "no data",
        )
        return {"kind": display_mode, "label": label} if label else None

    if subcriterion_key in {"sender_numeric_subdomain", "link_numeric_subdomain"}:
        if _insufficient(result):
            return {"kind": display_mode, "label": "Sin datos" if subcriterion_key == "link_numeric_subdomain" else "no data"}
        label = _label_numeric_bucket(display_value)
        return {"kind": display_mode, "label": label, "numeric_value": int(display_value or 0)} if label else None

    if display_mode == "native_score_band":
        numeric_value = _numeric_from_result(result, display_value)
        if numeric_value is None or _insufficient(result):
            return None
        return {"kind": display_mode, "numeric_value": numeric_value}

    if display_mode == "raw_exact_value":
        if subcriterion_key in {"sender_subdomain_count", "received_time_delta"} and _insufficient(result):
            return None
        if subcriterion_key in {"link_subdomain_count", "attachment_types"} and _insufficient(result):
            return None
        numeric_value = _numeric_from_result(result, display_value)
        if numeric_value is None:
            return None
        return {
            "kind": display_mode,
            "numeric_value": numeric_value,
            "label": str(int(numeric_value) if float(numeric_value).is_integer() else round(float(numeric_value), 2)),
        }

    if display_mode == "raw_binned_value":
        if _insufficient(result) and subcriterion_key in {"domain_age", "routing_domain_age", "link_domain_age", "received_time_delta"}:
            return None
        numeric_value = _numeric_from_result(result, display_value)
        if numeric_value is None:
            return None
        return {"kind": display_mode, "numeric_value": numeric_value}

    return None


def build_label_segments(
    subcriterion_key: str,
    labels: Sequence[str],
) -> List[Dict[str, Any]]:
    if not labels:
        return []
    counts: Dict[str, int] = {}
    for label in labels:
        counts[label] = counts.get(label, 0) + 1

    total = len(labels)
    ordered_labels = label_order_for_subcriterion(subcriterion_key)
    unordered_labels = [label for label in counts if label not in ordered_labels]
    sorted_labels = [*ordered_labels, *sorted(unordered_labels)]
    segments: List[Dict[str, Any]] = []
    for index, label in enumerate(sorted_labels):
        count = counts.get(label)
        if not count:
            continue
        segments.append(
            {
                "label": label,
                "value": float(index),
                "count": count,
                "ratio": round(count / total, 6),
            }
        )
    return segments


def build_label_bins(
    subcriterion_key: str,
    labels: Sequence[str],
) -> List[Dict[str, Any]]:
    segments = build_label_segments(subcriterion_key, labels)
    return [
        {
            "label": item["label"],
            "start": float(index),
            "end": float(index + 1),
            "center": float(index + 0.5),
            "count": item["count"],
            "ratio": item["ratio"],
        }
        for index, item in enumerate(segments)
    ]


def build_score_band_bins(values: Sequence[float]) -> List[Dict[str, Any]]:
    if not values:
        return []
    total = len(values)
    bins: List[Dict[str, Any]] = []
    for index, spec in enumerate(SCORE_BAND_SPECS):
        start = float(spec["start"])
        end = float(spec["end"])
        if index == len(SCORE_BAND_SPECS) - 1:
            count = sum(1 for value in values if start <= value <= end)
        else:
            count = sum(1 for value in values if start <= value < end)
        bins.append(
            {
                "label": str(spec["label"]),
                "start": start,
                "end": end,
                "center": round((start + end) / 2, 6),
                "count": count,
                "ratio": round(count / total, 6),
            }
        )
    return bins


def build_semantic_histogram_bins(
    subcriterion_key: str,
    values: Sequence[float],
) -> List[Dict[str, Any]]:
    specs = histogram_bin_specs_for_subcriterion(subcriterion_key)
    if not values or not specs:
        return []

    total = len(values)
    bins: List[Dict[str, Any]] = []
    for index, spec in enumerate(specs):
        start = float(spec["start"])
        end = spec["end"]
        next_start = None
        if index + 1 < len(specs):
            next_start_raw = specs[index + 1].get("start")
            if isinstance(next_start_raw, (int, float)):
                next_start = float(next_start_raw)
        if end is None:
            count = sum(1 for value in values if value >= start)
            center = start
        elif next_start is not None:
            count = sum(1 for value in values if start <= value < next_start)
            center = (start + float(end)) / 2
        else:
            numeric_end = float(end)
            count = sum(1 for value in values if start <= value <= numeric_end)
            center = (start + numeric_end) / 2
        bins.append(
            {
                "label": str(spec["label"]),
                "start": start,
                "end": float(end) if isinstance(end, (int, float)) else start,
                "center": round(center, 6),
                "count": count,
                "ratio": round(count / total, 6),
            }
        )
    return bins


def build_numeric_points(values: Sequence[float]) -> List[Dict[str, Any]]:
    if not values:
        return []
    counts: Dict[float, int] = {}
    for value in values:
        rounded = round(float(value), 6)
        counts[rounded] = counts.get(rounded, 0) + 1

    total = len(values)
    points: List[Dict[str, Any]] = []
    for raw_value in sorted(counts):
        count = counts[raw_value]
        label = str(int(raw_value)) if float(raw_value).is_integer() else str(round(raw_value, 2))
        points.append(
            {
                "label": label,
                "value": raw_value,
                "count": count,
                "ratio": round(count / total, 6),
            }
        )
    return points


def _validate_chart_contract() -> None:
    missing_chart_config = [key for key in ACTIVE_SUBCRITERIA_KEYS if key not in CHART_PLAN_BY_SUBCRITERION_KEY]
    if missing_chart_config:
        raise RuntimeError(
            "Faltan configuraciones de graficas para subcriterios activos. "
            f"Faltan: {sorted(missing_chart_config)}."
        )

    missing_label_orders = [
        key
        for key in ACTIVE_SUBCRITERIA_KEYS
        if CHART_PLAN_BY_SUBCRITERION_KEY.get(key, {}).get("display_mode") == "semantic_label"
        and key not in LABEL_ORDER_BY_SUBCRITERION_KEY
    ]
    if missing_label_orders:
        raise RuntimeError(
            "Faltan ordenes de etiquetas para graficas semanticas activas. "
            f"Faltan: {sorted(missing_label_orders)}."
        )

    missing_hist_specs = [
        key
        for key in ACTIVE_SUBCRITERIA_KEYS
        if CHART_PLAN_BY_SUBCRITERION_KEY.get(key, {}).get("display_mode") == "raw_binned_value"
        and key not in HISTOGRAM_BIN_SPECS_BY_SUBCRITERION_KEY
    ]
    if missing_hist_specs:
        raise RuntimeError(
            "Faltan bins de histograma para subcriterios activos con display_mode raw_binned_value. "
            f"Faltan: {sorted(missing_hist_specs)}."
        )


_validate_chart_contract()

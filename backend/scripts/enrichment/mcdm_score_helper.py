from __future__ import annotations

"""
Transforma valores del vector a puntuaciones unitarias, aplica exclusiones dinamicas y calcula TOPSIS para correos individuales o lotes.
"""

import os
from datetime import datetime, timezone
from math import log, sqrt
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from dotenv import load_dotenv

from enrichment.numeric_values_helper import build_numeric_values
from utils.origin_resolution import resolve_sender_domain
from enrichment.vector_schema import (
    LINK_COUNT_ZERO_SCORE_THRESHOLD,
    MCDM_FIELD_CURVES,
    MCDM_FIELD_DESATURATION,
    MCDM_FIELD_OBJECTIVES,
    MCDM_FIELD_PIECEWISE,
    MCDM_FIELD_WEIGHTS,
    RELIABLE_SENDER_DOMAIN_VECTOR_FIELDS,
    VECTOR_FIELD_ORDER,
)
from enrichment.topsis_library_helper import topsis_scores_with_library

load_dotenv()


NULL_UNIT_SCORE = 0.5
LINK_COUNT_FIELD = "c2_link_count"
LINK_CONTEXT_ZERO_FIELDS = {
    field
    for field in VECTOR_FIELD_ORDER
    if field == LINK_COUNT_FIELD or field.startswith("c2_link_")
}
INDIVIDUAL_REFERENCE_SOURCE = "Phishpot1050"
INDIVIDUAL_REFERENCE_BEST_EMAIL_ID = "9764a18d-9940-4cf4-9ff2-214181576b67"
INDIVIDUAL_REFERENCE_WORST_EMAIL_ID = "3082bb31-a7e5-4269-98bf-9a72693f99b6"
INDIVIDUAL_REFERENCE_BEST_MCDM_SCORE = 0.031186
INDIVIDUAL_REFERENCE_WORST_MCDM_SCORE = 0.593291
INDIVIDUAL_REFERENCE_BEST_VECTOR: Dict[str, Any] = {
    "c1_spf": 0.0,
    "c1_dkim": 0.0,
    "c1_dmarc": 0.0,
    "c1_php_mailer_score": 0.0,
    "c1_ip_reputation": 1,
    "c1_domain_reputation": 1,
    "c1_domain_vs_ip_country_score": 0.5,
    "c1_domain_age_days": None,
    "c1_sender_subdomain_count": None,
    "c1_sender_numeric_subdomain_count": None,
    "c1_from_return_path_mismatch": 0,
    "c1_received_hops_count": 2,
    "c1_routing_domain_reputation": 0,
    "c1_routing_ip_reputation": 0,
    "c1_routing_domain_age_days": 3913,
    "c1_routing_country_mismatch": 0.0,
    "c1_routing_subdomain_count": 2,
    "c1_received_time_delta_seconds": 0,
    "c2_body_keywords_count": 0,
    "c2_obfuscation_base64_present": 0,
    "c2_obfuscation_unicode_count": 0,
    "c2_link_count": 42,
    "c2_link_domain_reputation": None,
    "c2_link_domain_country_vs_modal_mismatch": None,
    "c2_link_domain_age_days": None,
    "c2_link_subdomain_count": None,
    "c2_link_numeric_subdomain_count": None,
    "c2_link_domain_match_modal_mismatch": 0,
    "c2_attachment_suspicious_count": 0,
    "c2_html_tag_count": 611,
    "c2_link_captcha_present": None,
    "c2_html_beacon_count": 0,
}
INDIVIDUAL_REFERENCE_WORST_VECTOR: Dict[str, Any] = {
    "c1_spf": 1.0,
    "c1_dkim": 1.0,
    "c1_dmarc": 0.6,
    "c1_php_mailer_score": 0.0,
    "c1_ip_reputation": 1,
    "c1_domain_reputation": 1,
    "c1_domain_vs_ip_country_score": 0.5,
    "c1_domain_age_days": None,
    "c1_sender_subdomain_count": None,
    "c1_sender_numeric_subdomain_count": None,
    "c1_from_return_path_mismatch": 0,
    "c1_received_hops_count": 7,
    "c1_routing_domain_reputation": 0,
    "c1_routing_ip_reputation": 0,
    "c1_routing_domain_age_days": 235,
    "c1_routing_country_mismatch": None,
    "c1_routing_subdomain_count": 3,
    "c1_received_time_delta_seconds": 0,
    "c2_body_keywords_count": 0,
    "c2_obfuscation_base64_present": 0,
    "c2_obfuscation_unicode_count": 0,
    "c2_link_count": 2,
    "c2_link_domain_reputation": 0,
    "c2_link_domain_country_vs_modal_mismatch": None,
    "c2_link_domain_age_days": 235,
    "c2_link_subdomain_count": None,
    "c2_link_numeric_subdomain_count": None,
    "c2_link_domain_match_modal_mismatch": 0,
    "c2_attachment_suspicious_count": 0,
    "c2_html_tag_count": 22,
    "c2_link_captcha_present": None,
    "c2_html_beacon_count": 0,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _as_float(value: Any) -> float:
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def _desaturation_enabled() -> bool:
    raw = os.getenv("MCDM_DESATURATION_ENABLED")
    if raw is None:
        return True
    return raw.strip().lower() not in ("0", "false", "no", "off")


def _uses_anchor_scaling(field: str) -> bool:
    return field in MCDM_FIELD_PIECEWISE


def _effective_objective(field: str) -> str:
    if _uses_anchor_scaling(field):

        return "maximize"
    objective = MCDM_FIELD_OBJECTIVES.get(field)
    if objective not in {"maximize", "minimize"}:
        raise RuntimeError(f"Objetivo MCDM no soportado para '{field}': {objective}")
    return objective


def _desaturate_value(field: str, value: float) -> float:
    config = MCDM_FIELD_DESATURATION.get(field)
    if not config or not _desaturation_enabled():
        return value

    method = config.get("method")
    if method != "half_saturation":
        raise RuntimeError(f"Metodo de desaturacion MCDM no soportado para '{field}': {method}")

    half_saturation = float(config["half_saturation"])
    safe_value = max(value, 0.0)
    return safe_value / (safe_value + half_saturation)


def _piecewise_value(field: str, value: float) -> Optional[float]:
    config = MCDM_FIELD_PIECEWISE.get(field)
    if not config:
        return None

    method = config.get("method")
    if method != "piecewise_linear":
        raise RuntimeError(f"Metodo piecewise MCDM no soportado para '{field}': {method}")

    anchors = config.get("anchors")
    if not isinstance(anchors, list) or len(anchors) < 2:
        raise RuntimeError(f"Configuracion piecewise invalida para '{field}'.")

    safe_value = max(value, 0.0)
    first = anchors[0]
    if safe_value <= float(first["value"]):
        return float(first["score"])

    for previous, current in zip(anchors, anchors[1:]):
        previous_value = float(previous["value"])
        current_value = float(current["value"])
        previous_score = float(previous["score"])
        current_score = float(current["score"])
        if safe_value <= current_value:
            span = current_value - previous_value
            if span <= 0:
                return current_score
            ratio = (safe_value - previous_value) / span
            return previous_score + ((current_score - previous_score) * ratio)

    last = anchors[-1]
    return float(last["score"])


def _curve_value(field: str, value: float) -> Optional[float]:
    config = MCDM_FIELD_CURVES.get(field)
    if not config:
        return None

    method = config.get("method")
    safe_value = max(value, 0.0)

    if method == "peak_one_inverse":
        if safe_value <= 0.0:
            return 0.0
        if safe_value <= 1.0:
            return 1.0
        return 1.0 / safe_value

    if method == "peak_one_inverse_sqrt":
        if safe_value <= 0.0:
            return 0.0
        if safe_value <= 1.0:
            return 1.0
        return 1.0 / sqrt(safe_value)

    if method == "log_scale_cap":
        cap_days = float(config.get("cap_days") or 3650.0)
        capped_value = min(safe_value, cap_days)
        denominator = log(cap_days + 1.0)
        if denominator <= 0.0:
            return 0.0
        return capped_value if capped_value <= 0.0 else log(capped_value + 1.0) / denominator

    if method == "sqrt_scale_cap":
        cap_days = float(config.get("cap_days") or 3650.0)
        capped_value = min(safe_value, cap_days)
        if cap_days <= 0.0:
            return 0.0
        return sqrt(capped_value / cap_days)

    raise RuntimeError(f"Curva MCDM no soportada para '{field}': {method}")


def _transform_value_for_mcdm(field: str, value: float) -> float:
    curve = _curve_value(field, value)
    if curve is not None:
        return curve
    piecewise = _piecewise_value(field, value)
    if piecewise is not None:
        return piecewise
    return _desaturate_value(field, value)


def _null_unit_score() -> float:
    return float(NULL_UNIT_SCORE)


def field_unit_score(field: str, value: Any) -> float | None:
    if value is None:
        return _null_unit_score()

    numeric_value = _as_float(value)
    if numeric_value != numeric_value:
        return _null_unit_score()

    safe_value = max(numeric_value, 0.0)
    objective = _effective_objective(field)
    if (
        field in MCDM_FIELD_CURVES
        or field in MCDM_FIELD_PIECEWISE
        or (field in MCDM_FIELD_DESATURATION and _desaturation_enabled())
    ):
        transformed = _transform_value_for_mcdm(field, safe_value)
        if _uses_anchor_scaling(field):
            return round(transformed, 6)
        if objective == "maximize":
            return round(transformed, 6)
        if objective == "minimize":
            return round(1.0 - transformed, 6)
        raise RuntimeError(f"Objetivo MCDM no soportado para '{field}': {objective}")

    if objective == "maximize":
        if safe_value <= 1.0:
            return round(safe_value, 6)
        return round(safe_value / (1.0 + safe_value), 6)

    if objective == "minimize":
        return round(1.0 / (1.0 + safe_value), 6)

    raise RuntimeError(f"Objetivo MCDM no soportado para '{field}': {objective}")


def _link_count_context_value(values_by_field: Mapping[str, Any]) -> Optional[float]:
    value = values_by_field.get(LINK_COUNT_FIELD)
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return max(float(value), 0.0)
    return None


def _link_count_zeroes_link_scores(values_by_field: Mapping[str, Any]) -> bool:
    link_count = _link_count_context_value(values_by_field)
    return link_count is not None and (
        link_count == 0.0
        or link_count >= LINK_COUNT_ZERO_SCORE_THRESHOLD
    )


def field_unit_score_with_context(
    field: str,
    value: Any,
    values_by_field: Mapping[str, Any],
) -> float | None:
    if field in LINK_CONTEXT_ZERO_FIELDS and _link_count_zeroes_link_scores(values_by_field):
        return 0.0
    return field_unit_score(field, value)


def _build_numeric_values_block(email: Dict[str, Any]) -> Dict[str, Any]:
    fields, values, by_key = build_numeric_values(email)
    return {
        "checked": True,
        "timestamp": _now_iso(),
        "version": 6,
        "fields": fields,
        "values": values,
        "by_key": by_key,
    }


def _ensure_numeric_values_block(email: Dict[str, Any]) -> Dict[str, Any]:
    numeric_values = email.get("numeric_values")
    fields = numeric_values.get("fields") if isinstance(numeric_values, dict) else None
    values = numeric_values.get("values") if isinstance(numeric_values, dict) else None
    by_key = numeric_values.get("by_key") if isinstance(numeric_values, dict) else None
    version = numeric_values.get("version") if isinstance(numeric_values, dict) else None
    if isinstance(fields, list) and isinstance(values, list) and isinstance(by_key, dict) and version == 6:
        return numeric_values

    numeric_values = _build_numeric_values_block(email)
    email["numeric_values"] = numeric_values
    return numeric_values


def _hardcoded_reference_numeric_values_block(vector: Mapping[str, Any]) -> Dict[str, Any]:
    by_key = {field: vector.get(field) for field in VECTOR_FIELD_ORDER}
    return {
        "checked": True,
        "timestamp": _now_iso(),
        "version": 6,
        "fields": list(VECTOR_FIELD_ORDER),
        "values": [by_key[field] for field in VECTOR_FIELD_ORDER],
        "by_key": by_key,
    }


def _extract_numeric_vector(
    numeric_values: Mapping[str, Any],
) -> Tuple[List[str], List[Optional[float]], int]:
    version = numeric_values.get("version")
    if version != 6:
        raise RuntimeError(
            "Solo se soporta numeric_values version 6. "
            f"Version recibida: {version!r}."
        )

    raw_fields = numeric_values.get("fields")
    fields = [str(field) for field in raw_fields] if isinstance(raw_fields, list) else None
    if fields != list(VECTOR_FIELD_ORDER):
        raise RuntimeError(
            "El orden de campos de numeric_values no coincide con la version actual del vector."
        )

    by_key = numeric_values.get("by_key") if isinstance(numeric_values.get("by_key"), dict) else {}
    if set(by_key.keys()) != set(VECTOR_FIELD_ORDER):
        raise RuntimeError(
            "Las claves de numeric_values.by_key no coinciden con la version actual del vector."
        )

    raw_values = numeric_values.get("values")
    if not isinstance(raw_values, list) or len(raw_values) != len(fields):
        raise RuntimeError(
            "numeric_values.values no coincide en longitud con la version actual del vector."
        )

    row: List[Optional[float]] = []
    zero_link_scores = _link_count_zeroes_link_scores(by_key)
    for field in fields:
        if zero_link_scores and field in LINK_CONTEXT_ZERO_FIELDS:
            row.append(0.0)
            continue
        value = by_key.get(field)
        row.append(_null_unit_score() if value is None else _transform_value_for_mcdm(field, _as_float(value)))
    return fields, row, 6


def _runtime_ignored_vector_fields(email: Mapping[str, Any]) -> Dict[str, str]:
    ignored: Dict[str, str] = {}
    headers = email.get("headers") if isinstance(email, Mapping) else None
    headers = headers if isinstance(headers, dict) else {}
    resolution = resolve_sender_domain(headers, reliable_only=True)
    has_reliable_sender_domain = isinstance(resolution.get("domain"), str) and bool(resolution.get("domain"))
    if not has_reliable_sender_domain:
        for field in RELIABLE_SENDER_DOMAIN_VECTOR_FIELDS:
            ignored[field] = "sender_domain_not_reliably_available_dmarc_not_pass"
    enrichment = email.get("enrichment") if isinstance(email, Mapping) else None
    enrichment = enrichment if isinstance(enrichment, dict) else {}
    domip_entry = enrichment.get("domain_vs_ip_country")
    domip_detail = domip_entry.get("detail") if isinstance(domip_entry, dict) else None
    if isinstance(domip_detail, dict) and domip_detail.get("mcdm_excluded") is True:
        ignored["c1_domain_vs_ip_country_score"] = str(
            domip_detail.get("mcdm_exclusion_reason") or "domain_vs_ip_country_excluded"
        )
    routing_country_entry = enrichment.get("routing_country_mismatch")
    routing_country_detail = routing_country_entry.get("detail") if isinstance(routing_country_entry, dict) else None
    if isinstance(routing_country_detail, dict) and routing_country_detail.get("mcdm_excluded") is True:
        ignored["c1_routing_country_mismatch"] = str(
            routing_country_detail.get("mcdm_exclusion_reason") or "routing_country_mismatch_excluded"
        )
    return ignored


def _apply_runtime_ignored_fields(
    fields: Sequence[str],
    row: Sequence[Optional[float]],
    ignored_fields: Mapping[str, str],
) -> List[Optional[float]]:
    if not ignored_fields:
        return list(row)
    masked: List[Optional[float]] = []
    for field, value in zip(fields, row):
        masked.append(_null_unit_score() if field in ignored_fields else value)
    return masked


def _normalized_weights(fields: Sequence[str]) -> List[float]:
    raw_weights: List[float] = []
    for field in fields:
        if field not in MCDM_FIELD_WEIGHTS:
            raise RuntimeError(f"Falta peso MCDM para el campo '{field}'.")
        weight = float(MCDM_FIELD_WEIGHTS[field])
        if weight < 0:
            raise RuntimeError(f"El peso MCDM de '{field}' no puede ser negativo.")
        raw_weights.append(weight)

    total = sum(raw_weights)
    if total <= 0:
        raise RuntimeError("La suma de pesos MCDM debe ser mayor que cero.")
    return [weight / total for weight in raw_weights]


def _with_reference_anchors(
    matrix: List[List[Optional[float]]],
    fields: Sequence[str],
) -> Tuple[List[List[Optional[float]]], str, bool]:
    actual_count = len(matrix)
    if actual_count >= 2:
        return matrix, "topsis", False

    risky_anchor: List[Optional[float]] = []
    benign_anchor: List[Optional[float]] = []
    for index, field in enumerate(fields):
        lower = 0.0
        available = [row[index] for row in matrix if row[index] is not None]
        upper = max(available, default=0.0)
        objective = _effective_objective(field)
        if objective == "maximize":
            risky_anchor.append(upper)
            benign_anchor.append(lower)
        elif objective == "minimize":
            risky_anchor.append(lower)
            benign_anchor.append(upper)
        else:
            raise RuntimeError(f"Objetivo MCDM no soportado para '{field}': {objective}")

    extended = list(matrix)
    extended.append(risky_anchor)
    extended.append(benign_anchor)
    return extended, "topsis_with_reference_anchors", True


def _topsis_scores(matrix: List[List[Optional[float]]], fields: Sequence[str]) -> List[float]:
    if not matrix:
        return []

    weights = _normalized_weights(fields)
    column_count = len(fields)
    criteria_types: List[int] = []
    for field in fields:
        objective = _effective_objective(field)
        if objective == "maximize":
            criteria_types.append(1)
        elif objective == "minimize":
            criteria_types.append(-1)
        else:
            raise RuntimeError(f"Objetivo MCDM no soportado para '{field}': {objective}")

    library_matrix: List[List[float]] = []
    for row in matrix:
        if len(row) != column_count:
            raise RuntimeError("Todas las filas TOPSIS deben tener la misma longitud.")
        library_row: List[float] = []
        for value in row:
            if value is None:
                library_row.append(_null_unit_score())
            else:
                library_row.append(float(value))
        library_matrix.append(library_row)

    return topsis_scores_with_library(library_matrix, weights, criteria_types)


def compute_mcdm_blocks(
    numeric_values_blocks: Sequence[Mapping[str, Any]],
    ignored_fields_per_row: Optional[Sequence[Mapping[str, str]]] = None,
) -> List[Dict[str, Any]]:
    if not numeric_values_blocks:
        return []

    extracted_rows: List[List[Optional[float]]] = []
    shared_fields: List[str] | None = None
    versions: List[int] = []
    ignored_field_lists: List[List[str]] = []

    for index, numeric_values in enumerate(numeric_values_blocks):
        fields, row, version = _extract_numeric_vector(numeric_values)
        if shared_fields is None:
            shared_fields = fields
        elif fields != shared_fields:
            raise RuntimeError("Todos los vectores MCDM deben compartir exactamente el mismo orden de campos.")
        ignored_fields = ignored_fields_per_row[index] if ignored_fields_per_row and index < len(ignored_fields_per_row) else {}
        extracted_rows.append(_apply_runtime_ignored_fields(fields, row, ignored_fields))
        versions.append(version)
        ignored_field_lists.append(sorted(str(field) for field in ignored_fields.keys()))

    assert shared_fields is not None
    matrix, method, used_reference_anchors = _with_reference_anchors(extracted_rows, shared_fields)
    scores = _topsis_scores(matrix, shared_fields)[: len(extracted_rows)]
    timestamp = _now_iso()
    uses_desaturation = _desaturation_enabled() and any(
        field in MCDM_FIELD_DESATURATION for field in shared_fields
    )
    uses_piecewise = any(field in MCDM_FIELD_PIECEWISE for field in shared_fields)
    uses_curves = any(field in MCDM_FIELD_CURVES for field in shared_fields)

    blocks: List[Dict[str, Any]] = []
    for index, score in enumerate(scores):
        blocks.append(
            {
                "checked": True,
                "timestamp": timestamp,
                "score": score,
                "is_mock": False,
                "method": f"{method}_scaled" if (uses_desaturation or uses_piecewise or uses_curves) else method,
                "vector_version": versions[index],
                "value_count": len(shared_fields),
                "comparison_count": len(extracted_rows),
                "uses_reference_anchors": used_reference_anchors,
                "uses_desaturation": uses_desaturation,
                "uses_piecewise_scaling": uses_piecewise,
                "uses_curve_scaling": uses_curves,
                "ignored_fields": ignored_field_lists[index],
            }
        )
    return blocks


def compute_mcdm_blocks_for_emails(emails: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    numeric_values_blocks = [_ensure_numeric_values_block(email) for email in emails]
    ignored_fields_per_row = [_runtime_ignored_vector_fields(email) for email in emails]
    return compute_mcdm_blocks(numeric_values_blocks, ignored_fields_per_row=ignored_fields_per_row)


def compute_mcdm_block_for_email_with_hardcoded_references(email: Dict[str, Any]) -> Dict[str, Any]:
    target_numeric_values = _ensure_numeric_values_block(email)
    reference_blocks = [
        _hardcoded_reference_numeric_values_block(INDIVIDUAL_REFERENCE_WORST_VECTOR),
        _hardcoded_reference_numeric_values_block(INDIVIDUAL_REFERENCE_BEST_VECTOR),
    ]
    blocks = compute_mcdm_blocks(
        [target_numeric_values, *reference_blocks],
        ignored_fields_per_row=[_runtime_ignored_vector_fields(email), {}, {}],
    )
    target_block = dict(blocks[0])
    method = str(target_block.get("method") or "topsis")
    if method.startswith("topsis_scaled"):
        method = "topsis_with_phishpot1050_extreme_references_scaled"
    elif method.startswith("topsis"):
        method = "topsis_with_phishpot1050_extreme_references"
    target_block.update(
        {
            "method": method,
            "comparison_count": 1,
            "reference_count": 2,
            "internal_matrix_count": 3,
            "uses_reference_anchors": True,
            "reference_source": INDIVIDUAL_REFERENCE_SOURCE,
            "reference_email_ids": {
                "best": INDIVIDUAL_REFERENCE_BEST_EMAIL_ID,
                "worst": INDIVIDUAL_REFERENCE_WORST_EMAIL_ID,
            },
            "reference_original_mcdm_scores": {
                "best": INDIVIDUAL_REFERENCE_BEST_MCDM_SCORE,
                "worst": INDIVIDUAL_REFERENCE_WORST_MCDM_SCORE,
            },
        }
    )
    return target_block


def enrich_mcdm_score_in_data(email: Dict[str, Any], force: bool = False) -> bool:
    existing = email.get("mcdm")
    if isinstance(existing, dict) and existing.get("checked") and not force:
        return False

    new_block = compute_mcdm_block_for_email_with_hardcoded_references(email)
    if existing == new_block:
        return False
    email["mcdm"] = new_block
    return True


__all__ = [
    "compute_mcdm_blocks",
    "compute_mcdm_block_for_email_with_hardcoded_references",
    "compute_mcdm_blocks_for_emails",
    "enrich_mcdm_score_in_data",
    "field_unit_score",
    "field_unit_score_with_context",
]

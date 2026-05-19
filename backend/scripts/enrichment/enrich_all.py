from __future__ import annotations

"""
Orquesta la ejecucion de subcriterios activos, normaliza selecciones solicitadas por API y recalcula valores numericos y MCDM.
"""

import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from .attachment_types_helper import enrich_attachment_types_in_data
from .body_keywords_helper import enrich_body_keywords_in_data
from .body_obfuscation_helper import (
    enrich_body_obfuscation_base64_in_data,
    enrich_body_obfuscation_unicode_in_data,
)
from .dmarc_helper import enrich_dmarc_in_data
from .dkim_helper import enrich_dkim_in_data
from .domain_age_helper import enrich_domain_age_in_data
from .domain_reputation_helper import enrich_domain_reputation_in_data
from .domain_vs_ip_country_helper import enrich_domain_vs_ip_country_in_data
from .external_api_errors import FatalExternalApiError, detect_fatal_neutrino_error
from .from_return_path_subdomain_match_helper import (
    enrich_from_return_path_subdomain_match_in_data,
)
from .html_beacon_count_helper import enrich_html_beacon_count_in_data
from .html_tag_count_helper import enrich_html_tag_count_in_data
from .ip_reputation_helper import enrich_ip_reputation_in_data
from .link_captcha_helper import enrich_link_captcha_in_data
from .link_count_helper import enrich_link_count_in_data
from .link_domain_age_helper import enrich_link_domain_age_in_data
from .link_domain_country_vs_modal_helper import (
    enrich_link_domain_country_vs_modal_in_data,
)
from .link_domain_match_modal_helper import enrich_link_domain_match_modal_in_data
from .link_domain_reputation_helper import enrich_link_domain_reputation_in_data
from .link_numeric_subdomain_helper import enrich_link_numeric_subdomain_in_data
from .link_subdomain_count_helper import enrich_link_subdomain_count_in_data
from .mcdm_score_helper import enrich_mcdm_score_in_data
from .numeric_values_helper import enrich_numeric_values_in_data
from .php_mailer_or_similar_header_indicator_helper import (
    enrich_php_mailer_or_similar_header_indicator_in_data,
)
from .received_hops_count_helper import enrich_received_hops_count_in_data
from .received_time_delta_helper import enrich_received_time_delta_in_data
from .routing_data_helper import (
    enrich_routing_country_mismatch_in_data,
    enrich_routing_domain_age_in_data,
    enrich_routing_domain_reputation_in_data,
    enrich_routing_ip_reputation_in_data,
    enrich_routing_subdomain_count_in_data,
)
from .sender_numeric_subdomain_helper import enrich_sender_numeric_subdomain_in_data
from .sender_subdomain_count_helper import enrich_sender_subdomain_count_in_data
from .spf_helper import enrich_spf_in_data
from .vector_schema import ACTIVE_SUBCRITERIA_KEYS
from ..utils.enrichment_utils import normalize_criterion_key


EnrichmentFn = Callable[[Dict[str, Any], bool], bool]
ProgressCallback = Callable[[Dict[str, Any], str, int, int], None]

API_DEPENDENT_SUBCRITERIA = {
    "ip_reputation",
    "domain_reputation",
    "domain_vs_ip_country",
    "domain_age",
    "routing_domain_reputation",
    "routing_ip_reputation",
    "routing_domain_age",
    "routing_country_mismatch",
    "routing_subdomain_count",
    "link_domain_reputation",
    "link_domain_country_vs_modal",
    "link_domain_age",
}

SUBCRITERION_REGISTRY: Dict[str, EnrichmentFn] = {
    "spf": enrich_spf_in_data,
    "dkim": enrich_dkim_in_data,
    "dmarc": enrich_dmarc_in_data,
    "php_mailer_or_similar_header_indicator": enrich_php_mailer_or_similar_header_indicator_in_data,
    "ip_reputation": enrich_ip_reputation_in_data,
    "domain_reputation": enrich_domain_reputation_in_data,
    "domain_vs_ip_country": enrich_domain_vs_ip_country_in_data,
    "domain_age": enrich_domain_age_in_data,
    "sender_subdomain_count": enrich_sender_subdomain_count_in_data,
    "sender_numeric_subdomain": enrich_sender_numeric_subdomain_in_data,
    "from_return_path_subdomain_match": enrich_from_return_path_subdomain_match_in_data,
    "received_hops_count": enrich_received_hops_count_in_data,
    "routing_domain_reputation": enrich_routing_domain_reputation_in_data,
    "routing_ip_reputation": enrich_routing_ip_reputation_in_data,
    "routing_domain_age": enrich_routing_domain_age_in_data,
    "routing_country_mismatch": enrich_routing_country_mismatch_in_data,
    "routing_subdomain_count": enrich_routing_subdomain_count_in_data,
    "received_time_delta": enrich_received_time_delta_in_data,
    "body_keywords": enrich_body_keywords_in_data,
    "body_obfuscation_base64": enrich_body_obfuscation_base64_in_data,
    "body_obfuscation_unicode": enrich_body_obfuscation_unicode_in_data,
    "link_count": enrich_link_count_in_data,
    "link_domain_reputation": enrich_link_domain_reputation_in_data,
    "link_domain_country_vs_modal": enrich_link_domain_country_vs_modal_in_data,
    "link_domain_age": enrich_link_domain_age_in_data,
    "link_subdomain_count": enrich_link_subdomain_count_in_data,
    "link_numeric_subdomain": enrich_link_numeric_subdomain_in_data,
    "link_domain_match_modal": enrich_link_domain_match_modal_in_data,
    "attachment_types": enrich_attachment_types_in_data,
    "html_tag_count": enrich_html_tag_count_in_data,
    "link_captcha": enrich_link_captcha_in_data,
    "html_beacon_count": enrich_html_beacon_count_in_data,
}

SUBCRITERION_ALIASES: Dict[str, str | List[str]] = {
    "criterio1.spf": "spf",
    "criterio1.dkim": "dkim",
    "criterio1.dmarc": "dmarc",
    "criterio1.ip_reputation": "ip_reputation",
    "criterio1.domain_reputation": "domain_reputation",
    "criterio1.pais_dominio_vs_ip": "domain_vs_ip_country",
    "criterio1.domain_vs_ip_country": "domain_vs_ip_country",
    "criterio1.domain_age": "domain_age",
    "criterio1.php_mailer_or_similar_header_indicator": "php_mailer_or_similar_header_indicator",
    "criterio1.from_return_path_subdomain_match": "from_return_path_subdomain_match",
    "criterio1.received_hops_count": "received_hops_count",
    "routing_data": [
        "routing_domain_reputation",
        "routing_ip_reputation",
        "routing_domain_age",
        "routing_country_mismatch",
        "routing_subdomain_count",
    ],
    "criterio1.routing_data": [
        "routing_domain_reputation",
        "routing_ip_reputation",
        "routing_domain_age",
        "routing_country_mismatch",
        "routing_subdomain_count",
    ],
    "criterio1.routing_domain_reputation": "routing_domain_reputation",
    "criterio1.routing_ip_reputation": "routing_ip_reputation",
    "criterio1.routing_domain_age": "routing_domain_age",
    "criterio1.routing_country_mismatch": "routing_country_mismatch",
    "criterio1.routing_subdomain_count": "routing_subdomain_count",
    "criterio1.received_time_delta": "received_time_delta",
    "criterio1.sender_subdomain_count": "sender_subdomain_count",
    "criterio1.sender_numeric_subdomain": "sender_numeric_subdomain",
    "criterio2.attachment_types": "attachment_types",
    "criterio2.body_keywords": "body_keywords",
    "criterio2.body_obfuscation_base64": "body_obfuscation_base64",
    "criterio2.body_obfuscation_unicode": "body_obfuscation_unicode",
    "criterio2.link_count": "link_count",
    "criterio2.html_tag_count": "html_tag_count",
    "criterio2.html_beacon_count": "html_beacon_count",
    "criterio2.link_subdomain_count": "link_subdomain_count",
    "criterio2.link_numeric_subdomain": "link_numeric_subdomain",
    "criterio2.link_domain_reputation": "link_domain_reputation",
    "criterio2.link_domain_match_modal": "link_domain_match_modal",
    "criterio2.link_domain_country_vs_modal": "link_domain_country_vs_modal",
    "criterio2.link_domain_age": "link_domain_age",
    "criterio2.link_captcha": "link_captcha",
}


def list_available_subcriteria() -> List[str]:
    return [key for key in SUBCRITERION_REGISTRY.keys() if key in ACTIVE_SUBCRITERIA_KEYS]


def normalize_selected_subcriteria(selected_subcriteria: Optional[List[str]]) -> List[str]:
    if not selected_subcriteria:
        return list_available_subcriteria()

    normalized: List[str] = []
    seen = set()
    for raw_key in selected_subcriteria:
        if not isinstance(raw_key, str):
            continue
        key = raw_key.strip()
        if not key:
            continue
        candidate = SUBCRITERION_ALIASES.get(key)
        if candidate is None:
            candidate = SUBCRITERION_ALIASES.get(normalize_criterion_key(key))
        candidates = candidate if isinstance(candidate, list) else [candidate] if isinstance(candidate, str) else [normalize_criterion_key(key)]
        for resolved in candidates:
            if resolved not in SUBCRITERION_REGISTRY:
                raise ValueError(f"Subcriterio no soportado: {raw_key}")
            if resolved not in ACTIVE_SUBCRITERIA_KEYS:
                continue
            if resolved in seen:
                continue
            seen.add(resolved)
            normalized.append(resolved)
    return normalized


def enrich_email_in_data(
    data: Dict[str, Any],
    selected_subcriteria: Optional[List[str]] = None,
    force: bool = False,
    include_numeric_values: bool = True,
    on_subcriterion_completed: Optional[ProgressCallback] = None,
) -> Dict[str, Any]:
    selected = normalize_selected_subcriteria(selected_subcriteria)
    changed_subcriteria: List[str] = []
    total = len(selected)

    for index, criterion_key in enumerate(selected, start=1):
        enrich_fn = SUBCRITERION_REGISTRY[criterion_key]
        if enrich_fn(data, force=force):
            changed_subcriteria.append(criterion_key)
        if criterion_key in API_DEPENDENT_SUBCRITERIA:
            enrichment = data.get("enrichment") or {}
            result_block = enrichment.get(criterion_key) if isinstance(enrichment, dict) else None
            fatal_error = detect_fatal_neutrino_error(result_block)
            if fatal_error:
                raise FatalExternalApiError(
                    provider=fatal_error["provider"],
                    criterion_key=criterion_key,
                    error_code=fatal_error["error_code"],
                    error_message=fatal_error.get("error_message"),
                )
        if on_subcriterion_completed is not None:
            on_subcriterion_completed(data, criterion_key, index, total)

    numeric_values_updated = False
    if include_numeric_values:
        numeric_values_updated = enrich_numeric_values_in_data(data, force=force)
    mcdm_updated = enrich_mcdm_score_in_data(data, force=force)

    return {
        "selected_subcriteria": selected,
        "changed_subcriteria": changed_subcriteria,
        "numeric_values_updated": numeric_values_updated,
        "mcdm_updated": mcdm_updated,
    }

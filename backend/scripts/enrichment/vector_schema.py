from __future__ import annotations

"""
Define el contrato del vector MCDM: subcriterios, pesos, objetivos, transformaciones y validaciones de consistencia.
"""

from typing import Any, Dict, List


LINK_COUNT_ZERO_SCORE_THRESHOLD = 20.0

MCDM_SUBCRITERIA_WEIGHTS: List[Dict[str, Any]] = [
    {"key": "spf", "name": "SPF (Sender Policy Framework)", "weight": 12.5},
    {"key": "dkim", "name": "DKIM (Domain Keys Indentified Mail)", "weight": 12.5},
    {"key": "dmarc", "name": "DMARC (Domain based Message Authentication...)", "weight": 7.5},
    {"key": "php_mailer_or_similar_header_indicator", "name": "PHPMailer Score", "weight": 0.0},
    {"key": "ip_reputation", "name": "Reputacion de la IP del remitente", "weight": 0.0},
    {"key": "domain_reputation", "name": "Reputacion del dominio del remitente", "weight": 0.0},
    {"key": "domain_vs_ip_country", "name": "Pais del dominio vs Pais de la IP", "weight": 0.0},
    {"key": "domain_age", "name": "Edad del dominio del remitente", "weight": 0.0},
    {"key": "sender_subdomain_count", "name": "Numero de subdominios del dominio modal", "weight": 0.0},
    {"key": "sender_numeric_subdomain", "name": "Numero de subdominios numericos dominio modal", "weight": 0.0},
    {"key": "from_return_path_subdomain_match", "name": "From vs Return Path", "weight": 2.5},
    {"key": "received_hops_count", "name": "Numero saltos received", "weight": 12.5},
    {"key": "routing_domain_reputation", "name": "Reputacion dominio routing", "weight": 0.0},
    {"key": "routing_ip_reputation", "name": "Reputacion IP routing", "weight": 2.5},
    {"key": "routing_domain_age", "name": "Edad del dominio de routing", "weight": 0.0},
    {"key": "routing_country_mismatch", "name": "Disparidad Pais de routing", "weight": 0.0},
    {"key": "routing_subdomain_count", "name": "Numero de subdominios del routing", "weight": 2.5},
    {"key": "received_time_delta", "name": "Tiempo delta entre received", "weight": 0.0},
    {"key": "body_keywords", "name": "Frases comunes y Palabras Clave", "weight": 0.0},
    {"key": "body_obfuscation_base64", "name": "Tecnicas de ofuscacion base64", "weight": 5.0},
    {"key": "body_obfuscation_unicode", "name": "Tecnicas de ofuscacion Unicode", "weight": 0.0},
    {"key": "link_count", "name": "Numero de enlaces del cuerpo", "weight": 10.0},
    {"key": "link_domain_reputation", "name": "Calidad/Reputacion de los enlaces", "weight": 2.5},
    {"key": "link_domain_country_vs_modal", "name": "Disparidad Pais enlace vs dominio modal", "weight": 0.0},
    {"key": "link_domain_age", "name": "Edad del dominio del enlace", "weight": 1.0},
    {"key": "link_subdomain_count", "name": "Numero de subdominios de los enlaces", "weight": 0.0},
    {"key": "link_numeric_subdomain", "name": "Numero de subdominios numericos dominio modal", "weight": 0.0},
    {"key": "link_domain_match_modal", "name": "Disparidad dominio enlace vs dominio modal", "weight": 5.0},
    {"key": "attachment_types", "name": "Numero adjuntos sospechosos", "weight": 0.0},
    {"key": "html_tag_count", "name": "Numero etiquetas html", "weight": 3.0},
    {"key": "link_captcha", "name": "Captcha presente en enlaces", "weight": 0.0},
    {"key": "html_beacon_count", "name": "Beacons anadidos", "weight": 1.5},
]


MCDM_SUBCRITERIA_DESATURATION: List[Dict[str, Any]] = []

MCDM_SUBCRITERIA_PIECEWISE: List[Dict[str, Any]] = [
    {
        "key": "spf",
        "method": "piecewise_linear",
        "anchors": [
            {"value": 0.0, "score": 0.0},
            {"value": 1.0, "score": 1.0},
        ],
    },
    {
        "key": "dkim",
        "method": "piecewise_linear",
        "anchors": [
            {"value": 0.0, "score": 0.0},
            {"value": 1.0, "score": 1.0},
        ],
    },
    {
        "key": "dmarc",
        "method": "piecewise_linear",
        "anchors": [
            {"value": 0.0, "score": 0.0},
            {"value": 1.0, "score": 1.0},
        ],
    },
    {
        "key": "php_mailer_or_similar_header_indicator",
        "method": "piecewise_linear",
        "anchors": [
            {"value": 0.0, "score": 0.0},
            {"value": 1.0, "score": 1.0},
        ],
    },
    {
        "key": "ip_reputation",
        "method": "piecewise_linear",
        "anchors": [
            {"value": 0.0, "score": 0.0},
            {"value": 1.0, "score": 1.0},
        ],
    },
    {
        "key": "domain_reputation",
        "method": "piecewise_linear",
        "anchors": [
            {"value": 0.0, "score": 0.0},
            {"value": 1.0, "score": 1.0},
        ],
    },
    {
        "key": "domain_vs_ip_country",
        "method": "piecewise_linear",
        "anchors": [
            {"value": 0.0, "score": 0.0},
            {"value": 0.5, "score": 0.5},
            {"value": 1.0, "score": 1.0},
        ],
    },
    {
        "key": "domain_age",
        "method": "piecewise_linear",
        "anchors": [
            {"value": 0.0, "score": 1.0},
            {"value": 30.0, "score": 1.0},
            {"value": 90.0, "score": 0.9},
            {"value": 180.0, "score": 0.8},
            {"value": 365.0, "score": 0.65},
            {"value": 730.0, "score": 0.45},
            {"value": 1095.0, "score": 0.3},
            {"value": 1825.0, "score": 0.15},
            {"value": 3650.0, "score": 0.0},
        ],
    },
    {
        "key": "sender_subdomain_count",
        "method": "piecewise_linear",
        "anchors": [
            {"value": 0.0, "score": 0.0},
            {"value": 1.0, "score": 0.2},
            {"value": 2.0, "score": 0.5},
            {"value": 3.0, "score": 0.8},
            {"value": 4.0, "score": 1.0},
        ],
    },
    {
        "key": "sender_numeric_subdomain",
        "method": "piecewise_linear",
        "anchors": [
            {"value": 0.0, "score": 0.0},
            {"value": 1.0, "score": 0.75},
            {"value": 2.0, "score": 1.0},
        ],
    },
    {
        "key": "from_return_path_subdomain_match",
        "method": "piecewise_linear",
        "anchors": [
            {"value": 0.0, "score": 0.0},
            {"value": 1.0, "score": 1.0},
        ],
    },
    {
        "key": "received_hops_count",
        "method": "piecewise_linear",
        "anchors": [
            {"value": 2.0, "score": 0.0},
            {"value": 3.0, "score": 0.25},
            {"value": 4.0, "score": 0.5},
            {"value": 5.0, "score": 0.75},
            {"value": 6.0, "score": 1.0},
        ],
    },
    {
        "key": "routing_domain_reputation",
        "method": "piecewise_linear",
        "anchors": [
            {"value": 0.0, "score": 0.0},
            {"value": 1.0, "score": 1.0},
        ],
    },
    {
        "key": "routing_ip_reputation",
        "method": "piecewise_linear",
        "anchors": [
            {"value": 0.0, "score": 0.0},
            {"value": 1.0, "score": 1.0},
        ],
    },
    {
        "key": "routing_domain_age",
        "method": "piecewise_linear",
        "anchors": [
            {"value": 0.0, "score": 1.0},
            {"value": 30.0, "score": 1.0},
            {"value": 90.0, "score": 0.9},
            {"value": 180.0, "score": 0.8},
            {"value": 365.0, "score": 0.65},
            {"value": 730.0, "score": 0.45},
            {"value": 1095.0, "score": 0.3},
            {"value": 1825.0, "score": 0.15},
            {"value": 3650.0, "score": 0.0},
        ],
    },
    {
        "key": "routing_country_mismatch",
        "method": "piecewise_linear",
        "anchors": [
            {"value": 0.0, "score": 0.0},
            {"value": 1.0, "score": 1.0},
        ],
    },
    {
        "key": "routing_subdomain_count",
        "method": "piecewise_linear",
        "anchors": [
            {"value": 2.0, "score": 0.0},
            {"value": 3.0, "score": 0.75},
            {"value": 4.0, "score": 1.0},
        ],
    },
    {
        "key": "received_time_delta",
        "method": "piecewise_linear",
        "anchors": [
            {"value": 0.0, "score": 0.0},
            {"value": 5.0, "score": 0.1},
            {"value": 30.0, "score": 0.25},
            {"value": 120.0, "score": 0.45},
            {"value": 600.0, "score": 0.65},
            {"value": 1800.0, "score": 0.85},
            {"value": 3600.0, "score": 1.0},
        ],
    },
    {
        "key": "body_keywords",
        "method": "piecewise_linear",
        "anchors": [
            {"value": 1.0, "score": 0.0},
            {"value": 2.0, "score": 0.33},
            {"value": 3.0, "score": 0.5},
            {"value": 4.0, "score": 0.75},
            {"value": 5.0, "score": 1.0},
        ],
    },
    {
        "key": "body_obfuscation_base64",
        "method": "piecewise_linear",
        "anchors": [
            {"value": 0.0, "score": 0.0},
            {"value": 1.0, "score": 1.0},
        ],
    },
    {
        "key": "body_obfuscation_unicode",
        "method": "piecewise_linear",
        "anchors": [
            {"value": 0.0, "score": 0.0},
            {"value": 1.0, "score": 0.35},
            {"value": 3.0, "score": 0.6},
            {"value": 6.0, "score": 0.8},
            {"value": 10.0, "score": 0.9},
            {"value": 20.0, "score": 1.0},
        ],
    },
    {
        "key": "link_count",
        "method": "piecewise_linear",
        "anchors": [
            {"value": 0.0, "score": 0.0},
            {"value": 1.0, "score": 1.0},
            {"value": 5.0, "score": 1.0},
            {"value": 10.0, "score": 0.50},
            {"value": 15.0, "score": 0.25},
            {"value": LINK_COUNT_ZERO_SCORE_THRESHOLD, "score": 0.0},
        ],
    },
    {
        "key": "link_domain_reputation",
        "method": "piecewise_linear",
        "anchors": [
            {"value": 0.0, "score": 0.0},
            {"value": 1.0, "score": 1.0},
        ],
    },
    {
        "key": "link_domain_country_vs_modal",
        "method": "piecewise_linear",
        "anchors": [
            {"value": 0.0, "score": 0.0},
            {"value": 1.0, "score": 1.0},
        ],
    },
    {
        "key": "link_domain_age",
        "method": "piecewise_linear",
        "anchors": [
            {"value": 0.0, "score": 1.0},
            {"value": 1121.0, "score": 0.85},
            {"value": 2657.0, "score": 0.55},
            {"value": 3841.0, "score": 0.35},
            {"value": 5151.6, "score": 0.2},
            {"value": 6986.0, "score": 0.1},
            {"value": 8543.0, "score": 0.05},
            {"value": 10220.0, "score": 0.0},
        ],
    },
    {
        "key": "link_subdomain_count",
        "method": "piecewise_linear",
        "anchors": [
            {"value": 0.0, "score": 1.0},
            {"value": 1.0, "score": 0.8},
            {"value": 2.0, "score": 0.45},
            {"value": 3.0, "score": 0.15},
            {"value": 4.0, "score": 0.0},
        ],
    },
    {
        "key": "link_numeric_subdomain",
        "method": "piecewise_linear",
        "anchors": [
            {"value": 0.0, "score": 0.0},
            {"value": 1.0, "score": 0.75},
            {"value": 2.0, "score": 1.0},
        ],
    },
    {
        "key": "link_domain_match_modal",
        "method": "piecewise_linear",
        "anchors": [
            {"value": 0.0, "score": 0.0},
            {"value": 1.0, "score": 1.0},
        ],
    },
    {
        "key": "attachment_types",
        "method": "piecewise_linear",
        "anchors": [
            {"value": 0.0, "score": 0.0},
            {"value": 1.0, "score": 1.0},
        ],
    },
    {
        "key": "html_tag_count",
        "method": "piecewise_linear",
        "anchors": [
            {"value": 75.0, "score": 1.0},
            {"value": 150.0, "score": 0.5},
            {"value": 200.0, "score": 0.25},
            {"value": 300.0, "score": 0.0},
        ],
    },
    {
        "key": "link_captcha",
        "method": "piecewise_linear",
        "anchors": [
            {"value": 0.0, "score": 0.0},
            {"value": 1.0, "score": 1.0},
        ],
    },
    {
        "key": "html_beacon_count",
        "method": "piecewise_linear",
        "anchors": [
            {"value": 0.0, "score": 1.0},
            {"value": 1.0, "score": 0.5},
            {"value": 2.0, "score": 0.25},
            {"value": 3.0, "score": 0.0},
        ],
    },
]

MCDM_SUBCRITERIA_CURVES: List[Dict[str, Any]] = []

_RAW_MCDM_WEIGHT_BY_SUBCRITERION_KEY = {
    str(item["key"]): float(item["weight"])
    for item in MCDM_SUBCRITERIA_WEIGHTS
}
ACTIVE_SUBCRITERIA_KEYS = {
    key
    for key, weight in _RAW_MCDM_WEIGHT_BY_SUBCRITERION_KEY.items()
    if weight > 0.0
}
_RAW_MCDM_WEIGHT_TOTAL = sum(_RAW_MCDM_WEIGHT_BY_SUBCRITERION_KEY.values())
MCDM_WEIGHT_BY_SUBCRITERION_KEY = {
    key: (weight / _RAW_MCDM_WEIGHT_TOTAL)
    for key, weight in _RAW_MCDM_WEIGHT_BY_SUBCRITERION_KEY.items()
}

MCDM_DESATURATION_BY_SUBCRITERION_KEY = {
    str(item["key"]): {
        "method": str(item["method"]),
        "half_saturation": float(item["half_saturation"]),
    }
    for item in MCDM_SUBCRITERIA_DESATURATION
}

MCDM_PIECEWISE_BY_SUBCRITERION_KEY = {
    str(item["key"]): {
        "method": str(item["method"]),
        "anchors": [
            {
                "value": float(anchor["value"]),
                "score": float(anchor["score"]),
            }
            for anchor in item["anchors"]
        ],
    }
    for item in MCDM_SUBCRITERIA_PIECEWISE
}

MCDM_CURVE_BY_SUBCRITERION_KEY = {
    str(item["key"]): {
        "method": str(item["method"]),
        **({"cap_days": float(item["cap_days"])} if "cap_days" in item else {}),
    }
    for item in MCDM_SUBCRITERIA_CURVES
}


MCDM_FIELD_OBJECTIVES: Dict[str, str] = {
    "c1_spf": "maximize",
    "c1_dkim": "maximize",
    "c1_dmarc": "maximize",
    "c1_php_mailer_score": "maximize",
    "c1_ip_reputation": "maximize",
    "c1_domain_reputation": "maximize",
    "c1_domain_vs_ip_country_score": "maximize",
    "c1_domain_age_days": "minimize",
    "c1_sender_subdomain_count": "maximize",
    "c1_sender_numeric_subdomain_count": "maximize",
    "c1_from_return_path_mismatch": "maximize",
    "c1_received_hops_count": "maximize",
    "c1_routing_domain_reputation": "maximize",
    "c1_routing_ip_reputation": "maximize",
    "c1_routing_domain_age_days": "minimize",
    "c1_routing_country_mismatch": "maximize",
    "c1_routing_subdomain_count": "maximize",
    "c1_received_time_delta_seconds": "maximize",
    "c2_body_keywords_count": "maximize",
    "c2_obfuscation_base64_present": "maximize",
    "c2_obfuscation_unicode_count": "maximize",
    "c2_link_count": "maximize",
    "c2_link_domain_reputation": "maximize",
    "c2_link_domain_country_vs_modal_mismatch": "maximize",
    "c2_link_domain_age_days": "minimize",
    "c2_link_subdomain_count": "minimize",
    "c2_link_numeric_subdomain_count": "maximize",
    "c2_link_domain_match_modal_mismatch": "maximize",
    "c2_attachment_suspicious_count": "maximize",
    "c2_html_tag_count": "minimize",
    "c2_link_captcha_present": "maximize",
    "c2_html_beacon_count": "minimize",
}


def _entry(
    key: str,
    label: str,
    family: str,
    enrichment_column: str,
    vector_field: str,
    value_type: str,
    measurement: str,
    requires_reliable_sender_domain: bool = False,
) -> Dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "family": family,
        "enrichment_column": enrichment_column,
        "vector_field": vector_field,
        "vector_fields": [vector_field],
        "value_type": value_type,
        "mcdm_objective": MCDM_FIELD_OBJECTIVES[vector_field],
        "mcdm_weight": float(MCDM_WEIGHT_BY_SUBCRITERION_KEY[key]),
        "mcdm_desaturation": MCDM_DESATURATION_BY_SUBCRITERION_KEY.get(key),
        "mcdm_piecewise": MCDM_PIECEWISE_BY_SUBCRITERION_KEY.get(key),
        "mcdm_curve": MCDM_CURVE_BY_SUBCRITERION_KEY.get(key),
        "measurement": measurement,
        "requires_reliable_sender_domain": requires_reliable_sender_domain,
    }


SUBCRITERIA_DEFINITIONS: List[Dict[str, Any]] = [
    _entry("spf", "Comprobar SPF", "criterio1", "sub_spf", "c1_spf", "float", "Score de riesgo SPF en [0,1]; mayor significa peor autenticacion SPF."),
    _entry("dkim", "Comprobar DKIM", "criterio1", "sub_dkim", "c1_dkim", "float", "Score de riesgo DKIM en [0,1]; mayor significa peor autenticacion DKIM."),
    _entry("dmarc", "Comprobar DMARC", "criterio1", "sub_dmarc", "c1_dmarc", "float", "Score de riesgo DMARC en [0,1]; mayor significa peor alineacion/politica DMARC."),
    _entry("php_mailer_or_similar_header_indicator", "Detectar indicadores de PHPMailer", "criterio1", "sub_php_mailer_or_similar_header_indicator", "c1_php_mailer_score", "float", "Score de riesgo en [0,1] derivado de indicadores de PHPMailer o herramientas similares."),
    _entry("ip_reputation", "Evaluar reputacion de la IP", "criterio1", "sub_ip_reputation", "c1_ip_reputation", "int", "Flag 0/1 donde 1 indica que la IP aparece en alguna blocklist de Neutrino."),
    _entry("domain_reputation", "Evaluar reputacion del dominio", "criterio1", "sub_domain_reputation", "c1_domain_reputation", "int", "Flag 0/1 donde 1 indica que Neutrino host-reputation lista el dominio en alguna blocklist.", requires_reliable_sender_domain=True),
    _entry("domain_vs_ip_country", "Comparar pais del dominio con la IP", "criterio1", "sub_domain_vs_ip_country", "c1_domain_vs_ip_country_score", "float", "Score en {0, 0.5, 1} donde 0 indica match, 0.5 falta de datos fiables y 1 mismatch entre infraestructura resuelta del dominio e IP.", requires_reliable_sender_domain=True),
    _entry("domain_age", "Calcular antiguedad del dominio", "criterio1", "sub_domain_age", "c1_domain_age_days", "int", "Edad del dominio del remitente en dias calculada desde la fecha de creacion del dominio hasta la fecha del correo.", requires_reliable_sender_domain=True),
    _entry("sender_subdomain_count", "Contar subdominios del remitente", "criterio1", "sub_sender_subdomain_count", "c1_sender_subdomain_count", "int", "Numero de labels de subdominio del remitente, excluyendo sufijo y un www inicial.", requires_reliable_sender_domain=True),
    _entry("sender_numeric_subdomain", "Contar subdominios numericos del remitente", "criterio1", "sub_sender_numeric_subdomain", "c1_sender_numeric_subdomain_count", "int", "Numero de labels numericas en el subdominio del remitente, ignorando solo un www inicial.", requires_reliable_sender_domain=True),
    _entry("from_return_path_subdomain_match", "Comparar From con Return-Path", "criterio1", "sub_from_return_path_subdomain_match", "c1_from_return_path_mismatch", "int", "Flag 0/1 donde 1 indica mismatch entre el dominio base de From y Return-Path."),
    _entry("received_hops_count", "Contar saltos Received", "criterio1", "sub_received_hops_count", "c1_received_hops_count", "int", "Numero de cabeceras Received parseadas como saltos."),
    _entry("routing_domain_reputation", "Routing: reputacion del dominio", "criterio1", "sub_routing_domain_reputation", "c1_routing_domain_reputation", "int", "Peor flag 0/1 de dominio listado en blocklists observado en los saltos Received procesados."),
    _entry("routing_ip_reputation", "Routing: reputacion de la IP", "criterio1", "sub_routing_ip_reputation", "c1_routing_ip_reputation", "int", "Peor flag 0/1 de IP listada observado en los saltos Received procesados."),
    _entry("routing_domain_age", "Routing: antiguedad del dominio", "criterio1", "sub_routing_domain_age", "c1_routing_domain_age_days", "int", "Menor antiguedad observada en routing usando solo la fecha de creacion del dominio de cada hop."),
    _entry("routing_country_mismatch", "Routing: pais dominio vs IP", "criterio1", "sub_routing_country_mismatch", "c1_routing_country_mismatch", "float", "Score en {0, 1} donde 0 indica match y 1 mismatch entre hops comparables; si no hay comparacion valida devuelve null."),
    _entry("routing_subdomain_count", "Routing: subdominios", "criterio1", "sub_routing_subdomain_count", "c1_routing_subdomain_count", "int", "Maximo numero de labels de subdominio observado en routing."),
    _entry("received_time_delta", "Medir delta temporal entre Received", "criterio1", "sub_received_time_delta", "c1_received_time_delta_seconds", "int", "Delta temporal en segundos entre cabeceras Received parseables."),
    _entry("body_keywords", "Detectar keywords en el cuerpo", "criterio2", "sub_body_keywords", "c2_body_keywords_count", "int", "Numero de keywords sospechosas detectadas en el cuerpo."),
    _entry("body_obfuscation_base64", "Detectar ofuscacion base64", "criterio2", "sub_body_obfuscation_base64", "c2_obfuscation_base64_present", "int", "Flag 0/1 donde 1 indica presencia de contenido base64 no adjunto en el cuerpo."),
    _entry("body_obfuscation_unicode", "Detectar ofuscacion unicode", "criterio2", "sub_body_obfuscation_unicode", "c2_obfuscation_unicode_count", "int", "Numero de caracteres unicode sospechosos en el cuerpo."),
    _entry("link_count", "Contar enlaces del cuerpo", "criterio2", "sub_link_count", "c2_link_count", "int", "Numero total de enlaces HTTP/HTTPS clicables detectados tras normalizacion y deduplicacion; si no hay enlaces devuelve null y, si los hay, el score MCDM se asigna por anclas con 0 enlaces como caso excepcional y caida por rangos desde 2 enlaces."),
    _entry("link_domain_reputation", "Evaluar reputacion de dominios enlazados", "criterio2", "sub_link_domain_reputation", "c2_link_domain_reputation", "int", "Peor flag 0/1 de dominio listado en blocklists entre los dominios encontrados en enlaces clicables."),
    _entry("link_domain_country_vs_modal", "Comparar pais del dominio enlazado con el modal", "criterio2", "sub_link_domain_country_vs_modal", "c2_link_domain_country_vs_modal_mismatch", "float", "Score en {0, 1} donde 0 indica match y 1 mismatch entre dominios enlazados comparables y el dominio modal; si no es comparable o faltan datos, devuelve null.", requires_reliable_sender_domain=True),
    _entry("link_domain_age", "Calcular antiguedad de dominios enlazados", "criterio2", "sub_link_domain_age", "c2_link_domain_age_days", "int", "Menor antiguedad en dias entre los dominios enlazados de forma clickable usando solo la fecha de creacion."),
    _entry("link_subdomain_count", "Contar subdominios en enlaces", "criterio2", "sub_link_subdomain_count", "c2_link_subdomain_count", "int", "Maximo numero de labels de subdominio entre los enlaces clicables detectados, ignorando solo un www inicial; este subcriterio se evalua como minimize en MCDM y si no hay enlaces devuelve null."),
    _entry("link_numeric_subdomain", "Contar subdominios numericos en enlaces", "criterio2", "sub_link_numeric_subdomain", "c2_link_numeric_subdomain_count", "int", "Maximo numero de labels numericas en subdominios de enlaces clicables; si no hay enlaces devuelve null."),
    _entry("link_domain_match_modal", "Comparar dominio del enlace con el modal", "criterio2", "sub_link_domain_match_modal", "c2_link_domain_match_modal_mismatch", "int", "Flag 0/1 donde 1 indica mismatch entre el dominio base real del enlace clickable y el dominio base mostrado en modal; si no hay enlaces devuelve null.", requires_reliable_sender_domain=True),
    _entry("attachment_types", "Detectar adjuntos sospechosos", "criterio2", "sub_attachment_types", "c2_attachment_suspicious_count", "int", "Numero de adjuntos con extensiones o tipos considerados sospechosos."),
    _entry("html_tag_count", "Contar tags HTML", "criterio2", "sub_html_tag_count", "c2_html_tag_count", "int", "Numero total de tags HTML presentes en el cuerpo."),
    _entry("link_captcha", "Detectar captcha en enlaces", "criterio2", "sub_link_captcha", "c2_link_captcha_present", "int", "Flag 0/1 donde 1 indica presencia de indicadores de captcha en enlaces clicables; si no hay enlaces devuelve null."),
    _entry("html_beacon_count", "Contar beacons HTML", "criterio2", "sub_html_beacon_count", "c2_html_beacon_count", "int", "Numero de beacons HTML o recursos invisibles de tracking detectados."),
]

SUBCRITERIA_BY_KEY = {item["key"]: item for item in SUBCRITERIA_DEFINITIONS}
VECTOR_FIELD_ORDER = [item["vector_field"] for item in SUBCRITERIA_DEFINITIONS]
VECTOR_FIELD_DEFINITIONS = {item["vector_field"]: item for item in SUBCRITERIA_DEFINITIONS}
RELIABLE_SENDER_DOMAIN_SUBCRITERIA_KEYS = {
    item["key"]
    for item in SUBCRITERIA_DEFINITIONS
    if item.get("requires_reliable_sender_domain") is True
}
RELIABLE_SENDER_DOMAIN_VECTOR_FIELDS = {
    item["vector_field"]
    for item in SUBCRITERIA_DEFINITIONS
    if item.get("requires_reliable_sender_domain") is True
}
MCDM_FIELD_WEIGHTS: Dict[str, float] = {
    item["vector_field"]: MCDM_WEIGHT_BY_SUBCRITERION_KEY[item["key"]]
    for item in SUBCRITERIA_DEFINITIONS
}
MCDM_FIELD_DESATURATION: Dict[str, Dict[str, float | str]] = {
    item["vector_field"]: dict(MCDM_DESATURATION_BY_SUBCRITERION_KEY[item["key"]])
    for item in SUBCRITERIA_DEFINITIONS
    if item["key"] in MCDM_DESATURATION_BY_SUBCRITERION_KEY
}
MCDM_FIELD_PIECEWISE: Dict[str, Dict[str, Any]] = {
    item["vector_field"]: dict(MCDM_PIECEWISE_BY_SUBCRITERION_KEY[item["key"]])
    for item in SUBCRITERIA_DEFINITIONS
    if item["key"] in MCDM_PIECEWISE_BY_SUBCRITERION_KEY
}
MCDM_FIELD_CURVES: Dict[str, Dict[str, str]] = {
    item["vector_field"]: dict(MCDM_CURVE_BY_SUBCRITERION_KEY[item["key"]])
    for item in SUBCRITERIA_DEFINITIONS
    if item["key"] in MCDM_CURVE_BY_SUBCRITERION_KEY
}

missing_weight_keys = [item["key"] for item in SUBCRITERIA_DEFINITIONS if item["key"] not in MCDM_WEIGHT_BY_SUBCRITERION_KEY]
extra_weight_keys = [item["key"] for item in MCDM_SUBCRITERIA_WEIGHTS if item["key"] not in SUBCRITERIA_BY_KEY]
if missing_weight_keys or extra_weight_keys:
    raise RuntimeError(
        "La lista editable de pesos MCDM no coincide con los subcriterios reales. "
        f"Faltan: {missing_weight_keys}. Sobran: {extra_weight_keys}."
    )

weights_total = sum(MCDM_WEIGHT_BY_SUBCRITERION_KEY.values())
if _RAW_MCDM_WEIGHT_TOTAL <= 0.0 or abs(weights_total - 1.0) > 1e-9:
    raise RuntimeError(
        "La matriz de pesos MCDM debe normalizarse a 1 y partir de un total bruto positivo. "
        f"Suma normalizada actual: {weights_total}. Total bruto: {_RAW_MCDM_WEIGHT_TOTAL}."
    )

extra_desaturation_keys = [item["key"] for item in MCDM_SUBCRITERIA_DESATURATION if item["key"] not in SUBCRITERIA_BY_KEY]
if extra_desaturation_keys:
    raise RuntimeError(
        "La lista de desaturacion MCDM contiene subcriterios no soportados. "
        f"Sobran: {extra_desaturation_keys}."
    )

invalid_desaturation_keys = [
    item["key"]
    for item in MCDM_SUBCRITERIA_DESATURATION
    if str(item.get("method")) != "half_saturation"
    or not isinstance(item.get("half_saturation"), (int, float))
    or isinstance(item.get("half_saturation"), bool)
    or float(item.get("half_saturation")) <= 0.0
]
if invalid_desaturation_keys:
    raise RuntimeError(
        "La configuracion de desaturacion MCDM es invalida. "
        f"Subcriterios invalidos: {invalid_desaturation_keys}."
    )

extra_piecewise_keys = [item["key"] for item in MCDM_SUBCRITERIA_PIECEWISE if item["key"] not in SUBCRITERIA_BY_KEY]
if extra_piecewise_keys:
    raise RuntimeError(
        "La lista de piecewise MCDM contiene subcriterios no soportados. "
        f"Sobran: {extra_piecewise_keys}."
    )

missing_piecewise_keys = [item["key"] for item in SUBCRITERIA_DEFINITIONS if item["key"] not in MCDM_PIECEWISE_BY_SUBCRITERION_KEY]
if missing_piecewise_keys:
    raise RuntimeError(
        "Todos los subcriterios MCDM deben tener anclas piecewise definidas. "
        f"Faltan: {missing_piecewise_keys}."
    )

invalid_piecewise_keys: List[str] = []
for item in MCDM_SUBCRITERIA_PIECEWISE:
    if str(item.get("method")) != "piecewise_linear":
        invalid_piecewise_keys.append(str(item.get("key")))
        continue
    key = str(item.get("key"))
    definition = SUBCRITERIA_BY_KEY.get(key)
    if not definition:
        invalid_piecewise_keys.append(key)
        continue
    anchors = item.get("anchors")
    if not isinstance(anchors, list) or len(anchors) < 2:
        invalid_piecewise_keys.append(key)
        continue
    previous_value = None
    for anchor in anchors:
        if not isinstance(anchor, dict):
            invalid_piecewise_keys.append(key)
            break
        value = anchor.get("value")
        score = anchor.get("score")
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or float(value) < 0.0
            or not isinstance(score, (int, float))
            or isinstance(score, bool)
            or not (0.0 <= float(score) <= 1.0)
        ):
            invalid_piecewise_keys.append(key)
            break
        if previous_value is not None and float(value) <= previous_value:
            invalid_piecewise_keys.append(key)
            break
        previous_value = float(value)

if invalid_piecewise_keys:
    raise RuntimeError(
        "La configuracion piecewise MCDM es invalida. "
        f"Subcriterios invalidos: {sorted(set(invalid_piecewise_keys))}."
    )

extra_curve_keys = [item["key"] for item in MCDM_SUBCRITERIA_CURVES if item["key"] not in SUBCRITERIA_BY_KEY]
if extra_curve_keys:
    raise RuntimeError(
        "La lista de curvas MCDM contiene subcriterios no soportados. "
        f"Sobran: {extra_curve_keys}."
    )

invalid_curve_keys = []
for item in MCDM_SUBCRITERIA_CURVES:
    method = str(item.get("method"))
    if method in {"peak_one_inverse", "peak_one_inverse_sqrt"}:
        continue
    if method in {"log_scale_cap", "sqrt_scale_cap"}:
        cap_days = item.get("cap_days")
        if (
            not isinstance(cap_days, (int, float))
            or isinstance(cap_days, bool)
            or float(cap_days) <= 0.0
        ):
            invalid_curve_keys.append(item["key"])
        continue
    invalid_curve_keys.append(item["key"])
if invalid_curve_keys:
    raise RuntimeError(
        "La configuracion de curvas MCDM es invalida. "
        f"Subcriterios invalidos: {invalid_curve_keys}."
    )

missing_weight_fields = [field for field in VECTOR_FIELD_ORDER if field not in MCDM_FIELD_WEIGHTS]
extra_weight_fields = [field for field in MCDM_FIELD_WEIGHTS if field not in VECTOR_FIELD_DEFINITIONS]
if missing_weight_fields or extra_weight_fields:
    raise RuntimeError(
        "La matriz de pesos MCDM no coincide con el vector. "
        f"Faltan: {missing_weight_fields}. Sobran: {extra_weight_fields}."
    )

missing_objective_fields = [field for field in VECTOR_FIELD_ORDER if field not in MCDM_FIELD_OBJECTIVES]
extra_objective_fields = [field for field in MCDM_FIELD_OBJECTIVES if field not in VECTOR_FIELD_DEFINITIONS]
if missing_objective_fields or extra_objective_fields:
    raise RuntimeError(
        "La matriz de objetivos MCDM no coincide con el vector. "
        f"Faltan: {missing_objective_fields}. Sobran: {extra_objective_fields}."
    )

invalid_objective_fields = [
    field for field, objective in MCDM_FIELD_OBJECTIVES.items() if objective not in {"maximize", "minimize"}
]
if invalid_objective_fields:
    raise RuntimeError(
        "Los objetivos MCDM deben ser 'maximize' o 'minimize'. "
        f"Campos invalidos: {invalid_objective_fields}."
    )


__all__ = [
    "MCDM_SUBCRITERIA_WEIGHTS",
    "LINK_COUNT_ZERO_SCORE_THRESHOLD",
    "MCDM_SUBCRITERIA_DESATURATION",
    "MCDM_SUBCRITERIA_PIECEWISE",
    "MCDM_SUBCRITERIA_CURVES",
    "ACTIVE_SUBCRITERIA_KEYS",
    "MCDM_WEIGHT_BY_SUBCRITERION_KEY",
    "MCDM_DESATURATION_BY_SUBCRITERION_KEY",
    "MCDM_PIECEWISE_BY_SUBCRITERION_KEY",
    "MCDM_CURVE_BY_SUBCRITERION_KEY",
    "MCDM_FIELD_WEIGHTS",
    "MCDM_FIELD_DESATURATION",
    "MCDM_FIELD_PIECEWISE",
    "MCDM_FIELD_CURVES",
    "MCDM_FIELD_OBJECTIVES",
    "SUBCRITERIA_DEFINITIONS",
    "SUBCRITERIA_BY_KEY",
    "VECTOR_FIELD_ORDER",
    "VECTOR_FIELD_DEFINITIONS",
    "RELIABLE_SENDER_DOMAIN_SUBCRITERIA_KEYS",
    "RELIABLE_SENDER_DOMAIN_VECTOR_FIELDS",
]

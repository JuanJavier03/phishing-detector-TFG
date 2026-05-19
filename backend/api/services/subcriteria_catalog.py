from __future__ import annotations

"""
Expone el catalogo activo de subcriterios para la API y valida que siga
alineado con el registro real de enriquecimiento y con el esquema del vector.
"""

import json
from typing import Any, Dict, List

from scripts.enrichment.enrich_all import (
    API_DEPENDENT_SUBCRITERIA,
    list_available_subcriteria,
    normalize_selected_subcriteria,
)
from scripts.enrichment.vector_schema import (
    ACTIVE_SUBCRITERIA_KEYS,
    SUBCRITERIA_BY_KEY as BASE_SUBCRITERIA_BY_KEY,
    SUBCRITERIA_DEFINITIONS,
    VECTOR_FIELD_DEFINITIONS,
    VECTOR_FIELD_ORDER,
)


SUBCRITERIA: List[Dict[str, Any]] = [
    {
        **dict(item),
        "uses_api": item["key"] in API_DEPENDENT_SUBCRITERIA,
    }
    for item in SUBCRITERIA_DEFINITIONS
    if item["key"] in ACTIVE_SUBCRITERIA_KEYS
]

SUBCRITERIA_BY_KEY = {item["key"]: item for item in SUBCRITERIA}


def _validate_catalog_consistency() -> None:
    registry_keys = list_available_subcriteria()
    missing_keys = [key for key in registry_keys if key not in SUBCRITERIA_BY_KEY]
    extra_keys = [key for key in SUBCRITERIA_BY_KEY if key not in registry_keys]
    if missing_keys or extra_keys:
        raise RuntimeError(
            "El catalogo de subcriterios no coincide con el registro real. "
            f"Faltan: {missing_keys}. Sobran: {extra_keys}."
        )

    registry_vector_order = [SUBCRITERIA_BY_KEY[key]["vector_field"] for key in registry_keys]
    active_vector_order = [
        field
        for field in VECTOR_FIELD_ORDER
        if BASE_SUBCRITERIA_BY_KEY[VECTOR_FIELD_DEFINITIONS[field]["key"]]["key"] in ACTIVE_SUBCRITERIA_KEYS
    ]
    if registry_vector_order != active_vector_order:
        raise RuntimeError(
            "El orden de subcriterios del registro no coincide con el orden del vector. "
            f"Registro: {registry_vector_order}. Vector activo: {active_vector_order}."
        )

    if set(SUBCRITERIA_BY_KEY) != set(ACTIVE_SUBCRITERIA_KEYS):
        raise RuntimeError("La base de metadatos de subcriterios activos no se ha cargado correctamente.")


_validate_catalog_consistency()


def available_subcriteria() -> List[Dict[str, Any]]:
    ordered_keys = list_available_subcriteria()
    return [SUBCRITERIA_BY_KEY[key] for key in ordered_keys if key in SUBCRITERIA_BY_KEY]


def get_subcriterion_definition(key: str) -> Dict[str, Any]:
    normalized = normalize_selected_subcriteria([key])
    if not normalized:
        raise ValueError(f"Subcriterio no soportado: {key}")
    if len(normalized) != 1:
        raise ValueError(f"Subcriterio no soportado: {key}")
    resolved_key = normalized[0]
    if resolved_key not in SUBCRITERIA_BY_KEY:
        raise ValueError(f"Subcriterio no soportado: {key}")
    return SUBCRITERIA_BY_KEY[resolved_key]


def parse_selected_subcriteria_input(raw: Any) -> List[str]:
    if raw is None:
        return list_available_subcriteria()

    if isinstance(raw, list):
        return normalize_selected_subcriteria([str(item) for item in raw])

    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return list_available_subcriteria()
        if text.startswith("["):
            parsed = json.loads(text)
            if not isinstance(parsed, list):
                raise ValueError("selected_subcriteria debe ser una lista JSON")
            return normalize_selected_subcriteria([str(item) for item in parsed])
        return normalize_selected_subcriteria([part.strip() for part in text.split(",") if part.strip()])

    raise ValueError("Formato de selected_subcriteria no soportado")


__all__ = [
    "SUBCRITERIA",
    "SUBCRITERIA_BY_KEY",
    "VECTOR_FIELD_DEFINITIONS",
    "available_subcriteria",
    "get_subcriterion_definition",
    "parse_selected_subcriteria_input",
]

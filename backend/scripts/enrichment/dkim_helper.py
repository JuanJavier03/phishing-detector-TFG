from __future__ import annotations

"""
Calcula y persiste el subcriterio DKIM usando la puntuacion comun de cabeceras de autenticacion.
"""

from typing import Any, Dict

from utils.auth_header_scoring import build_dkim_result_from_headers
from utils.subcriteria_utils import store_subcriterion_result


def enrich_dkim_in_data(email: Dict[str, Any], force: bool = False) -> bool:
    headers = email.get("headers") or {}
    headers = headers if isinstance(headers, dict) else {}
    result = build_dkim_result_from_headers(headers)
    return store_subcriterion_result(email, result)


__all__ = ["enrich_dkim_in_data"]

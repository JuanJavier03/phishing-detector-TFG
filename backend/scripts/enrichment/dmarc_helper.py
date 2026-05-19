from __future__ import annotations

"""
Calcula y persiste el subcriterio DMARC incluyendo la regla de coherencia con SPF y DKIM.
"""

from typing import Any, Dict

from utils.auth_header_scoring import build_dmarc_result_from_headers
from utils.subcriteria_utils import store_subcriterion_result


def enrich_dmarc_in_data(email: Dict[str, Any], force: bool = False) -> bool:
    headers = email.get("headers") or {}
    headers = headers if isinstance(headers, dict) else {}
    result = build_dmarc_result_from_headers(headers)
    return store_subcriterion_result(email, result)


__all__ = ["enrich_dmarc_in_data"]

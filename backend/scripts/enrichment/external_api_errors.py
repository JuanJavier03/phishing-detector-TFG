from __future__ import annotations

"""
Detecta errores fatales devueltos por proveedores externos para que el pipeline pueda detener jobs de forma controlada.
"""

from typing import Any, Dict, Optional


FATAL_NEUTRINO_ERROR_PREFIXES = (
    "neutrino_missing_credentials",
    "neutrino_api_error:",
    "neutrino_http_",
    "neutrino_request_error:",
    "neutrino_json_error:",
)


class FatalExternalApiError(RuntimeError):
    def __init__(
        self,
        *,
        provider: str,
        criterion_key: str,
        error_code: str,
        error_message: Optional[str] = None,
    ) -> None:
        self.provider = provider
        self.criterion_key = criterion_key
        self.error_code = error_code
        self.error_message = error_message or error_code
        super().__init__(self.error_message)


def _extract_fatal_neutrino_error(value: Any) -> Optional[str]:
    if isinstance(value, str):
        stripped = value.strip()
        if any(stripped.startswith(prefix) for prefix in FATAL_NEUTRINO_ERROR_PREFIXES):
            return stripped
        return None

    if isinstance(value, dict):
        for key in ("error", "error_reason"):
            extracted = _extract_fatal_neutrino_error(value.get(key))
            if extracted:
                return extracted
        for nested in value.values():
            extracted = _extract_fatal_neutrino_error(nested)
            if extracted:
                return extracted
        return None

    if isinstance(value, list):
        for nested in value:
            extracted = _extract_fatal_neutrino_error(nested)
            if extracted:
                return extracted
        return None

    return None


def detect_fatal_neutrino_error(result: Any) -> Optional[Dict[str, str]]:
    error_code = _extract_fatal_neutrino_error(result)
    if not error_code:
        return None
    return {
        "provider": "neutrino",
        "error_code": error_code,
        "error_message": error_code,
    }


__all__ = [
    "FatalExternalApiError",
    "detect_fatal_neutrino_error",
]

from __future__ import annotations

"""
Agrupa utilidades transversales para normalizar claves canonicas de subcriterios y compatibilizar nombres legacy.
"""

import re


CRITERIO_PREFIX_RE = re.compile(r"^criterio\d+\.(.+)$")


def normalize_criterion_key(name: str) -> str:
    if not isinstance(name, str):
        return name
    m = CRITERIO_PREFIX_RE.match(name)
    if m:
        return m.group(1)
    return name


__all__ = ["normalize_criterion_key"]

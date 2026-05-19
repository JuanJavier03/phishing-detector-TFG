from __future__ import annotations

"""
Define las extensiones de recursos tecnicos que se descartan al extraer URLs
analizables del cuerpo HTML. No debe incluir extensiones consideradas
sospechosas por el subcriterio de adjuntos, porque esas deben conservarse para
el analisis de riesgo.
"""

RESOURCE_EXTENSIONS = (
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".bmp",
    ".css",
    ".js",
    ".mjs",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
)


__all__ = ["RESOURCE_EXTENSIONS"]

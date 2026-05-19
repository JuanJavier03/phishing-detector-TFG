from __future__ import annotations

"""
Endpoints ligeros de metadatos consumidos por el frontend para poblar
catalogos, etiquetas y configuraciones derivadas del backend.
"""

from fastapi import APIRouter

from api.services.subcriteria_catalog import available_subcriteria


router = APIRouter()


@router.get("/subcriteria", summary="Catalogo de subcriterios")
def list_subcriteria() -> list[dict]:
    return available_subcriteria()

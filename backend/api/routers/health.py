from __future__ import annotations

"""Endpoint minimo de salud para comprobar que la API responde."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.db.session import get_db


router = APIRouter()


@router.get("/health", summary="Estado basico de la API")
def healthcheck(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("select 1"))
    return {"status": "ok"}

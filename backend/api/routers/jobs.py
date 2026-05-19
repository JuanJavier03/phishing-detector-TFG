from __future__ import annotations

"""
Endpoints de consulta de jobs asincronos para que el frontend pueda seguir
progreso, errores y estado final del procesamiento.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from uuid import UUID

from api.db.models import Job
from api.db.session import get_db
from api.services.application import _serialize_job


router = APIRouter()


@router.get("/{job_id}", summary="Detalle de job")
def get_job(job_id: UUID, db: Session = Depends(get_db)) -> dict:
    job = db.scalar(select(Job).where(Job.id == job_id))
    if job is None:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    return _serialize_job(job) or {}

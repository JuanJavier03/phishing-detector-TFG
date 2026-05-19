from __future__ import annotations

"""
Endpoints de consulta y operaciones sobre lotes de correos, incluidos analisis
agregados, exportacion y mantenimiento de jobs asociados.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from uuid import UUID

from api.db.models import Batch
from api.db.session import get_db
from api.services.application import (
    batch_score_analytics_overview,
    batch_subcriterion_analytics,
    create_analyze_missing_batch_job,
    create_merged_batch,
    create_retry_cancelled_batch_job,
    create_recompute_batch_mcdm_job,
    delete_batch_record,
    export_batch_mcdm_workbook,
    get_batch_query,
    get_batch_summary_query,
    serialize_batch_detail,
    serialize_batch_summary,
)


router = APIRouter()


class MergeBatchesRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    batch_ids: list[UUID] = Field(..., min_length=2)


@router.get("", summary="Listar lotes")
def list_batches(
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[dict]:
    batches = db.scalars(
        get_batch_summary_query()
        .order_by(Batch.created_at.desc(), Batch.id.asc())
        .offset(offset)
        .limit(limit)
    ).unique().all()
    return [serialize_batch_summary(db, batch) for batch in batches]


@router.post("/merge", summary="Crear un lote fusionando lotes existentes")
def merge_batches(payload: MergeBatchesRequest, db: Session = Depends(get_db)) -> dict:
    try:
        return create_merged_batch(
            db=db,
            batch_name=payload.name.strip(),
            batch_ids=payload.batch_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{batch_id}", summary="Detalle de batch")
def get_batch(
    batch_id: UUID,
    email_limit: int = Query(20, ge=1, le=200),
    email_offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> dict:
    batch = db.scalar(get_batch_query().where(Batch.id == batch_id))
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch no encontrado")
    return serialize_batch_detail(
        db,
        batch,
        email_limit=email_limit,
        email_offset=email_offset,
    )


@router.get("/{batch_id}/charts", summary="Analitica agregada para todas las graficas del lote")
def get_batch_charts(batch_id: UUID, db: Session = Depends(get_db)) -> dict:
    batch = db.scalar(get_batch_query().where(Batch.id == batch_id))
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch no encontrado")
    return batch_score_analytics_overview(batch)


@router.get("/{batch_id}/subcriteria/{subcriterion_key}", summary="Analitica de batch por subcriterio")
def get_batch_subcriterion(batch_id: UUID, subcriterion_key: str, db: Session = Depends(get_db)) -> dict:
    batch = db.scalar(get_batch_query().where(Batch.id == batch_id))
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch no encontrado")
    return batch_subcriterion_analytics(batch, subcriterion_key)


@router.get("/{batch_id}/export/mcdm", summary="Exportar Excel MCDM de un lote")
def export_batch_mcdm(batch_id: UUID, db: Session = Depends(get_db)) -> StreamingResponse:
    batch = db.scalar(get_batch_query().where(Batch.id == batch_id))
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch no encontrado")

    try:
        filename, content = export_batch_mcdm_workbook(db, batch)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.post("/{batch_id}/subcriteria/analyze-missing", summary="Analizar todos los subcriterios pendientes de un lote")
def analyze_missing_batch_subcriteria(
    batch_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict:
    batch = db.scalar(get_batch_query().where(Batch.id == batch_id))
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch no encontrado")
    try:
        payload = create_analyze_missing_batch_job(
            db=db,
            background_tasks=background_tasks,
            batch=batch,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"batch_id": str(batch_id), **payload}


@router.post("/{batch_id}/mcdm/recalculate", summary="Recalcular el MCDM global de un lote")
def recalculate_batch_mcdm(
    batch_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict:
    batch = db.scalar(get_batch_query().where(Batch.id == batch_id))
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch no encontrado")
    try:
        payload = create_recompute_batch_mcdm_job(
            db=db,
            background_tasks=background_tasks,
            batch=batch,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"batch_id": str(batch_id), **payload}


@router.post("/{batch_id}/retry-cancelled", summary="Reintentar todos los correos cancelados de un lote")
def retry_cancelled_batch(
    batch_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict:
    batch = db.scalar(get_batch_query().where(Batch.id == batch_id))
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch no encontrado")
    try:
        payload = create_retry_cancelled_batch_job(
            db=db,
            background_tasks=background_tasks,
            batch=batch,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"batch_id": str(batch_id), **payload}


@router.delete("/{batch_id}", summary="Eliminar batch")
def delete_batch(batch_id: UUID, db: Session = Depends(get_db)) -> dict:
    batch = db.scalar(get_batch_query().where(Batch.id == batch_id))
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch no encontrado")
    try:
        return delete_batch_record(db, batch)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

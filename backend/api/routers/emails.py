from __future__ import annotations

"""
Endpoints centrados en un correo individual: detalle, subcriterios, reanalisis
y operaciones de mantenimiento ligadas a su ciclo de vida.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from uuid import UUID

from api.db.models import Email
from api.db.session import get_db
from api.services.application import (
    _display_subcriterion_value,
    _effective_selected_subcriteria,
    _subcriterion_status,
    create_analyze_missing_email_job,
    create_reanalyze_job,
    create_retry_email_job,
    delete_email_record,
    get_email_detail_query,
    get_email_summary_query,
    serialize_email_detail,
    serialize_email_summary,
)
from api.services.subcriteria_catalog import get_subcriterion_definition
from scripts.utils.subcriteria_utils import normalize_subcriterion_result


router = APIRouter()


@router.get("", summary="Listar correos")
def list_emails(
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[dict]:
    emails = db.scalars(
        get_email_summary_query().order_by(Email.created_at.desc()).offset(offset).limit(limit)
    ).unique().all()
    return [serialize_email_summary(db, email) for email in emails]


@router.get("/{email_id}", summary="Detalle de correo")
def get_email(email_id: UUID, db: Session = Depends(get_db)) -> dict:
    email = db.scalar(get_email_detail_query().where(Email.id == email_id))
    if email is None:
        raise HTTPException(status_code=404, detail="Correo no encontrado")
    return serialize_email_detail(db, email)


@router.get("/{email_id}/subcriteria/{subcriterion_key}", summary="Detalle de un subcriterio")
def get_email_subcriterion(email_id: UUID, subcriterion_key: str, db: Session = Depends(get_db)) -> dict:
    email = db.scalar(get_email_detail_query().where(Email.id == email_id))
    if email is None:
        raise HTTPException(status_code=404, detail="Correo no encontrado")
    definition = get_subcriterion_definition(subcriterion_key)
    enrichment = email.enrichment
    result = getattr(enrichment, definition["enrichment_column"]) if enrichment is not None else None
    normalized_result = (
        normalize_subcriterion_result(
            result,
            criterion=f'{definition["family"]}.{definition["key"]}',
        )
        if isinstance(result, dict)
        else None
    )
    selected = set(_effective_selected_subcriteria(email))
    return {
        "email_id": str(email.id),
        "subcriterion": {
            "key": definition["key"],
            "label": definition["label"],
            "family": definition["family"],
            "vector_field": definition["vector_field"],
            "value_type": definition["value_type"],
            "mcdm_objective": definition["mcdm_objective"],
            "mcdm_weight": definition["mcdm_weight"],
            "measurement": definition["measurement"],
        },
        "status": _subcriterion_status(email, definition["key"], normalized_result, selected=selected),
        "value": _display_subcriterion_value(definition["key"], normalized_result),
        "result": normalized_result,
    }


@router.post("/{email_id}/subcriteria/{subcriterion_key}/analyze", summary="Analizar o reanalizar un subcriterio")
def analyze_email_subcriterion(
    email_id: UUID,
    subcriterion_key: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict:
    email = db.scalar(get_email_detail_query().where(Email.id == email_id))
    if email is None:
        raise HTTPException(status_code=404, detail="Correo no encontrado")
    try:
        payload = create_reanalyze_job(
            db=db,
            background_tasks=background_tasks,
            email=email,
            subcriterion_key=subcriterion_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"email_id": str(email_id), **payload}


@router.post("/{email_id}/subcriteria/analyze-missing", summary="Analizar todos los subcriterios pendientes de un correo")
def analyze_missing_email_subcriteria(
    email_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict:
    email = db.scalar(get_email_detail_query().where(Email.id == email_id))
    if email is None:
        raise HTTPException(status_code=404, detail="Correo no encontrado")
    try:
        payload = create_analyze_missing_email_job(
            db=db,
            background_tasks=background_tasks,
            email=email,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"email_id": str(email_id), **payload}


@router.post("/{email_id}/retry", summary="Reintentar un correo cancelado o con error")
def retry_email(
    email_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict:
    email = db.scalar(get_email_detail_query().where(Email.id == email_id))
    if email is None:
        raise HTTPException(status_code=404, detail="Correo no encontrado")
    try:
        payload = create_retry_email_job(
            db=db,
            background_tasks=background_tasks,
            email=email,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"email_id": str(email_id), **payload}


@router.delete("/{email_id}", summary="Eliminar correo")
def delete_email(email_id: UUID, db: Session = Depends(get_db)) -> dict:
    email = db.scalar(get_email_detail_query().where(Email.id == email_id))
    if email is None:
        raise HTTPException(status_code=404, detail="Correo no encontrado")
    try:
        return delete_email_record(db, email)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

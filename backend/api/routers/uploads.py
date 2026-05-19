from __future__ import annotations

"""
Endpoints de subida de correos individuales o en lote.

Validan formato y limites de entrada antes de delegar el parseo y la creacion
de jobs en los servicios de aplicacion.
"""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile as StarletteUploadFile

from api.db.config import get_max_batch_files, get_max_batch_total_bytes, get_max_upload_file_bytes
from api.db.models import Batch
from api.db.session import get_db
from api.services.application import (
    append_batch_upload_files,
    create_batch_upload_from_files,
    create_pending_batch_upload,
    create_single_upload,
    finalize_batch_upload,
    read_uploads,
)
from api.services.subcriteria_catalog import parse_selected_subcriteria_input


router = APIRouter()


def _extract_eml_files(raw_files: list[object], *, max_batch_files: int) -> list[StarletteUploadFile]:
    files = [item for item in raw_files if isinstance(item, StarletteUploadFile)]
    if len(files) != len(raw_files):
        raise HTTPException(status_code=400, detail="Todos los campos files deben ser archivos .eml")
    if not files:
        raise HTTPException(status_code=400, detail="Debes subir al menos un archivo .eml")
    if any(not (item.filename or "").lower().endswith(".eml") for item in files):
        raise HTTPException(status_code=400, detail="Todos los archivos deben ser .eml")
    if len(files) > max_batch_files:
        raise HTTPException(
            status_code=400,
            detail=f"El lote supera el maximo permitido de {max_batch_files} archivos.",
        )
    return files


@router.post("/email", summary="Subir un correo individual")
async def upload_email(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    name: str = Form(...),
    selected_subcriteria: str = Form(""),
    db: Session = Depends(get_db),
) -> dict:
    # La API solo acepta correos RFC822 en `.eml` para mantener el pipeline simple.
    if not (file.filename or "").lower().endswith(".eml"):
        raise HTTPException(status_code=400, detail="El archivo debe ser .eml")
    try:
        normalized_selected = parse_selected_subcriteria_input(selected_subcriteria)
        max_file_bytes = get_max_upload_file_bytes()
        max_batch_total_bytes = get_max_batch_total_bytes()
        uploads = await read_uploads(
            [file],
            max_file_bytes=max_file_bytes,
            max_total_bytes=max_batch_total_bytes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    payload = create_single_upload(
        db=db,
        background_tasks=background_tasks,
        email_name=name.strip() or (file.filename or "email"),
        file_name=uploads[0][0],
        content=uploads[0][1],
        selected_subcriteria=normalized_selected,
    )
    return {"type": "email", **payload}


@router.post("/batch", summary="Subir un lote de correos")
async def upload_batch(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict:
    max_batch_files = get_max_batch_files()
    try:
        async with request.form(max_files=max_batch_files + 1) as form:
            raw_files = form.getlist("files")
            files = _extract_eml_files(raw_files, max_batch_files=max_batch_files)

            name = str(form.get("name") or "")
            selected_subcriteria = str(form.get("selected_subcriteria") or "")
            normalized_selected = parse_selected_subcriteria_input(selected_subcriteria)
            payload = await create_batch_upload_from_files(
                db=db,
                background_tasks=background_tasks,
                batch_name=name.strip() or "Nuevo lote",
                files=files,
                selected_subcriteria=normalized_selected,
                max_file_bytes=get_max_upload_file_bytes(),
                max_total_bytes=get_max_batch_total_bytes(),
            )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"type": "batch", **payload}


@router.post("/batch/start", summary="Crear un lote pendiente para subida por partes")
async def start_batch_upload(
    name: str = Form("Nuevo lote"),
    db: Session = Depends(get_db),
) -> dict:
    payload = create_pending_batch_upload(
        db=db,
        batch_name=name.strip() or "Nuevo lote",
    )
    return {"type": "batch_upload", **payload}


@router.post("/batch/{batch_id}/chunk", summary="Anadir una parte de archivos a un lote pendiente")
async def upload_batch_chunk(
    batch_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    batch = db.get(Batch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Lote no encontrado")

    max_batch_files = get_max_batch_files()
    try:
        async with request.form(max_files=max_batch_files + 1) as form:
            files = _extract_eml_files(form.getlist("files"), max_batch_files=max_batch_files)
            try:
                expected_start_index = int(str(form.get("expected_start_index") or "1"))
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="expected_start_index debe ser un entero.") from exc
            payload = await append_batch_upload_files(
                db=db,
                batch=batch,
                files=files,
                expected_start_index=expected_start_index,
                max_file_bytes=get_max_upload_file_bytes(),
                max_batch_files=max_batch_files,
                max_total_bytes=get_max_batch_total_bytes(),
            )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"type": "batch_upload_chunk", **payload}


@router.post("/batch/{batch_id}/finalize", summary="Finalizar un lote pendiente y lanzar su analisis")
async def finalize_batch_upload_endpoint(
    batch_id: UUID,
    background_tasks: BackgroundTasks,
    selected_subcriteria: str = Form(""),
    db: Session = Depends(get_db),
) -> dict:
    batch = db.get(Batch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    try:
        normalized_selected = parse_selected_subcriteria_input(selected_subcriteria)
        payload = finalize_batch_upload(
            db=db,
            background_tasks=background_tasks,
            batch=batch,
            selected_subcriteria=normalized_selected,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"type": "batch", **payload}

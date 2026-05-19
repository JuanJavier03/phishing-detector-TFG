from __future__ import annotations

"""
Punto de entrada HTTP de la API FastAPI.

Mantiene una configuracion minima: CORS local para desarrollo y montaje de
routers por dominio funcional.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.formparsers import MultiPartParser

from .routers.batches import router as batches_router
from .routers.emails import router as emails_router
from .routers.health import router as health_router
from .routers.jobs import router as jobs_router
from .routers.metadata import router as metadata_router
from .routers.uploads import router as uploads_router

app = FastAPI(title="Phishing Detector API")

# Evita que lotes con muchos `.eml` pequenos acumulen hasta 1 MB por archivo
# en memoria durante el parseo multipart de Starlette.
MultiPartParser.spool_max_size = 64 * 1024

# CORS solo para los frontends locales previstos durante desarrollo.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, tags=["system"])
app.include_router(metadata_router, prefix="/metadata", tags=["metadata"])
app.include_router(uploads_router, prefix="/uploads", tags=["uploads"])
app.include_router(emails_router, prefix="/emails", tags=["emails"])
app.include_router(batches_router, prefix="/batches", tags=["batches"])
app.include_router(jobs_router, prefix="/jobs", tags=["jobs"])

from __future__ import annotations

"""
Carga configuracion de base de datos y limites de subida desde variables de
entorno, con validaciones simples y mensajes de error explicitos.
"""

import os
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_DIR = BACKEND_DIR.parent

# Se prioriza `backend/.env` y se deja el `.env` del repo como respaldo.
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(REPO_DIR / ".env", override=False)


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL no esta configurada. Define la URL en backend/.env o en variables de entorno."
        )

    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif database_url.startswith("postgresql://") and "+psycopg" not in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

    return database_url


def get_env_int(name: str, default: int, *, minimum: int = 1) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"La variable {name} debe ser un entero.") from exc

    if value < minimum:
        raise RuntimeError(f"La variable {name} debe ser >= {minimum}.")
    return value


def get_logical_cpu_count() -> int:
    return max(os.cpu_count() or 1, 1)


def _auto_analysis_batch_workers() -> int:
    logical_cpus = get_logical_cpu_count()
    return min(32, max(1, logical_cpus * 2))


def _auto_api_worker_processes() -> int:
    return min(2, get_logical_cpu_count())


def get_max_upload_file_bytes() -> int:
    return get_env_int("MAX_UPLOAD_FILE_BYTES", 5 * 1024 * 1024)


def get_max_batch_files() -> int:
    return get_env_int("MAX_BATCH_FILES", 2000)


def get_max_batch_total_bytes() -> int:
    return get_env_int("MAX_BATCH_TOTAL_BYTES", 512 * 1024 * 1024)


def get_analysis_batch_workers() -> int:
    return _auto_analysis_batch_workers()


def get_api_worker_processes() -> int:
    return _auto_api_worker_processes()


def get_database_pool_size() -> int:
    return max(5, get_analysis_batch_workers() + 4)


def get_database_max_overflow() -> int:
    return 4


__all__ = [
    "get_database_url",
    "BACKEND_DIR",
    "REPO_DIR",
    "get_env_int",
    "get_logical_cpu_count",
    "get_max_upload_file_bytes",
    "get_max_batch_files",
    "get_max_batch_total_bytes",
    "get_analysis_batch_workers",
    "get_api_worker_processes",
    "get_database_pool_size",
    "get_database_max_overflow",
]

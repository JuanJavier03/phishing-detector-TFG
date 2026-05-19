from __future__ import annotations

"""
Arranca la API calculando valores por defecto adecuados al equipo actual.
"""

import os
import sys
from pathlib import Path

import uvicorn


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from api.db.config import get_api_worker_processes  # noqa: E402


def _env_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, *, minimum: int = 1) -> int:
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


def main() -> None:
    reload_enabled = _env_bool("API_RELOAD", False)
    workers = 1 if reload_enabled else get_api_worker_processes()
    uvicorn.run(
        "api.main:app",
        host=os.getenv("API_HOST", "127.0.0.1"),
        port=_env_int("API_PORT", 8000, minimum=1),
        reload=reload_enabled,
        workers=workers,
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

"""
Centraliza la creacion lazy del engine y de la factoria de sesiones SQLAlchemy
para compartir configuracion entre routers, servicios y jobs en background.
"""

from typing import Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .config import get_database_max_overflow, get_database_pool_size, get_database_url


_engine: Optional[Engine] = None
_session_local: Optional[sessionmaker[Session]] = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(
            get_database_url(),
            pool_pre_ping=True,
            pool_size=get_database_pool_size(),
            max_overflow=get_database_max_overflow(),
            pool_timeout=60,
        )
    return _engine


def get_session_local() -> sessionmaker[Session]:
    global _session_local
    if _session_local is None:
        _session_local = sessionmaker(
            bind=get_engine(),
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
            class_=Session,
        )
    return _session_local


def get_db() -> Generator[Session, None, None]:
    db = get_session_local()()
    try:
        yield db
    finally:
        db.close()


__all__ = ["get_engine", "get_session_local", "get_db"]

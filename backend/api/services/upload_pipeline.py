from __future__ import annotations

"""
Convierte los uploads `.eml` en la estructura JSON interna normalizada que usa
el resto del backend para enriquecer, persistir y visualizar correos.
"""

from pathlib import Path
from typing import Any, Dict, Optional

from scripts.parse_emails import parse_email_bytes, sha256_bytes


def _safe_upload_name(file_name: str, index: Optional[int] = None) -> str:
    base_name = Path(file_name).name.strip() if isinstance(file_name, str) else ""
    if not base_name:
        suffix = f"_{index}" if index is not None else ""
        return f"email{suffix}.eml"
    return base_name


def _upload_relative_path(file_name: str, raw_sha: str, index: Optional[int] = None) -> str:
    safe_name = _safe_upload_name(file_name, index=index)
    prefix = f"{index:03d}_" if index is not None else ""
    return str(Path("uploads") / f"{prefix}{raw_sha[:12]}_{safe_name}")


def parse_uploaded_email(
    file_name: str,
    content: bytes,
    index: Optional[int] = None,
) -> Dict[str, Any]:
    raw_sha = sha256_bytes(content)
    rel_path = _upload_relative_path(file_name, raw_sha=raw_sha, index=index)
    return parse_email_bytes(
        raw=content,
        file_name=_safe_upload_name(file_name, index=index),
        file_path_rel=rel_path,
        raw_sha=raw_sha,
        raw_size=len(content),
    )

__all__ = ["parse_uploaded_email"]

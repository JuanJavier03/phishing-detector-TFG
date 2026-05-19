from __future__ import annotations

"""
Extrae los adjuntos del correo, normaliza extensiones/tipos MIME y calcula cuantos pertenecen a categorias consideradas sospechosas.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


SUSPICIOUS_TYPES = {"pdf", "zip", "lnk", "svg", "vhdx"}


CONTENT_TYPE_MAP = {
    "application/pdf": "pdf",
    "application/zip": "zip",
    "application/x-zip-compressed": "zip",
    "application/x-ms-shortcut": "lnk",
    "application/x-msdownload": "exe",
    "image/svg+xml": "svg",
    "application/vnd.ms-virtualhd": "vhdx",
    "application/x-vhdx": "vhdx",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ensure_enrichment(email: Dict[str, Any]) -> None:
    email.setdefault("enrichment", {})
    email["enrichment"].setdefault(
        "attachment_types",
        {
            "checked": False,
            "timestamp": None,
            "value": 0,
            "detail": None,
        },
    )


def _ext_from_filename(filename: Optional[str]) -> Optional[str]:
    if not filename or not isinstance(filename, str):
        return None
    name = filename.strip().lower()
    if "." not in name:
        return None
    return name.split(".")[-1] or None


def _type_from_content_type(content_type: Optional[str]) -> Optional[str]:
    if not content_type or not isinstance(content_type, str):
        return None
    ct = content_type.strip().lower()
    return CONTENT_TYPE_MAP.get(ct)


def enrich_attachment_types_in_data(email: Dict[str, Any], force: bool = False) -> bool:
    _ensure_enrichment(email)
    entry = email["enrichment"]["attachment_types"]

    if entry.get("checked") and not force:
        return False

    attachments = email.get("attachments") or []
    if not isinstance(attachments, list):
        attachments = []

    details: List[Dict[str, Any]] = []
    counts: Dict[str, int] = {}
    suspicious: List[Dict[str, Any]] = []

    for att in attachments:
        if not isinstance(att, dict):
            continue
        filename = att.get("filename") if isinstance(att.get("filename"), str) else None
        content_type = att.get("content_type") if isinstance(att.get("content_type"), str) else None
        ext = _ext_from_filename(filename)
        if not ext:
            ext = _type_from_content_type(content_type)
        ext = ext.lower() if isinstance(ext, str) and ext else None
        type_key = ext or "unknown"
        counts[type_key] = counts.get(type_key, 0) + 1
        is_suspicious = bool(ext in SUSPICIOUS_TYPES) if ext else False
        item = {
            "filename": filename,
            "content_type": content_type,
            "type": ext,
            "suspicious": is_suspicious,
        }
        details.append(item)
        if is_suspicious:
            suspicious.append(item)

    entry["checked"] = True
    entry["timestamp"] = _now_iso()
    entry["value"] = int(len(suspicious))
    entry["detail"] = {
        "total_attachments": len(details),
        "types_count": counts,
        "suspicious_types": sorted(SUSPICIOUS_TYPES),
        "suspicious_attachments": suspicious,
        "attachments": details,
        "insufficient_data": len(details) == 0,
    }
    return True


__all__ = ["enrich_attachment_types_in_data", "SUSPICIOUS_TYPES"]

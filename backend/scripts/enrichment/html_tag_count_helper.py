from __future__ import annotations

"""
Cuenta etiquetas HTML del cuerpo y genera el valor bruto usado por el subcriterio de densidad HTML.
"""

from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any, Dict


class _TagCounter(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.counts: Dict[str, int] = {}
        self.total = 0

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[override]
        t = tag.lower()
        self.counts[t] = self.counts.get(t, 0) + 1
        self.total += 1

    def handle_startendtag(self, tag: str, attrs) -> None:  # type: ignore[override]
        t = tag.lower()
        self.counts[t] = self.counts.get(t, 0) + 1
        self.total += 1


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ensure_enrichment(email: Dict[str, Any]) -> None:
    email.setdefault("enrichment", {})
    email["enrichment"].setdefault(
        "html_tag_count",
        {
            "checked": False,
            "timestamp": None,
            "value": 0,
            "detail": None,
        },
    )


def enrich_html_tag_count_in_data(email: Dict[str, Any], force: bool = False) -> bool:
    _ensure_enrichment(email)
    entry = email["enrichment"]["html_tag_count"]

    if entry.get("checked") and not force:
        return False

    body = email.get("body") or {}
    html = body.get("html") if isinstance(body, dict) else None
    if not isinstance(html, str) or not html.strip():
        entry["checked"] = True
        entry["timestamp"] = _now_iso()
        entry["value"] = 0
        entry["detail"] = {
            "total": 0,
            "counts": {},
            "insufficient_data": True,
        }
        return True

    parser = _TagCounter()
    try:
        parser.feed(html)
    except Exception:
        # fallback: treat as no data
        entry["checked"] = True
        entry["timestamp"] = _now_iso()
        entry["value"] = 0
        entry["detail"] = {
            "total": 0,
            "counts": {},
            "insufficient_data": True,
        }
        return True

    entry["checked"] = True
    entry["timestamp"] = _now_iso()
    entry["value"] = int(parser.total)
    entry["detail"] = {
        "total": int(parser.total),
        "counts": dict(sorted(parser.counts.items())),
        "insufficient_data": parser.total == 0,
    }
    return True


__all__ = ["enrich_html_tag_count_in_data"]

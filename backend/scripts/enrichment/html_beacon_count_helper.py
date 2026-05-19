from __future__ import annotations

"""
Analiza el HTML del cuerpo para detectar recursos invisibles o beacons de seguimiento y contar su presencia.
"""

import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from enrichment.link_domain_utils import extract_modal_domain


TRACKING_HINTS = re.compile(r"(pixel|beacon|track|open|utm_)", re.IGNORECASE)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ensure_enrichment(email: Dict[str, Any]) -> None:
    email.setdefault("enrichment", {})
    email["enrichment"].setdefault(
        "html_beacon_count",
        {
            "checked": False,
            "timestamp": None,
            "value": 0,
            "detail": None,
        },
    )


def _parse_int(value: Optional[str]) -> Optional[int]:
    if not value:
        return None
    try:
        return int(re.sub(r"[^\d]", "", value))
    except Exception:
        return None


def _parse_style_dims(style: str) -> Dict[str, Optional[int]]:
    dims = {"width": None, "height": None, "opacity0": False, "hidden": False}
    for part in style.split(";"):
        if ":" not in part:
            continue
        key, val = part.split(":", 1)
        k = key.strip().lower()
        v = val.strip().lower()
        if k in ("width", "height"):
            dims[k] = _parse_int(v)
        if k in ("display", "visibility", "opacity"):
            if k == "display" and v in ("none",):
                dims["hidden"] = True
            if k == "visibility" and v in ("hidden",):
                dims["hidden"] = True
            if k == "opacity" and v in ("0", "0.0"):
                dims["opacity0"] = True
    return dims


def _url_host(src: Optional[str]) -> Optional[str]:
    if not src:
        return None
    try:
        pr = urlparse(src)
    except Exception:
        return None
    host = pr.netloc.split("@")[-1].split(":")[0] if pr.netloc else None
    return host.lower() if host else None


class _BeaconParser(HTMLParser):
    def __init__(self, modal_domain: Optional[str]) -> None:
        super().__init__()
        self.modal_domain = modal_domain
        self.suspects: List[Dict[str, Any]] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[override]
        if tag.lower() != "img":
            return
        attr = {k.lower(): v for k, v in attrs if isinstance(k, str)}
        src = attr.get("src")
        width = _parse_int(attr.get("width"))
        height = _parse_int(attr.get("height"))
        style = attr.get("style") or ""
        style_dims = _parse_style_dims(style)
        if style_dims.get("width") is not None:
            width = style_dims["width"]
        if style_dims.get("height") is not None:
            height = style_dims["height"]

        host = _url_host(src)
        external = None
        if host and self.modal_domain:
            external = not host.endswith(self.modal_domain)

        has_tracking_hint = bool(src and TRACKING_HINTS.search(src))
        tiny = (width in (0, 1) or height in (0, 1)) and (width is not None or height is not None)
        hidden = bool(style_dims.get("hidden") or style_dims.get("opacity0"))

        suspicious = bool(tiny or hidden or has_tracking_hint)
        if suspicious:
            self.suspects.append(
                {
                    "src": src,
                    "host": host,
                    "width": width,
                    "height": height,
                    "hidden": hidden,
                    "tracking_hint": has_tracking_hint,
                    "external": external,
                }
            )


def enrich_html_beacon_count_in_data(email: Dict[str, Any], force: bool = False) -> bool:
    _ensure_enrichment(email)
    entry = email["enrichment"]["html_beacon_count"]

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
            "suspects": [],
            "modal_domain": None,
            "insufficient_data": True,
        }
        return True

    modal = extract_modal_domain(email)
    modal_domain = modal.get("domain")

    parser = _BeaconParser(modal_domain)
    try:
        parser.feed(html)
    except Exception:
        entry["checked"] = True
        entry["timestamp"] = _now_iso()
        entry["value"] = 0
        entry["detail"] = {
            "total": 0,
            "suspects": [],
            "modal_domain": modal_domain,
            "insufficient_data": True,
        }
        return True

    entry["checked"] = True
    entry["timestamp"] = _now_iso()
    entry["value"] = int(len(parser.suspects))
    entry["detail"] = {
        "total": len(parser.suspects),
        "suspects": parser.suspects,
        "modal_domain": modal_domain,
        # We had enough data to scan (valid HTML parsed). A "0" result is a valid outcome.
        "insufficient_data": False,
    }
    return True


__all__ = ["enrich_html_beacon_count_in_data"]

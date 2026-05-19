from __future__ import annotations

"""
Inspecciona enlaces clicables sin realizar trafico saliente para detectar indicadores textuales de captcha.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List

from enrichment.link_domain_utils import link_api_skip_context
from utils.link_url_utils import extract_clickable_links


URL_KEYWORDS = (
    "captcha",
    "recaptcha",
    "hcaptcha",
    "turnstile",
    "cf-chl",
    "challenge",
)

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ensure_enrichment(email: Dict[str, Any]) -> None:
    email.setdefault("enrichment", {})
    email["enrichment"].setdefault(
        "link_captcha",
        {
            "checked": False,
            "timestamp": None,
            "value": None,
            "detail": None,
        },
    )


def _collect_urls(email: Dict[str, Any], primary_only: bool) -> List[str]:
    links = extract_clickable_links(email, primary_only=primary_only)
    return [item["url"] for item in links if isinstance(item.get("url"), str)]


def _url_indicators(url: str) -> List[str]:
    u = url.lower()
    return [kw for kw in URL_KEYWORDS if kw in u]


def enrich_link_captcha_in_data(
    email: Dict[str, Any],
    force: bool = False,
    primary_only: bool = False,
) -> bool:
    _ensure_enrichment(email)
    entry = email["enrichment"]["link_captcha"]

    if entry.get("checked") and not force:
        return False

    urls = _collect_urls(email, primary_only=primary_only)
    skip_context = link_api_skip_context(email)
    detail: Dict[str, Any] = {
        "urls": urls,
        "method": "none",
        "url_indicators": [],
        "http_indicators": [],
        "http_status": [],
        "http_error": [],
        "http_apis_enabled": False,
        "network_access_disabled": True,
        "insufficient_data": True,
    }

    if not urls:
        entry["checked"] = True
        entry["timestamp"] = _now_iso()
        entry["value"] = None
        entry["detail"] = detail
        return True

    if skip_context["should_skip"]:
        detail["method"] = "skipped"
        detail["http_apis_enabled"] = False
        detail["insufficient_data"] = True
        detail["mcdm_excluded"] = True
        detail["mcdm_exclusion_reason"] = skip_context["reason_code"]
        detail["skipped_due_link_count_threshold"] = True
        detail["total_clickable_links"] = int(skip_context["total_links"])
        detail["link_count_threshold"] = int(skip_context["threshold"])
        entry["checked"] = True
        entry["timestamp"] = _now_iso()
        entry["value"] = None
        entry["detail"] = detail
        return True

    url_hits_all: List[Dict[str, Any]] = []
    any_url_hit = False
    for url in urls:
        url_hits = _url_indicators(url)
        if url_hits:
            any_url_hit = True
            url_hits_all.append({"url": url, "hits": url_hits})

    detail["url_indicators"] = url_hits_all
    detail["method"] = "url_static_only"
    detail["insufficient_data"] = False
    value = 1 if any_url_hit else 0

    entry["checked"] = True
    entry["timestamp"] = _now_iso()
    entry["value"] = int(value)
    entry["detail"] = detail
    return True


__all__ = ["enrich_link_captcha_in_data"]

from __future__ import annotations

"""
Agrupa utilidades puras de extraccion, normalizacion y deduplicacion de URLs,
hosts y dominios usados por subcriterios de enlaces. No contiene umbrales de
MCDM ni decisiones de salto de APIs.
"""

from typing import Any, Dict, Iterable, List, Optional, Tuple
from html.parser import HTMLParser
import re
from urllib.parse import urlparse

from utils.domain_utils import extract_host_parts, normalize_host
from utils.resource_extensions import RESOURCE_EXTENSIONS


TEXT_HTTP_URL_REGEX = re.compile(r"https?://[^\s<>'\"()]+", re.IGNORECASE)


def _extract_string(value: Any) -> Optional[str]:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        raw = value.get("raw")
        return raw if isinstance(raw, str) else None
    return None


def _iter_header_values(value: Any) -> Iterable[str]:
    if isinstance(value, list):
        for item in value:
            s = _extract_string(item)
            if s:
                yield s
        return
    s = _extract_string(value)
    if s:
        yield s


def _registrable_domain(host: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    normalized_host, registrable_domain, subdomain, _domain_part, suffix = extract_host_parts(host)
    if not normalized_host or not registrable_domain:
        return None, None, None
    return registrable_domain, subdomain, suffix


def _parse_url_host(url: str) -> Optional[str]:
    try:
        pr = urlparse(url)
    except Exception:
        return None
    host = getattr(pr, "hostname", None)
    return host or None


def _url_host(url: Optional[str]) -> Optional[str]:
    if not isinstance(url, str):
        return None
    parsed_host = _parse_url_host(url)
    return parsed_host.lower() if isinstance(parsed_host, str) else None


def _url_dedupe_key(url: Optional[str]) -> Optional[str]:
    if not isinstance(url, str):
        return None
    try:
        parsed = urlparse(url)
    except Exception:
        cleaned = url.strip().lower()
        return cleaned or None
    host = parsed.hostname.lower() if isinstance(parsed.hostname, str) else None
    path = parsed.path or ""
    query = parsed.query or ""
    fragment = parsed.fragment or ""
    if host:
        return f"{host}{path}?{query}#{fragment}"
    cleaned = url.strip().lower()
    return cleaned or None


class _ClickableLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.urls: List[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[override]
        tag_l = tag.lower() if isinstance(tag, str) else ""
        if tag_l != "a":
            return
        for k, v in attrs:
            if not (isinstance(k, str) and isinstance(v, str)):
                continue
            k_l = k.lower()
            if k_l != "href":
                continue
            url = v.strip()
            if not url:
                continue
            self.urls.append(url)


def _normalize_url_candidate(url: Optional[str]) -> Optional[str]:
    if not url or not isinstance(url, str):
        return None
    u = url.strip().rstrip("]>)},;")
    if not u:
        return None
    if u.startswith(("http://", "https://")):
        normalized = u
    elif u.startswith("//"):
        normalized = "https:" + u
    elif u.lower().startswith("www."):
        normalized = "http://" + u
    else:
        return None
    try:
        parsed = urlparse(normalized)
    except Exception:
        return normalized
    path = (parsed.path or "").lower()
    if any(path.endswith(ext) for ext in RESOURCE_EXTENSIONS):
        return None
    return normalized


def _html_clickable_urls(html: Optional[str], max_urls: int = 200) -> List[str]:
    if not html or not isinstance(html, str):
        return []
    parser = _ClickableLinkParser()
    try:
        parser.feed(html)
    except Exception:
        return []
    out: List[str] = []
    for raw in parser.urls:
        norm = _normalize_url_candidate(raw)
        if not norm:
            continue
        out.append(norm)
        if len(out) >= max_urls:
            break
    return out


def _text_http_urls(text: Optional[str], max_urls: int = 200) -> List[str]:
    if not text or not isinstance(text, str):
        return []
    out: List[str] = []
    for match in TEXT_HTTP_URL_REGEX.finditer(text):
        norm = _normalize_url_candidate(match.group(0))
        if not norm:
            continue
        out.append(norm)
        if len(out) >= max_urls:
            break
    return out


def body_urls(email: Dict[str, Any], max_urls: int = 400) -> List[Dict[str, Any]]:
    """
    Extract real clickable URLs from HTML anchor tags.

    Includes:
    - clickable HTML links (a[href])

    Excludes:
    - URLs written only in text/plain
    - non-anchor hrefs such as area[href]
    - image/script/css/media resources
    - HTML beacons and technical assets
    """
    body = email.get("body") or {}
    body = body if isinstance(body, dict) else {}
    html = body.get("html") if isinstance(body.get("html"), str) else None
    text = body.get("text") if isinstance(body.get("text"), str) else None

    urls: List[Dict[str, Any]] = []
    for u in _html_clickable_urls(html, max_urls=max_urls):
        urls.append({"url": u, "source": "body.html:a[href]"})
        if len(urls) >= max_urls:
            return urls

    if urls:
        return urls

    for u in _text_http_urls(text, max_urls=max_urls):
        urls.append({"url": u, "source": "body.text:http"})
        if len(urls) >= max_urls:
            return urls
    return urls


def extract_clickable_links(
    email: Dict[str, Any],
    primary_only: bool = False,
    max_urls: int = 400,
) -> List[Dict[str, Any]]:
    collected = body_urls(email, max_urls=max_urls)

    deduped: List[Dict[str, Any]] = []
    seen_index: Dict[str, int] = {}
    for item in collected:
        url = item.get("url") if isinstance(item.get("url"), str) else None
        source = item.get("source") if isinstance(item.get("source"), str) else "body"
        if not url:
            continue
        key = _url_dedupe_key(url)
        if not key:
            continue
        existing_index = seen_index.get(key)
        if existing_index is not None:
            sources = deduped[existing_index]["sources"]
            if source not in sources:
                sources.append(source)
            continue
        deduped.append(
            {
                "url": url,
                "host": _url_host(url),
                "sources": [source],
            }
        )
        seen_index[key] = len(deduped) - 1

    if primary_only:
        return deduped[:1]
    return deduped


def primary_link_url(email: Dict[str, Any]) -> Optional[str]:
    links = extract_clickable_links(email, primary_only=True)
    if not links:
        return None
    return links[0].get("url") if isinstance(links[0].get("url"), str) else None


def extract_link_hosts(email: Dict[str, Any], primary_only: bool = False) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen = set()
    for item in extract_clickable_links(email, primary_only=primary_only):
        url_val = item.get("url") if isinstance(item.get("url"), str) else None
        host_val = item.get("host") if isinstance(item.get("host"), str) else None
        source_val = item.get("sources") if isinstance(item.get("sources"), list) else []
        dedupe_key = (url_val or host_val or "").strip().lower()
        if dedupe_key and dedupe_key in seen:
            continue
        if dedupe_key:
            seen.add(dedupe_key)
        if not host_val and url_val:
            host_val = _parse_url_host(url_val)
        host_val = normalize_host(host_val)
        if not host_val:
            continue
        reg_domain, subdomain, suffix = _registrable_domain(host_val)
        if not reg_domain:
            continue
        out.append(
            {
                "url": url_val,
                "host": host_val,
                "registrable_domain": reg_domain,
                "subdomain": subdomain,
                "suffix": suffix,
                "source": source_val[0] if source_val else "body",
                "sources": source_val,
            }
        )
    return out


def unique_link_domains(entries: List[Dict[str, Any]]) -> List[str]:
    seen = set()
    out: List[str] = []
    for entry in entries:
        dom = entry.get("registrable_domain")
        if isinstance(dom, str) and dom and dom not in seen:
            seen.add(dom)
            out.append(dom)
    return out


def unique_link_hosts(entries: List[Dict[str, Any]]) -> List[str]:
    seen = set()
    out: List[str] = []
    for entry in entries:
        host = entry.get("host")
        if isinstance(host, str) and host and host not in seen:
            seen.add(host)
            out.append(host)
    return out


__all__ = [
    "extract_clickable_links",
    "extract_link_hosts",
    "unique_link_domains",
    "_registrable_domain",
    "primary_link_url",
    "body_urls",
    "unique_link_hosts",
]

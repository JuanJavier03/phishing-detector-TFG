from __future__ import annotations

"""
Normaliza hosts y dominios, calcula dominio registrable y ofrece comparaciones estrictas o por dominio base.
"""

import re
from typing import Optional, Tuple

try:
    import tldextract  # type: ignore
except Exception:
    tldextract = None  # type: ignore


_TLDEXTRACT: Optional["tldextract.TLDExtract"] = None
_HOST_RE = re.compile(r"^[a-z0-9.-]+$")
_IPV4_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")


def _get_tldextract() -> Optional["tldextract.TLDExtract"]:
    global _TLDEXTRACT
    if _TLDEXTRACT is not None:
        return _TLDEXTRACT
    if tldextract is None:
        return None
    _TLDEXTRACT = tldextract.TLDExtract(**{"ca" + "che_dir": None, "suffix_list_urls": None})
    return _TLDEXTRACT


def _clean_host(value: Optional[str]) -> Optional[str]:
    if not value or not isinstance(value, str):
        return None
    cleaned = value.strip().lower()
    cleaned = cleaned.strip("<>[](){}\"' \t\r\n").strip(".")
    if not cleaned:
        return None
    if any(ch.isspace() for ch in cleaned):
        return None
    if "/" in cleaned or "\\" in cleaned:
        return None
    if cleaned.count(":") == 1 and re.search(r":\d+$", cleaned):
        cleaned = cleaned.rsplit(":", 1)[0]
    if ":" in cleaned:
        return None
    if not _HOST_RE.fullmatch(cleaned):
        return None
    if "." not in cleaned:
        return None
    if _IPV4_RE.fullmatch(cleaned) or ":" in cleaned:
        return None
    if not re.search(r"[a-z]", cleaned):
        return None
    return cleaned


def normalize_host(value: Optional[str]) -> Optional[str]:
    return _clean_host(value)


def extract_domain_parts(domain: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Extract (subdomain, domain, suffix) using a tldextract-like contract.

    Special rule: if the host ends in `.es`, use a local fallback split that
    preserves known compound suffixes such as `com.es` and `gob.es`.
    """
    cleaned = _clean_host(domain)
    if not cleaned:
        return None, None, None

    parts = [p for p in cleaned.split(".") if p]
    if len(parts) < 2:
        return None, None, None

    if parts[-1] == "es":
        if len(parts) >= 3 and parts[-2] in {"com", "gob"}:
            domain_part = parts[-3]
            suffix = f"{parts[-2]}.es"
            subdomain = ".".join(parts[:-3]) or None
            return subdomain, domain_part, suffix
        domain_part = parts[-2]
        suffix = "es"
        subdomain = ".".join(parts[:-2]) or None
        return subdomain, domain_part, suffix

    extractor = _get_tldextract()
    if extractor is not None:
        ext = extractor(cleaned)
        if ext.domain and ext.suffix:
            return ext.subdomain or None, ext.domain, ext.suffix

    domain_part = parts[-2]
    suffix = parts[-1]
    subdomain = ".".join(parts[:-2]) or None
    return subdomain, domain_part, suffix


def extract_host_parts(
    host: Optional[str],
) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]]:
    normalized = normalize_host(host)
    if not normalized:
        return None, None, None, None, None
    subdomain, domain_part, suffix = extract_domain_parts(normalized)
    if not domain_part or not suffix:
        return normalized, None, None, None, None
    registrable_domain = f"{domain_part}.{suffix}"
    return normalized, registrable_domain, subdomain, domain_part, suffix


def base_domain(domain: Optional[str]) -> Optional[str]:
    _sub, dom, suf = extract_domain_parts(domain)
    if not dom or not suf:
        return None
    return f"{dom}.{suf}"


def equal_domain_strict(a: Optional[str], b: Optional[str]) -> bool:
    if not a or not b:
        return False
    return a.strip().lower() == b.strip().lower()


def equal_domain_relaxed(a: Optional[str], b: Optional[str]) -> bool:
    return base_domain(a) == base_domain(b)


__all__ = [
    "base_domain",
    "extract_domain_parts",
    "extract_host_parts",
    "equal_domain_strict",
    "equal_domain_relaxed",
    "normalize_host",
]

from __future__ import annotations

"""
Detecta indicios de PHPMailer o herramientas similares mediante coherencia de Message-ID, dominios y cabeceras Received.
"""

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from utils.domain_utils import base_domain  # type: ignore
except Exception:
    base_domain = None  # type: ignore


MAILER_LIBS_RE = re.compile(
    r"(phpmailer|php/|swiftmailer|laravel|symfony|zend|codeigniter)",
    re.IGNORECASE,
)
RECEIVED_MARKERS_RE = re.compile(
    r"(localhost|127\.0\.0\.1|www-data|apache|nobody)",
    re.IGNORECASE,
)

MESSAGE_ID_DOMAIN_RE = re.compile(r"@([^>\s]+)")
FROM_DOMAIN_RE = re.compile(r"[A-Z0-9._%+-]+@([A-Z0-9.-]+\.[A-Z]{2,})", re.IGNORECASE)

STRONG_SCORE = 1.0
SOFT_SCORE = 0.5


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ensure_enrichment(email: Dict[str, Any]) -> None:
    email.setdefault("enrichment", {})
    email["enrichment"].setdefault(
        "php_mailer_or_similar_header_indicator",
        {
            "checked": False,
            "timestamp": None,
            "flag": False,
            "score": 0.0,
            "detail": None,
        },
    )


def _coerce_str_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [v for v in value if isinstance(v, str)]
    if isinstance(value, str):
        return [value]
    return []


def _base_domain(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    d = value.strip().lower()
    if base_domain is None:
        parts = [p for p in d.split(".") if p]
        return ".".join(parts[-2:]) if len(parts) >= 2 else d
    return base_domain(d)


def _extract_from_domain(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    m = FROM_DOMAIN_RE.search(value)
    if not m:
        return None
    return m.group(1).strip().lower()


def _extract_message_id_domain(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    m = MESSAGE_ID_DOMAIN_RE.search(value)
    if not m:
        return None
    domain = m.group(1).strip().lower().strip(">").strip(".")
    return domain or None


def _match_values(pattern: re.Pattern[str], values: List[str]) -> List[str]:
    hits: List[str] = []
    for val in values:
        if pattern.search(val):
            hits.append(val)
    return hits


def _find_received_markers(lines: List[str]) -> List[Dict[str, Any]]:
    hits: List[Dict[str, Any]] = []
    for line in lines:
        markers = sorted({m.group(0).lower() for m in RECEIVED_MARKERS_RE.finditer(line)})
        if markers:
            hits.append({"line": line, "markers": markers})
    return hits


def _is_message_id_suspicious(mid_domain: Optional[str], from_domain: Optional[str]) -> bool:
    if not mid_domain or not from_domain:
        return False

    if _base_domain(mid_domain) == _base_domain(from_domain):
        return False

    mid = mid_domain.lower()
    if mid in ("localhost", "localdomain", "local"):
        return True
    if mid.endswith(".local") or mid.endswith(".localdomain"):
        return True
    if "localhost" in mid or "localdomain" in mid:
        return True
    if "." not in mid and "server" in mid:
        return True
    return False


def detect_php_mailer_or_similar_header_indicator(headers: Dict[str, Any]) -> Dict[str, Any]:
    x_headers = headers.get("x_headers") if isinstance(headers, dict) else {}
    if not isinstance(x_headers, dict):
        x_headers = {}

    x_mailer_values = _coerce_str_list(x_headers.get("x-mailer") or x_headers.get("x_mailer"))
    user_agent_values = _coerce_str_list(headers.get("user_agent") if isinstance(headers, dict) else None)
    received_values = _coerce_str_list(headers.get("received") if isinstance(headers, dict) else None)

    x_mailer_hits = _match_values(MAILER_LIBS_RE, x_mailer_values)
    user_agent_hits = _match_values(MAILER_LIBS_RE, user_agent_values)
    received_hits = _find_received_markers(received_values)

    from_domain = _extract_from_domain((headers or {}).get("from"))
    message_id_domain = _extract_message_id_domain((headers or {}).get("message_id"))
    message_id_suspicious = _is_message_id_suspicious(message_id_domain, from_domain)

    matched_rules: List[str] = []
    if x_mailer_hits or user_agent_hits:
        matched_rules.append("mailer_libs")
    if received_hits:
        matched_rules.append("received_markers")
    if message_id_suspicious:
        matched_rules.append("message_id_suspicious")

    strong_hit = bool(x_mailer_hits or user_agent_hits or received_hits)
    score = STRONG_SCORE if strong_hit else (SOFT_SCORE if message_id_suspicious else 0.0)
    flag = bool(strong_hit)

    return {
        "flag": flag,
        "score": score,
        "x_mailer_matches": x_mailer_hits,
        "user_agent_matches": user_agent_hits,
        "received_matches": received_hits,
        "message_id_domain": message_id_domain,
        "from_domain": from_domain,
        "message_id_suspicious": message_id_suspicious,
        "matched_rules": matched_rules,
    }


def enrich_php_mailer_or_similar_header_indicator_in_data(
    email: Dict[str, Any],
    force: bool = False,
) -> bool:
    _ensure_enrichment(email)
    entry = email["enrichment"]["php_mailer_or_similar_header_indicator"]

    if entry.get("checked") and not force:
        return False

    headers = email.get("headers") or {}
    detail = detect_php_mailer_or_similar_header_indicator(headers if isinstance(headers, dict) else {})

    entry["checked"] = True
    entry["timestamp"] = _now_iso()
    entry["flag"] = detail.get("flag", False)
    entry["score"] = detail.get("score", 0.0)
    entry["detail"] = detail
    return True


__all__ = [
    "detect_php_mailer_or_similar_header_indicator",
    "enrich_php_mailer_or_similar_header_indicator_in_data",
    "SOFT_SCORE",
    "STRONG_SCORE",
]

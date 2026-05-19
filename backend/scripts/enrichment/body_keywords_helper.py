from __future__ import annotations

"""
Normaliza texto y HTML del cuerpo del correo, busca palabras o frases de phishing y guarda el recuento con evidencia de coincidencias.
"""

import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple

from utils.keywords import PHISHING_KEYWORDS


MAX_SCAN_CHARS = 200_000


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: List[str] = []

    def handle_data(self, data: str) -> None:  # type: ignore[override]
        if data:
            self._chunks.append(data)

    def text(self) -> str:
        return " ".join(self._chunks)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ensure_enrichment(email: Dict[str, Any]) -> None:
    email.setdefault("enrichment", {})
    email["enrichment"].setdefault(
        "body_keywords",
        {
            "checked": False,
            "timestamp": None,
            "value": 0,
            "detail": None,
        },
    )


def _strip_accents(s: str) -> str:
    # NFKD splits accents into combining marks; drop those.
    return "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch))


def _normalize_text(s: str) -> str:
    """
    Lowercase, remove accents, map non-alnum to spaces, collapse whitespace.
    Produces a stable matching surface robust to diacritics and punctuation.
    """
    s = unescape(s or "")
    s = _strip_accents(s).lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _html_to_text(html: str) -> str:
    parser = _HTMLTextExtractor()
    try:
        parser.feed(html or "")
        return parser.text()
    except Exception:
        return ""


def _combined_body(email: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    body = email.get("body") or {}
    body = body if isinstance(body, dict) else {}
    text = body.get("text") if isinstance(body.get("text"), str) else ""
    html = body.get("html") if isinstance(body.get("html"), str) else ""
    html_text = _html_to_text(html) if html else ""
    combined = f"{text}\n{html_text}".strip()
    truncated = False
    if len(combined) > MAX_SCAN_CHARS:
        combined = combined[:MAX_SCAN_CHARS]
        truncated = True
    scanned = {
        "text_len": len(text),
        "html_len": len(html),
        "html_text_len": len(html_text),
        "combined_len": len(combined),
        "truncated": truncated,
    }
    return combined, scanned


def _compile_phrase_pattern(phrase_norm: str) -> Optional[re.Pattern[str]]:
    if not phrase_norm:
        return None
    # Allow flexible whitespace in multiword phrases.
    escaped = re.escape(phrase_norm).replace(r"\ ", r"\s+")
    # Word-boundary-ish guards (normalized surface is a-z0-9 + spaces).
    return re.compile(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])")


def _flatten_keywords() -> Dict[str, List[Dict[str, str]]]:
    """
    Returns mapping: phrase_norm -> list[{category, lang, phrase_raw}]
    Phrase norms are de-duplicated to avoid double-counting identical phrases
    across languages/categories.
    """
    out: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for category, langs in (PHISHING_KEYWORDS or {}).items():
        if not isinstance(langs, dict):
            continue
        for lang, phrases in langs.items():
            if not isinstance(phrases, list):
                continue
            for phrase in phrases:
                if not isinstance(phrase, str):
                    continue
                phrase_norm = _normalize_text(phrase)
                if not phrase_norm:
                    continue
                out[phrase_norm].append(
                    {
                        "category": str(category),
                        "lang": str(lang),
                        "phrase": phrase,
                    }
                )
    return dict(out)


_PHRASES = _flatten_keywords()
_PHRASE_PATTERNS: Dict[str, re.Pattern[str]] = {
    p: pat for p in _PHRASES.keys() if (pat := _compile_phrase_pattern(p)) is not None
}


def enrich_body_keywords_in_data(email: Dict[str, Any], force: bool = False) -> bool:
    _ensure_enrichment(email)
    entry = email["enrichment"]["body_keywords"]

    if entry.get("checked") and not force:
        return False

    combined_raw, scanned = _combined_body(email)
    insufficient = not bool(combined_raw)
    combined = _normalize_text(combined_raw)
    if not combined:
        insufficient = True

    total_matches = 0
    by_category: Dict[str, int] = defaultdict(int)
    matches: List[Dict[str, Any]] = []

    if not insufficient:
        for phrase_norm, pat in _PHRASE_PATTERNS.items():
            cnt = len(list(pat.finditer(combined)))
            if cnt <= 0:
                continue
            total_matches += cnt
            metas = _PHRASES.get(phrase_norm, [])
            # Do not inflate by_category due to identical phrases repeated across languages.
            cats = {m.get("category") for m in metas if isinstance(m, dict)}
            for cat in sorted([c for c in cats if isinstance(c, str) and c]):
                by_category[cat] += cnt
            matches.append(
                {
                    "phrase_norm": phrase_norm,
                    "count": cnt,
                    "metas": metas,
                }
            )

    matches.sort(key=lambda m: (-int(m.get("count") or 0), str(m.get("phrase_norm") or "")))

    entry["checked"] = True
    entry["timestamp"] = _now_iso()
    entry["value"] = int(total_matches)
    entry["detail"] = {
        "total_matches": int(total_matches),
        "by_category": dict(sorted(by_category.items())),
        "matches": matches[:50],  # cap detail size
        "scanned": scanned,
        "insufficient_data": insufficient,
    }
    return True


__all__ = ["enrich_body_keywords_in_data"]

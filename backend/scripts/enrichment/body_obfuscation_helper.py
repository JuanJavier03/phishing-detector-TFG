from __future__ import annotations

"""
Detecta senales de ofuscacion en el cuerpo, separando presencia de base64 y recuento de caracteres Unicode sospechosos.
"""

import base64
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


DATA_URI_RE = re.compile(
    r"data:[^;\s]+;\s*base64\s*,\s*([A-Za-z0-9+/=_\s-]{20,})",
    re.IGNORECASE,
)

# Remove URL-like segments before generic base64 scan to avoid false positives
# from tracking links / long URL tokens.
URL_LIKE_RE = re.compile(r"(?:https?:)?//[^\s\"'>)]+", re.IGNORECASE)
WWW_LIKE_RE = re.compile(r"\bwww\.[^\s\"'>)]+", re.IGNORECASE)

# Generic blocks: require longer candidates to keep FP low.
GENERIC_BLOCK_RE = re.compile(r"[A-Za-z0-9+/=_-]{80,}")

# Safety cap: prevents pathological large bodies from slowing down processing.
MAX_SCAN_CHARS = 200_000
_TRUNC_HEAD = 120_000
_TRUNC_TAIL = MAX_SCAN_CHARS - _TRUNC_HEAD
_PRINTABLE_HINTS = (b"http", b"<html", b"<a ", b"href", b"script", b"doctype", b"window.")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ensure_enrichment(email: Dict[str, Any]) -> None:
    email.setdefault("enrichment", {})
    email["enrichment"].setdefault(
        "body_obfuscation_base64",
        {
            "checked": False,
            "timestamp": None,
            "value": 0,
            "detail": None,
        },
    )
    email["enrichment"].setdefault(
        "body_obfuscation_unicode",
        {
            "checked": False,
            "timestamp": None,
            "value": 0,
            "detail": None,
        },
    )


def _combined_body(email: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    body = email.get("body") or {}
    body = body if isinstance(body, dict) else {}
    text = body.get("text") if isinstance(body.get("text"), str) else ""
    html = body.get("html") if isinstance(body.get("html"), str) else ""
    combined_full = f"{text}\n{html}".strip()
    combined = combined_full
    truncated = False
    if len(combined) > MAX_SCAN_CHARS:
        # Deterministic: take head + tail to keep both intro and ending.
        head = combined[:_TRUNC_HEAD]
        tail = combined[-_TRUNC_TAIL :]
        combined = head + tail
        truncated = True
    scanned = {
        "text_len": len(text),
        "html_len": len(html),
        "combined_len": len(combined_full),
        "combined_len_scanned": len(combined),
        "truncated": truncated,
    }
    return combined, scanned


def _normalize_b64_candidate(raw: str) -> Optional[str]:
    """
    Normalize candidate to standard base64 alphabet.
    - Removes whitespace
    - Converts URL-safe to standard ('-'->'+', '_'->'/')
    - Pads to multiple of 4
    Returns None if empty/too short.
    """
    if not raw:
        return None
    s = "".join(raw.split())
    if len(s) < 20:
        return None
    s = s.replace("-", "+").replace("_", "/")

    # Fix padding to a multiple of 4 if necessary.
    pad = (-len(s)) % 4
    if pad:
        s = s + ("=" * pad)
    return s


def _decode_base64(candidate: str) -> Optional[bytes]:
    try:
        return base64.b64decode(candidate, validate=True)
    except Exception:
        return None


def _sample(s: str, head: int = 32, tail: int = 8) -> str:
    if len(s) <= head + tail + 3:
        return s
    return f"{s[:head]}...{s[-tail:]}"


def _printable_ratio(data: bytes) -> float:
    if not data:
        return 0.0
    printable = 0
    for b in data:
        if b in (9, 10, 13) or 32 <= b <= 126:
            printable += 1
    return printable / max(1, len(data))


def _passes_b64_post_decode(decoded: bytes) -> bool:
    if decoded is None:
        return False
    if len(decoded) < 20:
        return False
    if _printable_ratio(decoded) >= 0.70:
        return True
    lowered = decoded.lower()
    return any(h in lowered for h in _PRINTABLE_HINTS)


def _find_base64_blocks(combined: str, max_blocks: int = 10) -> Tuple[int, List[Dict[str, Any]]]:
    blocks: List[Dict[str, Any]] = []
    # We count unique normalized blocks to reduce double-counting due to wrapping.
    seen_norm = set()

    def _add(kind: str, raw_block: str) -> None:
        nonlocal blocks
        norm = _normalize_b64_candidate(raw_block)
        if not norm:
            return
        if norm in seen_norm:
            return
        decoded = _decode_base64(norm)
        if decoded is None or not _passes_b64_post_decode(decoded):
            return
        seen_norm.add(norm)
        if len(blocks) < max_blocks:
            raw_compact = "".join(raw_block.split())
            blocks.append(
                {
                    "kind": kind,
                    "length": len(raw_compact),
                    "decoded_len": len(decoded),
                    "sample": _sample(raw_compact),
                }
            )

    for m in DATA_URI_RE.finditer(combined):
        _add("data_uri", m.group(1))

    # Generic scan surface:
    # - remove URL-like segments to reduce false positives (tracking links, long URL tokens)
    # - remove whitespace so wrapped base64 stays contiguous.
    combined_no_urls = URL_LIKE_RE.sub(" ", combined)
    combined_no_urls = WWW_LIKE_RE.sub(" ", combined_no_urls)
    combined_compact = re.sub(r"\s+", "", combined_no_urls)
    for m in GENERIC_BLOCK_RE.finditer(combined_compact):
        _add("block", m.group(0))

    return len(seen_norm), blocks


def _count_suspicious_unicode(combined: str, top_n: int = 10) -> Tuple[int, List[Dict[str, Any]]]:
    counts: Dict[str, int] = {}
    categories: Dict[str, str] = {}

    cf = 0
    co = 0
    cc = 0

    for ch in combined:
        cat = unicodedata.category(ch)
        if cat == "Cf":
            cf += 1
        elif cat == "Co":
            co += 1
        elif cat == "Cc" and ch not in ("\r", "\n", "\t"):
            cc += 1
        else:
            continue

        counts[ch] = counts.get(ch, 0) + 1
        categories[ch] = cat

    total = int(cf + co + cc)

    top = sorted(counts.items(), key=lambda kv: (-kv[1], ord(kv[0])))
    out: List[Dict[str, Any]] = []
    for ch, cnt in top[:top_n]:
        cat = categories.get(ch)
        cp = f"U+{ord(ch):04X}"
        # Avoid rendering invisible/control chars.
        char_val = ch if (ch.isprintable() and not ch.isspace() and cat not in ("Cf", "Cc", "Co")) else None
        out.append({"codepoint": cp, "char": char_val, "count": cnt, "category": cat})
    return total, out


def _compute_obfuscation(
    combined: str,
    insufficient: bool,
) -> Dict[str, Any]:
    base64_count, base64_blocks = _find_base64_blocks(combined) if not insufficient else (0, [])
    unicode_count, unicode_top = _count_suspicious_unicode(combined) if not insufficient else (0, [])
    base64_present = 1 if base64_count > 0 else 0
    return {
        "base64_blocks_count": int(base64_count),
        "base64_present": int(base64_present),
        "base64_blocks": base64_blocks,
        "unicode_suspicious_count": int(unicode_count),
        "unicode_suspicious_top": unicode_top,
    }


def _base64_encoded_sections(email: Dict[str, Any]) -> Tuple[int, List[Dict[str, Any]], str]:
    """
    Count non-attachment MIME sections whose Content-Transfer-Encoding is base64.

    Returns (count, section_details, source).
    """
    parts = email.get("parts")
    if not isinstance(parts, list):
        return 0, [], "none"

    sections: List[Dict[str, Any]] = []
    for idx, part in enumerate(parts):
        if not isinstance(part, dict):
            continue
        encoding = part.get("encoding")
        if not isinstance(encoding, str):
            continue
        if "base64" not in encoding.strip().lower():
            continue
        if part.get("is_attachment") is True:
            continue
        sections.append(
            {
                "part_index": idx,
                "content_type": part.get("content_type"),
                "content_disposition": part.get("content_disposition"),
                "encoding": encoding,
                "filename": part.get("filename"),
                "size": part.get("size"),
            }
        )
    return len(sections), sections, "parts"


def enrich_body_obfuscation_base64_in_data(email: Dict[str, Any], force: bool = False) -> bool:
    _ensure_enrichment(email)
    entry = email["enrichment"]["body_obfuscation_base64"]

    if entry.get("checked") and not force:
        return False

    combined, scanned = _combined_body(email)
    base64_sections_count, base64_sections, sections_source = _base64_encoded_sections(email)
    insufficient = False

    computed = _compute_obfuscation(combined, not bool(combined))
    if base64_sections_count <= 0:
        # If MIME parts are incomplete, inspect the rendered body as a backup path.
        fallback_insufficient = not bool(combined)
        scanned["insufficient_data"] = bool(fallback_insufficient)
        base64_sections_count = int(computed["base64_blocks_count"])
        base64_sections = []
        sections_source = "body_scan_fallback"
        insufficient = bool(fallback_insufficient)

    base64_present = 1 if base64_sections_count > 0 else 0
    scanned["insufficient_data"] = bool(insufficient)

    entry["checked"] = True
    entry["timestamp"] = _now_iso()
    entry["value"] = int(base64_present)
    entry["detail"] = {
        "base64_present": base64_present,
        "base64_sections_count": int(base64_sections_count),
        "base64_sections": base64_sections,
        "base64_sections_source": sections_source,
        "base64_blocks_count": int(computed["base64_blocks_count"]),
        "base64_blocks": computed["base64_blocks"],
        "scanned": scanned,
        "insufficient_data": insufficient,
    }
    return True


def enrich_body_obfuscation_unicode_in_data(email: Dict[str, Any], force: bool = False) -> bool:
    _ensure_enrichment(email)
    entry = email["enrichment"]["body_obfuscation_unicode"]

    if entry.get("checked") and not force:
        return False

    combined, scanned = _combined_body(email)
    insufficient = not bool(combined)
    scanned["insufficient_data"] = bool(insufficient)

    computed = _compute_obfuscation(combined, insufficient)
    unicode_count = int(computed["unicode_suspicious_count"])

    entry["checked"] = True
    entry["timestamp"] = _now_iso()
    entry["value"] = unicode_count
    entry["detail"] = {
        "unicode_suspicious_count": unicode_count,
        "unicode_suspicious_top": computed["unicode_suspicious_top"],
        "scanned": scanned,
        "insufficient_data": insufficient,
    }
    return True


__all__ = [
    "enrich_body_obfuscation_base64_in_data",
    "enrich_body_obfuscation_unicode_in_data",
]

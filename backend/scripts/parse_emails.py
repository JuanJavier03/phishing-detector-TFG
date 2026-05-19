from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from email import policy
from email.header import decode_header
from email.message import Message
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from utils.resource_extensions import RESOURCE_EXTENSIONS


IPV4_REGEX = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")
TEXT_HTTP_URL_REGEX = re.compile(r"https?://[^\s<>'\"()]+", re.IGNORECASE)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def decode_mime_value(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None

    try:
        parts: List[str] = []
        for fragment, encoding in decode_header(value):
            if isinstance(fragment, bytes):
                try:
                    parts.append(fragment.decode(encoding or "utf-8", errors="replace"))
                except LookupError:
                    parts.append(fragment.decode("utf-8", errors="replace"))
            else:
                parts.append(fragment)
        return "".join(parts)
    except Exception:
        return value


def normalize_date(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
        if parsed is None:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.isoformat()
    except Exception:
        return None


def to_utf8_text(data: bytes) -> str:
    return data.decode("utf-8", errors="replace")


def split_raw_headers_body(raw: bytes) -> Tuple[str, str]:
    match = re.search(br"\r?\n\r?\n", raw)
    if not match:
        return to_utf8_text(raw), ""
    boundary = match.end()
    return to_utf8_text(raw[:boundary]), to_utf8_text(raw[boundary:])


def collect_x_headers(message: Message) -> Dict[str, Any]:
    headers: Dict[str, Any] = {}
    for key, _value in message.raw_items():
        if not key.lower().startswith("x-"):
            continue
        values = [decode_mime_value(item) for item in raw_header_values(message, key)]
        headers[key.lower()] = values[0] if len(values) == 1 else values
    return headers


def raw_header_values(message: Message, key: str) -> List[str]:
    wanted = key.lower()
    return [value for raw_key, value in message.raw_items() if raw_key.lower() == wanted]


def raw_header_value(message: Message, key: str) -> Optional[str]:
    values = raw_header_values(message, key)
    return values[0] if values else None


class ClickableLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.urls: List[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        if tag.lower() != "a":
            return
        for key, value in attrs:
            if key.lower() != "href" or not isinstance(value, str):
                continue
            normalized = normalize_url_candidate(value)
            if normalized:
                self.urls.append(normalized)


def normalize_url_candidate(url: Optional[str]) -> Optional[str]:
    if not isinstance(url, str):
        return None

    cleaned = url.strip().rstrip("]>)},;")
    if not cleaned:
        return None

    if cleaned.startswith(("http://", "https://")):
        normalized = cleaned
    elif cleaned.startswith("//"):
        normalized = f"https:{cleaned}"
    elif cleaned.lower().startswith("www."):
        normalized = f"http://{cleaned}"
    else:
        return None

    try:
        parsed = urlparse(normalized)
    except Exception:
        return normalized

    path = (parsed.path or "").lower()
    if any(path.endswith(extension) for extension in RESOURCE_EXTENSIONS):
        return None
    return normalized


def html_clickable_urls(html: Optional[str]) -> List[str]:
    if not isinstance(html, str):
        return []
    parser = ClickableLinkParser()
    try:
        parser.feed(html)
    except Exception:
        return []
    return parser.urls


def text_http_urls(text: Optional[str]) -> List[str]:
    if not isinstance(text, str):
        return []
    urls: List[str] = []
    for match in TEXT_HTTP_URL_REGEX.finditer(text):
        normalized = normalize_url_candidate(match.group(0))
        if normalized:
            urls.append(normalized)
    return urls


def url_dedupe_key(url: Optional[str]) -> Optional[str]:
    if not isinstance(url, str):
        return None
    try:
        parsed = urlparse(url)
    except Exception:
        cleaned = url.strip().lower()
        return cleaned or None

    host = parsed.hostname.lower() if isinstance(parsed.hostname, str) else None
    if host:
        return f"{host}{parsed.path or ''}?{parsed.query or ''}#{parsed.fragment or ''}"
    cleaned = url.strip().lower()
    return cleaned or None


def extract_urls(text: str, html: str) -> List[Dict[str, Any]]:
    ordered_urls: List[str] = []
    seen: set[str] = set()

    for url in html_clickable_urls(html):
        key = url_dedupe_key(url)
        if key and key not in seen:
            seen.add(key)
            ordered_urls.append(url)

    if not ordered_urls:
        for url in text_http_urls(text):
            key = url_dedupe_key(url)
            if key and key not in seen:
                seen.add(key)
                ordered_urls.append(url)

    extracted: List[Dict[str, Any]] = []
    for url in ordered_urls:
        try:
            parsed = urlparse(url)
            host = parsed.netloc.split("@")[-1].split(":")[0]
            path = parsed.path or ""
            if parsed.query:
                path = f"{path}?{parsed.query}"
            extracted.append(
                {
                    "url": url,
                    "domain": host,
                    "scheme": parsed.scheme or None,
                    "path": path or None,
                    "is_punycode": "xn--" in host.lower(),
                    "is_ip": bool(IPV4_REGEX.match(host)),
                }
            )
        except Exception:
            extracted.append(
                {
                    "url": url,
                    "domain": None,
                    "scheme": None,
                    "path": None,
                    "is_punycode": False,
                    "is_ip": False,
                }
            )
    return extracted


def part_payload_bytes(part: Message) -> bytes:
    try:
        payload = part.get_payload(decode=True)
        return payload if payload is not None else b""
    except Exception:
        return b""


def part_text_content(part: Message) -> Optional[str]:
    content_type = (part.get_content_type() or "").lower()
    if not content_type.startswith("text/"):
        return None
    try:
        return part.get_content()
    except Exception:
        payload = part_payload_bytes(part)
        charset = part.get_content_charset() or "utf-8"
        try:
            return payload.decode(charset, errors="replace")
        except LookupError:
            return payload.decode("utf-8", errors="replace")


def decode_filename(value: Optional[str]) -> Optional[str]:
    return decode_mime_value(value) if value else value


def parse_email_bytes(
    raw: bytes,
    file_name: str,
    file_path_rel: str,
    raw_sha: str,
    raw_size: int,
) -> Dict[str, Any]:
    raw_headers, raw_body = split_raw_headers_body(raw)
    message = BytesParser(policy=policy.default).parsebytes(raw)

    headers: Dict[str, Any] = {
        "from": decode_mime_value(raw_header_value(message, "From")),
        "to": decode_mime_value(raw_header_value(message, "To")),
        "cc": decode_mime_value(raw_header_value(message, "Cc")),
        "bcc": decode_mime_value(raw_header_value(message, "Bcc")),
        "reply_to": decode_mime_value(raw_header_value(message, "Reply-To")),
        "subject": decode_mime_value(raw_header_value(message, "Subject")),
        "date": normalize_date(raw_header_value(message, "Date")),
        "message_id": decode_mime_value(raw_header_value(message, "Message-ID")),
        "return_path": decode_mime_value(raw_header_value(message, "Return-Path")),
        "received": [decode_mime_value(item) for item in raw_header_values(message, "Received")],
        "authentication_results": [
            decode_mime_value(item) for item in raw_header_values(message, "Authentication-Results")
        ],
        "received_spf": [decode_mime_value(item) for item in raw_header_values(message, "Received-SPF")],
        "dkim_signatures": [decode_mime_value(item) for item in raw_header_values(message, "DKIM-Signature")],
        "dkim_signature": decode_mime_value(raw_header_value(message, "DKIM-Signature")),
        "domainkey_signature": decode_mime_value(raw_header_value(message, "DomainKey-Signature")),
        "mime_version": decode_mime_value(raw_header_value(message, "MIME-Version")),
        "content_type": decode_mime_value(raw_header_value(message, "Content-Type")),
        "content_transfer_encoding": decode_mime_value(raw_header_value(message, "Content-Transfer-Encoding")),
        "user_agent": decode_mime_value(raw_header_value(message, "User-Agent")),
        "x_headers": collect_x_headers(message),
    }

    parts: List[Dict[str, Any]] = []
    body_text_chunks: List[str] = []
    body_html_chunks: List[str] = []
    attachments: List[Dict[str, Any]] = []
    detected_charsets: set[str] = set()
    transfer_encodings: set[str] = set()

    def append_part(part: Message) -> None:
        content_type = (part.get_content_type() or "").lower()
        disposition = part.get_content_disposition() or None
        charset = part.get_content_charset() or None
        filename = decode_filename(part.get_filename())
        transfer_encoding = part.get("Content-Transfer-Encoding")
        payload = part_payload_bytes(part)
        text_preview: Optional[str] = None
        html_preview: Optional[str] = None

        if charset:
            detected_charsets.add(charset.lower())
        if isinstance(transfer_encoding, str) and transfer_encoding:
            transfer_encodings.add(transfer_encoding.lower())

        if content_type == "text/plain":
            text = part_text_content(part)
            if text is not None:
                body_text_chunks.append(text)
                text_preview = text[:500]
        elif content_type == "text/html":
            html = part_text_content(part)
            if html is not None:
                body_html_chunks.append(html)
                html_preview = html[:500]

        is_attachment = disposition == "attachment" or filename is not None
        if is_attachment:
            attachments.append(
                {
                    "filename": filename,
                    "content_type": content_type or None,
                }
            )

        parts.append(
            {
                "content_type": content_type or None,
                "content_disposition": disposition,
                "filename": filename,
                "charset": charset,
                "encoding": transfer_encoding.lower() if isinstance(transfer_encoding, str) else transfer_encoding,
                "size": len(payload),
                "sha256": sha256_bytes(payload),
                "is_attachment": is_attachment,
                "text_preview": text_preview,
                "html_preview": html_preview,
            }
        )

    if message.is_multipart():
        for part in message.walk():
            if not part.is_multipart():
                append_part(part)
    else:
        append_part(message)

    body_text = "\n".join(chunk for chunk in body_text_chunks if chunk) or None
    body_html = "\n".join(chunk for chunk in body_html_chunks if chunk) or None

    return {
        "metadata": {
            "file_name": file_name,
            "file_stem": Path(file_name).stem,
            "file_ext": Path(file_name).suffix,
            "file_path": "/" + file_path_rel.replace("\\", "/"),
            "raw_size": raw_size,
            "raw_sha256": raw_sha,
            "parse_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        },
        "headers": headers,
        "parts": parts,
        "body": {"text": body_text, "html": body_html},
        "urls": extract_urls(body_text or "", body_html or ""),
        "attachments": attachments,
        "encodings": {
            "charsets_detected": sorted(detected_charsets),
            "transfer_encodings": sorted(transfer_encodings),
        },
        "enrichment": {},
        "raw": {"headers": raw_headers, "body": raw_body},
    }


__all__ = ["parse_email_bytes", "sha256_bytes"]

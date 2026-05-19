from __future__ import annotations

"""
Resuelve dominio, host e IP de origen a partir de cabeceras, priorizando fuentes fiables como DMARC y Received-SPF.
"""

import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from utils.subdomain_utils import normalize_subdomain
from utils.domain_utils import base_domain, extract_host_parts, normalize_host


EMAIL_DOMAIN_RE = re.compile(r"[A-Z0-9._%+-]+@([A-Z0-9.-]+\.[A-Z]{2,})", re.IGNORECASE)
AUTH_DMARC_RESULT_RE = re.compile(r"dmarc\s*=\s*([a-zA-Z-]+)", re.IGNORECASE)
AUTH_HEADER_FROM_RE = re.compile(r"header\.from=([^\s;]+)", re.IGNORECASE)
RECEIVED_CLIENT_IP_RE = re.compile(r"client-ip=([0-9a-fA-F\.:]+)", re.IGNORECASE)
IP_LITERAL_RE = re.compile(r"\[([0-9a-fA-F\.:]+)\]")
IP_FROM_HOST_RE = re.compile(r"\bfrom\s+[^\s]+\s+\(([0-9a-fA-F\.:]+)\)", re.IGNORECASE)

TRUSTED_DOMAIN_SOURCES = ("authentication_results_header_from",)
UNTRUSTED_DOMAIN_SOURCES = ("return_path", "from")


def _extract_string(value: Any) -> Optional[str]:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        raw = value.get("raw")
        return raw if isinstance(raw, str) else None
    return None


def iter_header_values(value: Any) -> Iterable[str]:
    if isinstance(value, list):
        for item in value:
            raw = _extract_string(item)
            if raw:
                yield raw
        return
    raw = _extract_string(value)
    if raw:
        yield raw


def _email_domains(value: Any) -> Iterable[str]:
    for raw in iter_header_values(value):
        for match in EMAIL_DOMAIN_RE.finditer(raw):
            yield match.group(1).lower()


def _normalize_dmarc_status(value: Optional[str]) -> Optional[str]:
    if not isinstance(value, str):
        return None
    cleaned = value.strip().lower()
    aliases = {
        "pass": "pass",
        "bestguesspass": "none",
        "none": "none",
        "temperror": "temperror",
        "temp-error": "temperror",
        "permerror": "permerror",
        "perm-error": "permerror",
        "fail": "fail",
        "fail-policy": "fail",
    }
    return aliases.get(cleaned, cleaned or None)


def extract_host_from_address_header(value: Any) -> Tuple[Optional[str], Optional[str]]:
    for raw in iter_header_values(value):
        for match in EMAIL_DOMAIN_RE.finditer(raw):
            host = normalize_host(match.group(1))
            if host:
                return host, raw
    return None, _extract_string(value)


def _host_from_auth_results_dmarc_pass(headers: Dict[str, Any]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    for line in iter_header_values(headers.get("authentication_results")):
        dmarc_match = AUTH_DMARC_RESULT_RE.search(line)
        if not dmarc_match:
            continue
        dmarc_status = _normalize_dmarc_status(dmarc_match.group(1))
        if dmarc_status != "pass":
            continue
        header_from_match = AUTH_HEADER_FROM_RE.search(line)
        if not header_from_match:
            continue
        token = header_from_match.group(1)
        host, _ = extract_host_from_address_header(token)
        if host:
            return host, line, dmarc_status
        normalized = normalize_host(token)
        if normalized:
            return normalized, line, dmarc_status
    return None, None, None


def _build_resolution_result(
    host: Optional[str],
    *,
    source: str,
    raw_evidence: Optional[str],
    candidates: Dict[str, Optional[str]],
    host_candidates: Dict[str, Optional[str]],
    evidence: Dict[str, Optional[str]],
    trusted: bool,
    reason: str,
    dmarc_status: Optional[str] = None,
) -> Dict[str, Any]:
    normalized_host, registrable_domain, subdomain, domain_part, suffix = extract_host_parts(host)
    return {
        "host": normalized_host,
        "domain": registrable_domain,
        "registrable_domain": registrable_domain,
        "subdomain": subdomain,
        "subdomain_normalized": normalize_subdomain(subdomain),
        "domain_part": domain_part,
        "suffix": suffix,
        "source": source,
        "raw_evidence": raw_evidence,
        "candidates": candidates,
        "host_candidates": host_candidates,
        "evidence": evidence,
        "trusted": trusted,
        "reason": reason,
        "trust_cutoff": "return_path",
        "dmarc_status": dmarc_status,
    }


def resolve_sender_host(
    headers: Dict[str, Any],
    *,
    reliable_only: bool = True,
) -> Dict[str, Any]:
    headers = headers if isinstance(headers, dict) else {}

    from_host, from_raw = extract_host_from_address_header(headers.get("from"))
    return_path_host, return_path_raw = extract_host_from_address_header(headers.get("return_path"))
    auth_header_from_host, auth_header_from_raw, dmarc_status = _host_from_auth_results_dmarc_pass(headers)

    host_candidates = {
        "authentication_results_header_from": auth_header_from_host,
        "from": from_host,
        "return_path": return_path_host,
    }
    candidates = {
        source: base_domain(host)
        for source, host in host_candidates.items()
    }
    evidence = {
        "authentication_results_header_from": auth_header_from_raw,
        "from": from_raw,
        "return_path": return_path_raw,
    }

    trusted_domains = [candidates[source] for source in TRUSTED_DOMAIN_SOURCES if candidates.get(source)]
    if trusted_domains:
        return _build_resolution_result(
            host_candidates.get("authentication_results_header_from"),
            source="authentication_results_header_from",
            raw_evidence=evidence.get("authentication_results_header_from"),
            candidates=candidates,
            host_candidates=host_candidates,
            evidence=evidence,
            trusted=True,
            reason="dmarc_pass_header_from",
            dmarc_status=dmarc_status,
        )

    if not reliable_only:
        for source in UNTRUSTED_DOMAIN_SOURCES:
            if host_candidates.get(source) and candidates.get(source):
                return _build_resolution_result(
                    host_candidates.get(source),
                    source=source,
                    raw_evidence=evidence.get(source),
                    candidates=candidates,
                    host_candidates=host_candidates,
                    evidence=evidence,
                    trusted=False,
                    reason="untrusted_source",
                    dmarc_status=dmarc_status,
                )

    return _build_resolution_result(
        None,
        source="none",
        raw_evidence=None,
        candidates=candidates,
        host_candidates=host_candidates,
        evidence=evidence,
        trusted=False,
        reason="dmarc_not_pass_or_missing"
        if dmarc_status != "pass"
        else ("untrusted_only" if any(candidates.get(source) for source in UNTRUSTED_DOMAIN_SOURCES) else "none"),
        dmarc_status=dmarc_status,
    )


def resolve_sender_domain(
    headers: Dict[str, Any],
    *,
    reliable_only: bool = True,
) -> Dict[str, Any]:
    return resolve_sender_host(headers, reliable_only=reliable_only)


def recipient_domains(headers: Dict[str, Any]) -> List[str]:
    headers = headers if isinstance(headers, dict) else {}
    domains = set()
    for key in ("to", "cc", "bcc", "delivered_to"):
        for domain in _email_domains(headers.get(key)):
            normalized = base_domain(domain)
            if normalized:
                domains.add(normalized)
    return sorted(domains)


def host_matches_recipient(host: Optional[str], recipient_domains_list: Iterable[str]) -> bool:
    normalized_domain = base_domain(host)
    if not normalized_domain:
        return False
    return normalized_domain in {domain for domain in recipient_domains_list if isinstance(domain, str)}


def extract_received_ip(line: str) -> Optional[str]:
    if not line:
        return None
    match = IP_LITERAL_RE.search(line)
    if match:
        return match.group(1).strip()
    match = IP_FROM_HOST_RE.search(line)
    if match:
        return match.group(1).strip()
    return None


def extract_received_by_host(line: str) -> Optional[str]:
    if not line:
        return None
    match = re.search(r"\bby\s+([^\s;]+)", line, re.IGNORECASE)
    if not match:
        return None
    return normalize_host(match.group(1).strip(")"))


def resolve_sender_ip_from_headers(headers: Dict[str, Any]) -> Tuple[Optional[str], str]:
    headers = headers if isinstance(headers, dict) else {}
    recipients = recipient_domains(headers)

    for line in iter_header_values(headers.get("received_spf")):
        match = RECEIVED_CLIENT_IP_RE.search(line)
        if match:
            return match.group(1).strip(), "received_spf"

    received_values = list(iter_header_values(headers.get("received")))
    for line in reversed(received_values):
        ip = extract_received_ip(line)
        if not ip:
            continue
        by_host = extract_received_by_host(line)
        if by_host and recipients and host_matches_recipient(by_host, recipients):
            continue
        return ip, "received"

    for line in received_values:
        ip = extract_received_ip(line)
        if ip:
            return ip, "received"

    return None, "none"


__all__ = [
    "TRUSTED_DOMAIN_SOURCES",
    "UNTRUSTED_DOMAIN_SOURCES",
    "extract_host_from_address_header",
    "extract_received_by_host",
    "extract_received_ip",
    "host_matches_recipient",
    "iter_header_values",
    "recipient_domains",
    "resolve_sender_domain",
    "resolve_sender_host",
    "resolve_sender_ip_from_headers",
]

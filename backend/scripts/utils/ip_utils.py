from __future__ import annotations

"""
Resuelve IPs de origen desde cabeceras y DNS, aplicando preferencia por candidatos publicos y trazables.
"""

import re
import socket
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import dns.resolver  # type: ignore
except Exception:
    dns = None  # type: ignore


EMAIL_DOMAIN_RE = re.compile(
    r"[A-Z0-9._%+-]+@([A-Z0-9.-]+\.[A-Z]{2,})", re.IGNORECASE
)
IPV4_RE = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")

from utils.origin_resolution import resolve_sender_domain


def _email_domains(value: Optional[str]) -> Iterable[str]:
    if not value or not isinstance(value, str):
        return []
    return [m.group(1).lower() for m in EMAIL_DOMAIN_RE.finditer(value)]


def _normalize_domain(value: Optional[str]) -> Optional[str]:
    if not value or not isinstance(value, str):
        return None
    domain = value.strip().lower().strip("<>").strip(".")
    if not domain or " " in domain or "/" in domain:
        return None
    if ":" in domain and not re.search(r"[a-z]", domain):
        # Likely an IPv6 literal
        return None
    if IPV4_RE.fullmatch(domain):
        return None
    parts = [p for p in domain.split(".") if p]
    if len(parts) < 2:
        return None
    return domain


def _get_domain_from_header(value: Optional[str]) -> Optional[str]:
    for dom in _email_domains(value):
        normalized = _normalize_domain(dom)
        if normalized:
            return normalized
    return None


def _get_domain_from_auth_results(headers: Dict[str, Any]) -> Optional[str]:
    auth_results = headers.get("authentication_results") or []
    for line in auth_results:
        if not isinstance(line, str):
            continue
        m = re.search(r"smtp\.mailfrom=([^\s;]+)", line, re.IGNORECASE)
        if m:
            dom = _get_domain_from_header(m.group(1))
            if dom:
                return dom
    return None


def _get_domain_from_received_spf(headers: Dict[str, Any]) -> Optional[str]:
    received_spf = headers.get("received_spf") or []
    for line in received_spf:
        if not isinstance(line, str):
            continue
        m = re.search(r"domain of\s+([^\s;]+)", line, re.IGNORECASE)
        if m:
            token = m.group(1)
            dom = _get_domain_from_header(token)
            if dom:
                return dom
            dom = _normalize_domain(token)
            if dom:
                return dom
        for dom in _email_domains(line):
            normalized = _normalize_domain(dom)
            if normalized:
                return normalized
    return None


def _get_domain_from_received_infra(headers: Dict[str, Any]) -> Optional[str]:
    received = headers.get("received") or []
    for line in reversed(received):
        if not isinstance(line, str):
            continue
        m = re.search(r"\bfrom\s+([^\s\(\);]+)", line, re.IGNORECASE)
        if not m:
            continue
        host = m.group(1)
        dom = _normalize_domain(host)
        if dom:
            return dom
    return None


def _get_origin_domain(headers: Dict[str, Any]) -> Tuple[Optional[str], str, Dict[str, Optional[str]]]:
    resolved = resolve_sender_domain(headers, reliable_only=True)
    domain = resolved.get("host") if isinstance(resolved.get("host"), str) else None
    source = resolved.get("source") if isinstance(resolved.get("source"), str) else "none"
    candidates = resolved.get("host_candidates") if isinstance(resolved.get("host_candidates"), dict) else {}
    return domain, source, candidates


def _dedupe(items: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _resolve_with_dnspython(domain: str) -> Tuple[List[str], Dict[str, Any]]:
    detail: Dict[str, Any] = {
        "resolver": "dnspython",
        "method": None,
        "mx_hosts": [],
        "ips": [],
        "errors": [],
    }
    ips: List[str] = []
    if dns is None:
        detail["errors"].append("dnspython_not_available")
        return ips, detail

    resolver = dns.resolver.Resolver()

    try:
        mx_answers = resolver.resolve(domain, "MX")
        mx_hosts = sorted(
            [(r.preference, str(r.exchange).rstrip(".")) for r in mx_answers],
            key=lambda x: x[0],
        )
        detail["mx_hosts"] = [host for _, host in mx_hosts]
        for _, host in mx_hosts:
            try:
                for rd in resolver.resolve(host, "A"):
                    ips.append(rd.to_text())
                for rd in resolver.resolve(host, "AAAA"):
                    ips.append(rd.to_text())
            except Exception as e:
                detail["errors"].append(f"mx_host_resolve_error:{host}:{e}")
        if ips:
            detail["method"] = "mx"
            detail["ips"] = _dedupe(ips)
            return detail["ips"], detail
    except Exception as e:
        detail["errors"].append(f"mx_lookup_error:{e}")

    try:
        for rd in resolver.resolve(domain, "A"):
            ips.append(rd.to_text())
        for rd in resolver.resolve(domain, "AAAA"):
            ips.append(rd.to_text())
        if ips:
            detail["method"] = "a_aaaa"
            detail["ips"] = _dedupe(ips)
            return detail["ips"], detail
    except Exception as e:
        detail["errors"].append(f"a_aaaa_lookup_error:{e}")

    return ips, detail


def _resolve_direct_with_dnspython(host: str) -> Tuple[List[str], Dict[str, Any]]:
    detail: Dict[str, Any] = {
        "resolver": "dnspython",
        "method": "a_aaaa",
        "mx_hosts": [],
        "ips": [],
        "errors": [],
    }
    ips: List[str] = []
    if dns is None:
        detail["errors"].append("dnspython_not_available")
        return ips, detail

    resolver = dns.resolver.Resolver()
    try:
        for rd in resolver.resolve(host, "A"):
            ips.append(rd.to_text())
        for rd in resolver.resolve(host, "AAAA"):
            ips.append(rd.to_text())
        detail["ips"] = _dedupe(ips)
        return detail["ips"], detail
    except Exception as e:
        detail["errors"].append(f"a_aaaa_lookup_error:{e}")
        return [], detail


def _resolve_with_socket(domain: str) -> Tuple[List[str], Dict[str, Any]]:
    detail: Dict[str, Any] = {
        "resolver": "socket",
        "method": "getaddrinfo",
        "mx_hosts": [],
        "ips": [],
        "errors": [],
    }
    try:
        infos = socket.getaddrinfo(domain, None)
        ips = _dedupe([info[4][0] for info in infos if info and info[4]])
        detail["ips"] = ips
        return ips, detail
    except Exception as e:
        detail["errors"].append(f"socket_lookup_error:{e}")
        return [], detail


def resolve_domain_ips(domain: str) -> Tuple[List[str], Dict[str, Any]]:
    if dns is not None:
        ips, detail = _resolve_with_dnspython(domain)
        if ips:
            return ips, detail
    return _resolve_with_socket(domain)


def resolve_host_ips(host: str) -> Tuple[List[str], Dict[str, Any]]:
    normalized = _normalize_domain(host)
    if not normalized:
        return [], {
            "resolver": "none",
            "method": None,
            "mx_hosts": [],
            "ips": [],
            "errors": ["invalid_host"],
        }
    if dns is not None:
        ips, detail = _resolve_direct_with_dnspython(normalized)
        if ips:
            return ips, detail
    return _resolve_with_socket(normalized)


def _select_preferred_ip(ips: Iterable[str], prefer_ipv4: bool = True) -> Optional[str]:
    ip_list = list(ips)
    if not ip_list:
        return None
    if prefer_ipv4:
        for ip in ip_list:
            if ":" not in ip:
                return ip
    return ip_list[0]


def resolve_ip_from_email(email: Dict[str, Any], prefer_ipv4: bool = True) -> Tuple[Optional[str], str, Dict[str, Any]]:
    headers = email.get("headers") or {}
    domain, domain_source, domain_candidates = _get_origin_domain(headers)
    detail: Dict[str, Any] = {
        "domain": domain,
        "domain_source": domain_source,
        "domain_candidates": domain_candidates,
        "resolver_detail": None,
        "selected_ip": None,
    }

    if not domain:
        return None, "none", detail

    ips, resolver_detail = resolve_domain_ips(domain)
    detail["resolver_detail"] = resolver_detail
    detail["resolved_ips"] = ips

    selected_ip = _select_preferred_ip(ips, prefer_ipv4=prefer_ipv4)
    detail["selected_ip"] = selected_ip

    if not selected_ip:
        return None, "resolved_none", detail

    method = (resolver_detail or {}).get("method") or "dns"
    source = f"resolved_{method}"
    return selected_ip, source, detail


__all__ = ["resolve_domain_ips", "resolve_host_ips", "resolve_ip_from_email"]

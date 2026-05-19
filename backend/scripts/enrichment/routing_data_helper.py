from __future__ import annotations

"""
Extrae hops de Received, calcula senales por salto y agrega los peores valores para subcriterios de routing.
"""

import re
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from enrichment import domain_reputation_helper as domrep
from enrichment import ip_reputation_helper as iprep
from enrichment import domain_age_helper as domage
from enrichment import domain_vs_ip_country_helper as domip
from utils.subdomain_utils import count_host_labels_without_suffix, normalize_subdomain
from utils.domain_utils import extract_host_parts, normalize_host


EMAIL_DOMAIN_RE = re.compile(r"[A-Z0-9._%+-]+@([A-Z0-9.-]+\.[A-Z]{2,})", re.IGNORECASE)
IPV4_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")

ROUTING_SPLIT_CONFIG = {
    "routing_domain_reputation": {
        "summary_key": "domain_reputation_score",
        "default": None,
        "cast": "int",
    },
    "routing_ip_reputation": {
        "summary_key": "ip_reputation_score",
        "default": None,
        "cast": "int",
    },
    "routing_domain_age": {
        "summary_key": "domain_age_days",
        "default": None,
        "cast": "int",
    },
    "routing_country_mismatch": {
        "summary_key": "country_mismatch",
        "default": None,
        "cast": "float",
    },
    "routing_subdomain_count": {
        "summary_key": "subdomain_count",
        "default": 0,
        "cast": "int",
    },
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ensure_enrichment(email: Dict[str, Any]) -> None:
    email.setdefault("enrichment", {})
    email["enrichment"].setdefault(
        "routing_data",
        {
            "checked": False,
            "timestamp": None,
            "value": 0,
            "detail": None,
        },
    )
    for key in ROUTING_SPLIT_CONFIG:
        email["enrichment"].setdefault(
            key,
            {
                "checked": False,
                "timestamp": None,
                "value": None,
                "detail": None,
            },
        )


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


def _email_domains(value: Optional[str]) -> Iterable[str]:
    if not value or not isinstance(value, str):
        return []
    return [m.group(1).lower() for m in EMAIL_DOMAIN_RE.finditer(value)]


def _get_recipient_domains(headers: Dict[str, Any]) -> List[str]:
    domains = set()
    for key in ("to", "cc", "bcc", "delivered_to"):
        val = headers.get(key)
        if isinstance(val, str):
            domains.update(_email_domains(val))
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, str):
                    domains.update(_email_domains(item))
    return sorted(domains)


def _is_ip(value: Optional[str]) -> bool:
    if not value:
        return False
    if IPV4_RE.fullmatch(value):
        return True
    return ":" in value


def _registrable_domain(host: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    normalized_host, registrable_domain, subdomain, _domain_part, suffix = extract_host_parts(host)
    if not normalized_host or not registrable_domain:
        return None, None, None
    return registrable_domain, subdomain, suffix


def _subdomain_count(subdomain: Optional[str], registrable_label: Optional[str]) -> int:
    return count_host_labels_without_suffix(subdomain, registrable_label)


def _extract_received_ip(line: str) -> Optional[str]:
    if not line:
        return None
    m = re.search(r"\[([0-9a-fA-F\.:]+)\]", line)
    if m:
        return m.group(1).strip()
    m = re.search(r"\bfrom\s+[^\s]+\s+\(([0-9a-fA-F\.:]+)\)", line)
    if m:
        return m.group(1).strip()
    return None


def _extract_received_from(line: str) -> Optional[str]:
    if not line:
        return None
    m = re.search(r"\bfrom\s+([^\s\(\);]+)", line, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None


def _extract_received_by(line: str) -> Optional[str]:
    if not line:
        return None
    m = re.search(r"\bby\s+([^\s;]+)", line, re.IGNORECASE)
    if m:
        return m.group(1).strip().strip(")")
    return None


def _is_local_host(host: Optional[str]) -> bool:
    h = normalize_host(host)
    if not h:
        return False
    return h == "localhost" or h.endswith(".local") or h.endswith(".localdomain")


def _destination_domain_matches(by_host: Optional[str], recipient_domains: List[str]) -> bool:
    if not by_host or not recipient_domains:
        return False
    by_reg, _, _ = _registrable_domain(by_host)
    if not by_reg:
        return False
    return by_reg in recipient_domains


def _domain_rep(domain: Optional[str], force: bool) -> Dict[str, Any]:
    allow_http = domrep._allow_http_apis()
    if not domain:
        return {
            "domain": None,
            "score": domrep.DEFAULT_SCORE_RISK,
            "sources": [],
            "detail": {
                "method": domrep.NEUTRINO_HOST_REPUTATION_SOURCE,
                "http_apis_enabled": allow_http,
                "insufficient_data": True,
                "fallback_value_applied": True,
                "error_reason": "domain_not_found",
                "score_aspects": {},
                "api_detail": {},
                "api_scores": {},
                "score": domrep.DEFAULT_SCORE_RISK,
            },
        }

    if allow_http:
        score, api_detail = domrep._query_neutrino(domain, force=force)
    else:
        score = None
        api_detail = {"error": "http_apis_disabled"}

    insufficient = score is None
    normalized_score = domrep.DEFAULT_SCORE_RISK if insufficient else int(score)
    detail = {
        "method": domrep.NEUTRINO_HOST_REPUTATION_SOURCE,
        "http_apis_enabled": allow_http,
        "insufficient_data": insufficient,
        "fallback_value_applied": insufficient,
        "error_reason": api_detail.get("error") if insufficient else None,
        "score_aspects": {domrep.NEUTRINO_HOST_REPUTATION_SOURCE: {"score": normalized_score, "weight": 1.0}}
        if not insufficient
        else {},
        "api_detail": api_detail,
        "api_scores": {
            domrep.NEUTRINO_HOST_REPUTATION_SOURCE: {
                "score": normalized_score,
                "is_listed": api_detail.get("is_listed"),
                "list_count": api_detail.get("list_count"),
            }
        }
        if not insufficient
        else {},
        "score": normalized_score,
    }

    return {
        "domain": domain,
        "score": normalized_score,
        "sources": [domrep.NEUTRINO_HOST_REPUTATION_SOURCE] if not insufficient else [],
        "detail": detail,
    }


def _ip_rep(ip: Optional[str], force: bool) -> Dict[str, Any]:
    allow_http = iprep._allow_http_apis()
    if not ip:
        return {
            "ip": None,
            "score": iprep.DEFAULT_SCORE_RISK,
            "sources": [],
            "detail": {
                "method": "neutrino.ip_blocklist",
                "http_apis_enabled": allow_http,
                "insufficient_data": True,
                "fallback_value_applied": True,
                "error_reason": "ip_not_found",
                "score_aspects": {},
                "api_detail": {},
                "api_scores": {},
                "score": iprep.DEFAULT_SCORE_RISK,
            },
        }

    if allow_http:
        score, api_detail = iprep._query_neutrino(ip, force=force)
    else:
        score = None
        api_detail = {"error": "http_apis_disabled"}

    insufficient = score is None
    normalized_score = iprep.DEFAULT_SCORE_RISK if insufficient else int(score)
    detail = {
        "method": "neutrino.ip_blocklist",
        "http_apis_enabled": allow_http,
        "insufficient_data": insufficient,
        "fallback_value_applied": insufficient,
        "error_reason": api_detail.get("error") if insufficient else None,
        "score_aspects": {"neutrino.ip_blocklist": {"score": normalized_score, "weight": 1.0}} if not insufficient else {},
        "api_detail": api_detail,
        "api_scores": {
            "neutrino.ip_blocklist": {
                "score": normalized_score,
                "is_listed": api_detail.get("is_listed"),
            }
        }
        if not insufficient
        else {},
        "score": normalized_score,
    }
    return {
        "ip": ip,
        "score": normalized_score,
        "sources": ["neutrino.ip_blocklist"] if not insufficient else [],
        "detail": detail,
    }


def _domain_age(
    domain: Optional[str],
    force: bool,
    reference_dt: Optional[datetime],
    reference_detail: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return domage.resolve_domain_age(
        domain,
        force=force,
        reference_dt=reference_dt,
        reference_detail=reference_detail,
        domain_source="routing_hop",
    )


def _domain_ip_country(domain: Optional[str], ip: Optional[str], force: bool) -> Dict[str, Any]:
    allow_http = domip._allow_http_apis()
    if not domain or not ip:
        return {
            "domain_country": None,
            "domain_country_code": None,
            "ip_country": None,
            "ip_country_code": None,
            "match": None,
            "score": domip.UNKNOWN_SCORE,
            "detail": {
                "method": "neutrino.country_compare",
                "http_apis_enabled": allow_http,
                "insufficient_data": True,
                "comparison_status": "fallback_risk",
                "fallback_value_applied": True,
                "error_reason": "domain_or_ip_missing",
                "domain_source": "routing_hop",
                "ip_source": "routing_hop",
                "resolution_detail": None,
                "api_detail": {},
            },
        }

    _normalized_host, _registrable_domain, _subdomain, _domain_part, suffix = extract_host_parts(domain)
    country_tld_label = domip._country_tld_label_from_resolution({"suffix": suffix})
    if not country_tld_label:
        return {
            "domain_country": None,
            "domain_country_code": None,
            "ip_country": None,
            "ip_country_code": None,
            "match": None,
            "score": None,
            "detail": {
                "method": "neutrino.country_compare",
                "http_apis_enabled": allow_http,
                "insufficient_data": False,
                "comparison_status": "not_applicable_no_country_tld",
                "fallback_value_applied": False,
                "error_reason": None,
                "reason_code": domip.NO_COUNTRY_TLD_REASON,
                "reason": "El dominio del hop no usa un ccTLD y no permite comparar pais de dominio contra pais de IP.",
                "mcdm_excluded": True,
                "mcdm_exclusion_reason": domip.NO_COUNTRY_TLD_REASON,
                "analysis_status": "completed_not_applicable",
                "domain_source": "routing_hop",
                "domain_suffix": suffix,
                "country_tld_label": None,
                "ip_source": "routing_hop",
                "resolution_detail": None,
                "api_detail": {},
            },
        }

    api_detail: Dict[str, Any] = {}
    domain_country = None
    ip_country = None
    error_reason = None
    if allow_http:
        domain_country, domain_detail = domip._query_domain_country(domain, force=force)
        api_detail["domain"] = domain_detail
        ip_country, ip_detail = domip._query_ip_country(ip, force=force)
        api_detail["ip"] = ip_detail
        if not domain_country:
            error_reason = str(domain_detail.get("error") or "domain_country_not_found")
        elif not ip_country:
            error_reason = str(ip_detail.get("error") or "ip_country_not_found")
    else:
        api_detail["error"] = "http_apis_disabled"
        error_reason = "http_apis_disabled"

    domain_code = domain_country if isinstance(domain_country, str) else None
    ip_code = ip_country if isinstance(ip_country, str) else None
    match = None
    if domain_code and ip_code:
        match = domain_code == ip_code

    insufficient = not (domain_code and ip_code)
    if match is None:
        comparison_status = "fallback_risk"
        score = domip.UNKNOWN_SCORE
    else:
        comparison_status = "match" if match else "mismatch"
        score = 0.0 if match else 1.0

    detail = {
        "method": "neutrino.country_compare",
        "http_apis_enabled": allow_http,
        "insufficient_data": insufficient,
        "comparison_status": comparison_status,
        "fallback_value_applied": insufficient,
        "error_reason": error_reason,
        "reason_code": error_reason,
        "reason": None,
        "mcdm_excluded": False,
        "mcdm_exclusion_reason": None,
        "analysis_status": "completed",
        "domain_source": "routing_hop",
        "domain_suffix": suffix,
        "country_tld_label": country_tld_label,
        "ip_source": "routing_hop",
        "resolution_detail": None,
        "api_detail": api_detail,
    }

    result = {
        "domain_country": domip._country_display(domain_code),
        "domain_country_code": domain_code,
        "ip_country": domip._country_display(ip_code),
        "ip_country_code": ip_code,
        "match": match,
        "score": float(score),
        "detail": detail,
    }

    return result


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _worst_of_scores(
    hops: List[Dict[str, Any]],
    field: str,
    id_key: str,
) -> Dict[str, Any]:
    """
    Pick the hop with the highest score for a given per-hop subcriterion block.

    Expects hop[field] to be a dict with keys: score, detail.insufficient_data.
    Hops marked as insufficient_data are excluded from the aggregation. If none
    of the processed hops expose a valid score, the split subcriterion becomes
    null and is excluded downstream from MCDM.
    """
    candidates: List[Tuple[float, Dict[str, Any]]] = []
    invalid_hops = 0

    for hop in hops:
        block = hop.get(field)
        if not isinstance(block, dict):
            continue
        score = block.get("score")
        if not _is_number(score):
            continue
        detail = block.get("detail") or {}
        insufficient = bool(isinstance(detail, dict) and detail.get("insufficient_data") is True)
        if insufficient:
            invalid_hops += 1
            continue
        candidates.append((float(score), hop))

    if not candidates:
        return {
            "value": None,
            "insufficient_data": True,
            "source": None,
            "valid_hops": 0,
            "invalid_hops": invalid_hops,
        }

    score, hop = max(candidates, key=lambda it: it[0])
    block = hop.get(field) if isinstance(hop.get(field), dict) else {}
    return {
        "value": float(score),
        "insufficient_data": False,
        "valid_hops": len(candidates),
        "invalid_hops": invalid_hops,
        "source": {
            "hop_index": hop.get("index"),
            "position": hop.get("position"),
            id_key: hop.get(id_key),
            "sources": block.get("sources"),
            "detail": block.get("detail"),
        },
    }


def _worst_of_domain_age(hops: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Pick the lowest age_days (youngest domain) only among hops with a valid age.

    Hops whose age block is marked as insufficient_data are excluded from the
    aggregation. If none of the processed hops expose a valid age, the routing
    age subcriterion becomes null and is excluded downstream from MCDM.
    """
    candidates: List[Tuple[int, Dict[str, Any]]] = []
    invalid_hops = 0

    for hop in hops:
        block = hop.get("domain_age")
        if not isinstance(block, dict):
            continue
        age_days = block.get("age_days")
        if not isinstance(age_days, int) or isinstance(age_days, bool):
            continue
        detail = block.get("detail") or {}
        insufficient = bool(isinstance(detail, dict) and detail.get("insufficient_data") is True)
        if insufficient:
            invalid_hops += 1
            continue
        candidates.append((int(age_days), hop))

    if not candidates:
        return {
            "value": None,
            "insufficient_data": True,
            "source": None,
            "valid_hops": 0,
            "invalid_hops": invalid_hops,
        }

    age_days, hop = min(candidates, key=lambda it: it[0])
    block = hop.get("domain_age") if isinstance(hop.get("domain_age"), dict) else {}
    return {
        "value": int(age_days),
        "insufficient_data": False,
        "valid_hops": len(candidates),
        "invalid_hops": invalid_hops,
        "source": {
            "hop_index": hop.get("index"),
            "position": hop.get("position"),
            "domain": hop.get("domain"),
            "detail": block.get("detail"),
        },
    }


def _worst_of_country_mismatch(hops: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Worst = any mismatch among comparable hops.

    Hops marked as not applicable because they do not expose a country ccTLD are
    excluded from the aggregation. If every processed hop is excluded for that
    reason, the split subcriterion becomes null and is excluded downstream from
    MCDM.
    """
    mismatch: List[Dict[str, Any]] = []
    match: List[Dict[str, Any]] = []
    no_data: List[Dict[str, Any]] = []
    excluded: List[Dict[str, Any]] = []

    for hop in hops:
        block = hop.get("country")
        if not isinstance(block, dict):
            continue
        detail = block.get("detail") if isinstance(block.get("detail"), dict) else {}
        if detail.get("mcdm_excluded") is True:
            excluded.append(hop)
            continue
        m = block.get("match")
        if m is False:
            mismatch.append(hop)
        elif m is True:
            match.append(hop)
        else:
            no_data.append(hop)

    chosen = mismatch[0] if mismatch else (match[0] if match else None)
    if not chosen:
        if excluded:
            return {
                "value": None,
                "insufficient_data": False,
                "mcdm_excluded": True,
                "mcdm_exclusion_reason": domip.NO_COUNTRY_TLD_REASON,
                "valid_hops": 0,
                "invalid_hops": len(excluded),
                "source": None,
            }
        return {
            "value": None,
            "insufficient_data": True,
            "mcdm_excluded": False,
            "mcdm_exclusion_reason": None,
            "valid_hops": len(no_data),
            "invalid_hops": len(excluded),
            "source": {
                "hop_index": no_data[0].get("index"),
                "position": no_data[0].get("position"),
                "domain": no_data[0].get("domain"),
                "ip": no_data[0].get("ip"),
                "detail": (no_data[0].get("country") or {}).get("detail"),
            }
            if no_data
            else None,
        }

    block = chosen.get("country") if isinstance(chosen.get("country"), dict) else {}
    is_mismatch = block.get("match") is False
    value = 1 if is_mismatch else 0
    return {
        "value": value,
        "insufficient_data": False,
        "mcdm_excluded": False,
        "mcdm_exclusion_reason": None,
        "valid_hops": len(mismatch) + len(match),
        "invalid_hops": len(excluded),
        "source": {
            "hop_index": chosen.get("index"),
            "position": chosen.get("position"),
            "domain": chosen.get("domain"),
            "ip": chosen.get("ip"),
            "domain_country_code": block.get("domain_country_code"),
            "ip_country_code": block.get("ip_country_code"),
            "match": block.get("match"),
            "detail": block.get("detail"),
        },
    }


def _worst_of_subdomain_count(hops: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Worst = max subdomain_count among hops.
    """
    candidates: List[Tuple[int, Dict[str, Any]]] = []
    for hop in hops:
        count = hop.get("subdomain_count")
        if isinstance(count, int) and not isinstance(count, bool):
            candidates.append((int(count), hop))
    if not candidates:
        return {"value": None, "insufficient_data": True, "source": None}
    count, hop = max(candidates, key=lambda it: it[0])
    return {
        "value": int(count),
        "insufficient_data": False,
        "source": {
            "hop_index": hop.get("index"),
            "position": hop.get("position"),
            "domain": hop.get("domain"),
            "subdomain": hop.get("subdomain"),
            "subdomain_normalized": hop.get("subdomain_normalized"),
            "subdomain_count": hop.get("subdomain_count"),
        },
    }


def _worst_routing_summary(hops: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute a "worst-of" summary across all processed hops.

    This is a synthetic view (not a real domain) that keeps, for each sub-subcriterion
    in routing data, the worst (most malicious) value observed across hops.
    """
    return {
        "domain_reputation_score": _worst_of_scores(hops, field="domain_reputation", id_key="domain"),
        "ip_reputation_score": _worst_of_scores(hops, field="ip_reputation", id_key="ip"),
        "domain_age_days": _worst_of_domain_age(hops),
        "country_mismatch": _worst_of_country_mismatch(hops),
        "subdomain_count": _worst_of_subdomain_count(hops),
    }


def _compute_routing_analysis(email: Dict[str, Any], force: bool = False) -> Dict[str, Any]:
    headers = email.get("headers") or {}
    headers = headers if isinstance(headers, dict) else {}
    received_values = list(_iter_header_values(headers.get("received")))
    reference_dt, reference_detail = domage.get_email_reference_datetime(email)
    recipient_domains_raw = _get_recipient_domains(headers)
    recipient_domains = []
    for dom in recipient_domains_raw:
        reg, _, _ = _registrable_domain(dom)
        if reg and reg not in recipient_domains:
            recipient_domains.append(reg)

    hops: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []

    for idx, line in enumerate(received_values):
        from_host = _extract_received_from(line)
        by_host = _extract_received_by(line)
        ip = _extract_received_ip(line)
        if not ip and _is_ip(normalize_host(from_host)):
            ip = normalize_host(from_host)

        if _is_local_host(from_host) or _is_local_host(by_host):
            skipped.append(
                {
                    "index": idx,
                    "raw": line,
                    "from_host": from_host,
                    "by_host": by_host,
                    "reason": "local_domain",
                }
            )
            continue

        if _destination_domain_matches(by_host, recipient_domains):
            skipped.append(
                {
                    "index": idx,
                    "raw": line,
                    "from_host": from_host,
                    "by_host": by_host,
                    "reason": "destination_domain",
                }
            )
            continue

        hop_host = normalize_host(from_host or by_host)
        hop_registrable_domain, hop_subdomain, hop_suffix = _registrable_domain(hop_host)
        hop_registrable_label = hop_registrable_domain.split(".", 1)[0] if hop_registrable_domain else None
        hop_subdomain_count = _subdomain_count(hop_subdomain, hop_registrable_label)
        hop_subdomain_normalized = normalize_subdomain(hop_subdomain)

        hop_domain_rep = _domain_rep(hop_host, force=force)
        hop_ip_rep = _ip_rep(ip, force=force)
        hop_age = _domain_age(
            hop_host,
            force=force,
            reference_dt=reference_dt,
            reference_detail=reference_detail,
        )
        hop_country = _domain_ip_country(hop_host, ip, force=force)

        position = "closest" if idx == 0 else "farthest" if idx == len(received_values) - 1 else "middle"

        hops.append(
            {
                "index": idx,
                "position": position,
                "raw": line,
                "from_host": from_host,
                "by_host": by_host,
                "host": hop_host,
                "domain": hop_host,
                "registrable_domain": hop_registrable_domain,
                "subdomain": hop_subdomain,
                "subdomain_normalized": hop_subdomain_normalized,
                "suffix": hop_suffix,
                "subdomain_count": hop_subdomain_count,
                "ip": ip,
                "domain_reputation": hop_domain_rep,
                "ip_reputation": hop_ip_rep,
                "domain_age": hop_age,
                "country": hop_country,
            }
        )

    return {
        "total_received": len(received_values),
        "processed_hops": len(hops),
        "skipped_hops": len(skipped),
        "recipient_domains": recipient_domains,
        "reference": reference_detail,
        "hops": hops,
        "skipped": skipped,
        "worst": _worst_routing_summary(hops),
    }


def _cast_split_value(value: Any, cast: str, default: float | int | None) -> float | int | None:
    if default is None and value is None:
        return None
    if cast == "float":
        if _is_number(value):
            return float(value)
        return float(default)
    if isinstance(value, int) and not isinstance(value, bool):
        return int(value)
    if isinstance(value, float):
        return int(value)
    if default is None:
        return None
    return int(default)


def _build_split_detail(metric_key: str, analysis: Dict[str, Any], worst_entry: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "metric_key": metric_key,
        "insufficient_data": bool(worst_entry.get("insufficient_data", True)),
        "mcdm_excluded": bool(worst_entry.get("mcdm_excluded", False)),
        "mcdm_exclusion_reason": worst_entry.get("mcdm_exclusion_reason"),
        "source": worst_entry.get("source"),
        "valid_hops": worst_entry.get("valid_hops"),
        "invalid_hops": worst_entry.get("invalid_hops"),
        "processed_hops": analysis.get("processed_hops"),
        "total_received": analysis.get("total_received"),
        "skipped_hops": analysis.get("skipped_hops"),
        "recipient_domains": analysis.get("recipient_domains"),
    }


def _populate_routing_split_entries(
    email: Dict[str, Any],
    analysis: Dict[str, Any],
) -> set[str]:
    _ensure_enrichment(email)
    changed: set[str] = set()
    timestamp = _now_iso()
    worst = analysis.get("worst") if isinstance(analysis.get("worst"), dict) else {}
    worst = worst if isinstance(worst, dict) else {}

    for key, config in ROUTING_SPLIT_CONFIG.items():
        summary_key = str(config["summary_key"])
        worst_entry = worst.get(summary_key)
        worst_entry = worst_entry if isinstance(worst_entry, dict) else {}
        value = _cast_split_value(worst_entry.get("value"), str(config["cast"]), config["default"])
        new_entry = {
            "checked": True,
            "timestamp": timestamp,
            "value": value,
            "detail": _build_split_detail(summary_key, analysis, worst_entry),
        }
        current_entry = email["enrichment"].get(key)
        if current_entry != new_entry:
            email["enrichment"][key] = new_entry
            changed.add(key)

    return changed


def _enrich_routing_split_entries(email: Dict[str, Any], force: bool = False) -> set[str]:
    _ensure_enrichment(email)
    analysis = _compute_routing_analysis(email, force=force)
    return _populate_routing_split_entries(email, analysis)


def enrich_routing_domain_reputation_in_data(email: Dict[str, Any], force: bool = False) -> bool:
    return "routing_domain_reputation" in _enrich_routing_split_entries(email, force=force)


def enrich_routing_ip_reputation_in_data(email: Dict[str, Any], force: bool = False) -> bool:
    return "routing_ip_reputation" in _enrich_routing_split_entries(email, force=force)


def enrich_routing_domain_age_in_data(email: Dict[str, Any], force: bool = False) -> bool:
    return "routing_domain_age" in _enrich_routing_split_entries(email, force=force)


def enrich_routing_country_mismatch_in_data(email: Dict[str, Any], force: bool = False) -> bool:
    return "routing_country_mismatch" in _enrich_routing_split_entries(email, force=force)


def enrich_routing_subdomain_count_in_data(email: Dict[str, Any], force: bool = False) -> bool:
    return "routing_subdomain_count" in _enrich_routing_split_entries(email, force=force)


def enrich_routing_data_in_data(email: Dict[str, Any], force: bool = False) -> bool:
    _ensure_enrichment(email)
    entry = email["enrichment"]["routing_data"]

    analysis = _compute_routing_analysis(email, force=force)
    _populate_routing_split_entries(email, analysis)

    entry["checked"] = True
    entry["timestamp"] = _now_iso()
    entry["value"] = int(analysis.get("processed_hops") or 0)
    entry["detail"] = analysis
    return True


__all__ = [
    "enrich_routing_domain_reputation_in_data",
    "enrich_routing_ip_reputation_in_data",
    "enrich_routing_domain_age_in_data",
    "enrich_routing_country_mismatch_in_data",
    "enrich_routing_subdomain_count_in_data",
    "enrich_routing_data_in_data",
]

from __future__ import annotations

"""
Centraliza la extraccion y puntuacion de SPF, DKIM y DMARC a partir de cabeceras ya parseadas para evitar duplicidad entre enriquecimiento y visualizacion.
"""

import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple


REC_SPF_STATUS_RE = re.compile(r"^([a-zA-Z]+)")
AUTH_SPF_TOKEN_RE = re.compile(r"spf\s*=\s*([a-zA-Z]+)")
AUTH_DKIM_TOKEN_RE = re.compile(r"dkim\s*=\s*([a-zA-Z]+)")
AUTH_DMARC_RESULT_RE = re.compile(r"dmarc\s*=\s*([a-zA-Z]+)")
AUTH_DMARC_POLICY_RE = re.compile(r"(?:policy|p)\s*=\s*([a-zA-Z]+)", re.IGNORECASE)


SPF_SCORE_MAP: Dict[str, float] = {
    "pass": 0.0,
    "neutral": 0.5,
    "none": 0.6,
    "softfail": 1.0,
    "fail": 1.0,
    "temperror": 0.5,
    "permerror": 0.75,
    "no-data": 0.75,
}

DKIM_SCORE_MAP: Dict[str, float] = {
    "pass": 0.0,
    "neutral": 0.5,
    "none": 0.6,
    "temperror": 0.5,
    "permerror": 0.75,
    "fail": 1.0,
    "no-data": 0.75,
}

DMARC_STATUS_SCORE_MAP: Dict[str, float] = {
    "pass": 0.0,
    "none": 0.6,
    "temperror": 0.5,
    "fail": 0.7,
    "permerror": 0.8,
    "quarantine": 0.75,
    "reject": 1.0,
    "no-data": 1.0,
}

DMARC_FAIL_POLICY_SCORE_MAP: Dict[str, float] = {
    "none": 0.5,
    "quarantine": 0.75,
    "reject": 1.0,
}

DMARC_POLICY_ORDER: Dict[str, int] = {
    "none": 1,
    "quarantine": 2,
    "reject": 3,
}

DMARC_AUTH_ALIGNMENT_RULE_VERSION = 2
DMARC_PASS_WITH_AUTH_FAILURE_SCORE = 0.6


def _header_values(headers: Dict[str, Any], key: str) -> List[str]:
    value = headers.get(key)
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    if isinstance(value, str):
        return [value]
    return []


def extract_spf_from_received_spf_lines(lines: List[str]) -> List[str]:
    statuses: List[str] = []
    for val in lines or []:
        if not isinstance(val, str):
            continue
        match = REC_SPF_STATUS_RE.match(val.strip())
        if match:
            statuses.append(match.group(1).lower())
    return statuses


def extract_spf_from_auth_results(auth_lines: List[str]) -> List[str]:
    statuses: List[str] = []
    for line in auth_lines or []:
        if not isinstance(line, str):
            continue
        for match in AUTH_SPF_TOKEN_RE.finditer(line):
            statuses.append(match.group(1).lower())
    return statuses


def normalize_spf_status(status: str) -> str:
    cleaned = (status or "").strip().lower()
    catalog = {
        "pass": "pass",
        "fail": "fail",
        "softfail": "softfail",
        "neutral": "neutral",
        "none": "none",
        "temperror": "temperror",
        "permerror": "permerror",
        "no-data": "no-data",
    }
    return catalog.get(cleaned, cleaned)


def spf_status_to_score(status: str) -> Optional[float]:
    return SPF_SCORE_MAP.get(normalize_spf_status(status), 1.0)


def extract_dkim_from_auth_results(auth_lines: List[str]) -> List[str]:
    statuses: List[str] = []
    for line in auth_lines or []:
        if not isinstance(line, str):
            continue
        for match in AUTH_DKIM_TOKEN_RE.finditer(line):
            statuses.append(match.group(1).lower())
    return statuses


def normalize_dkim_status(status: str) -> str:
    cleaned = (status or "").strip().lower()
    aliases = {
        "pass": "pass",
        "fail": "fail",
        "temperror": "temperror",
        "permerror": "permerror",
        "neutral": "neutral",
        "none": "none",
        "no-data": "no-data",
    }
    return aliases.get(cleaned, cleaned)


def dkim_status_to_score(status: str) -> Optional[float]:
    return DKIM_SCORE_MAP.get(normalize_dkim_status(status), 1.0)


def normalize_dmarc_status(status: str) -> str:
    cleaned = (status or "").strip().lower()
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
        "quarantine": "quarantine",
        "reject": "reject",
        "no-data": "no-data",
    }
    if cleaned in aliases:
        return aliases[cleaned]
    if "quarantine" in cleaned:
        return "quarantine"
    if "reject" in cleaned:
        return "reject"
    return cleaned


def dmarc_status_to_score(status: str) -> Optional[float]:
    return DMARC_STATUS_SCORE_MAP.get(normalize_dmarc_status(status), 1.0)


def compute_status_value(
    statuses: List[str],
    normalizer,
    scorer,
) -> Tuple[Optional[float], Dict[str, int]]:
    if not statuses:
        return None, {}
    normalized = [normalizer(s) for s in statuses]
    counts = Counter(normalized)
    scores: List[float] = []
    for token in normalized:
        score = scorer(token)
        if score is not None:
            scores.append(score)
    if not scores:
        return None, dict(counts)
    return max(scores), dict(counts)


def scores_worst(scores: List[Optional[float]]) -> Optional[float]:
    present = [s for s in scores if s is not None]
    return max(present) if present else None


def build_spf_result_from_headers(headers: Dict[str, Any]) -> Dict[str, Any]:
    headers = headers if isinstance(headers, dict) else {}
    rec_spf_status = extract_spf_from_received_spf_lines(_header_values(headers, "received_spf"))
    auth_spf_status = extract_spf_from_auth_results(_header_values(headers, "authentication_results"))
    all_statuses = rec_spf_status + auth_spf_status
    header_value, counts = compute_status_value(all_statuses, normalize_spf_status, spf_status_to_score)

    auth_scores: List[Optional[float]] = [spf_status_to_score(s) for s in auth_spf_status]
    rec_scores: List[Optional[float]] = [spf_status_to_score(s) for s in rec_spf_status]
    auth_worst = scores_worst(auth_scores)
    rec_worst = scores_worst(rec_scores)

    return {
        "criterion": "criterio1.spf",
        "value": 1.0 if header_value is None else header_value,
        "sources": {
            "received_spf": rec_spf_status,
            "authentication_results": auth_spf_status,
        },
        "counts": counts,
        "aggregation": {
            "headers": {
                "auth": {"worst": auth_worst, "count": len([s for s in auth_scores if s is not None])},
                "received_spf": {"worst": rec_worst, "count": len([s for s in rec_scores if s is not None])},
                "combined": {
                    "worst": scores_worst(
                        ([auth_worst] if auth_worst is not None else [])
                        + ([rec_worst] if rec_worst is not None else [])
                    ),
                },
            }
        },
        "total_observations": len(all_statuses),
    }


def build_dkim_result_from_headers(headers: Dict[str, Any]) -> Dict[str, Any]:
    headers = headers if isinstance(headers, dict) else {}
    auth_dkim_status = extract_dkim_from_auth_results(_header_values(headers, "authentication_results"))
    header_value, counts = compute_status_value(auth_dkim_status, normalize_dkim_status, dkim_status_to_score)

    auth_scores: List[Optional[float]] = [dkim_status_to_score(s) for s in auth_dkim_status]
    auth_worst = scores_worst(auth_scores)

    return {
        "criterion": "criterio1.dkim",
        "value": 1.0 if header_value is None else header_value,
        "sources": {"authentication_results": auth_dkim_status},
        "counts": counts,
        "aggregation": {
            "headers": {
                "auth": {"worst": auth_worst, "count": len([s for s in auth_scores if s is not None])},
                "combined": {"worst": auth_worst},
            }
        },
        "total_observations": len(auth_dkim_status),
    }


def _effective_policy(policy_tokens: List[str]) -> Optional[str]:
    normalized: List[str] = []
    for token in policy_tokens:
        policy = normalize_dmarc_status(token)
        if policy in DMARC_POLICY_ORDER:
            normalized.append(policy)
    if not normalized:
        return None
    return max(normalized, key=lambda token: DMARC_POLICY_ORDER[token])


def dmarc_observation_to_score(result: Optional[str], policy: Optional[str]) -> Optional[float]:
    normalized_result = normalize_dmarc_status(result or "")
    normalized_policy = normalize_dmarc_status(policy or "") if policy else None

    if normalized_result == "pass":
        return 0.0
    if normalized_result == "fail" and normalized_policy in DMARC_FAIL_POLICY_SCORE_MAP:
        return DMARC_FAIL_POLICY_SCORE_MAP[normalized_policy]
    if normalized_result in DMARC_STATUS_SCORE_MAP:
        return DMARC_STATUS_SCORE_MAP[normalized_result]
    if normalized_result:
        return dmarc_status_to_score(normalized_result)
    return None


def _all_statuses_pass(statuses: List[str], normalizer) -> bool:
    return bool(statuses) and all(normalizer(status) == "pass" for status in statuses)


def extract_spf_dkim_auth_context(headers: Dict[str, Any]) -> Dict[str, Any]:
    auth_lines = _header_values(headers, "authentication_results")
    rec_spf_lines = _header_values(headers, "received_spf")

    auth_spf_status = extract_spf_from_auth_results(auth_lines)
    rec_spf_status = extract_spf_from_received_spf_lines(rec_spf_lines)
    spf_statuses = rec_spf_status + auth_spf_status
    dkim_statuses = extract_dkim_from_auth_results(auth_lines)

    return {
        "spf": {
            "received_spf": rec_spf_status,
            "authentication_results": auth_spf_status,
            "statuses": spf_statuses,
            "pass": _all_statuses_pass(spf_statuses, normalize_spf_status),
        },
        "dkim": {
            "authentication_results": dkim_statuses,
            "statuses": dkim_statuses,
            "pass": _all_statuses_pass(dkim_statuses, normalize_dkim_status),
        },
    }


def apply_spf_dkim_context_to_observations(
    observations: List[Dict[str, Any]],
    auth_context: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    spf_pass = bool((auth_context.get("spf") or {}).get("pass"))
    dkim_pass = bool((auth_context.get("dkim") or {}).get("pass"))
    should_adjust_pass = not (spf_pass and dkim_pass)
    adjusted = False
    adjusted_observations: List[Dict[str, Any]] = []

    for observation in observations:
        updated = dict(observation)
        if updated.get("result") == "pass" and should_adjust_pass:
            raw_score = updated.get("score")
            score = float(raw_score) if isinstance(raw_score, (int, float)) else 0.0
            updated["score"] = max(score, DMARC_PASS_WITH_AUTH_FAILURE_SCORE)
            updated["auth_context_adjusted"] = True
            updated["auth_context_reason"] = "dmarc_pass_but_spf_or_dkim_not_pass"
            adjusted = True
        adjusted_observations.append(updated)

    return adjusted_observations, {
        "rule_version": DMARC_AUTH_ALIGNMENT_RULE_VERSION,
        "score_when_dmarc_pass_but_spf_or_dkim_not_pass": DMARC_PASS_WITH_AUTH_FAILURE_SCORE,
        "adjusted": adjusted,
        "spf_pass": spf_pass,
        "dkim_pass": dkim_pass,
        "reason": "dmarc_pass_but_spf_or_dkim_not_pass" if adjusted else None,
        "spf": auth_context.get("spf"),
        "dkim": auth_context.get("dkim"),
    }


def extract_dmarc_tokens_and_policy(
    auth_lines: List[str],
) -> Tuple[List[str], Optional[str], List[str], List[Dict[str, Any]]]:
    tokens: List[str] = []
    policy_tokens: List[str] = []
    norm_auth_lines: List[str] = []
    observations: List[Dict[str, Any]] = []

    for line in auth_lines or []:
        if not isinstance(line, str):
            continue
        norm_auth_lines.append(line)

        result_token: Optional[str] = None
        m_res = AUTH_DMARC_RESULT_RE.search(line)
        if m_res:
            result_token = (m_res.group(1) or "").strip().lower()
            tokens.append(result_token)

        line_policy_tokens: List[str] = []
        for m in AUTH_DMARC_POLICY_RE.finditer(line):
            pol = (m.group(1) or "").strip().lower()
            if pol not in ("reject", "quarantine", "none"):
                continue
            line_policy_tokens.append(pol)
            policy_tokens.append(pol)
            if result_token is None or normalize_dmarc_status(result_token) != "pass":
                tokens.append(pol)

        effective_policy = _effective_policy(line_policy_tokens)
        score = dmarc_observation_to_score(result_token, effective_policy)
        if score is not None:
            observations.append(
                {
                    "result": normalize_dmarc_status(result_token),
                    "policy": effective_policy,
                    "score": score,
                }
            )

    policy = _effective_policy(policy_tokens)
    return tokens, policy, norm_auth_lines, observations


def compute_dmarc_value(
    tokens: List[str],
    observations: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[Optional[float], Dict[str, int]]:
    if not tokens and not observations:
        return None, {}

    normalized = [normalize_dmarc_status(t) for t in tokens]
    counts = Counter(normalized)

    scores: List[float] = []
    for observation in observations or []:
        score = observation.get("score")
        if isinstance(score, (int, float)):
            scores.append(float(score))

    if not scores:
        for token in normalized:
            score = dmarc_status_to_score(token)
            if score is not None:
                scores.append(score)

    if not scores:
        return None, dict(counts)
    return max(scores), dict(counts)


def existing_dmarc_result_uses_current_rules(existing_result: Dict[str, Any]) -> bool:
    if not isinstance(existing_result, dict) or existing_result.get("value") is None:
        return False
    detail = existing_result.get("detail")
    detail = detail if isinstance(detail, dict) else {}
    return detail.get("auth_context_rule_version") == DMARC_AUTH_ALIGNMENT_RULE_VERSION


def build_dmarc_result_from_headers(headers: Dict[str, Any]) -> Dict[str, Any]:
    headers = headers if isinstance(headers, dict) else {}
    auth_lines_raw = _header_values(headers, "authentication_results")
    tokens, policy, auth_lines, observations = extract_dmarc_tokens_and_policy(auth_lines_raw)

    auth_context = extract_spf_dkim_auth_context(headers)
    observations, auth_context_adjustment = apply_spf_dkim_context_to_observations(
        observations,
        auth_context,
    )

    header_value, counts = compute_dmarc_value(tokens, observations=observations)
    auth_scores = [float(obs["score"]) for obs in observations if isinstance(obs.get("score"), (int, float))]
    auth_worst = scores_worst(auth_scores)

    return {
        "criterion": "criterio1.dmarc",
        "value": 1.0 if header_value is None else header_value,
        "auth_context_rule_version": DMARC_AUTH_ALIGNMENT_RULE_VERSION,
        "tokens": tokens,
        "policy": policy,
        "observations": observations,
        "sources": {
            "authentication_results": auth_lines,
            "spf": auth_context.get("spf"),
            "dkim": auth_context.get("dkim"),
        },
        "counts": counts,
        "aggregation": {
            "headers": {
                "auth": {"worst": auth_worst, "count": len(auth_scores)},
                "combined": {"worst": auth_worst},
            }
        },
        "auth_context": auth_context_adjustment,
        "extracted": {"auth_results": auth_lines},
        "total_observations": len(observations),
    }


__all__ = [
    "build_dkim_result_from_headers",
    "build_dmarc_result_from_headers",
    "build_spf_result_from_headers",
    "dkim_status_to_score",
    "dmarc_status_to_score",
    "existing_dmarc_result_uses_current_rules",
    "extract_dkim_from_auth_results",
    "extract_spf_from_auth_results",
    "extract_spf_from_received_spf_lines",
    "normalize_dkim_status",
    "normalize_dmarc_status",
    "normalize_spf_status",
    "spf_status_to_score",
]
